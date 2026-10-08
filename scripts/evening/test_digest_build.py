#!/usr/bin/env python3
"""저녁판 조립(digest_build) 테스트 — 같은 입력이면 같은 바이트, 같은 판 날짜 재실행, 숨김, 금리 자료일, 크기, 수집 부족·0건 연속·내리기.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요 — 입력(scored.json · collect_status.json)은 fixtures.py의 지어낸 글로 만든 예시다. 실제 채널 글은 넣지 않는다.
"""
import contextlib
import copy
import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_build as B
import digest_check as C
import digest_picks as K
import digest_rules as R
import digest_schema as S
import fixtures as F
import test_digest_picks as TK

DAY = f"digest/{F.EDITION}.json"
FILES = ("digest.json", DAY, "digest_index.json", "digest_state.json", "digest_status.json")
LATER = "2026-10-08T19:30:00+09:00"
_FX = {}


def fx(name):
    """fixtures의 예시를 한 번만 만들어 두고 사본을 준다."""
    if name not in _FX:
        _FX[name] = getattr(F, name)()
    return copy.deepcopy(_FX[name])


def index_before():
    """직전 판(2026-10-07)만 든 목차."""
    old = fx("index")["editions"][1]
    return {"schema": 1, "updated_at": old["collected_at"], "latest": old["date"], "editions": [old]}


def without_must(scored):
    """꼭 볼 것이 하나도 뽑히지 않은 날 — 세 묶음을 나머지 표로 내린 점수 자료."""
    for c in scored["clusters"]:
        if c["pick"] == "must":
            c.update(pick="rest", rank=None)
    return scored


def with_bond_singles(scored, n):
    """채권 채널이 혼자 쓴 글 n개를 더한 점수 자료(나머지 표를 길게 만든다)."""
    base = next(c for c in scored["clusters"] if c["seed"] == {"ch": "fxbond1", "id": 502})
    for k in range(1, n + 1):
        c = copy.deepcopy(base)
        c["members"][0]["id"] += 1000 * k
        c["seed"] = S.seed_of(c["members"])
        scored["clusters"].append(c)
    scored["stats"]["kept"] += n
    scored["stats"]["posts"] += n
    return scored


def with_heavy_rows(scored, collect, n):
    """네 채널이 함께 쓴 묶음 n개를 더한 점수 자료와 수집 기록(링크 둘 · 낱말 셋 · 숫자 하나가 붙는 무거운 줄)."""
    base = next(c for c in scored["clusters"] if c["seed"] == {"ch": "fxanal4", "id": 905})
    for k in range(1, n + 1):
        c = copy.deepcopy(base)
        for m in c["members"]:
            m["id"] += 100_000 * k
        c["seed"] = S.seed_of(c["members"])
        scored["clusters"].append(c)
    scored["stats"]["kept"] += n * len(base["members"])
    scored["stats"]["posts"] += n * len(base["members"])
    for ch in collect["channels"]:
        if ch["ch"] in {m["ch"] for m in base["members"]}:
            ch.update({k: ch[k] + n for k in ("in_window", "posts", "with_text")})
    return scored, collect


def rest_ids(d):
    return [x["id"] for g in d["rest"] for x in g["items"]]


class BuildCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work, self.data, self.out = (os.path.join(self.tmp.name, n) for n in ("work", "data", "out"))
        self.src = fx("sources")
        self.given(scored=fx("scored_doc"), collect=fx("collect_status"), state=fx("state"), index=index_before(),
                   overrides=F.overrides(), sources=self.src)
        S.write_json(os.path.join(self.work, "posts.json"), fx("posts_doc"))

    def given(self, **docs):
        """입력 파일을 바꿔 놓는다(None이면 지운다)."""
        where = {"scored": (self.work, "scored.json"), "collect": (self.work, "collect_status.json"),
                 "state": (self.data, "digest_state.json"), "index": (self.data, "digest_index.json"),
                 "overrides": (self.data, "digest_overrides.json"), "sources": (self.data, "sources.json")}
        for name, doc in docs.items():
            path = os.path.join(*where[name])
            if doc is None:
                os.remove(path)
            else:
                S.write_json(path, doc)

    def build(self, *extra, out=None):
        buf = io.StringIO()
        argv = ["--work", self.work, "--out", out or self.out, "--data", self.data, *extra]
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = S.run_cli("digest_build", B.main, argv)
        return code, buf.getvalue()

    def doc(self, name, out=None):
        return S.read_json(os.path.join(out or self.out, name))

    def raw(self, name, out=None):
        with open(os.path.join(out or self.out, name), "rb") as f:
            return f.read()

    def written(self, out=None):
        return sorted(os.path.relpath(os.path.join(r, n), out or self.out).replace(os.sep, "/")
                      for r, _, ns in os.walk(out or self.out) for n in ns)

    def publish(self, out=None):
        """나온 파일을 data/로 옮긴다(다음 실행의 입력이 되게)."""
        for name in self.written(out):
            os.makedirs(os.path.dirname(os.path.join(self.data, name)), exist_ok=True)
            shutil.copyfile(os.path.join(out or self.out, name), os.path.join(self.data, name))

    def passes_check(self, raw=True, out=None):
        found, _ = C.check_folder(out or self.out, self.src, self.work if raw else None)
        self.assertEqual(found, [])


class SampleTest(BuildCase):
    def test_sample_run_reproduces_the_contract_example(self):
        code, text = self.build()
        self.assertEqual(code, 0, text)
        self.assertEqual(self.written(), sorted(FILES))
        self.assertEqual(self.doc("digest.json"), fx("digest"))
        self.assertEqual(self.raw(DAY), self.raw("digest.json"))                # 날짜별 판은 오늘 판과 바이트까지 같다
        self.assertEqual(self.doc("digest_index.json"), fx("index"))
        self.assertEqual(self.doc("digest_state.json"), fx("state_after"))
        self.assertEqual(self.doc("digest_status.json"), fx("status"))
        self.passes_check()

    def test_nothing_of_the_posts_reaches_the_output(self):
        code, text = self.build()
        blob = b"".join(self.raw(n) for n in FILES).decode("utf-8")
        self.assertEqual(F.leaks(blob + text), [])
        self.assertRegex(text, r"^\[digest_build\] edition=2026-10-08 status=ok reason=ok must=3 rest=4 wire=5 solo=3 "
                               r"truncated=0 dropped=0 bytes=\d+ code=0\n$")
        self.assertLess(len(self.raw("digest.json")), C.EDITION_BYTES)

    def test_same_input_gives_the_same_bytes(self):
        other = os.path.join(self.tmp.name, "again")
        self.assertEqual((self.build()[0], self.build(out=other)[0]), (0, 0))
        for name in FILES:
            self.assertEqual(self.raw(name), self.raw(name, other), name)
        self.publish()                                                          # 낸 것을 입력으로 삼아 같은 자료를 다시 돌려도 같다
        replay = os.path.join(self.tmp.name, "replay")
        self.assertEqual(self.build(out=replay)[0], 0)
        for name in FILES:
            self.assertEqual(self.raw(name), self.raw(name, replay), name)

    def test_inputs_are_not_touched(self):
        scored, collect, state = fx("scored_doc"), fx("collect_status"), fx("state")
        before = copy.deepcopy((scored, collect, state))
        B.assemble(scored, collect, state, index_before(), F.overrides(), self.src)
        self.assertEqual((scored, collect, state), before)

    def test_tomorrow_keeps_only_the_next_few_days(self):
        scored = fx("scored_doc")
        row = scored["tomorrow"][0]
        days = ("2026-10-13", "2026-10-08", "2026-10-12", "2026-10-07", "2026-10-09")
        scored["tomorrow"] = [{**row, "date": d} for d in days] + [{**row, "date": "2026-10-08", "time": "09:00"}]
        self.given(scored=scored)
        self.assertEqual(self.build()[0], 0)
        got = [(r["date"], r["time"]) for r in self.doc("digest.json")["tomorrow"]]                # 창은 10-08 18:07에 끝났다
        self.assertEqual(got, [("2026-10-08", "21:30"), ("2026-10-09", "21:30"), ("2026-10-12", "21:30")])    # 오늘 밤 일정은 남는다


class RerunTest(BuildCase):
    def later(self, doc):
        """같은 판 날짜의 두 번째 실행 — 창의 시작은 그대로, 끝과 수집 시각만 늦다."""
        return {**doc, "window": {**doc["window"], "to": "2026-10-08T19:20:00+09:00"}, "collected_at": "2026-10-08T19:22:00+09:00"}

    def test_second_run_of_the_same_edition_replaces_instead_of_stacking(self):
        state = fx("state")
        state["edition"]["empty_streak"] = 1
        self.given(state=state, scored=without_must(fx("scored_doc")))
        self.assertEqual(self.build()[0], 0)
        first = self.doc("digest_state.json")
        self.assertEqual((first["edition"]["empty_streak"], first["base"]["date"]), (2, "2026-10-07"))
        self.publish()
        self.given(scored=self.later(without_must(fx("scored_doc"))), collect={**self.later(fx("collect_status")), "window_kind": "rerun"})
        again = os.path.join(self.tmp.name, "again")
        self.assertEqual(self.build(out=again)[0], 0)
        second = self.doc("digest_state.json", again)
        self.assertEqual(second["base"], first["base"])                         # '어제'는 여전히 그 앞 판이다
        self.assertEqual(second["edition"]["empty_streak"], 2)                  # 0건을 두 번 세지 않는다
        self.assertEqual(second["edition"]["window"]["from"], first["edition"]["window"]["from"])
        self.assertEqual([e["date"] for e in self.doc("digest_index.json", again)["editions"]], ["2026-10-08", "2026-10-07"])
        self.assertIn(R.phrase("note_rerun"), self.doc("digest.json", again)["notes"])
        self.assertEqual(self.doc("digest_status.json", again)["empty_streak"], 2)
        self.passes_check(raw=False, out=again)

    def test_first_run_ever_needs_no_state_or_index(self):
        self.given(state=None, index=None, overrides=None)
        self.given(collect={**fx("collect_status"), "window_kind": "first"})
        self.assertEqual(self.build()[0], 0)
        self.assertEqual(self.doc("digest_state.json")["base"], None)
        self.assertEqual([e["date"] for e in self.doc("digest_index.json")["editions"]], ["2026-10-08"])
        self.passes_check()

    def test_index_keeps_35_days(self):
        row = index_before()["editions"][0]
        days = ["2026-10-07", "2026-09-04", "2026-09-03", "2026-08-20"]                  # 9월 3일이 35일 전
        self.given(index={**index_before(), "editions": [{**row, "date": d} for d in days]})
        self.assertEqual(self.build()[0], 0)
        self.assertEqual([e["date"] for e in self.doc("digest_index.json")["editions"]], ["2026-10-08", "2026-10-07", "2026-09-04"])

    def test_channel_dropped_from_the_list_does_not_block_the_next_edition(self):
        state = fx("state")
        state["edition"]["channels"]["fxgone1"] = {"last_post": 9, "last_at": "2026-10-07T10:00:00+09:00", "fail_streak": 0}
        state["edition"]["must"].append({"id": "20261007-fxgone1-9", "keys": [S.key_of("k", "x")], "c": 2.0})
        self.given(state=state)
        self.assertEqual(self.build()[0], 0)
        base = self.doc("digest_state.json")["base"]
        self.assertNotIn("fxgone1", base["channels"])
        self.assertEqual([m["id"] for m in base["must"]], ["20261007-fxbond2-205"])
        self.passes_check()

    def test_a_short_edition_keeps_the_last_good_reading_point(self):
        """수집 부족인 날은 '여기까지 제대로 읽었다'(read_to)를 앞 판의 것으로 둔다 — 다음 판의 창이 그날 못 읽은 글까지 덮는다."""
        self.assertEqual(self.build()[0], 0)
        self.assertEqual(self.doc("digest_state.json")["edition"]["read_to"], F.WINDOW["to"])       # 정상 판은 창의 끝
        self.given(collect=F.collect_status(fail={"fxbond1": "fetch", "fxbond2": "fetch", "fxbond3": "empty"}))
        self.assertEqual(self.build()[0], 2)
        state = self.doc("digest_state.json")
        self.assertEqual(state["edition"]["read_to"], F.WINDOW["from"])        # 직전 판(10-07)이 읽은 곳 그대로
        nxt = S.collect_window(S.parse_iso("2026-10-09T17:41:00+09:00"), state)
        self.assertEqual((nxt["from"], nxt["kind"], nxt["capped"]), (F.WINDOW["from"], "next", False))
        self.given(overrides=F.overrides(withdraw=True), collect=fx("collect_status"))
        self.assertEqual(self.build()[0], 0)                                   # 일부러 내린 판은 창의 끝에서 이어 간다
        self.assertEqual(self.doc("digest_state.json")["edition"]["read_to"], F.WINDOW["to"])

    def test_unread_channel_keeps_its_last_post_number(self):
        self.given(collect=F.collect_status(fail={"fxpers8": "fetch"}))
        self.assertEqual(self.build()[0], 0)
        now, before = self.doc("digest_state.json")["edition"]["channels"]["fxpers8"], fx("state")["edition"]["channels"]["fxpers8"]
        self.assertEqual(now, {**before, "fail_streak": 1})
        self.assertIn(R.phrase("note_channels", n=1), self.doc("digest.json")["notes"])


class OverridesTest(BuildCase):
    def test_hidden_item_leaves_its_place_empty(self):
        want = fx("digest")
        self.given(overrides=F.overrides(hide_ids=[want["must"][1]["id"], rest_ids(want)[0]]))
        self.assertEqual(self.build()[0], 0)
        d = self.doc("digest.json")
        self.assertEqual([x["id"] for x in d["must"]], [want["must"][0]["id"], want["must"][2]["id"]])    # 다른 묶음으로 채우지 않는다
        self.assertEqual(rest_ids(d), rest_ids(want)[1:])
        self.assertEqual((d["funnel"]["must"], d["notes"]), (2, [R.phrase("note_fewer", n=2)]))
        self.assertEqual([m["id"] for m in self.doc("digest_state.json")["edition"]["must"]], [x["id"] for x in d["must"]])
        self.passes_check()

    def test_hidden_channel_disappears_from_the_edition(self):
        self.given(overrides=F.overrides(hide_channels=["fxbond1", "fxwire1", "fxpers6", "fxctx1"]))
        self.assertEqual(self.build()[0], 0)
        d = self.doc("digest.json")
        for ch in (b"fxbond1", b"fxwire1", b"fxpers6", b"fxctx1"):
            self.assertNotIn(ch, self.raw("digest.json"))
        self.assertEqual(d["must"][0]["id"], "20261008-fxbond2-212")           # id도 보이는 글 가운데 씨앗 글로 다시 만든다
        self.assertEqual(d["must"][0]["links"][0]["ch"], "fxbond2")
        self.assertNotIn("20261008-fxbond1-502", rest_ids(d))                  # 그 채널 혼자 쓴 글은 항목째 빠진다
        self.assertEqual(([c["ch"] for c in d["wire"]["channels"]], d["wire"]["rows"], d["context"]), (["fxwire2"], [], []))
        self.assertEqual([r["ch"] for r in d["solo"]["rows"]], ["fxpers8", "fxpers7"])
        self.passes_check()

    def test_withdraw_puts_out_an_empty_edition(self):
        self.given(overrides=F.overrides(withdraw=True))
        code, text = self.build()
        d, state, status = self.doc("digest.json"), self.doc("digest_state.json"), self.doc("digest_status.json")
        self.assertEqual((code, d["status"], d["must"], d["rest"], d["notes"]), (0, "withdrawn", [], [], [R.phrase("note_withdrawn")]))
        self.assertEqual((d["wire"]["rows"], d["solo"]["channels"], d["context"], d["tomorrow"]), ([], [], [], []))
        self.assertEqual((state["edition"]["window"], state["edition"]["must"]), (F.WINDOW, []))      # 다음 판의 창은 여기서 이어진다
        self.assertEqual((status["ok"], status["reason"], status["published"]), (False, "withdrawn", True))
        self.assertEqual(status["last_success"], {"date": "2026-10-07", "at": "2026-10-07T18:04:00+09:00"})
        self.assertNotIn(b"t.me", self.raw("digest.json"))
        self.passes_check()


class HeadTest(BuildCase):
    def with_head(self, **change):
        scored = fx("scored_doc")
        for k, v in change.items():
            scored["head"][k] = {**scored["head"][k], **v} if isinstance(v, dict) else v
        self.given(scored=scored)
        self.assertEqual(self.build()[0], 0)
        return self.doc("digest.json")

    def test_rate_dated_before_the_window_shows_no_direction(self):
        """아침 잡이 받아 둔 전일 종가뿐인 날 — 방향 칸을 비우고 '전일 종가'라고 적는다(앞 단계가 맞다고 적어 와도)."""
        stale = {"asof": "2026-10-07", "fits": True}
        d = self.with_head(kr10=stale, kr3=stale)
        h = d["head"]
        self.assertEqual((h["kr10"]["fits"], h["kr3"]["fits"], h["dir"], h["curve"], h["basis"]), (False, False, None, None, "전일 종가"))
        self.assertEqual((h["kr10"]["value"], h["kr10"]["asof"]), (4.376, "2026-10-07"))
        self.assertEqual(d["notes"], [R.phrase("note_prev_close")])
        self.passes_check()

    def test_only_three_year_stale_blanks_the_curve_alone(self):
        h = self.with_head(kr3={"asof": "2026-10-07"})["head"]
        self.assertEqual((h["dir"], h["curve"], h["basis"]), ("보합", None, "당일 종가"))

    def test_no_rates_at_all(self):
        d = self.with_head(kr10=None, kr3=None, us10=None, dir=None, curve=None, basis=None)
        self.assertEqual((d["head"]["kr10"], d["head"]["basis"], d["notes"]), (None, None, [R.phrase("note_no_rates")]))
        self.assertEqual(d["head"]["top_terms"], fx("digest")["head"]["top_terms"])
        self.passes_check()


class SizeTest(BuildCase):
    def test_rest_table_stops_at_thirty_lines(self):
        self.given(scored=with_bond_singles(fx("scored_doc"), 45))
        code, text = self.build()
        d = self.doc("digest.json")
        self.assertEqual((code, len(rest_ids(d)), d["funnel"]["truncated"]), (0, 30, 19))
        self.assertIn(R.phrase("note_truncated", n=19), d["notes"])
        self.assertEqual(rest_ids(d)[:1] + rest_ids(d)[-1:], ["20261008-fxanal4-905", "20261008-fxbond1-28502"])   # 점수 높은 것부터
        self.assertFalse({"20261008-fxpers5-610", "20261008-fxbond3-89"} & set(rest_ids(d)))      # 점수가 낮은 줄, 같으면 늦은 글부터 잘린다
        self.assertLessEqual(len(self.raw("digest.json")), C.EDITION_BYTES)
        self.passes_check(raw=False)

    def test_a_heavy_day_fits_the_real_limit(self):
        """링크 둘 · 낱말 · 덧낱말 · 시각이 붙은 줄이 30개면 30KB쯤이다(예전 상한 20KB로는 열 줄쯤 잘렸다) — 지금 상한 36KB에서는
        30줄이 다 실린다. 상한에 걸릴 때 점수가 낮은 줄부터 줄이는 것은 test_edition_is_trimmed_to_the_byte_limit가 본다."""
        scored, collect = with_heavy_rows(fx("scored_doc"), fx("collect_status"), 40)
        self.given(scored=scored, collect=collect)
        code, text = self.build()
        d = self.doc("digest.json")
        self.assertEqual(code, 0, text)
        self.assertTrue(20_000 < len(self.raw("digest.json")) <= C.EDITION_BYTES, len(self.raw("digest.json")))
        self.assertEqual((len(rest_ids(d)), d["funnel"]["truncated"]), (30, 14))     # 줄인 것은 30줄 상한 때문뿐이다
        self.assertIn(R.phrase("note_truncated", n=14), d["notes"])
        self.assertEqual(len(d["solo"]["channels"]), 8)                         # 줄이는 것은 나머지 표뿐이다
        self.passes_check(raw=False)

    def test_edition_is_trimmed_to_the_byte_limit(self):
        self.given(scored=with_bond_singles(fx("scored_doc"), 45))
        old, C.EDITION_BYTES = C.EDITION_BYTES, 9_000
        try:
            code, text = self.build()
            d = self.doc("digest.json")
            self.assertEqual(code, 0, text)
            self.assertLessEqual(len(self.raw("digest.json")), 9_000)
            self.assertLess(len(rest_ids(d)), 30)
            self.assertEqual(d["funnel"]["truncated"], 49 - len(rest_ids(d)))
            self.assertEqual(len(d["must"]), 3)                                 # 꼭 볼 것은 줄이지 않는다
            self.passes_check(raw=False)
            C.EDITION_BYTES = 1_500                                             # 나머지 표를 다 줄여도 안 맞으면 내지 않는다
            shutil.rmtree(self.out)
            self.assertEqual(self.build()[0], 1)
            self.assertFalse(os.path.exists(self.out) and self.written())
        finally:
            C.EDITION_BYTES = old


class HealthTest(BuildCase):
    def test_short_collection_empties_the_top_and_fails_the_run(self):
        self.given(collect=F.collect_status(fail={"fxbond1": "fetch", "fxbond2": "fetch", "fxbond3": "empty"}))
        code, text = self.build()
        d, status, want = self.doc("digest.json"), self.doc("digest_status.json"), fx("digest")
        self.assertEqual((code, d["status"], d["must"], d["funnel"]["must"]), (2, "short", [], 0))
        self.assertEqual(d["notes"], [R.phrase("note_short"), R.phrase("note_channels", n=3)])
        self.assertTrue({x["id"] for x in want["must"]} <= set(rest_ids(d)))    # 뽑혔던 묶음은 나머지 표로 내려 보여 준다
        self.assertEqual((status["ok"], status["reason"], status["published"], status["counts"]["bond_ok"]), (False, "short", True, 2))
        self.assertEqual(status["last_success"]["date"], "2026-10-07")
        self.assertEqual(self.doc("digest_state.json")["edition"]["must"], [])
        self.assertEqual(self.doc("digest_index.json")["editions"][0]["status"], "short")
        self.assertIn("status=short reason=short", text)
        self.passes_check(raw=False)

    def test_broken_preview_writes_the_status_only(self):
        collect = fx("collect_status")
        for c in collect["channels"]:
            c["with_text"] = 1                                                  # 글은 읽히는데 본문이 거의 없다 — 형식이 바뀐 것
        collect["verdict"] = "broken"
        self.given(collect=collect)
        code, text = self.build()
        status = self.doc("digest_status.json")
        self.assertEqual((code, self.written()), (3, ["digest_status.json"]))
        self.assertEqual((status["ok"], status["reason"], status["published"], status["edition"]), (False, "broken", False, F.EDITION))
        self.assertEqual(status["last_success"], {"date": "2026-10-07", "at": "2026-10-07T18:04:00+09:00"})
        self.assertEqual(len(status["channels"]), 24)
        self.passes_check(raw=False)

    def streak(self, before, scored=None, collect=None):
        state = fx("state")
        state["edition"]["empty_streak"] = before
        self.given(state=state, scored=scored or without_must(fx("scored_doc")), collect=collect or fx("collect_status"))
        code, text = self.build()
        status = self.doc("digest_status.json")
        self.assertEqual(self.doc("digest_state.json")["edition"]["empty_streak"], status["empty_streak"])
        self.passes_check(raw=False)
        return code, status["empty_streak"], status["reason"], self.doc("digest.json")

    def test_third_empty_edition_in_a_row_fails_the_run(self):
        code, streak, reason, d = self.streak(1)
        self.assertEqual((code, streak, reason, d["notes"]), (0, 2, "ok", [R.phrase("note_none")]))
        code, streak, reason, d = self.streak(2)
        self.assertEqual((code, streak, reason, d["status"]), (2, 3, "empty_streak", "ok"))       # 판은 정상으로 나가고 실행만 실패로 끝낸다
        self.assertEqual(self.doc("digest_status.json")["last_success"]["date"], F.EDITION)
        code, streak, reason, _ = self.streak(2, scored=fx("scored_doc"))
        self.assertEqual((code, streak, reason), (0, 0, "ok"))                 # 한 건이라도 실리면 0부터

    def test_day_without_bond_posts_is_not_counted(self):
        collect = fx("collect_status")
        for c in collect["channels"]:
            c["in_window"] = 0 if c["group"] == "bond" else c["in_window"]
        self.assertEqual(self.streak(2, collect=collect)[:3], (0, 2, "ok"))

    def test_changed_channel_fails_the_run_but_not_the_edition(self):
        for why in ("title", "rewind"):
            with self.subTest(why):
                self.given(collect=F.collect_status(fail={"fxanal6": why}))
                code, text = self.build()
                status = self.doc("digest_status.json")
                self.assertEqual((code, status["reason"], self.doc("digest.json")["status"]), (2, "ok", "ok"))
                self.assertIn("changed=1", text)
                self.passes_check()


    def unread(self, ch, streak):
        collect = F.collect_status(fail={ch: "no_preview"})
        next(c for c in collect["channels"] if c["ch"] == ch)["fail_streak"] = streak
        self.given(collect=collect)
        code, text = self.build()
        self.passes_check()
        return code, self.doc("digest_status.json")["reason"], self.doc("digest.json")["status"], text

    def test_bond_channel_unread_for_days_fails_the_run_but_not_the_edition(self):
        """채널이 여러 판 이어서 안 읽혀도 판은 정상으로 나간다 — 조용히 넘어가지 않게 채권 채널이면 실행을 실패로 끝낸다."""
        n = R.TH["fail_streak_alert"]
        code, reason, status, text = self.unread("fxbond5", n)
        self.assertEqual((code, reason, status), (2, "ok", "ok"))
        self.assertIn("stale=1", text)
        code, reason, status, text = self.unread("fxbond5", n - 1)             # 하루 이틀은 알리지 않는다
        self.assertEqual((code, "stale=" in text), (0, False))
        code, reason, status, text = self.unread("fxpers8", n + 5)             # 개인 채널은 화면의 줄로만 남긴다
        self.assertEqual((code, "stale=" in text), (0, False))


class TermsTest(unittest.TestCase):
    """항목의 낱말 — 여러 채널이 든 묶음은 두 곳 이상이 쓴 낱말만 싣는다(한 곳만 쓴 낱말이 제목이 되지 않게)."""

    def cluster(self, chans, terms):
        ms = [{"ch": ch} for ch in chans]
        return {"members": ms, "terms": [{"term": t, "n_ch": n} for t, n in terms]}

    def test_only_shared_terms_title_a_cluster_of_several_channels(self):
        c = self.cluster(["fxbond1", "fxbond2", "fxbond3"], [("연준 의사록", 3), ("금리", 2), ("미 고용", 1), ("유가", 1)])
        self.assertEqual(B._shown_terms(c, 4), ["연준 의사록", "금리"])
        lone = self.cluster(["fxbond1", "fxanal1"], [("한은 발언", 1), ("반도체", 1)])
        self.assertEqual(B._shown_terms(lone, 4), ["한은 발언"])                 # 같이 쓴 낱말이 없으면 대표 낱말 하나
        single = self.cluster(["fxbond1"], [("한은 발언", 1), ("반도체", 1), ("금리", 1), ("환율", 1)])
        self.assertEqual(B._shown_terms(single, 3), ["한은 발언", "반도체", "금리"])    # 한 채널뿐인 묶음(단독 글)은 그대로
        self.assertEqual(B._shown_terms(self.cluster(["fxbond1", "fxbond2"], []), 4), [])


class RowTest(unittest.TestCase):
    """속보형·개인 단독 줄 — 묶기 단계가 지은 짝(row)만 줄이 된다. 낱말과 숫자를 자리만으로 짝짓지 않는다."""

    def test_a_row_is_the_pair_made_while_clustering(self):
        m = {"ch": "fxpers8", "id": 7, "at": F.NOW, "group": "personal", "role": "source", "fwd": False, "terms": ["금통위", "유가"],
             "lead": ["금통위", "유가"], "results": ["인하"], "nums": ["1.45%"], "lead_nums": ["1.45%"], "row": None}
        self.assertIsNone(B._row(m))                                           # 첫머리에 A·B급 낱말과 숫자가 있어도 짝이 아니면 줄이 없다
        self.assertIsNone(B._row({k: v for k, v in m.items() if k != "row"}))  # 짝 칸이 없는 옛 자료도 줄이 없다
        row = B._row({**m, "row": {"term": "유가", "v": "1.45%"}})
        self.assertEqual((row["term"], row["result"], row["v"], row["url"]), ("유가", "인하", "1.45%", "https://t.me/fxpers8/7"))

    def test_fixture_rows_are_the_paired_ones(self):
        rows = {(r["ch"], r["term"], r["v"]) for side in ("wire", "solo") for r in fx("digest")[side]["rows"]}
        self.assertIn(("fxwire1", "미 PPI", "0.2%"), rows)
        self.assertIn(("fxpers6", "국고채 발행계획", "12.5조원"), rows)
        self.assertIn(("fxpers8", "한은 발언", None), rows)                    # 숫자 없는 줄(2026-10-08 저녁 — 낱말만)
        self.assertTrue(all(v is None or R.solo_num_ok(v) for _, _, v in rows))


class TakedownTest(BuildCase):
    def test_blank_takes_everything_of_the_evening_down(self):
        self.assertEqual(self.build()[0], 0)
        self.publish()
        S.write_json(os.path.join(self.data, "digest", "2026-10-07.json"), {"old": 1})
        S.write_json(os.path.join(self.data, "korea.json"), {"morning": 1})
        S.write_json(os.path.join(self.data, K.FILE), TK.doc())                 # PC가 올려 둔 AI 요약 문장
        shutil.rmtree(self.work)                                                # 내리기는 수집한 것 없이도 돈다
        code, text = self.build("--blank", "--now", LATER, out=self.data)
        d, state, status = (self.doc(n, self.data) for n in ("digest.json", "digest_state.json", "digest_status.json"))
        self.assertEqual((code, d["status"], d["must"], d["rest"], d["collected_at"]), (0, "withdrawn", [], [], LATER))
        self.assertEqual(sorted(os.listdir(os.path.join(self.data, "digest"))), ["2026-10-08.json"])       # 지난 판 파일도 지운다
        self.assertEqual(self.raw(DAY, self.data), self.raw("digest.json", self.data))
        self.assertEqual(self.doc("digest_index.json", self.data)["editions"], [C.index_row(d)])
        self.assertEqual((state["edition"]["must"], state["base"]["must"], state["edition"]["window"]), ([], [], F.WINDOW))
        self.assertEqual((status["ok"], status["reason"], status["published"], status["edition"]), (False, "withdrawn", True, F.EDITION))
        self.assertEqual(self.doc("korea.json", self.data), {"morning": 1})    # 아침 자료는 건드리지 않는다
        self.assertEqual(self.doc(K.FILE, self.data), K.blank_picks(F.EDITION, LATER))      # AI 요약 층도 빈 것으로 — 문장이 남지 않는다
        self.assertNotIn("다.".encode("utf-8"), self.raw(K.FILE, self.data))
        for name in ("digest.json", "digest_index.json", "digest_state.json"):
            self.assertNotIn(b"t.me", self.raw(name, self.data))
            self.assertNotIn(b"-fx", self.raw(name, self.data))                 # 항목 id(채널 이름 + 글 번호)도 남지 않는다
        self.assertEqual(C.check_folder(self.data, self.src)[0], [])
        before = {n: self.raw(n, self.data) for n in FILES}
        self.assertEqual(self.build("--blank", "--now", LATER, out=self.data)[0], 0)
        self.assertEqual({n: self.raw(n, self.data) for n in FILES}, before)

    def test_blank_works_on_an_empty_repository(self):
        self.given(state=None, index=None, overrides=None)
        self.assertEqual(self.build("--blank", "--now", LATER)[0], 0)
        self.assertEqual(self.doc("digest_state.json"), {"schema": 1, "edition": None, "base": None})
        self.passes_check(raw=False)
        self.assertEqual(self.doc(K.FILE)["items"], [])                         # 올린 적이 없어도 빈 요약 층을 둔다

    def test_blank_does_not_depend_on_files_a_person_may_have_broken(self):
        """내리는 날은 목록·숨김 파일을 손으로 고치다 깨뜨리기 쉽다 — 그래도 내려가야 한다."""
        for name in ("sources.json", "digest_state.json", "digest_index.json", "digest_overrides.json"):
            with open(os.path.join(self.data, name), "w", encoding="utf-8") as f:
                f.write('{"channels": [' + F.CANARIES[0])
        code, text = self.build("--blank", "--now", LATER)
        self.assertEqual((code, self.doc("digest.json")["status"]), (0, "withdrawn"))
        self.assertEqual(self.doc("digest_state.json"), {"schema": 1, "edition": None, "base": None})
        self.assertEqual(F.leaks(text + "".join(self.raw(n).decode("utf-8") for n in FILES)), [])

    def test_error_leaves_a_status_that_says_so(self):
        code, text = self.build("--error", "--now", LATER)
        status = self.doc("digest_status.json")
        self.assertEqual((code, self.written()), (0, ["digest_status.json"]))
        self.assertEqual((status["ok"], status["reason"], status["published"], status["edition"], status["checked_at"]),
                         (False, "error", False, F.EDITION, LATER))
        self.assertEqual(status["last_success"], {"date": "2026-10-07", "at": "2026-10-07T18:04:00+09:00"})
        self.assertEqual(len(status["channels"]), 24)                           # 수집까지는 됐으면 건강 숫자는 싣는다
        self.passes_check(raw=False)
        code, text = self.build("--error", "--now", "2026-10-09T19:30:00+09:00")       # 작업 폴더에 남은 것이 어제 판의 수집 기록이면
        status = self.doc("digest_status.json")
        self.assertEqual((status["edition"], status["channels"], status["counts"]["posts"]), ("2026-10-09", [], 0))   # 싣지 않는다
        shutil.rmtree(self.work)
        shutil.rmtree(self.out)
        self.assertEqual(self.build("--error", "--now", LATER)[0], 0)
        self.assertEqual(self.doc("digest_status.json")["channels"], [])
        self.passes_check(raw=False)


class RefusalTest(BuildCase):
    def nothing_written(self, code, text, kind="ValueError"):
        self.assertEqual((code, text), (1, f"[digest_build] 실패: {kind}\n"))
        self.assertFalse(os.path.exists(self.out) and self.written())

    def test_open_text_in_the_input_writes_nothing(self):
        scored = fx("scored_doc")
        scored["clusters"][0]["terms"][0]["term"] = F.CANARIES[0]
        self.given(scored=scored)
        self.nothing_written(*self.build())
        scored = fx("scored_doc")
        scored["clusters"][0]["text"] = F.CANARIES[2]
        self.given(scored=scored)
        self.nothing_written(*self.build())

    def test_inputs_from_different_runs_write_nothing(self):
        collect = fx("collect_status")
        collect["collected_at"] = "2026-10-08T18:10:00+09:00"
        self.given(collect=collect)
        self.nothing_written(*self.build())

    def test_missing_or_broken_inputs_write_nothing(self):
        self.given(scored=None)
        self.nothing_written(*self.build(), kind="FileNotFoundError")
        self.given(scored=fx("scored_doc"), sources=None)
        self.nothing_written(*self.build(), kind="FileNotFoundError")
        self.given(sources=self.src)
        with open(os.path.join(self.data, "digest_state.json"), "w", encoding="utf-8") as f:
            f.write('{"edition": "' + F.CANARIES[0])
        self.nothing_written(*self.build())

    def test_post_from_a_channel_outside_the_list_is_left_out(self):
        """묶음에 목록에 없는(또는 역할이 바뀐) 채널의 글이 섞여 와도 그 글만 빠지고 판은 나간다."""
        src = fx("sources")
        src["channels"] = [c for c in src["channels"] if c["handle"] != "fxanal2"]
        collect = fx("collect_status")
        collect["channels"] = [c for c in collect["channels"] if c["ch"] != "fxanal2"]
        collect["requests"] = len(collect["channels"])
        state = fx("state")
        del state["edition"]["channels"]["fxanal2"]
        self.src = src
        self.given(sources=src, collect=collect, state=state)
        code, text = self.build()
        self.assertEqual(code, 0, text)
        self.assertNotIn(b"fxanal2", b"".join(self.raw(n) for n in FILES))
        self.assertEqual([x["ch"] for x in self.doc("digest.json")["must"][0]["links"]],
                         ["fxbond1", "fxbond2", "fxbond3", "fxpers2", "fxpers3", "fxanal1"])
        self.passes_check(raw=False)


if __name__ == "__main__":
    unittest.main()
