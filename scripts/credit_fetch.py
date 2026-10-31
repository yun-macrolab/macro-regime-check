#!/usr/bin/env python3
"""참고 자료 — 신용 긴축 단계(규칙 C)와 그 곁의 측정 기록 (2026-10-30 추가, 사용자 결정: 비공개 줄 공개).

운영자의 비공개 월간 점검 [신용 긴축] 블록(비공개 원본 credit_block.py)을 공개한 것이다 — 같은 산식을 여기서 따로 쓴다(코드는
가져오지 않는다. 산식·문턱을 고치면 양쪽을 같이). 규칙 판정·공개본·그래프 스크립트는 이 파일(<out>/credit.json)을 읽지 않고,
단계는 이 사이트의 규칙 수에 들지 않는다. 칸(ITEMS — 화면 차례):
  stage     규칙 C 신용 긴축 단계 0/1/2 (문턱 고정 2026-10-29 · 예측력 미검증 — 1990년 이후 자기 분위):
              S   = DRTSCILM(SLOOS 대·중견기업 C&I 대출 기준 순긴축 %, 분기) 최신 조사 — 조사월 +1개월부터 쓴다
              N13 = NFCICREDIT(시카고 연은 NFCI 신용 하위 지수, 주간) 13주 변화(91일 전에서 6일 안의 마지막 관측) · NL = 그 수준
              2단계: S ≥ S2 그리고 (N13 ≥ N2 또는 NL ≥ NL2) · 1단계: 그 밖에 S ≥ S1 또는 N13 ≥ N1 · 0단계: 그 밖
            묵은 자료(NFCI 마지막 관측이 14일 넘음, SLOOS가 조사월부터 150일 넘음)는 그 계기를 모름으로 두고 3값 논리 —
            단계가 그래도 정해지면 적고, 아니면 '?'와 가능한 범위. 비교는 반올림 전 값으로, 비교 안에서만 소수 6자리 반올림
            (regime_rules._cmp·_and·_or를 import만 한다). 분위(p)는 1990년 이후 자기 시계열에서 값 이하 비율.
            측정 기록 줄(검증 약함, 긴축 쪽만 — 완화 쪽은 숫자만)과 측정상 경로 참고 줄을 덧붙인다(예측 아님).
  ebp       신용 스트레스(공개 자료) — 연준 이사회 초과 채권 프리미엄(EBP, ebp_csv.csv — 월간, 1973년부터, 매달 전 표본을
            다시 추정): 마지막 달 EBP(bp)·같은 파일 전 표본 분위·정확히 3개월 전 달 대비 변화(bp)·같은 달 GZ 스프레드(bp).
            침체 확률 열(est_prob)은 예측 값이라 읽지도 싣지도 않는다
  cmdi      신용 스트레스(공개 자료) — 뉴욕 연은 회사채 시장 스트레스 지수(CMDI, Market CMDI.xlsx — 주간 0~1, 매달 마지막
            수요일쯤 갱신): 시장 전체(열 'Market CMDI')와, 있으면 투자등급·하이일드 열 — 열마다 마지막 주 값·날짜·자기 전 표본
            분위·정확히 28일 전 관측 대비 4주 변화(없으면 적지 않는다). 머리글은 정해 둔 낱말(CMDI_WORDS)로만 이루어졌을 때만
            세 이름표(시장 전체·투자등급·하이일드)에 붙이고, 모르는 열은 버린다. 실행마다 통합 문서의 시트 이름과 머리글 칸(값 없이)을
            표준 출력에 찍는다 — 첫 CI 실행에서 꼴을 확인하게
            두 칸은 운영자의 비공개 ICE 회사채 등급별 스프레드 사다리(이용 조건상 공개 불가)를 대신하는 공개 자료다
  cell      AI 투자 칸 — 투자 축(정보처리 장비·SW 투자/명목 GDP의 4분기 변화 > 0 '확장', 아니면 '소화') × 조달 축(비금융기업
            설비투자/내부자금 4분기 합 > 1985년 이후 중앙값 '부채 조달', 아니면 '현금 조달' — ai_invest_fetch.calc_financing
            그대로). 금리 방향이 없는 서술 꼬리표다
  gap       자금 부족 조건 — 주가 조정 뒤 단기 금리가 내린 경로가 측정된 조건(설비투자/내부자금 > 중앙값)에 지금 드는지와
            1990년 이후 분위
  drawdown  주가 낙폭 — 나스닥100·Nasdaq CTA AI 지수의 252영업일 고점 대비 지금 낙폭(정수 % — 비공개 원본이 저장하는 소수 둘째
            자리로 먼저 반올림하고, 그 값의 0.5는 0에서 먼 쪽으로, −0은 0)과 그 구간('10% 안'·'10~20% 아래'·'20% 넘게 아래' — 반올림 전 값으로), 최근 126영업일
            안의 −10%/−20% 첫 진입 날짜(앞 126영업일에 그 낙폭이 없던 날). 2026-10-30 운영자 결정(재배포 제한 자료의 회색 지대,
            위험 감수): 지수마다 정수 낙폭 % 하나만 더 싣는다 — 지수 값·12개월 고점·수익률·낙폭 시계열은 여전히 파일·문구 어디에도
            쓰지 않는다. FRED 시리즈 쪽의 저작권 표시(COPYRIGHT — FRED 페이지의 깨진 'Â©'는 '©'로)와 FRED 권장 인용을 함께
            싣는다. 단계를 바꾸지 않는다
  sec       기업별 조달 — 같은 실행에서 먼저 쓴 <out>/sec.json(scripts/sec_fetch.py)의 칸을 검사해 다시 만든 것. 파일이
            없거나 깨졌으면 이 파일의 직전 값을 받지 못함으로

자료 이용 조건(2026-10-30 FRED 시리즈 쪽 license 확인 — LICENCE): DRTSCILM·BEA·연준 Z.1은 'Public Domain: Citation Requested',
NFCICREDIT은 'Copyrighted: Citation Required'(시카고 연은 — FRED 권장 인용을 함께 싣는다), NASDAQ100·NASDAQNQINTEL은
'Copyrighted: Pre-Approval Required'(재배포 제한 — 정수 낙폭 %·구간·날짜만, 저작권 표시·FRED 권장 인용과 함께).
FRED 밖(EXT): EBP는 연준 이사회 웹사이트 자료(따로 표시가 없으면 공공 영역 — 이사회 인장은 쓰지 않는다, 논문 인용과 출처 줄),
CMDI는 newyorkfed.org 이용약관(기본 출처 표시 · 계산값 표시 · 관계없음 고지 · 논문 인용 — tp_fetch의 ACM과 같은 틀).
요청 머리글: FRED는 기본 그대로(커스텀 User-Agent를 붙이면 FRED가 응답을 멈춘다 — fred_fetch 참고), 연준 이사회·뉴욕 연은에만
이 프로젝트를 밝히는 User-Agent(UA — 연락처·이메일 없음). 요청마다 min(REQ_TIMEOUT, 남은 예산)초, 다른 호스트로 넘겨지면 받지 않는다.

실패·이어 싣기·문구 원칙은 oil_fetch와 같다: 칸마다 따로(칸의 시리즈 가운데 하나라도 이번에 받지 못하면 직전 숫자를 '받지 못함'과
그날부터라는 날짜와 함께), 받은 자료가 직전보다 이르면 받지 않는다, 문구는 이 파일에 정해 둔 것뿐, 같은 내용이면 다시 쓰지
않는다, 수신 전체 BUDGET초(요청 10번 — FRED 8 · EBP · CMDI).

종료코드: 0 한 칸이라도 이번에 받음 / 1 하나도 못 받음(또는 파일을 쓰지 못함). 워크플로 단계는 continue-on-error, 알림 없음.

사용법: python scripts/credit_fetch.py [--out data] [--work .work] [--offline]   (sec_fetch.py 다음에)
  --offline: 요청하지 않고 <work>/credit/의 캐시(FRED CSV·ebp_csv.csv·Market_CMDI.xlsx)만 읽는다
"""
import os, re, io, sys, csv, json, math, time, zlib, zipfile, argparse, datetime, posixpath
import urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from collections import deque

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import fred_fetch as ff
import regime_rules as rr                     # _cmp·_and·_or만 쓴다(공유 파일 — 고치지 않는다)
import render_public as rp
import ai_invest_fetch as ai                  # 수신·쓰기·분기 비율·calc_financing을 그대로 쓴다
import sec_fetch as sf

D = datetime.date
SCHEMA = 1
REPO = os.path.dirname(SCRIPTS)
DEFAULT_OUT = os.path.join(REPO, "data")
DEFAULT_WORK = os.path.join(REPO, ".work")
FILE = "credit.json"
CACHE = "credit"                              # <work>/credit/<ID>.csv · ebp_csv.csv · Market_CMDI.xlsx
BUDGET = 60                                   # 수신 전체(초) — 워크플로 단계 제한(2분) 안에서
REQ_TIMEOUT = 10                              # 요청 하나엔 min(이것, 남은 예산) — FRED·연준 이사회·뉴욕 연은 모두
MAX_BYTES = 5_000_000                         # FRED 밖 응답 하나의 상한
XLSX_MAX_MEMBER = 20_000_000                  # 통합 문서 안 XML 하나를 풀었을 때의 상한
# 연준 이사회·뉴욕 연은 요청에만 다는 머리글 — 이 프로젝트를 밝히고 연락처(이메일)는 싣지 않는다. FRED에는 달지 않는다
UA = "macro-regime-check/1.0 (+https://github.com/yun-macrolab/macro-regime-check)"
EBP, CMDI = "EBP", "CMDI"
EBP_HOST = "www.federalreserve.gov"
EBP_URL = f"https://{EBP_HOST}/econres/notes/feds-notes/ebp_csv.csv"
CMDI_HOST = "www.newyorkfed.org"
CMDI_URL = f"https://{CMDI_HOST}/medialibrary/research/interactives/cmdi/downloads/Market%20CMDI.xlsx"
EBP_MAX_PP, GZ_MAX_PP = 20.0, 50.0            # 퍼센트포인트 단위가 아닌 꼴(bp 등)이면 넘는다 — 넘으면 꼴을 알아보지 못함으로
EBP_BACK = 3                                  # 3개월 변화 — 정확히 3개월 전 달
CMDI_BACK = 28                                # 4주 변화 — 정확히 28일 전 관측
CMDI_KEYS = ("market", "ig", "hy")
CMDI_LABEL = {"market": "시장 전체", "ig": "투자등급", "hy": "하이일드"}
# CMDI 머리글 낱말 — 머리글이 이 낱말로만 이루어졌을 때만 이름표를 붙인다(그 밖은 버린다: 업종별·변화 열 등)
CMDI_WORDS = {"market", "cmdi", "index", "corporate", "bond", "distress", "level", "ig", "hy", "investment", "grade",
              "high", "yield", "speculative"}

FIXED = "2026-10-29"                          # 문턱 고정일(비공개 references/credit.md '문턱 고정 기록')
# 문턱(고정 2026-10-29, 예측력 미검증) — 1990년 이후 자기 분위. 비공개 원본 credit_block.py와 같은 값
S1, S2 = 10.0, 24.2                           # DRTSCILM p70 · p80
N1, N2 = 0.077, 0.148                         # NFCICREDIT 13주 변화 p80 · p90
NL2 = 0.183                                   # NFCICREDIT 수준 p80
NFCI_STALE, SLOOS_STALE = 14, 150             # 일 — 넘으면 그 계기를 모름으로
SLOOS_LAG = 1                                 # 조사월 +1개월부터
WEEKS13, NEAR_DAYS = 91, 6
SINCE = D(1990, 1, 1)
DD_WINDOW, DD_REST = 252, 126                 # 12개월 고점(영업일) · 첫 진입 = 앞 126영업일에 그 낙폭이 없던 날
DD_LEVELS = (10, 20)
WARN = {"NASDAQ100": "나스닥100", "NASDAQNQINTEL": "AI 지수"}
BAND_NAME = {"in10": "10% 안", "10to20": "10~20% 아래", "over20": "20% 넘게 아래"}
# 구간 코드 → 정수 낙폭 %가 놓일 수 있는 범위(반올림 때문에 경계 −10·−20은 양쪽에 들 수 있다) — 직전 파일 검사
BAND_RANGE = {"in10": (-10, 0), "10to20": (-20, -10), "over20": (-100, -20)}

_BOARD, _BEA = "Board of Governors of the Federal Reserve System (US)", "U.S. Bureau of Economic Analysis"
# FRED 권장 인용의 출처·제목(2026-10-30 시리즈 쪽 제목 그대로)
SOURCES = {
    "DRTSCILM": (_BOARD, "Net Percentage of Domestic Banks Tightening Standards for Commercial and Industrial Loans to "
                         "Large and Middle-Market Firms"),
    "NFCICREDIT": ("Federal Reserve Bank of Chicago", "Chicago Fed National Financial Conditions Credit Subindex"),
    "A679RC1Q027SBEA": ai.SOURCES["A679RC1Q027SBEA"],
    "GDP": ai.SOURCES["GDP"],
    "BOGZ1FA105050005Q": ai.SOURCES["BOGZ1FA105050005Q"],
    "BOGZ1FA106000135Q": ai.SOURCES["BOGZ1FA106000135Q"],
    # 두 Nasdaq 지수의 출처·제목은 2026-10-30 FRED 시리즈 쪽 Suggested Citation 그대로(이 환경에서 확인)
    "NASDAQ100": ("Nasdaq, Inc.", "NASDAQ-100"),
    "NASDAQNQINTEL": ("Nasdaq, Inc.", "Nasdaq Consumer Technical Association Artificial Intelligence Index"),
}
LICENCE = {sid: "public-domain" for sid in SOURCES}
LICENCE.update({"NFCICREDIT": "citation-required", "NASDAQ100": "restricted", "NASDAQNQINTEL": "restricted"})
RESTRICTED = {sid for sid, v in LICENCE.items() if v == "restricted"}
# FRED 시리즈 쪽 Notes의 저작권 표시(2026-10-30 확인 — NASDAQ100 쪽의 깨진 'Â©'는 '©'로 고쳐 싣는다)
COPYRIGHT = {"NASDAQ100": "Copyright © 2016, NASDAQ OMX Group, Inc.",
             "NASDAQNQINTEL": "Copyright © 2025, NASDAQ, Inc."}
SERIES = list(SOURCES)                        # FRED — 차례 = 요청 차례
# FRED 밖 자료(EXT) — FRED 8개 다음에 받는다
EBP_PAPER = ('Favara, Gilchrist, Lewis and Zakrajšek (2016), "Updating the Recession Risk and the Excess Bond Premium," '
             'FEDS Notes, Board of Governors of the Federal Reserve System')
CMDI_PAPER = ('Boyarchenko, Crump, Kovner and Shachar, "Corporate Bond Market Distress," FRBNY Staff Report 957')
EXT = {
    EBP: {"url": EBP_URL, "host": EBP_HOST, "cache": "ebp_csv.csv", "name": "Board of Governors of the Federal Reserve System",
          "title": EBP_PAPER, "licence": "public-domain"},
    CMDI: {"url": CMDI_URL, "host": CMDI_HOST, "cache": "Market_CMDI.xlsx", "name": "Federal Reserve Bank of New York",
           "title": "Federal Reserve Bank of New York, Corporate Bond Market Distress Index (Market CMDI)",
           "licence": "nyfed-terms"},
}
FETCH = SERIES + [EBP, CMDI]                  # 요청 차례(10번)

NOTICE = ("이 사이트의 규칙 점검에 쓰지 않는 참고 자료다. 신용 긴축 단계는 정해 둔 문턱으로 지금 숫자를 적은 것이고 예측력은 "
          "검증하지 않았다. 측정 기록은 운영자가 과거 자료로 잰 숫자이고 금리를 예측하지 않는다.")
COMPUTED_NOTICE = "13주 변화·분위·비율·중앙값은 macro-regime-check가 원자료로 계산한 값이다."
CITATION_NOTICE = ("NFCICREDIT은 FRED에서 'Copyrighted: Citation Required'로 표시된 시카고 연은 자료라 FRED 권장 인용을 "
                   "함께 싣는다.")
RESTRICTED_NOTICE = ("나스닥100·Nasdaq CTA AI 지수는 FRED에서 'Copyrighted: Pre-Approval Required'로 표시된 재배포 제한 자료라 "
                     "지수 값·12개월 고점·수익률·낙폭 시계열은 싣지 않는다. 252영업일 고점 대비 지금 낙폭(지수마다 정수 % 하나)·"
                     "구간·날짜만 macro-regime-check가 그 자료(FRED 경유)로 계산해 FRED 권장 인용과 함께 싣는다.")
COPYRIGHT_NOTICE = ("저작권 표시(FRED 시리즈 쪽 그대로): NASDAQ-100 [NASDAQ100] " + COPYRIGHT["NASDAQ100"] +
                    " · Nasdaq CTA AI [NASDAQNQINTEL] " + COPYRIGHT["NASDAQNQINTEL"])
# 신용 스트레스(공개 자료) — EBP · CMDI의 고지
EBP_NOTICE = ("EBP·GZ 스프레드의 bp 환산·3개월 변화·분위는 macro-regime-check가 연준 이사회 자료(ebp_csv.csv)로 계산한 값이다. "
              "같은 파일의 침체 확률 열은 예측 값이라 싣지 않는다.")
EBP_CITE = EBP_PAPER + "."
EBP_SOURCE = "Source: Board of Governors of the Federal Reserve System (ebp_csv.csv), site calculations."
EBP_PD = ("연준 이사회 웹사이트의 자료는 따로 표시가 없으면 공공 영역(public domain)이라 출처를 밝혀 싣는다. "
          "이사회 인장은 쓰지 않는다.")
CMDI_DERIVED = ("CMDI 4주 변화·분위는 macro-regime-check가 뉴욕 연은 CMDI 자료(Market CMDI.xlsx)로 계산한 값이다. "
                "뉴욕 연은이 발표한 값이 아니다.")
CMDI_DERIVED_EN = ("Changes and percentiles are computed by macro-regime-check from the New York Fed Corporate Bond Market "
                   "Distress Index data (Market CMDI.xlsx); they are not New York Fed values.")
CMDI_CITE = CMDI_PAPER + "."
# 단계 정의 — 화면(site/credit.js의 STAGE_DEF)이 늘 함께 싣는 글과 같다(테스트가 견준다)
STAGE_DEF = (f"규칙 C(문턱 고정 {FIXED}, 예측력 미검증): S = SLOOS 대·중견기업 C&I 대출 기준 순긴축(%)의 최신 조사, "
             "N13 = NFCI 신용 하위 지수의 13주 변화, NL = 그 수준. "
             f"2단계: S ≥ {S2:g} 그리고 (N13 ≥ +{N2:g} 또는 NL ≥ +{NL2:g}). "
             f"1단계: 그 밖에 S ≥ {S1:g} 또는 N13 ≥ +{N1:g}. 0단계: 그 밖. "
             "문턱은 각 시계열의 1990년 이후 분위다(SLOOS p70·p80, 13주 변화 p80·p90, 수준 p80). "
             f"SLOOS가 조사월부터 {SLOOS_STALE}일, NFCI가 마지막 관측부터 {NFCI_STALE}일을 넘으면 그 계기는 모름으로 두고, "
             "단계가 그래도 정해지면 적고 아니면 '?'와 가능한 범위를 적는다.")
HYPO = ("측정 기록(검증 약함, 긴축 쪽만): 운영자가 1990년 이후 자료로 잰 회귀에서 SLOOS 순긴축이 10%p 높으면 12개월 뒤 "
        "2년 금리 −19bp · 정책금리 −21bp · 10년 ≈ 0이었다(2년·정책금리 t ≈ −3, 10년 t −0.7). 앞쪽 금리가 더 내린 쪽"
        "(불 스티프닝)이다. 예측이 아니다.")
EASING = " 지금은 완화 쪽(SLOOS < 0)이라 숫자만 싣고 이 기록을 대지 않는다."
PATH_NOTE = ("측정상 경로 참고(2년 금리, 6개월): 1단계 ≈ −10bp, 2단계 ≈ −25bp — SLOOS 문턱 10·24.2에 회귀 계수(순긴축 "
             "10%p당 6개월 −10.3bp)를 곱한 산술이다. 예측이 아니다.")
REASONS = {
    "fetch": "수신 실패",
    "cache": "수신 실패 · 묵은 캐시는 싣지 않음",
    "format": "계산할 자료가 모자람",
    "older": "받은 자료가 직전 자료보다 오래됨",
    "sec_file": "SEC 자료 파일을 읽지 못함",
    "layout": "받은 파일의 꼴을 알아보지 못함",
}


class ItemError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class LayoutError(Exception):
    """FRED 밖 파일의 꼴을 알아보지 못함(머리글·열·단위·XML 구조) — 그 자료만 'layout'으로."""


# ---------- 산술 (비공개 원본 credit_block과 같은 산식) ----------

_iso = ai._iso


def _r(v, nd=4):
    return None if v is None else round(v, nd) + 0.0


def _add_months(d, k):
    m = d.year * 12 + d.month - 1 + k
    return D(m // 12, m % 12 + 1, 1)


def _pct(vals, v):
    """v 이하인 비율(%) — fred_fetch.percentile과 같은 셈, 소수 한 자리."""
    return None if not vals or v is None else _r(sum(1 for x in vals if x <= v) / len(vals) * 100, 1)


def sloos(S, today):
    """(표시용 dict, 반올림 전 값) — 최신 조사(조사월 +SLOOS_LAG개월부터). 쓸 조사가 없으면 (None, None)."""
    s = [(d, v) for d, v in S.get("DRTSCILM") or () if _add_months(D(d.year, d.month, 1), SLOOS_LAG) <= today]
    if not s:
        return None, None
    d1, v1 = s[-1]
    age = (today - d1).days
    return {"value": _r(v1, 2), "survey": _iso(d1), "stale": age > SLOOS_STALE,
            "pct": _pct([v for d, v in s if d >= SINCE], v1)}, v1


def nfci(S, today):
    """(표시용 dict, 반올림 전 13주 변화, 반올림 전 수준). 13주 전 관측이 91일 전에서 NEAR_DAYS보다 멀면 13주 변화는 None.
    분위는 1990년 이후(13주 변화는 두 끝이 모두 1990년 이후 — 문턱과 같은 표본)."""
    s = [(d, v) for d, v in S.get("NFCICREDIT") or () if d <= today]
    if not s:
        return None, None, None
    d1, v1 = s[-1]
    target = d1 - datetime.timedelta(days=WEEKS13)
    old = ff.on_or_before(s, target)
    n13 = v1 - old[1] if old and (target - old[0]).days <= NEAR_DAYS else None
    h = [(d, v) for d, v in s if d >= SINCE]
    by = dict(h)
    hist = [v - by[d - datetime.timedelta(days=WEEKS13)] for d, v in h if d - datetime.timedelta(days=WEEKS13) in by]
    age = (today - d1).days
    return {"level": _r(v1), "n13": _r(n13), "asof": _iso(d1), "from": _iso(old[0]) if n13 is not None else None,
            "stale": age > NFCI_STALE, "pct_level": _pct([v for _, v in h], v1), "pct_n13": _pct(hist, n13),
            "n_hist": len(hist)}, n13, v1


def ge(x, th):
    return rr._cmp(x, ">=", th)


def rule_c(s_val, n13, nl):
    """규칙 C — (단계 | None, 가능한 최소, 최대). 입력이 None이면 그 계기를 모름(3값 논리)."""
    l2 = rr._and(ge(s_val, S2), rr._or(ge(n13, N2), ge(nl, NL2)))
    l1 = rr._or(ge(s_val, S1), ge(n13, N1))
    lo = 2 if l2 is True else (1 if l1 is True else 0)
    hi = 0 if l1 is False else (1 if l2 is False else 2)
    return (lo if lo == hi else None), lo, hi


def level_text(value, lo, hi):
    """'0/2' · '?/2 (1~2)'."""
    return f"{value}/2" if value is not None else f"?/2 ({lo}~{hi})"


def calc_stage(S, today):
    """규칙 C는 반올림 전 값으로 판정한다(비교 안에서만 소수 6자리 — rr._cmp). 표시용 반올림(SLOOS 2자리·NFCI 4자리)과 따로."""
    sl, s_raw = sloos(S, today)
    nf, n13_raw, nl_raw = nfci(S, today)
    if not sl or not nf:
        raise ItemError("format")
    s_val = None if sl["stale"] else s_raw
    n13 = None if nf["stale"] else n13_raw
    nl = None if nf["stale"] else nl_raw
    value, lo, hi = rule_c(s_val, n13, nl)
    return {"date": max(sl["survey"], nf["asof"]),
            "values": {"value": value, "lo": lo, "hi": hi,
                       "s": sl["value"], "s_survey": sl["survey"], "s_stale": sl["stale"], "s_pct": sl["pct"],
                       "n13": nf["n13"], "n_from": nf["from"], "nl": nf["level"], "n_asof": nf["asof"],
                       "n_stale": nf["stale"], "n_pct_level": nf["pct_level"], "n_pct_n13": nf["pct_n13"],
                       "n_hist": nf["n_hist"]}}


def invest_axis(S):
    """투자 축 — ICT 투자/GDP의 4분기 변화(정확히 1년 전 같은 분기) > 0 이면 확장, 아니면 소화. 1년 전 분기가 없으면 None."""
    tot = ai.quarterly_ratio(S["A679RC1Q027SBEA"], S["GDP"])
    if not tot:
        return None
    d1, v1 = tot[-1]
    y = ai._year_ago(tot)
    if y is None:
        return None
    ch = v1 - y
    return {"quarter": _iso(d1), "share": _r(v1), "ch4": _r(ch), "axis": "확장" if round(ch, 6) > 0 else "소화"}


def fund_axis(S):
    """조달 축 — Z.1 설비투자/내부자금(4분기 합) vs 1985년 이후 중앙값(ai_invest_fetch.calc_financing 그대로). 1990년 이후 분위도."""
    try:
        f = ai.calc_financing(S)
    except ai.ItemError:
        raise ItemError("format")
    v = f["values"]
    pts = [x for d, x in ai.quarterly_ratio(S["BOGZ1FA105050005Q"], S["BOGZ1FA106000135Q"], 4) if d >= SINCE]
    high = round(v["ratio"], 6) > round(v["median"], 6)
    return {"quarter": f["date"], "ratio": v["ratio"], "median": v["median"], "median_from": v["from"],
            "pct": _pct(pts, v["ratio"]), "high": high, "axis": "부채 조달" if high else "현금 조달"}


def calc_cell(S, today):
    inv = invest_axis(S)
    if inv is None:
        raise ItemError("format")
    fu = fund_axis(S)
    return {"date": max(inv["quarter"], fu["quarter"]),
            "values": {"quarter": inv["quarter"], "share": inv["share"], "ch4": inv["ch4"], "invest": inv["axis"],
                       "fq": fu["quarter"], "ratio": fu["ratio"], "median": fu["median"], "median_from": fu["median_from"],
                       "high": fu["high"], "fund": fu["axis"]}}


def calc_gap(S, today):
    fu = fund_axis(S)
    return {"date": fu["quarter"],
            "values": {"fq": fu["quarter"], "ratio": fu["ratio"], "median": fu["median"], "median_from": fu["median_from"],
                       "pct": fu["pct"], "high": fu["high"]}}


def drawdowns(series):
    """[(날짜, 12개월(DD_WINDOW 관측) 고점 대비 %)] — 창이 다 찬 날부터. 이 모듈 안에서만 쓴다(파일·문구에 싣지 않는다)."""
    out, q = [], deque()
    for i, (d, v) in enumerate(series):
        while q and series[q[-1]][1] <= v:
            q.pop()
        q.append(i)
        while q[0] <= i - DD_WINDOW:
            q.popleft()
        if i >= DD_WINDOW - 1 and series[q[0]][1]:
            out.append((d, (v / series[q[0]][1] - 1) * 100))
    return out


def first_entries(dd, x):
    """−x% 첫 진입(앞 DD_REST 관측에 −x% 이하가 없던 날) 가운데 최근 DD_REST 관측 안의 마지막 날짜 — 없으면 None."""
    hit = [round(v, 6) <= -x for _, v in dd]
    last, run = None, 0
    for i, h in enumerate(hit):
        if h and run >= DD_REST and i >= len(hit) - DD_REST:
            last = dd[i][0]
        run = 0 if h else run + 1
    return _iso(last) if last else None


def band(v):
    """낙폭(%) → 구간 코드. 경계값(정확히 −10%·−20%)은 아래 구간 — 첫 진입과 같은 비교(소수 6자리 반올림 뒤 이하)."""
    x = round(v, 6)
    return "over20" if x <= -20 else "10to20" if x <= -10 else "in10"


def dd_pct(v):
    """낙폭(%) → 정수 % — 소수 6자리 반올림 뒤 0.5는 0에서 먼 쪽으로(−12.5 → −13), −0은 0. 싣는 숫자는 이것 하나다
    (calc_drawdown은 소수 둘째 자리로 반올림한 낙폭을 넘긴다)."""
    x = round(v, 6)
    n = int(math.floor(abs(x) + 0.5))
    return -n if x < 0 and n else n


def calc_drawdown(S, today):
    """정수 낙폭 %는 소수 둘째 자리로 먼저 반올림한 값에서 — 비공개 원본(credit_block)이 그 자리로 저장하고(_r(dd, 2)) 줄에 쓰므로
    같은 날 두 쪽의 숫자가 갈리지 않게(−12.4996 → −12.50 → −13, −7.4983 → −7.50 → −8). 구간·첫 진입은 반올림 전 값으로."""
    vals, dates = {}, []
    for sid, pre in (("NASDAQ100", "ndx"), ("NASDAQNQINTEL", "ai")):
        dd = drawdowns(S[sid])
        if not dd:
            raise ItemError("format")                     # 252영업일이 다 차지 않음
        vals.update({f"{pre}_dd": max(-100, dd_pct(round(dd[-1][1], 2))), f"{pre}_band": band(dd[-1][1]),
                     f"{pre}_asof": _iso(dd[-1][0]),
                     f"{pre}_e10": first_entries(dd, 10), f"{pre}_e20": first_entries(dd, 20)})
        dates.append(_iso(dd[-1][0]))
    return {"date": max(dates), "values": vals}


# ---------- 신용 스트레스(공개 자료) — EBP · CMDI ----------

def _month(d):
    return D(d.year, d.month, 1)


def _num(v):
    """칸 → 유한한 수 또는 None(빈 칸·글·NaN). 참/거짓은 수가 아니다."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        x = float(v)
    else:
        t = str(v).strip()
        if not re.fullmatch(r"[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?", t):
            return None
        x = float(t)
    return x if math.isfinite(x) else None


def _text_date(t):
    """'YYYY-MM-DD'(뒤에 시각이 붙어도) · 'M/D/YYYY' · 'YYYY-MM' → 날짜 또는 None."""
    t = str(t).strip()
    try:
        m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T]\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?", t)
        if m:
            return D(int(m[1]), int(m[2]), int(m[3]))
        m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", t)
        if m:
            return D(int(m[3]), int(m[1]), int(m[2]))
        m = re.fullmatch(r"(\d{4})-(\d{1,2})", t)
        if m:
            return D(int(m[1]), int(m[2]), 1)
    except ValueError:
        return None
    return None


def _sorted_unique(pairs):
    """[(날짜, 값)] → 날짜 차례, 같은 날짜는 뒤의 것."""
    return sorted(dict(pairs).items())


def parse_ebp(blob):
    """연준 이사회 ebp_csv.csv(바이트) → {"ebp": [(달 첫날, pp)], "gz": [...]}. 머리글은 대소문자·앞뒤 공백을 가리지 않고,
    날짜는 'YYYY-MM-DD'·'M/D/YYYY'·'YYYY-MM'(달 첫날로), 빈 칸·수가 아닌 칸은 건너뛴다. 침체 확률 열(est_prob)은 읽지 않는다.
    줄 끝은 LF·CRLF·CR 어느 것이든. date·ebp 열이 없거나 쓸 행이 없거나 단위가 퍼센트포인트로 보이지 않거나, CSV로 읽히지
    않으면(닫히지 않은 따옴표·칸 상한(csv.field_size_limit)을 넘는 칸 같은 깨진 파일) LayoutError."""
    text = blob.decode("utf-8-sig", "replace") if isinstance(blob, bytes) else str(blob).lstrip("\ufeff")
    try:
        rows = list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error:
        raise LayoutError("csv")
    head = None
    for i, row in enumerate(rows[:20]):
        names = [c.strip().lstrip("\ufeff").lower() for c in row]
        if "date" in names and "ebp" in names:
            head = i, names
            break
    if head is None:
        raise LayoutError("no header")
    i, names = head
    ci, ce = names.index("date"), names.index("ebp")
    cg = names.index("gz_spread") if "gz_spread" in names else None
    ebp, gz = [], []
    for row in rows[i + 1:]:
        d = _text_date(row[ci]) if ci < len(row) else None
        if d is None:
            continue
        d = _month(d)
        e = _num(row[ce]) if ce < len(row) else None
        if e is not None:
            ebp.append((d, e))
        g = _num(row[cg]) if cg is not None and cg < len(row) else None
        if g is not None:
            gz.append((d, g))
    ebp, gz = _sorted_unique(ebp), _sorted_unique(gz)
    if not ebp:
        raise LayoutError("no rows")
    if max(abs(v) for _, v in ebp) > EBP_MAX_PP or (gz and max(abs(v) for _, v in gz) > GZ_MAX_PP):
        raise LayoutError("unit")
    return {"ebp": ebp, "gz": gz}


def calc_ebp(S, today):
    """마지막 달 EBP(bp)·같은 파일 전 표본 분위·정확히 3개월 전 달 대비 변화(bp)·같은 달 GZ 스프레드(bp)."""
    e = S[EBP].get("ebp") or []
    if not e:
        raise ItemError("format")
    d1, v1 = e[-1]
    back = dict(e).get(_add_months(d1, -EBP_BACK))
    gz = dict(S[EBP].get("gz") or ()).get(d1)
    return {"date": _iso(d1),
            "values": {"ebp": _r(v1 * 100, 1), "month": _iso(d1), "since": _iso(e[0][0]),
                       "pct": _pct([v for _, v in e], v1),
                       "ch3": None if back is None else _r((v1 - back) * 100, 1),
                       "gz": None if gz is None else _r(gz * 100, 1)}}


def _local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


_DECL = re.compile(rb"<!(?!--|\[CDATA\[)")


def _xml(z, name):
    """통합 문서 안 XML 하나 — 크기 상한, DTD·엔티티 선언이 든 것은 읽지 않는다(엔티티 부풀리기 막기)."""
    try:
        info = z.getinfo(name)
    except KeyError:
        raise LayoutError("missing part")
    if info.file_size > XLSX_MAX_MEMBER:
        raise LayoutError("too large")
    try:
        with z.open(info) as f:
            data = f.read(XLSX_MAX_MEMBER + 1)
    except (zipfile.BadZipFile, zlib.error, NotImplementedError, RuntimeError, ValueError, EOFError, OSError):
        raise LayoutError("zip")                       # 깨진 압축·CRC·지원하지 않는 방식·암호 — 수신이 아니라 꼴 문제
    if len(data) > XLSX_MAX_MEMBER or data[:2] in (b"\xff\xfe", b"\xfe\xff") or _DECL.search(data):
        raise LayoutError("xml")
    try:
        return ET.fromstring(data)
    except ET.ParseError:
        raise LayoutError("xml")


def _rich(node):
    """<si>·<is> 안의 글 — <t>와 <r><t>를 잇고 발음 표기(<rPh>)는 뺀다."""
    out = []
    for ch in node if node is not None else ():
        n = _local(ch.tag)
        if n == "t":
            out.append(ch.text or "")
        elif n == "r":
            out.extend(t.text or "" for t in ch if _local(t.tag) == "t")
    return "".join(out)


def _col(ref):
    m = re.match(r"([A-Za-z]{1,3})", ref or "")
    if not m:
        return None
    n = 0
    for ch in m.group(1).upper():
        n = n * 26 + ord(ch) - 64
    return n - 1


def _sheet_rows(z, path, shared):
    """시트 → [{열 번호: 값}] (행 차례). 값은 글(공유·인라인·수식 글) 또는 수."""
    rows = []
    for row in _xml(z, path).iter():
        if _local(row.tag) != "row":
            continue
        cells, nxt = {}, 0
        for c in row:
            if _local(c.tag) != "c":
                continue
            j = _col(c.get("r"))
            j = nxt if j is None else j
            nxt = j + 1
            t = c.get("t", "n")
            v = next((x.text for x in c if _local(x.tag) == "v"), None)
            if t == "s":
                k = (v or "").strip()
                val = shared[int(k)] if re.fullmatch(r"[0-9]{1,9}", k) and int(k) < len(shared) else None
            elif t == "inlineStr":
                val = _rich(next((x for x in c if _local(x.tag) == "is"), None))
            elif t in ("str", "d"):
                val = v
            elif t == "n":
                val = _num(v)
            else:                                   # 참/거짓(b)·오류(e)
                val = None
            if val is not None and val != "":
                cells[j] = val
        rows.append(cells)
    return rows


def _norm(t):
    return re.sub(r"[\s_\-/]+", " ", str(t)).strip().lower()


def cmdi_key(header):
    """CMDI 머리글 → 'market'·'ig'·'hy' 또는 None(모르는 열 — 버린다). 머리글이 CMDI_WORDS 낱말로만 이루어졌을 때만."""
    if not isinstance(header, str):
        return None
    words = _norm(header).split()
    if not words or not set(words) <= CMDI_WORDS:
        return None
    w = set(words)
    ig = bool(w & {"ig", "investment"}) or {"high", "grade"} <= w
    hy = "hy" in w or {"high", "yield"} <= w or "speculative" in w
    if ig and hy:
        return None
    if ig:
        return "ig"
    if hy:
        return "hy"
    if "high" in w:                                # 'high'만 있고 grade·yield가 없으면 모른다
        return None
    return "market" if "market" in w else None


def _xl_date(v):
    """eow_friday 칸 → 날짜. 수는 엑셀 일련번호(1899-12-30 기준 — 소수 부분(시각)은 버린다, 1 이상 2958466(10000-01-01)
    미만만 — 밖이면 None), 글은 _text_date의 꼴."""
    if isinstance(v, float):
        return D(1899, 12, 30) + datetime.timedelta(days=int(v)) if 1 <= v < 2958466 else None
    return _text_date(v) if isinstance(v, str) else None


def _safe(t, n=40):
    """로그에 찍는 바깥 글 — 제어·서식 문자를 지우고 공백을 하나로, 길이 상한."""
    t = "".join(ch if ch.isprintable() else " " for ch in str(t))
    t = re.sub(r"\s+", " ", t).strip()
    return t[:n] + ("…" if len(t) > n else "")


def _header_row(rows):
    for i, cells in enumerate(rows[:50]):
        if any(isinstance(v, str) and _norm(v) == "eow friday" for v in cells.values()):
            return i
    return None


def parse_cmdi(blob, log=None):
    """뉴욕 연은 Market CMDI.xlsx(바이트) → {"market": [(금요일, 값)], "ig": [...], "hy": [...]} (있는 열만).
    시트는 이름이 'Index Data' 꼴(index·data)인 것부터 통합 문서 차례로, eow_friday 머리글 줄에 시장 전체 열이 있는 첫 시트
    (eow_friday만 적힌 설명 시트는 건너뛴다). log가 있으면
    시트 이름과 머리글 칸(글만 — 값은 찍지 않는다)을 넘긴다. 시장 전체 열이 없거나 0~1 밖의 값이 섞이면 LayoutError
    (투자등급·하이일드 열이 0~1 밖이면 그 열만 버린다)."""
    say = log or (lambda t: None)
    try:
        z = zipfile.ZipFile(io.BytesIO(blob))
    except (zipfile.BadZipFile, ValueError, TypeError):
        raise LayoutError("zip")
    with z:
        names = set(z.namelist())
        shared = [_rich(si) for si in _xml(z, "xl/sharedStrings.xml") if _local(si.tag) == "si"] \
            if "xl/sharedStrings.xml" in names else []
        target = {r.get("Id"): r.get("Target") or "" for r in _xml(z, "xl/_rels/workbook.xml.rels")
                  if _local(r.tag) == "Relationship"}
        sheets = []
        for el in _xml(z, "xl/workbook.xml").iter():
            if _local(el.tag) != "sheet":
                continue
            rid = next((v for k, v in el.attrib.items() if k.endswith("}id")), None)
            t = target.get(rid)
            if t:
                path = t.lstrip("/") if t.startswith("/") else posixpath.normpath(posixpath.join("xl", t))
                sheets.append((el.get("name") or "", path))
        say("CMDI 시트: " + (" | ".join(_safe(n) for n, _ in sheets[:20]) or "없음"))
        liked = [x for x in sheets if {"index", "data"} <= set(_norm(x[0]).split())]
        found = first = None
        for name, path in liked + [x for x in sheets if x not in liked]:
            if path not in names:
                continue
            rows = _sheet_rows(z, path, shared)
            h = _header_row(rows)
            if h is None:
                continue
            first = first or (name, rows, h)
            if any(cmdi_key(v) == "market" for v in rows[h].values()):   # 설명 시트(eow_friday를 낱말로 적은 것)는 넘긴다
                found = name, rows, h
                break
        if found is None and first is None:
            say("CMDI 머리글(eow_friday) 없음")
            raise LayoutError("no header")
    name, rows, h = found or first                  # 시장 전체 열이 있는 시트가 없으면 첫 후보의 머리글을 찍고 아래에서 실패
    head = rows[h]
    say(f"CMDI 머리글({_safe(name)}): " + " | ".join(_safe(head[j]) if isinstance(head[j], str) else "#"
                                               for j in sorted(head)[:30]))
    dcol = next(j for j, v in head.items() if isinstance(v, str) and _norm(v) == "eow friday")
    cols = {}
    for j in sorted(head):
        k = cmdi_key(head[j]) if j != dcol else None
        if k and k not in cols.values():
            cols[j] = k
    out = {k: [] for k in cols.values()}
    for cells in rows[h + 1:]:
        d = _xl_date(cells.get(dcol))
        if d is None:
            continue
        for j, k in cols.items():
            v = _num(cells.get(j))
            if v is not None:
                out[k].append((d, v))
    out = {k: _sorted_unique(s) for k, s in out.items() if s}
    for k in list(out):
        if any(not 0 <= round(v, 6) <= 1 for _, v in out[k]):
            if k == "market":
                raise LayoutError("range")
            del out[k]
    if "market" not in out:
        raise LayoutError("no market column")
    return out


def calc_cmdi(S, today):
    """열마다 마지막 주 값·날짜·자기 전 표본 분위·정확히 28일 전 관측 대비 4주 변화. 칸의 날짜는 시장 전체의 날짜."""
    cols = S[CMDI]
    if not cols.get("market"):
        raise ItemError("format")
    vals = {}
    for k in CMDI_KEYS:
        s = cols.get(k) or []
        if not s:
            vals.update({k: None, f"{k}_date": None, f"{k}_since": None, f"{k}_pct": None, f"{k}_ch4": None})
            continue
        d1, v1 = s[-1]
        back = dict(s).get(d1 - datetime.timedelta(days=CMDI_BACK))
        vals.update({k: _r(v1), f"{k}_date": _iso(d1), f"{k}_since": _iso(s[0][0]), f"{k}_pct": _pct([v for _, v in s], v1),
                     f"{k}_ch4": None if back is None else _r(v1 - back)})
    return {"date": vals["market_date"], "values": vals}


# ---------- 칸 정의 (차례 = 화면 차례, sec는 sec.json에서) ----------
# values: 이름 → 꼴 — 직전 파일 검사에도 쓴다. ends: 칸의 date와 함께 하나라도 직전보다 이르면 받지 않는다.
# 재배포 제한 칸(drawdown)의 값은 지수마다 정수 낙폭 %(꼴 'dd' — −100~0의 정수) 하나와 구간 코드·날짜뿐이다 — 다른 숫자 꼴이
# 없어 직전 파일에 다른 숫자가 섞여 있으면 싣지 않는다.

_CMDI_VALUES = {}
for _k in CMDI_KEYS:
    _opt = "" if _k == "market" else "?"
    _CMDI_VALUES.update({_k: "unit" + _opt, f"{_k}_date": "day" + _opt, f"{_k}_since": "day" + _opt,
                         f"{_k}_pct": "num?", f"{_k}_ch4": "num?"})

ITEMS = [
    {"key": "stage", "title": "신용 긴축 단계 (규칙 C)", "series": ["DRTSCILM", "NFCICREDIT"], "calc": calc_stage,
     "values": {"value": "stage?", "lo": "stage", "hi": "stage", "s": "num", "s_survey": "day", "s_stale": "bool",
                "s_pct": "num?", "n13": "num?", "n_from": "day?", "nl": "num", "n_asof": "day", "n_stale": "bool",
                "n_pct_level": "num?", "n_pct_n13": "num?", "n_hist": "int"}, "ends": ["s_survey", "n_asof"]},
    {"key": "ebp", "title": "초과 채권 프리미엄 (연준 이사회 EBP, 월간)", "series": [EBP], "calc": calc_ebp,
     "values": {"ebp": "num", "month": "day", "since": "day", "pct": "num?", "ch3": "num?", "gz": "num?"},
     "ends": ["month"]},
    {"key": "cmdi", "title": "회사채 시장 스트레스 지수 (뉴욕 연은 CMDI, 주간)", "series": [CMDI], "calc": calc_cmdi,
     "values": _CMDI_VALUES, "ends": ["market_date"]},
    {"key": "cell", "title": "AI 투자 칸 — 투자 축 × 조달 축 (서술 꼬리표)",
     "series": ["A679RC1Q027SBEA", "GDP", "BOGZ1FA105050005Q", "BOGZ1FA106000135Q"], "calc": calc_cell,
     "values": {"quarter": "day", "share": "num", "ch4": "num", "invest": "invest", "fq": "day", "ratio": "num",
                "median": "num", "median_from": "day", "high": "bool", "fund": "fund"}, "ends": ["quarter", "fq"]},
    {"key": "gap", "title": "자금 부족 조건", "series": ["BOGZ1FA105050005Q", "BOGZ1FA106000135Q"], "calc": calc_gap,
     "values": {"fq": "day", "ratio": "num", "median": "num", "median_from": "day", "pct": "num?", "high": "bool"}},
    {"key": "drawdown", "title": "주가 낙폭 — 나스닥100 · AI 지수", "series": ["NASDAQ100", "NASDAQNQINTEL"],
     "calc": calc_drawdown,
     "values": {"ndx_dd": "dd", "ndx_band": "band", "ndx_asof": "day", "ndx_e10": "day?", "ndx_e20": "day?",
                "ai_dd": "dd", "ai_band": "band", "ai_asof": "day", "ai_e10": "day?", "ai_e20": "day?"},
     "ends": ["ndx_asof", "ai_asof"]},
]
STRESS = ("ebp", "cmdi")                      # 신용 스트레스(공개 자료) 묶음 — 화면이 한 무리로 그린다
BY_KEY = {it["key"]: it for it in ITEMS}
ORDER = [it["key"] for it in ITEMS] + ["sec"]


# ---------- 문구 ----------

def _q(day):
    d = D.fromisoformat(day)
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def _s(v, nd=3):
    if v is None:
        return "—"
    s = f"{v:+.{nd}f}"
    return f"{0:.{nd}f}" if float(s) == 0 else s


def _p(v):
    return "p—" if v is None else f"p{v:.0f}"


def texts(key, v, date):
    """칸 → (숫자 줄, 덧붙이는 줄 목록). 정해 둔 문구에 숫자만 넣는다."""
    if key == "stage":
        sl = f"SLOOS 대·중견 C&I 순긴축 {v['s']:.1f}% ({v['s_survey'][:7]} 조사, 1990~ {_p(v['s_pct'])})"
        if v["s_stale"]:
            sl += f" 묵음: 조사월부터 {SLOOS_STALE}일 넘음 — 모름으로"
        n13 = f"13주 {_s(v['n13'])} ({_p(v['n_pct_n13'])})" if v["n13"] is not None else "13주 변화 계산 불가"
        nf = f"NFCI 신용 {n13} · 수준 {_s(v['nl'])} ({_p(v['n_pct_level'])}, {v['n_asof']} 기준)"
        if v["n_stale"]:
            nf += f" 묵음: 마지막 관측이 {NFCI_STALE}일 넘음 — 모름으로"
        easing = v["s"] < 0
        return (f"긴축 {level_text(v['value'], v['lo'], v['hi'])} — {sl} · {nf}",
                ["SLOOS는 분기 조사(1·4·7·10월, 다음 달 발표)라 조사월 다음 달부터 쓴다. NFCI 신용은 시카고 연은이 매주 전 "
                 "표본으로 다시 추정하는 지수라 과거 값·분위가 조금씩 움직인다(현재 개정치, 실시간 아님). 분위(p)는 1990년 "
                 "이후 자기 시계열에서 값 이하의 비율이고, 단계는 반올림 전 값으로 정한다.",
                 HYPO + (EASING if easing else ""), PATH_NOTE])
    if key == "cell":
        fp = (f"설비투자/내부자금 {v['ratio']:.1f}% ({_q(v['fq'])}) {'>' if v['high'] else '≤'} "
              f"{v['median_from'][:4]}~ 중앙값 {v['median']:.1f}%")
        return (f"{v['invest']} × {v['fund']} — 정보처리 투자/GDP {v['share']:.2f}% ({_q(v['quarter'])}, 4분기 "
                f"{_s(v['ch4'], 2)}%p) · {fp}",
                ["투자 축: 정보처리 장비·소프트웨어 투자 / 명목 GDP의 4분기 변화(정확히 1년 전 같은 분기 대비)가 0보다 크면 "
                 "'확장', 아니면 '소화'. 조달 축: 비금융기업 설비투자 / 내부자금(4분기 합, 연준 Z.1)이 1985년 이후 중앙값보다 "
                 "높으면 '부채 조달', 아니면 '현금 조달'.",
                 "금리 방향이 없는 서술 꼬리표다 — 운영자가 2026-10-29에 잰 바로는 투자 축의 어느 칸도 금리와 유의하게 "
                 "이어지지 않았다."])
    if key == "gap":
        rank = ("1990~ 분위 —" if v["pct"] is None else f"1990~ 하위 {v['pct']:.0f}%" if v["pct"] < 50
                else f"1990~ 상위 {100 - v['pct']:.0f}%")
        return (f"주가 조정 뒤 단기 금리 경로의 조건(설비투자/내부자금 > {v['median_from'][:4]}~ 중앙값 {v['median']:.1f}%): "
                f"지금 {v['ratio']:.1f}% ({_q(v['fq'])}), {rank} — {'해당' if v['high'] else '해당 없음'}",
                ["운영자 측정(2026-10-29): 나스닥100이 고점 대비 −10%에 처음 들어선 뒤(17건) 3개월 동안 NFCI 신용 +0.07 · "
                 "SLOOS +7.8%p였고 2년 금리는 −2bp(t −0.1)로 움직임이 없었다. 설비투자/내부자금이 중앙값보다 높던 시기에만 "
                 "낙폭 10%p당 정책금리 3개월 −16bp가 보였다(사례 대부분 1990년대·2007년, 얇다). 예측이 아니다."])
    if key == "ebp":
        line = f"EBP {_s(v['ebp'], 0)}bp ({v['month'][:7]}, {v['since'][:4]}~ {_p(v['pct'])})"
        if v["ch3"] is not None:
            line += f" · 3개월 {_s(v['ch3'], 0)}bp"
        if v["gz"] is not None:
            line += f" · GZ 스프레드 {v['gz']:.0f}bp"
        return (line,
                ["EBP는 회사채 스프레드(GZ 스프레드)에서 발행 기업의 부도 위험으로 설명되는 몫을 뺀 나머지다. 연준 이사회가 "
                 "매달 전 표본으로 다시 추정해 과거 값·분위도 조금씩 움직인다. 분위(p)는 같은 파일 전 표본에서 값 이하의 "
                 f"비율, 3개월 변화는 정확히 {EBP_BACK}개월 전 달과 견준다."])
    if key == "cmdi":
        parts = []
        for k in CMDI_KEYS:
            if v[k] is None:
                continue
            bits = [] if v[f"{k}_date"] == date else [f"{v[f'{k}_date']} 기준"]
            bits.append(f"{v[f'{k}_since'][:4]}~ {_p(v[f'{k}_pct'])}")
            if v[f"{k}_ch4"] is not None:
                bits.append(f"4주 {_s(v[f'{k}_ch4'], 2)}")
            parts.append(f"{CMDI_LABEL[k]} {v[k]:.2f} ({', '.join(bits)})")
        return (" · ".join(parts),
                ["CMDI는 회사채 발행·유통 시장의 가격·거래 지표를 묶은 0~1 지수로, 1에 가까울수록 시장 기능이 빠듯한 쪽이다. "
                 f"분위(p)는 그 열의 전 표본에서 값 이하의 비율, 4주 변화는 정확히 {CMDI_BACK}일 전 관측과 견주고 그 관측이 "
                 "없으면 적지 않는다.",
                 "뉴욕 연은은 매달 마지막 수요일쯤 한 번 갱신하므로 마지막 값이 5주가량 지난 것일 수 있다. 날짜는 그 주 "
                 "금요일이다."])
    if key == "drawdown":
        parts, ent = [], []
        for pre, name in (("ndx", WARN["NASDAQ100"]), ("ai", WARN["NASDAQNQINTEL"])):
            asof = "" if v[f"{pre}_asof"] == date else f", {v[f'{pre}_asof']} 기준"
            parts.append(f"{name} 고점 대비 {_dd(v[f'{pre}_dd'])} ({BAND_NAME[v[f'{pre}_band']]}{asof})")
            for x in DD_LEVELS:
                if v[f"{pre}_e{x}"]:
                    ent.append(f"{name} −{x}% {v[f'{pre}_e{x}']}")
        return (f"{date} 기준 " + " · ".join(parts) + " · 최근 6개월 첫 진입: " + (", ".join(ent) if ent else "없음"),
                [f"252영업일(약 12개월) 고점 대비 지금 낙폭을 정수 %로 싣는다(소수 둘째 자리로 반올림한 값에서 0.5는 0에서 먼 쪽으로). 구간은 반올림 전 "
                 f"값으로 정하고, 경계값(정확히 −10%·−20%)은 아래 구간으로 센다. 첫 진입은 앞 {DD_REST}영업일 동안 그 낙폭"
                 f"(−10%·−20% 이하)이 없다가 처음 들어선 날이고, 최근 {DD_REST}영업일 안의 마지막 것을 적는다.",
                 "단계를 바꾸지 않는 참고다. 지수 값·12개월 고점·수익률·낙폭 시계열은 재배포 제한 자료라 싣지 않는다."])
    raise KeyError(key)


def _dd(n):
    """정수 낙폭 % → '−14%' · '0%'."""
    return "0%" if n == 0 else f"−{abs(n)}%"


def citation(sid, retrieved):
    d = D.fromisoformat(retrieved)
    when = f"{ai._MONTHS[d.month - 1]} {d.day}, {d.year}"
    if sid in EXT:
        return f"{EXT[sid]['title']}, retrieved from {EXT[sid]['url']}, {when}."
    src, title = SOURCES[sid]
    return (f"{src}, {title} [{sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; "
            f"{rp.FRED_URL.format(sid)}, {when}.")


def sources_of(spec, retrieved=None):
    out = []
    for sid in spec["series"]:
        if sid in EXT:
            s = {"series": sid, "name": EXT[sid]["name"], "url": EXT[sid]["url"], "licence": EXT[sid]["licence"],
                 "restricted": False}
        else:
            s = {"series": sid, "name": SOURCES[sid][0], "url": rp.FRED_URL.format(sid), "licence": LICENCE[sid],
                 "restricted": sid in RESTRICTED}
            if sid in COPYRIGHT:
                s["copyright"] = COPYRIGHT[sid]
        if retrieved:
            s["citation"] = citation(sid, retrieved)
        out.append(s)
    return out


def notices(spec, retrieved=None):
    """칸의 고지 — 정해 둔 글뿐. CMDI의 뉴욕 연은 기본 출처 표시는 처음 받은 해(retrieved)로."""
    if spec["series"] == [EBP]:
        return [EBP_NOTICE, EBP_CITE, EBP_SOURCE, EBP_PD]
    if spec["series"] == [CMDI]:
        year = (retrieved or "")[:4] if ai._is_day(retrieved) else None
        return [CMDI_DERIVED, CMDI_DERIVED_EN] + ([rp.nyfed_attribution(year)] if year else []) + \
            [rp.NOT_AFFILIATED, CMDI_CITE]
    if any(s in RESTRICTED for s in spec["series"]):
        return [RESTRICTED_NOTICE, COPYRIGHT_NOTICE]
    out = [COMPUTED_NOTICE]
    if any(LICENCE[s] == "citation-required" for s in spec["series"]):
        out.append(CITATION_NOTICE)
    return out


def present(key, core, retrieved):
    spec = BY_KEY[key]
    line, extra = texts(key, core["values"], core["date"])
    return {"key": key, "name": spec["title"], "date": core["date"], "values": core["values"], "retrieved": retrieved,
            "line": line, "extra": extra, "notices": notices(spec, retrieved), "sources": sources_of(spec, retrieved)}


# ---------- 직전 파일 ----------

_KIND = dict(ai._KIND, bool=lambda v: isinstance(v, bool), stage=lambda v: type(v) is int and v in (0, 1, 2),
             invest=lambda v: v in ("확장", "소화"), fund=lambda v: v in ("부채 조달", "현금 조달"),
             band=lambda v: v in BAND_NAME, dd=lambda v: type(v) is int and -100 <= v <= 0,
             unit=lambda v: ai._is_num(v) and 0 <= v <= 1)
_KIND["stage?"] = lambda v: v is None or _KIND["stage"](v)
_KIND["unit?"] = lambda v: v is None or _KIND["unit"](v)


def _consistent(key, v):
    """값끼리 어긋나지 않는지 — 단계·범위, 축 이름과 그 근거."""
    if key == "stage":
        return v["lo"] <= v["hi"] and (v["value"] is None) == (v["lo"] != v["hi"]) and \
            (v["value"] is None or v["value"] == v["lo"])
    if key == "cell":
        return (v["fund"] == "부채 조달") == v["high"] and (v["ch4"] >= 0 if v["invest"] == "확장" else v["ch4"] <= 0)
    if key == "drawdown":                         # 정수 낙폭 %가 구간과 맞는지(반올림이라 경계는 양쪽)
        return all(BAND_RANGE[v[f"{p}_band"]][0] <= v[f"{p}_dd"] <= BAND_RANGE[v[f"{p}_band"]][1] for p in ("ndx", "ai"))
    if key == "cmdi":                             # 투자등급·하이일드는 값이 있으면 날짜도, 없으면 모두 없음
        return all((v[k] is None) == (v[f"{k}_date"] is None) == (v[f"{k}_since"] is None) and
                   (v[k] is not None or (v[f"{k}_pct"] is None and v[f"{k}_ch4"] is None)) for k in CMDI_KEYS)
    return True


def core_of(item, key):
    """직전 파일의 칸 → (core, 받은 날) 또는 None(없거나 꼴이 어긋남)."""
    spec = BY_KEY[key]
    try:
        vals = item["values"]
        ok = (ai._is_day(item["date"]) and ai._is_day(item["retrieved"]) and isinstance(vals, dict)
              and set(vals) == set(spec["values"]) and all(_KIND[t](vals[k]) for k, t in spec["values"].items())
              and _consistent(key, vals))
        if ok:
            texts(key, vals, item["date"])
    except (KeyError, TypeError, IndexError, AttributeError, ValueError):
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
    return {k: v for k, v in js["items"].items() if k in ORDER and isinstance(v, dict)}


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


# ---------- 기업별 조달 (sec.json) ----------

def read_sec(out):
    """<out>/sec.json의 funding 칸 → dict 또는 None(없거나 깨짐)."""
    return sf.previous(out)


def sec_item(it, prev, today):
    """sec.json의 칸을 검사해 다시 만든다(문구는 sec_fetch가 숫자로 만든다 — 파일의 글을 그대로 옮기지 않는다).
    sec.json이 없거나 깨졌으면 이 파일의 직전 sec 칸을 받지 못함으로(직전도 없으면 사유만)."""
    if isinstance(it, dict):
        old = sf.core_of(it)
        err = it.get("error")
        since = it.get("failed_since") if ai._is_day(it.get("failed_since")) else None
        if old and it.get("ok") is True:
            return {"ok": True, "stale": False, "error": None, "failed_since": None, **sf.present(*old, key="sec")}
        if old and it.get("stale") is True and err in sf.REASONS.values():
            return {"ok": False, "stale": True, "error": err, "failed_since": since or today.isoformat(),
                    **sf.present(*old, key="sec")}
        if not old and it.get("ok") is False and err in sf.REASONS.values():
            return {"ok": False, "stale": False, "error": err, "failed_since": since or today.isoformat(), "key": "sec",
                    "name": sf.TITLE, "sources": sf.sources_of()}
    since = prev.get("failed_since") if prev and ai._is_day(prev.get("failed_since")) else today.isoformat()
    old = sf.core_of(prev) if prev else None
    if old:
        return {"ok": False, "stale": True, "error": REASONS["sec_file"], "failed_since": since,
                **sf.present(*old, key="sec")}
    return {"ok": False, "stale": False, "error": REASONS["sec_file"], "failed_since": since, "key": "sec",
            "name": sf.TITLE, "sources": sf.sources_of()}


def build(results, prev, now, sec=None):
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
    items["sec"] = sec_item(sec, prev.get("sec"), today)
    return {"schema": SCHEMA, "generated_at": now.isoformat(timespec="seconds"), "notice": NOTICE,
            "definition": STAGE_DEF, "order": ORDER, "items": items}


# ---------- 수신 ----------

def fetch_bytes(url, host, deadline, clock=time.monotonic, opener=None):
    """FRED 밖 파일 한 건(연준 이사회·뉴욕 연은) — 이 프로젝트를 밝히는 User-Agent(UA, 이메일 없음)를 단다. 남은 시간을
    타임아웃으로 주고 읽는 동안에도 마감을 본다. 다른 호스트·http로 넘겨지면 받지 않는다, MAX_BYTES 상한."""
    left = deadline - clock()
    if left <= 1:
        raise TimeoutError("budget")
    if urllib.parse.urlsplit(url)[:2] != ("https", host):
        raise ValueError("host")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    chunks, size = [], 0
    with (opener or urllib.request.urlopen)(req, timeout=min(REQ_TIMEOUT, left)) as r:
        final = urllib.parse.urlsplit(r.geturl())
        if (final.scheme, final.netloc) != ("https", host):
            raise ValueError("redirect")
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
    return b"".join(chunks)


def _say(text):
    print(f"[credit_fetch] {text}", flush=True)


def _parse_ext(sid, blob):
    return parse_ebp(blob) if sid == EBP else parse_cmdi(blob, log=_say)


def _write_bytes(path, blob):
    tmp = path + ".tmp"
    try:
        with open(tmp, "wb") as f:
            f.write(blob)
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def load_ext(sid, cache_dir, offline, deadline, clock=time.monotonic, opener=None):
    """(읽은 자료, 'net'|'cache'). 온라인이면 받아서(읽히면 캐시에 쓴다 — 캐시로 대신하지 않는다), --offline이면 캐시만.
    꼴을 알아보지 못하면 LayoutError."""
    path = os.path.join(cache_dir, EXT[sid]["cache"])
    if offline:
        with open(path, "rb") as f:
            return _parse_ext(sid, f.read()), "cache"
    blob = fetch_bytes(EXT[sid]["url"], EXT[sid]["host"], deadline, clock, opener)
    parsed = _parse_ext(sid, blob)
    try:
        os.makedirs(cache_dir, exist_ok=True)
        _write_bytes(path, blob)
    except OSError:
        pass                                    # 캐시는 덤이다
    return parsed, "net"


def load_all(work, offline=False, fred_load=None, clock=time.monotonic, budget=BUDGET, opener=None):
    """{ID: 자료}와 {ID: 실패 코드}. 요청마다 min(REQ_TIMEOUT, 남은 예산). 온라인에서 캐시로 대신한 것은 실패('cache').
    FRED 밖(EBP·CMDI)은 opener로 받는다(fred_load는 FRED만 — 테스트)."""
    cache = os.path.join(work, CACHE)
    data, errors = {}, {}
    deadline = clock() + budget
    for sid in FETCH:
        left = deadline - clock()
        if not offline and left <= 1:
            errors[sid] = "fetch"
            continue
        one = min(deadline, clock() + REQ_TIMEOUT)          # 이 요청의 마감
        try:
            if sid in EXT:
                series, src = load_ext(sid, cache, offline, one, clock, opener)
            elif fred_load:
                series, src = fred_load(sid, cache, offline=offline, timeout=min(REQ_TIMEOUT, max(1.0, left)))
            else:
                series, src = ai.load_series(sid, cache, offline, one, clock, opener)
        except LayoutError:
            errors[sid] = "layout"
            continue
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


def _upto(s, today):
    if isinstance(s, dict):
        return {k: [(d, v) for d, v in x if d <= today] for k, x in s.items()}
    return [(d, v) for d, v in s if d <= today]


def compute(data, errors, today):
    S = {sid: _upto(s, today) for sid, s in data.items()}
    out = {}
    for spec in ITEMS:
        miss = [sid for sid in spec["series"] if not S.get(sid)]
        if miss:
            out[spec["key"]] = ItemError(errors.get(miss[0], "format"))
            continue
        try:
            out[spec["key"]] = spec["calc"](S, today)
        except ItemError as e:
            out[spec["key"]] = e
        except Exception as e:                  # 계산 쪽 뜻밖의 오류도 그 칸만 실패로(예외 이름만)
            print(f"[credit_fetch] {spec['key']} 계산 오류: {type(e).__name__}", file=sys.stderr)
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
    ap = argparse.ArgumentParser(description="FRED 공개 통계·연준 이사회 EBP·뉴욕 연은 CMDI·sec.json → 신용 긴축 참고 자료"
                                             "(<out>/credit.json)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/) — sec.json도 여기서 읽는다")
    ap.add_argument("--work", default=DEFAULT_WORK, help="작업 폴더 — 원문 캐시는 <work>/credit/ (기본: 저장소의 .work/)")
    ap.add_argument("--offline", action="store_true", help="요청하지 않고 캐시만 읽는다(로컬 확인용)")
    a = ap.parse_args(argv)
    out, work = os.path.abspath(a.out), os.path.abspath(a.work)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    data, errors = load_all(work, a.offline, fred_load, clock, opener=opener)
    data = build(compute(data, errors, now.date()), previous(out), now, read_sec(out))
    for key in ORDER:                           # Actions 로그 — 날짜와 정해 둔 사유만(값은 찍지 않는다)
        it = data["items"][key]
        if it["ok"]:
            print(f"[credit_fetch] {key} {it['date']} 기준")
        else:
            kept = f" — 직전 값({it['date']} 기준) 유지" if it["stale"] else ""
            ai.annotate(f"신용 긴축 참고 {key} 받지 못함: {it['error']}{kept}")
    try:
        if differs(out, data):
            write(out, data)
    except OSError as e:
        print(f"[credit_fetch] {FILE}를 쓰지 못함: {type(e).__name__}", file=sys.stderr)
        return 1
    return 0 if any(data["items"][k]["ok"] for k in BY_KEY) else 1


if __name__ == "__main__":
    sys.exit(main())
