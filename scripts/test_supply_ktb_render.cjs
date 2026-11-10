// 수급 참고 칸(supplyPanel)과 국고채 민평 참고 절(renderKtb) — site/index.html 안의 함수라 그 부분만 잘라 아주 작은 가짜 DOM 위에서
// 돌려 글을 본다. 실패를 알리는 메일이 없는 칸이라 페이지의 표시(자료 없음·받지 못함·경과일·묵은 글)가 곧 실패 신호다. 숫자는 지어낸 것이다.
// 실행: node --test scripts/test_supply_ktb_render.cjs
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

class El {
 constructor(tag){this.tag=tag;this.kids=[];this.attrs={};this.hidden=false;this.dataset={};this.style={};}
 append(...xs){for(const x of xs)this.kids.push(typeof x==='string'?{text:x}:x);}
 replaceChildren(...xs){this.kids=[];this.append(...xs);}
 setAttribute(k,v){this.attrs[k]=String(v);}
 get textContent(){return this.kids.map(k=>k instanceof El?k.textContent:k.text).join('');}
 set textContent(v){this.kids=[{text:String(v)}];}
}
const walk=(n,f,out=[])=>{if(n instanceof El){if(f(n))out.push(n);n.kids.forEach(k=>walk(k,f,out));}return out;};
const cls=(n,c)=>walk(n,x=>(x.attrs.class||'').split(' ').includes(c));
const texts=n=>n instanceof El?n.kids.flatMap(texts):[n.text];   // 글자 마디 — 모두 글(text)로 들어갔는지 본다

const HTML=fs.readFileSync(path.join(__dirname,'../site/index.html'),'utf8');
function slice(start,end){
 const i=HTML.indexOf(start);assert.ok(i>=0,'index.html에 '+start+' 없음');
 const j=HTML.indexOf(end,i);assert.ok(j>i,'index.html에 '+end+' 없음');
 return HTML.slice(i,j);
}
const SRC=[slice('function el(tag, attrs','const SVG_NS'),slice('function chartFigure(','const GROUPS = ['),
 slice('let supplyData = null;','let activeView'),'const available = {};',slice('function renderKtb(k)','function renderPublic'),
 '({ supplyPanel, supplySide, renderKtb, available })'].join('\n');
const NOW=Date.parse('2026-11-10T03:00:00Z');                   // 한국 12:00
const KTB_IDS=['ktb-head','ktb-table','ktb-spreads','ktb-charts','ktb-notices'];

function load(opts={}){
 const ids=Object.fromEntries(KTB_IDS.map(k=>[k,new El('#'+k)]));
 const calls=[];
 class FakeDate extends Date{static now(){return opts.now||NOW;}}
 const document={createElement:t=>new El(t),getElementById:id=>ids[id]||null};
 const window=opts.charts?{MacroCharts:opts.charts}:{MacroCharts:{lineChart:(spec,o)=>{calls.push({spec,o});return new El('figure');}}};
 const api=vm.runInNewContext(SRC,{document,window,Date:FakeDate});
 return {...api,ids,calls};
}

const pts=(...vs)=>vs.map((v,i)=>['2026-10-'+String(7+7*i).padStart(2,'0'),v]);
function side(key,extra={}){
 const dealer=key==='dealer';
 return Object.assign({ok:true,stale:false,error:null,failed_since:null,
  name:dealer?'딜러 국채 순포지션(TIPS 제외)':'해외 공적 수탁 국채(뉴욕 연은 보관)',series:dealer?'PDPOSGST-TOT':'WMTSECL1',date:'2026-11-04',
  line:dealer?'433bn · 4주 +23 (2019년 이후 p5 -45 / p95 +52) · 52주 +54':'2,565bn · 4주 -25 (2019년 이후 p5 -53 / p95 +43) · 52주 -212',
  flag_text:null,extra:dealer?['2022년 말 이후 +282bn (기준 2022-12-28 150bn)']:[],
  chart:{key:'supply_'+key,title:'t',unit:'bn',years:5,zero:dealer,threshold:null,note:'n',source_note:'s',notices:[],
   lines:[{key,label:'t',role:'series',series:[],derived:false,points:dealer?pts(410.0,433.46):pts(2590.0,2565.477)}]},
  notices:dealer?['계산값 고지','© 2026 Federal Reserve Bank of New York.','관계없음 고지']:['계산값 고지']},extra);
}
const supply=(d={},c={})=>({schema:1,notice:'참고',dealer:side('dealer',d),custody:side('custody',c)});
const lines=panel=>walk(panel,n=>n.tag==='p').map(p=>(p.attrs.class||'')+'|'+p.textContent);

function ktb(extra={}){
 return Object.assign({schema:1,date:'2026-11-09',notices:['채널 자료 고지','관계없음 고지'],
  latest:{date:'2026-11-09',post_url:'https://t.me/jk_bond/23218',
   rows:[{tenor:'3년',yield:3.615,change_bp:-4.5},{tenor:'10년',yield:3.855,change_bp:2},{tenor:'30년',yield:3.972,change_bp:0.04}],
   spreads:[{label:'10년−3년',bp:24.0},{label:'30년−10년',bp:11.7}]},
  charts:[{key:'ktb_yields',title:'국고채 금리',unit:'%',years:3,zero:false,threshold:null,note:null,source_note:'s',notices:[],
    lines:[{key:'y3',label:'국고 3년',role:'series',series:[],derived:false,points:[['2026-11-06',3.66],['2026-11-09',3.615]]},
           {key:'y10',label:'국고 10년',role:'series',series:[],derived:false,points:[['2026-11-06',3.875],['2026-11-09',3.855]]}]},
   {key:'ktb_spreads',title:'국고채 장단기 금리차',unit:'bp',years:3,zero:true,threshold:null,note:null,source_note:'s',notices:[],
    lines:[{key:'s103',label:'10년−3년',role:'series',series:[],derived:false,points:[['2026-11-06',21.5],['2026-11-09',24.0]]}]}]},extra);
}

test('supply: both sides draw name, date, line, extra, chart and notices as text only',()=>{
 const t=load(), panel=t.supplyPanel(supply());
 const ls=lines(panel);
 assert.ok(ls.includes('supply-name|딜러 국채 순포지션(TIPS 제외) 2026-11-04 관측'),ls.join('\n'));
 assert.ok(ls.includes('supply-num|433bn · 4주 +23 (2019년 이후 p5 -45 / p95 +52) · 52주 +54'));
 assert.ok(ls.includes('muted|2022년 말 이후 +282bn (기준 2022-12-28 150bn)'));
 assert.ok(ls.includes('supply-num|2,565bn · 4주 -25 (2019년 이후 p5 -53 / p95 +43) · 52주 -212'));
 assert.equal(cls(panel,'supply-flag').length,0);
 assert.equal(cls(panel,'supply-late').length,0);
 assert.equal(t.calls.length,2);
 assert.deepEqual(t.calls.map(c=>[c.o.height,c.o.caption,c.o.format]),[[150,false,undefined],[150,false,undefined]]);   // 기본 꼴(정수 bn)
 assert.equal(cls(panel,'notices').length,2);
 assert.ok(texts(panel).every(x=>typeof x==='string'));
 assert.ok(!/undefined|NaN|null/.test(panel.textContent));
});

test('supply: the dealer side without the New York Fed notices shows no numbers, custody still draws',()=>{
 const t=load(), panel=t.supplyPanel(supply({notices:[]}));
 const ls=lines(panel);
 assert.ok(ls.includes('supply-name|딜러 국채 순포지션 — 자료 없음'),ls.join('\n'));
 assert.ok(!panel.textContent.includes('433bn'));
 assert.ok(ls.includes('supply-num|2,565bn · 4주 -25 (2019년 이후 p5 -53 / p95 +43) · 52주 -212'));
 assert.equal(t.calls.length,1);
 for(const bad of [[''],[1,null],'고지'])
  assert.ok(lines(load().supplyPanel(supply({notices:bad}))).includes('supply-name|딜러 국채 순포지션 — 자료 없음'),JSON.stringify(bad));
 const c=lines(load().supplyPanel(supply({},{notices:[]})));     // 수탁 쪽은 출처 표기 없이도 숫자(FRED 인용은 source에)
 assert.ok(c.includes('supply-num|2,565bn · 4주 -25 (2019년 이후 p5 -53 / p95 +43) · 52주 -212'));
});

test('supply: a missing file or a malformed side is one "자료 없음" line',()=>{
 for(const d of [null,undefined,'x',7]){
  const ls=lines(load().supplyPanel(d));
  assert.deepEqual(ls.slice(-1),['muted|자료 없음'],String(d));
 }
 for(const bad of [{date:'2026-11-4'},{date:'2026-13-40'},{date:null},{line:''},{line:7}]){
  const ls=lines(load().supplyPanel(supply(bad)));
  assert.ok(ls.includes('supply-name|딜러 국채 순포지션 — 자료 없음'),JSON.stringify(bad)+'\n'+ls.join('\n'));
 }
 const ls=lines(load().supplyPanel({dealer:null,custody:'x'}));
 assert.deepEqual(ls.filter(l=>l.startsWith('supply-name')),['supply-name|딜러 국채 순포지션 — 자료 없음','supply-name|해외 공적 수탁 국채 — 자료 없음']);
});

test('supply: a side not received this run says so, with the day it started when that is a date',()=>{
 let ls=lines(load().supplyPanel(supply({stale:true,failed_since:'2026-11-03'})));
 assert.ok(ls.includes('supply-late|이번 갱신에서 받지 못해 직전에 받은 값을 싣습니다 (2026-11-03부터)'),ls.join('\n'));
 ls=lines(load().supplyPanel(supply({stale:true,failed_since:'어제'})));
 assert.ok(ls.includes('supply-late|이번 갱신에서 받지 못해 직전에 받은 값을 싣습니다'));
 for(const v of ['true',1,false,null]){
  const p=load().supplyPanel(supply({stale:v,failed_since:'2026-11-03'}));
  assert.equal(cls(p,'supply-late').length,0,String(v));
 }
});

test('supply: the ⚠ line is drawn as its own paragraph, only from a string',()=>{
 const flag='⚠ 딜러 4주 변화 -45.4bn이 2019년 이후 p5(-45.3) 아래(하위 5%) — 재고 급감';
 const p=load().supplyPanel(supply({flag_text:flag}));
 assert.deepEqual(cls(p,'supply-flag').map(n=>n.textContent),[flag]);
 const order=lines(p).filter(l=>/^supply-(name|num|flag)/.test(l)).slice(0,3).map(l=>l.split('|')[0]);
 assert.deepEqual(order,['supply-name','supply-num','supply-flag']);                    // 숫자 줄 바로 아래
 for(const v of ['',null,7,['x']])assert.equal(cls(load().supplyPanel(supply({flag_text:v})),'supply-flag').length,0,String(v));
});

test('supply: the age of the last observation shows only past 21 days',()=>{
 const name=d=>cls(load().supplyPanel(supply({date:d})),'supply-name')[0].textContent;
 assert.equal(name('2026-10-20'),'딜러 국채 순포지션(TIPS 제외) 2026-10-20 관측');            // 21일 — 표시 없음
 assert.equal(name('2026-10-19'),'딜러 국채 순포지션(TIPS 제외) 2026-10-19 관측 · 22일 전');
 assert.equal(name('2026-09-10'),'딜러 국채 순포지션(TIPS 제외) 2026-09-10 관측 · 61일 전');
});

test('ktb: table, spreads, head, charts and notices',()=>{
 const t=load();
 t.renderKtb(ktb());
 assert.equal(t.available.korea,true);
 assert.equal(t.ids['ktb-head'].textContent,'2026-11-09 아침 글 기준 · 원문 글');
 assert.deepEqual(walk(t.ids['ktb-head'],n=>n.tag==='a').map(a=>a.attrs.href),['https://t.me/jk_bond/23218']);
 assert.deepEqual(walk(t.ids['ktb-table'],n=>n.tag==='tr').map(r=>r.kids.map(k=>k.textContent)),
  [['만기','금리','전일 대비'],['3년','3.615%','-4.5bp'],['10년','3.855%','+2.0bp'],['30년','3.972%','0.0bp']]);
 assert.equal(t.ids['ktb-spreads'].textContent,'10년−3년 24.0bp · 30년−10년 11.7bp (이 금리로 계산)');
 assert.equal(t.ids['ktb-charts'].kids.length,2);
 assert.ok(t.ids['ktb-charts'].kids.every(k=>k.attrs.class==='panel'));
 assert.deepEqual(t.ids['ktb-notices'].kids.map(k=>k.textContent),['채널 자료 고지','관계없음 고지']);
 assert.ok(KTB_IDS.every(id=>texts(t.ids[id]).every(x=>typeof x==='string')));
});

test('ktb: without notices, rows or a date the section stays hidden and empty',()=>{
 const cases=[ktb({notices:[]}),ktb({notices:['',7]}),ktb({latest:{...ktb().latest,rows:[]}}),
  ktb({latest:{...ktb().latest,rows:[{tenor:'3년',yield:'3.6'}]}}),ktb({latest:{...ktb().latest,date:'2026-11-9'}}),
  ktb({latest:{...ktb().latest,date:'2026-02-31x'}}),ktb({latest:null})];
 for(const k of cases){
  const t=load();
  t.renderKtb(k);
  assert.equal(t.available.korea,undefined,JSON.stringify(k).slice(0,80));
  assert.ok(KTB_IDS.every(id=>t.ids[id].kids.length===0));
  assert.equal(t.calls.length,0);
 }
});

test('ktb: a post older than 7 days says the latest post was not read',()=>{
 const head=d=>{const t=load();t.renderKtb(ktb({latest:{...ktb().latest,date:d}}));return t.ids['ktb-head'].textContent;};
 assert.equal(head('2026-11-03'),'2026-11-03 아침 글 기준 · 원문 글');                          // 7일
 assert.equal(head('2026-11-02'),'2026-11-02 아침 글 기준 · 원문 글 · 최근 글을 받지 못했다 — 아래는 마지막으로 읽은 값이다');
});

test('ktb: the post link is only to a post of that channel',()=>{
 for(const u of ['https://t.me/jk_bond/x','https://t.me/other/1','http://t.me/jk_bond/1','https://elsewhere.invalid/x',
                 'https://t.me/jk_bond/1?x=y','javascript:alert(1)',7,null]){
  const t=load();
  t.renderKtb(ktb({latest:{...ktb().latest,post_url:u}}));
  assert.equal(walk(t.ids['ktb-head'],n=>n.tag==='a').length,0,String(u));
  assert.equal(t.ids['ktb-head'].textContent,'2026-11-09 아침 글 기준 · 원문 글');
 }
});

test('ktb: a missing change is a dash, and bad rows and spreads are dropped',()=>{
 const t=load(), k=ktb();
 k.latest.rows=[{tenor:'3년',yield:3.615,change_bp:null},{tenor:'5년',yield:3.715},{tenor:'10년',yield:3.855,change_bp:'-2'},
  {tenor:'20년',yield:null,change_bp:1},{tenor:7,yield:3.9}];
 k.latest.spreads=[{label:'10년−3년',bp:24.0},{label:'x',bp:'1'},{bp:3}];
 t.renderKtb(k);
 assert.deepEqual(walk(t.ids['ktb-table'],n=>n.tag==='tr').slice(1).map(r=>r.kids.map(k=>k.textContent)),
  [['3년','3.615%','—'],['5년','3.715%','—'],['10년','3.855%','—']]);
 assert.equal(t.ids['ktb-spreads'].textContent,'10년−3년 24.0bp (이 금리로 계산)');
 k.latest.spreads=[];
 const u=load();u.renderKtb(k);
 assert.equal(u.ids['ktb-spreads'].textContent,'');
});

test('ktb: chart values use the table decimals — yields three, spreads one',()=>{
 const t=load(), k=ktb();
 k.charts.push({...k.charts[1],key:'other',unit:'계약'});
 t.renderKtb(k);
 assert.equal(t.calls.length,3);
 const [y,s,o]=t.calls.map(c=>c.o);
 assert.deepEqual([y.height,y.caption,y.notices],[220,true,undefined]);
 assert.deepEqual([3.855,3.615,3.972,4].map(y.format),['3.855%','3.615%','3.972%','4.000%']);
 assert.deepEqual([24,11.7,-0.04,0.04,-3.25].map(s.format),['24.0bp','11.7bp','0.0bp','0.0bp','-3.3bp']);
 assert.equal(o.format,undefined);                                                       // 다른 단위는 기본 꼴
});

test('real charts.js: KTB end labels and read-out match the table; a supply point ending in .477 matches its line',()=>{
 const mk=tag=>{const e=new El(tag);e.addEventListener=()=>{};e.clientWidth=600;e.classList={add(){},remove(){}};e.appendChild=c=>{e.kids.push(c);return c;};return e;};
 const doc={createElement:mk,createElementNS:(ns,t)=>mk(t),documentElement:{dataset:{motion:'off'}}};
 const sc={document:doc,requestAnimationFrame:f=>f(),addEventListener(){}};sc.window=sc;
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../site/charts.js'),'utf8'),sc);
 const t=load({charts:sc.MacroCharts});
 t.renderKtb(ktb());
 const svgs=walk(t.ids['ktb-charts'],n=>n.tag==='svg');
 assert.equal(svgs.length,2);
 assert.ok(svgs[0].attrs['aria-label'].includes('국고 3년 3.615%(2026-11-09)'),svgs[0].attrs['aria-label']);
 assert.ok(svgs[0].attrs['aria-label'].includes('국고 10년 3.855%(2026-11-09)'),svgs[0].attrs['aria-label']);
 assert.deepEqual(walk(svgs[0],n=>n.attrs.class==='ch-end').map(n=>n.textContent).sort(),['3.615%','3.855%']);
 assert.ok(svgs[1].attrs['aria-label'].includes('10년−3년 24.0bp(2026-11-09)'),svgs[1].attrs['aria-label']);
 const p=load({charts:sc.MacroCharts}).supplyPanel(supply());
 const ends=walk(p,n=>n.attrs.class==='ch-end').map(n=>n.textContent);
 assert.deepEqual(ends,['433bn','2565bn']);                                               // 줄의 433bn·2,565bn과 같은 정수
});
