#!/usr/bin/env python3
"""저녁판 화면 테스트(둘째 묶음) — 시범 수집을 보고 고친 읽는 순서: 금리와 주제가 먼저, 짧은 나머지 표는 펼쳐서, 낱말 없는 채권 단독 글은
한데 접어서, 한 곳만 쓴 숫자는 그렇다고 적어서. 도구(가짜 문서 · 지어낸 판)는 test_evening_site.py의 것을 쓴다.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요 — 자료는 fixtures.py의 지어낸 글로 만든 판뿐이다. node가 없으면 건너뛴다.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_evening_site import NODE, Screen, draw, flat, fx, posts, site


@unittest.skipUnless(NODE, "node가 없다")
class ReadingOrderTest(Screen):
    @classmethod
    def setUpClass(cls):
        cls.frame = draw(site())

    def test_head_says_rates_and_topics_before_the_counts(self):
        text = flat(self.frame["text"])
        order = [text.index(flat(x)) for x in ("국고 10년 4.376%", "가장 많이 다뤄진 주제", "읽은 41건", "24채널 중 24 읽음")]
        self.assertEqual(order, sorted(order))                                 # 폰 첫 화면에 금리와 주제가 먼저 온다

    def test_a_short_rest_table_is_shown_open(self):
        opened = [a for a in self.frame["attrs"] if a.startswith("open=")]
        self.assertEqual(len(opened), 2)                                       # 나머지 2줄(칸 2개) — 몇 줄 안 되면 펼쳐 둔다
        self.lacks(self.frame, "접혀 있습니다")
        long = fx("digest")
        row = long["rest"][0]["items"][0]
        long["rest"][0]["items"] = [{**row, "id": f"20261008-fxanal4-{9000 + i}"} for i in range(11)]
        frame = draw(site(digest=long))
        self.assertEqual([a for a in frame["attrs"] if a.startswith("open=")], [])
        self.shows(frame, "분류 칸별로 접혀 있습니다")

    def test_lone_bond_posts_without_a_term_are_folded_together(self):
        d = fx("digest")
        for g in d["rest"]:
            for x in g["items"]:
                if x["id"] == "20261008-fxbond3-89":
                    x["terms"] = []                                            # 첫머리에도 본문에도 사전 낱말이 없는 글
                    x.pop("words", None)
                    x["links"][0].pop("more", None)
        frame = draw(site(digest=d))
        self.assertTrue(any(flat(s).startswith(flat("사전 낱말이 없는 글 1건")) for s in frame["folds"]), frame["folds"])
        self.shows(frame, "통화정책 / 국내 금통위 의사록 · 소수의견 · 국고채 금리")           # 낱말이 있는 줄은 그대로 먼저
        self.assertIn("https://t.me/fxbond3/89", posts(frame))                 # 접힌 안에 링크는 남는다
        self.assertFalse(any("낱말이 없는 글" in s for s in self.frame["folds"]))

    def test_side_rows_say_what_their_numbers_are(self):
        self.shows(self.frame, "한 곳만 쓴 숫자입니다", "건수는 하루 전체가 아니라 검색어 '금리'에 걸린 글 수입니다",
                   "속보형·개인 채널이 혼자 쓴 글의 숫자는 한 곳만 쓴 숫자입니다")


if __name__ == "__main__":
    unittest.main()
