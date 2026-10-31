/* 기간 프리미엄 모형 대조 참고 — data/tp.json(scripts/tp_fetch.py)을 그린다 (2026-10-30).
   운영자의 비공개 점검에 있던 기간 프리미엄 줄(주간 Kim-Wright 4주 변화와 운영자 주간 점수 · 월간 ACM과 Kim-Wright 대조)을
   공개한 카드다. 이 사이트의 규칙 점검에 쓰지 않고 금리를 예측하지 않는다.
   자리: #tp-slot. index.html의 el() · link()를 쓴다(부를 때 이미 정의돼 있다). 글자는 전부 el()의 텍스트로만 넣는다.
   카드 이름·안내·점수 안내는 이 파일에 정해 둔 것이고(점수 안내는 주간 줄과 늘 함께 나간다), 칸의 숫자 줄·덧붙이는 줄은
   자료 파일에 정해 둔 문구다(그 스크립트가 숫자로 만든다). 형식이 어긋났거나 고지(notices)가 없는 칸은 숫자를 싣지 않고
   '미수신(까닭)' 또는 '자료 없음' 한 줄로 둔다. 자료 파일이 없으면(첫 자동 실행 전) 아무것도 그리지 않는다. 바깥 요청은 없다.
   카드 머리글은 ABOUT 하나(합니다체)다 — 자료 파일의 notice(자료를 직접 읽는 사람용, 같은 뜻의 한다체)는 되풀이하지 않는다.
   권장 인용(sources[].citation — Kim-Wright 둘은 FRED 'Public Domain: Citation Requested', ACM은 뉴욕 연은 이용약관)은
   출처 줄 아래 한 문단에 글자로 싣는다(고지가 '권장 인용과 함께 싣는다'고 적는 그 인용). */
"use strict";
window.TpCard = (() => {
  // 카드의 칸 차례 — 자료 파일의 order와 같다(scripts/test_tp_fetch.py가 견준다)
  const CARD = ["weekly", "models"];
  // 자료 파일의 실패 사유 — 이 목록의 글만 싣는다(scripts/tp_fetch.py의 REASONS와 같다 — 테스트가 견준다)
  const REASONS = ["수신 실패", "수신 실패 · 묵은 캐시는 싣지 않음", "계산할 자료가 모자람", "받은 자료가 직전 자료보다 오래됨"];
  const LABEL = "참고 — 금리 예측 아님";
  const ABOUT = "10년 기간 프리미엄을 두 모형(Kim-Wright · ACM)으로 견준 측정 기록입니다. 운영자의 비공개 점검에 있던 줄을 " +
    "공개한 것으로, 이 사이트의 규칙 수에 들지 않고 금리를 예측하지 않습니다.";
  // 주간 줄 바로 아래 — 자료 파일과 상관없이 늘 함께 나간다(점수가 정의 없이 나가지 않게)
  const SCORE_NOTE = "운영자 주간 점수는 z를 0 쪽으로 버린 크기에 부호를 뒤집은 값입니다(+는 금리 하락 쪽, −2~+2). " +
    "운영자가 정해 둔 규칙으로 매긴 참고값이고 금리를 예측하지 않습니다.";
  const GUIDE = [
    ["기간 프리미엄", "10년 금리를 '앞으로 10년간 단기금리의 평균 기대'와 '장기물을 들고 있는 대가'로 나눈 뒤쪽입니다. " +
      "시장에서 직접 보이지 않아 모형으로만 나오고, 모형마다 나누는 비율이 다릅니다."],
    ["두 모형", "Kim-Wright(연준 이사회, FRED — 매일 · 약 1주 늦게)는 전문가 설문의 금리 예상치로 기대 경로를 붙잡고, ACM(뉴욕 연은 — " +
      "월말 값 · 약 한 달 늦게)은 국채 수익률의 주성분을 회귀로 씁니다. 수준은 모형마다 체계적으로 달라 변화끼리만 견줍니다."],
    ["4주 변화와 σ", "4주 변화는 마지막 관측과 28일 전(그날 이하 마지막 관측)의 차입니다. σ는 2023년 이후 주마다 마지막 관측으로 낸 " +
      "4주 변화의 표준편차이고, z = 4주 변화 ÷ σ입니다."],
    ["운영자 주간 점수", "−부호(z) × min(2, ⌊|z|⌋)입니다. 평소 크기(1σ) 안의 움직임은 0점이고, 1σ 이상이면 ∓1, 2σ 이상이면 ∓2입니다. " +
      "마지막 관측이 14일보다 오래되면 매기지 않습니다."],
    ["10년 중 몫", "같은 4주의 Kim-Wright 적합 10년 변화 가운데 기간 프리미엄으로 돌린 비율입니다. Kim-Wright에서는 이 비율이 약 절반으로 " +
      "거의 일정해, 기간 프리미엄 점수는 사실상 10년 금리의 4주 추세를 따릅니다. 10년 변화가 10bp 미만이면 비율을 적지 않습니다."],
    ["해석 갈림", "ACM 월말에서 다음 월말까지와 같은 기간의 두 모형 변화를 각자 σ로 나눈 z로 견줍니다. 한쪽만 |z| ≥ 1이거나 둘이 반대 " +
      "방향이면서 두 z의 차이가 0.7 이상이면 '해석 갈림'입니다. 같은 금리 움직임을 한 모형은 기간 프리미엄으로, 다른 모형은 기대 경로로 " +
      "읽은 달이라, 기간 프리미엄 해석을 덜 믿고 정책 기대의 변화와 함께 봅니다."],
    ["12개월 일치도", "최근 12개월 두 모형 월간 변화의 상관과 같은 방향 비율입니다. 상관이 0.6 미만이면 '신뢰 낮음'으로 적습니다 — " +
      "요즘은 기간 프리미엄 해석 자체를 덜 믿을 때라는 뜻입니다."]
  ];
  const DAY = /^\d{4}-\d{2}-\d{2}$/;
  // 권장 인용의 꼴 — '…, retrieved from …, October 30, 2026.'(scripts/tp_fetch.py citation). 꼴이 다르면 싣지 않는다
  const CITE = /^[^<>]{1,300}, retrieved from [^<>]{1,300}, [A-Z][a-z]+ \d{1,2}, \d{4}\.$/;
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
      return el("div", { class: "oil-row tp-row" }, el("p", { class: "oil-name" }, el("strong", {}, name), " — ", missing(it)));
    return el("div", { class: "oil-row tp-row" + (key === "weekly" ? " tp-weekly" : "") },
      el("p", { class: "oil-name" }, el("strong", {}, name), " ", el("small", {}, it.date)),
      el("p", { class: "oil-num" }, it.line),
      key === "weekly" ? el("p", { class: "oil-note" }, SCORE_NOTE) : null,
      ...texts(it.extra).map(t => el("p", { class: "muted" }, t)),
      stale(it));
  }
  // 출처 — 칸마다의 시리즈(link()는 FRED 주소만 링크로 건다 — ACM은 글자로). 권장 인용은 아래 citeLine이 따로 싣는다
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
    return el("p", { class: "source-link" }, "자료(Kim-Wright: 연준 이사회, FRED 경유 · ACM: 뉴욕 연은): ", ...parts);
  }
  // 권장 인용 — 그린 칸의 출처 가운데 인용이 붙은 것만, 시리즈마다 하나(가장 늦게 받은 칸의 것), 한 문단에 글자로
  function citeLine(items) {
    const best = new Map();
    for (const k of CARD) {
      const it = items[k];
      if (!usable(it, k)) continue;
      const when = typeof it.retrieved === "string" && DAY.test(it.retrieved) ? it.retrieved : "";
      for (const s of Array.isArray(it.sources) ? it.sources : []) {
        if (!isObj(s) || typeof s.series !== "string" || !/^[A-Z0-9]+$/.test(s.series)) continue;
        if (typeof s.citation !== "string" || !CITE.test(s.citation)) continue;
        const was = best.get(s.series);
        if (!was || when > was.when) best.set(s.series, { when, text: s.citation });
      }
    }
    if (!best.size) return null;
    return el("div", { class: "notices tp-cite" }, el("p", {}, "권장 인용: " + [...best.values()].map(x => x.text).join(" ")));
  }

  function card(d) {
    const items = d.items, notices = [];
    for (const k of CARD) if (usable(items[k], k)) for (const t of texts(items[k].notices)) if (!notices.includes(t)) notices.push(t);
    return el("article", { class: "oil-card tp-card", "aria-label": "기간 프리미엄 모형 대조 참고" },
      el("h3", {}, "기간 프리미엄 모형 대조", el("span", { class: "reference-label" }, LABEL)),
      el("p", { class: "muted" }, ABOUT),
      ...CARD.map(k => row(items[k], k)),
      el("details", { class: "rule-detail rule-guide" }, el("summary", {}, "읽는 법 — 정의"),
        ...GUIDE.map(([head, text]) => el("p", {}, el("strong", {}, head), " · ", text))),
      notices.length ? el("div", { class: "notices" }, ...notices.map(t => el("p", {}, t))) : null,
      sourceLine(items),
      citeLine(items));
  }

  // 자료 파일 전체 → #tp-slot. 그린 칸이 하나도 없으면 카드를 두지 않고 false
  function render(d) {
    if (!isObj(d) || !isObj(d.items)) return false;
    const slot = document.getElementById("tp-slot");
    if (!slot || !CARD.some(k => usable(d.items[k], k))) return false;
    slot.replaceChildren(card(d));
    return true;
  }

  return Object.freeze({ render, CARD, REASONS, LABEL, ABOUT, SCORE_NOTE });
})();
