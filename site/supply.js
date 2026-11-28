/* 미 국채 수급 참고 — data/supply.json(scripts/supply_fetch.py)과 data/tic.json(scripts/tic_fetch.py)을 한 장의 카드로 그린다 (2026-11-19).
   전에는 '10년 기간 프리미엄' 규칙 카드의 접는 설명(읽는 법) 안에 있던 '수급 참고' 칸(2026-10-14~)을, 운영자 결정('1번 카드로 꺼내고
   TIC도 추가해')으로 금리·커브 묶음의 참고 카드로 꺼내고 재무부 TIC 월간 해외 보유를 더했다. 이 사이트의 규칙 점검에 쓰지 않는다.
   자리: #supply-slot — index.html의 renderPublic이 금리·커브 묶음 끝, 기간 프리미엄 모형 대조(#tp-slot)·국채–OIS(#ois-slot) 뒤에 둔다
   (값 두 장 다음에 양 — 누가 들고 있나. 국채–OIS가 기간 프리미엄 바로 뒤라는 자리는 그대로). '10년 기간 프리미엄' 카드의 읽는 법
   흐름도에서 TFP로 가는 요인 둘이 딜러 재고와 해외 공적 수요라, 그 자리에는 이 카드를 가리키는 한 줄만 남았다(숫자는 여기에만).
   index.html의 el() · chartFigure()를 쓴다(부를 때 이미 정의돼 있다). 글자는 전부 el()의 텍스트로만 넣는다(자료를 HTML로 해석하지 않는다).
   주간 — 뉴욕 연은 · 연준 H.4.1(딜러 재고는 뉴욕 연은, 해외 공적 수탁은 연준 이사회 H.4.1의 WMTSECL1 — FRED 경유. 뉴욕 연은은 그
   국채를 보관할 뿐 이 숫자를 내지 않는다 — 2026-11-19 2차 검토 반영): 글자는 supply.json에 정해 둔 문구를 글자로만 싣는다. 형식이 어긋난 쪽은 '자료 없음' 한 줄, 딜러 두 쪽은 뉴욕 연은
   출처 표기(notices)가 없으면 숫자를 싣지 않는다(SOFR과 같은 원칙). 7~11년 쪽은 숫자만 — 자료 파일에 ⚠ 줄이 있어도 싣지 않고, 그 쪽이
   없던 때의 자료 파일이면 줄을 두지 않는다. 그래프는 charts.js 그대로(끝 값은 줄과 같은 꼴 — 천 단위 쉼표). 고지는 숫자를 실은 쪽의
   것을 겹치지 않게 모아 주간 부분 끝에 한 번(2026-11-19 검토 반영 — 전엔 쪽마다라 같은 뉴욕 연은 고지가 두 번 나왔다). 지표의 뜻 ·
   p5/p95 · ⚠ 줄의 운영자 메모 · 7~11년의 까닭은 접는 '읽는 법 — 주간 숫자'에, ⚠ 줄이 실린 날만 그 줄 바로 아래에 운영자 메모라는 한 줄.
   월간 — 재무부 TIC: 그래프는 chart(전체·공적) · chart_countries(큰 보유 나라) · chart_korea(한국) 가운데 있는 것만.
   합계 줄과 나라 표의 칸은 tic.json의 숫자로 여기서 만든다(정수 bn · 변화는 부호 · 천 단위 쉼표 · 0은 부호 없이 ·
   비중은 소수 한 자리 — 자료 파일의 lines는 JSON을 직접 읽는 사람용이라 읽지 않는다). 나라 표는 rank 차례로 다시 놓는다(자료 파일의
   차례는 재무부 표의 차례라 순위와 다를 수 있다). 월·전체 보유가 어긋나거나 고지(notices)가 없으면
   숫자를 싣지 않고 '자료 없음'. 실패 사유 글은 싣지 않는다(자료 파일의 error는 원자료를 읽는 사람용). 단서(나라의 뜻 · 잔액 차 ≠
   순매입 · 개정 · TIC 공적과 WMTSECL1의 차이)·출처 글은 이 파일에 정해 둔 것이다. 주간 수탁과 월간 공적의 두 숫자는 그 차이 한 줄을
   붙여 합계 줄 바로 아래에(늘 보이게). 숫자·날짜 토막은 span.nw로 감싸 좁은 화면에서도 가운데서 끊지 않는다(글자는 그대로).
   재무부 주소는 링크 허용 목록(index.html의 safeUrl) 밖이라 글자로만 싣는다. 로고·그림 없음.
   한쪽이 없거나 깨졌으면 그쪽만 '자료 없음', 두 쪽 모두 쓸 것이 없으면 카드를 두지 않고 false. 바깥 요청은 없다. */
"use strict";
window.SupplyCard = (() => {
  const TITLE = "미 국채 수급 — 딜러 재고 · 해외 보유";
  const LABEL = "참고 — 예측 아님 · 판정에 쓰지 않음";
  // 카드 머리는 두 문장만(2026-11-19 검토 반영 — 긴 설명은 부분마다 접는 '읽는 법'으로)
  // 출처는 숫자마다 — 딜러 재고는 뉴욕 연은, 해외 공적 수탁은 연준 H.4.1(뉴욕 연은은 보관만 한다, 2026-11-19 2차 검토 반영)
  const ABOUT = "미 국채를 누가 들고 있는지 보는 공개 통계입니다. 위는 매주 나오는 숫자(뉴욕 연은의 딜러 재고 · 연준 H.4.1의 해외 " +
    "공적 수탁), 아래는 매달 나오는 재무부 TIC 숫자(해외 보유 전체 · 나라별, 한국 포함)입니다.";

  // ── 주간 — 뉴욕 연은 · 연준 H.4.1(전엔 index.html의 supplyPanel · supplySide) ───────────────────────────────────
  // 머리는 '월간 — 재무부 TIC'처럼 숫자를 낸 곳 — 딜러 재고는 뉴욕 연은, 해외 공적 수탁은 연준 이사회 H.4.1(2026-11-19 2차 검토 반영)
  const WEEKLY = "주간 — 뉴욕 연은 · 연준 H.4.1";
  const WEEKLY_GUIDE = [
    ["딜러 재고", "뉴욕 연은이 집계하는 프라이머리 딜러의 국채(TIPS 제외) 순포지션입니다."],
    ["해외 공적 수탁", "뉴욕 연은이 해외 중앙은행 등 공적·국제 기관을 위해 보관하는 국채로, 숫자는 연준 이사회의 주간 H.4.1(FRED " +
      "WMTSECL1)에서 옵니다. 보관 국채가 줄었다고 곧 판 것으로 볼 수는 없습니다(다른 보관 기관으로 옮겼을 수도 있습니다)."],
    ["p5·p95와 ⚠ 줄", "p5·p95는 표본 시작(각 줄에 적힌 해) 이후 모든 4주 변화 가운데 아래·위 5% 경계입니다. 마지막 4주 변화가 그 " +
      "밖이면 ⚠ 줄이 붙고, 줄 끝의 구절은 운영자 메모를 옮긴 참고이며 예측이 아닙니다."],
    ["딜러 이표채 7~11년", "10년 금리 구간의 딜러 재고입니다. 만기마다 다를 수 있는 효과가 합계로는 가려진다는 운영자 메모에 따라 " +
      "숫자만 싣습니다(⚠ 줄 없음)."],
    ["기간 프리미엄과의 관계", "‘10년 기간 프리미엄’ 카드의 흐름도에서 TFP(기간 자금 보상)로 가는 요인 가운데 둘이 딜러 재고와 해외 " +
      "공적 수요입니다. 이 카드의 숫자는 그 규칙의 판정에 쓰지 않습니다."]
  ];
  // ⚠ 줄이 실린 날만 그 줄 바로 아래에 — 줄 끝 구절이 무엇인지(접는 설명을 열지 않아도)
  const FLAG_NOTE = "⚠ 줄 끝의 구절은 운영자 메모를 옮긴 참고이며 예측이 아닙니다.";
  // [자료 파일의 키, 이름, 뉴욕 연은 출처 표기가 있어야 숫자를 싣는가, ⚠ 줄을 싣는가, 그 쪽이 없는 옛 파일이면 줄을 두지 않는가]
  const SIDES = [["dealer", "딜러 국채 순포지션", true, true, false], ["custody", "해외 공적 수탁 국채", false, true, false],
    ["dealer_7_11", "딜러 이표채 7~11년 순포지션", true, false, true]];
  const OLD_DAYS = 21;               // 마지막 관측이 이보다 묵으면 날짜 옆에 경과일을(딜러는 보통 1~2주, 수탁은 약 1주 늦게 나온다)
  const DAY = /^\d{4}-\d{2}-\d{2}$/;
  const texts = v => (Array.isArray(v) ? v : []).filter(x => typeof x === "string" && x);
  const isObj = v => !!v && typeof v === "object" && !Array.isArray(v);
  const num = v => typeof v === "number" && Number.isFinite(v);
  const sep = s => s.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  // 7~11년 쪽 그래프의 끝 값·읽기 글자 — 그 줄처럼 부호 붙인 정수 bn(기본 꼴은 100 미만에서 소수 둘째 자리)
  const signedBn = v => {
    const s = Math.abs(v).toFixed(0), sign = Number(s) === 0 ? "" : v < 0 ? "-" : "+";
    return sign + sep(s) + "bn";
  };
  const dayOf = s => (typeof s === "string" && DAY.test(s) ? Date.parse(s + "T00:00:00Z") : NaN);
  const nw = t => el("span", { class: "nw" }, t);           // 줄 가운데서 끊지 않는 토막(날짜 · 숫자와 그 이름)
  // ' · '로 이은 토막들 — 토막 안에서는 끊지 않고 ' · '에서만 접는다(글자는 그대로)
  const pieces = parts => parts.flatMap((p, i) => (i ? [" · ", nw(p)] : [nw(p)]));
  // 자료 파일의 숫자 줄(' · '로 이은 글) — 짧은 토막(2,524bn · 52주 -221)만 끊지 않고, 긴 토막(p5 · p95 괄호)은 그대로 접히게 둔다
  // (긴 토막까지 묶으면 320px 화면에서 가로로 넘칠 수 있다)
  const SHORT = 16;
  const soft = line => line.split(" · ").flatMap((p, i) => [...(i ? [" · "] : []), p.length <= SHORT ? nw(p) : p]);
  const bnText = v => {               // 수준 — 정수 bn, 천 단위 쉼표(9,241bn)
    const s = Math.abs(v).toFixed(0);
    return (v < 0 && Number(s) !== 0 ? "-" : "") + sep(s) + "bn";
  };

  // 한 쪽을 숫자로 실을 수 있는가 — 날짜·숫자 줄이 맞고, 출처 표기가 있어야 하는 쪽은 그것도
  function sideOk(s, attributed) {
    return isObj(s) && Number.isFinite(dayOf(s.date)) && typeof s.line === "string" && s.line !== "" &&
      (!attributed || texts(s.notices).length > 0);
  }
  // 한 쪽의 줄들 — 고지는 싣지 않는다(weekly가 숫자를 실은 쪽의 고지를 모아 한 번). 출처 표기가 있어야 하는 쪽은 그것이 없으면 '자료 없음'
  function side(s, name, attributed, flagged = true) {
    if (!sideOk(s, attributed)) return [el("p", { class: "supply-name" }, el("strong", {}, name), " — 자료 없음")];
    const age = Math.floor((Date.now() - dayOf(s.date)) / 864e5);
    const since = typeof s.failed_since === "string" && DAY.test(s.failed_since) ? ` (${s.failed_since}부터)` : "";
    const flag = flagged && typeof s.flag_text === "string" && s.flag_text ? s.flag_text : null;
    return [
      el("p", { class: "supply-name" }, el("strong", {}, typeof s.name === "string" && s.name ? s.name : name), " ",
        el("small", {}, nw(s.date), " 관측" + (age > OLD_DAYS ? ` · ${age}일 전` : ""))),
      el("p", { class: "supply-num" }, ...soft(s.line)),
      flag ? el("p", { class: "supply-flag" }, flag) : null,
      flag ? el("p", { class: "muted supply-flag-note" }, FLAG_NOTE) : null,
      ...texts(s.extra).map(t => el("p", { class: "muted" }, t)),
      s.stale === true ? el("p", { class: "supply-late" }, "이번 갱신에서 받지 못해 직전에 받은 값을 싣습니다" + since) : null,
      // 끝 값·읽기 글자도 줄과 같은 꼴 — 합계·수탁은 천 단위 쉼표 정수 bn(2,524bn), 7~11년은 부호 붙인 정수 bn
      chartFigure(s.chart, 150, false, undefined, flagged ? bnText : signedBn)
    ];
  }
  const weeklyOk = d => isObj(d) && SIDES.some(([key, , attributed]) => sideOk(d[key], attributed));
  function weekly(d) {
    const head = el("h4", { id: "supply-weekly-title" }, WEEKLY);
    const box = (...kids) => el("section", { class: "supply-part", "aria-labelledby": "supply-weekly-title" }, head, ...kids);
    if (!d || typeof d !== "object") return box(el("p", { class: "muted" }, "자료 없음"));
    const shown = SIDES.filter(([key, , , , optional]) => !(optional && d[key] === undefined));
    const notices = [];                 // 숫자를 실은 쪽의 고지 — 같은 글은 한 번(차례는 처음 나온 대로)
    for (const [key, , attributed] of shown)
      if (sideOk(d[key], attributed)) for (const t of texts(d[key].notices)) if (!notices.includes(t)) notices.push(t);
    return box(
      ...shown.map(([key, name, attributed, flagged]) => el("div", { class: "supply-row" }, ...side(d[key], name, attributed, flagged))),
      el("details", { class: "rule-detail rule-guide" }, el("summary", {}, "읽는 법 — 주간 숫자"),
        ...WEEKLY_GUIDE.map(([h, text]) => el("p", {}, el("strong", {}, h), " · ", text))),
      notices.length ? el("div", { class: "notices" }, ...notices.map(t => el("p", {}, t))) : null);
  }

  // ── 월간 — 재무부 TIC ────────────────────────────────────────────────────────────────────────────────────
  const MONTHLY = "월간 — 재무부 TIC";
  const MONTHLY_ABOUT = "재무부 TIC(Treasury International Capital) 표 ‘Major Foreign Holders of Treasury Securities’의 월말 보유 " +
    "잔액입니다(십억 달러). 재무부는 매달 18일 무렵 두 달 전 월말 자료를 냅니다.";
  // 늘 보이는 단서 한 줄 — 표를 사고판 양(순매입)이나 실제 주인의 나라로 읽지 않게. 자세한 것은 아래 접는 설명.
  // 나라는 '보관 기관이 있는 곳'이 아니다 — 미국 안의 보고 기관이 아는 보유자(또는 국채를 맡긴 해외 보관 기관)의 소재지(2026-11-19 검토 반영)
  const MONTHLY_NOTE = "변화는 월말 잔액의 차이일 뿐 사고판 양(순매입)이 아닙니다. 나라는 보고된 보유자(또는 해외 보관 기관)의 " +
    "소재지라 실제 주인의 나라와 다를 수 있습니다.";
  // 합계 줄 — [tic.json totals의 키, 이름(자료 파일에 이름이 없을 때 — tic_fetch.py의 TOTAL_NAME과 같은 글), 비중 칸, 비중의 기준]
  const TOTALS = [["grand", "해외 전체 보유", null, ""], ["official", "그중 해외 공적", "share_pct", "해외 전체의"],
    ["official_bills", "공적 중 단기채(T-bill)", "bills_share_of_official_pct", "공적의"],
    ["official_notes_bonds", "공적 중 이표채(T-note · T-bond)", null, ""]];
  const TOP = 10;                    // 짧은 표에 싣는 순위 — 한국은 순위와 상관없이 늘 싣는다
  const KOREA = "Korea, South";      // 재무부 표의 이름(자료 파일에 korea 칸이 없을 때만 이 이름으로 찾는다)
  const KOREA_MARK = "늘 싣는 줄";
  const GUIDE = [
    ["나라 ≠ 실제 주인일 수 있음", "재무부 표의 주석대로 이 숫자는 주로 미국 안의 보관 기관·증권사가 보고한 것이고, 나라는 그들이 " +
      "아는 보유자(또는 국채를 맡긴 해외 보관 기관)의 소재지입니다. 해외 보관 계좌에 든 국채는 실제 주인의 나라로 잡히지 않을 수 " +
      "있습니다(TIC FAQ 7번). 벨기에·룩셈부르크·케이맨 제도·영국처럼 보관·운용 기관이 모인 곳의 숫자에는 다른 나라 투자자의 몫이 " +
      "섞일 수 있습니다."],
    ["잔액 차 ≠ 순매입", "숫자는 월말 보유 잔액이고, 1개월·12개월은 그 잔액의 차이입니다. 가격·평가의 변화와 보관 기관을 옮긴 것도 " +
      "잔액을 바꾸므로, 줄었다고 곧 판 것으로, 늘었다고 곧 산 것으로 볼 수 없습니다. 재무부는 거래(순매입) 자료를 따로 내지만 이 카드에는 " +
      "싣지 않습니다."],
    // 한쪽이 다른 쪽의 일부라고 쓰지 않는다(2026-11-19 검토 반영) — 해외 보관 기관을 거친 공적 보유는 TIC에서 공적으로 잡히지 않을 수
    // 있고, WMTSECL1은 해외 공적·국제 기관 몫이라 범위가 다르다. 평가 기준은 1차 출처로 확인하지 못해 '다를 수 있습니다'까지만
    ["해외 공적과 주간 수탁의 차이", "‘그중 해외 공적’은 미국 안의 보관 기관·증권사가 외국 중앙은행·정부 등 공적 기관의 보유로 " +
      "보고한 값입니다(해외 보관 기관을 거친 몫은 공적으로 잡히지 않을 수 있습니다). 위 주간의 ‘해외 공적 수탁 국채’(WMTSECL1)는 " +
      "뉴욕 연은이 해외 공적·국제 기관을 위해 보관하는 국채라 범위가 다르고, 재는 때(주간은 수요일, 월간은 월말)와 평가 기준도 다를 " +
      "수 있습니다. 두 숫자를 같은 양으로 보지 않습니다."],
    ["단기채와 이표채", "공적 보유를 단기채(T-bill)와 이표채(T-note · T-bond)로 나눈 것도 재무부 표의 줄입니다. 재무부는 이표채를 " +
      "월간 SLT 보고, 단기채를 BL2 보고로 추정합니다(표의 주석)."],
    ["나라 표", "상위 10곳과 한국을 싣고 나머지는 ‘전체 목록’에 접어 둡니다. 순위는 마지막 달 보유가 큰 차례입니다. 재무부 표에 " +
      "드는 나라(20곳)는 달마다 바뀔 수 있고, 표에 없는 나라는 ‘그 밖’에 들어 있습니다. 비중은 해외 전체 보유 대비이고, 변화를 셀 수 " +
      "없는 칸은 ‘—’입니다."],
    ["개정과 그래프", "재무부는 지난 달 숫자를 고쳐 다시 내기도 합니다. 그래프는 2011년 12월부터 연도별 기록 파일과 지금 표를 이은 " +
      "것입니다. 겹치는 달은 지금 표의 값이고, 지금 표에서 빠진 달도 연도별 기록 파일에서 그 해의 날짜가 그 표를 받은 날과 " +
      "같거나 뒤가 되기 전까지는 전에 받은 표의 값을 둡니다. 그 해의 날짜는 파일에 해마다 적힌 개정일이고, 개정일이 적히지 않은 " +
      "해는 전에 적어 둔 그 해의 날짜(처음 보는 해는 그 파일의 날짜)입니다 — 파일 날짜는 다른 해를 고쳐도 바뀌므로, " +
      "이미 본 해를 새로 고친 것으로 치는 데는 쓰지 않습니다. 2011년 12월부터 모든 달의 이표채 보유가 월간 SLT 보고 " +
      "기준이라(그 파일의 주석 17번), 그 앞(이표채 집계 방식이 달라 이어지지 않는 곳이 있음)은 그래프에 넣지 않습니다."],
    ["발표", "재무부는 매달 18일 무렵 두 달 전 월말 자료를 냅니다(예: 2026년 9월 말 자료는 2026-11-18). 연도별 기록 파일은 정해진 때 " +
      "없이 고쳐 나옵니다(그 파일의 개정 기록으로는 2026년에만 1·7·9월)."]
  ];
  // 출처 — 자료 파일과 상관없이 이 글로만 싣는다. 주소는 글자로만(링크는 FRED·GitHub에만 건다)
  const SOURCE = "U.S. Department of the Treasury, Treasury International Capital (TIC) System — Major Foreign Holders of Treasury Securities";
  const SOURCE_AT = "ticdata.treasury.gov — 표 5(slt_table5.txt) · 연도별 기록(mfhhis01.txt)";
  const MONTH = /^\d{4}-(0[1-9]|1[0-2])$/;

  const chgText = v => {              // 변화 — 부호 붙인 정수(0은 부호 없이), 셀 수 없으면 —
    if (!num(v)) return "—";
    const s = Math.abs(v).toFixed(0);
    return (Number(s) === 0 ? "" : v < 0 ? "-" : "+") + sep(s);
  };
  const pctText = v => (num(v) ? v.toFixed(1) + "%" : "—");
  const totalParts = t => [bnText(t.level_bn), `1개월 ${chgText(t.chg_1m_bn)}`, `12개월 ${chgText(t.chg_12m_bn)}`];
  const rowOk = c => isObj(c) && typeof c.name_en === "string" && c.name_en !== "" && num(c.level_bn);
  const nameOf = c => (typeof c.name_ko === "string" && c.name_ko ? c.name_ko : c.name_en);
  const ranked = c => Number.isInteger(c.rank) && c.rank > 0;

  function ticOk(t) {
    return isObj(t) && typeof t.month === "string" && MONTH.test(t.month) && isObj(t.totals) && isObj(t.totals.grand) &&
      num(t.totals.grand.level_bn) && texts(t.notices).length > 0;
  }
  // 자료 달이 재무부 발표보다 묵었나 — 25일 이후면 두 달 전, 그 전이면 세 달 전 달까지는 나와 있을 때다(발표는 18일 무렵)
  function behind(month) {
    const now = new Date(Date.now()), [y, m] = month.split("-").map(Number);
    const want = now.getUTCFullYear() * 12 + now.getUTCMonth() - (now.getUTCDate() >= 25 ? 2 : 3);
    return y * 12 + (m - 1) < want;
  }
  function koreaOf(t, rows) {
    if (t.korea === null) return null;
    if (rowOk(t.korea)) return rows.find(c => c.name_en === t.korea.name_en) || t.korea;
    return rows.find(c => c.name_en === KOREA) || null;
  }
  // 한 줄 — 한국 줄은 바탕·왼쪽 선(tic-korea)에 더해, 짧은 표에서만 글자 표시('늘 싣는 줄' — 모든 줄이 있는 전체 목록에서는 뜻이 없다)
  function tr(c, korea, mark = true) {
    const k = c === korea;
    return el("tr", k ? (mark ? { class: "tic-korea", id: "supply-korea-row" } : { class: "tic-korea" }) : {},
      el("td", {}, ranked(c) ? String(c.rank) : "—"),
      el("th", { scope: "row" }, nameOf(c), k && mark ? el("small", { class: "tic-mark" }, " · " + KOREA_MARK) : null),
      el("td", {}, bnText(c.level_bn)), el("td", {}, chgText(c.chg_1m_bn)), el("td", {}, chgText(c.chg_12m_bn)),
      el("td", {}, pctText(c.share_pct)));
  }
  function table(caption, body, foot) {
    const head = el("tr", {}, ...["순위", "나라", "보유(bn)", "1개월", "12개월", "비중"].map(h => el("th", { scope: "col" }, h)));
    return el("div", { class: "tic-scroll" }, el("table", { class: "tic-table" }, el("caption", {}, caption),
      el("thead", {}, head), el("tbody", {}, ...body), foot ? el("tfoot", {}, foot) : null));
  }
  // 짧은 표에 한국 줄이 그려지나(countries와 같은 판단 — 바로 가기의 '한국 줄' 단추를 둘지)
  function koreaShown(t) {
    const rows = (Array.isArray(t.countries) ? t.countries : []).filter(rowOk);
    return rows.some(ranked) && !!koreaOf(t, rows);
  }
  function countries(t) {
    const rows = (Array.isArray(t.countries) ? t.countries : []).filter(rowOk);
    // 순위 차례로(같은 순위는 원래 차례 — 정렬은 안정). 자료 파일의 차례는 재무부 표의 차례라 순위와 다를 수 있다(2026-11-19 검토 반영)
    const listed = rows.filter(ranked).sort((a, b) => a.rank - b.rank), korea = koreaOf(t, rows);
    if (!listed.length) return [];
    const top = listed.slice(0, TOP), out = [];
    const body = top.map(c => tr(c, korea));
    if (korea && !top.includes(korea)) {
      const at = ranked(korea) ? korea.rank : null, from = top[top.length - 1].rank + 1;
      if (at === null || at > from) body.push(el("tr", { class: "tic-gap" },
        el("td", { colspan: "6" }, at === null ? `${from}위 아래는 ‘전체 목록’에`
          : at - 1 === from ? `${from}위는 ‘전체 목록’에` : `${from}~${at - 1}위는 ‘전체 목록’에`)));
      body.push(tr(korea, korea));
    }
    // 한국 줄이 없으면 머리에 '한국'을 적지 않는다 — 바로 아래 줄이 없다고 말한다(2026-11-19 2차 검토 반영). 표의 곳 수도 실제 줄 수
    out.push(table(`상위 ${top.length}곳${korea ? "과 한국" : ""} — ${t.month} 말`, body));
    if (!korea) out.push(el("p", { class: "muted" }, `한국은 이번 달 재무부 표(상위 ${listed.length}곳)에 없습니다 — ‘그 밖’에 들어 있습니다.`));
    const g = t.totals.grand;
    const foot = el("tr", {}, el("td", {}, ""), el("th", { scope: "row" }, "해외 전체"), el("td", {}, bnText(g.level_bn)),
      el("td", {}, chgText(g.chg_1m_bn)), el("td", {}, chgText(g.chg_12m_bn)), el("td", {}, "100.0%"));
    const others = rows.filter(c => !ranked(c));
    out.push(el("details", { class: "rule-detail tic-all" },
      el("summary", {}, `전체 목록 — ${listed.length}곳` + (others.length ? " · 그 밖" : "") + " · 해외 전체"),
      table(`재무부 표의 모든 줄 — ${t.month} 말`, [...listed, ...others].map(c => tr(c, korea, false)), foot)));
    return out;
  }
  // 그래프 선마다 마지막 값 — ['2026-09 말: ', span '일본 1,063bn', ' · ', …] 또는 null(선이 하나뿐이거나 꼴이 어긋나면).
  // 마지막 점의 날짜가 모두 같을 때만(선마다 다르면 한 줄로 묶지 않는다)
  function lastValues(spec) {
    if (!isObj(spec) || !Array.isArray(spec.lines) || spec.lines.length < 2) return null;
    const ends = [];
    for (const line of spec.lines) {
      const pts = isObj(line) && Array.isArray(line.points) ? line.points : [];
      const p = [...pts].reverse().find(q => Array.isArray(q) && q.length === 2 && DAY.test(String(q[0])) && num(q[1]));
      if (!p || typeof line.label !== "string" || !line.label) return null;
      ends.push([p[0], `${line.label} ${bnText(p[1])}`]);
    }
    if (ends.some(e => e[0] !== ends[0][0])) return null;
    return [`${ends[0][0].slice(0, 7)} 말: `, ...pieces(ends.map(e => e[1]))];
  }
  function monthly(t, supply) {
    const head = el("h4", { id: "supply-monthly-title" }, MONTHLY);
    const box = (...kids) => el("section", { class: "supply-part", "aria-labelledby": "supply-monthly-title" }, head, ...kids);
    if (!ticOk(t)) return box(el("p", { class: "muted" }, "자료 없음"));
    const retrieved = typeof t.retrieved === "string" && DAY.test(t.retrieved) ? t.retrieved : null;
    const since = typeof t.failed_since === "string" && DAY.test(t.failed_since) ? ` (${t.failed_since}부터)` : "";
    const prev = typeof t.prev_month === "string" && MONTH.test(t.prev_month) ? t.prev_month : null;
    const ago = typeof t.year_ago === "string" && MONTH.test(t.year_ago) ? t.year_ago : null;
    const totals = TOTALS.filter(([k]) => isObj(t.totals[k]) && num(t.totals[k].level_bn)).map(([k, name, shareKey, base]) => {
      const x = t.totals[k], share = shareKey === null ? null : shareKey === "share_pct" ? x.share_pct : t.totals[shareKey];
      return el("p", { class: "tic-total" }, el("strong", {}, typeof x.name === "string" && x.name ? x.name : name), " ",
        el("span", { class: "supply-num" }, ...pieces([...totalParts(x), ...(num(share) ? [`${base} ${pctText(share)}`] : [])])));
    });
    const fmt = v => bnText(v);       // 그래프 끝 값·읽기 글자도 위 줄과 같은 꼴(9,241bn)
    // 그래프 — 전체·공적, 큰 보유 나라, 한국(값의 크기가 달라 따로). 없거나 그리지 못한 그래프는 빠질 뿐.
    // 나라 그래프는 끝 값 글자가 겹치면(일본과 영국처럼 가까우면) charts.js가 뒤의 것을 빼므로, 그래프 아래에 선마다의 마지막 값 한 줄
    const figs = [[t.chart, false], [t.chart_countries, true], [t.chart_korea, false]].flatMap(([spec, ends]) => {
      const f = chartFigure(spec, 190, true, false, fmt);
      if (!f) return [];
      const last = ends ? lastValues(spec) : null;
      return [el("div", { class: "supply-row" }, f, last ? el("p", { class: "muted tic-ends" }, ...last) : null)];
    });
    // TIC 공적과 주간 수탁(WMTSECL1)의 이번 숫자 — 두 자료가 다 있을 때만, 같은 양이 아니라는 한 줄로 공적 합계 바로 아래에(늘 보이게)
    const c = isObj(supply) && sideOk(supply.custody, false) && num(supply.custody.level_bn) ? supply.custody : null;
    const o = isObj(t.totals.official) && num(t.totals.official.level_bn) ? t.totals.official : null;
    const pair = c && o ? el("p", { class: "muted tic-pair" }, "위 주간의 해외 공적 수탁(뉴욕 연은 보관, ", nw(`${c.date} ${bnText(c.level_bn)}`),
      ")은 이 ‘그중 해외 공적’과 범위·재는 때가 달라 같은 양이 아닙니다 — 아래 ‘읽는 법’.") : null;
    return box(
      el("p", { class: "muted" }, MONTHLY_ABOUT),
      el("p", { class: "supply-name" }, el("strong", {}, "재무부 TIC 해외 보유"), " ",
        el("small", {}, nw(`${t.month} 말 기준`), ...(retrieved ? [" · ", nw(`받은 날 ${retrieved}`)] : []),
          behind(t.month) ? " · 다음 달 자료를 아직 받지 못함" : null)),
      t.stale === true ? el("p", { class: "supply-late" }, "이번 갱신에서 받지 못해 직전에 받은 값을 싣습니다" + since) : null,
      el("div", { class: "supply-row tic-totals" }, ...totals),
      pair,
      el("p", { class: "tic-note" }, MONTHLY_NOTE),
      // 비중의 기준은 줄마다 적는다(공적은 '해외 전체의', 단기채는 '공적의') — 이 한 줄은 그 기준을 하나로 묶지 않고 나라 표의 비중만
      // (2026-11-19 2차 검토 반영 — 전엔 '비중은 해외 전체 보유 대비'라 바로 위 단기채 줄의 '공적의 7.9%'와 어긋났다)
      el("p", { class: "muted" }, prev && ago ? `1개월·12개월은 ${prev} 말·${ago} 말 잔액과의 차(bn)이고, 나라 표의 비중은 해외 전체 보유 대비입니다.`
        : "1개월·12개월은 한 달 전·1년 전 월말 잔액과의 차(bn)이고, 나라 표의 비중은 해외 전체 보유 대비입니다."),
      ...countries(t),
      ...figs,
      el("details", { class: "rule-detail rule-guide" }, el("summary", {}, "읽는 법 — TIC 숫자의 단서"),
        ...GUIDE.map(([h, text]) => el("p", {}, el("strong", {}, h), " · ", text))),
      el("div", { class: "notices" }, ...texts(t.notices).map(x => el("p", {}, x))),
      el("p", { class: "source-link" }, "자료: " + SOURCE + " (" + SOURCE_AT + ")"));
  }

  // 카드 머리 아래 바로 가기 — 카드가 길어(주간 그래프 셋 뒤에 월간) 월간 부분과 한국 줄로 곧장 내려가게(2026-11-19 검토 반영).
  // 주소(#…)를 쓰지 않는다 — 화면 이동이 주소의 #보기 이름을 쓰므로, 누르면 그 자리로 스크롤하고 초점만 옮긴다
  function jump(label, id) {
    const b = el("button", { type: "button", class: "supply-jump-btn" }, label);
    b.addEventListener("click", () => {
      const t = document.getElementById(id);
      if (!t) return;
      t.setAttribute("tabindex", "-1");
      t.scrollIntoView({ block: "start" });
      t.focus({ preventScroll: true });
    });
    return b;
  }
  function card(weeklyPart, monthlyPart, monthlyShown, koreaShown) {
    const nav = monthlyShown ? el("p", { class: "supply-jump" }, "바로 가기 ", jump("월간 — 재무부 TIC", "supply-monthly-title"),
      koreaShown ? " " : null, koreaShown ? jump("한국 줄", "supply-korea-row") : null) : null;
    return el("article", { class: "oil-card supply-card", "aria-labelledby": "supply-title" },
      el("h3", { id: "supply-title" }, TITLE, el("span", { class: "reference-label" }, LABEL)),
      el("p", { class: "muted" }, ABOUT),
      nav, weeklyPart, monthlyPart);
  }
  // 두 자료 파일을 #supply-slot에. 한쪽만 쓸 수 있으면 다른 쪽은 '자료 없음', 둘 다 없으면 카드를 두지 않고 false.
  // 한 부분을 그리다 깨지면 그 부분만 '자료 없음'(다른 부분은 그대로)
  // schema가 1이 아닌 파일은 없는 것과 같다 — 그쪽만 '자료 없음', 두 파일 모두 그러면 카드를 두지 않는다
  function render(supply, tic) {
    if (!isObj(supply) || supply.schema !== 1) supply = null;
    if (!isObj(tic) || tic.schema !== 1) tic = null;
    const slot = document.getElementById("supply-slot");
    if (!slot) return false;
    const w = weeklyOk(supply), m = ticOk(tic);
    if (!w && !m) { slot.replaceChildren(); return false; }
    let wk, mo, ok = m, korea = false;
    try { wk = weekly(w ? supply : null); } catch (e) { wk = weekly(null); }
    try { mo = monthly(m ? tic : null, w ? supply : null); korea = m && koreaShown(tic); } catch (e) { mo = monthly(null); ok = false; }
    // 바로 가기는 그 자리가 실제로 그려졌을 때만 — 월간 숫자(주간 부분 뒤에 있을 때)와 짧은 표의 한국 줄
    slot.replaceChildren(card(wk, mo, ok && w, korea));
    return true;
  }

  return Object.freeze({ render, weekly, side, monthly, weeklyOk, ticOk, bnText, chgText, pctText, signedBn,
    TITLE, LABEL, ABOUT, SIDES, GUIDE, WEEKLY_GUIDE, FLAG_NOTE, SOURCE, SOURCE_AT, MONTHLY_NOTE, TOTALS, KOREA_MARK, TOP });
})();
