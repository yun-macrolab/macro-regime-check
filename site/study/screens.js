// 공부 화면의 주간 · 질문 화면 — 주간: 이번 주 내 판정(두 번 눌러 저장) → 그 뒤에만 지난주 판정과 채점, 공유. 질문: 한 줄 · 말하기 2:00 · 세 칸 · 최근 질문.
// 문서 · 저장 공간 · 통신을 직접 만지지 않는다: 요소는 StudyApp.el로만 만들고, 기록은 StudyApp.write로만 적는다.
// 닻 내림 방지: 이번 주 판정을 저장하기 전에는 지난주 판정 · 채점 칸을 감추는 것이 아니라 만들지 않는다.
// 맞춤이 알리거나 화면으로 돌아왔을 때는 아무것도 바꾸지 않는다(쓰던 칸 · 확인 · 시계는 그대로다). 자기 저장 뒤에만 새로 그린다.
window.StudyScreens = (() => {
  "use strict";

  let week = null;               // 주간 화면에 그려 둔 자리(root · 그린 주 wk · 칸들). 화면을 떠나면 null이다
  let ask = null;                // 질문 화면에 그려 둔 자리(root · 칸들 form · 말하기 자리 stage · 시계 글자 face). 화면을 떠나면 null이다
  let clock = null;              // 질문 화면의 2분 시계 — 처음 쓸 때 만든다
  let turn = 0;                  // 주간 화면을 떠날 때마다 오른다(늦게 끝난 공유가 떠난 화면 · 다시 연 화면에 글을 쓰지 않게)

  const el = (tag, attrs, ...kids) => StudyApp.el(tag, attrs, ...kids);
  const t = (key, vars) => StudyCore.t(key, vars);
  const fill = (node, kids) => node.replaceChildren(...kids.flat(Infinity).filter(kid => kid !== null));
  const button = (id, key, more) => el("button", { id, class: "st-btn", type: "button", ...more }, t(key));
  const tap = (node, fn) => { node.addEventListener("click", fn); return node; };
  const says = (key, vars, attrs) => el("p", attrs || null, t(key, vars));
  const word = (group, value) => t(group + "_" + value.toUpperCase());
  const fine = (kind, name, input) => StudyCore.textIssue(kind, name, input.value) === null;
  const enumOf = (kind, name) => StudyCore.SCHEMA[kind].find(spec => spec[0] === name)[2];

  // ── 한 줄 칸 ── 쓰던 글이 값으로 들어간다. 칠 때마다 쓰던 글을 기기에 적고 changed()를 부른다.
  function field(id, slot, key, warnId, changed) {
    const input = el("input", { id, class: "st-input", type: "text", placeholder: t(key), "aria-label": t(key), "aria-describedby": warnId,
      enterkeyhint: "done", autocomplete: "off", value: StudyStore.draft(slot) });
    input.addEventListener("input", () => typed(input, slot, changed));
    return input;
  }
  function typed(input, slot, changed) {
    StudyStore.setDraft(slot, input.value);
    changed();
  }
  // 자판의 완료(Enter)는 그 칸의 저장 단추와 같다(단추가 꺼져 있거나 글자를 짓는 중이면 아니다)
  function onEnter(input, save, act) {
    input.addEventListener("keydown", ev => { if (ev.key === "Enter" && !ev.isComposing && !save.hasAttribute("disabled")) act(); });
  }
  // 칸 아래 경고: 너무 길다 · 받지 않는 글자 · 영숫자가 길게 이어짐. 비었거나 문제없으면 빈 글이다.
  function warnText(kind, name, value) {
    const issue = StudyCore.textIssue(kind, name, value);
    if (issue === "long") return t("WARN_LONG", { n: StudyCore.SCHEMA[kind].find(spec => spec[0] === name)[3] });
    if (issue === "ctrl") return t("WARN_CTRL");
    return issue === "secret" ? t("WARN_SECRET") : "";
  }

  // ── 고르기 묶음 ── 이름 한 줄 아래에 단추 셋(data-k가 값), 고른 것에 aria-pressed="true". 누르면 쓰던 글에 적고 눌림만 바꾼다(다른 칸은 그대로다).
  function choices(id, slot, key, group, values, changed) {
    const now = StudyStore.draft(slot);
    const nodes = values.map(v => el("button", { class: "st-btn", type: "button", "data-k": v, "aria-pressed": v === now }, word(group, v)));
    for (const node of nodes) tap(node, () => choose(nodes, node, slot, changed));
    return { nodes, box: el("div", { id, role: "group", "aria-label": t(key) }, says(key, null, { class: "st-dim" }), nodes) };
  }
  function choose(nodes, node, slot, changed) {
    StudyStore.setDraft(slot, node.getAttribute("data-k"));
    for (const other of nodes) other.setAttribute("aria-pressed", String(other === node));
    changed();
  }
  // 고른 값(아직 고르지 않았으면 null)
  function picked(choice) {
    const node = choice.nodes.find(n => n.getAttribute("aria-pressed") === "true");
    return node ? node.getAttribute("data-k") : null;
  }

  // ── 주간: 이번 주 내 판정 ── 넷(듀레이션 · 커브 · 근거 · 틀릴 조건)이 다 차고 문제없을 때만 [저장]이 켜진다. 두 번 눌러야 저장된다.
  function callParts() {
    const changed = () => showCall(false);
    const form = { dur: choices("wk-dur", "wk.dur", "WK_DUR", "DUR", enumOf("week", "dur"), changed),
      cur: choices("wk-cur", "wk.cur", "WK_CUR", "CUR", enumOf("week", "cur"), changed),
      why: field("wk-why", "wk.why", "WK_WHY_PH", "wk-warn", changed), wrong: field("wk-wrong", "wk.wrong", "WK_WRONG_PH", "wk-warn", changed),
      warn: el("p", { id: "wk-warn", class: "st-warn" }), box: el("div"), save: button("wk-save", "WK_SAVE") };
    for (const input of [form.why, form.wrong]) onEnter(input, form.save, () => pressSave());
    tap(form.save, () => pressSave());
    week = { ...week, form };
    showCall(false);
    return [el("h2", null, t("WK_HEAD")), form.dur.box, form.cur.box, form.why, form.wrong, form.warn, form.box, form.save];
  }
  // 칸이 바뀌면(armed = 거짓) 경고와 [저장]의 켜짐을 다시 정하고 확인 한 줄을 지운다 — 첫 누름으로 돌아간다. 첫 누름(armed = 참)은 확인 한 줄을 보인다.
  function showCall(armed) {
    const f = week.form;
    const [dur, cur] = [picked(f.dur), picked(f.cur)];
    const ready = dur !== null && cur !== null && fine("week", "why", f.why) && fine("week", "wrong_if", f.wrong);
    const on = armed && ready;
    f.warn.textContent = warnText("week", "why", f.why.value) || warnText("week", "wrong_if", f.wrong.value);
    StudyApp.flag(f.save, "disabled", !ready);
    f.save.textContent = t(on ? "WK_CONFIRM_BTN" : "WK_SAVE");
    fill(f.box, [on ? says("WK_CONFIRM", { dur: word("DUR_S", dur), cur: word("CUR", cur) }, { id: "wk-confirm", class: "st-amber" }) : null]);
    week = { ...week, armed: on };
  }
  function pressSave() {
    if (week.armed) saveCall();
    else showCall(true);
  }
  // 둘째 누름: 누른 순간의 주로 적는다. 칸을 연 채 주가 바뀌었으면(월요일 04:00) 쓰지 않고 새 주의 칸부터 다시 한다.
  function saveCall() {
    const [c, f] = [StudyApp.ctx(), week.form];
    const fields = { wk: c.wk, dur: picked(f.dur), cur: picked(f.cur), why: f.why.value, wrong_if: f.wrong.value };
    if (c.wk === week.wk && StudyApp.write("week", fields).ok) StudyStore.clearDrafts(["wk.dur", "wk.cur", "wk.why", "wk.wrong"]);
    redrawWeek();
  }

  // ── 주간: 저장한 뒤 ── 이번 주 내 판정(읽기 전용)과 [공유], 그 아래에 지난주 내 판정과 채점. 이번 주 판정이 있을 때만 만든다.
  function callLines(call, head) {
    return [head, says("SH_WHY", { text: call.why }), says("SH_WRONG", { text: call.wrong_if })];
  }
  function mineParts(c, call) {
    const head = says("WK_MINE", { dur: word("DUR", call.dur), cur: word("CUR", call.cur) });
    return [el("div", { id: "wk-mine" }, callLines(call, head)), tap(button("wk-share", "TD_SHARE"), () => shareWeek()), week.shown, lastParts(c)];
  }
  function lastParts(c) {
    const last = StudyCore.weekCall(c.view, c.lastWk);
    if (last === null) return [says("WK_LAST_NONE", null, { id: "wk-none", class: "st-dim" })];
    const head = says("SH_WEEK", { wk: c.lastWk, dur: word("DUR", last.dur), cur: word("CUR", last.cur) });
    const grade = StudyCore.gradeFor(c.view, c.lastWk);
    return [el("section", { id: "wk-last", class: "st-group" }, el("h2", null, t("WK_LAST_HEAD")), callLines(last, head)), grade === null ? gradeParts(last) : doneParts(grade)];
  }

  // ── 주간: 채점 ── 실제 한 줄과 듀레이션 · 커브의 맞음/빗나감/판단 보류가 차야 [채점 저장]이 켜진다. 빗나간 이유는 비워도 된다.
  function gradeParts(last) {
    const changed = () => showGrade();
    const form = { ref: last.id, actual: field("gr-actual", "gr.actual", "GR_ACTUAL_PH", "gr-warn", changed),
      dur: choices("gr-dur", "gr.dur", "WK_DUR", "HIT", enumOf("grade", "dur_hit"), changed),
      cur: choices("gr-cur", "gr.cur", "WK_CUR", "HIT", enumOf("grade", "cur_hit"), changed),
      miss: field("gr-miss", "gr.miss", "GR_MISS_PH", "gr-warn", changed), warn: el("p", { id: "gr-warn", class: "st-warn" }), save: button("gr-save", "GR_SAVE") };
    for (const input of [form.actual, form.miss]) onEnter(input, form.save, () => saveGrade());
    tap(form.save, () => saveGrade());
    week = { ...week, grade: form };
    showGrade();
    return [form.actual, form.dur.box, form.cur.box, form.miss, form.warn, form.save];
  }
  function showGrade() {
    const g = week.grade;
    g.warn.textContent = warnText("grade", "actual", g.actual.value) || warnText("grade", "miss", g.miss.value);
    StudyApp.flag(g.save, "disabled", picked(g.dur) === null || picked(g.cur) === null || !fine("grade", "actual", g.actual) || !fine("grade", "miss", g.miss));
  }
  // 누른 순간의 기록으로 적는다. 보이던 판정이 더는 지난주의 판정이 아니면(주가 바뀌었다 · 더 먼저 쓴 판정을 받았다) 쓰지 않고 다시 그리기만 한다.
  function saveGrade() {
    const [c, g] = [StudyApp.ctx(), week.grade];
    const last = StudyCore.weekCall(c.view, c.lastWk);
    const fields = { wk: c.lastWk, ref: g.ref, actual: g.actual.value, dur_hit: picked(g.dur), cur_hit: picked(g.cur), miss: g.miss.value };
    if (last !== null && last.id === g.ref && StudyApp.write("grade", fields).ok) StudyStore.clearDrafts(["gr.actual", "gr.dur", "gr.cur", "gr.miss"]);
    redrawWeek();
  }
  function doneParts(grade) {
    const hit = says("SH_HIT", { dur: word("HIT", grade.dur_hit), cur: word("HIT", grade.cur_hit) });
    const miss = grade.miss === "" ? null : says("SH_MISS", { text: grade.miss });
    return [el("div", { id: "gr-done" }, says("GR_SAVED", null, { class: "st-dim" }), says("SH_ACTUAL", { text: grade.actual }), hit, miss)];
  }

  // ── 주간: [공유] ── 누른 그 처리 안에서 곧바로 부른다. 공유 창이 닫히지 않아도 화면은 기다리지 않는다. 어느 앱으로 갔는지는 알지 못한다.
  function shareWeek() {
    const c = StudyApp.ctx();
    const text = StudyCore.shareWeek(c.view, c.wk);
    const mine = turn;
    StudyApp.note(text === null ? "SHARE_NONE" : null);
    if (text !== null) StudyApp.share(text).then(how => shared(how, text, mine));
  }
  function shared(how, text, mine) {
    if (mine !== turn || (how !== "copied" && how !== "shown")) return;
    StudyApp.note(how === "copied" ? "SHARE_COPIED" : "SHARE_SHOWN");
    if (how === "shown") fill(week.shown, [el("pre", { id: "wk-sharebox" }, text)]);
  }

  // ── 주간 화면 ── 이번 주 판정이 없으면 판정 칸만, 있으면 이번 주 판정 → [공유] → 지난주 판정 → 채점
  function paintWeek(root, c) {
    const call = StudyCore.weekCall(c.view, c.wk);
    week = { root, wk: c.wk, shown: el("div") };
    StudyApp.note(null);         // 새로 그리면 보여 주던 공유 글이 사라진다 — 알림 한 줄도 함께 치운다
    fill(root, call === null ? callParts() : mineParts(c, call));
  }
  function redrawWeek() {
    if (week !== null) paintWeek(week.root, StudyApp.ctx());
  }
  function refreshWeek(root, c, why) {
    if (why === "write" || week === null) paintWeek(root, c);
  }
  function leaveWeek() {
    turn += 1;
    week = null;
  }

  // ── 질문: 말하기와 시계 ── 시계의 상태는 기기 저장에 있다. 그릴 때마다 resume()으로 묻는다(화면이 죽었다 살아나도 이어 간다).
  function timer() {
    clock = clock || StudyTimer.create("ask", { onTick: left => ticked(left), onDone: () => drawTalk() });
    return clock;
  }
  function ticked(left) {
    if (ask !== null && ask.face !== null) ask.face.textContent = StudyCore.mmss(left);
  }
  function startTalk() {
    timer().start();
    drawTalk();
  }
  // 말하기 자리: 도는 동안은 남은 시간과 [그만], 그 밖에는 [말하기 2:00](끝났으면 "끝 · 말한 시간"과 함께 — 다시 말할 수 있다)
  function drawTalk() {
    if (ask === null) return;
    const phase = timer().resume();
    const s = timer().state();
    const face = phase === "idle" ? null : el("p", { id: "ask-clock", role: "timer" }, phase === "running" ? StudyCore.mmss(s.left) : t("TD_TALKED", { t: StudyCore.mmss(s.sec) }));
    const stop = phase === "running" ? tap(button("ask-stop", "TD_STOP"), () => timer().stop()) : null;
    const talk = phase === "running" ? null : tap(button("ask-talk", "TD_TALK", { class: "st-btn st-btn-big" }), () => startTalk());
    ask = { ...ask, face };
    fill(ask.stage, [face, stop, talk]);
  }

  // ── 질문: 세 칸과 저장 ── 세 칸(결론 먼저 · 근거 둘 · 틀릴 조건)은 스스로 체크한다. 바뀔 때마다 "101" 꼴로 쓰던 글에 적는다. 체크 칸은 제 이름표 안에 든다.
  const CHECKS = Object.freeze([["ask-head", "ASK_HEAD"], ["ask-two", "ASK_TWO"], ["ask-wrong", "ASK_WRONG"]]);
  function checkBoxes() {
    const bits = StudyStore.draft("ask.s");
    const boxes = CHECKS.map((pair, i) => el("input", { id: pair[0], type: "checkbox", checked: bits[i] === "1" }));
    for (const box of boxes) box.addEventListener("change", () => StudyStore.setDraft("ask.s", boxes.map(b => (b.checked ? "1" : "0")).join("")));
    return boxes;
  }
  function showAsk() {
    const f = ask.form;
    f.warn.textContent = warnText("q", "text", f.input.value);
    StudyApp.flag(f.save, "disabled", !fine("q", "text", f.input));
  }
  // [저장]: 시계가 돌고 있으면 멈추고 그때까지의 초로 적는다(어제의 시계는 없던 일이다 — 0초). 적은 뒤 칸 · 체크 · 시계 · 쓰던 글을 비운다.
  function saveAsk() {
    const f = ask.form;
    if (timer().resume() === "running") timer().stop();
    const fields = { text: f.input.value, sec: timer().state().sec, rec: 0, s_head: f.boxes[0].checked, s_two: f.boxes[1].checked, s_wrong: f.boxes[2].checked };
    if (!StudyApp.write("q", fields).ok) return;
    timer().clear();
    StudyStore.clearDrafts(["ask.text", "ask.s"]);
    redrawAsk();
  }

  // ── 질문: 최근 질문 ── 늦은 것부터 5개. [가리기]는 가림 줄을 쓴다 — 줄은 파일에 남고 화면과 공유 글에서만 빠진다.
  function listParts(c) {
    const qs = StudyCore.recentQs(c.view, 5);
    const hide = id => tap(el("button", { class: "st-btn ask-hide", type: "button" }, t("ASK_HIDE")), () => StudyApp.write("fix", { ref: id, hide: true }));
    const rows = qs.map(q => el("li", { "data-k": q.id }, el("span", null, q.text), " ", hide(q.id)));
    return [el("h2", null, t("ASK_RECENT")), el("ul", { id: "ask-list" }, rows), qs.length === 0 ? says("ASK_EMPTY", null, { class: "st-dim" }) : null];
  }

  // ── 질문 화면 ── 위에서부터: 한 줄 칸 → 규칙 한 줄 → 말하기 자리 → 세 칸 → [저장] → 최근 질문
  function paintAsk(root, c) {
    const form = { input: field("ask-text", "ask.text", "ASK_PH", "ask-warn", () => showAsk()), warn: el("p", { id: "ask-warn", class: "st-warn" }),
      boxes: checkBoxes(), save: button("ask-save", "ASK_SAVE") };
    const checks = el("div", null, form.boxes.map((box, i) => el("label", { for: CHECKS[i][0] }, box, t(CHECKS[i][1]))));
    onEnter(form.input, form.save, () => saveAsk());
    tap(form.save, () => saveAsk());
    ask = { root, form, stage: el("div"), face: null };
    fill(root, [form.input, form.warn, says("ASK_RULE", null, { id: "ask-rule", class: "st-dim" }), ask.stage, checks, form.save, listParts(c)]);
    showAsk();
    drawTalk();
  }
  function redrawAsk() {
    if (ask !== null) paintAsk(ask.root, StudyApp.ctx());
  }
  function refreshAsk(root, c, why) {
    if (why === "write" || ask === null) paintAsk(root, c);
  }
  function leaveAsk() {
    ask = null;
  }

  // ── 틀에 들어가기 ── 길 이름마다 화면 하나
  const weekScreen = { render: paintWeek, refresh: refreshWeek, leave: leaveWeek };
  const askScreen = { render: paintAsk, refresh: refreshAsk, leave: leaveAsk };
  StudyApp.register("week", weekScreen);
  StudyApp.register("ask", askScreen);

  return { _: { week: weekScreen, ask: askScreen } };
})();
