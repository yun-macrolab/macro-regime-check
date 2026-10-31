#!/usr/bin/env python3
"""참고 자료 — 유가·에너지 (2026-10-30 추가, 사용자 결정: 물가 묶음의 참고 카드 + 한국 시장의 Brent × 원/달러 한 줄.
같은 날 사용자 결정으로 운영자의 월간 점검에만 있던 줄 — 실질 WTI 분위·이번 달 평균·I4와 물가 꼬리표·상태별 실측 평균·
미국 공급 반응·두바이 × 원/달러 — 을 더했다. 산식은 그 점검과 같고, 저장소를 넘어 가져오지 않고 여기서 따로 쓴다).

공개 통계의 숫자와 산술(전년비·변화·기저 경로·나눔·분위)과 운영자가 고정해 둔 정의로 붙인 꼬리표·측정 기록만 싣는다.
규칙이 아니다 — 충족이 없고, 판정·공개본·그래프 스크립트는 이 파일(<out>/oil.json)을 읽지 않는다. 칸(ITEMS — 화면 차례):
  crude     Brent·WTI 현물(EIA, 일간) 수준 · 13주 변화(91일 전 이하 마지막 관측 대비) · 전년비(1년 전 같은 날 이하) ·
            실질 WTI 분위(WTI 월평균 ÷ 같은 달 CPI 전체 — CPI가 아직 없는 달은 3개월 안의 마지막 CPI로, 1986년 이후 달 가운데
            이 값 이하인 달의 비율)와 명목 분위. CPI를 받지 못하면 분위만 빠진다(OPTIONAL)
  base      최근 20영업일 평균이 그대로일 때 Brent 전년비의 이번 달과 앞 6개월(1년 전 같은 달 월평균 대비 — 기저 경로),
            그 경로에서 전년비가 이번 달보다 CLIFF_PP 넘게 낮아지는 첫 달(기저 절벽). 그래프 = 월평균 전년비 5년 + 그 경로
  products  미국 소매 휘발유·경유(EIA, 주간) 수준 · 13주 · 전년비 · 이번 달 평균(마지막 관측의 달) 대 지난달 평균
  cracks    3-2-1 정제 마진(뉴욕항 휘발유×2 + 초저유황 경유×1) ÷ 3 − WTI, 경유 − Brent(달러/배럴) — 마지막 값 · 20영업일
            평균 · 1년 전 20영업일 평균
  spread    Brent − WTI — 마지막 값 · 20영업일 평균 · 13주 전 20영업일 평균
  cpi       CPI 에너지 전년비, CPI 전체 − 근원 전년비(BLS 계절조정, 1년 전 같은 달이 있을 때만)
  i4        I4 = CPI 전체 3개월 연율 − 근원 3개월 연율(두 값이 있는 마지막 달)과 물가 꼬리표 둘 — '공급형(에너지)'(근원 PCE
            물가 상태가 P+이고 그 달 I4 ≥ SUPPLY_HC) · '에너지 하락'(그 달 I4 ≤ −SUPPLY_HC), 근원 PCE 마지막 달 기준. 물가 상태
            P는 운영자 측정 도구의 정의 그대로(띠 H_IN/H_OUT·LO_IN/LO_OUT × 모멘텀 MOM·MOM_DN — 고정 2026-10-14). 근원 PCE를
            받지 못하면 I4만(OPTIONAL)
  bei       5년 BEI(T5YIE) · 5년 뒤 5년(T5YIFR) · 둘의 차와 13주 변화(bp)
  state     유가 방향 상태 — 정해 둔 정의(STATE_DEF)로 적은 설명: Brent 월평균 3개월 로그 변화 > +10% 오름, < −10% 내림,
            그 밖 보합. 전년비 부호·기저 절벽(base의 달부터 — 달 초엔 상태의 달보다 한 달 늦어 그 달도 적는다)을 덧붙이고,
            줄 끝에 상태별 다음 3개월 CPI 에너지 평균(STATE_AVG — 운영자 측정 기록, 계산에 쓰지 않음)을 적는다.
            지난 석 달을 적은 것이고 유가·금리를 예측하지 않는다(문구에 적는다)
  supply    미국 공급 반응 — 석유·가스 시추 산업생산(계절조정 없음) 같은 달 전년비 · 석유·가스 추출 가동률과 1년 전(연준 G.17)
  korea     Brent × 원/달러(월평균끼리 곱, 달마다 둘 다 관측된 날 10일 이상) 전년비와 그 나눔(달러 유가 몫 + 환율 몫 —
            두 로그 변화의 비율로 나눠 합이 전년비와 같다). 화면은 한국 시장 화면의 한 줄(KOREA)
  dubai     두바이 × 원/달러(IMF 월간 가격 × 원/달러 월평균 — 관측 10일 이상) 전년비와 같은 나눔. 한국 시장 화면의 둘째 줄

자료 이용 조건(2026-10-30 시리즈 쪽 JSON-LD의 license에서 확인 — LICENCE): EIA·BLS·BEA·연준 시리즈는 'Public Domain:
Citation Requested', T5YIE·T5YIFR은 'Copyrighted: Citation Required'(공개 사이트에 이미 있는 T10YIE와 같은 표시 — 같은 방식으로
FRED 권장 인용을 함께 싣는다), POILDUBUSDM은 'Copyrighted: Citation Required'에 IMF 저작권 표시가 붙은 IMF 자료(FRED 권장
인용 + IMF 저작권 고지 + 원화 환산·나눔은 이 사이트의 계산값이라는 고지 — IMF_NOTICE). 그 밖의 조건(재배포 제한 등)이 붙은
시리즈는 이 파일에 넣지 않는다(테스트가 목록을 고정한다).

실패·이어 싣기·문구 원칙은 ai_invest_fetch와 같다: 칸마다 따로, 못 받은 칸은 직전 숫자를 '받지 못함'과 그날부터라는 날짜와
함께(직전 값이 없으면 사유만), 받은 자료가 직전보다 이르면 받지 않는다, 문구는 이 파일에 정해 둔 것뿐(오류 원문은 싣지 않는다),
같은 내용이면 다시 쓰지 않는다, 수신 전체 BUDGET초(응답을 읽는 동안에도 본다 — ai_invest_fetch.fetch_csv). 새로 더한 시리즈는
SERIES 끝이라 수신 시간이 모자라면 그쪽부터 빠진다.

종료코드: 0 한 칸이라도 이번에 받음 / 1 하나도 못 받음(또는 파일을 쓰지 못함). 워크플로 단계는 continue-on-error, 알림 없음.

사용법: python scripts/oil_fetch.py [--out data] [--work .work] [--offline]
"""
import os, sys, re, json, math, time, bisect, argparse, datetime, statistics

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import fred_fetch as ff
import render_public as rp
import ai_invest_fetch as ai                  # 수신(fetch_csv·load_series)·쓰기·월평균 산술을 그대로 쓴다

SCHEMA = 1
REPO = os.path.dirname(SCRIPTS)
DEFAULT_OUT = os.path.join(REPO, "data")
DEFAULT_WORK = os.path.join(REPO, ".work")
FILE = "oil.json"
CACHE = "oil"                                 # <work>/oil/<ID>.csv

BUDGET = 60                                   # 수신 전체(초) — 워크플로 단계 제한(2분) 안에서 끝나게
NUM_ND = 4
PT_ND = 2
MIN_DAYS = 10                                 # 월평균에 필요한 관측일 수
FLAT_N = 20                                   # 기저 경로의 '그대로' 가격 = 최근 20영업일 평균
AVG_N = 20                                    # 마진·스프레드의 평균 창(영업일)
STEP_DAYS = 91                                # 13주
TOL_DAYS = 7                                  # 견줄 관측이 목표 날짜보다 이만큼 넘게 이르면 비운다(휴일·주간 자료 여유)
PATH_MONTHS = 6
CLIFF_PP = 30.0                               # 기저 절벽: 이번 달보다 30%p 넘게 낮아지는 첫 달
STATE_PCT = 10.0                              # 상태: 3개월 로그 변화 ±10%
BASE_YEARS = 5
BBL = 42                                      # 갤런/배럴
REAL_SINCE = datetime.date(1986, 1, 1)        # 실질·명목 WTI 분위 표본(WTI 첫 관측 1986-01)
REAL_CPI_LAG = 3                              # 마지막 달에 CPI가 아직 없으면 이 달 수 안의 마지막 CPI로 나눈다
# 상태별 다음 3개월 CPI 에너지 로그 변화 평균(%) — 운영자 측정 기록(2026-10-30 고정, 상태 달 1990-01~2026-06 가운데 상태를
# 정할 수 있는 413달, CPI는 2026-09까지). 문구에만 쓰고 계산에 쓰지 않는다. 운영자 월간 점검의 같은 상수와 같아야 한다
STATE_AVG = {"up": 2.43, "flat": 0.81, "down": -1.16, "all": 0.83}
STATE_N = {"up": 117, "flat": 204, "down": 92}
STATE_FIXED = "2026-10-30"
# I4·물가 꼬리표 — 운영자 측정 도구의 정의 그대로(고정 2026-10-14). 비교는 소수 6자리 반올림 뒤
SUPPLY_HC = 1.0                               # 공급형(에너지): P+이고 I4 ≥ +1.0 · 에너지 하락: I4 ≤ −1.0
H_IN, H_OUT, LO_IN, LO_OUT = 3.1, 2.9, 2.6, 2.7   # 근원 PCE 전년비 3개월 평균의 띠(히스테리시스)
MOM, MOM_N = 0.5, 1                           # 가속: 6개월 연율 − 전년비 ≥ +0.5가 1개 발표
MOM_DN, MOM_DN_N = 0.3, 2                     # 둔화: ≤ −0.3이 2개 발표 연속
P_P, P_0, P_D, P_M, P_UNKNOWN = "P+", "P0", "Pd", "P−", "?"
P_GRID = {("H", "A"): P_P, ("H", "F"): P_P, ("H", "D"): P_D,
          ("M", "A"): P_P, ("M", "F"): P_0, ("M", "D"): P_M,
          ("Lo", "A"): P_0, ("Lo", "F"): P_M, ("Lo", "D"): P_M}
TAG_SUPPLY, TAG_DOWN = "공급형(에너지)", "에너지 하락"
TAGS = (TAG_SUPPLY, TAG_DOWN)

_EIA, _BLS, _BOARD = "U.S. Energy Information Administration", "U.S. Bureau of Labor Statistics", \
    "Board of Governors of the Federal Reserve System (US)"
_STL = "Federal Reserve Bank of St. Louis"
# FRED 권장 인용의 출처·제목(2026-10-30 시리즈 쪽 Suggested Citation 그대로)
SOURCES = {
    "DCOILBRENTEU": (_EIA, "Crude Oil Prices: Brent - Europe"),
    "DCOILWTICO": (_EIA, "Crude Oil Prices: West Texas Intermediate (WTI) - Cushing, Oklahoma"),
    "GASREGW": (_EIA, "US Regular All Formulations Gas Price"),
    "GASDESW": (_EIA, "US Diesel Sales Price"),
    "DGASNYH": (_EIA, "Conventional Gasoline Prices: New York Harbor, Regular"),
    "DDFUELNYH": (_EIA, "Ultra-Low-Sulfur No. 2 Diesel Fuel Prices: New York Harbor"),
    "CPIENGSL": (_BLS, "Consumer Price Index for All Urban Consumers: Energy in U.S. City Average"),
    "CPIAUCSL": (_BLS, "Consumer Price Index for All Urban Consumers: All Items in U.S. City Average"),
    "CPILFESL": (_BLS, "Consumer Price Index for All Urban Consumers: All Items Less Food and Energy in U.S. City Average"),
    "DEXKOUS": (_BOARD, "South Korean Won to U.S. Dollar Spot Exchange Rate"),
    "T5YIE": (_STL, "5-Year Breakeven Inflation Rate"),
    "T5YIFR": (_STL, "5-Year, 5-Year Forward Inflation Expectation Rate"),
    # 2026-10-30 더함(운영자 월간 점검에만 있던 줄) — 끝에 둬 수신 시간이 모자라면 이쪽부터 빠진다
    "PCEPILFE": ("U.S. Bureau of Economic Analysis",
                 "Personal Consumption Expenditures Excluding Food and Energy (Chain-Type Price Index)"),
    "IPN213111N": (_BOARD, "Industrial Production: Mining: Drilling Oil and Gas Wells (NAICS = 213111)"),
    "CAPUTLG211S": (_BOARD, "Capacity Utilization: Mining: Oil and Gas Extraction (NAICS = 211)"),
    "POILDUBUSDM": ("International Monetary Fund", "Global price of Dubai Crude"),
}
# 시리즈 쪽 JSON-LD의 license(2026-10-30 확인). 이 두 값 밖의 시리즈는 싣지 않는다
LICENCE = {sid: "public-domain" for sid in SOURCES}
LICENCE.update({"T5YIE": "citation-required", "T5YIFR": "citation-required", "POILDUBUSDM": "citation-required"})
SERIES = list(SOURCES)
KOREA = ("korea", "dubai")                    # 한국 시장 화면에 싣는 칸(카드에는 없다)

NOTICE = "이 사이트의 규칙 점검에 쓰지 않는 참고 자료다. 공개 통계로 계산한 산술이고, 유가나 금리를 예측하지 않는다."
COMPUTED_NOTICE = "변화·전년비·평균·마진·나눔은 macro-regime-check가 원자료로 계산한 값이다."
CITATION_NOTICE = ("T5YIE·T5YIFR은 FRED에서 'Copyrighted: Citation Required'로 표시된 세인트루이스 연은 자료라 "
                   "FRED 권장 인용을 함께 싣는다.")
IMF_NOTICE = ("두바이 원유 가격(POILDUBUSDM): Copyright © International Monetary Fund. IMF 1차 상품 가격 자료를 FRED에서 받아 "
              "FRED 권장 인용과 함께 싣는다. 원화 환산·전년비·나눔은 macro-regime-check의 계산값이다. IMF 이용 조건: "
              "www.imf.org/external/terms.htm")
SERIES_NOTICES = {"T5YIE": CITATION_NOTICE, "T5YIFR": CITATION_NOTICE, "POILDUBUSDM": IMF_NOTICE}
STATE_DEF = ("정의(고정): Brent 현물 월평균(관측 10일 이상인 달)의 이번 달 대 3개월 전 로그 변화가 +10%를 넘으면 '오름', "
             "−10%보다 낮으면 '내림', 그 사이면 '보합'이다. 전년비 부호는 1년 전 같은 달 월평균 대비, 기저 절벽은 "
             "'가격이 그대로일 때' 줄의 정의를 따른다. 상태·전년비는 관측 10일 이상인 마지막 달, 기저 절벽은 마지막 관측의 "
             "달부터 잰다 — 달 초에는 두 달이 다를 수 있어 줄에 둘 다 적는다.")
STATE_NAME = {"up": "오름", "flat": "보합", "down": "내림"}
REASONS = {
    "fetch": "수신 실패",
    "cache": "수신 실패 · 묵은 캐시는 싣지 않음",
    "format": "계산할 자료가 모자람",
    "older": "받은 자료가 직전 자료보다 오래됨",
}


class ItemError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


# ---------- 산술 ----------

_r = ai._r
_iso = ai._iso


def _dates(series):
    return [d for d, _ in series]


def at_or_before(series, target, tol=TOL_DAYS):
    """target 이하 마지막 관측 (날짜, 값) — 그 관측이 target보다 tol일 넘게 이르면 None."""
    i = bisect.bisect_right(_dates(series), target) - 1
    if i < 0 or (target - series[i][0]).days > tol:
        return None
    return series[i]


def pct(a, b):
    return None if a is None or b is None or b == 0 else (a / b - 1) * 100


def level_moves(series):
    """마지막 관측 → (날짜, 값, 13주 %, 전년비 %)."""
    d1, v1 = series[-1]
    b13, b1y = at_or_before(series, d1 - datetime.timedelta(days=STEP_DAYS)), at_or_before(series, ff.shift_year(d1))
    return d1, v1, pct(v1, b13 and b13[1]), pct(v1, b1y and b1y[1])


def combine(fn, *series):
    """여러 시계열의 공통 날짜에서 fn(값들) → [(날짜, 값)]."""
    maps = [dict(s) for s in series[1:]]
    return [(d, fn(v, *[m[d] for m in maps])) for d, v in series[0] if all(d in m for m in maps)]


def avg_ending(series, end, n=AVG_N):
    """end 이하 마지막 n개 관측의 평균(그 끝 관측이 end보다 TOL_DAYS 넘게 이르면, 또는 n개가 안 되면 None)."""
    i = bisect.bisect_right(_dates(series), end)
    if i < n or (end - series[i - 1][0]).days > TOL_DAYS:
        return None
    return statistics.fmean(v for _, v in series[i - n:i])


def _mkey(d):
    return d.year * 12 + d.month - 1


def _mday(mk):
    return datetime.date(mk // 12, mk % 12 + 1, 1)


def month_avgs(series):
    """{달 번호: 월평균} — 관측 MIN_DAYS일 이상인 달만(ai_invest_fetch.monthly_mean)."""
    return {_mkey(d): v for d, v in ai.monthly_mean(series, MIN_DAYS)}


def monthly_yoy_avg(avgs):
    """{달 번호: 월평균 전년비 %} — 1년 전 같은 달도 있을 때만."""
    return {m: pct(v, avgs[m - 12]) for m, v in avgs.items() if m - 12 in avgs}


def base_path(series):
    """가격이 그대로일 때(최근 FLAT_N 관측 평균)의 Brent 전년비 — 이번 달(마지막 관측의 달)과 앞 PATH_MONTHS개월.
    → (평균, 평균 창의 첫·끝 날짜, 이번 달 번호, [전년비 %(1년 전 같은 달 월평균이 없으면 None)], 절벽 달 번호 또는 None)."""
    if len(series) < FLAT_N:
        raise ItemError("format")
    win = series[-FLAT_N:]
    flat = statistics.fmean(v for _, v in win)
    avgs = month_avgs(series)
    m0 = _mkey(series[-1][0])
    path = [pct(flat, avgs.get(m0 + k - 12)) for k in range(PATH_MONTHS + 1)]
    cliff = None
    if path[0] is not None:
        for k in range(1, PATH_MONTHS + 1):
            if path[k] is not None and round(path[0] - path[k], 6) > CLIFF_PP:
                cliff = m0 + k
                break
    return flat, win[0][0], win[-1][0], m0, path, cliff


def state_of(d3):
    """3개월 로그 변화(%) → 'up'·'down'·'flat' (경계값은 보합 — 소수 6자리 반올림 뒤 비교)."""
    x = round(d3, 6)
    return "up" if x > STATE_PCT else "down" if x < -STATE_PCT else "flat"


def krw_split(b1, b0, k1, k0):
    """Brent 월평균 × 원/달러 월평균의 전년비(%)와 그 나눔(달러 유가 몫, 환율 몫 — %p, 합 = 전년비).
    두 로그 변화의 비율로 나눈다. 두 로그 변화가 서로 지워 합이 0이면 로그 변화 그대로(전년비도 0이다)."""
    lb, lk = math.log(b1 / b0), math.log(k1 / k0)
    y = (b1 * k1 / (b0 * k0) - 1) * 100
    tot = lb + lk
    if abs(tot) < 1e-12:
        return y, lb * 100, lk * 100
    return y, y * lb / tot, y * lk / tot


def month_to_date(series):
    """마지막 관측의 달 평균 대 지난달 평균 → (달 번호, 관측 수, 평균, 전월 대비 %). 지난달 관측이 없으면 None."""
    if not series:
        return None
    m = _mkey(series[-1][0])
    cur = [v for d, v in series if _mkey(d) == m]
    prev = [v for d, v in series if _mkey(d) == m - 1]
    if not prev:
        return None
    a, p = statistics.fmean(cur), statistics.fmean(prev)
    return m, len(cur), a, pct(a, p)


def share_le(vals, v):
    """vals 가운데 v 이하인 비율(%, 소수 한 자리) — 소수 6자리 반올림 뒤 견준다."""
    return None if not vals or v is None else _r(sum(1 for x in vals if round(x, 6) <= round(v, 6)) / len(vals) * 100, 1)


def real_wti(S):
    """실질 WTI 분위 — 월평균(관측 10일 이상, REAL_SINCE부터) ÷ 같은 달 CPI 전체. 마지막 달에 CPI가 아직 없으면
    REAL_CPI_LAG개월 안의 마지막 CPI로 나눈다. 분위 = 이 값 이하인 달의 비율(실질은 같은 CPI로 나눈 비율이라 기준 달러와
    무관). 명목 분위도 같은 달들로. CPI가 없거나 가까운 CPI가 없으면 None."""
    cpi = {_mkey(d): v for d, v in S.get("CPIAUCSL") or ()}
    avgs = {m: v for m, v in month_avgs(S["DCOILWTICO"]).items() if _mday(m) >= REAL_SINCE}
    if not cpi or not avgs:
        return None
    m = max(avgs)
    base = m if m in cpi else max((k for k in cpi if m - REAL_CPI_LAG <= k <= m), default=None)
    if base is None:
        return None
    real = {k: v / cpi[k] for k, v in avgs.items() if k in cpi}
    real[m] = avgs[m] / cpi[base]
    return {"wti_month": _iso(_mday(m)), "wti_avg": _r(avgs[m]), "real_pct": share_le(list(real.values()), real[m]),
            "nom_pct": share_le(list(avgs.values()), avgs[m]), "real_cpi_month": _iso(_mday(base)), "real_n": len(real)}


# ---------- 물가 상태 P와 꼬리표 — 운영자 측정 도구(infl_rows·pce_states·infl_tags)를 이 칸이 쓰는 만큼만 옮긴 것 ----------

def _ge(x, th):
    return x is not None and round(x, 6) >= round(th, 6)


def _le(x, th):
    return x is not None and round(x, 6) <= round(th, 6)


def _gt(x, th):
    return x is not None and round(x, 6) > round(th, 6)


def _lt(x, th):
    return x is not None and round(x, 6) < round(th, 6)


def ann_rate(m, key, k):
    """k개월 연율(%). m[key]와 m[key−k]가 둘 다 있을 때만 — 그 전 달로 대신하지 않는다."""
    v, b = m.get(key), m.get(key - k)
    if v is None or b is None or b <= 0 or v <= 0:
        return None
    return ((v / b) ** (12 / k) - 1) * 100


def infl_rows(series):
    """월간 지수 → {달 번호: {y12, a3, a6, Y3, mom}} — 지수가 있는 달마다. Y3 = 그 달까지 석 달 중 있는 전년비(2개 이상)의
    평균, mom = a6 − y12."""
    m = {_mkey(d): v for d, v in series}
    y = {t: v for t, v in ((t, ann_rate(m, t, 12)) for t in m) if v is not None}
    out = {}
    for t in sorted(m):
        vals = [y[k] for k in (t, t - 1, t - 2) if y.get(k) is not None]
        r = {"y12": y.get(t), "a3": ann_rate(m, t, 3), "a6": ann_rate(m, t, 6),
             "Y3": sum(vals) / len(vals) if len(vals) >= 2 else None}
        r["mom"] = None if r["a6"] is None or r["y12"] is None else r["a6"] - r["y12"]
        out[t] = r
    return out


def band_step(prev, y):
    """수준 띠(히스테리시스): H는 H_IN 초과로 들어가 H_OUT 미만에서 나온다, Lo는 LO_IN 미만으로 들어가 LO_OUT 초과에서 나온다."""
    if y is None:
        return None
    if prev == "H" and not _lt(y, H_OUT):
        return "H"
    if prev == "Lo" and not _gt(y, LO_OUT):
        return "Lo"
    if _gt(y, H_IN):
        return "H"
    if _lt(y, LO_IN):
        return "Lo"
    return "M"


def mom_class(seq):
    """seq = 모멘텀 열(마지막이 그 달). A: 마지막 MOM_N개가 모두 ≥ +MOM, D: 마지막 MOM_DN_N개가 모두 ≤ −MOM_DN, F: 그 밖.
    그 달 값이 없으면 None. 그 달이 한쪽 문턱을 넘었는데 앞 발표가 없어 가를 수 없으면 None."""
    seq = list(seq)
    cur = seq[-1] if seq else None
    if cur is None:
        return None
    for th, n, hit, label in ((MOM, MOM_N, lambda v, th: _ge(v, th), "A"), (MOM_DN, MOM_DN_N, lambda v, th: _le(v, -th), "D")):
        if hit(cur, th):
            need = seq[-n:]
            if len(need) < n or any(v is None for v in need):
                return None
            return label if all(hit(v, th) for v in need) else "F"
    return "F"


def pce_states(rows):
    """infl_rows(근원 PCE)에 band·mom_class·P를 더한다 — 띠는 처음 달부터 차례로(직전 상태를 넘긴다)."""
    months, state = sorted(rows), None
    moms = [rows[t]["mom"] for t in months]
    need = max(MOM_N, MOM_DN_N)
    for i, t in enumerate(months):
        b = band_step(state, rows[t]["Y3"])
        if b is not None:
            state = b
        rows[t]["band"] = b
        rows[t]["mom_class"] = mom_class(moms[max(0, i - need + 1):i + 1])
        rows[t]["P"] = P_GRID.get((b, rows[t]["mom_class"]), P_UNKNOWN)
    return rows


def energy_tags(S):
    """I4(CPI 전체 a3 − 근원 a3, 두 값이 있는 마지막 달)와 근원 PCE 마지막 달의 물가 상태·꼬리표.
    '공급형(에너지)': P+이고 그 달 I4 ≥ SUPPLY_HC · '에너지 하락': 그 달 I4 ≤ −SUPPLY_HC(P와 무관). 근원 PCE가 없으면 I4만."""
    h, c = infl_rows(S["CPIAUCSL"]), infl_rows(S["CPILFESL"])
    both = [t for t in sorted(set(h) & set(c)) if h[t]["a3"] is not None and c[t]["a3"] is not None]
    if not both:
        return None
    t = both[-1]
    out = {"i4": _r(h[t]["a3"] - c[t]["a3"]), "month": _iso(_mday(t)), "pce_month": None, "p": None, "tags": None,
           "hc_pce": None}
    if S.get("PCEPILFE"):
        pce = pce_states(infl_rows(S["PCEPILFE"]))
        tp = max(pce)
        ha, ca = h.get(tp, {}).get("a3"), c.get(tp, {}).get("a3")
        hc = None if ha is None or ca is None else ha - ca
        tags = []
        if pce[tp]["P"] == P_P and _ge(hc, SUPPLY_HC):
            tags.append(TAG_SUPPLY)
        if _le(hc, -SUPPLY_HC):
            tags.append(TAG_DOWN)
        out.update(pce_month=_iso(_mday(tp)), p=pce[tp]["P"], tags=tags, hc_pce=_r(hc))
    return out


def krw_months(price_months, fx):
    """{달 번호: 달러 가격} × 원/달러 월평균(관측 MIN_DAYS일 이상) → 그 달과 1년 전이 모두 있는 마지막 달의 전년비·나눔."""
    fxm = month_avgs(fx)
    ok = sorted(m for m in price_months if m in fxm and m - 12 in price_months and m - 12 in fxm)
    if not ok:
        raise ItemError("format")
    m = ok[-1]
    b1, b0, k1, k0 = price_months[m], price_months[m - 12], fxm[m], fxm[m - 12]
    y, dpp, fpp = krw_split(b1, b0, k1, k0)
    return m, {"month": _iso(_mday(m)), "krw": _r(b1 * k1 / 10000), "krw_1y": _r(b0 * k0 / 10000), "yoy": _r(y),
               "usd_pp": _r(dpp), "fx_pp": _r(fpp), "usd_yoy": _r(pct(b1, b0)), "fx_yoy": _r(pct(k1, k0))}


# ---------- 칸마다 계산 (S: {ID: [(date, value)]}) → core {date, values, lines} ----------

def calc_crude(S):
    b, w = S["DCOILBRENTEU"], S["DCOILWTICO"]
    bd, bv, b13, by = level_moves(b)
    wd, wv, w13, wy = level_moves(w)
    if by is None or wy is None:
        raise ItemError("format")
    vals = {"brent": _r(bv), "brent_date": _iso(bd), "brent_13w": _r(b13), "brent_yoy": _r(by),
            "wti": _r(wv), "wti_date": _iso(wd), "wti_13w": _r(w13), "wti_yoy": _r(wy)}
    vals.update(real_wti(S) or dict.fromkeys(REAL_KEYS))           # CPI를 받지 못하면 분위만 빈다
    return {"date": _iso(max(bd, wd)), "values": vals, "lines": {}}


def calc_base(S):
    b = S["DCOILBRENTEU"]
    flat, f0, f1, m0, path, cliff = base_path(b)
    if path[0] is None:
        raise ItemError("format")
    yoy = monthly_yoy_avg(month_avgs(b))
    start = _mkey(ff.shift_year(_mday(m0), -BASE_YEARS))
    hist = []
    if yoy:
        for m in range(max(start, min(yoy)), max(yoy) + 1):           # 빠진 달은 None으로 선을 끊는다
            hist.append([_iso(_mday(m)), _r(yoy[m], PT_ND) if yoy.get(m) is not None else None])
    vals = {"flat": _r(flat), "flat_from": _iso(f0), "flat_to": _iso(f1), "m0": _iso(_mday(m0)),
            "cliff": _iso(_mday(cliff)) if cliff is not None else None}
    vals.update({f"p{k}": _r(v) for k, v in enumerate(path)})
    return {"date": _iso(f1), "values": vals,
            "lines": {"yoy": hist, "path": [[_iso(_mday(m0 + k)), _r(v, PT_ND)] for k, v in enumerate(path)]}}


def calc_products(S):
    g, s = S["GASREGW"], S["GASDESW"]
    gd, gv, g13, gy = level_moves(g)
    dd, dv, d13, dy = level_moves(s)
    if gy is None or dy is None:
        raise ItemError("format")
    vals = {"gas": _r(gv), "gas_date": _iso(gd), "gas_13w": _r(g13), "gas_yoy": _r(gy),
            "diesel": _r(dv), "diesel_date": _iso(dd), "diesel_13w": _r(d13), "diesel_yoy": _r(dy)}
    for key, series in (("gas", g), ("diesel", s)):
        mt = month_to_date(series)
        vals.update({f"{key}_m": _iso(_mday(mt[0])) if mt else None, f"{key}_m_n": mt[1] if mt else None,
                     f"{key}_m_avg": _r(mt[2]) if mt else None, f"{key}_m_ch": _r(mt[3]) if mt else None})
    return {"date": _iso(max(gd, dd)), "values": vals, "lines": {}}


def crack_321(gas, ulsd, wti):
    """(휘발유×2 + 경유×1) ÷ 3 − WTI, 달러/배럴 — 휘발유·경유는 갤런당 달러 × 42."""
    return (2 * gas * BBL + ulsd * BBL) / 3 - wti


def _avg_pair(series):
    """마지막 값과 그 날까지 20영업일 평균, 1년 전 같은 날까지 20영업일 평균."""
    d1, v1 = series[-1]
    return d1, v1, avg_ending(series, d1), avg_ending(series, ff.shift_year(d1))


def calc_cracks(S):
    c = combine(crack_321, S["DGASNYH"], S["DDFUELNYH"], S["DCOILWTICO"])
    u = combine(lambda ul, br: ul * BBL - br, S["DDFUELNYH"], S["DCOILBRENTEU"])
    if not c or not u:
        raise ItemError("format")
    cd, cv, ca, c1 = _avg_pair(c)
    ud, uv, ua, u1 = _avg_pair(u)
    if ca is None or ua is None:
        raise ItemError("format")
    return {"date": _iso(cd),
            "values": {"c321": _r(cv), "c321_avg": _r(ca), "c321_avg_1y": _r(c1),
                       "ulsd": _r(uv), "ulsd_date": _iso(ud), "ulsd_avg": _r(ua), "ulsd_avg_1y": _r(u1)},
            "lines": {}}


def calc_spread(S):
    s = combine(lambda b, w: b - w, S["DCOILBRENTEU"], S["DCOILWTICO"])
    if not s:
        raise ItemError("format")
    d1, v1 = s[-1]
    a = avg_ending(s, d1)
    if a is None:
        raise ItemError("format")
    return {"date": _iso(d1),
            "values": {"last": _r(v1), "avg": _r(a),
                       "avg_13w": _r(avg_ending(s, d1 - datetime.timedelta(days=STEP_DAYS)))},
            "lines": {}}


def calc_cpi(S):
    e, h, c = (dict(ai.monthly_yoy(S[k])) for k in ("CPIENGSL", "CPIAUCSL", "CPILFESL"))
    both = sorted(set(h) & set(c))
    if not e or not both:
        raise ItemError("format")
    m = both[-1]
    em = max(e)
    return {"date": _iso(max(m, em)),
            "values": {"energy": _r(e[em]), "energy_month": _iso(em), "head": _r(h[m]), "core": _r(c[m]),
                       "month": _iso(m)},
            "lines": {}}


def calc_bei(S):
    a, f = S["T5YIE"], S["T5YIFR"]
    g = combine(lambda x, y: (x - y) * 100, a, f)
    if not g:
        raise ItemError("format")

    def bp13(series, scale=100):
        d1, v1 = series[-1]
        b = at_or_before(series, d1 - datetime.timedelta(days=STEP_DAYS))
        return None if b is None else (v1 - b[1]) * scale
    gd, gv = g[-1]
    return {"date": _iso(gd),
            "values": {"be5": _r(a[-1][1]), "be5_date": _iso(a[-1][0]), "be5_13w": _r(bp13(a)),
                       "fwd": _r(f[-1][1]), "fwd_date": _iso(f[-1][0]), "fwd_13w": _r(bp13(f)),
                       "gap": _r(gv), "gap_13w": _r(bp13(g, 1))},
            "lines": {}}


def calc_korea(S):
    """Brent × 원/달러 — 둘 다 관측된 날로 달마다 평균(MIN_DAYS일 이상), 그 평균끼리 곱한다."""
    kd = dict(S["DEXKOUS"])
    by = {}
    for d, v in S["DCOILBRENTEU"]:
        if d in kd:
            by.setdefault(_mkey(d), []).append((v, kd[d]))
    ok = {m: (statistics.fmean(x for x, _ in xs), statistics.fmean(y for _, y in xs), len(xs))
          for m, xs in by.items() if len(xs) >= MIN_DAYS}
    months = [m for m in sorted(ok) if m - 12 in ok]
    if not months:
        raise ItemError("format")
    m = months[-1]
    (b1, k1, n), (b0, k0, _) = ok[m], ok[m - 12]
    y, dpp, fpp = krw_split(b1, b0, k1, k0)
    return {"date": _iso(_mday(m)),
            "values": {"month": _iso(_mday(m)), "krw": _r(b1 * k1 / 10000), "krw_1y": _r(b0 * k0 / 10000),
                       "yoy": _r(y), "usd_pp": _r(dpp), "fx_pp": _r(fpp), "usd_yoy": _r(pct(b1, b0)),
                       "fx_yoy": _r(pct(k1, k0)), "days": n},
            "lines": {}}


def calc_i4(S):
    v = energy_tags(S)
    if v is None:
        raise ItemError("format")
    return {"date": max(d for d in (v["month"], v["pce_month"]) if d), "values": v, "lines": {}}


def calc_supply(S):
    """미국 공급 반응 — 시추 산업생산 같은 달 전년비(마지막 달), 추출 가동률 마지막 값과 1년 전 같은 달."""
    y = ai.monthly_yoy(S["IPN213111N"])
    cu = S["CAPUTLG211S"]
    if not y or not cu:
        raise ItemError("format")
    return {"date": _iso(max(y[-1][0], cu[-1][0])),
            "values": {"drill_month": _iso(y[-1][0]), "drill_yoy": _r(y[-1][1]), "util_month": _iso(cu[-1][0]),
                       "util": _r(cu[-1][1]), "util_1y": _r(ai._year_ago(cu))},
            "lines": {}}


def calc_dubai(S):
    """두바이 × 원/달러 — IMF 월간 가격 × 원/달러 월평균(관측 MIN_DAYS일 이상)의 전년비와 나눔(Brent 줄과 같은 나눔)."""
    m, vals = krw_months({_mkey(d): v for d, v in S["POILDUBUSDM"]}, S["DEXKOUS"])
    return {"date": _iso(_mday(m)), "values": vals, "lines": {}}


def calc_state(S):
    b = S["DCOILBRENTEU"]
    avgs = month_avgs(b)
    months = [m for m in sorted(avgs) if m - 3 in avgs]
    if not months:
        raise ItemError("format")
    m = months[-1]
    d3 = math.log(avgs[m] / avgs[m - 3]) * 100
    _, _, _, m0, _, cliff = base_path(b)                # 기저 경로의 달(마지막 관측의 달) — 달 초엔 상태의 달보다 늦다
    return {"date": _iso(_mday(m)),
            "values": {"month": _iso(_mday(m)), "d3": _r(d3), "state": state_of(d3),
                       "yoy": _r(pct(avgs[m], avgs.get(m - 12))), "path_month": _iso(_mday(m0)),
                       "cliff": _iso(_mday(cliff)) if cliff is not None else None},
            "lines": {}}


# ---------- 칸 정의 (차례 = 화면 차례, korea는 한국 시장 화면의 한 줄) ----------
# values: 이름 → 꼴("num" · "num?" · "day" · "day?" · "int" · "int?" · "state" · "pstate?" · "tags?") — 직전 파일 검사에도 쓴다
# ends: 시리즈마다의 끝 날짜(values의 날짜 칸) — 칸의 date와 함께 하나라도 직전보다 이르면 받지 않는다
# optional: 없어도 칸을 계산하는 시리즈 → 그 시리즈로 채우는 값 이름. 그 값이 있을 때만 출처에 싣는다

REAL_KEYS = ("wti_month", "wti_avg", "real_pct", "nom_pct", "real_cpi_month", "real_n")

def _l(key, label, role, series):
    return {"key": key, "label": label, "role": role, "series": series}


ITEMS = [
    {"key": "crude", "title": "원유 현물 (Brent · WTI)", "series": ["DCOILBRENTEU", "DCOILWTICO"], "calc": calc_crude,
     "optional": {"CPIAUCSL": "real_pct"},
     "values": {"brent": "num", "brent_date": "day", "brent_13w": "num?", "brent_yoy": "num", "wti": "num",
                "wti_date": "day", "wti_13w": "num?", "wti_yoy": "num", "wti_month": "day?", "wti_avg": "num?",
                "real_pct": "num?", "nom_pct": "num?", "real_cpi_month": "day?", "real_n": "int?"},
     "ends": ["brent_date", "wti_date"]},
    {"key": "base", "title": "Brent 전년비 — 가격이 그대로일 때의 앞 6개월", "series": ["DCOILBRENTEU"], "calc": calc_base,
     "values": {"flat": "num", "flat_from": "day", "flat_to": "day", "m0": "day", "cliff": "day?",
                **{f"p{k}": ("num" if k == 0 else "num?") for k in range(PATH_MONTHS + 1)}},
     "chart": {"unit": "%", "years": BASE_YEARS, "zero": True,
               "note": "최근 5년 · 월평균(관측 10일 이상)의 전년비 · 회색 선은 최근 20영업일 평균이 그대로일 때"},
     "lines": [_l("yoy", "Brent 월평균 전년비", "main", ["DCOILBRENTEU"]),
               _l("path", "가격이 그대로일 때", "ref", ["DCOILBRENTEU"])]},
    {"key": "products", "title": "미국 소매 휘발유·경유 (주간)", "series": ["GASREGW", "GASDESW"], "calc": calc_products,
     "values": {"gas": "num", "gas_date": "day", "gas_13w": "num?", "gas_yoy": "num", "diesel": "num",
                "diesel_date": "day", "diesel_13w": "num?", "diesel_yoy": "num",
                **{f"{k}_{x}": t for k in ("gas", "diesel") for x, t in (("m", "day?"), ("m_n", "int?"), ("m_avg", "num?"),
                                                                       ("m_ch", "num?"))}},
     "ends": ["gas_date", "diesel_date"]},
    {"key": "cracks", "title": "정제 마진 (3-2-1 · 경유 − Brent)", "series": ["DGASNYH", "DDFUELNYH", "DCOILWTICO", "DCOILBRENTEU"],
     "calc": calc_cracks,
     "values": {"c321": "num", "c321_avg": "num", "c321_avg_1y": "num?", "ulsd": "num", "ulsd_date": "day",
                "ulsd_avg": "num", "ulsd_avg_1y": "num?"}, "ends": ["ulsd_date"]},
    {"key": "spread", "title": "Brent − WTI", "series": ["DCOILBRENTEU", "DCOILWTICO"], "calc": calc_spread,
     "values": {"last": "num", "avg": "num", "avg_13w": "num?"}},
    {"key": "cpi", "title": "CPI 에너지 · 전체 − 근원", "series": ["CPIENGSL", "CPIAUCSL", "CPILFESL"], "calc": calc_cpi,
     "values": {"energy": "num", "energy_month": "day", "head": "num", "core": "num", "month": "day"},
     "ends": ["energy_month", "month"]},
    {"key": "i4", "title": "I4 · 물가 꼬리표 (운영자 정의)", "series": ["CPIAUCSL", "CPILFESL"], "calc": calc_i4,
     "optional": {"PCEPILFE": "pce_month"},
     "values": {"i4": "num", "month": "day", "pce_month": "day?", "p": "pstate?", "tags": "tags?", "hc_pce": "num?"},
     "ends": ["month", "pce_month"]},
    {"key": "bei", "title": "기대인플레이션 5년 · 5년 뒤 5년", "series": ["T5YIE", "T5YIFR"], "calc": calc_bei,
     "values": {"be5": "num", "be5_date": "day", "be5_13w": "num?", "fwd": "num", "fwd_date": "day", "fwd_13w": "num?",
                "gap": "num", "gap_13w": "num?"}, "ends": ["be5_date", "fwd_date"]},
    {"key": "state", "title": "유가 방향 상태 (정해 둔 정의로 적은 설명)", "series": ["DCOILBRENTEU"], "calc": calc_state,
     "values": {"month": "day", "d3": "num", "state": "state", "yoy": "num?", "path_month": "day", "cliff": "day?"}},
    {"key": "supply", "title": "미국 공급 반응 (시추 · 추출 가동률)", "series": ["IPN213111N", "CAPUTLG211S"],
     "calc": calc_supply,
     "values": {"drill_month": "day", "drill_yoy": "num", "util_month": "day", "util": "num", "util_1y": "num?"},
     "ends": ["drill_month", "util_month"]},
    {"key": "korea", "title": "Brent × 원/달러", "series": ["DCOILBRENTEU", "DEXKOUS"], "calc": calc_korea,
     "values": {"month": "day", "krw": "num", "krw_1y": "num", "yoy": "num", "usd_pp": "num", "fx_pp": "num",
                "usd_yoy": "num", "fx_yoy": "num", "days": "int"}},
    {"key": "dubai", "title": "두바이 × 원/달러", "series": ["POILDUBUSDM", "DEXKOUS"], "calc": calc_dubai,
     "values": {"month": "day", "krw": "num", "krw_1y": "num", "yoy": "num", "usd_pp": "num", "fx_pp": "num",
                "usd_yoy": "num", "fx_yoy": "num"}},
]
BY_KEY = {it["key"]: it for it in ITEMS}


# ---------- 문구 ----------

def _f(v, nd=1, sign=False, unit=""):
    return ai._f(v, nd, sign, unit)


def _usd(v):
    if v is None:
        return "—"
    s = f"${abs(v):,.2f}"
    return "-" + s if v < 0 and s != "$0.00" else s


def _ml(day):
    return day[:7] if day else "—"


def _asof(day, date):
    return "" if not day or day == date else f"({day})"


def _mon(day):
    """'2026-10-01' → '10월'."""
    return f"{int(day[5:7])}월"


def _prev_mon(day):
    return _mon(_iso(_mday(_mkey(datetime.date.fromisoformat(day)) - 1)))


def _p(v):
    return "p—" if v is None else f"p{v:.0f}"


def _mtd(v, k):
    """소매가의 이번 달 평균 대 지난달 — 값이 없으면 빈 글."""
    if not v.get(f"{k}_m"):
        return ""
    return (f" · {_mon(v[f'{k}_m'])} 평균 {_usd(v[f'{k}_m_avg'])}({v[f'{k}_m_n']}주) 대 {_prev_mon(v[f'{k}_m'])} "
            f"{_f(v[f'{k}_m_ch'], sign=True, unit='%')}")


def _krw_line(v):
    """원화 환산 줄 — 보이는 숫자끼리 합이 맞게(전년비·달러 몫을 각자 반올림하고 환율 몫은 그 차)."""
    y, d = round(v["yoy"], 1), round(v["usd_pp"], 1)
    return (f"{_ml(v['month'])} 월평균 배럴당 {_f(v['krw'], 1)}만원 · 전년비 {_f(y, sign=True, unit='%')} = "
            f"달러 유가 {_f(d, sign=True, unit='%p')} + 원/달러 {_f(y - d, sign=True, unit='%p')}")


def texts(key, v, date):
    """칸 → (숫자 줄, 덧붙이는 줄 목록). 정해 둔 문구에 숫자만 넣는다."""
    if key == "crude":
        real = (f" · 실질 WTI {_ml(v['wti_month'])} 월평균 {_p(v['real_pct'])} (명목 {_p(v['nom_pct'])}, 1986~)"
                if v.get("real_pct") is not None else "")
        extra = [f"{date} 기준 EIA 현물(배럴당 달러, 일간). 13주 변화는 91일 전, 전년비는 1년 전 같은 날(휴일이면 그 전 마지막 "
                 "관측)과 견준다."]
        if real:
            extra.append(f"실질 WTI는 WTI 월평균 {_usd(v['wti_avg'])}(관측 10일 이상인 달) ÷ 같은 달 CPI 전체다 — CPI가 아직 없는 "
                         f"달은 3개월 안의 마지막 CPI로 나눈다(이번엔 {_ml(v['real_cpi_month'])}). p는 1986년 이후 {v['real_n']}개 "
                         "달 가운데 이 값 이하인 달의 비율이고, 명목은 나누지 않은 월평균으로 같은 달들에서 잰다.")
        return (f"Brent {_usd(v['brent'])}{_asof(v['brent_date'], date)} · 13주 {_f(v['brent_13w'], sign=True, unit='%')} · "
                f"전년비 {_f(v['brent_yoy'], sign=True, unit='%')} / WTI {_usd(v['wti'])}{_asof(v['wti_date'], date)} · "
                f"13주 {_f(v['wti_13w'], sign=True, unit='%')} · 전년비 {_f(v['wti_yoy'], sign=True, unit='%')}{real}", extra)
    if key == "base":
        months = " · ".join(f"{_ml(_iso(_mday(_mkey(datetime.date.fromisoformat(v['m0'])) + k)))} "
                            f"{_f(v[f'p{k}'], sign=True, unit='%')}" for k in range(1, PATH_MONTHS + 1))
        cliff = (f"{_ml(v['cliff'])}" if v["cliff"] else "앞 6개월 안에 없음")
        return (f"최근 20영업일 평균 {_usd(v['flat'])}({v['flat_from']}~{v['flat_to']})이 그대로면 Brent 전년비: "
                f"{_ml(v['m0'])} {_f(v['p0'], sign=True, unit='%')} · {months}",
                [f"기저 절벽(가격이 그대로일 때 전년비가 이번 달보다 30%p 넘게 낮아지는 첫 달): {cliff}",
                 "전년비는 1년 전 같은 달의 월평균(관측 10일 이상)과 견준 산술이다. 가격을 그대로 둔 계산이라 유가를 예측하지 "
                 "않는다 — 1년 전 가격의 움직임이 전년비에 남기는 몫만 보인다."])
    if key == "products":
        return (f"휘발유 {_usd(v['gas'])}/갤런{_asof(v['gas_date'], date)} · 13주 {_f(v['gas_13w'], sign=True, unit='%')} · "
                f"전년비 {_f(v['gas_yoy'], sign=True, unit='%')}{_mtd(v, 'gas')} / 경유 {_usd(v['diesel'])}/갤런"
                f"{_asof(v['diesel_date'], date)} · 13주 {_f(v['diesel_13w'], sign=True, unit='%')} · "
                f"전년비 {_f(v['diesel_yoy'], sign=True, unit='%')}{_mtd(v, 'diesel')}",
                [f"{date} 기준 EIA 미국 평균 소매가(휘발유는 보통 등급·모든 제형, 주간). 원유 현물보다 CPI 에너지 항목에 가까운 가격이다.",
                 "이번 달 평균은 마지막 관측이 든 달의 주간 값 평균을 지난달 평균과 견준 것이다(계절조정 없음 — 달 초에는 한두 주뿐)."])
    if key == "cracks":
        return (f"{date} 3-2-1 {_usd(v['c321'])} (20영업일 평균 {_usd(v['c321_avg'])}, 1년 전 {_usd(v['c321_avg_1y'])}) · "
                f"경유 − Brent {_usd(v['ulsd'])}{_asof(v['ulsd_date'], date)} (20영업일 평균 {_usd(v['ulsd_avg'])}, "
                f"1년 전 {_usd(v['ulsd_avg_1y'])})",
                ["배럴당 달러. 3-2-1은 원유 3배럴로 휘발유 2배럴과 경유 1배럴을 만든다고 본 정제 마진이다: (뉴욕항 휘발유 × 2 + "
                 "뉴욕항 초저유황 경유 × 1) ÷ 3 − WTI(제품은 갤런당 달러 × 42). 경유 − Brent는 같은 경유 × 42 − Brent다.",
                 "미국 정제 마진은 WTI로 잰다 — Brent가 WTI보다 크게 벌어진 때 Brent로 재면 마진이 작아 보인다."])
    if key == "spread":
        return (f"{date} {_usd(v['last'])} · 20영업일 평균 {_usd(v['avg'])} · 13주 전 20영업일 평균 {_usd(v['avg_13w'])}",
                ["Brent(북해, 해상 운송 원유)와 WTI(미국 내륙) 현물 가격의 차, 배럴당 달러다. 벌어지면 미국 밖 원유가 미국 "
                 "원유보다 상대적으로 비싸졌다는 뜻이고, 좁혀지면 그 반대다. 원인은 이 숫자로 가리지 않는다."])
    if key == "cpi":
        h, c = round(v["head"], 1), round(v["core"], 1)
        return (f"CPI 에너지 전년비 {_f(v['energy'], sign=True, unit='%')}({_ml(v['energy_month'])}) · "
                f"전체 {_f(h, unit='%')} − 근원 {_f(c, unit='%')} = {_f(h - c, sign=True, unit='%p')}({_ml(v['month'])})",
                ["BLS 계절조정 지수의 전년비(1년 전 같은 달이 있을 때만). 전체 − 근원이 크면 식품·에너지 몫이 크다. 근원에 빠진 "
                 "달이 있으면 두 값이 모두 있는 마지막 달로 적는다."])
    if key == "i4":
        head = f"{_ml(v['month'])} I4(CPI 전체 a3 − 근원 a3) {_f(v['i4'], 2, True, '%p')}"
        if v["pce_month"] is None:
            tail = " · 꼬리표: 근원 PCE 미수신"
        else:
            tags = "·".join(v["tags"]) if v["tags"] else "없음"
            at = (f" · 그 달 I4 {_f(v['hc_pce'], 2, True, '%p')}" if v["pce_month"] != v["month"] else "")
            tail = f" · 꼬리표 {tags} — 근원 PCE {_ml(v['pce_month'])} 물가 상태 {v['p']}{at} 기준"
        return (head + tail,
                ["I4는 CPI 전체와 근원(식품·에너지 제외)의 3개월 연율 차다(BLS 계절조정, %p). 꼬리표 '공급형(에너지)'는 근원 PCE "
                 f"물가 상태가 P+이고 그 달 I4가 +{SUPPLY_HC:.1f}%p 이상일 때, '에너지 하락'은 그 달 I4가 -{SUPPLY_HC:.1f}%p "
                 "이하일 때 붙는다. 꼬리표는 근원 PCE가 있는 마지막 달로 잰다.",
                 f"물가 상태는 근원 PCE 전년비 3개월 평균의 띠(높음: {H_IN:g}% 넘으면 들어가 {H_OUT:g}% 밑에서 나옴 · 낮음: "
                 f"{LO_IN:g}% 밑이면 들어가 {LO_OUT:g}% 넘어서 나옴 · 그 밖 중간)와 모멘텀(6개월 연율 − 전년비가 +{MOM:g}%p "
                 f"이상이면 가속, -{MOM_DN:g}%p 이하가 {MOM_DN_N}개 발표 이어지면 둔화, 그 밖 보통)을 맞춘 칸이다: 높음 × 가속·보통 "
                 "= P+, 높음 × 둔화 = Pd, 중간 × 가속 = P+, 중간 × 보통 = P0, 중간 × 둔화 = P−, 낮음 × 가속 = P0, 낮음 × 보통·둔화 "
                 "= P−, 정하지 못하면 ?. 운영자가 2026-10-14에 고정한 측정 정의이고, 유가·금리를 예측하지 않는다."])
    if key == "bei":
        return (f"{date} 5년 BEI {_f(v['be5'], 2, unit='%')}{_asof(v['be5_date'], date)} (13주 "
                f"{_f(v['be5_13w'], 0, True, 'bp')}) · 5년 뒤 5년 {_f(v['fwd'], 2, unit='%')}{_asof(v['fwd_date'], date)} "
                f"(13주 {_f(v['fwd_13w'], 0, True, 'bp')}) · 차 {_f(v['gap'], 0, True, 'bp')} (13주 "
                f"{_f(v['gap_13w'], 0, True, 'bp')})",
                ["5년 BEI는 5년 명목 국채와 5년 TIPS 금리의 차, 5년 뒤 5년은 5년·10년 명목 국채와 TIPS 금리로 계산한 5년 뒤부터 "
                 "5년 동안의 값이다(세인트루이스 연은). 유가가 앞쪽 5년에만 실리는지, 5년 뒤 5년도 함께 움직이는지 나란히 본다. BEI에는 위험·"
                 "유동성 프리미엄도 섞인다."])
    if key == "state":
        sign = "—" if v["yoy"] is None else "+" if round(v["yoy"], 6) > 0 else "−" if round(v["yoy"], 6) < 0 else "0"
        cliff = _ml(v["cliff"]) if v["cliff"] else "없음"
        avg = " · ".join(f"{STATE_NAME[k]} {_f(STATE_AVG[k], 2, True, '%')}" for k in ("up", "flat", "down"))
        return (f"{_ml(v['month'])} {STATE_NAME[v['state']]} (Brent 월평균 3개월 로그 변화 {_f(v['d3'], sign=True, unit='%')}) · "
                f"전년비 {sign} · 기저 절벽 {cliff}({_ml(v['path_month'])}부터 앞 6개월, 가격이 그대로일 때) — 측정 기록: 다음 "
                f"3개월 CPI 에너지 평균 {avg} (전체 {_f(STATE_AVG['all'], 2, True, '%')}, 1990~)",
                [STATE_DEF,
                 "지난 석 달을 적은 것이고 유가나 금리를 예측하지 않는다. 운영자가 1990년 이후 자료로 재 본 바로는 유가의 3개월 "
                 "추세가 다음 3개월로 이어지지 않았다. 규칙 수에 들지 않고 다른 칸의 계산에 쓰지 않는다.",
                 f"줄 끝의 평균은 운영자 측정 기록이다({STATE_FIXED} 고정): 1990년 이후 상태 달 "
                 f"{sum(STATE_N.values())}개 — 오름 {STATE_N['up']} · 보합 {STATE_N['flat']} · 내림 {STATE_N['down']} — 의 다음 "
                 "3개월 CPI 에너지 로그 변화 평균. 지난 기록이고 예측이 아니며, 계산에 쓰지 않는다."])
    if key == "supply":
        return (f"석유·가스 시추 생산 전년비 {_f(v['drill_yoy'], sign=True, unit='%')}({_ml(v['drill_month'])}) · "
                f"석유·가스 추출 가동률 {_f(v['util'], unit='%')}({_ml(v['util_month'])}, 1년 전 {_f(v['util_1y'], unit='%')})",
                ["연준 산업생산(G.17): 시추는 석유·가스 시추 산업생산 지수(계절조정 없음)의 같은 달 전년비, 가동률은 석유·가스 추출 "
                 "업종의 설비 가동률(계절조정)이다. 미국 공급 쪽 반응을 보는 참고 한 줄이고, 유가를 예측하지 않는다."])
    if key == "korea":
        y = round(v["yoy"], 1)
        d = round(v["usd_pp"], 1)
        return (f"{_ml(v['month'])} 월평균 배럴당 {_f(v['krw'], 1)}만원 · 전년비 {_f(y, sign=True, unit='%')} = "
                f"달러 유가 {_f(d, sign=True, unit='%p')} + 원/달러 {_f(y - d, sign=True, unit='%p')}",
                [f"Brent 월평균(달러, {_f(v['usd_yoy'], sign=True, unit='%')}) × 원/달러 월평균({_f(v['fx_yoy'], sign=True, unit='%')})"
                 f" — 둘 다 관측된 날({v['days']}일)로 낸 평균이다. 두 몫은 전년비를 두 로그 변화의 비율로 나눈 것이라 합이 "
                 "전년비와 같다.",
                 "원유 도입 단가(두바이 등)와 다르고, 국내 소비자물가에는 세금·정부 가격 조치를 거쳐 실린다."])
    if key == "dubai":
        return (_krw_line(v),
                [f"IMF 두바이 원유 월평균 가격(달러, {_f(v['usd_yoy'], sign=True, unit='%')}) × 원/달러 월평균(관측 10일 이상, "
                 f"{_f(v['fx_yoy'], sign=True, unit='%')}). 두 몫은 Brent 줄과 같은 방식으로 나눠 합이 전년비와 같다.",
                 "한국이 들여오는 원유의 기준 가격에 가까운 쪽이다. 국내 소비자물가에는 세금·정부 가격 조치를 거쳐 실린다."])
    raise KeyError(key)


def citation(sid, retrieved):
    d = datetime.date.fromisoformat(retrieved)
    src, title = SOURCES[sid]
    return (f"{src}, {title} [{sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; "
            f"{rp.FRED_URL.format(sid)}, {ai._MONTHS[d.month - 1]} {d.day}, {d.year}.")


def series_of(spec, values=None):
    """칸이 쓴 시리즈 — 꼭 필요한 것과, 값이 채워진 optional 시리즈."""
    opt = [sid for sid, k in spec.get("optional", {}).items() if values and values.get(k) is not None]
    return list(spec["series"]) + opt


def sources_of(spec, retrieved=None, values=None):
    out = []
    for sid in series_of(spec, values):
        s = {"series": sid, "name": SOURCES[sid][0], "url": rp.FRED_URL.format(sid), "licence": LICENCE[sid]}
        if retrieved:
            s["citation"] = citation(sid, retrieved)
        out.append(s)
    return out


def source_note(spec):
    names = list(dict.fromkeys(SOURCES[sid][0] for sid in spec["series"]))
    return "자료: " + " · ".join(names) + " (via FRED) · 선은 macro-regime-check가 이 자료로 계산한 값"


def notices(spec, values=None):
    out = [COMPUTED_NOTICE]
    for sid in series_of(spec, values):
        t = SERIES_NOTICES.get(sid)
        if t and t not in out:
            out.append(t)
    return out


def present(key, core, retrieved):
    spec = BY_KEY[key]
    line, extra = texts(key, core["values"], core["date"])
    out = {"key": key, "name": spec["title"], "date": core["date"], "values": core["values"], "retrieved": retrieved,
           "line": line, "extra": extra, "notices": notices(spec, core["values"]),
           "sources": sources_of(spec, retrieved, core["values"])}
    if spec.get("lines"):
        c = spec["chart"]
        out["chart"] = {"key": f"oil_{key}", "title": spec["title"], "unit": c["unit"], "years": c["years"],
                        "zero": c["zero"], "threshold": None, "note": c["note"], "source_note": source_note(spec),
                        "notices": [], "lines": [{**ln, "derived": False, "points": core["lines"][ln["key"]]}
                                                 for ln in spec["lines"]]}
    return out


# ---------- 직전 파일 ----------

_KIND = dict(ai._KIND, state=lambda v: isinstance(v, str) and v in STATE_NAME,
             **{"int?": lambda v: v is None or (type(v) is int and v >= 0),
                "pstate?": lambda v: v is None or (isinstance(v, str) and v in {*P_GRID.values(), P_UNKNOWN}),
                "tags?": lambda v: v is None or (isinstance(v, list) and len(set(v)) == len(v)
                                                 and all(isinstance(x, str) and x in TAGS for x in v))})


def core_of(item, key):
    """직전 파일의 칸 → (core, 받은 날) 또는 None(없거나 꼴이 어긋남)."""
    spec = BY_KEY[key]
    try:
        vals = item["values"]
        lines = {ln["key"]: ln["points"] for ln in item["chart"]["lines"]} if spec.get("lines") else {}
        ok = (ai._is_day(item["date"]) and ai._is_day(item["retrieved"]) and isinstance(vals, dict)
              and set(vals) == set(spec["values"]) and all(_KIND[t](vals[k]) for k, t in spec["values"].items())
              and set(lines) == {ln["key"] for ln in spec.get("lines", ())}
              and all(isinstance(p, list) and len(p) == 2 and ai._is_day(p[0]) and (p[1] is None or ai._is_num(p[1]))
                      for pts in lines.values() for p in (pts if isinstance(pts, list) else [None])))
        texts(key, vals, item["date"])
    except (KeyError, TypeError, IndexError, AttributeError, ValueError):
        return None
    if not ok:
        return None
    return {"date": item["date"], "values": dict(vals), "lines": lines}, item["retrieved"]


def previous(out):
    try:
        with open(os.path.join(out, FILE), encoding="utf-8") as f:
            js = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(js, dict) or js.get("schema") != SCHEMA or not isinstance(js.get("items"), dict):
        return {}
    return {k: v for k, v in js["items"].items() if k in BY_KEY and isinstance(v, dict)}


def _ends(key, core):
    return [("date", core["date"])] + [(k, core["values"].get(k)) for k in BY_KEY[key].get("ends", ())]


def item_ok(key, core, prev, today):
    old = core_of(prev, key) if prev else None
    if old and any(new and was and new < was for (_, new), (_, was) in zip(_ends(key, core), _ends(key, old[0]))):
        raise ItemError("older")
    same = old and json.loads(json.dumps(old[0])) == json.loads(json.dumps(core))
    retrieved = old[1] if same else today.isoformat()
    return {"ok": True, "stale": False, "error": None, "failed_since": None, **present(key, core, retrieved)}


def item_failed(key, code, prev, today):
    since = prev.get("failed_since") if prev and ai._is_day(prev.get("failed_since")) else today.isoformat()
    old = core_of(prev, key) if prev else None
    if old:
        return {"ok": False, "stale": True, "error": REASONS[code], "failed_since": since, **present(key, *old)}
    spec = BY_KEY[key]
    return {"ok": False, "stale": False, "error": REASONS[code], "failed_since": since, "key": key,
            "name": spec["title"], "sources": sources_of(spec)}


def build(results, prev, now):
    today = now.date()
    items = {}
    for spec in ITEMS:
        key = spec["key"]
        r, p = results[key], prev.get(key)
        if not isinstance(r, ItemError):
            try:
                items[key] = item_ok(key, r, p, today)
                continue
            except ItemError as e:
                r = e
        items[key] = item_failed(key, r.code, p, today)
    return {"schema": SCHEMA, "generated_at": now.isoformat(timespec="seconds"), "notice": NOTICE,
            "order": [s["key"] for s in ITEMS], "items": items}


# ---------- 수신 ----------

def load_all(work, offline=False, fred_load=None, clock=time.monotonic, budget=BUDGET, opener=None):
    """{ID: 시계열}과 {ID: 실패 코드}. 온라인에서 캐시로 대신한 것은 실패('cache')."""
    cache = os.path.join(work, CACHE)
    data, errors = {}, {}
    deadline = clock() + budget
    for sid in SERIES:
        left = deadline - clock()
        if not offline and left <= 1:
            errors[sid] = "fetch"
            continue
        try:
            if fred_load:
                series, src = fred_load(sid, cache, offline=offline, timeout=min(ai.TIMEOUT, max(1.0, left)))
            else:
                series, src = ai.load_series(sid, cache, offline, deadline, clock, opener)
        except Exception:
            errors[sid] = "fetch"
            continue
        if src != "net" and not offline:
            errors[sid] = "cache"
            continue
        if not series:
            errors[sid] = "format"
            continue
        data[sid] = series
    return data, errors


def compute(data, errors, today):
    S = {sid: [(d, v) for d, v in s if d <= today] for sid, s in data.items()}
    out = {}
    for spec in ITEMS:
        miss = [sid for sid in spec["series"] if sid not in S or not S[sid]]
        if miss:
            out[spec["key"]] = ItemError(errors.get(miss[0], "format"))
            continue
        try:
            out[spec["key"]] = spec["calc"](S)
        except ItemError as e:
            out[spec["key"]] = e
        except Exception as e:                  # 계산 쪽 뜻밖의 오류도 그 칸만 실패로
            print(f"[oil_fetch] {spec['key']} 계산 오류: {type(e).__name__}", file=sys.stderr)
            out[spec["key"]] = ItemError("format")
    return out


# ---------- 쓰기 ----------

def differs(out, data):
    try:
        with open(os.path.join(out, FILE), encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        return True
    strip = lambda d: {k: v for k, v in d.items() if k != "generated_at"} if isinstance(d, dict) else d
    return strip(old) != strip(json.loads(json.dumps(data)))


def write(out, data):
    os.makedirs(out, exist_ok=True)
    ai._atomic_write(os.path.join(out, FILE), json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def main(argv=None, fred_load=None, now=None, clock=time.monotonic, opener=None):
    ap = argparse.ArgumentParser(description="FRED 공개 통계 → 유가·에너지 참고 자료(<out>/oil.json)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    ap.add_argument("--work", default=DEFAULT_WORK, help="작업 폴더 — 원문 캐시는 <work>/oil/ (기본: 저장소의 .work/)")
    ap.add_argument("--offline", action="store_true", help="요청하지 않고 캐시만 읽는다(로컬 확인용)")
    a = ap.parse_args(argv)
    out, work = os.path.abspath(a.out), os.path.abspath(a.work)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    data, errors = load_all(work, a.offline, fred_load, clock, opener=opener)
    data = build(compute(data, errors, now.date()), previous(out), now)
    for spec in ITEMS:                          # Actions 로그 — 날짜와 정해 둔 사유만(값은 찍지 않는다)
        it = data["items"][spec["key"]]
        if it["ok"]:
            print(f"[oil_fetch] {spec['key']} {it['date']} 기준")
        else:
            kept = f" — 직전 값({it['date']} 기준) 유지" if it["stale"] else ""
            ai.annotate(f"유가·에너지 참고 {spec['key']} 받지 못함: {it['error']}{kept}")
    try:
        if differs(out, data):
            write(out, data)
    except OSError as e:
        print(f"[oil_fetch] {FILE}를 쓰지 못함: {type(e).__name__}", file=sys.stderr)
        return 1
    return 0 if any(it["ok"] for it in data["items"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
