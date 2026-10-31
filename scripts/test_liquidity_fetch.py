#!/usr/bin/env python3
"""지준·재정 참고 자료(liquidity_fetch) 테스트 — 산식(손으로 셀 수 있는 합성 자료), 13주 나눔의 합·91일 근처, 규칙 카드와
같은 지준/GDP 값, 재정(정확히 12개 달·같은 분기·네 분기 앞), 칸마다 실패·직전 값 이어 싣기, 이용 조건 목록, 문구 원칙
(판정 낱말 없음), 화면·워크플로 연결.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — FRED는 가짜 loader 또는 합성 캐시(--offline). 숫자는 모두 지어낸 것이다.
"""
import os, sys, io, re, json, datetime, tempfile, unittest, shutil, contextlib
from unittest import mock

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import liquidity_fetch as liq
import ai_invest_fetch as ai
import regime_check as rc
import regime_rules as rr
import render_public as rp
from test_render_public import FORBIDDEN_TEXT

REPO = os.path.dirname(SCRIPTS)
D = datetime.date
NOW = datetime.datetime(2026, 10, 30, 1, 30, tzinfo=datetime.timezone.utc)
# 판정·방향 낱말 — 공개 카드 어디에도 없어야 한다(FORBIDDEN_TEXT에 더해)
VERDICT = ("판정", "충족", "신호", "경보", "전망", "매수", "매도", "⚠", "강세", "약세", "호재", "악재", "우려", "부담",
           "상승", "하락", "→", "긴축", "완화", "위험")
# 카드 주제 낱말 — FORBIDDEN_TEXT의 '재정'은 이 꼴로만 허용한다(재정 우위 같은 해석 낱말은 여전히 막는다)
TOPIC = ("지준·재정", "재정수지")


def wednesdays(start, end):
    out, d = [], start
    while d <= end:
        out.append(d)
        d += datetime.timedelta(days=7)
    return out


def months(start, end):
    out, (y, m) = [], (start.year, start.month)
    while D(y, m, 1) <= end:
        out.append(D(y, m, 1))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def quarters(start, end):
    return [d for d in months(start, end) if d.month in (1, 4, 7, 10)]


def step(before, after, at=D(2026, 8, 1)):
    return lambda d: before if d < at else after


def world(end=D(2026, 10, 28)):
    """13주(2026-07-29 → 2026-10-28): 지준 −95 = TGA +110(지준 쪽 −110) · 역레포 −19(+19) · 단기채 +57 · 이표채 −3 · 그 밖 −58.
    지준/GDP = 2,904 / 33,000 = 8.8%(하한 9.0 대비 −0.2%p ≈ −66bn). 재정 12개월 −1,920 · 1년 전 −1,800. 단위는 FRED 그대로."""
    wk = wednesdays(D(2025, 1, 1), end)
    lv = {"WRBWFRBL": step(3_100_000, 3_005_000), "WDTGAL": step(800_000, 910_000), "WLRRAL": step(50_000, 31_000),
          "WSHOBL": step(200_000, 257_000), "WSHONBNL": step(4_000_000, 3_997_000)}
    S = {sid: [(d, float(f(d))) for d in wk] for sid, f in lv.items()}
    S["WRESBAL"] = [(d, 2_904_000.0) for d in wk]
    qs = quarters(D(2025, 1, 1), D(2026, 7, 1))
    S["GDP"] = [(q, 30_000.0 + 500 * i) for i, q in enumerate(qs)]                       # 2026-07-01 = 33,000
    S["A091RC1Q027SBEA"] = [(q, 1_200.0 + 10 * i) for i, q in enumerate(qs)]             # 2026-07-01 = 1,260
    S["MTSDS133FMS"] = [(m, -160_000.0 if m >= D(2025, 10, 1) else -150_000.0) for m in months(D(2024, 1, 1), D(2026, 9, 1))]
    zq = quarters(D(2024, 1, 1), D(2026, 4, 1))
    S["BOGZ1FL313161110Q"] = [(q, 6_000.0 + 100 * i) for i, q in enumerate(zq)]          # 2026-04-01 = 6,900 · 1년 전 6,500
    S["BOGZ1FL313161275Q"] = [(q, 22_000.0) for q in zq]
    return S


class FakeFred:
    def __init__(self, data, fail=(), cache=()):
        self.data, self.fail, self.cache, self.calls = data, set(fail), set(cache), []

    def __call__(self, sid, cache_dir, offline=False, timeout=None):
        self.calls.append((sid, timeout))
        if sid in self.fail:
            raise RuntimeError(f"{sid}: 원문 사유 https://bad.invalid/xyz-77")
        return list(self.data[sid]), ("cache" if sid in self.cache else "net")


def line_numbers(line):
    """지준 줄의 보이는 정수 — [지준 변화, TGA, 역레포, 단기채, 이표채, 그 밖]. 줄 끝의 부호 안내는 떼고 읽는다."""
    assert line.endswith(" " + liq.SIGN_NOTE), line
    head, rest = line[:-len(liq.SIGN_NOTE) - 1].split(" = ", 1)
    nums = [int(x.replace(",", "")) for x in re.findall(r"(?<![\d-])([+-]?[\d,]+)(?=bn \()", head)]
    nums += [int(x.replace(",", "")) for x in re.findall(r" ([+-]?[\d,]+)(?= ·|$)", rest)]
    return nums


class ArithmeticTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.S = world()

    def test_reserves_decomposition_adds_up(self):
        c = liq.calc_reserves(self.S)
        v = c["values"]
        self.assertEqual((c["date"], v["from"]), ("2026-10-28", "2026-07-29"))
        want = {"res": -95, "tga": -110, "rrp": 19, "bills": 57, "coupons": -3, "other": -58}
        for k, w in want.items():
            self.assertAlmostEqual(v[k], w, msg=k)
        self.assertAlmostEqual(v["tga"] + v["rrp"] + v["bills"] + v["coupons"] + v["other"], v["res"])
        self.assertEqual((v["res_level"], v["tga_level"]), (3005.0, 910.0))
        line, extra = liq.texts("reserves", v, c["date"])
        self.assertEqual(line, "지준 13주 변화 -95bn (2026-07-29~2026-10-28, 수요일) = 재무부 현금(TGA) -110 · "
                               "역레포(해외 공적 포함) +19 · 연준 단기채 +57 · 연준 이표채 -3 · 그 밖 -58 (부호는 지준 쪽)")
        self.assertEqual(line_numbers(line), [-95, -110, 19, 57, -3, -58])
        self.assertEqual(line.count("(부호는 지준 쪽)"), 1)                      # 숫자 사이가 아니라 줄 끝에 한 번
        self.assertTrue(extra[0].startswith("2026-10-28 지준 3,005bn · 재무부 현금(TGA) 910bn."), extra[0])

    def test_reserves_uses_the_last_common_wednesday(self):
        S = dict(self.S, WSHOBL=self.S["WSHOBL"][:-1])                         # 단기채가 한 주 늦다
        c = liq.calc_reserves(S)
        self.assertEqual((c["date"], c["values"]["from"]), ("2026-10-21", "2026-07-22"))

    def test_reserves_needs_an_observation_near_91_days_before(self):
        d1 = D(2026, 10, 28)
        for gap, ok in ((6, True), (7, False)):
            old = d1 - datetime.timedelta(days=91 + gap)
            S = {sid: [(old, 1000.0), (d1, 2000.0)] for sid in liq.BS.values()}
            if ok:
                self.assertEqual(liq.calc_reserves(S)["values"]["from"], old.isoformat())
            else:
                with self.assertRaises(liq.ItemError) as e:
                    liq.calc_reserves(S)
                self.assertEqual(e.exception.code, "format")
        S = {sid: [(d1 - datetime.timedelta(days=90), 1.0), (d1, 2.0)] for sid in liq.BS.values()}   # 91일이 안 된다
        with self.assertRaises(liq.ItemError):
            liq.calc_reserves(S)
        S = dict(self.S, WDTGAL=[(d + datetime.timedelta(days=1), v) for d, v in self.S["WDTGAL"]])   # 공통 날짜가 없다
        with self.assertRaises(liq.ItemError):
            liq.calc_reserves(S)

    def test_shown_numbers_add_up_even_when_each_rounds_away(self):
        base = liq.calc_reserves(self.S)["values"]
        cases = [dict(res=-0.6, tga=0.4, rrp=0.4, bills=0.4, coupons=0.4, other=-2.2),      # 각자 반올림하면 0+0+0+0−2 ≠ −1
                 dict(res=10.5, tga=2.5, rrp=3.5, bills=-0.5, coupons=1.5, other=3.5),     # 반올림이 짝수 쪽으로
                 dict(res=1234.4, tga=-1100.6, rrp=0.49, bills=2000.51, coupons=-0.5, other=334.44)]
        for case in cases:
            v = dict(base, **case)
            nums = line_numbers(liq.texts("reserves", v, "2026-10-28")[0])
            self.assertEqual(len(nums), 6, nums)
            self.assertEqual(sum(nums[1:]), nums[0], (case, nums))
            self.assertEqual(nums[0], round(case["res"]))
        line = liq.texts("reserves", dict(base, **cases[0]), "2026-10-28")[0]
        self.assertIn("그 밖 -1", line)
        self.assertIn("지준 13주 변화 -1bn", line)
        line = liq.texts("reserves", dict(base, **cases[2]), "2026-10-28")[0]
        self.assertIn("지준 13주 변화 +1,234bn", line)

    def test_rule_matches_the_regime_check(self):
        for wres, gdp in ((self.S["WRESBAL"], self.S["GDP"]),
                          ([(d, 2_950_000.0 + 7 * i) for i, d in enumerate(wednesdays(D(2026, 1, 7), D(2026, 10, 21)))],
                           [(D(2026, 1, 1), 31_234.5), (D(2026, 4, 1), 32_100.25)])):
            S = {"WRESBAL": wres, "GDP": gdp}
            ind, _, _ = rc.compute(S, D(2026, 10, 30))
            c = liq.calc_rule(S)
            want = ind["reserves_gdp"]
            self.assertEqual(c["date"], want["asof"])
            self.assertEqual(c["values"]["gdp_quarter"], want["gdp_quarter"])
            self.assertAlmostEqual(c["values"]["value"], want["value"], places=4)
            self.assertEqual(c["values"]["low"], rr.TH["reserves_gdp_low"])
            self.assertAlmostEqual(c["values"]["gap_pp"], want["value"] - rr.TH["reserves_gdp_low"], places=4)
            self.assertAlmostEqual(c["values"]["gap_bn"], (want["value"] - rr.TH["reserves_gdp_low"]) / 100 * gdp[-1][1],
                                   places=3)
            self.assertEqual(c["values"]["gdp_bn"], gdp[-1][1])

    def test_rule_line(self):
        c = liq.calc_rule(self.S)
        v = c["values"]
        self.assertAlmostEqual(v["value"], 8.8)
        self.assertAlmostEqual(v["gap_bn"], -66.0)
        line, extra = liq.texts("rule", v, c["date"])
        self.assertEqual(line, "지준/명목GDP 8.80% (2026-10-28, GDP 2026Q3) · 규칙 하한 9.0% 대비 -0.20%p ≈ -66bn")
        self.assertIn("2026Q3 33,000bn", extra[0])
        line, _ = liq.texts("rule", dict(v, value=9.004, gap_pp=0.004, gap_bn=1.3), c["date"])
        self.assertIn("대비 0.00%p ≈ +1bn", line)                                   # 반올림해 0이면 부호 없이

    def test_fiscal(self):
        c = liq.calc_fiscal(self.S)
        v = c["values"]
        self.assertEqual(c["date"], "2026-09-01")
        self.assertAlmostEqual(v["sum12"], -1920)
        self.assertAlmostEqual(v["sum12_1y"], -1800)
        self.assertAlmostEqual(v["sum12_gdp"], -1920 / 33_000 * 100, places=4)
        self.assertAlmostEqual(v["interest_gdp"], 1260 / 33_000 * 100, places=4)
        self.assertAlmostEqual(v["bills_share"], 6900 / 28_900 * 100, places=4)
        self.assertAlmostEqual(v["bills_share_1y"], 6500 / 28_500 * 100, places=4)
        self.assertEqual((v["deficit_to"], v["interest_q"], v["bills_q"], v["gdp_quarter"]),
                         ("2026-09-01", "2026-07-01", "2026-04-01", "2026-07-01"))
        line, _ = liq.texts("fiscal", v, c["date"])
        self.assertEqual(line, "재정수지 12개월 합 -1,920bn (~2026-09, GDP의 5.8%) (1년 전 -1,800bn) · 연방 이자 지출 "
                               "1,260bn 연율(2026Q3, GDP의 3.8%) · 시장성 국채 중 단기채 23.9% (2026Q2, 1년 전 22.8%)")

    def test_fiscal_sum_needs_exactly_twelve_months(self):
        m = self.S["MTSDS133FMS"]
        S = dict(self.S, MTSDS133FMS=[p for p in m if p[0] != D(2025, 10, 1)])        # 이번 12개월의 첫 달이 빠졌다
        v = liq.calc_fiscal(S)["values"]
        self.assertIsNone(v["sum12"])
        self.assertIsNone(v["sum12_gdp"])
        self.assertAlmostEqual(v["sum12_1y"], -1800)
        line, _ = liq.texts("fiscal", v, "2026-09-01")
        self.assertTrue(line.startswith("재정수지 12개월 합: 12개 달이 다 있지 않음(~2026-09) · 연방 이자 지출"), line)
        S = dict(self.S, MTSDS133FMS=[p for p in m if p[0] != D(2025, 9, 1)])         # 1년 전 12개월의 마지막 달
        v = liq.calc_fiscal(S)["values"]
        self.assertAlmostEqual(v["sum12"], -1920)
        self.assertIsNone(v["sum12_1y"])
        self.assertNotIn("1년 전 —bn", liq.texts("fiscal", v, "2026-09-01")[0])
        self.assertNotIn("(1년 전", liq.texts("fiscal", v, "2026-09-01")[0])

    def test_interest_needs_gdp_of_the_same_quarter(self):
        S = dict(self.S, GDP=self.S["GDP"][:-1])                                    # GDP는 2026Q2까지, 이자는 2026Q3
        v = liq.calc_fiscal(S)["values"]
        self.assertIsNone(v["interest_gdp"])
        self.assertEqual(v["gdp_quarter"], "2026-04-01")
        self.assertAlmostEqual(v["sum12_gdp"], -1920 / 32_500 * 100, places=4)     # 12개월 합은 마지막 분기 GDP로
        line, _ = liq.texts("fiscal", v, "2026-09-01")
        self.assertIn("연방 이자 지출 1,260bn 연율(2026Q3) · ", line)

    def test_bills_share_uses_the_last_common_quarter(self):
        S = dict(self.S, BOGZ1FL313161275Q=self.S["BOGZ1FL313161275Q"][:-1])        # 그 밖 국채가 한 분기 늦다
        v = liq.calc_fiscal(S)["values"]
        self.assertEqual(v["bills_q"], "2026-01-01")
        self.assertAlmostEqual(v["bills_share"], 6800 / 28_800 * 100, places=4)
        self.assertAlmostEqual(v["bills_share_1y"], 6400 / 28_400 * 100, places=4)
        S = dict(self.S, BOGZ1FL313161110Q=[p for p in self.S["BOGZ1FL313161110Q"] if p[0] != D(2025, 4, 1)])
        v = liq.calc_fiscal(S)["values"]
        self.assertIsNone(v["bills_share_1y"])                                      # 네 분기 앞이 없으면 비운다(다른 분기로 대신하지 않는다)
        self.assertIn("(2026Q2, 1년 전 —)", liq.texts("fiscal", v, "2026-09-01")[0])
        S = dict(self.S, BOGZ1FL313161275Q=[(D(2020, 1, 1), 1.0)])                   # 겹치는 분기가 없다
        v = liq.calc_fiscal(S)["values"]
        self.assertEqual((v["bills_share"], v["bills_q"]), (None, None))
        self.assertNotIn("단기채", liq.texts("fiscal", v, "2026-09-01")[0])

    def test_observations_after_today_are_dropped(self):
        S = dict(self.S, WDTGAL=self.S["WDTGAL"] + [(D(2026, 11, 4), 999_999.0)],
                 MTSDS133FMS=self.S["MTSDS133FMS"] + [(D(2026, 11, 1), -1.0)])
        out = liq.compute({k: v for k, v in S.items()}, {}, NOW.date())
        self.assertEqual(out["reserves"]["date"], "2026-10-28")
        self.assertEqual(out["fiscal"]["values"]["deficit_to"], "2026-09-01")

    def test_wording(self):
        self.assertFalse([r for r in liq.REASONS.values() if "(" in r or ")" in r])   # '미수신(까닭)'이 겹 괄호가 되지 않게
        self.assertEqual(liq._s(-0.4), "0")
        self.assertEqual(liq._s(0.004, 2), "0.00")
        self.assertEqual(liq._s(-1234.5), "-1,234")
        self.assertEqual(liq._q("2026-10-01"), "2026Q4")

    def test_every_item_computes_and_texts_have_no_verdict_words(self):
        core = liq.compute(self.S, {}, NOW.date())
        for spec in liq.ITEMS:
            c = core[spec["key"]]
            self.assertNotIsInstance(c, liq.ItemError, spec["key"])
            self.assertEqual(set(c["values"]), set(spec["values"]), spec["key"])
            line, extra = liq.texts(spec["key"], c["values"], c["date"])
            for t in [line, *extra, spec["title"], liq.NOTICE, liq.COMPUTED_NOTICE]:
                self.assertNotIn("None", t)
                body = t
                for ok in TOPIC:
                    body = body.replace(ok, "")
                for word in list(FORBIDDEN_TEXT) + list(VERDICT):
                    self.assertNotIn(word, body, (spec["key"], word))


class LicenceTest(unittest.TestCase):
    def test_series_list_is_fixed_and_public(self):
        self.assertEqual(set(liq.SERIES), {"WRBWFRBL", "WDTGAL", "WLRRAL", "WSHOBL", "WSHONBNL", "WRESBAL", "GDP",
                                           "MTSDS133FMS", "A091RC1Q027SBEA", "BOGZ1FL313161110Q", "BOGZ1FL313161275Q"})
        self.assertEqual(set(liq.LICENCE), set(liq.SERIES))
        self.assertEqual(set(liq.LICENCE.values()), {"public-domain"})
        self.assertFalse(set(liq.SERIES) & (set(rp.RESTRICTED) | set(ai.RESTRICTED)))
        for spec in liq.ITEMS:
            self.assertLessEqual(set(spec["series"]), set(liq.SERIES))
        self.assertEqual(liq.SOURCES["WRESBAL"], (rp.FRED_SOURCE["WRESBAL"], rp.FRED_TITLE["WRESBAL"]))   # 규칙 카드와 같은 인용

    def test_citation_form(self):
        c = liq.citation("MTSDS133FMS", "2026-10-30")
        self.assertEqual(c, "U.S. Department of the Treasury. Fiscal Service, Federal Surplus or Deficit [-] [MTSDS133FMS], "
                            "retrieved from FRED, Federal Reserve Bank of St. Louis; "
                            "https://fred.stlouisfed.org/series/MTSDS133FMS, October 30, 2026.")


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.out = os.path.join(self.tmp, "data")
        self.work = os.path.join(self.tmp, ".work")
        self.path = os.path.join(self.out, liq.FILE)
        self.S = world()

    def run_main(self, fred=None, now=NOW, extra=(), clock=None):
        fred = fred or FakeFred(self.S)
        buf = io.StringIO()
        kw = {"clock": clock} if clock else {}
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = liq.main(["--out", self.out, "--work", self.work, *extra], fred_load=fred, now=now, **kw)
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
        self.assertEqual(js["order"], [s["key"] for s in liq.ITEMS])
        for key, it in js["items"].items():
            self.assertTrue(it["ok"], key)
            self.assertEqual(set(it), {"ok", "stale", "error", "failed_since", "key", "name", "date", "values", "retrieved",
                                       "line", "extra", "notices", "sources"})
            self.assertEqual(it["retrieved"], "2026-10-30")
            self.assertEqual(it["notices"], [liq.COMPUTED_NOTICE])
            self.assertEqual([s["series"] for s in it["sources"]], liq.BY_KEY[key]["series"])
            for src in it["sources"]:
                self.assertEqual(src["licence"], "public-domain")
                self.assertTrue(src["citation"].startswith(liq.SOURCES[src["series"]][0]))
                self.assertTrue(src["citation"].endswith("October 30, 2026."))
        self.assertNotIn("-95", log)                                               # 로그에는 날짜와 사유만

    def test_one_missing_series_only_stales_its_items(self):
        self.run_main()
        code, log = self.run_main(fred=FakeFred(self.S, fail={"WDTGAL"}), now=NOW + datetime.timedelta(days=1))
        self.assertEqual(code, 0, log)
        items = self.saved()["items"]
        r = items["reserves"]
        self.assertEqual((r["ok"], r["stale"], r["error"], r["failed_since"]), (False, True, liq.REASONS["fetch"], "2026-10-31"))
        self.assertEqual(r["retrieved"], "2026-10-30")
        self.assertIn("재무부 현금(TGA) -110", r["line"])                            # 직전 숫자에서 다시 만든 문구
        self.assertTrue(items["rule"]["ok"] and items["fiscal"]["ok"])
        self.assertIn("::warning::지준·재정 참고 reserves 받지 못함", log)
        self.assertNotIn("xyz-77", log)
        self.run_main(fred=FakeFred(self.S, fail={"GDP"}), now=NOW + datetime.timedelta(days=2))
        items = self.saved()["items"]
        self.assertEqual({k for k, it in items.items() if not it["ok"]}, {"rule", "fiscal"})
        self.assertEqual(items["reserves"]["failed_since"], None)                   # 다시 받으면 실패 날짜가 지워진다
        self.run_main(fred=FakeFred(self.S, fail={"GDP"}), now=NOW + datetime.timedelta(days=3))
        self.assertEqual(self.saved()["items"]["rule"]["failed_since"], "2026-11-01")   # 못 받기 시작한 날을 지킨다

    def test_first_failure_without_previous_has_no_numbers(self):
        self.run_main(fred=FakeFred(self.S, cache={"MTSDS133FMS"}))
        it = self.saved()["items"]["fiscal"]
        self.assertEqual((it["ok"], it["stale"], it["error"]), (False, False, liq.REASONS["cache"]))
        self.assertNotIn("line", it)
        self.assertNotIn("values", it)
        self.assertEqual([s["series"] for s in it["sources"]], liq.BY_KEY["fiscal"]["series"])

    def test_offline_reads_the_cache(self):
        cache = os.path.join(self.work, liq.CACHE)
        os.makedirs(cache)
        for sid, s in self.S.items():
            with open(os.path.join(cache, f"{sid}.csv"), "w", encoding="utf-8") as f:
                f.write("observation_date," + sid + "\n" + "".join(f"{d.isoformat()},{v}\n" for d, v in s))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), mock.patch.object(ai.urllib.request, "urlopen", side_effect=AssertionError("요청")):
            code = liq.main(["--out", self.out, "--work", self.work, "--offline"], now=NOW)
        self.assertEqual(code, 0, buf.getvalue())
        items = self.saved()["items"]
        self.assertTrue(all(it["ok"] for it in items.values()))
        self.assertAlmostEqual(items["reserves"]["values"]["other"], -58)

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
            sid = url.split("id=")[1]
            seen.append((sid, timeout))
            return Resp(bodies[sid])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = liq.main(["--out", self.out, "--work", self.work], now=NOW, opener=opener)
        self.assertEqual(code, 0, buf.getvalue())
        self.assertEqual([s for s, _ in seen], liq.SERIES)
        self.assertTrue(all(0 < t <= ai.TIMEOUT for _, t in seen))
        self.assertTrue(os.path.exists(os.path.join(self.work, liq.CACHE, "WRBWFRBL.csv")))

    def test_older_data_is_not_taken(self):
        self.run_main()
        short = dict(self.S, MTSDS133FMS=self.S["MTSDS133FMS"][:-1])
        self.run_main(fred=FakeFred(short), now=NOW + datetime.timedelta(days=1))
        it = self.saved()["items"]["fiscal"]
        self.assertEqual((it["ok"], it["stale"], it["error"]), (False, True, liq.REASONS["older"]))
        self.assertEqual(it["values"]["deficit_to"], "2026-09-01")
        short = dict(self.S, BOGZ1FL313161110Q=self.S["BOGZ1FL313161110Q"][:-1])  # 칸 날짜는 그대로, 단기채 분기만 이르다
        self.run_main(fred=FakeFred(short), now=NOW + datetime.timedelta(days=2))
        self.assertEqual(self.saved()["items"]["fiscal"]["error"], liq.REASONS["older"])
        short = dict(self.S, GDP=self.S["GDP"][:-1])
        self.run_main(fred=FakeFred(short), now=NOW + datetime.timedelta(days=3))
        self.assertEqual(self.saved()["items"]["rule"]["error"], liq.REASONS["older"])

    def test_same_numbers_keep_the_file(self):
        self.run_main()
        with open(self.path, "rb") as f:
            first = f.read()
        self.run_main(now=NOW + datetime.timedelta(days=1))
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), first)

    def test_new_numbers_get_a_new_retrieved_date(self):
        self.run_main()
        S = dict(self.S, WDTGAL=self.S["WDTGAL"] + [(D(2026, 11, 4), 905_000.0)])
        for sid in ("WRBWFRBL", "WLRRAL", "WSHOBL", "WSHONBNL"):
            S[sid] = self.S[sid] + [(D(2026, 11, 4), self.S[sid][-1][1])]
        self.run_main(fred=FakeFred(S), now=datetime.datetime(2026, 11, 6, 1, 30, tzinfo=datetime.timezone.utc))
        items = self.saved()["items"]
        self.assertEqual((items["reserves"]["date"], items["reserves"]["retrieved"]), ("2026-11-04", "2026-11-06"))
        self.assertEqual(items["fiscal"]["retrieved"], "2026-10-30")                # 같은 숫자는 처음 받은 날 그대로

    def test_a_broken_previous_file_is_not_carried(self):
        self.run_main()
        js = self.saved()
        js["items"]["fiscal"]["values"]["bills_q"] = "어제"                         # 날짜 꼴이 아니다
        js["items"]["rule"]["values"]["extra"] = 1.0                               # 모르는 값
        js["items"]["reserves"]["values"]["res"] = "9"                             # 숫자가 아니다
        self.save(js)
        self.run_main(fred=FakeFred(self.S, fail=set(self.S)), now=NOW + datetime.timedelta(days=1))
        items = self.saved()["items"]
        for key in ("fiscal", "rule", "reserves"):
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
        self.save(js)
        self.run_main(fred=FakeFred(self.S, fail=set(self.S)), now=NOW + datetime.timedelta(days=1))
        dump = json.dumps(self.saved(), ensure_ascii=False)
        for bad in ("bad.invalid", "매수", "바깥 글", "바뀐 이름"):
            self.assertNotIn(bad, dump)
        self.assertTrue(all(it["stale"] for it in self.saved()["items"].values()))

    def test_previous_checks_the_schema(self):
        good = {"reserves": {"key": "reserves"}, "rule": {"key": "rule"}}
        os.makedirs(self.out)
        for js, want in (({"schema": liq.SCHEMA, "items": good}, good),
                         ({"schema": liq.SCHEMA + 1, "items": good}, {}),
                         ({"items": good}, {}),
                         ({"schema": liq.SCHEMA, "items": [good]}, {}),
                         ([good], {}),
                         ({"schema": liq.SCHEMA, "items": dict(good, zzz={"key": "zzz"}, fiscal="x")}, good)):
            self.save(js)
            self.assertEqual(liq.previous(self.out), want, js)
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{깨진")
        self.assertEqual(liq.previous(self.out), {})

    def test_budget_runs_out_without_waiting(self):
        t = [0.0]

        def clock():
            t[0] += 30.0
            return t[0]
        fred = FakeFred(self.S)
        code, log = self.run_main(fred=fred, clock=clock)
        self.assertLess(len(fred.calls), len(liq.SERIES))
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
            S = dict(self.S, WRESBAL=[(d, v + 1000) for d, v in self.S["WRESBAL"]])
            code, log = self.run_main(fred=FakeFred(S), now=NOW + datetime.timedelta(days=1))
        self.assertEqual(code, 1, log)
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), before)
        self.assertEqual(os.listdir(self.out), [liq.FILE])

    def test_every_string_is_fixed_text_without_verdict_words(self):
        runs = [(FakeFred(self.S, fail={"A091RC1Q027SBEA"}), NOW),                   # 직전 값 없는 첫 실패
                (FakeFred(self.S), NOW + datetime.timedelta(days=1)),
                (FakeFred(self.S, fail={"WRESBAL", "WSHOBL"}), NOW + datetime.timedelta(days=2)),   # 직전 값을 이어 싣는 실패
                (FakeFred(self.S, cache={"GDP"}), NOW + datetime.timedelta(days=3))]
        urls, errors = set(), set()
        for fred, now in runs:                                                     # 실행마다 파일 전체를 본다
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
            nested = re.compile(r"\([^()]*\(")
            for t in re.findall(r'"((?:[^"\\]|\\.)*)"', dump):
                self.assertIsNone(nested.search(t), t)
        self.assertEqual(urls, {f"https://fred.stlouisfed.org/series/{sid}" for sid in liq.SERIES})
        self.assertEqual(errors, {liq.REASONS["fetch"], liq.REASONS["cache"]})        # 정해 둔 문구만


class StaticTest(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
            return f.read()

    def test_workflow_fetches_without_failing_the_run(self):
        wf = self.read(".github", "workflows", "daily.yml")
        self.assertTrue("id: liquidity" in wf, "daily.yml에 지준·재정 단계(id: liquidity) 없음")
        step = wf[wf.index("id: liquidity"):]
        self.assertIn("continue-on-error: true", step[:200])
        self.assertIn("timeout-minutes: 2", step[:200])
        self.assertIn("python scripts/liquidity_fetch.py", step[:300])
        self.assertLess(wf.index("id: liquidity"), wf.index("공개 전 검사(새 산출물 포함)"))
        self.assertLess(wf.index("id: liquidity"), wf.index("git add data"))
        self.assertNotIn("liquidity", wf[wf.index("\n  alert:"):])               # 실패해도 알림을 띄우지 않는다
        self.assertIn("node --test scripts/test_liquidity_render.cjs", wf[wf.index("\n  check:"):wf.index("\n  update:")])

    def test_readme_counts(self):
        readme = self.read("README.md")
        m = re.search(r"\*\*아침 쪽 Python 테스트 (\d+)개 \+ node 테스트 (\d+)개\*\*\((.*?)\)와 \*\*저녁판", readme)
        py_part, node_part = m.group(3).split(" / node: ")
        mine = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()
        self.assertRegex(py_part, rf"(^| · )지준·재정 참고 {mine}( · |$)")
        cjs = len(re.findall(r"^test\(", self.read("scripts", "test_liquidity_render.cjs"), flags=re.M))
        self.assertRegex(node_part, rf"(^| · )지준·재정 카드 그리기 {cjs}( · |$)")

    def test_page_wires_the_card(self):
        page = self.read("site", "index.html")
        for snippet in ('getJson("data/liquidity.json")', '<script src="liquidity.js"></script>',
                        '<a href="data/liquidity.json">', 'id:"liquidity-slot"', "window.LiquidityCard.render("):
            self.assertTrue(snippet in page, f"index.html에 {snippet} 없음")
        group = page[page.index('g.id === "liquidity"'):][:200]                    # 유동성 묶음 안
        self.assertIn('id:"liquidity-slot"', group)

    def test_card_intro_is_one_register_and_covers_the_notice(self):
        # 머리 안내는 합니다체 ABOUT 하나 — 자료 파일의 notice(한다체)를 겹쳐 싣지 않고, notice의 뜻은 ABOUT이 모두 담는다
        js = self.read("site", "liquidity.js")
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        self.assertNotIn("d.notice", code)
        self.assertIn('el("p", { class: "muted" }, ABOUT)', code)
        about = "".join(re.findall(r'"([^"]*)"', code[code.index("const ABOUT = "):].split(";\n", 1)[0]))
        for sent in filter(None, re.split(r"(?<=\.)\s+", about)):
            self.assertTrue(sent.endswith("니다."), sent)
        for mine, theirs in (("규칙 수에 들지 않습니다", "규칙 점검에 쓰지 않는"),
                             ("'지준과 통화승수'의 지준/GDP가 왜 움직였는지 읽는 재료", "'지준과 통화승수'의 지준/GDP가 왜 움직였는지 읽는"),
                             ("공개 통계와 그 산술", "공개 통계로 계산한 산술"),
                             ("금리나 자금 여건을 예측하지 않습니다", "금리나 자금 여건을 예측하지 않는다")):
            self.assertIn(mine, about)
            self.assertIn(theirs, liq.NOTICE)

    def test_screen_script_matches_the_file_and_avoids_verdict_words(self):
        js = self.read("site", "liquidity.js")
        card = re.findall(r'"(\w+)"', js[js.index("const CARD = ["):].split("]")[0])
        self.assertEqual(card, [s["key"] for s in liq.ITEMS])
        reasons = re.findall(r'"([^"]+)"', js[js.index("const REASONS = ["):].split("];")[0])
        self.assertEqual(reasons, list(liq.REASONS.values()))
        self.assertIn('const LABEL = "참고 — 판정 없음";', js)
        for tok in ("innerHTML", "outerHTML", "insertAdjacentHTML", "createElement", "fetch(", "eval(", "location.",
                    "localStorage"):
            self.assertNotIn(tok, js)
        body = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S).replace("참고 — 판정 없음", "")
        for ok in TOPIC:
            body = body.replace(ok, "")
        for word in list(FORBIDDEN_TEXT) + list(VERDICT):
            self.assertNotIn(word, body, word)
        self.assertIn('getElementById("liquidity-slot")', js)
        self.assertIn("window.LiquidityCard = ", js)


if __name__ == "__main__":
    unittest.main(verbosity=1)
