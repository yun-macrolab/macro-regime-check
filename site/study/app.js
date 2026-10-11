// 공부 화면의 틀 — 요소 도우미, 길, 상태 줄, 가드(틀 안 · 사파리 탭 · 기기 이름), 쓰기 한 길, 공유, 판 글자.
// 문서를 바꾸는 손은 여기 적힌 것뿐이다: 요소는 el()로만 만들고, 글은 글자(텍스트)로만 들어간다.
// 화면 모듈(오늘 · 주간 · 질문 · 설정)은 register()로 들어온다. 맞춤 · 녹음 모듈은 쓸 때마다 다시 보고, 없으면 없는 대로 돈다.
window.StudyApp = (() => {
  "use strict";

  const VERSION = "1";

  // ── 요소 도우미 ── 허용 목록 밖의 태그 · 속성 · 주소는 던진다(그것은 버그다). 문자열 자식은 글자로만 들어간다.
  const TAGS = Object.freeze(["div", "section", "header", "nav", "main", "h1", "h2", "p", "span", "strong", "small", "ul", "ol", "li",
    "a", "button", "input", "label", "details", "summary", "pre", "audio"]);
  const ATTRS = Object.freeze(["id", "class", "role", "type", "value", "placeholder", "maxlength", "inputmode", "enterkeyhint",
    "autocomplete", "autocapitalize", "autocorrect", "spellcheck", "name", "for", "disabled", "hidden", "checked", "readonly", "open",
    "tabindex", "href", "rel", "target", "src", "controls", "preload", "data-k",
    "aria-label", "aria-live", "aria-current", "aria-pressed", "aria-describedby", "aria-hidden"]);
  const FLAGS = Object.freeze(["disabled", "hidden", "checked", "open", "readonly"]);
  const TYPES = Object.freeze({ input: Object.freeze(["text", "checkbox"]), button: Object.freeze(["button"]) });
  const OUT_REL = "noopener noreferrer";
  const OUT_TARGET = "_blank";

  const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const fail = code => { throw new Error(code); };
  const inside = v => typeof v === "string" && v[0] === "#" && StudyCore.ROUTES.includes(v.slice(1));
  const secret = attrs => String(attrs.class || "").split(" ").includes("st-secret");

  // 켜고 끄는 속성: 참이면 빈 값으로 넣고, 거짓 · 없음이면 넣지 않는다
  function switchValue(v) {
    if (v === true || v === "") return "";
    return v === false ? null : fail("attr");
  }
  // 속성 하나의 값을 정한다: 넣을 글자, 넣지 않을 것이면 null
  function attrValue(tag, name, v, attrs) {
    if (!ATTRS.includes(name)) fail("attr");
    if (v === null || v === undefined) return null;
    if (FLAGS.includes(name) || name === "controls") return switchValue(v);
    if (name === "href") return tag === "a" && (inside(v) || StudyCore.safeLink(v)) ? v : fail("href");
    if (name === "src") return tag === "audio" && typeof v === "string" && v.startsWith("blob:") ? v : fail("src");
    if (name === "type" && !(has(TYPES, tag) && TYPES[tag].includes(v))) fail("attr");
    if ((name === "rel" && v !== OUT_REL) || (name === "target" && v !== OUT_TARGET)) fail("attr");
    if (name === "value" && secret(attrs)) fail("attr");
    return ["string", "number", "boolean"].includes(typeof v) ? String(v) : fail("attr");
  }
  // 바깥으로 가는 링크(열쇠 만들기)에는 rel · target을 스스로 붙인다
  function el(tag, attrs, ...children) {
    if (!TAGS.includes(tag)) fail("tag");
    const given = attrs || {};
    const pairs = Object.keys(given).map(name => [name, attrValue(tag, name, given[name], given)]).filter(pair => pair[1] !== null);
    const out = pairs.some(pair => pair[0] === "href" && !inside(pair[1]));
    const marks = out ? [["rel", OUT_REL], ["target", OUT_TARGET]] : [];
    const node = document.createElement(tag);
    for (const pair of [...pairs.filter(p => !marks.some(m => m[0] === p[0])), ...marks]) node.setAttribute(pair[0], pair[1]);
    for (const child of children.flat(Infinity)) {
      if (child !== null && child !== undefined && child !== false) node.append(typeof child === "number" ? String(child) : child);
    }
    return node;
  }
  function flag(node, name, on) {
    if (!FLAGS.includes(name)) fail("attr");
    if (on) node.setAttribute(name, "");
    else node.removeAttribute(name);
  }

  // ── 창 ── 주소 · 기기 · 난수 · 공유. 화면 모듈은 이것들을 직접 만지지 않는다.
  const ALPHA = "abcdefghijklmnopqrstuvwxyz0123456789";
  function framed() {
    try {
      return window.top !== window.self;
    } catch (err) {
      return true;
    }
  }
  function env() {
    return { https: location.protocol === "https:", standalone: navigator.standalone, framed: framed() };
  }
  function reload() {
    location.reload();
  }
  function rand4() {
    try {
      return Array.from(crypto.getRandomValues(new Uint8Array(4)), b => ALPHA[b % 36]).join("");
    } catch (err) {
      return (Date.now() % 1679616).toString(36).padStart(4, "0");
    }
  }
  // 복사한다. 안 되면 "shown"(화면이 글을 보여 준다)
  function copy(text) {
    try {
      const board = navigator.clipboard;
      if (!board || typeof board.writeText !== "function") return Promise.resolve("shown");
      return Promise.resolve(board.writeText(text)).then(() => "copied", () => "shown");
    } catch (err) {
      return Promise.resolve("shown");
    }
  }
  // 공유 창 → 사용자가 닫으면 "cancel" → 없거나 그 밖의 거절이면 복사 → 그것도 안 되면 "shown". 거절하는 약속을 돌려주지 않는다.
  function share(text) {
    try {
      if (typeof navigator.share !== "function") return copy(text);
      return Promise.resolve(navigator.share({ text })).then(() => "shared", err => (err && err.name === "AbortError" ? "cancel" : copy(text)));
    } catch (err) {
      return copy(text);
    }
  }

  // ── 틀의 상태 ──
  const NO_SYNC = Object.freeze({ phase: "idle", stop: "off", code: null, failedThisOpen: false });
  let screens = new Map();       // 길 이름 → 화면({ render, refresh, leave })
  let navs = new Map();          // 길 이름 → 이동 줄의 링크
  let started = false;
  let live = false;              // 날짜 줄 · 상태 줄 · 이동 줄을 그렸다(시작 차례의 6까지 왔다)
  let current = null;            // 지금 길
  let drawnDay = "";             // 마지막으로 그린 공부 날짜

  const byId = id => document.getElementById(id);
  // 맞춤 · 녹음 모듈을 부른다. 없으면 아무 일도 없고, 그 모듈이 던져도 화면은 계속 돈다.
  function tell(module, method, ...args) {
    try {
      return module && typeof module[method] === "function" ? module[method](...args) : undefined;
    } catch (err) {
      return undefined;
    }
  }
  function route() {
    const name = String(location.hash).replace(/^#/, "");
    return StudyCore.ROUTES.includes(name) ? name : "today";
  }
  function register(name, screen) {
    if (StudyCore.ROUTES.includes(name) && screen && typeof screen.render === "function") screens = new Map([...screens, [name, screen]]);
  }
  function ctx() {
    const nowMs = Date.now();
    const today = StudyCore.studyDate(nowMs);
    const wk = StudyCore.weekOf(today);
    return { nowMs, today, wk, lastWk: StudyCore.addDays(wk, -7), view: StudyCore.buildView(StudyStore.copies()), dev: StudyStore.getDevice(), env: env() };
  }
  function note(key, vars) {
    byId("st-note").textContent = key === null || key === undefined ? "" : StudyCore.t(key, vars);
  }

  // ── 날짜 줄 · 상태 줄 · 이동 줄 ──
  function status(today) {
    const snap = tell(window.StudySync, "snapshot") || NO_SYNC;
    const conn = StudyStore.getConn();
    const queue = StudyStore.queue();
    return StudyCore.pickStatus({
      storeOk: StudyStore.ok(), hasKey: conn.hasKey, auth401: conn.auth === "401", stop: snap.stop, code: snap.code,
      paused: StudyStore.getFlag("pause"), queueN: queue.length, lastOkMs: StudyStore.syncState().at,
      amber: Boolean(snap.failedThisOpen) && StudyCore.staleQueue(queue, today),
    });
  }
  function drawHead(c) {
    const s = status(c.today);
    drawnDay = c.today;
    byId("st-date").textContent = StudyCore.headDate(c.today);
    byId("st-status").textContent = StudyCore.t(s.key, s.vars);
    byId("st-status").setAttribute("class", s.tone === "" ? "st-status" : "st-status st-" + s.tone);
  }
  function navLink(name) {
    const a = el("a", { href: "#" + name, "data-k": name }, StudyCore.t("NAV_" + name.toUpperCase()));
    a.addEventListener("click", () => again(name));
    return a;
  }
  // 지금 길의 이름을 다시 누르면 그 화면을 새로 그린다(주소가 같아 hashchange가 오지 않는다)
  function again(name) {
    if (name === current) go(name);
  }

  // ── 길 ── 화면을 새로 그리는 곳은 show 하나다
  function show(name) {
    const old = screens.get(current);
    if (old && typeof old.leave === "function") old.leave();
    tell(window.StudyRecorder, "stopPlayback");
    current = name;
    const c = ctx();
    drawHead(c);
    for (const pair of navs) flagCurrent(pair[1], pair[0] === name);
    note(null);
    byId("st-main").replaceChildren();
    if (screens.has(name)) screens.get(name).render(byId("st-main"), c);
  }
  function flagCurrent(a, on) {
    if (on) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  }
  function go(name) {
    if (!live) return;
    const to = StudyCore.ROUTES.includes(name) ? name : "today";
    history.replaceState(null, "", "#" + to);
    show(to);
  }
  function refresh(why) {
    if (!live) return;
    const c = ctx();
    drawHead(c);
    const screen = screens.get(current);
    if (screen && typeof screen.refresh === "function") screen.refresh(byId("st-main"), c, why);
  }

  // ── 시작 차례 ── ① 틀 안이면 그만 ② 기본 문구 지움 ③ 사파리 탭이면 안내만 ④ 오래 두기 ⑤ 이름 ⑥ 들어가기
  function showGuide() {
    const steps = ["GUIDE_1", "GUIDE_2", "GUIDE_3"].map(key => el("p", null, StudyCore.T[key]));
    byId("st-main").replaceChildren(el("section", { id: "st-guide" }, el("h1", null, StudyCore.T.GUIDE_HEAD), steps));
  }
  // 꼴이 틀리면 경고만. 적지 못했어도(메모리 대역에 있다) 들어간다 — 도장은 찍을 수 있어야 한다
  function saveName(input, warn) {
    const r = StudyStore.setDevice(String(input.value).trim());
    warn.textContent = r.code === "dev" ? StudyCore.T.NAME_BAD : "";
    if (r.code !== "dev") enter();
  }
  function showName() {
    const input = el("input", { id: "st-name-input", class: "st-input", type: "text", autocomplete: "off", autocapitalize: "off",
      autocorrect: "off", spellcheck: "false", enterkeyhint: "done", "aria-describedby": "st-name-warn" });
    const save = el("button", { id: "st-name-save", class: "st-btn", type: "button" }, StudyCore.T.NAME_SAVE);
    const warn = el("p", { id: "st-name-warn", class: "st-warn" });
    save.addEventListener("click", () => saveName(input, warn));
    input.addEventListener("keydown", ev => { if (ev.key === "Enter" && !ev.isComposing) saveName(input, warn); });
    byId("st-main").replaceChildren(el("section", { id: "st-name" },
      el("label", { for: "st-name-input" }, StudyCore.T.NAME_ASK), el("p", { class: "st-dim" }, StudyCore.T.NAME_NOTE), input, save, warn));
  }
  function enter() {
    if (live) return;
    live = true;
    byId("st-head").replaceChildren(el("span", { id: "st-date" }), el("span", { id: "st-status", class: "st-status" }));
    navs = new Map(StudyCore.ROUTES.map(name => [name, navLink(name)]));
    byId("st-nav").replaceChildren(...navs.values());
    tell(window.StudySync, "init", onSync);
    window.addEventListener("hashchange", () => show(route()));
    document.addEventListener("visibilitychange", onVisible);
    show(route());
    requestSync("open");
  }
  function start() {
    if (started || env().framed) return;
    started = true;
    if (byId("st-fallback")) byId("st-fallback").remove();
    if (env().standalone === false) {
      showGuide();
      return;
    }
    StudyStore.persist();
    if (StudyStore.getDevice() === "") showName();
    else enter();
  }

  // ── 쓰기 한 길 · 맞춤 고리 · 돌아옴 ── 기기에 먼저 쓰고 → 그리고 → 올리기를 청한다
  function requestSync(reason) {
    tell(window.StudySync, "request", reason);
  }
  // 틀이 다 뜨기 전(틀 안 · 홈 화면 안내 · 이름 묻기)에는 쓰지 않는다
  function write(kind, fields) {
    if (!live) return { ok: false, code: "dev", obj: null, stored: false };
    const made = StudyCore.makeLine(kind, fields, { nowMs: Date.now(), dev: StudyStore.getDevice(), rand: rand4() });
    if (!made.ok) return { ok: false, code: made.code, obj: null, stored: false };
    const stored = StudyStore.appendLine(StudyCore.monthOf(made.obj.d), made.text).ok;
    refresh("write");
    requestSync(stored ? "save" : "store-fail");
    return { ok: true, code: null, obj: made.obj, stored };
  }
  function onSync(snap, info) {
    refresh("sync");
    if (info && info.big) note("NOTE_BIG");
  }
  // 화면으로 돌아왔을 때: 공부 날짜가 바뀌었으면 오늘 화면을 새로, 같으면 맞춤이 바꾸는 자리만
  function onVisible() {
    if (!live || document.visibilityState !== "visible") return;
    if (StudyCore.studyDate(Date.now()) === drawnDay) refresh("back");
    else go("today");
    requestSync("back");
  }

  document.addEventListener("DOMContentLoaded", start);

  return {
    VERSION, el, flag, register, start, go, ctx, write, refresh, requestSync, note, share, env, reload, rand4,
    _: { TAGS, ATTRS, FLAGS },
  };
})();
