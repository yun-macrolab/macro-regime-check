/* 신용 긴축 참고 — data/credit.json(scripts/credit_fetch.py)과 data/sec.json(scripts/sec_fetch.py)을 그린다 (2026-10-30).
   운영자의 비공개 월간 점검에 있던 [신용 긴축] 줄을 공개한 카드다. 이 사이트의 규칙 점검에 쓰지 않고 금리를 예측하지 않는다.
   단계 정의 바로 뒤에 '신용 스트레스(공개 자료)' 묶음(STRESS — 연준 이사회 EBP · 뉴욕 연은 CMDI)을 둔다: 운영자의 비공개 ICE
   등급별 스프레드 사다리(이용 조건상 공개 불가)를 대신하는 공개 자료라는 한 문장과 두 줄. 자료 파일에 두 칸이 모두 없으면
   (새 칸이 생기기 전 파일) 묶음을 두지 않는다. 고지(EBP 논문 인용·출처 줄·공공 영역, CMDI 뉴욕 연은 출처 표시·계산값 표시·
   관계없음 고지·논문 인용)는 그 칸의 notices로 함께 나간다.
   자리: #credit-slot. index.html의 el() · link()를 쓴다(부를 때 이미 정의돼 있다). 글자는 전부 el()의 텍스트로만 넣는다.
   카드 이름·안내·단계 정의는 이 파일에 정해 둔 것이고(정의는 늘 함께 나간다), 칸의 숫자 줄·덧붙이는 줄은 자료 파일에 정해 둔
   문구다(그 스크립트가 숫자로 만든다). 형식이 어긋났거나 고지(notices)가 없는 칸은 숫자를 싣지 않고 '미수신 — 까닭' 또는
   '자료 없음' 한 줄로 둔다. 기업별 조달 줄은 sec.json의 칸을 먼저 쓰고, 그것이 없으면 credit.json에 옮겨 둔 칸을 쓴다.
   카드 머리 안내는 ABOUT 하나(합니다체)다 — 자료 파일의 notice(한다체, 같은 뜻)는 겹쳐 싣지 않는다. 인용이 필요한 자료
   (licence 'citation-required' — 시카고 연은 NFCI 신용)와 정수 낙폭 %를 싣는 재배포 제한 자료(licence 'restricted' — 두 Nasdaq
   지수, 2026-10-30 운영자 결정)는 FRED 권장 인용(sources[].citation)을 카드 끝에 글자로 싣는다. Nasdaq 저작권 표시는 그 칸의
   고지(notices)로 나간다.
   자료 파일이 없으면(첫 자동 실행 전) 아무것도 그리지 않는다. 바깥 요청은 없다. */
"use strict";
window.CreditCard = (() => {
  // 카드의 칸 차례 — credit.json의 order와 같다(scripts/test_credit_fetch.py가 견준다)
  const CARD = ["stage", "ebp", "cmdi", "cell", "gap", "drawdown", "sec"];
  // 신용 스트레스(공개 자료) 묶음 — credit_fetch.STRESS와 같다(테스트가 견준다)
  const STRESS = ["ebp", "cmdi"];
  // 실패 사유 — 이 목록의 글만 싣는다(credit_fetch.REASONS · sec_fetch.REASONS와 같다 — 테스트가 견준다)
  const REASONS = ["수신 실패", "수신 실패 · 묵은 캐시는 싣지 않음", "계산할 자료가 모자람", "받은 자료가 직전 자료보다 오래됨",
    "SEC 자료 파일을 읽지 못함", "받은 파일의 꼴을 알아보지 못함", "연락처 미설정(SEC_USER_AGENT)", "SEC 거절 · 요청 한도 또는 미신고 도구", "시간 상한 안에 다 받지 못함",
    "연락처 꼴 글이 섞여 쓰지 않음"];
  const LABEL = "참고 — 금리 예측 아님";
  // 카드 머리 안내 — credit_fetch.NOTICE의 뜻을 모두 담는다(테스트가 견준다). 자료 파일의 notice는 따로 싣지 않는다
  const ABOUT = "신용 긴축 단계(규칙 C)와 그 곁의 측정 기록·서술 꼬리표입니다. 운영자의 비공개 월간 점검에 있던 줄을 공개한 것으로, " +
    "이 사이트의 규칙 수에 들지 않습니다. 단계는 정해 둔 문턱으로 지금 숫자를 적은 것이고 예측력은 검증하지 않았습니다. " +
    "측정 기록은 운영자가 과거 자료로 잰 숫자이며 금리를 예측하지 않습니다.";
  // 단계 정의 — 자료 파일과 상관없이 늘 함께 나간다(credit_fetch.STAGE_DEF와 같다 — 테스트가 견준다)
  const STAGE_DEF = "규칙 C(문턱 고정 2026-10-29, 예측력 미검증): S = SLOOS 대·중견기업 C&I 대출 기준 순긴축(%)의 최신 조사, " +
    "N13 = NFCI 신용 하위 지수의 13주 변화, NL = 그 수준. 2단계: S ≥ 24.2 그리고 (N13 ≥ +0.148 또는 NL ≥ +0.183). " +
    "1단계: 그 밖에 S ≥ 10 또는 N13 ≥ +0.077. 0단계: 그 밖. 문턱은 각 시계열의 1990년 이후 분위다(SLOOS p70·p80, " +
    "13주 변화 p80·p90, 수준 p80). SLOOS가 조사월부터 150일, NFCI가 마지막 관측부터 14일을 넘으면 그 계기는 모름으로 두고, " +
    "단계가 그래도 정해지면 적고 아니면 '?'와 가능한 범위를 적는다.";
  const STRESS_NAME = "신용 스트레스(공개 자료)";
  // 묶음 머리 한 문장(합니다체) — 왜 이 두 자료인지
  const STRESS_NOTE = "운영자의 비공개 점검이 보는 ICE 회사채 등급별 스프레드 사다리는 이용 조건(라이선스)상 공개할 수 없어, " +
    "공개 자료인 연준 이사회 초과 채권 프리미엄(EBP)과 뉴욕 연은 회사채 시장 스트레스 지수(CMDI)로 그 자리를 대신합니다.";
  const GUIDE = [
    ["SLOOS", "연준의 은행 대출 담당자 설문(분기)입니다. 대·중견기업 상업·산업 대출의 기준을 조인 은행 비율에서 푼 은행 비율을 뺀 값(%)입니다."],
    ["NFCI 신용", "시카고 연은의 금융 여건 지수 가운데 신용 하위 지수(주간)입니다. 0보다 크면 평균보다 빠듯한 쪽이고, 매주 전 표본으로 다시 추정합니다."],
    ["EBP", "연준 이사회가 매달 전 표본으로 다시 추정해 내는 초과 채권 프리미엄입니다. 회사채 스프레드(GZ 스프레드)에서 발행 기업의 " +
      "부도 위험으로 설명되는 몫을 뺀 나머지를 bp로 적습니다. 같은 파일의 침체 확률 열은 예측 값이라 싣지 않습니다."],
    ["CMDI", "뉴욕 연은의 회사채 시장 스트레스 지수(주간, 0~1)입니다. 발행·유통 시장의 가격·거래 지표를 묶은 것으로 1에 가까울수록 " +
      "시장 기능이 빠듯한 쪽입니다. 매달 마지막 수요일쯤 갱신돼 마지막 값이 5주가량 지난 것일 수 있습니다."],
    ["AI 투자 칸", "투자 축(정보처리 투자/GDP가 1년 전보다 늘었는지)과 조달 축(설비투자가 내부자금보다 얼마나 큰지)을 적은 서술 꼬리표입니다. 금리 방향은 없습니다."],
    ["주가 낙폭", "나스닥100·AI 지수가 252영업일 고점보다 지금 몇 % 아래인지(정수)와 그 구간(10% 안 · 10~20% 아래 · 20% 넘게 " +
      "아래)을 적습니다. 지수 값·고점·수익률은 재배포 제한 자료라 싣지 않고, 저작권 표시와 FRED 권장 인용을 함께 싣습니다."],
    ["기업별 조달", "마이크로소프트·알파벳·아마존·메타·오라클의 SEC 10-Q·10-K 공시에서 영업현금·설비투자·차입·주식 조달을 분기로 나눠 더한 숫자입니다."]
  ];
  const DAY = /^\d{4}-\d{2}-\d{2}$/;
  // 권장 인용의 꼴 — '…, retrieved from …, October 30, 2026.'(scripts/credit_fetch.py citation). 꼴이 다르면 싣지 않는다
  const CITE = /^[^<>]{1,300}, retrieved from [^<>]{1,300}, [A-Z][a-z]+ \d{1,2}, \d{4}\.$/;
  // 권장 인용을 글자로 싣는 이용 조건 — 인용 필요(시카고 연은 NFCI 신용)와 재배포 제한(Nasdaq 지수 — 정수 낙폭 %를 싣는다)
  const CITE_LICENCES = ["citation-required", "restricted"];
  const FRED_SERIES = /^https:\/\/fred\.stlouisfed\.org\/series\/[A-Z0-9]+$/;
  const texts = v => (Array.isArray(v) ? v : []).filter(x => typeof x === "string" && x);
  const isObj = v => v && typeof v === "object" && !Array.isArray(v);

  function usable(it, key) {
    return isObj(it) && it.key === key && typeof it.date === "string" && DAY.test(it.date) &&
      Number.isFinite(Date.parse(it.date + "T00:00:00Z")) && typeof it.line === "string" && it.line !== "" &&
      texts(it.notices).length > 0;
  }
  function missing(it) {             // 숫자를 싣지 못하는 칸의 한 줄 — 사유는 정해 둔 목록 안의 것만
    const why = isObj(it) && REASONS.includes(it.error) ? it.error : "";
    return why ? `미수신 — ${why}` : "자료 없음";
  }
  function stale(it) {
    if (it.stale !== true) return null;
    const since = typeof it.failed_since === "string" && DAY.test(it.failed_since) ? ` (${it.failed_since}부터)` : "";
    return el("p", { class: "credit-late" }, "이번 갱신의 값을 싣지 못해 직전에 받은 값을 싣습니다" + since);
  }
  function row(it, key) {
    const name = isObj(it) && typeof it.name === "string" && it.name ? it.name : key;
    if (!usable(it, key))
      return el("div", { class: "credit-row" }, el("p", { class: "credit-name" }, el("strong", {}, name), " — ", missing(it)));
    const detail = texts(it.detail);
    return el("div", { class: "credit-row" + (key === "stage" ? " credit-stage" : "") },
      el("p", { class: "credit-name" }, el("strong", {}, name), " ", el("small", {}, it.date)),
      el("p", { class: "credit-num" }, it.line),
      ...texts(it.extra).map(t => el("p", { class: "muted" }, t)),
      stale(it),
      detail.length ? el("details", { class: "rule-detail" }, el("summary", {}, "회사별"),
        ...detail.map(t => el("p", { class: "muted" }, t))) : null);
  }
  // 출처 — FRED 시리즈 링크(link()는 FRED 주소만 링크로 건다)와 권장 인용은 자료 파일(sources[].citation)에, SEC는 출처 글만.
  // FRED 밖 자료(EBP · CMDI)는 이 줄에 넣지 않는다 — 출처 표시는 그 칸의 고지(notices)로 나간다
  function sourceLine(items) {
    const seen = new Map();
    let sec = false;
    for (const k of CARD) {
      const it = items[k];
      if (!usable(it, k)) continue;
      for (const s of Array.isArray(it.sources) ? it.sources : []) {
        if (!isObj(s) || typeof s.series !== "string") continue;
        if (s.series === "EDGAR") sec = true;
        else if (/^[A-Z0-9]+$/.test(s.series) && typeof s.url === "string" && FRED_SERIES.test(s.url) && !seen.has(s.series))
          seen.set(s.series, s.url);
      }
    }
    if (!seen.size && !sec) return null;
    const parts = [...seen].flatMap(([sid, url], i) => (i ? [" · ", link(sid, url)] : [link(sid, url)]));
    return el("p", { class: "source-link" },
      seen.size ? "자료(FRED 경유, 연준 · 시카고 연은 · BEA · Nasdaq): " : "", ...parts,
      sec ? (seen.size ? " · " : "") + "Source: SEC EDGAR XBRL API (data.sec.gov); site calculations" : "");
  }

  // 권장 인용 — 그린 칸의 FRED 출처 가운데 CITE_LICENCES의 것만, 시리즈마다 하나(가장 늦게 받은 칸의 것), 줄마다 글자로
  function citeLines(items) {
    const best = new Map();
    for (const k of CARD) {
      const it = items[k];
      if (!usable(it, k)) continue;
      const when = typeof it.retrieved === "string" && DAY.test(it.retrieved) ? it.retrieved : "";
      for (const s of Array.isArray(it.sources) ? it.sources : []) {
        if (!isObj(s) || !CITE_LICENCES.includes(s.licence) || typeof s.series !== "string" || !/^[A-Z0-9]+$/.test(s.series) ||
          typeof s.url !== "string" || !FRED_SERIES.test(s.url)) continue;
        if (typeof s.citation !== "string" || !CITE.test(s.citation)) continue;
        const was = best.get(s.series);
        if (!was || when > was.when) best.set(s.series, { when, text: s.citation });
      }
    }
    if (!best.size) return null;
    return el("div", { class: "cite-lines" }, ...[...best.values()].map(x => el("p", { class: "muted" }, "권장 인용: " + x.text)));
  }

  // 신용 스트레스(공개 자료) 묶음 — 머리 한 문장과 EBP · CMDI 줄. 자료 파일에 두 칸이 모두 없으면 두지 않는다(null)
  function stress(items) {
    if (!STRESS.some(k => isObj(items[k]))) return null;
    return el("div", { class: "credit-row credit-group" },
      el("p", { class: "credit-name" }, el("strong", {}, STRESS_NAME)),
      el("p", { class: "muted" }, STRESS_NOTE),
      ...STRESS.map(k => row(items[k], k)));
  }

  function card(items) {
    const notices = [];
    for (const k of CARD) if (usable(items[k], k)) for (const t of texts(items[k].notices)) if (!notices.includes(t)) notices.push(t);
    const [stageKey] = CARD;
    const rest = CARD.filter(k => k !== stageKey && !STRESS.includes(k));
    return el("article", { class: "credit-card", "aria-label": "신용 긴축 참고" },
      el("h3", {}, "신용 긴축", el("span", { class: "reference-label" }, LABEL)),
      el("p", { class: "muted" }, ABOUT),
      row(items[stageKey], stageKey),
      el("p", { class: "credit-def" }, STAGE_DEF),
      stress(items),
      ...rest.map(k => row(items[k], k)),
      el("details", { class: "rule-detail rule-guide" }, el("summary", {}, "읽는 법 — 정의"),
        ...GUIDE.map(([head, text]) => el("p", {}, el("strong", {}, head), " · ", text))),
      notices.length ? el("div", { class: "notices" }, ...notices.map(t => el("p", {}, t))) : null,
      sourceLine(items),
      citeLines(items));
  }

  // credit.json(d)과 sec.json(sec) → 카드 하나. 그린 칸이 하나도 없으면 카드를 두지 않고 false
  function render(d, sec) {
    if (!isObj(d) || !isObj(d.items)) return false;
    const items = Object.assign({}, d.items);
    const f = isObj(sec) && isObj(sec.items) ? sec.items.funding : null;
    if (usable(f, "funding")) items.sec = Object.assign({}, f, { key: "sec" });
    const slot = document.getElementById("credit-slot");
    if (!slot || !CARD.some(k => usable(items[k], k))) return false;
    slot.replaceChildren(card(items));
    return true;
  }

  return Object.freeze({ render, CARD, STRESS, REASONS, LABEL, ABOUT, STAGE_DEF, STRESS_NAME, STRESS_NOTE });
})();
