"use strict";
// 공부 화면 테스트의 가짜 묶음 — 시계 · 난수 · 통신 · 저장 공간 · 문서를 모두 가짜로 갈아 끼운다.
// 화면 파일(site/study/*.js)은 이 파일의 world() · boot()로만 싣는다(require하지 않는다).
// 실제 통신 0번, 실제 시간 0초. 지어낸 글만 쓴다. 아래 가짜 객체는 속을 고쳐 쓴다(화면 파일과 달리 그래도 된다).
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const STUDY = path.join(__dirname, "..", "site", "study");
const T0 = Date.parse("2026-10-12T23:30:00Z");                   // KST 2026-10-13(화) 08:30 — 모든 테스트의 기준 시각

// 문맥 안에서 만든 배열 · 객체는 바깥 것과 원형이 달라 deepEqual이 실패한다 — 견주기 전에 바깥 값으로 옮긴다
const plain = v => (v === undefined ? undefined : JSON.parse(JSON.stringify(v)));
const named = name => Object.assign(new Error(name), { name });
// 약속이 끝나기를 기다린다(가짜 시계는 흐르지 않는다)
async function settle() {
  for (let i = 0; i < 12; i++) await new Promise(resolve => setImmediate(resolve));
}

// 가짜 저장 공간. failOn(정규식 | 글자 | null)에 걸리는 이름의 setItem만 예외를 낸다.
// 훑는 손(key · length)은 일부러 없다. 두 world에 같은 것을 넘기면 "탭 둘"이다.
function fakeStorage(seed) {
  const data = new Map(Object.entries(seed || {}));
  let fail = null;
  const hit = name => fail !== null && (fail instanceof RegExp ? fail.test(name) : name.includes(fail));
  return {
    data,
    getItem: name => (data.has(String(name)) ? data.get(String(name)) : null),
    setItem(name, value) {
      if (hit(String(name))) throw named("QuotaExceededError");
      data.set(String(name), String(value));
    },
    removeItem: name => { data.delete(String(name)); },
    failOn: pattern => { fail = pattern === undefined ? null : pattern; },
  };
}

// 가짜 시계. 문맥의 Date.now와 setTimeout · setInterval을 쥔다(world가 api를 문맥에 넣는다).
// advance(ms)는 그 사이에 걸린 때맞춤을 때의 차례대로, 그때의 시각으로 울린다. set(ms)은 울리지 않고 시각만 옮긴다.
function fakeClock(ms) {
  let now = ms;
  let seq = 0;
  const timers = new Map();
  const add = (fn, delay, every) => { seq += 1; timers.set(seq, { at: now + Math.max(0, Number(delay) || 0), fn, every }); return seq; };
  function next(limit) {
    let best = null;
    for (const [id, timer] of timers) if (timer.at <= limit && (best === null || timer.at < best.timer.at)) best = { id, timer };
    return best;
  }
  function advance(span) {
    const limit = now + span;
    for (let guard = 0; ; guard++) {
      const due = next(limit);
      if (!due) break;
      if (guard > 100000) throw new Error("가짜 시계: 때맞춤이 끝나지 않는다");
      now = Math.max(now, due.timer.at);
      if (due.timer.every === null) timers.delete(due.id);
      else due.timer.at = now + due.timer.every;
      due.timer.fn();
    }
    now = limit;
  }
  const api = {
    setTimeout: (fn, delay) => add(fn, delay, null),
    clearTimeout: id => { timers.delete(id); },
    setInterval: (fn, delay) => add(fn, delay, Math.max(1, Number(delay) || 0)),
    clearInterval: id => { timers.delete(id); },
  };
  return { now: () => now, set: v => { now = v; }, advance, pending: () => timers.size, api };
}

// 가짜 통신. route: { status, body, headers } · Error(통신 오류) · "hang"(끊길 때까지 안 끝남) · (call) => route
// 준비한 것이 떨어졌는데 요청이 오면 unexpected를 올리고 거절한다.
function fakeNet(routes) {
  const queue = [...(routes || [])];
  const net = { calls: [], unexpected: 0, fetch: null, push: route => { queue.push(route); } };
  net.fetch = (url, init = {}) => {
    const call = { url: String(url), method: init.method || "GET", headers: { ...(init.headers || {}) },
      body: init.body === undefined ? null : init.body, cache: init.cache, credentials: init.credentials,
      referrerPolicy: init.referrerPolicy, redirect: init.redirect };
    net.calls.push(call);
    if (queue.length === 0) {
      net.unexpected += 1;
      return Promise.reject(new Error("가짜 통신: 준비하지 않은 요청 " + call.method + " " + call.url));
    }
    const route = queue.shift();
    return answer(typeof route === "function" ? route(call) : route, init.signal);
  };
  return net;
}
function answer(route, signal) {
  if (route instanceof Error) return Promise.reject(route);
  if (route === "hang") return hang(signal);
  const body = route.body;
  const heads = new Map(Object.entries(route.headers || {}).map(([k, v]) => [k.toLowerCase(), String(v)]));
  return Promise.resolve({
    status: route.status,
    ok: route.status >= 200 && route.status < 300,
    headers: { get: name => (heads.has(String(name).toLowerCase()) ? heads.get(String(name).toLowerCase()) : null) },
    json: async () => JSON.parse(typeof body === "string" ? body : JSON.stringify(body)),
    text: async () => (typeof body === "string" ? body : JSON.stringify(body)),
  });
}
function hang(signal) {
  return new Promise((resolve, reject) => {
    if (!signal) return;
    if (signal.aborted) reject(named("AbortError"));
    else signal.addEventListener("abort", () => reject(named("AbortError")));
  });
}

Object.assign(module.exports, { T0, plain, settle, fakeStorage, fakeClock, fakeNet });

// ── 가짜 문서 ──
// 화면이 쓰는 손만 흉내 낸다: setAttribute · removeAttribute · getAttribute · hasAttribute · append · replaceChildren ·
// remove · textContent · addEventListener · focus · value · checked. 목록에 없는 대입(hidden = … 등)은 TypeError다.
// doc.touches는 나무와 값을 바꾼 횟수다("문서를 건드리지 않았다"를 볼 때 쓴다).
const SKELETON = ["st-fallback", "st-head", "st-nav", "st-note", "st-main"];
const SKELETON_TAGS = ["p", "header", "nav", "p", "main"];
const FOCUSABLE = ["a", "button", "input", "summary"];

class Text {
  constructor(data) { this.data = String(data); this.parent = null; }
  get textContent() { return this.data; }
}
class Elem {
  constructor(tag, doc) {
    this.tag = tag; this.doc = doc; this.attrs = new Map(); this.kids = []; this.parent = null; this.on = {};
    this.dirty = { value: null, checked: null };
    Object.preventExtensions(this);
  }
  touch() { this.doc.touches += 1; }
  setAttribute(k, v) { this.touch(); this.attrs.set(String(k), String(v)); }
  removeAttribute(k) { this.touch(); this.attrs.delete(String(k)); }
  getAttribute(k) { return this.attrs.has(String(k)) ? this.attrs.get(String(k)) : null; }
  hasAttribute(k) { return this.attrs.has(String(k)); }
  append(...xs) { this.touch(); for (const x of xs) adopt(this, x); }
  replaceChildren(...xs) { this.touch(); for (const k of this.kids) k.parent = null; this.kids = []; for (const x of xs) adopt(this, x); }
  remove() { this.touch(); detach(this); }
  addEventListener(type, fn) { (this.on[type] = this.on[type] || []).push(fn); }
  focus() { if (FOCUSABLE.includes(this.tag) || this.attrs.has("tabindex")) this.doc.activeElement = this; }
  get textContent() { return this.kids.map(k => k.textContent).join(""); }
  set textContent(v) { this.replaceChildren(...(v === null || v === undefined || v === "" ? [] : [String(v)])); }
  get value() { return this.dirty.value !== null ? this.dirty.value : (this.attrs.get("value") || ""); }
  set value(v) { this.touch(); this.dirty.value = String(v); }
  get checked() { return this.dirty.checked !== null ? this.dirty.checked : this.attrs.has("checked"); }
  set checked(v) { this.touch(); this.dirty.checked = Boolean(v); }
}
function detach(node) {
  if (!node.parent) return;
  node.parent.kids = node.parent.kids.filter(k => k !== node);
  node.parent = null;
}
function adopt(parent, x) {
  const node = x instanceof Elem || x instanceof Text ? x : new Text(x);
  detach(node);
  node.parent = parent;
  parent.kids.push(node);
}
function fakeDoc() {
  const doc = { visibilityState: "visible", activeElement: null, touches: 0, on: {}, body: null, goHash() {} };
  doc.createElement = tag => { doc.touches += 1; return new Elem(String(tag), doc); };
  doc.addEventListener = (type, fn) => { (doc.on[type] = doc.on[type] || []).push(fn); };
  doc.getElementById = id => byId(doc.body, String(id));
  doc.body = new Elem("body", doc);
  SKELETON.forEach((id, i) => { const node = new Elem(SKELETON_TAGS[i], doc); node.setAttribute("id", id); doc.body.append(node); });
  byId(doc.body, "st-note").setAttribute("role", "status");
  doc.touches = 0;
  return doc;
}

// ── 찾기 도우미 ── node 자리에는 요소나 가짜 문서(doc)를 넣는다
const rootOf = node => (node && node.body) || node;
function all(node, pred = () => true, out = []) {
  const n = rootOf(node);
  if (!(n instanceof Elem)) return out;
  if (pred(n)) out.push(n);
  for (const k of n.kids) all(k, pred, out);
  return out;
}
const byId = (node, id) => all(node, n => n.getAttribute("id") === id)[0] || null;
const byTag = (node, tag) => all(node, n => n.tag === tag);
const byClass = (node, cls) => all(node, n => (n.getAttribute("class") || "").split(" ").includes(cls));
const byK = (node, k) => all(node, n => n.getAttribute("data-k") === k);
const text = node => rootOf(node).textContent;

// ── 누름 흉내 ── 사건은 누른 요소에서 위로 올라간다(target은 누른 요소, currentTarget은 처리기가 걸린 요소)
function emit(node, type, more) {
  const ev = { type, target: node, currentTarget: node, defaultPrevented: false, stopped: false, ...more,
    preventDefault() { ev.defaultPrevented = true; }, stopPropagation() { ev.stopped = true; } };
  for (let n = node; n && !ev.stopped; n = n.parent) {
    ev.currentTarget = n;
    for (const fn of [...(n.on[type] || [])]) fn(ev);
  }
  return ev;
}
function check(node, on) {
  if (node.hasAttribute("disabled")) return;
  node.checked = on;
  for (const type of ["click", "input", "change"]) emit(node, type);
}
function press(node) {
  if (node.hasAttribute("disabled")) return;
  if (node.tag === "input" && node.getAttribute("type") === "checkbox") { check(node, !node.checked); return; }
  const ev = emit(node, "click");
  const href = node.tag === "a" ? node.getAttribute("href") : null;
  if (href && href.startsWith("#") && !ev.defaultPrevented) node.doc.goHash(href);
  const fold = node.tag === "summary" && node.parent && node.parent.tag === "details" ? node.parent : null;
  if (fold && fold.hasAttribute("open")) fold.removeAttribute("open");
  else if (fold) fold.setAttribute("open", "");
  if (fold) emit(fold, "toggle");
}
function type(node, value) {
  if (node.hasAttribute("disabled") || node.hasAttribute("readonly")) return;
  node.value = value;
  emit(node, "input");
}
const key = (node, name, more) => emit(node, "keydown", { key: name, isComposing: false, ...more });

// ── 가짜 창 ──
// 끝나는 꼴 넷: 그 밖("ok" · true · false)은 풀림, "deny"는 NotAllowedError, "cancel"은 AbortError, "hang"은 끝나지 않음
function outcome(mode, onOk) {
  if (mode === "hang") return new Promise(() => {});
  if (mode === "deny") return Promise.reject(named("NotAllowedError"));
  if (mode === "cancel") return Promise.reject(named("AbortError"));
  return Promise.resolve(onOk());
}
function fakeNav(opts, w) {
  const nav = {};
  const has = v => v !== undefined && v !== "none";
  if (opts.standalone !== undefined) nav.standalone = opts.standalone;
  if (has(opts.share)) nav.share = data => outcome(opts.share, () => { w.shared.push(data && data.text); });
  if (has(opts.clip)) nav.clipboard = { writeText: value => outcome(opts.clip, () => { w.copied.push(String(value)); }) };
  if (has(opts.persist)) nav.storage = { persist: () => outcome(opts.persist, () => opts.persist) };
  return nav;
}
// 난수도 정해진 차례로 나온다(같은 world에서 두 번 부르면 다른 값, 새 world는 처음부터)
function fakeCrypto() {
  let n = 7;
  return { getRandomValues(bytes) { for (let i = 0; i < bytes.length; i++) { n = (n * 73 + 41) % 251; bytes[i] = n; } return bytes; } };
}

// 뼈대(index.html)의 <script src>를 그 차례로 읽는다(?v=는 뗀다). html을 주면 그 글자열에서 읽는다.
function scripts(html) {
  const page = html === undefined ? fs.readFileSync(path.join(STUDY, "index.html"), "utf8") : html;
  return [...page.matchAll(/<script\b[^>]*\bsrc="([^"]+)"/g)].map(m => m[1].replace(/\?.*$/, ""));
}

// files를 한 문맥에 차례로 싣는다(시작은 하지 않는다). 새 문맥에 넣는 것은 언어 내장 말고 아래 것뿐이다.
// opts: now · storage · net · standalone · protocol · hash · framed · share · clip · persist · media · idb · extra
//   share: "ok" "deny" "cancel" "hang" "none"(기본) / clip: "ok" "deny" "none"(기본) / persist: true false "deny" "hang" "none"(기본)
//   media · idb: install(scope, w)가 있는 가짜(05가 만든다) / extra: 문맥에 더 넣을 전역(예: 대역 StudySync)
function world(files, opts = {}) {
  const w = { scope: null, doc: fakeDoc(), storage: opts.storage || fakeStorage(), clock: fakeClock(opts.now === undefined ? T0 : opts.now),
    net: opts.net || fakeNet([]), shared: [], copied: [], reloads: 0, fire: null };
  const winOn = {};
  const location = { protocol: opts.protocol || "https:", hash: opts.hash || "", reload: () => { w.reloads += 1; } };
  w.fire = (type, arg) => {
    if (type === "visibilitychange") w.doc.visibilityState = arg || "visible";
    for (const fn of [...(w.doc.on[type] || []), ...(winOn[type] || [])]) fn({ type, target: w.doc });
  };
  w.doc.goHash = hash => { if (location.hash !== hash) { location.hash = hash; w.fire("hashchange"); } };
  const scope = { TextEncoder, TextDecoder, atob, btoa, URL, AbortController, document: w.doc, location, navigator: fakeNav(opts, w),
    history: { replaceState: (state, title, url) => { if (String(url).startsWith("#")) location.hash = String(url); } },
    localStorage: w.storage, fetch: w.net.fetch, crypto: fakeCrypto(), ...w.clock.api,
    addEventListener: (type, fn) => { (winOn[type] = winOn[type] || []).push(fn); }, ...(opts.extra || {}) };
  scope.window = scope;
  scope.self = scope;
  scope.top = opts.framed ? {} : scope;
  w.scope = vm.createContext(scope);
  vm.runInContext("(now) => { Date.now = now; }", w.scope)(w.clock.now);
  for (const part of [opts.media, opts.idb]) if (part && typeof part.install === "function") part.install(scope, w);
  for (const name of files) vm.runInContext(fs.readFileSync(path.join(STUDY, name), "utf8"), w.scope, { filename: name });
  return w;
}
// index.html이 싣는 것을 그 차례로 싣고 시작한다. opts.html을 주면 파일 대신 그 글자열에서 차례를 읽는다.
async function boot(opts = {}) {
  const w = world(scripts(opts.html), opts);
  w.fire("DOMContentLoaded");
  await settle();
  return w;
}

Object.assign(module.exports, { SKELETON, scripts, world, boot, all, byId, byTag, byClass, byK, text, press, type, key, check });

// core.js의 makeLine으로 지어낸 줄을 만든다. at = { ms, dev, rand }(기본 T0 · "폰" · "k3f9"). 꼴이 맞지 않으면 던진다.
let lineCore = null;
function line(kind, fields, at = {}) {
  lineCore = lineCore || world(["core.js"]).scope.StudyCore;
  const made = lineCore.makeLine(kind, fields, { nowMs: at.ms === undefined ? T0 : at.ms, dev: at.dev || "폰", rand: at.rand || "k3f9" });
  if (!made.ok) throw new Error("line: " + kind + " 줄을 만들지 못했다 — " + made.code);
  return made.text;
}

Object.assign(module.exports, { line });

// ── 맞춤(sync.js)의 가짜 ── 가짜 열쇠와, 기록 저장소가 돌려주는 응답 본문.
// 열쇠 글자는 소스에 적지 않고 실행 때 만든다(영문 한 글자를 64번).
const KEY = "k".repeat(64);
// 파일 내용 응답: base64에 60자마다 줄바꿈이 들어가고 끝에도 줄바꿈이 붙는다. over로 칸을 바꾼다(예: { size: 700000 }).
function ghFile(text, sha, over = {}) {
  const bytes = Buffer.from(String(text), "utf8");
  const rows = bytes.toString("base64").match(/.{1,60}/g) || [];
  return { type: "file", encoding: "base64", size: bytes.length, sha: sha === undefined ? "sha0" : String(sha), content: rows.map(row => row + "\n").join(""), ...over };
}
// 저장소 정보 응답: 비공개이고 Pages가 꺼져 있다. over로 칸을 바꾼다(예: { private: false }).
const ghRepo = (over = {}) => ({ private: true, has_pages: false, ...over });

Object.assign(module.exports, { KEY, ghFile, ghRepo });

// ── 녹음(recorder.js)의 가짜 ── 가짜 마이크 · 녹음기 · 화면 켜 두기 · 재생 주소(fakeMedia)와 가짜 IndexedDB(fakeIdb).
// world의 opts.media · opts.idb로 꽂는다(install이 문맥에 전역을 단다). 실제 마이크도 실제 파일도 없고, 답은 모두 마이크로태스크로 온다(settle()이면 끝난다).
// 사건을 받는 것(트랙 · 녹음기 · 요청 · 트랜잭션)의 뿌리: addEventListener로 받고 emit으로 울린다
class FakeTarget {
  constructor() { this.on = {}; }
  addEventListener(type, fn) { (this.on[type] = this.on[type] || []).push(fn); }
  emit(type, more) { for (const fn of [...(this.on[type] || [])]) fn({ type, target: this, ...more }); }
}
// 가짜 소리 덩어리: 크기와 형식만 있다. 조각을 모으면 크기를 더한다
class FakeBlob {
  constructor(parts, opts) {
    this.size = (parts || []).reduce((sum, part) => sum + (part.size || 0), 0);
    this.type = (opts && opts.type) || "";
  }
}
const chunk = (size, type) => Object.assign(new FakeBlob([], { type }), { size });
class FakeTrack extends FakeTarget {
  constructor() { super(); this.kind = "audio"; this.readyState = "live"; }
  stop() { this.readyState = "ended"; }
}
// 가짜 녹음기의 틀. 돈 시간(가짜 시계) × rate 바이트의 덩어리 하나를 stop 뒤에 내놓는다
function recorderClass(media, w) {
  return class FakeRecorder extends FakeTarget {
    static isTypeSupported(type) { return media.types.includes(type); }
    constructor(stream, options = {}) {
      super();
      if (media.opts.recorder === "throw") throw named("NotSupportedError");
      Object.assign(this, { stream, options, state: "inactive", mimeType: options.mimeType || media.types[0] || "", began: null });
      media.recorders.push(this);
    }
    start() { this.state = "recording"; this.began = w.clock.now(); }
    stop() {
      if (this.state === "inactive") throw named("InvalidStateError");
      this.state = "inactive";
      const size = media.opts.recorder === "empty" ? 0 : Math.round((w.clock.now() - this.began) / 1000 * media.rate);
      if (media.opts.recorder === "nostop") return;
      Promise.resolve().then(() => { this.emit("dataavailable", { data: chunk(size, this.mimeType) }); this.emit("stop"); });
    }
  };
}
// 마이크를 청했다: 청한 것을 적고, mic에 따라 답한다. "hold"는 answer("ok" | "deny" | "error")를 부를 때까지 기다린다
function askMic(media, constraints) {
  const grant = () => { const stream = { tracks: [new FakeTrack()], getTracks() { return [...this.tracks]; } }; media.streams.push(stream); return stream; };
  const refuse = how => named(how === "deny" ? "NotAllowedError" : "NotFoundError");
  const mode = media.opts.mic || "ok";
  media.asks.push(constraints);
  media.log.push("mic");
  if (mode === "hold") return new Promise((resolve, reject) => { media.held = how => (how === "ok" ? resolve(grant()) : reject(refuse(how))); });
  return mode === "error" ? Promise.reject(refuse(mode)) : outcome(mode, grant);
}
function installMedia(media, scope, w) {
  const lock = () => { const held = { released: false, release() { held.released = true; return Promise.resolve(); } }; media.locks.push(held); return held; };
  const lend = () => { const url = "blob:study/" + (media.urls.length + 1); media.urls.push(url); media.log.push("url"); return url; };
  const wake = () => { media.log.push("wake"); return outcome(media.opts.wake || "ok", lock); };
  if (media.opts.mic !== "none") scope.navigator.mediaDevices = { getUserMedia: constraints => askMic(media, constraints) };
  if (media.opts.recorder !== "none") scope.MediaRecorder = recorderClass(media, w);
  if (media.opts.wake !== "none") scope.navigator.wakeLock = { request: wake };
  scope.Blob = FakeBlob;
  scope.URL = { createObjectURL: lend, revokeObjectURL: url => { media.revoked.push(String(url)); media.log.push("revoke"); } };
}
// 가짜 마이크 · 녹음기 · 화면 켜 두기 · 재생 주소.
// opts: mic "ok"(기본) "deny" "error"(마이크 없음) "hang"(허용이 끝나지 않음) "hold"(answer()로 나중에 답한다) "none"(mediaDevices 없음)
//       recorder "ok"(기본) "empty"(빈 파일) "nostop"(종료 사건이 오지 않음) "throw"(만들지 못함) "none"(MediaRecorder 없음)
//       wake "ok"(기본) "deny" "hang" "none"(wakeLock 없음) / types: 받는 형식(기본 ["audio/mp4"]) / rate: 초당 바이트(기본 8000 = 64kbps)
// 본 것: asks(청한 것) · streams · recorders · locks · urls(내준 재생 주소) · revoked(거둔 주소) · live()(열려 있는 마이크 트랙 수)
//       log(한 일의 차례 — "wake" "mic" "url" "revoke")
function fakeMedia(opts = {}) {
  const media = { opts, types: opts.types || ["audio/mp4"], rate: opts.rate || 8000, asks: [], streams: [], recorders: [], locks: [], urls: [], revoked: [],
    log: [], held: null };
  media.answer = how => { const held = media.held; media.held = null; if (held) held(how); };
  media.live = () => media.streams.flatMap(stream => stream.tracks).filter(track => track.readyState === "live").length;
  media.install = (scope, w) => installMedia(media, scope, w);
  return media;
}

// 가짜 IndexedDB. 요청은 마이크로태스크 뒤에 끝난다. 쓰기는 트랜잭션이 끝날 때 한꺼번에 들어간다(실패 · 끝나지 않음이면 하나도 들어가지 않는다).
function openIdb(idb, name, version) {
  const req = Object.assign(new FakeTarget(), { result: undefined, error: null });
  const how = idb.opts.open || "ok";
  idb.log.push("open " + name + " v" + version);
  if (how === "ok") Promise.resolve().then(() => opened(idb, name, req));
  if (how === "fail") Promise.resolve().then(() => { req.error = named("UnknownError"); req.emit("error"); });
  return req;
}
function opened(idb, name, req) {
  const fresh = !idb.stores.has(name);
  if (fresh) idb.stores.set(name, new Map());
  req.result = {
    createObjectStore: (store, options) => { idb.stores.get(name).set(store, options.keyPath); idb.log.push("store " + store + " keyPath=" + options.keyPath); },
    transaction: (store, mode) => txOf(idb, idb.stores.get(name), store, mode),
    close: () => { idb.log.push("close"); },
  };
  if (fresh) req.emit("upgradeneeded");
  req.emit("success");
}
function txOf(idb, stores, store, mode) {
  if (!stores.has(store)) throw named("NotFoundError");
  const how = idb.opts[mode === "readwrite" ? "write" : "read"] || "ok";
  const tx = Object.assign(new FakeTarget(), { error: null, jobs: [] });
  const add = (label, job) => { const req = Object.assign(new FakeTarget(), { result: undefined, error: null }); tx.jobs.push({ req, job }); idb.log.push(label); return req; };
  tx.objectStore = () => storeOf(idb, stores.get(store), add);
  if (how !== "hang") Promise.resolve().then(() => settleTx(tx, how));
  return tx;
}
function settleTx(tx, how) {
  if (how === "fail") {
    tx.error = named("QuotaExceededError");
    for (const type of ["error", "abort"]) tx.emit(type);
    return;
  }
  for (const { req, job } of tx.jobs) { req.result = job(); req.emit("success"); }
  tx.emit("complete");
}
function storeOf(idb, key, add) {
  const copy = row => ({ ...row });
  return {
    put: row => add("put " + row[key], () => { idb.rows.set(row[key], copy(row)); return row[key]; }),
    get: id => add("get " + id, () => (idb.rows.has(id) ? copy(idb.rows.get(id)) : undefined)),
    getAll: () => add("getAll", () => [...idb.rows.values()].map(copy)),
    delete: id => add("delete " + id, () => { idb.rows.delete(id); }),
    clear: () => add("clear", () => { idb.rows.clear(); }),
  };
}
// opts: open · write · read 가 저마다 "ok"(기본) "fail" "hang"(끝나지 않음) / none: true면 indexedDB가 없다. 도중에 opts를 바꿔도 된다.
// 본 것: rows(Map 키 → 값) · log(한 일의 차례). 두 world에 같은 것을 넘기면 같은 기기를 다시 연 것이다(rows가 남는다).
function fakeIdb(opts = {}) {
  const idb = { opts, rows: new Map(), stores: new Map(), log: [] };
  idb.install = scope => { if (!idb.opts.none) scope.indexedDB = { open: (name, version) => openIdb(idb, name, version) }; };
  return idb;
}

Object.assign(module.exports, { fakeMedia, fakeIdb });
