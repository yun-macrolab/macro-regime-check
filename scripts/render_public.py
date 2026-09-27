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
# 출처 표기 — FRED는 인용을 요청하고, SOFR은 뉴욕 연은 이용약관이 고지를 요구한다
# (정확한 고지 문구는 newyorkfed.org 이용약관 원문으로 확인할 것 — 검색 요약 기준으로 작성)
NYFED_NOTICE = ("SOFR: Federal Reserve Bank of New York. Content from the New York Fed "
                "subject to the Terms of Use at newyorkfed.org.")
ATTRIBUTION = [
    "Source: FRED®, Federal Reserve Bank of St. Louis (https://fred.stlouisfed.org/).",
    NYFED_NOTICE,
    "전년비·3개월 변화·상관·비율은 이 저장소 코드가 원자료로 계산한 값이다.",
]

# FRED 시리즈 고지에서 재배포·파생물을 제한한 시리즈 → 값은 싣지 않고 충족 여부와 FRED 링크만
RESTRICTED = {"SP500": "S&P Dow Jones Indices", "BAMLH0A0HYM2": "ICE Data Indices",
              "BAMLC0A0CM": "ICE Data Indices", "BAA10Y": "Moody's"}
OWNER = {"M2SL": "FRB", "BOGMBASE": "FRB", "M2V": "FRB St. Louis", "WRESBAL": "FRB", "GDP": "BEA",
         "LNFACBW027SBOG": "FRB", "TOTLL": "FRB", "BUSLOANS": "FRB", "THREEFYTP10": "FRB (Kim-Wright)",
         "DGS10": "FRB", "T10Y2Y": "FRB St. Louis", "DFII10": "FRB", "T10YIE": "FRB St. Louis",
         "PCEPILFE": "BEA", "CPILFESL": "BLS", "SOFR": "FRBNY", "DEXKOUS": "FRB", "CES5552300001": "BLS",
         **RESTRICTED}
# 공개 가능한 원본 경고 — 이 문구로 시작하는 것만 싣는다(미수신·경로가 섞인 오류 문구는 자료 신선도 표로 대신)
WARNING_PREFIXES = ("NDFI 계단", "C&I YoY 기준치", "근원 CPI 결측월", "근원 CPI YoY 산출 불가")


def _obs(key, label, unit, series, field="value", derived=False):
    return {"key": key, "label": label, "unit": unit, "series": series, "field": field, "derived": derived}


def citation(sid):
    """시리즈별 출처 문구 (FRED 인용 형식)."""
    if sid == "SOFR":
        return NYFED_NOTICE
    return f"{OWNER[sid]}, {rr.SERIES[sid][0]} [{sid}], retrieved from FRED, Federal Reserve Bank of St. Louis"


def public_rules():
    """규칙 key → 공개 문구·관측치 정의. 임계값은 호출 시점의 rr.TH에서 읽는다."""
    th = rr.TH
    return {
        "ci_vs_ngdp": {
            "title": "기업대출 증가율 대 명목 성장률",
            "rule": "C&I 대출 전년비가 명목GDP 전년비보다 낮으면 충족",
            "obs": [_obs("ci_yoy", "C&I 대출 전년비", "%", ["BUSLOANS"]),
                    _obs("ngdp_yoy", "명목GDP 전년비", "%", ["GDP"])]},
        "ndfi_credit": {
            "title": "은행의 비은행 금융기관 대출",
            "rule": f"전년비(재분류로 보이는 주간 +{th['ndfi_step_bn']:g}십억달러 이상 증가 계단 제외)가 "
                    f"{th['ndfi_two_digit']:g}% 미만이면 충족",
            "obs": [_obs("ndfi_yoy", "NDFI 대출 전년비(계단 제외)", "%", ["LNFACBW027SBOG"]),
                    _obs("ndfi_share", "총대출 중 비중", "%", ["LNFACBW027SBOG", "TOTLL"])]},
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
                    _obs("bei_chg_3m", "BEI 3개월 변화", "%p", ["T10YIE"])]},
        "core_inflation": {
            "title": "근원 물가",
            "rule": f"근원 PCE 전년비가 {th['core_pce_split']:g}% 이하이면 충족 (근원 CPI는 참고)",
            "obs": [_obs("core_pce_yoy", "근원 PCE 전년비", "%", ["PCEPILFE"]),
                    _obs("core_cpi_yoy", "근원 CPI 전년비", "%", ["CPILFESL"])]},
        "term_premium": {
            "title": "10년 기간 프리미엄",
            "rule": f"10년 기간 프리미엄(Kim-Wright)이 3개월 전보다 {th['tp_drop_3m']:g}%p 이상 낮아지면 충족",
            "obs": [_obs("tp", "기간 프리미엄", "%", ["THREEFYTP10"]),
                    _obs("tp_chg_3m", "3개월 변화", "%p", ["THREEFYTP10"])]},
        "sofr": {
            "title": "단기 조달금리 SOFR",
            "rule": f"SOFR이 3개월 전보다 {th['sofr_rise_3m']:g}%p 이상 높아지면 충족",
            "obs": [_obs("sofr", "SOFR", "%", ["SOFR"]),
                    _obs("sofr_chg_3m", "3개월 변화", "%p", ["SOFR"])]},
        "reserves_multiplier": {
            "title": "지준과 통화승수",
            "rule": f"지준/명목GDP가 {th['reserves_gdp_low']:g}% 미만이거나, 3개월 새 {th['reserves_gdp_rise_3m']:g}%p "
                    f"이상 늘고 근원 PCE 전년비가 {th['reserves_pce_floor']:g}%를 넘으면 충족",
            "obs": [_obs("reserves_gdp", "지준/명목GDP", "%", ["WRESBAL", "GDP"]),
                    _obs("reserves_gdp_chg_3m", "3개월 변화", "%p", ["WRESBAL", "GDP"]),
                    _obs("mult", "통화승수(M2/본원통화)", "배", ["M2SL", "BOGMBASE"])]},
        "employment": {
            "title": "미 증권·투자업 고용",
            "rule": "고용 전년비가 0보다 작으면 충족",
            "obs": [_obs("emp_yoy", "고용 전년비", "%", ["CES5552300001"])]},
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
    rules = []
    for s in raw["signals"]:
        spec = table[s["key"]]
        obs = [{"label": o["label"], "unit": o["unit"], "series": o["series"], "derived": o["derived"],
                "value": _round(ind.get(o["key"], {}).get(o["field"])), "asof": ind.get(o["key"], {}).get("asof")}
               for o in spec["obs"]]
        rules.append({"key": s["key"], "title": spec["title"], "rule": spec["rule"], "status": _status(s["fired"]),
                      "observations": obs,
                      "restricted_series": [{"series": sid, "owner": RESTRICTED[sid], "url": FRED_URL.format(sid)}
                                            for sid in spec.get("restricted", [])]})
    health = []
    for sid, (label, freq, _) in rr.SERIES.items():
        src = raw["sources"].get(sid, {})
        age = src.get("age_days")
        health.append({"series": sid, "label": label, "owner": OWNER.get(sid, ""), "url": FRED_URL.format(sid),
                       "last": src.get("last"), "age_days": age,
                       "fetched": src.get("source") or "missing",
                       "stale": bool(age is not None and age > rr.STALE_DAYS[freq]),
                       "display": "status_only" if sid in RESTRICTED else "value",
                       "citation": citation(sid)})
    counts = {k: sum(1 for r in rules if r["status"] == k) for k in ("met", "not_met", "unknown")}
    return {"schema": SCHEMA, "date": raw["date"],
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "notice": NOTICE, "attribution": list(ATTRIBUTION),
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
