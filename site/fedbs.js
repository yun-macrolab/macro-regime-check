/* 연준 재무상태표(H.4.1 주간) 참고 — data/fedbs.json(scripts/fedbs_fetch.py)을 그린다 (2026-11-03). 이 사이트의 규칙 점검에 쓰지 않는 숫자 묶음이다.
   한 곳: 유동성 묶음에서 지준·재정 카드 바로 뒤의 참고 카드(#fedbs-slot — index.html의 renderPublic이 둔다).
   index.html의 el() · link()를 쓴다(부를 때 이미 정의돼 있다). 글자는 전부 el()의 텍스트로만 넣는다(자료를 HTML로 해석하지 않는다).
   카드 이름·안내·읽는 법 문구는 이 파일에 정해 둔 것이고, 칸의 숫자 줄·덧붙이는 줄·고지는 자료 파일에 정해 둔 문구다(그 스크립트가 숫자로 만든다).
   형식이 어긋났거나 고지(notices)가 없는 칸은 숫자를 싣지 않고 '미수신(까닭)' 또는 '자료 없음' 한 줄로 둔다.
   자료 파일이 없으면(첫 자동 실행 전) 아무것도 그리지 않는다. 바깥 요청은 없다. 겉모양은 유가 카드의 클래스를 함께 쓴다.
   그래프(최근 52주 지준과 규칙 하한 × 마지막 분기 GDP)는 charts.js의 MacroCharts.lineChart로 — 없거나 깨지면 그래프만 뺀다.
   인용이 필요한 자료(licence 'citation-required' — 뉴욕 연은 SOFR · 상시 레포 · 익일물 역레포)는 FRED 권장 인용을 글자로 싣는다.
   카드 머리 안내는 ABOUT 하나(합니다체)다 — 자료 파일의 notice(한다체, 같은 뜻)는 겹쳐 싣지 않는다.
   지준 관리 매입(RMP) 칸(rmp_view)은 이 카드에만 있다(2026-11-03 — 처음의 계획 줄·대조 줄 두 칸을 같은 날 한 칸으로): 자료 파일의
   view(머리 토막·다음 날짜·묶음 표·뜻 덧줄·시작 뒤 나눔·하한 달러 크기·덧줄 — 모두 그 스크립트가 숫자로 만든 정해 둔 글)를 나눠
   그린다. 표는 .ai-table 꼴, 1280 폭에서는 표 옆에 머리 글과 뜻 덧줄을 두고 좁은 폭에서는 위아래로 쌓는다(dashboard.css의 rmp-*).
   숫자·날짜 토막은 줄 중간에서 끊지 않게 span.nw로 감싼다(글자는 그대로 — 감싸기만). view의 꼴이 어긋나면 숫자 줄과 덧줄만
   그린다. 그 칸이 없던 때의 자료 파일이면(옛 rmp_plan·rmp 칸뿐이어도) 줄을 두지 않는다(OPTIONAL). 계획 페이지·운영 결과는 FRED가
   아니라 뉴욕 연은에서 직접 받은 것이라 링크 없이 이름을 글자로 싣고 권장 인용(licence 'nyfed-terms')도 글자로 싣는다.
   읽는 법의 'RMP 칸' 항목은 화면에서 뺀 셈 규칙이 있는 저장소 README(GitHub)를 link()로 가리킨다.
   '연준 대차대조표 정책 — 1차 출처'(POLICY)는 접힌 읽는 법 밖에 보이는 짧은 칸이다 — 운영자가 연준·뉴욕 연은 원문을 확인해
   적은 고정 글(기준일 POLICY_ASOF, 자동 갱신 아님, 사람이 고친다). 짧은 영어 인용은 원문 그대로, 주소는 글자로만. */
"use strict";
window.FedBsCard = (() => {
  // 카드의 칸 차례 — 자료 파일의 order와 같다(scripts/test_fedbs_fetch.py가 견준다)
  const CARD = ["reserves", "dec", "rmp_view", "spread", "srf", "rrp", "week"];
  // 그 칸이 없던 때의 자료 파일이면 줄을 두지 않는 칸(나머지는 칸이 없으면 '자료 없음')
  const OPTIONAL = ["rmp_view"];
  // 뉴욕 연은에서 직접 받는 두 출처 — 자료 파일 sources[].series의 이름(scripts/fedbs_fetch.py의 OPS·PLAN과 같다 — 테스트가 견준다)
  const OPS = "TSYOPS";
  const PLAN = "TSYPLAN";
  const DIRECT = { [PLAN]: "뉴욕 연은 Treasury Securities Operational Details(월 일정 계획, 직접)",
    [OPS]: "뉴욕 연은 국채 운영 결과(Markets API, 직접)" };
  // 자료 파일의 실패 사유 — 이 목록의 글만 싣는다(scripts/fedbs_fetch.py의 REASONS와 같다 — 테스트가 견준다)
  const REASONS = ["수신 실패", "수신 실패 · 묵은 캐시는 싣지 않음", "계산할 자료가 모자람", "받은 자료가 직전 자료보다 오래됨",
    "공식 페이지에서 계획 표를 찾지 못함"];
  const LABEL = "참고 — 예측 아님";
  // 카드 머리 안내 — fedbs_fetch.NOTICE의 뜻을 모두 담는다(테스트가 견준다). 자료 파일의 notice는 따로 싣지 않는다
  const ABOUT = "연준 H.4.1 주간 대차대조표와 단기자금 시장의 공개 통계와 그 산술입니다. 위 규칙 카드 '지준과 통화승수'의 지준/GDP와 " +
    "지준·재정 카드의 13주 나눔을 주간으로 읽는 재료이고, 규칙 수에 들지 않습니다. 지준 관리 매입(RMP)은 뉴욕 연은 월 일정 공지의 " +
    "계획 금액이고, 운영 결과로 셈한 대조(공식 수치 아님)는 차 한 줄로만 둡니다. 금리나 자금 여건을 예측하지 않습니다.";
  // 읽는 법의 'RMP 칸' 항목이 가리키는 저장소 README 절(link()는 FRED·GitHub 주소만 링크로 건다)
  const README_URL = "https://github.com/yun-macrolab/macro-regime-check#rmp-칸의-셈-규칙";
  const README_LABEL = "저장소 README의 'RMP 칸의 셈 규칙' 절";
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
    ["RMP 칸", "창은 뉴욕 연은 계획 페이지의 월 일정 기간이고 시작 달로 부릅니다(예: 2026년 10월 창 = 2026-10-15~11-13). 재투자는 " +
      "MBS 상환분을 단기채로 바꾸는 보유 교체이고 RMP는 그 위에 더 사는 몫이라, 나눔 칸의 연준 단기채는 둘의 합입니다 — RMP는 " +
      "단기채 + MBS의 순증으로 봅니다. 'RMP 시작 뒤 지준' 줄은 네 수요일 평균의 차입니다. 한 주 끝점으로 셈하면 재무부 현금 한 " +
      "주치에 크게 흔들립니다 — 운영자가 2026-11-03에 재 본 바로는 2025-12-10에서 2026-10-28로 셈하면 지준 -78.5bn, 출발을 한 주 앞 " +
      "12-03으로 옮기면 +17.1bn이었습니다(재무부 현금이 12-10에 805.8bn, 10-28에 1,015.6bn — 측정 기록). 그 줄의 단기채+MBS가 계획 " +
      "누적보다 조금 낮게 나올 수 있는 것은 시작 앞 네 주에 보유 축소 때의 마지막 MBS 상환 전 수요일(2025-11-19)이, 최근 네 주에 " +
      "재투자 결제가 다 되기 전의 수요일들이 들어 있어서입니다(같은 날 +207 대 215). '그 밖'은 연준 이표채·TIPS(같은 날 약 +10)와 " +
      "대출·기타 부채 등의 나머지입니다. 운영 결과 대조는 창 안 매입 운영 결과의 합에서 그 달 MBS 상환(WSHOMCB)을 뺀 이 사이트의 " +
      "셈이고 공식 수치가 아닙니다. 창 경계·상환 수요일·소액 운영을 빼는 규칙과 읽는 계획 문장 꼴은 ",
      [README_LABEL, README_URL, "에 있습니다."]],
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
    ["정책 사실", "보유 축소 종료·지준 관리 매입 시작·태스크포스 같은 정책 사실은 위 '연준 대차대조표 정책 — 1차 출처' 칸에 " +
      "원문 인용·날짜·출처 주소와 함께 있습니다."]
  ];
  // 연준 대차대조표 정책 — 1차 출처(접힌 읽는 법 밖에 보이는 칸). 운영자가 2026-11-03 원문을 받아 확인한 고정 글 — 자동 갱신 아님.
  // 영어 인용은 원문 그대로(scripts/test_fedbs_fetch.py가 견준다), 주소는 글자로만(링크는 FRED·GitHub에만 건다)
  const POLICY_HEAD = "연준 대차대조표 정책 — 1차 출처";
  const POLICY_ASOF = "2026-11-03";
  const POLICY_NOTE = "운영자가 연준·뉴욕 연은 원문을 확인해 적은 고정 글입니다(자동으로 갱신하지 않습니다). 영어 인용은 원문 " +
    "그대로이고 주소는 글자로만 둡니다.";
  const POLICY = [
    ["보유 축소(QT) 종료 — 2025-12-01", "FOMC 성명 2025-10-29: 'The Committee decided to conclude the reduction of its " +
      "aggregate securities holdings on December 1.' 같은 날 시행 노트: 'Beginning on December 1, reinvest all principal " +
      "payments from the Federal Reserve's holdings of agency securities into Treasury bills.' " +
      "(federalreserve.gov/newsevents/pressreleases/monetary20251029a.htm · monetary20251029a1.htm)"],
    ["지준 관리 매입(RMP) 시작 — 2025-12", "FOMC 성명 2025-12-10: 'will initiate purchases of shorter-term Treasury securities " +
      "as needed to maintain an ample supply of reserves on an ongoing basis.' 같은 날 뉴욕 연은 운영 방침: 단기채(필요하면 잔존 " +
      "3년 이하 국채)를 유통시장에서 사고, 월 금액은 'on or around the ninth business day of each month' 다음 약 30일 치 일정과 " +
      "함께 발표, 첫 일정 2025-12-11에 약 $40bn(매입은 12-12부터). 4월의 비지준 부채 급증에 맞춰 몇 달은 높은 속도이고 그 뒤 " +
      "'the pace of total purchases will likely be significantly reduced'. MBS 상환분의 단기채 재투자도 같은 월 일정에 든다. " +
      "(federalreserve.gov/newsevents/pressreleases/monetary20251210a.htm · newyorkfed.org/markets/opolicy/operating_policy_251210a)"],
    ["FOMC 성명 2026-10-28", "목표 범위 3-3/4~4% 유지, 'The Committee is continuing its policy of maintaining ample reserves in " +
      "the banking system.' (federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm)"],
    ["대차대조표 태스크포스", "의장 기자회견 2026-10-28(예비 녹취록 14쪽): 권고는 'will be fed into the FOMC probably early in the " +
      "first quarter, but don't hold me exactly to that timing.' — 2027년 1분기 초쯤이고 시기는 단정하지 않았습니다. 8쪽: 태스크포스 " +
      "다섯 개에 연말 마감. (federalreserve.gov/mediacenter/files/FOMCpresconf20261028.pdf)"]
  ];
  const DAY = /^\d{4}-\d{2}-\d{2}$/;
  // 권장 인용의 꼴 — '…, retrieved from …, November 3, 2026.'(scripts/fedbs_fetch.py citation). 꼴이 다르면 싣지 않는다
  const CITE = /^[^<>]{1,300}, retrieved from [^<>]{1,300}, [A-Z][a-z]+ \d{1,2}, \d{4}\.$/;
  const CITE_LICENCE = ["citation-required", "nyfed-terms"];
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
  // 숫자·날짜 토막(부호·쉼표·소수·날짜 범위·bn·bp·%·바로 붙은 짧은 괄호·'께')을 span.nw로 — 글자는 그대로, 줄 중간에서만 끊지 않게
  const NUM = /[+-]?\d[\d,.]*(?:[-~/][+-]?\d[\d,.]*)*(?:bn|bp|%p|%)?(?:\([^()\s]{1,8}\))?(?:께)?/g;
  function nw(t) {
    const out = [];
    let at = 0;
    for (const m of String(t).matchAll(NUM)) {
      if (m.index > at) out.push(t.slice(at, m.index));
      out.push(el("span", { class: "nw" }, m[0]));
      at = m.index + m[0].length;
    }
    if (at < t.length) out.push(t.slice(at));
    return out;
  }
  // RMP 칸의 view — 정해 둔 꼴(글자열·줄 수 상한)일 때만 나눠 그린다. 아니면 null(숫자 줄과 덧줄만 그린다)
  function rmpView(v) {
    const str = x => typeof x === "string" && x !== "" && x.length <= 400;
    const strs = (a, lo, hi) => Array.isArray(a) && a.length >= lo && a.length <= hi && a.every(str);
    const pair = x => isObj(x) && str(x.tag) && str(x.text);
    if (!isObj(v) || !str(v.window) || !strs(v.head, 1, 5) || typeof v.dates !== "string" || !str(v.caption) || !str(v.mean) ||
        !pair(v.bridge) || !pair(v.floor) || !strs(v.notes, 1, 4) || !isObj(v.table) || !strs(v.table.head, 4, 4) ||
        !Array.isArray(v.table.rows) || v.table.rows.length < 1 || v.table.rows.length > 6 ||
        !v.table.rows.every(r => isObj(r) && strs(r.cells, 4, 4) && typeof r.note === "string")) return null;
    return v;
  }
  function rmpRow(it, name) {
    const v = rmpView(it.view);
    if (!v) return null;
    const t = v.table;
    const table = el("table", { class: "ai-table rmp-table" },
      el("caption", { class: "sr" }, v.caption.split(" — ")[0]),
      el("thead", {}, el("tr", {}, ...t.head.map(h => el("th", { scope: "col" }, h)))),
      el("tbody", {}, ...t.rows.map(r => el("tr", {},
        el("th", { scope: "row" }, r.cells[0], r.note ? el("small", {}, r.note) : null),
        ...r.cells.slice(1).map(c => el("td", {}, c))))));
    // 직전 값을 다시 실을 때 — 머리의 '지금 창'·다음 날짜는 그 값을 받은 날 기준이라 알림을 머리 바로 위에 둔다(긴 칸의 끝에
    // 두면 화면 밖)
    const old = it.stale === true;
    return el("div", { class: "oil-row fedbs-row fedbs-rmp" },
      el("p", { class: "oil-name" }, el("strong", {}, name), " ", el("small", {}, ...nw(v.window))),
      old ? rmpStale(it) : null,
      el("p", { class: "oil-num rmp-head" }, el("strong", {}, ...nw(v.head[0])), ...v.head.slice(1).flatMap(h => [" · ", ...nw(h)])),
      v.dates ? el("p", { class: "rmp-dates" }, ...nw(v.dates)) : null,
      el("div", { class: "rmp-grid" },
        el("p", { class: "muted rmp-cap" }, ...nw(v.caption)),
        el("div", { class: "ai-table-wrap rmp-wrap" }, table),
        el("p", { class: "muted rmp-mean" }, ...nw(v.mean))),
      el("p", { class: "oil-num rmp-bridge" }, el("span", { class: "rmp-tag" }, v.bridge.tag), " ", ...nw(v.bridge.text)),
      el("p", { class: "oil-num rmp-floor" }, el("span", { class: "rmp-tag" }, v.floor.tag), " ", ...nw(v.floor.text)),
      ...v.notes.map(n => el("p", { class: "muted" }, ...nw(n))));
  }
  function rmpStale(it) {
    const got = day(it.retrieved);
    const since = day(it.failed_since) ? ` (${it.failed_since}부터)` : "";
    return el("p", { class: "oil-late" }, ...nw((got ? `이번 갱신의 값을 싣지 못해 ${got}에 받은 값을 싣습니다 — 이 칸의 '지금 창'·'다음 날짜'도 그날 기준`
      : "이번 갱신의 값을 싣지 못해 직전에 받은 값을 싣습니다 — 이 칸의 '지금 창'·'다음 날짜'도 그때 기준") + since));
  }
  function row(it, key) {
    if (it === undefined && OPTIONAL.includes(key)) return null;
    const name = isObj(it) && typeof it.name === "string" && it.name ? it.name : key;
    if (!usable(it, key))
      return el("div", { class: "oil-row fedbs-row" }, el("p", { class: "oil-name" }, el("strong", {}, name), " — ", missing(it)));
    if (key === "rmp_view") {
      const r = rmpRow(it, name);
      if (r) return r;
    }
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
  // 출처 — 칸마다의 FRED 시리즈 링크(link()는 FRED 주소만 링크로 건다)와 권장 인용은 자료 파일(sources[].citation)에.
  // 뉴욕 연은에서 직접 받은 것(DIRECT — 공식 계획 페이지·국채 운영 결과)은 FRED가 아니라 링크 없이 이름만 글자로
  function sourceLine(items) {
    const seen = new Map(), direct = new Set();
    for (const k of CARD) {
      const it = items[k];
      if (!usable(it, k)) continue;
      for (const s of Array.isArray(it.sources) ? it.sources : []) {
        if (!isObj(s) || typeof s.series !== "string" || !/^[A-Z0-9]+$/.test(s.series)) continue;
        if (Object.prototype.hasOwnProperty.call(DIRECT, s.series)) direct.add(s.series);
        else if (!seen.has(s.series)) seen.set(s.series, s.url);
      }
    }
    if (!seen.size && !direct.size) return null;
    const parts = [...seen].flatMap(([sid, url], i) => (i ? [" · ", link(sid, url)] : [link(sid, url)]));
    const names = [PLAN, OPS].filter(x => direct.has(x)).map(x => DIRECT[x]).join(" · ");
    return el("p", { class: "source-link" }, "자료(연준 이사회 H.4.1 · 뉴욕 연은 · BEA — FRED 경유): ", ...parts,
      names ? (seen.size ? " · " : "") + names : null);
  }
  // 연준 대차대조표 정책 — 보이는 짧은 칸(고정 글)
  function policy() {
    return el("div", { class: "oil-row fedbs-policy" },
      el("p", { class: "oil-name" }, el("strong", {}, POLICY_HEAD), " ", el("small", {}, "기준일 " + POLICY_ASOF)),
      el("p", { class: "muted" }, POLICY_NOTE),
      ...POLICY.map(([h, t]) => el("p", {}, el("strong", {}, h), " · ", t)));
  }
  // 권장 인용 — 그린 칸의 출처 중 인용이 필요한 것(CITE_LICENCE)만, 시리즈마다 하나(가장 늦게 받은 칸의 것), 줄마다 글자로
  function citeLines(items) {
    const best = new Map();
    for (const k of CARD) {
      const it = items[k];
      if (!usable(it, k)) continue;
      const when = day(it.retrieved);
      for (const s of Array.isArray(it.sources) ? it.sources : []) {
        if (!isObj(s) || !CITE_LICENCE.includes(s.licence) || typeof s.series !== "string" || !/^[A-Z0-9]+$/.test(s.series)) continue;
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
      policy(),
      el("details", { class: "rule-detail rule-guide" }, el("summary", {}, "읽는 법 — 정의·측정 기록"),
        ...GUIDE.map(([h, text, to]) => el("p", {}, el("strong", {}, h), " · ", text, ...(to ? [link(to[0], to[1]), to[2]] : [])))),
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

  return Object.freeze({ render, CARD, REASONS, LABEL, ABOUT, OPS, PLAN, POLICY_HEAD, POLICY_ASOF });
})();
