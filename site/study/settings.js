// 공부 화면의 설정 화면 — 이 기기(이름), 상태 줄, [새로 받기].
// 문서 · 저장 공간 · 통신을 직접 만지지 않는다: 요소는 StudyApp.el로만 만들고, 기기 저장은 StudyStore의 약속된 손으로만 한다.
// 맞춤이 알리거나 값을 바꾼 뒤(refresh)에는 상태 묶음만 다시 그린다 — 쓰던 칸은 건드리지 않는다.
window.StudySettings = (() => {
  "use strict";

  let ui = null;                 // 지금 그려 둔 자리. 화면을 떠나면 null이다
  let kept = null;               // '오래 두기'의 답(true · false · 아직 모르거나 없으면 null)

  const el = (tag, attrs, ...kids) => StudyApp.el(tag, attrs, ...kids);
  const t = (key, vars) => StudyCore.t(key, vars);
  const button = (id, key) => el("button", { id, class: "st-btn", type: "button" }, t(key));
  const yesNo = v => t(v === true ? "YES" : v === false ? "NO" : "NA");

  // ── 이 기기 ── 이름을 바꾼다. 꼴이 틀리면 경고만 하고, 적지 못했어도(메모리 대역) 이번 실행 동안은 그 이름을 쓴다.
  function saveDev(input, warn) {
    const name = String(input.value).trim();
    const bad = StudyStore.setDevice(name).code === "dev";
    warn.textContent = bad ? t("NAME_BAD") : "";
    if (bad) return;
    input.value = name;
    StudyApp.refresh("set");
  }
  function devGroup(c) {
    const input = el("input", { id: "set-dev", class: "st-input", type: "text", value: c.dev, enterkeyhint: "done", autocomplete: "off",
      autocapitalize: "off", autocorrect: "off", spellcheck: "false", "aria-describedby": "set-devwarn" });
    const save = button("set-devsave", "SET_DEV_SAVE");
    const warn = el("p", { id: "set-devwarn", class: "st-warn" });
    save.addEventListener("click", () => saveDev(input, warn));
    input.addEventListener("keydown", ev => { if (ev.key === "Enter" && !ev.isComposing) saveDev(input, warn); });
    return el("section", { id: "set-g-dev", class: "st-group" }, el("h2", null, t("SET_G_DEV")), el("label", { for: "set-dev" }, t("SET_DEV")), input, save, warn);
  }

  // ── 상태 ── 줄마다 p.st-row[data-k="<줄 이름>"]. 줄의 차례가 화면의 차례다.
  function rows(c) {
    return [
      ["webapp", t("ROW_WEBAPP", { v: yesNo(c.env.standalone) })],
      ["persist", t("ROW_PERSIST", { v: yesNo(kept) })],
      ["queue", t("ROW_QUEUE", { n: StudyStore.queue().length })],
      ["version", t("ROW_VERSION", { v: StudyApp.VERSION })],
    ];
  }
  function drawRows(c) {
    ui.state.replaceChildren(el("h2", null, t("SET_G_STATE")), ...rows(c).map(row => el("p", { class: "st-row", "data-k": row[0] }, row[1])));
  }
  // '오래 두기'의 답은 늦게 온다(끝내 오지 않을 수도 있다) — 오면 적어 두고, 이 화면이 떠 있으면 줄을 다시 그린다
  function learned(v) {
    kept = v;
    if (ui !== null) drawRows(StudyApp.ctx());
  }

  // ── 화면 ── 이 기기 → 상태 → 아이콘 안내 한 줄 → [새로 받기]
  function render(root, c) {
    const reload = button("set-reload", "RELOAD");
    reload.addEventListener("click", () => StudyApp.reload());
    ui = { state: el("section", { id: "set-g-state", class: "st-group" }) };
    root.replaceChildren(devGroup(c), ui.state, el("p", { id: "set-iconnote", class: "st-dim" }, t("SET_ICON_NOTE")), reload);
    drawRows(c);
    StudyStore.persist().then(v => learned(v));
  }
  function refresh(root, c) {
    if (ui === null) render(root, c);
    else drawRows(c);
  }
  function leave() {
    ui = null;
  }

  StudyApp.register("set", { render, refresh, leave });

  return { _: { render, refresh, leave } };
})();
