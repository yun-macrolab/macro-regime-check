// 공부 화면의 오늘 화면 — 오늘 말할 개념, [말하기 2:00]과 시계, 녹음 한 줄, 막힌 곳 한 줄과 도장(○ · △), 내일 말할 개념, 공유, 최근 14일, 쉬는 날, 녹음 듣기.
// 문서 · 저장 공간 · 통신 · 마이크를 직접 만지지 않는다: 요소는 StudyApp.el로만 만들고, 기록은 StudyApp.write로만 적고, 녹음은 녹음 모듈에 맡긴다.
// 녹음은 '되면 얹는' 것이다: 녹음 모듈이 없거나 답이 없어도 시계 · 도장 · 한 줄은 그대로 돈다.
// 맞춤이 알리거나 화면으로 돌아왔을 때는 개념 줄 · 권고 줄 · 도장 자리 · 14일 줄만 다시 그린다 — 쓰던 칸과 시계는 건드리지 않는다.
window.StudyToday = (() => {
  "use strict";

  let ui = null;                 // 지금 그려 둔 자리들. 화면을 떠나면 null이다(그 뒤에 온 알림은 아무것도 그리지 않는다)
  let clock = null;              // 2분 시계 — 처음 쓸 때 만든다
  let turn = 0;                  // 화면을 새로 열거나 떠날 때마다 오른다(늦게 끝난 공유가 다른 화면에 글을 쓰지 않게)
  let recLine = { d: "", key: null, sec: 0, nowake: false };   // 녹음 한 줄의 재료: 그 말하기의 공부 날짜 · 문구 키 · 끊긴 초 · 화면 켜 두기를 얻지 못했는가

  const el = (tag, attrs, ...kids) => StudyApp.el(tag, attrs, ...kids);
  const t = (key, vars) => StudyCore.t(key, vars);
  const fill = (node, kids) => node.replaceChildren(...kids.flat(Infinity).filter(kid => kid !== null));
  const button = (id, key, more) => el("button", { id, class: "st-btn", type: "button", ...more }, t(key));
  const tap = (node, fn) => { node.addEventListener("click", fn); return node; };
  const size = bytes => (bytes >= 100000 ? (bytes / 1000000).toFixed(1) + "MB" : Math.round(bytes / 1000) + "KB");   // 녹음의 크기를 글로(2분 64kbps면 "1.0MB")
  // 녹음 모듈의 손 — 쓸 때마다 다시 본다. 모듈이 없거나 던지면 undefined다(없는 대로 돈다)
  function hear(method, ...args) {
    try {
      const recorder = window.StudyRecorder;
      return recorder && typeof recorder[method] === "function" ? recorder[method](...args) : undefined;
    } catch (err) {
      return undefined;
    }
  }

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

  // ── 녹음 한 줄 ── 녹음 모듈이 알려 온 것을 글로: 녹음 없이 진행 중(허용을 기다리는 동안에도) · 녹음 중 · 끊김 m:ss · 녹음 실패 · 녹음 보관 불가.
  // 보관됐다는 말은 하지 않는다. 다른 화면에 가 있는 동안 온 것도 적어 두었다가 돌아오면 보인다.
  const REC_KEYS = new Map([["on", "REC_ON"], ["off", "REC_OFF"], ["cut", "REC_CUT"], ["empty", "REC_FAIL"], ["store", "REC_NOSTORE"]]);
  function drawRec() {
    if (ui === null) return;
    const calm = recLine.key === "REC_ON" || recLine.key === "REC_OFF";
    const text = recLine.key === null ? "" : t(recLine.key, { t: StudyCore.mmss(recLine.sec) }) + (recLine.nowake && recLine.key === "REC_ON" ? " · " + t("REC_NOWAKE") : "");
    fill(ui.rec, [recLine.key === null ? null : el("p", { id: "td-recnote", class: calm ? "st-dim" : "st-amber", role: "status" }, text)]);
  }
  function recEvent(ev) {
    const key = REC_KEYS.get(ev.type === "fail" ? ev.code : ev.type);
    if (ev.type === "nowake") recLine = { ...recLine, nowake: true };
    if (key !== undefined) recLine = { ...recLine, key, sec: Number.isInteger(ev.sec) ? ev.sec : 0 };
    drawRec();
    if (ev.type === "saved") loadTakes();
  }
  // [말하기]를 누른 그 처리 안에서 부른다: 듣던 것을 멈추고 비운 뒤 녹음을 청하고 곧바로 돌아온다(허용을 기다리지 않는다 — 시계는 이미 돈다)
  function recStart(c) {
    dropPlayer();
    recLine = { d: c.today, key: null, sec: 0, nowake: false };
    hear("begin", "today", c.today, ev => recEvent(ev));
  }
  // 시계가 돌지 않으면 이 화면의 마이크도 닫혀 있어야 한다. "녹음 중" · "녹음 없이 진행 중"은 지우고, 끊김 · 실패의 줄은 남긴다
  function recStop() {
    hear("end", "today");
    if (recLine.key === "REC_ON" || recLine.key === "REC_OFF") recLine = { ...recLine, key: null };
  }
  // 도장에 적을 '녹음기를 돌린 초'(녹음하지 않았으면 0)
  function recSec() {
    const sec = hear("seconds", "today");
    return Number.isInteger(sec) && sec >= 0 && sec <= StudyCore.TALK_SEC ? sec : 0;
  }

  // ── 말하기와 시계 ── 시계의 상태는 기기 저장에 있다. 그릴 때마다 resume()으로 묻는다(화면이 죽었다 살아나도 이어 간다).
  function timer() {
    clock = clock || StudyTimer.create("today", { onTick: left => ticked(left), onDone: () => ended() });
    return clock;
  }
  function ticked(left) {
    if (ui !== null && ui.face !== null) ui.face.textContent = StudyCore.mmss(left);
  }
  // 2분이 찼거나 [그만]을 눌렀다 — 마이크를 닫고(다른 화면에 가 있어도) 말하기 자리를 다시 그린다
  function ended() {
    recStop();
    if (ui !== null) drawStage(StudyApp.ctx());
  }
  function startTalk() {
    const c = StudyApp.ctx();
    timer().start();
    recStart(c);
    drawStage(c);
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
  // 말하기 자리: [말하기] 또는 시계 → 녹음 한 줄 → 도장 자리 → 도장 칸(시계가 끝났고 도장이 없을 때) 또는 도장 뒤의 칸
  function drawStage(c) {
    const phase = timer().resume();
    const stamped = StudyCore.stampOn(c.view, c.today) !== null;
    const face = phase === "idle" ? null : el("p", { id: "td-clock", role: "timer" }, faceText(phase));
    const done = el("div", null, doneLine(c));
    if (phase !== "running") recStop();
    ui = { ...ui, face, done, rec: el("div"), box: el("div"), quiet: phase === "idle" && !stamped };
    fill(ui.stage, [talkParts(phase, stamped, face), ui.rec, done, stamped ? afterParts(c) : phase === "done" ? formParts(c) : null]);
    drawRec();
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
    const wrote = fresh && StudyApp.write("day", { mark, sec: timer().state().sec, rec: recSec(), stuck }).ok;
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

  // ── 녹음 듣기 ── 접힌 줄. 열 때 이 기기에 둔 최근 녹음(7개까지)을 읽어 온다. 줄을 누르면 그 아래에 재생 막대가 선다(한 번에 하나).
  // 녹음 모듈이 없으면 이 줄도 없다. 같은 화면에서 다시 그릴 때는 그대로 둔다(듣던 것이 끊기지 않게).
  function listenParts() {
    if (!window.StudyRecorder) return { listen: null, takes: null, player: null };
    const takes = el("div");
    const listen = el("details", { id: "td-listen", class: "st-fold" }, el("summary", null, t("LISTEN_FOLD")), takes);
    listen.addEventListener("toggle", () => loadTakes());
    return { listen, takes, player: null };
  }
  // 재생 막대를 비우고 치운다(주소를 빈 글로 바꾸면 틀던 것이 멈추고 놓인다). 녹음 모듈이 내준 재생 주소도 거둔다
  function dropPlayer() {
    if (ui !== null && ui.player !== null) {
      ui.player.setAttribute("src", "");
      ui.player.remove();
      ui = { ...ui, player: null };
    }
    hear("stopPlayback");
  }
  // 접힌 줄을 열었거나 새 녹음이 보관됐다: 목록을 다시 읽는다. 닫았으면 듣던 것을 멈춘다
  function loadTakes() {
    if (ui === null || ui.listen === null) return;
    const mine = turn;
    if (!ui.listen.hasAttribute("open")) dropPlayer();
    else Promise.resolve(hear("list")).then(rows => showTakes(mine, rows), () => showTakes(mine, []));
  }
  function showTakes(mine, rows) {
    if (ui === null || mine !== turn) return;
    const list = Array.isArray(rows) ? rows : [];
    dropPlayer();
    fill(ui.takes, [list.length === 0 ? el("p", { class: "st-dim" }, t("LISTEN_NONE")) : el("ul", null, list.map(row => takeRow(row)))]);
  }
  function takeRow(row) {
    const label = t("LISTEN_ITEM", { date: StudyCore.headDate(row.date), t: StudyCore.mmss(row.sec), size: size(row.bytes) });
    const spot = el("div");
    return el("li", { "data-k": row.id }, tap(el("button", { class: "st-btn", type: "button" }, label), () => playTake(row.id, spot)), spot);
  }
  // 줄을 눌렀다: 그 녹음의 재생 주소를 받아 그 줄 아래에 재생 막대를 세운다. 녹음하는 동안에는 주소가 오지 않는다(틀지 않는다)
  function playTake(id, spot) {
    const mine = turn;
    dropPlayer();
    Promise.resolve(hear("url", id)).then(src => showPlayer(mine, spot, src), () => undefined);
  }
  function showPlayer(mine, spot, src) {
    if (ui === null || mine !== turn || typeof src !== "string" || !src.startsWith("blob:")) return;
    const player = el("audio", { controls: true, preload: "metadata", src });
    spot.replaceChildren(player);
    ui = { ...ui, player };
  }

  // ── 화면 ── 위에서부터: 개념 줄과 권고 줄 → 말하기 자리 → 14일 줄 → 쉬는 날(접힌 줄, 열어 둔 채면 그대로 둔다) → 녹음 듣기(접힌 줄)
  function paint(root, c) {
    const open = ui !== null && ui.fold.hasAttribute("open");
    const heard = ui !== null ? { listen: ui.listen, takes: ui.takes, player: ui.player } : listenParts();
    StudyApp.note(null);         // 새로 그리면 보여 주던 공유 글이 사라진다 — 알림 한 줄도 함께 치운다
    const strip = el("ol", { id: "td-strip", class: "st-strip", "aria-label": t("TD_STRIP") }, stripCells(c));
    ui = { root, top: el("div", null, topLines(c)), stage: el("div"), strip, fold: restFold(c, open), ...heard, face: null, done: null, box: null, quiet: false };
    fill(root, [ui.top, ui.stage, ui.strip, ui.fold, ui.listen]);
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
    if (recLine.d !== c.today) recLine = { d: c.today, key: null, sec: 0, nowake: false };   // 지난 날의 녹음 한 줄은 버린다
    paint(root, c);
  }
  function refresh(root, c, why) {
    if (why === "write" || ui === null) paint(root, c);
    else repaint(c);
  }
  function leave() {
    turn += 1;
    dropPlayer();
    ui = null;
  }

  StudyApp.register("today", { render, refresh, leave });

  return { _: { render, refresh, leave } };
})();
