// 신용 긴축 참고(site/credit.js) — 아주 작은 가짜 DOM 위에서 render()를 돌려 글을 본다. 숫자는 지어낸 것이다.
// 실행: node --test scripts/test_credit_render.cjs
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
 const ids={'credit-slot':new El('div')};
 if(opts.noSlot)delete ids['credit-slot'];
 const el=(tag,attrs,...kids)=>{const n=new El(tag);for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,v);for(const c of kids)if(c!==null&&c!==undefined)n.append(c);return n;};
 const link=(text,url)=>/^https:\/\/fred\.stlouisfed\.org\//.test(url)?el('a',{href:url},text):text;   // index.html의 link()와 같은 꼴
 const sc={window:{},document:{getElementById:id=>ids[id]||null},el,link};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../site/credit.js'),'utf8'),sc);
 return {api:sc.window.CreditCard,ids};
}
const fred=(sid,licence='public-domain',on='October 30, 2026')=>({series:sid,name:'X',url:'https://fred.stlouisfed.org/series/'+sid,licence,
 citation:`Org X, Title ${sid} [${sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/${sid}, ${on}.`});
const edgar={series:'EDGAR',name:'U.S. Securities and Exchange Commission',url:'https://www.sec.gov/edgar/sec-api-documentation',licence:'public'};
const ext=(sid,url,licence)=>({series:sid,name:'Org '+sid,url,licence,restricted:false,
 citation:`Paper ${sid}, retrieved from ${url}, October 30, 2026.`});
const EBP_URL='https://www.federalreserve.gov/econres/notes/feds-notes/ebp_csv.csv';
const CMDI_URL='https://www.newyorkfed.org/medialibrary/research/interactives/cmdi/downloads/Market%20CMDI.xlsx';
const rowsOf=card=>cls(card,'credit-row').filter(r=>!(r.attrs.class||'').split(' ').includes('credit-group'));
function item(key,extra={}){
 return Object.assign({key,ok:true,stale:false,error:null,failed_since:null,name:key+' 이름',date:'2026-10-16',
  values:{},retrieved:'2026-10-30',line:key+' 숫자 줄 +0.040',extra:[key+' 덧붙임'],notices:['계산값 고지'],sources:[fred('DRTSCILM')]},extra);
}
function data(){
 const keys=['stage','ebp','cmdi','cell','gap','drawdown','sec'];
 const items=Object.fromEntries(keys.map(k=>[k,item(k)]));
 items.stage.notices=['계산값 고지','인용 고지'];items.stage.sources=[fred('DRTSCILM'),fred('NFCICREDIT','citation-required')];
 items.ebp.notices=['EBP 고지','EBP 인용'];items.ebp.sources=[ext('EBP',EBP_URL,'public-domain')];
 items.cmdi.notices=['CMDI 고지','관계없음 고지'];items.cmdi.sources=[ext('CMDI',CMDI_URL,'nyfed-terms')];
 items.drawdown.notices=['제한 고지','저작권 고지'];items.drawdown.sources=[fred('NASDAQ100','restricted')];
 items.sec=item('sec',{line:'credit 쪽 SEC 줄',detail:['credit 쪽 회사 줄'],sources:[edgar],notices:['SEC 고지']});
 return {schema:1,notice:'참고 자료다.',order:keys,items};
}
function secFile(extra={}){
 return {schema:1,order:['funding'],items:{funding:item('funding',Object.assign({name:'sec 이름',line:'sec.json 줄 2사 TTM 98%',
  detail:['TSTA 회사 줄','TSTA 태그 줄'],sources:[edgar],notices:['SEC 고지']},extra))}};
}

test('card draws every row in order with the label and the definition, and no stray words',()=>{
 const {api,ids}=load();
 assert.equal(api.render(data(),secFile()),true);
 const card=ids['credit-slot'].kids[0], text=card.textContent;
 const rows=rowsOf(card).map(r=>cls(r,'credit-name')[0].textContent.split(' 이름')[0]);
 assert.deepEqual(rows,[...api.CARD]);
 assert.deepEqual([...api.CARD],['stage','ebp','cmdi','cell','gap','drawdown','sec']);
 assert.equal(api.LABEL,'참고 — 금리 예측 아님');
 assert.ok(text.includes('참고 — 금리 예측 아님'));
 assert.ok(text.includes(api.STAGE_DEF));
 assert.ok(!/undefined|NaN|null/.test(text));
 assert.deepEqual(cls(card,'notices')[0].kids.map(k=>k.textContent),
  ['계산값 고지','인용 고지','EBP 고지','EBP 인용','CMDI 고지','관계없음 고지','제한 고지','저작권 고지','SEC 고지']);
 assert.equal(walk(card,n=>n.tag==='a').length,3);                                    // FRED 링크, 시리즈마다 한 번
 const src=cls(card,'source-link')[0].textContent;
 assert.ok(src.endsWith('Source: SEC EDGAR XBRL API (data.sec.gov); site calculations'));
 assert.ok(!/EBP|CMDI|newyorkfed|federalreserve/.test(src));                         // FRED 밖은 이 줄에 넣지 않는다(고지로 나간다)
});

test('the public credit stress group sits after the definition with its one-sentence reason',()=>{
 const {api,ids}=load();
 api.render(data(),secFile());
 const kids=ids['credit-slot'].kids[0].kids;
 const i=kids.findIndex(k=>k instanceof El&&(k.attrs.class||'').includes('credit-def'));
 const g=kids[i+1];
 assert.ok((g.attrs.class||'').split(' ').includes('credit-group'));
 assert.equal(g.kids[0].textContent,'신용 스트레스(공개 자료)');
 assert.equal(g.kids[1].textContent,api.STRESS_NOTE);
 assert.deepEqual(rowsOf(g).map(r=>cls(r,'credit-name')[0].textContent.split(' 이름')[0]),['ebp','cmdi']);
 assert.deepEqual([...api.STRESS],['ebp','cmdi']);
 const sentences=api.STRESS_NOTE.split(/(?<=\.)\s+/).filter(Boolean);
 assert.equal(sentences.length,1);                                                     // 한 문장, 합니다체
 assert.ok(/니다\.$/.test(sentences[0]));
 assert.ok(/ICE/.test(api.STRESS_NOTE)&&/공개할 수 없어/.test(api.STRESS_NOTE)&&/EBP/.test(api.STRESS_NOTE)&&/CMDI/.test(api.STRESS_NOTE));
});

test('the stress group is left out for an older file and shows fixed reasons when a source fails',()=>{
 let t=load();const d=data();delete d.items.ebp;delete d.items.cmdi;
 assert.equal(t.api.render(d,secFile()),true);
 assert.equal(cls(t.ids['credit-slot'],'credit-group').length,0);
 assert.ok(!t.ids['credit-slot'].textContent.includes('신용 스트레스'));
 t=load();const e=data();
 e.items.cmdi={key:'cmdi',ok:false,stale:false,error:'받은 파일의 꼴을 알아보지 못함',name:'CMDI 이름'};
 delete e.items.ebp;
 t.api.render(e,secFile());
 const g=cls(t.ids['credit-slot'],'credit-group')[0];
 assert.ok(g.textContent.includes('CMDI 이름 — 미수신 — 받은 파일의 꼴을 알아보지 못함'));
 assert.ok(g.textContent.includes('ebp — 자료 없음'));
});

test('the definition sits right after the stage row and stays when the stage row fails',()=>{
 for(const st of [item('stage'),{key:'stage',ok:false,stale:false,error:'수신 실패',name:'단계 이름'},undefined]){
  const {api,ids}=load();
  const d=data();d.items.stage=st;
  assert.equal(api.render(d),true);
  const kids=ids['credit-slot'].kids[0].kids;
  const i=kids.findIndex(k=>k instanceof El&&(k.attrs.class||'').includes('credit-def'));
  assert.ok(i>0);
  assert.ok((kids[i-1].attrs.class||'').includes('credit-row'));
  assert.equal(kids[i].textContent,api.STAGE_DEF);
 }
});

test('a missing file draws nothing',()=>{
 const {api,ids}=load();
 for(const d of [null,undefined,{},{items:null},'x'])assert.equal(api.render(d,secFile()),false);
 assert.equal(ids['credit-slot'].kids.length,0);
});

test('failed rows show a fixed reason only, never remote text',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.cell={key:'cell',ok:false,stale:false,error:'수신 실패',name:'칸 이름'};
 d.items.gap={key:'gap',ok:false,stale:false,error:'<b>원문 오류 https://bad.invalid</b>',name:'조건 이름'};
 d.items.drawdown=item('drawdown',{notices:[]});                                        // 고지가 없으면 숫자를 싣지 않는다
 d.items.sec={key:'sec',ok:false,stale:false,error:'연락처 미설정(SEC_USER_AGENT)',name:'SEC 이름'};
 api.render(d);
 const text=ids['credit-slot'].textContent;
 assert.ok(text.includes('칸 이름 — 미수신 — 수신 실패'));
 assert.ok(text.includes('조건 이름 — 자료 없음'));
 assert.ok(text.includes('SEC 이름 — 미수신 — 연락처 미설정(SEC_USER_AGENT)'));
 assert.ok(!text.includes('bad.invalid'));
 assert.ok(!text.includes('drawdown 숫자 줄'));
});

test('stale rows say since when and keep their numbers',()=>{
 const {api,ids}=load();
 const d=data();Object.assign(d.items.stage,{ok:false,stale:true,error:'수신 실패',failed_since:'2026-10-28'});
 api.render(d);
 assert.ok(cls(ids['credit-slot'],'credit-late')[0].textContent.includes('(2026-10-28부터)'));
 assert.ok(ids['credit-slot'].textContent.includes('stage 숫자 줄'));
});

test('the SEC row prefers sec.json and falls back to the copy in credit.json',()=>{
 let t=load();t.api.render(data(),secFile());
 let sec=rowsOf(t.ids['credit-slot']).at(-1);
 assert.ok(sec.textContent.includes('sec.json 줄 2사 TTM 98%'));
 assert.ok(!sec.textContent.includes('credit 쪽 SEC 줄'));
 const det=walk(sec,n=>n.tag==='details')[0];                                            // 회사별 줄은 접어 둔다
 assert.deepEqual(det.kids.slice(1).map(k=>k.textContent),['TSTA 회사 줄','TSTA 태그 줄']);
 for(const s of [undefined,null,{},secFile({notices:[]}),secFile({date:'어제'}),{items:{funding:item('sec')}}]){
  t=load();t.api.render(data(),s);
  sec=rowsOf(t.ids['credit-slot']).at(-1);
  assert.ok(sec.textContent.includes('credit 쪽 SEC 줄'),JSON.stringify(s));
 }
});

test('no card when the page has no slot or nothing is usable',()=>{
 const t=load({noSlot:true});assert.equal(t.api.render(data()),false);
 const u=load();const d=data();for(const k of u.api.CARD)d.items[k].notices=[];
 assert.equal(u.api.render(d),false);assert.equal(u.ids['credit-slot'].kids.length,0);
 const v=load();const e=data();for(const k of v.api.CARD)e.items[k].notices=[];
 assert.equal(v.api.render(e,secFile()),true);                                          // sec.json만 있어도 카드는 그린다
 assert.equal(rowsOf(v.ids['credit-slot']).length,7);
 assert.equal(cls(v.ids['credit-slot'],'credit-group').length,1);
});

test('citation-required and restricted FRED sources show their citation as text, once, and nothing else is cited',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.gap.sources=[fred('NFCICREDIT','citation-required','October 29, 2026')];d.items.gap.retrieved='2026-10-29';   // 더 이른 칸의 같은 시리즈
 d.items.cell.sources=[ext('XLIC','https://example.invalid/x.csv','restricted')];      // FRED 밖은 이용 조건이 같아도 인용 줄 없음
 api.render(d,secFile());
 const card=ids['credit-slot'].kids[0];
 const lines=cls(card,'cite-lines');
 assert.equal(lines.length,1);
 assert.deepEqual(lines[0].kids.map(k=>k.textContent),
  ['권장 인용: Org X, Title NFCICREDIT [NFCICREDIT], retrieved from FRED, Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/NFCICREDIT, October 30, 2026.',
   '권장 인용: Org X, Title NASDAQ100 [NASDAQ100], retrieved from FRED, Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/NASDAQ100, October 30, 2026.']);
 assert.equal(lines[0].kids[0].attrs.class,'muted');
 assert.ok(!card.textContent.includes('Title DRTSCILM'));                               // 공공 자료는 인용 줄 없음
 assert.ok(!lines[0].textContent.includes('Paper '));                                   // EBP·CMDI 인용은 고지로만
 assert.ok(!lines[0].textContent.includes('XLIC'));
});

test('a citation in the wrong form, on an unusable row, or missing draws no citation line',()=>{
 const bad=[s=>{s.citation='<b>x</b>, retrieved from y, October 30, 2026.';},s=>{s.citation='Org, retrieved from FRED 2026';},
  s=>{delete s.citation;},s=>{s.series='nfci credit';}];
 for(const f of bad){
  const {api,ids}=load();const d=data();f(d.items.stage.sources[1]);f(d.items.drawdown.sources[0]);
  api.render(d);
  assert.equal(cls(ids['credit-slot'],'cite-lines').length,0);
  assert.ok(!ids['credit-slot'].textContent.includes('<b>'));
 }
 const {api,ids}=load();const d=data();d.items.stage.notices=[];d.items.drawdown.notices=[];   // 그리지 않은 칸의 인용은 싣지 않는다
 api.render(d);
 assert.equal(cls(ids['credit-slot'],'cite-lines').length,0);
});

test('the intro is one register and does not repeat the data notice',()=>{
 const {api,ids}=load();
 const d=data();d.notice='이 사이트의 규칙 점검에 쓰지 않는 참고 자료다. 금리를 예측하지 않는다.';
 api.render(d,secFile());
 const intro=ids['credit-slot'].kids[0].kids[1];
 assert.equal(intro.textContent,api.ABOUT);
 assert.ok(!ids['credit-slot'].textContent.includes('참고 자료다.'));
 const sentences=api.ABOUT.split(/(?<=\.)\s+/).filter(Boolean);
 assert.ok(sentences.length>=3);
 for(const t of sentences)assert.ok(/(니다|습니다)\.$/.test(t),t);                   // 합니다체 하나
});
