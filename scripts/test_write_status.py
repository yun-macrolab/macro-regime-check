#!/usr/bin/env python3
"""갱신 상태(write_status) 테스트 — 사이트 첫 화면의 '마지막 성공 시각·실패 배너'가 여기서 나온다.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
실패한 날에도 상태 파일은 써야 하고(배너), 마지막 성공 시각과 공개본 날짜는 직전 값을 지켜야 한다.
문구는 정해 둔 것만 — 오류 원문(경로·URL·예외 문자열)은 공개 페이지에 싣지 않는다.
"""
import os, sys, json, re, datetime, tempfile, unittest, shutil

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import write_status as ws
from test_regime import run_cli

NOW = datetime.datetime(2026, 9, 28, 22, 20, 11, tzinfo=datetime.timezone.utc)
EARLIER = datetime.datetime(2026, 9, 25, 22, 19, 0, tzinfo=datetime.timezone.utc)
ENV = {"GITHUB_SERVER_URL": "https://github.com", "GITHUB_REPOSITORY": "someone/macro-regime-check",
       "GITHUB_RUN_ID": "123456789"}


class WriteStatusTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.out = os.path.join(self.tmp, "data")
        os.makedirs(self.out)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def put_public(self, date):
        with open(os.path.join(self.out, "public.json"), "w", encoding="utf-8") as f:
            json.dump({"schema": 1, "date": date}, f)

    def status(self):
        with open(os.path.join(self.out, "status.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_success(self):
        self.put_public("2026-09-28")
        st = ws.update(self.out, "success", "success", now=NOW, env=ENV)
        self.assertEqual(st, self.status())
        self.assertTrue(st["ok"])
        self.assertEqual(st["stage"], "ok")
        self.assertEqual(st["data_date"], "2026-09-28")
        self.assertEqual(st["checked_at"], "2026-09-28T22:20:11+00:00")
        self.assertEqual(st["last_success"], st["checked_at"])
        self.assertEqual(st["run_url"], "https://github.com/someone/macro-regime-check/actions/runs/123456789")

    def test_fetch_failure_keeps_last_success_and_data_date(self):
        self.put_public("2026-09-25")
        ws.update(self.out, "success", "success", now=EARLIER, env=ENV)
        st = ws.update(self.out, "failure", "skipped", now=NOW, env=ENV)
        self.assertFalse(st["ok"])
        self.assertEqual(st["stage"], "fetch")
        self.assertEqual(st["last_success"], "2026-09-25T22:19:00+00:00")
        self.assertEqual(st["data_date"], "2026-09-25")
        self.assertEqual(st["checked_at"], "2026-09-28T22:20:11+00:00")
        self.assertEqual(st["message"], ws.MESSAGES["fetch"])

    def test_render_failure(self):
        self.put_public("2026-09-25")
        st = ws.update(self.out, "success", "failure", now=NOW, env=ENV)
        self.assertFalse(st["ok"])
        self.assertEqual(st["stage"], "render")
        self.assertIsNone(st["last_success"])     # 성공한 적 없음

    def test_success_without_public_is_not_ok(self):
        # 단계가 성공이라고 해도 공개본이 없으면 성공이 아니다
        st = ws.update(self.out, "success", "success", now=NOW, env=ENV)
        self.assertFalse(st["ok"])
        self.assertEqual(st["stage"], "render")
        self.assertIsNone(st["data_date"])

    def test_cancelled_or_unknown_outcome_is_failure(self):
        self.put_public("2026-09-25")
        for fetch, render, stage in (("cancelled", "skipped", "fetch"), ("", "", "fetch"),
                                     ("success", "cancelled", "render"), ("success", "", "render")):
            st = ws.update(self.out, fetch, render, now=NOW, env=ENV)
            self.assertFalse(st["ok"], (fetch, render))
            self.assertEqual(st["stage"], stage)

    def test_only_fixed_strings(self):
        self.put_public("2026-09-28")
        for fetch, render in (("success", "success"), ("failure", "skipped"), ("success", "failure")):
            st = ws.update(self.out, fetch, render, now=NOW, env=ENV)
            self.assertIn(st["message"], ws.MESSAGES.values())
            self.assertEqual(set(st), set(ws.KEYS))

    def test_run_url_only_from_valid_env(self):
        self.put_public("2026-09-28")
        self.assertIsNone(ws.update(self.out, "success", "success", now=NOW, env={})["run_url"])
        bad = {**ENV, "GITHUB_REPOSITORY": "x/y\"><script>", "GITHUB_RUN_ID": "12a"}
        self.assertIsNone(ws.update(self.out, "success", "success", now=NOW, env=bad)["run_url"])
        other = {**ENV, "GITHUB_SERVER_URL": "https://evil.example"}
        self.assertIsNone(ws.update(self.out, "success", "success", now=NOW, env=other)["run_url"])

    def test_broken_previous_status_is_ignored(self):
        with open(os.path.join(self.out, "status.json"), "w", encoding="utf-8") as f:
            f.write("{not json")
        self.put_public("2026-09-28")
        st = ws.update(self.out, "failure", "skipped", now=NOW, env=ENV)
        self.assertIsNone(st["last_success"])

    def test_previous_last_success_must_be_a_timestamp(self):
        with open(os.path.join(self.out, "status.json"), "w", encoding="utf-8") as f:
            json.dump({"last_success": "<img src=x>"}, f)
        self.put_public("2026-09-28")
        st = ws.update(self.out, "failure", "skipped", now=NOW, env=ENV)
        self.assertIsNone(st["last_success"])

    def test_public_date_must_be_a_date(self):
        self.put_public("2026-09-28<b>")
        st = ws.update(self.out, "success", "success", now=NOW, env=ENV)
        self.assertIsNone(st["data_date"])
        self.assertFalse(st["ok"])


class WriteStatusCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.out = os.path.join(self.tmp, "data")
        os.makedirs(self.out)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_cli_one_line_and_exit_0_even_on_failure(self):
        # 실패를 기록하는 것 자체는 성공이다 — 워크플로가 이 뒤에 커밋·배포하고, 마지막에 따로 실패로 끝낸다
        r = run_cli("write_status.py", "--out", self.out, "--fetch", "failure", "--render", "skipped")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stderr, "")
        self.assertEqual(len(r.stdout.strip().splitlines()), 1)
        self.assertTrue(os.path.exists(os.path.join(self.out, "status.json")))

    def test_cli_missing_out_dir_fails_one_line(self):
        r = run_cli("write_status.py", "--out", os.path.join(self.tmp, "nope"), "--fetch", "success",
                    "--render", "success")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(len(r.stderr.strip().splitlines()), 1)
        self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
