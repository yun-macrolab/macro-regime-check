#!/usr/bin/env python3
"""저녁판 AI 요약(evening_llm)의 보강 테스트 — 물음 말고 다른 것이 모델에게 실리면 멈추는가(맥락 상한), 켜는 스위치를 보는가,
규칙판 실행을 제때에만 시작하는가(놓친 예약 작업이 아침 · 주말에 새 판을 내지 않게), 읽을거리가 모자란 항목을 묻지 않는가.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 · 모델 호출 · 실제 git이 없다 — 가짜 수신 · 가짜 claude · 가짜 git/gh로 돈다. 글은 fixtures.py의 지어낸 글이다.
"""
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_picks as K
import digest_rules as R
import digest_schema as S
import evening_llm as L
import fixtures as F
from test_evening_llm import CPI, GOOD, SHORT_OK, Claude, Net, fx, picked
from test_evening_llm_run import NOW, RunCase
from test_picks_push import MOD, NEW, OFF, Tool, good, runs

TH = R.TH
LONG = "지어낸 긴 글의 한 줄이다. " * 30
REAL = {"llm_read_min": 300}             # 이 파일의 다른 테스트는 짧은 지어낸 글로 돈다(SHORT_OK) — 하한을 볼 때만 되돌린다


def setUpModule():
    global _SHORT
    _SHORT = mock.patch.dict(R.TH, SHORT_OK)
    _SHORT.start()


def tearDownModule():
    _SHORT.stop()


class ContextTest(unittest.TestCase):
    """격리 — 도구가 없어도 사용자 폴더의 CLAUDE.md · rules 같은 것이 맥락에 실릴 수 있다(init의 네 칸에는 안 보인다).
    옵션과 환경 변수로 끄고, 그래도 실렸는지는 입력 토큰으로 본다."""

    def code(self, fn, *a, **kw):
        with self.assertRaises(L.Ask) as cm:
            fn(*a, **kw)
        return cm.exception.code

    def test_options_and_environment_switch_user_instructions_off(self):
        self.assertEqual(L.ARGS[:2], ("-p", "--safe-mode"))
        self.assertNotIn("--bare", L.ARGS)                                    # --bare는 구독 로그인을 읽지 않는다
        with mock.patch.dict(os.environ, {"PATH": "p", "CLAUDE_CODE_DISABLE_CLAUDE_MDS": "0", "GH_TOKEN": "x"}, clear=True):
            self.assertEqual(L.claude_env(os.environ), {"PATH": "p", "CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1"})

    def test_probe_stops_when_more_than_the_question_was_loaded(self):
        self.assertEqual(L.probe(Claude({}, tokens=TH["llm_probe_tokens"]), "claude-fx.exe"), TH["llm_probe_tokens"])
        self.assertEqual(self.code(L.probe, Claude({}, tokens=TH["llm_probe_tokens"] + 1), "claude-fx.exe"), "context")
        self.assertEqual(self.code(L.probe, Claude({}, tokens=9040), "claude-fx.exe"), "context")       # 검토에서 잰 값(규칙 파일 8개가 실렸다)
        self.assertEqual(L.probe(Claude({}, tokens=667), "claude-fx.exe"), 667)                         # 깨끗한 호출에서 잰 값
        self.assertEqual((TH["llm_probe_tokens"], TH["llm_char_tokens"]), (1000, 1.3))

    def test_main_call_is_bounded_by_the_size_of_the_question(self):
        prompt = "가" * 1000
        limit = TH["llm_probe_tokens"] + int(TH["llm_char_tokens"] * len(prompt))
        self.assertEqual(L.ask(prompt, [CPI], Claude({}, main_tokens=limit), "claude-fx.exe"), ({CPI: None}, "claude-fx-1"))
        self.assertEqual(self.code(L.ask, prompt, [CPI], Claude({}, main_tokens=limit + 1), "claude-fx.exe"), "context")

    def test_unreadable_usage_is_not_a_pass(self):
        for name, result in {"칸이 없음": {"usage": None}, "숫자가 아님": {"usage": {"input_tokens": "120"}}, "음수": {"usage": {"input_tokens": -1}},
                             "캐시 칸이 글자": {"usage": {"input_tokens": 3, "cache_read_input_tokens": "x"}}, "목록": {"usage": [120]}}.items():
            with self.subTest(name):
                self.assertEqual(self.code(L.probe, Claude({}, result=result), "claude-fx.exe"), "context")
        self.assertEqual(L.probe(Claude({}, result={"usage": {"input_tokens": 200}}), "claude-fx.exe"), 200)      # 캐시 칸이 없으면 0으로 센다

    def test_error_flag_must_be_present_and_false(self):
        done = {"type": "result", "subtype": "success", "result": "{}", "usage": {"input_tokens": 100}}
        init = {"type": "system", "subtype": "init", "tools": [], "mcp_servers": [], "skills": [], "slash_commands": []}
        self.assertEqual(self.code(L.probe, Claude({}, events=[init, done]), "claude-fx.exe"), "result")           # is_error 칸이 없다
        self.assertEqual(L.probe(Claude({}, events=[init, {**done, "is_error": False}]), "claude-fx.exe"), 100)

    def test_only_built_in_plugins(self):
        builtin = [{"name": "cc-plugin-agents-md", "path": "x"}, "cc-plugin-telemetry", {"name": "sec-default", "source": "sec-default@builtin"}]
        self.assertEqual(L.probe(Claude({}, plugins=builtin), "claude-fx.exe"), 120)
        self.assertEqual(L.probe(Claude({}, plugins=[]), "claude-fx.exe"), 120)
        for name, rows in {"밖에서 온 것": builtin + [{"name": "superpowers", "source": "superpowers@claude-plugins-official"}],
                           "이름이 없음": [{"path": "x"}], "목록이 아님": {"a": 1}}.items():
            with self.subTest(name):
                self.assertEqual(self.code(L.probe, Claude({}, plugins=rows), "claude-fx.exe"), "tools")


class EnoughToReadTest(unittest.TestCase):
    """읽을거리가 모자란 항목은 묻지 않는다 — 짧은 글 하나를 통째로 바꿔 쓴 문장이 검사를 통과했다(검토)."""

    def texts(self, **long):
        net = Net()
        got = L.read_posts(picked(), fx("sources"), L.live(net.open, net.sleep, net.clock))
        got.update({(k.rsplit("_", 1)[0], int(k.rsplit("_", 1)[1])): v for k, v in long.items()})
        return got

    def test_short_material_is_not_asked(self):
        names = K.names_of(fx("sources"))
        self.assertEqual(len(L.given(picked(), self.texts(), names)), 3)      # 하한을 끈 채로는 셋 다 묻는다
        with mock.patch.dict(R.TH, REAL):
            self.assertEqual(L.given(picked(), self.texts(), names), [])      # 지어낸 글은 모두 60자 안팎이다
            asked = L.given(picked(), self.texts(fxbond1_501=LONG), names)
        self.assertEqual([x["key"] for x in asked], [CPI])
        self.assertGreaterEqual(sum(map(len, asked[0]["texts"])), TH["llm_read_min"])
        self.assertEqual((REAL["llm_read_min"], TH["llm_chans_min"], SHORT_OK), (300, 1, {"llm_read_min": 0}))

    def test_channel_floor_can_be_raised(self):
        names, texts = K.names_of(fx("sources")), self.texts(fxbond1_501=LONG)
        only = {k: v for k, v in texts.items() if k == ("fxbond1", 501)}
        self.assertEqual(len(L.given(picked(), only, names)), 1)
        with mock.patch.dict(R.TH, {**REAL, "llm_chans_min": 2}):
            self.assertEqual(L.given(picked(), only, names), [])              # 한 채널의 글뿐인 항목을 묻지 않게 할 수 있다
            self.assertEqual(len(L.given(picked(), texts, names)), 1)


class DueTest(RunCase):
    """규칙판 실행을 시작할 때 — 판 날짜가 평일이고 17:30 뒤이고 그 판이 아직 없고 내린 판이 아닐 때만."""

    def due(self, now):
        return L.due(S.parse_iso(now), self.repo)

    def test_only_on_weekday_evenings_for_an_edition_not_yet_up(self):
        times = {"목 17:45": ("2026-10-15T17:45:00+09:00", True), "목 23:30": ("2026-10-15T23:30:00+09:00", True),
                 "금 03:00(목 판)": ("2026-10-16T03:00:00+09:00", True), "목 17:30": ("2026-10-15T17:30:00+09:00", True),
                 "목 17:29": ("2026-10-15T17:29:00+09:00", False), "금 08:40(놓친 실행)": ("2026-10-16T08:40:00+09:00", False),
                 "월 08:40": ("2026-10-12T08:40:00+09:00", False), "토 11:00": ("2026-10-17T11:00:00+09:00", False),
                 "토 19:00": ("2026-10-17T19:00:00+09:00", False), "토 03:00(금 판)": ("2026-10-17T03:00:00+09:00", True),
                 "금 06:00": ("2026-10-16T06:00:00+09:00", False)}
        for name, (now, want) in times.items():
            with self.subTest(name):
                self.assertEqual(self.due(now), want)
        self.assertEqual(TH["dispatch_from_min"], 17 * 60 + 30)

    def test_not_when_that_edition_is_already_up_or_taken_down(self):
        self.assertFalse(self.due("2026-10-08T23:30:00+09:00"))               # 그날 판(10-08)이 이미 올라와 있다
        self.assertFalse(self.due("2026-10-09T03:00:00+09:00"))
        self.assertTrue(self.due("2026-10-09T18:00:00+09:00"))
        S.write_json(os.path.join(self.data, "digest_overrides.json"), F.overrides(withdraw=True))
        self.assertFalse(self.due("2026-10-09T18:00:00+09:00"))               # 내리기 스위치
        S.write_json(os.path.join(self.data, "digest_overrides.json"), F.overrides())
        S.write_json(os.path.join(self.data, "digest.json"), S.blank_digest(S.parse_iso(F.NOW)))
        self.assertFalse(self.due("2026-10-09T18:00:00+09:00"))               # 내린 판을 PC가 다시 올리지 않는다
        with open(os.path.join(self.data, "digest.json"), "w", encoding="utf-8") as f:
            f.write("{broken")
        self.assertFalse(self.due("2026-10-09T18:00:00+09:00"))
        os.remove(os.path.join(self.data, "digest.json"))
        os.remove(os.path.join(self.data, "digest_overrides.json"))
        self.assertTrue(self.due("2026-10-09T18:00:00+09:00"))                # 아직 한 판도 없는 저장소

    def test_a_late_start_does_not_dispatch(self):
        for name, now in {"이튿날 아침": "2026-10-09T08:40:00+09:00", "토요일": "2026-10-10T11:00:00+09:00", "이미 올라옴": NOW}.items():
            with self.subTest(name):
                if os.path.exists(self.picks):
                    os.remove(self.picks)
                git = Tool(**good(status=[(0, ""), (0, NEW)]))
                code, out = self.go("--dispatch", git=git, now=now, net=Net())
                self.assertEqual((code, git.count("gh workflow run"), git.count("gh run list"), git.count("push")), (0, 0, 0, 1))
                self.assertIn("run switch=on dispatch=off code=ok", self.logged())    # 올라와 있는 판에 문장만 붙인다


class SwitchRunTest(RunCase):
    """켜는 스위치(EVENING_ENABLED)가 꺼져 있으면 규칙판 실행도, 채널 읽기도, 모델 호출도 하지 않는다."""
    LATER = "2026-10-09T18:20:00+09:00"

    def quiet(self, git, net=None):
        self.assertEqual((git.count("gh workflow run"), (net or self.net).calls, self.claude.calls), (0, [], []))

    def test_off_means_nothing_is_started_read_or_asked(self):
        git = Tool(**good(gh_variable_list=(0, OFF), status=(0, "")))
        code, out = self.go("--dispatch", git=git, now=self.LATER)
        self.assertEqual(code, 0, out)
        self.quiet(git)
        self.assertEqual(git.names(), ["gh variable list", "status", "fetch", "checkout"])
        self.assertIn("run switch=off dispatch=off code=ok", self.logged())
        self.assertIn("make result=off code=ok", self.logged())
        self.assertFalse(os.path.exists(self.picks))
        self.clean(self.logged(), out)

    def test_unreadable_switch_stops_everything(self):
        for name, got in {"gh 실패": 1, "변수 목록이 깨짐": (0, "{")}.items():
            with self.subTest(name):
                git = Tool(**good(gh_variable_list=got))
                code, out = self.go("--dispatch", git=git, now=self.LATER)
                self.assertEqual((code, git.names()), (2, ["gh variable list"]))
                self.quiet(git)
                self.assertIn("run switch=unread dispatch=skip code=switch", self.logged())

    def test_sentences_already_up_are_blanked_when_off(self):
        self.assertEqual(self.go()[0], 0)                                     # 켜져 있던 날 문장이 올라갔다
        self.assertEqual(len(self.doc()["items"]), 3)
        git = Tool(**good(gh_variable_list=(0, OFF), status=[(0, ""), (0, MOD)]))
        net = Net()
        code, out = self.go(git=git, net=net, now="2026-10-08T21:00:00+09:00")
        self.assertEqual((code, self.doc()["items"], git.count("push")), (0, [], 1))
        self.quiet(git, net)
        self.assertIn("picked=0 asked=0 posts=0 requests=0 kept=0 dropped=0 result=pushed code=ok", self.logged())
        code, out = self.go(git=Tool(**good(gh_variable_list=(0, OFF), status=(0, ""))), net=Net(), now="2026-10-08T22:00:00+09:00")
        self.assertEqual(code, 0)                                             # 빈 층이 올라간 뒤에는 할 일이 없다
        self.assertIn("make result=off code=ok", self.logged())

    def test_second_stage_reads_the_switch_itself_when_called_alone(self):
        git = Tool(**good(gh_variable_list=(0, OFF), status=(0, "")))
        code, out = self.go("--publish", git=git, cmd="make")
        self.assertEqual((code, git.names()), (0, ["gh variable list"]))
        self.quiet(git)
        code, out = self.go("--publish", git=Tool(**good(gh_variable_list=1)), cmd="make")
        self.assertEqual(code, 2)
        self.assertIn("make result=switch code=switch", self.logged())
        code, out = self.go("--publish", "--switch", "on", git=Tool(**good(gh_variable_list=1, status=(0, NEW))), cmd="make")
        self.assertEqual((code, len(self.doc()["items"])), (0, 3))            # run이 읽어 넘긴 값이 있으면 그것을 쓴다

    def test_dry_run_does_not_ask_the_switch(self):
        """켜기 전에 PC에서만 돌려 보는 길 — 올리지 않으니 스위치를 보지 않는다(git · gh를 부르지 않는다)."""
        git = Tool(gh_variable_list=1)
        code, out = self.go("--dry-run", git=git)
        self.assertEqual((code, git.calls), (0, []))


class ShortRunTest(RunCase):
    def test_items_without_enough_to_read_leave_an_empty_layer(self):
        """글은 받았지만 읽을거리가 모자란 날 — 실패가 아니다. 빈 층을 쓰고, 다음 실행에서는 같은 물음이라 다시 묻지 않는다."""
        with mock.patch.dict(R.TH, {"llm_read_min": 300}):
            code, out = self.go()
            self.assertEqual((code, self.doc()["items"], [c.probe for c in self.claude.calls]), (0, [], [True]))
            self.assertIn("picked=3 ctx=120 asked=0 posts=0 requests=7 kept=0 dropped=0 result=pushed code=ok", self.logged())
            code, out = self.go(git=Tool(**good(status=(0, ""))), net=Net(), now="2026-10-08T21:00:00+09:00")
            self.assertEqual((code, [c.probe for c in self.claude.calls]), (0, [True]))
            self.assertIn("requests=7 result=same code=ok", self.logged())

    def test_context_overflow_is_reported_by_code(self):
        code, out = self.go(claude=Claude(GOOD, tokens=9040))
        self.assertEqual((code, len(self.claude.calls), self.net.calls), (2, 1, []))      # 점검에서 멈췄다 — 글을 받지도 넣지도 않았다
        self.assertIn("picked=3 ctx=9040 code=context", self.logged())           # 얼마가 실렸는지는 남긴다
        self.assertFalse(os.path.exists(self.picks))


if __name__ == "__main__":
    unittest.main()
