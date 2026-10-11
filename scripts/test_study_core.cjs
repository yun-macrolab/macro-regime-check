"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const F = require("./study_fakes.cjs");

// 공부 화면의 규칙 테스트. 화면 파일은 가짜 묶음(study_fakes.cjs)으로만 싣는다. 지어낸 글만 쓴다.
// 돌리기: node --test scripts/test_study_core.cjs

// ── core.js: 상수 · 문구 표 · 날짜 ──
const C = F.world(["core.js"]).scope.StudyCore;
const at = isoText => Date.parse(isoText);

test("core: 상수와 문구 표", () => {
  assert.deepEqual([C.V, C.TALK_SEC, C.DAY_START_HOUR, F.plain(C.ROUTES)], [1, 120, 4, ["today", "week", "ask", "set"]]);
  const keys = Object.keys(C.T);
  assert.deepEqual([keys.length, Object.isFrozen(C.T), keys.filter(k => typeof C.T[k] !== "string" || C.T[k] === "")], [177, true, []]);
  const holes = new Set(keys.flatMap(k => [...C.T[k].matchAll(/\{(\w+)\}/g)].map(m => m[1])));
  assert.deepEqual([...holes].sort(), ["code", "cur", "date", "dur", "mark", "n", "size", "t", "text", "v", "wk"]);
  assert.deepEqual([C.T.APP_NAME, C.T.NA, C.T.MARK_FULL, C.T.MARK_MIN, C.T.MARK_REST, C.T.MARK_NONE], ["2분 노트", "—", "○", "△", "쉼", "·"]);
  assert.equal(C.T.FALLBACK, "화면을 다 받지 못했다 — 책을 덮고 2분 말한 뒤 나중에 도장");
  assert.deepEqual(["NAV_TODAY", "NAV_WEEK", "NAV_ASK", "NAV_SET"].map(k => C.T[k]), ["오늘", "주간", "질문", "설정"]);
});

test("core: t()는 {이름}만 바꾸고, 없는 키는 키를 그대로 돌려준다", () => {
  assert.equal(C.t("ST_QUEUE", { n: 3 }), "올릴 것 3건");
  assert.equal(C.t("ST_HALT", { code: 403 }), "맞춤 멈춤 — 오류 403");
  assert.equal(C.t("WK_CONFIRM", { dur: C.T.DUR_S_OW, cur: C.T.CUR_STEEP }), "확대 · 스티프닝으로 저장 — 고칠 수 없다");
  assert.equal(C.t("TD_TOPIC", { text: "$& {text} <b>" }), "오늘 말할 개념: $& {text} <b>");   // 넣은 글은 다시 바꾸지 않는다
  assert.equal(C.t("ST_QUEUE"), "올릴 것 {n}건");
  assert.deepEqual([C.t("NO_SUCH_KEY", { n: 1 }), C.t("constructor")], ["NO_SUCH_KEY", "constructor"]);
});

test("core 날짜: 공부 날짜는 KST 04:00에 바뀐다 — 03:59:59와 04:00:00, 달 · 해 · 주의 첫 새벽", () => {
  assert.equal(C.studyDate(at("2026-10-12T18:59:59.999Z")), "2026-10-12");              // KST 10-13 03:59:59.999
  assert.equal(C.studyDate(at("2026-10-12T19:00:00.000Z")), "2026-10-13");              // KST 10-13 04:00:00.000
  assert.equal(C.studyDate(F.T0), "2026-10-13");
  assert.equal(C.studyDate(at("2026-09-30T18:30:00Z")), "2026-09-30");                  // KST 10-01 03:30 → 아직 9월
  assert.equal(C.monthOf(C.studyDate(at("2026-09-30T18:30:00Z"))), "2026-09");
  assert.equal(C.studyDate(at("2026-12-31T18:59:59Z")), "2026-12-31");                  // KST 2027-01-01 03:59 → 아직 지난해
  assert.equal(C.studyDate(at("2026-12-31T19:00:00Z")), "2027-01-01");
  assert.equal(C.weekOf(C.studyDate(at("2026-10-18T18:59:59Z"))), "2026-10-12");        // KST 월 10-19 03:59 → 지난주 일요일
  assert.equal(C.weekOf(C.studyDate(at("2026-10-18T19:00:00Z"))), "2026-10-19");
  assert.deepEqual([C.studyDate(NaN), C.stampT(NaN), C.idTime(NaN)], ["", "", ""]);
});

test("core 날짜: 줄에 찍는 시각과 id 시각은 같은 순간이고, id 시각은 실제 시각만 되돌려진다", () => {
  const ms = at("2026-10-12T23:41:07.123Z");
  assert.deepEqual([C.stampT(ms), C.idTime(ms), C.idMs("20261012234107123-폰-k3f9")], ["2026-10-13T08:41:07+09:00", "20261012234107123", ms]);
  assert.equal(C.idMs("20280229120000000-PC-aaaa"), at("2028-02-29T12:00:00Z"));
  const bad = ["20261312234107123-폰-k3f9", "20261032234107123-폰-k3f9", "20260229000000000-폰-k3f9", "20261012240000000-폰-k3f9",
    "20261012235960000-폰-k3f9", "19991231235959999-폰-k3f9", "21000101000000000-폰-k3f9", "2026101223410712-폰-k3f9", "", null, 20261012234107123];
  assert.deepEqual(bad.filter(id => !Number.isNaN(C.idMs(id))), []);
  assert.deepEqual([C.hhmm(F.T0), C.hhmm(at("2026-10-12T15:00:00Z")), C.mmss(120), C.mmss(7), C.mmss(0)], ["08:30", "00:00", "2:00", "0:07", "0:00"]);
});

test("core 날짜: 달력 — 실제 날짜만 받고, 주는 월요일에 시작한다", () => {
  const ok = ["2026-10-13", "2028-02-29", "0001-01-01", "9999-12-31"];
  const no = ["2026-02-30", "2026-02-29", "2100-02-29", "2026-13-01", "2026-00-10", "2026-10-00", "0000-01-01", "2026-1-01",
    "2026-10-13 ", "2026-10-13\n", "２０２６-10-13", 20261013, null];
  assert.deepEqual([ok.filter(s => !C.isDate(s)), no.filter(s => C.isDate(s))], [[], []]);
  assert.deepEqual([C.addDays("2026-10-13", 1), C.addDays("2026-10-31", 1), C.addDays("2026-01-01", -1), C.addDays("2028-02-28", 2), C.addDays("2026-10-13", -13)],
    ["2026-10-14", "2026-11-01", "2025-12-31", "2028-03-01", "2026-09-30"]);
  assert.deepEqual(["2026-10-04", "2026-10-05", "2026-10-11", "2026-10-13", "2027-01-01"].map(d => C.weekOf(d)),
    ["2026-09-28", "2026-10-05", "2026-10-05", "2026-10-12", "2026-12-28"]);
  assert.deepEqual([C.monthOf("2026-10-13"), C.prevMonth("2026-10"), C.prevMonth("2026-01")], ["2026-10", "2026-09", "2025-12"]);
  assert.deepEqual(["2026-10-12", "2026-10-13", "2026-10-18"].map(d => C.headDate(d)), ["10-12 월", "10-13 화", "10-18 일"]);
});

// ── core.js: 기록 줄의 꼴 — 표와 본보기 ──
const CASES = require("./study_cases.json");
const verdict = (text, month) => { const r = C.checkLine(text, month); return r.ok ? "ok" : r.code; };
const caseOf = name => CASES.cases.find(c => c.name === name);

test("core 꼴: 표(SCHEMA · HEAD · REJECT)가 본보기 파일과 깊이 같다", () => {
  assert.deepEqual(F.plain(C.SCHEMA), CASES.schema);
  assert.deepEqual([F.plain(C.HEAD), F.plain(C.REJECT), F.plain(C.KINDS)], [CASES.head, CASES.reject, Object.keys(CASES.schema)]);
  assert.deepEqual([C.MAX_LINE_BYTES, CASES.v, Object.isFrozen(C.SCHEMA.day[0][2])], [2000, 1, true]);
  assert.deepEqual([C.ID_RE.source, C.DEV_RE.source], ["^\\d{17}-[가-힣A-Za-z0-9]{1,8}-[a-z0-9]{4}$", "^[가-힣A-Za-z0-9]{1,8}$"]);
});

test("core 꼴: 본보기 전부 — checkLine의 판정이 expect와 같다", () => {
  const wrong = CASES.cases.filter(c => verdict(c.text, c.month) !== c.expect).map(c => c.name + ": " + verdict(c.text, c.month) + " ≠ " + c.expect);
  assert.deepEqual(wrong, []);
  const names = CASES.cases.map(c => c.name);
  assert.deepEqual([names.length, new Set(names).size], [177, 177]);
  const seen = new Set(CASES.cases.map(c => c.expect));
  assert.deepEqual(CASES.reject.filter(code => !seen.has(code)), []);            // 거절 코드 15개마다 본보기가 있다
  const kinds = new Set(CASES.cases.filter(c => c.expect === "ok").map(c => JSON.parse(c.text).k));
  assert.deepEqual(Object.keys(CASES.schema).filter(k => !kinds.has(k)), []);      // 종류 일곱마다 통과 본보기가 있다
});

test("core 꼴: 날짜 경계의 본보기가 빠지지 않는다 — 새벽 줄 · 달과 해의 첫 새벽 · 월요일 새벽 · 하루 당긴 줄", () => {
  const d = name => JSON.parse(caseOf(name).text).d;
  assert.deepEqual(["boundary-0359", "boundary-0400", "month-edge-dawn", "year-edge-dawn", "year-edge-0400", "monday-dawn-week"].map(d),
    ["2026-10-12", "2026-10-13", "2026-09-30", "2026-12-31", "2027-01-01", "2026-10-18"]);
  assert.deepEqual(["boundary-0359", "month-edge-dawn", "monday-dawn-week"].map(n => caseOf(n).expect), ["ok", "ok", "ok"]);
  assert.deepEqual(["date-pulled-back", "date-pushed", "date-dawn-calendar-day", "month-edge-wrong-file", "rule-monday-dawn-week", "time-z-form"].map(n => caseOf(n).expect),
    ["date", "date", "date", "month", "rule", "time"]);
  assert.deepEqual([caseOf("month-edge-dawn").month, caseOf("month-edge-wrong-file").month], ["2026-09", "2026-10"]);
});

test("core 꼴: 통과한 줄은 얼린 객체로 돌려주고, 글자가 아닌 것은 던지지 않고 json이다", () => {
  const r = C.checkLine(caseOf("day-full").text, "2026-10");
  assert.deepEqual([r.ok, r.obj.mark, Object.isFrozen(r.obj), Object.keys(r.obj).join()], [true, "full", true, "v,id,k,d,t,dev,mark,sec,rec,stuck"]);
  assert.deepEqual(F.plain(C.checkLine("{", null)), { ok: false, code: "json" });
  assert.deepEqual([undefined, null, 1, {}, []].map(x => verdict(x, null)), ["json", "json", "json", "json", "json"]);
  assert.equal(verdict(caseOf("day-full").text, undefined), "ok");
});

// ── core.js: 줄 만들기와 입력 검사 ──
const AT = { nowMs: F.T0, dev: "폰", rand: "k3f9" };
const FIELDS = {
  day: { mark: "full", sec: 120, rec: 0, stuck: "볼록성을 말로 잇지 못함" },
  next: { text: "기간 프리미엄" },
  rest: { on: "2026-10-14" },
  week: { wk: "2026-10-12", dur: "ow", cur: "steep", why: "고용 둔화", wrong_if: "근원 물가가 높게 나오면" },
  grade: { wk: "2026-10-05", ref: "20261004235210007-PC-x71c", actual: "금리가 내렸다", dur_hit: "y", cur_hit: "na", miss: "" },
  q: { text: "기간 프리미엄이란", sec: 97, rec: 0, s_head: true, s_two: false, s_wrong: true },
  fix: { ref: "20261012234107123-폰-k3f9", hide: true },
};

test("core 만들기: 종류 일곱 모두 makeLine이 만든 줄은 checkLine을 통과하고, 키 차례는 HEAD + SCHEMA다", () => {
  for (const kind of Object.keys(CASES.schema)) {
    const made = C.makeLine(kind, FIELDS[kind], AT);
    assert.deepEqual([made.ok, verdict(made.text, "2026-10")], [true, "ok"], kind);
    assert.deepEqual(Object.keys(JSON.parse(made.text)), [...CASES.head, ...CASES.schema[kind].map(spec => spec[0])], kind);
    assert.deepEqual(F.plain(made.obj), JSON.parse(made.text), kind);
  }
  assert.equal(C.makeLine("day", FIELDS.day, AT).text,
    '{"v":1,"id":"20261012233000000-폰-k3f9","k":"day","d":"2026-10-13","t":"2026-10-13T08:30:00+09:00","dev":"폰","mark":"full","sec":120,"rec":0,"stuck":"볼록성을 말로 잇지 못함"}');
  assert.equal(C.makeId(F.T0, "폰", "k3f9"), "20261012233000000-폰-k3f9");
});

test("core 만들기: 글 칸은 앞뒤 공백을 떼고, 새벽에 만든 줄의 날짜는 전날이다", () => {
  assert.equal(C.makeLine("next", { text: "  기간 프리미엄 \n" }, AT).obj.text, "기간 프리미엄");
  const dawn = C.makeLine("day", FIELDS.day, { ...AT, nowMs: at("2026-09-30T18:30:00Z") });                    // KST 10-01 03:30
  assert.deepEqual([dawn.obj.d, dawn.obj.t, dawn.obj.id], ["2026-09-30", "2026-10-01T03:30:00+09:00", "20260930183000000-폰-k3f9"]);
  const monday = { ...AT, nowMs: at("2026-10-18T18:30:00Z") };                                                 // KST 월 10-19 03:30
  assert.deepEqual([C.makeLine("week", FIELDS.week, monday).obj.d, C.makeLine("week", { ...FIELDS.week, wk: "2026-10-19" }, monday).code], ["2026-10-18", "rule"]);
});

test("core 만들기: 꼴이 맞지 않으면 줄을 만들지 않고 코드를 돌려준다(던지지 않는다)", () => {
  const code = (kind, fields, when) => { const r = C.makeLine(kind, fields, when === undefined ? AT : when); return r.ok ? "ok" : r.code; };
  const D = FIELDS.day;
  assert.deepEqual([code("note", {}), code("constructor", {}), code("day", { mark: "full", sec: 120, rec: 0 }), code("day", null), code("day", D, null)],
    ["kind", "kind", "keys", "keys", "keys"]);
  assert.deepEqual([code("day", { ...D, stuck: "가".repeat(121) }), code("day", { ...D, stuck: "a".repeat(40) }), code("day", { ...D, stuck: "앞\t뒤" }), code("day", { ...D, sec: 121 }),
    code("day", { ...D, sec: NaN }), code("next", { text: "   " }), code("rest", { on: "2026-10-13" }), code("fix", { ref: "__proto__", hide: true }), code("q", { ...FIELDS.q, sec: 10n })],
    ["long", "secret", "ctrl", "field", "field", "field", "rule", "field", "json"]);
  assert.deepEqual([code("day", D, { ...AT, dev: "아주긴기기이름아홉" }), code("day", D, { ...AT, rand: "K3F9" }), code("day", D, { ...AT, nowMs: NaN })], ["id", "id", "id"]);
});

test("core 입력 검사: textIssue는 뗀 글로 보고 empty · long · ctrl · secret · null을 돌려준다", () => {
  const issue = (kind, name, value) => C.textIssue(kind, name, value);
  assert.deepEqual([issue("day", "stuck", ""), issue("day", "stuck", "  "), issue("day", "stuck", " 막힘 "), issue("next", "text", ""), issue("next", "text", "  "), issue("q", "text", undefined)],
    [null, null, null, "empty", "empty", "empty"]);
  assert.deepEqual([issue("next", "text", "가".repeat(60)), issue("next", "text", "가".repeat(61)), issue("next", "text", " " + "가".repeat(60) + " "),
    issue("day", "stuck", "😀".repeat(120)), issue("day", "stuck", "😀".repeat(121))], [null, "long", null, null, "long"]);
  assert.deepEqual([issue("week", "why", "앞\t뒤"), issue("week", "wrong_if", "x".repeat(40)), issue("week", "why", "x".repeat(39)), issue("grade", "miss", ""), issue("grade", "actual", "")],
    ["ctrl", "secret", null, null, "empty"]);
  assert.deepEqual([issue("day", "sec", "1"), issue("day", "없는칸", "글"), issue("note", "text", "글"), issue("constructor", "text", "글")], ["empty", "empty", "empty", "empty"]);
});

// ── core.js: 이름 검증과 열쇠 만들기 링크 ──
test("core 이름: 기기 · 주인 · 저장소 이름과 열쇠 꼴", () => {
  const miss = (fn, good, bad) => [good.filter(s => !fn(s)), bad.filter(s => fn(s))];
  assert.deepEqual(miss(s => C.devOk(s), ["폰", "PC", "a1", "가나다라마바사아"], ["", "아홉글자기기이름임", "a-b", "a b", "ㅍ", "폰\n", null, 1]), [[], []]);
  assert.deepEqual(miss(s => C.ownerOk(s), ["owner", "a", "a-b", "A1", "a".repeat(39)], ["", "-a", "a-", "a_b", "a.b", "a/b", "a".repeat(40), "owner\n", "가", null]), [[], []]);
  assert.deepEqual(miss(s => C.repoOk(s), ["repo", "a.b_c-d", "...", "a".repeat(100)], ["", ".", "..", "a/b", "a b", "a?b", "a#b", "a%2f", "a".repeat(101), "repo\n", "가", null]), [[], []]);
  const key = "k".repeat(64);                                                    // 가짜 열쇠 — 글자를 소스에 적지 않는다
  assert.deepEqual(miss(s => C.keyShape(s), [key, "k".repeat(60), "k_9".repeat(85)], ["k".repeat(59), "k".repeat(256), " " + key, key + "\n", key + "-", "가".repeat(64), "", null]), [[], []]);
});

test("core 링크: 열쇠 만들기 링크는 정해진 주소로만 가고, 이름 칸에는 기기 이름과 KST 달만 든다", () => {
  const base = "https://github.com/settings/personal-access-tokens/new";
  assert.equal(C.KEY_LINK_BASE, base);
  assert.equal(C.keyLink("PC", F.T0), base + "?name=note-PC-202610&expires_in=90&contents=write");
  assert.equal(C.keyLink("폰", at("2026-10-31T15:00:00Z")), base + "?name=note-%ED%8F%B0-202611&expires_in=90&contents=write");   // KST 11-01 00:00
  assert.deepEqual([C.safeLink(C.keyLink("폰", F.T0)), C.keyLink("a&b=c", F.T0).includes("b=c"), C.keyLink(null, NaN)], [true, false, base + "?name=note--&expires_in=90&contents=write"]);
  const no = [base, base + "/x?", base.slice(0, 19), base.replace("https:", "http:") + "?", " " + base + "?", "#today", "", null];
  assert.deepEqual(no.filter(url => C.safeLink(url)), []);
});

// ── core.js: 합치기 ──
const mk = (kind, fields, isoText, dev, rand) => F.line(kind, fields, { ms: at(isoText), dev, rand });
const BROKEN = '{"v":1,"id":';                                                                                  // 깨진 줄
const V2 = '{"v":2,"id":"20261012234500000-PC-v2v2","k":"tag","d":"2026-10-13","text":"모르는 판의 줄"}';   // 모르는 판 · 모르는 종류
const three = () => ["aaaa", "bbbb", "cccc"].map((rand, i) => mk("next", { text: "개념 " + i }, "2026-10-12T23:3" + i + ":00Z", "폰", rand));

test("core 합치기: 줄 쪼개기와 잇기 — 끝의 CR 하나만 떼고 빈 줄은 버린다", () => {
  assert.deepEqual(F.plain(C.splitLines("a\r\nb\n\n\r\nc")), ["a", "b", "c"]);
  assert.deepEqual(F.plain(C.splitLines("a\r\r\n b \n")), ["a\r", " b "]);
  assert.deepEqual([F.plain(C.splitLines("")), C.joinLines([]), C.joinLines(["a", "b"])], [[], "", "a\nb\n"]);
  assert.deepEqual(F.plain(C.splitLines(C.joinLines(["a", "b"]))), ["a", "b"]);
});

test("core 합치기: 차례 — 꼴이 맞는 줄은 id 순, 나머지는 글자 순으로 뒤에, 같은 글자는 하나로", () => {
  const a = mk("next", { text: "가" }, "2026-10-12T23:30:00Z", "폰", "aaaa");
  const b = mk("next", { text: "나" }, "2026-10-12T23:31:00Z", "PC", "bbbb");
  const c = mk("next", { text: "다" }, "2026-10-12T23:31:00Z", "폰", "cccc");                                   // b와 같은 시각 — id의 기기 이름 순
  const sept = mk("next", { text: "9월" }, "2026-09-29T23:00:00Z", "폰", "dddd");                              // 10월 파일에서는 꼴 불일치(month)
  const late = JSON.parse(mk("next", { text: "라" }, "2026-10-12T23:32:00Z", "폰", "eeee"));
  const odd = JSON.stringify({ text: late.text, ...late });                                                     // 키 차례가 다른 줄 — 글자가 아니라 id로 놓인다
  assert.deepEqual(F.plain(C.orderLines(Object.freeze([V2, odd, c, BROKEN, b, a, sept, b]), "2026-10")), [a, b, c, odd, BROKEN, sept, V2]);
  assert.deepEqual(F.plain(C.orderLines([a, sept], null)), [sept, a]);
  assert.deepEqual(F.plain(C.orderLines([], "2026-10")), []);
});

test("core 합치기: 순서와 무관하고 두 번 해도 같다 — 깨진 줄과 모르는 판의 줄은 글자 그대로 남는다", () => {
  const [a, b, c] = three();
  const m = C.mergeLines(Object.freeze([a, b]), Object.freeze([BROKEN, c, V2, a]), "2026-10");                 // 받은 배열은 고치지 않는다
  assert.deepEqual(F.plain(m), { lines: [a, b, c, BROKEN, V2], toUpload: [b], added: [BROKEN, c, V2] });
  assert.deepEqual(F.plain(C.mergeLines([b, a], [a, V2, c, BROKEN], "2026-10").lines), F.plain(m.lines));       // 순서와 무관
  const again = C.mergeLines([a, b, c], F.plain(m.lines), "2026-10");                                            // 올리고 흡수한 뒤 다시
  assert.deepEqual(F.plain(again), { lines: F.plain(m.lines), toUpload: [], added: [BROKEN, V2] });
});

test("core 합치기: 차례 · 끝 줄바꿈 · CR · 겹친 줄만 다른 원격 파일에는 올릴 것이 없다", () => {
  const [a, b, c] = three();
  const files = [c + "\n" + a + "\n" + b, a + "\r\n" + b + "\r\n" + c + "\r\n", "\n\n" + b + "\n" + c + "\n\n" + a + "\n\n", a + "\n" + a + "\n" + c + "\n" + b + "\n", C.joinLines([a, b, c])];
  for (const file of files) {
    const m = C.mergeLines([a, b, c], C.splitLines(file), "2026-10");
    assert.deepEqual(F.plain([m.toUpload, m.added, m.lines]), [[], [], [a, b, c]], JSON.stringify(file.slice(-3)));
  }
});

test("core 합치기: 같은 id · 다른 글자인 두 줄은 둘 다 남고, 두 기기가 한 바퀴 뒤에는 올릴 것이 없다", () => {
  const x1 = mk("next", { text: "하나" }, "2026-10-12T23:30:00Z", "폰", "same");
  const x2 = mk("next", { text: "둘" }, "2026-10-12T23:30:00Z", "폰", "same");
  let remote = [];
  const devices = [[x1], [x2]];
  const ups = [];
  for (let round = 0; round < 3; round++) {
    for (const i of [0, 1]) {
      const m = C.mergeLines(devices[i], remote, "2026-10");
      if (m.toUpload.length > 0) remote = F.plain(m.lines);
      devices[i] = [...devices[i], ...F.plain(m.added)];
      ups.push(m.toUpload.length);
    }
  }
  assert.deepEqual(ups, [1, 1, 0, 0, 0, 0]);
  assert.deepEqual([remote, devices.map(d => d.length)], [[x2, x1], [2, 2]]);                                    // "둘" < "하나"
});

test("core 합치기: 받을 달과 묵은 대기 줄", () => {
  const oct = mk("next", { text: "10월" }, "2026-10-12T23:30:00Z", "폰", "aaaa");
  const aug = mk("next", { text: "8월" }, "2026-08-20T01:00:00Z", "폰", "bbbb");
  const dawn = mk("next", { text: "새벽" }, "2026-09-30T18:30:00Z", "폰", "cccc");                             // KST 10-01 03:30 → 9월 파일
  assert.deepEqual([oct, dawn, BROKEN, V2].map(l => C.lineMonth(l)), ["2026-10", "2026-09", null, null]);
  assert.deepEqual(F.plain(C.monthsToFetch("2026-10-13", [])), ["2026-09", "2026-10"]);
  assert.deepEqual(F.plain(C.monthsToFetch("2026-10-13", [oct, aug, dawn, BROKEN, aug])), ["2026-08", "2026-09", "2026-10"]);
  assert.deepEqual(F.plain(C.monthsToFetch("2027-01-01", [])), ["2026-12", "2027-01"]);
  const stale = (queue, today) => C.staleQueue(queue, today);
  assert.deepEqual([stale([], "2026-10-13"), stale([oct], "2026-10-13"), stale([oct], "2026-10-14"), stale([oct, BROKEN], "2026-10-13"), stale([oct, dawn], "2026-10-13")],
    [false, false, true, false, true]);
});

// ── core.js: 보기 ──
const TODAY = "2026-10-13";
const kst = (date, time) => date + "T" + (time || "08:30") + ":00+09:00";
const idOf = text => JSON.parse(text).id;
const ids = recs => Array.from(recs, r => r.id);
const viewOf = lines => C.buildView([...new Set(lines.map(l => C.lineMonth(l)))].map(month => ({ month, lines: lines.filter(l => C.lineMonth(l) === month) })));
const stamp = (date, mark, opt = {}) => mk("day", { mark, sec: 120, rec: 0, stuck: opt.stuck || "" }, kst(date, opt.time), opt.dev || "폰", opt.rand || "st" + date.slice(8));
const ask = (text, date, time, rand) => mk("q", { text, sec: 97, rec: 77, s_head: true, s_two: true, s_wrong: false }, kst(date, time), "폰", rand);
const fix = (ref, hide, time, rand) => mk("fix", { ref, hide }, kst(TODAY, time), "폰", rand);

test("core 보기: 꼴이 맞지 않는 줄은 세고 버리고, 같은 id의 다른 글자는 앞선 하나만 쓴다", () => {
  const a = stamp("2026-10-12", "min");
  const x1 = mk("next", { text: "하나" }, kst(TODAY), "폰", "same");
  const x2 = mk("next", { text: "둘" }, kst(TODAY), "폰", "same");
  const sept = stamp("2026-09-30", "full");
  const view = C.buildView([{ month: "2026-10", lines: [x1, BROKEN, a, V2, x2, a, sept] }, { month: "2026-09", lines: [sept] }]);
  assert.deepEqual([view.bad, view.clash, view.hidden.size], [3, 1, 0]);                    // 깨진 줄 · 모르는 판 · 다른 달 파일의 줄
  assert.deepEqual([ids(view.recs), view.recs[2].text], [[idOf(sept), idOf(a), idOf(x2)], "둘"]);   // id 순, 충돌은 글자 순으로 앞선 것
  const junk = C.buildView([{ month: "2026-10", lines: [caseOf("field-ref-proto").text, caseOf("keys-proto").text] }, { month: "2026-11", lines: [] }]);
  assert.deepEqual([junk.bad, junk.clash, junk.recs.length], [2, 0, 0]);
  assert.deepEqual(F.plain(C.buildView([])), { recs: [], hidden: {}, clash: 0, bad: 0 });
});

test("core 보기: 가림은 가장 늦은 고침 줄이 정한다 — 가림 · 가림 풀림 · 엉뚱한 곳을 가리키는 고침은 무시", () => {
  const q1 = ask("첫 질문", TODAY, "21:00", "q001");
  const q2 = ask("둘째 질문", TODAY, "21:01", "q002");
  const h1 = fix(idOf(q1), true, "21:10", "f001");
  const h2 = fix(idOf(q1), false, "21:20", "f002");                                          // 가림 풀림
  const h3 = fix(idOf(q2), true, "21:30", "f003");
  const ghost = fix("20260101000000000-폰-none", true, "21:40", "f004");                    // 없는 줄
  const meta = fix(idOf(h3), true, "21:50", "f005");                                         // 고침 줄을 가리키는 고침
  assert.deepEqual(ids(viewOf([q1, q2, h1]).recs), [idOf(q2)]);
  const view = viewOf([meta, ghost, h3, h2, h1, q2, q1]);
  assert.deepEqual([ids(view.recs), [...view.hidden], view.bad, view.clash], [[idOf(q1)], [idOf(q2)], 0, 0]);
  assert.deepEqual([viewOf([h1]).recs.length, viewOf([h1]).hidden.size], [0, 0]);
});

test("core 보기: 그날의 도장은 정상이 이기고, 14일 줄에서 도장이 쉼을 이긴다 — 쉼은 내일부터", () => {
  const lines = [stamp("2026-10-10", "min"), stamp("2026-10-10", "full", { dev: "PC", time: "09:00" }),
    stamp("2026-10-11", "min", { time: "08:00", rand: "aaa1" }), stamp("2026-10-11", "min", { time: "09:00", rand: "aaa2" }),
    mk("rest", { on: "2026-10-12" }, kst("2026-10-11", "10:00"), "폰", "r001"), mk("rest", { on: "2026-10-11" }, kst("2026-10-10", "10:00"), "폰", "r002"),
    mk("rest", { on: "2026-10-12" }, kst("2026-10-11", "11:00"), "PC", "r003")];
  const view = viewOf(lines);
  assert.deepEqual([C.stampOn(view, "2026-10-10").dev, C.stampOn(view, "2026-10-11").id.slice(-4), C.stampOn(view, TODAY)], ["PC", "aaa1", null]);
  assert.deepEqual([F.plain(C.restOn(view, "2026-10-12")), F.plain(C.restOn(view, TODAY))], [{ on: true, id: idOf(lines[6]) }, { on: false, id: null }]);
  const strip = F.plain(C.strip14(view, TODAY));
  assert.deepEqual([strip.length, strip[0], strip[13]], [14, { date: "2026-09-30", cell: "none" }, { date: TODAY, cell: "none" }]);
  assert.deepEqual(strip.slice(10).map(c => c.cell), ["full", "min", "rest", "none"]);       // 10-11은 쉼이었지만 도장이 이긴다
  assert.equal(C.makeLine("rest", { on: TODAY }, { nowMs: at(kst(TODAY)), dev: "폰", rand: "r004" }).code, "rule");   // 오늘은 쉼으로 만들 수 없다
});

test("core 보기: 오늘 말할 개념 — 앞선 날에 적은 가장 늦은 것, 그 뒤에 말했으면 없다", () => {
  const n1 = mk("next", { text: "볼록성" }, kst("2026-10-09", "08:40"), "폰", "n001");
  const n2 = mk("next", { text: "기간 프리미엄" }, kst("2026-10-09", "08:50"), "PC", "n002");
  const mine = mk("next", { text: "내일 것" }, kst(TODAY, "08:40"), "폰", "n003");
  const topic = lines => C.topicFor(viewOf(lines), TODAY);
  assert.deepEqual([topic([]), topic([mine])], [null, null]);
  assert.equal(topic([n1, n2, mine]), "기간 프리미엄");                                       // 며칠 전 것이어도 뜬다. 오늘 쓴 것은 내일 몫
  assert.equal(topic([n1, n2, stamp("2026-10-09", "full", { time: "08:35" })]), "기간 프리미엄");   // 같은 날의 도장은 '그 뒤'가 아니다
  assert.equal(topic([n1, n2, stamp("2026-10-11", "min")]), null);                           // 그 뒤에 도장 → 이미 말했다
  assert.equal(topic([n1, n2, stamp(TODAY, "min")]), "기간 프리미엄");                        // 오늘 도장을 찍어도 오늘은 그대로
  assert.equal(topic([n1, n2, mk("fix", { ref: idOf(n2), hide: true }, kst("2026-10-09", "09:00"), "PC", "f001")]), "볼록성");
});

test("core 보기: 돌아오는 날 권고 — 첫날에는 없고, 어제가 빈칸이고 오늘 도장이 없을 때만", () => {
  const old = stamp("2026-10-10", "full");
  const call = mk("week", { wk: "2026-10-12", dur: "n", cur: "n", why: "근거", wrong_if: "조건" }, kst("2026-10-12"), "PC", "w001");
  const table = [
    [[], false],                                                                             // 기록이 한 줄도 없는 기기
    [[stamp(TODAY, "min")], false],                                                          // 오늘 것만 있다(첫날)
    [[mk("next", { text: "개념" }, kst(TODAY), "폰", "n001")], false],
    [[old], true],                                                                           // 어제 비었다
    [[old, stamp("2026-10-12", "min", { dev: "PC" })], false],                               // 어제 도장이 다른 기기에 있었다
    [[old, mk("rest", { on: "2026-10-12" }, kst("2026-10-10", "09:00"), "폰", "r001")], false],   // 어제는 쉼
    [[old, stamp(TODAY, "min")], false],                                                     // 오늘 이미 찍었다
    [[call], true],                                                                          // 도장이 아닌 기록만 있어도 '쓰던 기기'다
  ];
  assert.deepEqual(table.map(row => C.comeback(viewOf(row[0]), TODAY)), table.map(row => row[1]));
});

test("core 보기: 주간 판정은 먼저 쓴 것, 채점은 그 판정을 가리키는 것, 질문은 늦은 것부터", () => {
  const W = { wk: "2026-10-05", dur: "ow", cur: "steep", why: "근거", wrong_if: "조건" };
  const G = { wk: "2026-10-05", actual: "실제", dur_hit: "y", cur_hit: "n", miss: "" };
  const w1 = mk("week", W, kst("2026-10-05", "08:00"), "PC", "w001");
  const w2 = mk("week", { ...W, dur: "uw" }, kst("2026-10-06", "08:00"), "폰", "w002");
  const g2 = mk("grade", { ...G, ref: idOf(w2) }, kst("2026-10-12", "08:00"), "폰", "g002");   // 둘째 판정을 가리킨다 — 쓰지 않는다
  const g1 = mk("grade", { ...G, ref: idOf(w1) }, kst("2026-10-12", "09:00"), "PC", "g001");
  const g3 = mk("grade", { ...G, ref: idOf(w1), dur_hit: "n" }, kst("2026-10-12", "10:00"), "PC", "g003");
  const view = viewOf([g3, g2, g1, w2, w1]);
  assert.deepEqual([C.weekCall(view, "2026-10-05").dur, C.weekCall(view, "2026-10-12"), C.gradeFor(view, "2026-10-05").id, C.gradeFor(view, "2026-10-12")],
    ["ow", null, idOf(g1), null]);
  assert.equal(C.gradeFor(viewOf([w2, w1, g2]), "2026-10-05"), null);
  const qs = [1, 2, 3, 4, 5, 6].map(i => ask("질문 " + i, "2026-10-0" + i, "21:00", "q00" + i));
  const view2 = viewOf([...qs, mk("fix", { ref: idOf(qs[5]), hide: true }, kst("2026-10-07"), "폰", "f001")]);
  assert.deepEqual([Array.from(C.recentQs(view2, 3), r => r.text), C.recentQs(view2, 9).length, C.recentQs(viewOf([]), 5).length], [["질문 5", "질문 4", "질문 3"], 5, 0]);
});

// ── core.js: 상태 고르기 · 공유할 글 ──
test("core 상태: 위에서부터 처음 맞는 하나 — 일곱 가지의 차례", () => {
  const base = { storeOk: true, hasKey: true, auth401: false, stop: null, code: null, paused: false, queueN: 0, lastOkMs: null, amber: false };
  const pick = over => { const p = C.pickStatus({ ...base, ...over }); return [p.name, p.key, C.t(p.key, p.vars), p.tone]; };
  assert.deepEqual(pick({ storeOk: false, auth401: true, stop: "halt", queueN: 2 }), ["STORE_FAIL", "ST_STORE_FAIL", "이 기기에 저장하지 못함", "red"]);
  assert.deepEqual(pick({ storeOk: false, hasKey: false }), ["STORE_FAIL", "ST_STORE_FAIL", "이 기기에 저장하지 못함", "red"]);
  assert.deepEqual(pick({ auth401: true, stop: "missing", paused: true, queueN: 2 }), ["REKEY", "ST_REKEY", "열쇠 다시 넣기", ""]);
  assert.deepEqual(["missing", "public", "file"].map(stop => pick({ stop, paused: true, queueN: 2 }).slice(0, 3)),
    [["REPO", "ST_REPO_MISSING", "저장소를 찾지 못함"], ["REPO", "ST_REPO_PUBLIC", "공개 상태 — 올리지 않습니다"], ["REPO", "ST_FILE", "기록 파일을 읽지 못함"]]);
  assert.deepEqual(pick({ paused: true, stop: "halt", code: 403, queueN: 2 }), ["HALT", "ST_PAUSED", "맞춤 멈춤", ""]);
  assert.deepEqual(pick({ stop: "halt", code: 403, queueN: 2 }), ["HALT", "ST_HALT", "맞춤 멈춤 — 오류 403", ""]);
  assert.deepEqual([pick({ queueN: 2 }), pick({ queueN: 2, amber: true })], [["QUEUE", "ST_QUEUE", "올릴 것 2건", ""], ["QUEUE", "ST_QUEUE", "올릴 것 2건", "amber"]]);
  assert.deepEqual(pick({ hasKey: false, auth401: true, stop: "halt", paused: true, queueN: 5, amber: true }), ["LOCAL", "ST_LOCAL", "이 기기에만 저장", ""]);
  assert.deepEqual([pick({ lastOkMs: F.T0 + 60000, amber: true }), pick({}), pick({ stop: "off" }), pick({ stop: "constructor" })],
    [["SYNCED", "ST_SYNCED", "맞춤 08:31", ""], ["SYNCED", "ST_SYNC_WAIT", "맞춤 전", ""], ["SYNCED", "ST_SYNC_WAIT", "맞춤 전", ""], ["SYNCED", "ST_SYNC_WAIT", "맞춤 전", ""]]);
  assert.deepEqual(F.plain(C.pickStatus({ ...base, queueN: 3 })), { name: "QUEUE", key: "ST_QUEUE", vars: { n: 3 }, tone: "" });
});

test("core 공유: 그날의 글 — 도장 · 그날 쓴 개념 · 질문을 줄마다, 가린 줄 · 기기 이름 · 녹음 초는 넣지 않는다", () => {
  const st = stamp(TODAY, "full", { stuck: "볼록성을 말로 잇지 못함", dev: "기기이름" });
  const n = mk("next", { text: "기간 프리미엄" }, kst(TODAY, "08:45"), "기기이름", "n001");
  const q1 = ask("A사의 듀레이션은", TODAY, "21:00", "q001");
  const q2 = ask("가릴 질문", TODAY, "21:05", "q002");
  const other = mk("next", { text: "어제 것" }, kst("2026-10-12", "08:45"), "기기이름", "n000");
  const text = C.shareDay(viewOf([st, n, q1, q2, fix(idOf(q2), true, "21:06", "f001"), other]), TODAY);
  assert.equal(text, "10-13 화 · 2분 말하기 ○\n막힌 곳: 볼록성을 말로 잇지 못함\n내일 말할 개념: 기간 프리미엄\n질문: A사의 듀레이션은");
  assert.deepEqual([/기기이름|77|97|가릴|어제/.test(text), C.shareDay(viewOf([n, q1]), TODAY), C.shareDay(viewOf([stamp(TODAY, "min")]), TODAY)],
    [false, null, "10-13 화 · 2분 말하기 △"]);
  assert.equal(C.shareDay(viewOf([stamp(TODAY, "min", { stuck: "{mark} $& <b>" })]), TODAY), "10-13 화 · 2분 말하기 △\n막힌 곳: {mark} $& <b>");
});

test("core 공유: 그 주의 글 — 판정과, 있으면 채점. 판정이 없으면 없다", () => {
  const w = mk("week", { wk: "2026-10-05", dur: "ow", cur: "steep", why: "고용 둔화", wrong_if: "근원 물가" }, kst("2026-10-05", "08:00"), "PC", "w001");
  const G = { wk: "2026-10-05", ref: idOf(w), actual: "10년 금리 8bp 하락", dur_hit: "y", cur_hit: "na", miss: "단기가 더 내렸다" };
  const head = "2026-10-05 주 · 듀레이션 비중 확대 · 커브 스티프닝\n근거: 고용 둔화\n틀릴 조건: 근원 물가";
  const share = lines => C.shareWeek(viewOf(lines), "2026-10-05");
  assert.equal(share([w]), head);
  assert.equal(share([w, mk("grade", G, kst("2026-10-12", "08:00"), "PC", "g001")]), head + "\n실제: 10년 금리 8bp 하락\n듀레이션 맞음 · 커브 판단 보류\n빗나간 이유: 단기가 더 내렸다");
  assert.equal(share([w, mk("grade", { ...G, dur_hit: "n", miss: "" }, kst("2026-10-12", "08:00"), "PC", "g001")]), head + "\n실제: 10년 금리 8bp 하락\n듀레이션 빗나감 · 커브 판단 보류");
  assert.deepEqual([C.shareWeek(viewOf([w]), "2026-10-12"), share([]), /PC|w001/.test(share([w]))], [null, null, false]);
  const flat = mk("week", { wk: "2026-10-05", dur: "uw", cur: "flat", why: "근거", wrong_if: "조건" }, kst("2026-10-05", "08:00"), "PC", "w002");
  assert.equal(share([flat]).split("\n")[0], "2026-10-05 주 · 듀레이션 비중 축소 · 커브 플래트닝");
});

test("core: 약속된 이름이 모두 있고 그 밖의 것은 없다(뒤 단계는 이 이름에 기댄다)", () => {
  const names = ["V", "TALK_SEC", "DAY_START_HOUR", "MAX_LINE_BYTES", "KINDS", "HEAD", "SCHEMA", "REJECT", "ID_RE", "DEV_RE", "KEY_LINK_BASE", "ROUTES", "T",
    "studyDate", "stampT", "idTime", "idMs", "isDate", "addDays", "weekOf", "monthOf", "prevMonth", "headDate", "hhmm", "mmss",
    "makeId", "makeLine", "checkLine", "textIssue", "devOk", "ownerOk", "repoOk", "keyShape", "keyLink", "safeLink",
    "splitLines", "joinLines", "orderLines", "mergeLines", "lineMonth", "monthsToFetch", "staleQueue",
    "buildView", "stampOn", "restOn", "strip14", "topicFor", "comeback", "weekCall", "gradeFor", "recentQs",
    "pickStatus", "shareDay", "shareWeek", "t"];
  assert.deepEqual([names.length, Object.keys(C).sort()], [55, [...names].sort()]);
});

// ── store.js: 값 하나짜리 칸 — 기기 이름 · 켜고 끄기 · 연결 · 열쇠 ──
const LS = "macro-study.";                                                         // 저장 이름의 머리(화면 쪽 상수 P와 같은 글자)
const KEY = "k".repeat(64);                                                        // 가짜 열쇠 — 글자를 소스에 적지 않는다
const storeOn = (storage, opts = {}) => F.world(["core.js", "store.js"], { ...opts, storage }).scope.StudyStore;
const newStore = seed => { const storage = F.fakeStorage(seed); return { storage, S: storeOn(storage) }; };
const names = storage => [...storage.data.keys()].map(k => k.replace(LS, "")).sort();
const deaf = () => { const no = () => { throw new Error("SecurityError"); }; return { getItem: no, setItem: no, removeItem: no }; };

test("store 값: 읽기만으로는 아무것도 적지 않고, 처음 쓸 때 판 번호를 적는다 — 이름은 모두 접두어로 시작한다", () => {
  const { storage, S } = newStore();
  assert.deepEqual([S.ok(), S.getDevice(), S.getFlag("rec"), S.hasKey(), storage.data.size], [true, "", true, false, 0]);
  assert.deepEqual(F.plain(S.setDevice("폰")), { ok: true, code: null });
  assert.deepEqual([...storage.data], [[LS + "ver", "1"], [LS + "dev", "폰"]]);
  S.setFlag("pause", true);
  S.setOwner("owner");
  assert.deepEqual([[...storage.data.keys()].filter(k => !k.startsWith(LS)), names(storage)], [[], ["dev", "owner", "pause", "ver"]]);
  assert.deepEqual([storeOn(storage).getDevice(), S.ok()], ["폰", true]);              // 다시 열어도 남는다
});

test("store 기기 이름: 꼴이 틀리면 적지 않고, 꼴이 틀린 저장값은 없는 것으로 읽는다", () => {
  const { storage, S } = newStore();
  assert.deepEqual(["", "아홉글자기기이름임", "a b", null].map(name => F.plain(S.setDevice(name))), Array(4).fill({ ok: false, code: "dev" }));
  assert.equal(storage.data.size, 0);
  assert.deepEqual(["a b", "", "x".repeat(9)].map(dev => newStore({ [LS + "dev"]: dev }).S.getDevice()), ["", "", ""]);
  assert.equal(newStore({ [LS + "dev"]: "PC" }).S.getDevice(), "PC");
});

test("store 켜고 끄기: 녹음은 켬, 자동 맞춤 멈춤은 끔이 기본이다", () => {
  const { storage, S } = newStore({ [LS + "rec"]: "yes" });                             // 모르는 값은 기본값으로 읽는다
  assert.deepEqual([S.getFlag("rec"), S.getFlag("pause"), S.getFlag("key"), S.getFlag("constructor")], [true, false, false, false]);
  assert.deepEqual([F.plain(S.setFlag("rec", false)), F.plain(S.setFlag("pause", true)), F.plain(S.setFlag("key", true))], [{ ok: true }, { ok: true }, { ok: false }]);
  assert.deepEqual([S.getFlag("rec"), S.getFlag("pause"), storage.data.get(LS + "rec"), storage.data.get(LS + "pause")], [false, true, "0", "1"]);
});

test("store 연결: 주인 · 저장소 이름은 치는 대로 적고, 열쇠 값은 readKey로만 나간다", () => {
  const { storage, S } = newStore();
  assert.deepEqual(F.plain(S.getConn()), { owner: "", repo: "", hasKey: false, auth: "ok" });
  S.setOwner("own er/");                                                                 // 검증하지 않는다(맞춤이 요청 전에 본다)
  S.setRepo("repo");
  assert.deepEqual([F.plain(S.setKey(KEY)), S.hasKey(), S.readKey() === KEY], [{ ok: true }, true, true]);
  assert.deepEqual(F.plain(S.getConn()), { owner: "own er/", repo: "repo", hasKey: true, auth: "ok" });
  assert.equal(JSON.stringify(F.plain(S.getConn())).includes(KEY), false);
  assert.deepEqual([F.plain(S.setAuth("401")), S.getConn().auth, F.plain(S.setAuth("no")), S.getConn().auth], [{ ok: true }, "401", { ok: false }, "401"]);
  S.setKey(KEY);                                                                         // 새 열쇠를 넣으면 다시 "ok"
  assert.equal(S.getConn().auth, "ok");
  S.setAuth("401");
  assert.deepEqual([F.plain(S.clearKey()), S.hasKey(), S.readKey(), S.getConn().auth, storage.data.has(LS + "key")], [{ ok: true }, false, "", "ok", false]);
});

test("store 열쇠: 꼴이 아닌 글은 적지도 내주지도 않는다", () => {
  const { storage, S } = newStore();
  assert.deepEqual(["", "k".repeat(59), KEY + " ", KEY + "\n", null].map(s => F.plain(S.setKey(s))), Array(5).fill({ ok: false }));
  assert.deepEqual([storage.data.size, S.hasKey()], [0, false]);
  const odd = newStore({ [LS + "key"]: "줄\n바꿈", [LS + "auth"]: "nope" }).S;
  assert.deepEqual([odd.hasKey(), odd.readKey(), odd.getConn().auth], [false, "", "ok"]);
});

test("store 값: 적지 못한 값은 메모리 대역에 남아 이번 실행 동안은 읽히고, ok()는 거짓이 된다", () => {
  const { storage, S } = newStore({ [LS + "dev"]: "PC" });
  storage.failOn("macro-study");                                                         // 한도가 찼다
  assert.deepEqual([F.plain(S.setDevice("폰")), S.getDevice(), S.ok(), storage.data.get(LS + "dev")], [{ ok: false, code: "store" }, "폰", false, "PC"]);
  assert.deepEqual([F.plain(S.setFlag("rec", false)), S.getFlag("rec"), F.plain(S.setKey(KEY)), S.hasKey()], [{ ok: false }, false, { ok: false }, true]);
  storage.failOn(null);                                                                  // 자리가 났다
  assert.deepEqual([F.plain(S.setDevice("폰")), storage.data.get(LS + "dev"), S.ok()], [{ ok: true, code: null }, "폰", false]);   // ok()는 이번 실행 동안 거짓으로 남는다
  assert.equal(storeOn(storage).ok(), true);
});

test("store 값: 읽기 · 쓰기 · 지우기가 모두 던지는 저장 공간에서도 던지지 않는다", () => {
  const S = storeOn(deaf());
  assert.deepEqual([S.getDevice(), S.getFlag("pause"), F.plain(S.getConn()), S.ok()], ["", false, { owner: "", repo: "", hasKey: false, auth: "ok" }, true]);
  assert.deepEqual([F.plain(S.setDevice("폰")), S.getDevice(), S.ok()], [{ ok: false, code: "store" }, "폰", false]);
  assert.deepEqual([F.plain(S.setKey(KEY)), S.hasKey(), F.plain(S.clearKey()), S.hasKey(), S.readKey()], [{ ok: false }, true, { ok: false }, false, ""]);
  const w = F.world(["core.js", "store.js"]);
  Object.defineProperty(w.scope, "localStorage", { get() { throw new Error("SecurityError"); } });     // 손을 대는 것부터 던진다(저장을 막아 둔 브라우저)
  const blocked = w.scope.StudyStore;
  assert.deepEqual([blocked.getDevice(), F.plain(blocked.setDevice("PC")), blocked.getDevice(), blocked.ok()], ["", { ok: false, code: "store" }, "PC", false]);
});

// ── store.js: 줄 — 달 사본 · 달 목록 · 대기 줄 ──
const L1 = mk("next", { text: "하나" }, "2026-10-12T23:30:00Z", "폰", "aaaa");
const L2 = mk("next", { text: "둘" }, "2026-10-12T23:31:00Z", "폰", "bbbb");
const L3 = mk("next", { text: "셋" }, "2026-10-12T23:32:00Z", "폰", "cccc");
const SEPT = mk("next", { text: "9월" }, "2026-09-29T23:00:00Z", "폰", "dddd");                   // 9월 파일로 가는 줄

test("store 줄: 달 사본 → 달 목록 → 대기 줄 순으로 적고, 같은 줄은 한 번만 둔다", () => {
  const storage = F.fakeStorage();
  const wrote = [];
  const S = storeOn({ ...storage, setItem: (k, v) => { wrote.push(k.replace(LS, "")); storage.setItem(k, v); } });
  assert.deepEqual([F.plain(S.appendLine("2026-10", L1)), wrote], [{ ok: true }, ["ver", "m.2026-10", "months", "q"]]);
  assert.deepEqual([F.plain(S.appendLine("2026-10", L1)), wrote.length], [{ ok: true }, 4]);           // 이미 있는 줄 — 다시 적지 않는다
  S.appendLine("2026-10", L2);
  S.appendLine("2026-09", SEPT);
  assert.deepEqual(wrote.slice(4), ["m.2026-10", "q", "m.2026-09", "months", "q"]);
  assert.deepEqual(F.plain([S.monthLines("2026-10"), S.monthLines("2026-09"), S.monthLines("2026-08"), S.months(), S.queue()]),
    [[L1, L2], [SEPT], [], ["2026-09", "2026-10"], [L1, L2, SEPT]]);
  assert.deepEqual(F.plain(S.copies()), [{ month: "2026-09", lines: [SEPT] }, { month: "2026-10", lines: [L1, L2] }]);
  assert.deepEqual([storage.data.get(LS + "m.2026-10"), storage.data.get(LS + "months")], [L1 + "\n" + L2, '["2026-10","2026-09"]']);
});

test("store 줄: 달 이름이나 줄이 꼴이 아니면 적지 않는다", () => {
  const { storage, S } = newStore();
  const bad = [["2026-13", L1], ["2026-1", L1], ["__proto__", L1], [202610, L1], ["2026-10", ""], ["2026-10", L1 + "\n" + L2], ["2026-10", L1 + "\r"], ["2026-10", null]];
  assert.deepEqual(bad.map(pair => F.plain(S.appendLine(pair[0], pair[1]))), Array(8).fill({ ok: false }));
  assert.deepEqual([storage.data.size, S.ok(), F.plain(S.monthLines("__proto__")), F.plain(S.monthLines("2026-13"))], [0, true, [], []]);
});

test("store 줄: setItem이 예외를 내면 ok()가 거짓이 되고, 그 줄은 메모리 대역에 남아 함께 읽힌다", () => {
  const { storage, S } = newStore();
  S.appendLine("2026-10", L1);
  storage.failOn("macro-study");                                                         // 한도가 찼다
  assert.deepEqual([F.plain(S.appendLine("2026-10", L2)), F.plain(S.appendLine("2026-09", SEPT)), S.ok()], [{ ok: false }, { ok: false }, false]);
  assert.deepEqual(F.plain([S.monthLines("2026-10"), S.months(), S.queue()]), [[L1, L2], ["2026-09", "2026-10"], [L1, L2, SEPT]]);
  assert.equal(C.buildView(F.plain(S.copies())).recs.length, 3);                         // 화면은 그 줄을 그린다
  assert.deepEqual([storage.data.get(LS + "m.2026-10"), storage.data.has(LS + "m.2026-09")], [L1, false]);
  storage.failOn(null);                                                                  // 자리가 났다 — 다음 쓰기가 밀린 줄도 함께 적는다
  assert.deepEqual([F.plain(S.appendLine("2026-10", L3)), S.ok()], [{ ok: true }, false]);              // ok()는 이번 실행 동안 거짓으로 남는다
  const again = storeOn(storage);
  assert.deepEqual(F.plain([again.monthLines("2026-10"), again.monthLines("2026-09"), again.queue(), again.ok()]), [[L1, L2, L3], [SEPT], [L1, L2, SEPT, L3], true]);
});

test("store 줄: 달 사본만 적지 못해도 그 줄은 읽히고 대기 줄에 선다", () => {
  const { storage, S } = newStore();
  storage.failOn(/\.m\./);
  assert.deepEqual([F.plain(S.appendLine("2026-10", L1)), S.ok()], [{ ok: false }, false]);
  assert.deepEqual(F.plain([S.monthLines("2026-10"), JSON.parse(storage.data.get(LS + "q")), JSON.parse(storage.data.get(LS + "months"))]), [[L1], [L1], ["2026-10"]]);
});

test("store 줄: 던지기만 하는 저장 공간에서도 줄은 이번 실행 동안 읽히고, 올린 줄은 대기 줄에서 빠진다", () => {
  const S = storeOn(deaf());
  assert.deepEqual([F.plain(S.appendLine("2026-10", L1)), F.plain(S.appendLine("2026-10", L2)), S.ok()], [{ ok: false }, { ok: false }, false]);
  assert.deepEqual(F.plain([S.monthLines("2026-10"), S.months(), S.queue(), S.copies()]), [[L1, L2], ["2026-10"], [L1, L2], [{ month: "2026-10", lines: [L1, L2] }]]);
  assert.deepEqual([F.plain(S.dequeue([L1])), F.plain(S.queue()), F.plain(S.monthLines("2026-10"))], [{ ok: true }, [L2], [L1, L2]]);
});

test("store 줄: 한 저장 공간을 보는 두 store가 번갈아 써도 줄이 남는다(탭 둘)", () => {
  const storage = F.fakeStorage();
  const [A, B] = [storeOn(storage), storeOn(storage)];
  A.appendLine("2026-10", L1);
  B.appendLine("2026-10", L2);
  A.appendLine("2026-10", L3);
  B.appendLine("2026-09", SEPT);
  assert.deepEqual(F.plain([A.monthLines("2026-10"), B.monthLines("2026-10"), A.months(), A.queue()]), [[L1, L2, L3], [L1, L2, L3], ["2026-09", "2026-10"], [L1, L2, L3, SEPT]]);
  B.dequeue([L1, SEPT]);
  A.setOwner("owner");
  assert.deepEqual([F.plain(A.queue()), F.plain(B.queue()), B.getConn().owner], [[L2, L3], [L2, L3], "owner"]);
});

test("store 줄: 깨진 저장값은 빈 것으로 읽고, 다음 쓰기가 바로잡는다", () => {
  const { storage, S } = newStore({ [LS + "q"]: "{깨진 글", [LS + "months"]: '{"a":1}', [LS + "m.2026-10"]: "" });
  assert.deepEqual(F.plain([S.queue(), S.months(), S.monthLines("2026-10"), S.copies()]), [[], [], [], []]);
  const mixed = newStore({ [LS + "q"]: '[1,"a",null,"a",["b"]]', [LS + "months"]: '["2026-10","nope","2026-13",7]' }).S;
  assert.deepEqual(F.plain([mixed.queue(), mixed.months()]), [["a"], ["2026-10"]]);
  assert.deepEqual([F.plain(S.appendLine("2026-10", L1)), JSON.parse(storage.data.get(LS + "q")), JSON.parse(storage.data.get(LS + "months"))], [{ ok: true }, [L1], ["2026-10"]]);
});

test("store 줄: dequeue는 글자가 같은 줄만 빼고, 달 사본은 그대로 둔다", () => {
  const { storage, S } = newStore();
  [L1, L2, L3].forEach(line => S.appendLine("2026-10", line));
  assert.deepEqual([F.plain(S.dequeue([L2, L2.replace("둘", "셋"), "없는 줄"])), F.plain(S.queue()), S.monthLines("2026-10").length], [{ ok: true }, [L1, L3], 3]);
  assert.deepEqual([F.plain(S.dequeue(null)), F.plain(S.dequeue([])), S.queue().length], [{ ok: true }, { ok: true }, 2]);
  storage.failOn(/\.q$/);
  assert.deepEqual([F.plain(S.dequeue([L1])), F.plain(S.queue()), S.ok()], [{ ok: false }, [L1, L3], false]);   // 빼지 못했다 — 다음 맞춤에서 원격에 이미 있는 줄로 걸러진다
});

// ── store.js: 받은 줄 흡수 · 사본 비우기 ──
test("store 흡수: 없는 줄만 달 사본에 더하고, 대기 줄에는 넣지 않는다", () => {
  const { storage, S } = newStore();
  S.appendLine("2026-10", L1);
  assert.deepEqual(F.plain(S.absorb("2026-10", [L2, L1, L2, L3 + "\r", "a\nb", "", 7])), { ok: true, added: 1, code: null });
  assert.deepEqual(F.plain([S.monthLines("2026-10"), S.queue()]), [[L1, L2], [L1]]);
  const before = storage.data.get(LS + "m.2026-10");
  assert.deepEqual([F.plain(S.absorb("2026-10", [L2, L1])), F.plain(S.absorb("2026-10", [])), storage.data.get(LS + "m.2026-10") === before], [{ ok: true, added: 0, code: null }, { ok: true, added: 0, code: null }, true]);
  assert.deepEqual([F.plain(S.absorb("2026-09", [SEPT])), F.plain(S.months())], [{ ok: true, added: 1, code: null }, ["2026-09", "2026-10"]]);
  assert.deepEqual([F.plain(S.absorb("2026-13", [L3])), F.plain(S.absorb("2026-10", L3))], [{ ok: false, added: 0, code: "store" }, { ok: false, added: 0, code: "store" }]);
});

test("store 흡수: 달 사본이 300KB를 넘게 되면 하나도 더하지 않는다 — 그 뒤에도 내 줄은 적힌다", () => {
  const { S } = newStore();
  const full = "가".repeat(102400);                                                      // 한글 한 글자는 3바이트 — 꼭 300 × 1024바이트
  assert.deepEqual([S.MAX_COPY_BYTES, F.plain(S.absorb("2026-10", [full + "가"])), S.monthLines("2026-10").length], [307200, { ok: false, added: 0, code: "big" }, 0]);
  assert.deepEqual(F.plain(S.absorb("2026-10", [full])), { ok: true, added: 1, code: null });                 // 꼭 맞으면 받는다
  assert.deepEqual([F.plain(S.absorb("2026-10", [L1, L2])), S.monthLines("2026-10").length, S.ok()], [{ ok: false, added: 0, code: "big" }, 1, true]);
  assert.deepEqual([F.plain(S.appendLine("2026-10", L1)), F.plain(S.queue()), S.monthLines("2026-10").length], [{ ok: true }, [L1], 2]);
  assert.deepEqual(F.plain(S.absorb("2026-09", [SEPT])), { ok: true, added: 1, code: null });                 // 다른 달은 그대로 받는다
});

test("store 흡수: 적지 못하면 store — 받은 줄은 메모리 대역에 두지 않는다(원격에 있다)", () => {
  const { storage, S } = newStore();
  storage.failOn(/\.m\./);
  assert.deepEqual([F.plain(S.absorb("2026-10", [L1])), F.plain(S.monthLines("2026-10")), S.ok()], [{ ok: false, added: 0, code: "store" }, [], false]);
  const D = storeOn(deaf());
  D.appendLine("2026-10", L1);
  assert.deepEqual([F.plain(D.absorb("2026-10", [L2])), F.plain(D.resetMonths()), F.plain(D.queue())], [{ ok: false, added: 0, code: "store" }, { ok: false }, [L1]]);
});

test("store 사본 비우기: 달 사본과 달 목록을 비우고 대기 줄은 남긴다", () => {
  const { storage, S } = newStore();
  S.appendLine("2026-10", L1);
  S.absorb("2026-10", [L2]);
  S.absorb("2026-09", [SEPT]);
  S.setDevice("폰");
  assert.deepEqual([F.plain(S.resetMonths()), F.plain(S.months()), F.plain(S.copies()), F.plain(S.monthLines("2026-10")), F.plain(S.queue())], [{ ok: true }, [], [], [], [L1]]);
  assert.deepEqual([names(storage), S.getDevice()], [["dev", "q", "ver"], "폰"]);
  assert.deepEqual([F.plain(S.absorb("2026-10", [L2])), F.plain(S.monthLines("2026-10"))], [{ ok: true, added: 1, code: null }, [L2]]);   // 비운 뒤 받은 것만 있다
});

// ── store.js: 쓰던 글 · 시계 상태 · 맞춤 상태 · 오래 두기 ──
test("store 쓰던 글: 다시 열어도 남고, 칸 이름은 목록의 것만 받는다 — 열쇠 꼴의 글은 두지 않는다", () => {
  const { storage, S } = newStore();
  assert.deepEqual([F.plain(S.setDraft("td.stuck", "볼록성을 말로")), F.plain(S.setDraft("wk.dur", "ow")), storeOn(storage).draft("td.stuck"), S.draft("wk.cur")], [{ ok: true }, { ok: true }, "볼록성을 말로", ""]);
  assert.deepEqual(["set.key", "set-owner", "constructor", "__proto__"].map(slot => [F.plain(S.setDraft(slot, "글")), S.draft(slot)]), Array(4).fill([{ ok: false }, ""]));
  assert.deepEqual([F.plain(S.setDraft("td.stuck", "앞 " + KEY)), S.draft("td.stuck"), F.plain(S.setDraft("ask.text", "가".repeat(1001))), S.draft("ask.text")], [{ ok: false }, "", { ok: false }, ""]);
  assert.deepEqual([F.plain(S.setDraft("ask.text", "가".repeat(1000))), S.draft("ask.text").length, F.plain(S.setDraft("td.next", 7))], [{ ok: true }, 1000, { ok: false }]);
  S.setDraft("td.nostuck", "1");
  S.setDraft("wk.dur", "");                                                              // 빈 글은 칸을 지운다
  assert.deepEqual([F.plain(S.clearDrafts(["td.nostuck", "ask.text", "없는칸"])), JSON.parse(storage.data.get(LS + "draft"))], [{ ok: true }, {}]);
  assert.equal(JSON.stringify([...storage.data]).includes(KEY), false);
});

test("store 시계 상태: 화면마다 따로 두고, 꼴이 맞지 않으면 없는 것으로 친다", () => {
  const { storage, S } = newStore();
  const a = { d: "2026-10-13", at: F.T0, end: null };
  assert.deepEqual([F.plain(S.setTalk("today", a)), F.plain(S.setTalk("ask", { ...a, end: F.T0 + 5000, more: "x" })), F.plain(S.talk("today")), F.plain(S.talk("ask"))],
    [{ ok: true }, { ok: true }, a, { ...a, end: F.T0 + 5000 }]);
  assert.deepEqual([F.plain(S.setTalk("today", null)), S.talk("today"), F.plain(storeOn(storage).talk("ask")), S.talk("set")], [{ ok: true }, null, { ...a, end: F.T0 + 5000 }, null]);
  const bad = [{ d: "2026-02-30", at: 1, end: null }, { d: "2026-10-13", at: "1", end: null }, { d: "2026-10-13", at: 1 }, { d: "2026-10-13", at: 1, end: "x" }, "today", 7];
  assert.deepEqual(bad.map(v => F.plain(S.setTalk("today", v))).concat([F.plain(S.setTalk("week", a))]), Array(7).fill({ ok: false }));
  assert.equal(newStore({ [LS + "talk"]: '{"today":{"d":"어제","at":1,"end":null},"ask":[1]}' }).S.talk("today"), null);
});

test("store 맞춤 상태: 기본값에 얹어 적고, 꼴이 맞지 않는 칸은 기본값으로 읽는다", () => {
  const { storage, S } = newStore();
  assert.deepEqual(F.plain(S.syncState()), { at: null, err: null, repo: null, bad: 0 });
  S.setSyncState({ err: { code: 503, key: "ERR_SERVER" }, bad: 2 });
  S.setSyncState({ at: F.T0, repo: { d: "2026-10-13", state: "ok" }, extra: 1 });
  assert.deepEqual(F.plain(storeOn(storage).syncState()), { at: F.T0, err: { code: 503, key: "ERR_SERVER" }, repo: { d: "2026-10-13", state: "ok" }, bad: 2 });
  assert.deepEqual([F.plain(S.setSyncState({ err: null, repo: null })), S.syncState().err, S.syncState().repo, S.syncState().at], [{ ok: true }, null, null, F.T0]);
  S.setSyncState({ at: "어제", err: { code: "x", key: "<b>" }, repo: { d: "2026-10-13", state: "open" }, bad: -1 });
  assert.deepEqual([F.plain(S.syncState()), F.plain(S.setSyncState(null))], [{ at: null, err: null, repo: null, bad: 0 }, { ok: true }]);
});

test("store 쓰던 글 · 시계 상태 · 맞춤 상태: 깨진 저장값은 빈 것으로 읽고, 적지 못해도 이번 실행 동안은 읽힌다", () => {
  const broken = newStore({ [LS + "draft"]: "[1]", [LS + "talk"]: "null", [LS + "sync"]: '"x"' }).S;
  assert.deepEqual(F.plain([broken.draft("td.next"), broken.talk("today"), broken.syncState()]), ["", null, { at: null, err: null, repo: null, bad: 0 }]);
  const S = storeOn(deaf());
  const a = { d: "2026-10-13", at: F.T0, end: null };
  assert.deepEqual([F.plain(S.setDraft("td.next", "개념")), S.draft("td.next"), F.plain(S.setTalk("today", a)), F.plain(S.talk("today"))], [{ ok: false }, "개념", { ok: false }, a]);
  assert.deepEqual(F.plain([S.setSyncState({ bad: 2 }), S.syncState().bad, S.clearDrafts(["td.next"]), S.draft("td.next"), S.ok()]), [{ ok: false }, 2, { ok: false }, "", false]);
});

test("store 오래 두기: 없으면 null, 되면 true, 안 되면 false — 거절하지 않고 한 번만 청한다", async () => {
  const ask = persist => storeOn(F.fakeStorage(), { persist }).persist();
  assert.deepEqual([await ask("none"), await ask(true), await ask(false), await ask("deny")], [null, true, false, false]);
  let calls = 0;
  const counted = storeOn(F.fakeStorage(), { extra: { navigator: { storage: { persist: () => { calls += 1; return Promise.resolve(true); } } } } });
  assert.deepEqual([await counted.persist(), await counted.persist(), calls], [true, true, 1]);
  const broken = storeOn(F.fakeStorage(), { extra: { navigator: { storage: { persist: () => { throw new Error("x"); } } } } });
  assert.deepEqual([await broken.persist(), await storeOn(F.fakeStorage(), { extra: { navigator: {} } }).persist()], [false, null]);
});

test("store: 약속된 이름이 모두 있고 그 밖의 것은 없다", () => {
  const want = ["MAX_COPY_BYTES", "ok", "getDevice", "setDevice", "getFlag", "setFlag", "getConn", "setOwner", "setRepo", "setKey", "clearKey", "hasKey", "readKey", "setAuth",
    "appendLine", "monthLines", "months", "copies", "queue", "dequeue", "absorb", "resetMonths", "draft", "setDraft", "clearDrafts", "talk", "setTalk", "syncState", "setSyncState", "persist"];
  assert.deepEqual([want.length, Object.keys(newStore().S).sort()], [30, [...want].sort()]);
});
