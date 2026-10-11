// 공부 화면의 오늘 화면 — 오늘 말할 개념, [말하기 2:00]과 시계, 막힌 곳 한 줄과 도장(○ · △), 내일 말할 개념, 공유, 최근 14일, 쉬는 날.
// 문서 · 저장 공간 · 통신을 직접 만지지 않는다: 요소는 StudyApp.el로만 만들고, 기록은 StudyApp.write로만 적는다.
// 맞춤이 알리거나 화면으로 돌아왔을 때는 개념 줄 · 권고 줄 · 도장 자리 · 14일 줄만 다시 그린다 — 쓰던 칸과 시계는 건드리지 않는다.
window.StudyToday = (() => {
  "use strict";

  let ui = null;                 // 지금 그려 둔 자리들. 화면을 떠나면 null이다(그 뒤에 온 알림은 아무것도 그리지 않는다)
  let clock = null;              // 2분 시계 — 처음 쓸 때 만든다
  let turn = 0;                  // 화면을 새로 열거나 떠날 때마다 오른다(늦게 끝난 공유가 다른 화면에 글을 쓰지 않게)

  const el = (tag, attrs, ...kids) => StudyApp.el(tag, attrs, ...kids);
  const t = (key, vars) => StudyCore.t(key, vars);
  const fill = (node, kids) => node.replaceChildren(...kids.flat(Infinity).filter(kid => kid !== null));
  const button = (id, key, more) => el("button", { id, class: "st-btn", type: "button", ...more }, t(key));
  const tap = (node, fn) => { node.addEventListener("click", fn); return node; };

  // ── 맞춤이 바꾸는 자리 ── 맞춤이 알리거나 화면으로 돌아왔을 때 다시 그리는 줄들
  function topLines(c) {
    const topic = StudyCore.topicFor(c.view, c.today);
    return [
      el("p", { id: "td-topic" }, topic === null ? t("TD_TOPIC_NONE") : t("TD_TOPIC", { text: topic })),
      StudyCore.weekCall(c.view, c.wk) === null ? el("p", { id: "td-weekhint", class: "st-dim" }, t("TD_WEEK_HINT")) : null,
      StudyCore.comeback(c.view, c.today) ? el("p", { id: "td-advice", class: "st-amber" }, t("TD_ADVICE")) : null,
    ];
  }
  function doneLine(c) {
    const stamp = StudyCore.stampOn(c.view, c.today);
    if (stamp === null) return null;
    return el("p", { id: "td-done" }, t("TD_STAMPED", { mark: t(stamp.mark === "full" ? "MARK_FULL" : "MARK_MIN"), t: stamp.t.slice(11, 16) }));
  }
  function stripCells(c) {
    return StudyCore.strip14(c.view, c.today).map(day => el("li", { class: "st-cell", "data-k": day.cell }, t("MARK_" + day.cell.toUpperCase())));
  }

  // ── 말하기와 시계 ── 시계의 상태는 기기 저장에 있다. 그릴 때마다 resume()으로 묻는다(화면이 죽었다 살아나도 이어 간다).
  function timer() {
    clock = clock || StudyTimer.create("today", { onTick: left => ticked(left), onDone: () => ended() });
    return clock;
  }
  function ticked(left) {
    if (ui !== null && ui.face !== null) ui.face.textContent = StudyCore.mmss(left);
  }
  // 2분이 찼거나 [그만]을 눌렀다 — 말하기 자리를 다시 그린다
  function ended() {
    if (ui !== null) drawStage(StudyApp.ctx());
  }
  function startTalk() {
    timer().start();
    drawStage(StudyApp.ctx());
  }
  // 시계 글자: 도는 동안은 남은 시간, 끝나면 "끝 · 말한 시간"
  function faceText(phase) {
    const s = timer().state();
    return phase === "running" ? StudyCore.mmss(s.left) : t("TD_TALKED", { t: StudyCore.mmss(s.sec) });
  }
  function talkParts(phase, stamped, face) {
    if (phase === "running") return [face, tap(button("td-stop", "TD_STOP"), () => timer().stop())];
    if (phase === "done") return [face];
    return stamped ? [] : [tap(button("td-talk", "TD_TALK", { class: "st-btn st-btn-big" }), () => startTalk())];
  }
  // 말하기 자리: [말하기] 또는 시계 → 도장 자리 → 도장 칸(시계가 끝났고 도장이 없을 때) 또는 도장 뒤의 칸
  function drawStage(c) {
    const phase = timer().resume();
    const stamped = StudyCore.stampOn(c.view, c.today) !== null;
    const face = phase === "idle" ? null : el("p", { id: "td-clock", role: "timer" }, faceText(phase));
    const done = el("div", null, doneLine(c));
    ui = { ...ui, face, done, box: el("div"), quiet: phase === "idle" && !stamped };
    fill(ui.stage, [talkParts(phase, stamped, face), done, stamped ? afterParts(c) : phase === "done" ? formParts(c) : null]);
  }

  // ── 한 줄 칸 ── 쓰던 글이 값으로 들어간다. 자판의 완료(Enter)는 그 칸의 저장 단추와 같다(글자를 짓는 중이면 아니다).
  function field(id, slot, key) {
    return el("input", { id, class: "st-input", type: "text", placeholder: t(key), "aria-label": t(key), "aria-describedby": "td-warn",
      enterkeyhint: "done", autocomplete: "off", value: StudyStore.draft(slot) });
  }
  function onEnter(ev, save, act) {
    if (ev.key === "Enter" && !ev.isComposing && !save.hasAttribute("disabled")) act();
  }
  // 칸 아래 경고: 너무 길다 · 받지 않는 글자 · 영숫자가 길게 이어짐. 비었거나 문제없으면 빈 글이다.
  function warnText(kind, name, value) {
    const issue = StudyCore.textIssue(kind, name, value);
    if (issue === "long") return t("WARN_LONG", { n: StudyCore.SCHEMA[kind].find(spec => spec[0] === name)[3] });
    if (issue === "ctrl") return t("WARN_CTRL");
    return issue === "secret" ? t("WARN_SECRET") : "";
  }

  // ── 도장 칸 ── ○는 한 줄을 적거나 [막힘 없음]을 눌러야 켜진다. △는 언제나 켜져 있다. 돌아오는 날에는 △가 앞에 온다.
  function formParts(c) {
    const form = { input: field("td-stuck", "td.stuck", "TD_STUCK_PH"), warn: el("p", { id: "td-warn", class: "st-warn" }),
      none: button("td-nostuck", "TD_NOSTUCK", { "aria-pressed": StudyStore.draft("td.nostuck") === "1" }), full: button("td-full", "TD_FULL") };
    const min = tap(button("td-min", "TD_MIN"), () => stamp("min", form.input));
    form.input.addEventListener("input", () => stuckTyped(form));
    form.input.addEventListener("keydown", ev => onEnter(ev, form.full, () => stamp("full", form.input)));
    tap(form.none, () => noStuck(form));
    tap(form.full, () => stamp("full", form.input));
    showStuck(form);
    return [form.input, form.warn, form.none, StudyCore.comeback(c.view, c.today) ? [min, form.full] : [form.full, min]];
  }
  function showStuck(form) {
    const written = StudyCore.textIssue("day", "stuck", form.input.value) === null && form.input.value.trim() !== "";
    form.warn.textContent = warnText("day", "stuck", form.input.value);
    StudyApp.flag(form.full, "disabled", !(written || StudyStore.draft("td.nostuck") === "1"));
  }
  function stuckTyped(form) {
    StudyStore.setDraft("td.stuck", form.input.value);
    showStuck(form);
  }
  function noStuck(form) {
    StudyStore.setDraft("td.nostuck", "1");
    form.none.setAttribute("aria-pressed", "true");
    showStuck(form);
  }
  // 도장: 기기에 쓰고 → 시계와 쓰던 글을 치우고 → 다시 그린다. 시계가 오늘 것이 아니면(그 사이 날짜가 바뀌었다) 찍지 않고 다시 그리기만 한다.
  function stamp(mark, input) {
    const fresh = timer().resume() === "done";
    const stuck = StudyCore.textIssue("day", "stuck", input.value) === null ? input.value.trim() : "";
    const wrote = fresh && StudyApp.write("day", { mark, sec: timer().state().sec, rec: 0, stuck }).ok;
    if (wrote) timer().clear();
    if (wrote) StudyStore.clearDrafts(["td.stuck", "td.nostuck"]);
    if (wrote || !fresh) redraw();
  }

  // ── 도장 뒤 ── 내일 말할 개념 · [다시 말하기](연습 — 도장을 새로 만들지 않는다)
  function afterParts(c) {
    const form = { input: field("td-next", "td.next", "TD_NEXT_PH"), warn: el("p", { id: "td-warn", class: "st-warn" }), save: button("td-nextsave", "TD_NEXT_SAVE") };
    const nexts = c.view.recs.filter(r => r.k === "next" && r.d === c.today);
    const said = nexts.length === 0 ? null : el("p", { id: "td-nextdone", class: "st-dim" }, t("TD_NEXT_SAVED", { text: nexts[nexts.length - 1].text }));
    form.input.addEventListener("input", () => nextTyped(form));
    form.input.addEventListener("keydown", ev => onEnter(ev, form.save, () => saveNext(form.input)));
    tap(form.save, () => saveNext(form.input));
    showNext(form);
    const again = tap(button("td-again", "TD_AGAIN"), () => startTalk());
    return [form.input, form.warn, form.save, said, again, tap(button("td-share", "TD_SHARE"), () => shareDay()), ui.box];
  }
  function showNext(form) {
    form.warn.textContent = warnText("next", "text", form.input.value);
    StudyApp.flag(form.save, "disabled", StudyCore.textIssue("next", "text", form.input.value) !== null);
  }
  function nextTyped(form) {
    StudyStore.setDraft("td.next", form.input.value);
    showNext(form);
  }
  function saveNext(input) {
    if (!StudyApp.write("next", { text: input.value }).ok) return;
    StudyStore.clearDrafts(["td.next"]);
    redraw();
  }
  // [공유]: 누른 그 처리 안에서 곧바로 부른다. 공유 창이 닫히지 않아도 화면은 기다리지 않는다. 어느 앱으로 갔는지는 알지 못한다.
  function shareDay() {
    const c = StudyApp.ctx();
    const text = StudyCore.shareDay(c.view, c.today);
    const mine = turn;
    StudyApp.note(text === null ? "SHARE_NONE" : null);
    if (text !== null) StudyApp.share(text).then(how => shared(how, text, mine));
  }
  function shared(how, text, mine) {
    if (mine !== turn || (how !== "copied" && how !== "shown")) return;
    StudyApp.note(how === "copied" ? "SHARE_COPIED" : "SHARE_SHOWN");
    if (how === "shown") fill(ui.box, [el("pre", { id: "td-sharebox" }, text)]);
  }

  // ── 쉬는 날 ── 내일 · 모레만 미리 정한다. 다시 누르면 취소다(가림 줄을 쓴다).
  function restFold(c, open) {
    const rests = [restButton("td-rest1", "TD_REST1", 1, c), restButton("td-rest2", "TD_REST2", 2, c)];
    return el("details", { class: "st-fold", open }, el("summary", null, t("TD_REST_FOLD")), rests);
  }
  function restButton(id, key, days, c) {
    const node = button(id, key, { "aria-pressed": StudyCore.restOn(c.view, StudyCore.addDays(c.today, days)).on });
    return tap(node, () => toggleRest(node, days));
  }
  // 누른 순간의 날짜와 기록으로 정한다. 단추에 보이던 것과 다르면(다른 기기의 쉼을 받았다 · 날짜가 바뀌었다) 쓰지 않고 다시 그리기만 한다.
  function toggleRest(node, days) {
    const c = StudyApp.ctx();
    const on = StudyCore.addDays(c.today, days);
    const rest = StudyCore.restOn(c.view, on);
    if ((node.getAttribute("aria-pressed") === "true") !== rest.on) redraw();
    else if (rest.on) StudyApp.write("fix", { ref: rest.id, hide: true });
    else StudyApp.write("rest", { on });
  }

  // ── 화면 ── 위에서부터: 개념 줄과 권고 줄 → 말하기 자리 → 14일 줄 → 쉬는 날(접힌 줄, 열어 둔 채면 그대로 둔다)
  function paint(root, c) {
    const open = ui !== null && ui.fold.hasAttribute("open");
    StudyApp.note(null);         // 새로 그리면 보여 주던 공유 글이 사라진다 — 알림 한 줄도 함께 치운다
    const strip = el("ol", { id: "td-strip", class: "st-strip", "aria-label": t("TD_STRIP") }, stripCells(c));
    ui = { root, top: el("div", null, topLines(c)), stage: el("div"), strip, fold: restFold(c, open), face: null, done: null, box: null, quiet: false };
    root.replaceChildren(ui.top, ui.stage, ui.strip, ui.fold);
    drawStage(c);
  }
  function redraw() {
    if (ui !== null) paint(ui.root, StudyApp.ctx());
  }
  // 맞춤 · 돌아옴: 맞춤이 바꾸는 자리만. [말하기]만 있던 자리에 도장이 생겼으면(다른 기기에서 찍었다) 그 자리를 새로 그린다 — 쓰던 칸도 시계도 없다.
  function repaint(c) {
    fill(ui.top, topLines(c));
    if (ui.quiet && StudyCore.stampOn(c.view, c.today) !== null) drawStage(c);
    else fill(ui.done, [doneLine(c)]);
    fill(ui.strip, stripCells(c));
  }
  function render(root, c) {
    turn += 1;
    paint(root, c);
  }
  function refresh(root, c, why) {
    if (why === "write" || ui === null) paint(root, c);
    else repaint(c);
  }
  function leave() {
    turn += 1;
    ui = null;
  }

  StudyApp.register("today", { render, refresh, leave });

  return { _: { render, refresh, leave } };
})();
