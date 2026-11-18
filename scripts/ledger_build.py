#!/usr/bin/env python3
"""변화 층과 규칙 장부 (2026-11-18 운영자 결정) — 저장소에 이미 있는 공개 자료만 읽는다(네트워크 없음, 표준 라이브러리만).

읽는 것   <data>/history/YYYY-MM-DD.json  render_public이 날마다 쓴 그날의 공개본 사본(history_copy). 다시 계산하지 않는다 —
                                         그날 사이트가 공개한 상태(그때의 FRED 현재 개정치)가 그대로 기록이다.
          <data>/charts.json             render_charts의 '금리의 구조' 주간 점 — DGS10(yield10/dgs10) · T10Y2Y(term/t10y2y) ·
                                         THREEFYTP10(term/tp). FRED가 고치면 바뀌고, 그래프는 최근 몇 년(지금 5년)만 싣는 창이라
                                         날마다 한 주씩 옮겨 간다 — 결과와 평균은 이 장부를 만든 날의 charts.json으로 매번 다시 잰다.
쓰는 것   <out>/changes.json  이번 주 달라진 것 — 날짜별 기록끼리 견준 결정적인 차이(직전 기록 · 1주 전 · 4주 전, 최근 30일의 전환)
          <out>/ledger.json   규칙 장부 — 규칙마다 지금 상태 · 언제부터 · 전환 목록과, 평가 약속(아래)에 따른 전환 뒤의 금리 변화

평가 약속 1판(PROTOCOL_*, 2026-11-18 고정 — 측정 기록이지 예측이 아니다. 어느 규칙에도 금리가 오르거나 내리는 쪽을 정해 두지 않는다)
  전환     한 규칙의 날짜별 기록에서 상태가 충족·미충족(met · not_met)이고, 그 앞의 마지막 판정된 상태와 다른 날. 판정 불가(unknown)인
           날은 건너뛴다(unknown_days로 센다 — 전환을 만들지도 끊지도 않는다). 처음 판정된 상태는 출발 상태이지 전환이 아니다.
           나중에 더한 규칙(2026-10-14의 둘)은 처음 실린 기록부터 센다.
  약속 전  전환 날 < PROTOCOL_FIXED이면 before_protocol — 목록에는 싣되 요약 통계에서 뺀다(약속을 정할 때 그 뒤의 금리 변화 일부가
           이미 보였다).
  결과     기간 H(HORIZONS 주)·시리즈 s마다: 출발 = 전환 날 이후(그날 포함) START_DAYS일 안의 첫 주간 점 — 그날 기록은 그 앞날까지의
           자료로 정해졌으므로 전환을 만든 움직임은 결과에 들지 않는다(대신 전환 날부터 출발 점까지의 며칠은 빠진다). 그 선에 전환 날
           이후의 점이 아직 없으면 'pending'(start null), START_DAYS일 안에 점이 없으면 'missing'. 끝 = 출발 날짜 + 7H일에 가장
           가까운 주간 점(±TOL_DAYS일 안, 같은 거리면 이른 점). 출발 날짜 + 7H + TOL_DAYS가 그 선의 마지막 점 날짜보다 뒤면
           'pending', 범위 안인데 맞는 점이 없으면 'missing', 그 밖은 'done' — change_bp = (끝 − 출발) × 100, demeaned_bp =
           change_bp − baseline_bp(H, s). 덜 찬 마지막 주의 점이 출발 점이면 그 주가 차며 날짜가 옮겨 갈 수 있지만, 그때 결과는
           늘 'pending'이라 'done'이 된 결과의 출발 점은 옮겨 가지 않는다.
  평균     baseline_bp(H, s) = 같은 선의 모든 점 i에서 같은 규칙(±TOL_DAYS, 'pending'인 i는 뺀다)으로 맞춘 j까지의 (점 j − 점 i) × 100의
           평균. 쌍의 수와 첫 출발·마지막 끝 날짜를 baseline_detail에 함께 싣는다. 그래프 창이 옮겨 가면 FRED 개정 없이도 평균과
           평균을 뺀 값이 조금씩 달라지고, 출발 점이 창 밖으로 나간 전환은 'missing'이 된다(약속 문장 6 · 11).
  요약     규칙 × 방향(to_met · to_not_met) × H × s: n = 약속 뒤(before_protocol 거짓)의 'done' 전환 수. n ≥ N_MIN이면
           mean_demeaned_bp(소수 한 자리)와 up_share(change_bp > 0의 몫, 소수 둘째 자리), 아니면 둘 다 null(화면 '판단 보류 (n/10)').
  맥락     전환 날 기록의 핵심 신호 'met/total'(regime.core)과 국면 후보(regime.reference.candidate) — 없으면 null. 레짐 점검 절이
           있는데 후보가 null(완충 구간)이면 '판정불가'(UNDECIDED) — 변화 층의 국면 후보 칸도 같다(null은 그날 절이 없음).
  판       약속을 바꾸면 새 판 번호와 날짜를 붙이고 판을 바꾸지 않고는 정의를 고치지 않는다. ledger.json의 protocol.version이
           쓴 약속이고, 지난 판으로 낸 파일은 저장소 기록(git)에 남는다.
숫자 자리: 주간 점(% 값)을 적힌 그대로 십진수로 읽어 bp로 바꾸고 한 번만 반올림한다(소수 한 자리, 0.05는 0에서 먼 쪽 — Decimal
ROUND_HALF_UP). demeaned_bp는 반올림한 change_bp − 반올림한 baseline_bp라 보이는 숫자끼리 셈이 맞는다. −0.0은 0.0으로.

옮기지 않는 것: 관측값(observations)·해석 줄(reading)·이름표(scenario)·자료 상태의 날짜 — 상태·개수·날짜·국면 후보 이름표(정해 둔
네 값과 '판정불가'만)·시리즈 이름과, DGS10 · T10Y2Y · THREEFYTP10(공공 자료 · 인용 필요 자료 — 사이트에 이미 그래프로 싣는 선)의
bp 변화뿐이다. 그 세 시리즈의 FRED 권장 인용(render_public.citation — 받은 날은 charts.json의 날짜)과 '이 저장소가 계산한 값'
고지(한·영)를 ledger.json의 sources · notices에 싣는다. 규칙 제목·시리즈 이름에 꺾쇠(< >)가 있으면 key로 대신한다(화면 검사와 같다).
Baa−10년 · HY OAS · S&P · Nasdaq 숫자는 읽지도 않는다(테스트가 심어 둔 값으로 확인).
'받지 못함'은 화면(site/index.html)의 notReceived()와 같은 정의 — last가 없거나 fetched가 "missing"(not_received).
깨진 기록(읽지 못함 · JSON 아님 · schema ≠ 1 · 이름과 date가 다름 · rules가 목록이 아님)은 건너뛰고 센다(history.skipped). 이름 꼴이
YYYY-MM-DD.json이 아닌 파일은 보지 않는다. 기록이 하나도 없으면 아무것도 쓰지 않고 종료코드 0(화면은 그 상자를 그리지 않는다).
charts.json이 없거나 깨졌거나 세 선 가운데 하나라도 없으면 ledger.json은 쓰지 않고 직전 파일을 그대로 둔다(::warning:: 한 줄 —
한 시리즈만 못 받은 날에 지난 결과가 모두 '자료 없음'으로 바뀐 장부가 나가지 않게). changes.json은 날짜별 기록만 읽으므로 그대로
쓴다. 같은 입력이면 generated_at 말고 같은 출력이고,
내용이 그대로면 파일을 다시 쓰지 않는다(봇 커밋이 시각만 바뀐 파일을 싣지 않게). 쓰기는 임시 파일 → os.replace.

종료코드: 0 씀(또는 그대로 둠 · 입력 없음) / 1 쓰지 못함.
사용법: python scripts/ledger_build.py [--data data] [--out data]
"""
import os, re, sys, json, bisect, argparse, datetime
from decimal import Decimal, ROUND_HALF_UP

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import render_public as rp                             # FRED 권장 인용의 꼴 하나(citation)와 인용 필요 시리즈 목록 — 읽기만

D = datetime.date
REPO = os.path.dirname(SCRIPTS)
DEFAULT_DATA = os.path.join(REPO, "data")
SCHEMA = 1
CHANGES_FILE = "changes.json"
LEDGER_FILE = "ledger.json"

# ── 평가 약속 1판 (2026-11-18 고정 — 바꾸면 PROTOCOL_VERSION과 PROTOCOL_FIXED를 새로, README '기록 장부' 절도 같이) ──────────
PROTOCOL_VERSION = 1
PROTOCOL_FIXED = "2026-11-18"
HORIZONS = (4, 13)                                     # 주
OUTCOMES = [("dgs10", "미 10년", "DGS10"),
            ("t10y2y", "10년−2년", "T10Y2Y"),
            ("tp", "기간 프리미엄(Kim-Wright)", "THREEFYTP10")]
N_MIN = 10
TOL_DAYS = 3
START_DAYS = 7                                         # 출발 점: 전환 날 ~ 7일 뒤 안의 첫 주간 점(금요일이 휴일인 주는 목요일 점)
CHART_LINES = {"dgs10": ("yield10", "dgs10"), "t10y2y": ("term", "t10y2y"), "tp": ("term", "tp")}   # 결과 key → (overview key, 선 key)

# ── 변화 층 ────────────────────────────────────────────────────────────────────────────────────────────────────
WINDOWS = (("prev", "직전 기록", None), ("w1", "1주 전", 7), ("w4", "4주 전", 28))   # (key, 이름표, asof에서 뺀 날 — None은 바로 앞 기록)
RECENT_DAYS = 30                                       # recent: asof − 29일 ~ asof(30일)의 전환
HEADLINE_NAMED = 2                                     # 머리 둘째 줄에 이름을 적는 규칙 수

CHANGES_NOTICE = "날짜별 공개 기록(data/history)끼리 견준 것이다. 예측이 아니고 투자 판단이나 권유가 아니다."
LEDGER_NOTICE = ("규칙이 바뀐 날 뒤의 금리 변화를 정해 둔 방법(평가 약속)으로 적은 측정 기록이다. "
                 "예측이 아니고 투자 판단이나 권유가 아니다.")
COMPUTED_NOTICE = ("4주·13주 변화 · 평균을 뺀 값 · 평균(기준) · 요약은 macro-regime-check가 그래프 자료(data/charts.json)의 주간 점으로 "
                   "계산한 값이다. 연준 이사회 · 세인트루이스 연은 · FRED가 발표한 값이 아니다.")
COMPUTED_NOTICE_EN = ("The 4- and 13-week changes, demeaned values, baselines and summaries are computed by macro-regime-check "
                      "from the weekly points in data/charts.json; they are not published by the Federal Reserve Board, "
                      "the Federal Reserve Bank of St. Louis or FRED.")

STATUSES = ("met", "not_met", "unknown")
KNOWN = ("met", "not_met")
STATUS_WORD = {"met": "충족", "not_met": "미충족", "unknown": "판정 불가", None: "새 규칙"}
CANDIDATES = ("A", "A′", "B", "C")                      # regime_rules.classify_regime이 내는 네 값 — 그 밖의 글은 옮기지 않는다
UNDECIDED = "판정불가"                                  # 레짐 점검 절은 있는데 후보가 null인 날(완충 구간) — render_public의 글과 같다
TRANSITION_AUTO = 2                                     # 전환 경계 자동 트리거의 수(t2 · t4) — render_public의 '{auto}/2'
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}$")
FILE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\.json$")
KEY_RE = re.compile(r"[a-z][a-z0-9_]{0,47}$")
SERIES_RE = re.compile(r"[A-Z0-9][A-Z0-9_.]{0,39}$")
TEXT_MAX = 80
Q1, Q2 = Decimal("0.1"), Decimal("0.01")


def protocol_text():
    """화면·README에 같은 글로 싣는 평가 약속 문장(한다체). 숫자는 모두 위 상수에서."""
    h = "·".join(f"{x}주" for x in HORIZONS)
    series = " · ".join(f"{label}({sid})" for _, label, sid in OUTCOMES)
    return [
        f"평가 약속 {PROTOCOL_VERSION}판 — {PROTOCOL_FIXED}에 정했다.",
        "전환: 규칙의 상태(충족·미충족)가 그 규칙의 직전에 판정된 상태와 달라진 날짜별 기록을 전환으로 적는다. "
        "판정 불가인 날은 건너뛰어 전환을 만들지도 끊지도 않고, 처음 판정된 상태는 출발 상태이지 전환이 아니다. "
        "나중에 더한 규칙은 처음 실린 날부터 센다.",
        f"기간: 출발 점에서 {h} 뒤까지의 변화를 bp로 적는다. 끝 점은 출발 점 날짜에 7×주 수 일을 더한 날에 "
        f"가장 가까운 주간 점(±{TOL_DAYS}일 안, 같은 거리면 이른 점)이다. 그 범위 끝이 그래프의 마지막 점보다 뒤면 '기다리는 중', "
        "범위 안에 점이 없으면 '자료 없음'으로 둔다.",
        f"출발 점: 전환 날 이후(그날 포함) {START_DAYS}일 안의 첫 주간 점이다. 그날 기록은 그 앞날까지의 자료로 정해졌으므로 전환을 "
        "만든 움직임은 결과에 넣지 않는다 — 대신 전환 날부터 출발 점까지의 며칠(최대 일주일)은 결과에 들지 않는다. 그 점이 아직 "
        f"없으면 '기다리는 중', {START_DAYS}일 안에 점이 없으면 '자료 없음'이다.",
        f"시리즈: {series} — 사이트 '금리의 구조' 그래프(data/charts.json)와 같은 주간 점(주마다 마지막 관측)이다.",
        f"평균 빼기: 같은 그래프의 모든 주간 점에서 같은 규칙으로 잰 {h} 변화의 평균을 빼서 '평균을 뺀 값'으로도 적는다. 평균은 그날 "
        "그래프가 싣는 최근 기간(창)으로 갱신마다 다시 잰다 — 창이 한 주씩 옮겨 가면 FRED가 값을 고치지 않아도 평균과 평균을 뺀 값이 "
        "조금씩 달라진다.",
        f"요약: 방향(충족으로 · 미충족으로) · 기간 · 시리즈마다 약속 뒤 전환 가운데 결과가 나온 것('기다리는 중'·'자료 없음' 제외)이 "
        f"{N_MIN}개 이상일 때만 평균을 뺀 값의 평균과 오른 비율(변화가 0보다 큰 몫)을 낸다 — 그 전에는 판단 보류다.",
        f"약속 전 전환: {PROTOCOL_FIXED} 앞의 전환은 목록에 적되 요약에서 뺀다 — 약속을 정할 때 그 뒤의 금리 변화 일부가 이미 보였다.",
        "측정 기록이다(예측 아님) — 어느 규칙도 금리가 오르거나 내리는 쪽을 가리킨다고 미리 정하지 않았다.",
        "날짜별 기록(data/history)은 그날 사이트가 공개한 것(그때의 FRED 현재 개정치)이고 다시 계산하지 않는다.",
        "charts.json의 주간 점은 FRED가 값을 고치면 바뀐다 — 결과와 평균은 이 장부를 만든 날의 charts.json으로 잰다. 출발 점이 그래프 "
        "창 밖으로 나간 전환은 '자료 없음'이 되어 요약에서 빠진다.",
        "약속을 바꾸면 새 판 번호와 날짜를 붙이고, 판을 바꾸지 않고는 정의를 고치지 않는다 — 지난 판으로 낸 파일은 저장소 기록(git)에 "
        "남는다. 이 파일의 판 번호가 쓴 약속이다.",
    ]


# ── 읽기 ─────────────────────────────────────────────────────────────────────────────────────────────────────
def _date(s):
    if isinstance(s, str) and DATE_RE.match(s):
        try:
            return D.fromisoformat(s)
        except ValueError:
            return None
    return None


def _int(v, lo=0, hi=10 ** 6):
    return v if isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi else None


def _text(v):
    """화면에 옮기는 짧은 이름(규칙 제목·시리즈 이름) — 한 줄 · TEXT_MAX자 안 · 제어 문자와 꺾쇠(< >) 없음. 꺾쇠는 화면(site/ledger.js의
    PLAIN)이 받지 않으므로 여기서도 받지 않아 key로 대신한다 — 화면이 그 규칙을 통째로 빼지 않게."""
    if isinstance(v, str) and 0 < len(v) <= TEXT_MAX and v.strip() == v \
            and not any(ord(c) < 32 or ord(c) == 127 or c in "<>" for c in v):
        return v
    return None


def not_received(h):
    """site/index.html의 notReceived(h)와 같은 정의 — `!h.last || h.fetched === "missing"`."""
    return not h.get("last") or h.get("fetched") == "missing"


def _ratio(x):
    """{total, met} → 'met/total' (0 ≤ met ≤ total), 꼴이 다르면 None."""
    if not isinstance(x, dict):
        return None
    t, m = _int(x.get("total")), _int(x.get("met"))
    return f"{m}/{t}" if t is not None and m is not None and m <= t else None


def _regime(r):
    if not isinstance(r, dict):
        return None
    ref = r.get("reference") if isinstance(r.get("reference"), dict) else {}
    tr = ref.get("transition") if isinstance(ref.get("transition"), dict) else {}
    cand = ref.get("candidate")
    cand = cand if cand in CANDIDATES else UNDECIDED if "candidate" in ref and cand is None else None
    return {"core": _ratio(r.get("core")), "neutral": _ratio(r.get("neutral")),
            "candidate": cand, "transition": _int(tr.get("auto_on"), 0, TRANSITION_AUTO)}


def _snapshot(raw, date):
    """기록 한 장 → 쓰는 칸만. 꼴이 다르면 None(건너뜀). 규칙 항목은 key가 맞는 것만(같은 key는 처음 것), 모르는 상태는
    'unknown'으로 — 판정을 지어내지 않는다."""
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA or raw.get("date") != date.isoformat():
        return None
    if not isinstance(raw.get("rules"), list):
        return None
    rules, seen = [], set()
    for r in raw["rules"]:
        if not isinstance(r, dict) or not isinstance(r.get("key"), str) or not KEY_RE.match(r["key"]) or r["key"] in seen:
            continue
        seen.add(r["key"])
        st = r.get("status")
        rules.append({"key": r["key"], "title": _text(r.get("title")) or r["key"],
                      "status": st if st in STATUSES else "unknown"})
    health, hseen = [], set()
    for h in raw.get("data_health") if isinstance(raw.get("data_health"), list) else []:
        if not isinstance(h, dict) or not isinstance(h.get("series"), str) or not SERIES_RE.match(h["series"]) \
                or h["series"] in hseen:
            continue
        hseen.add(h["series"])
        health.append({"series": h["series"], "label": _text(h.get("label")) or h["series"],
                       "received": not not_received(h), "stale": h.get("stale") is True})
    return {"date": date, "rules": rules, "regime": _regime(raw.get("regime")), "health": health}


def load_history(hist_dir):
    """→ (기록 목록(날짜 순), 건너뛴 수). 이름 꼴이 YYYY-MM-DD.json인 파일만 본다."""
    try:
        names = sorted(os.listdir(hist_dir))
    except OSError:
        return [], 0
    snaps, skipped = [], 0
    for name in names:
        m = FILE_RE.match(name)
        if not m:
            continue
        date = _date(m.group(1))
        snap = None
        if date is not None:
            try:
                with open(os.path.join(hist_dir, name), encoding="utf-8") as f:
                    snap = _snapshot(json.load(f), date)
            except (OSError, ValueError, RecursionError):
                snap = None
        if snap is None:
            skipped += 1
        else:
            snaps.append(snap)
    snaps.sort(key=lambda s: s["date"])
    return snaps, skipped


def _dec(v):
    """유한한 숫자 → 적힌 그대로의 십진수(0.909 → Decimal('0.909')), 아니면 None."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    if isinstance(v, float) and (v != v or v in (float("inf"), float("-inf"))):
        return None
    return Decimal(repr(v))


def load_charts(path):
    """charts.json → (날짜 문자열|None, {결과 key: [(날짜, Decimal)] 날짜 순}). 없거나 깨졌으면 (None, {})."""
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError, RecursionError):
        return None, {}
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA or not isinstance(raw.get("overview"), list):
        return None, {}
    date = raw.get("date") if _date(raw.get("date")) else None
    lines = {}
    for key, _, sid in OUTCOMES:
        chart_key, line_key = CHART_LINES[key]
        for ch in raw["overview"]:
            if not isinstance(ch, dict) or ch.get("key") != chart_key or not isinstance(ch.get("lines"), list):
                continue
            for ln in ch["lines"]:
                if isinstance(ln, dict) and ln.get("key") == line_key and isinstance(ln.get("series"), list) \
                        and sid in ln["series"] and isinstance(ln.get("points"), list):
                    pts = {}
                    for p in ln["points"]:
                        if isinstance(p, list) and len(p) == 2:
                            d, v = _date(p[0]), _dec(p[1])
                            if d is not None and v is not None:
                                pts[d] = v
                    if pts and key not in lines:
                        lines[key] = sorted(pts.items())
    return date, lines


# ── 셈 ─────────────────────────────────────────────────────────────────────────────────────────────────────
def _q(x, step=Q1):
    """Decimal → 소수 step 자리 float(0.05는 0에서 먼 쪽, −0.0은 0.0)."""
    v = float(x.quantize(step, rounding=ROUND_HALF_UP))
    return 0.0 if v == 0 else v


def match(dates, target):
    """dates(날짜 순)에서 target에 가장 가까운 점의 자리(±TOL_DAYS 안, 같은 거리면 이른 점), 없으면 None."""
    tol = datetime.timedelta(days=TOL_DAYS)
    lo, hi = bisect.bisect_left(dates, target - tol), bisect.bisect_right(dates, target + tol)
    best = None
    for k in range(lo, hi):
        gap = abs((dates[k] - target).days)
        if best is None or gap < best[1]:
            best = (k, gap)
    return None if best is None else best[0]


def _pending(dates, target):
    return target + datetime.timedelta(days=TOL_DAYS) > dates[-1]


def baseline(points, h):
    """선 하나의 H주 평균 변화 → (bp Decimal, 쌍 수, 첫 출발, 마지막 끝) 또는 None."""
    if not points:
        return None
    dates = [d for d, _ in points]
    total, n, first, last = Decimal(0), 0, None, None
    for d, v in points:
        target = d + datetime.timedelta(days=7 * h)
        if _pending(dates, target):
            break                                       # 날짜 순이라 뒤의 점도 모두 기다리는 중
        j = match(dates, target)
        if j is None:
            continue
        total += (points[j][1] - v) * 100
        n += 1
        first = first or d
        last = dates[j]
    return None if n == 0 else (total / n, n, first, last)


def outcome(points, day, h, base_bp):
    """전환 날 day의 H주 결과 하나. base_bp는 반올림한 평균(float) 또는 None."""
    empty = {"state": "missing", "start": None, "end": None, "change_bp": None, "demeaned_bp": None}
    if not points:
        return empty
    dates = [d for d, _ in points]
    i = bisect.bisect_left(dates, day)
    if i == len(dates):
        return {**empty, "state": "pending"}            # 전환 날 이후의 점이 아직 없다 — 출발 점이 정해지기 전
    start, sv = points[i]
    if (start - day).days > START_DAYS:
        return empty
    target = start + datetime.timedelta(days=7 * h)
    if _pending(dates, target):
        return {**empty, "state": "pending", "start": start.isoformat()}
    j = match(dates, target)
    if j is None:
        return {**empty, "start": start.isoformat()}
    change = _q((points[j][1] - sv) * 100)
    demeaned = None if base_bp is None else _q(Decimal(repr(change)) - Decimal(repr(base_bp)))
    return {"state": "done", "start": start.isoformat(), "end": dates[j].isoformat(),
            "change_bp": change, "demeaned_bp": demeaned}


def track(snaps):
    """규칙마다 (기록 순서대로) 첫 날 · 마지막 날 · 상태 열 · 제목(그 규칙이 있는 가장 최근 기록의 것)."""
    tracks = {}
    for s in snaps:
        for r in s["rules"]:
            t = tracks.setdefault(r["key"], {"key": r["key"], "first": s["date"], "statuses": []})
            t["statuses"].append((s["date"], r["status"]))
            t["last"], t["title"] = s["date"], r["title"]
    return tracks


def flips(statuses):
    """상태 열 → (출발 상태, 지금 이어지는 상태가 시작된 날, 판정 불가 날 수, [(날, 앞, 뒤)]) — 평가 약속의 '전환'."""
    known = start = since = None
    unknown, out = 0, []
    for d, st in statuses:
        if st not in KNOWN:
            unknown += 1
            continue
        if known is None:
            start, since = st, d
        elif st != known:
            out.append((d, known, st))
            since = d
        known = st
    return start, since, unknown, out


def summarize(events):
    """방향 × H × s의 요약 — 약속 뒤 'done'만, n ≥ N_MIN일 때만 평균(평균을 뺀 값)과 오른 몫."""
    out = {}
    for name, to in (("to_met", "met"), ("to_not_met", "not_met")):
        out[name] = {}
        for h in HORIZONS:
            row = {}
            for key, _, _ in OUTCOMES:
                done = [e["outcomes"][str(h)][key] for e in events if e["to"] == to and not e["before_protocol"]
                        and e["outcomes"][str(h)][key]["state"] == "done"]
                n, mean, up = len(done), None, None
                if n >= N_MIN:
                    dm = [Decimal(repr(o["demeaned_bp"])) for o in done if o["demeaned_bp"] is not None]
                    mean = _q(sum(dm) / n) if len(dm) == n else None
                    up = _q(Decimal(sum(1 for o in done if o["change_bp"] > 0)) / n, Q2)
                row[key] = {"n": n, "mean_demeaned_bp": mean, "up_share": up}
            out[name][str(h)] = row
    return out


def rule_order(snaps, tracks):
    """가장 최근 기록의 규칙 차례, 그 뒤에 지금은 없는 규칙(처음 나온 차례)."""
    latest = [r["key"] for r in snaps[-1]["rules"]]
    return latest + [k for k in tracks if k not in latest]


def sources(charts_date):
    """세 시리즈의 출처 — FRED 권장 인용(받은 날 = charts.json의 날짜, 없으면 null)과 인용 필요 여부(render_public과 같은 목록)."""
    return [{"series": sid, "url": rp.FRED_URL.format(sid),
             "citation": rp.citation(sid, charts_date) if charts_date else None,
             "citation_required": sid in rp.CITATION_REQUIRED} for _, _, sid in OUTCOMES]


def chart_gaps(charts_date, lines):
    """ledger.json을 쓰지 못하는 까닭 — charts.json이 없거나 날짜가 없음, 또는 세 선 가운데 빠진 것. 없으면 []."""
    return ([] if charts_date else ["charts.json"]) + [k for k, _, _ in OUTCOMES if not lines.get(k)]


def build_ledger(snaps, skipped, charts_date, lines, now):
    by_date = {s["date"]: s for s in snaps}
    tracks = track(snaps)
    bases, base_detail, base_bp = {}, {}, {}
    for h in HORIZONS:
        bases[str(h)], base_detail[str(h)] = {}, {}
        for key, _, _ in OUTCOMES:
            b = baseline(lines.get(key), h)
            base_bp[(h, key)] = None if b is None else _q(b[0])
            bases[str(h)][key] = base_bp[(h, key)]
            base_detail[str(h)][key] = None if b is None else {"n": b[1], "from": b[2].isoformat(), "to": b[3].isoformat()}
    all_dates = [d for pts in lines.values() for d, _ in pts]
    rules = []
    for k in rule_order(snaps, tracks):
        t = tracks[k]
        start, since, unknown, fl = flips(t["statuses"])
        events = []
        for d, a, b in fl:
            reg = by_date[d]["regime"] or {}
            events.append({"date": d.isoformat(), "from": a, "to": b, "before_protocol": d.isoformat() < PROTOCOL_FIXED,
                           "core": reg.get("core"), "candidate": reg.get("candidate"),
                           "outcomes": {str(h): {key: outcome(lines.get(key), d, h, base_bp[(h, key)])
                                                 for key, _, _ in OUTCOMES} for h in HORIZONS}})
        rules.append({"key": k, "title": t["title"], "first": t["first"].isoformat(), "last": t["last"].isoformat(),
                      "start": start, "now": t["statuses"][-1][1], "since": since and since.isoformat(),
                      "unknown_days": unknown, "events": events, "summary": summarize(events)})
    return {"schema": SCHEMA, "generated_at": now, "notice": LEDGER_NOTICE,
            "protocol": {"version": PROTOCOL_VERSION, "fixed": PROTOCOL_FIXED, "horizons_weeks": list(HORIZONS),
                         "outcomes": [{"key": k, "label": lb, "series": sid} for k, lb, sid in OUTCOMES],
                         "n_min": N_MIN, "tolerance_days": TOL_DAYS, "start_days": START_DAYS, "text": protocol_text()},
            "history": {"from": snaps[0]["date"].isoformat(), "to": snaps[-1]["date"].isoformat(),
                        "snapshots": len(snaps), "skipped": skipped},
            "charts": {"date": charts_date,
                       "window": {"from": min(all_dates).isoformat() if all_dates else None,
                                  "to": max(all_dates).isoformat() if all_dates else None},
                       "last": {key: lines[key][-1][0].isoformat() if lines.get(key) else None for key, _, _ in OUTCOMES},
                       "baseline": bases, "baseline_detail": base_detail},
            "sources": sources(charts_date), "notices": [COMPUTED_NOTICE, COMPUTED_NOTICE_EN],
            "rules": rules}


# ── 변화 층 ──────────────────────────────────────────────────────────────────────────────────────────────────
def _met(s):
    return sum(1 for r in s["rules"] if r["status"] == "met"), len(s["rules"])


def _reg(s, field):
    return (s["regime"] or {}).get(field) if s else None


def pick_window(snaps, days):
    """비교할 기록 — days가 None이면 바로 앞 기록, 아니면 asof − days 이하의 가장 최근 기록. 없으면 None."""
    if days is None:
        return snaps[-2] if len(snaps) >= 2 else None
    cut = snaps[-1]["date"] - datetime.timedelta(days=days)
    old = [s for s in snaps[:-1] if s["date"] <= cut]
    return old[-1] if old else None


def window(key, label, base, cur, titles):
    then = {r["key"]: r["status"] for r in base["rules"]} if base else {}
    rules = [] if base is None else [
        {"key": r["key"], "title": titles[r["key"]], "from": then.get(r["key"]), "to": r["status"]}
        for r in cur["rules"] if then.get(r["key"]) != r["status"]]
    m1, t1 = _met(cur)
    m0, t0 = _met(base) if base else (None, None)
    health = {"lost": [], "recovered": [], "stale": [], "fresh": []}
    if base:
        old = {h["series"]: h for h in base["health"]}
        for h in cur["health"]:
            o = old.get(h["series"])
            if o is None:
                continue
            item = {"series": h["series"], "label": h["label"]}
            if o["received"] and not h["received"]:
                health["lost"].append(item)
            elif h["received"] and not o["received"]:
                health["recovered"].append(item)
            if h["stale"] and not o["stale"]:
                health["stale"].append(item)
            elif o["stale"] and not h["stale"]:
                health["fresh"].append(item)
    pair = lambda f: {"from": _reg(base, f), "to": _reg(cur, f)}
    return {"key": key, "label": label, "from": base["date"].isoformat() if base else None, "rules": rules,
            "met": {"from": m0, "to": m1, "total_from": t0, "total_to": t1},
            "core": pair("core"), "neutral": pair("neutral"), "candidate": pair("candidate"),
            "transition": pair("transition"), "health": health}


def _cand_word(s):
    if s is None or s["regime"] is None:
        return "—"
    return s["regime"]["candidate"] or UNDECIDED


def _real_cand(s):
    """정해 둔 네 값의 국면 후보가 있는가(판정불가 · 기록 없음은 아님) — 머리 셋째 줄을 낼지."""
    return _reg(s, "candidate") in CANDIDATES


def headline(cur, w1, w1_rules, week_flips=None):
    """머리 세 줄(결정적인 평서문, 판정 낱말 없음). week_flips는 (1주 전 기록 날, asof]의 전환 수 — 두 끝의 상태만 견주면
    오갔다 돌아온 전환이 보이지 않으므로, 끝끼리 바뀐 규칙(판정된 상태끼리)보다 많으면 둘째 줄에 ' · 그 사이 전환 n번'을 붙인다."""
    out = []
    if cur["regime"] and cur["regime"]["core"] and (w1 is None or (w1["regime"] and w1["regime"]["core"])):
        out.append(f"핵심 신호 {cur['regime']['core']}" + (f" · 1주 전 {w1['regime']['core']}" if w1 else ""))
    else:
        m1, t1 = _met(cur)
        line = f"충족 규칙 {m1}/{t1}"
        if w1:
            m0, t0 = _met(w1)
            line += f" · 1주 전 {m0}/{t0}"
        out.append(line)
    if w1 is not None:
        if not w1_rules:
            out.append("1주 사이 바뀐 규칙 없음")
        else:
            named = " · ".join(f"{r['title']}({STATUS_WORD[r['from']]}→{STATUS_WORD[r['to']]})"
                               for r in w1_rules[:HEADLINE_NAMED])
            rest = len(w1_rules) - HEADLINE_NAMED
            out.append(f"1주 사이 바뀐 규칙 {len(w1_rules)}개: {named}" + (f" 외 {rest}개" if rest > 0 else ""))
        shown = sum(1 for r in w1_rules if r["from"] in KNOWN and r["to"] in KNOWN)
        if week_flips is not None and week_flips > shown:
            out[-1] += f" · 그 사이 전환 {week_flips}번"
    parts = []
    if _real_cand(cur) or _real_cand(w1):
        parts.append(f"국면 후보 {_cand_word(cur)}" + (f" · 1주 전 {_cand_word(w1)}" if w1 else ""))
    missing = sum(1 for h in cur["health"] if not h["received"])
    if missing:
        parts.append(f"받지 못한 시리즈 {missing}개")
    if parts:
        out.append(" · ".join(parts))
    return out


def build_changes(snaps, now):
    cur = snaps[-1]
    tracks = track(snaps)
    titles = {k: t["title"] for k, t in tracks.items()}
    wins = {key: window(key, label, pick_window(snaps, days), cur, titles) for key, label, days in WINDOWS}
    w1 = pick_window(snaps, 7)
    order = {k: i for i, k in enumerate(rule_order(snaps, tracks))}
    recent_from = cur["date"] - datetime.timedelta(days=RECENT_DAYS - 1)
    recent = []
    for k, t in tracks.items():
        for d, a, b in flips(t["statuses"])[3]:
            if recent_from <= d <= cur["date"]:
                recent.append({"date": d.isoformat(), "key": k, "title": t["title"], "from": a, "to": b})
    recent.sort(key=lambda e: (-D.fromisoformat(e["date"]).toordinal(), order[e["key"]]))
    week_flips = None if w1 is None else sum(1 for t in tracks.values() for d, _, _ in flips(t["statuses"])[3]
                                             if w1["date"] < d <= cur["date"])
    return {"schema": SCHEMA, "generated_at": now, "notice": CHANGES_NOTICE, "asof": cur["date"].isoformat(),
            "headline": headline(cur, w1, wins["w1"]["rules"], week_flips),
            "windows": [wins[key] for key, _, _ in WINDOWS],
            "recent_from": recent_from.isoformat(), "recent": recent}


# ── 쓰기 ─────────────────────────────────────────────────────────────────────────────────────────────────────
def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def _same(path, obj):
    """이미 있는 파일이 generated_at 말고 같은 내용인가."""
    try:
        with open(path, encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError, RecursionError):
        return False
    if not isinstance(old, dict):
        return False
    strip = lambda o: {k: v for k, v in o.items() if k != "generated_at"}
    return strip(old) == strip(json.loads(dumps(obj)))


def write(out, name, obj):
    """임시 파일 → os.replace. 내용이 그대로면 쓰지 않는다. 썼으면 True."""
    path = os.path.join(out, name)
    if _same(path, obj):
        return False
    text = dumps(obj)
    os.makedirs(out, exist_ok=True)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return True


def _build(data_dir, now=None):
    """→ (changes, ledger, 그래프 자료의 빈 곳) 또는 기록이 없으면 None."""
    now = now or datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    snaps, skipped = load_history(os.path.join(data_dir, "history"))
    if not snaps:
        return None
    charts_date, lines = load_charts(os.path.join(data_dir, "charts.json"))
    return (build_changes(snaps, now), build_ledger(snaps, skipped, charts_date, lines, now),
            chart_gaps(charts_date, lines))


def build(data_dir, now=None):
    """→ (changes, ledger) 또는 기록이 없으면 None. now는 generated_at 글(기본: 지금 UTC). 그래프 자료가 모자라도 ledger를
    셈해 돌려준다(결과는 'missing') — 쓰지 않는 것은 main이 정한다."""
    res = _build(data_dir, now)
    return None if res is None else res[:2]


def main(argv=None, now=None):
    ap = argparse.ArgumentParser(description="날짜별 공개 기록 + 그래프 자료 → 변화 층(changes.json) · 규칙 장부(ledger.json)")
    ap.add_argument("--data", default=DEFAULT_DATA, help="읽을 사이트 데이터 폴더 — history/와 charts.json (기본: 저장소의 data/)")
    ap.add_argument("--out", default=None, help="쓸 폴더 (기본: --data와 같은 폴더)")
    a = ap.parse_args(argv)
    data = os.path.abspath(a.data)
    out = os.path.abspath(a.out) if a.out else data
    res = _build(data, now)
    if res is None:
        print("[ledger_build] 날짜별 기록(history/)이 없다 — 아무것도 쓰지 않음")
        return 0
    changes, ledger, gaps = res
    todo = [(CHANGES_FILE, changes)] + ([] if gaps else [(LEDGER_FILE, ledger)])
    if gaps:
        print(f"::warning::[ledger_build] 그래프 자료가 모자란다({', '.join(gaps)}) — ledger.json은 쓰지 않고 직전 파일을 그대로 둠",
              flush=True)
    try:
        wrote = [name for name, obj in todo if write(out, name, obj)]
    except (OSError, ValueError) as e:
        print(f"[ledger_build] 쓰지 못함: {type(e).__name__}", file=sys.stderr)
        return 1
    hist = ledger["history"]
    n_ev = sum(len(r["events"]) for r in ledger["rules"])
    n_after = sum(1 for r in ledger["rules"] for e in r["events"] if not e["before_protocol"])
    print(f"[ledger_build] {changes['asof']} 기준 — 기록 {hist['snapshots']}개(건너뜀 {hist['skipped']}) · "
          f"전환 {n_ev}개(약속 뒤 {n_after}) · 그래프 {ledger['charts']['date'] or '없음'}"
          + (" — 장부는 그대로 둠" if gaps else "") + " · "
          + (("씀: " + ", ".join(wrote)) if wrote else "내용 그대로 — 다시 쓰지 않음"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
