/* 단일종목 CDS 참고 — data/cds.json(scripts/cds_fetch.py)을 그린다 (2026-10-30). 운영자의 비공개 월간 점검에 있던 두 줄
   (하이퍼스케일러·AI 칩 업체 12곳의 5년 호가 · 새 거래 건수)을 공개한 카드다. 이 사이트의 규칙 점검에 쓰지 않는다.
   자리: #cds-slot. index.html의 el()을 쓴다(부를 때 이미 정의돼 있다). 글자는 전부 el()의 텍스트로만 넣는다(자료를 HTML로
   해석하지 않는다). 카드 이름·안내·정의·출처 문구는 이 파일에 정해 둔 것이고(자료 파일의 notice는 원자료를 읽는 사람용이라
   싣지 않는다 — 머리말 ABOUT과 내용이 같다), 칸의 숫자 줄·표·덧붙이는 줄은 자료 파일에 정해 둔
   문구다(그 스크립트가 숫자로 만든다). 표가 있으면 표를, 꼴이 어긋나면 숫자 줄을 싣는다. 형식이 어긋났거나 고지(notices)가 없는
   칸은 숫자를 싣지 않고 '미수신 — 까닭' 또는 '자료 없음' 한 줄로 둔다. 자료 파일이 없으면 아무것도 그리지 않는다. 바깥 요청은 없다. */
"use strict";
window.CdsCard = (() => {
  // 카드의 칸 차례 — 자료 파일의 order와 같다(scripts/test_cds_fetch.py가 견준다)
  const CARD = ["quotes", "trades"];
  // 실패 사유 — 이 목록의 글만 싣는다(scripts/cds_fetch.py의 REASONS와 같다 — 테스트가 견준다)
  const REASONS = ["수신 실패", "수신 시간 초과", "최근 날의 파일을 받지 못함 · 주소나 접근 방식이 바뀌었을 수 있음",
    "받아 둔 자료 없음", "새 날 자료가 들어오지 않음", "받은 자료가 직전 자료보다 오래됨", "계산할 자료가 모자람"];
  const LABEL = "참고 — 신용 사건 예측 아님";
  // 머리말 — 합니다체 한 벌. 자료 파일의 notice(한다체, 같은 내용)를 덧붙이지 않는다
  const ABOUT = "하이퍼스케일러·AI 칩 업체 12곳의 단일종목 CDS 거래를 DTCC 공개 거래 보고(SEC 규칙 Reg SBSR)로 세어, " +
    "표준 5년 만기 스프레드의 중앙값과 새 거래 건수를 싣습니다. 운영자의 비공개 월간 점검에 있던 두 줄을 공개한 것으로, " +
    "이 사이트의 규칙 수에 들지 않고 신용 사건이나 금리를 예측하지 않습니다.";
  // 출처 — 자료 파일과 상관없이 이 글로만 싣는다(scripts/cds_fetch.py의 CITATION과 같다 — 테스트가 견준다). DTCC 로고는 쓰지 않는다
  const SOURCE = "Source: DTCC Data Repository (U.S.) LLC, SEC security-based swap public dissemination (Reg SBSR); " +
    "site calculations";
  const GUIDE = [
    ["5년 호가", "새로 체결된 거래 가운데 만기가 표준 5년(3·9월 20일에 바뀝니다)이고 스프레드가 찍힌 것의 최근 14일 중앙값입니다(bp). " +
      "날마다의 중앙값을 그날 호가 수만큼 무게로 모읍니다. 체결된 값이라 시장의 중간값(mid)과 다르고, 호가가 3개보다 적으면 " +
      "'호가 부족'으로 둡니다."],
    ["새 거래 건수", "최근 28일과 1년 전 같은 28일의 새 단일종목 거래 수입니다. 같은 파일 안의 취소, 여러 이름에 같은 시각·명목·" +
      "선지급금으로 찍힌 묶음, 한 초에 10곳 이상 찍힌 포트폴리오 거래는 뺍니다. 다음 날 이후 취소된 거래는 섞입니다."],
    ["선지급금만 있는 거래", "공개분에는 사고판 방향 칸이 없어 선지급금을 스프레드로 바꾸지 않습니다. 그런 거래뿐인 이름은 " +
      "'호가 없음'이고 건수만 보입니다."],
    ["받은 날", "하루 파일을 날마다 받아 이름별 셈만 남깁니다(data/cds_days.json — 원 행·거래 식별자는 없습니다). 받지 못한 " +
      "날이 있으면 '받은 날 n/m'으로 적고 받은 날만 셉니다. 1년 전 건수는 그 28일을 모두 받은 때만 싣습니다."],
    ["자료 범위", "DTCC 쪽 보고(SEC 관할)만 들어 있습니다. ICE Trade Vault 쪽 보고와 미국 밖 거래는 없어 시장 전체 거래가 아닙니다."]
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
    return why ? `미수신 — ${why}` : "자료 없음";
  }
  function stale(it) {
    if (it.stale !== true) return null;
    const why = REASONS.includes(it.error) ? ` · ${it.error}` : "";
    const since = typeof it.failed_since === "string" && DAY.test(it.failed_since) ? ` (${it.failed_since}부터)` : "";
    return el("p", { class: "oil-late" }, "새 날 자료를 받지 못해 받아 둔 날까지로 셉니다" + why + since);
  }
  // 이름마다 한 줄의 표 — 머리글·칸 글자는 자료 파일에 숫자로 만든 것. 꼴이 어긋나면 null(숫자 줄을 대신 싣는다)
  function table(t) {
    const strs = a => Array.isArray(a) && a.every(x => typeof x === "string");
    if (!isObj(t) || !strs(t.columns) || t.columns.length < 2 || !Array.isArray(t.rows) || !t.rows.length ||
        !t.rows.every(r => strs(r) && r.length === t.columns.length)) return null;
    return el("div", { class: "ai-table-wrap" }, el("table", { class: "ai-table" },
      typeof t.caption === "string" && t.caption ? el("caption", {}, t.caption) : null,
      el("thead", {}, el("tr", {}, ...t.columns.map(c => el("th", { scope: "col" }, c)))),
      el("tbody", {}, ...t.rows.map(r => el("tr", {}, el("th", { scope: "row" }, r[0]), ...r.slice(1).map(c => el("td", {}, c)))))));
  }
  function row(it, key) {
    const name = isObj(it) && typeof it.name === "string" && it.name ? it.name : key;
    if (!usable(it, key))
      return el("div", { class: "oil-row cds-row" }, el("p", { class: "oil-name" }, el("strong", {}, name), " — ", missing(it)));
    return el("div", { class: "oil-row cds-row" },
      el("p", { class: "oil-name" }, el("strong", {}, name), " ", el("small", {}, it.date)),
      stale(it),
      table(it.table) || el("p", { class: "oil-num" }, it.line),
      ...texts(it.extra).map(t => el("p", { class: "muted" }, t)));
  }

  function card(d) {
    const items = d.items, notices = [];
    for (const k of CARD) if (usable(items[k], k)) for (const t of texts(items[k].notices)) if (!notices.includes(t)) notices.push(t);
    return el("article", { class: "oil-card cds-card", "aria-label": "단일종목 CDS 참고" },
      el("h3", {}, "단일종목 CDS — 하이퍼스케일러·AI 칩 12곳", el("span", { class: "reference-label" }, LABEL)),
      el("p", { class: "muted" }, ABOUT),
      ...CARD.map(k => row(items[k], k)),
      el("details", { class: "rule-detail rule-guide" }, el("summary", {}, "읽는 법 — 정의"),
        ...GUIDE.map(([head, text]) => el("p", {}, el("strong", {}, head), " · ", text))),
      notices.length ? el("div", { class: "notices" }, ...notices.map(t => el("p", {}, t))) : null,
      el("p", { class: "source-link" }, SOURCE));
  }

  // 자료 파일 전체 → 카드. 그릴 칸이 하나도 없거나 자리가 없으면 카드를 두지 않고 false
  function render(d) {
    if (!isObj(d) || !isObj(d.items)) return false;
    const slot = document.getElementById("cds-slot");
    if (!slot || !CARD.some(k => usable(d.items[k], k))) return false;
    slot.replaceChildren(card(d));
    return true;
  }

  return Object.freeze({ render, CARD, REASONS, LABEL, SOURCE, ABOUT });
})();
