#!/usr/bin/env python3
"""레짐 점검 — FRED 공개 통계를 받아 사전에 정한 규칙(regime_rules.py)으로 판정하고 원본 결과를 기록한다.

계기판이지 핸들이 아니다: 규칙이 충족됐는지만 계산하고, 투자 판단은 하지 않는다.

산출 (<work> 기본: 저장소의 .work/ — 사이트 폴더 data/ 밖):
  <work>/raw/latest.json               원본 결과 (schema=2). 가장 최근 날짜의 결과만 이 이름으로 둔다
  <work>/raw/history/YYYY-MM-DD.json   날짜별 사본 (같은 날 다시 돌면 덮어쓴다)
  <work>/fred/<ID>.csv                 원자료 캐시 (--offline이면 캐시만 사용)
raw/와 fred/에는 재배포가 제한된 시리즈(S&P·ICE·Moody's)의 원값이 들어 있어 커밋·배포하지 않는다.
공개용 표는 render_public.py가 raw/latest.json에서 만들어 data/에 쓴다.
수신 실패면 아무것도 쓰지 않고 한 줄 오류로 끝난다 — 직전 결과가 남는다. 수신 실패에는 FRED 요청이 실패해
캐시로 대신한 시리즈도 포함한다(오프라인 실행 제외): 미수신+캐시 대체가 MAX_MISSING을 넘으면 기록하지 않는다.
과거 날짜(--date)는 지금 시점의 개정치로 다시 계산한 값이라 history에만 쓰고 latest는 되돌리지 않는다.

사용법:
  python regime_check.py [--work .work] [--date YYYY-MM-DD] [--offline] [--prev-regime A]
"""
import os, sys, json, argparse, datetime, time

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import fred_fetch as ff
import regime_rules as rr

SCHEMA = 2
DEFAULT_WORK = os.path.join(os.path.dirname(SCRIPTS), ".work")
MAX_MISSING = 2                              # 미수신+캐시 대체가 이보다 많으면 그날 결과를 기록하지 않는다(직전 결과 유지)
BUDGET_SEC = 60                              # 22개 수신 전체 시간 상한 — 느린 날에도 스케줄 작업이 제한 시간 안에 끝나게
SINCE_1990 = datetime.date(1990, 1, 1)
CI_BREAK = datetime.date(2025, 1, 1)         # BUSLOANS 분류 변경: 이 날 이후 기준치만 YoY 유효


def raw_dir(work):
    return os.path.join(work, "raw")


def _iso(d):
    return d.isoformat() if isinstance(d, datetime.date) else d


def _write_text(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


# ---------- 수신 ----------

def load_all(cache_dir, offline, today):
    """모든 시리즈 수신. 미수신이 MAX_MISSING을 넘는 순간 나머지는 시도하지 않는다
    (FRED가 요청마다 15초씩 멈추는 장애 때 22×15초를 기다리지 않기 위해 — 어차피 그 달은 기록되지 않는다).
    실패 없이 느리기만 한 날을 위해 전체 시간도 BUDGET_SEC로 묶는다: 요청마다 남은 예산을 타임아웃으로 주고,
    예산을 다 쓰면 나머지는 미수신 처리한다.
    온라인 실행에서 FRED 요청이 실패해 캐시로 대신한 시리즈도 '받지 못한 것'으로 센다(값은 캐시로 계산에 쓴다).
    관측치는 today 이하만 쓴다(--date로 과거 날짜를 주면 그 시점까지)."""
    series, sources, warns, missing = {}, {}, [], 0          # missing = 미수신 + (온라인일 때) 캐시 대체
    deadline = time.monotonic() + BUDGET_SEC
    for sid, (label, freq, _) in rr.SERIES.items():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            missing += 1
            series[sid], sources[sid] = None, {"source": None, "error": f"중단(시간 상한 {BUDGET_SEC}초 초과)"}
            warns.append(f"{sid}({label}) 미수신: 시간 상한 {BUDGET_SEC}초 초과")
            continue
        if missing > MAX_MISSING:
            series[sid], sources[sid] = None, {"source": None, "error": "중단(미수신 초과)"}
            continue
        try:
            s, src = ff.load(sid, cache_dir, offline=offline, timeout=min(ff.TIMEOUT, remaining))
            s = [x for x in s if x[0] <= today]
            if not s:
                raise RuntimeError(f"{today} 이전 관측치 없음")
        except Exception as e:
            missing += 1
            series[sid], sources[sid] = None, {"source": None, "error": str(e)}
            warns.append(f"{sid}({label}) 미수신: {e}")
            continue
        series[sid] = s
        if src == "cache" and not offline:
            missing += 1
            warns.append(f"{sid}({label}) FRED 수신 실패 → 캐시 사용")
        age = ff.freshness_days(s, today)
        sources[sid] = {"source": src, "last": _iso(s[-1][0]), "n": len(s), "age_days": age}
        if age is not None and age > rr.STALE_DAYS[freq]:
            warns.append(f"{sid}({label}) 마지막 관측 {_iso(s[-1][0])} — {age}일 경과")
    return series, sources, warns


# ---------- 계산 ----------

def _ind(value, asof=None, **extra):
    return {"value": value, "asof": _iso(asof), **extra}


def _last(series):
    return series[-1] if series else None


def compute(series, today, prev_regime=None):
    """시계열 → (지표 dict, 국면 판정 재료 dict, 경고 목록). 자료가 없는 지표는 value=None."""
    S = lambda sid: series.get(sid)
    ind, warns = {}, []

    def put(key, res, field="value", **extra):
        ind[key] = _ind(None if res is None else res[field], None if res is None else res.get("asof"), **extra)

    # 1. 통화승수·유통속도·지준/GDP
    m2, mb = S("M2SL"), S("BOGMBASE")
    ind["m2"], ind["mb"] = _ind(*reversed(_last(m2))) if m2 else _ind(None), _ind(*reversed(_last(mb))) if mb else _ind(None)
    if m2 and mb:
        common = ff.on_or_before(mb, m2[-1][0]) if m2[-1][0] <= mb[-1][0] else None
        d = min(m2[-1][0], mb[-1][0])
        a, b = ff.on_or_before(m2, d), ff.on_or_before(mb, d)
        ind["mult"] = _ind(a[1] / b[1] if a and b and b[1] else None, d)
    else:
        ind["mult"] = _ind(None)
    put("m2_yoy", ff.yoy(m2, same_month=True) if m2 else None)
    put("mb_yoy", ff.yoy(mb, same_month=True) if mb else None)
    m2v = S("M2V")
    ind["m2v"] = _ind(*reversed(_last(m2v))) if m2v else _ind(None)
    wres, gdp = S("WRESBAL"), S("GDP")
    if wres and gdp:
        g = _last(gdp)
        ind["reserves_gdp"] = _ind(wres[-1][1] / 1000 / g[1] * 100, wres[-1][0], gdp_quarter=_iso(g[0]))
        c = ff.change_days(wres, 91)
        ind["reserves_gdp_chg_3m"] = _ind(c["delta"] / 1000 / g[1] * 100 if c else None, wres[-1][0])
    else:
        ind["reserves_gdp"], ind["reserves_gdp_chg_3m"] = _ind(None), _ind(None)

    # 2. NDFI 대출
    nd, tot = S("LNFACBW027SBOG"), S("TOTLL")
    ind["ndfi_level"] = _ind(*reversed(_last(nd))) if nd else _ind(None)
    if nd and tot:
        t = ff.on_or_before(tot, nd[-1][0])
        ind["ndfi_share"] = _ind(nd[-1][1] / t[1] * 100 if t and t[1] else None, nd[-1][0])
    else:
        ind["ndfi_share"] = _ind(None)
    st = ff.step_excluded_yoy(nd, rr.TH["ndfi_step_bn"]) if nd else None
    ind["ndfi_yoy"] = _ind(st["value"] if st else None, st["asof"] if st else None,
                           raw=st["raw_value"] if st else None,
                           excluded=[[_iso(d), round(v, 1)] for d, v in st["excluded"]] if st else [])
    if st and st["excluded"]:
        warns.append("NDFI 계단 " + ", ".join(f"{_iso(d)} {v:+.0f}" for d, v in st["excluded"]) + " — YoY에서 제외")

    # 3. C&I 대 명목GDP
    ci = ff.yoy(S("BUSLOANS"), same_month=True) if S("BUSLOANS") else None
    ind["ci_yoy"] = _ind(ci["value"] if ci else None, ci["asof"] if ci else None,
                         valid=bool(ci and ci["base_date"] >= CI_BREAK))
    if ci and not ind["ci_yoy"]["valid"]:
        warns.append(f"C&I YoY 기준치 {_iso(ci['base_date'])}가 2025-01 분류 단절 이전 — 판정에 쓰지 않음")
    put("ngdp_yoy", ff.yoy(S("GDP"), same_month=True) if S("GDP") else None)

    # 4~5. 기간 프리미엄·스프레드
    tp = S("THREEFYTP10")
    ind["tp"] = _ind(*reversed(_last(tp))) if tp else _ind(None)
    put("tp_chg_3m", ff.change_days(tp, 91) if tp else None, "delta")
    baa = S("BAA10Y")
    if baa:
        low = ff.trailing_min(baa, 365)
        ind["baa10y"] = _ind(baa[-1][1], baa[-1][0], pct_since_1990=ff.percentile(baa, baa[-1][1], SINCE_1990),
                             from_low_12m=baa[-1][1] - low if low is not None else None)
    else:
        ind["baa10y"] = _ind(None, pct_since_1990=None, from_low_12m=None)
    for key, sid in (("hy_oas", "BAMLH0A0HYM2"), ("ig_oas", "BAMLC0A0CM"), ("t10y2y", "T10Y2Y"),
                     ("dfii10", "DFII10"), ("dgs10", "DGS10"), ("bei", "T10YIE"), ("sofr", "SOFR"),
                     ("dexkous", "DEXKOUS"), ("emp_level", "CES5552300001")):
        s = S(sid)
        ind[key] = _ind(*reversed(_last(s))) if s else _ind(None)
    put("bei_chg_3m", ff.change_days(S("T10YIE"), 91) if S("T10YIE") else None, "delta")
    put("sofr_chg_3m", ff.change_days(S("SOFR"), 91) if S("SOFR") else None, "delta")

    # 6. ρ60
    corr = ff.corr_summary(S("SP500"), S("DGS10"), 60) if S("SP500") and S("DGS10") else None
    ind["rho60"] = _ind(corr["value"] if corr else None, corr["asof"] if corr else None,
                        run_days=corr["run_days"] if corr else None, sign=corr["sign"] if corr else None,
                        window_start=_iso(corr["start"]) if corr else None)

    # 8. 근원 물가
    pce, cpi = S("PCEPILFE"), S("CPILFESL")
    put("core_pce_yoy", ff.yoy(pce, same_month=True) if pce else None)
    cy = ff.yoy(cpi, same_month=True) if cpi else None
    gaps = [g for g in ff.missing_months(cpi) if g >= f"{today.year - 2:04d}-01"] if cpi else []
    ind["core_cpi_yoy"] = _ind(cy["value"] if cy else None, cy["asof"] if cy else None, gaps=gaps)
    if gaps:
        warns.append("근원 CPI 결측월 " + ", ".join(gaps) + " — 그 달이 기준치가 되는 12개월 뒤 YoY는 산출 불가(None)로 둔다."
                     " BLS 대체입력 탓에 결측 이후 값도 편의가 있을 수 있음")
    if cpi and cy is None:
        warns.append("근원 CPI YoY 산출 불가 — 1년 전 같은 달 관측치 없음(결측월). 근원 PCE로 판단")
    a, b = ind["core_pce_yoy"]["value"], ind["core_cpi_yoy"]["value"]
    ind["core_gap"] = _ind(b - a if a is not None and b is not None else None, ind["core_cpi_yoy"]["asof"])

    # 14. 고용
    put("emp_yoy", ff.yoy(S("CES5552300001"), same_month=True) if S("CES5552300001") else None)

    # 국면 판정 재료 — 주가·금리 13주 추세, ρ60, 전환 경계 (공개본에는 싣지 않는다)
    sp13 = ff.pct_change_days(S("SP500"), 91) if S("SP500") else None
    y13 = ff.change_days(S("DGS10"), 91) if S("DGS10") else None
    sp_pct = sp13["value"] if sp13 else None
    y10_bp = y13["delta"] * 100 if y13 else None
    cand, note = rr.classify_regime(sp_pct, y10_bp, prev_regime)
    rho = ind["rho60"]["value"]
    # 전환 경계는 완성된 주만으로: 평일이면 이번 주 월요일 이후 관측치를 버린다(미완성 주를 한 주로 세지 않음)
    week_start = today - datetime.timedelta(days=today.weekday()) if today.weekday() < 5 \
        else today + datetime.timedelta(days=7 - today.weekday())
    wk = lambda sid: ff.weekly_last(S(sid), before=week_start) if S(sid) else None
    trig = rr.transition_triggers(wk("SP500"), wk("DGS10"), wk("BAMLC0A0CM"))
    inputs = {
        "sp_13w_pct": sp_pct, "y10_13w_bp": y10_bp,
        "sp_asof": _iso(sp13["asof"]) if sp13 else None, "y10_asof": _iso(y13["asof"]) if y13 else None,
        "regime_prev": prev_regime, "regime_candidate": cand, "regime_note": note,
        "rho60": rho, "rho60_run_days": ind["rho60"]["run_days"],
        "rho60_alert": bool((cand or prev_regime) == "A" and rho is not None and rho < 0),
        "core_cpi_lt3": None if b is None else ("Y" if b < 3.0 else "N"),
        "core_pce_yoy": a, "core_cpi_yoy": b,
        "transition": trig,
    }
    return ind, inputs, warns


def flat(ind):
    """규칙 평가용 평면 dict."""
    v = lambda k: ind.get(k, {}).get("value")
    return {"ci_yoy": v("ci_yoy"), "ci_valid": ind.get("ci_yoy", {}).get("valid", False), "ngdp_yoy": v("ngdp_yoy"),
            "ndfi_yoy": v("ndfi_yoy"), "ndfi_share": v("ndfi_share"),
            "baa10y": v("baa10y"), "baa10y_from_low": ind.get("baa10y", {}).get("from_low_12m"),
            "baa10y_pct": ind.get("baa10y", {}).get("pct_since_1990"), "hy_oas": v("hy_oas"),
            "rho60": v("rho60"), "rho60_run": ind.get("rho60", {}).get("run_days"), "rho60_sign": ind.get("rho60", {}).get("sign"),
            "t10y2y": v("t10y2y"), "dfii10": v("dfii10"), "bei": v("bei"), "bei_chg_3m": v("bei_chg_3m"),
            "core_pce_yoy": v("core_pce_yoy"), "core_cpi_yoy": v("core_cpi_yoy"), "core_gap": v("core_gap"),
            "tp": v("tp"), "tp_chg_3m": v("tp_chg_3m"), "sofr": v("sofr"), "sofr_chg_3m": v("sofr_chg_3m"),
            "reserves_gdp": v("reserves_gdp"), "reserves_gdp_chg_3m": v("reserves_gdp_chg_3m"), "mult": v("mult"),
            "emp_yoy": v("emp_yoy")}


# ---------- 실행 ----------

def _latest_date(work):
    try:
        with open(os.path.join(raw_dir(work), "latest.json"), encoding="utf-8") as f:
            return json.load(f).get("date")
    except (OSError, ValueError):
        return None


def build(work, today, offline=False, prev_regime=None):
    """수신 → 계산 → <work>/raw/history/<날짜>.json 기록, 가장 최근 날짜면 raw/latest.json도. 같은 날 다시 돌면 덮어쓴다.
    미수신+캐시 대체가 MAX_MISSING을 넘으면 아무것도 쓰지 않고 RuntimeError — 직전 결과가 그대로 남는다.
    prev_regime(직전 국면)은 사람이 판단해 넣는 값이라 기본은 None이다."""
    series, sources, warns = load_all(os.path.join(work, "fred"), offline, today)
    missing = [sid for sid, s in series.items() if s is None]
    cached = [sid for sid, s in sources.items() if s.get("source") == "cache" and not offline]
    bad = missing + cached
    if len(bad) > MAX_MISSING:
        raise RuntimeError(f"미수신 {len(missing)}개·캐시 대체 {len(cached)}개({', '.join(bad[:4])}"
                           f"{'…' if len(bad) > 4 else ''}) — {today} 결과를 기록하지 않음(직전 결과 유지)."
                           f" 네트워크 확인 후 재실행")
    ind, inputs, w2 = compute(series, today, prev_regime)
    signals = rr.evaluate(flat(ind))
    js = {"date": today.isoformat(), "schema": SCHEMA, "sources": sources,
          "indicators": ind, "signals": signals, "regime_inputs": inputs,
          "manual": [list(m) for m in rr.MANUAL], "warnings": warns + w2}
    text = json.dumps(js, ensure_ascii=False, indent=2)
    hist = os.path.join(raw_dir(work), "history")
    os.makedirs(hist, exist_ok=True)
    _write_text(os.path.join(hist, f"{today.isoformat()}.json"), text)
    prev = _latest_date(work)
    latest_updated = prev is None or today.isoformat() >= prev      # 과거 날짜 재계산은 latest를 되돌리지 않는다
    if latest_updated:
        _write_text(os.path.join(raw_dir(work), "latest.json"), text)
    return {"status": "ok", "date": today.isoformat(), "latest_updated": latest_updated, "total": len(signals),
            "fired": sum(1 for s in signals if s["fired"] is True),
            "unknown": sum(1 for s in signals if s["fired"] is None),
            "net": sum(1 for s in sources.values() if s.get("source") == "net"),
            "cache": sum(1 for s in sources.values() if s.get("source") == "cache"),
            "missing": len(missing), "series": len(series)}


def main():
    ap = argparse.ArgumentParser(description="FRED 공개 통계로 규칙 점검 — 원본 결과를 <work>/raw/에 기록")
    ap.add_argument("--work", default=DEFAULT_WORK, help="작업 폴더 (기본: 저장소의 .work/ — 커밋·배포하지 않는다)")
    ap.add_argument("--date", default=None, help="계산 기준일 YYYY-MM-DD (기본: 오늘). 그 날짜 이후 관측치는 쓰지 않는다")
    ap.add_argument("--offline", action="store_true", help="FRED 수신 없이 캐시만 사용")
    ap.add_argument("--prev-regime", default=None, help="직전 국면(A/A′/B/C) — 사람이 판단해 넣는 값. 기본은 없음")
    a = ap.parse_args()
    try:
        today = datetime.datetime.strptime(a.date, "%Y-%m-%d").date() if a.date else datetime.date.today()
        if today > datetime.date.today():
            raise RuntimeError(f"미래 날짜 {today} — 계산하지 않음")
        res = build(os.path.abspath(a.work), today, offline=a.offline, prev_regime=a.prev_regime)
    except (RuntimeError, ValueError) as e:
        print(f"[regime_check] {e}", file=sys.stderr)    # 한 줄로 끝낸다 — 트레이스백 첫 줄로는 원인이 안 보인다
        sys.exit(1)
    # 이 출력은 공개 저장소의 Actions 로그에 남는다 — 요약 숫자만 찍고 지표 값·해석은 찍지 않는다
    print(f"[regime_check] {res['date']} 계산 — 규칙 {res['total']}개 중 충족 {res['fired']} · 판정 불가 {res['unknown']}"
          f" · 수신 {res['net']} · 캐시 {res['cache']} · 미수신 {res['missing']} / {res['series']}"
          + ("" if res["latest_updated"] else " · 과거 날짜라 latest 유지"))


if __name__ == "__main__":
    main()
