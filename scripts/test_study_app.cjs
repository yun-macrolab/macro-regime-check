"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const F = require("./study_fakes.cjs");

// 공부 화면의 시계(timer.js)와 틀(app.js) 테스트. 화면 파일은 가짜 묶음(study_fakes.cjs)으로만 싣는다. 지어낸 글만 쓴다.
// 돌리기: node --test scripts/test_study_app.cjs
const LS = "macro-study.";                                                         // 저장 이름의 머리(화면 쪽 상수 P와 같은 글자)
const kstMs = text => Date.parse(text + "+09:00");                                 // KST로 적은 시각의 ms

// ── timer.js: 2분 시계 ──
const TIMER_FILES = ["core.js", "store.js", "timer.js"];
// 시계 하나와, 그 시계가 알린 것(ticks: 남은 초, done: 말한 초)
function clockOn(w, slot = "today") {
  const seen = { ticks: [], done: [] };
  const timer = w.scope.StudyTimer.create(slot, { onTick: left => seen.ticks.push(left), onDone: sec => seen.done.push(sec) });
  return { timer, seen, talk: () => F.plain(w.scope.StudyStore.talk(slot)) };
}

test("시계: 시작 시각과의 차이로 잰다 — 남은 초가 바뀔 때만 알리고, 2분이면 끝을 한 번 알린다", () => {
  const w = F.world(TIMER_FILES);
  const { timer, seen, talk } = clockOn(w);
  assert.deepEqual([w.scope.StudyTimer.TICK_MS, F.plain(timer.state()), w.clock.pending()], [250, { phase: "idle", sec: 0, left: 120 }, 0]);
  assert.deepEqual([timer.start(), talk(), F.plain(timer.state())], [F.T0, { d: "2026-10-13", at: F.T0, end: null }, { phase: "running", sec: 0, left: 120 }]);
  w.clock.advance(999);
  assert.deepEqual([seen.ticks, w.clock.pending()], [[], 1]);
  w.clock.advance(1);
  assert.deepEqual(seen.ticks, [119]);
  w.clock.advance(118000);
  assert.deepEqual([seen.ticks.length, seen.ticks[118], seen.done, timer.state().phase], [119, 1, [], "running"]);
  w.clock.advance(1000);
  assert.deepEqual([seen.done, seen.ticks.length, w.clock.pending(), F.plain(timer.state()), talk().end], [[120], 119, 0, { phase: "done", sec: 120, left: 0 }, F.T0 + 120000]);
  w.clock.advance(600000);
  timer._.tick();
  assert.deepEqual(seen.done, [120]);                                                    // 끝은 한 번만 알린다
});

test("시계: 때맞춤이 멈춰 있었어도(화면이 가려짐) 다음 울림에서 지난 시간만큼 간다", () => {
  const w = F.world(TIMER_FILES);
  const { timer, seen, talk } = clockOn(w);
  timer.start();
  w.clock.set(F.T0 + 50400);                                                             // 때맞춤은 울리지 않고 시각만 갔다
  timer._.tick();
  assert.deepEqual([seen.ticks, F.plain(timer.state())], [[70], { phase: "running", sec: 50, left: 70 }]);
  w.clock.set(F.T0 + 500000);
  w.clock.advance(250);
  assert.deepEqual([seen.done, talk().end, w.clock.pending()], [[120], F.T0 + 120000, 0]);     // 끝 시각은 2분을 넘겨 적지 않는다
});

test("시계: [그만] — 말한 초를 돌려주고, 끝을 한 번만 알리고, 재기를 멈춘다", () => {
  const w = F.world(TIMER_FILES);
  const { timer, seen, talk } = clockOn(w);
  assert.deepEqual([timer.stop(), seen.done], [0, []]);                                  // 시작 전에는 아무 일도 없다
  timer.start();
  w.clock.advance(45300);
  assert.deepEqual([timer.stop(), seen.done, F.plain(timer.state()), talk().end, w.clock.pending()], [45, [45], { phase: "done", sec: 45, left: 75 }, F.T0 + 45300, 0]);
  w.clock.advance(300000);
  assert.deepEqual([timer.stop(), seen.done, timer.state().sec], [45, [45], 45]);
});

test("시계 이어 가기: 도중에 화면이 죽었다 살아나도 같은 공부 날짜면 이어 가고, 2분 뒤에 끝을 알린다", () => {
  const storage = F.fakeStorage();
  clockOn(F.world(TIMER_FILES, { storage })).timer.start();                              // 이 화면은 여기서 죽는다(때맞춤도 함께)
  const w = F.world(TIMER_FILES, { storage, now: F.T0 + 30000 });
  const { timer, seen, talk } = clockOn(w);
  assert.deepEqual([timer.resume(), F.plain(timer.state()), seen, w.clock.pending()], ["running", { phase: "running", sec: 30, left: 90 }, { ticks: [], done: [] }, 1]);
  w.clock.advance(89999);
  assert.deepEqual([seen.done, seen.ticks.length, seen.ticks[88]], [[], 89, 1]);
  w.clock.advance(1);
  assert.deepEqual([seen.done, talk(), w.clock.pending()], [[120], { d: "2026-10-13", at: F.T0, end: F.T0 + 120000 }, 0]);
});

test("시계 이어 가기: 2분이 지나 있으면 곧장 done이고 끝 시각을 채운다 — 다시 열 때는 알리지 않는다", () => {
  const storage = F.fakeStorage();
  clockOn(F.world(TIMER_FILES, { storage })).timer.start();
  const w = F.world(TIMER_FILES, { storage, now: F.T0 + 600000 });
  const { timer, seen, talk } = clockOn(w);
  assert.deepEqual([timer.resume(), F.plain(timer.state()), talk().end, seen, w.clock.pending()], ["done", { phase: "done", sec: 120, left: 0 }, F.T0 + 120000, { ticks: [], done: [] }, 0]);
  assert.deepEqual([timer.stop(), timer.resume(), seen.done], [120, "done", []]);
  const early = F.world(TIMER_FILES, { storage: F.fakeStorage(), now: F.T0 });
  const stopped = clockOn(early);
  stopped.timer.start();
  early.clock.advance(20000);
  stopped.timer.stop();
  assert.deepEqual([clockOn(F.world(TIMER_FILES, { storage: early.storage, now: F.T0 + 90000 })).timer.resume(), stopped.timer.state().sec], ["done", 20]);   // [그만]으로 끝낸 것도 done
});

test("시계 이어 가기: 공부 날짜가 바뀌었으면 지우고 idle이다 — 03:59:59와 04:00:00", () => {
  const storage = F.fakeStorage();
  const began = kstMs("2026-10-13T03:58:30");                                            // 공부 날짜는 아직 10-12
  clockOn(F.world(TIMER_FILES, { storage, now: began })).timer.start();
  assert.equal(JSON.parse(storage.data.get(LS + "talk")).today.d, "2026-10-12");
  const before = clockOn(F.world(TIMER_FILES, { storage, now: kstMs("2026-10-13T03:59:59") }));
  assert.deepEqual([before.timer.resume(), before.timer.state().left], ["running", 31]);
  const after = clockOn(F.world(TIMER_FILES, { storage, now: kstMs("2026-10-13T04:00:00") }));
  assert.deepEqual([after.timer.resume(), after.talk(), F.plain(after.timer.state()), after.seen.done], ["idle", null, { phase: "idle", sec: 0, left: 120 }, []]);
});

test("시계: 돌고 있는 시계는 04:00을 넘어도 끝까지 간다(다시 그리기 전까지)", () => {
  const w = F.world(TIMER_FILES, { now: kstMs("2026-10-13T03:59:00") });
  const { timer, seen } = clockOn(w);
  timer.start();
  w.clock.advance(120000);
  assert.deepEqual([seen.done, w.scope.StudyCore.studyDate(w.clock.now()), timer.resume()], [[120], "2026-10-13", "idle"]);
});

test("시계: 저장 공간이 말을 듣지 않아도 2분 뒤에 끝난다", () => {
  const storage = F.fakeStorage();
  storage.failOn("macro-study");
  const w = F.world(TIMER_FILES, { storage });
  const { timer, seen } = clockOn(w);
  timer.start();
  w.clock.advance(120000);
  assert.deepEqual([seen.done, timer.state().phase, storage.data.size, w.scope.StudyStore.ok()], [[120], "done", 0, false]);
});

test("시계: 화면마다 따로 돌고, 같은 화면이 다시 만들면 때맞춤은 하나이고 알림은 새 hooks로 간다", () => {
  const w = F.world(TIMER_FILES);
  const today = clockOn(w, "today");
  const ask = clockOn(w, "ask");
  today.timer.start();
  w.clock.advance(10000);
  ask.timer.start();
  assert.deepEqual([today.timer.state().left, ask.timer.state().left, w.clock.pending()], [110, 120, 2]);
  const redrawn = clockOn(w, "today");                                                   // 화면을 새로 그렸다
  assert.deepEqual([redrawn.timer.resume(), w.clock.pending()], ["running", 2]);
  w.clock.advance(110000);
  assert.deepEqual([today.seen.done, redrawn.seen.done, ask.seen.done, today.seen.ticks.length, ask.timer.state().left], [[], [120], [], 10, 10]);
  ask.timer.clear();
  assert.deepEqual([ask.talk(), F.plain(ask.timer.state()), w.clock.pending(), redrawn.talk().end], [null, { phase: "idle", sec: 0, left: 120 }, 0, F.T0 + 120000]);
});

test("시계: 다시 시작하면 처음부터 재고, hooks가 없어도 던지지 않는다", () => {
  const w = F.world(TIMER_FILES);
  const bare = w.scope.StudyTimer.create("today");
  bare.start();
  w.clock.advance(120000);
  assert.deepEqual([bare.state().phase, bare.stop()], ["done", 120]);
  const { timer, seen } = clockOn(w);
  w.clock.advance(5000);
  assert.deepEqual([timer.start(), F.plain(timer.state()), w.clock.pending()], [F.T0 + 125000, { phase: "running", sec: 0, left: 120 }, 1]);
  w.clock.advance(120000);
  assert.deepEqual([seen.done, Object.keys(timer).sort(), Object.keys(w.scope.StudyTimer).sort()], [[120], ["_", "clear", "resume", "start", "state", "stop"], ["TICK_MS", "create"]]);
});

// ── app.js: 요소 도우미 ──
const C = F.world(["core.js"]).scope.StudyCore;
const APP_FILES = ["core.js", "store.js", "timer.js", "app.js"];
const appOf = opts => F.world(APP_FILES, opts).scope.StudyApp;
const pairs = node => [...node.attrs];

test("틀 el: 허용한 태그와 속성으로 요소를 만들고, 문자열 자식은 글자로만 들어간다", () => {
  const w = F.world(APP_FILES);
  const A = w.scope.StudyApp;
  const node = A.el("p", { id: "x", class: "st-dim", "data-k": "full", tabindex: 0, hidden: false, "aria-pressed": true, role: null, name: undefined },
    "a<b onclick=1>", null, undefined, false, 3, [A.el("span", null, "c"), ["d"]]);
  assert.deepEqual([node.tag, pairs(node), F.text(node)], ["p", [["id", "x"], ["class", "st-dim"], ["data-k", "full"], ["tabindex", "0"], ["aria-pressed", "true"]], "a<b onclick=1>3cd"]);
  assert.deepEqual([F.byTag(node, "b").length, F.all(node).map(n => n.tag), A.el("div").attrs.size, F.text(A.el("ul", {}))], [0, ["p", "span"], 0, ""]);
});

test("틀 el: 금지 태그 · 처리기 이름 · 목록에 없는 속성은 던진다 — 요소를 만들기 전에", () => {
  const w = F.world(APP_FILES);
  const A = w.scope.StudyApp;
  for (const tag of ["script", "iframe", "img", "form", "textarea", "select", "style", "object", "svg", "DIV", "", null]) assert.throws(() => A.el(tag), { message: "tag" }, String(tag));
  for (const name of ["onclick", "onerror", "ONCLICK", "style", "srcdoc", "action", "formaction", "data-x", "is", "contenteditable"]) {
    assert.throws(() => A.el("div", { [name]: "x" }), { message: "attr" }, name);
  }
  for (const value of [{}, [], () => "x"]) assert.throws(() => A.el("div", { id: value }), { message: "attr" });
  assert.throws(() => A.el("div", ["id"]), { message: "attr" });
  assert.equal(w.doc.touches, 0);
});

test("틀 el: 링크는 안쪽 길 넷과 열쇠 만들기 링크뿐이다 — 바깥 링크에는 rel · target이 스스로 붙는다", () => {
  const A = appOf();
  const link = C.keyLink("폰", F.T0);
  assert.deepEqual(["#today", "#week", "#ask", "#set"].map(href => pairs(A.el("a", { href }))), [[["href", "#today"]], [["href", "#week"]], [["href", "#ask"]], [["href", "#set"]]]);
  assert.deepEqual(pairs(A.el("a", { href: link, class: "st-btn" }, "열기")), [["href", link], ["class", "st-btn"], ["rel", "noopener noreferrer"], ["target", "_blank"]]);
  assert.deepEqual(pairs(A.el("a", { target: "_blank", href: link, rel: "noopener noreferrer" })).map(p => p[0]), ["href", "rel", "target"]);
  const no = ["#nope", "#", "#today ", "./", "../", "index.html", "/", "https://example.org/", "//example.org", C.KEY_LINK_BASE, " " + link, "javascript:void 0", "data:text/html,x", 7, {}];
  for (const href of no) assert.throws(() => A.el("a", { href }), { message: "href" }, String(href));
  assert.throws(() => A.el("button", { href: "#today" }), { message: "href" });
  assert.throws(() => A.el("a", { href: "#today", target: "_top" }), { message: "attr" });
  assert.throws(() => A.el("a", { href: "#today", rel: "opener" }), { message: "attr" });
});

test("틀 el: src는 audio의 blob: 주소만, type은 정해진 것만, 열쇠 칸에는 value를 줄 수 없다", () => {
  const A = appOf();
  assert.deepEqual(pairs(A.el("audio", { src: "blob:https://example.org/1", controls: true, preload: "none" })), [["src", "blob:https://example.org/1"], ["controls", ""], ["preload", "none"]]);
  for (const pair of [["audio", "https://example.org/a.mp4"], ["audio", "data:audio/mp4,x"], ["audio", "a.mp4"], ["audio", 7], ["a", "blob:x"], ["input", "blob:x"]]) {
    assert.throws(() => A.el(pair[0], { src: pair[1] }), { message: "src" }, pair.join(" "));
  }
  assert.deepEqual([["input", "text"], ["input", "checkbox"], ["button", "button"]].map(p => A.el(p[0], { type: p[1] }).getAttribute("type")), ["text", "checkbox", "button"]);
  for (const pair of [["input", "password"], ["input", "file"], ["input", "hidden"], ["input", "submit"], ["button", "submit"], ["div", "text"], ["a", "button"], ["input", "constructor"]]) {
    assert.throws(() => A.el(pair[0], { type: pair[1] }), { message: "attr" }, pair.join(" "));
  }
  assert.throws(() => A.el("input", { type: "text", class: "st-input st-secret", value: "x" }), { message: "attr" });
  assert.deepEqual([A.el("input", { type: "text", class: "st-input", value: "글" }).value, A.el("input", { type: "text", class: "st-input st-secret" }).getAttribute("value")], ["글", null]);
});

test("틀 el · flag: 켜고 끄는 속성은 참이면 빈 값으로 넣고, 거짓이면 넣지 않는다", () => {
  const A = appOf();
  const button = A.el("button", { type: "button", disabled: true, hidden: false, open: null });
  assert.deepEqual(pairs(button), [["type", "button"], ["disabled", ""]]);
  for (const value of ["disabled", "true", 1, 0]) assert.throws(() => A.el("button", { disabled: value }), { message: "attr" }, String(value));
  A.flag(button, "disabled", false);
  A.flag(button, "hidden", true);
  A.flag(button, "hidden", 1);
  assert.deepEqual(pairs(button), [["type", "button"], ["hidden", ""]]);
  for (const name of ["onclick", "class", "value", "aria-pressed", "controls"]) assert.throws(() => A.flag(button, name, true), { message: "attr" }, name);
});

test("틀 el: 허용 목록이 약속과 같다(뒤 단계는 이 목록에 기댄다)", () => {
  const A = appOf();
  assert.deepEqual(F.plain(A._.TAGS), ["div", "section", "header", "nav", "main", "h1", "h2", "p", "span", "strong", "small", "ul", "ol", "li", "a", "button", "input", "label",
    "details", "summary", "pre", "audio"]);
  assert.deepEqual(F.plain(A._.ATTRS), ["id", "class", "role", "type", "value", "placeholder", "maxlength", "inputmode", "enterkeyhint", "autocomplete", "autocapitalize", "autocorrect",
    "spellcheck", "name", "for", "disabled", "hidden", "checked", "readonly", "open", "tabindex", "href", "rel", "target", "src", "controls", "preload", "data-k",
    "aria-label", "aria-live", "aria-current", "aria-pressed", "aria-describedby", "aria-hidden"]);
  assert.deepEqual([F.plain(A._.FLAGS), A.VERSION, Object.isFrozen(A._.TAGS)], [["disabled", "hidden", "checked", "open", "readonly"], "2", true]);
});

// ── app.js: 창 — 환경 · 난수 · 공유 ──
test("틀 창: env는 주소 · 기기 · 틀 안인지를 그대로 알려 준다", () => {
  const env = opts => { const e = appOf(opts).env(); return [e.https, e.standalone, e.framed]; };
  assert.deepEqual([env({}), env({ protocol: "http:", standalone: true }), env({ standalone: false, framed: true })], [[true, undefined, false], [false, true, false], [true, false, true]]);
});

test("틀 창: rand4는 [a-z0-9] 네 글자이고 난수가 없어도 던지지 않는다 — reload는 문서를 다시 읽는다", () => {
  const w = F.world(APP_FILES);
  const A = w.scope.StudyApp;
  const made = [A.rand4(), A.rand4(), appOf({ extra: { crypto: undefined } }).rand4()];
  assert.deepEqual([made.map(r => /^[a-z0-9]{4}$/.test(r)), made[0] === made[1]], [[true, true, true], false]);
  A.reload();
  assert.equal(w.reloads, 1);
});

test("틀 공유: 공유 창 → 닫으면 cancel → 없거나 거절이면 복사 → 그것도 안 되면 보여 주기", async () => {
  const run = async opts => { const w = F.world(APP_FILES, opts); return [await w.scope.StudyApp.share("오늘의 글"), w.shared, w.copied]; };
  assert.deepEqual(await run({ share: "ok", clip: "ok" }), ["shared", ["오늘의 글"], []]);
  assert.deepEqual(await run({ share: "cancel", clip: "ok" }), ["cancel", [], []]);                // 사용자가 닫았다 — 복사하지 않는다
  assert.deepEqual(await run({ share: "deny", clip: "ok" }), ["copied", [], ["오늘의 글"]]);
  assert.deepEqual(await run({ share: "none", clip: "ok" }), ["copied", [], ["오늘의 글"]]);
  assert.deepEqual([await run({ share: "deny", clip: "deny" }), await run({})], [["shown", [], []], ["shown", [], []]]);
  const boom = () => { throw new TypeError("x"); };
  assert.equal(await appOf({ extra: { navigator: { share: boom, clipboard: { writeText: boom } } } }).share("글"), "shown");
});

test("틀 공유: 공유 창이 닫히지 않아도 약속은 거절되지 않고, 화면의 다른 손은 그대로 돈다", async () => {
  const w = F.world(APP_FILES, { share: "hang", clip: "ok" });
  let ended = false;
  w.scope.StudyApp.share("글").then(() => { ended = true; });
  await F.settle();
  assert.deepEqual([ended, w.copied, w.scope.StudyApp.rand4().length, w.scope.StudyApp.el("p", null, "글").tag], [false, [], 4, "p"]);
});

// ── app.js: 시작 차례와 가드 · 길 ──
const KEY = "k".repeat(64);                                                        // 가짜 열쇠 — 글자를 소스에 적지 않는다
const next = (text, isoText, rand) => F.line("next", { text }, { ms: Date.parse(isoText), dev: "폰", rand });
const L1 = next("하나", "2026-10-12T23:30:00Z", "aaaa");
const OLD = next("어제 것", "2026-10-11T23:30:00Z", "oooo");                              // KST 10-12 08:30 — 오늘(10-13)보다 앞선 줄
// 이름이 이미 있는 기기의 저장 공간(seed의 이름에는 접두어를 붙여 넣는다)
const named = (seed = {}) => F.fakeStorage(Object.fromEntries(Object.entries({ dev: "폰", ...seed }).map(pair => [LS + pair[0], pair[1]])));
// 화면 대역 넷: 불린 것을 log에 적고, 그릴 때 자기 이름과 오늘 날짜를 한 줄 그린다
function stubScreens(w, log) {
  const A = w.scope.StudyApp;
  for (const name of ["today", "week", "ask", "set"]) {
    A.register(name, {
      render: (root, ctx) => { log.push("render " + name); root.append(A.el("p", { id: "scr-" + name }, name + " " + ctx.today)); },
      refresh: (root, ctx, why) => { log.push("refresh " + name + " " + why + " " + ctx.view.recs.length); },
      leave: () => { log.push("leave " + name); },
    });
  }
}
// 맞춤 모듈 대역: 불린 것을 같은 log에 적는다(차례를 본다)
function fakeSync(log, snap = {}) {
  const sync = { onChange: null, snap: { phase: "idle", stop: null, code: null, failedThisOpen: false, ...snap }, api: null };
  sync.api = { init: fn => { log.push("sync init"); sync.onChange = fn; }, request: reason => { log.push("sync " + reason); }, snapshot: () => sync.snap };
  return sync;
}
// 화면 파일 넷을 싣고 화면 대역을 넣은 뒤 시작한다
async function open(opts = {}, log = []) {
  const w = F.world(APP_FILES, opts);
  stubScreens(w, log);
  w.fire("DOMContentLoaded");
  await F.settle();
  return Object.assign(w, { A: w.scope.StudyApp, log, at: id => F.byId(w.doc, id) });
}
const idsIn = node => F.all(node).map(n => n.getAttribute("id")).filter(Boolean);

test("틀 시작: 다른 쪽의 틀 안이면 문서를 건드리지 않는다", async () => {
  const w = await open({ framed: true, storage: named() });
  w.A.start();
  w.A.go("week");
  w.A.refresh("back");
  assert.deepEqual([w.doc.touches, w.at("st-fallback") !== null, F.text(w.doc), w.log], [0, true, "", []]);
});

test("틀 시작: 아이폰 사파리 탭(standalone이 거짓)이면 홈 화면 안내만 그린다 — 저장 공간을 읽지 않는다", async () => {
  const touched = [];
  const spy = { getItem: k => { touched.push(k); return null; }, setItem: k => { touched.push(k); }, removeItem: k => { touched.push(k); } };
  const navigator = { standalone: false, storage: { persist: () => { touched.push("persist"); return Promise.resolve(true); } } };
  const w = await open({ storage: spy, hash: "#set", extra: { navigator } });
  assert.deepEqual([touched, w.at("st-fallback"), idsIn(w.at("st-main")), w.log], [[], null, ["st-main", "st-guide"], []]);
  assert.equal(F.text(w.at("st-guide")), C.T.GUIDE_HEAD + C.T.GUIDE_1 + C.T.GUIDE_2 + C.T.GUIDE_3);
  assert.deepEqual([F.byTag(w.doc, "input").length, F.byTag(w.doc, "a").length, F.byTag(w.doc, "button").length, F.text(w.at("st-head")), F.text(w.at("st-nav"))], [0, 0, 0, "", ""]);
  w.A.go("today");
  w.A.refresh("back");
  assert.deepEqual([touched, w.log, idsIn(w.at("st-main"))], [[], [], ["st-main", "st-guide"]]);
});

test("틀 시작: 파일은 실릴 때 다른 모듈을 만지지 않는다 — 어느 차례로 실어도 던지지 않고 문서도 그대로다", async () => {
  const w = F.world([...APP_FILES].reverse(), { storage: named() });
  assert.equal(w.doc.touches, 0);
  w.fire("DOMContentLoaded");
  await F.settle();
  assert.deepEqual([F.byTag(F.byId(w.doc, "st-nav"), "a").length, w.storage.data.size], [4, 1]);
});

test("틀 시작: PC(standalone이 없다)와 홈 화면 웹앱(참)에서는 안내가 없다", async () => {
  for (const standalone of [undefined, true]) {
    const w = await open({ standalone, storage: named() });
    assert.deepEqual([w.at("st-guide"), w.at("st-fallback"), F.byTag(w.at("st-nav"), "a").length, w.log], [null, null, 4, ["render today"]], String(standalone));
  }
});

test("틀 시작: 기기 이름이 없으면 어느 길에서든 이름부터 묻는다 — 꼴이 틀리면 경고, 맞으면 들어간다", async () => {
  const w = await open({ hash: "#set" });
  assert.deepEqual([idsIn(w.doc), w.log], [["st-head", "st-nav", "st-note", "st-main", "st-name", "st-name-input", "st-name-save", "st-name-warn"], []]);
  assert.deepEqual([F.text(F.byTag(w.at("st-name"), "label")[0]), F.byTag(w.at("st-name"), "label")[0].getAttribute("for"), F.text(w.at("st-name-save"))], [C.T.NAME_ASK, "st-name-input", C.T.NAME_SAVE]);
  const [input, save] = [w.at("st-name-input"), w.at("st-name-save")];
  w.A.go("week");                                                                        // 이름을 묻는 동안에는 길이 듣지 않는다
  w.doc.goHash("#week");
  F.type(input, "아홉글자기기이름임");
  F.press(save);
  assert.deepEqual([F.text(w.at("st-name-warn")), w.storage.data.size, w.log], [C.T.NAME_BAD, 0, []]);
  F.type(input, " 폰 ");
  F.key(input, "Enter", { isComposing: true });                                          // 한글을 짓는 중의 Enter는 저장이 아니다
  F.key(input, "a");
  assert.equal(w.storage.data.size, 0);
  F.key(input, "Enter");
  assert.deepEqual([w.storage.data.get(LS + "dev"), w.at("st-name"), w.log, F.text(w.at("st-head")), F.byTag(w.at("st-nav"), "a").length], ["폰", null, ["render week"], "10-13 화" + C.T.ST_LOCAL, 4]);
  F.press(save);                                                                         // 이미 들어왔다 — 다시 눌러도 한 번만 들어간다
  w.doc.goHash("#ask");
  assert.deepEqual(w.log, ["render week", "leave week", "render ask"]);
});

test("틀 시작: 저장 공간이 말을 듣지 않아도 이름을 받고 들어간다 — 상태 줄은 붉은 한 줄", async () => {
  const storage = F.fakeStorage();
  storage.failOn("macro-study");
  const w = await open({ storage });
  F.type(w.at("st-name-input"), "폰");
  F.press(w.at("st-name-save"));
  assert.deepEqual([F.text(w.at("st-status")), w.at("st-status").getAttribute("class"), w.log, w.A.ctx().dev, storage.data.size], [C.T.ST_STORE_FAIL, "st-status st-red", ["render today"], "폰", 0]);
});

test("틀 시작: 오래 두기를 청하되 기다리지 않고, 두 번 시작해도 한 번만 그린다", async () => {
  const w = await open({ storage: named(), persist: "hang" });
  w.A.start();
  w.fire("DOMContentLoaded");
  assert.deepEqual([w.log, F.byTag(w.at("st-nav"), "a").length, idsIn(w.at("st-head"))], [["render today"], 4, ["st-head", "st-date", "st-status"]]);
});

test("틀 길: 주소의 # 뒤 값으로 화면을 고르고 모르는 값은 오늘이다 — 이동 줄은 지금 길을 표시한다", async () => {
  const w = await open({ storage: named(), hash: "#week" });
  const nav = () => F.byTag(w.at("st-nav"), "a").map(a => [a.getAttribute("href"), a.getAttribute("data-k"), F.text(a), a.getAttribute("aria-current")]);
  assert.deepEqual(nav(), [["#today", "today", "오늘", null], ["#week", "week", "주간", "page"], ["#ask", "ask", "질문", null], ["#set", "set", "설정", null]]);
  F.press(F.byK(w.doc, "ask")[0]);
  assert.deepEqual([w.log, w.scope.location.hash, F.text(w.at("st-main")), nav().map(n => n[3])], [["render week", "leave week", "render ask"], "#ask", "ask 2026-10-13", [null, null, "page", null]]);
  w.doc.goHash("#nope");
  assert.deepEqual([w.log.slice(3), w.at("scr-today") !== null, w.at("scr-ask"), nav().map(n => n[3])], [["leave ask", "render today"], true, null, ["page", null, null, null]]);
  assert.deepEqual([(await open({ storage: named(), hash: "#__proto__" })).log, (await open({ storage: named(), hash: "" })).log], [["render today"], ["render today"]]);
});

test("틀 길: go는 주소를 바꾸고 그 화면을 새로 그린다 — 지금 길의 이름을 다시 눌러도 새로 그린다", async () => {
  const w = await open({ storage: named() });
  w.A.go("set");
  assert.deepEqual([w.scope.location.hash, w.log], ["#set", ["render today", "leave today", "render set"]]);
  F.press(F.byK(w.doc, "set")[0]);                                                       // 주소가 같아 hashchange는 오지 않는다
  assert.deepEqual(w.log.slice(3), ["leave set", "render set"]);
  w.A.go("nope");
  assert.deepEqual([w.scope.location.hash, w.log.slice(5)], ["#today", ["leave set", "render today"]]);
  F.press(F.byK(w.doc, "week")[0]);                                                      // 다른 길은 한 번만 그린다
  assert.deepEqual([w.log.slice(7), idsIn(w.at("st-main"))], [["leave today", "render week"], ["st-main", "scr-week"]]);
});

test("틀: ctx는 지금 시각 · 오늘 · 이번 주 · 지난주 · 보기 · 기기 이름 · 환경을 준다", async () => {
  const now = kstMs("2026-10-19T03:59:59");                                              // 월요일 새벽 — 아직 지난주 일요일이다
  const w = await open({ storage: named({ "m.2026-10": L1, months: '["2026-10"]' }), now, protocol: "http:" });
  const c = w.A.ctx();
  assert.deepEqual([c.nowMs, c.today, c.wk, c.lastWk, c.dev, c.view.recs.length, c.view.recs[0].text, c.view.bad, F.plain(c.env)],
    [now, "2026-10-18", "2026-10-12", "2026-10-05", "폰", 1, "하나", 0, { https: false, framed: false }]);
  assert.deepEqual([F.text(w.at("st-date")), w.log], ["10-18 일", ["render today"]]);
});

test("틀: 알림 한 줄은 문구 표의 글자로 쓰고 null이면 비운다 — 길을 바꾸면 지워진다", async () => {
  const w = await open({ storage: named() });
  const said = key => { w.A.note(key, { n: 2 }); return F.text(w.at("st-note")); };
  assert.deepEqual([said("SHARE_COPIED"), said("ST_QUEUE"), said(null), said("NOTE_BIG"), w.at("st-note").getAttribute("role")], ["복사했다", "올릴 것 2건", "", C.T.NOTE_BIG, "status"]);
  w.A.go("week");
  assert.equal(F.text(w.at("st-note")), "");
});

test("틀: 화면은 길 이름 넷으로만 들어오고, refresh · leave가 없는 화면도 돈다", async () => {
  const w = F.world(APP_FILES, { storage: named(), hash: "#week" });
  const A = w.scope.StudyApp;
  A.register("nope", { render: () => { throw new Error("x"); } });
  A.register("week", {});                                                                // 그리는 손이 없는 것은 받지 않는다
  A.register("week", null);
  A.register("ask", { render: root => { root.append("질문 화면"); } });
  w.fire("DOMContentLoaded");
  await F.settle();
  assert.deepEqual([F.text(F.byId(w.doc, "st-main")), F.byTag(F.byId(w.doc, "st-nav"), "a").length], ["", 4]);
  A.go("ask");
  A.refresh("back");
  A.go("today");
  A.go("ask");
  assert.equal(F.text(F.byId(w.doc, "st-main")), "질문 화면");
});

test("틀: 화면을 바꿀 때 녹음 모듈의 재생을 거둔다(있을 때만) — 새로 고칠 때는 두지 않는다", async () => {
  let stops = 0;
  const w = await open({ storage: named(), extra: { StudyRecorder: { stopPlayback: () => { stops += 1; } } } });
  w.A.refresh("back");
  assert.equal(stops, 1);
  w.A.go("week");
  assert.equal(stops, 2);
});

test("틀 상태 줄: 일곱 가지의 차례 — 저장 실패 > 열쇠 > 저장소 · 파일 > 멈춤 > 올릴 것 > 기기 전용 > 맞춤 시각", async () => {
  const q = JSON.stringify([OLD]);
  const line = async (seed, snap, breakIt) => {
    const storage = named(seed);
    const w = await open({ storage, extra: { StudySync: fakeSync([], snap).api } });
    if (breakIt) storage.failOn("macro-study");
    if (breakIt) w.scope.StudyStore.setFlag("rec", false);
    w.A.refresh("set");
    return F.text(w.at("st-status")) + " | " + w.at("st-status").getAttribute("class");
  };
  assert.equal(await line({ key: KEY, auth: "401", q }, { stop: "halt", code: 403 }, true), "이 기기에 저장하지 못함 | st-status st-red");
  assert.equal(await line({ key: KEY, auth: "401", pause: "1", q }, { stop: "auth" }), "열쇠 다시 넣기 | st-status");
  assert.deepEqual([await line({ key: KEY, pause: "1", q }, { stop: "missing" }), await line({ key: KEY, q }, { stop: "public" }), await line({ key: KEY, q }, { stop: "file" })],
    ["저장소를 찾지 못함 | st-status", "공개 상태 — 올리지 않습니다 | st-status", "기록 파일을 읽지 못함 | st-status"]);
  assert.deepEqual([await line({ key: KEY, pause: "1", q }, { stop: "paused" }), await line({ key: KEY, q }, { stop: "halt", code: 403 })], ["맞춤 멈춤 | st-status", "맞춤 멈춤 — 오류 403 | st-status"]);
  assert.deepEqual([await line({ key: KEY, q }, {}), await line({ key: KEY, q }, { failedThisOpen: true }), await line({ key: KEY, q: JSON.stringify([L1]) }, { failedThisOpen: true })],
    ["올릴 것 1건 | st-status", "올릴 것 1건 | st-status st-amber", "올릴 것 1건 | st-status"]);         // 호박색은 어제 이전의 줄이 밀려 있고 이번에 연 뒤 실패했을 때만
  assert.equal(await line({ auth: "401", pause: "1", q }, { stop: "halt", failedThisOpen: true }), "이 기기에만 저장 | st-status");
  assert.deepEqual([await line({ key: KEY, sync: JSON.stringify({ at: F.T0 + 60000 }) }, {}), await line({ key: KEY }, {})], ["맞춤 08:31 | st-status", "맞춤 전 | st-status"]);
});

// ── app.js: 쓰기 한 길 · 맞춤 고리 · 돌아옴 ──
const MIN = { mark: "min", sec: 120, rec: 0, stuck: "" };

test("틀 쓰기: 줄을 만들어 기기에 먼저 쓰고 → 화면을 새로 고치고 → 맞춤을 청한다", async () => {
  const log = [];
  const sync = fakeSync(log);
  const w = await open({ storage: named({ key: KEY }), extra: { StudySync: sync.api } }, log);
  assert.deepEqual([log, typeof sync.onChange, F.text(w.at("st-status"))], [["sync init", "render today", "sync open"], "function", C.T.ST_SYNC_WAIT]);
  const r = w.A.write("next", { text: "  기간 프리미엄 " });
  assert.deepEqual([r.ok, r.code, r.stored, r.obj.text, r.obj.d, r.obj.dev, /^\d{17}-폰-[a-z0-9]{4}$/.test(r.obj.id)], [true, null, true, "기간 프리미엄", "2026-10-13", "폰", true]);
  assert.deepEqual(log.slice(3), ["refresh today write 1", "sync save"]);                  // 새로 고칠 때 그 줄은 이미 보기에 있다
  assert.deepEqual([w.scope.StudyStore.monthLines("2026-10").length, w.scope.StudyStore.queue().length, F.text(w.at("st-status"))], [1, 1, "올릴 것 1건"]);
  w.A.requestSync("manual");
  assert.deepEqual([log.slice(5), w.A.write("day", MIN).obj.id === r.obj.id], [["sync manual"], false]);
});

test("틀 쓰기: 꼴이 맞지 않으면 적지 않고 코드를 돌려준다 — 화면도 맞춤도 그대로다", async () => {
  const log = [];
  const w = await open({ storage: named(), extra: { StudySync: fakeSync(log).api } }, log);
  const size = w.storage.data.size;
  assert.deepEqual(F.plain(w.A.write("next", { text: "   " })), { ok: false, code: "field", obj: null, stored: false });
  assert.deepEqual([w.A.write("note", {}).code, w.A.write("day", { ...MIN, stuck: KEY }).code, w.A.write("rest", { on: "2026-10-13" }).code, w.A.write("day").code], ["kind", "secret", "rule", "keys"]);
  assert.deepEqual([log, w.storage.data.size], [["sync init", "render today", "sync open"], size]);
});

test("틀 쓰기: 새벽에 쓴 줄은 전날의 것이다 — 10-01 03:30에 찍은 도장은 9월 파일로 간다", async () => {
  const w = await open({ storage: named(), now: kstMs("2026-10-01T03:30:00") });
  const r = w.A.write("day", MIN);
  assert.deepEqual([r.obj.d, r.obj.t, F.plain(w.scope.StudyStore.months()), F.text(w.at("st-date"))], ["2026-09-30", "2026-10-01T03:30:00+09:00", ["2026-09"], "09-30 수"]);
});

test("틀 쓰기: 기기 저장이 실패해도 줄은 남고(stored만 거짓) 곧바로 올리기를 청한다 — 상태 줄은 붉다", async () => {
  const log = [];
  const storage = named({ key: KEY });
  const w = await open({ storage, extra: { StudySync: fakeSync(log).api } }, log);
  storage.failOn(/\.(m\.|q$)/);
  const r = w.A.write("day", MIN);
  assert.deepEqual([r.ok, r.stored, log.slice(3), w.A.ctx().view.recs.length], [true, false, ["refresh today write 1", "sync store-fail"], 1]);
  assert.deepEqual([F.text(w.at("st-status")), w.at("st-status").getAttribute("class")], [C.T.ST_STORE_FAIL, "st-status st-red"]);
});

test("틀: 맞춤 모듈이 없으면 맞춤 요청은 아무 일도 하지 않는다 — 바깥 요청 0번", async () => {
  const w = await open({ storage: named({ key: KEY, owner: "owner", repo: "repo" }) });
  assert.equal(w.A.write("day", MIN).stored, true);
  w.A.requestSync("manual");
  w.fire("visibilitychange", "visible");
  await F.settle();
  assert.deepEqual([w.net.calls.length, w.net.unexpected, F.text(w.at("st-status")), w.log], [0, 0, "올릴 것 1건", ["render today", "refresh today write 1", "refresh today back 1"]]);
});

test("틀: 맞춤 · 녹음 모듈이 던져도 화면은 돌고 도장은 찍힌다", async () => {
  const boom = () => { throw new Error("x"); };
  const w = await open({ storage: named(), extra: { StudySync: { init: boom, request: boom, snapshot: boom }, StudyRecorder: { stopPlayback: boom } } });
  assert.deepEqual([[...w.log], w.A.write("day", MIN).stored], [["render today"], true]);
  w.A.go("week");
  w.fire("visibilitychange", "visible");
  assert.deepEqual([w.log.slice(1), F.text(w.at("st-status"))], [["refresh today write 1", "leave today", "render week", "refresh week back 1"], C.T.ST_LOCAL]);
});

test("틀 맞춤이 알릴 때: 상태 줄과 화면을 맞춤으로 새로 고치고, 사본이 크면 알림 한 줄", async () => {
  const log = [];
  const sync = fakeSync(log);
  const w = await open({ storage: named({ key: KEY }), extra: { StudySync: sync.api } }, log);
  w.scope.StudyStore.absorb("2026-10", [L1]);                                              // 다른 기기의 줄을 받았다
  sync.snap = { ...sync.snap, stop: "missing" };
  sync.onChange(sync.snap, { changed: true, big: false });
  assert.deepEqual([log.slice(3), F.text(w.at("st-status")), F.text(w.at("st-note"))], [["refresh today sync 1"], C.T.ST_REPO_MISSING, ""]);
  sync.onChange(sync.snap, { changed: false, big: true });
  sync.onChange(sync.snap);
  assert.deepEqual([log.slice(4), F.text(w.at("st-note"))], [["refresh today sync 1", "refresh today sync 1"], C.T.NOTE_BIG]);
});

test("틀 돌아옴: 날짜가 같으면 맞춤이 바꾸는 자리만, 날짜가 바뀌었으면 오늘 화면을 새로 — 그 뒤 맞춤을 청한다", async () => {
  const log = [];
  const w = await open({ storage: named(), hash: "#week", now: kstMs("2026-10-13T23:00:00"), extra: { StudySync: fakeSync(log).api } }, log);
  w.clock.set(kstMs("2026-10-14T03:59:59"));
  w.fire("visibilitychange", "hidden");
  assert.deepEqual(log, ["sync init", "render week", "sync open"]);                        // 가려질 때는 아무 일도 없다
  w.fire("visibilitychange", "visible");
  assert.deepEqual([log.slice(3), w.scope.location.hash, F.text(w.at("st-date"))], [["refresh week back 0", "sync back"], "#week", "10-13 화"]);
  w.clock.set(kstMs("2026-10-14T04:00:00"));                                               // 공부 날짜가 바뀌었다
  w.fire("visibilitychange", "visible");
  assert.deepEqual([log.slice(5), w.scope.location.hash, F.text(w.at("st-date")), F.text(w.at("st-main"))], [["leave week", "render today", "sync back"], "#today", "10-14 수", "today 2026-10-14"]);
  w.fire("visibilitychange", "visible");
  assert.deepEqual(log.slice(8), ["refresh today back 0", "sync back"]);
});

test("틀: 틀이 다 뜨기 전(틀 안 · 홈 화면 안내 · 이름 묻기)에는 돌아옴도 쓰기도 맞춤도 듣지 않는다", async () => {
  const not = { ok: false, code: "dev", obj: null, stored: false };
  for (const opts of [{ framed: true, storage: named() }, { standalone: false, storage: named() }, {}]) {
    const log = [];
    const w = await open({ ...opts, extra: { StudySync: fakeSync(log).api } }, log);
    const size = w.storage.data.size;
    w.fire("visibilitychange", "visible");
    w.fire("hashchange");
    assert.deepEqual([F.plain(w.A.write("day", MIN)), log, w.storage.data.size], [not, [], size], JSON.stringify(Object.keys(opts)));
  }
});

test("틀: 약속된 이름이 모두 있고 그 밖의 것은 없다", () => {
  assert.deepEqual(Object.keys(appOf()).sort(), ["VERSION", "_", "ctx", "el", "env", "flag", "go", "note", "rand4", "refresh", "register", "reload", "requestSync", "share", "start", "write"]);
});

// ── 뼈대 문서(index.html)가 싣는 그대로 ──
test("뼈대: index.html이 싣는 차례대로 실어 시작한다 — 틀의 파일 넷이 그 차례로 있고 화면은 틀 뒤에 실리며, 파일마다 전역 이름을 하나씩 단다", async () => {
  const listed = F.scripts();
  assert.deepEqual([listed.filter(name => APP_FILES.includes(name)), listed.indexOf("app.js") < listed.indexOf("today.js")], [APP_FILES, true]);
  const w = await F.boot({ storage: named() });
  assert.equal(Object.keys(w.scope).filter(k => k.startsWith("Study")).length, listed.length);
  const at = id => F.byId(w.doc, id);
  assert.deepEqual([F.text(at("st-head")), F.byTag(at("st-nav"), "a").length, at("st-fallback")], ["10-13 화" + C.T.ST_LOCAL, 4, null]);
  assert.equal(w.scope.StudyApp.write("day", MIN).stored, true);
  F.press(F.byK(w.doc, "set")[0]);
  assert.deepEqual([w.scope.location.hash, w.net.calls.length, w.net.unexpected, F.text(at("st-status"))], ["#set", 0, 0, C.T.ST_LOCAL]);
});
