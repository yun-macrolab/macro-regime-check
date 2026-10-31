#!/usr/bin/env python3
"""참고 자료 — 하이퍼스케일러 다섯 곳의 설비투자·영업현금·차입·주식 조달 (2026-10-30 추가, 사용자 결정: 비공개 줄 공개).

운영자의 비공개 월간 점검 [신용 긴축] 끝의 '기업별 조달' 줄을 공개한 것이다(비공개 원본 sec_capex.py와 같은 산식 — 코드는
가져오지 않고 여기서 따로 쓴다. 산식을 고치면 양쪽을 같이). 숫자만 싣는 서술이다 — 판정·문턱·단계·점수가 없고, 판정·공개본·
그래프 스크립트는 이 파일(<out>/sec.json)을 읽지 않는다. 신용 긴축 카드(credit_fetch.py)가 이 파일을 읽어 한 줄로 싣는다.

자료: SEC EDGAR XBRL companyconcept(data.sec.gov — 회사·태그마다 작은 JSON, 미국 정부 공개 자료). 마이크로소프트·알파벳·
  아마존·메타·오라클(COMPANIES, CIK·태그는 비공개 원본과 같다 — 2026-10-29 companyfacts에서 확인)의 영업현금·설비투자·금융리스
  원금·장기 차입 발행/상환·주식(전환우선주 포함) 발행·자사주 매입. 런마다 35개를 모두 받는다(원 응답은 디스크에 쓰지 않고, 이
  파일엔 분기 표와 합계만 남긴다). 출처 표기: 'Source: SEC EDGAR XBRL API (data.sec.gov); site calculations' — SEC 로고·인장은
  쓰지 않는다.
연락처: SEC 공정 접근 정책은 요청 머리글 User-Agent에 연락처를 싣게 한다. 그 값은 환경 변수 SEC_USER_AGENT(GitHub Actions
  비밀)에서만 읽는다 — 코드·문서·자료 파일·로그·오류 문구 어디에도 쓰지 않는다(오류는 정해 둔 사유 코드로만 남는다). 변수가
  없거나 비었으면 요청을 하나도 하지 않고 칸을 '연락처 미설정(SEC_USER_AGENT)'으로 둔다(직전 값이 있으면 그것을 받지 못함으로).
  요청은 https sec.gov 주소에만 만들고, https sec.gov 밖으로 옮기는 응답은 따라가지 않는다(머리글이 따라가지 않게). 주소는
  urllib이 실제로 붙는 호스트(Request.host)로 본다 — 사용자 정보('@')·역슬래시·443 밖 포트가 든 주소는 거절.
  쓰기·로그 직전에 한 번 더: 연락처 조각(값 전체·이메일 꼴의 앞·뒤 부분)이나 이메일 꼴 낱말이 글에 섞였으면 그 글을 쓰지 않고
  칸을 '연락처 꼴 글이 섞여 쓰지 않음'으로(직전 값에도 섞였으면 직전 값 없이), 로그 줄은 정해 둔 문구로 바꾼다.
  한 번에 하나씩, 요청 사이 GAP초(초당 4회 아래 — SEC 상한 10회), 수신 전체 BUDGET초(읽는 동안에도 본다).
분기 만들기(회사마다 회계연도대로 — MSFT 6월 말, ORCL 5월 말, 나머지 12월 말):
  - 10-Q·10-K의 기간 사실만(8-K 등 제외). 같은 (시작, 끝)은 늦게 낸 공시가 이긴다(정정 공시·다음 해 비교 수치).
  - 현금흐름표는 누적(YTD)이라 같은 시작일의 앞 누적을 뺀다: 2분기 = 6개월 − 3개월, 4분기 = 연간 − 9개월. 3개월 사실은 그대로.
  - 영업현금·설비투자는 필수. 나머지는 그 분기에 줄이 없거나 쓰지 않는 태그(404)면 0으로 채운다(영업현금이 공시된 분기만).
  - TTM = 마지막 4분기, 분기 끝 사이가 80~100일로 이어질 때만. 1년 전 TTM = 그 앞 4분기, 지금 창에 바로 이어질 때만.
  - 5사 합은 TTM을 낸 회사끼리, 칸 하나라도 모르는 회사가 있으면 그 칸 합은 비운다. 1년 전 FCF 합은 그 회사들 모두에 1년 전
    TTM이 있을 때만. '영업현금 초과'는 설비투자/영업현금 > 100%(정확히 100%는 아니다).

실패: 35개 가운데 하나라도 받지 못하면(연결 실패·시간 초과·SEC 거절·깨진 응답·시간 상한) 이번 숫자를 쓰지 않고 직전 파일의
숫자를 '받지 못함(stale)'과 그날부터라는 날짜와 함께 이어 싣는다(직전 값이 없으면 사유만). 문구는 이 파일에 정해 둔 것뿐이다.
같은 내용이면 다시 쓰지 않는다.

종료코드: 0 이번에 받음 / 1 받지 못함(연락처 미설정·연락처 꼴 글이 섞임 포함, 또는 파일을 쓰지 못함). 워크플로 단계는 continue-on-error, 알림 없음.

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
    ("META", "메타", "0001326801", 12, {
        "ocf": [[OCF]], "capex": [[PPE]], "flease": [[FLPP]],
        "debt_iss": [[PFILTD]], "debt_rep": [],
        "eq_iss": [], "buyback": [[BUYBACK]]}),
    ("ORCL", "오라클", "0001341439", 5, {
        "ocf": [[OCF]], "capex": [[PPE]], "flease": [[FLPP]],
        "debt_iss": [["ProceedsFromIssuanceOfSeniorLongTermDebt", PFILTD]],
        "debt_rep": [["RepaymentsOfDebt"]],
        "eq_iss": [[EQ], [CVPREF]], "buyback": [[BUYBACK]]}),
]

TITLE = "하이퍼스케일러 다섯 곳의 조달 (SEC 공시)"
NOTICE = ("이 사이트의 규칙 점검에 쓰지 않는 참고 자료다. 공시 숫자를 분기로 나눠 더한 산술이고, 단계·점수가 없으며 "
          "금리를 예측하지 않는다.")
COMPUTED_NOTICE = "분기·TTM·합계·비율은 macro-regime-check가 SEC EDGAR XBRL 공시로 계산한 값이다."
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
                   "not_consecutive": "4분기 연속 아님", "calc": "계산 오류"}


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


def tags_of(company):
    seen = []
    for parts in company[4].values():
        for alts in parts:
            for t in alts:
                if t not in seen:
                    seen.append(t)
    return seen


def fetch_all(ua, today, budget=BUDGET, opener=None, clock=time.monotonic, sleep=time.sleep):
    """(got {CIK: {태그: 사실 목록([] = 404)}}, 실패 코드 또는 None, 요청 수). 연락처가 없으면 요청 0번. 하나라도 실패하면
    거기서 멈춘다 — 이번 숫자는 쓰지 않는다."""
    if not ua:
        return {}, "no_ua", 0
    got, n, last = {}, 0, None
    deadline = clock() + budget
    for c in COMPANIES:
        for tag in tags_of(c):
            if last is not None:
                wait = GAP - (clock() - last)
                if wait > 0:
                    sleep(wait)
            if deadline - clock() <= 1:
                return got, "budget", n
            last = clock()
            n += 1
            try:
                js = fetch(c[2], tag, ua, deadline, clock, opener)
            except FetchError as e:
                return got, e.code, n
            got.setdefault(c[2], {})[tag] = trim(js, today) if js else []
    return got, None, n


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
        out["ttm_prev"] = {"ratio": p["ratio"], "fcf": p["fcf"], "from": p["from"], "to": p["to"]}
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


def _retrieved_text(retrieved):
    d = datetime.date.fromisoformat(retrieved)
    return f"{ai._MONTHS[d.month - 1]} {d.day}, {d.year}"


def sources_of(retrieved=None):
    s = {"series": "EDGAR", "name": "U.S. Securities and Exchange Commission", "url": DOC_URL, "licence": "public"}
    if retrieved:
        s["citation"] = f"{SOURCE_LINE}. Retrieved {_retrieved_text(retrieved)}."
    return [s]


def present(core, retrieved, key="funding"):
    line, extra, detail = texts(core["values"])
    return {"key": key, "name": TITLE, "date": core["date"], "values": core["values"], "retrieved": retrieved,
            "line": line, "extra": extra, "detail": detail, "notices": [COMPUTED_NOTICE], "sources": sources_of(retrieved)}


# ---------- 직전 파일 ----------

def _known_tags():
    return {t for c in COMPANIES for t in tags_of(c)}


_TTM = {**{k: "num?" for k in ITEMS}, "fcf": "num?", "ratio": "num?", "fcf_l": "num?", "debt_net": "num?",
        "eq_net": "num?", "from": "day", "to": "day"}
_PREV = {"ratio": "num?", "fcf": "num?", "from": "day", "to": "day"}
_TOT = {"n": "int", "of": "int", **{f: "num?" for f in TOTAL_FIELDS}, "ratio": "num?", "over": "int", "fcf_prev": "num?",
        "last_q": "day"}
_ROW = {"q": "day", **{k: "num?" for k in ITEMS}}
_KIND = ai._KIND


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
    """values 꼴 검사 — 정해 둔 키·꼴·회사 차례·태그 이름만(직전 파일 검사)."""
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


def core_of(item):
    """칸(dict) → (core, 받은 날) 또는 None(없거나 꼴이 어긋남)."""
    try:
        vals = item["values"]
        ok = ai._is_day(item["date"]) and ai._is_day(item["retrieved"]) and values_ok(vals) \
            and item["date"] == vals["total"]["last_q"]
        if ok:
            texts(vals)
    except (KeyError, TypeError, IndexError, AttributeError, ValueError):
        return None
    if not ok:
        return None
    return {"date": item["date"], "values": json.loads(json.dumps(vals))}, item["retrieved"]


def previous(out):
    try:
        with open(os.path.join(out, FILE), encoding="utf-8") as f:
            js = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(js, dict) or js.get("schema") != SCHEMA or not isinstance(js.get("items"), dict):
        return None
    it = js["items"].get("funding")
    return it if isinstance(it, dict) else None


def item_ok(core, prev, today, key="funding"):
    old = core_of(prev) if prev else None
    if old and core["date"] < old[0]["date"]:
        raise ItemError("older")
    same = old and json.loads(json.dumps(old[0])) == json.loads(json.dumps(core))
    retrieved = old[1] if same else today.isoformat()
    return {"ok": True, "stale": False, "error": None, "failed_since": None, **present(core, retrieved, key)}


def item_failed(code, prev, today, key="funding"):
    since = prev.get("failed_since") if prev and ai._is_day(prev.get("failed_since")) else today.isoformat()
    old = core_of(prev) if prev else None
    if old:
        return {"ok": False, "stale": True, "error": REASONS[code], "failed_since": since, **present(*old, key)}
    return {"ok": False, "stale": False, "error": REASONS[code], "failed_since": since, "key": key, "name": TITLE,
            "sources": sources_of()}


def build(result, prev, now):
    """result = core 또는 ItemError → 산출물 dict."""
    today = now.date()
    if not isinstance(result, ItemError):
        try:
            it = item_ok(result, prev, today)
        except ItemError as e:
            it = item_failed(e.code, prev, today)
    else:
        it = item_failed(result.code, prev, today)
    return {"schema": SCHEMA, "generated_at": now.isoformat(timespec="seconds"), "notice": NOTICE,
            "order": ["funding"], "items": {"funding": it}}


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


def guarded(result, prev, now, ua):
    """build + 연락처 검사. 섞였으면 사유 'leak'으로 직전 값과 다시, 그래도 섞였으면 직전 값 없이(사유만). 그래도면 None."""
    for res, pv in ((result, prev), (ItemError("leak"), prev), (ItemError("leak"), None)):
        data = build(res, pv, now)
        if not data_leaks(data, ua):
            return data
    return None


def main(argv=None, opener=None, now=None, clock=time.monotonic, sleep=time.sleep, env=None):
    ap = argparse.ArgumentParser(description="SEC EDGAR XBRL 공시 → 하이퍼스케일러 조달 참고 자료(<out>/sec.json)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    ua = user_agent(env)
    got, code, n = fetch_all(ua, now.date(), BUDGET, opener, clock, sleep)
    result = ItemError(code) if code else None
    if result is None:
        try:
            result = compute(got)
        except ItemError as e:
            result = e
        except Exception as e:                  # 계산 쪽 뜻밖의 오류도 실패로(예외 이름만)
            say(f"[sec_fetch] 계산 오류: {type(e).__name__}", ua, err=True)
            result = ItemError("format")
    data = guarded(result, previous(out), now, ua)
    if data is None:                            # 정해 둔 글에도 섞였다 — 아무것도 쓰지 않는다
        say(f"[sec_fetch] {FILE}를 쓰지 않음: {REASONS['leak']}", ua, err=True)
        return 1
    it = data["items"]["funding"]
    # 공개 저장소의 Actions 로그 — 날짜·요청 수·정해 둔 사유만(값·머리글·연락처는 찍지 않는다)
    if it["ok"]:
        say(f"[sec_fetch] funding {it['date']} 기준 · 요청 {n}번", ua)
    else:
        kept = f" — 직전 값({it['date']} 기준) 유지" if it["stale"] else ""
        say(f"SEC 조달 참고 받지 못함: {it['error']}{kept} · 요청 {n}번", ua, warn=True)
    try:
        if differs(out, data):
            write(out, data, ua)
    except ItemError:
        say(f"[sec_fetch] {FILE}를 쓰지 않음: {REASONS['leak']}", ua, err=True)
        return 1
    except OSError as e:
        say(f"[sec_fetch] {FILE}를 쓰지 못함: {type(e).__name__}", ua, err=True)
        return 1
    return 0 if it["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
