// 읽기 노트 — 읽은 글을 내 말로 옮긴 공부 기록의 목록("#notes")과 글("#notes/<글 이름>").
// 번역·전재가 아니다: 원문의 문장·그림·표는 싣지 않고 링크로만 잇는다(그림은 공개 통계와 직접 그린 도식).
// 자료는 data/ 아래 JSON 셋뿐이고 바깥 요청은 하지 않는다.
//   data/notes.json         노트 목록과 글마다의 블록 배열(← scripts/notes_build.py ← notes/*.md). #notes에 처음 들어올 때 한 번 읽는다
//   data/charts.json        사이트의 규칙 그래프(평일 아침마다 갱신) — 글이 끼워 넣은 것만, 그 글을 열 때 읽는다
//   data/notes_charts.json  받아 둔 값으로 그리는 정적 그래프(← scripts/notes_charts.py)
// index.html의 applyView()가 setView(화면 이름, 뒤에 붙은 값)를 부른다. index.html 안의 el() · svgEl() · getJson() · calm()과
// window.MacroCharts.lineChart를 쓴다(부를 때 이미 정의돼 있다). 글자는 el()의 텍스트로만 넣는다(자료를 HTML로 해석하지 않는다).
// 링크는 https일 때만 걸고(아니면 글자로 둔다) 새 창으로 연다. 키보드: 목록·차례·링크는 Tab. 노트 화면 안에서 옮기면 초점이
// 따라간다(글로 가면 제목, 목록으로 돌아오면 읽던 카드). 다른 화면에서 들어올 때는 초점을 가져가지 않는다(누른 링크에 둔다).
// 화면 읽기용 알림은 #notes-wrap 맨 앞의 상자 하나(role=status)에 글자만 바꿔 넣는다 — 글자를 담은 채 새로 끼운 알림은 잘 읽히지 않는다.
window.ReadingNotes = (() => {
  "use strict";
  const ISSUES = "https://github.com/yun-macrolab/macro-regime-check/issues";
  const FILES = { notes: "data/notes.json", charts: "data/charts.json", fixed: "data/notes_charts.json" };
  const SLUG = /^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$/, DAY = /^\d{4}-\d{2}-\d{2}$/;
  // 빌더(notes_build.py)의 주소 규칙과 같다 — https뿐이고, 보이지 않는 글자(제어 Cc · 서식 Cf)가 섞인 주소는 걸지 않는다
  const HTTPS = /^https:\/\/[A-Za-z0-9.-]+(?::\d+)?(?:\/[^\s()<>"'`\\\p{Cc}\p{Cf}]*)?$/u;
  const FORCE_COLORS = ["var(--ch-2)", "var(--ch-3)"];                 // 도식의 두 힘(첫째 호박색 · 둘째 하늘색) — 그래프 색을 그대로 쓴다
  const LINE_COLORS = ["var(--ch-1)", "var(--ch-2)", "var(--ch-3)"];   // 정적 그래프의 선(charts.js와 같은 순서)
  // 도식 한 칸의 자리(viewBox 단위): 0선 Z, 힘 화살표의 x, 합이 놓이는 자리의 x(하나일 때 · 둘일 때)와 0선에서의 거리
  const ND = { W: 200, H: 172, Z: 86, STEP: 23, X: [50, 94], NET: [[152], [136, 172]], OFF: { above: -46, zero: 0, below: 46 } };
  const SAY = { wait: "읽기 노트를 불러오는 중…", fail: "읽기 노트 자료를 불러오지 못했다.",
                missing: "주소에 적힌 노트를 찾지 못했다 — 아래 목록에서 골라 달라." };
  const got = {};                                   // 받고 있거나 받은 자료(약속) — 파일마다 한 번만 읽는다
  let notes = null, failed = false, shown = null, wanted = "";
  let marks = { title: null, cards: {} };           // 화면이 바뀐 뒤 초점을 둘 곳
  let live = null, stage = null;                    // #notes-wrap 안의 둘: 알림 상자(늘 있다)와 화면이 그려지는 자리
  let away = false, retry = false;                  // 다른 화면에 가 있었다 · '다시 읽기'를 눌렀다(초점을 어디 둘지 가른다)

  const isObj = v => v !== null && typeof v === "object" && !Array.isArray(v);
  const list = v => (Array.isArray(v) ? v : []);
  const str = (v, max) => (typeof v === "string" && v.length <= (max || 600) ? v : "");
  const own = (o, k) => (isObj(o) && Object.prototype.hasOwnProperty.call(o, k) ? o[k] : undefined);
  const fix = (v, unit) => (Number(v.toFixed(2)) === 0 ? "0.00" : v.toFixed(2)) + unit;      // 음의 0은 적지 않는다
  const valid = n => isObj(n) && SLUG.test(n.slug) && !!str(n.title, 120) && DAY.test(n.date) && Array.isArray(n.blocks);

  function load(name) {
    if (!got[name]) got[name] = getJson(FILES[name]).catch(e => { delete got[name]; throw e; });   // 실패하면 다음에 다시 읽는다
    return got[name];
  }

  // ── 글자 조각 ──
  function outLink(text, href, cls) {
    return el("a", { href, target: "_blank", rel: "noopener noreferrer", class: cls || "note-out" }, text,
      el("span", { class: "sr" }, " (새 창)"));
  }
  function pieces(spans) {
    return list(spans).filter(s => isObj(s) && typeof s.text === "string").map(s => {
      const inner = typeof s.href === "string" && HTTPS.test(s.href) ? outLink(s.text, s.href) : s.text;
      return s.bold === true ? el("strong", {}, inner) : inner;
    });
  }
  const textOf = spans => list(spans).map(s => (isObj(s) ? str(s.text) : "")).join("");
  function swatch(color) {
    const k = el("span", { class: "ch-key", "aria-hidden": "true" });
    k.style.background = color;
    return k;
  }
  // 맨 아래 고정 고지 — 목록에도 글에도 붙는다
  function fixedNotice() {
    return el("p", { class: "note-fixed" },
      "이 노트는 원문을 읽고 내 말로 옮긴 공부 기록이다. 번역이나 전재가 아니며 원문의 문장·그림·표를 싣지 않았다. 틀린 곳은 ",
      outLink("저장소 Issues", ISSUES), "로.");
  }

  // ── 본문 블록 ──
  function table(b) {
    const head = list(b.head), labels = head.map(textOf);
    const cell = (c, i) => {
      const kids = list(c).length ? pieces(c) : ["—"];
      if (i === 0) return el("th", { scope: "row", role: "rowheader" }, ...kids);
      return el("td", { role: "cell", "data-label": labels[i] || "", class: list(c).length ? "has" : "none" }, ...kids);
    };
    // 좁은 화면에서는 줄마다 카드로 쌓는다(notes.css) — 그때도 표로 읽히게 역할을 적어 둔다. 빈 머리 칸(왼쪽 위 모서리)은 열 머리가 아니다
    return el("div", { class: "note-table" }, el("table", { role: "table" },
      el("thead", { role: "rowgroup" }, el("tr", { role: "row" },
        ...head.map(h => (list(h).length ? el("th", { scope: "col", role: "columnheader" }, ...pieces(h)) : el("td", { role: "cell" }))))),
      el("tbody", { role: "rowgroup" }, ...list(b.rows).map(r => el("tr", { role: "row" }, ...list(r).map(cell))))));
  }
  function questions(b) {
    return el("ol", { class: "note-questions", role: "list" }, ...list(b.items).map((it, i) =>
      el("li", {}, el("span", { class: "note-q", "aria-hidden": "true" }, "Q" + (i + 1)), el("p", {}, ...pieces(it)))));
  }
  function capLine(no, nodes, extra) {
    return el("p", { class: "note-cap" }, el("span", { class: "note-cap-no" }, "그림 " + no), " ", ...nodes, extra || null);
  }
  // 자료를 받아야 그릴 수 있는 그림 — 받는 동안·실패했을 때도 자리를 지킨다(글은 그대로 읽힌다)
  function later(name, no, caption, make) {
    const box = el("div", { class: "note-fig" }, el("p", { class: "note-cap" }, `그림 ${no}의 자료를 불러오는 중…`));
    load(name).then(data => {
      const made = make(data);
      if (!made.node) throw new Error("그릴 자료 없음");
      box.replaceChildren(el("div", { class: "panel" }, made.node), capLine(no, pieces(caption), made.extra));
    }).catch(() => box.replaceChildren(capLine(no, pieces(caption), " (그래프 자료를 불러오지 못했다.)")));
    return box;
  }
  function figure(b, no) {
    if (b.kind === "site_chart") return later("charts", no, b.caption, data => {
      const spec = own(own(data, "rules"), str(b.rule, 40));
      // 사이트의 규칙 그래프를 그대로 — 매일 갱신되는 자료라 기준일을 함께 적는다
      return { node: isObj(spec) && window.MacroCharts ? window.MacroCharts.lineChart(spec, { height: 230, caption: true }) : null,
               extra: isObj(data) && DAY.test(data.date) ? ` 그래프 자료 기준일 ${data.date}.` : "" };
    });
    if (b.kind === "static_chart") return later("fixed", no, b.caption,
      data => ({ node: yearChart(own(own(data, "charts"), str(b.chart, 40))) }));
    const drawn = b.kind === "diagram" ? diagram(b.diagram) : null;
    return drawn ? el("div", { class: "note-fig" }, el("div", { class: "panel" }, drawn), capLine(no, [str(b.diagram.foot)])) : null;
  }
  const BLOCKS = {
    heading: b => (/^s\d+$/.test(b.id) ? el(b.level === 3 ? "h4" : "h3", { id: "note-" + b.id, tabindex: "-1" }, str(b.text)) : null),
    para: b => el("p", {}, ...pieces(b.spans)),
    list: b => el(b.ordered === true ? "ol" : "ul", {}, ...list(b.items).map(it => el("li", {}, ...pieces(it)))),
    table, questions, figure,
  };

  // ── 도식(kind: balance) — 0선을 사이에 두고 위·아래로 미는 힘과 그 합이 놓이는 자리. 수치 축이 없는 개념도다 ──
  function arrow(x, f, color) {
    const len = ND.STEP * ([1, 2, 3].includes(f.size) ? f.size : 1);
    const from = f.dir === "both" ? ND.Z + len / 2 : ND.Z;
    const to = f.dir === "down" ? ND.Z + len : f.dir === "both" ? ND.Z - len / 2 : ND.Z - len;
    const head = (y, up) => svgEl("path", { d: `M${x - 6} ${y + (up ? 10 : -10)}L${x} ${y}L${x + 6} ${y + (up ? 10 : -10)}Z` });
    const g = svgEl("g", { class: "nd-arrow" });
    g.style.color = color;
    g.append(svgEl("line", { x1: x, x2: x, y1: from + (f.dir === "both" ? -8 : 0), y2: to + (to < from ? 8 : -8) }), head(to, to < from));
    if (f.dir === "both") g.append(head(from, false));
    return g;
  }
  function gem(x, n) {
    const y = ND.Z + (Object.prototype.hasOwnProperty.call(ND.OFF, n.pos) ? ND.OFF[n.pos] : 0);
    const out = [svgEl("path", { class: "nd-gem", d: `M${x} ${y - 8}L${x + 8} ${y}L${x} ${y + 8}L${x - 8} ${y}Z` })];
    if (str(n.tag, 10)) out.push(svgEl("text", { class: "nd-tag", x, y: n.pos === "below" ? y + 22 : y - 14, "text-anchor": "middle" }, n.tag));
    return { y, out };
  }
  function balance(used, nets, forces) {
    const svg = svgEl("svg", { class: "nd-svg", viewBox: `0 0 ${ND.W} ${ND.H}`, "aria-hidden": "true", focusable: "false" });
    svg.append(svgEl("line", { class: "nd-zero", x1: 4, x2: ND.W - 4, y1: ND.Z, y2: ND.Z }),
      svgEl("text", { class: "nd-sign", x: 6, y: 14 }, "+"), svgEl("text", { class: "nd-sign", x: 6, y: ND.Z - 5 }, "0"),
      svgEl("text", { class: "nd-sign", x: 6, y: ND.H - 6 }, "−"));
    for (const f of used) {
      const i = forces.findIndex(x => x.key === f.key);
      if (i >= 0) svg.append(arrow(ND.X[i], f, FORCE_COLORS[i]));
    }
    const xs = ND.NET[nets.length - 1] || [], gems = nets.map((n, i) => gem(xs[i], n));
    if (gems.length === 2)                                     // 앞 자리에서 뒤 자리로 옮겨 갔다는 점선
      svg.append(svgEl("line", { class: "nd-shift", x1: xs[0] + 6, x2: xs[1] - 6, y1: gems[0].y, y2: gems[1].y }));
    for (const g of gems) svg.append(...g.out);
    return svg;
  }
  function cell(c, forces) {
    const index = f => forces.findIndex(x => x.key === f.key);
    const used = list(c.forces).filter(f => isObj(f) && index(f) >= 0), nets = list(c.net).filter(isObj).slice(0, 2);
    return el("div", { class: c.highlight === true ? "nd-cell nd-key" : "nd-cell" }, el("p", { class: "nd-name" }, str(c.label)),
      balance(used, nets, forces),
      el("ul", { class: "nd-notes" },
        ...used.map(f => el("li", {}, swatch(FORCE_COLORS[index(f)]), `${str(forces[index(f)].short)}: ${str(f.note)}`)),
        ...nets.map(n => el("li", {}, el("span", { class: "nd-gem-key", "aria-hidden": "true" }), str(n.note)))));
  }
  function diagram(d) {
    if (!isObj(d) || d.kind !== "balance") return null;
    const forces = list(d.forces).filter(isObj).slice(0, FORCE_COLORS.length);
    const cells = list(d.columns).filter(isObj).map(c => cell(c, forces));
    if (!cells.length) return null;
    // 칸 안의 글은 그림의 일부다 — 화면 읽기에는 설명 글(alt) 하나로 읽힌다
    return el("figure", { class: "nd" }, el("figcaption", { class: "ch-title" }, str(d.title)),
      el("div", { class: "ch-legend", "aria-hidden": "true" },
        ...forces.map((f, i) => el("span", {}, swatch(FORCE_COLORS[i]), `${str(f.label)} — ${str(f.effect)}`)),
        el("span", {}, el("span", { class: "nd-gem-key" }), str(d.net)), el("span", {}, el("span", { class: "nd-zero-key" }), str(d.zero))),
      el("div", { class: "nd-grid", role: "img", "aria-label": str(d.alt, 800) }, ...cells));
  }

  // ── 정적 그래프 — 받아 둔 값, 한 해에 점 하나라 가로축이 연도다. 모양은 charts.js의 그래프와 같은 문법(같은 CSS) ──
  function watch(box, draw) {
    let last = 0;
    const redraw = () => {
      const w = Math.floor(box.clientWidth);
      if (w && w !== last) { last = w; draw(w); }
    };
    if ("ResizeObserver" in window) new ResizeObserver(redraw).observe(box);
    else { requestAnimationFrame(redraw); window.addEventListener("resize", redraw); }
  }
  function drawLines(svg, lines, unit, X, Y, R) {
    const ends = [];
    for (const l of lines) {
      const d = l.pts.map((p, i) => `${i ? "L" : "M"}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`).join("");
      const path = svgEl("path", { class: "ch-line", d }), end = l.pts.at(-1);
      const dot = svgEl("circle", { class: "ch-dot", cx: X(end[0]), cy: Y(end[1]), r: 4 });
      path.style.stroke = l.color;
      dot.style.fill = l.color;
      svg.append(path, dot);
      ends.push({ y: Y(end[1]), label: fix(end[1], unit), color: l.color });
    }
    let floor = -Infinity;                                     // 끝 값 상자가 겹치면 아래로 밀어 둘 다 보이게
    for (const e of ends.sort((a, b) => a.y - b.y)) {
      const y = Math.max(e.y, floor + 18), box = svgEl("rect", { class: "ch-end-box", x: R + 5, y: y - 8, width: e.label.length * 7 + 8, height: 16 });
      box.style.fill = e.color;
      svg.append(box, svgEl("text", { class: "ch-end", x: R + 9, y: y + 4 }, e.label));
      floor = y;
    }
  }
  function drawYears(svg, lines, unit, width) {
    const H = 240, L = 40, R = Math.max(L + 80, width - 66), T = 10, B = H - 22, all = lines.flatMap(l => l.pts);
    const y0 = Math.min(...all.map(p => p[0])), y1 = Math.max(...all.map(p => p[0]));
    const low = Math.min(0, ...all.map(p => p[1])), high = Math.max(0, ...all.map(p => p[1])), pad = (high - low || 1) * 0.08;
    const lo = low - pad, hi = high + pad;
    const X = y => L + (y - y0) / Math.max(1, y1 - y0) * (R - L), Y = v => T + (hi - v) / (hi - lo) * (B - T);
    svg.replaceChildren();
    for (const [k, v] of [["viewBox", `0 0 ${width} ${H}`], ["width", width], ["height", H]]) svg.setAttribute(k, String(v));
    const step = [0.5, 1, 2, 5, 10, 20, 50].find(s => (hi - lo) / s <= 6) || (hi - lo) / 5;   // 눈금은 많아야 여섯 개
    for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) svg.append(
      svgEl("line", { class: v === 0 ? "ch-zero" : "ch-grid", x1: L, x2: R, y1: Y(v), y2: Y(v) }),
      svgEl("text", { class: "ch-tick", x: L - 6, y: Y(v) + 4, "text-anchor": "end" }, String(Number(v.toFixed(1)))));
    const gap = R - L < 300 ? 10 : 5;                          // 좁으면 10년마다
    for (let y = Math.ceil(y0 / gap) * gap; y <= y1; y += gap) svg.append(
      svgEl("line", { class: "ch-grid", x1: X(y), x2: X(y), y1: B, y2: B + 4 }),
      svgEl("text", { class: "ch-tick", x: X(y), y: H - 5, "text-anchor": "middle" }, String(y)));
    drawLines(svg, lines, unit, X, Y, R);
  }
  function yearTable(lines, unit) {
    const years = [...new Set(lines.flatMap(l => l.pts.map(p => p[0])))].sort((a, b) => b - a);
    const maps = lines.map(l => new Map(l.pts));
    return el("details", { class: "ch-table" }, el("summary", {}, "표로 보기"), el("div", { class: "ch-scroll" }, el("table", {},
      el("thead", {}, el("tr", {}, el("th", { scope: "col" }, "연도"),
        ...lines.map(l => el("th", { scope: "col" }, unit ? `${l.label} (${unit})` : l.label)))),
      el("tbody", {}, ...years.map(y => el("tr", {}, el("td", {}, String(y)),
        ...maps.map(m => el("td", {}, m.has(y) ? m.get(y).toFixed(2) : ""))))))));
  }
  function yearChart(c) {
    if (!isObj(c)) return null;
    const unit = str(c.unit, 8), title = str(c.title, 80);
    // 터무니없는 점(연도 1900~2100 밖, 값 ±1000 이상)은 버린다 — 눈금을 하나씩 그리는 반복이 화면을 멈추지 않게
    const sane = p => Array.isArray(p) && Number.isInteger(p[0]) && p[0] >= 1900 && p[0] <= 2100 && Number.isFinite(p[1]) && Math.abs(p[1]) < 1000;
    const lines = list(c.lines).filter(isObj).slice(0, LINE_COLORS.length).map((l, i) => ({ label: str(l.label, 40), color: LINE_COLORS[i],
      pts: list(l.points).filter(sane).sort((a, b) => a[0] - b[0]) }))
      .filter(l => l.pts.length > 1);
    if (!lines.length) return null;
    const ends = lines.map(l => `${l.label} ${l.pts[0][0]}년 ${fix(l.pts[0][1], unit)}, ${l.pts.at(-1)[0]}년 ${fix(l.pts.at(-1)[1], unit)}`);
    const svg = svgEl("svg", { role: "img", "aria-label": `${title}. ${ends.join(" · ")}. 해마다의 값은 아래 '표로 보기'에 있다.` });
    const plot = el("div", { class: "ch-plot" }, svg);
    watch(plot, w => drawYears(svg, lines, unit, w));
    const more = list(c.notices).filter(v => typeof v === "string" && v);
    return el("figure", { class: "ch" }, el("figcaption", { class: "ch-title" }, title),
      el("div", { class: "ch-legend" }, ...lines.map(l => el("span", {}, swatch(l.color), l.label))), plot,
      str(c.note) ? el("p", { class: "ch-note muted" }, c.note) : null,
      str(c.source_note) ? el("p", { class: "ch-note ch-source muted" }, c.source_note) : null,
      yearTable(lines, unit),
      more.length ? el("details", { class: "ch-table" }, el("summary", {}, "출처·계산 방법"),
        el("div", { class: "notices" }, ...more.map(v => el("p", {}, v)))) : null);
  }

  // ── 목록 화면 ──
  function card(n) {
    const src = isObj(n.source) ? n.source : {}, link = el("a", { href: "#notes/" + n.slug }, n.title);
    marks.cards[n.slug] = link;
    return el("li", {}, el("article", { class: "note-card" },
      el("p", { class: "note-kicker" }, str(src.name) || "출처 미상"), el("h3", {}, link),
      el("p", { class: "note-summary" }, ...pieces(n.summary)),
      el("p", { class: "note-meta" }, el("span", {}, "노트 " + n.date),
        DAY.test(src.published) ? el("span", {}, "원문 " + src.published) : null,
        Number.isInteger(n.minutes) ? el("span", {}, `읽는 데 ${n.minutes}분`) : null)));
  }
  function listing(missing) {
    const head = el("h2", { tabindex: "-1" }, "노트 목록");
    marks = { title: head, cards: {} };
    // 눈에 보이는 안내는 알림 상자가 같은 글로 읽어 준다 — 두 번 읽히지 않게 화면 읽기에서는 뺀다
    return el("div", { class: "notes" },
      missing ? el("p", { class: "note-missing", "aria-hidden": "true" }, SAY.missing) : null,
      el("div", { class: "section-heading" }, head, el("span", {}, `${notes.length}편 · 최근 글부터`)),
      notes.length ? el("ul", { class: "note-list", role: "list" }, ...notes.map(card)) : el("p", { class: "empty-state" }, "아직 올린 노트가 없다."),
      fixedNotice());
  }

  // ── 글 화면 ──
  function facts(n, src, url) {
    const row = (k, ...v) => el("div", {}, el("dt", {}, k), el("dd", {}, ...v));
    const name = str(src.title, 200) || str(src.name) || "원문";
    // 영문뿐인 원문 제목은 영어로 읽히게 표시한다(한국어 '(새 창)'은 그 밖에 남는다)
    const origin = /^[\x20-\x7e]+$/.test(name) && /[A-Za-z]{2}/.test(name) ? el("span", { lang: "en" }, name) : name;
    return el("dl", { class: "note-facts" },
      row("원문", url ? outLink(origin, url) : origin, str(src.title, 200) && str(src.name) ? el("small", {}, src.name) : null),
      row("저자", str(src.authors) || "—"), row("발행일", DAY.test(src.published) ? src.published : "—"),
      row("읽는 시간", Number.isInteger(n.minutes) ? `${n.minutes}분` : "—"), row("난이도", str(n.level) || "—"));
  }
  function rail(toc, url) {
    const jump = node => () => {                               // 움직임을 껐으면 바로 옮긴다
      node.scrollIntoView({ behavior: calm() ? "auto" : "smooth", block: "start" });
      node.focus({ preventScroll: true });
    };
    const items = toc.map(([text, node]) => {
      const b = el("button", { type: "button" }, text);
      b.addEventListener("click", jump(node));
      return el("li", {}, b);
    });
    return el("aside", { class: "note-rail" },
      items.length ? el("nav", { class: "note-toc", "aria-label": "이 글의 차례" }, el("h3", {}, "차례"), el("ol", { role: "list" }, ...items)) : null,
      url ? outLink("원문 읽기", url, "note-btn") : null);
  }
  function article(n) {
    const src = isObj(n.source) ? n.source : {}, url = HTTPS.test(src.url) ? src.url : "", toc = [];
    let figs = 0;
    const body = n.blocks.filter(isObj).map(b => {
      const draw = Object.prototype.hasOwnProperty.call(BLOCKS, b.type) ? BLOCKS[b.type] : null;
      const node = draw ? draw(b, b.type === "figure" ? ++figs : 0) : null;
      if (node && b.type === "heading" && b.level === 2) toc.push([str(b.text), node]);
      return node;
    });
    const title = el("h2", { id: "note-title", tabindex: "-1" }, n.title);
    marks = { title, cards: {} };
    return el("article", { class: "note", "aria-labelledby": "note-title" },
      el("p", { class: "note-back" }, el("a", { href: "#notes" }, "← 노트 목록")),
      el("header", { class: "note-head" }, el("p", { class: "note-kicker" }, "읽기 노트 · " + n.date), title, facts(n, src, url)),
      el("div", { class: "note-layout" }, rail(toc, url),
        el("div", { class: "note-body" },
          el("section", { class: "note-gist", "aria-label": "한 줄 결론" }, el("h3", {}, "한 줄 결론"), el("p", {}, ...pieces(n.summary))),
          ...body,
          el("p", { class: "note-end" }, url ? outLink("원문 읽기", url, "note-btn") : null, el("a", { href: "#notes" }, "← 노트 목록으로")))),
      fixedNotice());
  }

  // ── 화면 전환 ──
  function broken(wrap) {
    const again = el("button", { type: "button", class: "motion-toggle" }, "다시 읽기");
    again.addEventListener("click", () => { failed = false; shown = null; retry = true; start(wrap); paint(wrap); });
    return { again, node: el("p", { class: "empty-state" }, el("span", { "aria-hidden": "true" }, SAY.fail + " "), again) };
  }
  // 받는 중·실패 — 눈에 보이는 글은 알림 상자가 같은 글로 읽어 준다. '다시 읽기'가 또 실패하면 새 버튼에 초점을 둔다
  function waiting(wrap, state) {
    const fail = state === "fail" ? broken(wrap) : null;
    stage.replaceChildren(fail ? fail.node : el("p", { class: "muted", "aria-hidden": "true" }, SAY.wait));
    live.textContent = SAY[state];
    if (fail && retry) fail.again.focus({ preventScroll: true });
    if (fail) retry = false;
  }
  // back: 다른 화면에 갔다가 돌아왔다 — 그때는 초점을 가져가지 않는다
  function paint(wrap, back) {
    const state = failed ? "fail" : notes ? "ok" : "wait", key = state + "|" + wanted;
    if (key === shown) return;                                  // 같은 화면을 다시 그리지 않는다(applyView는 여러 번 불린다)
    const from = !back && state === "ok" && shown !== null && shown.startsWith("ok|") ? shown.slice(3) : null;
    shown = key;
    if (!live) {                                                // 알림 상자와 화면 자리는 한 번만 넣는다(뺐다 넣으면 새 알림으로 읽힌다)
      live = el("p", { class: "sr", role: "status" });
      stage = el("div", {});
      wrap.replaceChildren(live, stage);
    }
    if (state !== "ok") return waiting(wrap, state);
    const note = notes.find(n => n.slug === wanted), missing = !note && wanted !== "";
    stage.replaceChildren(note ? article(note) : listing(missing));
    live.textContent = missing ? SAY.missing : "";
    // 노트 화면 안에서 옮겨 다녔으면 읽던 자리로(글 → 제목, 목록 → 읽던 카드), '다시 읽기'로 그렸으면 제목으로 초점을 옮긴다
    const target = retry ? marks.title : from === null ? null : marks.cards[from] || marks.title;
    retry = false;
    if (!target) return;
    target.focus({ preventScroll: true });
    // index.html이 화면을 맨 위로 올린 다음에, 카드가 화면 밖이면 보이는 데까지만 옮긴다(바로 옮겨지고 움직임은 없다)
    if (target !== marks.title) requestAnimationFrame(() => target.scrollIntoView({ block: "nearest" }));
  }
  function start(wrap) {
    load("notes").then(data => {
      const all = isObj(data) && Array.isArray(data.notes) ? data.notes : null, good = list(all).filter(valid);
      // 꼴이 어긋난 자료(노트 배열이 없다 · 있는데 쓸 수 있는 것이 하나도 없다)는 '아직 없다'가 아니라 실패다 — 다음에 다시 받는다
      if (!all || (all.length && !good.length)) { delete got.notes; failed = true; } else notes = good;
    }, () => { failed = true; }).then(() => paint(wrap));
  }
  function setView(view, arg) {
    if (view !== "notes") { away = true; return; }
    const wrap = document.getElementById("notes-wrap");
    if (!wrap) return;
    const back = away;
    away = false;
    wanted = typeof arg === "string" ? arg : "";
    if (!got.notes && !failed) start(wrap);                     // #notes에 처음 들어올 때 읽는다
    paint(wrap, back);
  }
  return { setView };
})();
