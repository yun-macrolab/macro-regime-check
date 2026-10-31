// 지준·재정 참고(site/liquidity.js) — 아주 작은 가짜 DOM 위에서 render()를 돌려 글을 본다. 숫자는 지어낸 것이다.
// 실행: node --test scripts/test_liquidity_render.cjs
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
 const ids={'liquidity-slot':new El('div')};
 if(opts.noSlot)delete ids['liquidity-slot'];
 const el=(tag,attrs,...kids)=>{const n=new El(tag);for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,v);for(const c of kids)if(c!==null&&c!==undefined)n.append(c);return n;};
 const link=(text,url)=>/^https:\/\/fred\.stlouisfed\.org\//.test(url)?el('a',{href:url},text):text;   // index.html의 link()와 같은 꼴
 const sc={window:{},document:{getElementById:id=>ids[id]||null},el,link};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../site/liquidity.js'),'utf8'),sc);
 return {api:sc.window.LiquidityCard,ids};
}
const src=sid=>({series:sid,name:'X',url:'https://fred.stlouisfed.org/series/'+sid,licence:'public-domain'});
function item(key,extra={}){
 return Object.assign({key,ok:true,stale:false,error:null,failed_since:null,name:key+' 이름',date:'2026-10-28',
  values:{},retrieved:'2026-10-30',line:key+' 숫자 줄 -12bn',extra:[key+' 덧붙임'],notices:['계산값 고지'],sources:[src('GDP')]},extra);
}
function data(){
 const keys=['reserves','rule','fiscal'];
 const items=Object.fromEntries(keys.map(k=>[k,item(k)]));
 items.reserves.sources=['WRBWFRBL','WDTGAL'].map(src);
 return {schema:1,notice:'참고 자료다.',order:keys,items};
}

test('card draws every row in order with the fixed label and no stray words',()=>{
 const {api,ids}=load();
 assert.equal(api.render(data()),true);
 const card=ids['liquidity-slot'].kids[0], text=card.textContent;
 const rows=cls(card,'liq-row').map(r=>cls(r,'oil-name')[0].textContent.split(' 이름')[0]);
 assert.deepEqual(rows,[...api.CARD]);
 assert.deepEqual([...api.CARD],['reserves','rule','fiscal']);
 assert.equal(api.LABEL,'참고 — 판정 없음');                                                     // 이름표 글을 고정한다
 assert.equal(cls(card,'reference-label')[0].textContent,'참고 — 판정 없음');
 assert.ok(text.startsWith('지준·재정참고 — 판정 없음'),text.slice(0,40));
 assert.equal(card.kids[1].textContent,api.ABOUT);                                             // 머리 안내는 ABOUT 하나
 assert.ok(!text.includes('참고 자료다.'));                                                     // 자료 파일의 notice(한다체)는 겹쳐 싣지 않는다
 for(const t of api.ABOUT.split(/(?<=\.)\s+/).filter(Boolean))assert.ok(/니다\.$/.test(t),t);    // 합니다체 하나
 assert.ok(!/undefined|NaN|null/.test(text));
 assert.deepEqual(cls(card,'notices')[0].kids.map(k=>k.textContent),['계산값 고지']);           // 겹치는 고지는 한 번
 assert.deepEqual(walk(card,n=>n.tag==='a').map(a=>a.textContent),['WRBWFRBL','WDTGAL','GDP']);  // FRED 링크, 시리즈마다 한 번
 assert.ok(cls(card,'oil-card').length===1&&cls(card,'liq-card').length===1);                 // 유가 카드의 겉모양을 함께 쓴다
});

test('each row shows its date, number line and explanation lines',()=>{
 const {ids,api}=load();
 const d=data();d.items.rule.extra=['첫 줄','둘째 줄'];
 api.render(d);
 const r=cls(ids['liquidity-slot'],'liq-row')[1];
 assert.ok(r.textContent.includes('rule 이름 2026-10-28'));
 assert.equal(cls(r,'oil-num')[0].textContent,'rule 숫자 줄 -12bn');
 assert.ok(r.textContent.includes('첫 줄')&&r.textContent.includes('둘째 줄'));
});

test('the guide carries the fixed definitions and the measurement record',()=>{
 const {ids,api}=load();
 api.render(data());
 const g=cls(ids['liquidity-slot'],'rule-guide')[0];
 assert.ok(g.textContent.startsWith('읽는 법 — 정의와 측정 기록'));
 const heads=g.kids.filter(k=>k.tag==='p').map(p=>p.kids[0].textContent);
 assert.deepEqual(heads,['부호는 지준 쪽','수요일 수준과 주 평균','규칙 하한 대비','재정수지 · 이자 · 단기채','측정 기록']);
 const rec=g.kids.filter(k=>k.tag==='p')[4].textContent;
 assert.ok(rec.includes('2026-10-28')&&rec.includes('0.27')&&rec.includes('금리를 예측하지 않습니다'),rec);
});

test('a missing file draws nothing',()=>{
 const {api,ids}=load();
 for(const d of [null,undefined,{},{items:null},{items:[]},'x'])assert.equal(api.render(d),false);
 assert.equal(ids['liquidity-slot'].kids.length,0);
});

test('failed rows show a fixed reason only, never remote text',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.rule={key:'rule',ok:false,stale:false,error:'수신 실패 · 묵은 캐시는 싣지 않음',name:'규칙 이름'};
 d.items.fiscal={key:'fiscal',ok:false,stale:false,error:'<b>원문 오류 https://bad.invalid</b>',name:'재정 이름'};
 d.items.reserves=item('reserves',{notices:[]});                                       // 고지가 없으면 숫자를 싣지 않는다
 assert.equal(api.render(d),false);                                                  // 그린 칸이 없으면 카드도 없다
 d.items.reserves=item('reserves');
 assert.equal(api.render(d),true);
 const text=ids['liquidity-slot'].textContent;
 assert.ok(text.includes('규칙 이름 — 미수신(수신 실패 · 묵은 캐시는 싣지 않음)'));
 assert.ok(text.includes('재정 이름 — 자료 없음'));
 assert.ok(!text.includes('bad.invalid'));
 assert.ok(!/undefined|NaN|null/.test(text));
});

test('rows with a wrong key, bad date or empty line are not drawn as numbers',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.reserves=item('rule');                                                      // 자리와 key가 다르다
 d.items.rule=item('rule',{date:'어제'});
 d.items.fiscal=item('fiscal',{line:''});
 assert.equal(api.render(d),false);
 const e=data();e.items.rule=item('rule',{date:'2026-13-45'});e.items.fiscal=item('fiscal',{extra:[1,null,'남는 줄']});
 assert.equal(api.render(e),true);
 const text=ids['liquidity-slot'].textContent;
 assert.ok(text.includes('rule 이름 — 자료 없음'));
 assert.ok(!text.includes('2026-13-45'));
 const fiscal=cls(ids['liquidity-slot'],'liq-row')[2];
 assert.deepEqual(cls(fiscal,'muted').map(n=>n.textContent),['남는 줄']);                  // 글이 아닌 줄은 뺀다
 assert.ok(!/null|undefined/.test(text));
});

test('stale rows say since when and keep their numbers',()=>{
 const {api,ids}=load();
 const d=data();Object.assign(d.items.reserves,{ok:false,stale:true,error:'수신 실패',failed_since:'2026-10-29'});
 Object.assign(d.items.rule,{ok:false,stale:true,error:'수신 실패',failed_since:'언젠가'});
 Object.assign(d.items.fiscal,{stale:'true'});                                       // true 그 값일 때만
 api.render(d);
 const late=cls(ids['liquidity-slot'],'oil-late').map(n=>n.textContent);
 assert.deepEqual(late,['이번 갱신의 값을 싣지 못해 직전에 받은 값을 싣습니다 (2026-10-29부터)','이번 갱신의 값을 싣지 못해 직전에 받은 값을 싣습니다']);
 assert.ok(ids['liquidity-slot'].textContent.includes('reserves 숫자 줄'));
});

test('source links skip odd series names and unusable rows',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.rule.sources=[src('WRESBAL'),{series:'<x>',url:'https://fred.stlouisfed.org/series/x'},'GDP',null];
 d.items.fiscal={key:'fiscal',ok:false,error:'수신 실패',sources:[src('MTSDS133FMS')]};
 api.render(d);
 const links=walk(ids['liquidity-slot'],n=>n.tag==='a').map(a=>a.textContent);
 assert.deepEqual(links,['WRBWFRBL','WDTGAL','WRESBAL']);
});

test('no card when the page has no slot',()=>{
 const t=load({noSlot:true});
 assert.equal(t.api.render(data()),false);
});
