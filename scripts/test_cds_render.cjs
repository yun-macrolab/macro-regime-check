// 단일종목 CDS 참고(site/cds.js) — 아주 작은 가짜 DOM 위에서 render()를 돌려 글을 본다. 숫자는 지어낸 것이다.
// 실행: node --test scripts/test_cds_render.cjs
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
const tags=(n,t)=>walk(n,x=>x.tag===t);

function load(opts={}){
 const ids={'cds-slot':new El('div')};
 if(opts.noSlot)delete ids['cds-slot'];
 const el=(tag,attrs,...kids)=>{const n=new El(tag);for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,v);for(const c of kids)if(c!==null&&c!==undefined)n.append(c);return n;};
 const sc={window:{},document:{getElementById:id=>ids[id]||null},el};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../site/cds.js'),'utf8'),sc);
 return {api:sc.window.CdsCard,ids};
}
const NAMES=['오라클','메타','아마존','알파벳','MS','코어위브','브로드컴','엔비디아','AMD','인텔','마이크론','TSMC'];
function item(key,extra={}){
 const table=key==='quotes'
  ?{caption:'5년 호가, bp',columns:['이름','5년 호가','4주 전 대비','1년 전','호가 수'],rows:NAMES.map((n,i)=>[n,String(100+i),'+3','90','7'])}
  :{caption:'새 거래 건수',columns:['이름','최근 28일','1년 전 같은 28일'],rows:NAMES.map((n,i)=>[n,String(10+i),'—'])};
 return Object.assign({key,ok:true,stale:false,error:null,failed_since:null,name:key+' 이름',date:'2026-10-27',values:{},
  retrieved:'2026-10-28',line:key+' 숫자 줄 오라클 123bp',extra:[key+' 덧붙임'],table,notices:['계산값 고지','단서 고지'],
  sources:[{series:'SEC_CUMULATIVE_CREDITS',name:'DTCC Data Repository (U.S.) LLC',licence:'x',citation:'c'}]},extra);
}
function data(){return {schema:1,notice:'참고 자료다.',order:['quotes','trades'],items:{quotes:item('quotes'),trades:item('trades')}};}

test('card draws both rows in order with tables, label and the fixed source line',()=>{
 const {api,ids}=load();
 assert.equal(api.render(data()),true);
 const card=ids['cds-slot'].kids[0], text=card.textContent;
 assert.deepEqual(cls(card,'cds-row').map(r=>cls(r,'oil-name')[0].textContent.split(' 이름')[0]),[...api.CARD]);
 assert.equal(api.LABEL,'참고 — 신용 사건 예측 아님');
 assert.ok(text.includes('참고 — 신용 사건 예측 아님'));
 const t=tags(card,'table');
 assert.equal(t.length,2);
 assert.equal(walk(t[0],n=>n.tag==='th'&&n.attrs.scope==='row').length,12);                       // 이름마다 한 줄
 assert.deepEqual(walk(t[0],n=>n.tag==='th'&&n.attrs.scope==='col').map(n=>n.textContent),['이름','5년 호가','4주 전 대비','1년 전','호가 수']);
 assert.ok(!text.includes('quotes 숫자 줄'));                                                       // 표가 있으면 숫자 줄 대신 표
 assert.ok(text.includes('quotes 덧붙임')&&text.includes('trades 덧붙임'));
 assert.deepEqual(cls(card,'notices')[0].kids.map(k=>k.textContent),['계산값 고지','단서 고지']);   // 겹치는 고지는 한 번
 assert.equal(cls(card,'source-link')[0].textContent,api.SOURCE);
 assert.equal(api.SOURCE,'Source: DTCC Data Repository (U.S.) LLC, SEC security-based swap public dissemination (Reg SBSR); site calculations');
 assert.equal(walk(card,n=>n.tag==='a'||n.tag==='img').length,0);                                  // 링크·그림(로고) 없음
 assert.ok(!/undefined|NaN|null/.test(text));
});

test('a missing file draws nothing',()=>{
 const {api,ids}=load();
 for(const d of [null,undefined,{},{items:null},'x',[1]])assert.equal(api.render(d),false);
 assert.equal(ids['cds-slot'].kids.length,0);
});

test('a malformed table falls back to the numbers line',()=>{
 for(const bad of [null,'x',{columns:['a'],rows:[['b']]},{columns:['a','b'],rows:[['c']]},{columns:['a','b'],rows:[]},
   {columns:['a','b'],rows:[['c',3]]},{columns:'ab',rows:[]}]){
  const {api,ids}=load();
  const d=data();d.items.quotes.table=bad;
  assert.equal(api.render(d),true);
  const rows=cls(ids['cds-slot'],'cds-row');
  assert.ok(rows[0].textContent.includes('quotes 숫자 줄 오라클 123bp'),JSON.stringify(bad));
  assert.equal(tags(rows[0],'table').length,0);
  assert.equal(tags(rows[1],'table').length,1);
 }
});

test('failed rows show a fixed reason only, never remote text',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.trades={key:'trades',ok:false,stale:false,error:'수신 실패',name:'건수 이름'};
 api.render(d);
 assert.ok(ids['cds-slot'].textContent.includes('건수 이름 — 미수신 — 수신 실패'));
 const e=data();
 e.items.trades={key:'trades',ok:false,stale:false,error:'<b>URLError https://bad.invalid</b>',name:'건수 이름'};
 e.items.quotes=item('quotes',{notices:[]});                                         // 고지가 없으면 숫자를 싣지 않는다
 const t=load();t.api.render(e);
 assert.equal(t.ids['cds-slot'].kids.length,0);                                     // 그릴 칸이 없다
 const f=data();f.items.trades=e.items.trades;
 const u=load();u.api.render(f);
 const text=u.ids['cds-slot'].textContent;
 assert.ok(text.includes('건수 이름 — 자료 없음'));
 assert.ok(!text.includes('bad.invalid')&&!text.includes('URLError'));
});

test('stale rows say why and since when and keep their numbers',()=>{
 const {api,ids}=load();
 const d=data();
 Object.assign(d.items.quotes,{ok:false,stale:true,error:'새 날 자료가 들어오지 않음',failed_since:'2026-10-28'});
 Object.assign(d.items.trades,{ok:false,stale:true,error:'원격 <글>',failed_since:'어제'});
 api.render(d);
 const late=cls(ids['cds-slot'],'oil-late').map(n=>n.textContent);
 assert.deepEqual(late,['새 날 자료를 받지 못해 받아 둔 날까지로 셉니다 · 새 날 자료가 들어오지 않음 (2026-10-28부터)',
  '새 날 자료를 받지 못해 받아 둔 날까지로 셉니다']);
 assert.equal(tags(ids['cds-slot'],'table').length,2);
 assert.ok(!ids['cds-slot'].textContent.includes('원격'));
});

test('a broken item date or key is not drawn as numbers',()=>{
 const {api,ids}=load();
 const d=data();d.items.quotes.date='어제';d.items.trades.key='quotes';
 assert.equal(api.render(d),false);
 const t=load();const e=data();e.items.quotes.date='2026-13-45';
 assert.equal(t.api.render(e),true);
 assert.ok(t.ids['cds-slot'].textContent.includes('quotes 이름 — 자료 없음'));
});

test('no card when the page has no slot',()=>{
 const t=load({noSlot:true});assert.equal(t.api.render(data()),false);
});

test('the guide and about text carry the caveats',()=>{
 const {api,ids}=load();
 api.render(data());
 const text=ids['cds-slot'].textContent;
 for(const part of['DTCC 쪽 보고','ICE Trade Vault','중간값(mid)','취소된 거래','신용 사건이나 금리를 예측하지 않습니다'])
  assert.ok(text.includes(part),part);
});

test('the intro is one polite paragraph and does not repeat the data notice',()=>{
 const src=fs.readFileSync(path.join(__dirname,'cds_fetch.py'),'utf8');
 const m=src.match(/^NOTICE = \(([\s\S]*?)\)\n/m);
 assert.ok(m,'cds_fetch.py의 NOTICE를 찾지 못함');
 const notice=[...m[1].matchAll(/"([^"]*)"/g)].map(x=>x[1]).join('');
 assert.ok(notice.length>20);
 const {api,ids}=load();
 const d=data();d.notice=notice;
 api.render(d);
 const card=ids['cds-slot'].kids[0];
 const intro=cls(card,'muted')[0].textContent;
 assert.equal(intro,api.ABOUT);                                                     // 자료 파일의 notice를 덧붙이지 않는다
 assert.ok(!card.textContent.includes(notice.split('. ')[0]));
 const sentences=api.ABOUT.split(/(?<=\.)\s+/);
 assert.equal(sentences.length,2);
 for(const s of sentences)assert.match(s,/니다\.$/,s);                               // 합니다체 한 벌
 for(const part of['DTCC 공개 거래 보고','규칙 수에 들지 않','신용 사건이나 금리를 예측하지 않습니다'])
  assert.equal(intro.split(part).length-1,1,part);                                   // 같은 말을 되풀이하지 않는다
});
