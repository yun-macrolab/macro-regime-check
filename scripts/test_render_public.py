#!/usr/bin/env python3
"""공개용 표(render_public) 테스트 — 공개본에 들어가면 안 되는 것이 0건인지 강제한다.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — test_regime의 합성 FRED 캐시로 원본 결과를 만든 뒤 변환한다. 숫자는 모두 지어낸 것이다.
가장 강한 검사는 화이트리스트다: 공개본의 모든 문자열이 render_public이 정의한 문구·시리즈 정보·날짜 중 하나여야 한다.
2026-10-30 사용자 결정으로 해석 쪽(규칙마다 scenario·reading, regime 절)이 공개된다 — 그 부분은 따로 본다:
해석 줄은 원본 문장에서 내부 ID만 뺀 것(credit_spread는 Baa 부분 + ICE HY OAS 값 자리의 고정 문구 + 결론 구절)이어야 하고,
재배포 제한 입력(S&P·ICE)을 바꿔도 판정이 같으면 공개본이 한 글자도 바뀌지 않아야 한다.
2026-10-30 운영자 결정으로 Moody's Baa−10년은 값(수준·12개월 저점 대비·1990년 이후 분위)을 Moody's 고지·FRED 인용과 함께 싣는다 —
비공개 월간 점검 줄과 같은 숫자인지, ICE 값은 여전히 어디에도 없는지, 날짜별 기록(history/)에는 Baa 값이 빠지는지를 본다
(지어낸 숫자로).
FORBIDDEN_TEXT(다른 참고 자료 테스트들이 가져다 쓴다)는 그대로 두고, 해석 쪽을 뺀 나머지에만 적용한다.
"""
import os, sys, re, json, copy, datetime, tempfile, unittest, shutil, subprocess
from unittest import mock

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import regime_rules as rr
import regime_check as rck
import render_public as rp
from test_regime import make_cache, run_cli, BASE_IND

TODAY = datetime.date(2026, 9, 22)

# 공개본에 나오면 안 되는 문자열 — 시나리오 문자·이름, 내부 ID, 해석 문구, 개인 견해로 이어지는 말
FORBIDDEN_TEXT = ["→", "F-0", "S-01", "A′", "D1", "D2", "O/W", "U/W", "붕괴", "코호트", "재정", "신용수축",
                  "시나리오", "국면", "C19", "시트", "판단로그", "LBO", "전사 위험", "강세장", "진행", "선행", "경보",
                  "반증", "신호", "후보", "PIK", "빈티지", "임대료"]
# 공개본 어디에도 없어야 하는 키 — 원본의 내부 필드(시나리오 이름표는 2026-10-30부터 scenario로 싣는다)
FORBIDDEN_KEYS = {"log_ids", "text", "source", "regime_inputs", "manual", "signals", "indicators"}
# 해석 쪽(reading·regime 절)에도 없어야 하는 것 — 내부 ID(판단 기록 번호), 비공개 보고서·시트 참조
READING_FORBIDDEN = ["F-0", "S-01", "F-01", "판단로그", "판단 로그", "보고서", "00장", "01장", "7절", "미래 지도", "C19", "C24",
                     "시트", "운영기준", "regime_latest"]
HY_PUBLIC = "HY OAS 값 비공개(문턱은 규칙 문장)"          # 신용 스프레드 해석 줄의 ICE 값 자리


def expected_reading(sig):
    """원본 해석 문장 → 기대하는 공개 줄(구현과 따로 쓴다): 내부 ID 하나를 빼고, credit_spread는 원본의 Baa 부분 그대로 +
    HY OAS 값 자리의 고정 문구 + 결론 구절."""
    t = sig["text"]
    if sig["key"] == "credit_spread" and " → " in t:
        head, _, clause = t.rpartition(" → ")
        baa, sep, _ = head.partition(" · HY OAS ")
        assert sep, head
        return f"{baa} · {HY_PUBLIC} → {clause}"
    return t.replace("(F-01-C-01)", "")


def without_reading(pub):
    """해석 쪽(규칙의 scenario·reading, regime 절)을 뺀 사본 — 예전 원칙(FORBIDDEN_TEXT)은 여기에 그대로 적용한다."""
    p = copy.deepcopy(pub)
    p.pop("regime", None)
    for r in p["rules"]:
        r.pop("scenario", None)
        r.pop("reading", None)
    return p
def without_baa(pub):
    """신용 스프레드 카드의 BAA10Y 관측값과 해석 줄을 비운 사본 — 공개본과 날짜별 기록이 그 밖에서 같은지 견줄 때(구현과 따로 쓴다)."""
    p = copy.deepcopy(pub)
    card = next(r for r in p["rules"] if r["key"] == "credit_spread")
    for o in card["observations"]:
        if o["series"] == ["BAA10Y"]:
            o["value"] = None
    card["reading"] = None
    return p


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
    s |= {rp.BAA_DERIVED, rp.MOODYS_NOTICE}
    for spec in table.values():
        s |= {spec["title"], spec["rule"]}
        for o in spec["obs"]:
            s |= {o["label"], o["unit"], *o["series"]}
    for sid, (label, _, _) in rr.SERIES.items():
        s |= {sid, label, rp.OWNER[sid], rp.FRED_URL.format(sid), rp.citation(sid, TODAY.isoformat())}
    # 해석 쪽의 고정 문구(2026-10-30) — 이름표·읽는 법·국면 메모·방향·ON/OFF·수동 항목·그 밖의 관측값
    s |= {spec["scenario"] for spec in table.values()} | {rp.READING_NOTICE, rp.BUFFER_NOTE, *rp.REGIME_NOTE.values()}
    s |= set(rp.legend()) | {"상승", "하락", "보합", "ON", "OFF", "?", "Y", "N", "A", "A′", "B", "C"}
    s |= set(rp.MANUAL_PUBLIC.values()) | set(rp.CADENCES)
    for _, label, unit, series, _ in rp.MORE_VALUES:
        s |= {label, unit, *series}
    return s


HEADLINE_RE = re.compile(r"^핵심 신호 \d+/\d+ 발동, 판정불가 \d+ · 중립 규칙 \d+/\d+ 충족$")


NAN_RE = re.compile(r"\b(?:nan|inf|infinity)\b", re.I)                    # 숫자 자리에 새어 나온 글자(financing 같은 낱말은 아님)


def dropped_texts():
    """render가 남길 수 있는 '싣지 않음' 경고 전부 — 규칙 제목·개수만 넣는다(테스트 쪽에서 따로 만든다)."""
    titles = [spec["title"] for spec in rp.public_rules().values()]
    out = {rp.DROPPED["reading"].format(t) for t in titles} | {rp.DROPPED["label"].format(t) for t in titles}
    return out | {rp.DROPPED["manual"].format(n) for n in range(1, 20)} | {rp.DROPPED["note"], rp.DROPPED["section"]}


def drops(pub):
    """공개본 warnings 가운데 render가 남긴 '싣지 않음' 경고."""
    return [w for w in pub["warnings"] if w in dropped_texts()]


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
        # 해석 줄은 원본 문장에서 기대하는 공개 줄(expected_reading)과 같을 때만, 국면 참고값 줄은 ReferenceTest가 글자까지 본다.
        # '싣지 않음' 경고(rp.DROPPED)는 허용 목록에 없다 — 지금 공유 규칙의 원본이 정해 둔 꼴에서 벗어나면 여기서 실패한다
        allowed = allowed_strings()
        for raw, pub in zip((self.raw, self.raw2), self.pubs):
            ok = allowed | {expected_reading(s) for s in raw["signals"]} | set(pub["regime"]["reference"]["lines"])
            _, _, strs = walk(pub)
            bad = [s for s in strs if not (s in ok or DATE_RE.match(s) or TS_RE.match(s) or HEADLINE_RE.match(s)
                                            or s.startswith(rp.WARNING_PREFIXES))]
            self.assertEqual(bad, [])

    def test_forbidden_text_and_raw_texts_absent(self):
        # 예전 원칙(해석·시나리오 낱말 없음)은 해석 쪽을 뺀 나머지에 그대로. 해석 쪽에는 내부 ID·비공개 보고서 참조가 없어야 한다
        for raw, pub in zip((self.raw, self.raw2), self.pubs):
            dump = json.dumps(without_reading(pub), ensure_ascii=False)
            for word in FORBIDDEN_TEXT:
                self.assertNotIn(word, dump, word)
            for s in raw["signals"]:
                self.assertNotIn(s["text"], dump)
            full = json.dumps(pub, ensure_ascii=False)
            for word in READING_FORBIDDEN:
                self.assertNotIn(word, full, word)
            credit = next(s for s in raw["signals"] if s["key"] == "credit_spread")
            self.assertIn("Baa−10Y ", credit["text"])                   # 원본 문장에는 값이 있다 — 그 문장은 어디에도 없다
            self.assertNotIn(credit["text"].rpartition(" → ")[0], full)
            for s in raw["signals"]:
                for lid in s["log_ids"]:
                    self.assertNotIn(lid, full)

    def test_forbidden_keys_absent(self):
        for pub in self.pubs:
            keys, _, _ = walk(pub)
            self.assertEqual(FORBIDDEN_KEYS & set(keys), set())

    def test_restricted_series_values_absent(self):
        # 해석 쪽(reading·regime 절)까지 공개본 전체를 훑는다 — S&P 13주 변화는 방향만, ICE 값은 어디에도.
        # Moody's Baa는 2026-10-30부터 값을 싣는다(BaaPublishedTest) — 여기서는 제한 목록에 없음만 본다
        ind, inputs = self.raw["indicators"], self.raw["regime_inputs"]
        self.assertNotIn("BAA10Y", rp.RESTRICTED)
        self.assertEqual(set(rp.RESTRICTED), {"SP500", "BAMLH0A0HYM2", "BAMLC0A0CM"})
        restricted = [ind["hy_oas"]["value"], ind["ig_oas"]["value"], inputs["sp_13w_pct"]]
        self.assertTrue(all(v is not None for v in restricted))
        _, nums, strs = walk(self.pubs[0])
        str_nums = [float(x) for s in strs for x in re.findall(r"-?\d+\.\d+", s)]   # 문자열에 섞여 새는 경우
        # 반올림해 싣더라도 걸리게 비교한다: JSON 숫자는 소수 둘째·셋째 자리, 문자열 속 숫자는 첫째 자리까지.
        # 반올림 결과가 정수(0.0 등)면 공개본의 개수·경과일·작은 변화값과 겹쳐 유출인지 가릴 수 없으므로 건너뛴다
        checked = [v for v in restricted if v != int(v)]
        self.assertEqual(len(checked), 3)
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
        rows = {h["series"]: h for h in self.pubs[0]["data_health"]}
        self.assertEqual((rows["BAA10Y"]["display"], rows["BAA10Y"]["owner"]), ("value", "Moody's"))
        self.assertEqual({h["series"] for h in self.pubs[0]["data_health"] if h["display"] == "status_only"},
                         {"SP500", "BAMLH0A0HYM2", "BAMLC0A0CM"})
        credit = next(r for r in self.pubs[0]["rules"] if r["key"] == "credit_spread")
        self.assertEqual([s["series"] for s in credit["restricted_series"]], ["BAMLH0A0HYM2"])   # ICE는 그대로 값 비공개

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
                "reserves_multiplier": ["reserves_gdp_low", "reserves_gdp_rise_3m", "reserves_pce_floor"],
                "core_momentum": ["core_mom_gap"], "unemployment_rise": ["unrate_rise"]}
        for key, ths in uses.items():
            for th in ths:
                orig = rr.TH[th]
                rr.TH[th] = 131 if th == "corr_run_days" else 12.345
                try:                                  # 원본도 같은 임계값으로 다시 판정한다(해석 구절에 임계값이 든 규칙이 있다)
                    raw = {**self.raw, "signals": rr.evaluate(rck.flat(self.raw["indicators"]))}
                    rule = next(r for r in rp.render(raw)["rules"] if r["key"] == key)["rule"]
                finally:
                    rr.TH[th] = orig
                self.assertIn("131" if th == "corr_run_days" else "12.345", rule, (key, th))

    def test_new_rule_sentences_and_observations(self):
        # 2026-10-14 두 규칙 — 문장은 정해 둔 그대로(임계값만 TH), 관측치는 원본 지표의 값·자료일
        pub = {r["key"]: r for r in self.pubs[0]["rules"]}
        self.assertEqual(pub["core_momentum"]["rule"], "근원 PCE 6개월 연율이 전년비보다 0.5%p 이상 높으면 충족 "
                         "(기준 달이 빠진 구간은 계산하지 않음)")
        self.assertEqual(pub["unemployment_rise"]["rule"], "실업률 3개월 평균이 직전 12개월 중 가장 낮은 3개월 평균보다 "
                         "0.5%p 이상 높으면 충족 (빠진 달이 낀 평균은 2개월로 계산)")
        ind = self.raw["indicators"]
        rnd = lambda v: round(v, 3)
        got = [(o["label"], o["value"], o["asof"], o["computed"], o["series"]) for o in pub["core_momentum"]["observations"]]
        self.assertEqual(got, [
            ("근원 PCE 6개월 연율", rnd(ind["core_pce_a6"]["value"]), ind["core_pce_a6"]["asof"], True, ["PCEPILFE"]),
            ("근원 PCE 전년비", rnd(ind["core_pce_yoy"]["value"]), ind["core_pce_yoy"]["asof"], True, ["PCEPILFE"]),
            ("차이(6개월 연율 − 전년비)", rnd(ind["core_mom"]["value"]), ind["core_mom"]["asof"], True, ["PCEPILFE"])])
        ur = ind["unrate_rise"]
        got = [(o["label"], o["value"], o["asof"], o["computed"], o["series"])
               for o in pub["unemployment_rise"]["observations"]]
        self.assertEqual(got, [
            ("상승 폭(3개월 평균 − 직전 12개월 최저)", rnd(ur["value"]), ur["asof"], True, ["UNRATE"]),
            ("실업률 3개월 평균", rnd(ur["u3"]), ur["asof"], True, ["UNRATE"]),
            ("직전 12개월 최저 3개월 평균", rnd(ur["low"]), ur["low_month"], True, ["UNRATE"])])   # 자료일 = 최저 창의 끝 달
        self.assertEqual(ur["low_month"], "2025-08-01")               # make_cache의 손 계산(test_regime BuildTest와 같다)
        self.assertNotEqual(ur["low_month"], ur["asof"])
        for key in ("core_momentum", "unemployment_rise"):          # 해석 줄 = 원본 문장 그대로(내부 ID가 없는 중립 규칙)
            text = next(s for s in self.raw["signals"] if s["key"] == key)["text"]
            self.assertEqual((pub[key]["scenario"], pub[key]["reading"]), ("—", text))
            self.assertNotIn(text, json.dumps(without_reading(self.pubs[0]), ensure_ascii=False))

    def test_unemployment_missing_month_warning_is_public(self):
        # 실업률 결측월(make_cache의 2025-10) 경고는 공개 — 빠진 달과 계산 방식·개정치 안내뿐이다
        warns = [w for w in self.pubs[0]["warnings"] if w.startswith("실업률 결측월")]
        self.assertEqual(len(warns), 1)
        self.assertIn("2025-10", warns[0])
        self.assertIn(warns[0], self.raw["warnings"])

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
        self.assertEqual({r["key"] for r in pub["rules"] if r["notices"]}, {"sofr", "credit_spread"})   # Baa 고지는 BaaPublishedTest
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
        self.assertEqual(rows["UNRATE"]["citation"], "U.S. Bureau of Labor Statistics, Unemployment Rate [UNRATE], "
                         "retrieved from FRED, Federal Reserve Bank of St. Louis; "
                         "https://fred.stlouisfed.org/series/UNRATE, September 22, 2026.")
        self.assertEqual((rows["UNRATE"]["owner"], rows["UNRATE"]["display"]), ("BLS", "value"))   # 공공 자료 — 제한 아님
        self.assertEqual(set(rp.FRED_SOURCE), set(rr.SERIES))
        self.assertEqual(set(rp.FRED_TITLE), set(rr.SERIES))

    def test_licence_line_covers_every_source_the_site_carries(self):
        # 꼬리말의 자료 이용 조건 한 줄 — FRED(시리즈별 표시)·뉴욕 연은·IMF·DTCC·SEC EDGAR·시카고 연은을 모두 덮는다(2026-10-30)
        t = rp.DATA_LICENSE
        for part in ("MIT", "FRED 이용약관", "시리즈별 저작권·인용 표시", "시카고 연은 NFCI", "인용 필요",
                     "© International Monetary Fund", "newyorkfed.org 이용약관", "SOFR", "프라이머리 딜러", "ACM",
                     "DTCC", "Reg SBSR", "SEC EDGAR", "미 정부 공개 자료",
                     # 2026-10-30 운영자 결정 — Moody's Baa(FRED 경유, 인용 + 고지), 나스닥 낙폭, 연준 이사회 EBP, 뉴욕 연은 CMDI
                     "Moody's Baa−10년 스프레드는 FRED 경유 인용 필요 자료", "Moody's 저작권 고지", "나스닥100", "Nasdaq CTA AI",
                     "연준 이사회", "초과 채권 프리미엄(EBP)", "CMDI"):
            self.assertIn(part, t)
        self.assertNotIn("나머지는 FRED", t)                                  # 옛 문장(출처가 둘뿐이던 때)
        self.assertEqual(rp.attribution(2026)[-1], t)
        self.assertIn(t, self.pubs[0]["attribution"])
        self.assertIn(rp.MOODYS_NOTICE, self.pubs[0]["attribution"])         # 꼬리말에 고지 문단 그대로
        self.assertFalse(re.search(r"\d+\.\d+", t + rp.MOODYS_NOTICE))       # 그래프 자료(charts.json)에도 실린다 — 소수 없음
        # EBP 공공 자료 구절과 CMDI가 뉴욕 연은 이용약관 괄호 안에 있는지(출처마다 이용 조건이 맞게 붙었는지)
        self.assertRegex(t, r"초과 채권 프리미엄\(EBP\)은 미 정부 공개 자료")
        self.assertRegex(t, r"뉴욕 연은 자료\([^)]*CMDI\)는 newyorkfed\.org 이용약관")

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
        self.assertEqual(a, json.loads(json.dumps(self.pubs[0])))
        self.assertEqual(without_baa(a), without_baa(b))                       # 기록은 Baa 값만 빠진 사본(BaaPublishedTest)
        self.assertNotEqual(a, b)
        self.assertEqual(a["schema"], rp.SCHEMA)

    def test_older_date_does_not_replace_public(self):
        rp.write(self.out, self.pubs[0])
        older = {**self.pubs[0], "date": "2026-06-15"}
        self.assertFalse(rp.write(self.out, older))
        with open(os.path.join(self.out, "public.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["date"], "2026-09-22")
        self.assertTrue(os.path.exists(os.path.join(self.out, "history", "2026-06-15.json")))


def built_raw(tmp, prev_regime=None):
    """합성 FRED 캐시로 만든 원본 결과(TODAY)."""
    work = os.path.join(tmp, ".work")
    make_cache(os.path.join(work, "fred"))
    rck.build(work, TODAY, offline=True, prev_regime=prev_regime)
    with open(os.path.join(work, "raw", "latest.json"), encoding="utf-8") as f:
        return json.load(f)


def stable(pub):
    """생성 시각을 뺀 공개본 글자 — 같은 공개본인지 견줄 때."""
    return json.dumps({k: v for k, v in pub.items() if k != "generated_at"}, ensure_ascii=False, sort_keys=True)


# 해석 줄의 모든 갈래를 타게 하는 입력 — regime_rules.evaluate의 분기마다 하나 이상(BASE_IND에 덮어쓴다)
BRANCHES = [
    {}, {"ci_yoy": 5.0}, {"ci_valid": False},
    {"ndfi_yoy": 5.0, "ndfi_share": None}, {"ndfi_yoy": None},
    {"hy_oas": 5.0}, {"baa10y": None, "hy_oas": None}, {"hy_oas": None, "baa10y_from_low": None, "baa10y_pct": None},
    {"rho60_sign": "+", "rho60_run": 30, "rho60": 0.2}, {"rho60_sign": "+", "rho60_run": 130, "rho60": 0.31},
    {"rho60": None},
    {"t10y2y": -0.5}, {"t10y2y": None},
    {"dfii10": 1.5, "bei_chg_3m": 0.1}, {"dfii10": 1.5, "bei_chg_3m": 0.0}, {"dfii10": 1.5, "bei_chg_3m": None, "bei": None},
    {"dfii10": None},
    {"core_pce_yoy": 2.5, "core_cpi_yoy": None, "core_gap": None}, {"core_pce_yoy": None},
    {"tp_chg_3m": -0.3}, {"tp_chg_3m": None}, {"tp": None},
    {"sofr_chg_3m": 0.3}, {"sofr_chg_3m": None}, {"sofr": None},
    {"reserves_gdp": 8.5, "mult": None}, {"reserves_gdp_chg_3m": 0.4}, {"reserves_gdp_chg_3m": None}, {"reserves_gdp": None},
    {"emp_yoy": -1.0}, {"emp_yoy": None},
    {"core_mom": 0.6, "core_pce_a6": 3.94}, {"core_mom": None}, {"core_pce_a6": None},
    {"unrate_rise": 0.6}, {"unrate_rise": None}, {"unrate_n_used": 2, "unrate_low_month": None},
]


class ReadingTest(unittest.TestCase):
    """규칙마다의 시나리오 이름표와 해석 줄(2026-10-30) — 원본 문장에서 내부 ID만 뺀 것, 제한 값이 든 문장은 다시 쓴 것."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.raw = built_raw(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def render_with(self, **kw):
        sig = rr.evaluate({**BASE_IND, **kw})
        return sig, rp.render({**self.raw, "signals": sig})

    def test_every_branch_matches_the_expected_public_line(self):
        hit = {k: set() for k in rp.readings()}
        for kw in BRANCHES:
            sig, pub = self.render_with(**kw)
            # 지금 공유 규칙(regime_rules.evaluate)의 문장은 모두 정해 둔 꼴에 맞는다 — 런타임은 닫힌 채 빼지만 테스트는 엄격하다
            self.assertEqual(drops(pub), [], kw)
            for s, r in zip(sig, pub["rules"]):
                self.assertIsNotNone(r["reading"], (s["key"], kw))
                self.assertEqual(r["scenario"], s["scenario"], (s["key"], kw))
                self.assertEqual(r["reading"], expected_reading(s), (s["key"], kw))
                hit[s["key"]].add(r["reading"].rpartition(" → ")[2] if " → " in r["reading"] else "plain:" + r["reading"])
        # 정해 둔 구절이 모두 한 번 이상 쓰인다 — 원본 규칙 엔진의 갈래를 빠짐없이 검토했고, 죽은 항목이 없다
        for key, spec in rp.readings().items():
            for clause in spec["clauses"].values():
                self.assertIn(clause, hit[key], key)
            plains = {h for h in hit[key] if h.startswith("plain:")}
            for pat in spec["plain"]:
                self.assertTrue(any(re.fullmatch(pat, h[6:]) for h in plains), (key, pat))

    def test_scenario_tags_follow_the_engine_and_neutral_rules_are_dashes(self):
        sig, pub = self.render_with()
        self.assertEqual([r["scenario"] for r in pub["rules"]], [s["scenario"] for s in sig])
        neutral = {r["key"] for r in pub["rules"] if r["scenario"] == "—"}
        self.assertEqual(neutral, {"core_momentum", "unemployment_rise"})
        self.assertEqual({r["key"]: r["scenario"] for r in pub["rules"]}["employment"], "공통")

    def test_log_id_is_cut_from_the_one_clause_that_carries_it(self):
        sig, pub = self.render_with()                       # BASE_IND: 실질 2.61% → 'C 반증(F-01-C-01)'
        raw = next(s for s in sig if s["key"] == "real_rate_bei")["text"]
        got = next(r for r in pub["rules"] if r["key"] == "real_rate_bei")["reading"]
        self.assertTrue(raw.endswith("C 반증(F-01-C-01)"))
        self.assertTrue(got.endswith("→ 실질 2% 위 = C 반증"))

    def test_credit_spread_line_carries_baa_values_but_no_ice_value(self):
        # 지어낸 값 — Baa 쪽은 원본 서식 그대로 실리고, HY OAS(ICE) 값은 어떤 반올림으로도 실리지 않는다
        for kw, baa, clause in (
                ({"baa10y": 2.37, "baa10y_from_low": 0.21, "baa10y_pct": 0.6183, "hy_oas": 3.917},
                 "Baa−10Y 2.37%p(바닥 대비 +0.21, 1990년 이후 하위 61.8%)", "확대 없음(A 유지)"),
                ({"baa10y": 2.37, "baa10y_from_low": 0.21, "baa10y_pct": 0.6183, "hy_oas": 5.083},
                 "Baa−10Y 2.37%p(바닥 대비 +0.21, 1990년 이후 하위 61.8%)", "D 선행 신호"),
                ({"baa10y": None, "baa10y_from_low": None, "baa10y_pct": None, "hy_oas": 6.127},
                 "Baa−10Y —%p(바닥 대비 —, 1990년 이후 하위 —)", "D 선행 신호"),
                ({"hy_oas": None, "baa10y_from_low": None, "baa10y_pct": None},
                 "Baa−10Y 1.44%p(바닥 대비 —, 1990년 이후 하위 —)", rp.NO_VERDICT)):
            sig, pub = self.render_with(**kw)
            got = next(r for r in pub["rules"] if r["key"] == "credit_spread")["reading"]
            self.assertEqual(got, f"{baa} · {HY_PUBLIC} → {clause}", kw)
            raw = next(s for s in sig if s["key"] == "credit_spread")["text"]
            self.assertIn("· HY OAS ", raw)                                          # 원본에는 HY 값 자리가 있다
            hy = kw.get("hy_oas")
            dump = json.dumps(pub, ensure_ascii=False)
            if hy is not None:
                for txt in (f"{hy:.2f}", f"{hy:.1f}", f"{hy:.3f}"):
                    self.assertNotIn(txt, dump, (kw, txt))
            self.assertEqual(re.findall(r"\d+\.\d+", got.split(" · HY OAS ")[1]), [])   # HY 쪽에는 숫자 없음

    def test_headline_counts_core_and_neutral_separately(self):
        sig, pub = self.render_with(hy_oas=5.0, t10y2y=-0.5, sofr_chg_3m=None, core_mom=0.6, core_pce_a6=3.94)
        core = [s for s in sig if s["scenario"] != "—"]
        neu = [s for s in sig if s["scenario"] == "—"]
        n_f, n_u = sum(s["fired"] is True for s in core), sum(s["fired"] is None for s in core)
        k = sum(s["fired"] is True for s in neu)
        g = pub["regime"]
        self.assertEqual(g["headline"], f"핵심 신호 {n_f}/{len(core)} 발동, 판정불가 {n_u} · 중립 규칙 {k}/{len(neu)} 충족")
        self.assertEqual((g["core"], g["neutral"]), ({"total": 11, "met": n_f, "unknown": n_u},
                                                     {"total": 2, "met": 1, "unknown": 0}))
        self.assertGreaterEqual(n_f, 2)
        self.assertEqual(n_u, 1)

    def test_readings_follow_the_threshold_table(self):
        orig = rr.TH["core_mom_gap"]
        rr.TH["core_mom_gap"] = 0.75
        try:
            sig, pub = self.render_with(core_mom=0.8, core_pce_a6=4.14)
        finally:
            rr.TH["core_mom_gap"] = orig
        got = next(r for r in pub["rules"] if r["key"] == "core_momentum")["reading"]
        self.assertTrue(got.endswith("→ 0.75%p 이상(6개월 연율이 전년비보다 높음)"), got)


class RestrictedInvarianceTest(unittest.TestCase):
    """재배포 제한 입력(S&P·ICE)을 바꿔도 판정·방향·ON/OFF가 같으면 공개본이 한 글자도 바뀌지 않는다 —
    반올림 일치를 찾는 검사와 달리 우연히 같은 숫자에 흔들리지 않는다. Moody's Baa는 2026-10-30부터 값을 싣는다 —
    Baa를 바꾸면 공개본이 바뀌고(실린다), 그 차이는 신용 스프레드 카드 안뿐이다."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.raw = built_raw(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def variant(self, ind_kw, sp=None, extra_ind=None, baa=None):
        """ind_kw: 판정에 넣는 평면 값, extra_ind: 원본 지표의 value, baa: (수준, 12개월 저점 대비, 1990년 이후 분위) —
        판정과 원본 지표 양쪽에 같이 넣는다(공개 관측값과 해석 줄이 같은 Baa를 보게)."""
        raw = copy.deepcopy(self.raw)
        if baa is not None:
            b = raw["indicators"]["baa10y"]
            b["value"], b["from_low_12m"], b["pct_since_1990"] = baa
            ind_kw = {**ind_kw, "baa10y": baa[0], "baa10y_from_low": baa[1], "baa10y_pct": baa[2]}
        flat = {**rck.flat(raw["indicators"]), **ind_kw}
        raw["signals"] = rr.evaluate(flat)
        for k, v in (extra_ind or {}).items():
            raw["indicators"][k]["value"] = v
        if sp is not None:
            raw["regime_inputs"]["sp_13w_pct"] = sp
        return rp.render(raw)

    def test_values_inside_the_same_verdict_do_not_change_the_page(self):
        sp0 = self.raw["regime_inputs"]["sp_13w_pct"]
        baa = (1.44, 0.05, 0.015)                                        # Baa는 같게 — 실리는 값이다
        a = self.variant({"hy_oas": 2.68}, sp=sp0, extra_ind={"ig_oas": 0.81, "hy_oas": 2.68}, baa=baa)
        b = self.variant({"hy_oas": 3.37}, sp=sp0 + 4.7, extra_ind={"ig_oas": 0.97, "hy_oas": 3.37}, baa=baa)
        self.assertEqual(stable(a), stable(b))
        c = self.variant({"hy_oas": 5.02}, sp=-3.3, baa=baa)              # 발동 쪽, 하락 쪽에서도
        d = self.variant({"hy_oas": 6.41}, sp=-11.8, extra_ind={"ig_oas": 1.93, "hy_oas": 6.41}, baa=baa)
        self.assertEqual(stable(c), stable(d))
        self.assertNotEqual(stable(a), stable(c))                        # 판정·방향이 바뀌면 바뀐다(검사가 헛돌지 않게)

    def test_baa_values_reach_only_the_credit_card(self):
        # 같은 판정(확대 없음) 안에서 Baa만 바꾸면 공개본이 바뀐다 — 바뀌는 곳은 신용 스프레드 카드의 관측값·해석 줄뿐
        a = self.variant({}, baa=(1.44, 0.05, 0.015))
        b = self.variant({}, baa=(1.71, 0.13, 0.083))
        self.assertNotEqual(stable(a), stable(b))
        for x, y in zip(a["rules"], b["rules"]):
            if x["key"] != "credit_spread":
                self.assertEqual(x, y)
            else:
                self.assertEqual(x["status"], y["status"])
                self.assertNotEqual((x["observations"], x["reading"]), (y["observations"], y["reading"]))
        rest = lambda p: stable({**p, "rules": [r for r in p["rules"] if r["key"] != "credit_spread"]})
        self.assertEqual(rest(a), rest(b))

    def test_sp_change_reaches_the_page_only_as_a_direction(self):
        for sp, want in ((5.04, "상승"), (-4.4, "하락"), (1.37, "보합"), (-2.0, "보합"), (2.0000001, "상승")):
            ref = self.variant({}, sp=sp)["regime"]["reference"]
            self.assertEqual(ref["sp_13w"], want, sp)
            dump = json.dumps(ref, ensure_ascii=False)
            for digits in (1, 2):
                txt = f"{abs(round(sp, digits)):.{digits}f}"
                if txt not in ("2.0", "2.00"):                            # 완충 문턱(±2%)은 읽는 법에 적혀 있다
                    self.assertNotIn(txt, dump, sp)

    def test_direction_agrees_with_the_regime_buffer(self):
        y10 = 30.0                                                       # 금리 쪽은 완충 밖 — 주가 쪽만 본다
        for sp in (-5.0, -2.0001, -2.0, -0.3, 0.0, 1.999, 2.0, 2.0001, 7.0):
            cand, note = rr.classify_regime(sp, y10, None)
            self.assertEqual(rp.sp_direction(sp) == "보합", note.startswith("완충"), sp)


class ReferenceTest(unittest.TestCase):
    """국면 참고값 — 직전 국면 없이 다시 계산, S&P는 방향만, t2·t4는 ON/OFF만, 글자까지."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.raw = built_raw(cls.tmp, prev_regime="B")         # 원본에는 사람이 넣은 직전 국면이 있다 — 공개 계산은 쓰지 않는다

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def ref(self, sp=None, y10=None, rho=None, cpi=None, trig=None):
        raw = copy.deepcopy(self.raw)
        ri, ind = raw["regime_inputs"], raw["indicators"]
        if sp is not None:
            ri["sp_13w_pct"] = None if sp == "none" else sp
        if y10 is not None:
            ri["y10_13w_bp"] = y10
        if rho is not None:
            ind["rho60"]["value"], ind["rho60"]["run_days"] = rho
        if cpi is not None:
            ind["core_cpi_yoy"]["value"] = None if cpi == "none" else cpi
        if trig is not None:
            ri["transition"].update(trig)
        return rp.render(raw)["regime"]["reference"]

    def test_base_lines(self):
        self.assertEqual(self.raw["regime_inputs"]["regime_prev"], "B")
        ref = self.ref()
        self.assertEqual(ref["lines"], [
            "국면 후보 A (사분면 판정) · S&P 500 13주 상승 · 미 10년 13주 +13bp",
            "ρ60 +1.00 (390일 연속)",
            "근원 CPI<3% Y (근원 CPI 2.43% · 근원 PCE 3.29% — D1/D2 갈림은 근원 PCE 기준)",
            "전환 경계 자동 트리거 0/2 (t2 OFF · t4 OFF; t1·t3 수동, 넷 중 둘 이상이면 ON)"])
        self.assertEqual((ref["candidate"], ref["sp_13w"], ref["y10_13w_bp"], ref["rho60_alert"], ref["core_cpi_lt3"]),
                         ("A", "상승", 13.0, False, "Y"))
        self.assertEqual((ref["sp_asof"], ref["y10_asof"]), ("2026-09-21", "2026-09-18"))
        self.assertNotIn("prev", json.dumps(ref))

    def test_buffer_is_undecided_without_the_human_previous_regime(self):
        raw = copy.deepcopy(self.raw)
        raw["regime_inputs"]["sp_13w_pct"] = 1.37
        raw["regime_inputs"]["regime_candidate"] = "B"                  # 원본은 직전 국면(B)을 이어받았다
        ref = rp.render(raw)["regime"]["reference"]
        self.assertIsNone(ref["candidate"])
        self.assertEqual(ref["candidate_note"], rp.BUFFER_NOTE)
        self.assertEqual(ref["lines"][0], f"국면 후보 판정불가 ({rp.BUFFER_NOTE}) · S&P 500 13주 보합(±2% 안) · 미 10년 13주 +13bp")

    def test_quadrants_and_the_a_prime_alert(self):
        ref = self.ref(sp=-4.4, y10=25.0, rho=(-0.3, 40))
        self.assertEqual((ref["candidate"], ref["rho60_alert"]), ("A′", False))
        self.assertEqual(ref["lines"][0], "국면 후보 A′ (사분면 판정) · S&P 500 13주 하락 · 미 10년 13주 +25bp")
        ref = self.ref(sp=4.4, y10=25.0, rho=(-0.3, 40))
        self.assertEqual((ref["candidate"], ref["rho60_alert"]), ("A", True))
        self.assertEqual(ref["lines"][1], "ρ60 -0.30 (40일 연속) ⚠ A 국면에서 음(−) = A′ 경보")
        self.assertEqual(self.ref(sp=4.4, y10=-25.0)["candidate"], "C")
        self.assertEqual(self.ref(sp=-4.4, y10=-25.0)["candidate"], "B")
        ref = self.ref(sp="none")
        self.assertEqual((ref["candidate"], ref["sp_13w"]), (None, None))
        self.assertEqual(ref["lines"][0], "국면 후보 판정불가 (재료 없음) · S&P 500 13주 — · 미 10년 13주 +13bp")

    def test_core_cpi_flag_and_transition_status(self):
        ref = self.ref(cpi=3.1, trig={"t2": True, "t4": None})
        self.assertEqual(ref["core_cpi_lt3"], "N")
        self.assertEqual(ref["transition"], {"t2": "ON", "t4": "?", "auto_on": 1})
        self.assertEqual(ref["lines"][3], "전환 경계 자동 트리거 1/2 (t2 ON · t4 ?; t1·t3 수동, 넷 중 둘 이상이면 ON)")
        ref = self.ref(cpi="none", trig={"t2": True, "t4": True})
        self.assertEqual(ref["lines"][2], "근원 CPI<3% ? (근원 CPI —% · 근원 PCE 3.29% — D1/D2 갈림은 근원 PCE 기준)")
        self.assertEqual(ref["transition"]["auto_on"], 2)

    def test_core_cpi_flag_is_n_at_exactly_three(self):
        # 비공개 규칙과 같다: 3.0 '미만'일 때만 Y — 정확히 3.0은 N
        for cpi, want in ((3.0, "N"), (2.999999, "Y"), (3.000001, "N"), (0.0, "Y")):
            ref = self.ref(cpi=cpi)
            self.assertEqual(ref["core_cpi_lt3"], want, cpi)
            self.assertTrue(ref["lines"][2].startswith(f"근원 CPI<3% {want} "), ref["lines"][2])

    def test_non_numbers_are_missing_values_not_nan(self):
        nan, inf = float("nan"), float("inf")
        ref = self.ref(sp=nan, y10=inf, rho=(nan, nan), cpi=nan)
        self.assertEqual((ref["candidate"], ref["candidate_note"], ref["sp_13w"]), (None, "재료 없음", None))
        self.assertEqual((ref["y10_13w_bp"], ref["rho60"], ref["rho60_run_days"], ref["core_cpi_lt3"], ref["core_cpi_yoy"]),
                         (None, None, None, None, None))
        self.assertEqual(ref["lines"][1], "ρ60 — (—일 연속)")
        self.assertTrue(ref["lines"][2].startswith("근원 CPI<3% ? (근원 CPI —% "), ref["lines"][2])
        dump = json.dumps(ref, ensure_ascii=False, allow_nan=False)            # NaN이 남았으면 여기서 ValueError
        self.assertIsNone(NAN_RE.search(dump))

    def test_every_engine_note_is_known(self):
        # 지금 공유 규칙의 classify_regime이 낼 수 있는 메모(사분면·완충·재료 없음)는 모두 공개 문구가 있다 — 빠지면 실패한다
        for sp in (None, -9.0, -2.0, -1.0, 0.0, 1.0, 2.0, 9.0):
            for y10 in (None, -40.0, -10.0, 0.0, 10.0, 40.0):
                raw = copy.deepcopy(self.raw)
                raw["regime_inputs"]["sp_13w_pct"], raw["regime_inputs"]["y10_13w_bp"] = sp, y10
                pub = rp.render(raw)
                self.assertEqual(drops(pub), [], (sp, y10))
                self.assertEqual(len(pub["regime"]["reference"]["lines"]), 4, (sp, y10))
                self.assertIsNotNone(pub["regime"]["reference"]["candidate_note"], (sp, y10))

    def test_unknown_regime_note_drops_only_the_first_line(self):
        base = rp.render(self.raw)["regime"]["reference"]
        with mock.patch.object(rr, "classify_regime", return_value=("A", "새 메모 9.87")):
            pub = rp.render(self.raw)
        ref = pub["regime"]["reference"]
        self.assertEqual((ref["candidate"], ref["candidate_note"]), (None, None))
        self.assertEqual(ref["lines"], base["lines"][1:])                       # 나머지 세 줄은 그대로
        self.assertEqual(drops(pub), [rp.DROPPED["note"]])
        self.assertNotIn("9.87", json.dumps(pub, ensure_ascii=False))
        self.assertNotIn("새 메모", json.dumps(pub, ensure_ascii=False))
        self.assertEqual(len(pub["rules"]), len(self.raw["signals"]))          # 공개본 전체는 그대로 만들어진다


# FRED BAA10Y 시리즈 페이지 Notes의 Moody's 고지(2026-10-30 페이지에서 옮김) — 구현의 상수와 따로 적어 글자까지 견준다
MOODYS_PAGE_TEXT = (
    "©2017, Moody's Corporation, Moody's Investors Service, Inc., Moody's Analytics, Inc. and/or their licensors and "
    "affiliates (collectively, \"Moody's\"). All rights reserved. Moody's ratings and other information (\"Moody's "
    "Information\") are proprietary to Moody's and/or its licensors and are protected by copyright and other intellectual "
    "property laws. Moody's Information is licensed to Client by Moody's. MOODY'S INFORMATION MAY NOT BE COPIED OR "
    "OTHERWISE REPRODUCED, REPACKAGED, FURTHER TRANSMITTED, TRANSFERRED, DISSEMINATED, REDISTRIBUTED OR RESOLD, OR STORED "
    "FOR SUBSEQUENT USE FOR ANY SUCH PURPOSE, IN WHOLE OR IN PART, IN ANY FORM OR MANNER OR BY ANY MEANS WHATSOEVER, BY ANY "
    "PERSON WITHOUT MOODY'S PRIOR WRITTEN CONSENT.")
PRIVATE_BAA = re.compile(r"Baa−10Y (\S+)%p\(바닥 대비 (\S+), 1990년 이후 하위 (\S+)\)")   # 비공개 월간 점검 줄(공유 규칙)의 꼴


class BaaPublishedTest(unittest.TestCase):
    """Moody's Baa−10년(2026-10-30 운영자 결정) — 비공개 월간 점검 줄과 같은 숫자를 카드에 싣고, 그 곁에 계산값 표시·FRED 권장
    인용·Moody's 고지(페이지 그대로)를 싣는다. ICE(HY·IG OAS)·S&P 값은 여전히 어디에도 없다. 숫자는 모두 지어낸 것이다."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.raw = built_raw(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def with_baa(self, level, low, pct, hy=None, ig=None, sp=None):
        raw = copy.deepcopy(self.raw)
        ind = raw["indicators"]
        ind["baa10y"].update({"value": level, "from_low_12m": low, "pct_since_1990": pct})
        if hy is not None:
            ind["hy_oas"]["value"] = hy
        if ig is not None:
            ind["ig_oas"]["value"] = ig
        if sp is not None:
            raw["regime_inputs"]["sp_13w_pct"] = sp
        raw["signals"] = rr.evaluate(rck.flat(ind))
        return raw, rp.render(raw)

    @staticmethod
    def card(pub):
        return next(r for r in pub["rules"] if r["key"] == "credit_spread")

    def test_card_numbers_are_the_private_line_numbers(self):
        # 공유 규칙(regime_rules.evaluate)의 원본 문장 = 비공개 월간 점검 줄. 카드의 세 값을 그 줄의 서식으로 쓰면 같은 글자다
        # (반올림 경계 값 포함: 소수 셋째 자리 5, 분위의 소수 둘째 자리 5)
        for level, low, pct in ((2.37, 0.21, 0.6183), (2.345, 0.125, 0.6185), (1.06, 0.0, 0.0022), (3.9, -0.004, 1.0),
                                (2.71, 0.4049999, 0.99951)):
            raw, pub = self.with_baa(level, low, pct)
            text = next(s for s in raw["signals"] if s["key"] == "credit_spread")["text"]
            want = PRIVATE_BAA.search(text).groups()
            obs = self.card(pub)["observations"]
            self.assertEqual([o["label"] for o in obs], ["Baa−10년 스프레드", "12개월 저점 대비", "1990년 이후 분위(이 값 이하 비율)"])
            self.assertEqual([(o["unit"], o["series"], o["computed"], o["derived"]) for o in obs],
                             [("%p", ["BAA10Y"], False, False), ("%p", ["BAA10Y"], True, False), ("%", ["BAA10Y"], True, False)])
            got = (f"{obs[0]['value']:.2f}", f"{obs[1]['value']:+.2f}", f"{obs[2]['value']:.1f}%")
            self.assertEqual(got, want, (level, low, pct))
            self.assertEqual((obs[0]["value"], obs[1]["value"], obs[2]["value"]),
                             (round(level, 2), round(low, 2), round(pct * 100, 1)))   # 줄의 자릿수 그대로(더 싣지 않는다)
            self.assertTrue(all(o["asof"] == raw["indicators"]["baa10y"]["asof"] for o in obs))
            self.assertIn(PRIVATE_BAA.search(text).group(0), self.card(pub)["reading"])   # 해석 줄의 Baa 부분도 같은 글자

    def test_missing_or_broken_baa_values_are_null(self):
        for level, low, pct in ((None, None, None), (float("nan"), float("inf"), float("nan")), (2.5, None, None)):
            _, pub = self.with_baa(level, low, pct)
            vals = [o["value"] for o in self.card(pub)["observations"]]
            self.assertEqual(vals[1:], [None, None])
            self.assertEqual(vals[0], 2.5 if level == 2.5 else None)
            json.dumps(pub, allow_nan=False)                                           # NaN이 남지 않는다

    def test_ice_and_sp_values_absent_at_several_roundings_while_baa_is_present(self):
        hy, ig, sp = 4.873, 1.127, 6.791
        raw, pub = self.with_baa(2.36, 0.19, 0.4417, hy=hy, ig=ig, sp=sp)
        self.assertIn("HY OAS 4.87%p", next(s for s in raw["signals"] if s["key"] == "credit_spread")["text"])   # 원본에는 있다
        _, nums, strs = walk(pub)
        str_nums = [float(x) for s in strs for x in re.findall(r"-?\d+\.\d+", s)]
        for v in (hy, ig, sp):
            for digits in (1, 2, 3):
                rv = round(v, digits)
                self.assertFalse(any(abs(n - rv) < 10 ** -(digits + 1) for n in nums + str_nums), (v, digits))
        dump = json.dumps(pub, ensure_ascii=False)
        for txt in ("4.873", "4.87", "1.127", "1.13", "6.791", "6.79"):
            self.assertNotIn(txt, dump, txt)
        card = self.card(pub)
        self.assertEqual([o["value"] for o in card["observations"]], [2.36, 0.19, 44.2])   # Baa는 실린다
        self.assertTrue(card["reading"].startswith("Baa−10Y 2.36%p(바닥 대비 +0.19, 1990년 이후 하위 44.2%) · " + HY_PUBLIC))
        self.assertEqual(card["status"], "met")                                         # HY 4.873 > 4.61 — 충족 여부는 싣는다

    def test_notices_sit_with_the_values(self):
        _, pub = self.with_baa(2.36, 0.19, 0.4417)
        self.assertEqual(rp.MOODYS_NOTICE, MOODYS_PAGE_TEXT)                              # FRED 페이지 그대로(글자 하나도)
        cite = ("Federal Reserve Bank of St. Louis, Moody's Seasoned Baa Corporate Bond Yield Relative to Yield on 10-Year "
                "Treasury Constant Maturity [BAA10Y], retrieved from FRED, Federal Reserve Bank of St. Louis; "
                "https://fred.stlouisfed.org/series/BAA10Y, September 22, 2026.")        # FRED Suggested Citation 그대로
        self.assertEqual(self.card(pub)["notices"], [rp.BAA_DERIVED, cite, MOODYS_PAGE_TEXT])
        self.assertIn("macro-regime-check", rp.BAA_DERIVED)                              # 누가 계산했는지
        self.assertTrue(rp.BAA_DERIVED.endswith("니다."))
        self.assertNotIn("Â", json.dumps(pub, ensure_ascii=False))                       # FRED 페이지의 글자 깨짐을 옮기지 않는다
        rows = {h["series"]: h for h in pub["data_health"]}
        self.assertEqual(rows["BAA10Y"]["citation"], cite)
        self.assertIn(MOODYS_PAGE_TEXT, pub["attribution"])                              # 꼬리말에도

    def read_written(self, pub):
        out = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, out)
        rp.write(out, pub)
        files = []
        for name in ("public.json", os.path.join("history", f"{pub['date']}.json")):
            with open(os.path.join(out, name), encoding="utf-8") as f:
                files.append(json.load(f))
        return files

    def test_history_has_no_baa_values_while_public_does(self):
        # 그날 공개본에는 Baa 값 셋이 실리고, 날마다 쌓이는 기록(data/history/)에는 싣지 않는다 — 둘러볼 수 있는 Moody's 시계열을
        # 만들지 않게. 충족 여부·고지·인용·자료 상태는 기록에도 남는다. 지어낸 값
        raw, pub = self.with_baa(2.873, 0.347, 0.7319, hy=5.083)
        public, hist = self.read_written(pub)
        self.assertEqual([o["value"] for o in self.card(public)["observations"]], [2.87, 0.35, 73.2])
        self.assertEqual(self.card(public)["reading"],
                         f"Baa−10Y 2.87%p(바닥 대비 +0.35, 1990년 이후 하위 73.2%) · {HY_PUBLIC} → D 선행 신호")
        card = self.card(hist)
        self.assertEqual([o["value"] for o in card["observations"]], [None, None, None])
        self.assertEqual([(o["label"], o["series"], o["asof"]) for o in card["observations"]],
                         [(o["label"], o["series"], o["asof"]) for o in self.card(public)["observations"]])
        self.assertEqual(card["reading"], f"{rp.BAA_HISTORY} · {HY_PUBLIC} → D 선행 신호")
        self.assertEqual((card["status"], card["scenario"], card["notices"]),
                         ("met", "D", self.card(public)["notices"]))                  # 충족 여부·이름표·고지·인용은 남는다
        self.assertIn(MOODYS_PAGE_TEXT, card["notices"])
        self.assertEqual(hist["data_health"], public["data_health"])
        self.assertEqual(without_baa(hist), without_baa(public))                     # 그 밖은 한 글자도 같다
        _, nums, strs = walk(hist)
        dump = json.dumps(hist, ensure_ascii=False)
        for txt in ("2.873", "2.87", "0.347", "0.35", "73.2", "0.7319"):
            self.assertNotIn(txt, dump, txt)
        for v in (2.873, 0.347, 73.2, 2.87, 0.35):
            self.assertNotIn(v, nums, v)
        self.assertEqual(pub, json.loads(json.dumps(public)))                        # 공개본 dict는 고치지 않는다

    def test_history_reading_forms(self):
        for level, low, pct, hy, want in (
                (None, None, None, 6.127, f"{rp.BAA_HISTORY} · {HY_PUBLIC} → D 선행 신호"),          # 값 자리가 '—'여도
                (1.44, None, None, None, f"{rp.BAA_HISTORY} · {HY_PUBLIC} → {rp.NO_VERDICT}")):
            _, pub = self.with_baa(level, low, pct, hy=hy)
            self.assertIn("Baa−10Y ", self.card(pub)["reading"])
            self.assertEqual(self.card(self.read_written(pub)[1])["reading"], want)
        _, pub = self.with_baa(2.36, 0.19, 0.4417)
        for line, want in (("스프레드 자료 없음", "스프레드 자료 없음"), (None, None),
                           ("Baa−10Y 9.87%p → 다른 꼴", None),                                # 꼴을 모르는 Baa 줄은 싣지 않는다
                           (f"Baa−10Y 2.36%p(바닥 대비 +0.19, 1990년 이후 하위 44.2%) · Baa 9.87", None)):
            p = copy.deepcopy(pub)
            self.card(p)["reading"] = line
            before = copy.deepcopy(p)
            self.assertEqual(self.card(rp.history_copy(p))["reading"], want, line)
            self.assertEqual(p, before)

    def test_history_of_an_older_date_is_stripped_too(self):
        _, pub = self.with_baa(2.873, 0.347, 0.7319)
        out = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, out)
        rp.write(out, pub)
        old = {**copy.deepcopy(pub), "date": "2026-06-15"}
        self.assertFalse(rp.write(out, old))                                          # 공개본은 그대로, 기록에만
        with open(os.path.join(out, "history", "2026-06-15.json"), encoding="utf-8") as f:
            hist = json.load(f)
        self.assertEqual([o["value"] for o in self.card(hist)["observations"]], [None, None, None])
        self.assertNotIn("2.87", json.dumps(hist, ensure_ascii=False))

    def test_citation_required_flags_follow_the_fred_tags(self):
        # FRED 시리즈 페이지의 'Copyrighted: Citation Required' 표시(2026-10-30 23개 페이지에서 확인)
        rows = {h["series"]: h for h in rp.render(self.raw)["data_health"]}
        self.assertEqual({s for s, h in rows.items() if h["citation_required"] is True},
                         {"M2V", "BAA10Y", "T10Y2Y", "T10YIE", "SOFR"})
        self.assertTrue(all(isinstance(h["citation_required"], bool) for h in rows.values()))
        self.assertEqual(set(rp.CITATION_REQUIRED) - set(rr.SERIES), set())


class ManualAndMoreValuesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.raw = built_raw(cls.tmp)
        cls.pub = rp.render(cls.raw)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_manual_items_are_the_engine_items_without_ids(self):
        got = self.pub["regime"]["manual_checks"]
        self.assertEqual([(m["cadence"], m["item"]) for m in got], [(m[1], m[2]) for m in rr.MANUAL])
        self.assertEqual(set(rp.MANUAL_PUBLIC), {m[0] for m in rr.MANUAL})
        dump = json.dumps(got, ensure_ascii=False)
        for m in rr.MANUAL:
            self.assertNotIn(m[0], dump)

    def test_unknown_manual_item_is_dropped_alone_without_echoing_the_id(self):
        want = [(m[1], m[2]) for m in rr.MANUAL]
        for bad in (["F-99-01", "월", "새 항목"], ["F-00-15", "주", "x"], "F-00-15", [["F-00-15"], "월", "y"], None):
            raw = {**self.raw, "manual": self.raw["manual"][:1] + [bad] + self.raw["manual"][1:]}
            pub = rp.render(raw)
            got = pub["regime"]["manual_checks"]
            self.assertEqual([(m["cadence"], m["item"]) for m in got], want, bad)   # 나머지는 원본 순서 그대로
            self.assertEqual(drops(pub), [rp.DROPPED["manual"].format(1)], bad)
            dump = json.dumps(pub, ensure_ascii=False)
            for leak in ("F-99", "새 항목", "F-00"):
                self.assertNotIn(leak, dump, bad)
        raw = {**self.raw, "manual": [["F-99-01", "월", "a"], ["F-98-01", "분기", "b"]]}
        pub = rp.render(raw)
        self.assertEqual((pub["regime"]["manual_checks"], drops(pub)), ([], [rp.DROPPED["manual"].format(2)]))

    def test_m2_velocity_carries_its_citation(self):
        # M2V는 세인트루이스 연은이 계산한 시리즈(FRED 'Copyrighted: Citation Required') — 값 곁에 권장 인용
        got = {o["label"]: o for o in self.pub["regime"]["more_values"]}
        self.assertEqual(got["M2 유통속도"]["citation"], rp.citation("M2V", self.raw["date"]))
        self.assertTrue(got["M2 유통속도"]["citation"].startswith("Federal Reserve Bank of St. Louis, Velocity of M2"))
        self.assertEqual([k for k, o in got.items() if "citation" in o], ["M2 유통속도"])

    def test_more_values_come_from_public_series_already_fetched(self):
        ind = self.raw["indicators"]
        got = {o["label"]: o for o in self.pub["regime"]["more_values"]}
        self.assertEqual(len(got), len(rp.MORE_VALUES))
        for key, label, unit, series, computed in rp.MORE_VALUES:
            o = got[label]
            self.assertEqual((o["unit"], o["series"], o["computed"]), (unit, series, computed))
            self.assertEqual((o["value"], o["asof"]), (round(ind[key]["value"], 3), ind[key]["asof"]), key)
            self.assertTrue(set(series) <= set(rr.SERIES))
            self.assertFalse(set(series) & set(rp.RESTRICTED))
        self.assertAlmostEqual(got["명목GDP(연율)"]["value"], round(27000 * 1.013 ** 13, 3))     # make_cache의 마지막 분기
        self.assertEqual(got["명목GDP(연율)"]["asof"], "2026-04-01")
        self.assertEqual(got["실업률"]["value"], round(4.0 + 0.02 * 39, 3))
        self.assertEqual(got["M2"]["value"], 20800 + 60 * 39)
        cited = {h["series"] for h in self.pub["data_health"] if h["citation"]}
        self.assertTrue({sid for *_, series, _ in rp.MORE_VALUES for sid in series} <= cited)


class FailClosedTest(unittest.TestCase):
    """정해 둔 꼴과 다른 원본은 그 항목만 싣지 않는다(닫힌 채 실패) — 공개본 전체는 만들어지고, 경고·로그에 원본 문장(값)을
    싣지 않는다(공개 Actions 로그). public_rules()에 없는 규칙만 공개본 전체를 멈춘다."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.raw = built_raw(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def with_text(self, key, text=None, scenario=None):
        raw = copy.deepcopy(self.raw)
        sig = next(s for s in raw["signals"] if s["key"] == key)
        if text is not None:
            sig["text"] = text
        if scenario is not None:
            sig["scenario"] = scenario
        return raw

    def test_unexpected_texts_fail_without_echoing_values(self):
        cases = [("credit_spread", "Baa−10Y 9.87%p(바닥 대비 +0.05) · HY OAS 2.68%p → 확대 없음(A 유지)"),   # 앞부분 꼴이 다름
                 ("credit_spread", "Baa−10Y 9.87%p(바닥 대비 +0.05, 1990년 이후 하위 1.5%) · HY OAS 2.68%p → 9.87"),
                 ("ci_vs_ngdp", "C&I +9.8% vs 명목GDP +6.6% → 새 해석 9.87"),
                 ("ci_vs_ngdp", "C&I +nan% vs 명목GDP +6.6% → 상회 = A 진행"),
                 ("stock_bond_corr", "ρ60 +0.20, 양(+) 30영업일째(126일 미만) S&P 9.87"),
                 ("real_rate_bei", "10년 실질 2.61% · BEI 2.34%(3개월 +0.00) → 실질 2% 위 = C 반증(F-09-Z-99)")]
        base = rp.render(self.raw)
        title = {r["key"]: r["title"] for r in base["rules"]}
        for key, text in cases:
            pub = rp.render(self.with_text(key, text))
            got = {r["key"]: r for r in pub["rules"]}
            self.assertIsNone(got[key]["reading"], key)                          # 그 규칙의 해석 줄만 null
            self.assertEqual(got[key]["scenario"], next(r for r in base["rules"] if r["key"] == key)["scenario"])
            for r in base["rules"]:                                              # 다른 규칙·규칙 문장·판정은 그대로
                if r["key"] != key:
                    self.assertEqual(got[r["key"]], r)
                else:
                    self.assertEqual({k: v for k, v in got[key].items() if k != "reading"},
                                     {k: v for k, v in r.items() if k != "reading"})
            self.assertEqual(drops(pub), [rp.DROPPED["reading"].format(title[key])])
            dump = json.dumps(pub, ensure_ascii=False, allow_nan=False)
            for leak in ("9.87", "F-09", "2.68"):
                self.assertNotIn(leak, dump, (key, leak))
            self.assertIsNone(NAN_RE.search(dump), key)

    def test_nan_value_leaves_the_reading_null_not_nan(self):
        # 값 자리의 nan(원본 서식 '+nan')은 꼴에 맞지 않는다 — 해석 줄은 null, 관측값도 null(NaN은 JSON을 깨뜨린다)
        nan = float("nan")
        raw = copy.deepcopy(self.raw)
        raw["signals"] = rr.evaluate({**rck.flat(raw["indicators"]), "ci_yoy": nan, "tp": nan, "tp_chg_3m": nan})
        raw["indicators"]["ci_yoy"]["value"] = nan
        raw["indicators"]["tp"]["value"] = float("inf")
        self.assertIn("nan", next(s for s in raw["signals"] if s["key"] == "ci_vs_ngdp")["text"])   # 원본에는 nan 글자
        pub = rp.render(raw)
        got = {r["key"]: r for r in pub["rules"]}
        self.assertIsNone(got["ci_vs_ngdp"]["reading"])
        self.assertIsNone(got["term_premium"]["reading"])
        self.assertIsNone(got["ci_vs_ngdp"]["observations"][0]["value"])
        self.assertIsNone(got["term_premium"]["observations"][0]["value"])
        self.assertEqual(sorted(drops(pub)), sorted(rp.DROPPED["reading"].format(got[k]["title"])
                                                    for k in ("ci_vs_ngdp", "term_premium")))
        self.assertIsNotNone(got["sofr"]["reading"])                           # 다른 규칙은 그대로
        dump = json.dumps(pub, ensure_ascii=False, allow_nan=False)
        self.assertIsNone(NAN_RE.search(dump))
        out = os.path.join(self.tmp, "nan-out")
        self.assertTrue(rp.write(out, pub))
        with open(os.path.join(out, "public.json"), encoding="utf-8") as f:
            self.assertNotIn("NaN", f.read())

    def test_writer_refuses_nan_instead_of_breaking_the_page(self):
        pub = rp.render(self.raw)
        pub["rules"][0]["observations"][0]["value"] = float("nan")             # 어디선가 새어 들어와도
        out = os.path.join(self.tmp, "refuse-out")
        with self.assertRaises(ValueError):
            rp.write(out, pub)
        self.assertFalse(os.path.exists(os.path.join(out, "public.json")))

    def test_a_changed_scenario_tag_drops_the_tag_and_reading_only(self):
        base = rp.render(self.raw)
        for key, tag in (("ci_vs_ngdp", "B"), ("core_momentum", "A"), ("employment", None)):
            pub = rp.render(self.with_text(key, scenario=tag) if tag else self.with_text(key, scenario=""))
            got = {r["key"]: r for r in pub["rules"]}
            self.assertEqual((got[key]["scenario"], got[key]["reading"]), (None, None), key)
            self.assertEqual(got[key]["status"], next(r for r in base["rules"] if r["key"] == key)["status"])
            self.assertEqual(drops(pub), [rp.DROPPED["label"].format(got[key]["title"])])
            g, b = pub["regime"], base["regime"]
            neutral = key == "core_momentum"                                    # 이름표를 못 싣는 규칙은 어느 셈에도 없다
            self.assertEqual(g["core"]["total"], b["core"]["total"] - (0 if neutral else 1), key)
            self.assertEqual(g["neutral"]["total"], b["neutral"]["total"] - (1 if neutral else 0), key)

    def test_a_broken_regime_section_is_left_out_alone(self):
        with mock.patch.object(rp, "regime_reference", side_effect=TypeError("원본 9.87")):
            pub = rp.render(self.raw)
        self.assertIsNone(pub["regime"])
        self.assertEqual(drops(pub), [rp.DROPPED["section"]])
        self.assertEqual(len(pub["rules"]), len(self.raw["signals"]))
        self.assertTrue(all(r["reading"] for r in pub["rules"]))                # 규칙마다의 해석 줄은 따로 산다
        self.assertNotIn("9.87", json.dumps(pub, ensure_ascii=False))

    def test_dropped_warnings_carry_no_forbidden_words_or_values(self):
        for t in rp.DROPPED.values():
            for word in FORBIDDEN_TEXT + READING_FORBIDDEN:
                self.assertNotIn(word, t)
            self.assertFalse(t.startswith(rp.WARNING_PREFIXES))                # 원본 경고 통로와 섞이지 않는다
            self.assertLessEqual(t.count("{}"), 1)

    def test_cli_drift_is_published_without_the_line_and_without_values(self):
        work = os.path.join(self.tmp, "cli")
        os.makedirs(os.path.join(work, "raw"))
        raw = self.with_text("credit_spread", "Baa−10Y 9.87%p → 이상한 9.87")
        with open(os.path.join(work, "raw", "latest.json"), "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False)
        out = os.path.join(self.tmp, "cli-out")
        p = run_cli("render_public.py", "--work", work, "--out", out)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stderr, "")
        self.assertEqual(len(p.stdout.strip().splitlines()), 1)
        self.assertIn("참고 1건 싣지 않음", p.stdout)
        self.assertNotIn("9.87", p.stderr + p.stdout)
        with open(os.path.join(out, "public.json"), encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("9.87", text)
        pub = json.loads(text)
        self.assertIsNone(next(r for r in pub["rules"] if r["key"] == "credit_spread")["reading"])

    def test_cli_failure_on_an_unknown_rule_is_one_line_without_values(self):
        work = os.path.join(self.tmp, "cli-bad")
        os.makedirs(os.path.join(work, "raw"))
        raw = copy.deepcopy(self.raw)
        raw["signals"].append({**raw["signals"][0], "key": "new_rule", "text": "새 규칙 9.87"})
        with open(os.path.join(work, "raw", "latest.json"), "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False)
        out = os.path.join(self.tmp, "cli-bad-out")
        p = run_cli("render_public.py", "--work", work, "--out", out)
        self.assertEqual(p.returncode, 1)
        self.assertEqual(len(p.stderr.strip().splitlines()), 1)
        self.assertIn("new_rule", p.stderr)
        self.assertNotIn("9.87", p.stderr + p.stdout)
        self.assertFalse(os.path.exists(os.path.join(out, "public.json")))


def page_function(page, name):
    """index.html의 인라인 스크립트에서 function name(...) { … } 한 덩어리(중괄호 짝으로 끝을 찾는다)."""
    i = page.index(f"function {name}(")
    depth, j = 0, page.index("{", i)
    while True:
        c = page[j]
        depth += (c == "{") - (c == "}")
        j += 1
        if depth == 0:
            return page[i:j]


# 아주 작은 가짜 DOM 위에서 페이지의 renderRule·renderRegime을 그대로 돌리고 글자를 돌려준다(그 밖의 것은 대역)
NODE_HARNESS = r"""
const src = require('fs').readFileSync(0, 'utf8'), input = JSON.parse(src);
class El { constructor(t){this.tag=t;this.kids=[];this.attrs={};this.hidden=false;}
  append(...xs){for(const x of xs)this.kids.push(typeof x==='string'?{text:x}:x);}
  replaceChildren(...xs){this.kids=[];this.append(...xs.filter(x=>x!==null&&x!==undefined));}
  setAttribute(k,v){this.attrs[k]=String(v);} get childElementCount(){return this.kids.filter(k=>k instanceof El).length;}
  get textContent(){return this.kids.map(k=>k instanceof El?k.textContent:k.text).join('');} }
const find=(n,f,o=[])=>{if(n instanceof El){if(f(n))o.push(n);n.kids.forEach(k=>find(k,f,o));}return o;};
const ids={'regime-ref':new El('section')};
const el=(tag,attrs,...kids)=>{const n=new El(tag);for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,v);
  for(const c of kids)if(c!==null&&c!==undefined)n.append(c);return n;};
const ctx={el,document:{getElementById:id=>ids[id]||null},STATUS_TEXT:{met:'충족',not_met:'미충족',unknown:'판정 불가'},
  GROUPS:[],LEARN:{},GUIDE:{},link:t=>t,chartFigure:()=>null,guideDetails:()=>null,find,Number,Array,Object,String};
require('vm').runInNewContext(input.code+';out={regime:renderRegime(input.regime),cards:[],cites:[],texts:[]};'
  +'for(const r of input.rules){const c=renderRule(r,null,input.health||[]),has=k=>n=>(n.attrs.class||"").split(" ").includes(k);'
  +'out.cards.push(find(c,has("rule-reading")).map(n=>n.textContent));out.cites.push(find(c,has("cite-line")).map(n=>n.textContent));'
  +'out.texts.push(c.textContent);}',
  Object.assign(ctx,{input,out:null}));
process.stdout.write(JSON.stringify({ret:ctx.out.regime,text:ids['regime-ref'].textContent,cards:ctx.out.cards,
  cites:ctx.out.cites,texts:ctx.out.texts}));
"""


class PageTest(unittest.TestCase):
    """페이지 쪽(site/index.html) — 공개본의 해석 쪽을 글자로만 싣는지. node가 없으면 그리기 검사는 건너뛴다."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.pub = rp.render(built_raw(cls.tmp))
        with open(os.path.join(os.path.dirname(SCRIPTS), "site", "index.html"), encoding="utf-8") as f:
            cls.page = f.read()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def draw(self, regime, rules, health=None):
        if shutil.which("node") is None:
            self.skipTest("node 없음")
        code = page_function(self.page, "renderRegime") + "\n" + page_function(self.page, "renderRule")
        p = subprocess.run(["node", "-e", NODE_HARNESS],
                           input=json.dumps({"code": code, "regime": regime, "rules": rules, "health": health or []}),
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout)

    def test_page_is_wired(self):
        self.assertIn('<section id="regime-ref"', self.page)
        self.assertIn("available.regime = renderRegime(p.regime)", self.page)
        self.assertIn('document.getElementById("regime-ref").hidden = !(available.regime && activeView === "all")', self.page)
        self.assertLess(self.page.index('<section id="regime-ref"'), self.page.index('<div id="rules">'))
        block = page_function(self.page, "renderRegime") + page_function(self.page, "renderRule")
        for word in READING_FORBIDDEN:                                   # 화면 쪽 글에도 내부 ID·비공개 보고서 참조가 없다
            self.assertNotIn(word, block, word)
        self.assertNotIn("innerHTML", block)                            # 글자로만
        # 자료 상태 목록 — 인용 필요 시리즈에 표시, 값 비공개는 제한 시리즈(S&P·ICE)만(BAA10Y는 2026-10-30부터 값)
        pub_fn = page_function(self.page, "renderPublic")
        self.assertIn('h.citation_required === true ? " · 인용 필요" : ""', pub_fn)
        self.assertIn('h.display === "status_only" ? " · 값 비공개" : ""', pub_fn)

    def test_panel_and_card_lines_show_the_published_text(self):
        out = self.draw(self.pub["regime"], self.pub["rules"])
        g, text = self.pub["regime"], out["text"]
        self.assertTrue(out["ret"])
        self.assertTrue(text.startswith("레짐 점검 참고참고 — 예측 아님"), text[:40])
        for t in [g["headline"], g["notice"], *g["reference"]["lines"], *g["legend"],
                  *(m["item"] for m in g["manual_checks"])]:
            self.assertIn(t, text)
        self.assertIn("M2 23,140 십억 달러 · 2026-08-01", text)
        self.assertIn("실업률 4.78% · 2026-08-01", text)
        self.assertIn("근원 CPI − 근원 PCE 전년비 -0.862%p · 2026-08-01 · 계산값", text)
        self.assertFalse(re.search(r"undefined|NaN|null|\[object", text))
        cards = dict(zip((r["key"] for r in self.pub["rules"]), out["cards"]))
        self.assertEqual(cards["ci_vs_ngdp"], [f"시나리오 A · {self.pub['rules'][0]['reading']} · 참고(예측 아님)"])
        self.assertTrue(cards["core_momentum"][0].startswith("중립 규칙 · 근원 PCE 6개월 연율"))
        self.assertTrue(cards["credit_spread"][0].startswith("시나리오 D · Baa−10Y 1.42%p(바닥 대비 +0.00, 1990년 이후 하위 0.2%) · "
                                                             f"{HY_PUBLIC} → "), cards["credit_spread"])
        m2v = rp.citation("M2V", self.pub["date"])                             # 값 곁의 권장 인용(세인트루이스 연은 계산 시리즈)
        self.assertIn("M2 유통속도 ", text)
        self.assertEqual(text.count("권장 인용: "), 1)
        self.assertIn("권장 인용: " + m2v, text)

    def test_a_rule_without_a_published_tag_shows_no_reading(self):
        # 공개본이 이름표를 싣지 않은 규칙(scenario null)은 해석 줄을 '중립 규칙'으로 잘못 붙이지 않고 아예 그리지 않는다
        r = self.pub["rules"][0]
        rules = [{**r, "scenario": None}, {**r, "scenario": ""}, {**r, "scenario": 3}, {**r, "scenario": "—"}, r]
        out = self.draw(self.pub["regime"], rules)
        self.assertEqual(out["cards"][:3], [[], [], []])
        self.assertEqual(out["cards"][3], [f"중립 규칙 · {r['reading']} · 참고(예측 아님)"])
        self.assertEqual(out["cards"][4], [f"시나리오 A · {r['reading']} · 참고(예측 아님)"])

    def test_citation_needs_a_shown_value_and_the_citation_form(self):
        g = copy.deepcopy(self.pub["regime"])
        m2v = next(o for o in g["more_values"] if "citation" in o)
        good = m2v["citation"]
        for value, cite, shown in ((None, good, False), (1.5, "<b>x</b>, retrieved from y, May 1, 2026.", False),
                                   (1.5, good + " 덧붙임", False), (1.5, 7, False), (1.5, good, True)):
            m2v.update(value=value, citation=cite)
            text = self.draw(g, [])["text"]
            self.assertEqual("권장 인용: " in text, shown, (value, cite))
            self.assertNotIn("<b>", text)

    def test_rule_cards_show_citations_of_citation_required_series(self):
        # FRED 'Copyrighted: Citation Required' 시리즈(T10Y2Y·T10YIE·SOFR·BAA10Y)의 권장 인용을 카드의 출처 자리에 글자로.
        # 신용 스프레드는 인용이 값 곁(고지)에 이미 있어 출처 자리에 되풀이하지 않는다 — 카드 전체에 한 번
        pub, date = self.pub, self.pub["date"]
        out = self.draw(pub["regime"], pub["rules"], pub["data_health"])
        cites = dict(zip((r["key"] for r in pub["rules"]), out["cites"]))
        texts = dict(zip((r["key"] for r in pub["rules"]), out["texts"]))
        want = {"curve_inversion": ["T10Y2Y"], "real_rate_bei": ["T10YIE"], "sofr": ["SOFR"]}
        for key, got in cites.items():
            self.assertEqual(got, ["권장 인용: " + rp.citation(sid, date) for sid in want.get(key, [])], key)
        self.assertNotIn(rp.citation("DFII10", date), texts["real_rate_bei"])            # 공공 자료(인용 요청)는 링크만
        credit = texts["credit_spread"]
        self.assertEqual(credit.count(rp.citation("BAA10Y", date)), 1)
        self.assertEqual(credit.count(rp.MOODYS_NOTICE), 1)
        values = next(r for r in pub["rules"] if r["key"] == "credit_spread")["observations"]
        first = credit.index(f"{values[0]['value']}%p")                                 # 값이 먼저, 고지는 같은 카드 안 그 뒤
        self.assertLess(first, credit.index(rp.MOODYS_NOTICE))
        self.assertIn("원자료 값 비공개: BAMLH0A0HYM2 (ICE Data Indices)", credit)
        self.assertNotIn("BAA10Y (Moody's)", credit)                                     # Baa는 '값 비공개' 줄에 없다
        self.assertFalse(re.search(r"undefined|NaN|null|\[object", "".join(out["texts"])))

    def test_rule_card_citation_needs_the_flag_and_the_citation_form(self):
        pub = self.pub
        r = next(x for x in pub["rules"] if x["key"] == "curve_inversion")
        good = next(h for h in pub["data_health"] if h["series"] == "T10Y2Y")
        for patch, shown in (({}, True), ({"citation_required": False}, False), ({"citation_required": "true"}, False),
                             ({"citation": "<b>x</b>, retrieved from y, May 1, 2026."}, False),
                             ({"citation": good["citation"] + " 덧붙임"}, False), ({"citation": 7}, False)):
            out = self.draw(pub["regime"], [r], [{**good, **patch}])
            self.assertEqual(len(out["cites"][0]), int(shown), patch)
            self.assertNotIn("<b>", out["texts"][0])

    def test_broken_or_missing_parts_draw_nothing_odd(self):
        out = self.draw({"headline": 7}, [{**self.pub["rules"][0], "reading": {"x": 1}}])
        self.assertFalse(out["ret"])
        self.assertEqual(out["text"], "")
        self.assertEqual(out["cards"], [[]])                            # 글이 아닌 해석은 싣지 않는다
        g = {**self.pub["regime"], "more_values": [{"label": "M2", "value": "1e9", "unit": None}, 5],
             "manual_checks": [{"item": 3}, {"item": "항목", "cadence": None}], "legend": ["a", 9], "reference": None}
        out = self.draw(g, [])
        self.assertTrue(out["ret"])
        self.assertIn("M2 자료 없음", out["text"])
        self.assertIn("항목", out["text"])
        self.assertFalse(re.search(r"undefined|NaN|null|\[object|1e9", out["text"]))


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
