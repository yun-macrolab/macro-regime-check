#!/usr/bin/env python3
"""달러·기대인플레이션·성장·금융 여건 참고 자료(macro_fetch) 테스트 — 산식(답을 아는 합성 자료), 칸마다 실패·직전 값 이어 싣기,
이용 조건 목록과 고지(클리블랜드 CC BY-SA · 시카고 연은 '허락 확인 중'), 문구 원칙(판정·방향 낱말 없음), 화면·워크플로·README 연결.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — FRED는 가짜 loader. 숫자는 모두 지어낸 것이다.
"""
import os, sys, io, re, json, datetime, tempfile, unittest, shutil, contextlib

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import macro_fetch as mf
import ai_invest_fetch as ai
from test_render_public import FORBIDDEN_TEXT
from test_oil_fetch import VERDICT

REPO = os.path.dirname(SCRIPTS)
D = datetime.date
NOW = datetime.datetime(2026, 11, 28, 1, 30, tzinfo=datetime.timezone.utc)
CHICAGO = ("CFNAI", "CFNAIMA3", "NFCI", "ANFCI")


def bdays(start, end):
    out, d = [], start
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += datetime.timedelta(days=1)
    return out


def weekly(start, end, weekday):
    out, d = [], start
    while d <= end:
        if d.weekday() == weekday:
            out.append(d)
        d += datetime.timedelta(days=1)
    return out


def months(start, end):
    out, (y, m) = [], (start.year, start.month)
    while D(y, m, 1) <= end:
        out.append(D(y, m, 1))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def world():
    days = bdays(D(2025, 1, 1), D(2026, 11, 20))
    S = {"DTWEXBGS": [(d, 100.0 if d < D(2026, 8, 24) else 110.0 if d < D(2026, 10, 26) else 121.0) for d in days],
         "T10YIE": [(d, 2.0 if d < D(2026, 11, 2) else 2.25) for d in bdays(D(2025, 1, 1), D(2026, 11, 27))],
         "T5YIFR": [(d, 2.3 if d < D(2026, 8, 28) else 2.1) for d in bdays(D(2025, 1, 1), D(2026, 11, 26))]}
    sat = weekly(D(2025, 1, 4), D(2026, 11, 21), 5)
    S["WEI"] = [(d, 1.0 + i * 0.01) for i, d in enumerate(sat)]
    fri = weekly(D(2025, 1, 3), D(2026, 11, 20), 4)
    S["NFCI"] = [(d, -0.5 if d < D(2026, 10, 30) else -0.45) for d in fri]
    S["ANFCI"] = [(d, -0.4 if d < D(2026, 10, 16) else -0.42) for d in fri if d <= D(2026, 11, 13)]
    ms = months(D(2024, 1, 1), D(2026, 11, 1))
    S["EXPINF10YR"] = [(m, 2.5 + 0.01 * i) for i, m in enumerate(ms)]
    S["EXPINF1YR"] = [(m, 3.0) for m in ms if m <= D(2026, 10, 1)]
    S["INDPRO"] = [(m, 100.0 * 1.01 ** i) for i, m in enumerate(ms) if m <= D(2026, 10, 1)]
    S["CFNAI"] = [(m, 0.1 * (i % 3) - 0.1) for i, m in enumerate(ms) if m <= D(2026, 10, 1)]
    S["CFNAIMA3"] = [(m, -0.05) for m in ms if m <= D(2026, 9, 1)]
    return S


class FakeFred:
    def __init__(self, data, fail=(), cache=()):
        self.data, self.fail, self.cache, self.calls = data, set(fail), set(cache), []

    def __call__(self, sid, cache_dir, offline=False, timeout=None):
        self.calls.append((sid, timeout))
        if sid in self.fail:
            raise RuntimeError(f"{sid}: 원문 사유 https://bad.invalid/xyz-77")
        return list(self.data[sid]), ("cache" if sid in self.cache else "net")


def run(out, fred, now=NOW):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        rc = mf.main(["--out", out, "--work", os.path.join(out, ".work")], fred_load=fred, now=now)
    with open(os.path.join(out, mf.FILE), encoding="utf-8") as f:
        return rc, json.load(f)


class ArithmeticTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.S = world()

    def test_dollar_level_and_four_and_thirteen_weeks(self):
        c = mf.calc_dollar(self.S)
        self.assertEqual((c["date"], c["values"]["level"]), ("2026-11-20", 121.0))
        self.assertAlmostEqual(c["values"]["w4"], 10.0)                            # 10-26부터 121, 28일 전(10-23) 110
        self.assertAlmostEqual(c["values"]["w13"], 21.0)                           # 91일 전(08-21) 100

    def test_market_moves_are_basis_points_and_each_keeps_its_date(self):
        v = mf.calc_market(self.S)["values"]
        self.assertEqual((v["be10_date"], v["fwd_date"]), ("2026-11-27", "2026-11-26"))
        self.assertAlmostEqual(v["be10_4w"], 25.0)
        self.assertAlmostEqual(v["be10_13w"], 25.0)
        self.assertAlmostEqual(v["fwd_4w"], 0.0)
        self.assertAlmostEqual(v["fwd_13w"], -20.0)                                # 08-27 2.3 → 2.1
        self.assertEqual(mf.calc_market(self.S)["date"], "2026-11-27")

    def test_model_prev_month_and_optional_one_year(self):
        c = mf.calc_model(self.S)
        v = c["values"]
        self.assertEqual((v["month"], v["e1_month"], c["date"]), ("2026-11-01", "2026-10-01", "2026-11-01"))
        self.assertAlmostEqual(v["e10"] - v["e10_prev"], 0.01)
        S = dict(self.S)
        del S["EXPINF1YR"]
        v = mf.calc_model(S)["values"]
        self.assertIsNone(v["e1"])
        self.assertIsNone(v["e1_month"])
        self.assertIn("1년 미수신", mf.texts("model", v, "2026-11-01")[0])
        self.assertEqual([s["series"] for s in mf.sources_of(mf.BY_KEY["model"], values=v)], ["EXPINF10YR"])

    def test_wei_shows_values_four_and_thirteen_weeks_back(self):
        v = mf.calc_wei(self.S)["values"]
        n = len(self.S["WEI"]) - 1
        self.assertAlmostEqual(v["wei"], 1.0 + n * 0.01)
        self.assertAlmostEqual(v["w4"], 1.0 + (n - 4) * 0.01)
        self.assertAlmostEqual(v["w13"], 1.0 + (n - 13) * 0.01)

    def test_indpro_year_on_year_and_three_month_annualised(self):
        v = mf.calc_indpro(self.S)["values"]
        self.assertEqual(v["month"], "2026-10-01")
        self.assertAlmostEqual(v["yoy"], (1.01 ** 12 - 1) * 100, places=3)
        self.assertAlmostEqual(v["a3"], (1.01 ** 12 - 1) * 100, places=3)        # (1.01^3)^4
        short = {"INDPRO": self.S["INDPRO"][-6:]}
        with self.assertRaises(mf.ItemError):
            mf.calc_indpro(short)                                                  # 1년 전 같은 달이 없으면 칸을 싣지 않는다

    def test_cfnai_each_series_keeps_its_month(self):
        c = mf.calc_cfnai(self.S)
        v = c["values"]
        self.assertEqual((v["month"], v["ma3_month"], c["date"]), ("2026-10-01", "2026-09-01", "2026-10-01"))
        line = mf.texts("cfnai", v, c["date"])[0]
        self.assertIn("CFNAI-MA3 -0.05(2026-09)", line)

    def test_nfci_four_week_difference(self):
        v = mf.calc_nfci(self.S)["values"]
        self.assertEqual((v["nfci_date"], v["anfci_date"]), ("2026-11-20", "2026-11-13"))
        self.assertAlmostEqual(v["nfci_4w"], 0.05)                                 # 10-30부터 −0.45, 28일 전(10-23) −0.5
        self.assertAlmostEqual(v["anfci_4w"], 0.0)                                 # 10-16부터 −0.42 — 4주 전도 같다

    def test_back_leaves_a_gap_rather_than_reaching_far(self):
        s = [(D(2026, 1, 2), 1.0), (D(2026, 3, 6), 2.0)]
        self.assertIsNone(mf.back(s, 28))                                          # 28일 전 이하 마지막 관측이 7일 넘게 이르다


class TextTest(unittest.TestCase):
    def test_every_line_avoids_verdict_and_old_words(self):
        S = world()
        for spec in mf.ITEMS:
            core = spec["calc"](S)
            line, extra = mf.texts(spec["key"], core["values"], core["date"])
            for t in [line, *extra]:
                for word in list(FORBIDDEN_TEXT) + list(VERDICT):
                    self.assertNotIn(word, t, (spec["key"], word))
                self.assertNotRegex(t, r"None|nan|inf")

    def test_no_threshold_lands_in_the_data_file(self):
        # −0.70은 화면의 읽는 법에 '출처의 설명'으로만 있다 — 자료 파일의 줄에는 문턱 숫자가 없다
        S = world()
        for spec in mf.ITEMS:
            core = spec["calc"](S)
            line, extra = mf.texts(spec["key"], core["values"], core["date"])
            self.assertNotIn("0.70", line + "".join(extra))
            self.assertNotIn("0.7", "".join(extra))

    def test_dollar_explains_the_dxy_difference_without_its_value(self):
        extra = mf.texts("dollar", {"level": 1.0, "w4": None, "w13": None}, "2026-11-20")[1]
        self.assertTrue(any("DXY" in t and "26개" in t and "6개" in t and "싣지 않는다" in t for t in extra))
        self.assertNotIn("DTWEXBGS", "".join(extra))


class LicenceTest(unittest.TestCase):
    def test_the_series_list_is_fixed(self):
        self.assertEqual(set(mf.SOURCES), set(mf.LICENCE))
        self.assertEqual(mf.SERIES, ["DTWEXBGS", "T10YIE", "T5YIFR", "EXPINF10YR", "EXPINF1YR", "WEI", "INDPRO",
                                     "CFNAI", "CFNAIMA3", "NFCI", "ANFCI"])
        self.assertEqual(mf.SERIES[-4:], list(CHICAGO))                            # 시간이 모자라면 시카고 연은부터 빠진다
        for sid in ("MICH", "GDPNOW", "DTWEXAFEGS", "NFCICREDIT", "STLFSI4"):
            self.assertNotIn(sid, mf.SOURCES)
        self.assertEqual(set(mf.LICENCE.values()),
                         {"public-domain", "citation-required", "cc-by-sa-4.0", "chicago-fed-permission-pending"})
        self.assertEqual({s for s, v in mf.LICENCE.items() if v == "chicago-fed-permission-pending"}, set(CHICAGO))
        self.assertEqual({s for s, v in mf.LICENCE.items() if v == "cc-by-sa-4.0"}, {"EXPINF10YR", "EXPINF1YR"})
        used = {sid for it in mf.ITEMS for sid in it["series"] + list(it.get("optional", {}))}
        self.assertEqual(used, set(mf.SOURCES))

    def test_every_series_has_its_notice(self):
        self.assertEqual(set(mf.SERIES_NOTICES), set(mf.SOURCES))
        chi = mf.CHICAGO_NOTICE
        for want in ("허락 확인 중", "서면 허락", "허락을 받은 것이 아니다", "2026-11-28", "위험을 알고", "요청하면 내린다"):
            self.assertIn(want, chi)
        cle = mf.CLEVELAND_NOTICE
        for want in ("Creative Commons Attribution-ShareAlike 4.0 International", "https://doi.org/10.26509/frbc-infexp",
                     "CC BY-SA 4.0", "값을 바꾸지 않고"):
            self.assertIn(want, cle)
        self.assertIn("public domain", mf.BOARD_NOTICE)
        self.assertIn("달라스 연은", mf.WEI_NOTICE)

    def test_present_carries_citations_and_notices(self):
        S = world()
        p = mf.present("nfci", mf.calc_nfci(S), "2026-11-28")
        self.assertEqual(p["card"], "fincond")
        self.assertIn(mf.CHICAGO_NOTICE, p["notices"])
        self.assertEqual(p["notices"][0], mf.COMPUTED_NOTICE)
        cites = [s["citation"] for s in p["sources"]]
        self.assertEqual(cites[0], "Federal Reserve Bank of Chicago, Chicago Fed National Financial Conditions Index [NFCI], "
                         "retrieved from FRED, Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/NFCI, "
                         "November 28, 2026.")
        for s in p["sources"]:
            self.assertTrue(s["url"].startswith("https://fred.stlouisfed.org/series/"))


class RunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.S = world()

    def test_full_run_writes_every_item(self):
        rc, js = run(self.tmp, FakeFred(self.S))
        self.assertEqual(rc, 0)
        self.assertEqual(js["order"], [s["key"] for s in mf.ITEMS])
        self.assertEqual(js["cards"], {"dollar": ["dollar"], "expinf": ["market", "model"],
                                       "growth": ["wei", "indpro", "cfnai"], "fincond": ["nfci"]})
        for k, it in js["items"].items():
            self.assertTrue(it["ok"], k)
            self.assertEqual(it["retrieved"], "2026-11-28")
            self.assertTrue(it["notices"])

    def test_one_failed_series_keeps_the_previous_value_for_that_item_only(self):
        run(self.tmp, FakeFred(self.S))
        later = NOW + datetime.timedelta(days=3)
        rc, js = run(self.tmp, FakeFred(self.S, fail={"NFCI"}), later)
        self.assertEqual(rc, 0)
        it = js["items"]["nfci"]
        self.assertEqual((it["ok"], it["stale"], it["error"], it["failed_since"]), (False, True, "수신 실패", "2026-12-01"))
        self.assertEqual(it["date"], "2026-11-20")
        self.assertNotIn("bad.invalid", json.dumps(js))                            # 오류 원문은 싣지 않는다
        self.assertTrue(js["items"]["dollar"]["ok"])
        self.assertEqual(js["items"]["dollar"]["retrieved"], "2026-11-28")         # 같은 내용이면 받은 날을 바꾸지 않는다
        rc, js = run(self.tmp, FakeFred(self.S, fail={"NFCI", "EXPINF1YR"}), later + datetime.timedelta(days=1))
        self.assertEqual(js["items"]["nfci"]["failed_since"], "2026-12-01")        # 처음 못 받은 날을 지킨다
        # 선택 시리즈(EXPINF1YR)만 못 받으면 — 칸은 이번 10년 값으로 싣되 1년은 직전 값을 남기고 '받지 못함(언제부터)'을 단다
        m = js["items"]["model"]
        self.assertEqual((m["ok"], m["values"]["e1"], m["values"]["e1_month"], m["values"]["e1_failed_since"]),
                         (True, 3.0, "2026-10-01", "2026-12-02"))
        self.assertIn("1년 3.00%(2026-10 — 받지 못함(2026-12-02부터), 직전 값)", m["line"])
        self.assertIn("EXPINF1YR", [x["series"] for x in m["sources"]])
        rc, js = run(self.tmp, FakeFred(self.S, fail={"EXPINF1YR"}), later + datetime.timedelta(days=2))
        self.assertEqual(js["items"]["model"]["values"]["e1_failed_since"], "2026-12-02")   # 이어 못 받아도 첫날을 지킨다
        self.assertEqual(js["items"]["model"]["values"]["e1"], 3.0)
        rc, js = run(self.tmp, FakeFred(self.S), later + datetime.timedelta(days=3))
        self.assertIsNone(js["items"]["model"]["values"]["e1_failed_since"])     # 다시 받으면 표시가 사라진다

    def test_first_failure_without_previous_has_only_the_reason(self):
        rc, js = run(self.tmp, FakeFred(self.S, cache={"WEI"}))
        it = js["items"]["wei"]
        self.assertEqual((it["ok"], it["stale"], it["error"]), (False, False, "수신 실패 · 묵은 캐시는 싣지 않음"))
        self.assertNotIn("line", it)
        self.assertEqual([s["series"] for s in it["sources"]], ["WEI"])
        fresh = os.path.join(self.tmp, "fresh")
        rc, js = run(fresh, FakeFred(self.S, fail={"EXPINF1YR"}))
        v = js["items"]["model"]["values"]                                          # 직전 1년 값이 없으면 값은 비고 날짜만
        self.assertEqual((js["items"]["model"]["ok"], v["e1"], v["e1_month"], v["e1_failed_since"]),
                         (True, None, None, "2026-11-28"))
        self.assertIn("1년 미수신(2026-11-28부터)", js["items"]["model"]["line"])

    def test_older_data_is_not_taken(self):
        run(self.tmp, FakeFred(self.S))
        S = dict(self.S)
        S["DTWEXBGS"] = self.S["DTWEXBGS"][:-5]
        rc, js = run(self.tmp, FakeFred(S), NOW + datetime.timedelta(days=1))
        it = js["items"]["dollar"]
        self.assertEqual((it["ok"], it["stale"], it["error"], it["date"]),
                         (False, True, "받은 자료가 직전 자료보다 오래됨", "2026-11-20"))

    def test_nothing_received_exits_one_and_same_content_is_not_rewritten(self):
        rc, js = run(self.tmp, FakeFred(self.S, fail=set(mf.SERIES)))
        self.assertEqual(rc, 1)
        self.assertTrue(all(not it["ok"] for it in js["items"].values()))
        rc, _ = run(self.tmp, FakeFred(self.S))
        path = os.path.join(self.tmp, mf.FILE)
        before = os.path.getmtime(path)
        os.utime(path, (before - 100, before - 100))
        rc, _ = run(self.tmp, FakeFred(self.S), NOW + datetime.timedelta(hours=1))
        self.assertEqual(os.path.getmtime(path), before - 100)

    def test_broken_previous_file_is_ignored(self):
        with open(os.path.join(self.tmp, mf.FILE), "w", encoding="utf-8") as f:
            json.dump({"schema": 1, "items": {"dollar": {"values": {"level": "x"}, "date": "2026-11-01",
                                                          "retrieved": "2026-11-01"}}}, f)
        rc, js = run(self.tmp, FakeFred(self.S, fail={"DTWEXBGS"}))
        self.assertEqual((js["items"]["dollar"]["stale"], js["items"]["dollar"]["error"]), (False, "수신 실패"))

    def test_budget_runs_out_from_the_end(self):
        t = [0.0]

        def clock():
            t[0] += 8.0
            return t[0]
        fred = FakeFred(self.S)
        data, errors = mf.load_all(self.tmp, fred_load=fred, clock=clock)
        self.assertIn("DTWEXBGS", data)
        self.assertTrue(set(errors) <= set(mf.SERIES[-5:]))
        self.assertIn("ANFCI", errors)

    def test_future_dates_are_dropped(self):
        S = dict(self.S)
        S["DTWEXBGS"] = self.S["DTWEXBGS"] + [(D(2026, 12, 31), 999.0)]
        c = mf.compute(S, {}, D(2026, 11, 28))
        self.assertEqual(c["dollar"]["values"]["level"], 121.0)


class WiringTest(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
            return f.read()

    def test_screen_script_matches_the_file_and_avoids_verdict_words(self):
        js = self.read("site", "macro.js")
        block = js[js.index("const CARDS = {"):].split("};")[0]
        cards = {k: re.findall(r'"(\w+)"', v) for k, v in re.findall(r"(\w+): \[([^\]]*)\]", block)}
        self.assertEqual(cards, {c: [s["key"] for s in mf.ITEMS if s["card"] == c] for c in mf.CARDS})
        self.assertEqual(list(cards), mf.CARDS)
        reasons = re.findall(r'"([^"]+)"', js[js.index("const REASONS = ["):].split("];")[0])
        self.assertEqual(reasons, list(mf.REASONS.values()))
        for tok in ("innerHTML", "outerHTML", "insertAdjacentHTML", "createElement", "fetch(", "eval(", "http://", "https://"):
            self.assertNotIn(tok, js)
        body = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        for word in list(FORBIDDEN_TEXT) + list(VERDICT):
            self.assertNotIn(word, body, word)
        self.assertIn('const LABEL = "참고 — 예측 아님";', js)
        self.assertIn('fincond: "시카고 연은 · 허락 확인 중"', js)
        self.assertIn("허락 확인 중(CFNAI)", js)
        self.assertIn("CC BY-SA 4.0", js)
        # −0.70은 출처의 설명으로만 — 따옴표 인용 + 기준선·색으로 쓰지 않는다는 말과 함께, 다른 곳에는 없다
        self.assertEqual(body.count("0.70"), 1)
        self.assertIn('associated with a CFNAI-MA3 value below –0.70\\"', body)
        self.assertIn("기준선으로 쓰지 않으며 숫자의 색도 바꾸지 않습니다", body)

    def test_about_lines_are_one_register_and_say_no_forecast(self):
        js = self.read("site", "macro.js")
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        rule = re.search(r'const RULE = "([^"]+)";', code).group(1)
        self.assertIn("예측하지 않습니다", rule)
        self.assertIn("문턱을 두지 않으며", rule)
        about = code[code.index("const ABOUT = {"):].split("};")[0]
        self.assertEqual(about.count("+ RULE"), 4)
        for sent in filter(None, re.split(r"(?<=\.)\s+", "".join(re.findall(r'"([^"]*)"', about)) + rule)):
            self.assertTrue(sent.endswith("니다."), sent)
        for mine in ("규칙 점검에 쓰지 않는", "예측하지 않는다", "문턱을 두지 않으며"):
            self.assertIn(mine, mf.NOTICE)

    def test_page_wires_four_slots_in_their_groups(self):
        page = self.read("site", "index.html")
        self.assertIn('getJson("data/macro.json")', page)
        self.assertIn('<script src="oil.js"></script>\n<script src="macro.js"></script>', page)
        self.assertIn('<a href="data/macro.json">', page[page.index("<footer>"):page.index("</footer>")])
        for group, slot in (("inflation", "expinf-slot"), ("credit", "growth-slot"), ("credit", "fincond-slot"),
                            ("liquidity", "dollar-slot")):
            self.assertIn(f'g.id === "{group}" ? el("div", {{id:"{slot}", class:"oil-slot"}}) : null,', page)
        js = self.read("site", "macro.js")
        for slot in ("expinf-slot", "growth-slot", "fincond-slot", "dollar-slot"):
            self.assertIn(f'"{slot}"', js)
        line = next(l for l in page.splitlines() if "window.MacroCards.render(" in l)
        self.assertRegex(line, r"^\s*try \{ if \(isObj\(mac\) && window\.MacroCards\b")
        self.assertLess(page.index("window.MacroCards.render("), page.index("  applyView();\n  document.body"))
        self.assertLess(page.index("const macroJob"), page.index("const [st, pub,"))   # 다른 자료와 함께 받기 시작한다

    def test_workflow_fetches_without_failing_the_run(self):
        wf = self.read(".github", "workflows", "daily.yml")
        step = wf[wf.index("id: macro"):]
        self.assertIn("continue-on-error: true", step[:200])
        self.assertIn("timeout-minutes: 2", step[:200])
        self.assertIn("python scripts/macro_fetch.py", step[:300])
        self.assertLess(wf.index("id: oil"), wf.index("id: macro"))
        self.assertLess(wf.index("id: macro"), wf.index("공개 전 검사(새 산출물 포함)"))
        self.assertLess(wf.index("id: macro"), wf.index("git add data"))
        self.assertNotIn("macro", wf[wf.index("\n  alert:"):])                  # 실패해도 알림을 띄우지 않는다
        self.assertIn("node --test scripts/test_macro_render.cjs", wf[wf.index("\n  check:"):wf.index("\n  update:")])

    def test_readme_counts_and_section(self):
        readme = self.read("README.md")
        m = re.search(r"\*\*아침 쪽 Python 테스트 (\d+)개 \+ node 테스트 (\d+)개\*\*\((.*?)\)와 \*\*저녁판", readme)
        py_part, node_part = m.group(3).split(" / node: ")
        mine = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()
        self.assertIn(f" · 달러·기대인플레이션·성장·금융 여건 참고 {mine} · ", py_part)
        cjs = len(re.findall(r"^test\(", self.read("scripts", "test_macro_render.cjs"), flags=re.M))
        self.assertIn(f" · 달러·성장 카드 그리기 {cjs} · ", node_part)
        self.assertIn("## 참고: 달러·기대인플레이션·성장·금융 여건", readme)
        limits = readme[readme.index("## 한계"):readme.index("## 누가 무엇을 했나")]
        self.assertIn("시카고 연은", limits)
        self.assertIn("2026-11-28", limits)
        for sid in mf.SERIES:
            self.assertIn(f"`{sid}`", readme)


if __name__ == "__main__":
    unittest.main(verbosity=1)
