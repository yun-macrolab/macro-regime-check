/* 판단 격자 L × P 참고 — data/lp.json(scripts/lp_fetch.py)을 그린다 (2026-11-18 운영자 결정 '4번 L×P 격자 카드 시작해').
   운영자의 비공개 측정 도구(노동 상태 L × 물가 상태 P, 16칸)를 공개 통계(FRED 현재 개정치)로 이 사이트가 따로 다시 계산한 것이다.
   이 사이트의 규칙 점검에 쓰지 않고, 금리를 예측하지 않는다. 칸 이름 16개는 운영자 메모라 늘 LABEL 아래에 둔다(시나리오 이름표 A~D와
   같은 선례 — index.html '시나리오 이름표와 해석 구절'). 이 카드에서 방향을 말하는 글은 그 칸 이름 16개뿐이다 — 운영자가 미리 적어 둔
   기대는 상태 이름으로만 오고, 꼬리표 '고점 통과'는 비공개 도구의 꼬리표('고점 통과 — 되돌림 소진 가능')에서 해석 부분을 뺀 앞부분이다
   (자료에 긴 꼴이 와도 앞부분만 싣는다). 칸 종류(운영자 메모)는 칸 왼쪽 색 띠로만 가르고 방향 낱말로 풀지 않는다 — 노동과 물가가
   엇갈리는 두 칸(종류 mixed)만 격자 아래 줄에 칸 자리로 적는다.
   자리: 첫 화면(전체)의 '주제별 점검' 절(#rules-wrap) 바로 앞의 #lp-ref — 그 절 안의 규칙 상태 고르기와 규칙 목록 사이에 두지 않고,
   13개 규칙 뒤로 묻지도 않는다. 다리 13개의 값 표는 접어 두고 그 달 조건만의 노동 상태를 만든 절 한 줄만 늘 보인다. index.html의 el() · link()를 쓴다(부를 때 이미 정의돼 있다).
   글자는 전부 el()의 텍스트로만 넣는다. 바깥 요청은 없다.
   자료는 꼴을 하나하나 본다(schema 1 · 정해 둔 값 · 달 YYYY-MM · 날 YYYY-MM-DD · 유한한 숫자). 칸 이름은 운영자 표(CELLS)와 글자까지
   같아야 하고(그 칸의 L · P와 짝이 맞게), 물가 P는 띠 × 모멘텀(P_GRID)과 맞아야 한다. 꼴이 어긋난 항목은 건너뛰고, 파일 꼴이 어긋나면
   (schema · 날짜 · 문턱 · 격자) 아무것도 그리지 않는다(false — index.html이 절을 숨긴 채 둔다).
   꼬리표는 자료에 있어도 EXCLUDED(이 사이트가 싣지 않는 재료가 필요한 셋)와 밸류 크기 꼬리표를 빼고 싣는다. 자료 파일의 글에 예측·권유
   낱말(BANNED_WORDS)이 있으면 그 글은 싣지 않는다.
   숫자는 문턱 바로 옆에서 반대쪽처럼 보이지 않게 자리를 늘린다(near — 반올림한 숫자가 문턱과 견준 쪽이 실제 값과 같아질 때까지).
   음수 부호는 이 사이트의 숫자처럼 '-'로 쓴다 — 자료 파일의 글(다리 이름 · 정의 · 재생 규칙 · 꼬리표 풀이)에 숫자 앞 빼기(U+2212)가
   있으면 화면에서만 '-'로 바꾼다(dash). 상태 이름(L−− · L− · P−)의 빼기는 숫자가 뒤따르지 않아 그대로다.
   화면의 내 글은 합니다체, 자료 파일의 글(defs · want · notices)은 자료 그대로 싣는다. 자료 파일의 notice(한다체, 같은 뜻)는 ABOUT과
   겹쳐 싣지 않는다. */
"use strict";
window.LpCard = (() => {
  const LABEL = "운영자 판단 격자의 칸 이름(운영자 메모) — 예측 아님 · 예측력 검증 안 됨";
  const CHIP = "참고 — 예측 아님";
  const TITLE = "판단 격자 L × P";
  const ABOUT = "운영자가 비공개로 쓰는 측정 도구의 판단 격자(노동 상태 L 넷 × 물가 상태 P 넷, 16칸)를 FRED 공개 통계로 이 사이트가 " +
    "따로 다시 계산했습니다. 문턱은 운영자가 고정한 값 그대로이고, 이 사이트의 규칙 수에 들지 않습니다.";
  const L_STATES = ["L+", "L0", "L−", "L−−"];          // 격자의 행 차례(위에서 아래)
  const L_ORDER = ["L−−", "L−", "L+", "L0"];           // 정의를 보는 차례(위에서부터 처음 맞는 상태)
  const P_STATES = ["P+", "P0", "Pd", "P−"];           // 격자의 열 차례(왼쪽에서 오른쪽)
  const UNKNOWN = "?";
  const BANDS = ["H", "M", "Lo"], MOMS = ["A", "F", "D"];
  const BAND_WORD = { H: "높음", M: "중간", Lo: "낮음" };
  const MOM_WORD = { A: "가속", F: "평탄", D: "둔화" };
  // 운영자 판단 격자(운영자 메모, 2026-10-14) — 칸 이름과 종류. 사적 도구 econ_regime_check.CELLS와 글자까지 같다(짝 테스트가 견준다)
  const CELLS = {
    "L+|P+": ["금리 상방 여지 (확인)", "up"], "L+|P0": ["금리 상방 관찰 (노동 선행)", "up"],
    "L+|Pd": ["박스 (상단 시험)", "box"], "L+|P−": ["박스 (실질 성장형·골디락스)", "box"],
    "L0|P+": ["금리 상방 관찰 (물가 선행)", "up"], "L0|P0": ["박스", "box"],
    "L0|Pd": ["박스 (하단 시험)", "box"], "L0|P−": ["금리 하방 여지 (디스인플레이션형, 2023 하반기형)", "down"],
    "L−|P+": ["상충: 박스·스티프닝 경계 (스태그 초기)", "mixed"], "L−|P0": ["금리 하방 경계", "down"],
    "L−|Pd": ["금리 하방 경계 (되돌림 쪽)", "down"], "L−|P−": ["되돌림 위험 (2024 하반기형)", "down"],
    "L−−|P+": ["되돌림 제한 (스태그형·불 스티프닝)", "mixed"], "L−−|P0": ["큰 되돌림 위험", "down"],
    "L−−|Pd": ["큰 되돌림 위험", "down"], "L−−|P−": ["큰 되돌림 위험 (경기침체형)", "down"]
  };
  // 물가 P = 띠 × 모멘텀(운영자 정의 9칸) — 사적 도구 P_GRID와 같다
  const P_GRID = { "H|A": "P+", "H|F": "P+", "H|D": "Pd", "M|A": "P+", "M|F": "P0", "M|D": "P−",
    "Lo|A": "P0", "Lo|F": "P−", "Lo|D": "P−" };
  const KINDS = ["up", "down", "box", "mixed"];
  // 노동과 물가가 엇갈리는 칸(종류 mixed) — 색 띠만으로는 이름이 비슷한 이웃 칸과 가르기 어려워 격자 아래 줄에 칸 자리로 적는다
  const MIXED = Object.keys(CELLS).filter(k => CELLS[k][1] === "mixed").map(k => k.replace("|", " × "));
  // 격자 머리의 짧은 정의(운영자 정의의 이름) — 긴 정의(자료 파일 defs)는 '읽는 법'에
  const SHORT_L = { "L+": "회복 전환", "L0": "그 밖", "L−": "냉각", "L−−": "비선형 악화" };
  const SHORT_P = { "P+": "높음 또는 가속", "P0": "중간 · 평탄", "Pd": "높지만 둔화", "P−": "둔화 또는 낮음" };
  // 문턱(운영자 2026-10-14 고정) — 자료 파일 constants의 키. 하나라도 없거나 숫자가 아니면 파일을 쓰지 않는다
  const CONSTANTS = ["sahm_on", "sahm_watch", "hi_gap", "d6u", "claims_ratio", "claims_weeks", "epop_up", "epop_dn", "vu_up",
    "vu_dn", "quits_up", "h_in", "h_out", "lo_in", "lo_out", "mom", "mom_n", "mom_dn", "mom_dn_n"];
  // 해고 몫 꼬리표의 경계(해고형 ≥ 0.5 · 진입형 < 0.3 — 판단에 쓰지 않는 표시 줄). 자료 파일 constants에 layoff_hi · layoff_lo가 있으면 그것
  const LAYOFF = { layoff_hi: 0.5, layoff_lo: 0.3 };
  // 이 사이트가 싣지 않는 꼬리표 — 싣지 않는 재료가 필요하다(정책 경로 가격 · 기간 프리미엄 분해 · 댈러스 연은 트림 평균).
  // 자료에 있어도 앞부분이 같으면 뺀다(문턱 숫자가 바뀌어도 걸리게). 밸류 크기 꼬리표('금리<경제'·'금리>경제'·'밸류 …')도 뺀다
  const EXCLUDED = ["상당 부분 반영", "TP 주도", "폭 좁음(트림 ≤ 3)"];
  const EXCLUDED_HEADS = ["상당 부분 반영", "TP 주도", "폭 좁음", "금리<경제", "금리>경제", "밸류"];
  const EXCLUDED_WHY = "정책 경로가 금리에 얼마나 실렸는지 · 기간 프리미엄과 기대인플레이션의 3개월 변화 · 댈러스 연은 트림 평균";
  // 비공개 도구의 '고점 통과 — 되돌림 소진 가능'은 앞부분만 싣는다(해석 부분은 방향을 말한다)
  const PEAK = "고점 통과";
  const shortTag = t => (t.startsWith(PEAK) ? PEAK : t);
  // 자료 글의 숫자 앞 빼기(U+2212) → '-'(이 사이트가 쓰는 숫자와 같은 부호). 상태 이름의 빼기는 그대로
  const dash = t => t.replace(/\u2212(?=\d)/g, "-");
  // 자료 파일의 글에 있으면 그 글을 싣지 않는 낱말(예측 · 권유)
  const BANNED_WORDS = ["매수", "매도", "유망", "적중", "전망", "예상", "추천"];
  const HOLDOUT_MARK = "표본 밖(운영자 지정)";
  const STALE_DAYS = 10;              // 계산한 날이 이보다 오래되면 '오래됨'
  const SERIES = ["UNRATE", "LNS12300060", "UNEMPLOY", "LNS13026638", "LNS13025699", "USPRIV", "ICSA", "CCSA", "JTSJOL", "JTSQUR",
    "PCEPILFE", "CPIAUCSL", "CPILFESL", "CUSR0000SACL1E"];
  const FETCHED = { net: "", cache: "이번 갱신에서 받지 못해 저장해 둔 자료", missing: "받지 못함" };
  // 다리 13개 — 사적 도구 leg_list의 차례. 이름은 자료 그대로 싣되 앞부분(head)이 맞아야 그 다리로 읽는다.
  // kind: num(숫자) · bool(예/아니오). on: bool(●/○/?) · layoff(해고형/진입형/모호/-) · band(H/M/Lo) · mom(A/F/D).
  // ths: 값과 견주는 문턱(자리를 늘리는 기준) — 다리의 충족과 상관없이 값 자체가 문턱의 어느 쪽인지가 보이게. 같은 값을 쓰는 두 다리
  // (Sahm형 둘 · 고용률 둘 · V/U 둘)는 두 문턱을 함께 봐 같은 값이 두 줄에서 다르게 보이지 않게 한다. Sahm형은 L+ (B)의 '≤ 0'도 본다.
  // lp_fetch.LEG_THS와 같아야 한다(test_lp_fetch가 견준다). group: 표에서 묶는 칸(아래 GROUPS)
  const LEGS = [
    { head: "Sahm형 ≥", kind: "num", unit: "%p", dec: 2, ths: c => [c.sahm_on, c.sahm_watch, 0], on: "bool", group: 0 },
    { head: "Sahm형 ≥", kind: "num", unit: "%p", dec: 2, ths: c => [c.sahm_on, c.sahm_watch, 0], on: "bool", group: 0 },
    { head: "u3 상승", kind: "bool", on: "bool", group: 0 },
    { head: "청구 다리", kind: "num", unit: "배", dec: 2, ths: c => [c.claims_ratio], on: "bool", group: 0 },
    { head: "해고 몫", kind: "num", unit: "", dec: 2, ths: c => [c.layoff_hi, c.layoff_lo], on: "layoff", group: 0 },
    { head: "핵심연령 고용률", kind: "num", unit: "%p", dec: 2, signed: true, ths: c => [c.epop_dn, c.epop_up], on: "bool", group: 0 },
    { head: "V/U", kind: "num", unit: "", dec: 2, signed: true, ths: c => [c.vu_dn, c.vu_up], on: "bool", group: 0 },
    { head: "민간고용", kind: "num", unit: "", dec: 0, signed: true, ths: () => [0], on: "bool", group: 0 },
    { head: "고점 대비 하락", kind: "num", unit: "%p", dec: 2, signed: true, ths: c => [c.hi_gap], on: "bool", group: 1 },
    { head: "회복 확인(고용률", kind: "num", unit: "%p", dec: 2, signed: true, ths: c => [c.epop_dn, c.epop_up], on: "bool", group: 1 },
    { head: "회복 확인(V/U", kind: "num", unit: "", dec: 2, signed: true, ths: c => [c.vu_dn, c.vu_up], on: "bool", group: 1 },
    { head: "근원 PCE Y3 띠", kind: "num", unit: "%", dec: 2, ths: c => [c.h_in, c.h_out, c.lo_in, c.lo_out], on: "band", group: 2 },
    { head: "근원 PCE 모멘텀", kind: "num", unit: "%p", dec: 2, signed: true, ths: c => [c.mom, -c.mom_dn], on: "mom", group: 2 }
  ];
  const GROUPS = ["노동 — 악화 쪽 다리(L−− · L− 판단)", "노동 — 회복 쪽 다리(L+ 판단)", "물가 — 근원 PCE(P 판단)"];
  // 그 달 조건만의 노동 상태를 만든 절(자료 파일 current.raw_rules — lp_fetch.raw_rules). 숫자는 자료 파일의 문턱에서
  const RAW_RULE = c => ({
    "L−−": `Sahm형 ≥ ${c.sahm_on.toFixed(2)} · u3 상승 · 청구 다리 켜짐`,
    a: `(a) Sahm형 ≥ ${c.sahm_watch.toFixed(2)}이고 u3 상승`,
    b: `(b) Sahm형 ≥ ${c.sahm_on.toFixed(2)}이지만 해고 미확인(청구 다리가 켜져 있지 않음)`,
    c: "(c) 청구가 아닌 악화 다리 2개 이상",
    d: "(d) 청구 다리 켜짐과 악화 다리 1개 이상",
    A: "(A) 고점 대비 하락과 확인 다리 1개 이상",
    B: "(B) Sahm형 ≤ 0 · V/U와 이직률의 6개월 변화가 회복 문턱 이상"
  });
  const RAW_OF = { "L−−": ["L−−"], "L−": ["a", "b", "c", "d"], "L+": ["A", "B"] };
  const LAYOFF_ON = ["해고형", "진입형", "모호", "-"];
  // 상태가 바뀌는 규칙(운영자 정의) — 지금 상태와 '그 달 조건'이 다른 까닭. 숫자는 자료 파일의 문턱에서
  const rulesText = c => "노동 L은 서로 다른 두 발표가 이어서 같은 조건을 보여야 바뀝니다(L−−만 한 번으로 들어갑니다). L−·L−−에서 L0으로 " +
    "돌아갈 때는 실업률 3개월 평균이 3개월 전 이하이고, 청구 다리가 켜져 있지 않고(꺼짐 또는 ?), 악화 다리(고용률 · V/U · 민간고용)가 " +
    "둘 이상 켜져 있지 않은 상태가 두 발표 이어져야 하며, 그 달에 '고점 통과' 꼬리표가 한 번 붙습니다. 노동 L을 모르는 달은 연속 셈이 " +
    "끊기지만, 물가 P만 모르는 달(대개 근원 PCE 발표 전)은 칸만 판정 보류이고 셈은 이어집니다. 물가 띠는 들어가는 문턱과 나오는 문턱이 달라" +
    `(H ${c.h_in}/${c.h_out} · Lo ${c.lo_in}/${c.lo_out}) 작은 차이로 깜박이지 않습니다. 모멘텀은 가속이 ${c.mom_n}번, ` +
    `둔화가 ${c.mom_dn_n}번 이어진 발표에서 켜집니다.`;
  const EXP_NOTE = "운영자가 재생 결과를 보기 전에 적어 둔 기대(운영자 메모)를 이 사이트의 재생과 나란히 둡니다. 달마다 노동 L · 물가 P가 " +
    "기대한 상태에 드는지만 셉니다 — 기대 글의 꼬리표 점검(상당 부분 반영 · TP 주도)은 이 사이트가 계산하지 않습니다. 어긋나도 " +
    "문턱을 고치지 않고 적기만 합니다.";
  // 표본 밖 구간의 뜻 — 문턱을 정한 뒤에 나온 자료가 아니다(운영자 문턱 고정 기록: 둔화 모멘텀 문턱은 2024-09 재생도 보고 골랐다)
  const HOLDOUT_NOTE = (v, c) => ` ${v.holdout}부터의 사례는 ${HOLDOUT_MARK}입니다 — 운영자가 문턱의 근거와 따로 보려고 남겨 둔 구간이지만, ` +
    `문턱을 고정한 ${v.fixed}에는 이 구간의 자료도 이미 나와 있었고 둔화 모멘텀 문턱(${(-c.mom_dn).toFixed(1)} 이하 ${c.mom_dn_n}번 연속)은 ` +
    "2024-09의 재생 결과도 보고 골랐습니다. 문턱을 정한 뒤에 나온 자료로 한 검증이 아닙니다.";
  const NOT_FORECAST = "칸 이름은 운영자 메모입니다. 예측이 아니고 예측력을 검증하지 않았습니다.";
  // 권장 인용의 꼴 — ledger.js · tp.js와 같다('…, retrieved from …, November 18, 2026.'). 꼴이 다르면 싣지 않는다
  const CITE = /^[^<>]{1,300}, retrieved from [^<>]{1,300}, [A-Z][a-z]+ \d{1,2}, \d{4}\.$/;
  const DAY = /^\d{4}-\d{2}-\d{2}$/;
  const MONTH = /^\d{4}-(0[1-9]|1[0-2])$/;
  const PLAIN = /^[^\u0000-\u001f\u007f<>]+$/;            // 제어 문자 · 꺾쇠 없는 한 줄 글
  const HOLD = /^판정 보류\((노동|물가|노동·물가)\)$/;

  const isObj = v => v !== null && typeof v === "object" && !Array.isArray(v);
  const num = v => typeof v === "number" && Number.isFinite(v);
  const numOrNull = v => v === null || num(v);
  const count = v => Number.isInteger(v) && v >= 0;
  const day = v => typeof v === "string" && DAY.test(v) && Number.isFinite(Date.parse(v + "T00:00:00Z")) &&
    new Date(v + "T00:00:00Z").toISOString().slice(0, 10) === v;
  const month = v => typeof v === "string" && MONTH.test(v);
  const clean = t => !BANNED_WORDS.some(w => t.includes(w));
  const str = (v, max) => typeof v === "string" && v.length > 0 && v.length <= (max || 200) && PLAIN.test(v) && clean(v) ? v : null;
  const texts = (v, max) => (Array.isArray(v) ? v : []).map(x => str(x, max || 400)).filter(Boolean);
  const isL = v => v === UNKNOWN || L_STATES.includes(v);
  const isP = v => v === UNKNOWN || P_STATES.includes(v);
  const band = v => v === null || BANDS.includes(v);
  const mom = v => v === null || MOMS.includes(v);

  // 칸 이름이 그 칸의 L · P와 짝이 맞는가 — 둘 다 알면 운영자 표의 이름과 종류, 하나라도 '?'면 '판정 보류(빠진 쪽)'
  function cellOk(L, P, name, kind) {
    const lk = L_STATES.includes(L), pk = P_STATES.includes(P);
    if (lk && pk) {
      const c = CELLS[L + "|" + P];
      return c[0] === name && (kind === undefined || c[1] === kind);
    }
    const miss = [lk ? null : "노동", pk ? null : "물가"].filter(Boolean).join("·");
    return (kind === undefined || kind === "hold") && name === `판정 보류(${miss})`;
  }
  // 물가 P가 띠 × 모멘텀과 맞는가 — 둘 다 있으면 P_GRID, 하나라도 없으면 '?'
  const pOk = (P, b, m) => (b && m ? P_GRID[b + "|" + m] === P : P === UNKNOWN);
  const tagsOf = v => (Array.isArray(v) ? [...new Set(v.filter(t => str(t, 120) && !EXCLUDED_HEADS.some(h => t.startsWith(h))).map(shortTag))]
    : null);

  // ── 숫자 ──────────────────────────────────────────────────────────────────────────────
  const r6 = x => Math.round(x * 1e6) / 1e6;
  const side = (x, t) => Math.sign(r6(x) - r6(t));
  // 문턱 옆 숫자 — 기본 자리(dec)로 반올림한 숫자가 모든 문턱(ths)에 대해 실제 값과 같은 쪽(또는 같음)일 때까지 자리를 늘린다
  // (사적 도구의 비교처럼 소수 6자리 반올림 뒤). 0으로 반올림되면 부호 없이, signed면 양수에 +. 음수 부호는 '-'
  function near(v, dec, ths, signed) {
    let s = v.toFixed(dec);
    for (let d = dec; d <= 6; d++) {
      s = v.toFixed(d);
      if ((ths || []).filter(num).every(t => side(Number(s), t) === side(v, t))) break;
    }
    if (Number(s) === 0) return s.replace("-", "");
    return (signed && v > 0 ? "+" : "") + s;
  }
  const shown = (v, dec, ths, signed, unit) => (num(v) ? near(v, dec, ths, signed) + (unit || "") : "—");

  // ── 자료 읽기 ─────────────────────────────────────────────────────────────────────────
  function constantsOf(c) {
    if (!isObj(c) || !CONSTANTS.every(k => num(c[k]))) return null;
    const out = {};
    for (const k of CONSTANTS) out[k] = c[k];
    for (const k of Object.keys(LAYOFF)) out[k] = num(c[k]) ? c[k] : LAYOFF[k];
    return out;
  }
  // 격자 — 행 · 열 차례와 16칸의 이름 · 종류가 운영자 표와 같아야 한다(아니면 파일을 쓰지 않는다)
  function gridOk(g) {
    if (!isObj(g) || !Array.isArray(g.L) || !Array.isArray(g.P) || !Array.isArray(g.cells)) return false;
    if (g.L.join("|") !== L_STATES.join("|") || g.P.join("|") !== P_STATES.join("|") || g.cells.length !== 4) return false;
    return g.cells.every((row, i) => Array.isArray(row) && row.length === 4 && row.every((c, j) => isObj(c) &&
      c.L === L_STATES[i] && c.P === P_STATES[j] && cellOk(c.L, c.P, c.name, c.kind)));
  }
  function defsOf(d) {
    const out = { L: {}, P: {}, band: {}, mom: {}, pgrid: null, replay: [], tags: [] };
    if (!isObj(d)) return out;
    for (const [key, field, ok] of [["L", "state", v => L_STATES.includes(v)], ["P", "state", v => P_STATES.includes(v)],
      ["band", "band", v => BANDS.includes(v)], ["mom", "mom", v => MOMS.includes(v)]])
      for (const x of Array.isArray(d[key]) ? d[key] : [])
        if (isObj(x) && ok(x[field]) && str(x.text, 300) && !(x[field] in out[key])) out[key][x[field]] = x.text;
    // 띠 × 모멘텀 → P — 아홉 칸이 모두 운영자 정의와 같을 때만 표로 싣는다
    const pg = Array.isArray(d.pgrid) ? d.pgrid : [];
    const seen = new Set(pg.filter(x => isObj(x) && P_GRID[x.band + "|" + x.mom] === x.P).map(x => x.band + "|" + x.mom));
    if (pg.length === 9 && seen.size === 9) out.pgrid = P_GRID;
    // 재생 규칙(글 여러 줄)과 꼬리표 풀이({tag, text}) — 이 사이트가 싣지 않는 꼬리표는 풀이도 싣지 않는다
    out.replay = texts(d.replay, 300);
    const tseen = new Set();
    for (const x of Array.isArray(d.tags) ? d.tags : []) {
      if (!isObj(x) || !str(x.tag, 120) || !str(x.text, 300) || EXCLUDED_HEADS.some(h => x.tag.startsWith(h))) continue;
      const tag = shortTag(x.tag);
      if (tseen.has(tag)) continue;
      tseen.add(tag);
      out.tags.push({ tag, text: x.text });
    }
    return out;
  }
  function legOf(x, i) {
    const spec = LEGS[i];
    if (!spec || !isObj(x) || !str(x.name, 120) || !x.name.startsWith(spec.head) || !month(x.month)) return null;
    if (spec.kind === "num" ? !numOrNull(x.value) : !(x.value === null || typeof x.value === "boolean")) return null;
    const on = x.on;
    const okOn = spec.on === "bool" ? on === null || typeof on === "boolean"
      : spec.on === "layoff" ? LAYOFF_ON.includes(on)
      : spec.on === "band" ? band(on) : mom(on);
    return okOn ? { name: x.name, value: x.value, month: x.month, on, spec } : null;
  }
  function inflationOf(x) {
    if (!isObj(x) || !["y12", "a3", "a6", "mom", "Y3"].every(k => numOrNull(x[k])) ||
        !(x.Y3_n === null || (Number.isInteger(x.Y3_n) && x.Y3_n > 0 && x.Y3_n <= 3))) return null;
    return { y12: x.y12, a3: x.a3, a6: x.a6, mom: x.mom, Y3: x.Y3, n: x.Y3_n };
  }
  // 달 한 줄(재생 · 지금 칸) — 상태 · 칸 이름 · 띠 × 모멘텀이 서로 맞아야 한다
  function rowOf(r) {
    if (!isObj(r) || !month(r.month) || !day(r.known) || !isL(r.L) || !isL(r.L_raw) || !isP(r.P) || !band(r.band) ||
        !mom(r.mom_class) || !(KINDS.includes(r.kind) || r.kind === "hold") || !cellOk(r.L, r.P, r.cell, r.kind) ||
        !pOk(r.P, r.band, r.mom_class)) return null;
    const tags = tagsOf(r.tags);
    if (!tags) return null;
    return { month: r.month, known: r.known, L: r.L, raw: r.L_raw, P: r.P, band: r.band, mom: r.mom_class, cell: r.cell,
      kind: r.kind, tags };
  }
  // 그 달 조건만의 노동 상태를 만든 절 — 그 상태에 맞는 절 이름만(L0 · '?'은 빈 목록). 꼴이 어긋나면 null(줄을 싣지 않는다)
  function rawRulesOf(x, raw) {
    if (!Array.isArray(x)) return null;
    const allowed = RAW_OF[raw] || [];
    if (x.length > allowed.length || new Set(x).size !== x.length || !x.every(k => allowed.includes(k))) return null;
    return (x.length > 0) === (raw in RAW_OF) ? x.slice() : null;
  }
  function currentOf(c) {
    const r = rowOf(c);
    if (!r || r.kind === "hold") return null;                  // 지금 칸은 판정 보류가 아닌 마지막 달이다
    r.legs = (Array.isArray(c.legs) ? c.legs : []).slice(0, LEGS.length).map(legOf).filter(Boolean);
    r.inflation = inflationOf(c.inflation);
    r.rules = rawRulesOf(c.raw_rules, r.raw);
    r.d6u3 = num(c.d6u3) ? c.d6u3 : null;
    return r;
  }
  function latestOf(x, cur, history) {
    if (!isObj(x) || !month(x.month) || !isL(x.L) || !isP(x.P) || x.kind !== "hold" || !cellOk(x.L, x.P, x.cell, "hold")) return null;
    if (cur && x.month <= cur.month) return null;              // 지금 칸보다 새 달일 때만
    const tags = tagsOf(x.tags);
    const h = history.find(r => r.month === x.month);
    const known = day(x.known) ? x.known : h ? h.known : null; // 알려진 날(근사) — 없으면 재생 기록의 같은 달
    return tags ? { month: x.month, L: x.L, P: x.P, cell: x.cell, tags, known } : null;
  }
  function itemOf(x, c) {
    if (!isObj(x) || !month(x.month) || x.month < c.from || (c.to !== null && x.month > c.to) || !isL(x.L) || !isP(x.P) ||
        !cellOk(x.L, x.P, x.cell) || typeof x.match !== "boolean") return null;
    return { month: x.month, L: x.L, P: x.P, cell: x.cell, match: x.match };
  }
  // 기대 사례 — 항목 하나라도 꼴이 어긋나거나 셈(n · matched)이 항목과 다르면 그 사례를 뺀다. 기대한 상태 목록(want_L · want_P —
  // null은 '정하지 않음')이 있으면 항목마다의 듦(match)이 그 목록과 맞아야 한다. tag_unchecked는 이 사이트가 대조하지 않는 꼬리표(EXCLUDED 안)
  const wantOk = (w, states) => w === undefined || w === null || (Array.isArray(w) && w.length > 0 && w.every(s => states.includes(s)));
  const within = (w, s) => w === undefined || w === null || w.includes(s);
  function caseOf(x) {
    if (!isObj(x) || !str(x.case, 40) || !str(x.want, 200) || !month(x.from) || !(x.to === null || month(x.to)) ||
        typeof x.holdout !== "boolean" || !count(x.n) || !count(x.matched) || !Array.isArray(x.items) ||
        !wantOk(x.want_L, L_STATES) || !wantOk(x.want_P, P_STATES) ||
        !(x.tag_unchecked === undefined || x.tag_unchecked === null || EXCLUDED.includes(x.tag_unchecked))) return null;
    const c = { case: x.case, want: x.want, from: x.from, to: x.to, holdout: x.holdout, tag: x.tag_unchecked || null,
      wantL: x.want_L, wantP: x.want_P };
    const items = x.items.map(i => itemOf(i, c));
    if (items.some(i => !i) || items.length !== x.n || items.filter(i => i.match).length !== x.matched) return null;
    if ((x.want_L !== undefined || x.want_P !== undefined) &&
        items.some(i => i.match !== (within(x.want_L, i.L) && within(x.want_P, i.P)))) return null;
    return Object.assign(c, { n: x.n, matched: x.matched, items });
  }
  function seriesOf(list) {
    const seen = new Set();
    return (Array.isArray(list) ? list : []).filter(s => isObj(s) && SERIES.includes(s.series) && !seen.has(s.series) &&
      str(s.title, 160) && (s.last === null || day(s.last)) && Object.prototype.hasOwnProperty.call(FETCHED, s.fetched) &&
      seen.add(s.series));
  }
  function citesOf(list) {
    const seen = new Set(), out = [];
    for (const s of Array.isArray(list) ? list : []) {
      if (!isObj(s) || !SERIES.includes(s.series) || seen.has(s.series) || typeof s.citation !== "string" || !CITE.test(s.citation) ||
          typeof s.citation_required !== "boolean") continue;
      seen.add(s.series);
      out.push({ series: s.series, url: typeof s.url === "string" ? s.url : null, citation: s.citation });
    }
    return out;
  }
  // 파일 전체 — schema · 날짜 · 문턱 · 격자가 맞아야 쓰고, 지금 칸이나 재생 기록 가운데 하나는 있어야 한다
  function parse(d) {
    if (!isObj(d) || d.schema !== 1 || !day(d.asof) || !day(d.fixed) || !month(d.holdout_from) || !gridOk(d.grid)) return null;
    const c = constantsOf(d.constants);
    if (!c) return null;
    const current = currentOf(d.current);
    const seen = new Set();
    const history = (Array.isArray(d.history) ? d.history : []).map(rowOf).filter(r => r && !seen.has(r.month) && seen.add(r.month))
      .sort((a, b) => (a.month < b.month ? -1 : 1));
    if (!current && !history.length) return null;
    // 자료에 있었지만 꼴이 어긋나 뺀 달 — 재생 기록의 빈 달이 '실업률 미발표'인지 '자료 꼴'인지 가른다
    const dropped = new Set((Array.isArray(d.history) ? d.history : []).filter(r => isObj(r) && month(r.month) && !seen.has(r.month))
      .map(r => r.month));
    return { asof: d.asof, fixed: d.fixed, holdout: d.holdout_from, c, current, latest: latestOf(d.latest, current, history), history,
      dropped,
      defs: defsOf(d.defs), expected: (Array.isArray(d.expected) ? d.expected : []).map(caseOf).filter(Boolean),
      series: seriesOf(d.series), cites: citesOf(d.sources), notices: texts(d.notices) };
  }

  // ── 그리기 ────────────────────────────────────────────────────────────────────────────
  // 표 하나 — 설명 줄은 표 밖(좁은 화면에서도 접혀 다 보이게), 표는 가로 스크롤 상자 안. 표의 이름은 짧은 설명 줄(aria-labelledby),
  // 읽는 법이 긴 표는 그 아래 덧줄(note)에
  let capSeq = 0;
  function block(cap, cls, ...parts) {
    const id = "lp-cap-" + (++capSeq);
    const note = parts.length && parts[0] && parts[0].note ? parts.shift().note : null;
    return el("div", { class: "lp-block" }, el("p", { class: "muted lp-cap", id }, cap),
      note ? el("p", { class: "muted lp-note" }, note) : null,
      el("div", { class: "lp-scroll" }, el("table", { class: "lp-table " + cls, "aria-labelledby": id }, ...parts)));
  }
  const th = (t, scope) => el("th", { scope: scope || "col" }, t);
  const pPart = r => (r.band && r.mom ? ` (띠 ${r.band} ${BAND_WORD[r.band]} · 모멘텀 ${r.mom} ${MOM_WORD[r.mom]})` : "");
  const tagLine = tags => (tags.length ? "꼬리표: " + tags.join(" · ") : "꼬리표 없음");

  function summary(v) {
    const cur = v.current, out = [];
    if (cur) {
      out.push(el("p", { class: "lp-now" }, "기준월 ", el("strong", {}, cur.month), ` · 알려진 날 ${cur.known}(근사) · 노동 `,
        el("strong", {}, cur.L), " · 물가 ", el("strong", {}, cur.P), pPart(cur), " → ",
        el("strong", { class: "lp-name" }, cur.cell)));
      if (cur.raw !== cur.L)
        out.push(el("p", { class: "muted" }, cur.raw === UNKNOWN ? "그 달 조건만으로는 노동 상태를 정하지 못했습니다(자료가 모자람)."
          : `그 달 조건만 보면 ${cur.raw}입니다 — 상태는 두 발표가 이어져야 바뀌어 지금 상태는 ${cur.L}입니다.`));
      out.push(el("p", { class: "muted lp-tags" }, tagLine(cur.tags)));
    } else {
      out.push(el("p", { class: "lp-now" }, "판정할 수 있는 달이 아직 없습니다."));
    }
    const lt = v.latest;
    if (lt) {
      const lk = L_STATES.includes(lt.L), pk = P_STATES.includes(lt.P);
      const why = lk && !pk ? `노동 ${lt.L} — 물가 아직 발표 전이라 판정 보류`
        : !lk && pk ? `물가 ${lt.P} — 노동 상태를 정할 자료가 모자라 판정 보류` : "노동·물가 모두 판정 보류";
      out.push(el("p", { class: "lp-latest" }, `${lt.month}: ${why}` + (lt.known ? ` · 알려진 날 ${lt.known}(근사)` : ""),
        lt.tags.length ? el("small", {}, " · " + tagLine(lt.tags)) : null));
    }
    return out;
  }
  function gridBlock(v) {
    const cur = v.current;
    const head = el("thead", {}, el("tr", {}, el("th", { scope: "col", "aria-label": "노동 L(행) × 물가 P(열)" }, "L \\ P"),
      ...P_STATES.map(p => el("th", { scope: "col" }, el("strong", {}, p), " ", el("small", {}, SHORT_P[p])))));
    const body = el("tbody", {}, ...L_STATES.map(l => el("tr", {},
      el("th", { scope: "row" }, el("strong", {}, l), " ", el("small", {}, SHORT_L[l])),
      ...P_STATES.map(p => {
        const [name, kind] = CELLS[l + "|" + p], here = !!cur && cur.L === l && cur.P === p;
        return el("td", Object.assign({ class: "lp-c lp-k-" + kind }, here ? { "aria-current": "true" } : {}),
          here ? el("span", { class: "lp-here" }, "지금") : null, here ? " " : null, name);
      }))));
    return block("판단 격자 16칸 · " + LABEL, "lp-grid", { note: "행은 노동 L, 열은 물가 P입니다. 칸 왼쪽의 색 띠는 운영자가 칸마다 " +
      "적어 둔 종류 넷을 가릅니다 — 같은 색이면 같은 종류이고, 칸의 뜻은 칸 이름에 있습니다. 왼쪽 테두리가 점선인 두 칸(" +
      MIXED.join(" · ") + ")은 노동과 물가가 엇갈리는 칸입니다. 상태의 정의는 아래 '읽는 법'에 있습니다." }, head, body);
  }
  function legCell(l, c) {
    const s = l.spec;
    if (s.on === "bool") return l.on === true ? "●" : l.on === false ? "○" : "?";
    if (s.on === "layoff") return l.on === "-" ? "—" : l.on;
    if (s.on === "band") {
      if (!l.on) return "?";
      // 띠는 들어가는 문턱과 나오는 문턱이 달라, 진입 문턱 안쪽 값이어도 직전 띠가 남는다 — 그때 까닭을 함께
      const keep = !num(l.value) ? "" : l.on === "H" && side(l.value, c.h_in) <= 0 ? ` (${c.h_in} 초과로 들어간 뒤 ${c.h_out} 미만이 아니라 유지)`
        : l.on === "Lo" && side(l.value, c.lo_in) >= 0 ? ` (${c.lo_in} 미만으로 들어간 뒤 ${c.lo_out} 초과가 아니라 유지)` : "";
      return `${l.on} ${BAND_WORD[l.on]}${keep}`;
    }
    return l.on ? `${l.on} ${MOM_WORD[l.on]}` : "?";
  }
  function legValue(l, cur, c) {
    const s = l.spec;
    if (s.kind === "bool") return l.value === true ? "예" : l.value === false ? "아니요" : "—";
    const v = shown(l.value, s.dec, s.ths(c), s.signed, s.unit);
    // 고점 대비 하락은 두 조건(hi_gap · u3의 6개월 변화)이 함께 맞아야 켜진다 — 둘째 값도 함께
    return s.head === "고점 대비 하락" && num(cur.d6u3) ? `${v} · 6개월 변화 ${shown(cur.d6u3, 2, [c.d6u], true, "%p")}` : v;
  }
  function rawLine(cur, c) {
    if (!cur.rules || cur.raw === UNKNOWN) return null;
    const t = RAW_RULE(c);
    const why = cur.rules.length ? cur.rules.map(k => t[k]).join(" · ") : "L−− · L− · L+의 조건이 하나도 맞지 않음";
    return el("p", { class: "lp-why" }, `그 달 조건만의 노동 상태: ${cur.raw} — ${why}.` +
      (cur.raw !== cur.L ? ` 상태는 두 발표가 이어져야 바뀌어 지금 상태는 ${cur.L}입니다.` : ""));
  }
  function legsBlock(v) {
    const cur = v.current;
    if (!cur.legs.length) return el("p", { class: "muted" }, "다리 자료가 없습니다.");
    const bodies = GROUPS.map((g, i) => [g, cur.legs.filter(l => l.spec.group === i)]).filter(([, ls]) => ls.length)
      .map(([g, ls]) => el("tbody", {}, el("tr", { class: "lp-group" }, el("th", { scope: "rowgroup", colspan: "4" }, g)),
        ...ls.map(l => el("tr", {}, th(dash(l.name), "row"),
          el("td", { class: "lp-num" }, legValue(l, cur, v.c)), el("td", {}, l.month), el("td", {}, legCell(l, v.c))))));
    const table = block(`${cur.month} 다리 13개`, "lp-legs", { note: "● 충족 · ○ 미충족 · ? 자료 없음. 해고 몫은 판단에 쓰지 않는 표시 줄이라 " +
      "해고형 · 진입형 · 모호를, 띠 · 모멘텀 줄은 그 달의 구분을 적습니다. 자료 달은 그 다리가 쓴 자료의 달입니다(청구는 주간, " +
      "V/U는 그때까지 나온 JOLTS). 고점 대비 하락(hi_gap)은 u3 − 직전 12개 창의 u3 최고이고, u3의 6개월 변화도 함께 맞아야 켜집니다." },
      el("thead", {}, el("tr", {}, ...["다리", "값", "자료 달", "충족"].map(t => th(t)))), ...bodies);
    // 그 달 조건만의 노동 상태를 만든 절은 늘 보이고, 다리 13개의 값 표는 접어 둔다(카드가 길어 첫 화면에서 규칙 절을 밀어내지 않게)
    return [rawLine(cur, v.c), el("details", { class: "rule-detail lp-more lp-legs-more" },
      el("summary", {}, `다리 13개 — 값과 충족(${cur.month})`), table)];
  }
  function inflationLine(v) {
    const x = v.current && v.current.inflation, c = v.c;
    if (!x || !["y12", "Y3", "a6", "mom"].some(k => num(x[k]))) return null;
    return el("p", { class: "lp-infl" }, `근원 PCE(${v.current.month}): 전년비 y12 `, el("span", { class: "lp-num" }, shown(x.y12, 2, [], false, "%")),
      " · 전년비 3개월 평균 Y3 ", el("span", { class: "lp-num" }, shown(x.Y3, 2, [c.h_in, c.h_out, c.lo_in, c.lo_out], false, "%")),
      x.n === 2 && num(x.Y3) ? "(2개월 평균)" : "",
      " · 6개월 연율 a6 ", el("span", { class: "lp-num" }, shown(x.a6, 2, [], false, "%")),
      " · 모멘텀(a6 − y12) ", el("span", { class: "lp-num" }, shown(x.mom, 2, [c.mom, -c.mom_dn], true, "%p")));
  }
  // 두 달 사이의 빈 달(앞 달 다음부터 뒤 달 앞까지)
  const between = (a, b) => { const out = []; for (let m = mnext(a); m < b; m = mnext(m)) out.push(m); return out; };
  const mnext = m => { const y = +m.slice(0, 4), i = +m.slice(5, 7); return i === 12 ? `${y + 1}-01` : `${m.slice(0, 4)}-${String(i + 1).padStart(2, "0")}`; };
  function historyBlock(v) {
    const h = v.history;
    if (!h.length) return null;
    let marked = false;
    const rows = [], gaps = [];
    h.forEach((r, i) => {
      for (const m of i ? between(h[i - 1].month, r.month) : []) {        // 기준월이 없는 달 — 말없이 건너뛰지 않는다
        gaps.push(m);
        rows.push(el("tr", { class: "lp-gap" }, el("th", { scope: "row" }, m), el("td", { colspan: "5" }, v.dropped.has(m)
          ? "자료 꼴이 어긋나 싣지 않았습니다." : "기준월이 없습니다 — 그 달 실업률이 발표되지 않았습니다(재생은 다음 달로 이어집니다).")));
      }
      const mark = !marked && r.month >= v.holdout;
      if (mark) marked = true;
      rows.push(el("tr", { class: "lp-k-" + r.kind }, el("th", { scope: "row" }, r.month, mark ? el("small", {}, "여기부터 " + HOLDOUT_MARK) : null),
        el("td", {}, r.known),
        el("td", {}, r.L, r.raw !== r.L ? el("small", {}, `그 달 조건 ${r.raw}`) : null),
        el("td", {}, r.P, r.band && r.mom ? el("small", {}, `${r.band} · ${r.mom}`) : null),
        el("td", { class: "lp-cellname" }, r.cell), el("td", { class: "lp-tagcell" }, r.tags.length ? r.tags.join(" · ") : "—")));
    });
    const gapText = gaps.length ? ` · 빠진 달 ${gaps.length}(${gaps.slice(0, 6).join(" · ")}${gaps.length > 6 ? ` 외 ${gaps.length - 6}` : ""})` : "";
    return el("details", { class: "rule-detail lp-more" },
      el("summary", {}, `2022년부터 달마다 — ${h.length}달(${h[0].month} ~ ${h[h.length - 1].month}${gapText})`),
      block("달마다 노동 L · 물가 P · 칸 · " + LABEL, "lp-hist",
        el("thead", {}, el("tr", {}, ...["기준월", "알려진 날(근사)", "노동 L", "물가 P(띠 · 모멘텀)", "칸", "꼬리표"].map(t => th(t)))),
        el("tbody", {}, ...rows)));
  }
  // 기대에 들지 않은 달 가운데, 어긋난 쪽이 모두 '?'(판정 보류)인 달 — 아직 가를 수 없다(자료 파일의 셈은 벗어남으로 센다)
  function undecided(i, c) {
    if (i.match) return false;
    if (c.wantL === undefined && c.wantP === undefined) return HOLD.test(i.cell);
    const lOk = within(c.wantL, i.L), pOk = within(c.wantP, i.P);
    return (lOk || i.L === UNKNOWN) && (pOk || i.P === UNKNOWN);
  }
  function caseBlock(c) {
    const range = /^\d{4}-\d{2}/.test(c.case) ? "" : ` ${c.from} ~ ${c.to || "지금"}`;     // 사례 이름이 곧 기간이면 되풀이하지 않는다
    const head = el("p", {}, el("strong", {}, c.case), range, c.holdout ? " " : null,
      c.holdout ? el("span", { class: "lp-out-tag" }, HOLDOUT_MARK) : null);
    const want = el("p", {}, "기대(운영자 메모): " + c.want);
    const tag = c.tag ? el("p", { class: "muted" }, `이 사례에 적힌 꼬리표 '${c.tag}'의 대조는 이 사이트가 계산하지 않습니다.`) : null;
    if (!c.n) return el("div", { class: "lp-case" }, head, want, el("p", { class: "muted" }, "이 구간에 재생한 달이 없습니다."), tag);
    const open = c.items.filter(i => undecided(i, c)).length;
    const count = `기대한 L · P에 든 달 ${c.matched}/${c.n}` + (open ? ` — 판정 보류 ${open}달은 아직 가를 수 없어 벗어남으로 셉니다` +
      `(판정한 달만 보면 ${c.matched}/${c.n - open})` : "");
    return el("div", { class: "lp-case" }, head, want, el("p", { class: "muted" }, count), tag,
      block(`${c.case} 달마다`, "lp-exp", { note: "● 기대한 L · P에 듦 · ○ 벗어남 · ? 판정 보류(아직 가를 수 없음)" },
        el("thead", {}, el("tr", {}, ...["기준월", "노동 L", "물가 P", "칸", "기대"].map(t => th(t)))),
        el("tbody", {}, ...c.items.map(i => el("tr", {}, th(i.month, "row"), el("td", {}, i.L), el("td", {}, i.P),
          el("td", { class: "lp-cellname" }, i.cell), el("td", {}, i.match ? "●" : undecided(i, c) ? "?" : "○"))))));
  }
  function expectedBlock(v) {
    if (!v.expected.length) return null;
    return el("details", { class: "rule-detail lp-more" },
      el("summary", {}, `미리 적어 둔 기대와 대조 — 사례 ${v.expected.length}개`),
      el("p", { class: "lp-label" }, LABEL),
      el("p", { class: "muted" }, EXP_NOTE, HOLDOUT_NOTE(v, v.c)),
      ...v.expected.map(caseBlock));
  }
  function defsBlock(v) {
    const d = v.defs, c = v.c, list = (states, map) => states.filter(s => map[s]).map(s => el("li", {}, el("strong", {}, s), " · " + dash(map[s])));
    const lItems = list(L_ORDER, d.L);                       // 노동 L은 위에서부터 보는 차례(정의 글이 앞 상태를 가리킨다)
    const items = [...list(P_STATES, d.P), ...list(BANDS, d.band), ...list(MOMS, d.mom)];
    const n = x => near(x, 2, [], false), sn = x => near(x, 2, [], true);
    const ths = `문턱(운영자 ${v.fixed} 고정): Sahm형 ${n(c.sahm_on)}(주의 ${n(c.sahm_watch)}) · 청구 ${n(c.claims_ratio)}배 × ${c.claims_weeks}주 · ` +
      `고점 대비 하락(hi_gap) ${sn(c.hi_gap)}, 6개월 변화 ${sn(c.d6u)} · 핵심연령 고용률 6개월 변화 ${sn(c.epop_up)} / ${sn(c.epop_dn)} · ` +
      `V/U 6개월 변화 ${sn(c.vu_up)} / ${sn(c.vu_dn)} · 이직률 6개월 변화 ${sn(c.quits_up)} · 띠 H ${n(c.h_in)} 초과로 들어가 ${n(c.h_out)} 미만에서 나옴, ` +
      `Lo ${n(c.lo_in)} 미만으로 들어가 ${n(c.lo_out)} 초과에서 나옴 · 모멘텀 가속 ${sn(c.mom)} 이상 ${c.mom_n}회, 둔화 ${sn(-c.mom_dn)} 이하 ${c.mom_dn_n}회 연속.`;
    const pg = d.pgrid ? block("물가 P — 띠 × 모멘텀(운영자 정의)", "lp-pgrid",
      el("thead", {}, el("tr", {}, el("th", { scope: "col", "aria-label": "띠(행) × 모멘텀(열)" }, "띠 \\ 모멘텀"),
        ...MOMS.map(m => th(`${m} ${MOM_WORD[m]}`)))),
      el("tbody", {}, ...BANDS.map(b => el("tr", {}, th(`${b} ${BAND_WORD[b]}`, "row"), ...MOMS.map(m => el("td", {}, d.pgrid[b + "|" + m])))))) : null;
    // 재생 규칙 · 꼬리표 풀이(자료 파일의 글 그대로) — 재생 규칙이 없으면 이 사이트의 짧은 설명(rulesText)으로
    const replay = d.replay.length ? [el("p", { class: "lp-sub" }, "재생 규칙(운영자 정의):"), el("ul", { class: "lp-list" }, ...d.replay.map(t => el("li", {}, dash(t))))]
      : [el("p", {}, rulesText(c))];
    const tags = d.tags.length ? [el("p", { class: "lp-sub" }, "꼬리표 풀이:"),
      el("ul", { class: "lp-list" }, ...d.tags.map(t => el("li", {}, el("strong", {}, t.tag), " · " + dash(t.text))))] : [];
    return el("details", { class: "rule-detail lp-more" }, el("summary", {}, "읽는 법 — 상태 · 문턱 · 재생 규칙 · 꼬리표"),
      lItems.length ? el("p", { class: "lp-sub" }, "노동 L — 위에서부터 차례로 보고 처음 맞는 상태입니다(지금 상태는 아래 재생 규칙을 거칩니다):") : null,
      lItems.length ? el("ul", { class: "lp-list" }, ...lItems) : null,
      items.length ? el("ul", { class: "lp-list" }, ...items) : null, pg, ...replay, ...tags, el("p", { class: "muted" }, ths));
  }
  function notesBlock(v) {
    return el("ul", { class: "lp-list lp-notes" },
      el("li", {}, `문턱은 운영자가 과거 자료로 잰 뒤 ${v.fixed}에 고정했습니다. 그 뒤의 결과를 보고 다시 맞추지 않습니다.`),
      el("li", {}, "숫자는 FRED의 현재 개정치로 다시 계산한 것이라 처음 발표된 값과 다를 수 있습니다. 개정되면 지난 달의 상태와 칸도 바뀔 수 있습니다."),
      el("li", {}, "알려진 날은 발표 일정으로 어림한 근사입니다. 기준월의 상태는 그 달 근원 PCE · 고용 · 계속 청구 발표 가운데 늦은 날(근사) " +
        "뒤에 알려진 것으로 봅니다."),
      el("li", {}, `운영자 도구의 꼬리표 가운데 ${EXCLUDED.join(" · ")}는 이 사이트가 싣지 않는 재료(${EXCLUDED_WHY})가 필요해 빼고 싣습니다.`),
      el("li", {}, NOT_FORECAST));
  }
  // 계산값 고지는 늘 보이게, FRED 권장 인용(시리즈마다 한 줄 — 열세 줄이라 길다)은 바로 아래 '자료와 권장 인용'에 접어 둔다
  function citeBox(v) {
    if (!v.notices.length && !v.cites.length) return null;
    return el("div", { class: "notices lp-cite" }, ...v.notices.map(t => el("p", {}, t)),
      v.cites.length ? el("p", {}, `FRED 권장 인용(시리즈 ${v.cites.length}개)은 바로 아래 '자료와 권장 인용'에 시리즈마다 적습니다.`) : null);
  }
  function sourceBlock(v) {
    if (!v.series.length && !v.cites.length) return null;
    const seriesUrl = sid => { const s = v.cites.find(x => x.series === sid); return s && s.url ? s.url : "https://fred.stlouisfed.org/series/" + sid; };
    const parts = v.series.flatMap((s, i) => [i ? " · " : "", link(s.series, seriesUrl(s.series)), FETCHED[s.fetched] ? `(${FETCHED[s.fetched]})` : ""])
      .filter(x => x !== "");
    const n = v.series.length || v.cites.length;
    return el("details", { class: "rule-detail lp-more lp-sources" },
      el("summary", {}, `자료와 권장 인용 — FRED 시리즈 ${n}개(BLS · BEA · 미 노동부, FRED 경유)`),
      parts.length ? el("p", { class: "source-link" }, ...parts) : null,
      v.series.length ? el("ul", { class: "lp-list" }, ...v.series.map(s => el("li", {}, `${s.series} · ${s.title} — 마지막 관측 ${s.last || "없음"}` +
        (FETCHED[s.fetched] ? ` · ${FETCHED[s.fetched]}` : "")))) : null,
      v.cites.length ? el("div", { class: "notices lp-cites" }, el("p", {}, "권장 인용:"), ...v.cites.map(s => el("p", {}, s.citation))) : null);
  }
  function asofLine(v, now) {
    const t = num(now) ? now : now && typeof now.getTime === "function" && num(now.getTime()) ? now.getTime() : Date.now();
    const today = new Date(t).toISOString().slice(0, 10);
    const age = Math.round((Date.parse(today + "T00:00:00Z") - Date.parse(v.asof + "T00:00:00Z")) / 864e5);
    return age > STALE_DAYS ? el("p", { class: "muted lp-old" }, `마지막 계산 ${v.asof} — 오래됨`)
      : el("p", { class: "muted lp-asof" }, `${v.asof} 계산 · 문턱 ${v.fixed} 고정`);
  }
  function build(v, now) {
    return [
      el("div", { class: "group-heading" }, el("h3", { id: "lp-ref-title" }, TITLE), el("p", {}, el("span", { class: "reference-label" }, CHIP))),
      el("div", { class: "panel lp" },
        el("p", { class: "lp-label" }, LABEL),
        asofLine(v, now),
        el("p", { class: "muted" }, ABOUT),
        ...summary(v),
        gridBlock(v),
        ...(v.current ? [].concat(legsBlock(v)) : []),
        inflationLine(v),
        historyBlock(v),
        expectedBlock(v),
        defsBlock(v),
        notesBlock(v),
        citeBox(v),
        sourceBlock(v))
    ].filter(Boolean);
  }

  // 자료 파일 전체 → #lp-ref. 쓸 수 없는 파일이면(꼴이 어긋남 · 그리다 깨짐) 아무것도 바꾸지 않고 false. now(밀리초 · Date)는 시험용
  function render(d, now) {
    const wrap = document.getElementById("lp-ref");
    if (!wrap) return false;
    try {
      const v = parse(d);
      if (!v) return false;
      wrap.replaceChildren(...build(v, now));
      return true;
    } catch (e) {
      return false;
    }
  }

  return Object.freeze({ render, LABEL, CHIP, TITLE, ABOUT, CELLS, P_GRID, MIXED, BAND_WORD, MOM_WORD, L_STATES, L_ORDER, P_STATES,
    CONSTANTS, EXCLUDED, HOLDOUT_MARK, STALE_DAYS, SERIES, BANNED_WORDS, NOT_FORECAST, PEAK, GROUPS, near, dash });
})();
