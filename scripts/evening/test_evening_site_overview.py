#!/usr/bin/env python3
"""저녁판 화면 테스트 — 판 맨 위의 '오늘 판 한 단락'(data/digest_picks.json의 overview, 2026-11-28 E3).

  붙이는 조건  요약 층을 믿을 때(picksOf와 같은 조건)이고, 실린 항목 문장이 overview_items_min개 이상이고 하나도 빠지지 않았고, 그 문장들이
              모두 이 화면의 항목에 실제로 그려졌을 때만(파이썬 판은 digest_picks.attach_overview). 한 항목이라도 빠지면 단락도 빠진다
  2차 가드     길이(overview_min_chars~overview_chars) · 정해 둔 글자 · 주소 꼴 · '…다.'로 맺음. 글자는 텍스트 노드로만
  보이는 꼴    'AI 요약' 표시 · '오늘 판 한 단락' · 틀릴 수 있다는 말 — 판 머리 맨 위(금리 줄보다 앞)

도구는 test_evening_site.py의 것을 쓴다. 단락과 문장은 지어낸 것이다(fixtures.PICK_FACTS와 아래 상수).
실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서). node가 없으면 그려 보는 테스트는 건너뛴다.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_picks as K
import digest_rules as R
import fixtures as F
from test_evening_site import JS, NODE, Screen, blob, calls, draws, fx, rules_block, site
from test_evening_site_more import order

TAG = "오늘 판 한 단락"
# 지어낸 한 단락 — 지어낸 판의 꼭 볼 것 두 건(fixtures.picks()에 문장이 실린 것)을 가로지른다
OV = ("오늘 판은 미국 물가 지표와 국고채 입찰이 함께 다뤄졌다. 미국 9월 소비자물가는 3.1% 올랐고 10년 만기 국고채 입찰에서는 "
      "2.8조원이 낙찰됐다. 물가 항목은 채권 3곳과 애널 2곳이 다뤘다.")


def layer(overview=OV, fn=None):
    p = fx("picks")
    p["overview"] = overview
    if fn:
        fn(p)
    return p


class OverviewRulesTest(unittest.TestCase):
    def test_numbers_match_the_rules_and_the_example_is_valid(self):
        rules = rules_block()
        for key in ("overview_chars", "overview_min_chars", "overview_items_min", "fact_chars", "llm_items_max"):
            self.assertEqual(rules[key], R.TH[key], key)
        self.assertIs(K.validate_picks(layer(), F.sources())["overview"], OV)
        self.assertEqual(K.attach_overview(fx("digest"), layer(), F.sources(), F.overrides()), OV)
        self.assertIn('class: "eve-ai eve-overview"', JS)


@unittest.skipUnless(NODE, "node가 없다")
class OverviewGuardTest(unittest.TestCase):
    def test_guard_takes_what_the_rules_take(self):
        good = [OV, "가" * (R.TH["overview_chars"] - 2) + "다."]
        bad = ["가" * (R.TH["overview_chars"] - 1) + "다.", "짧은 단락이다. 두 문장이다.", OV.replace("다뤘다.", "다뤘다"),
               OV + " 자세한 것은 example.org 에 있다.", OV.replace("오늘", "<b>오늘</b>"), " " + OV, None, 7]
        self.assertEqual(calls("overviewText", *good, *bad), good + [None] * len(bad))


@unittest.skipUnless(NODE, "node가 없다")
class OverviewDrawTest(Screen):
    @classmethod
    def setUpClass(cls):
        hidden_ch = F.overrides(hide_channels=["fxbond1"])                       # 첫 항목 문장이 읽은 채널
        hidden_id = F.overrides(hide_ids=[fx("digest")["must"][1]["id"]])
        long_fact = lambda p: p["items"][1].update(fact="가" * (R.TH["fact_chars"] + 1) + "다.")
        one = lambda p: p.update(items=p["items"][:1])
        cls.on, cls.none, cls.ch, cls.id, cls.bad_fact, cls.one, cls.link, cls.other_day = draws(
            site(picks=layer()), site(picks=layer(None)), site(picks=layer(), overrides=hidden_ch), site(picks=layer(), overrides=hidden_id),
            site(picks=layer(fn=long_fact)), site(picks=layer(fn=one)), site(picks=layer(OV + " 원문은 t.me/fxbond1/501 이다.")),
            site(picks=layer(fn=lambda p: p.update(date="2026-10-07"))))

    def test_drawn_at_the_top_of_the_edition_with_the_ai_mark(self):
        self.shows(self.on, TAG, OV, "틀릴 수 있습니다 — 각 항목의 원문에서 확인하세요", "아래 항목의 AI 요약 문장과 규칙판의 낱말·숫자만 보고 씀")
        at = order(self.on, "저녁판 2026-10-08(목)", TAG, OV, "수집 ", F.PICK_FACTS[0])
        self.assertEqual(at, sorted(at))                                         # 판 머리 맨 위, 항목 문장보다 앞
        self.assertIn("class=eve-ai eve-overview", self.on["attrs"])
        self.assertEqual(F.leaks(blob(self.on)), [])
        for attr in self.on["attrs"]:
            self.assertNotIn(OV[:12], attr)                                      # 속성에는 들어가지 않는다

    def test_left_out_unless_every_item_sentence_is_on_screen(self):
        for name in ("none", "ch", "id", "bad_fact", "one", "link", "other_day"):
            with self.subTest(name):
                frame = getattr(self, name)
                self.lacks(frame, OV, "아래 항목의 AI 요약 문장과 규칙판의 낱말·숫자만 보고 씀")     # '오늘 판 한 단락'이라는 말은 안내 문단에도 있다
                self.assertNotIn("class=eve-ai eve-overview", frame["attrs"])
        self.shows(self.id, F.PICK_FACTS[0])                                     # 항목 문장은 그대로 — 단락만 빠진다
        self.shows(self.bad_fact, F.PICK_FACTS[0])


if __name__ == "__main__":
    unittest.main()
