"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const F = require("./study_fakes.cjs");

// 공부 화면의 마이크 닫기 — "끝난 그 자리에서 닫힌다"를 지키는 묶음. 뼈대 문서가 싣는 그대로(F.boot) 싣고 가짜 마이크 · 녹음기 · IndexedDB를 꽂는다.
// 녹음에는 한도가 있어서(녹음기가 돈 지 2분 5초면 스스로 닫는다) 화면이 닫지 않아도 마이크는 언젠가 닫힌다. 그래서 여기서는 '닫혔는가'가 아니라
// '한도 전에, 그 일이 일어난 바로 그 자리에서 닫혔는가'를 본다: 시계가 끝을 알리지 않는 길(2분이 찬 틈 · 날짜 바뀜)과 화면이 없는 길(다른 화면에 가 있는 동안).
// 실제 마이크 0번, 실제 시간 0초. 돌리기: node --test scripts/test_study_mic.cjs
const LS = "macro-study.";                                                         // 저장 이름의 머리(화면 쪽 상수 P와 같은 글자)
const C = F.world(["core.js"]).scope.StudyCore;
const DAY = "2026-10-13";                                                          // 기준 시각(F.T0 = KST 10-13 화 08:30)의 공부 날짜
const CAP = C.TALK_SEC * 1000 + 5000;                                              // 녹음의 한도(ms): 녹음기가 돈 지 2분 5초. 아래의 '그 자리'는 모두 이보다 앞이다
const size = sec => Math.round(sec * 8000);                                        // 그만큼 돈 가짜 녹음기가 내놓는 크기(초당 8000바이트) — 보관된 크기로 녹음기가 언제 멈췄는지 본다
const kstMs = text => Date.parse(text + "+09:00");                                 // KST로 적은 시각의 ms
// 화면마다: 길 · [말하기] · 시계 · 녹음 한 줄의 id
const TD = { hash: "", talk: "td-talk", clock: "td-clock", note: "td-recnote" };
const ASK = { hash: "#ask", talk: "ask-talk", clock: "ask-clock", note: "ask-recnote" };

// 이름이 있는 기기에서 그 화면을 열고 [말하기]를 눌러 ms만큼 말한다(허용은 곧바로 온다). began은 녹음기가 돌기 시작한 시각이다
async function talking(P, ms, now = F.T0) {
  const [media, idb] = [F.fakeMedia(), F.fakeIdb()];
  const w = await F.boot({ hash: P.hash, now, media, idb, storage: F.fakeStorage({ [LS + "dev"]: "폰" }) });
  Object.assign(w, { media, idb, began: now, S: w.scope.StudyStore, at: id => F.byId(w.doc, id) });
  F.press(w.at(P.talk));
  await F.settle();
  w.clock.advance(ms);
  await F.settle();
  return w;
}
// 틈: 2분이 찼는데 때맞춤(250ms)은 아직 울리지 않았다 — 119.9초까지 말하고 시각만 0.2초 옮긴다(시계는 끝을 적지도 알리지도 못했다)
async function inGap(P) {
  const w = await talking(P, 119900);
  w.clock.set(w.clock.now() + 200);
  return w;
}
const here = (w, ...ids) => ids.filter(id => w.at(id) !== null);                    // 그 가운데 지금 화면에 있는 id
const lineOf = (w, id) => (w.at(id) === null ? null : F.text(w.at(id)));            // 그 id의 글자(없으면 null)
const nav = (w, ...names) => names.forEach(name => F.press(F.byK(w.doc, name)[0])); // 이동 줄의 이름을 차례로 누른다
// 지금 그 자리에서 본 것: 열린 마이크 수 · 녹음기 상태 · 한도 전인가 · 녹음 한 줄 · 시계 글자
const seen = (w, P) => [w.media.live(), w.media.recorders[0].state, w.clock.now() - w.began < CAP, lineOf(w, P.note), lineOf(w, P.clock)];
// 약속이 끝난 뒤: 보관된 녹음(키 · 초 · 크기)과 이 기기가 쓴 줄의 수
async function kept(w) {
  await F.settle();
  return [[...w.idb.rows].map(pair => [pair[0], pair[1].sec, pair[1].bytes]), w.S.queue().length];
}

// ── 시계가 끝을 알리지 않는 길 ── resume()은 "done" · "idle"을 돌려줄 뿐 끝을 알리지 않는다. 그릴 때 닫는 한 줄이 받는다
test("오늘의 틈: 2분이 찼는데 때맞춤이 아직 울리지 않았을 때 저장 없이 화면만 다시 그려도 그 자리에서 마이크가 닫힌다 — 오늘을 다시 누르든 다른 화면에 갔다 오든, 2분이 보관되고 도장 칸이 열린다", async () => {
  for (const path of [["today"], ["week", "today"]]) {
    const w = await inGap(TD);
    assert.deepEqual([seen(w, TD), w.S.talk("today").end], [[1, "recording", true, C.T.REC_ON, "0:01"], null], String(path));
    nav(w, ...path);
    assert.deepEqual([seen(w, TD), here(w, "td-stop", "td-full", "td-min")], [[0, "inactive", true, null, "끝 · 2:00"], ["td-full", "td-min"]], String(path));
    assert.deepEqual(await kept(w), [[[DAY + ".today", 120, size(120.1)]], 0], String(path));    // 녹음기는 2:00.1에 멈췄다(한도까지 돌았다면 125초 분이다)
  }
});

test("오늘의 밤: 말하는 도중 공부 날짜가 바뀐 뒤 화면을 다시 그리면 그 자리에서 마이크가 닫힌다 — 녹음은 말하기를 시작한 날의 키로 있는 만큼 보관되고, 새 날의 화면에는 [말하기]만 있다", async () => {
  const w = await talking(TD, 40000, kstMs("2026-10-14T03:59:30"));                      // 03:59:30(공부 날짜는 아직 10-13)에 시작해 04:00:10까지 말했다
  assert.deepEqual([seen(w, TD), w.S.talk("today").d], [[1, "recording", true, C.T.REC_ON, "1:20"], DAY]);   // 날짜가 바뀌어도 돌던 시계는 그대로 간다
  nav(w, "today");
  assert.deepEqual([seen(w, TD), here(w, "td-talk", "td-stop", "td-min"), w.S.talk("today")], [[0, "inactive", true, null, null], ["td-talk"], null]);
  assert.deepEqual(await kept(w), [[[DAY + ".today", 40, size(40)]], 0]);
});

test("질문의 틈: 2분이 찼는데 때맞춤이 아직 울리지 않았을 때 저장 없이 화면만 다시 그려도 그 자리에서 마이크가 닫힌다 — 질문을 다시 누르든 다른 화면에 갔다 오든, 2분이 보관되고 쓴 줄은 없다", async () => {
  for (const path of [["ask"], ["week", "ask"]]) {
    const w = await inGap(ASK);
    assert.deepEqual([seen(w, ASK), w.S.talk("ask").end], [[1, "recording", true, C.T.REC_ON, "0:01"], null], String(path));
    nav(w, ...path);
    assert.deepEqual([seen(w, ASK), here(w, "ask-stop", "ask-talk")], [[0, "inactive", true, null, "끝 · 2:00"], ["ask-talk"]], String(path));
    assert.deepEqual(await kept(w), [[[DAY + ".ask", 120, size(120.1)]], 0], String(path));
  }
});

test("질문의 밤: 말하는 도중 공부 날짜가 바뀐 뒤 화면을 다시 그리면 그 자리에서 마이크가 닫힌다 — 녹음은 말하기를 시작한 날의 키로 있는 만큼 보관되고, 쓴 줄은 없다", async () => {
  const w = await talking(ASK, 40000, kstMs("2026-10-14T03:59:30"));                     // 오늘의 밤과 같은 시각 — 시계가 비워지는 쪽(idle)의 가지를 질문 화면에서도 지킨다
  assert.deepEqual(seen(w, ASK), [1, "recording", true, C.T.REC_ON, "1:20"]);
  nav(w, "ask");
  assert.deepEqual([seen(w, ASK), here(w, "ask-stop", "ask-talk")], [[0, "inactive", true, null, null], ["ask-talk"]]);
  assert.deepEqual(await kept(w), [[[DAY + ".ask", 40, size(40)]], 0]);
});

// ── 화면이 없는 길 ── 다른 화면에 가 있으면 말하기 자리를 다시 그리지 않는다. 시계가 끝을 알린 그 처리가 스스로 닫는다
test("질문의 2분: 말하다 다른 화면에 가 있는 동안 2분이 차면 2:00 그 자리에서 마이크가 닫힌다 — 한도(2:05)를 기다리지 않고, 2분이 보관되며, 돌아오면 '끊김' 줄이 없다", async () => {
  const w = await talking(ASK, 30000);
  nav(w, "week");
  w.clock.advance(89999);
  assert.deepEqual(seen(w, ASK), [1, "recording", true, null, null]);                    // 1:59.999 — 화면을 옮겨도 녹음은 이어진다
  w.clock.advance(1);
  assert.deepEqual(seen(w, ASK), [0, "inactive", true, null, null]);                     // 2:00.000 — 질문 화면이 없어도 닫는다
  assert.deepEqual(await kept(w), [[[DAY + ".ask", 120, size(120)]], 0]);
  w.clock.advance(600000);                                                               // 한도의 시각이 지나도 달라지는 것이 없다
  await F.settle();
  nav(w, "ask");
  assert.deepEqual([w.media.live(), lineOf(w, ASK.note), lineOf(w, ASK.clock), here(w, "ask-stop", "ask-talk")], [0, null, "끝 · 2:00", ["ask-talk"]]);
});
