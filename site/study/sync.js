// 공부 화면의 맞춤 — 이 기기의 줄과 기록 저장소의 달 파일을 같게 한다. 통신을 부르고 열쇠를 꺼내는 유일한 파일.
// 차례는 받기 → 합치기 → 흡수 → 올리기다. 받은 줄은 다시 만들지 않고 글자 그대로 다루며, 올리는 조건은 '기기에만 있는 줄이 있을 때' 하나다.
// 응답의 문구에는 기대지 않는다(상태 코드와 표 RESPONSES만 본다). 약속된 함수는 던지지 않고, 돌려주는 약속은 거절하지 않는다.
window.StudySync = (() => {
  "use strict";

  const API = "https://api.github.com/repos/";
  const API_VERSION = "2026-03-10";
  const TIMEOUT_MS = 15000;      // 요청 하나의 제한
  const THROTTLE_MS = 10000;     // 자동 맞춤은 이 창에 한 번
  const RETRY_MS = 1100;         // 겹친 뒤 다시 받기 전에 쉬는 시간
  const MAX_TRIES = 3;           // 한 달에서 올리기를 해 보는 횟수
  const SHA_TTL_MS = 60000;      // 방금 올린 달의 sha를 믿는 시간
  const MAX_FILE_BYTES = 614400; // 600 × 1024 — 이보다 큰 달 파일은 덮어쓰지 않는다
  const MONTH_RE = /^\d{4}-(0[1-9]|1[0-2])$/;

  const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const isObj = v => v !== null && typeof v === "object";

  // ── 요청의 꼴 ── 주소는 한 꼴뿐이다. 이름 · 달 · 열쇠가 꼴에 어긋나면 null(요청 0번). 열쇠는 인증 머리 한 줄에만 들어간다.
  // 올리기의 본문: message · content, 그리고 있을 때만 sha. 그 밖의 칸(커밋에 남길 이름 등)은 보내지 않는다.
  function putBody(body) {
    const b = isObj(body) ? body : {};
    const sha = typeof b.sha === "string" && b.sha !== "" ? { sha: b.sha } : {};
    return JSON.stringify({ message: String(b.message), content: String(b.content), ...sha });
  }
  function buildRequest(kind, cfg, extra) {
    const c = isObj(cfg) ? cfg : {};
    const x = isObj(extra) ? extra : {};
    const file = kind === "get" || kind === "put";
    if (!StudyCore.ownerOk(c.owner) || !StudyCore.repoOk(c.repo) || !StudyCore.keyShape(c.key)) return null;
    if (!(kind === "repo" || file) || (file && !(typeof x.month === "string" && MONTH_RE.test(x.month)))) return null;
    const put = kind === "put";
    const headers = { Accept: "application/vnd.github+json", Authorization: "Bearer " + c.key, "X-GitHub-Api-Version": API_VERSION,
      ...(put ? { "Content-Type": "application/json" } : {}) };
    const init = { method: put ? "PUT" : "GET", headers, cache: "no-store", credentials: "omit", referrerPolicy: "no-referrer",
      redirect: "error", signal: x.signal, ...(put ? { body: putBody(x.body) } : {}) };
    return { url: API + c.owner + "/" + c.repo + (file ? "/contents/log/" + x.month + ".jsonl" : ""), init };
  }

  // ── 응답 처리 표 ── 요청의 종류 → 상태 코드 → 처리 이름. c4는 표에 없는 4xx, c5는 5xx, 0은 통신 오류 · 시간 초과 · 끊음.
  const RESPONSES = Object.freeze({
    repo: Object.freeze({ 200: "check", 401: "auth", 404: "missing", c4: "halt", c5: "later", 0: "later" }),
    get: Object.freeze({ 200: "merge", 401: "auth", 404: "empty", c4: "halt", c5: "later", 0: "later" }),
    put: Object.freeze({ 200: "done", 201: "done", 401: "auth", 404: "missing", 409: "retry", 422: "retry", c4: "halt", c5: "later", 0: "later" }),
  });
  function classify(kind, status) {
    if (!has(RESPONSES, kind) || !Number.isInteger(status)) return "later";
    const table = RESPONSES[kind];
    if (has(table, status)) return table[status];
    if (status >= 400 && status <= 499) return table.c4;
    return status >= 500 && status <= 599 ? table.c5 : "later";
  }

  // ── 글자 ↔ base64 ── 올릴 때는 UTF-8 바이트를 하나씩 이어 붙여 싼다(배열을 펼치지 않는다). 받을 때는 공백 · 줄바꿈을 지우고 푼다.
  function toB64(text) {
    return btoa(Array.from(new TextEncoder().encode(String(text)), b => String.fromCharCode(b)).join(""));
  }
  // 풀리지 않으면 null
  function fromB64(b64) {
    try {
      const bin = atob(typeof b64 === "string" ? b64.replace(/\s+/g, "") : "!");
      return new TextDecoder().decode(Uint8Array.from(bin, ch => ch.charCodeAt(0)));
    } catch (err) {
      return null;
    }
  }
  // 올리기의 커밋 메시지: 달과 건수뿐
  function commitMsg(month, n) {
    return "log: " + month + " +" + n;
  }

  // ── 맞춤의 상태 ── 모두 메모리에만 있다(다시 열면 처음부터). 기기에 남는 것은 StudyStore의 맞춤 상태와 열쇠 거절 표시다.
  let onChange = null;           // 틀이 준 알림 함수
  let phase = "idle";            // "idle" · "wait"(창이 끝나기를 기다린다) · "run"
  let held = null;               // 메모리의 멈춤: "halt" · "file" · null
  let code = null;               // "halt"를 부른 상태 코드
  let failedThisOpen = false;    // 이번에 화면을 열거나 돌아온 뒤의 맞춤이 실패했다
  let turn = 0;                  // 판 번호. 끊을 때마다 올린다 — 옛 판의 응답은 버린다
  let live = new Set();          // 지금 나가 있는 요청을 끊는 손
  let memo = new Map();          // 달 → { sha, at, lines }: 방금 올린 달
  let lastAuto = null;           // 마지막 자동 시작의 시각
  let waiting = null;            // 창이 끝나기를 기다리는 때맞춤
  let again = null;              // 도는 중에 온 요청: "auto" · "now"

  const today = () => StudyCore.studyDate(Date.now());

  // ── 문지기 ── 하나라도 걸리면 요청 0번이다. 돌려주는 값이 곧 snapshot의 stop이다(걸리지 않으면 null).
  // 연결 설정(앞뒤 공백은 뗀다). 열쇠 값은 여기 없다 — 꺼내는 곳은 config() 하나다.
  function link() {
    const c = StudyStore.getConn();
    return { owner: c.owner.trim(), repo: c.repo.trim(), hasKey: c.hasKey, auth: c.auth };
  }
  function gate() {
    const c = link();
    if (!c.hasKey || !StudyCore.ownerOk(c.owner) || !StudyCore.repoOk(c.repo)) return "off";
    if (c.auth === "401") return "auth";
    if (StudyStore.getFlag("pause")) return "paused";
    const repo = StudyStore.syncState().repo;
    if (repo !== null && repo.d === today() && repo.state !== "ok") return repo.state;
    return held;
  }
  function config() {
    const c = link();
    return { owner: c.owner, repo: c.repo, key: StudyStore.readKey() };
  }
  function snapshot() {
    return { phase, stop: gate(), code: held === "halt" ? code : null, failedThisOpen };
  }
  function init(fn) {
    onChange = typeof fn === "function" ? fn : null;
  }
  // 틀에 알린다(맞춤 하나가 끝났을 때 · 멈춤이 바뀌었을 때). 알림을 받는 쪽이 던져도 맞춤은 계속 돈다.
  function tell(info) {
    try {
      if (onChange !== null) onChange(snapshot(), { changed: false, big: false, ...info });
    } catch (err) {
      return;
    }
  }

  // ── 요청 하나 ── 15초 제한. 판 번호가 바뀐 뒤(끊긴 뒤)에 온 응답은 버린다("gone").
  const GONE = Object.freeze({ act: "gone", status: 0, data: null, late: false });
  async function ask(req) {
    try {
      const res = await fetch(req.url, req.init);
      const data = await res.json().then(v => v, () => null);
      return { status: res.status, data };
    } catch (err) {
      return { status: 0, data: null };
    }
  }
  // → { act, status, data, late }. act는 표의 처리 이름, late는 15초 제한에 걸렸다는 표시다.
  async function send(kind, cfg, extra, mine) {
    const ctl = new AbortController();
    const req = buildRequest(kind, cfg, { ...extra, signal: ctl.signal });
    if (req === null || mine !== turn) return GONE;
    let late = false;
    const clock = setTimeout(() => { late = true; ctl.abort(); }, TIMEOUT_MS);
    live = new Set([...live, ctl]);
    const got = await ask(req);
    clearTimeout(clock);
    live = new Set([...live].filter(one => one !== ctl));
    if (mine !== turn) return GONE;
    const status = late || !Number.isInteger(got.status) ? 0 : got.status;
    return { act: classify(kind, status), status, data: late ? null : got.data, late };
  }

  // ── 멈추거나 미루는 처리 ── 처리 이름마다 기기에 남길 것과 메모리의 멈춤.
  // err의 code는 상태 코드다(상태 코드가 까닭이 아닌 통신 · 시간 초과 · 공개 상태 · 파일 · 사본이 큼은 0).
  const ERR = Object.freeze({ auth: "ERR_AUTH", missing: "ERR_MISSING", public: "ERR_PUBLIC", halt: "ERR_HALT", retry: "ERR_RACE",
    file: "ERR_FILE", big: "ERR_BIG" });
  const BY_STATUS = Object.freeze(["auth", "missing", "halt", "retry"]);
  function errOf(r) {
    if (r.act === "later") return { code: r.status, key: r.status !== 0 ? "ERR_SERVER" : r.late ? "ERR_TIMEOUT" : "ERR_NET" };
    return { code: BY_STATUS.includes(r.act) ? r.status : 0, key: ERR[r.act] };
  }
  function settle(r, day) {
    if (r.act === "auth") StudyStore.setAuth("401");
    if (r.act === "halt" || r.act === "file") held = r.act;
    if (r.act === "halt") code = r.status;
    const repo = r.act === "missing" || r.act === "public" ? { repo: { d: day, state: r.act } } : {};
    StudyStore.setSyncState({ err: errOf(r), ...repo });
  }

  // ── 저장소 확인 ── 200이고 비공개이며 Pages가 꺼져 있을 때만 지난다("pass"). 아니면 "public".
  function judge(r) {
    if (r.act !== "check") return r;
    return { ...r, act: isObj(r.data) && r.data.private === true && r.data.has_pages === false ? "pass" : "public" };
  }

  // ── [연결 확인] ── 저장소 정보 읽기 1번. 자동 맞춤을 멈췄어도 돈다. 설정이 비었거나 열쇠가 거절된 뒤면 요청 0번.
  const CONN = Object.freeze({ pass: "CONN_OK", public: "CONN_PUBLIC", missing: "CONN_MISSING", auth: "CONN_AUTH", file: "ST_FILE" });
  function connKey(r) {
    if (has(CONN, r.act)) return CONN[r.act];
    return r.status === 0 ? "CONN_NET" : "CONN_ERR";
  }
  async function check() {
    const stop = gate();
    if (stop === "off") return { key: "CONN_UNSET", code: null };
    if (stop === "auth") return { key: "CONN_AUTH", code: null };
    const day = today();
    const r = judge(await send("repo", config(), {}, turn));
    if (r.act === "gone") return { key: "CONN_NET", code: null };
    if (r.act === "pass") StudyStore.setSyncState({ repo: { d: day, state: "ok" } });
    else settle(r, day);
    held = r.act === "pass" && held === "halt" ? null : held;
    tell({});
    return { key: connKey(r), code: r.status };
  }
  function checkConn() {
    return check().then(r => r, () => ({ key: "CONN_NET", code: null }));
  }

  // ── 달 하나 ── 받기 → 합치기 → 흡수 → 올리기
  const nap = ms => new Promise(resolve => setTimeout(resolve, ms));
  const forget = month => new Map([...memo].filter(pair => pair[0] !== month));
  // 올리기 응답의 sha와 그때 올린 줄을 기억한 새 표(sha가 없으면 그 달을 잊는다)
  function remember(month, data, lines) {
    const sha = isObj(data) && isObj(data.content) && typeof data.content.sha === "string" ? data.content.sha : null;
    return new Map([...forget(month), ...(sha === null ? [] : [[month, { sha, at: Date.now(), lines }]])]);
  }
  // 이 기기의 그 달 줄: 달 사본과, 대기 줄 가운데 그 달의 것
  function localLines(month) {
    return [...new Set([...StudyStore.monthLines(month), ...StudyStore.queue().filter(text => StudyCore.lineMonth(text) === month)])];
  }
  // 받은 파일의 글. 600KB를 넘거나 base64가 아니거나 sha가 없으면 null(풀리지 않아도 null) — 그런 파일은 덮어쓰지 않는다.
  function readFile(data) {
    const d = isObj(data) ? data : {};
    const fine = d.size <= MAX_FILE_BYTES && d.encoding === "base64" && typeof d.content === "string" && typeof d.sha === "string";
    return fine ? fromB64(d.content) : null;
  }
  // 받기 → { act: "merge", lines, sha }. 없는 파일(404)은 빈 줄 · sha 없음이다.
  // 방금 올린 달(60초 안)이고 올릴 것이 있으면 받지 않고 그때 올린 줄과 sha를 쓴다. 받으러 가면 그 기억은 버린다(받은 것이 더 새롭다).
  async function pullMonth(cfg, month, mine) {
    const kept = memo.get(month);
    const seen = new Set(kept ? kept.lines : []);
    const usable = kept !== undefined && Date.now() - kept.at < SHA_TTL_MS && localLines(month).some(text => !seen.has(text));
    if (usable) return { ...GONE, act: "merge", lines: kept.lines, sha: kept.sha };
    memo = forget(month);
    const r = await send("get", cfg, { month }, mine);
    if (r.act === "empty") return { ...r, act: "merge", lines: [], sha: null };
    if (r.act !== "merge") return r;
    const text = readFile(r.data);
    return text === null ? { ...r, act: "file" } : { ...r, lines: StudyCore.splitLines(text), sha: r.data.sha };
  }
  // 흡수: 받은 줄 가운데 꼴이 맞는 것만 기기 사본에 더한다. 맞지 않는 줄은 수만 센다(올릴 때는 받은 글자 그대로 실린다).
  function take(month, added) {
    const good = added.filter(text => StudyCore.checkLine(text, month).ok);
    const got = good.length > 0 ? StudyStore.absorb(month, good) : { added: 0, code: null };
    return { bad: added.length - good.length, added: got.added, big: got.code === "big" };
  }
  // 올리기. 끝나면 파일에 실린 줄을 대기 줄에서 빼고 응답의 sha를 기억한다. 끝나지 못했으면 그 달의 기억을 버린다.
  async function pushMonth(cfg, month, m, sha, mine) {
    const body = { message: commitMsg(month, m.toUpload.length), content: toB64(StudyCore.joinLines(m.lines)), sha };
    const r = await send("put", cfg, { month, body }, mine);
    if (r.act === "done") StudyStore.dequeue(m.lines);
    memo = r.act === "done" ? remember(month, r.data, m.lines) : forget(month);
    return r;
  }
  // 달 하나를 한 번 맞춘다 → { r, bad, added, big }. r이 null이면 그 달은 끝났고, 아니면 맞춤을 끝낼 까닭이다("retry"는 겹침).
  // 사본이 너무 커서 흡수하지 못한 달(big)은 올리지도 않고 넘어간다. 올릴 것이 없으면 이미 올라가 있는 줄을 대기 줄에서 뺀다.
  async function tryMonth(cfg, month, mine) {
    const got = await pullMonth(cfg, month, mine);
    if (got.act !== "merge") return { r: got, bad: 0, added: 0, big: false };
    const m = StudyCore.mergeLines(localLines(month), got.lines, month);
    const took = take(month, m.added);
    if (took.big) return { r: null, ...took };
    const put = m.toUpload.length > 0 ? await pushMonth(cfg, month, m, got.sha, mine) : null;
    if (put === null) StudyStore.dequeue(m.lines);
    return { r: put === null || put.act === "done" ? null : put, ...took };
  }
  // 겹치면(409 · 422) 쉬었다가 다시 받아 합쳐 올린다. MAX_TRIES번째에도 겹치면 그만두고 대기 줄을 둔다.
  async function syncMonth(cfg, month, mine) {
    let one = await tryMonth(cfg, month, mine);
    for (let n = 1; n < MAX_TRIES && one.r !== null && one.r.act === "retry"; n += 1) {
      await nap(RETRY_MS);
      one = await tryMonth(cfg, month, mine).then(more => ({ ...more, added: one.added + more.added }));   // 앞 시도에서 흡수한 줄도 센다
    }
    return one;
  }

  // ── 맞춤 한 번 ── 저장소 확인 → 달마다 차례로 → 모두 끝나면 맞춘 시각을 적는다. 돌려주는 값은 틀에 알릴 것이다(끊긴 판은 null).
  // 저장소 확인은 공부 날짜마다 한 번만 묻는다(그날 이미 지났으면 요청 없이 지난다)
  async function ensureRepo(cfg, day, mine) {
    const known = StudyStore.syncState().repo;
    if (known !== null && known.d === day && known.state === "ok") return { ...GONE, act: "pass" };
    const r = judge(await send("repo", cfg, {}, mine));
    if (r.act === "pass") StudyStore.setSyncState({ repo: { d: day, state: "ok" } });
    return r;
  }
  function failed(r, day, sum) {
    if (r.act === "gone") return null;
    settle(r, day);
    failedThisOpen = true;
    return { changed: sum.changed, big: sum.big };
  }
  async function runOnce(mine) {
    const day = today();
    const cfg = config();
    const repo = await ensureRepo(cfg, day, mine);
    if (repo.act !== "pass") return failed(repo, day, { changed: false, big: false });
    let sum = { bad: 0, changed: false, big: false };
    for (const month of StudyCore.monthsToFetch(day, StudyStore.queue())) {
      const one = await syncMonth(cfg, month, mine);
      sum = { bad: sum.bad + one.bad, changed: sum.changed || one.added > 0, big: sum.big || one.big };
      if (one.r !== null) return failed(one.r, day, sum);
    }
    StudyStore.setSyncState({ at: Date.now(), err: sum.big ? { code: 0, key: ERR.big } : null, bad: sum.bad });
    return { changed: sum.changed, big: sum.big };
  }

  // ── 때 ── 한 번에 하나만 돈다. 자동(열기 · 돌아옴 · 저장)은 10초에 한 번이고, 손으로 누른 것과 저장 실패는 기다리지 않는다.
  const AUTO = Object.freeze(["open", "back", "save"]);
  const NOW = Object.freeze(["manual", "store-fail"]);
  // 나가 있는 요청을 끊고 판을 넘긴다 — 옛 판은 더 보내지도 적지도 않는다
  function cut() {
    turn += 1;
    for (const ctl of live) ctl.abort();
    live = new Set();
    phase = phase === "run" ? "idle" : phase;
    again = null;
  }
  function start(auto) {
    clearTimeout(waiting);
    waiting = null;
    phase = "run";
    lastAuto = auto ? Date.now() : lastAuto;
    const mine = turn;
    runOnce(mine).then(info => finish(mine, info), () => finish(mine, null));
  }
  function finish(mine, info) {
    if (mine !== turn) return;                                      // 끊긴 판 — 끊은 쪽이 다음을 정했다
    const next = again;
    phase = "idle";
    again = null;
    tell(info === null ? {} : info);
    if (next !== null && phase === "idle" && gate() === null) plan(next === "auto");
  }
  function wake() {
    waiting = null;
    phase = "idle";
    if (gate() === null) start(true);
  }
  // 문지기를 지난 요청을 언제 돌릴지: 도는 중이면 끝난 뒤 한 번, 자동이고 창 안이면 창이 끝날 때 한 번, 아니면 지금
  function plan(auto) {
    if (phase === "run") {
      again = auto && again !== "now" ? "auto" : "now";
      return;
    }
    const left = auto && lastAuto !== null ? lastAuto + THROTTLE_MS - Date.now() : 0;
    if (left <= 0) {
      start(auto);
      return;
    }
    if (phase === "wait") return;
    phase = "wait";
    waiting = setTimeout(() => wake(), left);
  }
  // 돌아왔을 때("back")는 멈춰 있던 요청을 먼저 끊는다 — 끊긴 요청의 결과는 버리고, 같은 올리기를 겹쳐 보내지 않는다.
  // 열거나 돌아오면 '이번에 연 뒤의 실패'를 처음부터 다시 센다(바뀌었으면 알린다).
  function request(reason) {
    const auto = AUTO.includes(reason);
    if (!auto && !NOW.includes(reason)) return;
    const cleared = failedThisOpen && (reason === "open" || reason === "back");
    failedThisOpen = cleared ? false : failedThisOpen;
    if (reason === "back" && phase === "run") cut();
    if (gate() === null) plan(auto);
    if (cleared) tell({});
  }

  // ── [사본 비우고 다시 받기] ── 자동 맞춤을 멈췄을 때만. 달 사본을 비우고 받기만 한다(올리지 않는다). 대기 줄은 남는다.
  // 대기 줄은 사본에 되돌려 둔다 — 올리지 못한 줄이 화면에서 사라지지 않게
  function restore(queue) {
    for (const text of queue) {
      const month = StudyCore.lineMonth(text);
      if (month !== null) StudyStore.absorb(month, [text]);
    }
  }
  function pullStopped(got, day, big) {
    if (got.act === "gone") return { ok: false, key: "CONN_NET", code: null };
    settle(got, day);
    tell({ changed: true, big });
    return { ok: false, key: connKey(got), code: got.status };
  }
  async function pull() {
    if (!StudyStore.getFlag("pause")) return { ok: false, key: "SET_REPULL_NOTE", code: null };
    const stop = gate();
    if (stop === "off" || stop === "auth") return { ok: false, key: stop === "off" ? "CONN_UNSET" : "CONN_AUTH", code: null };
    cut();
    const mine = turn;
    const day = today();
    const cfg = config();
    const queue = StudyStore.queue();
    StudyStore.resetMonths();
    memo = new Map();
    restore(queue);
    let big = false;
    for (const month of StudyCore.monthsToFetch(day, queue)) {
      const got = await pullMonth(cfg, month, mine);
      if (got.act !== "merge") return pullStopped(got, day, big);
      big = take(month, got.lines).big || big;
    }
    tell({ changed: true, big });
    return big ? { ok: false, key: "NOTE_BIG", code: null } : { ok: true, key: null, code: null };
  }
  function pullOnly() {
    return pull().then(r => r, () => ({ ok: false, key: "CONN_NET", code: null }));
  }

  // ── 설정이 바뀌었을 때 ── 돌던 것을 끊고 기다리던 것을 치우고, 메모리의 멈춤 · 기억한 sha · 그날의 저장소 확인을 지운다
  function reset() {
    cut();
    clearTimeout(waiting);
    waiting = null;
    phase = "idle";
    held = null;
    code = null;
    memo = new Map();
    lastAuto = null;
    StudyStore.setSyncState({ repo: null });
    tell({});
  }

  // ── 밖에서 쓰는 이름 ── 테스트만 쓰는 것은 _ 묶음에 둔다
  return {
    init, request, checkConn, pullOnly, reset, snapshot,
    _: { API, API_VERSION, TIMEOUT_MS, THROTTLE_MS, RETRY_MS, MAX_TRIES, SHA_TTL_MS, MAX_FILE_BYTES, RESPONSES,
      buildRequest, classify, toB64, fromB64, commitMsg },
  };
})();
