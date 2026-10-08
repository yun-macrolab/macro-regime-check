#!/usr/bin/env python3
"""저녁판 수집(tg_collect) 테스트 — 미리보기 쪽에서 글을 읽는지, 창·예산·실패를 닫힌 쪽으로 다루는지, 글자가 출력으로 새지 않는지.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서) · python scripts/evening/test_tg_collect.py
네트워크 불필요 — fixtures.py의 지어낸 글로 만든 쪽(미리보기와 같은 뼈대)과 가짜 urlopen만 쓴다. 실제 채널 글은 없다.
"""
import contextlib
import copy
import email
import html
import http.client
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
import urllib.request
import urllib.response
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_schema as S
import fixtures as F
import tg_collect as T

TH = S.TH
BASE = "https://t.me/s/"
Q = "?q=" + urllib.parse.quote(TH["wire_query"])
WIRE = tuple(ch for ch in F.REQUESTED if F.ROLE[ch] == "wire")
ORDER = tuple(ch for ch in F.REQUESTED if ch not in WIRE) + WIRE          # 채권 → 애널 → 개인 → 속보형
TEXT = "지어낸 글 한 줄입니다. 길이를 채우는 문장."
MSG = "tgme_widget_message text_not_supported_wrap js-widget_message"


def url(ch, before=None, search=None):
    """그 채널의 요청 주소 — 속보형의 첫 쪽은 검색, before를 주면 '한 쪽 더'."""
    if before is not None:
        return f"{BASE}{ch}?before={before}"
    return BASE + ch + (Q if (ch in WIRE if search is None else search) else "")


def post(ch, pid, at, text=TEXT, **kw):
    """지어낸 글 하나(계약의 post 꼴)."""
    return {"ch": ch, "id": pid, "at": at, "text": text, "links": [], "fwd": None, "card": None, "reply": False,
            "media": not text, "via": "search" if ch in WIRE else "page", **kw}


def run_of(ch, first, n, start="2026-10-08T09:00:00+09:00"):
    """번호가 이어지는 글 n개 — 1분 간격."""
    t0 = S.parse_iso(start)
    return [post(ch, first + i, S.iso(t0 + T.datetime.timedelta(minutes=i))) for i in range(n)]


def line(ch, code, pages, posts, text, timed, window, streak=0, cut=0):
    """채널 한 줄의 꼴 — 목록의 채널 이름과 코드·개수뿐이다."""
    return (f"[tg_collect] {ch} code={code} pages={pages} posts={posts} with_text={text} with_time={timed} in_window={window} "
            f"fail_streak={streak} cut={cut}\n")


def site(**over):
    """{주소: 쪽} — 요청하는 채널마다 첫 쪽(속보형은 검색 쪽). 없는 주소는 Net이 '글 없는 그 채널의 쪽'을 준다."""
    return {**{url(ch): F.render_page(ch) for ch in F.REQUESTED}, **over}


def state_with(**anchors):
    """직전 판 상태(F.state)에서 채널의 마지막 글 기록만 바꾼 것."""
    st = copy.deepcopy(F.state())
    for ch, row in anchors.items():
        st["edition"]["channels"][ch] = {"fail_streak": 0, **row}
    return st


def msg(ch, pid, inner, when="2026-10-08T01:00:00+00:00", cls=MSG):
    """실제 미리보기 쪽과 같은 뼈대의 글 하나 — 안쪽(전달 머리·본문·카드)은 inner로 준다."""
    time = f'<time datetime="{when}" class="time">10:00</time>' if when else '<time class="time">10:00</time>'
    return (f'<div class="tgme_widget_message_wrap js-widget_message_wrap"><div class="{cls}" data-post="{ch}/{pid}">'
            f'<div class="tgme_widget_message_user"><a href="https://t.me/{ch}"><i class="tgme_widget_message_user_photo"></i></a></div>'
            f'<div class="tgme_widget_message_bubble">{inner}<div class="tgme_widget_message_footer compact js-message_footer">'
            f'<div class="tgme_widget_message_info short js-message_info"><span class="tgme_widget_message_views">1</span>'
            f'<span class="tgme_widget_message_meta"><a class="tgme_widget_message_date" href="https://t.me/{ch}/{pid}">'
            f'{time}</a></span></div></div></div></div></div>')


def body(inner, cls="tgme_widget_message_text js-message_text"):
    return f'<div class="{cls}" dir="auto">{inner}</div>'


def page_of(ch, *msgs):
    return (f'<html><head><meta property="og:title" content="{html.escape(F.TITLE[ch])}"></head><body>'
            f'<section class="tgme_channel_history js-message_history">{"".join(msgs)}</section></body></html>')


def one(inner, **kw):
    """글 하나짜리 쪽을 읽은 결과."""
    got = T.parse_page(page_of("fxbond1", msg("fxbond1", 7, inner, **kw)), "fxbond1")
    assert len(got) == 1
    return got[0]


class Resp(io.BytesIO):
    def __init__(self, data, final):
        super().__init__(data)
        self.final = final

    def geturl(self):
        return self.final


class Net:
    """urlopen · sleep · 시계의 대역 — 주소별 쪽을 돌려주고, 부른 주소와 쉰 시간을 적고, 가짜 시계를 돌린다."""

    def __init__(self, pages=None, fail=None, final=None, cost=1.0):
        self.pages, self.fail, self.final = dict(site() if pages is None else pages), dict(fail or {}), dict(final or {})
        self.cost = cost
        self.calls, self.timeouts, self.naps, self.t = [], [], [], 0.0

    def open(self, u, timeout=None):
        self.calls.append(u)
        self.timeouts.append(timeout)
        self.t += self.cost
        if u in self.fail:
            raise self.fail[u]
        ch = urllib.parse.urlsplit(u).path.rsplit("/", 1)[-1]
        return Resp(self.pages.get(u, F.render_page(ch, only=[])).encode("utf-8"), self.final.get(u, u))

    def sleep(self, s):
        self.naps.append(s)
        self.t += s

    def clock(self):
        return self.t

    def firsts(self):
        return [u for u in self.calls if "before=" not in u]


class Canned(urllib.request.BaseHandler):
    """https 요청에 정해 둔 응답(상태, 머리말, 본문)을 돌려주는 urllib 처리기 — 진짜 처리기보다 먼저 불려 소켓을 열지 않는다."""
    handler_order = 50

    def __init__(self, table):
        self.table, self.seen, self.headers = table, [], []

    def https_open(self, req):
        self.seen.append(req.full_url)
        self.headers.append({k.lower(): v for k, v in req.header_items()})
        code, head, data = self.table[req.full_url]
        resp = urllib.response.addinfourl(io.BytesIO(data), email.message_from_string(head), req.full_url, code)
        resp.msg = "x"
        return resp


def no_net(*a, **kw):
    raise AssertionError("네트워크를 부르면 안 된다")


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.work = os.path.join(self.tmp, "work")

    def put(self, name, doc):
        S.write_json(os.path.join(self.tmp, name), doc)
        return os.path.join(self.tmp, name)

    def argv(self, state=..., now=F.NOW, replay=False):
        state = F.state() if state is ... else state
        argv = ["--sources", self.put("sources.json", F.sources()), "--work", self.work,
                "--state", self.put("state.json", state) if state else os.path.join(self.tmp, "no_state.json")]
        return argv + (["--now", now] if now else []) + (["--replay"] if replay else [])

    def collect(self, net=None, cli=False, **kw):
        """main을 가짜 네트워크로 돌린다 → 종료코드. cli면 run_cli로 감싼다(스크립트로 돌 때와 같게)."""
        self.net = Net() if net is None else net
        out, err = io.StringIO(), io.StringIO()
        go = lambda argv: T.main(argv, opener=self.net.open, sleep=self.net.sleep, clock=self.net.clock)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = S.run_cli("tg_collect", go, self.argv(**kw)) if cli else go(self.argv(**kw))
        self.out, self.err = out.getvalue(), err.getvalue()
        return code

    def doc(self, name):
        return S.validator_for(name)(S.read_json(os.path.join(self.work, name)))

    def rows(self):
        return {c["ch"]: c for c in self.doc("collect_status.json")["channels"]}

    def written(self):
        return sorted(os.listdir(self.work)) if os.path.isdir(self.work) else []


# ---------- 미리보기 쪽 → 글 ----------

class ParseTest(unittest.TestCase):
    def test_fixture_pages_read_back_as_the_posts(self):
        for ch in F.REQUESTED:
            want = sorted((p for p in F.all_posts() if p["ch"] == ch), key=lambda p: p["id"])
            got = T.parse_page(F.render_page(ch), ch, "search" if ch in WIRE else "page")
            self.assertEqual(got, want, ch)
            for p in got:
                S.validate_post(p)

    def test_body_is_text_only(self):
        self.assertEqual(one(body("A &amp; B &lt;c&gt;<br/>둘째 줄<br/><br/>  셋째   줄  "))["text"], "A & B <c>\n둘째 줄\n셋째 줄")
        self.assertEqual(one(body('<mark class="highlight">금리</mark>가 올랐다는 <b>지어낸</b> 글'))["text"], "금리가 올랐다는 지어낸 글")
        self.assertEqual(one(body('좋다 <i class="emoji" style="background-image:url(\'//x/y.png\')"><b>🙂</b></i> 끝'))["text"], "좋다 🙂 끝")
        self.assertEqual(one(body(body("안쪽 글자") + " 바깥 글자"))["text"], "안쪽 글자\n바깥 글자")         # 본문 칸이 겹쳐 있는 글
        quoted = body("앞 문장<blockquote>인용한 줄</blockquote>뒤 문장<pre>표 한 줄\n표 두 줄</pre>끝")
        self.assertEqual(one(quoted)["text"], "앞 문장\n인용한 줄\n뒤 문장\n표 한 줄\n표 두 줄\n끝")        # 덩어리 사이는 줄을 가른다

    def test_links_come_from_the_body_and_bare_addresses_leave_the_text(self):
        p = one(body('해시태그 <a href="?q=%23tag">#채권</a> 그리고 <a href="https://news.example.com/a?x=1" target="_blank">기사 보기</a>'
                     '<br/><a href="http://sho.example/q1">sho.example/q1</a> <a href="https://t.me/fxbond2">@fxbond2</a>'
                     '<br/><a href="https://news.example.com/a?x=1">https://news.example.com/a?x=1</a>'
                     '<a href="tg://resolve?domain=x">앱 링크</a>'))
        self.assertEqual(p["text"], "해시태그 #채권 그리고 기사 보기\n@fxbond2\n앱 링크")
        self.assertEqual(p["links"], ["https://news.example.com/a?x=1", "http://sho.example/q1", "https://t.me/fxbond2"])

    def test_reply_preview_is_not_the_body(self):
        reply = ('<a class="tgme_widget_message_reply" href="https://t.me/fxbond1/3">'
                 '<div class="tgme_widget_message_author accent_color"><span class="tgme_widget_message_author_name">누군가</span></div>'
                 '<div class="tgme_widget_message_text js-message_reply_text" dir="auto">답글 미리보기 글자</div></a>')
        p = one(reply + body("답글의 본문입니다"))
        self.assertEqual((p["text"], p["reply"], p["links"]), ("답글의 본문입니다", True, []))
        self.assertFalse(one(body("보통 글"))["reply"])

    def test_forwarded_origin(self):
        head = '<div class="tgme_widget_message_forwarded_from accent_color">Forwarded from&nbsp;{}</div>'
        named = '<a class="tgme_widget_message_forwarded_from_name" href="{}"><span dir="auto">전달 원글 채널</span></a>'
        fwd = lambda inner: one(head.format(inner) + body("전달한 글"))["fwd"]
        self.assertEqual(fwd(named.format("https://t.me/fxanal2/77")), {"ch": "fxanal2", "id": 77})
        self.assertEqual(fwd(named.format("https://t.me/fxanal2/77?single")), {"ch": "fxanal2", "id": 77})
        # 주소가 없는 전달(이름만) · 비공개 채널 · 글 번호가 없는 주소 — 전달이라는 것만 남기고 원글 이름은 남기지 않는다
        self.assertEqual(fwd('<span class="tgme_widget_message_forwarded_from_name"><span dir="auto">누군가</span></span>'),
                         {"ch": None, "id": None})
        for odd in ("https://t.me/c/1234567/89", "https://t.me/fxanal2", "https://example.org/fxanal2/77", ""):
            self.assertEqual(fwd(named.format(odd)), {"ch": None, "id": None}, odd)
        self.assertIsNone(one(body("전달이 아닌 글"))["fwd"])
        self.assertNotIn("누군가", S.dump(T.parse_page(page_of("fxbond1", msg("fxbond1", 7, head.format("누군가") + body("글"))), "fxbond1")))

    def test_link_card(self):
        card = ('<a class="tgme_widget_message_link_preview" href="https://sho.example/x1"><i class="link_preview_image"></i>'
                '<div class="link_preview_site_name accent_color" dir="auto">지어낸신문</div>'
                '<div class="link_preview_title" dir="auto">지어낸  카드 &quot;제목&quot;</div>'
                '<div class="link_preview_description" dir="auto">지어낸 카드 설명</div></a>')
        p = one(body("카드가 붙은 글") + card)
        self.assertEqual(p["card"], {"title": '지어낸 카드 "제목"', "site": "지어낸신문", "url": "https://sho.example/x1"})
        self.assertEqual((p["text"], p["links"]), ("카드가 붙은 글", []))                         # 카드의 글자·주소는 본문·links에 섞이지 않는다
        bare = '<a class="tgme_widget_message_link_preview" href="https://sho.example/x1"><i class="link_preview_image"></i></a>'
        self.assertIsNone(one(body("제목 없는 카드") + bare)["card"])

    def test_media_only_posts(self):
        photo = ('<a class="tgme_widget_message_photo_wrap" href="https://t.me/fxbond1/7">'
                 '<div class="tgme_widget_message_photo"></div></a>')
        video = ('<a class="tgme_widget_message_video_player js-message_video_player" href="https://t.me/fxbond1/7">'
                 '<time class="message_video_duration js-message_video_duration">0:12</time></a>')
        self.assertEqual((one(photo)["text"], one(photo)["media"]), ("", True))
        self.assertTrue(one(video)["media"])
        unsupported = '<div class="message_media_not_supported_wrap"><div class="message_media_not_supported"></div></div>'
        self.assertTrue(one(unsupported)["media"])
        self.assertFalse(one(photo + body("사진에 붙인 글"))["media"])                           # 본문이 있으면 '사진만'이 아니다
        self.assertEqual((one("")["text"], one("")["media"]), ("", False))
        self.assertEqual(one(video + body("영상에 붙인 글"))["at"], "2026-10-08T10:00:00+09:00")    # 영상 길이는 올린 시각이 아니다

    def test_time_is_kst_or_none(self):
        self.assertEqual(one(body("글"), when="2026-10-07T23:59:59+00:00")["at"], "2026-10-08T08:59:59+09:00")
        for bad in ("2026-10-07T23:59:59", "어제", "", None, "9999-12-31T23:59:59+00:00"):
            self.assertIsNone(one(body("글"), when=bad)["at"], bad)

    def test_only_this_channels_ordinary_posts(self):
        page = page_of("fxbond1", msg("fxbond2", 5, body("다른 채널의 글")), msg("fxbond1", "12x", body("번호가 이상한 글")),
                       msg("fxbond1", 9, body("알림: 글을 고정했습니다"), cls=MSG + " service_message"),
                       msg("FXBOND1", 8, body("둘째")), msg("fxbond1", 6, body("첫째")), msg("fxbond1", 8, body("겹친 번호")))
        got = T.parse_page(page, "fxbond1")
        self.assertEqual([(p["ch"], p["id"], p["text"]) for p in got], [("fxbond1", 6, "첫째"), ("fxbond1", 8, "둘째")])

    def test_broken_markup_does_not_merge_posts(self):
        open_div = msg("fxbond1", 3, body("닫히지 않은 글") + "<div><div>")                       # 태그가 어긋난 글
        got = T.parse_page(page_of("fxbond1", open_div, msg("fxbond1", 4, body("다음 글"))), "fxbond1")
        self.assertEqual([(p["id"], p["text"]) for p in got], [(3, "닫히지 않은 글"), (4, "다음 글")])
        self.assertEqual(T.parse_page("", "fxbond1"), [])
        self.assertEqual(T.parse_page("<html><body>미리보기가 아닌 쪽</body></html>", "fxbond1"), [])

    def test_limits_of_the_contract(self):
        long = one(body("가" * 25_000))
        self.assertEqual(len(long["text"]), S.MAX_TEXT)
        many = one(body("".join(f'<a href="https://l.example/{i}">링크</a>' for i in range(60))
                        + f'<a href="https://l.example/{"x" * 3000}">긴 주소</a>'))
        self.assertEqual(len(many["links"]), 50)
        S.validate_post(long)
        S.validate_post(many)


# ---------- 수신 ----------

class FetchTest(unittest.TestCase):
    def test_addresses_are_built_from_the_handle_only(self):
        self.assertEqual(T.page_url("fxbond1"), "https://t.me/s/fxbond1")
        self.assertEqual(T.page_url("fxwire1", "search"), "https://t.me/s/fxwire1?q=%EA%B8%88%EB%A6%AC")
        self.assertEqual(T.page_url("fxbond1", "more", 501), "https://t.me/s/fxbond1?before=501")
        for bad in ("fx/../x", "a b", "", "https://evil.example", "fxbond1?q=x"):
            with self.assertRaises(ValueError):
                T.page_url(bad)

    def test_default_headers_only(self):
        # User-Agent를 붙이지 않는다 — urllib이 스스로 넣는 머리말뿐이다
        self.assertEqual(T._OPENER.addheaders, urllib.request.build_opener().addheaders)
        self.assertTrue(any(isinstance(h, T._SameHost) for h in T._OPENER.handlers))
        net = Net()
        self.assertIn("EVE-TAG-5T1", T.fetch(url("fxbond5"), "fxbond5", net.open, net.clock))
        self.assertEqual((net.calls, net.timeouts), ([url("fxbond5")], [TH["timeout_s"]]))          # 주소 글자만 넘긴다(머리말 없음)

    def test_final_address_must_be_the_preview(self):
        for final in ("https://t.me/fxbond1", "https://example.org/s/fxbond1", "http://t.me/s/fxbond1", "https://t.me/s/fxbond2",
                      "https://t.me.example.org/s/fxbond1"):
            net = Net(final={url("fxbond1"): final})
            with self.assertRaises(T.Fail) as e:
                T.fetch(url("fxbond1"), "fxbond1", net.open, net.clock)
            self.assertEqual(e.exception.code, "no_preview", final)
        net = Net(final={url("fxwire1"): url("fxwire1")})                                           # 검색 쪽은 물음표 뒤가 붙어도 된다
        self.assertTrue(T.fetch(url("fxwire1"), "fxwire1", net.open, net.clock))

    def test_redirects_off_the_host_are_not_followed(self):
        h, req = T._SameHost(), urllib.request.Request(url("fxbond1"))
        for away in ("https://example.org/s/fxbond1", "http://t.me/s/fxbond1", "https://t.me.example.org/x", "ftp://t.me/x"):
            with self.assertRaises(T.Fail) as e:
                h.redirect_request(req, io.BytesIO(), 302, "Found", {}, away)
            self.assertEqual(e.exception.code, "no_preview", away)
        stay = h.redirect_request(req, io.BytesIO(), 302, "Found", {}, "https://t.me/fxbond1")
        self.assertEqual(stay.full_url, "https://t.me/fxbond1")                                     # 같은 호스트는 따라가서 끝 주소로 판단한다

    def test_redirect_is_refused_before_any_request_leaves_the_host(self):
        # urllib의 실제 리다이렉트 처리에 끼워 본다 — 정해 둔 응답만 돌려주는 대역이라 소켓은 열리지 않는다
        wired = lambda canned: urllib.request.build_opener(urllib.request.ProxyHandler({}), T._SameHost(), canned).open
        away = Canned({url("fxbond1"): (302, "Location: https://example.org/s/fxbond1\n\n", b"")})
        with self.assertRaises(T.Fail) as e:
            T.fetch(url("fxbond1"), "fxbond1", wired(away))
        self.assertEqual((e.exception.code, away.seen), ("no_preview", [url("fxbond1")]))            # 다른 호스트에는 요청이 가지 않았다
        off = Canned({url("fxbond1"): (302, "Location: https://t.me/fxbond1\n\n", b""), "https://t.me/fxbond1": (200, "\n", b"<html>")})
        with self.assertRaises(T.Fail) as e:                                                         # 미리보기가 꺼진 채널
            T.fetch(url("fxbond1"), "fxbond1", wired(off))
        self.assertEqual((e.exception.code, off.seen), ("no_preview", [url("fxbond1"), "https://t.me/fxbond1"]))
        fine = Canned({url("fxbond1"): (200, "\n", F.render_page("fxbond1").encode("utf-8"))})
        page = T.fetch(url("fxbond1"), "fxbond1", wired(fine))
        self.assertEqual([p["id"] for p in T.parse_page(page, "fxbond1")], [501, 502])
        self.assertEqual(sorted(fine.headers[0]), ["host", "user-agent"])                            # 보낸 머리말은 urllib이 스스로 넣는 둘뿐
        self.assertEqual((fine.headers[0]["host"], fine.headers[0]["user-agent"][:14]), ("t.me", "Python-urllib/"))

    def test_size_and_time_limits(self):
        big = Net({url("fxbond1"): "가" * (TH["max_bytes"] // 3 + 10)})
        with self.assertRaises(T.Fail) as e:
            T.fetch(url("fxbond1"), "fxbond1", big.open, big.clock)
        self.assertEqual(e.exception.code, "fetch")
        slow = Net(cost=TH["page_budget_s"] + 1)
        with self.assertRaises(T.Fail):
            T.fetch(url("fxbond1"), "fxbond1", slow.open, slow.clock)
        tight = Net(cost=1.0)                                                                       # 남은 전체 시간이 짧으면 그만큼만
        self.assertTrue(T.fetch(url("fxbond1"), "fxbond1", tight.open, tight.clock, left=7.5))
        self.assertEqual(tight.timeouts, [7.5])

    def test_limits_grow_with_a_long_window(self):
        short = {"from": "2026-10-07T18:00:00+09:00", "to": "2026-10-09T18:00:00+09:00"}             # 꼭 48시간
        long = {"from": "2026-10-09T17:41:00+09:00", "to": "2026-10-12T21:45:00+09:00"}              # 금 저녁 → 월 밤
        self.assertEqual(T.limits(short), (TH["max_requests"], TH["budget_s"]))
        self.assertEqual(T.limits(long), (40, 480))
        self.assertEqual((TH["long_window_h"], TH["max_requests_long"], TH["budget_long_s"]), (48, 40, 480))   # 숫자는 규칙 표(TH)에 있다


# ---------- 수집 ----------

class CollectTest(Case):
    def test_reads_every_listed_channel_once_in_order(self):
        self.assertEqual(self.collect(), 0)
        self.assertEqual(self.net.firsts(), [url(ch) for ch in ORDER])                             # 채권 → 애널 → 개인 → 속보형
        self.assertFalse(any("fxoff1" in u for u in self.net.calls))                               # off는 요청하지 않는다
        self.assertEqual(self.net.naps, [TH["pause_s"]] * (len(self.net.calls) - 1))               # 요청 사이 3초
        self.assertLessEqual(len(self.net.calls), TH["max_requests"])
        self.assertTrue(all(u.startswith(BASE) for u in self.net.calls))
        st = self.doc("collect_status.json")
        self.assertEqual([c["ch"] for c in st["channels"]], list(ORDER))
        self.assertEqual((st["verdict"], st["window_kind"], st["capped"], st["replay"]), ("ok", "next", False, False))
        self.assertEqual((st["requests"], st["elapsed_s"]), (len(self.net.calls), self.net.t))
        self.assertEqual(st["collected_at"], S.iso(S.parse_iso(F.NOW) + T.datetime.timedelta(seconds=self.net.t)))
        self.assertIn(url("fxbond1", 501), self.net.calls)                                          # 한 쪽 더 받았는데 더 옛 글이 없다
        self.assertIn(line("fxbond1", "ok", 2, 2, 2, 2, 2), self.out)

    def test_real_list_is_asked_in_group_order(self):
        src = S.validate_sources(S.read_json(os.path.join(S.DATA, "sources.json")))
        got = [(c["group"], c["role"]) for c in T.ordered(src)]
        rank = [3 if role == "wire" else list(S.R.GROUPS).index(group) for group, role in got]
        self.assertEqual(rank, sorted(rank))                                                        # 채권 → 애널 → 개인 → 속보형
        self.assertEqual((rank[0], rank[-1], len(got)), (0, 3, len(S.handles_of(src))))
        self.assertNotIn("off", [role for _, role in got])
        self.assertLessEqual(len(got), TH["max_requests"])                                          # 채널마다 첫 쪽은 받을 수 있다

    def test_posts_are_cut_to_the_window(self):
        self.collect()
        d = self.doc("posts.json")
        self.assertEqual(d["posts"], F.posts())                                                     # 창 밖의 두 글은 빠진다
        self.assertEqual((d["edition"], d["window"]), (F.EDITION, F.WINDOW))
        rows = self.rows()
        for ch in F.REQUESTED:
            mine = [p for p in F.all_posts() if p["ch"] == ch]
            last = max(mine, key=lambda p: p["id"])
            want = {"ok": True, "code": "ok", "posts": len(mine), "with_text": sum(bool(p["text"]) for p in mine),
                    "in_window": sum(p["at"] > F.WINDOW["from"] for p in mine), "last_post": last["id"], "last_at": last["at"],
                    "title_sha": S.title_sha(F.TITLE[ch]), "fail_streak": 0, "group": F.GROUP[ch], "role": F.ROLE[ch]}
            self.assertEqual({k: rows[ch][k] for k in want}, want, ch)
        self.assertEqual((rows["fxbond4"]["posts"], rows["fxbond4"]["in_window"]), (2, 1))

    def test_edge_of_the_window(self):
        at = lambda s: f"2026-10-0{s}:00+09:00"
        edge = [post("fxbond1", 601, at("7T18:02")), post("fxbond1", 602, at("7T18:03")), post("fxbond1", 603, at("8T18:07")),
                post("fxbond1", 604, at("8T18:08"))]                                               # from < at ≤ to
        self.collect(Net(site(**{url("fxbond1"): F.render_page("fxbond1", only=edge)})))
        self.assertEqual([p["id"] for p in self.doc("posts.json")["posts"] if p["ch"] == "fxbond1"], [602, 603])
        self.assertEqual((self.rows()["fxbond1"]["posts"], self.rows()["fxbond1"]["in_window"]), (4, 2))

    def test_first_run_takes_a_day(self):
        self.assertEqual(self.collect(state=None), 0)
        st = self.doc("collect_status.json")
        self.assertEqual((st["window_kind"], st["window"]["from"]), ("first", "2026-10-07T18:07:00+09:00"))
        self.assertEqual(self.doc("posts.json")["posts"], F.posts())

    def test_same_edition_again_starts_from_the_same_point(self):
        st = copy.deepcopy(F.state_after())
        st["edition"]["channels"]["fxbond1"]["fail_streak"] = 5                                     # 이 판의 첫 실행이 남긴 기록
        st["base"]["channels"]["fxbond1"] = {"last_post": 400, "last_at": "2026-10-07T10:00:00+09:00", "fail_streak": 1}
        net = Net(fail={url("fxbond1"): urllib.error.URLError("x")})
        self.assertEqual(self.collect(net, state=st, now="2026-10-08T21:00:00+09:00"), 0)
        doc = self.doc("collect_status.json")
        self.assertEqual((doc["window_kind"], doc["window"]["from"], doc["edition"]), ("rerun", F.WINDOW["from"], F.EDITION))
        row = self.rows()["fxbond1"]                                                               # 연속 실패·마지막 글은 직전 판(base)에서 센다
        self.assertEqual((row["fail_streak"], row["last_post"], row["last_at"]), (2, 400, "2026-10-07T10:00:00+09:00"))

    def test_one_more_page_when_the_last_post_is_not_reached(self):
        seen = "2026-10-07T18:00:00+09:00"                                                          # 직전 판의 마지막 글 480
        new, old = run_of("fxbond1", 490, 20), run_of("fxbond1", 470, 20, "2026-10-07T17:50:00+09:00")
        pages = site(**{url("fxbond1"): F.render_page("fxbond1", only=new), url("fxbond1", 490): F.render_page("fxbond1", only=old)})
        self.collect(Net(pages), state=state_with(fxbond1={"last_post": 480, "last_at": seen}))
        self.assertEqual(self.net.calls[:3], [url("fxbond1"), url("fxbond1", 490), url("fxbond2")])  # 가장 작은 글 번호로 한 쪽 더
        row = self.rows()["fxbond1"]
        self.assertEqual((row["pages"], row["posts"], row["in_window"], row["last_post"]), (2, 40, 27, 509))
        self.assertIn(line("fxbond1", "ok", 2, 40, 40, 40, 27), self.out)
        self.assertEqual(len([u for u in self.net.calls if u.startswith(url("fxbond1"))]), 2)        # 두 쪽까지만

    def test_no_more_page_when_reached_and_cut_when_two_pages_are_not_enough(self):
        new = run_of("fxbond1", 490, 20)
        pages = site(**{url("fxbond1"): F.render_page("fxbond1", only=new)})
        self.collect(Net(pages), state=state_with(fxbond1={"last_post": 495, "last_at": new[5]["at"]}))
        self.assertNotIn(url("fxbond1", 490), self.net.calls)                                       # 직전 판의 마지막 글이 쪽에 있다
        self.assertIn(line("fxbond1", "ok", 1, 20, 20, 20, 20), self.out)
        pages[url("fxbond1", 490)] = F.render_page("fxbond1", only=run_of("fxbond1", 470, 20, "2026-10-08T08:00:00+09:00"))
        self.collect(Net(pages), state=state_with(fxbond1={"last_post": 300, "last_at": "2026-10-07T10:00:00+09:00"}))
        self.assertIn(line("fxbond1", "ok", 2, 40, 40, 40, 40, cut=1), self.out)
        self.assertRegex(self.out, r"\[tg_collect\] edition=2026-10-08 .* cut=\d+ ")

    def test_a_failed_second_page_keeps_the_first(self):
        pages = site(**{url("fxbond1"): F.render_page("fxbond1", only=run_of("fxbond1", 490, 20))})
        far_back = state_with(fxbond1={"last_post": 300, "last_at": "2026-10-06T10:00:00+09:00"})     # 첫 쪽으로는 닿지 못한다
        self.collect(Net(pages, fail={url("fxbond1", 490): TimeoutError()}), state=far_back)
        row = self.rows()["fxbond1"]
        self.assertEqual((row["ok"], row["pages"], row["posts"]), (True, 1, 20))
        self.assertIn(line("fxbond1", "ok", 1, 20, 20, 20, 20, cut=1), self.out)
        pages = [(p["ch"], p["n"], p["kind"], p["ok"], p["code"]) for p in self.doc("pages/manifest.json")["pages"]]
        self.assertEqual(pages[:2], [("fxbond1", 1, "page", True, "ok"), ("fxbond1", 2, "more", False, "fetch")])

    def test_wire_channels_are_searched(self):
        self.collect()
        for ch in WIRE:
            self.assertIn(url(ch, search=True), self.net.calls)
            self.assertNotIn(url(ch, search=False), self.net.calls)                                 # 검색이 되면 최근 쪽은 받지 않는다
            self.assertFalse(any(u.startswith(f"{BASE}{ch}?before=") for u in self.net.calls))      # 속보형은 한 쪽씩만
        self.assertEqual({p["via"] for p in self.doc("posts.json")["posts"] if p["ch"] in WIRE}, {"search"})
        kinds = {p["ch"]: p["kind"] for p in self.doc("pages/manifest.json")["pages"] if p["n"] == 1}
        self.assertEqual({k for ch, k in kinds.items() if ch in WIRE}, {"search"})
        self.assertEqual({k for ch, k in kinds.items() if ch not in WIRE}, {"page"})

    def test_wire_falls_back_to_the_recent_page(self):
        recent = {url(ch, search=False): F.render_page(ch) for ch in WIRE}
        empty = Net(site(**recent, **{url("fxwire1"): F.render_page("fxwire1", only=[])}),          # 검색 결과가 비었거나 수신 실패
                    fail={url("fxwire2"): urllib.error.HTTPError(url("fxwire2"), 500, "x", {}, None)})
        with mock.patch.dict(TH, {"max_requests": 60}):
            self.assertEqual(self.collect(empty), 0)
        self.assertEqual(self.net.calls[-4:],
                         [url("fxwire1"), url("fxwire1", search=False), url("fxwire2"), url("fxwire2", search=False)])
        self.assertEqual(self.doc("posts.json")["posts"], [{**p, "via": "page"} if p["ch"] in WIRE else p for p in F.posts()])
        rows = self.rows()
        self.assertEqual([(rows[ch]["ok"], rows[ch]["pages"]) for ch in WIRE], [(True, 2), (True, 1)])
        tail = [(p["ch"], p["n"], p["kind"], p["code"]) for p in self.doc("pages/manifest.json")["pages"][-4:]]
        self.assertEqual(tail, [("fxwire1", 1, "search", "ok"), ("fxwire1", 2, "page", "ok"), ("fxwire2", 1, "search", "fetch"),
                                ("fxwire2", 2, "page", "ok")])

    def test_wire_fallback_leaves_the_next_channels_request(self):
        far = {ch: {"last_post": 999_999_999, "last_at": F.NOW} for ch in ORDER}                    # 모두 닿은 것으로 — '한 쪽 더' 없음
        pages = site(**{url("fxwire1"): F.render_page("fxwire1", only=[]), url("fxwire1", search=False): F.render_page("fxwire1")})
        with mock.patch.dict(TH, {"max_requests": 24}):
            self.assertEqual(self.collect(Net(pages), state=state_with(**far)), 0)
        self.assertEqual(self.net.calls, [url(ch) for ch in ORDER])                                 # 남은 한 번은 fxwire2의 첫 쪽 몫
        self.assertEqual([self.rows()[ch]["code"] for ch in WIRE], ["empty", "ok"])
        with mock.patch.dict(TH, {"max_requests": 25}):
            self.collect(Net(pages), state=state_with(**far))
        self.assertEqual(self.net.calls[-3:], [url("fxwire1"), url("fxwire1", search=False), url("fxwire2")])
        self.assertEqual([self.rows()[ch]["code"] for ch in WIRE], ["ok", "ok"])

    def test_request_budget(self):
        with mock.patch.dict(TH, {"max_requests": 10}):
            self.assertEqual(self.collect(), 0)
        self.assertEqual(self.net.calls, [url(ch) for ch in ORDER[:10]])                            # 남은 채널 몫이 없으면 '한 쪽 더'도 없다
        rows = self.rows()
        self.assertEqual([rows[ch]["code"] for ch in ORDER], ["ok"] * 10 + ["budget"] * 14)
        self.assertTrue(all(not rows[ch]["ok"] and rows[ch]["posts"] == 0 and rows[ch]["fail_streak"] == 1 for ch in ORDER[10:]))
        self.assertEqual(self.doc("collect_status.json")["verdict"], "short")
        self.assertEqual({p["ch"] for p in self.doc("posts.json")["posts"]}, set(ORDER[:10]))
        with mock.patch.dict(TH, {"max_requests": 26}):                                             # 24채널의 첫 쪽 + 남는 둘만 '한 쪽 더'
            self.collect()
        self.assertEqual((self.net.firsts(), len(self.net.calls)), ([url(ch) for ch in ORDER], 26))
        self.assertEqual(self.net.calls[:4], [url("fxbond1"), url("fxbond1", 501), url("fxbond2"), url("fxbond2", 212)])
        self.assertEqual(self.doc("posts.json")["posts"], F.posts())

    def test_time_budget(self):
        self.assertEqual(self.collect(Net(cost=30.0)), 0)
        asked = [ch for ch in ORDER if url(ch) in self.net.calls]
        self.assertTrue(0 < len(asked) < len(ORDER))
        self.assertEqual(asked, list(ORDER[:len(asked)]))
        rows = self.rows()
        self.assertEqual({rows[ch]["code"] for ch in ORDER[len(asked):]}, {"budget"})
        self.assertLess(self.net.t, TH["budget_s"] + TH["page_budget_s"])                           # 상한을 넘겨 한 쪽 넘게 더 쓰지 않는다
        self.assertEqual(len(self.doc("pages/manifest.json")["pages"]), len(self.net.calls) + len(ORDER) - len(asked))

    def test_network_failures_close_the_channel_not_the_run(self):
        fails = {url("fxbond1"): urllib.error.URLError("x"), url("fxbond2"): TimeoutError(),
                 url("fxanal1"): urllib.error.HTTPError(url("fxanal1"), 404, "x", {}, None),
                 url("fxanal2"): http.client.IncompleteRead(b""), url("fxpers1"): ConnectionResetError()}
        final = {url("fxbond3"): "https://example.org/s/fxbond3", url("fxpers2"): "https://t.me/fxpers2"}
        self.assertEqual(self.collect(Net(fail=fails, final=final), state=state_with(fxbond1={"last_post": 100, "last_at": None,
                                                                                             "fail_streak": 3})), 0)
        rows = self.rows()
        self.assertEqual({ch: rows[ch]["code"] for ch in rows if not rows[ch]["ok"]},
                         {"fxbond1": "fetch", "fxbond2": "fetch", "fxanal1": "fetch", "fxanal2": "fetch", "fxpers1": "fetch",
                          "fxbond3": "no_preview", "fxpers2": "no_preview"})
        self.assertEqual((rows["fxbond1"]["fail_streak"], rows["fxbond2"]["fail_streak"]), (4, 1))
        self.assertEqual((rows["fxbond1"]["pages"], rows["fxbond1"]["title_sha"]), (0, None))
        self.assertEqual(self.doc("collect_status.json")["verdict"], "short")                       # 채권 2곳만 읽힘
        lost = {"fxbond1", "fxbond2", "fxbond3", "fxanal1", "fxanal2", "fxpers1", "fxpers2"}
        self.assertEqual(self.doc("posts.json")["posts"], [p for p in F.posts() if p["ch"] not in lost])
        self.assertFalse(os.path.exists(os.path.join(self.work, "pages", "fxbond1-1.html")))

    def test_changed_format_is_unread_not_quiet(self):
        gone = F.render_page("fxbond1").replace('class="tgme_widget_message ', 'class="tgme_widget_msg ')
        clockless = F.render_page("fxbond2").replace("<time datetime=", "<time data-when=")
        self.collect(Net(site(**{url("fxbond1"): gone, url("fxbond2"): clockless})))
        rows = self.rows()
        self.assertEqual([(rows[ch]["ok"], rows[ch]["code"], rows[ch]["posts"]) for ch in ("fxbond1", "fxbond2")],
                         [(False, "empty", 0)] * 2)                                                # 글 0개 · 시각 0개 = 읽지 못함
        self.assertEqual((rows["fxbond1"]["last_post"], rows["fxbond1"]["fail_streak"]), (500, 1))  # 직전 판의 마지막 글을 그대로 둔다
        self.assertEqual({p["ch"] for p in self.doc("posts.json")["posts"]} & {"fxbond1", "fxbond2"}, set())

    def test_posts_without_a_time_are_counted_but_not_used(self):
        half = F.render_page("fxbond1").replace("<time datetime=", "<time data-when=", 1)             # 501만 시각이 없다
        self.assertEqual(self.collect(Net(site(**{url("fxbond1"): half}))), 0)
        row = self.rows()["fxbond1"]
        self.assertEqual((row["ok"], row["posts"], row["with_text"], row["in_window"], row["last_post"]), (True, 2, 2, 1, 502))
        self.assertEqual([p["id"] for p in self.doc("posts.json")["posts"] if p["ch"] == "fxbond1"], [502])
        self.assertRegex(self.out, r"fxbond1 code=ok pages=\d posts=2 with_text=2 with_time=1 in_window=1 ")
        self.assertRegex(self.out, r" posts=42 with_text=41 with_time=41 in_window=39 cut=\d+ verdict=ok\n$")

    def test_renamed_body_makes_the_verdict_broken(self):
        renamed = {u: p.replace("js-message_text", "js-message_body") for u, p in site().items()}
        self.assertEqual(self.collect(Net(renamed)), 0)
        st = self.doc("collect_status.json")
        self.assertEqual((st["verdict"], sum(c["ok"] for c in st["channels"]), sum(c["with_text"] for c in st["channels"])),
                         ("broken", 24, 0))
        self.assertIn(" verdict=broken", self.out)

    def test_unreadable_page_is_a_closed_code(self):
        with mock.patch.object(T, "parse_page", side_effect=ValueError(F.CANARIES[0])):
            self.assertEqual(self.collect(), 0)
        self.assertEqual({c["code"] for c in self.rows().values()}, {"empty"})
        self.assertEqual(F.leaks(self.out + self.err), [])

    def test_title_change_drops_the_channel(self):
        other = F.render_page("fxbond2").replace(html.escape(F.TITLE["fxbond2"]), "이름이 바뀐 채널")
        untitled = F.render_page("fxanal1").replace('property="og:title"', 'property="og:name"')
        self.assertEqual(self.collect(Net(site(**{url("fxbond2"): other, url("fxanal1"): untitled}))), 0)
        rows = self.rows()
        self.assertEqual((rows["fxbond2"]["ok"], rows["fxbond2"]["code"], rows["fxbond2"]["posts"]), (False, "title", 0))
        self.assertEqual(rows["fxbond2"]["title_sha"], S.title_sha("이름이 바뀐 채널"))                 # 목록을 고칠 때 볼 값(해시)
        self.assertEqual((rows["fxanal1"]["code"], rows["fxanal1"]["title_sha"], rows["fxanal1"]["last_post"]), ("title", None, 1400))
        self.assertEqual({p["ch"] for p in self.doc("posts.json")["posts"]} & {"fxbond2", "fxanal1"}, set())
        self.assertEqual(self.doc("collect_status.json")["verdict"], "ok")
        seen = f" title_sha={S.title_sha('이름이 바뀐 채널')}\n"                                    # 목록에 옮겨 적을 값을 로그에서 본다
        self.assertIn(line("fxbond2", "title", 1, 0, 0, 0, 0, streak=1).replace("\n", seen), self.out)
        self.assertIn(line("fxanal1", "title", 1, 0, 0, 0, 0, streak=1), self.out)                  # 제목을 못 읽은 쪽은 해시가 없다
        self.assertEqual(self.out.count("title_sha="), 1)                                           # 읽힌 채널의 줄에는 붙이지 않는다
        second = F.render_page("fxbond1", only=[]).replace(html.escape(F.TITLE["fxbond1"]), "둘째 쪽만 다른 제목")
        self.collect(Net(site(**{url("fxbond1", 501): second})))                                    # '한 쪽 더'의 제목이 달라도 뺀다
        row = self.rows()["fxbond1"]
        self.assertEqual((row["code"], row["pages"], row["posts"], row["title_sha"]), ("title", 2, 0, S.title_sha("둘째 쪽만 다른 제목")))

    def test_stored_last_post_must_keep_its_time(self):
        same = {"last_post": 501, "last_at": "2026-10-07T21:41:00+09:00"}
        self.collect(state=state_with(fxbond1=same))
        self.assertEqual(self.rows()["fxbond1"]["code"], "ok")
        moved = {"last_post": 501, "last_at": "2026-10-01T09:00:00+09:00", "fail_streak": 2}       # 같은 번호인데 시각이 다르다
        self.assertEqual(self.collect(state=state_with(fxbond1=moved)), 0)
        row = self.rows()["fxbond1"]
        self.assertEqual((row["ok"], row["code"], row["posts"], row["in_window"]), (False, "rewind", 0, 0))
        self.assertEqual((row["last_post"], row["last_at"], row["fail_streak"]), (501, moved["last_at"], 3))
        self.assertFalse(any(p["ch"] == "fxbond1" for p in self.doc("posts.json")["posts"]))

    def test_post_numbers_that_start_over_are_a_rewind(self):
        """채널 이름이 남에게 넘어가 글 번호가 처음부터 다시 시작한 경우 — 직전 판의 마지막 글보다 늦게 올린 글의 번호가 그 번호 이하다.
        (제목 해시는 공개된 제목을 베끼면 같아진다. 글 번호는 되돌아가지 않는다 — ktb_fetch.py와 같은 검사.)"""
        before = {"last_post": 9000, "last_at": "2026-10-07T12:00:00+09:00", "fail_streak": 0}      # 쪽에는 그 뒤에 올린 501 · 502번뿐
        self.assertEqual(self.collect(state=state_with(fxbond1=before)), 0)
        row = self.rows()["fxbond1"]
        self.assertEqual((row["ok"], row["code"], row["posts"], row["in_window"]), (False, "rewind", 0, 0))
        self.assertEqual((row["last_post"], row["last_at"], row["fail_streak"]), (9000, before["last_at"], 1))
        self.assertFalse(any(p["ch"] == "fxbond1" for p in self.doc("posts.json")["posts"]))
        quiet = {"last_post": 9000, "last_at": "2026-10-08T17:00:00+09:00"}                         # 마지막 글을 지웠을 뿐 새 글은 없다
        self.collect(state=state_with(fxbond1=quiet))
        self.assertEqual(self.rows()["fxbond1"]["code"], "ok")
        self.collect(state=None)                                                                    # 첫 실행에는 견줄 것이 없다
        self.assertEqual({c["code"] for c in self.rows().values()}, {"ok"})

    def test_bad_inputs_fail_without_writing(self):
        broken = copy.deepcopy(F.state())
        broken["edition"]["channels"]["fxbond1"]["last_post"] = F.CANARIES[0]
        for kw in ({"state": broken}, {"now": "어제 저녁"}, {"now": "2026-10-08T18:07:00"}):
            self.assertEqual(self.collect(cli=True, **kw), 1)
            self.assertEqual((self.net.calls, self.written(), self.out), ([], [], ""))
            self.assertEqual(self.err, "[tg_collect] 실패: ValueError\n")
        with mock.patch.object(T.S, "validate_posts_doc", side_effect=ValueError(F.CANARIES[2])):    # 다 받고 나서 검증에서 떨어져도
            self.assertEqual(self.collect(cli=True), 1)
        self.assertEqual((self.written(), self.err), ([], "[tg_collect] 실패: ValueError\n"))


# ---------- 저장분으로 다시 ----------

class ReplayTest(Case):
    def same(self, a, b):
        drop = lambda d: {k: v for k, v in d.items() if k not in ("replay", "collected_at", "elapsed_s")}
        self.assertEqual(drop(a), drop(b))

    def test_replay_gives_the_same_result_without_the_network(self):
        recent = {url("fxwire1", search=False): F.render_page("fxwire1")}
        net = Net(site(**recent, **{url("fxwire1"): F.render_page("fxwire1", only=[]),
                                    url("fxbond2"): F.render_page("fxbond2").replace(html.escape(F.TITLE["fxbond2"]), "다른 제목")}),
                  fail={url("fxanal3"): TimeoutError()}, final={url("fxpers2"): "https://t.me/fxpers2"})
        with mock.patch.dict(TH, {"max_requests": 60}):
            self.assertEqual(self.collect(net), 0)
            live = [self.doc("posts.json"), self.doc("collect_status.json"), self.out]
            pages = sorted(os.listdir(os.path.join(self.work, "pages")))
            os.remove(os.path.join(self.work, "posts.json"))
            os.remove(os.path.join(self.work, "collect_status.json"))
            dead = Net()
            dead.open = dead.sleep = no_net
            self.assertEqual(self.collect(dead, replay=True, now=None), 0)                          # --now가 없으면 manifest의 now
        again = [self.doc("posts.json"), self.doc("collect_status.json"), self.out]
        self.assertEqual(again[0]["posts"], live[0]["posts"])
        self.same(again[0], live[0])
        self.same(again[1], live[1])
        self.assertEqual((again[1]["replay"], again[1]["elapsed_s"], again[1]["collected_at"]), (True, 0.0, F.NOW))
        self.assertEqual({c["code"] for c in again[1]["channels"]}, {"ok", "title", "fetch", "no_preview"})
        self.assertEqual(again[2].splitlines()[:-1], live[2].splitlines()[:-1])                      # 채널 줄은 같고 요약 줄만 다르다
        self.assertEqual(sorted(os.listdir(os.path.join(self.work, "pages"))), pages)                # 저장분은 건드리지 않는다

    def test_replay_of_the_sample_pages(self):
        for name, page in F.pages().items():
            T._write_text(os.path.join(self.work, "pages", name), page)
        S.write_json(os.path.join(self.work, "pages", "manifest.json"), F.manifest())
        dead = Net()
        dead.open = dead.sleep = no_net
        self.assertEqual(self.collect(dead, replay=True, now=None), 0)
        self.assertEqual(self.doc("posts.json"), {**F.posts_doc(), "collected_at": F.NOW})
        st = self.doc("collect_status.json")
        self.assertEqual((st["verdict"], st["requests"], sum(c["ok"] for c in st["channels"])), ("ok", 24, 24))
        self.assertEqual(S.read_json(os.path.join(self.work, "pages", "manifest.json")), F.manifest())

    def test_missing_saved_pages_are_failures(self):
        self.collect()
        os.remove(os.path.join(self.work, "pages", "fxbond3-1.html"))
        m = S.read_json(os.path.join(self.work, "pages", "manifest.json"))
        m["pages"] = [p for p in m["pages"] if p["ch"] != "fxanal4"]
        S.write_json(os.path.join(self.work, "pages", "manifest.json"), m)
        self.assertEqual(self.collect(replay=True), 0)
        self.assertEqual({ch: r["code"] for ch, r in self.rows().items() if not r["ok"]}, {"fxbond3": "fetch", "fxanal4": "fetch"})
        self.assertEqual(self.net.calls, [])
        shutil.rmtree(os.path.join(self.work, "pages"))
        self.assertEqual(self.collect(cli=True, replay=True), 1)                                     # 저장분이 없으면 실패
        self.assertEqual(self.err, "[tg_collect] 실패: FileNotFoundError\n")


# ---------- 출력에 글자가 새지 않는다 ----------

class OutputTest(Case):
    LINE = (r"\[tg_collect\] (\w+) code=(\w+) pages=\d posts=\d+ with_text=\d+ with_time=\d+ in_window=\d+ fail_streak=\d+ cut=[01]"
            r"(?: title_sha=[0-9a-f]{16})?")                         # 제목이 바뀐 채널의 줄에만 쪽에서 본 해시가 붙는다
    SUM = (r"\[tg_collect\] edition=\d{4}-\d\d-\d\d window_kind=\w+ capped=\w+ replay=\w+ requests=\d+ elapsed_s=[\d.]+ channels_ok=\d+ "
           r"channels_total=\d+ bond_ok=\d+ posts=\d+ with_text=\d+ with_time=\d+ in_window=\d+ cut=\d+ verdict=\w+")

    def test_log_has_counts_codes_and_listed_handles_only(self):
        other = F.render_page("fxbond2").replace(html.escape(F.TITLE["fxbond2"]), F.CANARIES[1])
        self.assertEqual(self.collect(Net(site(**{url("fxbond2"): other}), fail={url("fxanal1"): OSError(F.CANARIES[0])}), cli=True), 0)
        lines = self.out.splitlines()
        self.assertEqual((len(lines), self.err), (25, ""))
        for line in lines[:-1]:
            m = T.re.fullmatch(self.LINE, line)
            self.assertTrue(m, len(line))
            self.assertIn(m.group(1), F.REQUESTED)
            self.assertIn(m.group(2), S.CH_CODES)
        self.assertRegex(lines[-1], f"^{self.SUM}$")
        self.assertEqual(F.leaks(self.out), [])
        with open(os.path.join(self.work, "posts.json"), encoding="utf-8") as f:
            self.assertGreaterEqual(len(F.leaks(f.read())), 6)                                      # 원문은 <work> 안에만 있다
        with open(os.path.join(self.work, "collect_status.json"), encoding="utf-8") as f:
            self.assertEqual(F.leaks(f.read()), [])                                                 # 상태 파일에는 숫자·코드·해시만

    def test_exception_prints_only_its_type(self):
        odd = UnicodeDecodeError("utf-8", F.CANARIES[1].encode(), 0, 1, "x")
        for boom in (RuntimeError(F.CANARIES[0]), KeyError(F.CANARIES[2]), odd):
            with mock.patch.object(T, "read_channel", side_effect=boom):
                self.assertEqual(self.collect(cli=True), 1)
            self.assertEqual((self.out, self.err), ("", f"[tg_collect] 실패: {type(boom).__name__}\n"))
            self.assertEqual(self.written(), [])                                                    # 아무것도 쓰지 않는다

    def test_as_a_script(self):
        self.collect()
        argv = [sys.executable, "-X", "utf8", os.path.join(HERE, "tg_collect.py")] + self.argv(replay=True)
        done = subprocess.run(argv, capture_output=True, timeout=120, cwd=self.tmp)
        out, err = done.stdout.decode("utf-8"), done.stderr.decode("utf-8")
        self.assertEqual((done.returncode, err, len(out.splitlines())), (0, "", 25))
        self.assertEqual(F.leaks(out), [])
        self.assertEqual(self.doc("posts.json")["posts"], F.posts())
        with open(os.path.join(self.work, "pages", "manifest.json"), "w", encoding="utf-8") as f:
            f.write('{"schema": 1, "now": "' + F.CANARIES[0] + '", "pages": [{"' + F.CANARIES[3] + '"')   # 깨진 저장분
        done = subprocess.run(argv, capture_output=True, timeout=120, cwd=self.tmp)
        self.assertEqual((done.returncode, done.stdout, done.stderr.decode("utf-8").replace("\r\n", "\n")),
                         (1, b"", "[tg_collect] 실패: ValueError\n"))


if __name__ == "__main__":
    unittest.main()
