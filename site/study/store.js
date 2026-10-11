// 공부 화면의 기기 저장 — 이 기기의 저장 공간과 '오래 두기' 요청을 만지는 유일한 파일.
// 저장 이름은 접두어 상수 P로만 만든다. 저장 공간을 훑지 않는다(이름을 아는 것만 읽는다).
// 쓰기는 매번 저장 공간에서 다시 읽어 덧붙인다(탭 둘이 서로 덮지 않게).
// 쓰지 못한 것은 메모리 대역에 두어 이번 실행 동안은 그대로 돌고, ok()가 거짓이 된다.
// 약속된 함수는 예외를 밖으로 던지지 않는다. 열쇠 값은 readKey()로만 나간다(부르는 곳은 맞춤 파일 하나).
window.StudyStore = (() => {
  "use strict";

  const P = "macro-study.";
  const VER = "1";

  let failed = false;            // 이번 실행에서 쓰기가 한 번이라도 예외를 냈다
  let stamped = false;           // 판 번호를 적었다
  let over = new Map();          // 메모리 대역 ①: 적지 못한 값(이름 → 글자, 지운 것은 null)

  const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const without = (map, name) => [...map].filter(pair => pair[0] !== name);

  // ── 저장 공간에 닿는 손 셋 ── 읽기 · 쓰기 · 지우기. 어느 것도 던지지 않는다.
  function raw(name) {
    try {
      const v = localStorage.getItem(P + name);
      return typeof v === "string" ? v : null;
    } catch (err) {
      return null;
    }
  }
  function put(name, value) {
    try {
      if (!stamped && localStorage.getItem(P + "ver") === null) localStorage.setItem(P + "ver", VER);
      stamped = true;
      localStorage.setItem(P + name, value);
    } catch (err) {
      failed = true;
      return false;
    }
    return true;
  }
  function drop(name) {
    try {
      localStorage.removeItem(P + name);
    } catch (err) {
      failed = true;
      return false;
    }
    return true;
  }
  function ok() {
    return !failed;
  }

  // ── 값 하나짜리 칸 ── 적지 못한 값은 메모리 대역에 두고, 읽을 때는 그것이 먼저다. value가 null이면 지운다.
  function read(name) {
    return over.has(name) ? over.get(name) : raw(name);
  }
  function save(name, value) {
    const done = value === null ? drop(name) : put(name, value);
    over = new Map(without(over, name).concat(done ? [] : [[name, value]]));
    return { ok: done };
  }
  function text(name) {
    const v = read(name);
    return v === null ? "" : v;
  }

  // ── 기기 이름 · 켜고 끄기 ──
  const FLAGS = Object.freeze({ rec: "1", pause: "0" });          // 이름 → 기본값
  function getDevice() {
    const name = read("dev");
    return StudyCore.devOk(name) ? name : "";
  }
  // 꼴이 틀리면 "dev", 적지 못했으면 "store"(이름은 메모리 대역에 있어 이번 실행 동안은 쓴다)
  function setDevice(name) {
    if (!StudyCore.devOk(name)) return { ok: false, code: "dev" };
    return save("dev", name).ok ? { ok: true, code: null } : { ok: false, code: "store" };
  }
  function getFlag(name) {
    if (!has(FLAGS, name)) return false;
    const v = read(name);
    return (v === "1" || v === "0" ? v : FLAGS[name]) === "1";
  }
  function setFlag(name, on) {
    return has(FLAGS, name) ? save(name, on ? "1" : "0") : { ok: false };
  }

  // ── 연결과 열쇠 ── 열쇠는 꼴이 맞는 것만 적고, 꼴이 맞는 것만 내준다. 값은 readKey()로만 나간다.
  function keyText() {
    const v = read("key");
    return StudyCore.keyShape(v) ? v : "";
  }
  function getConn() {
    return { owner: text("owner"), repo: text("repo"), hasKey: keyText() !== "", auth: read("auth") === "401" ? "401" : "ok" };
  }
  function setOwner(s) {
    return typeof s === "string" ? save("owner", s) : { ok: false };
  }
  function setRepo(s) {
    return typeof s === "string" ? save("repo", s) : { ok: false };
  }
  function setKey(s) {
    if (!StudyCore.keyShape(s)) return { ok: false };
    const key = save("key", s);
    const auth = save("auth", "ok");
    return { ok: key.ok && auth.ok };
  }
  function clearKey() {
    const key = save("key", null);
    const auth = save("auth", "ok");
    return { ok: key.ok && auth.ok };
  }
  function hasKey() {
    return keyText() !== "";
  }
  function readKey() {
    return keyText();
  }
  function setAuth(v) {
    return v === "ok" || v === "401" ? save("auth", v) : { ok: false };
  }

  // ── 줄 목록 ── 달 사본("m.<달>": 줄을 "\n"으로 이은 글) · 달 목록("months") · 대기 줄("q"). 뒤의 둘은 JSON 배열이다.
  const MONTH_RE = /^\d{4}-(0[1-9]|1[0-2])$/;
  let band = new Map();          // 메모리 대역 ②: 적지 못한 줄(이름 → 줄 배열)

  const uniq = list => [...new Set(list)];
  const monthOk = month => typeof month === "string" && MONTH_RE.test(month);
  const lineOk = line => typeof line === "string" && line !== "" && !/[\r\n]/.test(line);
  function decode(name, value) {
    if (value === null) return [];
    if (name.startsWith("m.")) return StudyCore.splitLines(value);
    try {
      const list = JSON.parse(value);
      return Array.isArray(list) ? list.filter(x => typeof x === "string") : [];
    } catch (err) {
      return [];
    }
  }
  function encode(name, list) {
    return name.startsWith("m.") ? list.join("\n") : JSON.stringify(list);
  }
  function stored(name) {
    return uniq(decode(name, raw(name)));
  }
  function items(name) {
    return uniq([...stored(name), ...(band.get(name) || [])]);
  }
  function hold(name, list) {
    band = new Map(without(band, name).concat(list.length > 0 ? [[name, list]] : []));
  }
  // 목록에 더한다: 저장 공간에서 다시 읽어 덧붙이고(앞서 적지 못한 것도 함께), 또 적지 못하면 메모리 대역에 둔다.
  function add(name, more) {
    const old = stored(name);
    const seen = new Set(old);
    const want = uniq([...(band.get(name) || []), ...more]).filter(x => !seen.has(x));
    const done = want.length === 0 || put(name, encode(name, [...old, ...want]));
    hold(name, done ? [] : want);
    return done;
  }
  // 달 사본 → 달 목록 → 대기 줄 순으로 적는다. 하나라도 적지 못하면 ok가 거짓이고, 그 줄은 메모리 대역에 남는다.
  function appendLine(month, line) {
    if (!monthOk(month) || !lineOk(line)) return { ok: false };
    const done = [add("m." + month, [line]), add("months", [month]), add("q", [line])].every(Boolean);
    if (done) [...band.keys()].forEach(name => add(name, []));               // 자리가 났다 — 앞서 적지 못한 다른 줄도 적는다
    return { ok: done };
  }
  function monthLines(month) {
    return monthOk(month) ? items("m." + month) : [];
  }
  function months() {
    return items("months").filter(monthOk).sort();
  }
  function copies() {
    return months().map(month => ({ month, lines: monthLines(month) }));
  }
  function queue() {
    return items("q");
  }
  // 글자가 같은 줄만 뺀다
  function dequeue(lines) {
    const gone = new Set(Array.isArray(lines) ? lines : []);
    const old = stored("q");
    const keep = old.filter(x => !gone.has(x));
    hold("q", (band.get("q") || []).filter(x => !gone.has(x)));
    return { ok: keep.length === old.length || put("q", encode("q", keep)) };
  }

  // ── 받은 줄 · 사본 비우기 ──
  const MAX_COPY_BYTES = 300 * 1024;
  // 받은 줄 가운데 없는 것만 달 사본에 더한다(대기 줄에는 넣지 않는다). 더한 뒤가 MAX_COPY_BYTES를 넘으면 하나도 더하지 않는다.
  function absorb(month, lines) {
    if (!monthOk(month) || !Array.isArray(lines)) return { ok: false, added: 0, code: "store" };
    const name = "m." + month;
    const seen = new Set(items(name));
    const fresh = uniq(lines.filter(lineOk)).filter(x => !seen.has(x));
    if (fresh.length === 0) return { ok: true, added: 0, code: null };
    const next = encode(name, [...stored(name), ...fresh]);
    if (new TextEncoder().encode(next).length > MAX_COPY_BYTES) return { ok: false, added: 0, code: "big" };
    if (!put(name, next)) return { ok: false, added: 0, code: "store" };
    add("months", [month]);
    return { ok: true, added: fresh.length, code: null };
  }
  // 달 사본과 달 목록을 비운다. 대기 줄은 남긴다.
  function resetMonths() {
    const dropped = months().map(month => drop("m." + month)).every(Boolean);
    const listed = drop("months");
    band = new Map([...band].filter(pair => pair[0] === "q"));
    return { ok: dropped && listed };
  }

  // ── 쓰던 글 ── 칸 이름은 아래 목록뿐이다(열쇠 칸 · 연결 칸은 없다). 너무 길거나 영숫자가 길게 이어진 글은 두지 않는다.
  const DRAFTS = Object.freeze(["td.stuck", "td.nostuck", "td.next", "wk.dur", "wk.cur", "wk.why", "wk.wrong",
    "gr.actual", "gr.dur", "gr.cur", "gr.miss", "ask.text", "ask.s"]);
  const MAX_DRAFT = 1000;
  const LONG_RE = /[A-Za-z0-9_]{40}/;
  function readObj(name) {
    try {
      const v = JSON.parse(read(name));
      return v !== null && typeof v === "object" && !Array.isArray(v) ? v : {};
    } catch (err) {
      return {};
    }
  }
  function drafts() {
    const o = readObj("draft");
    return DRAFTS.filter(slot => typeof o[slot] === "string" && o[slot] !== "").map(slot => [slot, o[slot]]);
  }
  function draft(slot) {
    const found = drafts().find(pair => pair[0] === slot);
    return found ? found[1] : "";
  }
  function setDraft(slot, value) {
    if (!DRAFTS.includes(slot) || typeof value !== "string") return { ok: false };
    const keep = value.length <= MAX_DRAFT && !LONG_RE.test(value);
    const rest = drafts().filter(pair => pair[0] !== slot);
    const saved = save("draft", JSON.stringify(Object.fromEntries(keep && value !== "" ? [...rest, [slot, value]] : rest)));
    return { ok: saved.ok && keep };
  }
  function clearDrafts(slots) {
    const gone = Array.isArray(slots) ? slots : [];
    return save("draft", JSON.stringify(Object.fromEntries(drafts().filter(pair => !gone.includes(pair[0])))));
  }

  // ── 시계 상태 ── 화면("today" · "ask")마다 { d, at, end }. 꼴이 맞지 않는 값은 없는 것으로 친다.
  const SLOTS = Object.freeze(["today", "ask"]);
  function talkOk(v) {
    return v !== null && typeof v === "object" && StudyCore.isDate(v.d) && Number.isFinite(v.at) && (v.end === null || Number.isFinite(v.end));
  }
  function talk(slot) {
    const v = SLOTS.includes(slot) ? readObj("talk")[slot] : null;
    return talkOk(v) ? { d: v.d, at: v.at, end: v.end } : null;
  }
  function setTalk(slot, value) {
    if (!SLOTS.includes(slot) || (value !== null && !talkOk(value))) return { ok: false };
    const rest = SLOTS.filter(s => s !== slot && talk(s) !== null).map(s => [s, talk(s)]);
    const mine = value === null ? [] : [[slot, { d: value.d, at: value.at, end: value.end }]];
    return save("talk", JSON.stringify(Object.fromEntries([...rest, ...mine])));
  }

  // ── 맞춤 상태 ── { at, err, repo, bad }. 꼴이 맞지 않는 칸은 기본값으로 읽는다.
  const SYNC_KEYS = Object.freeze(["at", "err", "repo", "bad"]);
  const REPO_STATES = Object.freeze(["ok", "missing", "public"]);
  function errOk(v) {
    return v !== null && typeof v === "object" && Number.isInteger(v.code) && typeof v.key === "string" && /^ERR_[A-Z]+$/.test(v.key);
  }
  function repoStateOk(v) {
    return v !== null && typeof v === "object" && StudyCore.isDate(v.d) && REPO_STATES.includes(v.state);
  }
  function syncState() {
    const o = readObj("sync");
    return {
      at: Number.isFinite(o.at) ? o.at : null,
      err: errOk(o.err) ? { code: o.err.code, key: o.err.key } : null,
      repo: repoStateOk(o.repo) ? { d: o.repo.d, state: o.repo.state } : null,
      bad: Number.isInteger(o.bad) && o.bad >= 0 ? o.bad : 0,
    };
  }
  function setSyncState(patch) {
    const p = patch !== null && typeof patch === "object" ? patch : {};
    const changed = SYNC_KEYS.filter(k => has(p, k)).map(k => [k, p[k]]);
    return save("sync", JSON.stringify({ ...syncState(), ...Object.fromEntries(changed) }));
  }

  // ── 오래 두기 ── 한 번만 청한다. 없으면 null, 거절 · 오류면 false. 거절하는 약속을 돌려주지 않는다.
  let asked = null;
  function askPersist() {
    try {
      const storage = navigator.storage;
      if (!storage || typeof storage.persist !== "function") return Promise.resolve(null);
      return Promise.resolve(storage.persist()).then(v => v === true, () => false);
    } catch (err) {
      return Promise.resolve(false);
    }
  }
  function persist() {
    asked = asked === null ? askPersist() : asked;
    return asked;
  }

  return {
    MAX_COPY_BYTES, ok,
    getDevice, setDevice, getFlag, setFlag,
    getConn, setOwner, setRepo, setKey, clearKey, hasKey, readKey, setAuth,
    appendLine, monthLines, months, copies, queue, dequeue, absorb, resetMonths,
    draft, setDraft, clearDrafts, talk, setTalk, syncState, setSyncState, persist,
  };
})();
