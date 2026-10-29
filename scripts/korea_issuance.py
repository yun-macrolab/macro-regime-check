#!/usr/bin/env python3
"""국고채 발행계획·바이백·교환 — 재정경제부 공개 보도자료와 국채 입찰 결과 공고에서 숫자·날짜·고정 낱말만 꺼낸다.

korea_market.build가 두 자료 묶음으로 부른다(각자 상태·마지막 성공 자료를 갖는다).
  ktb_plans  월별 '국고채 … 발행 계획' 보도자료 PDF(첨부): 경쟁입찰 총액·만기별 금액·전월 실적·보도자료에 적힌
             전월/당초 대비 변화(숫자만)·그달 매입(바이백)·교환 계획 금액과 날짜
  ktb_ops    입찰 결과 게시판의 '국고채 매입 입찰 결과'·'국고채 교환 입찰 결과' 첨부 PDF: 입찰일·입찰금액·응찰금액·응찰률·낙찰금액
원격 문구(제목·본문·종목명·담당자)는 내보내지 않는다. 형식이 다르면 고정 문구의 ValueError를 낸다 —
korea_market.skip_reason이 SKIP_REASONS로 공개 사유 코드로 바꾼다.
연간 발행 한도는 표(ANNUAL_LIMITS)로 둔다 — 연간 계획 보도자료에서 사람이 옮기고 출처 주소·날짜를 함께 적는다.
그해 한도가 표에 없거나 1월부터 빠진 달이 있으면 한도 대비 비율을 내지 않는다(추정하지 않음).
"""
import datetime as dt
import io
import re
import urllib.parse
from html.parser import HTMLParser

MOFE = "https://mofe.go.kr"
PRESS_BBS, PRESS_MENU = "MOSFBBS_000000000028", "4010100"
# 보도자료 게시판 제목 검색. '발행 계획' — 서버가 띄어쓰기를 지우고 맞추므로 '발행계획'도 걸리고, 2022년 이후 월별 계획의
# 제목 꼴(… 외평채 발행 계획 / … 경쟁입찰 n조원 … 발행 계획 / 'yyyy년 m월 국고채 발행계획 및 …')이 다 온다. 월별 계획이 아닌 것은 plan_links가 거른다.
PLAN_LIST = MOFE + "/nw/nes/nesdta.do?" + urllib.parse.urlencode(
    {"searchBbsId1": PRESS_BBS, "menuNo": PRESS_MENU, "searchCondition": "1", "searchKeyword": "발행 계획"})
# 목록은 쪽마다 10건 — 둘째 쪽부터는 pageIndex를 붙인다(목록의 쪽 링크 '?pageIndex=2'·fn_egov_link_page와 같은 칸, 2026-10-28 실측)


def plan_list_url(page=1):
    if type(page) is not int or not 1 <= page <= 9: raise ValueError("invalid page")
    return PLAN_LIST if page == 1 else PLAN_LIST + "&" + urllib.parse.urlencode({"pageIndex": page})


PRESS_DETAIL = MOFE + "/nw/nes/detailNesDtaView.do"
FILE_DOWN = MOFE + "/com/cmm/fms/FileDown.do"
# 입찰 결과 게시판(korea_market.RESULTS와 같은 곳)의 제목 검색 — 매입·교환 결과만
RESULTS = "https://mofe.go.kr/st/fnancstats/ktb50201.do?bbsId=MOSFBBS_000000000049&menuNo=6050300"
RESULT_DETAIL = "https://mofe.go.kr/st/fnancstats/updateTbFnancstatsView.do"
OPS = {"buyback": "국고채 매입 입찰 결과", "exchange": "국고채 교환 입찰 결과"}
OPS_LABEL = {"buyback": "매입", "exchange": "교환"}

MAX_PLANS = 12           # 화면에 두는 달 수(지난 달은 전에 읽은 값을 둔다)
MAX_OPS = 12             # 매입·교환 결과 행 수
READ_PLANS = 6           # 한 번 실행에서 새로 읽는 보도자료 수(가장 새 것 + 아직 없는 것) — 시간 예산 안에서
READ_OPS = 3             # 종류별로 새로 읽는 결과 공고 수
TENORS = ("2", "3", "5", "10", "20", "30", "50")
LONG = ("20", "30", "50")
LINKER = "물가채"

# 연간 국고채 발행 한도(억원) — 그해 '국고채 발행계획' 보도자료에서 옮긴다. 추경 등으로 수정 계획('…국고채 발행계획 수정')이
# 나오면 그 보도자료로 바꾼다 — 코드는 수정 계획을 찾지 않는다(README 한국 시장 절의 손볼 일).
ANNUAL_LIMITS = {
    2026: {"limit_100m": 2_257_000, "published": "2025-12-26",
           "source_url": PRESS_DETAIL + "?" + urllib.parse.urlencode(
               {"searchBbsId1": PRESS_BBS, "searchNttId1": "MOSF_000000000076306", "menuNo": PRESS_MENU})},
}

# 공개 사유 코드(korea_market.SKIP_REASONS에 합쳐진다)
SKIP_REASONS = {"ambiguous attachment": "attachment", "unexpected attachment": "pdf_shape",
                "missing plan total": "no_total", "plan month mismatch": "month_mismatch",
                "plan field changed": "field_changed", "ambiguous plan fields": "ambiguous_fields",
                "plan sum mismatch": "sum_mismatch", "plan outside range": "out_of_range",
                "missing release date": "no_date", "op kind mismatch": "kind_mismatch",
                "op field changed": "field_changed", "op date mismatch": "date_mismatch",
                "op outside range": "out_of_range", "future operation": "future"}
# 매입·교환 결과 목록 한 종류에서 공고를 하나도 못 찾았을 때(목록 형식 변경 등) — 공고 번호 대신 종류 이름과 함께 남긴다
NO_NOTICES = "no_notices"


class Anchors(HTMLParser):
    """<a>의 href·title·글자만 모은다(스크립트는 실행하지 않음)."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.cur = [], None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            a = dict(attrs); self.cur = [a.get("href") or "", a.get("title") or "", []]

    def handle_data(self, data):
        if self.cur is not None: self.cur[2].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.cur is not None:
            self.links.append((self.cur[0], self.cur[1], " ".join("".join(self.cur[2]).split()))); self.cur = None


def anchors(raw):
    p = Anchors(); p.feed(raw.decode("utf-8")); return p.links


def press_url(ident):
    if not re.fullmatch(r"MOSF_[0-9]{1,15}", ident): raise ValueError("invalid notice id")
    return PRESS_DETAIL + "?" + urllib.parse.urlencode({"searchBbsId1": PRESS_BBS, "searchNttId1": ident, "menuNo": PRESS_MENU})


def result_url(ident):
    if not re.fullmatch(r"MOSF_[0-9]{1,15}", ident): raise ValueError("invalid notice id")
    return RESULT_DETAIL + "?" + urllib.parse.urlencode({"searchSn": ident, "type": "ktb50201", "bbsId": "MOSFBBS_000000000049", "menuNo": "6050300"})


def ops_list_url(kind):
    return RESULTS + "&" + urllib.parse.urlencode({"searchCondition": "1", "searchKeyword": OPS[kind]})


def plan_links(raw):
    """보도자료 목록 → [(번호, (연도 두 자리, 월))]. 월별 국고채 발행계획만(경과물 모집·개인투자용·외평채 단독 계획은 뺀다).
    제목 꼴: 'yy.m월 국고채, …', 'yy.m월 국고채 경쟁입찰 n조원, … 발행 계획', 'yyyy년 m월 국고채 발행계획 및 …'.
    같은 달이 둘이면(정정 보도) 목록에서 먼저 나온(새) 것 하나만 — 다른 꼴의 PDF는 월 대조(month_mismatch)·양식 검사가 거른다.
    (새 것이 정정 사항만 적은 한 장이면 원래 보도자료를 가리게 되지만, 그 PDF는 총액·만기 합 검사에서 소리 나게 실패한다 — 드물어 그대로 둔다)"""
    out = []
    for href, _, title in anchors(raw):
        m = re.fullmatch(r"javascript:fn_egov_select\('(MOSF_[0-9]{1,15})'\);", href)
        t = re.match(r"[‘'’]?(?:20)?(\d{2})(?:\.|년\s*)(\d{1,2})월\s*국고채", title)
        if m and t and re.search(r"발행\s*계획", title) and not re.search(r"모집|경과물|개인투자용", title) \
                and 1 <= int(t[2]) <= 12 and m[1] not in [o[0] for o in out] \
                and (int(t[1]), int(t[2])) not in [o[1] for o in out]:
            out.append((m[1], (int(t[1]), int(t[2]))))
    if not out: raise ValueError("no plan notices")
    return out[:MAX_PLANS]


def page2_target(links, stored_months):
    """첫 쪽만으로 모자라 둘째 쪽을 읽어야 하면 그 이유가 된 달 (연도 두 자리, 2), 아니면 None.
    보고 연도 = (첫 쪽 가장 새 계획 달 − 한 달)의 해(1월 계획은 전년 12월 실적을 적으므로 전년). 그해 2월 계획만
    1월 실적(prev_actual)을 적는다 — 그 달이 첫 쪽에도 저장된 달에도 없고, 첫 쪽 가장 오래된 달이 그보다 늦을 때만.
    평소(2월부터 최근 달까지 저장됨)에는 None — 둘째 쪽을 읽지 않는다."""
    if not links: return None
    months = {ym for _, ym in links}
    yy, mm = max(months)
    target = (yy - 1 if mm == 1 else yy, 2)
    # 그 달이 첫 쪽에 있으면 가장 오래된 달이 그보다 늦지 않다 — 마지막 조건이 함께 거른다
    if f"{2000 + target[0]:04d}-02" in stored_months or min(months) <= target: return None
    return target


def join_links(first, second, oldest=None):
    """첫 쪽 링크 + 둘째 쪽 링크 중 번호도 달도 새 것만(같은 달이면 첫 쪽 — 새 보도). 최근 MAX_PLANS개.
    oldest(page2_target의 달)를 주면 둘째 쪽은 그 달부터만 — 더 오래된 계획은 보고 연도 합계에 쓰이지 않고
    처음 몇 번의 실행에서 시간 예산만 쓴다(실측: 한 건 7~8초, 묶음 60초)."""
    ids, months = {i for i, _ in first}, {ym for _, ym in first}
    return (list(first) + [l for l in second if l[0] not in ids and l[1] not in months
                           and (oldest is None or l[1] >= oldest)])[:MAX_PLANS]


def op_links(raw, kind):
    """입찰 결과 목록 → [(번호, 입찰일 ISO)]. 제목이 '…년도 제n차 국고채 매입(교환) 입찰 결과('yy.m.d.)'인 것만(외평채 매입은 뺀다)."""
    word = {"buyback": "매입", "exchange": "교환"}[kind]
    out = []
    for href, _, title in anchors(raw):
        m = re.fullmatch(r'javascript:fn_egov_updateView\("(MOSF_[0-9]{1,15})"\);', href)
        t = re.fullmatch(r"\d{4}년도\s*제\d{1,3}차\s*국고채\s*" + word + r"\s*입찰\s*결과\s*\([‘'’]?(\d{2})\.(\d{1,2})\.(\d{1,2})\.?\)", title)
        if m and t and m[1] not in [o[0] for o in out]:
            try: day = dt.date(2000 + int(t[1]), int(t[2]), int(t[3]))
            except ValueError: continue
            out.append((m[1], day.isoformat()))
    return out[:6]


def attachment_pdf_url(raw):
    """상세 화면의 첨부 중 PDF 하나의 내려받기 주소. 첨부 순서(fileSn)는 글마다 다르다 — 미리보기 링크의 제목(…pdf 파일 새 창 열림)으로 고른다."""
    found = set()
    for href, title, _ in anchors(raw):
        m = re.fullmatch(r"/com/synap/synapView\.do(?:;jsessionid=[\w.\-]{1,120})?\?atchFileId=(ATCH_[0-9]{1,20})&fileSn=([0-9]{1,3})", href)
        if m and title.strip().lower().endswith(".pdf 파일 새 창 열림"):
            found.add((m[1], m[2]))
    if len(found) != 1: raise ValueError("ambiguous attachment")
    atch, sn = found.pop()
    return FILE_DOWN + "?" + urllib.parse.urlencode({"atchFileId": atch, "fileSn": sn})


def pdf_text(raw, max_pages=12):
    if not raw.startswith(b"%PDF-"): raise ValueError("unexpected attachment")
    from pypdf import PdfReader
    pdf = PdfReader(io.BytesIO(raw))
    if pdf.is_encrypted or not 1 <= len(pdf.pages) <= max_pages: raise ValueError("unexpected attachment")
    return "\n".join(p.extract_text() or "" for p in pdf.pages)


def won(value, unit):
    """'1.5','조' → 15000(억원). '106,000','억' → 106000."""
    v = float(value.replace(",", ""))
    out = v * 10000 if unit == "조" else v
    if abs(out - round(out)) > 1e-6: raise ValueError("plan field changed")
    return int(round(out))


def near(year, month, m, d):
    """계획 달(year, month) 가까이의 m월 d일(연말·연초를 넘는 날짜도)."""
    base = dt.date(year, month, 15)
    cands = []
    for y in (year - 1, year, year + 1):
        try: cands.append(dt.date(y, m, d))
        except ValueError: pass
    if not cands: raise ValueError("plan field changed")
    best = min(cands, key=lambda c: abs((c - base).days))
    if abs((best - base).days) > 75: raise ValueError("plan outside range")
    return best.isoformat()


AMT = r"([\d,]+(?:\.\d+)?)(조|억)원"
DOWN, UP = ("축소", "감소", "감축", "감액"), ("확대", "증가", "증액")


def stated(matches):
    """[(금액, 단위, 낱말)] → 부호 붙은 억원 하나. 없으면 None, 값이 갈리면 거부."""
    values = {won(a, u) * (-1 if w in DOWN else 1) for a, u, w in matches}
    if len(values) > 1: raise ValueError("ambiguous plan fields")
    return values.pop() if values else None


def plan_section(s, word):
    """'N월국고채매입계획'·'N월국고채교환계획' 참고 절(다음 '참고n' 앞까지). 없으면 None."""
    m = re.search(r"참고\d{1,2}(?:참고\d{1,2})?\d{4}년\d{1,2}월국고채" + word + r"계획(.*?)(?=참고\d{1,2}|$)", s)
    return m[1] if m else None


def parse_plan_text(text, ident, ym, today):
    s = re.sub(r"\s+", "", text)
    yy, mm = ym
    heads = set(re.findall(r"□[’'‘]?(\d{2})년(\d{1,2})월([\d,]+)억원국고채경쟁입찰발행", s))
    if len(heads) != 1: raise ValueError("missing plan total")
    y2, m2, total = heads.pop()
    if (int(y2), int(m2)) != (yy, mm): raise ValueError("plan month mismatch")
    year, month, total = 2000 + yy, mm, int(total.replace(",", ""))
    if not 0 < total < 1_000_000: raise ValueError("plan outside range")
    sec = re.search(r"□[’'‘]?\d{2}년\d{1,2}월[\d,]+억원국고채경쟁입찰발행(.*?)(?=□|참고\d|$)", s)[1]
    amounts = {}
    for tenor, linker, amount in re.findall(r"매출되는(?:국고채(\d{1,2})년물|(물가연동국고채))([\d,]+)억", sec):
        key = LINKER if linker else tenor
        if key != LINKER and key not in TENORS: raise ValueError("plan field changed")
        if key in amounts: raise ValueError("ambiguous plan fields")
        amounts[key] = int(amount.replace(",", ""))
    if not amounts: raise ValueError("plan field changed")
    if sum(amounts.values()) != total: raise ValueError("plan sum mismatch")
    rel = re.search(r"배포(\d{4})\.(\d{1,2})\.(\d{1,2})\.", s)
    if not rel: raise ValueError("missing release date")
    published = dt.date(int(rel[1]), int(rel[2]), int(rel[3]))
    first = dt.date(year, month, 1)
    if published > today or not first - dt.timedelta(days=75) <= published <= first + dt.timedelta(days=31):
        raise ValueError("plan outside range")
    cut = s.find("연물별로는")
    if cut < 0: raise ValueError("plan field changed")
    lead = s[:cut]                         # 제목과 국고채 첫 문단(외평채·재정증권 문단은 그 뒤에 나온다)
    prev_month = 12 if month == 1 else month - 1
    found = []
    for n, a, u, w in re.findall(r"(?:전월보다|전월대비|(\d{1,2})월에비해)" + AMT + "(" + "|".join(DOWN + UP) + ")", lead):
        if n and int(n) != prev_month: raise ValueError("plan field changed")
        found.append((a, u, w))
    prev_change = stated(found)
    # '전월과 동일' 또는 'N월과 동일'(N = 전달, 2025-09 꼴) → 0. 다른 달이면 읽지 않는다
    if prev_change is None and ("전월과동일" in lead or str(prev_month) in re.findall(r"(?<!\d)(\d{1,2})월과동일", lead)):
        prev_change = 0
    # '당초(발행)(계획)((n조원))(대비|보다|에비해) n조원(을) 축소…' — 꼴이 달라 못 읽으면 None + unread 표시(멈추지 않는다)
    plan_change = stated(re.findall(r"당초(?:발행)?(?:계획)?(?:\([^()]{0,20}\))?(?:대비|보다|에비해)?" + AMT + "(?:을|를)?("
                                    + "|".join(DOWN + UP) + ")", lead))
    plan_change_unread = plan_change is None and "당초" in lead
    actual = None
    pm_year = year - 1 if month == 1 else year
    hits = set()
    for y, m, jo, eok in re.findall(r"(?:(\d{4})년)?(\d{1,2})월국고채발행규모는(?:(\d{1,3})조)?([\d,]+)억원", s):
        if int(m) != prev_month or (y and int(y) != pm_year): continue
        hits.add(int(jo or 0) * 10000 + int(eok.replace(",", "")))
    if len(hits) > 1: raise ValueError("ambiguous plan fields")
    if hits:
        value = hits.pop()
        if not 0 < value < 1_000_000: raise ValueError("plan outside range")
        actual = {"month": f"{pm_year:04d}-{prev_month:02d}", "amount_100m": value}
    def dates(sec_text):
        return sorted({near(year, month, int(m), int(d))
                       for m, d in re.findall(r"(?<![\d.])(\d{1,2})\.(\d{1,2})\.\([월화수목금토일]\)", sec_text)})
    buyback = None
    sec_bb = plan_section(s, "매입")
    if sec_bb is not None:
        amt = re.findall(r"□총([\d,]+)억원규모국고채매입계획", sec_bb)
        if len(amt) != 1: raise ValueError("plan field changed")
        buyback = {"amount_100m": int(amt[0].replace(",", "")), "dates": dates(sec_bb)}
    elif "국고채매입계획" in s or "매입(바이백)" in s:       # 본문에 매입이 적혔는데 참고 절이 없다 — '계획 없음'으로 두지 않는다
        # 본문 어디에든 '매입(바이백)'이 있으면 멈춘다(일부러 — 틀린 숫자보다 보이는 실패가 낫다)
        raise ValueError("plan field changed")
    exchange = None
    sec_ex = plan_section(s, "교환")
    if sec_ex is not None:
        body = re.search(r"□(.*?)교환을실시할계획(.*)", sec_ex)
        parts = re.findall(r"간([\d,]+)억원", body[1]) if body else []
        if not parts: raise ValueError("plan field changed")
        exchange = {"amount_100m": sum(int(p.replace(",", "")) for p in parts), "dates": dates(body[2])}
    elif "국고채교환계획" in s:
        raise ValueError("plan field changed")
    for item in (buyback, exchange):
        if item and not 0 < item["amount_100m"] < 1_000_000: raise ValueError("plan outside range")
    order = list(TENORS) + [LINKER]
    tenors = [{"tenor": k if k == LINKER else k + "년", "amount_100m": amounts[k]} for k in order if k in amounts]
    share = lambda keys: round(sum(amounts.get(k, 0) for k in keys) / total * 100, 1)
    return {"id": ident, "month": f"{year:04d}-{month:02d}", "published": published.isoformat(),
            "competitive_100m": total, "tenors": tenors, "long_share_pct": share(LONG), "y30_share_pct": share(("30",)),
            "stated_prev_change_100m": prev_change, "stated_plan_change_100m": plan_change,
            "stated_plan_change_unread": plan_change_unread,
            "buyback_plan": buyback, "exchange_plan": exchange, "prev_actual": actual, "source_url": press_url(ident)}


def parse_plan(raw, ident, ym, today):
    return parse_plan_text(pdf_text(raw), ident, ym, today)


def parse_op_text(text, ident, kind, date, today):
    s = re.sub(r"\s+", "", text)
    if {"buyback": "국고채매입입찰결과", "exchange": "국고채교환입찰결과"}[kind] not in s: raise ValueError("op kind mismatch")
    cut = s.find("2.입찰결과")
    if cut < 0: raise ValueError("op field changed")
    over, res = s[:cut], s[cut:]
    d = re.search(r"입찰일시.*?[’'‘](\d{2})\.(\d{1,2})\.(\d{1,2})\.", over)
    if not d: raise ValueError("op field changed")
    day = dt.date(2000 + int(d[1]), int(d[2]), int(d[3]))
    if day.isoformat() != date: raise ValueError("op date mismatch")
    if day > today: raise ValueError("future operation")
    # 입찰(교환예정)금액은 공백을 남긴 글에서 — 공백을 지우면 앞 종목 번호 끝자리('…-3007 5,000억원')와 붙는다(2026-10-20 교환 결과 실측)
    spaced = " ".join(text.split())
    head = re.split(r"2\s*\.\s*입\s*찰\s*결\s*과", spaced, maxsplit=1)[0]
    offered = re.findall(r"(?<![\d,.\-])(\d[\d,]*(?:\.\d+)?)\s*(조|억)\s*원", head)
    bids = re.findall(r"응찰금액:([\d,]+)억원\(응찰률([\d.]+)%\)", res)
    awarded = re.findall(r"낙찰금액:([\d,]+)억원", res)
    if len(bids) != 1 or len(awarded) != 1: raise ValueError("op field changed")
    bid = int(bids[0][0].replace(",", "")); ratio = float(bids[0][1]); award = int(awarded[0].replace(",", ""))
    if not offered and ratio > 0: offered = glued_offer(head, bid, ratio)
    if len(offered) != 1: raise ValueError("op field changed")
    offer = won(*offered[0])
    if not (0 < offer < 1_000_000 and 0 < bid < 5_000_000 and 0 < award <= offer and award <= bid and 0 < ratio < 5000):
        raise ValueError("op outside range")
    if abs(bid / offer * 100 - ratio) > 0.2: raise ValueError("op outside range")
    return {"id": ident, "kind": kind, "date": date, "offered_100m": offer, "bids_100m": bid,
            "bid_cover_pct": ratio, "awarded_100m": award, "source_url": result_url(ident)}


def glued_offer(head, bid, ratio):
    """금액이 앞 종목 번호에 붙어 나온 글('…-3007' + '5,000억원' → '…-30075,000억원' — pypdf 6.10.2가 표 칸 사이
    공백을 넣지 않는다, 2026-10-29 실측)에서 입찰금액 하나를 고른다. 붙은 숫자 묶음의 끝에서 쓸 수 있는 꼴
    (첫 자리 1~9, 세 자리마다 쉼표)을 모두 후보로 두고, 응찰금액 ÷ 후보 = 응찰률(±0.2%p)인 것이 꼭 하나일 때만.
    종목 번호에 붙은 경우만 본다(앞이 '-'로 시작하는 숫자 묶음) — 그 밖의 꼴은 고르지 않는다."""
    picks = []
    for run, unit in re.findall(r"-(\d[\d,]*(?:\.\d+)?)\s*(조|억)\s*원", head):
        for i in range(1, len(run)):
            cand = run[i:]
            if not re.fullmatch(r"[1-9]\d{0,2}(?:,\d{3})*(?:\.\d+)?", cand): continue
            v = float(cand.replace(",", "")) * (10000 if unit == "조" else 1)
            if v > 0 and abs(bid / v * 100 - ratio) <= 0.2: picks.append((cand, unit))
    return picks if len(picks) == 1 else []


def parse_op(raw, ident, kind, date, today):
    return parse_op_text(pdf_text(raw, max_pages=4), ident, kind, date, today)


def to_read(links, prev_ids, cap):
    """가장 새 공고는 늘 다시 읽고(정정 확인), 나머지는 아직 없는 것만 cap개까지.
    순서: 아직 없는 것(새 것부터) 먼저, 이미 읽은 가장 새 공고 다시 읽기는 맨 끝 — 묶음 시간이 모자라면
    다시 읽기가 not_tried로 빠지고 전에 읽은 값이 남는다(2026-10-29 실측: 다시 읽기 한 건 약 8초가 앞에서 2월 계획을 밀어냈다)."""
    if not links: return []
    rest = [l for l in links[1:] if l[0] not in prev_ids][:cap - 1]
    return rest + [links[0]] if links[0][0] in prev_ids else [links[0]] + rest


def ops_queue(per_kind, prev_ids, cap):
    """매입·교환 결과 읽을 순서. per_kind = {종류: [(번호, 입찰일)]}(목록 순서), 종류마다 to_read와 같은 집합(cap개).
    아직 없는 공고를 종류끼리 번갈아(종류 안에서는 새 것부터), 이미 읽은 가장 새 공고 다시 읽기는 종류 순서로 맨 끝.
    → [(번호, (종류, 입찰일))]. 전에는 매입을 다 읽은 뒤 교환이라 교환이 늘 시간 예산에 밀렸다(2026-10-29 실측)."""
    new, again = [], []
    for kind, found in per_kind.items():
        picked = [(ident, (kind, date)) for ident, date in to_read(found, prev_ids, cap)]
        new.append([l for l in picked if l[0] not in prev_ids])
        again += [l for l in picked if l[0] in prev_ids]
    turns = []
    for i in range(max(map(len, new), default=0)):
        turns += [q[i] for q in new if i < len(q)]
    return turns + again


def merge_plans(got, previous):
    """새로 읽은 달 + 전에 읽은 달(같은 달이면 새로 읽은 것). 달 순서, 최근 MAX_PLANS달."""
    by_month = {}
    for r in list(previous or []) + list(got):
        if isinstance(r, dict) and isinstance(r.get("month"), str):
            by_month[r["month"]] = r
    return [by_month[m] for m in sorted(by_month)][-MAX_PLANS:]


def merge_ops(got, previous):
    by_id = {}
    for r in list(previous or []) + list(got):
        if isinstance(r, dict) and isinstance(r.get("id"), str) and isinstance(r.get("date"), str):
            by_id[r["id"]] = r
    return sorted(by_id.values(), key=lambda r: (r["date"], r["id"]), reverse=True)[:MAX_OPS]


def summary(plans):
    """화면용 계산값: 최신 달과 전월 계획 대비(목록에 두 달이 다 있을 때만), 연간 한도 대비 보도자료 발행 규모 합계.
    달마다 다음 달 보도자료에 적힌 보도 시점 값을 더한다 — 뒤에 확정되는 20년물 비경쟁인수·모집분은 빠져 있어
    재정경제부가 밝힌 누계보다 작을 수 있다(2026년 상반기: 이 합 123.1조원, 7월 보도자료의 누적 124.1조원)."""
    def good(p):          # 전에 저장된 행이 깨져 있어도 스냅샷 전체를 멈추지 않게 — 모양이 맞는 행만 센다
        return (isinstance(p, dict) and isinstance(p.get("month"), str) and re.fullmatch(r"\d{4}-\d{2}", p["month"])
                and type(p.get("competitive_100m")) is int)
    plans = sorted((p for p in plans or [] if good(p)), key=lambda p: p["month"])
    out = {"latest_month": None, "prev_month_change_100m": None, "progress": None}
    if not plans: return out
    latest = plans[-1]; out["latest_month"] = latest["month"]
    y, m = map(int, latest["month"].split("-"))
    pm = f"{y - 1:04d}-12" if m == 1 else f"{y:04d}-{m - 1:02d}"
    prev = next((p for p in plans if p["month"] == pm), None)
    if prev: out["prev_month_change_100m"] = latest["competitive_100m"] - prev["competitive_100m"]
    actuals = {a["month"]: a["amount_100m"] for a in (p.get("prev_actual") for p in plans)
               if isinstance(a, dict) and isinstance(a.get("month"), str) and re.fullmatch(r"\d{4}-\d{2}", a["month"])
               and type(a.get("amount_100m")) is int}
    if not actuals: return out
    last = max(actuals); year = int(last[:4])
    months = sorted(k for k in actuals if k.startswith(f"{year:04d}-"))
    total = sum(actuals[k] for k in months)
    limit = ANNUAL_LIMITS.get(year)
    upto = int(last[5:])
    missing = [f"{year:04d}-{i:02d}" for i in range(1, upto + 1) if f"{year:04d}-{i:02d}" not in actuals]
    # 한도 대비 비율은 1월부터 빠진 달 없이 실적이 다 있을 때만 — 일부 달의 합을 한 해 진도처럼 보이지 않게
    out["progress"] = {"year": year, "months": months, "through": last, "missing": missing,
                       "actual_100m": total, "limit_100m": limit["limit_100m"] if limit else None,
                       "limit_published": limit["published"] if limit else None,
                       "limit_source_url": limit["source_url"] if limit else None,
                       "pct": round(total / limit["limit_100m"] * 100, 1) if limit and not missing else None}
    return out
