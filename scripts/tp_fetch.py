#!/usr/bin/env python3
"""참고 자료 — 기간 프리미엄 모형 대조 (2026-10-30 추가, 사용자 결정: 비공개 줄 공개).

운영자의 비공개 점검에 있던 기간 프리미엄 두 줄을 공개한 것이다 — 결론 알림의 주간 기간 프리미엄 근거 줄(비공개 원본
tp_auto.compute)과 월간 점검의 [TP 모형 대조] 블록(비공개 원본 tp_compare.models_block·render_block). 같은 산식을 여기서
따로 쓴다(코드는 가져오지 않는다 — 산식·문턱을 고치면 양쪽을 같이). 규칙 판정·공개본·그래프 스크립트는 이 파일(<out>/tp.json)을
읽지 않고, 점수는 이 사이트의 규칙 수에 들지 않는다. 칸(ITEMS — 화면 차례):
  weekly  Kim-Wright 10년 기간 프리미엄(FRED THREEFYTP10)의 4주 변화(마지막 관측 − 28일 전 이하 마지막 관측, bp) ÷ σ(2023년
          이후 ISO 주의 마지막 관측으로 낸 4주 변화의 표준편차, 20개 이상) = z와, 운영자 주간 평가 규칙의 점수
          −부호(z) × min(2, ⌊|z|⌋)(+는 금리 하락 쪽). 마지막 관측이 오늘보다 14일 넘게 이르면 점수를 매기지 않는다(숫자만).
          설명 줄: 같은 4주의 Kim-Wright 적합 10년(THREEFY10 — 관측일이 정확히 같을 때만) 변화, 그중 기간 프리미엄 몫(10년
          변화가 10bp 이상일 때만), 평소 몫(σ와 같은 주간 표본의 회귀 기울기, 20쌍 이상). ACM 참고: ACM 마지막 두 관측의 변화와
          같은 기간 Kim-Wright 변화(그날 이하 마지막 관측), 같은 기간 월간 변화 12쌍 이상이고 그 마지막 쌍이 ACM 마지막 달일
          때만 각자 σ로 나눈 z의 해석 갈림(마지막 달에 Kim-Wright 짝이 없으면 앞 달의 z를 싣지 않는다)
  models  ACM과 Kim-Wright 월간 대조 — ACM 월말(달마다 마지막 행)에서 다음 월말까지와 같은 기간의 Kim-Wright 변화(각 월말에서
          7일 안의 그날 이하 마지막 관측), 2023년 이후 달. 각자 σ로 나눈 z와 경우(공통 TP↑ · 공통 TP↓ · ACM만 · KW만 · 반대 ·
          둘 다 약함, |z| ≥ 1을 유의로), 해석 갈림(한쪽만 유의 또는 반대이고 z 차이 ≥ 0.7), 같은 달 10년(ACM 파일의 GSW 무이표
          — 그 열이 없는 달은 비운다. 비공개 원본 월간 점검도 적합 10년으로 대신하지 않는다) 변화 중 기간 프리미엄 몫(10bp
          이상이고 0~200%일 때만)과 평소 몫(표본 회귀 기울기), 최근 3달, 최근 12개월 상관(0.6 미만이면 '신뢰 낮음')·같은 방향 비율
숫자 자리: 비공개 원본과 같은 자리로 싣고 문구는 그 값에서 한 번만 반올림한다 — 주간 칸은 tp_auto.compute 그대로(bp 1자리,
몫 3자리, z 6자리 — 표시 때 0 쪽으로 자른다, ACM·KW 월간 z 3자리), 월간 칸은 tp_compare.models_block이 반올림하지 않은 값으로
그리므로 원값(-0.0만 0.0으로). 그래서 같은 원자료면 카드의 숫자가 비공개 줄의 숫자와 같다(4자리로 저장한 뒤 다시 반올림하면
-8.14999가 -8.2로 보이는 식으로 어긋났다).
비공개 원본에서 옮기지 않은 것: 사람 메모의 ACM 수치가 우선하는 채점, 메모용 ACM 월간 σ, 공급 일정 조정(±0.5), 시트의
기간 프리미엄 돌파 표시(−2 고정) — 모두 운영자가 손으로 넣는 것이다. ACM 판 보관도 하지 않는다. 오늘은 실행 시각(UTC)의 날짜다.

자료 이용 조건: THREEFYTP10·THREEFY10은 연준 이사회 자료(FRED, 'Public Domain: Citation Requested' — FRED 권장 인용을 싣는다).
ACM은 뉴욕 연은 웹 사이트의 acmPlot_data.csv(이 환경에서는 접속하지 못해 실제 응답을 보지 못했다 — 머리말 열 이름 TERMYld·
ACMFITYld·GSWYld와 '31-Aug-2026' 꼴 날짜는 비공개 원본의 해석기 그대로). 뉴욕 연은 이용약관의 기본 출처 형식·관계없음 고지와
계산값 표시(render_public — 수급 참고의 딜러 쪽과 같은 원칙), ACM 논문 인용을 함께 싣는다. 재배포가 제한된 시리즈는 쓰지 않는다.

실패·이어 싣기·문구 원칙은 oil_fetch와 같다: 칸마다 따로(칸에 꼭 필요한 자료 가운데 하나라도 이번에 받지 못하면 — 온라인에서
캐시로 대신한 것도 — 직전 숫자를 '받지 못함'과 그날부터라는 날짜와 함께, 직전 값이 없으면 사유만), 받은 자료가 직전보다 이르면
받지 않는다, 문구는 이 파일에 정해 둔 것뿐(받은 글은 숫자·날짜로만 읽고 공개 파일에 옮기지 않는다 — Actions 로그에는 예외 이름도
싣지 않는다), 같은 내용이면 다시 쓰지 않는다, 수신 전체 BUDGET초(응답을 읽는 동안에도 본다). ACM 주소가 다른 곳으로 넘겨지면
(리디렉션) 받지 않는다. 적합 10년은 SERIES 끝이라 수신 시간이 모자라면 그쪽부터 빠진다(설명 줄만 빈다).

종료코드: 0 한 칸이라도 이번에 받음 / 1 하나도 못 받음(또는 파일을 쓰지 못함). 워크플로 단계는 continue-on-error, 알림 없음.

사용법: python scripts/tp_fetch.py [--out data] [--work .work] [--offline]
"""
import os, sys, json, math, time, argparse, datetime, statistics, urllib.request, urllib.parse

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import fred_fetch as ff
import render_public as rp
import ai_invest_fetch as ai                  # FRED 수신(load_series)·쓰기·꼴 검사·문구 숫자를 그대로 쓴다

D = datetime.date
SCHEMA = 1
REPO = os.path.dirname(SCRIPTS)
DEFAULT_OUT = os.path.join(REPO, "data")
DEFAULT_WORK = os.path.join(REPO, ".work")
FILE = "tp.json"
CACHE = "tp"                                  # <work>/tp/<ID>.csv · acmPlot_data.csv

BUDGET = 45                                   # 수신 전체(초, 요청 3회) — 워크플로 단계 제한(2분) 안에서 끝나게
MAX_BYTES = 5_000_000                         # ACM 응답 하나의 상한
# 저장 자리 — 비공개 원본(tp_auto.compute)과 같게(위 머리말 '숫자 자리'). 월간 칸은 원값(_raw)
BP_ND = 1                                     # 4주 변화·σ·10년 변화·ACM/KW 월간 변화(bp)
SHARE_ND = 3                                  # 10년 중 기간 프리미엄 몫·평소 몫(비율)
Z_ND = 6                                      # 주간 z — 표시에서 0 쪽으로 자르므로 더 길게 둔다
MZ_ND = 3                                     # 주간 칸의 ACM·KW 월간 z

KW_ID, FY_ID, ACM = "THREEFYTP10", "THREEFY10", "ACM"
ACM_HOST = "www.newyorkfed.org"
ACM_URL = f"https://{ACM_HOST}/medialibrary/media/research/data_indicators/acmPlot_data.csv"
ACM_PAGE = f"https://{ACM_HOST}/research/data_indicators/term-premia-tabs"
ACM_CACHE = "acmPlot_data.csv"
ACM_COLS = {"tp": "TERMYld", "fit": "ACMFITYld", "gsw": "GSWYld"}
MONTHS = {m: i for i, m in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
                                      "Dec"), 1)}

# 운영자 규칙(비공개 원본 tp_auto·tp_compare와 같은 값 — 고치면 양쪽을 같이)
CHANGE_DAYS = 28                              # 4주 변화
SIGMA_SINCE = D(2023, 1, 1)                   # σ·월간 대조 표본 시작
MIN_SIGMA_OBS = 20                            # σ에 쓸 4주 변화가 이보다 적으면 계산하지 않는다
MAX_AGE_DAYS = 14                             # Kim-Wright 마지막 관측이 이보다 오래되면 점수를 매기지 않는다
MIN_SHARE_BP = 10                             # 10년 변화가 이보다 작으면 기간 프리미엄 몫(%)을 내지 않는다
SPLIT_Z = 1.0                                 # 모형 대조: |z| ≥ 1이면 그 모형이 '유의'
SPLIT_GAP = 0.7                               # 모형 대조: 두 z 차이가 이 이상이어야 '해석 갈림'
MONTH_GAP_DAYS = 7                            # 월말과 그 이하 마지막 Kim-Wright 관측이 이보다 멀면 그 달은 견주지 않는다
MIN_PAIRS = 12                                # 주간 칸의 ACM z: 같은 기간 월간 변화가 이보다 적으면 견주지 않는다
MIN_MONTHS = 3                                # 월간 칸: 견줄 달이 이보다 적으면 계산하지 않는다
RECENT = 3
WINDOW = 12                                   # 일치도 창(개월)
LOW_TRUST_CORR = 0.6                          # 최근 12개월 상관이 이보다 낮으면 '신뢰 낮음'
CASES = ("공통 TP↑", "공통 TP↓", "ACM만", "KW만", "반대", "둘 다 약함")
SPLIT_CASES = ("ACM만", "KW만", "반대")
YIELD_SRC = ("GSW",)                          # 월간 칸의 10년은 ACM 파일의 GSW만(비공개 원본과 같게 — 적합 10년으로 대신하지 않는다)

_BOARD = "Board of Governors of the Federal Reserve System (US)"
# FRED 권장 인용의 출처·제목 — THREEFY10 제목은 이 환경에서 FRED 시리즈 쪽과 대조하지 못했다(첫 실행 뒤 대조)
SOURCES = {KW_ID: (_BOARD, "Term Premium on a 10 Year Zero Coupon Bond"),
           FY_ID: (_BOARD, "Fitted Yield on a 10 Year Zero Coupon Bond"),
           ACM: ("Federal Reserve Bank of New York", "Treasury Term Premia (Adrian, Crump, and Moench), 10-year term premium")}
LICENCE = {KW_ID: "public-domain", FY_ID: "public-domain", ACM: "nyfed-terms"}
SERIES = [KW_ID, ACM, FY_ID]                  # 적합 10년은 끝 — 설명 줄에만 쓴다

NOTICE = ("이 사이트의 규칙 점검에 쓰지 않는 참고 자료다. 운영자의 비공개 점검에 있던 기간 프리미엄 줄을 공개한 것이고, "
          "금리를 예측하지 않는다.")
COMPUTED_NOTICE = "변화·σ·z·점수·몫·상관은 macro-regime-check가 원자료로 계산한 값이다."
KW_NOTICE = ("Kim-Wright 기간 프리미엄·적합 10년은 연준 이사회 추정치(Kim, D. H. and J. H. Wright (2005), Finance and Economics "
             "Discussion Series 2005-33)를 FRED에서 받아 FRED 권장 인용과 함께 싣는다.")
ACM_DERIVED = ("ACM 변화·z·몫·상관은 macro-regime-check가 뉴욕 연은 ACM 기간 프리미엄 자료(acmPlot_data.csv)로 계산한 값이다. "
               "뉴욕 연은이 발표한 값이 아니다.")
ACM_DERIVED_EN = ("Changes, z-scores, shares and correlations are computed by macro-regime-check from the New York Fed "
                  "ACM term premium data (acmPlot_data.csv); they are not published by the New York Fed.")
ACM_PAPER = ("ACM: Adrian, T., R. K. Crump, and E. Moench (2013), \"Pricing the Term Structure with Linear Regressions,\" "
             "Journal of Financial Economics 110(1): 110-138.")
REASONS = {
    "fetch": "수신 실패",
    "cache": "수신 실패 · 묵은 캐시는 싣지 않음",
    "format": "계산할 자료가 모자람",
    "older": "받은 자료가 직전 자료보다 오래됨",
}


class ItemError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


_r = ai._r
_iso = ai._iso


def _raw(v):
    """월간 칸 — 반올림하지 않은 값(비공개 원본 models_block이 그리는 값). -0.0만 0.0으로."""
    return None if v is None else v + 0.0


# ---------- ACM 자료 ----------

def parse_acm(text):
    """acmPlot_data.csv → [{date, tp, fit, gsw}] 날짜순(%). 열은 머리말 이름으로 찾고, 없는 열은 None. TP 열 이름이 없으면
    둘째 열을 TP로 본다. 못 읽는 줄은 건너뛴다(비공개 원본 tp_compare.parse_acm_full 그대로). 숫자는 유한한 것만."""
    lines = text.splitlines()
    if not lines:
        return []
    head = [h.strip() for h in lines[0].split(",")]
    idx = {k: (head.index(v) if v in head else None) for k, v in ACM_COLS.items()}
    if idx["tp"] is None:
        idx["tp"] = 1
    rows = {}
    for line in lines[1:]:
        parts = [p.strip() for p in line.split(",")]
        try:
            day, mon, year = parts[0].split("-")
            d = D(int(year), MONTHS[mon], int(day))
            tp = float(parts[idx["tp"]])
            if not math.isfinite(tp):
                continue
            row = {"date": d, "tp": tp}
        except (ValueError, KeyError, IndexError):
            continue
        for k in ("fit", "gsw"):
            try:
                v = float(parts[idx[k]]) if idx[k] is not None else None
                row[k] = v if v is not None and math.isfinite(v) else None
            except (ValueError, IndexError):
                row[k] = None
        rows[d] = row                          # 같은 날이 두 번이면 뒤의 것
    return [rows[d] for d in sorted(rows)]


def month_ends(rows):
    """달마다 마지막 행만 — ACM 파일이 월말값이든 일별이든 같은 월간 표본이 되게."""
    out = {}
    for r in rows:
        out[(r["date"].year, r["date"].month)] = r
    return [out[k] for k in sorted(out)]


# ---------- 산술 (비공개 원본 tp_auto·tp_compare·sheet_v2.tp_score 그대로) ----------

def tp_score(z):
    """운영자 주간 평가 규칙(8-4): −부호(z) × min(2, ⌊|z|⌋). +는 금리 하락 쪽(기간 프리미엄이 오르면 −)."""
    mag = min(2, math.floor(abs(z)))
    return 0 if mag == 0 else int(-math.copysign(mag, z))


def classify(za, zk, t=SPLIT_Z):
    """두 모형 z(TP↑ = +) → CASES 중 하나. t는 '유의'의 경계(|z| ≥ t)."""
    sa, sk = abs(za) >= t, abs(zk) >= t
    if sa and sk:
        if (za > 0) == (zk > 0):
            return "공통 TP↑" if za > 0 else "공통 TP↓"
        return "반대"
    if sa:
        return "ACM만"
    if sk:
        return "KW만"
    return "둘 다 약함"


def is_split(za, zk):
    """해석 갈림 — 한쪽만 유의(또는 둘이 반대)이면서 z 차이 ≥ SPLIT_GAP."""
    return classify(za, zk) in SPLIT_CASES and abs(za - zk) >= SPLIT_GAP


def kw_at(series, d):
    """d 이하 가장 최근 관측 — MONTH_GAP_DAYS보다 멀면 None."""
    hit = ff.on_or_before(series, d)
    return hit if hit and (d - hit[0]).days <= MONTH_GAP_DAYS else None


def month_pairs(kw, acm, since=SIGMA_SINCE):
    """ACM 연이은 두 관측 (d0, d1), d1 ≥ since마다 같은 기간의 (d1, ACM Δbp, KW Δbp). KW가 없는 달은 뺀다."""
    out = []
    for (d0, a0), (d1, a1) in zip(acm, acm[1:]):
        if d1 < since:
            continue
        k0, k1 = kw_at(kw, d0), kw_at(kw, d1)
        if k0 and k1:
            out.append((d1, (a1 - a0) * 100, (k1[1] - k0[1]) * 100))
    return out


def ols(x, y):
    """y = α + βx 최소제곱의 β. 점이 3개 미만이거나 x가 한 값이면 None."""
    n = len(x)
    if n < 3:
        return None
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    if sxx == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / sxx


def tp_share(vals, weekly, fy, last_d, base_d, chg_bp):
    """같은 4주의 10년(KW 적합) 변화, 그중 기간 프리미엄 몫, 평소 몫(σ와 같은 주간 표본에서 ΔTP를 Δ10년에 회귀한 기울기).
    10년 관측일이 TP 관측일과 정확히 같을 때만 — 아니면 비운다."""
    f1, f0 = ff.on_or_before(fy, last_d), ff.on_or_before(fy, base_d)
    if not (f1 and f0 and f1[0] == last_d and f0[0] == base_d):
        return
    y_bp = (f1[1] - f0[1]) * 100
    vals["y_4w_bp"] = _r(y_bp, BP_ND)
    if abs(y_bp) >= MIN_SHARE_BP:
        vals["tp_share"] = _r(chg_bp / y_bp, SHARE_ND)
    fyd = dict(ff.weekly_last(fy))
    pairs = [((b[1] - a[1]) * 100, (fyd[b[0]] - fyd[a[0]]) * 100)
             for a, b in zip(weekly, weekly[4:]) if a[0] in fyd and b[0] in fyd]
    if len(pairs) >= MIN_SIGMA_OBS:
        my = statistics.fmean(y for _, y in pairs)
        sxx = sum((y - my) ** 2 for _, y in pairs)
        if sxx > 0:
            mt = statistics.fmean(t for t, _ in pairs)
            vals["tp_share_typical"] = _r(sum((t - mt) * (y - my) for t, y in pairs) / sxx, SHARE_ND)


def calc_weekly(S, today):
    """주간 칸 — 비공개 원본 tp_auto.compute(숫자 자리도 같다). 마지막 관측이 MAX_AGE_DAYS보다 오래되면 숫자는 싣고 점수는
    비운다(age)."""
    kw = S[KW_ID]
    last_d = kw[-1][0]
    age = (today - last_d).days
    chg = ff.change_days(kw, CHANGE_DAYS)
    if not chg:
        raise ItemError("format")
    weekly = [x for x in ff.weekly_last(kw) if x[0] >= SIGMA_SINCE]
    diffs = [(b[1] - a[1]) * 100 for a, b in zip(weekly, weekly[4:])]
    if len(diffs) < MIN_SIGMA_OBS:
        raise ItemError("format")
    sigma = statistics.stdev(diffs)
    if not sigma > 0:
        raise ItemError("format")
    chg_bp = chg["delta"] * 100
    z = chg_bp / sigma
    fresh = age <= MAX_AGE_DAYS
    vals = {"kw_asof": _iso(last_d), "kw_base": _iso(chg["base_date"]), "tp_4w_bp": _r(chg_bp, BP_ND),
            "sigma_bp": _r(sigma, BP_ND),
            "sigma_n": len(diffs), "z": _r(z, Z_ND), "score": tp_score(z) if fresh else None,
            "age": None if fresh else age,
            "y_4w_bp": None, "tp_share": None, "tp_share_typical": None,
            "acm_month": None, "acm_month_bp": None, "kw_same_month_bp": None, "models_agree": None,
            "acm_z": None, "kw_month_z": None, "models_case": None, "models_split": None}
    if S.get(FY_ID):
        tp_share(vals, weekly, S[FY_ID], last_d, chg["base_date"], chg_bp)
    acm = [(r["date"], r["tp"]) for r in S.get(ACM) or ()]
    if len(acm) >= 2:
        (d0, v0), (d1, v1) = acm[-2], acm[-1]
        acm_bp = round((v1 - v0) * 100, BP_ND)
        vals.update(acm_month=_iso(d1), acm_month_bp=_r(acm_bp, BP_ND))
        k0, k1 = ff.on_or_before(kw, d0), ff.on_or_before(kw, d1)          # 같은 기간의 Kim-Wright
        if k0 and k1:
            kw_bp = round((k1[1] - k0[1]) * 100, BP_ND)
            vals["kw_same_month_bp"] = _r(kw_bp, BP_ND)
            if acm_bp != 0 and kw_bp != 0:
                vals["models_agree"] = (acm_bp > 0) == (kw_bp > 0)
    pairs = month_pairs(kw, acm)
    if len(pairs) >= MIN_PAIRS and pairs[-1][0] == acm[-1][0]:      # 마지막 쌍이 ACM 마지막 달일 때만 — 앞 달의 z를 싣지 않게
        sa, sk = statistics.stdev(p[1] for p in pairs), statistics.stdev(p[2] for p in pairs)
        if sa > 0 and sk > 0:
            za, zk = pairs[-1][1] / sa, pairs[-1][2] / sk
            vals.update(acm_z=_r(za, MZ_ND), kw_month_z=_r(zk, MZ_ND), models_case=classify(za, zk),
                        models_split=is_split(za, zk))
    return {"date": _iso(last_d), "values": vals}


def monthly_rows(kw, acm, since=SIGMA_SINCE):
    """ACM 연이은 두 월말 (a, b), b ≥ since인 달마다 같은 기간의 두 모형 변화(bp). dy는 실제 10년(ACM 파일 GSW) 변화 —
    GSW가 없는 달은 None(비공개 원본 월간 점검은 tp_compare.models_block에 적합 10년을 넘기지 않으므로 같게 비운다)."""
    out = []
    ends = month_ends(acm)
    for a, b in zip(ends, ends[1:]):
        if b["date"] < since:
            continue
        k0, k1 = kw_at(kw, a["date"]), kw_at(kw, b["date"])
        if not (k0 and k1):
            continue
        row = {"date": b["date"], "acm_dtp": (b["tp"] - a["tp"]) * 100, "kw_dtp": (k1[1] - k0[1]) * 100,
               "dy": None, "yield_src": None}
        if a.get("gsw") is not None and b.get("gsw") is not None:
            row["dy"], row["yield_src"] = (b["gsw"] - a["gsw"]) * 100, "GSW"
        out.append(row)
    return out


def _share(d, dy):
    """기간 프리미엄 몫(비율) — 10년 변화가 MIN_SHARE_BP 미만이거나 몫이 0~200% 밖이면 None."""
    if dy is None or abs(dy) < MIN_SHARE_BP:
        return None
    share = d / dy
    return share if 0 <= share <= 2 else None


def calc_models(S):
    """월간 칸 — 비공개 원본 tp_compare.models_block(summarize_monthly의 표본 σ·z·β). 비공개 원본이 반올림하지 않은 값으로
    그리므로 숫자는 원값으로 싣는다(_raw)."""
    rows = monthly_rows(S[KW_ID], S[ACM])
    if len(rows) < MIN_MONTHS:
        raise ItemError("format")
    a, k = [r["acm_dtp"] for r in rows], [r["kw_dtp"] for r in rows]
    sa, sk = statistics.stdev(a), statistics.stdev(k)
    if not (sa and sk):
        raise ItemError("format")
    for r in rows:
        r["z_acm"], r["z_kw"] = r["acm_dtp"] / sa, r["kw_dtp"] / sk
        r["case"], r["split"] = classify(r["z_acm"], r["z_kw"]), is_split(r["z_acm"], r["z_kw"])
    with_y = [r for r in rows if r["dy"] is not None]
    typ_acm = ols([r["dy"] for r in with_y], [r["acm_dtp"] for r in with_y])
    typ_kw = ols([r["dy"] for r in with_y], [r["kw_dtp"] for r in with_y])
    last, recent = rows[-1], rows[-WINDOW:]
    ra, rk = [r["acm_dtp"] for r in recent], [r["kw_dtp"] for r in recent]
    both = [r for r in recent if r["acm_dtp"] != 0 and r["kw_dtp"] != 0]
    corr = ff.pearson(ra, rk) if len(recent) >= 3 else None
    vals = {"month": _iso(last["date"]), "first": _iso(rows[0]["date"]), "n": len(rows),
            "dy": _raw(last["dy"]), "yield_src": last["yield_src"],
            "acm_dtp": _raw(last["acm_dtp"]), "kw_dtp": _raw(last["kw_dtp"]),
            "z_acm": _raw(last["z_acm"]), "z_kw": _raw(last["z_kw"]), "case": last["case"], "split": last["split"],
            "share_acm": _raw(_share(last["acm_dtp"], last["dy"])), "share_kw": _raw(_share(last["kw_dtp"], last["dy"])),
            "typ_acm": _raw(typ_acm), "typ_kw": _raw(typ_kw),
            "recent": [[_iso(r["date"]), r["case"], r["split"]] for r in rows[-RECENT:]],
            "corr12": _raw(corr), "n12": len(recent),
            "agree12": _raw(sum((r["acm_dtp"] > 0) == (r["kw_dtp"] > 0) for r in both) / len(both)) if both else None,
            "low_trust": corr is not None and corr < LOW_TRUST_CORR}
    return {"date": _iso(last["date"]), "values": vals}


# ---------- 칸 ----------
# values: 이름 → 꼴 — 직전 파일 검사와 새로 계산한 값 검사에 함께 쓴다. ends: 하나라도 직전보다 이르면 받지 않는다.
# optional: 없어도 칸을 계산하는 자료 → 그 자료로 채우는 값 이름(그 값이 있을 때만 출처에 싣는다)

ITEMS = [
    {"key": "weekly", "title": "Kim-Wright 10년 기간 프리미엄 4주 변화와 운영자 주간 점수", "series": [KW_ID],
     "optional": {FY_ID: "y_4w_bp", ACM: "acm_month"},
     "values": {"kw_asof": "day", "kw_base": "day", "tp_4w_bp": "num", "sigma_bp": "num", "sigma_n": "int", "z": "num",
                "score": "score?", "age": "int?", "y_4w_bp": "num?", "tp_share": "num?", "tp_share_typical": "num?",
                "acm_month": "day?", "acm_month_bp": "num?", "kw_same_month_bp": "num?", "models_agree": "bool?",
                "acm_z": "num?", "kw_month_z": "num?", "models_case": "case?", "models_split": "bool?"},
     "ends": ["kw_asof"]},
    {"key": "models", "title": "ACM과 Kim-Wright 월간 대조", "series": [KW_ID, ACM],
     "optional": {},                           # 10년은 ACM 파일의 GSW뿐 — 적합 10년을 쓰지 않는다
     "values": {"month": "day", "first": "day", "n": "int", "dy": "num?", "yield_src": "ysrc?", "acm_dtp": "num",
                "kw_dtp": "num", "z_acm": "num", "z_kw": "num", "case": "case", "split": "bool", "share_acm": "num?",
                "share_kw": "num?", "typ_acm": "num?", "typ_kw": "num?", "recent": "recent", "corr12": "num?",
                "n12": "int", "agree12": "num?", "low_trust": "bool"},
     "ends": ["month"]},
]
BY_KEY = {it["key"]: it for it in ITEMS}


def _is_recent(v):
    return (isinstance(v, list) and 1 <= len(v) <= RECENT
            and all(isinstance(x, list) and len(x) == 3 and ai._is_day(x[0]) and x[1] in CASES and type(x[2]) is bool
                    for x in v)
            and all(a[0] < b[0] for a, b in zip(v, v[1:])))


_KIND = dict(ai._KIND, **{
    "int?": lambda v: v is None or (type(v) is int and v >= 0),
    "score?": lambda v: v is None or (type(v) is int and -2 <= v <= 2),
    "bool": lambda v: type(v) is bool,
    "bool?": lambda v: v is None or type(v) is bool,
    "case": lambda v: isinstance(v, str) and v in CASES,
    "case?": lambda v: v is None or (isinstance(v, str) and v in CASES),
    "ysrc?": lambda v: v is None or (isinstance(v, str) and v in YIELD_SRC),
    "recent": _is_recent})


def values_ok(spec, vals):
    return (isinstance(vals, dict) and set(vals) == set(spec["values"])
            and all(_KIND[t](vals[k]) for k, t in spec["values"].items()))


# ---------- 문구 ----------

def _f(v, nd=1, sign=False, unit=""):
    return ai._f(v, nd, sign, unit)


def z_text(z):
    """표시용 z — 0 쪽으로 자른 둘째 자리(반올림하면 0.998이 '+1.00'으로 보여 점수와 어긋난다)."""
    t = math.trunc(z * 100) / 100
    return "0.00" if t == 0 else f"{t:+.2f}"


def score_text(v):
    return "0" if not v else f"{v:+d}"


def _pct(v):
    return "—" if v is None else f"{v * 100:.0f}%"


def _ml(day):
    return day[:7]


def _mon(day):
    return f"{int(day[5:7])}월"


def case_text(case, split):
    return "해석 갈림" if split else case


def split_reading(case):
    if case == "KW만":
        return "이 움직임을 KW는 기간 프리미엄 변화로, ACM은 기대 경로 변화로 더 읽음"
    if case == "ACM만":
        return "이 움직임을 ACM은 기간 프리미엄 변화로, KW는 기대 경로 변화로 더 읽음"
    return "두 모형의 기간 프리미엄 방향이 반대"


SCORE_DEF = (f"운영자 주간 평가 규칙(고정): z = 4주 변화 ÷ σ, σ = {SIGMA_SINCE.year}년 이후 주간(ISO 주의 마지막 관측) 4주 "
             "변화의 표준편차. 점수 = −부호(z) × min(2, ⌊|z|⌋) — |z|가 1 미만이면 0, 1 이상이면 ∓1, 2 이상이면 ∓2. 점수의 +는 "
             f"금리 하락 쪽이다(기간 프리미엄이 오르면 −). 마지막 관측이 {MAX_AGE_DAYS}일보다 오래되면 점수를 매기지 않는다. "
             "표시용 z는 0 쪽으로 자른다.")
SCORE_NOTE = ("운영자가 주간 평가에 쓰는 점수를 그대로 옮긴 참고값이다 — 금리를 예측하지 않고, 이 사이트의 규칙 수에 들지 "
              "않는다. Kim-Wright에서는 기간 프리미엄 변화가 10년 금리 변화의 약 절반으로 거의 일정해, 이 점수는 사실상 10년 "
              "금리의 4주 추세를 따른다.")
MODELS_DEF = (f"ACM 월말에서 다음 월말까지와 같은 기간의 Kim-Wright 변화를 각자 σ({SIGMA_SINCE.year}년 이후 같은 기간 월간 "
              f"변화의 표준편차)로 나눈 z로 견준다(bp끼리 견주면 ACM이 늘 커 보인다). |z| ≥ {SPLIT_Z:g}을 유의로 보고, 한쪽만 "
              f"유의이거나 둘이 반대 방향이면서 두 z의 차이가 {SPLIT_GAP:g} 이상이면 '해석 갈림'이다. 기간 프리미엄 몫(%)은 10년 "
              f"변화가 {MIN_SHARE_BP}bp 이상이고 몫이 0~200%일 때만 적고, '평소'는 같은 표본의 회귀 기울기(10년 1bp 중 기간 "
              "프리미엄으로 돌린 몫)다. 수준은 모형마다 체계적으로 달라 견주지 않는다.")


def texts(key, v, date):
    """칸 → (숫자 줄, 덧붙이는 줄 목록). 정해 둔 문구에 숫자만 넣는다."""
    if key == "weekly":
        score = (f"운영자 주간 점수 {score_text(v['score'])}" if v["age"] is None
                 else f"운영자 주간 점수 없음(마지막 관측이 {v['age']}일 전 — {MAX_AGE_DAYS}일 넘음)")
        line = (f"{v['kw_asof']} 기준 4주({v['kw_base']}부터) {_f(v['tp_4w_bp'], 1, True, 'bp')} ÷ σ "
                f"{_f(v['sigma_bp'], 1, unit='bp')} = z {z_text(v['z'])} · {score}")
        extra = []
        if v["y_4w_bp"] is not None:
            t = f"같은 4주 10년(Kim-Wright 적합) {_f(v['y_4w_bp'], 1, True, 'bp')}"
            if v["tp_share"] is not None:
                t += f" 중 기간 프리미엄 {_pct(v['tp_share'])}"
            if v["tp_share_typical"] is not None:
                t += f", 평소 {_pct(v['tp_share_typical'])}({SIGMA_SINCE.year}년 이후 주간 기울기)"
            extra.append(t)
        if v["acm_month"] is None:
            extra.append("ACM 참고 불가 — 이번에 받지 못했거나 견줄 관측이 모자람")
        else:
            t = f"ACM 참고: {_ml(v['acm_month'])} {_f(v['acm_month_bp'], 1, True, 'bp')}"
            if v["kw_same_month_bp"] is not None:
                t += f", 같은 기간 Kim-Wright {_f(v['kw_same_month_bp'], 1, True, 'bp')}"
            if v["models_split"]:
                t += (f" — 해석 갈림(z ACM {_f(v['acm_z'], 2, True)} · KW {_f(v['kw_month_z'], 2, True)}): 이 점수만 보지 말고 "
                      "정책 기대의 변화와 함께 볼 것")
            elif v["models_agree"] is False:
                t += " — 모형 방향 다름"
            extra.append(t)
        return line, extra + [SCORE_DEF, SCORE_NOTE]
    if key == "models":
        def part(name, d, share):
            return f"{name} {_f(d, 0, True, 'bp')}" + (f"({_pct(share)})" if share is not None else "")
        line = (f"{_ml(v['month'])} {case_text(v['case'], v['split'])}: "
                + (f"10년 {_f(v['dy'], 0, True, 'bp')} 중 " if v["dy"] is not None else "")
                + f"기간 프리미엄 몫 {part('KW', v['kw_dtp'], v['share_kw'])} · {part('ACM', v['acm_dtp'], v['share_acm'])}")
        if v["typ_kw"] is not None and v["typ_acm"] is not None:
            line += f", 평소 KW {_pct(v['typ_kw'])} · ACM {_pct(v['typ_acm'])}"
        extra = []
        if v["split"]:
            extra.append(f"{split_reading(v['case'])} — 이 달 기간 프리미엄 해석은 정책 기대의 변화와 함께 볼 것")
        extra.append("최근 3달: " + " · ".join(f"{_mon(m)} {case_text(c, sp)}" for m, c, sp in v["recent"])
                     + f" (z ACM {_f(v['z_acm'], 2, True)} · KW {_f(v['z_kw'], 2, True)}는 {_ml(v['month'])})")
        trust = f"{v['n12']}개월 일치도: 상관 {_f(v['corr12'], 2)} · 같은 방향 {_pct(v['agree12'])}"
        if v["low_trust"]:
            trust += f" · 신뢰 낮음 — 요즘은 기간 프리미엄 해석 자체를 덜 믿을 때(상관 {LOW_TRUST_CORR:g} 미만)"
        extra.append(trust)
        extra.append(f"표본 {_ml(v['first'])}~{_ml(v['month'])} {v['n']}개월. 10년은 "
                     + ("ACM 파일의 실제 10년 무이표 금리(GSW)" if v["yield_src"] == "GSW" else "이 달 자료 없음") + ".")
        return line, extra + [MODELS_DEF]
    raise KeyError(key)


def citation(sid, retrieved):
    d = datetime.date.fromisoformat(retrieved)
    when = f"{ai._MONTHS[d.month - 1]} {d.day}, {d.year}"
    src, title = SOURCES[sid]
    if sid == ACM:
        return f"{src}, {title} [TERMYld], retrieved from {ACM_URL}, {when}."
    return f"{src}, {title} [{sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; {rp.FRED_URL.format(sid)}, {when}."


def series_of(key, values=None):
    """칸이 쓴 자료 — 꼭 필요한 것과, 값을 채운 optional 자료."""
    spec, values = BY_KEY[key], values or {}
    out = list(spec["series"])
    for sid, field in spec.get("optional", {}).items():
        if values.get(field) is not None:
            out.append(sid)
    return out


def sources_of(key, retrieved=None, values=None):
    out = []
    for sid in series_of(key, values):
        url = ACM_PAGE if sid == ACM else rp.FRED_URL.format(sid)
        s = {"series": sid, "name": SOURCES[sid][0], "url": url, "licence": LICENCE[sid]}
        if retrieved:
            s["citation"] = citation(sid, retrieved)
        out.append(s)
    return out


def notices(key, retrieved, values=None):
    used = series_of(key, values)
    out = [COMPUTED_NOTICE, KW_NOTICE]
    if ACM in used:
        out += [ACM_DERIVED, ACM_DERIVED_EN, rp.nyfed_attribution(retrieved[:4]), rp.NOT_AFFILIATED, ACM_PAPER]
    return out


def present(key, core, retrieved):
    spec = BY_KEY[key]
    line, extra = texts(key, core["values"], core["date"])
    return {"key": key, "name": spec["title"], "date": core["date"], "values": core["values"], "retrieved": retrieved,
            "line": line, "extra": extra, "notices": notices(key, retrieved, core["values"]),
            "sources": sources_of(key, retrieved, core["values"])}


# ---------- 직전 파일 ----------

def core_of(item, key):
    """직전 파일의 칸 → (core, 받은 날) 또는 None(없거나 꼴이 어긋남)."""
    spec = BY_KEY[key]
    try:
        vals = item["values"]
        ok = ai._is_day(item["date"]) and ai._is_day(item["retrieved"]) and values_ok(spec, vals)
        if ok:
            texts(key, vals, item["date"])
    except (KeyError, TypeError, IndexError, AttributeError, ValueError):
        return None
    if not ok:
        return None
    return {"date": item["date"], "values": dict(vals)}, item["retrieved"]


def previous(out):
    try:
        with open(os.path.join(out, FILE), encoding="utf-8") as f:
            js = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(js, dict) or js.get("schema") != SCHEMA or not isinstance(js.get("items"), dict):
        return {}
    return {k: v for k, v in js["items"].items() if k in BY_KEY and isinstance(v, dict)}


def _ends(key, core):
    return [("date", core["date"])] + [(k, core["values"].get(k)) for k in BY_KEY[key].get("ends", ())]


def item_ok(key, core, prev, today):
    if not values_ok(BY_KEY[key], core["values"]):
        raise ItemError("format")                   # 새로 계산한 값도 같은 꼴을 넘어야 싣는다
    old = core_of(prev, key) if prev else None
    if old and any(new and was and new < was for (_, new), (_, was) in zip(_ends(key, core), _ends(key, old[0]))):
        raise ItemError("older")
    same = old and json.loads(json.dumps(old[0])) == json.loads(json.dumps(core))
    retrieved = old[1] if same else today.isoformat()
    return {"ok": True, "stale": False, "error": None, "failed_since": None, **present(key, core, retrieved)}


def item_failed(key, code, prev, today):
    since = prev.get("failed_since") if prev and ai._is_day(prev.get("failed_since")) else today.isoformat()
    old = core_of(prev, key) if prev else None
    if old:
        return {"ok": False, "stale": True, "error": REASONS[code], "failed_since": since, **present(key, *old)}
    return {"ok": False, "stale": False, "error": REASONS[code], "failed_since": since, "key": key,
            "name": BY_KEY[key]["title"], "sources": sources_of(key)}


def build(results, prev, now):
    today = now.date()
    items = {}
    for spec in ITEMS:
        key = spec["key"]
        r, p = results[key], prev.get(key)
        if not isinstance(r, ItemError):
            try:
                items[key] = item_ok(key, r, p, today)
                continue
            except ItemError as e:
                r = e
        items[key] = item_failed(key, r.code, p, today)
    return {"schema": SCHEMA, "generated_at": now.isoformat(timespec="seconds"), "notice": NOTICE,
            "order": [s["key"] for s in ITEMS], "items": items}


# ---------- 수신 ----------

def fetch_acm(deadline, clock=time.monotonic, opener=None):
    """ACM CSV 한 건. 남은 시간을 타임아웃으로 주고 읽는 동안에도 마감을 본다. 다른 곳으로 넘겨지면(리디렉션) 받지 않는다.
    헤더는 기본 그대로(비공개 원본 tp_auto.load_acm과 같다)."""
    left = deadline - clock()
    if left <= 1:
        raise TimeoutError("budget")
    chunks, size = [], 0
    with (opener or urllib.request.urlopen)(ACM_URL, timeout=min(ai.TIMEOUT, left)) as r:
        final = urllib.parse.urlsplit(r.geturl())
        if (final.scheme, final.netloc) != ("https", ACM_HOST):
            raise ValueError("redirect")
        while True:
            if clock() > deadline:
                raise TimeoutError("budget")
            chunk = r.read1(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError("too large")
            chunks.append(chunk)
    return b"".join(chunks).decode("utf-8", "replace")


def load_acm(cache_dir, offline, deadline, clock=time.monotonic, opener=None):
    """(ACM 행, 'net'|'cache'). 온라인이면 받아서(읽히면 캐시에 쓴다), --offline이면 캐시만."""
    path = os.path.join(cache_dir, ACM_CACHE)
    if offline:
        with open(path, encoding="utf-8") as f:
            return parse_acm(f.read()), "cache"
    text = fetch_acm(deadline, clock, opener)
    rows = parse_acm(text)
    if rows:
        try:
            os.makedirs(cache_dir, exist_ok=True)
            ai._atomic_write(path, text)
        except OSError:
            pass
    return rows, "net"


def load_all(work, offline=False, fred_load=None, clock=time.monotonic, budget=BUDGET, opener=None, acm_load=None):
    """{자료: 시계열}과 {자료: 실패 코드}. 온라인에서 캐시로 대신한 것은 실패('cache')."""
    cache = os.path.join(work, CACHE)
    data, errors = {}, {}
    deadline = clock() + budget
    for sid in SERIES:
        left = deadline - clock()
        if not offline and left <= 1:
            errors[sid] = "fetch"
            continue
        try:
            if sid == ACM:
                series, src = (acm_load(cache, offline=offline, timeout=min(ai.TIMEOUT, max(1.0, left))) if acm_load
                               else load_acm(cache, offline, deadline, clock, opener))
            elif fred_load:
                series, src = fred_load(sid, cache, offline=offline, timeout=min(ai.TIMEOUT, max(1.0, left)))
            else:
                series, src = ai.load_series(sid, cache, offline, deadline, clock, opener)
        except Exception:
            errors[sid] = "fetch"
            continue
        if src != "net" and not offline:
            errors[sid] = "cache"
            continue
        if not series:
            errors[sid] = "format"
            continue
        data[sid] = series
    return data, errors


def _upto(series, today):
    return [x for x in series if (x["date"] if isinstance(x, dict) else x[0]) <= today]


def compute(data, errors, today):
    S = {sid: _upto(s, today) for sid, s in data.items()}
    out = {}
    calc = {"weekly": lambda: calc_weekly(S, today), "models": lambda: calc_models(S)}
    for spec in ITEMS:
        miss = [sid for sid in spec["series"] if not S.get(sid)]
        if miss:
            out[spec["key"]] = ItemError(errors.get(miss[0], "format"))
            continue
        try:
            out[spec["key"]] = calc[spec["key"]]()
        except ItemError as e:
            out[spec["key"]] = e
        except Exception as e:                  # 계산 쪽 뜻밖의 오류도 그 칸만 실패로
            print(f"[tp_fetch] {spec['key']} 계산 오류: {type(e).__name__}", file=sys.stderr)
            out[spec["key"]] = ItemError("format")
    return out


# ---------- 쓰기 ----------

def differs(out, data):
    try:
        with open(os.path.join(out, FILE), encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        return True
    strip = lambda d: {k: v for k, v in d.items() if k != "generated_at"} if isinstance(d, dict) else d
    return strip(old) != strip(json.loads(json.dumps(data)))


def write(out, data):
    os.makedirs(out, exist_ok=True)
    ai._atomic_write(os.path.join(out, FILE), json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def main(argv=None, fred_load=None, now=None, clock=time.monotonic, opener=None, acm_load=None):
    ap = argparse.ArgumentParser(description="FRED Kim-Wright · 뉴욕 연은 ACM → 기간 프리미엄 모형 대조(<out>/tp.json)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    ap.add_argument("--work", default=DEFAULT_WORK, help="작업 폴더 — 원문 캐시는 <work>/tp/ (기본: 저장소의 .work/)")
    ap.add_argument("--offline", action="store_true", help="요청하지 않고 캐시만 읽는다(로컬 확인용)")
    a = ap.parse_args(argv)
    out, work = os.path.abspath(a.out), os.path.abspath(a.work)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    data, errors = load_all(work, a.offline, fred_load, clock, opener=opener, acm_load=acm_load)
    data = build(compute(data, errors, now.date()), previous(out), now)
    for spec in ITEMS:                          # Actions 로그 — 날짜와 정해 둔 사유만(값은 찍지 않는다)
        it = data["items"][spec["key"]]
        if it["ok"]:
            print(f"[tp_fetch] {spec['key']} {it['date']} 기준")
        else:
            kept = f" — 직전 값({it['date']} 기준) 유지" if it["stale"] else ""
            ai.annotate(f"기간 프리미엄 모형 대조 {spec['key']} 받지 못함: {it['error']}{kept}")
    for sid in SERIES:                          # 자료마다 — 선택 자료(적합 10년·주간 칸의 ACM)는 그 줄만 빈다
        if sid in errors:
            print(f"[tp_fetch] {sid} 받지 못함: {REASONS[errors[sid]]}")
    try:
        if differs(out, data):
            write(out, data)
    except OSError as e:
        print(f"[tp_fetch] {FILE}를 쓰지 못함: {type(e).__name__}", file=sys.stderr)
        return 1
    return 0 if any(it["ok"] for it in data["items"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
