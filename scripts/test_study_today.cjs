"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const F = require("./study_fakes.cjs");

// 공부 화면의 화면 테스트 — 오늘(today.js)과 [공유], 설정의 기기 묶음(settings.js). 뼈대 문서가 싣는 그대로(F.boot) 싣는다. 지어낸 글만 쓴다.
// 돌리기: node --test scripts/test_study_today.cjs
const LS = "macro-study.";                                                         // 저장 이름의 머리(화면 쪽 상수 P와 같은 글자)
const C = F.world(["core.js"]).scope.StudyCore;
const kstMs = text => Date.parse(text + "+09:00");                                 // KST로 적은 시각의 ms
// 지어낸 줄: at은 KST 시각("2026-10-12T08:30:00"), rand는 줄마다 달리 준다. 기본은 다른 기기(PC)가 쓴 줄이다
const line = (kind, fields, at, rand, dev = "PC") => F.line(kind, fields, { ms: kstMs(at), dev, rand });
const day = (at, mark, rand, more = {}) => line("day", { mark, sec: 120, rec: 0, stuck: "", ...more }, at, rand);
const next = (at, text, rand) => line("next", { text }, at, rand);
// 이름이 있는 기기의 저장 공간. lines는 달 사본에만 넣는다(받은 줄처럼 — 대기 줄은 비어 있다). more는 그 밖의 저장값
function device(lines = [], more = {}) {
  const months = [...new Set(lines.map(text => C.lineMonth(text)))].sort();
  const copies = months.map(month => ["m." + month, lines.filter(text => C.lineMonth(text) === month).join("\n")]);
  const seed = { dev: "폰", ...(months.length > 0 ? { months: JSON.stringify(months) } : {}), ...Object.fromEntries(copies), ...more };
  return F.fakeStorage(Object.fromEntries(Object.entries(seed).map(pair => [LS + pair[0], pair[1]])));
}
// 뼈대 문서가 싣는 그대로 싣고 시작한다. at(id)는 그 id의 요소(없으면 null), wrote()는 이 기기가 쓴 줄(쓴 차례)
async function open(opts = {}) {
  const w = await F.boot({ storage: device(), ...opts });
  const wrote = () => F.plain(w.scope.StudyStore.queue()).map(text => JSON.parse(text));
  return Object.assign(w, { A: w.scope.StudyApp, S: w.scope.StudyStore, at: id => F.byId(w.doc, id), wrote });
}
const on = (w, ...list) => list.filter(id => w.at(id) !== null);                   // 그 가운데 지금 화면에 있는 id
const cells = w => F.byClass(w.at("td-strip"), "st-cell").map(n => n.getAttribute("data-k"));
// 다른 기기의 줄을 받았다(맞춤이 한 일의 대역): 달 사본에 더하고, 맞춤이 알린 것처럼 새로 고친다
const receive = (w, lines) => { w.S.absorb("2026-10", lines); w.A.refresh("sync"); };

// ── 오늘: 맞춤이 바꾸는 자리 — 개념 줄 · 권고 줄 · 14일 줄 ──
test("오늘: 기록이 없는 첫날 — 개념 줄 · 이번 주 판정 권고 · 14일 줄이 뜨고, 돌아오는 날 권고는 없다", async () => {
  const w = await open();
  assert.deepEqual([F.text(w.at("td-topic")), F.text(w.at("td-weekhint")), w.at("td-weekhint").getAttribute("class"), on(w, "td-advice")],
    [C.T.TD_TOPIC_NONE, C.T.TD_WEEK_HINT, "st-dim", []]);
  const strip = w.at("td-strip");
  assert.deepEqual([strip.tag, strip.getAttribute("class"), strip.getAttribute("aria-label"), cells(w), F.text(strip)],
    ["ol", "st-strip", C.T.TD_STRIP, Array(14).fill("none"), "·".repeat(14)]);
  assert.deepEqual([Object.keys(w.scope.StudyToday), Object.keys(w.scope.StudyToday._).sort(), w.scope.location.hash], [["_"], ["leave", "refresh", "render"], ""]);
});

test("오늘 개념 줄: 앞선 날에 적은 '내일 말할 개념' 가운데 가장 늦은 것 — 그 뒤에 도장이 있으면 이미 말한 것이다", async () => {
  const older = next("2026-10-10T21:00:00", "기간 프리미엄", "n001");
  const later = next("2026-10-12T21:00:00", "볼록성", "n002");
  assert.equal(F.text((await open({ storage: device([older, later]) })).at("td-topic")), "오늘 말할 개념: 볼록성");
  assert.equal(F.text((await open({ storage: device([older]) })).at("td-topic")), "오늘 말할 개념: 기간 프리미엄");       // 며칠 전 것이어도 뜬다
  assert.equal(F.text((await open({ storage: device([older, day("2026-10-12T08:30:00", "min", "d001")]) })).at("td-topic")), C.T.TD_TOPIC_NONE);
});

test("오늘: 받은 글에 꺾쇠가 있어도 요소가 생기지 않는다 — 글자 그대로 보인다", async () => {
  const sharp = "<b onclick=alert(1)>굵게</b><img src=x>";
  const w = await open({ storage: device([next("2026-10-12T21:00:00", sharp, "n001")]) });
  assert.deepEqual([F.text(w.at("td-topic")), F.all(w.at("td-topic")).length, F.byTag(w.doc, "b").length, F.byTag(w.doc, "img").length],
    ["오늘 말할 개념: " + sharp, 1, 0, 0]);
});

test("오늘 권고: 앞선 기록이 있고 어제가 빈칸이면 호박색 한 줄 — 어제가 쉼이었으면 없다", async () => {
  const stamp = day("2026-10-11T08:30:00", "full", "d001");
  const w = await open({ storage: device([stamp]) });
  assert.deepEqual([F.text(w.at("td-advice")), w.at("td-advice").getAttribute("class"), cells(w).slice(-3)], [C.T.TD_ADVICE, "st-amber", ["full", "none", "none"]]);
  const rest = line("rest", { on: "2026-10-12" }, "2026-10-11T08:31:00", "r001");
  const rested = await open({ storage: device([stamp, rest]) });
  assert.deepEqual([on(rested, "td-advice"), cells(rested).slice(-3), F.text(rested.at("td-strip")).slice(-3)], [[], ["full", "rest", "none"], "○쉼·"]);
});

test("오늘 맞춤: 다른 기기의 어제 도장 · 개념 · 주간 판정을 받으면 권고 줄이 사라지고 개념 줄 · 14일 줄이 바뀐다", async () => {
  const w = await open({ storage: device([day("2026-10-11T08:30:00", "full", "d001")]) });
  assert.deepEqual([on(w, "td-advice", "td-weekhint"), F.text(w.at("td-topic")), cells(w).slice(-2)], [["td-advice", "td-weekhint"], C.T.TD_TOPIC_NONE, ["none", "none"]]);
  const call = line("week", { wk: "2026-10-12", dur: "ow", cur: "steep", why: "지어낸 근거", wrong_if: "지어낸 조건" }, "2026-10-12T09:00:00", "w001");
  receive(w, [day("2026-10-12T08:30:00", "min", "d002"), next("2026-10-12T21:00:00", "볼록성", "n001"), call]);
  assert.deepEqual([on(w, "td-advice", "td-weekhint"), F.text(w.at("td-topic")), cells(w).slice(-2)], [[], "오늘 말할 개념: 볼록성", ["min", "none"]]);
  w.S.absorb("2026-10", [next("2026-10-12T22:00:00", "캐리", "n002")]);
  w.fire("visibilitychange", "visible");                                                 // 화면으로 돌아왔을 때도 같은 자리를 다시 그린다
  assert.equal(F.text(w.at("td-topic")), "오늘 말할 개념: 캐리");
});

// ── 오늘: 말하기와 시계 ──
const ids = node => F.all(node).map(n => n.getAttribute("id")).filter(Boolean);
const tdIds = w => ids(w.at("st-main")).filter(id => id.startsWith("td-"));       // 오늘 화면이 그려 둔 id(문서 차례)
const talked = (w, ms = 120000) => { F.press(w.at("td-talk")); w.clock.advance(ms); };
const talkOf = w => F.plain(w.S.talk("today"));

test("오늘 말하기: [말하기 2:00] → 시계가 남은 시간을 보이고 → 2분이 차면 '끝'이다 — 시작 시각은 기기에 적는다", async () => {
  const w = await open();
  assert.deepEqual([F.text(w.at("td-talk")), w.at("td-talk").getAttribute("class"), on(w, "td-clock", "td-stop")], [C.T.TD_TALK, "st-btn st-btn-big", []]);
  F.press(w.at("td-talk"));
  assert.deepEqual([on(w, "td-talk"), F.text(w.at("td-clock")), w.at("td-clock").getAttribute("role"), F.text(w.at("td-stop")), talkOf(w)],
    [[], "2:00", "timer", C.T.TD_STOP, { d: "2026-10-13", at: F.T0, end: null }]);
  w.clock.advance(1000);
  assert.equal(F.text(w.at("td-clock")), "1:59");
  w.clock.advance(118000);
  assert.deepEqual([F.text(w.at("td-clock")), on(w, "td-stop")], ["0:01", ["td-stop"]]);
  w.clock.advance(1000);
  assert.deepEqual([F.text(w.at("td-clock")), on(w, "td-stop", "td-talk"), w.clock.pending(), talkOf(w).end], ["끝 · 2:00", [], 0, F.T0 + 120000]);
});

test("오늘 말하기: [그만] — 말한 만큼으로 끝난다", async () => {
  const w = await open();
  talked(w, 45300);
  F.press(w.at("td-stop"));
  assert.deepEqual([F.text(w.at("td-clock")), on(w, "td-stop"), talkOf(w).end, w.clock.pending()], ["끝 · 0:45", [], F.T0 + 45300, 0]);
});

test("오늘 말하기: 다른 화면에 가 있는 동안 시계가 끝나도 그 화면에 그리지 않는다 — 돌아오면 끝나 있다", async () => {
  const w = await open();
  F.press(w.at("td-talk"));
  F.press(F.byK(w.doc, "week")[0]);
  w.clock.advance(120000);
  assert.deepEqual([tdIds(w), talkOf(w).end], [[], F.T0 + 120000]);
  F.press(F.byK(w.doc, "today")[0]);
  assert.deepEqual([F.text(w.at("td-clock")), on(w, "td-talk", "td-stop")], ["끝 · 2:00", []]);
});

test("오늘 말하기: 공부 날짜가 바뀐 뒤 돌아오면 어제의 시계는 없던 일이다 — 03:59:59까지는 남아 있다", async () => {
  const w = await open({ now: kstMs("2026-10-13T23:00:00") });
  talked(w);
  w.clock.set(kstMs("2026-10-14T03:59:59"));
  w.fire("visibilitychange", "visible");
  assert.deepEqual([F.text(w.at("td-clock")), F.text(w.at("st-date"))], ["끝 · 2:00", "10-13 화"]);
  w.clock.set(kstMs("2026-10-14T04:00:00"));
  w.fire("visibilitychange", "visible");
  assert.deepEqual([on(w, "td-clock", "td-talk"), F.text(w.at("st-date")), talkOf(w)], [["td-talk"], "10-14 수", null]);
});

// ── 오늘: 도장 칸과 도장 ──
const FORM = ["td-stuck", "td-warn", "td-nostuck", "td-full", "td-min"];
const off = (w, id) => w.at(id).hasAttribute("disabled");
const days = w => w.A.ctx().view.recs.filter(r => r.k === "day").length;

test("오늘 정상 흐름: 말하기 → 2분 → 막힌 곳 한 줄 → ○ — 줄 하나가 기기에 적히고 '오늘 ○ 08:32'가 남는다", async () => {
  const w = await open();
  assert.deepEqual(on(w, ...FORM, "td-done"), []);
  talked(w);
  assert.deepEqual(tdIds(w).filter(id => FORM.includes(id) || id === "td-clock"), ["td-clock", ...FORM]);
  const stuck = w.at("td-stuck");
  assert.deepEqual(["placeholder", "aria-label", "enterkeyhint", "type", "aria-describedby", "maxlength"].map(name => stuck.getAttribute(name)),
    [C.T.TD_STUCK_PH, C.T.TD_STUCK_PH, "done", "text", "td-warn", null]);
  assert.deepEqual([off(w, "td-full"), off(w, "td-min"), F.text(w.at("td-full")), F.text(w.at("td-min")), F.text(w.at("td-nostuck"))], [true, false, C.T.TD_FULL, C.T.TD_MIN, C.T.TD_NOSTUCK]);
  F.type(stuck, "  듀레이션과 볼록성의 차이  ");
  assert.equal(off(w, "td-full"), false);
  F.press(w.at("td-full"));
  const [row] = w.wrote();
  assert.deepEqual([w.wrote().length, row.k, row.mark, row.sec, row.rec, row.stuck, row.d, row.dev], [1, "day", "full", 120, 0, "듀레이션과 볼록성의 차이", "2026-10-13", "폰"]);
  assert.deepEqual([F.text(w.at("td-done")), on(w, "td-stuck", "td-nostuck", "td-full", "td-min", "td-clock", "td-talk")], ["오늘 ○ 08:32", []]);
  assert.deepEqual([talkOf(w), w.S.draft("td.stuck"), w.S.draft("td.nostuck"), cells(w)[13], F.text(w.at("st-status"))], [null, "", "", "full", C.T.ST_LOCAL]);
});

test("오늘 최소판 흐름: 말하기 → [그만] → △ — 글 없이 누름 세 번이다", async () => {
  const w = await open();
  talked(w, 45000);
  F.press(w.at("td-stop"));
  F.press(w.at("td-min"));
  const [row] = w.wrote();
  assert.deepEqual([w.wrote().length, row.mark, row.sec, row.stuck, F.text(w.at("td-done")), cells(w)[13], days(w)], [1, "min", 45, "", "오늘 △ 08:30", "min", 1]);
});

test("오늘 도장 칸: ○는 한 줄을 적거나 [막힘 없음]을 눌러야 켜지고 △는 언제나 켜져 있다 — 받지 않는 글은 경고하고 줄에 싣지 않는다", async () => {
  const w = await open();
  talked(w);
  const state = text => { F.type(w.at("td-stuck"), text); return [F.text(w.at("td-warn")), off(w, "td-full"), off(w, "td-min")]; };
  assert.deepEqual([state(""), state("   "), state("막힌 곳")], [["", true, false], ["", true, false], ["", false, false]]);
  assert.deepEqual([state("가".repeat(120)), state("가".repeat(121))], [["", false, false], ["120자를 넘었다", true, false]]);
  assert.deepEqual([state("k".repeat(40)), state("탭\t글")], [[C.T.WARN_SECRET, true, false], [C.T.WARN_CTRL, true, false]]);
  assert.equal(w.at("td-nostuck").getAttribute("aria-pressed"), "false");
  F.press(w.at("td-nostuck"));
  assert.deepEqual([w.at("td-nostuck").getAttribute("aria-pressed"), off(w, "td-full"), w.S.draft("td.nostuck")], ["true", false, "1"]);
  F.press(w.at("td-full"));                                                              // 칸에 남은 것은 받지 않는 글이다 — 빈 글로 찍는다
  assert.deepEqual([w.wrote().length, w.wrote()[0].mark, w.wrote()[0].stuck], [1, "full", ""]);
  const m = await open();
  talked(m);
  F.type(m.at("td-stuck"), "k".repeat(64));
  F.press(m.at("td-min"));
  assert.deepEqual([m.wrote().length, m.wrote()[0].mark, m.wrote()[0].stuck, m.S.draft("td.stuck")], [1, "min", "", ""]);
});

test("오늘 도장 칸: 자판의 완료(Enter)는 ○와 같다 — 꺼져 있으면 아무 일도 없고, 글자를 짓는 중이면 아니다", async () => {
  const w = await open();
  talked(w);
  F.key(w.at("td-stuck"), "Enter");
  F.type(w.at("td-stuck"), "막힌 곳");
  F.key(w.at("td-stuck"), "Enter", { isComposing: true });
  F.key(w.at("td-stuck"), "a");
  assert.deepEqual([w.wrote(), on(w, "td-done")], [[], []]);
  F.key(w.at("td-stuck"), "Enter");
  assert.deepEqual([w.wrote().map(r => [r.mark, r.stuck]), on(w, "td-done")], [[["full", "막힌 곳"]], ["td-done"]]);
});

test("오늘 도장 칸: 쓰던 글과 [막힘 없음]은 다시 열어도 남는다", async () => {
  const first = await open();
  talked(first);
  F.type(first.at("td-stuck"), "쓰던 글");
  F.press(first.at("td-nostuck"));
  const w = await open({ storage: first.storage, now: F.T0 + 300000 });
  assert.deepEqual([w.at("td-stuck").value, w.at("td-nostuck").getAttribute("aria-pressed"), off(w, "td-full"), F.text(w.at("td-clock"))], ["쓰던 글", "true", false, "끝 · 2:00"]);
  F.press(F.byK(w.doc, "set")[0]);
  F.press(F.byK(w.doc, "today")[0]);
  assert.deepEqual([w.at("td-stuck").value, w.wrote()], ["쓰던 글", []]);
});

test("오늘 이어 가기: 시계 도중 화면이 죽었다 살아나도 2분 뒤 도장이 열린다 — 2분이 지나 다시 열면 곧장 열려 있다", async () => {
  const storage = device();
  F.press((await open({ storage })).at("td-talk"));                                        // 이 화면은 여기서 죽는다(때맞춤도 함께)
  const w = await open({ storage, now: F.T0 + 30000 });
  assert.deepEqual([F.text(w.at("td-clock")), on(w, "td-stop", "td-full", "td-min"), w.clock.pending()], ["1:30", ["td-stop"], 1]);
  w.clock.advance(89999);
  assert.deepEqual(on(w, "td-full", "td-min"), []);
  w.clock.advance(1);
  assert.deepEqual([F.text(w.at("td-clock")), off(w, "td-full"), off(w, "td-min"), w.clock.pending()], ["끝 · 2:00", true, false, 0]);
  const late = device();
  F.press((await open({ storage: late })).at("td-talk"));
  const again = await open({ storage: late, now: F.T0 + 600000 });                       // 끝을 적지 못하고 죽었다 — 열자마자 끝난 것으로 본다
  assert.deepEqual([F.text(again.at("td-clock")), on(again, "td-stop"), off(again, "td-min"), talkOf(again).end], ["끝 · 2:00", [], false, F.T0 + 120000]);
  F.press(again.at("td-min"));
  assert.deepEqual([again.wrote().map(r => [r.mark, r.sec, r.t]), F.text(again.at("td-done"))], [[["min", 120, "2026-10-13T08:40:00+09:00"]], "오늘 △ 08:40"]);
});

test("오늘 도장: 저장 공간이 말을 듣지 않아도 2분 뒤 도장이 열리고 찍힌다 — 상태 줄은 붉다", async () => {
  const storage = device();
  const w = await open({ storage });
  storage.failOn("macro-study");
  talked(w);
  F.type(w.at("td-stuck"), "막힌 곳");
  F.press(w.at("td-full"));
  assert.deepEqual([F.text(w.at("td-done")), days(w), on(w, "td-full"), F.text(w.at("st-status")), w.at("st-status").getAttribute("class"), storage.data.size],
    ["오늘 ○ 08:32", 1, [], C.T.ST_STORE_FAIL, "st-status st-red", 1]);
});

test("오늘 맞춤: 다른 기기의 어제 도장을 받으면 권고 줄이 사라지고, 쓰던 칸과 시계는 그대로다", async () => {
  const w = await open({ storage: device([day("2026-10-11T08:30:00", "full", "d001")]) });
  const yesterday = day("2026-10-12T08:30:00", "full", "d002");
  talked(w, 30000);
  const face = w.at("td-clock");
  assert.deepEqual([on(w, "td-advice"), F.text(face)], [["td-advice"], "1:30"]);
  receive(w, [yesterday]);
  assert.deepEqual([on(w, "td-advice", "td-stop"), w.at("td-clock") === face, F.text(face), w.clock.pending(), cells(w)[12]], [["td-stop"], true, "1:30", 1, "full"]);
  w.clock.advance(1000);
  assert.equal(F.text(face), "1:29");                                                    // 같은 시계가 이어서 간다
  const v = await open({ storage: device([day("2026-10-11T08:30:00", "full", "d001")]) });
  talked(v);
  assert.deepEqual(tdIds(v).filter(id => id === "td-full" || id === "td-min"), ["td-min", "td-full"]);   // 돌아오는 날에는 △가 앞에 온다
  F.type(v.at("td-stuck"), "쓰던 글");
  const [input, clock] = [v.at("td-stuck"), v.at("td-clock")];
  receive(v, [yesterday]);
  v.fire("visibilitychange", "visible");
  assert.deepEqual([on(v, "td-advice"), v.at("td-stuck") === input, input.value, v.at("td-clock") === clock, off(v, "td-full"), v.wrote()], [[], true, "쓰던 글", true, false, []]);
});

test("오늘 맞춤: 도장 칸이 열려 있을 때 다른 기기의 오늘 도장이 오면 도장 자리만 생긴다 — 내가 찍으면 정상이 최소판을 이긴다", async () => {
  const w = await open();
  talked(w);
  F.type(w.at("td-stuck"), "쓰던 글");
  const input = w.at("td-stuck");
  receive(w, [day("2026-10-13T07:50:00", "min", "d001")]);
  assert.deepEqual([F.text(w.at("td-done")), w.at("td-stuck") === input, input.value, off(w, "td-full"), cells(w)[13]], ["오늘 △ 07:50", true, "쓰던 글", false, "min"]);
  F.press(w.at("td-full"));
  assert.deepEqual([F.text(w.at("td-done")), days(w), w.wrote().length, cells(w)[13]], ["오늘 ○ 08:32", 2, 1, "full"]);
});

test("오늘 도장: 도장 칸을 연 채 공부 날짜가 바뀌었으면 찍지 않는다 — 03:59:59에는 찍히고 04:00:00에는 새 날의 [말하기]부터다", async () => {
  const before = await open({ now: kstMs("2026-10-13T23:00:00") });
  talked(before);
  before.clock.set(kstMs("2026-10-14T03:59:59"));                                        // 화면은 켜 둔 채였다(돌아옴 사건이 없다)
  F.press(before.at("td-min"));
  assert.deepEqual(before.wrote().map(r => [r.d, r.t]), [["2026-10-13", "2026-10-14T03:59:59+09:00"]]);
  const after = await open({ now: kstMs("2026-10-13T23:00:00") });
  talked(after);
  after.clock.set(kstMs("2026-10-14T04:00:00"));
  F.press(after.at("td-min"));
  assert.deepEqual([after.wrote(), on(after, "td-min", "td-talk", "td-done"), talkOf(after)], [[], ["td-talk"], null]);
  const across = await open({ now: kstMs("2026-10-13T03:59:00") });                      // 04:00에 걸친 말하기도 같다 — 끝나면 새 날의 [말하기]다
  talked(across);
  assert.deepEqual([on(across, "td-min", "td-clock", "td-talk"), talkOf(across), across.wrote()], [["td-talk"], null, []]);
});

// ── 오늘: 도장 뒤 — 내일 말할 개념 · 다시 말하기 ──
const MINE = line("day", { mark: "min", sec: 120, rec: 0, stuck: "" }, "2026-10-13T08:10:00", "m001", "폰");   // 이 기기가 오늘 찍어 둔 도장
const stamped = (opts = {}) => open({ storage: device([MINE]), ...opts });

test("오늘 도장 뒤: 내일 말할 개념을 적으면 줄 하나가 적히고 '내일: …'이 남는다 — 쓰던 글은 다시 열어도 남고, 적은 뒤에는 비운다", async () => {
  const first = await stamped();
  assert.deepEqual([F.text(first.at("td-done")), on(first, "td-talk", "td-nextdone"), off(first, "td-nextsave"), F.text(first.at("td-nextsave"))], ["오늘 △ 08:10", [], true, C.T.TD_NEXT_SAVE]);
  assert.deepEqual([first.at("td-next").getAttribute("placeholder"), first.at("td-next").getAttribute("enterkeyhint")], [C.T.TD_NEXT_PH, "done"]);
  F.type(first.at("td-next"), "가".repeat(61));
  assert.deepEqual([F.text(first.at("td-warn")), off(first, "td-nextsave")], ["60자를 넘었다", true]);
  F.type(first.at("td-next"), "기간 프리미엄");
  assert.deepEqual([F.text(first.at("td-warn")), off(first, "td-nextsave")], ["", false]);
  const w = await open({ storage: first.storage });
  assert.equal(w.at("td-next").value, "기간 프리미엄");
  F.key(w.at("td-next"), "Enter");
  assert.deepEqual([w.wrote().map(r => [r.k, r.text]), F.text(w.at("td-nextdone")), w.at("td-next").value, w.S.draft("td.next"), off(w, "td-nextsave")],
    [[["next", "기간 프리미엄"]], "내일: 기간 프리미엄", "", "", true]);
  w.clock.advance(60000);
  F.type(w.at("td-next"), "볼록성");
  F.press(w.at("td-nextsave"));
  assert.deepEqual([w.wrote().length, F.text(w.at("td-nextdone")), F.text(w.at("td-topic"))], [2, "내일: 볼록성", C.T.TD_TOPIC_NONE]);   // 가장 늦은 것이 남고, 오늘 적은 것은 내일 뜬다
});

test("오늘 도장 뒤: [다시 말하기]는 연습이다 — 시계는 돌지만 도장 칸은 열리지 않고 도장도 늘지 않는다", async () => {
  const w = await stamped();
  assert.equal(F.text(w.at("td-again")), C.T.TD_AGAIN);
  F.press(w.at("td-again"));
  assert.deepEqual([F.text(w.at("td-clock")), on(w, "td-stop", "td-done")], ["2:00", ["td-stop", "td-done"]]);
  F.type(w.at("td-next"), "쓰는 중");
  const input = w.at("td-next");
  w.clock.advance(119000);
  assert.deepEqual([w.at("td-next") === input, input.value, F.text(w.at("td-clock"))], [true, "쓰는 중", "0:01"]);   // 시계가 가는 동안 칸은 그대로다
  w.clock.advance(1000);
  assert.deepEqual([F.text(w.at("td-clock")), on(w, "td-full", "td-min", "td-again"), w.at("td-next").value, days(w), w.wrote()], ["끝 · 2:00", ["td-again"], "쓰는 중", 1, []]);
});

test("오늘 맞춤: [말하기]만 있던 화면에 다른 기기의 오늘 도장이 오면 도장 뒤 화면이 된다 — 시계가 돌고 있으면 도장 자리만 생긴다", async () => {
  const theirs = day("2026-10-13T08:10:00", "full", "d001");
  const w = await open();
  receive(w, [theirs]);
  assert.deepEqual([F.text(w.at("td-done")), on(w, "td-talk", "td-next", "td-again")], ["오늘 ○ 08:10", ["td-next", "td-again"]]);
  const v = await open();
  talked(v, 30000);
  const face = v.at("td-clock");
  receive(v, [theirs]);
  assert.deepEqual([v.at("td-clock") === face, F.text(v.at("td-done")), on(v, "td-next")], [true, "오늘 ○ 08:10", []]);
  v.clock.advance(90000);
  assert.deepEqual([F.text(v.at("td-clock")), on(v, "td-full", "td-min", "td-next")], ["끝 · 2:00", ["td-next"]]);
});

// ── 오늘: [공유] ──
const idOf = text => JSON.parse(text).id;
const said = w => F.text(w.at("st-note"));                                         // 알림 한 줄
const SHARED = "10-13 화 · 2분 말하기 △";                                                 // MINE만 있는 날의 글
const boxOf = w => (w.at("td-sharebox") === null ? null : w.at("td-sharebox").tag + ":" + F.text(w.at("td-sharebox")));

test("오늘 공유: 공유 창 → 닫으면 아무 일도 없음 → 없거나 거절이면 복사 → 그것도 안 되면 글을 보여 준다", async () => {
  const run = async opts => {
    const w = await stamped(opts);
    F.press(w.at("td-share"));
    await F.settle();
    return [w.shared, w.copied, said(w), boxOf(w)];
  };
  assert.equal(F.text((await stamped()).at("td-share")), C.T.TD_SHARE);
  assert.deepEqual(await run({ share: "ok", clip: "ok" }), [[SHARED], [], "", null]);
  assert.deepEqual(await run({ share: "cancel", clip: "ok" }), [[], [], "", null]);
  assert.deepEqual(await run({ share: "deny", clip: "ok" }), [[], [SHARED], C.T.SHARE_COPIED, null]);
  assert.deepEqual(await run({ share: "none", clip: "ok" }), [[], [SHARED], C.T.SHARE_COPIED, null]);
  assert.deepEqual(await run({ share: "deny", clip: "deny" }), [[], [], C.T.SHARE_SHOWN, "pre:" + SHARED]);
  const w = await stamped();
  F.press(w.at("td-share"));
  F.press(w.at("td-share"));
  await F.settle();
  assert.deepEqual([F.byTag(w.doc, "pre").length, said(w)], [1, C.T.SHARE_SHOWN]);
});

test("오늘 공유: 글에는 그날의 도장 · 내일 말할 개념 · 질문만 — 가린 줄 · 기기 이름 · 녹음 초 · 어제의 줄은 없고, 꺾쇠도 글자 그대로다", async () => {
  const mark = line("day", { mark: "full", sec: 97, rec: 77, stuck: "<b>굵게</b> 막힘" }, "2026-10-13T08:10:00", "m001", "기기A1");
  const q = text => ({ text, sec: 60, rec: 0, s_head: true, s_two: false, s_wrong: false });
  const hide = line("q", q("가릴 질문"), "2026-10-13T08:20:00", "q002", "기기A1");
  const lines = [mark, next("2026-10-13T08:11:00", "내일 개념", "n001"), line("q", q("보이는 질문"), "2026-10-13T08:15:00", "q001"), hide,
    line("fix", { ref: idOf(hide), hide: true }, "2026-10-13T08:21:00", "f001"), next("2026-10-12T21:00:00", "어제 것", "n000")];
  const w = await open({ storage: device(lines, { dev: "기기A1" }) });
  F.press(w.at("td-share"));
  await F.settle();
  const text = F.text(w.at("td-sharebox"));
  assert.equal(text, "10-13 화 · 2분 말하기 ○\n막힌 곳: <b>굵게</b> 막힘\n내일 말할 개념: 내일 개념\n질문: 보이는 질문");
  assert.deepEqual([/기기A1|77|97|가릴|어제/.test(text), F.byTag(w.doc, "b").length, F.all(w.at("td-sharebox")).length], [false, 0, 1]);
});

test("오늘 공유: 날짜가 바뀐 뒤 누른 [공유]는 어제 것을 넘기지 않는다 — 공유할 기록이 없다는 말만 한다", async () => {
  const w = await stamped({ share: "ok", clip: "ok", now: kstMs("2026-10-13T23:00:00") });
  w.clock.set(kstMs("2026-10-14T04:00:00"));
  F.press(w.at("td-share"));
  await F.settle();
  assert.deepEqual([w.shared, w.copied, said(w), boxOf(w)], [[], [], C.T.SHARE_NONE, null]);
});

test("오늘 공유: 공유 창이 닫히지 않아도 화면은 기다리지 않는다 — 다시 말하기 · 적기가 되고, 다음 날에도 2분 뒤 도장이 열린다", async () => {
  const w = await stamped({ share: "hang", clip: "ok" });
  F.press(w.at("td-share"));
  await F.settle();
  F.press(w.at("td-again"));
  w.clock.advance(120000);
  F.type(w.at("td-next"), "볼록성");
  F.press(w.at("td-nextsave"));
  assert.deepEqual([F.text(w.at("td-clock")), F.text(w.at("td-nextdone")), w.wrote().map(r => r.k), said(w), w.copied], ["끝 · 2:00", "내일: 볼록성", ["next"], "", []]);
  w.clock.set(kstMs("2026-10-14T08:30:00"));
  w.fire("visibilitychange", "visible");
  talked(w);
  assert.deepEqual([F.text(w.at("td-clock")), off(w, "td-full"), off(w, "td-min"), F.text(w.at("td-topic"))], ["끝 · 2:00", true, false, "오늘 말할 개념: 볼록성"]);
  F.press(w.at("td-min"));
  await F.settle();
  assert.deepEqual([w.wrote().map(r => [r.k, r.d]), F.text(w.at("td-done")), said(w), w.shared], [[["next", "2026-10-13"], ["day", "2026-10-14"]], "오늘 △ 08:32", "", []]);
});

test("오늘 공유: 늦게 끝난 공유는 떠난 화면에 글을 쓰지 않는다 — 머물러 있었으면 지금 화면에 보여 준다", async () => {
  const run = async leave => {
    const hold = { fail: null };
    const navigator = { share: () => new Promise((resolve, reject) => { hold.fail = reject; }) };
    const w = await stamped({ extra: { navigator } });
    F.press(w.at("td-share"));
    F.type(w.at("td-next"), "볼록성");
    F.press(w.at("td-nextsave"));                                                          // 그 사이 화면을 새로 그렸다
    if (leave) F.press(F.byK(w.doc, "set")[0]);
    if (leave) F.press(F.byK(w.doc, "today")[0]);                                          // 떠났다가 돌아왔다 — 그 공유는 지난 화면의 것이다
    hold.fail(new Error("공유 실패"));
    await F.settle();
    return [said(w), boxOf(w)];
  };
  assert.deepEqual(await run(true), ["", null]);
  assert.deepEqual(await run(false), [C.T.SHARE_SHOWN, "pre:" + SHARED]);                // 누른 순간의 글이다
});

// ── 오늘: 쉬는 날 · 화면의 차례 · 바깥 요청 0번 ──
const pressed = (w, id) => w.at(id).getAttribute("aria-pressed");

test("오늘 쉬는 날: [내일 쉼] [모레 쉼] — 누르면 쉼 줄, 다시 누르면 가림 줄(취소)이고, 접힌 줄은 열어 둔 채로 남는다", async () => {
  const w = await open();
  const fold = () => w.at("td-rest1").parent;
  assert.deepEqual([fold().tag, fold().getAttribute("class"), fold().hasAttribute("open"), F.text(F.byTag(fold(), "summary")[0]), F.text(w.at("td-rest1")), F.text(w.at("td-rest2"))],
    ["details", "st-fold", false, C.T.TD_REST_FOLD, C.T.TD_REST1, C.T.TD_REST2]);
  F.press(F.byTag(fold(), "summary")[0]);
  F.press(w.at("td-rest1"));
  assert.deepEqual([w.wrote().map(r => [r.k, r.on]), pressed(w, "td-rest1"), pressed(w, "td-rest2"), fold().hasAttribute("open")], [[["rest", "2026-10-14"]], "true", "false", true]);
  w.clock.advance(1000);
  F.press(w.at("td-rest2"));
  F.press(w.at("td-rest1"));
  const rows = w.wrote();
  assert.deepEqual([rows.map(r => r.k), rows[1].on, rows[2].ref === rows[0].id, rows[2].hide, pressed(w, "td-rest1"), pressed(w, "td-rest2"), cells(w)[13]],
    [["rest", "rest", "fix"], "2026-10-15", true, true, "false", "true", "none"]);
  F.press(F.byK(w.doc, "today")[0]);                                                     // 화면을 새로 열면 접힌 줄은 다시 접혀 있다
  assert.deepEqual([fold().hasAttribute("open"), pressed(w, "td-rest2")], [false, "true"]);
  const later = await open({ storage: w.storage, now: kstMs("2026-10-16T08:30:00") });   // 사흘 뒤 — 어제(10-15)는 쉼이었으니 권고가 없다
  assert.deepEqual([cells(later).slice(-3), on(later, "td-advice"), pressed(later, "td-rest1")], [["none", "rest", "none"], [], "false"]);
});

test("오늘 쉬는 날: 단추에 보이던 것과 기록이 다르면(다른 기기의 쉼을 받았다) 쓰지 않고 다시 그리기만 한다", async () => {
  const w = await open();
  const theirs = line("rest", { on: "2026-10-14" }, "2026-10-13T08:00:00", "r001");
  receive(w, [theirs]);
  assert.equal(pressed(w, "td-rest1"), "false");                                         // 쉬는 날 단추는 맞춤이 바꾸는 자리가 아니다
  F.press(w.at("td-rest1"));
  assert.deepEqual([w.wrote(), pressed(w, "td-rest1")], [[], "true"]);
  F.press(w.at("td-rest1"));
  assert.deepEqual([w.wrote().map(r => [r.k, r.ref, r.hide]), pressed(w, "td-rest1")], [[["fix", idOf(theirs), true]], "false"]);
});

test("오늘: 화면의 차례 — 개념 줄과 권고 → 말하기 자리 → 14일 줄 → 쉬는 날 → 녹음 듣기. 날짜 고르기도 다른 쪽으로 가는 링크도 없다", async () => {
  const w = await open({ storage: device([day("2026-10-11T08:30:00", "full", "d001")]) });
  assert.deepEqual(tdIds(w), ["td-topic", "td-weekhint", "td-advice", "td-talk", "td-strip", "td-rest1", "td-rest2", "td-listen"]);
  talked(w, 1000);
  assert.deepEqual(tdIds(w).slice(3, 6), ["td-clock", "td-stop", "td-recnote"]);           // 이 브라우저(가짜)에는 녹음기가 없다 — "녹음 없이 진행 중" 한 줄이 선다
  w.clock.advance(119000);
  assert.deepEqual(tdIds(w), ["td-topic", "td-weekhint", "td-advice", "td-clock", "td-stuck", "td-warn", "td-nostuck", "td-min", "td-full", "td-strip", "td-rest1", "td-rest2", "td-listen"]);
  F.press(w.at("td-min"));
  assert.deepEqual(tdIds(w), ["td-topic", "td-weekhint", "td-done", "td-next", "td-warn", "td-nextsave", "td-again", "td-share", "td-strip", "td-rest1", "td-rest2", "td-listen"]);
  const main = w.at("st-main");
  assert.deepEqual([F.byTag(main, "a").length, F.byTag(main, "input").map(n => n.getAttribute("type")), F.byTag(main, "audio").length], [0, ["text"], 0]);
});

test("오늘: 열쇠가 없으면 바깥 요청 0번 — 말하기 · 도장 · 적기 · 쉼 · 공유 · 돌아옴을 다 해도", async () => {
  const w = await open({ share: "ok" });
  talked(w);
  F.type(w.at("td-stuck"), "막힌 곳");
  F.press(w.at("td-full"));
  F.type(w.at("td-next"), "볼록성");
  F.press(w.at("td-nextsave"));
  F.press(w.at("td-rest1"));
  F.press(w.at("td-share"));
  w.fire("visibilitychange", "visible");
  await F.settle();
  assert.deepEqual([w.wrote().map(r => r.k), w.shared.length, w.net.calls.length, w.net.unexpected, F.text(w.at("st-status"))], [["day", "next", "rest"], 1, 0, 0, C.T.ST_LOCAL]);
});

// ── 설정: 이 기기 묶음 · 상태 줄 · [새로 받기] ──
const SET_IDS = ["set-g-dev", "set-dev", "set-devsave", "set-devwarn", "set-g-state", "set-iconnote", "set-reload"];
const ROWS = ["webapp", "persist", "queue", "version"];
const rowsOf = w => Object.fromEntries(F.byClass(w.at("set-g-state"), "st-row").map(n => [n.getAttribute("data-k"), F.text(n)]));

test("설정: 이 기기 묶음 · 상태 줄 넷 · 아이콘 안내 한 줄 · [새로 받기]", async () => {
  const w = await open({ hash: "#set" });
  assert.deepEqual(ids(w.at("st-main")).filter(id => SET_IDS.includes(id)), SET_IDS);
  const [group, state, label] = [w.at("set-g-dev"), w.at("set-g-state"), F.byTag(w.at("set-g-dev"), "label")[0]];
  assert.deepEqual([group.getAttribute("class"), F.text(F.byTag(group, "h2")[0]), F.text(label), label.getAttribute("for"), w.at("set-dev").value, F.text(w.at("set-devsave"))],
    ["st-group", C.T.SET_G_DEV, C.T.SET_DEV, "set-dev", "폰", C.T.SET_DEV_SAVE]);
  assert.deepEqual([state.getAttribute("class"), F.text(F.byTag(state, "h2")[0]), F.byClass(state, "st-row").every(n => n.tag === "p")], ["st-group", C.T.SET_G_STATE, true]);
  const rows = rowsOf(w);
  assert.deepEqual([Object.keys(rows).filter(k => ROWS.includes(k)), ROWS.map(k => rows[k])], [ROWS, ["웹앱으로 열림: —", "오래 두기: —", "올릴 것: 0건", "판: " + w.A.VERSION]]);
  assert.deepEqual([F.text(w.at("set-iconnote")), F.text(w.at("set-reload")), w.reloads], [C.T.SET_ICON_NOTE, C.T.RELOAD, 0]);
  F.press(w.at("set-reload"));
  assert.deepEqual([w.reloads, Object.keys(w.scope.StudySettings), tdIds(w)], [1, ["_"], []]);
});

test("설정 상태 줄: 웹앱으로 열렸는지와 '오래 두기'의 답을 그대로 보여 준다 — 답이 오지 않아도 화면은 돈다", async () => {
  const seen = async opts => { const rows = rowsOf(await open({ hash: "#set", ...opts })); return [rows.webapp, rows.persist]; };
  assert.deepEqual(await seen({ standalone: true, persist: true }), ["웹앱으로 열림: 예", "오래 두기: 예"]);
  assert.deepEqual(await seen({ persist: false }), ["웹앱으로 열림: —", "오래 두기: 아니오"]);
  assert.deepEqual([await seen({ persist: "deny" }), await seen({ persist: "hang" })], [["웹앱으로 열림: —", "오래 두기: 아니오"], ["웹앱으로 열림: —", "오래 두기: —"]]);
  const hold = { done: null };
  const navigator = { storage: { persist: () => new Promise(resolve => { hold.done = resolve; }) } };
  const w = await open({ hash: "#set", extra: { navigator } });
  F.press(F.byK(w.doc, "today")[0]);
  hold.done(true);                                                                       // 답이 다른 화면에 가 있는 동안 왔다
  await F.settle();
  assert.deepEqual([ids(w.at("st-main")).filter(id => id.startsWith("set-")), on(w, "td-topic")], [[], ["td-topic"]]);
  F.press(F.byK(w.doc, "set")[0]);
  assert.equal(rowsOf(w).persist, "오래 두기: 예");
});

test("설정 기기 이름: 꼴이 틀리면 경고만, 맞으면 바꾼다 — 그 뒤의 줄은 새 이름으로 적힌다", async () => {
  const w = await open({ hash: "#set" });
  const [input, name] = [w.at("set-dev"), () => w.storage.data.get(LS + "dev")];
  F.type(input, " 아홉글자기기이름임 ");
  F.press(w.at("set-devsave"));
  assert.deepEqual([F.text(w.at("set-devwarn")), name(), input.value, w.at("set-devwarn").getAttribute("class"), input.getAttribute("aria-describedby")],
    [C.T.NAME_BAD, "폰", " 아홉글자기기이름임 ", "st-warn", "set-devwarn"]);
  F.type(input, " PC ");
  F.key(input, "Enter", { isComposing: true });
  assert.equal(name(), "폰");
  F.key(input, "Enter");
  assert.deepEqual([name(), F.text(w.at("set-devwarn")), w.at("set-dev") === input, input.value], ["PC", "", true, "PC"]);
  assert.deepEqual([w.A.write("next", { text: "하나" }).obj.dev, w.A.ctx().dev], ["PC", "PC"]);
});

test("설정 맞춤: 줄이 늘거나 맞춤이 알려도 상태 묶음만 다시 그린다 — 쓰던 칸은 그대로다", async () => {
  const w = await open({ hash: "#set" });
  const input = w.at("set-dev");
  F.type(input, "쓰는중");
  w.A.write("next", { text: "하나" });
  assert.deepEqual([rowsOf(w).queue, w.at("set-dev") === input, input.value], ["올릴 것: 1건", true, "쓰는중"]);
  w.A.write("next", { text: "둘" });
  w.A.refresh("sync");
  w.fire("visibilitychange", "visible");
  assert.deepEqual([rowsOf(w).queue, w.at("set-dev") === input, input.value, F.byClass(w.at("set-g-state"), "st-row").length >= ROWS.length], ["올릴 것: 2건", true, "쓰는중", true]);
});

// ── 오늘: 새로 그리면 알림 한 줄도 치운다(2부의 고침) ──
test("오늘 공유: 글을 보여 준 뒤 화면을 새로 그리면 그 글과 알림 한 줄을 함께 치운다 — '아래 글을 …'만 남지 않는다", async () => {
  const w = await stamped();
  F.press(w.at("td-share"));
  await F.settle();
  assert.deepEqual([said(w), boxOf(w)], [C.T.SHARE_SHOWN, "pre:" + SHARED]);
  F.type(w.at("td-next"), "볼록성");
  F.press(w.at("td-nextsave"));                                                            // 적으면 화면을 새로 그린다 — 보여 주던 글이 사라진다
  assert.deepEqual([said(w), boxOf(w), F.text(w.at("td-nextdone"))], ["", null, "내일: 볼록성"]);
  F.press(w.at("td-share"));
  await F.settle();
  assert.deepEqual([said(w), boxOf(w)], [C.T.SHARE_SHOWN, "pre:" + SHARED + "\n내일 말할 개념: 볼록성"]);
});
