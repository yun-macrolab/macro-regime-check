// 유가·에너지 참고(site/oil.js) — 아주 작은 가짜 DOM 위에서 render()를 돌려 글을 본다. 숫자는 지어낸 것이다.
// 실행: node --test scripts/test_oil_render.cjs
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

class El {
 constructor(tag){this.tag=tag;this.kids=[];this.attrs={};this.hidden=false;}
 append(...xs){for(const x of xs)this.kids.push(typeof x==='string'?{text:x}:x);}
 replaceChildren(...xs){this.kids=[];for(const x of xs)this.kids.push(typeof x==='string'||x===null||x===undefined?{text:String(x)}:x);}
 setAttribute(k,v){this.attrs[k]=String(v);}
 get textContent(){return this.kids.map(k=>k instanceof El?k.textContent:k.text).join('');}
}
const walk=(n,f,out=[])=>{if(n instanceof El){if(f(n))out.push(n);n.kids.forEach(k=>walk(k,f,out));}return out;};
const cls=(n,c)=>walk(n,x=>(x.attrs.class||'').split(' ').includes(c));

function load(opts={}){
 const ids={'oil-slot':new El('div'),'korea-oil':new El('div')};ids['korea-oil'].hidden=true;
 if(opts.noSlot)delete ids['oil-slot'];
 const charts=[];
 const el=(tag,attrs,...kids)=>{const n=new El(tag);for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,v);for(const c of kids)if(c!==null&&c!==undefined)n.append(c);return n;};
 const link=(text,url)=>/^https:\/\/fred\.stlouisfed\.org\//.test(url)?el('a',{href:url},text):text;   // index.html의 link()와 같은 꼴
 const win=opts.noCharts?{}:{MacroCharts:{lineChart:(spec,o)=>{charts.push([spec,o]);if(opts.chartThrows)throw new Error('x');return new El('figure');}}};
 const sc={window:win,document:{getElementById:id=>ids[id]||null},el,link};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../site/oil.js'),'utf8'),sc);
 return {api:sc.window.OilEnergy,ids,charts};
}
const src=sid=>({series:sid,name:'X',url:'https://fred.stlouisfed.org/series/'+sid,licence:'public-domain'});
function item(key,extra={}){
 return Object.assign({key,ok:true,stale:false,error:null,failed_since:null,name:key+' 이름',date:'2026-10-23',
  values:{},retrieved:'2026-10-30',line:key+' 숫자 줄 +12.3%',extra:[key+' 덧붙임'],notices:['계산값 고지'],sources:[src('DCOILBRENTEU')]},extra);
}
const IMF='두바이 원유 가격(POILDUBUSDM): Copyright © International Monetary Fund. 지어낸 고지';
function data(){
 const keys=['crude','base','products','cracks','spread','cpi','i4','bei','state','supply','korea','dubai'];
 const items=Object.fromEntries(keys.map(k=>[k,item(k)]));
 items.base.chart={key:'oil_base',title:'t',unit:'%',years:5,zero:true,threshold:null,note:'n',source_note:'s',notices:[],
  lines:[{key:'yoy',label:'a',role:'main',series:[],derived:false,points:[['2026-09-01',12.34]]}]};
 items.bei.notices=['계산값 고지','인용 고지'];items.bei.sources=[src('T5YIE')];
 items.dubai.notices=['계산값 고지',IMF];items.dubai.sources=[src('POILDUBUSDM'),src('DEXKOUS')];
 return {schema:1,notice:'참고 자료다.',order:keys,items};
}

test('card draws every row in order and the korea line, with no stray words',()=>{
 const {api,ids}=load();
 assert.equal(api.render(data()),true);
 const card=ids['oil-slot'].kids[0], text=card.textContent;
 const rows=cls(card,'oil-row').map(r=>cls(r,'oil-name')[0].textContent.split(' 이름')[0]);
 assert.deepEqual(rows,[...api.CARD]);
 assert.equal(api.LABEL,'참고 — 유가·금리 예측 아님');                                              // 이름표 글을 고정한다
 assert.ok(text.includes('참고 — 유가·금리 예측 아님'));
 assert.ok(!/undefined|NaN|null/.test(text));
 assert.deepEqual(cls(card,'notices')[0].kids.map(k=>k.textContent),['계산값 고지','인용 고지']);   // 겹치는 고지는 한 번
 assert.deepEqual(walk(card,n=>n.tag==='a').map(a=>a.textContent),['DCOILBRENTEU','T5YIE','POILDUBUSDM','DEXKOUS']);   // 시리즈마다 한 번
 const k=ids['korea-oil'];
 assert.equal(k.hidden,false);
 assert.ok(k.textContent.includes('korea 숫자 줄'));
 assert.ok(!/undefined|NaN|null/.test(k.textContent));
 assert.ok(!text.includes('korea 숫자 줄'));                                                        // 한국 줄은 카드에 없다
 assert.ok(!text.includes('dubai 숫자 줄'));
 assert.deepEqual([...api.KOREA],['korea','dubai']);
});

test('korea box draws Brent then Dubai with the IMF notice once',()=>{
 const {api,ids}=load();
 api.render(data());
 const k=ids['korea-oil'], t=k.textContent;
 assert.ok(t.indexOf('Brent × 원/달러')<t.indexOf('korea 숫자 줄'));
 assert.ok(t.indexOf('korea 숫자 줄')<t.indexOf('두바이 × 원/달러'));
 assert.ok(t.indexOf('두바이 × 원/달러')<t.indexOf('dubai 숫자 줄'));
 assert.ok(t.includes('dubai 덧붙임'));
 assert.ok(t.includes('자료: EIA(Brent) · IMF(두바이) · 연준(원/달러), FRED 경유'));
 const notes=cls(k,'notices');
 assert.equal(notes.length,1);
 assert.deepEqual(notes[0].kids.map(x=>x.textContent),[IMF]);                                       // 한국 줄과 겹치는 고지는 빼고
 assert.equal(cls(k,'oil-num').length,2);
});

test('a failed dubai item shows a fixed reason and no IMF notice, Brent stays',()=>{
 for(const [bad,want] of [[{key:'dubai',ok:false,stale:false,error:'수신 실패',name:'x'},'미수신(수신 실패)'],
   [{key:'dubai',ok:false,error:'<i>원문 https://bad.invalid</i>'},'자료 없음'],
   [Object.assign(item('dubai'),{notices:[]}),'자료 없음']]){
  const {api,ids}=load();
  const d=data();d.items.dubai=bad;
  api.render(d);
  const t=ids['korea-oil'].textContent;
  assert.ok(t.includes('korea 숫자 줄'));
  assert.ok(t.includes('두바이 × 원/달러 참고 — 유가·금리 예측 아님 — '+want),t);
  assert.ok(!t.includes('bad.invalid'));
  assert.ok(!t.includes('Copyright'));
  assert.ok(t.includes('자료: EIA(Brent) · 연준(원/달러)'));                                       // 두바이를 그리지 않으면 IMF도 없다
  assert.equal(cls(ids['korea-oil'],'notices').length,0);
 }
});

test('dubai alone draws, stale dubai says since when',()=>{
 const {api,ids}=load();
 const d=data();delete d.items.korea;Object.assign(d.items.dubai,{ok:false,stale:true,error:'수신 실패',failed_since:'2026-10-29'});
 assert.equal(api.render(d),true);
 const k=ids['korea-oil'];
 assert.equal(k.hidden,false);
 assert.ok(!k.textContent.includes('Brent × 원/달러'));
 assert.ok(k.textContent.includes('dubai 숫자 줄'));
 assert.ok(cls(k,'oil-late')[0].textContent.includes('(2026-10-29부터)'));
 const notes=cls(k,'notices')[0].kids.map(x=>x.textContent);
 assert.deepEqual(notes,['계산값 고지',IMF]);                                                     // 한국 줄이 없으면 계산값 고지도 여기서
});

test('guide explains the added lines',()=>{
 const {api,ids}=load();
 api.render(data());
 const g=cls(ids['oil-slot'],'rule-guide')[0].textContent;
 for(const part of ['실질 WTI 분위','이번 달 평균','I4 · 물가 꼬리표',"'공급형(에너지)'","'에너지 하락'",'P+ · P0 · Pd · P−',
  '측정 기록','미국 공급 반응','두바이 × 원/달러','2026-10-14','예측이 아니며'])assert.ok(g.includes(part),part);
});

test('a missing file draws nothing',()=>{
 const {api,ids}=load();
 for(const d of [null,undefined,{},{items:null},'x'])assert.equal(api.render(d),false);
 assert.equal(ids['oil-slot'].kids.length,0);
 assert.equal(ids['korea-oil'].hidden,true);
});

test('state row always carries the fixed definition note',()=>{
 const {api,ids}=load();
 const d=data();d.items.state.extra=[];                                          // 자료 쪽 정의가 빠져도
 api.render(d);
 const st=cls(ids['oil-slot'],'oil-state')[0];
 assert.ok(st.textContent.includes(api.STATE_NOTE));
 assert.ok(api.STATE_NOTE.includes('예측하지 않습니다'));
});

test('each row draws its explanation lines, so the state definition from the data is shown',()=>{
 const {api,ids}=load();
 const d=data();d.items.state.extra=['정의(고정): 지어낸 정의 글','둘째 줄'];
 api.render(d);
 const st=cls(ids['oil-slot'],'oil-state')[0];
 assert.ok(st.textContent.includes('정의(고정): 지어낸 정의 글'));
 assert.ok(st.textContent.includes('둘째 줄'));
 assert.ok(ids['oil-slot'].textContent.includes('crude 덧붙임'));
});

test('failed rows show a fixed reason only, never remote text',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.cpi={key:'cpi',ok:false,stale:false,error:'수신 실패',name:'CPI 이름'};
 d.items.bei={key:'bei',ok:false,stale:false,error:'<b>원문 오류 https://bad.invalid</b>',name:'BEI 이름'};
 d.items.spread=item('spread',{notices:[]});                                       // 고지가 없으면 숫자를 싣지 않는다
 api.render(d);
 const text=ids['oil-slot'].textContent;
 assert.ok(text.includes('CPI 이름 — 미수신(수신 실패)'));
 assert.ok(text.includes('BEI 이름 — 자료 없음'));
 assert.ok(!text.includes('bad.invalid'));
 assert.ok(!text.includes('spread 숫자 줄'));
});

test('stale rows say since when and keep their numbers',()=>{
 const {api,ids}=load();
 const d=data();Object.assign(d.items.crude,{ok:false,stale:true,error:'수신 실패',failed_since:'2026-10-28'});
 Object.assign(d.items.korea,{ok:false,stale:true,error:'수신 실패',failed_since:'2026-10-28'});
 api.render(d);
 assert.ok(cls(ids['oil-slot'],'oil-late')[0].textContent.includes('(2026-10-28부터)'));
 assert.ok(ids['korea-oil'].textContent.includes('(2026-10-28부터)'));
 assert.ok(ids['oil-slot'].textContent.includes('crude 숫자 줄'));
});

test('a broken korea item shows one fixed line, a missing one hides it, and the card stays',()=>{
 const {api,ids}=load();
 const d=data();d.items.korea={key:'korea',date:'어제',line:'x',notices:['n']};delete d.items.dubai;
 assert.equal(api.render(d),true);
 const k=ids['korea-oil'];
 assert.equal(k.hidden,false);
 assert.ok(k.textContent.endsWith('Brent × 원/달러 참고 — 유가·금리 예측 아님 — 자료 없음'),k.textContent);
 assert.ok(!k.textContent.includes('어제'));
 assert.equal(cls(ids['oil-slot'],'oil-row').length,api.CARD.length);
 const t=load();const e=data();delete e.items.korea;delete e.items.dubai;
 assert.equal(t.api.render(e),true);
 assert.equal(t.ids['korea-oil'].hidden,true);
});

test('a first korea failure without a previous value shows the reason',()=>{
 for(const why of ['수신 실패','수신 실패 · 묵은 캐시는 싣지 않음']){
  const {api,ids}=load();
  const d=data();d.items.korea={key:'korea',ok:false,stale:false,error:why,failed_since:'2026-10-30',name:'Brent × 원/달러',
   sources:[src('DEXKOUS')]};delete d.items.dubai;
  api.render(d);
  const k=ids['korea-oil'];
  assert.equal(k.hidden,false);
  assert.equal(k.kids.length,1);                                                                       // 한 줄
  assert.equal(k.textContent,`Brent × 원/달러 참고 — 유가·금리 예측 아님 — 미수신(${why})`);
  assert.ok(!/undefined|NaN|null/.test(k.textContent));
 }
});

test('chart uses one-decimal values and failures only drop the chart',()=>{
 const {api,charts}=load();
 api.render(data());
 assert.equal(charts.length,1);
 const fmt=charts[0][1].format;
 assert.deepEqual([fmt(12.36),fmt(-3.26),fmt(0.01),fmt(-0.04),fmt(100)],['+12.4%','-3.3%','0.0%','0.0%','+100.0%']);
 for(const o of [{chartThrows:true},{noCharts:true}]){const t=load(o);assert.equal(t.api.render(data()),true);assert.equal(cls(t.ids['oil-slot'],'oil-row').length,t.api.CARD.length);}
});

test('no card when the page has no slot or nothing is usable',()=>{
 const t=load({noSlot:true});assert.equal(t.api.render(data()),false);assert.equal(t.ids['korea-oil'].hidden,false);   // 한국 줄은 따로
 const u=load();const d=data();for(const k of u.api.CARD)d.items[k].notices=[];
 assert.equal(u.api.render(d),false);assert.equal(u.ids['oil-slot'].kids.length,0);
});

const cited=(sid,on='October 30, 2026')=>Object.assign(src(sid),{licence:'citation-required',
 citation:`Org ${sid}, Title [${sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/${sid}, ${on}.`});
function citedData(){
 const d=data();
 d.items.bei.sources=[cited('T5YIE'),cited('T5YIFR')];
 d.items.crude.sources=[Object.assign(src('DCOILBRENTEU'),{citation:'Org B, Title [DCOILBRENTEU], retrieved from FRED, X; u, October 30, 2026.'})];
 d.items.dubai.sources=[cited('POILDUBUSDM'),src('DEXKOUS')];
 return d;
}

test('citation-required sources show their FRED citation as text where the row is drawn',()=>{
 const {api,ids}=load();
 api.render(citedData());
 const card=ids['oil-slot'].kids[0];
 const lines=cls(card,'cite-lines');
 assert.equal(lines.length,1);
 assert.deepEqual(lines[0].kids.map(k=>k.textContent),['T5YIE','T5YIFR'].map(sid=>
  `권장 인용: Org ${sid}, Title [${sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/${sid}, October 30, 2026.`));
 assert.ok(lines[0].kids.every(k=>k.attrs.class==='muted'));
 assert.ok(!card.textContent.includes('Title [DCOILBRENTEU]'));                       // 공공 자료는 인용 줄 없음
 assert.ok(!card.textContent.includes('Title [POILDUBUSDM]'));                        // 두바이는 한국 시장 줄 쪽
 const k=ids['korea-oil'];
 const kl=cls(k,'cite-lines');
 assert.equal(kl.length,1);
 assert.deepEqual(kl[0].kids.map(x=>x.textContent),['권장 인용: Org POILDUBUSDM, Title [POILDUBUSDM], retrieved from FRED, '+
  'Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/POILDUBUSDM, October 30, 2026.']);
 assert.ok(k.textContent.indexOf(IMF)<k.textContent.indexOf('권장 인용'));                // IMF 고지 뒤에
});

test('no citation line when the row is not drawn or the citation is malformed',()=>{
 let t=load();let d=citedData();d.items.bei={key:'bei',ok:false,stale:false,error:'수신 실패',name:'BEI 이름'};
 d.items.dubai={key:'dubai',ok:false,stale:false,error:'수신 실패',name:'x'};
 t.api.render(d);
 assert.equal(cls(t.ids['oil-slot'],'cite-lines').length,0);
 assert.equal(cls(t.ids['korea-oil'],'cite-lines').length,0);
 assert.ok(!t.ids['korea-oil'].textContent.includes('POILDUBUSDM'));
 t=load();d=citedData();d.items.bei.sources[0].citation='<i>x</i>, retrieved from y, May 1, 2026.';d.items.bei.sources[1].citation=3;
 t.api.render(d);
 assert.equal(cls(t.ids['oil-slot'],'cite-lines').length,0);
 assert.ok(!t.ids['oil-slot'].textContent.includes('<i>'));
});

test('the same series is cited once, from the latest retrieval',()=>{
 const {api,ids}=load();
 const d=citedData();
 d.items.i4.sources=[cited('T5YIE','October 12, 2026')];d.items.i4.retrieved='2026-10-12';
 api.render(d);
 const t=cls(ids['oil-slot'],'cite-lines')[0].kids.map(k=>k.textContent);
 assert.equal(t.length,2);
 assert.ok(t[0].endsWith('T5YIE, October 30, 2026.'),t[0]);
});

test('the intro is one register and does not repeat the data notice',()=>{
 const {api,ids}=load();
 const d=data();d.notice='이 사이트의 규칙 점검에 쓰지 않는 참고 자료다. 유가나 금리를 예측하지 않는다.';
 api.render(d);
 const card=ids['oil-slot'].kids[0];
 assert.equal(card.kids[1].textContent,api.ABOUT);
 assert.ok(!card.textContent.includes('참고 자료다.'));
 for(const t of api.ABOUT.split(/(?<=\.)\s+/).filter(Boolean))assert.ok(/니다\.$/.test(t),t);
 assert.ok(api.ABOUT.includes('유가나 금리를 예측하지 않습니다'));
});
