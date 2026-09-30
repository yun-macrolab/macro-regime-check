#!/usr/bin/env python3
"""그래프 자료(render_charts) 테스트 — 카드 값과의 일치, 제한 원값 부재, 화이트리스트, 페이지 정적 검사.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — test_regime의 합성 FRED 캐시로 원본 결과를 만든 뒤 그래프 자료를 만든다.
제한 시리즈(S&P·ICE·Moody's)는 다른 어떤 값과도 겹치지 않는 구간(70~80, 5000대)으로 덮어써서,
그 원값이 그래프 자료에 섞이면 숫자 범위만으로 잡히게 한다.
"""
import os, sys, re, json, math, datetime, tempfile, unittest, shutil
from unittest import mock

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import fred_fetch as ff
import regime_rules as rr
import regime_check as rck
import render_public as rp
import render_charts as rc
from test_regime import make_cache, run_cli, daily, weekly, monthly
from test_render_public import walk

TODAY = datetime.date(2026, 9, 22)
D = datetime.date
SITE = os.path.join(os.path.dirname(SCRIPTS), "site")
RESTRICTED_BAND = (70.0, 80.0)
# 규칙 key → [(선 key = 지표 key)] — 선의 마지막 점이 카드(공개본)의 값과 같아야 한다
RULE_LINES = {
    "ci_vs_ngdp": ["ci_yoy", "ngdp_yoy"],
    "ndfi_credit": ["ndfi_yoy"],
    "stock_bond_corr": ["rho60"],
    "curve_inversion": ["t10y2y"],
    "real_rate_bei": ["dfii10"],
    "core_inflation": ["core_pce_yoy", "core_cpi_yoy"],
    "term_premium": ["tp_chg_3m"],
    "reserves_multiplier": ["reserves_gdp"],
    "employment": ["emp_yoy"],
}
OVERVIEW_LINES = {"yield10": ["dgs10", "dfii10", "bei"], "term": ["tp", "t10y2y"]}
SPEC_KEYS = {"key", "title", "unit", "years", "zero", "threshold", "note", "lines"}
LINE_KEYS = {"key", "label", "role", "series", "derived", "points"}


def restrict_cache(cache_dir):
    """제한 시리즈를 고유 구간 값으로 덮어쓴다(날짜는 그대로)."""
    bases = {"BAA10Y": 71.0, "BAMLH0A0HYM2": 74.0, "BAMLC0A0CM": 77.0}
    for sid, base in bases.items():
        rows, _ = ff.load(sid, cache_dir, offline=True)
        with open(os.path.join(cache_dir, sid + ".csv"), "w", encoding="utf-8") as f:
            f.write(f"observation_date,{sid}\n")
            for i, (d, _) in enumerate(rows):
                f.write(f"{d.isoformat()},{base + 0.001 * (i % 1000)}\n")


def make_work(tmp, today=TODAY):
    work = os.path.join(tmp, ".work")
    make_cache(os.path.join(work, "fred"))
    restrict_cache(os.path.join(work, "fred"))
    rck.build(work, today, offline=True, prev_regime="A")
    with open(os.path.join(work, "raw", "latest.json"), encoding="utf-8") as f:
        return work, json.load(f)


def long_history(cache_dir, end=D(2026, 9, 18)):
    """그래프가 쓰는 시리즈를 약 8년 치로 덮어쓴다 — 3·5년 창과 계산 여유(LOOKBACK)가 실제로 잘리는지 보려면
    창 시작보다 훨씬 앞선 자료가 있어야 한다(make_cache는 약 1.8년뿐)."""
    nd, nw = 8 * 261, 8 * 52
    quarters = [D(2018 + (6 + 3 * i) // 12, (6 + 3 * i) % 12 + 1, 1) for i in range(32)]   # 2018-07-01 … 2026-04-01
    spec = {
        "DGS10": daily(end, [3 + math.sin(i / 50) for i in range(nd)]),
        "DFII10": daily(end, [1 + 0.8 * math.sin(i / 60) for i in range(nd)]),
        "T10YIE": daily(end, [2.2 + 0.2 * math.sin(i / 30) for i in range(nd)]),
        "T10Y2Y": daily(end, [0.3 * math.sin(i / 80) for i in range(nd)]),
        "THREEFYTP10": daily(end, [0.5 * math.sin(i / 70) for i in range(nd)]),
        "SP500": daily(end, [4000 + i + 40 * math.sin(i / 9) for i in range(nd)]),
        "WRESBAL": weekly(end - datetime.timedelta(days=2), [3000000 + 1000 * i for i in range(nw)]),
        "LNFACBW027SBOG": weekly(end - datetime.timedelta(days=9), [1000 + 2 * i for i in range(nw)]),
        "TOTLL": weekly(end - datetime.timedelta(days=9), [12000 + 10 * i for i in range(nw)]),
        "PCEPILFE": monthly(D(2018, 9, 1), [100 * 1.0025 ** i for i in range(96)]),
        "CPILFESL": monthly(D(2018, 9, 1), [250 * 1.002 ** i for i in range(96)]),
        "BUSLOANS": monthly(D(2018, 9, 1), [2500 + 5 * i for i in range(96)]),
        "CES5552300001": monthly(D(2018, 9, 1), [1000 + i for i in range(96)]),
        "GDP": [(q, 20000 * 1.012 ** i) for i, q in enumerate(quarters)],
    }
    for sid, rows in spec.items():
        with open(os.path.join(cache_dir, sid + ".csv"), "w", encoding="utf-8") as f:
            f.write(f"observation_date,{sid}\n")
            for d, v in rows:
                f.write(f"{d.isoformat()},{v}\n")
    return spec


def last_point(line):
    return line["points"][-1]


class ChartsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.work, cls.raw = make_work(cls.tmp)
        cls.charts, cls.skipped = rc.build(cls.work)
        cls.ind = cls.raw["indicators"]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def line(self, spec, key):
        return next(l for l in spec["lines"] if l["key"] == key)

    def assertLastEquals(self, line, ind_key):
        ind = self.ind[ind_key]
        exp_v = None if ind["value"] is None else round(ind["value"], 3)
        self.assertEqual(last_point(line), [ind["asof"], exp_v], (line["key"], ind_key))

    # ---- 1·2. 카드 값과 일치 ----
    def test_rule_lines_end_at_the_card_value(self):
        self.assertEqual(set(self.charts["rules"]), set(RULE_LINES))
        self.assertEqual(self.skipped, [])
        for rule, keys in RULE_LINES.items():
            spec = self.charts["rules"][rule]
            self.assertEqual([l["key"] for l in spec["lines"]], keys, rule)
            for k in keys:
                self.assertLastEquals(self.line(spec, k), k)

    def test_overview_lines_end_at_the_latest_level(self):
        self.assertEqual([s["key"] for s in self.charts["overview"]], list(OVERVIEW_LINES))
        for spec in self.charts["overview"]:
            self.assertEqual([l["key"] for l in spec["lines"]], OVERVIEW_LINES[spec["key"]])
            for l in spec["lines"]:
                self.assertEqual(l["role"], "series")
                self.assertLastEquals(l, l["key"])

    def test_rolling_corr_matches_corr_summary(self):
        S = {sid: ff.load(sid, os.path.join(self.work, "fred"), offline=True)[0] for sid in ("SP500", "DGS10")}
        vals = rc.rolling_corr(S["SP500"], S["DGS10"], 60)
        cs = ff.corr_summary(S["SP500"], S["DGS10"], 60)
        self.assertEqual(vals[-1], (cs["asof"], cs["value"]))
        self.assertGreater(len(vals), 200)
        # 중간 점도: 그 날까지 자른 원자료의 corr_summary와 날짜·값이 같다
        for d, v in vals[:: len(vals) // 6]:
            cut = ff.corr_summary(rc.upto(S["SP500"], d), rc.upto(S["DGS10"], d), 60)
            self.assertEqual((d, v), (cut["asof"], cut["value"]))

    def test_every_point_uses_the_rule_function(self):
        # 중간 점도 규칙 함수로 계산한 값이어야 한다 — 마지막 점만 맞추는 구현을 잡는다
        S = {sid: ff.load(sid, os.path.join(self.work, "fred"), offline=True)[0]
             for sid in ("THREEFYTP10", "LNFACBW027SBOG", "PCEPILFE", "WRESBAL", "GDP")}
        cut = lambda s, d: [x for x in s if x[0] <= d]
        checks = [("term_premium", "tp_chg_3m", lambda d: ff.change_days(cut(S["THREEFYTP10"], d), 91)["delta"]),
                  ("ndfi_credit", "ndfi_yoy",
                   lambda d: ff.step_excluded_yoy(cut(S["LNFACBW027SBOG"], d), rr.TH["ndfi_step_bn"])["value"]),
                  ("core_inflation", "core_pce_yoy", lambda d: ff.yoy(cut(S["PCEPILFE"], d), same_month=True)["value"]),
                  # 지난 점은 그 날 이하 최신 GDP로 — 나중에 나온 GDP로 과거 비율을 다시 쓰지 않는다
                  ("reserves_multiplier", "reserves_gdp",
                   lambda d: cut(S["WRESBAL"], d)[-1][1] / 1000 / ff.on_or_before(S["GDP"], d)[1] * 100)]
        for rule, key, fn in checks:
            pts = self.line(self.charts["rules"][rule], key)["points"]
            for ds, v in pts[:: max(1, len(pts) // 7)]:
                self.assertEqual(v, round(fn(D.fromisoformat(ds)), 3), (rule, ds))

    # ---- 4. 임계값 ----
    def test_thresholds_follow_TH(self):
        th = rr.TH
        expect = {"ci_vs_ngdp": None, "ndfi_credit": th["ndfi_two_digit"], "stock_bond_corr": None,
                  "curve_inversion": 0.0, "real_rate_bei": th["real_rate_c"], "core_inflation": th["core_pce_split"],
                  "term_premium": -th["tp_drop_3m"], "reserves_multiplier": th["reserves_gdp_low"], "employment": 0.0}
        self.assertEqual({k: s["threshold"] for k, s in self.charts["rules"].items()}, expect)
        with mock.patch.dict(rr.TH, {"ndfi_two_digit": 12.5, "tp_drop_3m": 0.4}):
            ch, _ = rc.build(self.work)
        self.assertEqual(ch["rules"]["ndfi_credit"]["threshold"], 12.5)
        self.assertEqual(ch["rules"]["term_premium"]["threshold"], -0.4)

    # ---- 5·6. 기간·순서·기준일 ----
    def test_points_are_in_window_ascending_and_not_after_the_date(self):
        asof = D.fromisoformat(self.charts["date"])
        self.assertEqual(self.charts["date"], self.raw["date"])
        for spec in self.charts["overview"] + list(self.charts["rules"].values()):
            start = ff.shift_year(asof, -spec["years"])
            for l in spec["lines"]:
                dates = [p[0] for p in l["points"]]
                self.assertEqual(dates, sorted(set(dates)), l["key"])
                self.assertTrue(all(start.isoformat() <= d <= asof.isoformat() for d in dates), l["key"])
        self.assertEqual({s["years"] for s in self.charts["overview"]}, {5})
        self.assertEqual({s["years"] for s in self.charts["rules"].values()}, {3})

    def test_earlier_as_of_date_cuts_later_observations(self):
        tmp = tempfile.mkdtemp()
        try:
            work, raw = make_work(tmp, today=D(2026, 9, 10))
            ch, _ = rc.build(work)
            self.assertEqual(ch["date"], "2026-09-10")
            for spec in ch["overview"] + list(ch["rules"].values()):
                for l in spec["lines"]:
                    self.assertLessEqual(l["points"][-1][0], "2026-09-10")
            ind = raw["indicators"]
            for rule, keys in RULE_LINES.items():
                for k in keys:
                    l = next(x for x in ch["rules"][rule]["lines"] if x["key"] == k)
                    exp = None if ind[k]["value"] is None else round(ind[k]["value"], 3)
                    self.assertEqual(l["points"][-1], [ind[k]["asof"], exp], k)
        finally:
            shutil.rmtree(tmp)

    def test_ci_starts_after_the_classification_break(self):
        ci = self.line(self.charts["rules"]["ci_vs_ngdp"], "ci_yoy")["points"]
        self.assertEqual(ci[0][0], "2026-01-01")                  # 기준치가 2025-01 이후인 첫 달
        self.assertTrue(all(v is not None for _, v in ci))
        ng = self.line(self.charts["rules"]["ci_vs_ngdp"], "ngdp_yoy")["points"]
        self.assertLess(ng[0][0], "2025-01-01")                   # 참고 선은 3년 그대로

    # ---- 7. 제한 원값 부재 ----
    def test_restricted_raw_values_absent(self):
        _, nums, strs = walk(self.charts)
        lo, hi = RESTRICTED_BAND
        self.assertFalse([n for n in nums if lo <= n < hi or abs(n) >= 1000])
        self.assertFalse([s for s in strs if re.search(r"\d+\.\d+", s)])
        derived = set()
        for spec in self.charts["overview"] + list(self.charts["rules"].values()):
            for l in spec["lines"]:
                if set(l["series"]) & set(rp.RESTRICTED):
                    self.assertTrue(l["derived"], l["key"])
                    derived.add(l["key"])
                else:
                    self.assertTrue(set(l["series"]) <= rc.ALLOWED, l["key"])
        self.assertEqual(derived, {"rho60"})
        self.assertEqual(rc.ALLOWED, set(rr.SERIES) - set(rp.RESTRICTED) - {"SOFR"})

    def test_restricted_band_is_really_in_the_cache(self):
        # 위 검사가 헛돌지 않게 — 원본 결과에는 그 구간 값이 실제로 있다
        self.assertTrue(RESTRICTED_BAND[0] <= self.ind["baa10y"]["value"] < RESTRICTED_BAND[1])

    # ---- 8. 화이트리스트·계약 ----
    def test_every_string_is_whitelisted(self):
        allowed = {"main", "ref", "series", "%", "%p", ""}
        table = rc.chart_table()
        for spec in table["overview"] + list(table["rules"].values()):
            allowed |= {spec["key"], spec["title"]} | ({spec["note"]} if spec["note"] else set())
            for l in spec["lines"]:
                allowed |= {l["key"], l["label"], *l["series"]}
        allowed |= set(table["rules"])
        keys, _, strs = walk(self.charts)
        date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        ts_re = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$")
        bad = [s for s in strs if s not in allowed and not date_re.match(s) and not ts_re.match(s)]
        self.assertEqual(bad, [])
        self.assertTrue(set(keys) <= SPEC_KEYS | LINE_KEYS | {"schema", "date", "generated_at", "overview", "rules"}
                        | set(table["rules"]))

    def test_contract_shape(self):
        self.assertEqual(set(self.charts), {"schema", "date", "generated_at", "overview", "rules"})
        self.assertEqual(self.charts["schema"], 1)
        for spec in self.charts["overview"] + list(self.charts["rules"].values()):
            self.assertEqual(set(spec), SPEC_KEYS, spec["key"])
            self.assertIn(spec["unit"], ("%", "%p", ""))
            self.assertIsInstance(spec["zero"], bool)
            for l in spec["lines"]:
                self.assertEqual(set(l), LINE_KEYS, l["key"])
                self.assertIn(l["role"], ("main", "ref", "series"))
                self.assertTrue(l["points"] and l["points"][0][1] is not None, l["key"])   # 앞쪽 null은 잘린다
                for d, v in l["points"]:
                    self.assertTrue(v is None or (isinstance(v, float) and math.isfinite(v)), (l["key"], d, v))
        for spec in self.charts["rules"].values():
            self.assertEqual(spec["lines"][0]["role"], "main")
            self.assertTrue(all(l["role"] == "ref" for l in spec["lines"][1:]))

    def _rewrite(self, work, sid, keep):
        """캐시 CSV에서 keep(date)이 참인 관측치만 남긴다."""
        rows, _ = ff.load(sid, os.path.join(work, "fred"), offline=True)
        with open(os.path.join(work, "fred", sid + ".csv"), "w", encoding="utf-8") as f:
            f.write(f"observation_date,{sid}\n")
            for d, v in rows:
                if keep(d):
                    f.write(f"{d.isoformat()},{v}\n")
        return rows

    def test_midweek_last_observation_still_matches_the_card(self):
        # 표본(주별 마지막)이 모두 금요일이면 91일과 90일이 같은 관측을 가리켜 계산 차이가 숨는다 — 수요일에 끝나게 한다
        tmp = tempfile.mkdtemp()
        try:
            work, _ = make_work(tmp)
            rows, _ = ff.load("THREEFYTP10", os.path.join(work, "fred"), offline=True)
            wed = max(d for d, _ in rows if d.weekday() == 2)
            self._rewrite(work, "THREEFYTP10", lambda d: d <= wed)
            rck.build(work, TODAY, offline=True, prev_regime="A")
            with open(os.path.join(work, "raw", "latest.json"), encoding="utf-8") as f:
                ind = json.load(f)["indicators"]["tp_chg_3m"]
            ch, _ = rc.build(work)
            tp = ch["rules"]["term_premium"]["lines"][0]["points"]
            self.assertEqual(tp[-1], [wed.isoformat(), round(ind["value"], 3)])
        finally:
            shutil.rmtree(tmp)

    def test_missing_base_month_is_a_gap_not_a_13_month_change(self):
        # 기준 달이 빠지면 그 달의 전년비는 비운다(null) — 전 달 값으로 13개월 변화를 전년비라 부르지 않는다
        tmp = tempfile.mkdtemp()
        try:
            work, _ = make_work(tmp)
            gone = D(2024, 11, 1)
            self._rewrite(work, "CPILFESL", lambda d: d != gone)
            ch, _ = rc.build(work)
            cpi = dict(map(tuple, next(l for l in ch["rules"]["core_inflation"]["lines"]
                                       if l["key"] == "core_cpi_yoy")["points"]))
            self.assertIsNone(cpi["2025-11-01"])
            self.assertIsNotNone(cpi["2025-12-01"])
        finally:
            shutil.rmtree(tmp)

    def test_reserves_last_point_matches_card_when_a_gdp_quarter_is_newer(self):
        # 분기 첫 주에 기준일을 과거로 준 재계산: GDP 관측일(분기 시작일)이 마지막 지준 주보다 늦다(리뷰 재현)
        tmp = tempfile.mkdtemp()
        try:
            work, _ = make_work(tmp)
            fred = os.path.join(work, "fred")
            wres, _ = ff.load("WRESBAL", fred, offline=True)
            gdp, _ = ff.load("GDP", fred, offline=True)
            with open(os.path.join(fred, "GDP.csv"), "a", encoding="utf-8") as f:
                f.write(f"{(wres[-1][0] + datetime.timedelta(days=1)).isoformat()},{gdp[-1][1] * 1.05}\n")
            rck.build(work, TODAY, offline=True, prev_regime="A")
            with open(os.path.join(work, "raw", "latest.json"), encoding="utf-8") as f:
                ind = json.load(f)["indicators"]["reserves_gdp"]
            ch, _ = rc.build(work)
            pts = ch["rules"]["reserves_multiplier"]["lines"][0]["points"]
            self.assertEqual(pts[-1], [ind["asof"], round(ind["value"], 3)])
            prev_d = D.fromisoformat(pts[-2][0])                   # 지난 점은 그 날 이하 GDP 그대로
            w = [x for x in wres if x[0] <= prev_d][-1][1]
            self.assertEqual(pts[-2][1], round(w / 1000 / ff.on_or_before(gdp, prev_d)[1] * 100, 3))
        finally:
            shutil.rmtree(tmp)

    def test_chart_rules_are_signal_keys_the_page_can_attach(self):
        # 페이지는 public.json 규칙 key로 그래프를 찾는다 — 규칙 key가 바뀌면 그래프가 조용히 빠지지 않게
        signals = {s["key"] for s in self.raw["signals"]}
        self.assertEqual(set(rc.chart_table()["rules"]), signals - {"credit_spread", "sofr"})

    # ---- 9. 자료 누락 ----
    def test_missing_series_drops_only_that_chart_or_line(self):
        tmp = tempfile.mkdtemp()
        try:
            work, _ = make_work(tmp)
            for sid in ("WRESBAL", "CPILFESL", "THREEFYTP10"):
                os.remove(os.path.join(work, "fred", sid + ".csv"))
            ch, skipped = rc.build(work)
            self.assertEqual(sorted(skipped), ["reserves_multiplier", "term_premium"])
            self.assertEqual(set(ch["rules"]), set(RULE_LINES) - {"reserves_multiplier", "term_premium"})
            self.assertEqual([l["key"] for l in ch["rules"]["core_inflation"]["lines"]], ["core_pce_yoy"])
            term = next(s for s in ch["overview"] if s["key"] == "term")
            self.assertEqual([l["key"] for l in term["lines"]], ["t10y2y"])
            # 주 선이 없으면 참고 선만으로 카드 그래프를 만들지 않는다
            os.remove(os.path.join(work, "fred", "BUSLOANS.csv"))
            ch, skipped = rc.build(work)
            self.assertIn("ci_vs_ngdp", skipped)
            self.assertNotIn("ci_vs_ngdp", ch["rules"])
            self.assertTrue(all(spec["lines"][0]["role"] == "main" for spec in ch["rules"].values()))
        finally:
            shutil.rmtree(tmp)


class LongHistoryTest(unittest.TestCase):
    """창 시작보다 훨씬 긴 자료 — 기간 창·계산 여유·주간 표본이 실제로 작동하는지."""
    GAP = {"D": 7, "W": 7, "M": 31, "Q": 92}

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.work = os.path.join(cls.tmp, ".work")
        make_cache(os.path.join(cls.work, "fred"))
        cls.spec = long_history(os.path.join(cls.work, "fred"))
        rck.build(cls.work, TODAY, offline=True, prev_regime="A")
        cls.charts, cls.skipped = rc.build(cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def lines(self):
        for spec in self.charts["overview"] + list(self.charts["rules"].values()):
            for l in spec["lines"]:
                yield spec, l

    def test_first_point_is_at_the_window_start_with_a_value(self):
        self.assertEqual(self.skipped, [])
        for spec, l in self.lines():
            if l["key"] == "ci_yoy":                               # 분류 단절 뒤부터만(따로 검사)
                continue
            start = ff.shift_year(TODAY, -spec["years"])
            first = D.fromisoformat(l["points"][0][0])
            gap = self.GAP[rr.SERIES[l["series"][0]][1]]
            self.assertTrue(start <= first <= start + datetime.timedelta(days=gap), (l["key"], first, start))
            self.assertIsNotNone(l["points"][0][1], l["key"])

    def test_daily_lines_have_one_point_per_week_at_its_last_observation(self):
        daily_lines = [(s, l) for s, l in self.lines() if rr.SERIES[l["series"][0]][1] == "D"]
        self.assertGreaterEqual(len(daily_lines), 7)
        for spec, l in daily_lines:
            dates = [D.fromisoformat(p[0]) for p in l["points"]]
            weeks = [d.isocalendar()[:2] for d in dates]
            self.assertEqual(len(weeks), len(set(weeks)), l["key"])
            if l["key"] == "rho60":
                continue
            obs = {}
            for d, _ in self.spec[l["series"][0]]:
                wk = d.isocalendar()[:2]
                obs[wk] = max(obs.get(wk, d), d)
            self.assertEqual(dates, [obs[w] for w in weeks], l["key"])
        self.assertLess(len(next(l for _, l in self.lines() if l["key"] == "dgs10")["points"]), 5 * 53 + 2)


class ChartsCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.out = os.path.join(self.tmp, "data")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_cli(self, work):
        return run_cli("render_charts.py", "--work", work, "--out", self.out)

    def test_missing_raw_is_one_line_and_exit_1(self):
        r = self.run_cli(os.path.join(self.tmp, "없음"))
        self.assertEqual(r.returncode, 1)
        self.assertEqual(len(r.stderr.strip().splitlines()), 1)
        self.assertFalse(os.path.exists(os.path.join(self.out, "charts.json")))

    def test_success_writes_compact_json_and_one_summary_line(self):
        work, raw = make_work(self.tmp)
        r = self.run_cli(work)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.strip().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertFalse(re.search(r"\d+\.\d+", lines[0]))      # 공개 로그에 지표 값을 찍지 않는다
        with open(os.path.join(self.out, "charts.json"), encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("\n", text)
        self.assertEqual(json.loads(text)["date"], raw["date"])

    def test_nothing_built_is_exit_1_and_keeps_the_previous_charts(self):
        work, _ = make_work(self.tmp)
        os.makedirs(self.out)
        prev = {"schema": 1, "date": "2026-09-22", "overview": [{"key": "yield10"}], "rules": {}}
        with open(os.path.join(self.out, "charts.json"), "w", encoding="utf-8") as f:
            json.dump(prev, f)
        shutil.rmtree(os.path.join(work, "fred"))
        r = self.run_cli(work)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(len(r.stderr.strip().splitlines()), 1)
        with open(os.path.join(self.out, "charts.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f), prev)

    def test_older_date_does_not_replace_newer_charts(self):
        os.makedirs(self.out)
        newer = {"schema": 1, "date": "2099-01-01"}
        with open(os.path.join(self.out, "charts.json"), "w", encoding="utf-8") as f:
            json.dump(newer, f)
        work, _ = make_work(self.tmp)
        ch, _ = rc.build(work)
        self.assertFalse(rc.write(self.out, ch))
        with open(os.path.join(self.out, "charts.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f), newer)


class PageStaticTest(unittest.TestCase):
    """페이지는 테스트 러너가 없어 정적 검사만 — 글자를 HTML로 해석하는 통로와 외부 스크립트를 막는다."""
    FORBIDDEN = ("innerHTML", "outerHTML", "insertAdjacentHTML", "eval(", "document.write", "new Function")

    def read(self, name):
        with open(os.path.join(SITE, name), encoding="utf-8") as f:
            return f.read()

    def test_no_html_injection_sinks_or_external_scripts(self):
        for name in ("index.html", "charts.js"):
            text = self.read(name)
            for tok in self.FORBIDDEN:
                self.assertNotIn(tok, text, (name, tok))
            self.assertFalse(re.search(r"<script[^>]*\bsrc=[\"']?(https?:)?//", text), name)

    def test_page_loads_charts_script_and_data(self):
        html = self.read("index.html")
        self.assertIn('<script src="charts.js"></script>', html)
        self.assertIn("data/charts.json", html)


if __name__ == "__main__":
    unittest.main(verbosity=1)
