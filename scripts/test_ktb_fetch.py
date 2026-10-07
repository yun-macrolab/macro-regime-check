#!/usr/bin/env python3
"""국고채 참고 자료(ktb_fetch) 테스트 — 채널 글에서 숫자만 읽는지, 형식이 바뀌면 닫힌 쪽으로 실패하는지.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — 미리보기 페이지와 같은 뼈대의 합성 HTML(지어낸 숫자)을 쓴다. 실제 글은 저장소에 넣지 않는다.
"""
import os, sys, io, re, json, html, datetime, tempfile, unittest, shutil, contextlib

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import ktb_fetch as kf

REPO = os.path.dirname(SCRIPTS)
D = datetime.date
NOW = datetime.datetime(2026, 10, 7, 1, 30, tzinfo=datetime.timezone.utc)
SPEC_KEYS = {"key", "title", "unit", "years", "zero", "threshold", "note", "source_note", "notices", "lines"}
LINE_KEYS = {"key", "label", "role", "series", "derived", "points"}


def daily_lines(y, m, d, y3=3.9, y5=4.1, y10=4.35, y30=4.6, chg=(0.3, -1.3, -1.7, 0), basis="민평3사 기준",
                spreads=None):
    """일일동향 글의 줄 — 미국 구역(10년물이 여기에도 있다) → 국고채 구역 → 크레딧 구역."""
    s103, s3010 = spreads or (round((y10 - y3) * 100, 1), round((y30 - y10) * 100, 1))
    return ["KB증권 리서치본부 채권크레딧팀", f"{y}년 {m}월 {d}일 채권시장 일일동향", "",
            "■ 미국 채권시장", "2년물: 9.111% (2.8bp)", "10년물: 9.222% (1.5bp)", "10-2년 스프레드: 11.1bp (-1.3bp)",
            "IG 스프레드: 81bp (0bp)", "",
            f"■ 국고채 금리 ({basis})",
            f"3년물: {y3}% ({chg[0]}bp)", f"5년물: {y5}% ({chg[1]}bp)",
            f"10년물: {y10}% ({chg[2]}bp)", f"30년물: {y30}% ({chg[3]}bp)",
            f"10-3년 스프레드: {s103}bp (-2bp)", f"30-10년 스프레드: {s3010}bp (1.7bp)",
            "3년 선물: 103.17 (3틱) (외국인 -4732계약 순매수)", "",
            "■ 국내 크레딧 스프레드 (국고채 대비, 3년물 기준)", "회사채 AAA: 45.1bp (0.2bp)", "5년물: 8.888% (1bp)"]


def post_html(pid, when, lines, channel="jk_bond", cls="tgme_widget_message_text js-message_text", mark=True):
    body = "<br/>".join(html.escape(x) for x in lines)
    if mark:                                    # 검색 결과는 검색어를 <mark>로 감싼다
        body = body.replace("채권시장", '<mark class="highlight">채권시장</mark>')
    return (f'<div class="tgme_widget_message_wrap js-widget_message_wrap">'
            f'<div class="tgme_widget_message text_not_supported_wrap js-widget_message" data-post="{channel}/{pid}">'
            f'<div class="tgme_widget_message_bubble">'
            f'<div class="tgme_widget_message_author"><span dir="auto">채널 이름 &amp; 누구</span></div>'
            f'<div class="{cls}" dir="auto">{body}</div>'
            f'<div class="tgme_widget_message_footer"><a class="tgme_widget_message_date" '
            f'href="https://t.me/{channel}/{pid}"><time datetime="{when}" class="time">08:00</time></a></div>'
            f'</div></div></div>')


def page(*posts):
    return "<html><body><section class='tgme_channel_history'>" + "".join(posts) + "</section></body></html>"


def morning(y, m, d):
    """그 날 아침 08:00 KST에 올라온 글의 시각(UTC로는 전날 23:00)."""
    t = datetime.datetime(y, m, d, 8, 0, tzinfo=kf.KST).astimezone(datetime.timezone.utc)
    return t.isoformat(timespec="seconds")


def daily_post(pid, y, m, d, **kw):
    return post_html(pid, morning(y, m, d), daily_lines(y, m, d, **kw))


class FakeOpener:
    """urlopen 대역 — URL별 응답을 돌려주고 부른 URL을 적는다."""
    def __init__(self, pages, final=None, error=None):
        self.pages, self.final, self.error, self.calls = list(pages), final, error, []

    def __call__(self, url, timeout=None):
        self.calls.append(url)
        if self.error:
            raise self.error
        body = (self.pages.pop(0) if self.pages else page()).encode("utf-8")
        final = self.final or url

        class R(io.BytesIO):
            def geturl(self_inner):
                return final

            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *a):
                return False
        return R(body)


class MessagesTest(unittest.TestCase):
    def test_extracts_post_time_and_lines_without_markup(self):
        ms = kf.messages(page(daily_post(22711, 2026, 10, 7)))
        self.assertEqual(len(ms), 1)
        self.assertEqual(ms[0]["post"], 22711)
        self.assertEqual(ms[0]["time"], morning(2026, 10, 7))
        self.assertEqual(ms[0]["lines"][1], "2026년 10월 7일 채권시장 일일동향")     # <mark> 벗김
        self.assertIn("3년물: 3.9% (0.3bp)", ms[0]["lines"])

    def test_other_channels_and_odd_ids_are_ignored(self):
        ms = kf.messages(page(post_html(5, morning(2026, 10, 7), daily_lines(2026, 10, 7), channel="other_ch"),
                              post_html("12x", morning(2026, 10, 7), daily_lines(2026, 10, 7)),
                              daily_post(7, 2026, 10, 7)))
        self.assertEqual([m["post"] for m in ms], [7])

    def test_reply_preview_text_is_not_the_body(self):
        reply = post_html(9, morning(2026, 10, 7), ["3년물: 1.111% (0bp)"], cls="tgme_widget_message_text")
        self.assertEqual(kf.messages(page(reply)), [])                               # 본문 표식(js-message_text) 없음

    def test_entities_are_unescaped_and_photo_posts_skipped(self):
        photo = ('<div class="tgme_widget_message js-widget_message" data-post="jk_bond/3">'
                 '<div class="tgme_widget_message_photo_wrap"></div></div>')
        ms = kf.messages(page(photo, post_html(4, morning(2026, 10, 7), ["A & B <c>", "둘째 줄"])))
        self.assertEqual([(m["post"], m["lines"]) for m in ms], [(4, ["A & B <c>", "둘째 줄"])])


class ParseDailyTest(unittest.TestCase):
    def one(self, pid=22711, when=None, **kw):
        y, m, d = kw.pop("date", (2026, 10, 7))
        lines = kw.pop("lines", None) or daily_lines(y, m, d, **kw)
        return kf.parse_daily(kf.messages(page(post_html(pid, when or morning(y, m, d), lines)))[0])

    def test_reads_only_the_ktb_section(self):
        kind, row = self.one(y3=3.934, y5=4.117, y10=4.372, y30=4.52, chg=(0.7, 0.2, 1.5, 1.8))
        self.assertEqual(kind, "ok")
        self.assertEqual(row["date"], D(2026, 10, 7))
        self.assertEqual(row["post"], 22711)
        self.assertEqual(row["y"], {"3": 3.934, "5": 4.117, "10": 4.372, "30": 4.52})     # 미국 10년물(9.222)이 아니다
        self.assertEqual(row["chg"], {"3": 0.7, "5": 0.2, "10": 1.5, "30": 1.8})

    def test_date_is_the_posting_day_in_korea(self):
        # UTC로는 전날 밤 — 한국 시간 날짜를 쓴다
        kind, row = self.one(when="2026-10-06T23:00:12+00:00")
        self.assertEqual((kind, row["date"]), ("ok", D(2026, 10, 7)))

    def test_ordinary_posts_are_not_daily_reports(self):
        news = ["국고채 금리가 올랐다는 기사", "■ 국고채 금리 (민평3사 기준)", "3년물: 3.9% (0.3bp)", "10년물: 4.3% (1bp)"]
        self.assertIsNone(self.one(lines=news))
        late = ["기사 제목", "둘째 줄", "셋째 줄", "2026년 10월 7일 채권시장 일일동향"] + daily_lines(2026, 10, 7)[2:]
        self.assertIsNone(self.one(lines=late))                                     # 제목은 첫 세 줄 안에서만

    def test_changed_basis_or_header_is_rejected(self):
        self.assertEqual(self.one(basis="민평4사 기준")[0], "bad")
        self.assertEqual(self.one(basis="최종호가수익률")[0], "bad")
        lines = [x for x in daily_lines(2026, 10, 7) if "국고채 금리" not in x]
        self.assertEqual(self.one(lines=lines)[0], "bad")

    def test_every_tenor_must_be_read(self):
        # 네 만기 중 하나라도 못 읽으면 그 글을 버린다 — 표기만 바뀐 만기가 조용히 빠지지 않게(검토)
        for gone in ("3년물: 3.9", "5년물: 4.1", "10년물: 4.35", "30년물: 4.6"):
            lines = [x for x in daily_lines(2026, 10, 7) if not x.startswith(gone)]
            self.assertEqual(self.one(lines=lines)[0], "bad", gone)
        renamed = [x.replace("30년물: 4.6%", "국고30년: 4.6%") for x in daily_lines(2026, 10, 7)]
        self.assertEqual(self.one(lines=renamed)[0], "bad")

    def test_spread_lines_must_be_there_to_check_against(self):
        # 스프레드 줄 형식이 바뀌면 금리를 맞춰 볼 수 없다 — 열린 쪽으로 통과시키지 않는다(검토)
        lines = [x.replace("10-3년 스프레드", "10/3년 스프레드") for x in daily_lines(2026, 10, 7, y10=5.35, spreads=(45.0, 25.0))]
        self.assertEqual(self.one(lines=lines)[0], "bad")
        lines = [x for x in daily_lines(2026, 10, 7) if not x.startswith("30-10년")]
        self.assertEqual(self.one(lines=lines)[0], "bad")

    def test_exact_flag_tells_whether_the_title_matches_the_posting_day(self):
        self.assertTrue(self.one()[1]["exact"])
        self.assertFalse(self.one(when=morning(2026, 10, 7), lines=daily_lines(2026, 10, 6))[1]["exact"])

    def test_out_of_range_numbers_are_rejected(self):
        self.assertEqual(self.one(y3=40.0)[0], "bad")
        self.assertEqual(self.one(y10=0.0)[0], "bad")
        self.assertEqual(self.one(chg=(500, 0, 0, 0))[0], "bad")

    def test_yields_must_agree_with_the_posted_spread(self):
        self.assertEqual(self.one(spreads=(99.9, 25.0))[0], "bad")                    # 10-3년이 금리와 안 맞음
        self.assertEqual(self.one(spreads=(45.0, 99.9))[0], "bad")                    # 30-10년이 안 맞음
        self.assertEqual(self.one(spreads=(45.0, 25.0))[0], "ok")

    def test_duplicate_or_malformed_tenor_lines_are_rejected(self):
        lines = daily_lines(2026, 10, 7)
        i = lines.index("3년물: 3.9% (0.3bp)")
        self.assertEqual(self.one(lines=lines[:i] + ["3년물: 3.8% (0.1bp)"] + lines[i:])[0], "bad")
        bad = [x.replace("10년물: 4.35% (-1.7bp)", "10년물: 4.35 (-1.7bp)") for x in lines]
        self.assertEqual(self.one(lines=bad)[0], "bad")                               # 형식이 어긋난 줄 → 10년물 없음
        bad = [x.replace("5년물: 4.1% (-1.3bp)", "5년물: 4.1% (약 -1.3bp)") for x in lines]
        self.assertEqual(self.one(lines=bad)[0], "bad")                               # 없어도 되는 만기라도 줄이 어긋나면 버린다

    def test_title_far_from_posting_day_is_rejected(self):
        lines = daily_lines(2026, 9, 1)
        self.assertEqual(self.one(when=morning(2026, 10, 7), lines=lines)[0], "bad")
        self.assertEqual(self.one(when=morning(2026, 10, 7), lines=daily_lines(2026, 10, 6))[0], "ok")

    def test_impossible_title_date_or_missing_time_is_rejected(self):
        self.assertEqual(self.one(lines=daily_lines(2026, 13, 40))[0], "bad")
        msg = kf.messages(page(daily_post(1, 2026, 10, 7)))[0]
        self.assertEqual(kf.parse_daily({**msg, "time": None})[0], "bad")
        self.assertEqual(kf.parse_daily({**msg, "time": "어제"})[0], "bad")
        self.assertEqual(kf.parse_daily({**msg, "time": "2026-10-07T08:00:00"})[0], "bad")   # 시간대 없는 시각
        self.assertEqual(kf.parse_daily({**msg, "time": "9999-12-31T20:00:00+00:00"})[0], "bad")   # 날짜 범위를 넘는 시각

    def test_absurd_post_ids_are_not_messages(self):
        huge = post_html("9" * 40, morning(2026, 10, 7), daily_lines(2026, 10, 7))
        self.assertEqual(kf.messages(page(huge)), [])


class CollectTest(unittest.TestCase):
    def test_pages_walk_backwards_by_the_smallest_post_id(self):
        op = FakeOpener([page(daily_post(30, 2026, 10, 7), daily_post(20, 2026, 10, 6)),
                         page(daily_post(10, 2026, 10, 5)), page()])
        naps = []
        ms = kf.collect(5, opener=op, sleep=naps.append)
        self.assertEqual([m["post"] for m in ms], [30, 20, 10])
        self.assertEqual(op.calls[0], kf.search_url())
        self.assertTrue(op.calls[0].startswith("https://t.me/s/jk_bond?q=%"))
        self.assertTrue(op.calls[1].endswith("&before=20") and op.calls[2].endswith("&before=10"))
        self.assertEqual(len(op.calls), 3)                                           # 빈 쪽에서 멈춘다
        self.assertEqual(naps, [kf.PAUSE, kf.PAUSE])                                  # 쪽 사이에 쉰다

    def test_one_page_by_default_and_a_hard_cap(self):
        many = [page(daily_post(100 - i, 2026, 10, 7)) for i in range(40)]
        op = FakeOpener(list(many))
        kf.collect(1, opener=op, sleep=lambda s: None)
        self.assertEqual(len(op.calls), 1)
        op = FakeOpener(list(many))
        kf.collect(999, opener=op, sleep=lambda s: None)
        self.assertEqual(len(op.calls), kf.MAX_PAGES)

    def test_a_page_that_does_not_go_back_stops_the_walk(self):
        same = page(daily_post(30, 2026, 10, 7))
        op = FakeOpener([same, same, same])
        kf.collect(5, opener=op, sleep=lambda s: None)
        self.assertEqual(len(op.calls), 2)

    def test_redirect_away_from_the_preview_is_an_error(self):
        op = FakeOpener([page(daily_post(1, 2026, 10, 7))], final="https://t.me/jk_bond")
        with self.assertRaises(RuntimeError):
            kf.collect(1, opener=op, sleep=lambda s: None)
        op = FakeOpener([page(daily_post(1, 2026, 10, 7))], final="https://t.me/s/jk_bond_fake?q=x")
        with self.assertRaises(RuntimeError):
            kf.collect(1, opener=op, sleep=lambda s: None)

    def test_oversized_response_is_an_error(self):
        op = FakeOpener(["x" * (kf.MAX_BYTES + 10)])
        with self.assertRaises(RuntimeError):
            kf.collect(1, opener=op, sleep=lambda s: None)

    def test_a_trickling_response_hits_the_overall_budget(self):
        # 요청 시한(TIMEOUT)은 수신 한 번에만 걸린다 — 조금씩 오는 응답은 전체 시한으로 끊는다(검토)
        ticks = iter(range(0, 10 * kf.BUDGET, kf.BUDGET // 3))
        op = FakeOpener(["x" * (3 * 65536)])
        with self.assertRaises(RuntimeError):
            kf.fetch(kf.search_url(), op, clock=lambda: next(ticks))
        self.assertEqual(kf.fetch(kf.search_url(), FakeOpener(["abc"]), clock=lambda: 0), "abc")


def row(d, post, y3=3.9, y5=4.1, y10=4.35, y30=4.6, chg=None):
    return {"date": d, "post": post, "y": {"3": y3, "5": y5, "10": y10, "30": y30},
            "chg": chg or {"3": 0.3, "5": -1.3, "10": -1.7, "30": 0.0}}


class BuildTest(unittest.TestCase):
    def test_merge_adds_days_and_newer_posts_win(self):
        old = [[D(2026, 10, 5), 10, 3.8, 4.0, 4.2, 4.5], [D(2026, 10, 6), 20, 3.9, 4.1, 4.3, 4.6]]
        new = [row(D(2026, 10, 6), 25, y3=3.95), row(D(2026, 10, 7), 30), row(D(2026, 10, 5), 9, y3=1.0)]
        rows, added, changed = kf.merge(old, new)
        self.assertEqual([r[0] for r in rows], [D(2026, 10, 5), D(2026, 10, 6), D(2026, 10, 7)])
        self.assertEqual((added, changed), (1, 1))
        self.assertEqual(rows[1][:3], [D(2026, 10, 6), 25, 3.95])                     # 같은 날은 나중 글이
        self.assertEqual(rows[0][:3], [D(2026, 10, 5), 10, 3.8])                      # 옛 글 번호는 덮지 않는다

    def test_title_matching_post_beats_a_later_post_with_another_days_title(self):
        # 같은 날 올라온 글 둘 — 제목 날짜가 그날인 글이 먼저다. 번호만 큰 다른 날짜 제목의 글이 덮지 않는다(검토)
        today, stray = row(D(2026, 10, 7), 40), {**row(D(2026, 10, 7), 41, y3=3.111), "exact": False}
        rows, added, changed = kf.merge([[D(2026, 10, 6), 20, 3.8, 4.0, 4.2, 4.5]], [today, stray])
        self.assertEqual((rows[-1][:3], added, changed), ([D(2026, 10, 7), 40, 3.9], 1, 0))
        rows, _, _ = kf.merge([[D(2026, 10, 7), 40, 3.9, 4.1, 4.35, 4.6]], [stray])       # 저장분도 덮지 않는다
        self.assertEqual(rows[-1][1], 40)
        fixed = {**row(D(2026, 10, 7), 42, y3=3.95), "exact": True}                        # 같은 날짜 제목의 정정 글은 덮는다
        self.assertEqual(kf.merge([], [today, fixed])[0][-1][:3], [D(2026, 10, 7), 42, 3.95])

    def test_two_posts_for_one_new_day_count_once(self):
        self.assertEqual(kf.merge([], [row(D(2026, 10, 7), 40), row(D(2026, 10, 7), 41, y3=3.95)])[1:], (1, 0))

    def test_merge_is_a_no_op_for_the_same_posts(self):
        old = [[D(2026, 10, 6), 20, 3.9, 4.1, 4.35, 4.6]]
        rows, added, changed = kf.merge(old, [row(D(2026, 10, 6), 20)])
        self.assertEqual((rows, added, changed), (old, 0, 0))

    def test_stored_rows_are_validated_on_load(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        good = ["2026-10-06", 20, 3.9, 4.1, 4.35, None]
        with open(os.path.join(tmp, "ktb.json"), "w", encoding="utf-8") as f:
            json.dump({"rows": [good, ["어제", 1, 3.9, 4.1, 4.3, 4.6], ["2026-10-05", "x", 3.9, 4.1, 4.3, 4.6],
                                ["2026-10-04", 2, "=1+1", 4.1, 4.3, 4.6], ["2026-10-03", 3, 3.9, 4.1, 99.0, 4.6],
                                ["2026-10-02", 4, 3.9], "문자열", ["2026-10-01", True, 3.9, 4.1, 4.3, 4.6]]}, f)
        self.assertEqual(kf.load_rows(tmp), [[D(2026, 10, 6), 20, 3.9, 4.1, 4.35, None]])
        self.assertEqual(kf.load_rows(os.path.join(tmp, "없는 폴더")), [])
        with open(os.path.join(tmp, "ktb.json"), "w", encoding="utf-8") as f:
            f.write("{깨진 json")
        self.assertEqual(kf.load_rows(tmp), [])

    def build(self):
        rows = [[D(2026, 10, 5), 10, 3.8, 4.0, 4.2, None], [D(2026, 10, 6), 20, 3.9, 4.1, 4.3, 4.6],
                [D(2026, 10, 7), 30, 3.934, 4.117, 4.372, 4.52]]
        latest = row(D(2026, 10, 7), 30, 3.934, 4.117, 4.372, 4.52, {"3": 0.7, "5": 0.2, "10": 1.5, "30": 1.8})
        return kf.build(rows, latest, NOW)

    def test_output_shape_and_latest_table(self):
        out = self.build()
        self.assertEqual(set(out), {"schema", "date", "updated_at", "source", "notices", "latest", "charts", "rows"})
        self.assertEqual((out["schema"], out["date"]), (kf.SCHEMA, "2026-10-07"))
        self.assertEqual(out["latest"]["post_url"], "https://t.me/jk_bond/30")
        self.assertEqual(out["latest"]["rows"][0], {"tenor": "3년", "yield": 3.934, "change_bp": 0.7})
        self.assertEqual([r["tenor"] for r in out["latest"]["rows"]], ["3년", "5년", "10년", "30년"])
        self.assertEqual(out["latest"]["spreads"], [{"label": "10년−3년", "bp": 43.8}, {"label": "30년−10년", "bp": 14.8}])
        self.assertEqual(out["rows"][-1], ["2026-10-07", 30, 3.934, 4.117, 4.372, 4.52])
        self.assertEqual(out["source"], {"name": kf.SOURCE, "url": kf.CHANNEL_URL, "basis": kf.BASIS})

    def test_latest_without_changes_when_the_newest_row_is_from_the_store(self):
        rows = [[D(2026, 10, 6), 20, 3.9, 4.1, 4.3, 4.6]]
        out = kf.build(rows, None, NOW)                                              # 오늘 글을 못 읽은 날
        self.assertEqual(out["latest"]["rows"][0], {"tenor": "3년", "yield": 3.9, "change_bp": None})
        self.assertEqual(out["date"], "2026-10-06")
        other = row(D(2026, 10, 6), 19)                                              # 같은 날의 다른 글에서 읽은 변화는 붙이지 않는다
        self.assertIsNone(kf.build(rows, other, NOW)["latest"]["rows"][0]["change_bp"])
        self.assertEqual(kf.build(rows, row(D(2026, 10, 6), 20), NOW)["latest"]["rows"][0]["change_bp"], 0.3)

    def test_charts_follow_the_page_contract(self):
        out = self.build()
        self.assertEqual([c["key"] for c in out["charts"]], ["ktb_yields", "ktb_spreads"])
        for c in out["charts"]:
            self.assertEqual(set(c), SPEC_KEYS, c["key"])
            self.assertEqual(c["source_note"].split(" · ")[0], kf.SOURCE_NOTE)
            for ln in c["lines"]:
                self.assertEqual(set(ln), LINE_KEYS)
                self.assertEqual(ln["role"], "series")
                self.assertLessEqual(len(c["lines"]), 3)                              # 분류색은 3개까지
        y, s = out["charts"]
        self.assertEqual([ln["key"] for ln in y["lines"]], ["ktb3", "ktb10", "ktb30"])
        self.assertEqual(y["lines"][0]["points"], [["2026-10-05", 3.8], ["2026-10-06", 3.9], ["2026-10-07", 3.934]])
        self.assertEqual(y["lines"][2]["points"][0], ["2026-10-05", None])            # 30년물 없는 날은 비운다
        self.assertEqual(s["unit"], "bp")
        self.assertEqual(s["lines"][0]["points"][-1], ["2026-10-07", 43.8])           # (4.372 − 3.934) × 100
        self.assertEqual(s["lines"][1]["points"][0], ["2026-10-05", None])
        self.assertTrue(all(ln["derived"] for ln in s["lines"]))
        self.assertIn("계산", s["source_note"])

    def test_charts_keep_only_the_recent_window(self):
        rows = [[D(2020, 1, 2), 1, 1.5, 1.6, 1.7, 1.8], [D(2026, 10, 7), 30, 3.9, 4.1, 4.3, 4.6]]
        out = kf.build(rows, None, NOW)
        self.assertEqual(len(out["charts"][0]["lines"][0]["points"]), 1)
        self.assertEqual(len(out["rows"]), 2)                                        # 저장은 전부

    def test_every_string_in_the_output_is_fixed_text(self):
        # 글에서 온 글자는 하나도 싣지 않는다 — 숫자·날짜·정해 둔 문구·글 주소만
        fixed = set(kf.NOTICES) | {kf.SOURCE, kf.CHANNEL_URL, kf.BASIS, "3년", "5년", "10년", "30년", "10년−3년",
                                   "30년−10년", "%", "bp", "series", "ktb_yields", "ktb_spreads", "ktb3", "ktb10",
                                   "ktb30", "s10_3", "s30_10"}
        fixed |= {c[k] for c in kf.chart_table() for k in ("title", "note") if c[k]}
        fixed |= {ln["label"] for c in kf.chart_table() for ln in c["lines"]}

        def strings(x):
            if isinstance(x, str):
                yield x
            elif isinstance(x, dict):
                for v in x.values():
                    yield from strings(v)
            elif isinstance(x, list):
                for v in x:
                    yield from strings(v)
        for s in strings(self.build()):
            if s in fixed or s.startswith(kf.SOURCE_NOTE) or re.fullmatch(r"\d{4}-\d\d-\d\d(T[\d:+]+)?", s) \
                    or re.fullmatch(r"https://t\.me/jk_bond/\d+", s):
                continue
            self.fail(f"정해 두지 않은 문자열: {s!r}")


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.out = os.path.join(self.tmp, "data")

    def run_main(self, pages, **kw):
        op = FakeOpener(pages, **kw)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = kf.main(["--out", self.out], opener=op, sleep=lambda s: None, now=NOW)
        return code, buf.getvalue(), op

    def saved(self):
        with open(os.path.join(self.out, "ktb.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_first_run_writes_the_file(self):
        code, log, _ = self.run_main([page(daily_post(30, 2026, 10, 7, y3=3.934, y10=4.372, y30=4.52),
                                           daily_post(20, 2026, 10, 6),
                                           post_html(25, morning(2026, 10, 6), ["그냥 뉴스", "국고채 얘기"]))])
        self.assertEqual(code, 0, log)
        data = self.saved()
        self.assertEqual([r[0] for r in data["rows"]], ["2026-10-06", "2026-10-07"])
        self.assertEqual(data["latest"]["rows"][0]["change_bp"], 0.3)
        self.assertNotIn("3.934", log)                                               # 공개 로그에 값은 찍지 않는다
        self.assertIn("2026-10-07", log)

    def test_nothing_new_leaves_the_file_untouched(self):
        pages = [page(daily_post(30, 2026, 10, 7))]
        self.run_main(list(pages))
        before = open(os.path.join(self.out, "ktb.json"), "rb").read()
        later = NOW + datetime.timedelta(days=1)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = kf.main(["--out", self.out], opener=FakeOpener(list(pages)), sleep=lambda s: None, now=later)
        self.assertEqual(code, 0)
        self.assertEqual(open(os.path.join(self.out, "ktb.json"), "rb").read(), before)   # 휴일에 빈 커밋을 만들지 않는다

    def test_fetch_failure_keeps_yesterday(self):
        self.run_main([page(daily_post(30, 2026, 10, 7))])
        before = open(os.path.join(self.out, "ktb.json"), "rb").read()
        code, log, _ = self.run_main([], error=OSError("timed out"))
        self.assertEqual(code, 1)
        self.assertEqual(open(os.path.join(self.out, "ktb.json"), "rb").read(), before)
        self.assertIn("ktb_fetch", log)

    def test_no_daily_post_at_all_is_a_failure(self):
        code, _, _ = self.run_main([page(post_html(1, morning(2026, 10, 7), ["뉴스만 있다"]))])
        self.assertEqual(code, 1)
        self.assertFalse(os.path.exists(os.path.join(self.out, "ktb.json")))

    def test_unreadable_newest_report_fails_but_keeps_what_was_read(self):
        code, log, _ = self.run_main([page(daily_post(30, 2026, 10, 7, basis="민평4사 기준"),
                                           daily_post(20, 2026, 10, 6))])
        self.assertEqual(code, 1, log)                                               # 형식이 바뀐 날을 알아채게
        data = self.saved()
        self.assertEqual([r[0] for r in data["rows"]], ["2026-10-06"])
        self.assertEqual((data["date"], data["latest"]["post_url"]), ("2026-10-06", "https://t.me/jk_bond/20"))
        self.assertNotIn("민평4사", json.dumps(data, ensure_ascii=False) + log)        # 글에서 온 글자는 어디에도 안 나간다

    def test_unreadable_old_report_is_only_a_warning(self):
        code, log, _ = self.run_main([page(daily_post(30, 2026, 10, 7),
                                           daily_post(20, 2026, 10, 6, spreads=(1.0, 1.0)))])
        self.assertEqual(code, 0, log)
        self.assertEqual([r[0] for r in self.saved()["rows"]], ["2026-10-07"])
        self.assertIn("읽지 못한 글 1개", log)

    def test_broken_store_is_never_overwritten(self):
        # 저장분이 깨졌는데 오늘 읽은 한 쪽만으로 다시 쓰면 이력이 조용히 줄어든다(검토)
        os.makedirs(self.out)
        path = os.path.join(self.out, "ktb.json")
        for broken in ("<<<<<<< HEAD\n{}", '{"rows": {"a": 1}}',
                       '{"rows": [["2026-10-05", 10, "3.9", 4.1, 4.3, 4.6], ["2026-10-06", 20, 3.9, 4.1, 4.3, 4.6]]}'):
            with open(path, "w", encoding="utf-8") as f:
                f.write(broken)
            code, log, _ = self.run_main([page(daily_post(30, 2026, 10, 7))])
            self.assertEqual(code, 1, broken)
            self.assertEqual(open(path, encoding="utf-8").read(), broken)
            self.assertIn("ktb_fetch", log)

    def test_a_newer_day_with_a_smaller_post_id_is_refused(self):
        # 채널 이름이 다른 곳으로 넘어가면 글 번호가 처음부터 다시 시작한다(검토)
        self.run_main([page(daily_post(22711, 2026, 10, 7))])
        code, _, _ = self.run_main([page(daily_post(5, 2026, 10, 8, y3=1.0, y5=1.2, y10=1.5, y30=1.7))],
                                   )
        self.assertEqual(code, 1)
        self.assertEqual([r[:2] for r in self.saved()["rows"]], [["2026-10-07", 22711]])

    def test_a_store_gone_stale_is_a_failure(self):
        # 제목 줄이 바뀌면 그 글은 일일동향으로 보이지 않아 '새 글 없음'과 같아진다 — 묵은 저장분으로 알아챈다(검토)
        pages = [page(daily_post(30, 2026, 10, 7))]
        self.run_main(list(pages))
        before = open(os.path.join(self.out, "ktb.json"), "rb").read()
        retitled = post_html(40, morning(2026, 10, 8), ["KB증권", "2026.10.8 채권시장 일일 동향"] + daily_lines(2026, 10, 8)[2:])
        for days, want in ((kf.STALE_DAYS, 0), (kf.STALE_DAYS + 2, 1)):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                code = kf.main(["--out", self.out], opener=FakeOpener([page(retitled, *pages)]), sleep=lambda s: None,
                               now=NOW + datetime.timedelta(days=days))
            self.assertEqual(code, want, (days, buf.getvalue()))
            self.assertEqual(open(os.path.join(self.out, "ktb.json"), "rb").read(), before)

    def test_edited_change_in_the_latest_post_is_picked_up(self):
        self.run_main([page(daily_post(30, 2026, 10, 7, chg=(7, -1.3, -1.7, 0)))])
        self.assertEqual(self.saved()["latest"]["rows"][0]["change_bp"], 7.0)
        code, log, _ = self.run_main([page(daily_post(30, 2026, 10, 7, chg=(0.7, -1.3, -1.7, 0)))])
        self.assertEqual((code, self.saved()["latest"]["rows"][0]["change_bp"]), (0, 0.7))

    def test_latest_change_survives_a_run_that_cannot_reread_the_post(self):
        self.run_main([page(daily_post(30, 2026, 10, 7))])
        before = open(os.path.join(self.out, "ktb.json"), "rb").read()
        code, _, _ = self.run_main([page(daily_post(20, 2026, 10, 6))])               # 그날 글이 쪽에 없다 — 옛 글만 더해진다
        data = self.saved()
        self.assertEqual((code, [r[0] for r in data["rows"]]), (0, ["2026-10-06", "2026-10-07"]))
        self.assertEqual(data["latest"]["rows"][0]["change_bp"], 0.3)                # 지워지지 않는다
        self.assertNotEqual(open(os.path.join(self.out, "ktb.json"), "rb").read(), before)

    def test_changed_fixed_text_is_rewritten_without_new_posts(self):
        self.run_main([page(daily_post(30, 2026, 10, 7))])
        path = os.path.join(self.out, "ktb.json")
        data = self.saved()
        data["notices"] = ["옛 문구"]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        self.run_main([page(daily_post(30, 2026, 10, 7))])
        self.assertEqual(self.saved()["notices"], kf.NOTICES)

    def test_pages_option_is_passed_through(self):
        op = FakeOpener([page(daily_post(30, 2026, 10, 7)), page(daily_post(20, 2026, 10, 6)), page()])
        with contextlib.redirect_stdout(io.StringIO()):
            code = kf.main(["--out", self.out, "--pages", "3"], opener=op, sleep=lambda s: None, now=NOW)
        self.assertEqual((code, len(op.calls)), (0, 3))
        self.assertEqual(len(self.saved()["rows"]), 2)


class StaticTest(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
            return f.read()

    def test_page_reads_the_reference_file_and_links_only_to_the_channel(self):
        page_src = self.read("site", "index.html")
        self.assertIn("data/ktb.json", page_src)
        self.assertIn("t\\.me\\/jk_bond\\/", page_src)                                # 링크 허용 목록은 이 채널의 글 주소만
        for tok in ("innerHTML", "outerHTML", "insertAdjacentHTML"):
            self.assertNotIn(tok, page_src)

    def test_workflow_runs_the_fetch_without_blocking_the_rule_check(self):
        wf = self.read(".github", "workflows", "daily.yml")
        step = wf[wf.index("id: ktb"):]
        self.assertIn("continue-on-error: true", step[:200])
        self.assertIn("python scripts/ktb_fetch.py", step[:300])
        self.assertIn("timeout-minutes: 2", step[:200])                             # 느린 응답이 규칙 점검 배포를 막지 않게
        self.assertIn("ktb: ${{ steps.ktb.outcome }}", wf)
        self.assertIn("needs.update.outputs.ktb == 'failure'", wf)


if __name__ == "__main__":
    unittest.main(verbosity=1)
