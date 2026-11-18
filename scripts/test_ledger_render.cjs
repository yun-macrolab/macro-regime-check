// 기록 장부(site/ledger.js) — 아주 작은 가짜 DOM 위에서 render()를 돌려 글을 본다. 자료는 scripts/ledger_build.py가 쓰는 꼴
// (data/changes.json · data/ledger.json)을 손으로 지은 것이고 숫자는 지어낸 것이다. 맨 끝 둘은 index.html의 applyView·go 가운데
// 기록 장부에 닿는 부분을 잘라 돌린다(상자가 그 화면에서만 열리는지, 명령 낱말이 똑같을 때만 넘어가는지).
// 실행: node --test scripts/test_ledger_render.cjs
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const SRC=fs.readFileSync(path.join(__dirname,'../site/ledger.js'),'utf8');
const PAGE=fs.readFileSync(path.join(__dirname,'../site/index.html'),'utf8');
const STRAY=/undefined|NaN|null|\[object/;
const VERDICT=['적중','맞았다','틀렸다','매수','매도','유망'];

class El {
 constructor(tag){this.tag=tag;this.kids=[];this.attrs={};this.hidden=false;}
 append(...xs){for(const x of xs){assert.ok(typeof x==='string'||x instanceof El,'el()에 글자·요소 밖의 값: '+String(x));this.kids.push(typeof x==='string'?{text:x}:x);}}
 replaceChildren(...xs){this.kids=[];this.append(...xs.filter(x=>x!==null&&x!==undefined));}
 setAttribute(k,v){this.attrs[k]=String(v);}
 get textContent(){return this.kids.map(k=>k instanceof El?k.textContent:k.text).join('');}
}
const walk=(n,f,out=[])=>{if(n instanceof El){if(f(n))out.push(n);n.kids.forEach(k=>walk(k,f,out));}return out;};
const cls=(n,c)=>walk(n,x=>(x.attrs.class||'').split(' ').includes(c));
const tags=(n,t)=>walk(n,x=>x.tag===t);
const plain=o=>JSON.parse(JSON.stringify(o));   // vm 안에서 만든 객체는 원형이 달라 deepEqual 전에 옮긴다

function load(opts={}){
 const ids={'changes-wrap':new El('section'),'ledger-wrap':new El('section')};
 for(const id of opts.drop||[])delete ids[id];
 const el=(tag,attrs,...kids)=>{const n=new El(tag);for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,v);for(const c of kids)if(c!==null&&c!==undefined)n.append(c);return n;};
 const link=(text,url)=>/^https:\/\/(fred\.stlouisfed\.org|github\.com)\//.test(url)?el('a',{href:url},text):text;   // index.html의 link()와 같은 꼴
 const sc={window:{},document:{getElementById:id=>ids[id]||null},el,link};
 vm.runInNewContext(SRC,sc);
 return {api:sc.window.LedgerView,ids};
}

// ── 지은 자료 ─────────────────────────────────────────────────────────────────────────
const health=(o={})=>Object.assign({lost:[],recovered:[],stale:[],fresh:[]},o);
function changes(){
 return {schema:1,generated_at:'2026-11-18T07:31:00+09:00',
  notice:'날짜별 공개 기록(data/history)끼리 견준 것이다. 예측이 아니고 투자 판단이나 권유가 아니다.',asof:'2026-11-17',
  headline:['핵심 신호 2/11 · 1주 전 1/11','1주 사이 바뀐 규칙 2개: 단기 조달금리 SOFR(미충족→충족) 근원 물가의 최근 속도(새 규칙)',
   '국면 후보 A′ · 1주 전 A · 받지 못한 시리즈 1개'],
  windows:[
   {key:'prev',label:'직전 기록',from:'2026-11-15',rules:[],met:{from:2,to:2,total_from:13,total_to:13},
    core:{from:'2/11',to:'2/11'},neutral:{from:'0/2',to:'0/2'},candidate:{from:'A′',to:'A′'},transition:{from:1,to:0},
    health:health({lost:[{series:'DGS10',label:'미 10년'}]})},
   {key:'w1',label:'1주 전',from:'2026-11-10',
    rules:[{key:'sofr',title:'단기 조달금리 SOFR',from:'not_met',to:'met'},{key:'core_momentum',title:'근원 물가의 최근 속도',from:null,to:'not_met'}],
    met:{from:1,to:2,total_from:12,total_to:13},core:{from:'1/11',to:'2/11'},neutral:{from:null,to:'0/2'},
    candidate:{from:'A',to:'A′'},transition:{from:null,to:0},
    health:health({recovered:[{series:'T10Y2Y',label:'10년−2년'}],stale:[{series:'NFCICREDIT',label:'NFCI 신용'}],fresh:[{series:'WRESBAL',label:'지준'}]})},
   {key:'w4',label:'4주 전',from:null,rules:[],met:{from:null,to:2,total_from:null,total_to:13},core:{from:null,to:'2/11'},
    neutral:{from:null,to:'0/2'},candidate:{from:null,to:'A′'},transition:{from:null,to:0},health:health()}],
  recent:[{date:'2026-11-12',key:'sofr',title:'단기 조달금리 SOFR',from:'not_met',to:'met'},
   {date:'2026-10-30',key:'reserves_multiplier',title:'지준과 통화승수',from:'not_met',to:'met'}]};
}
const OUT=[['dgs10','미 10년','DGS10'],['t10y2y','10년−2년','T10Y2Y'],['tp','기간 프리미엄(Kim-Wright)','THREEFYTP10']];
const CITES=Object.fromEntries(OUT.map(([,,sid])=>[sid,`지어낸 출처, 지어낸 제목 [${sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/${sid}, November 17, 2026.`]));
const capOf=(root,table)=>cls(root,'ledger-cap').find(p=>p.attrs.id===table.attrs['aria-labelledby']);   // 표의 이름이 된 설명 줄
const done=(start,end,change,dem)=>({state:'done',start,end,change_bp:change,demeaned_bp:dem});
const pending=start=>({state:'pending',start,end:null,change_bp:null,demeaned_bp:null});
const missing=start=>({state:'missing',start,end:null,change_bp:null,demeaned_bp:null});
const each=f=>Object.fromEntries(OUT.map(([k])=>[k,f(k)]));
const hold=n=>({to_met:{'4':each(()=>({n,mean_demeaned_bp:null,up_share:null})),'13':each(()=>({n,mean_demeaned_bp:null,up_share:null}))},
 to_not_met:{'4':each(()=>({n:0,mean_demeaned_bp:null,up_share:null})),'13':each(()=>({n:0,mean_demeaned_bp:null,up_share:null}))}});
function ledger(){
 const sum=hold(0);
 sum.to_met['4'].dgs10={n:12,mean_demeaned_bp:-3.5,up_share:0.42};
 sum.to_met['4'].tp={n:9,mean_demeaned_bp:null,up_share:null};
 return {schema:1,generated_at:'2026-11-18T07:31:00+09:00',
  notice:'규칙이 바뀐 날 뒤의 금리 변화를 정해 둔 방법(평가 약속)으로 적은 측정 기록이다. 예측이 아니고 투자 판단이나 권유가 아니다.',
  protocol:{version:1,fixed:'2026-11-18',horizons_weeks:[4,13],outcomes:OUT.map(([key,label,series])=>({key,label,series})),
   n_min:10,tolerance_days:3,start_days:7,text:['전환은 판정 가능한 상태가 직전에 알던 상태와 달라진 날이다.','측정 기록이다 — 예측이 아니고, 어느 규칙도 금리를 올리거나 내린다고 가정하지 않는다.']},
  history:{from:'2026-09-27',to:'2026-11-17',snapshots:40,skipped:1},
  charts:{date:'2026-11-17',window:{from:'2021-11-19',to:'2026-11-13'},last:{dgs10:'2026-11-13',t10y2y:'2026-11-16',tp:'2026-11-06'},
   baseline:{'4':{dgs10:0.4,t10y2y:-0.2,tp:0.1},'13':{dgs10:1.3,t10y2y:null,tp:0.3}},
   baseline_detail:{'4':{dgs10:{n:256,from:'2021-11-19',to:'2026-11-06'},t10y2y:{n:257,from:'2021-11-19',to:'2026-11-13'},tp:{n:255,from:'2021-11-19',to:'2026-10-30'}},
    '13':{dgs10:{n:247,from:'2021-11-19',to:'2026-11-06'},t10y2y:null,tp:{n:246,from:'2021-11-26',to:'2026-10-30'}}}},
  sources:OUT.map(([,,sid])=>({series:sid,url:'https://fred.stlouisfed.org/series/'+sid,citation:CITES[sid],citation_required:sid==='T10Y2Y'})),
  notices:['4주·13주 변화는 macro-regime-check가 계산한 값이다.','Computed by macro-regime-check.'],
  rules:[
   {key:'sofr',title:'단기 조달금리 SOFR',first:'2026-09-27',start:'not_met',now:'met',since:'2026-11-12',unknown_days:0,
    events:[
     {date:'2026-11-12',from:'not_met',to:'met',before_protocol:true,core:'2/11',candidate:'A′',
      outcomes:{'4':each(()=>pending('2026-11-06')),'13':each(()=>pending('2026-11-06'))}},
     {date:'2026-09-29',from:'not_met',to:'met',before_protocol:true,core:null,candidate:null,
      outcomes:{'4':{dgs10:done('2026-09-26','2026-10-24',12.3,11.9),t10y2y:done('2026-09-26','2026-10-24',-4.04,-3.84),tp:missing('2026-09-26')},
       '13':each(()=>pending('2026-09-26'))}},
     {date:'2026-10-02',from:'met',to:'not_met',before_protocol:true,core:null,candidate:null,
      outcomes:{'4':each(()=>missing('2026-10-01')),'13':each(()=>pending('2026-10-01'))}}],
    summary:hold(0)},
   {key:'term_premium',title:'10년 기간 프리미엄',first:'2026-09-27',start:'met',now:'not_met',since:'2027-01-08',unknown_days:3,
    events:[{date:'2027-01-08',from:'met',to:'not_met',before_protocol:false,core:'1/11',candidate:'B',
     outcomes:{'4':{dgs10:done('2027-01-08','2027-02-05',-7.26,-7.66),t10y2y:pending('2027-01-08'),tp:done('2027-01-08','2027-02-05',0.04,-0.06)},
      '13':each(()=>pending('2027-01-08'))}}],
    summary:sum},
   {key:'curve_inversion',title:'10년−2년 금리차',first:'2026-09-27',start:'not_met',now:'not_met',since:'2026-09-27',unknown_days:2,
    events:[],summary:hold(0)}]};
}

// ── 첫 화면 ──────────────────────────────────────────────────────────────────────────
test('home box: headline lines, closed details, the fixed note and the ledger link',()=>{
 const {api,ids}=load();
 assert.deepEqual(plain(api.render(changes(),ledger())),{changes:true,ledger:true});
 const box=ids['changes-wrap'],text=box.textContent;
 assert.equal(tags(box,'h2')[0].textContent,'이번 주 달라진 것');
 assert.equal(tags(box,'h2')[0].attrs.id,'changes-title');                              // index.html의 aria-labelledby
 assert.deepEqual(cls(box,'chg-head')[0].kids.map(k=>k.textContent),changes().headline);
 assert.ok(text.includes('2026-11-17 공개 기록 기준'));
 const det=tags(box,'details');
 assert.equal(det.length,1);
 assert.ok(!('open' in det[0].attrs));                                                  // 닫힌 채
 assert.equal(tags(det[0],'summary')[0].textContent,'자세히 — 직전 기록 · 1주 전 · 4주 전 · 최근 30일 규칙 전환');
 const note=cls(box,'chg-note')[0];
 assert.equal(note.textContent,api.NOTE+' 기록 장부 보기 →');
 assert.equal(api.NOTE,'날짜별 공개 기록끼리 견준 것 — 예측이 아닙니다.');
 assert.deepEqual(tags(note,'a').map(a=>a.attrs.href),['#ledger']);
 assert.ok(!STRAY.test(text),text);
 assert.ok(!text.includes(changes().notice));                                          // 자료 파일의 notice(한다체)는 되풀이하지 않는다
});

test('home box: the three windows list what changed, then what stayed and what was not recorded then',()=>{
 const {api,ids}=load();
 api.render(changes(),null);
 const wins=cls(ids['changes-wrap'],'chg-window').map(w=>({head:tags(w,'h3')[0].textContent,items:tags(w,'li').map(l=>l.textContent),
  same:cls(w,'chg-same').map(l=>l.textContent),text:w.textContent}));
 assert.deepEqual(wins.map(w=>w.head),['직전 기록 2026-11-15 대비','1주 전 2026-11-10 대비','4주 전','최근 30일 규칙 전환']);
 assert.deepEqual(wins[0].items,['바뀐 규칙 없음','전환 경계 자동 트리거 1/2 → 0/2','받지 못하게 된 시리즈: DGS10(미 10년)',   // 자동 트리거는 레짐 점검 참고와 같은 n/2
  '그대로: 충족 규칙 2/13 · 핵심 신호 2/11 · 중립 규칙 0/2 · 국면 후보 A′']);
 assert.deepEqual(wins[0].same,['그대로: 충족 규칙 2/13 · 핵심 신호 2/11 · 중립 규칙 0/2 · 국면 후보 A′']);
 assert.deepEqual(wins[1].items,['단기 조달금리 SOFR: 미충족 → 충족','근원 물가의 최근 속도: 새 규칙 → 미충족','충족 규칙 1/12 → 2/13',
  '핵심 신호 1/11 → 2/11','국면 후보 A → A′',
  '다시 받은 시리즈: T10Y2Y(10년−2년)','오래된 자료가 된 시리즈: NFCICREDIT(NFCI 신용)','오래됨이 풀린 시리즈: WRESBAL(지준)',
  '그때 기록하지 않은 칸(지금 값): 중립 규칙 0/2 · 전환 경계 자동 트리거 0/2']);                     // 바뀐 것처럼 보이는 '기록 없음 →' 줄이 아니다
 for(const w of wins)assert.ok(!w.text.includes('(같음)')&&!w.text.includes('기록 없음 →'),w.text);
 assert.equal(wins[2].text,'4주 전견줄 공개 기록이 없습니다.');                                      // 견줄 기록이 없는 창은 한 줄
 assert.deepEqual(wins[3].items,['2026-11-12 · 단기 조달금리 SOFR 미충족 → 충족','2026-10-30 · 지준과 통화승수 미충족 → 충족']);   // 자료 차례 그대로(새것 먼저)
});

test('home box: unchanged health joins the same line, undecided candidates show as such, no flips says so',()=>{
 const {api,ids}=load();
 const d=changes();d.windows[0].health=health();d.recent=[];
 d.windows[0].candidate={from:'판정불가',to:'A′'};d.windows[0].transition={from:0,to:0};
 api.render(d,null);
 const wins=cls(ids['changes-wrap'],'chg-window');
 assert.deepEqual(tags(wins[0],'li').map(l=>l.textContent),['바뀐 규칙 없음','국면 후보 판정불가 → A′',
  '그대로: 충족 규칙 2/13 · 핵심 신호 2/11 · 중립 규칙 0/2 · 전환 경계 자동 트리거 0/2 · 자료 상태']);
 assert.ok(!wins[1].textContent.includes('자료 상태'));
 assert.equal(wins[3].textContent,'최근 30일 규칙 전환최근 30일 사이 규칙 전환이 없습니다.');
 const t=load();const e=changes();e.windows[1].candidate={from:'A′',to:null};                     // 지금 기록에 절이 없으면 그쪽만 '기록 없음'
 t.api.renderChanges(e);
 assert.ok(cls(t.ids['changes-wrap'],'chg-window')[1].textContent.includes('국면 후보 A′ → 기록 없음'));
});

test('home box: bad items are skipped, the rest is drawn',()=>{
 const {api,ids}=load();
 const d=changes();
 d.headline=['첫 줄',3,null,'',{x:1},'<b>꺾쇠</b>','둘째 줄','셋째 줄','넷째 줄'];                  // 글자만, 셋까지
 d.windows.push({key:'w9',label:'9주 전',from:'2026-09-01',rules:[]},{key:'prev',from:'어제'},null,'w1');
 d.windows[1].rules.push({key:'x',title:'꼴이 틀린 상태',from:'maybe',to:'met'},{key:'y',title:'빈 to',from:'met'},
  {key:'z',title:'<i>꺾쇠</i>',from:'met',to:'not_met'},null);
 d.windows[1].health.lost=[{series:'<b>X</b>',label:'꺾쇠'},{series:'DGS2',label:3},null];
 d.windows[0].core={from:'두 개',to:'2/11'};                                            // 꼴이 틀리면 그 줄만 뺀다
 d.windows[0].transition={from:1.5,to:0};
 d.windows[0].met={from:2,to:'2',total_from:13,total_to:13};
 d.windows[1].transition={from:null,to:3};                                                // 자동 트리거는 둘뿐 — 3은 꼴이 아니다
 d.recent.push({date:'2026-13-01',key:'a',title:'날짜가 틀림',from:'met',to:'not_met'},{date:'2026-11-01',key:'b',title:'상태가 틀림',from:'met',to:'?'},
  {date:'2026-02-30',key:'c',title:'없는 날',from:'met',to:'not_met'},'x');
 assert.equal(api.renderChanges(d),true);
 const box=ids['changes-wrap'],text=box.textContent;
 assert.deepEqual(cls(box,'chg-head')[0].kids.map(k=>k.textContent),['첫 줄','둘째 줄','셋째 줄']);
 assert.deepEqual(cls(box,'chg-window').map(w=>tags(w,'h3')[0].textContent).slice(0,3),['직전 기록 2026-11-15 대비','1주 전 2026-11-10 대비','4주 전']);
 assert.equal(cls(box,'chg-window').length,4);
 for(const gone of ['9주 전','꼴이 틀린 상태','빈 to','꺾쇠','날짜가 틀림','상태가 틀림','없는 날','두 개','핵심 신호 기록 없음 → 2/11','전환 경계 자동 트리거 1/2','충족 규칙 2/13','3/2','전환 경계'])
  assert.ok(!text.includes(gone),gone);
 assert.ok(text.includes('받지 못하게 된 시리즈: DGS2'),text);                                  // 이름이 글자가 아니면 시리즈만
 assert.ok(!STRAY.test(text),text);
});

test('home box: a bad file draws nothing and leaves the box as it was',()=>{
 const bads=[null,undefined,'x',[],{},Object.assign(changes(),{schema:2}),Object.assign(changes(),{schema:'1'}),Object.assign(changes(),{asof:'2026-11-31'}),
  Object.assign(changes(),{headline:'한 줄'}),Object.assign(changes(),{headline:[1,2,'']}),Object.assign(changes(),{windows:{}})];
 for(const d of bads){
  const {api,ids}=load();
  assert.equal(api.renderChanges(d),false,JSON.stringify(d));
  assert.equal(ids['changes-wrap'].kids.length,0);
  assert.deepEqual(plain(api.render(d,null)),{changes:false,ledger:false});
 }
 const t=load({drop:['changes-wrap']});
 assert.equal(t.api.renderChanges(changes()),false);                                   // 자리가 없으면 그리지 않는다
});

// ── 기록 장부 화면 ─────────────────────────────────────────────────────────────────────
test('ledger: protocol box states the version, start rule, series, baseline and its pairs, last points and n_min',()=>{
 const {api,ids}=load();
 assert.equal(api.renderLedger(ledger()),true);
 const wrap=ids['ledger-wrap'];
 assert.equal(tags(wrap,'h2')[0].textContent,'기록 장부');
 assert.equal(tags(wrap,'h2')[0].attrs.id,'ledger-title');
 assert.equal(cls(wrap,'reference-label')[0].textContent,'평가 약속 1판 · 측정 기록 — 예측 아님');   // 판 — README·약속 문장과 같은 낱말
 assert.equal(wrap.kids[1],cls(wrap,'ledger-protocol')[0]);                               // 머리 바로 아래가 약속 상자 — 화면 머리의 설명을 되풀이하지 않는다
 assert.equal(api.ABOUT,undefined);
 const box=cls(wrap,'ledger-protocol')[0],items=tags(tags(box,'ul')[0],'li').map(l=>l.textContent);
 assert.equal(tags(box,'h3')[0].textContent,'평가 약속 1판 · 2026-11-18 고정');
 assert.deepEqual(items,[
  '보는 기간: 전환 뒤 4주 · 13주 — 출발 점은 전환 날 이후(그날 포함) 7일 안의 첫 주간 점(그날 기록은 그 앞날까지의 자료로 정해져 전환을 만든 움직임은 넣지 않습니다), '+
   '끝 점은 출발 점에서 주 수×7일 뒤 날짜의 ±3일 안에서 가장 가까운 주간 점',
  '보는 금리: 미 10년 DGS10 · 10년−2년 T10Y2Y · 기간 프리미엄(Kim-Wright) THREEFYTP10 (FRED)',
  '평균(기준, 계산값): 4주 — 미 10년 +0.4bp · 10년−2년 -0.2bp · 기간 프리미엄(Kim-Wright) +0.1bp / 13주 — 미 10년 +1.3bp · 10년−2년 — · 기간 프리미엄(Kim-Wright) +0.3bp'+
   ' · 기간이 다 지난 주간 쌍으로 잰 값(첫 출발 2021-11-19 ~ 마지막 끝 2026-11-13, 쌍 246~257개 — 시리즈·기간마다 다름)',
  '그래프의 마지막 점: 미 10년 2026-11-13 · 10년−2년 2026-11-16 · 기간 프리미엄(Kim-Wright) 2026-11-06 — 끝 점을 찾을 날의 ±3일이 이 날을 넘으면 기다리는 중',
  "방향별 요약은 약속 뒤 전환이 10건 이상 모였을 때만 — 그 전에는 '판단 보류 (n/10)'",
  api.CAUSE,
  '약속을 고치면 새 판 번호와 날짜를 붙입니다 — 같은 판 안에서도 결과와 평균은 갱신마다 그날 그래프 자료로 다시 잽니다.']);
 assert.ok(api.CAUSE.endsWith('니다.'),api.CAUSE);                                          // 화면의 글은 합니다체
 assert.ok(api.CAUSE.includes('그 규칙 때문이라는 뜻이 아닙니다'));
 assert.deepEqual(tags(box,'a').map(a=>[a.textContent,a.attrs.href]),OUT.map(([,,s])=>[s,'https://fred.stlouisfed.org/series/'+s]));
 const text=cls(box,'ledger-text')[0];                                                    // 약속 문장은 닫힌 접는 칸 안에 자료 그대로
 assert.equal(text.tag,'details');
 assert.ok(!('open' in text.attrs));
 assert.equal(tags(text,'summary')[0].textContent,'약속 문장 2개(자료 파일 그대로)');
 assert.deepEqual(cls(text,'notices')[0].kids.map(k=>k.textContent),ledger().protocol.text);
 assert.equal(cls(wrap,'ledger-basis')[0].textContent,'기록: 2026-09-27부터 2026-11-17까지 공개 기록 40일 치(읽지 못해 건너뛴 파일 1개). '+
  '결과와 평균(기준)은 2026-11-17의 그래프 자료(charts.json 주간 점, 2021-11-19~2026-11-13)로 갱신마다 다시 잽니다. '+
  "FRED가 값을 고치거나 그래프 창이 한 주씩 옮겨 가면 평균을 뺀 값이 조금씩 달라지고, 출발 점이 창 밖으로 나간 전환은 '자료 없음'이 됩니다.");
 // 쌍의 범위가 없으면 그래프 자료 범위라고만, 그것도 없으면 붙이지 않는다. 마지막 점이 없으면 그 줄이 없다
 const d=ledger();d.charts.baseline_detail={'4':{dgs10:{n:-1,from:'2021-11-19',to:'2026-11-06'},t10y2y:'x'}};delete d.charts.last;
 const t=load();t.api.renderLedger(d);
 const li=tags(tags(cls(t.ids['ledger-wrap'],'ledger-protocol')[0],'ul')[0],'li').map(l=>l.textContent);
 assert.ok(li[2].endsWith(' · 그래프 자료 범위 2021-11-19~2026-11-13 안에서 잰 값'),li[2]);
 assert.ok(!li.some(x=>x.startsWith('그래프의 마지막 점')));
 d.charts.window=null;t.api.renderLedger(d);
 assert.ok(tags(tags(cls(t.ids['ledger-wrap'],'ledger-protocol')[0],'ul')[0],'li')[2].textContent.endsWith('+0.3bp'));
});

test('ledger: the computed-values notice and FRED citations close the protocol box, bad ones are skipped',()=>{
 const {api,ids}=load();
 api.renderLedger(ledger());
 const cite=cls(cls(ids['ledger-wrap'],'ledger-protocol')[0],'ledger-cite')[0];
 assert.deepEqual(cite.kids.map(k=>k.textContent),[...ledger().notices,'권장 인용: '+OUT.map(([,,sid])=>CITES[sid]).join(' ')]);
 const d=ledger();
 d.sources=[{series:'DGS10',citation:'<b>나쁨</b>, retrieved from FRED, November 17, 2026.'},{series:'T10Y2Y',citation:'retrieved 없음'},
  {series:'BAA10Y',citation:CITES.DGS10.replace('DGS10','BAA10Y')},{series:'THREEFYTP10',citation:CITES.THREEFYTP10},
  {series:'THREEFYTP10',citation:CITES.THREEFYTP10},null,'x'];
 d.notices=['한 줄',3,null,'<i>꺾쇠</i>'];
 api.renderLedger(d);
 const c2=cls(cls(ids['ledger-wrap'],'ledger-protocol')[0],'ledger-cite')[0];
 assert.deepEqual(c2.kids.map(k=>k.textContent),['한 줄','권장 인용: '+CITES.THREEFYTP10]);       // 장부의 세 시리즈만, 시리즈마다 하나
 d.sources=[];d.notices=[];api.renderLedger(d);
 assert.equal(cls(ids['ledger-wrap'],'ledger-cite').length,0);
});

test('ledger: the rule table shows state, since, counts, the latest flip and its 4-week move',()=>{
 const {api,ids}=load();
 api.renderLedger(ledger());
 const table=cls(ids['ledger-wrap'],'ledger-rules')[0];
 assert.ok(cls(ids['ledger-wrap'],'ledger-scroll').some(s=>s.kids[0]===table));         // 표는 가로 스크롤 상자 안
 assert.deepEqual(tags(tags(table,'thead')[0],'th').map(t=>t.textContent),
  ['규칙','지금 상태','언제부터','전환 수(약속 뒤 / 전)','최근 전환','4주 뒤 미 10년(평균을 뺀 값)']);   // 칸의 숫자가 무엇인지 머리에
 const cap='규칙별 상태와 전환 — 마지막 열은 최근 전환 뒤 4주의 미 10년 변화에서 평균을 뺀 값';
 assert.equal(capOf(ids['ledger-wrap'],table).textContent,cap);                            // 표의 이름 = 표 밖의 설명 줄(aria-labelledby)
 assert.ok(!('aria-label' in table.attrs));                                                // 같은 글을 두 번 읽지 않게
 assert.equal(cls(ids['ledger-wrap'],'ledger-cap').map(c=>c.textContent).filter(t=>t===cap).length,1);   // 좁은 화면에서 접힌다
 assert.equal(tags(ids['ledger-wrap'],'caption').length,0);                              // 표 안의 caption은 스크롤 상자에 잘린다
 const rows=tags(tags(table,'tbody')[0],'tr').map(r=>r.kids.map(k=>k.textContent));
 assert.deepEqual(rows,[
  ['단기 조달금리 SOFR','충족','2026-11-12','0 / 3','2026-11-12 미충족 → 충족약속 전','기다리는 중끝 점 2026-12-04±3일'],   // 최근 = 날짜가 가장 늦은 전환
  ['10년 기간 프리미엄','미충족','2027-01-08','1 / 0','2027-01-08 충족 → 미충족','-7.7bp'],             // 평균을 뺀 값
  ['10년−2년 금리차','미충족','기록 시작(2026-09-27) 이전부터','0 / 0','없음','—']]);                   // 전환이 없으면 기록의 앞 끝에서 잘린 날
 assert.deepEqual(cls(table,'tag').map(t=>t.attrs.class),['tag met','tag not_met','tag not_met']);
 const d=ledger();d.rules[0].events=[d.rules[0].events[2]];                               // 4주 뒤 자료가 없는 전환
 api.renderLedger(d);
 const first=tags(tags(cls(ids['ledger-wrap'],'ledger-rules')[0],'tbody')[0],'tr')[0];
 assert.equal(first.kids[5].textContent,'자료 없음');
});

test('ledger: since and now for rules added later, first judged late, undeterminable now, and no longer published',()=>{
 const {api,ids}=load();
 const d=ledger();
 const rule=(o)=>Object.assign({first:'2026-09-27',start:'not_met',now:'not_met',since:'2026-09-27',last:'2026-11-17',unknown_days:0,events:[],summary:hold(0)},o);
 d.rules=[
  rule({key:'added',title:'더한 규칙',first:'2026-10-14',since:'2026-10-14'}),
  rule({key:'late',title:'늦게 판정된 규칙',since:'2026-10-02',unknown_days:3}),
  rule({key:'gone_unknown',title:'지금 판정 불가',start:'not_met',now:'unknown',since:'2026-10-17',unknown_days:1,
   events:[{date:'2026-10-17',from:'not_met',to:'met',before_protocol:true,core:null,candidate:null,
    outcomes:{'4':each(()=>pending('2026-10-16')),'13':each(()=>pending('2026-10-16'))}}]}),
  rule({key:'open_unknown',title:'처음부터 이어진 뒤 판정 불가',start:'met',now:'unknown',unknown_days:1}),
  rule({key:'never',title:'판정된 적 없음',start:null,now:'unknown',since:null,unknown_days:40}),
  rule({key:'retired',title:'지금은 없는 규칙',last:'2026-10-20'})];
 api.renderLedger(d);
 const wrap=ids['ledger-wrap'];
 const rows=tags(tags(cls(wrap,'ledger-rules')[0],'tbody')[0],'tr').map(r=>r.kids.slice(0,3).map(k=>k.textContent));
 assert.deepEqual(rows,[
  ['더한 규칙','미충족','규칙 추가(2026-10-14)부터'],
  ['늦게 판정된 규칙','미충족','첫 판정(2026-10-02)부터'],
  ['지금 판정 불가','판정 불가','—직전 판정 충족 · 2026-10-17부터'],                               // 판정 불가가 10-17부터라는 뜻이 아니다
  ['처음부터 이어진 뒤 판정 불가','판정 불가','—직전 판정 충족 · 기록 시작(2026-09-27) 이전부터'],
  ['판정된 적 없음','판정 불가','—'],
  ['지금은 없는 규칙','지금은 싣지 않는 규칙마지막 기록 2026-10-20 · 미충족','—']]);
 const facts=cls(wrap,'ledger-rule').map(x=>x.kids[1].textContent);
 assert.deepEqual(facts,[
  '처음 기록 2026-10-14 · 처음 상태 미충족 · 지금 미충족 · 규칙 추가(2026-10-14)부터 · 판정 불가 기록 0일',
  '처음 기록 2026-09-27 · 처음 상태 미충족 · 지금 미충족 · 첫 판정(2026-10-02)부터 · 판정 불가 기록 3일',
  '처음 기록 2026-09-27 · 처음 상태 미충족 · 지금 판정 불가 · 직전 판정 충족, 2026-10-17부터 · 판정 불가 기록 1일',
  '처음 기록 2026-09-27 · 처음 상태 충족 · 지금 판정 불가 · 직전 판정 충족, 기록 시작(2026-09-27) 이전부터 · 판정 불가 기록 1일',
  '처음 기록 2026-09-27 · 처음 상태 기록 없음 · 지금 판정 불가 · 판정 불가 기록 40일',
  '처음 기록 2026-09-27 · 처음 상태 미충족 · 지금은 싣지 않는 규칙 · 마지막 기록 2026-10-20(미충족) · 판정 불가 기록 0일']);
 const text=wrap.textContent;
 assert.ok(!/판정 불가\(20/.test(text),text);
 assert.ok(!STRAY.test(text),text);
});

test('ledger: headings name the protocol, the rule table and the per-rule records; tables are named by their caption line',()=>{
 const {api,ids}=load();
 api.renderLedger(ledger());
 const wrap=ids['ledger-wrap'];
 assert.deepEqual(tags(wrap,'h3').map(h=>h.textContent),['평가 약속 1판 · 2026-11-18 고정','규칙별 상태','규칙별 전환 기록']);
 const tables=tags(wrap,'table');
 assert.ok(tables.length>3);
 const ids_=tables.map(t=>t.attrs['aria-labelledby']);
 assert.equal(new Set(ids_).size,ids_.length);                                             // 표마다 다른 id
 for(const t of tables){assert.ok(capOf(wrap,t),t.attrs['aria-labelledby']);assert.ok(!('aria-label' in t.attrs));}
});

test('ledger: every flip is listed in a closed details with context and both horizons',()=>{
 const {api,ids}=load();
 api.renderLedger(ledger());
 const det=cls(ids['ledger-wrap'],'ledger-rule');
 assert.equal(det.length,3);
 for(const d of det)assert.ok(!('open' in d.attrs));
 assert.deepEqual(det.map(d=>tags(d,'summary')[0].textContent),
  ['단기 조달금리 SOFR · 전환 3건(약속 전 3건 포함)','10년 기간 프리미엄 · 전환 1건','10년−2년 금리차 · 전환 0건']);
 assert.equal(det[0].kids[1].textContent,'처음 기록 2026-09-27 · 처음 상태 미충족 · 지금 충족 · 2026-11-12부터 · 판정 불가 기록 0일');
 assert.equal(det[2].kids[1].textContent,'처음 기록 2026-09-27 · 처음 상태 미충족 · 지금 미충족 · 기록 시작(2026-09-27) 이전부터 · 판정 불가 기록 2일');
 const ev=cls(det[0],'ledger-event');
 assert.deepEqual(ev.map(e=>e.kids[0].textContent),[                                      // 날짜 차례로
  '2026-09-29 미충족 → 충족약속 전','2026-10-02 충족 → 미충족약속 전','2026-11-12 미충족 → 충족약속 전 · 그날 핵심 신호 2/11 · 국면 후보 A′']);
 const out=cls(ev[0],'ledger-out')[0];
 assert.equal(capOf(det[0],out).textContent,'2026-09-29 전환 뒤 변화(주간 점, bp)');
 assert.deepEqual(tags(tags(out,'thead')[0],'th').map(t=>t.textContent),['기간',...OUT.map(o=>o[1])]);
 const cells=tags(tags(out,'tbody')[0],'tr').map(r=>r.kids.map(k=>k.textContent));
 assert.deepEqual(cells,[
  ['4주 뒤','+12.3bp평균을 뺀 값 +11.9bp2026-09-26 → 2026-10-24','-4.0bp평균을 뺀 값 -3.8bp2026-09-26 → 2026-10-24','자료 없음'],
  ['13주 뒤',...Array(3).fill('기다리는 중출발 2026-09-26 · 끝 점 2026-12-26±3일')]]);                 // 끝 점을 찾을 날 = 출발 + 91일
 assert.equal(det[2].kids[2].textContent,'전환이 없습니다.');
 const tp=tags(tags(cls(det[1],'ledger-out')[0],'tbody')[0],'tr')[0].kids.map(k=>k.textContent);
 assert.deepEqual(tp,['4주 뒤','-7.3bp평균을 뺀 값 -7.7bp2027-01-08 → 2027-02-05','기다리는 중출발 2027-01-08 · 끝 점 2027-02-05±3일','0.0bp평균을 뺀 값 -0.1bp2027-01-08 → 2027-02-05']);
});

test('ledger: direction summaries stay on hold until n reaches n_min',()=>{
 const {api,ids}=load();
 api.renderLedger(ledger());
 const det=cls(ids['ledger-wrap'],'ledger-rule');
 const sum=cls(det[1],'ledger-sum')[0];
 assert.equal(capOf(det[1],sum).textContent,'방향별 요약 — 약속 뒤 전환만, 10건이 모이기 전에는 판단 보류');
 const rows=tags(tags(sum,'tbody')[0],'tr').map(r=>r.kids.map(k=>k.textContent));
 assert.deepEqual(rows,[
  ['충족으로 바뀐 뒤 4주','평균을 뺀 값 -3.5bp오른 비율 42% · 12건','판단 보류 (0/10)','판단 보류 (9/10)'],
  ['충족으로 바뀐 뒤 13주','판단 보류 (0/10)','판단 보류 (0/10)','판단 보류 (0/10)'],
  ['미충족으로 바뀐 뒤 4주','판단 보류 (0/10)','판단 보류 (0/10)','판단 보류 (0/10)'],
  ['미충족으로 바뀐 뒤 13주','판단 보류 (0/10)','판단 보류 (0/10)','판단 보류 (0/10)']]);
 const s0=tags(tags(cls(det[0],'ledger-sum')[0],'tbody')[0],'tr');
 assert.ok(s0.every(r=>r.kids.slice(1).every(k=>k.textContent==='판단 보류 (0/10)')));
});

test('ledger: bad rules, flips, cells and summaries are skipped or shown as a dash',()=>{
 const {api,ids}=load();
 const d=ledger();
 d.rules.push(null,'x',{key:'Bad Key',title:'키가 틀림',first:'2026-09-27',start:null,now:'met',events:[]},
  {key:'no_title',first:'2026-09-27',start:null,now:'met',events:[]},{key:'bad_now',title:'상태가 틀림',first:'2026-09-27',start:null,now:'?',events:[]},
  {key:'bad_start',title:'시작이 틀림',first:'2026-09-27',start:'unknown',now:'met',events:[]});
 d.rules[2].events.push({date:'2026-11-03',from:'met',to:'met',before_protocol:false,outcomes:{}},                 // 같은 상태는 전환이 아니다
  {date:'어제',from:'met',to:'not_met',before_protocol:false,outcomes:{}},{date:'2026-11-03',from:'met',to:'unknown',before_protocol:false,outcomes:{}},
  {date:'2026-11-03',from:'met',to:'not_met',before_protocol:'아니오',outcomes:{}},null);
 d.rules[1].events[0].outcomes['4'].tp={state:'done',start:'2027-01-08',end:'2027-02-05',change_bp:null,demeaned_bp:1};   // 숫자가 없는 done
 d.rules[1].events[0].outcomes['4'].t10y2y={state:'maybe'};
 d.rules[1].events[0].core='둘';d.rules[1].events[0].candidate='<b>B</b>';
 d.rules[1].summary.to_met['4'].dgs10={n:12,mean_demeaned_bp:null,up_share:0.4};
 d.rules[1].summary.to_met['13'].dgs10={n:-1};
 d.rules[1].summary.to_met['13'].tp={n:11,mean_demeaned_bp:2,up_share:1.5};
 d.rules[1].since='2027-02-30';d.rules[1].unknown_days=-1;
 d.protocol.text.push(7,'',null);
 assert.equal(api.renderLedger(d),true);
 const wrap=ids['ledger-wrap'],text=wrap.textContent;
 assert.equal(cls(wrap,'ledger-rule').length,3);
 for(const gone of ['키가 틀림','상태가 틀림','시작이 틀림','그날 핵심 신호 둘','<b>','판정 불가 기록 -1일'])assert.ok(!text.includes(gone),gone);
 const det=cls(wrap,'ledger-rule');
 assert.equal(tags(det[2],'summary')[0].textContent,'10년−2년 금리차 · 전환 0건');
 assert.equal(det[1].kids[1].textContent,'처음 기록 2026-09-27 · 처음 상태 충족 · 지금 미충족');
 assert.equal(cls(det[1],'ledger-event')[0].kids[0].textContent,'2027-01-08 충족 → 미충족');
 const row=tags(tags(cls(det[1],'ledger-out')[0],'tbody')[0],'tr')[0].kids.map(k=>k.textContent);
 assert.deepEqual(row.slice(2),['—','—']);
 const sum=tags(tags(cls(det[1],'ledger-sum')[0],'tbody')[0],'tr').map(r=>r.kids.map(k=>k.textContent));
 assert.equal(sum[0][1],'—');
 assert.equal(sum[1][1],'—');
 assert.equal(sum[1][3],'—');
 assert.equal(tags(tags(cls(wrap,'ledger-rules')[0],'tbody')[0],'tr')[1].kids[2].textContent,'—');   // 언제부터가 틀린 날짜
 assert.equal(cls(cls(wrap,'ledger-protocol')[0],'ledger-text')[0].textContent,'약속 문장 2개(자료 파일 그대로)'+ledger().protocol.text.join(''));
 assert.ok(!STRAY.test(text),text);
});

test('ledger: a bad file draws nothing — the page shows its empty line instead',()=>{
 const base=ledger();
 const with_=(f)=>{const d=ledger();f(d);return d;};
 const bads=[null,undefined,'x',[],{},Object.assign(ledger(),{schema:2}),Object.assign(ledger(),{rules:{}}),Object.assign(ledger(),{protocol:null}),
  with_(d=>{d.protocol.version=0;}),with_(d=>{d.protocol.fixed='2026-11-31';}),with_(d=>{d.protocol.horizons_weeks=['4',0];}),
  with_(d=>{d.protocol.outcomes=[{key:'DGS10',label:'미 10년',series:'dgs10'}];}),with_(d=>{d.protocol.n_min=0;}),
  with_(d=>{d.protocol.tolerance_days=-1;})];
 for(const d of bads){
  const {api,ids}=load();
  assert.equal(api.renderLedger(d),false,JSON.stringify(d));
  assert.equal(ids['ledger-wrap'].kids.length,0);
 }
 assert.ok(base);
 const {api}=load();
 assert.equal(api.EMPTY,'기록 장부를 불러오지 못했습니다. 자료가 갱신된 뒤 다시 확인해 주세요.');
 assert.ok(PAGE.includes('<p id="ledger-empty" class="empty-state" hidden>'+api.EMPTY+'</p>'));   // 그 빈 줄은 index.html에 있다
 const t=load({drop:['ledger-wrap']});
 assert.equal(t.api.renderLedger(ledger()),false);
});

test('ledger: an empty rule list still shows the protocol, and missing charts are said plainly',()=>{
 const {api,ids}=load();
 const d=ledger();d.rules=[];d.charts={date:null,window:null,baseline:null};d.history={from:null,to:null,snapshots:0,skipped:0};
 assert.equal(api.renderLedger(d),true);
 const text=ids['ledger-wrap'].textContent;
 assert.ok(text.includes('규칙 기록이 없습니다.'));
 assert.ok(text.includes('평균(기준, 계산값): 4주 — 미 10년 — · 10년−2년 — · 기간 프리미엄(Kim-Wright) — / 13주'));
 assert.equal(cls(ids['ledger-wrap'],'ledger-rules-detail').length,0);                        // 규칙이 없으면 전환 기록 칸도 없다
 assert.equal(cls(ids['ledger-wrap'],'ledger-basis')[0].textContent,'기록: 기록 없음 공개 기록 0일 치. 그래프 자료가 없어 결과를 적지 못했습니다.');
 assert.ok(!STRAY.test(text),text);
});

test('one broken part does not take the other down',()=>{
 const {api,ids}=load();
 const bad=ledger();Object.defineProperty(bad,'rules',{get(){throw new Error('깨짐');}});
 assert.deepEqual(plain(api.render(changes(),bad)),{changes:true,ledger:false});
 assert.ok(ids['changes-wrap'].kids.length>0);
 const t=load();
 const badC=changes();Object.defineProperty(badC,'windows',{get(){throw new Error('깨짐');}});
 assert.deepEqual(plain(t.api.render(badC,ledger())),{changes:false,ledger:true});
});

test('no stray words, no verdict words, sign and rounding of bp',()=>{
 const {api,ids}=load();
 api.render(changes(),ledger());
 const all=ids['changes-wrap'].textContent+ids['ledger-wrap'].textContent;
 assert.ok(!STRAY.test(all),all);
 for(const w of VERDICT){assert.ok(!all.includes(w),w);assert.ok(!SRC.includes(w),w);}
 for(const w of ['예측이 아닙니다','예측 아님'])assert.ok(all.includes(w),w);
 // 부호: 양(+)은 +, 음(−)은 -, 0으로 반올림되면 부호 없이(-0.04 → 0.0)
 const d=ledger();
 d.rules[1].events[0].outcomes['4'].dgs10=done('2027-01-08','2027-02-05',-0.04,0.05);
 d.rules[1].events[0].outcomes['4'].tp=done('2027-01-08','2027-02-05',2.25,-2.25);
 api.renderLedger(d);
 const row=tags(tags(cls(cls(ids['ledger-wrap'],'ledger-rule')[1],'ledger-out')[0],'tbody')[0],'tr')[0].kids.map(k=>k.textContent);
 assert.equal(row[1],'0.0bp평균을 뺀 값 +0.1bp2027-01-08 → 2027-02-05');
 assert.equal(row[3],'+2.3bp평균을 뺀 값 -2.3bp2027-01-08 → 2027-02-05');
});

test('the card script stays text-only and leans on index.html helpers only',()=>{
 const code=SRC.replace(/\/\*[\s\S]*?\*\//g,'').replace(/\/\/[^\n]*/g,'');
 for(const w of ['innerHTML','outerHTML','insertAdjacentHTML','createElement','fetch(','localStorage','location.','eval(','new Function'])
  assert.ok(!code.includes(w),w);
 assert.ok(/window\.LedgerView = \(\(\) => \{/.test(SRC));
 assert.ok(PAGE.indexOf('<script src="ledger.js"></script>')>PAGE.indexOf('<script src="cds.js"></script>'));
});

// ── index.html 연결 ──────────────────────────────────────────────────────────────────
function braceBlock(text,start){
 let i=text.indexOf('{',start),depth=0;
 for(;i<text.length;i++){depth+=(text[i]==='{')-(text[i]==='}');if(depth===0)return text.slice(start,i+1);}
 throw new Error('짝이 맞지 않음');
}
test('applyView opens the home box only on the home view and the ledger box only on #ledger',()=>{
 const groups=PAGE.slice(PAGE.indexOf('const GROUPS = ['),PAGE.indexOf('];',PAGE.indexOf('const GROUPS = ['))+2);
 const apply=braceBlock(PAGE,PAGE.indexOf('function applyView() {'));
 const nodes={};
 const node=id=>nodes[id]||(nodes[id]={id,hidden:false,textContent:'',dataset:{},setAttribute(){},removeAttribute(){}});
 const sc={location:{hash:''},window:{},document:{getElementById:node,querySelectorAll:()=>[],querySelector:()=>null}};
 const api=vm.runInNewContext('let activeView = "all", ruleState = "all", publicData = null;\n'+
  'const available = { overview: false, korea: false, snapshot: false, loaded: false, monitor: false, ai: false, regime: false, aiCredit: false, changes: false, ledger: false };\n'+
  groups+'\n'+apply+'\n({applyView, set: o => Object.assign(available, o)})',sc);
 const seen=(hash,avail)=>{api.set(Object.assign({loaded:true,changes:false,ledger:false},avail));sc.location.hash=hash;api.applyView();
  return {changes:!nodes['changes-wrap'].hidden,ledger:!nodes['ledger-wrap'].hidden,empty:!nodes['ledger-empty'].hidden,
   rules:!nodes['rules-wrap'].hidden,view:nodes.main.dataset.view,title:nodes['view-title'].textContent};};
 const home=seen('',{changes:true,ledger:true});
 assert.deepEqual([home.changes,home.ledger,home.empty,home.view],[true,false,false,'all']);
 const led=seen('#ledger',{changes:true,ledger:true});
 assert.deepEqual([led.changes,led.ledger,led.empty,led.rules,led.view,led.title],[false,true,false,false,'ledger','기록 장부 · 평가 약속']);
 assert.ok(nodes['view-description'].textContent.includes('예측이 아니고'));
 const none=seen('#ledger',{changes:true,ledger:false});
 assert.deepEqual([none.ledger,none.empty],[false,true]);                                      // 자료가 없으면 빈 줄
 assert.equal(seen('#ledger',{ledger:false,loaded:false}).empty,false);                          // 읽는 중에는 빈 줄도 없다
 assert.deepEqual([seen('',{changes:false}).changes,seen('#ai',{changes:true}).changes,seen('#rates',{changes:true}).changes],[false,false,false]);
 assert.equal(seen('#ai',{ledger:false}).empty,false);
});
test('the command line goes to the ledger on its exact words only',()=>{
 const i=PAGE.indexOf('const VIEWS = ['),j=PAGE.indexOf('document.getElementById("cmd-form")',i);
 assert.ok(i>0&&j>i,'명령줄 부분을 찾지 못함');
 const sc={location:{hash:''}};
 const go=vm.runInNewContext(PAGE.slice(i,j)+'\ngo',sc);
 for(const q of ['기록','장부','기록 장부','평가 약속','ledger','LEDGER',' 기록 ']){sc.location.hash='';assert.equal(go(q),true,q);assert.equal(sc.location.hash,'ledger',q);}
 for(const q of ['led','기','기록 보기','장']){sc.location.hash='x';go(q);assert.notEqual(sc.location.hash,'ledger',q);}
 sc.location.hash='';go('a');assert.equal(sc.location.hash,'all');                              // 'ai'와 같이 앞부분 검색에 끼지 않는다
 assert.ok(PAGE.includes('<a href="#ledger" data-view="ledger">기록 장부<span>평가 약속</span></a>'));
});

test('ledger: a flip with no weekly point yet on or after its day waits without a start (2026-11-18 출발 점 규칙)',()=>{
 const {api,ids}=load();
 const d=ledger();
 const nostart={state:'pending',start:null,end:null,change_bp:null,demeaned_bp:null};
 d.rules[0].events=[{date:'2026-11-18',from:'not_met',to:'met',before_protocol:false,core:null,candidate:null,
  outcomes:{'4':each(()=>nostart),'13':each(()=>nostart)}}];
 api.renderLedger(d);
 const wrap=ids['ledger-wrap'];
 const row=tags(tags(cls(wrap,'ledger-rules')[0],'tbody')[0],'tr')[0];
 assert.equal(row.kids[5].textContent,'기다리는 중');                                     // 끝 점 날짜를 짓지 않는다
 const cells=tags(cls(wrap,'ledger-out')[0],'td').map(t=>t.textContent);
 assert.deepEqual(cells,Array(6).fill('기다리는 중'));
 assert.ok(!/undefined|NaN|null/.test(wrap.textContent));
 d.protocol.start_days=99;api.renderLedger(d);                                            // 꼴 밖의 값이면 날 수를 빼고 적는다
 assert.ok(tags(tags(cls(ids['ledger-wrap'],'ledger-protocol')[0],'ul')[0],'li')[0].textContent.startsWith('보는 기간: 전환 뒤 4주 · 13주 — 출발 점은 전환 날 이후(그날 포함)의 첫 주간 점'));
});
