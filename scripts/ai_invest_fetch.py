#!/usr/bin/env python3
"""참고 자료 — AI 투자 (2026-10-27 추가, 사용자 결정: 판정 없는 블록).

AI 투자를 채널 다섯으로 나눠 공개 통계의 숫자와 그래프만 싣는다. 규칙이 아니다 — 충족·판정·문턱이 없고, 판정·공개본·
그래프 스크립트는 이 파일(<out>/ai_invest.json)을 읽지 않는다. 채널과 칸(ITEMS — 칸마다 그래프 하나):
  실물 투자   ict_share     정보처리 장비·소프트웨어 투자 / 명목 GDP(%) — BEA A679RC1Q027SBEA, 장비만 Y034RC1Q027SBEA, GDP
                            (분기, 1990년~). 1995~2002년 가운데 가장 높았던 분기를 '2000년 전후 고점'으로 함께 적는다
              tech_orders   컴퓨터·전자 신규 주문(Census A34SNO, 3개월 합 전년비) · 반도체 생산(연준 IPG3344S, 전년비) — 월간 10년
              office_cons   민간 사무실 건설 지출(Census PROFCONS, 데이터센터 포함, 3개월 평균 전년비) — 월간 10년
  조달        financing     비금융기업 설비투자 / 내부자금(연준 Z.1 BOGZ1FA105050005Q / BOGZ1FA106000135Q, 4분기 합의 비율, %)
                            — 분기 1985년~, 1985년 이후 중앙값을 참고선으로
  전력 가격   power         산업용 전력 PPI(BLS WPU0543) · CPI 전기(BLS CUSR0000SEHF01) 전년비 — 월간 10년
  금리 쪽 결과 curve_30_10  미 30년 − 10년 국채 금리차(bp, DGS30 − DGS10) — 주간 5년
  상관        corr60        주식 일간 수익률 × 미 10년 금리 일간 변화의 60영업일 상관 — AI 지수(Nasdaq CTA AI, NASDAQNQINTEL)·
                            S&P 500(SP500 — 규칙 카드 '주가-금리 60영업일 상관'과 같은 계산)·나스닥100 기술(NASDAQNDXTMC), 주간 3년
              corr20        AI 지수 × 10년 금리 20영업일 상관과 우연 범위(±, 상관이 0일 때 95%) — 주간 3년
              partial60     S&P 500을 통제한 60영업일 부분상관(AI 지수·나스닥100 기술) — 주간 3년
계산은 모두 이 파일이 한다(원본 파이프라인 ai_corr_check.py와 같은 산식 — 코드는 가져오지 않고 여기서 따로 쓴다). 상관은
fred_fetch.corr_summary와 같은 방식: 두 시계열의 공통 날짜에서 수익률(가격 0인 날은 건너뜀)과 금리 변화를 짝짓는다.

재배포 제한(S&P 500·Nasdaq 지수 — FRED 'copyrighted: pre-approval required'): 원값과 원값을 되살릴 수 있는 파생값은
싣지 않는다. 싣는 것은 상관·부분상관뿐(규칙 카드의 ρ60과 같은 원칙, render_public.RESTRICTED). 나머지(BEA·Census·BLS·
연준)는 FRED의 공개 자료(public domain: citation requested)라 값과 FRED 권장 인용을 싣는다. 시리즈 제목·출처는
2026-10-27 FRED 시리즈 쪽에서 확인했다.

실패: 칸마다 따로. 칸의 시리즈 가운데 하나라도 이번에 받지 못하면(온라인에서 캐시로 대신한 것도) 그 칸은 직전 파일의 숫자를
'받지 못함(stale)'과 그날부터라는 날짜와 함께 이어 싣는다(직전 값이 없으면 오류 문구만). 받은 자료의 기준일이 직전보다
이르면 받지 않는다. 직전 파일이 깨졌거나 꼴이 어긋나면 이어 실을 값이 없는 것으로 본다. 문구는 이 파일에 정해 둔 것뿐이다 —
이어 실을 때도 숫자에서 다시 만든다(오류 원문·예외 문자열은 공개 파일에 싣지 않는다, Actions 로그에는 예외 이름만).
같은 내용이면(생성 시각만 다르면) 파일을 다시 쓰지 않는다. 수신 전체는 BUDGET초 안에서 — 요청마다 남은 시간을 타임아웃으로
주고, 조금씩 흘려보내는 응답에 묶이지 않게 읽는 동안에도 마감을 본다(fetch_csv). 시리즈 끝 날짜가 서로 다르면 문구에 값마다
그 날짜를 적고, 끝 날짜가 하나라도 직전보다 이르면 그 칸은 받지 않는다(ITEMS의 ends).

종료코드: 0 한 칸이라도 이번에 받음 / 1 하나도 못 받음(또는 파일을 쓰지 못함). 워크플로 단계는 continue-on-error이고 알림도
띄우지 않는다 — 참고 자료가 아침 규칙 점검의 성패를 바꾸지 않게. 못 받은 칸은 ::warning:: 주석으로 남긴다.

사용법: python scripts/ai_invest_fetch.py [--out data] [--work .work] [--offline]
"""
import os, sys, re, json, math, time, bisect, argparse, datetime, statistics, urllib.request

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import fred_fetch as ff
import render_public as rp

SCHEMA = 1
REPO = os.path.dirname(SCRIPTS)
DEFAULT_OUT = os.path.join(REPO, "data")
DEFAULT_WORK = os.path.join(REPO, ".work")
FILE = "ai_invest.json"
CACHE = "ai_invest"                       # <work>/ai_invest/<ID>.csv

TIMEOUT = 15                              # 요청 하나(연결·한 번 읽기)
BUDGET = 60                               # 수신 전체(초) — 읽는 동안에도 본다. 워크플로 단계 제한(2분) 안에서 끝나게
MAX_BYTES = 5_000_000                     # 응답 하나의 상한
NUM_ND = 4                                # 문구로 가는 숫자의 소수 자리(문구에서 한 번만 반올림)
PT_ND = 2                                 # 그래프 점의 소수 자리(그래프 글자도 소수 둘째 자리)

CORR_YEARS = 3
MONTHLY_YEARS = 10
CURVE_YEARS = 5
ICT_SINCE = datetime.date(1990, 1, 1)
PEAK_FROM, PEAK_TO = datetime.date(1995, 1, 1), datetime.date(2002, 12, 31)
FIN_SINCE = datetime.date(1985, 1, 1)

_BOARD = "Board of Governors of the Federal Reserve System (US)"
_BEA, _CENSUS, _BLS = "U.S. Bureau of Economic Analysis", "U.S. Census Bureau", "U.S. Bureau of Labor Statistics"
# FRED 권장 인용의 출처·제목(2026-10-27 시리즈 쪽 Suggested Citation 그대로)
SOURCES = {
    "A679RC1Q027SBEA": (_BEA, "Private fixed investment in information processing equipment and software"),
    "Y034RC1Q027SBEA": (_BEA, "Gross Private Domestic Investment: Fixed Investment: Nonresidential: Equipment: "
                              "Information Processing Equipment"),
    "GDP": (_BEA, "Gross Domestic Product"),
    "A34SNO": (_CENSUS, "Manufacturers' New Orders: Computers and Electronic Products"),
    "IPG3344S": (_BOARD, "Industrial Production: Manufacturing: Durable Goods: Semiconductor and Other Electronic "
                         "Component (NAICS = 3344)"),
    "PROFCONS": (_CENSUS, "Total Private Construction Spending: Office in the United States"),
    "BOGZ1FA105050005Q": (_BOARD, "Nonfinancial Corporate Business; Total Capital Expenditures, Transactions"),
    "BOGZ1FA106000135Q": (_BOARD, "Nonfinancial Corporate Business; U.S. Internal Funds, Book, Transactions"),
    "WPU0543": (_BLS, "Producer Price Index by Commodity: Fuels and Related Products and Power: Industrial Electric Power"),
    "CUSR0000SEHF01": (_BLS, "Consumer Price Index for All Urban Consumers: Electricity in U.S. City Average"),
    "DGS30": (_BOARD, "Market Yield on U.S. Treasury Securities at 30-Year Constant Maturity, Quoted on an Investment Basis"),
    "DGS10": (_BOARD, "Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity, Quoted on an Investment Basis"),
    "SP500": ("S&P Dow Jones Indices LLC", "S&P 500"),
    "NASDAQNQINTEL": ("Nasdaq, Inc.", "Nasdaq Consumer Technical Association Artificial Intelligence Index"),
    "NASDAQNDXTMC": ("Nasdaq, Inc.", "NASDAQ-100 Technology Sector Market-Cap Weighted Index"),
}
# 재배포 제한 목록 하나 — 공개본의 목록(render_public.RESTRICTED)에 이 화면이 더 쓰는 Nasdaq 지수 둘을 더한다
RESTRICTED = {**rp.RESTRICTED, "NASDAQNQINTEL": "Nasdaq, Inc.", "NASDAQNDXTMC": "Nasdaq, Inc."}
SERIES = list(SOURCES)

NOTICE = ("이 사이트의 규칙 판정에 쓰지 않는 참고 자료다. 충족·미충족이 없고 상태를 판정하지 않는다. 값의 크기나 방향을 "
          "시장 전망으로 읽지 않는다.")
RESTRICTED_NOTICE = ("S&P 500·Nasdaq 지수는 재배포가 제한된 자료라 지수 값은 싣지 않는다. 상관·부분상관은 "
                     "macro-regime-check가 그 자료(FRED 경유)로 계산한 값이다.")
COMPUTED_NOTICE = "비율·전년비·금리차·분포 숫자는 macro-regime-check가 원자료로 계산한 값이다."
CHANNELS = [("invest", "실물 투자"), ("finance", "조달"), ("power", "전력 가격"), ("rates", "금리 쪽 결과"),
            ("corr", "주식과 미 10년 금리의 상관")]
REASONS = {                                            # 페이지·파일에 나가는 실패 문구는 이것뿐
    "fetch": "수신 실패",
    "cache": "수신 실패(묵은 캐시는 싣지 않음)",
    "format": "계산할 자료가 모자람",
    "older": "받은 자료가 직전 자료보다 오래됨",
}


class ItemError(Exception):
    """한 칸의 실패 — code는 REASONS의 키."""
    def __init__(self, code):
        super().__init__(code)
        self.code = code


# ---------- 산술 ----------

def _r(v, nd=NUM_ND):
    return None if v is None else round(v, nd) + 0.0          # + 0.0: -0.0을 0.0으로


def _iso(d):
    return d.isoformat()


def null_band(n, k=0):
    """상관이 0일 때 n개 표본 상관(통제 변수 k개)의 95% 범위 — Fisher z: tanh(1.96/√(n−3−k))."""
    return math.tanh(1.96 / math.sqrt(n - 3 - k))


def pairs(px, y):
    """fred_fetch.corr_summary와 같은 짝: 공통 날짜에서 (날짜, 수익률, 금리 변화). 가격이 0인 날은 건너뛴다."""
    al = ff.align(px, y)
    out = []
    for (_, p0, y0), (d, p1, y1) in zip(al, al[1:]):
        if p0 == 0:
            continue
        out.append((d, p1 / p0 - 1, y1 - y0))
    return out


def rolling_corr(px, y, n):
    """[(날짜, n일 상관)] — 마지막 점은 ff.corr_summary(px, y, n)['value']와 같다(테스트가 강제)."""
    pr = pairs(px, y)
    a, b = [r for _, r, _ in pr], [dy for _, _, dy in pr]
    return [(pr[e - 1][0], ff.pearson(a[e - n:e], b[e - n:e])) for e in range(n, len(pr) + 1)]


def triples(sp, x, y):
    """S&P·X·금리 셋의 공통 날짜에서 (날짜, S&P 수익률, X 수익률, 금리 변화). 가격이 0인 날은 건너뛴다."""
    xd, yd = dict(x), dict(y)
    al = [(d, s, xd[d], yd[d]) for d, s in sp if d in xd and d in yd]
    out = []
    for (_, s0, x0, y0), (d, s1, x1, y1) in zip(al, al[1:]):
        if s0 == 0 or x0 == 0:
            continue
        out.append((d, s1 / s0 - 1, x1 / x0 - 1, y1 - y0))
    return out


def partial(rxy, rxs, rys):
    """S를 통제한 X·Y 부분상관. 정의되지 않으면 None."""
    if None in (rxy, rxs, rys):
        return None
    den = (1 - rxs ** 2) * (1 - rys ** 2)
    return None if den <= 0 else (rxy - rxs * rys) / math.sqrt(den)


def rolling_partial(sp, x, y, n):
    """[(날짜, S&P를 통제한 X 수익률 × 금리 변화의 n일 부분상관)]."""
    tr = triples(sp, x, y)
    s, a, b = [t[1] for t in tr], [t[2] for t in tr], [t[3] for t in tr]
    out = []
    for e in range(n, len(tr) + 1):
        ss, aa, bb = s[e - n:e], a[e - n:e], b[e - n:e]
        out.append((tr[e - 1][0], partial(ff.pearson(aa, bb), ff.pearson(aa, ss), ff.pearson(bb, ss))))
    return out


def rolling_ret_corr(px, qx, n):
    """두 가격 시계열 일간 수익률의 n일 상관(공통 날짜) — 마지막 (날짜, 값). 모자라면 (None, None)."""
    al = ff.align(px, qx)
    a, b, last = [], [], None
    for (_, p0, q0), (d, p1, q1) in zip(al, al[1:]):
        if p0 == 0 or q0 == 0:
            continue
        a.append(p1 / p0 - 1)
        b.append(q1 / q0 - 1)
        last = d
    return (last, ff.pearson(a[-n:], b[-n:])) if len(a) >= n else (None, None)


def _last(vals):
    """[(날짜, 값)]의 마지막 (날짜, 값) — 값이 None이면 None."""
    return vals[-1] if vals and vals[-1][1] is not None else None


def _weekly_points(vals, start, nd=PT_ND):
    return [[_iso(d), _r(v, nd)] for d, v in ff.weekly_last(vals) if d >= start]


def _mkey(d):
    return d.year * 12 + d.month - 1


def monthly_yoy(series, k=1):
    """월간 시계열 → [(날짜, k개월 합의 전년비 %)] — k개월과 1년 전 같은 k개월이 모두 있을 때만(결측월을 대신하지 않는다)."""
    by = {_mkey(d): (d, v) for d, v in series}
    out = []
    for m in sorted(by):
        cur = [by.get(m - i) for i in range(k)]
        old = [by.get(m - 12 - i) for i in range(k)]
        if None in cur or None in old:
            continue
        den = sum(v for _, v in old)
        if den == 0:
            continue
        out.append((by[m][0], (sum(v for _, v in cur) / den - 1) * 100))
    return out


def _qkey(d):
    return d.year * 4 + (d.month - 1) // 3


def quarterly_ratio(num, den, k=1):
    """분기 시계열 둘 → [(날짜, k분기 합 비율 %)] — 같은 분기들이 모두 있을 때만."""
    a = {_qkey(d): (d, v) for d, v in num}
    b = {_qkey(d): v for d, v in den}
    out = []
    for q in sorted(a):
        qs = [q - i for i in range(k)]
        if any(x not in a or x not in b for x in qs):
            continue
        s_den = sum(b[x] for x in qs)
        if s_den == 0:
            continue
        out.append((a[q][0], sum(a[x][1] for x in qs) / s_den * 100))
    return out


def _year_ago(vals):
    """[(날짜, 값)]의 마지막 관측 1년 전(같은 달) 값 — 없으면 None."""
    d1 = vals[-1][0]
    t = ff.shift_year(d1)
    hit = [v for d, v in vals if (d.year, d.month) == (t.year, t.month)]
    return hit[-1] if hit else None


def qlabel(day):
    """'2026-04-01' → '2026Q2'."""
    d = datetime.date.fromisoformat(day)
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def mlabel(day):
    """'2026-09-01' → '2026-09'."""
    return day[:7]


# ---------- 칸마다 계산 (S: {ID: [(date, value)]}) → core {date, values, lines} ----------

def calc_ict_share(S):
    tot = quarterly_ratio(S["A679RC1Q027SBEA"], S["GDP"])
    hw = quarterly_ratio(S["Y034RC1Q027SBEA"], S["GDP"])
    if not tot or not hw:
        raise ItemError("format")
    win = [(d, v) for d, v in tot if PEAK_FROM <= d <= PEAK_TO]
    hwin = [(d, v) for d, v in hw if PEAK_FROM <= d <= PEAK_TO]
    if not win or not hwin:
        raise ItemError("format")
    pk, hpk = max(win, key=lambda t: t[1]), max(hwin, key=lambda t: t[1])
    d1, v1 = tot[-1]
    hw_d = dict(hw)
    return {"date": _iso(d1),
            "values": {"share": _r(v1), "share_1y": _r(_year_ago(tot)), "peak": _r(pk[1]), "peak_date": _iso(pk[0]),
                       "hw": _r(hw_d.get(d1)), "hw_peak": _r(hpk[1]), "hw_peak_date": _iso(hpk[0])},
            "lines": {"total": [[_iso(d), _r(v, PT_ND)] for d, v in tot if d >= ICT_SINCE],
                      "hw": [[_iso(d), _r(v, PT_ND)] for d, v in hw if d >= ICT_SINCE]}}


def _flat(pts, value):
    """참고선(값이 하나) — 주 선과 같은 날짜마다 점을 둔다(툴팁·표에 다른 날짜가 끼지 않게)."""
    days = [p[0] if isinstance(p, list) else _iso(p[0]) for p in pts]
    return [[d, _r(value, PT_ND)] for d in days]


def _monthly_points(vals, start):
    """월간 [(날짜, 값)] → 그래프 점. 빠진 달은 None으로 두어 선을 끊는다(빈 달을 곧은 선으로 잇지 않게)."""
    by = {_mkey(d): v for d, v in vals if d >= start}
    if not by:
        return []
    out = []
    for m in range(min(by), max(by) + 1):
        out.append([_iso(datetime.date(m // 12, m % 12 + 1, 1)), _r(by[m], PT_ND) if m in by else None])
    return out


def _since_years(vals, years):
    return _monthly_points(vals, ff.shift_year(vals[-1][0], -years))


def calc_tech_orders(S):
    orders, semis = monthly_yoy(S["A34SNO"], 3), monthly_yoy(S["IPG3344S"])
    if not orders or not semis:
        raise ItemError("format")
    last = max(orders[-1][0], semis[-1][0])
    start = ff.shift_year(last, -MONTHLY_YEARS)
    return {"date": _iso(last),
            "values": {"orders": _r(orders[-1][1]), "orders_date": _iso(orders[-1][0]),
                       "semis": _r(semis[-1][1]), "semis_date": _iso(semis[-1][0])},
            "lines": {"orders": _monthly_points(orders, start), "semis": _monthly_points(semis, start)}}


def calc_office_cons(S):
    yoy = monthly_yoy(S["PROFCONS"], 3)
    if not yoy:
        raise ItemError("format")
    d1, lvl = S["PROFCONS"][-1]
    return {"date": _iso(yoy[-1][0]),
            "values": {"yoy": _r(yoy[-1][1]), "level_bn": _r(lvl / 1000), "level_date": _iso(d1)},
            "lines": {"yoy": _since_years(yoy, MONTHLY_YEARS)}}


def calc_financing(S):
    ratio = quarterly_ratio(S["BOGZ1FA105050005Q"], S["BOGZ1FA106000135Q"], 4)
    hist = [v for d, v in ratio if d >= FIN_SINCE]
    if len(hist) < 8:
        raise ItemError("format")
    med = statistics.median(hist)
    d1, v1 = ratio[-1]
    pts = [(d, v) for d, v in ratio if d >= FIN_SINCE]
    return {"date": _iso(d1),
            "values": {"ratio": _r(v1), "ratio_1y": _r(_year_ago(ratio)), "median": _r(med),
                       "above100": _r(sum(v > 100 for v in hist) / len(hist) * 100), "n": len(hist),
                       "from": _iso(pts[0][0])},
            "lines": {"ratio": [[_iso(d), _r(v, PT_ND)] for d, v in pts], "median": _flat(pts, med)}}


def calc_power(S):
    ppi, cpi = monthly_yoy(S["WPU0543"]), monthly_yoy(S["CUSR0000SEHF01"])
    if not ppi or not cpi:
        raise ItemError("format")
    last = max(ppi[-1][0], cpi[-1][0])
    start = ff.shift_year(last, -MONTHLY_YEARS)
    return {"date": _iso(last),
            "values": {"ppi": _r(ppi[-1][1]), "ppi_date": _iso(ppi[-1][0]),
                       "cpi": _r(cpi[-1][1]), "cpi_date": _iso(cpi[-1][0])},
            "lines": {"ppi": _monthly_points(ppi, start), "cpi": _monthly_points(cpi, start)}}


def calc_curve_30_10(S):
    spread = [(d, (a - b) * 100) for d, a, b in ff.align(S["DGS30"], S["DGS10"])]
    if not spread:
        raise ItemError("format")
    d1, v1 = spread[-1]
    base = ff.on_or_before(spread, d1 - datetime.timedelta(days=364))
    start = ff.shift_year(d1, -CURVE_YEARS)
    win = [v for d, v in spread if d >= start]
    return {"date": _iso(d1),
            "values": {"spread": _r(v1), "spread_1y": _r(base and base[1]), "lo": _r(min(win)), "hi": _r(max(win))},
            "lines": {"spread": _weekly_points(spread, start, 1)}}


def _corr_start(*vals):
    return ff.shift_year(max(v[-1][0] for v in vals), -CORR_YEARS)


def calc_corr60(S):
    ai = rolling_corr(S["NASDAQNQINTEL"], S["DGS10"], 60)
    sp = rolling_corr(S["SP500"], S["DGS10"], 60)
    ndx = rolling_corr(S["NASDAQNDXTMC"], S["DGS10"], 60)
    la, ls, ln = _last(ai), _last(sp), _last(ndx)
    if not la or not ls or not ln:
        raise ItemError("format")
    start = _corr_start(ai, sp, ndx)
    ad, ac = rolling_ret_corr(S["NASDAQNQINTEL"], S["SP500"], 60)
    return {"date": _iso(la[0]),
            "values": {"ai": _r(la[1]), "sp": _r(ls[1]), "sp_date": _iso(ls[0]), "ndx": _r(ln[1]),
                       "ndx_date": _iso(ln[0]), "ai_sp": _r(ac), "ai_sp_date": ad and _iso(ad),
                       "band": _r(null_band(60))},
            "lines": {"ai": _weekly_points(ai, start), "sp": _weekly_points(sp, start),
                      "ndx": _weekly_points(ndx, start)}}


def calc_corr20(S):
    ai = rolling_corr(S["NASDAQNQINTEL"], S["DGS10"], 20)
    la = _last(ai)
    if not la:
        raise ItemError("format")
    band = null_band(20)
    start = _corr_start(ai)
    win = [v for d, v in ai if d >= start and v is not None]
    pts = _weekly_points(ai, start)
    return {"date": _iso(la[0]),
            "values": {"ai": _r(la[1]), "band": _r(band),
                       "outside": _r(sum(abs(v) > band for v in win) / len(win) * 100), "days": len(win)},
            "lines": {"ai": pts, "band_hi": _flat(pts, band), "band_lo": _flat(pts, -band)}}


def calc_partial60(S):
    ai = rolling_partial(S["SP500"], S["NASDAQNQINTEL"], S["DGS10"], 60)
    ndx = rolling_partial(S["SP500"], S["NASDAQNDXTMC"], S["DGS10"], 60)
    la, ln = _last(ai), _last(ndx)
    if not la or not ln:
        raise ItemError("format")
    start = _corr_start(ai, ndx)
    return {"date": _iso(la[0]),
            "values": {"ai": _r(la[1]), "ndx": _r(ln[1]), "ndx_date": _iso(ln[0]), "band": _r(null_band(60, 1))},
            "lines": {"ai": _weekly_points(ai, start), "ndx": _weekly_points(ndx, start)}}


# ---------- 칸 정의 (차례 = 화면 차례) ----------
# values: 이름 → 꼴("num" 숫자 · "num?" 숫자 또는 없음 · "day" 날짜 · "day?" 날짜 또는 없음 · "int" 정수) — 직전 파일 검사에도 쓴다
# ends: 시리즈마다의 끝 날짜(values의 날짜 칸) — 칸의 date와 함께 하나라도 직전보다 이르면 받지 않는다
# bounded: 재배포 제한 지수로 만든 칸 — 값(free 밖)과 그래프 점이 모두 −1~1이어야 한다(직전 파일 검사에도)
# lines: (선 key, 이름, 역할, 시리즈) — 역할 main/series/ref는 charts.js 그대로

def _l(key, label, role, series):
    return {"key": key, "label": label, "role": role, "series": series}


ITEMS = [
    {"key": "ict_share", "channel": "invest", "title": "정보처리 장비·소프트웨어 투자 / 명목 GDP",
     "series": ["A679RC1Q027SBEA", "Y034RC1Q027SBEA", "GDP"], "calc": calc_ict_share, "unit": "%", "years": 36,
     "zero": False, "note": "1990년 이후 · 분기 · 명목 투자 ÷ 명목 GDP(계절조정 연율)",
     "values": {"share": "num", "share_1y": "num?", "peak": "num", "peak_date": "day", "hw": "num?", "hw_peak": "num",
                "hw_peak_date": "day"},
     "lines": [_l("total", "장비·소프트웨어", "main", ["A679RC1Q027SBEA", "GDP"]),
               _l("hw", "정보처리 장비만", "series", ["Y034RC1Q027SBEA", "GDP"])]},
    {"key": "tech_orders", "channel": "invest", "title": "컴퓨터·전자 신규 주문과 반도체 생산 — 전년 대비",
     "series": ["A34SNO", "IPG3344S"], "calc": calc_tech_orders, "unit": "%", "years": MONTHLY_YEARS, "zero": True,
     "note": "최근 10년 · 월간 · 주문은 3개월 합, 생산은 지수의 전년 대비",
     "values": {"orders": "num", "orders_date": "day", "semis": "num", "semis_date": "day"},
     "ends": ["orders_date", "semis_date"],
     "lines": [_l("orders", "신규 주문(3개월 합)", "main", ["A34SNO"]),
               _l("semis", "반도체 생산", "series", ["IPG3344S"])]},
    {"key": "office_cons", "channel": "invest", "title": "민간 사무실 건설 지출(데이터센터 포함) — 전년 대비",
     "series": ["PROFCONS"], "calc": calc_office_cons, "unit": "%", "years": MONTHLY_YEARS, "zero": True,
     "note": "최근 10년 · 월간 · 3개월 평균의 전년 대비",
     "values": {"yoy": "num", "level_bn": "num", "level_date": "day"}, "ends": ["level_date"],
     "lines": [_l("yoy", "사무실 건설 지출", "main", ["PROFCONS"])]},
    {"key": "financing", "channel": "finance", "title": "비금융기업 설비투자 / 내부자금 (4분기 합)",
     "series": ["BOGZ1FA105050005Q", "BOGZ1FA106000135Q"], "calc": calc_financing, "unit": "%", "years": 41,
     "zero": False, "note": "1985년 이후 · 분기 · 연준 Z.1 금융계정",
     "values": {"ratio": "num", "ratio_1y": "num?", "median": "num", "above100": "num", "n": "int", "from": "day"},
     "lines": [_l("ratio", "설비투자 / 내부자금", "main", ["BOGZ1FA105050005Q", "BOGZ1FA106000135Q"]),
               _l("median", "1985년 이후 중앙값", "ref", ["BOGZ1FA105050005Q", "BOGZ1FA106000135Q"])]},
    {"key": "power", "channel": "power", "title": "전력 가격 — 전년 대비",
     "series": ["WPU0543", "CUSR0000SEHF01"], "calc": calc_power, "unit": "%", "years": MONTHLY_YEARS, "zero": True,
     "note": "최근 10년 · 월간",
     "values": {"ppi": "num", "ppi_date": "day", "cpi": "num", "cpi_date": "day"}, "ends": ["ppi_date", "cpi_date"],
     "lines": [_l("ppi", "산업용 전력 PPI", "main", ["WPU0543"]),
               _l("cpi", "CPI 전기", "series", ["CUSR0000SEHF01"])]},
    {"key": "curve_30_10", "channel": "rates", "title": "미 30년 − 10년 국채 금리차",
     "series": ["DGS30", "DGS10"], "calc": calc_curve_30_10, "unit": "bp", "years": CURVE_YEARS, "zero": True,
     "note": "최근 5년 · 주간(주의 마지막 관측) · bp",
     "values": {"spread": "num", "spread_1y": "num?", "lo": "num", "hi": "num"},
     "lines": [_l("spread", "30년 − 10년", "main", ["DGS30", "DGS10"])]},
    {"key": "corr60", "channel": "corr", "title": "주식 수익률 × 미 10년 금리 변화 — 60영업일 상관",
     "series": ["NASDAQNQINTEL", "SP500", "NASDAQNDXTMC", "DGS10"], "calc": calc_corr60, "unit": "", "years": CORR_YEARS,
     "zero": True, "note": "최근 3년 · 주간(주의 마지막 값) · 양(+)이면 주가와 금리가 같은 방향",
     "values": {"ai": "num", "sp": "num", "sp_date": "day", "ndx": "num", "ndx_date": "day", "ai_sp": "num?",
                "ai_sp_date": "day?", "band": "num"},
     "ends": ["sp_date", "ndx_date", "ai_sp_date"], "bounded": True,
     "lines": [_l("ai", "AI 지수", "main", ["NASDAQNQINTEL", "DGS10"]),
               _l("sp", "S&P 500", "series", ["SP500", "DGS10"]),
               _l("ndx", "나스닥100 기술", "series", ["NASDAQNDXTMC", "DGS10"])]},
    {"key": "corr20", "channel": "corr", "title": "AI 지수 × 미 10년 금리 변화 — 20영업일 상관",
     "series": ["NASDAQNQINTEL", "DGS10"], "calc": calc_corr20, "unit": "", "years": CORR_YEARS, "zero": True,
     "note": "최근 3년 · 주간(주의 마지막 값) · 회색 선 사이는 상관이 0이어도 나올 수 있는 범위(95%)",
     "values": {"ai": "num", "band": "num", "outside": "num", "days": "int"}, "bounded": True, "free": ["outside"],
     "lines": [_l("ai", "AI 지수 20영업일", "main", ["NASDAQNQINTEL", "DGS10"]),
               _l("band_hi", "우연 범위 위", "ref", []), _l("band_lo", "우연 범위 아래", "ref", [])]},
    {"key": "partial60", "channel": "corr", "title": "S&P 500을 통제한 부분상관 × 미 10년 금리 변화 — 60영업일",
     "series": ["SP500", "NASDAQNQINTEL", "NASDAQNDXTMC", "DGS10"], "calc": calc_partial60, "unit": "",
     "years": CORR_YEARS, "zero": True, "note": "최근 3년 · 주간(주의 마지막 값) · 시장 전체(S&P 500)로 설명되는 몫을 뺀 상관",
     "values": {"ai": "num", "ndx": "num", "ndx_date": "day", "band": "num"}, "ends": ["ndx_date"], "bounded": True,
     "lines": [_l("ai", "AI 지수", "main", ["SP500", "NASDAQNQINTEL", "DGS10"]),
               _l("ndx", "나스닥100 기술", "series", ["SP500", "NASDAQNDXTMC", "DGS10"])]},
]
BY_KEY = {it["key"]: it for it in ITEMS}


# ---------- 문구 ----------

def _f(v, nd=2, sign=False, unit=""):
    if v is None:
        return "—"
    s = f"{v:+.{nd}f}" if sign else f"{v:.{nd}f}"
    if float(s) == 0:
        s = f"{0:.{nd}f}"
    return s + unit


def _asof(day, date):
    """값의 끝 날짜가 칸의 날짜와 다르면 '(그 날짜 기준)' — 늦게 끝난 시리즈의 값을 칸 날짜의 값처럼 적지 않게."""
    return "" if not day or day == date else f"({day} 기준)"


def texts(key, v, date):
    """칸 → (숫자 줄, 덧붙이는 줄 목록). 모두 정해 둔 문구에 숫자만 넣는다."""
    if key == "ict_share":
        return (f"{qlabel(date)} {_f(v['share'], unit='%')} · 1년 전 {_f(v['share_1y'], unit='%')} · "
                f"2000년 전후 고점 {_f(v['peak'], unit='%')}({qlabel(v['peak_date'])})",
                [f"정보처리 장비만 {_f(v['hw'], unit='%')} (2000년 전후 고점 {_f(v['hw_peak'], unit='%')}, "
                 f"{qlabel(v['hw_peak_date'])})",
                 "BEA 국민계정의 명목 투자다(속보 뒤 여러 번 개정된다). 2000년 전후 고점은 1995~2002년 분기 가운데 가장 높은 값이다."])
    if key == "tech_orders":
        return (f"신규 주문(3개월 합) {_f(v['orders'], 1, True, '%')} ({mlabel(v['orders_date'])}) · "
                f"반도체 생산 {_f(v['semis'], 1, True, '%')} ({mlabel(v['semis_date'])})",
                ["주문은 Census 제조업 신규 주문(컴퓨터·전자제품, 명목), 생산은 연준 산업생산(반도체·전자부품, 물량 지수)이다."])
    if key == "office_cons":
        return (f"{mlabel(date)} 3개월 평균 {_f(v['yoy'], 1, True, '%')} · 지출 {_f(v['level_bn'], 1)}bn"
                f"(연율, {mlabel(v['level_date'])})",
                ["Census 건설 지출 분류에서 데이터센터는 '사무실' 안에 들어 있다. 데이터센터만 따로 본 계열은 FRED에 없어, "
                 "일반 사무실 건설이 줄면 데이터센터의 증가가 희석돼 보인다."])
    if key == "financing":
        return (f"{qlabel(date)} {_f(v['ratio'], unit='%')} · 1년 전 {_f(v['ratio_1y'], unit='%')} · "
                f"{v['from'][:4]}년 이후 중앙값 {_f(v['median'], unit='%')}",
                [f"100%를 넘으면 설비투자가 내부자금보다 많다(모자란 몫은 외부 조달). {v['from'][:4]}년 이후 분기의 "
                 f"{_f(v['above100'], 0, unit='%')}가 100%를 넘었다 — 100% 자체는 드문 일이 아니다.",
                 "비금융기업 전체의 합계라 대형 기술 기업의 조달 방식은 따로 보이지 않는다."])
    if key == "power":
        return (f"산업용 전력 PPI {_f(v['ppi'], 1, True, '%')} ({mlabel(v['ppi_date'])}) · "
                f"CPI 전기 {_f(v['cpi'], 1, True, '%')} ({mlabel(v['cpi_date'])})",
                ["데이터센터 전력 수요가 전기 요금에 실리는지 보는 칸이다. 전기는 근원 물가가 아니라 전체 물가에 들어간다. "
                 "연료 가격·날씨도 같이 움직인다."])
    if key == "curve_30_10":
        return (f"{date} {_f(v['spread'], 0, True, 'bp')} · 1년 전 {_f(v['spread_1y'], 0, True, 'bp')} · "
                f"최근 5년 범위 {_f(v['lo'], 0, True, 'bp')} ~ {_f(v['hi'], 0, True, 'bp')}",
                ["장기물 공급·기간 프리미엄이 함께 실리는 금리 쪽 결과다. AI 투자 때문인지는 이 숫자로 가릴 수 없다"
                 "(물가·연준 경로·국채 발행이 같이 움직인다)."])
    if key == "corr60":
        lines = [f"AI 지수와 S&P 500 일간 수익률의 60영업일 상관 {_f(v['ai_sp'])}{_asof(v['ai_sp_date'], date)} — 1에 "
                 "가까울수록 AI 지수의 금리 상관은 S&P 500의 것을 되풀이한다."] if v["ai_sp"] is not None else []
        return (f"{date} AI 지수 {_f(v['ai'], sign=True)} · S&P 500 {_f(v['sp'], sign=True)}{_asof(v['sp_date'], date)} · "
                f"나스닥100 기술 {_f(v['ndx'], sign=True)}{_asof(v['ndx_date'], date)}",
                lines + [f"상관이 0이어도 60영업일 상관은 95% 확률로 ±{_f(v['band'])} 안에 든다. S&P 500 선은 규칙 카드 "
                         "'주가-금리 60영업일 상관'과 같은 계산이다(받은 시각이 달라 마지막 값이 하루 어긋날 수 있다).",
                         "국채 가격 기준으로 보면 부호가 반대다 — 여기서 양(+)이면 주가와 국채 가격이 반대로 움직였다."])
    if key == "corr20":
        return (f"{date} AI 지수 20영업일 {_f(v['ai'], sign=True)} · 우연 범위 ±{_f(v['band'])}",
                [f"최근 3년 {v['days']}영업일 가운데 우연 범위 밖이던 날 {_f(v['outside'], 0, unit='%')}. 20영업일 상관은 "
                 "표본이 짧아 부호가 자주 바뀐다 — 60영업일 상관과 함께 본다."])
    if key == "partial60":
        return (f"{date} AI 지수 {_f(v['ai'], sign=True)} · 나스닥100 기술 {_f(v['ndx'], sign=True)}"
                f"{_asof(v['ndx_date'], date)} · 우연 범위 ±{_f(v['band'])}",
                ["S&P 500 수익률로 설명되는 몫을 뺀 뒤 남는 금리 상관이다. 양(+)이면 시장 전체보다 그 지수가 금리와 같은 "
                 "방향으로 더 움직였다는 뜻이다. 나스닥100 기술 선과 나란히 보면 AI 지수의 남는 몫이 대형 기술주 전체에도 "
                 "있는지 견줄 수 있다."])
    raise KeyError(key)


_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December")


def citation(sid, retrieved):
    """FRED 권장 인용 형식(render_public.citation과 같은 꼴). 날짜는 지금 값을 처음 받은 날."""
    d = datetime.date.fromisoformat(retrieved)
    src, title = SOURCES[sid]
    return (f"{src}, {title} [{sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; "
            f"{rp.FRED_URL.format(sid)}, {_MONTHS[d.month - 1]} {d.day}, {d.year}.")


def sources_of(spec, retrieved=None):
    out = []
    for sid in spec["series"]:
        s = {"series": sid, "name": SOURCES[sid][0], "url": rp.FRED_URL.format(sid), "restricted": sid in RESTRICTED}
        if retrieved:
            s["citation"] = citation(sid, retrieved)
        out.append(s)
    return out


def source_note(spec):
    names = list(dict.fromkeys(SOURCES[sid][0] for sid in spec["series"]))
    return "자료: " + " · ".join(names) + " (via FRED) · 선은 macro-regime-check가 이 자료로 계산한 값"


def notices(spec):
    return [RESTRICTED_NOTICE] if any(s in RESTRICTED for s in spec["series"]) else [COMPUTED_NOTICE]


def present(key, core, retrieved):
    """숫자(core) → 칸 전체(문구 · 그래프 · 고지 · 출처). 이어 실을 때도 이걸로 다시 만든다."""
    spec = BY_KEY[key]
    line, extra = texts(key, core["values"], core["date"])
    derived = any(s in RESTRICTED for s in spec["series"])
    chart = {"key": f"ai_{key}", "title": spec["title"], "unit": spec["unit"], "years": spec["years"],
             "zero": spec["zero"], "threshold": None, "note": spec["note"], "source_note": source_note(spec),
             "notices": [],
             "lines": [{**ln, "derived": derived, "points": core["lines"][ln["key"]]} for ln in spec["lines"]]}
    return {"key": key, "channel": spec["channel"], "name": spec["title"], "date": core["date"],
            "values": core["values"], "retrieved": retrieved, "line": line, "extra": extra, "chart": chart,
            "notices": notices(spec), "sources": sources_of(spec, retrieved)}


# ---------- 직전 파일 ----------

def _is_day(v):
    try:
        return (isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) is not None
                and datetime.date.fromisoformat(v) is not None)
    except ValueError:
        return False


def _is_num(v):
    return type(v) in (int, float) and v == v and abs(v) != float("inf")


_KIND = {"num": _is_num, "num?": lambda v: v is None or _is_num(v), "day": _is_day,
         "day?": lambda v: v is None or _is_day(v), "int": lambda v: type(v) is int and v >= 0}


def _in_bounds(spec, vals, lines):
    """재배포 제한 지수로 만든 칸이면 값(free 밖)과 점이 모두 −1~1 — 지수 수준 같은 값이 섞여 들어오면 싣지 않는다."""
    if not spec.get("bounded"):
        return True
    free = set(spec.get("free", ()))
    nums = [vals[k] for k, t in spec["values"].items() if t in ("num", "num?") and k not in free]
    nums += [p[1] for pts in lines.values() for p in pts]
    return all(x is None or abs(x) <= 1 for x in nums)


def core_of(item, key):
    """직전 파일의 칸 → (core, 받은 날) 또는 None(없거나 꼴이 어긋남 — 이어 실을 값이 없는 것으로 본다)."""
    spec = BY_KEY[key]
    try:
        vals, chart = item["values"], item["chart"]
        lines = {ln["key"]: ln["points"] for ln in chart["lines"]}
        ok = (_is_day(item["date"]) and _is_day(item["retrieved"]) and isinstance(vals, dict)
              and set(vals) == set(spec["values"]) and all(_KIND[t](vals[k]) for k, t in spec["values"].items())
              and set(lines) == {ln["key"] for ln in spec["lines"]}
              and all(isinstance(p, list) and len(p) == 2 and _is_day(p[0]) and (p[1] is None or _is_num(p[1]))
                      for pts in lines.values() for p in (pts if isinstance(pts, list) else [None]))
              and _in_bounds(spec, vals, lines))
        texts(key, vals, item["date"])                    # 문구를 다시 만들 수 있어야 한다
    except (KeyError, TypeError, IndexError, AttributeError, ValueError):
        return None
    if not ok:
        return None
    return {"date": item["date"], "values": dict(vals), "lines": lines}, item["retrieved"]


def previous(out):
    """직전 ai_invest.json → {칸: dict}. 없거나 못 읽으면 {}."""
    try:
        with open(os.path.join(out, FILE), encoding="utf-8") as f:
            js = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(js, dict) or js.get("schema") != SCHEMA or not isinstance(js.get("items"), dict):
        return {}
    return {k: v for k, v in js["items"].items() if k in BY_KEY and isinstance(v, dict)}


def _ends(key, core):
    """칸의 끝 날짜들 — date와 ends에 적은 값 칸(없는 값은 뺀다)."""
    return [("date", core["date"])] + [(k, core["values"].get(k)) for k in BY_KEY[key].get("ends", ())]


def item_ok(key, core, prev, today):
    old = core_of(prev, key) if prev else None
    if old and any(new and was and new < was
                   for (_, new), (_, was) in zip(_ends(key, core), _ends(key, old[0]))):
        raise ItemError("older")                    # 시리즈 하나라도 직전보다 이른 날짜에서 끝나면
    same = old and json.loads(json.dumps(old[0])) == json.loads(json.dumps(core))
    retrieved = old[1] if same else today.isoformat()
    return {"ok": True, "stale": False, "error": None, "failed_since": None, **present(key, core, retrieved)}


def item_failed(key, code, prev, today):
    since = prev.get("failed_since") if prev and _is_day(prev.get("failed_since")) else today.isoformat()
    old = core_of(prev, key) if prev else None
    if old:
        return {"ok": False, "stale": True, "error": REASONS[code], "failed_since": since, **present(key, *old)}
    spec = BY_KEY[key]
    return {"ok": False, "stale": False, "error": REASONS[code], "failed_since": since, "key": key,
            "channel": spec["channel"], "name": spec["title"], "sources": sources_of(spec)}


def build(results, prev, now):
    """results {칸: core 또는 ItemError} → 산출물 dict."""
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
            "channels": [list(c) for c in CHANNELS], "order": [s["key"] for s in ITEMS], "items": items}


# ---------- 수신 ----------

def fetch_csv(sid, deadline, clock=time.monotonic, opener=None):
    """FRED CSV 한 건. 남은 시간을 타임아웃으로 주고, 읽는 동안에도 마감을 본다 — 조금씩 흘려보내는 응답에 묶여 단계 제한을
    넘기지 않게(urllib의 타임아웃은 읽기 한 번마다라 전체 시간을 묶지 못한다). 헤더는 기본 그대로(fred_fetch.urlopen_text 참고)."""
    left = deadline - clock()
    if left <= 1:
        raise TimeoutError("budget")
    chunks, size = [], 0
    with (opener or urllib.request.urlopen)(ff.FRED_CSV.format(sid=sid), timeout=min(TIMEOUT, left)) as r:
        while True:
            if clock() > deadline:
                raise TimeoutError("budget")
            chunk = r.read1(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError("too large")
            chunks.append(chunk)
    return b"".join(chunks).decode("utf-8", "replace")


def load_series(sid, cache_dir, offline, deadline, clock=time.monotonic, opener=None):
    """(시계열, 'net'|'cache'). 온라인이면 받아서(읽히면 캐시에 쓴다 — 캐시로 대신하지 않는다), --offline이면 캐시만."""
    path = ff.cache_path(cache_dir, sid)
    if offline:
        with open(path, encoding="utf-8") as f:
            return ff.parse_csv(f.read()), "cache"
    text = fetch_csv(sid, deadline, clock, opener)
    series = ff.parse_csv(text)
    if series:
        try:
            os.makedirs(cache_dir, exist_ok=True)
            _atomic_write(path, text)
        except OSError:
            pass                                    # 캐시는 덤이다
    return series, "net"


def load_all(work, offline=False, fred_load=None, clock=time.monotonic, budget=BUDGET, opener=None):
    """{ID: 시계열} 과 {ID: 실패 코드}. 온라인에서 캐시로 대신한 것은 실패('cache')로 센다(fred_load를 준 경우 — 테스트)."""
    cache = os.path.join(work, CACHE)
    data, errors, start = {}, {}, clock()
    deadline = start + budget
    for sid in SERIES:
        left = deadline - clock()
        if not offline and left <= 1:
            errors[sid] = "fetch"
            continue
        try:
            if fred_load:
                series, src = fred_load(sid, cache, offline=offline, timeout=min(TIMEOUT, max(1.0, left)))
            else:
                series, src = load_series(sid, cache, offline, deadline, clock, opener)
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
    """{칸: core 또는 ItemError}. 칸의 시리즈가 하나라도 없으면 그 칸은 실패(첫 실패 코드)."""
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
            print(f"[ai_invest_fetch] {spec['key']} 계산 오류: {type(e).__name__}", file=sys.stderr)
            out[spec["key"]] = ItemError("format")
    return out


# ---------- 쓰기 ----------

def _atomic_write(path, text):
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
    _atomic_write(os.path.join(out, FILE), json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def annotate(text):
    print("::warning::" + text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A"), flush=True)


def main(argv=None, fred_load=None, now=None, clock=time.monotonic, opener=None):
    ap = argparse.ArgumentParser(description="FRED 공개 통계 → AI 투자 참고 자료(<out>/ai_invest.json)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    ap.add_argument("--work", default=DEFAULT_WORK, help="작업 폴더 — 원문 캐시는 <work>/ai_invest/ (기본: 저장소의 .work/)")
    ap.add_argument("--offline", action="store_true", help="요청하지 않고 캐시만 읽는다(로컬 확인용)")
    a = ap.parse_args(argv)
    out, work = os.path.abspath(a.out), os.path.abspath(a.work)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    data, errors = load_all(work, a.offline, fred_load, clock, opener=opener)
    data = build(compute(data, errors, now.date()), previous(out), now)
    # 공개 저장소의 Actions 로그 — 날짜와 정해 둔 사유만(값은 찍지 않는다). 못 받은 칸은 경고 주석으로
    for spec in ITEMS:
        it = data["items"][spec["key"]]
        if it["ok"]:
            print(f"[ai_invest_fetch] {spec['key']} {it['date']} 기준")
        else:
            kept = f" — 직전 값({it['date']} 기준) 유지" if it["stale"] else ""
            annotate(f"AI 투자 참고 {spec['key']} 받지 못함: {it['error']}{kept}")
    try:
        if differs(out, data):
            write(out, data)
    except OSError as e:
        print(f"[ai_invest_fetch] {FILE}를 쓰지 못함: {type(e).__name__}", file=sys.stderr)
        return 1
    return 0 if any(it["ok"] for it in data["items"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
