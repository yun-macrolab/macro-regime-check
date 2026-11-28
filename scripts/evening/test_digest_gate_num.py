#!/usr/bin/env python3
"""저녁판 고르는 기준(2026-11-28) 테스트 — 꼭 볼 것의 숫자 경로, 그림자 기록(funnel.shadow), 나머지 표의 같은 점수 순서.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요 — 묶음은 닫힌 값(낱말·숫자)으로 지어낸 것이고 채널은 fixtures.py의 가짜다.
"""
import copy
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_build as B
import digest_rules as R
import digest_schema as S
import digest_score as SC
import fixtures as F
from test_digest_score import ANALS, BONDS, PERS, cluster, member, one, score, team

TH = R.TH


def same_num(term, v="3.1%", n=2):
    return [{"term": term, "result": None, "v": v, "n_ch": n}]


def with_num(chans, lead, term=None, first=1, **kw):
    """채널마다 글 하나씩 + 숫자 칸(두 곳이 같은 낱말 곁에 같은 숫자를 직접 썼다)."""
    ms = [member(ch, first + i, f"08 09:{i:02d}", lead=lead) for i, ch in enumerate(chans)]
    return cluster(*ms, nums=same_num(term or lead[0]), **kw)


class NumPathTest(unittest.TestCase):
    def test_threshold_is_recorded_with_the_old_one_kept(self):
        self.assertEqual((TH["gate_s"], TH["gate_num_s"]), (5.0, 4.0))

    def test_two_bond_channels_on_a_b_word_pass_only_with_a_shared_number(self):
        plain = one(team(BONDS[:2], ["미 PPI"]))
        self.assertEqual((plain["score"]["total"], plain["gate"]["fails"]), (4.0, ["score"]))     # 3.0 + 1.0 — 그동안 가장 많이 막힌 꼴
        got = one(with_num(BONDS[:2], ["미 PPI"]))
        self.assertEqual((got["score"]["total"], got["gate"]["pass"]), (4.0, True))
        self.assertIn(R.phrase("why_num", n=2), got["why"])                                     # 까닭 칩에 '같은 숫자 2곳'이 남는다

    def test_bond_plus_another_group_with_a_shared_number(self):
        got = one(with_num(BONDS[:1] + PERS[:1], ["미 PPI"]))
        self.assertEqual((got["score"]["total"], got["gate"]["pass"]), (4.5, True))             # 2.0 + 0.5 + 1.0(X) + 1.0
        self.assertEqual(one(team(BONDS[:1] + PERS[:1], ["미 PPI"]))["gate"]["fails"], ["score"])

    def test_no_bond_channel_no_path(self):
        got = one(with_num(ANALS[:3], ["미 PPI"]))
        self.assertEqual((got["score"]["total"], got["gate"]["fails"]), (3.0, ["score"]))       # 1.0 + 0.5 + 0.5 + 1.0
        got = one(with_num(ANALS[:2] + PERS[:2], ["미 PPI"]))
        self.assertIn("score", got["gate"]["fails"])

    def test_below_the_lower_bar_still_fails(self):
        got = one(with_num(BONDS[:1] + ANALS[:1], ["관세"]))                                    # C급 낱말 — 숫자가 있어도 grade
        self.assertIn("grade", got["gate"]["fails"])
        with self.assertRaises(ValueError):                                                     # 한 채널 두 글은 두 곳이 아니다 —
            one(cluster(member("fxbond1", 1, lead=["미 PPI"]), member("fxbond1", 2, "08 09:01", lead=["미 PPI"]),  # 숫자 칸부터 계약 위반
                        nums=same_num("미 PPI")))

    def test_a_penalty_closes_the_path(self):
        c = with_num(BONDS[:2] + PERS[:1], ["금통위"], keys=[S.key_of("k", "금통위|국내")])
        got = one(c, state=F.state())                                                           # 직전 판의 꼭 볼 것과 같은 열쇠
        self.assertEqual((got["score"]["P"], got["score"]["total"]), (TH["p_repeat"], 4.0))
        self.assertEqual(got["gate"]["fails"], ["score"])
        self.assertTrue(one(c)["gate"]["pass"])                                                  # 감점이 없으면 같은 묶음이 통과

    def test_number_path_candidates_rank_below_the_normal_ones(self):
        hi = team(BONDS[2:4] + ANALS[:1], ["유가"], first=30)                                   # 6.0
        lo = with_num(BONDS[:2], ["미 PPI"], first=10)                                          # 4.0, 숫자 경로
        got = score(hi, lo)["clusters"]
        picks = sorted((c["rank"], c["terms"][0]["term"]) for c in got if c["pick"] == "must")
        self.assertEqual(picks, [(1, "유가"), (2, "미 PPI")])


class ShadowTest(unittest.TestCase):
    def setUp(self):
        self.scored = score(team(BONDS[2:5] + ANALS[:1], ["유가"], first=30),            # 통과(7.0)
                            with_num(BONDS[:2], ["미 PPI"], first=10),                   # 숫자 경로로 통과(4.0)
                            team(BONDS[:2], ["ISM"], first=20),                          # score 하나만(4.0)
                            team(BONDS[:1] + PERS[:1], ["ECB"], first=40),               # score 하나만(4.5) · 채권 + 다른 그룹
                            team(BONDS[:1], [], first=50),                               # 채권 단독, 낱말 없음 → 나머지 표
                            team(PERS[:1], ["미 PPI"], first=60))["clusters"]            # 개인 단독 → none

    def test_counts(self):
        sh = SC.shadow(self.scored)
        self.assertEqual(tuple(sh), S.SHADOW_KEYS)
        self.assertTrue(all(type(v) is int for v in sh.values()))
        want = {"only_score": 2, "near_s3": 2, "near_s4": 2, "near_s45": 1, "bond2_ab": 3, "bond2_ab_num": 1, "cross_ab": 2,
                "cross_ab_num": 0, "num_path": 1, "rest_noterm": 1}
        self.assertEqual({k: sh[k] for k in want}, want)
        self.assertEqual(sh["rest_pool"], sum(c["pick"] == "rest" for c in self.scored))
        self.assertEqual(sh["fail_group"], 1)                                            # 개인 단독

    def test_published_funnel_carries_it_and_the_schema_checks_it(self):
        d = copy.deepcopy(F.digest())
        sh = {k: 0 for k in S.SHADOW_KEYS}
        S.validate_digest({**d, "funnel": {**d["funnel"], "shadow": sh}})              # 칸이 있어도 없어도 된다
        S.validate_digest(d)
        bad = {"글자": {**sh, "rest_pool": "3"}, "모르는 칸": {**sh, "x": 1}, "칸 빠짐": {k: 0 for k in S.SHADOW_KEYS[1:]},
               "후보보다 많음": {**sh, "num_path": d["funnel"]["candidates"] + 1},
               "부분이 전체보다 큼": {**sh, "bond2_ab_num": 1}, "묶음보다 많음": {**sh, "rest_pool": d["funnel"]["clusters"] + 1}}
        for name, v in bad.items():
            with self.subTest(name), self.assertRaises(ValueError):
                S.validate_digest({**d, "funnel": {**d["funnel"], "shadow": v}})

    def test_build_writes_it(self):
        sc = F.scored_doc()
        d, _, _ = B.edition(sc, F.collect_status(), F.sources(), F.overrides())
        self.assertEqual(d["funnel"]["shadow"], SC.shadow(sc["clusters"]))
        self.assertEqual(d["funnel"]["shadow"]["num_path"] + sum(c["gate"]["pass"] and c["score"]["total"] >= TH["gate_s"]
                                                                 for c in sc["clusters"]), d["funnel"]["candidates"])
        S.validate_digest(d)


class RestOrderTest(unittest.TestCase):
    def test_same_score_puts_rows_with_words_first(self):
        def c(terms, at, pid):
            return {"pick": "rest", "terms": [{"term": t, "n_ch": 1} for t in terms], "score": {"total": 2.0},
                    "first_at": f"2026-10-08T{at}:00+09:00", "seed": {"ch": "fxbond1", "id": pid}}
        rows = [c([], "09:00", 1), c(["미 PPI"], "10:00", 2), c([], "08:00", 3), {**c([], "11:00", 4), "score": {"total": 2.5}}]
        _, rest = B._pick(rows, False)
        self.assertEqual([x["seed"]["id"] for x in rest], [4, 2, 3, 1])


if __name__ == "__main__":
    unittest.main()
