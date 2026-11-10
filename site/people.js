/* 연준 인물 페이지 — 자료는 people-data.js(window.PEOPLE_DATA)가 먼저 싣고, 이 파일은 그리기만 한다 */
const DATA = window.PEOPLE_DATA || {};
const MAP = DATA.map || { w: 960, h: 600, paths: [] };
/* 위치 눈금(stance_now)이 가리키는 때 — 자료의 stance_label(예: '10월 말'). 위치를 고칠 때 자료에서 함께 고친다(기준일 asof와 따로 —
   위치를 고치지 않고 asof만 옮긴 날이 있다). 없으면 '지금' */
const NOW_LBL = typeof DATA.stance_label === "string" && DATA.stance_label.trim() ? DATA.stance_label.trim() : "지금";
if (!Array.isArray(DATA.people) || !DATA.people.length) {
  (document.getElementById("file") || document.body).replaceChildren(document.createTextNode("자료 파일(people-data.js)을 읽지 못했다 — 새로 고침하거나 저장소의 site/people-data.js를 본다."));
  throw new Error("people-data.js 없음");
}

/* ───────── 도구 ───────── */
const NS = "http://www.w3.org/2000/svg";
const $ = id => document.getElementById(id);
function el(tag, attrs, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false || /^on/i.test(k)) continue;   // on* 속성은 받지 않는다
    if (k === "class") n.className = v; else if (k === "text") n.textContent = v; else n.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat()) if (c !== null && c !== undefined && c !== false) n.append(c.nodeType ? c : String(c));
  return n;
}
function sv(tag, attrs, ...kids) {
  const n = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs || {})) if (v !== null && v !== undefined && !/^on/i.test(k)) n.setAttribute(k, v);   // on* 속성은 받지 않는다
  for (const c of kids.flat()) if (c !== null && c !== undefined) n.append(c.nodeType ? c : String(c));
  return n;
}
/* 움직임 · 단축키 — 처음 값은 기기 설정, 누른 값은 이 브라우저에만 기억(저장소가 막혀 있으면 이번 화면만) */
let MOTION = true;
try { MOTION = !window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) {}
try { const s = localStorage.getItem("motion"); if (s === "on" || s === "off") MOTION = s === "on"; } catch (e) {}
let KEYS_ON = true;
try { KEYS_ON = localStorage.getItem("keys") !== "off"; } catch (e) {}

const people = DATA.people || [];
const byKey = Object.create(null);
people.forEach((p, i) => { p._i = i; byKey[p.key] = p; });
const hashKey = () => { try { return decodeURIComponent(location.hash.slice(1)); } catch (e) { return ""; } };
const SEAL = n => "ABCDEFGHIJKL"[n - 1] || "?";
/* 지구의 주 단위 근사 설명(자료의 approx — 나뉜 주를 통째로 넣은 곳) — 표의 줄 · 지도 표지에 마우스를 올리면 보인다 */
const approxOf = d => (typeof d.approx === "string" && d.approx.trim() ? "주 단위 근사: " + d.approx.trim() : null);
const DIST = Object.assign(Object.create(null), Object.fromEntries((DATA.districts || []).map(d => [d.n, d])));
const STATE_D = Object.create(null);
for (const d of DATA.districts || []) for (const s of d.states || []) STATE_D[s] = d.n;
const TONE = { 1: "a", 2: "b", 3: "c", 4: "a", 5: "d", 6: "b", 7: "c", 8: "e", 9: "a", 10: "b", 11: "c", 12: "d" };
const CAMP = { "매파": "hawk", "중도": "mid", "비둘기": "dove", "스윙": "swing", "미상": "unk" };
const CAMP_ORDER = ["매파", "중도", "스윙", "비둘기", "미상"];
const campCls = p => CAMP[p.camp] || "unk";
const campVar = p => `var(--${campCls(p)})`;
const KIND = { school: "학교", academia: "학계", company: "회사", government: "정부", fed: "연준", other: "기타" };
const sur = p => String(p.name_ko || p.key).trim().split(/\s+/).pop() || p.key;
const fmtS = v => v === null || v === undefined ? "—" : (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(1);
const md = d => (d || "").slice(5);
const SIDE = side => /인상/.test(side) ? { cls: "up", mark: "▲", word: "인상" } : /인하/.test(side) ? { cls: "down", mark: "▼", word: "인하" } : { cls: "text", mark: "◆", word: "문구" };
/* 도시 약호 — 이 페이지가 붙인 이름표(공항 약호를 닮게), 사실 자료 아님 */
const CODES = {
  "Stanford, CA": "STN", "Cambridge, MA": "CAM", "New York, NY": "NYC", "Washington, DC": "WDC", "Atlanta, GA": "ATL", "Seoul, South Korea": "SEL",
  "Ann Arbor, MI": "ARB", "Akron, OH": "AKR", "Ballwin, MO": "BWN", "Basel, Switzerland": "BSL", "Bemidji, MN": "BJI", "Berkeley, CA": "BRK",
  "Bloomington, IN": "BLM", "Boston, MA": "BOS", "Charlottesville, VA": "CVL", "Chicago, IL": "CHI", "Cleveland, OH": "CLE", "Council Grove, KS": "CGV",
  "Dallas, TX": "DAL", "Davidson, NC": "DVD", "East Lansing, MI": "ELN", "Evanston, IL": "EVN", "Kansas City, MO": "KCM", "Lawrence, KS": "LWR",
  "Lexington, KY": "LEX", "Lincoln, NE": "LNK", "London, United Kingdom": "LON", "Madison, WI": "MSN", "Milledgeville, GA": "MLV", "Minneapolis, MN": "MSP",
  "Nebraska, United States": "NEB", "New Haven, CT": "NHV", "Newport Beach, CA": "NPB", "Notre Dame, IN": "NDM", "Omaha, NE": "OMA",
  "Oxford, United Kingdom": "OXF", "Philadelphia, PA": "PHL", "Poughkeepsie, NY": "POU", "Princeton, NJ": "PRN", "Pullman, WA": "PUL",
  "Redondo Beach, CA": "RDB", "Richmond, VA": "RIC", "Sacramento, CA": "SAC", "San Francisco, CA": "SFO", "Scotland, United Kingdom": "SCO",
  "St. Louis, MO": "STL", "Stamford, CT": "STM", "Swarthmore, PA": "SWA", "Syracuse, NY": "SYR", "Topeka, KS": "TOP", "Urbana, IL": "URB",
  "Versailles, KY": "VRS", "(도시 미상), Japan": "JPN", "(도시 미상), Senegal": "SEN"
};
function code(place) {
  if (!place) return "???";
  if (CODES[place]) return CODES[place];
  const city = place.split(",")[0].replace(/[^A-Za-z ]/g, "").trim();
  const w = city.split(/\s+/).filter(Boolean);
  return (w.length > 1 ? w.map(x => x[0]).join("") + w[w.length - 1].slice(1, 3) : city).slice(0, 3).toUpperCase() || "???";
}
/* 2026년에 지금 자리에 앉은 사람의 시작일(지금 자리 note에 적힌 날짜) — 그 앞 회의는 '위원 아님' */
function memberSince(p) {
  const j = (p.journey || []).find(x => x.now && x.from === "2026");
  if (!j) return null;
  const m = /(\d{4})-(\d{2})(?:-(\d{2}))?/.exec(j.note || "");
  return m ? `${m[1]}-${m[2]}-${m[3] || "01"}` : null;
}
/* 명단 밖 위원: 반대표 기록에만 나오는 사람(마이런). 05-22 워시 취임 무렵 퇴임(events_2026) → 그 뒤 회의는 위원 아님 */
const OFFROSTER = { miran: { name: "마이런", full: "스티븐 마이런(전 이사)", until: "2026-05-22" } };
const meetings = DATA.meetings_2026 || [];
function cellOf(p, m) {
  const chair = m.chair === p.key;
  const since = memberSince(p);
  if (since && m.date < since) return { t: "before", chair };
  if (m.vote == null) return { t: p.voter_2026 ? "plan" : "none", chair };
  const d = (m.dissents || []).find(x => x.key === p.key);
  if (d) return { t: "dissent", side: d.side, chair };
  if (!p.voter_2026) return { t: "none", chair };
  return { t: "with", chair };
}
const nameOfKey = k => byKey[k] ? sur(byKey[k]) : (OFFROSTER[k] || {}).name || k;
/* 다음 회의까지 — 한국 날짜 기준(관측실 시계와 같은 기준). 미국 날짜와 하루 다를 수 있다 */
function todayKST() {
  const now = new Date(), k = new Date(now.getTime() + (now.getTimezoneOffset() + 540) * 60000), pad = n => String(n).padStart(2, "0");
  return `${k.getFullYear()}-${pad(k.getMonth() + 1)}-${pad(k.getDate())}`;
}
function nextMeeting() {
  const today = todayKST();
  const m = meetings.filter(x => (x.date || "") >= today).sort((a, b) => a.date < b.date ? -1 : 1)[0];
  if (!m) return null;
  const start = m.first_day || m.date;
  const days = Math.round((Date.parse(start + "T00:00:00Z") - Date.parse(today + "T00:00:00Z")) / 864e5);
  return { m, start, days, label: days > 0 ? `D-${days}` : "회의 중" };
}
/* 결정일(한국 날짜)이 지났는데 표가 아직 자료에 없는 회의 — 사람이 결과를 옮기기 전(FOMC 뒤 1주 안)이라 '예정'이라 하지 않는다 */
const waitsResult = m => m.vote == null && (m.date || "") < todayKST();
const WAITS_TITLE = "날짜는 지났고 결과를 아직 옮기지 않음";
const decOf = m => (m.decision === "예정" && waitsResult(m) ? "결과 미반영" : m.decision);

/* ───────── 투영 (지도와 같은 앨버스) ───────── */
const P = MAP.proj, R = Math.PI / 180;
const n_ = (Math.sin(P.p1 * R) + Math.sin(P.p2 * R)) / 2;
const C_ = Math.cos(P.p1 * R) ** 2 + 2 * n_ * Math.sin(P.p1 * R);
const rho0 = Math.sqrt(C_ - 2 * n_ * Math.sin(P.lat0 * R)) / n_;
function project(lat, lon) {
  if (lat == null || lon == null) return null;
  if (lat < 24 || lat > 50 || lon < -125.5 || lon > -66) return null;   /* 본토 48개 주만 */
  const th = n_ * (lon - P.lon0) * R, rho = Math.sqrt(C_ - 2 * n_ * Math.sin(lat * R)) / n_;
  return [P.ox + P.s * rho * Math.sin(th), P.oy - P.s * (rho0 - rho * Math.cos(th))];
}

/* ───────── 지도 바탕 (두 지도가 같이 쓴다) ───────── */
function buildBase(svg, tintFn) {
  svg.setAttribute("viewBox", `0 0 ${MAP.w} ${MAP.h}`);
  if (tintFn) {
    const pat = sv("pattern", { id: "hatch-unk", width: 6, height: 6, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" },
      sv("rect", { width: 6, height: 6, fill: "#1a1a1a" }), sv("rect", { width: 2, height: 6, fill: "#2e2e2e" }));
    svg.append(sv("defs", {}, pat));
  }
  const g = sv("g", { class: "states" });
  for (const [sid, d] of Object.entries(MAP.paths)) {
    const dn = STATE_D[sid];
    const cls = tintFn ? tintFn(dn) : "t-" + (TONE[dn] || "a");
    g.append(sv("path", { d, class: "st " + cls, "data-d": dn || "" }));
  }
  svg.append(g);
  return g;
}
function svgK(svg, vbw) { const w = svg.getBoundingClientRect().width; return (vbw || MAP.w) / (w > 10 ? w : MAP.w); }
/* 글자 상자 겹침을 줄이는 탐욕 배치: 세 겹의 고리(가까운 것부터) 후보 중 겹침이 가장 적은 곳. 먼 고리에 놓이면 끌어낸 선을 단다 */
function overlap(a, b) {
  const x = Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x));
  const y = Math.max(0, Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y));
  return x * y;
}
function placeLabels(items, obstacles, view) {
  const placed = [];
  for (const it of items) {
    const { cx, cy, r, w, h, k } = it;
    const g = r + 3 * k;
    const rings = it.rings || [1, 2.2, 3.6];
    let best = null, bestS = Infinity, bestRing = 0, i = 0;
    rings.forEach((m, ri) => {
      const G = g * m + (ri ? 3 * k : 0);
      [[cx + G, cy - h / 2], [cx - G - w, cy - h / 2], [cx - w / 2, cy - G - h], [cx - w / 2, cy + G],
        [cx + G * .7, cy - G * .7 - h], [cx + G * .7, cy + G * .7], [cx - G * .7 - w, cy - G * .7 - h], [cx - G * .7 - w, cy + G * .7]].forEach(([x, y]) => {
        const box = { x, y, w, h };
        let s = i * 0.5 * k * k + ri * 30 * k * k;
        for (const o of obstacles) s += overlap(box, o) * 2;
        for (const o of placed) s += overlap(box, o) * 3;
        if (view) {
          if (x < view.x) s += (view.x - x) * h * 4;
          if (x + w > view.x + view.w) s += (x + w - view.x - view.w) * h * 4;
          if (y < view.y) s += (view.y - y) * w * 4;
          if (y + h > view.y + view.h) s += (y + h - view.y - view.h) * w * 4;
        }
        if (s < bestS) { bestS = s; best = box; bestRing = ri; }
        i++;
      });
    });
    if (view && best) {
      const pad = 2 * k;
      best.x = Math.min(Math.max(best.x, view.x + pad), view.x + view.w - best.w - pad);
      best.y = Math.min(Math.max(best.y, view.y + pad), view.y + view.h - best.h - pad);
    }
    placed.push(best);
    it.box = best; it.ring = bestRing;
  }
  return placed;
}
function nearestOnBox(b, x, y) { return [Math.max(b.x, Math.min(x, b.x + b.w)), Math.max(b.y, Math.min(y, b.y + b.h))]; }

/* ───────── 노선도 ───────── */
const routeSvg = sv("svg", { id: "route-svg", role: "img", "aria-label": "걸어온 길 노선도" });
const route = { vb: { x: 0, y: 0, w: MAP.w, h: MAP.h }, mode: "fit", p: null, anim: 0, raf: 0, timer: 0, items: [] };
function buildRouteBase() {
  buildBase(routeSvg);
  route.ghosts = sv("g"); route.seals = sv("g"); route.arcs = sv("g"); route.stops = sv("g"); route.hubs = sv("g"); route.labs = sv("g");
  routeSvg.append(route.ghosts, route.seals, route.arcs, route.stops, route.hubs, route.labs);
}
function spotsOf(p) {
  const items = (p.journey || []).map((j, i) => ({ ...j, n: i + 1, xy: project(j.lat, j.lon), code: code(j.place) }));
  const spots = [];
  for (const it of items) {
    if (!it.xy) continue;
    let s = spots.find(s => Math.hypot(s.xy[0] - it.xy[0], s.xy[1] - it.xy[1]) < 6);
    if (!s) { s = { xy: it.xy, items: [], code: it.code }; spots.push(s); }
    s.items.push(it);
    it.spot = s;
  }
  spots.forEach(s => { s.now = s.items.some(x => x.now); s.guess = s.items.every(x => x.loc_guess); });
  return { items, spots };
}
function homeXY(p) {
  if (p.seat === "board") return project(DATA.board.lat, DATA.board.lon);
  const d = DIST[p.district]; return d ? project(d.lat, d.lon) : null;
}
const FULL = () => ({ x: 0, y: 0, w: MAP.w, h: MAP.h });
function fitView(pts) {
  if (!pts.length) return FULL();
  let x0 = Math.min(...pts.map(q => q[0])), x1 = Math.max(...pts.map(q => q[0]));
  let y0 = Math.min(...pts.map(q => q[1])), y1 = Math.max(...pts.map(q => q[1]));
  const pad = 56, ar = MAP.w / MAP.h;
  let w = Math.max(x1 - x0 + pad * 2, 460), h = Math.max(y1 - y0 + pad * 2, 460 / ar);
  if (w / h > ar) h = w / ar; else w = h * ar;
  if (w >= MAP.w || h >= MAP.h) return FULL();
  let x = (x0 + x1) / 2 - w / 2, y = (y0 + y1) / 2 - h / 2;
  x = Math.max(0, Math.min(MAP.w - w, x)); y = Math.max(0, Math.min(MAP.h - h, y));
  return { x, y, w, h };
}
function setVB(svg, v) { svg.setAttribute("viewBox", `${v.x.toFixed(1)} ${v.y.toFixed(1)} ${v.w.toFixed(1)} ${v.h.toFixed(1)}`); }
/* 지도가 옮겨 가는 것(이전 사람의 보기 → 이 사람의 보기) */
function animateVB(target, from) {
  cancelAnimationFrame(route.anim);
  route.vb = target;
  if (!MOTION || !from) { setVB(routeSvg, target); return; }
  const t0 = performance.now(), dur = 650;
  setVB(routeSvg, from);
  const step = now => {
    const t = Math.min(1, (now - t0) / dur), e = t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    setVB(routeSvg, { x: from.x + (target.x - from.x) * e, y: from.y + (target.y - from.y) * e, w: from.w + (target.w - from.w) * e, h: from.h + (target.h - from.h) * e });
    if (t < 1) route.anim = requestAnimationFrame(step); else setVB(routeSvg, target);
  };
  route.anim = requestAnimationFrame(step);
}
function arcD(a, b, bend) {
  const [x0, y0] = a, [x1, y1] = b, dx = x1 - x0, dy = y1 - y0, len = Math.hypot(dx, dy) || 1;
  let nx = -dy / len, ny = dx / len;
  if (ny > 0) { nx = -nx; ny = -ny; }                        /* 북쪽(위)으로 휘게 */
  const cx = (x0 + x1) / 2 + nx * bend, cy = (y0 + y1) / 2 + ny * bend;
  return { d: `M${x0.toFixed(1)},${y0.toFixed(1)} Q${cx.toFixed(1)},${cy.toFixed(1)} ${x1.toFixed(1)},${y1.toFixed(1)}`, cx, cy, len };
}
/* 19명 겹침: 도시마다 거쳐 간 사람 수(3명 이상) — 걸어온 길의 장소 글자로 센 것 */
let HUBS = null;
function hubList() {
  if (HUBS) return HUBS;
  const m = {};
  people.forEach(q => (q.journey || []).forEach(j => {
    const xy = project(j.lat, j.lon); if (!xy || !j.place) return;
    (m[j.place] = m[j.place] || { place: j.place, xy, who: new Set() }).who.add(q.key);
  }));
  HUBS = Object.values(m).filter(h => h.who.size >= 3).sort((a, b) => b.who.size - a.who.size);
  return HUBS;
}
function drawGhosts(p, k) {
  people.forEach(q => {
    if (q.key === p.key) return;
    const seq = spotsOf(q).items.filter(x => x.xy);
    for (let i = 1; i < seq.length; i++) {
      const a = seq[i - 1].xy, b = seq[i].xy;
      if (Math.hypot(a[0] - b[0], a[1] - b[1]) < 6) continue;
      const A = arcD(a, b, 0);
      const bend = Math.min(90, A.len * 0.18) * (i % 2 ? 1 : -1);
      route.ghosts.append(sv("path", { class: "ghost", d: arcD(a, b, bend).d, "stroke-width": (0.95 * k).toFixed(2), style: `stroke:${campVar(q)}` },
        sv("title", {}, `${q.name_ko} (${q.camp || "미상"})`)));
    }
  });
}
function placeHubs(k, view, obstacles) {
  const boxes = [];
  const narrow = routeSvg.getBoundingClientRect().width < 480;
  for (const h of hubList()) {
    const g = sv("g", { class: "hub" });
    const nT = sv("text", { class: "n", "font-size": 11 * k }, `${h.who.size}명`);
    const lT = narrow ? null : sv("text", { class: "lb", "font-size": 11 * k, "stroke-width": 3 * k }, h.place.split(",")[0]);
    g.append(nT, ...(lT ? [lT] : []), sv("title", {}, `${h.place} — ${h.who.size}명이 거쳐 감: ${[...h.who].map(nameOfKey).join(", ")}`));
    route.hubs.append(g);
    const bw = nT.getBBox().width + 8 * k, bh = 15 * k, lw = lT ? lT.getBBox().width + 4 * k : 0;
    const it = { cx: h.xy[0], cy: h.xy[1], r: 5 * k, w: bw + 3 * k + lw, h: bh, k, rings: [1.6, 3, 4.6] };
    placeLabels([it], obstacles.concat(boxes), view);
    const b = it.box;
    const near = nearestOnBox({ x: b.x, y: b.y, w: bw, h: bh }, h.xy[0], h.xy[1]);
    g.prepend(sv("line", { x1: h.xy[0].toFixed(1), y1: h.xy[1].toFixed(1), x2: near[0].toFixed(1), y2: near[1].toFixed(1), "stroke-width": k }),
      sv("rect", { x: b.x.toFixed(1), y: b.y.toFixed(1), width: bw.toFixed(1), height: bh.toFixed(1), "stroke-width": k }));
    nT.setAttribute("x", (b.x + bw / 2).toFixed(1)); nT.setAttribute("y", (b.y + bh / 2).toFixed(1));
    if (lT) { lT.setAttribute("x", (b.x + bw + 3 * k).toFixed(1)); lT.setAttribute("y", (b.y + bh / 2).toFixed(1)); }
    boxes.push(b);
  }
  return boxes;
}
function drawRoute(p, opt) {
  opt = opt || {};
  stopTrace();
  route.p = p;
  const all = route.mode === "all";
  routeSvg.dataset.mode = route.mode;
  const { items, spots } = spotsOf(p);
  const home = homeXY(p);
  const view = route.mode === "fit" ? fitView(spots.map(s => s.xy).concat(home ? [home] : [])) : FULL();
  const k = svgK(routeSvg, view.w);
  routeSvg.querySelectorAll(".st").forEach(s => s.classList.toggle("home", p.seat !== "board" && +s.dataset.d === p.district));
  route.ghosts.replaceChildren(); route.hubs.replaceChildren();
  if (all) drawGhosts(p, k);
  /* 표지 — 노선을 그릴 때는 흐리게(40%), 노선 글자·정거장과 겹치면 감춘다. 고향 표지만 또렷하게 */
  route.seals.replaceChildren();
  const obstacles = [], sealBoxes = [];
  for (const d of DATA.districts || []) {
    const xy = project(d.lat, d.lon); if (!xy) continue;
    const isHome = p.seat !== "board" && d.n === p.district;
    const r = (isHome ? 11 : 8) * k;
    const g = sv("g", { class: "seal" + (isHome ? " home" : " dimmed"), transform: `translate(${xy[0].toFixed(1)},${xy[1].toFixed(1)})` });
    g.append(sv("circle", { r, class: "seal-ring", "stroke-width": (isHome ? 1.6 : 1) * k }), sv("text", { class: "seal-txt", "font-size": (isHome ? 11.5 : 9) * k }, SEAL(d.n)));
    const tip = approxOf(d);
    g.append(sv("title", {}, `${d.n}지구 ${d.bank_ko} — 표지 ${SEAL(d.n)}${tip ? ` (${tip})` : ""}`));
    route.seals.append(g);
    const box = { x: xy[0] - r, y: xy[1] - r, w: r * 2, h: r * 2 };
    sealBoxes.push({ g, box, isHome });
    if (isHome) obstacles.push(box);
  }
  /* 호 */
  route.arcs.replaceChildren();
  const legs = [];
  let prev = null, skipped = false;
  for (const it of items) {
    if (!it.xy) { if (prev) skipped = true; continue; }
    if (prev && prev.spot !== it.spot) legs.push({ a: prev.spot, b: it.spot, skip: skipped, n: it.n });
    if (prev && prev.spot === it.spot && skipped) legs.push({ a: prev.spot, b: it.spot, skip: true, loop: true, n: it.n });
    prev = it; skipped = false;
  }
  const pairCount = {};
  legs.forEach(L => {
    if (L.loop) return;
    const key = [L.a.code + L.a.xy[0].toFixed(0), L.b.code + L.b.xy[0].toFixed(0)].sort().join("|");
    const c = pairCount[key] = (pairCount[key] || 0) + 1;
    const len = Math.hypot(L.b.xy[0] - L.a.xy[0], L.b.xy[1] - L.a.xy[1]) || 1;
    const bend = Math.min(140, len * 0.22 + 10 * k) * (c % 2 ? 1 : -1) * (1 + 0.5 * Math.floor((c - 1) / 2));
    const A = arcD(L.a.xy, L.b.xy, bend);
    const [x0, y0] = L.a.xy, [x1, y1] = L.b.xy, cx = A.cx, cy = A.cy;
    L.path = sv("path", { d: A.d, class: "arc" + (L.skip ? " skip" : ""), "stroke-width": 1.7 * k, style: `--dash:${(5 * k).toFixed(1)} ${(4 * k).toFixed(1)}` });
    route.arcs.append(L.path);
    /* 방향 표시: 곡선 위 0.58 지점의 꺾쇠 */
    const t = 0.58, mx = (1 - t) * (1 - t) * x0 + 2 * (1 - t) * t * cx + t * t * x1, my = (1 - t) * (1 - t) * y0 + 2 * (1 - t) * t * cy + t * t * y1;
    const tx = 2 * (1 - t) * (cx - x0) + 2 * t * (x1 - cx), ty = 2 * (1 - t) * (cy - y0) + 2 * t * (y1 - cy), tl = Math.hypot(tx, ty) || 1;
    const ux = tx / tl, uy = ty / tl, s = 4.2 * k;
    L.chev = sv("path", { class: "chev", d: `M${(mx + ux * s).toFixed(1)},${(my + uy * s).toFixed(1)} L${(mx - ux * s - uy * s * .8).toFixed(1)},${(my - uy * s + ux * s * .8).toFixed(1)} L${(mx - ux * s + uy * s * .8).toFixed(1)},${(my - uy * s - ux * s * .8).toFixed(1)}Z` });
    route.arcs.append(L.chev);
  });
  /* 정거장 */
  route.stops.replaceChildren(); route.labs.replaceChildren();
  const labelItems = [], stopBoxes = [];
  spots.forEach(s => {
    const r = (s.now ? 5.5 : 4.2) * k;
    const g = sv("g", { class: "stop", transform: `translate(${s.xy[0].toFixed(1)},${s.xy[1].toFixed(1)})` });
    s.g = g;
    if (s.now || s.guess) g.append(sv("circle", { r: r + 3.2 * k, class: "stop-ring" + (s.guess ? " guess" : ""), "stroke-width": 1.4 * k, style: `--dash:${(2.5 * k).toFixed(1)} ${(2 * k).toFixed(1)}` }));
    else g.append(sv("circle", { r: r + 3.2 * k, class: "stop-halo", "stroke-width": 1.4 * k }));
    g.append(sv("circle", { r, class: "stop-dot" + (s.now ? " now" : ""), "stroke-width": 1.2 * k }));
    g.append(sv("title", {}, s.items.map(x => `${x.n}. ${x.org_ko || x.org}`).join("\n")));
    route.stops.append(g);
    const sb = { x: s.xy[0] - r - 3 * k, y: s.xy[1] - r - 3 * k, w: (r + 3 * k) * 2, h: (r + 3 * k) * 2 };
    obstacles.push(sb); stopBoxes.push(sb);
    const t = sv("text", { class: "stop-lab" + (s.now ? " now" : ""), "font-size": 11.5 * k, "stroke-width": 3 * k },
      s.code, sv("tspan", { class: "n", "font-size": 10 * k, dx: 3 * k }, s.items.map(x => x.n).join("·")));
    route.labs.append(t);
    s.t = t;
    labelItems.push({ s, t, cx: s.xy[0], cy: s.xy[1], r: r + (s.now || s.guess ? 3 * k : 0), k });
  });
  /* 겹침 보기에서는 사람 수 상자가 먼저 자리를 잡는다 */
  const hubBoxes = all ? placeHubs(k, view, obstacles) : [];
  obstacles.push(...hubBoxes);
  labelItems.forEach(it => { const b = it.t.getBBox(); it.w = b.width || 30 * k; it.h = (b.height || 14 * k) * 0.92; });
  labelItems.sort((a, b) => (b.s.now - a.s.now) || (b.s.items.length - a.s.items.length));
  placeLabels(labelItems, obstacles, view);
  labelItems.forEach(it => {
    const b = it.box;
    it.t.setAttribute("x", b.x.toFixed(1));
    it.t.setAttribute("y", (b.y + it.h * 0.8).toFixed(1));
    const near = nearestOnBox(b, it.cx, it.cy);
    if (it.ring > 0 && Math.hypot(near[0] - it.cx, near[1] - it.cy) > it.r + 4 * k)
      route.labs.prepend(sv("line", { class: "stop-lead", x1: it.cx.toFixed(1), y1: it.cy.toFixed(1), x2: near[0].toFixed(1), y2: near[1].toFixed(1), "stroke-width": .9 * k }));
  });
  /* 고향 표지 이름 */
  const homeBoxes = [];
  if (home) {
    const d = p.seat !== "board" ? DIST[p.district] : null;
    const t = sv("text", { class: "seal-lab k", "font-size": 11 * k, "stroke-width": 3 * k }, d ? `${SEAL(d.n)} · ${d.bank_ko}` : "연준 이사회");
    route.labs.append(t);
    const b = t.getBBox();
    const it = { cx: home[0], cy: home[1], r: (d ? 12 : 10) * k, w: b.width, h: b.height * .92, k };
    placeLabels([it], obstacles.concat(labelItems.map(x => x.box)), view);
    t.setAttribute("x", it.box.x.toFixed(1)); t.setAttribute("y", (it.box.y + it.h * .8).toFixed(1));
    homeBoxes.push(it.box);
  }
  const blockers = labelItems.map(x => x.box).concat(stopBoxes, hubBoxes, homeBoxes);
  sealBoxes.forEach(({ g, box, isHome }) => { if (!isHome && blockers.some(b => overlap(box, b) > 0)) g.style.display = "none"; });
  route.items = items;
  if (opt.fly && MOTION && opt.from) animateVB(view, opt.from); else { cancelAnimationFrame(route.anim); route.vb = view; setVB(routeSvg, view); }
  capRest();
  if (opt.trace && MOTION && !all) startTrace(items, legs, opt.fly ? 220 : 0);
  return { items, spots };
}

/* 노선이 한 구간씩 그려진다 — 구간마다 운항 기록 줄이 그 정거장을 부른다. 움직임을 끄면 처음부터 완성된 모습 */
function stopTrace() {
  cancelAnimationFrame(route.raf); clearTimeout(route.timer);
  route.raf = 0; route.timer = 0;
}
function startTrace(items, legs, delay) {
  const byN = {};
  legs.forEach(L => { if (!L.loop) byN[L.n] = L; });
  const steps = items.map(it => ({ it, L: byN[it.n] || null }));
  if (!steps.length) return;
  const per = Math.max(140, Math.min(420, 1700 / steps.length));
  steps.forEach(s => { s.dur = s.L ? (s.L.skip ? per * .8 : per) : per * .55; });
  legs.forEach(L => {
    if (L.loop || !L.path) return;
    L.chev.style.opacity = "0";
    if (L.skip) L.path.style.opacity = "0";
    else { L.len = L.path.getTotalLength(); L.path.style.strokeDasharray = `${L.len}`; L.path.style.strokeDashoffset = `${L.len}`; }
  });
  const total = delay + steps.reduce((a, s) => a + s.dur, 0);
  const done = s => { const L = s.L; if (!L || !L.path) return; L.path.style.opacity = ""; L.chev.style.opacity = ""; if (!L.skip) { L.path.style.strokeDasharray = ""; L.path.style.strokeDashoffset = ""; } };
  const finish = () => { stopTrace(); steps.forEach(done); hlStop(null, false); capRest(); };
  let t0 = null, idx = -1;
  const ease = f => 1 - Math.pow(1 - f, 2);
  const frame = ts => {
    if (t0 === null) t0 = ts;
    const t = ts - t0 - delay;
    if (t < 0) { route.raf = requestAnimationFrame(frame); return; }
    let acc = 0, i = 0;
    for (; i < steps.length; i++) { if (t < acc + steps[i].dur) break; acc += steps[i].dur; }
    for (let j = Math.max(0, idx); j < Math.min(i, steps.length); j++) done(steps[j]);
    if (i >= steps.length) { finish(); return; }
    if (i !== idx) { idx = i; capItem(steps[i].it); hlStop(steps[i].it.n, true, true); }
    const L = steps[i].L, f = Math.min(1, (t - acc) / steps[i].dur);
    if (L && L.path) {
      if (L.skip) L.path.style.opacity = f.toFixed(2);
      else L.path.style.strokeDashoffset = String(L.len * (1 - ease(f)));
      if (f > .6) L.chev.style.opacity = "";
    }
    route.raf = requestAnimationFrame(frame);
  };
  route.raf = requestAnimationFrame(frame);
  route.timer = setTimeout(finish, total + 700);   /* 탭이 숨어 있어도 결국 완성된 모습으로 */
}

/* 운항 기록 한 줄 */
function yrsOf(x) { return x.from || x.to ? `${x.from || "?"}${x.to && x.to !== x.from ? "–" + x.to : (x.now ? "–현재" : (x.to ? "" : "–?"))}` : "연도 미상"; }
function capItem(x, rest) {
  const cap = $("flog"); if (!cap || !x) return;
  const total = route.items.length;
  cap.replaceChildren(
    el("span", { class: "n" + (x.now ? " now" : ""), text: String(x.n).padStart(2, "0") }),
    el("div", { class: "l1" }, el("span", { class: "yr", text: yrsOf(x) }), x.org_ko || x.org,
      el("span", { class: "badges" }, x.now ? el("span", { class: "cert nowb", text: "현재" }) : null, certBadge(x.cert), x.loc_guess ? el("span", { class: "cert guess", text: "위치 추정" }) : null)),
    el("div", { class: "l2", text: `${rest ? "지금 자리 · " : ""}${x.n}/${total} · ${KIND[x.kind] || "기타"} · ${x.place || "장소 미상"}${x.xy ? "" : " · 지도 밖"}` +
      (rest ? ` — 목록 줄에 손을 올리면 그 정거장` : "") }));
}
function capRest() {
  const its = route.items || [];
  const x = its.find(i => i.now) || its[its.length - 1];
  if (x) capItem(x, true); else { const cap = $("flog"); if (cap) cap.replaceChildren(el("span", { class: "n", text: "—" }), el("div", { class: "l1", text: "걸어온 길 기록 없음" })); }
}
/* 정거장 목록 ↔ 지도: 목록 줄에 올리면 그 정거장이 밝아지고 운항 기록이 그곳을 부른다 */
function hlStop(n, on, quiet) {
  const it = (route.items || []).find(x => x.n === n);
  document.querySelectorAll(".leg").forEach(l => l.classList.toggle("hl", !!on && +l.dataset.n === n));
  routeSvg.querySelectorAll(".stop.hl, .stop-lab.hl").forEach(x => x.classList.remove("hl"));
  if (on && it && it.spot && it.spot.g) { it.spot.g.classList.add("hl"); it.spot.t.classList.add("hl"); }
  if (!quiet) { if (on && it) capItem(it); else capRest(); }
}

/* ───────── 연대표 ───────── */
const ASOF_Y = (() => { const m = /(\d{4})-(\d{2})/.exec(DATA.asof || ""); return m ? +m[1] + (+m[2] - .5) / 12 : 2026.8; })();
function textPx(s) { let w = 0; for (const ch of String(s)) w += /[ᄀ-ᇿ㄰-㆏가-힣]/.test(ch) ? 12.4 : /[A-Z]/.test(ch) ? 8 : 6.6; return w; }
function ribbon(items, availPx) {
  const wrap = el("div", { class: "ribbon-wrap" });
  const yr = v => v == null ? null : +v;
  const dated = items.filter(x => yr(x.from) != null || yr(x.to) != null);
  const undated = items.filter(x => yr(x.from) == null && yr(x.to) == null);
  wrap.append(el("h4", {}, "연대표", el("span", { text: `연도가 있는 ${dated.length}곳 · 막대 길이 = 기록된 기간 · 흐려지는 끝 = 시작·끝 연도 미상` })));
  if (!dated.length) {
    wrap.append(el("p", { class: "small-note", text: "연도가 적힌 기록이 없어 연대표를 그리지 않았다." }));
  } else {
    const bars = dated.map(x => {
      const f = yr(x.from), t = yr(x.to);
      let s, e, os = false, oe = false;
      if (f != null) { s = f; e = t != null ? Math.max(t + 1, f + 1) : (x.now ? ASOF_Y : f + 2.5); oe = t == null && !x.now; }
      else { e = t + 1; s = t - 1.5; os = true; }
      if (x.now) e = Math.max(e, ASOF_Y); else if (e > ASOF_Y) e = Math.max(ASOF_Y, s + 0.5);
      return { x, s, e, os, oe, name: x.org_ko || x.org };
    });
    const y0 = Math.floor(Math.min(...bars.map(b => b.s)) - 1), y1 = Math.ceil(Math.max(ASOF_Y + 0.4, ...bars.map(b => b.e)));
    const span = y1 - y0, minPx = 15;
    const totalPx = Math.max(availPx || 0, span * minPx), ppy = totalPx / span;
    /* 이름이 막대 안에 들어가지 않으면 오른쪽(끝에 걸리면 왼쪽) 밖에 쓰고, 그 자리까지 같은 줄을 비워 둔다 */
    bars.forEach(b => {
      const need = 26 + textPx(b.name) + 8, w = (b.e - b.s) * ppy;
      b.mode = w >= need ? "in" : "out";
      b.lw = textPx(b.name) + 10;
      b.as = b.s; b.ae = b.e;
      if (b.mode === "out") {
        if (b.e * ppy + b.lw <= (y1 - 0.2) * ppy) { b.side = "r"; b.ae = b.e + b.lw / ppy; }
        else { b.side = "l"; b.as = b.s - b.lw / ppy; }
      }
    });
    const lanes = [];
    bars.slice().sort((a, b) => a.as - b.as || a.x.n - b.x.n).forEach(b => {
      let li = lanes.findIndex(end => end <= b.as + 0.01);
      if (li < 0) { li = lanes.length; lanes.push(0); }
      lanes[li] = b.ae + 4 / ppy; b.lane = li;
    });
    const scroll = el("div", { class: "ribbon-scroll", tabindex: "0", role: "group", "aria-label": "연대표 — 가로로 밀어 볼 수 있음" });
    const rb = el("div", { class: "ribbon", style: `min-width:${Math.round(span * minPx)}px;height:${lanes.length * 30 + 34}px` });
    const X = v => ((v - y0) / span * 100).toFixed(3) + "%";
    const gstep = span <= 12 ? 1 : 5, lstep = span <= 12 ? 1 : span < 30 ? 5 : 10;
    /* 축 글자: 양 끝에서 잘리지 않게(끝 16px 안의 해는 쓰지 않음), '지금' 이름표가 놓이는 쪽의 해는 비운다.
       이름표는 오른쪽에 들어갈 자리(약 92px)가 없으면 선의 왼쪽에 쓴다 */
    const NOW_W = 92, flip = (y1 - ASOF_Y) * ppy < NOW_W;
    for (let y = Math.ceil(y0 / gstep) * gstep; y <= y1; y += gstep) {
      rb.append(el("i", { class: "rb-grid" + (y % lstep === 0 ? " dec" : ""), style: `left:${X(y)}` }));
      const dx = (y - ASOF_Y) * ppy, edge = (y - y0) * ppy < 16 || (y1 - y) * ppy < 16;
      const underNow = flip ? dx > -NOW_W && dx < 18 : dx > -18 && dx < NOW_W;
      if (y % lstep === 0 && !edge && !underNow) rb.append(el("span", { class: "rb-tick", style: `left:${X(y)}`, text: String(y) }));
    }
    rb.append(el("i", { class: "rb-now" + (flip ? " flip" : ""), style: `left:${X(ASOF_Y)}` }, el("span", { text: "지금 " + (DATA.asof || "").slice(0, 7) })));
    bars.forEach(b => {
      const x = b.x, top = b.lane * 30 + 6;
      const yrs = (x.from || "?") + (x.to && x.to !== x.from ? "–" + x.to : (x.now ? "–" : ""));
      rb.append(el("div", { class: `bar k-${KIND[x.kind] ? x.kind : "other"}${b.os ? " open-start" : ""}${b.oe ? " open-end" : ""}${x.now ? " now-bar" : ""}${b.mode === "out" ? " slim" : ""}`,
        style: `left:${X(b.s)};width:max(22px, calc(${((b.e - b.s) / span * 100).toFixed(3)}% - 2px));top:${top}px`,
        title: `${x.n}. ${b.name} · ${yrs}${b.oe ? " (끝 연도 미상)" : ""}${b.os ? " (시작 연도 미상)" : ""}` },
        el("b", { text: String(x.n) }), b.mode === "in" ? el("span", { text: b.name }) : null));
      if (b.mode === "out") {
        rb.append(b.side === "r"
          ? el("span", { class: "bar-lab", "aria-hidden": "true", style: `left:calc(${X(b.e)} + ${b.e - b.s < 22 / ppy ? Math.ceil(22 - (b.e - b.s) * ppy) + 4 : 4}px);top:${top}px`, text: b.name })
          : el("span", { class: "bar-lab l", "aria-hidden": "true", style: `right:calc(${(100 - (b.s - y0) / span * 100).toFixed(3)}% + 4px);top:${top}px`, text: b.name }));
      }
    });
    scroll.append(rb);
    wrap.append(scroll);
  }
  if (undated.length) {
    wrap.append(el("div", { class: "ribbon-unk" }, el("span", { text: "연도 미상:" }),
      ...undated.map(x => el("span", { class: "chip" }, el("b", { text: String(x.n) }), x.org_ko || x.org))));
  }
  const used = [...new Set(items.map(x => KIND[x.kind] ? x.kind : "other"))];
  wrap.append(el("div", { class: "kinds" }, ...["school", "academia", "company", "government", "fed", "other"].filter(k => used.includes(k)).map(k =>
    el("span", {}, el("i", { class: `k-${k}`, style: kindSwatch(k) }), KIND[k]))));
  return wrap;
}
function kindSwatch(k) {
  return { fed: "background:#2a2011;border-color:#d3a45f", government: "background:#0d2418;border-color:#36d07f", company: "background:#2a1a05;border-color:#ff9e1b",
    school: "background:#1a1a1a;border-color:#c9c4b8", academia: "background:repeating-linear-gradient(135deg,#2a2a2a 0 2px,#121212 2px 4px);border-color:#9d978a",
    other: "background:#121212;border-color:#6a6a6a;border-style:dashed" }[k];
}

/* ───────── 작은 부품: 기울기 눈금 · 반대표 · 투표 등 ───────── */
function meterSvg(p, w, h) {
  const pad = 4, X = v => pad + (v + 2) / 4 * (w - 2 * pad), cy = h / 2;
  const s = sv("svg", { class: "meter", width: w, height: h, viewBox: `0 0 ${w} ${h}`, "aria-hidden": "true" });
  const a = p.stance_start_2026, b = p.stance_now;
  if (typeof b !== "number") { s.append(sv("text", { x: w / 2, y: cy + 3.5, "text-anchor": "middle" }, "판단 불가")); return s; }
  s.append(sv("line", { class: "trk", x1: pad, x2: w - pad, y1: cy, y2: cy }));
  for (let v = -2; v <= 2; v++) s.append(sv("line", { class: "tk" + (v === 0 ? " tk0" : ""), x1: X(v), x2: X(v), y1: cy - (v === 0 ? 5 : 3), y2: cy + (v === 0 ? 5 : 3) }));
  const col = campVar(p), unk = campCls(p) === "unk";
  if (typeof a === "number" && a !== b) {
    s.append(sv("line", { class: "path", x1: X(a), x2: X(b), y1: cy, y2: cy, style: `stroke:${col}` }));
    s.append(sv("circle", { class: "from", cx: X(a), cy, r: 2.6, style: "stroke:#a8a8a8" }));
  }
  s.append(sv("circle", { cx: X(b), cy, r: 3.6, style: unk ? "fill:#000;stroke:#a8a8a8;stroke-width:1.3;stroke-dasharray:1.6 1.2" : `fill:${col}` }));
  return s;
}
function pipsNode(p) {
  const ds = p.dissents_2026 || [];
  if (!ds.length) return el("span", { class: "pips", "aria-hidden": "true" }, el("span", { class: "none", text: "—" }));
  return el("span", { class: "pips", "aria-hidden": "true", title: "2026 반대표: " + ds.map(d => `${md(d.date)} ${SIDE(d.side).word}`).join(" · ") },
    ...ds.map(d => { const s = SIDE(d.side); return el("span", { class: s.cls, text: s.mark }); }));
}
function lampsNode(p) {
  return el("span", { class: "lamps", "aria-hidden": "true" },
    el("span", { class: "lamp" + (p.voter_2026 ? " on" : ""), text: "26", title: p.voter_2026 ? "2026 투표" : "2026 투표 없음" }),
    el("span", { class: "lamp" + (p.voter_2027 ? " on" : ""), text: "27", title: p.voter_2027 ? "2027 투표" : "2027 투표 없음" }));
}

/* ───────── 파일 ───────── */
function certBadge(c) {
  if (!c) return null;
  if (c === "1차") return el("span", { class: "cert c1", title: "1차 자료(제3자 사본·검색 조각 포함)", text: "1차" });
  if (c === "2차") return el("span", { class: "cert c2", title: "2차 보도", text: "2차" });
  if (/사전/.test(c)) return el("span", { class: "cert pk", title: "사전 지식 — 확인 안 됨", text: "사전 지식" });
  return el("span", { class: "cert", text: c });
}
function headlineNode(text) {
  const p = el("p");
  const parts = String(text || "").split("→");
  parts.forEach((t, i) => { if (i) p.append(el("span", { class: "arrow", "aria-hidden": "true", text: "→" }), el("span", { class: "sr", text: "그다음" })); p.append(t.trim()); });
  return p;
}
function fileTab(p) {
  const tab = $("file-tab"); tab.replaceChildren();
  tab.append(`파일 ${String(p._i + 1).padStart(2, "0")}/${people.length}`,
    el("span", { text: p.seat === "board" ? "워싱턴 이사회" : `표지 ${SEAL(p.district)} · 제${p.district}지구` }));
}
function renderFile(p, ropt) {
  fileTab(p);
  const f = $("file"); f.replaceChildren();
  f.setAttribute("aria-label", `${p.name_ko} 파일`);
  const camp = campCls(p);
  /* 머리: 표지 · 신분 · 신분 칸(관찰자 라벨 표지 · 위치 · 투표) · 올해의 흐름 */
  const seal = p.seat === "board"
    ? el("div", { class: "seal-big board", "aria-hidden": "true" }, el("b", { text: "이사" }), el("small", { text: "DC" }))
    : el("div", { class: "seal-big", "aria-hidden": "true" }, el("b", { text: SEAL(p.district) }), el("small", { text: `${p.district}지구` }));
  const idblock = el("div", { class: "idblock" },
    el("p", { class: "kicker", text: `${p.seat === "board" ? "워싱턴 이사회" : "제" + p.district + "지구"} · ${p.role_short || ""}` }),
    el("div", { class: "name-row" }, el("h2", { class: "file-name", id: "file-title", text: p.name_ko }), el("span", { class: "file-en", lang: "en", text: p.name_en || "" })),
    el("p", { class: "bgline" }, el("span", { class: "bgtype", title: "배경 분류", text: p.bg_type || "배경 미상" }), p.bg_line || ""),
    (p.phrases || [])[0] ? el("p", { class: "sig" }, el("q", { lang: "en", text: p.phrases[0].text }), el("span", { text: "  " + (p.phrases[0].date || "") })) : null);
  const ds = p.dissents_2026 || [];
  const pos = v => ((v + 2) / 4 * 100).toFixed(1) + "%";
  const num = typeof p.stance_now === "number";
  const idcard = el("div", { class: "idcard" },
    el("div", { class: "badge-row" }, el("span", { class: "badge-k", text: "관찰자 라벨" }),
      el("span", { class: "badge " + camp, title: "언론·관찰자 평판을 줄인 것 — 계산값 아님" + ((p.camp_src || []).length ? " · 라벨 출처: " + p.camp_src.map(s => `${s.outlet} ${s.date}`).join(" · ") : p.camp_cert ? ` · 라벨 출처: ${p.camp_cert}(미확인)` : ""), text: p.camp || "미상" }),
      el("span", { class: "badge-note", text: "평판 요약 · 계산값 아님" })),
    el("div", { class: "lean" }, el("span", { class: "lean-k", text: "위치 · 운영자 해석 (−2 비둘기 … +2 매파)" }),
      el("span", { class: "big", text: fmtS(p.stance_now) }),
      el("span", { class: "from", text: num ? (typeof p.stance_start_2026 === "number" ? `연초 ${fmtS(p.stance_start_2026)}` : "") : "판단 불가 — 2026 금리 발언 없음" })),
    num ? el("div", {}, el("div", { class: "track", "aria-hidden": "true" },
      ...[-2, -1, 0, 1, 2].map(v => el("span", { style: `left:${pos(v)}` })),
      typeof p.stance_start_2026 === "number" ? el("i", { class: "then", style: `left:${pos(p.stance_start_2026)}` }) : null,
      el("i", { class: "now", style: `left:${pos(p.stance_now)}` })),
      el("div", { class: "track-lab", "aria-hidden": "true" }, el("span", { text: "−2" }), el("span", { text: "빈 원 연초 · 찬 점 지금" }), el("span", { text: "+2" }))) : null,
    el("div", { class: "vrow" }, el("span", { class: "lamp" + (p.voter_2026 ? " on" : ""), text: p.voter_2026 ? "2026 투표" : "2026 투표 없음" }),
      el("span", { class: "lamp" + (p.voter_2027 ? " on" : ""), text: p.voter_2027 ? "2027 투표" : "2027 투표 없음" })),
    el("p", { class: "diss" }, ds.length
      ? [`반대 ${ds.length}회 — `, ...ds.flatMap((d, i) => { const s = SIDE(d.side); return [i ? " · " : "", el("span", { class: s.cls, text: s.mark }), ` ${md(d.date)} ${d.side}`]; })]
      : (p.voter_2026 ? "2026 반대 기록 없음" : "2026 투표권 없음 — 토론·점도표만")),
    p.voter_note ? el("p", { class: "vnote", text: p.voter_note }) : null);
  const head = el("header", { class: "file-head", id: "file-head" }, seal, idblock, idcard,
    el("div", { class: "headline" }, el("span", { class: "k", text: "올해의 흐름 · 운영자 해석" }), headlineNode(p.shift_note || "기록 없음")));
  f.append(head);
  /* 기준선 — 순서는 스펙트럼 축과 같다(비둘기 → 평소 → 매파). 넓은 화면은 가로 세 칸, 좁은 화면은 위에서 아래로 쌓은 띠 */
  const b = p.baseline || {};
  const li = arr => (arr && arr.length ? arr : ["자료 부족"]).map(x => el("li", { text: x }));
  const col = (cls, glyph, title, q, arr) => el("div", { class: "bcol " + cls },
    el("span", { class: "glyph", "aria-hidden": "true", text: glyph }),
    el("div", { class: "bbody" }, el("h4", {}, title, el("small", { text: q })), el("ul", {}, li(arr))));
  const base = el("section", { id: "sec-base", "aria-labelledby": "h-base" },
    el("div", { class: "sec-h" }, el("h3", { id: "h-base" }, el("span", { class: "no", text: "02" }), "기준선", el("span", { class: "tag", text: "운영자 정리 · " + reviewKo(reviewOf(p)) })),
      el("p", {}, el("span", { class: "wide", text: "새 발언은 주로 이 세 칸에 견준다 — 가운데 ‘평소’ 안이면 뉴스가 아니다 · 순서는 축과 같다: 비둘기 → 평소 → 매파 · "
        + "이 칸 밖의 운영자 정리(지금 입장 · 뉴스 아님 목록 · 반대표 기록)에 견준 발언은 그 줄을 ‘견준 항목’에 그대로 싣는다" }), el("span", { class: "narrow", text: "‘평소’ 안이면 뉴스 아님 · 위에서부터 비둘기 → 평소 → 매파(축 순서)" }))),
    el("div", { class: "base-axis", "aria-hidden": "true" }, el("span", { class: "d", text: "◀ 비둘기 쪽" }), el("span", { class: "u", text: "이 사람의 평소" }), el("span", { class: "h", text: "매파 쪽 ▶" })),
    el("div", { class: "base-grid" },
      col("dove", "▼", "비둘기 쪽 놀랄 일", "나오면 비둘기 쪽 뉴스", b.dove_surprise),
      col("usual", "■", "평소", "늘 하는 말 — 새 소식 아님", b.usual),
      col("hawk", "▲", "매파 쪽 놀랄 일", "나오면 매파 쪽 뉴스", b.hawk_surprise)),
    p.watch ? el("div", { class: "watch" }, el("b", { text: "다음 확인" }), el("p", { text: p.watch + " (운영자 정리 — 예측 아님)" })) : null,
    p.stance_basis ? el("p", { class: "basis" }, el("b", { text: "위치 근거(운영자 해석): " }), p.stance_basis) : null);
  f.append(base);
  /* 새 발언 — 기준선 바로 뒤. 자료(data/people_remarks.json)가 늦게 오면 loadRemarks()가 이 칸만 다시 채운다 */
  const news = el("section", { id: "sec-new", class: "rm-sec", "aria-labelledby": "h-new" });
  fillRemarks(news, p);
  f.append(news);
  /* 노선도 */
  const routeSec = el("section", { id: "sec-route", "aria-labelledby": "h-route" });
  const seg = el("div", { class: "seg", role: "group", "aria-label": "노선도 보기" });
  [["fit", "맞춤"], ["full", "전체 지도"], ["all", "19명 겹침"]].forEach(([m, label]) => {
    const btn = el("button", { type: "button", "data-mode": m, "aria-pressed": route.mode === m ? "true" : "false", text: label });
    btn.addEventListener("click", () => {
      if (route.mode === m) return;
      const from = { ...route.vb };
      route.mode = m;
      seg.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", x.dataset.mode === m ? "true" : "false"));
      drawRoute(p, { fly: true, from });
      routeTexts(p);
    });
    seg.append(btn);
  });
  const fig = el("figure", { class: "route-fig" });
  const box = el("div", { class: "mapbox" }); box.append(routeSvg);
  fig.append(box, el("div", { class: "flog", id: "flog", role: "status", "aria-live": "off" }));
  routeSec.append(el("div", { class: "sec-h" }, el("h3", { id: "h-route" }, el("span", { class: "no", text: "03" }), "노선도"),
    el("p", { id: "route-sub" }), el("div", { class: "tools" }, seg)));
  const grid = el("div", { class: "route-grid" }, fig);
  routeSec.append(grid);
  f.append(routeSec);
  fig.append(el("div", { class: "route-legend", id: "route-legend" }));
  const { items } = drawRoute(p, ropt);
  const off = items.filter(x => !x.xy);
  if (off.length) fig.append(el("div", { class: "offmap" }, el("span", { text: "지도 밖:" }),
    ...off.map(x => el("span", { class: "chip" }, el("b", { text: String(x.n) }), `${x.code} ${x.org_ko || x.org}`, x.loc_guess ? " · 위치 추정" : ""))));
  fig.append(el("p", { class: "small-note", text: "도시 약호는 이 페이지가 붙인 이름표다. 좌표는 캠퍼스·본사 도시의 대략값." }));
  routeTexts(p);
  /* 정거장 목록 */
  const ol = el("ol", { class: "manifest", "aria-label": "정거장 목록" });
  items.forEach(x => {
    const li = el("li", { class: "leg" + (x.now ? " now" : ""), "data-n": x.n },
      el("span", { class: "leg-n", text: String(x.n).padStart(2, "0") }),
      el("span", { class: "leg-code" + (x.xy ? "" : " off"), text: x.code, title: x.xy ? x.place : `${x.place} (지도 밖)` }),
      el("div", { class: "leg-body" },
        el("div", { class: "leg-yrs" + (x.from || x.to ? "" : " unk"), text: yrsOf(x) }),
        el("div", { class: "leg-org" }, x.org_ko || x.org, el("span", { class: "kind", text: KIND[x.kind] || "기타" }),
          el("span", { class: "badges" }, x.now ? el("span", { class: "cert nowb", text: "현재" }) : null, certBadge(x.cert), x.loc_guess ? el("span", { class: "cert guess", text: "위치 추정" }) : null)),
        el("div", { class: "leg-meta" }, x.org && x.org !== x.org_ko ? el("span", { class: "en", text: x.org }) : null, x.org && x.org !== x.org_ko ? " · " : "",
          [x.place, x.note].filter(Boolean).join(" · "))));
    li.addEventListener("mouseenter", () => hlStop(x.n, true));
    li.addEventListener("mouseleave", () => hlStop(x.n, false));
    ol.append(li);
  });
  grid.append(ol);
  const cs = getComputedStyle(f);
  routeSec.append(ribbon(items, f.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) - 2));
  /* 말·기록 */
  const st = p.style || [], ph = p.phrases || [];
  const talk = el("div", {},
    el("h4", { class: "sub", text: "말버릇" }),
    el("ul", { class: "styles" }, ...(st.length ? st : ["기록 없음"]).map(x => el("li", { text: x }))),
    el("h4", { class: "sub" }, "자주 나온 말", el("span", { text: "프로필에 옮겨진 문구 그대로" })),
    ph.length ? el("div", { class: "quotes" }, ...ph.map(q => el("blockquote", { class: "quote", lang: "en" }, el("p", { text: q.text }), el("footer", { text: q.date || "" }))))
      : el("p", { class: "dim", text: "기록된 문구 없음 — 이 사람에게는 침묵이 기준선이다." }),
    el("p", { class: "small-note", text: "2차 보도가 옮긴 문구는 원문과 다를 수 있다." }));
  const strip = el("div", { class: "mstrip", role: "list", "aria-label": "2026 회의별 이 사람의 표" });
  meetings.forEach(m => {
    const c = cellOf(p, m);
    const label = c.t === "dissent" ? c.side : c.t === "with" ? "다수" : c.t === "before" ? "취임 전" : c.t === "plan" ? (waitsResult(m) ? "미반영" : "예정") : "–";
    const cls = c.t === "dissent" ? SIDE(c.side).cls : c.t;
    strip.append(el("div", { class: `mcell ${cls}${c.chair ? " chair" : ""}`, role: "listitem",
      title: `${m.date} ${decOf(m)}${m.vote ? " (" + m.vote + ")" : ""} — ${c.t === "dissent" ? c.side + " 쪽 반대" : c.t === "with" ? "반대 기록 없음(다수 쪽으로 봄)" : c.t === "before" ? "그때는 위원 아님" : c.t === "plan" ? (waitsResult(m) ? WAITS_TITLE : "아직 열리지 않음") : "투표권 없음"}${c.chair ? " · 의장" : ""}` },
      el("span", { class: "md", text: md(m.date) }), el("span", { class: "mv", text: label })));
  });
  const rec = p.recent || [];
  const record = el("div", {},
    el("h4", { class: "sub" }, "2026 회의", el("span", { text: p.voter_2026 ? "투표권자" : "투표권 없음 — 토론·점도표만" })),
    strip,
    el("p", { class: "mlegend", text: "다수 = 반대 기록 없음(다수 쪽으로 봄) · – = 투표권 없음 · 점선 = 아직 열리지 않았거나 결과를 아직 옮기지 않은(미반영) 회의 · 호박색 밑줄 = 그 회의 의장" }),
    el("h4", { class: "sub", text: "최근 기록" }),
    el("ul", { class: "recent" }, ...rec.map(r => el("li", {}, el("time", { text: r.date }), el("span", { text: r.text })))));
  f.append(el("section", { id: "sec-talk", "aria-labelledby": "h-talk" },
    el("div", { class: "sec-h" }, el("h3", { id: "h-talk" }, el("span", { class: "no", text: "04" }), "말하는 방식과 올해 기록")),
    el("div", { class: "two" }, talk, record)));
  /* 출처 */
  const src = p.sources || [];
  f.append(el("div", { class: "sources" },
    p.conf ? el("p", {}, el("b", { text: "확신 수준: " }), p.conf) : null,
    el("ul", {}, ...src.map(s => el("li", {}, `${s.outlet || ""} · ${s.date || ""} · `, safeLink(s.url))))));
}
/* 노선도 설명 줄 · 범례 — 보기(맞춤/전체/겹침)에 따라 바뀐다 */
function routeTexts(p) {
  const items = route.items || [], off = items.filter(x => !x.xy).length;
  const sub = $("route-sub"), lg = $("route-legend");
  if (!sub || !lg) return;
  routeSvg.setAttribute("aria-label", `${p.name_ko}의 노선도: ` + items.map(x => `${x.n} ${x.org_ko || x.org}`).join(", ") + (route.mode === "all" ? " — 다른 18명의 경로를 가늘게 겹쳐 그림" : ""));
  if (route.mode === "all") {
    sub.textContent = `19명 경로 겹침 · 금색 = ${p.name_ko} · 상자 = 그 도시를 거쳐 간 사람 수(3명 이상)`;
    lg.replaceChildren(el("span", {}, el("i", { class: "lg-arc" }), sur(p)),
      ...CAMP_ORDER.filter(c => people.some(q => q.key !== p.key && q.camp === c)).map(c => el("span", {}, el("i", { class: "lg-ghost", style: `border-color:var(--${CAMP[c]})` }), c)),
      el("span", {}, el("i", { class: "lg-hub", text: "14명" }), "도시별 사람 수"), el("span", { text: "선 색 = 관찰자 라벨" }));
  } else {
    sub.textContent = `걸어온 길 ${items.length}곳 · 지도 위 ${items.length - off} · 지도 밖 ${off} — 번호는 걸어온 순서`;
    lg.replaceChildren(
      el("span", {}, el("i", { class: "lg-stop" }), "정거장(번호 = 순서)"), el("span", {}, el("i", { class: "lg-now" }), "지금 자리"),
      el("span", {}, el("i", { class: "lg-arc" }), "이동"), el("span", {}, el("i", { class: "lg-skip" }), "사이에 지도 밖 정거장"),
      el("span", {}, el("i", { class: "lg-guess" }), "위치 추정"), el("span", {}, el("i", { class: "lg-seal", text: "D" }), "연은 표지(흐리게)"));
  }
}
function safeLink(u) {
  if (typeof u !== "string" || !/^https:\/\//.test(u)) return el("span", { text: "링크 없음" });
  return el("a", { href: u, target: "_blank", rel: "noopener noreferrer", text: u.replace(/^https:\/\/(www\.)?/, "").replace(/\/$/, "") });
}

/* ───────── 새 발언 — 기준선 대비(자동 분류) ─────────
   data/people_remarks.json — 운영자 파이프라인의 결론 런이 자동 분류한 것을 게시 전용 PC가 검사해 매일 올리는 파일(scripts/people_push.py와 같은 약속).
   한 번 읽어(no-store) 다시 검사한다: 머리의 꼴이 약속과 다르면 파일 전체를 버리고, 틀린 발언은 그 발언만 뺀다.
   없거나 틀리면 '자동 발언 기록 없음' 한 줄. 글은 글자로만(el → textContent). 사람 확인 없이 올라가는 자동 분류라 그렇게 적는다 —
   판정 · 까닭 · 주제와 인용 고르기는 언어 모델(AI)이 기사를 읽고 운영자가 정리한 기준선에 견준 것이다(규칙 계산이 아니다).
   인용에는 늘 출처를 붙인다(매체 — 비면 '매체 미기재' · 요약 제목 ‘…’ — 제목은 분류할 때 언어 모델이 쓴 한 줄이라 기사 원제가 아닐 수 있다,
   둘 다 비면 '운영자가 모은 기사(매체 미기재)'), 남이 옮긴 말에는 '전언' */
const RM = {
  url: "data/people_remarks.json", schema: "people-remarks/1",
  top: ["schema", "asof", "window_from", "remarks", "held"],
  fields: ["id", "who", "said_on", "venue", "access", "topic", "quote", "vs_base", "basis", "why", "conditional", "dissent",
    "source", "title", "tags", "baseline_asof", "baseline_review"],
  venues: ["기자회견", "연설", "인터뷰", "의회 증언", "투표", "의사록", "기고", "기타"],
  access: ["직접", "전언"],
  vs: ["평소와 같음", "평소보다 매파", "평소보다 비둘기", "새 주제"],
  sides: ["인상", "인하", "동결", "문구"],
  tags: ["블랙아웃 중 — 전언 확인", "기준선 초안"],
  reviews: ["draft", "approved"],
  limits: { topic: 40, why: 120, conditional: 80, source: 40, title: 80 },
  words: 15, cut: "…", basisMax: 4, basisText: 120, pathMax: 80, perPerson: 30, maxItems: 400, windowDays: 365, show: 8, strip: 10
};
const VS_LOOK = { "평소와 같음": ["same", "■"], "평소보다 매파": ["hawk", "▲"], "평소보다 비둘기": ["dove", "▼"], "새 주제": ["new", "◆"] };
const RM_INVISIBLE = /[\p{Cc}\p{Cf}\p{Zl}\p{Zp}\p{Cs}]/u;      // 제어 · 서식(폭 없는 글자) · 줄/문단 구분 · 짝 없는 서로게이트
const RM_PATH = /^[A-Za-z_]\w*(?:\[\d{1,4}\])*(?:\.[A-Za-z_]\w*(?:\[\d{1,4}\])*)*$/;
const remarks = { state: "wait", list: [], held: 0, asof: "", from: "" };
function rmDay(v) {
  if (typeof v !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(v)) return false;
  const t = Date.parse(v + "T00:00:00Z");
  return Number.isFinite(t) && new Date(t).toISOString().slice(0, 10) === v;
}
/* 글 칸: 앞뒤 공백 · 보이지 않는 글자 · 주소("://") 없음, 글자 수(코드 포인트) 상한 */
function rmText(v, limit, need) {
  return typeof v === "string" && (!need || v.length > 0) && v === v.trim() && !v.includes("://") && !RM_INVISIBLE.test(v)
    && (limit == null || [...v].length <= limit);
}
function rmKeys(o, keys) {
  return !!o && typeof o === "object" && !Array.isArray(o) && Object.keys(o).length === keys.length && keys.every(k => Object.prototype.hasOwnProperty.call(o, k));
}
function rmQuote(q) {
  const w = q.split(/\s+/).filter(Boolean);
  return w.length <= RM.words || (w.length === RM.words + 1 && w[w.length - 1] === RM.cut);
}
function rmItem(r, from, asof) {
  if (!rmKeys(r, RM.fields) || !rmText(r.who, null, true) || !/^[a-z]+$/.test(r.who) || !byKey[r.who]) return false;
  if (!rmDay(r.said_on) || r.said_on < from || r.said_on > asof || !rmDay(r.baseline_asof)) return false;
  if (!RM.venues.includes(r.venue) || !RM.access.includes(r.access) || !RM.vs.includes(r.vs_base) || !RM.reviews.includes(r.baseline_review)) return false;
  if (typeof r.id !== "string" || !/^[0-9a-f]{12}$/.test(r.id)) return false;
  if (!Object.entries(RM.limits).every(([k, n]) => rmText(r[k], n))) return false;
  if (!rmText(r.quote) || (r.quote && !rmQuote(r.quote))) return false;
  if (!rmText(r.dissent) || (r.dissent && (!RM.sides.includes(r.dissent) || r.venue !== "투표"))) return false;
  if (!Array.isArray(r.basis) || r.basis.length < 1 || r.basis.length > RM.basisMax) return false;
  if (!r.basis.every(b => rmKeys(b, ["path", "text"]) && rmText(b.path, RM.pathMax, true) && RM_PATH.test(b.path) && rmText(b.text, RM.basisText, true))) return false;
  return Array.isArray(r.tags) && new Set(r.tags).size === r.tags.length && r.tags.every(t => RM.tags.includes(t));
}
/* 파일 → { asof, from, held, list } 또는 null(머리의 꼴이 약속과 다르다 — 파일 전체를 버린다) */
function checkRemarks(doc) {
  if (!rmKeys(doc, RM.top) || doc.schema !== RM.schema || !rmDay(doc.asof) || !rmDay(doc.window_from) || doc.window_from > doc.asof
    || !Array.isArray(doc.remarks) || doc.remarks.length > RM.maxItems || !Number.isInteger(doc.held) || doc.held < 0) return null;
  const keys = new Set(), ids = new Set(), per = Object.create(null), list = [];
  for (const r of doc.remarks) {
    const ok = rmItem(r, doc.window_from, doc.asof), k = ok ? `${r.who}|${r.said_on}|${r.venue}` : "";
    if (!ok || keys.has(k) || ids.has(r.id) || (per[r.who] || 0) >= RM.perPerson) continue;          // 틀린 · 겹친 · 넘친 발언은 그것만 뺀다
    keys.add(k); ids.add(r.id); per[r.who] = (per[r.who] || 0) + 1;
    list.push(r);
  }
  const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  list.sort((a, b) => cmp(b.said_on, a.said_on) || cmp(a.who, b.who) || cmp(a.venue, b.venue));   // 최신순, 같으면 사람 · 자리
  return { asof: doc.asof, from: doc.window_from, held: doc.held, list };
}
const reviewKo = v => (v === "approved" ? "확인함" : "초안");
/* 기준선의 확인 상태 — 사람마다(자료의 p.review), 없거나 다른 값이면 페이지 전체(DATA.review) */
function reviewOf(p) { return p && RM.reviews.includes(p.review) ? p.review : DATA.review; }
/* 고정 문구 — 사람 파일은 그 사람(r = 최신 발언 — 그 발언이 견준 기준선의 기준일), 머리 띠는 p 없이 */
function remarkLabel(r, p) {
  // 발언 칸의 기준선 표시는 그 사람의 가장 새 발언이 실제로 견준 기준선(파일에 고정된 baseline_asof·baseline_review) — 지금
  // 프로필의 확인 상태(위 기준선 칸의 꼬리표)와 다를 수 있다. 발언이 없으면 지금 프로필의 것
  const base = p ? (r ? `기준선(${r.baseline_asof} · ${reviewKo(r.baseline_review)})` : `기준선(${reviewKo(reviewOf(p))})`) : "기준선(사람마다 기준일 · 확인함/초안)";
  return `자동 분류 — 언어 모델(AI)이 기사를 읽고 운영자가 정리한 ${base}에 견준 결과입니다. 사람 확인 없이 매일 올라가며 틀릴 수 있고, 예측이 아닙니다. 인용은 발언자 본인의 말을 15단어 이내로 옮긴 것입니다.`;
}
/* 인용 · 발언의 출처 — 매체(비면 '매체 미기재') · 요약 제목. 제목(title)은 분류할 때 언어 모델이 기사를 한 줄로 줄인 것이라
   기사 원제처럼 보이지 않게 '요약 제목 ‘…’'으로 적는다. 둘 다 비면 운영자가 모은 기사라고만 */
function rmSource(r) {
  if (!r.source && !r.title) return "출처: 운영자가 모은 기사(매체 미기재)";
  return "출처: " + (r.source || "매체 미기재") + (r.title ? ` · 요약 제목 ‘${r.title}’` : "");
}
function rmHearsay(r) { return r.access === "전언" ? el("span", { class: "cert guess", title: "본인이 한 말이 아니라 남이 옮긴 것", text: "전언" }) : null; }
function vsChip(v) {
  const [cls, glyph] = VS_LOOK[v] || ["same", "■"];
  return el("span", { class: "vs " + cls }, el("span", { "aria-hidden": "true", text: glyph + " " }), v);
}
function rmWho(p) {
  const b = el("button", { type: "button", class: "rm-who", "data-key": p.key, title: `${p.name_ko} 파일 열기` }, p.name_ko);
  b.addEventListener("click", () => select(p.key, { push: true, scroll: true, focus: true }));
  return b;
}
function rmNone(text) { return el("p", { class: "rm-none", text }); }
/* 사람 파일 안의 발언 하나 — ref = 칸 머리 문구가 기준일을 말하는 발언(그 사람의 가장 새 발언). 비교는 처음 공개한 날의 기준선으로
   굳어 있어(baseline_asof) 옛 발언이 다른 기준일에 견줬으면 그 날짜를 카드에 붙인다 — 머리 문구의 새 기준선에 견준 것처럼 읽히지 않게 */
function remarkCard(r, ref) {
  const side = r.dissent ? SIDE(r.dissent) : null;
  return el("li", { class: "rm " + (VS_LOOK[r.vs_base] || ["same"])[0] },
    el("div", { class: "rm-meta" }, el("time", { text: r.said_on }), el("span", { class: "rm-venue", text: r.venue }), rmHearsay(r),
      vsChip(r.vs_base),
      side ? el("span", { class: "rm-dis " + side.cls, text: `반대표 ${side.mark} ${r.dissent}` }) : null,
      ...r.tags.map(t => el("span", { class: "cert", text: t })),
      ref && r.baseline_asof !== ref.baseline_asof
        ? el("span", { class: "cert", title: "이 발언이 견준 기준선의 기준일 — 처음 공개한 날의 것으로 고정", text: `기준선 ${r.baseline_asof}` }) : null),
    r.topic ? el("p", { class: "rm-topic", text: r.topic }) : null,
    r.quote ? el("p", { class: "rm-quote", lang: "en", text: `“${r.quote}”` }) : null,
    r.why ? el("p", { class: "rm-why", text: r.why }) : null,
    r.conditional ? el("p", { class: "rm-cond" }, el("b", { text: "조건: " }), r.conditional) : null,
    el("p", { class: "rm-basis" }, el("b", { text: "견준 항목: " }), r.basis.map(b => b.text).join(" · ")),
    r.quote || r.source || r.title ? el("p", { class: "rm-src", text: rmSource(r) }) : null);          // 인용이 있으면 출처 줄은 늘 있다
}
/* 사람 파일의 칸 — 최신순 8개, 나머지는 접어 둔다 */
function fillRemarks(sec, p) {
  const mine = remarks.state === "ok" ? remarks.list.filter(r => r.who === p.key) : [];
  const kids = [el("div", { class: "sec-h" },
    el("h3", { id: "h-new" }, "새 발언 — 기준선 대비(자동 분류)", mine.length ? el("span", { class: "tag", text: `${mine.length}건` }) : null),
    el("p", { class: "rm-label", text: remarkLabel(mine[0], p) }))];
  if (remarks.state === "wait") kids.push(rmNone("자동 발언 기록을 읽는 중…"));
  else if (remarks.state !== "ok") kids.push(rmNone("자동 발언 기록 없음"));
  else if (!mine.length) kids.push(rmNone(rmNoneFor()));
  else {
    kids.push(el("ol", { class: "rm-list" }, ...mine.slice(0, RM.show).map(r => remarkCard(r, mine[0]))));
    if (mine.length > RM.show) kids.push(el("details", { class: "rm-more" }, el("summary", { text: `나머지 ${mine.length - RM.show}건` }),
      el("ol", { class: "rm-list" }, ...mine.slice(RM.show).map(r => remarkCard(r, mine[0])))));
  }
  sec.replaceChildren(...kids);
}
/* 이 사람의 발언이 파일에 없을 때 — 파일이 담은 기간(window_from ~ asof)을 그대로 말한다. 내보내는 쪽(운영자 파이프라인)은 상한(400개 · 256KB)으로 덜어 낸
   날 window_from을 남은 가장 오래된 발언 날로 올린다 — 그날이 365일 창보다 늦으면 그 앞은 싣지 않았다고 덧붙인다 */
function rmNoneFor() {
  const span = (Date.parse(remarks.asof + "T00:00:00Z") - Date.parse(remarks.from + "T00:00:00Z")) / 864e5;
  return `${remarks.from}부터 ${remarks.asof}까지 공개된 이 사람의 자동 분류 발언 없음`
    + (span < RM.windowDays - 1 ? ` (파일 상한으로 ${remarks.from} 앞의 발언은 싣지 않음)` : "");
}
/* 페이지 머리(주의 줄 바로 뒤)의 띠 — 사람을 가리지 않고 최신 10개 */
function paintStrip() {
  let box = $("rm-strip");
  if (!box) { box = el("section", { id: "rm-strip", class: "rm-strip", "aria-labelledby": "h-rm-strip" }); $("caveat").after(box); }
  const ok = remarks.state === "ok", list = ok ? remarks.list.slice(0, RM.strip) : [];
  const head = el("div", { class: "rm-strip-h" }, el("h2", { id: "h-rm-strip", text: "최근 발언 — 기준선 대비(자동 분류)" }),
    ok ? el("span", { class: "rm-count", title: "보류 = 내보내지 않은 발언(화자 확인 대기 · 사람이 내린 것)", text: `${remarks.asof} 기준 · ${remarks.list.length}건 · 보류 ${remarks.held}` }) : null);
  const body = remarks.state === "wait" ? rmNone("자동 발언 기록을 읽는 중…") : !list.length ? rmNone("자동 발언 기록 없음")
    : el("ol", { class: "rm-rows" }, ...list.map(r => el("li", { class: "rm-row" }, el("time", { text: r.said_on }), rmWho(byKey[r.who]),
      el("span", { class: "rm-venue", text: r.venue }), rmHearsay(r), vsChip(r.vs_base), r.topic ? el("span", { class: "rm-topic", text: r.topic }) : null,
      r.quote ? el("span", { class: "rm-quote", lang: "en", text: `“${r.quote}”` }) : null,
      r.quote ? el("span", { class: "rm-src", text: rmSource(r) }) : null)));          // 인용 바로 뒤에 출처
  box.replaceChildren(head, el("p", { class: "rm-label", text: remarkLabel(null, null) }), body);
}
async function loadRemarks() {
  let got = null;
  const ctl = typeof AbortController === "function" ? new AbortController() : null;
  const timer = setTimeout(() => { if (ctl) ctl.abort(); }, 15000);
  try {
    const r = await fetch(RM.url, { cache: "no-store", signal: ctl ? ctl.signal : undefined });
    if (r && r.ok) got = checkRemarks(await r.json());
  } catch (e) { got = null; } finally { clearTimeout(timer); }
  Object.assign(remarks, got ? { state: "ok", ...got } : { state: "none", list: [] });
  /* 띠가 이미 화면 위(지나간 곳)에 있으면, 늘거나 준 만큼 스크롤을 맞춰 보던 곳(사람 주소로 연 좁은 화면이면 파일)을 그 자리에 둔다 —
     스크롤 고정(overflow-anchor)이 없는 브라우저(iOS Safari 등)에서 늦게 온 띠가 파일을 화면 밖으로 밀지 않게. 고정이 있는
     브라우저는 이미 맞춰 두어 띠 아래 끝의 화면 위치가 그대로다(차이 0 — 두 번 옮기지 않는다) */
  const box = $("rm-strip"), above = !!box && box.getBoundingClientRect().bottom <= 0, y0 = above ? box.getBoundingClientRect().bottom : 0;
  paintStrip();
  if (above) {
    const dy = $("rm-strip").getBoundingClientRect().bottom - y0;
    if (dy && typeof window.scrollBy === "function") window.scrollBy(0, dy);
  }
  const sec = $("sec-new"), p = byKey[current];
  if (sec && p) fillRemarks(sec, p);
}

/* ───────── 위원 모니터 (명단) ───────── */
function buildRail() {
  const rail = $("rail");
  rail.append(el("div", { class: "rail-head" }, el("h2", { text: "위원 모니터" }), el("span", { text: `${people.length}명 · 26/27 투표` })),
    el("div", { class: "rail-cols", "aria-hidden": "true" }, el("span", { text: "표지" }), el("span", { text: "이름 · 반대표" }), el("span", { text: "−2 … +2" }), el("span", { text: "투표" })));
  const groups = [["board", "워싱턴 이사회"], ["ny", "뉴욕 연은"], ["bank", "지구 총재"]];
  for (const [seat, label] of groups) {
    const ul = el("ul", { class: "rail-list" });
    people.filter(p => p.seat === seat).forEach(p => {
      const ds = p.dissents_2026 || [];
      const b = el("button", { class: "who", type: "button", "data-key": p.key, "aria-current": "false",
        "aria-label": `${p.name_ko}, ${p.role_short}, 관찰자 라벨 ${p.camp}, 위치 ${fmtS(p.stance_now)}${typeof p.stance_start_2026 === "number" ? "(연초 " + fmtS(p.stance_start_2026) + ")" : ""}, 2026 반대 ${ds.length}회, 2026 투표 ${p.voter_2026 ? "있음" : "없음"}, 2027 투표 ${p.voter_2027 ? "있음" : "없음"}` },
        p.seat === "board" ? el("span", { class: "mini-seal board", text: "이" }) : el("span", { class: "mini-seal", text: SEAL(p.district) }),
        el("span", { class: "who-name", text: p.name_ko }), el("span", { class: "who-sur", "aria-hidden": "true", text: sur(p) }),
        el("span", { class: "who-role", text: p.role_short || "" }), meterSvg(p, 56, 14), pipsNode(p), lampsNode(p));
      b.addEventListener("click", () => select(p.key, { push: true, scroll: true }));
      ul.append(el("li", {}, b));
    });
    rail.append(el("div", { class: "rail-group" }, el("span", { class: "rail-label", text: label }), ul));
  }
  rail.append(el("p", { class: "rail-foot" },
    el("span", { class: "wide-only" }, `눈금: 위치(운영자 해석) — 빈 원 연초, 찬 점 ${NOW_LBL}, 점 색 = 관찰자 라벨(`,
      ...CAMP_ORDER.flatMap((c, i) => [i ? " " : "", el("i", { class: "camp-sq " + CAMP[c], style: "margin:0 3px 0 2px" }), c]), "). "),
    "반대표 ", el("span", { class: "pips" }, el("span", { class: "text", text: "◆" })), " 문구 ", el("span", { class: "pips" }, el("span", { class: "up", text: "▲" })), " 인상 ",
    el("span", { class: "pips" }, el("span", { class: "down", text: "▼" })), " 인하",
    el("span", { class: "wide-only" }, " · ", el("span", { class: "lamp on", text: "26" }), " ", el("span", { class: "lamp on", text: "27" }), " = 그해 투표권")));
}

/* ───────── 지구 지도 ───────── */
const dmap = { svg: $("dmap") };
const DMAP_W = MAP.w + 60;                 /* 오른쪽(대서양) 여백 — 북동부 표지를 꺼내 놓는 자리 */
const NE = [1, 2, 3, 5];                    /* 보스턴·뉴욕·필라델피아·리치먼드: 서로 너무 가깝다 */
function presOf(d) { return byKey[d.president_key]; }
function buildDmap() {
  const svg = dmap.svg;
  buildBase(svg, dn => { const d = DIST[dn]; const p = d && presOf(d); return "tint-" + (p ? campCls(p) : "unk"); });
  svg.setAttribute("viewBox", `0 0 ${DMAP_W} ${MAP.h}`);
  dmap.seals = sv("g"); dmap.labs = sv("g");
  svg.append(dmap.seals, dmap.labs);
  drawDmapMarks();
  /* 표 */
  const t = $("dtable");
  t.append(el("thead", {}, el("tr", {}, el("th", { text: "표지" }), el("th", { text: "지구 · 연은" }), el("th", { text: "총재" }), el("th", { text: "라벨" }), el("th", { text: "투표" }))));
  const tb = el("tbody");
  for (const d of DATA.districts || []) {
    const p = presOf(d);
    const go = () => p && select(p.key, { push: true, scroll: true }), tip = approxOf(d);
    const btn = (cls, ...kids) => { const b = el("button", { type: "button", tabindex: "-1", "aria-hidden": "true", title: tip }, ...kids); b.addEventListener("click", go); return el("td", { class: cls }, b); };
    const main = el("button", { type: "button", title: tip, "aria-label": `${d.n}지구 ${d.bank_ko}, 표지 ${SEAL(d.n)}, 총재 ${p ? p.name_ko : "미상"} 파일 열기` }, el("span", { text: SEAL(d.n) }));
    main.addEventListener("click", go);
    tb.append(el("tr", { "data-key": p ? p.key : "" }, el("td", { class: "ltr" }, main),
      btn("bank", d.bank_ko.replace(" 연은", ""), el("small", {}, `${d.n}지구`, el("span", { class: "city", text: ` · ${d.city}` }))),
      btn("pres", p ? p.name_ko : "—"),
      btn("camp", el("i", { class: "camp-sq " + (p ? campCls(p) : "unk"), style: "margin-right:5px" }), p ? p.camp : "—"),
      btn("vt", p ? lampsNode(p) : "")));
  }
  t.append(tb);
  const bl = $("board-list");
  bl.append(el("h4", { text: "워싱턴 이사회 7명 — 늘 투표" }));
  const row = el("div");
  people.filter(p => p.seat === "board").forEach(p => {
    const b = el("button", { class: "namebtn", type: "button", "data-key": p.key, "aria-current": "false" }, el("i", { class: "camp-sq " + campCls(p) }), p.name_ko);
    b.addEventListener("click", () => select(p.key, { push: true, scroll: true }));
    row.append(b);
  });
  bl.append(row);
  $("tint-key").append(...CAMP_ORDER.map(c => el("span", {}, el("i", { class: "camp-sq " + CAMP[c], style: "margin-right:5px" }), c)),
    el("span", { text: "· 이사회(DC)는 지구가 아니다" }));
}
function drawDmapMarks() {
  const svg = dmap.svg, k = svgK(svg, DMAP_W);
  const compact = svg.getBoundingClientRect().width < 480;      /* 휴대폰 폭: 이름은 표에 맡기고 표지 글자만 */
  dmap.seals.replaceChildren(); dmap.labs.replaceChildren();
  const obstacles = [], labs = [];
  const sealG = (d, p) => {
    const g = sv("g", { class: "seal", "data-key": p ? p.key : "", tabindex: "0", role: "button",
      "aria-label": `${d.n}지구 ${d.bank_ko} — 표지 ${SEAL(d.n)}, 총재 ${p ? p.name_ko : "미상"}. 파일 열기` });
    const go = () => p && select(p.key, { push: true, scroll: true });
    g.addEventListener("click", go);
    g.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
    const tip = approxOf(d);
    g.append(sv("title", {}, `${SEAL(d.n)} ${d.bank_ko}${p ? " — " + p.name_ko : ""}${tip ? ` (${tip})` : ""}`));
    return g;
  };
  /* 1) 북동부 밖의 표지: 제자리 */
  for (const d of DATA.districts || []) {
    if (NE.includes(d.n)) continue;
    const xy = project(d.lat, d.lon); if (!xy) continue;
    const p = presOf(d), r = 11 * k;
    const g = sealG(d, p);
    g.append(sv("circle", { r, cx: xy[0].toFixed(1), cy: xy[1].toFixed(1), class: "seal-ring", "stroke-width": 1.3 * k }),
      sv("text", { x: xy[0].toFixed(1), y: xy[1].toFixed(1), class: "seal-txt", "font-size": 11.5 * k }, SEAL(d.n)));
    dmap.seals.append(g);
    obstacles.push({ x: xy[0] - r, y: xy[1] - r, w: 2 * r, h: 2 * r });
    if (p && !compact) {
      const t = sv("text", { class: "seal-lab", "font-size": 11 * k, "stroke-width": 3 * k }, sur(p));
      dmap.labs.append(t);
      labs.push({ t, cx: xy[0], cy: xy[1], r, k, rings: [1, 2.2] });
    }
  }
  /* 2) 북동부 표지 + 이사회: 대서양 쪽 여백에 한 줄로 꺼내고, 제자리 점에서 선으로 잇는다(위에서 아래로 실제 위도 순) */
  const dc = project(DATA.board.lat, DATA.board.lon);
  const ne = (DATA.districts || []).filter(d => NE.includes(d.n)).map(d => ({ d, xy: project(d.lat, d.lon) })).filter(x => x.xy);
  if (dc) ne.push({ board: true, xy: dc });
  ne.sort((a, b) => a.xy[1] - b.xy[1]);
  const r = 10 * k, step = (compact ? 19 : 22) * k;
  const cx = compact ? DMAP_W - 4 * k - r : 890;
  let y0 = 318;
  if (y0 + (ne.length - 1) * step + r > MAP.h - 6) y0 = MAP.h - 6 - r - (ne.length - 1) * step;
  ne.forEach((o, i) => {
    const cy = y0 + i * step;
    const lineEnd = o.board ? [cx - 14 * k, cy] : [cx - r, cy];
    const parts = [sv("line", { class: "callout-line", x1: o.xy[0].toFixed(1), y1: o.xy[1].toFixed(1), x2: lineEnd[0].toFixed(1), y2: lineEnd[1].toFixed(1), "stroke-width": k }),
      sv("circle", { class: "callout-dot", cx: o.xy[0].toFixed(1), cy: o.xy[1].toFixed(1), r: 2.4 * k })];
    if (o.board) {
      const w = 28 * k, h = 15 * k;
      const g = sv("g", { class: "board-box" }, ...parts, sv("rect", { x: (cx - 14 * k).toFixed(1), y: (cy - h / 2).toFixed(1), width: w.toFixed(1), height: h.toFixed(1), "stroke-width": k }),
        sv("text", { x: (cx - 14 * k + w / 2).toFixed(1), y: cy.toFixed(1), "font-size": 9.5 * k }, compact ? "DC" : "이사회"), sv("title", {}, "연준 이사회 — 워싱턴 DC(지구가 아니다)"));
      dmap.board = g;
      dmap.seals.append(g);
      if (!compact) dmap.seals.append(sv("text", { class: "seal-lab", x: (cx - 14 * k + w + 6 * k).toFixed(1), y: (cy + 4 * k).toFixed(1), "font-size": 11 * k, "stroke-width": 3 * k }, "7명"));
      return;
    }
    const p = presOf(o.d);
    const g = sealG(o.d, p);
    g.append(...parts, sv("circle", { r, cx: cx.toFixed(1), cy: cy.toFixed(1), class: "seal-ring", "stroke-width": 1.3 * k }),
      sv("text", { x: cx.toFixed(1), y: cy.toFixed(1), class: "seal-txt", "font-size": 11.5 * k }, SEAL(o.d.n)));
    if (p && !compact) g.append(sv("text", { class: "seal-lab", x: (cx + r + 5 * k).toFixed(1), y: (cy + 4 * k).toFixed(1), "font-size": 11 * k, "stroke-width": 3 * k }, sur(p)));
    dmap.seals.append(g);
  });
  labs.forEach(it => { const b = it.t.getBBox(); it.w = b.width; it.h = b.height * .92; });
  placeLabels(labs, obstacles, { x: 0, y: 0, w: MAP.w - 40, h: MAP.h });
  labs.forEach(it => { it.t.setAttribute("x", it.box.x.toFixed(1)); it.t.setAttribute("y", (it.box.y + it.h * .8).toFixed(1)); });
  markDmap();
}
function markDmap() {
  const p = current && byKey[current];
  dmap.svg.querySelectorAll(".seal").forEach(g => g.classList.toggle("home", !!p && g.dataset.key === p.key));
  if (dmap.board) dmap.board.classList.toggle("home", !!p && p.seat === "board");
  document.querySelectorAll("#dtable tbody tr").forEach(tr => tr.classList.toggle("cur", tr.dataset.key === current));
  document.querySelectorAll("#board-list .namebtn").forEach(b => b.setAttribute("aria-current", b.dataset.key === current ? "true" : "false"));
}

/* ───────── 스펙트럼 — 셈 칸 · 시점(지금 = NOW_LBL ↔ 1월) · 색(라벨 ↔ 투표권) ───────── */
const spec = { time: "now", color: "camp", rows: [] };
function median(vs) { const a = vs.filter(v => typeof v === "number").sort((x, y) => x - y); if (!a.length) return null; const m = a.length >> 1; return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2; }
const specPos = v => ((v + 2) / 4 * 100).toFixed(2) + "%";
function specCounts(field) {
  const vs = people.map(p => p[field]).filter(v => typeof v === "number");
  return { hawk: vs.filter(v => v > 0).length, zero: vs.filter(v => v === 0).length, dove: vs.filter(v => v < 0).length, med: median(vs), n: vs.length };
}
function buildSpectrum() {
  const box = $("spec");
  const now = specCounts("stance_now"), jan = specCounts("stance_start_2026");
  spec.cnt = { now, jan };
  const nulls = people.filter(p => typeof p.stance_now !== "number");
  /* 한 줄 요약 — 숫자는 데이터에서 센다 */
  const dir = now.med > jan.med ? "매파 쪽으로 옮겨 갔다" : now.med < jan.med ? "비둘기 쪽으로 옮겨 갔다" : "중간값은 그대로다";
  $("spec-lede").append(el("span", { class: "tag", text: "운영자 해석" }), `연초 → ${NOW_LBL}, 위원회 전체가 `, el("b", { text: dir }),
    ` — 중간값 ${fmtS(jan.med)} → ${fmtS(now.med)}, 매파 쪽 ${jan.hawk} → ${now.hawk}명, 0(유지) ${jan.zero} → ${now.zero}명, 비둘기 쪽 ${jan.dove} → ${now.dove}명.`,
    nulls.length ? ` 판단 불가 ${nulls.length}명(${nulls.map(sur).join("·")})은 셈에서 뺐다.` : "");
  const axis = el("div", { class: "spec-axis", "aria-hidden": "true" }, el("span"),
    el("div", { class: "ax", id: "spec-ax" }, el("span", { class: "lt", text: "◀ 비둘기" }), el("span", { class: "rt", text: "매파 ▶" }), el("span", { class: "mt", id: "spec-mt" }),
      ...[-2, -1, 0, 1, 2].map(v => el("span", { style: `left:${specPos(v)}`, text: fmtS(v).replace(".0", "") }))), el("span"));
  box.append(axis);
  people.filter(p => typeof p.stance_now === "number").forEach(p => {
    const r = { p };
    r.ln = el("i", { class: "ln" }); r.s0 = el("i", { class: "s0" }); r.s1 = el("i", { class: "s1" }); r.mdn = el("i", { class: "mdn" }); r.val = el("span", { class: "spec-val" });
    r.row = el("button", { class: "spec-row", type: "button", "data-key": p.key, "aria-current": "false" },
      el("span", { class: "spec-name" }, p.seat === "board" ? el("span", { class: "mini-seal board", text: "이" }) : el("span", { class: "mini-seal", text: SEAL(p.district) }),
        sur(p), p.voter_2026 ? el("em", { text: "26" }) : null),
      el("span", { class: "spec-track" }, ...[-2, -1, 0, 1, 2].map(v => el("i", { class: "g" + (v === 0 ? " z" : ""), style: `left:${specPos(v)}` })), r.mdn, r.ln, r.s0, r.s1),
      r.val);
    r.row.addEventListener("click", () => select(p.key, { push: true, scroll: true }));
    spec.rows.push(r);
  });
  if (nulls.length) {
    const n = $("spec-null");
    n.append(el("span", { text: "판단 불가(2026 금리 발언 없음):" }));
    nulls.forEach(p => { const b = el("button", { class: "namebtn", type: "button", text: p.name_ko }); b.addEventListener("click", () => select(p.key, { push: true, scroll: true })); n.append(b); });
  }
  const sl = $("scale-labels");
  const labels = (DATA.stance_scale || {}).labels || {};
  Object.keys(labels).map(Number).sort((a, b) => b - a).forEach(v => sl.append(el("li", {}, el("b", { text: fmtS(v).replace(".0", "") }), labels[String(v)])));
  sl.append(el("li", { text: "근거: " + ((DATA.stance_scale || {}).basis || "") + " · 라벨: " + (DATA.camp_note || "") }));
  $("t-now").textContent = NOW_LBL;                                          // 시점 단추의 이름도 자료에서(껍데기의 글은 '지금')
  const setT = t => { if (spec.time === t) return; spec.time = t; $("t-now").setAttribute("aria-pressed", t === "now" ? "true" : "false"); $("t-jan").setAttribute("aria-pressed", t === "jan" ? "true" : "false"); paintSpec(true); };
  const setC = c => { if (spec.color === c) return; spec.color = c; $("c-camp").setAttribute("aria-pressed", c === "camp" ? "true" : "false"); $("c-vote").setAttribute("aria-pressed", c === "vote" ? "true" : "false"); paintSpec(false); };
  $("t-now").addEventListener("click", () => setT("now")); $("t-jan").addEventListener("click", () => setT("jan"));
  $("c-camp").addEventListener("click", () => setC("camp")); $("c-vote").addEventListener("click", () => setC("vote"));
  paintSpec(false);
}
function paintSpec(animate) {
  const box = $("spec"), jan = spec.time === "jan";
  box.dataset.time = spec.time; box.dataset.color = spec.color;
  const mainOf = p => jan ? (typeof p.stance_start_2026 === "number" ? p.stance_start_2026 : p.stance_now) : p.stance_now;
  const otherOf = p => jan ? p.stance_now : p.stance_start_2026;
  const c = spec.cnt[spec.time], o = spec.cnt[jan ? "now" : "jan"], oLab = jan ? NOW_LBL : "1월";
  /* 셈 칸 */
  const tile = (cls, lb, v, unit, was) => el("div", { class: "tile " + cls }, el("div", { class: "lb", text: lb }), el("span", { class: "vl" }, String(v), unit ? el("small", { text: unit }) : null), el("span", { class: "was", text: was }));
  $("tiles").replaceChildren(
    tile("hawk", "매파 쪽 (0 위)", c.hawk, "명", `${oLab} ${o.hawk}명`), tile("zero", "0 — 유지가 기본", c.zero, "명", `${oLab} ${o.zero}명`),
    tile("dove", "비둘기 쪽 (0 아래)", c.dove, "명", `${oLab} ${o.dove}명`), tile("med", `중간값 · ${jan ? "1월 연초" : NOW_LBL}`, fmtS(c.med), "", `${oLab} ${fmtS(o.med)}`));
  $("spec-mt").textContent = `중간값 ${fmtS(c.med)}`;
  $("spec-mt").style.left = specPos(c.med);
  /* FLIP: 줄 순서가 바뀌면 옛 자리에서 새 자리로 미끄러진다(움직임을 끄면 즉시) */
  const go = animate && MOTION;
  const first = go ? new Map(spec.rows.map(r => [r, r.row.getBoundingClientRect().top])) : null;
  if (go) { box.classList.add("moving"); void box.offsetWidth; }
  const order = spec.rows.slice().sort((a, b) => mainOf(b.p) - mainOf(a.p) || ((otherOf(b.p) ?? 0) - (otherOf(a.p) ?? 0)) || a.p._i - b.p._i);
  order.forEach(r => {
    const p = r.p, m = mainOf(p), ot = otherOf(p);
    const vote = spec.color === "vote", unk = campCls(p) === "unk";
    const col = vote ? (p.voter_2026 ? "var(--amber)" : "#6a6a6a") : campVar(p);
    const lo = Math.min(ot ?? m, m), hi = Math.max(ot ?? m, m);
    r.ln.style.left = specPos(lo); r.ln.style.width = `calc(${specPos(hi)} - ${specPos(lo)})`; r.ln.style.background = col; r.ln.style.display = hi > lo ? "" : "none";
    r.s0.style.left = specPos(typeof ot === "number" ? ot : m); r.s0.style.display = typeof ot === "number" && ot !== m ? "" : "none";
    r.s1.style.left = specPos(m);
    r.s1.style.background = vote ? (p.voter_2026 ? "var(--amber)" : "#000") : (unk ? "#000" : col);
    r.s1.style.border = vote ? (p.voter_2026 ? "0" : "2px solid #8a8a8a") : (unk ? "2px dashed var(--unk)" : "0");
    r.mdn.style.left = specPos(c.med);
    r.val.textContent = fmtS(m);
    r.row.setAttribute("aria-label", `${p.name_ko}: ${jan ? "1월" : NOW_LBL} ${fmtS(m)}, ${jan ? NOW_LBL : "1월"} ${fmtS(ot)}, 관찰자 라벨 ${p.camp}, 2026 투표 ${p.voter_2026 ? "있음" : "없음"} (운영자 해석)`);
    box.append(r.row);
  });
  if (go) {
    order.forEach(r => {
      const dy = first.get(r) - r.row.getBoundingClientRect().top;
      if (!dy) return;
      r.row.style.transition = "none"; r.row.style.transform = `translateY(${dy}px)`; r.row.style.zIndex = "1";
    });
    void box.offsetWidth;
    order.forEach(r => { if (!r.row.style.transform) return; r.row.style.transition = "transform .6s cubic-bezier(.3, .1, .2, 1)"; r.row.style.transform = ""; });
    clearTimeout(spec.t);
    spec.t = setTimeout(() => { box.classList.remove("moving"); order.forEach(r => { r.row.style.transition = ""; r.row.style.zIndex = ""; }); }, 700);
  } else box.classList.remove("moving");
  const key = $("spec-key");
  key.replaceChildren(...(spec.color === "vote"
    ? [el("span", {}, el("i", { style: "background:var(--amber)" }), "2026 투표권"), el("span", {}, el("i", { style: "background:#000;border:2px solid #8a8a8a" }), "투표권 없음")]
    : CAMP_ORDER.map(cn => el("span", {}, el("i", { style: cn === "미상" ? "background:#000;border:2px dashed var(--unk)" : `background:var(--${CAMP[cn]})` }), cn))),
    el("span", { text: `찬 점 = ${jan ? "1월 연초" : NOW_LBL} · 빈 원 = ${jan ? NOW_LBL : "1월 연초"} · 호박색 점선 = 중간값 ${fmtS(c.med)}` }),
    el("span", { text: spec.color === "vote" ? "색: 투표권 — 라벨과 위치가 어긋나는 사람은 ‘관찰자 라벨’로 보면 보인다" : "색: 관찰자 라벨(위치 숫자와 다른 출처 — 둘이 어긋나는 사람이 볼거리)" }));
}

/* ───────── 표결 장부 ───────── */
function buildLedger() {
  const t = $("ledger");
  const rows = [];
  people.filter(p => p.voter_2026).forEach(p => rows.push({ key: p.key, name: sur(p), full: p.name_ko, p }));
  for (const [k, o] of Object.entries(OFFROSTER)) rows.splice(people.filter(p => p.voter_2026 && p.seat === "board").length, 0, { key: k, name: o.name, full: o.full, off: o });
  const cell = (r, m) => {
    if (r.p) return cellOf(r.p, m);
    if (m.date > r.off.until) return { t: "before" };
    if (m.vote == null) return { t: "plan" };
    const d = (m.dissents || []).find(x => x.key === r.key);
    return d ? { t: "dissent", side: d.side } : { t: "with" };
  };
  const decShort = m => /인상/.test(m.decision) ? (/(\+\d+bp)/.exec(m.decision) || ["인상"])[0].replace("bp", "") : /동결/.test(m.decision) ? "동결" : /인하/.test(m.decision) ? "인하" : (m.decision || "");
  const upper = m => { const r = /(\d+\.\d+)~(\d+\.\d+)%/.exec(m.decision || ""); return r ? r[2] : null; };
  const nm = nextMeeting();
  t.append(el("caption", { class: "sr", text: "2026 FOMC 회의별 투표권자의 표 — 머리 다섯 줄: 회의 날짜, 결정, 발표된 표 수, 상단 금리(%), 의장" }));
  const r1 = el("tr", { class: "r-date" }, el("th", { class: "rowh", scope: "col", text: "회의" }));
  const r2 = el("tr", { class: "r-dec" }, el("th", { class: "rowh", scope: "row", text: "결정" }));
  const r3 = el("tr", { class: "r-tally" }, el("th", { class: "rowh", scope: "row", text: "표" }));
  const r4 = el("tr", { class: "r-rate" }, el("th", { class: "rowh", scope: "row", text: "상단 %" }));
  const r5 = el("tr", { class: "r-chair" }, el("th", { class: "rowh", scope: "row", text: "의장" }));
  let prevRate = null, prevChair = null;
  meetings.forEach(m => {
    const plan = m.vote == null, soon = nm && nm.m === m;
    r1.append(el("th", { scope: "col", class: soon ? "cur-col" : null, title: `${m.first_day || ""} ~ ${m.date} · ${decOf(m)}${m.note ? " — " + m.note : ""}`, text: `${+m.date.slice(5, 7)}/${+m.date.slice(8, 10)}` }));
    r2.append(el("th", { class: plan ? "plan" : /인상/.test(m.decision) ? "hike" : null, title: plan && waitsResult(m) ? WAITS_TITLE : null, text: plan ? (waitsResult(m) ? "미반영" : "예정") : decShort(m) }));
    r3.append(el("th", { text: plan ? "?" : m.vote }));
    const u = upper(m), up = u && prevRate && +u > +prevRate;
    r4.append(el("th", { class: up ? "up" : null, title: u ? `범위 윗값 ${u}%` : waitsResult(m) ? WAITS_TITLE : "아직 열리지 않음", text: u ? (up ? "▲" : "") + u : "—" }));
    if (u) prevRate = u;
    const ch = byKey[m.chair] ? sur(byKey[m.chair]) : (m.chair || "");
    r5.append(el("th", { class: prevChair && prevChair !== m.chair ? "chg" : null, text: ch }));
    prevChair = m.chair;
  });
  t.append(el("thead", {}, r1, r2, r3, r4, r5));
  const tb = el("tbody");
  rows.forEach(r => {
    const nameBtn = el("button", { type: "button", title: r.full }, r.name, r.off ? el("small", { text: " 전" }) : null);
    if (r.p) nameBtn.addEventListener("click", () => select(r.key, { push: true, scroll: true }));
    else nameBtn.disabled = true;
    tb.append(el("tr", { "data-key": r.key }, el("th", { scope: "row" }, nameBtn),
      ...meetings.map(m => {
        const c = cell(r, m);
        const cls = (c.t === "dissent" ? SIDE(c.side).cls : c.t === "with" ? "with" : c.t === "plan" ? "plan" : "off") + (c.chair ? " chair" : "");
        const kid = c.t === "dissent" ? c.side : c.t === "with" ? "·" : c.t === "plan" ? el("span", { class: "q", text: "?" }) : "–";
        return el("td", { class: cls, title: `${r.full} · ${m.date}: ${c.t === "dissent" ? c.side + " 쪽 반대" : c.t === "with" ? "반대 기록 없음" : c.t === "plan" ? (waitsResult(m) ? WAITS_TITLE : "아직 열리지 않음") : "위원 아님"}${c.chair ? " · 의장" : ""}` }, kid);
      })));
  });
  t.append(tb);
  /* 칸 합계 확인 */
  const foot = el("tr", {}, el("th", { scope: "row", text: "칸 합" }));
  meetings.forEach(m => {
    if (!m.vote) {
      const cur = nm && nm.m === m, wait = !cur && waitsResult(m);
      foot.append(el("td", { class: "soon", title: cur ? (nm.days > 0 ? `첫날까지 ${nm.label}(한국 날짜)` : "회의 중(한국 날짜)") : wait ? WAITS_TITLE : "예정",
        text: cur ? nm.label : wait ? "미반영" : "예정" }));
      return;
    }
    const [a, b] = m.vote.split("-").map(Number);
    let w = 0, d = 0;
    rows.forEach(r => { const c = cell(r, m); if (c.t === "with") w++; else if (c.t === "dissent") d++; });
    const ok = w === a && d === b;
    foot.append(el("td", { class: ok ? "ok" : "bad", title: ok ? `칸 합 ${w}-${d} = 발표 ${m.vote}` : `칸 합 ${w}-${d} ≠ 발표 ${m.vote}` }, el("span", { class: "cnt", text: `${w}-${d}` }), ok ? "✓" : "?"));
  });
  t.append(el("tfoot", {}, foot));
  const ol = $("meets");
  meetings.forEach(m => ol.append(el("li", {}, el("time", { text: md(m.date) }),
    el("div", {}, el("b", { text: decOf(m) }), m.vote ? ` · ${m.vote}` : "", m.note ? el("span", { text: " — " + m.note }) : null))));
  /* 2027 교대 */
  const sw = $("swap");
  const outP = people.filter(p => p.voter_2026 && !p.voter_2027), inP = people.filter(p => !p.voter_2026 && p.voter_2027);
  const li = p => { const b = el("button", { type: "button" }, el("i", { class: "camp-sq " + campCls(p) }), p.name_ko, el("small", { text: `${p.camp} · ${p.seat === "board" ? "이사" : SEAL(p.district)}` })); b.addEventListener("click", () => select(p.key, { push: true, scroll: true })); return el("li", {}, b); };
  sw.append(el("div", { class: "out" }, el("h4", { text: `2027년에 투표권을 내려놓는 ${outP.length}명` }), el("ul", {}, ...outP.map(li))),
    el("div", { class: "in" }, el("h4", { text: `2027년에 투표권을 받는 ${inP.length}명` }), el("ul", {}, ...inP.map(li))),
    el("div", { class: "swap-note" }, "지구 총재 투표권의 해마다 돌아가는 몫(자료의 2026·2027 투표권 칸 그대로). 라벨은 관찰자 라벨. 조건: ",
      ...people.filter(p => p.voter_note).flatMap((p, i) => [i ? " · " : "", `${sur(p)} — ${p.voter_note}`])));
}

/* ───────── 출신 ───────── */
function buildMix() {
  const order = ["학계", "혼합", "실무(시장)", "실무(은행·감독)", "실무(경영)", "정책 관료", "법조"];
  const colors = ["#c9c4b8", "#8f8f8f", "#ff9e1b", "#d3a45f", "#f6d200", "#36d07f", "#b99cff"];
  const count = {};
  people.forEach(p => { const t = order.find(o => (p.bg_type || "") === o) || order.find(o => (p.bg_type || "").startsWith(o)) || "혼합"; (count[t] = count[t] || []).push(p); });
  order.forEach((t, i) => {
    const ps = count[t]; if (!ps) return;
    $("mix-bar").append(el("span", { style: `flex:${ps.length};background:${colors[i]}`, title: `${t} ${ps.length}명: ${ps.map(p => p.name_ko).join(", ")}`, text: String(ps.length) }));
    $("mix-keys").append(el("span", {}, el("i", { style: `background:${colors[i]}` }), `${t} ${ps.length} — ${ps.map(sur).join("·")}`));
  });
  const hubs = {};
  people.forEach(p => (p.journey || []).forEach(j => {
    if (j.now || j.kind === "other") return;
    let name = (j.org_ko || j.org).replace(/\(.*?\)/g, "").replace(/ 로스쿨| 와튼스쿨| 부스| 켈로그| 포드스쿨| 포드 공공정책대학|·스탠퍼드 GSB/g, "").trim();
    if (/^하버드/.test(name)) name = "하버드대";
    const h = hubs[name] = hubs[name] || { kinds: new Set(), ps: new Map() };
    h.kinds.add(KIND[j.kind] || "기타"); h.ps.set(p.key, p);
  }));
  const all = Object.entries(hubs).filter(([, h]) => h.ps.size >= 2).sort((a, b) => b[1].ps.size - a[1].ps.size || a[0].localeCompare(b[0], "ko"));
  const pbtn = p => { const b = el("button", { type: "button", text: p.name_ko }); b.addEventListener("click", () => select(p.key, { push: true, scroll: true })); return b; };
  all.filter(([, h]) => h.ps.size >= 3).forEach(([name, h]) => {
    $("hubs").append(el("li", {}, el("div", { class: "hn" }, el("b", { text: name }), el("span", { text: String(h.ps.size) })),
      el("div", { class: "hk", text: [...h.kinds].join("·") }),
      el("div", { class: "hp" }, ...[...h.ps.values()].map(pbtn))));
  });
  const two = all.filter(([, h]) => h.ps.size === 2);
  if (two.length) {
    const sbtn = p => { const b = el("button", { type: "button", title: p.name_ko, "aria-label": p.name_ko, text: sur(p) }); b.addEventListener("click", () => select(p.key, { push: true, scroll: true })); return b; };
    const box = el("ul", { class: "hubs2" });
    two.forEach(([name, h]) => {
      const [a, b] = [...h.ps.values()];
      box.append(el("li", {}, el("b", { text: name }), el("span", {}, sbtn(a), " · ", sbtn(b))));
    });
    $("hubs").after(el("p", { class: "hubs2-h", text: `두 사람씩 거쳐 간 곳 ${two.length}곳` }), box);
  }
}

/* ───────── 머리: 기능 키 · 찾기 · 띠 · 움직임 · 단축키 · D-n ───────── */
const SECTIONS = [["file-wrap", "파일", true], ["sec-base", "기준선", true], ["sec-route", "노선도", true], ["sec-talk", "말·기록", true],
  ["sec-dmap", "지구 지도"], ["sec-spec", "스펙트럼"], ["sec-ledger", "표결 장부"], ["sec-mix", "출신"], ["sec-notes", "읽기 전에"]];
let spyHold = 0;
function litKey(id) { document.querySelectorAll("#fkeys button").forEach(b => b.setAttribute("aria-current", b.dataset.target === id ? "true" : "false")); }
function jump(id, instant) {
  const n = $(id); if (!n) return;
  n.scrollIntoView({ behavior: MOTION && !instant ? "smooth" : "auto", block: "start" });
  if (SECTIONS.some(s => s[0] === id)) { litKey(id); spyHold = Date.now() + 800; }
}
function buildKeys() {
  const nav = $("fkeys");
  SECTIONS.forEach(([id, label, inFile], i) => {
    const b = el("button", { type: "button", class: inFile ? "file-key" : null, "data-target": id, "aria-keyshortcuts": String(i + 1) }, el("kbd", { text: String(i + 1) }), label);
    b.addEventListener("click", () => jump(id));
    nav.append(b);
  });
}
function buildTape() {
  const tape = $("tape");
  const who = (key, cls, text) => el("span", { class: "tw" + (cls ? " " + cls : ""), "data-key": key, text });
  const items = [];
  meetings.forEach(m => items.push({ d: m.date, node: () => el("span", { class: "tape-item" }, el("time", { text: m.date.slice(2) }),
    el("span", { text: "FOMC " + (m.vote == null ? `${waitsResult(m) ? "결과 미반영" : "예정"} ${md(m.first_day || m.date)}~${m.date.slice(8)}` : m.decision) }),
    m.vote ? el("em", { text: m.vote }) : null,
    (m.dissents || []).length ? el("small", {}, "반대 ", ...m.dissents.flatMap((x, i) => { const s = SIDE(x.side); return [i ? " " : "", who(x.key, s.cls, s.mark + nameOfKey(x.key))]; })) : null) }));
  (DATA.events_2026 || []).forEach(e => items.push({ d: e.date, node: () => {
    /* 사건 글 안의 이름(keys에 적힌 사람의 성)을 표시해 두면, 그 사람을 고를 때 호박색으로 켜진다 */
    const names = (e.keys || []).filter(k => byKey[k]).map(k => [sur(byKey[k]), k]).filter(([nm]) => nm);
    const span = el("span");
    let rest = e.text || "";
    while (rest) {
      let hit = null;
      for (const [nm, k] of names) { const i = rest.indexOf(nm); if (i >= 0 && (!hit || i < hit.i)) hit = { i, nm, k }; }
      if (!hit || !hit.nm) { span.append(rest); break; }
      span.append(rest.slice(0, hit.i), who(hit.k, null, hit.nm));
      rest = rest.slice(hit.i + hit.nm.length);
    }
    const src = (e.src || []).map(s => `${s.outlet} ${s.date}`).join(" · ");
    return el("span", { class: "tape-item", title: `확인 수준 ${e.cert || "미상"} — ` + (src ? "출처: " + src : "출처 미첨부") },
      el("time", { text: e.date.slice(2) }), span, e.cert === "2차" ? el("small", { text: "보도" }) : null);
  } }));
  items.sort((a, b) => a.d.localeCompare(b.d));
  people.forEach(p => { const q = (p.phrases || [])[0]; if (q) items.push({ node: () => el("span", { class: "tape-item" }, el("em", {}, who(p.key, null, sur(p))), el("span", { lang: "en", text: `“${q.text}”` }), el("small", { text: q.date || "" })) }); });
  const run = () => el("div", { class: "tape-run" }, ...items.map(i => i.node()));
  const r2 = run(); r2.setAttribute("aria-hidden", "true");
  tape.append(el("div", { class: "tape-track" }, run(), r2));
}
function markTape() { document.querySelectorAll(".tape .tw").forEach(n => n.classList.toggle("me", n.dataset.key === current)); }
function setMotion(on, save) {
  MOTION = on;
  document.documentElement.dataset.motion = on ? "on" : "off";
  const b = $("motion"); b.setAttribute("aria-pressed", on ? "true" : "false"); b.textContent = on ? "움직임 켬" : "움직임 끔";
  if (!on) { stopTrace(); if (route.p) drawRoute(route.p, {}); }
  if (save) { try { localStorage.setItem("motion", on ? "on" : "off"); } catch (e) {} }
}
function setKeys(on, save) {
  KEYS_ON = on;
  const b = $("keys"); b.setAttribute("aria-pressed", on ? "true" : "false"); b.textContent = on ? "단축키 켬" : "단축키 끔";
  document.querySelectorAll("#fkeys button").forEach((x, i) => { if (on) x.setAttribute("aria-keyshortcuts", String(i + 1)); else x.removeAttribute("aria-keyshortcuts"); });
  if (save) { try { localStorage.setItem("keys", on ? "on" : "off"); } catch (e) {} }
}
function tickDday() {
  const n = nextMeeting(), box = $("dday");
  box.replaceChildren();
  if (!n) { box.append(el("b", { text: "2026 일정 끝" })); return; }
  box.append(el("span", { class: "dlong", text: "FOMC " }), el("b", { text: `${md(n.start)}~${n.m.date.slice(8)}` }), " ", el("strong", { text: n.label }));
}
function buildSearch() {
  try { if (window.matchMedia("(max-width: 640px)").matches) $("q").placeholder = "이름·도시·표지 글자"; } catch (e) {}
  const dl = $("names");
  people.forEach(p => { dl.append(el("option", { value: p.name_ko }), el("option", { value: p.name_en })); });
  const norm = s => String(s || "").toLowerCase().replace(/[\s.·,]/g, "");
  function find(q) {
    const n = norm(q); if (!n) return [];
    if (/^[a-l]$/.test(n)) { const d = DIST["abcdefghijkl".indexOf(n) + 1]; return d ? [byKey[d.president_key]].filter(Boolean) : []; }
    const dn = /^제?(\d{1,2})(지구)?$/.exec(n); if (dn) { const d = DIST[+dn[1]]; return d ? [byKey[d.president_key]].filter(Boolean) : []; }
    if (n === "dc" || n === "이사" || n === "이사회") return people.filter(p => p.seat === "board");
    if (byKey[n]) return [byKey[n]];
    const hits = [];
    const score = p => {
      const d = DIST[p.district];
      const fields = [[p.name_ko, 5], [p.name_en, 5], [p.key, 4], [p.role_short, 2], [d && d.bank_ko, 3], [d && d.city, 3], [d && d.bank, 2], [p.seat === "board" ? "이사회 board 워싱턴 washington" : "", 1]];
      let s = 0; for (const [f, w] of fields) if (f && norm(f).includes(n)) s = Math.max(s, w);
      return s;
    };
    people.forEach(p => { const s = score(p); if (s) hits.push([s, p]); });
    return hits.sort((a, b) => b[0] - a[0] || a[1]._i - b[1]._i).map(h => h[1]);
  }
  $("cmd").addEventListener("submit", e => {
    e.preventDefault();
    const q = $("q").value, hits = find(q), msg = $("cmd-msg");
    if (!hits.length) { msg.textContent = q.trim() ? `‘${q.trim()}’ — 찾지 못함` : ""; return; }
    msg.textContent = hits.length > 1 ? `${hits.length}명 중 ${sur(hits[0])}` : `→ ${hits[0].name_ko}`;
    select(hits[0].key, { push: true, scroll: true, focus: true });
    $("q").value = "";
  });
}

/* ───────── 고르기 · 주소 ───────── */
let current = null;
function select(key, opt) {
  opt = opt || {};
  const p = byKey[key] || byKey.warsh || people[0]; if (!p) return;
  const changed = current !== p.key;
  const from = { ...route.vb };
  current = p.key;
  document.querySelectorAll(".who, .spec-row").forEach(b => b.setAttribute("aria-current", b.dataset.key === p.key ? "true" : "false"));
  document.querySelectorAll("#ledger tbody tr").forEach(tr => tr.classList.toggle("cur", tr.dataset.key === p.key));
  const anim = !!opt.push && changed;
  renderFile(p, { fly: anim, trace: anim, from });
  const live = $("file-live"); if (live) live.textContent = `${p.name_ko} 파일 — ${p._i + 1}/${people.length}`;
  markDmap();
  markTape();
  if (anim) { const f = $("file"); f.classList.remove("flash"); void f.offsetWidth; f.classList.add("flash"); }
  if (opt.push && location.hash !== "#" + p.key) { try { history.replaceState(null, "", "#" + p.key); } catch (e) { location.hash = p.key; } }
  if (opt.scroll) {
    const top = $("file-wrap").getBoundingClientRect().top;
    if (top < 0 || top > window.innerHeight * 0.6) jump("file-wrap");
  }
  if (opt.focus) $("file").focus({ preventScroll: true });
}
function step(d) { const i = current ? byKey[current]._i : 0; select(people[(i + d + people.length) % people.length].key, { push: true, scroll: true }); }
function cycleBoard() {
  const board = people.filter(p => p.seat === "board");
  const i = board.findIndex(p => p.key === current);
  select(board[(i + 1) % board.length].key, { push: true, scroll: true });
}
window.addEventListener("hashchange", () => { const k = hashKey(); if (k && k !== current && byKey[k]) select(k, { push: true, scroll: true }); });
/* 한 글자 단축키 — 머리의 ‘단축키’로 끈다(WCAG 2.1.4). 입력칸·조합 중·수정 키와 함께면 무시 */
document.addEventListener("keydown", e => {
  if (e.key === "Escape" && e.target === $("q")) { $("q").value = ""; $("q").blur(); return; }
  const tag = (e.target && e.target.tagName) || "";
  if (!KEYS_ON || e.isComposing || /INPUT|TEXTAREA|SELECT/.test(tag) || (e.target && e.target.isContentEditable) || e.metaKey || e.ctrlKey || e.altKey) return;
  const letter = /^Key([A-L])$/.exec(e.code || "");
  if (e.key === "/" || e.code === "Slash") { e.preventDefault(); $("q").focus(); return; }
  if (/^[1-9]$/.test(e.key)) { const s = SECTIONS[+e.key - 1]; if (s) { e.preventDefault(); jump(s[0]); } return; }
  if (e.repeat) return;
  if (letter) { const d = DIST["ABCDEFGHIJKL".indexOf(letter[1]) + 1]; if (d && byKey[d.president_key]) { e.preventDefault(); select(d.president_key, { push: true, scroll: true }); } return; }
  if (e.key === "0" || e.code === "Digit0") { e.preventDefault(); cycleBoard(); return; }
  if (e.key === "[" || e.code === "BracketLeft") { e.preventDefault(); step(-1); }
  else if (e.key === "]" || e.code === "BracketRight") { e.preventDefault(); step(1); }
});

/* 숫자 줄 · 주의 한 줄 · 읽기 전에 */
function buildStatus() {
  const held = meetings.filter(m => m.vote);
  const dis = held.flatMap(m => m.dissents || []);
  const stops = people.flatMap(p => p.journey || []);
  const cnt = c => stops.filter(j => j.cert === c).length;
  const kv = (k, v) => el("span", {}, k + " ", el("b", { text: String(v) }));
  $("status").append(...[["기준일", DATA.asof || "—"], ["위원", people.length], ["2026 투표", people.filter(p => p.voter_2026).length], ["회의", `${held.length}/${meetings.length}`],
    ["반대표", `${dis.length}(${new Set(dis.map(d => d.key)).size}명)`]].map(([k, v]) => kv(k, v)));
  /* 이력은 확인 수준별 셈과 한 덩어리로 — 셋의 합이 이력 수와 맞을 때만 '=' 꼴 */
  const lv = [["1차", cnt("1차")], ["2차", cnt("2차")], ["사전 지식", cnt("사전 지식")]];
  const sums = lv.reduce((a, [, v]) => a + v, 0) === stops.length;
  const piece = (k, v) => el("span", { class: "kvn" }, k + " ", el("b", { text: String(v) }));
  $("status").append(el("span", { class: "grp", title: "걸어온 길 기록 수와 그 확인 수준" }, piece("이력", stops.length),
    el("i", { class: "op", "aria-hidden": "true", text: sums ? " = " : " · " }),
    ...lv.flatMap(([k, v], i) => [i ? el("i", { class: "op", "aria-hidden": "true", text: sums ? " + " : " · " }) : null, piece(k, v)])),
    kv("위치 추정", stops.filter(j => j.loc_guess).length));
}
function buildNotes() {
  const asof = DATA.asof || "";
  $("h1-small").textContent = `FOMC 2026 · 참가자 ${people.length}명 · 참고 — 예측 아님`;
  const c = $("caveat");
  const toNotes = el("button", { type: "button", text: "전문 ↓" }); toNotes.addEventListener("click", () => jump("sec-notes"));
  const draft = DATA.review !== "approved";
  if (!draft) { const m = document.querySelector(".mark"); if (m) { m.title = "참고 자료이고 금리 예측이 아니다"; m.replaceChildren("참고 — 예측 아님"); } }
  /* 초안이면 사람마다의 확인 상태(p.review — 없으면 페이지 전체)를 센다: 2026-11-04부터 일부만 확인함 */
  const okN = people.filter(p => reviewOf(p) === "approved").length;
  const draftNote = okN ? ` 섞임 — ${okN}명 확인함 · ${people.length - okN}명 사람 확인 전` : " 사람 확인 전";
  c.append(el("b", { text: draft ? "초안" : "확인" }), draft ? draftNote : " 사람이 출처를 확인함", el("i", { "aria-hidden": "true", text: "|" }),
    el("b", { text: "라벨" }), " 매파·중도는 관찰자 평판, ±2 위치는 운영자 해석", el("i", { "aria-hidden": "true", text: "|" }),
    el("b", { text: "미확인" }), " ‘사전 지식’·‘위치 추정’ 표시", el("i", { "aria-hidden": "true", text: "|" }), "금리 예측 아님 ", toNotes);
  const ol = $("notes");
  (DATA.notes || []).forEach(t => ol.append(el("li", { text: t })));
  if (DATA.camp_note) ol.append(el("li", { text: DATA.camp_note }));
  const now = specCounts("stance_now"), jan = specCounts("stance_start_2026");
  const nulls = people.filter(p => typeof p.stance_now !== "number").map(sur).join("·");
  ol.append(el("li", { text: "이 페이지가 덧붙인 것(사실 자료 아님): 도시 약호(공항 약호를 닮게 붙인 이름표) · 지구 바탕색 · 표결 장부의 ‘다수’ 칸(반대 기록이 없는 투표권자를 다수 쪽으로 보고 발표된 표 수와 맞춰 본 것)과 ‘취임 전’ 칸(지금 자리 기록의 시작일 — 워시 2026-05-22) · 마이런의 마지막 회의(2026 사건 기록의 05-22 워시 취임 무렵 퇴임으로 보고 그 뒤를 ‘위원 아님’으로) · 장부의 상단 금리 줄(결정 문구 범위의 윗값) · " +
    `스펙트럼의 셈 칸과 중간값(운영자 해석 숫자를 센 것이라 이것도 운영자 해석 — ${NOW_LBL} 매파 쪽 ${now.hawk}·0 ${now.zero}·비둘기 쪽 ${now.dove}·중간값 ${fmtS(now.med)}, 1월 ${jan.hawk}·${jan.zero}·${jan.dove}·${fmtS(jan.med)}, 판단 불가 ${nulls} 제외) · ` +
    "위원 모니터의 기울기 눈금(같은 위치 숫자를 그린 것) · ‘19명 겹침’의 도시별 사람 수(걸어온 길의 장소 글자로 센 것 — 확인 수준이 섞여 있다) · 환승역 집계 · 다음 회의까지 D-n(보는 기기의 한국 날짜 기준). 사진·로고는 쓰지 않았다." }));
}

/* ───────── 시작 ───────── */
setMotion(MOTION, false);
setKeys(KEYS_ON, false);
buildKeys(); buildTape(); buildSearch(); buildRail(); buildRouteBase(); buildDmap(); buildSpectrum(); buildLedger(); buildMix(); buildStatus(); buildNotes();
paintStrip(); loadRemarks();
tickDday(); setInterval(tickDday, 60000);
$("motion").addEventListener("click", () => setMotion(!MOTION, true));
$("keys").addEventListener("click", () => setKeys(!KEYS_ON, true));
$("prev").addEventListener("click", () => step(-1));
$("next").addEventListener("click", () => step(1));
/* 머리 높이 · 크기가 바뀌면 지도 글자 크기를 다시 맞춘다 */
function syncHead() { document.documentElement.style.setProperty("--head-h", $("head").offsetHeight + "px"); }
syncHead();
{
  const k = hashKey();
  select(byKey[k] ? k : "warsh", {});
  /* 사람 주소로 열었고 명단이 파일 위에 쌓이는 좁은 화면이면 곧장 파일로 */
  if (byKey[k] && window.innerWidth <= 1079) requestAnimationFrame(() => jump("file-wrap", true));
}
let rz = 0, lastW = window.innerWidth;
window.addEventListener("resize", () => {
  syncHead();
  clearTimeout(rz);
  rz = setTimeout(() => { if (Math.abs(window.innerWidth - lastW) < 2) return; lastW = window.innerWidth; if (route.p) drawRoute(route.p, {}); drawDmapMarks(); }, 150);
});
if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { syncHead(); if (route.p && !route.raf) drawRoute(route.p, {}); drawDmapMarks(); }).catch(() => {});
/* 흐름에 따라 기능 키 불 켜기 — 위에서부터 머리선(머리 높이 + 16px)을 넘어선 마지막 절. 없으면 첫 절 */
let spyRaf = 0;
function spy() {
  spyRaf = 0;
  if (Date.now() < spyHold) return;
  const line = $("head").offsetHeight + 16;
  let best = SECTIONS[0][0];
  for (const [id] of SECTIONS) { const n = $(id); if (n && n.getBoundingClientRect().top <= line) best = id; }
  litKey(best);
}
window.addEventListener("scroll", () => { if (!spyRaf) spyRaf = requestAnimationFrame(spy); }, { passive: true });
spy();
/* 파일로 건너뛰기 — 주소(#사람)를 바꾸지 않고 초점만 옮긴다(점검 페이지와 같다) */
document.querySelector(".skip").addEventListener("click", e => { e.preventDefault(); $("file").focus(); });
