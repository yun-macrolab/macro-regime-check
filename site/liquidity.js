/* 지준·재정 참고 — data/liquidity.json(scripts/liquidity_fetch.py)을 그린다 (2026-10-30). 이 사이트의 규칙 점검에 쓰지 않는 숫자 묶음이다.
   한 곳: 유동성 묶음의 참고 카드(#liquidity-slot — index.html의 renderPublic이 유동성 묶음 아래에 둔다).
   index.html의 el() · link()를 쓴다(부를 때 이미 정의돼 있다). 글자는 전부 el()의 텍스트로만 넣는다(자료를 HTML로 해석하지 않는다).
   카드 이름·안내·정의·측정 기록 문구는 이 파일에 정해 둔 것이고, 칸의 숫자 줄·덧붙이는 줄은 자료 파일에 정해 둔 문구다(그 스크립트가 숫자로 만든다).
   형식이 어긋났거나 고지(notices)가 없는 칸은 숫자를 싣지 않고 '미수신(까닭)' 또는 '자료 없음' 한 줄로 둔다.
   자료 파일이 없으면(첫 자동 실행 전) 아무것도 그리지 않는다. 바깥 요청은 없다. 겉모양은 유가 카드의 클래스를 함께 쓴다.
   카드 머리 안내는 ABOUT 하나(합니다체)다 — 자료 파일의 notice(한다체, 같은 뜻)는 겹쳐 싣지 않는다. */
"use strict";
window.LiquidityCard = (() => {
  // 카드의 칸 차례 — 자료 파일의 order와 같다(scripts/test_liquidity_fetch.py가 견준다)
  const CARD = ["reserves", "rule", "fiscal"];
  // 자료 파일의 실패 사유 — 이 목록의 글만 싣는다(scripts/liquidity_fetch.py의 REASONS와 같다 — 테스트가 견준다)
  const REASONS = ["수신 실패", "수신 실패 · 묵은 캐시는 싣지 않음", "계산할 자료가 모자람", "받은 자료가 직전 자료보다 오래됨"];
  const LABEL = "참고 — 판정 없음";
  // 카드 머리 안내 — liquidity_fetch.NOTICE의 뜻을 모두 담는다(테스트가 견준다). 자료 파일의 notice는 따로 싣지 않는다
  const ABOUT = "연준 대차대조표와 미 연방 재정수지 · 이자 지출 · 국채 구성의 공개 통계와 그 산술입니다. 위 규칙 카드 '지준과 통화승수'의 지준/GDP가 " +
    "왜 움직였는지 읽는 재료이고, 규칙 수에 들지 않습니다. 금리나 자금 여건을 예측하지 않습니다.";
  const GUIDE = [
    ["부호는 지준 쪽", "13주 나눔의 숫자는 지준을 늘린 쪽이 +, 줄인 쪽이 −입니다. 재무부 현금(TGA)이나 역레포가 늘면 그만큼 지준이 줄어 " +
      "−로, 연준이 가진 국채가 늘면 +로 나옵니다. '그 밖'은 나머지(MBS 상환·현금 통화·대출 등)이고, 화면에 보이는 숫자끼리 합이 맞게 " +
      "반올림 차를 받습니다."],
    ["수요일 수준과 주 평균", "나눔은 연준 H.4.1의 수요일 수준끼리 13주(91일) 차를 냅니다. 규칙 카드의 지준/GDP는 주 평균 지준을 써서 " +
      "나눔의 지준과 조금 다릅니다."],
    ["규칙 하한 대비", "규칙 카드와 같은 지준/명목GDP 값에서 규칙의 하한을 뺀 산술입니다. 달러는 그 차에 마지막 분기 명목 GDP를 곱한 " +
      "값입니다. 다른 항목이 그대로일 때 재무부 현금이 그만큼 늘거나 줄면 하한에 닿는다는 크기만 보입니다."],
    ["재정수지 · 이자 · 단기채", "재정수지는 미 재무부 월간 재무제표(MTS)의 12개월 합(적자 −), 이자 지출은 국민계정(분기, 연율), 단기채 비중은 연준 금융계정" +
      "(Z.1, 분기)의 시장성 국채 중 단기채 몫입니다. GDP 대비는 명목 GDP로 나눈 산술입니다."],
    ["측정 기록", "운영자가 2026-10-28에 2025년 이후 자료로 재 본 바로는 지준 변화와 재무부 현금 변화가 거의 반대로 함께 움직였습니다" +
      "(수요일 수준끼리 또는 주 평균끼리 주간 상관 약 −0.8, 4주·13주 약 −0.86~−0.90). 지준의 주간·4주 변화와 10년 금리·기간 프리미엄 " +
      "변화의 상관은 약했습니다(절댓값 0.27 이하). 그래서 이 카드는 규칙 카드를 읽는 재료이고, 금리를 예측하지 않습니다."]
  ];
  const DAY = /^\d{4}-\d{2}-\d{2}$/;
  const texts = v => (Array.isArray(v) ? v : []).filter(x => typeof x === "string" && x);
  const isObj = v => v && typeof v === "object" && !Array.isArray(v);

  function usable(it, key) {
    return isObj(it) && it.key === key && typeof it.date === "string" && DAY.test(it.date) &&
      Number.isFinite(Date.parse(it.date + "T00:00:00Z")) && typeof it.line === "string" && it.line !== "" &&
      texts(it.notices).length > 0;
  }
  function missing(it) {             // 숫자를 싣지 못하는 칸의 한 줄 — 사유는 정해 둔 목록 안의 것만
    const why = isObj(it) && REASONS.includes(it.error) ? it.error : "";
    return why ? `미수신(${why})` : "자료 없음";
  }
  function stale(it) {
    if (it.stale !== true) return null;
    const since = typeof it.failed_since === "string" && DAY.test(it.failed_since) ? ` (${it.failed_since}부터)` : "";
    return el("p", { class: "oil-late" }, "이번 갱신의 값을 싣지 못해 직전에 받은 값을 싣습니다" + since);
  }
  function row(it, key) {
    const name = isObj(it) && typeof it.name === "string" && it.name ? it.name : key;
    if (!usable(it, key))
      return el("div", { class: "oil-row liq-row" }, el("p", { class: "oil-name" }, el("strong", {}, name), " — ", missing(it)));
    return el("div", { class: "oil-row liq-row" },
      el("p", { class: "oil-name" }, el("strong", {}, name), " ", el("small", {}, it.date)),
      el("p", { class: "oil-num" }, it.line),
      ...texts(it.extra).map(t => el("p", { class: "muted" }, t)),
      stale(it));
  }
  // 출처 — 칸마다의 FRED 시리즈 링크(link()는 FRED 주소만 링크로 건다)와 권장 인용은 자료 파일(sources[].citation)에
  function sourceLine(items) {
    const seen = new Map();
    for (const k of CARD) {
      const it = items[k];
      if (!usable(it, k)) continue;
      for (const s of Array.isArray(it.sources) ? it.sources : [])
        if (isObj(s) && typeof s.series === "string" && /^[A-Z0-9]+$/.test(s.series) && !seen.has(s.series)) seen.set(s.series, s.url);
    }
    if (!seen.size) return null;
    const parts = [...seen].flatMap(([sid, url], i) => (i ? [" · ", link(sid, url)] : [link(sid, url)]));
    return el("p", { class: "source-link" }, "자료(FRED 경유, 연준 · 미 재무부 · BEA): ", ...parts);
  }

  function card(d) {
    const items = d.items, notices = [];   // 머리 안내는 ABOUT만 — d.notice는 같은 뜻의 한다체라 싣지 않는다
    for (const k of CARD) if (usable(items[k], k)) for (const t of texts(items[k].notices)) if (!notices.includes(t)) notices.push(t);
    return el("article", { class: "oil-card liq-card", "aria-label": "지준·재정 참고" },
      el("h3", {}, "지준·재정", el("span", { class: "reference-label" }, LABEL)),
      el("p", { class: "muted" }, ABOUT),
      ...CARD.map(k => row(items[k], k)),
      el("details", { class: "rule-detail rule-guide" }, el("summary", {}, "읽는 법 — 정의와 측정 기록"),
        ...GUIDE.map(([head, text]) => el("p", {}, el("strong", {}, head), " · ", text))),
      notices.length ? el("div", { class: "notices" }, ...notices.map(t => el("p", {}, t))) : null,
      sourceLine(items));
  }

  // 자료 파일 전체 → 카드. 그린 칸이 하나도 없으면 카드를 두지 않고 false
  function render(d) {
    if (!isObj(d) || !isObj(d.items)) return false;
    const slot = document.getElementById("liquidity-slot");
    if (!slot || !CARD.some(k => usable(d.items[k], k))) return false;
    slot.replaceChildren(card(d));
    return true;
  }

  return Object.freeze({ render, CARD, REASONS, LABEL, ABOUT });
})();
