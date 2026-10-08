#!/usr/bin/env python3
"""읽기 노트의 정적 그래프 자료 — 받아 둔 값(<out>/notes_charts.json). 손으로 돌린다(아침 워크플로에서는 돌지 않는다).

지금은 그래프 하나: 일본·미국 소비자물가 상승률(연평균 전년비, 1995년부터).
  일본  FRED FPCPITOTLZGJPN — World Bank의 연간 상승률(%)을 받은 그대로
  미국  FRED CPIAUCSL — U.S. Bureau of Labor Statistics의 월별 지수를 이 저장소가 연평균으로 바꿔 전년과 견준 값.
        그 해와 전 해에 모두 값이 있는 달만 같은 달끼리 평균하고, 그런 달이 MIN_MONTHS개에 못 미치는 해는 싣지 않는다
        (2025-10은 FRED 자료에 값이 없어 2025년은 11개 달이다).
        세계은행의 미국 계열(FPCPITOTLZGUSA — 2024년까지라 그리지는 않는다)과 겹치는 해를 맞춰 보고, 차이가
        CHECK_TOL(%p)을 넘거나 겹치는 해가 모자라면 멈춘다. 2026-10-08 실행에서 1995~2024년 최대 차이 0.04%p.

자료 조건(닫힌 쪽으로) — 하나라도 어긋나면 파일을 쓰지 않고 종료코드 1 (test_notes_charts.py가 강제):
  - 계열 쪽(fred.stlouisfed.org/series/<ID>)의 저작권 표시가 'Public Domain: Citation Requested'나
    'Copyrighted: Citation Required'일 것. 'Copyrighted: Pre-approval Required'이거나 표시를 읽지 못하면 쓰지 않는다
    (저장소가 재배포 제한 계열을 다루는 기준 — render_public.RESTRICTED — 과 같다).
  - 마지막 값이 MIN_LAST_YEAR년 이후일 것.
  일본의 OECD 경유 월별 계열(CPALTT01JPM659N · JPNCPIALLMINMEI, 표시는 Copyrighted: Citation Required)은
  2021-06에서 멈춰 있어 쓰지 않았다(2026-10-08 확인).
출처 표기는 저장소의 다른 FRED 자료와 같게: 그래프 아래 출처 줄(FRED가 적은 출처 + FRED 경유 + 계산한 선 표시 + 받은 날),
계열마다 FRED 권장 인용. 페이지에 나가는 문구는 이 파일에 정해 둔 것뿐이다.

수신: urllib 기본 헤더(머리말을 붙이면 FRED가 응답을 멈춘다), 요청마다 20초.
산출: <out>/notes_charts.json — {schema, charts: {cpi_jp_us: {…}}} · 가로축이 연도인 그래프(site/notes.js가 그린다)
사용법: python notes_charts.py [--out data]
"""
import os, sys, json, math, argparse, datetime, urllib.request
from html.parser import HTMLParser

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import fred_fetch as ff

SCHEMA = 1
REPO = os.path.dirname(SCRIPTS)
DEFAULT_OUT = os.path.join(REPO, "data")
FRED_PAGE = "https://fred.stlouisfed.org/series/{}"
FRED_CSV = ff.FRED_CSV
TIMEOUT = 20
MAX_BYTES = 3_000_000
START = 1995                      # 그래프의 첫 해
MIN_LAST_YEAR = 2025              # 마지막 값이 이 해보다 앞이면 쓰지 않는다
MIN_MONTHS = 11                   # 연평균 전년비를 계산하는 데 필요한 달 수(그 해와 전 해에 모두 값이 있는 달)
CHECK_TOL = 0.1                   # 계산한 미국 값과 세계은행 미국 계열의 허용 차이(%p)
CHECK_YEARS = 10                  # 맞춰 볼 해가 이보다 적으면 맞춰 본 것으로 치지 않는다
JP, US, US_CHECK = "FPCPITOTLZGJPN", "CPIAUCSL", "FPCPITOTLZGUSA"
# FRED 계열 쪽이 적은 출처(Source)와 권장 인용의 제목(2026-10-08 확인)
SOURCE = {JP: ("World Bank", "Inflation, consumer prices for Japan"),
          US: ("U.S. Bureau of Labor Statistics",
               "Consumer Price Index for All Urban Consumers: All Items in U.S. City Average")}
# 계열 쪽의 저작권 표시(series-tag) → FRED 법적 고지가 쓰는 이름
MARKS = {"public domain: citation requested": "Public Domain: Citation Requested",
         "copyrighted: citation required": "Copyrighted: Citation Required",
         "copyrighted: pre-approval required": "Copyrighted: Pre-approval Required"}
USABLE = ("Public Domain: Citation Requested", "Copyrighted: Citation Required")
_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December")
TITLE = "일본·미국 소비자물가 상승률"
NOTE = "연평균을 전년과 견준 값 — 한 해에 점 하나"
HOW = ("일본은 세계은행(World Bank)이 낸 연간 상승률을 받은 그대로, 미국은 미 노동통계국(BLS)의 월별 지수(계절조정)를 "
       "macro-regime-check가 연평균으로 바꿔 전년과 견준 값이다. 미국 선은 발표 기관이 낸 값이 아니다.")
FROZEN = "받아 둔 값이라 매일 갱신되지 않는다 — 받은 날 뒤의 개정은 반영하지 않았다."


# ---------- 수신 · 자료 조건 ----------

class _Tags(HTMLParser):
    """FRED 계열 쪽의 <meta name="series-tag" content="…"> 값들."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and a.get("name") == "series-tag" and a.get("content"):
            self.tags.append(" ".join(a["content"].lower().split()))


def copyright_mark(page):
    """계열 쪽의 저작권 표시(MARKS의 값). 표시가 없거나 서로 다른 표시가 함께 있으면 None — 확인하지 못한 것으로 친다."""
    p = _Tags()
    p.feed(page)
    p.close()
    found = {MARKS[t] for t in p.tags if t in MARKS}
    return found.pop() if len(found) == 1 else None


def fetch(url, opener=None):
    with (opener or urllib.request.urlopen)(url, timeout=TIMEOUT) as r:    # 주소만 넘긴다 — 머리말을 붙이지 않는다
        body = r.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise RuntimeError("응답이 너무 큼")
    return body.decode("utf-8", "replace")


def refusal(sid, mark, last_year):
    """이 계열을 쓰면 안 되는 이유. 써도 되면 None."""
    if mark is None:
        return f"{sid}: 저작권 표시를 확인하지 못함"
    if mark not in USABLE:
        return f"{sid}: 표시가 '{mark}' — 싣지 않는다"
    if last_year is None or last_year < MIN_LAST_YEAR:
        return f"{sid}: {MIN_LAST_YEAR}년 이후 값이 없음"
    return None


# ---------- 계산 ----------

def yearly(series):
    """연간 계열 [(date, 값)] → {해: 값}."""
    return {d.year: v for d, v in series}


def annual_change(monthly, min_months=MIN_MONTHS):
    """월별 지수 [(date, 값)] → {해: (연평균 전년비 %, 쓴 달 수)}. 그 해와 전 해에 모두 값이 있는 달만 같은 달끼리
    평균해 견준다. 그런 달이 min_months개에 못 미치는 해(덜 끝난 해, 빈 달이 많은 해)는 싣지 않는다."""
    by = {(d.year, d.month): v for d, v in monthly}
    out = {}
    for y in sorted({y for y, _ in by}):
        months = [m for m in range(1, 13) if (y, m) in by and (y - 1, m) in by]
        prev = sum(by[(y - 1, m)] for m in months)
        if len(months) >= min_months and prev > 0:
            out[y] = ((sum(by[(y, m)] for m in months) / prev - 1) * 100, len(months))
    return out


def crosscheck(mine, ref):
    """계산한 값 {해: (값, 달 수)}과 참고 계열 {해: 값}을 START부터 겹치는 해에서 맞춰 본다 → {first, last, max}.
    max는 가장 큰 차이(%p)를 소수 둘째 자리로 올린 값. 겹치는 해가 CHECK_YEARS에 못 미치면 None."""
    years = sorted(y for y in mine if y in ref and y >= START)
    if len(years) < CHECK_YEARS:
        return None
    worst = max(abs(mine[y][0] - ref[y]) for y in years)
    return {"first": years[0], "last": years[-1], "max": math.ceil(round(worst * 100, 6)) / 100}


def citation(sid, day):
    """FRED 권장 인용 형식 그대로: 출처, 제목 [ID], retrieved from FRED, …; 주소, 받은 날."""
    source, title = SOURCE[sid]
    return (f"{source}, {title} [{sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; "
            f"{FRED_PAGE.format(sid)}, {_MONTHS[day.month - 1]} {day.day}, {day.year}.")


def _points(values):
    return [[y, round(values[y], 2) + 0.0] for y in sorted(values) if y >= START]


def build(jp, us, marks, day, check):
    """일본 {해: 값}, 미국 {해: (값, 달 수)}, 계열별 저작권 표시, 받은 날, 맞춰 본 결과 → 그래프 dict(문구는 정해 둔 것만)."""
    short = [f"미국 {y}년은 값이 있는 {n}개 달로 계산했다(그 해나 전 해에 값이 없는 달은 뺐다)."
             for y, (_, n) in sorted(us.items()) if y >= START and n < 12]
    checked = (f"같은 방식으로 계산한 미국 {check['first']}~{check['last']}년 값은 세계은행의 미국 계열"
               f"({US_CHECK})과 최대 {check['max']:.2f}%p 차이다.")
    marked = f"FRED의 저작권 표시({day.isoformat()} 확인): " + " · ".join(f"{sid} — {marks[sid]}" for sid in (JP, US)) + "."
    return {
        "key": "cpi_jp_us", "title": TITLE, "unit": "%", "zero": True, "note": NOTE,
        "source_note": (f"자료: {SOURCE[JP][0]} · {SOURCE[US][0]} (via FRED) · 미국 선은 macro-regime-check가 "
                        f"월별 지수로 계산한 값 · {day.isoformat()}에 받은 값"),
        "retrieved": day.isoformat(),
        "notices": [HOW, *short, checked, FROZEN, marked, *(citation(sid, day) for sid in (JP, US))],
        "series": [{"id": sid, "source": SOURCE[sid][0], "mark": marks[sid], "url": FRED_PAGE.format(sid),
                    "citation": citation(sid, day)} for sid in (JP, US)],
        "lines": [{"key": "jp", "label": "일본", "series": [JP], "computed": False, "points": _points(jp)},
                  {"key": "us", "label": "미국(계산값)", "series": [US], "computed": True,
                   "points": _points({y: v for y, (v, _) in us.items()})}],
    }


def write(out, data):
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "notes_charts.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    os.replace(tmp, path)


def main(argv=None, opener=None, today=None):
    for stream in (sys.stdout, sys.stderr):       # cp949 콘솔에서도 안내 문구(긴 줄표)가 죽지 않게 — notes_build와 같은 처리
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="읽기 노트의 정적 그래프 자료 받기(<out>/notes_charts.json) — 손으로 돌린다")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    a = ap.parse_args(argv)
    day = today or datetime.date.today()
    try:
        marks = {sid: copyright_mark(fetch(FRED_PAGE.format(sid), opener)) for sid in (JP, US)}
        raw = {sid: ff.parse_csv(fetch(FRED_CSV.format(sid=sid), opener)) for sid in (JP, US, US_CHECK)}
    except Exception as e:                        # 수신 어디서 실패해도 받아 둔 파일은 그대로
        print(f"[notes_charts] 수신 실패: {type(e).__name__}", file=sys.stderr)
        return 1
    bad = [r for r in (refusal(sid, marks[sid], raw[sid][-1][0].year if raw[sid] else None) for sid in (JP, US)) if r]
    for reason in bad:
        print(f"[notes_charts] {reason}", file=sys.stderr)
    if bad:
        return 1
    us = annual_change(raw[US])
    check = crosscheck(us, yearly(raw[US_CHECK]))
    if check is None or check["max"] > CHECK_TOL or max(us, default=0) < MIN_LAST_YEAR:
        print("[notes_charts] 계산한 미국 값을 참고 계열과 맞춰 보지 못했거나 차이가 크다 — 싣지 않는다", file=sys.stderr)
        return 1
    chart = build(yearly(raw[JP]), us, marks, day, check)
    write(os.path.abspath(a.out), {"schema": SCHEMA, "charts": {chart["key"]: chart}})
    print(f"[notes_charts] {chart['key']}: {START}~{chart['lines'][0]['points'][-1][0]}년 · 맞춰 본 차이 최대 {check['max']:.2f}%p")
    return 0


if __name__ == "__main__":
    sys.exit(main())
