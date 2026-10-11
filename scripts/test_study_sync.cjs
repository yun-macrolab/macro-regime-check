"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const F = require("./study_fakes.cjs");

// 공부 화면의 맞춤 테스트 — sync.js를 가짜 통신으로 본다. 실제 통신 0번, 실제 시간 0초.
// 지어낸 글만 쓴다(주인 · 저장소는 owner · repo, 열쇠는 F.KEY). 돌리기: node --test scripts/test_study_sync.cjs
const LS = "macro-study.";                                                         // 저장 이름의 머리(화면 쪽 상수 P와 같은 글자)
const C = F.world(["core.js"]).scope.StudyCore;
const SYNC_FILES = ["core.js", "store.js", "sync.js"];
const BASE = "https://api.github.com/repos/owner/repo";
const CFG = { owner: "owner", repo: "repo", key: F.KEY };
const kstMs = text => Date.parse(text + "+09:00");                                 // KST로 적은 시각의 ms
// 지어낸 줄: at은 KST 시각, rand는 줄마다 달리 준다. 기본은 이 기기(폰)가 쓴 줄이다
const line = (kind, fields, at, rand, dev = "폰") => F.line(kind, fields, { ms: kstMs(at), dev, rand });
const next = (at, text, rand, dev) => line("next", { text }, at, rand, dev);
const MINE = next("2026-10-13T08:00:00", "기간 프리미엄", "m001");                       // 이 기기가 오늘 쓴 줄
const THEIRS = next("2026-10-12T21:00:00", "볼록성", "t001", "PC");                    // 다른 기기가 어제 쓴 줄

// ── sync.js: 요청의 꼴 · 응답 표 · base64 ── 순수한 것들(StudySync._)
const Y = F.world(SYNC_FILES).scope.StudySync;
const HEADS = { Accept: "application/vnd.github+json", Authorization: "Bearer " + F.KEY, "X-GitHub-Api-Version": "2026-03-10" };
const FIXED = { cache: "no-store", credentials: "omit", referrerPolicy: "no-referrer", redirect: "error" };

test("맞춤 요청의 꼴: 주소는 한 꼴이다 — 저장소 정보 · 달 파일 받기 · 올리기의 방법 · 머리 · 선택값이 약속 그대로다", () => {
  const signal = { aborted: false };
  const repo = F.plain(Y._.buildRequest("repo", CFG, { signal }));
  assert.deepEqual(repo, { url: BASE, init: { method: "GET", headers: HEADS, ...FIXED, signal } });
  const get = F.plain(Y._.buildRequest("get", CFG, { month: "2026-10" }));
  assert.deepEqual(get, { url: BASE + "/contents/log/2026-10.jsonl", init: { method: "GET", headers: HEADS, ...FIXED } });
  const put = F.plain(Y._.buildRequest("put", CFG, { month: "2026-09", body: { message: "log: 2026-09 +1", content: "eA==", sha: "abc" } }));
  assert.deepEqual([put.url, put.init.method, put.init.headers], [BASE + "/contents/log/2026-09.jsonl", "PUT", { ...HEADS, "Content-Type": "application/json" }]);
  assert.deepEqual([JSON.parse(put.init.body), Object.keys(put.init).sort()],
    [{ message: "log: 2026-09 +1", content: "eA==", sha: "abc" }, ["body", "cache", "credentials", "headers", "method", "redirect", "referrerPolicy"]]);
  for (const made of [repo, get, put]) assert.deepEqual([made.init.cache, made.init.credentials, made.init.referrerPolicy, made.init.redirect], Object.values(FIXED));
  assert.deepEqual(Object.keys(HEADS).filter(name => /cache-control|pragma/i.test(name)), []);       // 사전 요청에서 막히는 머리는 넣지 않는다
});

test("맞춤 요청의 꼴: 올리기의 본문은 message · content와, 있을 때만 sha다 — 커밋에 남길 이름은 보내지 않는다", () => {
  const body = extra => JSON.parse(Y._.buildRequest("put", CFG, { month: "2026-10", body: extra }).init.body);
  assert.deepEqual(body({ message: "m", content: "c", sha: null }), { message: "m", content: "c" });
  assert.deepEqual(body({ message: "m", content: "c", sha: "" }), { message: "m", content: "c" });
  assert.deepEqual(body({ message: "m", content: "c", sha: "s9", committer: { name: "x" }, author: { name: "y" }, branch: "b" }), { message: "m", content: "c", sha: "s9" });
});

test("맞춤 요청의 꼴: 주인 · 저장소 이름 · 달 · 열쇠가 꼴에 어긋나면 null이다 — 요청을 만들지 않는다", () => {
  const made = (kind, cfg, extra) => Y._.buildRequest(kind, { ...CFG, ...cfg }, extra);
  const owners = ["", "a/b", "-a", "a-", "a b", "a..b", "../x", "owner?x=1", "owner#", null, 7];
  assert.deepEqual(owners.filter(owner => made("repo", { owner }) !== null), []);
  const repos = ["", ".", "..", "a/b", "a b", "repo?x", "repo#x", "a%2Fb", "한글", null];
  assert.deepEqual(repos.filter(repo => made("repo", { repo }) !== null), []);
  const months = ["2026-13", "2026-00", "2026-1", "202610", "2026-10-13", "2026-10/../x", "", null, undefined, 202610];
  assert.deepEqual(months.filter(month => made("get", {}, { month }) !== null || made("put", {}, { month, body: {} }) !== null), []);
  assert.deepEqual(["", "k".repeat(59), F.KEY + " ", F.KEY + "\n", null].filter(key => made("repo", { key }) !== null), []);
  assert.deepEqual([made("del", {}, { month: "2026-10" }), made(undefined, {}), Y._.buildRequest("repo"), Y._.buildRequest("repo", null, null)], [null, null, null, null]);
  assert.equal(made("repo", { owner: "a-b", repo: "a.b_c-d" }).url, "https://api.github.com/repos/a-b/a.b_c-d");
});

test("맞춤 응답 표: 상태 코드마다 처리 이름 — 표에 없는 4xx는 멈춤, 5xx와 통신 오류는 나중에", () => {
  assert.deepEqual(F.plain(Y._.RESPONSES), {
    repo: { 0: "later", 200: "check", 401: "auth", 404: "missing", c4: "halt", c5: "later" },
    get: { 0: "later", 200: "merge", 401: "auth", 404: "empty", c4: "halt", c5: "later" },
    put: { 0: "later", 200: "done", 201: "done", 401: "auth", 404: "missing", 409: "retry", 422: "retry", c4: "halt", c5: "later" },
  });
  const row = kind => [200, 201, 401, 403, 404, 409, 410, 422, 429, 500, 503, 0].map(status => Y._.classify(kind, status));
  assert.deepEqual(row("repo"), ["check", "later", "auth", "halt", "missing", "halt", "halt", "halt", "halt", "later", "later", "later"]);
  assert.deepEqual(row("get"), ["merge", "later", "auth", "halt", "empty", "halt", "halt", "halt", "halt", "later", "later", "later"]);
  assert.deepEqual(row("put"), ["done", "done", "auth", "halt", "missing", "retry", "halt", "retry", "halt", "later", "later", "later"]);
  assert.deepEqual([100, 204, 301, 304, 600, -1, 1.5, NaN, "200", "c4", null].map(status => Y._.classify("get", status)), Array(11).fill("later"));
  assert.deepEqual([Y._.classify("del", 200), Y._.classify("constructor", 200), Object.isFrozen(Y._.RESPONSES), Object.isFrozen(Y._.RESPONSES.put)], ["later", "later", true, true]);
});

test("맞춤 base64: 한글과 그림 글자가 60자 줄바꿈을 지나 그대로 돌아온다 — 풀리지 않으면 null이다", () => {
  const text = [MINE, THEIRS, next("2026-10-13T08:01:00", "곡선 😀 — 5y5y", "m002")].join("\n") + "\n";
  const file = F.ghFile(text, "s1");
  assert.deepEqual([Y._.fromB64(file.content), Y._.fromB64(Y._.toB64(text)), Y._.toB64(text)], [text, text, Buffer.from(text, "utf8").toString("base64")]);
  assert.deepEqual([file.content.split("\n").every(row => row.length <= 60), /[\r\n]/.test(Y._.toB64(text)), Y._.fromB64(""), Y._.toB64("")], [true, false, "", ""]);
  const big = "가나다라마바사아자차카타파하".repeat(15000);                                       // 약 630KB — 배열을 펼치면 인자 수 한도에 걸리는 크기
  assert.equal(Y._.fromB64(Y._.toB64(big)) === big, true);
  assert.deepEqual([Y._.fromB64("%%%"), Y._.fromB64("a"), Y._.fromB64(null)], [null, null, null]);
});

test("맞춤: 약속된 상수가 모두 있다 — 커밋 메시지는 달과 건수뿐이다", () => {
  const consts = ["API", "API_VERSION", "TIMEOUT_MS", "THROTTLE_MS", "RETRY_MS", "MAX_TRIES", "SHA_TTL_MS", "MAX_FILE_BYTES"].map(name => Y._[name]);
  assert.deepEqual(consts, ["https://api.github.com/repos/", "2026-03-10", 15000, 10000, 1100, 3, 60000, 614400]);
  assert.deepEqual(Object.keys(Y._).sort(), ["API", "API_VERSION", "MAX_FILE_BYTES", "MAX_TRIES", "RESPONSES", "RETRY_MS", "SHA_TTL_MS", "THROTTLE_MS", "TIMEOUT_MS",
    "buildRequest", "classify", "commitMsg", "fromB64", "toB64"]);
  assert.deepEqual([Y._.commitMsg("2026-10", 2), Y._.commitMsg("2026-09", 1)], ["log: 2026-10 +2", "log: 2026-09 +1"]);
});

// ── sync.js: 문지기 · 연결 확인 ── 여기부터는 가짜 통신과 가짜 저장 공간으로 돌린다
// 연결을 마친 기기의 저장 공간: 이름 · 주인 · 저장소 · 가짜 열쇠. mine은 이 기기가 쓴 줄(달 사본과 대기 줄에), got은 받은 줄(달 사본에만),
// 그 밖의 것은 저장값 그대로(null을 주면 그 값을 뺀다 — 예: { key: null })
function device({ mine = [], got = [], ...more } = {}) {
  const all = [...got, ...mine];
  const months = [...new Set(all.map(text => C.lineMonth(text)))].sort();
  const copies = months.map(month => ["m." + month, all.filter(text => C.lineMonth(text) === month).join("\n")]);
  const seed = { dev: "폰", owner: "owner", repo: "repo", key: F.KEY, ...(months.length > 0 ? { months: JSON.stringify(months) } : {}),
    ...(mine.length > 0 ? { q: JSON.stringify(mine) } : {}), ...Object.fromEntries(copies), ...more };
  return F.fakeStorage(Object.fromEntries(Object.entries(seed).filter(pair => pair[1] !== null).map(pair => [LS + pair[0], pair[1]])));
}
// 맞춤만 싣는다(틀 없이). routes는 가짜 통신이 차례로 내줄 응답, seen에는 맞춤이 틀에 알린 것이 차례로 쌓인다
function open(routes = [], opts = {}) {
  const w = F.world(SYNC_FILES, { storage: device(), net: F.fakeNet(routes), ...opts });
  const seen = [];
  w.scope.StudySync.init((snap, info) => { seen.push({ ...F.plain(snap), ...F.plain(info) }); });
  return Object.assign(w, { Y: w.scope.StudySync, S: w.scope.StudyStore, seen });
}
// 맞춤을 청하고 약속이 끝나기를 기다린다
async function ask(w, reason = "manual") {
  w.Y.request(reason);
  await F.settle();
  return w;
}
const short = call => call.method + " " + call.url.replace(BASE, "");                // "GET /contents/log/2026-10.jsonl"
const sent = w => w.net.calls.map(short);
const state = w => F.plain(w.S.syncState());
const snap = w => F.plain(w.Y.snapshot());
// 가짜 응답들
const REPO = "GET ";
const GET9 = "GET /contents/log/2026-09.jsonl";
const GET10 = "GET /contents/log/2026-10.jsonl";
const PUT10 = "PUT /contents/log/2026-10.jsonl";
const REPO_OK = { status: 200, body: F.ghRepo() };
const NONE = { status: 404, body: { message: "Not Found" } };
const code = status => ({ status, body: { message: "지어낸 응답" } });
const file = (lines, sha = "s1", over) => ({ status: 200, body: F.ghFile(lines.map(text => text + "\n").join(""), sha, over) });
const done = (sha = "s2", status = 200) => ({ status, body: { content: { sha } } });
const TODAY = "2026-10-13";
const CHECKED = JSON.stringify({ repo: { d: TODAY, state: "ok" } });               // 오늘 저장소 확인을 이미 지난 기기

test("연결 확인: 저장소 정보 읽기 한 번 — 비공개이고 Pages가 꺼져 있으면 '연결됨'이고, 그날의 저장소 확인으로 적는다", async () => {
  const w = open([REPO_OK]);
  assert.deepEqual(F.plain(await w.Y.checkConn()), { key: "CONN_OK", code: 200 });
  const call = w.net.calls[0];
  assert.deepEqual([w.net.calls.length, call.url, call.method, call.headers, call.body], [1, BASE, "GET", HEADS, null]);
  assert.deepEqual([call.cache, call.credentials, call.referrerPolicy, call.redirect], Object.values(FIXED));
  assert.deepEqual([state(w).repo, state(w).err, snap(w).stop, w.seen.length, w.clock.pending()], [{ d: TODAY, state: "ok" }, null, null, 1, 0]);
});

test("연결 확인: 공개 · Pages 켜짐 · 없음 · 열쇠 거절 · 그 밖의 4xx · 5xx · 통신 오류마다 문구 키가 다르고, 표의 처리대로 적는다", async () => {
  const run = async route => { const w = open([route]); return [F.plain(await w.Y.checkConn()), state(w).repo, state(w).err, w.S.getConn().auth, snap(w)]; };
  const idle = stop => ({ phase: "idle", stop, code: null, failedThisOpen: false });
  assert.deepEqual(await run({ status: 200, body: F.ghRepo({ private: false }) }),
    [{ key: "CONN_PUBLIC", code: 200 }, { d: TODAY, state: "public" }, { code: 0, key: "ERR_PUBLIC" }, "ok", idle("public")]);
  assert.deepEqual((await run({ status: 200, body: F.ghRepo({ has_pages: true }) }))[0], { key: "CONN_PUBLIC", code: 200 });
  assert.deepEqual((await run({ status: 200, body: "not json" }))[0], { key: "CONN_PUBLIC", code: 200 });           // 읽지 못한 답은 지난 것으로 치지 않는다
  assert.deepEqual((await run({ status: 200, body: { private: "true", has_pages: false } }))[0].key, "CONN_PUBLIC");
  assert.deepEqual(await run(NONE), [{ key: "CONN_MISSING", code: 404 }, { d: TODAY, state: "missing" }, { code: 404, key: "ERR_MISSING" }, "ok", idle("missing")]);
  assert.deepEqual(await run(code(401)), [{ key: "CONN_AUTH", code: 401 }, null, { code: 401, key: "ERR_AUTH" }, "401", idle("auth")]);
  assert.deepEqual(await run(code(403)), [{ key: "CONN_ERR", code: 403 }, null, { code: 403, key: "ERR_HALT" }, "ok", { ...idle("halt"), code: 403 }]);
  assert.deepEqual(await run(code(503)), [{ key: "CONN_ERR", code: 503 }, null, { code: 503, key: "ERR_SERVER" }, "ok", idle(null)]);
  assert.deepEqual(await run(new Error("끊김")), [{ key: "CONN_NET", code: 0 }, null, { code: 0, key: "ERR_NET" }, "ok", idle(null)]);
});

test("연결 확인: 15초 안에 답이 없으면 끊는다 — 통신 오류로 치고 시간 초과로 적는다", async () => {
  const w = open(["hang"]);
  let result = null;
  w.Y.checkConn().then(r => { result = F.plain(r); });
  await F.settle();
  w.clock.advance(14999);
  await F.settle();
  assert.deepEqual([result, w.clock.pending()], [null, 1]);
  w.clock.advance(1);
  await F.settle();
  assert.deepEqual([result, state(w).err, w.clock.pending(), w.net.calls.length], [{ key: "CONN_NET", code: 0 }, { code: 0, key: "ERR_TIMEOUT" }, 0, 1]);
});

test("연결 확인: 설정이 비었거나 열쇠가 거절된 뒤면 요청 0번 — 자동 맞춤을 멈췄어도, 그날 '없음'이었어도 확인은 된다", async () => {
  const none = async more => { const w = open([], { storage: device(more) }); return [F.plain(await w.Y.checkConn()), w.net.calls.length, w.net.unexpected]; };
  assert.deepEqual(await none({ key: null }), [{ key: "CONN_UNSET", code: null }, 0, 0]);
  assert.deepEqual(await none({ owner: "" }), [{ key: "CONN_UNSET", code: null }, 0, 0]);
  assert.deepEqual(await none({ repo: "a/b" }), [{ key: "CONN_UNSET", code: null }, 0, 0]);
  assert.deepEqual(await none({ auth: "401" }), [{ key: "CONN_AUTH", code: null }, 0, 0]);
  const gone = JSON.stringify({ repo: { d: TODAY, state: "missing" } });
  const w = open([REPO_OK], { storage: device({ pause: "1", sync: gone }) });
  assert.deepEqual([snap(w).stop, F.plain(await w.Y.checkConn()), state(w).repo.state, w.net.calls.length], ["paused", { key: "CONN_OK", code: 200 }, "ok", 1]);
  const spaced = open([REPO_OK], { storage: device({ owner: " owner ", repo: "repo\n" }) });                    // 앞뒤 공백은 떼고 본다
  assert.deepEqual([(await spaced.Y.checkConn()).key, spaced.net.calls[0].url], ["CONN_OK", BASE]);
});

test("연결 확인: 속에서 무엇이 던져도 약속은 거절하지 않는다 — 끊는 손(AbortController)이 없는 브라우저에서도 실패 값을 준다", async () => {
  const w = open([REPO_OK], { extra: { AbortController: null } });
  assert.deepEqual([F.plain(await w.Y.checkConn()), w.net.calls.length, state(w).repo], [{ key: "CONN_NET", code: null }, 0, null]);
});

test("문지기: 걸리는 까닭의 차례 — 열쇠 없음 · 잘못된 이름 > 열쇠 거절 > 멈춤 > 그날 확인한 저장소 상태. 어제 확인한 것은 묻지 않은 것이다", () => {
  const stop = more => snap(open([], { storage: device(more) })).stop;
  const repo = (state, d = TODAY) => JSON.stringify({ repo: { d, state } });
  assert.deepEqual([{ key: null }, { key: "k".repeat(59) }, { owner: "" }, { owner: "a/b" }, { owner: "-bad" }, { repo: ".." }, { repo: "" }].map(stop), Array(7).fill("off"));
  assert.deepEqual([stop({ key: null, auth: "401", pause: "1" }), stop({ auth: "401", pause: "1", sync: repo("missing") }), stop({ pause: "1", sync: repo("public") })],
    ["off", "auth", "paused"]);
  assert.deepEqual([stop({ sync: repo("missing") }), stop({ sync: repo("public") }), stop({ sync: repo("ok") }), stop({})], ["missing", "public", null, null]);
  assert.deepEqual([stop({ sync: repo("missing", "2026-10-12") }), stop({ sync: repo("public", "2026-10-12") })], [null, null]);
  const w = open([], { storage: device({ sync: repo("missing") }) });
  w.clock.set(kstMs("2026-10-14T03:59:59"));
  assert.equal(snap(w).stop, "missing");
  w.clock.set(kstMs("2026-10-14T04:00:00"));                                               // 공부 날짜가 바뀌었다
  assert.deepEqual([snap(w), w.net.calls.length], [{ phase: "idle", stop: null, code: null, failedThisOpen: false }, 0]);
});

// ── sync.js: 맞춤 한 번 ── 저장소 확인 → 달마다 받기 → 합치기 → 흡수 → 올리기
const PUT9 = "PUT /contents/log/2026-09.jsonl";
const bodyOf = call => JSON.parse(call.body);
const textOf = call => Buffer.from(bodyOf(call).content, "base64").toString("utf8");      // 올린 파일의 글
const linesOf = (w, month = "2026-10") => F.plain(w.S.monthLines(month)).sort();
const QUIET = { phase: "idle", stop: null, code: null, failedThisOpen: false };

test("맞춤 한 번: 저장소 확인 → 지난달 · 이번 달 받기 → 없는 파일(404)이면 sha 없이 새로 만든다 — 올린 줄은 대기 줄에서 빠지고 맞춘 시각을 적는다", async () => {
  const w = open([REPO_OK, NONE, NONE, done("s2", 201)], { storage: device({ mine: [MINE] }) });
  await ask(w, "open");
  assert.deepEqual(sent(w), [REPO, GET9, GET10, PUT10]);
  const put = w.net.calls[3];
  assert.deepEqual([Object.keys(bodyOf(put)), bodyOf(put).message, textOf(put), put.headers["Content-Type"]], [["message", "content"], "log: 2026-10 +1", MINE + "\n", "application/json"]);
  assert.deepEqual([F.plain(w.S.queue()), linesOf(w), state(w)], [[], [MINE], { at: F.T0, err: null, repo: { d: TODAY, state: "ok" }, bad: 0 }]);
  assert.deepEqual(w.seen, [{ ...QUIET, changed: false, big: false }]);
  w.net.push(NONE);
  w.net.push(file([MINE], "s2"));
  await ask(w);                                                                            // 저장소 확인은 그날 한 번이고, 올릴 것이 없으면 받기만 한다
  assert.deepEqual([sent(w).slice(4), w.net.unexpected, w.seen.length, w.clock.pending()], [[GET9, GET10], 0, 2, 0]);
});

test("문지기: 열쇠 없음 · 잘못된 이름 · 멈춤 · 401 뒤 · 그날 확인한 '없음' · '공개'에서는 열어도 돌아와도 저장해도 눌러도 요청 0번이다", async () => {
  const cases = [[{ key: null }, "off"], [{ key: "k".repeat(59) }, "off"], [{ owner: "" }, "off"], [{ owner: "a/b" }, "off"], [{ owner: "-bad" }, "off"],
    [{ repo: ".." }, "off"], [{ repo: "" }, "off"], [{ auth: "401" }, "auth"], [{ pause: "1" }, "paused"], [{ auth: "401", pause: "1" }, "auth"],
    [{ sync: JSON.stringify({ repo: { d: TODAY, state: "missing" } }) }, "missing"], [{ sync: JSON.stringify({ repo: { d: TODAY, state: "public" } }) }, "public"]];
  for (const [more, stop] of cases) {
    const w = open([], { storage: device({ mine: [MINE], ...more }) });
    for (const reason of ["open", "back", "save", "manual", "store-fail", "open"]) await ask(w, reason);
    w.clock.advance(60000);
    await F.settle();
    assert.deepEqual([snap(w), w.net.calls.length, w.net.unexpected, w.S.queue().length, w.seen, w.clock.pending()],
      [{ ...QUIET, stop }, 0, 0, 1, [], 0], JSON.stringify(more));
  }
});

test("맞춤: 가짜 열쇠 글자는 인증 머리 한 곳에만 있다 — 주소 · 본문 · 다른 머리 · 알린 것 · 다른 저장값 어디에도 없다", async () => {
  const w = open([REPO_OK, NONE, NONE, done("s2", 201)], { storage: device({ mine: [MINE] }) });
  const result = await w.Y.checkConn();
  await ask(w);
  assert.deepEqual(sent(w), [REPO, GET9, GET10, PUT10]);
  for (const call of w.net.calls) {
    const { Authorization, ...others } = call.headers;
    assert.equal(Authorization, "Bearer " + F.KEY);
    assert.equal(JSON.stringify([call.url, call.method, call.body, others]).includes(F.KEY), false, short(call));
    assert.deepEqual([call.url.startsWith(BASE), call.cache, call.credentials, call.referrerPolicy, call.redirect], [true, ...Object.values(FIXED)]);
  }
  const kept = [...w.storage.data].filter(pair => pair[0] !== LS + "key");
  assert.equal(JSON.stringify([result, w.seen, snap(w), kept]).includes(F.KEY), false);
});

test("맞춤: 모르는 까닭의 요청은 듣지 않는다 — 알림 함수가 없어도, 던져도, 속에서 무엇이 던져도 맞춤은 끝난다", async () => {
  const w = open([NONE, NONE, done("s2", 201)], { storage: device({ mine: [MINE], sync: CHECKED }) });
  for (const reason of ["", "sync", "OPEN", null, 7, {}]) await ask(w, reason);
  assert.equal(w.net.calls.length, 0);
  w.Y.init(() => { throw new Error("x"); });
  await ask(w);
  w.Y.init(null);
  w.net.push(NONE);
  w.net.push(file([MINE], "s2"));
  await ask(w, "store-fail");
  assert.deepEqual([sent(w), w.S.queue().length, w.net.unexpected, snap(w)], [[GET9, GET10, PUT10, GET9, GET10], 0, 0, QUIET]);
  const bare = open([], { storage: device({ mine: [MINE], sync: CHECKED }), extra: { AbortController: null } });   // 끊는 손이 없는 브라우저: 속에서 던져도 맞춤은 끝난다
  await ask(bare);
  assert.deepEqual([snap(bare), bare.net.calls.length, bare.seen.length, bare.S.queue().length], [QUIET, 0, 1, 1]);
});

test("맞춤: 다른 기기의 줄을 받아 사본에 더한다 — 차례 · 끝 줄바꿈 · CR만 다른 파일에는 올리지 않는다", async () => {
  const other = next("2026-10-13T07:00:00", "캐리", "t002", "PC");
  const crlf = { status: 200, body: F.ghFile(other + "\r\n" + MINE + "\r\n\r\n" + THEIRS + "\r\n", "s1") };          // 차례가 다르고 줄 끝이 CRLF, 빈 줄도 있다
  const w = open([NONE, crlf], { storage: device({ mine: [MINE], sync: CHECKED }) });
  await ask(w, "open");
  assert.deepEqual([sent(w), linesOf(w), F.plain(w.S.queue()), state(w).bad], [[GET9, GET10], [THEIRS, other, MINE].sort(), [], 0]);
  assert.deepEqual(w.seen, [{ ...QUIET, changed: true, big: false }]);                     // 사본에 줄이 더해졌다 — 내 줄은 이미 올라가 있어 대기 줄에서 빠진다
  const bare = { status: 200, body: F.ghFile(MINE + "\n" + THEIRS + "\n" + other, "s1") };   // 끝 줄바꿈이 없다
  w.net.push(NONE);
  w.net.push(bare);
  await ask(w);
  assert.deepEqual([sent(w).slice(2), w.seen[1].changed, w.net.unexpected], [[GET9, GET10], false, 0]);
});

test("맞춤: 깨진 줄과 모르는 판의 줄은 기기에 두지 않고 수만 센다 — 올릴 때는 받은 글자 그대로 싣는다", async () => {
  const broken = '{"v":1,"id":"깨진 줄';
  const v2 = THEIRS.replace('"v":1', '"v":2').replace("t001", "t009");
  const sept = next("2026-09-20T09:00:00", "지난달 줄", "s001", "PC");                       // 9월의 줄이 10월 파일에 들어 있다
  const w = open([NONE, file([v2, THEIRS, broken, sept], "s7"), done("s8")], { storage: device({ mine: [MINE], sync: CHECKED }) });
  await ask(w, "open");
  const put = w.net.calls[2];
  assert.deepEqual([sent(w), bodyOf(put).sha, bodyOf(put).message], [[GET9, GET10, PUT10], "s7", "log: 2026-10 +1"]);
  assert.equal(textOf(put), [THEIRS, MINE, sept, broken, v2].join("\n") + "\n");            // 꼴이 맞는 줄은 id 순, 나머지는 글자 순으로 뒤에
  assert.deepEqual([linesOf(w), F.plain(w.S.months()), state(w).bad, w.seen[0].changed, F.plain(w.S.queue())], [[THEIRS, MINE].sort(), ["2026-10"], 3, true, []]);
});

test("맞춤: 저장소 확인은 공부 날짜마다 한 번이다 — 공개이거나 Pages가 켜져 있으면 올리지 않고, 그날은 다시 묻지 않는다", async () => {
  for (const over of [{ has_pages: true }, { private: false }]) {
    const w = open([{ status: 200, body: F.ghRepo(over) }], { storage: device({ mine: [MINE] }) });
    await ask(w, "open");
    assert.deepEqual([sent(w), snap(w), state(w).repo, state(w).err, state(w).at], [[REPO], { ...QUIET, stop: "public", failedThisOpen: true }, { d: TODAY, state: "public" }, { code: 0, key: "ERR_PUBLIC" }, null]);
    for (const reason of ["manual", "save", "back"]) await ask(w, reason);
    assert.deepEqual([w.net.calls.length, w.net.unexpected, w.S.queue().length], [1, 0, 1]);
    w.clock.set(kstMs("2026-10-14T04:00:00"));                                             // 다음 공부 날짜 — 다시 묻는다
    for (const route of [REPO_OK, NONE, NONE, done("s2", 201)]) w.net.push(route);
    await ask(w);
    assert.deepEqual([sent(w).slice(1), state(w).repo, w.S.queue().length], [[REPO, GET9, GET10, PUT10], { d: "2026-10-14", state: "ok" }, 0]);
  }
});

test("맞춤 응답: 401이면 멈추고 기기에 적는다 — 다시 열어도 요청 0번이고, 새 열쇠를 넣으면 다시 돈다", async () => {
  const storage = device({ mine: [MINE], sync: CHECKED });
  const w = open([NONE, code(401)], { storage });
  await ask(w, "open");
  assert.deepEqual([sent(w), snap(w), w.S.getConn().auth, state(w).err, w.S.queue().length],
    [[GET9, GET10], { ...QUIET, stop: "auth", failedThisOpen: true }, "401", { code: 401, key: "ERR_AUTH" }, 1]);
  for (const reason of ["manual", "save", "back", "open"]) await ask(w, reason);
  const again = open([], { storage });                                                     // 화면을 다시 열었다
  for (const reason of ["open", "back", "save", "manual"]) await ask(again, reason);
  assert.deepEqual([w.net.calls.length, again.net.calls.length, again.net.unexpected, snap(again).stop], [2, 0, 0, "auth"]);
  again.S.setKey("n".repeat(64));
  for (const route of [NONE, NONE, done("s2", 201)]) again.net.push(route);
  await ask(again);
  assert.deepEqual([sent(again), again.net.calls[0].headers.Authorization, again.S.queue().length, snap(again)], [[GET9, GET10, PUT10], "Bearer " + "n".repeat(64), 0, QUIET]);
  const first = open([code(401)], { storage: device({ mine: [MINE] }) });                  // 저장소 확인에서 거절돼도 같다
  await ask(first, "open");
  assert.deepEqual([sent(first), snap(first).stop, first.S.getConn().auth], [[REPO], "auth", "401"]);
});

test("맞춤 응답: 그 밖의 4xx는 그 실행 동안만 멈춘다(다시 열면 한 번 더 한다) — 5xx · 통신 오류는 대기 줄을 두고 끝낸다", async () => {
  const storage = device({ mine: [MINE], sync: CHECKED });
  const w = open([NONE, NONE, code(403)], { storage });
  await ask(w, "open");
  assert.deepEqual([sent(w), snap(w), state(w).err, w.S.queue().length], [[GET9, GET10, PUT10], { ...QUIET, stop: "halt", code: 403, failedThisOpen: true }, { code: 403, key: "ERR_HALT" }, 1]);
  for (const reason of ["manual", "save", "back"]) await ask(w, reason);
  const again = open([NONE, NONE, done("s2", 201)], { storage });
  await ask(again, "open");
  assert.deepEqual([w.net.calls.length, w.net.unexpected, sent(again), again.S.queue().length, snap(again)], [3, 0, [GET9, GET10, PUT10], 0, QUIET]);
  for (const [route, err] of [[code(500), { code: 500, key: "ERR_SERVER" }], [code(503), { code: 503, key: "ERR_SERVER" }], [new Error("끊김"), { code: 0, key: "ERR_NET" }]]) {
    const later = open([NONE, NONE, route], { storage: device({ mine: [MINE], sync: CHECKED }) });
    await ask(later, "open");
    assert.deepEqual([sent(later), snap(later), state(later).err, state(later).at, later.S.queue().length], [[GET9, GET10, PUT10], { ...QUIET, failedThisOpen: true }, err, null, 1]);
    for (const next of [NONE, NONE, done("s2", 201)]) later.net.push(next);
    await ask(later);                                                                      // 멈추지 않는다 — 다음 맞춤에 올라간다
    assert.deepEqual([later.S.queue().length, state(later).err, state(later).at], [0, null, F.T0]);
  }
});

test("맞춤: 600KB를 넘는 파일 · base64가 아닌 응답 · 풀리지 않는 내용은 덮어쓰지 않고 멈춘다", async () => {
  const junk = "x".repeat(700000);
  const bodies = [F.ghFile(junk, "s1"), F.ghFile("", "s1", { size: 2000000, encoding: "none", content: "" }), F.ghFile(MINE, "s1", { encoding: "none" }),
    F.ghFile(MINE, "s1", { content: "%%%" }), F.ghFile(MINE, "s1", { sha: null }), F.ghFile(MINE, "s1", { size: undefined }), "not json", null];
  for (const body of bodies) {
    const w = open([NONE, { status: 200, body }], { storage: device({ mine: [MINE], sync: CHECKED }) });
    await ask(w, "open");
    assert.deepEqual([sent(w), snap(w), state(w).err, F.plain(w.S.queue()), linesOf(w)], [[GET9, GET10], { ...QUIET, stop: "file", failedThisOpen: true }, { code: 0, key: "ERR_FILE" }, [MINE], [MINE]]);
    for (const reason of ["manual", "save", "back"]) await ask(w, reason);
    assert.deepEqual([w.net.calls.length, w.net.unexpected], [2, 0]);
  }
});

test("맞춤 뒤의 도장: 600KB 쓰레기 파일을 받은 뒤에도 도장은 기기에 찍힌다 — 상태 줄은 '기록 파일을 읽지 못함'이고 요청은 더 없다", async () => {
  const net = F.fakeNet([NONE, { status: 200, body: F.ghFile("쓰레기 ".repeat(70000), "s1") }]);       // 약 770KB
  const w = await F.boot({ storage: device({ sync: CHECKED }), net });
  const at = id => F.byId(w.doc, id);
  assert.deepEqual([sent(w), F.text(at("st-status")), w.scope.StudySync.snapshot().stop], [[GET9, GET10], C.T.ST_FILE, "file"]);
  const r = w.scope.StudyApp.write("day", { mark: "min", sec: 120, rec: 0, stuck: "" });
  await F.settle();
  assert.deepEqual([r.ok, r.stored, F.text(at("td-done")), w.scope.StudyStore.queue().length, w.net.calls.length, w.net.unexpected, F.text(at("st-status"))],
    [true, true, "오늘 △ 08:30", 1, 2, 0, C.T.ST_FILE]);
  const junk = "y".repeat(500000);                                                         // 600KB에 못 미치는 쓰레기 한 줄은 글자 그대로 두고 내 줄만 얹는다
  const under = open([NONE, file([junk], "s1"), done("s2")], { storage: device({ mine: [MINE], sync: CHECKED }) });
  await ask(under, "open");
  assert.deepEqual([sent(under), textOf(under.net.calls[2]) === MINE + "\n" + junk + "\n", linesOf(under), state(under).bad], [[GET9, GET10, PUT10], true, [MINE], 1]);
});

test("맞춤: 사본이 300KB를 넘게 되는 달은 받지도 올리지도 않고 알린다 — 다른 달은 그대로 맞춘다", async () => {
  const q = i => line("q", { text: "가".repeat(200), sec: 0, rec: 0, s_head: false, s_two: false, s_wrong: false }, "2026-10-01T10:00:00", "b" + String(i).padStart(3, "0"), "PC");
  const many = Array.from({ length: 420 }, (unused, i) => q(i));                           // 꼴이 맞는 줄 약 320KB
  const old = next("2026-09-30T09:00:00", "지난달에 쓴 줄", "o001");
  const w = open([NONE, done("s2", 201), file(many, "s1")], { storage: device({ mine: [old, MINE], sync: CHECKED }) });
  await ask(w, "open");
  assert.deepEqual([sent(w), F.plain(w.S.queue()), linesOf(w), state(w)], [[GET9, PUT9, GET10], [MINE], [MINE], { at: F.T0, err: { code: 0, key: "ERR_BIG" }, repo: { d: TODAY, state: "ok" }, bad: 0 }]);
  assert.deepEqual(w.seen, [{ ...QUIET, changed: false, big: true }]);
});

// 가짜 기록 저장소 하나(두 기기가 함께 쓴다): 달 파일을 기억하고, sha가 낡았으면 409, 있는 파일에 sha 없이 쓰면 422를 준다
function hub() {
  const files = new Map();
  let n = 0;
  const serve = call => {
    const m = /\/contents\/log\/(\d{4}-\d{2})\.jsonl$/.exec(call.url);
    const had = m ? files.get(m[1]) : null;
    if (!m) return REPO_OK;
    if (call.method === "GET") return had ? { status: 200, body: F.ghFile(had.text, had.sha) } : NONE;
    if (had && bodyOf(call).sha !== had.sha) return code(bodyOf(call).sha ? 409 : 422);
    n += 1;
    files.set(m[1], { text: textOf(call), sha: "h" + n });
    return done("h" + n, had ? 200 : 201);
  };
  const net = F.fakeNet(Array(80).fill(serve));
  const puts = () => net.calls.filter(call => call.method === "PUT");
  return { net, puts, text: month => (files.has(month) ? files.get(month).text : null) };
}

test("맞춤 두 기기: 같은 id에 글자가 다른 줄 — 한 바퀴 뒤에는 더 올리지 않고, 파일에는 둘 다 남는다", async () => {
  const a = next("2026-10-13T08:00:00", "기간 프리미엄", "same");
  const b = a.replace("기간 프리미엄", "볼록성");                                             // 같은 id, 다른 글자
  const far = hub();
  const one = open([], { net: far.net, storage: device({ mine: [a], sync: CHECKED }) });
  const two = open([], { net: far.net, storage: device({ mine: [b], sync: CHECKED }) });
  await ask(one);
  await ask(two);                                                                          // 한 바퀴: 하나가 만들고, 다른 하나가 합쳐 올린다
  assert.deepEqual([far.puts().length, far.text("2026-10")], [2, [a, b].sort().join("\n") + "\n"]);
  for (const w of [one, two, one, two, two, one]) await ask(w);
  assert.deepEqual([far.puts().length, far.text("2026-10"), far.net.unexpected], [2, [a, b].sort().join("\n") + "\n", 0]);
  for (const w of [one, two]) {
    const view = C.buildView(F.plain(w.S.copies()));
    assert.deepEqual([F.plain(w.S.queue()), linesOf(w), view.clash, view.recs.length, view.recs[0].text], [[], [a, b].sort(), 1, 1, "기간 프리미엄"]);
  }
});

test("맞춤 두 기기: 번갈아 써도 서로의 줄을 받는다 — 한글이 깨지지 않고, 있는 파일에는 받은 sha를 붙여 올린다", async () => {
  const far = hub();
  const phone = open([], { net: far.net, storage: device({ mine: [MINE], sync: CHECKED }) });
  const pc = open([], { net: far.net, storage: device({ mine: [THEIRS], dev: "PC", sync: CHECKED }) });
  await ask(phone);
  await ask(pc);
  await ask(phone);
  const want = [THEIRS, MINE].join("\n") + "\n";                                           // id 순(어제 쓴 줄이 앞)
  assert.deepEqual([far.text("2026-10"), linesOf(phone), linesOf(pc)], [want, [THEIRS, MINE].sort(), [THEIRS, MINE].sort()]);
  assert.deepEqual(far.puts().map(call => [bodyOf(call).message, bodyOf(call).sha]), [["log: 2026-10 +1", undefined], ["log: 2026-10 +1", "h1"]]);
  assert.deepEqual(F.plain(C.buildView(F.plain(pc.S.copies())).recs).map(r => r.text), ["볼록성", "기간 프리미엄"]);
});

test("맞춤 뒤의 화면: 다른 기기의 어제 도장을 받으면 권고 줄이 사라진다 — 상태 줄은 맞춘 시각이 된다", async () => {
  const stamp = (at, rand) => line("day", { mark: "full", sec: 120, rec: 0, stuck: "" }, at, rand, "PC");
  const older = stamp("2026-10-11T08:30:00", "d001");
  const net = F.fakeNet([NONE, "hang"]);
  const w = await F.boot({ storage: device({ got: [older], sync: CHECKED }), net });
  const at = id => F.byId(w.doc, id);
  assert.deepEqual([at("td-advice") !== null, F.text(at("st-status"))], [true, C.T.ST_SYNC_WAIT]);          // 받기 전: 어제가 빈칸이다
  const far = F.fakeNet([NONE, file([older, stamp("2026-10-12T08:30:00", "d002")], "s1")]);
  const got = await F.boot({ storage: device({ got: [older], sync: CHECKED }), net: far });
  assert.deepEqual([F.byId(got.doc, "td-advice"), F.text(F.byId(got.doc, "st-status")), sent(got)], [null, "맞춤 08:30", [GET9, GET10]]);
});

test("맞춤: 열쇠가 없던 기기에 열쇠를 넣으면 쌓인 줄이 한 번에 올라간다 — 달마다 한 번, 건수만큼", async () => {
  const sept = next("2026-09-29T09:00:00", "지난달에 쓴 줄", "o001");
  const more = next("2026-10-13T08:10:00", "캐리", "m002");
  const net = F.fakeNet([]);
  const w = await F.boot({ storage: device({ mine: [sept, MINE, more], key: null }), net });
  w.scope.StudyApp.requestSync("manual");
  await F.settle();
  assert.deepEqual([net.calls.length, net.unexpected, F.text(F.byId(w.doc, "st-status"))], [0, 0, C.T.ST_LOCAL]);
  w.scope.StudyStore.setKey(F.KEY);
  for (const route of [REPO_OK, NONE, done("s1", 201), NONE, done("s2", 201)]) net.push(route);
  w.scope.StudyApp.requestSync("manual");
  await F.settle();
  assert.deepEqual([sent(w), net.calls.filter(call => call.method === "PUT").map(call => bodyOf(call).message)], [[REPO, GET9, PUT9, GET10, PUT10], ["log: 2026-09 +1", "log: 2026-10 +2"]]);
  assert.deepEqual([w.scope.StudyStore.queue().length, F.text(F.byId(w.doc, "st-status"))], [0, "맞춤 08:30"]);
});

// ── sync.js: 겹침(409 · 422)과 방금 올린 달의 sha ──
// 가짜 시계를 ms만큼 돌리고 약속이 끝나기를 기다린다
async function tick(w, ms) {
  w.clock.advance(ms);
  await F.settle();
}
const MORE = next("2026-10-13T08:30:20", "캐리", "m002");                               // 이 기기가 조금 뒤에 쓴 줄
const write = (w, text) => w.S.appendLine(C.lineMonth(text), text).ok;                 // 화면의 저장이 하는 일(달 사본과 대기 줄에)

test("맞춤 겹침: 409 · 422면 1.1초 쉬고 다시 받아 합쳐 올린다 — 그 사이 다른 기기가 쓴 줄을 잃지 않는다", async () => {
  const other = next("2026-10-13T07:00:00", "캐리", "t002", "PC");
  for (const status of [409, 422]) {
    const w = open([NONE, file([THEIRS], "s1"), code(status), file([THEIRS, other], "s5"), done("s6")], { storage: device({ mine: [MINE], sync: CHECKED }) });
    await ask(w, "open");
    assert.deepEqual([sent(w), snap(w).phase, w.S.queue().length, w.seen], [[GET9, GET10, PUT10], "run", 1, []]);      // 쉬는 중이다
    await tick(w, 1099);
    assert.equal(w.net.calls.length, 3);
    await tick(w, 1);
    const put = w.net.calls[4];
    assert.deepEqual([sent(w).slice(3), bodyOf(put).sha, bodyOf(put).message, textOf(put)], [[GET10, PUT10], "s5", "log: 2026-10 +1", [THEIRS, other, MINE].join("\n") + "\n"]);
    assert.deepEqual([F.plain(w.S.queue()), linesOf(w), state(w).err, w.seen, w.clock.pending()], [[], [THEIRS, other, MINE].sort(), null, [{ ...QUIET, changed: true, big: false }], 0]);
  }
});

test("맞춤 겹침: 세 번 겹치면 그만두고 대기 줄을 둔다 — 올리기는 세 번뿐이고, 다음 맞춤에 다시 해 본다", async () => {
  const w = open([NONE, NONE, code(422), file([THEIRS], "s1"), code(409), file([THEIRS], "s2"), code(409)], { storage: device({ mine: [MINE], sync: CHECKED }) });
  await ask(w, "open");
  await tick(w, 1100);
  await tick(w, 1100);
  await tick(w, 60000);
  assert.deepEqual(sent(w), [GET9, GET10, PUT10, GET10, PUT10, GET10, PUT10]);
  assert.deepEqual(w.net.calls.filter(call => call.method === "PUT").map(call => bodyOf(call).sha), [undefined, "s1", "s2"]);
  assert.deepEqual([snap(w), state(w).err, state(w).at, F.plain(w.S.queue()), w.net.unexpected, w.clock.pending(), linesOf(w), w.seen],
    [{ ...QUIET, failedThisOpen: true }, { code: 409, key: "ERR_RACE" }, null, [MINE], 0, 0, [THEIRS, MINE].sort(), [{ ...QUIET, failedThisOpen: true, changed: true, big: false }]]);
  for (const route of [NONE, file([THEIRS], "s2"), done("s3")]) w.net.push(route);
  await ask(w);
  assert.deepEqual([sent(w).slice(7), w.S.queue().length, state(w).err], [[GET9, GET10, PUT10], 0, null]);
});

test("맞춤 sha: 방금 올린 달은 60초 동안 받지 않고 그 sha로 올린다 — 받은 글자 그대로의 줄도 함께 실리고, 올릴 것이 없거나 60초가 지나면 다시 받는다", async () => {
  const broken = "깨진 줄 하나";
  const w = open([NONE, file([broken], "s1"), done("s2")], { storage: device({ mine: [MINE], sync: CHECKED }) });
  await ask(w, "open");                                                                    // T0: 올렸다(sha s2)
  w.clock.advance(20000);
  write(w, MORE);
  for (const route of [NONE, done("s3")]) w.net.push(route);
  await ask(w);
  const put = w.net.calls[4];
  assert.deepEqual([sent(w).slice(3), bodyOf(put).sha, bodyOf(put).message, textOf(put)], [[GET9, PUT10], "s2", "log: 2026-10 +1", [MINE, MORE, broken].join("\n") + "\n"]);
  for (const route of [NONE, file([MINE, MORE, broken], "s3")]) w.net.push(route);
  await ask(w);                                                                            // 올릴 것이 없으면 받는다(다른 기기의 줄을 받아야 한다)
  assert.deepEqual([sent(w).slice(5), state(w).bad], [[GET9, GET10], 1]);
  const third = next("2026-10-13T08:31:20", "롤다운", "m003");
  write(w, third);
  for (const route of [NONE, file([MINE, MORE, broken], "s3"), done("s4")]) w.net.push(route);
  await ask(w);                                                                            // 받은 뒤에는 기억을 버렸다 — 다시 받아서 올린다
  assert.deepEqual([sent(w).slice(7), bodyOf(w.net.calls[9]).sha], [[GET9, GET10, PUT10], "s3"]);
  w.clock.advance(60000);                                                                  // 올린 지 60초가 지났다
  write(w, next("2026-10-13T08:32:20", "베어 스티프닝", "m004"));
  for (const route of [NONE, file([MINE, MORE, third, broken], "s4"), done("s5")]) w.net.push(route);
  await ask(w);
  assert.deepEqual([sent(w).slice(10), bodyOf(w.net.calls[12]).sha, w.S.queue().length, w.net.unexpected], [[GET9, GET10, PUT10], "s4", 0, 0]);
});

test("맞춤 sha: 기억한 sha가 낡았으면(그 사이 다른 기기가 올렸다) 겹침으로 돌아가 다시 받아 합친다", async () => {
  const far = hub();
  const phone = open([], { net: far.net, storage: device({ mine: [MINE], sync: CHECKED }) });
  const pc = open([], { net: far.net, storage: device({ mine: [THEIRS], dev: "PC", sync: CHECKED }) });
  await ask(phone);                                                                        // 폰이 만들었다(h1을 기억한다)
  await ask(pc);                                                                           // PC가 그 위에 올렸다(h2)
  write(phone, MORE);
  await ask(phone);                                                                        // 폰은 받지 않고 h1으로 올린다 → 409
  assert.deepEqual([far.puts().map(call => bodyOf(call).sha), snap(phone).phase], [[undefined, "h1", "h1"], "run"]);
  await tick(phone, 1100);
  assert.deepEqual([far.puts().map(call => bodyOf(call).sha).slice(3), far.text("2026-10"), F.plain(phone.S.queue()), linesOf(phone)],
    [["h2"], [THEIRS, MINE, MORE].join("\n") + "\n", [], [THEIRS, MINE, MORE].sort()]);
});

// ── sync.js: 때 ── 한 번에 하나, 자동 맞춤은 10초에 한 번, 돌아오면 멈춰 있던 요청을 끊는다
const CREATED = [NONE, NONE, done("s2", 201)];                                          // 두 달 모두 없는 저장소에 처음 올릴 때의 응답 셋
const feed = (w, routes) => routes.forEach(route => w.net.push(route));

test("맞춤의 때: 자동 맞춤은 10초에 한 번이다 — 창 안의 저장 · 열기 · 돌아옴은 모아서 창이 끝날 때 한 번만 돈다", async () => {
  const w = open([NONE, NONE], { storage: device({ sync: CHECKED }) });
  await ask(w, "open");                                                                    // T0: 자동 시작
  w.clock.advance(2000);
  write(w, MINE);
  await ask(w, "save");
  w.clock.advance(1000);
  write(w, MORE);
  for (const reason of ["save", "open", "back", "save"]) await ask(w, reason);
  assert.deepEqual([sent(w), snap(w).phase, w.clock.pending(), w.seen.length], [[GET9, GET10], "wait", 1, 1]);
  feed(w, CREATED);
  await tick(w, 6999);
  assert.equal(w.net.calls.length, 2);
  await tick(w, 1);                                                                        // T0 + 10초
  assert.deepEqual([sent(w).slice(2), bodyOf(w.net.calls[4]).message, snap(w), w.S.queue().length, w.clock.pending()], [[GET9, GET10, PUT10], "log: 2026-10 +2", QUIET, 0, 0]);
  w.clock.advance(10000);                                                                  // 창이 지난 뒤의 저장은 곧바로 돈다
  write(w, next("2026-10-13T08:31:20", "롤다운", "m003"));
  feed(w, [NONE, done("s3")]);
  await ask(w, "save");
  assert.deepEqual([sent(w).slice(5), snap(w).phase, w.net.unexpected], [[GET9, PUT10], "idle", 0]);
});

test("맞춤의 때: [지금 맞춤]과 저장 실패는 창을 기다리지 않는다 — 기다리던 자동 맞춤은 그것으로 갈음한다", async () => {
  for (const reason of ["manual", "store-fail"]) {
    const w = open([NONE, NONE], { storage: device({ sync: CHECKED }) });
    await ask(w, "open");
    write(w, MINE);
    await ask(w, "save");
    assert.deepEqual([w.net.calls.length, snap(w).phase], [2, "wait"]);
    feed(w, CREATED);
    await ask(w, reason);
    assert.deepEqual([sent(w).slice(2), snap(w).phase, w.S.queue().length, w.clock.pending()], [[GET9, GET10, PUT10], "idle", 0, 0], reason);
    await tick(w, 60000);
    assert.deepEqual([w.net.calls.length, w.net.unexpected], [5, 0]);
  }
});

test("맞춤의 때: 저장 공간이 말을 듣지 않아 기기에 적지 못한 줄도 곧바로 올라간다 — 올라간 뒤에는 대기 줄에서 빠진다", async () => {
  const storage = device({ sync: CHECKED });
  const w = open([NONE, NONE], { storage });
  await ask(w, "open");
  storage.failOn(/\.(m\.|q$)/);
  assert.deepEqual([write(w, MINE), w.S.ok(), w.S.queue().length], [false, false, 1]);
  feed(w, CREATED);
  await ask(w, "store-fail");
  assert.deepEqual([sent(w).slice(2), textOf(w.net.calls[4]), w.S.queue().length, linesOf(w), storage.data.has(LS + "q")], [[GET9, GET10, PUT10], MINE + "\n", 0, [MINE], false]);
});

test("맞춤의 때: 한 번에 하나만 돈다 — 올리기가 끝나지 않은 동안 저장하고 눌러도 겹쳐 보내지 않고, 15초 뒤 끊긴 다음에 한 번 더 돈다", async () => {
  const w = open([NONE, NONE, "hang"], { storage: device({ mine: [MINE], sync: CHECKED }) });
  await ask(w, "open");
  write(w, MORE);
  for (const reason of ["save", "manual", "store-fail", "save", "open"]) await ask(w, reason);
  await tick(w, 14999);
  assert.deepEqual([sent(w), snap(w).phase, w.seen], [[GET9, GET10, PUT10], "run", []]);
  feed(w, CREATED);
  await tick(w, 1);                                                                        // 15초: 끊는다 → 시간 초과 → 미뤄 둔 요청을 한 번 돈다
  assert.deepEqual([sent(w).slice(3), bodyOf(w.net.calls[5]).message, w.S.queue().length, w.clock.pending(), w.net.unexpected], [[GET9, GET10, PUT10], "log: 2026-10 +2", 0, 0, 0]);
  assert.deepEqual(w.seen.map(s => [s.phase, s.failedThisOpen]), [["idle", true], ["idle", true]]);
  assert.deepEqual([state(w).err, state(w).at], [null, F.T0 + 15000]);                     // 처음 것은 시간 초과로 적혔다가, 다음 맞춤이 지웠다
});

test("맞춤의 때: 돌아오면 멈춰 있던 요청을 끊고 새로 시작한다 — 끊긴 올리기가 실은 닿았어도 다시 올리지 않고 대기 줄이 빈다", async () => {
  const w = open([NONE, NONE, "hang"], { storage: device({ mine: [MINE], sync: CHECKED }) });
  await ask(w, "open");                                                                    // 올리기가 멈춰 있다(화면이 가려져 통신이 얼었다)
  w.clock.advance(11000);
  feed(w, [NONE, file([MINE], "s9")]);                                                     // 끊긴 올리기는 실은 닿아 있었다
  await ask(w, "back");
  assert.deepEqual([sent(w), F.plain(w.S.queue()), snap(w), w.clock.pending()], [[GET9, GET10, PUT10, GET9, GET10], [], QUIET, 0]);
  assert.deepEqual(w.seen, [{ ...QUIET, changed: false, big: false }]);                    // 끊긴 판은 알리지도 적지도 않는다
  assert.deepEqual([state(w).err, state(w).at], [null, F.T0 + 11000]);
});

test("맞춤의 때: 끊긴 올리기가 닿지 않았으면 한 번만 다시 올린다 — 창 안에 돌아왔으면 창이 끝날 때 돈다", async () => {
  const w = open([NONE, NONE, "hang"], { storage: device({ mine: [MINE], sync: CHECKED }) });
  await ask(w, "open");
  w.clock.advance(3000);
  await ask(w, "back");                                                                    // 창 안이다: 끊기만 하고 기다린다
  assert.deepEqual([w.net.calls.length, snap(w).phase, w.clock.pending(), w.seen], [3, "wait", 1, []]);
  feed(w, CREATED);
  await tick(w, 7000);
  assert.deepEqual([sent(w).slice(3), w.S.queue().length, snap(w), w.clock.pending(), w.net.unexpected], [[GET9, GET10, PUT10], 0, QUIET, 0, 0]);
  const resting = open([NONE, NONE, code(409)], { storage: device({ mine: [MINE], sync: CHECKED }) });
  await ask(resting, "open");                                                              // 겹쳐서 쉬는 중에 돌아와도 같다 — 옛 판은 깨어나도 보내지 않는다
  resting.clock.advance(500);
  await ask(resting, "back");
  feed(resting, [NONE, file([THEIRS], "s1"), done("s2")]);
  await tick(resting, 20000);
  assert.deepEqual([sent(resting).slice(3), resting.S.queue().length, resting.net.unexpected, resting.clock.pending()], [[GET9, GET10, PUT10], 0, 0, 0]);
});

test("상태 줄: 올릴 줄이 어제 이전 것이고 이번에 연 뒤의 맞춤이 실패했을 때만 호박색이다 — 돌아오면 다시 판정한다", async () => {
  const old = next("2026-10-12T08:00:00", "어제 쓴 줄", "o001");
  const look = w => [F.text(F.byId(w.doc, "st-status")), F.byId(w.doc, "st-status").getAttribute("class")];
  const w = await F.boot({ storage: device({ mine: [old], sync: CHECKED }), net: F.fakeNet([NONE, new Error("끊김")]) });
  assert.deepEqual([look(w), sent(w)], [["올릴 것 1건", "st-status st-amber"], [GET9, GET10]]);
  w.clock.advance(11000);
  feed(w, ["hang"]);
  w.fire("visibilitychange", "visible");                                                   // 돌아왔다: 다시 판정한다(맞춤이 끝나기 전에는 호박색이 아니다)
  await F.settle();
  assert.deepEqual(look(w), ["올릴 것 1건", "st-status"]);
  feed(w, [NONE, NONE, done("s2", 201)]);
  w.clock.advance(11000);
  w.fire("visibilitychange", "visible");
  await F.settle();
  assert.deepEqual([look(w), w.net.unexpected], [["맞춤 08:30", "st-status"], 0]);
  const fresh = await F.boot({ storage: device({ mine: [MINE], sync: CHECKED }), net: F.fakeNet([NONE, new Error("끊김")]) });
  assert.deepEqual(look(fresh), ["올릴 것 1건", "st-status"]);                               // 오늘 쓴 줄만 밀려 있으면 실패해도 호박색이 아니다
  const locked = await F.boot({ storage: device({ mine: [old], sync: CHECKED }), net: F.fakeNet(["hang"]) });
  assert.deepEqual(look(locked), ["올릴 것 1건", "st-status"]);                              // 아직 실패하지 않았다(잠그며 끊긴 줄은 다음에 열 때 올라간다)
});

// ── sync.js: [사본 비우고 다시 받기](pullOnly) · 설정이 바뀌었을 때(reset) ──
const PAUSED = { ...QUIET, stop: "paused" };

test("사본 비우고 다시 받기: 멈춤일 때만 — 요청은 받기뿐이고, 원격에 없는 옛 줄은 되살아나지 않으며 대기 줄은 남는다", async () => {
  const erased = next("2026-10-10T09:00:00", "원격에서 지운 줄", "g001", "PC");              // 이 기기 사본에는 아직 남아 있다
  const summer = next("2026-07-01T09:00:00", "석 달 전 줄", "j001", "PC");                  // 받는 범위(이번 달 · 지난달) 밖의 옛 달 사본
  const w = open([NONE, file([THEIRS], "s1")], { storage: device({ mine: [MINE], got: [erased, THEIRS, summer], pause: "1", sync: CHECKED }) });
  assert.deepEqual(F.plain(await w.Y.pullOnly()), { ok: true, key: null, code: null });
  assert.deepEqual([sent(w), w.net.calls.every(call => call.method === "GET" && call.body === null)], [[GET9, GET10], true]);
  assert.deepEqual([linesOf(w), F.plain(w.S.months()), F.plain(w.S.queue()), w.seen], [[THEIRS, MINE].sort(), ["2026-10"], [MINE], [{ ...PAUSED, changed: true, big: false }]]);
  w.S.setFlag("pause", false);                                                             // 자동 맞춤을 다시 켜면 대기 줄만 올라간다 — 지운 줄은 올라가지 않는다
  feed(w, [NONE, file([THEIRS], "s1"), done("s2")]);
  await ask(w);
  assert.deepEqual([sent(w).slice(2), textOf(w.net.calls[4]), w.S.queue().length, w.net.unexpected], [[GET9, GET10, PUT10], [THEIRS, MINE].join("\n") + "\n", 0, 0]);
});

test("사본 비우고 다시 받기: 멈추지 않았거나 설정이 비었거나 열쇠가 거절된 뒤면 요청 0번이다 — 사본도 그대로다", async () => {
  const run = async more => {
    const w = open([], { storage: device({ mine: [MINE], got: [THEIRS], ...more }) });
    return [F.plain(await w.Y.pullOnly()), w.net.calls.length, w.net.unexpected, linesOf(w).length, w.seen.length];
  };
  assert.deepEqual(await run({}), [{ ok: false, key: "SET_REPULL_NOTE", code: null }, 0, 0, 2, 0]);
  assert.deepEqual(await run({ pause: "0", sync: CHECKED }), [{ ok: false, key: "SET_REPULL_NOTE", code: null }, 0, 0, 2, 0]);
  assert.deepEqual(await run({ pause: "1", key: null }), [{ ok: false, key: "CONN_UNSET", code: null }, 0, 0, 2, 0]);
  assert.deepEqual(await run({ pause: "1", repo: "a/b" }), [{ ok: false, key: "CONN_UNSET", code: null }, 0, 0, 2, 0]);
  assert.deepEqual(await run({ pause: "1", auth: "401" }), [{ ok: false, key: "CONN_AUTH", code: null }, 0, 0, 2, 0]);
});

test("사본 비우고 다시 받기: 받다가 실패하면 까닭을 돌려준다 — 올리지 못한 줄은 사본에 되돌려져 화면에 남는다", async () => {
  const run = async route => {
    const w = open([NONE, route], { storage: device({ mine: [MINE], got: [THEIRS], pause: "1" }) });
    return [F.plain(await w.Y.pullOnly()), sent(w), linesOf(w), F.plain(w.S.queue()), state(w).err, snap(w).stop];
  };
  const left = [[GET9, GET10], [MINE], [MINE]];
  assert.deepEqual(await run(new Error("끊김")), [{ ok: false, key: "CONN_NET", code: 0 }, ...left, { code: 0, key: "ERR_NET" }, "paused"]);
  assert.deepEqual(await run(code(500)), [{ ok: false, key: "CONN_ERR", code: 500 }, ...left, { code: 500, key: "ERR_SERVER" }, "paused"]);
  assert.deepEqual(await run(code(403)), [{ ok: false, key: "CONN_ERR", code: 403 }, ...left, { code: 403, key: "ERR_HALT" }, "paused"]);
  assert.deepEqual(await run(code(401)), [{ ok: false, key: "CONN_AUTH", code: 401 }, ...left, { code: 401, key: "ERR_AUTH" }, "auth"]);
  assert.deepEqual(await run({ status: 200, body: F.ghFile("x".repeat(700000), "s1") }), [{ ok: false, key: "ST_FILE", code: 200 }, ...left, { code: 0, key: "ERR_FILE" }, "paused"]);
  const q = i => line("q", { text: "가".repeat(200), sec: 0, rec: 0, s_head: false, s_two: false, s_wrong: false }, "2026-10-01T10:00:00", "b" + String(i).padStart(3, "0"), "PC");
  const big = await run(file(Array.from({ length: 420 }, (unused, i) => q(i)), "s1"));       // 사본이 300KB를 넘게 되는 달은 받지 않는다
  assert.deepEqual([big[0], big[2]], [{ ok: false, key: "NOTE_BIG", code: null }, [MINE]]);
  const bare = open([], { storage: device({ mine: [MINE], pause: "1" }), extra: { AbortController: null } });      // 속에서 던져도 약속은 거절하지 않는다
  assert.deepEqual([F.plain(await bare.Y.pullOnly()), bare.net.calls.length, linesOf(bare)], [{ ok: false, key: "CONN_NET", code: null }, 0, [MINE]]);
});

test("설정이 바뀌면(reset): 메모리의 멈춤 · 그날의 저장소 확인 · 기억한 sha를 지운다 — 다음 맞춤은 저장소 확인부터 다시 한다", async () => {
  const w = open([NONE, NONE, code(403)], { storage: device({ mine: [MINE], sync: CHECKED }) });
  await ask(w, "open");
  assert.deepEqual([snap(w).stop, state(w).repo.state, w.seen.length], ["halt", "ok", 1]);
  w.Y.reset();
  assert.deepEqual([snap(w), state(w).repo, w.seen.length, w.net.calls.length], [{ ...QUIET, failedThisOpen: true }, null, 2, 3]);
  feed(w, [REPO_OK, NONE, NONE, done("s2", 201)]);
  await ask(w);
  assert.deepEqual([sent(w).slice(3), w.S.queue().length], [[REPO, GET9, GET10, PUT10], 0]);
  write(w, MORE);                                                                          // 방금 올렸지만(60초 안) reset 뒤에는 기억한 sha를 쓰지 않는다
  w.Y.reset();
  feed(w, [REPO_OK, NONE, file([MINE], "s2"), done("s3")]);
  await ask(w);
  assert.deepEqual([sent(w).slice(7), bodyOf(w.net.calls[10]).sha, w.net.unexpected], [[REPO, GET9, GET10, PUT10], "s2", 0]);
});

test("설정이 바뀌면(reset): 돌던 요청을 끊고 기다리던 것도 치운다 — 끊긴 판은 적지 않고, 창도 처음부터다", async () => {
  const w = open([NONE, NONE, "hang"], { storage: device({ mine: [MINE], sync: CHECKED }) });
  await ask(w, "open");
  for (const reason of ["save", "manual"]) await ask(w, reason);                           // 끝난 뒤 한 번 더 돌 것이 걸려 있다
  w.Y.reset();
  await F.settle();
  assert.deepEqual([w.net.calls.length, snap(w), state(w).err, state(w).at, w.S.queue().length, w.clock.pending()], [3, QUIET, null, null, 1, 0]);
  feed(w, [REPO_OK, NONE, NONE, done("s2", 201)]);
  await ask(w, "save");                                                                    // 창도 처음부터다 — 같은 순간의 저장이 곧바로 돈다
  await tick(w, 60000);
  assert.deepEqual([sent(w).slice(3), w.S.queue().length, w.net.unexpected], [[REPO, GET9, GET10, PUT10], 0, 0]);
  const waiting = open([NONE, NONE], { storage: device({ sync: CHECKED }) });
  await ask(waiting, "open");
  write(waiting, MINE);
  await ask(waiting, "save");
  assert.equal(snap(waiting).phase, "wait");
  waiting.Y.reset();
  await tick(waiting, 60000);
  assert.deepEqual([waiting.net.calls.length, snap(waiting).phase, waiting.clock.pending(), waiting.S.queue().length], [2, "idle", 0, 1]);
});

test("연결 확인과 reset: 확인하는 동안 설정이 바뀌면 그 답은 버린다 — 지난 확인은 그 실행의 멈춤(4xx)을 푼다", async () => {
  const w = open(["hang"], { storage: device({ mine: [MINE] }) });
  let result = null;
  w.Y.checkConn().then(r => { result = F.plain(r); });
  await F.settle();
  w.Y.reset();
  await F.settle();
  assert.deepEqual([result, state(w).repo, state(w).err, w.clock.pending()], [{ key: "CONN_NET", code: null }, null, null, 0]);
  const halted = open([NONE, NONE, code(403), REPO_OK], { storage: device({ mine: [MINE], sync: CHECKED }) });
  await ask(halted, "open");
  assert.deepEqual([snap(halted).stop, (await halted.Y.checkConn()).key, snap(halted)], ["halt", "CONN_OK", { ...QUIET, failedThisOpen: true }]);
});

test("맞춤: 약속된 이름이 모두 있고 그 밖의 것은 없다 — 열쇠가 없는 기기의 처음 모습", () => {
  assert.deepEqual(Object.keys(Y).sort(), ["_", "checkConn", "init", "pullOnly", "request", "reset", "snapshot"]);
  assert.deepEqual(F.plain(Y.snapshot()), { phase: "idle", stop: "off", code: null, failedThisOpen: false });
  assert.deepEqual([Y.init(), Y.request("open"), Y.reset()], [undefined, undefined, undefined]);
});
