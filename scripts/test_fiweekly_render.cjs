// 평가사 주간 보고서(site/fiweekly.js) — 아주 작은 가짜 DOM 위에서 render()를 돌려 글을 본다. 글 · 숫자 · 호수는 지어낸 것이다.
// 실행: node --test scripts/test_fiweekly_render.cjs
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

class El {
 constructor(tag){this.tag=tag;this.kids=[];this.attrs={};this.hidden=false;}
 append(...xs){for(const x of xs)this.kids.push(typeof x==='string'?{text:x}:x);}
 replaceChildren(...xs){this.kids=[];for(const x of xs)this.kids.push(typeof x==='string'?{text:x}:x);}
 setAttribute(k,v){this.attrs[k]=String(v);}
 get textContent(){return this.kids.map(k=>k instanceof El?k.textContent:k.text).join('');}
}
const walk=(n,f,out=[])=>{if(n instanceof El){if(f(n))out.push(n);n.kids.forEach(k=>walk(k,f,out));}return out;};
const cls=(n,c)=>walk(n,x=>(x.attrs.class||'').split(' ').includes(c));

function load(opts={}){
 const ids={'fiweekly-body':new El('div')};
 if(opts.noSlot)delete ids['fiweekly-body'];
 const el=(tag,attrs,...kids)=>{const n=new El(tag);for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,v);for(const c of kids)if(c!==null&&c!==undefined)n.append(c);return n;};
 const sc={window:{},document:{getElementById:id=>ids[id]||null},el};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../site/fiweekly.js'),'utf8'),sc);
 return {api:sc.window.FiWeekly,slot:ids['fiweekly-body']};
}
const ROWS={irs_1y:[3.1,10],irs_3y:[3.3025,15.25],crs_1y:[2.9,5],crs_3y:[3,8],ss_1y:[-2,1],ss_3y:[1.25,2.25],
 basis_1y:[-20,-5],basis_3y:[-30.25,-7.25],aa_minus_3y:[65,-0.7],a_minus_3y:[175,1.2]};
const KIS={src:'kis',issue:'1212',date:'2026-11-13',posted:'2026-11-16',url:'https://www.bond.co.kr/post/dawn/37184',
 summary:[{topic:'국채',text:'지어낸 국채 요약이다. 둘째 문장이다.'},{topic:'크레딧',text:'지어낸 크레딧 요약이다.'},{topic:'스왑',text:'지어낸 스왑 요약이다.'}],
 summary_note:null,summary_dropped:0,model:'claude-fx-1',
 numbers:{date:'2026-11-13',prev:'2026-11-06',credit_date:'2026-11-13',credit_prev:'2026-11-06',rows:ROWS},numbers_note:null};
const KAP={src:'kap',issue:'26-46',date:'2026-11-16',posted:'2026-11-16',url:'https://www.koreaap.com/kor/data01_02.html',
 summary:[{topic:'국채',text:'지어낸 KAP 국채 요약이다.'},{topic:'단기자금',text:'지어낸 KAP 단기자금 요약이다.'}],
 summary_note:null,summary_dropped:1,model:'claude-fx-1'};
const doc=(...reports)=>({schema:'fi-weekly/1',asof:'2026-11-17',reports:reports.length?reports:[clone(KIS),clone(KAP)]});
const clone=x=>JSON.parse(JSON.stringify(x));
const NOW=Date.parse('2026-11-17T18:00:00+09:00');

test('both reports with label, AI tag, links and the fixed notes',()=>{
 const {api,slot}=load();
 assert.equal(api.render(doc(),NOW),true);
 const text=slot.textContent;
 assert.ok(text.startsWith(api.LABEL));
 assert.equal(api.LABEL,'평가사 산출값 · AI 요약 — 참고');
 const reps=cls(slot,'fi-report');
 assert.deepEqual(reps.map(r=>r.kids[0].textContent),['KIS자산평가 · KIS WEEKLY 제1212호','한국자산평가 · Fixed Income Weekly 제26-46호']);
 assert.deepEqual(cls(slot,'fi-ai-tag').map(n=>n.textContent),[api.AI_TAG,api.AI_TAG]);
 assert.deepEqual(cls(reps[0],'fi-topic').map(n=>[n.kids[0].textContent,n.kids[1].text]),
  [['국채','지어낸 국채 요약이다. 둘째 문장이다.'],['크레딧','지어낸 크레딧 요약이다.'],['스왑','지어낸 스왑 요약이다.']]);
 assert.deepEqual(cls(reps[1],'fi-topic').map(n=>n.kids[0].textContent),['국채','단기자금']);
 assert.ok(!reps[0].textContent.includes('검사에 걸린 주제'));
 assert.ok(reps[1].textContent.includes('검사에 걸린 주제 1개는 싣지 않았습니다.'));
 assert.deepEqual(walk(slot,n=>n.tag==='a').map(n=>n.attrs.href),[KIS.url,KAP.url]);   // 링크는 둘뿐
 assert.ok(reps[0].kids[1].textContent.startsWith('2026-11-13 기준 · 2026-11-16 게시 · 보고서 PDF'));
 assert.ok(reps[1].kids[1].textContent.startsWith('2026-11-16 게시 · 보고서 게시판'));
 assert.ok(text.includes('한국자산평가는 숫자 표를 싣지 않습니다(요약 문장 속 숫자만).'));
 assert.ok(text.includes('요약 속 숫자는 두 보고서 모두 보고서 글에 적힌 것만, 주제마다 셋까지 씁니다.'));
 assert.ok(!text.includes('보고서의 숫자는 싣지 않습니다'));
 assert.ok(text.includes('요청이 있으면 바로 내립니다'));
 assert.ok(text.includes('자료: KIS자산평가 KIS WEEKLY(bond.co.kr) · 한국자산평가 Fixed Income Weekly(koreaap.com)'));
 assert.equal(walk(slot,n=>n.tag==='img').length,0);
 assert.ok(!/undefined|NaN|null|\[object/.test(text));
});

test('the KIS table shows the ten cells as written with signed weekly changes',()=>{
 const {api,slot}=load();
 api.render(doc(),NOW);
 const tables=walk(slot,n=>n.tag==='table');
 assert.equal(tables.length,2);
 const rows=walk(tables[0],n=>n.tag==='tr').slice(1).map(r=>r.kids.map(c=>c.textContent));
 assert.deepEqual(rows,[['IRS','3.10%전주 +10.0bp','3.3025%전주 +15.25bp'],['CRS','2.90%전주 +5.0bp','3.00%전주 +8.0bp'],
  ['스왑 스프레드 (IRS − 국고)','-2.0bp전주 +1.0bp','1.25bp전주 +2.25bp'],['스왑 베이시스 (CRS − IRS)','-20.0bp전주 -5.0bp','-30.25bp전주 -7.25bp']]);
 const credit=walk(tables[1],n=>n.tag==='tr').slice(1).map(r=>r.kids.map(c=>c.textContent));
 assert.deepEqual(credit,[['AA-','65.0bp전주 -0.7bp'],['A-','175.0bp전주 +1.2bp']]);
 assert.ok(slot.textContent.includes('평가사 산출값 — KIS자산평가 KIS WEEKLY 제1212호, 2026-11-13 기준. 전주 대비는 2026-11-06(크레딧 2026-11-06)과의 차'));
 assert.deepEqual(Array.from(api.ROWS,r=>r[0]),Object.keys(ROWS));            // 다른 realm의 배열은 Array.from으로
});

test('missing summary or numbers say why, and stale issues are marked',()=>{
 const {api,slot}=load();
 const k=clone(KIS); k.summary=null; k.summary_note='copy'; k.summary_dropped=0; k.model=null; k.numbers=null; k.numbers_note='table'; k.posted='2026-10-30'; k.date='2026-10-30';
 api.render(doc(k,clone(KAP)),NOW);
 const text=slot.textContent;
 assert.ok(text.includes('요약 없음 — 요약이 보고서 문장과 너무 비슷함. 원문을 확인하세요.'));
 assert.ok(text.includes('보고서의 표를 읽지 못해 이번 호의 숫자는 싣지 않습니다'));
 assert.ok(text.includes('최근 호가 아닐 수 있습니다(게시 18일 전)'));
 assert.equal(cls(slot,'fi-ai-tag').length,1);
 for(const [code,label] of Object.entries(api.NOTES)){
  const x=clone(KAP); x.summary=null; x.summary_note=code; x.summary_dropped=0; x.model=null;
  api.render(doc(x),NOW);
  assert.ok(slot.textContent.includes('요약 없음 — '+label),code);
 }
});

test('a report that breaks the contract is left out, a bad file draws nothing',()=>{
 const {api,slot}=load();
 const t=(topic,text)=>({topic,text:text||'지어낸 글이다.'});
 const bads=[{url:'https://evil.example/post/dawn/1'},{url:'https://www.bond.co.kr/post/dawn/1?x'},{issue:'12a'},{date:'2026-13-01'},
  {posted:'2026-11-01'},{summary:'한 덩어리 글이다.'},{summary:3},{src:'xyz'},{summary:[t('국채')]},{summary:[t('크레딧'),t('국채')]},
  {summary:[t('국채'),t('국채')]},{summary:[t('국채'),t('주가')]},{summary:[t('국채'),t('크레딧','가'.repeat(231))]},
  {summary:[t('국채'),{topic:'크레딧'}]},{summary:[t('국채'),null]},{summary_dropped:-1},{summary_dropped:1.5},{summary_dropped:undefined},
  {summary:null,summary_note:'copy',summary_dropped:1}];
 for(const b of bads){
  assert.equal(api.render(doc(Object.assign(clone(KIS),b),clone(KAP)),NOW),true,JSON.stringify(b));
  assert.deepEqual(cls(slot,'fi-report').map(r=>r.kids[0].textContent.split(' · ')[0]),['한국자산평가'],JSON.stringify(b));
 }
 const n=clone(KIS); n.numbers.rows.irs_1y=[NaN,1];
 assert.equal(api.render(doc(n),NOW),false);
 assert.equal(slot.kids.length,0);
 const kapUrl=clone(KAP); kapUrl.url='https://www.koreaap.com/cm/files/x.pdf';
 assert.equal(api.render(doc(kapUrl),NOW),false);
 const kapSwap=clone(KAP); kapSwap.summary=[t('국채'),t('스왑')];                         // KAP에는 스왑 주제가 없다
 assert.equal(api.render(doc(kapSwap),NOW),false);
 assert.deepEqual(JSON.parse(JSON.stringify(api.TOPICS)),{kis:['국채','크레딧','단기자금','해외 금리','스왑'],kap:['국채','크레딧','단기자금','해외 금리']});
 for(const d of [null,[],{schema:'fi-weekly/2',reports:[KIS]},{schema:'fi-weekly/1',reports:{}},{schema:'fi-weekly/1',reports:[]}])
  assert.equal(api.render(d,NOW),false);
 assert.equal(api.render(doc(clone(KIS),clone(KIS)),NOW),true);                          // 같은 출처는 처음 것 하나만
 assert.equal(cls(slot,'fi-report').length,1);
 assert.equal(api.render(doc(clone(KAP),clone(KIS)),NOW),true);                          // 차례는 KIS → KAP
 assert.deepEqual(cls(slot,'fi-report').map(r=>r.kids[0].textContent.split(' · ')[0]),['KIS자산평가','한국자산평가']);
 assert.equal(load({noSlot:true}).api.render(doc(),NOW),false);
});

test('text from the file is never parsed as markup',()=>{
 const {api,slot}=load();
 const k=clone(KIS); k.summary[0].text='<img src=x onerror=alert(1)> 글자 그대로다.';
 api.render(doc(k),NOW);
 assert.ok(slot.textContent.includes('<img src=x onerror=alert(1)> 글자 그대로다.'));
 assert.equal(walk(slot,n=>n.tag==='img').length,0);
 const js=fs.readFileSync(path.join(__dirname,'../site/fiweekly.js'),'utf8');
 for(const tok of ['innerHTML','outerHTML','insertAdjacentHTML','createElement','fetch(','eval('])assert.ok(!js.includes(tok),tok);
});
