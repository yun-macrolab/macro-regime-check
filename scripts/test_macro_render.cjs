// 달러 · 기대인플레이션 · 성장 · 금융 여건 참고(site/macro.js) — 아주 작은 가짜 DOM 위에서 render()를 돌려 글을 본다. 숫자는 지어낸 것이다.
// 실행: node --test scripts/test_macro_render.cjs
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
const SLOTS=['dollar-slot','expinf-slot','growth-slot','fincond-slot'];

function load(opts={}){
 const ids=Object.fromEntries(SLOTS.filter(s=>!(opts.noSlot||[]).includes(s)).map(s=>[s,new El('div')]));
 const el=(tag,attrs,...kids)=>{const n=new El(tag);for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,v);for(const c of kids)if(c!==null&&c!==undefined)n.append(c);return n;};
 const link=(text,url)=>/^https:\/\/fred\.stlouisfed\.org\//.test(url)?el('a',{href:url},text):text;   // index.html의 link()와 같은 꼴
 const sc={window:{},document:{getElementById:id=>ids[id]||null},el,link};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../site/macro.js'),'utf8'),sc);
 return {api:sc.window.MacroCards,ids};
}
const cite=(sid,day='November 28, 2026')=>`Federal Reserve Bank of X, Title [${sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/${sid}, ${day}.`;
const src=(sid,licence='public-domain')=>({series:sid,name:'X',url:'https://fred.stlouisfed.org/series/'+sid,licence,citation:cite(sid)});
const SERIES={dollar:['DTWEXBGS'],market:['T10YIE','T5YIFR'],model:['EXPINF10YR','EXPINF1YR'],wei:['WEI'],indpro:['INDPRO'],
 cfnai:['CFNAI','CFNAIMA3'],nfci:['NFCI','ANFCI']};
function item(key,extra={}){
 return Object.assign({key,ok:true,stale:false,error:null,failed_since:null,name:key+' 이름',date:'2026-11-20',values:{},
  retrieved:'2026-11-28',line:key+' 숫자 줄 +1.2%',extra:[key+' 덧붙임'],notices:['계산값 고지',key+' 고지'],
  sources:SERIES[key].map(s=>src(s))},extra);
}
function data(){
 const items=Object.fromEntries(Object.keys(SERIES).map(k=>[k,item(k)]));
 items.cfnai.notices=['계산값 고지','시카고 고지'];items.nfci.notices=['계산값 고지','시카고 고지'];
 return {schema:1,notice:'참고 자료다.',order:Object.keys(SERIES),items};
}

test('four cards land in their four slots, rows in order, with the fixed label',()=>{
 const {api,ids}=load();
 assert.equal(api.render(data()),true);
 assert.deepEqual(Object.keys(api.CARDS),['dollar','expinf','growth','fincond']);
 for(const [name,keys] of Object.entries(api.CARDS)){
  const card=ids[api.SLOT[name]].kids[0];
  assert.equal(card.tag,'article');
  const rows=cls(card,'oil-row').map(r=>cls(r,'oil-name')[0].textContent.split(' 이름')[0]);
  assert.deepEqual(rows,[...keys],name);
  const text=card.textContent;
  assert.ok(text.startsWith(api.TITLE[name]+'참고 — 예측 아님'),text.slice(0,40));
  assert.ok(!/undefined|NaN|null/.test(text),name);
  assert.equal(card.kids[1].textContent,api.ABOUT[name]);
  assert.ok(!text.includes('참고 자료다.'));                                  // 자료 파일의 notice는 겹쳐 싣지 않는다
 }
 assert.equal(api.LABEL,'참고 — 예측 아님');
});

test('sources link each drawn series once and every citation is plain text',()=>{
 const {api,ids}=load();
 api.render(data());
 const growth=ids['growth-slot'].kids[0];
 assert.deepEqual(walk(growth,n=>n.tag==='a').map(a=>a.textContent),['WEI','INDPRO','CFNAI','CFNAIMA3']);
 const line=cls(growth,'source-link')[0].textContent;
 assert.ok(line.startsWith('자료(FRED 경유, 달라스 연은(WEI) · 연준 이사회 G.17 · 시카고 연은 · 허락 확인 중(CFNAI)): '),line);
 const fin=ids['fincond-slot'].kids[0];
 assert.ok(cls(fin,'source-link')[0].textContent.includes('시카고 연은 · 허락 확인 중'));
 const cites=cls(fin,'cite-lines')[0].kids.map(k=>k.textContent);
 assert.deepEqual(cites,['권장 인용: '+cite('NFCI'),'권장 인용: '+cite('ANFCI')]);
 assert.equal(walk(cls(fin,'cite-lines')[0],n=>n.tag==='a').length,0);          // 인용 속 주소는 글자로
 const exp=ids['expinf-slot'].kids[0];
 assert.ok(cls(exp,'source-link')[0].textContent.includes('클리블랜드 연은(CC BY-SA 4.0)'));
 // 고지·인용은 '출처 · 이용 조건' 접는 칸 안(기본 닫힘), 짧은 출처 줄과 이름표는 그 밖 — 카드에 바로 붙어 늘 보인다
 const terms=cls(fin,'macro-terms')[0];
 assert.equal(terms.tag,'details');
 assert.equal(terms.attrs.open,undefined);                                       // 기본은 닫힘
 assert.equal(terms.kids[0].tag,'summary');
 assert.equal(terms.kids[0].textContent,'출처 · 이용 조건');
 assert.deepEqual(terms.kids.slice(1).map(k=>k.attrs.class),['notices','cite-lines']);
 assert.ok(fin.kids.includes(cls(fin,'source-link')[0]));                        // 출처 줄(허락 확인 중)은 접는 칸 밖
 assert.ok(fin.kids.indexOf(cls(fin,'source-link')[0])<fin.kids.indexOf(terms));   // 출처 줄 바로 아래가 접는 칸
 assert.ok(cls(fin,'reference-label')[0].textContent==='참고 — 예측 아님' && walk(terms,n=>(n.attrs.class||'')==='reference-label').length===0);
 assert.deepEqual(cls(terms,'notices')[0].kids.map(k=>k.textContent),['계산값 고지','시카고 고지']);   // 닫혀 있어도 고지 문구는 DOM에 있다 · 겹치는 고지는 한 번
});

test('a broken citation or a non-FRED address is not drawn as such',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.dollar.sources=[{series:'DTWEXBGS',url:'https://bad.invalid/x',licence:'public-domain',citation:'<b>x</b>'}];
 api.render(d);
 const card=ids['dollar-slot'].kids[0];
 assert.equal(walk(card,n=>n.tag==='a').length,0);
 assert.ok(cls(card,'source-link')[0].textContent.includes('DTWEXBGS'));
 assert.equal(cls(card,'cite-lines').length,0);
});

test('failed rows show only a listed reason and stale rows say so',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.wei={key:'wei',ok:false,stale:false,error:'수신 실패',failed_since:'2026-11-27',name:'WEI 이름',sources:[src('WEI')]};
 d.items.indpro={key:'indpro',ok:false,stale:false,error:'원문 https://bad.invalid',name:'산업생산 이름'};
 d.items.cfnai=item('cfnai',{ok:false,stale:true,error:'수신 실패',failed_since:'2026-11-25'});
 api.render(d);
 const card=ids['growth-slot'].kids[0], text=card.textContent;
 assert.ok(text.includes('WEI 이름 — 미수신(수신 실패)'));
 assert.ok(text.includes('산업생산 이름 — 자료 없음'));
 assert.ok(!text.includes('bad.invalid'));
 assert.deepEqual(cls(card,'oil-late').map(n=>n.textContent),['이번 갱신의 값을 싣지 못해 직전에 받은 값을 싣습니다 (2026-11-25부터)']);
 assert.deepEqual(walk(card,n=>n.tag==='a').map(a=>a.textContent),['CFNAI','CFNAIMA3']);   // 그린 칸의 출처만
});

test('rows without notices are not drawn as numbers',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.dollar.notices=[];
 assert.equal(api.render(d),true);
 assert.equal(ids['dollar-slot'].kids.length,0);                                 // 그린 칸이 없으면 카드를 두지 않는다
 assert.equal(ids['expinf-slot'].kids.length,1);
});

test('missing slots or a missing file leave the page alone',()=>{
 const {api,ids}=load({noSlot:['growth-slot','fincond-slot']});
 assert.equal(api.render(data()),true);
 assert.equal(ids['dollar-slot'].kids.length,1);
 assert.equal(load().api.render(null),false);
 assert.equal(load().api.render({items:[]}),false);
 const empty=load();
 assert.equal(empty.api.render({items:{}}),false);
 for(const schema of [2,'1',undefined])assert.equal(empty.api.render({...data(),schema}),false);   // schema 2인 자료는 그리지 않는다
 for(const s of SLOTS)assert.equal(empty.ids[s].kids.length,0);
});

test('one broken card does not stop the others',()=>{
 const {api,ids}=load();
 const d=data();
 Object.defineProperty(d.items.wei,'extra',{get(){throw new Error('x');}});
 assert.equal(api.render(d),true);
 assert.equal(ids['growth-slot'].kids.length,0);
 assert.equal(ids['fincond-slot'].kids.length,1);
 assert.equal(ids['dollar-slot'].kids.length,1);
});

test('the guide quotes the source for CFNAI-MA3 and says the site does not use it as a line',()=>{
 const {api,ids}=load();
 api.render(data());
 const g=cls(ids['growth-slot'].kids[0],'rule-guide')[0].textContent;
 assert.ok(g.includes('"an increasing likelihood of a recession has historically been associated with a CFNAI-MA3 value below –0.70"'));
 assert.ok(g.includes('출처의 설명'));
 assert.ok(g.includes('기준선으로 쓰지 않으며 숫자의 색도 바꾸지 않습니다'));
 assert.ok(g.includes('GDPNow'));
 for(const name of ['dollar','expinf','fincond'])
  assert.ok(!ids[api.SLOT[name]].kids[0].textContent.includes('0.70'),name);
 const f=cls(ids['fincond-slot'].kids[0],'rule-guide')[0].textContent;
 assert.ok(f.includes('0은 1971년 이후 평균'));
 const dl=cls(ids['dollar-slot'].kids[0],'rule-guide')[0].textContent;
 assert.ok(dl.includes('DXY') && dl.includes('싣지 않습니다'));
});

test('intro lines are one register',()=>{
 const {api}=load();
 for(const t of Object.values(api.ABOUT))
  for(const s of t.split(/(?<=\.)\s+/).filter(Boolean))assert.ok(/니다\.$/.test(s),s);
});
