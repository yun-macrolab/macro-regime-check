#!/usr/bin/env python3
"""Korean market learning data. Public downloads only; no credentials or personal files.

BOK snapshot XLSX (3 charts), KRX public KTB statistics (3y/10y foreign net
contracts, spread trades included), Treasury auction calendar/results.
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
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from html.parser import HTMLParser
from pathlib import Path

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


def request(url, data=None):
    if data is not None:
        data = urllib.parse.urlencode(data).encode()
    with urllib.request.urlopen(url, data=data, timeout=25) as r:
        raw = r.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError("oversized response")
    return raw


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


def parse_calendar(raw):
    p = page(raw)
    year, month = int(p.inputs["searchYear"]), int(p.inputs["searchMonth"])
    dt.date(year, month, 1)
    out = []
    for r in p.rows:
        if len(r) != 2 or not re.fullmatch(r"\d{4}\.\d{2}\.\d{2}\.", r[0]): continue
        d = dt.date.fromisoformat(r[0].rstrip(".").replace(".", "-"))
        if (d.year, d.month) != (year, month): raise ValueError("calendar month mismatch")
        # Fixed labels only, never upstream prose or HTML.
        terms = re.findall(r"(?<!\d)(2|3|5|10|20|30|50)년물|물가채", r[1])
        for t in terms:
            out.append({"date": d.isoformat(), "tenor": t + "년" if t else "물가채"})
    return {"month": f"{year:04d}-{month:02d}", "rows": out, "source_url": KTB + "/mnbyIsuCldr.do"}


def result_links(raw):
    out = []
    for href, title in page(raw).links:
        m = re.fullmatch(r'javascript:fn_egov_updateView\("(MOSF_\d+)"\);', href)
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
    def field(label, suffix):
        matches = re.findall(label+r"\s*:\s*([\d,]+(?:\.\d+)?)\s*"+suffix, text)
        if len(matches) != 1: raise ValueError("auction field changed")
        return float(matches[0].replace(",", ""))
    offered = re.search(r"입찰금액\s*:\s*"+str(tenor)+r"년물\([^)]*\)\s*([\d,]+)\s*억원", text)
    if not offered: raise ValueError("missing offering amount")
    offer = int(offered[1].replace(",", ""))
    bids = field("응찰금액", "억원"); ratio = field("응찰률", "%")
    awarded = field("낙찰금액", "억원"); rate = field("가중평균낙찰금리", "%")
    if not (0 < offer < 1_000_000 and bids > 0 and awarded > 0 and 0 < rate < 20 and 0 < ratio < 5000):
        raise ValueError("auction values outside range")
    if abs(bids/offer*100-ratio) > 0.2: raise ValueError("bid cover mismatch")
    return {"id": ident, "date": date.isoformat(), "tenor": f"{tenor}년", "offered_100m": offer,
            "awarded_100m": awarded, "bid_cover_pct": ratio, "yield_pct": rate, "source_url": result_url(ident)}


def offering_links(raw):
    out = []
    for href, title in page(raw).links:
        ident = re.fullmatch(r"javascript:popup\('https://www\.bok\.or\.kr/portal/bbs/P0001794/view\.do\?nttId=(\d+)&menuNo=200364'\)", href)
        code = re.search(r"국고\s*(\d{5}-\d{4}-(?:02|03|05|10|20|30|50)\d{2})", title)
        if ident and code and "발행공고" in title:
            out.append((ident[1], code[1]))
    if not out: raise ValueError("no offering notices")
    return out[:8]


def offering_url(ident):
    if not re.fullmatch(r"\d+", ident): raise ValueError("invalid notice id")
    return BOK_PORTAL + "/portal/bbs/P0001794/view.do?nttId=" + ident + "&menuNo=200364"


def offering_pdf_url(raw):
    paths = {href for href, _ in page(raw).links if re.fullmatch(r"/fileSrc/portal/[a-f0-9]+/\d+/[a-f0-9]+\.pdf", href)}
    if len(paths) != 1: raise ValueError("ambiguous offering PDF")
    return BOK_PORTAL + paths.pop()


def parse_offering_text(text, ident, code, today):
    text = re.sub(r"\s+", "", text)
    if "국고" + code not in text: raise ValueError("offering bond mismatch")
    section = re.search(r"\(1\)경쟁입찰(.*?)\(2\)", text)
    if not section: raise ValueError("missing competitive section")
    dates = re.findall(r"입찰일[:：](\d{4})\.(\d{1,2})\.(\d{1,2})\.", section[1])
    amounts = re.findall(r"발행예정금액[:：]([\d,]+)억원", section[1])
    if len(dates) != 1 or len(amounts) != 1: raise ValueError("ambiguous offering fields")
    date = dt.date(*map(int, dates[0])); amount = int(amounts[0].replace(",", ""))
    if date > today + dt.timedelta(days=90) or not 0 < amount < 1_000_000:
        raise ValueError("offering outside range")
    return {"id": ident, "date": date.isoformat(), "tenor": str(int(code.split("-")[2][:2])) + "년",
            "offered_100m": amount, "source_url": offering_url(ident)}


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


def build(old, now, fetch=request):
    today = now.astimezone(KST).date(); stamp = now.isoformat(timespec="seconds")
    feeds = {}; previous = old.get("feeds", {}) if old.get("schema") == 1 else {}
    def run(name, fn):
        try:
            payload = fn()
            feeds[name] = {"ok": True, "checked_at": stamp, "last_success": stamp, "data": payload}
        except Exception as e:
            prev = previous.get(name, {})
            feeds[name] = {"ok": False, "checked_at": stamp, "last_success": prev.get("last_success"), "data": prev.get("data")}
            print(f"[korea_market] {name}: {type(e).__name__}")
    for name, (chart_id, specs) in CHARTS.items():
        run(name, lambda chart_id=chart_id, specs=specs: parse_bok(fetch(BOK+f"/api/chart/exportChart?chart_id={chart_id}"), specs, today))
    for key, code in (("foreign3", "KRDRVFUBM3"), ("foreign10", "KRDRVFUBMA")):
        run(key, lambda code=code: parse_flows(fetch(FLOW_URL, {
            "fr_work_dt": (today-dt.timedelta(days=100)).strftime("%Y%m%d"), "to_work_dt": today.strftime("%Y%m%d"),
            "isu_cd": code, "date_sch_type": "dd", "prt_check": "SUN", "prt_type": "VL", "spread_tp": "1"}), today))
    run("calendar", lambda: parse_calendar(fetch(KTB+"/mnbyIsuCldr.do")))
    def auctions():
        # Re-read recent notices so corrections are picked up. Max eight public pages.
        return [parse_result(fetch(result_url(ident)), ident, tenor, today) for ident, tenor in result_links(fetch(RESULTS))]
    run("auctions", auctions)
    def offerings():
        return [parse_offering(fetch(offering_pdf_url(fetch(offering_url(ident)))), ident, code, today)
                for ident, code in offering_links(fetch(OFFER_LIST))]
    run("offerings", offerings)
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
            "notices": ["학습용 참고 자료이며 기존 11개 규칙 판정에는 쓰지 않습니다.",
                "한국은행 스냅샷 자료는 출처를 명시하여 비상업적 학습 목적으로 이용합니다. 원자료 저작권은 각 제공기관에 있습니다.",
                "금리차·기간 변화·누적 순매수·분포는 이 사이트의 계산값입니다. 분포는 최근 관측일 기준 365일이며 저평가·고평가 판정이 아닙니다."]}


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1]/"data")); args = ap.parse_args(argv)
    out = Path(args.out); path = out/"korea.json"
    try: old = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError): old = {}
    data = build(old, dt.datetime.now(UTC)); out.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp"); tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8"); tmp.replace(path)
    failed = [k for k, v in data["feeds"].items() if not v["ok"]]
    print(f"[korea_market] {len(data['cards'])} cards; {len(failed)} failed feeds")
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
