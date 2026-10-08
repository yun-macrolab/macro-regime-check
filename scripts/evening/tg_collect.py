#!/usr/bin/env python3
"""저녁판 수집 — 텔레그램 공개 채널의 미리보기 쪽을 읽어 수집 창 안의 글을 모은다 (2026-10-08, 1단계 규칙 선별판).

목록(data/sources.json)의 채널마다 https://t.me/s/<채널> 한 쪽(최근 20글)을 받고, 직전 판의 마지막 글까지 닿지 못했으면
?before=<가장 작은 글 번호>로 한 쪽만 더 받는다. 속보형(wire) 채널은 미리보기 검색(?q=금리) 한 쪽 — 수신에 실패하거나 글이 없으면
최근 한 쪽. 제외(off) 채널은 요청하지 않는다. 형태·CLI·종료코드는 digest_schema.py 머리말이 기준이다.

가장 중요한 선: 여기서 읽은 글자는 <work>(.work/evening) 밖으로 나가지 않는다.
  - 원문이 든 파일은 <work>/pages/*.html과 <work>/posts.json뿐이다. 커밋·아티팩트·로그에 넣지 않는다.
  - 표준 출력·오류에는 개수·코드와 목록의 채널 이름만 찍는다(공개 Actions 로그). 예외가 나면 예외 종류 이름만 찍고 종료코드 1
    (run_cli) — 추적문과 메시지에 글 조각이 섞여 나가지 않게. test_tg_collect.py가 심어 둔 글자로 강제한다.
  - 채널에서 온 글자는 자료일 뿐이다. 요청 주소는 목록의 채널 이름과 정수 글 번호로만 만들고, 쪽에서 읽은 주소로는 아무것도 받지 않는다.

글 읽기(parse_page): 본문은 글자만 — 태그를 벗기고 줄마다 공백을 정리한다. 주소 자체로 쓴 링크의 글자는 본문에서 빼고 links에 둔다
(주소뿐인 글은 본문이 빈다). 전달 원글은 공개 글 주소가 있을 때만 채널·번호를 남기고 이름은 남기지 않는다. 링크 카드는 제목이 있을
때만(묶기 열쇠용 — 공개본에는 안 나간다), media는 본문 없이 사진·영상·파일만 있는 글이다. 알림 글(고정 알림 등)은 세지 않는다.

수신: urllib 기본 머리말(User-Agent를 붙이지 않는다), 요청 사이 3초, 요청당 20초·한 쪽 45초·3MB, 전체 30요청·6분
(수집 창이 48시간을 넘는 월요일·연휴 뒤에는 40요청·8분). 순서는 채권 → 애널 → 개인 → 속보형이고, 아직 첫 쪽을 받지 못한 채널 몫의
요청은 남겨 둔다(앞 채널의 '한 쪽 더'가 예산을 다 쓰지 않게). t.me 밖을 가리키는 리다이렉트는 따라가지 않고, 끝 주소가 미리보기
주소(https://t.me/s/<채널>)가 아니면 실패다.

닫힌 쪽으로: 채널 하나가 실패해도 수집은 마친다(종료코드 0). 채널마다 코드와 읽기 건강 숫자를 collect_status.json에 남기고,
판단(ok·short·broken)은 coverage_verdict가 한다. 실패한 채널의 글은 그날 싣지 않고, 연속 실패를 하나 올리고, 마지막 글 번호·시각은
직전 판의 것을 그대로 둔다.
  fetch 수신 실패 · no_preview 미리보기 주소가 아님 · budget 요청·시간 상한 · title 채널 제목 해시가 목록과 다름(이름이 다른 채널로
  넘어간 경우) · empty 글이나 올린 시각을 하나도 못 읽음(형식이 바뀐 쪽) · rewind 직전 판의 마지막 글이 쪽에 있는데 시각이 다르거나,
  그 글보다 늦게 올린 글의 번호가 그 번호 이하(글 번호가 처음부터 다시 시작 — 이름이 남에게 넘어간 채널)
  rewind는 스스로 풀리지 않는다(글 번호는 되돌아가지 않으니 넘어간 채널이거나 상태 파일이 깨진 것이다). 사람이 확인한 뒤 그 채널을
  한 판 동안 목록에서 빼거나 off로 두면 상태 기록에서 빠져, 되돌린 다음 판부터 새로 읽는다.
  title인 채널의 줄에는 쪽에서 본 제목 해시(title_sha=…)를 같이 찍는다 — 제목만 바뀐 것이면 그 값을 sources.json에 옮긴다.
본문 칸의 이름만 바뀌면 글은 읽히되 본문이 비므로, 채널이 아니라 판정이 broken이 된다(본문 비율이 절반 아래 — 판을 내지 않는다).
계약에 자리가 없는 건강 숫자 둘은 로그에만 찍는다: with_time(올린 시각을 읽은 글 수) · cut(두 쪽으로도 창의 시작에 닿지 못함).

--replay: 네트워크 없이 <work>/pages/의 저장분(manifest.json의 쪽과 코드 그대로)으로 posts.json · collect_status.json을 다시 만든다.
--now · --state가 같으면 글과 채널 숫자가 같다(다른 칸은 replay · collected_at · elapsed_s뿐). manifest에 없는 쪽은 못 받은 것으로 본다.

사용법: python scripts/evening/tg_collect.py [--sources data/sources.json] [--state data/digest_state.json]
                                             [--work .work/evening] [--replay] [--now 2026-10-08T18:07:00+09:00]
"""
import argparse
import datetime
import http.client
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

import digest_schema as S

TH = S.TH
HOST = "t.me"
PREVIEW = f"https://{HOST}/s/"
# 수집 창이 이보다 길면 요청·시간 상한을 늘린다 — 숫자는 digest_rules.TH에 있다
LONG_H, LONG_REQUESTS, LONG_BUDGET_S = TH["long_window_h"], TH["max_requests_long"], TH["budget_long_s"]
MAX_LINKS, MAX_TITLE, MAX_SITE = 50, 500, 200          # 계약(post)의 상한

# ---------- 미리보기 쪽 → 글 ----------

_HANDLE = r"[A-Za-z][A-Za-z0-9_]{3,31}"
_POST_RE = re.compile(rf"^(?P<ch>{_HANDLE})/(?P<id>[1-9]\d{{0,9}})$", re.ASCII)
_FWD_RE = re.compile(rf"^https?://(?:t|telegram)\.me/(?P<ch>{_HANDLE})/(?P<id>[1-9]\d{{0,9}})(?:[?#].*)?$", re.ASCII)
_HTTP_RE = re.compile(r"^https?://", re.IGNORECASE)
_BARE_RE = re.compile(r"^(?:https?://)?(?:www\.)?", re.IGNORECASE)
# 글자를 모으는 칸: 본문(답글 미리보기는 js-message_text 표식이 없다) · 링크 카드의 제목 · 사이트 이름
_BOXES = (("text", {"tgme_widget_message_text", "js-message_text"}), ("title", {"link_preview_title"}),
          ("site", {"link_preview_site_name"}))
_BLOCKS = ("div", "blockquote", "pre", "p", "li")      # 본문 안에서 줄을 가르는 덩어리 — 붙여 읽으면 앞뒤 낱말이 이어진다
_MEDIA = ("tgme_widget_message_photo", "tgme_widget_message_video", "tgme_widget_message_document", "tgme_widget_message_grouped",
          "tgme_widget_message_voice", "tgme_widget_message_roundvideo", "tgme_widget_message_sticker", "tgme_widget_message_poll",
          "tgme_widget_message_location", "message_media_not_supported")


def _fwd(href):
    """전달 원글의 주소 → {"ch", "id"}. 주소가 없거나 공개 글 주소가 아니면 둘 다 None(전달이라는 것만 남긴다)."""
    m = _FWD_RE.match(href or "")
    return {"ch": m.group("ch"), "id": int(m.group("id"))} if m else {"ch": None, "id": None}


def _is_address(shown, href):
    """a의 글자가 주소 자체인가 — 그러면 본문에서 뺀다(주소는 links에 있다). 이름을 붙인 링크의 글자는 본문에 둔다."""
    t = "".join(shown.split())
    bare = lambda u: _BARE_RE.sub("", u.strip()).rstrip("/")
    return bool(t) and (_HTTP_RE.match(t) is not None or t.lower().startswith("www.") or bare(t) == bare(href))


class _Page(HTMLParser):
    """t.me/s 미리보기 한 쪽에서 이 채널의 글을 뽑는다. 글자만 모으고 태그는 벗긴다. 알림 글(service_message)과 다른 채널의 글은 건너뛴다."""

    def __init__(self, handle):
        super().__init__(convert_charrefs=True)
        self.want, self.out, self.cur, self.depth, self.top = handle.lower(), [], None, 0, 0
        self.box, self.link, self.dated = None, None, False    # 모으는 칸 [이름, div 깊이, 조각] · 본문 안의 a [href, 조각] · 시각 a 안인가

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if tag == "div":
            self._div(a, cls)
            self.depth += 1
        if self.cur is None:
            return
        if any(c.startswith(_MEDIA) for c in cls):
            self.cur["has_media"] = True
        if (tag == "br" or tag in _BLOCKS) and self.box is not None:
            (self.link[1] if self.link is not None else self.box[2]).append("\n")
        elif tag == "time" and self.dated and a.get("datetime"):
            self.cur["time"] = a["datetime"]                     # 올린 시각 — 영상 길이(time)에는 datetime이 없다
        elif tag == "a":
            self._anchor(a.get("href") or "", cls)

    def _div(self, a, cls):
        m = _POST_RE.match(a.get("data-post") or "") if "tgme_widget_message" in cls else None
        if m:                                                    # 새 글 — 앞 글이 안 닫혔으면(태그가 어긋난 쪽) 여기서 닫는다
            self._close()
            if m.group("ch").lower() == self.want and "service_message" not in cls:
                self.top, self.cur = self.depth, {"id": int(m.group("id")), "time": None, "text": None, "title": None, "site": None,
                                                  "url": None, "links": [], "fwd": None, "reply": False, "has_media": False}
        elif self.cur is None:
            return
        elif "tgme_widget_message_forwarded_from" in cls:
            self.cur["fwd"] = {"ch": None, "id": None}
        elif self.box is None:
            name = next((n for n, need in _BOXES if need <= set(cls) and self.cur[n] is None), None)
            if name:
                self.box = [name, self.depth, []]

    def _anchor(self, href, cls):
        if "tgme_widget_message_date" in cls:
            self.dated = True
        elif "tgme_widget_message_forwarded_from_name" in cls:
            self.cur["fwd"] = _fwd(href)
        elif "tgme_widget_message_reply" in cls:
            self.cur["reply"] = True
        elif "tgme_widget_message_link_preview" in cls:
            self.cur["url"] = href
        elif self.box is not None and self.box[0] == "text":
            self._end_link()
            self.link = [href, []]

    def handle_data(self, data):
        if self.link is not None:
            self.link[1].append(data)
        elif self.box is not None:
            self.box[2].append(data)

    def handle_endtag(self, tag):
        if tag in _BLOCKS and self.box is not None:
            self.box[2].append("\n")
        if tag == "a":
            self._end_link()
            self.dated = False
        elif tag == "div":
            self.depth -= 1
            if self.box is not None and self.depth <= self.box[1]:
                self._end_box()
            if self.cur is not None and self.depth <= self.top:
                self._close()

    def _end_link(self):
        """본문 안의 a를 닫는다 — 주소는 links로, 글자는 주소 자체가 아닐 때만 본문에 둔다."""
        if self.link is None:
            return
        (href, parts), self.link = self.link, None
        if _HTTP_RE.match(href) and len(href) <= S.MAX_URL and href not in self.cur["links"]:
            self.cur["links"].append(href)
        if self.box is not None and not _is_address("".join(parts), href):
            self.box[2].append("".join(parts))

    def _end_box(self):
        self._end_link()
        (name, _, parts), self.box = self.box, None
        self.cur[name] = "".join(parts)

    def _close(self):
        if self.cur is None:
            return
        if self.box is not None:
            self._end_box()
        self.out.append(self.cur)
        self.cur, self.link, self.dated = None, None, False


def _lines(raw):
    """줄마다 공백 묶음을 공백 하나로, 빈 줄은 버린다."""
    return "\n".join(x for x in (" ".join(line.split()) for line in (raw or "").split("\n")) if x)


def _when(value):
    """올린 시각(시간대가 있는 ISO) → "…+09:00". 못 읽으면 None."""
    try:
        return S.iso(S.parse_iso(value))
    except (ValueError, OverflowError):
        return None


def _post(c, handle, via):
    """파서가 모은 조각 → 계약의 post. 카드는 제목이 있을 때만(묶기 열쇠용), media는 본문 없이 사진·영상·파일만 있는 글."""
    text, title = _lines(c["text"])[:S.MAX_TEXT], " ".join((c["title"] or "").split())[:MAX_TITLE]
    url = c["url"] if _HTTP_RE.match(c["url"] or "") and len(c["url"]) <= S.MAX_URL else ""
    card = {"title": title, "site": " ".join((c["site"] or "").split())[:MAX_SITE], "url": url} if title else None
    return {"ch": handle, "id": c["id"], "at": _when(c["time"]), "text": text, "links": c["links"][:MAX_LINKS], "fwd": c["fwd"],
            "card": card, "reply": c["reply"], "media": c["has_media"] and not text, "via": via}


def parse_page(page, handle, via="page"):
    """미리보기 한 쪽 → 이 채널의 글들(글 번호순, 같은 번호는 처음 것). 글 하나는 계약의 post 꼴이고, 시각을 못 읽은 글은 at이 None이다."""
    p = _Page(handle)
    p.feed(page)
    p.close()
    p._close()
    seen = {}
    for c in p.out:
        seen.setdefault(c["id"], c)
    return [_post(seen[i], handle, via) for i in sorted(seen)]


# ---------- 수신 ----------

class Fail(Exception):
    """쪽을 받지 못한 사유 — 코드(digest_schema.CH_CODES)만 들고 다닌다. 글자는 싣지 않는다."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


class _SameHost(urllib.request.HTTPRedirectHandler):
    """t.me 밖을 가리키는 리다이렉트는 따라가지 않는다 — 다른 호스트에는 요청을 보내지 않는다."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        u = urllib.parse.urlsplit(newurl)
        if (u.scheme, u.netloc.lower()) != ("https", HOST):
            fp.close()
            raise Fail("no_preview")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_SameHost())             # 머리말은 urllib 기본값 그대로


def page_url(handle, kind="page", before=None):
    """요청 주소 — 목록의 채널 이름과 정수 글 번호로만 만든다. kind: page(최근 쪽) · search(속보형의 검색 쪽) · more(before보다 앞 쪽)."""
    if not (isinstance(handle, str) and S.HANDLE_RE.fullmatch(handle)):
        raise ValueError("채널 이름 꼴이 아님")
    if kind == "search":
        return f"{PREVIEW}{handle}?q={urllib.parse.quote(TH['wire_query'])}"
    return f"{PREVIEW}{handle}" if before is None else f"{PREVIEW}{handle}?before={int(before)}"


def fetch(url, handle, opener=None, clock=time.monotonic, left=None):
    """한 쪽을 받아 글자로 돌려준다. 요청·수신 한 번은 timeout_s, 한 쪽 전체는 page_budget_s(남은 전체 시간 left가 더 짧으면 그만큼)를
    넘기지 않는다. 끝 주소가 https://t.me/s/<채널>이 아니면 Fail("no_preview"), 너무 느리거나 크면 Fail("fetch")."""
    limit = TH["page_budget_s"] if left is None else max(1.0, min(TH["page_budget_s"], left))
    start, chunks, size = clock(), [], 0
    with (opener or _OPENER.open)(url, timeout=min(TH["timeout_s"], limit)) as r:
        final = urllib.parse.urlsplit(r.geturl())
        if (final.scheme, final.netloc.lower(), final.path.lower()) != ("https", HOST, f"/s/{handle}".lower()):
            raise Fail("no_preview")
        while True:
            if clock() - start > limit:
                raise Fail("fetch")
            chunk = r.read1(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > TH["max_bytes"]:
                raise Fail("fetch")
            chunks.append(chunk)
    return b"".join(chunks).decode("utf-8", "replace")


def limits(window):
    """(요청 상한, 시간 상한 초) — 수집 창이 48시간을 넘으면(월요일·연휴 뒤) 늘린다."""
    span = S.parse_iso(window["to"]) - S.parse_iso(window["from"])
    long = span > datetime.timedelta(hours=LONG_H)
    return (LONG_REQUESTS, LONG_BUDGET_S) if long else (TH["max_requests"], TH["budget_s"])


class Live:
    """네트워크에서 쪽을 받는다 — 요청 사이 3초, 요청·시간 상한을 넘으면 더 받지 않는다(budget). 받은 쪽은 들고 있다가 끝에 한꺼번에 쓴다."""
    replay = False

    def __init__(self, cap, budget_s, opener=None, sleep=time.sleep, clock=time.monotonic):
        self.cap, self.budget_s, self.opener, self.sleep, self.clock = cap, budget_s, opener or _OPENER.open, sleep, clock
        self.t0, self.used, self.entries, self.pages = clock(), 0, [], {}

    def elapsed(self):
        return self.clock() - self.t0

    def room(self, reserve=0):
        """요청을 하나 더 보낼 수 있는가. reserve = 아직 첫 쪽을 받지 못한 채널 수(그 몫은 남겨 둔다)."""
        pause = TH["pause_s"] if self.used else 0
        return self.used + 1 + reserve <= self.cap and self.elapsed() + pause < self.budget_s

    def get(self, ch, n, kind, url):
        """쪽 하나 → (코드, 글자 또는 None). 요청한 것·못 한 것(budget) 모두 manifest의 한 줄로 남긴다."""
        code, page = "budget", None
        if self.room():
            if self.used:
                self.sleep(TH["pause_s"])
            self.used += 1
            try:
                page, code = fetch(url, ch, self.opener, self.clock, self.budget_s - self.elapsed()), "ok"
            except Fail as e:
                code = e.code
            except (OSError, ValueError, http.client.HTTPException):
                code = "fetch"
        name = f"{ch}-{n}.html"
        self.entries.append({"ch": ch, "n": n, "kind": kind, "file": name, "ok": code == "ok", "code": code})
        if page is not None:
            self.pages[name] = page
        return code, page


class Replay:
    """저장분(<work>/pages/)에서 쪽을 읽는다 — 네트워크도 기다림도 없다. manifest에 없는 쪽은 받지 못한 것으로 본다."""
    replay = True

    def __init__(self, work, manifest, cap):
        self.dir, self.cap, self.used = os.path.join(work, "pages"), cap, 0
        self.by = {(p["ch"], p["n"]): p for p in manifest["pages"]}

    def elapsed(self):
        return 0.0

    def room(self, reserve=0):
        return self.used + 1 + reserve <= self.cap

    def get(self, ch, n, kind, url):
        e = self.by.get((ch, n))
        if e is None or e["kind"] != kind:
            return "fetch", None
        if e["code"] == "budget":
            return "budget", None
        self.used += 1
        if not e["ok"]:
            return (e["code"] if e["code"] != "ok" else "fetch"), None
        try:
            with open(os.path.join(self.dir, e["file"]), encoding="utf-8", errors="replace", newline="") as f:
                return "ok", f.read()
        except OSError:
            return "fetch", None


# ---------- 채널 하나 ----------

def _page(chan, n, kind, src, before=None):
    """쪽 하나를 받아 읽는다 → (코드, 글들, 제목 해시). 제목 해시가 목록과 다르면 글을 읽지 않는다(title)."""
    ch = chan["handle"]
    code, page = src.get(ch, n, kind, page_url(ch, kind, before))
    if code != "ok":
        return code, [], None
    try:
        title = S.page_title(page)
        sha = S.title_sha(title) if title else None
        same = sha == chan["title_sha"]
        return ("ok" if same else "title"), (parse_page(page, ch, "search" if kind == "search" else "page") if same else []), sha
    except Exception:                                # 꼴이 어긋나 읽다 넘어진 쪽 — 사유는 싣지 않고 '못 읽음'으로
        return "empty", [], None


def _reached(posts, anchor, win):
    """받은 글이 직전 판의 마지막 글(또는 수집 창의 시작)까지 닿았는가. 시각을 하나도 못 읽었으면 더 받아도 소용없으니 닿은 것으로 둔다."""
    last = (anchor or {}).get("last_post")
    timed = [p for p in posts if p["at"]]
    return not timed or bool(last and any(p["id"] <= last for p in posts)) or any(p["at"] <= win["from"] for p in timed)


def _judge(posts, anchor):
    """읽은 글로 채널을 판정한다 — 글이나 시각을 하나도 못 읽었으면 empty. 직전 판의 마지막 글이 쪽에 있는데 시각이 다르거나,
    그 글보다 늦게 올린 글의 번호가 그 번호 이하면 rewind(글 번호는 되돌아가지 않는다 — 이름이 다른 채널로 넘어간 것으로 본다).
    마지막 글을 지우기만 한 채널은 새 글이 없으니 걸리지 않는다."""
    timed = [p for p in posts if p["at"]]
    if not timed:
        return "empty"
    if anchor and anchor["last_post"] and anchor["last_at"]:
        last, at = anchor["last_post"], anchor["last_at"]
        if any((p["id"] == last and p["at"] != at) or (p["id"] <= last and p["at"] > at) for p in timed):
            return "rewind"
    return "ok"


def _merge(*groups):
    """여러 쪽의 글 → 글 번호순, 같은 번호는 처음 것."""
    by = {}
    for p in (p for g in groups for p in g):
        by.setdefault(p["id"], p)
    return [by[i] for i in sorted(by)]


def read_channel(chan, anchor, win, src, waiting):
    """채널 하나를 읽는다 → {"code", "pages"(받은 쪽 수), "posts"(읽은 글 — 실패면 빈 목록), "sha", "cut"}.
    anchor = 직전 판의 {"last_post", "last_at", "fail_streak"}(없으면 None), waiting = 아직 첫 쪽을 받지 못한 채널 수."""
    wire, whole, got = chan["role"] == "wire", False, ("ok", "title", "empty")       # got = 쪽을 받기는 한 코드
    code, posts, sha = _page(chan, 1, "search" if wire else "page", src)
    pages = int(code in got)
    if wire and (code in ("fetch", "empty") or (code == "ok" and not posts)) and src.room(waiting):
        code, posts, sha = _page(chan, 2, "page", src)                 # 검색이 안 되면 최근 한 쪽
        pages += int(code in got)
    elif not wire and code == "ok" and posts and not _reached(posts, anchor, win) and src.room(waiting):
        more, older, seen = _page(chan, 2, "more", src, min(p["id"] for p in posts))
        pages += int(more in got)
        if more == "title":
            code, sha = more, seen
        elif more == "ok":
            posts, whole = _merge(older, posts), not older              # 더 옛 글이 없으면 끝까지 읽은 것
    code = _judge(posts, anchor) if code == "ok" else code
    ok = code == "ok"
    return {"code": code, "pages": pages, "posts": posts if ok else [], "sha": sha,
            "cut": ok and not whole and not _reached(posts, anchor, win)}


def _row(chan, got, anchor, win):
    """채널의 읽기 건강 숫자(collect_status.channels의 한 줄). 실패한 채널은 개수가 0이고 마지막 글은 직전 판의 것 그대로다."""
    ok, posts, keep = got["code"] == "ok", got["posts"], anchor or {"last_post": None, "last_at": None, "fail_streak": 0}
    last = max((p for p in posts if p["at"]), key=lambda p: p["id"], default=None)
    return {"ch": chan["handle"], "group": chan["group"], "role": chan["role"], "ok": ok, "code": got["code"], "pages": got["pages"],
            "posts": len(posts), "with_text": sum(bool(p["text"]) for p in posts), "in_window": len(_inside(posts, win)),
            "last_post": last["id"] if last else keep["last_post"], "last_at": last["at"] if last else keep["last_at"],
            "title_sha": got["sha"], "fail_streak": 0 if ok else min(keep["fail_streak"] + 1, 9_999)}


def _inside(posts, win):
    """수집 창 안의 글(from < 시각 ≤ to). 시각은 모두 +09:00 꼴이라 글자로 견준다(계약의 검증과 같은 방식)."""
    return [p for p in posts if p["at"] and win["from"] < p["at"] <= win["to"]]


# ---------- 전체 ----------

def ordered(sources):
    """요청 순서: 채권 → 애널 → 개인 → 속보형(그 안에서는 sources.json의 순서). off는 요청하지 않는다."""
    groups = S.R.GROUP_ORDER
    rank = lambda c: len(groups) if c["role"] == "wire" else groups.index(c["group"])
    return sorted((c for c in sources["channels"] if c["role"] != "off"), key=rank)


def _say(row, with_time, cut):
    """채널 한 줄 — 목록의 채널 이름과 코드·개수만 찍는다(공개 로그에 남는다). 제목 해시가 목록과 다른 채널(title)은 쪽에서 본
    해시도 찍는다 — 제목만 바뀐 것이면 그 값을 sources.json에 옮겨 적는다(해시 꼴이고, 같은 종류의 값이 목록에 이미 공개돼 있다)."""
    sha = row["title_sha"] if row["code"] == "title" and S.SHA_RE.fullmatch(row["title_sha"] or "") else None
    print(f"[tg_collect] {row['ch']} code={row['code']} pages={row['pages']} posts={row['posts']} with_text={row['with_text']} "
          f"with_time={with_time} in_window={row['in_window']} fail_streak={row['fail_streak']} cut={int(cut)}"
          + (f" title_sha={sha}" if sha else ""), flush=True)


def collect(sources, state, win, src):
    """요청하는 채널을 순서대로 읽는다 → (창 안의 글, 채널별 건강 숫자, {"with_time": 시각을 읽은 글 수, "cut": 잘린 채널 수})."""
    chans = ordered(sources)
    base = (S.state_base(state, win["date"]) or {}).get("channels", {})
    posts, rows, extra = [], [], {"with_time": 0, "cut": 0}
    for i, chan in enumerate(chans):
        anchor = base.get(chan["handle"])
        got = read_channel(chan, anchor, win, src, len(chans) - i - 1)
        row, timed = _row(chan, got, anchor, win), sum(p["at"] is not None for p in got["posts"])
        _say(row, timed, got["cut"])
        rows.append(row)
        posts += _inside(got["posts"], win)
        extra = {"with_time": extra["with_time"] + timed, "cut": extra["cut"] + int(got["cut"])}
    return sorted(posts, key=lambda p: (p["at"], p["ch"], p["id"])), rows, extra


def documents(win, now, src, posts, rows):
    """→ (posts.json, collect_status.json). 수집 시각은 실행 시각 + 걸린 시간이다(저장분으로 다시 만들 때는 실행 시각)."""
    spent = round(float(src.elapsed()), 3)
    head = {"schema": S.SCHEMA, "edition": win["date"], "window": {"from": win["from"], "to": win["to"]},
            "collected_at": S.iso(now + datetime.timedelta(seconds=spent))}
    status = {**head, "window_kind": win["kind"], "capped": win["capped"], "replay": src.replay, "requests": src.used,
              "elapsed_s": spent, "verdict": S.coverage_verdict(rows)["verdict"], "channels": rows}
    return {**head, "posts": posts}, status


def _write_text(path, text):
    """받은 쪽을 그대로 쓴다(임시 파일에 쓰고 바꿔치기)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(path + ".tmp", path)


def save(work, src, now, posts_doc, status):
    """검증을 모두 통과한 뒤에만 쓴다 — 하나라도 어긋나면 아무것도 쓰지 않는다. 저장분으로 다시 만들 때는 pages/를 건드리지 않는다."""
    S.validate_posts_doc(posts_doc)
    S.validate_collect_status(status)
    if not src.replay:
        manifest = S.validate_manifest({"schema": S.SCHEMA, "now": S.iso(now), "pages": src.entries})
        for name, page in src.pages.items():
            _write_text(os.path.join(work, "pages", name), page)
        S.write_json(os.path.join(work, "pages", "manifest.json"), manifest)
    S.write_json(os.path.join(work, "posts.json"), posts_doc)
    S.write_json(os.path.join(work, "collect_status.json"), status)


def main(argv=None, opener=None, sleep=time.sleep, clock=time.monotonic):
    ap = argparse.ArgumentParser(description="텔레그램 공개 채널 미리보기 → <work>/posts.json · collect_status.json (원문은 <work> 안에만)")
    ap.add_argument("--sources", default=os.path.join(S.DATA, "sources.json"), help="채널 목록 (기본: 저장소의 data/sources.json)")
    ap.add_argument("--state", default=os.path.join(S.DATA, "digest_state.json"), help="직전 판의 상태 (없으면 첫 실행)")
    ap.add_argument("--work", default=S.WORK, help="작업 폴더 (기본: .work/evening — git 제외)")
    ap.add_argument("--replay", action="store_true", help="네트워크 없이 <work>/pages/의 저장분으로 다시 만든다")
    ap.add_argument("--now", help="실행 시각(ISO, 시간대 포함). --replay에서 안 주면 manifest의 now")
    a = ap.parse_args(argv)
    work = os.path.abspath(a.work)
    sources = S.validate_sources(S.read_json(a.sources))
    state = S.read_json(a.state, None)
    if state is not None:
        S.validate_state(state)
    manifest = S.validate_manifest(S.read_json(os.path.join(work, "pages", "manifest.json"))) if a.replay else None
    now = S.parse_iso(a.now or manifest["now"]) if a.now or manifest else datetime.datetime.now(S.KST)
    win = S.collect_window(now, state)
    cap, budget_s = limits(win)
    src = Replay(work, manifest, cap) if a.replay else Live(cap, budget_s, opener, sleep, clock)
    posts, rows, extra = collect(sources, state, win, src)
    posts_doc, status = documents(win, now, src, posts, rows)
    save(work, src, now, posts_doc, status)
    health = S.coverage_verdict(rows)
    S.report("tg_collect", edition=win["date"], window_kind=win["kind"], capped=win["capped"], replay=src.replay, requests=src.used,
             elapsed_s=status["elapsed_s"], channels_ok=health["channels_ok"], channels_total=health["channels_total"],
             bond_ok=health["bond_ok"], posts=health["posts"], with_text=health["with_text"], with_time=extra["with_time"],
             in_window=len(posts), cut=extra["cut"], verdict=health["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(S.run_cli("tg_collect", main))
