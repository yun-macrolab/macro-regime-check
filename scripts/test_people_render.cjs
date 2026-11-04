// 연준 인물 페이지(site/people.js)의 자동 분류 발언 칸 — 아주 작은 가짜 DOM 위에서 저장소의 people-data.js와 people.js를 그대로 돌리고,
// 가짜 fetch로 지어낸 data/people_remarks.json을 준다. 발언 · 출처는 지어낸 것이다.
// 실행: node --test scripts/test_people_render.cjs
// 보는 것: 머리 띠(최신 10개, 이름을 누르면 그 사람 파일) · 사람 파일의 칸(최신 8개 + 접기) · 고정 문구 · 틀린 발언은 그것만 빠짐 ·
// 머리의 꼴이 틀리거나 파일이 없거나 받지 못하면 '자동 발언 기록 없음' 한 줄 · 한 번만 · 같은 출처 · no-store로 읽음 · 글은 글자로만.
// 모양(칩 색 · 좁은 화면)은 여기서 볼 수 없다 — 그건 브라우저로 확인한다.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ROOT = path.join(__dirname, '..');
const read = name => fs.readFileSync(path.join(ROOT, 'site', name), 'utf8');
const HTML = read('people.html'), DATA_JS = read('people-data.js'), JS = read('people.js');
const IDS = [...HTML.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]);

class Text { constructor(t) { this.data = String(t); this.parent = null; } get nodeType() { return 3; } get textContent() { return this.data; } }
class Elem {
  constructor(tag, doc) {
    this.tag = tag; this.doc = doc; this.attrs = {}; this.kids = []; this.parent = null; this.on = {}; this.dataset = {};
    this.style = { setProperty() {} };
    const self = this;
    this.classList = {
      add: (...c) => { const s = new Set(self.cls()); c.forEach(x => s.add(x)); self.attrs.class = [...s].join(' '); },
      remove: (...c) => { self.attrs.class = self.cls().filter(x => !c.includes(x)).join(' '); },
      toggle: (c, on) => { const has = self.cls().includes(c); if (on === undefined ? !has : on) self.classList.add(c); else self.classList.remove(c); },
      contains: c => self.cls().includes(c)
    };
    this.offsetWidth = 800; this.offsetHeight = 40; this.clientWidth = 800;
  }
  get nodeType() { return 1; }
  cls() { return (this.attrs.class || '').split(' ').filter(Boolean); }
  set className(v) { this.attrs.class = String(v); }
  get className() { return this.attrs.class || ''; }
  set innerHTML(v) { throw new Error('innerHTML을 쓰면 안 된다'); }
  setAttribute(k, v) {
    this.attrs[k] = String(v);
    if (k.startsWith('data-')) this.dataset[k.slice(5).replace(/-(\w)/g, (_, c) => c.toUpperCase())] = String(v);
    if (k === 'id') this.doc.ids[v] = this;
  }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  removeAttribute(k) { delete this.attrs[k]; }
  adopt(x) { const n = x instanceof Elem || x instanceof Text ? x : new Text(x); n.parent = this; return n; }
  append(...xs) { for (const x of xs) this.kids.push(this.adopt(x)); }
  appendChild(x) { this.append(x); return x; }
  replaceChildren(...xs) { this.kids = []; this.append(...xs); }
  after(...xs) { const at = this.parent.kids.indexOf(this); this.parent.kids.splice(at + 1, 0, ...xs.map(x => this.parent.adopt(x))); }
  addEventListener(type, fn) { (this.on[type] = this.on[type] || []).push(fn); }
  click() { for (const fn of this.on.click || []) fn({ preventDefault() {} }); }
  get textContent() { return this.kids.map(k => k.textContent).join(''); }
  set textContent(v) { this.kids = [this.adopt(String(v))]; }
  get isConnected() { let n = this; while (n.parent) n = n.parent; return n === this.doc.root; }
  querySelectorAll() { return []; }
  querySelector() { return null; }
  getBoundingClientRect() { return { top: 0, left: 0, right: 800, bottom: 600, width: 800, height: 600, x: 0, y: 0 }; }
  getBBox() { return { x: 0, y: 0, width: 40, height: 12 }; }
  getTotalLength() { return 100; }
  focus() { this.doc.activeElement = this; }
  blur() {} scrollIntoView() {}
}
const all = (node, pred, out = []) => { if (node instanceof Elem) { if (pred(node)) out.push(node); node.kids.forEach(k => all(k, pred, out)); } return out; };
const byClass = (node, c) => all(node, n => n.cls().includes(c));
const settle = async () => { for (let i = 0; i < 6; i++) await new Promise(r => setImmediate(r)); };

function boot(answer, hash = '') {
  const doc = { ids: Object.create(null), activeElement: null };
  doc.root = new Elem('html', doc);
  const body = new Elem('body', doc); doc.root.append(body);
  for (const id of IDS) { const n = new Elem(id === 'dmap' ? 'svg' : 'div', doc); n.setAttribute('id', id); body.append(n); }
  doc.documentElement = doc.root; doc.body = body;
  doc.createElement = tag => new Elem(tag, doc);
  doc.createElementNS = (ns, tag) => new Elem(tag, doc);
  doc.createTextNode = t => new Text(t);
  doc.getElementById = id => { const n = doc.ids[id]; return n && n.isConnected ? n : null; };
  doc.querySelector = sel => { const n = new Elem('span', doc); return sel === '.skip' || sel === '.mark' ? n : null; };
  doc.querySelectorAll = () => [];
  doc.addEventListener = () => {};
  const calls = [];
  const fetch = async (url, opts) => {
    calls.push({ url, opts });
    if (answer instanceof Error) throw answer;
    if (typeof answer === 'number') return { ok: false, status: answer, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => JSON.parse(JSON.stringify(answer)) };
  };
  const store = new Map();
  const scope = {
    document: doc, fetch, AbortController, setTimeout, clearTimeout, console, performance,
    setInterval: () => 0, requestAnimationFrame: () => 0, cancelAnimationFrame() {},
    getComputedStyle: () => ({ paddingLeft: '0px', paddingRight: '0px' }),
    matchMedia: () => ({ matches: false }), innerWidth: 1280, innerHeight: 800, addEventListener() {},
    localStorage: { getItem: k => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, String(v)) },
    location: { hash }, history: { replaceState: (a, b, h) => { scope.location.hash = h; } }
  };
  scope.window = scope;
  vm.createContext(scope);
  vm.runInContext(DATA_JS, scope, { filename: 'people-data.js' });
  vm.runInContext(JS, scope, { filename: 'people.js' });
  return { doc, calls, scope, strip: () => doc.getElementById('rm-strip'), sec: () => doc.getElementById('sec-new') };
}

const PEOPLE = (() => { const s = { window: {} }; vm.runInNewContext(DATA_JS, s); return s.window.PEOPLE_DATA.people; })();
const name = k => PEOPLE.find(p => p.key === k).name_ko;
const rid = (w, d, v) => crypto.createHash('sha1').update(`${w}|${d}|${v}`, 'utf8').digest('hex').slice(0, 12);
function remark(who, said_on, venue = '연설', more = {}) {
  return Object.assign({ id: rid(who, said_on, venue), who, said_on, venue, access: '직접', topic: `${who} 주제 ${said_on}`,
    quote: 'rates find the cracks', vs_base: '평소와 같음', basis: [{ path: 'baseline.usual[0]', text: '늘 하는 말' }],
    why: '늘 하던 말', conditional: '', dissent: '', source: '지어낸 매체', title: '지어낸 제목', tags: ['기준선 초안'],
    baseline_asof: '2026-10-31', baseline_review: 'draft' }, more);
}
const day = i => new Date(Date.UTC(2026, 10, 3) - i * 864e5).toISOString().slice(0, 10);
function file(list, more = {}) {
  return Object.assign({ schema: 'people-remarks/1', asof: '2026-11-04', window_from: '2025-11-04', remarks: list, held: 2 }, more);
}
// 워시 12개(하루씩), 쿡 · 해맥 하나씩 — 쿡은 반대표 · 매파, 해맥은 전언 · 조건 · 블랙아웃 꼬리표
const MANY = [...Array.from({ length: 12 }, (_, i) => remark('warsh', day(i + 1))),
  remark('cook', '2026-11-03', '투표', { quote: '', vs_base: '평소보다 매파', dissent: '인상', topic: '10월 결정' }),
  remark('hammack', '2026-10-01', '인터뷰', { access: '전언', vs_base: '새 주제', conditional: '물가가 다시 오르면',
    tags: ['블랙아웃 중 — 전언 확인', '기준선 초안'], basis: [{ path: 'baseline.not_news[0]', text: '자금시장' }, { path: 'baseline.usual[1]', text: '물가' }] })];

test('page strip shows the latest ten with the fixed label, newest first', async () => {
  const t = boot(file(MANY));
  assert.equal(t.calls.length, 1);
  assert.equal(t.calls[0].url, 'data/people_remarks.json');
  assert.equal(t.calls[0].opts.cache, 'no-store');
  await settle();
  const strip = t.strip();
  assert.ok(strip, '띠가 주의 줄 바로 뒤에 붙는다');
  const caveat = t.doc.getElementById('caveat');
  assert.equal(caveat.parent.kids[caveat.parent.kids.indexOf(caveat) + 1], strip);
  const text = strip.textContent;
  assert.match(text, /^최근 발언 — 기준선 대비\(자동 분류\)/);
  assert.match(text, /2026-11-04 기준 · 14건 · 보류 2/);
  assert.match(text, /자동 분류 — 운영 규칙이 기준선\(사람마다 기준일 · 확인함\/초안\)에 견준 결과이고 사람 확인 없이 매일 올라갑니다\. 예측이 아닙니다\. 인용은 발언자 본인의 말을 15단어 이내로 옮긴 것입니다\./);
  const rows = byClass(strip, 'rm-row');
  assert.equal(rows.length, 10);
  const dates = rows.map(r => r.kids[0].textContent);
  assert.deepEqual(dates, [...dates].sort().reverse());
  assert.equal(rows[0].kids[0].textContent, '2026-11-03');
  assert.deepEqual(rows.slice(0, 2).map(r => byClass(r, 'rm-who')[0].textContent), [name('cook'), name('warsh')]);   // 같은 날은 사람 순
  assert.match(rows[0].textContent, /투표.*▲ 평소보다 매파.*10월 결정/);
  assert.match(rows[1].textContent, /“rates find the cracks”/);
});

test('a name in the strip opens that person file', async () => {
  const t = boot(file(MANY));
  await settle();
  const btn = byClass(t.strip(), 'rm-who').find(b => b.dataset.key === 'cook');
  assert.equal(btn.tag, 'button');
  assert.equal(btn.attrs.type, 'button');
  btn.click();
  assert.equal(t.doc.getElementById('file').attrs['aria-label'], `${name('cook')} 파일`);
  assert.equal(t.scope.location.hash, '#cook');
  const sec = t.sec();
  assert.match(sec.textContent, /새 발언 — 기준선 대비\(자동 분류\)1건/);
  const card = byClass(sec, 'rm')[0];
  assert.match(card.textContent, /2026-11-03투표▲ 평소보다 매파반대표 ▲ 인상기준선 초안/);
  assert.ok(card.cls().includes('hawk'));
  assert.equal(byClass(card, 'rm-quote').length, 0);                         // 인용이 빈 발언은 인용 줄이 없다
});

test('person file shows eight newest and folds the rest', async () => {
  const t = boot(file(MANY));
  await settle();
  const sec = t.sec();                                                        // 처음 연 파일은 워시
  assert.equal(t.doc.getElementById('file').attrs['aria-label'], `${name('warsh')} 파일`);
  assert.match(sec.textContent, /^새 발언 — 기준선 대비\(자동 분류\)12건자동 분류 — 운영 규칙이 기준선\(2026-10-31 · 초안\)에 견준 결과이고 사람 확인 없이 매일 올라갑니다\./);
  const lists = byClass(sec, 'rm-list');
  assert.equal(lists.length, 2);
  assert.equal(lists[0].kids.length, 8);
  const more = byClass(sec, 'rm-more')[0];
  assert.equal(more.tag, 'details');
  assert.equal(more.kids[0].tag, 'summary');
  assert.equal(more.kids[0].textContent, '나머지 4건');
  assert.equal(lists[1].kids.length, 4);
  const first = lists[0].kids[0];
  assert.equal(byClass(first, 'rm-meta')[0].kids[0].textContent, '2026-11-02');
  assert.equal(byClass(first, 'rm-quote')[0].textContent, '“rates find the cracks”');
  assert.equal(byClass(first, 'rm-quote')[0].attrs.lang, 'en');
  assert.equal(byClass(first, 'rm-basis')[0].textContent, '견준 항목: 늘 하는 말');
  assert.equal(byClass(first, 'rm-src')[0].textContent, '출처: 지어낸 매체 · 지어낸 제목');
  assert.match(byClass(first, 'vs')[0].textContent, /■ 평소와 같음/);
});

test('hearsay, condition, tags and several basis items', async () => {
  const t = boot(file(MANY), '#hammack');
  await settle();
  const card = byClass(t.sec(), 'rm')[0];
  assert.ok(card.cls().includes('new'));
  assert.match(card.textContent, /2026-10-01인터뷰전언◆ 새 주제블랙아웃 중 — 전언 확인기준선 초안/);
  assert.equal(byClass(card, 'rm-cond')[0].textContent, '조건: 물가가 다시 오르면');
  assert.equal(byClass(card, 'rm-basis')[0].textContent, '견준 항목: 자금시장 · 물가');
  assert.equal(byClass(card, 'guess')[0].textContent, '전언');
});

test('approved baseline is labelled as checked', async () => {
  const t = boot(file([remark('warsh', '2026-11-01', '연설', { baseline_review: 'approved', tags: [] })]));
  await settle();
  assert.match(t.sec().textContent, /기준선\(2026-10-31 · 확인함\)/);
});

test('bad items are skipped, good ones stay', async () => {
  const bad = [
    remark('nobody', '2026-11-02'), remark('warsh', '2026-11-02', '방송'), remark('warsh', '2026-11-01', '연설', { why: '벨\u0007' }),
    remark('warsh', '2026-10-31', '연설', { title: 'https://example.invalid/x' }), remark('warsh', '2026-10-30', '연설', { quote: Array(16).fill('w').join(' ') }),
    remark('warsh', '2026-10-29', '연설', { dissent: '인상' }), remark('warsh', '2026-10-28', '연설', { topic: ' 앞 공백' }),
    remark('warsh', '2026-10-27', '연설', { basis: [] }), remark('warsh', '2026-10-26', '연설', { tags: ['딴 꼬리표'] }),
    remark('warsh', '2026-10-25', '연설', { extra: 1 }), remark('warsh', '2024-01-01'), remark('warsh', '2026-11-05'),
    remark('warsh', '2026-10-24', '연설', { id: 'XYZ' }), remark('warsh', '2026-10-23', '연설', { topic: '가'.repeat(41) }),
    remark('warsh', '2026-10-22', '연설', { why: '폭​없음' }), remark('warsh', '2026-10-21', '연설', { basis: [{ path: 'a..b', text: 'x' }] })];
  const good = [remark('warsh', '2026-10-20'), remark('cook', '2026-10-20'), remark('warsh', '2026-10-20')];   // 셋째는 겹침 — 빠진다
  const t = boot(file([...bad, ...good]));
  await settle();
  assert.match(t.strip().textContent, /2026-11-04 기준 · 2건 · 보류 2/);
  assert.equal(byClass(t.strip(), 'rm-row').length, 2);
  assert.equal(byClass(t.sec(), 'rm').length, 1);
});

test('thirty per person at most', async () => {
  const t = boot(file(Array.from({ length: 32 }, (_, i) => remark('warsh', day(i)))));
  await settle();
  assert.match(t.sec().textContent, /\(자동 분류\)30건/);
});

test('a bad head, a missing file or a failed read is one quiet line', async () => {
  const bads = [file(MANY, { schema: 'people-remarks/2' }), file(MANY, { extra: 1 }), file(MANY, { held: -1 }), file(MANY, { held: 1.5 }),
    file(MANY, { asof: '2026-13-01' }), file(MANY, { window_from: '2026-11-05' }), Object.assign(file(MANY), { generated_at: 'x' }),
    file(Array.from({ length: 401 }, (_, i) => remark('warsh', day(i % 300)))), file('x'), [], null, 404, new Error('network')];
  for (const answer of bads) {
    const t = boot(answer);
    await settle();
    const s = t.strip().textContent, f = t.sec().textContent;
    assert.match(s, /자동 발언 기록 없음$/, String(answer && answer.schema));
    assert.doesNotMatch(s, /보류/);
    assert.match(f, /자동 발언 기록 없음$/);
    assert.equal(byClass(t.strip(), 'rm-row').length, 0);
  }
});

test('before the file arrives the sections say they are reading, and a person with none says so', async () => {
  const t = boot(file([remark('cook', '2026-11-01')]));
  assert.match(t.strip().textContent, /자동 발언 기록을 읽는 중…$/);
  assert.match(t.sec().textContent, /자동 발언 기록을 읽는 중…$/);
  await settle();
  assert.match(t.sec().textContent, /2025-11-04 이후 이 사람의 자동 분류 발언 없음$/);           // 워시는 없음
  const e = boot(file([], { held: 0 }));
  await settle();
  assert.match(e.strip().textContent, /0건 · 보류 0.*자동 발언 기록 없음$/);
});

test('text from the file goes in as text nodes only', async () => {
  const evil = '<img src=x onerror=alert(1)>';
  const t = boot(file([remark('warsh', '2026-11-01', '연설', { topic: evil, why: evil, quote: '<b>x</b>', title: evil })]));
  await settle();
  const els = all(t.sec(), () => true).concat(all(t.strip(), () => true));
  assert.ok(els.every(n => !['img', 'script'].includes(n.tag)));
  assert.ok(els.every(n => Object.keys(n.attrs).every(k => !/^on/i.test(k))));
  assert.equal(byClass(t.sec(), 'rm-topic')[0].kids.length, 1);                 // 글 마디 하나 — 태그로 풀리지 않는다
  assert.ok(byClass(t.sec(), 'rm-topic')[0].kids[0] instanceof Text);
  assert.match(t.sec().textContent, /<img src=x onerror=alert\(1\)>/);
  assert.match(t.sec().textContent, /“<b>x<\/b>”/);
});
