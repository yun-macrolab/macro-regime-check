#!/usr/bin/env python3
"""참고 자료 — 한국 국고채 금리 (2026-10-08 추가).

KB증권 리서치본부 채권크레딧팀이 텔레그램 공개 채널(t.me/jk_bond)에 평일 아침 올리는 '채권시장 일일동향' 글에서
국고채 금리 숫자만 읽어 <out>/ktb.json에 쌓는다. 공개 통계가 아니다 — 규칙 판정(regime_check)과 무관한 참고 절이고,
다른 스크립트는 이 파일을 읽지 않는다. 이 형식의 글은 2026-09-03부터 있다.

글에서 가져오는 것은 숫자뿐이다 (test_ktb_fetch.py가 강제):
  - 국고채 구역(머리글이 정확히 '■ 국고채 금리 (민평3사 기준)')의 3·5·10·30년 금리와 전일 대비 — 미국·크레딧·환율 구역,
    해설 문장, 글에 있던 어떤 글자도 산출물·로그에 싣지 않는다. 페이지에 나가는 문구는 이 파일에 정해 둔 것뿐이다.
  - 날짜는 글이 올라온 날(한국 시간). 글이 아침에 올라오므로 값은 직전 영업일 금리다.
형식이 바뀌면 닫힌 쪽으로: 머리글·만기 줄이 다르거나, 네 만기나 스프레드 줄 중 못 읽은 것이 있거나, 금리가 범위를 벗어나거나,
금리와 글에 적힌 스프레드가 맞지 않으면 그 글은 버린다. 가장 최근 글을 못 읽은 날은 읽은 것만 반영하고 종료코드 1(워크플로가 알림).
수신 실패·글 없음도 종료코드 1이고 어제 자료는 그대로 둔다. 새 글이 없는 날(휴일)은 파일을 건드리지 않는다.
조용히 멈추지 않게: 제목 줄이 바뀌면 그 글은 일일동향으로 보이지 않아 '새 글 없음'과 구분되지 않는다 — 그래서 저장분의
마지막 글이 STALE_DAYS일 넘게 묵으면 종료코드 1. 저장 파일이 깨져 있으면 덮어쓰지 않고 종료코드 1, 저장분보다 새 날짜인데
글 번호가 작은 글(채널 이름을 다른 곳이 쓰게 된 경우)은 받지 않고 종료코드 1.

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
    "국고채 금리는 공개 통계가 아니고 FRED 자료도 아니다. KB증권 리서치본부 채권크레딧팀이 텔레그램 공개 채널(t.me/jk_bond)에 "
    "올리는 '채권시장 일일동향' 글에서 국고채 금리 숫자만 옮겼다. 금리 기준은 그 글에 적힌 민평3사(민간 채권평가사 세 곳 "
    "평균)다. 글의 해설은 옮기지 않는다.",
    "날짜는 글이 올라온 날(한국 시간)이다. 글이 아침에 올라오므로 값은 직전 영업일 금리이고, 금리차는 "
    "macro-regime-check가 이 금리로 계산했다. 갱신 시각에 따라 하루 늦게 반영될 수 있다.",
    "이 사이트의 규칙 판정에는 쓰지 않는 참고 자료다. macro-regime-check는 KB증권·채권평가사와 관계가 없고, 채널 운영자나 "
    "금리 산출처가 요청하면 이 절을 내린다.",
]
KST = datetime.timezone(datetime.timedelta(hours=9))
TIMEOUT = 20
PAUSE = 1.5                       # 쪽 사이 쉬는 시간(초)
MAX_PAGES = 5
MAX_BYTES = 3_000_000
TENORS = ("3", "5", "10", "30")   # 네 만기 모두 있어야 한다 — 하나라도 못 읽으면 그 글을 버린다
PAIRS = (("10", "3"), ("30", "10"))    # 글에 있어야 하는 스프레드 줄 — 금리와 맞춰 본다
YEARS = 3                         # 그래프에 싣는 기간(규칙 카드와 같게)
TITLE_DRIFT = 3                   # 제목 날짜와 글 올린 날의 허용 차이(일)
SPREAD_TOL = 0.25                 # 금리 차와 글에 적힌 스프레드의 허용 오차(bp)
STALE_DAYS = 12                   # 저장분 마지막 글이 이보다 묵으면 실패로 끝낸다(긴 연휴의 글 간격 11일보다 길게)
BUDGET = 45                       # 한 쪽을 받는 데 쓰는 전체 시간 상한(초) — TIMEOUT은 요청·수신 한 번에만 걸린다

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
            m = re.fullmatch(rf"{CHANNEL}/(\d{{1,10}})", a.get("data-post") or "")
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
        posted = when.astimezone(KST).date() if when.tzinfo else None
    except (TypeError, ValueError, OverflowError):
        return "bad", "글 시각이나 제목 날짜를 읽을 수 없음"
    if posted is None:
        return "bad", "글 시각에 시간대가 없음"
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
    if any(t not in y for t in TENORS):
        return "bad", "네 만기(3·5·10·30년) 중 못 읽은 것이 있음"
    if any(pair not in stated for pair in PAIRS):
        return "bad", "스프레드 줄이 없어 금리를 맞춰 볼 수 없음"
    for t in TENORS:
        if t in y and not (0 < y[t] < 20 and abs(chg[t]) <= 100):
            return "bad", "금리나 변화 폭이 범위를 벗어남"
    for (a, b), v in stated.items():                              # 글에 적힌 스프레드로 금리를 맞춰 본다
        if a in y and b in y and abs((y[a] - y[b]) * 100 - v) > SPREAD_TOL:
            return "bad", "금리와 글에 적힌 스프레드가 맞지 않음"
    return "ok", {"date": posted, "post": msg["post"], "y": {t: y.get(t) for t in TENORS},
                  "chg": {t: chg.get(t) for t in TENORS}, "exact": posted == titled}


# ---------- 수신 ----------

def search_url(before=None):
    url = f"{PREVIEW_URL}?q={urllib.parse.quote(QUERY)}"
    return url if before is None else f"{url}&before={int(before)}"


def fetch(url, opener=None, clock=time.monotonic):
    """한 쪽을 받는다. 조금씩 흘려보내는 응답에 묶이지 않게 전체 BUDGET초를 넘기면 그만둔다."""
    start, chunks, size = clock(), [], 0
    with (opener or urllib.request.urlopen)(url, timeout=TIMEOUT) as r:
        final = urllib.parse.urlsplit(r.geturl())
        if (final.scheme, final.netloc, final.path) != ("https", "t.me", f"/s/{CHANNEL}"):
            raise RuntimeError("미리보기 주소가 아님 — 채널 미리보기가 꺼졌거나 주소가 바뀜")
        while True:
            if clock() - start > BUDGET:
                raise RuntimeError("응답이 너무 느림")
            chunk = r.read1(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES:
                raise RuntimeError("응답이 너무 큼")
            chunks.append(chunk)
    return b"".join(chunks).decode("utf-8", "replace")


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


def stored(out):
    """(검증된 저장 행, 온전한가). 파일이 없으면 ([], True). 있는데 못 읽거나 검증에서 떨어진 행이 있으면 온전하지 않다 —
    그 위에 오늘 읽은 한 쪽만 얹어 이력을 줄여 쓰지 않게 main이 멈춘다."""
    path = os.path.join(out, "ktb.json")
    if not os.path.exists(path):
        return [], True
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)["rows"]
    except (OSError, ValueError, KeyError, TypeError):
        return [], False
    rows = load_rows(out)
    return rows, isinstance(raw, list) and len(rows) == len(raw)


def merge(old, new):
    """저장분에 새로 읽은 글을 합친다 → (rows, 새 날 수, 고친 날 수). 같은 날에 글이 겹치면 제목 날짜가 올린 날과 같은
    글이 먼저이고(저장분은 그런 글로 본다), 그다음은 번호가 같거나 큰(나중) 글이 이긴다. 이번에 새로 넣은 날을 같은
    호출 안에서 다시 바꾼 것은 '고침'으로 세지 않는다."""
    by = {r[0]: r for r in old}
    exact = {r[0]: True for r in old}
    fresh, added, changed = set(), 0, 0
    for n in sorted(new, key=lambda r: r["post"]):
        cand = [n["date"], n["post"]] + [n["y"][t] for t in TENORS]
        cur, ex = by.get(n["date"]), n.get("exact", True)
        if cur is None:
            by[n["date"]], exact[n["date"]] = cand, ex
            fresh.add(n["date"])
            added += 1
        elif (ex, n["post"]) >= (exact[n["date"]], cur[1]) and cand != cur:
            by[n["date"]], exact[n["date"]] = cand, ex
            changed += n["date"] not in fresh
    return [by[d] for d in sorted(by)], added, changed


def carried(out, last):
    """저장 파일의 latest가 같은 글이면 그 '전일 대비'를 이어 쓴다(그 글을 이번에 다시 읽지 못한 날). 아니면 None."""
    try:
        with open(os.path.join(out, "ktb.json"), encoding="utf-8") as f:
            lt = json.load(f)["latest"]
        if (lt["date"], lt["post_url"]) != (last[0].isoformat(), f"{CHANNEL_URL}/{last[1]}"):
            return None
        chg = {r["tenor"].removesuffix("년"): r["change_bp"] for r in lt["rows"]}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
    return {"date": last[0], "post": last[1],
            "chg": {t: chg.get(t) if type(chg.get(t)) in (int, float) else None for t in TENORS}}


def differs(out, data):
    """저장 파일과 내용이 다른가(갱신 시각은 빼고). 파일이 없거나 못 읽으면 다르다 — 같으면 쓰지 않는다(빈 커밋 방지)."""
    try:
        with open(os.path.join(out, "ktb.json"), encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        return True
    return not isinstance(old, dict) or any(old.get(k) != v for k, v in data.items() if k != "updated_at")


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
    old, intact = stored(out)
    if not intact:
        print("[ktb_fetch] 저장분(ktb.json)을 읽을 수 없거나 일부 행이 깨져 있음 — 덮어쓰지 않음", file=sys.stderr)
        return 1
    # 글 번호는 날짜와 함께 커진다 — 저장분보다 새 날짜인데 번호가 작은 글은 받지 않는다(채널 이름이 다른 곳으로 넘어간 경우)
    top = max((r[1] for r in old), default=0)
    odd = [g for g in good if old and g["date"] > old[-1][0] and g["post"] < top]
    good = [g for g in good if g not in odd]
    rows, added, changed = merge(old, good)
    if not daily or not rows:
        print("[ktb_fetch] 읽을 수 있는 일일동향 글이 없음 — 채널 형식·검색 확인", file=sys.stderr)
        return 1
    latest = next((g for g in good if (g["date"], g["post"]) == (rows[-1][0], rows[-1][1])), None)
    data = build(rows, latest or carried(out, rows[-1]), now)
    if differs(out, data):
        write(out, data)
    print(f"[ktb_fetch] {rows[-1][0]} 글까지 — 새로 {added}일 · 고침 {changed}일 · 읽지 못한 글 {len(daily) - len(good) - len(odd)}개")
    failed = False
    if max(daily, key=lambda x: x[0])[1][0] != "ok":
        print("[ktb_fetch] 가장 최근 일일동향 글을 읽지 못함 — 글 형식이 바뀌었는지 확인", file=sys.stderr)
        failed = True
    if odd:
        print("[ktb_fetch] 글 번호가 거꾸로 간 글이 있어 받지 않음 — 채널이 바뀌었는지 확인", file=sys.stderr)
        failed = True
    if (now.astimezone(KST).date() - rows[-1][0]).days > STALE_DAYS:
        print(f"[ktb_fetch] 마지막으로 읽은 글이 {STALE_DAYS}일 넘게 묵음 — 제목 형식이 바뀌었거나 연재가 멈췄는지 확인",
              file=sys.stderr)
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
