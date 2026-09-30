#!/usr/bin/env python3
"""공개용 표 — regime_check.py의 원본 결과(<work>/raw/latest.json)를 사이트가 읽는 공개본(<out>)으로 바꾼다.

공개본에서 빼는 것 (test_render_public.py가 강제):
  - 규칙 엔진의 해석 문구·시나리오 구분·내부 ID (regime_rules.evaluate의 text·scenario·log_ids)
  - 국면 판정 재료(regime_inputs) — 직전 국면은 사람이 판단해 넣는 값이라 공개하지 않는다
  - 재배포가 제한된 시리즈(S&P·ICE·Moody's)의 원값과 원값을 역산할 수 있는 파생값
    (예외: 60영업일 상관처럼 원값을 되살릴 수 없는 통계는 derived로 표시해 싣는다)
넣는 것: 규칙마다 중립적인 규칙 문장(임계값은 regime_rules.TH에서 읽는다), 공개 가능한 관측치와 기준일,
충족 여부, 시리즈별 자료 신선도와 출처 표기.
public_rules()에 없는 규칙이 원본에 있으면 실패한다 — 검토하지 않은 문구가 공개되지 않게.
public.json은 더 최근 날짜의 공개본을 과거 날짜로 덮지 않는다(history에만 쓴다).

산출: <out>/public.json, <out>/history/YYYY-MM-DD.json   (원본 <work>는 사이트 폴더 밖)
사용법: python render_public.py [--work .work] [--out data]
"""
import os, sys, json, argparse, datetime

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import regime_rules as rr

SCHEMA = 1
REPO = os.path.dirname(SCRIPTS)
DEFAULT_WORK = os.path.join(REPO, ".work")
DEFAULT_OUT = os.path.join(REPO, "data")
FRED_URL = "https://fred.stlouisfed.org/series/{}"
NOTICE = "공개 통계에 사전에 정한 규칙을 적용한 결과다. 투자 판단이나 권유가 아니다."
# 출처 표기 — FRED는 출처와 'FRED 경유'를 함께 적으라고 하고(Citation required/requested), SOFR은 뉴욕 연은 이용약관의
# 참조금리 조항(Use Restrictions — Reference Rates, 2023-06-09 개정)이 정해 둔 고지·면책을 요구한다(2026-09-30 원문 확인).
# 파생값(3개월 변화 등)은 누가 계산했는지 밝히고 뉴욕 연은의 것으로 보이지 않게 한다(같은 약관 Conditions 4).
PUBLISHER = "macro-regime-check (github.com/yun-macrolab)"
SOFR_NOTICE = ("The SOFR data is subject to the Terms of Use posted at newyorkfed.org. The New York Fed is not "
               f"responsible for publication of the SOFR data by {PUBLISHER}, does not sanction or endorse any "
               "particular republication, and has no liability for your use.")
# 약관 원문 그대로(BGCR 구절 포함) — Conditions 1: 뉴욕 연은이 붙인 출처 표시는 그대로 옮긴다
SOFR_DTCC = ("The Secured Overnight Financing Rate (SOFR) Data and Broad General Collateral Rate (BGCR) Data are "
             "calculated using data provided under a license granted to the New York Fed by DTCC Solutions LLC "
             "(\u201cSolutions\u201d), an affiliate of The Depository Trust & Clearing Corporation. Solutions, its affiliates, "
             "and third parties from which they obtained data have no liability for the content of this material.")
SOFR_DERIVED = ("SOFR 3개월 변화는 macro-regime-check가 뉴욕 연은 SOFR 일별 자료(FRED 경유)로 계산한 값이다. "
                "뉴욕 연은이 발표한 값이 아니다.")
SOFR_DERIVED_EN = ("The SOFR 3-month change is computed by macro-regime-check from SOFR data (via FRED); "
                   "it is not published by the New York Fed.")
NOT_AFFILIATED = (f"{PUBLISHER} is not affiliated with the New York Fed. The New York Fed does not sanction, endorse, "
                  f"or recommend any products or services offered by {PUBLISHER}. It is not sponsored by, affiliated with, "
                  "or endorsed by the Federal Reserve Bank of St. Louis or FRED®.")
DATA_LICENSE = ("코드는 MIT 라이선스지만 자료(FRED·뉴욕 연은 등)는 그 대상이 아니다 — 각 출처의 이용 조건을 따른다. "
                "SOFR은 newyorkfed.org 이용약관, 나머지는 FRED 이용약관과 시리즈별 저작권 표시.")


def nyfed_attribution(year):
    """뉴욕 연은 이용약관 Conditions 2의 기본 출처 형식."""
    return (f"© {year} Federal Reserve Bank of New York. "
            "Content from the New York Fed subject to the Terms of Use at newyorkfed.org.")


def sofr_notices(year):
    """SOFR을 보여 주는 곳(카드·그래프·JSON)에 함께 싣는 고지 — 파생값 표시(한·영), 참조금리 고지·면책, DTCC 문장,
    기본 출처, 관계없음 고지(SOFR 이름을 제목에 쓰므로 가능한 한 눈에 띄게)."""
    return [SOFR_DERIVED, SOFR_DERIVED_EN, SOFR_NOTICE, SOFR_DTCC, nyfed_attribution(year), NOT_AFFILIATED]


def attribution(year):
    """페이지 꼬리말·공개본의 출처 목록."""
    return ["Source: FRED®, Federal Reserve Bank of St. Louis (https://fred.stlouisfed.org/).",
            SOFR_NOTICE, SOFR_DTCC, nyfed_attribution(year),
            "전년비·3개월 변화·상관·비율은 이 저장소 코드가 원자료로 계산한 값이다.",
            NOT_AFFILIATED, DATA_LICENSE]

# FRED 시리즈 고지에서 재배포·파생물을 제한한 시리즈 → 값은 싣지 않고 충족 여부와 FRED 링크만
RESTRICTED = {"SP500": "S&P Dow Jones Indices", "BAMLH0A0HYM2": "ICE Data Indices",
              "BAMLC0A0CM": "ICE Data Indices", "BAA10Y": "Moody's"}
OWNER = {"M2SL": "FRB", "BOGMBASE": "FRB", "M2V": "FRB St. Louis", "WRESBAL": "FRB", "GDP": "BEA",
         "LNFACBW027SBOG": "FRB", "TOTLL": "FRB", "BUSLOANS": "FRB", "THREEFYTP10": "FRB (Kim-Wright)",
         "DGS10": "FRB", "T10Y2Y": "FRB St. Louis", "DFII10": "FRB", "T10YIE": "FRB St. Louis",
         "PCEPILFE": "BEA", "CPILFESL": "BLS", "SOFR": "FRBNY", "DEXKOUS": "FRB", "CES5552300001": "BLS",
         **RESTRICTED}
# FRED 시리즈 페이지가 적은 출처(Source) 그대로 — 인용 문구에 쓴다(2026-09-30 22개 시리즈 페이지에서 확인)
_BOARD, _STL = "Board of Governors of the Federal Reserve System (US)", "Federal Reserve Bank of St. Louis"
FRED_SOURCE = {"M2SL": _BOARD, "BOGMBASE": _BOARD, "M2V": _STL, "WRESBAL": _BOARD,
               "GDP": "U.S. Bureau of Economic Analysis", "LNFACBW027SBOG": _BOARD, "TOTLL": _BOARD, "BUSLOANS": _BOARD,
               "THREEFYTP10": _BOARD, "BAA10Y": _STL, "BAMLH0A0HYM2": "Ice Data Indices, LLC",
               "BAMLC0A0CM": "Ice Data Indices, LLC", "SP500": "S&P Dow Jones Indices LLC", "DGS10": _BOARD,
               "T10Y2Y": _STL, "DFII10": _BOARD, "T10YIE": _STL, "PCEPILFE": "U.S. Bureau of Economic Analysis",
               "CPILFESL": "U.S. Bureau of Labor Statistics", "SOFR": "Federal Reserve Bank of New York",
               "DEXKOUS": _BOARD, "CES5552300001": "U.S. Bureau of Labor Statistics"}
# FRED 권장 인용의 시리즈 제목(Suggested Citation 그대로, 2026-09-30 확인)
FRED_TITLE = {
    "M2SL": "M2", "BOGMBASE": "Monetary Base: Total", "M2V": "Velocity of M2 Money Stock",
    "WRESBAL": "Liabilities and Capital: Other Factors Draining Reserve Balances: Reserve Balances with Federal "
               "Reserve Banks: Week Average",
    "GDP": "Gross Domestic Product",
    "LNFACBW027SBOG": "Other Loans and Leases: All Other Loans and Leases: Loans to Nondepository Financial "
                      "Institutions, All Commercial Banks",
    "TOTLL": "Loans and Leases in Bank Credit, All Commercial Banks",
    "BUSLOANS": "Commercial and Industrial Loans, All Commercial Banks",
    "THREEFYTP10": "Term Premium on a 10 Year Zero Coupon Bond",
    "BAA10Y": "Moody's Seasoned Baa Corporate Bond Yield Relative to Yield on 10-Year Treasury Constant Maturity",
    "BAMLH0A0HYM2": "ICE BofA US High Yield Index Option-Adjusted Spread",
    "BAMLC0A0CM": "ICE BofA US Corporate Index Option-Adjusted Spread",
    "SP500": "S&P 500",
    "DGS10": "Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity, Quoted on an Investment Basis",
    "T10Y2Y": "10-Year Treasury Constant Maturity Minus 2-Year Treasury Constant Maturity",
    "DFII10": "Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity, Quoted on an Investment Basis, "
              "Inflation-Indexed",
    "T10YIE": "10-Year Breakeven Inflation Rate",
    "PCEPILFE": "Personal Consumption Expenditures Excluding Food and Energy (Chain-Type Price Index)",
    "CPILFESL": "Consumer Price Index for All Urban Consumers: All Items Less Food and Energy in U.S. City Average",
    "SOFR": "Secured Overnight Financing Rate",
    "DEXKOUS": "South Korean Won to U.S. Dollar Spot Exchange Rate",
    "CES5552300001": "All Employees, Securities, Commodity Contracts, Funds, Trusts, and Other Financial Vehicles, "
                     "Investments, and Related Activities",
}
_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December")
# 공개 가능한 원본 경고 — 이 문구로 시작하는 것만 싣는다(미수신·경로가 섞인 오류 문구는 자료 신선도 표로 대신)
WARNING_PREFIXES = ("NDFI 계단", "C&I YoY 기준치", "근원 CPI 결측월", "근원 CPI YoY 산출 불가")


def _obs(key, label, unit, series, field="value", derived=False, computed=False):
    """derived: 재배포 제한 시리즈에서 원값을 되살릴 수 없게 계산한 통계(상관)만. computed: 이 저장소가 원자료로
    계산한 값(전년비·3개월 변화·비율·상관) — 페이지에 '계산값'으로 표시(원 발행처의 값으로 보이지 않게)."""
    return {"key": key, "label": label, "unit": unit, "series": series, "field": field, "derived": derived,
            "computed": computed or derived}


def citation(sid, date):
    """시리즈별 출처 문구 — FRED 권장 인용 형식 그대로: 출처, 제목 [ID], retrieved from FRED, …; URL, 날짜.
    날짜는 공개본 기준일(그날 받은 자료). SOFR도 같은 형식(참조금리 고지는 attribution·규칙 notices에 따로)."""
    d = datetime.date.fromisoformat(date)
    return (f"{FRED_SOURCE[sid]}, {FRED_TITLE[sid]} [{sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; "
            f"{FRED_URL.format(sid)}, {_MONTHS[d.month - 1]} {d.day}, {d.year}.")


def public_rules():
    """규칙 key → 공개 문구·관측치 정의. 임계값은 호출 시점의 rr.TH에서 읽는다."""
    th = rr.TH
    return {
        "ci_vs_ngdp": {
            "title": "기업대출 증가율 대 명목 성장률",
            "rule": "C&I 대출 전년비가 명목GDP 전년비보다 낮으면 충족",
            "obs": [_obs("ci_yoy", "C&I 대출 전년비", "%", ["BUSLOANS"], computed=True),
                    _obs("ngdp_yoy", "명목GDP 전년비", "%", ["GDP"], computed=True)]},
        "ndfi_credit": {
            "title": "은행의 비은행 금융기관 대출",
            "rule": f"전년비(재분류로 보이는 주간 +{th['ndfi_step_bn']:g}십억달러 이상 증가 계단 제외)가 "
                    f"{th['ndfi_two_digit']:g}% 미만이면 충족",
            "obs": [_obs("ndfi_yoy", "NDFI 대출 전년비(계단 제외)", "%", ["LNFACBW027SBOG"], computed=True),
                    _obs("ndfi_share", "총대출 중 비중", "%", ["LNFACBW027SBOG", "TOTLL"], computed=True)]},
        "credit_spread": {
            "title": "신용 스프레드",
            "rule": f"Baa−10년 스프레드가 12개월 저점보다 {th['spread_widen_pp']:g}%p 이상 넓어지거나 "
                    f"HY OAS가 {th['hy_oas_break']:g}%p를 넘으면 충족",
            "obs": [], "restricted": ["BAA10Y", "BAMLH0A0HYM2"]},
        "stock_bond_corr": {
            "title": "주가-금리 60영업일 상관",
            "rule": f"S&P500 일간 수익률과 미 10년 금리 일간 변화의 60영업일 상관이 "
                    f"{th['corr_run_days']:g}영업일 이상 계속 양(+)이면 충족",
            "obs": [_obs("rho60", "60영업일 상관", "", ["SP500", "DGS10"], derived=True),
                    _obs("rho60", "같은 부호 연속", "영업일", ["SP500", "DGS10"], field="run_days", derived=True)]},
        "curve_inversion": {
            "title": "10년−2년 금리차",
            "rule": "10년−2년 금리차가 0보다 작으면 충족",
            "obs": [_obs("t10y2y", "10년−2년", "%p", ["T10Y2Y"])]},
        "real_rate_bei": {
            "title": "실질금리와 기대인플레이션",
            "rule": f"10년 실질금리가 {th['real_rate_c']:g}% 미만이고 10년 BEI가 3개월 전보다 높으면 충족",
            "obs": [_obs("dfii10", "10년 실질금리", "%", ["DFII10"]),
                    _obs("bei", "10년 BEI", "%", ["T10YIE"]),
                    _obs("bei_chg_3m", "BEI 3개월 변화", "%p", ["T10YIE"], computed=True)]},
        "core_inflation": {
            "title": "근원 물가",
            "rule": f"근원 PCE 전년비가 {th['core_pce_split']:g}% 이하이면 충족 (근원 CPI는 참고)",
            "obs": [_obs("core_pce_yoy", "근원 PCE 전년비", "%", ["PCEPILFE"], computed=True),
                    _obs("core_cpi_yoy", "근원 CPI 전년비", "%", ["CPILFESL"], computed=True)]},
        "term_premium": {
            "title": "10년 기간 프리미엄",
            "rule": f"10년 기간 프리미엄(Kim-Wright)이 3개월 전보다 {th['tp_drop_3m']:g}%p 이상 낮아지면 충족",
            "obs": [_obs("tp", "기간 프리미엄", "%", ["THREEFYTP10"]),
                    _obs("tp_chg_3m", "3개월 변화", "%p", ["THREEFYTP10"], computed=True)]},
        "sofr": {
            "title": "단기 조달금리 SOFR",
            "rule": f"SOFR이 3개월 전보다 {th['sofr_rise_3m']:g}%p 이상 높아지면 충족",
            "obs": [_obs("sofr", "SOFR", "%", ["SOFR"]),
                    _obs("sofr_chg_3m", "3개월 변화", "%p", ["SOFR"], computed=True)]},
        "reserves_multiplier": {
            "title": "지준과 통화승수",
            "rule": f"지준/명목GDP가 {th['reserves_gdp_low']:g}% 미만이거나, 3개월 새 {th['reserves_gdp_rise_3m']:g}%p "
                    f"이상 늘고 근원 PCE 전년비가 {th['reserves_pce_floor']:g}%를 넘으면 충족",
            "obs": [_obs("reserves_gdp", "지준/명목GDP", "%", ["WRESBAL", "GDP"], computed=True),
                    _obs("reserves_gdp_chg_3m", "3개월 변화", "%p", ["WRESBAL", "GDP"], computed=True),
                    _obs("mult", "통화승수(M2/본원통화)", "배", ["M2SL", "BOGMBASE"], computed=True)]},
        "employment": {
            "title": "미 증권·투자업 고용",
            "rule": "고용 전년비가 0보다 작으면 충족",
            "obs": [_obs("emp_yoy", "고용 전년비", "%", ["CES5552300001"], computed=True)]},
    }


def _round(v):
    return None if v is None else round(v, 3)


def _status(fired):
    return "met" if fired is True else ("not_met" if fired is False else "unknown")


def render(raw):
    """원본 결과 dict → 공개본 dict. 검토 안 된 규칙이 있으면 RuntimeError."""
    table = public_rules()
    unknown = [s["key"] for s in raw["signals"] if s["key"] not in table]
    if unknown:
        raise RuntimeError(f"공개 문구가 없는 규칙 {unknown} — render_public.public_rules()에 추가하고 검토할 것")
    ind = raw["indicators"]
    year = int(raw["date"][:4])
    rules = []
    for s in raw["signals"]:
        spec = table[s["key"]]
        obs = [{"label": o["label"], "unit": o["unit"], "series": o["series"], "derived": o["derived"],
                "computed": o["computed"],
                "value": _round(ind.get(o["key"], {}).get(o["field"])), "asof": ind.get(o["key"], {}).get("asof")}
               for o in spec["obs"]]
        rules.append({"key": s["key"], "title": spec["title"], "rule": spec["rule"], "status": _status(s["fired"]),
                      "observations": obs,
                      "restricted_series": [{"series": sid, "owner": RESTRICTED[sid], "url": FRED_URL.format(sid)}
                                            for sid in spec.get("restricted", [])],
                      "notices": sofr_notices(year) if s["key"] == "sofr" else []})
    health = []
    for sid, (label, freq, _) in rr.SERIES.items():
        src = raw["sources"].get(sid, {})
        age = src.get("age_days")
        health.append({"series": sid, "label": label, "owner": OWNER.get(sid, ""), "url": FRED_URL.format(sid),
                       "last": src.get("last"), "age_days": age,
                       "fetched": src.get("source") or "missing",
                       "stale": bool(age is not None and age > rr.STALE_DAYS[freq]),
                       "display": "status_only" if sid in RESTRICTED else "value",
                       "citation": citation(sid, raw["date"])})
    counts = {k: sum(1 for r in rules if r["status"] == k) for k in ("met", "not_met", "unknown")}
    return {"schema": SCHEMA, "date": raw["date"],
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "notice": NOTICE, "attribution": attribution(year),
            "summary": {"total": len(rules), **counts}, "rules": rules,
            "data_health": health,
            "warnings": [w for w in raw.get("warnings", []) if w.startswith(WARNING_PREFIXES)]}


def _write_text(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def _public_date(out):
    try:
        with open(os.path.join(out, "public.json"), encoding="utf-8") as f:
            return json.load(f).get("date")
    except (OSError, ValueError):
        return None


def write(out, pub):
    """history/<날짜>.json은 항상, public.json은 기존 공개본보다 날짜가 같거나 늦을 때만. public.json을 썼으면 True."""
    text = json.dumps(pub, ensure_ascii=False, indent=2)
    hist = os.path.join(out, "history")
    os.makedirs(hist, exist_ok=True)
    _write_text(os.path.join(hist, f"{pub['date']}.json"), text)
    prev = _public_date(out)
    if prev is not None and pub["date"] < prev:
        return False
    _write_text(os.path.join(out, "public.json"), text)
    return True


def main():
    ap = argparse.ArgumentParser(description="원본 결과(<work>/raw/latest.json) → 공개본(<out>/public.json)")
    ap.add_argument("--work", default=DEFAULT_WORK, help="작업 폴더 (기본: 저장소의 .work/)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    a = ap.parse_args()
    try:
        path = os.path.join(os.path.abspath(a.work), "raw", "latest.json")
        if not os.path.exists(path):
            raise RuntimeError("raw/latest.json 없음 — regime_check.py를 먼저 실행할 것")
        with open(path, encoding="utf-8") as f:
            pub = render(json.load(f))
        wrote = write(os.path.abspath(a.out), pub)
    except (RuntimeError, ValueError, KeyError) as e:
        print(f"[render_public] {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
    sm = pub["summary"]
    print(f"[render_public] {pub['date']} 공개본 — 규칙 {sm['total']}개 중 충족 {sm['met']} · 판정 불가 {sm['unknown']}"
          + ("" if wrote else " · 더 최근 공개본이 있어 history에만 기록"))


if __name__ == "__main__":
    main()
