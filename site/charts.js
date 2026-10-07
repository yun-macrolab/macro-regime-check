"use strict";
// 사이트 그래프 — data/charts.json의 그래프 하나(ChartSpec, 형태는 scripts/render_charts.py 머리말)를 <figure>로 그린다.
// 외부 라이브러리 없음. 글자는 textContent로만 넣는다(자료를 HTML로 해석하지 않게). 색은 site/dashboard.css의 CSS 변수(--ch-*).
// 툴팁은 보조 — 모든 값은 "표로 보기"에도 있다. 키보드: 그래프에 초점 → ←/→ 이동, Home/End, Esc 닫기.
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const PAD = { top: 10, right: 68, bottom: 22, left: 40 };   // right: 끝 값 글자 자리, bottom: 연도 눈금
  const SERIES = ["var(--ch-1)", "var(--ch-2)", "var(--ch-3)"];  // 분류색은 이 순서로만(돌려 쓰지 않는다)
  const DAY = 864e5;

  function svg(tag, attrs, text) {
    const n = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, String(v));
    if (text !== undefined) n.textContent = text;
    return n;
  }
  function html(tag, attrs, ...kids) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, v);
    for (const c of kids) if (c !== null && c !== undefined) n.append(c);   // 문자열은 텍스트로만 들어간다
    return n;
  }
  const iso = t => new Date(t).toISOString().slice(0, 10);
  const colorOf = (line, i) =>
    line.role === "main" ? "var(--ch-1)" : line.role === "ref" ? "var(--ch-ref)" : (SERIES[i] || "var(--ch-ref)");
  function fmt(v, unit) {
    if (v === null || v === undefined) return "—";
    const s = v.toFixed(Math.abs(v) >= 100 ? 0 : 2);
    return (Number(s) === 0 ? s.replace("-", "") : s) + unit;        // -0.001 → "0.00"(음의 0 표시 안 함)
  }
  const short = (v, unit) => String(+v.toFixed(2)) + unit;               // 임계값 글자: 10%, -0.25%p, 0%

  // 자료 검증 — 형식이 어긋난 점·선은 버린다. 남은 선이 없으면 그래프를 만들지 않는다
  function parse(spec) {
    const lines = (Array.isArray(spec.lines) ? spec.lines : []).map((l, i) => {
      const pts = (Array.isArray(l.points) ? l.points : [])
        .filter(p => Array.isArray(p) && typeof p[0] === "string" && /^\d{4}-\d{2}-\d{2}$/.test(p[0]) &&
          (p[1] === null || Number.isFinite(p[1])))
        .map(p => [Date.parse(p[0] + "T00:00:00Z"), p[1]])
        .filter(p => Number.isFinite(p[0]));
      return { key: String(l.key), label: String(l.label), role: l.role, color: colorOf(l, i), pts };
    }).filter(l => l.pts.some(p => p[1] !== null));
    if (!lines.length) throw new Error("그릴 자료 없음");
    return lines;
  }

  function lastValid(pts) {
    for (let i = pts.length - 1; i >= 0; i--) if (pts[i][1] !== null) return pts[i];
    return null;
  }
  function onOrBefore(pts, t) {
    let lo = 0, hi = pts.length - 1, ans = null;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (pts[mid][0] <= t) { ans = pts[mid]; lo = mid + 1; } else hi = mid - 1;
    }
    return ans;
  }

  // 눈금 간격: 1·2·2.5·5×10^k 중 눈금 수가 maxN 이하가 되는 가장 촘촘한 것.
  // 이웃 간격 비가 2 이하라 maxN이 5면 눈금이 3개 아래로 떨어지지 않는다
  function niceTicks(lo, hi, maxN) {
    const count = st => Math.floor(hi / st + 1e-9) - Math.ceil(lo / st - 1e-9) + 1;
    let step = null, mag = Math.pow(10, Math.floor(Math.log10(hi - lo)) - 2);
    // 범위가 0·무한이거나 간격을 못 정하면(자료가 오염된 경우) 눈금 없이 그린다 — 탭이 멈추지 않게
    const none = { ticks: [], decimals: 0 };
    if (!(hi > lo) || !Number.isFinite(hi - lo) || !(mag > 0) || !Number.isFinite(mag)) return none;
    for (let i = 0; step === null && i < 40; i++, mag *= 10)
      for (const m of [1, 2, 2.5, 5]) if (count(m * mag) <= maxN) { step = m * mag; break; }
    if (step === null) return none;
    const decimals = (String(+step.toPrecision(3)).split(".")[1] || "").length;
    const ticks = [];
    for (let k = Math.ceil(lo / step - 1e-9); k * step <= hi + step * 1e-9; k++) ticks.push(k * step);
    return { ticks, decimals };
  }

  function domain(lines, spec) {
    let lo = Infinity, hi = -Infinity, t0 = Infinity, t1 = -Infinity;
    for (const l of lines) for (const [t, v] of l.pts) {
      t0 = Math.min(t0, t); t1 = Math.max(t1, t);
      if (v !== null) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
    }
    if (Number.isFinite(spec.threshold)) { lo = Math.min(lo, spec.threshold); hi = Math.max(hi, spec.threshold); }
    if (!(hi > lo)) { lo -= 1; hi += 1; }
    const pad = (hi - lo) * 0.08;
    return { lo: lo - pad, hi: hi + pad, t0, t1: t1 > t0 ? t1 : t0 + DAY };
  }

  function draw(st) {
    const width = Math.max(240, Math.floor(st.plot.clientWidth || 600)), height = st.height;
    const { lo, hi, t0, t1 } = st.dom;
    const L = PAD.left, R = width - PAD.right, T = PAD.top, B = height - PAD.bottom;
    const X = t => L + (t - t0) / (t1 - t0) * (R - L), Y = v => T + (hi - v) / (hi - lo) * (B - T);
    st.X = X; st.Y = Y; st.L = L; st.R = R; st.T = T; st.B = B; st.width = width;
    const el = st.svg;
    el.replaceChildren();
    el.setAttribute("viewBox", `0 0 ${width} ${height}`);
    el.setAttribute("width", width);
    el.setAttribute("height", height);

    const { ticks, decimals } = niceTicks(lo, hi, Math.max(3, Math.min(6, Math.floor((B - T) / 23))));
    for (const v of ticks) {
      el.append(svg("line", { class: "ch-grid", x1: L, x2: R, y1: Y(v), y2: Y(v) }));
      el.append(svg("text", { class: "ch-tick", x: L - 6, y: Y(v) + 4, "text-anchor": "end" }, v.toFixed(decimals)));
    }
    // 가로 눈금: 해가 바뀌는 곳. 기간이 짧으면(약 1년 이하) 달이 바뀌는 곳 — 1월은 연도로 적고, 글자가 겹치면 건너뛴다
    const xTick = (t, label) => {
      const x = X(t);
      el.append(svg("line", { class: "ch-grid", x1: x, x2: x, y1: B, y2: B + 4 }));
      if (label) el.append(svg("text", { class: "ch-tick", x, y: height - 5, "text-anchor": "middle" }, label));
    };
    const d0 = new Date(t0);
    if (t1 - t0 > 400 * DAY) {
      for (let y = d0.getUTCFullYear() + 1; y <= new Date(t1).getUTCFullYear(); y++) xTick(Date.UTC(y, 0, 1), String(y));
    } else {
      const starts = [];
      for (let k = 1; k <= 14 && Date.UTC(d0.getUTCFullYear(), d0.getUTCMonth() + k, 1) <= t1; k++)
        starts.push(new Date(Date.UTC(d0.getUTCFullYear(), d0.getUTCMonth() + k, 1)));
      const every = Math.max(1, Math.ceil(starts.length * 40 / Math.max(1, R - L)));
      const jan = starts.findIndex(d => d.getUTCMonth() === 0), phase = jan < 0 ? 0 : jan % every;   // 건너뛰어도 1월(연도)은 남게
      starts.forEach((d, i) => xTick(d.getTime(), i % every !== phase ? null
        : d.getUTCMonth() === 0 ? String(d.getUTCFullYear()) : `${d.getUTCMonth() + 1}월`));
      // 기간이 한 달 안이면 달 경계가 없다 — 첫 날짜를 한 번 적는다
      if (!starts.length) el.append(svg("text", { class: "ch-tick", x: L, y: height - 5, "text-anchor": "start" },
        `${d0.getUTCMonth() + 1}/${d0.getUTCDate()}`));
    }
    const th = st.spec.threshold;
    if (st.spec.zero && lo < 0 && hi > 0 && th !== 0)
      el.append(svg("line", { class: "ch-zero", x1: L, x2: R, y1: Y(0), y2: Y(0) }));
    if (Number.isFinite(th)) el.append(svg("line", { class: "ch-th", x1: L, x2: R, y1: Y(th), y2: Y(th) }));

    for (const l of st.lines) {
      let d = "", pen = false;
      for (const [t, v] of l.pts) {
        if (v === null) { pen = false; continue; }
        d += (pen ? "L" : "M") + X(t).toFixed(1) + " " + Y(v).toFixed(1);
        pen = true;
      }
      const path = svg("path", { class: "ch-line", d, pathLength: 1 });   // pathLength: 처음 볼 때 선을 그려 넣는 움직임용
      path.style.stroke = l.color;
      el.append(path);
    }
    // 끝 점 + 끝 값(오른쪽 여백). 글자가 겹치면 참고 선부터 생략 — 범례·툴팁·표가 대신한다
    const placed = [];
    const ends = st.lines.map(l => ({ l, p: lastValid(l.pts) })).filter(e => e.p)
      .sort((a, b) => (a.l.role === "ref") - (b.l.role === "ref"));
    for (const e of ends) {
      const dot = svg("circle", { class: "ch-dot", cx: X(e.p[0]), cy: Y(e.p[1]), r: 4 });
      dot.style.fill = e.l.color;
      el.append(dot);
      const y = Y(e.p[1]);
      if (placed.some(py => Math.abs(py - y) < 17)) continue;
      placed.push(y);
      // 최근 값 — 선 색으로 칠한 상자에 검은 글자(단말기 방식). 참고 선은 테두리만
      const label = fmt(e.p[1], st.unit), ref = e.l.role === "ref" ? " ref" : "";
      const box = svg("rect", { class: "ch-end-box" + ref, x: R + 5, y: y - 8, width: label.length * 7 + 8, height: 16 });
      box.style.fill = e.l.color;
      el.append(box, svg("text", { class: "ch-end" + ref, x: R + 9, y: y + 4 }, label));
    }

    if (Number.isFinite(th)) {                           // 임계값 글자는 선 위에(바탕색 테두리로 선을 가린다)
      const ly = Y(th) - 5 < T + 10 ? Y(th) + 13 : Y(th) - 5;
      el.append(svg("text", { class: "ch-th-label", x: L + 4, y: ly }, "기준 " + short(th, st.unit)));
    }
    st.cross = svg("line", { class: "ch-cross", x1: 0, x2: 0, y1: T, y2: B, visibility: "hidden" });
    el.append(st.cross);
    st.focus = st.lines.map(l => {
      const c = svg("circle", { class: "ch-dot", r: 4, visibility: "hidden" });
      c.style.fill = l.color;
      el.append(c);
      return c;
    });
    if (st.idx !== null) show(st, st.idx);
  }

  function show(st, i) {
    if (!st.X) return;                                   // 아직 한 번도 그리지 않았다(폭 0)
    st.idx = i;
    st.last = i;
    const t = st.times[i], x = st.X(t), dotYs = [];
    st.cross.setAttribute("x1", x);
    st.cross.setAttribute("x2", x);
    st.cross.setAttribute("visibility", "visible");
    const rows = st.lines.map((l, j) => {
      const p = onOrBefore(l.pts, t), dot = st.focus[j];
      if (!p || p[1] === null) {
        dot.setAttribute("visibility", "hidden");
        return html("div", { class: "ch-tip-row" }, keyOf(l), html("strong", {}, "—"), l.label);
      }
      dot.setAttribute("cx", st.X(p[0]));
      dot.setAttribute("cy", st.Y(p[1]));
      dot.setAttribute("visibility", "visible");
      dotYs.push(st.Y(p[1]));
      return html("div", { class: "ch-tip-row" }, keyOf(l), html("strong", {}, fmt(p[1], st.unit)), l.label,
        p[0] !== t ? html("span", { class: "ch-tip-asof" }, ` (${iso(p[0])})`) : null);
    });
    st.tip.replaceChildren(html("div", { class: "ch-tip-date" }, iso(t)), ...rows);
    st.tip.hidden = false;
    const w = st.tip.offsetWidth, h = st.tip.offsetHeight;
    let left = x + 12, top = st.T;
    if (left + w > st.width) left = x - 12 - w;
    if (left < 0) {             // 양옆 어디에도 안 들어가면(좁은 화면) 가운데에 두고, 점들이 적은 쪽(위/아래)으로
      left = Math.max(0, Math.min(x - w / 2, st.width - w));
      const avg = dotYs.length ? dotYs.reduce((a, b) => a + b, 0) / dotYs.length : st.B;
      top = avg < (st.T + st.B) / 2 ? Math.max(st.T, st.B - h) : st.T;
    }
    st.tip.style.left = left + "px";
    st.tip.style.top = top + "px";
  }

  function hide(st) {
    st.idx = null;
    st.tip.hidden = true;
    if (st.cross) st.cross.setAttribute("visibility", "hidden");
    for (const d of st.focus || []) d.setAttribute("visibility", "hidden");
  }

  function keyOf(l) {
    const k = html("span", { class: "ch-key", "aria-hidden": "true" });
    k.style.background = l.color;
    return k;
  }

  function nearest(st, clientX) {
    const r = st.svg.getBoundingClientRect(), x = clientX - r.left;
    const t = st.dom.t0 + (x - st.L) / (st.R - st.L) * (st.dom.t1 - st.dom.t0);
    let lo = 0, hi = st.times.length - 1;
    while (hi - lo > 1) {
      const mid = (lo + hi) >> 1;
      if (st.times[mid] <= t) lo = mid; else hi = mid;
    }
    return Math.abs(st.times[hi] - t) < Math.abs(st.times[lo] - t) ? hi : lo;
  }

  function noticeBlock(notices) {
    const list = Array.isArray(notices) ? notices.filter(n => typeof n === "string" && n) : [];
    return list.length ? html("div", { class: "notices" }, ...list.map(n => html("p", {}, n))) : null;
  }

  function tableView(lines, unit) {
    const box = html("div", { class: "ch-scroll" });
    const det = html("details", { class: "ch-table" }, html("summary", {}, "표로 보기"), box);
    det.addEventListener("toggle", () => {            // 열 때 한 번만 만든다
      if (!det.open || box.childElementCount) return;
      const maps = lines.map(l => new Map(l.pts));
      const times = [...new Set(lines.flatMap(l => l.pts.map(p => p[0])))].sort((a, b) => b - a);
      const head = html("tr", {}, html("th", { scope: "col" }, "날짜"),
        ...lines.map(l => html("th", { scope: "col" }, unit ? `${l.label} (${unit})` : l.label)));
      const body = times.map(t => html("tr", {}, html("td", {}, iso(t)), ...maps.map(m => {
        const v = m.get(t);
        return html("td", {}, v === undefined ? "" : v === null ? "—" : v.toFixed(3));
      })));
      box.append(html("table", {}, html("thead", {}, head), html("tbody", {}, ...body)));
    });
    return det;
  }

  function lineChart(spec, opts) {
    const o = opts || {};
    const lines = parse(spec);
    const unit = typeof spec.unit === "string" ? spec.unit : "";
    const title = String(spec.title || "");
    const el = svg("svg", { role: "img", tabindex: "0" });
    const summary = lines.map(l => {
      const p = lastValid(l.pts);
      return `${l.label} ${fmt(p[1], unit)}(${iso(p[0])})`;
    }).join(", ");
    el.setAttribute("aria-label", `${title}. 최근 ${summary}` +
      (Number.isFinite(spec.threshold) ? `. 기준 ${short(spec.threshold, unit)}` : ""));
    const tip = html("div", { class: "ch-tip", "aria-hidden": "true" });
    tip.hidden = true;
    const plot = html("div", { class: "ch-plot" }, el, tip);
    const legend = lines.length > 1 ? html("div", { class: "ch-legend" }, ...lines.map(l =>
      html("span", {}, keyOf(l), l.role === "ref" ? `${l.label} (참고)` : l.label))) : null;
    const fig = html("figure", { class: "ch" },
      o.caption ? html("figcaption", { class: "ch-title" }, title) : null, legend, plot,
      spec.note ? html("p", { class: "ch-note muted" }, String(spec.note)) : null,
      spec.source_note ? html("p", { class: "ch-note ch-source muted" }, String(spec.source_note)) : null,
      // 참조금리 고지(SOFR) — 카드 안 그래프는 카드가 같은 고지를 싣으므로 opts.notices === false로 생략
      o.notices !== false ? noticeBlock(spec.notices) : null, tableView(lines, unit));

    const st = { spec, unit, lines, svg: el, tip, plot, height: o.height || 150, idx: null, last: null, focus: [],
                 fromPointer: false,
                 dom: domain(lines, spec),
                 times: [...new Set(lines.flatMap(l => l.pts.map(p => p[0])))].sort((a, b) => a - b) };
    // 터치: 손가락을 떼면 pointerleave가 오지만 찍은 날짜는 남긴다(다음 탭에서 바뀌고, 다른 곳을 누르면(blur) 닫힌다).
    // 탭이 만든 초점(focus)은 마지막 날짜로 되돌리지 않는다 — 키보드로 들어온 초점만 최신 날짜에서 시작
    el.addEventListener("pointerdown", ev => { st.fromPointer = true; show(st, nearest(st, ev.clientX)); });
    el.addEventListener("pointermove", ev => {
      if (ev.pointerType !== "touch" || ev.buttons) show(st, nearest(st, ev.clientX));
    });
    el.addEventListener("pointerleave", ev => { if (ev.pointerType !== "touch") hide(st); });
    el.addEventListener("focus", () => {
      if (!st.fromPointer && st.idx === null) show(st, st.times.length - 1);
      st.fromPointer = false;
    });
    el.addEventListener("blur", () => { st.fromPointer = false; hide(st); });
    el.addEventListener("keydown", ev => {
      const n = st.times.length, i = st.idx ?? st.last ?? n - 1;       // 마우스가 나간 뒤에도 마지막으로 본 날짜에서 이어서
      const next = { ArrowLeft: i - 1, ArrowRight: i + 1, Home: 0, End: n - 1 }[ev.key];
      if (ev.key === "Escape") { hide(st); return; }
      if (next === undefined) return;
      ev.preventDefault();
      show(st, Math.min(n - 1, Math.max(0, next)));
    });
    // 처음 화면에 들어올 때 한 번 선을 그려 넣는다(움직임을 껐으면 생략 — index.html이 html[data-motion]에 적어 둔다). 끝나면 표식을 떼어 다시 그릴 때 반복하지 않는다
    if ("IntersectionObserver" in window && document.documentElement.dataset.motion !== "off") {
      fig.classList.add("ch-fresh");
      const io = new IntersectionObserver(entries => {
        if (!entries.some(e => e.isIntersecting)) return;
        io.disconnect();
        fig.classList.add("ch-seen");
        setTimeout(() => fig.classList.remove("ch-fresh", "ch-seen"), 1400);
      }, { threshold: .25 });
      io.observe(fig);
    }
    let lastW = 0;
    const redraw = () => {
      const w = Math.floor(plot.clientWidth);
      if (w && w !== lastW) { lastW = w; draw(st); }
    };
    if ("ResizeObserver" in window) new ResizeObserver(redraw).observe(plot);
    else { requestAnimationFrame(redraw); window.addEventListener("resize", redraw); }
    return fig;
  }

  window.MacroCharts = Object.freeze({ lineChart });
})();
