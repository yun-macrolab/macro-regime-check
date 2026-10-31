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
              private_credit 사모대출(2026-10-30, 비공개 알림에서 옮김) — 연준 Z.1(분기) 잔액·전년비, 비금융기업 부채 중 몫
                            (BOGZ1FL103167205Q / BCNSDODNS), 부채/금융자산(사모대출펀드 BOGZ1FL444190005Q/…090000Q · BDC
                            BOGZ1FL454190005Q/…090003Q), 은행이 펀드·BDC에 빌려준 돈(BOGZ1FL443168000Q + BOGZ1FL453168003Q),
                            미소진 약정(BOGZ1FL442000093Q). 열 줄이 모두 있는 마지막 분기, 1년 전 = 정확히 네 분기 앞
  전력 가격   power         산업용 전력 PPI(BLS WPU0543) · CPI 전기(BLS CUSR0000SEHF01) 전년비 — 월간 10년
  금리 쪽 결과 curve_30_10  미 30년 − 10년 국채 금리차(bp, DGS30 − DGS10) — 주간 5년
  상관        corr60        주식 일간 수익률 × 미 10년 금리 일간 변화의 60영업일 상관 — AI 지수(Nasdaq CTA AI, NASDAQNQINTEL)·
                            S&P 500(SP500 — 규칙 카드 '주가-금리 60영업일 상관'과 같은 계산)·나스닥100 기술(NASDAQNDXTMC), 주간 3년
              corr20        AI 지수 × 10년 금리 20영업일 상관과 우연 범위(±, 상관이 0일 때 95%) — 주간 3년
              partial60     S&P 500을 통제한 60영업일 부분상관(AI 지수·나스닥100 기술) — 주간 3년
              ai_b2         AI 고유 몫 b2(2026-10-30, 비공개 알림에서 옮김) — 2025년부터 해마다 따로 Δ10년(bp) = a + b1·S&P(%) +
                            b2·(AI − S&P)(%), HC1 견고 t. 해·b1·t1·b2·t2·관측일 수·처음·끝 날짜만 싣는다(표 하나, 그래프 없음)
계산은 모두 이 파일이 한다(원본 파이프라인 ai_corr_check.py·ai_invest_block.py와 같은 산식 — 코드는 가져오지 않고 여기서 따로
쓴다). 상관은 fred_fetch.corr_summary와 같은 방식: 두 시계열의 공통 날짜에서 수익률(가격 0인 날은 건너뜀)과 금리 변화를 짝짓는다.
b2의 짝은 ai_corr_check.changes와 같다(S&P·AI·10년 셋의 공통 날짜, 이웃한 두 날 사이 변화, 끝 날짜의 해로 묶는다).

재배포 제한(S&P 500·Nasdaq 지수 — FRED 'copyrighted: pre-approval required'): 원값과 원값을 되살릴 수 있는 파생값(수익률
포함)은 싣지 않는다. 싣는 것은 상관·부분상관과 회귀 계수·t값·관측일 수뿐(규칙 카드의 ρ60과 같은 원칙, render_public.RESTRICTED).
지킴: 상관 칸(bounded)은 값과 점이 모두 −1~1, b2(coef_rows)는 정해 둔 여덟 칸의 해마다 한 줄뿐이고 계수·t값의 크기에 상한을
둔다 — 새로 계산한 값과 직전 파일 모두. 나머지(BEA·Census·BLS·연준·재무부)는 FRED의 공개 자료(public domain: citation
requested)라 값과 FRED 권장 인용을 싣는다. 시리즈 제목·출처는 2026-10-27(사모대출 열 줄은 2026-10-30) FRED 시리즈 쪽에서
확인했다. 이용 조건은 sources[].licence(LICENCE): 사모대출 아홉 줄(BCNSDODNS 밖)은 FRED 시리즈 쪽에 이용 조건 표시가 없어
'board-public-domain (FRED unlabeled)' — 연준 이사회 자료의 공개 정책에 기대고, 인용에 Z.1 이름을 넣는다(Z1_RELEASE).

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
import regime_rules as rr
import render_public as rp

SCHEMA = 1
REPO = os.path.dirname(SCRIPTS)
DEFAULT_OUT = os.path.join(REPO, "data")
DEFAULT_WORK = os.path.join(REPO, ".work")
FILE = "ai_invest.json"
CACHE = "ai_invest"                       # <work>/ai_invest/<ID>.csv

TIMEOUT = 15                              # 요청 하나(연결·한 번 읽기)
BUDGET = 80                               # 수신 전체(초, 요청 30회) — 읽는 동안에도 본다. 워크플로 단계 제한(2분) 안에서 끝나게
MAX_BYTES = 5_000_000                     # 응답 하나의 상한
NUM_ND = 4                                # 문구로 가는 숫자의 소수 자리(문구에서 한 번만 반올림)
PT_ND = 2                                 # 그래프 점의 소수 자리(그래프 글자도 소수 둘째 자리)

CORR_YEARS = 3
MONTHLY_YEARS = 10
CURVE_YEARS = 5
ICT_SINCE = datetime.date(1990, 1, 1)
PEAK_FROM, PEAK_TO = datetime.date(1995, 1, 1), datetime.date(2002, 12, 31)
FIN_SINCE = datetime.date(1985, 1, 1)
HQ_SINCE = datetime.date(2000, 1, 1)      # 고신용 장기 스프레드 그래프 시작
HQ_PCT_FROM = datetime.date(2006, 3, 1)   # 분포 표본 시작 — DGS30 공식 발표 중단(2002-02-18~2006-02-09, FRED 주석) 뒤부터
DGS30_OFF = (datetime.date(2002, 2, 1), datetime.date(2006, 2, 1))   # 그 중단에 걸친 달은 빼고 그린다(FRED에 값이 있어도 출처를 확인 못 함)
HQ_MIN_DAYS = 10                          # 국채 월평균에 필요한 관측일 수(공백 달은 비운다)
SB_N = 252                                # 긴 그림의 상관 창(영업일)
ERAS = [("e1", None, datetime.date(1997, 12, 31)), ("e2", datetime.date(1998, 1, 1), datetime.date(2020, 12, 31)),
        ("e3", datetime.date(2021, 1, 1), None)]           # 경계는 상관 부호가 바뀐 해(사후에 고른 것 — 문구에 적는다)
CELLS = [("I", "근원 PCE 3% 초과만"), ("B", "둘 다"), ("U", "실업률 상승 폭 0.5%p 이상만"), ("N", "둘 다 아님")]
B2_SINCE = datetime.date(2025, 1, 1)      # AI 고유 몫 b2 표본 시작(원본 ai_invest_block.B2_SINCE)
MIN_OLS = 60                              # 회귀 표본이 이보다 적은 해는 싣지 않는다(원본 ai_corr_check.MIN_OLS)
COEF_CAP = 20.0                           # b1·b2(bp / 1%)의 크기 상한 — 지수 값 같은 큰 수가 섞이면 싣지 않는다
T_CAP = 100.0                             # t값의 크기 상한
B2_KEYS = ("year", "b1", "t1", "b2", "t2", "n", "from", "to")   # b2 한 해에 싣는 칸 — 이것뿐

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
    "HQMCB30YRP": ("U.S. Department of the Treasury", "30-Year High Quality Market (HQM) Corporate Bond Par Yield"),
    "HQMCB10YRP": ("U.S. Department of the Treasury", "10-Year High Quality Market (HQM) Corporate Bond Par Yield"),
    "NASDAQCOM": ("Nasdaq, Inc.", "NASDAQ Composite"),
    "PCEPILFE": (rp.FRED_SOURCE["PCEPILFE"], rp.FRED_TITLE["PCEPILFE"]),
    "UNRATE": (rp.FRED_SOURCE["UNRATE"], rp.FRED_TITLE["UNRATE"]),
}
# 사모대출 — 연준 Z.1(분기, 백만 달러). 원본 ai_invest_block.PC와 같은 열 줄. 제목은 2026-10-30 FRED 시리즈 쪽 Suggested Citation 그대로
PC = {"total": "BOGZ1FL893167205Q", "nfc": "BOGZ1FL103167205Q", "nfc_debt": "BCNSDODNS",
      "pdf_liab": "BOGZ1FL444190005Q", "pdf_fa": "BOGZ1FL444090000Q", "bdc_liab": "BOGZ1FL454190005Q",
      "bdc_fa": "BOGZ1FL454090003Q", "pdf_bank": "BOGZ1FL443168000Q", "bdc_bank": "BOGZ1FL453168003Q",
      "dry": "BOGZ1FL442000093Q"}
SOURCES.update({
    "BOGZ1FL893167205Q": (_BOARD, "All Sectors; Private Credit Loans; Liability, Level"),
    "BOGZ1FL103167205Q": (_BOARD, "Nonfinancial Corporate Business; Private Credit Loans; Liability, Level"),
    "BCNSDODNS": (_BOARD, "Nonfinancial Corporate Business; Debt Securities and Loans; Liability, Level"),
    "BOGZ1FL444190005Q": (_BOARD, "Private Debt Funds; Total Liabilities, Level"),
    "BOGZ1FL444090000Q": (_BOARD, "Private Debt Funds; Total Financial Assets, Level"),
    "BOGZ1FL454190005Q": (_BOARD, "Business Development Companies; Total Liabilities, Level"),
    "BOGZ1FL454090003Q": (_BOARD, "Business Development Companies; Total Financial Assets (Balance Sheet), Level"),
    "BOGZ1FL443168000Q": (_BOARD, "Private Debt Funds; Depository Institution Loans N.e.c.; Liability, Level"),
    "BOGZ1FL453168003Q": (_BOARD, "Business Development Companies; Depository Institution Loans N.e.c.; Liability, Level"),
    "BOGZ1FL442000093Q": (_BOARD, "Private Debt Funds; Uncalled Capital Commitments (Dry Powder), Level"),
})
Z1_RELEASE = "Financial Accounts of the United States (Z.1)"     # 사모대출 열 줄의 인용에 넣는 발표 이름
# 재배포 제한 목록 하나 — 공개본의 목록(render_public.RESTRICTED)에 이 화면이 더 쓰는 Nasdaq 지수 둘을 더한다
RESTRICTED = {**rp.RESTRICTED, "NASDAQNQINTEL": "Nasdaq, Inc.", "NASDAQNDXTMC": "Nasdaq, Inc.", "NASDAQCOM": "Nasdaq, Inc."}
SERIES = list(SOURCES)                    # 사모대출 열 줄은 끝 — 수신 시간이 모자라면 그쪽부터 빠진다
# 이용 조건(sources[].licence). 사모대출 아홉 줄은 FRED 시리즈 쪽 license가 일반 법적 고지(/legal/)뿐이다(2026-10-30 JSON-LD)
UNLABELED = "board-public-domain (FRED unlabeled)"
LICENCE = {sid: "restricted" if sid in RESTRICTED else "public-domain" for sid in SOURCES}
LICENCE.update({sid: UNLABELED for sid in PC.values() if sid != "BCNSDODNS"})

NOTICE = ("이 사이트의 규칙 판정에 쓰지 않는 참고 자료다. 충족·미충족이 없고 상태를 판정하지 않는다. 값의 크기나 방향을 "
          "시장 전망으로 읽지 않는다.")
RESTRICTED_NOTICE = ("S&P 500·Nasdaq 지수는 재배포가 제한된 자료라 지수 값은 싣지 않는다. 상관·부분상관과 그 평균은 "
                     "macro-regime-check가 그 자료(FRED 경유)로 계산한 값이다.")
COMPUTED_NOTICE = "비율·전년비·금리차·분포 숫자는 macro-regime-check가 원자료로 계산한 값이다."
COEF_NOTICE = ("S&P 500·Nasdaq 지수는 재배포가 제한된 자료라 지수 값과 수익률은 싣지 않는다. 회귀 계수·t값·관측일 수는 "
               "macro-regime-check가 그 자료(FRED 경유)로 계산한 값이다.")
Z1_NOTICE = ("사모대출 시리즈는 FRED 시리즈 쪽에 이용 조건 표시가 없다 — 연준 이사회 자료의 공개 정책에 따라 출처(Z.1, FRED 경유)를 "
             "밝혀 싣는다.")
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


def calc_private_credit(S):
    """연준 Z.1 사모대출 — 열 시리즈가 모두 있는 마지막 분기(Z.1은 한 번에 나온다). 1년 전 = 정확히 네 분기 앞.
    원본 ai_invest_block.calc_private_credit과 같은 산식. 그래프는 비금융기업 부채 중 몫(두 시리즈가 다 있는 분기, 잔액이 0이
    아닌 첫 분기부터)."""
    s = {k: {_qkey(d): (d, v) for d, v in S[sid]} for k, sid in PC.items()}
    common = sorted(set.intersection(*(set(v) for v in s.values())))
    if not common:
        raise ItemError("format")
    q = common[-1]
    at = lambda k, qq: s[k][qq][1] if qq in s[k] else None
    ratio = lambda a, b, qq: (at(a, qq) / at(b, qq) * 100) if at(a, qq) is not None and at(b, qq) else None
    yoy = lambda v1, v0: (v1 / v0 - 1) * 100 if v1 is not None and v0 else None
    bank = lambda qq: (at("pdf_bank", qq) + at("bdc_bank", qq)) if at("pdf_bank", qq) is not None \
        and at("bdc_bank", qq) is not None else None
    nz = [qq for qq, (_, v) in s["total"].items() if v]
    first = min(nz) if nz else q
    share = [(s["nfc"][qq][0], ratio("nfc", "nfc_debt", qq)) for qq in sorted(s["nfc"]) if first <= qq <= q]
    return {"date": _iso(s["total"][q][0]),
            "values": {"total_tn": _r(at("total", q) / 1e6), "total_yoy": _r(yoy(at("total", q), at("total", q - 4))),
                       "share": _r(ratio("nfc", "nfc_debt", q)), "share_1y": _r(ratio("nfc", "nfc_debt", q - 4)),
                       "pdf_lev": _r(ratio("pdf_liab", "pdf_fa", q)), "pdf_lev_1y": _r(ratio("pdf_liab", "pdf_fa", q - 4)),
                       "bdc_lev": _r(ratio("bdc_liab", "bdc_fa", q)), "bdc_lev_1y": _r(ratio("bdc_liab", "bdc_fa", q - 4)),
                       "bank_bn": _r(bank(q) / 1e3), "bank_yoy": _r(yoy(bank(q), bank(q - 4))),
                       "dry_bn": _r(at("dry", q) / 1e3), "dry_yoy": _r(yoy(at("dry", q), at("dry", q - 4))),
                       "from": _iso(s["total"][min(nz)][0]) if nz else None},
            "lines": {"share": [[_iso(d), _r(v, PT_ND)] for d, v in share]}}


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


def b2_rows(S, since=B2_SINCE):
    """ai_corr_check.changes와 같은 짝: S&P·AI·10년 셋의 공통 날짜에서 이웃한 두 날 사이 (끝 날짜, S&P %, AI %, Δ10년 bp).
    앞 날 가격이 0이면 건너뛴다. 끝 날짜가 since 이후인 것만(첫 줄은 그 앞 날에서 시작할 수 있다)."""
    sp, ax, y = dict(S["SP500"]), dict(S["NASDAQNQINTEL"]), dict(S["DGS10"])
    days = sorted(set(sp) & set(ax) & set(y))
    out = []
    for d0, d1 in zip(days, days[1:]):
        if sp[d0] == 0 or ax[d0] == 0 or d1 < since:
            continue
        out.append((d1, (sp[d1] / sp[d0] - 1) * 100, (ax[d1] / ax[d0] - 1) * 100, (y[d1] - y[d0]) * 100))
    return out


def _inv(m):
    """작은 정방행렬의 역행렬(가우스-조르단, 원본 ai_corr_check._inv). 특이하면 None."""
    k = len(m)
    a = [row[:] + [1.0 if i == j else 0.0 for j in range(k)] for i, row in enumerate(m)]
    for c in range(k):
        p = max(range(c, k), key=lambda r: abs(a[r][c]))
        if abs(a[p][c]) < 1e-12:
            return None
        a[c], a[p] = a[p], a[c]
        piv = a[c][c]
        a[c] = [v / piv for v in a[c]]
        for r in range(k):
            if r != c and a[r][c] != 0:
                f = a[r][c]
                a[r] = [v - f * w for v, w in zip(a[r], a[c])]
    return [row[k:] for row in a]


def ols(y, X):
    """최소제곱 + HC1(화이트) 견고 se(원본 ai_corr_check.ols). X는 상수항을 포함한 행 목록. {b, se, n} 또는 None(표본 부족·특이)."""
    if not y or not X:
        return None
    n, k = len(y), len(X[0])
    if n < max(MIN_OLS, k + 10):
        return None
    xtx = [[sum(r[i] * r[j] for r in X) for j in range(k)] for i in range(k)]
    inv = _inv(xtx)
    if inv is None:
        return None
    xty = [sum(r[i] * v for r, v in zip(X, y)) for i in range(k)]
    b = [sum(inv[i][j] * xty[j] for j in range(k)) for i in range(k)]
    e = [v - sum(bi * xi for bi, xi in zip(b, r)) for r, v in zip(X, y)]
    meat = [[sum(r[i] * r[j] * ei * ei for r, ei in zip(X, e)) for j in range(k)] for i in range(k)]
    tmp = [[sum(inv[i][m] * meat[m][j] for m in range(k)) for j in range(k)] for i in range(k)]
    cov = [[sum(tmp[i][m] * inv[m][j] for m in range(k)) * n / (n - k) for j in range(k)] for i in range(k)]
    return {"b": b, "se": [math.sqrt(max(cov[i][i], 0.0)) for i in range(k)], "n": n}


def calc_ai_b2(S):
    """원본 ai_invest_block.calc_ai_b2 — B2_SINCE 해부터 해마다 따로 Δ10년(bp) = a + b1·S&P(%) + b2·(AI − S&P)(%), HC1.
    표본이 MIN_OLS보다 적은 해는 싣지 않는다. 해마다 따로 맞추는 까닭: 묶으면 S&P 기울기를 여러 해에 하나로 강제해 b2가 낮게
    나온다. 싣는 것은 B2_KEYS뿐(지수 값·수익률은 없다)."""
    rows = b2_rows(S)
    by = {}
    for r in rows:
        by.setdefault(r[0].year, []).append(r)
    years = []
    for yr, sub in sorted(by.items()):
        fit = ols([dy for _, _, _, dy in sub], [[1.0, sp, a - sp] for _, sp, a, _ in sub])
        if not fit:
            continue
        b, se = fit["b"], fit["se"]
        years.append({"year": yr, "b1": _r(b[1]), "t1": _r(b[1] / se[1]) if se[1] else None,
                      "b2": _r(b[2]), "t2": _r(b[2] / se[2]) if se[2] else None, "n": fit["n"],
                      "from": _iso(sub[0][0]), "to": _iso(sub[-1][0])})
    if not years:
        raise ItemError("format")
    return {"date": _iso(rows[-1][0]), "values": {"years": years}, "lines": {}}


def monthly_mean(series, min_days=HQ_MIN_DAYS):
    """일간 → [(그 달 1일, 월평균)] — 관측일이 min_days 미만인 달은 뺀다(국채 공백 달을 0이나 일부 날로 채우지 않게)."""
    by = {}
    for d, v in series:
        by.setdefault((d.year, d.month), []).append(v)
    return [(datetime.date(y, m, 1), sum(vs) / len(vs)) for (y, m), vs in sorted(by.items()) if len(vs) >= min_days]


def _spread_months(hqm, tsy):
    """HQM par(월간, 그 달 평균) − 같은 달 국채 월평균, bp."""
    t = dict(monthly_mean(tsy))
    return [(d, (v - t[d]) * 100) for d, v in hqm if d in t]


def calc_hq_spread(S):
    s30 = [(d, v) for d, v in _spread_months(S["HQMCB30YRP"], S["DGS30"]) if not DGS30_OFF[0] <= d <= DGS30_OFF[1]]
    s10 = _spread_months(S["HQMCB10YRP"], S["DGS10"])
    if not s30 or not s10:
        raise ItemError("format")
    d30, v30 = s30[-1]
    hist = [v for d, v in s30 if d >= HQ_PCT_FROM]
    return {"date": _iso(max(d30, s10[-1][0])),
            "values": {"s30": _r(v30), "s30_date": _iso(d30), "s30_1y": _r(_year_ago(s30)),
                       "le30": _r(sum(x <= v30 for x in hist) / len(hist) * 100) if len(hist) >= 24 else None,
                       "n30": len(hist), "pct_from": _iso(HQ_PCT_FROM),
                       "s10": _r(s10[-1][1]), "s10_date": _iso(s10[-1][0]), "s10_1y": _r(_year_ago(s10))},
            "lines": {"s30": _monthly_points(s30, HQ_SINCE), "s10": _monthly_points(s10, HQ_SINCE)}}


def rolling_corr_fast(px, y, n):
    """rolling_corr와 같은 값(공통 날짜·같은 짝)을 합계를 밀어 가며 — 1972년 이후 일간 252영업일 창 수만 개라.
    부동소수 누적을 막으려고 n번마다 합계를 처음부터 다시 잰다. 분산이 사실상 0이면 None(ff.pearson과 같게)."""
    pr = pairs(px, y)
    if len(pr) < n:
        return []
    xs, ys = [r for _, r, _ in pr], [dy for _, _, dy in pr]
    out = []
    for e in range(n, len(pr) + 1):
        if (e - n) % n == 0:
            a, b = xs[e - n:e], ys[e - n:e]
            sx, sy = sum(a), sum(b)
            sxx, syy, sxy = sum(v * v for v in a), sum(v * v for v in b), sum(u * v for u, v in zip(a, b))
        else:
            xo, yo, xn, yn = xs[e - n - 1], ys[e - n - 1], xs[e - 1], ys[e - 1]
            sx += xn - xo
            sy += yn - yo
            sxx += xn * xn - xo * xo
            syy += yn * yn - yo * yo
            sxy += xn * yn - xo * yo
        vx, vy = sxx - sx * sx / n, syy - sy * sy / n
        out.append((pr[e - 1][0], (sxy - sx * sy / n) / math.sqrt(vx * vy) if vx > 1e-18 and vy > 1e-18 else None))
    return out


def _upto(series, d):
    return series[:bisect.bisect_right(series, (d, float("inf")))]


def month_states(S, since):
    """{달 번호: (값, 조건)} 둘 — 근원 PCE 전년비 > 3(규칙 '근원 물가'의 미충족 쪽)과 실업률 상승 폭 ≥ 0.5(규칙 '실업률 상승 폭'
    충족). 카드와 같은 함수(ff.yoy 같은 달 · ff.sahm_stats)와 같은 비교(소수 6자리 반올림 뒤). 자료 달 기준(발표 시차 없음)."""
    infl, unemp = {}, {}
    pce, un = S["PCEPILFE"], S["UNRATE"]
    for d, _ in pce:
        if d >= since:
            r = ff.yoy(_upto(pce, d), same_month=True)
            if r:
                infl[_mkey(d)] = (r["value"], round(r["value"], 6) > rr.TH["core_pce_split"])
    for d, _ in un:
        if d >= since:
            r = ff.sahm_stats(_upto(un, d))
            if r:
                unemp[_mkey(d)] = (r["value"], round(r["value"], 6) >= rr.TH["unrate_rise"])
    return infl, unemp


def _at(states, keys, mk):
    """mk 이하 가장 늦은 달의 상태 — 시리즈 안의 빠진 달(UNRATE 2025-10 등)만 그 전 달로 잇는다. 마지막 자료 달 뒤(아직
    발표 전)는 None: 띠·표 모두 '자료 달 기준'이라 발표되지 않은 달을 조건이 맞은 달로 세지 않는다."""
    i = bisect.bisect_right(keys, mk) - 1
    return states[keys[i]] if i >= 0 and mk <= keys[-1] else None


def _era(d):
    for e, lo, hi in ERAS:
        if (lo is None or d >= lo) and (hi is None or d <= hi):
            return e
    return None


def _cell(i, u):
    return "B" if i and u else "I" if i else "U" if u else "N"


def _mday(mk, last=False):
    """달 번호 → 그 달 1일(또는 말일)."""
    if not last:
        return datetime.date(mk // 12, mk % 12 + 1, 1)
    return datetime.date((mk + 1) // 12, (mk + 1) % 12 + 1, 1) - datetime.timedelta(days=1)


def _ranges(flags):
    """[(달 번호, 조건)] 차례대로 → 조건이 이어진 달들의 [[첫 달 1일, 끝 달 말일]](달이 건너뛰면 끊는다)."""
    out, run = [], None
    for mk, on in flags:
        if on and run and mk == run[1] + 1:
            run[1] = mk
        else:
            if run:
                out.append(run)
            run = [mk, mk] if on else None
    if run:
        out.append(run)
    return [[_iso(_mday(a)), _iso(_mday(b, True))] for a, b in out]


def _month_end_points(vals, nd=PT_ND):
    """일간 [(날짜, 값)] → 달마다 마지막 관측 [[날짜, 값]]."""
    by = {}
    for d, v in vals:
        by[(d.year, d.month)] = (d, v)
    return [[_iso(d), _r(v, nd)] for d, v in (by[k] for k in sorted(by))]


def calc_sb_long(S):
    rho = rolling_corr_fast(S["NASDAQCOM"], S["DGS10"], SB_N)
    sp = rolling_corr_fast(S["SP500"], S["DGS10"], SB_N)
    lr = _last(rho)
    if not lr:
        raise ItemError("format")
    first = next(d for d, v in rho if v is not None)
    infl, unemp = month_states(S, datetime.date(first.year - 2, 1, 1))
    ik, uk = sorted(infl), sorted(unemp)
    if not ik or not uk:
        raise ItemError("format")
    acc = {}                                      # (시대, 칸) → [합, 일수]
    for d, v in rho:
        if v is None:
            continue
        i, u = _at(infl, ik, _mkey(d)), _at(unemp, uk, _mkey(d))
        if i is None or u is None:
            continue
        c = _cell(i[1], u[1])
        for e in (_era(d), "all"):
            a = acc.setdefault((e, c), [0.0, 0])
            a[0] += v
            a[1] += 1
    months = range(_mkey(first), _mkey(lr[0]) + 1)
    seq = []                                      # 달마다 (시대, 칸) — 이어진 구간 수를 센다
    for mk in months:
        i, u = _at(infl, ik, mk), _at(unemp, uk, mk)
        if i is not None and u is not None:
            seq.append((mk, _era(_mday(mk)), _cell(i[1], u[1])))
    runs = {}
    for j, (mk, e, c) in enumerate(seq):
        if j == 0 or seq[j - 1][1:] != (e, c) or seq[j - 1][0] != mk - 1:
            runs[(e, c)] = runs.get((e, c), 0) + 1
        if j == 0 or seq[j - 1][2] != c or seq[j - 1][0] != mk - 1:
            runs[("all", c)] = runs.get(("all", c), 0) + 1
    values = {"rho": _r(lr[1]), "first": _iso(first)}
    ls = _last(sp)
    values.update(sp=_r(ls and ls[1]), sp_date=ls and _iso(ls[0]))
    pi, ui = infl[ik[-1]], unemp[uk[-1]]
    values.update(pce=_r(pi[0]), pce_month=_iso(_mday(ik[-1])), ur=_r(ui[0]), ur_month=_iso(_mday(uk[-1])))
    for e in [x[0] for x in ERAS] + ["all"]:
        for c, _ in CELLS:
            tot, n = acc.get((e, c), [0.0, 0])
            values.update({f"m_{e}_{c}": _r(tot / n) if n else None, f"d_{e}_{c}": n, f"r_{e}_{c}": runs.get((e, c), 0)})
    chart_months = list(months)
    return {"date": _iso(lr[0]), "values": values,
            "lines": {"nasdaq": _month_end_points([(d, v) for d, v in rho if d >= first]),
                      "sp": _month_end_points([(d, v) for d, v in sp if v is not None])},
            "bands": {"infl": _ranges([(mk, bool(_at(infl, ik, mk) and _at(infl, ik, mk)[1])) for mk in chart_months]),
                      "unemp": _ranges([(mk, bool(_at(unemp, uk, mk) and _at(unemp, uk, mk)[1])) for mk in chart_months])}}


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
    {"key": "hq_spread", "channel": "finance", "title": "고신용 장기 회사채 − 국채 금리차 (par)",
     "series": ["HQMCB30YRP", "HQMCB10YRP", "DGS30", "DGS10"], "calc": calc_hq_spread, "unit": "bp", "years": 26,
     "zero": False, "note": "2000년 이후 · 월간 · 재무부 HQM 회사채 par 수익률 − 같은 달 국채 금리 평균",
     "values": {"s30": "num", "s30_date": "day", "s30_1y": "num?", "le30": "num?", "n30": "int", "pct_from": "day",
                "s10": "num", "s10_date": "day", "s10_1y": "num?"},
     "ends": ["s30_date", "s10_date"],
     "lines": [_l("s30", "30년", "main", ["HQMCB30YRP", "DGS30"]), _l("s10", "10년", "series", ["HQMCB10YRP", "DGS10"])]},
    {"key": "private_credit", "channel": "finance", "title": "사모대출 — 잔액·비금융기업 부채 중 몫·레버리지 (연준 Z.1)",
     "series": list(PC.values()), "calc": calc_private_credit, "unit": "%", "years": 14, "zero": False,
     "note": "분기 · 그래프는 비금융기업 부채(부채증권+대출) 중 사모대출 몫",
     "values": {"total_tn": "num", "total_yoy": "num?", "share": "num", "share_1y": "num?", "pdf_lev": "num",
                "pdf_lev_1y": "num?", "bdc_lev": "num", "bdc_lev_1y": "num?", "bank_bn": "num", "bank_yoy": "num?",
                "dry_bn": "num", "dry_yoy": "num?", "from": "day?"},
     "lines": [_l("share", "비금융기업 부채 중 사모대출", "main", ["BOGZ1FL103167205Q", "BCNSDODNS"])]},
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
    {"key": "ai_b2", "channel": "corr", "title": "AI 고유 몫 b2 — 해마다 회귀 (측정 기록, 예측 아님)",
     "series": ["SP500", "NASDAQNQINTEL", "DGS10"], "calc": calc_ai_b2, "unit": "bp", "years": 2, "zero": True,
     "note": "2025년부터 해마다 · 일간 · Δ10년(bp) = a + b1·S&P 500(%) + b2·(AI − S&P 500)(%) · HC1",
     "values": {"years": "coef_rows"}, "bounded": True, "notice": COEF_NOTICE, "lines": []},
]
ITEMS.append(
    {"key": "sb_long", "channel": "corr", "title": "주가-금리 252영업일 상관과 물가·고용 조건 — 1972년 이후",
     "series": ["NASDAQCOM", "SP500", "DGS10", "PCEPILFE", "UNRATE"], "calc": calc_sb_long, "unit": "", "years": 54,
     "zero": True, "note": "월말 값 · 양(+)이면 주가와 금리가 같은 방향 · 아래 띠는 조건이 맞은 달(자료 달 기준)",
     "values": {"rho": "num", "first": "day", "sp": "num?", "sp_date": "day?", "pce": "num", "pce_month": "day", "ur": "num",
                "ur_month": "day",
                **{f"{k}_{e}_{c}": t for e in ("e1", "e2", "e3", "all") for c in "IBUN"
                   for k, t in (("m", "num?"), ("d", "int"), ("r", "int"))}},
     "ends": ["sp_date", "pce_month", "ur_month"], "bounded": True, "free": ["pce", "ur"],
     "lines": [_l("nasdaq", "나스닥 종합", "main", ["NASDAQCOM", "DGS10"]), _l("sp", "S&P 500", "series", ["SP500", "DGS10"])],
     "bands": [("infl", "근원 PCE 전년비 3% 초과"), ("unemp", "실업률 상승 폭 0.5%p 이상")]})
BY_KEY = {it["key"]: it for it in ITEMS}


# ---------- 문구 ----------

def _f(v, nd=2, sign=False, unit=""):
    if v is None:
        return "—"
    s = f"{v:+.{nd}f}" if sign else f"{v:.{nd}f}"
    if float(s) == 0:
        s = f"{0:.{nd}f}"
    return s + unit


def _eok(bn):
    """10억 달러 단위 → '3,251억 달러' · 1조 이상이면 '1.20조 달러'(원본 ai_invest_block._eok — 반올림한 값으로 가른다)."""
    if bn is None:
        return "—"
    return f"{bn / 1000:.2f}조 달러" if round(bn * 10) >= 10000 else f"{bn * 10:,.0f}억 달러"


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
    if key == "private_credit":
        start = qlabel(v["from"]) if v["from"] else "—"
        return (f"{qlabel(date)} 잔액 {_f(v['total_tn'], 2)}조 달러 (전년비 {_f(v['total_yoy'], 1, True, '%')}) · "
                f"비금융기업 부채 중 {_f(v['share'], 1, unit='%')} (1년 전 {_f(v['share_1y'], 1, unit='%')}) · "
                f"부채/금융자산 사모대출펀드 {_f(v['pdf_lev'], 0, unit='%')} (1년 전 {_f(v['pdf_lev_1y'], 0, unit='%')}) · "
                f"BDC {_f(v['bdc_lev'], 0, unit='%')} (1년 전 {_f(v['bdc_lev_1y'], 0, unit='%')}) · "
                f"은행이 펀드·BDC에 빌려준 돈 {_eok(v['bank_bn'])} (전년비 {_f(v['bank_yoy'], 1, True, '%')}) · "
                f"미소진 약정 {_eok(v['dry_bn'])} (전년비 {_f(v['dry_yoy'], 1, True, '%')})",
                [f"연준 Z.1의 사모대출 추정({start}부터) — 분기마다 과거 값이 고쳐진다. 비금융기업 몫 = 비금융기업의 사모대출 ÷ "
                 "비금융기업 부채(부채증권+대출).",
                 "부채/금융자산은 Z.1 대차대조표의 총부채 ÷ 금융자산 — 펀드 레버리지의 대략이다(총부채의 구성은 나눠 보지 않았다).",
                 "은행이 펀드·BDC에 빌려준 돈 = 예금기관 대출(사모대출펀드 + BDC) — 은행과의 연결 정도. 미소진 약정 = 투자자가 "
                 "약정했지만 아직 부르지 않은 자본(앞으로 나갈 수 있는 대출 여력).",
                 "사모대출 전체라 AI·데이터센터 금융만 따로 보이지 않는다. 1년 전은 정확히 네 분기 앞이다."])
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
    if key == "ai_b2":
        ys = v["years"]
        per = " · ".join(f"{y['year']}{'(~' + y['to'][5:] + ')' if y['to'][:4] == date[:4] else ''} "
                         f"{_f(y['b2'], 2, True, 'bp')} (t {_f(y['t2'], 1, True)}, {y['n']}일)" for y in ys)
        return (f"AI 지수가 S&P 500보다 1%p 더 오른 날의 10년 금리 변화(b2) {per} — 측정 기록, 예측 아님",
                ["Δ10년(bp) = a + b1·S&P 500(%) + b2·(AI − S&P 500)(%), HC1 견고 표준오차, 세 시리즈의 공통 관측일, 해마다 따로 "
                 "맞춘다(묶으면 S&P 500 기울기를 여러 해에 하나로 강제해 b2가 낮게 나온다). b1(S&P 500과 AI 지수가 함께 1% 오른 "
                 "날): " + " · ".join(f"{y['year']} {_f(y['b1'], 2, True, 'bp')} (t {_f(y['t1'], 1, True)})" for y in ys) + ".",
                 "나스닥100 기술 섹터를 먼저 넣으면 AI 지수의 추가 몫은 거의 남지 않았다(2026-10-27 측정) — 대형 기술주 공통 요인과 "
                 "겹친다. 한 해 치 표본이라 계수의 오차가 크다 — t값과 함께 본다.",
                 "국채 가격 기준으로 보면 부호가 반대다 — 여기서 양(+)이면 AI 지수가 더 오른 날 금리가 올랐다(국채 가격은 내렸다)."])
    if key == "hq_spread":
        d10 = "" if v["s10_date"] == v["s30_date"] else f" ({mlabel(v['s10_date'])})"
        extra = []
        if v["le30"] is not None:
            extra.append(f"30년은 {v['pct_from'][:7]} 이후 {v['n30']}개월 가운데 이 값 이하인 달이 {_f(v['le30'], 0, unit='%')}다"
                         "(낮을수록 금리차가 좁다).")
        return (f"{mlabel(v['s30_date'])} 30년 {_f(v['s30'], 0, unit='bp')} (1년 전 {_f(v['s30_1y'], 0, unit='bp')}) · "
                f"10년 {_f(v['s10'], 0, unit='bp')}{d10} (1년 전 {_f(v['s10_1y'], 0, unit='bp')})",
                extra + ["재무부 HQM 곡선(AAA·AA·A 등급 회사채)의 par 수익률에서 같은 달 국채 금리(일간 값의 월평균)를 뺀 값이다. "
                         "고신용 회사채 전체의 값이라 대형 기술 기업만의 값이 아니다(BBB 이하 회사채는 들어가지 않는다).",
                         "par끼리 견준다 — 현물 금리를 쓰면 곡선 모양이 섞인다. 30년 국채 금리는 2002-02-18~2006-02-09에 "
                         "공식 발표가 중단됐다(FRED 주석) — 30년 선은 그 기간을 빼고 그린다."])
    if key == "sb_long":
        sp = (f" · S&P 500 {_f(v['sp'], sign=True)}{_asof(v['sp_date'], date)}" if v["sp"] is not None else "")
        extra = ["주가 일간 수익률 × 10년 금리 일간 변화의 252영업일 상관이다. 양(+)이면 주가와 금리가 같은 방향(주가와 국채 "
                 "가격은 반대 — 채권이 주식을 헤지), 음(−)이면 주가와 국채 가격이 같은 방향이다.",
                 "아래 띠는 이 사이트의 두 규칙 조건이다: 근원 PCE 전년비 3% 초과(규칙 '근원 물가' 미충족 쪽), 실업률 3개월 평균 "
                 "상승 폭 0.5%p 이상(규칙 '실업률 상승 폭' 충족). 자료 달 기준이고 발표 시차는 넣지 않았다(현재 개정치).",
                 "표는 두 조건의 조합별 252영업일 상관 평균이다(괄호는 일수 · 이어진 구간 수). 시대 경계(1998·2021년)는 상관의 "
                 "부호가 바뀐 해를 보고 정했다. 구간 수가 적은 칸의 평균은 몇 번의 시기에 기댄다."]
        if v["d_e2_I"] == 0 and v["d_e2_B"] == 0:
            extra.append("1998~2020년에는 근원 PCE 전년비가 3%를 넘은 달이 없다 — 칸끼리 견줄 때 시대가 섞여 있다는 점을 함께 본다.")
        extra += ["과거 자료에서 두 조건의 변화가 상관 부호의 변화보다 일정하게 앞서지는 않았다 — 이 그림은 앞날을 가리키지 않는다.",
                  "긴 기간의 주가는 나스닥 종합(기술주 비중이 크다)을 썼다. S&P 500은 FRED에 최근 10년만 있어 그 기간만 함께 그렸다."]
        return (f"{date} 나스닥 종합 {_f(v['rho'], sign=True)}{sp} · 근원 PCE 전년비 {_f(v['pce'], unit='%')}"
                f"({mlabel(v['pce_month'])}) · 실업률 상승 폭 {_f(v['ur'], unit='%p')}({mlabel(v['ur_month'])})", extra)
    raise KeyError(key)


def table_of(key, v):
    """sb_long의 시대 × 조건 표 · ai_b2의 해마다 계수 표 — 숫자에서 만든다(정해 둔 머리글 + 숫자). 다른 칸은 None."""
    if key == "ai_b2":
        return {"caption": "해마다 회귀 계수(bp는 1%당 10년 금리 변화, t는 HC1)",
                "columns": ["해", "b2 (bp)", "t (b2)", "b1 (bp)", "t (b1)", "관측일", "기간"],
                "rows": [[str(y["year"]), _f(y["b2"], 2, True), _f(y["t2"], 1, True), _f(y["b1"], 2, True),
                          _f(y["t1"], 1, True), f"{y['n']}", f"{y['from']} ~ {y['to']}"] for y in v["years"]]}
    if key != "sb_long":
        return None
    label = {"e1": f"{v['first'][:4]}~1997", "e2": "1998~2020", "e3": "2021~", "all": "전체"}

    def cell(e, c):
        m, d, r = v[f"m_{e}_{c}"], v[f"d_{e}_{c}"], v[f"r_{e}_{c}"]
        return "—" if not d or m is None else f"{_f(m, sign=True)} ({d:,}일 · {r}구간)"
    return {"caption": "조건 조합별 252영업일 상관 평균(시대별)",
            "columns": ["시대"] + [name for _, name in CELLS],
            "rows": [[label[e]] + [cell(e, c) for c, _ in CELLS] for e in ("e1", "e2", "e3", "all")]}


_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December")


def citation(sid, retrieved):
    """FRED 권장 인용 형식(render_public.citation과 같은 꼴). 날짜는 지금 값을 처음 받은 날. 사모대출 열 줄은 출처 뒤에 Z.1
    발표 이름을 넣는다."""
    d = datetime.date.fromisoformat(retrieved)
    src, title = SOURCES[sid]
    rel = f"{Z1_RELEASE}, " if sid in PC.values() else ""
    return (f"{src}, {rel}{title} [{sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; "
            f"{rp.FRED_URL.format(sid)}, {_MONTHS[d.month - 1]} {d.day}, {d.year}.")


def sources_of(spec, retrieved=None):
    out = []
    for sid in spec["series"]:
        s = {"series": sid, "name": SOURCES[sid][0], "url": rp.FRED_URL.format(sid), "restricted": sid in RESTRICTED,
             "licence": LICENCE[sid]}
        if retrieved:
            s["citation"] = citation(sid, retrieved)
        out.append(s)
    return out


def source_note(spec):
    names = list(dict.fromkeys(SOURCES[sid][0] for sid in spec["series"]))
    return "자료: " + " · ".join(names) + " (via FRED) · 선은 macro-regime-check가 이 자료로 계산한 값"


def notices(spec):
    if spec.get("notice"):
        return [spec["notice"]]
    out = [RESTRICTED_NOTICE] if any(s in RESTRICTED for s in spec["series"]) else [COMPUTED_NOTICE]
    if any(LICENCE[s] == UNLABELED for s in spec["series"]):
        out.append(Z1_NOTICE)
    return out


def present(key, core, retrieved):
    """숫자(core) → 칸 전체(문구 · 그래프 · 고지 · 출처). 이어 실을 때도 이걸로 다시 만든다."""
    spec = BY_KEY[key]
    line, extra = texts(key, core["values"], core["date"])
    derived = any(s in RESTRICTED for s in spec["series"])
    out = {"key": key, "channel": spec["channel"], "name": spec["title"], "date": core["date"],
           "values": core["values"], "retrieved": retrieved, "line": line, "extra": extra,
           "notices": notices(spec), "sources": sources_of(spec, retrieved)}
    if spec["lines"]:                                    # 선이 없는 칸(ai_b2 — 표만)은 그래프를 싣지 않는다
        chart = {"key": f"ai_{key}", "title": spec["title"], "unit": spec["unit"], "years": spec["years"],
                 "zero": spec["zero"], "threshold": None, "note": spec["note"], "source_note": source_note(spec),
                 "notices": [],
                 "lines": [{**ln, "derived": derived, "points": core["lines"][ln["key"]]} for ln in spec["lines"]]}
        if spec.get("bands"):
            chart["bands"] = [{"key": k, "label": label, "ranges": core["bands"][k]} for k, label in spec["bands"]]
        out["chart"] = chart
    table = table_of(key, core["values"])
    if table:
        out["table"] = table
    return out


# ---------- 직전 파일 ----------

def _is_day(v):
    try:
        return (isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) is not None
                and datetime.date.fromisoformat(v) is not None)
    except ValueError:
        return False


def _is_num(v):
    return type(v) in (int, float) and v == v and abs(v) != float("inf")


def coef_rows_ok(rows):
    """b2 표의 지킴(재배포 제한 지수로 만든 회귀) — 해마다 한 줄, 칸은 B2_KEYS뿐, 해는 늘어나는 차례, 계수 |b| ≤ COEF_CAP,
    |t| ≤ T_CAP, 관측일 수 MIN_OLS~366, 처음·끝 날짜는 그해 안. 지수 값·수익률 열이 섞이거나 칸이 늘면 싣지 않는다."""
    if not isinstance(rows, list) or not rows:
        return False
    last = None
    for y in rows:
        if not isinstance(y, dict) or set(y) != set(B2_KEYS):
            return False
        yr = y["year"]
        if type(yr) is not int or (last is not None and yr <= last):
            return False
        last = yr
        if not all(_is_num(y[k]) and abs(y[k]) <= COEF_CAP for k in ("b1", "b2")):
            return False
        if not all(y[k] is None or (_is_num(y[k]) and abs(y[k]) <= T_CAP) for k in ("t1", "t2")):
            return False
        if type(y["n"]) is not int or not MIN_OLS <= y["n"] <= 366:
            return False
        if not (_is_day(y["from"]) and _is_day(y["to"]) and y["from"] <= y["to"]
                and y["from"][:4] == y["to"][:4] == f"{yr:04d}"):
            return False
    return True


_KIND = {"num": _is_num, "num?": lambda v: v is None or _is_num(v), "day": _is_day,
         "day?": lambda v: v is None or _is_day(v), "int": lambda v: type(v) is int and v >= 0,
         "coef_rows": coef_rows_ok}


def _in_bounds(spec, vals, lines):
    """재배포 제한 지수로 만든 칸이면 값(free 밖)과 점이 모두 −1~1 — 지수 수준 같은 값이 섞여 들어오면 싣지 않는다."""
    if not spec.get("bounded"):
        return True
    free = set(spec.get("free", ()))
    nums = [vals[k] for k, t in spec["values"].items() if t in ("num", "num?") and k not in free]
    nums += [p[1] for pts in lines.values() for p in pts]
    return all(x is None or abs(x) <= 1 for x in nums)


def values_ok(spec, vals, lines):
    """값·선의 꼴과 지킴(_in_bounds·coef_rows) — 직전 파일을 이어 실을 때와 새로 계산한 값을 쓸 때 모두 본다."""
    return (isinstance(vals, dict) and set(vals) == set(spec["values"])
            and all(_KIND[t](vals[k]) for k, t in spec["values"].items())
            and isinstance(lines, dict) and set(lines) == {ln["key"] for ln in spec["lines"]}
            and all(isinstance(p, list) and len(p) == 2 and _is_day(p[0]) and (p[1] is None or _is_num(p[1]))
                    for pts in lines.values() for p in (pts if isinstance(pts, list) else [None]))
            and _in_bounds(spec, vals, lines))


def core_of(item, key):
    """직전 파일의 칸 → (core, 받은 날) 또는 None(없거나 꼴이 어긋남 — 이어 실을 값이 없는 것으로 본다)."""
    spec = BY_KEY[key]
    try:
        vals = item["values"]
        lines = {ln["key"]: ln["points"] for ln in item["chart"]["lines"]} if spec["lines"] else {}
        chart = item.get("chart")
        ok = (_is_day(item["date"]) and _is_day(item["retrieved"]) and values_ok(spec, vals, lines)
              and (spec["lines"] or chart is None))
        bands = None
        if spec.get("bands"):
            bands = {b["key"]: b["ranges"] for b in chart["bands"]}
            ok = ok and set(bands) == {k for k, _ in spec["bands"]} and all(
                isinstance(rs, list) and all(isinstance(r, list) and len(r) == 2 and _is_day(r[0]) and _is_day(r[1])
                                             and r[0] <= r[1] for r in rs) for rs in bands.values())
        texts(key, vals, item["date"])                    # 문구·표를 다시 만들 수 있어야 한다
        table_of(key, vals)
    except (KeyError, TypeError, IndexError, AttributeError, ValueError):
        return None
    if not ok:
        return None
    core = {"date": item["date"], "values": dict(vals), "lines": lines}
    if bands is not None:
        core["bands"] = bands
    return core, item["retrieved"]


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
    if not values_ok(BY_KEY[key], core["values"], core["lines"]):
        raise ItemError("format")                   # 새로 계산한 값도 같은 꼴·지킴을 넘어야 싣는다
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
