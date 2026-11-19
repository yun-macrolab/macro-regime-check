/* 판단 연표 — data/timeline.json(scripts/timeline_build.py)을 그린다 (2026-11-19 운영자 결정 '5번도 공개').
   운영자가 공개 기록 저장소(yun-macrolab/macro-notes-automation의 records/)에 올린 주간 판정(듀레이션 · 커브)을 옮겨, 주마다 처음
   확정한 판정 옆에 그 뒤 미 국채 금리의 변화를 판단 연표 약속(자료 파일 protocol — 결과를 보기 전에 정한 방법)대로 두고, 맥락으로
   (a) 그 주 끝의 이 사이트 날짜별 기록(핵심 신호 · 국면 후보 — 그날 실린 그대로)과 (b) 판단 격자 L × P(오늘의 자료로 다시 계산한
   값 — 그때 실린 값이 아니고 개정되면 바뀐다)를 함께 적는다. 표의 열은 판정 바로 뒤에 그 판정의 금리 변화가 오게 둔다(넓은 화면에서
   한눈에, 좁은 화면에서 옆으로 덜 밀게). 고친 칸은 확정 시각 칸에, 운영자 국면 FLAG는 사이트의 국면 후보 곁에 둔다.
   자리: '기록 장부' 화면(#ledger)의 #timeline-wrap — 기록 장부(#ledger-wrap · #ledger-empty) 바로 뒤. 파일이 없거나 꼴이 어긋나면
   false(index.html이 절을 숨긴 채 둔다). 기록 장부와 따로 그린다 — 한쪽이 깨져도 다른 쪽은 그대로.
   측정 기록이다 — 판정의 좋고 나쁨을 가리지 않는다. 판정 이름표(O/W · U/W · 강한 … · Neutral · Flattening · Steepening · 채점 미완 n/7)는
   운영자의 기록이라 늘 LABEL 아래에 두고, 이 화면이 쓰는 방향 글은 그 이름표의 풀이('읽는 법')뿐이다. 확정한 판정은 대개 자동화가 쓴
   초안을 사람이 고치지 않은 것이라 '고친 칸'(edited_n)을 늘 보인다(초안 점수 자체는 어디에도 싣지 않는다).
   판단 격자 칸 이름은 lp.js의 운영자 표(window.LpCard.CELLS)와 글자까지 같을 때만 싣고, 그 이름 곁에 lp.js와 같은 이름표(LP_LABEL)를
   한 번 둔다. lp.js가 없으면 칸 이름 없이 L × P만.
   index.html의 el() · link()를 쓴다(부를 때 이미 정의돼 있다). 글자는 전부 el()의 텍스트로만 넣는다. 바깥 요청은 없다 — 공개 기록
   사이트(github.io)는 link()의 허용 목록 밖이라 주소를 글자로만 적고, 커밋과 저장소는 github.com 링크로 잇는다.
   자료는 꼴을 하나하나 본다(schema 1 · 정해 둔 판정 글 · 월요일 날짜 · ISO 시각 · 커밋 sha · 유한한 숫자): 꼴이 어긋난 주는 건너뛰고,
   파일 꼴(schema · 약속 · 주 목록)이 어긋나면 아무것도 그리지 않는다. 자료 글에 예측 · 권유 · 채점 낱말이 있으면 그 글은 싣지 않는다.
   화면의 내 글은 합니다체, 자료 파일의 약속 문장(protocol.text)은 자료 그대로(한다체) 접은 칸에 싣는다. 자료 파일의 notice(한다체)는
   LABEL과 겹쳐 싣지 않는다. */
"use strict";
window.TimelineView = (() => {
  const TITLE = "판단 연표";
  const CHIP = "측정 기록 — 예측 아님";                // 머리의 칩은 약속 판과 함께('판단 연표 약속 1판 · ' + CHIP)
  const LABEL = "운영자 주간 판정(공개 기록에서 옮김) — 투자 판단·권유 아님 · 측정 기록";
  const LP_LABEL = "운영자 판단 격자의 칸 이름(운영자 메모) — 예측 아님 · 예측력 검증 안 됨";   // lp.js의 LABEL과 같다(테스트가 견준다)
  const BLOCK = { dur: "듀레이션", cur: "커브" };
  // 운영자 시트 v2의 판정 글(sheet_v2.verdict) — 그 밖의 글은 받지 않는다
  const VERDICTS = { dur: ["O/W", "U/W", "강한 O/W", "강한 U/W", "Neutral"],
    cur: ["Flattening", "Steepening", "강한 Flattening", "강한 Steepening", "Neutral"] };
  const UNSCORED = /^채점 미완 [0-6]\/7$/;             // 7행 가운데 0~6행만 채점한 주
  // 요약의 판정 묶음 — 자료 파일 summary의 키
  const GROUPS = {
    dur: [["ow", "O/W 쪽", "O/W · 강한 O/W"], ["neutral", "Neutral", null], ["uw", "U/W 쪽", "U/W · 강한 U/W"]],
    cur: [["flat", "Flattening 쪽", "Flattening · 강한 Flattening"], ["neutral", "Neutral", null],
      ["steep", "Steepening 쪽", "Steepening · 강한 Steepening"]]
  };
  const REGIME = ["A", "A′", "B", "C"];                          // 운영자 국면 FLAG(시트 C19)
  const L_OK = ["L+", "L0", "L−", "L−−", "?"], P_OK = ["P+", "P0", "Pd", "P−", "?"];
  const STATES = ["done", "pending", "missing"];
  const NONE = "기록 없음";
  // 자료 파일의 글에 있으면 그 글을 싣지 않는 낱말(예측 · 권유 · 채점)
  const BANNED_WORDS = ["매수", "매도", "유망", "적중", "맞았다", "틀렸다", "전망", "예상", "추천", "성적"];
  // 권장 인용의 꼴 — ledger.js · tp.js와 같다('…, retrieved from …, November 19, 2026.'). 꼴이 다르면 싣지 않는다
  const CITE = /^[^<>]{1,300}, retrieved from [^<>]{1,300}, [A-Z][a-z]+ \d{1,2}, \d{4}\.$/;
  const DAY = /^\d{4}-\d{2}-\d{2}$/;
  const MONTH = /^\d{4}-(0[1-9]|1[0-2])$/;
  const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})$/;
  const SHA = /^[0-9a-f]{7,40}$/;
  const SERIES = /^[A-Z0-9]{1,30}$/;
  const KEY = /^[a-z0-9_]{1,40}$/;
  const RATIO = /^\d{1,3}\/\d{1,3}$/;
  const HHMM = /^([01]\d|2[0-3]):[0-5]\d$/;
  const KST_HOURS = 9;                                   // 한국 시각(서머타임 없음)
  const REPO = /^[A-Za-z0-9-]{1,39}\/[A-Za-z0-9._-]{1,100}$/;
  const PATH = /^[a-z0-9_-]{1,40}\/$/;
  const SITE = /^https:\/\/[a-z0-9-]{1,39}\.github\.io\/[A-Za-z0-9._\/-]{0,100}$/;
  const PLAIN = /^[^\u0000-\u001f\u007f<>]+$/;            // 제어 문자 · 꺾쇠 없는 한 줄 글

  const isObj = v => v !== null && typeof v === "object" && !Array.isArray(v);
  const own = (o, k) => isObj(o) && Object.prototype.hasOwnProperty.call(o, k);
  // 날짜 — 꼴이 맞고 달력에 있는 날(2026-02-30처럼 넘어가는 날은 아님)
  const day = v => typeof v === "string" && DAY.test(v) && Number.isFinite(Date.parse(v + "T00:00:00Z")) &&
    new Date(v + "T00:00:00Z").toISOString().slice(0, 10) === v;
  const monday = v => day(v) && new Date(v + "T00:00:00Z").getUTCDay() === 1;
  const iso = v => typeof v === "string" && ISO.test(v) && day(v.slice(0, 10)) && Number.isFinite(Date.parse(v));
  const num = v => typeof v === "number" && Number.isFinite(v);
  const count = v => Number.isInteger(v) && v >= 0;
  const clean = t => !BANNED_WORDS.some(w => t.includes(w));
  const str = (v, max) => typeof v === "string" && v.length > 0 && v.length <= (max || 200) && PLAIN.test(v) && clean(v) ? v : null;
  const texts = v => (Array.isArray(v) ? v : []).map(x => str(x, 600)).filter(Boolean);
  // 약속 문장 — 꺾쇠는 받는다(빌더의 문장이 'records/<그 주 월요일>.json'처럼 쓴다. 글자로만 넣으므로 태그가 되지 않는다). 제어 문자 · 금지 낱말은 뺀다
  const LINE = /^[^\u0000-\u001f\u007f]+$/;
  const sentences = v => (Array.isArray(v) ? v : []).filter(x => typeof x === "string" && x.length > 0 && x.length <= 800 && LINE.test(x) && clean(x));
  const plusDays = (d, n) => new Date(Date.parse(d + "T00:00:00Z") + n * 86400000).toISOString().slice(0, 10);
  // 한국 시각(UTC+9, 서머타임 없음) 'YYYY-MM-DD HH:MM'
  const kst = v => { const t = new Date(Date.parse(v) + 9 * 36e5).toISOString(); return `${t.slice(0, 10)} ${t.slice(11, 16)}`; };
  // bp — 부호를 붙인 소수 첫째 자리(0으로 반올림되면 부호 없이 0.0)
  const bp = v => {
    const s = Math.abs(v).toFixed(1);
    return (Number(s) === 0 ? "0.0" : (v < 0 ? "-" : "+") + s) + "bp";
  };
  // Total — 운영자 시트처럼 소수 둘째 자리, 부호를 붙인다(0으로 반올림되면 부호 없이 0.00)
  const signed2 = v => {
    const s = Math.abs(v).toFixed(2);
    return Number(s) === 0 ? "0.00" : (v < 0 ? "-" : "+") + s;
  };
  const shown = v => v.verdict + (v.total === null ? "" : ` (${signed2(v.total)})`);
  const pill = text => el("span", { class: "ledger-pre" }, text);
  // 주(월~일) — 두 토막이 각자 한 줄을 지키게(좁은 화면에서 '11-' · '08'처럼 날짜 가운데서 접히지 않게)
  const weekSpan = (from, to) => [el("span", { class: "tl-week" }, from), el("span", { class: "tl-week" }, " ~ " + to)];
  // 칸 밑 작은 글은 접히되 날짜 · 숫자 토막은 한 줄을 지키게('2026-11-' · '13'처럼 가운데서 접히지 않게)
  const nb = t => el("span", { class: "tl-nb" }, t);

  // ── 자료 읽기 ───────────────────────────────────────────────────────────────────────
  function protocolOf(p) {
    if (!isObj(p) || !Number.isInteger(p.version) || p.version < 1 || !day(p.fixed)) return null;
    const horizons = (Array.isArray(p.horizons_weeks) ? p.horizons_weeks : []).filter(h => Number.isInteger(h) && h > 0 && h <= 52);
    const seen = new Set();
    const pairs = (Array.isArray(p.pairs) ? p.pairs : []).filter(x => isObj(x) && own(BLOCK, x.verdict) && !seen.has(x.verdict) &&
      typeof x.series === "string" && SERIES.test(x.series) && str(x.label, 40) && seen.add(x.verdict));
    if (!horizons.length || !pairs.length || !Number.isInteger(p.n_min) || p.n_min < 1 || !count(p.tolerance_days)) return null;
    // key — 그래프 선 이름(charts.baseline · last의 키). 자료에 line이 없으면 시리즈 이름의 소문자(ledger.json과 같은 꼴)
    return { version: p.version, fixed: p.fixed, horizons, pairs: pairs.map(x => ({ block: x.verdict, series: x.series, label: x.label,
      key: typeof x.line === "string" && KEY.test(x.line) ? x.line : x.series.toLowerCase() })), nMin: p.n_min, tol: p.tolerance_days,
      startDays: Number.isInteger(p.start_days) && p.start_days > 0 && p.start_days <= 31 ? p.start_days : null,
      open: typeof p.open_utc === "string" && HHMM.test(p.open_utc) ? p.open_utc : null, text: sentences(p.text) };
  }
  // '늦게 확정'의 시각 — 화면의 확정 시각이 KST라 한국 시각을 앞에, UTC를 괄호에(같은 날이 아니면 짓지 않고 UTC만)
  function openText(p) {
    if (!p.open) return "정해 둔 시각";
    const h = Number(p.open.slice(0, 2)) + KST_HOURS;
    return h < 24 ? `${String(h).padStart(2, "0")}${p.open.slice(2)} KST(${p.open} UTC)` : `${p.open} UTC`;
  }
  function verdictOf(v, block) {             // {total, verdict} — 판정 글은 정해 둔 것만, Total은 유한한 숫자 또는 null
    if (!isObj(v) || !(v.total === null || num(v.total)) || typeof v.verdict !== "string") return null;
    if (!VERDICTS[block].includes(v.verdict) && !UNSCORED.test(v.verdict)) return null;
    return { total: v.total, verdict: v.verdict };
  }
  function lockOf(l) {
    if (!isObj(l) || typeof l.sha !== "string" || !SHA.test(l.sha) || !iso(l.at) || typeof l.late !== "boolean") return null;
    // first_upload — 처음 올린 판이 곧 확정본, in_history — 잠근 커밋이 지금 공개 기록에 있다(없으면 기록을 고쳐 쓴 것). 없으면 기본값
    return { sha: l.sha, at: l.at, late: l.late, firstUpload: l.first_upload === true, inHistory: l.in_history !== false };
  }
  function commitOf(c) {                     // 지운 커밋 {at, sha} — 꼴이 어긋나면 null
    return isObj(c) && iso(c.at) && typeof c.sha === "string" && SHA.test(c.sha) ? { at: c.at, sha: c.sha } : null;
  }
  function changedOf(c) {                    // 확정 뒤 고침 — 꼴이 어긋나면 그 칸만 뺀다
    if (!isObj(c) || !iso(c.at) || typeof c.sha !== "string" || !SHA.test(c.sha) || !count(c.edited_n)) return null;
    const dur = verdictOf(c.dur, "dur"), cur = verdictOf(c.cur, "cur");
    return dur && cur ? { at: c.at, sha: c.sha, dur, cur, edited: c.edited_n } : null;
  }
  function siteOf(s) {
    if (!isObj(s) || !(s.snapshot === null || day(s.snapshot))) return null;
    const ratio = v => (typeof v === "string" && RATIO.test(v) ? v : null);
    return { snapshot: s.snapshot, core: ratio(s.core), met: ratio(s.met), candidate: str(s.candidate, 12) };
  }
  // 판단 격자 — 칸 이름은 lp.js의 운영자 표와 글자까지 같아야 하고, 모르는 쪽이 있으면 그쪽을 적은 '판정 보류(…)'여야 한다
  function lpOf(x) {
    if (!isObj(x) || typeof x.month !== "string" || !MONTH.test(x.month) || !L_OK.includes(x.L) || !P_OK.includes(x.P) ||
        typeof x.cell !== "string") return null;
    const cells = window.LpCard && isObj(window.LpCard.CELLS) ? window.LpCard.CELLS : null;
    const known = x.L !== "?" && x.P !== "?";
    const hold = `판정 보류(${[x.L === "?" ? "노동" : null, x.P === "?" ? "물가" : null].filter(Boolean).join("·")})`;
    const right = known ? (cells && Array.isArray(cells[x.L + "|" + x.P]) ? cells[x.L + "|" + x.P][0] === x.cell : null) : x.cell === hold;
    if (right === false) return null;
    return { month: x.month, L: x.L, P: x.P, cell: right ? x.cell : null };
  }
  function cellOf(c) {                       // 결과 한 칸 — 꼴이 어긋나면 null('—')
    if (!isObj(c) || !STATES.includes(c.state) || !(c.start === null || c.start === undefined || day(c.start))) return null;
    if (c.state === "done")
      return num(c.change_bp) && num(c.demeaned_bp) && day(c.start) && day(c.end) ? c : null;
    return c;
  }
  function weekOf(w) {
    if (!isObj(w) || !monday(w.week) || w.end !== plusDays(w.week, 6)) return null;
    if (w.state !== "confirmed" && w.state !== "in_progress") return null;
    const dur = verdictOf(w.dur, "dur"), cur = verdictOf(w.cur, "cur");
    if (!dur || !cur || !count(w.edited_n) || typeof w.before_protocol !== "boolean") return null;
    if (!(w.regime_flag === null || w.regime_flag === undefined || REGIME.includes(w.regime_flag))) return null;
    const lock = w.state === "confirmed" ? lockOf(w.lock) : null;
    if (w.state === "confirmed" && !lock) return null;         // 확정한 주는 확정 커밋과 시각이 있어야 한다
    const flag = REGIME.includes(w.regime_flag) ? w.regime_flag : null;
    return { week: w.week, end: w.end, confirmed: w.state === "confirmed", lock, pre: w.before_protocol, dur, cur,
      edited: w.edited_n, flag, flagOther: !flag && w.regime_flag_other === true,
      changed: w.state === "confirmed" ? changedOf(w.changed_after) : null,
      removed: w.state === "confirmed" ? commitOf(w.removed) : null, site: siteOf(w.site), lp: lpOf(w.lp),
      outcomes: isObj(w.outcomes) ? w.outcomes : {} };
  }
  const outcome = (w, h, block) => (own(w.outcomes, String(h)) && isObj(w.outcomes[String(h)])
    ? cellOf(w.outcomes[String(h)][block]) : null);
  function sourceOf(s) {
    if (!isObj(s)) return {};
    return { repo: typeof s.repo === "string" && REPO.test(s.repo) ? s.repo : null,
      path: typeof s.path === "string" && PATH.test(s.path) ? s.path : null,
      site: typeof s.site === "string" && SITE.test(s.site) ? s.site : null,
      newest: typeof s.newest_commit === "string" && SHA.test(s.newest_commit) ? s.newest_commit : null,
      checked: iso(s.checked_at) ? s.checked_at : null, skipped: count(s.skipped_versions) ? s.skipped_versions : 0 };
  }

  // ── 그리기 ─────────────────────────────────────────────────────────────────────────
  // 표 하나 — 설명 줄은 표 밖(좁은 화면에서도 접혀 다 보이게), 표는 가로 스크롤 상자 안. 표의 이름은 그 설명 줄(aria-labelledby)
  let capSeq = 0;
  function block(cap, cls, extra, ...parts) {
    const id = "tl-cap-" + (++capSeq);
    return el("div", { class: "ledger-block" }, el("p", { class: "muted ledger-cap", id }, cap), extra,
      el("div", { class: "ledger-scroll tl-scroll" }, el("table", { class: "ledger-table " + cls, "aria-labelledby": id }, ...parts)));
  }
  const commitLink = (src, sha) => (src.repo ? link(sha.slice(0, 7), `https://github.com/${src.repo}/commit/${sha}`) : sha.slice(0, 7));
  // 기다리는 중 — 끝 점을 찾을 날(출발 + 7 × 주 수일, ±tol일)
  function outcomeCell(w, c, h, tol) {
    // 확정 전인 주는 출발 점이 정해지지 않았다(자료는 start 없는 '기다리는 중')
    if (!w.confirmed && (!c || c.state === "pending")) return el("td", {}, el("span", { class: "ledger-wait" }, "확정 전"));
    if (!c) return el("td", {}, "—");
    if (c.state === "pending") return el("td", {}, el("span", { class: "ledger-wait" }, "기다리는 중"),
      day(c.start) ? el("small", {}, nb(`출발 ${c.start}`), " · ", nb(`끝 점 ${plusDays(c.start, 7 * h)}±${tol}일`)) : null);
    if (c.state === "missing") return el("td", {}, el("span", { class: "ledger-wait" }, "자료 없음"));
    return el("td", {}, el("span", { class: "ledger-num" }, bp(c.change_bp)), el("small", {}, "평균을 뺀 값 ", nb(bp(c.demeaned_bp))),
      el("small", {}, nb(c.start), " → ", nb(c.end)));
  }
  function verdictCell(w, blockKey) {
    const v = w[blockKey], ch = w.changed;
    const moved = ch && (ch[blockKey].verdict !== v.verdict || ch[blockKey].total !== v.total);
    return el("td", {}, el("span", { class: "tl-verdict" }, shown(v)),
      moved ? el("small", { class: "tl-moved" }, "확정 뒤 고침 → " + shown(ch[blockKey])) : null);
  }
  // 확정 시각 · 고친 칸 — 확정 커밋(지금 공개 기록에 없으면 글자로만), 고친 칸 수, 표시(늦게 확정 · 확정 뒤 고침 · 지움 · 기록 고쳐 씀),
  // 같은 출발 점을 나눈 주
  function lockCell(w, src, twins) {
    const edited = el("small", {}, `고친 칸 ${w.edited}`, w.changed && w.changed.edited !== w.edited ? ` · 확정 뒤 ${w.changed.edited}` : "");
    if (!w.confirmed) return el("td", {}, el("span", { class: "ledger-wait" }, "확정 전"), edited);
    const L = w.lock;
    return el("td", {}, kst(L.at), el("small", {}, "KST · 커밋 ", L.inHistory ? commitLink(src, L.sha) : L.sha.slice(0, 7)), edited,
      L.late ? pill("늦게 확정") : null,
      w.changed ? pill("확정 뒤 고침") : null,
      w.removed ? pill("공개 기록에서 지움") : null,
      L.inHistory ? null : pill("기록 고쳐 씀"),
      L.firstUpload ? el("small", {}, "처음 올린 판이 확정본") : null,
      w.changed ? el("small", {}, `고친 커밋 ${kst(w.changed.at)} · `, commitLink(src, w.changed.sha)) : null,
      w.removed ? el("small", {}, `지운 커밋 ${kst(w.removed.at)} · `, commitLink(src, w.removed.sha)) : null,
      L.inHistory ? null : el("small", {}, "잠근 커밋이 지금 공개 기록에 없음 — 처음 판정 그대로"),
      twins ? el("small", { class: "tl-twin" }, "출발 점 ", nb(twins.start), " — ", twins.others.map(x => x.slice(5)).join(" · "),
        " 주와 같음") : null);
  }
  // 사이트의 날짜별 기록(그날 실린 그대로)과, 그 곁에 운영자 국면 FLAG
  function siteCell(s, w) {
    const flag = el("small", { class: "tl-flag" }, "운영자 FLAG ",
      w.flag || el("span", { class: "ledger-wait" }, w.flagOther ? "정해 둔 값 밖" : "비어 있음"));
    if (!s || s.snapshot === null) return el("td", {}, el("span", { class: "ledger-wait" }, NONE), flag);
    // 핵심 신호(레짐 점검 절이 있는 기록) — 없던 날은 충족 규칙 수(전체 규칙 가운데). 둘은 견줄 수 없다('읽는 법')
    const head = s.core ? `핵심 신호 ${s.core}` : s.met ? `충족 규칙 ${s.met}` : null;
    // 국면 후보: A · A′ · B · C, 그날 레짐 점검 절은 있는데 후보가 없으면 '판정불가', 절이 없던 날은 '—'
    return el("td", {}, head || "—", el("small", { class: "tl-cand" }, `국면 후보 ${s.candidate || "—"}`), flag,
      el("small", {}, "기록 ", nb(s.snapshot)));
  }
  function lpCell(x) {
    if (!x) return el("td", {}, "—");
    return el("td", {}, `${x.L} × ${x.P}`, x.cell ? el("small", { class: "tl-cell" }, x.cell) : null, el("small", {}, "기준월 ", nb(x.month)));
  }
  // 두 주 사이의 빈 주(월요일) — 말없이 건너뛰지 않는다. 이어진 빈 주는 한 줄로
  function gapRow(newer, older, cols) {
    const from = plusDays(older, 7), to = plusDays(newer, -1);
    if (from >= newer) return null;
    const n = Math.round((Date.parse(newer + "T00:00:00Z") - Date.parse(from + "T00:00:00Z")) / (7 * 86400000));
    return el("tr", { class: "tl-gap" }, el("th", { scope: "row" }, ...weekSpan(from, to.slice(5)), n > 1 ? el("small", {}, `${n}주`) : null),
      el("td", { colspan: String(cols - 1) }, "공개 기록이 없는 주입니다."));
  }
  // 확정한 주의 출발 점(첫 짝 · 첫 기간의 칸에서) — 같은 날을 나눈 주끼리 결과가 같다
  function startOf(w, p) {
    if (!w.confirmed) return null;
    for (const x of p.pairs) for (const h of p.horizons) { const c = outcome(w, h, x.block); if (c && day(c.start)) return c.start; }
    return null;
  }
  function weekTable(weeks, p, src, lpNamed) {
    const head = ["주(월~일)", "확정 시각 · 고친 칸",
      ...p.pairs.flatMap(x => [`${BLOCK[x.block]} 판정(Total)`, ...p.horizons.map(h => `${h}주 뒤 ${x.label}`)]),
      "사이트 규칙 · 국면 후보 · 운영자 FLAG", "L×P(칸) — 오늘 다시 계산"];
    const byStart = {};
    for (const w of weeks) { const s = startOf(w, p); if (s) (byStart[s] = byStart[s] || []).push(w.week); }
    const rows = [];
    weeks.forEach((w, i) => {
      if (i) { const g = gapRow(weeks[i - 1].week, w.week, head.length); if (g) rows.push(g); }
      const s = startOf(w, p), same = s ? byStart[s].filter(x => x !== w.week) : [];
      rows.push(el("tr", { class: w.confirmed ? "tl-row" : "tl-row tl-open" },
        el("th", { scope: "row" }, ...weekSpan(w.week, w.end.slice(5)), !w.confirmed ? pill("진행 중") : w.pre ? pill("약속 전") : null),
        lockCell(w, src, same.length ? { start: s, others: same } : null),
        ...p.pairs.flatMap(x => [verdictCell(w, x.block), ...p.horizons.map(h => outcomeCell(w, outcome(w, h, x.block), h, p.tol))]),
        siteCell(w.site, w), lpCell(w.lp)));
    });
    return block("주마다 — 운영자가 처음 확정한 판정과 그 뒤 금리 변화(주간 점, bp), 맥락으로 그 주 끝의 이 사이트 날짜별 기록(그날 실린 그대로)과 " +
      "판단 격자 L × P(오늘의 자료로 다시 계산한 값 — 그때 실린 값이 아님). 새 주가 위입니다.",
      "tl-table", lpNamed ? el("p", { class: "muted tl-lplabel" }, "'L×P(칸)' 열의 칸 이름: " + LP_LABEL) : null,
      el("thead", {}, el("tr", {}, ...head.map(t => el("th", { scope: "col" }, t)))),
      el("tbody", {}, ...(rows.length ? rows : [el("tr", {}, el("td", { colspan: String(head.length) }, "옮겨 온 주간 기록이 없습니다."))])));
  }
  // 요약 한 칸 — 같은 출발 점을 나눈 주는 한 번(starts). 자료에 starts가 없으면 주 수로
  function summaryCell(s, nMin) {
    if (!isObj(s) || !count(s.n)) return el("td", {}, "—");
    const k = count(s.starts) && s.starts <= s.n ? s.starts : s.n;
    const weeksNote = k !== s.n ? ` · 주 ${s.n}` : "";
    if (k < nMin) return el("td", {}, el("span", { class: "ledger-wait" }, `판단 보류 (${k}/${nMin})`),
      weeksNote ? el("small", {}, `출발 점 ${k}개` + weeksNote) : null);
    if (!num(s.mean_demeaned_bp) || !num(s.up_share) || s.up_share < 0 || s.up_share > 1) return el("td", {}, "—");
    return el("td", {}, el("span", { class: "ledger-num" }, "평균을 뺀 값 " + bp(s.mean_demeaned_bp)),
      el("small", {}, `오른 비율 ${Math.round(s.up_share * 100)}% · 출발 점 ${k}개` + weeksNote));
  }
  function summaryTable(d, p) {
    const sum = isObj(d.summary) ? d.summary : {};
    const rows = p.pairs.flatMap(x => GROUPS[x.block].map(([key, name, members]) => {
      const g = isObj(sum[x.block]) && isObj(sum[x.block][key]) ? sum[x.block][key] : {};
      return el("tr", {}, el("th", { scope: "row" }, `${BLOCK[x.block]} ${name}`, members ? el("small", {}, members) : null),
        el("td", {}, x.label), ...p.horizons.map(h => summaryCell(g[String(h)], p.nMin)));
    }));
    return block(`판정 묶음별 요약 — 약속 ${p.version}판(${p.fixed}) 뒤에 확정한 주만, 같은 출발 점을 나눈 주는 한 번으로 세어 출발 점이 ` +
      `${p.nMin}개 모이기 전에는 판단 보류`,
      "tl-sum", null,
      el("thead", {}, el("tr", {}, ...["판정 묶음", "금리", ...p.horizons.map(h => `${h}주 뒤(평균을 뺀 값)`)].map(t => el("th", { scope: "col" }, t)))),
      el("tbody", {}, ...rows));
  }
  function summaryLine(weeks) {
    const done = weeks.filter(w => w.confirmed), open = weeks.filter(w => !w.confirmed);
    if (!weeks.length) return el("p", { class: "tl-sum-line" }, "아직 옮겨 온 주간 기록이 없습니다.");
    const latest = weeks[0];
    const n = f => done.filter(f).length;
    const pre = n(w => w.pre), late = n(w => w.lock.late), moved = n(w => w.changed), gone = n(w => w.removed),
      rewritten = n(w => !w.lock.inHistory);
    const parts = [`공개 기록 ${weeks.length}주 가운데 ${done.length}주를 확정했고` +
      (open.length > 1 ? `(확정 전 ${open.length}주)` : "") +
      `, 가장 최근 ${latest.week} 주는 ${latest.confirmed ? "확정했습니다" : "진행 중입니다(확정 전)"}.`];
    const zero = n(w => w.edited === 0);
    const notes = [done.length ? (zero === done.length ? `확정한 ${done.length}주 모두 고친 칸이 0입니다 — 운영자 시트가 사람이 고친 점수 칸을 ` +
      "잡지 못했다는 뜻이고, 그 주 마지막 자동 실행 뒤(주말 등)에 고친 점수는 세지 못하므로 초안 그대로라는 보장은 아닙니다"
      : `확정한 ${done.length}주 가운데 고친 칸이 0인 주는 ${zero}주입니다`) : null,
      pre ? `약속 전 ${pre}주` : null, late ? `늦게 확정 ${late}주` : null, moved ? `확정 뒤 고침 ${moved}주` : null,
      gone ? `공개 기록에서 지움 ${gone}주` : null, rewritten ? `기록 고쳐 씀 ${rewritten}주` : null].filter(Boolean);
    return el("div", {}, el("p", { class: "tl-sum-line" }, parts[0]),
      notes.length ? el("p", { class: "muted tl-sum-note" }, notes.join(" · ") + ".") : null);
  }
  // 평균(기준) — 기간마다 시리즈의 평균과(있으면) 잰 쌍의 범위
  function baseText(p, charts) {
    const base = isObj(charts.baseline) ? charts.baseline : {}, det = isObj(charts.baseline_detail) ? charts.baseline_detail : {};
    const head = p.horizons.map(h => {
      const b = isObj(base[String(h)]) ? base[String(h)] : {};
      return `${h}주 — ` + p.pairs.map(x => `${x.label} ${num(b[x.key]) ? bp(b[x.key]) : "—"}`).join(" · ");
    }).join(" / ");
    const spans = p.horizons.flatMap(h => p.pairs.map(x => {
      const s = isObj(det[String(h)]) ? det[String(h)][x.key] : null;
      return isObj(s) && count(s.n) && s.n > 0 && day(s.from) && day(s.to) ? s : null;
    })).filter(Boolean);
    if (!spans.length) return head;
    const from = spans.map(s => s.from).sort()[0], to = spans.map(s => s.to).sort().slice(-1)[0];
    const ns = spans.map(s => s.n), lo = Math.min(...ns), hi = Math.max(...ns);
    return `${head}(첫 출발 ${from} ~ 마지막 끝 ${to}, 쌍 ${lo === hi ? lo : lo + "~" + hi}개 — 시리즈·기간마다 다름)`;
  }
  function basisLine(p, charts) {
    if (!day(charts.date)) return el("p", { class: "muted ledger-basis" }, "그래프 자료가 없어 결과를 적지 못했습니다.");
    const last = isObj(charts.last) ? p.pairs.filter(x => day(charts.last[x.key])).map(x => `${x.label} ${charts.last[x.key]}`) : [];
    return el("p", { class: "muted ledger-basis" },
      `결과와 평균(기준)은 ${charts.date}의 그래프 자료(charts.json 주간 점)로 갱신마다 다시 잽니다. 평균(기준, 계산값): ${baseText(p, charts)}.` +
      (last.length ? ` 그래프의 마지막 점: ${last.join(" · ")} — 끝 점을 찾을 날의 ±${p.tol}일이 이 날을 넘으면 기다리는 중입니다.` : ""));
  }
  // 늘 보이는 약속의 요지(기록 장부의 약속 상자처럼) — 판 · 기간과 출발 점 · 짝 · 요약 문턱. 문장 전체는 아래 접은 칸
  function keyList(p) {
    const within = p.startDays ? ` ${p.startDays}일 안` : "";
    const pairParts = p.pairs.flatMap((x, i) => [i ? " · " : "", `${BLOCK[x.block]} 판정 ↔ ${x.label} `,
      link(x.series, "https://fred.stlouisfed.org/series/" + x.series)]).filter(t => t !== "");
    return el("ul", { class: "chg-list tl-keys" },
      el("li", {}, el("strong", {}, `판단 연표 약속 ${p.version}판`), ` · ${p.fixed} 고정 — 결과를 보기 전에 정한 방법입니다(약속 문장은 아래 접은 칸).`),
      el("li", {}, `보는 기간: ${p.horizons.map(h => h + "주").join(" · ")} 뒤 — 출발 점은 그 주 안의 마지막 주간 점(보통 금요일 값)이고, ` +
        `확정이 다음 월요일 ${openText(p)}보다 늦은 주는 확정한 날(UTC) 이후${within}의 첫 주간 점입니다.`),
      el("li", {}, "짝: ", ...pairParts, " (FRED, 주간 점의 bp 변화)."),
      el("li", {}, `요약: 약속 뒤에 확정한 주를 같은 출발 점은 한 번으로 세어 ${p.nMin}개가 모였을 때만 냅니다 — 그 전에는 '판단 보류 (n/${p.nMin})'.`));
  }
  function readingBox(p) {
    const open = openText(p);
    const within = p.startDays ? ` ${p.startDays}일 안` : "";
    const items = [
      el("li", {}, el("strong", {}, "판정 이름표"), " — 운영자 시트의 이름표를 그대로 옮겼습니다. 이 사이트가 내린 판정이 아니고 투자 판단·권유가 아닙니다. " +
        "O/W(강한 O/W)는 듀레이션 비중 확대 쪽(금리 하락 쪽에 선 판정), U/W(강한 U/W)는 그 반대인 비중 축소 쪽(금리 상승 쪽에 선 판정)입니다. " +
        "Flattening은 커브 평탄화 쪽(10년−2년 금리차가 줄어드는 쪽에 선 판정), Steepening은 가팔라지는 쪽(차가 커지는 쪽)입니다. " +
        "Neutral은 어느 쪽에도 서지 않은 주, '채점 미완 n/7'은 7행 가운데 n행만 점수가 있어 판정하지 않은 주입니다."),
      el("li", {}, el("strong", {}, "Total"), " — 운영자 시트의 가중 점수 합입니다(듀레이션은 + 쪽이 금리 하락, 커브는 + 쪽이 평탄화). " +
        "운영자 시트의 규칙으로 ±0.5 이상이면 O/W · U/W(Flattening · Steepening), ±1.0 이상이면 '강한'이 붙고, 이벤트 FLAG가 켜진 주는 ±0.75가 문턱입니다. " +
        "국면 A′이고 근원 CPI가 3% 아래인 주는 U/W 쪽을 한 단계 누그러뜨립니다."),
      el("li", {}, el("strong", {}, "고친 칸"), " — 운영자 시트가 '사람이 고친 칸'으로 잠근 점수 칸(7행 × 듀레이션 · 커브)의 수입니다. " +
        "시트는 자동 실행이 돌 때만 초안과 다른 값을 알아채고 잠그므로, 그 주 마지막 자동 실행 뒤(주말 등)에 고친 점수는 세지 못합니다. " +
        "그래서 0은 시트가 사람이 고친 칸을 잡지 못했다는 뜻이지, 확정한 판정이 초안 그대로라는 보장은 아닙니다. 초안 점수 자체는 공개 기록에도 이 사이트에도 싣지 않습니다."),
      el("li", {}, el("strong", {}, "확정 시각"), " — 그 주 기록이 공개 기록 저장소에 처음 '확정'으로 올라간 커밋에 적힌 시각(커미터 시각, 한국 시각으로 보입니다)입니다. " +
        "운영자의 게시기는 커밋을 GitHub API로 날짜 없이 만들어 GitHub이 그때의 시각을 적습니다(PC에서 git으로 만든 커밋이면 그 PC의 시계). " +
        "검증한 시각이 아니라 적힌 시각입니다. '처음 올린 판이 확정본'은 그 주의 확정 전 판이 공개 기록에 올라온 적 없이 처음부터 확정본으로 올라온 주로, " +
        "확정 시각이 곧 첫 업로드 시각이라 실제 확정은 그 앞일 수 있습니다. 연표의 판정과 계산은 모두 이 첫 확정본으로 합니다."),
      el("li", {}, el("strong", {}, "늦게 확정"), ` — 확정 시각이 그 주 다음 월요일 ${open}보다 늦은 주입니다(뉴욕 주식 현물 시장이 가장 일찍 여는 시각). ` +
        `이런 주는 그 주 끝 값이 아니라 확정한 날(UTC) 이후${within}의 첫 주간 점에서 잽니다 — 확정이 늦어 이미 보인 움직임을 결과에 넣지 않으려는 것입니다. ` +
        "다만 미 국채는 그 시각보다 앞서 아시아·런던 시간에도 거래되므로, 그 앞에 확정한 주도 월요일 앞부분의 움직임이 확정 전에 보였을 수 있고 그 움직임은 1주 변화 안에 듭니다."),
      el("li", {}, el("strong", {}, "같은 출발 점"), " — 늦게 확정한 주의 출발 점은 뒤 주의 출발 점과 겹칠 수 있습니다. 출발 날짜가 같은 줄은 결과가 같고 서로 독립이 아닙니다 " +
        "(확정 시각 칸에 같은 출발 점의 주를 적습니다). 요약은 같은 출발 점을 한 번만 셉니다."),
      el("li", {}, el("strong", {}, "확정 뒤 고침 · 지움"), " — 처음 확정한 뒤에 그 주의 판정이나 Total을 바꾼 커밋이 있으면 바뀐 값을 함께 적습니다. " +
        "그 주 파일을 공개 기록에서 지웠거나 이름을 바꿨으면 '공개 기록에서 지움', 공개 기록 저장소의 기록을 고쳐 써 처음 확정한 커밋이 지금 기록에 없으면 '기록 고쳐 씀'을 붙입니다. " +
        "어느 경우에도 처음 확정한 판정과 시각을 그대로 두고, 결과와 요약은 그것으로 셉니다."),
      el("li", {}, el("strong", {}, "약속 전"), ` — 판단 연표 약속(${p.fixed}) 앞에 확정한 주입니다. 약속을 정할 때 그 뒤의 금리 움직임이 이미 보였으므로 ` +
        "목록에만 적고 요약에서 뺍니다. 채점 미완인 주와 확정 전인 주도 요약에 넣지 않습니다."),
      el("li", {}, el("strong", {}, "결과"), ` — 출발 점에서 ${p.horizons.join("주 · ")}주 뒤 주간 점까지의 변화(bp)와, ` +
        `같은 그래프의 모든 같은 기간 변화의 평균을 뺀 값입니다. 끝 점은 주 수×7일 뒤 날짜의 ±${p.tol}일 안에서 가장 가까운 주간 점입니다. ` +
        "'기다리는 중'은 그 날짜가 아직 오지 않은 것, '자료 없음'은 범위 안에 주간 점이 없는 것입니다."),
      el("li", {}, el("strong", {}, "사이트 · 국면"), " — 그 주 일요일까지의 마지막 날짜별 기록(data/history — 그날 이 사이트에 실린 그대로)에 적힌 핵심 신호와 국면 후보입니다. " +
        "레짐 점검 절이 날짜별 기록에 생기기 전의 주는 핵심 신호 대신 '충족 규칙 m/전체 규칙 수'를 적고 국면 후보는 —입니다 — 두 숫자는 서로 견줄 수 없고, " +
        "전체 규칙 수는 규칙을 더한 날부터 늘었습니다. 운영자 FLAG는 그 주 시트에 운영자가 적은 국면입니다 — '비어 있음'은 그 칸이 비어 있던 주, " +
        "'정해 둔 값 밖'은 A · A′ · B · C가 아닌 글이 있던 주입니다(그 글은 옮기지 않습니다)."),
      el("li", {}, el("strong", {}, "L×P"), " — 그 주 일요일까지 나왔을 마지막 기준월(발표일은 근사)의 판단 격자를 오늘의 FRED 자료로 다시 계산한 값입니다. " +
        "그때 이 사이트에 실린 값을 옮긴 것이 아니고(판단 격자 카드는 2026-11-18부터 실렸습니다), FRED가 지난 값을 고치면 바뀝니다. 칸 이름은 운영자 메모이고 예측이 아닙니다."),
      el("li", {}, el("strong", {}, "FRED 개정"), " — 결과와 평균은 갱신마다 그날 그래프 자료로 다시 잽니다. FRED가 값을 고치거나 그래프 창이 옮겨 가면 " +
        "조금씩 달라지고, 출발 점이 창 밖으로 나간 주는 '자료 없음'이 됩니다.")];
    return el("details", { class: "rule-detail tl-read" }, el("summary", {}, "읽는 법"), el("ul", { class: "chg-list" }, ...items));
  }
  // 계산값 고지와 FRED 권장 인용 — 꼴이 맞는 것만, 시리즈마다 하나
  function citeBox(d, p) {
    const notes = texts(d.notices);
    const seen = new Set(), cites = [];
    for (const s of Array.isArray(d.sources) ? d.sources : []) {
      if (!isObj(s) || typeof s.series !== "string" || !SERIES.test(s.series) || seen.has(s.series)) continue;
      if (!p.pairs.some(x => x.series === s.series) || typeof s.citation !== "string" || !CITE.test(s.citation)) continue;
      seen.add(s.series);
      cites.push(s.citation);
    }
    if (!notes.length && !cites.length) return null;
    return el("div", { class: "notices ledger-cite" }, ...notes.map(t => el("p", {}, t)),
      cites.length ? el("p", {}, "권장 인용: " + cites.join(" ")) : null);
  }
  function sourceLine(src) {
    if (!src.repo) return null;
    const where = src.path ? `${src.repo}의 ${src.path}` : src.repo;
    return el("p", { class: "muted tl-source" }, "옮겨 온 곳: 공개 기록 저장소 ",
      link(where, `https://github.com/${src.repo}` + (src.path ? `/tree/HEAD/${src.path.slice(0, -1)}` : "")),
      src.site ? ` · 공개 기록 사이트 ${src.site}` : "",
      src.checked ? ` · 확인 ${kst(src.checked)} (KST)` : "",
      src.newest ? el("span", {}, " · 마지막으로 읽은 커밋 ", link(src.newest.slice(0, 7), `https://github.com/${src.repo}/commit/${src.newest}`)) : null,
      src.skipped ? ` · 꼴이 어긋나 쓰지 않은 판 ${src.skipped}개` : "");
  }

  function render(d) {
    try {
      const wrap = document.getElementById("timeline-wrap");
      if (!wrap || !isObj(d) || d.schema !== 1 || !Array.isArray(d.weeks)) return false;
      const p = protocolOf(d.protocol);
      if (!p) return false;
      const seen = new Set();
      const weeks = d.weeks.map(weekOf).filter(w => w && !seen.has(w.week) && seen.add(w.week))
        .sort((a, b) => (a.week < b.week ? 1 : a.week > b.week ? -1 : 0));
      const src = sourceOf(d.source), charts = isObj(d.charts) ? d.charts : {};
      const lpNamed = weeks.some(w => w.lp && w.lp.cell);
      wrap.replaceChildren(
        el("div", { class: "section-heading" }, el("h2", { id: "timeline-title" }, TITLE),
          el("span", { class: "reference-label" }, `판단 연표 약속 ${p.version}판 · ${CHIP}`)),
        el("div", { class: "panel tl" },
          el("p", { class: "tl-label" }, LABEL),
          summaryLine(weeks),
          keyList(p),
          weekTable(weeks, p, src, lpNamed),
          summaryTable(d, p),
          basisLine(p, charts),
          p.text.length ? el("details", { class: "rule-detail ledger-text" },
            el("summary", {}, `약속 문장 ${p.text.length}개 — 판단 연표 약속 ${p.version}판 · ${p.fixed} 고정(자료 파일 그대로)`),
            el("div", { class: "notices" }, ...p.text.map(t => el("p", {}, t)))) : null,
          readingBox(p),
          citeBox(d, p),
          sourceLine(src)));
      return true;
    } catch (e) {
      return false;
    }
  }

  return Object.freeze({ render, TITLE, CHIP, LABEL, LP_LABEL, VERDICTS, GROUPS });
})();
