#!/usr/bin/env python3
"""Korean market learning data. Public downloads only; no credentials or personal files.

BOK snapshot XLSX (3 charts), KRX public KTB statistics (3y/10y foreign net
contracts, spread trades included), Treasury auction calendar/results, and the
monthly KTB issuance plans / buyback·exchange results (korea_issuance.py).
Only allowlisted numeric fields, dates and fixed labels leave the parsers.
Independent feeds retain their last successful values on failure and expose status.
pypdf reads official offering PDFs; other parsers use the standard library.
Run: python scripts/korea_market.py [--out data]
"""
import argparse
import datetime as dt
import html
import io
import json
import math
import re
import time
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from html.parser import HTMLParser
from pathlib import Path

import korea_issuance as ki

UTC = dt.timezone.utc
KST = dt.timezone(dt.timedelta(hours=9))
BOK = "https://snapshot.bok.or.kr"
KTB = "https://ktb.mofe.go.kr"
RESULTS = "https://mofe.go.kr/st/fnancstats/ktb50201.do?bbsId=MOSFBBS_000000000049&menuNo=6050300"
DETAIL = "https://mofe.go.kr/st/fnancstats/updateTbFnancstatsView.do"
FLOW_URL = "https://kasp.krx.co.kr/ktbasp/ktb/ktb40302_table.jsp"
OFFER_LIST = KTB + "/isuNdReprchsPblanc.do"
BOK_PORTAL = "https://www.bok.or.kr"
LIMIT = 5_000_000
NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
CHARTS = {
    "credit": (857, {"aa_spread": ("회사채(AA-, 3년) - 국고채(3년)", "(%p)", 100)}),
    "money": (851, {"cd91": ("CD(91일)", "(%)", 1), "cp91": ("CP(91일)", "(%)", 1)}),
    "rates": (852, {"kr3": ("국고채(3년)", "(%)", 1), "kr10": ("국고채(10년)", "(%)", 1),
                    "us10": ("미국 국채(10년)", "(%)", 1)}),
}
META = {
    "kr3": ("국고채 3년 · 최종호가", "rates", "%", "단기 정책 기대와 국내 채권금리의 움직임을 함께 봅니다."),
    "kr10": ("국고채 10년 · 최종호가", "rates", "%", "성장·물가 전망과 장기채 수급이 함께 반영됩니다."),
    "us10": ("미국 국채 10년 · par yield", "rates", "%", "미국 현지 관측일 기준입니다. 한국과 시장 마감 시각은 다릅니다."),
    "kr_curve": ("한국 10년−3년 금리차", "rates", "bp", "장단기 금리차가 커졌는지, 어느 만기가 더 움직였는지 살펴봅니다."),
    "kr_us": ("한국−미국 10년 금리차", "rates", "bp", "같은 날짜에 양국 값이 모두 있는 날만 계산합니다. 동시 시세나 환헤지 수익률은 아닙니다."),
    "aa_spread": ("회사채 AA− 3년 신용 스프레드", "credit", "bp", "회사채 AA− 3년과 국고채 3년의 금리차입니다. 확대는 신용·유동성 보상의 증가를 뜻할 수 있습니다."),
    "cd91": ("CD 91일", "credit", "%", "은행의 단기 조달 여건을 살펴보는 참고 금리입니다."),
    "cp91": ("CP 91일", "credit", "%", "기업어음 금리입니다. 원 자료의 할인율을 수익률로 환산한 수치입니다."),
    "cp_cd": ("CP−CD 91일 금리차", "credit", "bp", "기업과 은행의 단기 조달비용 차이입니다. 신용·유동성·발행 구성의 영향이 섞입니다."),
    "foreign3": ("외국인 3년 국채선물 순매수", "flows", "계약", "매수−매도 계약수, 스프레드 거래 포함. 헤지·차익거래도 섞여 있어 방향 전망으로 단정하지 않습니다."),
    "foreign10": ("외국인 10년 국채선물 순매수", "flows", "계약", "3년물과 계약당 금리 민감도가 다르므로 계약수를 단순 합산하지 않습니다."),
}


class FeedError(ValueError):
    """Fixed public reason codes; never publish remote exception text."""


class PublicFetcher:
    """One retry for transient failures; budgets leave time to publish failure status."""
    def __init__(self, budget=150, per_feed=45, clock=time.monotonic, sleep=time.sleep, opener=urllib.request.urlopen):
        self.clock, self.sleep, self.opener = clock, sleep, opener
        self.deadline = clock() + budget
        self.per_feed = per_feed
        self.feed_deadline = self.deadline

    def start_feed(self):
        self.feed_deadline = min(self.deadline, self.clock() + self.per_feed)

    def remaining(self):
        remaining = min(self.deadline, self.feed_deadline) - self.clock()
        if remaining <= 0: raise FeedError("timeout")
        return remaining

    def __call__(self, url, data=None):
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        for attempt in range(2):
            try:
                with self.opener(url, data=body, timeout=min(10, self.remaining())) as response:
                    chunks, size = [], 0
                    while True:
                        self.remaining()
                        chunk = response.read1(min(65536, LIMIT + 1 - size))
                        self.remaining()
                        if not chunk: break
                        chunks.append(chunk); size += len(chunk)
                        if size > LIMIT: raise ValueError("oversized response")
                return b"".join(chunks)
            except urllib.error.HTTPError as exc:
                if exc.code not in (408, 429, 500, 502, 503, 504): raise
                exc.close()
                if attempt: raise
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if attempt: raise
            if self.remaining() <= 1: raise FeedError("timeout")
            self.sleep(1)


def request(url, data=None):
    return PublicFetcher()(url, data)


def xlsx_rows(raw):
    """Read the public export's first sheet. No formulas/macros are executed."""
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if sum(f.file_size for f in z.infolist()) > 30_000_000:
            raise ValueError("oversized workbook")
        strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            strings = ["".join(s.itertext()) for s in root]
        root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in root.findall("x:sheetData/x:row", NS):
            cells = {}
            for c in row.findall("x:c", NS):
                if c.find("x:f", NS) is not None:
                    raise ValueError("unexpected formula")
                col = re.fullmatch(r"([A-Z]+)\d+", c.attrib["r"])[1]
                idx = 0
                for char in col:
                    idx = idx * 26 + ord(char) - 64
                if idx > 30:
                    raise ValueError("unexpected column")
                v = c.find("x:v", NS)
                typ = c.get("t")
                if typ == "inlineStr":
                    value = "".join(c.find("x:is", NS).itertext())
                elif v is None or v.text is None:
                    value = None
                elif typ == "s":
                    value = strings[int(v.text)]
                elif typ in (None, "n"):
                    value = float(v.text)
                else:
                    raise ValueError("unexpected cell type")
                cells[idx - 1] = value
            rows.append([cells.get(i) for i in range(max(cells, default=-1) + 1)])
        return rows


def parse_bok(raw, specs, today):
    rows = xlsx_rows(raw)
    def header(name):
        found = [r for r in rows if r and r[0] == name]
        if len(found) != 1:
            raise ValueError("export header changed")
        return found[0]
    labels, units, freq = header("범례명"), header("단위"), header("주기")
    out = {}
    for key, (label, unit, scale) in specs.items():
        if labels.count(label) != 1:
            raise ValueError("series label changed")
        col = labels.index(label)
        if units[col] != unit or freq[col] != "일":
            raise ValueError("unit or frequency changed")
        points = {}
        for row in rows:
            if not row or not isinstance(row[0], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row[0]):
                continue
            day = dt.date.fromisoformat(row[0])
            if day > today:
                raise ValueError("future observation")
            v = row[col] if col < len(row) else None
            if v is None:
                continue
            if type(v) not in (float, int) or not math.isfinite(v) or not -30 < v < 50:
                raise ValueError("invalid yield")
            if day in points:
                raise ValueError("duplicate date")
            points[day] = round(v * scale, 4)
        if not points:
            raise ValueError("empty series")
        cutoff = today - dt.timedelta(days=400)
        out[key] = [[d.isoformat(), points[d]] for d in sorted(points) if d >= cutoff]
        if not out[key]:
            raise ValueError("no recent observations")
    return out


def difference(a, b):
    right = dict(b)
    return [[d, round((v - right[d]) * 100, 4)] for d, v in a if d in right]


def metrics(points, unit):
    if not points:
        return None
    date, value = points[-1]
    result = {"date": date, "value": value, "changes": {}, "sums": {}, "distribution": None}
    if unit == "계약":
        for n in (1, 5, 20):
            if len(points) >= n:
                result["sums"][str(n)] = {"value": sum(v for _, v in points[-n:]), "from": points[-n][0]}
        return result
    scale = 100 if unit == "%" else 1
    for n in (1, 5, 20):
        if len(points) > n:
            result["changes"][str(n)] = {"value": round((value - points[-1-n][1]) * scale, 2), "from": points[-1-n][0]}
    cutoff = dt.date.fromisoformat(date) - dt.timedelta(days=365)
    window = [(d, v) for d, v in points if dt.date.fromisoformat(d) >= cutoff]
    # A short initial history must not masquerade as a year's distribution.
    if len(window) >= 200 and (dt.date.fromisoformat(date) - dt.date.fromisoformat(window[0][0])).days >= 300:
        values = [v for _, v in window]
        low, high = min(values), max(values)
        result["distribution"] = {"from": window[0][0], "to": date, "count": len(values), "min": low, "max": high,
            "range_position": round((value-low)/(high-low)*100, 1) if high != low else None,
            "percentile": round((sum(v < value for v in values)+0.5*sum(v == value for v in values))/len(values)*100, 1)}
    return result


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.cell = [], None, None
        self.inputs, self.links = {}, []
        self.anchor = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "tr": self.row = []
        if tag in ("td", "th") and self.row is not None: self.cell = []
        if tag == "input" and a.get("id"): self.inputs[a["id"]] = a.get("value", "")
        if tag == "a": self.anchor = [a.get("href", ""), []]

    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)
        if self.anchor is not None: self.anchor[1].append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split())); self.cell = None
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row); self.row = None
        if tag == "a" and self.anchor is not None:
            self.links.append((self.anchor[0], " ".join("".join(self.anchor[1]).split()))); self.anchor = None


def page(raw):
    p = TableParser(); p.feed(raw.decode("utf-8")); return p


def parse_flows(raw, today):
    p = page(raw)
    headers = [r for r in p.rows if r and r[0] == "년/월/일" and "외국인" in r]
    if len(headers) != 1 or "단위:계약" not in raw.decode("utf-8").replace(" ", ""):
        raise ValueError("flow table changed")
    h = headers[0]; idx = h.index("외국인"); out = {}
    for r in p.rows:
        if not r or not re.fullmatch(r"\d{4}/\d{2}/\d{2}", r[0]): continue
        d = dt.date.fromisoformat(r[0].replace("/", "-"))
        if len(r) != len(h) or d > today or d.isoformat() in out:
            raise ValueError("invalid flow row")
        values = [int(v.replace(",", "")) for v in r[1:]]
        if values[-1] != 0 or sum(values[:-1]) != 0 or any(abs(v) > 10_000_000 for v in values):
            raise ValueError("net flows do not balance")
        out[d.isoformat()] = values[idx-1]
    if not out: raise ValueError("no flow rows")
    return sorted([[d, v] for d, v in out.items()])


def parse_calendar(raw, today=None):
    p = page(raw)
    year, month = int(p.inputs["searchYear"]), int(p.inputs["searchMonth"])
    dt.date(year, month, 1)
    if today and (year, month) != (today.year, today.month): raise FeedError("calendar_month")
    out = []
    for r in p.rows:
        if len(r) != 2 or not re.fullmatch(r"\d{4}\.\d{2}\.\d{2}\.", r[0]): continue
        d = dt.date.fromisoformat(r[0].rstrip(".").replace(".", "-"))
        if (d.year, d.month) != (year, month): raise ValueError("calendar month mismatch")
        # Fixed labels only, never upstream prose or HTML.
        terms = re.findall(r"(?<!\d)(2|3|5|10|20|30|50)년물|물가채", r[1])
        for t in terms:
            out.append({"date": d.isoformat(), "tenor": t + "년" if t else "물가채"})
    if not out or len({(r['date'], r['tenor']) for r in out}) != len(out):
        raise FeedError("empty_or_duplicate")
    return {"month": f"{year:04d}-{month:02d}", "rows": out, "source_url": KTB + "/mnbyIsuCldr.do"}


def result_links(raw):
    out = []
    for href, title in page(raw).links:
        m = re.fullmatch(r'javascript:fn_egov_updateView\("(MOSF_[0-9]{1,15})"\);', href)
        tenor = re.search(r"^국고채\s+(2|3|5|10|20|30|50)년물", title)
        if m and tenor and "경쟁입찰 결과" in title:
            out.append((m[1], int(tenor[1])))
    if not out: raise ValueError("no auction notices")
    return out[:8]


def result_url(ident):
    return DETAIL + "?" + urllib.parse.urlencode({"searchSn": ident, "type": "ktb50201", "bbsId": "MOSFBBS_000000000049", "menuNo": "6050300"})


def parse_result(raw, ident, tenor, today):
    body = page(raw).inputs.get("cn", "")
    text = " ".join(html.unescape(re.sub(r"<[^>]*>", " ", body)).split())
    d = re.search(r"입찰일시\s*:\s*[’'‘]?(\d{2})\.(\d{1,2})\.(\d{1,2})", text)
    if not d: raise ValueError("missing auction date")
    date = dt.date(2000+int(d[1]), int(d[2]), int(d[3]))
    if date > today: raise ValueError("future auction result")
    def field(label, suffix, need=True):
        matches = re.findall(label+r"\s*:\s*([\d,]+(?:\.\d+)?)\s*"+suffix, text)
        if not matches and not need: return None
        if len(matches) != 1: raise ValueError("auction field changed")
        return float(matches[0].replace(",", ""))
    offered = re.search(r"입찰금액\s*:\s*"+str(tenor)+r"년물\([^)]*\)\s*([\d,]+)\s*억원", text)
    if not offered: raise ValueError("missing offering amount")
    offer = int(offered[1].replace(",", ""))
    bids = field("응찰금액", "억원"); ratio = field("응찰률", "%")
    awarded = field("낙찰금액", "억원"); rate = field("가중평균낙찰금리", "%", need=False)
    if rate is None:    # 50년물은 단일 '낙찰금리'(+부분낙찰률)만 싣는다(2026-10-16 결과 공고 실측)
        rate = field("(?<![가-힣])낙찰금리", "%")
    if not (0 < offer < 1_000_000 and bids > 0 and awarded > 0 and 0 < rate < 20 and 0 < ratio < 5000):
        raise ValueError("auction values outside range")
    if abs(bids/offer*100-ratio) > 0.2: raise ValueError("bid cover mismatch")
    return {"id": ident, "date": date.isoformat(), "tenor": f"{tenor}년", "offered_100m": offer,
            "awarded_100m": awarded, "bid_cover_pct": ratio, "yield_pct": rate, "source_url": result_url(ident)}


def offering_links(raw):
    out = []
    for href, title in page(raw).links:
        ident = re.fullmatch(r"javascript:popup\('https://www\.bok\.or\.kr/portal/bbs/P0001794/view\.do\?nttId=([0-9]{1,12})&menuNo=200364'\)", href)
        code = re.search(r"국고\s*(\d{5}-\d{4}-(?:02|03|05|10|20|30|50)\d{2})", title)
        if ident and code and "발행공고" in title:
            out.append((ident[1], code[1]))
    if not out: raise ValueError("no offering notices")
    return out[:8]


def offering_url(ident):
    if not re.fullmatch(r"[0-9]{1,12}", ident): raise ValueError("invalid notice id")
    return BOK_PORTAL + "/portal/bbs/P0001794/view.do?nttId=" + ident + "&menuNo=200364"


def offering_pdf_url(raw):
    paths = {href for href, _ in page(raw).links if re.fullmatch(r"/fileSrc/portal/[a-f0-9]+/\d+/[a-f0-9]+\.pdf", href)}
    if len(paths) != 1: raise ValueError("ambiguous offering PDF")
    return BOK_PORTAL + paths.pop()


def competitive_section(text):
    """공백을 뺀 본문에서 경쟁입찰 구역. 보통은 '(1)경쟁입찰 … (2)일반인입찰'이다. 일반인입찰이 없는 공고(50년물 등,
    2026-10-14 실측: 'ㅇ경쟁입찰(국고…) -입찰일:… -발행예정금액:… -대금납입일:… 4.발행,상환…')는 번호가 없어
    '경쟁입찰' 뒤부터 다음 구역((n)·번호 항목·※·일반인입찰·비경쟁인수)까지로 본다. 그때는 '경쟁입찰'이 한 번만 있어야 한다."""
    numbered = re.search(r"\(1\)경쟁입찰(.*?)\(2\)", text)
    if numbered: return numbered[1]
    if len(re.findall(r"(?<!비)경쟁입찰", text)) != 1: return None
    bare = re.search(r"(?<!비)경쟁입찰(.*?)(?=\(\d\)|(?<![\d.])\d{1,2}\.(?=[가-힣])|※|일반인입찰|비경쟁인수|$)", text)
    return bare[1] if bare else None


def parse_offering_text(text, ident, code, today):
    text = re.sub(r"\s+", "", text)
    if "국고" + code not in text: raise ValueError("offering bond mismatch")
    section = competitive_section(text)
    if not section: raise ValueError("missing competitive section")
    dates = re.findall(r"입찰일[:：](\d{4})\.(\d{1,2})\.(\d{1,2})\.", section)
    amounts = re.findall(r"발행예정금액[:：]([\d,]+)억원", section)
    if len(dates) != 1 or len(amounts) != 1: raise ValueError("ambiguous offering fields")
    date = dt.date(*map(int, dates[0])); amount = int(amounts[0].replace(",", ""))
    if date > today + dt.timedelta(days=90) or not 0 < amount < 1_000_000:
        raise ValueError("offering outside range")
    return {"id": ident, "date": date.isoformat(), "tenor": str(int(code.split("-")[2][:2])) + "년",
            "offered_100m": amount, "source_url": offering_url(ident)}


# 공고 하나를 건너뛸 때 남기는 고정 사유 코드. 원격 문구는 남기지 않는다(우리 코드의 고정 문구만 코드로 바꾼다).
SKIP_REASONS = {"ambiguous offering PDF": "pdf_link", "offering bond mismatch": "bond_mismatch",
                "missing competitive section": "no_competitive_section", "ambiguous offering fields": "ambiguous_fields",
                "offering outside range": "out_of_range", "unexpected offering PDF": "pdf_shape",
                "oversized response": "oversized", "invalid notice id": "bad_id",
                "missing auction date": "no_date", "future auction result": "future", "auction field changed": "field_changed",
                "missing offering amount": "no_amount", "auction values outside range": "out_of_range",
                "bid cover mismatch": "bid_cover", **ki.SKIP_REASONS}


def skip_reason(exc):
    """Fixed public code for one unreadable notice — never remote exception text."""
    if isinstance(exc, FeedError): return str(exc)
    if isinstance(exc, urllib.error.HTTPError): return f"http_{int(exc.code)}"
    if isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError)): return "network"
    if isinstance(exc, UnicodeError): return "decode"
    if type(exc).__module__.split(".")[0] == "pypdf": return "pdf_read"
    if type(exc) is ValueError and str(exc) in SKIP_REASONS: return SKIP_REASONS[str(exc)]
    return "parse"


def parse_offering(raw, ident, code, today):
    from pypdf import PdfReader
    pdf = PdfReader(io.BytesIO(raw))
    if pdf.is_encrypted or not 1 <= len(pdf.pages) <= 12: raise ValueError("unexpected offering PDF")
    return parse_offering_text(pdf.pages[0].extract_text(), ident, code, today)


def card(key, points, source, today):
    title, group, unit, note = META[key]
    m = metrics(points, unit)
    return {"key": key, "title": title, "group": group, "unit": unit, "note": note,
            "points": points, "metrics": m, "source": source,
            "stale": m is None or (today-dt.date.fromisoformat(m["date"])).days > 7}


def validate_freshness(name, payload, previous, today):
    if name == "ktb_plans":
        # 발행계획은 전달 말(대개 마지막 목요일, 늦으면 그달 1~3일)에 나온다 — 그달 8일부터는 그달 계획이 있어야 하고,
        # 7일까지는 지난달 계획까지 둔다(공휴일 달력 없이 7일 여유). 제목·검색어·목록이 바뀌어 새 달을 못 찾아도 여기서 잡힌다
        if not payload: raise FeedError("empty_or_duplicate")
        latest = max(r["month"] for r in payload)
        floor = (today if today.day > 7 else today.replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
        if latest < floor: raise FeedError("stale")
        if previous and latest < max((r["month"] for r in previous if isinstance(r, dict) and isinstance(r.get("month"), str)), default=""):
            raise FeedError("regressed")
        return
    if name == "ktb_ops":
        if not payload: raise FeedError("empty_or_duplicate")     # 매입·교환은 달마다 있지 않다 — 날짜로 묵음을 따지지 않는다
        return
    series = payload if name in CHARTS else {name: payload} if name in ("foreign3", "foreign10") else {}
    old_series = (previous or {}) if name in CHARTS else {name: previous or []}
    for key, points in series.items():
        if not points: raise FeedError("empty_or_duplicate")
        latest = dt.date.fromisoformat(points[-1][0])
        if (today - latest).days > 7: raise FeedError("stale")
        old_points = old_series.get(key) or []
        if old_points and points[-1][0] < old_points[-1][0]: raise FeedError("regressed")


def build(old, now, fetch=None):
    fetch = PublicFetcher() if fetch is None else fetch
    today = now.astimezone(KST).date(); stamp = now.isoformat(timespec="seconds")
    feeds = {}; previous = old.get("feeds", {}) if old.get("schema") == 1 else {}
    def run(name, fn):
        prev = previous.get(name, {})
        try:
            if isinstance(fetch, PublicFetcher): fetch.start_feed()
            payload = fn()
            validate_freshness(name, payload, prev.get("data"), today)
            feeds[name] = {"ok": True, "checked_at": stamp, "last_success": stamp, "data": payload}
        except Exception as e:
            reason = str(e) if isinstance(e, FeedError) else "unavailable"
            feeds[name] = {"ok": False, "reason": reason, "checked_at": stamp, "last_success": prev.get("last_success"), "data": prev.get("data")}
            print(f"[korea_market] {name}: {type(e).__name__}")
    for name, (chart_id, specs) in CHARTS.items():
        run(name, lambda chart_id=chart_id, specs=specs: parse_bok(fetch(BOK+f"/api/chart/exportChart?chart_id={chart_id}"), specs, today))
    for key, code in (("foreign3", "KRDRVFUBM3"), ("foreign10", "KRDRVFUBMA")):
        run(key, lambda code=code: parse_flows(fetch(FLOW_URL, {
            "fr_work_dt": (today-dt.timedelta(days=100)).strftime("%Y%m%d"), "to_work_dt": today.strftime("%Y%m%d"),
            "isu_cd": code, "date_sch_type": "dd", "prt_check": "SUN", "prt_type": "VL", "spread_tp": "1"}), today))
    run("calendar", lambda: parse_calendar(fetch(KTB+"/mnbyIsuCldr.do"), today))
    def notices(name, links, read, retain_transient=False):
        """공고마다 따로 읽는다 — 한 건의 양식이 달라도 나머지는 갱신한다(발행공고 2026-10-14, 입찰 결과 2026-10-26).
        못 읽은 공고는 고정 사유 코드로 남기고, 같은 공고를 전에 읽었으면 그 값을 둔다. 한 건도 새로 못 읽으면
        이 묶음만 실패(이전 자료 유지). links = [(공고 번호, 읽을 때 넘길 값)], read(번호, 값) → 행.
        retain_transient(발행계획·매입/교환만): 평소엔 가장 새 공고 하나만 다시 읽으므로, 못 읽은 공고가 모두 전에 읽은
        것이고 사유가 모두 일시 오류(접속·시간 초과·408·429·5xx)면 실패로 두지 않고 전에 읽은 값으로 둔다(사유 코드·경고는 남음)."""
        prev = {r["id"]: r for r in (previous.get(name, {}).get("data") or []) if isinstance(r, dict) and isinstance(r.get("id"), str)}
        got, skipped = [], skips[name]
        for i, (ident, arg) in enumerate(links):
            try:
                got.append(read(ident, arg))
            except Exception as e:
                skipped.append({"id": ident, "reason": skip_reason(e)})
                if ident in prev: got.append(prev[ident])
                if isinstance(e, FeedError):     # 시간 예산을 다 썼다 — 남은 공고는 시도하지 않고 전에 읽은 값만 둔다
                    for rest, _ in links[i + 1:]:
                        skipped.append({"id": rest, "reason": "not_tried"})
                        if rest in prev: got.append(prev[rest])
                    break
        for s_ in skipped:
            print(f"[korea_market] {name} skip {s_['id']}: {s_['reason']}")
        if not any(r.get("id") not in {s_["id"] for s_ in skipped} for r in got):
            codes = {s_["reason"] for s_ in skipped} - {"not_tried"}     # 한 건도 새로 못 읽음 — 원인에 맞는 코드로
            transient = lambda c: c in ("network", "timeout", "http_408", "http_429") or c.startswith("http_5")
            if retain_transient and got and codes and all(map(transient, codes)) and all(s_["id"] in prev for s_ in skipped):
                return got
            if "timeout" in codes: raise FeedError("timeout")
            if codes and all(c == "network" or c.startswith("http_") for c in codes): raise FeedError("unavailable")
            raise FeedError("unreadable_notices")
        return got
    skips = {"auctions": [], "offerings": [], "ktb_plans": [], "ktb_ops": []}
    # Re-read recent notices so corrections are picked up. Max eight public pages.
    run("auctions", lambda: notices("auctions", result_links(fetch(RESULTS)),
                                    lambda ident, tenor: parse_result(fetch(result_url(ident)), ident, tenor, today)))
    run("offerings", lambda: notices("offerings", offering_links(fetch(OFFER_LIST)),
                                     lambda ident, code: parse_offering(fetch(offering_pdf_url(fetch(offering_url(ident)))),
                                                                        ident, code, today)))
    # 재정경제부 발행계획 보도자료·매입/교환 결과 — 시간 예산을 다른 묶음에 먼저 쓰도록 맨 뒤에. 지난 달·지난 결과는 전에 읽은 값을 둔다
    def plan_feed():
        prev = [r for r in previous.get("ktb_plans", {}).get("data") or [] if isinstance(r, dict)]
        links = ki.plan_links(fetch(ki.plan_list_url(1)))
        # 첫 쪽(10건)에 경과물 모집 공고가 끼면 보고 연도 2월 계획(1월 실적의 유일한 출처)이 둘째 쪽으로 밀린다(2026-10-28 실측).
        # 그 달이 첫 쪽에도 저장된 달에도 없을 때만 둘째 쪽을 한 번 더 읽는다 — 그 계획을 못 읽으면 다음 해 2월 계획이
        # 나올 때까지 실행마다 다시 읽지만 목록 요청 하나뿐이다. 둘째 쪽의 어떤 문제도 이 묶음을 실패로 만들지 않는다
        target = ki.page2_target(links, {r.get("month") for r in prev if isinstance(r.get("month"), str)})
        if target:
            try:
                links = ki.join_links(links, ki.plan_links(fetch(ki.plan_list_url(2))), target)
            except Exception as e:
                print(f"[korea_market] ktb_plans page2: {type(e).__name__}")
        links = ki.to_read(links, {r.get("id") for r in prev if isinstance(r.get("id"), str)}, ki.READ_PLANS)
        got = notices("ktb_plans", links, lambda ident, ym: ki.parse_plan(
            fetch(ki.attachment_pdf_url(fetch(ki.press_url(ident)))), ident, ym, today), retain_transient=True)
        return ki.merge_plans(got, prev)
    def ops_feed():
        prev = previous.get("ktb_ops", {}).get("data") or []
        seen = {r.get("id") for r in prev if isinstance(r, dict) and isinstance(r.get("id"), str)}
        links, empty = [], []
        for kind in ki.OPS:
            found = ki.op_links(fetch(ki.ops_list_url(kind)), kind)
            if not found: empty.append(kind)          # 한 종류 목록만 비었다 — 다른 종류로 갱신하되 사유 코드로 남긴다
            links += [(ident, (kind, date)) for ident, date in ki.to_read(found, seen, ki.READ_OPS)]
        try:
            if not links: raise ValueError("no operation notices")       # 목록 형식이 바뀜 — 공고 하나의 문제가 아니다
            got = notices("ktb_ops", links, lambda ident, arg: ki.parse_op(
                fetch(ki.attachment_pdf_url(fetch(ki.result_url(ident)))), ident, arg[0], arg[1], today), retain_transient=True)
        finally:                                       # 종류별 빈 목록은 공고 읽기가 끝난 뒤에 더한다(묶음 실패 사유 판단과 섞지 않게)
            skips["ktb_ops"] += [{"id": kind, "reason": ki.NO_NOTICES} for kind in empty]
        return ki.merge_ops(got, prev)
    run("ktb_plans", plan_feed)
    run("ktb_ops", ops_feed)
    for name, skipped in skips.items():
        feeds[name]["skipped"] = skipped
    cards = []
    for name, (chart_id, _) in CHARTS.items():
        feed = feeds[name]; data = dict(feed["data"] or {})
        if name == "money" and data:
            data["cp_cd"] = difference(data["cp91"], data["cd91"])
        if name == "rates" and data:
            data["kr_curve"] = difference(data["kr10"], data["kr3"])
            data["kr_us"] = difference(data["kr10"], data["us10"])
        source = {"name": "한국은행 금융·경제 스냅샷 · 금융투자협회·ECOS" + ("·미국 재무부" if name == "rates" else ""),
                  "url": BOK+"/dashboard/A", "download_url": BOK+f"/api/chart/exportChart?chart_id={chart_id}"}
        for key, points in data.items():
            c = card(key, points, source, today); c["feed"] = name; cards.append(c)
    for key in ("foreign3", "foreign10"):
        if feeds[key]["data"]:
            c = card(key, feeds[key]["data"], {"name": "한국거래소 · 국채시장 투자자별 거래동향", "url": KTB+"/invstrDelngTrend.do"}, today)
            c["feed"] = key; cards.append(c)
    return {"schema": 1, "checked_at": stamp, "feeds": feeds, "cards": cards,
            "calendar": feeds["calendar"]["data"], "auctions": feeds["auctions"]["data"] or [],
            "offerings": feeds["offerings"]["data"] or [],
            "ktb_plans": feeds["ktb_plans"]["data"] or [], "ktb_ops": feeds["ktb_ops"]["data"] or [],
            "ktb_summary": ki.summary(feeds["ktb_plans"]["data"] or []),
            "notices": ["학습용 참고 자료이며 기존 13개 규칙 판정에는 쓰지 않습니다.",
                "한국은행 스냅샷 자료는 출처를 명시하여 비상업적 학습 목적으로 이용합니다. 원자료 저작권은 각 제공기관에 있습니다.",
                "금리차·기간 변화·누적 순매수·분포는 이 사이트의 계산값입니다. 분포는 최근 관측일 기준 365일이며 저평가·고평가 판정이 아닙니다."]}


def atomic_json(path, data):
    path = Path(path)
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=path.name+".", suffix=".tmp", delete=False) as f:
            temp = Path(f.name); f.write(encoded)
        temp.replace(path)
    finally:
        if temp is not None and temp.exists(): temp.unlink()


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1]/"data")); args = ap.parse_args(argv)
    out = Path(args.out); path = out/"korea.json"
    try:
        try: old = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError: old = {}
        if not isinstance(old, dict) or (old and (old.get("schema") != 1 or not isinstance(old.get("feeds"), dict))):
            raise ValueError("invalid previous snapshot")
        data = build(old, dt.datetime.now(UTC)); out.mkdir(parents=True, exist_ok=True)
        atomic_json(path, data)
    except Exception as exc:
        print(f"[korea_market] snapshot not replaced: {type(exc).__name__}")
        return 1
    failed = [k for k, v in data["feeds"].items() if not v["ok"]]
    print(f"[korea_market] {len(data['cards'])} cards; {len(failed)} failed feeds")
    for name, what in (("auctions", "입찰 결과 공고"), ("offerings", "한국은행 발행공고"),
                       ("ktb_plans", "국고채 발행계획 보도자료"), ("ktb_ops", "국고채 매입·교환 결과 공고")):
        skipped = data["feeds"][name].get("skipped") or []
        if skipped:     # GitHub Actions 경고(실행을 실패로 만들지 않음) — 공고 번호와 고정 사유 코드만
            print(f"::warning::{what} " + str(len(skipped)) + "건을 읽지 못함 — "
                  + ", ".join(f"{s_['id']} {s_['reason']}" for s_ in skipped))
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
