// 공부 화면의 설정 화면 — 이 기기(이름 · 자동 맞춤 · 녹음), 연결(주인 · 저장소 이름 · 열쇠 · [연결 확인]), 열쇠 만들기, 상태 줄,
// 단추([지금 맞춤] [새로 받기] [녹음 모두 지우기] [이 기기에서 열쇠 지우기] [사본 비우고 다시 받기]).
// 문서 · 저장 공간 · 통신 · 녹음 보관을 직접 만지지 않는다: 요소는 StudyApp.el로만 만들고, 기기 저장은 StudyStore의, 맞춤은 StudySync의, 녹음은 StudyRecorder의 약속된 손으로만 한다.
// 열쇠는 칸에서 읽어 StudyStore.setKey에 넘기고 곧바로 칸을 비운다 — 화면 글자 · 속성 · 쓰던 글 어디에도 두지 않고, 다시 꺼내지도 않는다.
// 맞춤이 알리거나 값을 바꾼 뒤(refresh)에는 상태 줄과 단추의 글 · 켜짐만 다시 그린다 — 쓰던 칸은 건드리지 않는다.
window.StudySettings = (() => {
  "use strict";

  let ui = null;                 // 지금 그려 둔 자리. 화면을 떠나면 null이다
  let kept = null;               // '오래 두기'의 답(true · false · 아직 모르거나 없으면 null)
  let heard = null;              // 이 기기에 둔 녹음의 수와 크기({ n, bytes } · 아직 모르거나 녹음 모듈이 없으면 null)
  let gen = 0;                   // 연결 설정이 바뀌거나 화면을 떠날 때마다 오른다 — 그 전에 물은 것의 답은 버린다
  let checking = false;          // [연결 확인]의 답을 기다리는 중이다(그동안 단추는 꺼져 있다)
  let pulling = false;           // [사본 비우고 다시 받기]의 답을 기다리는 중이다

  const el = (tag, attrs, ...kids) => StudyApp.el(tag, attrs, ...kids);
  const t = (key, vars) => StudyCore.t(key, vars);
  const button = (id, key) => el("button", { id, class: "st-btn", type: "button" }, t(key));
  const yesNo = v => t(v === true ? "YES" : v === false ? "NO" : "NA");
  const tap = (node, fn) => { node.addEventListener("click", fn); return node; };
  const PLAIN = Object.freeze({ enterkeyhint: "done", autocomplete: "off", autocapitalize: "off", autocorrect: "off", spellcheck: "false" });   // 칸이 글을 채우거나 고치지 않게

  // ── 맞춤 모듈의 손 ── 쓸 때마다 다시 본다. 모듈이 없거나 던지면 undefined다(없는 대로 돈다).
  function lend(method, ...args) {
    try {
      const sync = window.StudySync;
      return sync && typeof sync[method] === "function" ? sync[method](...args) : undefined;
    } catch (err) {
      return undefined;
    }
  }
  // 녹음 모듈의 손 — 맞춤과 같다: 쓸 때마다 다시 보고, 없거나 던지면 undefined다
  function hear(method, ...args) {
    try {
      const recorder = window.StudyRecorder;
      return recorder && typeof recorder[method] === "function" ? recorder[method](...args) : undefined;
    } catch (err) {
      return undefined;
    }
  }
  // 약속을 기다린다. 약속이 아니거나 거절돼도 거절하지 않는다(undefined)
  const settled = v => Promise.resolve(v).then(r => r, () => undefined);
  // 연결 설정(멈춤 · 주인 · 저장소 이름 · 열쇠)이 바뀌었다: 기다리던 답은 버리고, 맞춤의 멈춤과 기억을 지우고, 줄과 단추를 다시 그린다
  function changed() {
    gen += 1;
    checking = false;
    pulling = false;
    if (ui !== null) ui.checkout.textContent = "";
    if (ui !== null) ui.repullnote.textContent = t("SET_REPULL_NOTE");
    lend("reset");
    StudyApp.refresh("set");
  }

  // ── 이 기기 ── 이름을 바꾼다. 꼴이 틀리면 경고만 하고, 적지 못했어도(메모리 대역) 이번 실행 동안은 그 이름을 쓴다.
  function saveDev(input, warn) {
    const name = String(input.value).trim();
    const bad = StudyStore.setDevice(name).code === "dev";
    warn.textContent = bad ? t("NAME_BAD") : "";
    if (bad) return;
    input.value = name;
    StudyApp.refresh("set");
  }
  function devGroup(c, pause) {
    const input = el("input", { id: "set-dev", class: "st-input", type: "text", value: c.dev, enterkeyhint: "done", autocomplete: "off",
      autocapitalize: "off", autocorrect: "off", spellcheck: "false", "aria-describedby": "set-devwarn" });
    const save = button("set-devsave", "SET_DEV_SAVE");
    const warn = el("p", { id: "set-devwarn", class: "st-warn" });
    save.addEventListener("click", () => saveDev(input, warn));
    input.addEventListener("keydown", ev => { if (ev.key === "Enter" && !ev.isComposing) saveDev(input, warn); });
    return el("section", { id: "set-g-dev", class: "st-group" }, el("h2", null, t("SET_G_DEV")), el("label", { for: "set-dev" }, t("SET_DEV")), input, save, warn, el("div", null, pause));
  }

  // ── 자동 맞춤 멈춤/켬 ── 멈추면 저장 · 열기 · 돌아옴 · [지금 맞춤] 어디서도 요청이 없다. 다시 켜면 곧바로 한 번 맞춘다.
  function togglePause() {
    const paused = !StudyStore.getFlag("pause");
    StudyStore.setFlag("pause", paused);
    changed();
    if (!paused) StudyApp.requestSync("manual");
  }
  // ── 녹음 켬/끔 ── 끄면 [말하기]를 눌러도 마이크를 청하지 않는다. 돌고 있던 녹음은 그 자리에서 닫는다(있는 만큼 보관된다).
  function toggleRec() {
    const on = !StudyStore.getFlag("rec");
    StudyStore.setFlag("rec", on);
    if (!on) hear("end");
    StudyApp.refresh("set");
  }
  // 단추의 글 · 눌림 · 켜짐 — 단추는 새로 만들지 않고 그 자리에서 고친다
  function drawKnobs() {
    const paused = StudyStore.getFlag("pause");
    const rec = StudyStore.getFlag("rec");
    if (ui.rec !== null) ui.rec.textContent = t("SET_REC", { v: t(rec ? "ON" : "OFF") });
    if (ui.rec !== null) ui.rec.setAttribute("aria-pressed", String(rec));
    ui.pause.textContent = t("SET_PAUSE", { v: t(paused ? "PAUSED" : "ON") });
    ui.pause.setAttribute("aria-pressed", String(paused));
    StudyApp.flag(ui.check, "disabled", checking);
    StudyApp.flag(ui.repull, "disabled", !paused || pulling);
  }

  // ── 연결 ── 주인 · 저장소 이름은 치는 즉시 적는다(꼴은 맞춤이 본다 — 어긋나면 요청이 없다). 열쇠 칸은 https로 열렸을 때만 있다.
  // 열쇠 꼴의 글(영문 · 숫자 · 밑줄이 40자 이상 이어짐)을 이 칸에 붙였으면 적지 않고 칸을 비운다 — 저장 공간 · 화면 · 주소에 열쇠가 남지 않게
  function typed(save, input) {
    const keyish = /[A-Za-z0-9_]{40}/.test(String(input.value));
    if (keyish) input.value = "";
    save(String(input.value));
    changed();
    if (keyish && ui !== null) ui.checkout.textContent = t("WARN_SECRET");
  }
  function field(id, key, value, save) {
    const input = el("input", { id, class: "st-input", type: "text", value, ...PLAIN });
    input.addEventListener("input", () => typed(save, input));
    return [el("label", { for: id }, t(key)), input];
  }
  // 열쇠 칸: 일반 글 칸에 글자 가림 모양만 준다. value 속성을 주지 않고(저장된 열쇠를 칸에 되돌려 넣지 않는다) 쓰던 글로도 두지 않는다.
  function keyField(c) {
    if (!c.env.https) return { input: null, nodes: [el("p", { id: "set-keynote", class: "st-dim" }, t("SET_KEY_HTTP"))] };
    const input = el("input", { id: "set-key", class: "st-input st-secret", type: "text", placeholder: t("SET_KEY_PH"), ...PLAIN });
    input.addEventListener("keydown", ev => { if (ev.key === "Enter" && !ev.isComposing) check(); });
    return { input, nodes: [el("label", { for: "set-key" }, t("SET_KEY")), input] };
  }
  function connGroup(key, more) {
    const conn = StudyStore.getConn();
    return el("section", { id: "set-g-conn", class: "st-group" }, el("h2", null, t("SET_G_CONN")),
      field("set-owner", "SET_OWNER", conn.owner, v => StudyStore.setOwner(v)), field("set-repo", "SET_REPO", conn.repo, v => StudyStore.setRepo(v)), key.nodes, more);
  }
  // [연결 확인]: 칸에 글이 있으면 꼴이 맞을 때만 열쇠로 적고, 어느 쪽이든 칸을 비운다. 그 뒤 저장소 정보를 한 번 읽어 결과를 한 줄로 보인다.
  function check() {
    if (ui === null || checking) return;
    const pasted = ui.key === null ? "" : String(ui.key.value).trim();
    if (ui.key !== null) ui.key.value = "";
    if (pasted !== "" && !StudyCore.keyShape(pasted)) {
      ui.checkout.textContent = t("SET_KEY_BAD");
      return;
    }
    if (pasted !== "") {
      StudyStore.setKey(pasted);
      changed();
    }
    const mine = gen;
    checking = true;
    ui.checkout.textContent = "";
    drawKnobs();
    settled(lend("checkConn")).then(r => checked(mine, r));
  }
  // 답이 왔다. 그 사이 설정이 바뀌었거나 화면을 떠났으면 버린다. 연결됐으면 곧바로 한 번 맞춘다(쌓인 줄이 올라간다).
  function checked(mine, r) {
    if (ui === null || mine !== gen) return;
    const got = r && typeof r.key === "string" ? r : { key: "CONN_NET", code: null };
    checking = false;
    ui.checkout.textContent = t(got.key, { code: got.code });
    StudyApp.refresh("set");
    if (got.key === "CONN_OK") StudyApp.requestSync("manual");
  }

  // ── 열쇠 만들기 ── 미리 채운 링크(이름 · 만료 90일 · 내용 쓰기)와 안내 일곱 줄. 링크에는 저장소의 주인 · 이름이 없다.
  const STEPS = Object.freeze([1, 2, 3, 4, 5, 6, 7]);
  function keyGroup(box) {
    const steps = el("ol", { id: "set-keysteps" }, STEPS.map(n => el("li", null, t("KEYSTEP_" + n))));
    return el("section", { id: "set-g-key", class: "st-group" }, el("h2", null, t("SET_G_KEY")), box, steps);
  }
  // 링크의 이름 칸에는 기기 이름과 이번 달이 든다 — 이름을 바꾸거나 달이 넘어갔을 때만 링크를 새로 만든다
  function drawLink(c) {
    const href = StudyCore.keyLink(c.dev, c.nowMs);
    if (ui.link !== null && ui.link.getAttribute("href") === href) return;
    const link = el("a", { id: "set-keylink", class: "st-btn", href }, t("SET_KEYLINK"));
    ui.linkbox.replaceChildren(link);
    ui = { ...ui, link };
  }
  // [이 기기에서 열쇠 지우기]: 기기를 넘기거나 유출이 의심될 때 쓴다. 열쇠 값은 다시 볼 수 없으니 지우면 새로 만들어 넣어야 한다.
  function clearKey() {
    if (ui !== null && ui.key !== null) ui.key.value = "";
    StudyStore.clearKey();
    changed();
  }

  // ── [사본 비우고 다시 받기] ── 자동 맞춤을 멈췄을 때만 눌린다. 이 기기의 달 사본을 비우고 받기만 한다(올리지 않는다. 대기 줄은 남는다).
  // 받기는 돌던 요청을 끊으므로, 기다리던 [연결 확인]의 답도 버린다.
  function repull() {
    if (ui === null || pulling || !StudyStore.getFlag("pause")) return;
    gen += 1;
    const mine = gen;
    checking = false;
    pulling = true;
    ui.repullnote.textContent = t("SET_REPULL_NOTE");
    drawKnobs();
    settled(lend("pullOnly")).then(r => pulled(mine, r));
  }
  // 받지 못했으면 까닭을 단추 아래 한 줄에 적는다. 다 받았으면 늘 있던 안내 글 그대로다.
  function pulled(mine, r) {
    if (ui === null || mine !== gen) return;
    const got = r && (r.ok === true || typeof r.key === "string") ? r : { ok: false, key: "CONN_NET", code: null };
    pulling = false;
    ui.repullnote.textContent = got.ok === true ? t("SET_REPULL_NOTE") : t(got.key, { code: got.code });
    StudyApp.refresh("set");
  }

  // ── 상태 ── 줄마다 p.st-row[data-k="<줄 이름>"]. 줄의 차례가 화면의 차례다.
  // 마지막 맞춤의 때: 오늘(KST 달력 날짜)이면 시각만, 다른 날이면 날짜도
  function when(ms, nowMs) {
    const at = StudyCore.stampT(ms);
    return (at.slice(0, 10) === StudyCore.stampT(nowMs).slice(0, 10) ? "" : at.slice(5, 10) + " ") + at.slice(11, 16);
  }
  // 마지막 오류: 상태 코드와 문구 표의 글뿐이다. 상태 코드가 까닭이 아닌 것(code 0)은 글만, 없으면 "없음"
  function lastErr(err) {
    if (err === null) return t("ROW_LASTERR", { code: t("HASNOT"), text: "" }).trim();
    return t("ROW_LASTERR", err.code === 0 ? { code: t(err.key), text: "" } : { code: err.code, text: t(err.key) }).trim();
  }
  function rows(c) {
    const s = StudyStore.syncState();
    return [
      ["webapp", t("ROW_WEBAPP", { v: yesNo(c.env.standalone) })],
      ["persist", t("ROW_PERSIST", { v: yesNo(kept) })],
      ["key", t("ROW_KEY", { v: t(StudyStore.getConn().hasKey ? "HAS" : "HASNOT") })],
      ["queue", t("ROW_QUEUE", { n: StudyStore.queue().length })],
      ["lastsync", t("ROW_LASTSYNC", { t: s.at === null ? t("NA") : when(s.at, c.nowMs) })],
      ["lasterr", lastErr(s.err)],
      ["bad", t("ROW_BAD", { n: s.bad + c.view.bad })],
      ["clash", t("ROW_CLASH", { n: c.view.clash })],
      ...(heard === null ? [] : [["rec", t("ROW_REC", { n: heard.n, size: size(heard.bytes) })]]),
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
  // 녹음의 수와 크기도 늦게 온다(64kbps가 지켜졌는지는 이 크기로 본다 — 2분에 약 1MB). 답이 없으면 줄도 없다
  const size = bytes => (bytes >= 100000 ? (bytes / 1000000).toFixed(1) + "MB" : Math.round(bytes / 1000) + "KB");
  function counted(v) {
    if (!v || !Number.isInteger(v.n) || !Number.isFinite(v.bytes)) return;
    heard = { n: v.n, bytes: v.bytes };
    if (ui !== null) drawRows(StudyApp.ctx());
  }
  function countTakes() {
    settled(hear("stats")).then(v => counted(v));
  }
  // [녹음 모두 지우기]: 되묻지 않고 곧바로 지운다. 그 뒤 수와 크기를 다시 센다
  function clearTakes() {
    settled(hear("clearAll")).then(() => countTakes());
  }

  // ── 화면 ── 이 기기 → 연결 → 열쇠 만들기 → 상태 → 아이콘 안내 한 줄 → 단추 두 줄
  function draw(c) {
    drawRows(c);
    drawKnobs();
    drawLink(c);
  }
  function render(root, c) {
    const key = keyField(c);
    ui = { state: el("section", { id: "set-g-state", class: "st-group" }),
      pause: tap(el("button", { id: "set-pause", class: "st-btn", type: "button" }), () => togglePause()),
      rec: window.StudyRecorder ? tap(el("button", { id: "set-rec", class: "st-btn", type: "button" }), () => toggleRec()) : null,
      key: key.input, check: tap(button("set-check", "SET_CHECK"), () => check()), checkout: el("p", { id: "set-checkout", role: "status" }),
      linkbox: el("p", null), link: null,
      repull: tap(button("set-repull", "SET_REPULL"), () => repull()), repullnote: el("p", { id: "set-repullnote", class: "st-dim" }, t("SET_REPULL_NOTE")) };
    const acts = [tap(button("set-syncnow", "SET_SYNCNOW"), () => StudyApp.requestSync("manual")), tap(button("set-reload", "RELOAD"), () => StudyApp.reload())];
    const wipe = ui.rec === null ? null : tap(button("set-recclear", "SET_RECCLEAR"), () => clearTakes());
    const risky = [wipe, tap(button("set-keyclear", "SET_KEYCLEAR"), () => clearKey()), ui.repull, ui.repullnote];
    root.replaceChildren(devGroup(c, [ui.pause, ui.rec]), connGroup(key, [ui.check, ui.checkout]), keyGroup(ui.linkbox), ui.state,
      el("p", { id: "set-iconnote", class: "st-dim" }, t("SET_ICON_NOTE")), el("div", null, acts), el("div", null, risky));
    draw(c);
    StudyStore.persist().then(v => learned(v));
    countTakes();
  }
  function refresh(root, c) {
    if (ui === null) render(root, c);
    else draw(c);
  }
  function leave() {
    ui = null;
    gen += 1;
    checking = false;
    pulling = false;
  }

  StudyApp.register("set", { render, refresh, leave });

  return { _: { render, refresh, leave } };
})();
