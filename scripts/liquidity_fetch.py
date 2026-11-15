#!/usr/bin/env python3
"""참고 자료 — 지준·재정 (2026-10-30 추가, 사용자 결정: 비공개 월간 알림의 [지준·재정] 블록을 공개 카드로).

공개 통계의 숫자와 산술(13주 차·나눔·비율·12개월 합)만 싣는다. 규칙이 아니다 — 충족·판정이 없고, 판정·공개본·그래프
스크립트는 이 파일(<out>/liquidity.json)을 읽지 않는다. 규칙 카드 '지준과 통화승수'(reserves_multiplier)의 지준/GDP가 왜
움직였는지 읽는 재료다. 칸(ITEMS — 화면 차례):
  reserves  최근 13주(91일) 지준 변화(H.4.1 수요일 수준 WRBWFRBL)를 대차대조표 항목으로 나눈다 — 재무부 현금 TGA(WDTGAL)·
            역레포 전체(WLRRAL — 익일물 + 해외 공적 풀)·연준 보유 단기채(WSHOBL)·명목 이표채(WSHONBNL)·그 밖(나머지:
            MBS 상환·현금 통화·대출 등). 부호는 지준 쪽 — TGA·역레포가 늘면 −. 다섯 줄이 모두 있는 마지막 수요일과 그 91일
            전 이하 마지막 공통 관측(NEAR_DAYS 안). 문구는 보이는 숫자끼리 합이 맞게 '그 밖'이 반올림 차를 받는다
  rule      지준/명목GDP와 규칙 하한(regime_rules.TH['reserves_gdp_low'])의 차(값 − 하한)를 %p와 달러로 — 값·GDP 분기는
            regime_check.compute와 같은 식(주 평균 WRESBAL의 마지막 값 ÷ 1000 ÷ 마지막 분기 GDP × 100)이라 규칙 카드와
            같은 숫자다(테스트가 견준다). 판정이 아니라 산술. 비율은 6자리로 한 번만 반올림해 두고, 화면의 %p는 보이는 둘째
            자리 비율에서 하한을 뺀 값이다(shown_gap — 따로 반올림하면 x.xx5 바로 아래 주에 두 숫자가 어긋났다)
  fiscal    연방 재정수지 12개월 합(MTSDS133FMS, 정확히 12개 달이 있을 때만)과 명목 GDP 대비 · 1년 전 12개월 · 연방 이자
            지출(국민계정 A091RC1Q027SBEA, 연율)/같은 분기 GDP · 시장성 국채 중 단기채 비중(Z.1 BOGZ1FL313161110Q /
            (그것 + BOGZ1FL313161275Q)) · 1년 전 같은 분기
  maturity  (2026-11-15) 연준 보유 국채의 잔존만기 구간 — H.4.1 수요일 수준 TREAS10Y(10년 초과)·TREAS5T10(5~10년)·TREAS1T5
            (1~5년), 세 줄이 모두 있는 마지막 수요일의 수준과 13주 변화(91일 전 이하 마지막 공통 관측, NEAR_DAYS 안 — 없으면 그
            변화만 비운다). 잔존만기 구간이라 변화가 곧 매입이 아니다(시간이 지나면 아래 구간으로 옮겨 가고, 만기 재투자는 입찰에서
            장기물을 더한다)
  holdings  (2026-11-15) 국채 잔존만기별 민간 보유 = 미 재무부 MSPD 표 3(시장성 국채 종목별 월말 잔액, 백만 달러 —
            api.fiscaldata.treasury.gov) − 뉴욕 연은 SOMA 종목별 보유(MSPD 기록일 이하 마지막 SOMA 날짜, 액면 + 물가 보상분,
            달러 — markets.newyorkfed.org). 한 종목이 발행·재발행마다 여러 행이고 잔액(outstanding_amt)은 그중 한 행에만 있어
            종목별로 더한다. 9자리 종목·다섯 종류(단기채·이표채·장기채·물가연동·변동금리)·기록일 뒤 만기만. 종목마다 민간 =
            잔액 − min(연준, 잔액). 잔존만기 구간은 달력으로(만기 ≤ 기록일 + 1·5·10년). 10년물 환산 = Σ 민간 × 수정 듀레이션 ÷
            10년 par 채권의 수정 듀레이션 — 금리는 기록일 이하 마지막 DGS10 하나로 평평하다고 본 근사(단기채 무이표, 변동금리
            0.25년 무이표, 물가연동은 실질 이표 그대로), DGS10이 없으면 환산을 뺀다. 1년 전 = 12개월 앞 같은 달 말일의 MSPD와
            그 이하 SOMA(받지 못하면 그 비교만 뺀다). 요청은 FRED 다음에 따로 HOLD_BUDGET초 안 최대 6번(가장 새 기록일 · 그 달
            MSPD · SOMA 날짜 목록 · SOMA, 1년 전 MSPD · SOMA) — credit_fetch.fetch_bytes(이 프로젝트를 밝히는 UA, https·같은
            호스트만, 다른 곳으로 넘겨지면 받지 않음). 받은 원문은 <work>/liquidity/에 두고(--offline이면 이것만) 공개 data에는
            종목 행을 싣지 않는다 — 구간 합만. 상태 파일은 없다(실행마다 다시 받는다 — 월말 자료라 숫자가 같으면 파일도 그대로)
산식은 비공개 파이프라인의 liquidity_block.py(민간 보유는 tsy_holdings.py)와 같다(저장소를 넘어 가져오지 않고 여기서 따로 쓴다 —
고치면 양쪽을 같이. 민간 보유·만기 구간의 짝 테스트는 비공개 쪽 test_tsy_holdings.PairTest가 형제 폴더가 있을 때 견준다).
비공개 쪽과 다른 곳: TGA 수준은 재정 줄 끝이 아니라 지준 칸의 덧붙이는 줄에 적는다(칸마다 따로 실패하게), 규칙까지의 거리는
규칙 점검 결과를 넘겨받지 않고 같은 식으로 다시 계산한다(GDP는 재정 칸과 같은 수신분).

자료 이용 조건(2026-10-30 시리즈 쪽 JSON-LD의 license에서 확인 — LICENCE, 만기 구간 셋과 DGS10은 2026-11-15): 모두 'Public
Domain: Citation Requested'(연준·재무부·BEA). FRED 권장 인용을 함께 싣는다. 그 밖의 조건이 붙은 시리즈는 이 파일에 넣지 않는다
(테스트가 목록을 고정한다). FRED 밖(holdings 칸, EXT): 미 재무부 Fiscal Data의 MSPD는 미 연방 정부 저작물('public-domain'),
뉴욕 연은 SOMA는 newyorkfed.org 이용약관('nyfed-terms') — 수급 카드의 딜러 통계와 같은 꼴로 기본 출처 형식(© 연도)·관계없음
고지·계산값 표시(한·영)를 싣고, 두 출처의 인용을 sources[].citation에 글자로(사이트는 FRED·GitHub에만 링크를 건다).

실패·이어 싣기·문구 원칙은 oil_fetch·ai_invest_fetch와 같다: 칸마다 따로, 못 받은 칸은 직전 숫자를 '받지 못함'과 그날부터라는
날짜와 함께(직전 값이 없으면 사유만), 받은 자료가 직전보다 이르면 받지 않는다, 문구는 이 파일에 정해 둔 것뿐(오류 원문은 싣지
않는다), 같은 내용이면 다시 쓰지 않는다, 수신 전체 BUDGET초(응답을 읽는 동안에도 본다 — ai_invest_fetch.fetch_csv).

종료코드: 0 한 칸이라도 이번에 받음 / 1 하나도 못 받음(또는 파일을 쓰지 못함). 워크플로 단계는 continue-on-error, 알림 없음.

사용법: python scripts/liquidity_fetch.py [--out data] [--work .work] [--offline]
"""
import os, sys, json, time, argparse, calendar, datetime

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import regime_rules as rr                     # 규칙 하한(TH['reserves_gdp_low'])만 읽는다 — 공유 파일, 고치지 않는다
import render_public as rp
import ai_invest_fetch as ai                  # 수신(fetch_csv·load_series)·쓰기·꼴 검사를 그대로 쓴다
import credit_fetch as cf                     # FRED 밖 요청 한 건(fetch_bytes — 이 프로젝트를 밝히는 UA, https·같은 호스트·옮김 검사)
import fred_fetch as ff

SCHEMA = 1
REPO = os.path.dirname(SCRIPTS)
DEFAULT_OUT = os.path.join(REPO, "data")
DEFAULT_WORK = os.path.join(REPO, ".work")
FILE = "liquidity.json"
CACHE = "liquidity"                           # <work>/liquidity/<ID>.csv

BUDGET = 60                                   # FRED 수신 전체(초) — 워크플로 단계 제한(2분) 안에서 끝나게
HOLD_BUDGET = 30                              # 민간 보유 칸의 FRED 밖 요청(최대 6번) 전체(초) — FRED와 따로, 합쳐도 단계 제한 안
WEEKS13 = 91                                  # 13주
NEAR_DAYS = 6                                 # 13주 전 공통 관측이 91일 전에서 이보다 멀면 비운다

_BOARD = "Board of Governors of the Federal Reserve System (US)"
_BEA = "U.S. Bureau of Economic Analysis"
_FISCAL = "U.S. Department of the Treasury. Fiscal Service"
# FRED 권장 인용의 출처·제목(2026-10-30 시리즈 쪽 Suggested Citation 그대로)
SOURCES = {
    "WRBWFRBL": (_BOARD, "Liabilities and Capital: Other Factors Draining Reserve Balances: Reserve Balances with Federal "
                         "Reserve Banks: Wednesday Level"),
    "WDTGAL": (_BOARD, "Liabilities and Capital: Liabilities: Deposits with F.R. Banks, Other Than Reserve Balances: "
                       "U.S. Treasury, General Account: Wednesday Level"),
    "WLRRAL": (_BOARD, "Liabilities and Capital: Liabilities: Reverse Repurchase Agreements: Wednesday Level"),
    "WSHOBL": (_BOARD, "Assets: Securities Held Outright: U.S. Treasury Securities: Bills: Wednesday Level"),
    "WSHONBNL": (_BOARD, "Assets: Securities Held Outright: U.S. Treasury Securities: Notes and Bonds, Nominal: "
                         "Wednesday Level"),
    "WRESBAL": (rp.FRED_SOURCE["WRESBAL"], rp.FRED_TITLE["WRESBAL"]),
    "GDP": (rp.FRED_SOURCE["GDP"], rp.FRED_TITLE["GDP"]),
    "MTSDS133FMS": (_FISCAL, "Federal Surplus or Deficit [-]"),
    "A091RC1Q027SBEA": (_BEA, "Federal government current expenditures: Interest payments"),
    "BOGZ1FL313161110Q": (_BOARD, "Federal Government; Total Marketable Treasury Bills; Liability, Level"),
    "BOGZ1FL313161275Q": (_BOARD, "Federal Government; Other Marketable Treasury Securities; Liability, Level"),
    # 2026-11-15 — 연준 보유 국채의 잔존만기 구간(시리즈 쪽 Suggested Citation 그대로)과 민간 보유의 10년물 환산 금리
    "TREAS10Y": (_BOARD, "Assets: Securities Held Outright: U.S. Treasury Securities: Maturing in over 10 Years: "
                         "Wednesday Level"),
    "TREAS5T10": (_BOARD, "Assets: Securities Held Outright: U.S. Treasury Securities: Maturing in over 5 Years to 10 "
                          "Years: Wednesday Level"),
    "TREAS1T5": (_BOARD, "Assets: Securities Held Outright: U.S. Treasury Securities: Maturing in over 1 Year to 5 Years: "
                         "Wednesday Level"),
    "DGS10": (rp.FRED_SOURCE["DGS10"], rp.FRED_TITLE["DGS10"]),
}
# 시리즈 쪽 JSON-LD의 license(2026-10-30 확인). 이 값 밖의 시리즈는 싣지 않는다
LICENCE = {sid: "public-domain" for sid in SOURCES}
SERIES = list(SOURCES)                        # 만기 구간·DGS10은 맨 뒤 — 예산이 모자라면 먼저 빠진다
BS = {"res": "WRBWFRBL", "tga": "WDTGAL", "rrp": "WLRRAL", "bills": "WSHOBL", "coupons": "WSHONBNL"}   # 수요일 수준, 백만 달러
FISCAL = {"deficit": "MTSDS133FMS", "interest": "A091RC1Q027SBEA", "bills_out": "BOGZ1FL313161110Q",
          "other_out": "BOGZ1FL313161275Q"}
MATURITY = {"y10p": "TREAS10Y", "y5_10": "TREAS5T10", "y1_5": "TREAS1T5"}   # 연준 보유 국채 잔존만기 구간(수요일, 백만 달러)
MAT_LABEL = {"y10p": "10년 초과", "y5_10": "5~10년", "y1_5": "1~5년"}
PARTS = ("tga", "rrp", "bills", "coupons")    # 문구에서 각자 반올림하는 몫 — '그 밖'이 나머지를 받는다
SIGN_NOTE = "(부호는 지준 쪽)"                 # 지준 줄 끝 — 숫자 사이에 끼지 않게(보이는 숫자끼리 합은 그대로)

NOTICE = ("이 사이트의 규칙 점검에 쓰지 않는 참고 자료다. 규칙 카드 '지준과 통화승수'의 지준/GDP가 왜 움직였는지 읽는 "
          "재료로, 공개 통계로 계산한 산술만 싣는다. 금리나 자금 여건을 예측하지 않는다.")
COMPUTED_NOTICE = "13주 차·나눔·비율·12개월 합·하한 대비 차는 macro-regime-check가 원자료로 계산한 값이다."
# 민간 보유 칸의 고지 — 뉴욕 연은 이용약관의 기본 출처 형식·관계없음 고지와 함께(수급 카드의 딜러 통계와 같은 꼴)
HOLD_NOTICE = ("민간 보유·연준 몫·10년물 환산·1년 전 대비는 macro-regime-check가 미 재무부 MSPD 표 3의 종목별 월말 잔액과 뉴욕 연은 "
               "SOMA 종목별 보유로 계산한 값이다. 미 재무부·뉴욕 연은이 발표한 값이 아니다.")
HOLD_NOTICE_EN = ("Private holdings, Fed shares, 10-year equivalents and year-ago changes are computed by macro-regime-check "
                  "from U.S. Treasury MSPD Table 3 security-level month-end amounts outstanding and New York Fed SOMA "
                  "security-level holdings; they are not published by the U.S. Treasury or the New York Fed.")
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


def _mkey(d):
    return d.year * 12 + d.month - 1


def _qkey(d):
    return d.year * 4 + (d.month - 1) // 3


def calc_reserves(S):
    """13주 지준 분해 — 다섯 줄이 모두 있는 마지막 수요일과, 그 91일 전 이하 마지막 공통 관측(NEAR_DAYS 안). 십억 달러."""
    common = sorted(set.intersection(*(set(d for d, _ in S[sid]) for sid in BS.values())))
    if not common:
        raise ItemError("format")
    d1 = common[-1]
    target = d1 - datetime.timedelta(days=WEEKS13)
    old = [d for d in common if d <= target]
    if not old or (target - old[-1]).days > NEAR_DAYS:
        raise ItemError("format")
    d0 = old[-1]
    v = {k: dict(S[sid]) for k, sid in BS.items()}
    ch = {k: (v[k][d1] - v[k][d0]) / 1000 for k in BS}
    parts = {"tga": -ch["tga"], "rrp": -ch["rrp"], "bills": ch["bills"], "coupons": ch["coupons"]}
    parts["other"] = ch["res"] - sum(parts.values())
    return {"date": _iso(d1),
            "values": {"from": _iso(d0), "res": _r(ch["res"]), "res_level": _r(v["res"][d1] / 1000),
                       "tga_level": _r(v["tga"][d1] / 1000), **{k: _r(x) for k, x in parts.items()}}}


def reserves_gdp(S):
    """regime_check.compute의 reserves_gdp와 같은 식 → (값 %, 지준 날짜, GDP 분기 날짜, GDP 십억 달러)."""
    wres, gdp = S["WRESBAL"], S["GDP"]
    gd, g = gdp[-1]
    if not g:
        raise ItemError("format")
    return wres[-1][1] / 1000 / g * 100, wres[-1][0], gd, g


def shown_gap(value, low):
    """화면의 하한 대비 차(%p) — 화면에 보이는 둘째 자리 비율에서 하한을 뺀다. 저장한 차를 따로 반올림하면 비율이
    x.xx5 경계 바로 아래일 때(약 0.5%의 주) '9.86% · 대비 +0.85%p'처럼 보이는 두 숫자가 어긋났다(2026-11-10 점검).
    연준 재무상태표 카드(fedbs_fetch)도 이것을 쓴다."""
    return float(f"{value:.2f}") - low


def calc_rule(S):
    value, wd, gd, g = reserves_gdp(S)
    low = float(rr.TH["reserves_gdp_low"])
    return {"date": _iso(wd),
            "values": {"value": round(value, 6) + 0.0, "gdp_quarter": _iso(gd), "gdp_bn": _r(g), "low": low,
                       "gap_pp": _r(value - low), "gap_bn": _r((value - low) / 100 * g)}}


def calc_fiscal(S):
    """재정 — 12개월 합은 정확히 12개 달이 있을 때만, 1년 전 = 12개월 앞의 12개월. 이자 지출/GDP는 같은 분기끼리.
    단기채 비중은 두 줄이 모두 있는 마지막 분기, 1년 전 = 네 분기 앞(없으면 비움)."""
    m = {_mkey(d): (d, v) for d, v in S[FISCAL["deficit"]]}
    last = max(m)

    def sum12(k):
        return sum(m[k - i][1] for i in range(12)) / 1000 if all(k - i in m for i in range(12)) else None
    gdp = S["GDP"]
    g_d, g = gdp[-1]
    gq = {_qkey(d): v for d, v in gdp}
    i_d, i_v = S[FISCAL["interest"]][-1]
    bills = {_qkey(d): (d, v) for d, v in S[FISCAL["bills_out"]]}
    other = {_qkey(d): v for d, v in S[FISCAL["other_out"]]}

    def share(q):
        return bills[q][1] / (bills[q][1] + other[q]) * 100 if q in bills and q in other and \
            (bills[q][1] + other[q]) else None
    both = [q for q in bills if q in other]
    qb = max(both) if both else None
    s12, s12y = sum12(last), sum12(last - 12)
    dates = [m[last][0], i_d, g_d] + ([bills[qb][0]] if qb is not None else [])
    return {"date": _iso(max(dates)),
            "values": {"deficit_to": _iso(m[last][0]), "sum12": _r(s12), "sum12_1y": _r(s12y),
                       "sum12_gdp": _r(s12 / g * 100) if s12 is not None and g else None, "gdp_quarter": _iso(g_d),
                       "interest": _r(i_v), "interest_q": _iso(i_d),
                       "interest_gdp": _r(i_v / gq[_qkey(i_d)] * 100) if gq.get(_qkey(i_d)) else None,
                       "bills_share": _r(share(qb)) if qb is not None else None,
                       "bills_share_1y": _r(share(qb - 4)) if qb is not None else None,
                       "bills_q": _iso(bills[qb][0]) if qb is not None else None}}


def calc_maturity(S):
    """연준 보유 국채 잔존만기 구간 — 세 줄이 모두 있는 마지막 수요일의 수준과 13주 변화(91일 전 이하 마지막 공통 관측,
    NEAR_DAYS 안 — 없으면 변화만 비운다). 십억 달러. 비공개 liquidity_block.maturity와 같은 식."""
    common = sorted(set.intersection(*(set(d for d, _ in S[sid]) for sid in MATURITY.values())))
    if not common:
        raise ItemError("format")
    d1 = common[-1]
    target = d1 - datetime.timedelta(days=WEEKS13)
    old = [d for d in common if d <= target]
    d0 = old[-1] if old and (target - old[-1]).days <= NEAR_DAYS else None
    v = {k: dict(S[sid]) for k, sid in MATURITY.items()}
    vals = {"from": _iso(d0) if d0 else None}
    for k in MATURITY:
        vals[k] = _r(v[k][d1] / 1000)
        vals[f"{k}_chg13"] = _r((v[k][d1] - v[k][d0]) / 1000) if d0 else None
    return {"date": _iso(d1), "values": vals}


# ---------- 국채 잔존만기별 민간 보유 (미 재무부 MSPD 표 3 − 뉴욕 연은 SOMA, 2026-11-15) ----------
# 비공개 tsy_holdings.py와 같은 산식(가져오지 않고 따로 쓴다). 응답 꼴(2026-11-15 받아 확인): MSPD {"data": [{record_date,
# security_class1_desc, security_class2_desc(종목 9자리 — 합계 줄은 이름), interest_rate_pct, maturity_date, outstanding_amt(백만
# 달러의 글자 · 'null')…}], "meta": {"total-pages": 1 …}} — 2026-10-31 892행 약 600KB · SOMA 날짜 목록 {"soma": {"asOfDates":
# ["2026-11-10", …]}} · SOMA {"soma": {"holdings": [{cusip, parValue(달러의 글자), inflationCompensation('' 또는 글자) …}]}}
MSPD_HOST = "api.fiscaldata.treasury.gov"
MSPD_URL = f"https://{MSPD_HOST}/services/api/fiscal_service/v1/debt/mspd/mspd_table_3_market"
MSPD_LATEST_Q = "?sort=-record_date&fields=record_date&page%5Bsize%5D=1"
MSPD_MONTH_Q = "?filter=record_date:eq:{}&page%5Bsize%5D=10000"
MSPD_PAGE = ("https://fiscaldata.treasury.gov/datasets/monthly-statement-public-debt/"
             "detail-of-marketable-treasury-securities-outstanding")
MSPD_TITLE = "Monthly Statement of the Public Debt, Detail of Marketable Treasury Securities Outstanding"
SOMA_HOST = "markets.newyorkfed.org"
SOMA_DATES_URL = f"https://{SOMA_HOST}/api/soma/asofdates/list.json"
SOMA_URL = f"https://{SOMA_HOST}/api/soma/tsy/get/all/asof/{{}}.json"
SOMA_PAGE = "https://www.newyorkfed.org/markets/soma-holdings"
SOMA_TITLE = "System Open Market Account Holdings of Domestic Securities"
_TREASURY = "U.S. Department of the Treasury, Bureau of the Fiscal Service"
_NYFED = "Federal Reserve Bank of New York"
# FRED 밖 출처(이 파일 안의 이름 — sources[].series) → (이름, 화면 주소, 제목, 이용 조건)
EXT = {"MSPD": (_TREASURY, MSPD_PAGE, MSPD_TITLE, "public-domain"),
       "SOMA": (_NYFED, SOMA_PAGE, SOMA_TITLE, "nyfed-terms")}
HOLD_CLASSES = ("Bills Maturity Value", "Notes", "Bonds", "Inflation-Protected Securities", "Floating Rate Notes")
HOLD_BUCKETS = (("le1", "1년 이하", 1), ("y1_5", "1~5년", 5), ("y5_10", "5~10년", 10), ("y10p", "10년 초과", None))
HOLD_KEYS = ("y10p", "y5_10", "y1_5", "le1", "total")          # 값 칸·문구 차례(긴 만기부터)
FRN_YEARS = 0.25                              # 변동금리채의 듀레이션 근사(다음 금리 재설정까지 — 넉넉히)


def _hnum(v):
    """MSPD·SOMA의 숫자 글자('1,234.5' · 'null' · '') → float 또는 None."""
    try:
        x = float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return x if x == x and abs(x) != float("inf") else None


def _hday(v):
    try:
        return datetime.date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def month_end(y, m):
    return datetime.date(y, m, calendar.monthrange(y, m)[1])


def year_before(day):
    """12개월 앞 같은 달 말일 — MSPD 기록일은 늘 말일."""
    return month_end(day.year - 1, day.month)


def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:                        # 2월 29일
        return d.replace(year=d.year + n, day=28)


def bucket_of(mat, record):
    """잔존만기 구간 — 달력으로: 만기 ≤ 기록일 + 1년 → 1년 이하, ≤ + 5년 → 1~5년, ≤ + 10년 → 5~10년, 그 밖 → 10년 초과."""
    for k, _, hi in HOLD_BUCKETS[:-1]:
        if mat <= add_years(record, hi):
            return k
    return HOLD_BUCKETS[-1][0]


def mod_duration(cpn, years, y):
    """반기 이표 채권의 수정 듀레이션(해) — 이표 cpn(%), 잔존 years, 평평한 수익률 y(%). 무이표(cpn 0)도 같은 식."""
    if years <= 0:
        return 0.0
    yy, c = y / 100 / 2, cpn / 100 / 2
    n = max(1, round(years * 2))
    first = years * 2 - (n - 1)               # 첫 이표까지의 반기 수(0~1] — 마지막 현금흐름이 정확히 만기에 오게
    pv = dur = 0.0
    for k in range(n):
        t = first + k
        cf_ = c + (1 if k == n - 1 else 0)
        df = (1 + yy) ** -t
        pv += cf_ * df
        dur += t * cf_ * df
    if pv <= 0:
        return 0.0
    return dur / pv / 2 / (1 + yy)


def duration_of(item, years, y):
    if item["cls"] == "Floating Rate Notes":
        return mod_duration(0.0, min(years, FRN_YEARS), y)
    return mod_duration(item["cpn"] or 0.0, years, y)


def mspd_outstanding(rows, record):
    """MSPD 표 3 행 → {종목: {out(백만 달러), mat, cpn, cls}} — 9자리 종목·다섯 종류·기록일 뒤 만기만, 잔액은 종목별 합."""
    out = {}
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        c = str(r.get("security_class2_desc") or "")
        if len(c) != 9 or r.get("security_class1_desc") not in HOLD_CLASSES:
            continue
        mat = _hday(r.get("maturity_date"))
        if mat is None or mat <= record:
            continue
        e = out.setdefault(c, {"out": 0.0, "mat": mat, "cpn": None, "cls": r.get("security_class1_desc")})
        v = _hnum(r.get("outstanding_amt"))
        if v is not None:
            e["out"] += v
        cpn = _hnum(r.get("interest_rate_pct"))
        if cpn is not None and e["cpn"] is None:
            e["cpn"] = cpn
    return {c: e for c, e in out.items() if e["out"] > 0}


def soma_holdings(items):
    """SOMA 종목 행 → {종목: 보유(백만 달러)} — 액면 + 물가 보상분."""
    out = {}
    for x in items or []:
        if not isinstance(x, dict):
            continue
        c = str(x.get("cusip") or "")
        par = _hnum(x.get("parValue"))
        if len(c) != 9 or par is None:
            continue
        out[c] = out.get(c, 0.0) + (par + (_hnum(x.get("inflationCompensation")) or 0.0)) / 1e6
    return out


def holdings_buckets(out, fed, record, y=None):
    """구간 합(십억 달러) — {buckets: {구간: {out, fed, private, dd, share, eq10}}, total, y, d10, n, fed_missing}. y(%)가 없으면
    10년물 환산을 뺀다. 소수 넷째 자리로 한 번만 반올림해 둔다(비공개 tsy_holdings.buckets와 같은 꼴·같은 자리)."""
    res = {k: {"out": 0.0, "fed": 0.0, "private": 0.0, "dd": 0.0} for k, _, _ in HOLD_BUCKETS}
    miss = sum(1 for c in fed if c not in out)
    for c, e in out.items():
        years = (e["mat"] - record).days / 365.25
        k = bucket_of(e["mat"], record)
        f = min(fed.get(c, 0.0), e["out"])
        p = e["out"] - f
        res[k]["out"] += e["out"] / 1000
        res[k]["fed"] += f / 1000
        res[k]["private"] += p / 1000
        if y is not None:
            res[k]["dd"] += p / 1000 * duration_of(e, years, y)
    d10 = mod_duration(y, 10, y) if y is not None else None
    for v in res.values():
        v["share"] = v["fed"] / v["out"] * 100 if v["out"] else None
        v["eq10"] = v["dd"] / d10 if d10 else None
    tot = {f: sum(v[f] for v in res.values()) for f in ("out", "fed", "private", "dd")}
    tot["share"] = tot["fed"] / tot["out"] * 100 if tot["out"] else None
    tot["eq10"] = tot["dd"] / d10 if d10 else None
    r4 = lambda v: {k: (None if x is None else round(x, 4)) for k, x in v.items()}
    return {"buckets": {k: r4(v) for k, v in res.items()}, "total": r4(tot), "y": y,
            "d10": None if d10 is None else round(d10, 6), "n": len(out), "fed_missing": miss}


def calc_holdings(now, ya=None):
    """구간 합 둘(지금 · 1년 전 — holdings_buckets 꼴에 record·soma를 더한 것) → 칸의 core {date, values}."""
    pick = lambda h, k: h["total"] if k == "total" else h["buckets"][k]
    vals = {"soma": now["soma"], "y": now["y"], "n": now["n"], "fed_missing": now["fed_missing"]}
    for k in HOLD_KEYS:
        b = pick(now, k)
        vals.update({f"{k}_out": b["out"], f"{k}_fed": b["fed"], f"{k}_private": b["private"], f"{k}_share": b["share"],
                     f"{k}_eq10": b["eq10"]})
    vals.update(ya_record=ya["record"] if ya else None, ya_soma=ya["soma"] if ya else None, ya_y=ya["y"] if ya else None,
                ya_total_eq10=ya["total"]["eq10"] if ya else None)
    for k in HOLD_KEYS:
        vals[f"ya_{k}_private"] = pick(ya, k)["private"] if ya else None
    return {"date": now["record"], "values": vals}


def _hold_get(name, url, host, work, offline, deadline, clock, fetch):
    """FRED 밖 JSON 한 건 — 온라인이면 받아서(읽히면 <work>/liquidity/name에 원문), --offline이면 그 원문만. 실패는 ItemError."""
    path = os.path.join(work, CACHE, name)
    if offline:
        try:
            with open(path, "rb") as f:
                blob = f.read()
        except OSError:
            raise ItemError("fetch")
    else:
        if deadline - clock() <= 1:
            raise ItemError("fetch")
        try:
            blob = fetch(url, host, deadline)
        except Exception:                     # 연결·HTTP·시간 초과·옮김 — 원문은 싣지 않는다
            raise ItemError("fetch")
    try:
        js = json.loads(blob.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, AttributeError):
        raise ItemError("format")
    if not isinstance(js, dict):
        raise ItemError("format")
    if not offline:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path + ".tmp", "wb") as f:
                f.write(blob)
            os.replace(path + ".tmp", path)
        except OSError:
            pass                              # 캐시는 덤이다
    return js


def _month(record, get, dates, dgs10):
    """그 기록일의 구간 합 — MSPD 그 달 · SOMA(기록일 이하 마지막 날짜). 실패는 ItemError."""
    js = get(f"mspd_{record.isoformat()}.json", MSPD_URL + MSPD_MONTH_Q.format(record.isoformat()), MSPD_HOST)
    meta = js.get("meta") if isinstance(js.get("meta"), dict) else {}
    if isinstance(meta.get("total-pages"), int) and meta["total-pages"] > 1:
        raise ItemError("format")             # 한 쪽에 다 오지 않았다 — 일부 종목만으로 싣지 않는다
    rows = js.get("data") if isinstance(js.get("data"), list) else None
    out = mspd_outstanding(rows, record)
    if not out:
        raise ItemError("format")
    cand = [d for d in dates if d <= record]
    if not cand:
        raise ItemError("format")
    sd = cand[-1]
    sj = get(f"soma_{sd.isoformat()}.json", SOMA_URL.format(sd.isoformat()), SOMA_HOST)
    fed = soma_holdings(((sj.get("soma") or {}) if isinstance(sj.get("soma"), dict) else {}).get("holdings"))
    if not fed:
        raise ItemError("format")
    hit = ff.on_or_before(dgs10, record) if dgs10 else None
    return {"record": record.isoformat(), "soma": sd.isoformat(), **holdings_buckets(out, fed, record, hit[1] if hit else None)}


def load_holdings(work, today, offline=False, dgs10=None, clock=time.monotonic, opener=None, fetch=None,
                  budget=HOLD_BUDGET):
    """민간 보유 칸의 core 또는 ItemError — 예외를 내보내지 않는다. fetch(url, host, deadline) → bytes(기본
    credit_fetch.fetch_bytes, opener를 넘긴다). 1년 전을 받지 못하면 그 비교만 뺀다."""
    try:
        fetch = fetch or (lambda url, host, deadline: cf.fetch_bytes(url, host, deadline, clock, opener))
        deadline = clock() + budget
        get = lambda name, url, host: _hold_get(name, url, host, work, offline, deadline, clock, fetch)
        js = get("mspd_latest.json", MSPD_URL + MSPD_LATEST_Q, MSPD_HOST)
        top = js.get("data")[0] if isinstance(js.get("data"), list) and js.get("data") else None
        record = _hday(top.get("record_date")) if isinstance(top, dict) else None
        if record is None or record > today or record != month_end(record.year, record.month):
            raise ItemError("format")
        dj = get("soma_dates.json", SOMA_DATES_URL, SOMA_HOST)
        got = ((dj.get("soma") or {}) if isinstance(dj.get("soma"), dict) else {}).get("asOfDates")
        dates = sorted(d for d in (_hday(x) for x in (got if isinstance(got, list) else [])) if d)
        now = _month(record, get, dates, dgs10)
        try:
            ya = _month(year_before(record), get, dates, dgs10)
        except ItemError:
            ya = None
        return calc_holdings(now, ya)
    except ItemError as e:
        return e
    except Exception as e:                    # 뜻밖의 오류도 그 칸만 실패로(Actions 로그엔 예외 이름만)
        print(f"[liquidity_fetch] holdings 계산 오류: {type(e).__name__}", file=sys.stderr)
        return ItemError("format")


# ---------- 칸 정의 (차례 = 화면 차례) ----------
# values: 이름 → 꼴("num" · "num?" · "day" · "day?") — 직전 파일 검사에도 쓴다
# ends: 시리즈마다의 끝 날짜(values의 날짜 칸) — 칸의 date와 함께 하나라도 직전보다 이르면 받지 않는다

ITEMS = [
    {"key": "reserves", "title": "지준 13주 변화의 나눔 (연준 대차대조표)", "series": list(BS.values()),
     "calc": calc_reserves,
     "values": {"from": "day", "res": "num", "res_level": "num", "tga_level": "num", "tga": "num", "rrp": "num",
                "bills": "num", "coupons": "num", "other": "num"}},
    {"key": "rule", "title": "지준/명목GDP와 규칙 하한의 차", "series": ["WRESBAL", "GDP"], "calc": calc_rule,
     "values": {"value": "num", "gdp_quarter": "day", "gdp_bn": "num", "low": "num", "gap_pp": "num", "gap_bn": "num"},
     "ends": ["gdp_quarter"]},
    {"key": "fiscal", "title": "미 연방 재정수지 · 이자 지출 · 단기채 비중",
     "series": [*FISCAL.values(), "GDP"], "calc": calc_fiscal,
     "values": {"deficit_to": "day", "sum12": "num?", "sum12_1y": "num?", "sum12_gdp": "num?", "gdp_quarter": "day",
                "interest": "num", "interest_q": "day", "interest_gdp": "num?", "bills_share": "num?",
                "bills_share_1y": "num?", "bills_q": "day?"},
     "ends": ["deficit_to", "interest_q", "bills_q", "gdp_quarter"]},
    {"key": "maturity", "title": "연준 보유 국채의 잔존만기 구간 (H.4.1)", "series": list(MATURITY.values()),
     "calc": calc_maturity,
     "values": {"from": "day?", **{f: t for k in MATURITY for f, t in ((k, "num"), (f"{k}_chg13", "num?"))}}},
    # FRED 밖 자료로 따로 받는 칸 — compute가 아니라 load_holdings가 만든다(series는 10년물 환산의 DGS10 인용만)
    {"key": "holdings", "title": "국채 잔존만기별 민간 보유 (미 재무부 월말 잔액 − 연준 보유)", "series": ["DGS10"],
     "ext": ["MSPD", "SOMA"], "calc": None,
     "values": {"soma": "day", "y": "num?", "n": "int", "fed_missing": "int",
                **{f"{k}_{f}": t for k in HOLD_KEYS for f, t in (("out", "num"), ("fed", "num"), ("private", "num"),
                                                                   ("share", "num?"), ("eq10", "num?"))},
                "ya_record": "day?", "ya_soma": "day?", "ya_y": "num?", "ya_total_eq10": "num?",
                **{f"ya_{k}_private": "num?" for k in HOLD_KEYS}},
     "ends": ["soma"]},
]
BY_KEY = {it["key"]: it for it in ITEMS}


# ---------- 문구 ----------

def _s(v, nd=0):
    """부호·천 단위 쉼표 — 반올림해 0이면 부호 없이."""
    if v is None:
        return "—"
    s = f"{v:+,.{nd}f}"
    return f"{0:.{nd}f}" if float(s.replace(",", "")) == 0 else s


def _q(day):
    """'2026-04-01' → '2026Q2'."""
    d = datetime.date.fromisoformat(day)
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def shown_parts(v):
    """문구의 정수 몫 — 지준 변화와 네 몫은 각자 반올림, '그 밖' = 반올림한 지준 변화 − 네 몫(보이는 숫자끼리 합이 맞게)."""
    sh = {k: round(v[k]) for k in PARTS}
    res = round(v["res"])
    return res, sh, res - sum(sh.values())


def texts(key, v, date):
    """칸 → (숫자 줄, 덧붙이는 줄 목록). 정해 둔 문구에 숫자만 넣는다."""
    if key == "reserves":
        res, sh, oth = shown_parts(v)
        return (f"지준 13주 변화 {_s(res)}bn ({v['from']}~{date}, 수요일) = 재무부 현금(TGA) "
                f"{_s(sh['tga'])} · 역레포(해외 공적 포함) {_s(sh['rrp'])} · 연준 단기채 {_s(sh['bills'])} · "
                f"연준 이표채 {_s(sh['coupons'])} · 그 밖 {_s(oth)} {SIGN_NOTE}",
                [f"{date} 지준 {v['res_level']:,.0f}bn · 재무부 현금(TGA) {v['tga_level']:,.0f}bn. bn은 십억 달러, H.4.1 "
                 "수요일 수준의 13주(91일 전 이하 마지막 공통 수요일) 차다.",
                 "부호는 지준 쪽이다 — 재무부 현금(TGA)·역레포가 늘면 그만큼 지준이 줄어 −, 연준 보유 국채가 늘면 +. 역레포는 "
                 "익일물 역레포와 해외 공적 역레포 풀을 합친 전체(WLRRAL)다. '그 밖'은 MBS 상환·현금 통화·대출·기타 부채의 "
                 "합(나머지)이고, 보이는 숫자끼리 합이 맞게 반올림 차를 받는다.",
                 "연준 이표채 13주 변화가 +면 연준의 명목 이표채(장기물) 보유가 늘었다는 뜻이다. 규칙 카드의 지준/GDP는 주 평균"
                 "(WRESBAL)을 써서 이 나눔의 지준(수요일 수준)과 다르다 — 수준 차는 1% 안팎이지만 13주 변화는 주에 따라 수십bn, "
                 "월말·분기말 수요일이 끼면 100bn 넘게 다를 수 있어 규칙 카드의 3개월 변화와 이 나눔의 합은 맞지 않을 수 있다."])
    if key == "rule":
        return (f"지준/명목GDP {v['value']:.2f}% ({date}, GDP {_q(v['gdp_quarter'])}) · 규칙 하한 {v['low']:.1f}% 대비 "
                f"{_s(shown_gap(v['value'], v['low']), 2)}%p ≈ {_s(v['gap_bn'])}bn",
                [f"규칙 카드 '지준과 통화승수'와 같은 값·같은 GDP 분기다: 주 평균 지준(WRESBAL) ÷ 마지막 분기 명목 GDP"
                 f"(계절조정 연율, {_q(v['gdp_quarter'])} {v['gdp_bn']:,.0f}bn). 달러 환산 = (값 − 하한) × 그 분기 GDP.",
                 "하한 대비 차(값 − 하한)는 산술이다 — 다른 항목이 그대로일 때 +면 재무부 현금(TGA)이 그만큼 더 늘면 하한에 "
                 "닿고, −면 TGA가 그만큼 줄어야 하한으로 돌아온다."])
    if key == "fiscal":
        yr = f" (1년 전 {_s(v['sum12_1y'])}bn)" if v["sum12_1y"] is not None else ""
        bs = (f" · 시장성 국채 중 단기채 {v['bills_share']:.1f}% ({_q(v['bills_q'])}, 1년 전 "
              f"{'—' if v['bills_share_1y'] is None else format(v['bills_share_1y'], '.1f') + '%'})"
              if v["bills_share"] is not None else "")
        gdp_part = f", GDP의 {abs(v['sum12_gdp']):.1f}%" if v["sum12_gdp"] is not None else ""
        intr = f" · 연방 이자 지출 {v['interest']:,.0f}bn 연율({_q(v['interest_q'])}" + \
            (f", GDP의 {v['interest_gdp']:.1f}%)" if v["interest_gdp"] is not None else ")")
        head = (f"재정수지 12개월 합 {_s(v['sum12'])}bn (~{v['deficit_to'][:7]}{gdp_part}){yr}"
                if v["sum12"] is not None else f"재정수지 12개월 합: 12개 달이 다 있지 않음(~{v['deficit_to'][:7]})")
        return (head + intr + bs,
                [f"재정수지는 월간 재무제표(MTS)의 부호 그대로다(적자 −). 12개월 합은 12개 달이 모두 있을 때만, 1년 전은 그 "
                 f"12개월 앞의 12개월이다. GDP 대비는 마지막 분기 명목 GDP(계절조정 연율, {_q(v['gdp_quarter'])})로 나눈 산술이다.",
                 "이자 지출은 국민계정(분기, 계절조정 연율)이고 같은 분기 명목 GDP로 나눈다. 단기채 비중은 연준 금융계정(Z.1, "
                 "분기, 약 2.5개월 늦음)의 시장성 단기채 ÷ (단기채 + 그 밖 시장성 국채)이고, 1년 전은 네 분기 앞이다. 분기 "
                 "리펀딩은 FRED 밖이라 싣지 않는다 — 월간 국채 잔액 MSPD는 아래 민간 보유 칸이 종목별로 쓴다."])
    if key == "maturity":
        parts = " · ".join(f"{MAT_LABEL[k]} {v[k]:,.0f}bn(13주 {_s(v[f'{k}_chg13'])})" for k in MATURITY)
        span = (f"13주 변화는 {v['from']}~{date} 수요일 수준의 차다" if v["from"] else
                "91일 전 근처의 공통 수요일 관측이 없어 13주 변화는 비운다")
        return (f"{parts} — 잔존만기 구간이라 변화 ≠ 매입",
                [f"{date} 수요일 수준(연준 H.4.1의 보유 국채 잔존만기 구간 셋)이고, {span}. bn은 십억 달러, 1년 이하 구간은 이 "
                 "줄에 없다.",
                 "잔존만기 기준이다 — 사지 않아도 시간이 지나면 위 구간에서 아래 구간으로 옮겨 가고, 만기 재투자는 입찰에서 "
                 "장기물을 더한다. 그래서 13주 변화가 +라고 연준이 장기물을 '샀다'고 읽지 않는다."])
    if key == "holdings":
        lab = {k: l for k, l, _ in HOLD_BUCKETS}
        share = lambda x: "—" if x is None else f"{x:.0f}%"
        parts = " · ".join(f"{lab[k]} {v[f'{k}_private']:,.0f}bn(연준 {share(v[f'{k}_share'])})" for k in HOLD_KEYS[:-1])
        tail = f" · 합계 {v['total_private']:,.0f}bn"
        if v["total_eq10"] is not None:
            tail += f" = 10년물 환산 {v['total_eq10']:,.0f}bn"
            if v["ya_total_eq10"] is not None:
                tail += f"(1년 전 대비 {_s(v['total_eq10'] - v['ya_total_eq10'])})"
        elif v["ya_total_private"] is not None:
            tail += f"(1년 전 대비 {_s(v['total_private'] - v['ya_total_private'])})"
        extra = [f"민간 = 미 재무부 MSPD 표 3의 종목별 월말 잔액({date}) − 뉴욕 연은 SOMA 종목별 보유({v['soma']}, 물가 보상분 "
                 f"포함)이고, 종목마다 잔액을 넘는 연준 보유는 잔액까지만 뺀다. 종목 {v['n']:,}개 · SOMA 기준일과 월말 사이에 "
                 f"만기돼 빠진 연준 종목 {v['fed_missing']:,}개. bn은 십억 달러, 잔존만기 구간은 월말에서 만기까지를 달력으로 "
                 "1·5·10년에서 나눈다."]
        if v["total_eq10"] is not None:
            extra.append(f"10년물 환산 = Σ 민간 보유 × 수정 듀레이션 ÷ 10년 par 채권의 수정 듀레이션이다. 금리는 월말 이하 "
                         f"마지막 미 10년 금리 DGS10 {v['y']:.2f}% 하나로 평평하다고 본 근사다(단기채는 무이표, 변동금리채는 "
                         "0.25년 무이표, 물가연동채는 실질 이표 그대로).")
        else:
            extra.append("미 10년 금리 DGS10을 받지 못해 10년물 환산은 싣지 않는다.")
        if v["ya_record"] is not None:
            rows = " · ".join(f"{lab[k]} {_s(v[f'{k}_private'] - v[f'ya_{k}_private'])}" for k in HOLD_KEYS[:-1])
            extra.append(f"1년 전 {v['ya_record']} 월말(SOMA {v['ya_soma']}) 대비 민간 보유 변화(bn): {rows}")
        else:
            extra.append("1년 전 같은 달 말의 자료를 받지 못해 1년 전 대비는 싣지 않는다.")
        extra.append("공급의 크기를 보는 숫자다 — 선호 서식지 이론에서는 발행 총량보다 가격에 민감한 민간이 떠안는 양을 본다. "
                     "연준 보유와 같은 기준(종목별 잔존만기)으로 뺐을 뿐 금리를 예측하지 않는다.")
        return (f"국채 민간 보유(재무부 월말 잔액 − 연준, {date} · SOMA {v['soma']}, 잔존만기): " + parts + tail, extra)
    raise KeyError(key)


def citation(sid, retrieved):
    d = datetime.date.fromisoformat(retrieved)
    src, title = SOURCES[sid]
    return (f"{src}, {title} [{sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; "
            f"{rp.FRED_URL.format(sid)}, {ai._MONTHS[d.month - 1]} {d.day}, {d.year}.")


def ext_citation(ext, retrieved, values=None):
    """FRED 밖 출처의 인용 — '<이름>, <제목>, retrieved from <받은 주소>, <날짜>.'(fedbs_fetch.ops_citation과 같은 꼴).
    SOMA는 그 칸이 쓴 기준일의 주소."""
    d = datetime.date.fromisoformat(retrieved)
    name, _, title, _ = EXT[ext]
    url = MSPD_URL if ext == "MSPD" else SOMA_URL.format(values["soma"]) if values and values.get("soma") else SOMA_DATES_URL
    return f"{name}, {title}, retrieved from {url}, {ai._MONTHS[d.month - 1]} {d.day}, {d.year}."


def sources_of(spec, retrieved=None, values=None):
    out = []
    for sid in spec["series"]:
        s = {"series": sid, "name": SOURCES[sid][0], "url": rp.FRED_URL.format(sid), "licence": LICENCE[sid]}
        if retrieved:
            s["citation"] = citation(sid, retrieved)
        out.append(s)
    for ext in spec.get("ext", ()):
        name, page, _, licence = EXT[ext]
        s = {"series": ext, "name": name, "url": page, "licence": licence}
        if retrieved:
            s["citation"] = ext_citation(ext, retrieved, values)
        out.append(s)
    return out


def notices(spec, retrieved=None):
    if spec["key"] == "holdings":
        return [HOLD_NOTICE, HOLD_NOTICE_EN, rp.nyfed_attribution(retrieved[:4]), rp.NOT_AFFILIATED]
    return [COMPUTED_NOTICE]


def present(key, core, retrieved):
    spec = BY_KEY[key]
    line, extra = texts(key, core["values"], core["date"])
    return {"key": key, "name": spec["title"], "date": core["date"], "values": core["values"], "retrieved": retrieved,
            "line": line, "extra": extra, "notices": notices(spec, retrieved),
            "sources": sources_of(spec, retrieved, core["values"])}


# ---------- 직전 파일 ----------

def core_of(item, key):
    """직전 파일의 칸 → (core, 받은 날) 또는 None(없거나 꼴이 어긋남 — 이어 실을 값이 없는 것으로 본다)."""
    spec = BY_KEY[key]
    try:
        vals = item["values"]
        ok = (ai._is_day(item["date"]) and ai._is_day(item["retrieved"]) and isinstance(vals, dict)
              and set(vals) == set(spec["values"]) and all(ai._KIND[t](vals[k]) for k, t in spec["values"].items()))
        if ok:
            texts(key, vals, item["date"])          # 문구를 다시 만들 수 있어야 한다
    except (KeyError, TypeError, IndexError, AttributeError, ValueError, OverflowError):
        return None
    if not ok:
        return None
    return {"date": item["date"], "values": dict(vals)}, item["retrieved"]


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
    """FRED 칸들(calc가 있는 칸) → {칸: core 또는 ItemError}. 민간 보유 칸은 load_holdings가 따로 만든다."""
    S = {sid: [(d, v) for d, v in s if d <= today] for sid, s in data.items()}
    out = {}
    for spec in ITEMS:
        if spec["calc"] is None:
            continue
        miss = [sid for sid in spec["series"] if sid not in S or not S[sid]]
        if miss:
            out[spec["key"]] = ItemError(errors.get(miss[0], "format"))
            continue
        try:
            out[spec["key"]] = spec["calc"](S)
        except ItemError as e:
            out[spec["key"]] = e
        except Exception as e:                  # 계산 쪽 뜻밖의 오류도 그 칸만 실패로
            print(f"[liquidity_fetch] {spec['key']} 계산 오류: {type(e).__name__}", file=sys.stderr)
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


def main(argv=None, fred_load=None, now=None, clock=time.monotonic, opener=None, hold_fetch=None):
    ap = argparse.ArgumentParser(description="FRED 공개 통계 · 미 재무부 MSPD · 뉴욕 연은 SOMA → 지준·재정 참고 자료"
                                             "(<out>/liquidity.json)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    ap.add_argument("--work", default=DEFAULT_WORK, help="작업 폴더 — 원문 캐시는 <work>/liquidity/ (기본: 저장소의 .work/)")
    ap.add_argument("--offline", action="store_true", help="요청하지 않고 캐시만 읽는다(로컬 확인용)")
    a = ap.parse_args(argv)
    out, work = os.path.abspath(a.out), os.path.abspath(a.work)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    data, errors = load_all(work, a.offline, fred_load, clock, opener=opener)
    results = compute(data, errors, now.date())
    dgs10 = [(d, v) for d, v in data.get("DGS10") or [] if d <= now.date()] or None   # 10년물 환산(없으면 환산을 뺀다)
    results["holdings"] = load_holdings(work, now.date(), a.offline, dgs10, clock, opener, hold_fetch)
    data = build(results, previous(out), now)
    for spec in ITEMS:                          # Actions 로그 — 날짜와 정해 둔 사유만(값은 찍지 않는다)
        it = data["items"][spec["key"]]
        if it["ok"]:
            print(f"[liquidity_fetch] {spec['key']} {it['date']} 기준")
        else:
            kept = f" — 직전 값({it['date']} 기준) 유지" if it["stale"] else ""
            ai.annotate(f"지준·재정 참고 {spec['key']} 받지 못함: {it['error']}{kept}")
    try:
        if differs(out, data):
            write(out, data)
    except OSError as e:
        print(f"[liquidity_fetch] {FILE}를 쓰지 못함: {type(e).__name__}", file=sys.stderr)
        return 1
    return 0 if any(it["ok"] for it in data["items"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
