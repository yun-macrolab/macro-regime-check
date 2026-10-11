// 공부 화면의 2분 시계 한 부품 — 오늘 · 질문 화면이 빌려 쓴다.
// 횟수가 아니라 시작 시각과의 차이로 계산한다. 상태({ d, at, end })는 기기 저장에 있어서 화면이 죽었다 살아나도 이어 간다.
// 시계는 화면(slot)마다 하나다: 같은 화면이 create를 다시 불러도 때맞춤은 하나만 돌고, 알림은 마지막에 받은 hooks로 간다.
window.StudyTimer = (() => {
  "use strict";

  const TICK_MS = 250;
  const quiet = () => {};

  let clocks = new Map();        // 화면 이름 → { onTick, onDone, handle, shown, told }

  function patch(slot, change) {
    clocks = new Map([...clocks, [slot, { ...clocks.get(slot), ...change }]]);
  }
  // phase: "idle"(시작 전) · "running" · "done". sec은 말한 초(0~TALK_SEC), left는 남은 초. 날짜는 보지 않는다(resume이 본다).
  function state(slot) {
    const talk = StudyStore.talk(slot);
    if (talk === null) return { phase: "idle", sec: 0, left: StudyCore.TALK_SEC };
    const until = talk.end === null ? Date.now() : talk.end;
    const sec = Math.max(0, Math.min(StudyCore.TALK_SEC, Math.floor((until - talk.at) / 1000)));
    const over = talk.end !== null || sec >= StudyCore.TALK_SEC;
    return { phase: over ? "done" : "running", sec, left: StudyCore.TALK_SEC - sec };
  }
  function halt(slot) {
    const handle = clocks.get(slot).handle;
    if (handle !== null) clearInterval(handle);
    patch(slot, { handle: null });
  }
  function run(slot) {
    if (clocks.get(slot).handle === null) patch(slot, { handle: setInterval(() => tick(slot), TICK_MS) });
  }
  // 끝 시각이 비어 있으면 적는다(2분을 넘겨 적지 않는다)
  function seal(slot) {
    const talk = StudyStore.talk(slot);
    if (talk !== null && talk.end === null) StudyStore.setTalk(slot, { ...talk, end: Math.min(Date.now(), talk.at + StudyCore.TALK_SEC * 1000) });
  }
  // 끝을 적고 재기를 멈춘 뒤, 끝났다는 것을 한 번만 알린다
  function finish(slot) {
    seal(slot);
    halt(slot);
    const sec = state(slot).sec;
    const clock = clocks.get(slot);
    patch(slot, { told: true });
    if (!clock.told) clock.onDone(sec);
    return sec;
  }
  function tick(slot) {
    const s = state(slot);
    if (s.phase === "idle") halt(slot);
    if (s.phase === "done") finish(slot);
    if (s.phase !== "running" || s.left === clocks.get(slot).shown) return;
    patch(slot, { shown: s.left });
    clocks.get(slot).onTick(s.left);
  }
  function start(slot) {
    const now = Date.now();
    StudyStore.setTalk(slot, { d: StudyCore.studyDate(now), at: now, end: null });
    patch(slot, { shown: StudyCore.TALK_SEC, told: false });
    run(slot);
    return now;
  }
  // 화면을 그릴 때 부른다. 저장된 것이 오늘 공부 날짜가 아니면 지운다. hooks는 부르지 않는다.
  function resume(slot) {
    const talk = StudyStore.talk(slot);
    if (talk !== null && talk.d !== StudyCore.studyDate(Date.now())) StudyStore.setTalk(slot, null);
    const s = state(slot);
    if (s.phase === "running") {
      patch(slot, { shown: s.left, told: false });
      run(slot);
      return "running";
    }
    if (s.phase === "done") seal(slot);
    halt(slot);
    patch(slot, { told: true });
    return s.phase;
  }
  function stop(slot) {
    if (StudyStore.talk(slot) !== null) return finish(slot);
    halt(slot);
    return 0;
  }
  function clear(slot) {
    StudyStore.setTalk(slot, null);
    halt(slot);
    patch(slot, { told: true });
  }
  function create(slot, hooks) {
    const h = hooks || {};
    const fresh = { handle: null, shown: null, told: true, ...clocks.get(slot) };
    patch(slot, { ...fresh, onTick: typeof h.onTick === "function" ? h.onTick : quiet, onDone: typeof h.onDone === "function" ? h.onDone : quiet });
    return { start: () => start(slot), resume: () => resume(slot), stop: () => stop(slot), state: () => state(slot), clear: () => clear(slot), _: { tick: () => tick(slot) } };
  }

  return { TICK_MS, create };
})();
