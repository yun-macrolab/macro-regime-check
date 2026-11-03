/* 연준 재무상태표(H.4.1 주간) 참고 — data/fedbs.json(scripts/fedbs_fetch.py)을 그린다 (2026-11-03). 이 사이트의 규칙 점검에 쓰지 않는 숫자 묶음이다.
   한 곳: 유동성 묶음에서 지준·재정 카드 바로 뒤의 참고 카드(#fedbs-slot — index.html의 renderPublic이 둔다).
   index.html의 el() · link()를 쓴다(부를 때 이미 정의돼 있다). 글자는 전부 el()의 텍스트로만 넣는다(자료를 HTML로 해석하지 않는다).
   카드 이름·안내·읽는 법 문구는 이 파일에 정해 둔 것이고, 칸의 숫자 줄·덧붙이는 줄·고지는 자료 파일에 정해 둔 문구다(그 스크립트가 숫자로 만든다).
   형식이 어긋났거나 고지(notices)가 없는 칸은 숫자를 싣지 않고 '미수신(까닭)' 또는 '자료 없음' 한 줄로 둔다.
   자료 파일이 없으면(첫 자동 실행 전) 아무것도 그리지 않는다. 바깥 요청은 없다. 겉모양은 유가 카드의 클래스를 함께 쓴다.
   그래프(최근 52주 지준과 규칙 하한 × 마지막 분기 GDP)는 charts.js의 MacroCharts.lineChart로 — 없거나 깨지면 그래프만 뺀다.
   인용이 필요한 자료(licence 'citation-required' — 뉴욕 연은 SOFR · 상시 레포 · 익일물 역레포)는 FRED 권장 인용을 글자로 싣는다.
   카드 머리 안내는 ABOUT 하나(합니다체)다 — 자료 파일의 notice(한다체, 같은 뜻)는 겹쳐 싣지 않는다. */
"use strict";
window.FedBsCard = (() => {
  // 카드의 칸 차례 — 자료 파일의 order와 같다(scripts/test_fedbs_fetch.py가 견준다)
  const CARD = ["reserves", "dec", "spread", "srf", "rrp", "week"];
  // 자료 파일의 실패 사유 — 이 목록의 글만 싣는다(scripts/fedbs_fetch.py의 REASONS와 같다 — 테스트가 견준다)
  const REASONS = ["수신 실패", "수신 실패 · 묵은 캐시는 싣지 않음", "계산할 자료가 모자람", "받은 자료가 직전 자료보다 오래됨"];
  const LABEL = "참고 — 예측 아님";
  // 카드 머리 안내 — fedbs_fetch.NOTICE의 뜻을 모두 담는다(테스트가 견준다). 자료 파일의 notice는 따로 싣지 않는다
  const ABOUT = "연준 H.4.1 주간 대차대조표와 단기자금 시장의 공개 통계와 그 산술입니다. 위 규칙 카드 '지준과 통화승수'의 지준/GDP와 " +
    "지준·재정 카드의 13주 나눔을 주간으로 읽는 재료이고, 규칙 수에 들지 않습니다. 금리나 자금 여건을 예측하지 않습니다.";
  const GUIDE = [
    ["거리는 4주 평균과 함께", "규칙 하한까지의 거리는 한 주의 숫자보다 4주 평균과 함께 읽습니다. 최신 주가 하한 아래여도 4주 평균이 " +
      "위면 한 주의 재무부 현금 흔들림일 수 있습니다. 운영자가 2026-11-03에 최근 52주(주 평균 지준)로 재 본 바로는 주간 지준 변화의 " +
      "표준편차가 약 62bn, 4주 변화는 약 89bn이었습니다(측정 기록)."],
    ["분모 바뀜", "지준이 그대로여도 명목 GDP(분모)가 새 분기로 바뀌거나 개정되면 거리가 움직입니다. 분모 바뀜은 직전 주를 처음 실을 " +
      "때의 GDP로 같은 지준을 나눈 값과의 차이입니다. 같은 주 안에서 GDP만 바뀌면 그 바뀜은 다음 주에 싣습니다. 거리의 상당 부분이 " +
      "분모 바뀜이면 지준이 아니라 GDP가 움직인 것입니다."],
    ["재무부 현금(TGA)", "나눔의 재무부 현금 칸이 지준 변화 대부분을 설명하면 재무부의 현금 흐름이지 연준의 운용이 아닙니다. 운영자가 " +
      "2026-11-03에 최근 52주 수요일 수준으로 재 본 바로는 주간 지준 변화를 재무부 현금 변화로 설명하는 R²가 0.91이었습니다(104주로 " +
      "늘리면 0.57 — 기간에 따라 다릅니다, 측정 기록)."],
    ["연준 단기채와 MBS는 짝으로", "연준 단기채 칸은 지준 관리 매입(RMP)만이 아닙니다. 보유 축소(QT)가 2025-12-01에 끝난 뒤 MBS " +
      "상환분은 단기채로 재투자되므로, 단기채 증가는 RMP와 재투자의 합이고 MBS 칸의 감소와 거의 상쇄됩니다. RMP는 단기채 + MBS의 " +
      "순증으로 대략 봅니다(상환 기록일·재투자 시차로 4주 창에서는 흔들립니다)."],
    ["창의 출발일", "4주·13주 창의 출발 수요일에 월말·분기말·15일 표시가 있으면 그날 하루 튄 역레포·재무부 현금의 되돌림이 그 칸에 " +
      "섞여 있습니다. 창은 옮기지 않고 표시만 합니다. 1주 변화는 15일·월말 하루에 크게 흔들려 싣지 않습니다."],
    ["FOMC 뒤 첫 H.4.1", "FOMC 결정일(수)이 그 주의 마지막 날이라 그 주의 지준·나눔·주 평균은 결정이 시행되기 전 값입니다. IORB·" +
      "역레포 금리·운용 변경은 결정 다음 날(목)부터라 결정의 흔적은 다음 주 숫자에서 봅니다. 다음 FOMC는 갱신 시각에 아직 성명" +
      "(결정일 14:00 미 동부)이 나오지 않은 첫 회의입니다. FOMC 일정은 연준 FOMC 일정 페이지(2026-10-28 갱신)를 이 사이트에 " +
      "적어 둔 표이고, 연준 고지대로 각 회의는 직전 회의에서 확정되기 전까지 잠정이라 2027년 날짜에 '(잠정)'을 붙입니다. 연준 " +
      "의장은 2026-10-28 기자회견에서 2027년 회의 하나(일정 변경은 2027년 가을부터, 어느 회의인지 미정)는 금리 표결·성명 없이 " +
      "전략만 다룬다고 밝혔습니다 — 그 회의의 주에는 표시가 붙어도 시행할 결정이 없습니다. (federalreserve.gov fomccalendars · " +
      "FOMCpresconf20261028)"],
    ["단기자금", "단기자금의 빠듯함은 지준/GDP보다 SOFR − IORB와 상시 레포(SRF) 이용으로 직접 봅니다. 규칙 하한 9%는 추정값이고, " +
      "단기자금이 빠듯해지는 경계라는 근거는 약합니다."],
    ["정책 사실(1차 출처)", "보유 축소 종료 — FOMC 성명 2025-10-29: 'The Committee decided to conclude the reduction of its " +
      "aggregate securities holdings on December 1.' 같은 날 시행 노트: 'Beginning on December 1, reinvest all principal payments " +
      "from the Federal Reserve's holdings of agency securities into Treasury bills.' 지준 관리 매입 시작 — FOMC 성명 2025-12-10: " +
      "'will initiate purchases of shorter-term Treasury securities as needed to maintain an ample supply of reserves on an " +
      "ongoing basis.' (federalreserve.gov 보도자료 monetary20251029a · monetary20251029a1 · monetary20251210a)"],
    ["측정 기록 — 추정", "운영자가 2026-11-03에 뉴욕 연은의 단기채 매입 운영 결과(받아들인 금액)를 월 일정 창마다 더해 그 달 MBS " +
      "상환(H.4.1)과 견준 바로는, 2026년 8·9월 창의 매입은 MBS 상환 재투자뿐인 크기였습니다(RMP 약 0). 10월 창(10-19부터 다음 달 " +
      "중순까지 — 아직 끝나지 않은 창)은 10-29까지 세 번의 운영으로 약 7bn이고, 같은 속도로 늘려 잡으면 그 달 MBS 상환(약 15bn)과 비슷한 " +
      "크기입니다. 월 일정 원문의 RMP·재투자 나눔을 받지 못해 운영 결과로 거꾸로 셈한 추정이고(10월은 늘려 잡은 값), 공식 수치가 " +
      "아닙니다."]
  ];
  const DAY = /^\d{4}-\d{2}-\d{2}$/;
  // 권장 인용의 꼴 — '…, retrieved from …, November 3, 2026.'(scripts/fedbs_fetch.py citation). 꼴이 다르면 싣지 않는다
  const CITE = /^[^<>]{1,300}, retrieved from [^<>]{1,300}, [A-Z][a-z]+ \d{1,2}, \d{4}\.$/;
  const CITE_LICENCE = "citation-required";
  const texts = v => (Array.isArray(v) ? v : []).filter(x => typeof x === "string" && x);
  const isObj = v => v && typeof v === "object" && !Array.isArray(v);
  const day = v => (typeof v === "string" && DAY.test(v) && Number.isFinite(Date.parse(v + "T00:00:00Z")) ? v : "");
  const bn0 = v => {                 // 그래프 값 — 십억 달러 정수, 천 단위 쉼표
    const s = String(Math.round(Math.abs(v))).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    return (v < 0 && Math.round(v) !== 0 ? "-" : "") + s + "bn";
  };

  function usable(it, key) {
    return isObj(it) && it.key === key && day(it.date) !== "" && typeof it.line === "string" && it.line !== "" &&
      texts(it.notices).length > 0;
  }
  function missing(it) {             // 숫자를 싣지 못하는 칸의 한 줄 — 사유는 정해 둔 목록 안의 것만
    const why = isObj(it) && REASONS.includes(it.error) ? it.error : "";
    return why ? `미수신(${why})` : "자료 없음";
  }
  function stale(it) {
    if (it.stale !== true) return null;
    const since = day(it.failed_since) ? ` (${it.failed_since}부터)` : "";
    return el("p", { class: "oil-late" }, "이번 갱신의 값을 싣지 못해 직전에 받은 값을 싣습니다" + since);
  }
  function chart(spec) {
    if (!isObj(spec) || !window.MacroCharts) return null;
    try { return window.MacroCharts.lineChart(spec, { height: 190, caption: false, notices: false, format: bn0 }); }
    catch (e) { return null; }
  }
  function row(it, key) {
    const name = isObj(it) && typeof it.name === "string" && it.name ? it.name : key;
    if (!usable(it, key))
      return el("div", { class: "oil-row fedbs-row" }, el("p", { class: "oil-name" }, el("strong", {}, name), " — ", missing(it)));
    return el("div", { class: "oil-row fedbs-row" },
      el("p", { class: "oil-name" }, el("strong", {}, name), " ", el("small", {}, it.date)),
      el("p", { class: "oil-num" }, it.line),
      ...texts(it.extra).map(t => el("p", { class: "muted" }, t)),
      stale(it),
      key === "reserves" ? chart(it.chart) : null);
  }
  // 머리의 기준 주 — 주 칸(없으면 지준 칸)의 날짜(H.4.1 수요일)와 받은 날
  function head(items) {
    const it = ["week", "reserves"].map(k => usable(items[k], k) ? items[k] : null).find(Boolean);
    if (!it) return null;
    const got = day(it.retrieved);
    return el("p", { class: "muted fedbs-head" }, `기준 주(수요일) ${it.date}` + (got ? ` · 받은 날 ${got}` : ""));
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
    return el("p", { class: "source-link" }, "자료(FRED 경유, 연준 이사회 H.4.1 · 뉴욕 연은 · BEA): ", ...parts);
  }
  // 권장 인용 — 그린 칸의 출처 중 인용이 필요한 것(CITE_LICENCE)만, 시리즈마다 하나(가장 늦게 받은 칸의 것), 줄마다 글자로
  function citeLines(items) {
    const best = new Map();
    for (const k of CARD) {
      const it = items[k];
      if (!usable(it, k)) continue;
      const when = day(it.retrieved);
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
    const items = d.items, notices = [];   // 머리 안내는 ABOUT만 — d.notice는 같은 뜻의 한다체라 싣지 않는다
    for (const k of CARD) if (usable(items[k], k)) for (const t of texts(items[k].notices)) if (!notices.includes(t)) notices.push(t);
    return el("article", { class: "oil-card fedbs-card", "aria-label": "연준 재무상태표 참고" },
      el("h3", {}, "연준 재무상태표(H.4.1 주간)", el("span", { class: "reference-label" }, LABEL)),
      el("p", { class: "muted" }, ABOUT),
      head(items),
      ...CARD.map(k => row(items[k], k)),
      el("details", { class: "rule-detail rule-guide" }, el("summary", {}, "읽는 법 — 정의·정책 사실·측정 기록"),
        ...GUIDE.map(([h, text]) => el("p", {}, el("strong", {}, h), " · ", text))),
      notices.length ? el("div", { class: "notices" }, ...notices.map(t => el("p", {}, t))) : null,
      sourceLine(items),
      citeLines(items));
  }

  // 자료 파일 전체 → 카드. 그린 칸이 하나도 없으면 카드를 두지 않고 false
  function render(d) {
    if (!isObj(d) || !isObj(d.items)) return false;
    const slot = document.getElementById("fedbs-slot");
    if (!slot || !CARD.some(k => usable(d.items[k], k))) return false;
    slot.replaceChildren(card(d));
    return true;
  }

  return Object.freeze({ render, CARD, REASONS, LABEL, ABOUT });
})();
