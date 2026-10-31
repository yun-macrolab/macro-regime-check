#!/usr/bin/env python3
"""공개용 표 — regime_check.py의 원본 결과(<work>/raw/latest.json)를 사이트가 읽는 공개본(<out>)으로 바꾼다.

공개본에서 빼는 것 (test_render_public.py가 강제):
  - 규칙 엔진의 내부 ID(regime_rules.evaluate의 log_ids)와 출처 줄(보고서 장·절), 원본 문장(text) 그대로
  - 직전 국면 — 사람이 판단해 넣는 값이라 공개 계산에는 없다(국면 후보는 직전 국면 없이 다시 계산한다)
  - 재배포가 제한된 시리즈(S&P·ICE)의 원값과 원값을 역산할 수 있는 파생값
    (예외: 60영업일 상관처럼 원값을 되살릴 수 없는 통계는 derived로 표시해 싣는다. S&P 500 13주 변화는 방향(상승·하락·보합)만,
     ICE IG OAS가 재료인 전환 경계 t2는 ON/OFF만)
넣는 것: 규칙마다 중립적인 규칙 문장(임계값은 regime_rules.TH에서 읽는다), 공개 가능한 관측치와 기준일,
충족 여부, 시리즈별 자료 신선도와 출처 표기.
2026-10-30 운영자 결정(이용 조건 검토 뒤, 위험을 알고 받아들임) — Moody's Baa−10년(BAA10Y)은 비공개 월간 점검 줄과 같은 숫자
(수준 %p · 12개월 저점 대비 · 1990년 이후 분위)를 싣는다. FRED 표시는 'Copyrighted: Citation Required'지만 FRED 페이지의
Moody's 고지는 재배포를 막는다 — 그 고지(MOODYS_NOTICE, FRED 페이지 그대로)와 FRED 권장 인용을 값 곁(카드 notices)과 꼬리말에
함께 싣는다. ICE HY OAS는 그대로 충족 여부만.
2026-10-30 사용자 결정 — 비공개 월간 점검 알림 [레짐 점검]의 해석 쪽도 '참고 — 예측 아님'으로 싣는다(regime 절과 규칙마다
scenario·reading): 시나리오 이름표(A~D, 중립 규칙은 '—'), 해석 줄, 핵심 신호 n/m, 국면 참고값, 손으로 보는 항목(내부 ID 없이),
아직 싣지 않던 공개 관측값. 해석 줄은 규칙마다 정해 둔 꼴(READINGS)과 원본 문장이 통째로 맞을 때만 싣는다 — 숫자 자리는 공개
시리즈의 값뿐이고, 재배포 제한 값이 든 원본 문장(credit_spread)은 싣지 않고 결론 구절만 골라 다시 쓴다.
public_rules()에 없는 규칙이 원본에 있으면 실패한다(규칙 문장은 이 사이트의 본 내용 — 검토 없이 나가지 않게, 오류 문구에는
규칙 이름만). 해석 쪽(참고)은 항목마다 닫힌 채 실패한다: 정해 둔 꼴과 다른 해석 문장(nan 같은 값 포함)은 그 규칙의 reading을
null로, 이름표가 다른 규칙은 scenario·reading을 null로(핵심 신호·중립 규칙 셈에서도 뺀다), 모르는 수동 항목은 그 항목만,
모르는 국면 판정 메모는 국면 참고값의 첫 줄만 빼고, 정해 둔 경고 문구(DROPPED — 규칙 제목·개수만, 원본 문장·값·내부 ID 없음)를
공개본 warnings에 남긴다. 참고 하나 때문에 공개본 전체가 멈추지 않게(2026-10-30). 숫자가 아닌 값(nan·inf)은 null로 싣는다.
public.json은 더 최근 날짜의 공개본을 과거 날짜로 덮지 않는다(history에만 쓴다).
날짜별 기록(history/)에는 Baa−10년 값 셋과 해석 줄의 Baa 부분을 빼고 쓴다(history_copy — 날마다 쌓여 둘러볼 수 있는 Moody's
시계열을 만들지 않게. 충족 여부·고지·인용은 남긴다). 다만 봇이 날마다 커밋하는 public.json의 git 기록에는 지난 날의 값이
남는다 — 운영자가 같은 회색 지대 결정에서 받아들였다(README '공개 원칙').

산출: <out>/public.json, <out>/history/YYYY-MM-DD.json   (원본 <work>는 사이트 폴더 밖)
사용법: python render_public.py [--work .work] [--out data]
"""
import os, re, sys, json, math, argparse, datetime

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import regime_rules as rr

SCHEMA = 1
REPO = os.path.dirname(SCRIPTS)
DEFAULT_WORK = os.path.join(REPO, ".work")
DEFAULT_OUT = os.path.join(REPO, "data")
FRED_URL = "https://fred.stlouisfed.org/series/{}"
NOTICE = "공개 통계에 사전에 정한 규칙을 적용한 결과다. 투자 판단이나 권유가 아니다."
# 출처 표기 — FRED는 출처와 'FRED 경유'를 함께 적으라고 하고(Citation required/requested), SOFR은 뉴욕 연은 이용약관의
# 참조금리 조항(Use Restrictions — Reference Rates, 2023-06-09 개정)이 정해 둔 고지·면책을 요구한다(2026-09-30 원문 확인).
# 파생값(3개월 변화 등)은 누가 계산했는지 밝히고 뉴욕 연은의 것으로 보이지 않게 한다(같은 약관 Conditions 4).
PUBLISHER = "macro-regime-check (github.com/yun-macrolab)"
SOFR_NOTICE = ("The SOFR data is subject to the Terms of Use posted at newyorkfed.org. The New York Fed is not "
               f"responsible for publication of the SOFR data by {PUBLISHER}, does not sanction or endorse any "
               "particular republication, and has no liability for your use.")
# 약관 원문 그대로(BGCR 구절 포함) — Conditions 1: 뉴욕 연은이 붙인 출처 표시는 그대로 옮긴다
SOFR_DTCC = ("The Secured Overnight Financing Rate (SOFR) Data and Broad General Collateral Rate (BGCR) Data are "
             "calculated using data provided under a license granted to the New York Fed by DTCC Solutions LLC "
             "(\u201cSolutions\u201d), an affiliate of The Depository Trust & Clearing Corporation. Solutions, its affiliates, "
             "and third parties from which they obtained data have no liability for the content of this material.")
SOFR_DERIVED = ("SOFR 3개월 변화는 macro-regime-check가 뉴욕 연은 SOFR 일별 자료(FRED 경유)로 계산한 값이다. "
                "뉴욕 연은이 발표한 값이 아니다.")
SOFR_DERIVED_EN = ("The SOFR 3-month change is computed by macro-regime-check from SOFR data (via FRED); "
                   "it is not published by the New York Fed.")
NOT_AFFILIATED = (f"{PUBLISHER} is not affiliated with the New York Fed. The New York Fed does not sanction, endorse, "
                  f"or recommend any products or services offered by {PUBLISHER}. It is not sponsored by, affiliated with, "
                  "or endorsed by the Federal Reserve Bank of St. Louis or FRED®.")
# Moody's 저작권 고지 — FRED BAA10Y 시리즈 페이지 Notes의 문단 그대로(2026-10-30 확인, FRED 약관 I절: 자료와 함께 나오는 저작권
# 고지를 함께 싣는다). 글자 하나 바꾸지 않는다(test_render_public이 견준다)
MOODYS_NOTICE = ("©2017, Moody's Corporation, Moody's Investors Service, Inc., Moody's Analytics, Inc. and/or their licensors "
                 "and affiliates (collectively, \"Moody's\"). All rights reserved. Moody's ratings and other information "
                 "(\"Moody's Information\") are proprietary to Moody's and/or its licensors and are protected by copyright and "
                 "other intellectual property laws. Moody's Information is licensed to Client by Moody's. MOODY'S INFORMATION "
                 "MAY NOT BE COPIED OR OTHERWISE REPRODUCED, REPACKAGED, FURTHER TRANSMITTED, TRANSFERRED, DISSEMINATED, "
                 "REDISTRIBUTED OR RESOLD, OR STORED FOR SUBSEQUENT USE FOR ANY SUCH PURPOSE, IN WHOLE OR IN PART, IN ANY FORM "
                 "OR MANNER OR BY ANY MEANS WHATSOEVER, BY ANY PERSON WITHOUT MOODY'S PRIOR WRITTEN CONSENT.")
BAA_DERIVED = ("Baa−10년 스프레드의 12개월 저점 대비와 1990년 이후 분위는 macro-regime-check가 FRED의 BAA10Y로 계산한 "
               "값입니다. Moody's가 발표한 값이 아닙니다.")
# FRED 시리즈 페이지에 'Copyrighted: Citation Required' 표시가 붙은 시리즈(2026-10-30 23개 페이지에서 확인) — 값을 싣는 카드에
# 권장 인용을 글자로 함께 싣는다(data_health.citation_required). 나머지는 'Public Domain: Citation Requested'(S&P·ICE는 사전 승인)
CITATION_REQUIRED = ("M2V", "BAA10Y", "T10Y2Y", "T10YIE", "SOFR")
# 꼬리말의 자료 이용 조건 한 줄 — 이 사이트가 싣는 자료의 출처를 모두 덮는다(2026-10-30: 참고 카드 출처가 늘어 다시 씀)
DATA_LICENSE = ("코드는 MIT 라이선스지만 자료와 그것으로 계산한 값은 그 대상이 아니다 — 각 출처의 이용 조건을 따른다. "
                "FRED 경유 자료는 FRED 이용약관과 시리즈별 저작권·인용 표시(시카고 연은 NFCI 신용 하위 지수와 세인트루이스 연은이 "
                "계산한 시리즈는 인용 필요, IMF 두바이 유가는 © International Monetary Fund), "
                "Moody's Baa−10년 스프레드는 FRED 경유 인용 필요 자료(FRED 권장 인용과 Moody's 저작권 고지를 값 곁과 이 꼬리말에 "
                "함께), 나스닥100·Nasdaq CTA AI 지수의 고점 대비 낙폭(정수 %)은 FRED 경유 저작권 자료(FRED 페이지의 저작권 표시와 "
                "권장 인용을 그 카드에 함께), 연준 이사회 웹 사이트의 초과 채권 프리미엄(EBP)은 미 정부 공개 자료, "
                "뉴욕 연은 자료(SOFR·프라이머리 딜러 통계·ACM 기간 프리미엄·회사채 시장 스트레스 지수 CMDI)는 newyorkfed.org 이용약관, "
                "단일종목 CDS 건수·호가는 DTCC가 SEC 규정 Reg SBSR에 따라 공개 배포한 거래 보고, "
                "하이퍼스케일러 조달 숫자는 미 정부 공개 자료인 SEC EDGAR 공시에서 계산한다. "
                "FRED 시리즈의 권장 인용은 공개 JSON 파일의 citation 칸에 싣고, 인용 필요 시리즈는 그 값을 싣는 카드에도 싣는다.")


def nyfed_attribution(year):
    """뉴욕 연은 이용약관 Conditions 2의 기본 출처 형식."""
    return (f"© {year} Federal Reserve Bank of New York. "
            "Content from the New York Fed subject to the Terms of Use at newyorkfed.org.")


def sofr_notices(year):
    """SOFR을 보여 주는 곳(카드·그래프·JSON)에 함께 싣는 고지 — 파생값 표시(한·영), 참조금리 고지·면책, DTCC 문장,
    기본 출처, 관계없음 고지(SOFR 이름을 제목에 쓰므로 가능한 한 눈에 띄게)."""
    return [SOFR_DERIVED, SOFR_DERIVED_EN, SOFR_NOTICE, SOFR_DTCC, nyfed_attribution(year), NOT_AFFILIATED]


def attribution(year):
    """페이지 꼬리말·공개본의 출처 목록."""
    return ["Source: FRED®, Federal Reserve Bank of St. Louis (https://fred.stlouisfed.org/).",
            SOFR_NOTICE, SOFR_DTCC, nyfed_attribution(year),
            "전년비·3개월 변화·상관·비율은 이 저장소 코드가 원자료로 계산한 값이다.",
            NOT_AFFILIATED, MOODYS_NOTICE, DATA_LICENSE]

# FRED 시리즈 고지에서 재배포·파생물을 제한한 시리즈 → 값은 싣지 않고 충족 여부와 FRED 링크만.
# Moody's Baa−10년(BAA10Y)은 2026-10-30 운영자 결정으로 뺐다(값·고지·인용을 함께 싣는다 — 모듈 머리말)
RESTRICTED = {"SP500": "S&P Dow Jones Indices", "BAMLH0A0HYM2": "ICE Data Indices",
              "BAMLC0A0CM": "ICE Data Indices"}
OWNER = {"M2SL": "FRB", "BOGMBASE": "FRB", "M2V": "FRB St. Louis", "WRESBAL": "FRB", "GDP": "BEA",
         "LNFACBW027SBOG": "FRB", "TOTLL": "FRB", "BUSLOANS": "FRB", "THREEFYTP10": "FRB (Kim-Wright)",
         "BAA10Y": "Moody's", "DGS10": "FRB", "T10Y2Y": "FRB St. Louis", "DFII10": "FRB", "T10YIE": "FRB St. Louis",
         "PCEPILFE": "BEA", "CPILFESL": "BLS", "SOFR": "FRBNY", "DEXKOUS": "FRB", "CES5552300001": "BLS",
         "UNRATE": "BLS", **RESTRICTED}
# FRED 시리즈 페이지가 적은 출처(Source) 그대로 — 인용 문구에 쓴다(2026-09-30 22개 시리즈 페이지에서 확인,
# 2026-10-30 23개 모두 시리즈 페이지의 Suggested Citation과 다시 대조 — UNRATE 포함)
_BOARD, _STL = "Board of Governors of the Federal Reserve System (US)", "Federal Reserve Bank of St. Louis"
FRED_SOURCE = {"M2SL": _BOARD, "BOGMBASE": _BOARD, "M2V": _STL, "WRESBAL": _BOARD,
               "GDP": "U.S. Bureau of Economic Analysis", "LNFACBW027SBOG": _BOARD, "TOTLL": _BOARD, "BUSLOANS": _BOARD,
               "THREEFYTP10": _BOARD, "BAA10Y": _STL, "BAMLH0A0HYM2": "Ice Data Indices, LLC",
               "BAMLC0A0CM": "Ice Data Indices, LLC", "SP500": "S&P Dow Jones Indices LLC", "DGS10": _BOARD,
               "T10Y2Y": _STL, "DFII10": _BOARD, "T10YIE": _STL, "PCEPILFE": "U.S. Bureau of Economic Analysis",
               "CPILFESL": "U.S. Bureau of Labor Statistics", "SOFR": "Federal Reserve Bank of New York",
               "DEXKOUS": _BOARD, "CES5552300001": "U.S. Bureau of Labor Statistics",
               "UNRATE": "U.S. Bureau of Labor Statistics"}
# FRED 권장 인용의 시리즈 제목(Suggested Citation 그대로, 2026-09-30 확인)
FRED_TITLE = {
    "M2SL": "M2", "BOGMBASE": "Monetary Base: Total", "M2V": "Velocity of M2 Money Stock",
    "WRESBAL": "Liabilities and Capital: Other Factors Draining Reserve Balances: Reserve Balances with Federal "
               "Reserve Banks: Week Average",
    "GDP": "Gross Domestic Product",
    "LNFACBW027SBOG": "Other Loans and Leases: All Other Loans and Leases: Loans to Nondepository Financial "
                      "Institutions, All Commercial Banks",
    "TOTLL": "Loans and Leases in Bank Credit, All Commercial Banks",
    "BUSLOANS": "Commercial and Industrial Loans, All Commercial Banks",
    "THREEFYTP10": "Term Premium on a 10 Year Zero Coupon Bond",
    "BAA10Y": "Moody's Seasoned Baa Corporate Bond Yield Relative to Yield on 10-Year Treasury Constant Maturity",
    "BAMLH0A0HYM2": "ICE BofA US High Yield Index Option-Adjusted Spread",
    "BAMLC0A0CM": "ICE BofA US Corporate Index Option-Adjusted Spread",
    "SP500": "S&P 500",
    "DGS10": "Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity, Quoted on an Investment Basis",
    "T10Y2Y": "10-Year Treasury Constant Maturity Minus 2-Year Treasury Constant Maturity",
    "DFII10": "Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity, Quoted on an Investment Basis, "
              "Inflation-Indexed",
    "T10YIE": "10-Year Breakeven Inflation Rate",
    "PCEPILFE": "Personal Consumption Expenditures Excluding Food and Energy (Chain-Type Price Index)",
    "CPILFESL": "Consumer Price Index for All Urban Consumers: All Items Less Food and Energy in U.S. City Average",
    "SOFR": "Secured Overnight Financing Rate",
    "DEXKOUS": "South Korean Won to U.S. Dollar Spot Exchange Rate",
    "CES5552300001": "All Employees, Securities, Commodity Contracts, Funds, Trusts, and Other Financial Vehicles, "
                     "Investments, and Related Activities",
    "UNRATE": "Unemployment Rate",
}
_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December")
# 공개 가능한 원본 경고 — 이 문구로 시작하는 것만 싣는다(미수신·경로가 섞인 오류 문구는 자료 신선도 표로 대신)
WARNING_PREFIXES = ("NDFI 계단", "C&I YoY 기준치", "근원 CPI 결측월", "근원 CPI YoY 산출 불가",
                    "실업률 결측월")     # 빠진 달과 계산 방식·개정치 안내뿐(경로·예외 문구 없음, 2026-10-14)


def _obs(key, label, unit, series, field="value", derived=False, computed=False, asof_field="asof", scale=1, digits=3):
    """derived: 재배포 제한 시리즈에서 원값을 되살릴 수 없게 계산한 통계(상관)만. computed: 이 저장소가 원자료로
    계산한 값(전년비·3개월 변화·비율·상관) — 페이지에 '계산값'으로 표시(원 발행처의 값으로 보이지 않게).
    asof_field: 자료일을 읽을 필드 — 값이 가리키는 달이 기준일과 다를 때(직전 12개월 최저 → 그 3개월 평균의 끝 달).
    scale·digits: 싣는 값 = round(원본 × scale, digits) — 비율(0~1)을 비공개 줄의 '{:.1%}'와 같은 숫자로 실을 때."""
    return {"key": key, "label": label, "unit": unit, "series": series, "field": field, "derived": derived,
            "computed": computed or derived, "asof_field": asof_field, "scale": scale, "digits": digits}


def citation(sid, date):
    """시리즈별 출처 문구 — FRED 권장 인용 형식 그대로: 출처, 제목 [ID], retrieved from FRED, …; URL, 날짜.
    날짜는 공개본 기준일(그날 받은 자료). SOFR도 같은 형식(참조금리 고지는 attribution·규칙 notices에 따로)."""
    d = datetime.date.fromisoformat(date)
    return (f"{FRED_SOURCE[sid]}, {FRED_TITLE[sid]} [{sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; "
            f"{FRED_URL.format(sid)}, {_MONTHS[d.month - 1]} {d.day}, {d.year}.")


def public_rules():
    """규칙 key → 공개 문구·관측치 정의·시나리오 이름표. 임계값은 호출 시점의 rr.TH에서 읽는다.
    이름표(scenario)는 원본 규칙 엔진의 것과 같아야 한다 — render가 견주고 다르면 실패한다(검토 없이 바뀌지 않게)."""
    th = rr.TH
    return {
        "ci_vs_ngdp": {
            "title": "기업대출 증가율 대 명목 성장률", "scenario": "A",
            "rule": "C&I 대출 전년비가 명목GDP 전년비보다 낮으면 충족",
            "obs": [_obs("ci_yoy", "C&I 대출 전년비", "%", ["BUSLOANS"], computed=True),
                    _obs("ngdp_yoy", "명목GDP 전년비", "%", ["GDP"], computed=True)]},
        "ndfi_credit": {
            "title": "은행의 비은행 금융기관 대출", "scenario": "A, D",
            "rule": f"전년비(재분류로 보이는 주간 +{th['ndfi_step_bn']:g}십억달러 이상 증가 계단 제외)가 "
                    f"{th['ndfi_two_digit']:g}% 미만이면 충족",
            "obs": [_obs("ndfi_yoy", "NDFI 대출 전년비(계단 제외)", "%", ["LNFACBW027SBOG"], computed=True),
                    _obs("ndfi_share", "총대출 중 비중", "%", ["LNFACBW027SBOG", "TOTLL"], computed=True)]},
        # Baa−10년(Moody's, 2026-10-30부터 공개)은 비공개 월간 점검 줄과 같은 숫자·자릿수 — 수준과 12개월 저점 대비는 소수
        # 둘째 자리(줄의 '{:.2f}'), 1990년 이후 분위(그 값 이하인 관측치 비율)는 소수 첫째 자리 %(줄의 '{:.1%}').
        # HY OAS(ICE)는 그대로 충족 여부만
        "credit_spread": {
            "title": "신용 스프레드", "scenario": "D",
            "rule": f"Baa−10년 스프레드가 12개월 저점보다 {th['spread_widen_pp']:g}%p 이상 넓어지거나 "
                    f"HY OAS가 {th['hy_oas_break']:g}%p를 넘으면 충족",
            "obs": [_obs("baa10y", "Baa−10년 스프레드", "%p", ["BAA10Y"], digits=2),
                    _obs("baa10y", "12개월 저점 대비", "%p", ["BAA10Y"], field="from_low_12m", computed=True, digits=2),
                    _obs("baa10y", "1990년 이후 분위(이 값 이하 비율)", "%", ["BAA10Y"], field="pct_since_1990",
                         computed=True, scale=100, digits=1)],
            "restricted": ["BAMLH0A0HYM2"]},
        "stock_bond_corr": {
            "title": "주가-금리 60영업일 상관", "scenario": "B",
            "rule": f"S&P500 일간 수익률과 미 10년 금리 일간 변화의 60영업일 상관이 "
                    f"{th['corr_run_days']:g}영업일 이상 계속 양(+)이면 충족",
            "obs": [_obs("rho60", "60영업일 상관", "", ["SP500", "DGS10"], derived=True),
                    _obs("rho60", "같은 부호 연속", "영업일", ["SP500", "DGS10"], field="run_days", derived=True)]},
        "curve_inversion": {
            "title": "10년−2년 금리차", "scenario": "D",
            "rule": "10년−2년 금리차가 0보다 작으면 충족",
            "obs": [_obs("t10y2y", "10년−2년", "%p", ["T10Y2Y"])]},
        "real_rate_bei": {
            "title": "실질금리와 기대인플레이션", "scenario": "C",
            "rule": f"10년 실질금리가 {th['real_rate_c']:g}% 미만이고 10년 BEI가 3개월 전보다 높으면 충족",
            "obs": [_obs("dfii10", "10년 실질금리", "%", ["DFII10"]),
                    _obs("bei", "10년 BEI", "%", ["T10YIE"]),
                    _obs("bei_chg_3m", "BEI 3개월 변화", "%p", ["T10YIE"], computed=True)]},
        "core_inflation": {
            "title": "근원 물가", "scenario": "B, D",
            "rule": f"근원 PCE 전년비가 {th['core_pce_split']:g}% 이하이면 충족 (근원 CPI는 참고)",
            "obs": [_obs("core_pce_yoy", "근원 PCE 전년비", "%", ["PCEPILFE"], computed=True),
                    _obs("core_cpi_yoy", "근원 CPI 전년비", "%", ["CPILFESL"], computed=True)]},
        "term_premium": {
            "title": "10년 기간 프리미엄", "scenario": "A",
            "rule": f"10년 기간 프리미엄(Kim-Wright)이 3개월 전보다 {th['tp_drop_3m']:g}%p 이상 낮아지면 충족",
            "obs": [_obs("tp", "기간 프리미엄", "%", ["THREEFYTP10"]),
                    _obs("tp_chg_3m", "3개월 변화", "%p", ["THREEFYTP10"], computed=True)]},
        "sofr": {
            "title": "단기 조달금리 SOFR", "scenario": "A, D",
            "rule": f"SOFR이 3개월 전보다 {th['sofr_rise_3m']:g}%p 이상 높아지면 충족",
            "obs": [_obs("sofr", "SOFR", "%", ["SOFR"]),
                    _obs("sofr_chg_3m", "3개월 변화", "%p", ["SOFR"], computed=True)]},
        "reserves_multiplier": {
            "title": "지준과 통화승수", "scenario": "A, C",
            "rule": f"지준/명목GDP가 {th['reserves_gdp_low']:g}% 미만이거나, 3개월 새 {th['reserves_gdp_rise_3m']:g}%p "
                    f"이상 늘고 근원 PCE 전년비가 {th['reserves_pce_floor']:g}%를 넘으면 충족",
            "obs": [_obs("reserves_gdp", "지준/명목GDP", "%", ["WRESBAL", "GDP"], computed=True),
                    _obs("reserves_gdp_chg_3m", "3개월 변화", "%p", ["WRESBAL", "GDP"], computed=True),
                    _obs("mult", "통화승수(M2/본원통화)", "배", ["M2SL", "BOGMBASE"], computed=True)]},
        "employment": {
            "title": "미 증권·투자업 고용", "scenario": "공통",
            "rule": "고용 전년비가 0보다 작으면 충족",
            "obs": [_obs("emp_yoy", "고용 전년비", "%", ["CES5552300001"], computed=True)]},
        # 아래 둘(2026-10-14)은 문턱을 과거 자료로 고정한 중립 규칙 — '충족'은 조건이 성립한다는 사실만 뜻한다
        "core_momentum": {
            "title": "근원 물가의 최근 속도", "scenario": "—",
            "rule": f"근원 PCE 6개월 연율이 전년비보다 {th['core_mom_gap']:g}%p 이상 높으면 충족 "
                    "(기준 달이 빠진 구간은 계산하지 않음)",
            "obs": [_obs("core_pce_a6", "근원 PCE 6개월 연율", "%", ["PCEPILFE"], computed=True),
                    _obs("core_pce_yoy", "근원 PCE 전년비", "%", ["PCEPILFE"], computed=True),
                    _obs("core_mom", "차이(6개월 연율 − 전년비)", "%p", ["PCEPILFE"], computed=True)]},
        "unemployment_rise": {
            "title": "실업률 상승 폭", "scenario": "—",
            "rule": f"실업률 3개월 평균이 직전 12개월 중 가장 낮은 3개월 평균보다 {th['unrate_rise']:g}%p 이상 높으면 "
                    "충족 (빠진 달이 낀 평균은 2개월로 계산)",
            "obs": [_obs("unrate_rise", "상승 폭(3개월 평균 − 직전 12개월 최저)", "%p", ["UNRATE"], computed=True),
                    _obs("unrate_rise", "실업률 3개월 평균", "%", ["UNRATE"], field="u3", computed=True),
                    _obs("unrate_rise", "직전 12개월 최저 3개월 평균", "%", ["UNRATE"], field="low", computed=True,
                         asof_field="low_month")]},
    }


# ---------- 해석 줄 · 레짐 점검 참고 (2026-10-30 사용자 결정: 비공개 알림 [레짐 점검]의 공개판) ----------

NEUTRAL = "—"                                  # 중립 규칙의 이름표 — '핵심 신호 n/m'에 넣지 않고 따로 센다(비공개 알림과 같다)
NO_VERDICT = "일부 자료 없음(판정 불가)"        # regime_rules._sig가 판정 불가 문장 끝에 붙이는 구절
READING_NOTICE = ("시나리오 이름표(A~D)·해석 구절·국면 참고값은 운영자가 개인 월간 점검에 적어 둔 메모를 옮긴 참고다 — "
                  "예측이 아니라 그날 규칙을 잰 측정 기록이다. 이름표와 구절의 예측력은 검증하지 않았고, 규칙의 충족 여부는 "
                  "규칙 문장만으로 정해진다. 투자 판단이나 권유가 아니다.")
# 해석 쪽을 싣지 못한 곳의 공개 경고 — 이 문구뿐이다(넣는 것은 공개 규칙 제목이나 개수만 — 원본 문장·값·내부 ID는 싣지 않는다)
DROPPED = {
    "reading": "참고 해석 줄을 싣지 않음(검토하지 않은 문구) — {}",
    "label": "참고 이름표와 해석 줄을 싣지 않음(공개 정의와 다른 이름표) — {}",
    "manual": "손으로 보는 항목 {}개를 싣지 않음(검토하지 않은 문구)",
    "note": "레짐 점검 참고의 첫 줄을 싣지 않음(검토하지 않은 판정 메모)",
    "section": "레짐 점검 참고를 싣지 않음(만들지 못함)",
}
HY_HIDDEN = "HY OAS 값 비공개(문턱은 규칙 문장)"   # 신용 스프레드 해석 줄에서 ICE HY OAS 값 자리를 바꾸는 고정 문구
# 숫자 자리의 꼴 — regime_rules.evaluate의 서식 그대로({:+.1f} · {:+.2f} · {:.1f} · {:.2f}). 다른 글자(nan 등)는 맞지 않는다
_S1, _S2, _U1, _U2 = r"[+-]\d+\.\d", r"[+-]\d+\.\d\d", r"-?\d+\.\d", r"-?\d+\.\d\d"


def _o(p):
    """regime_rules._f 자리 — 값이 없으면 '—'."""
    return rf"(?:{p}|—)"


# 신용 스프레드 해석 줄의 Baa−10년 부분(Moody's 값 셋 — 원본 서식 그대로). 날짜별 기록에서는 이 부분을 고정 문구로 바꾼다
BAA_PART = rf"Baa−10Y {_o(_U2)}%p\(바닥 대비 {_o(_S2)}, 1990년 이후 하위 (?:-?\d+\.\d%|—)\)"


def _same(*xs):
    return {x: x for x in xs}


def readings():
    """규칙 key → 원본 해석 문장이 가질 수 있는 꼴(규칙마다 정해 둔 것뿐). plain: 통째로 싣는 문장(화살표 없음 — 자료 없음 등),
    head: ' → ' 앞(공개 시리즈의 값 자리만), clauses: ' → ' 뒤 원본 구절 → 공개 구절(내부 ID는 뺀다).
    public_head가 있으면 원본의 앞부분 대신 head 일치의 expand(public_head)를 싣는다 — 원본 앞부분에 재배포 제한 값이 든
    규칙(credit_spread: Baa 부분(\\1)은 그대로, ICE HY OAS 값 자리는 고정 문구로).
    중립 규칙의 구절은 임계값이 들어 있어 호출 시점의 rr.TH로 만든다."""
    th, nv = rr.TH, {NO_VERDICT: NO_VERDICT}
    fixed = lambda *xs: [re.escape(x) for x in xs]
    return {
        "ci_vs_ngdp": {"plain": fixed("C&I YoY 판정불가(2025-01 분류 단절 이전 기준치 또는 자료 없음)"),
                       "head": rf"C&I {_S1}% vs 명목GDP {_S1}%",
                       "clauses": _same("명목성장률 아래 = A 반증", "상회 = A 진행")},
        "ndfi_credit": {"plain": fixed("NDFI YoY 자료 없음"),
                        "head": rf"NDFI 대출 YoY {_S1}%\(계단 제외\), 총대출의 {_o(_U1)}%",
                        "clauses": _same("두 자릿수 붕괴 = A→D 방아쇠 주의", "두 자릿수 유지 = A 진행")},
        # 원본 앞부분 = Baa−10Y 값(Moody's — 2026-10-30부터 공개) · HY OAS 값(ICE — 재배포 제한). 꼴을 통째로 확인하고
        # Baa 부분은 그대로, HY OAS 값 자리만 고정 문구로 바꾼다(ICE 값은 어디에도 옮기지 않는다)
        "credit_spread": {"plain": fixed("스프레드 자료 없음"),
                          "head": rf"({BAA_PART}) · HY OAS {_o(_U2)}%p",
                          "public_head": r"\1 · " + HY_HIDDEN,
                          "clauses": {**_same("D 선행 신호", "확대 없음(A 유지)"), **nv}},
        "stock_bond_corr": {"plain": fixed("ρ60 자료 없음")
                            + [rf"ρ60 {_S2}, 양\(\+\) \d+영업일째\(126일 미만\)",
                               rf"ρ60 {_S2}, 음\(−\) \d+영업일 지속 = 분산 붕괴·전사 위험 한도 압박"],
                            "head": rf"ρ60 {_S2}, 양\(\+\) \d+영업일 = 126일 복귀",
                            "clauses": _same("B 신호")},
        "curve_inversion": {"plain": fixed("2s10s 자료 없음"), "head": rf"2s10s {_o(_S2)}%p",
                            "clauses": _same("역전 = D 선행", "정상(역전 없음)")},
        "real_rate_bei": {"plain": fixed("실질금리 자료 없음"),
                          "head": rf"10년 실질 {_U2}% · BEI {_o(_U2)}%\(3개월 {_o(_S2)}\)",
                          "clauses": {**_same("실질 2% 하회 + BEI 상승 = C 신호", "실질 2% 아래이나 BEI 상승 없음"),
                                      "실질 2% 위 = C 반증(F-01-C-01)": "실질 2% 위 = C 반증", **nv}},
        "core_inflation": {"plain": fixed("근원 PCE 자료 없음"),
                           "head": rf"근원 PCE {_U2}% \(근원 CPI {_o(_U2)}%, 괴리 {_o(_S2)}%p\)",
                           "clauses": _same("3% 이하 = D1 쪽, SEP 경로 추종이면 B",
                                            "3% 초과 = D2 쪽(붕괴 시 채권 방어 불완전)")},
        "term_premium": {"plain": fixed("기간 프리미엄 자료 없음"), "head": rf"TP\(Kim-Wright\) {_U2}% \(3개월 {_o(_S2)}\)",
                         "clauses": {**_same("하락 = 듀레이션 수요 충분 후보(A 반증, 발행 지속 여부 수동 확인)",
                                             "하락 없음(A 진행)"), **nv}},
        "sofr": {"plain": fixed("SOFR 자료 없음"), "head": rf"SOFR {_U2}% \(3개월 {_o(_S2)}\)",
                 "clauses": {**_same("재상승 = 2021 빈티지 이자보상 재악화·PIK 증가", "재상승 없음"), **nv}},
        "reserves_multiplier": {"plain": fixed("지준/GDP 자료 없음"),
                                "head": rf"승수 {_o(_U2)} · 지준/명목GDP {_U1}% \(3개월 {_o(_S2)}%p\)",
                                "clauses": {**_same("8%대 = 대차대조표 임대료 상승(A)",
                                                    "지준 재확대 + 물가 목표 상회 = C 후보(장기물 매입 여부 수동 확인)",
                                                    "9%대 유지(B 산술)"), **nv}},
        "employment": {"plain": fixed("고용 자료 없음"), "head": rf"증권·투자업 고용 YoY {_S1}%",
                       "clauses": _same("감소 전환 = 인원 조정 시작", "증가 유지(강세장 코호트)")},
        "core_momentum": {"plain": fixed("근원 PCE 6개월 연율 − 전년비 산출 불가(6개월 전·1년 전 같은 달 관측치 없음)"),
                          "head": rf"근원 PCE 6개월 연율 {_o(_U2)}% − 전년비 {_o(_U2)}% = {_S2}%p",
                          "clauses": _same(f"{th['core_mom_gap']:g}%p 이상(6개월 연율이 전년비보다 높음)",
                                           f"{th['core_mom_gap']:g}%p 미만")},
        "unemployment_rise": {"plain": fixed("실업률 3개월 평균 상승 폭 산출 불가(자료 없음 또는 직전 12개월 평균 9개 미만)"),
                              "head": rf"실업률 3개월 평균 {_o(_U2)}%(?:\(\d개월 평균\))? − 직전 12개월 최저 {_o(_U2)}%"
                                      rf"\((?:\d{{4}}-\d{{2}}|—)\) = {_S2}%p",
                              "clauses": _same(f"{th['unrate_rise']:g}%p 이상(현재 개정치 기준)",
                                               f"{th['unrate_rise']:g}%p 미만")},
    }


def reading(key, text, table=None):
    """원본 해석 문장 → 공개 해석 줄, 정해 둔 꼴과 통째로 맞지 않으면 None(그 규칙의 해석 줄만 싣지 않는다 — render가
    DROPPED 경고를 남긴다). 원본 문장은 어디에도 옮기지 않는다(재배포 제한 값이 있을 수 있고, 로그는 공개 저장소에 남는다).
    꼴의 숫자 자리는 서식 그대로라 nan·inf 같은 글자는 맞지 않는다."""
    spec = (table or readings()).get(key)
    if spec is None or not isinstance(text, str):
        return None
    if any(re.fullmatch(p, text) for p in spec["plain"]):
        return text
    head, sep, clause = text.rpartition(" → ")
    m = re.fullmatch(spec["head"], head) if sep and clause in spec["clauses"] else None
    if m:
        return f"{m.expand(spec['public_head']) if 'public_head' in spec else head} → {spec['clauses'][clause]}"
    return None


def legend():
    """레짐 점검 참고의 읽는 법 — 임계값은 rr.TH에서."""
    th = rr.TH
    return [
        f"시나리오 이름표: A~D는 운영자가 미리 정해 둔 네 갈래 시나리오, D1·D2는 D의 두 갈래(근원 PCE 전년비 "
        f"{th['core_pce_split']:g}% 이하·초과), '공통'은 갈래와 무관, '{NEUTRAL}'는 이름표 없는 중립 규칙이다. "
        "이름표의 정의는 운영자 메모라 싣지 않는다.",
        "핵심 신호: 이름표가 있는 규칙 가운데 충족(발동)한 수. 중립 규칙(근원 PCE 모멘텀·실업률 상승 폭)은 '충족'의 방향이 "
        "달라 따로 센다.",
        f"국면 A·A′·B·C: S&P 500 13주 방향 × 미 10년 13주 변화의 사분면 — 주가↑금리↑ A · 주가↑금리↓ C · 주가↓금리↑ A′ · "
        f"주가↓금리↓ B. 주가 ±{th['sp_buf_pct']:g}% 또는 금리 ±{th['y10_buf_bp']:g}bp 안은 완충 구간으로 직전 국면을 따르는데, "
        "직전 국면은 사람이 정하는 값이라 공개 계산에서는 판정불가로 둔다. S&P 500은 재배포가 제한된 지수라 13주 변화의 "
        f"방향만 싣는다(보합 = ±{th['sp_buf_pct']:g}% 안).",
        "ρ60 경보: 국면 후보가 A인데 주가-금리 60영업일 상관이 음(−)이면 'A′ 경보'를 붙인다(운영자 메모의 표시 — 판정 조건 아님).",
        "전환 경계 트리거 넷: t1 하이퍼스케일러 capex 가이던스(수동) · t2 IG OAS 4주 연속 확대 또는 13주 고점(자동 — ICE 지수라 "
        "값은 싣지 않고 ON/OFF만) · t3 반도체 수출(수동) · t4 주가·미 10년 주간 변화 3주 연속 동반 하락(자동, 완성된 주만). "
        "넷 중 둘 이상이면 ON.",
    ]


REGIME_NOTE = {"사분면 판정": "사분면 판정", "재료 없음": "재료 없음"}
BUFFER_NOTE = "완충 구간 — 직전 국면을 따르는데 직전 국면은 사람이 정하는 값이라 공개 계산에는 없음"


def sp_direction(pct):
    """S&P 500 13주 변화 → 방향만(상승·하락·보합). 보합 = 국면 완충 구간(±sp_buf_pct) 안 — classify_regime과 같은 비교."""
    if pct is None:
        return None
    if abs(pct) <= rr.TH["sp_buf_pct"]:
        return "보합"
    return "상승" if pct > 0 else "하락"


def _onoff(v):
    return "ON" if v is True else ("OFF" if v is False else "?")


def regime_reference(raw, warn=None):
    """비공개 알림의 '시트 참고값' 공개판. 국면 후보는 직전 국면 없이 다시 계산하고(공개 계산에는 사람이 정하는 값이 없다),
    S&P 500은 13주 변화의 방향만, 전환 경계 t2(ICE IG OAS)는 ON/OFF만 싣는다. 숫자가 아닌 값(nan·inf)은 없는 값으로 본다.
    판정 메모가 정해 둔 것과 다르면 국면 후보와 첫 줄만 빼고 warn(목록)에 DROPPED['note']를 더한다."""
    ri, ind = raw.get("regime_inputs") or {}, raw["indicators"]
    sp, y10 = _num(ri.get("sp_13w_pct")), _num(ri.get("y10_13w_bp"))
    cand, note = rr.classify_regime(sp, y10, None)
    if note in REGIME_NOTE:
        pub_note = REGIME_NOTE[note]
    elif isinstance(note, str) and note.startswith("완충 구간"):
        pub_note = BUFFER_NOTE
    else:
        cand = pub_note = None
        if warn is not None:
            warn.append(DROPPED["note"])
    direction = sp_direction(sp)
    rho, run = _num(ind.get("rho60", {}).get("value")), _num(ind.get("rho60", {}).get("run_days"))
    alert = bool(cand == "A" and rho is not None and rho < 0)
    cpi, pce = _num(ind.get("core_cpi_yoy", {}).get("value")), _num(ind.get("core_pce_yoy", {}).get("value"))
    lt3 = None if cpi is None else ("Y" if cpi < 3.0 else "N")
    tr = ri.get("transition") or {}
    t2, t4 = _onoff(tr.get("t2")), _onoff(tr.get("t4"))
    auto = sum(1 for k in ("t2", "t4") if tr.get(k) is True)
    f = rr._f
    shown = "—" if direction is None else direction + (f"(±{rr.TH['sp_buf_pct']:g}% 안)" if direction == "보합" else "")
    lines = [
        None if pub_note is None else
        f"국면 후보 {cand or '판정불가'} ({pub_note}) · S&P 500 13주 {shown} · 미 10년 13주 {f(y10, '{:+.0f}')}bp",
        f"ρ60 {f(rho)} ({f(run, '{:.0f}')}일 연속)" + (" ⚠ A 국면에서 음(−) = A′ 경보" if alert else ""),
        f"근원 CPI<3% {lt3 or '?'} (근원 CPI {f(cpi, '{:.2f}')}% · 근원 PCE {f(pce, '{:.2f}')}% — D1/D2 갈림은 근원 PCE 기준)",
        f"전환 경계 자동 트리거 {auto}/2 (t2 {t2} · t4 {t4}; t1·t3 수동, 넷 중 둘 이상이면 ON)",
    ]
    lines = [x for x in lines if x is not None]
    return {"candidate": cand, "candidate_note": pub_note, "sp_13w": direction, "sp_asof": ri.get("sp_asof"),
            "y10_13w_bp": None if y10 is None else round(y10, 1), "y10_asof": ri.get("y10_asof"),
            "rho60": _round(rho), "rho60_run_days": None if run is None else int(run), "rho60_alert": alert,
            "core_cpi_lt3": lt3, "core_cpi_yoy": _round(cpi), "core_pce_yoy": _round(pce),
            "transition": {"t2": t2, "t4": t4, "auto_on": auto}, "lines": lines}


# 손으로 보는 항목 — 원본(regime_rules.MANUAL)의 ID → 공개 문구. 내부 ID(판단 기록 번호)는 싣지 않는다
MANUAL_PUBLIC = {
    "F-00-15": "비상장 BDC 환매 요청률(한도 5%) · bad PIK 비중 · 직접대출 디폴트율",
    "F-00-16": "하이퍼스케일러 capex 가이던스 · capex/OCF · 5사 회사채 발행 누계",
    "F-00-17": "Z.1 생보 회사채 순취득(FA543063005) · Athene 순스프레드(2분기 연속 1.0% 하회 여부)",
    "F-00-11": "한국: 국고 10-30 · 3년−기준금리 · CP·전단채 스프레드 · 발행어음 잔액 · 일평균 거래대금 · "
               "국민연금 국내주식 비중 대 목표",
    "F-00-02": "연준 장기물 매입 재개 여부(지준/GDP 상승과 함께 읽을 것) · 재무부 단기물 편중 발행",
    "S-01-A-02": "하이퍼스케일러 capex 가이던스 상향 지속 여부",
}
CADENCES = ("월", "분기")


def manual_checks(raw, warn=None):
    """원본 수동 항목 → [{cadence, item}] (원본 순서). 모르는 ID·주기·꼴의 항목은 그 항목만 빼고, 뺀 수를 warn(목록)에
    DROPPED['manual']로 남긴다(ID·원본 글은 싣지 않는다)."""
    out, dropped = [], 0
    for m in raw.get("manual") or []:
        if not (isinstance(m, (list, tuple)) and len(m) == 3 and isinstance(m[0], str) and m[0] in MANUAL_PUBLIC
                and m[1] in CADENCES):
            dropped += 1
            continue
        out.append({"cadence": m[1], "item": MANUAL_PUBLIC[m[0]]})
    if dropped and warn is not None:
        warn.append(DROPPED["manual"].format(dropped))
    return out


# 아직 싣지 않던 공개 관측값 — regime_check가 이미 받는 시리즈뿐(재배포 제한 시리즈 없음)
MORE_VALUES = [   # (지표 key, 이름, 단위, 시리즈, 계산값)
    ("m2", "M2", "십억 달러", ["M2SL"], False),
    ("m2_yoy", "M2 전년비", "%", ["M2SL"], True),
    ("mb", "본원통화", "십억 달러", ["BOGMBASE"], False),
    ("mb_yoy", "본원통화 전년비", "%", ["BOGMBASE"], True),
    ("m2v", "M2 유통속도", "배", ["M2V"], False),
    ("ndfi_level", "NDFI 대출 잔액", "십억 달러", ["LNFACBW027SBOG"], False),
    ("gdp", "명목GDP(연율)", "십억 달러", ["GDP"], False),
    ("dexkous", "원/달러", "원", ["DEXKOUS"], False),
    ("emp_level", "미 증권·투자업 고용", "천 명", ["CES5552300001"], False),
    ("unrate", "실업률", "%", ["UNRATE"], False),
    ("core_gap", "근원 CPI − 근원 PCE 전년비", "%p", ["CPILFESL", "PCEPILFE"], True),
]


def more_values(ind, date):
    """그 밖의 관측값. 인용 필요 시리즈(CITATION_REQUIRED — 지금은 세인트루이스 연은이 계산한 M2V)는 값 곁에 싣게
    FRED 권장 인용(citation)을 함께 넣는다."""
    out = []
    for key, label, unit, series, computed in MORE_VALUES:
        o = {"label": label, "unit": unit, "series": series, "computed": computed,
             "value": _round(ind.get(key, {}).get("value")), "asof": ind.get(key, {}).get("asof")}
        cites = [citation(sid, date) for sid in series if sid in CITATION_REQUIRED]
        if cites:
            o["citation"] = " ".join(cites)
        out.append(o)
    return out


def regime_section(raw, rules, warn=None):
    """public.json의 regime 절 — 핵심 신호 n/m(중립 규칙은 따로), 읽는 법, 국면 참고값, 손으로 보는 항목, 그 밖의 관측값.
    이름표를 싣지 못한 규칙(scenario None)은 어느 셈에도 넣지 않는다."""
    core = [r for r in rules if r["scenario"] not in (NEUTRAL, None)]
    neu = [r for r in rules if r["scenario"] == NEUTRAL]
    cnt = lambda rs, k: sum(1 for r in rs if r["status"] == k)
    head = f"핵심 신호 {cnt(core, 'met')}/{len(core)} 발동, 판정불가 {cnt(core, 'unknown')}"
    if neu:
        head += f" · 중립 규칙 {cnt(neu, 'met')}/{len(neu)} 충족"
    return {"notice": READING_NOTICE, "headline": head,
            "core": {"total": len(core), "met": cnt(core, "met"), "unknown": cnt(core, "unknown")},
            "neutral": {"total": len(neu), "met": cnt(neu, "met"), "unknown": cnt(neu, "unknown")},
            "reference": regime_reference(raw, warn), "manual_checks": manual_checks(raw, warn),
            "more_values": more_values(raw["indicators"], raw["date"]), "legend": legend()}


def _num(v):
    """유한한 실수만 — 그 밖(None·nan·inf·글자·참거짓)은 None. 공개본 JSON에 NaN이 들어가면 화면이 파일을 읽지 못한다."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return v


def _round(v, scale=1, digits=3):
    v = _num(v)
    return None if v is None else round(v * scale, digits)


def rule_notices(key, date):
    """규칙 카드에 함께 싣는 고지 — SOFR은 참조금리 고지, 신용 스프레드는 Baa 계산값 표시·FRED 권장 인용·Moody's 고지(값 곁에)."""
    if key == "sofr":
        return sofr_notices(int(date[:4]))
    if key == "credit_spread":
        return [BAA_DERIVED, citation("BAA10Y", date), MOODYS_NOTICE]
    return []


def _status(fired):
    return "met" if fired is True else ("not_met" if fired is False else "unknown")


def render(raw):
    """원본 결과 dict → 공개본 dict. public_rules()에 없는 규칙이 있으면 RuntimeError. 해석 쪽(이름표·해석 문장·수동
    항목·국면 메모)은 검토 안 된 것만 빼고 DROPPED 경고를 warnings 끝에 남긴다 — regime 절을 아예 만들지 못하면 그 절만 null."""
    table = public_rules()
    unknown = [s["key"] for s in raw["signals"] if s["key"] not in table]
    if unknown:
        raise RuntimeError(f"공개 문구가 없는 규칙 {unknown} — render_public.public_rules()에 추가하고 검토할 것")
    ind = raw["indicators"]
    year = int(raw["date"][:4])
    texts = readings()
    rules, dropped = [], []
    for s in raw["signals"]:
        spec = table[s["key"]]
        if s.get("scenario") == spec["scenario"]:
            scenario, line = spec["scenario"], reading(s["key"], s.get("text"), texts)
            if line is None:
                dropped.append(DROPPED["reading"].format(spec["title"]))
        else:                                          # 이름표가 바뀐 규칙 — 해석 쪽만 빼고 규칙은 그대로 싣는다
            scenario = line = None
            dropped.append(DROPPED["label"].format(spec["title"]))
        obs = [{"label": o["label"], "unit": o["unit"], "series": o["series"], "derived": o["derived"],
                "computed": o["computed"],
                "value": _round(ind.get(o["key"], {}).get(o["field"]), o["scale"], o["digits"]),
                "asof": ind.get(o["key"], {}).get(o["asof_field"])}
               for o in spec["obs"]]
        rules.append({"key": s["key"], "title": spec["title"], "rule": spec["rule"], "status": _status(s["fired"]),
                      "scenario": scenario, "reading": line,
                      "observations": obs,
                      "restricted_series": [{"series": sid, "owner": RESTRICTED[sid], "url": FRED_URL.format(sid)}
                                            for sid in spec.get("restricted", [])],
                      "notices": rule_notices(s["key"], raw["date"])})
    health = []
    for sid, (label, freq, _) in rr.SERIES.items():
        src = raw["sources"].get(sid, {})
        age = src.get("age_days")
        health.append({"series": sid, "label": label, "owner": OWNER.get(sid, ""), "url": FRED_URL.format(sid),
                       "last": src.get("last"), "age_days": age,
                       "fetched": src.get("source") or "missing",
                       "stale": bool(age is not None and age > rr.STALE_DAYS[freq]),
                       "display": "status_only" if sid in RESTRICTED else "value",
                       "citation_required": sid in CITATION_REQUIRED,
                       "citation": citation(sid, raw["date"])})
    counts = {k: sum(1 for r in rules if r["status"] == k) for k in ("met", "not_met", "unknown")}
    try:
        part = []
        regime = regime_section(raw, rules, part)
        dropped += part
    except Exception:                                  # 참고 절 하나 때문에 공개본 전체가 멈추지 않게(원본 글은 싣지 않는다)
        regime = None
        dropped.append(DROPPED["section"])
    return {"schema": SCHEMA, "date": raw["date"],
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "notice": NOTICE, "attribution": attribution(year),
            "summary": {"total": len(rules), **counts}, "rules": rules,
            "regime": regime,
            "data_health": health,
            "warnings": public_warnings(raw) + dropped}


def public_warnings(raw):
    """원본 경고 가운데 공개 가능한 것(WARNING_PREFIXES로 시작하는 글)만."""
    return [w for w in raw.get("warnings", []) if isinstance(w, str) and w.startswith(WARNING_PREFIXES)]


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


# 날짜별 기록(history/)에서 Moody's Baa−10년 값을 뺀 자리 — 2026-10-30 회색 지대 결정은 그날 공개본의 값 셋까지다(날마다 쌓아
# 둘러볼 수 있는 Moody's 시계열을 만들지 않는다). 충족 여부·고지·인용은 기록에도 남긴다
BAA_HISTORY = "Baa−10Y 값은 그날 공개본에만(날짜별 기록에는 싣지 않음)"


def history_copy(pub):
    """공개본 → 날짜별 기록 사본: 신용 스프레드 카드의 BAA10Y 관측값(수준·12개월 저점 대비·1990년 이후 분위)을 null로, 해석 줄의
    Baa 부분을 BAA_HISTORY로. 상태(충족 여부)·고지·인용·자료 상태는 그대로. 꼴을 알아보지 못한 해석 줄에 Baa가 있으면 줄을
    싣지 않는다(닫힌 채 실패). 공개본(pub)은 고치지 않는다."""
    h = json.loads(json.dumps(pub, allow_nan=False))
    for r in h.get("rules") or []:
        if r.get("key") != "credit_spread":
            continue
        for o in r.get("observations") or []:
            if "BAA10Y" in (o.get("series") or ()):
                o["value"] = None
        line = r.get("reading")
        if isinstance(line, str) and "Baa" in line:
            m = re.fullmatch(rf"{BAA_PART}( · .*)", line, re.S)
            r["reading"] = BAA_HISTORY + m.group(1) if m and "Baa" not in m.group(1) else None
    return h


def write(out, pub):
    """history/<날짜>.json(Baa 값을 뺀 사본 — history_copy)은 항상, public.json은 기존 공개본보다 날짜가 같거나 늦을 때만.
    public.json을 썼으면 True."""
    text = json.dumps(pub, ensure_ascii=False, indent=2, allow_nan=False)    # NaN이 섞이면 쓰지 않는다(화면이 못 읽는다)
    hist = os.path.join(out, "history")
    os.makedirs(hist, exist_ok=True)
    _write_text(os.path.join(hist, f"{pub['date']}.json"),
                json.dumps(history_copy(pub), ensure_ascii=False, indent=2, allow_nan=False))
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
            raw = json.load(f)
        pub = render(raw)
        wrote = write(os.path.abspath(a.out), pub)
    except (RuntimeError, ValueError, KeyError) as e:
        print(f"[render_public] {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
    sm = pub["summary"]
    n_drop = len(pub["warnings"]) - len(public_warnings(raw))
    print(f"[render_public] {pub['date']} 공개본 — 규칙 {sm['total']}개 중 충족 {sm['met']} · 판정 불가 {sm['unknown']}"
          + (f" · 참고 {n_drop}건 싣지 않음(warnings)" if n_drop else "")
          + ("" if wrote else " · 더 최근 공개본이 있어 history에만 기록"))



if __name__ == "__main__":
    main()
