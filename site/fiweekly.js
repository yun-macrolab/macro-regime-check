/* 평가사 주간 보고서 — data/fi_weekly.json(scripts/fi_weekly.py — 운영자 PC의 저녁 예약 작업이 올린다)을 그린다 (2026-11-23).
   두 채권 평가사(KIS자산평가 · 한국자산평가)의 최신 주간 보고서 하나씩: AI가 보고서의 요약 쪽과 주요 절의 본문을 읽고 주제별(국채 ·
   크레딧 · 단기자금 · 해외 금리 · 스왑)로 쓴 두세 문장씩과, KIS 보고서에
   적힌 평가사 산출값 열 칸(IRS · CRS · 스왑 스프레드 · 스왑 베이시스 1·3년, AA- · A- 회사채 3년 크레딧 스프레드). 한국자산평가는
   숫자 표를 만들지 않는다 — 요약 문장 속 숫자는 두 회사 같은 규칙(2026-11-23 운영자 결정). 이 사이트의 규칙 점검에 쓰지 않는다.
   자리: #fiweekly-body — 한국 시장 화면(세 칸 모두)의 지표 아래 절 #fiweekly-wrap. index.html의 applyView가 절을 보이고 숨긴다.
   index.html의 el()을 쓴다(부를 때 이미 정의돼 있다). 글자는 전부 el()의 텍스트로만 넣는다(자료를 HTML로 해석하지 않는다).
   링크는 두 곳의 정해 둔 꼴만 — KIS 보고서 글(https://www.bond.co.kr/post/dawn/<번호>, 그 주소가 PDF다)과 한국자산평가 게시판 화면.
   보고서 하나가 약속에 어긋나면 그 보고서만 뺀다. 그릴 보고서가 없으면 false를 돌려준다(절이 숨는다). 바깥 요청은 없다. */
"use strict";
window.FiWeekly = (() => {
  // 출처 차례와 이름 — scripts/fi_weekly.py의 SOURCES와 같다(scripts/test_fi_weekly.py가 견준다)
  const SOURCES = ["kis", "kap"];
  const NAMES = { kis: ["KIS자산평가", "KIS WEEKLY"], kap: ["한국자산평가", "Fixed Income Weekly"] };
  // 숫자 칸 — scripts/fi_weekly.py의 ROWS와 같은 열쇠 · 단위 · 차례(테스트가 견준다)
  const ROWS = [["irs_1y", "%"], ["irs_3y", "%"], ["crs_1y", "%"], ["crs_3y", "%"], ["ss_1y", "bp"], ["ss_3y", "bp"],
    ["basis_1y", "bp"], ["basis_3y", "bp"], ["aa_minus_3y", "bp"], ["a_minus_3y", "bp"]];
  // 표의 줄 — [이름, 1년 칸, 3년 칸]
  const SWAP = [["IRS", "irs_1y", "irs_3y"], ["CRS", "crs_1y", "crs_3y"], ["스왑 스프레드 (IRS − 국고)", "ss_1y", "ss_3y"],
    ["스왑 베이시스 (CRS − IRS)", "basis_1y", "basis_3y"]];
  const CREDIT = [["AA-", "aa_minus_3y"], ["A-", "a_minus_3y"]];
  // 요약의 주제 — scripts/fi_weekly.py의 TOPICS_OF와 같은 차례(테스트가 견준다). 주제 하나는 TOPIC_CHARS자까지, 둘 이상
  const TOPICS = { kis: ["국채", "크레딧", "단기자금", "해외 금리", "스왑"], kap: ["국채", "크레딧", "단기자금", "해외 금리"] };
  const TOPIC_CHARS = 230, MIN_TOPICS = 2;
  // 요약이 없는 사유 — scripts/fi_weekly.py의 NOTES와 같은 열쇠(테스트가 견준다)
  const NOTES = { model: "AI 요약을 만들지 못함", none: "AI가 요약하지 않음", shape: "요약이 꼴 검사에 걸림",
    banned: "요약에 쓰지 않는 말이 들어감", copy: "요약이 보고서 문장과 너무 비슷함", number: "요약의 숫자가 보고서와 맞지 않음",
    term: "요약의 낱말이 보고서와 맞지 않음", name: "요약의 이름이 보고서에 없음",
    text: "보고서에서 요약할 쪽을 찾지 못함" };
  const NUM_NOTES = { table: "보고서의 표를 읽지 못해 이번 호의 숫자는 싣지 않습니다" };
  const LABEL = "평가사 산출값 · AI 요약 — 참고";
  const AI_TAG = "AI 요약 — 틀릴 수 있습니다";
  const KAP_BOARD = "https://www.koreaap.com/kor/data01_02.html";
  const KIS_ITEM = /^https:\/\/www\.bond\.co\.kr\/post\/dawn\/[0-9]{1,9}$/;
  const ISSUE = { kis: /^[0-9]{1,5}$/, kap: /^[0-9]{2}-[0-9]{1,3}$/ };
  const DAY = /^\d{4}-\d{2}-\d{2}$/;
  const STALE_DAYS = 14;                       // 게시된 지 이만큼 지난 호는 '최근 호가 아닐 수 있음'
  const ABOUT = [
    "요약은 AI가 각 보고서의 요약 쪽과 주요 절(국공채 · 금융채 · 회사채 · 단기자금 · 해외 · 스왑)의 본문을 읽고 이 사이트의 말로 주제마다 " +
      "두세 문장씩 쓴 것입니다. 보고서의 문장이 아니며, 틀릴 수 있으니 원문을 확인하세요. 검사(전망 · 권유 같은 말, 보고서 문장과 너무 " +
      "비슷함, 보고서에 없는 숫자 · 이름)에 걸린 주제는 싣지 않습니다. 요약 속 숫자는 두 보고서 모두 보고서 글에 적힌 것만, 주제마다 " +
      "셋까지 씁니다.",
    "숫자는 KIS자산평가가 그 호에 적은 평가사 산출값을 옮긴 것이고, 스왑 스프레드(IRS − KIS 산출 국고) · 스왑 베이시스(CRS − IRS)와 " +
      "bp로 적은 전주 대비는 그 값으로 이 사이트가 뺀 것입니다. 최신 호만 싣고 지난 호의 숫자는 남기지 않습니다. 한국자산평가는 " +
      "숫자 표를 싣지 않습니다(요약 문장 속 숫자만).",
    "두 회사와 맺은 계약은 없습니다. 각 사가 누리집에 공개한 보고서를 받아 쓰며, 요청이 있으면 바로 내립니다. 예측이 아니고 이 사이트의 " +
      "규칙 판정에 쓰지 않습니다."
  ];
  const isObj = v => v && typeof v === "object" && !Array.isArray(v);
  const num = v => typeof v === "number" && Number.isFinite(v);
  const day = v => typeof v === "string" && DAY.test(v) && Number.isFinite(Date.parse(v + "T00:00:00Z"));

  function usableNumbers(n, date) {
    if (!isObj(n) || n.date !== date || n.credit_date !== date || !day(n.prev) || !day(n.credit_prev) || !isObj(n.rows)) return false;
    return ROWS.every(([k]) => Array.isArray(n.rows[k]) && n.rows[k].length === 2 && n.rows[k].every(num));
  }
  function usableSummary(r) {
    if (!Number.isInteger(r.summary_dropped) || r.summary_dropped < 0) return false;
    if (r.summary === null) return r.summary_dropped === 0;
    const topics = TOPICS[r.src];
    if (!Array.isArray(r.summary) || r.summary.length < MIN_TOPICS || r.summary.length > topics.length) return false;
    let last = -1;
    for (const x of r.summary) {
      const at = isObj(x) ? topics.indexOf(x.topic) : -1;
      if (at <= last || typeof x.text !== "string" || !x.text || x.text.length > TOPIC_CHARS) return false;   // 주제마다 하나 · 차례대로
      last = at;
    }
    return true;
  }
  function usable(r) {
    if (!isObj(r) || !SOURCES.includes(r.src) || typeof r.issue !== "string" || !ISSUE[r.src].test(r.issue)) return false;
    if (!day(r.date) || !day(r.posted) || r.posted < r.date) return false;
    if (r.src === "kis" ? !(typeof r.url === "string" && KIS_ITEM.test(r.url)) : r.url !== KAP_BOARD) return false;
    if (!usableSummary(r)) return false;
    if (r.src === "kis" && r.numbers !== null && !usableNumbers(r.numbers, r.date)) return false;
    return true;
  }
  function signed(v, digits) {
    const s = Math.abs(v).toLocaleString("ko-KR", { minimumFractionDigits: 1, maximumFractionDigits: digits });
    return (v > 0 ? "+" : v < 0 ? "-" : "") + s;
  }
  function value(v, unit) {
    const s = Math.abs(v).toLocaleString("ko-KR", unit === "%" ? { minimumFractionDigits: 2, maximumFractionDigits: 4 }
      : { minimumFractionDigits: 1, maximumFractionDigits: 2 });
    return (v < 0 ? "-" : "") + s + unit;
  }
  function cell(rows, key) {
    const [v, d] = rows[key], unit = ROWS.find(r => r[0] === key)[1];
    return el("td", {}, el("strong", {}, value(v, unit)), el("small", { class: "fi-chg" }, "전주 " + signed(d, 2) + "bp"));
  }
  function ageDays(posted, now) {
    return Math.floor((now - Date.parse(posted + "T00:00:00+09:00")) / 864e5);
  }
  function link(r) {
    const text = r.src === "kis" ? "보고서 PDF (bond.co.kr)" : "보고서 게시판 (koreaap.com)";
    return el("a", { href: r.url, rel: "noopener" }, text);
  }
  function numbers(r) {
    if (r.numbers === null) return el("p", { class: "market-warning" }, NUM_NOTES[r.numbers_note] || "이번 호의 숫자는 싣지 않습니다");
    const n = r.numbers;
    const swap = el("table", { class: "ktb fi-table", "aria-label": "KIS 산출 IRS · CRS · 스왑 스프레드 · 스왑 베이시스" },
      el("thead", {}, el("tr", {}, el("th", {}, "스왑 (" + n.date + ")"), el("th", {}, "1년"), el("th", {}, "3년"))),
      el("tbody", {}, ...SWAP.map(([name, a, b]) => el("tr", {}, el("th", {}, name), cell(n.rows, a), cell(n.rows, b)))));
    const credit = el("table", { class: "ktb fi-table", "aria-label": "KIS 산출 회사채 3년 크레딧 스프레드" },
      el("thead", {}, el("tr", {}, el("th", {}, "회사채 3년 크레딧 스프레드 (국고 대비)"), el("th", {}, "3년"))),
      el("tbody", {}, ...CREDIT.map(([name, k]) => el("tr", {}, el("th", {}, name), cell(n.rows, k)))));
    return el("div", { class: "fi-numbers" }, swap, credit,
      el("p", { class: "ch-note muted" }, "평가사 산출값 — KIS자산평가 KIS WEEKLY 제" + r.issue + "호, " + n.date + " 기준. 전주 대비는 " +
        n.prev + "(크레딧 " + n.credit_prev + ")과의 차, bp. 스왑 스프레드 · 베이시스와 bp 환산은 이 사이트의 뺄셈."));
  }
  function report(r, now) {
    const [house, title] = NAMES[r.src];
    const age = ageDays(r.posted, now);
    const head = el("p", { class: "muted" }, (r.src === "kis" ? r.date + " 기준 · " : "") + r.posted + " 게시 · ", link(r));
    const body = r.summary !== null
      ? el("div", { class: "fi-summary" }, el("p", { class: "fi-ai-line" }, el("span", { class: "fi-ai-tag" }, AI_TAG)),
          ...r.summary.map(x => el("p", { class: "fi-topic" }, el("strong", {}, x.topic), x.text)),
          r.summary_dropped > 0 ? el("p", { class: "ch-note muted" }, "검사에 걸린 주제 " + r.summary_dropped + "개는 싣지 않았습니다.") : null)
      : el("p", { class: "fi-summary muted" }, "요약 없음 — " + (NOTES[r.summary_note] || "까닭을 알 수 없음") + ". 원문을 확인하세요.");
    const out = el("article", { class: "panel fi-report" }, el("h3", {}, house + " · " + title + " 제" + r.issue + "호"), head, body);
    if (Number.isFinite(age) && age > STALE_DAYS) out.append(el("p", { class: "market-warning" }, "최근 호가 아닐 수 있습니다(게시 " + age + "일 전)"));
    if (r.src === "kis") out.append(numbers(r));
    else out.append(el("p", { class: "ch-note muted" }, "한국자산평가는 숫자 표를 싣지 않습니다(요약 문장 속 숫자만)."));
    return out;
  }
  function render(doc, now = Date.now()) {
    const slot = document.getElementById("fiweekly-body");
    if (!slot || !isObj(doc) || doc.schema !== "fi-weekly/1" || !Array.isArray(doc.reports)) return false;
    const seen = new Set();
    const good = doc.reports.filter(r => usable(r) && !seen.has(r.src) && seen.add(r.src));
    good.sort((a, b) => SOURCES.indexOf(a.src) - SOURCES.indexOf(b.src));
    if (!good.length) { slot.replaceChildren(); return false; }
    slot.replaceChildren(el("p", { class: "reference-label fi-label" }, LABEL), ...good.map(r => report(r, now)),
      el("div", { class: "notices" }, ...ABOUT.map(t => el("p", {}, t))),
      el("p", { class: "source-link" }, "자료: KIS자산평가 KIS WEEKLY(bond.co.kr) · 한국자산평가 Fixed Income Weekly(koreaap.com) — 각 사 공개 게시물"));
    return true;
  }
  return { render, SOURCES, ROWS, TOPICS, NOTES, NUM_NOTES, LABEL, AI_TAG, KAP_BOARD, STALE_DAYS };
})();
