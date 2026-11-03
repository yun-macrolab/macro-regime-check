#!/usr/bin/env python3
"""참고 자료 — 연준 재무상태표(H.4.1 주간) (2026-11-03 추가, 사용자 결정: 운영자 비공개 결론 런 메일의 연준 재무상태표
주간 줄(fed_bs)을 공개 카드로 — 먼저 올려 써 보며 다듬기로).

공개 통계의 숫자와 산술(나눔·4주/13주 차·5영업일 최대)만 싣는다. 규칙이 아니다 — 충족·판정·문턱 표식이 없고, 판정·공개본·
그래프 스크립트는 이 파일(<out>/fedbs.json)을 읽지 않는다. 유동성 묶음에서 지준·재정 카드 바로 뒤의 카드이고, 규칙 카드
'지준과 통화승수'의 지준/GDP와 지준·재정 카드의 13주 나눔을 주간으로 읽는 재료다. 칸(ITEMS — 화면 차례):
  reserves  지준(주 평균 WRESBAL)과 지준/명목GDP — regime_check.compute와 같은 식(liquidity_fetch.reserves_gdp: 주 평균의 마지막
            값 ÷ 1000 ÷ 마지막 분기 GDP × 100)이라 규칙 카드와 같은 숫자다(테스트가 견준다). 규칙 하한(regime_rules.TH
            ['reserves_gdp_low'])의 차 %p·bn. 4주 평균 = (최근 4주 WRESBAL 평균) ÷ 최신 GDP — 정의는 이것 하나(네 주가 이어질
            때만, 첫 주와 마지막 주가 21일 차). 분모 바뀜: 직전 fedbs.json의 주를 처음 실을 때의 GDP(first)와 이번 GDP가
            다르면(새 분기·개정) 같은 지준으로 견준 분모 몫(%p) — 같은 주를 다시 실을 때는 그 주의 견줌을 그대로 두고, 같은 주
            안에서 GDP만 바뀌면 다음 주가 싣는다(비공개가 메일로 실은 주의 GDP와 견주는 것과 같은 뜻). 그래프: 최근 52주 지준과
            규칙 하한 × 마지막 분기 GDP(지난 주들도 지금 GDP로 그은 선)
  dec       지준 변화의 나눔 4주/13주 — 수요일 수준(WRBWFRBL) = 재무부 현금 TGA(WDTGAL) · 익일물 역레포(WLRRAOL — H.4.1
            '역레포: 그 밖', 익일물 역레포 기구가 대부분) · 해외 공적 역레포 풀(WLRRAFOIAL — 부채 쪽, 자산 쪽 FIMA 레포 기구가
            아니다) · 연준 단기채(WSHOBL) · 이표채(WSHONBNL) · MBS(WSHOMCB) · 현금 통화(WCICL) · 그 밖(나머지). 부호는 지준 쪽.
            창 규칙은 liquidity_fetch.calc_reserves와 같다(여덟 시리즈가 모두 있는 마지막 수요일과 그 28·91일 전 이하 마지막
            공통 관측 — NEAR_DAYS 안). 13주는 지준·재정 카드의 13주 나눔과 같은 창·같은 값이다(역레포 = 익일물 + 해외 공적,
            그 카드의 그 밖 = MBS + 현금 통화 + 이 카드의 그 밖 — 테스트가 견준다). 보이는 정수끼리 합이 맞게 '그 밖'이 반올림을
            받는다. 1주는 15일·월말 하루에 크게 흔들려 싣지 않는다. 두 창의 출발·끝 수요일이 월말(분기 끝 달이면 분기말)·15일이면
            표시한다(창은 옮기지 않는다)
  spread    SOFR − IORB 최근 5영업일(SOFR의 마지막 관측 다섯): 최대 bp와 날짜(같은 값이면 이른 날)·0보다 큰 날 n/m(그 SOFR
            날짜 이하 IORB가 3일보다 멀면 그날은 비우고 m에서 뺀다)·월말·15일 표시
  srf       상시 레포(SRF) 이용(RPONTTLD) 최근 5영업일 최대 bn과 날짜
  rrp       익일물 역레포(RRPONTSYD) 마지막 값
  week      그 H.4.1 주(목~수)가 15일·월말·FOMC 결정일을 품는지('FOMC 뒤 첫 H.4.1' — 결정일(수)이 그 주 마지막 날이라 그 주
            숫자는 시행 전 값)와 다음 FOMC 결정일(실행 시각에 아직 성명 — 결정일 14:00 미 동부 — 이 나오지 않은 첫 회의: 예약
            실행 UTC 22:17은 결정일에도 성명 뒤라 그날 회의는 '다음'이 아니다). FOMC 일정은 이 파일의 FOMC 표(2026년은
            site/people-data.js의 회의 장부와 같다, 테스트가 견준다. 2027년은 연준 FOMC 일정 페이지(2026-10-28 갱신)의 여덟
            회의 — 연준 고지대로 각 회의는 직전 회의에서 확정되기 전까지 잠정이라 '(잠정)')
산식은 비공개 파이프라인의 fed_bs.py와 같다(저장소를 넘어 가져오지 않고 여기서 따로 쓴다 — 고치면 양쪽을 같이). 비공개 쪽과
다른 곳: 상태 파일이 없다 — 날마다 받고, '분모 바뀜'은 직전 fedbs.json의 주를 처음 실을 때의 GDP와 견준다(비공개는 메일로
실은 주의 GDP와 — 같은 뜻, 같은 주를 다시 실을 때도 그 견줌을 보인다).
같은 주를 다시 실을 때 '싣는 때' 규칙(새 주 한 번·보완·미수신 한 줄)은 없다 — 카드는 늘 마지막으로 받은 값을 보인다.
날짜는 YYYY-MM-DD, 분기는 2026Q3, 음수 부호는 '-'(지준·재정 카드와 같은 꼴), '→' 대신 '~'·'에서 …로'.

자료 이용 조건(2026-11-03 이 샌드박스에서 FRED 시리즈 쪽 JSON-LD의 license와 Suggested Citation으로 확인 — LICENCE):
  'Public Domain: Citation Requested' — 연준 이사회 H.4.1 열(WRESBAL·WRBWFRBL·WDTGAL·WLRRAOL·WLRRAFOIAL·WSHOBL·WSHONBNL·
  WSHOMCB·WCICL)·IORB, BEA GDP. FRED 권장 인용을 자료 파일(sources[].citation)에 싣는다.
  'Copyrighted: Citation Required' — 뉴욕 연은 SOFR·RPONTTLD·RRPONTSYD. FRED 권장 인용을 카드에 글자로, 뉴욕 연은 이용약관의
  기본 출처 형식(© 연도)과 관계없음 고지, 계산값 표시(한·영)를 함께 — SOFR은 참조금리 고지·DTCC 문장도(규칙 카드 SOFR과
  같은 문구, render_public). 그 밖의 조건이 붙은 시리즈는 이 파일에 넣지 않는다(테스트가 목록을 고정한다).

수신: FRED CSV 14개(기본 머리글 그대로 — 머리글을 더하면 FRED가 응답을 멈춘다, ai_invest_fetch.load_series), 요청마다 min(15초, 남은 예산),
수신 전체 BUDGET초(응답을 읽는 동안에도 본다). 주간·일간 모두 실행마다 받는다(공개 쪽은 하루 1회 실행 — 상태 파일 없음).
H.4.1은 목요일 16:30(미 동부)에 나오고 FRED에 몇 분 안에 들어온다 — 예약 실행(UTC 22:17, 미 동부 같은 날 17:17·18:17)이 같은
날 받는다(국경일이 끼면 하루 늦게 나온다).

실패·이어 싣기·문구 원칙은 liquidity_fetch·oil_fetch와 같다: 칸마다 따로, 못 받은 칸은 직전 숫자를 '받지 못함'과 그날부터라는
날짜와 함께(직전 값이 없으면 사유만), 받은 자료가 직전보다 이르면 받지 않는다, 문구는 이 파일에 정해 둔 것뿐(오류 원문은 싣지
않는다), 같은 내용이면 다시 쓰지 않는다.

종료코드: 0 한 칸이라도 이번에 받음 / 1 하나도 못 받음(또는 파일을 쓰지 못함). 워크플로 단계는 continue-on-error, 알림 없음.

사용법: python scripts/fedbs_fetch.py [--out data] [--work .work] [--offline]
"""
import os, sys, json, time, argparse, datetime

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import regime_rules as rr                     # 규칙 하한(TH['reserves_gdp_low'])만 읽는다 — 공유 파일, 고치지 않는다
import render_public as rp                    # FRED 주소·SOFR 고지·뉴욕 연은 출처 형식
import ai_invest_fetch as ai                  # 수신(load_series)·쓰기·꼴 검사를 그대로 쓴다
import liquidity_fetch as liq                 # 지준/GDP 식(reserves_gdp)·13주 창 상수(WEEKS13·NEAR_DAYS)

SCHEMA = 1
REPO = os.path.dirname(SCRIPTS)
DEFAULT_OUT = os.path.join(REPO, "data")
DEFAULT_WORK = os.path.join(REPO, ".work")
FILE = "fedbs.json"
CACHE = "fedbs"                               # <work>/fedbs/<ID>.csv

BUDGET = 60                                   # 수신 전체(초) — 워크플로 단계 제한(2분) 안에서 끝나게
WIN4, WIN13 = 28, liq.WEEKS13                 # 4주·13주(91일) — 창 규칙은 지준·재정 카드와 같다
NEAR_DAYS = liq.NEAR_DAYS
MM_DAYS = 5                                   # 단기자금 최근 5영업일(시리즈마다 마지막 관측 다섯)
IORB_GAP = 3                                  # SOFR 날짜 이하 IORB 관측이 이보다 멀면 그날은 비운다
CHART_WEEKS = 52
AVG4_DEF = "4주 평균 = (최근 4주 WRESBAL 평균) ÷ 최신 GDP"   # 정의는 이것 하나 — 비공개 fed_bs.AVG4_DEF와 같은 글

_BOARD = "Board of Governors of the Federal Reserve System (US)"
_NYFED = "Federal Reserve Bank of New York"
# FRED 권장 인용의 출처·제목(2026-11-03 시리즈 쪽 Suggested Citation 그대로)
SOURCES = {
    "WRESBAL": (rp.FRED_SOURCE["WRESBAL"], rp.FRED_TITLE["WRESBAL"]),
    "GDP": (rp.FRED_SOURCE["GDP"], rp.FRED_TITLE["GDP"]),
    "WRBWFRBL": (_BOARD, "Liabilities and Capital: Other Factors Draining Reserve Balances: Reserve Balances with Federal "
                         "Reserve Banks: Wednesday Level"),
    "WDTGAL": (_BOARD, "Liabilities and Capital: Liabilities: Deposits with F.R. Banks, Other Than Reserve Balances: "
                       "U.S. Treasury, General Account: Wednesday Level"),
    "WLRRAOL": (_BOARD, "Liabilities and Capital: Liabilities: Reverse Repurchase Agreements: Others: Wednesday Level"),
    "WLRRAFOIAL": (_BOARD, "Liabilities and Capital: Liabilities: Reverse Repurchase Agreements: Foreign Official and "
                           "International Accounts: Wednesday Level"),
    "WSHOBL": (_BOARD, "Assets: Securities Held Outright: U.S. Treasury Securities: Bills: Wednesday Level"),
    "WSHONBNL": (_BOARD, "Assets: Securities Held Outright: U.S. Treasury Securities: Notes and Bonds, Nominal: "
                         "Wednesday Level"),
    "WSHOMCB": (_BOARD, "Assets: Securities Held Outright: Mortgage-Backed Securities: Wednesday Level"),
    "WCICL": (_BOARD, "Liabilities and Capital: Other Factors Draining Reserve Balances: Currency in Circulation: "
                      "Wednesday Level"),
    "SOFR": (rp.FRED_SOURCE["SOFR"], rp.FRED_TITLE["SOFR"]),
    "IORB": (_BOARD, "Interest Rate on Reserve Balances (IORB Rate)"),
    "RPONTTLD": (_NYFED, "Overnight Repurchase Agreements: Total Securities Purchased by the Federal Reserve in the "
                         "Temporary Open Market Operations"),
    "RRPONTSYD": (_NYFED, "Overnight Reverse Repurchase Agreements: Treasury Securities Sold by the Federal Reserve in "
                          "the Temporary Open Market Operations"),
}
# 시리즈 쪽 JSON-LD의 license(2026-11-03 확인). 이 값 밖의 시리즈는 싣지 않는다
CITE_REQUIRED = ("SOFR", "RPONTTLD", "RRPONTSYD")
LICENCE = {sid: ("citation-required" if sid in CITE_REQUIRED else "public-domain") for sid in SOURCES}
SERIES = list(SOURCES)
RES_AVG = "WRESBAL"
BS = {"res": "WRBWFRBL", "tga": "WDTGAL", "onrrp": "WLRRAOL", "pool": "WLRRAFOIAL", "bills": "WSHOBL",
      "coupons": "WSHONBNL", "mbs": "WSHOMCB", "cur": "WCICL"}     # 수요일 수준, 백만 달러 — 순서가 문구의 순서다
SIGN = {"tga": -1, "onrrp": -1, "pool": -1, "bills": 1, "coupons": 1, "mbs": 1, "cur": -1}   # 지준 쪽 부호
PARTS = (*SIGN, "other")
PART_NAME = {"tga": "재무부 현금(TGA)", "onrrp": "익일물 역레포", "pool": "해외 공적 역레포", "bills": "연준 단기채",
             "coupons": "연준 이표채", "mbs": "연준 MBS", "cur": "현금 통화", "other": "그 밖"}
SIGN_NOTE = "(부호는 지준 쪽)"
WINDOWS = (("4", WIN4), ("13", WIN13))

# FOMC 결정일 표 — (첫날, 결정일, 잠정). 2025-12·2026년은 연준 FOMC 성명 일정(2026년은 site/people-data.js의 meetings_2026과
# 같다 — 테스트가 견준다). 2027년은 연준 FOMC 일정 페이지(federalreserve.gov/monetarypolicy/fomccalendars.htm, 'Last Update:
# October 28, 2026' — 2026-11-03 확인)의 여덟 회의다. 연준 고지('Each meeting date is tentative until confirmed at the meeting
# immediately preceding it')대로 잠정 표시를 붙인다. 2027년 회의 하나(가을부터, 어느 회의인지 미정)는 표결·성명 없는 전략
# 회의라고 의장이 밝혔다(기자회견 2026-10-28). 매년 1월 갱신 때 비공개 fed_people.json의 fomc와 같이 고친다(그쪽 짝 테스트가
# 이 표가 그 일정의 앞부분과 같은지 본다)
FOMC = (("2025-12-09", "2025-12-10", False),
        ("2026-01-27", "2026-01-28", False), ("2026-03-17", "2026-03-18", False), ("2026-04-28", "2026-04-29", False),
        ("2026-06-16", "2026-06-17", False), ("2026-07-28", "2026-07-29", False), ("2026-09-15", "2026-09-16", False),
        ("2026-10-27", "2026-10-28", False), ("2026-12-08", "2026-12-09", False),
        ("2027-01-26", "2027-01-27", True), ("2027-03-16", "2027-03-17", True), ("2027-04-27", "2027-04-28", True),
        ("2027-06-08", "2027-06-09", True), ("2027-07-27", "2027-07-28", True), ("2027-09-14", "2027-09-15", True),
        ("2027-10-26", "2027-10-27", True), ("2027-12-07", "2027-12-08", True))
DECISION_HOUR = 14                            # FOMC 성명 시각(미 동부) — 이보다 늦은 실행에서 그날 회의는 '다음'이 아니다

NOTICE = ("이 사이트의 규칙 점검에 쓰지 않는 참고 자료다. 연준 H.4.1 주간 대차대조표와 단기자금 시장의 공개 통계로 계산한 "
          "산술만 싣는다. 규칙 카드 '지준과 통화승수'의 지준/GDP와 지준·재정 카드의 13주 나눔을 주간으로 읽는 재료다. "
          "금리나 자금 여건을 예측하지 않는다.")
COMPUTED_NOTICE = ("지준/GDP·하한 대비 차·4주 평균·분모 바뀜·4주/13주 차·5영업일 최대는 macro-regime-check가 원자료로 "
                   "계산한 값이다.")
SPREAD_DERIVED = ("SOFR − IORB 차와 그 5영업일 최대·0보다 큰 날 수는 macro-regime-check가 뉴욕 연은 SOFR 일별 자료와 연준 "
                  "이사회 IORB(FRED 경유)로 계산한 값이다. 뉴욕 연은이 발표한 값이 아니다.")
SPREAD_DERIVED_EN = ("The SOFR − IORB spread, its 5-business-day maximum and the count of positive days are computed by "
                     "macro-regime-check from SOFR (New York Fed) and IORB (Federal Reserve Board) data via FRED; they are "
                     "not published by the New York Fed.")
SRF_DERIVED = ("상시 레포 이용의 5영업일 최대는 macro-regime-check가 뉴욕 연은 임시 공개시장 운영 자료(FRED 경유)에서 고른 "
               "값이다. 뉴욕 연은이 발표한 값이 아니다.")
SRF_DERIVED_EN = ("The 5-business-day maximum of standing repo usage is selected by macro-regime-check from New York Fed "
                  "temporary open market operations data via FRED; it is not published by the New York Fed.")
WEEK_NOTICE = ("주의 15일·월말·FOMC 표시는 macro-regime-check가 H.4.1 주(목~수)의 날짜와 이 저장소에 적어 둔 연준 FOMC "
               "일정으로 붙인 것이다.")
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


D = datetime.date
TD = datetime.timedelta
_r = ai._r
_iso = ai._iso


def _r6(v):
    return None if v is None else round(v, 6) + 0.0


def _day(s):
    return D.fromisoformat(s)


# ---------- 날짜 표시 ----------

def level_tag(d):
    """수요일 수준 날짜(창의 출발·끝)가 그 달 마지막 날(분기 끝 달이면 '분기말', 아니면 '월말')이거나 15일이면 그 표시 — 아니면 ''."""
    if (d + TD(days=1)).month != d.month:
        return "분기말" if d.month % 3 == 0 else "월말"
    return "15일" if d.day == 15 else ""


def cal_tag(d, dates):
    """일간 관측 날짜의 표시 — 월말(그 달의 마지막 관측: 다음 관측이 다음 달이거나, 마지막 관측이면 그 뒤 사흘 안에 그 달
    평일이 없음) · 15일(15일, 또는 15일이 주말이라 밀린 16·17일의 첫 관측) — 아니면 ''."""
    i = dates.index(d)
    nxt = dates[i + 1] if i + 1 < len(dates) else None
    if nxt is not None:
        end = nxt.month != d.month
    else:
        end = all((d + TD(days=k)).month != d.month or (d + TD(days=k)).weekday() >= 5 for k in range(1, 4))
    if end:
        return "월말"
    prev = dates[i - 1] if i else None
    if d.day == 15 or (d.day in (16, 17) and prev is not None and prev.month == d.month and prev.day < 15):
        return "15일"
    return ""


def meetings():
    """FOMC 표 → [(첫날, 결정일, 잠정)] 날짜 차례."""
    return sorted((_day(a), _day(b), t) for a, b, t in FOMC)


def _nth_sunday(y, m, n):
    first = D(y, m, 1)
    return first + TD(days=(6 - first.weekday()) % 7 + 7 * (n - 1))


def decided_at(b):
    """결정일 b의 성명 시각(DECISION_HOUR시 미 동부)을 UTC로 — 서머타임(2007년 규칙: 3월 둘째 일요일 ~ 11월 첫 일요일)이면
    UTC−4, 아니면 UTC−5. 결정일은 수요일이라 전환 날(일요일)에 걸리지 않는다. 시간대 자료(tzdata)에 기대지 않는다."""
    off = 4 if _nth_sunday(b.year, 3, 2) <= b < _nth_sunday(b.year, 11, 1) else 5
    return datetime.datetime(b.year, b.month, b.day, DECISION_HOUR + off, tzinfo=datetime.timezone.utc)


# ---------- 산술 ----------

def calc_reserves(S, today):
    """지준(주 평균)·지준/GDP(규칙 카드와 같은 식)·하한 대비·4주 평균과 그래프(최근 52주 지준 · 하한 × 마지막 분기 GDP).
    분모 바뀜 칸은 비워 두고 build가 직전 파일과 견줘 채운다(with_base)."""
    value, wd, gd, g = liq.reserves_gdp(S)
    low = float(rr.TH["reserves_gdp_low"])
    w = S[RES_AVG]
    last4 = w[-4:]
    avg4 = (sum(v for _, v in last4) / 4 / 1000 / g * 100
            if len(last4) == 4 and (last4[-1][0] - last4[0][0]).days == 21 else None)
    floor = low / 100 * g
    pts = w[-CHART_WEEKS:]
    return {"date": _iso(wd),
            "values": {"level": _r(w[-1][1] / 1000), "value": _r6(value), "gdp_quarter": _iso(gd), "gdp_bn": _r(g),
                       "low": low, "gap_pp": _r(value - low), "gap_bn": _r((value - low) / 100 * g),
                       "avg4": _r6(avg4), "avg4_from": _iso(last4[0][0]) if avg4 is not None else None,
                       "base_quarter": None, "base_bn": None, "denom_pp": None,
                       "first_quarter": _iso(gd), "first_bn": _r(g)},
            "lines": {"res": [[_iso(d), round(v / 1000, 1)] for d, v in pts],
                      "low": [[_iso(d), round(floor, 1)] for d, _ in pts]}}


def with_base(core, old):
    """분모 바뀜 — 기준은 직전 주를 처음 실을 때의 GDP(비공개 fed_bs가 메일로 실은 주의 GDP와 견주는 것과 같은 뜻).
    직전 파일의 칸(old core)이 이번보다 이른 주면 그 주의 first(처음 실을 때의 GDP)를, 같은 주면 그 주가 견준 기준과 first를
    그대로 둔다. 기준과 이번 GDP(분기·크기)가 다르면 같은 지준으로 견준 분모 몫 = 지준 ÷ 이번 GDP − 지준 ÷ 기준 GDP(%p).
    first는 이번 주를 처음 실을 때의 GDP다 — 같은 주 안에서 GDP만 바뀌어도(H.4.1이 하루 늦은 주의 GDP 발표 등) 다음 주가 그
    바뀜을 분모 바뀜으로 싣는다."""
    v = dict(core["values"], base_quarter=None, base_bn=None, denom_pp=None,
             first_quarter=core["values"]["gdp_quarter"], first_bn=core["values"]["gdp_bn"])
    base = None
    if old:
        ov = old["values"]
        if core["date"] > old["date"]:
            base = (ov["first_quarter"], ov["first_bn"])
        elif core["date"] == old["date"]:
            v["first_quarter"], v["first_bn"] = ov["first_quarter"], ov["first_bn"]
            if ov.get("base_quarter") and ov.get("base_bn"):
                base = (ov["base_quarter"], ov["base_bn"])
    if base and base[1]:
        v["base_quarter"], v["base_bn"] = base
        if base != (v["gdp_quarter"], v["gdp_bn"]):
            v["denom_pp"] = _r6(v["level"] / v["gdp_bn"] * 100 - v["level"] / base[1] * 100)
    return {**core, "values": v}


def decompose(S, days):
    """여덟 수요일 수준 시리즈가 모두 있는 마지막 수요일과 그 days일 전 이하 마지막 공통 관측(NEAR_DAYS 안) → (출발, 끝,
    {지준: 변화, 몫: 지준 쪽 부호의 변화}) 또는 None. 십억 달러. 그 밖 = 지준 변화 − 나머지 합."""
    common = sorted(set.intersection(*(set(d for d, _ in S[sid]) for sid in BS.values())))
    if not common:
        return None
    d1 = common[-1]
    old = [d for d in common if d <= d1 - TD(days=days)]
    if not old or (d1 - TD(days=days) - old[-1]).days > NEAR_DAYS:
        return None
    d0 = old[-1]
    v = {k: dict(S[sid]) for k, sid in BS.items()}
    ch = {k: (v[k][d1] - v[k][d0]) / 1000 for k in BS}
    parts = {k: SIGN[k] * ch[k] for k in SIGN}
    parts["other"] = ch["res"] - sum(parts.values())
    return d0, d1, {"res": ch["res"], **parts}


def calc_dec(S, today):
    common = sorted(set.intersection(*(set(d for d, _ in S[sid]) for sid in BS.values())))
    if not common:
        raise ItemError("format")
    vals = {"to": _iso(common[-1])}
    any_ok = False
    for w, days in WINDOWS:
        r = decompose(S, days)
        vals[f"from{w}"] = _iso(r[0]) if r else None
        for k in ("res", *PARTS):
            vals[f"{k}{w}"] = _r(r[2][k]) if r else None
        any_ok = any_ok or r is not None
    if not any_ok:
        raise ItemError("format")
    return {"date": vals["to"], "values": vals, "lines": {}}


def _max_with_date(rows):
    d, v = max(rows, key=lambda x: x[1])             # 같은 값이면 이른 날(첫 최대)
    return v, d


def calc_spread(S, today):
    sofr, iorb = S["SOFR"], S["IORB"]
    win = sofr[-MM_DAYS:]
    rows = []
    for d, v in win:
        b = None
        for x in reversed(iorb):                     # 그 날 이하 마지막 IORB
            if x[0] <= d:
                b = x
                break
        if b and (d - b[0]).days <= IORB_GAP:
            rows.append((d, round((v - b[1]) * 100, 6)))
    if not rows:
        raise ItemError("format")
    mx, md = _max_with_date(rows)
    dates = [d for d, _ in sofr]
    return {"date": _iso(win[-1][0]),
            "values": {"from": _iso(win[0][0]), "max_bp": mx + 0.0, "max_date": _iso(md), "max_tag": cal_tag(md, dates),
                       "pos": sum(1 for _, x in rows if x > 0), "n": len(rows), "days": len(win)},
            "lines": {}}


def calc_srf(S, today):
    srf = S["RPONTTLD"]
    win = srf[-MM_DAYS:]
    mx, md = _max_with_date(win)
    return {"date": _iso(win[-1][0]),
            "values": {"from": _iso(win[0][0]), "max_bn": _r(mx), "max_date": _iso(md),
                       "max_tag": cal_tag(md, [d for d, _ in srf])},
            "lines": {}}


def calc_rrp(S, today):
    rrp = S["RRPONTSYD"]
    d, v = rrp[-1]
    return {"date": _iso(d), "values": {"bn": _r(v), "tag": cal_tag(d, [x for x, _ in rrp])}, "lines": {}}


def calc_week(S, today, now=None):
    """그 H.4.1 주(목~수 — 주 평균 지준의 마지막 수요일)가 15일·월말·FOMC 결정일을 품는지와 다음 FOMC 결정일 — now(실행 시각,
    UTC)에 아직 성명(decided_at)이 나오지 않은 첫 회의. now가 없으면 today 0시(UTC)로 본다(그날 회의는 '다음')."""
    wed = S[RES_AVG][-1][0]
    start = wed - TD(days=6)
    days = [start + TD(days=i) for i in range(7)]
    ms = meetings()
    if now is None:
        now = datetime.datetime.combine(today, datetime.time(0), tzinfo=datetime.timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)
    nxt = next(((b, t) for _, b, t in ms if decided_at(b) > now), None)
    return {"date": _iso(wed),
            "values": {"from": _iso(start), "d15": any(d.day == 15 for d in days),
                       "month_end": any((d + TD(days=1)).month != d.month for d in days),
                       "fomc": [_iso(b) for _, b, _ in ms if start <= b <= wed],
                       "next_fomc": _iso(nxt[0]) if nxt else None, "next_tentative": bool(nxt and nxt[1])},
            "lines": {}}


# ---------- 칸 정의 (차례 = 화면 차례) ----------

def _l(key, label, role, series):
    return {"key": key, "label": label, "role": role, "series": series}


def _dec_values():
    out = {"to": "day"}
    for w, _ in WINDOWS:
        out[f"from{w}"] = "day?"
        out.update({f"{k}{w}": "num?" for k in ("res", *PARTS)})
    return out


def _dec_ok(v):
    """창마다 출발 날짜가 있으면 숫자가 모두 있고, 없으면 모두 비었다. 적어도 한 창은 있다."""
    seen = False
    for w, _ in WINDOWS:
        nums = [v[f"{k}{w}"] for k in ("res", *PARTS)]
        if v[f"from{w}"] is None:
            if any(x is not None for x in nums):
                return False
        else:
            if any(x is None for x in nums) or not v[f"from{w}"] < v["to"]:
                return False
            seen = True
    return seen


ITEMS = [
    {"key": "reserves", "title": "지준과 규칙 하한 (주 평균 · 지준/명목GDP)", "series": [RES_AVG, "GDP"],
     "calc": calc_reserves,
     "values": {"level": "num", "value": "num", "gdp_quarter": "day", "gdp_bn": "num", "low": "num", "gap_pp": "num",
                "gap_bn": "num", "avg4": "num?", "avg4_from": "day?", "base_quarter": "day?", "base_bn": "num?",
                "denom_pp": "num?", "first_quarter": "day", "first_bn": "num"},
     "ends": ["gdp_quarter"],
     "chart": {"unit": "bn", "zero": False,
               "note": "최근 52주 · 주 평균 지준(십억 달러) · 회색 선은 규칙 하한 × 마지막 분기 명목 GDP(지난 주들도 지금 GDP로 그은 선)"},
     "lines": [_l("res", "주 평균 지준", "main", [RES_AVG]), _l("low", "규칙 하한 × 마지막 분기 GDP", "ref", [RES_AVG, "GDP"])]},
    {"key": "dec", "title": "지준 변화의 나눔 4주/13주 (수요일 수준)", "series": list(BS.values()), "calc": calc_dec,
     "values": _dec_values(), "check": _dec_ok},
    {"key": "spread", "title": "SOFR − IORB (최근 5영업일)", "series": ["SOFR", "IORB"], "calc": calc_spread,
     "values": {"from": "day", "max_bp": "num", "max_date": "day", "max_tag": "tag", "pos": "int", "n": "int",
                "days": "int"},
     "check": lambda v: 0 <= v["pos"] <= v["n"] <= v["days"] <= MM_DAYS and v["n"] >= 1 and v["from"] <= v["max_date"]},
    {"key": "srf", "title": "상시 레포(SRF) 이용 (최근 5영업일)", "series": ["RPONTTLD"], "calc": calc_srf,
     "values": {"from": "day", "max_bn": "num", "max_date": "day", "max_tag": "tag"},
     "check": lambda v: v["from"] <= v["max_date"]},
    {"key": "rrp", "title": "익일물 역레포 (마지막 값)", "series": ["RRPONTSYD"], "calc": calc_rrp,
     "values": {"bn": "num", "tag": "tag"}},
    {"key": "week", "title": "이 H.4.1 주 (목~수)", "series": [RES_AVG], "calc": calc_week, "now": True,
     "values": {"from": "day", "d15": "bool", "month_end": "bool", "fomc": "days", "next_fomc": "day?",
                "next_tentative": "bool"},
     "check": lambda v: (v["next_fomc"] is not None or not v["next_tentative"]) and all(v["from"] <= x for x in v["fomc"])},
]
BY_KEY = {it["key"]: it for it in ITEMS}

TAGS = ("", "월말", "분기말", "15일")
_KIND = dict(ai._KIND, tag=lambda v: isinstance(v, str) and v in TAGS, bool=lambda v: type(v) is bool,
             days=lambda v: isinstance(v, list) and len(v) <= 3 and all(ai._is_day(x) for x in v) and v == sorted(set(v)))


# ---------- 문구 ----------

def _s(v, nd=0):
    """부호·천 단위 쉼표 — 반올림해 0이면 부호 없이. 없으면 '—'."""
    return liq._s(v, nd)


def _q(day):
    return liq._q(day)


def _tagged(day, tag):
    """일간 날짜 표시 — '2026-10-30 월말'(괄호 안에 쓴다)."""
    return f"{day} {tag}" if tag else day


def _lvl(day):
    """창의 출발·끝 수요일 — '2026-09-30(분기말)'."""
    tag = level_tag(_day(day))
    return f"{day}({tag})" if tag else day


def _span(v, w):
    fr = v[f"from{w}"]
    if fr is None:
        return f"{w}주 —"
    return f"{w}주 {_lvl(fr)}~{_lvl(v['to'])}"


def shown(v, w):
    """창 하나의 보이는 정수 — (지준 변화, {몫: 정수}). 지준과 일곱 몫은 각자 반올림, 그 밖 = 반올림한 지준 − 일곱 몫의 합
    (보이는 숫자끼리 합이 맞게 — 지준·재정 카드 관례). 창이 없으면 (None, {})."""
    if v[f"from{w}"] is None:
        return None, {}
    sh = {k: round(v[f"{k}{w}"]) for k in SIGN}
    res = round(v[f"res{w}"])
    return res, {**sh, "other": res - sum(sh.values())}


def _pair(a, b):
    return f"{_s(a)}/{_s(b)}"


def texts(key, v, date):
    """칸 → (숫자 줄, 덧붙이는 줄 목록). 정해 둔 문구에 숫자만 넣는다(판정 낱말·문턱 표식 없음)."""
    if key == "reserves":
        avg4 = "—" if v["avg4"] is None else f"{v['avg4']:.2f}%"
        line = (f"지준 {v['level']:,.1f}bn (주 평균) = 명목 GDP의 {v['value']:.2f}% ({_q(v['gdp_quarter'])}) · "
                f"규칙 하한 {v['low']:.1f}% 대비 {_s(v['gap_pp'], 2)}%p ≈ {_s(v['gap_bn'], 1)}bn · 4주 평균 {avg4}")
        extra = [f"{date} 주(목~수)의 주 평균 지준(WRESBAL) ÷ 마지막 분기 명목 GDP(계절조정 연율, {_q(v['gdp_quarter'])} "
                 f"{v['gdp_bn']:,.0f}bn)다 — 규칙 카드 '지준과 통화승수'와 같은 식·같은 GDP 분기다. 달러 환산 = (값 − 하한) × "
                 "그 분기 GDP."]
        if v["avg4"] is not None:
            extra.append(f"{AVG4_DEF} — {v['avg4_from']}~{date} 네 주가 이어질 때만 싣는다(각 주를 그 주의 GDP로 나눈 "
                         "평균이 아니다).")
        else:
            extra.append(f"{AVG4_DEF} — 최근 네 주가 이어지지 않아 싣지 않는다.")
        if v["denom_pp"] is not None:
            how = (f"{_q(v['gdp_quarter'])} 개정" if v["base_quarter"] == v["gdp_quarter"]
                   else f"GDP {_q(v['base_quarter'])}에서 {_q(v['gdp_quarter'])}로")
            line += f" · 분모 바뀜 {_s(v['denom_pp'], 2)}%p ({how})"
            extra.append(f"분모 바뀜 = 이번 지준 ÷ 이번 GDP − 같은 지준 ÷ 직전 주를 처음 실을 때의 GDP"
                         f"({_q(v['base_quarter'])} {v['base_bn']:,.0f}bn). 지준이 그대로여도 GDP가 바뀌면 하한까지의 거리가 "
                         "움직인다.")
        return line, extra
    if key == "dec":
        r4, p4 = shown(v, "4")
        r13, p13 = shown(v, "13")
        line = (f"지준 변화 4주/13주 {_pair(r4, r13)}bn = "
                + " · ".join(f"{PART_NAME[k]} {_pair(p4.get(k), p13.get(k))}" for k in PARTS) + f" {SIGN_NOTE}")
        extra = [f"창: {_span(v, '4')} · {_span(v, '13')} — H.4.1 수요일 수준의 차이고, bn은 십억 달러다."]
        starts = [(w, v[f"from{w}"], level_tag(_day(v[f"from{w}"]))) for w, _ in WINDOWS if v[f"from{w}"]]
        marked = [f"{w}주 창은 {t}({d})" for w, d, t in starts if t]
        if marked:
            extra.append(" · ".join(marked) + "에서 출발해, 그날 하루 튄 역레포·재무부 현금·지준이 되돌아온 몫이 그 칸에 "
                         "섞여 있다.")
        extra.append("부호는 지준 쪽이다 — 재무부 현금(TGA)·역레포·현금 통화가 늘면 그만큼 지준이 줄어 −, 연준 보유 단기채·"
                     "이표채·MBS가 늘면 +. '그 밖'은 나머지(대출·상시 레포·기타 부채 등)이고, 보이는 정수끼리 합이 맞게 반올림 "
                     "차를 받는다. 1주 변화는 15일·월말 하루에 크게 흔들려 싣지 않는다.")
        extra.append("13주 칸은 위 지준·재정 카드의 13주 나눔과 같은 규칙으로 낸 값이다 — 그 카드의 역레포는 익일물 + 해외 "
                     "공적 역레포, 그 카드의 '그 밖'은 연준 MBS + 현금 통화 + 이 카드의 '그 밖'이다.")
        return line, extra
    if key == "spread":
        line = (f"SOFR − IORB 최대 {_s(v['max_bp'])}bp ({_tagged(v['max_date'], v['max_tag'])}) · 0보다 큰 날 "
                f"{v['pos']}/{v['n']}일 ({v['from']}~{date})")
        extra = ["SOFR(뉴욕 연은 담보부 익일물 금리)에서 그날 이하 마지막 IORB(연준 지준 부리 금리)를 뺀 bp다 — SOFR의 마지막 "
                 "관측 다섯(영업일). 같은 최대가 여러 날이면 이른 날을 적는다."]
        if v["n"] < v["days"]:
            extra.append(f"IORB 관측이 {IORB_GAP}일보다 먼 날은 비워 {v['days']}일 중 {v['n']}일만 견줬다.")
        return line, extra
    if key == "srf":
        line = f"상시 레포 이용 최대 {v['max_bn']:,.1f}bn ({_tagged(v['max_date'], v['max_tag'])}) · {v['from']}~{date}"
        return line, ["뉴욕 연은 임시 공개시장 운영의 익일물 레포 합계(RPONTTLD — 상시 레포 기구 SRF 이용), 십억 달러다. "
                      "시리즈의 마지막 관측 다섯 가운데 최대이고, 같은 값이면 이른 날을 적는다."]
    if key == "rrp":
        line = f"익일물 역레포 {v['bn']:,.1f}bn ({_tagged(date, v['tag'])})"
        return line, ["뉴욕 연은 익일물 역레포 기구(RRPONTSYD)의 마지막 값, 십억 달러다. 나눔 칸의 익일물 역레포(WLRRAOL)는 "
                      "H.4.1 수요일 수준이라 날짜가 다르다."]
    if key == "week":
        marks = [x for x, on in (("15일", v["d15"]), ("월말", v["month_end"])) if on]
        bits = [("·".join(marks) + " 포함") if marks else "",
                f"FOMC 뒤 첫 H.4.1({', '.join(v['fomc'])} 결정)" if v["fomc"] else ""]
        inside = " · ".join(b for b in bits if b) or "15일·월말·FOMC 없음"
        nxt = (f" · 다음 FOMC {v['next_fomc']}" + ("(잠정)" if v["next_tentative"] else "")) if v["next_fomc"] \
            else " · 다음 FOMC 미기재"
        line = f"이 주({v['from']}~{date}) {inside}{nxt}"
        extra = []
        if v["fomc"]:
            extra.append("FOMC 결정일(수)이 이 주의 마지막 날이라 이 주의 지준·나눔·주 평균은 결정이 시행되기 전 값이다 — "
                         "IORB·역레포 금리·운용 변경은 결정 다음 날(목)부터라 결정의 흔적은 다음 주 숫자에서 본다.")
        if marks:
            extra.append("15일·월말이 든 주는 수요일 수준이 그날 하루의 결제(국채 결제·세금)에 흔들릴 수 있다.")
        extra.append("H.4.1 주는 목요일부터 수요일까지이고, 연준이 다음 날(목) 16:30(미 동부)에 발표한다.")
        return line, extra
    raise KeyError(key)


def citation(sid, retrieved):
    d = datetime.date.fromisoformat(retrieved)
    src, title = SOURCES[sid]
    return (f"{src}, {title} [{sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; "
            f"{rp.FRED_URL.format(sid)}, {ai._MONTHS[d.month - 1]} {d.day}, {d.year}.")


def sources_of(spec, retrieved=None):
    out = []
    for sid in spec["series"]:
        s = {"series": sid, "name": SOURCES[sid][0], "url": rp.FRED_URL.format(sid), "licence": LICENCE[sid]}
        if retrieved:
            s["citation"] = citation(sid, retrieved)
        out.append(s)
    return out


def notices(key, retrieved):
    year = retrieved[:4]
    if key == "spread":
        return [COMPUTED_NOTICE, SPREAD_DERIVED, SPREAD_DERIVED_EN, rp.SOFR_NOTICE, rp.SOFR_DTCC,
                rp.nyfed_attribution(year), rp.NOT_AFFILIATED]
    if key == "srf":
        return [COMPUTED_NOTICE, SRF_DERIVED, SRF_DERIVED_EN, rp.nyfed_attribution(year), rp.NOT_AFFILIATED]
    if key == "rrp":
        return [rp.nyfed_attribution(year), rp.NOT_AFFILIATED]
    if key == "week":
        return [WEEK_NOTICE]
    return [COMPUTED_NOTICE]


def source_note(spec):
    names = list(dict.fromkeys(SOURCES[sid][0] for sid in spec["series"]))
    return "자료: " + " · ".join(names) + " (via FRED) · 하한 선은 macro-regime-check가 이 자료로 계산한 값"


def present(key, core, retrieved):
    spec = BY_KEY[key]
    line, extra = texts(key, core["values"], core["date"])
    out = {"key": key, "name": spec["title"], "date": core["date"], "values": core["values"], "retrieved": retrieved,
           "line": line, "extra": extra, "notices": notices(key, retrieved), "sources": sources_of(spec, retrieved)}
    if spec.get("lines"):
        c = spec["chart"]
        out["chart"] = {"key": f"fedbs_{key}", "title": spec["title"], "unit": c["unit"], "zero": c["zero"],
                        "threshold": None, "note": c["note"], "source_note": source_note(spec), "notices": [],
                        "lines": [{**ln, "derived": False, "points": core["lines"][ln["key"]]} for ln in spec["lines"]]}
    return out


# ---------- 직전 파일 ----------

def values_ok(spec, vals, lines):
    return (isinstance(vals, dict) and set(vals) == set(spec["values"])
            and all(_KIND[t](vals[k]) for k, t in spec["values"].items())
            and (spec.get("check") is None or spec["check"](vals))
            and isinstance(lines, dict) and set(lines) == {ln["key"] for ln in spec.get("lines", ())}
            and all(isinstance(pts, list) and len(pts) <= CHART_WEEKS
                    and all(isinstance(p, list) and len(p) == 2 and ai._is_day(p[0]) and ai._is_num(p[1]) for p in pts)
                    for pts in lines.values()))


def core_of(item, key):
    """직전 파일의 칸 → (core, 받은 날) 또는 None(없거나 꼴이 어긋남 — 이어 실을 값이 없는 것으로 본다)."""
    spec = BY_KEY[key]
    try:
        vals = item["values"]
        lines = {ln["key"]: ln["points"] for ln in item["chart"]["lines"]} if spec.get("lines") else {}
        ok = ai._is_day(item["date"]) and ai._is_day(item["retrieved"]) and values_ok(spec, vals, lines)
        if ok:
            texts(key, vals, item["date"])          # 문구를 다시 만들 수 있어야 한다
    except (KeyError, TypeError, IndexError, AttributeError, ValueError, OverflowError):
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
    if key == "reserves":
        core = with_base(core, old[0] if old else None)
    if not values_ok(BY_KEY[key], core["values"], core["lines"]):
        raise ItemError("format")                   # 새로 계산한 값도 같은 꼴을 넘어야 싣는다
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


def compute(data, errors, today, now=None):
    """칸마다 계산 — now(실행 시각, UTC)는 '다음 FOMC'를 고르는 주 칸만 쓴다(없으면 today 0시)."""
    S = {sid: [(d, v) for d, v in s if d <= today] for sid, s in data.items()}
    out = {}
    for spec in ITEMS:
        miss = [sid for sid in spec["series"] if sid not in S or not S[sid]]
        if miss:
            out[spec["key"]] = ItemError(errors.get(miss[0], "format"))
            continue
        try:
            out[spec["key"]] = spec["calc"](S, today, now) if spec.get("now") else spec["calc"](S, today)
        except ItemError as e:
            out[spec["key"]] = e
        except Exception as e:                  # 계산 쪽 뜻밖의 오류도 그 칸만 실패로
            print(f"[fedbs_fetch] {spec['key']} 계산 오류: {type(e).__name__}", file=sys.stderr)
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
    ap = argparse.ArgumentParser(description="FRED 공개 통계 → 연준 재무상태표 참고 자료(<out>/fedbs.json)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    ap.add_argument("--work", default=DEFAULT_WORK, help="작업 폴더 — 원문 캐시는 <work>/fedbs/ (기본: 저장소의 .work/)")
    ap.add_argument("--offline", action="store_true", help="요청하지 않고 캐시만 읽는다(로컬 확인용)")
    a = ap.parse_args(argv)
    out, work = os.path.abspath(a.out), os.path.abspath(a.work)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    data, errors = load_all(work, a.offline, fred_load, clock, opener=opener)
    data = build(compute(data, errors, now.date(), now), previous(out), now)
    for spec in ITEMS:                          # Actions 로그 — 날짜와 정해 둔 사유만(값은 찍지 않는다)
        it = data["items"][spec["key"]]
        if it["ok"]:
            print(f"[fedbs_fetch] {spec['key']} {it['date']} 기준")
        else:
            kept = f" — 직전 값({it['date']} 기준) 유지" if it["stale"] else ""
            ai.annotate(f"연준 재무상태표 참고 {spec['key']} 받지 못함: {it['error']}{kept}")
    try:
        if differs(out, data):
            write(out, data)
    except OSError as e:
        print(f"[fedbs_fetch] {FILE}를 쓰지 못함: {type(e).__name__}", file=sys.stderr)
        return 1
    return 0 if any(it["ok"] for it in data["items"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
