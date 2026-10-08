#!/usr/bin/env python3
"""저녁판 검사(digest_check) 테스트 — 닫힌 글자, 뺄 것과 판을 멈출 것의 구분, 금리·수집 판정·0건 연속, 파일끼리의 맞춤.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요 — 자료는 fixtures.py의 지어낸 글뿐이다. 실제 채널 글은 테스트에 넣지 않는다.
"""
import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_check as C
import digest_rules as R
import digest_schema as S
import fixtures as F

DAY = f"digest/{F.EDITION}.json"
_FX = {}


def fx(name):
    """fixtures의 예시를 한 번만 만들어 두고 사본을 준다(만들 때마다 낱말 사전을 다시 돌려 0.1초씩 든다)."""
    if name not in _FX:
        _FX[name] = getattr(F, name)()
    return copy.deepcopy(_FX[name])


def docs(**change):
    """공개 폴더에 놓일 자료 한 벌(예시 판). change = {파일 이름의 앞머리: 바꾼 자료}."""
    d = fx("digest")
    out = {"digest.json": d, DAY: d, "digest_index.json": fx("index"), "digest_state.json": fx("state_after"),
           "digest_status.json": fx("status")}
    for name, doc in change.items():
        for key in (("digest.json", DAY) if name == "digest" else (name + ".json",)):
            out[key] = doc
    return out


def put(tmp, files):
    for name, doc in files.items():
        if isinstance(doc, bytes):
            os.makedirs(os.path.dirname(os.path.join(tmp, name)), exist_ok=True)
            with open(os.path.join(tmp, name), "wb") as f:
                f.write(doc)
        elif doc is not None:
            S.write_json(os.path.join(tmp, name), doc)
    return tmp


def put_raw(tmp):
    S.write_json(os.path.join(tmp, "posts.json"), fx("posts_doc"))
    S.write_json(os.path.join(tmp, "collect_status.json"), fx("collect_status"))
    return tmp


def codes(found):
    return sorted({(f["code"], f["scope"]) for f in found})


def edit(doc, path, value):
    """doc의 깊은 사본에서 path 자리만 바꾼 것."""
    out = copy.deepcopy(doc)
    node = out
    for k in path[:-1]:
        node = node[k]
    node[path[-1]] = value
    return out


class FolderCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pub, self.raw = os.path.join(self.tmp.name, "public"), put_raw(os.path.join(self.tmp.name, "raw"))
        self.src = fx("sources")
        self.src_path = os.path.join(self.tmp.name, "sources.json")
        S.write_json(self.src_path, self.src)

    def check(self, raw=False, **change):
        put(self.pub, docs(**change))
        return C.check_folder(self.pub, self.src, self.raw if raw else None)

    def cli(self, *extra, raw=False):
        out, err = io.StringIO(), io.StringIO()
        argv = ["--public", self.pub, "--sources", self.src_path, *extra] + (["--raw", self.raw] if raw else [])
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = S.run_cli("digest_check", C.main, argv)
        return code, out.getvalue() + err.getvalue()


class ClosedTextTest(FolderCase):
    def test_sample_folder_passes_with_and_without_raw(self):
        self.assertEqual(self.check()[0], [])
        found, facts = self.check(raw=True)
        self.assertEqual(found, [])
        self.assertEqual((facts["edition"], facts["published"], facts["reason"], facts["files"]), (F.EDITION, True, "ok", 5))
        self.assertEqual(self.cli(raw=True)[0], 0)

    def test_long_dictionary_words_pass_even_though_posts_use_them(self):
        """8자 이상 사전 낱말은 원문에도 그대로 있다 — '원문과 8자 이상 겹침' 검사였다면 스스로 걸렸을 항목이 통과한다."""
        raw = " ".join(p["text"] for p in fx("posts"))
        shown = {t for x in fx("digest")["must"] + [i for g in fx("digest")["rest"] for i in g["items"]] for t in x["terms"]}
        shown |= {r["term"] for r in fx("digest")["solo"]["rows"]}
        long_words = sorted(t for t in shown if len(t) >= 8 and t in raw)
        self.assertEqual(long_words, ["AI 회사채 발행", "Capex 가이던스", "국고채 발행계획"])
        self.assertEqual(self.check(raw=True)[0], [])

    def test_planted_text_is_refused_wherever_it_hides(self):
        good = fx("digest")
        cases = {
            "낱말 자리": edit(good, ["must", 0, "terms", 0], F.CANARIES[0]),
            "알림 줄": edit(good, ["notes"], [F.CANARIES[2]]),
            "가장 많이 다뤄진 주제": edit(good, ["head", "top_terms", 0], F.CANARIES[1]),
            "모르는 칸": edit(good, ["must", 1, "fact"], F.CANARIES[3]),
            "칸 이름": edit(good, ["must", 2, F.CANARIES[5]], 1),
            "보이지 않는 문자": edit(good, ["rest", 0, "items", 0, "terms", 0], F.CANARIES[4]),
            "바깥 주소": edit(good, ["must", 0, "links", 0, "url"], "https://" + F.CANARIES[6]),
            "속보 줄의 낱말": edit(good, ["wire", "rows", 0, "term"], F.CANARIES[0]),
        }
        for name, bad in cases.items():
            with self.subTest(name):
                found, _ = self.check(raw=True, digest=bad)
                self.assertTrue(found)
                code, text = self.cli(raw=True)
                self.assertEqual(code, 1)
                self.assertIn("[digest_check] 위반 ", text)
                self.assertEqual(F.leaks(text), [], "검사 출력에 심은 글자가 실렸다")
        found, _ = self.check(raw=True, digest=cases["낱말 자리"])
        self.assertIn(("leak", "item"), codes(found))                       # 원문과 대조하면 '새어 나온 글자'로 부른다
        found, _ = self.check(digest=cases["낱말 자리"])
        self.assertIn(("open", "item"), codes(found))                       # 원문 없이도 닫힌 글자가 아닌 것으로 잡힌다

    def test_planted_text_in_the_small_files_is_refused_too(self):
        state = fx("state_after")
        state["edition"]["channels"]["zqx7_planted_key"] = state["edition"]["channels"]["fxbond1"]
        status = edit(fx("status"), ["channels", 0, "ch"], "zqx7_nobody")
        for name, bad in (("digest_state", state), ("digest_status", status)):
            with self.subTest(name):
                found, _ = self.check(**{name: bad})
                self.assertTrue(any(f["file"] == name + ".json" for f in found))
                code, text = self.cli()
                self.assertEqual((code, F.leaks(text)), (1, []))

    def test_hidden_bytes_are_refused(self):
        """다시 쓴 바이트와 같아야 한다 — 겹친 칸이나 덧붙인 글자가 숨을 자리가 없게."""
        body = S.dump(fx("digest"))
        twice = ('{"schema":1,"notes":["' + F.CANARIES[0] + '"],' + body[1:]).encode("utf-8")      # 같은 칸이 두 번 — 뒤의 것만 읽힌다
        cases = {"겹친 칸": twice, "끝에 덧붙인 글자": (body + "\n" + F.CANARIES[0]).encode("utf-8"),
                 "보기 좋게 다시 쓴 것": json.dumps(fx("digest"), ensure_ascii=False, indent=1).encode("utf-8"),
                 "UTF-8이 아님": body.encode("utf-16"), "너무 큼": (body[:-1] + "," + '"x":"' + "0" * R.TH["bytes_max"] + '"}').encode("utf-8")}
        for name, raw in cases.items():
            with self.subTest(name):
                found, _ = self.check(digest=raw)
                self.assertTrue({c for c, _ in codes(found)} & {"json", "canon", "size"}, codes(found))
                self.assertEqual(F.leaks(self.cli()[1]), [])

    def test_files_outside_the_contract_are_refused(self):
        for name, mark in (("digest/latest.json", "latest"), ("digest/zqx7-note.html", "zqx7"), ("digest_picks.json", "picks"),
                           ("digest/2026-10-07/zqx7.json", "zqx7")):
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                self.pub = put(tmp, {**docs(), name: {"schema": 1}})
                found, _ = C.check_folder(self.pub, self.src)
                self.assertEqual(codes(found), [("stray", "edition")])
                self.assertNotIn(mark, self.cli()[1])                                       # 모르는 파일 이름은 찍지 않는다
        with tempfile.TemporaryDirectory() as tmp:                                          # 아침 자료가 같이 있어도 된다(data/를 볼 때)
            self.assertEqual(C.check_folder(put(tmp, {**docs(), "korea.json": {"any": 1}, "sources.json": self.src}), self.src)[0], [])


    def test_the_artifact_folder_holds_nothing_but_the_edition(self):
        """아티팩트로 올라가는 폴더(--strict)에는 저녁판 파일 말고 아무것도 없어야 한다 — 이름이 digest로 시작하지 않아도 걸린다."""
        extra = {"posts.json": fx("posts_doc"), "pages/fxbond1-1.html": b"<html>zqx7</html>", "note.txt": b"zqx7", ".hidden": b"zqx7",
                 "korea.json": {"any": 1}, "digest_overrides.json": F.overrides(), "digest/zqx7.txt": b"zqx7"}
        for name, doc in extra.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                self.pub = put(tmp, {**docs(), name: doc})
                self.assertEqual(codes(C.check_folder(self.pub, self.src, strict=True)[0]), [("stray", "edition")])
                code, text = self.cli("--strict")
                self.assertEqual((code, "zqx7" in text), (1, False))
        with tempfile.TemporaryDirectory() as tmp:
            self.pub = put(tmp, docs())
            self.assertEqual(C.check_folder(self.pub, self.src, strict=True)[0], [])
            self.assertEqual(self.cli("--strict")[0], 0)


class ScopeTest(FolderCase):
    """설계 8절 — 걸린 것만 빼면 되는 위반(link · row · item · rate)과 판을 멈추는 위반(edition)."""

    def test_bad_links_cost_only_the_link(self):
        good = fx("digest")
        link = good["must"][0]["links"][0]
        cases = {
            "목록에 없는 채널": ({**link, "ch": "nobody_here", "url": "https://t.me/nobody_here/5"}, "url"),
            "요청하지 않는 채널": ({**link, "ch": "fxoff1", "url": "https://t.me/fxoff1/5"}, "role"),
            "속보형 채널": ({**link, "ch": "fxwire1", "url": "https://t.me/fxwire1/90011"}, "role"),
            "미리보기 주소": ({**link, "url": "https://t.me/s/fxbond1/501"}, "url"),
            "주소에 꼬리": ({**link, "url": "https://t.me/fxbond1/501?single"}, "url"),
            "주소와 채널이 다름": ({**link, "url": "https://t.me/fxbond2/501"}, "url"),
        }
        for name, (bad, code) in cases.items():
            with self.subTest(name):
                d = edit(good, ["must", 0, "links", 0], bad)
                self.assertEqual(codes(C.check_edition(d, self.src)), [(code, "link")])
                pruned, found = C.prune(d, self.src)
                self.assertEqual([x["ch"] for x in pruned["must"][0]["links"]], [x["ch"] for x in good["must"][0]["links"][1:]])
                self.assertEqual(len(pruned["must"]), 3)
                self.assertEqual(C.check_edition(pruned, self.src), [])
                self.assertEqual(d["must"][0]["links"][0], bad)                 # 입력은 고치지 않는다

    def test_item_goes_when_no_link_is_left_or_its_text_is_open(self):
        good = fx("digest")
        only = good["must"][2]["links"][0]
        lone = edit(good, ["must", 2, "links"], [{**only, "ch": "nobody_here", "url": "https://t.me/nobody_here/5"}])
        self.assertEqual(codes(C.check_edition(lone, self.src)), [("empty", "item"), ("url", "link")])
        pruned, _ = C.prune(lone, self.src)
        self.assertEqual(([x["id"] for x in pruned["must"]], pruned["funnel"]["must"]), ([x["id"] for x in good["must"][:2]], 2))
        open_text = edit(good, ["rest", 0, "items", 0, "terms"], [F.CANARIES[0]])
        self.assertEqual(codes(C.check_edition(open_text, self.src)), [("open", "item")])
        pruned, _ = C.prune(open_text, self.src)
        self.assertEqual([g["cell"] for g in pruned["rest"]], [g["cell"] for g in good["rest"][1:]])      # 빈 칸 묶음은 남기지 않는다
        self.assertEqual(C.check_edition(pruned, self.src), [])

    def test_rows_go_one_by_one(self):
        good = fx("digest")
        d = edit(good, ["wire", "rows", 1, "v"], "약 0.4%p")
        d["solo"]["rows"][0].update(ch="fxbond1", url="https://t.me/fxbond1/502")       # 개인 단독 절에 채권 채널
        d["context"][0].update(ch="fxpers1", url="https://t.me/fxpers1/3001")           # 참고 채널이 아님
        self.assertEqual(codes(C.check_edition(d, self.src)), [("open", "row"), ("role", "row")])
        pruned, found = C.prune(d, self.src)
        self.assertEqual(len(found), 3)
        self.assertEqual((len(pruned["wire"]["rows"]), len(pruned["solo"]["rows"]), pruned["context"]),
                         (len(good["wire"]["rows"]) - 1, len(good["solo"]["rows"]) - 1, []))
        self.assertEqual(C.check_edition(pruned, self.src), [])

    def test_rate_out_of_range_costs_only_that_rate(self):
        good = fx("digest")
        for value in (0, 20.0, 20, 27.5):
            with self.subTest(value):
                d = edit(good, ["head", "kr10", "value"], value)
                self.assertEqual(codes(C.check_edition(d, self.src)), [("rate", "rate")])
                head = C.prune(d, self.src)[0]["head"]
                self.assertEqual((head["kr10"], head["dir"], head["curve"], head["basis"]), (None, None, None, None))
                self.assertEqual(head["kr3"], good["head"]["kr3"])
        self.assertEqual(codes(C.check_edition(edit(good, ["head", "us10", "value"], 20.0), self.src)), [("rate", "rate")])
        self.assertEqual(C.check_edition(edit(good, ["head", "us10", "value"], 19.999), self.src), [])

    def test_what_pruning_cannot_fix_stops_the_edition(self):
        good = fx("digest")
        cases = {
            "지어 쓴 알림 줄": edit(good, ["notes"], ["오늘은 좋은 날"]),
            "개수 불일치": edit(good, ["funnel", "candidates"], 99),
            "판 날짜": edit(good, ["date"], "2026-10-07"),
            "모드": edit(good, ["mode"], "ai"),
            "내일 볼 것": edit(good, ["tomorrow", 0, "term"], "미국 생산자물가 발표"),
            "목록이 아닌 칸": edit(good, ["must"], "없음"),
            "객체가 아님": [1, 2, 3],
        }
        for name, bad in cases.items():
            with self.subTest(name):
                self.assertIn("edition", {s for _, s in codes(C.check_edition(bad, self.src))})
        old, C.EDITION_BYTES = C.EDITION_BYTES, 2_000
        try:
            self.assertEqual(codes(C.check_edition(good, self.src)), [("size", "edition")])
        finally:
            C.EDITION_BYTES = old
        self.assertEqual(C.EDITION_BYTES, 20_000)


class HeadTest(unittest.TestCase):
    def head(self, **change):
        h = copy.deepcopy(fx("head"))
        for k, v in change.items():
            h[k] = {**h[k], **v} if isinstance(v, dict) else v
        return C.head_line(h, F.WINDOW)

    def test_sample_head_is_already_in_line(self):
        self.assertEqual(self.head(), fx("head"))

    def test_stale_rate_blanks_the_direction(self):
        """자료일의 마감이 수집 창 밖이면 방향 칸을 비우고 '전일 종가'로 적는다 — 앞 단계가 맞다고 적어 와도 다시 셈한다."""
        h = self.head(kr10={"asof": "2026-10-07", "fits": True})
        self.assertEqual((h["kr10"]["fits"], h["dir"], h["curve"], h["basis"]), (False, None, None, "전일 종가"))
        h = self.head(kr3={"asof": "2026-10-07"})
        self.assertEqual((h["kr3"]["fits"], h["dir"], h["curve"], h["basis"]), (False, "보합", None, "당일 종가"))
        h = self.head(us10={"asof": "2026-10-06"})
        self.assertEqual((h["us10"]["fits"], h["dir"], h["curve"]), (False, "보합", "플랫"))          # 미 10년은 방향 칸과 무관
        h = self.head(kr10=None)
        self.assertEqual((h["kr10"], h["dir"], h["curve"], h["basis"]), (None, None, None, None))

    def test_direction_needs_a_move_beyond_one_bp(self):
        for chg, want in ((1.0, "보합"), (1.1, "약세"), (-1.0, "보합"), (-1.1, "강세"), (0, "보합"), (None, None)):
            self.assertEqual(self.head(kr10={"chg_bp": chg})["dir"], want, chg)
        for chg10, chg3, want in ((3.0, 1.0, "스팁"), (3.0, 2.0, "보합"), (0.7, 2.8, "플랫"), (None, 2.8, None), (0.7, None, None)):
            self.assertEqual(self.head(kr10={"chg_bp": chg10}, kr3={"chg_bp": chg3})["curve"], want, (chg10, chg3))

    def test_curve_needs_both_rates_from_the_same_day(self):
        """창이 길면(주말) 두 자료일이 모두 창 안이어도 서로 다른 날일 수 있다 — 그러면 10년−3년 변화는 뜻이 없다."""
        long = {"from": "2026-10-05T18:00:00+09:00", "to": F.NOW}
        h = C.head_line({**fx("head"), "kr3": {**fx("head")["kr3"], "asof": "2026-10-07"}}, long)
        self.assertEqual((h["kr10"]["fits"], h["kr3"]["fits"], h["dir"], h["curve"]), (True, True, "보합", None))

    def test_input_is_left_alone(self):
        h = fx("head")
        before = copy.deepcopy(h)
        C.head_line(h, F.WINDOW)
        self.assertEqual(h, before)


def short_set(must=()):
    """수집 부족인 날의 한 벌 — 채권 세 곳을 못 읽었다."""
    fail = {"fxbond1": "fetch", "fxbond2": "fetch", "fxbond3": "empty"}
    cs = F.collect_status(fail=fail)
    d = {**fx("digest"), "status": "short", "must": list(must), "notes": [R.phrase("note_short")]}
    d["funnel"] = {**d["funnel"], "must": len(d["must"])}
    d["sources"] = {"channels_ok": 21, "channels_total": 24}
    keep = ("ch", "ok", "code", "posts", "with_text", "in_window", "fail_streak")
    counts = {k: v for k, v in S.coverage_verdict(cs["channels"]).items() if k != "verdict"}
    status = {**fx("status"), "ok": False, "reason": "short", "counts": counts, "last_success": None,
              "channels": [{k: c[k] for k in keep} for c in cs["channels"]]}
    state = fx("state_after")
    state["edition"]["must"] = []
    index = fx("index")
    index["editions"][0] = C.index_row(d)
    return {"digest": d, "digest_index": index, "digest_state": state, "digest_status": status}


class HealthTest(FolderCase):
    def test_short_collection_must_empty_the_top_and_say_so(self):
        good = short_set()
        self.assertEqual(self.check(**good)[0], [])
        self.assertEqual(self.cli()[0], 0)
        self.assertEqual(self.cli("--alert")[0], 2)                         # 판은 맞지만 실행은 실패로 끝내야 한다
        hidden = {**good, "digest_status": {**good["digest_status"], "ok": True, "reason": "ok"}}
        self.assertEqual(codes(self.check(**hidden)[0]), [("coverage", "edition")])
        full = short_set(must=fx("digest")["must"][:1])                       # 수집 부족인데 꼭 볼 것을 실었다
        self.assertTrue(self.check(**full)[0])
        counts = edit(good["digest_status"], ["counts", "bond_ok"], 5)
        self.assertEqual(codes(self.check(**{**good, "digest_status": counts})[0]), [("coverage", "edition")])

    def test_status_must_not_claim_short_when_the_numbers_are_fine(self):
        status = {**fx("status"), "ok": False, "reason": "short"}
        self.assertEqual(codes(self.check(digest_status=status)[0]), [("coverage", "edition")])

    def streak_set(self, before, must, bond_new=True, claim=None, reason=None):
        """직전 판까지 0건이 before판 이어졌고, 이번 판의 꼭 볼 것이 must건인 한 벌."""
        d = fx("digest")
        d = {**d, "must": d["must"][:must], "funnel": {**d["funnel"], "must": must},
             "notes": [] if must == 3 else [R.phrase("note_none") if must == 0 else R.phrase("note_fewer", n=must)]}
        state = fx("state_after")
        state["base"]["empty_streak"] = before
        state["edition"]["must"] = state["edition"]["must"][:must]
        want = C.next_streak("ok", must, bond_new, before)
        state["edition"]["empty_streak"] = want if claim is None else claim
        status = fx("status")
        if not bond_new:
            groups = {c["handle"]: c["group"] for c in self.src["channels"]}
            for c in status["channels"]:
                c["in_window"] = 0 if groups[c["ch"]] == "bond" else c["in_window"]
        streak = state["edition"]["empty_streak"]
        why = reason or ("empty_streak" if streak >= R.TH["empty_streak_fail"] else "ok")
        status = {**status, "empty_streak": streak, "ok": why == "ok", "reason": why}
        index = fx("index")
        index["editions"][0] = C.index_row(d)
        return {"digest": d, "digest_index": index, "digest_state": state, "digest_status": status}

    def test_three_empty_editions_in_a_row_must_be_flagged(self):
        self.assertEqual(self.check(**self.streak_set(1, 0))[0], [])
        self.assertEqual(self.cli("--alert")[0], 0)                         # 2판째 — 아직 알리지 않는다
        self.assertEqual(self.check(**self.streak_set(2, 0))[0], [])
        self.assertEqual(self.cli("--alert")[0], 2)                         # 3판째 — 실패로 끝낸다
        self.assertEqual(codes(self.check(**self.streak_set(2, 0, reason="ok"))[0]), [("streak", "edition")])
        self.assertEqual(codes(self.check(**self.streak_set(2, 0, claim=0))[0]), [("streak", "edition")])
        self.assertEqual(self.check(**self.streak_set(2, 1))[0], [])        # 한 건이라도 실리면 0으로 돌아간다
        self.assertEqual(self.cli("--alert")[0], 0)

    def test_day_without_bond_posts_is_not_counted(self):
        self.assertEqual(C.next_streak("ok", 0, 0, 2), 2)
        self.assertEqual(C.next_streak("ok", 0, 7, 2), 3)
        self.assertEqual(C.next_streak("ok", 2, 7, 2), 0)
        self.assertEqual(C.next_streak("short", 0, 7, 2), 2)                # 수집 부족·내린 판은 세지도 지우지도 않는다
        self.assertEqual(C.next_streak("withdrawn", 0, 7, 2), 2)
        self.assertEqual(self.check(**self.streak_set(2, 0, bond_new=False))[0], [])
        self.assertEqual(self.cli("--alert")[0], 0)
        self.assertEqual(codes(self.check(**self.streak_set(2, 0, bond_new=False, claim=3))[0]), [("streak", "edition")])

    def test_status_only_folder(self):
        """형식이 바뀐 날(본문 비율이 절반 아래)과 실행 실패는 상태 파일만 낸다."""
        cs = fx("collect_status")
        chans = [{"ch": c["ch"], "ok": c["ok"], "code": c["code"], "posts": c["posts"], "with_text": 1, "in_window": c["in_window"],
                  "fail_streak": 0} for c in cs["channels"]]
        counts = {k: v for k, v in S.coverage_verdict([{**c, "group": F.GROUP[c["ch"]]} for c in chans]).items() if k != "verdict"}
        broken = {**fx("status"), "ok": False, "reason": "broken", "published": False, "channels": chans, "counts": counts}
        error = {**fx("status"), "ok": False, "reason": "error", "published": False, "channels": [],
                 "counts": dict.fromkeys(counts, 0)}
        for name, status in (("broken", broken), ("error", error)):
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                self.pub = put(tmp, {"digest_status.json": status})
                found, facts = C.check_folder(self.pub, self.src)
                self.assertEqual((found, facts["published"], facts["reason"]), ([], False, name))
                self.assertEqual((self.cli()[0], self.cli("--alert")[0]), (0, 2))
        with tempfile.TemporaryDirectory() as tmp:                           # 본문 비율이 절반 아래인데 판을 냈다
            self.pub = put(tmp, docs(digest_status={**fx("status"), "channels": chans, "counts": counts}))
            self.assertEqual(codes(C.check_folder(self.pub, self.src)[0]), [("coverage", "edition")])
        with tempfile.TemporaryDirectory() as tmp:                           # 상태 파일이 없으면 볼 것이 없다
            self.pub = put(tmp, {"digest.json": fx("digest")})
            self.assertEqual(codes(C.check_folder(self.pub, self.src)[0]), [("missing", "edition")])


class CrossTest(FolderCase):
    def test_files_must_agree_with_each_other(self):
        d = fx("digest")
        other = edit(d, ["funnel", "truncated"], 1)
        cases = {
            "날짜별 판이 오늘 판과 다름": {"digest.json": other},
            "목차의 줄이 판과 다름": {"digest_index.json": edit(fx("index"), ["editions", 0, "must"], 2)},
            "목차에 이 판이 없음": {"digest_index.json": {**fx("index"), "editions": fx("index")["editions"][1:], "latest": "2026-10-07"}},
            "상태의 판 날짜": {"digest_status.json": {**fx("status"), "edition": "2026-10-07"}},
            "상태 기록의 창": {"digest_state.json": edit(fx("state_after"), ["edition", "window", "from"], "2026-10-07T18:00:00+09:00")},
            "상태 기록의 꼭 볼 것": {"digest_state.json": edit(fx("state_after"), ["edition", "must"], [])},
            "파일 하나가 없음": {"digest_state.json": None},
            "날짜별 판이 없음": {DAY: None},
        }
        for name, change in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                found, _ = C.check_folder(put(tmp, {**docs(), **change}), self.src)
                self.assertTrue({c for c, _ in codes(found)} & {"cross", "missing"}, codes(found))
                self.assertEqual({s for _, s in codes(found)}, {"edition"})

    def test_withdrawn_edition_is_consistent_on_its_own_terms(self):
        d = S.blank_digest(S.parse_iso(F.NOW))
        state = fx("state")                                                    # 내린 날 — 상태 기록은 지난 판 그대로일 수 있다
        state["edition"]["must"] = []
        status = {**fx("status"), "checked_at": d["collected_at"], "ok": False, "reason": "withdrawn", "last_success": None,
                  "channels": [], "counts": dict.fromkeys(fx("status")["counts"], 0)}
        index = {"schema": 1, "updated_at": d["collected_at"], "latest": d["date"], "editions": [C.index_row(d)]}
        with tempfile.TemporaryDirectory() as tmp:
            self.pub = put(tmp, {"digest.json": d, DAY: d, "digest_index.json": index, "digest_state.json": state,
                                 "digest_status.json": status})
            self.assertEqual(C.check_folder(self.pub, self.src)[0], [])
            self.assertEqual(self.cli("--alert")[0], 0)                      # 일부러 내린 것은 실패가 아니다
            for change in ({"reason": "ok", "ok": True}, {"published": False}):     # 내린 판인데 상태가 다른 말을 한다
                put(tmp, {"digest_status.json": {**status, **change}})
                self.assertIn(("coverage", "edition"), codes(C.check_folder(self.pub, self.src)[0]), change)
        self.assertEqual(codes(self.check(digest_status={**status, "reason": "ok", "ok": True})[0])[0][1], "edition")
        says_down = {**fx("status"), "ok": False, "reason": "withdrawn"}       # 판은 정상인데 상태만 '내림'이라고 한다
        self.assertIn(("coverage", "edition"), codes(self.check(digest_status=says_down)[0]))

    def test_index_row(self):
        self.assertEqual(C.index_row(fx("digest")), fx("index")["editions"][0])


class RawTest(FolderCase):
    def test_links_must_point_at_posts_that_were_collected(self):
        good = fx("digest")
        ghost = edit(good, ["must", 0, "links", 0], {**good["must"][0]["links"][0], "url": "https://t.me/fxbond1/777"})
        self.assertEqual(self.check(digest=ghost)[0], [])                   # 원문 없이는 알 수 없다
        self.assertEqual(codes(self.check(raw=True, digest=ghost)[0]), [("unseen", "link")])
        moved = edit(good, ["wire", "rows", 0, "at"], "2026-10-08T08:02:00+09:00")
        self.assertEqual(codes(self.check(raw=True, digest=moved)[0]), [("unseen", "row")])
        old = edit(good, ["context", 0], {"ch": "fxctx1", "at": "2026-10-08T16:09:00+09:00", "url": "https://t.me/fxctx1/4099"})
        self.assertEqual(codes(self.check(raw=True, digest=old)[0]), [("unseen", "row")])

    def test_words_and_numbers_must_come_from_the_posts(self):
        good = fx("digest")
        self.assertEqual(codes(self.check(raw=True, digest=edit(good, ["wire", "rows", 0, "v"], "9.9%"))[0]), [("mismatch", "row")])
        self.assertEqual(codes(self.check(raw=True, digest=edit(good, ["wire", "rows", 0, "term"], "FOMC"))[0]), [("mismatch", "row")])
        self.assertEqual(codes(self.check(raw=True, digest=edit(good, ["must", 0, "nums", 0, "v"], "77.7%"))[0]), [("mismatch", "item")])
        self.assertEqual(codes(self.check(raw=True, digest=edit(good, ["must", 2, "terms"], ["잭슨홀"]))[0]), [("mismatch", "item")])

    def test_raw_folder_must_be_the_same_run(self):
        doc = fx("posts_doc")
        doc["window"]["from"] = "2026-10-07T18:01:00+09:00"
        S.write_json(os.path.join(self.raw, "posts.json"), doc)
        self.assertEqual(codes(self.check(raw=True)[0]), [("cross", "edition")])
        put_raw(self.raw)
        S.write_json(os.path.join(self.raw, "collect_status.json"), F.collect_status(fail={"fxpers8": "fetch"}))
        self.assertEqual(codes(self.check(raw=True)[0]), [("cross", "edition")])       # 건강 숫자가 수집 기록과 다르다


class CliTest(FolderCase):
    def test_output_shows_places_and_codes_only(self):
        d = edit(fx("digest"), ["must", 0, "terms", 0], F.CANARIES[0])
        d["must"][0]["links"][0] = {**d["must"][0]["links"][0], "ch": "nobody_here", "url": "https://t.me/nobody_here/5"}
        put(self.pub, docs(digest=d))
        code, text = self.cli()
        self.assertEqual(code, 1)
        self.assertIn("[digest_check] 위반 file=digest.json code=url scope=link at=$.must[0].links[0]", text)
        self.assertIn("code=open scope=item at=$.must[0]", text)
        self.assertRegex(text, r"\[digest_check\] files=5 published=True reason=ok edition=2026-10-08 violations=\d+\n$")
        self.assertNotIn("nobody_here", text)
        self.assertEqual(F.leaks(text), [])

    def test_place_names_from_data_are_masked(self):
        state = fx("state_after")
        state["edition"]["channels"]["zqx7_planted_key"] = {"last_post": "x", "last_at": None, "fail_streak": 0}
        put(self.pub, docs(digest_state=state))
        code, text = self.cli()
        self.assertEqual(code, 1)
        self.assertIn("file=digest_state.json code=shape scope=edition at=state.edition.channels.?", text)
        self.assertEqual(F.leaks(text), [])

    def test_broken_inputs_fail_quietly(self):
        put(self.pub, docs())
        with open(self.src_path, "w", encoding="utf-8") as f:
            f.write('{"channels": "' + F.CANARIES[0])
        code, text = self.cli()
        self.assertEqual((code, text), (1, "[digest_check] 실패: ValueError\n"))
        S.write_json(self.src_path, self.src)
        code, text = self.cli("--public", os.path.join(self.tmp.name, "nowhere"))
        self.assertEqual((code, text), (1, "[digest_check] 실패: FileNotFoundError\n"))

    def test_check_never_writes(self):
        put(self.pub, docs())
        before = {n: os.path.getmtime(os.path.join(r, n)) for r, _, ns in os.walk(self.tmp.name) for n in ns}
        self.cli(raw=True)
        after = {n: os.path.getmtime(os.path.join(r, n)) for r, _, ns in os.walk(self.tmp.name) for n in ns}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
