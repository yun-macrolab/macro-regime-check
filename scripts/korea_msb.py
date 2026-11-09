"""통화안정증권 경쟁입찰 결과 — 한국은행 '공개시장운영 공지'의 결과 공고에서 숫자·날짜·고정 낱말만 꺼낸다(2026-11-09).

korea_market.build가 'msb' 묶음으로 부른다(상태·마지막 성공 자료를 따로 갖는다).
  목록  /portal/singl/newsData/listCont.do — 공개시장운영 공지(menuNo=200295)를 제목 '통화안정증권 경쟁입찰 실시 결과'로 찾은
        HTML 조각(화면의 목록이 스크립트로 불러오는 것과 같은 요청). 검색이 '실시 정보'(예정) 공고도 함께 돌려줘 결과는 그 절반이다.
  상세  /portal/bbs/P0001773/view.do?nttId=…&menuNo=200295 — 본문(div.dbdata)의 짧은 글 한 쪽
읽는 것: 입찰일(목록 제목·본문 첫 줄 — 요일까지 맞춰 본다), 만기(n일물·n년물), 발행예정액, 응찰액·응찰기관수, 낙찰액, 낙찰금리
(1년 미만 할인채는 '낙찰할인율', 1년 이상은 '낙찰수익률' — 만기와 낱말이 어긋나면 버린다). 응찰금리 범위·낙찰기관수·부분낙찰률(없음·n%·'0~60%' 같은 범위)은
맞춰 보는 데만 쓰고(낙찰금리가 응찰금리 범위 안, 낙찰기관 ≤ 응찰기관, 낙찰액 ≤ 응찰액) 내보내지 않는다.
종목 번호·담당자·원격 문구는 내보내지 않는다. 금액은 공고의 조원(소수 둘째 자리) → 억원 정수.
응찰률은 이 사이트의 계산값(응찰액 ÷ 발행예정액 — 둘 다 0.01조원 단위로 반올림된 공고 값이라 근사).
형식이 다르면 고정 문구의 ValueError를 낸다 — korea_market.skip_reason이 SKIP_REASONS로 공개 사유 코드로 바꾼다.
이용 조건: 한국은행 홈페이지 저작권 보호방침(출처 표시, 원문은 직접·심층 링크) — 옮기는 것은 입찰 결과 숫자뿐이고
화면은 출처(한국은행)·원문 링크·'옮긴 값과 계산값' 구분을 함께 싣는다. robots.txt는 /portal/을 허용한다.
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

LIST_UNIT = 200          # 목록 한 번에 받는 행 수 — 결과·정보 공고가 반씩이라 결과 약 100건(주 두 번, 한 해 치쯤), 약 210KB(2026-11-09 실측)
MAX_ROWS = 110           # 저장하는 결과 수
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


def body_lines(raw):
    """상세 쪽의 제목(h2.subject)과 본문(div.dbdata) 글 줄. 본문 칸이 정확히 하나가 아니면 형식이 바뀐 것."""
    t = raw.decode("utf-8")
    bodies = re.findall(r'<div class="dbdata">(.*?)</div>', t, flags=re.S)
    subjects = re.findall(r'<h2 class="subject">(.*?)</h2>', t, flags=re.S)
    if len(bodies) != 1 or len(subjects) != 1: raise ValueError("msb field changed")
    # 줄은 문단·줄바꿈 태그로만 나눈다 — 글자마다 <span>이 끼인 공고가 있다(2026-03-16 결과: '부분낙찰률 : 60%'가 글자 단위 서식)
    block = re.sub(r"<(?:br|/?p|/?div|/?li)\b[^>]*>", "\n", re.sub(r"<!--.*?-->", "", bodies[0], flags=re.S), flags=re.I)
    text = html.unescape(re.sub(r"<[^>]*>", "", block))
    lines = [" ".join(x.split()) for x in text.split("\n")]
    subject = " ".join(html.unescape(re.sub(r"<[^>]*>", " ", subjects[0])).split())
    return subject, [x for x in lines if x]


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


def to_read(links, prev_ids):
    """아직 없는 공고(새 것부터 READ_NEW개) 먼저, 이미 읽은 가장 새 공고 REREAD개 다시 읽기는 끝에 —
    시간 예산이 모자라면 다시 읽기가 not_tried로 빠지고 전에 읽은 값이 남는다."""
    fresh = [l for l in links if l[0] not in prev_ids][:READ_NEW]
    again = [l for l in links if l[0] in prev_ids][:REREAD]
    return fresh + again


def _good(r):
    return (isinstance(r, dict) and isinstance(r.get("id"), str) and re.fullmatch(r"[0-9]{1,12}", r["id"])
            and isinstance(r.get("date"), str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["date"])
            and isinstance(r.get("tenor"), str))


def merge(got, previous):
    """전에 읽은 결과 + 새로 읽은 결과(같은 번호면 새로 읽은 것). 같은 입찰일·만기의 공고가 둘이면(정정 공고) 번호가 큰(나중) 것.
    새 것부터, 최근 MAX_ROWS건."""
    by_id = {}
    for r in list(previous or []) + list(got):
        if _good(r): by_id[r["id"]] = r
    by_auction = {}
    for r in by_id.values():
        key = (r["date"], r["tenor"])
        if key not in by_auction or int(r["id"]) > int(by_auction[key]["id"]): by_auction[key] = r
    return sorted(by_auction.values(), key=lambda r: (r["date"], int(r["id"])), reverse=True)[:MAX_ROWS]


def latest_date(rows):
    return max((r["date"] for r in rows or [] if _good(r)), default="")


def summary(rows, today):
    """화면용 계산값 — 달마다 이 사이트가 읽은 결과 공고의 합(최근 4개월, 이번 달 포함).
    저장분이 그달 1일 앞부터 있을 때만 그달을 싣는다(처음 몇 번의 실행처럼 그달 앞쪽이 아직 없으면 합이 작게 보이지 않게).
    못 읽은 공고가 있는 달은 그만큼 빠진다 — 화면이 '읽은 공고 n건 기준'으로 적는다."""
    good = [r for r in rows or [] if _good(r) and all(type(r.get(k)) is int for k in ("offered_100m", "bids_100m", "awarded_100m"))]
    if not good: return {"months": []}
    first = min(r["date"] for r in good)
    out = []
    y, m = today.year, today.month
    for _ in range(4):
        month = f"{y:04d}-{m:02d}"
        if first < month + "-01":
            these = [r for r in good if r["date"].startswith(month)]
            out.append({"month": month, "count": len(these),
                        "offered_100m": sum(r["offered_100m"] for r in these),
                        "bids_100m": sum(r["bids_100m"] for r in these),
                        "awarded_100m": sum(r["awarded_100m"] for r in these),
                        "short": sum(r["bids_100m"] < r["offered_100m"] for r in these)})
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return {"months": out}
