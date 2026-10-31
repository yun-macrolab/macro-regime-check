#!/usr/bin/env python3
"""AI 투자 참고 자료(ai_invest_fetch) 테스트 — 산식(답을 아는 합성 자료), 칸마다 실패·직전 값 이어 싣기, 재배포 제한 지수 값
비노출, 문구 원칙, 원자적 쓰기, 종료코드, 화면·워크플로 연결.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — FRED는 가짜 loader 또는 합성 캐시(--offline). 숫자는 모두 지어낸 것이다.
"""
import os, sys, io, re, json, math, random, datetime, tempfile, unittest, shutil, contextlib
from unittest import mock

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import ai_invest_fetch as ai
import render_public as rp
import fred_fetch as ff
from test_render_public import FORBIDDEN_TEXT

REPO = os.path.dirname(SCRIPTS)
D = datetime.date
NOW = datetime.datetime(2026, 10, 27, 1, 30, tzinfo=datetime.timezone.utc)
SPEC_KEYS = {"key", "title", "unit", "years", "zero", "threshold", "note", "source_note", "notices", "lines"}
LINE_KEYS = {"key", "label", "role", "series", "derived", "points"}
# 재배포 제한 지수의 지어낸 수준 — 출력 어디에도 이 값이 나오면 안 된다(시작값을 눈에 띄게)
LEVEL_START = {"SP500": 7351.37, "NASDAQNQINTEL": 1234.56, "NASDAQNDXTMC": 2468.13, "NASDAQCOM": 9876.54}


def bdays(start, end):
    out, d = [], start
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += datetime.timedelta(days=1)
    return out


def months(start, end):
    out, (y, m) = [], (start.year, start.month)
    while D(y, m, 1) <= end:
        out.append(D(y, m, 1))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def quarters(start, end):
    return [d for d in months(start, end) if d.month in (1, 4, 7, 10)]


def world(end=D(2026, 10, 23), seed=7):
    """{ID: [(date, value)]} — 일간 주가·금리, 월간·분기 통계. 주가 수익률이 금리 변화와 일정 몫 같이 움직인다."""
    rnd = random.Random(seed)
    days = bdays(D(2018, 10, 29), end)
    S = {k: [] for k in ("SP500", "NASDAQNQINTEL", "NASDAQNDXTMC", "NASDAQCOM", "DGS10", "DGS30")}
    sp, aiv, ndx, y10, y30 = LEVEL_START["SP500"], LEVEL_START["NASDAQNQINTEL"], LEVEL_START["NASDAQNDXTMC"], 2.5, 3.0
    com = LEVEL_START["NASDAQCOM"]
    for d in days:
        dy = rnd.gauss(0, 0.05)
        m = rnd.gauss(0, 0.01) + 0.05 * dy
        sp *= 1 + m
        aiv *= 1 + 1.2 * m + rnd.gauss(0, 0.008) + 0.03 * dy
        ndx *= 1 + 1.1 * m + rnd.gauss(0, 0.006) + 0.02 * dy
        com *= 1 + 1.05 * m + rnd.gauss(0, 0.004)
        y10 += dy
        y30 += dy * 0.8 + rnd.gauss(0, 0.01)
        S["SP500"].append((d, sp))
        S["NASDAQNQINTEL"].append((d, aiv))
        S["NASDAQCOM"].append((d, com))
        if d >= D(2022, 3, 21):
            S["NASDAQNDXTMC"].append((d, ndx))
        S["DGS10"].append((d, round(y10, 2)))
        S["DGS30"].append((d, round(y30, 2)))
    qs = quarters(D(1980, 1, 1), D(2026, 4, 1))
    gdp = [(q, 3000 * 1.0125 ** i) for i, q in enumerate(qs)]
    S["GDP"] = gdp
    peak = D(2000, 10, 1)

    def share(q, base, bump):
        x = base + bump * math.exp(-((q - peak).days / 700) ** 2)
        return x + (1.5 if q >= D(2024, 1, 1) else 0) * ((q - D(2024, 1, 1)).days / 900 if q >= D(2024, 1, 1) else 0)

    S["A679RC1Q027SBEA"] = [(q, g * share(q, 3.4, 1.0) / 100) for q, g in gdp]
    S["Y034RC1Q027SBEA"] = [(q, g * share(q, 2.0, 0.8) / 100) for q, g in gdp]
    S["BOGZ1FA106000135Q"] = [(q, 1000 * 1.012 ** i) for i, q in enumerate(qs)]
    S["BOGZ1FA105050005Q"] = [(q, v * (1.05 + 0.15 * math.sin(i / 7))) for i, (q, v) in enumerate(S["BOGZ1FA106000135Q"])]
    ms = months(D(2005, 1, 1), D(2026, 9, 1))
    S["A34SNO"] = [(m, 20000 * 1.004 ** i * (1 + 0.05 * math.sin(i / 5))) for i, m in enumerate(ms)]
    S["IPG3344S"] = [(m, 50 * 1.006 ** i) for i, m in enumerate(ms)]
    S["PROFCONS"] = [(m, 60000 * 1.003 ** i) for i, m in enumerate(ms) if m <= D(2026, 8, 1)]
    S["WPU0543"] = [(m, 150 * 1.003 ** i) for i, m in enumerate(ms)]
    S["CUSR0000SEHF01"] = [(m, 200 * 1.0035 ** i) for i, m in enumerate(ms) if m != D(2025, 10, 1)]   # 결측월
    S["PCEPILFE"] = [(m, 100 * 1.0022 ** i) for i, m in enumerate(ms)]
    S["UNRATE"] = [(m, round(4.0 + 0.3 * math.sin(i / 11), 1)) for i, m in enumerate(ms) if m != D(2025, 10, 1)]
    t30, t10 = dict(ai.monthly_mean(S["DGS30"])), dict(ai.monthly_mean(S["DGS10"]))
    S["HQMCB30YRP"] = [(m, t30[m] + 0.9 + 0.2 * math.sin(i / 7)) for i, m in enumerate(sorted(t30))
                       if m <= D(2026, 9, 1)]
    S["HQMCB10YRP"] = [(m, t10[m] + 0.7) for m in sorted(t10) if m <= D(2026, 9, 1)]
    S.update(z1_world())
    return S


def z1_world(end=D(2026, 4, 1)):
    """연준 Z.1 사모대출 열 줄(백만 달러) — 분기마다 곧은 선, 잔액은 2012Q4 앞이 0. 값은 지어낸 것이다."""
    qs = quarters(D(2010, 1, 1), end)
    lin = lambda a, b: [(q, a + b * i) for i, q in enumerate(qs)]
    pc = ai.PC
    return {pc["total"]: [(q, 0.0 if q < D(2012, 10, 1) else 400000.0 + 15000.0 * i) for i, q in enumerate(qs)],
            pc["nfc"]: lin(100000.0, 5000.0), pc["nfc_debt"]: lin(9000000.0, 40000.0),
            pc["pdf_liab"]: lin(200000.0, 6000.0), pc["pdf_fa"]: lin(600000.0, 9000.0),
            pc["bdc_liab"]: lin(80000.0, 3000.0), pc["bdc_fa"]: lin(200000.0, 4000.0),
            pc["pdf_bank"]: lin(50000.0, 2000.0), pc["bdc_bank"]: lin(30000.0, 1000.0),
            pc["dry"]: lin(100000.0, 3500.0)}


def long_world(seed=11):
    """1990~2026 — 물가 조건(근원 PCE 연 약 5%)인 달은 주가와 금리가 반대로(음), 실업률이 오르는 달은 같은 방향(양)으로 움직이는 세계."""
    rnd = random.Random(seed)
    ms = months(D(1985, 1, 1), D(2026, 9, 1))
    infl_m = {m for m in ms if D(1990, 1, 1) <= m <= D(1994, 12, 1) or D(2022, 1, 1) <= m <= D(2023, 6, 1)}
    pce, lvl = [], 100.0
    for m in ms:
        lvl *= 1.0042 if m in infl_m else 1.0015
        pce.append((m, lvl))
    un, u = [], 5.0
    for m in ms:
        if D(2001, 4, 1) <= m <= D(2002, 6, 1) or D(2008, 7, 1) <= m <= D(2009, 10, 1):
            u += 0.15
        elif u > 4.0:
            u -= 0.05
        un.append((m, round(u, 1)))
    S = {"PCEPILFE": pce, "UNRATE": un, "NASDAQCOM": [], "DGS10": [], "SP500": []}
    infl, unemp = ai.month_states(S, D(1985, 1, 1))
    px, y = 5000.0, 6.0
    for d in bdays(D(1989, 1, 2), D(2026, 10, 23)):
        mk = ai._mkey(d)
        i, u2 = infl.get(mk, (0, False))[1], unemp.get(mk, (0, False))[1]
        beta = -0.1 if i else 0.1 if u2 else 0.03
        dy = rnd.gauss(0, 0.05)
        px *= 1 + rnd.gauss(0, 0.01) + beta * dy
        y += dy
        S["NASDAQCOM"].append((d, px))
        S["DGS10"].append((d, round(y, 2)))
        if d >= D(2016, 10, 24):
            S["SP500"].append((d, px * 0.7))
    return S


class FakeFred:
    """fred_fetch.load 꼴. fail: 실패할 ID, cache: 캐시로 대신한 것처럼 돌려줄 ID."""
    def __init__(self, data, fail=(), cache=()):
        self.data, self.fail, self.cache, self.calls = data, set(fail), set(cache), []

    def __call__(self, sid, cache_dir, offline=False, timeout=None):
        self.calls.append((sid, timeout))
        if sid in self.fail:
            raise RuntimeError(f"{sid}: 원문 사유 https://bad.invalid/xyz-77")
        return list(self.data[sid]), ("cache" if sid in self.cache else "net")


class ArithmeticTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.S = world()

    def test_60_day_corr_is_the_rule_card_calculation(self):
        core = ai.calc_corr60(self.S)
        for key, sid in (("sp", "SP500"), ("ai", "NASDAQNQINTEL"), ("ndx", "NASDAQNDXTMC")):
            want = ff.corr_summary(self.S[sid], self.S["DGS10"], 60)["value"]
            self.assertAlmostEqual(core["values"][key], want, places=4)
        last = core["lines"]["sp"][-1]
        self.assertAlmostEqual(last[1], ff.corr_summary(self.S["SP500"], self.S["DGS10"], 60)["value"], places=2)

    def test_rolling_corr_skips_a_zero_price_like_corr_summary(self):
        px = list(self.S["NASDAQNQINTEL"])
        px[-30] = (px[-30][0], 0.0)
        got = ai.rolling_corr(px, self.S["DGS10"], 60)[-1][1]
        self.assertAlmostEqual(got, ff.corr_summary(px, self.S["DGS10"], 60)["value"], places=12)

    def test_partial_corr_equals_correlation_of_residuals(self):
        tr = ai.triples(self.S["SP500"], self.S["NASDAQNQINTEL"], self.S["DGS10"])[-60:]
        s, x, y = [t[1] for t in tr], [t[2] for t in tr], [t[3] for t in tr]

        def resid(v):
            ms, mv = sum(s) / 60, sum(v) / 60
            b = sum((a - ms) * (c - mv) for a, c in zip(s, v)) / sum((a - ms) ** 2 for a in s)
            return [c - mv - b * (a - ms) for a, c in zip(s, v)]
        want = ff.pearson(resid(x), resid(y))
        got = ai.rolling_partial(self.S["SP500"], self.S["NASDAQNQINTEL"], self.S["DGS10"], 60)[-1][1]
        self.assertAlmostEqual(got, want, places=10)

    def test_chance_band(self):
        self.assertAlmostEqual(ai.null_band(20), 0.4424, places=3)
        self.assertAlmostEqual(ai.null_band(60), 0.2539, places=3)
        self.assertAlmostEqual(ai.null_band(60, 1), 0.2561, places=3)

    def test_monthly_yoy_needs_the_same_months_a_year_earlier(self):
        s = [(m, float(i + 100)) for i, m in enumerate(months(D(2023, 1, 1), D(2025, 6, 1))) if m != D(2024, 3, 1)]
        one = dict(ai.monthly_yoy(s))
        self.assertNotIn(D(2024, 3, 1), one)                     # 그 달이 없다
        self.assertNotIn(D(2025, 3, 1), one)                     # 1년 전 같은 달이 없다 — 전 달로 대신하지 않는다
        self.assertAlmostEqual(one[D(2025, 6, 1)], (129 / 117 - 1) * 100)
        three = dict(ai.monthly_yoy(s, 3))
        for m in (D(2024, 3, 1), D(2024, 4, 1), D(2024, 5, 1), D(2025, 3, 1), D(2025, 4, 1), D(2025, 5, 1)):
            self.assertNotIn(m, three)                           # 석 달 가운데 하나라도 없으면 비운다
        self.assertAlmostEqual(three[D(2025, 6, 1)], ((127 + 128 + 129) / (115 + 116 + 117) - 1) * 100)

    def test_quarterly_ratio_of_four_quarter_sums(self):
        qs = quarters(D(2020, 1, 1), D(2021, 10, 1))
        num = [(q, 10.0 + i) for i, q in enumerate(qs) if q != D(2020, 7, 1)]
        den = [(q, 20.0) for q in qs]
        r = dict(ai.quarterly_ratio(num, den, 4))
        self.assertEqual(sorted(r), [D(2021, 7, 1), D(2021, 10, 1)])   # 빠진 분기(2020-07)가 든 합은 없다
        self.assertAlmostEqual(r[D(2021, 10, 1)], (14 + 15 + 16 + 17) / 80 * 100)

    def test_ict_share_peak_is_taken_inside_1995_2002(self):
        core = ai.calc_ict_share(self.S)
        v = core["values"]
        self.assertEqual(v["peak_date"], "2000-10-01")
        self.assertGreater(v["share"], v["peak"])                 # 지금 값이 더 높아도 고점은 그 창에서만
        tot = dict(ai.quarterly_ratio(self.S["A679RC1Q027SBEA"], self.S["GDP"]))
        self.assertAlmostEqual(v["share_1y"], tot[D(2025, 4, 1)], places=4)
        self.assertEqual(core["lines"]["total"][0][0], "1990-01-01")

    def test_financing_median_and_share_above_100(self):
        v = ai.calc_financing(self.S)["values"]
        ratio = [x for d, x in ai.quarterly_ratio(self.S["BOGZ1FA105050005Q"], self.S["BOGZ1FA106000135Q"], 4)
                 if d >= D(1985, 1, 1)]
        self.assertAlmostEqual(v["median"], sorted(ratio)[len(ratio) // 2] if len(ratio) % 2 else
                               (sorted(ratio)[len(ratio) // 2 - 1] + sorted(ratio)[len(ratio) // 2]) / 2, places=4)
        self.assertAlmostEqual(v["above100"], sum(x > 100 for x in ratio) / len(ratio) * 100, places=4)
        self.assertEqual((v["n"], v["from"]), (len(ratio), "1985-01-01"))

    def test_power_keeps_each_series_own_month(self):
        v = ai.calc_power(self.S)["values"]
        self.assertEqual((v["ppi_date"], v["cpi_date"]), ("2026-09-01", "2026-09-01"))
        cpi = dict(ai.monthly_yoy(self.S["CUSR0000SEHF01"]))
        self.assertNotIn(D(2025, 10, 1), cpi)
        self.assertNotIn(D(2026, 10, 1), cpi)

    def test_curve_in_bp_with_year_ago_and_five_year_range(self):
        v = ai.calc_curve_30_10(self.S)["values"]
        sp = [(d, (a - b) * 100) for d, a, b in ff.align(self.S["DGS30"], self.S["DGS10"])]
        self.assertAlmostEqual(v["spread"], sp[-1][1], places=4)
        self.assertAlmostEqual(v["spread_1y"], ff.on_or_before(sp, D(2026, 10, 23) - datetime.timedelta(days=364))[1], 4)
        win = [x for d, x in sp if d >= D(2021, 10, 23)]
        self.assertEqual((v["lo"], v["hi"]), (round(min(win), 4), round(max(win), 4)))

    def test_corr20_share_outside_the_band(self):
        v = ai.calc_corr20(self.S)["values"]
        r = [c for d, c in ai.rolling_corr(self.S["NASDAQNQINTEL"], self.S["DGS10"], 20) if d >= D(2023, 10, 23)]
        self.assertEqual(v["days"], len(r))
        self.assertAlmostEqual(v["outside"], sum(abs(c) > ai.null_band(20) for c in r) / len(r) * 100, places=4)

    def test_every_item_computes_and_rebuilds_its_text(self):
        res = ai.compute(self.S, {}, NOW.date())
        for spec in ai.ITEMS:
            core = res[spec["key"]]
            self.assertIsInstance(core, dict, spec["key"])
            self.assertEqual(set(core["values"]), set(spec["values"]), spec["key"])
            self.assertEqual(set(core["lines"]), {ln["key"] for ln in spec["lines"]}, spec["key"])
            line, extra = ai.texts(spec["key"], core["values"], core["date"])
            self.assertTrue(line)


class NewItemsTest(unittest.TestCase):
    """고신용 장기 스프레드(hq_spread)와 긴 기간 주가-금리 상관(sb_long) — 2026-10-28."""

    def test_fast_rolling_corr_equals_pearson_everywhere(self):
        rnd = random.Random(3)
        days = bdays(D(2020, 1, 1), D(2024, 12, 31))
        px, y, p, r = [], [], 100.0, 2.0
        for d in days:
            dy = rnd.gauss(0, 0.05)
            p *= 1 + rnd.gauss(0, 0.01) + 0.05 * dy
            r += dy
            px.append((d, p))
            y.append((d, round(r, 2)))
        px[100] = (px[100][0], 0.0)                                            # 가격 0인 날도 같은 짝으로
        slow, fast = ai.rolling_corr(px, y, 252), ai.rolling_corr_fast(px, y, 252)
        self.assertEqual([d for d, _ in slow], [d for d, _ in fast])
        for (_, a), (_, b) in zip(slow, fast):
            self.assertAlmostEqual(a, b, places=9)

    def test_flat_window_gives_none_like_pearson(self):
        days = bdays(D(2020, 1, 1), D(2021, 6, 30))
        px = [(d, 100.0 + i) for i, d in enumerate(days)]
        y = [(d, 2.0) for d in days]                                         # 금리가 움직이지 않는다
        self.assertTrue(all(v is None for _, v in ai.rolling_corr_fast(px, y, 252)))

    def test_monthly_mean_skips_thin_months(self):
        s = [(D(2026, 1, k), float(k)) for k in range(1, 21)] + [(D(2026, 2, k), 1.0) for k in range(1, 6)]
        self.assertEqual(ai.monthly_mean(s), [(D(2026, 1, 1), 10.5)])          # 2월은 관측 5일 — 빈 달로 둔다

    def test_hq_spread_is_par_minus_monthly_mean_with_gap_months_blank(self):
        S = world()
        S["DGS30"] = [p for p in S["DGS30"] if not D(2020, 3, 1) <= p[0] <= D(2020, 6, 30)]   # 국채 공백 넉 달
        core = ai.calc_hq_spread(S)
        v = core["values"]
        t30 = dict(ai.monthly_mean(S["DGS30"]))
        hq = dict(S["HQMCB30YRP"])
        self.assertEqual(v["s30_date"], "2026-09-01")
        self.assertAlmostEqual(v["s30"], (hq[D(2026, 9, 1)] - t30[D(2026, 9, 1)]) * 100, places=3)
        self.assertAlmostEqual(v["s30_1y"], (hq[D(2025, 9, 1)] - t30[D(2025, 9, 1)]) * 100, places=3)
        hist = [(hq[m] - t30[m]) * 100 for m in hq if m in t30 and m >= ai.HQ_PCT_FROM]
        self.assertEqual(v["n30"], len(hist))
        self.assertAlmostEqual(v["le30"], sum(x <= v["s30"] + 1e-4 for x in hist) / len(hist) * 100, places=3)   # s30은 소수 넷째 자리
        pts = dict(map(tuple, core["lines"]["s30"]))
        self.assertIsNone(pts["2020-04-01"])                                  # 공백 달은 선을 끊는다
        self.assertIsNotNone(pts["2020-02-01"])

    def test_hq_spread_leaves_out_the_months_dgs30_was_discontinued(self):
        S = world()
        ms = months(D(2001, 1, 1), D(2007, 12, 1))
        S["DGS30"] = [(d, 5.0) for m in ms for d in bdays(m, m + datetime.timedelta(days=27))] + S["DGS30"]
        S["HQMCB30YRP"] = [(m, 6.0) for m in ms] + S["HQMCB30YRP"]
        pts = dict(map(tuple, ai.calc_hq_spread(S)["lines"]["s30"]))
        self.assertEqual(pts["2002-01-01"], 100.0)
        self.assertIsNone(pts["2002-02-01"])                                  # FRED 주석: 2002-02-18 발표 중단
        self.assertIsNone(pts["2006-02-01"])                                  # 2006-02-09 재개 — 그 달까지 뺀다
        self.assertEqual(pts["2006-03-01"], 100.0)

    def test_month_states_use_the_rule_functions_and_comparisons(self):
        ms = months(D(2020, 1, 1), D(2023, 12, 1))
        pce = [(m, 100 * 1.0025 ** i) for i, m in enumerate(ms)]
        pce[-1] = (pce[-1][0], pce[-13][1] * 1.03)                            # 마지막 달 전년비가 정확히 3.0%
        un = [(m, 4.0) for m in ms[:-3]] + [(m, 4.5) for m in ms[-3:]]       # 마지막 달 상승 폭이 정확히 0.5
        infl, unemp = ai.month_states({"PCEPILFE": pce, "UNRATE": un}, D(2020, 1, 1))
        last = ai._mkey(ms[-1])
        self.assertAlmostEqual(infl[last][0], ff.yoy(pce, same_month=True)["value"])
        self.assertFalse(infl[last][1])                                       # 3.0%는 '3% 초과'가 아니다(규칙 충족 쪽)
        self.assertAlmostEqual(unemp[last][0], ff.sahm_stats(un)["value"])
        self.assertTrue(unemp[last][1])                                       # 0.5는 '0.5 이상'(규칙 충족)
        self.assertTrue(infl[ai._mkey(ms[-2])][1])                            # 연 3.0% 넘는 증가(0.25%/월)

    def test_ranges_merge_consecutive_months_and_break_on_gaps(self):
        mk = ai._mkey(D(2020, 1, 1))
        flags = [(mk, True), (mk + 1, True), (mk + 2, False), (mk + 3, True), (mk + 5, True)]
        self.assertEqual(ai._ranges(flags), [["2020-01-01", "2020-02-29"], ["2020-04-01", "2020-04-30"],
                                             ["2020-06-01", "2020-06-30"]])

    def test_sb_long_cells_match_a_brute_force_and_carry_the_signs(self):
        S = long_world()
        core = ai.calc_sb_long(S)
        v = core["values"]
        infl, unemp = ai.month_states(S, D(1985, 1, 1))
        rho = ai.rolling_corr(S["NASDAQCOM"], S["DGS10"], 252)                  # 느린 길(ff.pearson)로 따로
        latest = lambda st, mk: st[max(k for k in st if k <= mk)]
        acc = {}
        for d, r in rho:
            mk = ai._mkey(d)
            if r is None or mk > max(infl) or mk > max(unemp):                 # 발표 전 달은 세지 않는다(자료 달 기준)
                continue
            i, u = latest(infl, mk)[1], latest(unemp, mk)[1]
            c = "B" if i and u else "I" if i else "U" if u else "N"
            e = "e1" if d.year <= 1997 else "e2" if d.year <= 2020 else "e3"
            for k in (e, "all"):
                acc.setdefault((k, c), []).append(r)
        for (e, c), rs in acc.items():
            self.assertEqual(v[f"d_{e}_{c}"], len(rs), (e, c))
            self.assertAlmostEqual(v[f"m_{e}_{c}"], sum(rs) / len(rs), places=4)
        self.assertEqual(sum(v[f"d_all_{c}"] for c in "IBUN"),
                         sum(1 for d, r in rho if r is not None and ai._mkey(d) <= min(max(infl), max(unemp))))
        self.assertLess(v["m_all_I"], -0.2)                                   # 합성 세계: 물가 달은 음(−)
        self.assertGreater(v["m_all_U"], 0.2)                                 # 실업률이 오르는 달은 양(+)
        self.assertEqual(v["r_e1_I"], 1)                                      # 1990~1994 한 덩어리
        self.assertEqual(v["first"], rho[next(i for i, (_, r) in enumerate(rho) if r is not None)][0].isoformat())
        on = sorted(mk for mk, (_, f) in infl.items() if f and mk >= ai._mkey(D(1990, 1, 1)))
        self.assertEqual(core["bands"]["infl"][0][0], ai._iso(ai._mday(on[0])))      # 전년비가 3%를 넘은 첫 달부터
        first_end = max(mk for mk in on if mk < ai._mkey(D(2000, 1, 1)))
        self.assertEqual(core["bands"]["infl"][0][1], ai._iso(ai._mday(first_end, True)))   # 성장이 늦춰진 뒤에도 전년비가 남는 달까지
        self.assertEqual(len(core["bands"]["infl"]), 2)                              # 1990년대 초 · 2022~23년
        self.assertEqual(core["lines"]["sp"][0][0][:4], "2017")              # S&P 500은 2016-10부터라 252일 뒤부터

    def test_bands_stop_at_the_last_data_month(self):
        S = long_world()
        S["PCEPILFE"] = S["PCEPILFE"][:-2]                                   # PCE가 두 달 늦다(2026-07까지)
        S["PCEPILFE"][-1] = (S["PCEPILFE"][-1][0], S["PCEPILFE"][-13][1] * 1.05)   # 마지막 달은 조건이 맞는다
        core = ai.calc_sb_long(S)
        self.assertEqual(core["bands"]["infl"][-1][1], "2026-07-31")          # 발표 전 8~10월로 늘리지 않는다
        for rs in core["bands"].values():
            self.assertTrue(all(r[1] <= "2026-09-30" for r in rs))
        un = [p for p in S["UNRATE"] if p[0] != D(2015, 6, 1)]                # 시리즈 안의 빠진 달은 잇는다
        S["UNRATE"] = un
        v = ai.calc_sb_long(S)["values"]
        self.assertGreater(v["d_all_N"] + v["d_all_U"] + v["d_all_I"] + v["d_all_B"], 0)

    def test_sb_long_table_and_text(self):
        S = long_world()
        core = ai.calc_sb_long(S)
        t = ai.table_of("sb_long", core["values"])
        self.assertEqual(t["columns"], ["시대"] + [name for _, name in ai.CELLS])
        self.assertEqual([r[0] for r in t["rows"]], [f"{core['values']['first'][:4]}~1997", "1998~2020", "2021~", "전체"])
        self.assertEqual(t["rows"][1][1], "—")                                 # 1998~2020에는 물가 조건인 날이 없다
        line, extra = ai.texts("sb_long", core["values"], core["date"])
        self.assertTrue(any("1998~2020년에는 근원 PCE" in e for e in extra))
        for word in FORBIDDEN_TEXT:
            for text in [line, *extra, t["caption"], *[c for r in t["rows"] for c in r], *t["columns"]]:
                self.assertNotIn(word, text, (word, text))

    def test_bands_go_into_the_chart_and_must_be_well_formed_to_carry(self):
        S = long_world()
        core = ai.calc_sb_long(S)
        it = {"ok": True, "stale": False, "error": None, "failed_since": None, **ai.present("sb_long", core, "2026-10-27")}
        self.assertEqual([b["key"] for b in it["chart"]["bands"]], ["infl", "unemp"])
        self.assertEqual(it["chart"]["bands"][0]["ranges"], core["bands"]["infl"])
        back = ai.core_of(json.loads(json.dumps(it)), "sb_long")
        self.assertEqual(back[0]["bands"], json.loads(json.dumps(core["bands"])))
        bad = json.loads(json.dumps(it))
        bad["chart"]["bands"][0]["ranges"][0] = ["2023-01-31", "2023-01-01"]   # 끝이 시작보다 이르다
        self.assertIsNone(ai.core_of(bad, "sb_long"))
        bad = json.loads(json.dumps(it))
        bad["chart"]["lines"][0]["points"][5][1] = 9876.54                      # 지수 수준 같은 값
        self.assertIsNone(ai.core_of(bad, "sb_long"))
        ok = json.loads(json.dumps(it))
        ok["values"]["pce"] = 4.5                                              # 물가 값은 범위 검사 밖(free)
        self.assertIsNotNone(ai.core_of(ok, "sb_long"))


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.out = os.path.join(self.tmp, "data")
        self.work = os.path.join(self.tmp, ".work")
        self.path = os.path.join(self.out, ai.FILE)
        self.S = world()

    def run_main(self, fred=None, now=NOW, extra=(), clock=None):
        fred = fred or FakeFred(self.S)
        buf = io.StringIO()
        kw = {"clock": clock} if clock else {}
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = ai.main(["--out", self.out, "--work", self.work, *extra], fred_load=fred, now=now, **kw)
        return code, buf.getvalue()

    def saved(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def test_first_run_writes_every_item(self):
        code, log = self.run_main()
        self.assertEqual(code, 0, log)
        js = self.saved()
        self.assertEqual(set(js), {"schema", "generated_at", "notice", "channels", "order", "items"})
        self.assertEqual(js["order"], [s["key"] for s in ai.ITEMS])
        for key, it in js["items"].items():
            self.assertTrue(it["ok"], key)
            self.assertEqual(it["retrieved"], "2026-10-27")
            if not ai.BY_KEY[key]["lines"]:                                       # 표만 싣는 칸(ai_b2)
                self.assertNotIn("chart", it, key)
                self.assertTrue(it["table"]["rows"], key)
                continue
            self.assertEqual(set(it["chart"]), SPEC_KEYS | ({"bands"} if ai.BY_KEY[key].get("bands") else set()))
            for ln in it["chart"]["lines"]:
                self.assertEqual(set(ln), LINE_KEYS)
                self.assertTrue(ln["points"], (key, ln["key"]))
            self.assertTrue(it["notices"])
            for src in it["sources"]:
                self.assertTrue(src["citation"].startswith(ai.SOURCES[src["series"]][0]))
                self.assertIn(f"[{src['series']}], retrieved from FRED", src["citation"])
                self.assertTrue(src["citation"].endswith("October 27, 2026."))
        self.assertEqual(js["items"]["corr60"]["date"], "2026-10-23")
        self.assertEqual(js["items"]["ict_share"]["date"], "2026-04-01")

    def test_restricted_index_levels_never_appear(self):
        self.run_main()
        js = self.saved()
        dump = json.dumps(js)
        for sid, start in LEVEL_START.items():
            for d, v in self.S[sid][::50] + self.S[sid][-5:]:
                for nd in (1, 2, 3, 4):
                    self.assertNotIn(f"{v:.{nd}f}", dump, (sid, d))
        for key in ("corr60", "corr20", "partial60"):
            it = js["items"][key]
            for ln in it["chart"]["lines"]:
                self.assertTrue(ln["derived"])
                self.assertTrue(all(p[1] is None or -1 <= p[1] <= 1 for p in ln["points"]), (key, ln["key"]))
            for name, x in it["values"].items():
                if isinstance(x, float) and name not in ("outside",):
                    self.assertLessEqual(abs(x), 1, (key, name))
            self.assertEqual(it["notices"], [ai.RESTRICTED_NOTICE])
        restricted = {s["series"] for it in js["items"].values() for s in it["sources"] if s["restricted"]}
        self.assertEqual(restricted, set(ai.RESTRICTED) & set(ai.SERIES))
        self.assertLessEqual(set(rp.RESTRICTED), set(ai.RESTRICTED))                # 공개본의 목록을 그대로 품는다

    def test_one_missing_series_only_stales_its_items(self):
        self.run_main()
        before = self.saved()["items"]
        code, log = self.run_main(fred=FakeFred(self.S, fail={"NASDAQNDXTMC"}), now=NOW + datetime.timedelta(days=1))
        self.assertEqual(code, 0, log)
        items = self.saved()["items"]
        for key in ("corr60", "partial60"):
            it = items[key]
            self.assertEqual((it["ok"], it["stale"], it["error"], it["failed_since"]),
                             (False, True, ai.REASONS["fetch"], "2026-10-28"))
            self.assertEqual(it["line"], before[key]["line"])                    # 문구는 숫자로 다시 만든다
            self.assertEqual(it["retrieved"], "2026-10-27")
        for key in ("corr20", "ict_share", "curve_30_10"):
            self.assertTrue(items[key]["ok"], key)
        self.assertIn("::warning::AI 투자 참고 corr60 받지 못함", log)
        self.assertNotIn("xyz-77", log)
        self.run_main(fred=FakeFred(self.S, fail={"NASDAQNDXTMC"}), now=NOW + datetime.timedelta(days=3))
        self.assertEqual(self.saved()["items"]["corr60"]["failed_since"], "2026-10-28")   # 못 받기 시작한 날을 지킨다

    def test_online_cache_fallback_counts_as_a_failure(self):
        self.run_main(fred=FakeFred(self.S, cache={"PROFCONS"}))
        it = self.saved()["items"]["office_cons"]
        self.assertEqual((it["ok"], it["stale"], it["error"]), (False, False, ai.REASONS["cache"]))
        self.assertNotIn("line", it)                                           # 직전 값이 없으면 숫자 없이

    def test_offline_reads_the_cache(self):
        cache = os.path.join(self.work, ai.CACHE)
        os.makedirs(cache)
        for sid, s in self.S.items():
            with open(os.path.join(cache, f"{sid}.csv"), "w", encoding="utf-8") as f:
                f.write("observation_date," + sid + "\n" + "".join(f"{d.isoformat()},{v}\n" for d, v in s))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), mock.patch.object(ai.urllib.request, "urlopen", side_effect=AssertionError("요청")):
            code = ai.main(["--out", self.out, "--work", self.work, "--offline"], now=NOW)
        self.assertEqual(code, 0, buf.getvalue())
        self.assertTrue(all(it["ok"] for it in self.saved()["items"].values()))

    def test_older_data_is_not_taken(self):
        self.run_main()
        short = dict(self.S, DGS30=[p for p in self.S["DGS30"] if p[0] <= D(2026, 9, 30)])
        self.run_main(fred=FakeFred(short), now=NOW + datetime.timedelta(days=1))
        it = self.saved()["items"]["curve_30_10"]
        self.assertEqual((it["ok"], it["stale"], it["error"], it["date"]), (False, True, ai.REASONS["older"], "2026-10-23"))

    def test_same_numbers_keep_the_file_and_the_retrieved_day(self):
        self.run_main()
        with open(self.path, "rb") as f:
            first = f.read()
        self.run_main(now=NOW + datetime.timedelta(days=1))
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), first)                                   # 생성 시각만 다르면 다시 쓰지 않는다

    def test_a_broken_previous_file_is_not_carried(self):
        self.run_main()
        js = self.saved()
        js["items"]["power"]["values"]["ppi"] = "4.2"                            # 숫자 자리의 글자
        js["items"]["financing"]["values"]["extra"] = 1                          # 정해 둔 것 밖의 키
        js["items"]["curve_30_10"]["chart"]["lines"][0]["points"][0][0] = "2026-W40-3"
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(js, f, ensure_ascii=False)
        self.run_main(fred=FakeFred(self.S, fail={"WPU0543", "BOGZ1FA105050005Q", "DGS30"}),
                      now=NOW + datetime.timedelta(days=1))
        items = self.saved()["items"]
        for key in ("power", "financing", "curve_30_10"):
            self.assertEqual((items[key]["ok"], items[key]["stale"]), (False, False), key)
            self.assertNotIn("line", items[key])

    def test_a_lagging_series_keeps_its_own_date(self):
        lag = dict(self.S, SP500=[p for p in self.S["SP500"] if p[0] <= D(2026, 10, 16)],
                   NASDAQNDXTMC=[p for p in self.S["NASDAQNDXTMC"] if p[0] <= D(2026, 10, 2)])
        self.run_main(fred=FakeFred(lag))
        it = self.saved()["items"]["corr60"]
        self.assertTrue(it["ok"])
        self.assertEqual((it["date"], it["values"]["sp_date"], it["values"]["ndx_date"]),
                         ("2026-10-23", "2026-10-16", "2026-10-02"))
        self.assertIn("S&P 500 ", it["line"])
        self.assertIn("(2026-10-16 기준)", it["line"])                            # 늦게 끝난 값을 칸 날짜의 값처럼 적지 않는다
        self.assertIn("(2026-10-02 기준)", it["line"])
        self.assertIn("(2026-10-02 기준)", self.saved()["items"]["partial60"]["line"])

    def test_one_series_ending_earlier_than_before_is_not_taken(self):
        self.run_main()
        short = dict(self.S, WPU0543=[p for p in self.S["WPU0543"] if p[0] <= D(2026, 5, 1)])
        self.run_main(fred=FakeFred(short), now=NOW + datetime.timedelta(days=1))
        it = self.saved()["items"]["power"]
        self.assertEqual((it["ok"], it["stale"], it["error"]), (False, True, ai.REASONS["older"]))
        self.assertEqual(it["values"]["ppi_date"], "2026-09-01")                 # 칸 날짜(CPI)는 그대로여도

    def test_carried_correlations_must_stay_within_minus_one_to_one(self):
        self.run_main()
        js = self.saved()
        js["items"]["corr60"]["chart"]["lines"][1]["points"][0][1] = 7351.37     # 지수 수준 같은 값이 섞여 들어온 직전 파일
        js["items"]["corr20"]["values"]["outside"] = 37.5                        # 비율(%)은 범위 밖이어도 된다
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(js, f, ensure_ascii=False)
        self.run_main(fred=FakeFred(self.S, fail={"SP500", "NASDAQNQINTEL"}), now=NOW + datetime.timedelta(days=1))
        items = self.saved()["items"]
        self.assertEqual((items["corr60"]["stale"], "line" in items["corr60"]), (False, False))
        self.assertTrue(items["corr20"]["stale"])
        self.assertNotIn("7351.37", json.dumps(self.saved()))

    def test_reference_lines_share_the_main_line_dates(self):
        self.run_main()
        for key, main_key, ref in (("corr20", "ai", "band_hi"), ("financing", "ratio", "median")):
            lines = {ln["key"]: ln["points"] for ln in self.saved()["items"][key]["chart"]["lines"]}
            self.assertEqual([p[0] for p in lines[ref]], [p[0] for p in lines[main_key]], key)

    def test_a_missing_month_breaks_the_line(self):
        self.run_main()
        pts = dict(map(tuple, self.saved()["items"]["power"]["chart"]["lines"][1]["points"]))
        self.assertIn("2025-10-01", pts)
        self.assertIsNone(pts["2025-10-01"])                                   # 빈 달을 곧은 선으로 잇지 않는다
        self.assertIsNotNone(pts["2025-09-01"])

    def test_new_items_refuse_a_series_that_ends_earlier_than_before(self):
        self.run_main()
        for sid, key, field in (("PCEPILFE", "sb_long", "pce_month"), ("UNRATE", "sb_long", "ur_month"),
                                ("HQMCB10YRP", "hq_spread", "s10_date")):
            before = self.saved()["items"][key]["values"][field]
            self.run_main(fred=FakeFred(dict(self.S, **{sid: self.S[sid][:-1]})), now=NOW + datetime.timedelta(days=1))
            it = self.saved()["items"][key]
            self.assertEqual((it["ok"], it["stale"], it["error"]), (False, True, ai.REASONS["older"]), sid)
            self.assertEqual(it["values"][field], before, sid)
            self.run_main(now=NOW + datetime.timedelta(days=2))                # 다음 날 다시 받으면 돌아온다
            self.assertTrue(self.saved()["items"][key]["ok"], sid)

    def test_budget_runs_out_without_waiting(self):
        t = [0.0]

        def clock():
            t[0] += 30.0                                                        # 요청마다 30초가 흐른 것처럼
            return t[0]
        fred = FakeFred(self.S)
        code, log = self.run_main(fred=fred, clock=clock)
        self.assertLess(len(fred.calls), len(ai.SERIES))                         # 남은 시간이 없으면 더 요청하지 않는다
        self.assertTrue(all(1 <= tmo <= ai.TIMEOUT for _, tmo in fred.calls))
        self.assertIn("::warning::", log)

    def test_nothing_fetched_exits_1(self):
        code, log = self.run_main(fred=FakeFred(self.S, fail=set(self.S)))
        self.assertEqual(code, 1, log)
        self.assertTrue(all(not it["ok"] for it in self.saved()["items"].values()))

    def test_the_write_is_atomic(self):
        self.run_main()
        with open(self.path, "rb") as f:
            before = f.read()
        with mock.patch.object(ai.os, "replace", side_effect=OSError("disk full")):
            code, log = self.run_main(fred=FakeFred(dict(self.S, DGS10=self.S["DGS10"][:-3], DGS30=self.S["DGS30"][:-3])),
                                      now=NOW + datetime.timedelta(days=1))
        self.assertEqual(code, 1, log)
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), before)
        self.assertEqual(os.listdir(self.out), [ai.FILE])
        self.assertIn("쓰지 못함", log)

    def test_every_string_is_fixed_text_without_banned_words(self):
        self.run_main(fred=FakeFred(self.S, fail={"SP500"}))
        self.run_main(now=NOW + datetime.timedelta(days=1))
        self.run_main(fred=FakeFred(self.S, fail={"GDP", "DGS10"}), now=NOW + datetime.timedelta(days=2))
        dump = json.dumps(self.saved(), ensure_ascii=False)
        for word in FORBIDDEN_TEXT:
            self.assertNotIn(word, dump, word)
        urls = {u.rstrip(".") for u in re.findall(r"https?://[^\s,;)\"]+", dump)}
        self.assertEqual(urls, {f"https://fred.stlouisfed.org/series/{sid}" for sid in ai.SERIES})
        self.assertNotIn("bad.invalid", dump)
        self.assertNotIn("xyz-77", dump)
        errors = {it["error"] for it in self.saved()["items"].values()} - {None}
        self.assertLessEqual(errors, set(ai.REASONS.values()))

    def test_static_text_avoids_banned_words(self):
        texts = [ai.NOTICE, ai.RESTRICTED_NOTICE, ai.COMPUTED_NOTICE, *ai.REASONS.values(), *[c[1] for c in ai.CHANNELS]]
        texts += [s[k] for s in ai.ITEMS for k in ("title", "note")] + [ln["label"] for s in ai.ITEMS for ln in s["lines"]]
        core = ai.compute(world(), {}, NOW.date())
        for spec in ai.ITEMS:
            line, extra = ai.texts(spec["key"], core[spec["key"]]["values"], core[spec["key"]]["date"])
            texts += [line, *extra]
        for t in texts:
            for word in FORBIDDEN_TEXT:
                self.assertNotIn(word, t, (word, t))


class B2Test(unittest.TestCase):
    """AI 고유 몫 b2(2026-10-30, 비공개 알림에서 옮김) — 회귀 산식, 해마다 표, 재배포 제한 지킴."""
    @staticmethod
    def b2_world(end=D(2026, 10, 23), seed=3, coef=None, noise=0.05):
        """S&P·AI·10년 일간 — Δ10년(bp) = b1·S&P(%) + b2·(AI − S&P)(%) + 잡음, 해마다 정해 둔 (b1, b2)."""
        coef = coef or {2024: (0.5, 0.0), 2025: (-2.0, 1.0), 2026: (-1.0, -0.5)}
        rnd = random.Random(seed)
        sp, aiv, y = LEVEL_START["SP500"], LEVEL_START["NASDAQNQINTEL"], 4.0
        S = {"SP500": [], "NASDAQNQINTEL": [], "DGS10": []}
        for d in bdays(D(2024, 6, 3), end):
            r_sp, rel = rnd.gauss(0, 1.0), rnd.gauss(0, 0.8)
            b1, b2 = coef[d.year]
            dy = b1 * r_sp + b2 * rel + rnd.gauss(0, noise)
            sp *= 1 + r_sp / 100
            aiv *= 1 + (r_sp + rel) / 100
            y += dy / 100
            S["SP500"].append((d, sp))
            S["NASDAQNQINTEL"].append((d, aiv))
            S["DGS10"].append((d, y))
        return S

    def test_ols_hc1_matches_the_closed_form_for_one_regressor(self):
        rnd = random.Random(5)
        x = [rnd.gauss(0, 1) for _ in range(80)]
        y = [0.3 + 1.7 * v + rnd.gauss(0, 0.5) * (1 + abs(v)) for v in x]
        fit = ai.ols(y, [[1.0, v] for v in x])
        n, mx, my = len(x), sum(x) / len(x), sum(y) / len(y)
        sxx = sum((v - mx) ** 2 for v in x)
        b = sum((u - mx) * (v - my) for u, v in zip(x, y)) / sxx
        e = [v - (my - b * mx) - b * u for u, v in zip(x, y)]
        var = n / (n - 2) * sum((u - mx) ** 2 * r * r for u, r in zip(x, e)) / sxx ** 2   # HC1
        self.assertAlmostEqual(fit["b"][1], b, places=10)
        self.assertAlmostEqual(fit["se"][1], math.sqrt(var), places=10)
        self.assertEqual(fit["n"], 80)

    def test_ols_refuses_short_or_singular_samples(self):
        x = [float(i % 7) for i in range(59)]
        self.assertIsNone(ai.ols([v * 2 for v in x], [[1.0, v] for v in x]))       # MIN_OLS(60) 미만
        x = [float(i % 7) for i in range(80)]
        self.assertIsNone(ai.ols(x, [[1.0, v, 2 * v] for v in x]))                 # 특이(같은 열 둘)
        self.assertIsNotNone(ai.ols([v + (i % 3) for i, v in enumerate(x)], [[1.0, v] for v in x]))

    def test_rows_pair_common_days_like_ai_corr_check(self):
        S = {"SP500": [(D(2024, 12, 30), 100.0), (D(2024, 12, 31), 0.0), (D(2025, 1, 2), 101.0), (D(2025, 1, 3), 102.01),
                       (D(2025, 1, 6), 100.99)],
             "NASDAQNQINTEL": [(D(2024, 12, 30), 50.0), (D(2024, 12, 31), 50.0), (D(2025, 1, 2), 51.0),
                               (D(2025, 1, 6), 51.51)],
             "DGS10": [(D(2024, 12, 30), 4.0), (D(2024, 12, 31), 4.1), (D(2025, 1, 2), 4.05), (D(2025, 1, 3), 4.0),
                       (D(2025, 1, 6), 4.2)]}
        rows = ai.b2_rows(S)
        # 12-31은 앞 날 가격이 0이라 건너뛰고(01-02 줄 없음), 01-03은 AI가 없어 공통 날짜가 아니다 → 01-02 → 01-06 한 줄
        self.assertEqual([r[0] for r in rows], [D(2025, 1, 6)])
        d, sp, a, dy = rows[0]
        self.assertAlmostEqual(sp, (100.99 / 101 - 1) * 100)
        self.assertAlmostEqual(a, (51.51 / 51 - 1) * 100)
        self.assertAlmostEqual(dy, (4.2 - 4.05) * 100)
        S["SP500"][1] = (D(2024, 12, 31), 99.0)
        rows = ai.b2_rows(S)
        self.assertEqual([r[0] for r in rows], [D(2025, 1, 2), D(2025, 1, 6)])     # 첫 줄은 그 앞 해의 날에서 시작한다
        self.assertEqual([r[0] for r in ai.b2_rows(S, since=D(2024, 1, 1))][0], D(2024, 12, 31))

    def test_recovers_the_coefficients_year_by_year(self):
        v = ai.calc_ai_b2(self.b2_world())
        ys = {y["year"]: y for y in v["values"]["years"]}
        self.assertEqual(sorted(ys), [2025, 2026])                                    # 2024는 표본 시작 앞
        for yr, (b1, b2) in ((2025, (-2.0, 1.0)), (2026, (-1.0, -0.5))):
            self.assertAlmostEqual(ys[yr]["b1"], b1, delta=0.02)
            self.assertAlmostEqual(ys[yr]["b2"], b2, delta=0.02)
            self.assertGreater(abs(ys[yr]["t2"]), 50)
        self.assertEqual((ys[2025]["from"], ys[2025]["to"]), ("2025-01-01", "2025-12-31"))
        self.assertEqual((ys[2026]["from"], ys[2026]["to"], v["date"]), ("2026-01-01", "2026-10-23", "2026-10-23"))
        self.assertEqual(ys[2025]["n"], len(bdays(D(2025, 1, 1), D(2025, 12, 31))))
        self.assertEqual(set(ys[2025]), set(ai.B2_KEYS))
        self.assertEqual(v["lines"], {})
        # 해마다 따로 맞춘다 — 묶으면 다른 값이 나오는 세계에서 각 해의 값이 그해 기울기다
        rows = ai.b2_rows(self.b2_world())
        pooled = ai.ols([r[3] for r in rows], [[1.0, r[1], r[2] - r[1]] for r in rows])
        self.assertGreater(abs(pooled["b"][2] - ys[2025]["b2"]), 0.3)

    def test_a_short_year_is_left_out_and_none_at_all_fails(self):
        v = ai.calc_ai_b2(self.b2_world(end=D(2026, 3, 20)))                           # 2026은 57일(MIN_OLS 60 미만)
        self.assertEqual([y["year"] for y in v["values"]["years"]], [2025])
        self.assertEqual(v["date"], "2026-03-20")                                       # 칸 날짜는 마지막 관측
        with self.assertRaises(ai.ItemError):
            ai.calc_ai_b2(self.b2_world(end=D(2025, 3, 20)))

    def test_table_and_text(self):
        core = ai.calc_ai_b2(self.b2_world())
        line, extra = ai.texts("ai_b2", core["values"], core["date"])
        self.assertIn("2025 +1.00bp", line)
        self.assertIn("2026(~10-23) -0.50bp", line)
        self.assertIn("측정 기록, 예측 아님", line)
        self.assertIn("2025 -2.00bp", extra[0])
        t = ai.table_of("ai_b2", core["values"])
        self.assertEqual(len(t["columns"]), 7)
        self.assertEqual([r[0] for r in t["rows"]], ["2025", "2026"])
        self.assertEqual(t["rows"][1][1], "-0.50")
        self.assertEqual(t["rows"][1][6], "2026-01-01 ~ 2026-10-23")

    def test_coefficient_guard(self):
        good = [{"year": 2025, "b1": -2.0, "t1": -5.1, "b2": 0.9, "t2": 2.6, "n": 250, "from": "2025-01-02",
                 "to": "2025-12-31"},
                {"year": 2026, "b1": -2.5, "t1": None, "b2": 0.5, "t2": 2.5, "n": 205, "from": "2026-01-02",
                 "to": "2026-10-23"}]
        self.assertTrue(ai.coef_rows_ok(good))
        bad = [lambda r: r[0].update(b2=7351.37),                      # 지수 수준 같은 값
               lambda r: r[0].update(sp_ret=0.42),                     # 정해 둔 칸 밖(수익률 열)
               lambda r: r[1].pop("t2"),
               lambda r: r[0].update(t1=500.0),
               lambda r: r[0].update(n=12),
               lambda r: r[0].update(n=400),
               lambda r: r[0].update(b1="0.5"),
               lambda r: r[1].update(year=2025),                       # 같은 해 둘
               lambda r: r[0].update(to="2026-01-02"),                 # 그해 밖
               lambda r: r[0].update(year=True),
               lambda r: r.append([1, 2, 3]),
               lambda r: r.clear()]
        for i, f in enumerate(bad):
            rows = json.loads(json.dumps(good))
            f(rows)
            self.assertFalse(ai.coef_rows_ok(rows), i)
        self.assertFalse(ai.coef_rows_ok({"years": good}))
        self.assertEqual(ai.BY_KEY["ai_b2"]["values"], {"years": "coef_rows"})


class B2MainTest(unittest.TestCase):
    """b2·사모대출을 실은 산출물 — 지수 값·수익률 비노출, 직전 파일·새 값의 지킴, 인용."""
    setUp = MainTest.setUp
    run_main = MainTest.run_main
    saved = MainTest.saved

    def test_no_index_value_or_return_is_written(self):
        self.run_main()
        js = self.saved()
        dump = json.dumps(js)
        it = js["items"]["ai_b2"]
        self.assertEqual(set(it["values"]), {"years"})
        self.assertTrue(it["values"]["years"])
        self.assertTrue(all(set(y) == set(ai.B2_KEYS) for y in it["values"]["years"]))
        self.assertEqual(it["notices"], [ai.COEF_NOTICE])
        self.assertEqual({s["series"]: s["licence"] for s in it["sources"]},
                         {"SP500": "restricted", "NASDAQNQINTEL": "restricted", "DGS10": "public-domain"})
        for d, sp, a, dy in ai.b2_rows(self.S)[-40:]:
            for x in (sp, a):
                if abs(x) >= 0.01:
                    self.assertNotIn(f"{x:.4f}", dump, d)                       # 일간 수익률(%)
        for sid in ("SP500", "NASDAQNQINTEL"):
            for d, v in self.S[sid][-60:]:
                for nd in (1, 2, 3, 4):
                    self.assertNotIn(f"{v:.{nd}f}", dump, (sid, d))

    def test_a_carried_b2_with_an_index_value_or_extra_column_is_dropped(self):
        for k, v in (("b2", 7351.37), ("sp_ret", 0.4242)):
            self.run_main()
            js = self.saved()
            js["items"]["ai_b2"]["values"]["years"][0][k] = v
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(js, f, ensure_ascii=False)
            self.run_main(fred=FakeFred(self.S, fail={"SP500"}), now=NOW + datetime.timedelta(days=1))
            it = self.saved()["items"]["ai_b2"]
            self.assertEqual((it["ok"], it["stale"], "line" in it, "table" in it), (False, False, False, False), k)
            self.assertNotIn(str(v), json.dumps(self.saved()))
            os.remove(self.path)
        self.run_main()
        self.run_main(fred=FakeFred(self.S, fail={"SP500"}), now=NOW + datetime.timedelta(days=1))
        it = self.saved()["items"]["ai_b2"]                                             # 온전한 직전 값은 이어 싣는다
        self.assertEqual((it["ok"], it["stale"], it["failed_since"]), (False, True, "2026-10-28"))
        self.assertTrue(it["table"]["rows"])

    def test_fresh_values_pass_the_same_guard(self):
        level = {"date": "2026-10-23", "lines": {},
                 "values": {"years": [{"year": 2026, "b1": 7351.37, "t1": 1.0, "b2": 0.5, "t2": 2.0, "n": 200,
                                       "from": "2026-01-02", "to": "2026-10-23"}]}}
        with mock.patch.dict(ai.BY_KEY["ai_b2"], {"calc": lambda S: level}), \
                mock.patch.dict(ai.BY_KEY["corr20"], {"calc": lambda S: dict(ai.calc_corr20(S), values=dict(
                    ai.calc_corr20(S)["values"], ai=1234.56))}):
            self.run_main()
        items = self.saved()["items"]
        for key in ("ai_b2", "corr20"):
            self.assertEqual((items[key]["ok"], items[key]["error"]), (False, ai.REASONS["format"]), key)
            self.assertNotIn("line", items[key])
        self.assertNotIn("7351.37", json.dumps(self.saved()))
        self.assertNotIn("1234.56", json.dumps(self.saved()))
        self.assertTrue(items["corr60"]["ok"])

    def test_private_credit_cites_z1_and_says_the_licence(self):
        self.run_main()
        it = self.saved()["items"]["private_credit"]
        self.assertTrue(it["ok"])
        self.assertEqual(it["channel"], "finance")
        self.assertEqual([s["series"] for s in it["sources"]], list(ai.PC.values()))
        for src in it["sources"]:
            want = "public-domain" if src["series"] == "BCNSDODNS" else ai.UNLABELED
            self.assertEqual(src["licence"], want, src["series"])
            self.assertFalse(src["restricted"])
            self.assertTrue(src["citation"].startswith(
                "Board of Governors of the Federal Reserve System (US), Financial Accounts of the United States (Z.1), "))
            self.assertIn(f"{ai.SOURCES[src['series']][1]} [{src['series']}], retrieved from FRED, Federal Reserve Bank "
                          f"of St. Louis; https://fred.stlouisfed.org/series/{src['series']}, October 27, 2026.",
                          src["citation"])
        self.assertEqual(it["notices"], [ai.COMPUTED_NOTICE, ai.Z1_NOTICE])
        self.assertEqual({sid for sid, lic in ai.LICENCE.items() if lic == ai.UNLABELED},
                         set(ai.PC.values()) - {"BCNSDODNS"})
        self.assertEqual(set(ai.LICENCE), set(ai.SERIES))
        fin = self.saved()["items"]["financing"]
        self.assertEqual(fin["notices"], [ai.COMPUTED_NOTICE])
        self.assertNotIn("Z.1), ", fin["sources"][0]["citation"])                     # 다른 Z.1 칸의 인용은 그대로
        self.assertEqual(ai.SERIES[-len(ai.PC):], list(ai.PC.values()))                # 수신 시간이 모자라면 끝부터 빠진다

    def test_private_credit_fails_alone_and_refuses_an_earlier_quarter(self):
        self.run_main()
        code, log = self.run_main(fred=FakeFred(self.S, fail={ai.PC["dry"]}), now=NOW + datetime.timedelta(days=1))
        self.assertEqual(code, 0, log)
        items = self.saved()["items"]
        self.assertEqual((items["private_credit"]["stale"], items["private_credit"]["failed_since"]), (True, "2026-10-28"))
        self.assertTrue(all(it["ok"] for k, it in items.items() if k != "private_credit"))
        short = dict(self.S, **{ai.PC["nfc"]: self.S[ai.PC["nfc"]][:-1]})
        self.run_main(fred=FakeFred(short), now=NOW + datetime.timedelta(days=2))
        it = self.saved()["items"]["private_credit"]
        self.assertEqual((it["ok"], it["error"], it["date"]), (False, ai.REASONS["older"], "2026-04-01"))


class PrivateCreditTest(unittest.TestCase):
    """사모대출(연준 Z.1) — 손으로 셀 수 있는 곧은 선 자료(z1_world)."""
    def test_values_by_hand(self):
        S = z1_world()
        v = ai.calc_private_credit(S)
        i = len(quarters(D(2010, 1, 1), D(2026, 4, 1))) - 1                              # 2026Q2의 차례
        tot, tot0 = 400000 + 15000 * i, 400000 + 15000 * (i - 4)
        self.assertEqual(v["date"], "2026-04-01")
        w = v["values"]
        self.assertAlmostEqual(w["total_tn"], round(tot / 1e6, 4))
        self.assertAlmostEqual(w["total_yoy"], round((tot / tot0 - 1) * 100, 4))
        self.assertAlmostEqual(w["share"], round((100000 + 5000 * i) / (9000000 + 40000 * i) * 100, 4))
        self.assertAlmostEqual(w["share_1y"], round((100000 + 5000 * (i - 4)) / (9000000 + 40000 * (i - 4)) * 100, 4))
        self.assertAlmostEqual(w["pdf_lev"], round((200000 + 6000 * i) / (600000 + 9000 * i) * 100, 4))
        self.assertAlmostEqual(w["bdc_lev_1y"], round((80000 + 3000 * (i - 4)) / (200000 + 4000 * (i - 4)) * 100, 4))
        bank, bank0 = 80000 + 3000 * i, 80000 + 3000 * (i - 4)
        self.assertAlmostEqual(w["bank_bn"], round(bank / 1e3, 4))
        self.assertAlmostEqual(w["bank_yoy"], round((bank / bank0 - 1) * 100, 4))
        self.assertAlmostEqual(w["dry_bn"], round((100000 + 3500 * i) / 1e3, 4))
        self.assertEqual(w["from"], "2012-10-01")                                        # 잔액이 0이 아닌 첫 분기
        pts = v["lines"]["share"]
        self.assertEqual((pts[0][0], pts[-1][0]), ("2012-10-01", "2026-04-01"))
        self.assertAlmostEqual(pts[-1][1], round(w["share"], 2))

    def test_last_quarter_all_ten_share_and_exact_year_ago(self):
        S = z1_world()
        pc = ai.PC
        S[pc["pdf_bank"]] = S[pc["pdf_bank"]][:-1]                                      # 한 줄이 한 분기 늦다
        S[pc["dry"]] = [(d, x) for d, x in S[pc["dry"]] if d != D(2025, 1, 1)]           # 1년 전 분기가 빠졌다
        v = ai.calc_private_credit(S)
        self.assertEqual(v["date"], "2026-01-01")
        self.assertIsNone(v["values"]["dry_yoy"])                                        # 다른 분기로 대신하지 않는다
        self.assertIsNotNone(v["values"]["bank_yoy"])
        line, _ = ai.texts("private_credit", v["values"], v["date"])
        self.assertIn("2026Q1 잔액", line)
        self.assertIn("미소진 약정", line)
        self.assertIn("(전년비 —)", line)
        S[pc["total"]] = []
        with self.assertRaises(ai.ItemError):
            ai.calc_private_credit(S)

    def test_eok_switches_to_jo_on_the_rounded_value(self):
        self.assertEqual(ai._eok(325.1), "3,251억 달러")
        self.assertEqual(ai._eok(999.94), "9,999억 달러")
        self.assertEqual(ai._eok(999.96), "1.00조 달러")
        self.assertEqual(ai._eok(1200.0), "1.20조 달러")
        self.assertEqual(ai._eok(None), "—")


class FetchTest(unittest.TestCase):
    class Drip:
        """한 번에 몇 바이트씩만 흘려보내는 응답 — 읽을 때마다 시계가 10초씩 간다."""
        def __init__(self, clock, n=50):
            self.clock, self.n = clock, n

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read1(self, size):
            self.clock.t += 10
            self.n -= 1
            return b"x" * 10 if self.n > 0 else b""

    class Clock:
        def __init__(self):
            self.t = 0.0

        def __call__(self):
            return self.t

    def test_a_slow_dripping_response_stops_at_the_deadline(self):
        clock = self.Clock()
        opener = lambda url, timeout: self.Drip(clock)
        with self.assertRaises(TimeoutError):
            ai.fetch_csv("DGS30", deadline=60, clock=clock, opener=opener)
        self.assertLessEqual(clock.t, 70)

    def test_online_reads_never_fall_back_to_the_cache(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        with open(os.path.join(tmp, "DGS30.csv"), "w", encoding="utf-8") as f:
            f.write("observation_date,DGS30\n2020-01-02,2.0\n")
        def broken(url, timeout):
            raise OSError("down")
        with self.assertRaises(OSError):
            ai.load_series("DGS30", tmp, False, deadline=1e9, opener=broken)
        series, src = ai.load_series("DGS30", tmp, True, deadline=0)
        self.assertEqual((series, src), ([(D(2020, 1, 2), 2.0)], "cache"))

    def test_the_fetched_text_is_cached_for_offline_runs(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)

        class Body(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        opener = lambda url, timeout: Body(b"observation_date,DGS30\n2026-10-23,4.9\n")
        series, src = ai.load_series("DGS30", tmp, False, deadline=1e12, opener=opener)
        self.assertEqual((series, src), ([(D(2026, 10, 23), 4.9)], "net"))
        self.assertEqual(ai.load_series("DGS30", tmp, True, deadline=0)[0], series)


class StaticTest(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
            return f.read()

    def test_workflow_fetches_without_failing_the_run(self):
        wf = self.read(".github", "workflows", "daily.yml")
        step = wf[wf.index("id: ai_invest"):]
        self.assertIn("continue-on-error: true", step[:200])
        self.assertIn("timeout-minutes: 2", step[:200])
        job = wf[wf.index("\n  update:"):wf.index("\n  deploy:")]
        self.assertIn("timeout-minutes: 30", job[:300])                          # 참고 단계 제한의 합이 일을 넘기지 않게
        self.assertIn("python scripts/ai_invest_fetch.py", step[:300])
        self.assertLess(wf.index("id: ai_invest"), wf.index("공개 전 검사(새 산출물 포함)"))
        self.assertLess(wf.index("id: ai_invest"), wf.index("git add data"))
        alert = wf[wf.index("\n  alert:"):]
        self.assertNotIn("ai_invest", alert)                                    # 실패해도 알림을 띄우지 않는다

    def test_ai_alias_matches_only_whole_words(self):
        page = self.read("site", "index.html")
        views = page[page.index("const VIEWS = ["):page.index("function go(")]
        self.assertNotIn('"ai"', views)                                          # 앞부분·포함 검색에 끼지 않는다('a' → 전체)
        self.assertIn('["ai", "ai 투자", "인공지능", "데이터센터"].includes(q) ? ["ai"]', page)

    def test_teaser_shows_the_first_item_of_each_channel(self):
        js = self.read("site", "ai_invest.js")
        teaser = re.findall(r'"(\w+)"', js[js.index("const TEASER = ["):].split("]")[0])
        firsts = []
        for spec in ai.ITEMS:
            if spec["channel"] not in [ai.BY_KEY[k]["channel"] for k in firsts]:
                firsts.append(spec["key"])
        self.assertEqual(teaser, firsts)

    def test_page_reads_the_file_and_draws_the_block(self):
        page = self.read("site", "index.html")
        self.assertIn('getJson("data/ai_invest.json")', page)
        self.assertIn('<script src="ai_invest.js"></script>', page)
        self.assertIn('<a href="data/ai_invest.json">', page)
        self.assertIn('<section id="ai-wrap" hidden', page)
        self.assertIn('<section id="ai-teaser" hidden', page)
        self.assertIn('href="#ai" data-view="ai"', page)
        self.assertIn('"sources", "ai"]', page)                                 # 알려진 화면

    def test_screen_order_matches_the_file(self):
        js = self.read("site", "ai_invest.js")
        keys = re.findall(r'\["(\w+)"(?:, "\w+")*\]\]', js)
        groups = re.findall(r'\[\s*"(\w+)", "[^"]+",(?:\s|\S)*?\[([^\]]*)\]\]', js)
        order = [k for _, ks in groups for k in re.findall(r'"(\w+)"', ks)]
        self.assertEqual(order, [s["key"] for s in ai.ITEMS])
        self.assertEqual([g for g, _ in groups], [c[0] for c in ai.CHANNELS])
        self.assertTrue(keys)

    def test_screen_script_writes_text_only_and_avoids_banned_words(self):
        js = self.read("site", "ai_invest.js")
        self.assertIn("function table(t)", js)
        self.assertIn("table(it.table)", js)
        charts = self.read("site", "charts.js")
        self.assertIn("function parseBands(spec)", charts)
        self.assertIn("tableView(lines, unit, bands,", charts)                    # 띠 기간도 표로 읽힌다(넷째 = 값 글자, format을 준 그래프만)
        page = self.read("site", "index.html")
        guide = page[page.index("const GUIDE = {"):page.index("function tpFlowFigure()")]
        self.assertIn("stock_bond_corr: {", guide)
        self.assertIn('el("a", { href: "#ai" }', guide)
        for word in FORBIDDEN_TEXT:
            block = guide[guide.index("stock_bond_corr: {"):]
        block = block[:block.index("\n};")]
        for word in FORBIDDEN_TEXT:
            self.assertNotIn(word, block, word)
        for tok in ("innerHTML", "outerHTML", "insertAdjacentHTML", "createElement", "fetch(", "eval("):
            self.assertNotIn(tok, js)
        body = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        for word in FORBIDDEN_TEXT:
            self.assertNotIn(word, body, word)
        page = self.read("site", "index.html")
        for sid in ("ai-teaser", "ai-wrap"):
            block = page[page.index(f'<section id="{sid}"'):]
            block = block[:block.index("</section>")].replace("전체 보기 →", "")   # 이동 링크의 화살표(한국 시장 요약과 같은 꼴)
            for word in FORBIDDEN_TEXT:
                self.assertNotIn(word, block, word)
        css = self.read("site", "dashboard.css")
        self.assertRegex(css, r"\.ai-item p \{[^}]*overflow-wrap: anywhere")       # 390px에서 숫자 줄이 넘치지 않게


if __name__ == "__main__":
    unittest.main(verbosity=1)
