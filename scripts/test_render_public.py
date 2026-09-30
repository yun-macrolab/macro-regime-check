#!/usr/bin/env python3
"""공개용 표(render_public) 테스트 — 공개본에 들어가면 안 되는 것이 0건인지 강제한다.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — test_regime의 합성 FRED 캐시로 원본 결과를 만든 뒤 변환한다.
가장 강한 검사는 화이트리스트다: 공개본의 모든 문자열이 render_public이 정의한 문구·시리즈 정보·날짜 중 하나여야 한다.
"""
import os, sys, re, json, copy, datetime, tempfile, unittest, shutil

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import regime_rules as rr
import regime_check as rck
import render_public as rp
from test_regime import make_cache, run_cli

TODAY = datetime.date(2026, 9, 22)

# 공개본에 나오면 안 되는 문자열 — 시나리오 문자·이름, 내부 ID, 해석 문구, 개인 견해로 이어지는 말
FORBIDDEN_TEXT = ["→", "F-0", "S-01", "A′", "D1", "D2", "O/W", "U/W", "붕괴", "코호트", "재정", "신용수축",
                  "시나리오", "국면", "C19", "시트", "판단로그", "LBO", "전사 위험", "강세장", "진행", "선행", "경보",
                  "반증", "신호", "후보", "PIK", "빈티지", "임대료"]
# 공개본 어디에도 없어야 하는 키 — 원본의 해석·내부 필드
FORBIDDEN_KEYS = {"scenario", "log_ids", "text", "source", "regime_inputs", "manual", "signals", "indicators"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$")


def walk(node):
    """(키 목록, 숫자 목록, 문자열 목록) — 중첩 JSON 전체."""
    keys, nums, strs = [], [], []
    if isinstance(node, dict):
        items = node.items()
    elif isinstance(node, list):
        items = ((None, v) for v in node)
    else:
        if isinstance(node, str):
            strs.append(node)
        elif isinstance(node, (int, float)) and not isinstance(node, bool):
            nums.append(node)
        return keys, nums, strs
    for k, v in items:
        if k is not None:
            keys.append(k)
        kk, nn, ss = walk(v)
        keys += kk
        nums += nn
        strs += ss
    return keys, nums, strs


def allowed_strings():
    table = rp.public_rules()
    s = {rp.NOTICE, "met", "not_met", "unknown", "net", "cache", "missing", "value", "status_only"}
    s |= set(rp.attribution(TODAY.year)) | set(rp.sofr_notices(TODAY.year)) | set(table)
    for spec in table.values():
        s |= {spec["title"], spec["rule"]}
        for o in spec["obs"]:
            s |= {o["label"], o["unit"], *o["series"]}
    for sid, (label, _, _) in rr.SERIES.items():
        s |= {sid, label, rp.OWNER[sid], rp.FRED_URL.format(sid), rp.citation(sid, TODAY.isoformat())}
    return s


class RenderPublicTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.work = os.path.join(self.tmp, ".work")
        self.out = os.path.join(self.tmp, "data")
        make_cache(os.path.join(self.work, "fred"))
        rck.build(self.work, TODAY, offline=True, prev_regime="A")
        with open(os.path.join(self.work, "raw", "latest.json"), encoding="utf-8") as f:
            self.raw = json.load(f)
        # 충족·판정 불가 분기도 타게 만든 두 번째 원본 — 해석 문구가 다양한 분기에서 새는지 본다
        self.raw2 = copy.deepcopy(self.raw)
        self.raw2["signals"] = rr.evaluate({**rck.flat(self.raw["indicators"]), "t10y2y": -0.5, "hy_oas": 5.0,
                                            "emp_yoy": -1.0, "sofr_chg_3m": None, "bei_chg_3m": None,
                                            "dfii10": 1.5, "reserves_gdp": 8.5})
        self.pubs = [rp.render(self.raw), rp.render(self.raw2)]

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_second_raw_covers_all_statuses(self):
        self.assertEqual({r["status"] for r in self.pubs[1]["rules"]}, {"met", "not_met", "unknown"})

    def test_every_string_is_whitelisted(self):
        allowed = allowed_strings()
        for pub in self.pubs:
            _, _, strs = walk(pub)
            bad = [s for s in strs if not (s in allowed or DATE_RE.match(s) or TS_RE.match(s)
                                            or s.startswith(rp.WARNING_PREFIXES))]
            self.assertEqual(bad, [])

    def test_forbidden_text_and_raw_texts_absent(self):
        for raw, pub in zip((self.raw, self.raw2), self.pubs):
            dump = json.dumps(pub, ensure_ascii=False)
            for word in FORBIDDEN_TEXT:
                self.assertNotIn(word, dump, word)
            for s in raw["signals"]:
                self.assertNotIn(s["text"], dump)

    def test_forbidden_keys_absent(self):
        for pub in self.pubs:
            keys, _, _ = walk(pub)
            self.assertEqual(FORBIDDEN_KEYS & set(keys), set())

    def test_restricted_series_values_absent(self):
        ind, inputs = self.raw["indicators"], self.raw["regime_inputs"]
        restricted = [ind["hy_oas"]["value"], ind["ig_oas"]["value"], ind["baa10y"]["value"],
                      ind["baa10y"]["from_low_12m"], ind["baa10y"]["pct_since_1990"], inputs["sp_13w_pct"]]
        self.assertTrue(all(v is not None for v in restricted))
        _, nums, strs = walk(self.pubs[0])
        str_nums = [float(x) for s in strs for x in re.findall(r"-?\d+\.\d+", s)]   # 문자열에 섞여 새는 경우
        # 반올림해 싣더라도 걸리게 비교한다: JSON 숫자는 소수 둘째·셋째 자리, 문자열 속 숫자는 첫째 자리까지.
        # 반올림 결과가 정수(0.0 등)면 공개본의 개수·경과일·작은 변화값과 겹쳐 유출인지 가릴 수 없으므로 건너뛴다
        checked = [v for v in restricted if v != int(v)]
        self.assertGreaterEqual(len(checked), 4)
        for v in checked:
            for pool, digit_levels in ((nums, (2, 3)), (str_nums, (1, 2, 3))):
                for digits in digit_levels:
                    rv = round(v, digits)
                    if rv == int(rv):
                        continue
                    self.assertFalse(any(abs(n - rv) < 10 ** -(digits + 1) for n in pool), (v, digits))
        derived = set()
        for r in self.pubs[0]["rules"]:
            for o in r["observations"]:
                if o.get("derived"):            # 원값을 되살릴 수 없는 파생 통계(상관)만 예외
                    derived.add(r["key"])
                    continue
                self.assertFalse(set(o["series"]) & set(rp.RESTRICTED), o)
        self.assertEqual(derived, {"stock_bond_corr"})
        for h in self.pubs[0]["data_health"]:
            self.assertEqual(h["display"], "status_only" if h["series"] in rp.RESTRICTED else "value")

    def test_every_rule_rendered_with_status_and_summary(self):
        pub = self.pubs[0]
        self.assertEqual([r["key"] for r in pub["rules"]], [s["key"] for s in self.raw["signals"]])
        want = {True: "met", False: "not_met", None: "unknown"}
        for r, s in zip(pub["rules"], self.raw["signals"]):
            self.assertEqual(r["status"], want[s["fired"]])
            self.assertTrue(r["title"] and r["rule"])
        sm = pub["summary"]
        self.assertEqual(sm["total"], len(self.raw["signals"]))
        self.assertEqual(sm["met"] + sm["not_met"] + sm["unknown"], sm["total"])
        self.assertEqual(pub["date"], "2026-09-22")
        self.assertEqual(len(pub["data_health"]), len(rr.SERIES))

    def test_observations_come_from_raw_values(self):
        ci = next(r for r in self.pubs[0]["rules"] if r["key"] == "ci_vs_ngdp")
        got = {o["label"]: o["value"] for o in ci["observations"]}
        self.assertAlmostEqual(got["명목GDP 전년비"], round(self.raw["indicators"]["ngdp_yoy"]["value"], 3))

    def test_rule_text_follows_every_threshold(self):
        # 규칙 문장의 숫자는 regime_rules.TH에서 온다 — 임계값을 바꾸면 문장도 같이 바뀌어야 한다
        uses = {"ndfi_credit": ["ndfi_step_bn", "ndfi_two_digit"], "credit_spread": ["spread_widen_pp", "hy_oas_break"],
                "stock_bond_corr": ["corr_run_days"], "real_rate_bei": ["real_rate_c"],
                "core_inflation": ["core_pce_split"], "term_premium": ["tp_drop_3m"], "sofr": ["sofr_rise_3m"],
                "reserves_multiplier": ["reserves_gdp_low", "reserves_gdp_rise_3m", "reserves_pce_floor"]}
        for key, ths in uses.items():
            for th in ths:
                orig = rr.TH[th]
                rr.TH[th] = 131 if th == "corr_run_days" else 12.345
                try:
                    rule = next(r for r in rp.render(self.raw)["rules"] if r["key"] == key)["rule"]
                finally:
                    rr.TH[th] = orig
                self.assertIn("131" if th == "corr_run_days" else "12.345", rule, (key, th))

    def test_unknown_rule_key_fails_loudly(self):
        raw = {**self.raw, "signals": self.raw["signals"] + [{"key": "new_rule", "fired": True, "text": "?"}]}
        with self.assertRaises(RuntimeError):
            rp.render(raw)

    def test_only_whitelisted_warnings_pass(self):
        raw = {**self.raw, "warnings": [r"C:\Users\someone\cache 오류", "NDFI 계단 2025-01-01 +236 — YoY에서 제외",
                                         "SOFR(SOFR) 미수신: TimeoutError"]}
        self.assertEqual(rp.render(raw)["warnings"], ["NDFI 계단 2025-01-01 +236 — YoY에서 제외"])

    def test_attribution_and_citations(self):
        pub = self.pubs[0]
        self.assertTrue(any("New York" in a for a in pub["attribution"]))
        self.assertTrue(any("FRED" in a for a in pub["attribution"]))
        rows = {h["series"]: h for h in pub["data_health"]}
        self.assertIn("New York", rows["SOFR"]["citation"])
        self.assertTrue(all(h["citation"] for h in pub["data_health"]))

    def test_sofr_reference_rate_notice_and_citation(self):
        # 뉴욕 연은 이용약관(2023-06-09 개정) Use Restrictions — Reference Rates: SOFR 자료를 쓰거나 배포하면 정해진
        # 고지·면책을 함께 싣는다(2026-09-30 원문 확인). 페이지 꼬리말·SOFR 카드·JSON 모두에 실린다
        pub = self.pubs[0]
        year = int(pub["date"][:4])
        # 약관의 틀에 [이름]·[발행처]만 채운 그대로 — 중간 문구가 바뀌어도 잡히게 전체를 비교한다
        self.assertEqual(rp.SOFR_NOTICE,
                         "The SOFR data is subject to the Terms of Use posted at newyorkfed.org. The New York Fed is not "
                         "responsible for publication of the SOFR data by macro-regime-check (github.com/yun-macrolab), "
                         "does not sanction or endorse any particular republication, and has no liability for your use.")
        self.assertEqual(rp.SOFR_DTCC,
                         "The Secured Overnight Financing Rate (SOFR) Data and Broad General Collateral Rate (BGCR) Data "
                         "are calculated using data provided under a license granted to the New York Fed by DTCC Solutions "
                         "LLC (\u201cSolutions\u201d), an affiliate of The Depository Trust & Clearing Corporation. Solutions, "
                         "its affiliates, and third parties from which they obtained data have no liability for the content "
                         "of this material.")
        self.assertTrue(rp.NOT_AFFILIATED.startswith(
            "macro-regime-check (github.com/yun-macrolab) is not affiliated with the New York Fed. The New York Fed does "
            "not sanction, endorse, or recommend any products or services offered by macro-regime-check"))
        self.assertEqual(rp.nyfed_attribution(year), f"© {year} Federal Reserve Bank of New York. "
                         "Content from the New York Fed subject to the Terms of Use at newyorkfed.org.")
        for line in (rp.SOFR_NOTICE, rp.SOFR_DTCC, rp.nyfed_attribution(year), rp.NOT_AFFILIATED, rp.DATA_LICENSE):
            self.assertIn(line, pub["attribution"])
        sofr = next(r for r in pub["rules"] if r["key"] == "sofr")
        self.assertEqual(sofr["notices"], rp.sofr_notices(year))
        self.assertIn(rp.SOFR_NOTICE, sofr["notices"])
        self.assertTrue(any("macro-regime-check" in n and "계산" in n for n in sofr["notices"]))   # 파생값은 누가 계산했는지
        self.assertIn(rp.SOFR_DERIVED_EN, sofr["notices"])                                   # 영어로 읽는 사람에게도
        self.assertIn(rp.NOT_AFFILIATED, sofr["notices"])
        obs = {o["label"]: o for o in sofr["observations"]}
        self.assertEqual((obs["SOFR"]["computed"], obs["3개월 변화"]["computed"]), (False, True))
        self.assertTrue(all(r["notices"] == [] for r in pub["rules"] if r["key"] != "sofr"))
        rows = {h["series"]: h for h in pub["data_health"]}
        # FRED 시리즈 페이지의 Suggested Citation 그대로(날짜 = 공개본 기준일)
        self.assertEqual(rows["SOFR"]["citation"], "Federal Reserve Bank of New York, Secured Overnight Financing Rate "
                         "[SOFR], retrieved from FRED, Federal Reserve Bank of St. Louis; "
                         "https://fred.stlouisfed.org/series/SOFR, September 22, 2026.")
        self.assertEqual(rows["DGS10"]["citation"], "Board of Governors of the Federal Reserve System (US), Market Yield "
                         "on U.S. Treasury Securities at 10-Year Constant Maturity, Quoted on an Investment Basis [DGS10], "
                         "retrieved from FRED, Federal Reserve Bank of St. Louis; "
                         "https://fred.stlouisfed.org/series/DGS10, September 22, 2026.")
        self.assertEqual(rows["T10Y2Y"]["citation"].split(",")[0], "Federal Reserve Bank of St. Louis")
        self.assertEqual(set(rp.FRED_SOURCE), set(rr.SERIES))
        self.assertEqual(set(rp.FRED_TITLE), set(rr.SERIES))

    def test_computed_values_are_marked(self):
        # 이 저장소가 계산한 값(전년비·3개월 변화·비율·상관)은 원 발행처의 값으로 보이지 않게 '계산값'으로
        comp = {(r["key"], o["label"]): o["computed"] for r in self.pubs[0]["rules"] for o in r["observations"]}
        self.assertTrue(comp[("sofr", "3개월 변화")] and comp[("term_premium", "3개월 변화")])
        self.assertTrue(comp[("ndfi_credit", "NDFI 대출 전년비(계단 제외)")] and comp[("stock_bond_corr", "60영업일 상관")])
        self.assertFalse(comp[("sofr", "SOFR")] or comp[("curve_inversion", "10년−2년")] or comp[("real_rate_bei", "10년 실질금리")])

    def test_quarterly_series_not_stale_before_next_advance_release(self):
        raw = copy.deepcopy(self.raw)
        raw["sources"]["GDP"]["age_days"] = 207          # 2026-04-01 관측, 2026-10-25 기준
        self.assertFalse(next(h for h in rp.render(raw)["data_health"] if h["series"] == "GDP")["stale"])

    def test_write_public_and_history(self):
        rp.write(self.out, self.pubs[0])
        with open(os.path.join(self.out, "public.json"), encoding="utf-8") as f:
            a = json.load(f)
        with open(os.path.join(self.out, "history", "2026-09-22.json"), encoding="utf-8") as f:
            b = json.load(f)
        self.assertEqual(a, b)
        self.assertEqual(a["schema"], rp.SCHEMA)

    def test_older_date_does_not_replace_public(self):
        rp.write(self.out, self.pubs[0])
        older = {**self.pubs[0], "date": "2026-06-15"}
        self.assertFalse(rp.write(self.out, older))
        with open(os.path.join(self.out, "public.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["date"], "2026-09-22")
        self.assertTrue(os.path.exists(os.path.join(self.out, "history", "2026-06-15.json")))


class RenderCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.work = os.path.join(self.tmp, ".work")
        self.out = os.path.join(self.tmp, "data")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_missing_raw_is_one_line_and_exit_1(self):
        p = run_cli("render_public.py", "--work", self.work, "--out", self.out)
        self.assertEqual(p.returncode, 1)
        err = p.stderr.strip().splitlines()
        self.assertEqual(len(err), 1)
        self.assertNotIn("Traceback", err[0])

    def test_success_prints_one_summary_line_only(self):
        make_cache(os.path.join(self.work, "fred"))
        self.assertEqual(run_cli("regime_check.py", "--work", self.work, "--offline",
                                 "--date", TODAY.isoformat()).returncode, 0)
        p = run_cli("render_public.py", "--work", self.work, "--out", self.out)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, "")
        self.assertEqual(len(p.stdout.strip().splitlines()), 1)
        for leak in ("HY OAS", "Baa", "→", "%p"):
            self.assertNotIn(leak, p.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.out, "public.json")))
        self.assertFalse(os.path.exists(os.path.join(self.out, "raw")))       # 원본은 사이트 폴더에 없다
        self.assertFalse(os.path.exists(os.path.join(self.out, "fred")))


if __name__ == "__main__":
    unittest.main(verbosity=1)
