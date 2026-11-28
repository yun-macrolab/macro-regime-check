/* 달러 · 기대인플레이션 · 성장 · 금융 여건 참고 — data/macro.json(scripts/macro_fetch.py)을 그린다 (2026-11-28). 이 사이트의 규칙
   점검에 쓰지 않는 숫자 묶음이다. 카드 넷, 자리 넷(index.html의 renderPublic이 둔다 — 빈 자리는 .oil-slot:empty로 숨는다):
     달러          유동성 묶음(#dollar-slot)     — 달러 값은 해외 달러 자금 사정과 함께 읽히고, 금리·커브 묶음에는 이미 카드가 셋이라
     기대인플레이션 물가 묶음(#expinf-slot)       — 규칙 '실질금리와 기대인플레이션'의 10년 BEI와 나란히
     성장          신용·경기 묶음(#growth-slot)  — 이 묶음의 규칙(고용·실업률)과 같은 '경기' 쪽
     금융 여건     신용·경기 묶음(#fincond-slot) — 이 묶음의 규칙(신용 여건)과 같은 쪽
   index.html의 el() · link()를 쓴다(부를 때 이미 정의돼 있다). 글자는 전부 el()의 텍스트로만 넣는다(자료를 HTML로 해석하지 않는다).
   카드 이름·안내·읽는 법·출처 줄의 기관 이름은 이 파일에 정해 둔 것이고, 칸의 숫자 줄·덧붙이는 줄·고지는 자료 파일에 정해 둔 문구다.
   형식이 어긋났거나 고지(notices)가 없는 칸은 숫자를 싣지 않고 '미수신(까닭)' 또는 '자료 없음' 한 줄로 둔다. 판정·문턱·색은 없다.
   자료 파일이 없으면(첫 자동 실행 전) 아무것도 그리지 않는다. 바깥 요청은 없다. 그린 칸의 시리즈마다 FRED 권장 인용을 글자로 싣는다. */
"use strict";
window.MacroCards = (() => {
  // 카드 → 칸 차례 — 자료 파일의 cards와 같다(scripts/test_macro_fetch.py가 견준다)
  const CARDS = {
    dollar: ["dollar"],
    expinf: ["market", "model"],
    growth: ["wei", "indpro", "cfnai"],
    fincond: ["nfci"]
  };
  const SLOT = { dollar: "dollar-slot", expinf: "expinf-slot", growth: "growth-slot", fincond: "fincond-slot" };
  const TITLE = { dollar: "달러", expinf: "기대인플레이션 — 시장 · 모형", growth: "성장 — 주간 · 월간 활동 지표", fincond: "금융 여건" };
  // 자료 파일의 실패 사유 — 이 목록의 글만 싣는다(scripts/macro_fetch.py의 REASONS와 같다 — 테스트가 견준다)
  const REASONS = ["수신 실패", "수신 실패 · 묵은 캐시는 싣지 않음", "계산할 자료가 모자람", "받은 자료가 직전 자료보다 오래됨"];
  const LABEL = "참고 — 예측 아님";
  const RULE = "규칙 수에 들지 않는 참고 숫자이고, 문턱을 두지 않으며, 예측하지 않습니다.";
  const ABOUT = {
    dollar: "연준 이사회의 광의 달러지수(명목)를 그대로 옮기고 4주·13주 변화만 계산합니다. " + RULE,
    expinf: "같은 기대인플레이션을 시장 값(국채와 TIPS)과 모형 추정치(클리블랜드 연은)로 나란히 둡니다. 재는 방식이 다르다는 것만 보이고, 두 값을 잇거나 차를 내지 않습니다. " + RULE,
    growth: "주간·월간 활동 지표 셋(WEI · 산업생산 · CFNAI)의 공개 통계와 그 산술입니다. " + RULE,
    fincond: "시카고 연은 금융여건지수(NFCI · ANFCI)의 수준과 4주 변화입니다. " + RULE
  };
  // 출처 줄의 기관 이름 — 시카고 연은 자료는 서면 허락을 확인하는 중이라는 것을 그대로 적는다(README '한계'의 회색 지대)
  const SOURCE_LABEL = {
    dollar: "연준 이사회 H.10 · 공공 영역",
    expinf: "세인트루이스 연은 · 클리블랜드 연은(CC BY-SA 4.0)",
    growth: "달라스 연은(WEI) · 연준 이사회 G.17 · 시카고 연은 · 허락 확인 중(CFNAI)",
    fincond: "시카고 연은 · 허락 확인 중"
  };
  const GUIDE = {
    dollar: [
      ["광의 달러지수", "연준 이사회가 26개 교역 상대국 통화에 견준 달러 값을 교역 비중으로 묶은 지수입니다(명목, 2006년 1월 = 100). " +
        "오르면 그 통화들에 견줘 달러 값이 올랐다는 뜻입니다."],
      ["DXY와 다른 점", "흔히 보는 ICE 달러지수(DXY)는 6개 통화(유로 비중이 가장 큽니다)로 만듭니다. 광의 지수는 중국·멕시코·캐나다 같은 " +
        "교역 상대국을 더 넓게 담습니다. 이 사이트는 DXY 값을 싣지 않습니다."],
      ["4주 · 13주", "28일 전 · 91일 전(휴일이면 그 전 마지막 관측)과 견준 % 변화입니다. H.10은 주마다 나와 마지막 관측이 한 주 남짓 늦습니다."]
    ],
    expinf: [
      ["시장 기반", "10년 BEI와 5년 뒤 5년은 명목 국채와 물가연동국채(TIPS) 금리의 차로 잽니다. 매일 바뀌고, 위험·유동성 프리미엄이 섞입니다. " +
        "10년 BEI는 규칙 '실질금리와 기대인플레이션'이 쓰는 시리즈입니다."],
      ["모형 기반", "클리블랜드 연은은 국채 금리·인플레이션 스왑·전문가 설문·CPI를 함께 넣은 모형으로 기대인플레이션을 위험 프리미엄과 " +
        "나눠 추정합니다. 한 달에 한 번, CPI가 나오는 날 갱신됩니다. 이 자료는 CC BY-SA 4.0 라이선스이고, 카드의 그 값도 같은 라이선스입니다."],
      ["나란히 두는 까닭", "같은 '기대인플레이션'이라도 재는 방식이 다르면 값이 다릅니다. 이 카드는 두 방식을 나란히 보일 뿐, 두 값의 차를 " +
        "내거나 어느 쪽이 맞는지 가리지 않습니다. 미시간대 설문과 뉴욕 연은 소비자 기대 설문(SCE)은 이용 조건 때문에 싣지 않습니다."]
    ],
    growth: [
      ["WEI", "실업수당 청구·철강 생산·전력 사용 같은 주간 자료 10개로 만든 지수로, 실질 GDP의 4분기 전 대비 성장률 눈금에 맞춥니다. " +
        "2023년 12월부터 달라스 연은이 냅니다(그 전에는 뉴욕 연은)."],
      ["산업생산", "제조·광업·전기·가스의 생산량 지수입니다(연준 이사회 G.17). 3개월 연율은 석 달 변화를 1년으로 늘린 값이라 전년비보다 " +
        "많이 흔들립니다. 산업 부문만이라 경제 전체의 성장률이 아닙니다."],
      ["CFNAI", "85개 월간 지표의 가중 평균입니다. 시카고 연은의 정의로 0은 과거 추세 성장, 양수는 추세보다 빠른 성장, 음수는 추세보다 " +
        "느린 성장입니다. 한 달 값은 많이 흔들려 석 달 평균(CFNAI-MA3)을 함께 싣습니다."],
      ["출처의 설명 (CFNAI-MA3)", "시카고 연은은 CFNAI 자료 페이지(chicagofed.org)에 확장이 이어진 뒤의 경우로 이렇게 적습니다: \"an " +
        "increasing likelihood of a recession has historically been associated with a CFNAI-MA3 value below –0.70\". 출처의 " +
        "설명을 옮긴 것일 뿐이고, 이 사이트는 이 값을 기준선으로 쓰지 않으며 숫자의 색도 바꾸지 않습니다."],
      ["싣지 않는 것", "애틀랜타 연은 GDPNow는 이용 조건을 확인하지 못해 싣지 않습니다."]
    ],
    fincond: [
      ["NFCI", "위험·신용·레버리지 세 갈래 105개 금융 지표의 가중 평균을 1971년 이후 평균 0 · 표준편차 1로 맞춘 값입니다. 시카고 연은의 " +
        "정의로 0은 1971년 이후 평균, 양수는 평균보다 빠듯한 여건, 음수는 평균보다 느슨한 여건입니다(\"Positive values of the NFCI " +
        "indicate financial conditions that are tighter than average\"). 0 말고 다른 기준선은 두지 않습니다."],
      ["ANFCI", "NFCI에서 경제 활동·물가로 설명되는 몫을 뺀 값입니다. 지금의 경기·물가에 견준 금융 여건을 봅니다."],
      ["고쳐지는 값", "새 자료가 들어오면 지난 주들의 값도 조금씩 바뀝니다. 카드의 4주 변화는 이번에 받은 계열 안에서 견준 값입니다."],
      ["신용 긴축 카드와의 관계", "AI 투자 화면의 신용 긴축 카드가 쓰는 NFCI 신용 하위 지수(NFCICREDIT)는 NFCI의 한 갈래입니다. 두 카드는 " +
        "따로 계산합니다."]
    ]
  };
  const DAY = /^\d{4}-\d{2}-\d{2}$/;
  // 권장 인용의 꼴 — '…, retrieved from …, November 28, 2026.'(scripts/macro_fetch.py citation). 꼴이 다르면 싣지 않는다
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
      return el("div", { class: "oil-row" }, el("p", { class: "oil-name" }, el("strong", {}, name), " — ", missing(it)));
    return el("div", { class: "oil-row" },
      el("p", { class: "oil-name" }, el("strong", {}, name), " ", el("small", {}, it.date)),
      el("p", { class: "oil-num" }, it.line),
      ...texts(it.extra).map(t => el("p", { class: "muted" }, t)),
      stale(it));
  }
  // 그린 칸의 출처 — 시리즈마다 한 번. link()는 FRED 주소만 링크로 건다
  function drawnSources(items, keys) {
    const seen = new Map();
    for (const k of keys) {
      const it = items[k];
      if (!usable(it, k)) continue;
      const when = typeof it.retrieved === "string" && DAY.test(it.retrieved) ? it.retrieved : "";
      for (const s of Array.isArray(it.sources) ? it.sources : []) {
        if (!isObj(s) || typeof s.series !== "string" || !/^[A-Z0-9]+$/.test(s.series)) continue;
        const cite = typeof s.citation === "string" && CITE.test(s.citation) ? s.citation : "";
        const was = seen.get(s.series);
        if (!was) seen.set(s.series, { url: s.url, when, cite });
        else if (cite && when > was.when) seen.set(s.series, { url: was.url, when, cite });
      }
    }
    return seen;
  }
  function sourceLine(card, seen) {
    if (!seen.size) return null;
    const parts = [...seen].flatMap(([sid, s], i) => (i ? [" · ", link(sid, s.url)] : [link(sid, s.url)]));
    return el("p", { class: "source-link" }, `자료(FRED 경유, ${SOURCE_LABEL[card]}): `, ...parts);
  }
  function citeLines(seen) {
    const lines = [...seen.values()].filter(s => s.cite).map(s => el("p", { class: "muted" }, "권장 인용: " + s.cite));
    return lines.length ? el("div", { class: "cite-lines" }, ...lines) : null;
  }

  function card(name, items) {
    const keys = CARDS[name], notices = [];   // 머리 안내는 ABOUT만 — 자료 파일의 notice는 같은 뜻의 한다체라 싣지 않는다
    for (const k of keys) if (usable(items[k], k)) for (const t of texts(items[k].notices)) if (!notices.includes(t)) notices.push(t);
    const seen = drawnSources(items, keys);
    return el("article", { class: "oil-card macro-card", "aria-label": TITLE[name] + " 참고" },
      el("h3", {}, TITLE[name], el("span", { class: "reference-label" }, LABEL)),
      el("p", { class: "muted" }, ABOUT[name]),
      ...keys.map(k => row(items[k], k)),
      el("details", { class: "rule-detail rule-guide" }, el("summary", {}, "읽는 법 — 정의"),
        ...GUIDE[name].map(([head, text]) => el("p", {}, el("strong", {}, head), " · ", text))),
      sourceLine(name, seen),                 // 기관 이름 · '허락 확인 중'은 접는 칸 밖 — 자료와 함께 늘 보인다
      terms(notices, seen));
  }
  // 출처 · 이용 조건 — 고지(공공 영역 · CC BY-SA · 시카고 허락 확인 중 · 달라스 연은 · 계산값)와 FRED 권장 인용. 기본은 닫힘(2026-11-28)
  function terms(notices, seen) {
    const kids = [notices.length ? el("div", { class: "notices" }, ...notices.map(t => el("p", {}, t))) : null, citeLines(seen)]
      .filter(Boolean);
    return kids.length ? el("details", { class: "rule-detail macro-terms" }, el("summary", {}, "출처 · 이용 조건"), ...kids) : null;
  }

  // 자료 파일 전체 → 카드 넷. 카드마다 따로: 자리가 없거나 그린 칸이 하나도 없으면 그 카드만 두지 않는다. 하나라도 그렸으면 true
  function render(d) {
    if (!isObj(d) || !isObj(d.items)) return false;
    let any = false;
    for (const name of Object.keys(CARDS)) {
      try {
        const slot = document.getElementById(SLOT[name]);
        if (!slot || !CARDS[name].some(k => usable(d.items[k], k))) continue;
        slot.replaceChildren(card(name, d.items));
        any = true;
      } catch (e) { /* 한 카드가 깨져도 다른 카드는 그린다 */ }
    }
    return any;
  }

  return Object.freeze({ render, CARDS, SLOT, TITLE, REASONS, LABEL, ABOUT, SOURCE_LABEL });
})();
