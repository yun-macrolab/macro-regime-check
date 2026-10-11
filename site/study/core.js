// 공부 화면의 순수 계산과 자료 표 — 날짜, 기록 줄의 꼴과 검증, 합치기, 보기, 상태 고르기, 공유할 글, 화면 문구.
// 문서 · 저장 공간 · 통신 · 시계 · 난수를 모른다. 시각은 인자(ms)로만 받는다. 같은 인자면 같은 값이다.
// 값은 고치지 않고 새로 만든다. 약속된 함수는 예외를 밖으로 던지지 않는다(실패는 값으로 돌려준다).
window.StudyCore = (() => {
  "use strict";

  const V = 1;
  const TALK_SEC = 120;
  const DAY_START_HOUR = 4;
  const ROUTES = Object.freeze(["today", "week", "ask", "set"]);
  const HOUR_MS = 3600000;
  const KST_MS = 9 * HOUR_MS;
  const DAY_MS = 24 * HOUR_MS;
  const WEEKDAYS = "월화수목금토일";

  const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const pad = (n, width) => String(n).padStart(width, "0");

  // ── 날짜 ── ms는 UTC 기준 밀리초, 날짜 글자는 YYYY-MM-DD. 공부 날짜는 KST 04:00에 바뀐다.
  function iso(ms) {
    const d = new Date(ms);
    return Number.isNaN(d.getTime()) ? "" : d.toISOString();
  }
  function studyDate(ms) {
    return iso(ms + KST_MS - DAY_START_HOUR * HOUR_MS).slice(0, 10);
  }
  function stampT(ms) {
    const s = iso(ms + KST_MS);
    return s === "" ? "" : s.slice(0, 19) + "+09:00";
  }
  function idTime(ms) {
    return iso(ms).replace(/[-T:.Z]/g, "");
  }
  // id 앞 17자리(UTC)의 ms. 2000~2099년의 실제 시각만 받는다(13월 · 32일 · 24시는 되돌린 글자가 달라 걸린다).
  function idMs(id) {
    const m = /^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(\d{3})/.exec(typeof id === "string" ? id : "");
    if (!m || m[1] < "2000" || m[1] > "2099") return NaN;
    const ms = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]), Number(m[4]), Number(m[5]), Number(m[6]), Number(m[7]));
    return idTime(ms) === m[0] ? ms : NaN;
  }
  // 날짜 글자의 자정(UTC) ms. 두 자리 연도로 읽히지 않게 연도를 따로 넣는다.
  function dateMs(date) {
    const p = String(date).split("-").map(Number);
    return new Date(0).setUTCFullYear(p[0], p[1] - 1, p[2]);
  }
  // 꼴을 먼저 보고 달력으로 확인한다. 연도 0000은 달력에 없는 것으로 친다.
  function isDate(s) {
    if (typeof s !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(s) || s < "0001") return false;
    return iso(dateMs(s)).slice(0, 10) === s;
  }
  function addDays(date, n) {
    return iso(dateMs(date) + n * DAY_MS).slice(0, 10);
  }
  function weekdayOf(date) {
    return (new Date(dateMs(date)).getUTCDay() + 6) % 7;
  }
  function weekOf(date) {
    return addDays(date, -weekdayOf(date));
  }
  function monthOf(date) {
    return String(date).slice(0, 7);
  }
  function prevMonth(month) {
    const y = Number(String(month).slice(0, 4));
    const m = Number(String(month).slice(5, 7));
    return m === 1 ? pad(y - 1, 4) + "-12" : pad(y, 4) + "-" + pad(m - 1, 2);
  }
  function headDate(date) {
    return String(date).slice(5) + " " + WEEKDAYS[weekdayOf(date)];
  }
  function hhmm(ms) {
    return iso(ms + KST_MS).slice(11, 16);
  }
  function mmss(sec) {
    return Math.floor(sec / 60) + ":" + pad(sec % 60, 2);
  }

  // ── 기록 줄의 꼴 ── 표(SCHEMA)의 칸 차례가 곧 직렬화 차례다. 본보기는 scripts/study_cases.json.
  const MAX_LINE_BYTES = 2000;
  const KINDS = Object.freeze(["day", "next", "rest", "week", "grade", "q", "fix"]);
  const HEAD = Object.freeze(["v", "id", "k", "d", "t", "dev"]);
  const REJECT = Object.freeze(["bytes", "json", "ver", "kind", "keys", "id", "dev", "time", "date", "month", "field", "long", "ctrl", "secret", "rule"]);
  const ID_RE = /^\d{17}-[가-힣A-Za-z0-9]{1,8}-[a-z0-9]{4}$/;
  const DEV_RE = /^[가-힣A-Za-z0-9]{1,8}$/;
  const CTRL_RE = /[\p{Cc}\p{Cs}\u2028\u2029]/u;
  const SECRET_RE = /[A-Za-z0-9_]{40}/;
  const SCHEMA = deepFreeze({
    day: [["mark", "enum", ["full", "min"]], ["sec", "int", 0, 120], ["rec", "int", 0, 120], ["stuck", "text", 0, 120]],
    next: [["text", "text", 1, 60]],
    rest: [["on", "date"]],
    week: [["wk", "date"], ["dur", "enum", ["ow", "n", "uw"]], ["cur", "enum", ["flat", "n", "steep"]], ["why", "text", 1, 160], ["wrong_if", "text", 1, 160]],
    grade: [["wk", "date"], ["ref", "id"], ["actual", "text", 1, 160], ["dur_hit", "enum", ["y", "n", "na"]], ["cur_hit", "enum", ["y", "n", "na"]], ["miss", "text", 0, 160]],
    q: [["text", "text", 1, 200], ["sec", "int", 0, 120], ["rec", "int", 0, 120], ["s_head", "bool"], ["s_two", "bool"], ["s_wrong", "bool"]],
    fix: [["ref", "id"], ["hide", "bool"]],
  });
  function deepFreeze(value) {
    if (value !== null && typeof value === "object") Object.values(value).forEach(deepFreeze);
    return Object.freeze(value);
  }

  // 검증의 차례: bytes → json → ver → kind → keys → id → dev → time → date → month → 칸(field · long · ctrl · secret) → rule.
  // 처음 걸리는 코드 하나를 돌려준다. 공백을 떼지 않고, 기기 시계와 견주지 않는다.
  function parseLine(text) {
    if (typeof text !== "string") return { ok: false, code: "json" };
    if (new TextEncoder().encode(text).length > MAX_LINE_BYTES) return { ok: false, code: "bytes" };
    let obj = null;
    try {
      obj = JSON.parse(text);
    } catch (err) {
      return { ok: false, code: "json" };
    }
    if (obj === null || typeof obj !== "object" || Array.isArray(obj)) return { ok: false, code: "json" };
    return { ok: true, obj };
  }
  function checkHead(obj, month) {
    if (!has(obj, "v") || obj.v !== 1) return "ver";
    if (!has(obj, "k") || !KINDS.includes(obj.k)) return "kind";
    const names = [...HEAD, ...SCHEMA[obj.k].map(spec => spec[0])];
    if (Object.keys(obj).length !== names.length || !names.every(name => has(obj, name))) return "keys";
    const ms = typeof obj.id === "string" && ID_RE.test(obj.id) ? idMs(obj.id) : NaN;
    if (Number.isNaN(ms)) return "id";
    if (obj.dev !== obj.id.split("-")[1]) return "dev";
    if (obj.t !== stampT(ms)) return "time";
    if (obj.d !== studyDate(ms)) return "date";
    if (month !== null && month !== undefined && monthOf(obj.d) !== month) return "month";
    return null;
  }
  // 글 칸: 꼴 → 길이(코드 포인트) → 제어 글자 → 긴 영숫자
  function checkText(value, min, max) {
    if (typeof value !== "string") return "field";
    const n = Array.from(value).length;
    if (n < min) return "field";
    if (n > max) return "long";
    if (CTRL_RE.test(value)) return "ctrl";
    return SECRET_RE.test(value) ? "secret" : null;
  }
  function checkField(spec, value) {
    const type = spec[1];
    if (type === "enum") return spec[2].includes(value) ? null : "field";
    if (type === "int") return typeof value === "number" && Number.isInteger(value) && value >= spec[2] && value <= spec[3] ? null : "field";
    if (type === "bool") return value === true || value === false ? null : "field";
    if (type === "date") return isDate(value) ? null : "field";
    if (type === "id") return typeof value === "string" && ID_RE.test(value) ? null : "field";
    return checkText(value, spec[2], spec[3]);
  }
  function checkFields(obj) {
    for (const spec of SCHEMA[obj.k]) {
      const code = checkField(spec, obj[spec[0]]);
      if (code) return code;
    }
    return null;
  }
  function checkRule(obj) {
    if (obj.k === "rest") return obj.on > obj.d ? null : "rule";
    if (obj.k === "week") return obj.wk === weekOf(obj.d) ? null : "rule";
    if (obj.k === "grade") return weekOf(obj.wk) === obj.wk && obj.wk < weekOf(obj.d) ? null : "rule";
    return null;
  }
  function checkLine(text, month) {
    const parsed = parseLine(text);
    if (!parsed.ok) return parsed;
    const code = checkHead(parsed.obj, month) || checkFields(parsed.obj) || checkRule(parsed.obj);
    return code ? { ok: false, code } : { ok: true, obj: Object.freeze(parsed.obj) };
  }

  // ── 줄 만들기 ── 화면의 저장은 모두 makeLine을 지난다. 만든 글자를 checkLine에 넣어 통과한 것만 ok다.
  function makeId(nowMs, dev, rand) {
    return idTime(nowMs) + "-" + dev + "-" + rand;
  }
  function toJson(value) {
    try {
      return JSON.stringify(value);
    } catch (err) {
      return "";
    }
  }
  // at = { nowMs, dev, rand }. 글 칸은 앞뒤 공백을 뗀 뒤 넣는다. 키 차례는 HEAD + SCHEMA[kind] 차례다.
  function makeLine(kind, fields, at) {
    if (!KINDS.includes(kind)) return { ok: false, code: "kind" };
    const src = fields || {};
    const when = at || {};
    const head = { v: V, id: makeId(when.nowMs, when.dev, when.rand), k: kind, d: studyDate(when.nowMs), t: stampT(when.nowMs), dev: when.dev };
    const cells = SCHEMA[kind].map(spec => [spec[0], spec[1] === "text" && typeof src[spec[0]] === "string" ? src[spec[0]].trim() : src[spec[0]]]);
    const text = toJson({ ...head, ...Object.fromEntries(cells) });
    const checked = checkLine(text, null);
    return checked.ok ? { ok: true, obj: checked.obj, text } : { ok: false, code: checked.code };
  }
  // 입력 중인 글의 문제: null · "empty" · "long" · "ctrl" · "secret". 앞뒤 공백을 뗀 값으로 본다. 모르는 칸은 "empty".
  function textIssue(kind, name, value) {
    const spec = KINDS.includes(kind) ? SCHEMA[kind].find(s => s[0] === name && s[1] === "text") : undefined;
    if (!spec) return "empty";
    const code = checkText(typeof value === "string" ? value.trim() : "", spec[2], spec[3]);
    return code === "field" ? "empty" : code;
  }

  // ── 이름 검증과 열쇠 만들기 링크 ── 링크에는 저장소의 주인 · 이름을 넣지 않는다.
  const KEY_LINK_BASE = "https://github.com/settings/personal-access-tokens/new";
  const OWNER_RE = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$/;
  const REPO_RE = /^[A-Za-z0-9._-]{1,100}$/;
  const KEY_RE = /^[A-Za-z0-9_]{60,255}$/;
  function devOk(s) {
    return typeof s === "string" && DEV_RE.test(s);
  }
  function ownerOk(s) {
    return typeof s === "string" && OWNER_RE.test(s);
  }
  function repoOk(s) {
    return typeof s === "string" && REPO_RE.test(s) && s !== "." && s !== "..";
  }
  // 앞뒤 공백을 뗀 값을 받는다(떼는 일은 부르는 쪽이 한다). 꼴만 본다 — 접두어는 보지 않는다.
  function keyShape(s) {
    return typeof s === "string" && KEY_RE.test(s);
  }
  // 이름 칸: note-<기기 이름>-<KST 달 YYYYMM>
  function keyLink(dev, nowMs) {
    const name = "note-" + (devOk(dev) ? dev : "") + "-" + iso(nowMs + KST_MS).slice(0, 7).replace("-", "");
    return KEY_LINK_BASE + "?name=" + encodeURIComponent(name) + "&expires_in=90&contents=write";
  }
  function safeLink(url) {
    return typeof url === "string" && url.startsWith(KEY_LINK_BASE + "?");
  }

  // ── 합치기 ── 단위는 줄 글자 전체다. 받은 줄은 다시 만들지 않고 글자 그대로 다룬다. 비교는 UTF-16 단위(기본 <).
  const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  // "\n"으로 쪼개고, 줄 끝의 "\r" 하나만 떼고, 빈 줄은 버린다
  function splitLines(fileText) {
    return String(fileText).split("\n").map(s => (s.endsWith("\r") ? s.slice(0, -1) : s)).filter(s => s !== "");
  }
  function joinLines(lines) {
    return lines.length === 0 ? "" : lines.join("\n") + "\n";
  }
  // 글자가 같은 줄은 하나로. 꼴이 맞는 줄을 id 순(같으면 글자 순)으로 앞에, 나머지(깨진 줄 · 모르는 판)를 글자 순으로 뒤에.
  function orderLines(lines, month) {
    const checked = [...new Set(lines)].map(text => ({ text, r: checkLine(text, month) }));
    const good = checked.filter(c => c.r.ok).map(c => ({ id: c.r.obj.id, text: c.text })).sort((a, b) => cmp(a.id, b.id) || cmp(a.text, b.text));
    const rest = checked.filter(c => !c.r.ok).map(c => c.text).sort(cmp);
    return [...good.map(g => g.text), ...rest];
  }
  // lines = 합집합을 차례 지은 것, toUpload = 기기에만 있는 줄, added = 원격에만 있는 줄.
  // 올리는 조건은 toUpload.length > 0 하나다(차례 · 끝 줄바꿈 · CR만 다르면 비어 있다).
  function mergeLines(local, remote, month) {
    const mine = new Set(local);
    const theirs = new Set(remote);
    return {
      lines: orderLines([...local, ...remote], month),
      toUpload: [...mine].filter(text => !theirs.has(text)),
      added: [...theirs].filter(text => !mine.has(text)),
    };
  }
  function lineDate(text) {
    const r = checkLine(text, null);
    return r.ok ? r.obj.d : null;
  }
  function lineMonth(text) {
    const d = lineDate(text);
    return d === null ? null : monthOf(d);
  }
  // 이번 달, 지난달, 대기 줄에 든 줄의 달(오름차순, 겹침 없음)
  function monthsToFetch(today, queue) {
    const now = monthOf(today);
    return [...new Set([now, prevMonth(now), ...queue.map(lineMonth).filter(m => m !== null)])].sort();
  }
  function staleQueue(queue, today) {
    return queue.some(text => (lineDate(text) || today) < today);
  }

  // ── 보기(view) ── 기기 사본에서 화면이 읽을 것을 뽑는다. id · ref 조회는 Map으로만 한다.
  // 한 사본 안에서 글자가 같은 줄은 한 번만 본다. 꼴이 맞지 않는 줄은 bad로 세고 버린다.
  // 같은 id에 글자가 다른 줄이 둘 이상이면 글자 순으로 앞선 하나만 쓰고, 나머지 수만큼 clash를 올린다.
  function collect(copies) {
    const byId = new Map();
    let bad = 0;
    let clash = 0;
    for (const copy of copies) {
      for (const text of new Set(copy.lines)) {
        const r = checkLine(text, copy.month);
        const old = r.ok ? byId.get(r.obj.id) : undefined;
        if (!r.ok) bad += 1;
        else if (old && old.text !== text) clash += 1;
        if (r.ok && (!old || text < old.text)) byId.set(r.obj.id, { text, obj: r.obj });
      }
    }
    return { byId, bad, clash };
  }
  // 가림: 대상 id마다 가장 늦은(id 순) fix 줄의 hide 값. fix를 가리키는 fix와 없는 id를 가리키는 fix는 무시한다.
  function buildView(copies) {
    const found = collect(copies);
    const all = [...found.byId.values()].map(entry => entry.obj).sort((a, b) => cmp(a.id, b.id));
    const state = new Map();
    for (const fix of all.filter(o => o.k === "fix")) {
      const target = found.byId.get(fix.ref);
      if (target && target.obj.k !== "fix") state.set(fix.ref, fix.hide);
    }
    const hidden = new Set([...state].filter(pair => pair[1]).map(pair => pair[0]));
    const recs = all.filter(o => o.k !== "fix" && !hidden.has(o.id));
    return { recs, hidden, clash: found.clash, bad: found.bad };
  }
  // 그날 도장이 둘이면 정상이 이긴다. 같은 표시면 먼저 쓴 것.
  function stampOn(view, date) {
    const days = view.recs.filter(r => r.k === "day" && r.d === date);
    return days.find(r => r.mark === "full") || days[0] || null;
  }
  function restOn(view, date) {
    const rests = view.recs.filter(r => r.k === "rest" && r.on === date);
    return { on: rests.length > 0, id: rests.length > 0 ? rests[rests.length - 1].id : null };
  }
  function cellOn(view, date) {
    const stamp = stampOn(view, date);
    if (stamp) return stamp.mark;
    return restOn(view, date).on ? "rest" : "none";
  }
  // 14칸(옛날 → 오늘). 도장이 쉼을 이긴다.
  function strip14(view, today) {
    return Array.from({ length: 14 }, (unused, i) => addDays(today, i - 13)).map(date => ({ date, cell: cellOn(view, date) }));
  }
  // 앞선 날에 적은 '내일 말할 개념' 가운데 가장 늦은 것. 그 뒤(오늘 전)에 도장이 있으면 이미 말한 것이다.
  function topicFor(view, today) {
    const nexts = view.recs.filter(r => r.k === "next" && r.d < today);
    const last = nexts[nexts.length - 1];
    if (!last) return null;
    return view.recs.some(r => r.k === "day" && r.d > last.d && r.d < today) ? null : last.text;
  }
  // 돌아오는 날 권고: 앞선 기록이 하나라도 있고, 어제 칸이 빈칸(쉼 아님)이고, 오늘 도장이 없을 때만.
  function comeback(view, today) {
    const before = view.recs.some(r => r.d < today);
    return before && cellOn(view, addDays(today, -1)) === "none" && stampOn(view, today) === null;
  }
  function weekCall(view, wk) {
    return view.recs.find(r => r.k === "week" && r.wk === wk) || null;
  }
  function gradeFor(view, wk) {
    const call = weekCall(view, wk);
    if (!call) return null;
    return view.recs.find(r => r.k === "grade" && r.wk === wk && r.ref === call.id) || null;
  }
  function recentQs(view, n) {
    return view.recs.filter(r => r.k === "q").reverse().slice(0, n);
  }

  // ── 상태 고르기 ── 위에서부터 처음 맞는 하나. s = { storeOk, hasKey, auth401, stop, code, paused, queueN, lastOkMs, amber }
  const STOP_KEYS = Object.freeze({ missing: "ST_REPO_MISSING", public: "ST_REPO_PUBLIC", file: "ST_FILE" });
  function pickStatus(s) {
    const pick = (name, key, vars, tone) => ({ name, key, vars: vars || {}, tone: tone || "" });
    if (!s.storeOk) return pick("STORE_FAIL", "ST_STORE_FAIL", null, "red");
    if (s.hasKey && s.auth401) return pick("REKEY", "ST_REKEY");
    if (s.hasKey && has(STOP_KEYS, s.stop)) return pick("REPO", STOP_KEYS[s.stop]);
    if (s.hasKey && s.paused) return pick("HALT", "ST_PAUSED");
    if (s.hasKey && s.stop === "halt") return pick("HALT", "ST_HALT", { code: s.code });
    if (s.hasKey && s.queueN > 0) return pick("QUEUE", "ST_QUEUE", { n: s.queueN }, s.amber ? "amber" : "");
    if (!s.hasKey) return pick("LOCAL", "ST_LOCAL");
    return s.lastOkMs ? pick("SYNCED", "ST_SYNCED", { t: hhmm(s.lastOkMs) }) : pick("SYNCED", "ST_SYNC_WAIT");
  }

  // ── 공유할 글 ── 줄 사이는 "\n". 가린 줄 · 기기 이름 · 저장소 이름 · 녹음 초는 넣지 않는다.
  function shareDay(view, date) {
    const stamp = stampOn(view, date);
    if (!stamp) return null;
    const mine = view.recs.filter(r => r.d === date);
    const lines = [
      t("SH_DAY", { date: headDate(date), mark: stamp.mark === "full" ? T.MARK_FULL : T.MARK_MIN }),
      ...(stamp.stuck ? [t("SH_STUCK", { text: stamp.stuck })] : []),
      ...mine.filter(r => r.k === "next").map(r => t("SH_NEXT", { text: r.text })),
      ...mine.filter(r => r.k === "q").map(r => t("SH_Q", { text: r.text })),
    ];
    return lines.join("\n");
  }
  function shareWeek(view, wk) {
    const call = weekCall(view, wk);
    if (!call) return null;
    const grade = gradeFor(view, wk);
    const word = (group, value) => T[group + "_" + value.toUpperCase()];
    const lines = [
      t("SH_WEEK", { wk, dur: word("DUR", call.dur), cur: word("CUR", call.cur) }),
      t("SH_WHY", { text: call.why }),
      t("SH_WRONG", { text: call.wrong_if }),
      ...(grade ? [t("SH_ACTUAL", { text: grade.actual }), t("SH_HIT", { dur: word("HIT", grade.dur_hit), cur: word("HIT", grade.cur_hit) })] : []),
      ...(grade && grade.miss ? [t("SH_MISS", { text: grade.miss })] : []),
    ];
    return lines.join("\n");
  }

  // ── 문구 표 ── 사용자에게 보이는 글자 전부. 코드와 테스트는 키로만 쓴다.
  const T = Object.freeze({
    // 틀 · 상태 줄
    APP_NAME: "2분 노트",
    FALLBACK: "화면을 다 받지 못했다 — 책을 덮고 2분 말한 뒤 나중에 도장",
    RELOAD: "새로 받기",
    NAV_TODAY: "오늘",
    NAV_WEEK: "주간",
    NAV_ASK: "질문",
    NAV_SET: "설정",
    ST_STORE_FAIL: "이 기기에 저장하지 못함",
    ST_REKEY: "열쇠 다시 넣기",
    ST_REPO_MISSING: "저장소를 찾지 못함",
    ST_REPO_PUBLIC: "공개 상태 — 올리지 않습니다",
    ST_FILE: "기록 파일을 읽지 못함",
    ST_HALT: "맞춤 멈춤 — 오류 {code}",
    ST_PAUSED: "맞춤 멈춤",
    ST_QUEUE: "올릴 것 {n}건",
    ST_LOCAL: "이 기기에만 저장",
    ST_SYNCED: "맞춤 {t}",
    ST_SYNC_WAIT: "맞춤 전",
    GUIDE_HEAD: "홈 화면에 추가한 뒤 아이콘으로 연다",
    GUIDE_1: "1. 아래의 공유 단추를 누른다",
    GUIDE_2: "2. '홈 화면에 추가'를 고른다('웹 앱으로 열기' 켬)",
    GUIDE_3: "3. 홈 화면의 아이콘으로 연다",
    NAME_ASK: "이 기기의 이름을 정한다(한글 · 영문 · 숫자 1~8자)",
    NAME_NOTE: "전에 쓰던 기기라면 평소 쓰던 아이콘 · 프로필로 열었는지 본다",
    NAME_SAVE: "정하기",
    NAME_BAD: "한글 · 영문 · 숫자 1~8자만 된다",
    NOTE_BIG: "이 기기의 사본이 커서 그 달은 더 받지 않는다",
    WARN_LONG: "{n}자를 넘었다",
    WARN_CTRL: "받지 않는 글자가 있다",
    WARN_SECRET: "영문 · 숫자가 길게 이어진 글은 받지 않는다",
    // 오늘
    TD_TOPIC: "오늘 말할 개념: {text}",
    TD_TOPIC_NONE: "오늘 말할 개념: 어제 배운 개념 하나",
    TD_WEEK_HINT: "이번 주 판정이 아직 없다",
    TD_ADVICE: "어제 비었다. 오늘은 최소판 하나면 된다",
    TD_TALK: "말하기 2:00",
    TD_STOP: "그만",
    TD_TALKED: "끝 · {t}",
    TD_STUCK_PH: "막힌 곳 한 줄",
    TD_NOSTUCK: "막힘 없음",
    TD_FULL: "○ 정상",
    TD_MIN: "△ 최소판",
    TD_STAMPED: "오늘 {mark} {t}",
    TD_NEXT_PH: "내일 말할 개념",
    TD_NEXT_SAVE: "적기",
    TD_NEXT_SAVED: "내일: {text}",
    TD_AGAIN: "다시 말하기",
    TD_SHARE: "공유",
    TD_STRIP: "최근 14일",
    TD_REST_FOLD: "쉬는 날",
    TD_REST1: "내일 쉼",
    TD_REST2: "모레 쉼",
    MARK_FULL: "○",
    MARK_MIN: "△",
    MARK_REST: "쉼",
    MARK_NONE: "·",
    SHARE_COPIED: "복사했다",
    SHARE_SHOWN: "아래 글을 길게 눌러 복사한다",
    SHARE_NONE: "공유할 기록이 없다",
    // 공유할 글
    SH_DAY: "{date} · 2분 말하기 {mark}",
    SH_STUCK: "막힌 곳: {text}",
    SH_NEXT: "내일 말할 개념: {text}",
    SH_Q: "질문: {text}",
    SH_WEEK: "{wk} 주 · 듀레이션 {dur} · 커브 {cur}",
    SH_WHY: "근거: {text}",
    SH_WRONG: "틀릴 조건: {text}",
    SH_ACTUAL: "실제: {text}",
    SH_HIT: "듀레이션 {dur} · 커브 {cur}",
    SH_MISS: "빗나간 이유: {text}",
    // 주간 · 질문
    WK_HEAD: "이번 주 내 판정",
    WK_DUR: "듀레이션",
    WK_CUR: "커브",
    DUR_OW: "비중 확대",
    DUR_N: "중립",
    DUR_UW: "비중 축소",
    DUR_S_OW: "확대",
    DUR_S_N: "중립",
    DUR_S_UW: "축소",
    CUR_FLAT: "플래트닝",
    CUR_N: "중립",
    CUR_STEEP: "스티프닝",
    WK_WHY_PH: "근거 한 줄",
    WK_WRONG_PH: "틀릴 조건 한 줄",
    WK_SAVE: "저장",
    WK_CONFIRM: "{dur} · {cur}으로 저장 — 고칠 수 없다",
    WK_CONFIRM_BTN: "한 번 더 눌러 저장",
    WK_MINE: "이번 주: 듀레이션 {dur} · 커브 {cur}",
    WK_LAST_HEAD: "지난주 내 판정",
    WK_LAST_NONE: "채점할 지난주 판정이 없다",
    GR_ACTUAL_PH: "실제 한 줄",
    GR_MISS_PH: "빗나간 이유 한 줄",
    HIT_Y: "맞음",
    HIT_N: "빗나감",
    HIT_NA: "판단 보류",
    GR_SAVE: "채점 저장",
    GR_SAVED: "채점함",
    ASK_PH: "가장 어려웠던 질문 한 줄",
    ASK_RULE: "고유 이름은 적지도 말하지도 않는다(A, B로)",
    ASK_HEAD: "결론 먼저",
    ASK_TWO: "근거 둘",
    ASK_WRONG: "틀릴 조건",
    ASK_SAVE: "저장",
    ASK_RECENT: "최근 질문",
    ASK_EMPTY: "아직 없다",
    ASK_HIDE: "가리기",
    // 설정
    SET_G_DEV: "이 기기",
    SET_G_CONN: "연결",
    SET_G_KEY: "열쇠 만들기",
    SET_G_STATE: "상태",
    SET_DEV: "기기 이름",
    SET_DEV_SAVE: "바꾸기",
    SET_REC: "녹음: {v}",
    SET_PAUSE: "자동 맞춤: {v}",
    ON: "켬",
    OFF: "끔",
    PAUSED: "멈춤",
    SET_OWNER: "주인",
    SET_REPO: "저장소 이름",
    SET_KEY: "열쇠",
    SET_KEY_PH: "길게 눌러 붙여 넣기",
    SET_KEY_BAD: "열쇠 꼴이 아니다 — 다시 복사해 붙여 넣는다",
    SET_KEY_HTTP: "열쇠는 배포된 주소에서만 넣는다",
    SET_CHECK: "연결 확인",
    CONN_OK: "연결됨 · 비공개",
    CONN_PUBLIC: "공개 상태 — 올리지 않습니다",
    CONN_MISSING: "저장소를 찾지 못함",
    CONN_AUTH: "열쇠 다시 넣기",
    CONN_ERR: "확인하지 못함 — 오류 {code}",
    CONN_NET: "확인하지 못함 — 통신",
    CONN_UNSET: "주인 · 저장소 이름 · 열쇠를 먼저 넣는다",
    SET_KEYLINK: "열쇠 만들기 화면 열기",
    KEYSTEP_1: "본인 확인 창이 한 번 뜬다. 여기서 로그인이 안 되면 사파리 앱에서 만들어 복사한다",
    KEYSTEP_2: "Repository access에서 Only select repositories를 고르고 기록 저장소 하나만 고른다",
    KEYSTEP_3: "권한이 Contents: Read and write 하나인지 본다",
    KEYSTEP_4: "만료가 90일인지 본다",
    KEYSTEP_5: "만들고, 창을 닫기 전에 값을 복사한다",
    KEYSTEP_6: "이 화면의 열쇠 칸에 붙여 넣고 [연결 확인]을 누른다. 저장하겠냐는 창에는 '안 함'",
    KEYSTEP_7: "github.com의 열쇠 목록에서 '저장소 1개 · Contents 읽기와 쓰기'인지 본다",
    ROW_WEBAPP: "웹앱으로 열림: {v}",
    ROW_PERSIST: "오래 두기: {v}",
    YES: "예",
    NO: "아니오",
    NA: "—",
    ROW_KEY: "열쇠: {v}",
    HAS: "있음",
    HASNOT: "없음",
    ROW_QUEUE: "올릴 것: {n}건",
    ROW_LASTSYNC: "마지막 맞춤: {t}",
    ROW_LASTERR: "마지막 오류: {code} {text}",
    ROW_BAD: "꼴이 맞지 않는 줄: {n}개",
    ROW_CLASH: "같은 id 충돌: {n}건",
    ROW_REC: "녹음: {n}개 · {size}",
    ROW_VERSION: "판: {v}",
    ERR_AUTH: "열쇠",
    ERR_MISSING: "저장소 없음",
    ERR_PUBLIC: "공개 상태",
    ERR_HALT: "요청 거절",
    ERR_SERVER: "서버",
    ERR_NET: "통신",
    ERR_TIMEOUT: "시간 초과",
    ERR_RACE: "겹침",
    ERR_FILE: "파일",
    ERR_BIG: "사본이 큼",
    SET_ICON_NOTE: "아이콘을 지우거나 다시 추가하기 전에 '올릴 것 0건'을 확인한다. 아이콘마다 저장 공간이 따로다.",
    SET_SYNCNOW: "지금 맞춤",
    SET_RECCLEAR: "녹음 모두 지우기",
    SET_KEYCLEAR: "이 기기에서 열쇠 지우기",
    SET_REPULL: "사본 비우고 다시 받기",
    SET_REPULL_NOTE: "자동 맞춤을 멈춘 뒤에만 된다",
    // 녹음
    REC_ON: "녹음 중",
    REC_OFF: "녹음 없이 진행 중",
    REC_NOWAKE: "화면이 꺼지면 녹음이 끊깁니다",
    REC_CUT: "끊김 {t}",
    REC_FAIL: "녹음 실패",
    REC_NOSTORE: "녹음 보관 불가",
    LISTEN_FOLD: "녹음 듣기",
    LISTEN_ITEM: "{date} · {t} · {size}",
    LISTEN_NONE: "녹음이 없다",
  });
  function t(key, vars) {
    if (!has(T, key)) return String(key);
    const bag = vars || {};
    return T[key].replace(/\{(\w+)\}/g, (whole, name) => (has(bag, name) ? String(bag[name]) : whole));
  }

  return {
    V, TALK_SEC, DAY_START_HOUR, ROUTES, T, t,
    studyDate, stampT, idTime, idMs, isDate, addDays, weekOf, monthOf, prevMonth, headDate, hhmm, mmss,
    MAX_LINE_BYTES, KINDS, HEAD, SCHEMA, REJECT, ID_RE, DEV_RE, checkLine,
    makeId, makeLine, textIssue,
    KEY_LINK_BASE, devOk, ownerOk, repoOk, keyShape, keyLink, safeLink,
    splitLines, joinLines, orderLines, mergeLines, lineMonth, monthsToFetch, staleQueue,
    buildView, stampOn, restOn, strip14, topicFor, comeback, weekCall, gradeFor, recentQs,
    pickStatus, shareDay, shareWeek,
  };
})();
