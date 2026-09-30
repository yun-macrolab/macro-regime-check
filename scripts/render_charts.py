#!/usr/bin/env python3
"""그래프 자료 — regime_check.py가 받은 원자료(<work>/fred)로 사이트 그래프용 시계열(<out>/charts.json)을 만든다.

규칙 카드 그래프는 규칙이 실제로 보는 양을 그린다. 표본 날짜마다 원자료를 그 날 이하로 자르고 규칙 점검과
같은 함수(fred_fetch)로 계산하므로, 마지막 점이 공개본 카드의 값과 같다(test_render_charts.py가 강제).
싣지 않는 것 (test_render_charts.py가 강제):
  - 재배포가 제한된 시리즈(render_public.RESTRICTED)의 원값 — 예외는 원값을 되살릴 수 없는 60영업일 상관(derived)
  - 고정 표(chart_table) 밖의 문자열
그래프마다 출처 줄(source_note: FRED가 적은 출처 + FRED 경유, 계산한 선이면 누가 계산했는지)을 싣고,
SOFR 그래프에는 뉴욕 연은 참조금리 고지(render_public.sofr_notices)를 함께 싣는다(이용약관 원문 확인 2026-09-30).
기준일은 <work>/raw/latest.json의 date — 그 뒤 관측치는 쓰지 않는다. 한 시리즈가 없으면 그 선만 빠지고,
규칙 그래프의 주 선이 없으면 그 그래프만 빠진다(나머지는 만든다).
charts.json은 더 최근 날짜의 그래프 자료를 과거 날짜로 덮지 않는다.

산출: <out>/charts.json (압축 JSON)
사용법: python render_charts.py [--work .work] [--out data]
"""
import os, sys, json, bisect, argparse, datetime

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import fred_fetch as ff
import regime_rules as rr
import regime_check as rck
import render_public as rp

SCHEMA = 1
REPO = os.path.dirname(SCRIPTS)
DEFAULT_WORK = os.path.join(REPO, ".work")
DEFAULT_OUT = os.path.join(REPO, "data")
ALLOWED = set(rr.SERIES) - set(rp.RESTRICTED)
NOTICE_CHARTS = {"sofr"}                      # 참조금리 고지를 함께 싣는 그래프
LOOKBACK = datetime.timedelta(days=400)       # 전년비·3개월 변화·60영업일 상관이 기간 첫 점에서 보는 과거(1년+여유)


# ---------- 점마다 규칙 함수로 ----------

def upto(series, d):
    """d 이하 관측치만 (날짜 오름차순 시계열)."""
    return series[:bisect.bisect_right(series, (d, float("inf")))]


def _level(sid):
    def calc(S, d):
        s = upto(S[sid], d)
        return s[-1][1] if s else None
    return calc


def _yoy(sid, since=None):
    def calc(S, d):
        r = ff.yoy(upto(S[sid], d), same_month=True)
        return None if not r or (since and r["base_date"] < since) else r["value"]
    return calc


def _chg3m(sid):
    def calc(S, d):
        r = ff.change_days(upto(S[sid], d), 91)
        return r["delta"] if r else None
    return calc


def _ndfi_yoy(S, d):
    r = ff.step_excluded_yoy(upto(S["LNFACBW027SBOG"], d), rr.TH["ndfi_step_bn"])
    return r["value"] if r else None


def _reserves_gdp(S, d):
    """지준/명목GDP(%). 지난 점은 d 이하 최신 분기 GDP로 나눈다(나중에 나온 GDP로 과거 비율을 다시 쓰지 않게).
    마지막 점만은 regime_check.compute처럼 기준일 이하 최신 GDP로 — 분기 첫 주에 기준일을 과거로 준 재계산에서
    분기 시작일(GDP 관측일)이 마지막 지준 주보다 늦어도 카드 값과 같게."""
    w = upto(S["WRESBAL"], d)
    g = S["GDP"][-1] if w and w[-1][0] == S["WRESBAL"][-1][0] else ff.on_or_before(S["GDP"], d)
    return w[-1][1] / 1000 / g[1] * 100 if w and g and g[1] else None


def _sampled(base, calc):
    """표본 날짜 = base 시리즈의 관측일(일간이면 ISO 주별 마지막 관측일) → [(date, calc(S, date))]."""
    def points(S, start):
        s = S[base]
        dates = [d for d, _ in (ff.weekly_last(s) if rr.SERIES[base][1] == "D" else s) if d >= start]
        return [(d, calc(S, d)) for d in dates]
    return points


def rolling_corr(px, y, n=60):
    """ff.corr_summary와 같은 계산의 전체 목록 [(date, corr|None)] — 마지막 원소가 corr_summary의 값."""
    al = ff.align(px, y)
    rets, difs, dates = [], [], []
    for (_, p0, y0), (d, p1, y1) in zip(al, al[1:]):
        if p0 == 0:
            continue
        rets.append(p1 / p0 - 1)
        difs.append(y1 - y0)
        dates.append(d)
    return [(dates[end - 1], ff.pearson(rets[end - n:end], difs[end - n:end])) for end in range(n, len(rets) + 1)]


def _rho60_points(S, start):
    return [(d, v) for d, v in ff.weekly_last(rolling_corr(S["SP500"], S["DGS10"], 60)) if d >= start]


# ---------- 고정 표 ----------

def _line(key, label, role, series, points, derived=False):
    return {"key": key, "label": label, "role": role, "series": series, "derived": derived, "points": points}


def _chart(key, title, unit, years, lines, zero=False, threshold=None, note=None, computed=True):
    """computed=False: 원자료 수준을 그대로 그리는 그래프(출처 줄에 '계산한 값'을 붙이지 않는다)."""
    return {"key": key, "title": title, "unit": unit, "years": years, "zero": zero,
            "threshold": threshold, "note": note, "computed": computed, "lines": lines}


def source_note(spec, keys=None):
    """그래프 밑 출처 줄 — FRED 시리즈 페이지의 출처와 FRED 경유(FRED: 보여 줄 때 출처·FRED 경유를 함께),
    계산한 선이면 누가 계산했는지(뉴욕 연은 이용약관 Conditions 4: 파생값을 원 발행처의 것으로 보이게 하지 않는다).
    keys를 주면 그 선(실제로 그려진 선)의 출처만 — 자료가 없어 빠진 선의 출처는 적지 않는다."""
    names = list(dict.fromkeys(rp.FRED_SOURCE[sid] for ln in spec["lines"]
                               if keys is None or ln["key"] in keys for sid in ln["series"]))
    note = "자료: " + " · ".join(names) + " (via FRED)"
    return note + (" · 선은 macro-regime-check가 이 자료로 계산한 값" if spec["computed"] else "")


def _lvl(key, label, role, sid):
    return _line(key, label, role, [sid], _sampled(sid, _level(sid)))


def chart_table():
    """그래프 정의 — 문구·시리즈·계산. 임계값은 호출 시점의 rr.TH에서 읽는다."""
    th = rr.TH
    overview = [
        _chart("yield10", "미 10년 금리 분해", "%", 5, zero=True, computed=False, lines=[
            _lvl("dgs10", "명목 10년", "series", "DGS10"),
            _lvl("dfii10", "10년 실질", "series", "DFII10"),
            _lvl("bei", "10년 BEI", "series", "T10YIE")]),
        _chart("term", "기간 프리미엄과 10년−2년", "%p", 5, zero=True, computed=False, lines=[
            _lvl("tp", "기간 프리미엄", "series", "THREEFYTP10"),
            _lvl("t10y2y", "10년−2년", "series", "T10Y2Y")]),
    ]
    rules = {
        "ci_vs_ngdp": _chart("ci_vs_ngdp", "C&I 대출 전년비와 명목GDP 전년비", "%", 3,
                             note="C&I 전년비는 2025-01 분류 변경 뒤 기준치가 있는 달부터", lines=[
            _line("ci_yoy", "C&I 대출 전년비", "main", ["BUSLOANS"],
                  _sampled("BUSLOANS", _yoy("BUSLOANS", since=rck.CI_BREAK))),
            _line("ngdp_yoy", "명목GDP 전년비", "ref", ["GDP"], _sampled("GDP", _yoy("GDP")))]),
        "ndfi_credit": _chart("ndfi_credit", "NDFI 대출 전년비(계단 제외)", "%", 3, threshold=th["ndfi_two_digit"],
                              lines=[_line("ndfi_yoy", "NDFI 대출 전년비(계단 제외)", "main", ["LNFACBW027SBOG"],
                                           _sampled("LNFACBW027SBOG", _ndfi_yoy))]),
        "stock_bond_corr": _chart("stock_bond_corr", "주가-금리 60영업일 상관", "", 3, zero=True,
                                  note="S&P500 원값은 싣지 않는다 — 이 저장소 코드가 계산한 상관만", lines=[
            _line("rho60", "60영업일 상관", "main", ["SP500", "DGS10"], _rho60_points, derived=True)]),
        "curve_inversion": _chart("curve_inversion", "10년−2년 금리차", "%p", 3, threshold=0.0, computed=False,
                                  lines=[_lvl("t10y2y", "10년−2년", "main", "T10Y2Y")]),
        "real_rate_bei": _chart("real_rate_bei", "10년 실질금리", "%", 3, zero=True, threshold=th["real_rate_c"],
                                computed=False,
                                lines=[_lvl("dfii10", "10년 실질금리", "main", "DFII10"),
                                       _lvl("bei", "10년 BEI", "ref", "T10YIE")]),
        "core_inflation": _chart("core_inflation", "근원 PCE·CPI 전년비", "%", 3, threshold=th["core_pce_split"],
                                 note="근원 CPI는 참고 — 1년 전 같은 달 관측치가 없는 달은 비운다", lines=[
            _line("core_pce_yoy", "근원 PCE 전년비", "main", ["PCEPILFE"], _sampled("PCEPILFE", _yoy("PCEPILFE"))),
            _line("core_cpi_yoy", "근원 CPI 전년비", "ref", ["CPILFESL"], _sampled("CPILFESL", _yoy("CPILFESL")))]),
        "term_premium": _chart("term_premium", "기간 프리미엄 3개월 변화", "%p", 3, zero=True,
                               threshold=-th["tp_drop_3m"], lines=[
            _line("tp_chg_3m", "기간 프리미엄 3개월 변화", "main", ["THREEFYTP10"],
                  _sampled("THREEFYTP10", _chg3m("THREEFYTP10")))]),
        "reserves_multiplier": _chart("reserves_multiplier", "지준/명목GDP", "%", 3, threshold=th["reserves_gdp_low"],
                                      lines=[_line("reserves_gdp", "지준/명목GDP", "main", ["WRESBAL", "GDP"],
                                                   _sampled("WRESBAL", _reserves_gdp))]),
        "employment": _chart("employment", "미 증권·투자업 고용 전년비", "%", 3, threshold=0.0, lines=[
            _line("emp_yoy", "고용 전년비", "main", ["CES5552300001"],
                  _sampled("CES5552300001", _yoy("CES5552300001")))]),
        "sofr": _chart("sofr", "SOFR 3개월 변화", "%p", 3, zero=True, threshold=th["sofr_rise_3m"],
                       note="주마다 마지막 관측일의 91일 전 대비 변화(카드 값과 같은 계산) — 월말·분기말 급등이 섞일 수 있다",
                       lines=[_line("sofr_chg_3m", "SOFR 3개월 변화", "main", ["SOFR"], _sampled("SOFR", _chg3m("SOFR")))]),
    }
    return {"overview": overview, "rules": rules}


# ---------- 만들기 ----------

def _round(v):
    return None if v is None else round(v, 3) + 0.0          # + 0.0: -0.0을 0.0으로


def _render_chart(spec, S, asof):
    """고정 표의 그래프 하나 → 공개 형태. 자료가 없는 선은 빼고, 남은 선이 없거나 규칙의 주 선이 없으면 None."""
    start = ff.shift_year(asof, -spec["years"])
    lines = []
    for ln in spec["lines"]:
        if any(S.get(sid) is None for sid in ln["series"]):
            continue
        T = {sid: [x for x in S[sid] if x[0] >= start - LOOKBACK] for sid in ln["series"]}
        pts = [(d, _round(v)) for d, v in ln["points"](T, start)]
        while pts and pts[0][1] is None:                     # 계산이 시작되기 전(기준치 없음)은 자른다
            pts.pop(0)
        if pts:
            lines.append({**{k: ln[k] for k in ("key", "label", "role", "series", "derived")},
                          "points": [[d.isoformat(), v] for d, v in pts]})
    if not lines or (spec["lines"][0]["role"] == "main" and lines[0]["key"] != spec["lines"][0]["key"]):
        return None
    return {**{k: spec[k] for k in ("key", "title", "unit", "years", "zero", "threshold", "note")},
            "source_note": source_note(spec, {l["key"] for l in lines}),
            "notices": rp.sofr_notices(asof.year) if spec["key"] in NOTICE_CHARTS else [], "lines": lines}


def _as_of(work):
    path = os.path.join(work, "raw", "latest.json")
    if not os.path.exists(path):
        raise RuntimeError("raw/latest.json 없음 — regime_check.py를 먼저 실행할 것")
    with open(path, encoding="utf-8") as f:
        return datetime.date.fromisoformat(json.load(f)["date"])


def load_series(cache_dir, sids, asof):
    """원자료 캐시(오프라인)에서 asof 이하만. 없거나 읽을 수 없으면 None."""
    S = {}
    for sid in sorted(sids):
        try:
            s = [x for x in ff.load(sid, cache_dir, offline=True)[0] if x[0] <= asof]
        except Exception:                                    # 한 시리즈 실패가 나머지 그래프를 막지 않게
            s = []
        S[sid] = s or None
    return S


def build(work):
    """(그래프 자료 dict, 빠진 그래프 key 목록)."""
    asof = _as_of(work)
    table = chart_table()
    specs = table["overview"] + list(table["rules"].values())
    S = load_series(os.path.join(work, "fred"), {sid for sp in specs for ln in sp["lines"] for sid in ln["series"]},
                    asof)
    out = {"schema": SCHEMA, "date": asof.isoformat(),
           "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "attribution": rp.attribution(asof.year),      # 파일만 받아 가도 출처·고지가 따라가게
           "overview": [], "rules": {}}
    skipped = []
    for spec in table["overview"]:
        ch = _render_chart(spec, S, asof)
        if ch:
            out["overview"].append(ch)
        else:
            skipped.append(spec["key"])
    for key, spec in table["rules"].items():
        ch = _render_chart(spec, S, asof)
        if ch:
            out["rules"][key] = ch
        else:
            skipped.append(key)
    return out, skipped


def _charts_date(out):
    try:
        with open(os.path.join(out, "charts.json"), encoding="utf-8") as f:
            return json.load(f).get("date")
    except (OSError, ValueError, AttributeError):
        return None


def write(out, charts):
    """charts.json을 원자적으로 쓴다. 기존 것이 더 최근 날짜면 쓰지 않고 False."""
    prev = _charts_date(out)
    if prev is not None and charts["date"] < prev:
        return False
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "charts.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(charts, ensure_ascii=False, separators=(",", ":")))
    os.replace(tmp, path)
    return True


def main():
    ap = argparse.ArgumentParser(description="원자료(<work>/fred) → 사이트 그래프 자료(<out>/charts.json)")
    ap.add_argument("--work", default=DEFAULT_WORK, help="작업 폴더 (기본: 저장소의 .work/)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    a = ap.parse_args()
    try:
        charts, skipped = build(os.path.abspath(a.work))
        if not charts["overview"] and not charts["rules"]:     # 빈 자료로 어제 그래프를 지우지 않는다
            raise RuntimeError("그래프를 하나도 만들지 못함 — 원자료 캐시(<work>/fred) 확인")
        wrote = write(os.path.abspath(a.out), charts)
    except (RuntimeError, ValueError, KeyError, OSError) as e:
        print(f"[render_charts] {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
    # 공개 저장소의 Actions 로그에 남는다 — 날짜·개수·빠진 그래프 key만 찍고 값은 찍지 않는다
    print(f"[render_charts] {charts['date']} 그래프 — 큰 그래프 {len(charts['overview'])}개 · "
          f"규칙 그래프 {len(charts['rules'])}개"
          + (f" · 빠짐 {', '.join(skipped)}" if skipped else "")
          + ("" if wrote else " · 더 최근 그래프 자료가 있어 쓰지 않음"))


if __name__ == "__main__":
    main()
