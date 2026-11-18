/* 기록 장부 — data/changes.json · data/ledger.json(scripts/ledger_build.py)을 그린다 (2026-11-18 운영자 결정).
   두 자리:
     #changes-wrap  첫 화면(전체)의 '이번 주 달라진 것' — 날짜별 공개 기록(data/history)끼리 견준 머리 줄 셋과, 접은 칸 안의
                    세 창(직전 기록 · 1주 전 · 4주 전)의 바뀐 것(규칙 · 충족 수 · 핵심 신호 · 중립 규칙 · 국면 후보 · 전환 경계 · 자료 상태)
                    — 그대로인 칸은 '그대로:' 한 줄, 그때 기록하지 않은 칸은 '그때 기록하지 않은 칸' 한 줄 — 과 최근 30일 규칙 전환.
                    국면 후보의 '판정불가'는 그날 레짐 점검 절은 있는데 후보가 없던 날(완충 구간), null은 그날 절이 없던 날('기록 없음')
     #ledger-wrap   '기록 장부' 화면(#ledger) — 평가 약속(판 · 고정일 · 기간 · 금리 · 기준 평균과 그 쌍의 범위 · 그래프의 마지막 점 ·
                    최소 건수 · 접은 약속 문장 · 계산값 고지와 FRED 권장 인용), 규칙별 표, 규칙마다 접은 전환 목록(그날의 맥락 ·
                    4주/13주 뒤 세 금리의 변화와 평균을 뺀 값 · 방향별 요약). '언제부터'는 전환이 없던 규칙이면 기록 시작 · 규칙 추가 ·
                    첫 판정에서 잘린 날이라 그렇게 적고, 지금 판정 불가면 직전 판정과 그 날을, 가장 최근 기록에 없는 규칙은
                    '지금은 싣지 않는 규칙'으로 적는다
   측정 기록이다 — 예측이 아니고, 어느 규칙도 금리를 올리거나 내린다고 가정하지 않는다. 판정 낱말을 쓰지 않는다.
   index.html의 el() · link()를 쓴다(부를 때 이미 정의돼 있다). 글자는 전부 el()의 텍스트로만 넣는다. 바깥 요청은 없다.
   자료는 꼴을 하나하나 본다(schema 1 · 배열 · 정해 둔 값 · 날짜 꼴 · 유한한 숫자): 꼴이 어긋난 항목은 건너뛰고, 파일 꼴이 어긋나면
   첫 화면에는 아무것도 두지 않고(false) 장부 화면은 index.html의 빈 줄(#ledger-empty — EMPTY와 같은 글)이 대신한다.
   화면의 내 글은 합니다체, 자료 파일의 약속 문장(protocol.text)은 자료 그대로(한다체) 접은 칸에 싣는다. 장부가 무엇인지('예측 아님')는
   화면 머리(#view-description)와 공지 줄(#notice)이 이미 말하므로 따로 되풀이하지 않는다. */
"use strict";
window.LedgerView = (() => {
  const STATUS = { met: "충족", not_met: "미충족", unknown: "판정 불가" };
  const WINDOWS = [["prev", "직전 기록"], ["w1", "1주 전"], ["w4", "4주 전"]];
  const DIRS = [["to_met", "충족으로 바뀐 뒤"], ["to_not_met", "미충족으로 바뀐 뒤"]];
  const STATES = ["done", "pending", "missing"];
  const NONE = "기록 없음";
  const NOTE = "날짜별 공개 기록끼리 견준 것 — 예측이 아닙니다.";
  const EMPTY = "기록 장부를 불러오지 못했습니다. 자료가 갱신된 뒤 다시 확인해 주세요.";
  const CHG_LABEL = "공개 기록 대조 — 예측 아님";
  const LABEL = "측정 기록 — 예측 아님";
  const CAUSE = "전환 뒤의 변화는 그 규칙 때문이라는 뜻이 아닙니다 — 같은 기간의 다른 일이 섞이고, 출발 점이 같은 전환" +
    "(며칠 사이에 두 번 바뀐 규칙)은 같은 결과를 나눠 가져 서로 독립이 아닙니다.";
  const RECENT = "최근 30일 규칙 전환";
  const AUTO = 2;                             // 전환 경계 자동 트리거의 수(t2 · t4) — 레짐 점검 참고의 '0/2'와 같은 꼴
  // 권장 인용의 꼴 — tp.js와 같다('…, retrieved from …, November 17, 2026.'). 꼴이 다르면 싣지 않는다
  const CITE = /^[^<>]{1,300}, retrieved from [^<>]{1,300}, [A-Z][a-z]+ \d{1,2}, \d{4}\.$/;
  const DAY = /^\d{4}-\d{2}-\d{2}$/;
  const KEY = /^[a-z0-9_]{1,40}$/;
  const SERIES = /^[A-Z0-9]{1,30}$/;
  const RATIO = /^\d{1,3}\/\d{1,3}$/;
  const PLAIN = /^[^\u0000-\u001f\u007f<>]+$/;            // 제어 문자 · 꺾쇠 없는 한 줄 글

  const isObj = v => v !== null && typeof v === "object" && !Array.isArray(v);
  const own = (o, k) => isObj(o) && Object.prototype.hasOwnProperty.call(o, k);
  // 날짜 — 꼴이 맞고 달력에 있는 날(2026-02-30처럼 넘어가는 날은 아님)
  const day = v => typeof v === "string" && DAY.test(v) && Number.isFinite(Date.parse(v + "T00:00:00Z")) &&
    new Date(v + "T00:00:00Z").toISOString().slice(0, 10) === v;
  const str = (v, max) => typeof v === "string" && v.length > 0 && v.length <= (max || 200) && PLAIN.test(v) ? v : null;
  const count = v => Number.isInteger(v) && v >= 0;
  const num = v => typeof v === "number" && Number.isFinite(v);
  const status = v => typeof v === "string" && own(STATUS, v);
  const known = v => v === "met" || v === "not_met";
  const word = s => (status(s) ? STATUS[s] : NONE);
  // bp — 부호를 붙인 소수 첫째 자리(0으로 반올림되면 부호 없이 0.0)
  const bp = v => {
    const s = Math.abs(v).toFixed(1);
    return (Number(s) === 0 ? "0.0" : (v < 0 ? "-" : "+") + s) + "bp";
  };
  const texts = v => (Array.isArray(v) ? v : []).map(x => str(x, 400)).filter(Boolean);
  const plusDays = (d, n) => new Date(Date.parse(d + "T00:00:00Z") + n * 86400000).toISOString().slice(0, 10);

  // ── 첫 화면: 이번 주 달라진 것 ─────────────────────────────────────────────────────────
  function pair(v, ok) {                     // {from, to} — 각 쪽은 꼴이 맞는 값 또는 null. 꼴이 어긋나면 그 칸을 뺀다
    if (!isObj(v)) return null;
    const side = x => (x === null ? null : ok(x) ? x : undefined);
    const from = side(v.from), to = side(v.to);
    return from === undefined || to === undefined || (from === null && to === null) ? null : { from, to };
  }
  function windowOf(w) {
    const spec = isObj(w) ? WINDOWS.find(([k]) => k === w.key) : null;
    if (!spec || !(w.from === null || day(w.from))) return null;
    const rules = (Array.isArray(w.rules) ? w.rules : []).filter(r => isObj(r) && str(r.key, 40) && str(r.title, 80) &&
      (r.from === null || status(r.from)) && status(r.to));
    const met = isObj(w.met) && count(w.met.from) && count(w.met.to) && count(w.met.total_from) && count(w.met.total_to) ? w.met : null;
    const health = {};
    for (const k of ["lost", "recovered", "stale", "fresh"])
      health[k] = (isObj(w.health) && Array.isArray(w.health[k]) ? w.health[k] : [])
        .filter(h => isObj(h) && typeof h.series === "string" && SERIES.test(h.series));
    return { key: w.key, label: str(w.label, 20) || spec[1], from: w.from, rules, met,
      core: pair(w.core, x => typeof x === "string" && RATIO.test(x)), neutral: pair(w.neutral, x => typeof x === "string" && RATIO.test(x)),
      candidate: pair(w.candidate, x => !!str(x, 12)), transition: pair(w.transition, x => count(x) && x <= AUTO), health };
  }
  const series = list => list.map(h => h.series + (str(h.label, 60) ? `(${h.label})` : "")).join(" · ");
  // 창 하나 — 바뀐 것만 줄마다, 그대로인 칸은 '그대로:' 한 줄, 그때 기록에 없던 칸(레짐 점검 절이 생기기 전 등)은 따로 한 줄
  function windowBlock(w) {
    const head = el("h3", {}, w.label, w.from ? el("small", {}, ` ${w.from} 대비`) : null);
    if (!w.from) return el("div", { class: "chg-window" }, head, el("p", { class: "muted" }, "견줄 공개 기록이 없습니다."));
    const items = [], same = [], unrecorded = [];
    if (!w.rules.length) items.push(el("li", {}, "바뀐 규칙 없음"));
    for (const r of w.rules)
      items.push(el("li", {}, el("strong", {}, r.title), r.from === null ? `: 새 규칙 → ${word(r.to)}` : `: ${word(r.from)} → ${word(r.to)}`));
    if (w.met) {
      const a = `${w.met.from}/${w.met.total_from}`, b = `${w.met.to}/${w.met.total_to}`;
      if (a === b) same.push(`충족 규칙 ${b}`); else items.push(el("li", {}, `충족 규칙 ${a} → ${b}`));
    }
    for (const [name, p, show] of [["핵심 신호", w.core, String], ["중립 규칙", w.neutral, String], ["국면 후보", w.candidate, String],
      ["전환 경계 자동 트리거", w.transition, n => `${n}/${AUTO}`]]) {
      if (!p) continue;
      if (p.from === null) unrecorded.push(`${name} ${show(p.to)}`);
      else if (p.from === p.to) same.push(`${name} ${show(p.to)}`);
      else items.push(el("li", {}, `${name} ${show(p.from)} → ${p.to === null ? NONE : show(p.to)}`));
    }
    const h = w.health;
    for (const [k, name] of [["lost", "받지 못하게 된 시리즈"], ["recovered", "다시 받은 시리즈"], ["stale", "오래된 자료가 된 시리즈"],
      ["fresh", "오래됨이 풀린 시리즈"]])
      if (h[k].length) items.push(el("li", {}, `${name}: ${series(h[k])}`));
    if (!["lost", "recovered", "stale", "fresh"].some(k => h[k].length)) same.push("자료 상태");
    if (same.length) items.push(el("li", { class: "chg-same" }, "그대로: " + same.join(" · ")));
    if (unrecorded.length) items.push(el("li", { class: "chg-same" }, "그때 기록하지 않은 칸(지금 값): " + unrecorded.join(" · ")));
    return el("div", { class: "chg-window" }, head, el("ul", { class: "chg-list" }, ...items));
  }
  function recentBlock(list) {
    const rows = (Array.isArray(list) ? list : []).filter(r => isObj(r) && day(r.date) && str(r.key, 40) && str(r.title, 80) &&
      status(r.from) && status(r.to));
    return el("div", { class: "chg-window" }, el("h3", {}, RECENT),
      rows.length ? el("ul", { class: "chg-list" }, ...rows.map(r => el("li", {}, `${r.date} · `, el("strong", {}, r.title),
        ` ${word(r.from)} → ${word(r.to)}`)))
        : el("p", { class: "muted" }, "최근 30일 사이 규칙 전환이 없습니다."));
  }
  function renderChanges(d) {
    const wrap = document.getElementById("changes-wrap");
    if (!wrap || !isObj(d) || d.schema !== 1 || !day(d.asof) || !Array.isArray(d.headline) || !Array.isArray(d.windows)) return false;
    const head = texts(d.headline).slice(0, 3);
    if (!head.length) return false;
    const windows = d.windows.map(windowOf).filter(Boolean);
    const more = [...windows.map(w => w.label), RECENT].join(" · ");
    wrap.replaceChildren(
      el("div", { class: "section-heading" }, el("h2", { id: "changes-title" }, "이번 주 달라진 것"),
        el("span", { class: "reference-label" }, CHG_LABEL)),
      el("div", { class: "panel chg" },
        el("p", { class: "muted chg-asof" }, `${d.asof} 공개 기록 기준`),
        el("ul", { class: "chg-head" }, ...head.map(t => el("li", {}, t))),
        el("details", { class: "rule-detail chg-more" }, el("summary", {}, "자세히 — " + more),
          ...windows.map(windowBlock), recentBlock(d.recent)),
        el("p", { class: "muted chg-note" }, NOTE, " ", el("a", { href: "#ledger" }, "기록 장부 보기 →"))));
    return true;
  }

  // ── 기록 장부 화면 ───────────────────────────────────────────────────────────────────
  function protocolOf(p) {
    if (!isObj(p) || !Number.isInteger(p.version) || p.version < 1 || !day(p.fixed)) return null;
    const horizons = (Array.isArray(p.horizons_weeks) ? p.horizons_weeks : []).filter(h => Number.isInteger(h) && h > 0 && h <= 520);
    const outcomes = (Array.isArray(p.outcomes) ? p.outcomes : [])
      .filter(o => isObj(o) && typeof o.key === "string" && KEY.test(o.key) && str(o.label, 40) && typeof o.series === "string" &&
        SERIES.test(o.series));
    if (!horizons.length || !outcomes.length || !Number.isInteger(p.n_min) || p.n_min < 1 || !count(p.tolerance_days)) return null;
    return { version: p.version, fixed: p.fixed, horizons, outcomes, nMin: p.n_min, tol: p.tolerance_days,
      startDays: Number.isInteger(p.start_days) && p.start_days > 0 && p.start_days <= 31 ? p.start_days : null, text: texts(p.text) };
  }
  function cellOf(c) {                       // 결과 한 칸 — 꼴이 어긋나면 null('—')
    if (!isObj(c) || !STATES.includes(c.state)) return null;
    if (c.state === "done")
      return num(c.change_bp) && num(c.demeaned_bp) && day(c.start) && day(c.end) ? c : null;
    return c;
  }
  function eventOf(e) {
    if (!isObj(e) || !day(e.date) || !known(e.from) || !known(e.to) || e.from === e.to || typeof e.before_protocol !== "boolean") return null;
    return { date: e.date, from: e.from, to: e.to, pre: e.before_protocol,
      core: typeof e.core === "string" && RATIO.test(e.core) ? e.core : null, candidate: str(e.candidate, 12),
      outcomes: isObj(e.outcomes) ? e.outcomes : {} };
  }
  function ruleOf(r) {
    if (!isObj(r) || typeof r.key !== "string" || !KEY.test(r.key) || !str(r.title, 80) || !day(r.first) || !status(r.now) ||
        !(r.start === null || known(r.start))) return null;
    const raw = Array.isArray(r.events) ? r.events : [];
    const events = raw.map(eventOf).filter(Boolean).sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
    return { key: r.key, title: r.title, first: r.first, last: day(r.last) ? r.last : null, start: r.start, now: r.now,
      since: day(r.since) ? r.since : null, unknownDays: count(r.unknown_days) ? r.unknown_days : null, events,
      open: raw.length === 0,                // 전환이 하나도 없던 규칙 — 지금 상태는 기록이 시작된 날(또는 규칙을 더한 날)에 잘린다
      lastKnown: events.length ? events[events.length - 1].to : r.start,
      summary: isObj(r.summary) ? r.summary : {} };
  }
  // 지금 상태가 이어진 첫 날 — 전환이 없던 규칙은 기록의 앞 끝에서 잘린 날이라 그렇게 적는다(그 앞부터일 수 있다)
  function sincePhrase(r, histFrom) {
    if (!r.since) return null;
    if (!r.open || !day(histFrom)) return `${r.since}부터`;
    if (r.since !== r.first) return `첫 판정(${r.since})부터`;
    if (r.first > histFrom) return `규칙 추가(${r.first})부터`;
    return `기록 시작(${r.since}) 이전부터`;
  }
  // 가장 최근 기록에 없는 규칙 — 그 규칙의 마지막 기록이 장부의 마지막 기록보다 앞
  const retired = (r, histTo) => !!(r.last && day(histTo) && r.last < histTo);
  const outcome = (e, h, key) => cellOf(own(e.outcomes, String(h)) && isObj(e.outcomes[String(h)]) ? e.outcomes[String(h)][key] : null);
  // 기다리는 중 — 끝 점을 찾을 날(출발 + 7 × 주 수일, ±tol일)
  const waitEnd = (c, h, tol) => (day(c.start) ? `끝 점 ${plusDays(c.start, 7 * h)}±${tol}일` : null);
  function outcomeCell(c, h, tol) {
    if (!c) return el("td", {}, "—");
    if (c.state === "pending") return el("td", {}, el("span", { class: "ledger-wait" }, "기다리는 중"),
      day(c.start) ? el("small", {}, `출발 ${c.start} · ${waitEnd(c, h, tol)}`) : null);
    if (c.state === "missing") return el("td", {}, el("span", { class: "ledger-wait" }, "자료 없음"));
    return el("td", {}, el("span", { class: "ledger-num" }, bp(c.change_bp)), el("small", {}, "평균을 뺀 값 " + bp(c.demeaned_bp)),
      el("small", {}, `${c.start} → ${c.end}`));
  }
  function summaryCell(s, nMin) {
    if (!isObj(s) || !count(s.n)) return el("td", {}, "—");
    if (s.n < nMin) return el("td", {}, el("span", { class: "ledger-wait" }, `판단 보류 (${s.n}/${nMin})`));
    if (!num(s.mean_demeaned_bp) || !num(s.up_share) || s.up_share < 0 || s.up_share > 1) return el("td", {}, "—");
    return el("td", {}, el("span", { class: "ledger-num" }, "평균을 뺀 값 " + bp(s.mean_demeaned_bp)),
      el("small", {}, `오른 비율 ${Math.round(s.up_share * 100)}% · ${s.n}건`));
  }
  const headRow = (first, p) => el("thead", {}, el("tr", {}, el("th", { scope: "col" }, first),
    ...p.outcomes.map(o => el("th", { scope: "col" }, o.label))));
  // 표 하나 — 설명 줄은 표 밖(좁은 화면에서도 접혀 다 보이게), 표는 가로 스크롤 상자 안. 표의 이름은 그 설명 줄(aria-labelledby)
  let capSeq = 0;
  function block(cap, cls, ...parts) {
    const id = "ledger-cap-" + (++capSeq);
    return el("div", { class: "ledger-block" }, el("p", { class: "muted ledger-cap", id }, cap),
      el("div", { class: "ledger-scroll" }, el("table", { class: "ledger-table " + cls, "aria-labelledby": id }, ...parts)));
  }
  function eventBlock(e, p) {
    const ctx = [e.core ? `그날 핵심 신호 ${e.core}` : null, e.candidate ? `국면 후보 ${e.candidate}` : null].filter(Boolean);
    return el("div", { class: "ledger-event" },
      el("p", {}, el("strong", {}, e.date), ` ${word(e.from)} → ${word(e.to)}`,
        e.pre ? el("span", { class: "ledger-pre" }, "약속 전") : null,
        ctx.length ? el("small", {}, " · " + ctx.join(" · ")) : null),
      block(`${e.date} 전환 뒤 변화(주간 점, bp)`, "ledger-out",
        headRow("기간", p),
        el("tbody", {}, ...p.horizons.map(h => el("tr", {}, el("th", { scope: "row" }, `${h}주 뒤`),
          ...p.outcomes.map(o => outcomeCell(outcome(e, h, o.key), h, p.tol)))))));
  }
  function summaryBlock(r, p) {
    const rows = [];
    for (const [dir, name] of DIRS) for (const h of p.horizons) {
      const byDir = isObj(r.summary[dir]) ? r.summary[dir] : {}, byH = isObj(byDir[String(h)]) ? byDir[String(h)] : {};
      rows.push(el("tr", {}, el("th", { scope: "row" }, `${name} ${h}주`), ...p.outcomes.map(o => summaryCell(byH[o.key], p.nMin))));
    }
    return block(`방향별 요약 — 약속 뒤 전환만, ${p.nMin}건이 모이기 전에는 판단 보류`, "ledger-sum",
      headRow("방향 · 기간", p), el("tbody", {}, ...rows));
  }
  function nowFact(r, hist) {
    const since = sincePhrase(r, hist.from);
    if (retired(r, hist.to)) return `지금은 싣지 않는 규칙 · 마지막 기록 ${r.last}(${word(r.now)})`;
    if (r.now === "unknown")
      return "지금 판정 불가" + (known(r.lastKnown) && since ? ` · 직전 판정 ${word(r.lastKnown)}, ${since}` : "");
    return `지금 ${word(r.now)}` + (since ? ` · ${since}` : "");
  }
  function ruleDetails(r, p, hist) {
    const pre = r.events.filter(e => e.pre).length;
    const facts = [`처음 기록 ${r.first}`, `처음 상태 ${r.start ? word(r.start) : NONE}`, nowFact(r, hist),
      r.unknownDays !== null ? `판정 불가 기록 ${r.unknownDays}일` : null].filter(Boolean);
    return el("details", { class: "rule-detail ledger-rule" },
      el("summary", {}, `${r.title} · 전환 ${r.events.length}건` + (pre ? `(약속 전 ${pre}건 포함)` : "")),
      el("p", { class: "muted" }, facts.join(" · ")),
      ...(r.events.length ? r.events.map(e => eventBlock(e, p)) : [el("p", { class: "muted" }, "전환이 없습니다.")]),
      summaryBlock(r, p));
  }
  function ruleTable(rules, p, hist) {
    const h = p.horizons[0], o = p.outcomes[0];
    const rows = rules.map(r => {
      const last = r.events.length ? r.events[r.events.length - 1] : null, after = r.events.filter(e => !e.pre).length;
      const c = last ? outcome(last, h, o.key) : null, gone = retired(r, hist.to), since = sincePhrase(r, hist.from);
      const move = !last ? el("td", {}, "—") : !c ? el("td", {}, "—")
        : c.state === "pending" ? el("td", {}, el("span", { class: "ledger-wait" }, "기다리는 중"),
          waitEnd(c, h, p.tol) ? el("small", {}, waitEnd(c, h, p.tol)) : null)
        : c.state === "missing" ? el("td", {}, el("span", { class: "ledger-wait" }, "자료 없음"))
        : el("td", {}, el("span", { class: "ledger-num" }, bp(c.demeaned_bp)));
      const state = gone ? el("td", {}, el("span", { class: "ledger-wait" }, "지금은 싣지 않는 규칙"),
        el("small", {}, `마지막 기록 ${r.last} · ${word(r.now)}`))
        : el("td", {}, el("span", { class: "tag " + r.now }, word(r.now)));
      const from = gone ? el("td", {}, "—")
        : r.now === "unknown" ? el("td", {}, "—", known(r.lastKnown) && since ? el("small", {}, `직전 판정 ${word(r.lastKnown)} · ${since}`) : null)
        : el("td", {}, !since ? "—" : r.open ? since : r.since);
      return el("tr", {}, el("th", { scope: "row" }, r.title), state, from,
        el("td", {}, `${after} / ${r.events.length - after}`),
        el("td", {}, last ? `${last.date} ${word(last.from)} → ${word(last.to)}` : "없음",
          last && last.pre ? el("span", { class: "ledger-pre" }, "약속 전") : null),
        move);
    });
    return block(`규칙별 상태와 전환 — 마지막 열은 최근 전환 뒤 ${h}주의 ${o.label} 변화에서 평균을 뺀 값`, "ledger-rules",
      el("thead", {}, el("tr", {}, ...["규칙", "지금 상태", "언제부터", "전환 수(약속 뒤 / 전)", "최근 전환", `${h}주 뒤 ${o.label}(평균을 뺀 값)`]
        .map(t => el("th", { scope: "col" }, t)))),
      el("tbody", {}, ...(rows.length ? rows : [el("tr", {}, el("td", { colspan: "6" }, "규칙 기록이 없습니다."))])));
  }
  // 평균(기준)을 잰 쌍의 범위 — baseline_detail(기간 · 시리즈마다 {n, from, to})에서. 없으면 그래프 자료 범위라고만
  function baseSpan(p, charts) {
    const det = isObj(charts.baseline_detail) ? charts.baseline_detail : {};
    const spans = p.horizons.flatMap(h => p.outcomes.map(o => {
      const x = isObj(det[String(h)]) ? det[String(h)][o.key] : null;
      return isObj(x) && count(x.n) && x.n > 0 && day(x.from) && day(x.to) ? x : null;
    })).filter(Boolean);
    if (spans.length) {
      const from = spans.map(x => x.from).sort()[0], to = spans.map(x => x.to).sort().slice(-1)[0];
      const ns = spans.map(x => x.n), lo = Math.min(...ns), hi = Math.max(...ns);
      return ` · 기간이 다 지난 주간 쌍으로 잰 값(첫 출발 ${from} ~ 마지막 끝 ${to}, 쌍 ${lo === hi ? lo : lo + "~" + hi}개 — 시리즈·기간마다 다름)`;
    }
    const win = isObj(charts.window) && day(charts.window.from) && day(charts.window.to) ? charts.window : null;
    return win ? ` · 그래프 자료 범위 ${win.from}~${win.to} 안에서 잰 값` : "";
  }
  // 계산값 고지와 FRED 권장 인용 — 꼴이 맞는 것만, 시리즈마다 하나
  function citeBox(d, p) {
    const notes = texts(d.notices);
    const seen = new Set(), cites = [];
    for (const s of Array.isArray(d.sources) ? d.sources : []) {
      if (!isObj(s) || typeof s.series !== "string" || !SERIES.test(s.series) || seen.has(s.series)) continue;
      if (!p.outcomes.some(o => o.series === s.series) || typeof s.citation !== "string" || !CITE.test(s.citation)) continue;
      seen.add(s.series);
      cites.push(s.citation);
    }
    if (!notes.length && !cites.length) return null;
    return el("div", { class: "notices ledger-cite" }, ...notes.map(t => el("p", {}, t)),
      cites.length ? el("p", {}, "권장 인용: " + cites.join(" ")) : null);
  }
  function protocolBox(p, charts, d) {
    const base = isObj(charts.baseline) ? charts.baseline : {};
    const baseText = p.horizons.map(h => {
      const b = isObj(base[String(h)]) ? base[String(h)] : {};
      return `${h}주 — ` + p.outcomes.map(o => `${o.label} ${num(b[o.key]) ? bp(b[o.key]) : "—"}`).join(" · ");
    }).join(" / ");
    const lastPts = isObj(charts.last) ? p.outcomes.filter(o => day(charts.last[o.key])).map(o => `${o.label} ${charts.last[o.key]}`) : [];
    const seriesParts = p.outcomes.flatMap((o, i) => [i ? " · " : "", o.label + " ",
      link(o.series, "https://fred.stlouisfed.org/series/" + o.series)]).filter(x => x !== "");
    return el("div", { class: "panel ledger-protocol" },
      el("h3", {}, `평가 약속 ${p.version}판`, el("small", {}, ` · ${p.fixed} 고정`)),
      el("ul", { class: "chg-list" },
        el("li", {}, `보는 기간: 전환 뒤 ${p.horizons.map(h => h + "주").join(" · ")} — 출발 점은 전환 날 이후(그날 포함)` +
          (p.startDays !== null ? ` ${p.startDays}일 안` : "") + "의 첫 주간 점(그날 기록은 그 앞날까지의 자료로 정해져 전환을 만든 움직임은 넣지 않습니다), " +
          `끝 점은 출발 점에서 주 수×7일 뒤 날짜의 ±${p.tol}일 안에서 가장 가까운 주간 점`),
        el("li", {}, "보는 금리: ", ...seriesParts, " (FRED)"),
        el("li", {}, `평균(기준, 계산값): ${baseText}`, el("small", {}, baseSpan(p, charts))),
        lastPts.length ? el("li", {}, `그래프의 마지막 점: ${lastPts.join(" · ")} — 끝 점을 찾을 날의 ±${p.tol}일이 이 날을 넘으면 기다리는 중`) : null,
        el("li", {}, `방향별 요약은 약속 뒤 전환이 ${p.nMin}건 이상 모였을 때만 — 그 전에는 '판단 보류 (n/${p.nMin})'`),
        el("li", {}, CAUSE),
        el("li", {}, "약속을 고치면 새 판 번호와 날짜를 붙입니다 — 같은 판 안에서도 결과와 평균은 갱신마다 그날 그래프 자료로 다시 잽니다.")),
      p.text.length ? el("details", { class: "rule-detail ledger-text" }, el("summary", {}, `약속 문장 ${p.text.length}개(자료 파일 그대로)`),
        el("div", { class: "notices" }, ...p.text.map(t => el("p", {}, t)))) : null,
      citeBox(d, p));
  }
  function renderLedger(d) {
    const wrap = document.getElementById("ledger-wrap");
    if (!wrap || !isObj(d) || d.schema !== 1 || !Array.isArray(d.rules)) return false;
    const p = protocolOf(d.protocol);
    if (!p) return false;
    const hist = isObj(d.history) ? d.history : {}, charts = isObj(d.charts) ? d.charts : {};
    const rules = d.rules.map(ruleOf).filter(Boolean);
    const span = day(hist.from) ? `${hist.from}부터` + (day(hist.to) ? ` ${hist.to}까지` : "") : NONE;
    const counted = (count(hist.snapshots) ? ` 공개 기록 ${hist.snapshots}일 치` : "") +
      (count(hist.skipped) && hist.skipped > 0 ? `(읽지 못해 건너뛴 파일 ${hist.skipped}개)` : "");
    const win = isObj(charts.window) && day(charts.window.from) && day(charts.window.to) ? charts.window : null;
    const basis = day(charts.date) ? `결과와 평균(기준)은 ${charts.date}의 그래프 자료(charts.json 주간 점` + (win ? `, ${win.from}~${win.to}` : "") +
      `)로 갱신마다 다시 잽니다. FRED가 값을 고치거나 그래프 창이 한 주씩 옮겨 가면 평균을 뺀 값이 조금씩 달라지고, ` +
      `출발 점이 창 밖으로 나간 전환은 '자료 없음'이 됩니다.`
      : "그래프 자료가 없어 결과를 적지 못했습니다.";
    wrap.replaceChildren(
      el("div", { class: "section-heading" }, el("h2", { id: "ledger-title" }, "기록 장부"),
        el("span", { class: "reference-label" }, `평가 약속 ${p.version}판 · ${LABEL}`)),
      protocolBox(p, charts, d),
      el("div", { class: "panel ledger-panel" }, el("h3", {}, "규칙별 상태"), ruleTable(rules, p, hist)),
      rules.length ? el("div", { class: "panel ledger-panel ledger-rules-detail" }, el("h3", {}, "규칙별 전환 기록"),
        ...rules.map(r => ruleDetails(r, p, hist))) : null,
      el("p", { class: "muted ledger-basis" }, `기록: ${span}${counted}. ${basis}`));
    return true;
  }

  // 두 자리를 따로 그린다 — 한쪽이 깨져도 다른 쪽은 그대로. 돌려주는 값: {changes, ledger}(그렸으면 true)
  function render(changes, ledger) {
    const out = { changes: false, ledger: false };
    try { out.changes = renderChanges(changes) === true; } catch (e) { out.changes = false; }
    try { out.ledger = renderLedger(ledger) === true; } catch (e) { out.ledger = false; }
    return out;
  }

  return Object.freeze({ render, renderChanges, renderLedger, STATUS, NOTE, EMPTY, LABEL, CHG_LABEL, CAUSE, RECENT });
})();
