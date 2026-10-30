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
function data(){
 const keys=['crude','base','products','cracks','spread','cpi','bei','state','korea'];
 const items=Object.fromEntries(keys.map(k=>[k,item(k)]));
 items.base.chart={key:'oil_base',title:'t',unit:'%',years:5,zero:true,threshold:null,note:'n',source_note:'s',notices:[],
  lines:[{key:'yoy',label:'a',role:'main',series:[],derived:false,points:[['2026-09-01',12.34]]}]};
 items.bei.notices=['계산값 고지','인용 고지'];items.bei.sources=[src('T5YIE')];
 return {schema:1,notice:'참고 자료다.',order:keys,items};
}

test('card draws every row in order and the korea line, with no stray words',()=>{
 const {api,ids}=load();
 assert.equal(api.render(data()),true);
 const card=ids['oil-slot'].kids[0], text=card.textContent;
 const rows=cls(card,'oil-row').map(r=>cls(r,'oil-name')[0].textContent.split(' 이름')[0]);
 assert.deepEqual(rows,[...api.CARD]);
 assert.ok(text.includes(api.LABEL));
 assert.ok(!/undefined|NaN|null/.test(text));
 assert.deepEqual(cls(card,'notices')[0].kids.map(k=>k.textContent),['계산값 고지','인용 고지']);   // 겹치는 고지는 한 번
 assert.equal(walk(card,n=>n.tag==='a').length,2);                                                   // FRED 링크, 시리즈마다 한 번
 const k=ids['korea-oil'];
 assert.equal(k.hidden,false);
 assert.ok(k.textContent.includes('korea 숫자 줄'));
 assert.ok(!/undefined|NaN|null/.test(k.textContent));
 assert.ok(!text.includes('korea 숫자 줄'));                                                        // 한국 줄은 카드에 없다
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

test('a broken korea item hides the line but the card stays',()=>{
 const {api,ids}=load();
 const d=data();d.items.korea={key:'korea',date:'어제',line:'x',notices:['n']};
 assert.equal(api.render(d),true);
 assert.equal(ids['korea-oil'].hidden,true);
 assert.equal(cls(ids['oil-slot'],'oil-row').length,8);
});

test('chart uses one-decimal values and failures only drop the chart',()=>{
 const {api,charts}=load();
 api.render(data());
 assert.equal(charts.length,1);
 const fmt=charts[0][1].format;
 assert.deepEqual([fmt(12.36),fmt(-3.26),fmt(0.01),fmt(-0.04),fmt(100)],['+12.4%','-3.3%','0.0%','0.0%','+100.0%']);
 for(const o of [{chartThrows:true},{noCharts:true}]){const t=load(o);assert.equal(t.api.render(data()),true);assert.equal(cls(t.ids['oil-slot'],'oil-row').length,8);}
});

test('no card when the page has no slot or nothing is usable',()=>{
 const t=load({noSlot:true});assert.equal(t.api.render(data()),false);assert.equal(t.ids['korea-oil'].hidden,false);   // 한국 줄은 따로
 const u=load();const d=data();for(const k of u.api.CARD)d.items[k].notices=[];
 assert.equal(u.api.render(d),false);assert.equal(u.ids['oil-slot'].kids.length,0);
});
