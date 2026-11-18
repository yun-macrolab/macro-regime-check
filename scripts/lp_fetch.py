#!/usr/bin/env python3
"""참고 자료 — 노동 L × 물가 P 판단 격자 (2026-11-18 운영자 결정 '4번 L×P 격자 카드 시작해').

운영자의 비공개 측정 도구(econ_regime_check.py — 권고안 4절 '판단 표', 문턱 고정 2026-10-14)가
정해 둔 판단 격자를 FRED 공개 통계(현재 개정치)로 이 저장소가 따로 다시 계산한다. 비공개 저장소의 코드를 가져오지 않고 여기서
따로 쓴다 — 규칙(문턱·다리·히스테리시스·꼬리표·칸 이름)을 고치면 양쪽을 같이 고치고, 비공개 저장소의 짝 테스트가 같은 입력으로
두 쪽의 답(기준월마다 L·raw L·P·띠·모멘텀·칸·꼬리표, 지금 칸의 다리 13개, 사례 대조)을 견준다.

규칙이 아니다 — 충족이 없고, 판정·공개본·그래프 스크립트는 이 파일(<out>/lp.json)을 읽지 않는다. 칸 이름 16개는 운영자 메모이고
늘 LABEL('운영자 판단 격자의 칸 이름(운영자 메모) — 예측 아님 · 예측력 검증 안 됨') 아래에 싣는다.

계산(비공개 도구와 같은 순서·같은 비교 — 비교는 소수 6자리 반올림 뒤):
  노동 다리(labor_panel) 기준월 t = 실업률이 발표된 달, 1960-01부터(SINCE — 비공개 도구의 LABOR_START·기본 --since와 같다).
      u3 = 실업률 3개월 평균(빠진 달은 남은 2개월), Sahm형 = u3 − 직전 12개 창의 u3 최저(창 9개 이상), hi_gap = u3 − 그 최고,
      u3 상승 = 3개월 전 u3보다 높음, 핵심연령 고용률·V/U·이직률은 3개월 평균의 6개월 변화(JOLTS는 t의 근원 PCE 발표일까지
      나온 최신 달), 민간고용 3개월 평균 증감, 해고 몫 = 영구 실직 3개월 평균의 12개월 증가 ÷ 실업자 3개월 평균의 12개월 증가
      (실업자 증가 100천 명 이상일 때만 — 표시만), 청구 다리 = 4주 평균이 직전 52주(그중 40개 이상) 최저의 1.25배 이상인 주가
      4주 연속 그리고 계속 청구(그 주 이하 13일 안의 최근 주)가 13주 전(6일 여유)보다 높음 — 그 달 마지막 주로.
  L(l_raw·replay_l) 4-1 표와 4-4 히스테리시스 — 모든 변화는 서로 다른 두 발표 연속(L−−만 한 발표로 진입), L−·L−−에서는 이탈
      조건이 두 발표 연속이면 L0과 꼬리표 '고점 통과' 한 번(비공개 도구의 '고점 통과 — 되돌림 소진 가능'에서 해석 부분을 뺀
      앞부분 — 이 카드에서 방향을 말하는 글은 칸 이름 16개뿐이다), 그 달 L을 모르면 '?'이고 연속 셈이 끊긴다(상태는 이어진다).
      P만 모르는 달은 칸이 보류일 뿐 L의 셈에 닿지 않는다(P는 L 재생의 입력이 아니다).
  P(infl_rows·pce_states) 근원 PCE 전년비 3개월 평균 Y3의 띠(H 3.1 초과로 들어가 2.9 미만에서 나옴 · Lo 2.6 미만으로 들어가
      2.7 초과에서 나옴) × 모멘텀 a6 − y12(A ≥ +0.5 한 발표 · D ≤ −0.3 두 발표 연속 · F 그 밖) → 9칸.
  칸(cell) 4-2 격자 16칸, L 또는 P를 모르면 '판정 보류(노동·물가)'(종류 hold).
  꼬리표 비공개 재생의 꼬리표에서 셋을 뺀 것(EXCLUDED_TAGS — '상당 부분 반영'(정책 경로 가격) · 'TP 주도'(기간 프리미엄) ·
      '폭 좁음(트림 ≤ 3)'(댈러스 연은 트림 평균): 이 사이트가 싣지 않는 자료·렌즈가 필요하다).
  지금 칸(current) = 칸이 '판정 보류'가 아닌 마지막 기준월(비공개 sec_decision의 current), 그보다 새 달이 보류면 latest로 따로.
  사례 대조(expected) 운영자가 미리 적어 둔 4-5 사례를 L·P로만 견준다(꼬리표 대조는 하지 않는다). 2024-01부터는 운영자가
      지정한 hold-out — 문턱 고정(2026-10-14) 때 이미 나와 있던 자료이고, 둔화 모멘텀 문턱은 2024-09 재생도 보고 골랐다.
  지금 칸의 덧칸(공개만 — 비공개 도구에 없는 표시용): raw_rules = 그 달 조건만의 L(l_raw)을 만든 절의 이름(l_raw와 같은 갈래를
      따라간다), d6u3 = u3의 6개월 변화(고점 대비 하락 다리의 둘째 조건). latest.known = 가장 새 달의 알려진 날(근사).
비공개 도구에만 있는 것(밸류 크기 꼬리표·밸류 숫자·가격 경로 숫자·β·칸별 이후 금리 변화·1·4·5·7절)은 싣지 않는다.
숫자가 유한하지 않은 관측(FRED CSV의 NaN·inf 꼴)은 받는 자리에서 버리고, 쓰는 JSON은 allow_nan=False로 만든다(깨진 JSON을
커밋하면 다음 날 check 잡이 실패해 모든 갱신이 멈춘다 — 만들 수 없으면 어제 파일을 둔다).

자료(FRED, 모두 'Public Domain: Citation Requested' — 2026-11-18 시리즈 쪽에서 확인): UNRATE · LNS12300060 · UNEMPLOY ·
LNS13026638(받지 못하면 LNS13025699 — 비공개 Ctx.perm_sid와 같은 규칙) · USPRIV · ICSA · CCSA · JTSJOL · JTSQUR · PCEPILFE ·
CPIAUCSL · CPILFESL · CUSR0000SACL1E. 전체 이력을 받는다(FRED CSV 기본 — 비공개 load_series도 앞쪽 관측을 버리지 않는다).

수신: fred_fetch.load(기본 헤더 그대로), 캐시 <cache>(기본 .work/lp/). 같은 실행에서 규칙 점검(regime_check.py)이 이미 받아
<reuse>(기본 .work/fred/)에 오늘(UTC) 쓴 파일이 있으면 그것을 읽는다(요청 0번). 수신 전체 BUDGET초, 요청마다 min(15초, 남은 시간).
전부 아니면 쓰지 않음: 하나라도 받지 못하면(온라인에서 캐시로 대신한 것도 — 영구 실직자 두 시리즈는 하나로 센다) <out>/lp.json을
쓰지 않고 '::warning::[lp_fetch] …' 한 줄을 남긴 뒤 종료코드 0(어제 파일이 그대로 남는다). 빠진 다리로 계산한 격자를 싣지 않는다.
--offline이면 캐시만 읽는다(로컬 확인용 — 출처에 cache). 계산한 내용이 지금 파일과 generated_at 말고 같으면 다시 쓰지 않는다.
쓰기는 임시 파일 → os.replace.

종료코드: 0 썼거나, 같아서 두었거나, 받지 못해 두었음 / 1 파일을 쓰지 못함.

사용법: python scripts/lp_fetch.py [--out data] [--offline] [--cache DIR] [--reuse DIR] [--budget SECONDS]
"""
import os, sys, json, math, time, bisect, argparse, calendar, datetime

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import fred_fetch as ff
import render_public as rp

D = datetime.date
SCHEMA = 1
REPO = os.path.dirname(SCRIPTS)
DEFAULT_OUT = os.path.join(REPO, "data")
DEFAULT_CACHE = os.path.join(REPO, ".work", "lp")
DEFAULT_REUSE = os.path.join(REPO, ".work", "fred")      # regime_check.py가 같은 실행에서 받아 둔 원자료
FILE = "lp.json"
BUDGET = 45
TIMEOUT = 15
SINCE = D(1960, 1, 1)
FIXED = "2026-10-14"
HISTORY_FROM = "2022-01"

# ---------- 상수 — 비공개 econ_regime_check.py와 같은 값('(고정 2026-10-14)'은 운영자 권고안의 '문턱 고정 기록') ----------
SAHM_ON = 0.50
SAHM_WATCH = 0.40          # (고정 2026-10-14)
HI_GAP = -0.30
D6U = -0.20
MIN_WINDOWS = 9
LAYOFF_HI, LAYOFF_LO = 0.5, 0.3     # 해고형/진입형 꼬리표만(판단 다리 아님)
MIN_DU = 100               # 천 명
CLAIMS_RATIO, CLAIMS_WEEKS = 1.25, 4    # (고정 2026-10-14)
EPOP_UP, EPOP_DN = 0.2, -0.3
VU_UP, VU_DN = 0.10, -0.15      # VU_DN (고정 2026-10-14)
QUITS_UP = 0.10
H_IN, H_OUT, LO_IN, LO_OUT = 3.1, 2.9, 2.6, 2.7     # H_IN·H_OUT (고정 2026-10-14)
MOM, MOM_N = 0.5, 1        # 가속 A (고정 2026-10-14)
MOM_DN, MOM_DN_N = 0.3, 2  # 둔화 D (고정 2026-10-14)
SUPPLY_HC, GOODS_LED = 1.0, 2.0
SHUTDOWN_CPI = ("2025-10", "2025-11", "2026-04")
# 셧다운으로 늦어진 월간 발표 (종류, 기준월) → 실제 발표일 — 비공개 도구의 표 그대로(그쪽 주석: 기억에 의한 값, 확인할 것)
RELEASE_DATE_OVERRIDE = {
    ("cps", "2013-09"): D(2013, 10, 22), ("cps", "2013-10"): D(2013, 11, 8), ("cpi", "2013-09"): D(2013, 10, 30),
    ("pce", "2013-09"): D(2013, 11, 8), ("cps", "2025-09"): D(2025, 11, 20), ("cps", "2025-10"): D(2025, 12, 16),
    ("cps", "2025-11"): D(2025, 12, 16), ("cpi", "2025-09"): D(2025, 10, 24), ("cpi", "2025-11"): D(2025, 12, 18),
    ("pce", "2025-09"): D(2025, 12, 5),
}
DELAYED_REFS = ("2013-09", "2013-10", "2025-09", "2025-10", "2025-11", "2025-12")
LABOR_START = "1960-01"
REPLAY_START = "1990-01"
HOLDOUT = "2024-01"
DAYS_3M = 91
CCSA_TOL = 13

# 공개 파일의 문턱 — data/lp.json 'constants'(약속된 키 그대로)
CONSTANTS = {"sahm_on": SAHM_ON, "sahm_watch": SAHM_WATCH, "hi_gap": HI_GAP, "d6u": D6U, "claims_ratio": CLAIMS_RATIO,
             "claims_weeks": CLAIMS_WEEKS, "epop_up": EPOP_UP, "epop_dn": EPOP_DN, "vu_up": VU_UP, "vu_dn": VU_DN,
             "quits_up": QUITS_UP, "h_in": H_IN, "h_out": H_OUT, "lo_in": LO_IN, "lo_out": LO_OUT, "mom": MOM,
             "mom_n": MOM_N, "mom_dn": MOM_DN, "mom_dn_n": MOM_DN_N,
             "layoff_hi": LAYOFF_HI, "layoff_lo": LAYOFF_LO}     # 해고 몫 표시 줄의 경계(판단 다리 아님 — 화면이 숫자 자리를 정한다)


def _th(x, fmt="{:.2f}"):
    """문턱 표기 — 음수는 유니코드 빼기(−)."""
    return fmt.format(x).replace("-", "−")


# 다리 이름 — 비공개 leg_list와 같은 글(상수에서 만든다)
LEG_SAHM_ON = f"Sahm형 ≥ {_th(SAHM_ON)}"
LEG_SAHM_WATCH = f"Sahm형 ≥ {_th(SAHM_WATCH)}"
LEG_RISING = "u3 상승(3개월 전보다)"
LEG_LAYOFF = "해고 몫(표시만)"
LEG_CLAIMS = f"청구 다리({_th(CLAIMS_RATIO)} × {CLAIMS_WEEKS}주 + CCSA 상승)"
LEG_EPOP_DN = f"핵심연령 고용률 3개월 Δ6 ≤ {_th(EPOP_DN, '{:g}')}"
LEG_VU_DN = f"V/U 3개월 Δ6 ≤ {_th(VU_DN)}"
LEG_U2 = f"고점 대비 하락(U2: hi_gap ≤ {_th(HI_GAP)} · Δ6 ≤ {_th(D6U)})"
LEG_P3 = "민간고용 3개월 평균 ≤ 0(천 명)"
LEG_EPOP_UP = f"회복 확인(고용률 ≥ +{EPOP_UP:g})"
LEG_VU_UP = f"회복 확인(V/U Δ6 ≥ +{VU_UP:.2f})"
LEG_BAND = "근원 PCE Y3 띠"
LEG_MOM = "근원 PCE 모멘텀(a6 − y12)"
LEG_ORDER = (LEG_SAHM_ON, LEG_SAHM_WATCH, LEG_RISING, LEG_CLAIMS, LEG_LAYOFF, LEG_EPOP_DN, LEG_VU_DN, LEG_P3, LEG_U2,
             LEG_EPOP_UP, LEG_VU_UP, LEG_BAND, LEG_MOM)
# 다리 값을 저장할 때 견줄 문턱(4자리로 반올림한 값이 문턱의 다른 쪽에 보이면 6자리로 둔다)
_SAHM_THS = (SAHM_ON, SAHM_WATCH, 0.0)
LEG_THS = {LEG_SAHM_ON: _SAHM_THS, LEG_SAHM_WATCH: _SAHM_THS, LEG_CLAIMS: (CLAIMS_RATIO,),
           LEG_LAYOFF: (LAYOFF_HI, LAYOFF_LO), LEG_EPOP_DN: (EPOP_DN, EPOP_UP), LEG_EPOP_UP: (EPOP_DN, EPOP_UP),
           LEG_VU_DN: (VU_DN, VU_UP), LEG_VU_UP: (VU_DN, VU_UP), LEG_P3: (0.0,), LEG_U2: (HI_GAP,),
           LEG_BAND: (H_IN, H_OUT, LO_IN, LO_OUT), LEG_MOM: (MOM, -MOM_DN)}

# 상태 이름(비공개 도구 표기 그대로 — 빼기는 U+2212)
L_MM, L_M, L_0, L_P = "L−−", "L−", "L0", "L+"
P_P, P_0, P_D, P_M = "P+", "P0", "Pd", "P−"
UNKNOWN = "?"
GRID_L = (L_P, L_0, L_M, L_MM)
GRID_P = (P_P, P_0, P_D, P_M)
P_GRID = {("H", "A"): P_P, ("H", "F"): P_P, ("H", "D"): P_D,
          ("M", "A"): P_P, ("M", "F"): P_0, ("M", "D"): P_M,
          ("Lo", "A"): P_0, ("Lo", "F"): P_M, ("Lo", "D"): P_M}
# 판단 격자(4-2) — 운영자 메모의 칸 이름 그대로(예측 아님 · 예측력 검증 안 됨). 종류: up · down · box · mixed
CELLS = {
    (L_P, P_P): ("금리 상방 여지 (확인)", "up"), (L_P, P_0): ("금리 상방 관찰 (노동 선행)", "up"),
    (L_P, P_D): ("박스 (상단 시험)", "box"), (L_P, P_M): ("박스 (실질 성장형·골디락스)", "box"),
    (L_0, P_P): ("금리 상방 관찰 (물가 선행)", "up"), (L_0, P_0): ("박스", "box"),
    (L_0, P_D): ("박스 (하단 시험)", "box"), (L_0, P_M): ("금리 하방 여지 (디스인플레이션형, 2023 하반기형)", "down"),
    (L_M, P_P): ("상충: 박스·스티프닝 경계 (스태그 초기)", "mixed"), (L_M, P_0): ("금리 하방 경계", "down"),
    (L_M, P_D): ("금리 하방 경계 (되돌림 쪽)", "down"), (L_M, P_M): ("되돌림 위험 (2024 하반기형)", "down"),
    (L_MM, P_P): ("되돌림 제한 (스태그형·불 스티프닝)", "mixed"), (L_MM, P_0): ("큰 되돌림 위험", "down"),
    (L_MM, P_D): ("큰 되돌림 위험", "down"), (L_MM, P_M): ("큰 되돌림 위험 (경기침체형)", "down"),
}
LABEL = "운영자 판단 격자의 칸 이름(운영자 메모) — 예측 아님 · 예측력 검증 안 됨"
# 운영자가 미리 적어 둔 사례(4-5) — L·P만 견준다. tag는 비공개 쪽만 견주는 꼬리표(여기서는 계산하지 않는다)
EXPECTED = (
    {"case": "2022", "from": "2022-01", "to": "2022-12", "L": (L_0, L_P), "P": (P_P,)},
    {"case": "2023 하반기", "from": "2023-07", "to": "2023-12", "L": (L_0,), "P": (P_D, P_M)},
    {"case": "2024 1분기", "from": "2024-01", "to": "2024-03", "L": (L_0,), "P": (P_P, P_0)},
    {"case": "2024-08~09", "from": "2024-08", "to": "2024-09", "L": (L_M,), "P": (P_M,), "tag": "상당 부분 반영"},
    {"case": "2024-12~2025-01", "from": "2024-12", "to": "2025-01", "L": (L_0,), "P": None},
    {"case": "2026-05 이후", "from": "2026-05", "to": None, "L": None, "P": (P_P, P_D), "tag": "TP 주도"},
)

# 꼬리표 — 비공개 재생의 꼬리표 가운데 여기서 내는 것과 빼는 것
TAG_PEAK = "고점 통과"     # 비공개 도구는 "고점 통과 — 되돌림 소진 가능" — 해석 부분은 싣지 않는다(짝 테스트가 이 대응을 견준다)
PRIVATE_TAG_PEAK = "고점 통과 — 되돌림 소진 가능"
TAG_SUPPLY = "공급형(에너지)"
TAG_ENERGY_DOWN = "에너지 하락"
TAG_GOODS = "재화 주도"
TAG_SEASONAL = "계절성(1~6월)"
TAG_SHUTDOWN = "셧다운 왜곡(CPI)"
TAG_TWO_MONTH = "2개월 평균"
TAG_DELAYED = "발표 지연(셧다운 — 알려진 날은 근사·확인 필요)"
EXCLUDED_TAGS = ("상당 부분 반영", "TP 주도", "폭 좁음(트림 ≤ 3)")

_BLS, _ETA, _BEA = ("U.S. Bureau of Labor Statistics", "U.S. Employment and Training Administration",
                    "U.S. Bureau of Economic Analysis")
# FRED 권장 인용의 출처·제목(2026-11-18 시리즈 쪽 Suggested Citation 그대로). 모두 'Public Domain: Citation Requested'
SOURCES = {
    "UNRATE": (_BLS, "Unemployment Rate"),
    "LNS12300060": (_BLS, "Employment-Population Ratio - 25-54 Yrs."),
    "UNEMPLOY": (_BLS, "Unemployment Level"),
    "LNS13026638": (_BLS, "Unemployment Level - Permanent Job Losers"),
    "USPRIV": (_BLS, "All Employees, Total Private"),
    "ICSA": (_ETA, "Initial Claims"),
    "CCSA": (_ETA, "Continued Claims (Insured Unemployment)"),
    "JTSJOL": (_BLS, "Job Openings: Total Nonfarm"),
    "JTSQUR": (_BLS, "Quits: Total Nonfarm"),
    "PCEPILFE": (_BEA, "Personal Consumption Expenditures Excluding Food and Energy (Chain-Type Price Index)"),
    "CPIAUCSL": (_BLS, "Consumer Price Index for All Urban Consumers: All Items in U.S. City Average"),
    "CPILFESL": (_BLS, "Consumer Price Index for All Urban Consumers: All Items Less Food and Energy in U.S. City Average"),
    "CUSR0000SACL1E": (_BLS, "Consumer Price Index for All Urban Consumers: Commodities Less Food and Energy "
                             "Commodities in U.S. City Average"),
    "LNS13025699": (_BLS, "Unemployment Level - Job Losers Not on Layoff"),     # LNS13026638을 받지 못한 날만
}
SERIES = tuple(s for s in SOURCES if s != "LNS13025699")       # 받는 차례(13개)
PERM, PERM_ALT = "LNS13026638", "LNS13025699"

NOTICE = ("운영자의 비공개 측정 도구가 정해 둔 노동 L × 물가 P 판단 격자(문턱 고정 2026-10-14)를 FRED 현재 개정치로 이 사이트가 "
          "다시 계산한 기록이다. 발표 당시 값과 다를 수 있고, 금리나 경기를 예측하지 않는다.")
NOTICES = ["L·P 상태, 띠, 모멘텀, 칸, 꼬리표와 다리 값은 macro-regime-check가 FRED 원자료로 다시 계산한 값이다. 원 출처 기관이 "
           "내는 값이 아니다.",
           "L and P states, bands, momentum classes, cells, tags and leg values are computed by macro-regime-check from "
           "FRED data; they are not published by the source agencies."]
EXPECTED_NOTE = ("운영자가 문턱을 정하기 전에 적어 둔 사례별 기대(4-5)를 재생 결과와 L·P로만 견준다. 꼬리표 '상당 부분 반영'·'TP 주도' "
                 "대조는 이 사이트가 계산하지 않는다(정책 경로 가격·기간 프리미엄 자료를 싣지 않는다). 2024-01부터는 운영자가 "
                 "표본 밖(hold-out)으로 지정한 구간이다 — 문턱을 고정한 2026-10-14에는 이 구간의 자료도 이미 나와 있었고, 둔화 "
                 "모멘텀 문턱(−0.3 두 발표 연속)은 2024-09의 재생 결과도 보고 골랐다. 그 뒤에 나온 자료로 한 검증이 아니다. "
                 "판정 보류인 달은 기대에 들지 않은 것으로 센다. 어긋나도 문턱을 고치지 않는다.")
DEFS = {
    "L": [
        {"state": L_MM, "text": "비선형 악화 — Sahm형 ≥ 0.50, u3가 3개월 전보다 높음, 청구 다리 켜짐이 모두 성립. 한 발표로 들어간다."},
        {"state": L_M, "text": "냉각 — L−−가 아니면서 (a) Sahm형 ≥ 0.40이고 u3 상승, (b) Sahm형 ≥ 0.50이지만 해고 미확인(청구 다리가 "
                               "켜져 있지 않음 — 꺼짐 또는 ?), "
                               "(c) 청구가 아닌 악화 다리(핵심연령 고용률 Δ6 ≤ −0.3 · V/U Δ6 ≤ −0.15 · 민간고용 3개월 평균 증감 ≤ 0) "
                               "2개 이상, (d) 청구 다리 켜짐과 악화 다리 1개 이상 가운데 하나."},
        {"state": L_P, "text": "회복 전환 — L−−·L−가 아니면서 (A) u3가 직전 12개 창 최고보다 0.30%p 이상 낮고 6개월 전보다 0.20%p 이상 "
                               "낮으며 확인 다리(고용률 Δ6 ≥ +0.2 · 청구 4주 평균이 13주 전보다 낮은 상태 4주 · V/U Δ6 ≥ +0.10) "
                               "1개 이상, 또는 (B) Sahm형 ≤ 0, V/U Δ6 ≥ +0.10, 이직률 Δ6 ≥ +0.1."},
        {"state": L_0, "text": "L−−·L−·L+가 아닌 달."},
    ],
    "P": [
        {"state": P_P, "text": "띠 H에 모멘텀 A·F, 또는 띠 M에 모멘텀 A."},
        {"state": P_0, "text": "띠 M에 모멘텀 F, 또는 띠 Lo에 모멘텀 A."},
        {"state": P_D, "text": "띠 H에 모멘텀 D(높지만 둔화)."},
        {"state": P_M, "text": "띠 M에 모멘텀 D, 또는 띠 Lo에 모멘텀 F·D."},
    ],
    "band": [
        {"band": "H", "text": "근원 PCE 전년비 3개월 평균(Y3)이 3.1 초과면 들어가고 2.9 미만이 되면 나온다."},
        {"band": "M", "text": "H·Lo가 아닌 상태. Y3가 2.6~3.1 사이여도 직전 띠가 H이고 2.9 미만이 아니면 H, 직전 띠가 Lo이고 "
                              "2.7 초과가 아니면 Lo로 남는다."},
        {"band": "Lo", "text": "Y3가 2.6 미만이면 들어가고 2.7 초과가 되면 나온다."},
    ],
    "mom": [
        {"mom": "A", "text": "가속 — 근원 PCE 6개월 연율 − 전년비(a6 − y12) ≥ +0.5가 한 발표."},
        {"mom": "F", "text": "평탄 — A·D가 아닌 발표."},
        {"mom": "D", "text": "둔화 — a6 − y12 ≤ −0.3이 두 발표 연속."},
    ],
    "pgrid": [{"band": b, "mom": m, "P": P_GRID[(b, m)]} for b in ("H", "M", "Lo") for m in ("A", "F", "D")],
    "replay": [
        "기준월은 실업률이 발표된 달이다. 1960-01부터 달마다 차례로 다시 계산한다(상태 파일 없음).",
        "u3는 실업률 3개월 평균(빠진 달이 끼면 남은 2개월), Sahm형은 u3 − 직전 12개 창의 u3 최저(창 9개 이상)다.",
        "hi_gap은 u3 − 직전 12개 창의 u3 최고다. 고점 대비 하락 다리(U2)는 hi_gap ≤ −0.30이고 u3의 6개월 변화 ≤ −0.20일 때 켜진다.",
        "Δ6은 3개월 평균의 6개월 변화(고용률·V/U·이직률)다. V/U는 구인 ÷ 실업자다.",
        "L의 모든 변화는 서로 다른 두 발표 연속에서 조건이 성립해야 한다. L−−만 한 발표로 들어간다.",
        "L−·L−−에서는 u3가 3개월 전 이하, 청구 다리가 켜져 있지 않음(꺼짐 또는 ?), (c) 악화 다리 2개 이상이 아님이 두 발표 "
        "연속이면 L0으로 나온다.",
        "그 달 L을 모르면('?') L의 연속 셈은 끊긴다(상태는 이어진다). P만 모르면(대개 근원 PCE 발표 전) 칸은 '판정 보류'이지만 "
        "L의 연속 셈은 이어진다.",
        "청구 다리는 신규 청구 4주 평균이 직전 52주(그중 40개 이상) 최저의 1.25배 이상인 주가 4주 연속이고 계속 청구가 13주 "
        "전보다 높은 것이다. 그 달 마지막 주로 본다.",
        "JOLTS(V/U·이직률)는 그 기준월의 근원 PCE 발표일까지 나온 최신 달을 쓴다.",
        "알려진 날은 근원 PCE·고용·계속 청구 발표일(근사)의 늦은 쪽이다.",
    ],
    "tags": [
        {"tag": TAG_PEAK, "text": "L−·L−−에서 L0으로 나온 달에 한 번 붙는다(운영자 도구의 꼬리표 가운데 앞부분만)."},
        {"tag": TAG_SUPPLY, "text": "P+이고 CPI 전체 3개월 연율 − 근원 3개월 연율 ≥ 1.0."},
        {"tag": TAG_ENERGY_DOWN, "text": "CPI 전체 3개월 연율 − 근원 3개월 연율 ≤ −1.0(P와 무관)."},
        {"tag": TAG_GOODS, "text": "근원 상품 CPI 6개월 연율 ≥ 2.0."},
        {"tag": TAG_SEASONAL, "text": "기준월이 1~6월."},
        {"tag": TAG_SHUTDOWN, "text": "근원 CPI 3·6·12개월 창이 2025-10·2025-11·2026-04에 닿음."},
        {"tag": TAG_TWO_MONTH, "text": "u3가 빠진 달 때문에 2개월 평균."},
        {"tag": TAG_DELAYED, "text": "셧다운으로 발표가 늦은 기준월."},
        {"tag": "단일 자료(… 없음)", "text": "그 달에 값이 없는 노동 다리가 있음."},
    ],
}


# ---------- 비교(소수 6자리 반올림 뒤) ----------

def ge(x, th):
    return x is not None and round(x, 6) >= round(th, 6)


def le(x, th):
    return x is not None and round(x, 6) <= round(th, 6)


def gt(x, th):
    return x is not None and round(x, 6) > round(th, 6)


def lt(x, th):
    return x is not None and round(x, 6) < round(th, 6)


# ---------- 달 ----------

def mkey(d):
    return f"{d.year:04d}-{d.month:02d}"


def mshift(m, k):
    y, mo = int(m[:4]), int(m[5:7]) - 1 + k
    return f"{y + mo // 12:04d}-{mo % 12 + 1:02d}"


def mdiff(a, b):
    """a − b (달 수)."""
    return (int(a[:4]) - int(b[:4])) * 12 + int(a[5:7]) - int(b[5:7])


def mdate(m):
    return D(int(m[:4]), int(m[5:7]), 1)


def month_last_day(m):
    y, mo = int(m[:4]), int(m[5:7])
    return D(y, mo, calendar.monthrange(y, mo)[1])


def mrange(a, b):
    out, m = [], a
    while m <= b:
        out.append(m)
        m = mshift(m, 1)
    return out


def _roll(d):
    """주말이면 다음 평일."""
    while d.weekday() >= 5:
        d += datetime.timedelta(days=1)
    return d


def first_friday(y, m):
    d = D(y, m, 1)
    return d + datetime.timedelta(days=(4 - d.weekday()) % 7)


def release_date(kind, ref):
    """발표일 근사 — 비공개 도구의 release_date에서 이 카드가 쓰는 종류만(cps·pce·jolts·ccsa)."""
    if (kind, ref) in RELEASE_DATE_OVERRIDE:
        return RELEASE_DATE_OVERRIDE[(kind, ref)]
    if kind == "cps":                       # 고용 보고서: 다음 달 첫 금요일
        m = mshift(ref, 1)
        return first_friday(int(m[:4]), int(m[5:7]))
    if kind == "pce":                       # 다음 달 마지막 평일
        d = month_last_day(mshift(ref, 1))
        while d.weekday() >= 5:
            d -= datetime.timedelta(days=1)
        return d
    if kind == "jolts":                     # 다다음 달 7일(주말이면 다음 평일)
        m = mshift(ref, 2)
        return _roll(D(int(m[:4]), int(m[5:7]), 7))
    if kind == "ccsa":
        return ref + datetime.timedelta(days=12)
    raise ValueError(f"모르는 발표 종류 {kind}")


# ---------- 시계열 도우미 ----------

class Daily:
    """날짜순 [(date, v)] — 이분 탐색 조회."""

    def __init__(self, series):
        self.s = list(series or [])
        self.d = [x[0] for x in self.s]

    def before(self, d, tol=None):
        """d 이하 마지막 관측(tol일 안)."""
        i = bisect.bisect_right(self.d, d)
        if not i:
            return None
        x = self.s[i - 1]
        return x if tol is None or (d - x[0]).days <= tol else None


def mmap(series):
    """월간 시리즈 → {'YYYY-MM': v} (FRED 날짜는 달의 첫날)."""
    return {mkey(d): v for d, v in series or []}


def ann_rate(m, key, k):
    """k개월 연율(%). m[key]와 m[key−k]가 둘 다 있을 때만 — 그 전 달로 대신하지 않는다."""
    v, b = m.get(key), m.get(mshift(key, -k))
    if v is None or b is None or b <= 0 or v <= 0:
        return None
    return ((v / b) ** (12 / k) - 1) * 100


def y12(m, key):
    return ann_rate(m, key, 12)


def mavg(m, key, n=3, min_n=2):
    """key−n+1..key 중 있는 달의 평균 → (평균, 쓴 달 수). min_n개 미만이면 None."""
    vals = [m[k] for k in (mshift(key, -i) for i in range(n)) if m.get(k) is not None]
    if len(vals) < min_n:
        return None
    return sum(vals) / len(vals), len(vals)


def _mv(m, key, n=3, min_n=2):
    r = mavg(m, key, n, min_n)
    return r[0] if r else None


def _d(a, b):
    return None if a is None or b is None else a - b


def sahm_stats(u3map, key, window=12, min_windows=MIN_WINDOWS):
    """Sahm형: u3(key) − 직전 window개 창의 u3 최솟값(창이 min_windows개 미만이면 None). hi_gap = u3 − 그 최댓값.
    같은 값이 여럿이면 가장 늦은 달을 최저·최고 달로 적는다(비공개 도구와 같다 — fred_fetch.sahm_stats와 달리 아무 달이나)."""
    cur = u3map.get(key)
    if cur is None:
        return None
    prior = [(k, u3map[k]) for k in (mshift(key, -i) for i in range(window, 0, -1)) if u3map.get(k) is not None]
    if len(prior) < min_windows:
        return None
    lo_k, lo = prior[0]
    hi_k, hi = prior[0]
    for k, v in prior[1:]:
        if v <= lo:
            lo_k, lo = k, v
        if v >= hi:
            hi_k, hi = k, v
    return {"value": cur - lo, "low": lo, "high": hi, "hi_gap": cur - hi, "n_windows": len(prior),
            "low_month": lo_k, "high_month": hi_k, "u3": cur}


# ---------- 노동 ----------

def layoff_share(d_unemp, d_perm, min_du=MIN_DU):
    """해고 몫 = Δ12(영구 실직 3개월 평균) / Δ12(실업자 3개월 평균) — 실업자 증가가 min_du(천 명) 이상일 때만.
    → (몫, '해고형'|'진입형'|'모호') 또는 (None, None)."""
    if d_unemp is None or d_perm is None or lt(d_unemp, min_du):
        return None, None
    share = d_perm / d_unemp
    return share, ("해고형" if ge(share, LAYOFF_HI) else "진입형" if lt(share, LAYOFF_LO) else "모호")


def claims_on_flags(rows, ratio=CLAIMS_RATIO, weeks=CLAIMS_WEEKS):
    """주마다 청구 다리: ratio52 ≥ ratio가 weeks주 연속 그리고 CCSA가 13주 전보다 높음. 비율 조건은 찼는데 CCSA 비교를 할 수
    없으면 None."""
    out, run = [], 0
    for r in rows:
        q = r.get("ratio52")
        run = run + 1 if ge(q, ratio) else 0
        up = r.get("ccsa_up")
        out.append(False if run < weeks else (None if up is None else up is True))
    return out


def claims_panel(icsa, ccsa):
    """주간 청구: c4(4주 평균, 4주가 21일 간격일 때만) · ratio52(직전 52개 주 중 c4가 40개 이상일 때 그 최저 대비) ·
    CCSA 13주 상승(그 주 이하 CCSA_TOL일 안의 최근 CCSA를 그 CCSA 주의 91일 전(6일 안)과) · 청구 다리 · c4가 13주 전보다
    낮은 상태 4주. 비공개 도구의 claims_panel에서 표시만 하는 ICNSA 전년비를 뺀 것."""
    wk = list(icsa or [])
    cc = Daily(ccsa)
    rows = []
    for i, (d, v) in enumerate(wk):
        c4 = sum(x[1] for x in wk[i - 3:i + 1]) / 4 if i >= 3 and (d - wk[i - 3][0]).days == 21 else None
        rows.append({"week": d, "icsa": v, "c4": c4, "ratio52": None, "ccsa_up": None, "c4_13": None})
    c4s = [r["c4"] for r in rows]
    for i, r in enumerate(rows):
        d = r["week"]
        if r["c4"] is not None:
            prior = [x for x in c4s[max(0, i - 52):i] if x is not None]
            if len(prior) >= 40 and min(prior) > 0:
                r["ratio52"] = r["c4"] / min(prior)
            if i >= 13 and (d - rows[i - 13]["week"]).days == 91:
                r["c4_13"] = c4s[i - 13]
        a = cc.before(d, CCSA_TOL)
        b = cc.before(a[0] - datetime.timedelta(days=DAYS_3M), 6) if a else None
        if a and b:
            r["ccsa_up"], r["ccsa_week"] = a[1] > b[1], a[0]
    run = 0
    for r, on in zip(rows, claims_on_flags(rows)):
        r["claims_on"] = on
        down = r["c4"] is not None and r["c4_13"] is not None and r["c4"] < r["c4_13"]
        run = run + 1 if down else 0
        r["c4_down13_4w"] = run >= 4
    return rows


def jolts_month(jmonths, t):
    """기준월 t에 쓸 JOLTS 달 — t 이하이면서 t의 근원 PCE 발표일(근사)까지 나온 최신 달(보통 t−1)."""
    cut = release_date("pce", t)
    i = bisect.bisect_right(jmonths, t)
    while i:
        m = jmonths[i - 1]
        if release_date("jolts", m) <= cut:
            return m
        i -= 1
    return None


def perm_sid(data):
    """영구 실직자 시리즈 — LNS13026638, 없으면 LNS13025699(비공개 Ctx.perm_sid와 같다)."""
    return PERM if data.get(PERM) else (PERM_ALT if data.get(PERM_ALT) else None)


def labor_panel(data, since=SINCE):
    """기준월(실업률이 발표된 달)마다 노동 다리. u3는 결측월도 있는 달로(2개월 평균) 채운다. data = {ID: [(date, v)]}.
    UNRATE가 없으면 빈 행. 다리에 쓰지 않는 표시 칸(SAHMREALTIME·NROU·JTSLDR·ICNSA)은 계산하지 않는다."""
    has = lambda sid: bool(data.get(sid))
    un = mmap(data.get("UNRATE"))
    u3, u3n = {}, {}
    if un:
        for m in mrange(min(un), max(un)):
            r = mavg(un, m)
            if r:
                u3[m], u3n[m] = r
    epop, unemp = mmap(data.get("LNS12300060")), mmap(data.get("UNEMPLOY"))
    psid = perm_sid(data)
    perm = mmap(data.get(psid)) if psid else {}
    priv = mmap(data.get("USPRIV"))
    jol, quits = mmap(data.get("JTSJOL")), mmap(data.get("JTSQUR"))
    vu = {m: jol[m] / unemp[m] for m in jol if unemp.get(m)}
    jmonths = sorted(jol)
    claims_m = {}
    for r in claims_panel(data.get("ICSA"), data.get("CCSA")):
        claims_m[mkey(r["week"])] = r
    absent = [name for name, ok in (("고용률", bool(epop)), ("V/U", bool(vu)), ("민간고용", bool(priv)),
                                    ("청구", has("ICSA") and has("CCSA")), ("해고 몫", bool(perm and unemp)))
              if not ok]
    rows = []
    start = max(LABOR_START, mkey(since))
    for t in sorted(un):
        if t < start:
            continue
        st = sahm_stats(u3, t) or {}
        g = {"month": t, "unrate": un[t], "u3": u3.get(t), "u3_n": u3n.get(t), "sahm": st.get("value"),
             "low": st.get("low"), "high": st.get("high"), "hi_gap": st.get("hi_gap"),
             "n_windows": st.get("n_windows"), "low_month": st.get("low_month"), "high_month": st.get("high_month")}
        d3 = _d(u3.get(t), u3.get(mshift(t, -3)))
        g["rising3"] = None if d3 is None else gt(d3, 0)
        g["d6u3"] = _d(u3.get(t), u3.get(mshift(t, -6)))
        g["epop3_d6"] = _d(_mv(epop, t), _mv(epop, mshift(t, -6)))
        jm = jolts_month(jmonths, t) if jmonths else None
        g["jolts_month"] = jm
        g["vu3"] = _mv(vu, jm) if jm else None
        g["vu3_d6"] = _d(g["vu3"], _mv(vu, mshift(jm, -6))) if jm else None
        g["quits3_d6"] = _d(_mv(quits, jm), _mv(quits, mshift(jm, -6))) if jm else None
        diffs = [priv[k] - priv[mshift(k, -1)] for k in (mshift(t, -i) for i in range(3))
                 if k in priv and mshift(k, -1) in priv]
        g["p3"] = sum(diffs) / len(diffs) if len(diffs) >= 2 else None
        du = _d(_mv(unemp, t), _mv(unemp, mshift(t, -12)))
        dp = _d(_mv(perm, t), _mv(perm, mshift(t, -12))) if perm else None
        g["d_unemp12"], g["d_perm12"] = du, dp
        g["layoff_share"], g["layoff_class"] = layoff_share(du, dp)
        c = claims_m.get(t)
        g["claims_week"] = c["week"] if c else None
        g["claims_on"] = c["claims_on"] if c else None
        g["ratio52"] = c["ratio52"] if c else None
        g["c4_down13_4w"] = c["c4_down13_4w"] if c else None
        month_gap = [name for name, v in (("고용률", g["epop3_d6"]), ("V/U", g["vu3_d6"]), ("민간고용", g["p3"]),
                                          ("청구", g["ratio52"]), ("해고 몫", None if du is None else dp))
                     if v is None and name not in absent]
        g["absent"] = absent + month_gap
        rows.append(g)
    return {"rows": rows, "u3": u3, "u3n": u3n, "vu": vu, "perm_sid": psid, "absent": absent}


# ---------- 물가 ----------

def infl_rows(m, cpi=False):
    """{달: {y12, a3, a6, Y3, Y3_n, mom, seasonal, shutdown}} — 지수가 있는 달마다. shutdown(CPI만): a3·a6·y12의 창(기준 달~그 달)에
    SHUTDOWN_CPI 달이 들면 그 측정 이름."""
    y = {t: v for t, v in ((t, y12(m, t)) for t in m) if v is not None}
    out = {}
    for t in sorted(m):
        r = {"y12": y.get(t), "a3": ann_rate(m, t, 3), "a6": ann_rate(m, t, 6)}
        y3 = mavg(y, t)
        r["Y3"], r["Y3_n"] = y3 if y3 else (None, None)
        r["mom"] = _d(r["a6"], r["y12"])
        r["seasonal"] = int(t[5:7]) <= 6
        r["shutdown"] = ([k for k, n in (("a3", 3), ("a6", 6), ("y12", 12))
                          if any(mshift(t, -n) <= s <= t for s in SHUTDOWN_CPI)] if cpi else [])
        out[t] = r
    return out


def band_step(prev, y, h_in=H_IN, h_out=H_OUT, lo_in=LO_IN, lo_out=LO_OUT):
    """수준 띠(히스테리시스): H는 h_in 초과로 들어가 h_out 미만에서 나온다, Lo는 lo_in 미만으로 들어가 lo_out 초과에서 나온다."""
    if y is None:
        return None
    if prev == "H" and not lt(y, h_out):
        return "H"
    if prev == "Lo" and not gt(y, lo_out):
        return "Lo"
    if gt(y, h_in):
        return "H"
    if lt(y, lo_in):
        return "Lo"
    return "M"


def bands(values):
    """Y3 열 → 띠 열. 빈 값은 None이고 직전 상태를 그대로 넘긴다."""
    out, state = [], None
    for v in values:
        b = band_step(state, v)
        out.append(b)
        if b is not None:
            state = b
    return out


def mom_class(seq, up=(MOM, MOM_N), down=(MOM_DN, MOM_DN_N)):
    """seq = 모멘텀(a6 − y12) 열(마지막이 그 달). A: 마지막 up[1]개 발표가 모두 ≥ +up[0], D: 마지막 down[1]개가 모두 ≤ −down[0],
    F: 그 밖. 그 달 값이 없으면 None. 그 달이 한쪽 문턱을 넘었는데 앞 발표가 없어 가를 수 없으면 None."""
    seq = list(seq)
    cur = seq[-1] if seq else None
    if cur is None:
        return None
    for (th, n), hit, label in ((up, lambda v, th: ge(v, th), "A"), (down, lambda v, th: le(v, -th), "D")):
        if hit(cur, th):
            need = seq[-n:]
            if len(need) < n or any(v is None for v in need):
                return None
            return label if all(hit(v, th) for v in need) else "F"
    return "F"


def p_state(band, mom):
    """4-1 물가 격자(9칸). 하나라도 없으면 '?'."""
    return P_GRID.get((band, mom), UNKNOWN)


def pce_states(rows):
    """infl_rows(근원 PCE)에 band·mom_class·P를 더한다(처음 달부터 차례로)."""
    months = sorted(rows)
    bl = bands([rows[t]["Y3"] for t in months])
    moms = [rows[t]["mom"] for t in months]
    need = max(MOM_N, MOM_DN_N)
    for i, t in enumerate(months):
        rows[t]["band"] = bl[i]
        rows[t]["mom_class"] = mom_class(moms[max(0, i - need + 1):i + 1])
        rows[t]["P"] = p_state(rows[t]["band"], rows[t]["mom_class"])
    return rows


def infl_tags(t, prow, cpi_all, cpi_core, goods_m):
    """그 달의 물가 꼬리표 — 비공개 infl_tags에서 '폭 좁음(트림 ≤ 3)'(트림 평균 자료)을 뺀 것.
    cpi_all·cpi_core = infl_rows(…, cpi=True), goods_m = 근원 상품 CPI {달: 지수}."""
    tags = []
    hc = _d(cpi_all.get(t, {}).get("a3"), cpi_core.get(t, {}).get("a3"))
    goods = ann_rate(goods_m, t, 6)
    if prow.get("P") == P_P and ge(hc, SUPPLY_HC):
        tags.append(TAG_SUPPLY)
    if le(hc, -SUPPLY_HC):
        tags.append(TAG_ENERGY_DOWN)
    if ge(goods, GOODS_LED):
        tags.append(TAG_GOODS)
    if prow.get("seasonal"):
        tags.append(TAG_SEASONAL)
    if cpi_core.get(t, {}).get("shutdown"):
        tags.append(TAG_SHUTDOWN)
    return tags


# ---------- 판단 재생 ----------

def layoff_confirmed(g):
    """L−−의 '해고 확인' = 청구 다리 켜짐(고정 2026-10-14)."""
    return g.get("claims_on") is True


def det_legs(g):
    """청구가 아닌 악화 다리: 핵심연령 고용률 Δ6 ≤ −0.3, V/U Δ6 ≤ −0.15, 민간고용 3개월 ≤ 0."""
    return [le(g.get("epop3_d6"), EPOP_DN), le(g.get("vu3_d6"), VU_DN), le(g.get("p3"), 0.0)]


def l_raw(g):
    """4-1 노동 상태(그 달 조건만, 히스테리시스 전). 실업률 다리가 없으면 '?'. 선택 다리가 없으면 거짓으로 센다."""
    s, r = g.get("sahm"), g.get("rising3")
    if s is None:
        return UNKNOWN
    lay = layoff_confirmed(g)
    if ge(s, SAHM_ON) and lay:
        if r is True:
            return L_MM
        if r is None:
            return UNKNOWN
    n_det = sum(det_legs(g))
    claims = g.get("claims_on") is True
    cond_a = False if not ge(s, SAHM_WATCH) else r
    if cond_a is True or (ge(s, SAHM_ON) and not lay) or n_det >= 2 or (claims and n_det >= 1):
        return L_M
    if cond_a is None:
        return UNKNOWN
    u2 = le(g.get("hi_gap"), HI_GAP) and le(g.get("d6u3"), D6U)
    confirm = ge(g.get("epop3_d6"), EPOP_UP) or g.get("c4_down13_4w") is True or ge(g.get("vu3_d6"), VU_UP)
    reheat = le(s, 0.0) and ge(g.get("vu3_d6"), VU_UP) and ge(g.get("quits3_d6"), QUITS_UP)
    if (u2 and confirm) or reheat:
        return L_P
    return L_0


RAW_RULES = ("L−−", "a", "b", "c", "d", "A", "B")


def raw_rules(g):
    """그 달 조건만의 L(l_raw)을 만든 절 — 화면이 '왜 이 상태인가'를 적는 데만 쓴다(공개만, 판단에 쓰지 않는다).
    l_raw와 같은 갈래를 같은 비교로 따라간다: L−−면 ['L−−'], L−면 맞은 절 (a)~(d), L+면 (A)·(B), L0·'?'면 []."""
    raw = l_raw(g)
    s, r = g.get("sahm"), g.get("rising3")
    if raw == L_MM:
        return ["L−−"]
    if raw == L_M:
        lay, n_det = layoff_confirmed(g), sum(det_legs(g))
        return [k for k, on in (("a", ge(s, SAHM_WATCH) and r is True), ("b", ge(s, SAHM_ON) and not lay),
                                ("c", n_det >= 2), ("d", g.get("claims_on") is True and n_det >= 1)) if on]
    if raw == L_P:
        u2 = le(g.get("hi_gap"), HI_GAP) and le(g.get("d6u3"), D6U)
        confirm = ge(g.get("epop3_d6"), EPOP_UP) or g.get("c4_down13_4w") is True or ge(g.get("vu3_d6"), VU_UP)
        reheat = le(s, 0.0) and ge(g.get("vu3_d6"), VU_UP) and ge(g.get("quits3_d6"), QUITS_UP)
        return [k for k, on in (("A", u2 and confirm), ("B", reheat)) if on]
    return []


def breadth_on(g):
    """4-1 (c): 청구가 아닌 악화 다리 2개 이상."""
    return sum(det_legs(g)) >= 2


def exit_ok(g):
    """이탈 조건: u3가 3개월 전 이하 그리고 청구 다리가 켜져 있지 않음(꺼짐 또는 ?) 그리고 (c) 꺼짐. 실업률 상승 여부를 모르면
    None."""
    r = g.get("rising3")
    if r is None:
        return None
    return r is False and g.get("claims_on") is not True and not breadth_on(g)


def replay_l(legs):
    """기준월 순서로 노동 상태를 결정적으로 재생(4-4). → [{L, raw, exit, tags, state}]"""
    state, prev_raw, prev_exit = L_0, None, False
    out = []
    for g in legs:
        raw, ex = l_raw(g), exit_ok(g)
        tags = []
        if raw == UNKNOWN:
            out.append({"L": UNKNOWN, "raw": raw, "exit": ex, "tags": tags, "state": state})
            prev_raw, prev_exit = None, False
            continue
        if state in (L_M, L_MM):
            if ex is True and prev_exit:
                state = L_0
                tags.append(TAG_PEAK)
            elif state == L_M and raw == L_MM:
                state = L_MM
            elif state == L_MM and raw == L_M and prev_raw == L_M:
                state = L_M
        else:
            if raw == L_MM:
                state = L_MM
            elif raw == L_M and prev_raw in (L_M, L_MM) and ex is not True:
                state = L_M
            elif raw in (L_0, L_P) and raw != state and prev_raw == raw:
                state = raw
        out.append({"L": state, "raw": raw, "exit": ex, "tags": tags, "state": state})
        prev_raw, prev_exit = raw, ex is True
    return out


def cell(L, P):
    """4-2 격자 → (칸 이름, 종류). '?'(또는 모르는 값)가 있으면 ('판정 보류(<다리>)', 'hold')."""
    miss = ([] if L in (L_MM, L_M, L_0, L_P) else ["노동"]) + ([] if P in (P_P, P_0, P_D, P_M) else ["물가"])
    if miss:
        return f"판정 보류({'·'.join(miss)})", "hold"
    return CELLS[(L, P)]


def replay(data, since=SINCE):
    """노동 다리를 1960-01부터 데워 기준월마다 L·P·칸·꼬리표. 행은 REPLAY_START(1990-01)부터 — 비공개 replay와 같다.
    → {"rows": [...], "legs": {달: 노동 다리}, "pce": {달: 근원 PCE 행}}"""
    legs = labor_panel(data, since)["rows"]
    pce = pce_states(infl_rows(mmap(data.get("PCEPILFE")))) if data.get("PCEPILFE") else {}
    cpi_all = infl_rows(mmap(data.get("CPIAUCSL")), cpi=True)
    cpi_core = infl_rows(mmap(data.get("CPILFESL")), cpi=True)
    goods_m = mmap(data.get("CUSR0000SACL1E"))
    ls = replay_l(legs)
    rows = []
    start = max(REPLAY_START, mkey(since))
    for g, l in zip(legs, ls):
        t = g["month"]
        if t < start:
            continue
        p = pce.get(t, {})
        P = p.get("P", UNKNOWN) or UNKNOWN
        name, kind = cell(l["L"], P)
        known = max(release_date("pce", t), release_date("cps", t),
                    release_date("ccsa", g["claims_week"]) if g.get("claims_week") else D(1900, 1, 1))
        tags = list(l["tags"])
        if p:
            tags += infl_tags(t, p, cpi_all, cpi_core, goods_m)
        if g.get("u3_n") == 2:
            tags.append(TAG_TWO_MONTH)
        if t in DELAYED_REFS:
            tags.append(TAG_DELAYED)
        if g.get("absent"):
            tags.append("단일 자료(" + "·".join(g["absent"]) + " 없음)")
        rows.append({"month": t, "known": known, "L": l["L"], "L_raw": l["raw"], "absent": g.get("absent") or [],
                     "P": P, "band": p.get("band"), "mom_class": p.get("mom_class"), "cell": name, "kind": kind,
                     "tags": tags})
    return {"rows": rows, "legs": {g["month"]: g for g in legs}, "pce": pce}


def leg_list(g, p):
    """지금 칸의 다리마다 (이름, 값, 기준월, 충족) — 비공개 leg_list와 같은 차례·이름·값. 해고 몫·띠·모멘텀의 충족 칸은 글자
    (해고형/진입형/모호/'-' · H/M/Lo · A/F/D)."""
    def b(x):
        return None if x is None else bool(x)
    s, t = g.get("sahm"), g["month"]
    jm = g.get("jolts_month") or t
    return [(LEG_SAHM_ON, s, t, None if s is None else ge(s, SAHM_ON)),
            (LEG_SAHM_WATCH, s, t, None if s is None else ge(s, SAHM_WATCH)),
            (LEG_RISING, g.get("rising3"), t, b(g.get("rising3"))),
            (LEG_CLAIMS, g.get("ratio52"), mkey(g["claims_week"]) if g.get("claims_week") else t, b(g.get("claims_on"))),
            (LEG_LAYOFF, g.get("layoff_share"), t, g.get("layoff_class") or "-"),
            (LEG_EPOP_DN, g.get("epop3_d6"), t, None if g.get("epop3_d6") is None else le(g["epop3_d6"], EPOP_DN)),
            (LEG_VU_DN, g.get("vu3_d6"), jm, None if g.get("vu3_d6") is None else le(g["vu3_d6"], VU_DN)),
            (LEG_P3, g.get("p3"), t, None if g.get("p3") is None else le(g["p3"], 0.0)),
            (LEG_U2, g.get("hi_gap"), t,
             None if g.get("hi_gap") is None or g.get("d6u3") is None
             else le(g["hi_gap"], HI_GAP) and le(g["d6u3"], D6U)),
            (LEG_EPOP_UP, g.get("epop3_d6"), t, None if g.get("epop3_d6") is None else ge(g["epop3_d6"], EPOP_UP)),
            (LEG_VU_UP, g.get("vu3_d6"), jm, None if g.get("vu3_d6") is None else ge(g["vu3_d6"], VU_UP)),
            (LEG_BAND, p.get("Y3"), t, p.get("band")),
            (LEG_MOM, p.get("mom"), t, p.get("mom_class"))]


def expected_check(rows, expected=EXPECTED):
    """4-5 사례: 재생 칸을 기대와 나란히(L·P만). 어긋나면 적기만 한다."""
    by = {r["month"]: r for r in rows}
    out = []
    for e in expected:
        ms = [m for m in sorted(by) if m >= e["from"] and (e["to"] is None or m <= e["to"])]
        items = []
        for m in ms:
            r = by[m]
            ok = (e["L"] is None or r["L"] in e["L"]) and (e["P"] is None or r["P"] in e["P"])
            items.append({"month": m, "L": r["L"], "P": r["P"], "cell": r["cell"], "match": ok})
        out.append({"case": e["case"], "from": e["from"], "to": e["to"], "holdout": e["from"] >= HOLDOUT,
                    "want_L": list(e["L"]) if e["L"] else None, "want_P": list(e["P"]) if e["P"] else None,
                    "tag_unchecked": e.get("tag"), "n": len(items), "matched": sum(i["match"] for i in items),
                    "items": items})
    return out


def decision(rep):
    """비공개 sec_decision의 고르기 — current = 칸이 보류가 아닌 마지막 기준월(없으면 마지막 달), latest = 마지막 달
    (current와 같은 달이면 None). current의 legs는 leg_list의 날 것 그대로(반올림 전)."""
    rows = rep["rows"]
    if not rows:
        return None, None
    known = [r for r in rows if r["kind"] != "hold"]
    cur = known[-1] if known else rows[-1]
    g = rep["legs"][cur["month"]]
    p = rep["pce"].get(cur["month"], {})
    current = {**cur, "legs": leg_list(g, p),
               "inflation": {k: p.get(k) for k in ("y12", "a3", "a6", "mom", "Y3", "Y3_n")}}
    last = rows[-1]
    return current, (None if last["month"] == cur["month"] else last)


def compute(data, asof, since=SINCE):
    """메모리의 시리즈(data = {ID: [(date, float)]})로 계산 — 네트워크·파일 없음. asof 이후 관측은 버린다(비공개 load_series와
    같다). → {"rows", "legs", "pce", "current", "latest", "history", "expected"} — 행·다리는 반올림 전 값."""
    data = {sid: [x for x in (s or []) if x[0] <= asof] for sid, s in (data or {}).items()}
    rep = replay(data, since)
    current, latest = decision(rep)
    rep.update(current=current, latest=latest, history=[r for r in rep["rows"] if r["month"] >= HISTORY_FROM],
               expected=expected_check(rep["rows"]))
    return rep


# ---------- 공개 파일 ----------

def _cmp(a, b):
    return (a > b) - (a < b)


def num(v, ths=()):
    """저장 값 — 소수 넷째 자리까지. 다만 넷째 자리 반올림이 어느 문턱과의 비교(소수 6자리 반올림 뒤)를 뒤집거나 문턱과 같게
    보이게 하면 여섯째 자리까지 둔다(문턱 옆 값이 반대쪽처럼 보이지 않게). 참/거짓·None은 그대로."""
    if v is None or isinstance(v, bool):
        return v
    r4 = round(v, 4) + 0.0
    for th in ths:
        if _cmp(round(r4, 6), round(th, 6)) != _cmp(round(v, 6), round(th, 6)):
            return round(v, 6) + 0.0
    return r4


def _iso(d):
    return d.isoformat() if d else None


def _row_out(r):
    return {"month": r["month"], "known": _iso(r["known"]), "L": r["L"], "L_raw": r["L_raw"], "P": r["P"],
            "band": r["band"], "mom_class": r["mom_class"], "cell": r["cell"], "kind": r["kind"], "tags": list(r["tags"])}


def citation(sid, date):
    """FRED 권장 인용 — render_public.citation과 같은 꼴(출처, 제목 [ID], retrieved from FRED, …; URL, 날짜)."""
    d = datetime.date.fromisoformat(date)
    src, title = SOURCES[sid]
    return (f"{src}, {title} [{sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; "
            f"{rp.FRED_URL.format(sid)}, {rp._MONTHS[d.month - 1]} {d.day}, {d.year}.")


def used_series(data):
    """이번 계산에 쓴 시리즈 — 13개(영구 실직자는 받은 쪽)."""
    p = perm_sid(data) or PERM
    return [p if sid == PERM else sid for sid in SERIES]


def build(data, info, now):
    """lp.json 내용. info = {ID: 'net'|'cache'|'missing'} (fetch_all), now = UTC datetime."""
    asof = now.date()
    rep = compute(data, asof)
    cur, lat = rep["current"], rep["latest"]
    current = None
    if cur:
        p = cur["inflation"]
        g = rep["legs"][cur["month"]]
        current = {**_row_out(cur),
                   "legs": [{"name": n, "value": num(v, LEG_THS.get(n, ())), "month": m, "on": on}
                            for n, v, m, on in cur["legs"]],
                   "inflation": {"y12": num(p["y12"]), "a3": num(p["a3"]), "a6": num(p["a6"]),
                                 "mom": num(p["mom"], LEG_THS[LEG_MOM]), "Y3": num(p["Y3"], LEG_THS[LEG_BAND]),
                                 "Y3_n": p["Y3_n"]},
                   "raw_rules": raw_rules(g), "d6u3": num(g.get("d6u3"), (D6U,))}
    latest = None if not lat else {"month": lat["month"], "known": _iso(lat["known"]), "L": lat["L"], "P": lat["P"],
                                   "cell": lat["cell"], "kind": lat["kind"], "tags": list(lat["tags"])}
    expected = []
    for e in rep["expected"]:
        want = (f"노동 {' 또는 '.join(e['want_L']) if e['want_L'] else '(정하지 않음)'} · "
                f"물가 {' 또는 '.join(e['want_P']) if e['want_P'] else '(정하지 않음)'}")
        expected.append({"case": e["case"], "want": want, "from": e["from"], "to": e["to"], "holdout": e["holdout"],
                         "n": e["n"], "matched": e["matched"], "items": e["items"], "want_L": e["want_L"],
                         "want_P": e["want_P"], "tag_unchecked": e["tag_unchecked"]})
    used = used_series(data)
    listed = []                                     # 대체 시리즈를 쓴 날은 받지 못한 원 시리즈도 그 자리에 적는다
    for sid in used:
        listed += [PERM, PERM_ALT] if sid == PERM_ALT else [sid]
    series = [{"series": sid, "title": SOURCES[sid][1],
               "last": _iso(max((d for d, _ in data.get(sid) or [] if d <= asof), default=None)),
               "fetched": info.get(sid, "missing")} for sid in listed]
    sources = [{"series": sid, "url": rp.FRED_URL.format(sid), "citation": citation(sid, asof.isoformat()),
                "citation_required": sid in rp.CITATION_REQUIRED} for sid in used]     # ledger_build.sources()와 같은 규칙
    return {
        "schema": SCHEMA, "generated_at": now.isoformat(timespec="seconds"), "asof": asof.isoformat(),
        "notice": NOTICE, "label": LABEL, "fixed": FIXED, "holdout_from": HOLDOUT, "constants": dict(CONSTANTS),
        "grid": {"L": list(GRID_L), "P": list(GRID_P),
                 "cells": [[{"L": L, "P": P, "name": CELLS[(L, P)][0], "kind": CELLS[(L, P)][1]} for P in GRID_P]
                           for L in GRID_L]},
        "defs": json.loads(json.dumps(DEFS, ensure_ascii=False)),
        "current": current, "latest": latest, "history": [_row_out(r) for r in rep["history"]],
        "expected": expected, "expected_note": EXPECTED_NOTE, "excluded_tags": list(EXCLUDED_TAGS),
        "series": series, "sources": sources, "notices": list(NOTICES),
    }


# ---------- 수신 ----------

def _mtime_day(path):
    try:
        return datetime.datetime.fromtimestamp(os.path.getmtime(path), tz=datetime.timezone.utc).date()
    except OSError:
        return None


def _reused(reuse, sid, today, cache=None):
    """규칙 점검이 같은 실행에서 받아 둔 원자료(<reuse>/<ID>.csv, 오늘(UTC) 쓴 파일)가 있으면 그 시계열. 읽으면 이 카드의
    캐시(<cache>/<ID>.csv)에도 옮겨 둔다(--offline 확인용 — 캐시는 덤이라 실패해도 그만)."""
    if not reuse:
        return None
    path = ff.cache_path(reuse, sid)
    if _mtime_day(path) != today:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    series = ff.parse_csv(text)
    if series and cache and os.path.abspath(cache) != os.path.abspath(reuse):
        try:
            os.makedirs(cache, exist_ok=True)
            _atomic_write(ff.cache_path(cache, sid), text)
        except OSError:
            pass
    return series or None


def _usable(series, today):
    """오늘 이하이고 숫자가 유한한 관측만(FRED CSV의 'NaN'·'inf' 꼴은 float()가 받아 버리므로 여기서 거른다)."""
    return [x for x in series or [] if x[0] <= today and isinstance(x[1], (int, float)) and math.isfinite(x[1])]


def fetch_all(cache, reuse, offline, budget, today, clock=time.monotonic, loader=None):
    """→ (data {ID: 시계열}, info {ID: 'net'|'cache'|'missing'}, missing [받지 못한 이름]).
    온라인에서 캐시로 대신한 시리즈는 받지 못한 것으로 센다. 영구 실직자는 LNS13026638을 받지 못했을 때만 LNS13025699를 받고,
    둘 다 없으면 'LNS13026638/LNS13025699' 하나로 센다."""
    loader = loader or ff.load
    data, info, deadline = {}, {}, clock() + budget

    def one(sid):
        if offline:
            timeout = TIMEOUT
        else:
            s = _reused(reuse, sid, today, cache)
            s = _usable(s, today)
            if s:
                return s, "net"
            left = deadline - clock()
            if left <= 0:
                return None, "missing"
            timeout = max(0.1, min(TIMEOUT, left))
        try:
            s, src = loader(sid, cache, offline=offline, timeout=timeout)
        except Exception:
            return None, "missing"
        s = _usable(s, today)
        if not s or (src != "net" and not offline):
            return None, "missing"
        return s, ("cache" if offline else "net")

    missing = []
    for sid in SERIES:
        s, how = one(sid)
        info[sid] = how
        if s:
            data[sid] = s
            continue
        if sid == PERM:                                 # 영구 실직자: 대안 시리즈를 받아 본다(둘이 한 다리)
            s, how = one(PERM_ALT)
            info[PERM_ALT] = how
            if s:
                data[PERM_ALT] = s
                continue
            missing.append(f"{PERM}/{PERM_ALT}")
        else:
            missing.append(sid)
    return data, info, missing


# ---------- 쓰기 ----------

def _atomic_write(path, text):
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def dumps(content):
    """쓰는 꼴 — 한 줄 JSON. NaN·inf가 섞이면 ValueError(엄격한 JSON만 쓴다 — 화면의 JSON.parse가 받지 못한다)."""
    return json.dumps(content, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _strict(x):
    raise ValueError(f"JSON 밖의 값 {x}")


def differs(out, content):
    """지금 파일과 generated_at 말고 다르면 참(파일이 없거나 깨졌거나 NaN 같은 JSON 밖의 값이 있어도 참)."""
    try:
        with open(os.path.join(out, FILE), encoding="utf-8") as f:
            old = json.load(f, parse_constant=_strict)
    except (OSError, ValueError):
        return True
    strip = lambda d: {k: v for k, v in d.items() if k != "generated_at"} if isinstance(d, dict) else d
    return strip(old) != strip(json.loads(dumps(content)))


def write(out, content):
    text = dumps(content)                       # 쓰기 전에 만든다 — 만들 수 없으면 파일을 건드리지 않는다
    os.makedirs(out, exist_ok=True)
    _atomic_write(os.path.join(out, FILE), text)


def annotate(text):
    print("::warning::" + text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A"), flush=True)


def main(argv=None, now=None, clock=time.monotonic, loader=None):
    ap = argparse.ArgumentParser(description="FRED 공개 통계 → 노동 L × 물가 P 판단 격자 참고 자료(<out>/lp.json)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    ap.add_argument("--offline", action="store_true", help="요청하지 않고 캐시만 읽는다(로컬 확인용)")
    ap.add_argument("--cache", default=DEFAULT_CACHE, help="원자료 캐시 폴더 (기본: 저장소의 .work/lp/)")
    ap.add_argument("--reuse", default=DEFAULT_REUSE,
                    help="규칙 점검이 같은 실행에서 받아 둔 원자료 폴더 — 오늘(UTC) 쓴 파일만 읽는다 (기본: .work/fred/)")
    ap.add_argument("--budget", type=float, default=BUDGET, help=f"수신 전체 초 (기본 {BUDGET})")
    a = ap.parse_args(argv)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    out = os.path.abspath(a.out)
    data, info, missing = fetch_all(os.path.abspath(a.cache), a.reuse and os.path.abspath(a.reuse), a.offline,
                                    a.budget, today, clock, loader)
    if missing:
        annotate(f"[lp_fetch] 받지 못한 시리즈: {', '.join(missing)} — 빠진 다리로 계산하지 않고 {FILE}을 그대로 둔다")
        return 0
    try:
        content = build(data, info, now)
        dumps(content)                          # NaN·inf가 섞이면 여기서 ValueError — 깨진 JSON을 쓰지 않는다
    except Exception as e:                      # 계산 쪽 뜻밖의 오류 — 어제 파일을 그대로 둔다
        annotate(f"[lp_fetch] 계산 오류({type(e).__name__}) — {FILE}을 그대로 둔다")
        return 0
    if not differs(out, content):
        print(f"[lp_fetch] {FILE} 내용이 같아 다시 쓰지 않음")
        return 0
    try:
        write(out, content)
    except OSError as e:
        print(f"[lp_fetch] {FILE}을 쓰지 못함: {type(e).__name__}", file=sys.stderr)
        return 1
    cur = content["current"]
    print(f"[lp_fetch] {FILE} 씀 — 지금 칸 " + (f"{cur['month']} {cur['L']} × {cur['P']}" if cur else "없음"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
