#!/usr/bin/env python3
"""참고 자료 — 달러 · 기대인플레이션 두 번째 출처 · 성장 실시간 · 금융 여건 (2026-11-28 추가, 운영자 승인).

공개 통계의 숫자와 산술(변화·전년비·연율)만 싣는다. 규칙이 아니다 — 충족·판정이 없고, 문턱을 두지 않고, 판정·공개본·그래프
스크립트는 이 파일(<out>/macro.json)을 읽지 않는다. 카드 넷(CARDS — 화면 자리는 site/macro.js), 칸(ITEMS — 화면 차례):
  dollar   [달러 카드 · 유동성 묶음] 연준 광의 달러지수(명목, DTWEXBGS — H.10, 2006-01 = 100) 수준 · 4주 변화(28일 전 이하 마지막
           관측 대비 %) · 13주 변화(91일 전 이하). ICE 달러지수(DXY) 값은 싣지 않는다(설명 글에서 차이만)
  market   [기대인플레이션 카드 · 물가 묶음] 시장 기반: 10년 BEI(T10YIE — 규칙 '실질금리와 기대인플레이션'이 쓰는 시리즈) ·
           5년 뒤 5년(T5YIFR) 수준과 4주 · 13주 변화(bp)
  model    [같은 카드] 모형 기반: 클리블랜드 연은 10년 기대인플레이션(EXPINF10YR, 월간)과 전월 값, 1년(EXPINF1YR — 없어도 칸은
           싣는다, OPTIONAL). 두 줄을 잇거나 차를 내지 않는다 — '재는 방식이 다르다'는 것만 보인다
  wei      [성장 카드 · 신용·경기 묶음] 주간경제지수 WEI(Lewis-Mertens-Stock — 2023-12부터 달라스 연은이 낸다) 마지막 주 값 ·
           4주 전 · 13주 전 값(같은 눈금이라 차가 아니라 값을 나란히)
  indpro   [같은 카드] 산업생산(INDPRO — 연준 이사회 G.17) 지수 · 전년비(1년 전 같은 달) · 3개월 연율((이번 달 ÷ 3개월 전)^4 − 1)
  cfnai    [같은 카드] 시카고 연은 국가활동지수 CFNAI와 3개월 평균 CFNAIMA3의 마지막 달 값과 전월 값
  nfci     [금융 여건 카드 · 신용·경기 묶음] 시카고 연은 NFCI · ANFCI(주간) 수준 · 4주 변화(28일 전 이하 마지막 관측 대비 차) ·
           관측 주(금요일). 신용 긴축 카드의 NFCICREDIT 로직(credit_fetch)과 따로다 — 그 파일을 읽지도 고치지도 않는다

자료 이용 조건(LICENCE · NOTICES):
  DTWEXBGS · INDPRO  연준 이사회 — 'public domain and may be copied and distributed without permission'(이사회 고지), FRED
                     'Public Domain: Citation Requested'. FRED 권장 인용을 싣는다
  WEI                FRED 'Public Domain: Citation Requested'. 달라스 연은 고지는 사적 이익 목적이 아니고 출처를 밝히면 복제를 허락한다
  T10YIE · T5YIFR    세인트루이스 연은 계산 시리즈 — FRED 'Copyrighted: Citation Required'(공개 사이트에 이미 있는 T10YIE와 같다)
  EXPINF10YR · 1YR   클리블랜드 연은 — CC BY-SA 4.0(클리블랜드 연은 원문 문구와 DOI 인용을 싣는다, CLEVELAND_NOTICE)
  NFCI · ANFCI · CFNAI · CFNAIMA3
                     시카고 연은 — FRED 'Copyrighted: Citation Required'이지만 시카고 연은 법적 고지는 재게시·배포에 서면 허락을
                     요구한다. 운영자가 2026-11-28 위험을 알고 우선 싣기로 했다(허락 요청은 따로 — README '한계'의 회색 지대).
                     카드 출처 줄에 '허락 확인 중'을 적는다(CHICAGO_NOTICE)
그 밖의 조건(재배포 제한 등)이 붙은 시리즈는 이 파일에 넣지 않는다(테스트가 목록을 고정한다). 미시간대(MICH) · 뉴욕 연은 SCE ·
GDPNow는 넣지 않는다.

실패·이어 싣기·문구 원칙은 oil_fetch와 같다: 칸마다 따로, 못 받은 칸은 직전 숫자를 '받지 못함'과 그날부터라는 날짜와 함께(직전
값이 없으면 사유만), 받은 자료가 직전보다 이르면 받지 않는다, 문구는 이 파일에 정해 둔 것뿐(오류 원문은 싣지 않는다), 같은 내용이면
다시 쓰지 않는다, 수신 전체 BUDGET초(응답을 읽는 동안에도 본다 — ai_invest_fetch.fetch_csv). 시카고 연은 시리즈는 SERIES 끝이라 수신
시간이 모자라면 그쪽부터 빠진다.

종료코드: 0 한 칸이라도 이번에 받음 / 1 하나도 못 받음(또는 파일을 쓰지 못함). 워크플로 단계는 continue-on-error, 알림 없음.

사용법: python scripts/macro_fetch.py [--out data] [--work .work] [--offline]
"""
import os, sys, json, time, bisect, argparse, datetime

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import fred_fetch as ff
import render_public as rp
import ai_invest_fetch as ai                  # 수신(load_series)·쓰기·꼴 검사·숫자 꼴을 그대로 쓴다

SCHEMA = 1
REPO = os.path.dirname(SCRIPTS)
DEFAULT_OUT = os.path.join(REPO, "data")
DEFAULT_WORK = os.path.join(REPO, ".work")
FILE = "macro.json"
CACHE = "macro"                               # <work>/macro/<ID>.csv

BUDGET = 60                                   # 수신 전체(초, 요청 11회) — 워크플로 단계 제한(2분) 안에서 끝나게
W4_DAYS, W13_DAYS = 28, 91                    # 4주 · 13주
TOL_DAYS = 7                                  # 견줄 관측이 목표 날짜보다 이만큼 넘게 이르면 비운다(휴일·주간 자료 여유)

_BOARD = "Board of Governors of the Federal Reserve System (US)"
_STL = "Federal Reserve Bank of St. Louis"
_CLE = "Federal Reserve Bank of Cleveland"
_CHI = "Federal Reserve Bank of Chicago"
_WEI = "Lewis, Daniel J., Mertens, Karel and Stock, James H."   # FRED가 WEI의 출처로 적는 저자(발표는 달라스 연은)
# FRED 권장 인용의 출처·제목
SOURCES = {
    "DTWEXBGS": (_BOARD, "Nominal Broad U.S. Dollar Index"),
    "T10YIE": (_STL, "10-Year Breakeven Inflation Rate"),
    "T5YIFR": (_STL, "5-Year, 5-Year Forward Inflation Expectation Rate"),
    "EXPINF10YR": (_CLE, "10-Year Expected Inflation"),
    "EXPINF1YR": (_CLE, "1-Year Expected Inflation"),
    "WEI": (_WEI, "Weekly Economic Index (Lewis-Mertens-Stock)"),
    "INDPRO": (_BOARD, "Industrial Production: Total Index"),
    # 시카고 연은 — 끝에 둬 수신 시간이 모자라면 이쪽부터 빠진다
    "CFNAI": (_CHI, "Chicago Fed National Activity Index"),
    "CFNAIMA3": (_CHI, "Chicago Fed National Activity Index: Three Month Moving Average"),
    "NFCI": (_CHI, "Chicago Fed National Financial Conditions Index"),
    "ANFCI": (_CHI, "Chicago Fed Adjusted National Financial Conditions Index"),
}
# 화면에 적는 기관 이름(출처 줄 — 화면은 site/macro.js의 SOURCE_LABEL)
LICENCE = {"DTWEXBGS": "public-domain", "INDPRO": "public-domain", "WEI": "public-domain",
           "T10YIE": "citation-required", "T5YIFR": "citation-required",
           "EXPINF10YR": "cc-by-sa-4.0", "EXPINF1YR": "cc-by-sa-4.0",
           "CFNAI": "chicago-fed-permission-pending", "CFNAIMA3": "chicago-fed-permission-pending",
           "NFCI": "chicago-fed-permission-pending", "ANFCI": "chicago-fed-permission-pending"}
SERIES = list(SOURCES)
PERMISSION_DECIDED = "2026-11-28"             # 시카고 연은 자료를 허락 확인 전에 싣기로 한 운영자 결정 날

NOTICE = ("이 사이트의 규칙 점검에 쓰지 않는 참고 자료다. 공개 통계를 그대로 옮기거나 그것으로 계산한 산술이고, 문턱을 두지 않으며, "
          "예측하지 않는다.")
COMPUTED_NOTICE = "변화·전년비·연율은 macro-regime-check가 원자료로 계산한 값이다."
BOARD_NOTICE = ("연준 이사회 자료(DTWEXBGS — H.10 · INDPRO — G.17)는 이사회 고지대로 공공 영역이다('public domain and may be "
                "copied and distributed without permission'). Source: Board of Governors of the Federal Reserve System. "
                "이사회 인장·로고는 쓰지 않는다.")
CITATION_NOTICE = ("T10YIE·T5YIFR은 FRED에서 'Copyrighted: Citation Required'로 표시된 세인트루이스 연은 자료라 FRED 권장 인용을 "
                   "함께 싣는다.")
CLEVELAND_NOTICE = ("클리블랜드 연은 기대인플레이션(EXPINF10YR · EXPINF1YR): \"This work by Federal Reserve Bank of Cleveland is "
                    "licensed under Creative Commons Attribution-ShareAlike 4.0 International.\" 인용: \"Inflation Expectations.\" "
                    "Federal Reserve Bank of Cleveland. https://doi.org/10.26509/frbc-infexp — FRED에서 받아 값을 바꾸지 않고 "
                    "싣는다. 이 칸의 값도 같은 CC BY-SA 4.0으로 내놓는다(https://creativecommons.org/licenses/by-sa/4.0/).")
WEI_NOTICE = ("WEI(Lewis-Mertens-Stock)는 2023년 12월부터 달라스 연은이 낸다(FRED 경유). 달라스 연은 고지는 사적 이익 목적이 "
              "아니고 출처를 밝히면 복제를 허락한다. FRED 권장 인용은 저자 세 사람을 출처로 적는다.")
CHICAGO_NOTICE = ("시카고 연은 자료(NFCI · ANFCI · CFNAI · CFNAIMA3) — 허락 확인 중. FRED는 'Copyrighted: Citation Required'로 "
                  "표시하지만, 시카고 연은 법적 고지는 재게시·배포에 시카고 연은의 서면 허락을 요구한다. 허락을 받은 것이 아니다 — "
                  f"운영자가 {PERMISSION_DECIDED} 위험을 알고 우선 싣기로 했고 허락 요청은 따로 한다. 시카고 연은이 요청하면 내린다. "
                  "FRED 권장 인용을 함께 싣는다.")
SERIES_NOTICES = {"DTWEXBGS": BOARD_NOTICE, "INDPRO": BOARD_NOTICE, "T10YIE": CITATION_NOTICE, "T5YIFR": CITATION_NOTICE,
                  "EXPINF10YR": CLEVELAND_NOTICE, "EXPINF1YR": CLEVELAND_NOTICE, "WEI": WEI_NOTICE,
                  **{sid: CHICAGO_NOTICE for sid in ("CFNAI", "CFNAIMA3", "NFCI", "ANFCI")}}
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


def at_or_before(series, target, tol=TOL_DAYS):
    """target 이하 마지막 관측 (날짜, 값) — 그 관측이 target보다 tol일 넘게 이르면 None."""
    i = bisect.bisect_right([d for d, _ in series], target) - 1
    if i < 0 or (target - series[i][0]).days > tol:
        return None
    return series[i]


def pct(a, b):
    return None if a is None or b is None or b == 0 else (a / b - 1) * 100


def back(series, days):
    """마지막 관측의 days일 전 이하 마지막 관측 값(없으면 None)."""
    b = at_or_before(series, series[-1][0] - datetime.timedelta(days=days))
    return None if b is None else b[1]


def diff(a, b, scale=1.0):
    return None if a is None or b is None else (a - b) * scale


def _mkey(d):
    return d.year * 12 + d.month - 1


def by_month(series):
    return {_mkey(d): v for d, v in series}


def calc_dollar(S):
    s = S["DTWEXBGS"]
    d1, v1 = s[-1]
    return {"date": _iso(d1),
            "values": {"level": _r(v1), "w4": _r(pct(v1, back(s, W4_DAYS))), "w13": _r(pct(v1, back(s, W13_DAYS)))}}


def calc_market(S):
    a, f = S["T10YIE"], S["T5YIFR"]
    (ad, av), (fd, fv) = a[-1], f[-1]
    return {"date": _iso(max(ad, fd)),
            "values": {"be10": _r(av), "be10_date": _iso(ad), "be10_4w": _r(diff(av, back(a, W4_DAYS), 100)),
                       "be10_13w": _r(diff(av, back(a, W13_DAYS), 100)),
                       "fwd": _r(fv), "fwd_date": _iso(fd), "fwd_4w": _r(diff(fv, back(f, W4_DAYS), 100)),
                       "fwd_13w": _r(diff(fv, back(f, W13_DAYS), 100))}}


def calc_model(S):
    e = S["EXPINF10YR"]
    m = by_month(e)
    d1, v1 = e[-1]
    one = S.get("EXPINF1YR") or []
    return {"date": _iso(max([d1] + ([one[-1][0]] if one else []))),
            "values": {"month": _iso(d1), "e10": _r(v1), "e10_prev": _r(m.get(_mkey(d1) - 1)),
                       "e1": _r(one[-1][1]) if one else None, "e1_month": _iso(one[-1][0]) if one else None,
                       "e1_failed_since": None}}


def calc_wei(S):
    w = S["WEI"]
    d1, v1 = w[-1]
    return {"date": _iso(d1), "values": {"wei": _r(v1), "w4": _r(back(w, W4_DAYS)), "w13": _r(back(w, W13_DAYS))}}


def calc_indpro(S):
    s = S["INDPRO"]
    m = by_month(s)
    d1, v1 = s[-1]
    k = _mkey(d1)
    yoy = pct(v1, m.get(k - 12))
    if yoy is None:
        raise ItemError("format")
    b3 = m.get(k - 3)
    a3 = None if not b3 else ((v1 / b3) ** 4 - 1) * 100
    return {"date": _iso(d1), "values": {"month": _iso(d1), "level": _r(v1), "yoy": _r(yoy), "a3": _r(a3)}}


def calc_cfnai(S):
    c, ma = S["CFNAI"], S["CFNAIMA3"]
    (cd, cv), (md, mv) = c[-1], ma[-1]
    return {"date": _iso(max(cd, md)),
            "values": {"month": _iso(cd), "cfnai": _r(cv), "cfnai_prev": _r(by_month(c).get(_mkey(cd) - 1)),
                       "ma3_month": _iso(md), "ma3": _r(mv), "ma3_prev": _r(by_month(ma).get(_mkey(md) - 1))}}


def calc_nfci(S):
    n, a = S["NFCI"], S["ANFCI"]
    (nd, nv), (ad, av) = n[-1], a[-1]
    return {"date": _iso(max(nd, ad)),
            "values": {"nfci": _r(nv), "nfci_date": _iso(nd), "nfci_4w": _r(diff(nv, back(n, W4_DAYS))),
                       "anfci": _r(av), "anfci_date": _iso(ad), "anfci_4w": _r(diff(av, back(a, W4_DAYS)))}}


# ---------- 칸 정의 (차례 = 화면 차례) ----------
# card: 화면의 카드(site/macro.js의 CARDS와 같다 — 테스트가 견준다)
# values: 이름 → 꼴("num" · "num?" · "day" · "day?") — 직전 파일 검사에도 쓴다
# ends: 시리즈마다의 끝 날짜(values의 날짜 칸) — 칸의 date와 함께 하나라도 직전보다 이르면 받지 않는다
# optional: 없어도 칸을 계산하는 시리즈 → 그 시리즈로 채우는 값 이름. 그 값이 있을 때만 출처에 싣는다
# carry: optional 시리즈를 이번에 받지 못하면 → (직전 파일에서 이어 싣는 값 이름들, 못 받은 첫날을 적는 값 이름).
#        다른 칸처럼 직전 값을 남기고 '받지 못함(언제부터)'을 단다 — 칸의 나머지는 이번 값(2026-11-28 교차 검토)

ITEMS = [
    {"key": "dollar", "card": "dollar", "title": "연준 광의 달러지수 (명목, 2006-01 = 100)", "series": ["DTWEXBGS"],
     "calc": calc_dollar, "values": {"level": "num", "w4": "num?", "w13": "num?"}},
    {"key": "market", "card": "expinf", "title": "시장 기반 — 10년 BEI · 5년 뒤 5년 (일간)", "series": ["T10YIE", "T5YIFR"],
     "calc": calc_market,
     "values": {"be10": "num", "be10_date": "day", "be10_4w": "num?", "be10_13w": "num?",
                "fwd": "num", "fwd_date": "day", "fwd_4w": "num?", "fwd_13w": "num?"},
     "ends": ["be10_date", "fwd_date"]},
    {"key": "model", "card": "expinf", "title": "모형 기반 — 클리블랜드 연은 10년 · 1년 (월간)", "series": ["EXPINF10YR"],
     "calc": calc_model, "optional": {"EXPINF1YR": "e1"},
     "carry": {"EXPINF1YR": (("e1", "e1_month"), "e1_failed_since")},
     "values": {"month": "day", "e10": "num", "e10_prev": "num?", "e1": "num?", "e1_month": "day?", "e1_failed_since": "day?"},
     "ends": ["month", "e1_month"]},
    {"key": "wei", "card": "growth", "title": "주간경제지수 WEI (달라스 연은, 주간)", "series": ["WEI"], "calc": calc_wei,
     "values": {"wei": "num", "w4": "num?", "w13": "num?"}},
    {"key": "indpro", "card": "growth", "title": "산업생산 (연준 이사회 G.17, 월간)", "series": ["INDPRO"], "calc": calc_indpro,
     "values": {"month": "day", "level": "num", "yoy": "num", "a3": "num?"}},
    {"key": "cfnai", "card": "growth", "title": "시카고 연은 국가활동지수 CFNAI · CFNAI-MA3 (월간)", "series": ["CFNAI", "CFNAIMA3"],
     "calc": calc_cfnai,
     "values": {"month": "day", "cfnai": "num", "cfnai_prev": "num?", "ma3_month": "day", "ma3": "num", "ma3_prev": "num?"},
     "ends": ["month", "ma3_month"]},
    {"key": "nfci", "card": "fincond", "title": "시카고 연은 금융여건지수 NFCI · ANFCI (주간)", "series": ["NFCI", "ANFCI"],
     "calc": calc_nfci,
     "values": {"nfci": "num", "nfci_date": "day", "nfci_4w": "num?", "anfci": "num", "anfci_date": "day", "anfci_4w": "num?"},
     "ends": ["nfci_date", "anfci_date"]},
]
BY_KEY = {it["key"]: it for it in ITEMS}
CARDS = list(dict.fromkeys(it["card"] for it in ITEMS))


# ---------- 문구 ----------

def _f(v, nd=2, sign=False, unit=""):
    return ai._f(v, nd, sign, unit)


def _ml(day):
    return day[:7] if day else "—"


def _asof(day, date):
    return "" if not day or day == date else f"({day})"


def _bp(v):
    return _f(v, 0, True, "bp")


def texts(key, v, date):
    """칸 → (숫자 줄, 덧붙이는 줄 목록). 정해 둔 문구에 숫자만 넣는다."""
    if key == "dollar":
        return (f"{date} {_f(v['level'], 2)} · 4주 {_f(v['w4'], 1, True, '%')} · 13주 {_f(v['w13'], 1, True, '%')}",
                ["연준 이사회 H.10의 명목 광의 달러지수(일간 값, 주간 공표 — 보통 한 주 남짓 늦게 나온다). 4주 변화는 28일 전, 13주 "
                 "변화는 91일 전(휴일이면 그 전 마지막 관측)과 견준 %다. 값이 오르면 교역 비중으로 묶은 여러 통화에 견줘 달러 값이 "
                 "올랐다는 뜻이다.",
                 "ICE 달러지수(DXY)와 다르다 — 광의 지수는 26개 교역 상대국 통화를 교역 비중으로 묶고, DXY는 6개 통화(유로 비중이 "
                 "가장 크다)로 만든다. 이 사이트는 DXY 값을 싣지 않는다."])
    if key == "market":
        return (f"{date} 10년 BEI {_f(v['be10'], 2, unit='%')}{_asof(v['be10_date'], date)} (4주 {_bp(v['be10_4w'])} · 13주 "
                f"{_bp(v['be10_13w'])}) · 5년 뒤 5년 {_f(v['fwd'], 2, unit='%')}{_asof(v['fwd_date'], date)} (4주 "
                f"{_bp(v['fwd_4w'])} · 13주 {_bp(v['fwd_13w'])})",
                ["둘 다 국채 시장의 값이다(세인트루이스 연은 계산). 10년 BEI는 10년 명목 국채와 10년 TIPS 금리의 차로, 규칙 "
                 "'실질금리와 기대인플레이션'이 쓰는 시리즈다. 5년 뒤 5년은 5년·10년 BEI로 계산한 5년 뒤부터 5년 동안의 값이다. "
                 "위험·유동성 프리미엄이 섞인다. 4주·13주 변화는 28일·91일 전(휴일이면 그 전 마지막 관측)과의 차다."])
    if key == "model":
        since = v.get("e1_failed_since")
        late = f" — 받지 못함({since}부터), 직전 값" if since else ""
        one = (f" · 1년 {_f(v['e1'], 2, unit='%')}({_ml(v['e1_month'])}{late})" if v.get("e1") is not None
               else f" · 1년 미수신({since}부터)" if since else " · 1년 미수신")
        return (f"{_ml(v['month'])} 10년 {_f(v['e10'], 2, unit='%')} (전월 {_f(v['e10_prev'], 2, unit='%')}){one}",
                ["클리블랜드 연은의 모형 추정치(월간)다. 국채 금리·인플레이션 스왑·전문가 설문·CPI를 함께 써서 기대인플레이션과 "
                 "위험 프리미엄을 나눠 추정한다. 위 시장 기반 줄과 재는 방식이 달라 두 값을 잇거나 차를 내지 않는다. CPI가 "
                 "발표되는 날 새 달의 값이 나온다."])
    if key == "wei":
        return (f"{date} 주 {_f(v['wei'], 2, unit='%')} · 4주 전 {_f(v['w4'], 2, unit='%')} · 13주 전 "
                f"{_f(v['w13'], 2, unit='%')}",
                ["WEI(Lewis-Mertens-Stock)는 실업수당 청구·철강 생산·전력 사용 같은 주간 자료 10개의 공통 움직임을 실질 GDP의 "
                 "4분기 전 대비 성장률 눈금에 맞춘 지수다. 2023년 12월부터 달라스 연은이 낸다. 토요일로 끝나는 주의 값이 다음 주에 "
                 "나오고, 지난 값도 고쳐진다."])
    if key == "indpro":
        return (f"{_ml(v['month'])} 지수 {_f(v['level'], 1)} · 전년비 {_f(v['yoy'], 1, True, '%')} · 3개월 연율 "
                f"{_f(v['a3'], 1, True, '%')}",
                ["연준 이사회 G.17 산업생산(제조·광업·전기·가스, 계절조정, 2022 = 100). 전년비는 1년 전 같은 달, 3개월 연율은 "
                 "(이번 달 ÷ 3개월 전)^4 − 1이다. 산업 부문만이라 경제 전체의 성장률이 아니다."])
    if key == "cfnai":
        return (f"{_ml(v['month'])} CFNAI {_f(v['cfnai'], 2, True)} (전월 {_f(v['cfnai_prev'], 2, True)}) · CFNAI-MA3 "
                f"{_f(v['ma3'], 2, True)}{_asof(_ml(v['ma3_month']), _ml(v['month']))} (전월 {_f(v['ma3_prev'], 2, True)})",
                ["시카고 연은 국가활동지수: 생산·소득, 고용, 소비·주택, 판매·주문·재고 네 갈래 85개 월간 지표의 가중 평균이다. "
                 "시카고 연은의 정의로 0은 과거 추세 성장, 양수는 추세보다 빠른 성장, 음수는 추세보다 느린 성장이다. CFNAI-MA3는 "
                 "석 달 평균이다. 지난 값은 발표마다 고쳐진다."])
    if key == "nfci":
        return (f"{date} 주 NFCI {_f(v['nfci'], 3, True)}{_asof(v['nfci_date'], date)} (4주 {_f(v['nfci_4w'], 3, True)}) · "
                f"ANFCI {_f(v['anfci'], 3, True)}{_asof(v['anfci_date'], date)} (4주 {_f(v['anfci_4w'], 3, True)})",
                ["시카고 연은 국가금융여건지수: 위험·신용·레버리지 세 갈래 105개 지표의 가중 평균을 1971년 이후 평균 0·표준편차 "
                 "1로 맞춘 값이다. 시카고 연은의 정의로 0은 1971년 이후 평균이고, 양수는 평균보다 빠듯한 여건, 음수는 평균보다 "
                 "느슨한 여건이다. ANFCI는 경제 활동·물가로 설명되는 몫을 뺀 값이다.",
                 "금요일로 끝나는 주의 값이 다음 주 수요일에 나오고, 지난 값도 주마다 조금씩 고쳐진다. 4주 변화는 28일 전 관측과의 "
                 "차다. 신용 긴축 카드의 NFCI 신용 하위 지수(NFCICREDIT)는 이 지수의 한 갈래다."])
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
    return {"key": key, "card": spec["card"], "name": spec["title"], "date": core["date"], "values": core["values"],
            "retrieved": retrieved, "line": line, "extra": extra, "notices": notices(spec, core["values"]),
            "sources": sources_of(spec, retrieved, core["values"])}


# ---------- 직전 파일 ----------

def core_of(item, key):
    """직전 파일의 칸 → (core, 받은 날) 또는 None(없거나 꼴이 어긋남)."""
    spec = BY_KEY[key]
    try:
        vals = item["values"]
        ok = (ai._is_day(item["date"]) and ai._is_day(item["retrieved"]) and isinstance(vals, dict)
              and set(vals) == set(spec["values"]) and all(ai._KIND[t](vals[k]) for k, t in spec["values"].items()))
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
    return {k: v for k, v in js["items"].items() if k in BY_KEY and isinstance(v, dict)}


def _ends(key, core):
    return [("date", core["date"])] + [(k, core["values"].get(k)) for k in BY_KEY[key].get("ends", ())]


def carry_over(key, core, old, today):
    """이번에 받지 못한 optional 시리즈(core의 missing) — 그 값은 직전 파일의 것을 남기고, 못 받은 첫날을 적는다(직전에도 못
    받았으면 그날을 지킨다). 직전 값이 없으면 값은 비고 날짜만 적는다."""
    was = old[0]["values"] if old else {}
    for sid in core.pop("missing", ()):
        fields, since_key = BY_KEY[key]["carry"][sid]
        for f in fields:
            core["values"][f] = was.get(f)
        since = was.get(since_key)
        core["values"][since_key] = since if ai._is_day(since) else today.isoformat()
    return core


def item_ok(key, core, prev, today):
    old = core_of(prev, key) if prev else None
    core = carry_over(key, core, old, today)
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
    return {"ok": False, "stale": False, "error": REASONS[code], "failed_since": since, "key": key, "card": spec["card"],
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
            "cards": {c: [s["key"] for s in ITEMS if s["card"] == c] for c in CARDS},
            "order": [s["key"] for s in ITEMS], "items": items}


# ---------- 수신 ----------

def load_all(work, offline=False, fred_load=None, clock=time.monotonic, budget=BUDGET, opener=None):
    """{ID: 시계열}과 {ID: 실패 코드}. 온라인에서 캐시로 대신한 것은 실패('cache')(fred_load를 준 경우 — 테스트)."""
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
    S = {sid: s for sid, s in S.items() if s}
    out = {}
    for spec in ITEMS:
        miss = [sid for sid in spec["series"] if sid not in S]
        if miss:
            out[spec["key"]] = ItemError(errors.get(miss[0], "format"))
            continue
        try:
            core = spec["calc"](S)
            missing = [sid for sid in spec.get("carry", {}) if sid not in S]
            if missing:
                core["missing"] = missing
            out[spec["key"]] = core
        except ItemError as e:
            out[spec["key"]] = e
        except Exception as e:                  # 계산 쪽 뜻밖의 오류도 그 칸만 실패로
            print(f"[macro_fetch] {spec['key']} 계산 오류: {type(e).__name__}", file=sys.stderr)
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
    ap = argparse.ArgumentParser(description="FRED 공개 통계 → 달러·기대인플레이션·성장·금융 여건 참고 자료(<out>/macro.json)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    ap.add_argument("--work", default=DEFAULT_WORK, help="작업 폴더 — 원문 캐시는 <work>/macro/ (기본: 저장소의 .work/)")
    ap.add_argument("--offline", action="store_true", help="요청하지 않고 캐시만 읽는다(로컬 확인용)")
    a = ap.parse_args(argv)
    out, work = os.path.abspath(a.out), os.path.abspath(a.work)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    data, errors = load_all(work, a.offline, fred_load, clock, opener=opener)
    data = build(compute(data, errors, now.date()), previous(out), now)
    for spec in ITEMS:                          # Actions 로그 — 날짜와 정해 둔 사유만(값은 찍지 않는다)
        it = data["items"][spec["key"]]
        if it["ok"]:
            print(f"[macro_fetch] {spec['key']} {it['date']} 기준")
        else:
            kept = f" — 직전 값({it['date']} 기준) 유지" if it["stale"] else ""
            ai.annotate(f"달러·기대인플레이션·성장·금융 여건 참고 {spec['key']} 받지 못함: {it['error']}{kept}")
    try:
        if differs(out, data):
            write(out, data)
    except OSError as e:
        print(f"[macro_fetch] {FILE}를 쓰지 못함: {type(e).__name__}", file=sys.stderr)
        return 1
    return 0 if any(it["ok"] for it in data["items"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
