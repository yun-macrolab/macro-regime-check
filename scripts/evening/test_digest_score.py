#!/usr/bin/env python3
"""저녁판 점수(digest_score) 테스트 — S = C + X + K + E + M + Y − P, 게이트, 꼭 볼 것 3건과 나머지 표, 금리 머리 줄, 내일 볼 것.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요 — 묶음은 닫힌 값(낱말·숫자)으로 지어낸 것이고 채널·일정·금리도 fixtures.py의 가짜다.
설계 4절의 세 예(미 고용 발표일 12.5 · 채권 1곳 국고 5년 입찰 4.0 · 개인 4곳+속보형 소문 2.25)를 DesignExamplesTest가 그대로 셈한다.
"""
import collections
import contextlib
import copy
import datetime
import io
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_cluster as DC
import digest_rules as R
import digest_schema as S
import digest_score as SC
import fixtures as F

TH = R.TH
NO_EVENTS = {"schema": 1, "updated": "2026-10-01", "events": []}
NO_STATE = {"schema": 1, "edition": None, "base": None}
MONDAY = {"edition": "2026-10-12", "window": {"from": "2026-10-09T17:41:00+09:00", "to": "2026-10-12T17:50:00+09:00"},
          "collected_at": "2026-10-12T17:52:00+09:00"}


def member(ch, pid, when="08 09:00", lead=(), results=(), nums=(), fwd=False, body=()):
    """닫힌 값의 글 하나. lead = 첫머리 낱말, body = 첫머리 밖의 낱말. when = "일 시:분"(2026-10)."""
    return {"ch": ch, "id": pid, "at": f"2026-10-{when[:2]}T{when[3:]}:00+09:00", "group": F.GROUP[ch], "role": F.ROLE[ch], "fwd": fwd,
            "terms": [*lead, *body], "lead": list(lead), "results": list(results), "nums": list(nums), "lead_nums": list(nums)}


def cluster(*members, keys=None, nums=()):
    seed = S.seed_of(members)
    return DC.shape(members, keys or [S.key_of("g", f"{seed['ch']}/{seed['id']}")], nums)


def team(chans, lead, first=1, when="08 09:{:02d}", **kw):
    """채널마다 글 하나씩인 묶음. 글 번호는 first부터."""
    return cluster(*[member(ch, first + i, when.format(i), lead=lead, **kw) for i, ch in enumerate(chans)])


def doc(*clusters, **head):
    cs = sorted(clusters, key=lambda c: (c["first_at"], c["seed"]["ch"], c["seed"]["id"]))
    kept = sum(len(c["members"]) for c in cs)
    base = {"schema": 1, "edition": F.EDITION, "window": dict(F.WINDOW), "collected_at": F.COLLECTED, **head}
    stats = {"posts": kept, "kept": kept, "dropped": {c: 0 for c in R.DROP_CODES}}
    return S.validate_clusters_doc({**base, "stats": stats, "clusters": cs})


def score(*clusters, calendar=NO_EVENTS, korea=None, state=NO_STATE, **head):
    return S.validate_scored_doc(SC.score_doc(doc(*clusters, **head), calendar, korea, state))


def one(c, **kw):
    return score(c, **kw)["clusters"][0]


def points(c, **kw):
    s = one(c, **kw)["score"]
    return {k: s[k] for k in "CXKEMP"} | {"total": s["total"]}


def events(*rows):
    return {"schema": 1, "updated": "2026-10-01",
            "events": [{"date": d, "time": t, "term": term, "tier": tier} for d, t, term, tier in rows]}


def card(key, last_day, last, changes):
    """평일 시계열 — 마지막 값이 last이고 일간 변화(bp, 옛것부터)가 changes."""
    days, d = [], datetime.date.fromisoformat(last_day)
    while len(days) < len(changes) + 1:
        if d.weekday() < 5:
            days.append(d)
        d -= datetime.timedelta(days=1)
    vals = [last]
    for c in reversed(changes):
        vals.append(round(vals[-1] - c / 100, 4))
    return {"key": key, "points": [[x.isoformat(), v] for x, v in zip(reversed(days), reversed(vals))]}


def calm(last):
    """60관측일의 일간 변화: ±1bp 44번, ±3bp 9번, ±7bp 6번, 그리고 마지막 변화 last — 위에서 15번째는 3bp, 6번째는 7bp 언저리."""
    return [1.0, -1.0] * 22 + [3.0, -3.0] * 4 + [3.0] + [7.0, -7.0] * 3 + [last]


BONDS = ["fxbond1", "fxbond2", "fxbond3", "fxbond4", "fxbond5"]
ANALS = ["fxanal1", "fxanal2", "fxanal3", "fxanal4", "fxanal5", "fxanal6"]
PERS = [f"fxpers{i}" for i in range(1, 9)]


class DesignExamplesTest(unittest.TestCase):
    """설계 4절의 세 예 — 숫자가 그대로 나와야 한다."""

    def test_us_jobs_day_scores_12_5_and_passes(self):
        who = BONDS[:3] + ANALS[:2] + PERS[:3] + ["fxwire1"]
        c = cluster(*[member(ch, i + 1, f"07 22:{10 + i}", lead=["미 고용"], results=["상회"]) for i, ch in enumerate(who)],
                    keys=[S.key_of("k", "미 고용|글로벌")])
        got = one(c, calendar=events(("2026-10-07", "21:30", "미 고용", "A")), korea=F.korea())
        self.assertEqual(got["coverage"], {"bond": 3, "analyst": 2, "personal": 3, "wire": 1})
        self.assertEqual(got["score"], {"total": 12.5, "C": 6.75, "X": 1.5, "K": 2.25, "E": 2.0, "M": 0, "Y": 0, "P": 0, "L": None})
        self.assertEqual((got["gate"], got["pick"], got["rank"]), ({"pass": True, "fails": []}, "must", 1))
        self.assertEqual(got["why"], ["채권 채널 3곳", "세 그룹 모두", "발표일 일치", "같은 결과 낱말 9곳"])

    def test_five_year_auction_by_one_bond_channel_scores_4_0_and_fails(self):
        korea = {**F.korea(), "calendar": {"rows": [{"date": "2026-10-08", "tenor": "5년"}]}, "offerings": []}
        got = one(team(BONDS[:1], ["국고채 입찰"]), korea=korea)
        self.assertEqual(got["score"], {"total": 4.0, "C": 2.0, "X": 0, "K": 1.0, "E": 1.0, "M": 0, "Y": 0, "P": 0, "L": None})
        self.assertEqual((got["gate"], got["pick"]), ({"pass": False, "fails": ["sources", "score"]}, "rest"))     # '채권 단독' 줄
        two = one(team(BONDS[:2], ["국고채 입찰"]), korea=korea)                      # 2곳이면 5.0 통과
        self.assertEqual((two["score"]["total"], two["score"]["C"], two["gate"]["pass"], two["pick"]), (5.0, 3.0, True, "must"))

    def test_rumour_among_four_personal_channels_scores_2_25_and_fails(self):
        got = one(team(PERS[:4] + ["fxwire2"], ["추경"]), korea=F.korea())
        self.assertEqual(got["score"], {"total": 2.25, "C": 1.25, "X": 0, "K": 1.0, "E": 0, "M": 0, "Y": 0, "P": 0, "L": None})
        self.assertEqual((got["gate"], got["pick"]), ({"pass": False, "fails": ["score", "group"]}, "rest"))
        self.assertEqual(got["coverage"], {"bond": 0, "analyst": 0, "personal": 4, "wire": 1})


class CoverageTest(unittest.TestCase):
    def test_second_channel_counts_half_and_groups_are_capped(self):
        self.assertEqual(points(team(BONDS[:1], ["미 PPI"]))["C"], 2.0)
        self.assertEqual(points(team(BONDS[:2], ["미 PPI"]))["C"], 3.0)
        self.assertEqual(points(team(BONDS, ["미 PPI"]))["C"], 4.0)                   # 그룹 상한 2w
        self.assertEqual(points(team(ANALS[:3], ["미 PPI"]))["C"], 2.0)
        self.assertEqual(points(team(PERS, ["미 PPI"]))["C"], 1.0)
        self.assertEqual(points(team(BONDS + ANALS + PERS + ["fxwire1", "fxwire2"], ["미 PPI"]))["C"], TH["c_cap"])

    def test_a_channel_that_only_forwarded_counts_half_in_a_later_slot(self):
        c = cluster(member("fxbond1", 1, lead=["미 PPI"]), member("fxanal1", 2, "08 09:01", lead=["미 PPI"], fwd=True),
                    member("fxanal2", 3, "08 09:02", lead=["미 PPI"]), member("fxpers1", 4, "08 09:03", lead=["미 PPI"], fwd=True))
        self.assertEqual(points(c)["C"], 2.0 + (1.0 + 0.25) + 0.25)                  # 직접 쓴 애널이 앞자리, 전달뿐인 채널은 뒤에서 절반
        both = cluster(member("fxbond1", 1, lead=["미 PPI"], fwd=True), member("fxbond1", 2, "08 09:05", lead=["미 PPI"]))
        self.assertEqual(points(both)["C"], 2.0)                                     # 직접 쓴 글이 하나라도 있으면 온전히 센다
        self.assertEqual(points(team(BONDS[:1], ["미 PPI"], fwd=True))["C"], 1.0)

    def test_wire_adds_a_quarter_only_next_to_a_source(self):
        with_wire = one(team(PERS[:1] + ["fxwire1", "fxwire2"], ["미 PPI"]))
        self.assertEqual((with_wire["score"]["C"], with_wire["coverage"]["wire"]), (0.75, 2))     # 몇 곳이든 +0.25
        alone = one(team(["fxwire1", "fxwire2"], ["미 PPI"]))
        self.assertEqual((alone["score"]["C"], alone["score"]["total"], alone["pick"]), (0, 1.0, "none"))
        self.assertEqual(alone["coverage"], {"bond": 0, "analyst": 0, "personal": 0, "wire": 2})

    def test_topic_channels_count_only_in_ai_clusters(self):
        ai = one(team(["fxanal4", "fxtopa1", "fxtopp1"], ["Capex 가이던스"]))
        self.assertEqual((ai["coverage"], ai["score"]["C"]), ({"bond": 0, "analyst": 2, "personal": 1, "wire": 0}, 2.0))
        other = one(team(["fxanal4", "fxtopa1", "fxtopp1"], ["미 PPI"]))
        self.assertEqual((other["coverage"], other["score"]["C"]), ({"bond": 0, "analyst": 1, "personal": 0, "wire": 0}, 1.0))
        own = cluster(member("fxanal4", 1, lead=["미 PPI"]), member("fxtopa1", 2, "08 09:01", lead=["AI"]))
        self.assertEqual(one(own)["coverage"]["analyst"], 1)                         # 주제 한정 채널이 혼자 쓴 AI 낱말로는 세지 않는다

    def test_context_posts_are_not_counted(self):
        got = one(cluster(member("fxctx1", 1, lead=["국내 증시"])))
        self.assertEqual((got["coverage"], got["score"]["C"], got["pick"]),
                         ({"bond": 0, "analyst": 0, "personal": 0, "wire": 0}, 0, "none"))


class CrossAndWordTest(unittest.TestCase):
    def test_x_needs_a_bond_channel(self):
        self.assertEqual(points(team(BONDS[:1] + ANALS[:1], ["미 PPI"]))["X"], 1.0)
        self.assertEqual(points(team(BONDS[:1] + PERS[:1], ["미 PPI"]))["X"], 1.0)
        self.assertEqual(points(team(BONDS[:1] + ANALS[:1] + PERS[:1], ["미 PPI"]))["X"], 1.5)
        self.assertEqual(points(team(ANALS[:1] + PERS[:1], ["미 PPI"]))["X"], 0)
        self.assertEqual(points(team(BONDS[:2], ["미 PPI"]))["X"], 0)

    def test_k_takes_the_highest_grade_only(self):
        self.assertEqual(points(team(BONDS[:1], ["미 PPI", "금리"]))["K"], 1.0)
        self.assertEqual(points(team(BONDS[:1], ["금리", "원/달러 환율"]))["K"], 0.5)
        self.assertEqual(points(team(BONDS[:1], []))["K"], 0)

    def test_a_grade_is_worth_two_only_when_its_event_is_in_the_window(self):
        c = team(BONDS[:1], ["미 CPI"])
        self.assertEqual(points(c)["K"], 1.0)                                         # 일정표에 없으면 B와 같다
        self.assertEqual(points(c, calendar=events(("2026-10-07", "21:30", "미 CPI", "A")))["K"], 2.0)
        self.assertEqual(points(c, calendar=events(("2026-10-09", "21:30", "미 CPI", "A")))["K"], 1.0)   # 창 밖
        self.assertEqual(points(c, calendar=events(("2026-10-07", "21:30", "미 PCE", "A")))["K"], 1.0)   # 다른 낱말의 일정

    def test_words_outside_the_lead_do_not_score(self):
        c = cluster(member("fxbond1", 1, lead=[], body=["미 CPI", "FOMC"]), member("fxbond2", 2, "08 09:01", lead=["금리"], body=["금통위"]))
        got = one(c, calendar=events(("2026-10-07", "21:30", "미 CPI", "A")))
        self.assertEqual((got["score"]["K"], got["score"]["E"], [t["term"] for t in got["terms"]]), (0.5, 0, ["금리"]))
        self.assertEqual(got["gate"]["fails"], ["grade", "score"])

    def test_same_result_word_from_two_channels_adds_a_quarter(self):
        hot = events(("2026-10-08", "10:00", "금통위", "A"))
        two = cluster(member("fxbond1", 1, "08 10:30", lead=["금통위"], results=["동결"]),
                      member("fxanal1", 2, "08 10:40", lead=["금통위"], results=["동결", "확대"]))
        self.assertEqual(points(two, calendar=hot)["K"], TH["k_cap"])
        lone = cluster(member("fxbond1", 1, "08 10:30", lead=["금통위"], results=["동결"]),
                       member("fxanal1", 2, "08 10:40", lead=["금통위"], results=["인하"]))
        self.assertEqual(points(lone, calendar=hot)["K"], 2.0)
        soft = cluster(member("fxbond1", 1, "08 10:30", lead=["금통위"], results=["확대"]),
                       member("fxanal1", 2, "08 10:40", lead=["금통위"], results=["확대"]))
        self.assertEqual(points(soft, calendar=hot)["K"], 2.0)                        # 확대·축소 같은 흔한 말은 세지 않는다
        copied = cluster(member("fxbond1", 1, "08 10:30", lead=["금통위"], results=["동결"]),
                         member("fxanal1", 2, "08 10:40", lead=["금통위"], results=["동결"], fwd=True))
        self.assertEqual(points(copied, calendar=hot)["K"], 2.0)                      # 전달 글은 '같이 쓴 곳'이 아니다


class EventTest(unittest.TestCase):
    def test_event_bonus_follows_the_tier(self):
        c = team(BONDS[:2], ["미 PPI"])
        self.assertEqual(points(c)["E"], 0)
        b = one(c, calendar=events(("2026-10-07", "21:30", "미 PPI", "B")))
        self.assertEqual((b["score"]["E"], b["why"]), (1.0, ["채권 채널 2곳", "발표일 일치"]))
        self.assertEqual(points(c, calendar=events(("2026-10-07", "21:30", "미 PPI", "A")))["E"], 2.0)
        self.assertEqual(points(c, calendar=events(("2026-10-07", "18:02", "미 PPI", "A")))["E"], 0)     # 창의 시작 시각은 지난 판 몫
        self.assertEqual(points(c, calendar=events(("2026-10-08", "21:30", "미 PPI", "A")))["E"], 0)     # 오늘 밤 일정은 아직
        self.assertEqual(points(c, calendar=events(("2026-10-07", "21:30", "ISM", "A")))["E"], 0)

    def test_friday_night_event_counts_in_the_monday_edition(self):
        c = cluster(member("fxbond1", 1, "09 22:00", lead=["미 고용"]), member("fxbond2", 2, "12 08:00", lead=["미 고용"]))
        got = one(c, calendar=events(("2026-10-09", "21:30", "미 고용", "A")), **MONDAY)
        self.assertEqual((got["score"]["E"], got["score"]["K"]), (2.0, 2.0))
        late = one(c, calendar=events(("2026-10-12", "21:30", "미 고용", "A")), **MONDAY)
        self.assertEqual((late["score"]["E"], late["score"]["K"]), (0, 1.0))

    def test_auction_day_comes_from_korea_json(self):
        c = team(BONDS[:1], ["국고채 입찰"])
        rows = lambda *r: {"calendar": {"rows": [{"date": d, "tenor": t} for d, t in r]}}
        ten = one(c, korea=rows(("2026-10-08", "10년")))
        self.assertEqual((ten["score"]["E"], ten["score"]["total"]), (2.0, 5.0))
        self.assertEqual((ten["gate"], ten["pick"], ten["why"]), ({"pass": True, "fails": []}, "must", ["채권 채널 1곳", "채권 1곳 + 일정"]))
        self.assertEqual(points(c, korea=rows(("2026-10-08", "2년"), ("2026-10-08", "30년")))["E"], 2.0)
        self.assertEqual(points(c, korea=rows(("2026-10-08", "물가채")))["E"], 1.0)
        self.assertEqual(points(c, korea=rows(("2026-10-07", "30년")))["E"], 0)       # 어제 입찰은 어제 판에서 셌다
        self.assertEqual(points(c, korea=rows(("2026-10-09", "10년")))["E"], 0)
        two = one(team(BONDS[:2], ["국고채 입찰"]), korea=rows(("2026-10-08", "3년")))
        self.assertEqual(two["why"], ["채권 채널 2곳", "입찰일 일치"])


class RateMoveTest(unittest.TestCase):
    def test_big_move_scores_only_for_bond_channels_with_a_rate_word(self):
        k = F.korea()                                                                # 미 10년 -4bp(60일 가운데 가장 큼), 국고 10년 +0.7bp
        us = one(team(BONDS[:1] + ANALS[:1], ["미 국채 입찰"]), korea=k)
        self.assertEqual((us["score"]["M"], us["why"]), (TH["m_cap"], ["채권 채널 1곳", "채권 + 다른 그룹", "금리 변동 큼"]))
        self.assertEqual(points(team(ANALS[:2], ["미 국채 입찰"]), korea=k)["M"], 0)   # 채권 채널이 없다
        self.assertEqual(points(team(BONDS[:2], ["미 PPI"]), korea=k)["M"], 0)        # 금리 낱말이 없다
        self.assertEqual(points(team(BONDS[:2], ["국고채 입찰"]), korea=k)["M"], 0)    # 국내 칸은 국고 10년을 본다 — 평소 수준
        self.assertEqual(points(team(BONDS[:2], ["미 국채 입찰"]))["M"], 0)           # 금리 자료가 없다

    def test_steps_are_top_quarter_and_top_tenth(self):
        cases = ((4.0, 1.0), (-4.0, 1.0), (3.0, 1.0), (7.0, 1.5), (-9.0, 1.5), (1.0, 0), (0.0, 0))
        for last, want in cases:
            k = {"cards": [card("kr10", "2026-10-08", 4.5, calm(last))]}
            self.assertEqual(points(team(BONDS[:2], ["국고채 입찰"]), korea=k)["M"], want, last)
        short = {"cards": [card("kr10", "2026-10-08", 4.5, calm(7.0)[-30:])]}        # 관측일이 모자라면 가산하지 않는다
        got = score(team(BONDS[:2], ["국고채 입찰"]), korea=short)
        self.assertEqual((got["clusters"][0]["score"]["M"], got["head"]["kr10"]["chg_bp"]), (0, 7.0))

    def test_no_bonus_when_the_rate_day_is_outside_the_window(self):
        stale = {"cards": [card("kr10", "2026-10-07", 4.5, calm(7.0)), card("us10", "2026-10-06", 5.0, calm(-7.0))]}
        for lead in (["국고채 입찰"], ["미 국채 입찰"]):
            self.assertEqual(points(team(BONDS[:2], lead), korea=stale)["M"], 0, lead)
        head = score(team(BONDS[:2], ["국고채 입찰"]), korea=stale)["head"]
        self.assertEqual((head["kr10"]["fits"], head["us10"]["fits"], head["basis"], head["dir"]), (False, False, "전일 종가", None))
        fresh = {"cards": [card("kr10", "2026-10-08", 4.5, calm(7.0)), card("us10", "2026-10-07", 5.0, calm(-7.0))]}
        self.assertEqual(points(team(BONDS[:2], ["미 국채 입찰"]), korea=fresh)["M"], 1.5)

    def test_rates_outside_the_sane_range_are_dropped(self):
        wild = {"cards": [card("kr10", "2026-10-08", 25.0, calm(7.0)), card("kr3", "2026-10-08", 3.9, calm(1.0))]}
        got = score(team(BONDS[:2], ["국고채 입찰"]), korea=wild)
        self.assertEqual((got["clusters"][0]["score"]["M"], got["head"]["kr10"], got["head"]["basis"]), (0, None, None))
        self.assertEqual(got["head"]["kr3"]["value"], 3.9)


class PenaltyTest(unittest.TestCase):
    def test_same_topic_as_yesterday_loses_points_unless_coverage_grew(self):
        key = S.key_of("k", "금통위|국내")                                            # F.state()의 어제 꼭 볼 것: 이 열쇠, C 4.0
        same = cluster(*[member(ch, i + 1, lead=["금통위"]) for i, ch in enumerate(BONDS[:2] + ANALS[:1])], keys=[key])
        got = one(same, state=F.state())
        self.assertEqual((got["score"]["C"], got["score"]["P"], got["score"]["total"]), (4.0, 1.5, 4.5))
        self.assertIn("어제와 같은 주제", got["why"])
        grown = cluster(*[member(ch, i + 1, lead=["금통위"]) for i, ch in enumerate(BONDS[:3] + ANALS[:1])], keys=[key])
        self.assertEqual(points(grown, state=F.state())["P"], 0)                      # C가 1.0 늘었다
        self.assertEqual(points(same)["P"], 0)                                        # 어제 판이 없다
        other = cluster(*[member(ch, i + 1, lead=["금통위"]) for i, ch in enumerate(BONDS[:2])], keys=[S.key_of("k", "한은 발언|국내")])
        self.assertEqual(points(other, state=F.state())["P"], 0)

    def test_rerun_compares_with_the_edition_before_not_with_itself(self):
        key = S.key_of("k", "미 고용|글로벌")
        c = cluster(*[member(ch, i + 1, lead=["미 고용"]) for i, ch in enumerate(BONDS[:2])], keys=[key])
        first_run = {"date": F.EDITION, "window": dict(F.WINDOW), "collected_at": F.COLLECTED, "empty_streak": 0, "channels": {},
                     "must": [{"id": "20261008-fxbond1-1", "keys": [key], "c": 3.0}]}
        again = S.validate_state(S.next_state(F.state(), first_run))
        self.assertEqual(points(c, state=again)["P"], 0)                              # 오늘 첫 실행의 기록은 '어제'가 아니다
        self.assertEqual(points(c, state={"schema": 1, "edition": first_run, "base": first_run | {"date": "2026-10-07",
                         "window": F.state()["edition"]["window"], "collected_at": "2026-10-07T18:04:00+09:00"}})["P"], 1.5)

    def test_mostly_forwarded_loses_one_point(self):
        c = cluster(member("fxbond1", 1, lead=["미 PPI"]), member("fxanal1", 2, "08 09:01", lead=["미 PPI"], fwd=True),
                    member("fxpers1", 3, "08 09:02", lead=["미 PPI"], fwd=True))
        got = one(c)
        self.assertEqual((got["score"]["C"], got["score"]["P"]), (2.75, 1.0))
        self.assertIn("전달 글이 절반 넘음", got["why"])
        half = cluster(member("fxbond1", 1, lead=["미 PPI"]), member("fxanal1", 2, "08 09:01", lead=["미 PPI"], fwd=True))
        self.assertEqual(points(half)["P"], 0)                                        # 절반은 '넘게'가 아니다

    def test_only_c_grade_words_in_the_etc_cell_lose_two_points(self):
        self.assertEqual(points(team(PERS[:2], ["관세"]))["P"], 2.0)
        self.assertEqual(points(team(PERS[:2], ["반도체"]))["P"], 0)                  # C급이지만 칸이 있다
        self.assertEqual(points(team(PERS[:2], ["국가 신용등급"]))["P"], 0)            # 기타 칸이지만 B급
        self.assertEqual(points(team(PERS[:2], []))["P"], 0)
        worst = cluster(member("fxpers1", 1, lead=["관세"]), member("fxpers2", 2, "08 09:01", lead=["관세"], fwd=True),
                        member("fxpers3", 3, "08 09:02", lead=["관세"], fwd=True), keys=[S.key_of("k", "금통위|국내")])
        self.assertEqual(points(worst, state=F.state())["P"], TH["p_cap"])


class GateTest(unittest.TestCase):
    def test_each_gate_reports_its_code(self):
        fails = lambda c, **kw: one(c, **kw)["gate"]["fails"]
        self.assertEqual(fails(team(BONDS[:3] + ANALS[:1], ["미 PPI"])), [])                       # 5.0 + 1.0 + 1.0
        self.assertEqual(fails(team(BONDS[:1], ["미 PPI"])), ["sources", "score"])
        self.assertEqual(fails(team(BONDS[:3] + ANALS[:2], ["금리"])), ["grade"])                  # C급 낱말뿐
        self.assertEqual(fails(team(BONDS[:1] + ANALS[:1], ["미 PPI"])), [])                       # 3.0 + 1.0 + 1.0 = 5.0
        self.assertEqual(fails(team(ANALS[:2], ["미 PPI"])), ["score"])
        self.assertEqual(fails(team(PERS[:4], ["미 PPI"])), ["score", "group"])
        self.assertEqual(fails(cluster(member("fxwire1", 1, lead=[]))), ["sources", "grade", "score", "group"])
        self.assertEqual(set(S.GATE_CODES), {"sources", "grade", "score", "group"})

    def test_one_bond_channel_passes_only_with_a_two_point_event(self):
        c = team(BONDS[:1], ["금통위"])
        a = one(c, calendar=events(("2026-10-08", "10:00", "금통위", "A")))
        self.assertEqual((a["score"]["total"], a["gate"]["pass"]), (6.0, True))                    # 2.0 + 2.0 + 2.0
        b = one(c, calendar=events(("2026-10-08", "10:00", "금통위", "B")))
        self.assertEqual(b["gate"]["fails"], ["sources"])                                          # 2.0 + 2.0 + 1.0 = 5.0이지만 E가 2.0이 아니다
        solo = one(team(ANALS[:1], ["금통위"]), calendar=events(("2026-10-08", "10:00", "금통위", "A")))
        self.assertEqual(solo["gate"]["fails"], ["sources"])                                       # 예외는 채권 채널만


class PickTest(unittest.TestCase):
    def setUp(self):
        self.c1 = team(BONDS[:3] + ANALS[:1] + PERS[:1], ["미 PPI"], first=10)       # 펀더멘털/글로벌 8.0
        self.c2 = team(BONDS[:2] + ANALS[:1] + PERS[:1], ["ISM"], first=20)          # 펀더멘털/글로벌 7.0
        self.c3 = team(BONDS[:2] + ANALS[:1], ["유가"], first=30)                    # 펀더멘털/글로벌 6.0
        self.c4 = team(BONDS[:1] + ANALS[:2], ["연준 발언"], first=40)               # 통화정책/글로벌 5.5
        self.c5 = team(BONDS[:1] + ANALS[:1], ["추경"], first=50)                    # 수급/국내 5.0

    def picks(self, out):
        return {c["seed"]["id"]: (c["score"]["total"], c["pick"], c["rank"]) for c in out["clusters"]}

    def test_three_at_most_and_two_per_cell(self):
        got = self.picks(score(self.c1, self.c2, self.c3, self.c4))
        self.assertEqual(got, {10: (8.0, "must", 1), 20: (7.0, "must", 2), 30: (6.0, "rest", None), 40: (5.5, "must", 3)})

    def test_one_slot_goes_to_a_domestic_cluster_that_passed(self):
        got = self.picks(score(self.c1, self.c2, self.c3, self.c4, self.c5))
        self.assertEqual(got, {10: (8.0, "must", 1), 20: (7.0, "must", 2), 30: (6.0, "rest", None), 40: (5.5, "rest", None),
                               50: (5.0, "must", 3)})

    def test_fewer_when_fewer_pass(self):
        got = self.picks(score(self.c1, self.c5, team(PERS[:3], ["관세"], first=60)))
        self.assertEqual(got, {10: (8.0, "must", 1), 50: (5.0, "must", 2), 60: (-0.5, "rest", None)})     # 1.0 + 0.5 − 2.0
        self.assertEqual([c["pick"] for c in score(team(PERS[:1], ["관세"]))["clusters"]], ["none"])
        self.assertEqual(score()["clusters"], [])

    def test_ties_go_to_the_earlier_cluster(self):
        a, b = team(BONDS[:1] + ANALS[:1], ["미 PPI"], first=10, when="08 10:{:02d}"), team(BONDS[:1] + ANALS[:1], ["ECB"], first=20)
        got = self.picks(score(a, b))
        self.assertEqual((got[20][2], got[10][2]), (1, 2))

    def test_rest_table_rules(self):
        out = score(team(BONDS[:1], [], first=1),                                    # 채권 채널 단독 글은 낱말이 없어도 전부
                    team(BONDS[:1], ["관세"], first=2, fwd=True),                    # 점수가 낮아도 채권 채널이면
                    team(ANALS[:1], ["미 PPI"], first=3),                            # 애널 단독 S 2.0
                    team(ANALS[:1], ["금리"], first=4),                              # 애널 단독 S 1.5
                    team(PERS[:1], ["미 CPI"], first=5),                             # 개인 단독은 표에 넣지 않는다(solo 절의 몫)
                    team(PERS[:2], [], first=6),                                     # 원천 2곳
                    team(["fxwire1"], ["미 CPI"], first=8),
                    team(["fxtopa1", "fxtopp1"], ["AI"], first=9))                   # 주제 한정 채널끼리
        self.assertEqual({c["seed"]["id"]: c["pick"] for c in out["clusters"]},
                         {1: "rest", 2: "rest", 3: "rest", 4: "none", 5: "none", 6: "rest", 8: "none", 9: "none"})
        self.assertEqual({c["seed"]["id"]: c["score"]["total"] for c in out["clusters"]}[3], TH["rest_s"])


class HeadTest(unittest.TestCase):
    def test_head_from_the_fixture_rates(self):
        head = score(korea=F.korea())["head"]
        self.assertEqual(head, {**F.head(), "top_terms": []})

    def test_direction_and_curve_need_more_than_one_bp(self):
        def head(c10, c3):
            return score(korea={"cards": [card("kr10", "2026-10-08", 4.4, calm(c10)), card("kr3", "2026-10-08", 3.9, calm(c3))]})["head"]
        self.assertEqual([head(a, b)["dir"] for a, b in ((2.0, 2.0), (-2.0, -2.0), (1.0, 1.0), (-1.0, 0.0))], ["약세", "강세", "보합", "보합"])
        self.assertEqual([head(a, b)["curve"] for a, b in ((3.0, 0.5), (0.5, 3.0), (2.0, 1.0), (2.0, 2.5))], ["스팁", "플랫", "보합", "보합"])
        self.assertEqual(head(2.0, 2.0)["basis"], "당일 종가")

    def test_yesterdays_close_blanks_the_direction(self):
        k = {"cards": [card("kr10", "2026-10-07", 4.376, calm(0.7)), card("kr3", "2026-10-07", 3.961, calm(2.8)),
                       card("us10", "2026-10-06", 5.27, calm(-4.0))]}
        head = score(korea=k)["head"]
        self.assertEqual(head["kr10"], {"value": 4.376, "chg_bp": 0.7, "asof": "2026-10-07", "fits": False})
        self.assertEqual((head["dir"], head["curve"], head["basis"], head["us10"]["fits"]), (None, None, "전일 종가", False))
        mixed = {"cards": [card("kr10", "2026-10-08", 4.4, calm(3.0)), card("kr3", "2026-10-07", 3.9, calm(0.5))]}
        head = score(korea=mixed)["head"]
        self.assertEqual((head["dir"], head["curve"]), ("약세", None))                # 3년의 자료일이 다르면 커브는 비운다

    def test_unreadable_rates_give_an_empty_head(self):
        blank = {"kr10": None, "kr3": None, "us10": None, "dir": None, "curve": None, "basis": None, "top_terms": []}
        junk = [None, {}, [], "korea", {"cards": "x"}, {"cards": [{"key": "kr10"}]},
                {"cards": [{"key": "kr10", "points": [["2026-10-08", "4.4"]]}]},
                {"cards": [{"key": "kr10", "points": [["2026-10-08", 4.4], ["2026-10-07", 4.3]]}]},        # 날짜가 거꾸로
                {"cards": [{"key": "kr10", "points": [["2026-10-07", 4.3], ["어제", 4.4]]}]},
                {"cards": [{"key": "kr10", "points": [["2026-10-07", 4.3], ["2026-10-08", float("nan")]]}]}]
        for k in junk:
            self.assertEqual(score(korea=k)["head"], blank, k)

    def test_top_terms_count_channels_not_clusters(self):
        """가장 많이 다뤄진 주제 = 원천 채널이 첫머리에 직접 쓴 A·B급 낱말을 채널 수로 센 것 — 묶음의 대표 낱말이 아니라서
        묶기가 틀려도(서로 다른 주제가 한 묶음이 돼도) 흔들리지 않는다."""
        mixed = cluster(member(ANALS[0], 60, lead=["유가"]), member(PERS[0], 61, lead=["금리"]),
                        member(PERS[1], 62, lead=["유가"], fwd=True))                # 전달 글은 세지 않는다
        out = score(team(BONDS[:3] + ANALS[:1], ["미 PPI"], first=10), team(BONDS[:2], ["ISM", "금리"], first=20),
                    team(ANALS[1:3], ["미 PPI"], first=30),                          # 다른 묶음의 채널도 같은 낱말로 센다 — 미 PPI 6곳
                    team(PERS[:2], ["관세"], first=40),                              # C급 낱말은 세지 않는다
                    team(BONDS[:1], ["금통위"], first=50),                           # 한 곳만 쓴 낱말은 뺀다
                    mixed, team(PERS[2:5], ["유가"], first=70))                      # 유가 4곳(애널 1 + 개인 3)
        self.assertEqual(out["head"]["top_terms"], ["미 PPI", "유가", "ISM"])


class TomorrowTest(unittest.TestCase):
    def test_fixture_calendar_gives_the_sample_list(self):
        out = score(calendar=F.calendar(), korea=F.korea())
        self.assertEqual(out["tomorrow"], F.tomorrow())

    def test_tonight_counts_as_ahead_and_the_list_is_bounded(self):
        cal = events(("2026-10-08", "21:30", "미 PPI", "B"), ("2026-10-08", "09:00", "ISM", "B"), ("2026-10-12", None, "금통위", "A"),
                     ("2026-10-13", None, "FOMC", "A"), ("2026-10-08", None, "미 PCE", "A"))
        got = score(calendar=cal)["tomorrow"]
        self.assertEqual([(e["date"], e["time"], e["term"]) for e in got], [("2026-10-08", "21:30", "미 PPI"), ("2026-10-12", None, "금통위")])
        many = events(*[("2026-10-09", f"{h:02d}:00", "미 PPI", "B") for h in range(8, 20)])
        self.assertEqual(len(score(calendar=many)["tomorrow"]), TH["tomorrow_max"])


class FixtureTest(unittest.TestCase):
    """지어낸 글 40개를 묶기 → 점수까지 — 꼭 볼 것 3건, 원문 없음."""

    @classmethod
    def setUpClass(cls):
        cls.clusters = DC.cluster_posts(F.posts_doc(), F.collect_status())
        cls.out = SC.score_doc(cls.clusters, F.calendar(), F.korea(), F.state())

    def by(self, ch, pid):
        return next(c for c in self.out["clusters"] if any((m["ch"], m["id"]) == (ch, pid) for m in c["members"]))

    def test_output_follows_the_contract(self):
        S.validate_scored_doc(self.out)
        self.assertEqual((self.out["head"], self.out["tomorrow"], self.out["stats"]), (F.head(), F.tomorrow(), self.clusters["stats"]))
        self.assertEqual(F.leaks(S.dump(self.out)), [])
        self.assertEqual(S.closed_violations(self.out, S.handles_of(F.sources())), [])

    def test_three_picks_in_order(self):
        must = sorted((c for c in self.out["clusters"] if c["pick"] == "must"), key=lambda c: c["rank"])
        self.assertEqual([(c["seed"]["ch"], c["seed"]["id"]) for c in must], [("fxbond1", 501), ("fxbond4", 640), ("fxbond2", 213)])
        cpi, auction, card_ = must
        self.assertEqual(cpi["coverage"], {"bond": 3, "analyst": 2, "personal": 3, "wire": 1})
        self.assertEqual(cpi["score"], {"total": 13.625, "C": 6.375, "X": 1.5, "K": 2.25, "E": 2.0, "M": 1.5, "Y": 0, "P": 0, "L": None})
        self.assertEqual(cpi["why"], ["채권 채널 3곳", "세 그룹 모두", "발표일 일치", "금리 변동 큼"])
        self.assertEqual(auction["score"], {"total": 8.25, "C": 4.0, "X": 1.0, "K": 1.25, "E": 2.0, "M": 0, "Y": 0, "P": 0, "L": None})
        self.assertEqual(auction["why"], ["채권 채널 2곳", "채권 + 다른 그룹", "입찰일 일치", "같은 숫자 2곳"])
        self.assertEqual((card_["score"]["total"], card_["why"]), (5.0, ["채권 채널 1곳", "채권 + 다른 그룹"]))

    def test_the_rest(self):
        self.assertEqual(collections.Counter(c["pick"] for c in self.out["clusters"]), {"must": 3, "rest": 4, "none": 10})
        capex, rumor = self.by("fxanal4", 905), self.by("fxpers5", 610)
        self.assertEqual((capex["coverage"], capex["score"]["C"], capex["pick"]),
                         ({"bond": 0, "analyst": 2, "personal": 2, "wire": 0}, 2.25, "rest"))
        self.assertEqual((rumor["score"]["C"], rumor["score"]["P"], rumor["gate"]["fails"], rumor["pick"]),
                         (1.25, 2.0, ["grade", "score", "group"], "rest"))
        self.assertEqual({self.by(ch, pid)["pick"] for ch, pid in (("fxbond1", 502), ("fxbond3", 89))}, {"rest"})       # 채권 단독
        alone = (("fxpers6", 73), ("fxpers7", 1901), ("fxwire1", 90016), ("fxctx1", 4100))       # 개인·속보형·참고 채널이 혼자 쓴 글
        self.assertEqual({self.by(ch, pid)["pick"] for ch, pid in alone}, {"none"})

    def test_members_carry_what_the_link_rule_needs(self):
        links = S.pick_links(self.by("fxbond1", 501)["members"])                      # 링크는 조립 단계가 이 규칙으로 고른다
        self.assertEqual([x["ch"] for x in links], ["fxbond1", "fxbond2", "fxbond3", "fxanal2", "fxpers2", "fxpers3"])
        self.assertEqual({x["fwd"] for x in links}, {False})                          # 전달 글·속보형 글은 밀려난다
        self.assertEqual([x["ch"] for x in S.pick_links(self.by("fxpers5", 610)["members"])], ["fxpers5", "fxpers7"])

    def test_inputs_are_untouched_and_the_result_repeats(self):
        args = [copy.deepcopy(x) for x in (self.clusters, F.calendar(), F.korea(), F.state())]
        again = SC.score_doc(*args)
        self.assertEqual(args, [self.clusters, F.calendar(), F.korea(), F.state()])
        self.assertEqual(again, self.out)


class CliTest(unittest.TestCase):
    def setup(self, tmp, clusters=None):
        work = os.path.join(tmp, "work")
        clusters = DC.cluster_posts(F.posts_doc(), F.collect_status()) if clusters is None else clusters
        S.write_json(os.path.join(work, "clusters.json"), clusters)
        for name, data in (("calendar.json", F.calendar()), ("korea.json", F.korea()), ("digest_state.json", F.state())):
            S.write_json(os.path.join(tmp, name), data)
        return ["--work", work, "--calendar", os.path.join(tmp, "calendar.json"), "--korea", os.path.join(tmp, "korea.json"),
                "--state", os.path.join(tmp, "digest_state.json")]

    def call(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = S.run_cli("digest_score", SC.main, argv)
        return code, out.getvalue(), err.getvalue()

    def test_writes_scored_and_prints_counts_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            argv = self.setup(tmp)
            code, out, err = self.call(argv)
            self.assertEqual((code, err), (0, ""))
            self.assertEqual(out, "[digest_score] clusters=17 candidates=3 must=3 rest=4 events=2 rates=3\n")
            got = S.validate_scored_doc(S.read_json(os.path.join(tmp, "work", "scored.json")))
            self.assertEqual(got, SC.score_doc(S.read_json(os.path.join(tmp, "work", "clusters.json")), F.calendar(), F.korea(), F.state()))
            with open(os.path.join(tmp, "work", "scored.json"), encoding="utf-8") as f:
                self.assertEqual(F.leaks(f.read()), [])

    def test_missing_side_files_do_not_stop_the_edition(self):
        with tempfile.TemporaryDirectory() as tmp:
            argv = self.setup(tmp)
            for name in ("calendar.json", "korea.json", "digest_state.json"):
                os.remove(os.path.join(tmp, name))
            code, out, err = self.call(argv)
            self.assertEqual((code, err, out), (0, "", "[digest_score] clusters=17 candidates=3 must=3 rest=4 events=0 rates=0\n"))
            got = S.read_json(os.path.join(tmp, "work", "scored.json"))
            self.assertEqual((got["head"]["kr10"], got["head"]["basis"], got["tomorrow"]), (None, None, []))
            with open(os.path.join(tmp, "korea.json"), "w", encoding="utf-8") as f:
                f.write("{깨진 파일 " + F.C1)
            self.assertEqual(self.call(argv)[0], 0)                                   # 금리 파일이 깨져도 판은 낸다(금리 칸만 빈다)

    def test_failure_prints_only_the_kind_of_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.call(["--work", tmp]), (1, "", "[digest_score] 실패: FileNotFoundError\n"))
            broken = DC.cluster_posts(F.posts_doc(), F.collect_status())
            broken["clusters"][0]["members"][0]["terms"] = [F.C3]
            argv = self.setup(tmp, broken)
            self.assertEqual(self.call(argv), (1, "", "[digest_score] 실패: ValueError\n"))
            argv = self.setup(tmp)
            S.write_json(os.path.join(tmp, "digest_state.json"), {"schema": 1, "edition": F.C3, "base": None})
            self.assertEqual(self.call(argv), (1, "", "[digest_score] 실패: ValueError\n"))
            S.write_json(os.path.join(tmp, "digest_state.json"), F.state())
            bad_event = {"date": "2026-10-07", "term": F.C1, "tier": "A"}              # 사전에 없는 낱말(심은 글자)
            S.write_json(os.path.join(tmp, "calendar.json"), {**F.calendar(), "events": [bad_event]})
            self.assertEqual(self.call(argv), (1, "", "[digest_score] 실패: ValueError\n"))
            self.assertNotIn("scored.json", os.listdir(os.path.join(tmp, "work")))

    def test_script_runs_from_the_repo_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            argv = self.setup(tmp)
            done = subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, "digest_score.py"), *argv],
                                  capture_output=True, text=True, encoding="utf-8", cwd=S.REPO, timeout=120)
            self.assertEqual((done.returncode, done.stderr), (0, ""))
            self.assertEqual(done.stdout, "[digest_score] clusters=17 candidates=3 must=3 rest=4 events=2 rates=3\n")


if __name__ == "__main__":
    unittest.main()
