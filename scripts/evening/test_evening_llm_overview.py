#!/usr/bin/env python3
"""저녁판 AI 요약 넓히기(2026-11-28 E3)의 실행 테스트 — 오늘 판 한 단락을 묻는 두 번째 본 호출, 넓힌 고르기로 한 번에 돌리기.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 · 모델 호출 · 실제 git이 없다 — 가짜 수신(Net) · 가짜 claude(Claude) · 가짜 git/gh(Tool)로 돈다. 글은 fixtures.py의 지어낸 글이다.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_picks as K
import digest_rules as R
import digest_schema as S
import evening_llm as L
import fixtures as F
from unittest import mock

from test_digest_overview import OVERVIEW
from test_evening_llm import AUCTION, CARD, CPI, GOOD, MUST_ONLY, REST3, SHORT_OK, WIDE, Claude, Net, fx
from test_evening_llm_run import NOW, RunCase

TH = R.TH


def setUpModule():
    global _SHORT
    _SHORT = mock.patch.dict(R.TH, {**SHORT_OK, **MUST_ONLY})
    _SHORT.start()


def tearDownModule():
    _SHORT.stop()


class OverviewPromptTest(unittest.TestCase):
    """한 단락의 물음 — 실린 문장과 규칙판의 닫힌 값뿐. 채널 글 · 채널 이름 · 심어 둔 글자가 없다."""

    def rows(self):
        return L.overview_rows(fx("digest"), [{"key": k} for k in (CPI, AUCTION, CARD)], GOOD)

    def test_only_facts_and_board_values(self):
        text = L.overview_prompt(self.rows(), "abc123")
        self.assertIn(L.OVERVIEW_RULES.format(chars=TH["overview_chars"]), text)
        self.assertEqual((text.count("<<<자료 abc123 시작>>>"), text.count("<<<자료 abc123 끝>>>")), (1, 1))
        body = text.split("<<<자료 abc123 시작>>>", 1)[1].split("<<<자료 abc123 끝>>>", 1)[0]
        for fact in GOOD.values():
            self.assertIn("| 문장: " + fact, body)
        self.assertIn("| 숫자: 국고채 입찰 247.4%", body)
        self.assertIn("| 다룬 곳: 채권 3곳 · 애널 2곳 · 개인 3곳", body)
        self.assertTrue(all(line.startswith(("항목 ", "| ")) for line in body.strip().split("\n")))
        posts = [p["text"] for p in F.posts()]
        self.assertFalse(any(len(p) > 30 and p[:30] in text for p in posts))         # 채널 글은 한 토막도 없다
        self.assertEqual(F.leaks(text), [])
        for ch in F.REQUESTED:
            self.assertNotIn(ch, text)

    def test_order_follows_what_was_asked_and_only_kept_facts(self):
        rows = L.overview_rows(fx("digest"), [{"key": k} for k in (AUCTION, CPI, CARD)], {CPI: GOOD[CPI], AUCTION: GOOD[AUCTION]})
        self.assertEqual([x["key"] for x, _ in rows], [AUCTION, CPI])                # 걸린 문장(CARD)은 단락에도 건네지 않는다

    def test_summarize_skips_when_too_few_facts(self):
        calls = Claude(overview=OVERVIEW)
        got = L.summarize(fx("digest"), [{"key": CPI, "texts": ["x"]}], {CPI: GOOD[CPI]}, (), calls, "claude")
        self.assertEqual((got, calls.calls), ((None, "skip", None), []))


class OverviewRunTest(RunCase):
    """한 번에 돌리기 — 항목 문장 다음에 한 단락을 한 번 더 묻고, 검사를 통과한 것만 overview 칸에 싣는다."""

    def test_a_passing_overview_is_written(self):
        code, out = self.go(claude=Claude(GOOD, overview=OVERVIEW))
        self.assertEqual(code, 0, out)
        d = K.validate_picks(self.doc(), fx("sources"))
        self.assertEqual(d["overview"], OVERVIEW)
        self.assertEqual(K.attach_overview(fx("digest"), d, fx("sources"), F.overrides()), OVERVIEW)
        ov = self.claude.overview_calls()
        self.assertEqual(len(ov), 1)
        self.assertEqual([c.probe for c in self.claude.calls], [True, False, False])  # 점검 · 항목 · 한 단락(채널 글 없음 — 점검을 다시 하지 않는다)
        self.assertEqual(F.leaks(ov[0].text), [])
        self.assertTrue(ov[0].empty)                                                  # 같은 격리(새 빈 폴더)
        self.assertEqual(ov[0].cmd, self.claude.main_calls()[0].cmd)                  # 같은 옵션
        self.assertIn("kept=3 dropped=0 ov=ok result=pushed code=ok", self.logged())
        self.clean(self.logged(), out)

    def test_a_failing_overview_is_dropped_alone(self):
        for text, code in ((OVERVIEW.replace("3.1%", "3.4%"), "number"), (OVERVIEW + " 금리는 더 오를 것으로 보인다.", "banned"),
                           (GOOD[CPI] + " " + GOOD[AUCTION], "copy"), (None, "none"), ("한 단락이 아니다", "json")):
            with self.subTest(code):
                self.setUp()
                rc, out = self.go(claude=Claude(GOOD, overview="{not json" if code == "json" else text))
                d = self.doc()
                self.assertEqual((rc, d["overview"], len(d["items"])), (0, None, 3))       # 항목 문장은 그대로 나간다
                self.assertIn(f"ov={code} result=pushed code=ok", self.logged())
                self.assertNotIn("3.4", self.logged() + out + S.dump(d))
                self.clean(self.logged(), out)

    def test_a_broken_isolation_on_the_overview_call_drops_only_the_overview(self):
        code, out = self.go(claude=Claude(GOOD, overview=OVERVIEW, tools=("Bash",), bad_from=2))       # 셋째 호출(한 단락)에만 도구가 보인다
        d = self.doc()
        self.assertEqual((code, d["overview"], [x["key"] for x in d["items"]]), (0, None, [CPI, AUCTION, CARD]))
        self.assertIn("ov=tools", self.logged())

    def test_one_kept_fact_is_not_summarized(self):
        code, out = self.go(claude=Claude({CPI: GOOD[CPI], AUCTION: None, CARD: None}, overview=OVERVIEW))
        self.assertEqual((code, self.doc()["overview"], self.claude.overview_calls()), (0, None, []))
        self.assertIn("ov=skip", self.logged())

    def test_dry_run_keeps_the_overview_review_in_work(self):
        code, out = self.go("--dry-run", claude=Claude(GOOD, overview=OVERVIEW.replace("3.1%", "3.4%")), cmd="make")
        dry = os.path.join(self.work, "picks_dry")
        self.assertEqual(code, 0, out)
        self.assertIsNone(S.read_json(os.path.join(dry, K.FILE))["overview"])
        review = S.read_json(os.path.join(dry, "review_overview.json"))
        self.assertEqual((review["code"], review["checks"]["number"], review["checks"]["shape"]), ("number", False, True))


class WideRunTest(RunCase):
    """넓힌 고르기 그대로(llm_rest_sources 1) — 지어낸 판에서 나머지 표의 세 항목이 더 물리고, 채널마다 한 번 받기는 그대로다."""

    def setUp(self):
        super().setUp()
        wide = mock.patch.dict(R.TH, WIDE)
        wide.start()
        self.addCleanup(wide.stop)

    def test_six_items_are_asked_and_each_channel_is_read_once(self):
        code, out = self.go(claude=Claude(GOOD, overview=OVERVIEW))
        self.assertEqual(code, 0, out)
        main = self.claude.main_calls()[0].text
        for key in (CPI, AUCTION, CARD, *REST3):
            self.assertIn(f"항목 {key} ", main)
        chans = [u.split("/s/", 1)[1].split("?", 1)[0] for u in self.net.calls]
        self.assertEqual(len(chans), len(set(chans)))                                 # 채널마다 한 번
        self.assertEqual(len(chans), 8)                                               # 꼭 볼 것만일 때 7 → 나머지 표의 fxanal4 하나가 더
        self.assertIn("picked=6 ctx=120 asked=6 posts=11 requests=8", self.logged())
        d = self.doc()
        self.assertEqual([x["key"] for x in d["items"]], [CPI, AUCTION, CARD])        # 가짜 claude가 쓰지 않은 셋은 none
        self.assertEqual((d["dropped"]["none"], d["overview"]), (3, OVERVIEW))


if __name__ == "__main__":
    unittest.main()
