"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const F = require("./study_fakes.cjs");

// 공부 화면의 화면 테스트 ② — 주간 · 질문(screens.js)과 주간 [공유]. 뼈대 문서가 싣는 그대로(F.boot) 싣는다. 지어낸 글만 쓴다.
// 돌리기: node --test scripts/test_study_screens.cjs
const LS = "macro-study.";                                                         // 저장 이름의 머리(화면 쪽 상수 P와 같은 글자)
const C = F.world(["core.js"]).scope.StudyCore;
const kstMs = text => Date.parse(text + "+09:00");                                 // KST로 적은 시각의 ms
// 지어낸 줄: at은 KST 시각("2026-10-12T08:30:00"), rand는 줄마다 달리 준다. 기본은 다른 기기(PC)가 쓴 줄이다
const line = (kind, fields, at, rand, dev = "PC") => F.line(kind, fields, { ms: kstMs(at), dev, rand });
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
const ids = node => F.all(node).map(n => n.getAttribute("id")).filter(Boolean);
const shown = (w, head) => ids(w.at("st-main")).filter(id => id.startsWith(head)); // 화면이 그려 둔 id 가운데 그 머리로 시작하는 것(문서 차례)
const off = (w, id) => w.at(id).hasAttribute("disabled");
const said = w => F.text(w.at("st-note"));                                         // 알림 한 줄
const idOf = text => JSON.parse(text).id;
const texts = node => F.byTag(node, "p").map(p => F.text(p));                      // 그 안의 줄들
// 다른 기기의 줄을 받았다(맞춤이 한 일의 대역): 달 사본에 더하고, 맞춤이 알린 것처럼 새로 고친다
const receive = (w, lines) => { w.S.absorb("2026-10", lines); w.A.refresh("sync"); };

// ── 주간: 이번 주 내 판정 ── 기준 시각(F.T0)은 10-13 화요일이다: 이번 주는 10-12(월) 주, 지난주는 10-05 주
const WK = "2026-10-12";
const LAST = "2026-10-05";
const WHY = "고용 둔화가 인하 기대를 앞당긴다";
const WRONG = "근원 물가가 예상보다 높게 나오면";
const CALL_IDS = ["wk-dur", "wk-cur", "wk-why", "wk-wrong", "wk-warn", "wk-save"];
// 지어낸 주간 판정 줄(다른 기기). at은 쓴 시각 — wk는 그 시각이 든 주의 월요일이어야 한다
const call = (wk, at, rand, more = {}) => line("week", { wk, dur: "uw", cur: "flat", why: "지난 근거", wrong_if: "지난 조건", ...more }, at, rand);
const pick = (w, group, k) => F.press(F.byK(w.at(group), k)[0]);                   // 고르기 묶음에서 하나를 누른다
const picks = (w, group) => F.byTag(w.at(group), "button").filter(n => n.getAttribute("aria-pressed") === "true").map(n => n.getAttribute("data-k")).join("+");
// 판정 칸 넷을 채운다
function fillCall(w, more = {}) {
  const v = { dur: "ow", cur: "steep", why: WHY, wrong: WRONG, ...more };
  pick(w, "wk-dur", v.dur);
  pick(w, "wk-cur", v.cur);
  F.type(w.at("wk-why"), v.why);
  F.type(w.at("wk-wrong"), v.wrong);
}

test("주간: 이번 주 내 판정 칸만 있다 — 저장 전에는 지난주 판정 · 채점이 나무에 없다(감춘 것이 아니라 없다)", async () => {
  const last = call(LAST, "2026-10-06T08:50:00", "w001");
  const grade = line("grade", { wk: LAST, ref: idOf(last), actual: "지난 실제", dur_hit: "y", cur_hit: "n", miss: "지난 이유" }, "2026-10-12T09:00:00", "g001");
  const w = await open({ hash: "#week", storage: device([call("2026-09-28", "2026-09-29T08:50:00", "w000"), last, grade]) });
  const main = w.at("st-main");
  assert.deepEqual([shown(w, "wk-"), shown(w, "gr-"), F.all(main).filter(n => n.hasAttribute("hidden")).length, /지난|2026-10-05|2026-09-28/.test(F.text(main))],
    [CALL_IDS, [], 0, false]);
  const [dur, cur] = [w.at("wk-dur"), w.at("wk-cur")];
  assert.deepEqual([F.byTag(main, "h2").map(n => F.text(n)), dur.getAttribute("role"), dur.getAttribute("aria-label"), cur.getAttribute("aria-label"), texts(dur), texts(cur)],
    [[C.T.WK_HEAD], "group", C.T.WK_DUR, C.T.WK_CUR, [C.T.WK_DUR], [C.T.WK_CUR]]);
  assert.deepEqual(F.byTag(dur, "button").map(n => [n.getAttribute("data-k"), F.text(n), n.getAttribute("aria-pressed")]),
    [["ow", "비중 확대", "false"], ["n", "중립", "false"], ["uw", "비중 축소", "false"]]);
  assert.deepEqual(F.byTag(cur, "button").map(n => [n.getAttribute("data-k"), F.text(n)]), [["flat", "플래트닝"], ["n", "중립"], ["steep", "스티프닝"]]);
  assert.deepEqual([w.at("wk-why").getAttribute("placeholder"), w.at("wk-wrong").getAttribute("placeholder"), F.text(w.at("wk-save")), off(w, "wk-save")],
    [C.T.WK_WHY_PH, C.T.WK_WRONG_PH, C.T.WK_SAVE, true]);
  assert.deepEqual([Object.keys(w.scope.StudyScreens), Object.keys(w.scope.StudyScreens._.week).sort(), w.wrote()], [["_"], ["leave", "refresh", "render"], []]);
});

test("주간 판정 칸: 넷(듀레이션 · 커브 · 근거 · 틀릴 조건)이 다 차고 문제없을 때만 [저장]이 켜진다 — 받지 않는 글은 경고한다", async () => {
  const w = await open({ hash: "#week" });
  const state = () => [off(w, "wk-save"), F.text(w.at("wk-warn"))];
  pick(w, "wk-dur", "ow");
  pick(w, "wk-cur", "steep");
  F.type(w.at("wk-why"), WHY);
  assert.deepEqual([state(), picks(w, "wk-dur"), picks(w, "wk-cur")], [[true, ""], "ow", "steep"]);
  F.type(w.at("wk-wrong"), "   ");
  assert.deepEqual(state(), [true, ""]);
  F.type(w.at("wk-wrong"), WRONG);
  assert.deepEqual(state(), [false, ""]);
  pick(w, "wk-dur", "uw");                                                               // 다시 고르면 눌림이 옮겨 간다
  assert.deepEqual([picks(w, "wk-dur"), w.S.draft("wk.dur"), state()], ["uw", "uw", [false, ""]]);
  F.type(w.at("wk-why"), "가".repeat(161));
  assert.deepEqual(state(), [true, "160자를 넘었다"]);
  F.type(w.at("wk-why"), "가".repeat(160));
  F.type(w.at("wk-wrong"), "k".repeat(40));
  assert.deepEqual(state(), [true, C.T.WARN_SECRET]);
  F.type(w.at("wk-wrong"), "탭\t글");
  assert.deepEqual([state(), w.at("wk-warn").getAttribute("class"), w.wrote()], [[true, C.T.WARN_CTRL], "st-warn", []]);
  assert.deepEqual(["aria-describedby", "aria-label", "enterkeyhint", "type", "maxlength"].map(name => w.at("wk-wrong").getAttribute(name)),
    ["wk-warn", C.T.WK_WRONG_PH, "done", "text", null]);
});

test("주간 저장: 두 번 눌러야 저장된다 — 첫 누름은 확인 한 줄이고, 그 사이에 칸이 바뀌면 첫 누름으로 돌아간다", async () => {
  const w = await open({ hash: "#week" });
  fillCall(w);
  const seen = () => [w.at("wk-confirm") === null ? null : F.text(w.at("wk-confirm")), F.text(w.at("wk-save")), w.wrote().length];
  assert.deepEqual(seen(), [null, C.T.WK_SAVE, 0]);
  F.press(w.at("wk-save"));
  assert.deepEqual([seen(), w.at("wk-confirm").getAttribute("class")], [["확대 · 스티프닝으로 저장 — 고칠 수 없다", C.T.WK_CONFIRM_BTN, 0], "st-amber"]);
  pick(w, "wk-cur", "flat");                                                             // 고른 것을 바꿨다
  assert.deepEqual(seen(), [null, C.T.WK_SAVE, 0]);
  F.press(w.at("wk-save"));
  assert.equal(seen()[0], "확대 · 플래트닝으로 저장 — 고칠 수 없다");
  F.type(w.at("wk-why"), "  " + WHY + " ");                                              // 글을 고쳤다
  assert.deepEqual(seen(), [null, C.T.WK_SAVE, 0]);
  F.press(w.at("wk-save"));
  F.press(w.at("wk-save"));
  const [row] = w.wrote();
  assert.deepEqual([w.wrote().length, row.k, row.wk, row.dur, row.cur, row.why, row.wrong_if, row.d, row.dev], [1, "week", WK, "ow", "flat", WHY, WRONG, "2026-10-13", "폰"]);
  assert.deepEqual([on(w, ...CALL_IDS, "wk-confirm"), ["wk.dur", "wk.cur", "wk.why", "wk.wrong"].map(slot => w.S.draft(slot)), F.text(w.at("st-status"))],
    [[], ["", "", "", ""], C.T.ST_LOCAL]);
});

test("주간 판정 칸: 자판의 완료(Enter)는 [저장]과 같다 — 꺼져 있으면 아무 일도 없고, 글자를 짓는 중이면 아니며, 두 번이어야 저장된다", async () => {
  const w = await open({ hash: "#week" });
  F.type(w.at("wk-why"), WHY);
  F.key(w.at("wk-why"), "Enter");                                                        // 아직 넷이 다 차지 않았다
  fillCall(w);
  F.key(w.at("wk-wrong"), "Enter", { isComposing: true });
  F.key(w.at("wk-wrong"), "a");
  assert.deepEqual(on(w, "wk-confirm"), []);
  F.key(w.at("wk-wrong"), "Enter");
  assert.deepEqual([on(w, "wk-confirm"), w.wrote()], [["wk-confirm"], []]);
  F.key(w.at("wk-why"), "Enter");
  assert.deepEqual(w.wrote().map(r => [r.k, r.wk]), [["week", WK]]);
});

test("주간 판정 칸: 쓰던 글과 고른 것은 다시 열어도 남는다 — 확인 한 줄은 남지 않고, 모르는 값은 고른 것이 아니다", async () => {
  const first = await open({ hash: "#week" });
  fillCall(first);
  F.press(first.at("wk-save"));
  const w = await open({ hash: "#week", storage: first.storage });
  assert.deepEqual([picks(w, "wk-dur"), picks(w, "wk-cur"), w.at("wk-why").value, w.at("wk-wrong").value, off(w, "wk-save"), on(w, "wk-confirm"), F.text(w.at("wk-save"))],
    ["ow", "steep", WHY, WRONG, false, [], C.T.WK_SAVE]);
  F.press(F.byK(w.doc, "today")[0]);
  F.press(F.byK(w.doc, "week")[0]);                                                      // 다른 화면에 다녀와도 같다
  assert.deepEqual([picks(w, "wk-dur"), w.at("wk-why").value, w.wrote()], ["ow", WHY, []]);
  const odd = await open({ hash: "#week", storage: device([], { draft: JSON.stringify({ "wk.dur": "zz", "wk.cur": "steep" }) }) });
  assert.deepEqual([picks(odd, "wk-dur"), picks(odd, "wk-cur"), off(odd, "wk-save")], ["", "steep", true]);
});

test("주간 맞춤: 다른 기기의 줄을 받거나 화면으로 돌아와도 판정 칸은 그대로다 — 지난주 판정이 와도 저장 전에는 나무에 없다", async () => {
  const w = await open({ hash: "#week" });
  fillCall(w);
  F.press(w.at("wk-save"));
  const [why, confirm] = [w.at("wk-why"), w.at("wk-confirm")];
  receive(w, [call(LAST, "2026-10-06T08:50:00", "w001")]);
  w.fire("visibilitychange", "visible");
  assert.deepEqual([w.at("wk-why") === why, w.at("wk-confirm") === confirm, why.value, shown(w, "wk-"), shown(w, "gr-")],
    [true, true, WHY, [...CALL_IDS.slice(0, 5), "wk-confirm", "wk-save"], []]);
  F.press(w.at("wk-save"));                                                              // 확인도 그대로였다 — 둘째 누름으로 저장된다
  assert.deepEqual(w.wrote().map(r => r.k), ["week"]);
});

test("주간 주 경계: 월요일 03:59:59까지는 지난주가 '이번 주'다 — 칸을 연 채 04:00:00을 넘겼으면 쓰지 않고 새 주의 칸부터다", async () => {
  const before = await open({ hash: "#week", now: kstMs("2026-10-18T23:00:00") });       // 일요일 밤
  fillCall(before);
  F.press(before.at("wk-save"));
  before.clock.set(kstMs("2026-10-19T03:59:59"));                                        // 화면은 켜 둔 채였다(돌아옴 사건이 없다)
  F.press(before.at("wk-save"));
  assert.deepEqual(before.wrote().map(r => [r.wk, r.d, r.t]), [[WK, "2026-10-18", "2026-10-19T03:59:59+09:00"]]);
  const after = await open({ hash: "#week", now: kstMs("2026-10-18T23:00:00") });
  fillCall(after);
  F.press(after.at("wk-save"));
  after.clock.set(kstMs("2026-10-19T04:00:00"));
  F.press(after.at("wk-save"));
  assert.deepEqual([after.wrote(), on(after, "wk-confirm"), after.at("wk-why").value, picks(after, "wk-dur"), F.text(after.at("wk-save"))], [[], [], WHY, "ow", C.T.WK_SAVE]);
  F.press(after.at("wk-save"));
  F.press(after.at("wk-save"));                                                          // 새 주의 판정으로 다시 두 번 누른다
  assert.deepEqual(after.wrote().map(r => [r.wk, r.d]), [["2026-10-19", "2026-10-19"]]);
});

// ── 주간: 저장한 뒤 — 이번 주 판정(읽기 전용) · 지난주 판정과 채점 ──
const MINE = line("week", { wk: WK, dur: "ow", cur: "steep", why: WHY, wrong_if: WRONG }, "2026-10-12T08:52:10", "m001", "폰");   // 이 기기가 월요일에 적어 둔 이번 주 판정
const PAST = call(LAST, "2026-10-06T08:50:00", "w001");                                   // 지난주 판정(다른 기기)
const GRADE_IDS = ["gr-actual", "gr-dur", "gr-cur", "gr-miss", "gr-warn", "gr-save"];
const saved = (opts = {}) => open({ hash: "#week", storage: device([PAST, MINE]), ...opts });
// 채점 칸을 채운다(빗나간 이유는 비운다)
function fillGrade(w, actual = "금리가 올랐다", dur = "y", cur = "n") {
  F.type(w.at("gr-actual"), actual);
  pick(w, "gr-dur", dur);
  pick(w, "gr-cur", cur);
}

test("주간 저장 뒤: 판정을 저장하면 그 자리에 이번 주 판정(읽기 전용)과 지난주 판정 · 채점 칸이 생긴다 — 지난주 판정이 없으면 한 줄뿐이다", async () => {
  const w = await open({ hash: "#week", storage: device([PAST]) });
  assert.deepEqual([on(w, "wk-save", "wk-mine", "wk-last", "wk-none"), shown(w, "gr-")], [["wk-save"], []]);
  fillCall(w);
  F.press(w.at("wk-save"));
  F.press(w.at("wk-save"));
  assert.deepEqual([on(w, "wk-save", "wk-mine", "wk-last", "wk-none"), shown(w, "gr-")], [["wk-mine", "wk-last"], GRADE_IDS]);
  assert.deepEqual(texts(w.at("wk-mine")), ["이번 주: 듀레이션 비중 확대 · 커브 스티프닝", "근거: " + WHY, "틀릴 조건: " + WRONG]);
  const last = w.at("wk-last");
  assert.deepEqual([last.tag, last.getAttribute("class"), F.byTag(last, "h2").map(n => F.text(n)), texts(last)],
    ["section", "st-group", [C.T.WK_LAST_HEAD], ["2026-10-05 주 · 듀레이션 비중 축소 · 커브 플래트닝", "근거: 지난 근거", "틀릴 조건: 지난 조건"]]);
  assert.deepEqual(F.byTag(w.at("st-main"), "input").map(n => n.getAttribute("id")), ["gr-actual", "gr-miss"]);   // 이번 주 판정을 고칠 칸은 없다
  const alone = await open({ hash: "#week", storage: device([MINE]) });
  assert.deepEqual([on(alone, "wk-save", "wk-mine", "wk-last", "wk-none"), shown(alone, "gr-"), F.text(alone.at("wk-none")), alone.at("wk-none").getAttribute("class")],
    [["wk-mine", "wk-none"], [], C.T.WK_LAST_NONE, "st-dim"]);
});

test("주간 채점: 실제 한 줄과 맞음 · 빗나감 둘이 차야 [채점 저장]이 켜진다 — 저장하면 지난주 판정을 가리키는 줄이 적히고 '채점함'이 남는다", async () => {
  const w = await saved();
  const marks = group => F.byTag(w.at(group), "button").map(n => [n.getAttribute("data-k"), F.text(n)]);
  assert.deepEqual([marks("gr-dur"), marks("gr-cur"), w.at("gr-dur").getAttribute("aria-label"), w.at("gr-cur").getAttribute("aria-label")],
    [[["y", "맞음"], ["n", "빗나감"], ["na", "판단 보류"]], [["y", "맞음"], ["n", "빗나감"], ["na", "판단 보류"]], C.T.WK_DUR, C.T.WK_CUR]);
  assert.deepEqual([w.at("gr-actual").getAttribute("placeholder"), w.at("gr-miss").getAttribute("placeholder"), F.text(w.at("gr-save")), off(w, "gr-save")],
    [C.T.GR_ACTUAL_PH, C.T.GR_MISS_PH, C.T.GR_SAVE, true]);
  F.type(w.at("gr-actual"), " 금리가 올랐다 ");
  pick(w, "gr-dur", "n");
  assert.equal(off(w, "gr-save"), true);
  pick(w, "gr-cur", "na");
  assert.equal(off(w, "gr-save"), false);                                                // 빗나간 이유는 비워도 된다
  F.type(w.at("gr-miss"), "가".repeat(161));
  assert.deepEqual([off(w, "gr-save"), F.text(w.at("gr-warn"))], [true, "160자를 넘었다"]);
  F.type(w.at("gr-miss"), "물가를 가볍게 봤다");
  F.key(w.at("gr-miss"), "Enter");                                                       // 자판의 완료 = 저장(채점은 한 번이다)
  const [row] = w.wrote();
  assert.deepEqual([w.wrote().length, row.k, row.wk, row.ref, row.actual, row.dur_hit, row.cur_hit, row.miss, row.d],
    [1, "grade", LAST, idOf(PAST), "금리가 올랐다", "n", "na", "물가를 가볍게 봤다", "2026-10-13"]);
  assert.deepEqual([shown(w, "gr-"), texts(w.at("gr-done")), ["gr.actual", "gr.dur", "gr.cur", "gr.miss"].map(slot => w.S.draft(slot))],
    [["gr-done"], [C.T.GR_SAVED, "실제: 금리가 올랐다", "듀레이션 빗나감 · 커브 판단 보류", "빗나간 이유: 물가를 가볍게 봤다"], ["", "", "", ""]]);
});

test("주간 채점: 같은 주 판정이 둘이면 먼저 쓴 것이 판정이고 채점도 그것을 가리킨다 — 채점이 이미 있으면 칸 대신 내용이 뜬다", async () => {
  const later = call(LAST, "2026-10-07T08:50:00", "w002", { dur: "ow", why: "나중 근거" });
  const w = await open({ hash: "#week", storage: device([later, PAST, MINE]) });
  assert.deepEqual(texts(w.at("wk-last")).slice(0, 2), ["2026-10-05 주 · 듀레이션 비중 축소 · 커브 플래트닝", "근거: 지난 근거"]);
  fillGrade(w, "실제", "y", "y");
  F.press(w.at("gr-save"));
  assert.deepEqual([w.wrote().map(r => r.ref), texts(w.at("gr-done"))], [[idOf(PAST)], [C.T.GR_SAVED, "실제: 실제", "듀레이션 맞음 · 커브 맞음"]]);   // 빗나간 이유가 없으면 그 줄도 없다
  const theirs = line("grade", { wk: LAST, ref: idOf(PAST), actual: "다른 기기의 채점", dur_hit: "n", cur_hit: "n", miss: "" }, "2026-10-12T21:00:00", "g001");
  const v = await open({ hash: "#week", storage: device([PAST, MINE, theirs]) });
  assert.deepEqual([shown(v, "gr-"), texts(v.at("gr-done"))[1]], [["gr-done"], "실제: 다른 기기의 채점"]);
});

test("주간 채점: 쓰던 글은 다시 열어도 남는다 — 보이던 지난주 판정보다 먼저 쓴 판정을 받았으면 쓰지 않고 다시 그리기만 한다", async () => {
  const first = await saved();
  F.type(first.at("gr-actual"), "쓰던 실제");
  pick(first, "gr-dur", "y");
  const w = await open({ hash: "#week", storage: first.storage });
  assert.deepEqual([w.at("gr-actual").value, picks(w, "gr-dur"), picks(w, "gr-cur"), off(w, "gr-save")], ["쓰던 실제", "y", "", true]);
  pick(w, "gr-cur", "n");
  const older = call(LAST, "2026-10-05T09:00:00", "w000", { why: "더 먼저 쓴 근거" });
  receive(w, [older]);                                                                   // 맞춤은 주간 화면을 바꾸지 않는다 — 보이는 것은 아직 앞의 판정이다
  assert.equal(texts(w.at("wk-last"))[1], "근거: 지난 근거");
  F.press(w.at("gr-save"));
  assert.deepEqual([w.wrote(), texts(w.at("wk-last"))[1], w.at("gr-actual").value, off(w, "gr-save")], [[], "근거: 더 먼저 쓴 근거", "쓰던 실제", false]);
  F.press(w.at("gr-save"));
  assert.deepEqual(w.wrote().map(r => [r.k, r.ref]), [["grade", idOf(older)]]);
});

test("주간 주 경계(저장 뒤): 월요일 03:59:59에는 지난주 판정이 아직 '이번 주'다 — 04:00:00부터 새 주의 칸이고, 저장하면 그 판정이 지난주로 내려간다", async () => {
  const before = await saved({ now: kstMs("2026-10-19T03:59:59") });
  assert.deepEqual([texts(before.at("wk-mine"))[0], texts(before.at("wk-last"))[0].slice(0, 12)], ["이번 주: 듀레이션 비중 확대 · 커브 스티프닝", "2026-10-05 주"]);
  const w = await saved({ now: kstMs("2026-10-19T04:00:00") });
  assert.deepEqual([on(w, "wk-mine", "wk-last", "wk-save"), /스티프닝으로|2026-10-1[29]|지난/.test(F.text(w.at("st-main")))], [["wk-save"], false]);
  fillCall(w, { dur: "n", cur: "n", why: "새 근거", wrong: "새 조건" });
  F.press(w.at("wk-save"));
  F.press(w.at("wk-save"));
  assert.deepEqual([texts(w.at("wk-mine")), texts(w.at("wk-last")).slice(0, 2), shown(w, "gr-")],
    [["이번 주: 듀레이션 중립 · 커브 중립", "근거: 새 근거", "틀릴 조건: 새 조건"], ["2026-10-12 주 · 듀레이션 비중 확대 · 커브 스티프닝", "근거: " + WHY], GRADE_IDS]);
  const g = await saved({ now: kstMs("2026-10-18T23:00:00") });
  fillGrade(g);
  g.clock.set(kstMs("2026-10-19T04:00:00"));                                             // 채점 칸을 연 채 주가 바뀌었다 — 그 채점은 쓰지 않는다
  F.press(g.at("gr-save"));
  assert.deepEqual([g.wrote(), shown(g, "gr-"), on(g, "wk-save", "wk-last")], [[], [], ["wk-save"]]);
});

// ── 주간: [공유] ──
const SHARED = "2026-10-12 주 · 듀레이션 비중 확대 · 커브 스티프닝\n근거: " + WHY + "\n틀릴 조건: " + WRONG;   // MINE의 글
const boxOf = w => (w.at("wk-sharebox") === null ? null : w.at("wk-sharebox").tag + ":" + F.text(w.at("wk-sharebox")));

test("주간 공유: 공유 창 → 닫으면 아무 일도 없음 → 없거나 거절이면 복사 → 그것도 안 되면 글을 보여 준다", async () => {
  const run = async opts => {
    const w = await saved(opts);
    F.press(w.at("wk-share"));
    await F.settle();
    return [w.shared, w.copied, said(w), boxOf(w)];
  };
  assert.equal(F.text((await saved()).at("wk-share")), C.T.TD_SHARE);
  assert.deepEqual(await run({ share: "ok", clip: "ok" }), [[SHARED], [], "", null]);
  assert.deepEqual(await run({ share: "cancel", clip: "ok" }), [[], [], "", null]);
  assert.deepEqual(await run({ share: "deny", clip: "ok" }), [[], [SHARED], C.T.SHARE_COPIED, null]);
  assert.deepEqual(await run({ share: "none", clip: "ok" }), [[], [SHARED], C.T.SHARE_COPIED, null]);
  assert.deepEqual(await run({ share: "deny", clip: "deny" }), [[], [], C.T.SHARE_SHOWN, "pre:" + SHARED]);
  const w = await saved();
  F.press(w.at("wk-share"));
  F.press(w.at("wk-share"));
  await F.settle();
  assert.deepEqual([F.byTag(w.doc, "pre").length, said(w)], [1, C.T.SHARE_SHOWN]);
});

test("주간 공유: 글에는 이번 주 판정만 — 가린 판정 · 기기 이름 · 지난주 판정과 채점은 없고, 꺾쇠도 글자 그대로다", async () => {
  const gone = line("week", { wk: WK, dur: "uw", cur: "flat", why: "가릴 근거", wrong_if: "가릴 조건" }, "2026-10-12T08:00:00", "h001", "기기A1");
  const mine = line("week", { wk: WK, dur: "n", cur: "steep", why: "<b>굵게</b> 근거", wrong_if: "조건 & 조건" }, "2026-10-12T09:00:00", "m002", "기기A1");
  const grade = line("grade", { wk: LAST, ref: idOf(PAST), actual: "지난 실제", dur_hit: "y", cur_hit: "n", miss: "" }, "2026-10-12T09:10:00", "g001", "기기A1");
  const lines = [gone, line("fix", { ref: idOf(gone), hide: true }, "2026-10-12T08:30:00", "f001"), mine, PAST, grade];
  const w = await open({ hash: "#week", storage: device(lines, { dev: "기기A1" }) });
  F.press(w.at("wk-share"));
  await F.settle();
  const text = F.text(w.at("wk-sharebox"));
  assert.equal(text, "2026-10-12 주 · 듀레이션 중립 · 커브 스티프닝\n근거: <b>굵게</b> 근거\n틀릴 조건: 조건 & 조건");
  assert.deepEqual([/기기A1|가릴|지난|2026-10-05/.test(text), F.byTag(w.doc, "b").length, F.all(w.at("wk-sharebox")).length, texts(w.at("wk-mine"))[1]],
    [false, 0, 1, "근거: <b>굵게</b> 근거"]);
});

test("주간 공유: 공유 창이 닫히지 않아도 화면은 기다리지 않는다 — 채점이 저장되고, 늦게 끝난 공유는 떠난 화면에 글을 쓰지 않는다", async () => {
  const w = await saved({ share: "hang", clip: "ok" });
  F.press(w.at("wk-share"));
  await F.settle();
  fillGrade(w);
  F.press(w.at("gr-save"));
  assert.deepEqual([w.wrote().map(r => r.k), on(w, "gr-done"), said(w), w.copied], [["grade"], ["gr-done"], "", []]);
  const run = async where => {
    const hold = { fail: null };
    const navigator = { share: () => new Promise((resolve, reject) => { hold.fail = reject; }) };
    const v = await saved({ extra: { navigator } });
    F.press(v.at("wk-share"));
    fillGrade(v);
    F.press(v.at("gr-save"));                                                            // 그 사이 화면을 새로 그렸다
    if (where !== "stay") F.press(F.byK(v.doc, "set")[0]);                               // 화면을 떠났다
    if (where === "back") F.press(F.byK(v.doc, "week")[0]);                              // 돌아왔다 — 그 공유는 지난 화면의 것이다
    hold.fail(new Error("공유 실패"));
    await F.settle();
    return [said(v), boxOf(v)];
  };
  assert.deepEqual([await run("away"), await run("back")], [["", null], ["", null]]);
  assert.deepEqual(await run("stay"), [C.T.SHARE_SHOWN, "pre:" + SHARED]);               // 머물러 있었으면 누른 순간의 글을 보여 준다
});

test("주간 공유: 주가 바뀐 뒤 누른 [공유]는 지난주 것을 넘기지 않는다 — 공유할 기록이 없다는 말만 한다", async () => {
  const w = await saved({ share: "ok", clip: "ok", now: kstMs("2026-10-18T23:00:00") });
  w.clock.set(kstMs("2026-10-19T04:00:00"));
  F.press(w.at("wk-share"));
  await F.settle();
  assert.deepEqual([w.shared, w.copied, said(w), boxOf(w)], [[], [], C.T.SHARE_NONE, null]);
});

test("주간: 화면의 차례 — 이번 주 판정 → [공유] → 지난주 판정 → 채점. 시트 판정도 다른 쪽으로 가는 링크도 없다", async () => {
  const w = await saved();
  assert.deepEqual([shown(w, "wk-"), shown(w, "gr-")], [["wk-mine", "wk-share", "wk-last"], GRADE_IDS]);
  F.press(w.at("wk-share"));
  await F.settle();
  assert.deepEqual([said(w), boxOf(w)], [C.T.SHARE_SHOWN, "pre:" + SHARED]);
  fillGrade(w);
  F.press(w.at("gr-save"));                                                              // 저장하면 화면을 새로 그린다 — 보여 주던 글과 알림 한 줄도 함께 치운다
  assert.deepEqual([said(w), boxOf(w)], ["", null]);
  F.press(w.at("wk-share"));
  await F.settle();
  const main = w.at("st-main");
  assert.deepEqual([ids(main).slice(1), F.byTag(main, "a").length, F.byTag(main, "input").length, F.byTag(main, "h2").map(n => F.text(n))],
    [["wk-mine", "wk-share", "wk-sharebox", "wk-last", "gr-done"], 0, 0, [C.T.WK_LAST_HEAD]]);
});

// ── 질문: 한 줄 · 말하기 · 세 칸 · 저장 ──
const Q = "A사 금리가 오르면 B사 조달은 어떻게 되나";
const ASK_IDS = ["ask-text", "ask-warn", "ask-rule", "ask-talk", "ask-clock", "ask-stop", "ask-head", "ask-two", "ask-wrong", "ask-save"];
const asked = (opts = {}) => open({ hash: "#ask", ...opts });
const form = w => shown(w, "ask-").filter(id => ASK_IDS.includes(id));             // 질문 칸의 id(문서 차례)
const talkOf = w => F.plain(w.S.talk("ask"));
const checksOf = w => ["ask-head", "ask-two", "ask-wrong"].map(id => w.at(id).checked);

test("질문: 한 줄 칸 → 규칙 한 줄 → [말하기 2:00] → 세 칸 → [저장] — 규칙 한 줄은 말하는 중에도 끝난 뒤에도 보인다", async () => {
  const w = await asked();
  assert.deepEqual(form(w), ["ask-text", "ask-warn", "ask-rule", "ask-talk", "ask-head", "ask-two", "ask-wrong", "ask-save"]);
  const input = w.at("ask-text");
  assert.deepEqual(["placeholder", "aria-label", "aria-describedby", "enterkeyhint", "type", "maxlength"].map(name => input.getAttribute(name)),
    [C.T.ASK_PH, C.T.ASK_PH, "ask-warn", "done", "text", null]);
  assert.deepEqual([F.text(w.at("ask-rule")), F.text(w.at("ask-talk")), w.at("ask-talk").getAttribute("class"), F.text(w.at("ask-save")), off(w, "ask-save")],
    [C.T.ASK_RULE, C.T.TD_TALK, "st-btn st-btn-big", C.T.ASK_SAVE, true]);
  const labels = F.byTag(w.at("st-main"), "label").map(n => [n.getAttribute("for"), F.text(n)]);
  assert.deepEqual([labels, ["ask-head", "ask-two", "ask-wrong"].map(id => [w.at(id).getAttribute("type"), w.at(id).parent.tag]), checksOf(w)],
    [[["ask-head", "결론 먼저"], ["ask-two", "근거 둘"], ["ask-wrong", "틀릴 조건"]], Array(3).fill(["checkbox", "label"]), [false, false, false]]);
  F.press(w.at("ask-talk"));
  assert.deepEqual([form(w).slice(2, 5), F.text(w.at("ask-rule"))], [["ask-rule", "ask-clock", "ask-stop"], C.T.ASK_RULE]);
  w.clock.advance(120000);
  assert.deepEqual([form(w).slice(2, 5), F.text(w.at("ask-rule"))], [["ask-rule", "ask-clock", "ask-talk"], C.T.ASK_RULE]);
  assert.deepEqual([Object.keys(w.scope.StudyScreens._).sort(), Object.keys(w.scope.StudyScreens._.ask).sort()], [["ask", "week"], ["leave", "refresh", "render"]]);
});

test("질문 저장: 한 줄 → 말하기 → [그만] → 세 칸 체크 → [저장] — 줄 하나가 적히고 칸 · 체크 · 시계 · 쓰던 글이 비워진다", async () => {
  const w = await asked();
  F.type(w.at("ask-text"), "  " + Q + " ");
  F.press(w.at("ask-talk"));
  assert.deepEqual([F.text(w.at("ask-clock")), w.at("ask-clock").getAttribute("role"), F.text(w.at("ask-stop")), on(w, "ask-talk"), talkOf(w)],
    ["2:00", "timer", C.T.TD_STOP, [], { d: "2026-10-13", at: F.T0, end: null }]);
  w.clock.advance(45300);
  assert.equal(F.text(w.at("ask-clock")), "1:15");
  F.press(w.at("ask-stop"));
  assert.deepEqual([F.text(w.at("ask-clock")), on(w, "ask-stop", "ask-talk"), w.clock.pending()], ["끝 · 0:45", ["ask-talk"], 0]);
  F.check(w.at("ask-head"), true);
  F.press(w.at("ask-wrong"));
  assert.deepEqual([checksOf(w), w.S.draft("ask.s")], [[true, false, true], "101"]);
  F.press(w.at("ask-save"));
  const [row] = w.wrote();
  assert.deepEqual([w.wrote().length, row.k, row.text, row.sec, row.rec, row.s_head, row.s_two, row.s_wrong, row.d, row.dev],
    [1, "q", Q, 45, 0, true, false, true, "2026-10-13", "폰"]);
  assert.deepEqual([w.at("ask-text").value, checksOf(w), on(w, "ask-clock", "ask-talk"), talkOf(w), w.S.draft("ask.text"), w.S.draft("ask.s"), off(w, "ask-save")],
    ["", [false, false, false], ["ask-talk"], null, "", "", true]);
});

test("질문 저장: 시계가 돌고 있으면 멈추고 그때까지의 초로 적는다 — 말하지 않았으면 0초이고, 자판의 완료(Enter)도 [저장]이다", async () => {
  const w = await asked();
  F.key(w.at("ask-text"), "Enter");                                                      // 꺼져 있으면 아무 일도 없다
  F.type(w.at("ask-text"), Q);
  F.key(w.at("ask-text"), "Enter", { isComposing: true });
  assert.deepEqual(w.wrote(), []);
  F.key(w.at("ask-text"), "Enter");
  assert.deepEqual(w.wrote().map(r => [r.text, r.sec, r.s_head, r.s_two, r.s_wrong]), [[Q, 0, false, false, false]]);
  w.clock.advance(60000);
  F.type(w.at("ask-text"), "둘째 질문");
  F.press(w.at("ask-talk"));
  w.clock.advance(30500);
  F.press(w.at("ask-save"));
  assert.deepEqual([w.wrote().map(r => r.sec), talkOf(w), w.clock.pending(), on(w, "ask-clock", "ask-stop", "ask-talk")], [[0, 30], null, 0, ["ask-talk"]]);
});

test("질문 칸: [저장]은 글이 문제없을 때만 켜진다 — 200자를 넘거나 받지 않는 글이면 경고한다", async () => {
  const w = await asked();
  const state = text => { F.type(w.at("ask-text"), text); return [F.text(w.at("ask-warn")), off(w, "ask-save")]; };
  assert.deepEqual([state(""), state("   "), state("질문")], [["", true], ["", true], ["", false]]);
  assert.deepEqual([state("가".repeat(200)), state("가".repeat(201))], [["", false], ["200자를 넘었다", true]]);
  assert.deepEqual([state("k".repeat(40)), state("탭\t글"), w.at("ask-warn").getAttribute("class")], [[C.T.WARN_SECRET, true], [C.T.WARN_CTRL, true], "st-warn"]);
  F.press(w.at("ask-talk"));
  F.key(w.at("ask-text"), "Enter");                                                      // 꺼진 [저장]은 자판의 완료로도 눌리지 않는다 — 시계도 멈추지 않는다
  F.press(w.at("ask-save"));
  assert.deepEqual([w.wrote(), on(w, "ask-stop"), talkOf(w).end], [[], ["ask-stop"], null]);
});

test("질문 이어 가기: 쓰던 글 · 체크 · 시계는 다시 열어도 남는다 — 시계 도중 화면이 죽었다 살아나도 이어 가고, 2분이 지나 있으면 끝나 있다", async () => {
  const first = await asked();
  F.type(first.at("ask-text"), Q);
  F.press(first.at("ask-two"));
  F.press(first.at("ask-talk"));                                                         // 이 화면은 여기서 죽는다(때맞춤도 함께)
  const w = await asked({ storage: first.storage, now: F.T0 + 30000 });
  assert.deepEqual([w.at("ask-text").value, checksOf(w), F.text(w.at("ask-clock")), on(w, "ask-stop", "ask-talk"), w.clock.pending()],
    [Q, [false, true, false], "1:30", ["ask-stop"], 1]);
  w.clock.advance(89999);
  assert.equal(F.text(w.at("ask-clock")), "0:01");
  w.clock.advance(1);
  assert.deepEqual([F.text(w.at("ask-clock")), on(w, "ask-stop", "ask-talk"), w.clock.pending(), talkOf(w).end], ["끝 · 2:00", ["ask-talk"], 0, F.T0 + 120000]);
  const dead = await asked();
  F.type(dead.at("ask-text"), Q);
  F.press(dead.at("ask-talk"));
  const late = await asked({ storage: dead.storage, now: F.T0 + 600000 });               // 끝을 적지 못하고 죽었다 — 열자마자 끝난 것으로 본다
  assert.deepEqual([F.text(late.at("ask-clock")), on(late, "ask-stop"), off(late, "ask-save")], ["끝 · 2:00", [], false]);
  F.press(late.at("ask-save"));
  assert.deepEqual(late.wrote().map(r => [r.sec, r.t]), [[120, "2026-10-13T08:40:00+09:00"]]);
});

test("질문 시계: 다른 화면에 가 있는 동안 끝나도 그 화면에 그리지 않는다 — 돌아오면 끝나 있고, 끝난 뒤에는 다시 말할 수 있다", async () => {
  const w = await asked();
  F.press(w.at("ask-talk"));
  F.press(F.byK(w.doc, "set")[0]);
  w.clock.advance(120000);
  assert.deepEqual([shown(w, "ask-"), talkOf(w).end], [[], F.T0 + 120000]);
  F.press(F.byK(w.doc, "ask")[0]);
  assert.deepEqual([F.text(w.at("ask-clock")), on(w, "ask-stop", "ask-talk")], ["끝 · 2:00", ["ask-talk"]]);
  F.press(w.at("ask-talk"));                                                             // 다시 말한다 — 앞의 것은 버린다
  w.clock.advance(10000);
  assert.deepEqual([F.text(w.at("ask-clock")), talkOf(w).at, talkOf(w).end, on(w, "ask-stop", "ask-talk")], ["1:50", F.T0 + 120000, null, ["ask-stop"]]);
});

test("질문 날짜 경계: 말한 뒤 공부 날짜가 바뀌었으면 어제의 시계는 싣지 않는다 — 03:59:59에는 그 초로, 04:00:00에는 0초로 새 날에 적힌다", async () => {
  const run = async at => {
    const w = await asked({ now: kstMs("2026-10-13T23:00:00") });
    F.type(w.at("ask-text"), Q);
    F.press(w.at("ask-talk"));
    w.clock.advance(120000);
    w.clock.set(kstMs(at));                                                              // 화면은 켜 둔 채였다(돌아옴 사건이 없다)
    F.press(w.at("ask-save"));
    return w.wrote().map(r => [r.d, r.sec, r.t]);
  };
  assert.deepEqual(await run("2026-10-14T03:59:59"), [["2026-10-13", 120, "2026-10-14T03:59:59+09:00"]]);
  assert.deepEqual(await run("2026-10-14T04:00:00"), [["2026-10-14", 0, "2026-10-14T04:00:00+09:00"]]);
});

test("질문 맞춤: 다른 기기의 줄을 받거나 화면으로 돌아와도 질문 화면은 그대로다 — 쓰던 칸 · 체크 · 시계를 건드리지 않는다", async () => {
  const w = await asked();
  F.type(w.at("ask-text"), "쓰는 중");
  F.press(w.at("ask-head"));
  F.press(w.at("ask-talk"));
  w.clock.advance(30000);
  const [input, face] = [w.at("ask-text"), w.at("ask-clock")];
  receive(w, [line("q", { text: "다른 기기의 질문", sec: 60, rec: 0, s_head: true, s_two: true, s_wrong: true }, "2026-10-13T08:00:00", "q001")]);
  w.fire("visibilitychange", "visible");
  assert.deepEqual([w.at("ask-text") === input, input.value, checksOf(w), w.at("ask-clock") === face, F.text(face), w.clock.pending(), /다른 기기/.test(F.text(w.at("st-main")))],
    [true, "쓰는 중", [true, false, false], true, "1:30", 1, false]);
  w.clock.advance(1000);
  assert.equal(F.text(face), "1:29");                                                    // 같은 시계가 이어서 간다
});

// ── 질문: 최근 질문 · [가리기] ──
const q = (text, at, rand) => line("q", { text, sec: 60, rec: 0, s_head: true, s_two: false, s_wrong: false }, at, rand);
const SIX = [1, 2, 3, 4, 5, 6].map(n => q("질문 " + n, "2026-10-0" + n + "T22:00:00", "q00" + n));     // 엿새 동안 하나씩
const listed = w => F.byTag(w.at("ask-list"), "li").map(li => F.text(F.byTag(li, "span")[0]));

test("질문 최근: 늦은 것부터 5개 — 없으면 '아직 없다', 저장하면 맨 위에 올라온다", async () => {
  const empty = await asked();
  assert.deepEqual(shown(empty, "ask-"), ["ask-text", "ask-warn", "ask-rule", "ask-talk", "ask-head", "ask-two", "ask-wrong", "ask-save", "ask-list"]);
  assert.deepEqual([empty.at("ask-list").tag, listed(empty), F.byClass(empty.at("st-main"), "st-dim").map(n => F.text(n)), F.byTag(empty.at("st-main"), "h2").map(n => F.text(n))],
    ["ul", [], [C.T.ASK_RULE, C.T.ASK_EMPTY], [C.T.ASK_RECENT]]);
  const w = await asked({ storage: device(SIX) });
  assert.deepEqual([listed(w), F.byClass(w.at("st-main"), "st-dim").length], [["질문 6", "질문 5", "질문 4", "질문 3", "질문 2"], 1]);
  const rows = F.byTag(w.at("ask-list"), "li");
  assert.deepEqual([rows.map(li => li.getAttribute("data-k")), F.byClass(rows[0], "ask-hide").map(n => [n.tag, n.getAttribute("class"), n.getAttribute("type"), F.text(n)])],
    [SIX.slice(1).reverse().map(idOf), [["button", "st-btn ask-hide", "button", C.T.ASK_HIDE]]]);
  F.type(w.at("ask-text"), Q);
  F.press(w.at("ask-save"));
  assert.deepEqual(listed(w), [Q, "질문 6", "질문 5", "질문 4", "질문 3"]);
});

test("질문 가리기: [가리기]를 누르면 가림 줄이 적히고 그 줄이 빠진다 — 여섯째가 올라오고, 쓰던 칸 · 체크 · 시계는 남는다", async () => {
  const w = await asked({ storage: device(SIX) });
  F.type(w.at("ask-text"), "쓰는 중");
  F.press(w.at("ask-two"));
  F.press(w.at("ask-talk"));
  w.clock.advance(30000);
  F.press(F.byClass(F.byK(w.at("ask-list"), idOf(SIX[4]))[0], "ask-hide")[0]);           // '질문 5'를 가린다
  assert.deepEqual([w.wrote().map(r => [r.k, r.ref, r.hide]), listed(w)], [[["fix", idOf(SIX[4]), true]], ["질문 6", "질문 4", "질문 3", "질문 2", "질문 1"]]);
  assert.deepEqual([w.at("ask-text").value, checksOf(w), F.text(w.at("ask-clock")), w.clock.pending()], ["쓰는 중", [false, true, false], "1:30", 1]);
  const again = await asked({ storage: w.storage, now: F.T0 + 60000 });                  // 다시 열어도 가려져 있다. 줄은 지워지지 않았다(달 사본에 그대로 있다)
  assert.deepEqual([listed(again), F.plain(again.S.monthLines("2026-10")).filter(text => text === SIX[4]).length], [["질문 6", "질문 4", "질문 3", "질문 2", "질문 1"], 1]);
});

test("질문 최근: 받은 글에 꺾쇠가 있어도 요소가 생기지 않는다 — 다른 기기의 질문은 화면을 다시 열면 보인다", async () => {
  const sharp = "<b onclick=alert(1)>굵게</b><img src=x>";
  const w = await asked({ storage: device([q(sharp, "2026-10-12T22:00:00", "q001")]) });
  assert.deepEqual([listed(w), F.byTag(w.doc, "b").length, F.byTag(w.doc, "img").length], [[sharp], 0, 0]);
  receive(w, [q("다른 기기의 질문", "2026-10-13T08:00:00", "q002")]);
  assert.deepEqual(listed(w), [sharp]);                                                  // 맞춤은 질문 화면을 바꾸지 않는다
  F.press(F.byK(w.doc, "ask")[0]);
  assert.deepEqual(listed(w), ["다른 기기의 질문", sharp]);
});

test("주간 · 질문: 열쇠가 없으면 바깥 요청 0번 — 판정 · 채점 · 공유 · 질문 · 가리기 · 돌아옴을 다 해도. 다른 쪽으로 가는 링크도 없다", async () => {
  const w = await open({ hash: "#week", storage: device([PAST]), share: "ok" });
  fillCall(w);
  F.press(w.at("wk-save"));
  F.press(w.at("wk-save"));
  fillGrade(w);
  F.press(w.at("gr-save"));
  F.press(w.at("wk-share"));
  const links = F.byTag(w.at("st-main"), "a").length;
  F.press(F.byK(w.doc, "ask")[0]);
  F.type(w.at("ask-text"), Q);
  F.press(w.at("ask-talk"));
  w.clock.advance(120000);
  F.press(w.at("ask-save"));
  F.press(F.byClass(w.at("ask-list"), "ask-hide")[0]);
  w.fire("visibilitychange", "visible");
  await F.settle();
  assert.deepEqual([w.wrote().map(r => r.k), w.shared.length, w.net.calls.length, w.net.unexpected, F.text(w.at("st-status"))],
    [["week", "grade", "q", "fix"], 1, 0, 0, C.T.ST_LOCAL]);
  assert.deepEqual([links, F.byTag(w.at("st-main"), "a").length, F.byTag(w.at("st-main"), "audio").length, listed(w)], [0, 0, 0, []]);
});
