#!/usr/bin/env python3
"""참고 자료 — 미 국채 수급 두 지표 (2026-10-14 추가, 사용자 결정).

'10년 기간 프리미엄' 카드의 흐름도에서 TFP(기간 자금 보상)로 가는 요인 가운데 둘의 실제 숫자다. 규칙이 아니다 —
충족·판정이 없고, 판정·공개본·그래프 스크립트는 이 파일(<out>/supply.json)을 읽지 않는다.
  딜러  뉴욕 연은 프라이머리 딜러 통계의 국채(TIPS 제외) 순포지션 합계 PDPOSGST-TOT — 주간(수요일 관측), 백만 달러
  수탁  뉴욕 연은이 해외 공적·국제 기관을 위해 보관하는 시장성 국채 — FRED WMTSECL1(연준 H.4.1), 주간(수요일), 백만 달러
계산(쪽마다, 십억 달러): 수준 · 4주·52주 변화(28·364일 전 이하 최근 관측 대비, fred_fetch.change_days — 4주는 그 관측이
28일 전에서 6일 넘게 멀면 비운다, 분위수 표본과 같은 기준) · 표본 시작(2019년, 자료가 늦게 시작하면 첫 관측 28일 뒤 —
q4w.from, 문구에 그 해를 적는다) 이후 4주 변화 분포의 p5·p50·p95(28일 전 관측이 6일 넘게 멀면 그 변화는 세지 않는다,
선형 보간) · 마지막 4주 변화가 p95 위/p5 아래면 그렇다는 ⚠ 줄(4주 변화가 20개 미만이면 붙이지 않는다 — 줄 끝에 비공개 월간
점검 [수급 구조]의 구절을 그대로, 2026-10-30 사용자 결정: '재고 급증(조달 압박·TFP 상승 쪽)' 등. 참고이고 예측 아님) ·
최근 5년 주간 그래프.
문구로 가는 숫자는 소수 셋째 자리로 두고 문구에서 한 번만 반올림한다(그래프 점만 소수 첫째 자리).
딜러는 2022년 말(그 이하 마지막 관측) 이후 변화와, 거기에 Dallas Fed WP 2613 표 2의 TFP 계수(0.038bp/십억 달러)를 곱한
산술 참고값도 — 원본 파이프라인 월간 점검의 [수급 구조]와 같은 계산이다(코드는 가져오지 않고 여기서 따로 쓴다).

뉴욕 연은 단일 시계열 주소(/api/pd/get/PDPOSGST-TOT.json)의 응답 형식은 이 저장소에서 확인하지 못했다 — 너그럽게 읽는다:
아무 깊이의 dict 가운데 날짜 필드(asofdate·asOfDate·date …)와 value 필드가 함께 있는 것만 관측으로 보고, 키 필드(keyid …)가
있으면 PDPOSGST-TOT만(바깥 dict의 키·시리즈 구분을 물려받는다), '*'(기밀)·숫자가 아닌 값은 버리며, 같은 날이 여러 시리즈
구분(series break)에 있으면 가장 새 구분(이름 끝 숫자가 큰 것)의 값. 수준의 중앙값이 그럴듯한 범위(PLAUSIBLE) 밖이면 단위를
잘못 읽은 것으로 보고 닫힌 쪽으로 실패한다.

실패: 한쪽이 실패해도 다른 쪽은 갱신한다. 실패한 쪽은 직전 파일의 값을 '받지 못함(stale)'과 그날부터라는 날짜와 함께 이어
싣고(직전 값이 없으면 오류 문구만), 받은 자료가 직전 것보다 오래된 날짜면 받지 않는다. 온라인에서 FRED가 캐시로 대신한 것도
실패로 센다(묵은 캐시를 오늘 받은 것처럼 싣지 않게). 직전 파일이 깨져 있거나 값의 꼴이 어긋나면(숫자 자리의 글자,
'YYYY-MM-DD'가 아닌 날짜, 정해 둔 것 밖의 표시 등) 이어 실을 값이 없는 것으로 본다 — 값은 매번
원자료 전체로 다시 계산하므로 잃는 것이 없다. 같은 내용이면(생성 시각만 다르면) 파일을 다시 쓰지 않는다.
문구는 이 파일에 정해 둔 것뿐이다(오류 원문·주소·예외 문자열은 공개 파일에 싣지 않는다 — Actions 로그에는 예외 이름만).
출처 표기: 딜러 쪽은 뉴욕 연은 이용약관의 기본 출처 형식과 관계없음 고지(render_public — SOFR과 같은 원칙, Conditions 2·4),
수탁 쪽은 FRED 권장 인용 형식. FRED 시리즈 제목(FRED_TITLE)과 뉴욕 연은 통계 쪽 주소(PD_PAGE)는 이 환경에서 확인하지 못했다.

종료코드: 0 한쪽이라도 이번에 받음 / 1 둘 다 못 받음(또는 파일을 쓰지 못함). 워크플로 단계는 continue-on-error이고 알림도
띄우지 않는다(.github/workflows/daily.yml 머리말). 그래서 한쪽만 못 받은 날은 단계가 성공으로 끝난다 — 실패는 못 받은 쪽마다
표준 출력에 찍는 GitHub Actions 경고 주석(::warning::, 정해 둔 사유와 관측일만)이 실행 요약에 남는 것과, 페이지의 그 쪽
표시('받지 못함'(그날부터)과 직전 관측일, 직전 값이 없으면 '자료 없음')로 본다. 단계가 빨갛게 표시되는 것은 둘 다 못 받았거나
파일을 쓰지 못한 날뿐이다.

산출: <out>/supply.json (압축 JSON)
사용법: python supply_fetch.py [--out data] [--work .work] [--offline]
  캐시: <work>/supply/ — 받은 원문(딜러 JSON · WMTSECL1.csv). --offline이면 요청 없이 이 캐시만 읽는다(로컬 확인용).
"""
import os, sys, re, json, time, bisect, argparse, datetime, statistics, urllib.request, urllib.parse

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import fred_fetch as ff
import render_public as rp

SCHEMA = 1
REPO = os.path.dirname(SCRIPTS)
DEFAULT_OUT = os.path.join(REPO, "data")
DEFAULT_WORK = os.path.join(REPO, ".work")
FILE = "supply.json"

PD_KEY = "PDPOSGST-TOT"
PD_HOST = "markets.newyorkfed.org"
PD_URL = f"https://{PD_HOST}/api/pd/get/{PD_KEY}.json"
PD_PAGE = "https://www.newyorkfed.org/markets/counterparties/primary-dealers-statistics"   # 미확인(이 환경에서 접속 불가)
PD_CACHE = f"pd_{PD_KEY}.json"
FRED_ID = "WMTSECL1"
# FRED 권장 인용의 출처·제목 — 제목은 2026-10-14 이 환경에서 FRED에 접속하지 못해 확인하지 못했다(첫 실행 뒤 시리즈 쪽과 대조)
FRED_SOURCE = "Board of Governors of the Federal Reserve System (US)"
FRED_TITLE = "Memorandum Items: Custody Holdings: Marketable U.S. Treasury Securities: Wednesday Level"

TIMEOUT = 20                      # 요청 하나(연결·수신 한 번)
BUDGET = 30                       # 딜러 응답 하나를 받는 데 쓰는 전체 시간 상한(초) — 조금씩 흘려보내는 응답에 묶이지 않게
MAX_BYTES = 5_000_000
SINCE = datetime.date(2019, 1, 1)           # 4주 변화 분위수 표본 시작(논문 표본 시작 — 원본 파이프라인과 같다)
END_2022 = datetime.date(2022, 12, 31)
CHANGE_DAYS = 28                            # 4주
YEAR_DAYS = 364                             # 52주
STEP_TOL_DAYS = 6                           # 분위수 표본: 28일 전 관측이 이보다 멀면(자료 공백) 그 변화는 세지 않는다
MIN_Q = 20                                  # 4주 변화가 이보다 적으면 p5/p95 밖 표시를 붙이지 않는다
YEARS = 5                                   # 그래프 기간
PAPER_TFP = 0.038                           # Dallas Fed WP 2613(2026) 표 2 — TFP의 딜러 보유 계수(bp / 십억 달러, 1% 유의)
NUM_ND = 3                                  # 문구로 가는 숫자의 소수 자리 — 소수 첫째 자리로 두면 문구(정수)에서 두 번 반올림된다

NOTICE = ("이 사이트의 규칙 판정에 쓰지 않는 참고 자료다. 충족·미충족이 없고, 값의 크기나 방향을 시장 전망으로 읽지 않는다. "
          "⚠ 줄 끝의 구절은 운영자가 개인 월간 점검에 적어 둔 메모를 옮긴 참고이고 예측이 아니다.")
PD_DERIVED = ("수준은 뉴욕 연은 프라이머리 딜러 통계(PDPOSGST-TOT, 백만 달러)를 십억 달러로 바꾼 값이고, 4주·52주 변화와 "
              "분위수, 2022년 말 이후 변화와 논문 계수 대입 참고값은 macro-regime-check가 계산한 값이다. 뉴욕 연은이 발표한 "
              "값이 아니다.")
PD_DERIVED_EN = ("Changes, quantiles and the paper-coefficient figure are computed by macro-regime-check from the "
                 "New York Fed Primary Dealer Statistics (series PDPOSGST-TOT); they are not published by the New York Fed.")
CUSTODY_DERIVED = ("수준은 FRED의 WMTSECL1(연준 H.4.1, 백만 달러)을 십억 달러로 바꾼 값이고, 4주·52주 변화와 분위수는 "
                   "macro-regime-check가 계산한 값이다.")

# 쪽마다 정해 둔 것 — 이름·그래프 문구·단위 검사 범위(십억 달러, 수준의 |중앙값|)
SIDES = {
    "dealer": {"name": "딜러 국채 순포지션(TIPS 제외)", "series": PD_KEY, "zero": True, "plausible": (5.0, 3000.0),
               "title": "딜러 국채 순포지션(TIPS 제외)",
               "source_note": f"자료: Federal Reserve Bank of New York, Primary Dealer Statistics ({PD_KEY}) · "
                              "백만 달러를 십억 달러로 바꾼 값"},
    "custody": {"name": "해외 공적 수탁 국채(뉴욕 연은 보관)", "series": FRED_ID, "zero": False,
                "plausible": (100.0, 10000.0), "title": "해외 공적 수탁 국채",
                "source_note": f"자료: {FRED_SOURCE}, H.4.1 (via FRED, {FRED_ID}) · 백만 달러를 십억 달러로 바꾼 값"},
}
CHART_NOTE = "최근 5년 · 주간(수요일 관측) · 십억 달러"
# 4주 변화가 p5/p95 밖일 때의 ⚠ 줄(2026-10-30 사용자 결정 — 비공개 월간 점검 [수급 구조]의 문구 그대로, tp_drivers._flag_line)
FLAG_NAME = {"dealer": "딜러", "custody": "해외 공적 수탁"}
FLAG_READING = {("dealer", "high"): "재고 급증(조달 압박·TFP 상승 쪽)", ("dealer", "low"): "재고 급감",
                ("custody", "high"): "수탁 급증",
                ("custody", "low"): "수탁 급감(매도 또는 민간 수탁 이전 — 단정하지 않음)"}
LABEL = {"dealer": "딜러", "custody": "수탁"}           # Actions 로그용(값은 찍지 않는다)
REASONS = {                                            # 페이지·파일에 나가는 실패 문구는 이것뿐
    "fetch": "수신 실패",
    "format": "형식이 다름(읽은 관측 없음)",
    "unit": "단위가 맞지 않음(값의 크기가 범위 밖)",
    "older": "받은 자료가 직전 자료보다 오래됨",
    "cache": "수신 실패(묵은 캐시는 싣지 않음)",
}


class SideError(Exception):
    """한쪽의 실패 — code는 REASONS의 키."""
    def __init__(self, code):
        super().__init__(code)
        self.code = code


# ---------- 딜러: 수신 · 해석 ----------

def fetch_text(url, opener=None, clock=time.monotonic):
    """한 번 받는다. 다른 곳으로 넘겨지면(리디렉션) 실패, 전체 BUDGET초·MAX_BYTES를 넘기면 그만둔다."""
    start, chunks, size = clock(), [], 0
    with (opener or urllib.request.urlopen)(url, timeout=TIMEOUT) as r:
        final = urllib.parse.urlsplit(r.geturl())
        if (final.scheme, final.netloc) != ("https", PD_HOST):
            raise SideError("fetch")
        while True:
            if clock() - start > BUDGET:
                raise SideError("fetch")
            chunk = r.read1(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES:
                raise SideError("fetch")
            chunks.append(chunk)
    return b"".join(chunks).decode("utf-8", "replace")


DATE_NAMES = ("asofdate", "date")                      # 필드 이름은 소문자·영숫자만 남겨 견준다(asOfDate·as_of_date → asofdate)
VALUE_NAMES = ("value",)
KEY_NAMES = ("keyid", "key", "seriesid", "timeseries", "series")
BREAK_NAMES = ("seriesbreak", "break")


def _norm(name):
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def _field(d, names, kinds):
    """d에서 이름이 names 차례로 맞고 값이 kinds 꼴인 첫 필드의 값. 없으면 None."""
    by = {}
    for k, v in d.items():
        by.setdefault(_norm(k), v)
    for n in names:
        v = by.get(n)
        if isinstance(v, kinds) and not isinstance(v, bool):
            return v
    return None


def _date(s):
    s = str(s).strip()
    try:
        return datetime.date.fromisoformat(s[:10])
    except ValueError:
        pass
    for fmt in ("%m/%d/%Y", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _num(v):
    """숫자 또는 숫자 글자('1,234' · '-5') → float. '*'(기밀)·빈 값·숫자가 아닌 것·무한은 None."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        x = float(v)
    else:
        s = str(v).strip().replace(",", "")
        if not re.fullmatch(r"-?\d+(?:\.\d+)?", s):
            return None
        x = float(s)
    return x if x == x and abs(x) != float("inf") else None


def _walk(node, ctx, out):
    """JSON → [(date, 키, 시리즈 구분, 백만 달러)]. 키·구분은 바깥 dict에서 물려받는다({keyid, data: [{date, value}]} 꼴)."""
    if isinstance(node, list):
        for v in node:
            _walk(v, ctx, out)
        return
    if not isinstance(node, dict):
        return
    ctx = dict(ctx)
    key = _field(node, KEY_NAMES, (str,))
    if key and key.strip():
        ctx["key"] = key.strip()
    sb = _field(node, BREAK_NAMES, (str,))
    if sb and sb.strip():
        ctx["sb"] = sb.strip()
    d, v = _field(node, DATE_NAMES, (str,)), _field(node, VALUE_NAMES, (str, int, float))
    if d is not None and v is not None:
        dd, vv = _date(d), _num(v)
        if dd is not None and vv is not None:
            out.append((dd, ctx.get("key", PD_KEY), ctx.get("sb"), vv))
    for v in node.values():
        if isinstance(v, (dict, list)):
            _walk(v, ctx, out)


def _sb_rank(sb):
    """시리즈 구분의 새 정도 — 이름 끝 숫자(SBN2022 < SBN2024). 구분이 없으면 가장 낮다."""
    if sb is None:
        return (-1, "")
    nums = re.findall(r"\d+", sb)
    return (int(nums[-1]) if nums else 0, sb)


def parse_pd(text, today=None):
    """딜러 단일 시계열 응답 → [(date, 십억 달러)] 날짜순. 키 필드가 있는 기록은 PD_KEY만(없으면 주소가 정한 키로 본다).
    같은 날은 가장 새 시리즈 구분의 값(같은 구분이면 뒤의 것). today 뒤 날짜는 버린다. JSON이 아니면 빈 목록."""
    s = (text or "").lstrip("﻿").lstrip()
    if s[:1] not in ("{", "["):
        return []
    try:
        obj = json.loads(s)
    except ValueError:
        return []
    recs = []
    _walk(obj, {}, recs)
    best = {}
    for d, key, sb, v in recs:
        if key.upper() != PD_KEY or (today is not None and d > today):
            continue
        if d not in best or _sb_rank(sb) >= _sb_rank(best[d][0]):
            best[d] = (sb, v)
    return [(d, best[d][1] / 1000) for d in sorted(best)]


def _atomic_write(path, text):
    """같은 폴더의 임시 파일을 다 쓴 뒤 바꿔 넣는다. 실패하면 임시 파일을 지우고 예외를 그대로 — data/에 .tmp가 남아
    봇 커밋(git add data)에 실리지 않게."""
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _write_cache(path, text):
    """받은 원문을 캐시에(--offline용). 못 써도 그쪽 갱신은 그대로 — 캐시는 덤이다."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        _atomic_write(path, text)
    except OSError:
        pass


def load_dealer(work, today, offline=False, opener=None):
    """[(date, 십억 달러)]. 온라인이면 받아서(읽히면 캐시에 쓴다), --offline이면 캐시만. 실패는 SideError."""
    path = os.path.join(work, "supply", PD_CACHE)
    if offline:
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            raise SideError("fetch")
    else:
        try:
            text = fetch_text(PD_URL, opener)
        except SideError:
            raise
        except Exception:                       # 연결·HTTP·시간 초과 — 원문은 싣지 않는다
            raise SideError("fetch")
    series = parse_pd(text, today)
    if not series:
        raise SideError("format")
    if not offline:
        _write_cache(path, text)
    return series


def load_custody(work, today, offline=False, fred_load=None):
    """[(date, 십억 달러)] — fred_fetch.load(캐시 <work>/supply). 온라인에서 캐시로 대신한 것은 실패로 센다."""
    try:
        raw, src = (fred_load or ff.load)(FRED_ID, os.path.join(work, "supply"), offline=offline, timeout=TIMEOUT)
    except Exception:
        raise SideError("fetch")
    if src != "net" and not offline:
        raise SideError("cache")
    series = [(d, v / 1000) for d, v in raw if d <= today]
    if not series:
        raise SideError("format")
    return series


# ---------- 계산 ----------

def quantile(vals, q):
    """선형 보간 분위수(q는 0~1)."""
    s = sorted(vals)
    pos = (len(s) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def changes_over(series, since=SINCE, days=CHANGE_DAYS, tol=STEP_TOL_DAYS):
    """since 이후 관측마다 days일 전(이하 최근, tol일 안) 관측 대비 변화 — 분위수의 표본."""
    dates = [d for d, _ in series]
    out = []
    for d, v in series:
        if d < since:
            continue
        target = d - datetime.timedelta(days=days)
        i = bisect.bisect_right(dates, target) - 1
        if i >= 0 and (target - dates[i]).days <= tol:
            out.append(v - series[i][1])
    return out


def _r(v, nd=1):
    return None if v is None else round(v, nd) + 0.0          # + 0.0: -0.0을 0.0으로


def stats(kind, series, since=SINCE):
    """[(date, 십억 달러)] → 쪽의 숫자(JSON 꼴, 반올림) — 문구는 present()가 이 숫자로 만든다."""
    lo, hi = SIDES[kind]["plausible"]
    if not lo <= statistics.median(abs(v) for _, v in series) <= hi:
        raise SideError("unit")
    d1, v1 = series[-1]
    c4, c52 = ff.change_days(series, CHANGE_DAYS), ff.change_days(series, YEAR_DAYS)
    if c4 and (d1 - datetime.timedelta(days=CHANGE_DAYS) - c4["base_date"]).days > STEP_TOL_DAYS:
        c4 = None                       # 28일 전 관측이 멀면(자료 공백) 5~7주 변화를 '4주'로 싣지 않는다 — 분위수 표본과 같은 기준
    ch = changes_over(series, since)
    q = {"from": max(since, series[0][0] + datetime.timedelta(days=CHANGE_DAYS)).isoformat(), "n": len(ch),
         **{k: _r(quantile(ch, p), NUM_ND) if ch else None for k, p in (("p5", 0.05), ("p50", 0.5), ("p95", 0.95))}}
    flag = None
    if c4 and len(ch) >= MIN_Q:
        flag = "high" if c4["delta"] > quantile(ch, 0.95) else "low" if c4["delta"] < quantile(ch, 0.05) else None
    core = {"date": d1.isoformat(), "level_bn": _r(v1, NUM_ND),
            "chg_4w_bn": _r(c4 and c4["delta"], NUM_ND), "chg_4w_base": c4 and c4["base_date"].isoformat(),
            "chg_52w_bn": _r(c52 and c52["delta"], NUM_ND), "chg_52w_base": c52 and c52["base_date"].isoformat(),
            "q4w": q, "flag": flag, "since_2022": None,
            "points": [[d.isoformat(), _r(v)] for d, v in ff.weekly_last(series) if d >= ff.shift_year(d1, -YEARS)]}
    if kind == "dealer":
        base = ff.on_or_before(series, END_2022)
        if base:
            delta = v1 - base[1]
            core["since_2022"] = {"base_date": base[0].isoformat(), "base_bn": _r(base[1], NUM_ND),
                                  "delta_bn": _r(delta, NUM_ND), "paper_tfp_bp": _r(delta * PAPER_TFP)}
    return core


# ---------- 문구 · 산출물 ----------

def _signed(v):
    """정수로 반올림한 부호 붙은 수(천 단위 쉼표). 0은 부호 없이, 없으면 '—'."""
    if v is None:
        return "—"
    r = int(round(v))
    return "0" if r == 0 else f"{r:+,d}"


_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December")                 # 달 이름은 지역 설정(locale)에 기대지 않는다 — render_public과 같은 꼴


def citation(kind, retrieved):
    """FRED 권장 인용 형식(render_public.citation과 같은 꼴). 날짜는 지금 값을 처음 받은 날(retrieved)."""
    d = datetime.date.fromisoformat(retrieved)
    when = f"{_MONTHS[d.month - 1]} {d.day}, {d.year}"
    if kind == "custody":
        return (f"{FRED_SOURCE}, {FRED_TITLE} [{FRED_ID}], retrieved from FRED, Federal Reserve Bank of St. Louis; "
                f"{rp.FRED_URL.format(FRED_ID)}, {when}.")
    return (f"Federal Reserve Bank of New York, Primary Dealer Statistics, U.S. Treasury securities (excluding TIPS) "
            f"net positions [{PD_KEY}], retrieved from {PD_URL}, {when}.")


def source_of(kind, retrieved=None):
    if kind == "custody":
        src = {"name": f"{FRED_SOURCE} (H.4.1, via FRED)", "series": FRED_ID, "url": rp.FRED_URL.format(FRED_ID)}
    else:
        src = {"name": "Federal Reserve Bank of New York, Primary Dealer Statistics", "series": PD_KEY,
               "url": PD_PAGE, "api": PD_URL}
    if retrieved:
        src["citation"] = citation(kind, retrieved)
    return src


def notices(kind, year):
    if kind == "custody":
        return [CUSTODY_DERIVED]
    return [PD_DERIVED, PD_DERIVED_EN, rp.nyfed_attribution(year), rp.NOT_AFFILIATED]


def present(kind, core, retrieved):
    """숫자(core) → 쪽 전체(정해 둔 문구 · 그래프 · 고지 · 출처). 직전 파일에서 이어 실을 때도 이걸로 다시 만든다 —
    문구를 고치면 이어 실은 쪽에도 바로 반영된다."""
    spec, q = SIDES[kind], core["q4w"]
    year = q["from"][:4]
    line = f"{core['level_bn']:,.0f}bn · 4주 {_signed(core['chg_4w_bn'])}"
    if q["n"] >= MIN_Q:
        line += f" ({year}년 이후 p5 {_signed(q['p5'])} / p95 {_signed(q['p95'])})"
    line += f" · 52주 {_signed(core['chg_52w_bn'])}"
    flag_text = None
    if core["flag"] in ("high", "low"):
        hi = core["flag"] == "high"
        flag_text = (f"⚠ {FLAG_NAME[kind]} 4주 변화 {_signed(core['chg_4w_bn'])}bn이 {year}년 이후 "
                     + (f"p95({_signed(q['p95'])}) 위(상위 5%)" if hi else f"p5({_signed(q['p5'])}) 아래(하위 5%)")
                     + f" — {FLAG_READING[(kind, core['flag'])]}")
    extra = []
    s22 = core.get("since_2022")
    if s22:
        extra = [f"2022년 말 이후 {_signed(s22['delta_bn'])}bn (기준 {s22['base_date']} {s22['base_bn']:,.0f}bn)",
                 f"논문 계수 대입 참고값: {_signed(s22['delta_bn'])}bn × {PAPER_TFP:g}bp = 약 {s22['paper_tfp_bp']:+.1f}bp "
                 "(Dallas Fed WP 2613 표 2 — 딜러 보유 십억 달러당 TFP 계수, 2019~2025 월간 회귀). 계수를 곱한 산술일 뿐 "
                 "이 사이트의 추정이 아니고, 논문의 딜러 보유 자료와 정의가 다를 수 있으며, 판정에 쓰지 않음"]
    chart = {"key": f"supply_{kind}", "title": spec["title"], "unit": "bn", "years": YEARS, "zero": spec["zero"],
             "threshold": None, "note": CHART_NOTE, "source_note": spec["source_note"], "notices": [],
             "lines": [{"key": kind, "label": spec["title"], "role": "series", "series": [spec["series"]],
                        "derived": False, "points": core["points"]}]}
    return {"name": spec["name"], "series": spec["series"], **{k: v for k, v in core.items() if k != "points"},
            "retrieved": retrieved, "line": line, "flag_text": flag_text, "extra": extra, "chart": chart,
            "notices": notices(kind, int(retrieved[:4])), "source": source_of(kind, retrieved)}


def _is_day(v):
    """'YYYY-MM-DD' 꼴의 실제 날짜만 — fromisoformat이 받는 다른 꼴('2026-W40-3' 등)은 아니다."""
    try:
        return (isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) is not None
                and datetime.date.fromisoformat(v) is not None)
    except ValueError:
        return False


def _is_num(v, optional=False):
    return (optional and v is None) or (type(v) in (int, float) and v == v and abs(v) != float("inf"))


def core_of(side):
    """직전 파일의 쪽 → (숫자, 받은 날) 또는 None(없거나 형식이 어긋남 — 이어 실을 값이 없는 것으로 본다)."""
    try:
        q, s22 = side["q4w"], side.get("since_2022")
        pts = side["chart"]["lines"][0]["points"]
        ok = (_is_day(side["date"]) and _is_day(side["retrieved"]) and _is_num(side["level_bn"])
              and all(_is_num(side[k], True) for k in ("chg_4w_bn", "chg_52w_bn"))
              and all(side[k] is None or _is_day(side[k]) for k in ("chg_4w_base", "chg_52w_base"))
              and _is_day(q["from"]) and type(q["n"]) is int and all(_is_num(q[k], True) for k in ("p5", "p50", "p95"))
              and side["flag"] in (None, "high", "low")
              and (s22 is None or (_is_day(s22["base_date"]) and all(_is_num(s22[k]) for k in
                                                                     ("base_bn", "delta_bn", "paper_tfp_bp"))))
              and isinstance(pts, list) and all(isinstance(p, list) and len(p) == 2 and _is_day(p[0])
                                                and _is_num(p[1], True) for p in pts))
    except (KeyError, TypeError, IndexError, AttributeError):
        return None
    if not ok:
        return None
    core = {k: side[k] for k in ("date", "level_bn", "chg_4w_bn", "chg_4w_base", "chg_52w_bn", "chg_52w_base", "flag")}
    core.update(q4w={k: q[k] for k in ("from", "n", "p5", "p50", "p95")},
                since_2022=None if s22 is None else {k: s22[k] for k in ("base_date", "base_bn", "delta_bn",
                                                                       "paper_tfp_bp")},
                points=pts)
    return core, side["retrieved"]


def previous(out):
    """직전 supply.json → {쪽: 그 쪽 dict}. 없거나 못 읽으면 {}."""
    try:
        with open(os.path.join(out, FILE), encoding="utf-8") as f:
            js = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(js, dict) or js.get("schema") != SCHEMA:
        return {}
    return {k: js[k] for k in SIDES if isinstance(js.get(k), dict)}


def side_ok(kind, core, prev, today):
    """이번에 받은 쪽. 숫자가 직전과 같으면 받은 날(retrieved)을 그대로 둔다 — 같은 자료로 매일 파일을 바꾸지 않게."""
    old = core_of(prev) if prev else None
    if old and core["date"] < old[0]["date"]:
        raise SideError("older")
    retrieved = old[1] if old and old[0] == core else today.isoformat()
    return {"ok": True, "stale": False, "error": None, "failed_since": None, **present(kind, core, retrieved)}


def side_failed(kind, code, prev, today):
    """이번에 못 받은 쪽 — 직전 값이 있으면 '받지 못함'으로 이어 싣고, 못 받기 시작한 날을 지킨다."""
    since = prev.get("failed_since") if prev and _is_day(prev.get("failed_since")) else today.isoformat()
    old = core_of(prev) if prev else None
    if old:
        return {"ok": False, "stale": True, "error": REASONS[code], "failed_since": since, **present(kind, *old)}
    return {"ok": False, "stale": False, "error": REASONS[code], "failed_since": since, "name": SIDES[kind]["name"],
            "series": SIDES[kind]["series"], "source": source_of(kind)}


def build(results, prev, now):
    """results {쪽: core 또는 SideError} → 산출물 dict."""
    today = now.date()
    out = {"schema": SCHEMA, "generated_at": now.isoformat(timespec="seconds"), "notice": NOTICE}
    for kind in SIDES:
        r, p = results[kind], prev.get(kind)
        if not isinstance(r, SideError):
            try:
                out[kind] = side_ok(kind, r, p, today)
                continue
            except SideError as e:
                r = e
        out[kind] = side_failed(kind, r.code, p, today)
    return out


def differs(out, data):
    """저장 파일과 내용이 다른가(생성 시각은 빼고). 없거나 못 읽으면 다르다."""
    try:
        with open(os.path.join(out, FILE), encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        return True
    strip = lambda d: {k: v for k, v in d.items() if k != "generated_at"} if isinstance(d, dict) else d
    return strip(old) != strip(json.loads(json.dumps(data)))


def write(out, data):
    os.makedirs(out, exist_ok=True)
    _atomic_write(os.path.join(out, FILE), json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def annotate(text):
    """GitHub Actions 경고 주석 한 줄(표준 출력) — 단계가 성공으로 끝나도 실행 요약에 남는다. 명령 글자는 규약대로 바꾼다."""
    print("::warning::" + text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A"), flush=True)


def main(argv=None, opener=None, fred_load=None, now=None):
    ap = argparse.ArgumentParser(description="뉴욕 연은 딜러 순포지션 · FRED WMTSECL1 → 수급 참고 자료(<out>/supply.json)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    ap.add_argument("--work", default=DEFAULT_WORK, help="작업 폴더 — 원문 캐시는 <work>/supply/ (기본: 저장소의 .work/)")
    ap.add_argument("--offline", action="store_true", help="요청하지 않고 <work>/supply/의 캐시만 읽는다(로컬 확인용)")
    a = ap.parse_args(argv)
    out, work = os.path.abspath(a.out), os.path.abspath(a.work)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    loaders = {"dealer": lambda: load_dealer(work, today, a.offline, opener),
               "custody": lambda: load_custody(work, today, a.offline, fred_load)}
    results = {}
    for kind, load in loaders.items():
        try:
            results[kind] = stats(kind, load())
        except SideError as e:
            results[kind] = e
        except Exception as e:                  # 계산 쪽 뜻밖의 오류도 그쪽만 실패로
            print(f"[supply_fetch] {LABEL[kind]} 계산 오류: {type(e).__name__}", file=sys.stderr)
            results[kind] = SideError("format")
    data = build(results, previous(out), now)
    # 공개 저장소의 Actions 로그에 남는다 — 날짜와 정해 둔 사유만 찍고 값은 찍지 않는다. 못 받은 쪽은 경고 주석으로
    # (한쪽만 못 받으면 종료코드 0이라 단계가 초록으로 끝난다 — 주석이 없으면 실행 요약에 흔적이 없다)
    for kind in SIDES:
        s = data[kind]
        if s["ok"]:
            print(f"[supply_fetch] {LABEL[kind]} {s['date']} 관측까지")
        else:
            kept = f" — 직전 값({s['date']} 관측) 유지" if s["stale"] else ""
            annotate(f"수급 참고 {LABEL[kind]} 받지 못함: {s['error']}{kept}")
    try:
        if differs(out, data):
            write(out, data)
    except OSError as e:
        print(f"[supply_fetch] {FILE}를 쓰지 못함: {type(e).__name__}", file=sys.stderr)
        return 1
    return 0 if any(data[k]["ok"] for k in SIDES) else 1


if __name__ == "__main__":
    sys.exit(main())
