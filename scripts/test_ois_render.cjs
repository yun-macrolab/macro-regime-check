// 국채–OIS 참고(site/ois.js) — 아주 작은 가짜 DOM 위에서 render()를 돌려 글을 본다. 숫자는 지어낸 것이다.
// 실행: node --test scripts/test_ois_render.cjs
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
 const ids={'ois-slot':new El('div')};
 if(opts.noSlot)delete ids['ois-slot'];
 const el=(tag,attrs,...kids)=>{const n=new El(tag);for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,v);for(const c of kids)if(c!==null&&c!==undefined)n.append(c);return n;};
 const link=(text,url)=>/^https:\/\/fred\.stlouisfed\.org\//.test(url)?el('a',{href:url},text):text;   // index.html의 link()와 같은 꼴
 const sc={window:{},document:{getElementById:id=>ids[id]||null},el,link};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../site/ois.js'),'utf8'),sc);
 return {api:sc.window.OisCard,ids};
}
const DTCC={series:'CFTC_CUMULATIVE_RATES',name:'DTCC Data Repository (U.S.) LLC',licence:'cftc-part43-public-dissemination',
 citation:'Source: DTCC Data Repository (U.S.) LLC, CFTC swap data public dissemination (17 CFR Part 43); site calculations'};
const fred=(sid,day='November 16, 2026')=>({series:sid,name:'Board',url:'https://fred.stlouisfed.org/series/'+sid,licence:'public-domain',
 citation:`Board, 제목 ${sid} [${sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/${sid}, ${day}.`});
const ALL=['DGS2','DGS5','DGS10','DGS30'];
function item(key,extra={}){
 return Object.assign({key,ok:true,stale:false,error:null,failed_since:null,name:key+' 이름',date:'2026-11-13',values:{},
  retrieved:'2026-11-16',line:key+' 숫자 줄 2년 +15 · 10년 +40bp',extra:[key+' 덧붙임'],notices:['계산값 고지','단서 고지'],
  sources:[DTCC,...ALL.map(s=>fred(s))]},extra);
}
function data(){return {schema:1,notice:'이 사이트의 규칙 점검에 쓰지 않는 참고 자료다.',order:['level','ten'],items:{level:item('level'),ten:item('ten')}};}

test('card draws both rows in order with the fixed label, source and FRED links',()=>{
 const {api,ids}=load();
 assert.equal(api.render(data()),true);
 const card=ids['ois-slot'].kids[0], text=card.textContent;
 assert.deepEqual(cls(card,'ois-row').map(r=>cls(r,'oil-name')[0].textContent.split(' 이름')[0]),[...api.CARD]);
 assert.deepEqual([...api.CARD],['level','ten']);
 assert.equal(api.LABEL,'참고 — 예측 아님');
 assert.ok(text.startsWith('국채–OIS 스프레드(par) — 2·5·10·30년참고 — 예측 아님'),text.slice(0,40));
 assert.ok(text.includes('level 숫자 줄 2년 +15 · 10년 +40bp')&&text.includes('ten 덧붙임'));
 assert.deepEqual(cls(card,'notices')[0].kids.map(k=>k.textContent),['계산값 고지','단서 고지']);   // 겹치는 고지는 한 번
 const src=cls(card,'source-link').map(n=>n.textContent);
 assert.equal(src[0],api.SOURCE);
 assert.equal(api.SOURCE,DTCC.citation);
 assert.equal(src[1],'국채 par 금리(연준 이사회 H.15, FRED 경유): DGS2 · DGS5 · DGS10 · DGS30');
 const a=walk(card,n=>n.tag==='a');
 assert.deepEqual(a.map(n=>n.attrs.href),ALL.map(s=>'https://fred.stlouisfed.org/series/'+s));   // 링크는 FRED 넷뿐
 assert.equal(walk(card,n=>n.tag==='img').length,0);                                               // 그림(로고) 없음
 assert.ok(text.includes('권장 인용: Board, 제목 DGS2 [DGS2]'));
 assert.ok(!/undefined|NaN|null|\[object/.test(text));
});

test('a missing file draws nothing',()=>{
 const {api,ids}=load();
 for(const d of [null,undefined,{},{items:null},'x',[1]])assert.equal(api.render(d),false);
 assert.equal(ids['ois-slot'].kids.length,0);
});

test('failed rows show a fixed reason only, never remote text',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.ten={key:'ten',ok:false,stale:false,error:'국채 금리(FRED)를 받지 못함',name:'10년 이름'};
 api.render(d);
 assert.ok(ids['ois-slot'].textContent.includes('10년 이름 — 미수신 — 국채 금리(FRED)를 받지 못함'));
 const e=data();
 e.items.ten={key:'ten',ok:false,stale:false,error:'<b>URLError https://bad.invalid</b>',name:'10년 이름'};
 e.items.level=item('level',{notices:[]});                                           // 고지가 없으면 숫자를 싣지 않는다
 const t=load();assert.equal(t.api.render(e),false);
 assert.equal(t.ids['ois-slot'].kids.length,0);                                     // 그릴 칸이 없다
 const f=data();f.items.ten=e.items.ten;
 const u=load();u.api.render(f);
 const text=u.ids['ois-slot'].textContent;
 assert.ok(text.includes('10년 이름 — 자료 없음'));
 assert.ok(!text.includes('bad.invalid')&&!text.includes('URLError'));
});

test('stale rows say why and since when and keep their numbers',()=>{
 const {api,ids}=load();
 const d=data();
 Object.assign(d.items.level,{ok:false,stale:true,error:'새 날 자료가 들어오지 않음',failed_since:'2026-11-16'});
 Object.assign(d.items.ten,{ok:false,stale:true,error:'원격 <글>',failed_since:'어제'});
 api.render(d);
 const late=cls(ids['ois-slot'],'oil-late').map(n=>n.textContent);
 assert.deepEqual(late,['새 날 자료를 받지 못해 받아 둔 날까지로 셉니다 · 새 날 자료가 들어오지 않음 (2026-11-16부터)',
  '새 날 자료를 받지 못해 받아 둔 날까지로 셉니다']);
 assert.ok(ids['ois-slot'].textContent.includes('level 숫자 줄'));
 assert.ok(!ids['ois-slot'].textContent.includes('원격'));
});

test('a broken item date or key is not drawn as numbers',()=>{
 const {api}=load();
 const d=data();d.items.level.date='어제';d.items.ten.key='level';
 assert.equal(api.render(d),false);
 const t=load();const e=data();e.items.level.date='2026-13-45';
 assert.equal(t.api.render(e),true);
 assert.ok(t.ids['ois-slot'].textContent.includes('level 이름 — 자료 없음'));
});

test('no card when the page has no slot',()=>{
 const t=load({noSlot:true});assert.equal(t.api.render(data()),false);
});

test('only FRED series are linked and only well-formed citations are shown',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.level.sources=[DTCC,fred('DGS10'),{series:'DGS2',url:'https://bad.invalid/x',citation:'<script>'},
  {series:'XYZ',url:'https://fred.stlouisfed.org/series/XYZ',citation:fred('XYZ').citation},'x',null];
 d.items.ten.sources=[DTCC,Object.assign(fred('DGS10','November 17, 2026'))];
 d.items.ten.retrieved='2026-11-17';
 api.render(d);
 const card=ids['ois-slot'].kids[0];
 const a=walk(card,n=>n.tag==='a');
 assert.deepEqual(a.map(n=>n.attrs.href),['https://fred.stlouisfed.org/series/DGS10']);     // 낯선 주소는 글자로
 assert.equal(cls(card,'source-link')[1].textContent,'국채 par 금리(연준 이사회 H.15, FRED 경유): DGS2 · DGS10');
 const cite=cls(card,'notices').map(n=>n.textContent).join(' ');
 assert.ok(cite.includes('November 17, 2026'));                                     // 가장 늦게 받은 칸의 인용
 assert.ok(!cite.includes('November 16, 2026')&&!cite.includes('<script>')&&!cite.includes('XYZ'));
 const t=load();const e=data();
 for(const k of ['level','ten'])e.items[k].sources=[DTCC];                           // FRED 출처가 없으면 그 두 줄은 없다
 t.api.render(e);
 assert.equal(cls(t.ids['ois-slot'],'source-link').length,1);
 assert.ok(!t.ids['ois-slot'].textContent.includes('권장 인용'));
});

test('the guide and about text carry the caveats',()=>{
 const {api,ids}=load();
 api.render(data());
 const text=ids['ois-slot'].textContent;
 for(const part of['스와프 스프레드','부호를 뒤집은','같은 시각이 아님','zero(현물)','편의수익','연방기금 OIS 제외',
   '다른 스와프 데이터 저장소','취소된 거래','data/ois_days.json','금리를 예측하지 않습니다'])
  assert.ok(text.includes(part),part);
});

test('the intro is one polite paragraph and does not repeat the data notice',()=>{
 const src=fs.readFileSync(path.join(__dirname,'ois_fetch.py'),'utf8');
 const m=src.match(/^NOTICE = \(([\s\S]*?)\)\n/m);
 assert.ok(m,'ois_fetch.py의 NOTICE를 찾지 못함');
 const notice=[...m[1].matchAll(/"([^"]*)"/g)].map(x=>x[1]).join('');
 assert.ok(notice.length>20);
 const {api,ids}=load();
 const d=data();d.notice=notice;
 api.render(d);
 const card=ids['ois-slot'].kids[0];
 const intro=cls(card,'muted')[0].textContent;
 assert.equal(intro,api.ABOUT);                                                     // 자료 파일의 notice를 덧붙이지 않는다
 assert.ok(!card.textContent.includes(notice.split('. ')[0]));
 const sentences=api.ABOUT.split(/(?<=\.)\s+/);
 assert.equal(sentences.length,2);
 for(const s of sentences)assert.match(s,/니다\.$/,s);                               // 합니다체 한 벌
 for(const part of['DTCC 공개 금리 스와프 거래 보고','규칙 수에 들지 않','금리를 예측하지 않습니다'])
  assert.equal(intro.split(part).length-1,1,part);                                   // 같은 말을 되풀이하지 않는다
});
