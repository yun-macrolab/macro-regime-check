// 공부 화면의 녹음 — 마이크 · 녹음기 · 화면 켜 두기 · 보관(IndexedDB) · 재생 주소를 만지는 유일한 파일.
// 녹음은 '되면 얹는' 것이다: 어느 함수도 호출한 쪽을 기다리게 하지 않는다(2분 시계와 도장은 이 파일 밖에서 돈다).
// 마이크는 [말하기]를 누른 그 처리 안에서 begin()이 청한다. 2분 종료 · [그만] · 끊김 어느 경우든 마이크를 닫는다.
// 녹음은 이 기기에만 최근 7개를 둔다(올리지 않는다). 화면에는 onEvent로 알리기만 하고, 문서는 건드리지 않는다.
window.StudyRecorder = (() => {
  "use strict";

  const DB = "macro-study.takes";                                      // 보관하는 데이터베이스(이 기기의 IndexedDB)
  const STORE = "takes";                                               // 그 안의 저장소. 키는 "<공부 날짜>.<화면>"
  const KEEP = 7;                                                      // 기기에 두는 녹음의 수
  const BITS = 64000;                                                  // 청하는 비트레이트(2분 약 1MB). 지켜진다는 보장은 없다
  const TYPES = Object.freeze(["audio/mp4", "audio/webm;codecs=opus"]);   // 형식: 앞의 것부터 받는 것을 고른다
  const OVER = 5000;                                                   // 한도: 녹음기가 2분을 돌고도 이만큼(ms) 더 끝을 듣지 못하면 스스로 끊는다
  const quiet = () => {};

  // ── 녹음의 상태 ── 화면(slot)마다 마지막(또는 지금) 녹음 하나를 쥔다. 마이크를 쥔 녹음은 한 번에 하나다.
  // 녹음 하나: { n, slot, date, tell, phase, stream, rec, lock, cap, chunks, at, end, packed }
  //   phase: "wait"(허용을 기다린다) → "on"(녹음기가 돈다) → "over"(닫았다). at · end는 녹음기가 돈 처음과 끝(ms). cap은 한도의 때맞춤(없으면 null)
  let seq = 0;                   // begin을 부를 때마다 오른다 — 늦게 온 답이 어느 녹음의 것인지 가린다
  let takes = new Map();         // 화면 이름 → 그 화면의 녹음
  let liveN = 0;                 // 마이크를 쥔 녹음의 번호(없으면 0)
  let watching = false;          // 화면이 가려지는지 보고 있다(처음 녹음할 때 한 번 건다)
  let playing = null;            // 내준 재생 주소(없으면 null). 한 번에 하나만 내준다
  let asks = 0;                  // 재생 주소를 청하거나 거둘 때마다 오른다 — 그 전에 청한 것의 답은 버린다

  const find = n => [...takes.values()].find(take => take.n === n) || null;
  function patch(n, change) {
    const take = find(n);
    if (take !== null) takes = new Map([...takes, [take.slot, { ...take, ...change }]]);
  }
  // 화면에 알린다. 화면이 던져도 녹음은 제 일을 마친다
  function report(tell, ev) {
    try {
      tell(ev);
    } catch (err) {
      return;
    }
  }
  function say(n, ev) {
    const take = find(n);
    if (take !== null) report(take.tell, ev);
  }
  // 그 화면의 마지막(또는 지금) 녹음에서 녹음기가 돈 초(0~TALK_SEC). 허용을 기다린 시간은 세지 않는다. slot을 주지 않으면 가장 늦게 시작한 것
  function seconds(slot) {
    const take = slot === undefined ? find(Math.max(0, ...[...takes.values()].map(one => one.n))) : takes.get(slot);
    if (!take || take.at === null) return 0;
    const until = take.end === null ? Date.now() : take.end;
    return Math.max(0, Math.min(StudyCore.TALK_SEC, Math.floor((until - take.at) / 1000)));
  }
  function supported() {
    try {
      return typeof MediaRecorder === "function" && typeof navigator.mediaDevices.getUserMedia === "function";
    } catch (err) {
      return false;
    }
  }

  // ── 닫기 ── 녹음기를 멈추고, 마이크의 트랙을 모두 닫고, 화면 켜 두기를 놓고, 한도의 때맞춤을 거둔다. 두 번 불러도 한 번만 한다(닫았으면 참).
  function halt(rec) {
    try {
      if (rec !== null && rec.state !== "inactive") rec.stop();
    } catch (err) {
      return;
    }
  }
  function mute(stream) {
    try {
      if (stream !== null) stream.getTracks().forEach(track => track.stop());
    } catch (err) {
      return;
    }
  }
  function release(lock) {
    try {
      if (lock !== null) Promise.resolve(lock.release()).then(quiet, quiet);
    } catch (err) {
      return;
    }
  }
  function shut(n) {
    const take = find(n);
    if (take === null || take.phase === "over") return false;
    patch(n, { phase: "over", end: Date.now(), lock: null, cap: null });
    if (liveN === n) liveN = 0;
    if (take.cap !== null) clearTimeout(take.cap);
    halt(take.rec);
    mute(take.stream);
    release(take.lock);
    return true;
  }
  // 끊김: 화면이 가려졌다 · 마이크가 음소거되거나 끝났다 · 녹음기가 오류를 냈거나 스스로 멈췄다 · 다른 화면이 마이크를 가져갔다 · 한도를 넘겼다.
  // 그 자리에서 닫고 알린다(녹음기가 돌던 때만). 저절로 다시 시작하지 않는다.
  function cut(n) {
    const take = find(n);
    if (take !== null && shut(n) && take.phase === "on") say(n, { type: "cut", sec: seconds(take.slot) });
  }
  function hidden() {
    if (liveN !== 0 && document.visibilityState !== "visible") cut(liveN);
  }
  function watch() {
    if (watching) return;
    watching = true;
    document.addEventListener("visibilitychange", () => hidden());
  }

  // ── 시작 ── 화면 켜 두기와 마이크를 청하고 곧바로 돌아간다. 답은 나중에 온다(끝내 오지 않을 수도 있다).
  // 화면 켜 두기: 없거나 거절되면 한 줄로 알린다. 늦게 얻은 것은(녹음이 이미 끝났다) 곧바로 놓는다.
  function awake(n, lock) {
    const take = find(n);
    if (take === null || take.phase === "over") release(lock);
    else patch(n, { lock });
  }
  function asleep(n) {
    const take = find(n);
    if (take !== null && take.phase !== "over") say(n, { type: "nowake" });
  }
  function wake(n) {
    try {
      Promise.resolve(navigator.wakeLock.request("screen")).then(lock => awake(n, lock), () => asleep(n));
    } catch (err) {
      asleep(n);
    }
  }
  // 녹음기를 만들어 돌린다. mp4 먼저, 없으면 webm. 만들지 못하면 null
  function build(stream) {
    try {
      const type = TYPES.find(one => MediaRecorder.isTypeSupported(one));
      const rec = new MediaRecorder(stream, type === undefined ? { audioBitsPerSecond: BITS } : { mimeType: type, audioBitsPerSecond: BITS });
      rec.start();
      return rec;
    } catch (err) {
      return null;
    }
  }
  function keep(n, data) {
    const take = find(n);
    if (take !== null && data) patch(n, { chunks: [...take.chunks, data] });
  }
  function wire(n, rec, stream) {
    rec.addEventListener("dataavailable", ev => keep(n, ev.data));
    rec.addEventListener("stop", () => stopped(n));
    rec.addEventListener("error", () => cut(n));
    for (const track of stream.getTracks()) {
      track.addEventListener("mute", () => cut(n));
      track.addEventListener("ended", () => cut(n));
    }
  }
  // 허용이 왔다. 그 녹음이 이미 끝났으면(늦게 온 허용) 마이크를 곧바로 닫는다.
  // 한도: 끝(2분 · [그만])은 화면의 시계가 알린다. 그 시계가 치워져(같은 저장 공간을 쓰는 다른 창) 끝이 오지 않아도 마이크가 남지 않게,
  // 녹음기가 돈 지 2분 남짓이면 스스로 끊는다. 제때 닫히면 shut이 이 때맞춤을 거둔다(한 창에서는 시계가 녹음기보다 먼저 돌기 시작하므로 제때 온 끝이 언제나 앞선다).
  function granted(n, stream) {
    const take = find(n);
    const rec = take !== null && take.phase === "wait" ? build(stream) : null;
    if (rec === null) {
      mute(stream);
      if (shut(n)) say(n, { type: "off", code: "error" });
      return;
    }
    patch(n, { phase: "on", stream, rec, at: Date.now(), cap: setTimeout(() => cut(n), StudyCore.TALK_SEC * 1000 + OVER) });
    wire(n, rec, stream);
    say(n, { type: "on" });
  }
  function refused(n, err) {
    const denied = Boolean(err) && (err.name === "NotAllowedError" || err.name === "SecurityError");
    if (shut(n)) say(n, { type: "off", code: denied ? "denied" : "error" });
  }
  function ask(n) {
    try {
      Promise.resolve(navigator.mediaDevices.getUserMedia({ audio: true })).then(stream => granted(n, stream), err => refused(n, err));
    } catch (err) {
      refused(n, err);
    }
  }
  // [말하기]를 누른 그 처리 안에서 부른다. 녹음을 끈 기기에서는 마이크를 청하지 않는다(알리지도 않는다).
  // 다른 화면의 녹음이 돌고 있었으면 거기서 끊고, 같은 화면의 것이면 버린다(새것이 바꾼다).
  function begin(slot, date, onEvent) {
    const old = find(liveN);
    stopPlayback();
    if (old !== null && old.slot !== slot) cut(liveN);
    if (old !== null && old.slot === slot) shut(liveN);
    seq += 1;
    const take = { n: seq, slot, date, tell: typeof onEvent === "function" ? onEvent : quiet, phase: "over", stream: null, rec: null, lock: null, cap: null,
      chunks: [], at: null, end: null, packed: false };
    takes = new Map([...takes, [slot, take]]);
    if (!StudyStore.getFlag("rec")) return;
    if (!supported()) {
      say(take.n, { type: "off", code: "unsupported" });
      return;
    }
    patch(take.n, { phase: "wait" });
    liveN = take.n;
    watch();
    say(take.n, { type: "off", code: "wait" });
    wake(take.n);
    ask(take.n);
  }
  // 2분이 찼거나 [그만]을 눌렀다. slot을 주면 그 화면의 녹음이 마이크를 쥐고 있을 때만 닫는다(다른 화면의 녹음을 끊지 않는다).
  // slot 없이 부르면(설정에서 녹음을 껐다) 어느 화면의 것이든 닫고, 실제로 닫았을 때만 그 화면에 알린다 — 시계는 가는데 줄이 "녹음 중"으로 남지 않게.
  function end(slot) {
    const take = find(liveN);
    if (take === null || (slot !== undefined && take.slot !== slot)) return;
    if (shut(take.n) && slot === undefined) say(take.n, { type: "off", code: "error" });
  }

  // ── 보관(IndexedDB) ── 열기 · 쓰기 · 읽기는 모두 실패하거나 끝나지 않을 수 있다. 실패는 거절로 올라가고, 부른 쪽이 값으로 바꾼다.
  // 열기의 '막힘' 사건은 듣지 않는다 — 끝이 아니라서, 다른 연결이 닫히면 이어서 성공이나 실패가 온다
  function answer(req, resolve, reject) {
    req.addEventListener("success", () => resolve(req.result));
    req.addEventListener("error", () => reject(req.error));
  }
  function openDb() {
    try {
      const req = indexedDB.open(DB, 1);
      req.addEventListener("upgradeneeded", () => req.result.createObjectStore(STORE, { keyPath: "id" }));
      return new Promise((resolve, reject) => answer(req, resolve, reject));
    } catch (err) {
      return Promise.reject(err);
    }
  }
  function done(db, settle, value) {
    settle(value);
    try {
      db.close();
    } catch (err) {
      return;
    }
  }
  // 일 하나를 트랜잭션 하나로 한다. 트랜잭션이 끝나야(디스크에 닿아야) 답을 준다. 끝나면 연결을 닫는다.
  function carry(db, mode, job, resolve, reject) {
    try {
      const tx = db.transaction(STORE, mode);
      const req = job(tx.objectStore(STORE));
      tx.addEventListener("complete", () => done(db, resolve, req.result));
      tx.addEventListener("error", () => done(db, reject, tx.error));
      tx.addEventListener("abort", () => done(db, reject, tx.error));
    } catch (err) {
      done(db, reject, err);
    }
  }
  function work(mode, job) {
    return openDb().then(db => new Promise((resolve, reject) => carry(db, mode, job, resolve, reject)));
  }
  // 보관된 것 가운데 꼴이 맞는 것 전부(늦은 것부터). 같은 주소의 다른 코드도 이 저장소에 닿을 수 있다 — 꼴이 다른 값은 건너뛴다.
  function sound(row) {
    const texts = Boolean(row) && [row.id, row.slot, row.type].every(v => typeof v === "string") && StudyCore.isDate(row.date);
    return texts && [row.at, row.sec, row.bytes].every(v => Number.isFinite(v));
  }
  function rows() {
    return work("readonly", store => store.getAll()).then(all => Array.from(all).filter(sound).sort((a, b) => b.at - a.at));
  }
  // 최근 KEEP개만 남긴다. 지우지 못해도 조용히 넘어간다(다음 보관 때 다시 해 본다).
  function prune() {
    const drop = all => all.slice(KEEP).reduce((before, row) => before.then(() => work("readwrite", store => store.delete(row.id))), Promise.resolve());
    rows().then(drop).then(quiet, quiet);
  }

  // ── 녹음기가 멈춘 뒤 ── 우리가 멈췄든 스스로 멈췄든 여기로 온다(스스로 멈춘 것이면 끊김이다). 있는 만큼 보관한다.
  // 덩어리를 하나로 묶는다. 형식은 녹음기가 실제로 쓴 것을 적는다(형식 없는 덩어리는 재생되지 않을 수 있다). 묶지 못하면 null
  function pack(take) {
    try {
      const type = (take.rec && take.rec.mimeType) || (take.chunks[0] && take.chunks[0].type) || TYPES[0];
      return new Blob(take.chunks, { type });
    } catch (err) {
      return null;
    }
  }
  function saved(n, row) {
    say(n, { type: "saved", sec: row.sec, bytes: row.bytes });
    prune();
  }
  // 같은 날 같은 화면에서 다시 말하면 새것이 앞의 것을 바꾼다(키가 같다). 빈 파일은 두지 않고 알리기만 한다.
  function stopped(n) {
    cut(n);
    const take = find(n);
    if (take === null || take.packed) return;
    const blob = pack(take);
    patch(n, { packed: true, chunks: [], stream: null, rec: null });
    if (blob === null || blob.size === 0) {
      say(n, { type: "fail", code: blob === null ? "store" : "empty" });
      return;
    }
    const row = { id: take.date + "." + take.slot, date: take.date, slot: take.slot, at: take.at, sec: seconds(take.slot), bytes: blob.size, type: blob.type, blob };
    work("readwrite", store => store.put(row)).then(() => saved(n, row), () => say(n, { type: "fail", code: "store" }));
  }

  // ── 듣기와 설정이 읽는 것 ── 읽지 못하면 빈 값이다(거절하지 않는다). 답이 끝내 오지 않을 수는 있다 — 부른 쪽은 기다리지 않는다.
  function brief(row) {
    return { id: row.id, date: row.date, slot: row.slot, sec: row.sec, bytes: row.bytes, type: row.type };
  }
  function list() {
    return rows().then(all => all.slice(0, KEEP).map(brief), () => []);
  }
  function stats() {
    return list().then(all => ({ n: all.length, bytes: all.reduce((sum, row) => sum + row.bytes, 0) }));
  }
  function clearAll() {
    stopPlayback();
    return work("readwrite", store => store.clear()).then(() => true, () => false);
  }

  // ── 재생 주소 ── 듣기가 쓴다. 주소는 한 번에 하나만 살아 있다: 새로 청하거나, 녹음을 시작하거나, 화면을 떠나면 거둔다.
  function stopPlayback() {
    const old = playing;
    asks += 1;
    playing = null;
    try {
      if (old !== null) URL.revokeObjectURL(old);
    } catch (err) {
      return;
    }
  }
  // 읽어 온 녹음을 주소로 바꾼다. 그 사이 다른 것을 청했거나 거뒀으면, 또 녹음하는 중이면 내주지 않는다(null)
  function lend(mine, row) {
    if (mine !== asks || liveN !== 0 || !row || !row.blob) return null;
    try {
      playing = URL.createObjectURL(row.blob);
      return playing;
    } catch (err) {
      return null;
    }
  }
  function url(id) {
    stopPlayback();
    const mine = asks;
    return work("readonly", store => store.get(id)).then(row => lend(mine, row), () => null);
  }

  // ── 밖에서 쓰는 이름 ──
  return {
    supported, begin, end, seconds, list, url, stopPlayback, clearAll, stats,
    _: { DB, STORE, KEEP, BITS, TYPES },
  };
})();
