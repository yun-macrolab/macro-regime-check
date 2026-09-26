#!/usr/bin/env python3
"""월간 레짐 점검 — FRED 지표를 받아 시나리오 A/B/C/D 신호를 판정하고 기록한다.

보고서(금융업계 미래 지도, 2026-09-22) 00장 7절 월간 점검표의 자동화. 계기판이지 핸들이 아니다:
시트의 FLAG(C19:C24)·판단로그의 '상태'는 계속 사람이 쓴다. 이 스크립트는 판정 재료와 후보만 보여준다.

산출:
  <폴더>/_news-to-macro/regime/YYYY-MM.json     그 달의 전체 결과 (schema=1)
  <폴더>/_news-to-macro/regime/YYYY-MM.md       상세 표
  <폴더>/_news-to-macro/regime/regime_latest.md 알림용 압축본 — 오늘 쓰였을 때만 daily_run이 [레짐 점검]으로 싣는다
  <폴더>/_news-to-macro/regime/fred/<ID>.csv    원자료 캐시 (--offline 이면 캐시만 사용)
그 달의 JSON이 이미 있으면 아무것도 쓰지 않는다(--force로 덮어쓰기). daily_run이 달의 첫 런에 자동 호출.

사용법:
  python monthly_regime.py <폴더> [--date YYYY-MM-DD] [--offline] [--force]
                           [--prev-regime A] [--log-csv <판단로그.csv>]
  --log-csv: 판단로그 CSV의 매칭 ID 행에 '최근 점검일'과 '점검 메모'만 기입한다. '상태'는 절대 건드리지 않는다.
"""
import os, sys, csv, json, argparse, datetime, time

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import fred_fetch as ff
import regime_rules as rr

SCHEMA = 1
LATEST_NAME = "regime_latest.md"
MAX_MISSING = 2                              # 미수신 시리즈가 이보다 많으면 그 달을 기록하지 않는다(다음 날 재시도)
BUDGET_SEC = 60                              # 22개 수신 전체 시간 상한 — 헤드리스 셸의 명령당 2분 제한 안에 끝내기 위해
SINCE_1990 = datetime.date(1990, 1, 1)
CI_BREAK = datetime.date(2025, 1, 1)         # BUSLOANS 분류 변경: 이 날 이후 기준치만 YoY 유효


def regime_dir(folder):
    return os.path.join(folder, "_news-to-macro", "regime")


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
    관측치는 today 이하만 쓴다(--date로 과거 날짜를 주면 그 시점까지)."""
    series, sources, warns, missing = {}, {}, [], 0
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
    """시계열 → (지표 dict, 시트 참고값 dict, 경고 목록). 자료가 없는 지표는 value=None."""
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

    # 시트 참고값 (운영기준 7-1·7-2·7-4)
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
    sheet = {
        "sp_13w_pct": sp_pct, "y10_13w_bp": y10_bp,
        "sp_asof": _iso(sp13["asof"]) if sp13 else None, "y10_asof": _iso(y13["asof"]) if y13 else None,
        "regime_prev": prev_regime, "regime_candidate": cand, "regime_note": note,
        "rho60": rho, "rho60_run_days": ind["rho60"]["run_days"],
        "rho60_alert": bool((cand or prev_regime) == "A" and rho is not None and rho < 0),
        "core_cpi_lt3": None if b is None else ("Y" if b < 3.0 else "N"),
        "core_pce_yoy": a, "core_cpi_yoy": b,
        "transition": trig,
    }
    return ind, sheet, warns


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


# ---------- 렌더 ----------

def _mark(fired):
    return "●" if fired else ("?" if fired is None else "○")


def render_md(js):
    """알림용 압축본. 머리말 [레짐 점검]은 compose_report가 붙인다."""
    sig = js["signals"]
    n_f, n_u = sum(1 for s in sig if s["fired"]), sum(1 for s in sig if s["fired"] is None)
    si, tr = js["sheet_inputs"], js["sheet_inputs"]["transition"]
    f = rr._f
    lines = [f"{js['month']} 월간 점검 (계산 {js['date']}) — 핵심 신호 {n_f}/{len(sig)} 발동, 판정불가 {n_u}",
             "● 발동 · ○ 미발동 · ? 자료 부족"]
    lines += [f"{_mark(s['fired'])} [{s['scenario']}] {s['text']}" for s in sig]
    tri = " · ".join(f"t{k[1]} {'ON' if v else ('OFF' if v is False else '?')}" for k, v in (("t2", tr["t2"]), ("t4", tr["t4"])))
    lines += [
        "",
        "시트 참고값 (C19:C24는 사람이 입력 — 아래는 계산값):",
        f"  국면 후보 {si['regime_candidate'] or '판정불가'} ({si['regime_note']}, 직전 {si['regime_prev'] or '미입력'})"
        f" · S&P 13주 {f(si['sp_13w_pct'], '{:+.1f}')}% · 10년 13주 {f(si['y10_13w_bp'], '{:+.0f}')}bp",
        f"  ρ60 {f(si['rho60'])} ({f(si['rho60_run_days'], '{:.0f}')}일 연속)" + (" ⚠ A 국면에서 음(−) = A′ 경보" if si["rho60_alert"] else ""),
        f"  근원 CPI<3% {si['core_cpi_lt3'] or '?'} (근원 CPI {f(si['core_cpi_yoy'], '{:.2f}')}% · 근원 PCE {f(si['core_pce_yoy'], '{:.2f}')}% — 보고서 D1/D2 기준은 PCE)",
        f"  전환 경계 자동 트리거 {tr['auto_on']}/2 ({tri}; t1·t3 수동, 넷 중 둘 이상이면 ON)",
        "",
        "수동 확인: " + " · ".join(f"{m[2]} ({m[0]}, {m[1]})" for m in js["manual"]),
    ]
    if js["warnings"]:
        lines += ["", "경고: " + " / ".join(js["warnings"])]
    src = [s.get("source") for s in js["sources"].values()]
    lines.append(f"자료: FRED 수신 {src.count('net')} · 캐시 {src.count('cache')} · 미수신 {src.count(None)}"
                 f" · 상세 regime/{js['month']}.md")
    return "\n".join(lines)


def render_detail_md(js):
    f = rr._f
    lines = [f"# 레짐 점검 {js['month']} (계산 {js['date']}, schema {js['schema']})", "",
             "보고서 00장 7절 월간 점검표의 자동 계산. 시트 FLAG·판단로그 상태는 사람이 쓴다.", "",
             "## 신호", "", "| | 시나리오 | 규칙 | 판정 | 판단로그 ID | 출처 |", "|---|---|---|---|---|---|"]
    lines += [f"| {_mark(s['fired'])} | {s['scenario']} | {s['name']} | {s['text']} | {', '.join(s['log_ids'])} | {s['source']} |"
              for s in js["signals"]]
    lines += ["", "## 지표", "", "| 키 | 값 | 기준일 | 부가 |", "|---|---|---|---|"]
    for k, v in js["indicators"].items():
        extra = {kk: vv for kk, vv in v.items() if kk not in ("value", "asof")}
        lines.append(f"| {k} | {f(v['value'], '{:.3f}')} | {v['asof'] or '—'} | {json.dumps(extra, ensure_ascii=False) if extra else ''} |")
    lines += ["", "## 시트 참고값", "", "```", json.dumps(js["sheet_inputs"], ensure_ascii=False, indent=1), "```",
              "", "## 수동 확인 항목", ""]
    lines += [f"- [ ] {m[2]} — {m[0]} ({m[1]})" for m in js["manual"]]
    lines += ["", "## 자료 출처", "", "| ID | 출처 | 마지막 관측 | n | 경과일 |", "|---|---|---|---|---|"]
    lines += [f"| {k} | {v.get('source') or '미수신'} | {v.get('last', '—')} | {v.get('n', '—')} | {v.get('age_days', '—')} |"
              for k, v in js["sources"].items()]
    if js["warnings"]:
        lines += ["", "## 경고", ""] + [f"- {w}" for w in js["warnings"]]
    return "\n".join(lines) + "\n"


# ---------- 판단로그 CSV ----------

REQUIRED_LOG_COLS = ("ID", "최근 점검일", "점검 메모")


def read_log_csv(path):
    """판단로그 CSV 읽기 + 헤더 검사. 열이 빠졌거나 행 필드 수가 헤더와 다르면 파일을 건드리지 않고 RuntimeError."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, restkey="_extra")
        cols, rows = reader.fieldnames or [], list(reader)
    missing = [c for c in REQUIRED_LOG_COLS if c not in cols]
    if missing:
        raise RuntimeError(f"판단로그 CSV 열 누락 {missing}: {path}")
    if any("_extra" in r for r in rows):
        raise RuntimeError(f"판단로그 CSV에 헤더보다 필드가 많은 행이 있음: {path}")
    return cols, rows


def patch_log_csv(path, js, today):
    """판단로그 CSV의 매칭 ID 행에 최근 점검일·점검 메모만 기입. 상태는 건드리지 않는다. 기입한 행 수 반환.
    매칭 행이 없으면 파일을 다시 쓰지 않는다."""
    memo = {}
    for s in js["signals"]:
        for lid in s["log_ids"]:
            memo.setdefault(lid, []).append(s["text"])
    cols, rows = read_log_csv(path)
    n = 0
    for r in rows:
        if r.get("ID") in memo:
            r["최근 점검일"] = today.isoformat()
            r["점검 메모"] = ("[자동] " + " / ".join(memo[r["ID"]]))[:300]
            n += 1
    if n == 0:
        return 0
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)
    return n


# ---------- 실행 ----------

def sheet_regime(folder, today):
    """현재 주 워크북의 국면 FLAG(C19). 읽지 못하면 None — 필수 아님."""
    try:
        import week_utils as wu
        import sheet_v2 as sv
        return sv.read_state(wu.week_path(folder, today))["flags"].get("regime")
    except Exception:
        return None


def build(folder, today, offline=False, force=False, prev_regime=None, log_csv=None):
    rdir = regime_dir(folder)
    month = today.strftime("%Y-%m")
    month_json = os.path.join(rdir, f"{month}.json")
    if os.path.exists(month_json) and not force:
        return {"status": "skipped", "path": month_json}
    if log_csv:
        read_log_csv(log_csv)                # 헤더가 틀리면 월 파일을 쓰기 전에 실패
    os.makedirs(rdir, exist_ok=True)
    series, sources, warns = load_all(os.path.join(rdir, "fred"), offline, today)
    missing = [sid for sid, s in series.items() if s is None]
    if len(missing) > MAX_MISSING:       # 빈 결과로 그 달을 '완료'로 만들면 daily_run이 다시 시도하지 않는다
        raise RuntimeError(f"미수신 {len(missing)}개({', '.join(missing[:4])}{'…' if len(missing) > 4 else ''})"
                           f" — {month} 결과를 기록하지 않음. 네트워크 확인 후 재실행")
    if prev_regime is None:
        prev_regime = sheet_regime(folder, today)
    ind, sheet, w2 = compute(series, today, prev_regime)
    signals = rr.evaluate(flat(ind))
    js = {"date": today.isoformat(), "month": month, "schema": SCHEMA, "sources": sources,
          "indicators": ind, "signals": signals, "sheet_inputs": sheet,
          "manual": [list(m) for m in rr.MANUAL], "warnings": warns + w2}
    _write_text(month_json, json.dumps(js, ensure_ascii=False, indent=2))
    _write_text(os.path.join(rdir, f"{month}.md"), render_detail_md(js))
    _write_text(os.path.join(rdir, LATEST_NAME), render_md(js))
    patched = patch_log_csv(log_csv, js, today) if log_csv else 0
    return {"status": "ok", "path": month_json, "fired": sum(1 for s in signals if s["fired"]),
            "total": len(signals), "patched": patched, "text": render_md(js)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--date", default=None)
    ap.add_argument("--offline", action="store_true", help="FRED 수신 없이 캐시만 사용")
    ap.add_argument("--force", action="store_true", help="그 달의 결과가 있어도 다시 계산")
    ap.add_argument("--prev-regime", default=None, help="직전 국면(A/A′/B/C). 없으면 현재 주 시트 C19를 읽는다")
    ap.add_argument("--log-csv", default=None, help="판단로그 CSV 경로 — 최근 점검일·점검 메모만 기입")
    a = ap.parse_args()
    today = datetime.datetime.strptime(a.date, "%Y-%m-%d").date() if a.date else datetime.date.today()
    try:
        res = build(os.path.abspath(a.folder), today, offline=a.offline, force=a.force,
                    prev_regime=a.prev_regime, log_csv=a.log_csv)
    except RuntimeError as e:
        # 한 줄로 끝낸다 — daily_run이 이 stderr 첫 줄을 알림 '[레짐 점검] 실패 — …'에 싣는다
        print(f"[레짐] {e}", file=sys.stderr)
        sys.exit(1)
    if res["status"] == "skipped":
        print(f"[레짐] {today:%Y-%m} 결과가 이미 있음 — 건너뜀 ({res['path']}); 다시 계산하려면 --force")
        return
    print(res["text"])
    if a.log_csv:
        print(f"[레짐] 판단로그 {res['patched']}행 기입: {a.log_csv}")


if __name__ == "__main__":
    main()
