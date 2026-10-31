// 기간 프리미엄 모형 대조 참고(site/tp.js) — 아주 작은 가짜 DOM 위에서 render()를 돌려 글을 본다. 숫자는 지어낸 것이다.
// 실행: node --test scripts/test_tp_render.cjs
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
 const ids={'tp-slot':new El('div')};
 if(opts.noSlot)delete ids['tp-slot'];
 const el=(tag,attrs,...kids)=>{const n=new El(tag);for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,v);for(const c of kids)if(c!==null&&c!==undefined)n.append(c);return n;};
 const link=(text,url)=>/^https:\/\/fred\.stlouisfed\.org\//.test(url)?el('a',{href:url},text):text;   // index.html의 link()와 같은 꼴
 const sc={window:{},document:{getElementById:id=>ids[id]||null},el,link};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../site/tp.js'),'utf8'),sc);
 return {api:sc.window.TpCard,ids};
}
const cite=(sid,title,from,day='October 30, 2026')=>`Board, ${title} [${sid}], retrieved from ${from}, ${day}.`;
const fred=(sid,day)=>({series:sid,name:'Board',url:'https://fred.stlouisfed.org/series/'+sid,licence:'public-domain',
 citation:cite(sid,'제목 '+sid,'FRED, Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/'+sid,day)});
const ACM={series:'ACM',name:'Federal Reserve Bank of New York',url:'https://www.newyorkfed.org/research/data_indicators/term-premia-tabs',licence:'nyfed-terms',
 citation:'Federal Reserve Bank of New York, Treasury Term Premia, 10-year term premium [TERMYld], retrieved from https://www.newyorkfed.org/x.csv, October 30, 2026.'};
function item(key,extra={}){
 return Object.assign({key,ok:true,stale:false,error:null,failed_since:null,name:key+' 이름',date:'2026-10-23',
  values:{},retrieved:'2026-10-30',line:key+' 숫자 줄 +12.3bp',extra:[key+' 덧붙임'],notices:['계산값 고지','KW 고지'],
  sources:[fred('THREEFYTP10')]},extra);
}
function data(){
 const items={weekly:item('weekly',{sources:[fred('THREEFYTP10'),fred('THREEFY10'),ACM],notices:['계산값 고지','KW 고지','뉴욕 연은 고지']}),
  models:item('models',{date:'2026-09-30',retrieved:'2026-10-28',sources:[fred('THREEFYTP10','October 28, 2026'),
   Object.assign({},ACM,{citation:ACM.citation.replace('October 30','October 28')})],notices:['계산값 고지','KW 고지','뉴욕 연은 고지','논문 고지']})};
 return {schema:1,notice:'참고 자료다. 금리를 예측하지 않는다.',order:['weekly','models'],items};
}

test('card draws both rows in order with the fixed label and no stray words',()=>{
 const {api,ids}=load();
 assert.equal(api.render(data()),true);
 const card=ids['tp-slot'].kids[0], text=card.textContent;
 assert.deepEqual(cls(card,'tp-row').map(r=>cls(r,'oil-name')[0].textContent.split(' 이름')[0]),[...api.CARD]);
 assert.deepEqual([...api.CARD],['weekly','models']);
 assert.equal(api.LABEL,'참고 — 금리 예측 아님');                                                 // 이름표 글을 고정한다
 assert.ok(text.startsWith('기간 프리미엄 모형 대조참고 — 금리 예측 아님'),text.slice(0,40));
 assert.ok(text.includes('weekly 숫자 줄 +12.3bp')&&text.includes('models 덧붙임'));
 assert.ok(!/undefined|NaN|null|\[object/.test(text));
});

test('the intro is one 합니다체 paragraph and does not repeat the data file notice',()=>{
 const {api,ids}=load();
 api.render(data());
 const card=ids['tp-slot'].kids[0];
 const intro=card.kids.find(k=>k.tag==='p'&&(k.attrs.class||'')==='muted').textContent;
 assert.equal(intro,api.ABOUT);                                                   // 머리글은 ABOUT 하나
 assert.ok(intro.includes('금리를 예측하지 않습니다'));                               // 자료 파일 notice의 뜻을 합니다체로
 for(const s of intro.split(/(?<=\.)\s+/))assert.ok(s.endsWith('니다.'),s);         // 문장마다 합니다체
 assert.ok(!card.textContent.includes('참고 자료다.')&&!card.textContent.includes('예측하지 않는다'));
});

test('recommended citations are shown once per series, compactly, from the latest drawn row',()=>{
 const {api,ids}=load();
 api.render(data());
 const cites=cls(ids['tp-slot'],'tp-cite');
 assert.equal(cites.length,1);
 assert.equal(cites[0].kids.length,1);                                            // 한 문단
 const t=cites[0].textContent;
 assert.ok(t.startsWith('권장 인용: '),t);
 assert.equal(t,'권장 인용: '+[fred('THREEFYTP10').citation,fred('THREEFY10').citation,ACM.citation].join(' '));
 assert.ok(!t.includes('October 28'));                                            // 같은 시리즈는 가장 늦게 받은 칸의 것
 const d=data();d.items.models.retrieved='2026-10-31';
 d.items.models.sources=[fred('THREEFYTP10','October 31, 2026'),ACM];
 api.render(d);
 const t2=cls(ids['tp-slot'],'tp-cite')[0].textContent;
 assert.ok(t2.includes('[THREEFYTP10], retrieved from FRED, Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/THREEFYTP10, October 31, 2026.'));
 assert.equal(t2.split('[THREEFYTP10]').length,2);
 const card=ids['tp-slot'].kids[0];                                               // 출처 줄 다음, 인용은 링크가 아니라 글자
 assert.ok(card.kids.indexOf(cls(card,'source-link')[0])<card.kids.indexOf(cls(card,'tp-cite')[0]));
 assert.deepEqual(walk(card,n=>n.tag==='a').map(a=>a.textContent),['THREEFYTP10','THREEFY10']);
});

test('citations of rows not drawn or of the wrong shape are left out',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.weekly.sources=[fred('THREEFYTP10'),Object.assign(fred('THREEFY10'),{citation:'<b>원문</b>, retrieved from x, October 30, 2026.'}),
  Object.assign({},ACM,{citation:'Federal Reserve Bank of New York, ACM'})];                       // 꼴이 다르면 빠진다
 d.items.models={key:'models',ok:false,stale:false,error:'수신 실패',name:'월간 이름',sources:[ACM]};   // 그리지 않는 칸
 api.render(d);
 const t=cls(ids['tp-slot'],'tp-cite')[0].textContent;
 assert.equal(t,'권장 인용: '+fred('THREEFYTP10').citation);
 for(const s of d.items.weekly.sources)s.citation='x'.repeat(5);
 api.render(d);
 assert.equal(cls(ids['tp-slot'],'tp-cite').length,0);                            // 실을 인용이 없으면 문단도 없다
 assert.ok(!ids['tp-slot'].textContent.includes('원문'));
});

test('the weekly row always carries the fixed score note, the models row does not',()=>{
 const {api,ids}=load();
 const d=data();d.items.weekly.extra=[];                                          // 자료 쪽 설명이 빠져도
 api.render(d);
 const rows=cls(ids['tp-slot'],'tp-row');
 assert.ok(rows[0].textContent.includes(api.SCORE_NOTE));
 assert.ok(!rows[1].textContent.includes(api.SCORE_NOTE));
 assert.ok(api.SCORE_NOTE.includes('+는 금리 하락 쪽')&&api.SCORE_NOTE.includes('예측하지 않습니다'));
 const t=rows[0].textContent;
 assert.ok(t.indexOf('weekly 숫자 줄')<t.indexOf(api.SCORE_NOTE));                  // 숫자 줄 바로 아래
});

test('notices are shown once and sources link FRED only, ACM as text',()=>{
 const {ids,api}=load();
 api.render(data());
 const card=ids['tp-slot'].kids[0];
 assert.deepEqual(cls(card,'notices')[0].kids.map(k=>k.textContent),['계산값 고지','KW 고지','뉴욕 연은 고지','논문 고지']);
 assert.deepEqual(walk(card,n=>n.tag==='a').map(a=>a.textContent),['THREEFYTP10','THREEFY10']);
 const src=cls(card,'source-link')[0].textContent;
 assert.equal(src,'자료(Kim-Wright: 연준 이사회, FRED 경유 · ACM: 뉴욕 연은): THREEFYTP10 · THREEFY10 · ACM');
});

test('failed rows show a fixed reason only, never remote text',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.models={key:'models',ok:false,stale:false,error:'수신 실패 · 묵은 캐시는 싣지 않음',name:'월간 이름'};
 d.items.weekly={key:'weekly',ok:false,stale:false,error:'<b>원문 https://bad.invalid</b>',name:'주간 이름'};
 assert.equal(api.render(d),false);                                               // 그릴 칸이 없으면 카드를 두지 않는다
 d.items.weekly=item('weekly',{notices:['계산값 고지']});
 assert.equal(api.render(d),true);
 const text=ids['tp-slot'].textContent;
 assert.ok(text.includes('월간 이름 — 미수신(수신 실패 · 묵은 캐시는 싣지 않음)'));
 d.items.models={key:'models',error:'<b>원문 https://bad.invalid</b>',name:'월간 이름'};
 api.render(d);
 assert.ok(ids['tp-slot'].textContent.includes('월간 이름 — 자료 없음'));
 assert.ok(!ids['tp-slot'].textContent.includes('bad.invalid'));
});

test('rows without notices or with a broken date or key are not drawn',()=>{
 for(const bad of [{notices:[]},{date:'어제'},{date:'2026-13-45'},{key:'weekly'},{line:''}]){
  const {api,ids}=load();
  const d=data();Object.assign(d.items.models,bad);
  api.render(d);
  const t=ids['tp-slot'].textContent;
  assert.ok(!t.includes('models 숫자 줄'),JSON.stringify(bad));
  assert.ok(t.includes('— 자료 없음'),JSON.stringify(bad));
 }
});

test('stale rows say since when and keep their numbers',()=>{
 const {api,ids}=load();
 const d=data();Object.assign(d.items.models,{ok:false,stale:true,error:'수신 실패',failed_since:'2026-10-28'});
 Object.assign(d.items.weekly,{ok:false,stale:true,error:'수신 실패',failed_since:'어제'});
 api.render(d);
 const late=cls(ids['tp-slot'],'oil-late').map(x=>x.textContent);
 assert.deepEqual(late,['이번 갱신의 값을 싣지 못해 직전에 받은 값을 싣습니다','이번 갱신의 값을 싣지 못해 직전에 받은 값을 싣습니다 (2026-10-28부터)']);
 assert.ok(ids['tp-slot'].textContent.includes('models 숫자 줄'));
});

test('guide explains the definitions',()=>{
 const {api,ids}=load();
 api.render(data());
 const g=cls(ids['tp-slot'],'rule-guide')[0].textContent;
 for(const part of ['기간 프리미엄 · ','두 모형','4주 변화와 σ','운영자 주간 점수','−부호(z) × min(2, ⌊|z|⌋)','14일',
  '10년 중 몫','해석 갈림','0.7','12개월 일치도','0.6 미만','신뢰 낮음'])assert.ok(g.includes(part),part);
});

test('a missing file or slot draws nothing',()=>{
 const {api,ids}=load();
 for(const d of [null,undefined,{},{items:null},{items:[]},'x'])assert.equal(api.render(d),false);
 assert.equal(ids['tp-slot'].kids.length,0);
 const t=load({noSlot:true});assert.equal(t.api.render(data()),false);
});
