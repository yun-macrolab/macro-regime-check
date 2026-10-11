"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const F = require("./study_fakes.cjs");

// 공부 화면의 녹음 모듈(recorder.js) — 가짜 마이크 · 녹음기 · 화면 켜 두기 · IndexedDB로만 돈다. 실제 마이크 0번, 실제 시간 0초.
// 화면과 함께 도는 모습(녹음 한 줄 · 도장 · 듣기 · 설정)은 test_study_device.cjs가 본다. 돌리기: node --test scripts/test_study_recorder.cjs
const LS = "macro-study.";                                                         // 저장 이름의 머리(화면 쪽 상수 P와 같은 글자)
const FILES = ["core.js", "store.js", "recorder.js"];
const DAY = "2026-10-13";                                                          // 기준 시각(F.T0 = KST 10-13 화 08:30)의 공부 날짜
// 녹음 모듈만 실은 기기. media · idb는 가짜에 줄 것, flags는 저장값(예: { rec: "0" }). hear는 알림을 seen에 모은다
function rig({ media = {}, idb = {}, flags = {} } = {}) {
  const [m, db] = [F.fakeMedia(media), F.fakeIdb(idb)];
  const storage = F.fakeStorage(Object.fromEntries(Object.entries(flags).map(pair => [LS + pair[0], pair[1]])));
  const w = F.world(FILES, { media: m, idb: db, storage });
  const seen = [];
  return Object.assign(w, { R: w.scope.StudyRecorder, media: m, idb: db, seen, hear: ev => { seen.push(F.plain(ev)); } });
}
// [말하기]를 누른 것처럼 시작하고 약속이 끝나기를 기다린다
async function talk(w, slot = "today", date = DAY) {
  w.R.begin(slot, date, w.hear);
  await F.settle();
}
const types = w => w.seen.map(ev => ev.type + (ev.code ? ":" + ev.code : ""));     // 알림의 차례("off:wait" 꼴)
const locks = w => w.media.locks.map(lock => lock.released);                       // 화면 켜 두기마다 놓았는가

// ── 시작과 끝 ──
test("녹음: 녹음기와 마이크가 둘 다 있어야 된다고 답한다 — 상수는 최근 7개 · 64kbps · mp4 먼저", () => {
  assert.deepEqual([rig().R.supported(), rig({ media: { recorder: "none" } }).R.supported(), rig({ media: { mic: "none" } }).R.supported()], [true, false, false]);
  const K = rig().R._;
  assert.deepEqual([K.KEEP, K.BITS, F.plain(K.TYPES), Object.isFrozen(K.TYPES)], [7, 64000, ["audio/mp4", "audio/webm;codecs=opus"], true]);
});

test("녹음 시작: 부른 그 자리에서 마이크를 청하고 곧바로 돌아온다 — 허용되면 mp4 · 64kbps로 돌고 화면 켜 두기를 쥔다", async () => {
  const w = rig();
  const back = w.R.begin("today", DAY, w.hear);
  assert.deepEqual([back, F.plain(w.media.asks), types(w), w.media.recorders.length, w.R.seconds("today")], [undefined, [{ audio: true }], ["off:wait"], 0, 0]);   // 돌아온 때에는 이미 청해 두었다
  await F.settle();
  const rec = w.media.recorders[0];
  assert.deepEqual([types(w), rec.state, F.plain(rec.options), w.media.live(), locks(w)], [["off:wait", "on"], "recording", { mimeType: "audio/mp4", audioBitsPerSecond: 64000 }, 1, [false]]);
});

test("녹음 형식: mp4를 받지 않으면 webm, 둘 다 아니면 형식을 정하지 않고 맡긴다", async () => {
  const made = async list => { const w = rig({ media: { types: list } }); await talk(w); return F.plain(w.media.recorders[0].options); };
  assert.deepEqual([await made(["audio/webm;codecs=opus", "audio/mp4"]), await made(["audio/webm;codecs=opus"]), await made(["audio/ogg"])],
    [{ mimeType: "audio/mp4", audioBitsPerSecond: 64000 }, { mimeType: "audio/webm;codecs=opus", audioBitsPerSecond: 64000 }, { audioBitsPerSecond: 64000 }]);
});

test("녹음 끝: 녹음기를 멈추고 마이크의 트랙을 모두 닫고 화면 켜 두기를 놓는다 — 두 번 불러도 한 번만 한다", async () => {
  const w = rig();
  await talk(w);
  w.clock.advance(45300);
  const back = w.R.end("today");
  assert.deepEqual([back, w.media.recorders[0].state, w.media.live(), locks(w), w.R.seconds("today")], [undefined, "inactive", 0, [true], 45]);
  w.clock.advance(5000);
  w.R.end("today");
  w.R.end();
  await F.settle();
  assert.deepEqual([types(w).includes("cut"), w.R.seconds("today"), w.media.asks.length, w.media.recorders.length], [false, 45, 1, 1]);
});

test("녹음은 기다리게 하지 않는다: 허용 창이 떠 있는 채여도 시작 · 끝은 곧바로 돌아온다 — 늦게 온 허용은 마이크를 곧바로 닫는다", async () => {
  const hung = rig({ media: { mic: "hang", wake: "hang" } });
  await talk(hung);
  hung.clock.advance(120000);
  assert.equal(hung.R.end("today"), undefined);
  await F.settle();
  assert.deepEqual([types(hung), hung.media.asks.length, hung.media.recorders.length, hung.R.seconds("today")], [["off:wait"], 1, 0, 0]);
  const late = rig({ media: { mic: "hold" } });
  await talk(late);
  late.R.end("today");                                                                   // 허용 창이 떠 있는 채 2분이 찼다
  late.media.answer("ok");                                                               // 그 뒤에야 허용을 눌렀다
  await F.settle();
  assert.deepEqual([late.media.streams.length, late.media.live(), late.media.recorders.length, types(late), locks(late)], [1, 0, 0, ["off:wait"], [true]]);
});

test("녹음 없이: 거절 · 마이크 없음 · 녹음기를 만들지 못함 · 미지원이면 알리고 끝이다 — 녹음을 끈 기기에서는 마이크를 청하지도 알리지도 않는다", async () => {
  const run = async opts => { const w = rig(opts); await talk(w); return [types(w), w.media.asks.length, w.media.live(), locks(w)]; };
  assert.deepEqual(await run({ media: { mic: "deny" } }), [["off:wait", "off:denied"], 1, 0, [true]]);
  assert.deepEqual(await run({ media: { mic: "error" } }), [["off:wait", "off:error"], 1, 0, [true]]);
  assert.deepEqual(await run({ media: { recorder: "throw" } }), [["off:wait", "off:error"], 1, 0, [true]]);
  assert.deepEqual(await run({ media: { recorder: "none" } }), [["off:unsupported"], 0, 0, []]);
  assert.deepEqual(await run({ media: { mic: "none" } }), [["off:unsupported"], 0, 0, []]);
  assert.deepEqual(await run({ flags: { rec: "0" } }), [[], 0, 0, []]);
});

test("화면 켜 두기: 없거나 거절되면 한 줄로 알린다 — 녹음은 그대로 돈다. 끝내 답이 없으면 아무 말도 없다", async () => {
  const run = async wake => { const w = rig({ media: { wake } }); await talk(w); return [types(w).sort(), w.media.recorders[0].state]; };
  assert.deepEqual([await run("none"), await run("deny")], Array(2).fill([["nowake", "off:wait", "on"], "recording"]));
  assert.deepEqual([await run("hang"), await run("ok")], Array(2).fill([["off:wait", "on"], "recording"]));
  const refused = rig({ media: { wake: "none", mic: "hold" } });
  await talk(refused);
  refused.media.answer("deny");
  await F.settle();
  assert.deepEqual(types(refused), ["off:wait", "nowake", "off:denied"]);
});

// ── 끊김 ──
test("끊김: 화면이 가려지면 그 자리에서 닫고 초와 함께 알린다 — 다시 보여도 저절로 다시 시작하지 않는다", async () => {
  const w = rig();
  await talk(w);
  w.clock.advance(45300);
  w.fire("visibilitychange", "hidden");
  assert.deepEqual([w.seen.slice(2), w.media.live(), w.media.recorders[0].state, locks(w)], [[{ type: "cut", sec: 45 }], 0, "inactive", [true]]);
  w.fire("visibilitychange", "visible");
  w.clock.advance(60000);
  w.fire("visibilitychange", "hidden");
  w.R.end("today");
  await F.settle();
  assert.deepEqual([w.media.asks.length, w.media.recorders.length, w.R.seconds("today"), types(w).filter(one => one === "cut").length], [1, 1, 45, 1]);
});

test("끊김: 마이크가 음소거되거나 끝나도, 녹음기가 오류를 내거나 스스로 멈춰도 끊김이다 — 허용을 기다리던 중에 가려지면 말없이 닫는다", async () => {
  const cutBy = async poke => {
    const w = rig();
    await talk(w);
    w.clock.advance(30000);
    poke(w);
    await F.settle();
    return [w.seen.filter(ev => ev.type === "cut"), w.media.live(), w.media.recorders[0].state, locks(w)];
  };
  const want = [[{ type: "cut", sec: 30 }], 0, "inactive", [true]];
  assert.deepEqual(await cutBy(w => w.media.streams[0].tracks[0].emit("mute")), want);
  assert.deepEqual(await cutBy(w => w.media.streams[0].tracks[0].emit("ended")), want);
  assert.deepEqual(await cutBy(w => w.media.recorders[0].emit("error")), want);
  assert.deepEqual(await cutBy(w => w.media.recorders[0].stop()), want);                  // 녹음기가 스스로 멈췄다
  const waiting = rig({ media: { mic: "hold" } });
  await talk(waiting);
  waiting.fire("visibilitychange", "hidden");
  waiting.media.answer("ok");
  await F.settle();
  assert.deepEqual([types(waiting), waiting.media.live(), waiting.media.recorders.length], [["off:wait"], 0, 0]);
});

// ── 녹음기가 돈 초 · 화면 둘 ──
test("녹음 초: 녹음기가 돈 동안만 센다 — 허용을 기다린 시간은 빼고, 2분에서 멈추고, 녹음을 끄고 다시 말하면 0이다", async () => {
  const w = rig({ media: { mic: "hold" } });
  assert.deepEqual([w.R.seconds("today"), w.R.seconds()], [0, 0]);
  await talk(w);
  w.clock.advance(20000);
  w.media.answer("ok");
  await F.settle();
  w.clock.advance(59999);
  assert.equal(w.R.seconds("today"), 59);
  w.clock.advance(200000);
  assert.equal(w.R.seconds("today"), 120);
  w.R.end("today");
  w.clock.advance(60000);
  assert.deepEqual([w.R.seconds("today"), w.R.seconds("ask"), w.R.seconds()], [120, 0, 120]);
  w.storage.setItem(LS + "rec", "0");
  await talk(w);
  assert.deepEqual([w.R.seconds("today"), w.R.seconds(), w.media.asks.length], [0, 0, 1]);
});

test("녹음은 한 번에 하나: 다른 화면이 시작하면 앞의 것은 거기서 끊기고, 같은 화면이 다시 시작하면 앞의 것을 버린다 — 끝은 제 화면의 것만 닫는다", async () => {
  const w = rig();
  const [today, ask] = [[], []];
  w.R.begin("today", DAY, ev => today.push(ev.type));
  await F.settle();
  w.clock.advance(30000);
  w.R.begin("ask", DAY, ev => ask.push(ev.type));
  await F.settle();
  assert.deepEqual([today.slice(0, 3), ask, w.media.live(), w.media.recorders.map(rec => rec.state), w.R.seconds("today")],
    [["off", "on", "cut"], ["off", "on"], 1, ["inactive", "recording"], 30]);
  w.clock.advance(90000);
  w.R.end("today");                                                                      // 오늘 화면의 시계가 끝났다 — 질문 화면의 녹음은 그대로 돈다
  assert.deepEqual([w.media.live(), w.R.seconds("ask"), w.R.seconds()], [1, 90, 90]);
  w.R.begin("ask", DAY, ev => ask.push("again:" + ev.type));                             // 같은 화면에서 다시 말한다
  await F.settle();
  assert.deepEqual([ask.slice(2), w.media.live(), w.media.recorders.map(rec => rec.state), w.R.seconds("ask")],
    [["again:off", "again:on"], 1, ["inactive", "inactive", "recording"], 0]);
  w.R.end();
  assert.deepEqual([w.media.live(), locks(w)], [0, [true, true, true]]);
});

test("녹음이 알릴 때 화면이 던져도 녹음은 제 일을 마친다 — 알릴 곳을 주지 않아도 된다", async () => {
  const w = rig();
  w.R.begin("today", DAY, () => { throw new Error("지어낸 고장"); });
  await F.settle();
  w.R.end("today");
  assert.deepEqual([w.media.recorders[0].state, w.media.live()], ["inactive", 0]);
  w.R.begin("today", DAY);
  await F.settle();
  assert.equal(w.media.live(), 1);
  w.R.end();
  assert.equal(w.media.live(), 0);
});

// ── 보관 ── 이 기기의 IndexedDB에 최근 7개
const C = F.world(["core.js"]).scope.StudyCore;
const TODAY_ID = DAY + ".today";                                                   // 오늘 화면에서 한 녹음의 키
const kept = w => [...w.idb.rows.values()].map(row => [row.id, row.sec]);          // 보관된 것(넣은 차례)
// 한 번 말하고 끝낸다: ms만큼 녹음한 뒤 end, 보관이 끝나기를 기다린다
async function take(w, ms, slot = "today", date = DAY) {
  await talk(w, slot, date);
  w.clock.advance(ms);
  w.R.end(slot);
  await F.settle();
}

test("보관: 끝나면 이 기기의 IndexedDB에 둔다 — 데이터베이스 · 저장소 · 키와 값의 꼴, 그리고 '보관됨'을 초 · 크기와 함께 알린다", async () => {
  const w = rig();
  await take(w, 120000);
  assert.deepEqual([w.seen.slice(2), w.idb.log.slice(0, 2), [...w.idb.rows.keys()]],
    [[{ type: "saved", sec: 120, bytes: 960000 }], ["open macro-study.takes v1", "store takes keyPath=id"], [TODAY_ID]]);
  const row = w.idb.rows.get(TODAY_ID);
  assert.deepEqual({ ...row, blob: [row.blob.size, row.blob.type] },
    { id: TODAY_ID, date: DAY, slot: "today", at: F.T0, sec: 120, bytes: 960000, type: "audio/mp4", blob: [960000, "audio/mp4"] });
  assert.deepEqual([w.R._.DB, w.R._.STORE, w.idb.log.filter(one => one === "open macro-study.takes v1").length, w.idb.log.filter(one => one === "close").length], ["macro-study.takes", "takes", 2, 2]);
});

test("보관: 같은 날 같은 화면에서 다시 말하면 새것이 앞의 것을 바꾼다 — 화면이 다르면 따로 남고, list는 늦은 것부터다", async () => {
  const w = rig();
  await take(w, 100000);
  w.clock.advance(60000);
  await take(w, 30000);
  w.clock.advance(60000);
  await take(w, 60000, "ask");
  assert.deepEqual(kept(w), [[TODAY_ID, 30], [DAY + ".ask", 60]]);
  assert.deepEqual(F.plain(await w.R.list()), [{ id: DAY + ".ask", date: DAY, slot: "ask", sec: 60, bytes: 480000, type: "audio/mp4" },
    { id: TODAY_ID, date: DAY, slot: "today", sec: 30, bytes: 240000, type: "audio/mp4" }]);
  assert.deepEqual(F.plain(await w.R.stats()), { n: 2, bytes: 720000 });
});

test("보관: 최근 7개만 남긴다 — 아홉 날을 녹음하면 앞의 이틀 것이 지워진다", async () => {
  const w = rig();
  const days = [0, 1, 2, 3, 4, 5, 6, 7, 8].map(i => C.addDays("2026-10-05", i));
  for (const date of days) {
    await take(w, 10000, "today", date);
    w.clock.advance(86400000 - 10000);
  }
  assert.deepEqual([[...w.idb.rows.keys()], F.plain(await w.R.list()).map(row => row.date), F.plain(await w.R.stats())],
    [days.slice(2).map(date => date + ".today"), days.slice(2).reverse(), { n: 7, bytes: 560000 }]);
  assert.deepEqual(w.idb.log.filter(one => one.startsWith("delete")), ["delete 2026-10-05.today", "delete 2026-10-06.today"]);
});

test("보관은 기다리게 하지 않는다: 쓰기가 끝나지 않아도, 녹음기의 종료 사건이 오지 않아도 끝은 곧바로 돌아온다 — 마이크는 닫히고 알림만 없다", async () => {
  for (const opts of [{ idb: { write: "hang" } }, { idb: { open: "hang" } }, { media: { recorder: "nostop" } }]) {
    const w = rig(opts);
    await talk(w);
    w.clock.advance(120000);
    assert.equal(w.R.end("today"), undefined);
    await F.settle();
    assert.deepEqual([types(w), w.media.live(), w.idb.rows.size, w.R.seconds("today"), locks(w)], [["off:wait", "on"], 0, 0, 120, [true]], JSON.stringify(opts));
  }
});

test("빈 파일 · 보관 실패: 알리기만 한다 — 빈 파일은 두지 않고, 보관하지 못해도 마이크는 닫혀 있다", async () => {
  const run = async opts => { const w = rig(opts); await take(w, 60000); return [w.seen.slice(2), w.idb.rows.size, w.media.live()]; };
  assert.deepEqual(await run({ media: { recorder: "empty" } }), [[{ type: "fail", code: "empty" }], 0, 0]);
  for (const idb of [{ write: "fail" }, { open: "fail" }, { none: true }]) {
    assert.deepEqual(await run({ idb }), [[{ type: "fail", code: "store" }], 0, 0], JSON.stringify(idb));
  }
});

test("보관: 끊긴 녹음도 있는 만큼 둔다 — 같은 화면에서 다시 시작해 버린 것은 두지 않는다", async () => {
  const w = rig();
  await talk(w);
  w.clock.advance(45300);
  w.fire("visibilitychange", "hidden");
  await F.settle();
  assert.deepEqual([w.seen.slice(2), kept(w)], [[{ type: "cut", sec: 45 }, { type: "saved", sec: 45, bytes: 362400 }], [[TODAY_ID, 45]]]);
  const v = rig();
  await talk(v);
  v.clock.advance(30000);
  await talk(v);                                                                         // 같은 화면에서 다시 말한다 — 앞의 30초는 버린다
  assert.deepEqual([v.idb.rows.size, types(v)], [0, ["off:wait", "on", "off:wait", "on"]]);
  v.clock.advance(10000);
  v.R.end("today");
  await F.settle();
  assert.deepEqual([kept(v), v.seen.slice(4)], [[[TODAY_ID, 10]], [{ type: "saved", sec: 10, bytes: 80000 }]]);
});

test("녹음 끄기: 화면을 대지 않은 끝(설정에서 녹음을 껐다)은 실제로 닫았을 때만 그 녹음의 화면에 '녹음 없이'를 알린다 — 있는 만큼 보관되고, 화면을 대고 부른 끝에는 알림이 더해지지 않는다", async () => {
  const w = rig();
  await talk(w, "ask");
  w.clock.advance(30000);
  w.R.end();
  assert.deepEqual([w.seen.slice(2), w.media.live(), locks(w), w.R.seconds("ask")], [[{ type: "off", code: "error" }], 0, [true], 30]);
  w.R.end();                                                                             // 이미 닫혔다 — 다시 알리지 않는다
  await F.settle();
  assert.deepEqual([w.seen.slice(3), kept(w)], [[{ type: "saved", sec: 30, bytes: 240000 }], [[DAY + ".ask", 30]]]);
  const waiting = rig({ media: { mic: "hold" } });
  await talk(waiting);
  waiting.R.end();                                                                       // 허용을 기다리던 중에 껐다 — 늦게 온 허용은 마이크를 곧바로 닫는다
  waiting.media.answer("ok");
  await F.settle();
  assert.deepEqual([types(waiting), waiting.media.live(), waiting.media.recorders.length, locks(waiting)], [["off:wait", "off:error"], 0, 0, [true]]);
  const v = rig();
  await talk(v);
  v.clock.advance(10000);
  v.R.end("today");                                                                      // 2분 · [그만]: 화면을 대고 부른 끝
  v.R.end();
  rig().R.end();                                                                         // 녹음한 적이 없는 기기 — 닫을 것도 알릴 곳도 없다
  await F.settle();
  assert.deepEqual(types(v), ["off:wait", "on", "saved"]);
});

test("녹음의 한도: 화면이 끝을 알리지 않아도 녹음기가 돈 지 2분 5초면 스스로 끊는다 — 2분으로 보관되고, 제때 닫힌 녹음에는 때맞춤이 남지 않는다", async () => {
  const w = rig();
  await talk(w, "ask");
  w.clock.advance(124999);                                                               // 화면의 시계가 치워졌다(같은 저장 공간을 쓰는 다른 창) — 끝도 [그만]도 오지 않는다
  assert.deepEqual([w.media.live(), types(w)], [1, ["off:wait", "on"]]);
  w.clock.advance(1);
  assert.deepEqual([w.seen.slice(2), w.media.live(), w.media.recorders[0].state, locks(w), w.clock.pending()], [[{ type: "cut", sec: 120 }], 0, "inactive", [true], 0]);
  await F.settle();
  w.clock.advance(600000);
  assert.deepEqual([w.seen.slice(3), kept(w), w.R.seconds("ask")], [[{ type: "saved", sec: 120, bytes: 1000000 }], [[DAY + ".ask", 120]], 120]);
  const v = rig();
  await talk(v);
  v.clock.advance(30000);
  await talk(v);                                                                         // 같은 화면에서 다시 말한다 — 앞 녹음의 한도는 거둔다
  assert.equal(v.clock.pending(), 1);
  v.clock.advance(110000);
  v.R.end("today");                                                                      // 제때 온 끝
  assert.equal(v.clock.pending(), 0);
  v.clock.advance(600000);
  await F.settle();
  assert.deepEqual([types(v).slice(4), kept(v)], [["saved"], [[TODAY_ID, 110]]]);
});

test("보관한 것 읽기 · 지우기: 읽지 못하면 빈 값이고 거절하지 않는다 — 꼴이 다른 값은 건너뛰고, [모두 지우기]는 곧바로 비운다", async () => {
  const w = rig();
  await take(w, 60000);
  w.idb.rows.set("낯선 것", { id: "낯선 것", blob: null });                                  // 같은 주소의 다른 코드가 넣은 값
  w.idb.rows.set("2026-10-12.today", { id: "2026-10-12.today", date: "2026-10-12", slot: "today", at: "어제", sec: 1, bytes: 1, type: "audio/mp4" });
  w.idb.rows.set("<b>굵게</b>", { id: "<b>굵게</b>", date: "<i>기울게</i>", slot: "today", at: F.T0 + 1, sec: 1, bytes: 1, type: "audio/mp4" });
  assert.deepEqual([F.plain(await w.R.list()).map(row => row.id), F.plain(await w.R.stats())], [[TODAY_ID], { n: 1, bytes: 480000 }]);
  assert.deepEqual([await w.R.clearAll(), w.idb.rows.size, F.plain(await w.R.list()), F.plain(await w.R.stats())], [true, 0, [], { n: 0, bytes: 0 }]);
  for (const idb of [{ read: "fail", write: "fail" }, { open: "fail" }, { none: true }]) {
    const broken = rig({ idb });
    assert.deepEqual([F.plain(await broken.R.list()), F.plain(await broken.R.stats()), await broken.R.clearAll()], [[], { n: 0, bytes: 0 }, false], JSON.stringify(idb));
  }
});

// ── 재생 주소 ── 듣기가 쓴다. 한 번에 하나만 살아 있다
test("재생 주소: 보관된 녹음의 주소를 내준다 — 새로 청하면 앞의 것을 거두고, stopPlayback은 한 번만 거둔다", async () => {
  const w = rig();
  await take(w, 60000);
  await take(w, 30000, "ask");
  assert.deepEqual([await w.R.url(TODAY_ID), w.media.urls, w.media.revoked], ["blob:study/1", ["blob:study/1"], []]);
  assert.deepEqual([await w.R.url(DAY + ".ask"), w.media.revoked], ["blob:study/2", ["blob:study/1"]]);
  assert.equal(w.R.stopPlayback(), undefined);
  w.R.stopPlayback();
  assert.deepEqual(w.media.revoked, ["blob:study/1", "blob:study/2"]);
  assert.deepEqual([await w.R.url("없는 것"), await w.R.url(undefined), w.media.urls.length], [null, null, 2]);
  const broken = rig({ idb: { read: "fail" } });
  assert.deepEqual([await broken.R.url(TODAY_ID), await rig({ idb: { none: true } }).R.url(TODAY_ID), broken.media.urls], [null, null, []]);
});

test("재생과 녹음: 새 녹음은 재생 주소를 거둔 뒤에 마이크를 청한다 — 녹음하는 동안과, 주소를 기다리던 중에 녹음을 시작했거나 재생을 거뒀으면 내주지 않는다", async () => {
  const w = rig();
  await take(w, 60000);
  await w.R.url(TODAY_ID);
  const before = w.media.log.length;
  w.R.begin("ask", DAY, w.hear);
  assert.deepEqual(w.media.log.slice(before), ["revoke", "wake", "mic"]);                  // 거두고 → 화면 켜 두기 → 마이크
  await F.settle();
  assert.deepEqual([await w.R.url(TODAY_ID), w.media.urls.length], [null, 1]);              // 녹음하는 동안
  w.R.end("ask");
  await F.settle();
  const waiting = w.R.url(TODAY_ID);
  w.R.begin("ask", DAY, w.hear);                                                         // 주소를 기다리던 중에 녹음을 시작했다
  assert.equal(await waiting, null);
  w.R.end("ask");
  await F.settle();
  const left = w.R.url(TODAY_ID);
  w.R.stopPlayback();                                                                    // 주소를 기다리던 중에 화면을 떠났다
  const again = w.R.url(TODAY_ID);
  assert.deepEqual([await left, await again, w.media.urls.length, w.media.revoked.length], [null, "blob:study/2", 2, 1]);
  assert.deepEqual([await w.R.clearAll(), w.media.revoked.length, await w.R.url(TODAY_ID)], [true, 2, null]);   // 모두 지우면 틀던 것도 거둔다
});

test("녹음 모듈이 내보내는 이름 — 어느 것도 부른 쪽을 기다리게 하지 않는다: 마이크 · 화면 켜 두기 · 보관이 모두 답하지 않아도 곧바로 돌아온다", async () => {
  const w = rig({ media: { mic: "hang", wake: "hang" }, idb: { open: "hang" } });
  assert.deepEqual(Object.keys(w.R).sort(), ["_", "begin", "clearAll", "end", "list", "seconds", "stats", "stopPlayback", "supported", "url"]);
  assert.deepEqual([w.R.begin("today", DAY, w.hear), w.R.seconds("today"), w.R.end("today"), w.R.stopPlayback(), w.R.supported()], [undefined, 0, undefined, undefined, true]);
  const pending = [w.R.list(), w.R.url(TODAY_ID), w.R.stats(), w.R.clearAll()];
  const settled = [];
  for (const one of pending) one.then(() => settled.push(1), () => settled.push(-1));
  await F.settle();
  assert.deepEqual([pending.map(one => typeof one.then), settled, types(w), w.clock.pending()], [Array(4).fill("function"), [], ["off:wait"], 0]);   // 약속은 끝나지 않지만 아무도 기다리지 않는다
});
