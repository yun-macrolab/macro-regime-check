/* AI 투자 참고 — data/ai_invest.json(scripts/ai_invest_fetch.py)을 그린다 (2026-10-27). 이 사이트의 규칙 판정에 쓰지 않는 공개 통계 묶음이다.
   index.html의 el() · chartFigure()를 쓴다(부를 때 이미 정의돼 있다). 글자는 전부 el()의 텍스트로만 넣는다(자료를 HTML로 해석하지 않는다).
   채널 이름·안내 문구는 이 파일에 정해 둔 것이고, 칸의 숫자 줄·덧붙이는 줄은 자료 파일에 정해 둔 문구다(그 스크립트가 숫자로 만든다).
   형식이 어긋난 칸, 고지(notices)가 한 줄도 없는 칸은 숫자를 싣지 않고 '자료 없음' 한 줄로 둔다. 바깥 요청은 없다. */
"use strict";
window.AiInvest = (() => {
  // 화면 차례 — 자료 파일의 order와 같다(scripts/test_ai_invest_fetch.py가 견준다)
  const CHANNELS = [
    ["invest", "실물 투자", "데이터센터에 들어가는 장비·소프트웨어·건물 투자의 크기와 속도입니다.",
      ["ict_share", "tech_orders", "office_cons"]],
    ["finance", "조달", "기업이 투자를 내부 자금으로 하는지, 바깥에서 빌려서 하는지의 총량입니다.", ["financing"]],
    ["power", "전력 가격", "데이터센터 전력 수요가 전기 요금에 실리는지 봅니다.", ["power"]],
    ["rates", "금리 쪽 결과", "장기 금리 쪽에 남는 숫자입니다. 원인을 가리지 않습니다.", ["curve_30_10"]],
    ["corr", "주식과 미 10년 금리의 상관",
      "AI 관련 주식이 금리와 같은 방향으로 움직이는지 봅니다. 양(+)이면 주가와 금리가 같은 방향, 국채 가격으로는 반대 방향입니다. " +
      "지수 값은 재배포가 제한돼 싣지 않고 상관만 싣습니다.", ["corr60", "corr20", "partial60"]]
  ];
  const TEASER = ["ict_share", "financing", "power", "curve_30_10", "corr60"];   // 첫 화면에는 채널마다 첫 칸의 숫자 줄만
  const DAY = /^\d{4}-\d{2}-\d{2}$/;
  const texts = v => (Array.isArray(v) ? v : []).filter(x => typeof x === "string" && x);
  const isObj = v => v && typeof v === "object" && !Array.isArray(v);

  // 그릴 수 있는 칸인가 — 날짜·숫자 줄·고지가 있어야 한다(숫자만 고지 없이 나가지 않게)
  function usable(it, key) {
    return isObj(it) && it.key === key && typeof it.date === "string" && DAY.test(it.date) &&
      Number.isFinite(Date.parse(it.date + "T00:00:00Z")) && typeof it.line === "string" && it.line !== "" &&
      texts(it.notices).length > 0;
  }

  function item(it, key) {
    const name = isObj(it) && typeof it.name === "string" && it.name ? it.name : key;
    if (!usable(it, key)) return el("div", { class: "ai-item" }, el("p", { class: "ai-name" }, el("strong", {}, name), " — 자료 없음"));
    const since = typeof it.failed_since === "string" && DAY.test(it.failed_since) ? ` (${it.failed_since}부터)` : "";
    return el("div", { class: "ai-item panel" },
      el("p", { class: "ai-name" }, el("strong", {}, name)),
      el("p", { class: "ai-num" }, it.line),
      ...texts(it.extra).map(t => el("p", { class: "muted" }, t)),
      it.stale === true ? el("p", { class: "ai-late" }, "이번 갱신에서 받지 못해 직전에 받은 값을 싣습니다" + since) : null,
      chartFigure(it.chart, 190, false),
      el("div", { class: "notices" }, ...texts(it.notices).map(t => el("p", {}, t))));
  }

  // 자료 파일 전체 → 화면 두 곳(첫 화면 요약 · 'AI 투자' 화면). 그린 칸이 하나도 없으면 false
  function render(d) {
    if (!isObj(d) || !isObj(d.items)) return false;
    const items = d.items;
    if (!TEASER.some(k => usable(items[k], k))) return false;
    const notice = typeof d.notice === "string" ? d.notice : "";
    document.getElementById("ai-head").textContent =
      "AI 투자를 다섯 갈래로 나눠 공개 통계의 숫자와 그래프만 싣습니다. " + notice;
    document.getElementById("ai-body").replaceChildren(...CHANNELS.map(([id, title, about, keys]) =>
      el("section", { class: "ai-channel", "aria-label": title },
        el("h3", {}, title), el("p", { class: "muted" }, about),
        ...keys.map(k => item(items[k], k)))));
    document.getElementById("ai-teaser-values").replaceChildren(...TEASER.filter(k => usable(items[k], k)).map(k =>
      el("li", {}, el("span", {}, items[k].name), " ", el("strong", {}, items[k].line),
        items[k].stale === true ? el("small", {}, " · 직전 값") : null)));
    return true;
  }

  return Object.freeze({ render, CHANNELS, TEASER });
})();
