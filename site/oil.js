/* 유가·에너지 참고 — data/oil.json(scripts/oil_fetch.py)을 그린다 (2026-10-30). 이 사이트의 규칙 점검에 쓰지 않는 숫자 묶음이다.
   두 곳: 물가 묶음의 참고 카드(#oil-slot — index.html의 renderPublic이 물가 묶음 아래에 둔다) · 한국 시장 화면의 한 줄(#korea-oil).
   index.html의 el() · link()를 쓴다(부를 때 이미 정의돼 있다). 글자는 전부 el()의 텍스트로만 넣는다(자료를 HTML로 해석하지 않는다).
   카드 이름·안내·정의 문구는 이 파일에 정해 둔 것이고, 칸의 숫자 줄·덧붙이는 줄은 자료 파일에 정해 둔 문구다(그 스크립트가 숫자로 만든다).
   형식이 어긋났거나 고지(notices)가 없는 칸은 숫자를 싣지 않고 '미수신(까닭)' 또는 '자료 없음' 한 줄로 둔다.
   자료 파일이 없으면(첫 자동 실행 전) 아무것도 그리지 않는다. 바깥 요청은 없다. */
"use strict";
window.OilEnergy = (() => {
  // 카드의 칸 차례 — 자료 파일의 order에서 korea(한국 시장 화면)를 뺀 것과 같다(scripts/test_oil_fetch.py가 견준다)
  const CARD = ["crude", "base", "products", "cracks", "spread", "cpi", "bei", "state"];
  // 자료 파일의 실패 사유 — 이 목록의 글만 싣는다(scripts/oil_fetch.py의 REASONS와 같다 — 테스트가 견준다)
  const REASONS = ["수신 실패", "수신 실패 · 묵은 캐시는 싣지 않음", "계산할 자료가 모자람", "받은 자료가 직전 자료보다 오래됨"];
  const LABEL = "참고 — 유가·금리 예측 아님";
  const ABOUT = "유가가 물가로 실리는 길목(원유 · 소매 휘발유·경유 · 정제 마진 · CPI 에너지 · 기대인플레이션)의 공개 통계와 그 산술입니다. " +
    "규칙 수에 들지 않는 참고 숫자입니다.";
  // 상태 줄 바로 아래 — 자료 파일과 상관없이 늘 함께 나간다(정의 없이 이름만 나가지 않게)
  const STATE_NOTE = "상태 이름(오름·보합·내림)은 위의 고정된 정의로 지난 석 달을 적은 것입니다. 유가나 금리를 예측하지 않습니다.";
  const GUIDE = [
    ["13주 · 전년비", "13주 변화는 91일 전, 전년비는 1년 전 같은 날(휴일이면 그 전 마지막 관측)과 견줍니다. 소매 가격은 주간 자료입니다."],
    ["가격이 그대로일 때", "최근 20영업일 평균 가격이 앞으로도 같다고 둔 산술입니다. 달마다 1년 전 같은 달의 월평균(관측 10일 이상)과 견줘 " +
      "전년비를 냅니다. 1년 전 가격이 많이 올랐던 달이 기준이 되면, 가격이 그대로여도 전년비는 크게 낮아집니다. 이번 달보다 30%p 넘게 " +
      "낮아지는 첫 달을 '기저 절벽'으로 적습니다."],
    ["정제 마진", "3-2-1은 원유 3배럴로 휘발유 2배럴과 경유 1배럴을 만든다고 본 마진입니다: (뉴욕항 휘발유 × 2 + 뉴욕항 초저유황 경유) ÷ 3 − WTI. " +
      "제품 값은 갤런당 달러 × 42(배럴). 제품 쪽이 빠듯하면 원유 값이 멈춰도 CPI·PPI로 실릴 수 있습니다."],
    ["Brent − WTI", "북해(해상 운송) 원유와 미국 내륙 원유의 차입니다. 벌어지면 미국 밖 원유가 미국 원유보다 상대적으로 비싸졌다는 뜻이고, " +
      "좁혀지면 그 반대입니다. 원인은 가리지 않습니다."],
    ["5년 뒤 5년", "5년·10년 명목 국채와 TIPS 금리로 계산한, 5년 뒤부터 5년 동안의 기대인플레이션입니다. 유가가 앞쪽 5년에만 실리는지, 먼 쪽까지 " +
      "움직이는지 나란히 봅니다."],
    ["유가 방향 상태", "Brent 현물 월평균의 3개월 로그 변화가 +10%를 넘으면 오름, −10%보다 낮으면 내림, 그 사이면 보합입니다(경계값은 보합). " +
      "상태·전년비는 관측 10일 이상인 마지막 달, 기저 절벽은 마지막 관측의 달부터 잽니다(달 초에는 두 달이 다를 수 있어 줄에 둘 다 적습니다). " +
      "지난 석 달을 적은 설명일 뿐이고, 운영자가 1990년 이후 자료로 재 본 바로는 유가의 3개월 추세가 다음 3개월로 이어지지 않았습니다."],
    ["Brent × 원/달러", "한국 시장 화면에 한 줄로 싣습니다. Brent 월평균 × 원/달러 월평균의 전년비를 달러 유가 몫과 환율 몫으로 나눕니다(두 로그 " +
      "변화의 비율로 나눠 합이 전년비와 같습니다)."]
  ];
  const DAY = /^\d{4}-\d{2}-\d{2}$/;
  const texts = v => (Array.isArray(v) ? v : []).filter(x => typeof x === "string" && x);
  const isObj = v => v && typeof v === "object" && !Array.isArray(v);
  const pct1 = v => {                // 그래프 값 — 숫자 줄과 같은 소수 한 자리(반올림해 0이면 부호 없이)
    const s = v.toFixed(1);
    return (Number(s) === 0 ? "0.0" : (v > 0 ? "+" : "") + s) + "%";
  };

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
  function chart(spec) {
    if (!spec || !window.MacroCharts) return null;
    try { return window.MacroCharts.lineChart(spec, { height: 190, caption: false, notices: false, format: pct1 }); }
    catch (e) { return null; }
  }
  function row(it, key) {
    const name = isObj(it) && typeof it.name === "string" && it.name ? it.name : key;
    if (!usable(it, key))
      return el("div", { class: "oil-row" }, el("p", { class: "oil-name" }, el("strong", {}, name), " — ", missing(it)));
    return el("div", { class: "oil-row" + (key === "state" ? " oil-state" : "") },
      el("p", { class: "oil-name" }, el("strong", {}, name), " ", el("small", {}, it.date)),
      el("p", { class: "oil-num" }, it.line),
      ...texts(it.extra).map(t => el("p", { class: "muted" }, t)),
      key === "state" ? el("p", { class: "oil-note" }, STATE_NOTE) : null,
      stale(it),
      key === "base" ? chart(it.chart) : null);
  }
  // 출처 — 칸마다의 FRED 시리즈 링크(link()는 FRED 주소만 링크로 건다)와 권장 인용은 자료 파일(sources[].citation)에
  function sourceLine(items) {
    const seen = new Map();
    for (const k of [...CARD, "korea"]) {
      const it = items[k];
      if (!usable(it, k)) continue;
      for (const s of Array.isArray(it.sources) ? it.sources : [])
        if (isObj(s) && typeof s.series === "string" && /^[A-Z0-9]+$/.test(s.series) && !seen.has(s.series)) seen.set(s.series, s.url);
    }
    if (!seen.size) return null;
    const parts = [...seen].flatMap(([sid, url], i) => (i ? [" · ", link(sid, url)] : [link(sid, url)]));
    return el("p", { class: "source-link" }, "자료(FRED 경유, EIA · BLS · 연준 · 세인트루이스 연은): ", ...parts);
  }

  function card(d) {
    const items = d.items, notices = [];
    for (const k of CARD) if (usable(items[k], k)) for (const t of texts(items[k].notices)) if (!notices.includes(t)) notices.push(t);
    return el("article", { class: "oil-card", "aria-label": "유가·에너지 참고" },
      el("h3", {}, "유가·에너지", el("span", { class: "reference-label" }, LABEL)),
      el("p", { class: "muted" }, ABOUT + (typeof d.notice === "string" && d.notice ? " " + d.notice : "")),
      ...CARD.map(k => row(items[k], k)),
      el("details", { class: "rule-detail rule-guide" }, el("summary", {}, "읽는 법 — 정의"),
        ...GUIDE.map(([head, text]) => el("p", {}, el("strong", {}, head), " · ", text))),
      notices.length ? el("div", { class: "notices" }, ...notices.map(t => el("p", {}, t))) : null,
      sourceLine(items));
  }

  // 한국 시장 화면의 한 줄 — Brent × 원/달러 전년비와 그 나눔. 칸이 없으면 감춘 채 두고, 숫자를 싣지 못하는 칸은
  // 카드 줄처럼 '미수신(까닭)' 또는 '자료 없음' 한 줄로 둔다(직전 값이 없는 첫 실패도 보이게)
  function korea(it) {
    const box = document.getElementById("korea-oil");
    if (!box) return false;
    if (!isObj(it)) { box.hidden = true; return false; }
    const name = () => el("strong", {}, "Brent × 원/달러");
    if (!usable(it, "korea")) {
      box.replaceChildren(el("p", { class: "oil-name" }, name(), " ", el("span", { class: "reference-label" }, LABEL),
        " — ", missing(it)));
      box.hidden = false;
      return false;
    }
    box.replaceChildren(...[                          // replaceChildren은 null을 글자로 넣는다 — 빈 칸은 걸러 낸다
      el("p", { class: "oil-name" }, name(), " ", el("span", { class: "reference-label" }, LABEL)),
      el("p", { class: "oil-num" }, it.line),
      ...texts(it.extra).map(t => el("p", { class: "muted" }, t)),
      stale(it),
      el("p", { class: "muted" }, "자료: EIA(Brent) · 연준(원/달러), FRED 경유 · 월평균·전년비·나눔은 이 사이트의 계산값 · 규칙 점검에 쓰지 않습니다.")
    ].filter(Boolean));
    box.hidden = false;
    return true;
  }

  // 자료 파일 전체 → 두 곳. 카드에 그린 칸이 하나도 없으면 카드를 두지 않고 false
  function render(d) {
    if (!isObj(d) || !isObj(d.items)) return false;
    const items = d.items;
    try { korea(items.korea); } catch (e) { /* 한 줄이 깨져도 카드는 그린다 */ }
    const slot = document.getElementById("oil-slot");
    if (!slot || !CARD.some(k => usable(items[k], k))) return false;
    slot.replaceChildren(card(d));
    return true;
  }

  return Object.freeze({ render, CARD, REASONS, LABEL, STATE_NOTE });
})();
