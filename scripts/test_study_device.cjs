"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const F = require("./study_fakes.cjs");

// 공부 화면의 기기 쪽 테스트 — 설정 화면의 연결 · 열쇠 · 상태 줄 · 단추(settings.js). 뼈대 문서가 싣는 그대로(F.boot) 싣는다.
// 실제 통신 0번, 실제 시간 0초. 지어낸 글만 쓴다(주인 · 저장소는 owner · repo, 열쇠는 F.KEY). 돌리기: node --test scripts/test_study_device.cjs
const LS = "macro-study.";                                                         // 저장 이름의 머리(화면 쪽 상수 P와 같은 글자)
const C = F.world(["core.js"]).scope.StudyCore;
const TODAY = "2026-10-13";                                                        // 기준 시각(F.T0 = KST 10-13 화 08:30)의 공부 날짜
const kstMs = text => Date.parse(text + "+09:00");                                 // KST로 적은 시각의 ms
// 지어낸 줄: at은 KST 시각, rand는 줄마다 달리 준다. 기본은 이 기기(폰)가 쓴 줄이다
const next = (at, text, rand, dev = "폰") => F.line("next", { text }, { ms: kstMs(at), dev, rand });
// 이 기기의 저장 공간. 기본은 이름만 있는 기기다(연결 전). mine은 이 기기가 쓴 줄(달 사본과 대기 줄에), got은 받은 줄(달 사본에만),
// 그 밖의 것은 저장값 그대로(객체는 JSON으로 적는다)
function device({ mine = [], got = [], ...more } = {}) {
  const all = [...got, ...mine];
  const months = [...new Set(all.map(text => C.lineMonth(text) || "2026-10"))].sort();
  const copies = months.map(month => ["m." + month, all.filter(text => (C.lineMonth(text) || "2026-10") === month).join("\n")]);
  const seed = { dev: "폰", ...(months.length > 0 ? { months: JSON.stringify(months) } : {}), ...(mine.length > 0 ? { q: JSON.stringify(mine) } : {}),
    ...Object.fromEntries(copies), ...more };
  return F.fakeStorage(Object.fromEntries(Object.entries(seed).map(pair => [LS + pair[0], typeof pair[1] === "string" ? pair[1] : JSON.stringify(pair[1])])));
}
// 설정 화면을 연다. seed는 device()에 줄 것, routes는 가짜 통신이 차례로 내줄 응답. at(id)는 그 id의 요소(없으면 null)
async function open(seed = {}, routes = [], opts = {}) {
  const w = await F.boot({ hash: "#set", storage: device(seed), net: F.fakeNet(routes), ...opts });
  return Object.assign(w, { A: w.scope.StudyApp, S: w.scope.StudyStore, at: id => F.byId(w.doc, id) });
}
const stored = (w, name) => (w.storage.data.has(LS + name) ? w.storage.data.get(LS + name) : null);   // 저장 공간에 적힌 값 그대로
const rowsOf = w => F.byClass(w.at("set-g-state"), "st-row").map(n => [n.getAttribute("data-k"), F.text(n)]);
const row = (w, k) => F.text(F.byK(w.at("set-g-state"), k)[0]);                    // 상태 줄 하나의 글자

// ── 설정: 상태 줄 ── 03의 넷(webapp · persist · queue · version)에 맞춤의 다섯(key · lastsync · lasterr · bad · clash)이 끼어든다
test("설정 상태 줄: 아홉 줄의 차례 — 연결하지 않았고 맞춘 적 없는 기기의 처음 모습", async () => {
  const w = await open();
  assert.deepEqual(rowsOf(w), [["webapp", "웹앱으로 열림: —"], ["persist", "오래 두기: —"], ["key", "열쇠: 없음"], ["queue", "올릴 것: 0건"],
    ["lastsync", "마지막 맞춤: —"], ["lasterr", "마지막 오류: 없음"], ["bad", "꼴이 맞지 않는 줄: 0개"], ["clash", "같은 id 충돌: 0건"], ["version", "판: " + w.A.VERSION]]);
  assert.deepEqual([row(await open({ key: F.KEY }), "key"), row(await open({ key: "k".repeat(59) }), "key")], ["열쇠: 있음", "열쇠: 없음"]);
  assert.deepEqual([w.net.calls.length, w.net.unexpected], [0, 0]);
});

test("설정 상태 줄: 마지막 맞춤은 오늘이면 시각만, 다른 날이면 날짜도 — 마지막 오류는 상태 코드와 고정 문구뿐이다", async () => {
  const synced = async at => row(await open({ sync: { at: kstMs(at) } }), "lastsync");
  assert.deepEqual([await synced("2026-10-13T08:10:00"), await synced("2026-10-13T03:30:00"), await synced("2026-10-12T21:05:00"), await synced("2026-09-30T23:59:00")],
    ["마지막 맞춤: 08:10", "마지막 맞춤: 03:30", "마지막 맞춤: 10-12 21:05", "마지막 맞춤: 09-30 23:59"]);
  const night = await open({ sync: { at: kstMs("2026-10-14T01:00:00") } }, [], { now: kstMs("2026-10-14T02:00:00") });   // 새벽: 공부 날짜는 어제지만 달력으로는 같은 날이다
  assert.equal(row(night, "lastsync"), "마지막 맞춤: 01:00");
  const failed = async err => row(await open({ sync: { err } }), "lasterr");
  assert.deepEqual([await failed({ code: 403, key: "ERR_HALT" }), await failed({ code: 500, key: "ERR_SERVER" }), await failed({ code: 409, key: "ERR_RACE" })],
    ["마지막 오류: 403 요청 거절", "마지막 오류: 500 서버", "마지막 오류: 409 겹침"]);
  assert.deepEqual([await failed({ code: 0, key: "ERR_NET" }), await failed({ code: 0, key: "ERR_TIMEOUT" }), await failed({ code: 0, key: "ERR_BIG" })],
    ["마지막 오류: 통신", "마지막 오류: 시간 초과", "마지막 오류: 사본이 큼"]);                             // 상태 코드가 까닭이 아니면 0을 보이지 않는다
  assert.deepEqual([await failed({ code: "403", key: "ERR_HALT" }), await failed({ code: 403, key: "<b>굵게</b>" }), await failed(null)],
    Array(3).fill("마지막 오류: 없음"));                                                                    // 꼴이 맞지 않는 저장값은 없는 것으로 읽는다
});

test("설정 상태 줄: 꼴이 맞지 않는 줄은 받은 파일의 것과 이 기기 사본의 것을 더하고, 같은 id에 글자가 다른 줄을 센다 — 맞춤이 알리면 다시 그린다", async () => {
  const twin = [next("2026-10-12T21:00:00", "볼록성", "c001", "PC"), next("2026-10-12T21:00:00", "캐리", "c001", "PC")];      // id가 같고 글자가 다르다
  const w = await open({ got: [...twin, "{깨진 줄", "꼴이 아닌 줄", next("2026-10-11T21:00:00", "기간 프리미엄", "g001", "PC")], sync: { bad: 3 } });
  assert.deepEqual([row(w, "bad"), row(w, "clash"), row(w, "queue")], ["꼴이 맞지 않는 줄: 5개", "같은 id 충돌: 1건", "올릴 것: 0건"]);       // 받은 파일의 3 + 사본의 2
  w.S.setSyncState({ bad: 0, at: F.T0, err: { code: 0, key: "ERR_FILE" } });
  w.A.refresh("sync");
  assert.deepEqual([row(w, "bad"), row(w, "lastsync"), row(w, "lasterr")], ["꼴이 맞지 않는 줄: 2개", "마지막 맞춤: 08:30", "마지막 오류: 파일"]);
});

// ── 설정: 자동 맞춤 멈춤/켬 · [지금 맞춤] ── 여기부터는 진짜 맞춤(sync.js)을 가짜 통신으로 돌린다
const BASE = "https://api.github.com/repos/owner/repo";
const LINKED = { owner: "owner", repo: "repo", key: F.KEY };                       // 연결을 마친 기기의 저장값
const CHECKED = { repo: { d: TODAY, state: "ok" } };                               // 오늘 저장소 확인을 이미 지난 기기의 맞춤 상태
const MINE = next("2026-10-13T08:00:00", "기간 프리미엄", "m001");                       // 이 기기가 오늘 쓴 줄(아직 올리지 못했다)
const short = call => call.method + " " + call.url.replace(BASE, "");              // "GET /contents/log/2026-10.jsonl"
const sent = w => w.net.calls.map(short);
const REPO = "GET ";
const GET9 = "GET /contents/log/2026-09.jsonl";
const GET10 = "GET /contents/log/2026-10.jsonl";
const PUT10 = "PUT /contents/log/2026-10.jsonl";
const REPO_OK = { status: 200, body: F.ghRepo() };
const NONE = { status: 404, body: { message: "Not Found" } };
const done = (sha = "s2", status = 201) => ({ status, body: { content: { sha } } });
const status = w => F.text(w.at("st-status"));                                     // 맨 위 상태 줄
const pauseOf = w => [F.text(w.at("set-pause")), w.at("set-pause").getAttribute("aria-pressed"), stored(w, "pause")];
const LONE = F.scripts().filter(name => name !== "sync.js").map(name => '<script src="' + name + '"></script>').join("");   // 맞춤 모듈(sync.js)을 싣지 않는 뼈대
// 누르고 약속이 끝나기를 기다린다
async function tap(w, id) {
  F.press(w.at(id));
  await F.settle();
}

test("설정 자동 맞춤: 단추 하나로 멈추고 켠다 — 글자 · 눌림 · 저장값 · 상태 줄이 함께 바뀌고, 쓰던 칸은 그대로다", async () => {
  const w = await open({ ...LINKED, sync: CHECKED }, [NONE, NONE]);
  const [knob, name] = [w.at("set-pause"), w.at("set-dev")];
  assert.deepEqual([knob.tag, knob.getAttribute("class"), knob.getAttribute("type"), F.all(w.at("set-g-dev")).includes(knob), pauseOf(w), status(w), sent(w)],
    ["button", "st-btn", "button", true, ["자동 맞춤: 켬", "false", null], "맞춤 08:30", [GET9, GET10]]);
  F.type(name, "쓰는중");
  await tap(w, "set-pause");
  assert.deepEqual([pauseOf(w), status(w), w.S.syncState().repo], [["자동 맞춤: 멈춤", "true", "1"], C.T.ST_PAUSED, null]);
  assert.deepEqual([w.at("set-pause") === knob, w.at("set-dev") === name, name.value, w.net.calls.length, w.net.unexpected], [true, true, "쓰는중", 2, 0]);
});

test("설정 자동 맞춤: 멈추면 다시 열기 · [지금 맞춤] · 저장 · 돌아옴 어디에서도 요청 0번이다 — 대기 줄은 남는다", async () => {
  const seed = { ...LINKED, sync: CHECKED, pause: "1", mine: [MINE] };
  const w = await open(seed);
  assert.deepEqual([pauseOf(w), status(w), w.at("set-syncnow").hasAttribute("disabled")], [["자동 맞춤: 멈춤", "true", "1"], C.T.ST_PAUSED, false]);
  await tap(w, "set-syncnow");
  assert.equal(w.A.write("next", { text: "볼록성" }).stored, true);
  await F.settle();
  w.fire("visibilitychange", "hidden");
  w.fire("visibilitychange", "visible");
  w.clock.advance(60000);
  await F.settle();
  assert.deepEqual([w.net.calls.length, w.net.unexpected, w.S.queue().length, status(w)], [0, 0, 2, C.T.ST_PAUSED]);
  const again = await F.boot({ storage: w.storage, net: F.fakeNet([]) });                       // 같은 기기를 다시 열었다
  assert.deepEqual([again.net.calls.length, again.net.unexpected, F.text(F.byId(again.doc, "st-status"))], [0, 0, C.T.ST_PAUSED]);
});

test("설정 자동 맞춤: 다시 켜면 곧바로 한 번 맞춘다 — 저장소 확인부터 다시 하고, 쌓인 줄이 올라간다", async () => {
  const w = await open({ ...LINKED, sync: CHECKED, pause: "1", mine: [MINE] }, [REPO_OK, NONE, NONE, done()]);
  await tap(w, "set-pause");
  assert.deepEqual([sent(w), pauseOf(w), w.S.queue().length, status(w)], [[REPO, GET9, GET10, PUT10], ["자동 맞춤: 켬", "false", "0"], 0, "맞춤 08:30"]);
  assert.deepEqual([row(w, "queue"), row(w, "lastsync"), w.net.unexpected], ["올릴 것: 0건", "마지막 맞춤: 08:30", 0]);
});

test("설정 [지금 맞춤]: 10초 창을 기다리지 않고 곧바로 돈다 — 연결하지 않았거나 주인 이름이 꼴에 어긋난 기기에서는 요청 0번이다", async () => {
  const w = await open({ ...LINKED, sync: CHECKED }, [NONE, NONE, NONE, NONE]);
  const ids = F.all(w.at("st-main")).map(n => n.getAttribute("id"));
  assert.deepEqual([F.text(w.at("set-syncnow")), ids.indexOf("set-iconnote") < ids.indexOf("set-syncnow"), ids.indexOf("set-syncnow") < ids.indexOf("set-reload"), sent(w)],
    [C.T.SET_SYNCNOW, true, true, [GET9, GET10]]);
  await tap(w, "set-syncnow");                                                                  // 방금 연 뒤라 자동 맞춤이면 10초를 기다렸을 것이다
  assert.deepEqual([sent(w), w.clock.pending(), w.net.unexpected], [[GET9, GET10, GET9, GET10], 0, 0]);
  const offs = [[{}, C.T.ST_LOCAL], [{ ...LINKED, key: "k".repeat(59) }, C.T.ST_LOCAL], [{ ...LINKED, owner: "a/b" }, "올릴 것 1건"], [{ ...LINKED, repo: ".." }, "올릴 것 1건"]];
  for (const [seed, line] of offs) {
    const off = await open({ ...seed, mine: [MINE] });
    await tap(off, "set-syncnow");
    assert.deepEqual([off.net.calls.length, off.net.unexpected, status(off)], [0, 0, line]);
  }
});

test("설정: 맞춤 모듈이 실리지 않았거나 던져도 화면은 돈다 — 멈춤 단추는 저장값을 바꾸고, [지금 맞춤]은 아무 일도 하지 않는다", async () => {
  const boom = () => { throw new Error("지어낸 고장"); };
  for (const extra of [{}, { StudySync: { init: boom, request: boom, reset: boom, snapshot: boom } }]) {
    const w = await open({ ...LINKED, mine: [MINE] }, [], { html: LONE, extra });
    assert.deepEqual([w.scope.StudySync === extra.StudySync, pauseOf(w)], [true, ["자동 맞춤: 켬", "false", null]]);
    await tap(w, "set-pause");
    await tap(w, "set-syncnow");
    assert.deepEqual([pauseOf(w), status(w), w.net.calls.length, w.net.unexpected], [["자동 맞춤: 멈춤", "true", "1"], C.T.ST_PAUSED, 0, 0]);
  }
});

// ── 설정: 연결 묶음 — 주인 · 저장소 이름 · 열쇠 칸 ──
const PLAIN = { enterkeyhint: "done", autocomplete: "off", autocapitalize: "off", autocorrect: "off", spellcheck: "false" };   // 칸이 글을 채우거나 고치지 않는다
const attrsOf = node => Object.fromEntries(node.attrs);                             // 요소의 속성 전부
const labels = w => F.byTag(w.at("set-g-conn"), "label").map(n => [n.getAttribute("for"), F.text(n)]);

test("설정 연결: 주인 · 저장소 이름 칸과 열쇠 칸 — 열쇠 칸은 글자 가림 모양의 일반 글 칸이고, 저장된 열쇠를 되돌려 넣지 않는다", async () => {
  const w = await open({ ...LINKED, pause: "1" });
  const [group, ids] = [w.at("set-g-conn"), F.all(w.at("st-main")).map(n => n.getAttribute("id"))];
  assert.deepEqual([group.tag, group.getAttribute("class"), F.text(F.byTag(group, "h2")[0]), ids.indexOf("set-g-dev") < ids.indexOf("set-g-conn"), ids.indexOf("set-g-conn") < ids.indexOf("set-g-state")],
    ["section", "st-group", C.T.SET_G_CONN, true, true]);
  assert.deepEqual(labels(w), [["set-owner", "주인"], ["set-repo", "저장소 이름"], ["set-key", "열쇠"]]);
  assert.deepEqual(attrsOf(w.at("set-owner")), { id: "set-owner", class: "st-input", type: "text", value: "owner", ...PLAIN });
  assert.deepEqual(attrsOf(w.at("set-repo")), { id: "set-repo", class: "st-input", type: "text", value: "repo", ...PLAIN });
  const key = w.at("set-key");
  assert.deepEqual(attrsOf(key), { id: "set-key", class: "st-input st-secret", type: "text", placeholder: C.T.SET_KEY_PH, ...PLAIN });
  assert.deepEqual([key.tag, key.value, key.parent === group, w.at("set-keynote"), row(w, "key")], ["input", "", true, null, "열쇠: 있음"]);
  assert.deepEqual([F.byTag(w.doc, "form").length, F.all(w.doc, n => n.getAttribute("type") === "password" || n.hasAttribute("name")).length, w.net.calls.length], [0, 0, 0]);
});

test("설정 연결: https로 열리지 않았으면 열쇠 칸이 없다 — 대신 한 줄이 있고, 열쇠를 받을 곳이 화면에 없다", async () => {
  for (const protocol of ["http:", "file:"]) {
    const w = await open({}, [], { protocol });
    assert.deepEqual([w.at("set-key"), F.byClass(w.doc, "st-secret").length, labels(w)], [null, 0, [["set-owner", "주인"], ["set-repo", "저장소 이름"]]], protocol);
    const note = w.at("set-keynote");
    assert.deepEqual([note.tag, note.getAttribute("class"), F.text(note), note.parent === w.at("set-g-conn")], ["p", "st-dim", C.T.SET_KEY_HTTP, true]);
    assert.deepEqual([w.at("set-owner") !== null, w.at("set-repo") !== null, w.net.calls.length], [true, true, 0]);
  }
});

test("설정 연결: 주인 · 저장소 이름은 치는 즉시 적는다 — 글자마다 그날의 저장소 확인을 지우되 요청은 보내지 않고, 다음 맞춤이 그 이름으로 간다", async () => {
  const w = await open({ key: F.KEY, owner: "ownre", repo: "repo", sync: { repo: { d: TODAY, state: "missing" } } }, [REPO_OK, NONE, NONE]);
  const [owner, repo] = [w.at("set-owner"), w.at("set-repo")];
  assert.deepEqual([owner.value, status(w), w.scope.StudySync.snapshot().stop], ["ownre", C.T.ST_REPO_MISSING, "missing"]);    // 어제 친 오타가 '없음'으로 남아 있다
  F.type(owner, "o");
  assert.deepEqual([stored(w, "owner"), w.S.syncState().repo, w.scope.StudySync.snapshot().stop, status(w)], ["o", null, null, C.T.ST_SYNC_WAIT]);
  F.type(owner, " owner ");
  F.type(repo, "repo ");
  await F.settle();
  assert.deepEqual([stored(w, "owner"), stored(w, "repo"), w.net.calls.length], [" owner ", "repo ", 0]);              // 친 글자 그대로 적고, 치는 것만으로는 요청이 없다
  assert.deepEqual([w.at("set-owner") === owner, owner.value, w.at("set-repo") === repo, repo.value], [true, " owner ", true, "repo "]);
  await tap(w, "set-syncnow");
  assert.deepEqual([sent(w), status(w), w.net.unexpected], [[REPO, GET9, GET10], "맞춤 08:30", 0]);                    // 앞뒤 공백은 맞춤이 떼고 본다
  for (const [input, name] of [[repo, "repo"], [owner, "owner"]]) {                                                    // 열쇠를 이 칸에 잘못 붙였다 — 적지 않고 칸을 비운 뒤 한 줄로 알린다
    F.type(input, "my-" + F.KEY);
    assert.deepEqual([input.value, stored(w, name), answer(w), leak(w)], ["", "", C.T.WARN_SECRET, { dom: [], store: ["key"] }], name);
    w.fire("visibilitychange", "hidden");                                                                              // 다녀오고 60초가 지나도 그 글이 실린 요청은 없다
    w.fire("visibilitychange", "visible");
    w.clock.advance(60000);
    await F.settle();
    assert.deepEqual([w.net.calls.length, w.net.unexpected], [3, 0], name);
  }
});

// ── 설정: [연결 확인] — 열쇠를 적고 칸을 비운 뒤 저장소 정보를 한 번 읽는다 ──
const NAMED = { owner: "owner", repo: "repo" };                                    // 주인 · 저장소 이름만 넣은 기기(열쇠는 아직 없다)
const answer = w => F.text(w.at("set-checkout"));                                  // [연결 확인]의 결과 한 줄
// 가짜 열쇠 글자가 남아 있는 곳: 화면의 요소(글자 · 속성 · 칸의 값)와 저장 공간의 이름
function leak(w) {
  const held = n => [...n.attrs.values(), F.text(n), n.value].some(v => String(v).includes(F.KEY));
  const named = [...w.storage.data].filter(pair => (pair[0] + pair[1]).includes(F.KEY)).map(pair => pair[0].replace(LS, ""));
  return { dom: F.all(w.doc, held).map(n => n.getAttribute("id") || n.tag), store: named };
}
// 열쇠 칸에 붙여 넣고 [연결 확인]을 누른다
async function paste(w, text) {
  F.type(w.at("set-key"), text);
  await tap(w, "set-check");
}

test("설정 [연결 확인]: 붙여 넣은 열쇠를 적고 곧바로 칸을 비운다 — 열쇠 글자는 화면 글자 · 속성 · 쓰던 글 어디에도 없고 인증 머리 한 곳에만 실린다", async () => {
  const w = await open({ ...NAMED, mine: [MINE] }, [REPO_OK, NONE, NONE, done()]);
  const [check, out] = [w.at("set-check"), w.at("set-checkout")];
  assert.deepEqual([check.tag, F.text(check), check.parent === w.at("set-g-conn"), out.tag, out.getAttribute("role"), answer(w)], ["button", C.T.SET_CHECK, true, "p", "status", ""]);
  F.type(w.at("set-key"), "  " + F.KEY + "\n");
  assert.deepEqual(leak(w), { dom: ["set-key"], store: [] });                                    // 치는 동안에는 그 칸에만 있다 — 어디에도 적지 않는다
  await tap(w, "set-check");
  assert.deepEqual([w.at("set-key").value, stored(w, "key") === F.KEY, leak(w)], ["", true, { dom: [], store: ["key"] }]);
  assert.deepEqual([answer(w), row(w, "key"), sent(w), status(w), stored(w, "draft"), F.text(w.at("st-note"))],
    [C.T.CONN_OK, "열쇠: 있음", [REPO, GET9, GET10, PUT10], "맞춤 08:30", null, ""]);                 // 연결되면 쌓인 줄이 곧바로 올라간다
  for (const call of w.net.calls) {
    assert.deepEqual([JSON.stringify(call).split(F.KEY).length - 1, call.headers.Authorization], [1, "Bearer " + F.KEY], short(call));
  }
  assert.deepEqual([w.net.unexpected, check.hasAttribute("disabled")], [0, false]);
});

test("설정 [연결 확인]: 열쇠 꼴이 아니면 적지 않고 요청도 없다 — 칸은 비우고 한 줄로 알린다. 자판의 완료도 [연결 확인]이다", async () => {
  const w = await open(NAMED, [REPO_OK, NONE, NONE]);
  const key = w.at("set-key");
  for (const bad of ["abc", "k".repeat(59), "k".repeat(30) + " " + "k".repeat(34), "k".repeat(63) + "-", "k".repeat(256)]) {
    await paste(w, bad);
    assert.deepEqual([answer(w), key.value, stored(w, "key"), w.net.calls.length], [C.T.SET_KEY_BAD, "", null, 0], String(bad.length));
  }
  await tap(w, "set-check");                                                                     // 빈 칸으로 누르면 넣을 것부터 알린다
  assert.deepEqual([answer(w), w.net.calls.length], [C.T.CONN_UNSET, 0]);
  F.type(key, F.KEY);
  F.key(key, "Enter", { isComposing: true });
  assert.deepEqual([key.value, stored(w, "key")], [F.KEY, null]);
  F.key(key, "Enter");
  await F.settle();
  assert.deepEqual([key.value, stored(w, "key") === F.KEY, answer(w), sent(w), w.net.unexpected], ["", true, C.T.CONN_OK, [REPO, GET9, GET10], 0]);
});

test("설정 [연결 확인]: 결과 한 줄은 문구 표의 글이다 — 공개 · Pages 켜짐 · 없음 · 열쇠 거절 · 그 밖의 오류 · 통신. 연결되지 않으면 맞춤도 없다", async () => {
  const cases = [
    [{ status: 200, body: F.ghRepo({ private: false }) }, "공개 상태 — 올리지 않습니다", C.T.ST_REPO_PUBLIC],
    [{ status: 200, body: F.ghRepo({ has_pages: true }) }, "공개 상태 — 올리지 않습니다", C.T.ST_REPO_PUBLIC],
    [NONE, "저장소를 찾지 못함", C.T.ST_REPO_MISSING],
    [{ status: 401, body: {} }, "열쇠 다시 넣기", C.T.ST_REKEY],
    [{ status: 403, body: {} }, "확인하지 못함 — 오류 403", "맞춤 멈춤 — 오류 403"],
    [{ status: 500, body: {} }, "확인하지 못함 — 오류 500", C.T.ST_SYNC_WAIT],
    [new Error("지어낸 끊김"), "확인하지 못함 — 통신", C.T.ST_SYNC_WAIT],
  ];
  for (const [route, text, line] of cases) {
    const w = await open(NAMED, [route]);
    await paste(w, F.KEY);
    assert.deepEqual([answer(w), status(w), sent(w), w.net.unexpected, w.at("set-check").hasAttribute("disabled"), leak(w).dom], [text, line, [REPO], 0, false, []]);
  }
  const lone = await open(NAMED, [], { html: LONE });                                            // 맞춤 모듈이 실리지 않았으면 물을 손이 없다
  await paste(lone, F.KEY);
  assert.deepEqual([answer(lone), lone.at("set-key").value, lone.at("set-check").hasAttribute("disabled"), lone.net.calls.length], [C.T.CONN_NET, "", false, 0]);
});

test("설정 [연결 확인]: 자동 맞춤을 멈췄어도 확인은 된다 — 그 뒤의 맞춤은 없고 대기 줄은 남는다", async () => {
  const w = await open({ ...LINKED, pause: "1", mine: [MINE] }, [REPO_OK]);
  await tap(w, "set-check");
  assert.deepEqual([answer(w), sent(w), w.net.unexpected, w.S.queue().length, status(w)], [C.T.CONN_OK, [REPO], 0, 1, C.T.ST_PAUSED]);
});

test("설정 [연결 확인]: 답을 기다리는 동안 단추는 꺼져 있다 — 그 사이 설정을 바꾸거나 화면을 떠나면 그 답은 버린다", async () => {
  const w = await open({ ...NAMED, pause: "1", sync: { repo: { d: TODAY, state: "missing" } } }, ["hang", REPO_OK, REPO_OK, "hang"]);
  await paste(w, F.KEY);
  assert.deepEqual([w.at("set-check").hasAttribute("disabled"), answer(w), w.net.calls.length], [true, "", 1]);
  assert.deepEqual([row(w, "key"), w.S.syncState().repo, w.at("set-key").value], ["열쇠: 있음", null, ""]);          // 열쇠를 적은 것은 곧바로 보이고, 그날의 저장소 확인은 지워졌다
  await tap(w, "set-check");                                                                     // 꺼진 단추와 자판의 완료는 겹쳐 보내지 않는다
  F.key(w.at("set-key"), "Enter");
  await F.settle();
  assert.equal(w.net.calls.length, 1);
  F.type(w.at("set-repo"), "repo2");                                                             // 이름을 고쳤다 — 앞의 물음은 옛 이름의 것이다
  await F.settle();
  assert.deepEqual([w.at("set-check").hasAttribute("disabled"), answer(w), w.net.calls.length], [false, "", 1]);
  await tap(w, "set-check");
  assert.deepEqual([answer(w), w.net.calls.map(call => call.url).slice(1)], [C.T.CONN_OK, ["https://api.github.com/repos/owner/repo2"]]);
  F.type(w.at("set-owner"), "owner2");                                                           // 이름을 또 고치면 앞의 결과 한 줄도 지운다(옛 이름의 것이다)
  assert.equal(answer(w), "");
  await tap(w, "set-check");
  assert.equal(answer(w), C.T.CONN_OK);
  await tap(w, "set-check");                                                                     // 다시 묻는 동안에는 앞의 결과를 지워 둔다. 답이 오기 전에 다른 화면에 다녀온다
  assert.deepEqual([answer(w), w.at("set-check").hasAttribute("disabled")], ["", true]);
  F.press(F.byK(w.doc, "today")[0]);
  F.press(F.byK(w.doc, "set")[0]);
  w.clock.advance(15000);
  await F.settle();
  assert.deepEqual([w.at("set-check").hasAttribute("disabled"), answer(w), w.net.calls.length, w.net.unexpected], [false, "", 4, 0]);
});

test("설정 [연결 확인]: 저장 공간이 말을 듣지 않아 열쇠를 적지 못해도 칸은 비우고 확인은 한다 — 상태 줄은 붉은 한 줄이다", async () => {
  const storage = device(NAMED);
  storage.failOn(/\.key$/);
  const w = await open({}, [REPO_OK, NONE, NONE], { storage });
  await paste(w, F.KEY);
  assert.deepEqual([w.at("set-key").value, leak(w), w.net.calls[0].headers.Authorization], ["", { dom: [], store: [] }, "Bearer " + F.KEY]);
  assert.deepEqual([answer(w), row(w, "key"), status(w), w.at("st-status").getAttribute("class"), sent(w)],
    [C.T.CONN_OK, "열쇠: 있음", C.T.ST_STORE_FAIL, "st-status st-red", [REPO, GET9, GET10]]);
});

test("설정 [연결 확인]: 열쇠가 거절된 뒤에는 눌러도 요청 0번이다 — 새 열쇠를 넣으면 거절 표시를 지우고 다시 묻는다", async () => {
  const w = await open({ ...LINKED, auth: "401", mine: [MINE] }, [REPO_OK, NONE, NONE, done()]);
  await tap(w, "set-check");
  await tap(w, "set-syncnow");
  assert.deepEqual([answer(w), status(w), w.net.calls.length, stored(w, "auth")], [C.T.CONN_AUTH, C.T.ST_REKEY, 0, "401"]);
  await paste(w, "n".repeat(64));
  assert.deepEqual([answer(w), stored(w, "auth"), sent(w), w.net.calls.map(call => call.headers.Authorization === "Bearer " + "n".repeat(64)), status(w)],
    [C.T.CONN_OK, "ok", [REPO, GET9, GET10, PUT10], [true, true, true, true], "맞춤 08:30"]);
});

// ── 설정: 열쇠 만들기 묶음 · [이 기기에서 열쇠 지우기] ──
test("설정 열쇠 만들기: 미리 채운 링크와 안내 일곱 줄 — 링크에는 기기 이름과 이번 달뿐이고, 주인 · 저장소 이름 · 열쇠는 없다", async () => {
  const w = await open({ ...LINKED, pause: "1" });
  const [group, link, steps, ids] = [w.at("set-g-key"), w.at("set-keylink"), w.at("set-keysteps"), F.all(w.at("st-main")).map(n => n.getAttribute("id"))];
  assert.deepEqual([group.tag, group.getAttribute("class"), F.text(F.byTag(group, "h2")[0]), ids.indexOf("set-g-conn") < ids.indexOf("set-g-key"), ids.indexOf("set-g-key") < ids.indexOf("set-g-state")],
    ["section", "st-group", C.T.SET_G_KEY, true, true]);
  assert.deepEqual(attrsOf(link), { id: "set-keylink", class: "st-btn", rel: "noopener noreferrer", target: "_blank",
    href: "https://github.com/settings/personal-access-tokens/new?name=note-%ED%8F%B0-202610&expires_in=90&contents=write" });
  assert.deepEqual([link.tag, F.text(link), /owner|repo/.test(link.getAttribute("href")), leak(w).dom], ["a", C.T.SET_KEYLINK, false, []]);
  assert.deepEqual([steps.tag, steps.parent === group, F.byTag(steps, "li").map(n => F.text(n))], ["ol", true, [1, 2, 3, 4, 5, 6, 7].map(n => C.T["KEYSTEP_" + n])]);
  assert.deepEqual([F.byTag(w.doc, "a").filter(a => !a.getAttribute("href").startsWith("#")).length, w.net.calls.length], [1, 0]);   // 바깥으로 가는 링크는 이것 하나다
});

test("설정 열쇠 만들기: 기기 이름을 바꾸거나 달이 넘어가면 링크의 이름 칸도 바뀐다 — 그대로면 링크를 새로 만들지 않는다", async () => {
  const w = await open();
  const [link, name] = [w.at("set-keylink"), () => decodeURIComponent(w.at("set-keylink").getAttribute("href").split("name=")[1].split("&")[0])];
  w.A.refresh("sync");
  assert.deepEqual([w.at("set-keylink") === link, name()], [true, "note-폰-202610"]);
  F.type(w.at("set-dev"), "PC");
  F.press(w.at("set-devsave"));
  assert.deepEqual([name(), w.at("set-keylink") === link, F.all(w.at("set-g-key"), n => n.tag === "a").length], ["note-PC-202610", false, 1]);
  w.clock.set(kstMs("2026-11-01T00:00:10"));
  w.A.refresh("back");
  assert.equal(name(), "note-PC-202611");
});

test("설정 [이 기기에서 열쇠 지우기]: 열쇠와 거절 표시를 지운다 — 그 뒤에는 어디서도 요청 0번이고 기록은 이 기기에만 남는다", async () => {
  const w = await open({ ...LINKED, auth: "401", pause: "1", mine: [MINE] });
  const ids = F.all(w.at("st-main")).map(n => n.getAttribute("id"));
  assert.deepEqual([F.text(w.at("set-keyclear")), ids.indexOf("set-reload") < ids.indexOf("set-keyclear"), row(w, "key"), status(w)], [C.T.SET_KEYCLEAR, true, "열쇠: 있음", C.T.ST_REKEY]);
  F.type(w.at("set-key"), F.KEY);                                                                // 칸에 붙여만 두고 [연결 확인]은 누르지 않았다
  await tap(w, "set-keyclear");
  assert.equal(w.at("set-key").value, "");                                                       // 지우면 칸에 붙여 둔 글도 비운다
  assert.deepEqual([stored(w, "key"), stored(w, "auth"), row(w, "key"), status(w), leak(w)], [null, "ok", "열쇠: 없음", C.T.ST_LOCAL, { dom: [], store: [] }]);
  await tap(w, "set-pause");                                                                     // 멈춤을 풀어도 열쇠가 없으니 맞춤은 없다
  await tap(w, "set-syncnow");
  await tap(w, "set-check");
  assert.deepEqual([w.net.calls.length, w.net.unexpected, answer(w), w.S.queue().length, stored(w, "owner")], [0, 0, C.T.CONN_UNSET, 1, "owner"]);
});

// ── 설정: [사본 비우고 다시 받기] — 자동 맞춤을 멈췄을 때만 ──
const THEIRS = next("2026-10-12T21:00:00", "볼록성", "t001", "PC");                    // 기록 저장소에 있는 줄(다른 기기가 썼다)
const WIPED = next("2026-10-11T21:00:00", "지운 줄", "g001", "PC");                    // 전에 받았지만 기록 저장소에서는 지운 줄
const file = (lines, sha = "s1") => ({ status: 200, body: F.ghFile(lines.map(text => text + "\n").join(""), sha) });
const pullNote = w => F.text(w.at("set-repullnote"));
const copyOf = (w, month = "2026-10") => F.plain(w.S.monthLines(month)).sort();     // 이 기기의 그 달 사본

test("설정 [사본 비우고 다시 받기]: 자동 맞춤을 멈췄을 때만 켜진다 — 멈추지 않았으면 눌리지 않고, 사본도 그대로다", async () => {
  const w = await open({ ...LINKED, sync: CHECKED, got: [WIPED] }, [NONE, file([WIPED]), "hang"]);
  const [knob, note, ids] = [w.at("set-repull"), w.at("set-repullnote"), F.all(w.at("st-main")).map(n => n.getAttribute("id"))];
  assert.deepEqual([F.text(knob), knob.hasAttribute("disabled"), note.tag, note.getAttribute("class"), pullNote(w)], [C.T.SET_REPULL, true, "p", "st-dim", C.T.SET_REPULL_NOTE]);
  assert.deepEqual([ids.indexOf("set-keyclear") < ids.indexOf("set-repull"), ids.indexOf("set-repull") < ids.indexOf("set-repullnote")], [true, true]);
  await tap(w, "set-check");                                                                     // (답을 기다리는 물음이 하나 있다)
  await tap(w, "set-repull");                                                                    // 꺼진 단추는 눌리지 않는다
  for (const fn of knob.on.click) fn({});                                                        // 누름이 닿았더라도 하지 않는다 — 묻던 것도 끊지 않는다
  await F.settle();
  assert.deepEqual([sent(w), copyOf(w), pullNote(w), w.at("set-check").hasAttribute("disabled")], [[GET9, GET10, REPO], [WIPED], C.T.SET_REPULL_NOTE, true]);
  await tap(w, "set-pause");
  assert.deepEqual([w.at("set-repull") === knob, knob.hasAttribute("disabled")], [true, false]);
  await tap(w, "set-keyclear");                                                                  // 열쇠가 없으면 받을 수 없다 — 요청 없이 알린다
  await tap(w, "set-repull");
  assert.deepEqual([pullNote(w), copyOf(w), w.net.calls.length, w.net.unexpected], [C.T.CONN_UNSET, [WIPED], 3, 0]);
});

test("설정 [사본 비우고 다시 받기]: 이 기기의 사본을 비우고 받기만 한다 — 지운 줄은 되살아나지 않고, 올리지 못한 줄은 남으며, 올리기는 없다", async () => {
  const w = await open({ ...LINKED, pause: "1", got: [WIPED], mine: [MINE] }, [NONE, file([THEIRS])]);
  assert.deepEqual([copyOf(w), w.at("set-repull").hasAttribute("disabled")], [[WIPED, MINE].sort(), false]);
  await tap(w, "set-repull");
  assert.deepEqual([sent(w), copyOf(w), F.plain(w.S.queue()), pullNote(w)], [[GET9, GET10], [MINE, THEIRS].sort(), [MINE], C.T.SET_REPULL_NOTE]);
  assert.deepEqual([w.at("set-repull").hasAttribute("disabled"), row(w, "queue"), status(w)], [false, "올릴 것: 1건", C.T.ST_PAUSED]);
  w.clock.advance(60000);
  await F.settle();
  assert.deepEqual([w.net.calls.filter(call => call.method !== "GET").length, w.net.calls.length, w.net.unexpected], [0, 2, 0]);
});

test("설정 [사본 비우고 다시 받기]: 받지 못하면 까닭을 그 아래 한 줄로 알린다 — 올리지 못한 줄은 그때도 남는다", async () => {
  const junk = { status: 200, body: F.ghFile("쓰레기 ".repeat(70000), "s1") };                          // 약 770KB — 읽지 않는다
  const cases = [[[new Error("지어낸 끊김")], {}, "확인하지 못함 — 통신", 1], [[{ status: 500, body: {} }], {}, "확인하지 못함 — 오류 500", 1],
    [[NONE, junk], {}, C.T.ST_FILE, 2], [[], { auth: "401" }, C.T.CONN_AUTH, 0], [[], {}, "확인하지 못함 — 통신", 0, { html: LONE }]];
  for (const [routes, more, text, calls, opts] of cases) {
    const w = await open({ ...LINKED, pause: "1", got: [WIPED], mine: [MINE], ...more }, routes, opts);
    await tap(w, "set-repull");
    assert.deepEqual([pullNote(w), w.net.calls.length, w.net.unexpected, F.plain(w.S.queue()), w.at("set-repull").hasAttribute("disabled")], [text, calls, 0, [MINE], false]);
    F.type(w.at("set-owner"), "owner");                                                          // 설정을 고치면 그 까닭 한 줄은 늘 있던 안내 글로 돌아간다
    assert.equal(pullNote(w), C.T.SET_REPULL_NOTE);
  }
});

test("설정 [사본 비우고 다시 받기]: 받는 동안 단추는 꺼져 있다 — 묻던 [연결 확인]은 끊고, 그 사이 자동 맞춤을 켜면 받던 답도 버린다", async () => {
  const w = await open({ ...LINKED, pause: "1", got: [WIPED] }, ["hang", "hang", "hang", REPO_OK, NONE, file([THEIRS])]);
  const off = id => w.at(id).hasAttribute("disabled");
  await tap(w, "set-check");
  await tap(w, "set-repull");                                                                    // 받기는 돌던 요청을 끊는다 — 끊긴 물음의 답("통신")을 적지 않는다
  assert.deepEqual([off("set-repull"), off("set-check"), answer(w), sent(w), copyOf(w)], [true, false, "", [REPO, GET9], []]);
  await tap(w, "set-repull");
  assert.equal(w.net.calls.length, 2);
  F.type(w.at("set-repo"), "repo");                                                              // 설정을 고치면 받던 것을 끊고 단추를 다시 켠다
  await F.settle();
  assert.deepEqual([off("set-repull"), pullNote(w), w.net.calls.length], [false, C.T.SET_REPULL_NOTE, 2]);
  await tap(w, "set-repull");
  assert.deepEqual([off("set-repull"), w.net.calls.length], [true, 3]);
  F.press(F.byK(w.doc, "today")[0]);                                                             // 다른 화면에 다녀오면 단추는 다시 켜져 있다
  F.press(F.byK(w.doc, "set")[0]);
  assert.deepEqual([off("set-repull"), pullNote(w)], [false, C.T.SET_REPULL_NOTE]);
  await tap(w, "set-pause");                                                                     // 자동 맞춤을 켰다 — 받던 것은 끊기고, 켠 맞춤이 사본을 다시 채운다
  assert.deepEqual([sent(w), copyOf(w), pullNote(w), off("set-repull"), status(w), w.net.unexpected],
    [[REPO, GET9, GET9, REPO, GET9, GET10], [THEIRS], C.T.SET_REPULL_NOTE, true, "맞춤 08:30", 0]);
});
