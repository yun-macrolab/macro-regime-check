#!/usr/bin/env python3
"""수급 참고 자료(supply_fetch) 테스트 — 너그러운 딜러 응답 읽기, 계산, 한쪽 실패·직전 값 이어 싣기, 원자적 쓰기, 종료코드.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — 뉴욕 연은 응답은 지어낸 JSON(형식은 이 저장소에서 확인하지 못해 여러 꼴로), FRED는 가짜 loader 또는
합성 캐시(--offline). 숫자는 모두 지어낸 것이다.
"""
import os, sys, io, re, json, math, datetime, tempfile, unittest, shutil, contextlib
from unittest import mock

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import supply_fetch as sf
from test_render_public import FORBIDDEN_TEXT

REPO = os.path.dirname(SCRIPTS)
D = datetime.date
NOW = datetime.datetime(2026, 10, 14, 1, 30, tzinfo=datetime.timezone.utc)
SPEC_KEYS = {"key", "title", "unit", "years", "zero", "threshold", "note", "source_note", "notices", "lines"}
LINE_KEYS = {"key", "label", "role", "series", "derived", "points"}


def wednesdays(start=D(2015, 1, 7), end=D(2026, 9, 30)):
    out, d = [], start
    while d <= end:
        out.append(d)
        d += datetime.timedelta(days=7)
    return out


def dealer_series(end=D(2026, 9, 30)):
    """[(date, 백만 달러)] — 지어낸 주간 딜러 순포지션(약 100~500십억 달러)."""
    return [(w, 300000 + 150000 * math.sin(i / 23) + 40 * i) for i, w in enumerate(wednesdays(end=end))]


def custody_series(end=D(2026, 10, 7)):
    return [(w, 3000000 - 300 * i + 20000 * math.sin(i / 9)) for i, w in enumerate(wednesdays(end=end))]


def pd_json(series, key=sf.PD_KEY, **extra):
    """문서로 보는 꼴 {"pd": {"timeseries": [{asofdate, keyid, value(글자)}]}} — 실제 형식은 확인하지 못했다."""
    rows = [{"asofdate": d.isoformat(), "keyid": key, "value": f"{v:.0f}", **extra} for d, v in series]
    return json.dumps({"pd": {"timeseries": rows}})


class Resp(io.BytesIO):
    def __init__(self, body, final):
        super().__init__(body)
        self.final = final

    def geturl(self):
        return self.final

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeOpener:
    """urlopen 대역 — 정해 둔 본문을 돌려주고 부른 주소를 적는다. error를 주면 그 예외."""
    def __init__(self, body="", final=None, error=None):
        self.body, self.final, self.error, self.calls = body, final, error, []

    def __call__(self, url, timeout=None):
        self.calls.append((url, timeout))
        if self.error:
            raise self.error
        return Resp(self.body.encode("utf-8") if isinstance(self.body, str) else self.body, self.final or url)


class FakeFred:
    """fred_fetch.load 대역 — (시계열, 'net'|'cache') 또는 예외."""
    def __init__(self, series=None, src="net", error=None):
        self.series, self.src, self.error, self.calls = series, src, error, []

    def __call__(self, sid, cache_dir, offline=False, timeout=None):
        self.calls.append((sid, offline))
        if self.error:
            raise self.error
        return list(self.series), self.src


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)


# ---------- 딜러 응답 읽기 ----------

class ParsePdTest(unittest.TestCase):
    def test_reads_the_documented_shape_in_billions(self):
        s = sf.parse_pd(pd_json([(D(2026, 9, 23), 455000), (D(2026, 9, 30), 432100)]))
        self.assertEqual(s, [(D(2026, 9, 23), 455.0), (D(2026, 9, 30), 432.1)])

    def test_other_keys_are_dropped_and_key_case_does_not_matter(self):
        rows = [{"asofdate": "2026-09-30", "keyid": "PDPOSGS-B", "value": "999999"},          # 단기채만 — 합계가 아니다
                {"asofdate": "2026-09-30", "keyid": "pdposgst-tot", "value": "432100"},
                {"asofdate": "2026-09-23", "keyid": "PDPOSTIPS-TOT", "value": "1"}]
        self.assertEqual(sf.parse_pd(json.dumps({"pd": {"timeseries": rows}})), [(D(2026, 9, 30), 432.1)])

    def test_confidential_and_non_numeric_values_are_skipped(self):
        rows = [{"asofdate": f"2026-09-{d:02d}", "keyid": sf.PD_KEY, "value": v}
                for d, v in ((2, "*"), (9, ""), (16, "N/A"), (23, None), (24, True), (25, "1e9"), (30, "432,100"))]
        rows.append({"asofdate": "2026-09-01", "keyid": sf.PD_KEY, "value": -12000})          # 숫자 그대로도
        self.assertEqual(sf.parse_pd(json.dumps(rows)), [(D(2026, 9, 1), -12.0), (D(2026, 9, 30), 432.1)])

    def test_the_newest_series_break_wins_on_the_same_day(self):
        rows = [{"asofdate": "2026-09-30", "keyid": sf.PD_KEY, "seriesbreak": "SBN2024", "value": "432100"},
                {"asofdate": "2026-09-30", "keyid": sf.PD_KEY, "seriesbreak": "SBN2013", "value": "100000"},
                {"asofdate": "2022-12-28", "keyid": sf.PD_KEY, "seriesbreak": "SBN2013", "value": "150000"},
                {"asofdate": "2022-12-28", "keyid": sf.PD_KEY, "value": "1"}]                   # 구분 없는 기록은 가장 낮다
        self.assertEqual(sf.parse_pd(json.dumps(rows)), [(D(2022, 12, 28), 150.0), (D(2026, 9, 30), 432.1)])

    def test_key_and_break_are_inherited_from_an_outer_record(self):
        body = {"data": [
            {"keyId": sf.PD_KEY, "seriesBreak": "SBN2022",
             "observations": [{"asOfDate": "2026-09-30", "value": "432100"}, {"asOfDate": "2026-09-23", "value": "*"}]},
            {"keyId": sf.PD_KEY, "seriesBreak": "SBN2015", "observations": [{"asOfDate": "2026-09-30", "value": "5"}]},
            {"keyId": "PDPOSGSC-L2", "observations": [{"asOfDate": "2026-09-16", "value": "7"}]}]}
        self.assertEqual(sf.parse_pd(json.dumps(body)), [(D(2026, 9, 30), 432.1)])

    def test_records_without_a_key_field_belong_to_the_requested_series(self):
        body = {"timeseries": [{"date": "09/30/2026", "value": 432100}, {"date": "2026-09-23T00:00:00", "value": "455000"}]}
        self.assertEqual(sf.parse_pd(json.dumps(body)), [(D(2026, 9, 23), 455.0), (D(2026, 9, 30), 432.1)])

    def test_future_dates_are_dropped(self):
        s = sf.parse_pd(pd_json([(D(2026, 9, 30), 1000), (D(2026, 10, 21), 2000)]), today=D(2026, 10, 14))
        self.assertEqual(s, [(D(2026, 9, 30), 1.0)])

    def test_anything_but_json_reads_as_nothing(self):
        for text in ("", "<html>잠시 후 다시</html>", "asofdate,keyid,value\n2026-09-30,PDPOSGST-TOT,1", "{깨진",
                     json.dumps({"pd": {"timeseries": []}}), json.dumps({"error": "no data"})):
            self.assertEqual(sf.parse_pd(text), [], text)


class FetchTest(unittest.TestCase):
    def test_a_redirect_away_from_the_api_host_is_a_failure(self):
        op = FakeOpener("{}", final="https://example.org/login")
        with self.assertRaises(sf.SideError):
            sf.fetch_text(sf.PD_URL, op)

    def test_an_https_to_http_downgrade_is_a_failure(self):
        op = FakeOpener("{}", final="http://markets.newyorkfed.org/api/pd/get/PDPOSGST-TOT.json")   # 같은 호스트·경로라도
        with self.assertRaises(sf.SideError) as e:
            sf.fetch_text(sf.PD_URL, op)
        self.assertEqual(e.exception.code, "fetch")

    def test_an_oversized_response_is_a_failure(self):
        with mock.patch.object(sf, "MAX_BYTES", 10), self.assertRaises(sf.SideError):
            sf.fetch_text(sf.PD_URL, FakeOpener("x" * 100))

    def test_a_trickling_response_hits_the_overall_budget(self):
        ticks = iter(range(0, 1000, 20))
        with self.assertRaises(sf.SideError):
            sf.fetch_text(sf.PD_URL, FakeOpener("x" * 400000), clock=lambda: next(ticks))

    def test_timeout_is_passed_to_each_request(self):
        op = FakeOpener("{}")
        sf.fetch_text(sf.PD_URL, op)
        self.assertEqual(op.calls, [(sf.PD_URL, sf.TIMEOUT)])


# ---------- 계산 ----------

def bn(series):
    return [(d, v / 1000) for d, v in series]


class StatsTest(unittest.TestCase):
    def test_level_and_changes_follow_change_days(self):
        s = bn(dealer_series())
        core = sf.stats("dealer", s)
        d1, v1 = s[-1]
        base4 = [x for x in s if x[0] <= d1 - datetime.timedelta(days=28)][-1]
        base52 = [x for x in s if x[0] <= d1 - datetime.timedelta(days=364)][-1]
        self.assertEqual(core["date"], "2026-09-30")
        self.assertEqual(core["level_bn"], round(v1, 3))
        self.assertEqual((core["chg_4w_bn"], core["chg_4w_base"]), (round(v1 - base4[1], 3), base4[0].isoformat()))
        self.assertEqual((core["chg_52w_bn"], core["chg_52w_base"]), (round(v1 - base52[1], 3), base52[0].isoformat()))

    def test_quantiles_use_changes_since_2019_and_skip_gaps(self):
        s = bn(dealer_series())
        gap = {D(2021, 3, 3), D(2021, 3, 10), D(2021, 3, 17)}            # 3주 빈 곳 — 그 뒤 몇 주는 28일 전 관측이 멀다
        holed = [x for x in s if x[0] not in gap]
        ch = sf.changes_over(holed)
        expect = []
        for d, v in holed:
            if d < sf.SINCE:
                continue
            base = [x for x in holed if x[0] <= d - datetime.timedelta(days=28)][-1]
            if (d - datetime.timedelta(days=28) - base[0]).days <= 6:
                expect.append(v - base[1])
        self.assertEqual(ch, expect)
        self.assertEqual(len([d for d, _ in holed if d >= sf.SINCE]) - len(ch), 3)   # 빈 곳 뒤 세 주가 빠진다
        q = sf.stats("dealer", holed)["q4w"]
        self.assertEqual(q["n"], len(ch))
        self.assertEqual((q["p5"], q["p50"], q["p95"]),
                         tuple(round(sf.quantile(ch, p), 3) for p in (0.05, 0.5, 0.95)))
        self.assertEqual(q["from"], "2019-01-01")

    def test_quantile_is_linear_interpolation(self):
        self.assertEqual(sf.quantile([4, 1, 3, 2], 0.5), 2.5)
        self.assertAlmostEqual(sf.quantile(list(range(101)), 0.05), 5.0)
        self.assertEqual(sf.quantile([7], 0.95), 7)

    def test_flag_marks_a_4_week_change_beyond_p5_or_p95(self):
        base = [(w, 200.0 + 10 * math.sin(i * 1.7)) for i, w in enumerate(wednesdays(D(2018, 1, 3), D(2026, 9, 2)))]
        for jump, want in ((80.0, "high"), (-80.0, "low"), (0.5, None)):
            s = base + [(D(2026, 9, 30), base[-1][1] + jump)]
            core = sf.stats("dealer", s)
            self.assertEqual(core["flag"], want, jump)
            text = sf.present("dealer", core, "2026-10-14")["flag_text"]
            self.assertEqual(text is None, want is None)
            if text:
                self.assertIn("2019년 이후", text)
                self.assertIn("p95 위" if want == "high" else "p5 아래", text)

    def test_flag_thresholds_are_p95_and_p5_not_p90_or_p10(self):
        base = [(w, 200.0 + 10 * math.sin(i * 1.7)) for i, w in enumerate(wednesdays(D(2018, 1, 3), D(2026, 9, 2)))]
        ch0, q = sf.changes_over(base), sf.quantile
        cases = (((q(ch0, 0.90) + q(ch0, 0.95)) / 2, (0.90, 0.95), None),      # p90과 p95 사이 — 표시 없음
                 (q(ch0, 0.95) + 0.01, (0.95, 0.99), "high"),                   # p95 바로 위
                 ((q(ch0, 0.05) + q(ch0, 0.10)) / 2, (0.05, 0.10), None),       # p5와 p10 사이 — 표시 없음
                 (q(ch0, 0.05) - 0.01, (0.01, 0.05), "low"))                    # p5 바로 아래
        for c, (lo, hi), want in cases:
            s = base + [(D(2026, 9, 30), base[-1][1] + c)]
            ch = sf.changes_over(s)                                             # 마지막 변화까지 든 표본 — stats()와 같다
            last = ch[-1]
            self.assertTrue(q(ch, lo) < last < q(ch, hi), (c, lo, hi))           # 전제: 마지막 4주 변화가 그 두 분위 사이
            self.assertEqual(sf.stats("dealer", s)["flag"], want, (c, lo, hi))

    def test_a_4_week_change_without_a_near_base_is_left_blank(self):
        base = [(w, 200.0 + 10 * math.sin(i * 1.7)) for i, w in enumerate(wednesdays(D(2018, 1, 3), D(2026, 9, 2)))]
        s = [x for x in base if x[0] not in (D(2026, 8, 26), D(2026, 9, 2))] + [(D(2026, 9, 30), base[-1][1] + 80.0)]
        self.assertEqual(sf.ff.change_days(s, 28)["base_date"], D(2026, 8, 19))   # 그대로 두면 6주 변화가 '4주'로(표시까지)
        core = sf.stats("dealer", s)
        self.assertEqual((core["chg_4w_bn"], core["chg_4w_base"], core["flag"]), (None, None, None))
        self.assertIsNotNone(core["chg_52w_bn"])
        self.assertIn("4주 —", sf.present("dealer", core, "2026-10-14")["line"])
        for base_day, want in ((D(2026, 8, 27), (23.0, "2026-08-27")), (D(2026, 8, 26), (None, None))):   # 6일까지만
            core = sf.stats("dealer", [(D(2026, 8, 19), 100.0), (base_day, 110.0), (D(2026, 9, 30), 133.0)])
            self.assertEqual((core["chg_4w_bn"], core["chg_4w_base"]), want, base_day)

    def test_text_rounds_once_from_the_raw_values(self):
        core = sf.stats("dealer", [(D(2026, 8, 26), 400.0), (D(2026, 9, 2), 410.0), (D(2026, 9, 30), 433.46)])
        self.assertEqual((core["level_bn"], core["chg_4w_bn"]), (433.46, 23.46))
        # 소수 첫째 자리로 저장하면 433.5·23.5가 되어 문구가 434bn·+24로 — 원값에서 한 번만 반올림하면 433bn·+23
        self.assertEqual(sf.present("dealer", core, "2026-10-14")["line"], "433bn · 4주 +23 · 52주 —")
        self.assertEqual(core["points"][-1], ["2026-09-30", 433.5])                    # 그래프 점은 소수 첫째 자리

    def test_no_flag_while_the_sample_is_short(self):
        s = [(w, 200.0) for w in wednesdays(D(2026, 6, 3), D(2026, 9, 2))] + [(D(2026, 9, 30), 300.0)]
        core = sf.stats("dealer", s)
        self.assertLess(core["q4w"]["n"], sf.MIN_Q)
        self.assertIsNone(core["flag"])
        self.assertEqual(core["q4w"]["from"], "2026-07-01")                           # 첫 관측 + 28일
        self.assertNotIn("p95", sf.present("dealer", core, "2026-10-14")["line"])     # 표본이 짧으면 분위수를 적지 않는다

    def test_dealer_change_since_end_2022_and_the_paper_figure(self):
        s = [(D(2022, 12, 21), 140.0), (D(2022, 12, 28), 150.0), (D(2023, 1, 4), 160.0), (D(2026, 9, 30), 432.0)]
        core = sf.stats("dealer", s)
        self.assertEqual(core["since_2022"], {"base_date": "2022-12-28", "base_bn": 150.0, "delta_bn": 282.0,
                                              "paper_tfp_bp": round(282 * 0.038, 1)})
        self.assertIsNone(sf.stats("custody", [(d, v * 10) for d, v in s])["since_2022"])   # 수탁에는 없다
        late = [(D(2023, 1, 4), 160.0), (D(2026, 9, 30), 432.0)]                       # 2022년 말 이전 관측이 없으면 비운다
        self.assertIsNone(sf.stats("dealer", late)["since_2022"])

    def test_a_unit_slip_fails_closed(self):
        s = bn(dealer_series())
        with self.assertRaises(sf.SideError) as e:
            sf.stats("dealer", [(d, v / 1000) for d, v in s])                         # 십억 달러 값을 백만 달러로 읽은 경우
        self.assertEqual(e.exception.code, "unit")
        with self.assertRaises(sf.SideError):
            sf.stats("custody", [(d, v * 1000) for d, v in bn(custody_series())])

    def test_chart_points_are_weekly_for_the_last_five_years(self):
        s = bn(custody_series())
        core = sf.stats("custody", s)
        pts = core["points"]
        self.assertEqual(pts[-1], [core["date"], round(s[-1][1], 1)])                # 그래프 점은 소수 첫째 자리
        self.assertGreaterEqual(pts[0][0], "2021-10-07")
        self.assertLessEqual(pts[0][0], "2021-10-14")
        weeks = [D.fromisoformat(p[0]).isocalendar()[:2] for p in pts]
        self.assertEqual(len(weeks), len(set(weeks)))
        self.assertTrue(250 <= len(pts) <= 262)


class PresentTest(unittest.TestCase):
    """2026-10-14 실측(사용자 PC) 숫자로 만든 숫자 묶음 — 문구의 꼴을 본다."""
    DEALER = {"date": "2026-09-30", "level_bn": 432.0, "chg_4w_bn": -23.0, "chg_4w_base": "2026-09-02",
              "chg_52w_bn": 54.0, "chg_52w_base": "2025-10-01",
              "q4w": {"from": "2019-01-01", "n": 400, "p5": -45.0, "p50": 1.0, "p95": 52.0}, "flag": None,
              "since_2022": {"base_date": "2022-12-28", "base_bn": 150.0, "delta_bn": 282.0, "paper_tfp_bp": 10.7},
              "points": [["2026-09-23", 455.0], ["2026-09-30", 432.0]]}
    CUSTODY = {"date": "2026-10-07", "level_bn": 2565.0, "chg_4w_bn": -25.0, "chg_4w_base": "2026-09-09",
               "chg_52w_bn": -212.0, "chg_52w_base": "2025-10-08",
               "q4w": {"from": "2019-01-01", "n": 400, "p5": -53.0, "p50": -6.0, "p95": 43.0}, "flag": None,
               "since_2022": None, "points": [["2026-10-07", 2565.0]]}

    def test_compact_lines(self):
        d = sf.present("dealer", self.DEALER, "2026-10-14")
        c = sf.present("custody", self.CUSTODY, "2026-10-14")
        self.assertEqual(d["line"], "432bn · 4주 -23 (2019년 이후 p5 -45 / p95 +52) · 52주 +54")
        self.assertEqual(c["line"], "2,565bn · 4주 -25 (2019년 이후 p5 -53 / p95 +43) · 52주 -212")
        self.assertEqual(d["extra"][0], "2022년 말 이후 +282bn (기준 2022-12-28 150bn)")
        self.assertTrue(d["extra"][1].startswith("논문 계수 대입 참고값: +282bn × 0.038bp = 약 +10.7bp"))
        self.assertIn("판정에 쓰지 않음", d["extra"][1])
        self.assertEqual(c["extra"], [])

    def test_sign_rounding_has_no_negative_zero(self):
        self.assertEqual([sf._signed(v) for v in (-0.4, 0.4, 0, None, 1234.6, -1234.6)],
                         ["0", "0", "0", "—", "+1,235", "-1,235"])

    def test_chart_follows_the_page_contract(self):
        for kind, core in (("dealer", self.DEALER), ("custody", self.CUSTODY)):
            ch = sf.present(kind, core, "2026-10-14")["chart"]
            self.assertEqual(set(ch), SPEC_KEYS)
            self.assertEqual(set(ch["lines"][0]), LINE_KEYS)
            self.assertEqual((ch["unit"], ch["years"], ch["threshold"], ch["notices"]), ("bn", 5, None, []))
            self.assertEqual(ch["lines"][0]["points"], core["points"])
            self.assertIn(sf.SIDES[kind]["series"], ch["source_note"])
        self.assertIn("via FRED", sf.present("custody", self.CUSTODY, "2026-10-14")["chart"]["source_note"])

    def test_sources_and_notices(self):
        d = sf.present("dealer", self.DEALER, "2026-10-14")
        c = sf.present("custody", self.CUSTODY, "2026-10-14")
        # 뉴욕 연은 기본 출처 형식(© 연도)과 관계없음 고지 — SOFR과 같은 문구
        self.assertIn(sf.rp.nyfed_attribution(2026), d["notices"])
        self.assertIn(sf.rp.NOT_AFFILIATED, d["notices"])
        self.assertTrue(any("not published by the New York Fed" in n for n in d["notices"]))
        self.assertEqual(c["source"]["citation"],
                         "Board of Governors of the Federal Reserve System (US), Memorandum Items: Custody Holdings: "
                         "Marketable U.S. Treasury Securities: Wednesday Level [WMTSECL1], retrieved from FRED, Federal "
                         "Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/WMTSECL1, October 14, 2026.")
        self.assertIn("[PDPOSGST-TOT]", d["source"]["citation"])
        self.assertEqual(d["source"]["api"], sf.PD_URL)


# ---------- 실행 전체 ----------

class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.out = os.path.join(self.tmp, "data")
        self.work = os.path.join(self.tmp, ".work")
        self.path = os.path.join(self.out, "supply.json")

    def run_main(self, opener=None, fred=None, now=NOW, extra=()):
        opener = opener or FakeOpener(pd_json(dealer_series()))
        fred = fred or FakeFred(custody_series())
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = sf.main(["--out", self.out, "--work", self.work, *extra], opener=opener, fred_load=fred, now=now)
        return code, buf.getvalue()

    def saved(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def raw(self):
        with open(self.path, "rb") as f:
            return f.read()

    def test_first_run_writes_both_sides(self):
        code, log = self.run_main()
        self.assertEqual(code, 0, log)
        js = self.saved()
        self.assertEqual(set(js), {"schema", "generated_at", "notice", "dealer", "custody"})
        self.assertEqual((js["dealer"]["date"], js["custody"]["date"]), ("2026-09-30", "2026-10-07"))
        for k in ("dealer", "custody"):
            self.assertEqual((js[k]["ok"], js[k]["stale"], js[k]["error"], js[k]["failed_since"]), (True, False, None, None))
            self.assertEqual(js[k]["retrieved"], "2026-10-14")
        self.assertNotIn(b"\n", self.raw())                                              # 압축 JSON
        self.assertFalse(re.search(r"\d+\.\d+|bn", log))                               # 공개 로그에 값은 찍지 않는다
        self.assertIn("2026-09-30", log)

    def test_one_side_failing_keeps_the_other(self):
        code, log = self.run_main(opener=FakeOpener(error=OSError("timed out")))
        self.assertEqual(code, 0, log)                                                 # 한쪽이라도 받았으면 0
        js = self.saved()
        self.assertEqual((js["dealer"]["ok"], js["dealer"]["stale"], js["dealer"]["error"]), (False, False, "수신 실패"))
        self.assertNotIn("line", js["dealer"])                                         # 직전 값이 없으면 숫자도 없다
        self.assertEqual(js["dealer"]["failed_since"], "2026-10-14")
        self.assertTrue(js["custody"]["ok"])
        self.assertNotIn("timed out", json.dumps(js, ensure_ascii=False) + log)        # 예외 원문은 싣지 않는다

    def test_a_failed_side_carries_its_previous_values_as_stale(self):
        self.run_main()
        first = self.saved()["dealer"]
        later = NOW + datetime.timedelta(days=1)
        code, _ = self.run_main(opener=FakeOpener("<html>점검 중</html>"), now=later)
        self.assertEqual(code, 0)
        d = self.saved()["dealer"]
        self.assertEqual((d["ok"], d["stale"], d["error"], d["failed_since"]),
                         (False, True, sf.REASONS["format"], "2026-10-15"))
        for k in ("date", "level_bn", "line", "chart", "retrieved", "notices", "extra"):
            self.assertEqual(d[k], first[k], k)
        code, _ = self.run_main(opener=FakeOpener(error=OSError()), now=later + datetime.timedelta(days=1))
        self.assertEqual(self.saved()["dealer"]["failed_since"], "2026-10-15")       # 못 받기 시작한 날을 지킨다
        self.run_main(now=later + datetime.timedelta(days=2))
        d = self.saved()["dealer"]
        self.assertEqual((d["ok"], d["stale"], d["error"], d["failed_since"]), (True, False, None, None))
        self.assertEqual(d["retrieved"], "2026-10-14")                                  # 같은 숫자 — 받은 날은 그대로

    def test_both_failing_is_exit_1_and_keeps_the_previous_values(self):
        self.run_main()
        code, log = self.run_main(opener=FakeOpener(error=OSError()), fred=FakeFred(error=RuntimeError("x")),
                                  now=NOW + datetime.timedelta(days=1))
        self.assertEqual(code, 1, log)
        js = self.saved()
        self.assertTrue(all(js[k]["stale"] and not js[k]["ok"] for k in ("dealer", "custody")))
        self.assertEqual(js["custody"]["date"], "2026-10-07")
        self.assertIn("직전 값(2026-09-30 관측) 유지", log)

    def test_both_failing_without_a_previous_file(self):
        code, _ = self.run_main(opener=FakeOpener(error=OSError()), fred=FakeFred(error=RuntimeError("x")))
        self.assertEqual(code, 1)
        js = self.saved()                                                              # 실패 표시만 있는 파일 — 페이지는 '자료 없음'
        for k in ("dealer", "custody"):
            self.assertEqual(set(js[k]), {"ok", "stale", "error", "failed_since", "name", "series", "source"})

    def test_an_online_fred_cache_fallback_counts_as_a_failure(self):
        code, _ = self.run_main(fred=FakeFred(custody_series(), src="cache"))
        self.assertEqual(code, 0)
        c = self.saved()["custody"]
        self.assertEqual((c["ok"], c["error"]), (False, sf.REASONS["cache"]))

    def test_offline_reads_the_caches_only(self):
        os.makedirs(os.path.join(self.work, "supply"))
        with open(os.path.join(self.work, "supply", sf.PD_CACHE), "w", encoding="utf-8") as f:
            f.write(pd_json(dealer_series()))
        with open(os.path.join(self.work, "supply", "WMTSECL1.csv"), "w", encoding="utf-8") as f:   # 합성 FRED 캐시
            f.write("observation_date,WMTSECL1\n" + "".join(f"{d},{v:.0f}\n" for d, v in custody_series()))
        op = FakeOpener(error=AssertionError("요청하면 안 된다"))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = sf.main(["--out", self.out, "--work", self.work, "--offline"], opener=op, now=NOW)   # 진짜 fred_fetch.load
        self.assertEqual(code, 0, buf.getvalue())
        self.assertEqual(op.calls, [])
        js = self.saved()
        self.assertEqual((js["dealer"]["date"], js["custody"]["date"]), ("2026-09-30", "2026-10-07"))
        self.assertEqual(js["custody"]["level_bn"], round(round(custody_series()[-1][1]) / 1000, 3))

    def test_offline_without_caches_fails_both(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = sf.main(["--out", self.out, "--work", self.work, "--offline"], now=NOW)    # 진짜 fred_fetch.load, 캐시 없음
        self.assertEqual(code, 1)
        js = self.saved()
        self.assertEqual({js[k]["error"] for k in ("dealer", "custody")}, {sf.REASONS["fetch"]})

    def test_an_online_success_leaves_the_dealer_cache(self):
        self.run_main()
        with open(os.path.join(self.work, "supply", sf.PD_CACHE), encoding="utf-8") as f:
            self.assertEqual(sf.parse_pd(f.read())[-1][0], D(2026, 9, 30))

    def test_older_data_does_not_replace_newer(self):
        self.run_main()
        code, _ = self.run_main(opener=FakeOpener(pd_json(dealer_series(end=D(2026, 9, 16)))),
                                now=NOW + datetime.timedelta(days=1))
        d = self.saved()["dealer"]
        self.assertEqual((code, d["ok"], d["stale"], d["error"], d["date"]),
                         (0, False, True, sf.REASONS["older"], "2026-09-30"))

    def test_unchanged_content_is_not_rewritten(self):
        self.run_main()
        before = self.raw()
        code, _ = self.run_main(now=NOW + datetime.timedelta(days=1))
        self.assertEqual(code, 0)
        self.assertEqual(self.raw(), before)                                            # 같은 자료로 매일 커밋을 만들지 않는다

    def test_new_values_move_the_retrieved_date(self):
        self.run_main()
        later = NOW + datetime.timedelta(days=8)
        self.run_main(opener=FakeOpener(pd_json(dealer_series(end=D(2026, 10, 7)))), now=later)
        js = self.saved()
        self.assertEqual((js["dealer"]["date"], js["dealer"]["retrieved"]), ("2026-10-07", "2026-10-22"))
        self.assertEqual(js["custody"]["retrieved"], "2026-10-14")
        self.assertIn("October 22, 2026", js["dealer"]["source"]["citation"])

    def test_a_broken_previous_file_has_nothing_to_carry(self):
        os.makedirs(self.out)
        for broken in ("<<<<<<< HEAD\n{}", "[]", json.dumps({"schema": 1, "dealer": {"date": "어제", "line": "x"}}),
                       json.dumps({"schema": 99, "dealer": {}})):
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(broken)
            code, _ = self.run_main(opener=FakeOpener(error=OSError()))
            self.assertEqual(code, 0, broken)
            d = self.saved()["dealer"]
            self.assertEqual((d["stale"], "line" in d), (False, False), broken)

    def test_a_previous_side_with_wrong_types_is_not_carried(self):
        self.run_main()
        good = self.saved()

        def spoil(name, js):
            d = js["dealer"]
            if name == "level_bn 글자":
                d["level_bn"] = "432"
            elif name == "그래프 점":
                d["chart"]["lines"][0]["points"][0] = ["x", 1]
            elif name == "flag":
                d["flag"] = "up"
            elif name == "q4w.n 실수":
                d["q4w"]["n"] = float(d["q4w"]["n"])
            elif name == "ISO 주 날짜":                                                   # fromisoformat은 받는 꼴
                d["date"] = "2026-W40-3"
            return js

        for name in (None, "level_bn 글자", "그래프 점", "flag", "q4w.n 실수", "ISO 주 날짜"):
            js = json.loads(json.dumps(good))
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(spoil(name, js) if name else js, f, ensure_ascii=False)
            code, log = self.run_main(opener=FakeOpener(error=OSError()), now=NOW + datetime.timedelta(days=1))
            self.assertEqual(code, 0, (name, log))
            self.assertNotIn("Traceback", log, name)
            js = self.saved()
            d = js["dealer"]
            carried = name is None                                                        # 멀쩡한 직전 값만 이어 싣는다
            self.assertEqual((d["ok"], d["stale"], "line" in d), (False, carried, carried), name)
            self.assertTrue(js["custody"]["ok"], name)

    def test_a_failed_side_leaves_a_warning_annotation(self):
        def run(**kw):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = sf.main(["--out", self.out, "--work", self.work],
                               opener=kw.get("opener") or FakeOpener(pd_json(dealer_series())),
                               fred_load=kw.get("fred") or FakeFred(custody_series()), now=kw.get("now", NOW))
            notes = [l for l in out.getvalue().splitlines() if l.startswith("::")]
            self.assertFalse(re.search(r"\d+\.\d+|bn", out.getvalue()))                  # 주석에도 값은 찍지 않는다
            return code, notes

        code, notes = run(opener=FakeOpener(error=OSError("timed out")))
        self.assertEqual(code, 0)                                                      # 한쪽만 — 단계는 성공으로 끝난다
        self.assertEqual(notes, ["::warning::수급 참고 딜러 받지 못함: 수신 실패"])       # 받은 쪽(수탁)은 주석이 없다
        self.assertEqual(run(now=NOW + datetime.timedelta(days=1)), (0, []))           # 둘 다 받으면 주석 없음
        code, notes = run(fred=FakeFred(error=RuntimeError("x")), now=NOW + datetime.timedelta(days=2))
        self.assertEqual((code, notes), (0, ["::warning::수급 참고 수탁 받지 못함: 수신 실패 — 직전 값(2026-10-07 관측) 유지"]))
        code, notes = run(opener=FakeOpener(error=OSError()), fred=FakeFred(error=RuntimeError("x")),
                          now=NOW + datetime.timedelta(days=3))
        self.assertEqual((code, len(notes)), (1, 2))
        self.assertTrue(all(n.startswith("::warning::수급 참고 ") for n in notes))

    def test_changed_fixed_text_reaches_a_carried_side(self):
        self.run_main()
        js = self.saved()
        line, js["dealer"]["line"], js["dealer"]["notices"] = js["dealer"]["line"], "옛 문구", ["옛 고지"]
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(js, f, ensure_ascii=False)
        self.run_main(opener=FakeOpener(error=OSError()), now=NOW + datetime.timedelta(days=1))
        d = self.saved()["dealer"]
        self.assertTrue(d["stale"])
        self.assertEqual(d["line"], line)                                               # 문구는 숫자로 다시 만든다
        self.assertEqual(d["notices"], sf.notices("dealer", 2026))

    def test_the_write_is_atomic(self):
        self.run_main()
        before = self.raw()
        with mock.patch.object(sf.os, "replace", side_effect=OSError("disk full")):
            code, log = self.run_main(opener=FakeOpener(pd_json(dealer_series(end=D(2026, 10, 7)))),
                                      now=NOW + datetime.timedelta(days=8))
        self.assertEqual(code, 1, log)
        self.assertEqual(self.raw(), before)                                            # 반쯤 쓴 파일이 남지 않는다
        self.assertEqual(os.listdir(self.out), ["supply.json"])                         # 임시 파일도(봇 커밋에 실리지 않게)
        self.assertIn("쓰지 못함", log)

    def test_every_string_is_fixed_text_without_banned_words(self):
        self.run_main(opener=FakeOpener(error=OSError("원문 사유 xyz-77")))
        self.run_main(now=NOW + datetime.timedelta(days=1))
        self.run_main(fred=FakeFred(error=RuntimeError("https://bad.invalid/")), now=NOW + datetime.timedelta(days=2))
        dump = json.dumps(self.saved(), ensure_ascii=False)
        for word in FORBIDDEN_TEXT:                                                     # 공개 문구 원칙(시장 견해·내부 낱말 없음)
            self.assertNotIn(word, dump, word)
        urls = set(re.findall(r"https?://[^\s,;)\"]+", dump))
        self.assertEqual({u.rstrip(".") for u in urls},
                         {sf.PD_URL, sf.PD_PAGE, "https://fred.stlouisfed.org/series/WMTSECL1"})
        self.assertNotIn("bad.invalid", dump)
        self.assertNotIn("xyz-77", dump)
        errors = {self.saved()[k]["error"] for k in ("dealer", "custody")} - {None}
        self.assertLessEqual(errors, set(sf.REASONS.values()))

    def test_static_text_avoids_banned_words(self):
        texts = [sf.NOTICE, sf.PD_DERIVED, sf.PD_DERIVED_EN, sf.CUSTODY_DERIVED, sf.CHART_NOTE, *sf.REASONS.values()]
        texts += [v for spec in sf.SIDES.values() for v in spec.values() if isinstance(v, str)]
        texts += sf.present("dealer", PresentTest.DEALER, "2026-10-14")["extra"]
        for t in texts:
            for word in FORBIDDEN_TEXT:
                self.assertNotIn(word, t, (word, t))


class StaticTest(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
            return f.read()

    def test_workflow_fetches_without_failing_the_run(self):
        wf = self.read(".github", "workflows", "daily.yml")
        step = wf[wf.index("id: supply"):]
        self.assertIn("continue-on-error: true", step[:200])
        self.assertIn("timeout-minutes: 2", step[:200])
        self.assertIn("python scripts/supply_fetch.py", step[:300])
        self.assertLess(wf.index("id: supply"), wf.index("공개 전 검사(새 산출물 포함)"))   # 새 파일도 검사를 거쳐
        self.assertLess(wf.index("id: supply"), wf.index("git add data"))                 # 봇 커밋에 실린다
        alert = wf[wf.index("\n  alert:"):]
        self.assertNotIn("supply", alert)                                                # 실패해도 알림을 띄우지 않는다(머리말)

    def test_page_reads_the_file_and_puts_the_panel_in_the_term_premium_guide(self):
        page = self.read("site", "index.html")
        self.assertIn('getJson("data/supply.json")', page)
        guide = page[page.index("const GUIDE = {"):page.index("function tpFlowFigure()")]
        self.assertIn("panel: () => supplyPanel(supplyData)", guide)
        self.assertIn('"수급 참고"', page)
        self.assertIn("판정에 쓰지 않음", page)
        self.assertIn('<a href="data/supply.json">', page)                                # 꼬리말의 원자료 목록

    def test_page_text_avoids_banned_words_and_wraps_on_narrow_screens(self):
        page = self.read("site", "index.html")
        block = page[page.index("// 수급 참고 — data/supply.json"):page.index("\nlet activeView")]
        self.assertIn("function supplyPanel(", block)
        for word in FORBIDDEN_TEXT:                                                     # 공개 문구 원칙 — 화면 쪽 글도
            self.assertNotIn(word, block, word)
        css = self.read("site", "dashboard.css")
        self.assertRegex(css, r"\.rule-guide \.supply p \{[^}]*overflow-wrap: anywhere")       # 390px에서 숫자 줄이 넘치지 않게


if __name__ == "__main__":
    unittest.main(verbosity=1)
