"""통화안정증권 경쟁입찰 결과 — 한국은행 '공개시장운영 공지'의 결과 공고에서 숫자·날짜·고정 낱말만 꺼낸다(2026-11-09).

korea_market.build가 'msb' 묶음으로 부른다(상태·마지막 성공 자료를 따로 갖는다).
  목록  /portal/singl/newsData/listCont.do — 공개시장운영 공지(menuNo=200295)를 제목 '통화안정증권 경쟁입찰 실시 결과'로 찾은
        HTML 조각(화면의 목록이 스크립트로 불러오는 것과 같은 요청). 조각은 공고마다 같은 행을 두 번 싣는다 — 200행이면 결과 100건.
  상세  /portal/bbs/P0001773/view.do?nttId=…&menuNo=200295 — 본문(div.dbdata)의 짧은 글 한 쪽
읽는 것: 입찰일(목록 제목·본문 첫 줄 — 요일까지 맞춰 본다), 만기(n일물·n년물), 발행예정액, 응찰액·응찰기관수, 낙찰액, 낙찰금리
(1년 미만 할인채는 '낙찰할인율', 1년 이상은 '낙찰수익률' — 만기와 낱말이 어긋나면 버린다). 응찰금리 범위·낙찰기관수·부분낙찰률(없음·n%·'0~60%' 같은 범위)은
맞춰 보는 데만 쓰고(낙찰금리가 응찰금리 범위 안, 낙찰기관 ≤ 응찰기관, 낙찰액 ≤ 응찰액) 내보내지 않는다.
종목 번호·담당자·원격 문구는 내보내지 않는다. 금액은 공고의 조원(소수 둘째 자리) → 억원 정수.
응찰률은 이 사이트의 계산값(응찰액 ÷ 발행예정액 — 둘 다 0.01조원 단위로 반올림된 공고 값이라 근사).
형식이 다르면 고정 문구의 ValueError를 낸다 — korea_market.skip_reason이 SKIP_REASONS로 공개 사유 코드로 바꾼다.
이용 조건(회색 지대): 한국은행 홈페이지 저작권 보호방침은 제공대상 공공데이터 목록에 없는 정보를 직접·심층 링크로 이용하게 하고
(2항), 그 밖의 방법은 사전 협의·승인을 요구한다(3항). 이 공고는 그 목록에서 확인하지 못했고 승인을 받지 않았다 — 공고 문장이 아니라
입찰 결과 숫자(사실)만 옮기고, 화면은 출처(한국은행)·공고마다 원문 링크·'옮긴 값과 계산값' 구분을 함께 싣는다(국고채 발행공고 PDF에서
예정액만 옮기는 것과 같은 방식). 한국은행이 요청하면 내린다. robots.txt는 /portal/을 허용한다.
"""
import datetime as dt
import html
import re
import urllib.parse
from decimal import Decimal
from html.parser import HTMLParser

BOK = "https://www.bok.or.kr"
MENU = "200295"
QUERY = "통화안정증권 경쟁입찰 실시 결과"
LIST_CONT = BOK + "/portal/singl/newsData/listCont.do"
# 사람이 보는 목록(같은 검색어) — 화면의 출처 링크
LIST_PAGE = BOK + "/portal/singl/newsData/list.do?" + urllib.parse.urlencode(
    {"menuNo": MENU, "searchCnd": "2", "searchKwd": QUERY})
VIEW = BOK + "/portal/bbs/P0001773/view.do"

LIST_UNIT = 200          # 목록 한 번에 받는 행 수 — 같은 행이 두 번씩이라 결과 100건(주 두 번, 한 해 치쯤), 약 210KB(2026-11-09 실측)
MAX_ROWS = 110           # 저장하는 결과 수 — 다 차면 가장 오래된 입찰일보다 앞선 공고는 새로 읽지 않는다(to_read — 읽어도 merge가 버린다)
READ_NEW = 20            # 한 번 실행에서 새로 읽는 공고 수(가장 새 것부터, 한 건 약 2초) — 처음 다섯 번쯤의 실행이 한 해 치를 채운다
REREAD = 2               # 이미 읽은 가장 새 공고 중 다시 읽는 수(정정 확인) — 새 공고 뒤에, 시간이 모자라면 not_tried
STALE_DAYS = 21          # 마지막 입찰이 이보다 묵으면 stale(평소 주 두 번, 설·추석 연휴 간격 14일 — 2025-09-29 → 10-13)
WEEKDAYS = "월화수목금토일"

# 숫자는 ASCII만(re.A) — 다른 문자 체계의 숫자도 int()·Decimal()은 받아 준다
TITLE = re.compile(r"(\d{4})\.(\d{1,2})\.(\d{1,2})\(([월화수목금토일])\)\s*통화안정증권\s*경쟁입찰\s*실시\s*결과(?:\s*\(정정\))?", re.A)
_AMT = r"(\d{1,2}\.\d{1,2})\s*조원"
_RATE = r"(\d{1,2}(?:\.\d{1,4})?)"
FIELDS = {
    "offered": re.compile(r"발행예정액\s*:\s*" + _AMT, re.A),
    "bids": re.compile(r"응찰액\s*\(\s*응찰기관수\s*\)\s*:\s*" + _AMT + r"\s*\(\s*(\d{1,3})\s*개사\s*\)", re.A),
    "range": re.compile(r"응찰금리\s*:\s*" + _RATE + r"(?:\s*~\s*" + _RATE + r")?\s*%", re.A),
    "awarded": re.compile(r"낙찰액\s*\(\s*낙찰기관수\s*\)\s*:\s*" + _AMT + r"\s*\(\s*(\d{1,3})\s*개사\s*\)", re.A),
    "rate": re.compile(r"낙찰(할인율|수익률)\s*:\s*" + _RATE + r"\s*%", re.A),
}
TENOR = re.compile(r"-\s*(\d{1,3})\s*(일|년)물\s*\(", re.A)
PARTIAL = re.compile(r"부분낙찰\s*없음|부분낙찰[률율]\s*:\s*(\d{1,3})(?:\s*~\s*(\d{1,3}))?\s*%", re.A)

# 공개 사유 코드(korea_market.SKIP_REASONS에 합쳐진다)
SKIP_REASONS = {"msb date mismatch": "date_mismatch", "msb field changed": "field_changed",
                "msb tenor changed": "tenor_changed", "msb rate kind": "rate_kind",
                "msb outside range": "out_of_range", "future msb result": "future"}


def list_url():
    return LIST_CONT + "?" + urllib.parse.urlencode(
        {"pageIndex": 1, "targetDepth": 4, "menuNo": MENU, "syncMenuChekKey": 1,
         "searchCnd": 2, "searchKwd": QUERY, "pageUnit": LIST_UNIT})


def view_url(ident):
    if not re.fullmatch(r"[0-9]{1,12}", ident): raise ValueError("invalid notice id")
    return VIEW + "?" + urllib.parse.urlencode({"nttId": ident, "menuNo": MENU})


def title_date(text):
    """'2026.11.6(금) 통화안정증권 경쟁입찰 실시 결과' → 날짜. 꼴이 다르거나 요일이 맞지 않으면 None."""
    t = TITLE.fullmatch(" ".join(text.split()))
    if not t: return None
    try: day = dt.date(int(t[1]), int(t[2]), int(t[3]))
    except ValueError: return None
    return day if WEEKDAYS[day.weekday()] == t[4] else None


class _Titles(HTMLParser):
    """목록 조각에서 class="title"인 <a>의 href와 글자만(주석·스크립트는 글자로 치지 않는다)."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.cur, self.skip = [], None, 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"): self.skip += 1
        a = dict(attrs)
        if tag == "a" and "title" in (a.get("class") or "").split(): self.cur = [a.get("href") or "", []]

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip: self.skip -= 1
        if tag == "a" and self.cur is not None:
            self.links.append((self.cur[0], " ".join("".join(self.cur[1]).split()))); self.cur = None

    def handle_data(self, data):
        if self.cur is not None and not self.skip: self.cur[1].append(data)


def result_links(raw):
    """목록 조각 → [(공고 번호, 입찰일 ISO)](목록 순서 = 새 것부터, 같은 번호는 한 번). 제목 꼴이 맞는 결과 공고만 —
    '실시 정보'(예정 공고)·다른 공지는 뺀다. 하나도 없으면 목록 형식이 바뀐 것."""
    p = _Titles(); p.feed(raw.decode("utf-8"))
    out = []
    for href, title in p.links:
        m = re.fullmatch(r"/portal/bbs/P0001773/view\.do\?nttId=([0-9]{1,12})(?:&[^\s\"'<>]*)?", html.unescape(href))
        day = title_date(title)
        if m and day and m[1] not in [o[0] for o in out]:
            out.append((m[1], day.isoformat()))
    if not out: raise ValueError("no msb notices")
    return out


class _Body(HTMLParser):
    """상세 쪽에서 h2.subject 글과 div.dbdata 글 — 본문 칸은 안쪽 <div>를 세어 그 칸이 닫힐 때까지 읽는다
    (편집기가 본문에 '<div><br></div>'를 넣는다 — 2025-09 ~ 2026-11 공고 100건 중 8건, 지금은 모두 '문의' 줄 뒤).
    줄은 문단·줄바꿈 태그에서만 나눈다 — 글자마다 <span>이 끼인 공고가 있다(2026-03-16 결과). 주석·스크립트는 글로 치지 않는다."""
    BLOCK = {"p", "br", "div", "li", "tr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.bodies, self.subjects, self.depth, self.subj, self.skip = [], [], 0, None, 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"): self.skip += 1; return
        cls = (dict(attrs).get("class") or "").split()
        if self.depth:
            if tag == "div": self.depth += 1
            if tag in self.BLOCK: self.bodies[-1].append("\n")
        elif tag == "div" and "dbdata" in cls:
            self.depth = 1; self.bodies.append([])
        if tag == "h2" and "subject" in cls: self.subj = []

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            if self.skip: self.skip -= 1
            return
        if self.depth:
            if tag in self.BLOCK: self.bodies[-1].append("\n")
            if tag == "div": self.depth -= 1
        if tag == "h2" and self.subj is not None: self.subjects.append("".join(self.subj)); self.subj = None

    def handle_data(self, data):
        if self.skip: return
        if self.depth: self.bodies[-1].append(data)
        if self.subj is not None: self.subj.append(data)


def body_lines(raw):
    """상세 쪽의 제목(h2.subject)과 본문(div.dbdata) 글 줄. 본문 칸·제목이 정확히 하나가 아니면 형식이 바뀐 것."""
    p = _Body(); p.feed(raw.decode("utf-8")); p.close()
    if len(p.bodies) != 1 or len(p.subjects) != 1: raise ValueError("msb field changed")
    lines = [" ".join(x.split()) for x in "".join(p.bodies[0]).split("\n")]
    return " ".join(p.subjects[0].split()), [x for x in lines if x]


def _one(pattern, text):
    found = pattern.findall(text)
    if len(found) != 1: raise ValueError("msb field changed")
    return found[0]


def _won(trillion):
    """'0.60'(조원) → 6000(억원). 공고는 소수 둘째 자리까지라 억원 정수로 딱 떨어진다."""
    return int(Decimal(trillion) * 10000)


def parse_result(raw, ident, date, today):
    subject, lines = body_lines(raw)
    day = title_date(subject)
    if not lines or day is None or day.isoformat() != date or title_date(lines[0]) != day:
        raise ValueError("msb date mismatch")
    if day > today: raise ValueError("future msb result")
    text = " ".join(lines)
    tenors = TENOR.findall(text)
    if len(tenors) != 1: raise ValueError("msb tenor changed")
    n, unit = int(tenors[0][0]), tenors[0][1]
    if not ((unit == "일" and 7 <= n <= 546) or (unit == "년" and 1 <= n <= 10)): raise ValueError("msb tenor changed")
    offered = _won(_one(FIELDS["offered"], text))
    bids_s, bidders = _one(FIELDS["bids"], text)
    low_s, high_s = _one(FIELDS["range"], text)
    awarded_s, winners = _one(FIELDS["awarded"], text)
    kind, rate_s = _one(FIELDS["rate"], text)
    partial = PARTIAL.findall(text)
    if len(partial) != 1: raise ValueError("msb field changed")
    # 1년 미만은 할인채(낙찰할인율), 1년 이상은 이표채(낙찰수익률) — 어긋나면 다른 꼴의 공고다
    if (unit == "일") != (kind == "할인율"): raise ValueError("msb rate kind")
    bids, awarded, bidders, winners = _won(bids_s), _won(awarded_s), int(bidders), int(winners)
    low, rate = float(low_s), float(rate_s)
    high = float(high_s) if high_s else low
    p_lo, p_hi = partial[0]
    shares = [int(x) for x in (p_lo, p_hi) if x]
    if not (0 < offered <= 300_000 and 0 < awarded <= bids <= 3_000_000 and 1 <= winners <= bidders <= 300
            and 0 < low <= rate <= high < 20 and all(0 <= s <= 100 for s in shares) and shares == sorted(shares)):
        raise ValueError("msb outside range")
    return {"id": ident, "date": date, "tenor": f"{n}{unit}", "offered_100m": offered, "bids_100m": bids,
            "bidders": bidders, "awarded_100m": awarded, "rate_kind": "discount" if kind == "할인율" else "yield",
            "rate_pct": rate, "bid_cover_pct": round(bids / offered * 100, 1), "source_url": view_url(ident)}


def _ids(values):
    return {x for x in values if isinstance(x, str) and re.fullmatch(r"[0-9]{1,12}", x)}


def _replaced(r):
    return _ids(r.get("replaces") or []) if isinstance(r, dict) and isinstance(r.get("replaces"), list) else set()


def to_read(links, previous):
    """읽을 공고 — 아직 없는 공고(새 것부터 READ_NEW개) 먼저, 이미 읽은 가장 새 공고 REREAD개 다시 읽기는 끝에
    (시간 예산이 모자라면 다시 읽기가 not_tried로 빠지고 전에 읽은 값이 남는다).
    새로 읽지 않는 것: 정정 공고에 밀린 원 공고(저장된 행의 replaces — 읽어도 merge가 다시 버린다),
    저장분이 MAX_ROWS로 찼을 때 가장 오래된 입찰일보다 앞선 공고(읽어도 merge가 잘라 낸다)."""
    good = [r for r in previous or [] if _good(r)]
    seen = {r["id"] for r in good}
    replaced = set().union(*(_replaced(r) for r in good)) - seen
    floor = min(r["date"] for r in good) if len(good) >= MAX_ROWS else ""
    fresh = [l for l in links if l[0] not in seen and l[0] not in replaced and l[1] >= floor][:READ_NEW]
    again = [l for l in links if l[0] in seen][:REREAD]
    return fresh + again


def _good(r):
    return (isinstance(r, dict) and isinstance(r.get("id"), str) and re.fullmatch(r"[0-9]{1,12}", r["id"])
            and isinstance(r.get("date"), str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["date"])
            and isinstance(r.get("tenor"), str))


def _with_replaced(r, ids):
    r = dict(r); r.pop("replaces", None)
    ids = ids - {r["id"]}
    if ids: r["replaces"] = sorted(ids, key=int)[-10:]
    return r


def merge(got, previous):
    """전에 읽은 결과 + 새로 읽은 결과(같은 번호면 새로 읽은 것 — 전에 적어 둔 replaces는 잇는다).
    같은 입찰일·만기의 공고가 둘이면(정정 공고) 번호가 큰(나중) 것을 두고, 밀린 번호를 그 행의 replaces에 적는다
    (to_read가 다시 읽지 않게). 새 것부터, 최근 MAX_ROWS건."""
    by_id = {}
    for r in list(previous or []) + list(got):
        if _good(r): by_id[r["id"]] = _with_replaced(r, _replaced(by_id.get(r["id"])) | _replaced(r))
    by_auction = {}
    for r in by_id.values():
        key = (r["date"], r["tenor"])
        cur = by_auction.get(key)
        if cur is None: by_auction[key] = r; continue
        win, lose = (r, cur) if int(r["id"]) > int(cur["id"]) else (cur, r)
        by_auction[key] = _with_replaced(win, _replaced(win) | _replaced(lose) | {lose["id"]})
    return sorted(by_auction.values(), key=lambda r: (r["date"], int(r["id"])), reverse=True)[:MAX_ROWS]


def latest_date(rows):
    return max((r["date"] for r in rows or [] if _good(r)), default="")


def summary(rows, today):
    """화면용 계산값 — 달마다 이 사이트가 읽은 결과 공고의 합(오늘이 속한 달부터 거꾸로 네 달 중 아래 조건을 맞는 달).
    - 저장분이 그달 1일 앞부터 있을 때만 싣는다(처음 몇 번의 실행처럼 그달 앞쪽이 아직 없으면 합이 작게 보이지 않게).
    - 마지막으로 읽은 입찰의 달보다 뒤의 달은 싣지 않는다(월초 입찰 전이나 수집이 멈춘 동안 '0회'를 보이지 않게).
    - 오늘이 속한 달은 아직 끝나지 않았다 — through(그달 마지막으로 읽은 입찰일)를 붙여 화면이 'n일까지'로 적는다.
    못 읽은 공고가 있는 달은 그만큼 빠진다 — 화면이 '읽은 공고'로 적는다."""
    good = [r for r in rows or [] if _good(r) and all(type(r.get(k)) is int for k in ("offered_100m", "bids_100m", "awarded_100m"))]
    if not good: return {"months": []}
    first, last = min(r["date"] for r in good), max(r["date"] for r in good)
    out = []
    y, m = today.year, today.month
    for _ in range(4):
        month = f"{y:04d}-{m:02d}"
        if first < month + "-01" and month <= last[:7]:
            these = [r for r in good if r["date"].startswith(month)]
            row = {"month": month, "count": len(these),
                   "offered_100m": sum(r["offered_100m"] for r in these),
                   "bids_100m": sum(r["bids_100m"] for r in these),
                   "awarded_100m": sum(r["awarded_100m"] for r in these),
                   "short": sum(r["bids_100m"] < r["offered_100m"] for r in these)}
            if (y, m) == (today.year, today.month): row["through"] = max(r["date"] for r in these)
            out.append(row)
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return {"months": out}
