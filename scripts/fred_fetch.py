#!/usr/bin/env python3
"""FRED 시계열 무키 수신·캐시 + 시계열 산술 (stdlib only).

수신: https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>  (API 키 불필요)
캐시: <cache_dir>/<ID>.csv — 네트워크 실패 시 캐시로 폴백하고, 성공하면 캐시를 덮어쓴다.
시계열 표현: [(datetime.date, float), ...] 오름차순. 결측('.')은 파싱 단계에서 버린다.

산술 함수는 전부 순수 함수이며 마지막 관측치를 기준으로 계산한다(테스트는 test_regime.py).
"""
import os, io, csv, math, datetime, urllib.request

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
TIMEOUT = 15
YOY_TOLERANCE_DAYS = 45      # 1년 전 기준치가 이보다 멀면 YoY로 치지 않는다


# ---------- 수신·캐시 ----------

def urlopen_text(url, timeout=TIMEOUT):
    # 커스텀 User-Agent를 붙이면 FRED가 응답을 멈춘다(2026-09-22 read timeout 확인) — 기본 헤더 그대로 쓴다
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_csv(text):
    """FRED CSV(헤더 1행, 'YYYY-MM-DD,value') → [(date, float)]. 값이 '.'이면 건너뛴다."""
    out = []
    for i, row in enumerate(csv.reader(io.StringIO(text))):
        if i == 0 or len(row) < 2:
            continue
        try:
            out.append((datetime.date.fromisoformat(row[0].strip()), float(row[1])))
        except ValueError:
            continue
    return out


def cache_path(cache_dir, sid):
    return os.path.join(cache_dir, f"{sid}.csv")


def load(sid, cache_dir, offline=False, timeout=TIMEOUT):
    """(series, source). source는 'net' 또는 'cache'. 둘 다 안 되면 RuntimeError."""
    os.makedirs(cache_dir, exist_ok=True)
    cp = cache_path(cache_dir, sid)
    err = "offline"
    if not offline:
        try:
            text = urlopen_text(FRED_CSV.format(sid=sid), timeout)
            series = parse_csv(text)
            if series:
                tmp = cp + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(text)
                os.replace(tmp, cp)
                return series, "net"
            err = "빈 응답"
        except Exception as e:          # 캐시 폴백 — 호출자가 source로 구분한다
            err = f"{type(e).__name__}: {e}"
    if os.path.exists(cp):
        with open(cp, encoding="utf-8") as f:
            series = parse_csv(f.read())
        if series:
            return series, "cache"
    raise RuntimeError(f"{sid}: 수신 실패({err}), 캐시 없음")


# ---------- 기본 조회 ----------

def last(series):
    return series[-1] if series else None


def on_or_before(series, d):
    """d 이하 가장 최근 관측치 (date, value). 없으면 None."""
    for dd, v in reversed(series):
        if dd <= d:
            return dd, v
    return None


def shift_year(d, years=-1):
    try:
        return d.replace(year=d.year + years)
    except ValueError:                  # 2월 29일
        return d.replace(year=d.year + years, day=28)


def freshness_days(series, today):
    return (today - series[-1][0]).days if series else None


# ---------- 변화율 ----------

def yoy(series, same_month=False):
    """마지막 관측치의 전년비(%). 1년 전 관측치가 45일 넘게 멀면 None.
    same_month=True(월간·분기 시리즈)면 기준치의 (년, 월)이 정확히 1년 전이어야 한다 —
    결측월(CPILFESL 2025-10 등)을 그 전 달로 대체해 13개월 변화를 YoY라고 내지 않는다."""
    if not series:
        return None
    d1, v1 = series[-1]
    target = shift_year(d1)
    base = on_or_before(series, target)
    if not base or base[1] == 0 or (target - base[0]).days > YOY_TOLERANCE_DAYS:
        return None
    if same_month and (base[0].year, base[0].month) != (target.year, target.month):
        return None
    return {"value": (v1 / base[1] - 1) * 100, "asof": d1, "base_date": base[0], "base_value": base[1]}


def change_days(series, days):
    """마지막 관측치 − days일 전(이하 최근) 관측치."""
    if not series:
        return None
    d1, v1 = series[-1]
    base = on_or_before(series, d1 - datetime.timedelta(days=days))
    if not base:
        return None
    return {"delta": v1 - base[1], "asof": d1, "base_date": base[0], "base_value": base[1]}


def pct_change_days(series, days):
    c = change_days(series, days)
    if not c or c["base_value"] == 0:
        return None
    return {"value": c["delta"] / c["base_value"] * 100, "asof": c["asof"], "base_date": c["base_date"]}


def step_excluded_yoy(series, step, base_days=364):
    """주간 증분 합으로 계산한 YoY(%). |증분| ≥ step인 주(재분류 계단)는 제외한다.
    보고서 00장 7절 #2의 규칙: 한 주에 +$40bn 이상 뛰면 그 주를 빼고 읽는다."""
    if not series:
        return None
    d1, v1 = series[-1]
    base = on_or_before(series, d1 - datetime.timedelta(days=base_days))
    if not base or base[1] == 0:
        return None
    prev, incl, excluded = base[1], 0.0, []
    for d, v in series:
        if not (base[0] < d <= d1):
            continue
        diff = v - prev
        if abs(diff) >= step:
            excluded.append((d, diff))
        else:
            incl += diff
        prev = v
    return {"value": incl / base[1] * 100, "raw_value": (v1 / base[1] - 1) * 100, "asof": d1,
            "base_date": base[0], "base_value": base[1], "excluded": excluded}


# ---------- 상관·분포 ----------

def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx == 0 or syy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(sxx * syy)


def align(a, b):
    """두 시계열의 공통 날짜만 [(date, va, vb)]."""
    bd = dict(b)
    return [(d, va, bd[d]) for d, va in a if d in bd]


def corr_summary(px, y, n=60):
    """px의 일간 수익률 × y의 일간 변화의 n일 롤링 상관(운영기준 7-2의 ρ60).
    반환: 마지막 상관값, 기준일, 창 시작일, 같은 부호가 이어진 영업일 수."""
    al = align(px, y)
    rets, difs, dates = [], [], []
    for (_, p0, y0), (d, p1, y1) in zip(al, al[1:]):
        if p0 == 0:
            continue
        rets.append(p1 / p0 - 1)
        difs.append(y1 - y0)
        dates.append(d)
    if len(rets) < n:
        return None
    vals = [(dates[end - 1], pearson(rets[end - n:end], difs[end - n:end]))
            for end in range(n, len(rets) + 1)]
    last_d, last_c = vals[-1]
    if last_c is None:
        return None
    run = 0
    for _, c in reversed(vals):
        if c is None or c == 0 or (c > 0) != (last_c > 0):
            break
        run += 1
    return {"value": last_c, "asof": last_d, "start": dates[len(rets) - n], "n": n,
            "run_days": run, "sign": "+" if last_c > 0 else ("-" if last_c < 0 else "0")}


def percentile(series, value, since=None):
    """value 이하인 관측치의 비율(0~1). since 이후만 센다."""
    vals = [v for d, v in series if since is None or d >= since]
    if not vals:
        return None
    return sum(1 for v in vals if v <= value) / len(vals)


def trailing_min(series, days):
    d1 = series[-1][0]
    vals = [v for d, v in series if d >= d1 - datetime.timedelta(days=days)]
    return min(vals) if vals else None


# ---------- 빈도 변환·결측 ----------

def _next_month(y, m):
    return (y + 1, 1) if m == 12 else (y, m + 1)


def missing_months(series):
    """월간 시계열에서 빠진 달 ['YYYY-MM', ...] (CPILFESL 2025-10 결측 같은 것)."""
    out = []
    for (d0, _), (d1, _) in zip(series, series[1:]):
        y, m = _next_month(d0.year, d0.month)
        while (y, m) < (d1.year, d1.month):
            out.append(f"{y:04d}-{m:02d}")
            y, m = _next_month(y, m)
    return out


def weekly_last(series, before=None):
    """ISO 주별 마지막 관측치 — 일간 시계열을 주간(금요일 기준)으로.
    before(보통 이번 주 월요일)를 주면 그 날 이후 관측치는 버려 미완성 주를 한 주로 세지 않는다."""
    out = {}
    for d, v in series:
        if before is not None and d >= before:
            continue
        out[d.isocalendar()[:2]] = (d, v)
    return [out[k] for k in sorted(out)]
