#!/usr/bin/env python3
"""연준 재무상태표 참고 자료(fedbs_fetch) 테스트 — 산식(손으로 셀 수 있는 합성 자료), 지준/GDP가 규칙 카드와 같은 값, 4주 평균의
정의, 분모 바뀜(새 분기·개정·같은 주), 4주/13주 나눔의 합·창·표시와 13주가 지준·재정 카드와 같은 값, 단기자금 5영업일(최대·이른
날·n/m·월말·15일), 주의 꼬리표와 FOMC 표(연준 인물 페이지의 회의 장부와 같다), 칸마다 실패·직전 값 이어 싣기, 이용 조건 목록,
문구 원칙(판정 낱말 없음), 화면·워크플로 연결.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — FRED는 가짜 loader 또는 합성 캐시(--offline). 숫자는 모두 지어낸 것이다(실자료 숫자를 넣지 않는다).
"""
import os, sys, io, re, json, datetime, tempfile, unittest, shutil, contextlib
from unittest import mock

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import fedbs_fetch as fb
import liquidity_fetch as liq
import ai_invest_fetch as ai
import regime_check as rc
import regime_rules as rr
import render_public as rp
from test_render_public import FORBIDDEN_TEXT
from test_people_site import load_data as load_people

REPO = os.path.dirname(SCRIPTS)
D = datetime.date
TD = datetime.timedelta
NOW = datetime.datetime(2026, 10, 30, 22, 30, tzinfo=datetime.timezone.utc)
# 판정·방향 낱말 — 공개 카드 어디에도 없어야 한다(FORBIDDEN_TEXT에 더해)
VERDICT = ("판정", "충족", "신호", "경보", "전망", "매수", "매도", "⚠", "●", "○", "강세", "약세", "호재", "악재", "우려", "부담",
           "상승", "하락", "→", "긴축", "완화", "위험", "문턱", "임계", "발동")
# 카드 주제 낱말 — FORBIDDEN_TEXT의 '재정'은 이 꼴로만 허용한다(앞 카드 이름 '지준·재정')
TOPIC = ("지준·재정",)

# 수요일 수준(백만 달러): 07-29 이하 = 기준, 07-29 뒤 ~ 09-30 = 중간, 09-30 뒤 = 마지막
# → 13주(07-29 → 10-28)·4주(09-30 분기말 → 10-28) 변화를 손으로 셀 수 있다
LEVELS = {"WRBWFRBL": (3_000_000, 2_950_000, 2_900_000),     # 지준 −100 / −50
          "WDTGAL": (800_000, 850_000, 880_000),             # TGA +80 / +30 → 지준 쪽 −80 / −30
          "WLRRAOL": (10_000, 5_000, 2_000),                 # 익일물 역레포 −8 / −3 → +8 / +3
          "WLRRAFOIAL": (300_000, 310_000, 300_000),         # 해외 공적 0 / −10 → 0 / +10
          "WSHOBL": (200_000, 230_000, 260_000),             # 단기채 +60 / +30
          "WSHONBNL": (3_600_000, 3_598_000, 3_597_000),     # 이표채 −3 / −1
          "WSHOMCB": (2_000_000, 1_970_000, 1_950_000),      # MBS −50 / −20
          "WCICL": (2_400_000, 2_410_000, 2_415_000)}        # 현금 +15 / +5 → −15 / −5
# 그 밖: 13주 −100 − (−80 + 8 + 0 + 60 − 3 − 50 − 15) = −20 · 4주 −50 − (−30 + 3 + 10 + 30 − 1 − 20 − 5) = −37
WANT13 = {"res": -100, "tga": -80, "onrrp": 8, "pool": 0, "bills": 60, "coupons": -3, "mbs": -50, "cur": -15, "other": -20}
WANT4 = {"res": -50, "tga": -30, "onrrp": 3, "pool": 10, "bills": 30, "coupons": -1, "mbs": -20, "cur": -5, "other": -37}
WED = D(2026, 10, 28)


def weds(start, end):
    out, d = [], start
    while d <= end:
        out.append(d)
        d += TD(days=7)
    return out


def bdays(start, end):
    out, d = [], start
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += TD(days=1)
    return out


def level(sid, d):
    a, b, c = LEVELS[sid]
    return a if d <= D(2026, 7, 29) else b if d <= D(2026, 9, 30) else c


def world(last_wed=WED, last_day=D(2026, 10, 30)):
    """주 평균 지준 2,800bn(마지막 네 주 3,100·3,000·2,900·2,800 → 4주 평균 2,950) ÷ GDP 2026Q3 32,000 = 8.75%(하한 9.0 대비
    −0.25%p ≈ −80bn · 4주 평균 9.21875%). 단기자금: SOFR − IORB 10-26~10-30 = 0 · +2 · 0 · 0 · +8(10-30 월말) → 최대 +8 · 2/5일,
    상시 레포 10-30에 12.5bn, 익일물 역레포 마지막 3.2bn."""
    W = weds(D(2025, 1, 1), last_wed)
    S = {"WRESBAL": [(d, 3_000_000.0) for d in W[:-4]]
         + list(zip(W[-4:], (3_100_000.0, 3_000_000.0, 2_900_000.0, 2_800_000.0))),
         "GDP": [(D(2026, 1, 1), 29_000.0), (D(2026, 4, 1), 30_000.0), (D(2026, 7, 1), 32_000.0)]}
    for sid in LEVELS:
        S[sid] = [(d, float(level(sid, d))) for d in W]
    B = bdays(D(2026, 9, 1), last_day)
    S["IORB"] = [(D(2026, 9, 1) + TD(days=i), 3.90) for i in range((last_day - D(2026, 9, 1)).days + 1)]
    S["SOFR"] = [(d, {D(2026, 10, 30): 3.98, D(2026, 10, 27): 3.92}.get(d, 3.90)) for d in B]
    S["RPONTTLD"] = [(d, 12.5 if d == D(2026, 10, 30) else 0.0) for d in B]
    S["RRPONTSYD"] = [(d, 3.2 if d == last_day else 1.0) for d in B]
    return S


class FakeFred:
    def __init__(self, data, fail=(), cache=()):
        self.data, self.fail, self.cache, self.calls = data, set(fail), set(cache), []

    def __call__(self, sid, cache_dir, offline=False, timeout=None):
        self.calls.append((sid, timeout))
        if sid in self.fail:
            raise RuntimeError(f"{sid}: 원문 사유 https://bad.invalid/xyz-77")
        return list(self.data[sid]), ("cache" if sid in self.cache else "net")


def calc(key, S=None, today=NOW.date()):
    return fb.BY_KEY[key]["calc"](world() if S is None else S, today)


def dec_numbers(line):
    """나눔 줄의 보이는 정수 — {창: [지준, TGA, 익일물, 해외, 단기채, 이표채, MBS, 현금, 그 밖]} ('—'는 None)."""
    assert line.endswith(" " + fb.SIGN_NOTE), line
    body = line[:-len(fb.SIGN_NOTE) - 1]
    pairs = re.findall(r"(—|[+-]?[\d,]+)/(—|[+-]?[\d,]+)", body)
    num = lambda x: None if x == "—" else int(x.replace(",", ""))
    return {"4": [num(a) for a, _ in pairs], "13": [num(b) for _, b in pairs]}


class ArithmeticTest(unittest.TestCase):
    def test_reserves_values_and_line(self):
        c = calc("reserves")
        v = c["values"]
        self.assertEqual(c["date"], "2026-10-28")
        self.assertEqual((v["level"], v["gdp_quarter"], v["gdp_bn"], v["low"]), (2800.0, "2026-07-01", 32000.0, 9.0))
        self.assertAlmostEqual(v["value"], 8.75)
        self.assertAlmostEqual(v["gap_pp"], -0.25)
        self.assertAlmostEqual(v["gap_bn"], -80.0)
        self.assertAlmostEqual(v["avg4"], 2950 / 32000 * 100, places=6)
        self.assertEqual(v["avg4_from"], "2026-10-07")
        self.assertEqual((v["base_quarter"], v["base_bn"], v["denom_pp"]), (None, None, None))
        self.assertEqual((v["first_quarter"], v["first_bn"]), ("2026-07-01", 32000.0))   # 이 주를 처음 실을 때의 GDP
        line, extra = fb.texts("reserves", v, c["date"])
        self.assertEqual(line, "지준 2,800.0bn (주 평균) = 명목 GDP의 8.75% (2026Q3) · 규칙 하한 9.0% 대비 -0.25%p ≈ -80.0bn · "
                               "4주 평균 9.22%")
        self.assertIn("2026Q3 32,000bn", extra[0])
        self.assertTrue(extra[1].startswith(fb.AVG4_DEF + " — 2026-10-07~2026-10-28 네 주"), extra[1])

    def test_reserves_match_the_rule_card(self):
        for S in (world(), {"WRESBAL": [(d, 2_950_000.0 + 7 * i) for i, d in enumerate(weds(D(2026, 1, 7), D(2026, 10, 21)))],
                            "GDP": [(D(2026, 1, 1), 31_234.5), (D(2026, 4, 1), 32_100.25)]}):
            ind, _, _ = rc.compute(S, D(2026, 10, 30))
            want = ind["reserves_gdp"]
            v = fb.calc_reserves(S, D(2026, 10, 30))["values"]
            rule = liq.calc_rule(S)["values"]
            self.assertAlmostEqual(v["value"], want["value"], places=6)
            self.assertEqual(v["gdp_quarter"], want["gdp_quarter"])
            self.assertEqual(fb.calc_reserves(S, D(2026, 10, 30))["date"], want["asof"])
            self.assertEqual(v["low"], rr.TH["reserves_gdp_low"])
            self.assertAlmostEqual(v["gap_pp"], rule["gap_pp"], places=4)              # 지준·재정 카드의 하한 대비와 같은 값
            self.assertAlmostEqual(v["gap_bn"], rule["gap_bn"], places=4)
            self.assertEqual(f"{v['value']:.2f}", f"{rule['value']:.2f}")            # 화면의 같은 숫자

    def test_four_week_average_needs_four_consecutive_weeks(self):
        S = world()
        S["WRESBAL"] = S["WRESBAL"][:-3] + S["WRESBAL"][-2:]                           # 10-14 주가 빠졌다
        v = fb.calc_reserves(S, NOW.date())["values"]
        self.assertEqual((v["avg4"], v["avg4_from"]), (None, None))
        line, extra = fb.texts("reserves", v, "2026-10-28")
        self.assertTrue(line.endswith("4주 평균 —"), line)
        self.assertIn("최근 네 주가 이어지지 않아", extra[1])
        S["WRESBAL"] = world()["WRESBAL"][-3:]                                         # 세 주뿐
        self.assertIsNone(fb.calc_reserves(S, NOW.date())["values"]["avg4"])

    def test_four_week_average_divides_by_the_latest_gdp(self):
        # 정의는 하나 — (최근 4주 지준 평균) ÷ 최신 GDP. 각 주를 그 주의 GDP로 나눈 평균이 아니다
        S = world()
        S["GDP"] = S["GDP"] + [(D(2026, 10, 1), 40_000.0)]                             # 마지막 주 안에 새 분기가 들어와도
        v = fb.calc_reserves(S, NOW.date())["values"]
        self.assertAlmostEqual(v["avg4"], 2950 / 40000 * 100, places=6)
        self.assertEqual(v["gdp_quarter"], "2026-10-01")

    def test_chart_lines_are_52_weeks_and_the_floor_uses_the_latest_gdp(self):
        c = calc("reserves")
        res, low = c["lines"]["res"], c["lines"]["low"]
        self.assertEqual(len(res), fb.CHART_WEEKS)
        self.assertEqual([p[0] for p in res], [p[0] for p in low])
        self.assertEqual(res[-1], ["2026-10-28", 2800.0])
        self.assertEqual({p[1] for p in low}, {9.0 / 100 * 32000})                     # 2,880bn — 지난 주들도 지금 GDP로
        self.assertEqual(res[0][0], (WED - TD(weeks=51)).isoformat())

    @staticmethod
    def shown_with(core, q, g, date="2026-10-21"):
        """직전 파일의 칸 — 그 주를 GDP (q, g)로 처음 실었다."""
        return {"date": date, "values": dict(core["values"], gdp_quarter=q, gdp_bn=g, first_quarter=q, first_bn=g)}

    def test_denominator_change_new_quarter(self):
        core = calc("reserves")
        old = self.shown_with(core, "2026-04-01", 30000.0)
        v = fb.with_base(core, old)["values"]
        self.assertEqual((v["base_quarter"], v["base_bn"]), ("2026-04-01", 30000.0))
        self.assertAlmostEqual(v["denom_pp"], 2800 / 32000 * 100 - 2800 / 30000 * 100, places=6)
        line, extra = fb.texts("reserves", v, "2026-10-28")
        self.assertTrue(line.endswith(" · 분모 바뀜 -0.58%p (GDP 2026Q2에서 2026Q3로)"), line)
        self.assertIn("직전 주를 처음 실을 때의 GDP(2026Q2 30,000bn)", extra[-1])
        self.assertEqual((v["first_quarter"], v["first_bn"]), ("2026-07-01", 32000.0))   # 이번 주는 이번 GDP로 처음 싣는다

    def test_denominator_change_same_quarter_revision(self):
        core = calc("reserves")
        old = self.shown_with(core, "2026-07-01", 31000.0)
        v = fb.with_base(core, old)["values"]
        self.assertAlmostEqual(v["denom_pp"], 2800 / 32000 * 100 - 2800 / 31000 * 100, places=6)
        self.assertTrue(fb.texts("reserves", v, "2026-10-28")[0].endswith(" · 분모 바뀜 -0.28%p (2026Q3 개정)"))

    def test_denominator_same_gdp_or_first_week_is_quiet(self):
        core = calc("reserves")
        v = fb.with_base(core, {"date": "2026-10-21", "values": dict(core["values"])})["values"]
        self.assertEqual((v["base_quarter"], v["base_bn"], v["denom_pp"]), ("2026-07-01", 32000.0, None))   # 기준은 남긴다
        self.assertNotIn("분모 바뀜", fb.texts("reserves", v, "2026-10-28")[0])
        v = fb.with_base(core, None)["values"]                                          # 처음 싣는 주 — 견줄 것이 없다
        self.assertEqual((v["base_quarter"], v["denom_pp"]), (None, None))

    def test_denominator_same_week_keeps_its_base(self):
        core = calc("reserves")
        shown = fb.with_base(core, self.shown_with(core, "2026-04-01", 30000.0))
        again = fb.with_base(core, shown)["values"]                                    # 같은 주를 다음 날 다시
        self.assertEqual((again["base_quarter"], again["base_bn"]), ("2026-04-01", 30000.0))
        self.assertEqual(again["denom_pp"], shown["values"]["denom_pp"])
        first = fb.with_base(core, None)                                                # 같은 주, 기준 없음 → 계속 없음
        self.assertIsNone(fb.with_base(core, first)["values"]["denom_pp"])

    def test_denominator_compares_with_the_gdp_the_last_week_was_first_shown_with(self):
        # 검토 F1(site): 같은 주 안에서 GDP만 바뀌면(H.4.1이 하루 늦은 주의 GDP 발표 등) 다음 주가 그 바뀜을 싣는다 — 기준은 직전
        # 주를 처음 실을 때의 GDP(비공개 fed_bs가 메일로 실은 주의 GDP와 견주는 것과 같은 뜻)
        S = world(last_wed=D(2026, 10, 21), last_day=D(2026, 10, 23))
        S["GDP"] = S["GDP"][:-1]                                                        # 10-21 주를 2026Q2 GDP 30,000으로
        day1 = fb.with_base(fb.calc_reserves(S, D(2026, 10, 22)), None)
        S["GDP"] = world()["GDP"]                                                       # 같은 주, 다음 날 GDP 2026Q3 32,000
        day2 = fb.with_base(fb.calc_reserves(S, D(2026, 10, 23)), day1)["values"]
        self.assertEqual((day2["gdp_quarter"], day2["first_quarter"], day2["first_bn"]), ("2026-07-01", "2026-04-01", 30000.0))
        self.assertIsNone(day2["denom_pp"])                                             # 처음 실은 주라 그 주엔 견줄 기준이 없다
        nxt = fb.with_base(calc("reserves"), {"date": "2026-10-21", "values": day2})["values"]   # 10-28 주
        self.assertEqual((nxt["base_quarter"], nxt["base_bn"]), ("2026-04-01", 30000.0))
        self.assertAlmostEqual(nxt["denom_pp"], 2800 / 32000 * 100 - 2800 / 30000 * 100, places=6)
        self.assertEqual((nxt["first_quarter"], nxt["first_bn"]), ("2026-07-01", 32000.0))

    def test_decomposition_adds_up(self):
        c = calc("dec")
        v = c["values"]
        self.assertEqual((c["date"], v["to"], v["from4"], v["from13"]), ("2026-10-28", "2026-10-28", "2026-09-30", "2026-07-29"))
        for w, want in (("4", WANT4), ("13", WANT13)):
            for k, x in want.items():
                self.assertAlmostEqual(v[f"{k}{w}"], x, msg=f"{k}{w}")
            self.assertAlmostEqual(sum(v[f"{k}{w}"] for k in fb.PARTS), v[f"res{w}"])
        line, extra = fb.texts("dec", v, c["date"])
        self.assertEqual(line, "지준 변화 4주/13주 -50/-100bn = 재무부 현금(TGA) -30/-80 · 익일물 역레포 +3/+8 · 해외 공적 역레포 "
                               "+10/0 · 연준 단기채 +30/+60 · 연준 이표채 -1/-3 · 연준 MBS -20/-50 · 현금 통화 -5/-15 · "
                               "그 밖 -37/-20 (부호는 지준 쪽)")
        self.assertEqual(line.count(fb.SIGN_NOTE), 1)
        self.assertTrue(extra[0].startswith("창: 4주 2026-09-30(분기말)~2026-10-28 · 13주 2026-07-29~2026-10-28 — "), extra[0])
        self.assertTrue(extra[1].startswith("4주 창은 분기말(2026-09-30)에서 출발해"), extra[1])

    def test_thirteen_weeks_equal_the_liquidity_card(self):
        S = world()
        S["WLRRAL"] = [(d, a + b) for (d, a), (_, b) in zip(S["WLRRAOL"], S["WLRRAFOIAL"])]
        lq = liq.calc_reserves(S)
        v = fb.calc_dec(S, NOW.date())["values"]
        self.assertEqual((lq["date"], lq["values"]["from"]), (v["to"], v["from13"]))
        for mine, theirs in ((v["res13"], "res"), (v["tga13"], "tga"), (v["bills13"], "bills"), (v["coupons13"], "coupons"),
                             (v["onrrp13"] + v["pool13"], "rrp"), (v["mbs13"] + v["cur13"] + v["other13"], "other")):
            self.assertAlmostEqual(mine, lq["values"][theirs], places=6, msg=theirs)

    def test_one_window_can_be_missing(self):
        S = world()
        for sid in ("WDTGAL",):                                                         # 09-23·09-30 두 주가 빠졌다 → 4주 출발이 없다
            S[sid] = [p for p in S[sid] if p[0] not in (D(2026, 9, 23), D(2026, 9, 30))]
        v = fb.calc_dec(S, NOW.date())["values"]
        self.assertIsNone(v["from4"])
        self.assertTrue(all(v[f"{k}4"] is None for k in ("res", *fb.PARTS)))
        self.assertEqual(v["from13"], "2026-07-29")
        line, extra = fb.texts("dec", v, v["to"])
        self.assertEqual(dec_numbers(line)["4"], [None] * 9)
        self.assertEqual(dec_numbers(line)["13"], [WANT13[k] for k in ("res", *fb.PARTS)])
        self.assertIn("4주 —", extra[0])
        self.assertTrue(fb._dec_ok(v))
        S = {sid: [(WED, 1.0)] for sid in fb.BS.values()}                               # 창이 하나도 없다
        with self.assertRaises(fb.ItemError) as e:
            fb.calc_dec(S, NOW.date())
        self.assertEqual(e.exception.code, "format")

    def test_window_needs_an_observation_near_the_start(self):
        for gap, ok in ((6, True), (7, False)):
            old = WED - TD(days=91 + gap)
            S = {sid: [(old, 1000.0), (WED, 2000.0)] for sid in fb.BS.values()}
            r = fb.decompose(S, 91)
            self.assertEqual(r is not None, ok, gap)

    def test_last_common_wednesday(self):
        S = world()
        S["WCICL"] = S["WCICL"][:-1]                                                    # 현금 통화가 한 주 늦다
        v = fb.calc_dec(S, NOW.date())["values"]
        self.assertEqual((v["to"], v["from4"], v["from13"]), ("2026-10-21", "2026-09-23", "2026-07-22"))

    def test_shown_numbers_add_up_even_when_each_rounds_away(self):
        base = calc("dec")["values"]
        cases = [dict(res4=-0.6, tga4=0.4, onrrp4=0.4, pool4=0.4, bills4=0.4, coupons4=0.4, mbs4=0.4, cur4=0.4, other4=-3.4),
                 dict(res4=10.5, tga4=2.5, onrrp4=3.5, pool4=-0.5, bills4=1.5, coupons4=0.5, mbs4=0.5, cur4=0.5, other4=1.5),
                 dict(res4=1234.4, tga4=-1100.6, onrrp4=0.49, pool4=2000.51, bills4=-0.5, coupons4=0.5, mbs4=-1.5, cur4=0.0,
                      other4=335.44)]
        for case in cases:
            v = dict(base, **case)
            nums = dec_numbers(fb.texts("dec", v, "2026-10-28")[0])["4"]
            self.assertEqual(sum(nums[1:]), nums[0], (case, nums))
            self.assertEqual(nums[0], round(case["res4"]))
        self.assertIn("지준 변화 4주/13주 +1,234/-100bn", fb.texts("dec", dict(base, **cases[2]), "2026-10-28")[0])

    def test_level_and_daily_tags(self):
        self.assertEqual([fb.level_tag(D(2026, m, d)) for m, d in ((9, 30), (10, 31), (10, 15), (10, 14), (12, 31), (11, 30))],
                         ["분기말", "월말", "15일", "", "분기말", "월말"])
        days = bdays(D(2026, 11, 2), D(2026, 12, 3))                                    # 11-15는 일요일 → 11-16(월)이 15일 표시
        self.assertEqual(fb.cal_tag(D(2026, 11, 16), days), "15일")
        self.assertEqual(fb.cal_tag(D(2026, 11, 17), days), "")
        self.assertEqual(fb.cal_tag(D(2026, 11, 30), days), "월말")                      # 다음 관측이 다음 달
        self.assertEqual(fb.cal_tag(D(2026, 10, 30), bdays(D(2026, 10, 1), D(2026, 10, 30))), "월말")   # 마지막 관측(금), 뒤 평일 없음
        self.assertEqual(fb.cal_tag(D(2026, 10, 29), bdays(D(2026, 10, 1), D(2026, 10, 29))), "")    # 마지막 관측이지만 30일(금)이 남음

    def test_short_term_funding(self):
        v = calc("spread")["values"]
        self.assertEqual(v, {"from": "2026-10-26", "max_bp": 8.0, "max_date": "2026-10-30", "max_tag": "월말", "pos": 2,
                             "n": 5, "days": 5})
        self.assertEqual(fb.texts("spread", v, "2026-10-30")[0],
                         "SOFR − IORB 최대 +8bp (2026-10-30 월말) · 0보다 큰 날 2/5일 (2026-10-26~2026-10-30)")
        s = calc("srf")
        self.assertEqual(s["values"], {"from": "2026-10-26", "max_bn": 12.5, "max_date": "2026-10-30", "max_tag": "월말"})
        self.assertEqual(fb.texts("srf", s["values"], s["date"])[0], "상시 레포 이용 최대 12.5bn (2026-10-30 월말) · 2026-10-26~2026-10-30")
        r = calc("rrp")
        self.assertEqual((r["date"], r["values"]), ("2026-10-30", {"bn": 3.2, "tag": "월말"}))
        self.assertEqual(fb.texts("rrp", r["values"], r["date"])[0], "익일물 역레포 3.2bn (2026-10-30 월말)")

    def test_ties_take_the_earliest_day_and_far_iorb_is_left_out(self):
        S = world()
        S["SOFR"] = [(d, 3.95 if d in (D(2026, 10, 27), D(2026, 10, 30)) else 3.90) for d, _ in S["SOFR"]]
        S["RPONTTLD"] = [(d, 0.0) for d, _ in S["RPONTTLD"]]
        self.assertEqual(calc("spread", S)["values"]["max_date"], "2026-10-27")         # 같은 최대면 이른 날(월말이 가져가지 않게)
        self.assertEqual(calc("srf", S)["values"]["max_date"], "2026-10-26")
        S["IORB"] = [p for p in S["IORB"] if p[0] <= D(2026, 10, 25)]                   # IORB가 10-25에서 끊겼다
        v = calc("spread", S)["values"]
        self.assertEqual((v["n"], v["days"]), (3, 5))                                   # 10-26·27·28(3일 안)만
        line, extra = fb.texts("spread", v, "2026-10-30")
        self.assertIn("0보다 큰 날 1/3일", line)
        self.assertIn("5일 중 3일만", extra[-1])
        S["IORB"] = [p for p in S["IORB"] if p[0] <= D(2026, 10, 10)]
        with self.assertRaises(fb.ItemError):
            calc("spread", S)

    def test_week_tags_and_next_fomc(self):
        v = calc("week")["values"]
        self.assertEqual(v, {"from": "2026-10-22", "d15": False, "month_end": False, "fomc": ["2026-10-28"],
                             "next_fomc": "2026-12-09", "next_tentative": False})
        line, extra = fb.texts("week", v, "2026-10-28")
        self.assertEqual(line, "이 주(2026-10-22~2026-10-28) FOMC 뒤 첫 H.4.1(2026-10-28 결정) · 다음 FOMC 2026-12-09")
        self.assertTrue(extra[0].startswith("FOMC 결정일(수)이 이 주의 마지막 날이라"), extra[0])
        S = world(last_wed=D(2026, 9, 30))                                               # 09-24~09-30: 월말(분기말) 포함, FOMC 없음
        v = fb.calc_week(S, D(2026, 10, 1))["values"]
        self.assertEqual((v["month_end"], v["d15"], v["fomc"], v["next_fomc"]), (True, False, [], "2026-10-28"))
        self.assertTrue(fb.texts("week", v, "2026-09-30")[0].startswith("이 주(2026-09-24~2026-09-30) 월말 포함 · 다음 FOMC"))
        v = fb.calc_week(world(last_wed=D(2026, 9, 16)), D(2026, 9, 16))["values"]      # 09-10~09-16: 15일 + 결정일 09-16
        self.assertEqual((v["d15"], v["fomc"], v["next_fomc"]), (True, ["2026-09-16"], "2026-09-16"))   # 결정일 당일은 '다음'
        self.assertIn("15일 포함 · FOMC 뒤 첫 H.4.1(2026-09-16 결정)", fb.texts("week", v, "2026-09-16")[0])
        v = fb.calc_week(world(last_wed=D(2026, 10, 21)), D(2026, 10, 21))["values"]
        self.assertTrue(fb.texts("week", v, "2026-10-21")[0].startswith("이 주(2026-10-15~2026-10-21) 15일 포함 · 다음 FOMC"))
        v = fb.calc_week(world(), D(2026, 12, 10))["values"]                             # 2027년은 연준 일정 페이지의 잠정 일정
        self.assertEqual((v["next_fomc"], v["next_tentative"]), ("2027-01-27", True))
        self.assertTrue(fb.texts("week", v, "2026-10-28")[0].endswith("다음 FOMC 2027-01-27(잠정)"))
        v = fb.calc_week(world(), D(2027, 3, 18))["values"]                              # 검토 F1: 3월 뒤에도 4월 회의가 있다
        self.assertEqual((v["next_fomc"], v["next_tentative"]), ("2027-04-28", True))
        S = world()
        S["WRESBAL"] = [(D(2027, 4, 21), 3_000_000.0), (D(2027, 4, 28), 3_000_000.0)]     # 04-22~04-28 주 = 04-28 결정 주
        v = fb.calc_week(S, D(2027, 4, 30))["values"]
        self.assertEqual((v["fomc"], v["next_fomc"]), (["2027-04-28"], "2027-06-09"))
        self.assertIn("FOMC 뒤 첫 H.4.1(2027-04-28 결정)", fb.texts("week", v, "2027-04-28")[0])
        v = fb.calc_week(world(), D(2027, 12, 9))["values"]                              # 표 밖(2027-12-08 뒤)
        self.assertEqual((v["next_fomc"], v["next_tentative"]), (None, False))
        self.assertTrue(fb.texts("week", v, "2026-10-28")[0].endswith("다음 FOMC 미기재"))
        v = calc("week", world(last_wed=D(2026, 10, 7)), D(2026, 10, 9))["values"]       # 15일·월말·FOMC 없음
        self.assertIn("이 주(2026-10-01~2026-10-07) 15일·월말·FOMC 없음", fb.texts("week", v, "2026-10-07")[0])

    def test_next_fomc_is_the_first_meeting_without_a_statement_yet(self):
        # 검토 F2: 예약 실행(UTC 22:17)은 결정일에도 성명(14:00 미 동부) 뒤다 — 그날 회의는 '다음'이 아니다
        utc = datetime.timezone.utc
        S = world(last_wed=D(2026, 12, 2), last_day=D(2026, 12, 4))
        at = lambda *a: fb.calc_week(S, D(*a[:3]), datetime.datetime(*a, tzinfo=utc))["values"]["next_fomc"]
        self.assertEqual(at(2026, 12, 9, 22, 17), "2027-01-27")                         # 결정일 저녁 예약 실행 — 다음 회의
        self.assertEqual(at(2026, 12, 9, 15, 0), "2026-12-09")                          # 성명 전(10:00 EST) — 그날 회의
        self.assertEqual(at(2026, 12, 9, 18, 59), "2026-12-09")                         # 겨울(EST)엔 19:00 UTC
        self.assertEqual(at(2026, 12, 9, 19, 0), "2027-01-27")
        self.assertEqual(at(2026, 10, 28, 17, 59), "2026-10-28")                        # 서머타임(EDT)엔 18:00 UTC
        self.assertEqual(at(2026, 10, 28, 18, 0), "2026-12-09")
        self.assertEqual(at(2026, 12, 8, 22, 17), "2026-12-09")                         # 하루 앞
        v = fb.calc_week(S, D(2026, 12, 9))["values"]                                   # 시각을 주지 않으면 그날 0시(UTC)
        self.assertEqual(v["next_fomc"], "2026-12-09")
        naive = fb.calc_week(S, D(2026, 12, 9), datetime.datetime(2026, 12, 9, 22, 17))["values"]   # 시간대 없으면 UTC로
        self.assertEqual(naive["next_fomc"], "2027-01-27")
        # compute·main이 실행 시각을 주 칸에 넘긴다
        core = fb.compute(S, {}, D(2026, 12, 9), datetime.datetime(2026, 12, 9, 22, 17, tzinfo=utc))
        self.assertEqual(core["week"]["values"]["next_fomc"], "2027-01-27")
        self.assertEqual(fb.compute(S, {}, D(2026, 12, 9))["week"]["values"]["next_fomc"], "2026-12-09")

    def test_decision_time_follows_us_daylight_saving(self):
        utc = datetime.timezone.utc
        self.assertEqual(fb.decided_at(D(2026, 3, 18)), datetime.datetime(2026, 3, 18, 18, tzinfo=utc))   # 03-08부터 EDT
        self.assertEqual(fb.decided_at(D(2026, 1, 28)), datetime.datetime(2026, 1, 28, 19, tzinfo=utc))
        self.assertEqual(fb.decided_at(D(2026, 11, 4)), datetime.datetime(2026, 11, 4, 19, tzinfo=utc))   # 11-01부터 EST
        self.assertEqual(fb.decided_at(D(2026, 10, 28)), datetime.datetime(2026, 10, 28, 18, tzinfo=utc))
        self.assertEqual(fb.decided_at(D(2027, 3, 17)), datetime.datetime(2027, 3, 17, 18, tzinfo=utc))   # 2027-03-14부터 EDT
        try:
            from zoneinfo import ZoneInfo
            ny = ZoneInfo("America/New_York")
        except Exception:                                                              # 시간대 자료가 없는 환경 — 위 손 셈만
            return
        for _, b, _ in fb.FOMC:                                                         # 표의 모든 결정일 — tzdata와 같다
            d = D.fromisoformat(b)
            want = datetime.datetime(d.year, d.month, d.day, fb.DECISION_HOUR, tzinfo=ny).astimezone(utc)
            self.assertEqual(fb.decided_at(d), want, b)

    def test_fomc_table_matches_the_people_page(self):
        with open(os.path.join(REPO, "site", "people-data.js"), encoding="utf-8") as f:
            page = load_people(f.read())
        theirs = [(m["first_day"], m["date"]) for m in page["meetings_2026"]]
        mine = [(a, b) for a, b, _ in fb.FOMC if b.startswith("2026")]
        self.assertEqual(mine, theirs)
        for a, b, tentative in fb.FOMC:
            self.assertEqual(D.fromisoformat(b).weekday(), 2, b)                       # 결정일은 수요일
            self.assertEqual(D.fromisoformat(b) - D.fromisoformat(a), TD(days=1))
            self.assertEqual(tentative, b >= "2027", b)                                # 잠정은 2027년만
        self.assertEqual([b for _, b, _ in fb.FOMC], sorted(b for _, b, _ in fb.FOMC))
        # 2027년 = 연준 FOMC 일정 페이지(2026-10-28 갱신, 2026-11-03 확인)의 여덟 회의(검토 F1 — 전엔 2차 보도의 3월까지만)
        self.assertEqual([(a, b) for a, b, _ in fb.FOMC if b.startswith("2027")],
                         [("2027-01-26", "2027-01-27"), ("2027-03-16", "2027-03-17"), ("2027-04-27", "2027-04-28"),
                          ("2027-06-08", "2027-06-09"), ("2027-07-27", "2027-07-28"), ("2027-09-14", "2027-09-15"),
                          ("2027-10-26", "2027-10-27"), ("2027-12-07", "2027-12-08")])

    def test_observations_after_today_are_dropped(self):
        S = world()
        S["WDTGAL"] = S["WDTGAL"] + [(D(2026, 11, 4), 999_999.0)]
        S["SOFR"] = S["SOFR"] + [(D(2026, 11, 2), 9.0)]
        out = fb.compute(S, {}, NOW.date())
        self.assertEqual(out["dec"]["date"], "2026-10-28")
        self.assertEqual(out["spread"]["values"]["max_bp"], 8.0)

    def test_every_item_computes_and_texts_have_no_verdict_words(self):
        core = fb.compute(world(), {}, NOW.date())
        for spec in fb.ITEMS:
            c = core[spec["key"]]
            self.assertNotIsInstance(c, fb.ItemError, spec["key"])
            self.assertEqual(set(c["values"]), set(spec["values"]), spec["key"])
            self.assertTrue(fb.values_ok(spec, c["values"], c["lines"]), spec["key"])
            line, extra = fb.texts(spec["key"], c["values"], c["date"])
            for t in [line, *extra, spec["title"], fb.NOTICE, fb.COMPUTED_NOTICE, fb.WEEK_NOTICE, fb.SPREAD_DERIVED,
                      fb.SRF_DERIVED, *[ln["label"] for ln in spec.get("lines", ())], spec.get("chart", {}).get("note", "")]:
                self.assertNotIn("None", t)
                body = t
                for ok in TOPIC:
                    body = body.replace(ok, "")
                for word in list(FORBIDDEN_TEXT) + list(VERDICT):
                    self.assertNotIn(word, body, (spec["key"], word))


class LicenceTest(unittest.TestCase):
    def test_series_list_is_fixed_and_checked(self):
        self.assertEqual(fb.SERIES, ["WRESBAL", "GDP", "WRBWFRBL", "WDTGAL", "WLRRAOL", "WLRRAFOIAL", "WSHOBL", "WSHONBNL",
                                     "WSHOMCB", "WCICL", "SOFR", "IORB", "RPONTTLD", "RRPONTSYD"])
        self.assertEqual(fb.LICENCE, {**{sid: "public-domain" for sid in fb.SERIES},
                                      "SOFR": "citation-required", "RPONTTLD": "citation-required",
                                      "RRPONTSYD": "citation-required"})
        self.assertFalse(set(fb.SERIES) & (set(rp.RESTRICTED) | set(ai.RESTRICTED)))
        self.assertIn("SOFR", rp.CITATION_REQUIRED)                                    # 규칙 카드와 같은 판단
        for spec in fb.ITEMS:
            self.assertLessEqual(set(spec["series"]), set(fb.SERIES))
        for sid in ("WRESBAL", "GDP", "SOFR"):                                        # 규칙 카드와 같은 인용
            self.assertEqual(fb.SOURCES[sid], (rp.FRED_SOURCE[sid], rp.FRED_TITLE[sid]))
        for sid in ("WRBWFRBL", "WDTGAL", "WSHOBL", "WSHONBNL"):                       # 지준·재정 카드와 같은 인용
            self.assertEqual(fb.SOURCES[sid], liq.SOURCES[sid])

    def test_citation_form(self):
        self.assertEqual(fb.citation("RPONTTLD", "2026-11-03"),
                         "Federal Reserve Bank of New York, Overnight Repurchase Agreements: Total Securities Purchased by the "
                         "Federal Reserve in the Temporary Open Market Operations [RPONTTLD], retrieved from FRED, Federal "
                         "Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/RPONTTLD, November 3, 2026.")

    def test_new_york_fed_items_carry_the_notices(self):
        sp = fb.notices("spread", "2026-11-03")
        for t in (rp.SOFR_NOTICE, rp.SOFR_DTCC, rp.nyfed_attribution("2026"), rp.NOT_AFFILIATED, fb.SPREAD_DERIVED,
                  fb.SPREAD_DERIVED_EN):
            self.assertIn(t, sp)
        for key in ("srf", "rrp"):
            nt = fb.notices(key, "2027-01-04")
            self.assertIn(rp.nyfed_attribution("2027"), nt)
            self.assertIn(rp.NOT_AFFILIATED, nt)
            self.assertNotIn(rp.SOFR_NOTICE, nt)                                       # 참조금리 고지는 SOFR 칸만
        self.assertIn(fb.SRF_DERIVED, fb.notices("srf", "2026-11-03"))
        for key in ("reserves", "dec", "week"):
            self.assertFalse([t for t in fb.notices(key, "2026-11-03") if "New York" in t], key)
        self.assertIn("newyorkfed.org 이용약관", rp.DATA_LICENSE)
        self.assertRegex(rp.DATA_LICENSE, r"뉴욕 연은 자료\([^)]*상시 레포·익일물 역레포[^)]*\)는 newyorkfed\.org 이용약관")


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.out = os.path.join(self.tmp, "data")
        self.work = os.path.join(self.tmp, ".work")
        self.path = os.path.join(self.out, fb.FILE)
        self.S = world()

    def run_main(self, fred=None, now=NOW, extra=(), clock=None):
        fred = fred or FakeFred(self.S)
        buf = io.StringIO()
        kw = {"clock": clock} if clock else {}
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = fb.main(["--out", self.out, "--work", self.work, *extra], fred_load=fred, now=now, **kw)
        return code, buf.getvalue()

    def saved(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def save(self, js):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(js, f, ensure_ascii=False)

    def test_first_run_writes_every_item(self):
        code, log = self.run_main()
        self.assertEqual(code, 0, log)
        js = self.saved()
        self.assertEqual(set(js), {"schema", "generated_at", "notice", "order", "items"})
        self.assertEqual(js["order"], ["reserves", "dec", "spread", "srf", "rrp", "week"])
        for key, it in js["items"].items():
            self.assertTrue(it["ok"], key)
            want = {"ok", "stale", "error", "failed_since", "key", "name", "date", "values", "retrieved", "line", "extra",
                    "notices", "sources"} | ({"chart"} if key == "reserves" else set())
            self.assertEqual(set(it), want, key)
            self.assertEqual(it["retrieved"], "2026-10-30")
            self.assertEqual([s["series"] for s in it["sources"]], fb.BY_KEY[key]["series"])
            for src in it["sources"]:
                self.assertEqual(src["licence"], fb.LICENCE[src["series"]])
                self.assertTrue(src["citation"].startswith(fb.SOURCES[src["series"]][0]))
                self.assertTrue(src["citation"].endswith("October 30, 2026."))
        ch = js["items"]["reserves"]["chart"]
        self.assertEqual([ln["key"] for ln in ch["lines"]], ["res", "low"])
        self.assertEqual((ch["unit"], ch["threshold"]), ("bn", None))
        self.assertEqual(len(ch["lines"][0]["points"]), fb.CHART_WEEKS)
        self.assertNotIn("2,800", log)                                                 # 로그에는 날짜와 사유만
        self.assertNotIn("-80", log)

    def test_one_missing_series_only_stales_its_items(self):
        self.run_main()
        code, log = self.run_main(fred=FakeFred(self.S, fail={"WDTGAL"}), now=NOW + TD(days=1))
        self.assertEqual(code, 0, log)
        items = self.saved()["items"]
        d = items["dec"]
        self.assertEqual((d["ok"], d["stale"], d["error"], d["failed_since"]), (False, True, fb.REASONS["fetch"], "2026-10-31"))
        self.assertEqual(d["retrieved"], "2026-10-30")
        self.assertIn("재무부 현금(TGA) -30/-80", d["line"])                             # 직전 숫자에서 다시 만든 문구
        self.assertTrue(all(items[k]["ok"] for k in ("reserves", "spread", "srf", "rrp", "week")))
        self.assertIn("::warning::연준 재무상태표 참고 dec 받지 못함", log)
        self.assertNotIn("xyz-77", log)
        self.run_main(fred=FakeFred(self.S, fail={"IORB", "WRESBAL"}), now=NOW + TD(days=2))
        items = self.saved()["items"]
        self.assertEqual({k for k, it in items.items() if not it["ok"]}, {"spread", "reserves", "week"})
        self.assertEqual(items["dec"]["failed_since"], None)                           # 다시 받으면 실패 날짜가 지워진다
        self.run_main(fred=FakeFred(self.S, fail={"IORB"}), now=NOW + TD(days=3))
        self.assertEqual(self.saved()["items"]["spread"]["failed_since"], "2026-11-01")  # 못 받기 시작한 날을 지킨다

    def test_first_failure_without_previous_has_no_numbers(self):
        self.run_main(fred=FakeFred(self.S, cache={"RRPONTSYD"}))
        it = self.saved()["items"]["rrp"]
        self.assertEqual((it["ok"], it["stale"], it["error"]), (False, False, fb.REASONS["cache"]))
        for k in ("line", "values", "notices", "chart"):
            self.assertNotIn(k, it)
        self.assertEqual([s["series"] for s in it["sources"]], ["RRPONTSYD"])

    def test_offline_reads_the_cache(self):
        cache = os.path.join(self.work, fb.CACHE)
        os.makedirs(cache)
        for sid, s in self.S.items():
            with open(os.path.join(cache, f"{sid}.csv"), "w", encoding="utf-8") as f:
                f.write("observation_date," + sid + "\n" + "".join(f"{d.isoformat()},{v}\n" for d, v in s))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), mock.patch.object(ai.urllib.request, "urlopen", side_effect=AssertionError("요청")):
            code = fb.main(["--out", self.out, "--work", self.work, "--offline"], now=NOW)
        self.assertEqual(code, 0, buf.getvalue())
        items = self.saved()["items"]
        self.assertTrue(all(it["ok"] for it in items.values()))
        self.assertAlmostEqual(items["dec"]["values"]["other13"], -20)

    def test_online_fetch_goes_through_the_bounded_reader(self):
        bodies = {sid: ("observation_date," + sid + "\n" + "".join(f"{d.isoformat()},{v}\n" for d, v in s)).encode()
                  for sid, s in self.S.items()}

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read1(self, n=-1):
                return self.read(n)
        seen = []

        def opener(url, timeout=None):
            self.assertTrue(url.startswith("https://fred.stlouisfed.org/graph/fredgraph.csv?id="), url)
            sid = url.split("id=")[1]
            seen.append((sid, timeout))
            return Resp(bodies[sid])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = fb.main(["--out", self.out, "--work", self.work], now=NOW, opener=opener)
        self.assertEqual(code, 0, buf.getvalue())
        self.assertEqual([s for s, _ in seen], fb.SERIES)                               # 시리즈마다 한 번, 14번
        self.assertTrue(all(0 < t <= ai.TIMEOUT for _, t in seen))
        self.assertTrue(os.path.exists(os.path.join(self.work, fb.CACHE, "WSHOMCB.csv")))

    def test_requests_carry_no_custom_headers(self):
        # FRED는 사용자 정의 User-Agent를 붙이면 응답을 멈춘다 — 주소 글자만 넘기고 Request 객체·머리글을 만들지 않는다
        with open(os.path.join(SCRIPTS, "fedbs_fetch.py"), encoding="utf-8") as f:
            src = f.read()
        for tok in ("User-Agent", "Request(", "headers", "urlopen"):
            self.assertNotIn(tok, src)

    def test_older_data_is_not_taken(self):
        self.run_main()
        short = dict(self.S, SOFR=self.S["SOFR"][:-1])
        self.run_main(fred=FakeFred(short), now=NOW + TD(days=1))
        it = self.saved()["items"]["spread"]
        self.assertEqual((it["ok"], it["stale"], it["error"]), (False, True, fb.REASONS["older"]))
        self.assertEqual(it["date"], "2026-10-30")
        short = dict(self.S, GDP=self.S["GDP"][:-1])                                    # 칸 날짜는 그대로, GDP 분기만 이르다
        self.run_main(fred=FakeFred(short), now=NOW + TD(days=2))
        self.assertEqual(self.saved()["items"]["reserves"]["error"], fb.REASONS["older"])

    def test_same_numbers_keep_the_file(self):
        self.run_main()
        with open(self.path, "rb") as f:
            first = f.read()
        self.run_main(now=NOW + TD(days=1))
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), first)

    def test_a_new_week_compares_the_denominator_with_the_last_file(self):
        S = world(last_wed=D(2026, 10, 21), last_day=D(2026, 10, 23))
        S["GDP"] = S["GDP"][:-1]                                                        # 10-21 주엔 2026Q2 GDP 30,000까지
        self.run_main(fred=FakeFred(S), now=datetime.datetime(2026, 10, 22, 22, 30, tzinfo=datetime.timezone.utc))
        r = self.saved()["items"]["reserves"]
        self.assertEqual((r["date"], r["values"]["denom_pp"]), ("2026-10-21", None))   # 처음 싣는 주엔 견줄 것이 없다
        self.run_main(now=NOW)                                                          # 10-28 주, 2026Q3 GDP 32,000
        r = self.saved()["items"]["reserves"]
        self.assertEqual((r["date"], r["retrieved"], r["values"]["base_quarter"]), ("2026-10-28", "2026-10-30", "2026-04-01"))
        self.assertAlmostEqual(r["values"]["denom_pp"], 2800 / 32000 * 100 - 2800 / 30000 * 100, places=6)
        self.assertIn("분모 바뀜 -0.58%p (GDP 2026Q2에서 2026Q3로)", r["line"])
        self.run_main(now=NOW + TD(days=1))                                             # 같은 주 다음 날 — 견줌을 그대로
        r2 = self.saved()["items"]["reserves"]
        self.assertEqual((r2["line"], r2["retrieved"]), (r["line"], "2026-10-30"))
        self.run_main(fred=FakeFred(self.S, fail={"GDP"}), now=NOW + TD(days=2))      # 이어 실을 때도 문구 그대로
        self.assertEqual(self.saved()["items"]["reserves"]["line"], r["line"])

    def test_a_gdp_change_inside_a_week_shows_on_the_next_week(self):
        # 검토 F1(site): 10-21 주를 2분기 GDP로 처음 싣고 → 같은 주에 3분기 GDP가 들어옴 → 10-28 주가 분모 바뀜을 싣는다
        S = world(last_wed=D(2026, 10, 21), last_day=D(2026, 10, 23))
        S["GDP"] = S["GDP"][:-1]
        self.run_main(fred=FakeFred(S), now=datetime.datetime(2026, 10, 22, 22, 30, tzinfo=datetime.timezone.utc))
        S2 = world(last_wed=D(2026, 10, 21), last_day=D(2026, 10, 23))
        self.run_main(fred=FakeFred(S2), now=datetime.datetime(2026, 10, 23, 22, 30, tzinfo=datetime.timezone.utc))
        r = self.saved()["items"]["reserves"]
        self.assertEqual((r["date"], r["values"]["gdp_quarter"], r["values"]["first_quarter"]),
                         ("2026-10-21", "2026-07-01", "2026-04-01"))
        self.run_main(now=NOW)                                                          # 10-28 주
        r = self.saved()["items"]["reserves"]
        self.assertIn("분모 바뀜 -0.58%p (GDP 2026Q2에서 2026Q3로)", r["line"])
        self.run_main(now=NOW + TD(days=7))                                             # 같은 숫자의 다음 실행 — 그대로
        self.assertIn("분모 바뀜 -0.58%p", self.saved()["items"]["reserves"]["line"])

    def test_a_broken_previous_file_is_not_carried(self):
        self.run_main()
        js = self.saved()
        js["items"]["week"]["values"]["fomc"] = ["어제"]                                # 날짜 꼴이 아니다
        js["items"]["dec"]["values"]["res4"] = None                                     # 창의 숫자가 반만 있다
        js["items"]["spread"]["values"]["pos"] = 9                                      # n보다 크다
        js["items"]["reserves"]["chart"]["lines"][0]["points"][0][1] = "9"              # 그래프 점이 숫자가 아니다
        js["items"]["rrp"]["values"]["tag"] = "<b>"                                     # 정해 둔 표시가 아니다
        js["items"]["srf"]["values"]["extra"] = 1.0                                     # 모르는 값
        self.save(js)
        self.run_main(fred=FakeFred(self.S, fail=set(self.S)), now=NOW + TD(days=1))
        items = self.saved()["items"]
        for key in fb.BY_KEY:
            self.assertEqual((items[key]["ok"], items[key]["stale"]), (False, False), key)
            self.assertNotIn("line", items[key])
        self.assertNotIn("어제", json.dumps(self.saved(), ensure_ascii=False))

    def test_carried_text_is_rebuilt_from_numbers(self):
        self.run_main()
        js = self.saved()
        for it in js["items"].values():
            it["line"] = "<b>원문 오류 https://bad.invalid</b>"
            it["extra"] = ["매수"]
            it["notices"] = ["바깥 글"]
            it["name"] = "바뀐 이름"
        js["items"]["reserves"]["chart"]["note"] = "바깥 글"
        self.save(js)
        self.run_main(fred=FakeFred(self.S, fail=set(self.S)), now=NOW + TD(days=1))
        dump = json.dumps(self.saved(), ensure_ascii=False)
        for bad in ("bad.invalid", "매수", "바깥 글", "바뀐 이름"):
            self.assertNotIn(bad, dump)
        self.assertTrue(all(it["stale"] for it in self.saved()["items"].values()))

    def test_previous_checks_the_schema(self):
        good = {"reserves": {"key": "reserves"}, "dec": {"key": "dec"}}
        os.makedirs(self.out)
        for js, want in (({"schema": fb.SCHEMA, "items": good}, good),
                         ({"schema": fb.SCHEMA + 1, "items": good}, {}),
                         ({"items": good}, {}),
                         ({"schema": fb.SCHEMA, "items": [good]}, {}),
                         ([good], {}),
                         ({"schema": fb.SCHEMA, "items": dict(good, zzz={"key": "zzz"}, week="x")}, good)):
            self.save(js)
            self.assertEqual(fb.previous(self.out), want, js)
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{깨진")
        self.assertEqual(fb.previous(self.out), {})

    def test_budget_runs_out_without_waiting(self):
        t = [0.0]

        def clock():
            t[0] += 15.0
            return t[0]
        fred = FakeFred(self.S)
        code, log = self.run_main(fred=fred, clock=clock)
        self.assertLess(len(fred.calls), len(fb.SERIES))
        self.assertTrue(all(1 <= tmo <= ai.TIMEOUT for _, tmo in fred.calls))
        self.assertIn("::warning::", log)

    def test_nothing_fetched_exits_1(self):
        code, log = self.run_main(fred=FakeFred(self.S, fail=set(self.S)))
        self.assertEqual(code, 1, log)
        self.assertTrue(all(not it["ok"] for it in self.saved()["items"].values()))

    def test_a_calculation_error_fails_only_its_item(self):
        with mock.patch.dict(fb.BY_KEY["srf"], calc=mock.Mock(side_effect=ZeroDivisionError("원문"))):   # ITEMS와 같은 dict
            code, log = self.run_main()
        self.assertEqual(code, 0, log)
        items = self.saved()["items"]
        self.assertEqual((items["srf"]["ok"], items["srf"]["error"]), (False, fb.REASONS["format"]))
        self.assertTrue(items["rrp"]["ok"])
        self.assertNotIn("원문", log)

    def test_the_write_is_atomic(self):
        self.run_main()
        with open(self.path, "rb") as f:
            before = f.read()
        with mock.patch.object(ai.os, "replace", side_effect=OSError("disk full")):
            S = dict(self.S, RRPONTSYD=self.S["RRPONTSYD"] + [(D(2026, 11, 2), 4.0)])
            code, log = self.run_main(fred=FakeFred(S), now=NOW + TD(days=3))
        self.assertEqual(code, 1, log)
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), before)
        self.assertEqual(os.listdir(self.out), [fb.FILE])

    def test_every_string_is_fixed_text_without_verdict_words(self):
        runs = [(FakeFred(self.S, fail={"IORB"}), NOW),                                  # 직전 값 없는 첫 실패
                (FakeFred(self.S), NOW + TD(days=1)),
                (FakeFred(self.S, fail={"WRESBAL", "WSHOMCB"}), NOW + TD(days=2)),      # 직전 값을 이어 싣는 실패
                (FakeFred(self.S, cache={"SOFR"}), NOW + TD(days=3))]
        urls, errors = set(), set()
        for fred, now in runs:                                                          # 실행마다 파일 전체를 본다
            self.run_main(fred=fred, now=now)
            dump = json.dumps(self.saved(), ensure_ascii=False)
            body = dump
            for ok in TOPIC:
                body = body.replace(ok, "")
            for word in list(FORBIDDEN_TEXT) + list(VERDICT):
                self.assertNotIn(word, body, word)
            urls |= {u.rstrip(".") for u in re.findall(r"https?://[^\s,;)\"]+", dump)}
            self.assertNotIn("bad.invalid", dump)
            self.assertNotIn("@", dump)
            errors |= {it["error"] for it in self.saved()["items"].values()} - {None}
            nested = re.compile(r"\([^()]*\(")                                         # 겹 괄호 없음('미수신(까닭)'이 겹치지 않게)
            for t in re.findall(r'"((?:[^"\\]|\\.)*)"', dump):
                self.assertIsNone(nested.search(t), t)
        self.assertEqual(urls, {f"https://fred.stlouisfed.org/series/{sid}" for sid in fb.SERIES})
        self.assertEqual(errors, {fb.REASONS["fetch"], fb.REASONS["cache"]})          # 정해 둔 문구만


class StaticTest(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
            return f.read()

    def test_workflow_fetches_without_failing_the_run(self):
        wf = self.read(".github", "workflows", "daily.yml")
        self.assertTrue("id: fedbs" in wf, "daily.yml에 연준 재무상태표 단계(id: fedbs) 없음")
        step = wf[wf.index("id: fedbs"):]
        self.assertIn("continue-on-error: true", step[:200])
        self.assertIn("timeout-minutes: 2", step[:200])
        self.assertIn("python scripts/fedbs_fetch.py", step[:300])
        self.assertLess(wf.index("id: liquidity"), wf.index("id: fedbs"))               # 지준·재정 바로 뒤
        self.assertLess(wf.index("id: fedbs"), wf.index("id: tp"))
        self.assertLess(wf.index("id: fedbs"), wf.index("공개 전 검사(새 산출물 포함)"))
        self.assertLess(wf.index("id: fedbs"), wf.index("git add data"))
        self.assertNotIn("fedbs", wf[wf.index("\n  alert:"):])                           # 실패해도 알림을 띄우지 않는다
        self.assertIn("node --test scripts/test_fedbs_render.cjs", wf[wf.index("\n  check:"):wf.index("\n  update:")])
        # 갱신 잡의 상한 주석 — 참고 단계 제한의 합(2분짜리 단계 수 × 2 + 한국 4)
        m = re.search(r"timeout-minutes: (\d+) +# 참고 자료 단계 제한의 합\((.*?) = (\d+)분\)", wf)
        self.assertIsNotNone(m)
        parts = [int(x) for x in re.findall(r"(\d+)(?= \+| =|$)", m.group(2))]
        self.assertEqual(sum(parts), int(m.group(3)))
        upd = wf[wf.index("\n  update:"):wf.index("\n  deploy:")]
        steps = re.findall(r"^ {8}timeout-minutes: (\d+)", upd, flags=re.M)          # 단계(들여쓰기 8칸)만 — 잡의 상한은 빼고
        self.assertEqual(sum(int(x) for x in steps), int(m.group(3)))                  # 주석의 합 = 실제 단계 제한의 합
        self.assertLess(int(m.group(3)), int(m.group(1)))

    def test_readme_counts_and_section(self):
        readme = self.read("README.md")
        m = re.search(r"\*\*아침 쪽 Python 테스트 (\d+)개 \+ node 테스트 (\d+)개\*\*\((.*?)\)와 \*\*저녁판", readme)
        py_part, node_part = m.group(3).split(" / node: ")
        mine = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()
        self.assertRegex(py_part, rf"(^| · )연준 재무상태표 참고 {mine}( · |$)")
        cjs = len(re.findall(r"^test\(", self.read("scripts", "test_fedbs_render.cjs"), flags=re.M))
        self.assertRegex(node_part, rf"(^| · )연준 재무상태표 카드 그리기 {cjs}( · |$)")
        self.assertIn("## 참고: 연준 재무상태표", readme)
        sec = readme[readme.index("## 참고: 연준 재무상태표"):]
        sec = sec[:sec.index("\n## ", 5)]
        for sid in fb.SERIES:
            self.assertIn(f"`{sid}`", sec, sid)
        self.assertIn("python -X utf8 scripts/fedbs_fetch.py", readme)
        self.assertIn("node --test scripts/test_fedbs_render.cjs", readme)

    def test_page_wires_the_card(self):
        page = self.read("site", "index.html")
        for snippet in ('getJson("data/fedbs.json")', '<script src="fedbs.js"></script>',
                        '<a href="data/fedbs.json">', 'id:"fedbs-slot"', "window.FedBsCard.render("):
            self.assertTrue(snippet in page, f"index.html에 {snippet} 없음")
        group = page[page.index('g.id === "liquidity" ? el("div", {id:"liquidity-slot"'):][:300]   # 유동성 묶음, 지준·재정 바로 뒤
        self.assertIn('g.id === "liquidity" ? el("div", {id:"fedbs-slot", class:"oil-slot"})', group)
        self.assertLess(page.index('<script src="charts.js"></script>'), page.index('<script src="fedbs.js"></script>'))
        line = next(l for l in page.splitlines() if "window.FedBsCard.render(" in l)
        self.assertRegex(line, r"^\s*try \{ if \(isObj\(fbs\) && window\.FedBsCard\)")   # 깨져도 그 카드만 빠진다

    def test_card_intro_is_one_register_and_covers_the_notice(self):
        js = self.read("site", "fedbs.js")
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        self.assertNotIn("d.notice", code)
        self.assertIn('el("p", { class: "muted" }, ABOUT)', code)
        about = "".join(re.findall(r'"([^"]*)"', code[code.index("const ABOUT = "):].split(";\n", 1)[0]))
        for sent in filter(None, re.split(r"(?<=\.)\s+", about)):
            self.assertTrue(sent.endswith("니다."), sent)
        for mine, theirs in (("규칙 수에 들지 않습니다", "규칙 점검에 쓰지 않는"),
                             ("H.4.1 주간 대차대조표와 단기자금 시장의 공개 통계", "H.4.1 주간 대차대조표와 단기자금 시장의 공개 통계"),
                             ("'지준과 통화승수'의 지준/GDP와 지준·재정 카드의 13주 나눔을 주간으로 읽는 재료",
                              "'지준과 통화승수'의 지준/GDP와 지준·재정 카드의 13주 나눔을 주간으로 읽는 재료"),
                             ("금리나 자금 여건을 예측하지 않습니다", "금리나 자금 여건을 예측하지 않는다")):
            self.assertIn(mine, about)
            self.assertIn(theirs, fb.NOTICE)

    def test_screen_script_matches_the_file_and_avoids_verdict_words(self):
        js = self.read("site", "fedbs.js")
        card = re.findall(r'"(\w+)"', js[js.index("const CARD = ["):].split("]")[0])
        self.assertEqual(card, [s["key"] for s in fb.ITEMS])
        reasons = re.findall(r'"([^"]+)"', js[js.index("const REASONS = ["):].split("];")[0])
        self.assertEqual(reasons, list(fb.REASONS.values()))
        self.assertIn('const LABEL = "참고 — 예측 아님";', js)
        self.assertIn('"연준 재무상태표(H.4.1 주간)"', js)
        for tok in ("innerHTML", "outerHTML", "insertAdjacentHTML", "createElement", "fetch(", "eval(", "location.",
                    "localStorage", "<img", "src=", "href"):
            self.assertNotIn(tok, js)
        body = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        for ok in TOPIC:
            body = body.replace(ok, "")
        for word in list(FORBIDDEN_TEXT) + list(VERDICT):
            self.assertNotIn(word, body, word)
        self.assertIn('getElementById("fedbs-slot")', js)
        self.assertIn("window.FedBsCard = ", js)

    def test_policy_quotes_match_the_checked_primary_text(self):
        # 정책 사실은 2026-11-03 연준 원문(보도자료 monetary20251029a · a1 · 20251210a)에서 옮긴 그대로 — 글자를 바꾸지 않는다
        js = self.read("site", "fedbs.js")
        flat = "".join(re.findall(r'"([^"]*)"', js[js.index('["정책 사실(1차 출처)"'):].split("]", 1)[0]))
        for quote in ("The Committee decided to conclude the reduction of its aggregate securities holdings on December 1.",
                      "Beginning on December 1, reinvest all principal payments from the Federal Reserve's holdings of agency "
                      "securities into Treasury bills.",
                      "will initiate purchases of shorter-term Treasury securities as needed to maintain an ample supply of "
                      "reserves on an ongoing basis.",
                      "monetary20251029a", "monetary20251029a1", "monetary20251210a"):
            self.assertIn(quote, flat)
        est = "".join(re.findall(r'"([^"]*)"', js[js.index('["측정 기록 — 추정"'):].split("]", 1)[0]))
        for word in ("추정", "공식 수치가 아닙니다", "2026-11-03", "8·9월 창", "아직 끝나지 않은 창", "늘려 잡"):
            self.assertIn(word, est)
        self.assertNotIn("8·9·10월", est)                                              # 검토 F3: 10월 창은 끝나지 않았다
        fomc = "".join(re.findall(r'"([^"]*)"', js[js.index('["FOMC 뒤 첫 H.4.1"'):].split("]", 1)[0]))
        for word in ("2026-10-28 갱신", "확정되기 전까지 잠정", "FOMCpresconf20261028", "14:00 미 동부"):
            self.assertIn(word, fomc)
        self.assertNotIn("2차 보도", fomc)


if __name__ == "__main__":
    unittest.main(verbosity=1)
