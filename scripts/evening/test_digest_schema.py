#!/usr/bin/env python3
"""저녁판 계약(digest_schema · digest_base) 테스트 — 판 날짜와 수집 창, 형태 검증, 닫힌 글자 검사, 예외 때 출력.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요 — 자료는 fixtures.py의 지어낸 글뿐이다. 아침의 "discover -s scripts"는 이 폴더를 줍지 않는다(__init__.py 없음).
"""
import contextlib
import copy
import datetime
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_rules as R
import digest_schema as S
import fixtures as F

KST = S.KST
BAD = F.CANARIES[0]                 # 틀린 값으로 넣어 보는 글자 — 오류 메시지에 나오면 안 된다


def at(day, hh, mm, month=10):
    return datetime.datetime(2026, month, day, hh, mm, tzinfo=KST)


def snap(date, start, end):
    """판 하나의 상태 기록(창만 다르게)."""
    return {"date": date, "window": {"from": S.iso(start), "to": S.iso(end)}, "collected_at": S.iso(end), "empty_streak": 0,
            "must": [], "channels": {}}


def state_of(date, start, end, base=None):
    return {"schema": 1, "edition": snap(date, start, end), "base": base}


class EditionWindowTest(unittest.TestCase):
    def test_edition_is_the_kst_date_six_hours_back(self):
        self.assertEqual(S.edition_date(at(8, 17, 41)), "2026-10-08")
        self.assertEqual(S.edition_date(at(9, 5, 59)), "2026-10-08")          # 새벽까지 밀린 실행도 전날 판
        self.assertEqual(S.edition_date(at(9, 6, 0)), "2026-10-09")
        utc = datetime.datetime(2026, 10, 8, 8, 41, tzinfo=datetime.timezone.utc)   # 예약 cron 41 8 UTC = 17:41 KST
        self.assertEqual(S.edition_date(utc), "2026-10-08")
        self.assertEqual(S.edition_date(datetime.datetime(2026, 10, 8, 21, 30, tzinfo=datetime.timezone.utc)), "2026-10-09")

    def test_time_without_zone_is_refused(self):
        for bad in (datetime.datetime(2026, 10, 8, 17, 41), "2026-10-08T17:41:00+09:00", None):
            with self.assertRaises(ValueError):
                S.edition_date(bad)
        with self.assertRaises(ValueError):
            S.parse_iso("2026-10-08T17:41:00")
        with self.assertRaises(ValueError):
            S.parse_iso("어제 저녁")

    def test_first_run_reads_one_day(self):
        w = S.collect_window(at(8, 18, 7))
        self.assertEqual(w, {"date": "2026-10-08", "from": "2026-10-07T18:07:00+09:00", "to": "2026-10-08T18:07:00+09:00",
                             "kind": "first", "capped": False})
        self.assertEqual(S.collect_window(at(8, 18, 7), {"schema": 1, "edition": None, "base": None})["kind"], "first")

    def test_next_edition_starts_where_the_last_one_ended(self):
        w = S.collect_window(S.parse_iso(F.NOW), F.state())
        self.assertEqual((w["date"], w["from"], w["to"], w["kind"], w["capped"]),
                         (F.EDITION, F.WINDOW["from"], F.WINDOW["to"], "next", False))

    def test_weekend_is_covered_without_hitting_the_cap(self):
        self.assertEqual((datetime.date(2026, 10, 9).weekday(), datetime.date(2026, 10, 12).weekday()), (4, 0))   # 금 · 월
        friday = state_of("2026-10-09", at(8, 17, 50), at(9, 17, 41))
        w = S.collect_window(at(12, 17, 50), friday)
        self.assertEqual((w["date"], w["from"], w["kind"], w["capped"]), ("2026-10-12", "2026-10-09T17:41:00+09:00", "next", False))

    def test_missed_runs_are_capped_at_96_hours(self):
        thursday = state_of("2026-10-08", at(7, 18, 2), at(8, 18, 0))
        w = S.collect_window(at(13, 17, 45), thursday)                      # 금·월을 놓치고 화요일 — 119.75시간 뒤
        self.assertEqual((w["date"], w["from"], w["kind"], w["capped"]), ("2026-10-13", "2026-10-09T17:45:00+09:00", "next", True))

    def test_a_short_edition_does_not_move_the_start(self):
        """수집 부족이던 판은 '여기까지 제대로 읽었다'(read_to)를 앞 판 것 그대로 둔다 — 다음 판이 그날 못 읽은 글부터 다시 읽는다."""
        wed = snap("2026-10-07", at(6, 17, 41), at(7, 17, 41))
        short = {"schema": 1, "edition": {**wed, "read_to": S.iso(at(6, 17, 41))}, "base": None}
        w = S.collect_window(at(8, 17, 41), short)
        self.assertEqual((w["from"], w["kind"], w["capped"]), ("2026-10-06T17:41:00+09:00", "next", False))
        fine = {"schema": 1, "edition": {**wed, "read_to": S.iso(at(7, 17, 41))}, "base": None}
        self.assertEqual(S.collect_window(at(8, 17, 41), fine)["from"], "2026-10-07T17:41:00+09:00")
        self.assertEqual(S.collect_window(at(8, 17, 41), {"schema": 1, "edition": wed, "base": None})["from"],
                         "2026-10-07T17:41:00+09:00")                                    # 칸이 없는 옛 기록은 창의 끝에서
        long_ago = {"schema": 1, "edition": {**wed, "read_to": S.iso(at(2, 17, 41))}, "base": None}
        w = S.collect_window(at(8, 17, 41), long_ago)                                    # 여러 날 못 읽었어도 96시간까지만
        self.assertEqual((w["from"], w["capped"]), ("2026-10-04T17:41:00+09:00", True))
        again = S.collect_window(at(7, 21, 0), short)                                    # 같은 판의 재실행은 첫 실행의 시작점 그대로
        self.assertEqual((again["from"], again["kind"]), (wed["window"]["from"], "rerun"))
        S.validate_state(short)
        with self.assertRaises(ValueError):
            S.validate_state({"schema": 1, "edition": {**wed, "read_to": S.iso(at(7, 18, 0))}, "base": None})   # 창의 끝보다 뒤

    def test_same_edition_rerun_keeps_the_first_start(self):
        first = S.collect_window(at(8, 18, 7), F.state())
        after_first = S.next_state(F.state(), snap(first["date"], S.parse_iso(first["from"]), S.parse_iso(first["to"])))
        for later in (at(8, 19, 30), at(8, 23, 59), at(9, 2, 0), at(9, 5, 59)):          # 새벽 5:59까지 같은 판
            w = S.collect_window(later, after_first)
            self.assertEqual((w["date"], w["from"], w["kind"], w["capped"]), ("2026-10-08", first["from"], "rerun", False))
            self.assertEqual(w["to"], S.iso(later))
        w = S.collect_window(at(9, 6, 30), after_first)                                  # 06:00부터는 다음 판
        self.assertEqual((w["date"], w["from"], w["kind"]), ("2026-10-09", first["to"], "next"))

    def test_rerun_does_not_shrink_a_capped_window(self):
        thursday = state_of("2026-10-08", at(7, 18, 2), at(8, 18, 0))
        first = S.collect_window(at(13, 17, 45), thursday)
        st = S.next_state(thursday, snap(first["date"], S.parse_iso(first["from"]), S.parse_iso(first["to"])))
        again = S.collect_window(at(13, 21, 0), st)                         # 세 시간 뒤 — 상한을 다시 걸면 시작점이 밀린다
        self.assertEqual((again["from"], again["kind"], again["capped"]), (first["from"], "rerun", False))

    def test_state_from_the_future_is_treated_as_first_run(self):
        later = state_of("2026-10-12", at(9, 17, 41), at(12, 17, 50))
        w = S.collect_window(at(8, 18, 7), later)                           # --now로 시각을 되돌린 재실행
        self.assertEqual((w["kind"], w["from"]), ("first", "2026-10-07T18:07:00+09:00"))
        same_day = state_of("2026-10-08", at(8, 20, 0), at(8, 21, 0))
        self.assertEqual(S.collect_window(at(8, 18, 7), same_day)["kind"], "first")       # 시작점이 지금보다 뒤

    def test_window_is_pure_and_repeatable(self):
        st = F.state()
        before = copy.deepcopy(st)
        self.assertEqual(S.collect_window(S.parse_iso(F.NOW), st), S.collect_window(S.parse_iso(F.NOW), st))
        self.assertEqual(st, before)

    def test_events_follow_the_window_not_the_calendar_day(self):
        monday = {"from": "2026-10-09T17:41:00+09:00", "to": "2026-10-12T17:50:00+09:00"}
        self.assertTrue(S.in_window(monday, "2026-10-09", "21:30"))         # 금요일 밤 미국 지표는 월요일 판이 센다
        self.assertFalse(S.in_window(monday, "2026-10-09", "17:41"))        # 시작 시각은 지난 판의 것
        self.assertTrue(S.in_window(monday, "2026-10-12", "17:50"))
        self.assertFalse(S.in_window(monday, "2026-10-12", "21:30"))
        self.assertTrue(S.in_window(monday, "2026-10-10"))                  # 시각이 없으면 날짜가 걸치는지만
        self.assertFalse(S.in_window(monday, "2026-10-13"))

    def test_rates_count_only_when_their_close_is_inside_the_window(self):
        w = F.WINDOW                                                         # 10-07 18:02 ~ 10-08 18:07
        self.assertFalse(S.rate_fits("kr", "2026-10-07", w))                # 전일 종가(10-07 16:00)는 창 앞
        self.assertTrue(S.rate_fits("kr", "2026-10-08", w))
        self.assertTrue(S.rate_fits("us", "2026-10-07", w))                 # 미국 10-07 마감 = 한국 10-08 아침
        self.assertFalse(S.rate_fits("us", "2026-10-06", w))
        self.assertFalse(S.rate_fits("us", "2026-10-08", w))


class StateTest(unittest.TestCase):
    def test_new_edition_pushes_the_old_one_down(self):
        old = F.state()
        new = S.next_state(old, snap("2026-10-08", at(7, 18, 2), at(8, 18, 7)))
        self.assertEqual((new["edition"]["date"], new["base"]["date"]), ("2026-10-08", "2026-10-07"))
        self.assertEqual(new["base"], old["edition"])
        S.validate_state(new)

    def test_rerun_keeps_comparing_with_the_edition_before(self):
        once = S.next_state(F.state(), snap("2026-10-08", at(7, 18, 2), at(8, 18, 7)))
        twice = S.next_state(once, snap("2026-10-08", at(7, 18, 2), at(8, 20, 0)))
        self.assertEqual(twice["base"], once["base"])                        # '어제'는 그대로 10-07
        self.assertEqual(S.state_base(once, "2026-10-08")["date"], "2026-10-07")
        self.assertEqual(S.state_base(once, "2026-10-09")["date"], "2026-10-08")
        self.assertIsNone(S.state_base(once, "2026-10-07"))                  # 상태보다 앞선 날짜
        self.assertIsNone(S.state_base(None, "2026-10-08"))

    def test_state_functions_return_copies(self):
        old = F.state()
        before = copy.deepcopy(old)
        s = snap("2026-10-08", at(7, 18, 2), at(8, 18, 7))
        new = S.next_state(old, s)
        new["base"]["must"].append("x")
        new["edition"]["channels"]["fxbond1"] = {}
        S.state_base(old, "2026-10-08")["channels"].clear()
        self.assertEqual(old, before)
        self.assertEqual(s["channels"], {})

    def test_state_shape(self):
        S.validate_state(F.state())
        S.validate_state(F.state_after())
        S.validate_state({"schema": 1, "edition": None, "base": None})
        bad = F.state_after()
        bad["base"]["date"] = bad["edition"]["date"]
        with self.assertRaises(ValueError):
            S.validate_state(bad)
        bad = F.state()
        bad["edition"]["channels"][BAD] = {"last_post": 1, "last_at": None, "fail_streak": 0}
        with self.assertRaises(ValueError) as e:
            S.validate_state(bad)
        self.assertEqual(F.leaks(str(e.exception)), [])


class BuildersTest(unittest.TestCase):
    def test_url_and_id_are_built_from_handle_and_number_only(self):
        self.assertEqual(S.post_url("yieldnspread", 1234), "https://t.me/yieldnspread/1234")
        self.assertEqual(S.item_id("2026-10-08", "yieldnspread", 1234), "20261008-yieldnspread-1234")
        for ch, post in (("a/b", 1), ("abc", 1), ("x" * 33, 1), ("good_name", 0), ("good_name", "12"), ("good_name", True),
                         ("https://evil.example", 3), (None, 1)):
            with self.assertRaises(ValueError):
                S.post_url(ch, post)
        with self.assertRaises(ValueError):
            S.item_id("20261008", "yieldnspread", 1)
        self.assertTrue(S.URL_RE.match(S.post_url("jk_bond", 5)) and S.ID_RE.match(S.item_id("2026-10-08", "jk_bond", 5)))

    def test_keys_are_hashes_and_priority_is_fixed(self):
        k = S.key_of("u", "https://news.example.com/a")
        self.assertRegex(k, r"^u:[0-9a-f]{12}$")
        self.assertEqual(k, S.key_of("u", "https://news.example.com/a"))
        self.assertNotEqual(k, S.key_of("t", "https://news.example.com/a"))
        self.assertEqual(F.leaks(S.key_of("t", BAD)), [])
        for kind, material in (("x", "a"), ("u", ""), ("u", None)):
            with self.assertRaises(ValueError):
                S.key_of(kind, material)
        keys = [S.key_of(kind, "m") for kind in ("g", "k", "n", "t", "u", "f")]
        self.assertEqual(S.primary_key(keys)[0], "f")
        self.assertEqual(S.primary_key(keys[:3])[0], "n")
        with self.assertRaises(ValueError):
            S.primary_key([])

    def test_title_hash_reads_the_preview_title(self):
        page = F.render_page("fxbond1")
        self.assertEqual(S.page_title(page), F.TITLE["fxbond1"])
        self.assertEqual(S.title_sha(S.page_title(page)), S.title_sha("  " + F.TITLE["fxbond1"].replace(" ", " \n ") + " "))
        self.assertRegex(S.title_sha(F.TITLE["fxbond1"]), r"^[0-9a-f]{16}$")
        self.assertNotEqual(S.title_sha(F.TITLE["fxbond1"]), S.title_sha(F.TITLE["fxbond2"]))
        self.assertIsNone(S.page_title("<html><head><title>제목 표식 없음</title></head></html>"))

    def test_seed_is_the_earliest_source_post(self):
        c = next(c for c in F.clusters_doc()["clusters"] if len(c["members"]) == 9)
        self.assertEqual(c["members"][0]["ch"], "fxwire1")                   # 가장 이른 글은 속보형이지만
        self.assertEqual(S.seed_of(c["members"]), {"ch": "fxbond1", "id": 501})          # 씨앗은 가장 이른 원천 글
        wire_only = [m for m in c["members"] if m["role"] == "wire"]
        self.assertEqual(S.seed_of(wire_only), {"ch": "fxwire1", "id": 90011})

    def test_link_order_rule(self):
        c = next(c for c in F.clusters_doc()["clusters"] if len(c["members"]) == 9)
        before = copy.deepcopy(c["members"])
        links = S.pick_links(c["members"])
        self.assertEqual([x["ch"] for x in links], ["fxbond1", "fxbond2", "fxbond3", "fxanal2", "fxpers2", "fxpers3"])
        self.assertEqual(c["members"], before)
        self.assertTrue(all(x["url"] == f"https://t.me/{x['ch']}/{x['url'].rsplit('/', 1)[1]}" and not x["fwd"] for x in links))
        wide = S.pick_links(c["members"], limit=20, personal_max=9)          # 전달 글은 맨 뒤, 속보형은 없다
        self.assertEqual([x["ch"] for x in wide],
                         ["fxbond1", "fxbond2", "fxbond3", "fxanal2", "fxpers2", "fxpers3", "fxanal1", "fxpers1"])
        self.assertEqual([x["fwd"] for x in wide], [False] * 6 + [True] * 2)
        self.assertEqual([x["ch"] for x in S.pick_links(c["members"], limit=2)], ["fxbond1", "fxbond2"])
        capped = [x["ch"] for x in S.pick_links(c["members"], limit=20)]     # 개인 채널은 2개까지 — 셋째(fxpers1)는 빠진다
        self.assertEqual(capped, ["fxbond1", "fxbond2", "fxbond3", "fxanal2", "fxpers2", "fxpers3", "fxanal1"])
        twice = c["members"] + [{**c["members"][1], "id": 9999, "at": "2026-10-08T10:00:00+09:00"}]
        self.assertEqual(len(S.pick_links(twice, limit=20, personal_max=9)), 8)          # 한 채널에 링크 하나(이른 글)

    def test_coverage_verdict(self):
        rows = F.collect_status()["channels"]
        self.assertEqual(S.coverage_verdict(rows)["verdict"], "ok")
        self.assertEqual(S.coverage_verdict(rows)["channels_total"], 24)
        three_bonds = F.collect_status(fail={"fxbond1": "fetch", "fxbond2": "fetch", "fxbond3": "title"})["channels"]
        self.assertEqual((S.coverage_verdict(three_bonds)["verdict"], S.coverage_verdict(three_bonds)["bond_ok"]), ("short", 2))
        two_bonds = F.collect_status(fail={"fxbond1": "fetch", "fxbond2": "fetch"})["channels"]
        self.assertEqual(S.coverage_verdict(two_bonds)["verdict"], "ok")     # 채권 3곳이면 통과
        nine = F.collect_status(fail={ch: "fetch" for ch in F.REQUESTED[5:14]})["channels"]
        self.assertEqual((S.coverage_verdict(nine)["verdict"], S.coverage_verdict(nine)["channels_ok"]), ("short", 15))
        no_text = [{**r, "with_text": r["posts"] // 3} for r in rows]       # 글은 읽히는데 본문이 비었다 — 형식이 바뀐 것
        self.assertEqual(S.coverage_verdict(no_text)["verdict"], "broken")


class ShapesTest(unittest.TestCase):
    """단계별 예시가 계약을 통과하고, 어긋난 것은 값 없이 거절되는지."""

    def refuse(self, validate, doc, *extra):
        with self.assertRaises(ValueError) as e:
            validate(doc, *extra)
        self.assertEqual(F.leaks(str(e.exception)), [], "오류 메시지에 값이 실렸다")
        return str(e.exception)

    def test_every_sample_is_valid(self):
        S.validate_sources(F.sources())
        S.validate_calendar(F.calendar())
        S.validate_overrides(F.overrides(hide_ids=["20261008-fxbond1-501"], hide_channels=["fxpers5"]))
        S.validate_posts_doc(F.posts_doc())
        S.validate_collect_status(F.collect_status())
        S.validate_manifest(F.manifest())
        S.validate_clusters_doc(F.clusters_doc())
        S.validate_scored_doc(F.scored_doc())
        S.validate_digest(F.digest(), F.sources())
        S.validate_index(F.index())
        S.validate_status(F.status())
        for p in F.all_posts():
            S.validate_post(p)
        for c in F.scored_doc()["clusters"]:
            S.validate_scored(c)
            S.validate_cluster({k: v for k, v in c.items() if k in ("seed", "key", "keys", "first_at", "last_at", "cell", "terms",
                                                                    "results", "nums", "members")})

    def test_validators_return_the_document_untouched(self):
        d = F.digest()
        before = copy.deepcopy(d)
        self.assertIs(S.validate_digest(d, F.sources()), d)
        self.assertEqual(d, before)

    def test_validator_lookup(self):
        self.assertIs(S.validator_for("digest.json"), S.validate_digest)
        self.assertIs(S.validator_for("digest/2026-10-08.json"), S.validate_digest)
        self.assertIs(S.validator_for("digest\\2026-10-08.json"), S.validate_digest)
        self.assertIs(S.validator_for("pages/manifest.json"), S.validate_manifest)
        for name in S.PUBLIC_FILES + S.HUMAN_FILES:
            self.assertTrue(callable(S.validator_for(name)))
        for name in ("korea.json", "digest/latest.json", "../digest.json", "digest_picks.json"):
            with self.assertRaises(ValueError):
                S.validator_for(name)

    def test_post_shape(self):
        p = F.posts()[0]
        for bad in ({**p, "at": "2026-10-08T07:12:00Z"}, {**p, "at": "2026-10-08 07:12"}, {**p, "id": 0}, {**p, "id": "12"},
                    {**p, "ch": "t.me/x"}, {**p, "extra": 1}, {k: v for k, v in p.items() if k != "via"}, {**p, "text": None},
                    {**p, "links": "https://a.example"}, {**p, "fwd": {"ch": "fxbond1"}}, {**p, "via": "api"}, [p], None):
            self.refuse(S.validate_post, bad)

    def test_posts_doc_must_be_in_window_sorted_and_unique(self):
        d = F.posts_doc()
        self.refuse(S.validate_posts_doc, {**d, "posts": d["posts"] + [F.old_posts()[0]]})
        self.refuse(S.validate_posts_doc, {**d, "posts": d["posts"][::-1]})
        self.refuse(S.validate_posts_doc, {**d, "posts": d["posts"] + [d["posts"][-1]]})
        self.refuse(S.validate_posts_doc, {**d, "edition": "2026-10-07"})
        self.refuse(S.validate_posts_doc, {**d, "window": {"from": d["window"]["to"], "to": d["window"]["from"]}})
        self.refuse(S.validate_posts_doc, {**d, "window": {"from": "2026-10-01T18:07:00+09:00", "to": d["window"]["to"]}})
        S.validate_posts_doc({**d, "collected_at": "2026-10-09T00:07:00+09:00"})        # 수집 시각은 창의 끝에서 6시간 안
        self.refuse(S.validate_posts_doc, {**d, "collected_at": "2026-10-09T00:08:00+09:00"})
        self.refuse(S.validate_posts_doc, {**d, "collected_at": "2026-10-08T18:06:00+09:00"})    # 창의 끝보다 앞설 수도 없다

    def test_collect_status_must_agree_with_its_numbers(self):
        d = F.collect_status()
        self.refuse(S.validate_collect_status, {**d, "verdict": "short"})
        short = F.collect_status(fail={"fxbond1": "fetch", "fxbond2": "fetch", "fxbond3": "title"})
        self.assertEqual(S.validate_collect_status(short)["verdict"], "short")
        rows = copy.deepcopy(d["channels"])
        rows[0]["code"] = "fetch"                                             # ok인데 실패 코드
        self.refuse(S.validate_collect_status, {**d, "channels": rows})
        rows = copy.deepcopy(d["channels"])
        rows[0]["with_text"] = rows[0]["posts"] + 1
        self.refuse(S.validate_collect_status, {**d, "channels": rows})
        self.refuse(S.validate_collect_status, {**d, "channels": d["channels"] + [d["channels"][0]]})
        off = {**d["channels"][0], "ch": "fxoff1", "role": "off"}
        self.refuse(S.validate_collect_status, {**d, "channels": d["channels"] + [off]})

    def test_cluster_holds_closed_values_only(self):
        doc = F.clusters_doc()

        def with_member(**change):
            d = copy.deepcopy(doc)
            d["clusters"][0]["members"][0].update(change)
            return d
        for change in ({"terms": [BAD]}, {"lead": [BAD]}, {"results": ["대폭 상회"]}, {"nums": ["약 3%"]}, {"nums": ["3.10%"]},
                       {"lead_nums": ["9.9%"]}, {"lead": ["FOMC"]}, {"text": BAD}, {"group": "채권"}, {"role": "owner"}):
            self.refuse(S.validate_clusters_doc, with_member(**change))
        for field, value in (("key", "u:" + "0" * 12), ("keys", ["u:" + BAD]), ("seed", {"ch": "fxwire1", "id": 90011}),
                             ("cell", None), ("first_at", "2026-10-07T18:03:00+09:00"),
                             ("terms", [{"term": "미 CPI", "n_ch": 10}]),
                             ("nums", [{"term": "미 CPI", "result": None, "v": "3.1%", "n_ch": 1}])):
            d = copy.deepcopy(doc)
            big = next(c for c in d["clusters"] if len(c["members"]) == 9)
            big[field] = value
            self.refuse(S.validate_clusters_doc, d)

    def test_cluster_doc_counts_every_post_once(self):
        doc = F.clusters_doc()
        d = copy.deepcopy(doc)
        d["clusters"][1]["members"].append(d["clusters"][0]["members"][0])
        self.refuse(S.validate_clusters_doc, d)
        self.refuse(S.validate_clusters_doc, {**doc, "stats": {**doc["stats"], "kept": doc["stats"]["kept"] + 1}})
        self.refuse(S.validate_clusters_doc, {**doc, "clusters": doc["clusters"][1:]})
        self.assertEqual(doc["stats"], {"posts": 41, "kept": 36, "dropped": {"empty": 1, "short": 1, "ad": 1, "coin": 1, "filing": 1}})

    def test_scored_doc_rules(self):
        doc = F.scored_doc()

        def with_cluster(which, **change):
            d = copy.deepcopy(doc)
            c = next(c for c in d["clusters"] if c["pick"] == which)
            for k, v in change.items():
                c[k] = {**c[k], **v} if isinstance(v, dict) else v
            return d
        self.refuse(S.validate_scored_doc, with_cluster("must", score={"total": 99}))
        self.refuse(S.validate_scored_doc, with_cluster("must", score={"total": 1.0}))             # 합과 다르다
        self.refuse(S.validate_scored_doc, with_cluster("must", score={"C": 8.0}))                 # 상한 밖
        self.refuse(S.validate_scored_doc, with_cluster("must", rank=None))
        self.refuse(S.validate_scored_doc, with_cluster("rest", rank=3))
        self.refuse(S.validate_scored_doc, with_cluster("rest", pick="must", rank=4))
        self.refuse(S.validate_scored_doc, with_cluster("must", gate={"pass": True, "fails": ["score"]}))
        self.refuse(S.validate_scored_doc, with_cluster("must", why=[BAD]))
        self.refuse(S.validate_scored_doc, with_cluster("must", why=["채권 채널 세 곳"]))
        self.refuse(S.validate_scored_doc, {**doc, "head": {**doc["head"], "kr10": {**doc["head"]["kr10"], "fits": False}}})
        gap = copy.deepcopy(doc)
        next(c for c in gap["clusters"] if c["rank"] == 2)["rank"] = 3                              # 순위가 겹친다
        self.refuse(S.validate_scored_doc, gap)

    def test_digest_refusals(self):
        src, good = F.sources(), F.digest()

        def change(path, value):
            d = copy.deepcopy(good)
            node = d
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = value
            return d
        link = good["must"][0]["links"][0]
        cases = {
            "모르는 칸": change(["debug"], 1),
            "원문 칸": change(["must", 0, "text"], BAD),
            "사전에 없는 낱말": change(["must", 0, "terms"], [BAD]),
            "지어 쓴 이유": change(["must", 0, "why"], ["채권 채널 3곳이 다뤘습니다"]),
            "숫자가 아닌 값": change(["must", 0, "nums", 0, "v"], "3.1% 상회"),
            "바깥 주소": change(["must", 0, "links", 0, "url"], "https://" + F.CANARIES[6]),
            "주소와 채널이 다름": change(["must", 0, "links", 0, "url"], "https://t.me/fxbond2/501"),
            "링크 7개": change(["must", 0, "links"], [link] * 7),
            "한 채널 두 링크": change(["must", 0, "links"], [link, {**link, "url": "https://t.me/fxbond1/502"}]),
            "창 밖의 글": change(["must", 0, "links", 0, "at"], "2026-10-07T09:00:00+09:00"),
            "꼭 볼 것 4건": change(["must"], good["must"] + [good["must"][0]]),
            "개수 불일치": change(["funnel", "must"], 2),
            "id 날짜 불일치": change(["must", 0, "id"], "20261007-fxbond1-501"),
            "점수 합 불일치": change(["must", 0, "score", "total"], 12.0),
            "수집 부족인데 꼭 볼 것": change(["status"], "short"),
            "내린 판인데 내용": change(["status"], "withdrawn"),
            "칸 불일치": change(["rest", 0, "cell"], "수급/국내"),
            "방향 표시": change(["head", "kr10", "fits"], False),
            "금리 범위": change(["head", "us10", "value"], 20.0),
            "판 날짜 불일치": change(["date"], "2026-10-07"),
            "유튜브 켜짐": change(["youtube", "enabled"], True),
            "모드": change(["mode"], "ai"),
            "채널당 6줄": change(["wire", "rows"], good["wire"]["rows"] + [good["wire"]["rows"][0]]),
            "줄의 채널이 목록에 없음": change(["solo", "channels"], good["solo"]["channels"][:1]),
            "내일 볼 것의 낱말": change(["tomorrow", 0, "term"], "미국 생산자물가 발표"),
            "내일 볼 것의 덧붙임": change(["tomorrow", 1, "detail"], ["3년물 2.4조 입찰"]),
            "알림 줄": change(["notes"], ["오늘은 좋은 날"]),
        }
        for name, bad in cases.items():
            with self.subTest(name):
                self.refuse(S.validate_digest, bad, src)

    def test_digest_role_rules_need_the_source_list(self):
        src, good = F.sources(), F.digest()
        links = good["must"][0]["links"]
        cases = {
            "속보형 채널 링크": [{**links[0], "ch": "fxwire1", "url": "https://t.me/fxwire1/90011"}] + links[1:],
            "목록에 없는 채널": [{**links[0], "ch": "nobody_here", "url": "https://t.me/nobody_here/5"}] + links[1:],
            "애널이 채권보다 앞": [links[3]] + links[:3] + links[4:],
            "전달 글이 앞": [{**links[0], "fwd": True}] + links[1:],
            "개인 링크 3개": links[:3] + [{**links[4], "ch": f"fxpers{i}", "url": f"https://t.me/fxpers{i}/9"} for i in (2, 3, 4)],
        }
        for name, bad_links in cases.items():
            with self.subTest(name):
                d = copy.deepcopy(good)
                d["must"][0]["links"] = bad_links
                self.refuse(S.validate_digest, d, src)
        d = copy.deepcopy(good)
        d["must"][0]["links"] = cases["애널이 채권보다 앞"]
        S.validate_digest(d)                                                 # 목록 없이는 꼴만 본다
        d = copy.deepcopy(good)
        d["context"][0].update(ch="fxbond1", url="https://t.me/fxbond1/502")
        self.refuse(S.validate_digest, d, src)
        d = copy.deepcopy(good)
        d["solo"]["channels"].append({"ch": "fxwire2", "read": 1, "joined": 1, "hit": 0})
        self.refuse(S.validate_digest, d, src)

    def test_direction_is_blank_unless_the_rate_date_fits(self):
        good = F.digest()

        def with_head(**change):
            d = copy.deepcopy(good)
            for k, v in change.items():
                d["head"][k] = {**d["head"][k], **v} if isinstance(v, dict) else v
            return d
        stale = {"kr10": {"asof": "2026-10-07", "fits": False}, "kr3": {"asof": "2026-10-07", "fits": False}, "basis": "전일 종가"}
        self.refuse(S.validate_digest, with_head(**stale))                                  # 방향·커브가 남아 있다
        self.refuse(S.validate_digest, with_head(**stale, curve=None))
        self.refuse(S.validate_digest, with_head(**stale, dir=None))
        S.validate_digest(with_head(**stale, dir=None, curve=None))
        self.refuse(S.validate_digest, with_head(**{**stale, "basis": "당일 종가"}, dir=None, curve=None))
        self.refuse(S.validate_digest, with_head(kr3={"fits": False}))                      # 3년이 안 맞으면 커브도 비운다
        S.validate_digest(with_head(kr3={"fits": False}, curve=None))
        S.validate_digest(with_head(kr10=None, kr3=None, us10=None, dir=None, curve=None, basis=None, top_terms=[]))
        self.refuse(S.validate_digest, with_head(kr10=None, kr3=None, dir=None, curve=None))            # 금리가 없는데 기준 표시

    def test_digest_size_limit(self):
        old = R.TH["bytes_max"]
        R.TH["bytes_max"] = 2_000
        try:
            self.refuse(S.validate_digest, F.digest())
        finally:
            R.TH["bytes_max"] = old
        self.assertLess(len(S.dump(F.digest()).encode("utf-8")), R.TH["bytes_max"])

    def test_blank_digest_is_a_valid_withdrawn_edition(self):
        d = S.blank_digest(S.parse_iso(F.NOW))
        S.validate_digest(d, F.sources())
        self.assertEqual((d["status"], d["date"], d["must"], d["notes"]), ("withdrawn", F.EDITION, [], [R.phrase("note_withdrawn")]))
        self.assertEqual(S.closed_violations(d), [])

    def test_small_public_shapes(self):
        idx = F.index()
        self.refuse(S.validate_index, {**idx, "editions": idx["editions"][::-1]})
        self.refuse(S.validate_index, {**idx, "latest": "2026-10-07"})
        self.refuse(S.validate_index, {**idx, "editions": idx["editions"] + [idx["editions"][-1]]})
        S.validate_index({"schema": 1, "updated_at": F.COLLECTED, "latest": None, "editions": []})
        # 한도 숫자(TH must_max · rest_max · c_cap)를 낮춘 날에도 지난 목차·상태 기록은 읽혀야 한다 — 쌓인 기록의 상한은 넉넉한 고정값
        row = {**idx["editions"][0], "must": R.TH["must_max"] + 2, "rest": R.TH["rest_max"] + 50}
        S.validate_index({**idx, "editions": [row] + idx["editions"][1:]})
        old = F.state_after()
        old["edition"]["must"] = [{"id": f"20261008-fxbond1-{i + 1}", "keys": [S.key_of("g", str(i))], "c": R.TH["c_cap"] + 1}
                                  for i in range(R.TH["must_max"] + 2)]
        S.validate_state(old)
        st = F.status()
        self.refuse(S.validate_status, {**st, "reason": "short"})
        self.refuse(S.validate_status, {**st, "counts": {**st["counts"], "channels_ok": 23}})
        self.refuse(S.validate_status, {**st, "reason": BAD})
        S.validate_status({**st, "ok": False, "reason": "broken", "published": False})
        cal = F.calendar()
        self.refuse(S.validate_calendar, {**cal, "events": [{"date": "2026-10-14", "term": "미국 물가 발표", "tier": "A"}]})
        self.refuse(S.validate_calendar, {**cal, "events": [{"date": "2026-02-30", "term": "미 CPI", "tier": "A"}]})
        self.refuse(S.validate_calendar, {**cal, "events": [{"date": "2026-10-14", "time": "25:00", "term": "미 CPI", "tier": "A"}]})
        self.refuse(S.validate_calendar, {**cal, "events": [{"date": "2026-10-14", "term": "미 CPI", "tier": "C"}]})
        self.refuse(S.validate_overrides, F.overrides(hide_ids=[BAD]))
        self.refuse(S.validate_overrides, F.overrides(withdraw="yes"))
        S.validate_overrides(F.overrides(withdraw=True))

    def test_sources_shape(self):
        src = F.sources()

        def with_channel(i, **change):
            d = copy.deepcopy(src)
            d["channels"][i].update(change)
            return d
        self.refuse(S.validate_sources, with_channel(1, handle="FXBOND1"))                # 대소문자만 다른 같은 이름
        self.refuse(S.validate_sources, with_channel(0, title_sha=None))
        self.refuse(S.validate_sources, with_channel(len(src["channels"]) - 1, title_sha="0" * 16))      # off인데 해시
        self.refuse(S.validate_sources, with_channel(0, group="bonds"))
        for label in ("", " 앞뒤 공백 ", "x" * 41, "https://t.me/x", "<b>굵게</b>", "@handle", F.CANARIES[4], "줄\n바꿈"):
            self.refuse(S.validate_sources, with_channel(0, label=label))
        self.refuse(S.validate_sources, {**src, "groups": src["groups"][::-1]})
        self.refuse(S.validate_sources, {**src, "roles": [{**src["roles"][0], "label": "소스"}] + src["roles"][1:]})
        self.refuse(S.validate_sources, {**src, "youtube": [{"id": "x"}]})
        self.assertEqual(len(S.handles_of(src)), 24)
        self.assertEqual(S.handles_of(src, ["wire"]), {"fxwire1", "fxwire2"})
        self.assertNotIn("fxoff1", S.handles_of(src))


class ClosedTextTest(unittest.TestCase):
    """공개본의 모든 문자열이 허용 목록으로 다시 조립되는가 — 규칙판의 글자 검사는 이것 하나다."""

    def setUp(self):
        self.handles = S.handles_of(F.sources())

    def test_samples_are_closed_and_carry_no_planted_text(self):
        docs = {"digest": F.digest(), "index": F.index(), "status": F.status(), "state": F.state_after(), "calendar": F.calendar(),
                "overrides": F.overrides(hide_ids=["20261008-fxbond1-501"]), "clusters": F.clusters_doc(), "scored": F.scored_doc()}
        for name, doc in docs.items():
            with self.subTest(name):
                self.assertEqual(S.closed_violations(doc, self.handles), [])
                self.assertEqual(F.leaks(S.dump(doc)), [])
                self.assertEqual(F.leaks(json.dumps(doc)), [])                # \\u 이스케이프로 써도 없다
        self.assertEqual(F.leaks(S.dump(F.posts_doc())), list(range(len(F.CANARIES))))    # 원문에는 전부 들어 있다

    def test_anything_outside_the_list_is_reported_by_place_only(self):
        d = F.digest()
        d["must"][0]["terms"][0] = F.CANARIES[0]
        d["must"][0]["links"][0]["url"] = "https://t.me/someone_else/77"
        d["must"][1][F.CANARIES[2]] = 1
        d["rest"][0]["items"][0]["note"] = "ok"
        d["head"]["top_terms"].append("미 CPI 3.1% 상회")
        d["wire"]["rows"][0]["at"] = "어젯밤"
        d["funnel"]["posts"] = [1.5, None, True, {"x": b"raw"}]
        got = S.closed_violations(d, self.handles)
        self.assertEqual(sorted(got), sorted([
            "$.must[0].terms[0]", "$.must[0].links[0].url", "$.must[1].<정해지지 않은 칸>", "$.rest[0].items[0].<정해지지 않은 칸>",
            "$.head.top_terms[3]", "$.wire.rows[0].at", "$.funnel.posts[3].<정해지지 않은 칸>"]))
        self.assertEqual(F.leaks(" ".join(got)), [])

    def test_handles_and_labels_count_only_when_given(self):
        url, item = "https://t.me/fxbond1/501", "20261008-fxbond1-501"
        self.assertTrue(S.is_closed(url, self.handles) and S.is_closed(item, self.handles) and S.is_closed("fxbond1", self.handles))
        self.assertFalse(S.is_closed(url) or S.is_closed(item) or S.is_closed("fxbond1"))
        self.assertFalse(S.is_closed("https://t.me/fxoff1/3", self.handles))                # 요청하지 않는 채널
        self.assertFalse(S.is_closed("https://t.me/s/fxbond1/501", self.handles))
        self.assertFalse(S.is_closed("https://t.me/fxbond1/501?x=1", self.handles))
        src = F.sources()
        labels = [c["label"] for c in src["channels"]] + list(R.GROUPS.values()) + list(R.ROLES.values())
        self.assertEqual(S.closed_violations(src, S.handles_of(src, list(R.ROLES)), labels), [])
        self.assertEqual(len(S.closed_violations(src, S.handles_of(src, list(R.ROLES)))), 25 + 3 + 5)        # 라벨을 주지 않으면 전부 걸린다

    def test_closed_words(self):
        for s in ("미 CPI", "상회", "3.1%", "-4bp", "2.8조원", "채권 채널 3곳", "통화정책", "국내", "수급/국내", "기타", "30년", "물가채",
                  "2026-10-08", "2026-10-08T18:07:00+09:00", "21:30", "u:9f2c1a7b03de", "1a3b9196792571c7", "rules", "must", "ok"):
            self.assertTrue(S.is_closed(s), s)
        for s in ("미 CPI 상회", "3.1 %", "약 3%", "채권 채널 3곳 이상", "2026-10-08T18:07:00Z", "2026/10/08", "x:9f2c1a7b03de",
                  "가짜 문장", "", " ", "미 CPI\n", "2026-10-08\n", "3.1%\n", "21:30\n", "채권 채널 3곳\n", "u:9f2c1a7b03de\n",
                  "https://example.com/a", "https://t.me/fxbond1/501"):
            self.assertFalse(S.is_closed(s), repr(s))
        self.assertFalse(S.is_closed("https://t.me/fxbond1/501\n", self.handles))             # 끝에 줄바꿈을 붙여도 안 된다

    def test_digits_of_other_scripts_are_never_closed(self):
        """날짜 · 시각 · 주소 · id · 숫자 · 고정 문구 어느 꼴에도 다른 문자의 숫자 글자(아라비아-인도 · 타이 숫자 등)는 들어갈 수 없다."""
        odd = chr(0x0663)
        for s in (f"3.{odd}5%", f"2026-10-0{odd}", f"2{odd}:30", f"2026-10-08T18:0{odd}:00+09:00", f"https://t.me/fxbond1/50{odd}",
                  f"2026100{odd}-fxbond1-501", f"20261008-fxbond1-50{odd}", f"채권 채널 {odd}곳", f"1{odd}bp"):
            self.assertFalse(S.is_closed(s, self.handles), ascii(s))
        self.assertFalse(S.PAGE_FILE_RE.fullmatch(f"fxbond1-{odd}.html"))
        with self.assertRaises(ValueError):
            S.validator_for(f"digest/2026-10-0{odd}.json")
        d = F.digest()
        d["wire"]["rows"][0]["v"] = f"0.{odd}%"
        self.assertEqual(S.closed_violations(d, self.handles), ["$.wire.rows[0].v"])


class CliGuardTest(unittest.TestCase):
    def run_cli(self, main):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = S.run_cli("digest_test", main)
        return code, out.getvalue(), err.getvalue()

    def test_exception_prints_its_kind_only(self):
        def boom(argv):
            raise RuntimeError(f"본문 조각이 든 메시지: {F.CANARIES[0]} {F.CANARIES[2]}")
        code, out, err = self.run_cli(boom)
        self.assertEqual((code, out, err), (1, "", "[digest_test] 실패: RuntimeError\n"))
        self.assertEqual(F.leaks(err), [])

    def test_validation_error_and_key_error_stay_quiet(self):
        def bad_doc(argv):
            S.validate_digest({**F.digest(), F.CANARIES[1]: F.CANARIES[3]})

        def bad_key(argv):
            return {}[F.CANARIES[0]]
        for main, kind in ((bad_doc, "ValueError"), (bad_key, "KeyError")):
            code, out, err = self.run_cli(main)
            self.assertEqual((code, out, err), (1, "", f"[digest_test] 실패: {kind}\n"))

    def test_exit_codes_pass_through(self):
        self.assertEqual(self.run_cli(lambda argv: None)[0], 0)
        self.assertEqual(self.run_cli(lambda argv: 2)[0], 2)
        self.assertEqual(self.run_cli(lambda argv: 3)[0], 3)
        self.assertEqual(self.run_cli(lambda argv: sys.exit(2))[0], 2)
        self.assertEqual(self.run_cli(lambda argv: sys.exit("문자열 종료"))[:2], (1, ""))

    def test_report_prints_counts_and_closed_words_only(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            S.report("tg_collect", posts=171, edition="2026-10-08", verdict="short", ok=True, first=F.CANARIES[0], title="아무 문장")
        self.assertEqual(out.getvalue(), "[tg_collect] posts=171 edition=2026-10-08 verdict=short ok=True first=(가림) title=(가림)\n")

    def test_json_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "deep", "digest.json")
            S.write_json(path, F.digest())
            self.assertEqual(S.read_json(path), F.digest())
            self.assertEqual(os.listdir(os.path.dirname(path)), ["digest.json"])            # 임시 파일이 남지 않는다
            with open(path, encoding="utf-8") as f:
                self.assertIn('"미 CPI"', f.read())                                          # 한글을 이스케이프하지 않는다
            self.assertEqual(S.read_json(os.path.join(tmp, "none.json"), None), None)
            default = {"schema": 1}
            got = S.read_json(os.path.join(tmp, "none.json"), default)
            got["x"] = 1
            self.assertEqual(default, {"schema": 1})
            with self.assertRaises(FileNotFoundError):
                S.read_json(os.path.join(tmp, "none.json"))
            broken = os.path.join(tmp, "broken.json")
            with open(broken, "w", encoding="utf-8") as f:
                f.write('{"text": "' + F.CANARIES[0])
            with self.assertRaises(ValueError) as e:
                S.read_json(broken)
            self.assertEqual(F.leaks(str(e.exception)), [])


class RealSourcesTest(unittest.TestCase):
    """data/sources.json — 공개 출처 목록. 규칙만 본다(명단·개수는 못 박지 않는다): 삭제 요청대로 채널을 빼거나 끄는 편집이
    저녁 테스트를 깨뜨려 수집 전체를 멈추면 안 된다."""

    def setUp(self):
        self.src = S.read_json(os.path.join(S.DATA, "sources.json"))

    def test_list_is_valid_and_can_make_an_edition(self):
        S.validate_sources(self.src)
        on = [c for c in self.src["channels"] if c["role"] != "off"]
        self.assertGreaterEqual(sum(c["group"] == "bond" and c["role"] == "source" for c in on), R.TH["min_bond_ok"])
        self.assertGreaterEqual(len(on), R.TH["min_total_ok"])              # 이보다 적으면 날마다 수집 부족이다
        self.assertEqual(self.src["youtube"], [])

    def test_labels_are_the_only_free_text(self):
        chans = self.src["channels"]
        labels = [c["label"] for c in chans] + list(R.GROUPS.values()) + list(R.ROLES.values())
        self.assertEqual(S.closed_violations(self.src, S.handles_of(self.src, list(R.ROLES)), labels), [])
        self.assertEqual(len({c["label"] for c in chans}), len(chans))
        shas = [c["title_sha"] for c in chans if c["title_sha"]]
        self.assertEqual((len(set(shas)), len(shas)), (len(S.handles_of(self.src)),) * 2)

    def test_removing_or_switching_off_a_channel_keeps_the_list_valid(self):
        """삭제 요청 처리 그대로: 채널 하나를 목록에서 빼거나, off로 돌리거나(title_sha null), 숨김 파일에 적는다."""
        chans = self.src["channels"]
        first = next(i for i, c in enumerate(chans) if c["role"] != "off")
        gone = {**self.src, "channels": chans[:first] + chans[first + 1:]}
        off = {**self.src, "channels": chans[:first] + [{**chans[first], "role": "off", "title_sha": None}] + chans[first + 1:]}
        for src in (gone, off):
            S.validate_sources(src)
            self.assertNotIn(chans[first]["handle"], S.handles_of(src))
        S.validate_overrides(F.overrides(hide_channels=[chans[first]["handle"], "gone_channel_1"],
                                         hide_ids=["20261008-gone_channel_1-7"]))        # 목록에 없는 채널도 적을 수 있다

    def test_other_files_people_write_are_valid(self):
        cal = S.validate_calendar(S.read_json(os.path.join(S.DATA, "calendar.json")))
        self.assertEqual(S.closed_violations(cal), [])                       # 일정의 낱말은 사전에 있는 것만
        over = S.validate_overrides(S.read_json(os.path.join(S.DATA, "digest_overrides.json")))
        named = set(over["hide_channels"]) | {S.ID_RE.fullmatch(i).group("ch") for i in over["hide_ids"]}      # 목록에서 뺀 채널일 수 있다
        self.assertEqual(S.closed_violations(over, S.handles_of(self.src, list(R.ROLES)) | named), [])


if __name__ == "__main__":
    unittest.main()
