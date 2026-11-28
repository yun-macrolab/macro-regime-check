/* 국채–OIS 스프레드(par) 참고 — data/ois.json(scripts/ois_fetch.py)을 그린다 (2026-11-15). 운영자의 비공개 월간 점검
   [수급 구조]의 끝 줄(2·5·10·30년 국채 − SOFR OIS)을 공개한 카드다. 이 사이트의 규칙 점검에 쓰지 않는다.
   자리: #ois-slot — index.html의 renderPublic이 금리·커브 묶음에서 기간 프리미엄 모형 대조(#tp-slot) 바로 뒤에 둔다.
   index.html의 el() · link()를 쓴다(부를 때 이미 정의돼 있다). 글자는 전부 el()의 텍스트로만 넣는다(자료를 HTML로 해석하지 않는다).
   카드 이름·안내·정의·출처 문구는 이 파일에 정해 둔 것이고(자료 파일의 notice는 원자료를 읽는 사람용이라 싣지 않는다 — 머리말
   ABOUT과 뜻이 같다), 칸의 숫자 줄·덧붙이는 줄은 자료 파일에 정해 둔 문구다(그 스크립트가 숫자로 만든다). 형식이 어긋났거나
   고지(notices)가 없는 칸은 숫자를 싣지 않고 '미수신 — 까닭' 또는 '자료 없음' 한 줄로 둔다. 자료 파일이 없으면 아무것도 그리지
   않는다. 바깥 요청은 없다. 링크는 FRED 시리즈 주소에만(link()가 거른다) — DTCC 쪽은 정해 둔 출처 글(SOURCE)만, 로고·링크 없이. */
"use strict";
window.OisCard = (() => {
  // 카드의 칸 차례 — 자료 파일의 order와 같다(scripts/test_ois_fetch.py가 견준다)
  const CARD = ["level", "ten"];
  // 실패 사유 — 이 목록의 글만 싣는다(scripts/ois_fetch.py의 REASONS와 같다 — 테스트가 견준다)
  const REASONS = ["수신 실패", "수신 시간 초과", "최근 날의 파일을 받지 못함 · 주소나 접근 방식이 바뀌었을 수 있음",
    "받아 둔 자료 없음", "국채 금리(FRED)를 받지 못함", "새 날 자료가 들어오지 않음", "받은 자료가 직전 자료보다 오래됨",
    "계산할 자료가 모자람"];
  const LABEL = "참고 — 예측 아님";
  // 국채 금리 쪽 — FRED에서 받는 네 시리즈(scripts/ois_fetch.py의 DGS와 같다 — 테스트가 견준다). 이 이름만 링크로 건다
  const FRED = ["DGS2", "DGS5", "DGS10", "DGS30"];
  // 머리말 — 합니다체 한 벌. 자료 파일의 notice(한다체, 같은 뜻)를 덧붙이지 않는다
  const ABOUT = "미 국채 par 금리에서 같은 만기의 SOFR OIS 고정금리를 뺀 차(bp)를, DTCC 공개 금리 스와프 거래 보고(CFTC 규칙 " +
    "Part 43)의 새 거래 중앙값과 FRED의 재무부 par 금리로 잽니다. 운영자의 비공개 월간 점검에 있던 한 줄을 공개한 측정 기록으로, " +
    "이 사이트의 규칙 수에 들지 않고 금리를 예측하지 않습니다.";
  // 출처 — 자료 파일과 상관없이 이 글로만 싣는다(scripts/ois_fetch.py의 CITATION과 같다 — 테스트가 견준다). DTCC 로고는 쓰지 않는다
  const SOURCE = "Source: DTCC Data Repository (U.S.) LLC, CFTC swap data public dissemination (17 CFR Part 43); " +
    "site calculations";
  const GUIDE = [
    ["무엇을 빼나", "국채 금리에서 같은 만기의 OIS(익일물 SOFR을 고정금리와 맞바꾸는 스와프)를 빼면 앞으로의 정책금리 기대가 " +
      "대부분 지워지고 국채만의 몫이 남습니다. 공급의 크기와 딜러가 국채를 들고 있는 비용은 + 쪽, 국채를 안전 자산·담보로 쓰는 " +
      "값(편의수익)은 − 쪽입니다. 기간 프리미엄 카드가 10년 금리 전체의 움직임을 따르는 것과 달리 수급 쪽 몫을 따로 봅니다."],
    ["부호", "국채 − OIS는 시장에서 흔히 말하는 '스와프 스프레드'(스와프 금리 − 국채 금리)의 부호를 뒤집은 값입니다. +가 클수록 " +
      "국채 금리가 같은 만기 OIS보다 높습니다 — 국채가 그만큼 싸게 거래된다는 뜻입니다."],
    ["5영업일 중앙값", "그 만기의 새 거래가 하루 10건 이상인 날만 쓰고, 마지막 날까지 최근 5개 날의 스프레드 중앙값을 싣습니다. " +
      "하루 안에서도 거래마다 고정금리가 몇 bp씩 달라(사분위 폭) 하루 값은 싣지 않습니다. 최근 5개가 마지막 날부터 14일 안에 모두 " +
      "있지 않은 만기는 '—'로 둡니다."],
    ["고르는 거래", "새 거래만 셉니다. 같은 파일 안에서 취소된 거래와 사후에 가격을 정하는 거래는 빼고, 기준 금리 이름에 USD와 " +
      "SOFR이 있고 명목 통화가 USD인 것(연방기금 OIS 제외), 고정 다리가 하나인 것, 체결한 날의 파일에 있고 5일 안에 시작하는 것, " +
      "만기가 2·5·10·30년에서 0.03년(약 11일) 안인 것만 남깁니다. 패키지 거래도 넣습니다."],
    ["같은 시각이 아님", "재무부 par 금리(FRED DGS)는 장 마감 무렵의 값이고, OIS는 하루 동안 체결된 거래의 중앙값입니다. 하루 사이 " +
      "금리가 크게 움직인 날은 그만큼 섞입니다. par 기준이라 zero(현물) 기준으로 잰 다른 자료의 수준과는 그대로 견주지 않습니다."],
    ["13주 변화 · 1년 범위", "13주 변화는 지금의 10년 5영업일 중앙값에서 마지막 날 91일 전까지의 5영업일 중앙값을 뺀 값입니다. " +
      "1년 범위는 마지막 날까지 364일 안에서 5개씩 옮겨 가며 낸 중앙값의 최저~최고이고, '받은 날'은 그 364일의 평일 가운데 10년 " +
      "스프레드를 셀 수 있었던 날 수입니다."],
    ["받은 날", "하루 파일을 날마다 새 날부터 이어 받아 만기별 중앙값만 남깁니다(data/ois_days.json — 원 행·거래 식별자는 " +
      "없습니다). 처음 몇 번의 갱신 동안은 받은 날이 적어 13주 변화·1년 범위가 비거나 짧습니다. DTCC는 약 2년 치만 두어 그보다 " +
      "오래된 날은 받지 않습니다."],
    ["자료 범위", "DTCC Data Repository (U.S.)에 보고된 거래만 들어 있습니다. 다른 스와프 데이터 저장소에 보고된 거래는 없어 시장 " +
      "전체가 아닙니다. 다음 날 이후 취소된 거래는 섞입니다."]
  ];
  const DAY = /^\d{4}-\d{2}-\d{2}$/;
  // 권장 인용의 꼴 — '…, retrieved from …, November 15, 2026.'(scripts/ois_fetch.py citation). 꼴이 다르면 싣지 않는다
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
    return why ? `미수신 — ${why}` : "자료 없음";
  }
  function stale(it) {
    if (it.stale !== true) return null;
    const why = REASONS.includes(it.error) ? ` · ${it.error}` : "";
    const since = typeof it.failed_since === "string" && DAY.test(it.failed_since) ? ` (${it.failed_since}부터)` : "";
    return el("p", { class: "oil-late" }, "새 날 자료를 받지 못해 받아 둔 날까지로 셉니다" + why + since);
  }
  function row(it, key) {
    const name = isObj(it) && typeof it.name === "string" && it.name ? it.name : key;
    if (!usable(it, key))
      return el("div", { class: "oil-row ois-row" }, el("p", { class: "oil-name" }, el("strong", {}, name), " — ", missing(it)));
    return el("div", { class: "oil-row ois-row" },
      el("p", { class: "oil-name" }, el("strong", {}, name), " ", el("small", {}, it.date)),
      stale(it),
      el("p", { class: "oil-num" }, it.line),
      ...texts(it.extra).map(t => el("p", { class: "muted" }, t)));
  }
  // 그린 칸의 FRED 출처 — 시리즈마다 하나. 권장 인용은 가장 늦게 받은 칸의 것
  function fredSources(items) {
    const best = new Map();
    for (const k of CARD) {
      const it = items[k];
      if (!usable(it, k)) continue;
      const when = typeof it.retrieved === "string" && DAY.test(it.retrieved) ? it.retrieved : "";
      for (const s of Array.isArray(it.sources) ? it.sources : []) {
        if (!isObj(s) || !FRED.includes(s.series)) continue;
        const cite = typeof s.citation === "string" && CITE.test(s.citation) ? s.citation : "";
        const was = best.get(s.series);
        if (!was || (cite && when > was.when)) best.set(s.series, { when, url: s.url, cite });
      }
    }
    return FRED.filter(x => best.has(x)).map(x => [x, best.get(x)]);
  }
  function sourceLine(fred) {
    if (!fred.length) return null;
    const parts = fred.flatMap(([sid, s], i) => (i ? [" · ", link(sid, s.url)] : [link(sid, s.url)]));
    return el("p", { class: "source-link" }, "국채 par 금리(연준 이사회 H.15, FRED 경유): ", ...parts);
  }
  function citeLine(fred) {
    const cites = fred.map(([, s]) => s.cite).filter(Boolean);
    return cites.length ? el("div", { class: "notices" }, el("p", {}, "권장 인용: " + cites.join(" "))) : null;
  }

  function card(d) {
    const items = d.items, notices = [];
    for (const k of CARD) if (usable(items[k], k)) for (const t of texts(items[k].notices)) if (!notices.includes(t)) notices.push(t);
    const fred = fredSources(items);
    return el("article", { class: "oil-card", "aria-label": "국채–OIS 스프레드 참고" },
      el("h3", {}, "국채–OIS 스프레드(par) — 2·5·10·30년", el("span", { class: "reference-label" }, LABEL)),
      el("p", { class: "muted" }, ABOUT),
      ...CARD.map(k => row(items[k], k)),
      el("details", { class: "rule-detail rule-guide" }, el("summary", {}, "읽는 법 — 정의"),
        ...GUIDE.map(([head, text]) => el("p", {}, el("strong", {}, head), " · ", text))),
      notices.length ? el("div", { class: "notices" }, ...notices.map(t => el("p", {}, t))) : null,
      el("p", { class: "source-link" }, SOURCE),
      sourceLine(fred),
      citeLine(fred));
  }

  // 자료 파일 전체 → 카드. 그릴 칸이 하나도 없거나 자리가 없으면 카드를 두지 않고 false
  function render(d) {
    if (!isObj(d) || d.schema !== 1 || !isObj(d.items)) return false;
    const slot = document.getElementById("ois-slot");
    if (!slot || !CARD.some(k => usable(d.items[k], k))) return false;
    slot.replaceChildren(card(d));
    return true;
  }

  return Object.freeze({ render, CARD, REASONS, LABEL, SOURCE, ABOUT, FRED });
})();
