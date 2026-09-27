#!/usr/bin/env python3
"""레짐 점검(fred_fetch · regime_rules · regime_check) 단위 테스트 — stdlib unittest.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — FRED는 합성 CSV 캐시로 대체하고 urlopen은 몽키패치한다.
"""
import os, sys, json, math, datetime, tempfile, unittest, shutil, subprocess

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import fred_fetch as ff
import regime_rules as rr
import regime_check as rck

TODAY = datetime.date(2026, 9, 22)
D = datetime.date


def monthly(start, values):
    """start 달부터 매월 1일 시계열."""
    out, y, m = [], start.year, start.month
    for v in values:
        out.append((D(y, m, 1), v))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def daily(end, values):
    """end에서 거꾸로 영업일(월~금) 시계열. values는 오래된 것부터."""
    days, d = [], end
    while len(days) < len(values):
        if d.weekday() < 5:
            days.append(d)
        d -= datetime.timedelta(days=1)
    days.reverse()
    return list(zip(days, values))


def weekly(end, values, step=7):
    n = len(values)
    return [(end - datetime.timedelta(days=step * (n - 1 - i)), v) for i, v in enumerate(values)]


class ParseAndLoadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_parse_drops_missing_and_parses_dates(self):
        # 결측은 '.'(일간)일 수도, 빈 값(CPILFESL 2025-10-01 실제 사례)일 수도 있다
        s = ff.parse_csv("observation_date,DGS10\n2026-01-02,4.5\n2026-01-05,.\n2026-01-06,4.6\n2026-01-07,\n")
        self.assertEqual(s, [(D(2026, 1, 2), 4.5), (D(2026, 1, 6), 4.6)])

    def _put(self, name, text):
        with open(os.path.join(self.tmp, name), "w", encoding="utf-8") as f:
            f.write(text)

    def test_offline_uses_cache_and_raises_without(self):
        self._put("X.csv", "observation_date,X\n2026-01-01,1\n")
        s, src = ff.load("X", self.tmp, offline=True)
        self.assertEqual((s, src), ([(D(2026, 1, 1), 1.0)], "cache"))
        with self.assertRaises(RuntimeError):
            ff.load("Y", self.tmp, offline=True)

    def test_network_failure_falls_back_to_cache(self):
        self._put("Z.csv", "observation_date,Z\n2026-01-01,2\n")
        orig = ff.urlopen_text
        ff.urlopen_text = lambda url, timeout: (_ for _ in ()).throw(OSError("down"))
        try:
            s, src = ff.load("Z", self.tmp)
        finally:
            ff.urlopen_text = orig
        self.assertEqual(src, "cache")
        self.assertEqual(s[0][1], 2.0)

    def test_network_success_writes_cache(self):
        orig = ff.urlopen_text
        ff.urlopen_text = lambda url, timeout: "observation_date,W\n2026-02-01,7\n"
        try:
            s, src = ff.load("W", self.tmp)
        finally:
            ff.urlopen_text = orig
        self.assertEqual(src, "net")
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "W.csv")))


class SeriesMathTest(unittest.TestCase):
    def test_yoy_monthly(self):
        s = monthly(D(2025, 1, 1), [100 + i for i in range(20)])   # 2025-01 .. 2026-08
        r = ff.yoy(s)
        self.assertEqual(r["asof"], D(2026, 8, 1))
        self.assertEqual(r["base_date"], D(2025, 8, 1))
        self.assertAlmostEqual(r["value"], (119 / 107 - 1) * 100)

    def test_yoy_none_when_short(self):
        self.assertIsNone(ff.yoy(monthly(D(2026, 1, 1), [1, 2, 3])))

    def test_yoy_same_month_rejects_missing_base_month(self):
        # 2025-08 결측: 느슨한 yoy는 2025-07을 기준으로 13개월 변화를 내지만, same_month는 None
        s = [r for r in monthly(D(2025, 1, 1), [100 + i for i in range(20)]) if r[0] != D(2025, 8, 1)]
        loose = ff.yoy(s)
        self.assertEqual(loose["base_date"], D(2025, 7, 1))
        self.assertIsNone(ff.yoy(s, same_month=True))
        full = monthly(D(2025, 1, 1), [100 + i for i in range(20)])
        self.assertAlmostEqual(ff.yoy(full, same_month=True)["value"], (119 / 107 - 1) * 100)

    def test_change_days_and_pct(self):
        s = daily(D(2026, 9, 18), [4.0 + 0.01 * i for i in range(120)])
        c = ff.change_days(s, 91)
        self.assertEqual(c["asof"], D(2026, 9, 18))
        self.assertLessEqual(c["base_date"], D(2026, 9, 18) - datetime.timedelta(days=91))
        self.assertGreater(c["delta"], 0)
        p = ff.pct_change_days(s, 91)
        self.assertGreater(p["value"], 0)

    def test_rolling_corr_signs(self):
        rets = [math.sin(i / 3.0) for i in range(100)]
        px, y_up, y_dn = [100.0], [4.0], [4.0]
        for r in rets:
            px.append(px[-1] * (1 + r / 100))
            y_up.append(y_up[-1] + r / 100)
            y_dn.append(y_dn[-1] - r / 100)
        sp = daily(D(2026, 9, 18), px)
        a = ff.corr_summary(sp, daily(D(2026, 9, 18), y_up), n=60)
        b = ff.corr_summary(sp, daily(D(2026, 9, 18), y_dn), n=60)
        self.assertAlmostEqual(a["value"], 1.0, places=6)
        self.assertAlmostEqual(b["value"], -1.0, places=6)
        self.assertEqual(a["asof"], D(2026, 9, 18))
        self.assertEqual(a["run_days"], 41)        # 수익률 100개 → 60일 창 41개 전부 같은 부호
        self.assertEqual(a["sign"], "+")

    def test_rolling_corr_none_when_short(self):
        sp = daily(D(2026, 9, 18), [100 + i for i in range(30)])
        y = daily(D(2026, 9, 18), [4 + 0.01 * i for i in range(30)])
        self.assertIsNone(ff.corr_summary(sp, y, n=60))

    def test_missing_months(self):
        s = monthly(D(2025, 6, 1), [1, 2, 3, 4]) + monthly(D(2025, 11, 1), [5, 6])   # 2025-10 결측
        self.assertEqual(ff.missing_months(s), ["2025-10"])
        self.assertEqual(ff.missing_months(monthly(D(2026, 1, 1), [1, 2, 3])), [])

    def test_step_excluded_yoy(self):
        vals = [1000 + 6 * i for i in range(60)]
        vals = [v + (236 if i >= 30 else 0) for i, v in enumerate(vals)]   # 30번째 주에 +236 계단
        s = weekly(D(2026, 9, 9), vals)
        r = ff.step_excluded_yoy(s, step=40)
        self.assertEqual(len(r["excluded"]), 1)
        self.assertEqual(r["excluded"][0][1], 236 + 6)
        base = r["base_value"]
        self.assertEqual(r["base_date"], D(2026, 9, 9) - datetime.timedelta(days=364))
        self.assertAlmostEqual(r["value"], (6 * 51) / base * 100)      # 52주 증분 중 계단 주 1개 제외
        self.assertGreater(r["raw_value"], r["value"])

    def test_percentile_since(self):
        s = monthly(D(1989, 1, 1), list(range(100)))
        self.assertAlmostEqual(ff.percentile(s, 10, since=D(1990, 1, 1)), 0.0, places=6)   # 1990-01은 값 12부터
        self.assertAlmostEqual(ff.percentile(s, 99, since=D(1990, 1, 1)), 1.0)

    def test_weekly_last_obs_per_week(self):
        s = daily(D(2026, 9, 18), list(range(10)))   # 2026-09-07(월)~09-18(금)
        w = ff.weekly_last(s)
        self.assertEqual([d for d, _ in w], [D(2026, 9, 11), D(2026, 9, 18)])
        self.assertEqual([v for _, v in w], [4, 9])

    def test_weekly_last_before_drops_incomplete_week(self):
        s = daily(D(2026, 9, 21), list(range(11)))   # 09-07(월)~09-21(월): 마지막 주는 월요일 하루
        w = ff.weekly_last(s, before=D(2026, 9, 21))
        self.assertEqual([d for d, _ in w], [D(2026, 9, 11), D(2026, 9, 18)])

    def test_freshness_days(self):
        s = monthly(D(2026, 1, 1), [1, 2, 3])
        self.assertEqual(ff.freshness_days(s, D(2026, 3, 31)), 30)


class RulesTest(unittest.TestCase):
    def test_regime_quadrants(self):
        self.assertEqual(rr.classify_regime(5.0, 30.0, "B")[0], "A")
        self.assertEqual(rr.classify_regime(5.0, -30.0, "A")[0], "C")
        self.assertEqual(rr.classify_regime(-5.0, 30.0, "A")[0], "A′")
        self.assertEqual(rr.classify_regime(-5.0, -30.0, "A")[0], "B")

    def test_regime_buffer_keeps_previous(self):
        r, note = rr.classify_regime(1.5, 30.0, "A")
        self.assertEqual(r, "A")
        self.assertIn("완충", note)
        r, note = rr.classify_regime(5.0, 8.0, None)
        self.assertIsNone(r)
        self.assertIn("직전", note)
        self.assertEqual(rr.classify_regime(None, 30.0, "A")[0], None)

    def test_transition_t4_three_negative_weeks(self):
        sp = weekly(D(2026, 9, 18), [100, 101, 99, 98, 97])       # 마지막 3주 연속 하락
        y = weekly(D(2026, 9, 18), [4.0, 4.1, 4.05, 4.0, 3.9])   # 마지막 3주 연속 하락
        t = rr.transition_triggers(sp_weekly=sp, y10_weekly=y, ig_weekly=None)
        self.assertTrue(t["t4"])
        self.assertIsNone(t["t2"])
        self.assertEqual(t["auto_on"], 1)
        y2 = weekly(D(2026, 9, 18), [4.0, 4.1, 4.05, 4.2, 3.9])
        self.assertFalse(rr.transition_triggers(sp_weekly=sp, y10_weekly=y2, ig_weekly=None)["t4"])

    def test_transition_aligns_weeks_when_series_end_on_different_days(self):
        # SP500만 다음 주 월요일 관측이 하나 더 있는 경우(FRED 공표 시차): 같은 ISO 주끼리 비교해야 한다
        sp = weekly(D(2026, 9, 18), [100, 101, 99, 98, 97]) + [(D(2026, 9, 21), 99.5)]
        y = weekly(D(2026, 9, 18), [4.0, 4.1, 4.05, 4.0, 3.9])
        self.assertTrue(rr.transition_triggers(sp_weekly=sp, y10_weekly=y, ig_weekly=None)["t4"])

    def test_transition_t2_widening_or_13w_high(self):
        ig = weekly(D(2026, 9, 18), [0.8] * 10 + [0.81, 0.82, 0.83, 0.84])   # 4주 연속 확대
        t = rr.transition_triggers(sp_weekly=None, y10_weekly=None, ig_weekly=ig)
        self.assertTrue(t["t2"])
        ig2 = weekly(D(2026, 9, 18), [0.9] + [0.8] * 12 + [0.85])            # 13주 고점 아님, 연속도 아님
        self.assertFalse(rr.transition_triggers(sp_weekly=None, y10_weekly=None, ig_weekly=ig2)["t2"])
        ig3 = weekly(D(2026, 9, 18), [0.8] * 13 + [0.95])                    # 13주 고점 경신
        self.assertTrue(rr.transition_triggers(sp_weekly=None, y10_weekly=None, ig_weekly=ig3)["t2"])

    def _ind(self, **kw):
        base = {"ci_yoy": 9.8, "ci_valid": True, "ngdp_yoy": 6.6, "ndfi_yoy": 18.6, "ndfi_share": 14.5,
                "hy_oas": 2.68, "baa10y": 1.44, "baa10y_from_low": 0.05, "baa10y_pct": 0.015,
                "rho60": -0.43, "rho60_run": 40, "rho60_sign": "-", "t10y2y": 0.25, "dfii10": 2.61,
                "bei": 2.34, "bei_chg_3m": 0.0, "core_pce_yoy": 3.34, "core_cpi_yoy": 2.45,
                "tp": 0.96, "tp_chg_3m": 0.1, "sofr": 3.85, "sofr_chg_3m": 0.0,
                "reserves_gdp": 9.3, "reserves_gdp_chg_3m": 0.0, "mult": 4.20, "emp_yoy": 2.7}
        return {**base, **kw}

    def _sig(self, ind, key):
        return next(s for s in rr.evaluate(ind) if s["key"] == key)

    def test_ci_rule_fires_when_below_nominal_gdp(self):
        self.assertFalse(self._sig(self._ind(), "ci_vs_ngdp")["fired"])
        s = self._sig(self._ind(ci_yoy=5.0), "ci_vs_ngdp")
        self.assertTrue(s["fired"])
        self.assertIn("F-00-04", s["log_ids"])
        self.assertIn("F-01-A-02", s["log_ids"])

    def test_ci_rule_unusable_before_break(self):
        self.assertIsNone(self._sig(self._ind(ci_valid=False), "ci_vs_ngdp")["fired"])

    def test_spread_rule(self):
        self.assertFalse(self._sig(self._ind(), "credit_spread")["fired"])
        self.assertTrue(self._sig(self._ind(hy_oas=4.7), "credit_spread")["fired"])
        self.assertTrue(self._sig(self._ind(baa10y_from_low=0.45), "credit_spread")["fired"])

    def test_corr_rule_positive_run(self):
        self.assertFalse(self._sig(self._ind(), "stock_bond_corr")["fired"])
        s = self._sig(self._ind(rho60=0.3, rho60_sign="+", rho60_run=130), "stock_bond_corr")
        self.assertTrue(s["fired"])
        self.assertEqual(s["scenario"], "B")

    def test_core_rule_text_and_missing(self):
        s = self._sig(self._ind(), "core_inflation")
        self.assertIn("D2", s["text"])
        self.assertFalse(s["fired"])
        self.assertTrue(self._sig(self._ind(core_pce_yoy=2.4), "core_inflation")["fired"])
        self.assertIsNone(self._sig(self._ind(core_pce_yoy=None), "core_inflation")["fired"])

    def test_every_rule_has_log_ids_and_source(self):
        for s in rr.evaluate(self._ind()):
            self.assertTrue(s["log_ids"], s["key"])
            self.assertTrue(s["source"], s["key"])
            self.assertIn(s["fired"], (True, False, None))


def make_cache(cache_dir, end=D(2026, 9, 18)):
    """모든 SERIES에 대해 그럴듯한 합성 CSV를 만든다(네트워크 대체)."""
    os.makedirs(cache_dir, exist_ok=True)
    n_d, n_m, n_w, n_q = 450, 40, 130, 14

    def wig(i, k=0.3):
        return k * math.sin(i / 5.0)

    quarters = [D(2023 + i // 4, 1 + 3 * (i % 4), 1) for i in range(n_q)]     # 2023-01-01 … 2026-04-01
    spec = {
        # SP500은 다음 주 월요일(end+3일) 관측이 하나 더 있다 — FRED 공표 시차 재현
        "SP500": daily(end + datetime.timedelta(days=3), [5000 + 4 * i + 20 * wig(i) for i in range(n_d + 1)]),
        "DGS10": daily(end, [4.0 + 0.002 * i + 0.05 * wig(i) for i in range(n_d)]),
        "THREEFYTP10": daily(end - datetime.timedelta(days=14), [0.5 + 0.001 * i for i in range(n_d)]),   # 신선도 경고 재현
        "BAA10Y": daily(end, [1.6 - 0.0004 * i for i in range(n_d)]),
        "BAMLH0A0HYM2": daily(end, [3.0 - 0.001 * i for i in range(n_d)]),
        "BAMLC0A0CM": daily(end, [0.9 - 0.0003 * i for i in range(n_d)]),
        "T10Y2Y": daily(end, [0.1 + 0.0004 * i for i in range(n_d)]),
        "DFII10": daily(end, [2.0 + 0.0014 * i for i in range(n_d)]),
        "T10YIE": daily(end, [2.3 + 0.0001 * i for i in range(n_d)]),
        "SOFR": daily(end, [4.3 - 0.001 * i for i in range(n_d)]),
        "DEXKOUS": daily(end, [1350 + 0.1 * i for i in range(n_d)]),
        "WRESBAL": weekly(end - datetime.timedelta(days=2), [3300000 - 2000 * i for i in range(n_w)]),
        "LNFACBW027SBOG": weekly(end - datetime.timedelta(days=9), [1600 + 3.5 * i + (236 if i >= 100 else 0) for i in range(n_w)]),
        "TOTLL": weekly(end - datetime.timedelta(days=9), [12500 + 12 * i for i in range(n_w)]),
        "M2SL": monthly(D(2023, 5, 1), [20800 + 60 * i for i in range(n_m)]),
        "BOGMBASE": monthly(D(2023, 5, 1), [5600 - 3 * i for i in range(n_m)]),
        "BUSLOANS": monthly(D(2023, 5, 1), [2700 + 20 * i for i in range(n_m)]),
        "PCEPILFE": monthly(D(2023, 5, 1), [120 * (1.0027 ** i) for i in range(n_m)]),
        "CPILFESL": [r for r in monthly(D(2023, 5, 1), [310 * (1.002 ** i) for i in range(n_m)]) if r[0] != D(2025, 10, 1)],
        "CES5552300001": monthly(D(2023, 5, 1), [1100 + 2 * i for i in range(n_m)]),
        "GDP": [(q, 27000 * (1.013 ** i)) for i, q in enumerate(quarters)],
        "M2V": [(q, 1.35 + 0.005 * i) for i, q in enumerate(quarters)],
    }
    for sid, series in spec.items():
        with open(os.path.join(cache_dir, sid + ".csv"), "w", encoding="utf-8") as f:
            f.write(f"observation_date,{sid}\n")
            for d, v in series:
                f.write(f"{d.isoformat()},{v}\n")
    return spec


BASE_IND = {"ci_yoy": 9.8, "ci_valid": True, "ngdp_yoy": 6.6, "ndfi_yoy": 18.6, "ndfi_share": 14.5,
            "hy_oas": 2.68, "baa10y": 1.44, "baa10y_from_low": 0.05, "baa10y_pct": 0.015,
            "rho60": -0.43, "rho60_run": 40, "rho60_sign": "-", "t10y2y": 0.25, "dfii10": 2.61,
            "bei": 2.34, "bei_chg_3m": 0.0, "core_pce_yoy": 3.34, "core_cpi_yoy": 2.45, "core_gap": -0.9,
            "tp": 0.96, "tp_chg_3m": 0.1, "sofr": 3.85, "sofr_chg_3m": 0.0,
            "reserves_gdp": 9.3, "reserves_gdp_chg_3m": 0.0, "mult": 4.20, "emp_yoy": 2.7}


def fired(key, **kw):
    return next(s for s in rr.evaluate({**BASE_IND, **kw}) if s["key"] == key)["fired"]


class RuleBoundaryTest(unittest.TestCase):
    """공개 규칙 문장의 '이상·이하·미만·초과'가 코드와 같아야 한다. 경계값은 실제 자료처럼 뺄셈으로 만든다
    (소수 둘째 자리 값끼리 빼면 0.3999999…가 되어 '이상' 경계를 놓치던 문제)."""

    def test_inclusive_boundaries_from_subtraction(self):
        self.assertTrue(fired("credit_spread", baa10y_from_low=1.40 - 1.00))     # 0.4%p 이상
        self.assertTrue(fired("sofr", sofr_chg_3m=4.10 - 3.85))                  # 0.25%p 이상 상승
        self.assertTrue(fired("term_premium", tp_chg_3m=0.04 - 0.29))            # 0.25%p 이상 하락
        self.assertTrue(fired("core_inflation", core_pce_yoy=3.0))               # 3% 이하
        self.assertTrue(fired("stock_bond_corr", rho60=0.2, rho60_sign="+", rho60_run=126))
        self.assertFalse(fired("stock_bond_corr", rho60=0.2, rho60_sign="+", rho60_run=125))
        self.assertTrue(fired("reserves_multiplier", reserves_gdp_chg_3m=9.6 - 9.3))  # 0.3%p 이상 증가 + PCE>2

    def test_exclusive_boundaries(self):
        self.assertFalse(fired("credit_spread", hy_oas=4.61))                    # 4.61%p 초과
        self.assertFalse(fired("real_rate_bei", dfii10=2.0, bei_chg_3m=0.1))     # 2% 미만
        self.assertFalse(fired("ndfi_credit", ndfi_yoy=10.0))                    # 10% 미만
        self.assertFalse(fired("curve_inversion", t10y2y=0.0))                   # 0보다 작으면
        self.assertFalse(fired("employment", emp_yoy=0.0))
        self.assertFalse(fired("reserves_multiplier", reserves_gdp=9.0))        # 9% 미만

    def test_missing_leg_is_unknown_not_unmet(self):
        # 한쪽 자료가 없으면 결론을 낼 수 없다 — 미충족으로 공개하면 틀린 말이 된다
        self.assertIsNone(fired("credit_spread", baa10y_from_low=None))          # OR: 다른 쪽 거짓 → 판정 불가
        self.assertTrue(fired("credit_spread", baa10y_from_low=None, hy_oas=5.0))  # OR: 다른 쪽 참 → 충족
        self.assertIsNone(fired("real_rate_bei", dfii10=1.5, bei_chg_3m=None))   # AND: 다른 쪽 참 → 판정 불가
        self.assertFalse(fired("real_rate_bei", dfii10=2.5, bei_chg_3m=None))    # AND: 다른 쪽 거짓 → 미충족
        self.assertIsNone(fired("term_premium", tp_chg_3m=None))
        self.assertIsNone(fired("sofr", sofr_chg_3m=None))
        self.assertIsNone(fired("reserves_multiplier", reserves_gdp_chg_3m=None))
        self.assertTrue(fired("reserves_multiplier", reserves_gdp=8.5, reserves_gdp_chg_3m=None))

    def test_unknown_text_does_not_claim_a_verdict(self):
        s = next(x for x in rr.evaluate({**BASE_IND, "sofr_chg_3m": None}) if x["key"] == "sofr")
        self.assertIn("판정 불가", s["text"])
        self.assertNotIn("재상승 없음", s["text"])

    def test_reserves_pce_floor_is_a_threshold(self):
        self.assertIn("reserves_pce_floor", rr.TH)
        self.assertFalse(fired("reserves_multiplier", reserves_gdp_chg_3m=0.5, core_pce_yoy=rr.TH["reserves_pce_floor"]))


class StepAndStaleTest(unittest.TestCase):
    def test_step_excluded_only_for_increases(self):
        vals = [1000 + 6 * i for i in range(60)]
        vals = [v - (80 if i >= 30 else 0) for i, v in enumerate(vals)]   # 30번째 주에 −80 실제 급감
        r = ff.step_excluded_yoy(weekly(D(2026, 9, 9), vals), step=40)
        self.assertEqual(r["excluded"], [])                                # 감소는 계단으로 빼지 않는다
        self.assertAlmostEqual(r["value"], r["raw_value"])

    def test_quarterly_stale_allows_advance_release_lag(self):
        # 분기 관측일은 분기 시작일 — 다음 속보 직전 나이가 ~212일이라 그 전엔 신선하다
        self.assertGreaterEqual(rr.STALE_DAYS["Q"], 212)


class BuildTest(unittest.TestCase):
    """regime_check.build: 매일 원본 결과를 <work>/raw/에 기록한다. 수신 실패면 아무것도 쓰지 않는다.
    원본과 캐시는 사이트 폴더(data/) 밖의 작업 폴더에 둔다 — 배포 산출물에 섞이지 않게."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.work = os.path.join(self.tmp, ".work")
        make_cache(os.path.join(self.work, "fred"))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _raw(self, name="latest.json"):
        with open(os.path.join(self.work, "raw", name), encoding="utf-8") as f:
            return json.load(f)

    def test_build_writes_raw_latest_and_history(self):
        res = rck.build(self.work, TODAY, offline=True, prev_regime="A")
        self.assertEqual(res["status"], "ok")
        js = self._raw()
        self.assertEqual((js["date"], js["schema"]), ("2026-09-22", rck.SCHEMA))
        for k in ("indicators", "signals", "regime_inputs", "manual", "sources", "warnings"):
            self.assertIn(k, js)
        self.assertEqual(js, self._raw(os.path.join("history", "2026-09-22.json")))
        # 합성값에서 손으로 계산한 기대치 (구현 공식을 되풀이하지 않는다)
        self.assertAlmostEqual(js["indicators"]["mult"]["value"], (20800 + 60 * 39) / (5600 - 3 * 39), places=6)
        self.assertEqual(js["indicators"]["mult"]["asof"], "2026-08-01")
        self.assertAlmostEqual(js["indicators"]["core_cpi_yoy"]["value"], (1.002 ** 12 - 1) * 100, places=6)
        self.assertAlmostEqual(js["indicators"]["ngdp_yoy"]["value"], (1.013 ** 4 - 1) * 100, places=6)
        self.assertTrue(all(s["fired"] in (True, False, None) for s in js["signals"]))
        si = js["regime_inputs"]
        self.assertEqual(si["regime_candidate"], "A")          # 주가 +5%·금리 +13bp 사분면
        self.assertEqual((si["sp_asof"], si["y10_asof"]), ("2026-09-21", "2026-09-18"))
        self.assertIn("2025-10", js["indicators"]["core_cpi_yoy"]["gaps"])
        self.assertTrue(any("계단" in w for w in js["warnings"]))
        self.assertTrue(any("결측" in w for w in js["warnings"]))
        self.assertTrue(any("THREEFYTP10" in w and "경과" in w for w in js["warnings"]))
        self.assertTrue(all(v["age_days"] >= 0 for v in js["sources"].values() if v.get("source")))

    def test_no_prev_regime_by_default(self):
        # 직전 국면은 사람이 넣는 값(비공개 견해)이라 자동으로 채우지 않는다
        rck.build(self.work, TODAY, offline=True)
        self.assertIsNone(self._raw()["regime_inputs"]["regime_prev"])

    def test_runs_every_day_and_keeps_one_history_file_per_date(self):
        rck.build(self.work, TODAY, offline=True)
        latest = os.path.join(self.work, "raw", "latest.json")
        os.utime(latest, (0, 0))
        self.assertEqual(rck.build(self.work, TODAY, offline=True)["status"], "ok")   # 같은 날 다시 돌아도 덮어쓴다
        self.assertGreater(os.path.getmtime(latest), 0)
        rck.build(self.work, TODAY + datetime.timedelta(days=1), offline=True)
        self.assertEqual(sorted(os.listdir(os.path.join(self.work, "raw", "history"))),
                         ["2026-09-22.json", "2026-09-23.json"])
        self.assertEqual(self._raw()["date"], "2026-09-23")

    def test_past_date_writes_history_only(self):
        # 과거 날짜 재계산은 지금 시점의 개정치로 만든 값이다 — 최신 결과(latest)를 되돌리지 않는다
        rck.build(self.work, TODAY, offline=True)
        res = rck.build(self.work, D(2026, 6, 15), offline=True)
        self.assertFalse(res["latest_updated"])
        self.assertEqual(self._raw()["date"], "2026-09-22")
        js = self._raw(os.path.join("history", "2026-06-15.json"))
        self.assertLessEqual(js["regime_inputs"]["sp_asof"], "2026-06-15")
        self.assertLessEqual(js["indicators"]["rho60"]["asof"], "2026-06-15")
        self.assertTrue(all(v["age_days"] >= 0 for v in js["sources"].values() if v.get("source")))

    def test_missing_series_is_warning_not_fatal(self):
        os.remove(os.path.join(self.work, "fred", "SOFR.csv"))
        self.assertEqual(rck.build(self.work, TODAY, offline=True)["status"], "ok")
        js = self._raw()
        self.assertIsNone(js["indicators"]["sofr"]["value"])
        self.assertTrue(any("SOFR" in w for w in js["warnings"]))
        self.assertIsNone(next(s for s in js["signals"] if s["key"] == "sofr")["fired"])

    def test_too_many_missing_series_keeps_previous_result(self):
        rck.build(self.work, TODAY, offline=True)
        before = self._raw()
        for sid in ("SOFR", "DGS10", "SP500", "M2SL", "GDP"):
            os.remove(os.path.join(self.work, "fred", sid + ".csv"))
        with self.assertRaises(RuntimeError):
            rck.build(self.work, TODAY + datetime.timedelta(days=1), offline=True)
        self.assertEqual(self._raw(), before)                  # 직전 결과가 그대로 남는다
        self.assertFalse(os.path.exists(os.path.join(self.work, "raw", "history", "2026-09-23.json")))

    def _with_network(self, fail_ids):
        """fail_ids에 든 시리즈는 FRED 요청이 즉시 실패(캐시는 있음), 나머지는 캐시 파일 내용을 '수신'한 것처럼."""
        orig = ff.urlopen_text

        def fake(url, timeout=None):
            sid = url.rsplit("=", 1)[-1]
            if sid in fail_ids:
                raise OSError("HTTP Error 503")
            with open(os.path.join(self.work, "fred", sid + ".csv"), encoding="utf-8") as f:
                return f.read()
        ff.urlopen_text = fake
        return orig

    def test_cache_fallback_counts_as_not_received(self):
        # FRED가 즉시 실패하고 캐시만 있으면 '수신 22/22'가 아니다 — 새 날짜로 기록하지 않는다
        rck.build(self.work, TODAY, offline=True)
        before = self._raw()
        orig = self._with_network(set(rr.SERIES))
        try:
            with self.assertRaises(RuntimeError):
                rck.build(self.work, TODAY + datetime.timedelta(days=1), offline=False)
        finally:
            ff.urlopen_text = orig
        self.assertEqual(self._raw(), before)
        self.assertFalse(os.path.exists(os.path.join(self.work, "raw", "history", "2026-09-23.json")))

    def test_few_cache_fallbacks_are_allowed_and_reported(self):
        orig = self._with_network({"SOFR", "DEXKOUS"})
        try:
            res = rck.build(self.work, TODAY, offline=False)
        finally:
            ff.urlopen_text = orig
        self.assertEqual((res["net"], res["cache"], res["missing"]), (len(rr.SERIES) - 2, 2, 0))
        self.assertEqual(self._raw()["sources"]["SOFR"]["source"], "cache")

    def test_load_all_stops_after_max_missing(self):
        calls = []
        orig = ff.load

        def boom(sid, cache_dir, offline=False, timeout=None):
            calls.append(sid)
            raise RuntimeError("hang")
        ff.load = boom
        try:
            series, sources, _ = rck.load_all(os.path.join(self.work, "fred"), False, TODAY)
        finally:
            ff.load = orig
        self.assertEqual(len(calls), rck.MAX_MISSING + 1)         # 초과 확정 뒤엔 더 기다리지 않는다
        self.assertTrue(all(s is None for s in series.values()))
        self.assertTrue(any("중단" in v.get("error", "") for v in sources.values()))

    def _load_all_with(self, fake, budget):
        orig, orig_budget = ff.load, rck.BUDGET_SEC
        ff.load, rck.BUDGET_SEC = fake, budget
        try:
            return rck.load_all(os.path.join(self.work, "fred"), False, TODAY)
        finally:
            ff.load, rck.BUDGET_SEC = orig, orig_budget

    def test_load_all_stops_when_time_budget_spent(self):
        calls = []
        series, sources, _ = self._load_all_with(lambda sid, *a, **k: calls.append(sid), budget=0)
        self.assertEqual(calls, [])
        self.assertTrue(all(s is None for s in series.values()))
        self.assertTrue(all("시간 상한" in v["error"] for v in sources.values()))

    def test_load_all_caps_each_timeout_by_remaining_budget(self):
        timeouts = []
        real = ff.load

        def spy(sid, cache_dir, offline=False, timeout=None):
            timeouts.append(timeout)
            s, _ = real(sid, cache_dir, offline=True)
            return s, "net"                  # 정상 수신처럼 — 캐시 대체로 세면 3개에서 멈춘다
        self._load_all_with(spy, budget=10)
        self.assertEqual(len(timeouts), len(rr.SERIES))
        self.assertTrue(all(0 < t <= 10 for t in timeouts))


def run_cli(script, *args):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args],
                          capture_output=True, env=env, text=True, encoding="utf-8")


class CliTest(unittest.TestCase):
    """CLI 출력은 공개 저장소의 Actions 로그에 남는다 — 요약 한 줄만, 지표 값·해석 문구는 찍지 않는다."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.work = os.path.join(self.tmp, ".work")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_success_prints_one_summary_line_only(self):
        make_cache(os.path.join(self.work, "fred"))
        p = run_cli("regime_check.py", "--work", self.work, "--offline", "--date", TODAY.isoformat())
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, "")
        lines = p.stdout.strip().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertIn("2026-09-22", lines[0])
        for leak in ("HY OAS", "Baa", "S&P", "%p", "→", "진행", "선행"):
            self.assertNotIn(leak, p.stdout)

    def test_failure_is_one_line_and_exit_1(self):
        p = run_cli("regime_check.py", "--work", self.work, "--offline", "--date", TODAY.isoformat())
        self.assertEqual(p.returncode, 1)                      # 캐시 없는 빈 폴더 + offline → 22개 미수신
        err = p.stderr.strip().splitlines()
        self.assertEqual(len(err), 1)
        self.assertNotIn("Traceback", err[0])
        self.assertIn("미수신", err[0])
        self.assertFalse(os.path.exists(os.path.join(self.work, "raw", "latest.json")))

    def test_future_date_rejected(self):
        make_cache(os.path.join(self.work, "fred"))
        future = (datetime.date.today() + datetime.timedelta(days=3)).isoformat()
        p = run_cli("regime_check.py", "--work", self.work, "--offline", "--date", future)
        self.assertEqual(p.returncode, 1)
        self.assertEqual(len(p.stderr.strip().splitlines()), 1)
        self.assertFalse(os.path.exists(os.path.join(self.work, "raw")))


if __name__ == "__main__":
    unittest.main(verbosity=1)


