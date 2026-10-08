// 읽기 노트 화면(site/notes.js)을 브라우저 없이 돌려 본다 — 아주 작은 가짜 DOM 위에서 저장소의 data/notes.json을 그대로 그린다.
// 실행: node --test scripts/test_notes_render.cjs   (test_notes_site.py가 node가 있으면 함께 돌린다)
// 보는 것: 목록·글이 예외 없이 그려지는지, 블록이 빠짐없이 나오는지, 링크 규칙(https · 새 창 · noopener noreferrer),
// 자료를 한 번만 읽는지, 없는 글·수신 실패·오염된 자료에서 닫힌 쪽으로 가는지, 초점 이동과 움직임 끄기,
// 화면 읽기가 기대는 역할·이름(표 · 목록 · 차례 · 알림 상자)과 터무니없는 그래프 값에서 화면이 멈추지 않는지.
// 모양(글줄 폭·좁은 화면)은 여기서 볼 수 없다 — 그건 브라우저로 확인한다.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ROOT = path.join(__dirname, '..');
const SRC = fs.readFileSync(path.join(ROOT, 'site', 'notes.js'), 'utf8');
const read = name => JSON.parse(fs.readFileSync(path.join(ROOT, 'data', name), 'utf8'));
const NOTES = read('notes.json'), FIXED = read('notes_charts.json');
// 사이트 그래프 자료는 매일 바뀐다 — 지어낸 것으로 대신한다(그리는 쪽 MacroCharts도 대역이다)
const CHARTS = { date: '2026-10-07', rules: { real_rate_bei: { key: 'real_rate_bei', title: '지어낸 그래프', lines: [] } } };
const files = () => ({ 'data/notes.json': NOTES, 'data/notes_charts.json': FIXED, 'data/charts.json': CHARTS });
const first = NOTES.notes[0];

class Text {
  constructor(t) { this.data = String(t); }
  get textContent() { return this.data; }
}
class Elem {
  constructor(tag, doc) { this.tag = tag; this.doc = doc; this.attrs = {}; this.kids = []; this.style = {}; this.on = {}; this.clientWidth = doc.width; this.swaps = 0; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  append(...xs) { for (const x of xs) this.kids.push(x instanceof Elem || x instanceof Text ? x : new Text(x)); }
  replaceChildren(...xs) { this.swaps++; this.kids = []; this.append(...xs); }
  addEventListener(type, fn) { (this.on[type] = this.on[type] || []).push(fn); }
  click() { for (const fn of this.on.click || []) fn({}); }
  // 브라우저처럼: 링크 · 버튼 · tabindex가 있는 것만 초점을 받는다(없는 것에 focus()를 불러도 아무 일도 없다)
  focus(opts) { if (['a', 'button'].includes(this.tag) || 'tabindex' in this.attrs) { this.doc.activeElement = this; this.focusOpts = opts; } }
  scrollIntoView(opts) { this.scrolled = opts; }
  get textContent() { return this.kids.map(k => k.textContent).join(''); }
  set textContent(v) { this.kids = [new Text(v)]; }
}
function all(node, pred, out = []) {
  if (!(node instanceof Elem)) return out;
  if (pred(node)) out.push(node);
  for (const k of node.kids) all(k, pred, out);
  return out;
}
const byTag = (node, tag) => all(node, n => n.tag === tag);
const byClass = (node, cls) => all(node, n => (n.attrs.class || '').split(' ').includes(cls));
const settle = async () => { for (let i = 0; i < 3; i++) await new Promise(r => setImmediate(r)); };

// index.html이 주는 것(el · svgEl · getJson · calm)과 같은 약속의 대역을 깔고 notes.js를 돌린다
function boot(data = files(), motion = 'on', width = 640) {
  const doc = { activeElement: null, width, documentElement: { dataset: { motion } } };
  const wrap = new Elem('section', doc), calls = [], drawn = [];
  doc.createElement = tag => new Elem(tag, doc);
  doc.createElementNS = (ns, tag) => new Elem(tag, doc);
  doc.getElementById = id => (id === 'notes-wrap' ? wrap : null);
  const scope = {
    document: doc,
    el(tag, attrs, ...children) {
      const node = doc.createElement(tag);
      for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, v);
      for (const c of children) if (c !== null && c !== undefined) node.append(c);
      return node;
    },
    svgEl(tag, attrs, text) {
      const node = doc.createElementNS('http://www.w3.org/2000/svg', tag);
      for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, String(v));
      if (text !== undefined) node.textContent = text;
      return node;
    },
    getJson(p) {
      calls.push(p);
      return Object.prototype.hasOwnProperty.call(data, p) ? Promise.resolve(structuredClone(data[p])) : Promise.reject(new Error(p));
    },
    calm: () => doc.documentElement.dataset.motion === 'off',
    requestAnimationFrame: fn => setImmediate(fn),                     // 다음 그리기 — settle()을 기다리면 돈다
    ResizeObserver: class { constructor(fn) { this.fn = fn; } observe() { this.fn(); } },
    MacroCharts: { lineChart(spec, opts) { drawn.push([spec, opts]); const f = doc.createElement('figure'); f.setAttribute('class', 'ch'); return f; } },
  };
  scope.window = scope;
  vm.runInNewContext(SRC, scope);
  return { doc, wrap, calls, drawn, data, view: (v, a) => scope.ReadingNotes.setView(v, a) };
}
const count = type => first.blocks.filter(b => b.type === type).length;
const figures = kind => first.blocks.filter(b => b.type === 'figure' && b.kind === kind);

test('목록: 노트마다 카드 — 제목 링크 · 출처 · 날짜 · 읽는 시간 · 한 줄 결론', async () => {
  const b = boot();
  b.view('notes', '');
  assert.match(b.wrap.textContent, /불러오는 중/);
  await settle();
  const cards = byClass(b.wrap, 'note-card');
  assert.equal(cards.length, NOTES.notes.length);
  const link = byTag(cards[0], 'a')[0];
  assert.equal(link.attrs.href, '#notes/' + first.slug);
  assert.equal(link.textContent, first.title);
  for (const part of [first.source.name, first.date, `${first.minutes}분`, first.summary[0].text]) assert.ok(cards[0].textContent.includes(part), part);
  assert.deepEqual(b.calls, ['data/notes.json']);                     // 목록에서는 그래프 자료를 읽지 않는다
});

test('글: 머리 · 한 줄 결론 · 본문 블록 · 질문 · 원문 링크 · 목록으로 돌아가기', async () => {
  const b = boot();
  b.view('notes', first.slug);
  await settle();
  const art = byClass(b.wrap, 'note')[0];
  assert.equal(byTag(art, 'h2')[0].textContent, first.title);
  const head = byClass(art, 'note-head')[0].textContent;
  for (const part of [first.source.title, first.source.name, first.source.authors, first.source.published, `${first.minutes}분`]) assert.ok(head.includes(part), part);
  assert.ok(byClass(art, 'note-gist')[0].textContent.includes(first.summary[0].text));
  const sections = first.blocks.filter(x => x.type === 'heading' && x.level === 2);
  const h3 = byTag(byClass(art, 'note-body')[0], 'h3').map(h => h.textContent);
  assert.deepEqual(h3, ['한 줄 결론', ...sections.map(s => s.text)]);
  assert.deepEqual(byTag(byClass(art, 'note-toc')[0], 'button').map(x => x.textContent), sections.map(s => s.text));
  assert.equal(byClass(art, 'note-table').length, count('table'));
  assert.equal(byClass(art, 'note-q').length, 3);
  assert.equal(byTag(byClass(art, 'note-body')[0], 'p').filter(p => !p.attrs.class).length >= count('para'), true);
  // 글 끝: 원문으로 가는 링크와 목록으로 돌아가기(위쪽에도 돌아가기가 하나 더 있다)
  const end = byTag(byClass(art, 'note-end')[0], 'a');
  assert.deepEqual(end.map(a => a.attrs.href), [first.source.url, '#notes']);
  assert.match(end[0].textContent, /원문 읽기/);
  assert.equal(byTag(byClass(art, 'note-back')[0], 'a')[0].attrs.href, '#notes');
});

test('글: 그림 셋 — 사이트 그래프 · 도식 · 정적 그래프, 번호와 캡션', async () => {
  const b = boot();
  b.view('notes', first.slug);
  await settle();
  const art = byClass(b.wrap, 'note')[0], figs = byClass(art, 'note-fig');
  assert.equal(figs.length, count('figure'));
  assert.deepEqual(byClass(art, 'note-cap-no').map(x => x.textContent), figs.map((_, i) => `그림 ${i + 1}`));
  // 사이트 그래프: charts.json의 그 규칙을 lineChart에 그대로 넘기고, 기준일을 캡션에 적는다
  assert.deepEqual(b.drawn.map(([spec]) => spec.key), figures('site_chart').map(f => f.rule));
  assert.equal(b.drawn[0][1].caption, true);
  assert.ok(art.textContent.includes('그래프 자료 기준일 2026-10-07'));
  // 도식: 칸 · 화살표 · 마름모 수가 선언과 같고, 화면 읽기용 설명이 붙는다
  const d = figures('diagram')[0].diagram, grid = byClass(art, 'nd-grid')[0];
  assert.equal(byClass(grid, 'nd-cell').length, d.columns.length);
  assert.equal(byClass(grid, 'nd-arrow').length, d.columns.reduce((n, c) => n + c.forces.length, 0));
  assert.equal(byClass(grid, 'nd-gem').length, d.columns.reduce((n, c) => n + c.net.length, 0));
  assert.equal(grid.attrs.role, 'img');
  assert.equal(grid.attrs['aria-label'], d.alt);
  assert.ok(byTag(grid, 'svg').every(s => s.attrs['aria-hidden'] === 'true'));
  // 정적 그래프: 선 수, 출처 줄(받은 날), 표로 보기
  const fixed = FIXED.charts[figures('static_chart')[0].chart];
  const chart = all(art, n => n.tag === 'figure' && n.attrs.class === 'ch' && byClass(n, 'ch-line').length > 0)[0];
  assert.equal(byClass(chart, 'ch-line').length, fixed.lines.length);
  assert.ok(chart.textContent.includes(fixed.source_note));
  assert.ok(chart.textContent.includes(`${fixed.retrieved}에 받은 값`));
  assert.equal(byTag(chart, 'tbody')[0].kids.length, fixed.lines[0].points.length);
  assert.equal(byTag(chart, 'svg')[0].attrs.role, 'img');
  assert.deepEqual(b.calls.slice().sort(), ['data/charts.json', 'data/notes.json', 'data/notes_charts.json']);
});

test('링크: 바깥 링크는 https · 새 창 · noopener noreferrer, 안쪽 링크는 #notes뿐', async () => {
  for (const arg of ['', first.slug]) {
    const b = boot();
    b.view('notes', arg);
    await settle();
    const links = byTag(b.wrap, 'a');
    assert.ok(links.length > 0);
    for (const a of links) {
      if (a.attrs.href.startsWith('#')) { assert.match(a.attrs.href, /^#notes(\/[a-z0-9-]+)?$/); continue; }
      assert.match(a.attrs.href, /^https:\/\//);
      assert.equal(a.attrs.target, '_blank');
      assert.equal(a.attrs.rel, 'noopener noreferrer');
      // 새 창으로 열린다는 것은 화면 읽기용 글자로 알린다(title 속성에 맡기지 않는다)
      assert.equal(a.kids.at(-1).attrs.class, 'sr');
      assert.ok(a.textContent.endsWith(' (새 창)'), a.textContent);
      assert.equal(a.attrs.title, undefined);
    }
    const fixed = byClass(b.wrap, 'note-fixed');
    assert.equal(fixed.length, 1);
    assert.equal(fixed[0].textContent, '이 노트는 원문을 읽고 내 말로 옮긴 공부 기록이다. 번역이나 전재가 아니며 원문의 문장·그림·표를 싣지 않았다. 틀린 곳은 저장소 Issues (새 창)로.');
    assert.equal(byTag(fixed[0], 'a')[0].attrs.href, 'https://github.com/yun-macrolab/macro-regime-check/issues');
    assert.equal(b.wrap.kids.at(-1).kids.at(-1).kids.at(-1), fixed[0]);  // 맨 아래(알림 상자 · 화면 자리 → 목록이나 글 → 고지)
  }
});

test('글: 화면 읽기가 기대는 역할과 이름 — 표 · 목록 · 차례 · 제목 · 그래프', async () => {
  const b = boot();
  b.view('notes', '');
  await settle();
  assert.equal(byClass(b.wrap, 'note-list')[0].attrs.role, 'list');      // list-style: none이어도 목록으로 읽히게
  b.view('notes', first.slug);
  await settle();
  const art = byClass(b.wrap, 'note')[0];
  // 표: 좁은 화면에서 줄마다 카드로 쌓아도 표로 읽히게 역할을 적어 둔다
  const tables = first.blocks.filter(x => x.type === 'table');
  for (const [i, box] of byClass(art, 'note-table').entries()) {
    const t = byTag(box, 'table')[0];
    assert.equal(t.attrs.role, 'table');
    assert.deepEqual([byTag(t, 'thead')[0].attrs.role, byTag(t, 'tbody')[0].attrs.role], ['rowgroup', 'rowgroup']);
    assert.ok(byTag(t, 'tr').every(r => r.attrs.role === 'row'));
    const th = byTag(t, 'th');
    assert.deepEqual(th.filter(h => h.attrs.scope === 'col').map(h => h.attrs.role), tables[i].head.filter(h => h.length).map(() => 'columnheader'));
    assert.deepEqual(th.filter(h => h.attrs.scope === 'row').map(h => h.attrs.role), tables[i].rows.map(() => 'rowheader'));
    assert.ok(th.every(h => ['col', 'row'].includes(h.attrs.scope) && h.textContent !== ''));   // 내용 없는 머리 칸은 없다
    assert.ok(byTag(t, 'td').every(d => d.attrs.role === 'cell'));
  }
  assert.equal(byClass(art, 'note-questions')[0].attrs.role, 'list');
  const toc = byClass(art, 'note-toc')[0];
  assert.equal(toc.tag, 'nav');
  assert.equal(toc.attrs['aria-label'], '이 글의 차례');
  assert.equal(byTag(toc, 'ol')[0].attrs.role, 'list');
  // 차례가 초점을 옮겨 둘 제목은 tabindex="-1"이어야 실제로 초점을 받는다
  const heads = byTag(byClass(art, 'note-body')[0], 'h3').filter(h => /^note-s\d+$/.test(h.attrs.id || ''));
  assert.ok(heads.length > 0 && heads.every(h => h.attrs.tabindex === '-1'));
  // 도식: 칸은 설명 글 하나로 읽히고, 색 견본뿐인 범례는 읽지 않는다
  const nd = byClass(art, 'nd')[0];
  assert.equal(byClass(nd, 'ch-legend')[0].attrs['aria-hidden'], 'true');
  // 정적 그래프: 그림의 이름에 제목 · 처음과 끝 값 · 표가 있다는 안내
  const fixed = FIXED.charts[figures('static_chart')[0].chart];
  const svg = byTag(all(art, n => n.tag === 'figure' && byClass(n, 'ch-line').length > 0)[0], 'svg')[0];
  assert.ok(svg.attrs['aria-label'].startsWith(fixed.title + '. '), svg.attrs['aria-label']);
  assert.match(svg.attrs['aria-label'], /표로 보기/);
  // 영문 원문 제목은 영어로 읽히게 — 한국어 '(새 창)'은 그 밖에 둔다
  const origin = byTag(byClass(art, 'note-facts')[0], 'a')[0], en = all(origin, n => n.attrs.lang === 'en');
  assert.deepEqual(en.map(n => n.textContent), [first.source.title]);
  assert.equal(origin.attrs.lang, undefined);
});

test('표: 빈 머리 칸은 열 머리가 아니고, 빈 칸은 — 로 채운다', async () => {
  const note = structuredClone(first);
  note.blocks = [{ type: 'table', head: [[], [{ text: '값' }], [{ text: '비고' }]],
    rows: [[[{ text: '가' }], [{ text: '1' }], []], [[{ text: '나' }], [], [{ text: '끝' }]]] }];
  const data = files();
  data['data/notes.json'] = { schema: 1, notes: [note] };
  const b = boot(data);
  b.view('notes', note.slug);
  await settle();
  const t = byTag(byClass(b.wrap, 'note-table')[0], 'table')[0], headRow = byTag(byTag(t, 'thead')[0], 'tr')[0];
  assert.deepEqual(headRow.kids.map(k => [k.tag, k.attrs.scope, k.textContent]), [['td', undefined, ''], ['th', 'col', '값'], ['th', 'col', '비고']]);
  const empty = byClass(t, 'none');
  assert.deepEqual(empty.map(d => [d.tag, d.textContent, d.attrs['data-label']]), [['td', '—', '비고'], ['td', '—', '값']]);
  assert.equal(byClass(t, 'has').length, 2);
});

test('없는 글 이름이면 목록과 안내 문구', async () => {
  for (const arg of ['2026-01-01-no-such-note', '../x', '<img src=x onerror=alert(1)>']) {
    const b = boot();
    b.view('notes', arg);
    await settle();
    assert.equal(byClass(b.wrap, 'note-card').length, NOTES.notes.length);
    assert.match(byClass(b.wrap, 'note-missing')[0].textContent, /찾지 못했다/);
    assert.ok(!b.wrap.textContent.includes(arg));
  }
});

test('자료는 #notes에 처음 들어올 때 한 번만 읽는다', async () => {
  const b = boot();
  b.view('all', '');
  b.view('rates', '');
  b.view('evening', '2026-10-08');
  await settle();
  assert.deepEqual(b.calls, []);
  assert.equal(b.wrap.kids.length, 0);
  b.view('notes', '');
  b.view('notes', '');
  await settle();
  b.view('notes', first.slug);
  b.view('notes', '');
  b.view('notes', first.slug);
  await settle();
  assert.deepEqual(b.calls.slice().sort(), ['data/charts.json', 'data/notes.json', 'data/notes_charts.json']);
});

test('수신 실패: 안내와 다시 읽기 버튼, 다시 읽으면 그린다', async () => {
  const data = files();
  delete data['data/notes.json'];
  const b = boot(data);
  b.view('notes', '');
  await settle();
  assert.match(b.wrap.textContent, /불러오지 못했다/);
  b.view('notes', '');                                                 // 화면이 다시 불려도 혼자 되풀이해 읽지 않는다
  await settle();
  assert.equal(b.calls.length, 1);
  data['data/notes.json'] = NOTES;
  byTag(b.wrap, 'button')[0].click();
  await settle();
  assert.equal(byClass(b.wrap, 'note-card').length, NOTES.notes.length);
});

test('그래프 자료를 못 받아도 글은 그대로 읽힌다', async () => {
  const data = files();
  delete data['data/charts.json'];
  data['data/notes_charts.json'] = { charts: { cpi_jp_us: { lines: [{ label: '깨진 선', points: [['x', 'y']] }] } } };
  const b = boot(data);
  b.view('notes', first.slug);
  await settle();
  const art = byClass(b.wrap, 'note')[0];
  assert.equal(byClass(art, 'note-fig').length, count('figure'));
  assert.equal(all(art, n => /불러오지 못했다/.test(n.attrs.class === 'note-cap' ? n.textContent : '')).length, 2);
  assert.equal(byClass(art, 'nd-cell').length, figures('diagram')[0].diagram.columns.length);
  assert.equal(byClass(art, 'note-q').length, 3);
});

test('오염된 자료: https가 아닌 링크는 글자로, 꼴이 어긋난 노트·블록은 버린다', async () => {
  const bad = structuredClone(first);
  bad.title = '<img src=x onerror=alert(1)>';
  bad.source.url = 'javascript:alert(1)';
  bad.summary = [{ text: '위험한 링크', href: 'javascript:alert(1)' }, { text: '평문 링크', href: 'http://example.org/a' }, { text: 7 }, null];
  const hidden = code => 'https://example.org/a' + String.fromCharCode(code) + 'b';   // 보이지 않는 글자가 섞인 주소
  bad.blocks = [{ type: 'para', spans: [{ text: '상대 링크', href: '/x' }, { text: '좋은 링크', href: 'https://example.org/a' },
    { text: '뒤집는 글자가 든 링크', href: hidden(0x202e) }, { text: '제어 문자가 든 링크', href: hidden(1) }, { text: '폭 없는 공백이 든 링크', href: hidden(0x200b) }] },
    { type: 'script', text: 'alert(1)' }, null, 'x', { type: 'figure', kind: 'diagram', diagram: { kind: 'flow' } },
    { type: 'figure', kind: 'unknown' }, { type: 'table', head: 'x', rows: [[null, 3]] }, { type: 'heading', level: 2, id: 'x"y', text: '이상한 id' },
    { type: 'questions', items: 'x' }, { type: 'list', items: [[{ text: '항목' }], 5] }];
  const data = files();
  data['data/notes.json'] = { notes: [bad, { ...first, slug: '../../etc' }, { ...first, blocks: 'x', slug: '2026-01-01-b' }, null, 3] };
  const b = boot(data);
  b.view('notes', '');
  await settle();
  assert.equal(byClass(b.wrap, 'note-card').length, 1);                // 이름·꼴이 어긋난 노트는 목록에 없다
  b.view('notes', bad.slug);
  await settle();
  const art = byClass(b.wrap, 'note')[0];
  assert.equal(byTag(art, 'h2')[0].textContent, bad.title);            // 글자 그대로(태그로 해석하지 않는다)
  assert.equal(byTag(art, 'img').length + byTag(art, 'script').length, 0);
  const hrefs = byTag(art, 'a').map(a => a.attrs.href);
  assert.deepEqual(hrefs.filter(h => !h.startsWith('#notes')).sort(),
    ['https://example.org/a', 'https://github.com/yun-macrolab/macro-regime-check/issues']);
  for (const word of ['위험한 링크', '평문 링크', '상대 링크', '뒤집는 글자가 든 링크', '제어 문자가 든 링크', '폭 없는 공백이 든 링크', '항목']) assert.ok(art.textContent.includes(word), word);
  assert.ok(!art.textContent.includes('alert(1)') || art.textContent.includes(bad.title));
  assert.equal(byClass(art, 'note-fig').length, 0);
});

test('노트 화면 안에서 옮기면 초점이 따라간다 — 글로 가면 제목, 돌아오면 읽던 카드', async () => {
  const b = boot();
  b.view('notes', '');
  await settle();
  assert.equal(b.doc.activeElement, null);                             // 처음 들어올 때는 초점을 가져가지 않는다
  b.view('notes', first.slug);
  const title = byTag(b.wrap, 'h2')[0];
  assert.equal(b.doc.activeElement, title);
  assert.deepEqual({ ...title.focusOpts }, { preventScroll: true });
  assert.equal(title.attrs.tabindex, '-1');
  b.view('notes', '');
  assert.equal(b.doc.activeElement, byTag(byClass(b.wrap, 'note-card')[0], 'a')[0]);
});

test('차례 버튼: 그 절로 옮기고 초점을 둔다 — 움직임을 껐으면 부드러운 이동 없이', async () => {
  for (const [motion, behavior] of [['on', 'smooth'], ['off', 'auto']]) {
    const b = boot(files(), motion);
    b.view('notes', first.slug);
    await settle();
    const button = byTag(byClass(b.wrap, 'note-toc')[0], 'button')[1];
    const target = byTag(byClass(b.wrap, 'note-body')[0], 'h3').find(h => h.textContent === button.textContent);
    button.click();
    assert.equal(target.scrolled.behavior, behavior);
    assert.equal(b.doc.activeElement, target);
  }
});

test('그림의 좌표가 그림 안에 있다 — 좁은 화면 폭에서도 넘치지 않는다', async () => {
  const pairs = d => (d.match(/-?\d+(?:\.\d+)?/g) || []).map(Number).reduce((out, v, i) => (i % 2 ? out[out.length - 1].push(v) : out.push([v]), out), []);
  for (const width of [325, 640, 814]) {
    const b = boot(files(), 'on', width);
    b.view('notes', first.slug);
    await settle();
    const art = byClass(b.wrap, 'note')[0];
    // 정적 그래프: 그림 폭 = 놓인 자리의 폭, 선·눈금·끝 값 상자가 모두 그 안
    const svg = byTag(all(art, n => n.tag === 'figure' && byClass(n, 'ch-line').length > 0)[0], 'svg')[0];
    assert.equal(svg.attrs.viewBox, `0 0 ${width} 240`);
    for (const line of byClass(svg, 'ch-line')) for (const [x, y] of pairs(line.attrs.d)) {
      assert.ok(x >= 40 && x <= width - 66 && y >= 10 && y <= 218, `${width}: 선 ${x},${y}`);
    }
    const boxes = byClass(svg, 'ch-end-box').map(r => ({ y: Number(r.attrs.y), right: Number(r.attrs.x) + Number(r.attrs.width) }));
    assert.equal(boxes.length, 2);
    assert.ok(boxes.every(r => r.right <= width && r.y >= 0 && r.y + 16 <= 240), `${width}: 끝 값 상자`);
    assert.ok(Math.abs(boxes[0].y - boxes[1].y) >= 16, `${width}: 끝 값 상자가 겹친다`);
    const years = byClass(svg, 'ch-tick').filter(t => /^(19|20)\d\d$/.test(t.textContent));
    assert.ok(years.length >= 3 && years.length <= 8, `${width}: 연도 눈금 ${years.length}개`);
    const gapPx = Number(years[1].attrs.x) - Number(years[0].attrs.x);
    assert.ok(gapPx >= 36, `${width}: 연도 글자 간격 ${gapPx}`);                    // 네 자리 숫자(약 27px)가 겹치지 않는다
    assert.ok(byClass(svg, 'ch-zero').length === 1);                                // 0% 선(일본이 오래 머문 자리)
    // 도식: 화살표·마름모·0선이 칸(200×172) 안
    for (const cell of byTag(byClass(art, 'nd-grid')[0], 'svg')) {
      assert.equal(cell.attrs.viewBox, '0 0 200 172');
      for (const p of byTag(cell, 'path')) for (const [x, y] of pairs(p.attrs.d)) assert.ok(x >= 0 && x <= 200 && y >= 0 && y <= 172, `도식 ${x},${y}`);
      for (const l of byTag(cell, 'line')) for (const k of ['x1', 'x2', 'y1', 'y2']) assert.ok(Number(l.attrs[k]) >= 0 && Number(l.attrs[k]) <= 200, k);
    }
  }
});

test('도식: 힘의 방향과 합이 놓이는 자리가 선언대로 그려진다', async () => {
  const b = boot();
  b.view('notes', first.slug);
  await settle();
  const d = figures('diagram')[0].diagram, cells = byClass(b.wrap, 'nd-cell');
  const tipY = g => Number(byTag(g, 'path')[0].attrs.d.match(/L(-?[\d.]+) (-?[\d.]+)L/)[2]);      // 화살촉의 끝
  d.columns.forEach((col, i) => {
    const arrows = byClass(cells[i], 'nd-arrow'), gems = byClass(cells[i], 'nd-gem');
    col.forces.forEach((f, k) => {
      if (f.dir === 'up') assert.ok(tipY(arrows[k]) < 86, `${col.label}: 위로`);
      if (f.dir === 'down') assert.ok(tipY(arrows[k]) > 86, `${col.label}: 아래로`);
      assert.equal(byTag(arrows[k], 'path').length, f.dir === 'both' ? 2 : 1);              // 부호가 바뀌는 힘은 양쪽 화살촉
      assert.equal(Math.abs(tipY(arrows[k]) - 86), f.dir === 'both' ? 11.5 * f.size : 23 * f.size);
    });
    col.net.forEach((n, k) => {
      const top = Number(gems[k].attrs.d.match(/^M[\d.]+ ([\d.]+)/)[1]) + 8;                 // 마름모의 가운데
      assert.equal(Math.sign(86 - top), { above: 1, zero: 0, below: -1 }[n.pos], `${col.label}: ${n.pos}`);
    });
    assert.equal((cells[i].attrs.class || '').includes('nd-key'), col.highlight === true);
    for (const text of [col.label, ...col.forces.map(f => f.note), ...col.net.map(n => n.note)]) assert.ok(cells[i].textContent.includes(text), text);
  });
});

test('정적 그래프: 오염된 값이 와도 눈금이 끝없이 늘지 않는다', async () => {
  // 연도가 20250101이거나 값이 1e7이면 눈금을 하나씩 세다가 탭이 멈춘다 — 터무니없는 점은 버리고, 눈금 수에는 상한을 둔다
  const cases = [[[1995, 1], [1996, 2], [20250101, 3]], [[1995, 1], [1996, 2], [1997, 1e7]], [[1995, 1], [1996, 2], [-40000, 3]],
    [[1995, 900], [1996, -900]], [[1995, 0.001], [1996, 0.002]]];
  for (const points of cases) {
    const data = files();
    data['data/notes_charts.json'] = { charts: { cpi_jp_us: { title: '지어낸 그래프', unit: '%', lines: [{ label: '지어낸 선', points }] } } };
    const b = boot(data);
    b.view('notes', first.slug);
    await settle();
    const chart = all(b.wrap, n => n.tag === 'figure' && byClass(n, 'ch-line').length > 0)[0];
    assert.ok(chart, JSON.stringify(points));
    const marks = all(chart, n => ['ch-grid', 'ch-zero', 'ch-tick'].includes(n.attrs.class));
    assert.ok(marks.length <= 100, `${JSON.stringify(points)}: 눈금 요소 ${marks.length}개`);
    const rows = marks.filter(n => n.tag === 'line' && n.attrs.y1 === n.attrs.y2);          // 가로 눈금선
    assert.ok(rows.length >= 1 && rows.length <= 7, `${JSON.stringify(points)}: 가로 눈금 ${rows.length}개`);
    const table = byTag(byTag(chart, 'tbody')[0], 'tr').map(r => r.kids.map(k => Number(k.textContent)));
    assert.ok(table.every(([y, v]) => y >= 1900 && y <= 2100 && Math.abs(v) < 1000), `${JSON.stringify(points)}: 표 ${JSON.stringify(table)}`);
  }
});

test('꼴이 어긋난 notes.json은 빈 목록이 아니라 수신 실패로 보이고, 다시 읽으면 새로 받는다', async () => {
  for (const bad of [{}, { notes: 'x' }, [], null, 3, { schema: 1, notes: [null, { ...first, slug: '../x' }] }]) {
    const data = files();
    data['data/notes.json'] = bad;
    const b = boot(data);
    b.view('notes', '');
    await settle();
    assert.match(b.wrap.textContent, /불러오지 못했다/, JSON.stringify(bad));
    assert.ok(!/아직 올린 노트가 없다/.test(b.wrap.textContent), JSON.stringify(bad));
    data['data/notes.json'] = NOTES;                                   // 고쳐진 뒤 '다시 읽기' — 앞서 받은 것을 다시 쓰지 않는다
    byTag(b.wrap, 'button')[0].click();
    await settle();
    assert.equal(byClass(b.wrap, 'note-card').length, NOTES.notes.length, JSON.stringify(bad));
    assert.equal(b.calls.filter(c => c === 'data/notes.json').length, 2);
  }
  const data = files();
  data['data/notes.json'] = { schema: 1, notes: [] };                  // 정말 빈 목록은 실패가 아니다
  const b = boot(data);
  b.view('notes', '');
  await settle();
  assert.match(b.wrap.textContent, /아직 올린 노트가 없다/);
  assert.equal(byTag(b.wrap, 'button').length, 0);
});

test('다시 읽기: 버튼이 사라진 뒤 초점 둘 곳 — 성공하면 제목, 또 실패하면 새 버튼', async () => {
  const data = files();
  delete data['data/notes.json'];
  const b = boot(data);
  b.view('notes', '');
  await settle();
  const again = byTag(b.wrap, 'button')[0];
  again.focus();                                                       // 누르는 사람의 초점은 이 버튼에 있다
  again.click();
  await settle();
  const next = byTag(b.wrap, 'button')[0];
  assert.notEqual(next, again);
  assert.equal(b.doc.activeElement, next);                             // 또 실패 — 새로 그린 버튼으로
  data['data/notes.json'] = NOTES;
  next.click();
  await settle();
  assert.equal(b.doc.activeElement, byTag(b.wrap, 'h2')[0]);           // 성공 — 목록 제목으로
  assert.deepEqual({ ...b.doc.activeElement.focusOpts }, { preventScroll: true });
});

test('다른 화면을 거쳐 돌아오면 초점을 가져가지 않는다 — 노트 화면 안에서 옮길 때만 따라간다', async () => {
  const b = boot();
  b.view('notes', first.slug);
  await settle();
  b.view('rates', '');                                                 // 화면 선택 링크로 다른 화면에 갔다가
  b.doc.activeElement = null;
  b.view('notes', '');                                                 // 다시 읽기 노트로
  await settle();
  assert.equal(b.doc.activeElement, null);                             // 누른 링크에 있던 초점을 카드로 끌어가지 않는다
  b.view('notes', first.slug);
  assert.equal(b.doc.activeElement, byTag(b.wrap, 'h2')[0]);
  b.view('notes', '');
  const card = byTag(byClass(b.wrap, 'note-card')[0], 'a')[0];
  assert.equal(b.doc.activeElement, card);
  // index.html이 화면을 맨 위로 올린 다음에, 초점을 둔 카드가 화면 밖이면 보이는 데까지만 옮긴다
  assert.equal(card.scrolled, undefined);
  await settle();
  assert.deepEqual({ ...card.scrolled }, { block: 'nearest' });
});

test('알림 상자: 늘 있는 role=status 하나에 글자만 바꾼다', async () => {
  // 글자를 담은 채 새로 끼워 넣은 알림은 읽히지 않는 일이 많다 — 상자는 한 번 넣어 두고 글자만 바꾼다
  const status = b => all(b.wrap, n => n.attrs.role === 'status');
  const b = boot();
  b.view('notes', '2026-01-01-no-such-note');
  const [live] = status(b);
  assert.equal(status(b).length, 1);
  assert.equal(b.wrap.kids[0], live);
  assert.equal(live.attrs.class, 'sr');
  assert.match(live.textContent, /불러오는 중/);
  const swaps = b.wrap.swaps;
  await settle();
  assert.match(live.textContent, /찾지 못했다/);
  const seen = byClass(b.wrap, 'note-missing')[0];
  assert.equal(seen.textContent, live.textContent);                    // 눈에 보이는 안내는 그대로 — 같은 글이라
  assert.equal(seen.attrs['aria-hidden'], 'true');                     // 화면 읽기에는 알림 상자 하나만 읽힌다
  b.view('notes', first.slug);
  await settle();
  assert.equal(live.textContent, '');
  b.view('notes', '');
  assert.deepEqual(status(b), [live]);                                 // 화면이 바뀌어도 같은 상자 하나
  assert.equal(b.wrap.swaps, swaps);                                   // 상자를 뺐다 다시 넣지 않는다
  const data = files();
  delete data['data/notes.json'];
  const f = boot(data);
  f.view('notes', '');
  await settle();
  assert.deepEqual(status(f).map(n => n.textContent), ['읽기 노트 자료를 불러오지 못했다.']);
  // 실패 화면: 보이는 글만 화면 읽기에서 빼고, 버튼은 그대로 닿는다
  const hidden = all(f.wrap, n => n.attrs['aria-hidden'] === 'true');
  assert.deepEqual(hidden.map(n => n.textContent.trim()), ['읽기 노트 자료를 불러오지 못했다.']);
  assert.equal(hidden.flatMap(n => byTag(n, 'button')).length, 0);
  assert.equal(byTag(f.wrap, 'button').length, 1);
});
