#!/usr/bin/env python3
"""참고 자료 — 하이퍼스케일러 다섯 곳의 조달·조달 흐름·재무상태 잔액 (2026-10-30 추가, 2026-11-02 칸 둘 더함 — 사용자 결정:
비공개 줄 공개, 'AI 하이퍼스케일러 조달' 1단계 지표).

운영자의 비공개 월간 점검 [신용 긴축] 끝의 '기업별 조달' 줄을 공개한 것이다(비공개 원본 sec_capex.py와 같은 산식 — 코드는
가져오지 않고 여기서 따로 쓴다. 산식을 고치면 양쪽을 같이). 숫자만 싣는 서술이다 — 판정·문턱·단계·점수가 없고, 판정·공개본·
그래프 스크립트는 이 파일(<out>/sec.json)을 읽지 않는다. 신용 긴축 카드(credit_fetch.py)가 funding 칸을 읽어 한 줄로 싣고,
화면(site/credit.js)은 flow·bal 칸을 이 파일에서 바로 읽는다. 칸(ORDER):
  funding   TTM 설비투자/영업현금·FCF·순차입·순주식(아래 '분기 만들기')
  flow      조달 흐름 — 흐름 7칸에서(새 요청 없음): 달력 분기에 맞춘 5사 분기 FCF(최근 5분기)와 연속 감소 분기 수(앞 분기
            대비 — 계절조정 아님), 외부 조달(순) 몫 = 5사 TTM(순차입 + 순주식) / 5사 TTM 설비투자(다섯 회사 모두 있을 때만),
            마지막 분기 자사주 매입 0인 회사 수(그 분기 공시에 줄이 없어 0으로 채운 회사는 '줄 없음' noline으로 따로)와 5사 TTM
            매입 합(1년 전). 순수 함수 flow_calc(회사별 분기 dict, 0 채움) — 비공개 원본과의 짝 테스트가 부른다
  bal       재무상태 잔액 — 시점 사실(start 없음)을 새로 받는다(BAL): 현금·장기 차입(유동 + 비유동)·순현금, 리스부채(운용 + 금융),
            수주잔고(RPO — 공시하는 회사만). 회사마다 마지막 공시일, 1년 전 = 355~375일 앞. 순수 함수 bal_calc(시점 사실 목록)
달력 분기(flow): 분기 끝 날짜 e → (e.year, ceil(e.month/3)), 표기 'YYQn'. 오라클(5월 말 회계연도)은 2·5·8·11월 끝이라 한 달
  앞선 분기를 같은 달력 분기로 센다(문구에 밝힌다). 5사 분기 FCF는 그 달력 분기에 모든 회사가 영업현금·설비투자를 가진 분기만.
  분기 줄의 구분은 쉼표다 — 비공개 원본의 알림은 화살표로 잇지만 이 사이트의 공개 글에는 화살표를 쓰지 않는다(FORBIDDEN_TEXT).

자료: SEC EDGAR XBRL companyconcept(data.sec.gov — 회사·태그마다 작은 JSON, 미국 정부 공개 자료). 마이크로소프트·알파벳·
  아마존·메타·오라클(COMPANIES, CIK·태그는 비공개 원본과 같다 — 2026-10-29 companyfacts에서 확인)의 영업현금·설비투자·금융리스
  원금·장기 차입 발행/상환·주식(전환우선주 포함) 발행·자사주 매입(흐름 37개 — 메타 차입 상환 대체 태그 둘은 2026-11-02 더함), 그리고
  잔액 태그(BAL — 2026-11-02 탐침으로 확인, 31개). 런마다 68개를 모두 받는다(원 응답은 디스크에 쓰지 않고, 이 파일엔 분기 표와 합계만 남긴다). 출처 표기: 'Source: SEC
  EDGAR XBRL API (data.sec.gov); site calculations' — SEC 로고·인장은 쓰지 않는다.
연락처: SEC 공정 접근 정책은 요청 머리글 User-Agent에 연락처를 싣게 한다. 그 값은 환경 변수 SEC_USER_AGENT(GitHub Actions
  비밀)에서만 읽는다 — 코드·문서·자료 파일·로그·오류 문구 어디에도 쓰지 않는다(오류는 정해 둔 사유 코드로만 남는다). 변수가
  없거나 비었으면 요청을 하나도 하지 않고 세 칸 모두 '연락처 미설정(SEC_USER_AGENT)'으로 둔다(직전 값이 있으면 그것을 받지 못함으로).
  요청은 https sec.gov 주소에만 만들고, https sec.gov 밖으로 옮기는 응답은 따라가지 않는다(머리글이 따라가지 않게). 주소는
  urllib이 실제로 붙는 호스트(Request.host)로 본다 — 사용자 정보('@')·역슬래시·443 밖 포트가 든 주소는 거절.
  쓰기·로그 직전에 한 번 더: 연락처 조각(값 전체·이메일 꼴의 앞·뒤 부분)이나 이메일 꼴 낱말이 칸의 글에 섞였으면 그 칸을 쓰지
  않고 '연락처 꼴 글이 섞여 쓰지 않음'으로(직전 값에도 섞였으면 직전 값 없이), 로그 줄은 정해 둔 문구로 바꾼다.
  한 번에 하나씩, 요청 사이 GAP초(초당 4회 아래 — SEC 상한 10회), 수신 전체 BUDGET초(읽는 동안에도 본다) — 흐름 태그 먼저,
  그다음 잔액 태그.
분기 만들기(회사마다 회계연도대로 — MSFT 6월 말, ORCL 5월 말, 나머지 12월 말):
  - 10-Q·10-K의 기간 사실만(8-K 등 제외). 같은 (시작, 끝)은 늦게 낸 공시가 이긴다(정정 공시·다음 해 비교 수치).
  - 현금흐름표는 누적(YTD)이라 같은 시작일의 앞 누적을 뺀다: 2분기 = 6개월 − 3개월, 4분기 = 연간 − 9개월. 3개월 사실은 그대로.
  - 영업현금·설비투자는 필수. 나머지는 그 분기에 줄이 없거나 쓰지 않는 태그(404)면 0으로 채운다(영업현금이 공시된 분기만).
  - TTM = 마지막 4분기, 분기 끝 사이가 80~100일로 이어질 때만. 1년 전 TTM = 그 앞 4분기, 지금 창에 바로 이어질 때만.
  - 5사 합은 TTM을 낸 회사끼리, 칸 하나라도 모르는 회사가 있으면 그 칸 합은 비운다. 1년 전 FCF 합은 그 회사들 모두에 1년 전
    TTM이 있을 때만. '영업현금 초과'는 설비투자/영업현금 > 100%(정확히 100%는 아니다).
잔액 만들기(bal):
  - 10-Q·10-K의 시점 사실(USD)만. 같은 날짜의 사실이 여럿이면 늦게 낸 것(같은 날이면 앞에 적은 태그).
  - 칸마다 줄 묶음 — 첫 줄은 필수, 뒤 줄은 그 날짜에 없으면 0으로 채우고 채운 수를 회사별 줄에 적는다. 태그를 받지 못했으면
    0이 아니라 모름.
  - 회사의 잔액 날짜 = 현금·장기 차입이 모두 있는 마지막 날짜. 1년 전 = 그 날짜보다 355~375일 앞인 날짜 가운데 둘이 모두
    있는 것(365일에 가장 가까운 것). 리스부채·수주잔고는 잔액 날짜 이하의 마지막 날짜(다르면 회사 옆에 그 달).
  - 5사 합은 잔액을 낸 회사끼리(n/5사), 1년 전 합은 다섯 회사 모두 1년 전이 있을 때만. 리스부채 합은 잔액을 낸 회사가 모두
    알 때만, 수주잔고 합은 공시하는 회사가 모두 있을 때만.

실패: 칸마다 따로 — funding·flow는 흐름 태그 37개 가운데 하나라도, bal은 잔액 태그 31개 가운데 하나라도 받지 못하면(연결
실패·시간 초과·SEC 거절·깨진 응답·시간 상한) 그 칸의 이번 숫자를 쓰지 않고 직전 파일의 숫자를 '받지 못함(stale)'과 그날부터라는
날짜와 함께 이어 싣는다(직전 값이 없으면 사유만). 흐름 태그가 하나 실패해도 잔액 태그는 받는다 — 다만 SEC가 거절했으면(요청
한도·미신고 도구) 거기서 모두 멈춘다. 응답의 꼴이 뜻밖이면(units.USD가 목록이 아님 등) 그 묶음만 '계산할 자료가
모자람'(예외를 밖으로 내보내지 않는다). 문구는 이 파일에 정해 둔 것뿐이다. 같은 내용이면 다시 쓰지 않는다.

종료코드: 0 한 칸이라도 이번에 받음 / 1 하나도 못 받음(연락처 미설정·연락처 꼴 글이 섞임 포함, 또는 파일을 쓰지 못함).
워크플로 단계는 continue-on-error, 알림 없음.

사용법: SEC_USER_AGENT="<이름> <연락처>" python scripts/sec_fetch.py [--out data]
"""
import os, sys, re, json, gzip, time, argparse, datetime, urllib.parse, urllib.request, urllib.error

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import ai_invest_fetch as ai                  # 쓰기·날짜 검사·경고 주석을 그대로 쓴다

SCHEMA = 1
REPO = os.path.dirname(SCRIPTS)
DEFAULT_OUT = os.path.join(REPO, "data")
FILE = "sec.json"
ENV = "SEC_USER_AGENT"
HOSTS = ("data.sec.gov", "www.sec.gov", "sec.gov")
URL = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{tag}.json"
DOC_URL = "https://www.sec.gov/edgar/sec-api-documentation"

BUDGET = 60                                   # 수신 전체(초) — 워크플로 단계 제한(2분) 안에서
TIMEOUT = 10                                  # 요청 하나엔 min(이것, 남은 예산)
GAP = 0.25                                    # 요청 사이(초) — 초당 4회 아래
MAX_BYTES = 8 * 1024 * 1024
KEEP_DAYS = 5 * 366                           # 끝이 이 안인 사실만(8분기 + 누적 빼기 여유)
Q_MIN, Q_MAX = 80, 100                        # 분기 길이(일)
ROWS = 9                                      # 회사마다 분기 표에 남기는 마지막 분기 수
UA_MAX = 200

OCF = "NetCashProvidedByUsedInOperatingActivities"
PPE = "PaymentsToAcquirePropertyPlantAndEquipment"
FLPP = "FinanceLeasePrincipalPayments"
EQ = "ProceedsFromIssuanceOfCommonStock"
CVPREF = "ProceedsFromIssuanceOfConvertiblePreferredStock"
BUYBACK = "PaymentsForRepurchaseOfCommonStock"
PFILTD = "ProceedsFromIssuanceOfLongTermDebt"
REQUIRED = ("ocf", "capex")
ITEMS = ("ocf", "capex", "flease", "debt_iss", "debt_rep", "eq_iss", "buyback")
OPTIONAL = tuple(i for i in ITEMS if i not in REQUIRED)
ITEM_NAME = {"ocf": "영업현금", "capex": "설비투자", "flease": "금융리스 원금", "debt_iss": "차입 발행",
             "debt_rep": "차입 상환", "eq_iss": "주식 발행", "buyback": "자사주 매입"}
# (키, 표시, CIK, 회계연도 끝 달, {칸: [[대체 태그…], …(더하는 부분)]}) — 비공개 원본과 같다. 빈 칸 = 쓰지 않는 줄(0)
COMPANIES = [
    ("MSFT", "마이크로소프트", "0000789019", 6, {
        "ocf": [[OCF]], "capex": [[PPE]], "flease": [[FLPP]],
        "debt_iss": [["ProceedsFromDebtMaturingInMoreThanThreeMonths"]],
        "debt_rep": [["RepaymentsOfDebtMaturingInMoreThanThreeMonths"]],
        "eq_iss": [[EQ]], "buyback": [[BUYBACK]]}),
    ("GOOGL", "알파벳", "0001652044", 12, {
        "ocf": [[OCF]], "capex": [[PPE]], "flease": [[FLPP]],
        "debt_iss": [["ProceedsFromDebtNetOfIssuanceCosts"]],
        "debt_rep": [["RepaymentsOfDebtAndCapitalLeaseObligations"]],
        "eq_iss": [[EQ], [CVPREF]], "buyback": [[BUYBACK]]}),
    ("AMZN", "아마존", "0001018724", 12, {
        "ocf": [[OCF]], "capex": [["PaymentsToAcquireProductiveAssets"]], "flease": [[FLPP]],
        "debt_iss": [[PFILTD]], "debt_rep": [["RepaymentsOfLongTermDebt"]],
        "eq_iss": [], "buyback": [[BUYBACK]]}),
    ("META", "메타", "0001326801", 12, {                  # 차입 상환: 2026-11-02 확인 — 상환 공시 없음(→ 0). 1년 안 만기 장기
        "ocf": [[OCF]], "capex": [[PPE]], "flease": [[FLPP]],  # 차입이 생겨 상환이 공시되면 어느 태그로 내든 잡히게
        "debt_iss": [[PFILTD]], "debt_rep": [["RepaymentsOfLongTermDebt", "RepaymentsOfSeniorDebt"]],
        "eq_iss": [], "buyback": [[BUYBACK]]}),
    ("ORCL", "오라클", "0001341439", 5, {
        "ocf": [[OCF]], "capex": [[PPE]], "flease": [[FLPP]],
        "debt_iss": [["ProceedsFromIssuanceOfSeniorLongTermDebt", PFILTD]],
        "debt_rep": [["RepaymentsOfDebt"]],
        "eq_iss": [[EQ], [CVPREF]], "buyback": [[BUYBACK]]}),
]

# 재무상태 잔액(bal) — 시점 사실 태그(2026-11-02 탐침으로 확인, 비공개 원본과 같다). {칸: [[대체 태그…], …(더하는 줄)]} —
# 첫 줄은 필수, 뒤 줄은 그 날짜에 없으면 0. 빈 칸 = 쓰지 않는다(아마존·메타의 RPO 태그는 2020년에 멈춰 쓰지 않는다)
CASH_STI = "CashCashEquivalentsAndShortTermInvestments"
CASH = "CashAndCashEquivalentsAtCarryingValue"
MSEC = "MarketableSecuritiesCurrent"
AFS_CUR = "AvailableForSaleSecuritiesDebtSecuritiesCurrent"
LTD_NC, LTD_C = "LongTermDebtNoncurrent", "LongTermDebtCurrent"
NOTES_LT, NOTES_C = "LongTermNotesAndLoans", "NotesPayableCurrent"
OP_LEASE, FIN_LEASE = "OperatingLeaseLiability", "FinanceLeaseLiability"
RPO = "RevenueRemainingPerformanceObligation"
BAL_FIELDS = ("cash", "debt", "lease", "rpo")
BAL_NAME = {"cash": "현금", "debt": "장기 차입", "lease": "리스부채", "rpo": "수주잔고"}
BAL = {
    "MSFT": {"cash": [[CASH_STI]], "debt": [[LTD_NC], [LTD_C]], "lease": [[OP_LEASE], [FIN_LEASE]], "rpo": [[RPO]]},
    "GOOGL": {"cash": [[CASH_STI]], "debt": [[LTD_NC], [LTD_C]], "lease": [[OP_LEASE], [FIN_LEASE]], "rpo": [[RPO]]},
    "AMZN": {"cash": [[CASH], [MSEC]], "debt": [[LTD_NC], [LTD_C]], "lease": [[OP_LEASE], [FIN_LEASE]], "rpo": []},
    "META": {"cash": [[CASH], [MSEC]], "debt": [[LTD_NC], [LTD_C]], "lease": [[OP_LEASE], [FIN_LEASE]], "rpo": []},
    "ORCL": {"cash": [[CASH], [AFS_CUR]], "debt": [[NOTES_LT], [NOTES_C]], "lease": [[OP_LEASE], [FIN_LEASE]], "rpo": [[RPO]]},
}
YEAR_MIN, YEAR_MAX = 355, 375                 # 잔액 1년 전(일)
FLOW_SHOW, FLOW_HIST = 5, 8                   # 조달 흐름 — 싣는 달력 분기 수 · 연속 감소를 세는 이력

ORDER = ["funding", "flow", "bal"]
TITLE = "하이퍼스케일러 다섯 곳의 조달 (SEC 공시)"
FLOW_TITLE = "하이퍼스케일러 다섯 곳의 조달 흐름 (SEC 공시, 달력 분기)"
BAL_TITLE = "하이퍼스케일러 다섯 곳의 재무상태 잔액 (SEC 공시, 분기 말)"
NOTICE = ("이 사이트의 규칙 점검에 쓰지 않는 참고 자료다. 공시 숫자를 분기로 나누거나 잔액을 더한 산술이고, 단계·점수가 "
          "없으며 금리를 예측하지 않는다.")
COMPUTED_NOTICE = "분기·TTM·달력 분기 합·잔액 합계·비율은 macro-regime-check가 SEC EDGAR XBRL 공시로 계산한 값이다."
SOURCE_LINE = "Source: SEC EDGAR XBRL API (data.sec.gov); site calculations"
REASONS = {                                   # 페이지·파일에 나가는 실패 문구는 이것뿐
    "no_ua": "연락처 미설정(SEC_USER_AGENT)",
    "fetch": "수신 실패",
    "blocked": "SEC 거절 · 요청 한도 또는 미신고 도구",
    "budget": "시간 상한 안에 다 받지 못함",
    "format": "계산할 자료가 모자람",
    "older": "받은 자료가 직전 자료보다 오래됨",
    "leak": "연락처 꼴 글이 섞여 쓰지 않음",
}
COMPANY_REASONS = {"no_ocf": "영업현금 자료 없음", "no_capex": "설비투자 자료 없음",
                   "not_consecutive": "4분기 연속 아님", "calc": "계산 오류",
                   "no_q": "분기 자료 없음", "no_bal": "잔액 자료 없음"}


class ItemError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class FetchError(ItemError):
    """요청 하나의 실패 — code는 REASONS의 키(fetch·blocked·budget·format)."""


# ---------- 연락처 ----------

def user_agent(env=None):
    """SEC_USER_AGENT — 앞뒤 공백을 뺀 값. 없거나 비었거나 제어 문자가 섞였거나 너무 길면 None(요청하지 않는다)."""
    ua = str((os.environ if env is None else env).get(ENV) or "").strip()
    if not ua or len(ua) > UA_MAX or any(ord(ch) < 32 or ord(ch) == 127 for ch in ua):
        return None
    return ua


_EMAIL = re.compile(r"[^\s@<>()\"']+@[^\s@<>()\"']+")


def scrub(s, ua=None):
    """글에서 연락처를 가린다 — User-Agent 값과 '@'가 든 낱말. 로그에 예외 이름 밖을 찍을 일이 생겨도 이것을 거친다."""
    s = str(s)
    if ua:
        s = s.replace(ua, "<UA>")
    return _EMAIL.sub("<연락처>", s)


BIT_MIN = 4                                   # 이보다 짧은 조각은 보지 않는다(흔한 글자와 겹쳐 늘 거절하지 않게)


def contact_bits(ua):
    """글에 섞이면 안 되는 연락처 조각 — 값 전체, 이메일 꼴 낱말과 그 앞(로컬)·뒤(도메인) 부분. BIT_MIN자 미만은 뺀다."""
    if not ua:
        return []
    bits = {ua}
    for m in _EMAIL.finditer(ua):
        local, _, domain = m.group(0).partition("@")
        bits |= {m.group(0), local, domain}
    return sorted((b for b in bits if len(b) >= BIT_MIN), key=len, reverse=True)


def leaks(text, ua=None):
    """글에 연락처 조각(대소문자 무시)이나 이메일 꼴 낱말이 있는가 — 쓰기·찍기 직전에 한 번 더 본다(이중 안전)."""
    t = str(text)
    low = t.casefold()
    return _EMAIL.search(t) is not None or any(b.casefold() in low for b in contact_bits(ua))


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(k)
            yield from _strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _strings(v)


def data_leaks(data, ua=None):
    """산출물(dict)에 연락처가 섞였는가 — 쓸 글(JSON)과 그 안의 문자열 하나하나를 함께 본다(JSON 이스케이프로 갈라져도)."""
    return leaks(dump(data), ua) or any(leaks(s, ua) for s in _strings(data))


SAY_LEAK = "[sec_fetch] 로그 줄에 연락처 꼴 글이 섞여 찍지 않음"


def say(msg, ua=None, warn=False, err=False):
    """Actions 로그 한 줄 — 연락처 조각이 섞였으면 정해 둔 문구로 바꿔 찍는다."""
    if leaks(msg, ua):
        msg = SAY_LEAK
    if warn:
        ai.annotate(msg)
    else:
        print(msg, file=sys.stderr if err else sys.stdout)


# ---------- 요청 ----------

_HOST = re.compile(r"([a-z0-9-]+(?:\.[a-z0-9-]+)*)(?::443)?")


def _sec_https(url):
    """https sec.gov 주소인가 — urllib이 실제로 붙는 곳(Request.host)으로 본다. 사용자 정보 앞에 역슬래시를 넣은 주소
    (https://<다른 호스트><역슬래시><골뱅이>www.sec.gov/)를 urlsplit().hostname은 www.sec.gov로 읽지만 urllib은 다른 곳에 붙는다.
    그래서 모두 맞아야 참: scheme https · Request.host(소문자, 포트는 없거나 443)가 HOSTS · urlsplit도 같은 호스트 ·
    netloc에 '@'·역슬래시 없음 · 주소에 공백·제어 문자 없음. 비공개 원본 sec_capex._sec_https와 같다."""
    if not isinstance(url, str) or any(ord(ch) <= 32 or ord(ch) == 127 for ch in url):
        return False
    try:
        p = urllib.parse.urlsplit(url)
        req = urllib.request.Request(url)
        port = p.port
    except (ValueError, TypeError):
        return False
    if p.scheme != "https" or req.type != "https" or "@" in p.netloc or "\\" in p.netloc:
        return False
    m = _HOST.fullmatch((req.host or "").lower())
    return bool(m) and m.group(1) in HOSTS and (p.hostname or "") == m.group(1) and port in (None, 443)


def sec_request(url, ua):
    """User-Agent(연락처)를 단 요청 — https sec.gov 주소에만 만든다(그 밖은 ValueError)."""
    if not _sec_https(url):
        raise ValueError("SEC https 주소가 아니다 — 연락처를 싣지 않는다")
    return urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Encoding": "gzip"})


class SecOnlyRedirect(urllib.request.HTTPRedirectHandler):
    """https sec.gov 밖으로 옮기는 응답은 따라가지 않는다(머리글이 따라가지 않게 — http로 옮겨도 평문이라 거절)."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _sec_https(newurl):
            raise urllib.error.HTTPError(newurl, code, "SEC https 밖으로 옮김 — 따라가지 않음", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _default_opener():
    return urllib.request.build_opener(SecOnlyRedirect()).open


def fetch(cik, tag, ua, deadline, clock=time.monotonic, opener=None):
    """태그 하나 → companyconcept JSON(dict), 그 회사가 쓰지 않는 태그면 None(404). 그 밖은 FetchError(사유 코드만 —
    예외 원문은 버린다). 남은 시간을 타임아웃으로 주고, 읽는 동안에도 마감을 본다(ai_invest_fetch.fetch_csv와 같게)."""
    left = deadline - clock()
    if left <= 1:
        raise FetchError("budget")
    opener = opener or _default_opener()
    try:
        r = opener(sec_request(URL.format(cik=cik, tag=tag), ua), timeout=min(TIMEOUT, left))
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read(4096) or b""
            e.close()
        except Exception:
            pass
        if e.code == 404:
            return None
        if e.code == 429 or (e.code == 403 and (b"Undeclared" in body or b"Rate Threshold" in body)):
            raise FetchError("blocked")
        raise FetchError("fetch")
    except Exception:
        raise FetchError("fetch")
    chunks, size = [], 0
    try:
        with r:
            read = getattr(r, "read1", None) or r.read
            while True:
                if clock() > deadline:
                    raise FetchError("budget")
                chunk = read(65536)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    raise FetchError("format")
                chunks.append(chunk)
            hd = getattr(r, "headers", None)
            enc = (hd.get("Content-Encoding") or "") if hd is not None else ""
    except FetchError:
        raise
    except Exception:
        raise FetchError("fetch")
    blob = b"".join(chunks)
    try:
        if enc == "gzip" or blob[:2] == b"\x1f\x8b":
            blob = gzip.decompress(blob)
        js = json.loads(blob.decode("utf-8"))
    except (ValueError, OSError, EOFError):
        raise FetchError("format")
    if not isinstance(js, dict) or not isinstance(js.get("units"), dict):
        raise FetchError("format")
    if not isinstance(js["units"].get("USD", []), list):       # 깨진 꼴은 그 묶음만 실패(trim이 넘어지지 않게)
        raise FetchError("format")
    return js


def trim(js, today):
    """companyconcept → [[시작, 끝, 값, 낸 날, 양식]] — USD 기간 사실, 10-Q·10-K만, 끝이 KEEP_DAYS 안인 것."""
    lo = (today - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    out = []
    for x in (js.get("units") or {}).get("USD") or []:
        try:
            s, e, v, f, form = x.get("start"), x["end"], x["val"], x["filed"], str(x.get("form") or "")
        except (KeyError, TypeError, AttributeError):
            continue
        if not s or not form.startswith("10-") or not isinstance(e, str) or e < lo or isinstance(v, bool) \
                or not isinstance(v, (int, float)):
            continue
        out.append([s, e, v, f, form])
    return sorted(out)


_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")


def trim_instant(js, today):
    """companyconcept → [[끝, 값, 낸 날, 양식]] — USD 시점 사실(start 없음), 10-Q·10-K만, 끝이 KEEP_DAYS 안이고 오늘을
    넘지 않는 것, 유한한 수만(잔액 태그)."""
    lo, hi = (today - datetime.timedelta(days=KEEP_DAYS)).isoformat(), today.isoformat()
    out = []
    for x in (js.get("units") or {}).get("USD") or []:
        try:
            s, e, v, f, form = x.get("start"), x["end"], x["val"], x["filed"], str(x.get("form") or "")
        except (KeyError, TypeError, AttributeError):
            continue
        if s or not form.startswith("10-") or not isinstance(e, str) or not _DAY.fullmatch(e) or not lo <= e <= hi \
                or not isinstance(f, str) or not _DAY.fullmatch(f) or isinstance(v, bool) \
                or not isinstance(v, (int, float)) or v != v or abs(v) == float("inf"):
            continue
        out.append([e, v, f, form])
    return sorted(out)


def tags_of(company):
    seen = []
    for parts in company[4].values():
        for alts in parts:
            for t in alts:
                if t not in seen:
                    seen.append(t)
    return seen


def bal_tags_of(key):
    """잔액 태그 — BAL[key]의 칸 차례(겹치는 태그는 한 번). BAL에 없는 회사는 빈 목록."""
    seen = []
    for f in BAL_FIELDS:
        for alts in (BAL.get(key) or {}).get(f) or []:
            for t in alts:
                if t not in seen:
                    seen.append(t)
    return seen


def flow_plan():
    """흐름 태그 [(CIK, 태그)] — 회사 차례."""
    return [(c[2], t) for c in COMPANIES for t in tags_of(c)]


def bal_plan():
    """잔액 태그 [(CIK, 태그)] — 회사 차례."""
    return [(c[2], t) for c in COMPANIES for t in bal_tags_of(c[0])]


def _fetch_plan(plan, ua, today, deadline, keep, pace, opener, clock, sleep):
    """(got {CIK: {태그: 사실 목록([] = 404)}}, 실패 코드 또는 None, 요청 수). 하나라도 실패하면 거기서 멈춘다.
    pace = [앞 요청 시각] — 묶음(흐름 → 잔액) 사이에도 간격을 지킨다."""
    got, n = {}, 0
    for cik, tag in plan:
        if pace[0] is not None:
            wait = GAP - (clock() - pace[0])
            if wait > 0:
                sleep(wait)
        if deadline - clock() <= 1:
            return got, "budget", n
        pace[0] = clock()
        n += 1
        try:
            js = fetch(cik, tag, ua, deadline, clock, opener)
        except FetchError as e:
            return got, e.code, n
        try:
            facts = keep(js, today) if js else []
        except Exception:                                      # 뜻밖의 꼴 — 그 묶음만 정해 둔 사유로 실패(다른 묶음·칸은 그대로)
            return got, "format", n
        got.setdefault(cik, {})[tag] = facts
    return got, None, n


def fetch_all(ua, today, budget=BUDGET, opener=None, clock=time.monotonic, sleep=time.sleep):
    """흐름 태그만 — (got, 실패 코드 또는 None, 요청 수). 연락처가 없으면 요청 0번. 하나라도 실패하면 거기서 멈춘다."""
    if not ua:
        return {}, "no_ua", 0
    return _fetch_plan(flow_plan(), ua, today, clock() + budget, trim, [None], opener, clock, sleep)


def fetch_both(ua, today, budget=BUDGET, opener=None, clock=time.monotonic, sleep=time.sleep):
    """흐름 태그 먼저, 그다음 잔액 태그 — 한 예산(budget초) 안에서. → {got, code, bgot, bcode, n, nb}(code·bcode = 실패 코드
    또는 None, n·nb = 요청 수). 잔액은 흐름과 따로 실패한다(흐름 태그 하나가 실패해도 잔액 태그는 받는다). 다만 SEC가
    거절했으면(blocked) 거기서 모두 멈춘다. 연락처가 없으면 요청 0번."""
    if not ua:
        return {"got": {}, "code": "no_ua", "bgot": {}, "bcode": "no_ua", "n": 0, "nb": 0}
    deadline, pace = clock() + budget, [None]
    got, code, n = _fetch_plan(flow_plan(), ua, today, deadline, trim, pace, opener, clock, sleep)
    if code == "blocked":
        return {"got": got, "code": code, "bgot": {}, "bcode": "blocked", "n": n, "nb": 0}
    bgot, bcode, nb = _fetch_plan(bal_plan(), ua, today, deadline, trim_instant, pace, opener, clock, sleep)
    return {"got": got, "code": code, "bgot": bgot, "bcode": bcode, "n": n, "nb": nb}


# ---------- 분기 (비공개 원본 sec_capex와 같은 산식) ----------

def _d(s):
    return datetime.date.fromisoformat(s)


def _days(a, b):
    return (_d(b) - _d(a)).days


def merged(facts_lists):
    """[(태그, [[시작, 끝, 값, 낸 날, 양식]…])…] → {(시작, 끝): (값, 낸 날, 태그)} — 같은 기간은 늦게 낸 것(같은 날이면 앞 태그)."""
    best = {}
    for tag, facts in facts_lists:
        for s, e, v, f, _form in facts:
            k = (s, e)
            if k not in best or f > best[k][1]:
                best[k] = (v, f, tag)
    return best


def ref_quarter_ends(ref):
    """영업현금 기간 집합에서 분기 끝 — 3개월 사실이거나 같은 시작의 앞 누적이 있는 누적 사실의 끝."""
    ends = set()
    for (s, e) in ref:
        if Q_MIN <= _days(s, e) <= Q_MAX or any(s2 == s and Q_MIN <= _days(e2, e) <= Q_MAX for (s2, e2) in ref):
            ends.add(e)
    return ends


def quarters(best, ref=None, optional=False):
    """{분기 끝: (값, 태그)}와 0으로 채운 분기 끝 집합. 3개월 사실 그대로 · 누적은 같은 시작의 앞 누적(끝이 80~100일 앞)을
    뺀다 · optional이면 앞 누적이 없고 영업현금엔 있을 때 앞을 0으로, 영업현금 분기에 값이 없으면 0으로 채운다."""
    q, filled = {}, set()
    for (s, e), (v, _f, tag) in best.items():
        if Q_MIN <= _days(s, e) <= Q_MAX:
            q[e] = (v, tag)
    for (s, e), (v, _f, tag) in sorted(best.items()):
        if _days(s, e) <= Q_MAX or e in q:
            continue
        prev = [(s2, e2) for (s2, e2) in best if s2 == s and Q_MIN <= _days(e2, e) <= Q_MAX]
        if prev:
            q[e] = (v - best[prev[0]][0], tag)
        elif optional and ref and any(s2 == s and Q_MIN <= _days(e2, e) <= Q_MAX for (s2, e2) in ref):
            q[e] = (v, tag)                                  # 앞 누적 공시에 이 줄이 없었다 — 앞 = 0
    if optional and ref:
        for e in ref_quarter_ends(ref):
            if e not in q:
                q[e] = (0, None)
                filled.add(e)
    return q, filled


def consecutive(ends):
    return all(Q_MIN <= _days(a, b) <= Q_MAX for a, b in zip(ends, ends[1:]))


def company_quarters(got_c, company):
    """회사 하나(got_c = {태그: 사실 목록}) → {ok, ends, items: {칸: {끝: 값}}, tags, filled, missing}."""
    _key, _lab, _cik, _fy, spec = company
    missing = [t for t in tags_of(company) if t not in got_c]
    ocf_best = merged([(t, got_c[t]) for t in spec["ocf"][0] if t in got_c])
    if not ocf_best:
        return {"ok": False, "reason": "no_ocf", "missing": missing}
    ref = set(ocf_best)
    items, tags, filled = {}, {}, {}
    for item in ITEMS:
        parts = spec.get(item) or []
        optional = item not in REQUIRED
        if not parts:                                         # 쓰지 않는 줄 — 영업현금 분기마다 0
            ends = ref_quarter_ends(ref)
            items[item], tags[item], filled[item] = {e: 0 for e in ends}, {}, set(ends)
            continue
        acc, tg, fl, ok = None, {}, set(), True
        for alts in parts:
            avail = [(t, got_c[t]) for t in alts if t in got_c]
            if not avail:                                     # 받지 않은 태그 — 0으로 채우지 않는다(모름)
                ok = False
                break
            q, f = quarters(merged(avail), ref, optional)
            fl |= f
            vals = {e: v for e, (v, _t) in q.items()}
            for e, (_v, t) in q.items():
                if t and e not in tg:
                    tg[e] = t
            acc = vals if acc is None else {e: acc[e] + vals[e] for e in acc if e in vals}
        if ok and acc is not None:
            items[item], tags[item] = acc, tg
            filled[item] = {e for e in fl if e in acc}
    if any(r not in items for r in REQUIRED):
        return {"ok": False, "reason": "no_capex", "missing": missing}
    ends = sorted(set(items["ocf"]) & set(items["capex"]))
    return {"ok": True, "ends": ends, "items": items, "tags": tags, "filled": filled, "missing": missing}


def _bn(v):
    return None if v is None else round(v / 1e9, 3) + 0.0


def _sum(cq, item, ends):
    vals = cq["items"].get(item)
    if vals is None or any(e not in vals for e in ends):
        return None
    return sum(vals[e] for e in ends)


def _ttm(cq, ends):
    t = {item: _sum(cq, item, ends) for item in ITEMS}
    o, c = t["ocf"], t["capex"]
    fcf = None if o is None or c is None else o - c
    out = {k: _bn(v) for k, v in t.items()}
    out.update({"fcf": _bn(fcf), "ratio": None if not o or c is None else round(c / o * 100, 1) + 0.0,
                "fcf_l": _bn(None if fcf is None or t["flease"] is None else fcf - t["flease"]),
                "debt_net": _bn(None if t["debt_iss"] is None or t["debt_rep"] is None else t["debt_iss"] - t["debt_rep"]),
                "eq_net": _bn(None if t["eq_iss"] is None or t["buyback"] is None else t["eq_iss"] - t["buyback"]),
                "from": ends[0], "to": ends[-1]})
    return out


def company_summary(got, company):
    """회사 하나의 요약 — {key, ok, last_q, ttm, ttm_prev, last_fcf, tags, filled, rows} 또는 {key, ok: False, reason, last_q}."""
    key, _lab, cik, _fy, _spec = company
    try:
        cq = company_quarters(got.get(cik) or {}, company)
    except Exception:
        return {"key": key, "ok": False, "reason": "calc", "last_q": None}
    if not cq["ok"]:
        return {"key": key, "ok": False, "reason": cq["reason"], "last_q": None}
    ends = cq["ends"]
    last4, prev4 = ends[-4:], ends[-8:-4]
    if len(last4) < 4 or not consecutive(last4):
        return {"key": key, "ok": False, "reason": "not_consecutive", "last_q": ends[-1] if ends else None}
    out = {"key": key, "ok": True, "last_q": ends[-1], "ttm": _ttm(cq, last4), "ttm_prev": None}
    if len(prev4) == 4 and consecutive(prev4 + [last4[0]]):
        p = _ttm(cq, prev4)
        out["ttm_prev"] = {"ratio": p["ratio"], "fcf": p["fcf"], "capex": p["capex"], "debt_net": p["debt_net"],
                           "eq_net": p["eq_net"], "buyback": p["buyback"], "from": p["from"], "to": p["to"]}
    e = ends[-1]
    o, c = cq["items"]["ocf"].get(e), cq["items"]["capex"].get(e)
    out["last_fcf"] = _bn(None if o is None or c is None else o - c)
    out["tags"] = {item: (cq["tags"].get(item) or {}).get(e) for item in ITEMS if item in cq["items"]}
    out["filled"] = {item: sum(1 for x in last4 if x in cq["filled"].get(item, set()))
                     for item in OPTIONAL if item in cq["items"]}
    out["rows"] = [{"q": x, **{item: _bn((cq["items"].get(item) or {}).get(x)) for item in ITEMS}} for x in ends[-ROWS:]]
    return out


TOTAL_FIELDS = ("ocf", "capex", "fcf", "fcf_l", "debt_iss", "debt_net", "eq_net")


def summary(got):
    """받은 것 → {total, companies} (JSON 꼴 values). TTM을 낸 회사가 없으면 ItemError('format')."""
    comps = [company_summary(got, c) for c in COMPANIES]
    ok = [c for c in comps if c["ok"]]
    if not ok:
        raise ItemError("format")
    s = {f: sum(c["ttm"][f] for c in ok if c["ttm"][f] is not None) for f in TOTAL_FIELDS}
    full = {f: all(c["ttm"][f] is not None for c in ok) for f in TOTAL_FIELDS}
    tot = {"n": len(ok), "of": len(COMPANIES),
           **{f: (round(v, 3) + 0.0 if full[f] else None) for f, v in s.items()},
           "ratio": round(s["capex"] / s["ocf"] * 100, 1) + 0.0 if s["ocf"] else None,
           "over": sum(1 for c in ok if c["ttm"]["ratio"] is not None and c["ttm"]["ratio"] > 100),
           "fcf_prev": None, "last_q": max(c["last_q"] for c in ok)}
    if all((c["ttm_prev"] or {}).get("ratio") is not None for c in ok):
        tot["fcf_prev"] = round(sum(c["ttm_prev"]["fcf"] for c in ok), 3) + 0.0
    return {"total": tot, "companies": comps}


def compute(got):
    """got → core {date, values}. 실패는 ItemError."""
    v = summary(got)
    return {"date": v["total"]["last_q"], "values": v}


# ---------- 조달 흐름 (flow — 비공개 원본과 같은 산식, 흐름 7칸에서) ----------

def cal_q(end):
    """분기 끝 'YYYY-MM-DD' → 달력 분기 번호(해 × 4 + 분기 − 1) — 끝 달로 맞춘다(1~3월 = 1분기, 오라클 2월 끝 = 1분기)."""
    d = _d(end)
    return d.year * 4 + (d.month - 1) // 3


def cal_label(k):
    """달력 분기 번호 → 'YYQn'(예 26Q3)."""
    return f"{(k // 4) % 100:02d}Q{k % 4 + 1}"


def _raw_sum(items, item, ends):
    vals = items.get(item)
    if not isinstance(vals, dict) or any(e not in vals for e in ends):
        return None
    return sum(vals[e] for e in ends)


def _window(items, ends):
    """4분기 창 → (설비투자, 외부 조달(순) = 순차입 + 순주식, 자사주 매입) 합 — 모르는 칸은 None(반올림 전 달러)."""
    capex = _raw_sum(items, "capex", ends)
    di, dr, ei, bb = (_raw_sum(items, k, ends) for k in ("debt_iss", "debt_rep", "eq_iss", "buyback"))
    ext = None if None in (di, dr, ei, bb) else (di - dr) + (ei - bb)
    return capex, ext, bb


def _share(pairs):
    """[(설비투자, 외부 조달)] → 외부 조달 합 / 설비투자 합 × 100(소수 넷째 자리 — 글은 정수 %로 한 번만 반올림한다, 비공개
    원본과 같은 저장 자리) — 설비투자 합이 0 이하면 None."""
    cap = sum(c for c, _ in pairs)
    return round(sum(x for _, x in pairs) / cap * 100, 4) + 0.0 if cap > 0 else None


def flow_calc(quarterly, filled=None):
    """조달 흐름 — 순수 함수(비공개 원본 sec_capex와의 짝 테스트가 부른다).

    quarterly = {회사 키(COMPANIES의 'MSFT' 등): {칸(ITEMS): {분기 끝 'YYYY-MM-DD': 달러}}} — company_quarters()의 items 꼴
    (0 채움 반영). 회사가 없거나 None이면 그 회사는 분기를 만들지 못한 것. filled = {회사 키: {칸: 0으로 채운 분기 끝들}} —
    company_quarters()의 filled 꼴(없으면 채움을 모르는 것으로 — noline이 빈다). 반환 values:
      of          회사 수(len(COMPANIES))
      asof        마지막 5사 완전 달력 분기에서 가장 늦은 분기 끝(칸 날짜)
      last        그 달력 분기 'YYQn'
      quarters    [{cal, fcf}] — last에서 거꾸로 이어진 FLOW_SHOW개(오래된 것부터), fcf = 그 달력 분기에 모든 회사가 영업현금·
                  설비투자를 가졌으면 Σ(영업현금 − 설비투자) bn, 아니면 None
      dec         마지막 분기부터 거꾸로 바로 앞 분기보다 작았던 횟수(FLOW_HIST분기 이력 안, 반올림 전 값으로)
      ext·ext_n   5사 TTM 외부 조달(순)/설비투자 %(소수 넷째 자리)와 그 둘을 아는 회사 수 — 모든 회사가 알 때만 값
      ext_prev·ext_prev_n  같은 것의 1년 전(회사마다 직전 4분기)
      zero_n·buyers·unknown  회사마다 마지막 분기 자사주 매입 — 0인 회사 수, [[키, bn]](0이 아닌 곳), 모르는 회사 키
      noline      0인 회사 가운데 그 분기 공시에 매입 줄이 없어 0으로 채운 회사 키(공시가 0이라고 낸 것과 다르다 — 2026-11-02)
      bb·bb_prev  5사 TTM 자사주 매입 합 bn(1년 전) — 모든 회사가 알 때만
      companies   회사마다 {key, ok, last_q, rows[{cal, end, fcf}](quarters 안의 분기만), bb_last, capex, ext, bb,
                  capex_prev, ext_prev, bb_prev} 또는 {key, ok: False, reason: 'no_q'}
    모든 회사가 함께 가진 달력 분기가 없으면 ItemError('format')."""
    quarterly, filled = quarterly or {}, filled or {}
    of = len(COMPANIES)
    raw, comps = {}, []
    for key, _lab, _cik, _fy, _spec in COMPANIES:
        items = quarterly.get(key)
        ocf = items.get("ocf") if isinstance(items, dict) else None
        capex = items.get("capex") if isinstance(items, dict) else None
        ends = sorted(set(ocf) & set(capex)) if isinstance(ocf, dict) and isinstance(capex, dict) else []
        if not ends:
            comps.append({"key": key, "ok": False, "reason": "no_q"})
            continue
        cal = {}
        for e in ends:                                        # 같은 달력 분기에 끝이 둘이면 늦은 것
            cal[cal_q(e)] = e
        last4, prev4 = ends[-4:], ends[-8:-4]
        now = _window(items, last4) if len(last4) == 4 and consecutive(last4) else (None, None, None)
        before = (_window(items, prev4) if now[0] is not None and len(prev4) == 4 and consecutive(prev4 + [last4[0]])
                  else (None, None, None))
        bbs = items.get("buyback")
        fb = (filled.get(key) or {}).get("buyback") if isinstance(filled.get(key), dict) else None
        raw[key] = {"cal": cal, "fcf": {k: ocf[e] - capex[e] for k, e in cal.items()}, "now": now, "before": before,
                    "bb_last": bbs.get(ends[-1]) if isinstance(bbs, dict) else None, "last_q": ends[-1],
                    "bb_filled": bool(fb) and ends[-1] in fb}
        comps.append({"key": key})
    common = set.intersection(*(set(r["fcf"]) for r in raw.values())) if len(raw) == of and raw else set()
    if not common:
        raise ItemError("format")
    last = max(common)

    def total(k):
        return sum(r["fcf"][k] for r in raw.values()) if k in common else None
    hist = [total(last - i) for i in range(FLOW_HIST - 1, -1, -1)]          # 오래된 것부터
    dec = 0
    for i in range(len(hist) - 1, 0, -1):
        if hist[i] is None or hist[i - 1] is None or not hist[i] < hist[i - 1]:
            break
        dec += 1
    show = [last - i for i in range(FLOW_SHOW - 1, -1, -1)]

    def share(which):
        pairs = [r[which][:2] for r in raw.values() if r[which][0] is not None and r[which][1] is not None]
        return (_share(pairs) if len(pairs) == of else None), len(pairs)
    ext, ext_n = share("now")
    ext_prev, ext_prev_n = share("before")
    bb_now = [r["now"][2] for r in raw.values() if r["now"][2] is not None]
    bb_before = [r["before"][2] for r in raw.values() if r["before"][2] is not None]
    zero_n, buyers, unknown, noline = 0, [], [], []
    for c in comps:
        r = raw.get(c["key"])
        if r is None or r["bb_last"] is None:
            unknown.append(c["key"])
        elif r["bb_last"] == 0:
            zero_n += 1
            if r["bb_filled"]:
                noline.append(c["key"])
        else:
            buyers.append([c["key"], _bn(r["bb_last"])])
        if r is None:
            continue
        c.update({"ok": True, "last_q": r["last_q"],
                  "rows": [{"cal": cal_label(k), "end": r["cal"][k], "fcf": _bn(r["fcf"][k])} for k in show if k in r["cal"]],
                  "bb_last": _bn(r["bb_last"]), "capex": _bn(r["now"][0]), "ext": _bn(r["now"][1]), "bb": _bn(r["now"][2]),
                  "capex_prev": _bn(r["before"][0]), "ext_prev": _bn(r["before"][1]), "bb_prev": _bn(r["before"][2])})
    return {"of": of, "asof": max(r["cal"][last] for r in raw.values()), "last": cal_label(last),
            "quarters": [{"cal": cal_label(k), "fcf": _bn(total(k))} for k in show], "dec": dec,
            "ext": ext, "ext_n": ext_n, "ext_prev": ext_prev, "ext_prev_n": ext_prev_n,
            "zero_n": zero_n, "buyers": buyers, "unknown": unknown, "noline": noline,
            "bb": _bn(sum(bb_now)) if len(bb_now) == of else None,
            "bb_prev": _bn(sum(bb_before)) if len(bb_before) == of else None, "companies": comps}


def compute_flow(got):
    """got(흐름 태그) → core {date, values}. 회사마다 company_quarters로 분기를 만든다(계산 오류는 그 회사만 없음)."""
    quarterly, filled = {}, {}
    for c in COMPANIES:
        try:
            cq = company_quarters(got.get(c[2]) or {}, c)
        except Exception:
            continue
        if cq.get("ok"):
            quarterly[c[0]], filled[c[0]] = cq["items"], cq["filled"]
    v = flow_calc(quarterly, filled)
    return {"date": v["asof"], "values": v}


# ---------- 재무상태 잔액 (bal — 비공개 원본과 같은 산식, 시점 사실에서) ----------

def _inst_part(fc, alts):
    """줄 하나(대체 태그) → {날짜: 값} — 같은 날짜는 늦게 낸 것(같은 날이면 앞 태그). 어느 태그도 받지 못했으면 None(모름)."""
    avail = [fc[t] for t in alts if t in fc]
    if not avail:
        return None
    best = {}
    for facts in avail:
        for e, v, f, _form in facts:
            if e not in best or f > best[e][1]:
                best[e] = (v, f)
    return {e: v for e, (v, _f) in best.items()}


def _field(fc, parts):
    """칸 하나 → (첫 줄 {날짜: 값}, [뒤 줄 {날짜: 값}…]) · 'none'(쓰지 않는 칸) · None(받지 못한 줄이 있다 — 모름)."""
    if not parts:
        return "none"
    got = [_inst_part(fc, alts) for alts in parts]
    if any(g is None for g in got):
        return None
    return got[0], got[1:]


def _at(field, d):
    """그 날짜의 칸 값 → (값, 0으로 채운 뒤 줄 수) 또는 None(첫 줄에 그 날짜가 없다)."""
    first, rest = field
    if d not in first:
        return None
    v, filled = first[d], 0
    for r in rest:
        if d in r:
            v += r[d]
        else:
            filled += 1
    return v, filled


def _year_before(dates, d):
    """d보다 YEAR_MIN~YEAR_MAX일 앞인 날짜 가운데 365일에 가장 가까운 것(같으면 늦은 날) — 없으면 None."""
    dd = _d(d)
    cand = [x for x in dates if YEAR_MIN <= (dd - _d(x)).days <= YEAR_MAX]
    return min(cand, key=lambda x: (abs((dd - _d(x)).days - 365), -_d(x).toordinal())) if cand else None


def _bal_company(fc, spec):
    """회사 하나 → (출력 dict, 반올림 전 값 dict) — 잔액 날짜가 없으면 (실패 dict, None)."""
    f = {k: _field(fc, spec.get(k) or []) for k in BAL_FIELDS}
    cash, debt = f["cash"], f["debt"]
    both = sorted(set(cash[0]) & set(debt[0])) if isinstance(cash, tuple) and isinstance(debt, tuple) else []
    if not both:
        return {"ok": False, "reason": "no_bal"}, None
    d = both[-1]
    (c, cf), (b, bf) = _at(cash, d), _at(debt, d)
    pd = _year_before(both, d)
    cp, bp = (_at(cash, pd)[0], _at(debt, pd)[0]) if pd else (None, None)
    filled = {"cash": cf, "debt": bf}
    out = {"ok": True, "date": d, "prev_date": pd}
    raw = {"cash": c, "debt": b, "net": c - b, "cash_prev": cp, "debt_prev": bp,
           "net_prev": None if pd is None else cp - bp, "lease": None, "rpo": None, "rpo_prev": None}
    for k in ("lease", "rpo"):
        out[f"{k}_date"] = None
        if not isinstance(f[k], tuple):
            continue
        dates = [x for x in f[k][0] if x <= d]
        if not dates:
            continue
        kd = max(dates)
        v, fl = _at(f[k], kd)
        out[f"{k}_date"], raw[k], filled[k] = kd, v, fl
        if k == "rpo":
            py = _year_before(list(f[k][0]), kd)
            raw["rpo_prev"] = _at(f[k], py)[0] if py else None
    out.update({k: _bn(raw[k]) for k in ("cash", "debt", "net", "cash_prev", "debt_prev", "net_prev", "lease", "rpo",
                                         "rpo_prev")})
    out["filled"] = filled
    return out, raw


def bal_calc(facts):
    """재무상태 잔액 — 순수 함수(비공개 원본 sec_capex와의 짝 테스트가 부른다).

    facts = {회사 키: {태그: [[끝 'YYYY-MM-DD', 값(달러), 낸 날 'YYYY-MM-DD', 양식]…]}} — 10-Q·10-K의 USD 시점 사실
    (trim_instant 꼴). 태그가 없으면 받지 못한 것(모름), 빈 목록이면 그 회사가 쓰지 않는 태그(404 — 첫 줄이면 그 칸 없음, 뒤
    줄이면 0). 태그 차림은 BAL. 반환 values = {total, companies}:
      companies  회사마다 {key, ok, date, cash, debt, net, prev_date, cash_prev, debt_prev, net_prev, lease, lease_date, rpo,
                 rpo_date, rpo_prev, filled{칸: 0으로 채운 줄 수}} (bn) 또는 {key, ok: False, reason}
      total      {n, of, date(가장 늦은 잔액 날짜), cash, debt, net(잔액을 낸 회사끼리), pos(순현금 > 0인 회사 수),
                 cash_prev·debt_prev·net_prev(모든 회사가 1년 전을 가질 때만), lease(잔액을 낸 회사가 모두 알 때만),
                 rpo_of(BAL에 RPO가 있는 회사 수), rpo_n(그 가운데 값이 있는 회사 수), rpo·rpo_prev(rpo_of 모두 있을 때만)}
    잔액을 낸 회사가 없으면 ItemError('format')."""
    facts = facts or {}
    comps, raws = [], {}
    for key, *_rest in COMPANIES:
        try:
            out, raw = _bal_company(facts.get(key) or {}, BAL.get(key) or {})
        except Exception:
            out, raw = {"ok": False, "reason": "calc"}, None
        comps.append({"key": key, **out})
        if raw is not None:
            raws[key] = raw
    ok = [c for c in comps if c["ok"]]
    if not ok:
        raise ItemError("format")
    of = len(COMPANIES)
    rs = [raws[c["key"]] for c in ok]

    def tsum(k, need):
        vals = [r[k] for r in need]
        return None if not vals or any(v is None for v in vals) else _bn(sum(vals))
    prev_ok = len(ok) == of and all(r["net_prev"] is not None for r in rs)
    rpo_keys = [c[0] for c in COMPANIES if (BAL.get(c[0]) or {}).get("rpo")]
    rpo_rs = [raws[k] for k in rpo_keys if k in raws and raws[k]["rpo"] is not None]
    full_rpo = bool(rpo_keys) and len(rpo_rs) == len(rpo_keys)
    tot = {"n": len(ok), "of": of, "date": max(c["date"] for c in ok),
           "cash": tsum("cash", rs), "debt": tsum("debt", rs), "net": tsum("net", rs),
           "cash_prev": tsum("cash_prev", rs) if prev_ok else None, "debt_prev": tsum("debt_prev", rs) if prev_ok else None,
           "net_prev": tsum("net_prev", rs) if prev_ok else None,
           "pos": sum(1 for r in rs if r["net"] > 0), "lease": tsum("lease", rs),
           "rpo_of": len(rpo_keys), "rpo_n": len(rpo_rs), "rpo": tsum("rpo", rpo_rs) if full_rpo else None,
           "rpo_prev": tsum("rpo_prev", rpo_rs) if full_rpo else None}
    return {"total": tot, "companies": comps}


def compute_bal(bgot):
    """bgot(잔액 태그, {CIK: {태그: 시점 사실}}) → core {date, values}."""
    v = bal_calc({c[0]: bgot.get(c[2]) or {} for c in COMPANIES})
    return {"date": v["total"]["date"], "values": v}


# ---------- 문구 ----------

def _f(v, nd=1):
    if v is None:
        return "—"
    s = f"{v:+.{nd}f}"
    return f"{0:.{nd}f}" if float(s) == 0 else s


def _g(v):
    return "—" if v is None else f"{v:.1f}"


def _pct(v):
    return "—" if v is None else f"{v:.0f}%"


def _pct0(v):
    """정수 % — 반올림해 0이면 부호 없이('-0%'가 아니라 '0%'). 외부 조달(순) 몫처럼 0 근처·음수가 나오는 칸."""
    if v is None:
        return "—"
    t = f"{v:.0f}"
    return ("0" if float(t) == 0 else t) + "%"


def _label(key):
    """회사 키 → (표시, 회계연도 끝 달)."""
    return next((c[1], c[3]) for c in COMPANIES if c[0] == key)


def texts(v):
    """values → (숫자 줄, 덧붙이는 줄 목록, 회사별 줄 목록). 정해 둔 문구에 숫자만 넣는다."""
    t, comps = v["total"], v["companies"]
    who = []
    for c in comps:
        if c["ok"]:
            mark = "" if c["last_q"] == t["last_q"] else f"(~{c['last_q'][:7]})"
            who.append(f"{c['key']} {_pct(c['ttm']['ratio'])}{mark}")
        else:
            who.append(f"{c['key']} {COMPANY_REASONS[c['reason']]}")
    n = f"{t['n']}사" if t["n"] == t["of"] else f"{t['n']}/{t['of']}사"
    prev = f" (1년 전 {_f(t['fcf_prev'])})" if t["fcf_prev"] is not None else ""
    line = (f"{n} TTM 설비투자/영업현금 {_pct(t['ratio'])} · FCF {_f(t['fcf'])}bn{prev} · 리스 원금 뺀 FCF {_f(t['fcf_l'])}bn · "
            f"장기 차입 발행 {_g(t['debt_iss'])}bn · 순차입 {_f(t['debt_net'])}bn · 순주식 {_f(t['eq_net'])}bn · "
            f"영업현금 초과 {t['over']}/{t['n']}사 — " + " · ".join(who))
    detail = []
    for c in comps:
        lab, fy = _label(c["key"])
        if not c["ok"]:
            detail.append(f"{c['key']}({lab}): {COMPANY_REASONS[c['reason']]}")
            continue
        tt, p = c["ttm"], c["ttm_prev"] or {}
        axis = "영업현금 초과 · 외부·보유 현금 조달" if tt["ratio"] is not None and tt["ratio"] > 100 else "영업현금 안 · 현금 조달"
        detail.append(f"{c['key']}({lab}, 회계연도 {fy}월 말, 마지막 분기 {c['last_q']}): 설비투자/영업현금 TTM {_pct(tt['ratio'])}"
                      f" (1년 전 {_pct(p.get('ratio'))}) · FCF TTM {_f(tt['fcf'])}bn · 마지막 분기 {_f(c['last_fcf'])}bn · "
                      f"리스 원금 뺀 FCF TTM {_f(tt['fcf_l'])}bn · 순차입 TTM {_f(tt['debt_net'])}bn (발행 {_g(tt['debt_iss'])} · "
                      f"상환 {_g(tt['debt_rep'])}) · 순주식 TTM {_f(tt['eq_net'])}bn (발행 {_g(tt['eq_iss'])} · "
                      f"매입 {_g(tt['buyback'])}) · {axis}")
        tg = [f"{ITEM_NAME[k]} {x}" for k, x in c["tags"].items() if x and k != "ocf"]
        fl = [f"{ITEM_NAME[k]} {m}" for k, m in c["filled"].items() if m]
        detail.append(f"{c['key']} 마지막 분기 태그: " + (" · ".join(tg) or "—") +
                      " · TTM 가운데 0으로 채운 분기 수: " + (" · ".join(fl) or "없음"))
    extra = ["회사마다 자기 마지막 4분기(TTM)의 합이다 — 회계연도가 달라 마지막 분기가 다를 수 있다(마이크로소프트 6월 말, "
             "오라클 5월 말, 나머지 12월 말 · 다르면 비율 옆에 그 달을 적는다). 단위 bn = 십억 달러. FCF = 영업현금 − 설비투자, "
             "리스 원금 뺀 FCF = FCF − 금융리스 원금, 순차입 = 장기 차입 발행 − 상환(기업어음 제외), 순주식 = 주식 발행(전환우선주 "
             "포함) − 자사주 매입(배당 제외). 영업현금 초과 = 설비투자/영업현금이 100%를 넘은 회사 수.",
             "분기는 누적(YTD) 공시의 차다(2분기 = 6개월 − 3개월, 4분기 = 연간 − 9개월). 같은 기간은 늦게 낸 공시(정정·다음 해 "
             "비교 수치)를 쓴다. TTM은 4분기가 이어질 때만. 그 분기 공시에 줄이 없거나 회사가 쓰지 않는 줄은 0으로 채우고 회사별 "
             "줄에 그 수를 적는다(영업현금·설비투자는 채우지 않는다).",
             "숫자만 싣는 서술이다 — 단계·점수가 없고 금리를 예측하지 않는다."]
    return line, extra, detail


def _topic(word):
    """받침이 있으면 '은', 없으면 '는'(한글이 아니면 '은')."""
    ch = word[-1:] if word else ""
    return "는" if "가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28 == 0 else "은"


def flow_texts(v):
    """조달 흐름 values → (숫자 줄, 덧붙이는 줄 목록, 회사별 줄 목록)."""
    of = v["of"]
    qs = ", ".join(f"{q['cal']} {_f(q['fcf'])}" for q in v["quarters"])
    dec = f"연속 감소 {v['dec']}분기" if v["dec"] else "연속 감소 없음"
    if v["ext"] is not None:
        ext = _pct0(v["ext"]) + (f" (1년 전 {_pct0(v['ext_prev'])})" if v["ext_prev"] is not None else "")
    else:
        ext = f"— ({v['ext_n']}/{of}사만 계산됨)"
    bits = []
    if v["noline"]:                                                   # 그 분기 공시에 매입 줄이 없어 0으로 채운 회사(공시된 0과 다르다)
        bits.append(f"줄 없음 {len(v['noline'])}: " + "·".join(v["noline"]))
    if v["buyers"]:
        bits.append("매입: " + ", ".join(f"{k} {_g(x)}bn" for k, x in v["buyers"]))
    if v["unknown"]:
        bits.append("모름: " + ", ".join(v["unknown"]))
    bb = f" ({' · '.join(bits)})" if bits else ""
    prev = f" (1년 전 {_g(v['bb_prev'])})" if v["bb_prev"] is not None else ""
    line = (f"{of}사 분기 FCF(달력 분기, bn): {qs} · {dec} · 외부 조달(순)/설비투자 TTM {ext} · "
            f"마지막 분기 자사주 매입 0: {v['zero_n']}/{of}사{bb} · TTM 자사주 매입 {_g(v['bb'])}bn{prev}")
    shifted = []
    for key, lab, _cik, fy, _spec in COMPANIES:
        if fy % 3:
            months = "·".join(str(m) for m in sorted((fy + 3 * i - 1) % 12 + 1 for i in range(4)))
            ahead = {1: "두 달", 2: "한 달"}[fy % 3]
            shifted.append(f"{lab}{_topic(lab)} 분기 끝이 {months}월이라 {ahead} 앞선 분기를 같은 달력 분기로 센다.")
    extra = [" ".join(["달력 분기는 회사 분기의 끝 달로 맞춘다(1~3월 끝 = 1분기, 표기 YYQn)."] + shifted),
             "5사 분기 FCF = 그 달력 분기에 모든 회사가 낸 분기의 영업현금 − 설비투자 합이다(한 곳이라도 없으면 비움). "
             f"연속 감소는 마지막 분기부터 거꾸로 바로 앞 분기보다 작았던 분기 수다(최근 {FLOW_HIST}분기 안, 반올림 전 값으로). "
             "앞 분기 대비이고 계절조정이 아니다 — 영업현금은 계절성이 커서 계절만으로도 감소가 세어질 수 있다. "
             "외부 조달(순) = 순차입(장기 차입 발행 − 상환) + 순주식(주식 발행 − 자사주 매입)이고, 그 몫은 모든 회사에 "
             "TTM이 있을 때만 낸다(회사마다 자기 마지막 4분기, 1년 전은 그 앞 4분기). 자사주 매입 0의 '줄 없음'은 그 분기 공시에 "
             "매입 줄이 없어 0으로 채운 회사다 — 공시가 0이라고 낸 것과 달리 다른 줄에 합쳤을 수 있다. 단위 bn = 십억 달러.",
             "숫자만 싣는 서술이다 — 단계·점수가 없고 금리를 예측하지 않는다."]
    detail = []
    for c in v["companies"]:
        lab, fy = _label(c["key"])
        if not c["ok"]:
            detail.append(f"{c['key']}({lab}): {COMPANY_REASONS[c['reason']]}")
            continue
        rows = ", ".join(f"{r['cal']} {_f(r['fcf'])}" + ("" if int(r["end"][5:7]) % 3 == 0 else f"({r['end'][:7]} 말)")
                         for r in c["rows"]) or "—"
        detail.append(f"{c['key']}({lab}, 회계연도 {fy}월 말, 마지막 분기 {c['last_q']}): 분기 FCF {rows} · "
                      f"마지막 분기 자사주 매입 {_g(c['bb_last'])}bn · TTM 외부 조달(순) {_f(c['ext'])}bn / 설비투자 "
                      f"{_g(c['capex'])}bn (1년 전 {_f(c['ext_prev'])} / {_g(c['capex_prev'])}) · TTM 자사주 매입 "
                      f"{_g(c['bb'])}bn (1년 전 {_g(c['bb_prev'])})")
    return line, extra, detail


def bal_texts(v):
    """재무상태 잔액 values → (숫자 줄, 덧붙이는 줄 목록, 회사별 줄 목록)."""
    t, comps = v["total"], v["companies"]
    n = f"{t['n']}사" if t["n"] == t["of"] else f"{t['n']}/{t['of']}사"
    who = []
    for c in comps:
        if not c["ok"]:
            who.append(f"{c['key']} {COMPANY_REASONS[c['reason']]}")
            continue
        marks = [] if c["date"] == t["date"] else [f"~{c['date'][:7]}"]   # 비공개 원본 bal_line과 같은 표식
        for k, name in (("lease", "리스"), ("rpo", "RPO")):
            if c[f"{k}_date"] and c[f"{k}_date"] != c["date"]:
                marks.append(f"{name} ~{c[f'{k}_date'][:7]}")
            elif k == "lease" and not c["lease_date"]:
                marks.append("리스 모름")
        who.append(f"{c['key']} {_f(c['net'])}" + (f"({' · '.join(marks)})" if marks else ""))
    prev = f" (1년 전 {_f(t['net_prev'])})" if t["net_prev"] is not None else ""
    if t["rpo_of"]:
        rpo = (f" · 수주잔고(RPO) {t['rpo_of']}사 {_g(t['rpo'])}bn" +
               (f" (1년 전 {_g(t['rpo_prev'])})" if t["rpo_prev"] is not None else "")
               if t["rpo"] is not None else f" · 수주잔고(RPO) — ({t['rpo_n']}/{t['rpo_of']}사만 있음)")
    else:
        rpo = ""
    line = (f"{n} 분기 말 잔액(회사마다 마지막 공시일): 현금 {_g(t['cash'])}bn · 장기 차입 {_g(t['debt'])}bn · 순현금 "
            f"{_f(t['net'])}bn{prev} · 순현금 양(+) {t['pos']}/{t['of']}사 · 리스부채 {_g(t['lease'])}bn{rpo} — 순현금 "
            + " · ".join(who))
    rpo_names = "·".join(c[1] for c in COMPANIES if (BAL.get(c[0]) or {}).get("rpo"))
    extra = ["분기 말 잔액은 회사마다 마지막 공시일의 것이다 — 회계연도가 달라 날짜가 다르면 회사 옆에 그 달을 적는다. "
             "현금 = 현금·현금성 자산 + 단기 투자(회사마다 공시 줄이 다르다), 장기 차입 = 유동 + 비유동(기업어음·리스 제외 — 다만 "
             "오라클의 유동 줄 NotesPayableCurrent는 재무상태표에 기업어음 줄이 따로 없어 기업어음 등 단기 차입이 섞일 수 있다), "
             "순현금 = 현금 − 장기 차입. 리스부채 = 운용 + 금융, 잔액 날짜 이하의 마지막 공시다(연간에만 내는 회사는 날짜가 "
             "이를 수 있다). 수주잔고(RPO)는 그 줄을 공시하는 회사만" + (f"({rpo_names})" if rpo_names else "") +
             ". 단위 bn = 십억 달러.",
             "회사 옆 표식: ~YYYY-MM 잔액 날짜가 다름 · 리스 ~YYYY-MM · RPO ~YYYY-MM 그 칸의 날짜가 잔액 날짜와 다름 · 리스 모름 "
             "리스 공시가 없음.",
             f"1년 전 = 그 날짜보다 {YEAR_MIN}~{YEAR_MAX}일 앞의 공시이고, 합은 모든 회사에 1년 전이 있을 때만 낸다. 같은 "
             "날짜의 사실이 여럿이면 늦게 낸 공시를 쓴다. 칸의 두 번째 줄(단기 투자·유동 차입·금융리스)은 그 날짜에 없으면 0으로 "
             "채우고 회사별 줄에 그 수를 적는다.",
             "숫자만 싣는 서술이다 — 단계·점수가 없고 금리를 예측하지 않는다."]
    detail = []
    for c in comps:
        lab, _fy = _label(c["key"])
        if not c["ok"]:
            detail.append(f"{c['key']}({lab}): {COMPANY_REASONS[c['reason']]}")
            continue
        spec = BAL.get(c["key"]) or {}
        lease = (f"리스부채 {_g(c['lease'])}bn" + ("" if c["lease_date"] == c["date"] else f" ({c['lease_date']})")
                 if c["lease_date"] else "리스부채 —")
        if not spec.get("rpo"):
            rpo = "수주잔고 싣지 않음"
        elif c["rpo_date"]:
            rpo = (f"수주잔고 {_g(c['rpo'])}bn" + ("" if c["rpo_date"] == c["date"] else f" ({c['rpo_date']})") +
                   f" · 1년 전 {_g(c['rpo_prev'])}")
        else:
            rpo = "수주잔고 —"
        fl = " · ".join(f"{BAL_NAME[k]} {m}" for k, m in c["filled"].items() if m) or "없음"
        detail.append(f"{c['key']}({lab}, 잔액 {c['date']}, 1년 전 {c['prev_date'] or '없음'}): 현금 {_g(c['cash'])}bn · "
                      f"장기 차입 {_g(c['debt'])}bn · 순현금 {_f(c['net'])}bn · 1년 전 현금 {_g(c['cash_prev'])} · "
                      f"장기 차입 {_g(c['debt_prev'])} · 순현금 {_f(c['net_prev'])} · {lease} · {rpo} · "
                      f"0으로 채운 줄: {fl}")
    return line, extra, detail


def _texts(kind, v):
    """칸 종류 → 문구 — 부를 때 이 모듈의 함수를 찾는다(테스트가 바꿔 끼울 수 있게)."""
    if kind == "flow":
        return flow_texts(v)
    if kind == "bal":
        return bal_texts(v)
    return texts(v)


def _retrieved_text(retrieved):
    d = datetime.date.fromisoformat(retrieved)
    return f"{ai._MONTHS[d.month - 1]} {d.day}, {d.year}"


def sources_of(retrieved=None):
    s = {"series": "EDGAR", "name": "U.S. Securities and Exchange Commission", "url": DOC_URL, "licence": "public"}
    if retrieved:
        s["citation"] = f"{SOURCE_LINE}. Retrieved {_retrieved_text(retrieved)}."
    return [s]


TITLES = {"funding": TITLE, "flow": FLOW_TITLE, "bal": BAL_TITLE}


def _kind(key):
    """칸 키 → 칸 종류(funding·flow·bal). 신용 긴축 카드가 옮겨 싣는 'sec'는 funding."""
    return key if key in TITLES else "funding"


def present(core, retrieved, key="funding"):
    kind = _kind(key)
    line, extra, detail = _texts(kind, core["values"])
    return {"key": key, "name": TITLES[kind], "date": core["date"], "values": core["values"], "retrieved": retrieved,
            "line": line, "extra": extra, "detail": detail, "notices": [COMPUTED_NOTICE], "sources": sources_of(retrieved)}


# ---------- 직전 파일 ----------

def _known_tags():
    return {t for c in COMPANIES for t in tags_of(c)}


_TTM = {**{k: "num?" for k in ITEMS}, "fcf": "num?", "ratio": "num?", "fcf_l": "num?", "debt_net": "num?",
        "eq_net": "num?", "from": "day", "to": "day"}
_PREV = {"ratio": "num?", "fcf": "num?", "capex": "num?", "debt_net": "num?", "eq_net": "num?", "buyback": "num?",
         "from": "day", "to": "day"}
_TOT = {"n": "int", "of": "int", **{f: "num?" for f in TOTAL_FIELDS}, "ratio": "num?", "over": "int", "fcf_prev": "num?",
        "last_q": "day"}
_ROW = {"q": "day", **{k: "num?" for k in ITEMS}}
_CAL = re.compile(r"\d{2}Q[1-4]")
_KIND = dict(ai._KIND, cal=lambda v: isinstance(v, str) and _CAL.fullmatch(v) is not None,
             key=lambda v: v in {c[0] for c in COMPANIES}, bool=lambda v: isinstance(v, bool),
             list=lambda v: isinstance(v, list), dict=lambda v: isinstance(v, dict))
_KIND["key_bn"] = lambda v: isinstance(v, list) and len(v) == 2 and _KIND["key"](v[0]) and _KIND["num"](v[1])


def _shape(d, kinds):
    return isinstance(d, dict) and set(d) == set(kinds) and all(_KIND[t](d[k]) for k, t in kinds.items())


def _company_ok(c, key):
    if not isinstance(c, dict) or c.get("key") != key or not isinstance(c.get("ok"), bool):
        return False
    if not c["ok"]:
        return set(c) == {"key", "ok", "reason", "last_q"} and c["reason"] in COMPANY_REASONS and \
            (c["last_q"] is None or ai._is_day(c["last_q"]))
    return (set(c) == {"key", "ok", "last_q", "ttm", "ttm_prev", "last_fcf", "tags", "filled", "rows"}
            and ai._is_day(c["last_q"]) and _shape(c["ttm"], _TTM)
            and (c["ttm_prev"] is None or _shape(c["ttm_prev"], _PREV)) and _KIND["num?"](c["last_fcf"])
            and isinstance(c["tags"], dict) and set(c["tags"]) <= set(ITEMS)
            and all(x is None or x in _known_tags() for x in c["tags"].values())
            and isinstance(c["filled"], dict) and set(c["filled"]) <= set(OPTIONAL)
            and all(type(m) is int and 0 <= m <= 4 for m in c["filled"].values())
            and isinstance(c["rows"], list) and len(c["rows"]) <= ROWS and all(_shape(r, _ROW) for r in c["rows"]))


def values_ok(v):
    """funding values 꼴 검사 — 정해 둔 키·꼴·회사 차례·태그 이름만(직전 파일 검사)."""
    if not isinstance(v, dict) or set(v) != {"total", "companies"} or not _shape(v["total"], _TOT):
        return False
    comps = v["companies"]
    if not isinstance(comps, list) or len(comps) != len(COMPANIES):
        return False
    if not all(_company_ok(c, co[0]) for c, co in zip(comps, COMPANIES)):
        return False
    t = v["total"]
    ok = [c for c in comps if c["ok"]]
    return t["of"] == len(COMPANIES) and t["n"] == len(ok) and 0 < t["n"] and t["over"] <= t["n"] \
        and t["last_q"] == max(c["last_q"] for c in ok)


_FLOW = {"of": "int", "asof": "day", "last": "cal", "quarters": "list", "dec": "int", "ext": "num?", "ext_n": "int",
         "ext_prev": "num?", "ext_prev_n": "int", "zero_n": "int", "buyers": "list", "unknown": "list", "noline": "list",
         "bb": "num?", "bb_prev": "num?", "companies": "list"}
_FLOW_CO = {"key": "key", "ok": "bool", "last_q": "day", "rows": "list", "bb_last": "num?", "capex": "num?", "ext": "num?",
            "bb": "num?", "capex_prev": "num?", "ext_prev": "num?", "bb_prev": "num?"}
_FLOW_Q = {"cal": "cal", "fcf": "num?"}
_FLOW_ROW = {"cal": "cal", "end": "day", "fcf": "num"}


def _cal_num(label):
    return (2000 + int(label[:2])) * 4 + int(label[3]) - 1


def flow_values_ok(v):
    """flow values 꼴 검사 — 정해 둔 키·꼴, 달력 분기가 이어지고 마지막 분기에 값, 회사 차례, 매입 셈이 회사 수와 맞음."""
    if not _shape(v, _FLOW):
        return False
    of, comps, qs = v["of"], v["companies"], v["quarters"]
    if of != len(COMPANIES) or not isinstance(comps, list) or len(comps) != of or not isinstance(qs, list) \
            or len(qs) != FLOW_SHOW or not all(_shape(q, _FLOW_Q) for q in qs):
        return False
    nums = [_cal_num(q["cal"]) for q in qs]
    if nums != list(range(nums[0], nums[0] + FLOW_SHOW)) or qs[-1]["cal"] != v["last"] or qs[-1]["fcf"] is None:
        return False
    for c, co in zip(comps, COMPANIES):
        if not isinstance(c, dict) or c.get("key") != co[0]:
            return False
        if c.get("ok") is False:
            if set(c) != {"key", "ok", "reason"} or c["reason"] not in COMPANY_REASONS:
                return False
            continue
        if not _shape(c, _FLOW_CO) or c["ok"] is not True or not isinstance(c["rows"], list) \
                or len(c["rows"]) > FLOW_SHOW or not all(_shape(r, _FLOW_ROW) for r in c["rows"]):
            return False
    keys = [c["key"] for c in comps]
    buyers, unknown = v["buyers"], v["unknown"]
    if not isinstance(buyers, list) or not all(_KIND["key_bn"](b) for b in buyers) or not isinstance(unknown, list) \
            or not all(_KIND["key"](k) for k in unknown):
        return False
    named = [b[0] for b in buyers] + unknown
    noline = v["noline"]
    if not isinstance(noline, list) or not all(_KIND["key"](k) for k in noline) or len(set(noline)) != len(noline) \
            or set(noline) & set(named) or len(noline) > v["zero_n"]:
        return False
    return (len(set(named)) == len(named) and set(named) <= set(keys) and v["zero_n"] + len(named) == of
            and v["dec"] <= FLOW_HIST - 1 and v["ext_n"] <= of and v["ext_prev_n"] <= of
            and (v["ext"] is None or v["ext_n"] == of) and (v["ext_prev"] is None or v["ext_prev_n"] == of)
            and all(c["ok"] for c in comps))                   # 5사 완전 분기가 있으면 모든 회사가 분기를 가졌다


_BAL_CO = {"key": "key", "ok": "bool", "date": "day", "cash": "num", "debt": "num", "net": "num", "prev_date": "day?",
           "cash_prev": "num?", "debt_prev": "num?", "net_prev": "num?", "lease": "num?", "lease_date": "day?",
           "rpo": "num?", "rpo_date": "day?", "rpo_prev": "num?", "filled": "dict"}
_BAL_TOT = {"n": "int", "of": "int", "date": "day", "cash": "num", "debt": "num", "net": "num", "cash_prev": "num?",
            "debt_prev": "num?", "net_prev": "num?", "pos": "int", "lease": "num?", "rpo_of": "int", "rpo_n": "int",
            "rpo": "num?", "rpo_prev": "num?"}


def bal_values_ok(v):
    """bal values 꼴 검사 — 정해 둔 키·꼴, 회사 차례, 날짜끼리(리스·수주잔고 ≤ 잔액 날짜), 합계의 셈."""
    if not isinstance(v, dict) or set(v) != {"total", "companies"} or not _shape(v["total"], _BAL_TOT):
        return False
    comps, t = v["companies"], v["total"]
    if not isinstance(comps, list) or len(comps) != len(COMPANIES):
        return False
    for c, co in zip(comps, COMPANIES):
        if not isinstance(c, dict) or c.get("key") != co[0]:
            return False
        if c.get("ok") is False:
            if set(c) != {"key", "ok", "reason"} or c["reason"] not in COMPANY_REASONS:
                return False
            continue
        if not _shape(c, _BAL_CO) or c["ok"] is not True:
            return False
        fl = c["filled"]
        if not isinstance(fl, dict) or not set(fl) <= set(BAL_FIELDS) or not all(type(m) is int and 0 <= m <= 4
                                                                                  for m in fl.values()):
            return False
        if any(c[f"{k}_date"] is not None and c[f"{k}_date"] > c["date"] for k in ("lease", "rpo")) \
                or (c["prev_date"] is not None and c["prev_date"] >= c["date"]) \
                or ((c["lease"] is None) != (c["lease_date"] is None)) or ((c["rpo"] is None) != (c["rpo_date"] is None)) \
                or (c["rpo"] is not None and not (BAL.get(c["key"]) or {}).get("rpo")):
            return False
    ok = [c for c in comps if c["ok"]]
    rpo_of = sum(1 for co in COMPANIES if (BAL.get(co[0]) or {}).get("rpo"))
    return (t["of"] == len(COMPANIES) and t["n"] == len(ok) and 0 < t["n"] and t["pos"] <= t["n"]
            and t["date"] == max(c["date"] for c in ok) and t["rpo_of"] == rpo_of and t["rpo_n"] <= rpo_of
            and (t["rpo"] is None or t["rpo_n"] == rpo_of))


def _values_ok(kind, v):
    if kind == "flow":
        return flow_values_ok(v)
    if kind == "bal":
        return bal_values_ok(v)
    return values_ok(v)


def _date_of(kind, v):
    """values → 칸 날짜(직전 파일 검사·새 숫자 검사가 같은지 본다)."""
    if kind == "flow":
        return v["asof"]
    if kind == "bal":
        return v["total"]["date"]
    return v["total"]["last_q"]


def core_of(item, kind="funding"):
    """칸(dict) → (core, 받은 날) 또는 None(없거나 꼴이 어긋남)."""
    try:
        vals = item["values"]
        ok = ai._is_day(item["date"]) and ai._is_day(item["retrieved"]) and _values_ok(kind, vals) \
            and item["date"] == _date_of(kind, vals)
        if ok:
            _texts(kind, vals)
    except (KeyError, TypeError, IndexError, AttributeError, ValueError):
        return None
    if not ok:
        return None
    return {"date": item["date"], "values": json.loads(json.dumps(vals))}, item["retrieved"]


def previous_items(out):
    """<out>/sec.json의 칸 → {키: dict}(ORDER의 키만). 없거나 깨졌으면 {}."""
    try:
        with open(os.path.join(out, FILE), encoding="utf-8") as f:
            js = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(js, dict) or js.get("schema") != SCHEMA or not isinstance(js.get("items"), dict):
        return {}
    return {k: v for k, v in js["items"].items() if k in ORDER and isinstance(v, dict)}


def previous(out):
    """funding 칸(신용 긴축 카드가 옮겨 싣는다) — dict 또는 None."""
    return previous_items(out).get("funding")


def item_ok(core, prev, today, key="funding"):
    kind = _kind(key)
    try:                                         # 새 숫자도 직전 파일과 같은 꼴 검사를 거친다(NaN·뜻밖의 꼴은 싣지 않는다)
        fresh = json.loads(json.dumps(core, allow_nan=False))
        good = _values_ok(kind, fresh["values"]) and fresh["date"] == _date_of(kind, fresh["values"])
    except (ValueError, TypeError, KeyError):
        good = False
    if not good:
        raise ItemError("format")
    old = core_of(prev, kind) if prev else None
    if old and core["date"] < old[0]["date"]:
        raise ItemError("older")
    same = old and json.loads(json.dumps(old[0])) == fresh
    retrieved = old[1] if same else today.isoformat()
    return {"ok": True, "stale": False, "error": None, "failed_since": None, **present(fresh, retrieved, key)}


def item_failed(code, prev, today, key="funding"):
    kind = _kind(key)
    since = prev.get("failed_since") if prev and ai._is_day(prev.get("failed_since")) else today.isoformat()
    old = core_of(prev, kind) if prev else None
    if old:
        return {"ok": False, "stale": True, "error": REASONS[code], "failed_since": since, **present(*old, key)}
    return {"ok": False, "stale": False, "error": REASONS[code], "failed_since": since, "key": key, "name": TITLES[kind],
            "sources": sources_of()}


def _one(key, result, prev, today):
    if not isinstance(result, ItemError):
        try:
            return item_ok(result, prev, today, key)
        except ItemError as e:
            result = e
    return item_failed(result.code, prev, today, key)


def build(results, prevs, now):
    """results = {칸: core 또는 ItemError}(없는 칸은 'format'), prevs = {칸: 직전 칸} → 산출물 dict."""
    today = now.date()
    prevs = prevs or {}
    items = {key: _one(key, results.get(key, ItemError("format")), prevs.get(key), today) for key in ORDER}
    return {"schema": SCHEMA, "generated_at": now.isoformat(timespec="seconds"), "notice": NOTICE,
            "order": list(ORDER), "items": items}


# ---------- 쓰기 ----------

def differs(out, data):
    try:
        with open(os.path.join(out, FILE), encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        return True
    strip = lambda d: {k: v for k, v in d.items() if k != "generated_at"} if isinstance(d, dict) else d
    return strip(old) != strip(json.loads(json.dumps(data)))


def dump(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def write(out, data, ua=None):
    """연락처 조각이 섞인 글은 쓰지 않는다(ItemError('leak')) — 부르는 쪽이 정해 둔 사유로 바꿔 다시 만든다."""
    if data_leaks(data, ua):
        raise ItemError("leak")
    os.makedirs(out, exist_ok=True)
    ai._atomic_write(os.path.join(out, FILE), dump(data))


def guarded(results, prevs, now, ua):
    """build + 연락처 검사(칸마다). 칸에 섞였으면 그 칸만 사유 'leak'으로 직전 값과 다시, 그래도 섞였으면 직전 값 없이(사유만).
    정해 둔 글(머리 안내 등)에 섞여 그래도 남으면 None — 아무것도 쓰지 않는다."""
    prevs = prevs or {}
    data = build(results, prevs, now)
    today = now.date()
    for key in ORDER:
        if data_leaks(data["items"][key], ua):
            it = item_failed("leak", prevs.get(key), today, key)
            data["items"][key] = it if not data_leaks(it, ua) else item_failed("leak", None, today, key)
    return None if data_leaks(data, ua) else data


def _calc(fn, arg, ua):
    """계산 하나 — ItemError는 그대로, 뜻밖의 오류는 'format'(로그엔 예외 이름만)."""
    try:
        return fn(arg)
    except ItemError as e:
        return e
    except Exception as e:
        say(f"[sec_fetch] {fn.__name__} 계산 오류: {type(e).__name__}", ua, err=True)
        return ItemError("format")


def results_of(f, ua=None):
    """fetch_both 결과 → {칸: core 또는 ItemError}. funding·flow는 흐름 태그, bal은 잔액 태그."""
    out = {}
    if f["code"]:
        out["funding"] = out["flow"] = ItemError(f["code"])
    else:
        out["funding"] = _calc(compute, f["got"], ua)
        out["flow"] = _calc(compute_flow, f["got"], ua)
    out["bal"] = ItemError(f["bcode"]) if f["bcode"] else _calc(compute_bal, f["bgot"], ua)
    return out


def main(argv=None, opener=None, now=None, clock=time.monotonic, sleep=time.sleep, env=None):
    ap = argparse.ArgumentParser(description="SEC EDGAR XBRL 공시 → 하이퍼스케일러 조달 참고 자료(<out>/sec.json)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    ua = user_agent(env)
    f = fetch_both(ua, now.date(), BUDGET, opener, clock, sleep)
    data = guarded(results_of(f, ua), previous_items(out), now, ua)
    if data is None:                            # 정해 둔 글에도 섞였다 — 아무것도 쓰지 않는다
        say(f"[sec_fetch] {FILE}를 쓰지 않음: {REASONS['leak']}", ua, err=True)
        return 1
    # 공개 저장소의 Actions 로그 — 날짜·요청 수·정해 둔 사유만(값·머리글·연락처는 찍지 않는다)
    for key in ORDER:
        it = data["items"][key]
        if it["ok"]:
            say(f"[sec_fetch] {key} {it['date']} 기준", ua)
        else:
            kept = f" — 직전 값({it['date']} 기준) 유지" if it["stale"] else ""
            say(f"SEC 조달 참고 {key} 받지 못함: {it['error']}{kept}", ua, warn=True)
    say(f"[sec_fetch] 요청 {f['n'] + f['nb']}번 (흐름 {f['n']} · 잔액 {f['nb']})", ua)
    try:
        if differs(out, data):
            write(out, data, ua)
    except ItemError:
        say(f"[sec_fetch] {FILE}를 쓰지 않음: {REASONS['leak']}", ua, err=True)
        return 1
    except OSError as e:
        say(f"[sec_fetch] {FILE}를 쓰지 못함: {type(e).__name__}", ua, err=True)
        return 1
    return 0 if any(data["items"][k]["ok"] for k in ORDER) else 1


if __name__ == "__main__":
    sys.exit(main())
