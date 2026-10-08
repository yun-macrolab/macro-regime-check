// 저녁판 화면(site/evening.js)을 브라우저 없이 그려 보는 틀 — test_evening_site.py가 node로 부른다 (2026-10-08).
//   node scripts/evening/evening_dom.cjs <입력.json>
//   입력  {"runs": [{"files": {"data/…": 자료}, "steps": [단계 …]}, …]}      출력  벌마다 단계별 결과의 JSON 배열(표준 출력)
// 단계
//   {"now": ISO, "view": "evening", "arg": "", "calm": false}   시계를 맞추고 화면을 바꾼다(index.html의 applyView가 하는 일)
//   {"now": ISO, "tick": true}                                   시계를 맞추고 1분 시계와 탭 복귀 알림을 한 번 울린다
//   {"put": {"data/…": 자료 | null}}                             자료를 바꾼다(null이면 없는 파일)
//   {"reader": false}                                            getJson을 없앤다(자료를 아예 읽을 수 없는 경우) · true면 되돌린다
//   {"wrap": false}                                              #evening-wrap을 없앤다(페이지 뼈대가 바뀐 경우) · true면 되돌린다
//   {"fn": 이름, "args": [ … ]}                                  Evening._의 함수를 부른다(화면 없이 규칙만 볼 때)
// 화면 단계의 결과: text(글자) · links · attrs · heads(제목) · folds(접는 줄) · requested(읽은 경로) · early(자료가 오기 전의 글자)
// 가짜 문서는 evening.js가 쓰는 것만 흉내 낸다: 요소 만들기 · 붙이기 · 속성 · class · 글자. 모양과 가로 넘침은 여기서 볼 수 없다.
// el()은 index.html에 있는 것을 그대로 꺼내 쓴다(화면이 실제로 쓰는 도우미로 그려 보려는 것). 네트워크는 쓰지 않는다.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const SITE = path.join(__dirname, '..', '..', 'site');

class Text {
  constructor(data) { this.nodeType = 3; this.data = data; }
  get textContent() { return this.data; }
}

class Element {
  constructor(tag) { this.nodeType = 1; this.tagName = tag; this.attrs = {}; this.children = []; this.hidden = false; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; }
  removeAttribute(k) { delete this.attrs[k]; }
  append(...xs) {
    for (const x of xs) {
      if (x instanceof Element || x instanceof Text) this.children.push(x);
      else if (typeof x === 'string' || typeof x === 'number') this.children.push(new Text(String(x)));
      else throw new TypeError('요소·글자가 아닌 것을 붙였다: ' + Object.prototype.toString.call(x));   // 진짜 문서라면 "[object Object]"가 찍힌다
    }
  }
  replaceChildren(...xs) { this.children = []; this.append(...xs); }
  addEventListener() {}
  get textContent() { return this.children.map(c => c.textContent).join(''); }
  set textContent(v) { this.children = v === '' ? [] : [new Text(String(v))]; }
  get classList() {
    const el = this, names = () => (el.attrs.class || '').split(/\s+/).filter(Boolean);
    const save = xs => { el.attrs.class = xs.join(' '); };
    return { add: n => { if (!names().includes(n)) save([...names(), n]); }, remove: n => save(names().filter(x => x !== n)),
      contains: n => names().includes(n) };
  }
}

function pageHelper(name) {
  const page = fs.readFileSync(path.join(SITE, 'index.html'), 'utf8');
  const a = page.indexOf(`function ${name}(`), b = page.indexOf('\n}', a);          // 줄 맨 앞의 닫는 괄호까지가 그 함수다
  if (a < 0 || b < 0) throw new Error(`index.html에서 ${name}()을 찾지 못했다`);
  return page.slice(a, b + 2);
}

function world(files) {
  const root = new Element('section'), requested = [], beats = [], waking = [];
  const document = { visibilityState: 'visible', createElement: tag => new Element(tag),
    getElementById: id => (id === 'evening-wrap' && scope.wrapOn ? root : null),
    addEventListener: (type, fn) => { if (type === 'visibilitychange') waking.push(fn); } };
  const scope = { document, console, calmNow: false, clockNow: 0, wrapOn: true,
    setInterval: fn => { beats.push(fn); return beats.length; }, clearInterval() {}, setTimeout: () => 0, clearTimeout() {},
    getJson: p => {                                    // 화면이 부르는 getJson — 없는 파일은 404처럼 거절한다
      requested.push(p);
      const v = Object.prototype.hasOwnProperty.call(files, p) ? files[p] : null;
      return v === null ? Promise.reject(new Error('404')) : Promise.resolve(JSON.parse(JSON.stringify(v)));
    } };
  scope.window = scope;
  const ctx = vm.createContext(scope);
  vm.runInContext('Date.now = () => clockNow; const calm = () => calmNow;\n' + pageHelper('el'), ctx);
  vm.runInContext(fs.readFileSync(path.join(SITE, 'evening.js'), 'utf8'), ctx, { filename: 'evening.js' });
  return { root, requested, beats, waking, scope, getJson: scope.getJson };
}

// 지금 화면 — 감춘 가지는 빼고 글자·링크·속성·제목을 모은다
function frame(w) {
  const texts = [], links = [], attrs = [], heads = [], folds = [];
  (function walk(n) {
    if (n.nodeType === 3) { texts.push(n.data); return; }
    if (n.hidden || n.getAttribute('hidden') !== null) return;
    for (const [k, v] of Object.entries(n.attrs)) attrs.push(`${k}=${v}`);
    if (n.tagName === 'a') links.push({ href: n.getAttribute('href'), rel: n.getAttribute('rel'), target: n.getAttribute('target'),
      current: n.getAttribute('aria-current'), text: n.textContent });
    if (/^h[1-6]$/.test(n.tagName)) heads.push(n.textContent);
    if (n.tagName === 'summary') folds.push(n.textContent);
    n.children.forEach(walk);
  })(w.root);
  return { text: texts.join(''), links, attrs, heads, folds, requested: w.requested.slice() };
}

const settle = async () => { for (let i = 0; i < 12; i++) await new Promise(r => setImmediate(r)); };

async function run(input) {
  const files = { ...input.files }, w = world(files), out = [];
  for (const step of input.steps) {
    if (step.now) w.scope.clockNow = Date.parse(step.now);
    if (typeof step.calm === 'boolean') w.scope.calmNow = step.calm;
    if (step.put) { Object.assign(files, step.put); out.push(null); continue; }
    if (typeof step.reader === 'boolean') { w.scope.getJson = step.reader ? w.getJson : undefined; out.push(null); continue; }
    if (typeof step.wrap === 'boolean') { w.scope.wrapOn = step.wrap; out.push(null); continue; }
    if (step.fn) { out.push(w.scope.Evening._[step.fn](...(step.args || []))); continue; }
    if (step.tick) { w.beats.forEach(fn => fn()); w.waking.forEach(fn => fn()); }
    else w.scope.Evening.setView(step.view, step.arg || '');
    const early = frame(w);                            // 자료가 오기 전의 화면(불러오는 중)
    await settle();
    out.push({ ...frame(w), early: early.text });
  }
  return out;
}

// 벌마다 새 문서·새 화면으로 돈다(앞 벌의 상태가 넘어가지 않는다)
async function runAll(input) {
  const out = [];
  for (const one of input.runs) out.push(await run(one));
  return out;
}

runAll(JSON.parse(fs.readFileSync(process.argv[2], 'utf8')))
  .then(out => { process.stdout.write(JSON.stringify(out)); }, e => { process.stderr.write(String(e && e.stack || e)); process.exitCode = 1; });
