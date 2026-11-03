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
 const link=(text,url)=>/^https:\/\/(fred\.stlouisfed\.org|github\.com)\//.test(url)?el('a',{href:url},text):text;   // index.html의 link()와 같은 꼴(FRED·GitHub만)
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
const VIEW={window:'지금 창 2026-10-15~11-13',
 head:['지금 창 RMP 0bn','8월 창부터 세 창째 0','2025-12-12 창부터 계획 누적 142bn','이번 창 단기채 매입 계획 9.0bn은 모두 MBS 상환분 재투자'],
 dates:'다음 날짜: 11월 계획 공지 11-13(금)께 · FOMC 12-09(수) · 12월 계획 공지 12-11(금)께',
 caption:'창마다의 계획 금액(bn) — 창은 시작 달로 부르고(10월 창 = 10-15~11-13), RMP가 같은 창끼리 한 줄로 묶었다.',
 table:{head:['창(시작 달)','RMP 계획','RMP 누적','재투자 계획'],
  rows:[{cells:['2025-12~2026-02','30 × 3창','90','10.5~12.0'],note:''},{cells:['2026-03~2026-04','20 × 2창','130','9.5~10.0'],note:''},
        {cells:['2026-05~2026-07','4 × 3창','142','8.8~11.1'],note:''},{cells:['2026-08~2026-10','0 × 3창','142','9.0~13.3'],note:'지금 창까지'}]},
 mean:'재투자는 보유 교체다. 위 나눔 칸의 연준 단기채(4주/13주 +30/+60)는 둘의 합이다.',
 bridge:{tag:'RMP 시작 뒤 지준',text:'-100bn = 연준 단기채+MBS -53 · 재무부 현금(TGA) -80 · 현금 통화 -15 · 역레포 +8 · 그 밖 +40 (수요일 수준 네 주 평균의 차, 부호는 지준 쪽)'},
 floor:{tag:'같은 기간 규칙 하한의 달러 크기',text:'2,520bn(2025Q4)에서 2,880bn(2026Q3)으로 +360bn (9.0% × 분기 명목 GDP)'},
 notes:['네 주 = RMP 시작 앞 2025-11-19~12-10과 최근 2026-10-07~10-28 · GDP는 현재 개정치.','계획 금액은 옮긴 것이다 · 차는 끝난 10창에서 -0.4~+0.2bn.']};
function data(){
 const keys=['reserves','dec','rmp_view','spread','srf','rrp','week'];
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
 Object.assign(items.rmp_view,{date:'2026-10-15',name:'지준 관리 매입(RMP) — 뉴욕 연은 월 일정 계획',line:VIEW.head.join(' · '),
  extra:['날짜 덧줄','표 줄'],notices:['계산값 고지','옮긴 값·계산한 값 고지','뉴욕 연은 기본 출처'],view:JSON.parse(JSON.stringify(VIEW))});
 items.rmp_view.sources=[src('WSHOMCB'),{series:'TSYPLAN',name:'Federal Reserve Bank of New York',url:PLAN_URL,licence:'nyfed-terms',
  citation:'Federal Reserve Bank of New York, Treasury Securities Operational Details, retrieved from '+PLAN_URL+', November 3, 2026.'},
  {series:'TSYOPS',name:'Federal Reserve Bank of New York',
  url:'https://markets.newyorkfed.org/api/tsy/all/results/summary/search.json',licence:'nyfed-terms',
  citation:'Federal Reserve Bank of New York, Treasury Securities Operations, results summary, retrieved from https://markets.newyorkfed.org/api/tsy/all/results/summary/search.json, November 3, 2026.'}];
 return {schema:1,notice:'참고 자료다.',order:keys,items};
}
const README='저장소 README의 \'RMP 칸의 셈 규칙\' 절';

test('card draws every row in order with the fixed label, head and no stray words',()=>{
 const {api,ids}=load();
 assert.equal(api.render(data()),true);
 const card=ids['fedbs-slot'].kids[0], text=card.textContent;
 const rows=cls(card,'fedbs-row').map(r=>cls(r,'oil-name')[0].textContent.split(' 이름')[0].split(' — ')[0]);
 assert.deepEqual(rows,['reserves','dec','지준 관리 매입(RMP)','spread','srf','rrp','week']);
 assert.deepEqual([...api.CARD],['reserves','dec','rmp_view','spread','srf','rrp','week']);
 assert.equal(api.LABEL,'참고 — 예측 아님');
 assert.equal(cls(card,'reference-label')[0].textContent,'참고 — 예측 아님');
 assert.ok(text.startsWith('연준 재무상태표(H.4.1 주간)참고 — 예측 아님'),text.slice(0,40));
 assert.equal(card.kids[1].textContent,api.ABOUT);                                             // 머리 안내는 ABOUT 하나
 assert.equal(cls(card,'fedbs-head')[0].textContent,'기준 주(수요일) 2026-10-28 · 받은 날 2026-10-31');   // 주 칸의 날짜·받은 날
 assert.ok(!text.includes('참고 자료다.'));                                                     // 자료 파일의 notice(한다체)는 겹쳐 싣지 않는다
 for(const t of api.ABOUT.split(/(?<=\.)\s+/).filter(Boolean))assert.ok(/니다\.$/.test(t),t);
 assert.ok(!/undefined|NaN|null/.test(text));
 assert.deepEqual(cls(card,'notices')[0].kids.map(k=>k.textContent),['계산값 고지','옮긴 값·계산한 값 고지','뉴욕 연은 기본 출처','SOFR 고지']);   // 겹치는 고지는 한 번
 // 링크는 FRED 시리즈와 읽는 법의 저장소 README(GitHub)뿐 — 뉴욕 연은에서 직접 받은 둘(공식 계획 페이지·국채 운영 결과)은 링크 없이 이름 글자로
 assert.deepEqual(walk(card,n=>n.tag==='a').map(a=>a.textContent),[README,'WRESBAL','GDP','WSHOMCB','SOFR','IORB','RPONTTLD','RRPONTSYD']);
 assert.ok(walk(card,n=>n.tag==='a').every(a=>/^https:\/\/(fred\.stlouisfed\.org|github\.com\/yun-macrolab\/macro-regime-check)/.test(a.attrs.href)));
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
 assert.deepEqual(heads,['거리는 4주 평균과 함께','분모 바뀜','재무부 현금(TGA)','RMP 칸','창의 출발일',
  'FOMC 뒤 첫 H.4.1','단기자금','정책 사실']);                                                 // 'RMP 칸' 한 항목(전엔 둘)
 const ps=g.kids.filter(k=>k.tag==='p');
 assert.ok(ps[7].textContent.includes("'연준 대차대조표 정책 — 1차 출처' 칸"),ps[7].textContent);   // 정책 사실은 가리키기만
 const rmp=ps[3];
 for(const w of ['나눔 칸의 연준 단기채는 둘의 합','네 수요일 평균의 차','-78.5bn','+17.1bn','이 사이트의 셈이고 공식 수치가 아닙니다'])
  assert.ok(rmp.textContent.includes(w),w);
 const a=walk(rmp,n=>n.tag==='a');                                                             // 셈 규칙은 README를 GitHub 링크로
 assert.equal(a.length,1);
 assert.equal(a[0].textContent,README);
 assert.equal(a[0].attrs.href,'https://github.com/yun-macrolab/macro-regime-check#rmp-칸의-셈-규칙');
 assert.ok(rmp.textContent.endsWith(README+'에 있습니다.'),rmp.textContent.slice(-40));
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
 d.items.rmp_view={key:'rmp_view',ok:false,stale:false,error:'공식 페이지에서 계획 표를 찾지 못함',name:'RMP 이름'};
 assert.equal(api.render(d),true);
 const text=ids['fedbs-slot'].textContent;
 assert.ok(text.includes('RMP 이름 — 미수신(공식 페이지에서 계획 표를 찾지 못함)'));
 assert.ok(text.includes('나눔 이름 — 미수신(수신 실패 · 묵은 캐시는 싣지 않음)'));
 assert.ok(text.includes('SOFR 이름 — 자료 없음'));
 assert.ok(text.includes('SRF 이름 — 미수신(받은 자료가 직전 자료보다 오래됨)'));
 assert.ok(text.includes('rrp 이름 — 자료 없음'));
 assert.ok(!text.includes('bad.invalid'));
 assert.ok(!text.includes('rrp 숫자 줄'));
 assert.ok(!/undefined|NaN|null/.test(text));
 assert.deepEqual(walk(ids['fedbs-slot'],n=>n.tag==='a').map(a=>a.textContent),[README,'WRESBAL','GDP']);           // 그린 칸의 출처만, 시리즈마다 한 번
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
 const rrp=cls(ids['fedbs-slot'],'fedbs-row')[5];
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
 assert.deepEqual(links,[README,'WRESBAL','GDP','WRBWFRBL','WSHOMCB','SOFR','IORB','RPONTTLD','RRPONTSYD']);
});

test('no card when the page has no slot',()=>{
 const t=load({noSlot:true});
 assert.equal(t.api.render(data()),false);
});

test('the RMP row sits after the decomposition as one row: bold head, dates, table beside its caption, bridge, floor, notes',()=>{
 const {api,ids}=load();
 api.render(data());
 const rows=cls(ids['fedbs-slot'],'fedbs-row');
 assert.equal(rows.length,7);
 const r=rows[2];
 assert.ok((r.attrs.class||'').split(' ').includes('fedbs-rmp'));
 assert.equal(cls(r,'oil-name')[0].textContent,'지준 관리 매입(RMP) — 뉴욕 연은 월 일정 계획 지금 창 2026-10-15~11-13');
 const head=cls(r,'rmp-head')[0];
 assert.equal(head.textContent,VIEW.head.join(' · '));
 assert.equal(head.kids[0].tag,'strong');                                                     // 첫 토막(지금 창 값)만 굵게
 assert.equal(head.kids[0].textContent,'지금 창 RMP 0bn');
 assert.equal(cls(r,'rmp-dates')[0].textContent,VIEW.dates);
 const grid=cls(r,'rmp-grid')[0];
 assert.deepEqual(grid.kids.map(k=>(k.attrs.class||'').split(' ').pop()),['rmp-cap','rmp-wrap','rmp-mean']);
 assert.equal(cls(grid,'rmp-cap')[0].textContent,VIEW.caption);
 assert.equal(cls(grid,'rmp-mean')[0].textContent,VIEW.mean);
 const table=walk(grid,n=>n.tag==='table')[0];
 assert.deepEqual((table.attrs.class||'').split(' '),['ai-table','rmp-table']);              // 기존 .ai-table 꼴
 assert.equal(walk(table,n=>n.tag==='caption')[0].textContent,'창마다의 계획 금액(bn)');
 assert.deepEqual(walk(table,n=>n.tag==='th'&&n.attrs.scope==='col').map(t=>t.textContent),VIEW.table.head);
 const trs=walk(walk(table,n=>n.tag==='tbody')[0],n=>n.tag==='tr');
 assert.equal(trs.length,4);
 assert.deepEqual(trs.map(tr=>tr.kids.map(k=>k.textContent)),
  [['2025-12~2026-02','30 × 3창','90','10.5~12.0'],['2026-03~2026-04','20 × 2창','130','9.5~10.0'],['2026-05~2026-07','4 × 3창','142','8.8~11.1'],
   ['2026-08~2026-10지금 창까지','0 × 3창','142','9.0~13.3']]);
 assert.equal(walk(trs[3].kids[0],n=>n.tag==='small')[0].textContent,'지금 창까지');           // 지금 창이 든 묶음 표시
 assert.equal(trs[0].kids[0].attrs.scope,'row');
 assert.equal(cls(r,'rmp-bridge')[0].textContent,VIEW.bridge.tag+' '+VIEW.bridge.text);
 assert.equal(cls(cls(r,'rmp-bridge')[0],'rmp-tag')[0].textContent,'RMP 시작 뒤 지준');
 assert.equal(cls(r,'rmp-floor')[0].textContent,VIEW.floor.tag+' '+VIEW.floor.text);
 const muted=r.kids.filter(k=>k instanceof El&&(k.attrs.class||'')==='muted').map(k=>k.textContent);
 assert.deepEqual(muted,VIEW.notes);
 assert.ok(!r.textContent.includes('날짜 덧줄'));                                               // view를 그리면 덧줄(extra)은 겹쳐 싣지 않는다
 assert.equal(walk(r,n=>n.tag==='figure').length,0);
 // 숫자·날짜 토막은 span.nw로 — 글자는 그대로, 감싸기만
 const nws=cls(r,'nw').map(n=>n.textContent);
 for(const t of ['0bn','2025-12-12','142bn','9.0bn','11-13(금)께','12-09(수)','10-15~11-13','2026-10-15~11-13',
  '-100bn','+40','2,520bn(2025Q4)','2,880bn(2026Q3)','-0.4~+0.2bn','2025-11-19~12-10','+30/+60'])
  assert.ok(nws.includes(t),t);
 assert.ok(texts(r).every(t=>typeof t==='string'));
 assert.ok(!/undefined|NaN|null/.test(r.textContent));
});

test('the RMP row falls back to its line and extra when the view is odd; old files without it draw no RMP row',()=>{
 const {api,ids}=load();
 for(const bad of [null,'x',{},Object.assign(JSON.parse(JSON.stringify(VIEW)),{head:[]}),
   Object.assign(JSON.parse(JSON.stringify(VIEW)),{table:{head:['a','b','c'],rows:[]}}),
   Object.assign(JSON.parse(JSON.stringify(VIEW)),{notes:[1]}),
   Object.assign(JSON.parse(JSON.stringify(VIEW)),{table:{head:VIEW.table.head,rows:Array(7).fill({cells:['a','b','c','d'],note:''})}}),
   Object.assign(JSON.parse(JSON.stringify(VIEW)),{bridge:{tag:'t'}})]){
  const d=data();d.items.rmp_view.view=bad;
  assert.equal(api.render(d),true);
  const r=cls(ids['fedbs-slot'],'fedbs-row')[2];
  assert.ok(!(r.attrs.class||'').includes('fedbs-rmp'));
  assert.equal(cls(r,'oil-num')[0].textContent,VIEW.head.join(' · '));                       // 숫자 줄과 덧줄만
  assert.deepEqual(cls(r,'muted').map(n=>n.textContent),['날짜 덧줄','표 줄']);
  assert.equal(walk(r,n=>n.tag==='table').length,0);
 }
 // 재설계 앞의 자료 파일(rmp_plan·rmp 두 칸, rmp_view 없음) — RMP 줄을 두지 않고, 옛 칸은 그리지 않는다
 const old=data();delete old.items.rmp_view;
 old.items.rmp_plan=item('rmp_plan',{line:'2026-10-15~2026-11-13(지금 창) 재투자 약 14.6bn · RMP 없음'});
 old.items.rmp=item('rmp',{line:'거꾸로 셈한 RMP'});
 old.order=['reserves','dec','rmp_plan','rmp','spread','srf','rrp','week'];
 assert.equal(api.render(old),true);
 const t=ids['fedbs-slot'].textContent;
 assert.equal(cls(ids['fedbs-slot'],'fedbs-row').length,6);
 assert.ok(!t.includes('rmp_plan')&&!t.includes('거꾸로 셈한')&&!t.includes('재투자 약'));
 assert.ok(!t.includes('Operational Details(월 일정 계획, 직접)'));                          // 그린 칸의 출처만
 // 받지 못한 날 — 직전 값 + 받지 못함, 칸이 깨졌으면 '자료 없음'
 // 직전 값의 '지금 창'·다음 날짜는 받은 날 기준 — 알림은 이름 줄 바로 뒤(머리 위, 긴 칸의 끝이 아니라), 날짜 토막은 끊지 않게
 const stale=data();Object.assign(stale.items.rmp_view,{ok:false,stale:true,error:'수신 실패',failed_since:'2026-11-04'});
 api.render(stale);
 const sr=cls(ids['fedbs-slot'],'fedbs-row')[2];
 assert.ok((sr.attrs.class||'').split(' ').includes('fedbs-rmp'));
 assert.ok(sr.textContent.includes('지금 창 RMP 0bn'));
 assert.equal(cls(sr,'oil-late').length,1);
 assert.equal(cls(sr,'oil-late')[0].textContent,
  "이번 갱신의 값을 싣지 못해(2026-11-04부터) 2026-10-30에 받은 값을 싣습니다 — 이 칸의 창 표시·다음 날짜도 그날 기준");
 assert.deepEqual(sr.kids.slice(0,3).map(k=>(k.attrs.class||'').split(' ').pop()),['oil-name','oil-late','rmp-head']);
 assert.equal(cls(sr,'rmp-dates')[0].textContent,VIEW.dates);
 assert.ok(cls(cls(sr,'oil-late')[0],'nw').map(n=>n.textContent).includes('2026-11-04'));
 const stale2=data();Object.assign(stale2.items.rmp_view,{ok:false,stale:true,error:'수신 실패',failed_since:'언젠가',retrieved:'어제'});
 api.render(stale2);
 assert.equal(cls(cls(ids['fedbs-slot'],'fedbs-row')[2],'oil-late')[0].textContent,
  "이번 갱신의 값을 싣지 못해 직전에 받은 값을 싣습니다 — 이 칸의 창 표시·다음 날짜도 그때 기준");
 const bad=data();bad.items.rmp_view=null;
 api.render(bad);
 assert.ok(ids['fedbs-slot'].textContent.includes('rmp_view — 자료 없음'));
 const failed=data();failed.items.rmp_view={key:'rmp_view',ok:false,stale:false,error:'수신 실패',name:'지준 관리 매입(RMP) — 뉴욕 연은 월 일정 계획'};
 api.render(failed);
 assert.ok(ids['fedbs-slot'].textContent.includes('지준 관리 매입(RMP) — 뉴욕 연은 월 일정 계획 — 미수신(수신 실패)'));
 assert.ok(!cls(ids['fedbs-slot'],'source-link')[0].textContent.includes('Operational Details'));
});

test('remote-looking text in the RMP view stays plain text',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.rmp_view.view.head[0]='<img src=x onerror=alert(1)> 0bn';
 d.items.rmp_view.view.table.rows[0].cells[1]='<b>40</b>';
 d.items.rmp_view.view.notes=['<script>alert(1)</script>'];
 api.render(d);
 const slot=ids['fedbs-slot'];
 assert.equal(walk(slot,n=>['img','script','b'].includes(n.tag)).length,0);
 assert.ok(slot.textContent.includes('<img src=x onerror=alert(1)> 0bn'));
 assert.ok(slot.textContent.includes('<b>40</b>'));
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
