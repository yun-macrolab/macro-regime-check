#!/usr/bin/env python3
"""월간 레짐 점검의 규칙 표 — 시리즈 목록 · 임계값 · 신호 판정 · 시트 FLAG 판정 재료.

출처: 금융업계 미래 지도(2026-09-22) 00장 7절 월간 점검표 · 01장 3절 시나리오 신호,
      채권 주간평가 시트 v2 운영기준 7-1(국면)·7-2(ρ60)·7-4(전환 경계).
임계값은 보고서의 [추정] 수치다. 고칠 때는 이 파일만 고친다(코드가 아니라 표).
log_ids는 비공개 판단 로그의 행 ID다(공개판 화면에는 쓰지 않는다).
"""

# sid: (설명, 빈도 D/W/M/Q, 단위 메모)
SERIES = {
    "M2SL": ("M2", "M", "$bn"),
    "BOGMBASE": ("본원통화", "M", "$bn"),
    "M2V": ("M2 유통속도", "Q", ""),
    "WRESBAL": ("지준 잔액", "W", "$mn"),
    "GDP": ("명목GDP", "Q", "$bn SAAR"),
    "LNFACBW027SBOG": ("은행의 비은행금융(NDFI) 대출", "W", "$bn"),
    "TOTLL": ("은행 총대출", "W", "$bn"),
    "BUSLOANS": ("C&I 대출", "M", "$bn"),
    "THREEFYTP10": ("10년 기간 프리미엄(Kim-Wright)", "D", "%"),
    "BAA10Y": ("Baa−10년 스프레드", "D", "%p"),
    "BAMLH0A0HYM2": ("HY OAS", "D", "%p"),
    "BAMLC0A0CM": ("IG OAS", "D", "%p"),
    "SP500": ("S&P500", "D", ""),
    "DGS10": ("미 10년", "D", "%"),
    "T10Y2Y": ("10년−2년", "D", "%p"),
    "DFII10": ("10년 실질", "D", "%"),
    "T10YIE": ("10년 BEI", "D", "%"),
    "PCEPILFE": ("근원 PCE 물가", "M", "지수"),
    "CPILFESL": ("근원 CPI", "M", "지수"),
    "SOFR": ("SOFR", "D", "%"),
    "DEXKOUS": ("원/달러", "D", "KRW"),
    "CES5552300001": ("미 증권·투자업 고용", "M", "천명"),
}
# 마지막 관측일이 오늘보다 이보다 오래됐으면 경고. 관측일 기준이라 공표 시차를 포함한다
# (월간 M2·PCE는 다음다음 달 말 공표 → 최대 ~90일, 분기 GDP는 관측일이 분기 시작일이라 다음 속보 직전 ~212일,
#  Kim-Wright TP는 주 1회 갱신)
STALE_DAYS = {"D": 14, "W": 21, "M": 95, "Q": 220}

TH = {
    "ndfi_step_bn": 40.0,        # 00장 7절 #2: 한 주 +$40bn 이상 증가 = 재분류 계단, 제외 (감소는 제외하지 않는다)
    "ndfi_two_digit": 10.0,      # 00장 7절 #2: 두 자릿수 증가 유지 = A
    "spread_widen_pp": 0.4,      # 00장 7절 #5: 바닥 대비 +0.4~0.7%p = D 선행
    "hy_oas_break": 4.61,        # 00장 7절 #5 · 01장 F-01-A-04
    "corr_run_days": 126,        # 00장 7절 #6: 126영업일 양(+) 복귀 = B
    "real_rate_c": 2.0,          # 00장 7절 #7 · 01장 F-01-C-01
    "core_pce_split": 3.0,       # 00장 7절 #8: D1/D2의 갈림
    "reserves_gdp_low": 9.0,     # 00장 2-4절: 8%대 = 은행 대차대조표 임대료 상승(A)
    "reserves_gdp_rise_3m": 0.3, # (제안) 3개월 +0.3%p 이상 = 지준 재확대
    "reserves_pce_floor": 2.0,   # (제안) 지준 재확대가 C 후보가 되려면 근원 PCE 전년비가 이보다 높아야 한다
    "tp_drop_3m": 0.25,          # (제안) 00장 7절 #4엔 임계값 없음
    "sofr_rise_3m": 0.25,        # (제안) 00장 7절 #9엔 임계값 없음
    "sp_buf_pct": 2.0,           # 운영기준 7-1 완충 [초기값]
    "y10_buf_bp": 10.0,          # 운영기준 7-1 완충 [초기값]
}

# 자동화할 수 없는 항목 — 알림·md에 빈 칸으로 남긴다
MANUAL = [
    ("F-00-15", "분기", "비상장 BDC 환매 요청률(한도 5%) · bad PIK 비중 · 직접대출 디폴트율"),
    ("F-00-16", "분기", "하이퍼스케일러 capex 가이던스 · capex/OCF · 5사 회사채 발행 누계"),
    ("F-00-17", "분기", "Z.1 생보 회사채 순취득(FA543063005) · Athene 순스프레드(2분기 연속 1.0% 하회 여부)"),
    ("F-00-11", "월", "한국: 국고 10-30 · 3년−기준금리 · CP·전단채 스프레드 · 발행어음 잔액 · 일평균 거래대금 · 국민연금 국내주식 비중 대 목표"),
    ("F-00-02", "월", "연준 장기물 매입 재개 여부(지준/GDP 상승과 함께 읽을 것) · 재무부 단기물 편중 발행"),
    ("S-01-A-02", "분기", "하이퍼스케일러 capex 가이던스 상향 지속 여부"),
]


def _v(ind, key):
    x = ind.get(key)
    return None if isinstance(x, bool) and key != "ci_valid" else x


def _f(x, fmt="{:+.2f}", none="—"):
    return none if x is None else fmt.format(x)


# ---------- 시트 FLAG 판정 재료 (운영기준 7장) ----------

def classify_regime(sp_pct, y10_bp, prev=None, pct_buf=None, bp_buf=None):
    """운영기준 7-1: S&P 13주 수익률 × 미 10년 13주 변화의 사분면.
    주가↑금리↑ A / 주가↑금리↓ C / 주가↓금리↑ A′ / 주가↓금리↓ B. 완충 구간이면 직전 유지."""
    pct_buf = TH["sp_buf_pct"] if pct_buf is None else pct_buf
    bp_buf = TH["y10_buf_bp"] if bp_buf is None else bp_buf
    if sp_pct is None or y10_bp is None:
        return None, "재료 없음"
    if abs(sp_pct) <= pct_buf or abs(y10_bp) <= bp_buf:
        return prev, "완충 구간 → 직전 유지" + ("" if prev else " (직전 국면 미입력)")
    if sp_pct > 0:
        return ("A" if y10_bp > 0 else "C"), "사분면 판정"
    return ("A′" if y10_bp > 0 else "B"), "사분면 판정"


def _diffs(vals, k):
    if not vals or len(vals) < k + 1:
        return None
    v = vals[-(k + 1):]
    return [b - a for a, b in zip(v, v[1:])]


def _align_weeks(a, b):
    """두 주간 시계열을 ISO 주 키 교집합으로 맞춘 값 목록 — SP500과 DGS10의 마지막 관측일이 달라도 같은 주끼리 비교."""
    if not a or not b:
        return None, None
    bk = {d.isocalendar()[:2]: v for d, v in b}
    va, vb = [], []
    for d, v in a:
        k = d.isocalendar()[:2]
        if k in bk:
            va.append(v)
            vb.append(bk[k])
    return va, vb


def transition_triggers(sp_weekly, y10_weekly, ig_weekly):
    """운영기준 7-4 전환 경계 트리거 중 자동화 가능한 둘.
    t2: IG OAS 4주 연속 확대 또는 13주 고점 경신. t4: 주가·10년 주간 변화가 3주 연속 모두 음(−).
    t1(capex 가이던스)·t3(반도체 수출)은 수동. 넷 중 둘 이상이면 ON.
    입력은 완성된 주만 담은 주간 시계열이어야 한다(fred_fetch.weekly_last(before=이번 주 월요일))."""
    t2 = t4 = None
    va, vb = _align_weeks(sp_weekly, y10_weekly)
    ds, dy = _diffs(va, 3), _diffs(vb, 3)
    if ds is not None and dy is not None:
        t4 = all(x < 0 for x in ds) and all(x < 0 for x in dy)
    vals = [v for _, v in ig_weekly] if ig_weekly else None
    d_ig = _diffs(vals, 4)
    if d_ig is not None:
        high13 = len(vals) >= 14 and vals[-1] > max(vals[-14:-1])
        t2 = all(x > 0 for x in d_ig) or high13
    return {"t2": t2, "t4": t4, "auto_on": sum(1 for t in (t2, t4) if t),
            "note": "t1 capex 가이던스·t3 반도체 수출은 수동. 둘 이상이면 ON"}


# ---------- 시나리오 신호 규칙 ----------

def _sig(key, name, scenario, log_ids, source, fired, text):
    if fired is None and " → " in text:      # 값은 있는데 판정에 필요한 다른 자료가 없는 경우 — 결론 문구를 달지 않는다
        text = text.split(" → ")[0] + " → 일부 자료 없음(판정 불가)"
    return {"key": key, "name": name, "scenario": scenario, "log_ids": log_ids,
            "source": source, "fired": fired, "text": text}


def _cmp(x, op, th):
    """3값 비교: x가 None이면 None. 비교 전 소수 6자리로 반올림한다 — 소수 둘째 자리 자료끼리 뺀 값이
    0.3999999…가 되어 '0.4 이상' 경계를 놓치지 않게."""
    if x is None:
        return None
    x = round(x, 6)
    return {"<": x < th, "<=": x <= th, ">": x > th, ">=": x >= th}[op]


def _and(*xs):
    """3값 논리 AND: 하나라도 거짓이면 거짓, 아니고 하나라도 모르면 모름."""
    if any(x is False for x in xs):
        return False
    return None if any(x is None for x in xs) else True


def _or(*xs):
    """3값 논리 OR: 하나라도 참이면 참, 아니고 하나라도 모르면 모름."""
    if any(x is True for x in xs):
        return True
    return None if any(x is None for x in xs) else False


def evaluate(ind):
    """ind(평면 dict: 지표 → 값/None) → 신호 목록. fired: True 발동 / False 미발동 / None 판정불가.
    복합 조건은 3값 논리 — 한쪽 자료가 없으면 결론이 나는 경우에만 참·거짓, 아니면 판정 불가."""
    out = []
    ci, ng = ind.get("ci_yoy"), ind.get("ngdp_yoy")
    if ci is None or ng is None or not ind.get("ci_valid"):
        f, t = None, "C&I YoY 판정불가(2025-01 분류 단절 이전 기준치 또는 자료 없음)"
    else:
        f = _cmp(ci - ng, "<", 0)
        t = f"C&I {ci:+.1f}% vs 명목GDP {ng:+.1f}% → " + ("명목성장률 아래 = A 반증" if f else "상회 = A 진행")
    out.append(_sig("ci_vs_ngdp", "C&I 대출 YoY 대 명목GDP YoY", "A",
                    ["F-00-04", "S-01-A-01", "F-01-A-02", "S-01-B-04"], "00장 7절 #3 · 01장 3절 A/B", f, t))

    ny, sh = ind.get("ndfi_yoy"), ind.get("ndfi_share")
    if ny is None:
        f, t = None, "NDFI YoY 자료 없음"
    else:
        f = _cmp(ny, "<", TH["ndfi_two_digit"])
        t = f"NDFI 대출 YoY {ny:+.1f}%(계단 제외), 총대출의 {_f(sh, '{:.1f}')}% → " + \
            ("두 자릿수 붕괴 = A→D 방아쇠 주의" if f else "두 자릿수 유지 = A 진행")
    out.append(_sig("ndfi_credit", "은행의 비은행 대출(NDFI) YoY", "A, D",
                    ["F-00-03", "S-01-A-04", "S-01-D-05"], "00장 7절 #2 · 01장 3절 A/D", f, t))

    baa, low, hy, pct = ind.get("baa10y"), ind.get("baa10y_from_low"), ind.get("hy_oas"), ind.get("baa10y_pct")
    if baa is None and hy is None:
        f, t = None, "스프레드 자료 없음"
    else:
        wide = _cmp(low, ">=", TH["spread_widen_pp"])
        brk = _cmp(hy, ">", TH["hy_oas_break"])
        f = _or(wide, brk)
        t = (f"Baa−10Y {_f(baa, '{:.2f}')}%p(바닥 대비 {_f(low)}, 1990년 이후 하위 {_f(pct, '{:.1%}', '—')})"
             f" · HY OAS {_f(hy, '{:.2f}')}%p → " + ("D 선행 신호" if f else "확대 없음(A 유지)"))
    out.append(_sig("credit_spread", "신용 스프레드 (Baa−10Y · HY OAS)", "D",
                    ["F-00-06", "S-01-D-01", "F-01-A-04", "F-01-D-02"], "00장 7절 #5 · 01장 3절 A/D", f, t))

    rho, run, sign = ind.get("rho60"), ind.get("rho60_run"), ind.get("rho60_sign")
    if rho is None:
        f, t = None, "ρ60 자료 없음"
    else:
        f = sign == "+" and (run or 0) >= TH["corr_run_days"]
        if f:
            t = f"ρ60 {rho:+.2f}, 양(+) {run}영업일 = 126일 복귀 → B 신호"
        elif sign == "+":
            t = f"ρ60 {rho:+.2f}, 양(+) {run}영업일째(126일 미만)"
        else:
            t = f"ρ60 {rho:+.2f}, 음(−) {run}영업일 지속 = 분산 붕괴·전사 위험 한도 압박"
    out.append(_sig("stock_bond_corr", "주가-금리 60일 상관", "B",
                    ["F-00-07", "F-00-01", "S-01-B-02", "F-01-B-03"], "00장 7절 #6 · 01장 3절 B", f, t))

    c = ind.get("t10y2y")
    f = _cmp(c, "<", 0)
    t = f"2s10s {_f(c)}%p → " + ("역전 = D 선행" if f else "정상(역전 없음)") if c is not None else "2s10s 자료 없음"
    out.append(_sig("curve_inversion", "2s10s 커브", "D",
                    ["F-00-08", "S-01-D-02", "S-01-B-03"], "00장 7절 #7 · 01장 3절 D/B", f, t))

    rr_, bei_chg, bei = ind.get("dfii10"), ind.get("bei_chg_3m"), ind.get("bei")
    if rr_ is None:
        f, t = None, "실질금리 자료 없음"
    else:
        f = _and(_cmp(rr_, "<", TH["real_rate_c"]), _cmp(bei_chg, ">", 0))
        t = (f"10년 실질 {rr_:.2f}% · BEI {_f(bei, '{:.2f}')}%(3개월 {_f(bei_chg)}) → "
             + ("실질 2% 하회 + BEI 상승 = C 신호" if f else ("실질 2% 위 = C 반증(F-01-C-01)" if rr_ >= TH["real_rate_c"] else "실질 2% 아래이나 BEI 상승 없음")))
    out.append(_sig("real_rate_bei", "실질금리·BEI", "C",
                    ["F-00-08", "S-01-C-04", "F-01-C-01", "S-01-A-05"], "00장 7절 #7 · 01장 3절 C/A", f, t))

    pce, cpi, gap = ind.get("core_pce_yoy"), ind.get("core_cpi_yoy"), ind.get("core_gap")
    if pce is None:
        f, t = None, "근원 PCE 자료 없음"
    else:
        f = _cmp(pce, "<=", TH["core_pce_split"])
        t = (f"근원 PCE {pce:.2f}% (근원 CPI {_f(cpi, '{:.2f}')}%, 괴리 {_f(gap)}%p) → "
             + ("3% 이하 = D1 쪽, SEP 경로 추종이면 B" if f else "3% 초과 = D2 쪽(붕괴 시 채권 방어 불완전)"))
    out.append(_sig("core_inflation", "근원 PCE (근원 CPI 병기)", "B, D",
                    ["F-00-09", "F-00-01", "S-01-B-01", "F-01-B-01", "F-00-25"], "00장 7절 #8 · 01장 3절 B", f, t))

    tp, tpc = ind.get("tp"), ind.get("tp_chg_3m")
    if tp is None:
        f, t = None, "기간 프리미엄 자료 없음"
    else:
        f = _cmp(tpc, "<=", -TH["tp_drop_3m"])
        t = f"TP(Kim-Wright) {tp:.2f}% (3개월 {_f(tpc)}) → " + \
            ("하락 = 듀레이션 수요 충분 후보(A 반증, 발행 지속 여부 수동 확인)" if f else "하락 없음(A 진행)")
    out.append(_sig("term_premium", "기간 프리미엄", "A",
                    ["F-00-05", "S-01-A-03", "F-01-A-03"], "00장 7절 #4 · 01장 3절 A", f, t))

    so, soc = ind.get("sofr"), ind.get("sofr_chg_3m")
    f = None if so is None else _cmp(soc, ">=", TH["sofr_rise_3m"])
    t = "SOFR 자료 없음" if so is None else \
        f"SOFR {so:.2f}% (3개월 {_f(soc)}) → " + ("재상승 = 2021 빈티지 이자보상 재악화·PIK 증가" if f else "재상승 없음")
    out.append(_sig("sofr", "SOFR (LBO 기준금리)", "A, D", ["F-00-10"], "00장 7절 #9", f, t))

    rg, rgc, mult = ind.get("reserves_gdp"), ind.get("reserves_gdp_chg_3m"), ind.get("mult")
    if rg is None:
        f, t = None, "지준/GDP 자료 없음"
    else:
        a_side = _cmp(rg, "<", TH["reserves_gdp_low"])
        c_side = _and(_cmp(rgc, ">=", TH["reserves_gdp_rise_3m"]), _cmp(pce, ">", TH["reserves_pce_floor"]))
        f = _or(a_side, c_side)
        t = f"승수 {_f(mult, '{:.2f}')} · 지준/명목GDP {rg:.1f}% (3개월 {_f(rgc)}%p) → " + \
            ("8%대 = 대차대조표 임대료 상승(A)" if a_side else
             ("지준 재확대 + 물가 목표 상회 = C 후보(장기물 매입 여부 수동 확인)" if c_side else "9%대 유지(B 산술)"))
    out.append(_sig("reserves_multiplier", "통화승수·지준/GDP", "A, C",
                    ["F-00-02", "S-01-C-01", "F-01-C-02"], "00장 2-4절·7절 #1 · 01장 3절 C", f, t))

    ey = ind.get("emp_yoy")
    f = _cmp(ey, "<", 0)
    t = "고용 자료 없음" if ey is None else f"증권·투자업 고용 YoY {ey:+.1f}% → " + ("감소 전환 = 인원 조정 시작" if f else "증가 유지(강세장 코호트)")
    out.append(_sig("employment", "미 증권·투자업 고용", "공통", ["F-00-18", "F-00-20"], "00장 7절 #14", f, t))
    return out
