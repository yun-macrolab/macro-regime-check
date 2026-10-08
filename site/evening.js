/* 저녁판 — 텔레그램 공개 채널 여러 곳이 함께 다룬 주제를 규칙으로 고른 판(data/digest*.json)을 그린다 (2026-10-08, 1단계 규칙 선별판).
   index.html의 applyView()가 setView(화면 이름, 뒤에 붙은 값)를 부른다 — "#evening"이면 최신 판, "#evening/2026-10-07"이면 그날 판.
   index.html 안의 el() · getJson() · calm()을 쓴다(부를 때 이미 정의돼 있다). 자료는 이 화면에 처음 들어올 때 읽는다.

   화면에 나가는 글자는 닫혀 있다. 채널 글의 글자는 자료에 없고(digest_check가 막는다), 자료가 잘못돼도 화면이 문장을 옮기지 않게 한 번 더 거른다:
     낱말      낱말 꼴(20자 이하, 한글·영문·숫자와 · / & +)일 때만. 낱말 사전과 견주지는 않는다 — 그 검사는 digest_check의 몫
     고정 문구  아래 RULES.phrases에 있는 것만(digest_rules.py의 PHRASES와 같다)
     숫자      숫자 + 허용 단위 꼴만
     원문 링크  https://t.me/<채널>/<글 번호> 꼴이고, 주소의 채널이 그 줄의 채널과 같고, sources.json 목록에 있는 채널일 때만
     출처 라벨  sources.json(사람이 쓰는 파일)의 라벨, 이상하면 채널 이름
   글자는 전부 el()의 텍스트 노드로 넣는다. 바깥 요청은 없다(자료는 data/ 아래 JSON뿐).
   숨김 목록(digest_overrides.json)이나 출처 목록(sources.json)을 읽지 못하면 닫는 쪽으로 간다 — 항목을 가리고, 링크를 걸지 않는다. */
"use strict";
window.Evening = (() => {
  // 규칙 쪽과 같아야 하는 값 — scripts/evening/digest_rules.py · digest_schema.py가 기준이다. JSON 꼴로 두고 test_evening_site.py가 견준다
  const RULES = {
    "phrases": {
      "why_bond": "채권 채널 {n}곳", "why_analyst": "애널 채널 {n}곳", "why_personal": "개인 채널 {n}곳",
      "why_wire": "속보형 겹침", "why_cross": "채권 + 다른 그룹", "why_all": "세 그룹 모두",
      "why_grade_a": "A급 낱말", "why_result": "같은 결과 낱말 {n}곳", "why_num": "같은 숫자 {n}곳",
      "why_event": "발표일 일치", "why_auction": "입찰일 일치", "why_bond_alone": "채권 1곳 + 일정",
      "why_move": "금리 변동 큼", "why_repeat": "어제와 같은 주제", "why_fwd": "전달 글이 절반 넘음",
      "note_short": "수집 부족 — 꼭 볼 것을 비웠습니다", "note_withdrawn": "이 판은 내렸습니다",
      "note_fewer": "오늘은 {n}건", "note_none": "오늘은 기준을 넘은 묶음이 없습니다",
      "note_prev_close": "금리는 전일 종가 — 방향 표시를 비웠습니다", "note_no_rates": "금리 자료를 읽지 못했습니다",
      "note_capped": "수집 창이 96시간 상한에 걸렸습니다", "note_rerun": "같은 판을 다시 계산했습니다",
      "note_truncated": "나머지 표에서 {n}줄을 줄였습니다", "note_channels": "채널 {n}곳을 읽지 못했습니다"
    },
    "groups": {"bond": "채권", "analyst": "애널", "personal": "개인"},
    "roles": {"source": "원천", "wire": "속보형", "topic": "주제 한정", "context": "참고", "off": "제외"},
    "units": ["%p", "%", "bp", "조원", "조달러", "조", "억원", "억달러", "억", "만명", "천명", "명", "만계약", "계약", "달러", "원", "배"],
    "no_region": ["기술적", "기타"],
    "codes": {"fetch": "수신 실패", "no_preview": "미리보기 없음", "empty": "글을 읽지 못함", "title": "채널 제목이 바뀜",
              "rewind": "글 번호·시각이 거꾸로 감", "budget": "요청 예산 초과"},
    "reasons": {"broken": "채널 글의 형식이 바뀐 것으로 보여 판을 내지 않았습니다", "error": "실행이 실패해 판을 내지 못했습니다",
                "empty_streak": "꼭 볼 것이 없는 판이 여러 영업일 이어지고 있습니다"},
    "src": {"korea": "국고채 입찰 일정", "calendar": "일정표"},
    "run_kst": "17:41", "late_kst": "22:41", "edition_shift_h": 6, "show_editions": 10, "keep_days": 35,
    "min_bond_ok": 3, "min_total_ok": 16, "rows_per_channel": 5, "wire_query": "금리"
  };
  const P = RULES.phrases;
  const QUIET_NOTES = ["note_short", "note_withdrawn", "note_fewer", "note_none", "note_channels"];   // 판 머리가 아닌 자리에서 말하는 알림
  const SCORE_PARTS = [["C", "다룬 곳"], ["X", "그룹을 넘은 확인"], ["K", "낱말 등급"], ["E", "일정"], ["M", "금리 변동"], ["Y", "유튜브"],
    ["P", "감점"]];
  const HOW = [
    `텔레그램 공개 채널의 웹 미리보기를 평일 저녁에 한 번 읽습니다(예약 ${RULES.run_kst} KST — 늦게 돌 수 있어 실제 수집 시각을 위에 적습니다). ` +
      "로그인하지 않으며 누구나 볼 수 있는 미리보기 쪽만 읽습니다.",
    "채널 글의 문장은 싣지 않습니다. 미리 정한 낱말 사전의 낱말, 두 곳 이상이 똑같이 쓴 숫자와 단위, 글을 올린 시각, 원문 링크만 싣습니다. " +
      "다만 속보형·개인 채널이 혼자 쓴 글의 숫자는 한 곳만 쓴 숫자입니다(낱말 바로 곁의 숫자 하나). " +
      "무슨 내용인지는 링크를 눌러 원문에서 읽어 주세요.",
    "고르는 일은 LLM 없이 규칙이 합니다. 규칙은 몇 곳이 함께 다뤘는지를 셀 뿐이고 금리의 방향이나 강도, 매매 판단을 내지 않습니다. " +
      "낱말과 숫자만으로는 글의 뜻을 잘못 짚을 수 있습니다.",
    "이 화면은 아침 점검표의 규칙 판정과 무관한 참고 자료입니다. 시범 운영 중이라 낱말 사전과 점수 기준은 바뀔 수 있습니다."
  ];
  const TAKEDOWN = "https://github.com/yun-macrolab/macro-regime-check/issues/new?template=takedown.md";
  // 판이 늦거나 실행이 실패했을 때 무엇을 하면 되는지 — 읽는 사람이 곧 운영자다(바깥 링크는 늘리지 않고 글로만 적는다)
  const RERUN = " 저장소 Actions의 evening 실행 기록에서 원인을 볼 수 있고, 수동 실행으로 다시 돌릴 수 있습니다.";
  const UNFOLD = 10;                                                      // 나머지 표가 이 줄 수 이하면 펼쳐 둔다
  const COMMON = ["digest.json", "digest_index.json", "digest_status.json", "sources.json", "digest_overrides.json"];
  const PIECES = ["latest", "index", "status", "sources", "overrides"];        // COMMON과 같은 순서
  const HOUR = 36e5, DAY = 24 * HOUR, KST = 9 * HOUR, BEAT_MS = 6e4, REFETCH_MS = 10 * 6e4;
  const DOW = "일월화수목금토";

  // ---------- 꼴 검사 — 자료에서 온 값은 모두 여기를 거친다 ----------
  const HANDLE = "[A-Za-z][A-Za-z0-9_]{3,31}";
  const HANDLE_RE = new RegExp("^" + HANDLE + "$");
  const POST_RE = new RegExp("^https://t\\.me/(" + HANDLE + ")/([1-9]\\d{0,9})$");
  const ID_RE = new RegExp("^\\d{8}-" + HANDLE + "-[1-9]\\d{0,9}$");
  const NUM_RE = new RegExp("^-?(?:0|[1-9]\\d{0,6})(?:\\.\\d{0,2}[1-9])?(?:" + RULES.units.join("|") + ")$");
  const WORD_RE = /^[가-힣A-Za-z0-9][가-힣A-Za-z0-9 ·\/&+]{0,19}$/;
  const DATE_RE = /^\d{4}-\d{2}-\d{2}$/, HHMM_RE = /^(?:[01]\d|2[0-3]):[0-5]\d$/;
  const ISO_RE = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}):\d{2}\+09:00$/;
  const NOT_LABEL = /[<>@\\\p{Cc}\p{Cf}\p{Zl}\p{Zp}]|https?:/u;
  const PHRASE_RES = Object.entries(P).map(([code, text]) =>
    [code, new RegExp("^" + text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace("\\{n\\}", "[1-9]\\d{0,2}") + "$")]);

  const isObj = v => !!v && typeof v === "object" && !Array.isArray(v);
  const list = v => (Array.isArray(v) ? v : []);
  const own = (o, k) => typeof k === "string" && Object.prototype.hasOwnProperty.call(o, k);
  const count = v => (Number.isInteger(v) && v >= 0 && v < 1e7 ? v : null);
  const isHandle = v => typeof v === "string" && HANDLE_RE.test(v);
  const word = v => (typeof v === "string" && WORD_RE.test(v) ? v : null);
  const label = v => (typeof v === "string" && v.length > 0 && v.length <= 40 && v === v.trim() && !NOT_LABEL.test(v) ? v : null);
  const hhmm = (v, fallback) => (typeof v === "string" && HHMM_RE.test(v) ? v : fallback);
  // 숫자 + 허용 단위. 보기 좋게 정수부에 쉼표만 넣는다("4732계약" → "4,732계약")
  const num = v => (typeof v === "string" && NUM_RE.test(v)
    ? v.replace(/^(-?)(\d+)/, (_, sign, n) => sign + n.replace(/\B(?=(\d{3})+$)/g, ",")) : null);
  function phraseCode(v) {
    const hit = typeof v === "string" ? PHRASE_RES.find(([, rx]) => rx.test(v)) : null;
    return hit ? hit[0] : null;
  }
  function realDate(v) {
    if (typeof v !== "string" || !DATE_RE.test(v)) return false;
    const t = Date.parse(v + "T00:00:00Z");                               // 2월 30일 같은 없는 날짜를 브라우저마다 다르게 읽는다
    return Number.isFinite(t) && new Date(t).toISOString().slice(0, 10) === v;
  }
  // 판으로 쓸 수 있는 자료인가 — 이 화면이 아는 형식이고 날짜가 있다
  const usable = d => (isObj(d) && d.schema === 1 && realDate(d.date) ? d : null);

  // ---------- 시각 · 판 날짜 ----------
  const clock = () => Date.now();
  const dow = date => DOW[new Date(date + "T00:00:00Z").getUTCDay()];
  const md = date => `${date.slice(5)}(${dow(date)})`;                    // "10-08(목)"
  const weekday = date => "월화수목금".includes(dow(date));
  const kstDay = ms => new Date(ms + KST).toISOString().slice(0, 10);
  // 판 날짜 = (시각 − 6시간)의 한국 날짜 — digest_base.edition_date와 같다
  const editionOf = ms => kstDay(ms - RULES.edition_shift_h * HOUR);
  function stamp(iso) {                                                   // 자료의 시각(ISO +09:00) → "10-08 18:07"
    const m = typeof iso === "string" ? ISO_RE.exec(iso) : null;
    return m && realDate(m[1]) ? { iso, date: m[1], text: `${m[1].slice(5)} ${m[2]}` } : null;
  }
  function when(iso) {
    const s = stamp(iso);
    return s ? el("time", { datetime: s.iso }, s.text) : null;
  }
  // 지금까지 나왔어야 하는 가장 최근 판 날짜 — 평일 d의 마감 시각(late, 기본 22:41 KST)이 지났으면 d. 주말판은 없고 한국 휴일에는 돈다
  function dueEdition(ms, late) {
    const [h, m] = hhmm(late, RULES.late_kst).split(":").map(Number);
    for (let back = 0; back < 8; back++) {
      const day = kstDay(ms - back * DAY);
      if (weekday(day) && ms >= Date.parse(day + "T00:00:00+09:00") + (h * 60 + m) * 6e4) return day;
    }
    return null;
  }
  // 보이는 판(날짜)이 지금 기준으로 어떤가: none 판 없음 · late 나왔어야 할 판이 없다 · pending 오늘 판은 아직 수집 전 · fresh
  function judge(date, ms, late) {
    if (!realDate(date)) return { kind: "none", due: null };
    const due = dueEdition(ms, late), today = editionOf(ms);
    if (due && date < due) return { kind: "late", due };
    return weekday(today) && date < today ? { kind: "pending", due: today } : { kind: "fresh", due: null };
  }

  // ---------- 자료 읽기 ----------
  const live = { on: false, want: "", bad: false, seq: 0, timer: 0, model: null, alerts: null, body: null, said: null };
  const store = { common: null, pending: null, editions: new Map() };

  async function fetchCommon() {
    const got = await Promise.allSettled(COMMON.map(name => getJson("data/" + name)));
    const pick = i => (got[i].status === "fulfilled" && isObj(got[i].value) ? got[i].value : null);
    return { latest: usable(pick(0)), index: pick(1), status: pick(2), sources: pick(3), overrides: pick(4), at: clock() };
  }
  // 공용 자료 — 처음 한 번 읽고, 10분이 지났으면 다시 읽는다. 다시 읽다 못 받은 조각은 가진 것을 둔다(잠깐의 수신 실패로 화면이 비지 않게)
  function common() {
    if (store.common && clock() - store.common.at < REFETCH_MS) return Promise.resolve(store.common);
    if (!store.pending) store.pending = fetchCommon().then(next => {
      const old = store.common || {}, merged = { at: next.at };
      for (const k of PIECES) merged[k] = next[k] || old[k] || null;
      store.common = merged;
      store.pending = null;
      return merged;
    }, e => { store.pending = null; throw e; });
    return store.pending;
  }
  // 지난 판 하나(없으면 null). 파일 이름과 안의 날짜가 같아야 그 판이다. 읽은 판은 다시 받지 않는다
  async function edition(date) {
    if (store.editions.has(date)) return store.editions.get(date);
    let d = null;
    try { d = usable(await getJson(`data/digest/${date}.json`)); } catch (e) { d = null; }
    if (!d || d.date !== date) return null;
    store.editions.set(date, d);
    return d;
  }
  const mark = c => JSON.stringify([c.latest && [c.latest.date, c.latest.collected_at], c.status && c.status.checked_at,
    c.index && c.index.updated_at, c.overrides, !!c.sources]);

  // ---------- 화면 전환 · 다시 판정 ----------
  // index.html의 applyView()가 화면이 바뀔 때마다 부른다. 여기서 난 예외가 다른 화면의 전환을 막지 않게 삼킨다
  function setView(view, arg) {
    try { turn(view, arg); } catch (e) { /* 저녁판만 비고 나머지 화면은 그대로 돈다 */ }
  }
  function turn(view, arg) {
    if (view !== "evening") { live.on = false; return; }
    const want = realDate(arg) ? arg : "", bad = !!arg && !want;
    const same = live.on && live.model && live.want === want && live.bad === bad;
    Object.assign(live, { on: true, want, bad });
    if (!live.timer) {                                                    // 열어 둔 채 시간이 지나도 다시 판정한다
      live.timer = setInterval(beat, BEAT_MS);
      document.addEventListener("visibilitychange", beat);
    }
    if (same) paintAlerts(); else show();
  }
  async function show() {
    const ticket = ++live.seq;
    try {
      if (!store.common) paint({ loading: true });
      const c = await common();
      const past = live.want && !(c.latest && c.latest.date === live.want) ? live.want : "";
      const digest = past ? await edition(past) : c.latest;
      if (ticket === live.seq) paint({ ...c, digest, past, bad: live.bad });   // 기다리는 사이 다른 판으로 넘어갔으면 그리지 않는다
    } catch (e) {
      if (ticket === live.seq) quiet(() => paint({ failed: true }));
    }
  }
  // 1분마다, 그리고 탭으로 돌아올 때 — 알림을 지금 시각으로 다시 쓰고, 10분이 지났으면 자료를 다시 읽어 달라졌을 때만 다시 그린다
  async function beat() {
    try {
      if (!live.on || !live.model || live.model.loading) return;
      if (live.model.failed) { show(); return; }
      paintAlerts();
      const c = store.common;
      if (!c || document.visibilityState === "hidden" || clock() - c.at < REFETCH_MS) return;
      const before = mark(c);
      if (mark(await common()) !== before && live.on) show();
    } catch (e) { /* 다시 읽지 못하면 보던 판을 그대로 둔다 */ }
  }

  // ---------- 출처 목록 · 숨김 목록 ----------
  // sources.json → {채널 이름: {handle, label, group, role}}. 못 읽었으면 null — 그러면 링크를 걸지 않는다
  function directory(sources) {
    if (!isObj(sources) || !Array.isArray(sources.channels)) return null;
    return new Map(sources.channels.filter(c => isObj(c) && isHandle(c.handle))
      .map(c => [c.handle, { handle: c.handle, label: label(c.label) || c.handle, group: c.group, role: c.role }]));
  }
  // 그룹·역할 이름 — sources.json의 라벨, 없으면 규칙의 이름
  function names(sources, key) {
    const mine = list(isObj(sources) ? sources[key] : null).filter(x => isObj(x) && own(RULES[key], x.id) && label(x.label));
    return { ...RULES[key], ...Object.fromEntries(mine.map(x => [x.id, x.label])) };
  }
  // 그리는 데 쓰는 것들. hide.all이면 판의 항목을 모두 가린다: 숨김 목록을 못 읽었거나(broken), 내리기 스위치가 켜졌거나, 내린 판이거나
  function context(m) {
    const ov = m.overrides, d = m.digest, dir = directory(m.sources);
    const ok = isObj(ov) && ov.schema === 1 && typeof ov.withdraw === "boolean" && Array.isArray(ov.hide_ids)
      && Array.isArray(ov.hide_channels);
    const hide = { broken: !ok, all: !ok || ov.withdraw || (!!d && d.status === "withdrawn"),
      ids: new Set(ok ? ov.hide_ids : []), chans: new Set(ok ? ov.hide_channels : []) };
    return { dir, hide, group: names(m.sources, "groups"), role: names(m.sources, "roles"),
      label: ch => (dir && dir.has(ch) ? dir.get(ch).label : ch) };
  }
  // 새 창으로 여는 바깥 링크는 여기서만 만든다 — 연 쪽 창을 건드리지 못하고, 어디서 왔는지 넘기지 않는다
  function out(href, text, name) {
    const a = el("a", { href, target: "_blank", rel: "noopener noreferrer" }, text);
    if (name) a.setAttribute("aria-label", name);
    return a;
  }
  // 원문 링크 하나. 꼴이 어긋났거나 숨긴 채널·목록에 없는 채널이면 null, 출처 목록을 못 읽었으면 링크 없이 채널 이름만
  function source(ctx, ch, url, text, name) {
    const m = typeof url === "string" ? POST_RE.exec(url) : null;
    if (!m || m[1] !== ch || ctx.hide.chans.has(ch)) return null;
    if (!ctx.dir) return el("span", { class: "eve-meta" }, text || ch);
    const c = ctx.dir.get(ch);
    return c && c.role !== "off" ? out(url, text || c.label, name) : null;
  }

  // ---------- 알림 줄 ----------
  function alertsFor(m, ms) {
    const lines = [], say = (bad, ...parts) => lines.push(el("p", { class: bad ? "banner" : "eve-info" }, ...parts));
    if (m.loading) { say(false, "저녁판을 불러오는 중…"); return lines; }
    if (m.failed) { say(true, "저녁판 자료를 불러오지 못했습니다. 잠시 뒤 다시 열어 주세요."); return lines; }
    const d = m.digest, latest = () => el("a", { href: "#evening" }, "최신 판 보기");
    if (m.bad) say(false, "주소의 날짜를 읽을 수 없어 최신 판을 보여 줍니다.");
    if (m.past && d) say(false, `지난 판(${md(m.past)})을 보고 있습니다. `, latest());
    if (m.past && !d)
      say(true, `${md(m.past)} 판이 없습니다 — 그날 판이 나오지 않았거나 보관 기간(${RULES.keep_days}일)이 지났습니다. `, latest());
    if (!m.past) timeAlerts(m, ms, say);
    if (d) editionAlerts(d, context(m), say);
    return lines;
  }
  // 최신 판 화면에서만: 판이 없다 · 오늘 판이 아직 없다 · 최근 실행이 실패했다
  function timeAlerts(m, ms, say) {
    const d = m.digest, st = isObj(m.status) ? m.status : {}, expect = isObj(st.expect) ? st.expect : {};
    const run = hhmm(expect.run_kst, RULES.run_kst), late = hhmm(expect.late_kst, RULES.late_kst);
    const j = judge(d && d.date, ms, late), below = d ? ` 아래는 ${md(d.date)} 판입니다.` : "";
    if (j.kind === "none") say(true, "아직 판이 없습니다 — 첫 저녁 실행 전이거나 판 파일을 읽지 못했습니다.");
    if (j.kind === "late")
      say(true, `${md(j.due)} 판이 아직 없습니다 — 평일 ${run} 예약 실행이 ${late}까지 반영되지 않았습니다.` + below + RERUN);
    if (j.kind === "pending") say(false, `오늘 ${md(j.due)} 판은 평일 ${run}(KST) 수집 뒤에 나옵니다.` + below);
    const ran = st.ok === false && own(RULES.reasons, st.reason) ? stamp(st.checked_at) : null;
    if (ran && (!d || st.checked_at >= String(d.collected_at)))            // 보이는 판보다 앞선 실행의 실패는 지난 일이다
      say(true, `최근 저녁 실행(${ran.text}): ${RULES.reasons[st.reason]}.` + (st.published === false ? below : "")
        + (st.reason === "empty_streak" ? "" : RERUN));
  }
  function editionAlerts(d, ctx, say) {
    const s = isObj(d.sources) ? d.sources : {}, ok = count(s.channels_ok), total = count(s.channels_total);
    if (ctx.hide.broken) say(true, "숨김 목록(digest_overrides.json)을 읽지 못해 이 판의 항목을 가렸습니다.");
    else if (ctx.hide.all) say(true, P.note_withdrawn + ".");
    else if (d.status === "short")
      say(true, `${P.note_short}. 채권 채널 ${RULES.min_bond_ok}곳 미만이거나 전체 ${RULES.min_total_ok}곳 미만만 읽혔습니다.`);
    if (ctx.hide.all) return;
    if (ok !== null && total !== null && ok < total)
      say(false, `채널 일부를 읽지 못했습니다 — ${total}채널 중 ${ok} 읽음. 채널별 상태는 맨 아래 '출처와 수집 방식'에 있습니다.`);
    if (!ctx.dir) say(true, "출처 목록(sources.json)을 읽지 못해 원문 링크를 걸지 않았습니다.");
  }
  function paintAlerts() {
    if (!live.model || !live.alerts) return;
    const lines = alertsFor(live.model, clock()), text = lines.map(n => n.textContent).join("\n");
    if (text === live.said) return;                                       // 같은 말이면 다시 쓰지 않는다(화면 읽기가 1분마다 되풀이해 읽지 않게)
    live.said = text;
    live.alerts.replaceChildren(...lines);
  }

  // ---------- 그리기 ----------
  function paint(m) {
    live.model = m;
    if (!live.body) {                                                     // 알림 줄과 본문 자리를 한 번 만든다(붙이고 나서야 기억한다)
      const alerts = el("div", { class: "eve-alerts", role: "status" }), body = el("div", { class: "eve-body" });
      document.getElementById("evening-wrap").replaceChildren(alerts, body);
      Object.assign(live, { alerts, body, said: null });
    }
    paintAlerts();
    if (m.loading || m.failed) { live.body.replaceChildren(); return; }
    const ctx = context(m), d = m.digest;
    const parts = [d ? () => headBox(ctx, d, m.status) : null, ctx.hide.all ? null : () => editionNav(m.index, d ? d.date : "")];
    if (d && !ctx.hide.all) parts.push(() => mustSection(ctx, d), () => tomorrowSection(d), () => restSection(ctx, d),
      () => bondSection(ctx, d), () => sideSection(ctx, d), () => contextSection(ctx, d));
    parts.push(() => about(ctx, m));
    live.body.replaceChildren(...parts.map(part).filter(Boolean));
    if (!calm()) {                                                        // 판이 그려질 때 숫자가 한 번 깜박인다(움직임을 껐으면 하지 않는다)
      live.body.classList.add("eve-fresh");
      setTimeout(() => live.body.classList.remove("eve-fresh"), 1000);
    }
  }
  // 절 하나 — 자료의 어느 칸이 깨져도 그 절만 빠지고 나머지는 그린다
  function part(make) {
    if (!make) return null;
    try { return make(); } catch (e) { return el("p", { class: "empty-state" }, "이 절을 그리지 못했습니다 — 자료의 형식을 확인해야 합니다."); }
  }
  const quiet = make => { try { return make(); } catch (e) { return null; } };      // 줄 하나 — 깨졌으면 그 줄만 뺀다
  const section = (title, sub, ...children) => el("section", { class: "eve-sec" },
    el("div", { class: "section-heading" }, el("h2", {}, title), sub ? el("span", {}, sub) : null), ...children);

  // ---------- 판 머리 ----------
  function headBox(ctx, d, status) {
    const f = isObj(d.funnel) ? d.funnel : {}, s = isObj(d.sources) ? d.sources : {}, w = isObj(d.window) ? d.window : {};
    const n = v => el("strong", {}, count(v) === null ? "—" : String(v));
    const open = ctx.hide.all ? [] : [                                     // 금리와 주제가 먼저 — 폰 첫 화면에 들어오게
      part(() => ratesLine(d.head)), part(() => topTerms(d.head)),
      el("p", { class: "eve-funnel" }, "읽은 ", n(f.posts), "건 → 묶음 ", n(f.clusters), " → 후보 ", n(f.candidates), " → 꼭 ", n(f.must), "건"),
      el("p", { class: "eve-funnel" }, n(s.channels_total), "채널 중 ", n(s.channels_ok), " 읽음", unread(ctx, d, status)),
      part(() => notes(d.notes))];
    return el("section", { class: "box eve-head" },
      el("div", { class: "eve-bar" }, el("h2", {}, `저녁판 ${d.date}(${dow(d.date)})`),
        el("span", { class: "eve-badges" }, el("span", { class: "eve-badge eve-pilot" }, "시범"),
          el("span", { class: "eve-badge" }, "규칙 선별 · 문장 없음"))),
      el("div", { class: "eve-head-body" },
        el("p", {}, "수집 ", when(d.collected_at) || "시각 없음", " (KST) · 수집 창 ", when(w.from) || "?", " ~ ", when(w.to) || "?"),
        ...open));
  }
  const codeText = code => (own(RULES.codes, code) ? RULES.codes[code] : "실패");
  // 이번 판에서 읽지 못한 채널 — 상태 파일이 이 판의 것일 때만
  function unread(ctx, d, status) {
    if (!isObj(status) || status.edition !== d.date) return null;
    const lost = list(status.channels).filter(c => isObj(c) && c.ok === false && isHandle(c.ch) && !ctx.hide.chans.has(c.ch)
      && (!ctx.dir || ctx.dir.has(c.ch)));
    return lost.length ? el("small", {}, " · 읽지 못한 곳: " + lost.map(c => `${ctx.label(c.ch)}(${codeText(c.code)})`).join(", ")) : null;
  }
  function bp(v) {
    const s = v.toFixed(1);
    return (Number(s) === 0 ? "0.0" : (v > 0 ? "+" : "") + s) + "bp";
  }
  function rate(name, r) {                                                // "국고 10년 4.376% (+0.7bp) 자료일 10-08"
    if (!isObj(r) || !Number.isFinite(r.value) || r.value <= 0 || r.value >= 20) return null;
    return el("span", { class: "eve-rate" }, name + " ", el("strong", {}, r.value.toFixed(3).replace(/0$/, "") + "%"),
      Number.isFinite(r.chg_bp) ? ` (${bp(r.chg_bp)})` : null, realDate(r.asof) ? el("small", {}, " 자료일 " + r.asof.slice(5)) : null);
  }
  // 금리 한 줄. 방향(약세·강세, 스팁·플랫)은 자료에 있을 때만 — 자료일이 수집 창과 안 맞으면 조립 단계가 비워 보낸다
  function ratesLine(head) {
    const h = isObj(head) ? head : {}, kr10 = rate("국고 10년", h.kr10), kr3 = rate("국고 3년", h.kr3), us10 = rate("미 10년", h.us10);
    if (!kr10 && !kr3 && !us10) return el("p", {}, "금리 자료 없음");
    const dir = [word(h.dir), word(h.curve)].filter(Boolean).join(" · "), basis = word(h.basis);
    const turn = kr10 || kr3
      ? el("span", { class: "eve-dir" }, dir ? "→ " + dir : "방향 표시 없음", basis ? el("small", {}, " " + basis) : null) : null;
    return el("p", { class: "eve-rates" }, kr10, kr3, turn, us10);
  }
  function topTerms(head) {
    const terms = list(isObj(head) ? head.top_terms : null).map(word).filter(Boolean).slice(0, 3);
    return terms.length ? el("p", {}, "가장 많이 다뤄진 주제: ", el("strong", {}, terms.join(" · ")),
      el("small", {}, " (건수 기준 — 금리가 움직인 원인을 뜻하지 않습니다)")) : null;
  }
  function notes(raw) {
    const lines = list(raw).filter(t => { const code = phraseCode(t); return code && !QUIET_NOTES.includes(code); });
    return lines.length ? el("ul", { class: "eve-notes", "aria-label": "이 판의 알림" }, ...lines.map(t => el("li", {}, t))) : null;
  }
  // 지난 판 넘기기 — 최근 10영업일. 맨 앞(최신)은 "#evening", 나머지는 "#evening/<날짜>"
  function editionNav(index, shown) {
    const rows = list(isObj(index) ? index.editions : null).filter(e => isObj(e) && realDate(e.date))
      .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0)).slice(0, RULES.show_editions);
    if (!rows.length) return null;
    const latest = rows[0].date;
    return el("nav", { class: "eve-editions", "aria-label": "지난 판 넘기기" }, ...rows.map(e => {
      const tail = e.status === "short" ? "수집 부족" : e.status === "withdrawn" ? "내림" : count(e.must) === null ? "" : `꼭 ${e.must}`;
      const a = el("a", { href: e.date === latest ? "#evening" : "#evening/" + e.date }, md(e.date),
        tail ? el("small", {}, " " + tail) : null);
      if (e.date === shown) a.setAttribute("aria-current", "page");
      return a;
    }));
  }

  // ---------- 항목 ----------
  function cellName(cell) {                                               // {요인, 지역} → "펀더멘털 / 글로벌". 없으면 null(분류 보류)
    const factor = isObj(cell) ? word(cell.factor) : null, region = isObj(cell) ? word(cell.region) : null;
    if (!factor || !region) return null;
    return RULES.no_region.includes(factor) ? factor : `${factor} / ${region}`;
  }
  const cellTag = name => el("span", { class: name ? "eve-cell" : "eve-cell eve-hold" }, name || "분류 보류");
  function numRow(n) {
    const v = isObj(n) ? num(n.v) : null;
    return v ? { v, lead: [word(n.term), word(n.result)].filter(Boolean).join(" · "), n: count(n.n_ch) } : null;
  }
  function coverText(ctx, c) {                                            // "채권 3 · 애널 2 · 개인 3 · 속보형 1"
    if (!isObj(c)) return "";
    const rows = Object.keys(RULES.groups).map(g => [ctx.group[g], count(c[g])]).concat([[ctx.role.wire, count(c.wire)]]);
    return rows.filter(([, n]) => n).map(([name, n]) => `${name} ${n}`).join(" · ");
  }
  // 꼭 볼 것·나머지 항목에서 화면에 쓸 것만 추린다. id가 이상하거나, 숨긴 항목이거나, 걸 수 있는 링크가 하나도 없으면 null
  function item(ctx, x) {
    if (!isObj(x) || typeof x.id !== "string" || !ID_RE.test(x.id) || ctx.hide.ids.has(x.id)) return null;
    const links = list(x.links).filter(isObj).map(l => ({ node: source(ctx, l.ch, l.url), at: when(l.at), fwd: l.fwd === true }))
      .filter(l => l.node);
    if (!links.length) return null;
    return { raw: x, links, cell: cellName(x.cell), cover: coverText(ctx, x.coverage),
      terms: list(x.terms).map(word).filter(Boolean).slice(0, 4), nums: list(x.nums).map(numRow).filter(Boolean).slice(0, 3) };
  }
  const items = (ctx, raw) => list(raw).map(x => quiet(() => item(ctx, x))).filter(Boolean);
  const termNodes = terms => (terms.length
    ? [el("strong", {}, terms[0]), terms.length > 1 ? " · " + terms.slice(1).join(" · ") : null] : ["낱말 없음"]);
  const linkNodes = it => it.links.flatMap((l, i) => [i ? " · " : null, l.node, l.at ? " " : null, l.at]);

  // ---------- 꼭 볼 것 ----------
  function mustSection(ctx, d) {
    const shown = items(ctx, d.must), n = shown.length, lost = list(d.must).length - n;
    const sub = n >= 3 ? "여러 곳이 함께 다룬 묶음 가운데 기준을 모두 넘은 것"
      : n ? `${P.note_fewer.replace("{n}", n)} — 기준을 넘은 묶음만 싣습니다` : null;
    const why = d.status === "short" ? P.note_short : lost ? "표시할 수 있는 항목이 없습니다" : P.note_none;
    const where = d.status === "ok" && !lost ? " 아래 '채권 채널 단독 글'과 '나머지'에서 채널들이 쓴 낱말을 볼 수 있습니다." : "";
    return section(n ? `꼭 ${n}건` : "꼭 볼 것", sub,
      n ? el("ol", { class: "eve-must" }, ...shown.map((it, i) => el("li", {}, mustCard(it, i + 1))))
        : el("p", { class: "empty-state" }, why + "." + where),
      lost > 0 ? el("p", { class: "reading-note" }, `표시하지 않은 항목 ${lost}건 — 숨김 목록에 있거나 자료의 형식이 맞지 않습니다.`) : null);
  }
  function mustCard(it, rank) {
    const why = list(it.raw.why).filter(phraseCode).slice(0, 4);
    return el("article", { class: "eve-item" },
      el("div", { class: "eve-item-head" }, el("span", { class: "eve-rank", "aria-hidden": "true" }, String(rank)), cellTag(it.cell)),
      el("h3", { class: "eve-terms" }, ...termNodes(it.terms)),
      it.nums.length ? el("ul", { class: "eve-nums", "aria-label": "두 곳 이상이 똑같이 쓴 숫자" }, ...it.nums.map(n => el("li", {},
        n.lead ? el("span", {}, n.lead + " · ") : null, el("strong", {}, n.v), n.n ? el("small", {}, ` ${n.n}곳`) : null))) : null,
      why.length ? el("ul", { class: "eve-why", "aria-label": "고른 이유" }, ...why.map(t => el("li", {}, t))) : null,
      it.cover ? el("p", { class: "eve-cover" }, "다룬 곳 ", el("strong", {}, it.cover)) : null,
      el("ul", { class: "eve-links", "aria-label": "원문 링크" }, ...it.links.map(l => el("li", {}, l.node, l.at ? " " : null, l.at,
        l.fwd ? el("span", { class: "eve-fwd" }, "전달") : null))),
      quiet(() => scoreFold(it.raw.score)));
  }
  // 규칙 점수 — 여러 곳이 함께 다뤘는지를 센 값이다(방향·강도가 아니다). 접어 둔다
  function scoreFold(s) {
    if (!isObj(s) || !Number.isFinite(s.total)) return null;
    const show = v => String(Math.round(v * 1000) / 1000);
    const rows = SCORE_PARTS.filter(([k]) => Number.isFinite(s[k]) && (s[k] !== 0 || "CXKE".includes(k)))
      .map(([k, name]) => el("div", {}, el("dt", {}, name), el("dd", {}, (k === "P" && s[k] ? "-" : "") + show(s[k]))));
    return el("details", { class: "eve-score" }, el("summary", {}, "규칙 점수 ", el("strong", {}, show(s.total)), " · 항별 보기"),
      el("dl", {}, ...rows), el("p", {}, "여러 곳이 함께 다뤘는지를 센 값입니다. 금리의 방향이나 강도가 아닙니다."));
  }

  // ---------- 내일 볼 것 · 나머지 · 채권 단독 ----------
  function tomorrowSection(d) {
    const rows = list(d.tomorrow).map(e => quiet(() => dayRow(e))).filter(Boolean);
    return rows.length ? section("다가오는 일정", "발표·입찰 — 수집이 끝난 뒤의 오늘 일정부터", el("ul", { class: "eve-rows eve-boxed" }, ...rows))
      : null;
  }
  function dayRow(e) {
    if (!isObj(e) || !realDate(e.date) || !word(e.term)) return null;
    const detail = list(e.detail).map(x => word(x) || num(x)).filter(Boolean).join(" · ");
    return el("li", {}, el("time", { datetime: e.date }, md(e.date) + (hhmm(e.time, "") ? " " + e.time : "")),
      el("span", { class: "eve-main" }, el("strong", {}, e.term), detail ? " · " + detail : null),
      e.tier === "A" || e.tier === "B" ? el("span", { class: "eve-badge" }, e.tier + "급") : null,
      own(RULES.src, e.src) ? el("span", { class: "eve-meta" }, RULES.src[e.src]) : null);
  }
  // 채권 채널 한 곳만 쓴 글은 나머지 표에서 따로 떼어 보여 준다
  const bondAlone = it => { const c = it.raw.coverage; return isObj(c) && c.bond === 1 && !c.analyst && !c.personal; };
  function restGroups(ctx, d) {
    return list(d.rest).filter(isObj).map(g => ({ cell: word(g.cell), items: items(ctx, g.items) })).filter(g => g.items.length);
  }
  function restRow(it, withCell) {
    const n = it.nums[0], s = it.raw.s;
    return el("li", {},
      el("span", { class: "eve-main" }, withCell ? cellTag(it.cell) : null, withCell ? " " : null, ...termNodes(it.terms)),
      n ? el("span", { class: "eve-v" }, n.lead ? n.lead + " " : null, el("strong", {}, n.v)) : null,
      it.cover ? el("span", { class: "eve-meta" }, it.cover) : null,
      Number.isFinite(s) ? el("span", { class: "eve-meta" }, `점수 ${Math.round(s * 100) / 100}`) : null,
      el("span", { class: "eve-row-links" }, ...linkNodes(it)));
  }
  function restSection(ctx, d) {
    const groups = restGroups(ctx, d).map(g => ({ ...g, items: g.items.filter(it => !bondAlone(it)) })).filter(g => g.items.length);
    const total = groups.reduce((n, g) => n + g.items.length, 0), cut = count(isObj(d.funnel) ? d.funnel.truncated : null);
    if (!total) return null;
    const fold = total > UNFOLD ? { class: "eve-fold" } : { class: "eve-fold", open: "" };       // 몇 줄 안 되면 펼쳐 둔다
    return section("나머지", `${total}줄 · 분류 칸별` + (total > UNFOLD ? "로 접혀 있습니다" : ""), ...groups.map(g => el("details", fold,
      el("summary", {}, el("strong", {}, g.cell || "분류 보류"), ` ${g.items.length}줄`,
        el("small", {}, g.items.map(it => it.terms[0]).filter(Boolean).slice(0, 3).join(" · "))),
      el("ul", { class: "eve-rows" }, ...g.items.map(it => restRow(it, false))))),
      cut ? el("p", { class: "reading-note" }, P.note_truncated.replace("{n}", cut) + ".") : null);
  }
  function bondSection(ctx, d) {
    const alone = restGroups(ctx, d).flatMap(g => g.items.filter(bondAlone));
    const named = alone.filter(it => it.terms.length), bare = alone.filter(it => !it.terms.length);   // 낱말 없는 글은 한데 접는다
    return alone.length ? section("채권 채널 단독 글", "채권 채널 한 곳만 쓴 글 — 낱말과 링크만",
      named.length ? el("ul", { class: "eve-rows eve-boxed" }, ...named.map(it => restRow(it, true))) : null,
      bare.length ? el("details", { class: "eve-fold" }, el("summary", {}, el("strong", {}, `낱말 없는 글 ${bare.length}건`), " 링크만"),
        el("ul", { class: "eve-rows" }, ...bare.map(it => restRow(it, false)))) : null) : null;
  }

  // ---------- 속보형 · 개인 단독 · 참고 ----------
  function sideRow(ctx, r) {
    const v = isObj(r) ? num(r.v) : null, term = v ? word(r.term) : null, at = term ? stamp(r.at) : null;
    const link = term ? source(ctx, r.ch, r.url, "원문", `${ctx.label(r.ch)} 원문${at ? " " + at.text : ""}`) : null;
    if (!link) return null;
    return { ch: r.ch, node: el("li", {}, when(r.at),
      el("span", { class: "eve-main" }, [term, word(r.result)].filter(Boolean).join(" · "), " ", el("strong", {}, v)), link) };
  }
  function sideBlock(ctx, side, title, note) {
    if (!isObj(side)) return null;
    const rows = list(side.rows).map(r => quiet(() => sideRow(ctx, r))).filter(Boolean);
    const chans = list(side.channels).filter(c => isObj(c) && isHandle(c.ch) && count(c.read) !== null && !ctx.hide.chans.has(c.ch)
      && (!ctx.dir || ctx.dir.has(c.ch)));
    if (!chans.length) return null;
    const mine = c => rows.filter(r => r.ch === c.ch).map(r => r.node);
    const loud = chans.filter(c => mine(c).length), still = chans.filter(c => !mine(c).length);
    const more = c => [count(c.joined) === null ? null : `다른 채널과 겹친 글 ${c.joined}`,
      count(c.hit) === null ? null : `조건에 맞은 단독 글 ${c.hit}`].filter(Boolean).join(" · ");
    return el("div", { class: "eve-side" }, el("h3", {}, title), note ? el("p", { class: "eve-quiet" }, note) : null,
      ...loud.map(c => el("div", { class: "eve-side-ch" },
        el("p", {}, el("strong", {}, ctx.label(c.ch)), ` ${c.read}건 중 ${mine(c).length}건`, more(c) ? el("small", {}, " · " + more(c)) : null),
        el("ul", { class: "eve-rows" }, ...mine(c)))),
      still.length ? el("p", { class: "eve-quiet" }, "줄 없이 건수만: " + still.map(c => `${ctx.label(c.ch)} ${c.read}건`).join(" · ")) : null);
  }
  function sideSection(ctx, d) {
    const searched = `건수는 하루 전체가 아니라 검색어 '${RULES.wire_query}'에 걸린 글 수입니다.`;
    const blocks = [quiet(() => sideBlock(ctx, d.wire, "속보형 채널", searched)), quiet(() => sideBlock(ctx, d.solo, "개인 채널"))]
      .filter(Boolean);
    return blocks.length ? section("속보형·개인 채널이 혼자 쓴 글",
      `한 곳만 쓴 숫자입니다 — 첫머리에서 주요 낱말 바로 곁에 숫자가 있는 글만 채널당 ${RULES.rows_per_channel}줄까지, 나머지는 건수만`,
      ...blocks) : null;
  }
  function contextSection(ctx, d) {
    const rows = list(d.context).filter(isObj).map(x => ({ link: source(ctx, x.ch, x.url), at: when(x.at) })).filter(r => r.link)
      .map(r => el("li", {}, r.at, el("span", { class: "eve-main" }, r.link)));
    return rows.length ? section("참고 링크", "점수에 넣지 않는 시황 채널의 글", el("ul", { class: "eve-rows eve-boxed" }, ...rows)) : null;
  }

  // ---------- 출처와 수집 방식 ----------
  function channelList(ctx, status) {
    if (!ctx.dir) return el("p", {}, "출처 목록을 읽지 못했습니다.");
    const health = new Map(list(status && status.channels).filter(c => isObj(c) && isHandle(c.ch)).map(c => [c.ch, c]));
    const state = h => (!h ? "" : h.ok === false ? ` · 이번 판에서 읽지 못함(${codeText(h.code)})`
      : count(h.in_window) === null ? "" : ` · 창 안 글 ${h.in_window}건`);
    const row = c => el("li", {}, out("https://t.me/" + c.handle, c.label), " ",
      el("small", {}, (own(ctx.role, c.role) ? ctx.role[c.role] : "") + state(health.get(c.handle))));
    const all = [...ctx.dir.values()].filter(c => !ctx.hide.chans.has(c.handle));
    return el("div", {}, ...Object.keys(RULES.groups).map(g => [g, all.filter(c => c.group === g)]).filter(([, cs]) => cs.length)
      .flatMap(([g, cs]) => [el("h4", {}, `${ctx.group[g]} ${cs.length}곳`), el("ul", { class: "eve-chans" }, ...cs.map(row))]));
  }
  function about(ctx, m) {
    const d = m.digest, status = isObj(m.status) && d && m.status.edition === d.date ? m.status : null;
    return el("details", { class: "eve-about" }, el("summary", {}, "출처와 수집 방식"),
      el("h3", {}, "수집 방식"), ...HOW.map(t => el("p", {}, t)),
      el("h3", {}, "삭제·정정 요청"),
      el("p", {}, "채널 운영자가 요청하면 그 채널을 목록에서 내립니다. 잘못 실린 것이 있으면 알려 주세요 — ", out(TAKEDOWN, "GitHub 이슈로 요청하기")),
      el("h3", {}, "채널 목록"), part(() => channelList(ctx, status)));
  }

  return { setView, _: { editionOf, dueEdition, judge, num, word, label, phraseCode } };
})();
