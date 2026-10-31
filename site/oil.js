/* 유가·에너지 참고 — data/oil.json(scripts/oil_fetch.py)을 그린다 (2026-10-30). 이 사이트의 규칙 점검에 쓰지 않는 숫자 묶음이다.
   두 곳: 물가 묶음의 참고 카드(#oil-slot — index.html의 renderPublic이 물가 묶음 아래에 둔다) · 한국 시장 화면의 줄(#korea-oil —
   Brent × 원/달러와 두바이 × 원/달러, 두바이 줄은 IMF 저작권 고지와 함께).
   index.html의 el() · link()를 쓴다(부를 때 이미 정의돼 있다). 글자는 전부 el()의 텍스트로만 넣는다(자료를 HTML로 해석하지 않는다).
   카드 이름·안내·정의 문구는 이 파일에 정해 둔 것이고, 칸의 숫자 줄·덧붙이는 줄은 자료 파일에 정해 둔 문구다(그 스크립트가 숫자로 만든다).
   형식이 어긋났거나 고지(notices)가 없는 칸은 숫자를 싣지 않고 '미수신(까닭)' 또는 '자료 없음' 한 줄로 둔다.
   자료 파일이 없으면(첫 자동 실행 전) 아무것도 그리지 않는다. 바깥 요청은 없다.
   카드 머리 안내는 ABOUT 하나(합니다체)다 — 자료 파일의 notice(한다체, 같은 뜻)는 겹쳐 싣지 않는다. 인용이 필요한 자료(licence
   'citation-required' — 세인트루이스 연은 T5YIE·T5YIFR은 카드에, IMF 두바이 POILDUBUSDM은 한국 시장 줄에)는 그 줄을 그렸을 때
   FRED 권장 인용(sources[].citation)을 글자로 함께 싣는다(고지가 약속한 대로). */
"use strict";
window.OilEnergy = (() => {
  // 카드의 칸 차례 — 자료 파일의 order에서 한국 시장 화면의 칸(KOREA)을 뺀 것과 같다(scripts/test_oil_fetch.py가 견준다)
  const CARD = ["crude", "base", "products", "cracks", "spread", "cpi", "i4", "bei", "state", "supply"];
  const KOREA = ["korea", "dubai"];
  const KOREA_NAME = { korea: "Brent × 원/달러", dubai: "두바이 × 원/달러" };
  // 자료 파일의 실패 사유 — 이 목록의 글만 싣는다(scripts/oil_fetch.py의 REASONS와 같다 — 테스트가 견준다)
  const REASONS = ["수신 실패", "수신 실패 · 묵은 캐시는 싣지 않음", "계산할 자료가 모자람", "받은 자료가 직전 자료보다 오래됨"];
  const LABEL = "참고 — 유가·금리 예측 아님";
  // 카드 머리 안내 — oil_fetch.NOTICE의 뜻을 모두 담는다(테스트가 견준다). 자료 파일의 notice는 따로 싣지 않는다
  const ABOUT = "유가가 물가로 실리는 길목(원유 · 소매 휘발유·경유 · 정제 마진 · CPI 에너지 · 기대인플레이션)의 공개 통계와 그 산술입니다. " +
    "규칙 수에 들지 않는 참고 숫자이고, 유가나 금리를 예측하지 않습니다.";
  // 상태 줄 바로 아래 — 자료 파일과 상관없이 늘 함께 나간다(정의 없이 이름만 나가지 않게)
  const STATE_NOTE = "상태 이름(오름·보합·내림)은 위의 고정된 정의로 지난 석 달을 적은 것입니다. 유가나 금리를 예측하지 않습니다.";
  const GUIDE = [
    ["13주 · 전년비", "13주 변화는 91일 전, 전년비는 1년 전 같은 날(휴일이면 그 전 마지막 관측)과 견줍니다. 소매 가격은 주간 자료입니다."],
    ["실질 WTI 분위", "WTI 월평균(관측 10일 이상인 달)을 같은 달 CPI 전체로 나눈 값이 1986년 이후 달 가운데 어디쯤인지입니다. " +
      "p62는 62%의 달이 이 값 이하라는 뜻입니다. 명목은 나누지 않은 월평균으로 같은 달들에서 잽니다. CPI가 아직 없는 달은 3개월 안의 마지막 CPI로 나눕니다."],
    ["이번 달 평균", "소매 휘발유·경유의 마지막 관측이 든 달의 주간 값 평균을 지난달 평균과 견줍니다(계절조정 없음). 달 초에는 한두 주뿐입니다."],
    ["가격이 그대로일 때", "최근 20영업일 평균 가격이 앞으로도 같다고 둔 산술입니다. 달마다 1년 전 같은 달의 월평균(관측 10일 이상)과 견줘 " +
      "전년비를 냅니다. 1년 전 가격이 많이 올랐던 달이 기준이 되면, 가격이 그대로여도 전년비는 크게 낮아집니다. 이번 달보다 30%p 넘게 " +
      "낮아지는 첫 달을 '기저 절벽'으로 적습니다."],
    ["정제 마진", "3-2-1은 원유 3배럴로 휘발유 2배럴과 경유 1배럴을 만든다고 본 마진입니다: (뉴욕항 휘발유 × 2 + 뉴욕항 초저유황 경유) ÷ 3 − WTI. " +
      "제품 값은 갤런당 달러 × 42(배럴). 제품 쪽이 빠듯하면 원유 값이 멈춰도 CPI·PPI로 실릴 수 있습니다."],
    ["Brent − WTI", "북해(해상 운송) 원유와 미국 내륙 원유의 차입니다. 벌어지면 미국 밖 원유가 미국 원유보다 상대적으로 비싸졌다는 뜻이고, " +
      "좁혀지면 그 반대입니다. 원인은 가리지 않습니다."],
    ["I4 · 물가 꼬리표", "I4는 CPI 전체와 근원의 3개월 연율 차입니다. '공급형(에너지)'는 근원 PCE 물가 상태가 P+이고 그 달 I4가 +1.0%p 이상일 때, " +
      "'에너지 하락'은 그 달 I4가 -1.0%p 이하일 때 붙습니다. 물가 상태(P+ · P0 · Pd · P−)는 근원 PCE 전년비 3개월 평균의 띠(높음 · 중간 · 낮음)와 " +
      "모멘텀(6개월 연율 − 전년비: 가속 · 보통 · 둔화)을 맞춘 칸으로, 운영자가 2026-10-14에 고정한 측정 정의입니다. 칸마다의 경계는 줄 아래에 적습니다."],
    ["5년 뒤 5년", "5년·10년 명목 국채와 TIPS 금리로 계산한, 5년 뒤부터 5년 동안의 기대인플레이션입니다. 유가가 앞쪽 5년에만 실리는지, 먼 쪽까지 " +
      "움직이는지 나란히 봅니다."],
    ["유가 방향 상태", "Brent 현물 월평균의 3개월 로그 변화가 +10%를 넘으면 오름, −10%보다 낮으면 내림, 그 사이면 보합입니다(경계값은 보합). " +
      "상태·전년비는 관측 10일 이상인 마지막 달, 기저 절벽은 마지막 관측의 달부터 잽니다(달 초에는 두 달이 다를 수 있어 줄에 둘 다 적습니다). " +
      "지난 석 달을 적은 설명일 뿐이고, 운영자가 1990년 이후 자료로 재 본 바로는 유가의 3개월 추세가 다음 3개월로 이어지지 않았습니다."],
    ["측정 기록", "상태 줄 끝의 평균은 1990년 이후 상태 달마다 다음 3개월 CPI 에너지 로그 변화를 평균한 운영자 측정 기록입니다(2026-10-30 고정). " +
      "지난 기록이고 예측이 아니며, 다른 칸의 계산에 쓰지 않습니다."],
    ["미국 공급 반응", "연준 산업생산의 석유·가스 시추 지수(계절조정 없음) 같은 달 전년비와 석유·가스 추출 업종의 설비 가동률입니다."],
    ["Brent × 원/달러", "한국 시장 화면에 한 줄로 싣습니다. Brent 월평균 × 원/달러 월평균의 전년비를 달러 유가 몫과 환율 몫으로 나눕니다(두 로그 " +
      "변화의 비율로 나눠 합이 전년비와 같습니다)."],
    ["두바이 × 원/달러", "한국 시장 화면의 Brent 줄 아래에 싣습니다. IMF 두바이 원유 월평균 가격 × 원/달러 월평균의 전년비를 같은 방식으로 나눕니다. " +
      "IMF 자료라 저작권 고지를 함께 싣습니다."]
  ];
  const DAY = /^\d{4}-\d{2}-\d{2}$/;
  // 권장 인용의 꼴 — '…, retrieved from …, October 30, 2026.'(scripts/oil_fetch.py citation). 꼴이 다르면 싣지 않는다
  const CITE = /^[^<>]{1,300}, retrieved from [^<>]{1,300}, [A-Z][a-z]+ \d{1,2}, \d{4}\.$/;
  const CITE_LICENCE = "citation-required";
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
    for (const k of [...CARD, ...KOREA]) {
      const it = items[k];
      if (!usable(it, k)) continue;
      for (const s of Array.isArray(it.sources) ? it.sources : [])
        if (isObj(s) && typeof s.series === "string" && /^[A-Z0-9]+$/.test(s.series) && !seen.has(s.series)) seen.set(s.series, s.url);
    }
    if (!seen.size) return null;
    const parts = [...seen].flatMap(([sid, url], i) => (i ? [" · ", link(sid, url)] : [link(sid, url)]));
    return el("p", { class: "source-link" }, "자료(FRED 경유, EIA · BLS · BEA · 연준 · 세인트루이스 연은 · IMF): ", ...parts);
  }

  // 권장 인용 — keys 가운데 그린 칸의 출처 중 인용이 필요한 것(CITE_LICENCE)만, 시리즈마다 하나(가장 늦게 받은 칸의 것), 줄마다 글자로
  function citeLines(items, keys) {
    const best = new Map();
    for (const k of keys) {
      const it = items[k];
      if (!usable(it, k)) continue;
      const when = typeof it.retrieved === "string" && DAY.test(it.retrieved) ? it.retrieved : "";
      for (const s of Array.isArray(it.sources) ? it.sources : []) {
        if (!isObj(s) || s.licence !== CITE_LICENCE || typeof s.series !== "string" || !/^[A-Z0-9]+$/.test(s.series)) continue;
        if (typeof s.citation !== "string" || !CITE.test(s.citation)) continue;
        const was = best.get(s.series);
        if (!was || when > was.when) best.set(s.series, { when, text: s.citation });
      }
    }
    if (!best.size) return null;
    return el("div", { class: "cite-lines" }, ...[...best.values()].map(x => el("p", { class: "muted" }, "권장 인용: " + x.text)));
  }

  function card(d) {
    const items = d.items, notices = [];   // 머리 안내는 ABOUT만 — 자료 파일의 notice는 같은 뜻의 한다체라 싣지 않는다
    for (const k of CARD) if (usable(items[k], k)) for (const t of texts(items[k].notices)) if (!notices.includes(t)) notices.push(t);
    return el("article", { class: "oil-card", "aria-label": "유가·에너지 참고" },
      el("h3", {}, "유가·에너지", el("span", { class: "reference-label" }, LABEL)),
      el("p", { class: "muted" }, ABOUT),
      ...CARD.map(k => row(items[k], k)),
      el("details", { class: "rule-detail rule-guide" }, el("summary", {}, "읽는 법 — 정의"),
        ...GUIDE.map(([head, text]) => el("p", {}, el("strong", {}, head), " · ", text))),
      notices.length ? el("div", { class: "notices" }, ...notices.map(t => el("p", {}, t))) : null,
      sourceLine(items),
      citeLines(items, CARD));
  }

  // 한국 시장 화면의 줄 — Brent × 원/달러와 두바이 × 원/달러(전년비와 그 나눔). 두 칸이 모두 없으면 감춘 채 두고,
  // 숫자를 싣지 못하는 칸은 카드 줄처럼 '미수신(까닭)' 또는 '자료 없음' 한 줄로 둔다(직전 값이 없는 첫 실패도 보이게).
  // 두바이 줄을 그리면 그 칸의 고지(IMF 저작권)를 함께 싣는다
  function koreaRow(it, key) {
    const name = () => el("strong", {}, KOREA_NAME[key]);
    if (!usable(it, key))
      return [el("p", { class: "oil-name" }, name(), " ", el("span", { class: "reference-label" }, LABEL), " — ", missing(it))];
    return [el("p", { class: "oil-name" }, name(), " ", el("span", { class: "reference-label" }, LABEL)),
      el("p", { class: "oil-num" }, it.line),
      ...texts(it.extra).map(t => el("p", { class: "muted" }, t)),
      stale(it)];
  }
  function korea(items) {
    const box = document.getElementById("korea-oil");
    if (!box) return false;
    const keys = KOREA.filter(k => isObj(items[k]));
    if (!keys.length) { box.hidden = true; return false; }
    const shown = keys.filter(k => usable(items[k], k));
    const notes = [];
    if (shown.includes("dubai"))
      for (const t of texts(items.dubai.notices))
        if (!notes.includes(t) && !(shown.includes("korea") && texts(items.korea.notices).includes(t))) notes.push(t);
    const src = shown.length ? el("p", { class: "muted" }, "자료: EIA(Brent)" + (shown.includes("dubai") ? " · IMF(두바이)" : "") +
      " · 연준(원/달러), FRED 경유 · 월평균·전년비·나눔은 이 사이트의 계산값 · 규칙 점검에 쓰지 않습니다.") : null;
    box.replaceChildren(...[                          // replaceChildren은 null을 글자로 넣는다 — 빈 칸은 걸러 낸다
      ...keys.flatMap(k => koreaRow(items[k], k)),
      src,
      notes.length ? el("div", { class: "notices" }, ...notes.map(t => el("p", {}, t))) : null,
      citeLines(items, shown)                         // 두바이(IMF ©)를 그렸으면 그 권장 인용
    ].filter(Boolean));
    box.hidden = false;
    return shown.length > 0;
  }

  // 자료 파일 전체 → 두 곳. 카드에 그린 칸이 하나도 없으면 카드를 두지 않고 false
  function render(d) {
    if (!isObj(d) || !isObj(d.items)) return false;
    const items = d.items;
    try { korea(items); } catch (e) { /* 한국 줄이 깨져도 카드는 그린다 */ }
    const slot = document.getElementById("oil-slot");
    if (!slot || !CARD.some(k => usable(items[k], k))) return false;
    slot.replaceChildren(card(d));
    return true;
  }

  return Object.freeze({ render, CARD, KOREA, REASONS, LABEL, ABOUT, STATE_NOTE });
})();
