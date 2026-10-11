"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const F = require("./study_fakes.cjs");

const vm = require("node:vm");

// 가짜 묶음(study_fakes.cjs) 자체의 테스트 — 가짜가 약속대로 움직여야 그 위의 화면 테스트를 믿을 수 있다. 지어낸 글만 쓴다.
// 돌리기: node --test scripts/test_study_fakes.cjs
const inside = (w, code) => vm.runInContext(code, w.scope);      // 문맥 안에서 한 줄 돌린다(가짜 자체를 볼 때만 쓴다)

// ── 가짜 묶음: 시계 · 저장 공간 · 통신 ──
test("가짜: 기준 시각 T0는 KST 2026-10-13 08:30이고, plain은 값을 옮긴다", () => {
  assert.equal(new Date(F.T0 + 9 * 3600000).toISOString(), "2026-10-13T08:30:00.000Z");
  assert.deepEqual(F.plain({ a: [1, { b: "가" }] }), { a: [1, { b: "가" }] });
  assert.equal(F.plain(undefined), undefined);
});

test("가짜 저장 공간: 글자로 넣고, failOn에 걸린 이름의 쓰기만 예외를 낸다", () => {
  const s = F.fakeStorage({ "a.b": "1" });
  assert.deepEqual([s.getItem("a.b"), s.getItem("없음")], ["1", null]);
  s.setItem("n", 7);
  assert.equal(s.getItem("n"), "7");
  s.failOn(/^a\./);
  assert.throws(() => s.setItem("a.b", "2"), { name: "QuotaExceededError" });
  assert.equal(s.data.get("a.b"), "1");
  s.setItem("n", "8");
  s.failOn(null);
  s.setItem("a.b", "2");
  s.removeItem("n");
  assert.deepEqual([...s.data], [["a.b", "2"]]);
  assert.deepEqual([typeof s.key, typeof s.length], ["undefined", "undefined"]);
});

test("가짜 시계: advance가 그 사이의 때맞춤을 때의 차례대로 울린다", () => {
  const c = F.fakeClock(1000);
  const seen = [];
  c.api.setTimeout(() => seen.push(["b", c.now()]), 300);
  c.api.setTimeout(() => { seen.push(["a", c.now()]); c.api.setTimeout(() => seen.push(["c", c.now()]), 50); }, 100);
  const every = c.api.setInterval(() => seen.push(["i", c.now()]), 250);
  c.api.clearTimeout(c.api.setTimeout(() => seen.push(["x", c.now()]), 10));
  c.advance(500);
  assert.deepEqual(seen, [["a", 1100], ["c", 1150], ["i", 1250], ["b", 1300], ["i", 1500]]);
  assert.deepEqual([c.now(), c.pending()], [1500, 1]);
  c.api.clearInterval(every);
  c.set(5000);
  assert.deepEqual([c.now(), c.pending()], [5000, 0]);
});

test("가짜 통신: 준비한 응답을 차례로 주고, 요청의 꼴을 남기고, 떨어지면 unexpected를 센다", async () => {
  const net = F.fakeNet([{ status: 200, body: { n: 1 }, headers: { ETag: "x" } }, new Error("offline"), call => ({ status: 404, body: call.method })]);
  const init = { method: "PUT", headers: { Accept: "x" }, body: "{}", cache: "no-store", credentials: "omit", referrerPolicy: "no-referrer", redirect: "error" };
  const first = await net.fetch("/a", init);
  assert.deepEqual([first.ok, await first.json(), first.headers.get("etag"), first.headers.get("x")], [true, { n: 1 }, "x", null]);
  await assert.rejects(net.fetch("/b"), /offline/);
  const third = await net.fetch("/c");
  assert.deepEqual([third.status, third.ok, await third.text()], [404, false, "GET"]);
  assert.deepEqual(net.calls[0], { url: "/a", ...init });
  assert.deepEqual([net.calls[1].body, net.calls[1].method, net.unexpected], [null, "GET", 0]);
  await assert.rejects(net.fetch("/d"), /준비하지 않은 요청/);
  assert.equal(net.unexpected, 1);
});

test("가짜 통신: hang은 끊길 때까지 끝나지 않고, 끊으면 AbortError로 거절한다", async () => {
  const net = F.fakeNet([]);
  net.push("hang");
  const ctl = new AbortController();
  let state = "wait";
  const done = net.fetch("/h", { signal: ctl.signal }).then(() => { state = "ok"; }, e => { state = e.name; });
  await F.settle();
  assert.equal(state, "wait");
  ctl.abort();
  await done;
  assert.equal(state, "AbortError");
});

// ── 가짜 묶음: 문서 · 누름 · 싣기 ──

test("가짜 문서: 뼈대 다섯이 미리 있고, 목록에 없는 대입은 던진다", () => {
  const w = F.world([]);
  assert.deepEqual(F.SKELETON, ["st-fallback", "st-head", "st-nav", "st-note", "st-main"]);
  assert.deepEqual(F.SKELETON.map(id => F.byId(w.doc, id).tag), ["p", "header", "nav", "p", "main"]);
  assert.deepEqual([w.doc.getElementById("st-note").getAttribute("role"), w.doc.getElementById("없음"), w.doc.touches], ["status", null, 0]);
  const node = w.doc.createElement("div");
  assert.throws(() => { node.hidden = true; }, TypeError);
  assert.throws(() => { node.onclick = () => {}; }, TypeError);
  assert.deepEqual([node.classList, node.style, w.doc.touches], [undefined, undefined, 1]);
});

test("가짜 문서: 속성 · 자식 · 글자 — 꺾쇠가 든 글자는 요소가 되지 않는다", () => {
  const w = F.world([]);
  const main = F.byId(w.doc, "st-main");
  const box = w.doc.createElement("div");
  const btn = w.doc.createElement("button");
  box.setAttribute("class", "st-row st-dim");
  box.setAttribute("data-k", "queue");
  box.append("올릴 것 ", btn, "<b>1</b>");
  btn.append("건");
  main.append(box);
  assert.deepEqual([box.getAttribute("class"), box.hasAttribute("id"), box.getAttribute("id")], ["st-row st-dim", false, null]);
  assert.deepEqual([F.text(main), F.all(main).length], ["올릴 것 건<b>1</b>", 3]);
  assert.equal(F.byClass(w.doc, "st-dim")[0], box);
  assert.equal(F.byK(w.doc, "queue")[0], box);
  assert.equal(F.byTag(main, "button")[0], btn);
  F.byId(w.doc, "st-head").append(btn);                           // 옮겨 붙이면 앞의 자리에서 빠진다
  box.removeAttribute("data-k");
  assert.deepEqual([F.text(box), F.byK(w.doc, "queue").length], ["올릴 것 <b>1</b>", 0]);
  box.textContent = "새 글";
  assert.deepEqual([F.text(box), box.kids.length], ["새 글", 1]);
  main.replaceChildren();
  btn.remove();
  assert.deepEqual([box.parent, F.byTag(w.doc, "button").length, F.text(w.doc)], [null, 0, ""]);
});

test("가짜 문서: 입력의 value · checked는 속성에서 시작하고, 한 번 쓰면 속성과 떨어진다", () => {
  const w = F.world([]);
  const input = w.doc.createElement("input");
  const box = w.doc.createElement("input");
  input.setAttribute("value", "처음");
  assert.deepEqual([input.value, box.value, box.checked], ["처음", "", false]);
  input.value = "고침";
  input.setAttribute("value", "다시");
  box.setAttribute("checked", "");
  assert.deepEqual([input.value, box.checked], ["고침", true]);
  box.checked = false;
  assert.deepEqual([box.checked, box.hasAttribute("checked")], [false, true]);
  input.focus();
  w.doc.createElement("div").focus();                             // 초점을 받지 못하는 요소
  assert.equal(w.doc.activeElement, input);
});

test("가짜 누름: press · type · key · check가 사건을 울리고, disabled는 눌리지 않는다", () => {
  const w = F.world([]);
  const main = F.byId(w.doc, "st-main");
  const [btn, input, box, fold, head] = ["button", "input", "input", "details", "summary"].map(tag => w.doc.createElement(tag));
  box.setAttribute("type", "checkbox");
  fold.append(head);
  main.append(btn, input, box, fold);
  const seen = [];
  main.addEventListener("click", ev => seen.push("main:" + ev.target.tag + ">" + ev.currentTarget.tag));
  btn.addEventListener("click", ev => seen.push("btn:" + ev.type));
  input.addEventListener("input", ev => seen.push("input:" + ev.target.value));
  input.addEventListener("keydown", ev => seen.push("key:" + ev.key + ":" + ev.isComposing));
  box.addEventListener("change", ev => seen.push("change:" + ev.target.checked));
  fold.addEventListener("toggle", () => seen.push("toggle:" + fold.hasAttribute("open")));
  F.press(btn);
  F.type(input, "한 줄");
  F.key(input, "Enter");
  F.key(input, "Enter", { isComposing: true });
  F.check(box, true);
  F.press(box);
  F.press(head);
  btn.setAttribute("disabled", "");
  F.press(btn);
  assert.deepEqual(seen, ["btn:click", "main:button>main", "input:한 줄", "key:Enter:false", "key:Enter:true",
    "main:input>main", "change:true", "main:input>main", "change:false", "main:summary>main", "toggle:true"]);
});

test("가짜 누름: 이동 줄의 링크를 누르면 주소의 #이 바뀌고 hashchange가 한 번 울린다", () => {
  const w = F.world([], { hash: "#today" });
  const a = w.doc.createElement("a");
  a.setAttribute("href", "#week");
  let n = 0;
  w.scope.addEventListener("hashchange", () => { n += 1; });
  F.press(a);
  F.press(a);                                                     // 같은 곳이면 울리지 않는다
  assert.deepEqual([w.scope.location.hash, n], ["#week", 1]);
  w.scope.history.replaceState(null, "", "#ask");                 // 스크립트가 바꾼 주소는 사건을 울리지 않는다
  a.addEventListener("click", ev => ev.preventDefault());
  F.press(a);
  assert.deepEqual([w.scope.location.hash, n], ["#ask", 1]);
});

test("가짜 세계: 시계 · 난수 · 환경 값이 주입되고, 준비하지 않은 통신은 unexpected로 센다", async () => {
  const w = F.world([], { standalone: false, protocol: "http:", framed: true, share: "ok", clip: "ok", persist: true, extra: { StudySync: { tag: "대역" } } });
  let rang = 0;
  inside(w, "(fn) => setTimeout(fn, 250)")(() => { rang = inside(w, "Date.now()"); });
  w.clock.advance(1000);
  assert.deepEqual([rang, inside(w, "Date.now()")], [F.T0 + 250, F.T0 + 1000]);
  assert.deepEqual(F.plain(inside(w, "[navigator.standalone, location.protocol, window.top !== window.self, window === self, StudySync.tag]")), [false, "http:", true, true, "대역"]);
  await inside(w, "navigator.share({ text: '글' }).then(() => navigator.clipboard.writeText('복사'))");
  assert.deepEqual([w.shared, w.copied, await inside(w, "navigator.storage.persist()")], [["글"], ["복사"], true]);
  const draw = "[Array.from(crypto.getRandomValues(new Uint8Array(4))), Array.from(crypto.getRandomValues(new Uint8Array(4)))]";
  const rand = F.plain(inside(w, draw));
  assert.notDeepEqual(rand[0], rand[1]);
  assert.deepEqual(rand, F.plain(inside(F.world([]), draw)));     // 새 세계는 같은 차례로 다시 나온다
  await assert.rejects(inside(w, "fetch('/x')"), /준비하지 않은 요청/);
  inside(w, "location.reload()");
  assert.deepEqual([w.net.unexpected, w.reloads], [1, 1]);
});

test("가짜 세계: 기본값은 PC · https · 공유 창 없음 · 틀 밖이고, 거절과 끝나지 않는 약속을 고를 수 있다", async () => {
  const seen = "[typeof navigator.standalone, location.protocol, location.hash, typeof navigator.share, typeof navigator.clipboard, typeof navigator.storage, window.top === window.self, document.visibilityState]";
  assert.deepEqual(F.plain(inside(F.world([]), seen)), ["undefined", "https:", "", "undefined", "undefined", "undefined", true, "visible"]);
  const w = F.world([], { share: "cancel", clip: "deny", persist: "deny" });
  const names = await inside(w, "Promise.all([navigator.share({ text: 'x' }), navigator.clipboard.writeText('x'), navigator.storage.persist()].map(p => p.catch(e => e.name)))");
  assert.deepEqual(F.plain(names), ["AbortError", "NotAllowedError", "NotAllowedError"]);
  let done = false;
  inside(F.world([], { share: "hang" }), "navigator.share({ text: 'x' })").then(() => { done = true; }, () => { done = true; });
  await F.settle();
  assert.equal(done, false);                                      // 닫히지 않는 공유 창
});

test("가짜 세계: fire가 문서와 창의 처리기를 울리고, boot는 뼈대의 script 차례로 싣고 시작한다", async () => {
  const w = F.world([]);
  const seen = [];
  w.doc.addEventListener("visibilitychange", () => seen.push("doc:" + w.doc.visibilityState));
  w.scope.addEventListener("visibilitychange", () => seen.push("win"));
  w.fire("visibilitychange", "hidden");
  w.fire("visibilitychange");
  assert.deepEqual(seen, ["doc:hidden", "win", "doc:visible", "win"]);
  const html = '<head><link rel="stylesheet" href="study.css?v=1"></head><body><script src="core.js?v=1"></script>\n<script src="store.js?v=1"></script></body>';
  assert.deepEqual(F.scripts(html), ["core.js", "store.js"]);
  const booted = await F.boot({ html: "<body><p id=\"st-fallback\"></p></body>", now: 5 });
  assert.deepEqual([booted.clock.now(), booted.reloads, F.all(booted.doc).length], [5, 0, 6]);
});

// ── 화면 파일 싣기 ──
test("가짜 세계: boot가 뼈대에 적힌 화면 파일을 차례로 싣는다(문서는 건드리지 않는다)", async () => {
  const w = await F.boot({ html: '<script src="core.js?v=1"></script>' });
  assert.deepEqual([w.scope.StudyCore.V, w.doc.touches, w.net.unexpected], [1, 0, 0]);
  assert.equal(inside(w, "typeof StudyCore.studyDate"), "function");
});

// ── 지어낸 줄 ──
test("가짜 줄: line은 core.js의 makeLine으로 만들고, 꼴이 맞지 않으면 던진다", () => {
  assert.equal(F.line("next", { text: "기간 프리미엄" }),
    '{"v":1,"id":"20261012233000000-폰-k3f9","k":"next","d":"2026-10-13","t":"2026-10-13T08:30:00+09:00","dev":"폰","text":"기간 프리미엄"}');
  const other = JSON.parse(F.line("fix", { ref: "20261012233000000-폰-k3f9", hide: true }, { ms: F.T0 + 61000, dev: "PC", rand: "zz00" }));
  assert.deepEqual([other.id, other.dev, other.t], ["20261012233101000-PC-zz00", "PC", "2026-10-13T08:31:01+09:00"]);
  assert.throws(() => F.line("next", { text: "" }), /line: next 줄을 만들지 못했다 — field/);
  assert.throws(() => F.line("note", {}), /kind/);
});

// ── 맞춤의 가짜 ── 가짜 열쇠와 기록 저장소의 응답 본문
const fs = require("node:fs");
const path = require("node:path");

test("가짜 열쇠: 한 글자를 64번 되풀이한 것이다 — 열쇠 꼴을 지나고, 그 글자열은 테스트 소스 어디에도 적혀 있지 않다", () => {
  assert.deepEqual([F.KEY.length, new Set(F.KEY).size, F.world(["core.js"]).scope.StudyCore.keyShape(F.KEY)], [64, 1, true]);
  const sources = fs.readdirSync(__dirname).filter(name => /^(?:test_)?study_\w+\.cjs$/.test(name));
  assert.deepEqual([sources.includes("study_fakes.cjs"), sources.filter(name => fs.readFileSync(path.join(__dirname, name), "utf8").includes(F.KEY))], [true, []]);
});

test("가짜 응답 ghFile: base64에 60자마다 줄바꿈이 들어가고 끝에도 붙는다 — 풀면 한글이 그대로고, over로 칸을 바꾼다", () => {
  const text = "가나다 😀 abc\n".repeat(9);
  const body = F.ghFile(text, "s1");
  const rows = body.content.split("\n");
  assert.deepEqual([rows.pop(), rows.length > 2, rows.slice(0, -1).every(row => row.length === 60), rows[rows.length - 1].length <= 60], ["", true, true, true]);
  assert.equal(Buffer.from(body.content, "base64").toString("utf8"), text);
  assert.deepEqual([body.type, body.encoding, body.size, body.sha], ["file", "base64", Buffer.byteLength(text), "s1"]);
  const odd = F.ghFile("x", "s1", { size: 700000, encoding: "none", content: "" });
  assert.deepEqual([F.ghFile("", "s0").content, F.ghFile("", "s0").size, odd.size, odd.encoding, odd.content, odd.sha], ["", 0, 700000, "none", "", "s1"]);
});

test("가짜 응답 ghRepo: 비공개이고 Pages가 꺼져 있다 — over로 칸을 바꾼다", () => {
  assert.deepEqual([F.ghRepo(), F.ghRepo({ private: false }), F.ghRepo({ has_pages: true, name: "repo" })],
    [{ private: true, has_pages: false }, { private: false, has_pages: false }, { private: true, has_pages: true, name: "repo" }]);
});

// ── 녹음의 가짜 ── 가짜 마이크 · 녹음기 · 화면 켜 두기 · 재생 주소와 가짜 IndexedDB
const mediaWorld = opts => { const media = F.fakeMedia(opts); return { media, w: F.world([], { media }) }; };
const seenBy = promise => { const seen = []; promise.then(v => seen.push(["ok", v]), err => seen.push(["no", err.name])); return seen; };

test("가짜 마이크: 허용 · 거절 · 마이크 없음 · 끝나지 않음 · 나중에 답함을 고른다 — 청한 것을 적고, 트랙을 닫으면 live가 준다", async () => {
  const { media, w } = mediaWorld();
  const stream = await w.scope.navigator.mediaDevices.getUserMedia({ audio: true });
  assert.deepEqual([media.asks, media.streams.length, stream.getTracks().map(t => [t.kind, t.readyState]), media.live()], [[{ audio: true }], 1, [["audio", "live"]], 1]);
  stream.getTracks()[0].stop();
  assert.deepEqual([stream.getTracks()[0].readyState, media.live()], ["ended", 0]);
  const ask = opts => seenBy(mediaWorld(opts).w.scope.navigator.mediaDevices.getUserMedia({ audio: true }));
  const [deny, error, hang] = [ask({ mic: "deny" }), ask({ mic: "error" }), ask({ mic: "hang" })];
  const held = mediaWorld({ mic: "hold" });
  const late = seenBy(held.w.scope.navigator.mediaDevices.getUserMedia({ audio: true }));
  await F.settle();
  assert.deepEqual([deny, error, hang, late, held.media.asks.length], [[["no", "NotAllowedError"]], [["no", "NotFoundError"]], [], [], 1]);
  held.media.answer("ok");
  await F.settle();
  assert.deepEqual([late.length, late[0][0], held.media.live()], [1, "ok", 1]);
  const bare = mediaWorld({ mic: "none", recorder: "none", wake: "none" }).w.scope;
  assert.deepEqual([bare.navigator.mediaDevices, bare.MediaRecorder, bare.navigator.wakeLock], [undefined, undefined, undefined]);
});

test("가짜 녹음기: 받는 형식을 답하고, 돈 시간만큼의 덩어리를 stop 뒤에 내놓는다 — 빈 파일 · 종료 사건 없음 · 만들지 못함을 고른다", async () => {
  const run = async (opts, ms = 30000) => {
    const { media, w } = mediaWorld(opts);
    const rec = new w.scope.MediaRecorder({}, { mimeType: media.types[0], audioBitsPerSecond: 64000 });
    const seen = [];
    rec.addEventListener("dataavailable", ev => seen.push(["data", ev.data.size, ev.data.type]));
    rec.addEventListener("stop", () => seen.push(["stop"]));
    rec.start();
    w.clock.advance(ms);
    rec.stop();
    await F.settle();
    return { rec, seen, media, w };
  };
  const ok = await run({});
  assert.deepEqual([ok.seen, ok.rec.state, ok.rec.options, ok.media.recorders.length], [[["data", 240000, "audio/mp4"], ["stop"]], "inactive", { mimeType: "audio/mp4", audioBitsPerSecond: 64000 }, 1]);
  assert.throws(() => ok.rec.stop(), { name: "InvalidStateError" });
  assert.deepEqual([(await run({ recorder: "empty" })).seen, (await run({ recorder: "nostop" })).seen, (await run({ types: ["audio/webm;codecs=opus"], rate: 1000 }, 2000)).seen],
    [[["data", 0, "audio/mp4"], ["stop"]], [], [["data", 2000, "audio/webm;codecs=opus"], ["stop"]]]);
  const R = ok.w.scope.MediaRecorder;
  assert.deepEqual([R.isTypeSupported("audio/mp4"), R.isTypeSupported("audio/webm;codecs=opus")], [true, false]);
  assert.throws(() => new (mediaWorld({ recorder: "throw" }).w.scope.MediaRecorder)({}), { name: "NotSupportedError" });
  const blob = new ok.w.scope.Blob([{ size: 3 }, { size: 4 }], { type: "audio/mp4" });
  assert.deepEqual([blob.size, blob.type, new ok.w.scope.Blob([]).size], [7, "audio/mp4", 0]);
});

test("가짜 화면 켜 두기 · 재생 주소: 잠금은 놓으면 표시가 남고, 주소는 내준 것과 거둔 것을 적는다", async () => {
  const { media, w } = mediaWorld();
  const lock = await w.scope.navigator.wakeLock.request("screen");
  assert.deepEqual([media.locks.length, lock.released], [1, false]);
  await lock.release();
  assert.equal(media.locks[0].released, true);
  const asked = opts => seenBy(mediaWorld(opts).w.scope.navigator.wakeLock.request("screen"));
  const [deny, hang] = [asked({ wake: "deny" }), asked({ wake: "hang" })];
  await F.settle();
  assert.deepEqual([deny, hang], [[["no", "NotAllowedError"]], []]);
  const urls = [w.scope.URL.createObjectURL({ size: 1 }), w.scope.URL.createObjectURL({ size: 2 })];
  w.scope.URL.revokeObjectURL(urls[0]);
  assert.deepEqual([urls, media.urls, media.revoked], [["blob:study/1", "blob:study/2"], urls, ["blob:study/1"]]);
  w.scope.navigator.mediaDevices.getUserMedia({ audio: true });
  assert.deepEqual(media.log, ["wake", "url", "url", "revoke", "mic"]);                    // 한 일의 차례가 남는다
});

// 가짜 IndexedDB를 화면 코드가 쓰는 꼴 그대로 부른다: 열고 → 트랜잭션 하나에서 일 하나 → 끝나면 답
function idbDo(scope, mode, job) {
  return new Promise((resolve, reject) => {
    const open = scope.indexedDB.open("db", 1);
    open.addEventListener("upgradeneeded", () => open.result.createObjectStore("box", { keyPath: "id" }));
    open.addEventListener("error", () => reject(open.error));
    open.addEventListener("success", () => {
      const tx = open.result.transaction("box", mode);
      const req = job(tx.objectStore("box"));
      tx.addEventListener("complete", () => resolve(req.result));
      tx.addEventListener("error", () => reject(tx.error));
    });
  });
}

test("가짜 IndexedDB: 넣고 · 꺼내고 · 모두 읽고 · 지우고 · 비운다 — 같은 것을 두 world에 넘기면 남아 있다", async () => {
  const idb = F.fakeIdb();
  const w = F.world([], { idb });
  assert.equal(await idbDo(w.scope, "readwrite", s => s.put({ id: "a", n: 1 })), "a");
  await idbDo(w.scope, "readwrite", s => s.put({ id: "b", n: 2 }));
  await idbDo(w.scope, "readwrite", s => s.put({ id: "a", n: 3 }));
  assert.deepEqual([await idbDo(w.scope, "readonly", s => s.get("a")), await idbDo(w.scope, "readonly", s => s.get("없음")), await idbDo(w.scope, "readonly", s => s.getAll())],
    [{ id: "a", n: 3 }, undefined, [{ id: "a", n: 3 }, { id: "b", n: 2 }]]);
  assert.deepEqual(idb.log.slice(0, 5), ["open db v1", "store box keyPath=id", "put a", "open db v1", "put b"]);   // 저장소는 처음 열 때 한 번만 만든다
  const again = F.world([], { idb });
  await idbDo(again.scope, "readwrite", s => s.delete("a"));
  assert.deepEqual([[...idb.rows.keys()], idb.log.filter(row => row.startsWith("store")).length], [["b"], 1]);
  await idbDo(again.scope, "readwrite", s => s.clear());
  assert.equal(idb.rows.size, 0);
  assert.equal(F.world([], { idb: F.fakeIdb({ none: true }) }).scope.indexedDB, undefined);
});

test("가짜 IndexedDB: 열기 · 쓰기 · 읽기를 따로 실패시키거나 끝나지 않게 한다 — 실패한 쓰기는 하나도 들어가지 않는다", async () => {
  const run = (opts, mode, job) => { const idb = F.fakeIdb(opts); return { idb, seen: seenBy(idbDo(F.world([], { idb }).scope, mode, job)) }; };
  const put = s => s.put({ id: "a" });
  const cases = [run({ open: "fail" }, "readwrite", put), run({ open: "hang" }, "readwrite", put), run({ write: "fail" }, "readwrite", put), run({ write: "hang" }, "readwrite", put),
    run({ read: "fail" }, "readonly", s => s.getAll()), run({ read: "hang" }, "readonly", s => s.getAll()), run({ read: "fail" }, "readwrite", put)];
  await F.settle();
  assert.deepEqual(cases.map(c => [c.seen, c.idb.rows.size]),
    [[[["no", "UnknownError"]], 0], [[], 0], [[["no", "QuotaExceededError"]], 0], [[], 0], [[["no", "QuotaExceededError"]], 0], [[], 0], [[["ok", "a"]], 1]]);
  const idb = F.fakeIdb({ write: "hang" });
  const w = F.world([], { idb });
  const first = seenBy(idbDo(w.scope, "readwrite", put));
  await F.settle();
  idb.opts.write = "ok";                                                                  // 도중에 고쳐도 된다 — 그 뒤에 연 쓰기부터 끝난다
  const second = seenBy(idbDo(w.scope, "readwrite", s => s.put({ id: "b" })));
  await F.settle();
  assert.deepEqual([first, second, [...idb.rows.keys()]], [[], [["ok", "b"]], ["b"]]);
});
