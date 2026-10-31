#!/usr/bin/env python3
"""참고 자료 — 지준·재정 (2026-10-30 추가, 사용자 결정: 비공개 월간 알림의 [지준·재정] 블록을 공개 카드로).

공개 통계의 숫자와 산술(13주 차·나눔·비율·12개월 합)만 싣는다. 규칙이 아니다 — 충족·판정이 없고, 판정·공개본·그래프
스크립트는 이 파일(<out>/liquidity.json)을 읽지 않는다. 규칙 카드 '지준과 통화승수'(reserves_multiplier)의 지준/GDP가 왜
움직였는지 읽는 재료다. 칸(ITEMS — 화면 차례):
  reserves  최근 13주(91일) 지준 변화(H.4.1 수요일 수준 WRBWFRBL)를 대차대조표 항목으로 나눈다 — 재무부 현금 TGA(WDTGAL)·
            역레포 전체(WLRRAL — 익일물 + 해외 공적 풀)·연준 보유 단기채(WSHOBL)·명목 이표채(WSHONBNL)·그 밖(나머지:
            MBS 상환·현금 통화·대출 등). 부호는 지준 쪽 — TGA·역레포가 늘면 −. 다섯 줄이 모두 있는 마지막 수요일과 그 91일
            전 이하 마지막 공통 관측(NEAR_DAYS 안). 문구는 보이는 숫자끼리 합이 맞게 '그 밖'이 반올림 차를 받는다
  rule      지준/명목GDP와 규칙 하한(regime_rules.TH['reserves_gdp_low'])의 차(값 − 하한)를 %p와 달러로 — 값·GDP 분기는
            regime_check.compute와 같은 식(주 평균 WRESBAL의 마지막 값 ÷ 1000 ÷ 마지막 분기 GDP × 100)이라 규칙 카드와
            같은 숫자다(테스트가 견준다). 판정이 아니라 산술
  fiscal    연방 재정수지 12개월 합(MTSDS133FMS, 정확히 12개 달이 있을 때만)과 명목 GDP 대비 · 1년 전 12개월 · 연방 이자
            지출(국민계정 A091RC1Q027SBEA, 연율)/같은 분기 GDP · 시장성 국채 중 단기채 비중(Z.1 BOGZ1FL313161110Q /
            (그것 + BOGZ1FL313161275Q)) · 1년 전 같은 분기
산식은 비공개 파이프라인의 liquidity_block.py와 같다(저장소를 넘어 가져오지 않고 여기서 따로 쓴다 — 고치면 양쪽을 같이).
비공개 쪽과 다른 곳: TGA 수준은 재정 줄 끝이 아니라 지준 칸의 덧붙이는 줄에 적는다(칸마다 따로 실패하게), 규칙까지의 거리는
규칙 점검 결과를 넘겨받지 않고 같은 식으로 다시 계산한다(GDP는 재정 칸과 같은 수신분).

자료 이용 조건(2026-10-30 시리즈 쪽 JSON-LD의 license에서 확인 — LICENCE): 모두 'Public Domain: Citation Requested'(연준·
재무부·BEA). FRED 권장 인용을 함께 싣는다. 그 밖의 조건이 붙은 시리즈는 이 파일에 넣지 않는다(테스트가 목록을 고정한다).

실패·이어 싣기·문구 원칙은 oil_fetch·ai_invest_fetch와 같다: 칸마다 따로, 못 받은 칸은 직전 숫자를 '받지 못함'과 그날부터라는
날짜와 함께(직전 값이 없으면 사유만), 받은 자료가 직전보다 이르면 받지 않는다, 문구는 이 파일에 정해 둔 것뿐(오류 원문은 싣지
않는다), 같은 내용이면 다시 쓰지 않는다, 수신 전체 BUDGET초(응답을 읽는 동안에도 본다 — ai_invest_fetch.fetch_csv).

종료코드: 0 한 칸이라도 이번에 받음 / 1 하나도 못 받음(또는 파일을 쓰지 못함). 워크플로 단계는 continue-on-error, 알림 없음.

사용법: python scripts/liquidity_fetch.py [--out data] [--work .work] [--offline]
"""
import os, sys, json, time, argparse, datetime

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import regime_rules as rr                     # 규칙 하한(TH['reserves_gdp_low'])만 읽는다 — 공유 파일, 고치지 않는다
import render_public as rp
import ai_invest_fetch as ai                  # 수신(fetch_csv·load_series)·쓰기·꼴 검사를 그대로 쓴다

SCHEMA = 1
REPO = os.path.dirname(SCRIPTS)
DEFAULT_OUT = os.path.join(REPO, "data")
DEFAULT_WORK = os.path.join(REPO, ".work")
FILE = "liquidity.json"
CACHE = "liquidity"                           # <work>/liquidity/<ID>.csv

BUDGET = 60                                   # 수신 전체(초) — 워크플로 단계 제한(2분) 안에서 끝나게
WEEKS13 = 91                                  # 13주
NEAR_DAYS = 6                                 # 13주 전 공통 관측이 91일 전에서 이보다 멀면 비운다

_BOARD = "Board of Governors of the Federal Reserve System (US)"
_BEA = "U.S. Bureau of Economic Analysis"
_FISCAL = "U.S. Department of the Treasury. Fiscal Service"
# FRED 권장 인용의 출처·제목(2026-10-30 시리즈 쪽 Suggested Citation 그대로)
SOURCES = {
    "WRBWFRBL": (_BOARD, "Liabilities and Capital: Other Factors Draining Reserve Balances: Reserve Balances with Federal "
                         "Reserve Banks: Wednesday Level"),
    "WDTGAL": (_BOARD, "Liabilities and Capital: Liabilities: Deposits with F.R. Banks, Other Than Reserve Balances: "
                       "U.S. Treasury, General Account: Wednesday Level"),
    "WLRRAL": (_BOARD, "Liabilities and Capital: Liabilities: Reverse Repurchase Agreements: Wednesday Level"),
    "WSHOBL": (_BOARD, "Assets: Securities Held Outright: U.S. Treasury Securities: Bills: Wednesday Level"),
    "WSHONBNL": (_BOARD, "Assets: Securities Held Outright: U.S. Treasury Securities: Notes and Bonds, Nominal: "
                         "Wednesday Level"),
    "WRESBAL": (rp.FRED_SOURCE["WRESBAL"], rp.FRED_TITLE["WRESBAL"]),
    "GDP": (rp.FRED_SOURCE["GDP"], rp.FRED_TITLE["GDP"]),
    "MTSDS133FMS": (_FISCAL, "Federal Surplus or Deficit [-]"),
    "A091RC1Q027SBEA": (_BEA, "Federal government current expenditures: Interest payments"),
    "BOGZ1FL313161110Q": (_BOARD, "Federal Government; Total Marketable Treasury Bills; Liability, Level"),
    "BOGZ1FL313161275Q": (_BOARD, "Federal Government; Other Marketable Treasury Securities; Liability, Level"),
}
# 시리즈 쪽 JSON-LD의 license(2026-10-30 확인). 이 값 밖의 시리즈는 싣지 않는다
LICENCE = {sid: "public-domain" for sid in SOURCES}
SERIES = list(SOURCES)
BS = {"res": "WRBWFRBL", "tga": "WDTGAL", "rrp": "WLRRAL", "bills": "WSHOBL", "coupons": "WSHONBNL"}   # 수요일 수준, 백만 달러
FISCAL = {"deficit": "MTSDS133FMS", "interest": "A091RC1Q027SBEA", "bills_out": "BOGZ1FL313161110Q",
          "other_out": "BOGZ1FL313161275Q"}
PARTS = ("tga", "rrp", "bills", "coupons")    # 문구에서 각자 반올림하는 몫 — '그 밖'이 나머지를 받는다
SIGN_NOTE = "(부호는 지준 쪽)"                 # 지준 줄 끝 — 숫자 사이에 끼지 않게(보이는 숫자끼리 합은 그대로)

NOTICE = ("이 사이트의 규칙 점검에 쓰지 않는 참고 자료다. 규칙 카드 '지준과 통화승수'의 지준/GDP가 왜 움직였는지 읽는 "
          "재료로, 공개 통계로 계산한 산술만 싣는다. 금리나 자금 여건을 예측하지 않는다.")
COMPUTED_NOTICE = "13주 차·나눔·비율·12개월 합·하한 대비 차는 macro-regime-check가 원자료로 계산한 값이다."
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


# ---------- 산술 ----------

_r = ai._r
_iso = ai._iso


def _mkey(d):
    return d.year * 12 + d.month - 1


def _qkey(d):
    return d.year * 4 + (d.month - 1) // 3


def calc_reserves(S):
    """13주 지준 분해 — 다섯 줄이 모두 있는 마지막 수요일과, 그 91일 전 이하 마지막 공통 관측(NEAR_DAYS 안). 십억 달러."""
    common = sorted(set.intersection(*(set(d for d, _ in S[sid]) for sid in BS.values())))
    if not common:
        raise ItemError("format")
    d1 = common[-1]
    target = d1 - datetime.timedelta(days=WEEKS13)
    old = [d for d in common if d <= target]
    if not old or (target - old[-1]).days > NEAR_DAYS:
        raise ItemError("format")
    d0 = old[-1]
    v = {k: dict(S[sid]) for k, sid in BS.items()}
    ch = {k: (v[k][d1] - v[k][d0]) / 1000 for k in BS}
    parts = {"tga": -ch["tga"], "rrp": -ch["rrp"], "bills": ch["bills"], "coupons": ch["coupons"]}
    parts["other"] = ch["res"] - sum(parts.values())
    return {"date": _iso(d1),
            "values": {"from": _iso(d0), "res": _r(ch["res"]), "res_level": _r(v["res"][d1] / 1000),
                       "tga_level": _r(v["tga"][d1] / 1000), **{k: _r(x) for k, x in parts.items()}},
            "lines": {}}


def reserves_gdp(S):
    """regime_check.compute의 reserves_gdp와 같은 식 → (값 %, 지준 날짜, GDP 분기 날짜, GDP 십억 달러)."""
    wres, gdp = S["WRESBAL"], S["GDP"]
    gd, g = gdp[-1]
    if not g:
        raise ItemError("format")
    return wres[-1][1] / 1000 / g * 100, wres[-1][0], gd, g


def calc_rule(S):
    value, wd, gd, g = reserves_gdp(S)
    low = float(rr.TH["reserves_gdp_low"])
    return {"date": _iso(wd),
            "values": {"value": _r(value), "gdp_quarter": _iso(gd), "gdp_bn": _r(g), "low": low,
                       "gap_pp": _r(value - low), "gap_bn": _r((value - low) / 100 * g)},
            "lines": {}}


def calc_fiscal(S):
    """재정 — 12개월 합은 정확히 12개 달이 있을 때만, 1년 전 = 12개월 앞의 12개월. 이자 지출/GDP는 같은 분기끼리.
    단기채 비중은 두 줄이 모두 있는 마지막 분기, 1년 전 = 네 분기 앞(없으면 비움)."""
    m = {_mkey(d): (d, v) for d, v in S[FISCAL["deficit"]]}
    last = max(m)

    def sum12(k):
        return sum(m[k - i][1] for i in range(12)) / 1000 if all(k - i in m for i in range(12)) else None
    gdp = S["GDP"]
    g_d, g = gdp[-1]
    gq = {_qkey(d): v for d, v in gdp}
    i_d, i_v = S[FISCAL["interest"]][-1]
    bills = {_qkey(d): (d, v) for d, v in S[FISCAL["bills_out"]]}
    other = {_qkey(d): v for d, v in S[FISCAL["other_out"]]}

    def share(q):
        return bills[q][1] / (bills[q][1] + other[q]) * 100 if q in bills and q in other and \
            (bills[q][1] + other[q]) else None
    both = [q for q in bills if q in other]
    qb = max(both) if both else None
    s12, s12y = sum12(last), sum12(last - 12)
    dates = [m[last][0], i_d, g_d] + ([bills[qb][0]] if qb is not None else [])
    return {"date": _iso(max(dates)),
            "values": {"deficit_to": _iso(m[last][0]), "sum12": _r(s12), "sum12_1y": _r(s12y),
                       "sum12_gdp": _r(s12 / g * 100) if s12 is not None and g else None, "gdp_quarter": _iso(g_d),
                       "interest": _r(i_v), "interest_q": _iso(i_d),
                       "interest_gdp": _r(i_v / gq[_qkey(i_d)] * 100) if gq.get(_qkey(i_d)) else None,
                       "bills_share": _r(share(qb)) if qb is not None else None,
                       "bills_share_1y": _r(share(qb - 4)) if qb is not None else None,
                       "bills_q": _iso(bills[qb][0]) if qb is not None else None},
            "lines": {}}


# ---------- 칸 정의 (차례 = 화면 차례) ----------
# values: 이름 → 꼴("num" · "num?" · "day" · "day?") — 직전 파일 검사에도 쓴다
# ends: 시리즈마다의 끝 날짜(values의 날짜 칸) — 칸의 date와 함께 하나라도 직전보다 이르면 받지 않는다

ITEMS = [
    {"key": "reserves", "title": "지준 13주 변화의 나눔 (연준 대차대조표)", "series": list(BS.values()),
     "calc": calc_reserves,
     "values": {"from": "day", "res": "num", "res_level": "num", "tga_level": "num", "tga": "num", "rrp": "num",
                "bills": "num", "coupons": "num", "other": "num"}},
    {"key": "rule", "title": "지준/명목GDP와 규칙 하한의 차", "series": ["WRESBAL", "GDP"], "calc": calc_rule,
     "values": {"value": "num", "gdp_quarter": "day", "gdp_bn": "num", "low": "num", "gap_pp": "num", "gap_bn": "num"},
     "ends": ["gdp_quarter"]},
    {"key": "fiscal", "title": "미 연방 재정수지 · 이자 지출 · 단기채 비중",
     "series": [*FISCAL.values(), "GDP"], "calc": calc_fiscal,
     "values": {"deficit_to": "day", "sum12": "num?", "sum12_1y": "num?", "sum12_gdp": "num?", "gdp_quarter": "day",
                "interest": "num", "interest_q": "day", "interest_gdp": "num?", "bills_share": "num?",
                "bills_share_1y": "num?", "bills_q": "day?"},
     "ends": ["deficit_to", "interest_q", "bills_q", "gdp_quarter"]},
]
BY_KEY = {it["key"]: it for it in ITEMS}


# ---------- 문구 ----------

def _s(v, nd=0):
    """부호·천 단위 쉼표 — 반올림해 0이면 부호 없이."""
    if v is None:
        return "—"
    s = f"{v:+,.{nd}f}"
    return f"{0:.{nd}f}" if float(s.replace(",", "")) == 0 else s


def _q(day):
    """'2026-04-01' → '2026Q2'."""
    d = datetime.date.fromisoformat(day)
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def shown_parts(v):
    """문구의 정수 몫 — 지준 변화와 네 몫은 각자 반올림, '그 밖' = 반올림한 지준 변화 − 네 몫(보이는 숫자끼리 합이 맞게)."""
    sh = {k: round(v[k]) for k in PARTS}
    res = round(v["res"])
    return res, sh, res - sum(sh.values())


def texts(key, v, date):
    """칸 → (숫자 줄, 덧붙이는 줄 목록). 정해 둔 문구에 숫자만 넣는다."""
    if key == "reserves":
        res, sh, oth = shown_parts(v)
        return (f"지준 13주 변화 {_s(res)}bn ({v['from']}~{date}, 수요일) = 재무부 현금(TGA) "
                f"{_s(sh['tga'])} · 역레포(해외 공적 포함) {_s(sh['rrp'])} · 연준 단기채 {_s(sh['bills'])} · "
                f"연준 이표채 {_s(sh['coupons'])} · 그 밖 {_s(oth)} {SIGN_NOTE}",
                [f"{date} 지준 {v['res_level']:,.0f}bn · 재무부 현금(TGA) {v['tga_level']:,.0f}bn. bn은 십억 달러, H.4.1 "
                 "수요일 수준의 13주(91일 전 이하 마지막 공통 수요일) 차다.",
                 "부호는 지준 쪽이다 — 재무부 현금(TGA)·역레포가 늘면 그만큼 지준이 줄어 −, 연준 보유 국채가 늘면 +. 역레포는 "
                 "익일물 역레포와 해외 공적 역레포 풀을 합친 전체(WLRRAL)다. '그 밖'은 MBS 상환·현금 통화·대출·기타 부채의 "
                 "합(나머지)이고, 보이는 숫자끼리 합이 맞게 반올림 차를 받는다.",
                 "연준 이표채 13주 변화가 +면 연준의 명목 이표채(장기물) 보유가 늘었다는 뜻이다. 규칙 카드의 지준/GDP는 주 평균"
                 "(WRESBAL)을 써서 이 나눔의 지준(수요일 수준)과 조금 다르다."])
    if key == "rule":
        return (f"지준/명목GDP {v['value']:.2f}% ({date}, GDP {_q(v['gdp_quarter'])}) · 규칙 하한 {v['low']:.1f}% 대비 "
                f"{_s(v['gap_pp'], 2)}%p ≈ {_s(v['gap_bn'])}bn",
                [f"규칙 카드 '지준과 통화승수'와 같은 값·같은 GDP 분기다: 주 평균 지준(WRESBAL) ÷ 마지막 분기 명목 GDP"
                 f"(계절조정 연율, {_q(v['gdp_quarter'])} {v['gdp_bn']:,.0f}bn). 달러 환산 = (값 − 하한) × 그 분기 GDP.",
                 "하한 대비 차(값 − 하한)는 산술이다 — 다른 항목이 그대로일 때 +면 재무부 현금(TGA)이 그만큼 더 늘면 하한에 "
                 "닿고, −면 TGA가 그만큼 줄어야 하한으로 돌아온다."])
    if key == "fiscal":
        yr = f" (1년 전 {_s(v['sum12_1y'])}bn)" if v["sum12_1y"] is not None else ""
        bs = (f" · 시장성 국채 중 단기채 {v['bills_share']:.1f}% ({_q(v['bills_q'])}, 1년 전 "
              f"{'—' if v['bills_share_1y'] is None else format(v['bills_share_1y'], '.1f') + '%'})"
              if v["bills_share"] is not None else "")
        gdp_part = f", GDP의 {abs(v['sum12_gdp']):.1f}%" if v["sum12_gdp"] is not None else ""
        intr = f" · 연방 이자 지출 {v['interest']:,.0f}bn 연율({_q(v['interest_q'])}" + \
            (f", GDP의 {v['interest_gdp']:.1f}%)" if v["interest_gdp"] is not None else ")")
        head = (f"재정수지 12개월 합 {_s(v['sum12'])}bn (~{v['deficit_to'][:7]}{gdp_part}){yr}"
                if v["sum12"] is not None else f"재정수지 12개월 합: 12개 달이 다 있지 않음(~{v['deficit_to'][:7]})")
        return (head + intr + bs,
                [f"재정수지는 월간 재무제표(MTS)의 부호 그대로다(적자 −). 12개월 합은 12개 달이 모두 있을 때만, 1년 전은 그 "
                 f"12개월 앞의 12개월이다. GDP 대비는 마지막 분기 명목 GDP(계절조정 연율, {_q(v['gdp_quarter'])})로 나눈 산술이다.",
                 "이자 지출은 국민계정(분기, 계절조정 연율)이고 같은 분기 명목 GDP로 나눈다. 단기채 비중은 연준 금융계정(Z.1, "
                 "분기, 약 2.5개월 늦음)의 시장성 단기채 ÷ (단기채 + 그 밖 시장성 국채)이고, 1년 전은 네 분기 앞이다. 월간 국채 "
                 "잔액(MSPD)·분기 리펀딩은 FRED 밖이라 싣지 않는다."])
    raise KeyError(key)


def citation(sid, retrieved):
    d = datetime.date.fromisoformat(retrieved)
    src, title = SOURCES[sid]
    return (f"{src}, {title} [{sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; "
            f"{rp.FRED_URL.format(sid)}, {ai._MONTHS[d.month - 1]} {d.day}, {d.year}.")


def sources_of(spec, retrieved=None):
    out = []
    for sid in spec["series"]:
        s = {"series": sid, "name": SOURCES[sid][0], "url": rp.FRED_URL.format(sid), "licence": LICENCE[sid]}
        if retrieved:
            s["citation"] = citation(sid, retrieved)
        out.append(s)
    return out


def notices(spec):
    return [COMPUTED_NOTICE]


def present(key, core, retrieved):
    spec = BY_KEY[key]
    line, extra = texts(key, core["values"], core["date"])
    return {"key": key, "name": spec["title"], "date": core["date"], "values": core["values"], "retrieved": retrieved,
            "line": line, "extra": extra, "notices": notices(spec), "sources": sources_of(spec, retrieved)}


# ---------- 직전 파일 ----------

def core_of(item, key):
    """직전 파일의 칸 → (core, 받은 날) 또는 None(없거나 꼴이 어긋남 — 이어 실을 값이 없는 것으로 본다)."""
    spec = BY_KEY[key]
    try:
        vals = item["values"]
        ok = (ai._is_day(item["date"]) and ai._is_day(item["retrieved"]) and isinstance(vals, dict)
              and set(vals) == set(spec["values"]) and all(ai._KIND[t](vals[k]) for k, t in spec["values"].items()))
        if ok:
            texts(key, vals, item["date"])          # 문구를 다시 만들 수 있어야 한다
    except (KeyError, TypeError, IndexError, AttributeError, ValueError, OverflowError):
        return None
    if not ok:
        return None
    return {"date": item["date"], "values": dict(vals), "lines": {}}, item["retrieved"]


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
    spec = BY_KEY[key]
    return {"ok": False, "stale": False, "error": REASONS[code], "failed_since": since, "key": key,
            "name": spec["title"], "sources": sources_of(spec)}


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

def load_all(work, offline=False, fred_load=None, clock=time.monotonic, budget=BUDGET, opener=None):
    """{ID: 시계열}과 {ID: 실패 코드}. 온라인에서 캐시로 대신한 것은 실패('cache')."""
    cache = os.path.join(work, CACHE)
    data, errors = {}, {}
    deadline = clock() + budget
    for sid in SERIES:
        left = deadline - clock()
        if not offline and left <= 1:
            errors[sid] = "fetch"
            continue
        try:
            if fred_load:
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


def compute(data, errors, today):
    S = {sid: [(d, v) for d, v in s if d <= today] for sid, s in data.items()}
    out = {}
    for spec in ITEMS:
        miss = [sid for sid in spec["series"] if sid not in S or not S[sid]]
        if miss:
            out[spec["key"]] = ItemError(errors.get(miss[0], "format"))
            continue
        try:
            out[spec["key"]] = spec["calc"](S)
        except ItemError as e:
            out[spec["key"]] = e
        except Exception as e:                  # 계산 쪽 뜻밖의 오류도 그 칸만 실패로
            print(f"[liquidity_fetch] {spec['key']} 계산 오류: {type(e).__name__}", file=sys.stderr)
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


def main(argv=None, fred_load=None, now=None, clock=time.monotonic, opener=None):
    ap = argparse.ArgumentParser(description="FRED 공개 통계 → 지준·재정 참고 자료(<out>/liquidity.json)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    ap.add_argument("--work", default=DEFAULT_WORK, help="작업 폴더 — 원문 캐시는 <work>/liquidity/ (기본: 저장소의 .work/)")
    ap.add_argument("--offline", action="store_true", help="요청하지 않고 캐시만 읽는다(로컬 확인용)")
    a = ap.parse_args(argv)
    out, work = os.path.abspath(a.out), os.path.abspath(a.work)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    data, errors = load_all(work, a.offline, fred_load, clock, opener=opener)
    data = build(compute(data, errors, now.date()), previous(out), now)
    for spec in ITEMS:                          # Actions 로그 — 날짜와 정해 둔 사유만(값은 찍지 않는다)
        it = data["items"][spec["key"]]
        if it["ok"]:
            print(f"[liquidity_fetch] {spec['key']} {it['date']} 기준")
        else:
            kept = f" — 직전 값({it['date']} 기준) 유지" if it["stale"] else ""
            ai.annotate(f"지준·재정 참고 {spec['key']} 받지 못함: {it['error']}{kept}")
    try:
        if differs(out, data):
            write(out, data)
    except OSError as e:
        print(f"[liquidity_fetch] {FILE}를 쓰지 못함: {type(e).__name__}", file=sys.stderr)
        return 1
    return 0 if any(it["ok"] for it in data["items"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
