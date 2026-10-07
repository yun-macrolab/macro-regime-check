#!/usr/bin/env python3
"""참고 자료 — 한국 국고채 금리 (2026-10-08 추가).

KB증권 리서치본부 채권크레딧팀이 텔레그램 공개 채널(t.me/jk_bond)에 평일 아침 올리는 '채권시장 일일동향' 글에서
국고채 금리 숫자만 읽어 <out>/ktb.json에 쌓는다. 공개 통계가 아니다 — 규칙 판정(regime_check)과 무관한 참고 절이고,
다른 스크립트는 이 파일을 읽지 않는다. 이 형식의 글은 2026-09-03부터 있다.

글에서 가져오는 것은 숫자뿐이다 (test_ktb_fetch.py가 강제):
  - 국고채 구역(머리글이 정확히 '■ 국고채 금리 (민평3사 기준)')의 3·5·10·30년 금리와 전일 대비 — 미국·크레딧·환율 구역,
    해설 문장, 글에 있던 어떤 글자도 산출물·로그에 싣지 않는다. 페이지에 나가는 문구는 이 파일에 정해 둔 것뿐이다.
  - 날짜는 글이 올라온 날(한국 시간). 글이 아침에 올라오므로 값은 직전 영업일 금리다.
형식이 바뀌면 닫힌 쪽으로: 머리글·만기 줄이 다르거나, 금리가 범위를 벗어나거나, 금리와 글에 적힌 스프레드가 맞지 않으면
그 글은 버린다. 가장 최근 글을 못 읽은 날은 읽은 것만 반영하고 종료코드 1(워크플로가 알림).
수신 실패·글 없음도 종료코드 1이고 어제 자료는 그대로 둔다. 새 글이 없는 날(휴일)은 파일을 건드리지 않는다.

수신은 하루 한 번 검색 결과 한 쪽(최근 20개 글)만 — urllib 기본 헤더, 20초 타임아웃. 처음 채울 때만 --pages로 뒤쪽까지.

산출: <out>/ktb.json — rows(저장분 전체) · latest(가장 최근 글의 표) · charts(site/charts.js가 그리는 형태, 최근 3년)
사용법: python ktb_fetch.py [--out data] [--pages 1]
"""
import os, sys, re, json, time, argparse, datetime, urllib.request, urllib.parse
from html.parser import HTMLParser

SCHEMA = 1
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(REPO, "data")
CHANNEL = "jk_bond"
CHANNEL_URL = f"https://t.me/{CHANNEL}"
PREVIEW_URL = f"https://t.me/s/{CHANNEL}"
QUERY = "채권시장 일일동향"
SOURCE = "KB증권 리서치본부 채권크레딧팀 텔레그램 채널"
BASIS = "민평3사 기준"
SOURCE_NOTE = f"자료: {SOURCE} '채권시장 일일동향'({BASIS})"
NOTICES = [
    "국고채 금리는 공개 통계가 아니다. KB증권 리서치본부 채권크레딧팀이 텔레그램 공개 채널(t.me/jk_bond)에 올리는 "
    "'채권시장 일일동향' 글에서 국고채 금리 숫자만 옮겼다(민평3사 기준). 글의 해설은 옮기지 않는다.",
    "날짜는 글이 올라온 날(한국 시간)이다. 글이 아침에 올라오므로 값은 직전 영업일 금리이고, 금리차는 "
    "macro-regime-check가 이 금리로 계산했다. 갱신 시각에 따라 하루 늦게 반영될 수 있다.",
    "위 규칙 판정에는 쓰지 않는 참고 자료다. macro-regime-check는 KB증권과 관계가 없고, 원 출처가 요청하면 이 절을 내린다.",
]
KST = datetime.timezone(datetime.timedelta(hours=9))
TIMEOUT = 20
PAUSE = 1.5                       # 쪽 사이 쉬는 시간(초)
MAX_PAGES = 5
MAX_BYTES = 3_000_000
TENORS = ("3", "5", "10", "30")
CORE = ("3", "10")                # 없으면 그 글을 버린다
YEARS = 3                         # 그래프에 싣는 기간(규칙 카드와 같게)
TITLE_DRIFT = 3                   # 제목 날짜와 글 올린 날의 허용 차이(일)
SPREAD_TOL = 0.25                 # 금리 차와 글에 적힌 스프레드의 허용 오차(bp)

TITLE = re.compile(r"^(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일\s*채권시장\s*일일동향$")
HEADER = f"■ 국고채 금리 ({BASIS})"
TENOR = re.compile(r"^(\d{1,2})년물\s*:\s*(\d{1,2}(?:\.\d{1,4})?)%\s*\((-?\d{1,3}(?:\.\d{1,2})?)bp\)$")
SPREAD = re.compile(r"^(\d{1,2})-(\d{1,2})년 스프레드\s*:\s*(-?\d{1,4}(?:\.\d{1,2})?)bp\s*\((-?\d{1,3}(?:\.\d{1,2})?)bp\)$")


# ---------- 미리보기 페이지 → 글 ----------

class _Messages(HTMLParser):
    """t.me/s 미리보기 HTML에서 이 채널 글의 (글 번호, 올린 시각, 본문 줄)을 뽑는다. 본문은 글자만(태그는 벗긴다)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.cur, self.depth, self.msg_depth, self.text_depth, self.buf = [], None, 0, None, None, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if tag == "div":
            m = re.fullmatch(rf"{CHANNEL}/(\d+)", a.get("data-post") or "")
            if self.cur is None and "tgme_widget_message" in cls and m:
                self.cur, self.msg_depth = {"post": int(m.group(1)), "time": None, "text": None}, self.depth
            elif (self.cur is not None and self.text_depth is None and self.cur["text"] is None
                  and "tgme_widget_message_text" in cls and "js-message_text" in cls):     # 답글 미리보기는 표식이 없다
                self.text_depth, self.buf = self.depth, []
            self.depth += 1
        elif tag == "br" and self.text_depth is not None:
            self.buf.append("\n")
        elif tag == "time" and self.cur is not None and a.get("datetime"):
            self.cur["time"] = a["datetime"]                      # 글 아래쪽의 올린 시각이 마지막에 온다

    def handle_endtag(self, tag):
        if tag != "div":
            return
        self.depth -= 1
        if self.text_depth is not None and self.depth == self.text_depth:
            self.cur["text"], self.text_depth = "".join(self.buf), None
        if self.cur is not None and self.depth == self.msg_depth:
            self.out.append(self.cur)
            self.cur, self.msg_depth = None, None

    def handle_data(self, data):
        if self.text_depth is not None:
            self.buf.append(data)


def messages(page):
    """[{post, time, lines}] — 본문이 없는 글(사진만)은 뺀다. 줄은 앞뒤 공백을 떼고 빈 줄은 버린다."""
    p = _Messages()
    p.feed(page)
    p.close()
    out = []
    for m in p.out:
        lines = [" ".join(x.split()) for x in (m["text"] or "").split("\n")]
        lines = [x for x in lines if x]
        if lines:
            out.append({"post": m["post"], "time": m["time"], "lines": lines})
    return out


def parse_daily(msg):
    """일일동향 글이 아니면 None. 맞으면 ("ok", {date, post, y, chg}) 또는 ("bad", 사유) — 사유는 내부용(싣지 않는다)."""
    lines = msg["lines"]
    title = next((m for m in map(TITLE.match, lines[:3]) if m), None)
    if not title:
        return None
    try:
        when = datetime.datetime.fromisoformat(msg["time"])
        titled = datetime.date(*map(int, title.groups()))
    except (TypeError, ValueError):
        return "bad", "글 시각이나 제목 날짜를 읽을 수 없음"
    if when.tzinfo is None:
        return "bad", "글 시각에 시간대가 없음"
    posted = when.astimezone(KST).date()
    if abs((posted - titled).days) > TITLE_DRIFT:
        return "bad", "제목 날짜가 글 올린 날과 다름"
    heads = [i for i, x in enumerate(lines) if x.startswith("■") and "국고채 금리" in x]
    if len(heads) != 1 or lines[heads[0]] != HEADER:
        return "bad", "국고채 머리글이 다름(기준 표기 포함)"
    y, chg, stated = {}, {}, {}
    for x in lines[heads[0] + 1:]:
        if x.startswith("■"):                                    # 다음 구역(크레딧 등)은 읽지 않는다
            break
        m = TENOR.match(x)
        if m:
            if m.group(1) in y:
                return "bad", "같은 만기가 두 번"
            y[m.group(1)], chg[m.group(1)] = float(m.group(2)), float(m.group(3))
        elif re.match(r"^\d{1,2}년물", x):
            return "bad", "만기 줄 형식이 다름"
        else:
            m = SPREAD.match(x)
            if m:
                stated[(m.group(1), m.group(2))] = float(m.group(3))
    if any(t not in y for t in CORE):
        return "bad", "3년물·10년물이 없음"
    for t in TENORS:
        if t in y and not (0 < y[t] < 20 and abs(chg[t]) <= 100):
            return "bad", "금리나 변화 폭이 범위를 벗어남"
    for (a, b), v in stated.items():                              # 글에 적힌 스프레드로 금리를 맞춰 본다
        if a in y and b in y and abs((y[a] - y[b]) * 100 - v) > SPREAD_TOL:
            return "bad", "금리와 글에 적힌 스프레드가 맞지 않음"
    return "ok", {"date": posted, "post": msg["post"], "y": {t: y.get(t) for t in TENORS},
                  "chg": {t: chg.get(t) for t in TENORS}}


# ---------- 수신 ----------

def search_url(before=None):
    url = f"{PREVIEW_URL}?q={urllib.parse.quote(QUERY)}"
    return url if before is None else f"{url}&before={int(before)}"


def fetch(url, opener=None):
    with (opener or urllib.request.urlopen)(url, timeout=TIMEOUT) as r:
        final = urllib.parse.urlsplit(r.geturl())
        if (final.scheme, final.netloc, final.path) != ("https", "t.me", f"/s/{CHANNEL}"):
            raise RuntimeError("미리보기 주소가 아님 — 채널 미리보기가 꺼졌거나 주소가 바뀜")
        raw = r.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise RuntimeError("응답이 너무 큼")
    return raw.decode("utf-8", "replace")


def collect(pages=1, opener=None, sleep=time.sleep):
    """검색 결과를 최근 쪽부터 pages쪽(최대 MAX_PAGES)까지. 다음 쪽 주소는 받은 글의 가장 작은 번호로 직접 만든다."""
    out, seen, before = [], set(), None
    for i in range(max(1, min(int(pages), MAX_PAGES))):
        if i:
            sleep(PAUSE)
        ms = messages(fetch(search_url(before), opener))
        fresh = [m for m in ms if m["post"] not in seen]
        if not fresh:
            break
        out += fresh
        seen.update(m["post"] for m in fresh)
        before = min(m["post"] for m in ms)
    return out


# ---------- 저장분 · 산출물 ----------

def _yield_ok(v, optional=False):
    return optional if v is None else type(v) in (int, float) and 0 < v < 20


def load_rows(out):
    """<out>/ktb.json의 rows를 검증해 [[date, post, y3, y5, y10, y30]] 날짜순. 없거나 깨졌으면 []."""
    try:
        with open(os.path.join(out, "ktb.json"), encoding="utf-8") as f:
            rows = json.load(f)["rows"]
    except (OSError, ValueError, KeyError, TypeError):
        return []
    by = {}
    for r in rows if isinstance(rows, list) else []:
        try:
            if not (isinstance(r, list) and len(r) == 6 and type(r[1]) is int and r[1] > 0):
                continue
            d = datetime.date.fromisoformat(r[0])
        except (TypeError, ValueError):
            continue
        if _yield_ok(r[2]) and _yield_ok(r[4]) and _yield_ok(r[3], True) and _yield_ok(r[5], True):
            if d not in by or r[1] > by[d][1]:
                by[d] = [d, r[1]] + [None if v is None else float(v) for v in r[2:]]
    return [by[d] for d in sorted(by)]


def merge(old, new):
    """저장분에 새로 읽은 글을 합친다 → (rows, 새 날 수, 고친 날 수). 같은 날은 번호가 같거나 큰(나중) 글이 이긴다."""
    by = {r[0]: r for r in old}
    added = changed = 0
    for n in sorted(new, key=lambda r: r["post"]):
        cand = [n["date"], n["post"]] + [n["y"][t] for t in TENORS]
        cur = by.get(n["date"])
        if cur is None:
            by[n["date"]] = cand
            added += 1
        elif n["post"] >= cur[1] and cand != cur:
            by[n["date"]] = cand
            changed += 1
    return [by[d] for d in sorted(by)], added, changed


def _spread(y, a, b):
    return None if y[a] is None or y[b] is None else round((y[a] - y[b]) * 100, 1) + 0.0


def chart_table():
    """그래프 정의 — 문구와 계산. 선은 3개까지(분류색이 3개다) — 5년물은 표에만."""
    return [
        {"key": "ktb_yields", "title": "국고채 금리", "unit": "%", "zero": False, "computed": False,
         "note": "날짜는 글이 올라온 날 — 값은 직전 영업일 금리",
         "lines": [{"key": "ktb3", "label": "국고 3년", "calc": lambda y: y["3"]},
                   {"key": "ktb10", "label": "국고 10년", "calc": lambda y: y["10"]},
                   {"key": "ktb30", "label": "국고 30년", "calc": lambda y: y["30"]}]},
        {"key": "ktb_spreads", "title": "국고채 장단기 금리차", "unit": "bp", "zero": True, "computed": True, "note": None,
         "lines": [{"key": "s10_3", "label": "10년−3년", "calc": lambda y: _spread(y, "10", "3")},
                   {"key": "s30_10", "label": "30년−10년", "calc": lambda y: _spread(y, "30", "10")}]},
    ]


def build(rows, latest, now):
    """rows(날짜순 저장분 전체)와 이번에 읽은 가장 최근 글(latest, 없으면 None) → 산출물 dict."""
    last = rows[-1]
    start = last[0] - datetime.timedelta(days=365 * YEARS + 1)
    recent = [(r[0].isoformat(), dict(zip(TENORS, r[2:]))) for r in rows if r[0] >= start]
    charts = []
    for c in chart_table():
        charts.append({
            "key": c["key"], "title": c["title"], "unit": c["unit"], "years": YEARS, "zero": c["zero"],
            "threshold": None, "note": c["note"],
            "source_note": SOURCE_NOTE + (" · 금리차는 macro-regime-check가 이 금리로 계산한 값" if c["computed"] else ""),
            "notices": [],
            "lines": [{"key": ln["key"], "label": ln["label"], "role": "series", "series": [], "derived": c["computed"],
                       "points": [[d, ln["calc"](y)] for d, y in recent]} for ln in c["lines"]]})
    y = dict(zip(TENORS, last[2:]))
    chg = latest["chg"] if latest and (latest["date"], latest["post"]) == (last[0], last[1]) else {}
    spreads = (("10년−3년", _spread(y, "10", "3")), ("30년−10년", _spread(y, "30", "10")))
    return {
        "schema": SCHEMA, "date": last[0].isoformat(), "updated_at": now.isoformat(timespec="seconds"),
        "source": {"name": SOURCE, "url": CHANNEL_URL, "basis": BASIS}, "notices": list(NOTICES),
        "latest": {"date": last[0].isoformat(), "post_url": f"{CHANNEL_URL}/{last[1]}",
                   "rows": [{"tenor": f"{t}년", "yield": y[t], "change_bp": chg.get(t)} for t in TENORS
                            if y[t] is not None],
                   "spreads": [{"label": label, "bp": v} for label, v in spreads if v is not None]},
        "charts": charts,
        "rows": [[r[0].isoformat()] + r[1:] for r in rows],
    }


def write(out, data):
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "ktb.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    os.replace(tmp, path)


def main(argv=None, opener=None, sleep=time.sleep, now=None):
    ap = argparse.ArgumentParser(description="텔레그램 채널의 '채권시장 일일동향' 글 → 국고채 참고 자료(<out>/ktb.json)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    ap.add_argument("--pages", type=int, default=1, help=f"검색 결과 쪽 수 (기본 1, 최대 {MAX_PAGES} — 처음 채울 때만)")
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    # 공개 저장소의 Actions 로그에 남는다 — 날짜·개수만 찍고 값과 글의 글자는 찍지 않는다
    try:
        daily = [(m["post"], r) for m in collect(a.pages, opener, sleep) for r in [parse_daily(m)] if r]
    except Exception as e:                       # 수신·해석 어디서 실패해도 어제 자료는 그대로
        print(f"[ktb_fetch] 수신 실패: {type(e).__name__}", file=sys.stderr)
        return 1
    good = [r[1] for _, r in daily if r[0] == "ok"]
    rows, added, changed = merge(load_rows(out), good)
    if not daily or not rows:
        print("[ktb_fetch] 읽을 수 있는 일일동향 글이 없음 — 채널 형식·검색 확인", file=sys.stderr)
        return 1
    if added or changed or not os.path.exists(os.path.join(out, "ktb.json")):
        latest = next((g for g in good if (g["date"], g["post"]) == (rows[-1][0], rows[-1][1])), None)
        write(out, build(rows, latest, now))
    print(f"[ktb_fetch] {rows[-1][0]} 글까지 — 새로 {added}일 · 고침 {changed}일 · 읽지 못한 글 {len(daily) - len(good)}개")
    if max(daily, key=lambda x: x[0])[1][0] != "ok":
        print("[ktb_fetch] 가장 최근 일일동향 글을 읽지 못함 — 글 형식이 바뀌었는지 확인", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
