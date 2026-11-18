// 판단 격자 L × P(site/lp.js) — 아주 작은 가짜 DOM 위에서 render()를 돌려 글을 본다. 자료는 scripts/lp_fetch.py가 쓰는 꼴
// (data/lp.json)을 손으로 지은 것이고 숫자 · 상태는 지어낸 것이다. 맨 끝 둘은 index.html의 applyView 가운데 이 절에 닿는 부분을
// 잘라 돌리고(첫 화면에서만 열리는지), 스크립트가 글자로만 그리는지 본다.
// 실행: node --test scripts/test_lp_render.cjs
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const SRC=fs.readFileSync(path.join(__dirname,'../site/lp.js'),'utf8');
const PAGE=fs.readFileSync(path.join(__dirname,'../site/index.html'),'utf8');
const STRAY=/undefined|NaN|null|\[object/;
const BANNED=['매수','매도','유망','적중','전망','예상','추천'];
const NOW=Date.parse('2026-11-18T03:00:00Z');

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
const plain=o=>JSON.parse(JSON.stringify(o));

function load(opts={}){
 const ids={'lp-ref':new El('section')};
 for(const id of opts.drop||[])delete ids[id];
 const el=(tag,attrs,...kids)=>{const n=new El(tag);for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,v);for(const c of kids)if(c!==null&&c!==undefined)n.append(c);return n;};
 const link=(text,url)=>/^https:\/\/(fred\.stlouisfed\.org|github\.com)\//.test(url)?el('a',{href:url},text):text;   // index.html의 link()와 같은 꼴
 const sc={window:{},document:{getElementById:id=>ids[id]||null},el,link};
 vm.runInNewContext(SRC,sc);
 return {api:sc.window.LpCard,ids,wrap:ids['lp-ref']};
}
const draw=(d,now=NOW)=>{const t=load();const ok=t.api.render(d,now);return Object.assign(t,{ok});};
const capOf=(root,table)=>cls(root,'lp-cap').find(p=>p.attrs.id===table.attrs['aria-labelledby']);   // 표의 이름이 된 설명 줄
const tableOf=(root,c)=>cls(root,c).find(n=>n.tag==='table');
const rowsOf=t=>tags(tags(t,'tbody')[0],'tr').map(r=>r.kids.map(k=>k.textContent));

// ── 지은 자료 ─────────────────────────────────────────────────────────────────────────
const LS=['L+','L0','L−','L−−'],PS=['P+','P0','Pd','P−'];
const NAMES={'L+|P+':['금리 상방 여지 (확인)','up'],'L+|P0':['금리 상방 관찰 (노동 선행)','up'],'L+|Pd':['박스 (상단 시험)','box'],
 'L+|P−':['박스 (실질 성장형·골디락스)','box'],'L0|P+':['금리 상방 관찰 (물가 선행)','up'],'L0|P0':['박스','box'],
 'L0|Pd':['박스 (하단 시험)','box'],'L0|P−':['금리 하방 여지 (디스인플레이션형, 2023 하반기형)','down'],
 'L−|P+':['상충: 박스·스티프닝 경계 (스태그 초기)','mixed'],'L−|P0':['금리 하방 경계','down'],'L−|Pd':['금리 하방 경계 (되돌림 쪽)','down'],
 'L−|P−':['되돌림 위험 (2024 하반기형)','down'],'L−−|P+':['되돌림 제한 (스태그형·불 스티프닝)','mixed'],'L−−|P0':['큰 되돌림 위험','down'],
 'L−−|Pd':['큰 되돌림 위험','down'],'L−−|P−':['큰 되돌림 위험 (경기침체형)','down']};
const PG={'H|A':'P+','H|F':'P+','H|D':'Pd','M|A':'P+','M|F':'P0','M|D':'P−','Lo|A':'P0','Lo|F':'P−','Lo|D':'P−'};
const cellOf=(L,P)=>{const lk=LS.includes(L),pk=PS.includes(P);if(lk&&pk)return NAMES[L+'|'+P];
 return ['판정 보류('+[lk?null:'노동',pk?null:'물가'].filter(Boolean).join('·')+')','hold'];};
const mshift=(m,k)=>{const y=+m.slice(0,4),i=+m.slice(5,7)-1+k;return `${y+Math.floor(i/12)}`.padStart(4,'0')+'-'+String((i%12+12)%12+1).padStart(2,'0');};
const CONST={sahm_on:0.5,sahm_watch:0.4,hi_gap:-0.3,d6u:-0.2,claims_ratio:1.25,claims_weeks:4,epop_up:0.2,epop_dn:-0.3,vu_up:0.1,vu_dn:-0.15,
 quits_up:0.1,h_in:3.1,h_out:2.9,lo_in:2.6,lo_out:2.7,mom:0.5,mom_n:1,mom_dn:0.3,mom_dn_n:2};
const SERIES=['UNRATE','LNS12300060','UNEMPLOY','LNS13026638','USPRIV','ICSA','CCSA','JTSJOL','JTSQUR','PCEPILFE','CPIAUCSL','CPILFESL','CUSR0000SACL1E'];
const CITE=sid=>`지어낸 기관, 지어낸 제목 [${sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/${sid}, November 18, 2026.`;
// 달마다 [L, 그 달 조건, 띠, 모멘텀, 꼬리표]. 띠 · 모멘텀이 없으면 P는 '?'
function plan(m){
 if(m<='2022-12')return m>='2022-03'&&m<='2022-04'?['L+','L+','H','A',[]]:['L0','L0','H',m<='2022-03'?'A':'F',[]];
 if(m<='2023-06')return ['L0','L0','H','F',+m.slice(5)<=6?['계절성(1~6월)']:[]];
 if(m<='2023-12')return ['L0',m==='2023-08'?'L−':'L0','H','D',[]];
 if(m==='2024-01')return ['L0','L0','H','D',['계절성(1~6월)']];
 if(m<='2024-03')return ['L0','L0','H','F',['계절성(1~6월)']];
 if(m<='2024-07')return ['L0','L0','M','F',[]];
 if(m<='2024-09')return ['L−','L−','M','D',['상당 부분 반영']];                  // 이 사이트가 싣지 않는 꼬리표 — 화면에서 빠진다
 if(m<='2024-11')return ['L−','L0','M','F',[]];
 if(m==='2024-12')return ['L0','L0','M','F',['고점 통과 — 되돌림 소진 가능']];
 if(m<='2025-12')return ['L0','L0','M','F',m>='2025-09'?['발표 지연(셧다운 — 알려진 날은 근사·확인 필요)']:[]];
 if(m<='2026-04')return ['L0','L0','M','A',['계절성(1~6월)']];
 if(m<='2026-07')return ['L0','L0','H','F',['TP 주도','폭 좁음(트림 ≤ 3)','공급형(에너지)']];
 if(m==='2026-08')return ['L0','L−','H','F',['밸류 갈림(명목 0.4 · 실질 0.6) — 물가 지속성에 달림']];
 if(m==='2026-09')return ['L−','L−','M','F',['에너지 하락']];
 return ['L−','L−',null,null,[]];                                                  // 2026-10 — 물가 아직 없음
}
function row(m){
 const [L,raw,band,mom,t]=plan(m),P=band&&mom?PG[band+'|'+mom]:'?',[cell,kind]=cellOf(L,P);
 return {month:m,known:mshift(m,1)+'-28',L,L_raw:raw,P,band,mom_class:mom,cell,kind,tags:t.slice()};
}
function history(){const out=[];for(let m='2022-01';m<='2026-10';m=mshift(m,1))out.push(row(m));return out;}
// 사례 — scripts/lp_fetch.py가 쓰는 꼴(기대 글은 상태 이름으로만 · 기대한 상태 목록 · 대조하지 않는 꼬리표)
const CASES=[['2022','2022-01','2022-12',['L0','L+'],['P+'],'노동 L0 또는 L+ · 물가 P+',null],
 ['2023 하반기','2023-07','2023-12',['L0'],['Pd','P−'],'노동 L0 · 물가 Pd 또는 P−',null],
 ['2024 1분기','2024-01','2024-03',['L0'],['P+','P0'],'노동 L0 · 물가 P+ 또는 P0',null],
 ['2024-08~09','2024-08','2024-09',['L−'],['P−'],'노동 L− · 물가 P−','상당 부분 반영'],
 ['2024-12~2025-01','2024-12','2025-01',['L0'],null,'노동 L0 · 물가 (정하지 않음)',null],
 ['2026-05 이후','2026-05',null,null,['P+','Pd'],'노동 (정하지 않음) · 물가 P+ 또는 Pd','TP 주도']];
function expected(h){
 return CASES.map(([c,from,to,L,P,want,tag])=>{
  const items=h.filter(r=>r.month>=from&&(to===null||r.month<=to)).map(r=>({month:r.month,L:r.L,P:r.P,cell:r.cell,
   match:(L===null||L.includes(r.L))&&(P===null||P.includes(r.P))}));
  return {case:c,want,from,to,holdout:from>='2024-01',n:items.length,matched:items.filter(i=>i.match).length,want_L:L,want_P:P,
   tag_unchecked:tag,items};
 });
}
const LEG_NAMES=['Sahm형 ≥ 0.50','Sahm형 ≥ 0.40','u3 상승(3개월 전보다)','청구 다리(1.25 × 4주 + CCSA 상승)','해고 몫(표시만)',
 '핵심연령 고용률 3개월 Δ6 ≤ −0.3','V/U 3개월 Δ6 ≤ −0.15','민간고용 3개월 평균 ≤ 0(천 명)','고점 대비 하락(U2: hi_gap ≤ −0.30 · Δ6 ≤ −0.20)',
 '회복 확인(고용률 ≥ +0.2)','회복 확인(V/U Δ6 ≥ +0.10)','근원 PCE Y3 띠','근원 PCE 모멘텀(a6 − y12)'];
// 문턱 바로 옆 값 — 두 자리로 반올림하면 문턱과 같아져 반대쪽처럼 보이는 것들. 같은 값을 쓰는 다리(Sahm형 둘 · 고용률 둘 · V/U 둘)는 같은 값
function legs(){
 const v=[[0.4996,false],[0.4996,true],[true,true],[1.2496,false],[0.4996,'모호'],[-0.2996,false],[-0.15,true],[0.4,false],[-0.31,false],
  [-0.2996,false],[-0.15,false],[3.0996,'M'],[0.4996,'F']];
 return LEG_NAMES.map((name,i)=>({name,value:v[i][0],month:i===3?'2026-10':i===6||i===10?'2026-08':'2026-09',on:v[i][1]}));
}
function lp(){
 const h=history(),cur=h.find(r=>r.month==='2026-09'),last=h[h.length-1];
 return {schema:1,generated_at:'2026-11-18T01:23:45Z',asof:'2026-11-18',
  notice:'운영자 판단 격자를 FRED 현재 개정치로 다시 계산한 것이다. 예측이 아니다.',
  label:'운영자 판단 격자의 칸 이름(운영자 메모) — 예측 아님 · 예측력 검증 안 됨',fixed:'2026-10-14',holdout_from:'2024-01',
  constants:Object.assign({},CONST),
  grid:{L:LS.slice(),P:PS.slice(),cells:LS.map(L=>PS.map(P=>({L,P,name:NAMES[L+'|'+P][0],kind:NAMES[L+'|'+P][1]})))},
  defs:{L:[{state:'L−−',text:'비선형 악화 — Sahm형 0.50 이상 · 실업률 상승 · 청구 다리'},{state:'L−',text:'냉각 — Sahm형 0.40 이상이고 상승 중 등'},
    {state:'L0',text:'그 밖'},{state:'L+',text:'회복 전환 — 고점 대비 하락과 확인'}],
   P:[{state:'P+',text:'높거나 가속'},{state:'P0',text:'중간 · 평탄'},{state:'Pd',text:'높지만 둔화'},{state:'P−',text:'중간 · 둔화 또는 낮음'}],
   band:[{band:'H',text:'Y3 3.1 초과로 들어가 2.9 미만에서 나온다'},{band:'M',text:'그 사이'},{band:'Lo',text:'2.6 미만으로 들어가 2.7 초과에서 나온다'}],
   mom:[{mom:'A',text:'a6 − y12 ≥ +0.5가 한 발표'},{mom:'F',text:'그 밖'},{mom:'D',text:'a6 − y12 ≤ −0.3이 두 발표 연속'}],
   pgrid:Object.entries(PG).map(([k,P])=>({band:k.split('|')[0],mom:k.split('|')[1],P}))},
  current:Object.assign({},cur,{legs:legs(),inflation:{y12:2.84,a3:3.02,a6:3.3396,mom:0.4996,Y3:3.0996,Y3_n:3}}),
  latest:{month:last.month,L:last.L,P:last.P,cell:last.cell,kind:last.kind,tags:[]},
  history:h,expected:expected(h),excluded_tags:['상당 부분 반영','TP 주도','폭 좁음(트림 ≤ 3)'],
  series:SERIES.map(s=>({series:s,title:'지어낸 제목 '+s,last:'2026-10-01',fetched:s==='JTSQUR'?'cache':s==='CCSA'?'missing':'net'})),
  sources:SERIES.map(s=>({series:s,url:'https://fred.stlouisfed.org/series/'+s,citation:CITE(s),citation_required:false})),
  notices:['L · P 상태와 칸은 macro-regime-check가 계산한 값이다.','States and cells are computed by macro-regime-check.']};
}
const HEAD='기준월 2026-09 (발표일 근사 2026-10-28) · 노동 L− · 물가 P0 (띠 M 중간 · 모멘텀 F 평탄) → 금리 하방 경계 · 금리 하방·되돌림 쪽 칸';

// ── 그리기 ────────────────────────────────────────────────────────────────────────────
test('full render: heading, label, summary, latest line, tags',()=>{
 const {api,ok,wrap}=draw(lp());
 assert.equal(ok,true);
 const h3=tags(wrap,'h3')[0];
 assert.equal(h3.textContent,'판단 격자 L × P');
 assert.equal(h3.attrs.id,'lp-ref-title');                                         // index.html의 aria-labelledby
 assert.equal(cls(wrap,'reference-label')[0].textContent,'참고 — 예측 아님');
 const panel=cls(wrap,'lp')[0];
 assert.equal(panel.kids[0].textContent,api.LABEL);                                 // 칸 이름보다 먼저 이름표
 assert.equal(api.LABEL,'운영자 판단 격자의 칸 이름(운영자 메모) — 예측 아님 · 예측력 검증 안 됨');
 assert.equal(cls(wrap,'lp-asof')[0].textContent,'2026-11-18 계산 · 문턱 2026-10-14 고정');
 assert.equal(cls(wrap,'lp-now')[0].textContent,HEAD);
 assert.equal(cls(wrap,'lp-kind')[0].textContent,' · 금리 하방·되돌림 쪽 칸');             // 색만이 아니라 말로
 assert.equal(cls(wrap,'lp-latest')[0].textContent,'2026-10: 노동 L− — 물가 아직 발표 전이라 판정 보류');
 assert.equal(cls(wrap,'lp-tags')[0].textContent,'꼬리표: 에너지 하락');
 const text=wrap.textContent;
 assert.ok(!STRAY.test(text),text);
 assert.ok(!text.includes(lp().notice));                                             // 자료 파일의 notice(한다체)는 되풀이하지 않는다
 for(const t of api.ABOUT.split(/(?<=\.)\s+/).filter(Boolean))assert.ok(/니다\.$/.test(t),t);   // 내 글은 합니다체
});

test('grid: 16 named cells in operator order, the current cell marked by aria-current and a visible word',()=>{
 const {api,wrap}=draw(lp());
 const t=tableOf(wrap,'lp-grid');
 const cap=capOf(wrap,t);
 assert.ok(cap&&cap.textContent.includes(api.LABEL),'격자의 이름(설명 줄)에 이름표');
 const head=tags(tags(t,'thead')[0],'th').map(x=>x.textContent);
 assert.deepEqual(head,['L \\ P','P+높음 또는 가속','P0중간 · 평탄','Pd높지만 둔화','P−둔화 또는 낮음']);   // 짧은 정의는 이 파일의 것
 const rows=tags(tags(t,'tbody')[0],'tr');
 assert.deepEqual(rows.map(r=>r.kids[0].textContent),['L+회복 전환','L0그 밖','L−냉각','L−−비선형 악화']);   // 긴 정의(자료 파일)는 '읽는 법'에
 assert.deepEqual(rows.map(r=>r.kids[0].attrs.scope),['row','row','row','row']);
 const here=walk(t,n=>n.attrs['aria-current']==='true');
 assert.equal(here.length,1);
 assert.equal(here[0].tag,'td');
 assert.equal(here[0].textContent,'지금금리 하방 경계');
 assert.equal(cls(here[0],'lp-here')[0].textContent,'지금');
 rows.forEach((r,i)=>r.kids.slice(1).forEach((td,j)=>{
  const [name,kind]=NAMES[LS[i]+'|'+PS[j]];
  assert.ok(td.textContent.endsWith(name),name);
  assert.ok(td.attrs.class.split(' ').includes('lp-k-'+kind),name);
 }));
 assert.deepEqual(plain(api.CELLS),NAMES);
 // 지금 칸이 없으면 표시도 없다
 const d=lp();d.current=null;
 const b=draw(d);
 assert.equal(b.ok,true);
 assert.equal(walk(tableOf(b.wrap,'lp-grid'),n=>n.attrs['aria-current']).length,0);
 assert.equal(cls(b.wrap,'lp-now')[0].textContent,'판정할 수 있는 달이 아직 없습니다.');
 assert.equal(cls(b.wrap,'lp-latest')[0].textContent,'2026-10: 노동 L− — 물가 아직 발표 전이라 판정 보류');   // 지금 칸이 없어도 가장 새 달은 보인다
 assert.equal(cls(b.wrap,'lp-legs').length,0);
});

test('legs: values next to a threshold get enough digits to stay on their side',()=>{
 const {wrap}=draw(lp());
 const t=tableOf(wrap,'lp-legs');
 assert.ok(capOf(wrap,t).textContent.startsWith('2026-09 다리 — ● 충족 · ○ 미충족 · ? 자료 없음.'));
 assert.deepEqual(rowsOf(t).map(r=>r.slice(1)),[
  ['0.4996%p','2026-09','○'],                    // 0.50으로 보이면 Sahm형 ≥ 0.50을 채운 것처럼 읽힌다
  ['0.4996%p','2026-09','●'],                    // 같은 값은 0.40 줄에서도 같게
  ['예','2026-09','●'],
  ['1.2496배','2026-10','○'],
  ['0.4996','2026-09','모호'],                   // 해고형 0.5 경계
  ['-0.2996%p','2026-09','○'],
  ['-0.15','2026-08','●'],                       // 문턱과 똑같은 값은 그대로
  ['+0.4','2026-09','○'],                        // 0으로 보이면 '≤ 0'을 채운 것처럼 읽힌다
  ['-0.31%p','2026-09','○'],
  ['-0.2996%p','2026-09','○'],
  ['-0.15','2026-08','○'],
  ['3.0996%','2026-09','M 중간'],                 // H 진입 3.1 옆
  ['+0.4996%p','2026-09','F 평탄']]);             // 가속 +0.5 옆
 assert.deepEqual(rowsOf(t).map(r=>r[0]),LEG_NAMES);
 assert.deepEqual(tags(rowsOf(t).length?tags(t,'tbody')[0]:t,'th').map(x=>x.attrs.scope),Array(13).fill('row'));
});

test('legs: near() picks the fewest digits that keep every threshold on the same side',()=>{
 const {api}=load();
 assert.equal(api.near(0.5,2,[0.5]),'0.50');
 assert.equal(api.near(0.49996,2,[0.5]),'0.49996');
 assert.equal(api.near(0.506,2,[0.5]),'0.51');
 assert.equal(api.near(0.5004,2,[0.5]),'0.5004');
 assert.equal(api.near(2.8996,2,[3.1,2.9,2.6,2.7]),'2.8996');
 assert.equal(api.near(2.65,1,[2.6,2.7]),'2.65');                // 띠 사이 값 — 2.6으로 보이면 Lo 진입 문턱과 같아진다
 assert.equal(api.near(-0.3,2,[-0.3],true),'-0.30');
 assert.equal(api.near(0.004,0,[0],true),'+0.004');
 assert.equal(api.near(-0.004,2,[0.1],true),'0.00');
 assert.equal(api.near(12.4,0,[0],true),'+12');
});

test('inflation line and its digits near the band and momentum edges',()=>{
 const {wrap}=draw(lp());
 assert.equal(cls(wrap,'lp-infl')[0].textContent,
  '근원 PCE(2026-09): 전년비 y12 2.84% · 전년비 3개월 평균 Y3 3.0996% · 6개월 연율 a6 3.34% · 모멘텀(a6 − y12) +0.4996%p');
 const d=lp();Object.assign(d.current.inflation,{Y3:2.95,Y3_n:2,a6:null,mom:-0.31});
 assert.equal(cls(draw(d).wrap,'lp-infl')[0].textContent,
  '근원 PCE(2026-09): 전년비 y12 2.84% · 전년비 3개월 평균 Y3 2.95%(2개월 평균) · 6개월 연율 a6 — · 모멘텀(a6 − y12) -0.31%p');
 const e=lp();e.current.inflation={y12:null,a3:null,a6:null,mom:null,Y3:null,Y3_n:null};
 assert.equal(cls(draw(e).wrap,'lp-infl').length,0);                               // 숫자가 하나도 없으면 줄이 없다
 const f=lp();f.current.inflation={y12:'2.8'};
 assert.equal(cls(draw(f).wrap,'lp-infl').length,0);
});

test('history: closed details from 2022-01, raw L when different, hold row, one hold-out marker, excluded tags dropped',()=>{
 const {api,wrap}=draw(lp());
 const det=cls(wrap,'lp-more').find(d=>tags(d,'summary')[0].textContent.startsWith('2022년부터 달마다'));
 assert.ok(det&&!('open' in det.attrs));
 assert.equal(tags(det,'summary')[0].textContent,'2022년부터 달마다 — 58달(2022-01 ~ 2026-10)');
 const t=tableOf(det,'lp-hist');
 assert.ok(capOf(det,t).textContent.includes(api.LABEL));
 const rows=rowsOf(t);
 assert.equal(rows.length,58);
 assert.deepEqual(rows[0],['2022-01','L0','P+H · A','금리 상방 관찰 (물가 선행)','—']);
 assert.deepEqual(rows.find(r=>r[0]==='2023-08'),['2023-08','L0그 달 조건 L−','PdH · D','박스 (하단 시험)','—']);
 assert.deepEqual(rows.find(r=>r[0].startsWith('2024-01')),['2024-01여기부터 '+api.HOLDOUT_MARK,'L0','PdH · D','박스 (하단 시험)','계절성(1~6월)']);
 assert.equal(rows.filter(r=>r[0].includes(api.HOLDOUT_MARK)).length,1);
 assert.deepEqual(rows.find(r=>r[0]==='2024-08'),['2024-08','L−','P−M · D','되돌림 위험 (2024 하반기형)','—']);   // '상당 부분 반영'은 빠진다
 assert.deepEqual(rows.find(r=>r[0]==='2024-12').slice(3),['박스','고점 통과 — 되돌림 소진 가능']);
 assert.deepEqual(rows.find(r=>r[0]==='2026-06').slice(4),['공급형(에너지)']);        // TP 주도 · 폭 좁음은 빠진다
 assert.deepEqual(rows.find(r=>r[0]==='2026-08').slice(1),['L0그 달 조건 L−','P+H · F','금리 상방 관찰 (물가 선행)','—']);   // 밸류 꼬리표도 빠진다
 assert.deepEqual(rows[rows.length-1],['2026-10','L−','?','판정 보류(물가)','—']);
 const tr=tags(tags(t,'tbody')[0],'tr');
 assert.ok(tr[tr.length-1].attrs.class.includes('lp-k-hold'));
 for(const w of api.EXCLUDED)assert.ok(!t.textContent.includes(w),w);
 assert.ok(!t.textContent.includes('밸류'));
});

test('expected cases: closed details under the label, hold-out chip from 2024-01, L · P match only, tag checks said to be not computed',()=>{
 const {api,wrap}=draw(lp());
 const det=cls(wrap,'lp-more').find(d=>tags(d,'summary')[0].textContent.startsWith('미리 적어 둔 기대와 대조'));
 assert.ok(det&&!('open' in det.attrs));
 assert.equal(tags(det,'summary')[0].textContent,'미리 적어 둔 기대와 대조 — 사례 6개');
 assert.equal(cls(det,'lp-label')[0].textContent,api.LABEL);
 const note=det.kids[2].textContent;
 assert.ok(note.includes('꼬리표 점검(상당 부분 반영 · TP 주도)은 이 사이트가 계산하지 않습니다'),note);
 assert.ok(note.includes('2024-01부터의 사례는 '+api.HOLDOUT_MARK+'입니다'),note);
 const cases=cls(det,'lp-case');
 assert.deepEqual(cases.map(c=>c.kids[0].textContent),['2022 2022-01 ~ 2022-12','2023 하반기 2023-07 ~ 2023-12',
  '2024 1분기 2024-01 ~ 2024-03'+api.HOLDOUT_MARK,'2024-08~09 2024-08 ~ 2024-09'+api.HOLDOUT_MARK,
  '2024-12~2025-01 2024-12 ~ 2025-01'+api.HOLDOUT_MARK,'2026-05 이후 2026-05 ~ 지금'+api.HOLDOUT_MARK]);
 assert.equal(cases[0].kids[1].textContent,'기대(운영자 메모): 노동 L0 또는 L+ · 물가 P+');
 assert.equal(cases[3].kids[3].textContent,"이 사례에 적힌 꼬리표 '상당 부분 반영'의 대조는 이 사이트가 계산하지 않습니다.");
 assert.equal(cases[5].kids[3].textContent,"이 사례에 적힌 꼬리표 'TP 주도'의 대조는 이 사이트가 계산하지 않습니다.");
 assert.ok(!cases[0].textContent.includes('꼬리표'));
 assert.deepEqual(cases.map(c=>c.kids[2].textContent),['기대한 L · P에 든 달 12/12','기대한 L · P에 든 달 6/6',
  '기대한 L · P에 든 달 2/3','기대한 L · P에 든 달 2/2','기대한 L · P에 든 달 2/2','기대한 L · P에 든 달 4/6']);
 const last=rowsOf(tableOf(cases[5],'lp-exp'));
 assert.deepEqual(last.map(r=>r[4]),['●','●','●','●','○','○']);                    // 2026-05~08 P+ · 2026-09 P0 · 2026-10 ?
 assert.deepEqual(last[5],['2026-10','L−','?','판정 보류(물가)','○']);
 assert.ok(capOf(cases[5],tableOf(cases[5],'lp-exp')).textContent.endsWith('● 기대한 L · P에 듦 · ○ 벗어남'));
 // 셈이 항목과 다르거나 항목 하나가 깨진 사례는 통째로 뺀다 · 항목이 없는 사례는 한 줄
 const d=lp();d.expected[0].matched=11;d.expected[1].items[2].cell='박스';d.expected[2].n=99;
 d.expected[3].items=[];d.expected[3].n=0;d.expected[3].matched=0;d.expected[4].holdout='yes';
 d.expected[5].items[0].match=false;d.expected[5].matched-=1;                    // 셈은 맞아도 기대한 상태 목록과 어긋난 듦
 const b=draw(d).wrap;
 const det2=cls(b,'lp-more').find(x=>tags(x,'summary')[0].textContent.startsWith('미리 적어 둔'));
 assert.equal(tags(det2,'summary')[0].textContent,'미리 적어 둔 기대와 대조 — 사례 1개');
 assert.deepEqual(cls(det2,'lp-case')[0].kids.slice(2).map(k=>k.textContent),['이 구간에 재생한 달이 없습니다.',
  "이 사례에 적힌 꼬리표 '상당 부분 반영'의 대조는 이 사이트가 계산하지 않습니다."]);
 for(const m of [c=>{c.want_L=['L9'];},c=>{c.want_P=[];},c=>{c.tag_unchecked='재화 주도';},c=>{c.want_L='L0';}]){
  const e=lp();m(e.expected[0]);
  const w=draw(e).wrap;
  const x=cls(w,'lp-more').find(y=>tags(y,'summary')[0].textContent.startsWith('미리 적어 둔'));
  assert.equal(tags(x,'summary')[0].textContent,'미리 적어 둔 기대와 대조 — 사례 5개');
 }
 const old=lp();for(const c of old.expected){delete c.want_L;delete c.want_P;delete c.tag_unchecked;}   // 목록이 없는 꼴도 받는다
 assert.equal(cls(draw(old).wrap,'lp-case').length,6);
 const e=lp();e.expected=[];
 assert.ok(!cls(draw(e).wrap,'lp-more').some(x=>tags(x,'summary')[0].textContent.startsWith('미리 적어 둔')));
});

test('definitions: the P table only when all nine cells match, rules and thresholds from the file',()=>{
 const {wrap}=draw(lp());
 const det=cls(wrap,'lp-more').find(d=>tags(d,'summary')[0].textContent==='읽는 법 — 상태와 문턱');
 assert.ok(det&&!('open' in det.attrs));
 const t=tableOf(det,'lp-pgrid');
 assert.deepEqual(rowsOf(t),[['H 높음','P+','P+','Pd'],['M 중간','P+','P0','P−'],['Lo 낮음','P0','P−','P−']]);
 const items=tags(cls(det,'lp-list')[0],'li').map(l=>l.textContent);
 assert.equal(items.length,14);
 assert.equal(items[0],'L+ · 회복 전환 — 고점 대비 하락과 확인');
 const text=det.textContent;
 assert.ok(text.includes('(H 3.1/2.9 · Lo 2.6/2.7)'),text);
 assert.ok(text.includes('가속이 1번, 둔화가 2번 이어진 발표에서 켜집니다'),text);
 assert.ok(text.includes('문턱(운영자 2026-10-14 고정): Sahm형 0.50(주의 0.40) · 청구 1.25배 × 4주'),text);
 assert.ok(text.includes('모멘텀 가속 +0.50 이상 1회, 둔화 -0.30 이하 2회 연속.'),text);
 const d=lp();d.defs.pgrid[0].P='P0';
 assert.equal(tableOf(draw(d).wrap,'lp-pgrid'),undefined);
 const e=lp();e.defs.pgrid.pop();
 assert.equal(tableOf(draw(e).wrap,'lp-pgrid'),undefined);
 const f=lp();f.defs={L:[{state:'L9',text:'x'},{state:'L0',text:'<b>x</b>'},{state:'L+',text:'이 칸은 유망하다'}]};   // 꼴 밖 · 꺾쇠 · 권유 낱말
 const g=draw(f).wrap;
 assert.equal(cls(cls(g,'lp-more').find(d=>tags(d,'summary')[0].textContent==='읽는 법 — 상태와 문턱'),'lp-list').length,0);
});

test('notes, computed-values notices, FRED citations and series — citation shape checked, links only to FRED',()=>{
 const {api,wrap}=draw(lp());
 const notes=tags(cls(wrap,'lp-notes')[0],'li').map(l=>l.textContent);
 assert.equal(notes.length,5);
 assert.ok(notes[0].includes('2026-10-14에 고정했습니다'));
 assert.ok(notes[1].includes('현재 개정치'));
 assert.ok(notes[2].includes('근사'));
 assert.equal(notes[3],'운영자 도구의 꼬리표 가운데 상당 부분 반영 · TP 주도 · 폭 좁음(트림 ≤ 3)는 이 사이트가 싣지 않는 재료(정책 경로가 금리에 ' +
  '얼마나 실렸는지 · 기간 프리미엄과 기대인플레이션의 3개월 변화 · 댈러스 연은 트림 평균)가 필요해 빼고 싣습니다.');
 assert.ok(notes[4].includes('예측이 아니고 예측력을 검증하지 않았습니다'));
 assert.equal(notes[4],api.NOT_FORECAST);
 const cite=cls(wrap,'lp-cite')[0];                                                // 계산값 고지는 늘 보이고, 인용은 바로 아래 접은 칸에
 assert.deepEqual(cite.kids.map(k=>k.textContent),[...lp().notices,"FRED 권장 인용(시리즈 13개)은 바로 아래 '자료와 권장 인용'에 시리즈마다 적습니다."]);
 const ser=cls(wrap,'lp-more').find(d=>tags(d,'summary')[0].textContent.startsWith('자료와 권장 인용'));
 assert.ok(!('open' in ser.attrs));
 assert.equal(tags(ser,'summary')[0].textContent,'자료와 권장 인용 — FRED 시리즈 13개(BLS · BEA · 미 노동부, FRED 경유)');
 assert.deepEqual(cls(ser,'lp-cites')[0].kids.map(k=>k.textContent),['권장 인용:',...SERIES.map(CITE)]);
 assert.equal(walk(wrap,n=>n.textContent===CITE('UNRATE')).filter(n=>n.tag==='p').length,1);
 assert.deepEqual(tags(ser,'a').map(a=>a.attrs.href),SERIES.map(s=>'https://fred.stlouisfed.org/series/'+s));
 const items=tags(cls(ser,'lp-list')[0],'li').map(l=>l.textContent);
 assert.equal(items[0],'UNRATE · 지어낸 제목 UNRATE — 마지막 관측 2026-10-01');
 assert.equal(items[SERIES.indexOf('CCSA')],'CCSA · 지어낸 제목 CCSA — 마지막 관측 2026-10-01 · 받지 못함');
 assert.equal(items[SERIES.indexOf('JTSQUR')],'JTSQUR · 지어낸 제목 JTSQUR — 마지막 관측 2026-10-01 · 이번 갱신에서 받지 못해 저장해 둔 자료');
 // 꼴이 다른 인용 · 모르는 시리즈 · FRED 밖 주소 · 겹친 시리즈는 싣지 않거나 글자로만
 const d=lp();
 d.sources[0].citation='<a>지어낸 출처</a>, retrieved from FRED, November 18, 2026.';
 d.sources[1].url='https://example.com/x';
 d.sources.push({series:'SP500',url:'https://fred.stlouisfed.org/series/SP500',citation:CITE('SP500'),citation_required:false});
 d.sources.push(Object.assign({},d.sources[2]));
 d.series.push({series:'NASDAQCOM',title:'x',last:null,fetched:'net'},{series:'UNRATE',title:'겹침',last:null,fetched:'net'},
  {series:'DGS10',title:'x',last:'2026-02-30',fetched:'net'});
 d.series[2].fetched='later';
 const b=draw(d).wrap;
 const sb=cls(b,'lp-more').find(x=>tags(x,'summary')[0].textContent.startsWith('자료와 권장 인용'));
 const cb=cls(sb,'lp-cites')[0].textContent;
 assert.ok(!cb.includes('[UNRATE]')&&!cb.includes('SP500'),cb);
 assert.equal(cb.split('retrieved from').length-1,12);
 assert.equal(tags(sb,'summary')[0].textContent,'자료와 권장 인용 — FRED 시리즈 12개(BLS · BEA · 미 노동부, FRED 경유)');
 assert.ok(!tags(sb,'a').some(a=>/example|NASDAQ|SP500/.test(a.attrs.href)));
 assert.equal(tags(sb,'a').length,11);                                          // LNS12300060은 주소가 FRED 밖이라 글자로
 assert.ok(cls(sb,'source-link')[0].textContent.includes('LNS12300060'));
 // 고지 · 인용이 모두 없으면 상자도 없다
 const e=lp();e.notices=[];e.sources=[];
 assert.equal(cls(draw(e).wrap,'lp-cite').length,0);
 assert.equal(cls(draw(e).wrap,'lp-cites').length,0);
 const f=lp();f.series=[];f.sources=[];
 assert.equal(cls(draw(f).wrap,'lp-sources').length,0);
});

test('asof: a muted stale line when more than ten days old',()=>{
 const at=(asof,now)=>{const d=lp();d.asof=asof;return draw(d,now).wrap;};
 assert.equal(cls(at('2026-11-08',NOW),'lp-asof')[0].textContent,'2026-11-08 계산 · 문턱 2026-10-14 고정');   // 정확히 10일은 그대로
 const old=at('2026-11-07',NOW);
 assert.equal(cls(old,'lp-asof').length,0);
 const line=cls(old,'lp-old')[0];
 assert.equal(line.textContent,'마지막 계산 2026-11-07 — 오래됨');
 assert.ok(line.attrs.class.split(' ').includes('muted'));
 assert.equal(cls(at('2026-11-07',new Date('2026-11-17T23:59:00Z')),'lp-old').length,0);   // Date도 받는다
 const {api,ids}=load();                                                         // now를 주지 않으면 지금 시계 — 오늘 계산한 파일은 오래되지 않았다
 const d=lp();d.asof=new Date().toISOString().slice(0,10);
 assert.equal(api.render(d),true);
 assert.equal(cls(ids['lp-ref'],'lp-old').length,0);
});

// ── 꼴 검사 ───────────────────────────────────────────────────────────────────────────
test('unusable files draw nothing and return false',()=>{
 const bad=[
  null,[],'x',{},
  Object.assign(lp(),{schema:2}),Object.assign(lp(),{schema:'1'}),
  Object.assign(lp(),{asof:'2026-02-30'}),Object.assign(lp(),{asof:'2026-11-18T00:00:00Z'}),
  Object.assign(lp(),{fixed:null}),Object.assign(lp(),{holdout_from:'2024-13'}),Object.assign(lp(),{holdout_from:'2024-01-01'}),
  Object.assign(lp(),{constants:null})];
 const mut=[
  d=>{delete d.constants.mom_dn_n;},d=>{d.constants.h_in='3.1';},d=>{d.constants.sahm_on=Infinity;},
  d=>{delete d.grid;},d=>{d.grid.L.reverse();},d=>{d.grid.P=['P+','P0','P−','Pd'];},d=>{d.grid.cells.pop();},
  d=>{d.grid.cells[0][0].name='금리 상방 여지';},d=>{d.grid.cells[2][0].kind='down';},d=>{d.grid.cells[1][1].L='L+';},
  d=>{d.grid.cells[3].push({L:'L−−',P:'P−',name:'큰 되돌림 위험 (경기침체형)',kind:'down'});},
  d=>{d.current=null;d.history=[];},d=>{d.current={month:'2026-09'};d.history='x';}];
 for(const m of mut){const d=lp();m(d);bad.push(d);}
 const throws=lp();Object.defineProperty(throws,'history',{get(){throw new Error('깨짐');}});
 bad.push(throws);
 bad.forEach((d,i)=>{
  const t=load();
  t.wrap.replaceChildren(new El('p'));
  assert.equal(t.api.render(d,NOW),false,'#'+i);
  assert.equal(t.wrap.kids.length,1,'#'+i);                                        // 그리던 것을 지우지도 않는다
 });
 const t=load({drop:['lp-ref']});
 assert.equal(t.api.render(lp(),NOW),false);                                       // 자리가 없으면 false
});

test('malformed items are skipped one by one',()=>{
 const d=lp();
 const h=d.history;
 h.find(r=>r.month==='2022-02').cell='박스';                                      // 칸 이름이 L · P와 짝이 아님
 h.find(r=>r.month==='2022-05').P='P0';                                           // 띠 × 모멘텀과 다른 P
 h.find(r=>r.month==='2022-06').kind='down';                                      // 종류가 다름
 h.find(r=>r.month==='2022-07').tags='계절성';                                     // 꼬리표가 배열이 아님
 h.find(r=>r.month==='2022-08').known='2022-09-31';
 h.find(r=>r.month==='2022-09').L='L1';
 h.find(r=>r.month==='2022-10').band='X';
 h.find(r=>r.month==='2022-11').tags=['재화 주도','이 달은 매수','<b>x</b>',3,'TP 주도 (3개월)'];   // 권유 낱말 · 꺾쇠 · 숫자 · 앞부분이 같은 제외 꼬리표
 h.reverse();                                                                     // 차례가 뒤집혀 와도 달 순서로
 h.push(Object.assign({},h[h.length-1],{tags:['겹친 달']}));                       // 같은 달이 두 번이면 파일에서 앞의 것
 const {wrap}=draw(d);
 const det=cls(wrap,'lp-more').find(x=>tags(x,'summary')[0].textContent.startsWith('2022년부터 달마다'));
 assert.equal(tags(det,'summary')[0].textContent,'2022년부터 달마다 — 51달(2022-01 ~ 2026-10)');
 const rows=rowsOf(tableOf(det,'lp-hist'));
 assert.deepEqual(rows.slice(0,4).map(r=>r[0]),['2022-01','2022-03','2022-04','2022-11']);
 assert.equal(rows[0][4],'—');
 assert.equal(rows[3][4],'재화 주도');
 // 지금 칸 — 판정 보류이거나 이름이 맞지 않으면 없는 것으로(재생 기록은 그대로)
 for(const m of [c=>{c.kind='hold';},c=>{c.cell='박스';},c=>{c.L='?';},c=>{c.band=null;},c=>{c.mom_class='Z';}]){
  const e=lp();m(e.current);
  const w=draw(e).wrap;
  assert.equal(cls(w,'lp-now')[0].textContent,'판정할 수 있는 달이 아직 없습니다.');
  assert.ok(tableOf(w,'lp-hist'));
 }
 // 가장 새 달 — 지금 칸보다 새 달이고 판정 보류일 때만
 for(const m of [x=>{x.month='2026-09';},x=>{x.kind='box';},x=>{x.cell='판정 보류(노동)';},x=>{x.tags=null;},x=>{x.P='P+';}]){
  const e=lp();m(e.latest);
  assert.equal(cls(draw(e).wrap,'lp-latest').length,0);
 }
 const f=lp();Object.assign(f.latest,{L:'?',P:'P0',cell:'판정 보류(노동)'});
 assert.equal(cls(draw(f).wrap,'lp-latest')[0].textContent,'2026-10: 물가 P0 — 노동 상태를 정할 자료가 모자라 판정 보류');
 const g=lp();Object.assign(g.latest,{L:'?',P:'?',cell:'판정 보류(노동·물가)',tags:['2개월 평균','상당 부분 반영']});
 assert.equal(cls(draw(g).wrap,'lp-latest')[0].textContent,'2026-10: 노동·물가 모두 판정 보류 · 꼬리표: 2개월 평균');
 // 다리 — 이름 앞부분 · 값의 꼴 · 충족 칸의 꼴이 어긋난 다리만 빠진다
 const k=lp();const L=k.current.legs;
 L[0].name='Sham형 ≥ 0.50';L[2].value=1;L[4].on='해고';L[7].value='0.4';L[11].on='HH';L[12].month='2026-9';
 const kt=rowsOf(tableOf(draw(k).wrap,'lp-legs'));
 assert.equal(kt.length,7);
 assert.deepEqual(kt.map(r=>r[0]),[1,3,5,6,8,9,10].map(i=>LEG_NAMES[i]));
 const n=lp();n.current.legs=[];
 assert.equal(cls(draw(n).wrap,'lp-legs').length,0);
 assert.ok(draw(n).wrap.textContent.includes('다리 자료가 없습니다.'));
 const z=lp();Object.assign(z.current.legs[0],{value:null,on:null});Object.assign(z.current.legs[11],{value:null,on:null});
 Object.assign(z.current.legs[4],{value:null,on:'-'});Object.assign(z.current.legs[2],{value:null,on:null});
 const zr=rowsOf(tableOf(draw(z).wrap,'lp-legs'));
 assert.deepEqual([zr[0].slice(1),zr[2].slice(1),zr[4].slice(1),zr[11].slice(1)],
  [['—','2026-09','?'],['—','2026-09','?'],['—','2026-09','—'],['—','2026-09','?']]);
 // 지금 칸의 L과 그 달 조건이 다르면 한 줄
 const r=lp();r.current.L_raw='L0';
 assert.ok(draw(r).wrap.textContent.includes('그 달 조건만 보면 L0입니다 — 상태는 두 발표가 이어져야 바뀌어 지금 상태는 L−입니다.'));
 assert.ok(!draw(lp()).wrap.textContent.includes('그 달 조건만 보면'));
});

// ── 글 ────────────────────────────────────────────────────────────────────────────────
test('no stray words, no prediction words, and no direction words beyond the cell names and their kinds',()=>{
 const {api,wrap}=draw(lp());
 const text=wrap.textContent;
 assert.ok(!STRAY.test(text),text);
 for(const w of BANNED)assert.ok(!text.includes(w),w);
 const code=SRC.replace(/const BANNED_WORDS = \[[^\]]*\];/,'');
 for(const w of BANNED)assert.ok(!code.includes(w),w);
 assert.deepEqual(plain(api.BANNED_WORDS),BANNED);
 // 방향을 말하는 낱말은 칸 이름 · 칸 종류의 말 · 운영자 도구의 꼬리표에만(기대 글은 상태 이름으로만 적혀 온다)
 let rest=text;
 const allowed=[...Object.values(NAMES).map(x=>x[0]),...Object.values(api.KIND_WORD),'고점 통과 — 되돌림 소진 가능',api.LABEL]
  .sort((a,b)=>b.length-a.length);
 for(const a of allowed)rest=rest.split(a).join(' ');
 for(const w of ['상방','하방','되돌림','스티프닝','상충','박스','골디락스','스태그'])assert.ok(!rest.includes(w),w+' — '+rest.slice(0,200));
 for(const w of ['예측이 아니고 예측력을 검증하지 않았습니다','예측 아님'])assert.ok(text.includes(w),w);
 // 이름표는 칸 이름이 나오는 곳마다: 카드 머리 · 격자 · 재생 기록 · 기대 대조
 assert.equal(text.split(api.LABEL).length-1,4);
});

test('the card script stays text-only and leans on index.html helpers only',()=>{
 const code=SRC.replace(/\/\*[\s\S]*?\*\//g,'').replace(/\/\/[^\n]*/g,'');
 for(const w of ['innerHTML','outerHTML','insertAdjacentHTML','createElement','fetch(','localStorage','sessionStorage','location.',
  'navigator.','eval(','new Function','url(','style'])
  assert.ok(!code.includes(w),w);
 assert.ok(/window\.LpCard = \(\(\) => \{/.test(SRC));
 assert.ok(PAGE.indexOf('<script src="lp.js"></script>')>PAGE.indexOf('<script src="ledger.js"></script>'));
 assert.ok(PAGE.indexOf('<script src="lp.js"></script>')<PAGE.indexOf('<script>\n"use strict";'));
});

// ── index.html 연결 ──────────────────────────────────────────────────────────────────
function braceBlock(text,start){
 let i=text.indexOf('{',start),depth=0;
 for(;i<text.length;i++){depth+=(text[i]==='{')-(text[i]==='}');if(depth===0)return text.slice(start,i+1);}
 throw new Error('짝이 맞지 않음');
}
test('applyView opens the grid section only on the home view, and only when it was drawn',()=>{
 const groups=PAGE.slice(PAGE.indexOf('const GROUPS = ['),PAGE.indexOf('];',PAGE.indexOf('const GROUPS = ['))+2);
 const apply=braceBlock(PAGE,PAGE.indexOf('function applyView() {'));
 const decl=PAGE.slice(PAGE.indexOf('const available = {'),PAGE.indexOf('};',PAGE.indexOf('const available = {'))+2);
 assert.ok(decl.includes('lp: false'));
 const nodes={};
 const node=id=>nodes[id]||(nodes[id]={id,hidden:false,textContent:'',dataset:{},setAttribute(){},removeAttribute(){}});
 const sc={location:{hash:''},window:{},document:{getElementById:node,querySelectorAll:()=>[],querySelector:()=>null}};
 const api=vm.runInNewContext('let activeView = "all", ruleState = "all", publicData = null;\n'+decl+'\n'+groups+'\n'+apply+
  '\n({applyView, set: o => Object.assign(available, o)})',sc);
 const seen=(hash,avail)=>{api.set(Object.assign({loaded:true,lp:false},avail));sc.location.hash=hash;api.applyView();
  return {lp:!nodes['lp-ref'].hidden,rules:!nodes['rules-wrap'].hidden,regime:!nodes['regime-ref'].hidden};};
 assert.deepEqual(seen('',{lp:true,regime:true}),{lp:true,rules:true,regime:true});
 assert.deepEqual(seen('#all',{lp:true,regime:false}),{lp:true,rules:true,regime:false});
 assert.equal(seen('',{lp:false}).lp,false);                                       // 그리지 못했으면 숨긴 채
 for(const h of ['#rates','#inflation','#credit','#liquidity','#ledger','#ai','#sources','#korea','#evening','#notes'])
  assert.equal(seen(h,{lp:true}).lp,false,h);
});

// ── 실제 자료 파일 ────────────────────────────────────────────────────────────────────
const REAL=path.join(__dirname,'../data/lp.json');
test('the committed data/lp.json (if any) draws whole — nothing in it is skipped by the checks',{skip:!fs.existsSync(REAL)&&'data/lp.json 없음'},()=>{
 const d=JSON.parse(fs.readFileSync(REAL,'utf8'));
 const {api,ok,wrap}=draw(d,Date.parse(d.asof+'T12:00:00Z'));
 assert.equal(ok,true);
 assert.equal(d.label,api.LABEL);
 const det=cls(wrap,'lp-more');
 const hist=det.find(x=>tags(x,'summary')[0].textContent.startsWith('2022년부터 달마다'));
 assert.equal(rowsOf(tableOf(hist,'lp-hist')).length,d.history.length);
 assert.equal(cls(wrap,'lp-case').length,d.expected.length);
 if(d.current){
  assert.equal(rowsOf(tableOf(wrap,'lp-legs')).length,d.current.legs.length);
  assert.equal(d.current.legs.length,13);
  assert.equal(walk(tableOf(wrap,'lp-grid'),n=>n.attrs['aria-current']==='true').length,1);
 }
 assert.equal(!!d.latest,cls(wrap,'lp-latest').length===1);
 const src=det.find(x=>tags(x,'summary')[0].textContent.startsWith('자료와 권장 인용'));
 assert.equal(tags(cls(src,'lp-list')[0],'li').length,d.series.length);
 assert.equal(cls(src,'lp-cites')[0].kids.length-1,d.sources.length);
 assert.ok(tableOf(wrap,'lp-pgrid'));
 for(const k of api.CONSTANTS)assert.ok(Number.isFinite(d.constants[k]),k);
 const text=wrap.textContent;
 assert.ok(!STRAY.test(text));
 for(const w of BANNED)assert.ok(!text.includes(w),w);
 for(const t of api.EXCLUDED)assert.ok(!d.history.some(r=>r.tags.includes(t)),t);
});
