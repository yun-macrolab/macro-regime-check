// 판단 연표(site/timeline.js) — 아주 작은 가짜 DOM 위에서 render()를 돌려 글을 본다. 자료는 scripts/timeline_build.py가 쓰는 꼴
// (data/timeline.json)을 손으로 지은 것이고 숫자 · 커밋 · 시각은 지어낸 것이다. lp.js를 같은 창에 함께 실어 판단 격자 칸 이름을
// 운영자 표와 견주는지도 본다. 맨 끝 둘은 index.html의 applyView 가운데 이 절에 닿는 부분을 잘라 돌리고(기록 장부 화면에서만
// 열리는지), 스크립트가 글자로만 그리는지 본다.
// 실행: node --test scripts/test_timeline_render.cjs
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const SRC=fs.readFileSync(path.join(__dirname,'../site/timeline.js'),'utf8');
const LP=fs.readFileSync(path.join(__dirname,'../site/lp.js'),'utf8');
const PAGE=fs.readFileSync(path.join(__dirname,'../site/index.html'),'utf8');
const STRAY=/undefined|NaN|null|\[object/;
const BANNED=['매수','매도','유망','적중','맞았다','틀렸다','전망','예상','추천','성적'];

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

function load(opts={}){
 const ids={'timeline-wrap':new El('section')};
 for(const id of opts.drop||[])delete ids[id];
 const el=(tag,attrs,...kids)=>{const n=new El(tag);for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,v);for(const c of kids)if(c!==null&&c!==undefined)n.append(c);return n;};
 const link=(text,url)=>/^https:\/\/(fred\.stlouisfed\.org|github\.com)\//.test(url)?el('a',{href:url},text):text;   // index.html의 link()와 같은 꼴
 const ctx=vm.createContext({window:{},document:{getElementById:id=>ids[id]||null},el,link});
 if(opts.lp!==false)vm.runInContext(LP,ctx);                                    // index.html처럼 lp.js가 먼저
 vm.runInContext(SRC,ctx);
 return {api:ctx.window.TimelineView,lp:ctx.window.LpCard,ids,wrap:ids['timeline-wrap']};
}
const draw=(d,opts)=>{const t=load(opts);const ok=t.api.render(d);return Object.assign(t,{ok});};
const tableOf=(root,c)=>walk(root,n=>n.tag==='table'&&(n.attrs.class||'').split(' ').includes(c))[0];
const capOf=(root,table)=>cls(root,'ledger-cap').find(p=>p.attrs.id===table.attrs['aria-labelledby']);
const bodyRows=t=>tags(tags(t,'tbody')[0],'tr');
const cells=r=>r.kids.map(k=>k.textContent);

// ── 지은 자료 ─────────────────────────────────────────────────────────────────────────
const SHA=n=>String(n).repeat(40).slice(0,40).replace(/[^0-9a-f]/g,'a');
const REPO='yun-macrolab/macro-notes-automation';
const done=(start,end,change,dem)=>({state:'done',start,end,change_bp:change,demeaned_bp:dem});
const pending=start=>({state:'pending',start,end:null,change_bp:null,demeaned_bp:null});
const missing=start=>({state:'missing',start,end:null,change_bp:null,demeaned_bp:null});
const both=(d,c)=>({dur:d,cur:c});
const site=(snapshot,core,candidate,met)=>({snapshot,core,met:met===undefined?null:met,candidate});
const NEUTRAL=t=>({total:t,verdict:'Neutral'});
const hold=()=>({'1':{n:0,mean_demeaned_bp:null,up_share:null},'4':{n:0,mean_demeaned_bp:null,up_share:null}});
const CITES={DGS10:'Board of Governors of the Federal Reserve System (US), 지어낸 제목 [DGS10], retrieved from FRED, Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/DGS10, November 19, 2026.',
 T10Y2Y:'Federal Reserve Bank of St. Louis, 지어낸 제목 [T10Y2Y], retrieved from FRED, Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/T10Y2Y, November 19, 2026.'};
function week(o){
 return Object.assign({state:'confirmed',lock:null,before_protocol:true,dur:NEUTRAL(0),cur:NEUTRAL(0),edited_n:0,regime_flag:null,
  changed_after:null,site:null,lp:null,outcomes:{}},o);
}
function timeline(){
 return {schema:1,generated_at:'2026-11-19T07:31:00+09:00',
  notice:'운영자의 주간 판정을 공개 기록에서 옮긴 것이다. 투자 판단이나 권유가 아니고 측정 기록이다.',
  label:'운영자 주간 판정(공개 기록에서 옮김) — 투자 판단·권유 아님 · 측정 기록',
  source:{repo:REPO,path:'records/',site:'https://yun-macrolab.github.io/macro-notes-automation/',newest_commit:SHA('1d0b26b'),
   checked_at:'2026-11-18T22:31:00+00:00',via:'api',skipped_versions:0},
  protocol:{version:1,fixed:'2026-11-19',horizons_weeks:[1,4],
   pairs:[{verdict:'dur',series:'DGS10',label:'미 10년',line:'dgs10'},{verdict:'cur',series:'T10Y2Y',label:'10년−2년',line:'t10y2y'}],
   n_min:10,tolerance_days:3,start_days:7,open_utc:'13:30',
   text:['판단 연표 약속 1판 — 2026-11-19에 정했다.','판정은 records/<그 주 월요일>.json이 처음 확정으로 올라간 커밋의 내용이다.',
    '측정 기록이다 — 판정의 좋고 나쁨을 가리지 않는다.']},
  charts:{date:'2026-11-18',baseline:{'1':{dgs10:1.3,t10y2y:-0.2},'4':{dgs10:5.5,t10y2y:-0.9}},
   baseline_detail:{'1':{dgs10:{n:260,from:'2021-11-19',to:'2026-11-13'},t10y2y:{n:260,from:'2021-11-19',to:'2026-11-13'}},
    '4':{dgs10:{n:257,from:'2021-11-19',to:'2026-10-23'},t10y2y:{n:257,from:'2021-11-19',to:'2026-10-23'}}},
   last:{dgs10:'2026-11-16',t10y2y:'2026-11-17'}},
  // 차례를 일부러 섞는다 — 화면은 새 주가 위
  weeks:[
   week({week:'2026-10-12',end:'2026-10-18',lock:{sha:SHA('5caf129'),at:'2026-10-26T13:05:12+09:00',late:true},
    site:site('2026-10-18','1/11','A′'),lp:{month:'2026-08',L:'L0',P:'P+',cell:'금리 상방 관찰 (물가 선행)'},
    outcomes:{'1':both(done('2026-10-30','2026-11-06',-8.04,-9.3),done('2026-10-30','2026-11-06',-3,-2.8)),
     '4':both(pending('2026-10-30'),pending('2026-10-30'))}}),
   week({week:'2026-11-16',end:'2026-11-22',state:'in_progress',before_protocol:false,dur:NEUTRAL(0.1),cur:NEUTRAL(0.2),
    site:site('2026-11-18','2/11','A′'),lp:{month:'2026-09',L:'L+',P:'P+',cell:'금리 상방 여지 (확인)'}}),
   week({week:'2026-11-09',end:'2026-11-15',lock:{sha:SHA('d2728b4'),at:'2026-11-16T13:02:41+09:00',late:false},dur:NEUTRAL(0.1),cur:NEUTRAL(0.2),
    site:site('2026-11-15','2/11','판정불가'),lp:{month:'2026-09',L:'L+',P:'P+',cell:'금리 상방 여지 (확인)'},
    outcomes:{'1':both(pending('2026-11-13'),pending('2026-11-13')),'4':both(pending('2026-11-13'),pending('2026-11-13'))}}),
   week({week:'2026-09-21',end:'2026-09-27',lock:{sha:SHA('0a1b2c3'),at:'2026-09-28T13:04:00+09:00',late:false},
    dur:{total:-0.9,verdict:'U/W'},cur:{total:0.88,verdict:'Flattening'},site:site(null,null,null),lp:null,
    outcomes:{'1':both(done('2026-09-25','2026-10-02',6.2,4.9),done('2026-09-25','2026-10-02',-1.04,-0.84)),
     '4':both(done('2026-09-25','2026-10-23',-2.35,-7.85),done('2026-09-25','2026-10-23',-4,-3.1))}}),
   week({week:'2026-10-26',end:'2026-11-01',lock:{sha:SHA('3b4c5d6'),at:'2026-11-02T13:03:00+09:00',late:false},
    site:site('2026-11-01','2/11','A′'),lp:{month:'2026-09',L:'L+',P:'P+',cell:'금리 상방 여지 (확인)'},
    outcomes:{'1':both(done('2026-10-30','2026-11-06',-8.04,-9.3),done('2026-10-30','2026-11-06',-3,-2.8)),'4':both(pending('2026-10-30'),pending('2026-10-30'))}}),
   week({week:'2026-11-02',end:'2026-11-08',lock:{sha:SHA('7e8f9a0'),at:'2026-11-09T13:01:00+09:00',late:false},dur:NEUTRAL(0.1),cur:NEUTRAL(0.2),
    site:site('2026-11-08','2/11','A′'),lp:{month:'2026-09',L:'L+',P:'P+',cell:'금리 상방 여지 (확인)'},
    outcomes:{'1':both(done('2026-11-06','2026-11-13',29,27.7),done('2026-11-06','2026-11-13',-8,-7.8)),'4':both(pending('2026-11-06'),pending('2026-11-06'))}}),
   week({week:'2026-10-05',end:'2026-10-11',lock:{sha:SHA('6c7d8e9'),at:'2026-10-12T13:00:00+09:00',late:false},dur:NEUTRAL(-0.2),cur:NEUTRAL(-0.28),
    site:site('2026-10-11',null,'—','3/13'),lp:{month:'2026-08',L:'L0',P:'P+',cell:'금리 상방 관찰 (물가 선행)'},
    outcomes:{'1':both(done('2026-10-09','2026-10-16',-15,-16.3),done('2026-10-09','2026-10-16',-9,-8.8)),
     '4':both(done('2026-10-09','2026-11-06',-38,-43.5),done('2026-10-09','2026-11-06',-9,-8.1))}}),
   week({week:'2026-09-28',end:'2026-10-04',lock:{sha:SHA('9f0e1d2'),at:'2026-10-05T13:00:00+09:00',late:false},dur:NEUTRAL(-0.33),cur:NEUTRAL(0.05),
    site:site('2026-10-04',null,null,'2/12'),lp:{month:'2026-07',L:'?',P:'P+',cell:'판정 보류(노동)'},
    outcomes:{'1':both(done('2026-10-02','2026-10-09',-4,-5.3),done('2026-10-02','2026-10-09',-1,-0.8)),
     '4':both(done('2026-10-02','2026-10-30',-34,-39.5),done('2026-10-02','2026-10-30',-7,-6.1))}})],
  summary:{dur:{ow:hold(),neutral:hold(),uw:hold()},cur:{flat:hold(),neutral:hold(),steep:hold()}},
  sources:[{series:'DGS10',url:'https://fred.stlouisfed.org/series/DGS10',citation:CITES.DGS10,citation_required:false},
   {series:'T10Y2Y',url:'https://fred.stlouisfed.org/series/T10Y2Y',citation:CITES.T10Y2Y,citation_required:true}],
  notices:['1주·4주 변화 · 평균을 뺀 값 · 요약은 macro-regime-check가 계산한 값이다.','Computed by macro-regime-check.']};
}
const HEAD=['주(월~일)','확정 시각 · 고친 칸','듀레이션 판정(Total)','1주 뒤 미 10년','4주 뒤 미 10년','커브 판정(Total)','1주 뒤 10년−2년',
 '4주 뒤 10년−2년','사이트 규칙 · 국면 후보 · 운영자 FLAG','L×P(칸) — 오늘 다시 계산'];
const C={lock:1,dur:2,dur1:3,dur4:4,cur:5,cur1:6,cur4:7,site:8,lp:9};                  // 열 차례
const OUTS=[C.dur1,C.dur4,C.cur1,C.cur4];
const ZERO='확정한 7주 모두 고친 칸이 0입니다 — 운영자 시트가 사람이 고친 점수 칸을 잡지 못했다는 뜻이고, 그 주 마지막 자동 실행 뒤(주말 등)에 고친 점수는 세지 못하므로 초안 그대로라는 보장은 아닙니다';
const pick=(c,idx)=>idx.map(i=>c[i]);
const rowOf=(wrap,weekStart)=>bodyRows(tableOf(wrap,'tl-table')).find(r=>r.attrs.class!=='tl-gap'&&r.kids[0].textContent.startsWith(weekStart));

// ── 전체 그림 ────────────────────────────────────────────────────────────────────────
test('full render: heading, chip, label line, summary sentence and the week table newest first with the gap week',()=>{
 const {api,lp,ok,wrap}=draw(timeline());
 assert.equal(ok,true);
 const h2=tags(wrap,'h2')[0];
 assert.equal(h2.textContent,'판단 연표');
 assert.equal(h2.attrs.id,'timeline-title');                                         // index.html의 aria-labelledby
 assert.equal(cls(wrap,'reference-label')[0].textContent,'판단 연표 약속 1판 · 측정 기록 — 예측 아님');   // 약속 판을 칩에
 assert.equal(cls(wrap,'tl-label')[0].textContent,'운영자 주간 판정(공개 기록에서 옮김) — 투자 판단·권유 아님 · 측정 기록');
 assert.equal(api.LABEL,timeline().label);
 assert.equal(cls(wrap,'tl-sum-line')[0].textContent,'공개 기록 8주 가운데 7주를 확정했고, 가장 최근 2026-11-16 주는 진행 중입니다(확정 전).');
 assert.equal(cls(wrap,'tl-sum-note')[0].textContent,ZERO+' · 약속 전 7주 · 늦게 확정 1주.');
 // 늘 보이는 약속의 요지 — 판 · 기간과 출발 점 · 짝(FRED 링크) · 요약 문턱
 const keys=cls(wrap,'tl-keys')[0];
 assert.deepEqual(tags(keys,'li').map(x=>x.textContent),[
  '판단 연표 약속 1판 · 2026-11-19 고정 — 결과를 보기 전에 정한 방법입니다(약속 문장은 아래 접은 칸).',
  '보는 기간: 1주 · 4주 뒤 — 출발 점은 그 주 안의 마지막 주간 점(보통 금요일 값)이고, 확정이 다음 월요일 22:30 KST(13:30 UTC)보다 늦은 주는 확정한 날(UTC) 이후 7일 안의 첫 주간 점입니다.',
  '짝: 듀레이션 판정 ↔ 미 10년 DGS10 · 커브 판정 ↔ 10년−2년 T10Y2Y (FRED, 주간 점의 bp 변화).',
  "요약: 약속 뒤에 확정한 주를 같은 출발 점은 한 번으로 세어 10개가 모였을 때만 냅니다 — 그 전에는 '판단 보류 (n/10)'."]);
 assert.deepEqual(tags(keys,'a').map(a=>a.attrs.href),['https://fred.stlouisfed.org/series/DGS10','https://fred.stlouisfed.org/series/T10Y2Y']);
 const t=tableOf(wrap,'tl-table');
 // 열 차례: 판정 바로 뒤에 그 판정의 금리 변화(1280px에 맞게 — 고친 칸은 확정 시각 칸에, 운영자 FLAG는 사이트 칸에)
 assert.deepEqual(tags(tags(t,'thead')[0],'th').map(x=>x.textContent),HEAD);
 const heads=bodyRows(t).map(r=>r.kids[0].textContent);
 assert.deepEqual(heads,['2026-11-16 ~ 11-22진행 중','2026-11-09 ~ 11-15약속 전','2026-11-02 ~ 11-08약속 전','2026-10-26 ~ 11-01약속 전',
  '2026-10-19 ~ 10-25','2026-10-12 ~ 10-18약속 전','2026-10-05 ~ 10-11약속 전','2026-09-28 ~ 10-04약속 전','2026-09-21 ~ 09-27약속 전']);
 const gap=bodyRows(t)[4];
 assert.equal(gap.attrs.class,'tl-gap');
 assert.deepEqual(cells(gap),['2026-10-19 ~ 10-25','공개 기록이 없는 주입니다.']);
 assert.equal(gap.kids[1].attrs.colspan,'9');
 for(const r of bodyRows(t))assert.equal(r.kids[0].tag,'th'),assert.equal(r.kids[0].attrs.scope,'row');
 assert.equal(capOf(wrap,t).textContent,'주마다 — 운영자가 처음 확정한 판정과 그 뒤 금리 변화(주간 점, bp), 맥락으로 그 주 끝의 이 사이트 날짜별 기록(그날 실린 그대로)과 '+
  '판단 격자 L × P(오늘의 자료로 다시 계산한 값 — 그때 실린 값이 아님). 새 주가 위입니다.');
 // 판단 격자 칸 이름 곁의 이름표는 lp.js와 같은 글로 한 번
 assert.equal(api.LP_LABEL,lp.LABEL);
 assert.deepEqual(cls(wrap,'tl-lplabel').map(p=>p.textContent),["'L×P(칸)' 열의 칸 이름: "+lp.LABEL]);
 assert.ok(!STRAY.test(wrap.textContent),wrap.textContent);
 assert.ok(!wrap.textContent.includes(timeline().notice));                            // 자료 파일의 notice(한다체)는 되풀이하지 않는다
});

test('a confirmed week row: lock time in KST with the commit link and edited cells, verdict and Total next to its outcomes, site with the operator FLAG, L×P',()=>{
 const {wrap}=draw(timeline());
 const r=rowOf(wrap,'2026-09-21');
 const c=cells(r);
 assert.equal(c[C.lock],'2026-09-28 13:04KST · 커밋 0a1b2c3고친 칸 0');
 const a=tags(r.kids[C.lock],'a')[0];
 assert.equal(a.attrs.href,`https://github.com/${REPO}/commit/${SHA('0a1b2c3')}`);
 assert.equal(c[C.dur],'U/W (-0.90)');
 assert.equal(c[C.cur],'Flattening (+0.88)');
 assert.equal(c[C.site],'기록 없음운영자 FLAG 비어 있음');                           // 그 주 끝까지 공개 기록이 없던 주 · FLAG 칸이 빈 주
 assert.equal(c[C.lp],'—');
 assert.deepEqual(pick(c,OUTS),['+6.2bp평균을 뺀 값 +4.9bp2026-09-25 → 2026-10-02','-2.4bp평균을 뺀 값 -7.8bp2026-09-25 → 2026-10-23',   // 반올림: -2.35 → -2.4(toFixed)
  '-1.0bp평균을 뺀 값 -0.8bp2026-09-25 → 2026-10-02','-4.0bp평균을 뺀 값 -3.1bp2026-09-25 → 2026-10-23']);
 const r2=cells(rowOf(wrap,'2026-11-09'));
 assert.equal(r2[C.lock],'2026-11-16 13:02KST · 커밋 d2728b4고친 칸 0');
 assert.equal(r2[C.dur],'Neutral (+0.10)');
 assert.equal(r2[C.site],'핵심 신호 2/11국면 후보 판정불가운영자 FLAG 비어 있음기록 2026-11-15');
 assert.equal(r2[C.lp],'L+ × P+금리 상방 여지 (확인)기준월 2026-09');
 const r3=cells(rowOf(wrap,'2026-10-05'));
 assert.equal(r3[C.site],'충족 규칙 3/13국면 후보 —운영자 FLAG 비어 있음기록 2026-10-11');   // 핵심 신호가 없던 날은 충족 규칙 수
 assert.equal(r3[C.dur],'Neutral (-0.20)');
 const r4=cells(rowOf(wrap,'2026-09-28'));
 assert.equal(r4[C.lp],'? × P+판정 보류(노동)기준월 2026-07');
 assert.equal(r4[C.site],'충족 규칙 2/12국면 후보 —운영자 FLAG 비어 있음기록 2026-10-04');      // 레짐 점검 절이 없던 날은 —
 // 운영자 FLAG — 정해 둔 넷은 그대로, 정해 둔 값 밖의 글이 있던 주는 빈 칸과 가른다(그 글은 자료에도 없다)
 const d=timeline();
 Object.assign(d.weeks.find(x=>x.week==='2026-11-09'),{regime_flag:'A′'});
 Object.assign(d.weeks.find(x=>x.week==='2026-11-02'),{regime_flag:null,regime_flag_other:true});
 Object.assign(d.weeks.find(x=>x.week==='2026-10-26'),{regime_flag:'A′',regime_flag_other:true});         // 둘 다면 값이 앞선다
 const t=draw(d);
 assert.equal(cells(rowOf(t.wrap,'2026-11-09'))[C.site],'핵심 신호 2/11국면 후보 판정불가운영자 FLAG A′기록 2026-11-15');
 assert.equal(cells(rowOf(t.wrap,'2026-11-02'))[C.site],'핵심 신호 2/11국면 후보 A′운영자 FLAG 정해 둔 값 밖기록 2026-11-08');
 assert.equal(cells(rowOf(t.wrap,'2026-10-26'))[C.site],'핵심 신호 2/11국면 후보 A′운영자 FLAG A′기록 2026-11-01');
});

test('the in-progress week: no lock, its outcomes wait for the confirmation',()=>{
 const {wrap}=draw(timeline());
 const r=rowOf(wrap,'2026-11-16');
 assert.equal(r.attrs.class,'tl-row tl-open');
 const c=cells(r);
 assert.equal(c[C.lock],'확정 전고친 칸 0');
 assert.deepEqual(pick(c,OUTS),['확정 전','확정 전','확정 전','확정 전']);
 assert.equal(c[C.dur],'Neutral (+0.10)');
 // 확정 전 주에 잘못 붙은 확정 커밋 · 확정 뒤 고침 · 지운 커밋은 싣지 않는다
 const d=timeline();
 const w=d.weeks.find(x=>x.week==='2026-11-16');
 w.lock={sha:SHA('abcdef1'),at:'2026-11-23T13:00:00+09:00',late:false};
 w.changed_after={at:'2026-11-24T09:00:00+09:00',sha:SHA('bbbbbbb'),dur:NEUTRAL(0.6),cur:NEUTRAL(0),edited_n:2};
 w.removed={at:'2026-11-25T09:00:00+09:00',sha:SHA('ccccccc')};
 w.outcomes={'1':both(pending(null),pending(null)),'4':both(pending(null),missing(null))};   // 빌더는 확정 전 주에 start 없는 '기다리는 중'을 쓴다
 const t=draw(d);
 assert.equal(cells(rowOf(t.wrap,'2026-11-16'))[C.lock],'확정 전고친 칸 0');
 assert.deepEqual(pick(cells(rowOf(t.wrap,'2026-11-16')),OUTS),['확정 전','확정 전','확정 전','자료 없음']);
 assert.ok(!t.wrap.textContent.includes('확정 뒤 고침 →'));
 assert.ok(!t.wrap.textContent.includes('지운 커밋'));
});

test('late and changed-after marks: a pill each, the new values beside the first-confirmed ones, weeks sharing a start point',()=>{
 const d=timeline();
 const w=d.weeks.find(x=>x.week==='2026-11-02');
 w.changed_after={at:'2026-11-10T21:15:00+09:00',sha:SHA('cafe123'),dur:{total:0.6,verdict:'O/W'},cur:NEUTRAL(0.2),edited_n:2};
 const {wrap}=draw(d);
 const late=rowOf(wrap,'2026-10-12');
 assert.deepEqual(cls(late.kids[C.lock],'ledger-pre').map(p=>p.textContent),['늦게 확정']);
 // 늦게 확정해 뒤 주(10-26)와 출발 점을 나눈 주 — 확정 시각 칸에 같은 출발 점의 주를 적는다(결과가 같고 독립이 아니다)
 assert.equal(cells(late)[C.lock],'2026-10-26 13:05KST · 커밋 5caf129고친 칸 0늦게 확정출발 점 2026-10-30 — 10-26 주와 같음');
 assert.equal(cells(rowOf(wrap,'2026-10-26'))[C.lock],'2026-11-02 13:03KST · 커밋 3b4c5d6고친 칸 0출발 점 2026-10-30 — 10-12 주와 같음');
 const r=rowOf(wrap,'2026-11-02');
 assert.deepEqual(cls(r.kids[C.lock],'ledger-pre').map(p=>p.textContent),['확정 뒤 고침']);
 assert.equal(cells(r)[C.lock],'2026-11-09 13:01KST · 커밋 7e8f9a0고친 칸 0 · 확정 뒤 2확정 뒤 고침고친 커밋 2026-11-10 21:15 · cafe123');
 assert.deepEqual(tags(r.kids[C.lock],'a').map(a=>a.attrs.href),[`https://github.com/${REPO}/commit/${SHA('7e8f9a0')}`,`https://github.com/${REPO}/commit/${SHA('cafe123')}`]);
 assert.equal(cells(r)[C.dur],'Neutral (+0.10)확정 뒤 고침 → O/W (+0.60)');            // 첫 확정본이 앞, 바뀐 값은 작은 글
 assert.equal(cells(r)[C.cur],'Neutral (+0.20)');                                     // 그대로인 쪽은 표시 없음
 assert.equal(cls(wrap,'tl-sum-note')[0].textContent,ZERO+' · 약속 전 7주 · 늦게 확정 1주 · 확정 뒤 고침 1주.');
 // 확정 뒤 고침의 꼴이 어긋나면 그 칸만 뺀다(주는 남는다)
 const d2=timeline();
 d2.weeks.find(x=>x.week==='2026-11-02').changed_after={at:'2026-11-10',sha:'xyz',dur:NEUTRAL(0),cur:NEUTRAL(0),edited_n:-1};
 const t2=draw(d2);
 assert.equal(cells(rowOf(t2.wrap,'2026-11-02'))[C.lock],'2026-11-09 13:01KST · 커밋 7e8f9a0고친 칸 0');
});

test('removed, rewritten history and first upload: the first-confirmed verdict stays, with a mark and the commit as text when it left the history',()=>{
 const d=timeline();
 Object.assign(d.weeks.find(x=>x.week==='2026-11-02'),{removed:{at:'2026-11-20T10:00:00+09:00',sha:SHA('dead001')}});
 Object.assign(d.weeks.find(x=>x.week==='2026-11-09').lock,{in_history:false});
 Object.assign(d.weeks.find(x=>x.week==='2026-09-21').lock,{first_upload:true});
 const {wrap}=draw(d);
 const r=rowOf(wrap,'2026-11-02');
 assert.deepEqual(cls(r.kids[C.lock],'ledger-pre').map(p=>p.textContent),['공개 기록에서 지움']);
 assert.equal(cells(r)[C.lock],'2026-11-09 13:01KST · 커밋 7e8f9a0고친 칸 0공개 기록에서 지움지운 커밋 2026-11-20 10:00 · dead001');
 assert.equal(cells(r)[C.dur],'Neutral (+0.10)');                                     // 판정은 처음 확정한 그대로
 const g=rowOf(wrap,'2026-11-09');
 assert.deepEqual(cls(g.kids[C.lock],'ledger-pre').map(p=>p.textContent),['기록 고쳐 씀']);
 assert.equal(cells(g)[C.lock],'2026-11-16 13:02KST · 커밋 d2728b4고친 칸 0기록 고쳐 씀잠근 커밋이 지금 공개 기록에 없음 — 처음 판정 그대로');
 assert.equal(tags(g.kids[C.lock],'a').length,0);                                     // 기록에 없는 커밋은 링크하지 않는다
 assert.equal(cells(rowOf(wrap,'2026-09-21'))[C.lock],'2026-09-28 13:04KST · 커밋 0a1b2c3고친 칸 0처음 올린 판이 확정본');
 assert.equal(cls(wrap,'tl-sum-note')[0].textContent,ZERO+' · 약속 전 7주 · 늦게 확정 1주 · 공개 기록에서 지움 1주 · 기록 고쳐 씀 1주.');
 // 꼴이 어긋난 지운 커밋은 싣지 않는다(주는 남는다)
 const d2=timeline();
 d2.weeks.find(x=>x.week==='2026-11-02').removed={at:'어제',sha:SHA('dead001')};
 assert.equal(cells(rowOf(draw(d2).wrap,'2026-11-02'))[C.lock],'2026-11-09 13:01KST · 커밋 7e8f9a0고친 칸 0');
});

test('pending and missing outcome cells, a start-less wait, and a broken cell as a dash',()=>{
 const d=timeline();
 const w=d.weeks.find(x=>x.week==='2026-10-26');
 w.outcomes={'1':both(missing('2026-10-30'),{state:'pending',start:null,end:null,change_bp:null,demeaned_bp:null}),
  '4':both({state:'done',start:'2026-10-30',end:'2026-11-27',change_bp:'3',demeaned_bp:1},{state:'weird'})};
 const {wrap}=draw(d);
 // 열 차례: 1주 뒤 미 10년 · 4주 뒤 미 10년 · 1주 뒤 10년−2년 · 4주 뒤 10년−2년. 꼴이 어긋난 결과(문자열 숫자 · 모르는 상태)는 —
 assert.deepEqual(pick(cells(rowOf(wrap,'2026-10-26')),OUTS),['자료 없음','—','기다리는 중','—']);
 const c=pick(cells(rowOf(wrap,'2026-11-09')),OUTS);
 assert.deepEqual(c,Array(2).fill(null).flatMap(()=>['기다리는 중출발 2026-11-13 · 끝 점 2026-11-20±3일','기다리는 중출발 2026-11-13 · 끝 점 2026-12-11±3일']));
 // 칸 밑 작은 글은 접히되 날짜 토막은 한 줄을 지킨다(.tl-nb — 좁은 칸에서 '2026-11-' · '13'처럼 가운데서 접히지 않게)
 assert.deepEqual(cls(rowOf(wrap,'2026-11-09'),'tl-nb').map(x=>x.textContent),
  [...Array(4).fill(null).flatMap((_,i)=>['출발 2026-11-13',`끝 점 ${i%2?'2026-12-11':'2026-11-20'}±3일`]),'2026-11-15','2026-09']);   // 출발 · 끝 점 · 사이트 기록 날짜 · 기준월
 const all=wrap.textContent;
 assert.ok(!STRAY.test(all),all);
});

test('summary by verdict group: hold below n_min, numbers at n_min, a dash for a broken cell',()=>{
 const d=timeline();
 d.summary.dur.ow['1']={n:12,mean_demeaned_bp:-3.46,up_share:0.4166};
 d.summary.cur.steep['4']={n:10,mean_demeaned_bp:0.04,up_share:0.5};
 d.summary.dur.uw['4']={n:11,mean_demeaned_bp:null,up_share:0.5};
 d.summary.cur.neutral['1']={n:3};
 d.summary.cur.flat['1']={n:11,starts:9,mean_demeaned_bp:null,up_share:null};          // 주는 11개여도 출발 점이 9개 — 판단 보류
 d.summary.cur.flat['4']={n:12,starts:10,mean_demeaned_bp:1.25,up_share:0.6};
 d.summary.dur.neutral['4']={n:3,starts:5,mean_demeaned_bp:null,up_share:null};        // 출발 점이 주보다 많으면 꼴이 어긋난 것 — 주 수로
 const {wrap}=draw(d);
 const t=tableOf(wrap,'tl-sum');
 assert.equal(capOf(wrap,t).textContent,'판정 묶음별 요약 — 약속 1판(2026-11-19) 뒤에 확정한 주만, 같은 출발 점을 나눈 주는 한 번으로 세어 출발 점이 10개 모이기 전에는 판단 보류');
 assert.deepEqual(tags(tags(t,'thead')[0],'th').map(x=>x.textContent),['판정 묶음','금리','1주 뒤(평균을 뺀 값)','4주 뒤(평균을 뺀 값)']);
 assert.deepEqual(bodyRows(t).map(cells),[
  ['듀레이션 O/W 쪽O/W · 강한 O/W','미 10년','평균을 뺀 값 -3.5bp오른 비율 42% · 출발 점 12개','판단 보류 (0/10)'],
  ['듀레이션 Neutral','미 10년','판단 보류 (0/10)','판단 보류 (3/10)'],
  ['듀레이션 U/W 쪽U/W · 강한 U/W','미 10년','판단 보류 (0/10)','—'],
  ['커브 Flattening 쪽Flattening · 강한 Flattening','10년−2년','판단 보류 (9/10)출발 점 9개 · 주 11','평균을 뺀 값 +1.3bp오른 비율 60% · 출발 점 10개 · 주 12'],
  ['커브 Neutral','10년−2년','판단 보류 (3/10)','판단 보류 (0/10)'],
  ['커브 Steepening 쪽Steepening · 강한 Steepening','10년−2년','판단 보류 (0/10)','평균을 뺀 값 0.0bp오른 비율 50% · 출발 점 10개']]);
 const t2=draw(Object.assign(timeline(),{summary:null}));                             // 요약이 없으면 칸마다 —
 assert.ok(bodyRows(tableOf(t2.wrap,'tl-sum')).every(r=>cells(r).slice(2).every(x=>x==='—')));
});

test('validators: bad weeks are skipped one by one, duplicates keep the first, the rest still draws',()=>{
 const d=timeline();
 const base=d.weeks.find(x=>x.week==='2026-11-09');
 const bad=[
  Object.assign({},base,{week:'2026-11-10',end:'2026-11-16'}),                       // 월요일이 아님
  Object.assign({},base,{week:'2026-08-03',end:'2026-08-10'}),                       // 끝 날이 6일 뒤가 아님
  Object.assign({},base,{week:'2026-08-10',end:'2026-08-16',state:'done'}),
  Object.assign({},base,{week:'2026-08-17',end:'2026-08-23',dur:{total:0.1,verdict:'Overweight'}}),
  Object.assign({},base,{week:'2026-08-24',end:'2026-08-30',cur:{total:0.1,verdict:'O/W'}}),                     // 커브에 듀레이션 이름표
  Object.assign({},base,{week:'2026-08-31',end:'2026-09-06',dur:{total:'0.1',verdict:'Neutral'}}),
  Object.assign({},base,{week:'2026-09-07',end:'2026-09-13',edited_n:-1}),
  Object.assign({},base,{week:'2026-09-14',end:'2026-09-20',lock:null}),                                         // 확정했는데 커밋이 없음
  Object.assign({},base,{week:'2026-07-06',end:'2026-07-12',lock:{sha:'XYZ',at:'2026-07-13T13:00:00+09:00',late:false}}),
  Object.assign({},base,{week:'2026-07-13',end:'2026-07-19',lock:{sha:SHA('1234567'),at:'2026-07-20 13:00',late:false}}),
  Object.assign({},base,{week:'2026-07-20',end:'2026-07-26',regime_flag:'D'}),
  Object.assign({},base,{week:'2026-07-27',end:'2026-08-02',before_protocol:'yes'}),
  Object.assign({},base,{dur:{total:9,verdict:'강한 O/W'}}),                                                      // 같은 주 둘째 — 첫 것을 쓴다
  null,'x',[]];
 d.weeks.push(...bad);
 const {ok,wrap}=draw(d);
 assert.equal(ok,true);
 const heads=bodyRows(tableOf(wrap,'tl-table')).map(r=>r.kids[0].textContent.slice(0,10));
 assert.deepEqual(heads,['2026-11-16','2026-11-09','2026-11-02','2026-10-26','2026-10-19','2026-10-12','2026-10-05','2026-09-28','2026-09-21']);
 assert.equal(cells(rowOf(wrap,'2026-11-09'))[2],'Neutral (+0.10)');
 // 판정 글 — 정해 둔 것만(강한 · 채점 미완 n/7 포함)
 const d2=timeline();
 const w=d2.weeks.find(x=>x.week==='2026-11-02');
 w.dur={total:null,verdict:'채점 미완 5/7'};w.cur={total:-1.2,verdict:'강한 Steepening'};
 const t2=draw(d2);
 assert.deepEqual(pick(cells(rowOf(t2.wrap,'2026-11-02')),[C.dur,C.cur]),['채점 미완 5/7','강한 Steepening (-1.20)']);
 for(const v of ['채점 미완 7/7','채점 미완 8/7','채점 미완 5/8','강한  O/W','o/w','Neutral ']){
  const d3=timeline();d3.weeks.find(x=>x.week==='2026-11-02').dur={total:0,verdict:v};
  assert.equal(rowOf(draw(d3).wrap,'2026-11-02'),undefined,v);
 }
});

test('L×P: the cell name must match the operator table (lp.js), holds name the unknown side, and without lp.js no names',()=>{
 const d=timeline();
 d.weeks.find(x=>x.week==='2026-11-02').lp={month:'2026-09',L:'L+',P:'P+',cell:'박스'};                // 칸 이름이 그 칸과 다르다
 d.weeks.find(x=>x.week==='2026-10-26').lp={month:'2026-09',L:'L+',P:'?',cell:'판정 보류(노동)'};      // 모르는 쪽이 다르다
 d.weeks.find(x=>x.week==='2026-10-05').lp={month:'2026-09',L:'?',P:'?',cell:'판정 보류(노동·물가)'};
 d.weeks.find(x=>x.week==='2026-11-09').lp={month:'2026-13',L:'L+',P:'P+',cell:'금리 상방 여지 (확인)'};
 const {wrap}=draw(d);
 assert.equal(cells(rowOf(wrap,'2026-11-02'))[C.lp],'—');
 assert.equal(cells(rowOf(wrap,'2026-10-26'))[C.lp],'—');
 assert.equal(cells(rowOf(wrap,'2026-10-05'))[C.lp],'? × ?판정 보류(노동·물가)기준월 2026-09');
 assert.equal(cells(rowOf(wrap,'2026-11-09'))[C.lp],'—');
 // lp.js가 없으면 칸 이름 없이 L × P만, 이름표 줄도 없다
 const t=draw(timeline(),{lp:false});
 assert.equal(t.ok,true);
 assert.equal(cells(rowOf(t.wrap,'2026-11-09'))[C.lp],'L+ × P+기준월 2026-09');
 assert.equal(cells(rowOf(t.wrap,'2026-09-28'))[C.lp],'? × P+판정 보류(노동)기준월 2026-07');           // 판정 보류는 운영자 표가 없어도 꼴로 본다
 assert.equal(cls(t.wrap,'tl-lplabel').length,1);
 const t2=draw(Object.assign(timeline(),{weeks:timeline().weeks.map(w=>Object.assign(w,{lp:null}))}));
 assert.equal(cls(t2.wrap,'tl-lplabel').length,0);                                     // 칸 이름이 하나도 없으면 이름표 줄도 없다
});

test('a bad file draws nothing and leaves the box as it was',()=>{
 const w=f=>{const d=timeline();f(d);return d;};
 const bads=[null,undefined,'x',[],{},Object.assign(timeline(),{schema:2}),Object.assign(timeline(),{weeks:{}}),
  Object.assign(timeline(),{protocol:null}),w(d=>{d.protocol.version=0;}),w(d=>{d.protocol.fixed='2026-11-31';}),
  w(d=>{d.protocol.horizons_weeks=['1',0];}),w(d=>{d.protocol.pairs=[{verdict:'tp',series:'THREEFYTP10',label:'기간 프리미엄'}];}),
  w(d=>{d.protocol.pairs=[{verdict:'dur',series:'dgs10',label:'미 10년'}];}),w(d=>{d.protocol.n_min=0;}),w(d=>{d.protocol.tolerance_days=-1;})];
 for(const d of bads){
  const t=load();
  t.wrap.append('그대로');
  assert.equal(t.api.render(d),false,JSON.stringify(d));
  assert.equal(t.wrap.textContent,'그대로');
 }
 const t=load({drop:['timeline-wrap']});
 assert.equal(t.api.render(timeline()),false);
 // 그리기 중에 깨져도 예외를 내지 않고 false
 const broken=timeline();Object.defineProperty(broken,'summary',{get(){throw new Error('깨짐');}});
 const t2=load();
 assert.equal(t2.api.render(broken),false);
 assert.equal(t2.wrap.kids.length,0);
 // 주 목록이 비면 그 말을 하고 그린다
 const t3=draw(Object.assign(timeline(),{weeks:[]}));
 assert.equal(t3.ok,true);
 assert.equal(cls(t3.wrap,'tl-sum-line')[0].textContent,'아직 옮겨 온 주간 기록이 없습니다.');
 assert.ok(t3.wrap.textContent.includes('옮겨 온 주간 기록이 없습니다.'));
 assert.ok(!STRAY.test(t3.wrap.textContent));
});

test('protocol text and reading notes are folded; data text with banned words is dropped',()=>{
 const d=timeline();
 d.protocol.text.push('다음 주 금리 전망을 적는다.','줄\n바꿈',7,'');
 d.notices.push('이 표를 추천한다.');
 const {wrap}=draw(d);
 const det=tags(wrap,'details');
 assert.deepEqual(det.map(x=>tags(x,'summary')[0].textContent),['약속 문장 3개 — 판단 연표 약속 1판 · 2026-11-19 고정(자료 파일 그대로)','읽는 법']);
 for(const x of det)assert.ok(!('open' in x.attrs));                                   // 닫힌 채
 assert.equal(cls(det[0],'notices')[0].kids.map(k=>k.textContent).join('|'),timeline().protocol.text.join('|'));
 const read=det[1].textContent;
 for(const w of ['O/W(강한 O/W)는 듀레이션 비중 확대 쪽(금리 하락 쪽에 선 판정)','Flattening은 커브 평탄화 쪽','운영자 시트의 이름표',
  "'채점 미완 n/7'",'0은 시트가 사람이 고친 칸을 잡지 못했다는 뜻이지, 확정한 판정이 초안 그대로라는 보장은 아닙니다',
  '그 주 마지막 자동 실행 뒤(주말 등)에 고친 점수는 세지 못합니다','GitHub API로 날짜 없이','검증한 시각이 아니라 적힌 시각',
  '처음 올린 판이 확정본','다음 월요일 22:30 KST(13:30 UTC)보다 늦은 주','뉴욕 주식 현물 시장이 가장 일찍 여는 시각','아시아·런던 시간',
  '확정한 날(UTC) 이후 7일 안의 첫 주간 점','출발 날짜가 같은 줄은 결과가 같고 서로 독립이 아닙니다','요약은 같은 출발 점을 한 번만',
  '공개 기록에서 지움','기록 고쳐 씀','처음 확정한 판정과 시각을 그대로',"'충족 규칙 m/전체 규칙 수'",'두 숫자는 서로 견줄 수 없고',
  "'정해 둔 값 밖'은 A · A′ · B · C가 아닌 글이 있던 주",'오늘의 FRED 자료로 다시 계산한 값','그때 이 사이트에 실린 값을 옮긴 것이 아니고',
  '판단 격자 카드는 2026-11-18부터','확정 뒤 고침','판단 연표 약속(2026-11-19) 앞에','±3일','FRED가 값을 고치거나'])
  assert.ok(read.includes(w),w);
 for(const w of ['운영자 PC의 시계','미국 현물 시장이 여는','초안 점수 그대로라는 뜻'])assert.ok(!read.includes(w),w);   // 고친 풀이
 assert.deepEqual(tags(det[1],'a').map(a=>a.attrs.href),[]);                          // FRED 링크는 늘 보이는 약속 요지에
 assert.ok(!wrap.textContent.includes('추천'));
 assert.ok(!wrap.textContent.includes('전망'));
 // open_utc · start_days가 꼴 밖이면 시각 · 날 수를 짓지 않는다
 const d2=timeline();d2.protocol.open_utc='25:00';d2.protocol.start_days=99;
 const read2=tags(draw(d2).wrap,'details')[1].textContent;
 assert.ok(read2.includes('다음 월요일 정해 둔 시각'));
 assert.ok(read2.includes('확정한 날(UTC) 이후의 첫 주간 점'));
 const d3=timeline();d3.protocol.open_utc='16:00';                                     // 한국 시각이 다음 날로 넘어가면 UTC만
 assert.ok(tags(draw(d3).wrap,'details')[1].textContent.includes('다음 월요일 16:00 UTC보다 늦은 주'));
});

test('basis line, notices and FRED citations (shape-checked), and the source line links only to github.com',()=>{
 const d=timeline();
 d.sources.push({series:'THREEFYTP10',url:'https://fred.stlouisfed.org/series/THREEFYTP10',citation:CITES.DGS10.replace('DGS10','THREEFYTP10'),citation_required:false});
 d.sources.push({series:'DGS10',url:'x',citation:'두 번째',citation_required:false});
 const {wrap}=draw(d);
 assert.equal(cls(wrap,'ledger-basis')[0].textContent,'결과와 평균(기준)은 2026-11-18의 그래프 자료(charts.json 주간 점)로 갱신마다 다시 잽니다. ' +
  '평균(기준, 계산값): 1주 — 미 10년 +1.3bp · 10년−2년 -0.2bp / 4주 — 미 10년 +5.5bp · 10년−2년 -0.9bp(첫 출발 2021-11-19 ~ 마지막 끝 2026-11-13, 쌍 257~260개 — 시리즈·기간마다 다름). ' +
  '그래프의 마지막 점: 미 10년 2026-11-16 · 10년−2년 2026-11-17 — 끝 점을 찾을 날의 ±3일이 이 날을 넘으면 기다리는 중입니다.');
 const cite=cls(wrap,'ledger-cite')[0];
 assert.deepEqual(cite.kids.map(k=>k.textContent),[timeline().notices[0],timeline().notices[1],'권장 인용: '+CITES.DGS10+' '+CITES.T10Y2Y]);   // 짝 밖 시리즈 · 같은 시리즈 둘째는 뺀다
 const src=cls(wrap,'tl-source')[0];
 assert.equal(src.textContent,'옮겨 온 곳: 공개 기록 저장소 yun-macrolab/macro-notes-automation의 records/ · 공개 기록 사이트 https://yun-macrolab.github.io/macro-notes-automation/ · 확인 2026-11-19 07:31 (KST) · 마지막으로 읽은 커밋 1d0b26b');
 assert.deepEqual(tags(src,'a').map(a=>a.attrs.href),[`https://github.com/${REPO}/tree/HEAD/records`,`https://github.com/${REPO}/commit/${SHA('1d0b26b')}`]);
 for(const a of tags(wrap,'a'))assert.match(a.attrs.href,/^https:\/\/(fred\.stlouisfed\.org|github\.com)\//);   // 공개 기록 사이트(github.io)는 글자로만
 // 꼴이 어긋나 쓰지 않은 판이 있으면 그 수를 함께
 const d1=timeline();d1.source.skipped_versions=2;
 assert.ok(cls(draw(d1).wrap,'tl-source')[0].textContent.endsWith(' · 꼴이 어긋나 쓰지 않은 판 2개'));
 // 꼴이 어긋난 저장소 · 사이트 주소는 싣지 않는다
 const d2=timeline();d2.source={repo:'yun-macrolab/../x',path:'records/',site:'http://evil.example/'};
 const t2=draw(d2);
 assert.equal(cls(t2.wrap,'tl-source').length,0);
 assert.ok(!t2.wrap.textContent.includes('evil'));
 assert.equal(cells(rowOf(t2.wrap,'2026-09-21'))[C.lock],'2026-09-28 13:04KST · 커밋 0a1b2c3고친 칸 0');       // 저장소를 모르면 커밋은 글자로
 assert.equal(tags(rowOf(t2.wrap,'2026-09-21').kids[C.lock],'a').length,0);
 const d3=timeline();d3.charts={};
 assert.equal(cls(draw(d3).wrap,'ledger-basis')[0].textContent,'그래프 자료가 없어 결과를 적지 못했습니다.');
});

test('no stray words, no banned words beyond the operator verdict labels, signs and rounding',()=>{
 const d=timeline();
 const w=d.weeks.find(x=>x.week==='2026-10-05');
 w.dur={total:-0.004,verdict:'Neutral'};
 w.outcomes['1'].dur=done('2026-10-09','2026-10-16',-0.04,0.05);
 const {wrap}=draw(d);
 const all=wrap.textContent;
 assert.ok(!STRAY.test(all),all);
 for(const b of BANNED){assert.ok(!all.includes(b),b);}
 const code=SRC.split('\n').filter(l=>!l.includes('const BANNED_WORDS')).join('\n');
 for(const b of BANNED)assert.ok(!code.includes(b),b);                                // 스크립트의 글에도(거르는 목록 한 줄 밖)
 const c=cells(rowOf(wrap,'2026-10-05'));
 assert.equal(c[C.dur],'Neutral (0.00)');                                              // 0으로 반올림되면 부호 없이
 assert.equal(c[C.dur1],'0.0bp평균을 뺀 값 +0.1bp2026-10-09 → 2026-10-16');
 for(const x of ['예측 아님','측정 기록'])assert.ok(all.includes(x),x);
});

test('the card script stays text-only and leans on index.html helpers only',()=>{
 const code=SRC.replace(/\/\*[\s\S]*?\*\//g,'').replace(/\/\/[^\n]*/g,'');
 for(const w of ['innerHTML','outerHTML','insertAdjacentHTML','createElement','fetch(','localStorage','location.','eval(','new Function','style'])
  assert.ok(!code.includes(w),w);
 assert.ok(/window\.TimelineView = \(\(\) => \{/.test(SRC));
 assert.ok(PAGE.indexOf('<script src="timeline.js"></script>')>PAGE.indexOf('<script src="lp.js"></script>'));
});

// ── index.html 연결 ──────────────────────────────────────────────────────────────────
function braceBlock(text,start){
 let i=text.indexOf('{',start),depth=0;
 for(;i<text.length;i++){depth+=(text[i]==='{')-(text[i]==='}');if(depth===0)return text.slice(start,i+1);}
 throw new Error('짝이 맞지 않음');
}
test('applyView opens the timeline only on #ledger, and only when it was drawn',()=>{
 const groups=PAGE.slice(PAGE.indexOf('const GROUPS = ['),PAGE.indexOf('];',PAGE.indexOf('const GROUPS = ['))+2);
 const apply=braceBlock(PAGE,PAGE.indexOf('function applyView() {'));
 const avail=PAGE.match(/const available = \{[^}]*\};/);
 assert.ok(avail&&avail[0].includes('timeline: false'),'available에 timeline이 없다');
 const nodes={};
 const node=id=>nodes[id]||(nodes[id]={id,hidden:false,textContent:'',dataset:{},setAttribute(){},removeAttribute(){}});
 const sc={location:{hash:''},window:{},document:{getElementById:node,querySelectorAll:()=>[],querySelector:()=>null}};
 const api=vm.runInNewContext('let activeView = "all", ruleState = "all", publicData = null;\n'+avail[0]+'\n'+groups+'\n'+apply+
  '\n({applyView, set: o => Object.assign(available, o)})',sc);
 const seen=(hash,avail)=>{api.set(Object.assign({loaded:true,ledger:true,timeline:false},avail));sc.location.hash=hash;api.applyView();
  return {tl:!nodes['timeline-wrap'].hidden,ledger:!nodes['ledger-wrap'].hidden,empty:!nodes['ledger-empty'].hidden,
   tlEmpty:!nodes['timeline-empty'].hidden};};
 assert.deepEqual(seen('#ledger',{timeline:true}),{tl:true,ledger:true,empty:false,tlEmpty:false});
 assert.deepEqual(seen('#ledger',{timeline:true,ledger:false}),{tl:true,ledger:false,empty:true,tlEmpty:false});   // 장부가 없어도 연표는 따로
 assert.deepEqual(seen('#ledger',{timeline:false}),{tl:false,ledger:true,empty:false,tlEmpty:true});    // 연표를 못 그리면 그 빈 줄
 assert.deepEqual(seen('#ledger',{timeline:false,loaded:false}),{tl:false,ledger:true,empty:false,tlEmpty:false});   // 읽는 중에는 빈 줄도 없다
 for(const h of ['','#all','#rates','#ai','#sources','#evening']){const v=seen(h,{timeline:true});assert.equal(v.tl,false,h);
  assert.equal(seen(h,{timeline:false}).tlEmpty,false,h);}
 seen('#ledger',{timeline:true});
 assert.ok(nodes['view-description'].textContent.includes('판단 연표'));                       // 화면 설명이 연표를 말한다
 assert.ok(nodes['view-description'].textContent.includes('예측이 아니고'));
 assert.equal(nodes['view-title'].textContent,'기록 장부 · 평가 약속');
});
test('the page wiring: script, section after the ledger, data file in the footer, render in its own try after the L×P card',()=>{
 const sec='<section id="timeline-wrap" hidden aria-labelledby="timeline-title"></section>';
 assert.ok(PAGE.includes(sec));
 assert.ok(PAGE.indexOf('<p id="ledger-empty"')<PAGE.indexOf(sec));
 assert.ok(PAGE.indexOf(sec)<PAGE.indexOf('<section id="lp-ref"'));
 assert.ok(PAGE.includes('getJson("data/timeline.json")'));
 const footer=PAGE.slice(PAGE.indexOf('<footer>'),PAGE.indexOf('</footer>'));
 assert.ok(footer.includes('<a href="data/timeline.json">timeline.json</a>(판단 연표)'));
 const line=PAGE.split('\n').find(l=>l.includes('window.TimelineView.render('));
 assert.match(line,/^\s*try \{ if \(isObj\(tl\) && window\.TimelineView\) available\.timeline = window\.TimelineView\.render\(tl\.value\) === true; \}$/);
 assert.ok(PAGE.indexOf('window.LpCard.render(')<PAGE.indexOf('window.TimelineView.render('));
 assert.ok(PAGE.includes('<a href="#ledger" data-view="ledger">기록 장부<span>평가 약속 · 연표</span></a>'));
 // 연표를 못 그린 날의 빈 줄은 절 바로 뒤
 const empty='<p id="timeline-empty" class="empty-state" hidden>';
 assert.ok(PAGE.indexOf(sec)<PAGE.indexOf(empty)&&PAGE.indexOf(empty)<PAGE.indexOf('<section id="lp-ref"'));
});

test("the command words '연표' · '판단 연표' open the ledger view and then move to the timeline heading (or its empty line)",()=>{
 const go=braceBlock(PAGE,PAGE.indexOf('function go(text) {'));
 const views=PAGE.slice(PAGE.indexOf('const VIEWS = ['),PAGE.indexOf('];',PAGE.indexOf('const VIEWS = ['))+2);
 const sc={location:{hash:''}};
 const api=vm.runInNewContext(views+'\nlet jumpTo = null;\n'+go+'\n({go, jump: () => jumpTo})',sc);
 for(const q of ['연표','판단 연표',' 판단 연표 ']){sc.location.hash='';assert.equal(api.go(q),true,q);assert.equal(sc.location.hash,'ledger',q);
  assert.deepEqual(Array.from(api.jump()),['timeline-title','timeline-empty'],q);}
 for(const q of ['기록 장부','장부','금리']){api.go(q);assert.equal(api.jump(),null,q);}                 // 다른 낱말은 화면 제목으로
 // 제출 뒤의 초점 옮기기 — 보이는 첫 대상(연표 제목, 없으면 빈 줄)으로 내려가 초점, 그다음은 지운다
 const sub=PAGE.slice(PAGE.indexOf('document.getElementById("cmd-form").addEventListener("submit"'));
 const body=sub.slice(0,sub.indexOf('\n});')+4);
 assert.ok(body.includes('const jump = (jumpTo || []).map(id => document.getElementById(id)).find(h => h && h.offsetParent);'));
 assert.ok(body.includes('jumpTo = null;'));
 assert.ok(/jump\.scrollIntoView\(\{ block: "start" \}\);\s*jump\.focus\(\{ preventScroll: true \}\);/.test(body));
});
