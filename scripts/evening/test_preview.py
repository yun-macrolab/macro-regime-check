#!/usr/bin/env python3
"""저녁판 미리 보기(preview.py) 테스트 — 지어낸 판의 경우들이 계약대로인지, 날짜가 물은 날을 따르는지, 실제 결과는 검사를 통과한 것만
조립하는지, 공개 폴더에는 쓰지 않는지. 도구(가짜 문서 · 지어낸 판)는 test_evening_site.py의 것을 쓴다.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요 — 자료는 fixtures.py의 지어낸 글로 만든 판뿐이다.
"""
import contextlib
import copy
import datetime
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_schema as S
import fixtures as F
import preview as PV
from test_evening_site import C1, NODE, REPO, Screen, blob, draws, fx, named


class PreviewTest(Screen):
    DAY = datetime.date(2026, 10, 12)              # 월요일 — 지난 판들이 주말을 건너뛰는지 같이 본다

    def test_every_case_is_valid_closed_and_free_of_planted_text(self):
        handles = S.handles_of(fx("sources"))
        for case in PV.CASES:
            docs = PV.build(case, self.DAY)                                      # 안에서 형태를 검증한다 — 틀리면 ValueError
            self.assertEqual(F.leaks(S.dump(docs)), [], case)
            for name, doc in docs.items():
                if name != "sources.json":                                       # 출처 목록의 라벨은 사람이 쓴 글이라 따로 본다
                    self.assertEqual(S.closed_violations(doc, handles), [], (case, name))
        with self.assertRaises(ValueError):
            PV.build("없는 경우", self.DAY)

    def test_dates_follow_the_day_asked_for(self):
        docs = PV.build("ok", self.DAY)
        self.assertEqual(docs["digest.json"]["date"], "2026-10-12")
        days = ["2026-10-12", "2026-10-09", "2026-10-08", "2026-10-07"]           # 월 → 금 → 목 → 수
        self.assertEqual([e["date"] for e in docs["digest_index.json"]["editions"]], days)
        self.assertEqual(sorted(n for n in docs if n.startswith("digest/")), sorted(f"digest/{d}.json" for d in days))
        self.assertEqual(PV.build("late", self.DAY)["digest.json"]["date"], "2026-10-08")      # 평일로 이틀 전
        failed = PV.build("failed", self.DAY)
        self.assertEqual((failed["digest.json"]["date"], failed["digest_status.json"]["edition"]), ("2026-10-09", "2026-10-12"))
        self.assertEqual(sorted(PV.build("empty", self.DAY)), ["calendar.json", "digest_overrides.json", "sources.json"])
        hidden = PV.build("hidden", self.DAY)
        self.assertIn(hidden["digest_overrides.json"]["hide_ids"][0], [x["id"] for x in hidden["digest.json"]["must"]])

    def test_shift_moves_dates_times_and_ids_and_nothing_else(self):
        src = {"date": "2026-10-08", "at": "2026-10-08T23:59:00+09:00", "id": "20261008-fxbond1-501", "time": "21:30", "v": "3.1%",
               "key": "f:e7b13565420b", "n": 3, "list": ["2026-12-31", None, True]}
        before = copy.deepcopy(src)
        moved = {**src, "date": "2026-10-09", "at": "2026-10-09T23:59:00+09:00", "id": "20261009-fxbond1-501",
                 "list": ["2027-01-01", None, True]}
        self.assertEqual(PV.shift(src, 1), moved)
        self.assertEqual(src, before)                                            # 받은 자료는 고치지 않는다
        self.assertEqual(PV.shift(fx("digest"), 0), fx("digest"))

    def test_edition_day_goes_back_to_a_weekday(self):
        def at(day, hour):
            return datetime.datetime(2026, 10, day, hour, 0, tzinfo=S.KST)
        self.assertEqual(PV.edition_day(at(8, 18)).isoformat(), "2026-10-08")
        self.assertEqual(PV.edition_day(at(10, 12)).isoformat(), "2026-10-09")   # 토요일 낮 → 금요일
        self.assertEqual(PV.edition_day(at(12, 3)).isoformat(), "2026-10-09")    # 월요일 새벽(판 날짜는 일요일) → 금요일
        self.assertEqual(PV.back(datetime.date(2026, 10, 12), 2).isoformat(), "2026-10-08")

    def test_assemble_writes_the_site_and_the_data_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            n = PV.assemble(tmp, PV.build("ok", self.DAY))
            self.assertEqual(n, 10)
            for rel in ("index.html", "evening.js", "evening.css", "dashboard.css", "data/digest.json", "data/digest/2026-10-09.json",
                        "data/sources.json", "data/digest_overrides.json"):
                self.assertTrue(os.path.isfile(os.path.join(tmp, *rel.split("/"))), rel)
            self.assertEqual(S.read_json(os.path.join(tmp, "data", "sources.json")), fx("sources"))      # 가짜 채널 목록
            PV.assemble(tmp, PV.build("empty", self.DAY))
            self.assertFalse(os.path.exists(os.path.join(tmp, "data", "digest.json")))                 # 앞서 조립한 판을 치운다
            self.assertEqual(os.listdir(os.path.join(tmp, "data", "digest")), [])

    def test_real_results_are_previewed_as_made_and_only_after_the_check(self):
        """--from: 파이프라인이 낸 공개 폴더(digest_build --out)와 사람이 쓰는 파일로 조립한다. 날짜를 옮기지 않고, 검사에 걸린 폴더는 받지 않는다."""
        d = fx("digest")
        made = {"digest.json": d, f"digest/{F.EDITION}.json": d, "digest_index.json": fx("index"),
                "digest_state.json": fx("state_after"), "digest_status.json": fx("status")}
        human = {"sources.json": fx("sources"), "calendar.json": fx("calendar"), "digest_overrides.json": F.overrides()}
        with tempfile.TemporaryDirectory() as tmp:
            pub, data, out = (os.path.join(tmp, n) for n in ("public", "data", "preview"))
            for folder, files in ((pub, made), (data, human)):
                for name, doc in files.items():
                    S.write_json(os.path.join(folder, *name.split("/")), doc)
            docs = PV.real(pub, data)
            self.assertEqual(sorted(docs), sorted([*made, *human]))
            self.assertEqual((docs["digest.json"], docs["sources.json"]), (d, human["sources.json"]))      # 낸 그대로
            with contextlib.redirect_stdout(io.StringIO()) as said:
                self.assertEqual(PV.main(["--from", pub, "--data", data, "--out", out]), 0)
            self.assertIn("files=8", said.getvalue())
            self.assertEqual(S.read_json(os.path.join(out, "data", "digest", f"{F.EDITION}.json")), d)
            self.assertTrue(os.path.isfile(os.path.join(out, "evening.js")))
            S.write_json(os.path.join(pub, "digest.json"), {**d, "notes": [C1]})                         # 닫히지 않은 글자가 든 판
            with self.assertRaises(ValueError):
                PV.real(pub, data)
            os.remove(os.path.join(data, "sources.json"))                                                # 출처 목록 없이는 검사할 수 없다
            with self.assertRaises(FileNotFoundError):
                PV.real(pub, data)

    def test_assemble_refuses_the_public_folders(self):
        def tree():
            tops = (os.path.join(REPO, top) for top in ("data", "site"))
            return sorted(os.path.join(d, f) for top in tops for d, _, fs in os.walk(top) for f in fs)
        before = tree()
        for out in (os.path.join(REPO, "data"), os.path.join(REPO, "site"), REPO, os.path.join(REPO, "data", "preview")):
            with self.assertRaises(ValueError):
                PV.assemble(out, PV.build("ok", self.DAY))
        self.assertEqual(tree(), before)                                         # 가짜 채널 주소가 공개 폴더에 들어가지 않는다

    @unittest.skipUnless(NODE, "node가 없다")
    def test_every_case_draws(self):
        want = {"ok": "꼭 3건", "fewer": "꼭 2건", "none": "오늘은 기준을 넘은 묶음이 없습니다", "short": "수집 부족",
                "partial": "24채널 중 23 읽음", "hidden": "표시하지 않은 항목 1건", "withdrawn": "이 판은 내렸습니다",
                "late": "10-09(금) 판이 아직 없습니다", "failed": "판을 내지 않았습니다", "empty": "아직 판이 없습니다"}
        self.assertEqual(set(want), set(PV.CASES))
        frames = draws(*[(named(PV.build(case, self.DAY)), "2026-10-12T19:00:00+09:00") for case in want])
        for (case, text), frame in zip(want.items(), frames):
            self.shows(frame, text)
            self.assertEqual(F.leaks(blob(frame)), [], case)


if __name__ == "__main__":
    unittest.main()
