// 연준 재무상태표 참고(site/fedbs.js) — 아주 작은 가짜 DOM 위에서 render()를 돌려 글을 본다. 숫자는 지어낸 것이다.
// 실행: node --test scripts/test_fedbs_render.cjs
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
const texts=n=>n instanceof El?n.kids.flatMap(texts):[n.text];   // 글자 마디 — 모두 글(text)로 들어갔는지 본다

function load(opts={}){
 const ids={'fedbs-slot':new El('div')};
 if(opts.noSlot)delete ids['fedbs-slot'];
 const el=(tag,attrs,...kids)=>{const n=new El(tag);for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,v);for(const c of kids)if(c!==null&&c!==undefined)n.append(c);return n;};
 const link=(text,url)=>/^https:\/\/fred\.stlouisfed\.org\//.test(url)?el('a',{href:url},text):text;   // index.html의 link()와 같은 꼴
 const calls=[];
 const win={};
 if(opts.charts!==false)win.MacroCharts={lineChart:(spec,o)=>{calls.push({spec,o});if(opts.chartThrows)throw new Error('x');return el('figure',{class:'ch'},String(spec.title));}};
 const sc={window:win,document:{getElementById:id=>ids[id]||null},el,link};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../site/fedbs.js'),'utf8'),sc);
 return {api:sc.window.FedBsCard,ids,calls};
}
const PLAN_URL='https://www.newyorkfed.org/markets/domestic-market-operations/monetary-policy-implementation/treasury-securities/treasury-securities-operational-details';
const src=(sid,lic='public-domain')=>({series:sid,name:'X',url:'https://fred.stlouisfed.org/series/'+sid,licence:lic,
 citation:`X, Title [${sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/${sid}, November 3, 2026.`});
function item(key,extra={}){
 return Object.assign({key,ok:true,stale:false,error:null,failed_since:null,name:key+' 이름',date:'2026-10-28',
  values:{},retrieved:'2026-10-30',line:key+' 숫자 줄 -12bn',extra:[key+' 덧붙임'],notices:['계산값 고지'],sources:[src('GDP')]},extra);
}
function data(){
 const keys=['reserves','dec','rmp_plan','rmp','spread','srf','rrp','week'];
 const items=Object.fromEntries(keys.map(k=>[k,item(k)]));
 items.reserves.sources=['WRESBAL','GDP'].map(s=>src(s));
 items.reserves.chart={key:'fedbs_reserves',title:'지준 차트',unit:'bn',zero:false,threshold:null,note:'n',source_note:'s',notices:[],
  lines:[{key:'res',label:'주 평균 지준',role:'main',points:[['2026-10-21',2900.0],['2026-10-28',2800.0]]},
         {key:'low',label:'규칙 하한',role:'ref',points:[['2026-10-21',2880.0],['2026-10-28',2880.0]]}]};
 items.spread.sources=[src('SOFR','citation-required'),src('IORB')];
 items.spread.notices=['계산값 고지','SOFR 고지'];
 items.srf.sources=[src('RPONTTLD','citation-required')];
 items.rrp.sources=[src('RRPONTSYD','citation-required')];
 items.week.date='2026-10-28';items.week.retrieved='2026-10-31';items.week.sources=[src('WRESBAL')];
 items.rmp.date='2026-10-29';items.rmp.notices=['계산값 고지','뉴욕 연은 기본 출처'];
 items.rmp.extra=['2026-07 창 덧붙임','셈 줄','한계 줄'];
 items.rmp_plan.date='2026-10-15';items.rmp_plan.notices=['옮긴 값 고지','뉴욕 연은 기본 출처'];
 items.rmp_plan.line='2026-10-15~2026-11-13(지금 창) 재투자 약 9.0bn · RMP 없음';items.rmp_plan.extra=['계획 덧붙임','꼴 줄'];
 items.rmp_plan.sources=[{series:'TSYPLAN',name:'Federal Reserve Bank of New York',url:PLAN_URL,licence:'nyfed-terms',
  citation:'Federal Reserve Bank of New York, Treasury Securities Operational Details, retrieved from '+PLAN_URL+', November 3, 2026.'}];
 items.rmp.sources=[src('WSHOMCB'),{series:'TSYOPS',name:'Federal Reserve Bank of New York',
  url:'https://markets.newyorkfed.org/api/tsy/all/results/summary/search.json',licence:'nyfed-terms',
  citation:'Federal Reserve Bank of New York, Treasury Securities Operations, results summary, retrieved from https://markets.newyorkfed.org/api/tsy/all/results/summary/search.json, November 3, 2026.'}];
 return {schema:1,notice:'참고 자료다.',order:keys,items};
}

test('card draws every row in order with the fixed label, head and no stray words',()=>{
 const {api,ids}=load();
 assert.equal(api.render(data()),true);
 const card=ids['fedbs-slot'].kids[0], text=card.textContent;
 const rows=cls(card,'fedbs-row').map(r=>cls(r,'oil-name')[0].textContent.split(' 이름')[0]);
 assert.deepEqual(rows,[...api.CARD]);
 assert.deepEqual([...api.CARD],['reserves','dec','rmp_plan','rmp','spread','srf','rrp','week']);
 assert.equal(api.LABEL,'참고 — 예측 아님');
 assert.equal(cls(card,'reference-label')[0].textContent,'참고 — 예측 아님');
 assert.ok(text.startsWith('연준 재무상태표(H.4.1 주간)참고 — 예측 아님'),text.slice(0,40));
 assert.equal(card.kids[1].textContent,api.ABOUT);                                             // 머리 안내는 ABOUT 하나
 assert.equal(cls(card,'fedbs-head')[0].textContent,'기준 주(수요일) 2026-10-28 · 받은 날 2026-10-31');   // 주 칸의 날짜·받은 날
 assert.ok(!text.includes('참고 자료다.'));                                                     // 자료 파일의 notice(한다체)는 겹쳐 싣지 않는다
 for(const t of api.ABOUT.split(/(?<=\.)\s+/).filter(Boolean))assert.ok(/니다\.$/.test(t),t);
 assert.ok(!/undefined|NaN|null/.test(text));
 assert.deepEqual(cls(card,'notices')[0].kids.map(k=>k.textContent),['계산값 고지','옮긴 값 고지','뉴욕 연은 기본 출처','SOFR 고지']);   // 겹치는 고지는 한 번
 // 링크는 FRED 시리즈만 — 뉴욕 연은에서 직접 받은 둘(공식 계획 페이지·국채 운영 결과)은 링크 없이 이름 글자로
 assert.deepEqual(walk(card,n=>n.tag==='a').map(a=>a.textContent),['WRESBAL','GDP','WSHOMCB','SOFR','IORB','RPONTTLD','RRPONTSYD']);
 const srcLine=cls(card,'source-link')[0].textContent;
 assert.ok(srcLine.endsWith(' · 뉴욕 연은 Treasury Securities Operational Details(월 일정 계획, 직접) · 뉴욕 연은 국채 운영 결과(Markets API, 직접)'),srcLine);
 assert.ok(!srcLine.includes('TSYOPS')&&!srcLine.includes('TSYPLAN')&&!srcLine.includes('https://'));
 assert.ok(cls(card,'oil-card').length===1&&cls(card,'fedbs-card').length===1);
});

test('citation-required sources carry their FRED citation as text, once per series',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.srf.sources=[src('RPONTTLD','citation-required'),{series:'XYZ',licence:'citation-required',citation:'<b>bad</b>'}];
 api.render(d);
 const cites=cls(ids['fedbs-slot'],'cite-lines')[0].kids.map(k=>k.textContent);
 assert.deepEqual(cites.filter(c=>/\[\w+\]/.test(c)).map(c=>c.match(/\[(\w+)\]/)[1]),['SOFR','RPONTTLD','RRPONTSYD']);   // 공공 자료(IORB·GDP·WSHOMCB)는 인용 줄 없음
 assert.deepEqual(cites.filter(c=>!/\[\w+\]/.test(c)),['권장 인용: Federal Reserve Bank of New York, Treasury Securities Operational Details, '+
  'retrieved from '+PLAN_URL+', November 3, 2026.',
  '권장 인용: Federal Reserve Bank of New York, Treasury Securities Operations, '+
  'results summary, retrieved from https://markets.newyorkfed.org/api/tsy/all/results/summary/search.json, November 3, 2026.']);   // 뉴욕 연은 이용약관 자료도 글자로
 assert.equal(cites.length,5);
 assert.equal(walk(cls(ids['fedbs-slot'],'cite-lines')[0],n=>n.tag==='a').length,0);                 // 인용 속 주소는 글자로
});

test('the reserves row carries the chart with the bn format; no charts tool means no figure',()=>{
 let t=load();
 t.api.render(data());
 const r=cls(t.ids['fedbs-slot'],'fedbs-row')[0];
 assert.equal(walk(r,n=>n.tag==='figure').length,1);
 assert.equal(t.calls.length,1);
 assert.equal(t.calls[0].spec.key,'fedbs_reserves');
 assert.equal(t.calls[0].o.notices,false);                                                      // 고지는 카드가 한 번 싣는다
 assert.equal(t.calls[0].o.format(2880),'2,880bn');
 assert.equal(t.calls[0].o.format(2893.8),'2,894bn');
 assert.equal(t.calls[0].o.format(-0.4),'0bn');
 assert.equal(t.calls[0].o.format(-1234.6),'-1,235bn');
 for(const k of ['dec','spread','week'])assert.equal(walk(cls(t.ids['fedbs-slot'],'fedbs-row')[t.api.CARD.indexOf(k)],n=>n.tag==='figure').length,0);
 t=load({charts:false});
 assert.equal(t.api.render(data()),true);
 assert.equal(walk(t.ids['fedbs-slot'],n=>n.tag==='figure').length,0);
 t=load({chartThrows:true});
 assert.equal(t.api.render(data()),true);                                                       // 그래프가 깨져도 카드는 그대로
 assert.equal(walk(t.ids['fedbs-slot'],n=>n.tag==='figure').length,0);
 assert.ok(t.ids['fedbs-slot'].textContent.includes('reserves 숫자 줄'));
 t=load();const d=data();delete d.items.reserves.chart;
 assert.equal(t.api.render(d),true);
 assert.equal(t.calls.length,0);
});

test('the guide carries the definitions, policy facts and the measurement records',()=>{
 const {ids,api}=load();
 api.render(data());
 const g=cls(ids['fedbs-slot'],'rule-guide')[0];
 assert.ok(g.textContent.startsWith('읽는 법 — 정의·측정 기록'));
 const heads=g.kids.filter(k=>k.tag==='p').map(p=>p.kids[0].textContent);
 assert.deepEqual(heads,['거리는 4주 평균과 함께','분모 바뀜','재무부 현금(TGA)','연준 단기채와 MBS는 짝으로','창의 출발일',
  'FOMC 뒤 첫 H.4.1','단기자금','정책 사실','RMP 계획과 대조']);
 const ps=g.kids.filter(k=>k.tag==='p');
 assert.ok(ps[7].textContent.includes("'연준 대차대조표 정책 — 1차 출처' 칸"),ps[7].textContent);   // 정책 사실은 가리키기만
 assert.ok(ps[8].textContent.includes('대조 줄은 공식 수치가 아닙니다'),ps[8].textContent);
 assert.ok(ps[8].textContent.includes('계획일 뿐 실제 매입은 운영 결과'),ps[8].textContent);
 assert.ok(ps[3].textContent.includes("'공식 계획' 줄"),ps[3].textContent);
 assert.ok(!g.textContent.includes('conclude the reduction'));                                 // 같은 사실을 두 번 싣지 않는다
 const fomc=g.kids.filter(k=>k.tag==='p')[5].textContent;
 assert.ok(fomc.includes('시행되기 전 값')&&fomc.includes('다음 주 숫자'),fomc);
});

test('a missing file draws nothing',()=>{
 const {api,ids}=load();
 for(const d of [null,undefined,{},{items:null},{items:[]},'x'])assert.equal(api.render(d),false);
 assert.equal(ids['fedbs-slot'].kids.length,0);
});

test('each failed row shows a fixed reason only, never remote text',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.dec={key:'dec',ok:false,stale:false,error:'수신 실패 · 묵은 캐시는 싣지 않음',name:'나눔 이름'};
 d.items.spread={key:'spread',ok:false,stale:false,error:'<b>원문 오류 https://bad.invalid</b>',name:'SOFR 이름'};
 d.items.srf={key:'srf',ok:false,stale:false,error:'받은 자료가 직전 자료보다 오래됨',name:'SRF 이름'};
 d.items.rrp=item('rrp',{notices:[]});                                                         // 고지가 없으면 숫자를 싣지 않는다
 d.items.rmp={key:'rmp',ok:false,stale:false,error:'계산할 자료가 모자람',name:'RMP 이름'};
 d.items.rmp_plan={key:'rmp_plan',ok:false,stale:false,error:'공식 페이지에서 계획 표를 찾지 못함',name:'계획 이름'};
 assert.equal(api.render(d),true);
 const text=ids['fedbs-slot'].textContent;
 assert.ok(text.includes('RMP 이름 — 미수신(계산할 자료가 모자람)'));
 assert.ok(text.includes('계획 이름 — 미수신(공식 페이지에서 계획 표를 찾지 못함)'));
 assert.ok(text.includes('나눔 이름 — 미수신(수신 실패 · 묵은 캐시는 싣지 않음)'));
 assert.ok(text.includes('SOFR 이름 — 자료 없음'));
 assert.ok(text.includes('SRF 이름 — 미수신(받은 자료가 직전 자료보다 오래됨)'));
 assert.ok(text.includes('rrp 이름 — 자료 없음'));
 assert.ok(!text.includes('bad.invalid'));
 assert.ok(!text.includes('rrp 숫자 줄'));
 assert.ok(!/undefined|NaN|null/.test(text));
 assert.deepEqual(walk(ids['fedbs-slot'],n=>n.tag==='a').map(a=>a.textContent),['WRESBAL','GDP']);                  // 그린 칸의 출처만, 시리즈마다 한 번
 const cites=cls(ids['fedbs-slot'],'cite-lines');
 assert.equal(cites.length,0);                                                                  // 인용 필요 칸을 하나도 그리지 않았다
 const all=data();for(const k of api.CARD)all.items[k]={key:k,ok:false,error:'수신 실패',name:k};
 assert.equal(api.render(all),false);                                                          // 그린 칸이 없으면 카드도 없다(앞 카드 그대로)
});

test('without the week row the head falls back to the reserves row; with neither there is no head',()=>{
 const {api,ids}=load();
 const d=data();d.items.week={key:'week',ok:false,error:'수신 실패',name:'주'};
 api.render(d);
 assert.equal(cls(ids['fedbs-slot'],'fedbs-head')[0].textContent,'기준 주(수요일) 2026-10-28 · 받은 날 2026-10-30');
 d.items.reserves={key:'reserves',ok:false,error:'수신 실패',name:'지준'};
 api.render(d);
 assert.equal(cls(ids['fedbs-slot'],'fedbs-head').length,0);
 d.items.dec.retrieved='어제';d.items.week=item('week',{retrieved:'어제'});
 api.render(d);
 assert.equal(cls(ids['fedbs-slot'],'fedbs-head')[0].textContent,'기준 주(수요일) 2026-10-28');   // 받은 날이 날짜 꼴이 아니면 뺀다
});

test('rows with a wrong key, bad date or empty line are not drawn as numbers',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.reserves=item('dec');                                                                  // 자리와 key가 다르다
 d.items.dec=item('dec',{date:'어제'});
 d.items.spread=item('spread',{line:''});
 d.items.srf=item('srf',{date:'2026-13-45'});
 d.items.rrp=item('rrp',{extra:[1,null,'남는 줄']});
 assert.equal(api.render(d),true);
 const text=ids['fedbs-slot'].textContent;
 assert.ok(text.includes('dec 이름 — 자료 없음'));
 assert.ok(text.includes('srf 이름 — 자료 없음'));
 assert.ok(!text.includes('2026-13-45'));
 const rrp=cls(ids['fedbs-slot'],'fedbs-row')[6];
 assert.deepEqual(cls(rrp,'muted').map(n=>n.textContent),['남는 줄']);                            // 글이 아닌 줄은 뺀다
 assert.ok(!/null|undefined/.test(text));
});

test('stale rows say since when and keep their numbers',()=>{
 const {api,ids}=load();
 const d=data();Object.assign(d.items.dec,{ok:false,stale:true,error:'수신 실패',failed_since:'2026-10-31'});
 Object.assign(d.items.spread,{ok:false,stale:true,error:'수신 실패',failed_since:'언젠가'});
 Object.assign(d.items.srf,{stale:'true'});                                                     // true 그 값일 때만
 api.render(d);
 const late=cls(ids['fedbs-slot'],'oil-late').map(n=>n.textContent);
 assert.deepEqual(late,['이번 갱신의 값을 싣지 못해 직전에 받은 값을 싣습니다 (2026-10-31부터)','이번 갱신의 값을 싣지 못해 직전에 받은 값을 싣습니다']);
 assert.ok(ids['fedbs-slot'].textContent.includes('dec 숫자 줄'));
});

test('remote-looking text stays plain text (no markup is parsed)',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.dec.line='<img src=x onerror=alert(1)> -3bn';
 d.items.dec.extra=['<script>alert(1)</script>'];
 d.items.dec.name='<b>이름</b>';
 api.render(d);
 const slot=ids['fedbs-slot'];
 assert.equal(walk(slot,n=>['img','script','b'].includes(n.tag)).length,0);                   // 요소로 바뀐 것은 없다
 assert.ok(texts(slot).includes('<img src=x onerror=alert(1)> -3bn'));                          // 글자 그대로
 assert.ok(texts(slot).includes('<script>alert(1)</script>'));
});

test('source links skip odd series names and unusable rows',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.dec.sources=[src('WRBWFRBL'),{series:'<x>',url:'https://fred.stlouisfed.org/series/x'},'GDP',null];
 d.items.week={key:'week',ok:false,error:'수신 실패',sources:[src('WCICL')]};
 api.render(d);
 const links=walk(ids['fedbs-slot'],n=>n.tag==='a').map(a=>a.textContent);
 assert.deepEqual(links,['WRESBAL','GDP','WRBWFRBL','WSHOMCB','SOFR','IORB','RPONTTLD','RRPONTSYD']);
});

test('no card when the page has no slot',()=>{
 const t=load({noSlot:true});
 assert.equal(t.api.render(data()),false);
});

test('the RMP rows sit after the decomposition (plan, then cross-check) and show their lines; old files without them draw no row',()=>{
 const {api,ids}=load();
 const d=data();
 api.render(d);
 const rows=cls(ids['fedbs-slot'],'fedbs-row');
 assert.equal(rows.length,8);
 const p=rows[2];
 assert.equal(cls(p,'oil-name')[0].textContent,'rmp_plan 이름 2026-10-15');                    // 공식 계획이 위
 assert.equal(cls(p,'oil-num')[0].textContent,'2026-10-15~2026-11-13(지금 창) 재투자 약 9.0bn · RMP 없음');
 assert.deepEqual(cls(p,'muted').map(n=>n.textContent),['계획 덧붙임','꼴 줄']);
 const r=rows[3];
 assert.equal(cls(r,'oil-name')[0].textContent,'rmp 이름 2026-10-29');
 assert.equal(cls(r,'oil-num')[0].textContent,'rmp 숫자 줄 -12bn');
 assert.deepEqual(cls(r,'muted').map(n=>n.textContent),['2026-07 창 덧붙임','셈 줄','한계 줄']);
 assert.equal(walk(r,n=>n.tag==='figure').length,0);                                         // 그래프 없음
 const older=data();delete older.items.rmp_plan;                                              // 계획 칸이 없던 때(2026-11-03 첫 공개)
 api.render(older);
 assert.equal(cls(ids['fedbs-slot'],'fedbs-row').length,7);
 assert.ok(!ids['fedbs-slot'].textContent.includes('rmp_plan')&&!ids['fedbs-slot'].textContent.includes('Operational Details'));
 assert.ok(ids['fedbs-slot'].textContent.includes('rmp 숫자 줄'));
 const old=data();delete old.items.rmp;delete old.items.rmp_plan;                               // 그 칸이 없던 때의 자료 파일
 api.render(old);
 const t=ids['fedbs-slot'].textContent;
 assert.equal(cls(ids['fedbs-slot'],'fedbs-row').length,6);
 assert.ok(!t.includes('rmp — 자료 없음')&&!t.includes('TSYOPS'));
 assert.ok(!t.includes('뉴욕 연은 국채 운영 결과(Markets API, 직접)'));                       // 그린 칸의 출처만
 const failed=data();failed.items.rmp={key:'rmp',ok:false,stale:false,error:'수신 실패',name:'운영 결과로 거꾸로 셈한 대조'};
 api.render(failed);
 assert.ok(ids['fedbs-slot'].textContent.includes('운영 결과로 거꾸로 셈한 대조 — 미수신(수신 실패)'));
 assert.ok(cls(ids['fedbs-slot'],'source-link')[0].textContent.endsWith('Operational Details(월 일정 계획, 직접)'));   // 그린 칸(계획)의 출처만
 const stale=data();Object.assign(stale.items.rmp_plan,{ok:false,stale:true,error:'수신 실패',failed_since:'2026-11-04'});
 api.render(stale);                                                                            // 받지 못한 날 — 직전 계획 + 받지 못함
 const pr=cls(ids['fedbs-slot'],'fedbs-row')[2];
 assert.ok(pr.textContent.includes('재투자 약 9.0bn'));
 assert.equal(cls(pr,'oil-late')[0].textContent,'이번 갱신의 값을 싣지 못해 직전에 받은 값을 싣습니다 (2026-11-04부터)');
 const bad=data();bad.items.rmp=null;                                                          // 칸이 있는데 깨졌으면 '자료 없음'
 api.render(bad);
 assert.ok(ids['fedbs-slot'].textContent.includes('rmp — 자료 없음'));
});

test('the policy box is visible outside the folded guide, dated and with addresses as plain text',()=>{
 const {api,ids}=load();
 api.render(data());
 const card=ids['fedbs-slot'].kids[0];
 const box=cls(card,'fedbs-policy');
 assert.equal(box.length,1);
 const kids=card.kids.filter(k=>k instanceof El);
 const at=kids.indexOf(box[0]);
 assert.ok(at>kids.indexOf(cls(card,'fedbs-row').slice(-1)[0])&&at<kids.findIndex(k=>k.tag==='details'));   // 줄 뒤, 접힌 읽는 법 앞
 assert.equal(walk(card,n=>n.tag==='details').filter(dd=>cls(dd,'fedbs-policy').length).length,0);
 const ps=box[0].kids.filter(k=>k.tag==='p');
 assert.equal(ps[0].textContent,`${api.POLICY_HEAD} 기준일 ${api.POLICY_ASOF}`);
 assert.equal(api.POLICY_HEAD,'연준 대차대조표 정책 — 1차 출처');
 assert.ok(ps[1].textContent.includes('자동으로 갱신하지 않습니다'));
 assert.deepEqual(ps.slice(2).map(p=>p.kids[0].textContent),['보유 축소(QT) 종료 — 2025-12-01','지준 관리 매입(RMP) 시작 — 2025-12',
  'FOMC 성명 2026-10-28','대차대조표 태스크포스']);
 const text=box[0].textContent;
 for(const w of ['monetary20251029a.htm','monetary20251210a.htm','monetary20261028a.htm','operating_policy_251210a','FOMCpresconf20261028.pdf',
  'ninth business day','3-3/4~4%','2027년 1분기 초쯤'])assert.ok(text.includes(w),w);
 assert.equal(walk(box[0],n=>n.tag==='a').length,0);                                          // 1차 출처 주소는 글자로(링크 아님)
 assert.ok(texts(box[0]).every(t=>typeof t==='string'));
 const all=data();for(const k of api.CARD)all.items[k]={key:k,ok:false,error:'수신 실패',name:k};
 assert.equal(api.render(all),false);                                                         // 그린 칸이 없으면 정책 칸만으로 카드를 두지 않는다
});
