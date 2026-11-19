// 미 국채 수급 카드(site/supply.js, 2026-11-19 — 운영자 결정 '1번 카드로 꺼내고 TIC도 추가해') — 금리·커브 묶음의 참고 카드 한 장에
// 주간(뉴욕 연은 — data/supply.json)과 월간(재무부 TIC — data/tic.json). index.html에서 el()·chartFigure()를 잘라 아주 작은 가짜 DOM 위에
// supply.js와 같은 맥락으로 싣고 render()를 돌려 글을 본다. 주간 부분의 쪽마다의 규칙(출처 표기·⚠ 줄·7~11년·경과일)은
// test_supply_ktb_render.cjs가 본다. 이름은 재무부 표의 꼴이고, 숫자는 2026-09 말 표를 본떠 지어낸 것이다.
// 실행: node --test scripts/test_supply_card_render.cjs
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

class El {
 constructor(tag){this.tag=tag;this.kids=[];this.attrs={};this.hidden=false;this.dataset={};this.style={};this.listeners={};}
 append(...xs){for(const x of xs)this.kids.push(typeof x==='string'?{text:x}:x);}
 replaceChildren(...xs){this.kids=[];this.append(...xs);}
 setAttribute(k,v){this.attrs[k]=String(v);}
 addEventListener(type,f){this.listeners[type]=f;}
 get childElementCount(){return this.kids.filter(k=>k instanceof El).length;}
 get textContent(){return this.kids.map(k=>k instanceof El?k.textContent:k.text).join('');}
 set textContent(v){this.kids=[{text:String(v)}];}
}
const walk=(n,f,out=[])=>{if(n instanceof El){if(f(n))out.push(n);n.kids.forEach(k=>walk(k,f,out));}return out;};
const cls=(n,c)=>walk(n,x=>(x.attrs.class||'').split(' ').includes(c));
const tags=(n,t)=>walk(n,x=>x.tag===t);
const texts=n=>n instanceof El?n.kids.flatMap(texts):[n.text];   // 글자 마디 — 모두 글(text)로 들어갔는지 본다
const cells=tr=>tr.kids.filter(k=>k instanceof El).map(k=>k.textContent);

const HTML=fs.readFileSync(path.join(__dirname,'../site/index.html'),'utf8');
function slice(start,end){
 const i=HTML.indexOf(start);assert.ok(i>=0,'index.html에 '+start+' 없음');
 const j=HTML.indexOf(end,i);assert.ok(j>i,'index.html에 '+end+' 없음');
 return HTML.slice(i,j);
}
const PAGE=[slice('function el(tag, attrs','const SVG_NS'),slice('function chartFigure(','const GROUPS = [')].join('\n');
const SUPPLY=fs.readFileSync(path.join(__dirname,'../site/supply.js'),'utf8');
const NOW=Date.parse('2026-11-19T03:00:00Z');                   // 한국 12:00

function load(opts={}){
 const ids={'supply-slot':new El('div')};
 if(opts.noSlot)delete ids['supply-slot'];
 const calls=[];
 class FakeDate extends Date{static now(){return opts.now||NOW;}}
 const document={createElement:t=>new El(t),getElementById:id=>ids[id]||null};
 const window={MacroCharts:opts.charts||{lineChart:(spec,o)=>{calls.push({spec,o});return new El('figure');}}};
 const ctx=vm.createContext({document,window,Date:FakeDate});
 vm.runInContext(PAGE,ctx);
 vm.runInContext(SUPPLY,ctx);
 return {api:window.SupplyCard,ids,calls,slot:ids['supply-slot']};
}

// ── 지어낸 자료 ───────────────────────────────────────────────────────────────────────────────────────────
const wk=(d,i)=>['2026-10-'+String(7+7*i).padStart(2,'0'),d];
function side(key,extra={}){
 const dealer=key==='dealer';
 return Object.assign({ok:true,stale:false,error:null,failed_since:null,
  name:dealer?'딜러 국채 순포지션(TIPS 제외)':'해외 공적 수탁 국채(뉴욕 연은 보관)',series:dealer?'PDPOSGST-TOT':'WMTSECL1',date:'2026-11-04',
  level_bn:dealer?433.46:2565.477,
  line:dealer?'433bn · 4주 +23 (2019년 이후 p5 -45 / p95 +52) · 52주 +54':'2,565bn · 4주 -25 (2019년 이후 p5 -53 / p95 +43) · 52주 -212',
  flag_text:null,extra:[],
  chart:{key:'supply_'+key,title:'t',unit:'bn',years:5,zero:dealer,threshold:null,note:'n',source_note:'s',notices:[],
   lines:[{key,label:'t',role:'series',series:[],derived:false,points:[wk(410,0),wk(dealer?433.46:2565.477,1)]}]},
  notices:dealer?['딜러 계산값 고지','© 2026 Federal Reserve Bank of New York.','관계없음 고지']:['수탁 계산값 고지']},extra);
}
const supply=()=>({schema:1,notice:'참고',dealer:side('dealer'),custody:side('custody')});

const NAMES=[['Japan','일본',1063.1,1068.3,1189.3],['United Kingdom','영국',985.8,994.5,862.5],['China, Mainland','중국 본토',563.9,590.7,699.2],
 ['Belgium','벨기에',507.9,490.5,463.6],['Cayman Islands','케이맨 제도',486.8,463.0,426.8],['Canada','캐나다',467.7,464.6,476.1],
 ['Luxembourg','룩셈부르크',445.0,448.2,420.6],['Ireland','아일랜드',344.8,352.1,340.0],['France','프랑스',332.0,363.4,375.5],
 ['Taiwan','대만',290.9,298.4,312.5],['Switzerland','스위스',289.0,285.8,301.8],['Singapore','싱가포르',274.5,277.9,258.6],
 ['Hong Kong','홍콩',249.2,261.5,238.9],['India','인도',228.2,219.7,202.7],['Norway','노르웨이',209.4,214.0,215.9],
 ['Brazil','브라질',165.9,168.4,172.8],['Korea, South','한국',139.9,134.2,142.7],['Saudi Arabia','사우디아라비아',135.9,141.2,134.2],
 ['Bermuda','버뮤다',108.5,111.8,103.4],['United Arab Emirates','아랍에미리트',108.1,116.1,103.3]];
const GRAND=9241.2;
const r1=v=>Math.round(v*10)/10;
function row(name_en,name_ko,now,prev,ago,rank){
 return {rank,name_en,name_ko,level_bn:now,chg_1m_bn:r1(now-prev),chg_12m_bn:r1(now-ago),share_pct:r1(now/GRAND*100)};
}
function tic(extra={}){
 const countries=NAMES.map((n,i)=>row(...n,i+1));
 countries.push(row('All Other','그 밖',1844.9,1852.3,1797.9,null));
 const tot=(name,now,prev,ago,more={})=>Object.assign({name,level_bn:now,chg_1m_bn:r1(now-prev),chg_12m_bn:r1(now-ago)},more);
 const pts=(a,b)=>[['2011-12-31',a],['2026-08-31',b[0]],['2026-09-30',b[1]]];
 return Object.assign({schema:1,generated_at:'2026-11-19T09:00:00+00:00',ok:true,stale:false,error:null,failed_since:null,
  retrieved:'2026-11-19',month:'2026-09',prev_month:'2026-08',year_ago:'2025-09',
  totals:{grand:tot('해외 전체 보유',GRAND,9316.7,9238.2),official:tot('그중 해외 공적',3674.7,3755.6,3872.6,{share_pct:39.8}),
   official_bills:tot('공적 중 단기채(T-bill)',288.5,312.2,371.3),official_notes_bonds:tot('공적 중 이표채(T-note · T-bond)',3386.1,3443.4,3501.2),
   bills_share_of_official_pct:7.9},
  countries,korea:countries[16],lines:{grand:'JSON용 글 — 화면은 숫자로 다시 만든다'},
  chart:{key:'tic_totals',title:'해외 보유 미 국채 — 전체와 해외 공적',unit:'bn',zero:false,threshold:null,note:'2011-12 이후 · 월말',source_note:'s',notices:[],
   lines:[{key:'grand',label:'해외 전체',role:'series',points:pts(5004.4,[9316.7,GRAND])},
          {key:'official',label:'그중 해외 공적',role:'series',points:pts(3600,[3755.6,3674.7])}]},
  chart_countries:{key:'tic_countries',title:'나라별 보유',unit:'bn',zero:false,threshold:null,note:'n',source_note:'s',notices:[],
   lines:[{key:'jp',label:'일본',role:'series',points:pts(1100,[1068.3,1063.1])},
          {key:'uk',label:'영국',role:'series',points:pts(114.3,[994.5,985.8])},
          {key:'cn',label:'중국 본토',role:'series',points:pts(1100,[590.7,563.9])}]},
  chart_korea:{key:'tic_korea',title:'한국 보유',unit:'bn',zero:false,threshold:null,note:'n',source_note:'s',notices:[],
   lines:[{key:'kr',label:'한국',role:'series',points:pts(47.3,[134.2,139.9])}]},
  source:{table:'https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table5.txt',
   history:'https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/mfhhis01.txt',name:'x'},
  notices:['TIC 계산값 고지','TIC 관계없음 고지'],release_note:'매달 18일 무렵 두 달 전 월말 자료'},extra);
}
const lines=n=>walk(n,x=>x.tag==='p').map(p=>(p.attrs.class||'')+'|'+p.textContent);
const part=(card,i)=>tags(card,'section')[i];
// 판정·권유로 읽히는 낱말 — 아래 부정 구절 안의 것은 뺀 뒤에 센다(‘…가 아닙니다’, ‘…라고 볼 수는 없습니다’)
const BANNED=['매수','매도','유망','적중','전망','예상','추천','과열','위험 신호','경고'];
const NEGATED=[];   // 부정 구절 안의 낱말 — 2026-11-19부터 주간 부분도 ‘곧 판 것으로’로 써 비었다(새 부정 구절이 생기면 여기에)
const clean=t=>{for(const p of NEGATED)t=t.split(p).join('');return t;};

test('full card: one article, heading with the label, weekly part then monthly part, everything as text',()=>{
 const {api,slot,calls}=load();
 assert.equal(api.render(supply(),tic()),true);
 assert.equal(slot.kids.length,1);
 const card=slot.kids[0], text=card.textContent;
 assert.equal(card.tag,'article');
 assert.deepEqual(card.attrs,{class:'oil-card supply-card','aria-labelledby':'supply-title'});
 const h3=tags(card,'h3')[0];
 assert.equal(h3.attrs.id,'supply-title');
 assert.equal(h3.textContent,'미 국채 수급 — 딜러 재고 · 해외 보유참고 — 예측 아님 · 판정에 쓰지 않음');
 assert.equal(cls(h3,'reference-label')[0].textContent,api.LABEL);
 assert.deepEqual(tags(card,'h4').map(h=>h.textContent),['주간 — 뉴욕 연은','월간 — 재무부 TIC']);
 assert.deepEqual(tags(card,'section').map(s=>s.attrs['aria-labelledby']),['supply-weekly-title','supply-monthly-title']);
 const ls=lines(card);
 assert.ok(ls.includes('supply-num|433bn · 4주 +23 (2019년 이후 p5 -45 / p95 +52) · 52주 +54'),ls.join('\n'));
 assert.ok(ls.includes('supply-num|2,565bn · 4주 -25 (2019년 이후 p5 -53 / p95 +43) · 52주 -212'));
 assert.equal(cls(part(card,0),'supply-row').length,2);                       // 7~11년이 없던 때의 파일 — 두 쪽
 assert.equal(calls.length,5);                                               // 주간 둘 + TIC 셋
 // 카드 머리 글은 두 문장(긴 설명은 부분마다 접는 '읽는 법'으로) — 머리 글은 h3 바로 뒤 한 줄
 const about=card.kids.filter(k=>k instanceof El)[1];
 assert.deepEqual([about.tag,about.attrs.class,about.textContent],['p','muted',api.ABOUT]);
 assert.equal(api.ABOUT.split('니다.').length-1,2);
 assert.ok(api.ABOUT.includes('한국 포함'));
 // 접는 설명은 둘(주간 · 월간) 다 닫혀 있다
 assert.deepEqual(cls(card,'rule-guide').map(d=>[d.tag,d.attrs.open,tags(d,'summary')[0].textContent]),
  [['details',undefined,'읽는 법 — 주간 숫자'],['details',undefined,'읽는 법 — TIC 숫자의 단서']]);
 assert.ok(texts(card).every(x=>typeof x==='string'));
 assert.ok(!/undefined|NaN|null|\[object/.test(text),text.match(/.{20}(undefined|NaN|null|\[object).{20}/));
 for(const w of BANNED)assert.ok(!clean(text).includes(w),w);
 assert.equal(tags(card,'a').length,0);                                      // 링크 없음(재무부 주소는 글자로)
 assert.equal(tags(card,'img').length,0);
});

test('a jump line under the card head goes to the monthly part and the Korea row without touching the address',()=>{
 const {api,slot,ids}=load();
 api.render(supply(),tic());
 const card=slot.kids[0];
 const nav=cls(card,'supply-jump');
 assert.equal(nav.length,1);
 assert.equal(card.kids.filter(k=>k instanceof El).indexOf(nav[0]),2);                // 머리 글 바로 뒤
 const btns=tags(nav[0],'button');
 assert.deepEqual(btns.map(b=>[b.textContent,b.attrs.type]),[['월간 — 재무부 TIC','button'],['한국 줄','button']]);
 assert.equal(nav[0].textContent,'바로 가기 월간 — 재무부 TIC 한국 줄');
 // 한국 줄의 id는 짧은 표에만(전체 목록에는 없다 — id가 한 번)
 const withId=walk(card,n=>n.attrs.id==='supply-korea-row');
 assert.equal(withId.length,1);
 assert.ok(walk(tags(card,'table')[0],n=>n===withId[0]).length===1);
 // 누르면 그 자리로 스크롤하고 초점 — 주소는 쓰지 않는다
 for(const [b,id] of [[btns[0],'supply-monthly-title'],[btns[1],'supply-korea-row']]){
  const target=walk(card,n=>n.attrs.id===id)[0];
  let scrolled=null,focused=null;
  target.scrollIntoView=o=>{scrolled=o;};target.focus=o=>{focused=o;};
  ids[id]=target;
  b.listeners.click();
  assert.equal(JSON.stringify([scrolled,focused,target.attrs.tabindex]),JSON.stringify([{block:'start'},{preventScroll:true},'-1']),id);
 }
 // 한국이 표에 없으면 월간 단추만, 월간이 '자료 없음'이거나 주간이 없으면(카드가 짧다) 바로 가기 없음
 const none=tic({korea:null});none.countries=none.countries.filter(c=>c.name_en!=='Korea, South');
 let t=load();t.api.render(supply(),none);
 assert.deepEqual(tags(cls(t.slot,'supply-jump')[0],'button').map(b=>b.textContent),['월간 — 재무부 TIC']);
 for(const [s2,t2] of [[supply(),null],[null,tic()],[supply(),tic({notices:[]})]]){
  t=load();t.api.render(s2,t2);
  assert.equal(cls(t.slot,'supply-jump').length,0);
 }
});

test('monthly totals: level, signed 1- and 12-month changes with thousands separators, official and bills shares',()=>{
 const {api,slot}=load();
 api.render(supply(),tic());
 const m=part(slot.kids[0],1);
 assert.deepEqual(cls(m,'tic-total').map(p=>p.textContent),[
  '해외 전체 보유 9,241bn · 1개월 -76 · 12개월 +3',
  '그중 해외 공적 3,675bn · 1개월 -81 · 12개월 -198 · 해외 전체의 39.8%',
  '공적 중 단기채(T-bill) 289bn · 1개월 -24 · 12개월 -83 · 공적의 7.9%',
  '공적 중 이표채(T-note · T-bond) 3,386bn · 1개월 -57 · 12개월 -115']);
 // 토막(수준 · 1개월 · 12개월 · 비중)마다 span.nw — 좁은 화면에서 '해외 전체의 / 39.8%'처럼 가운데서 끊지 않는다(글자는 그대로)
 const off=cls(m,'tic-total')[1];
 assert.deepEqual(cls(off,'nw').map(n=>n.textContent),['3,675bn','1개월 -81','12개월 -198','해외 전체의 39.8%']);
 const small=tags(cls(m,'supply-name')[0],'small')[0];
 assert.deepEqual(cls(small,'nw').map(n=>n.textContent),['2026-09 말 기준','받은 날 2026-11-19']);
 assert.ok(lines(m).includes('supply-name|재무부 TIC 해외 보유 2026-09 말 기준 · 받은 날 2026-11-19'),lines(m).join('\n'));
 assert.ok(lines(m).includes('muted|1개월·12개월은 2026-08 말·2025-09 말 잔액과의 차(bn), 비중은 해외 전체 보유 대비입니다.'));
 assert.ok(m.textContent.includes(api.MONTHLY_NOTE));
 assert.ok(!m.textContent.includes('JSON용 글'));                            // lines는 읽지 않는다
 // 자료 파일에 이름이 없으면 정해 둔 이름, 없는 합계 줄은 빼고, 비중 칸이 없으면 비중 없이
 const t=tic();delete t.totals.grand.name;delete t.totals.official_notes_bonds;delete t.totals.official.share_pct;t.totals.bills_share_of_official_pct='7.9';
 const u=load();u.api.render(supply(),t);
 assert.deepEqual(cls(u.slot,'tic-total').map(p=>p.textContent),['해외 전체 보유 9,241bn · 1개월 -76 · 12개월 +3',
  '그중 해외 공적 3,675bn · 1개월 -81 · 12개월 -198','공적 중 단기채(T-bill) 289bn · 1개월 -24 · 12개월 -83']);
});

test('number formats: integer bn with separators, signed changes (0 without sign), one-decimal shares, dash when missing',()=>{
 const {api}=load();
 assert.deepEqual([9241.2,139.9,0.4,1234.5,12345678.9,-0.4].map(api.bnText),['9,241bn','140bn','0bn','1,235bn','12,345,679bn','0bn']);
 assert.deepEqual([-75.5,5.7,0,0.4,-0.4,1234.5,-1234.5,null,undefined,NaN,'3',Infinity].map(api.chgText),
  ['-76','+6','0','0','0','+1,235','-1,235','—','—','—','—','—']);
 assert.deepEqual([39.76,1.5,0,null,'1'].map(api.pctText),['39.8%','1.5%','0.0%','—','—']);
});

test('countries: top 10 plus Korea marked by text, a gap row for the ranks in between, full list folded',()=>{
 const {api,slot}=load();
 api.render(supply(),tic());
 const m=part(slot.kids[0],1);
 const [short,full]=tags(m,'table');
 assert.equal(tags(short,'caption')[0].textContent,'상위 10곳과 한국 — 2026-09 말');
 assert.deepEqual(cells(tags(short,'thead')[0].kids[0]),['순위','나라','보유(bn)','1개월','12개월','비중']);
 const body=tags(tags(short,'tbody')[0],'tr');
 assert.equal(body.length,12);
 assert.deepEqual(cells(body[0]),['1','일본','1,063bn','-5','-126','11.5%']);
 assert.deepEqual(body.slice(0,10).map(r=>cells(r)[1]),['일본','영국','중국 본토','벨기에','케이맨 제도','캐나다','룩셈부르크','아일랜드','프랑스','대만']);
 assert.deepEqual(cells(body[10]),['11~16위는 ‘전체 목록’에']);
 assert.equal(body[10].attrs.class,'tic-gap');
 assert.deepEqual(cells(body[11]),['17','한국 · 늘 싣는 줄','140bn','+6','-3','1.5%']);
 assert.equal(body[11].attrs.class,'tic-korea');                               // 바탕색만이 아니라 글자로도 표시
 assert.equal(cls(body[11],'tic-mark')[0].textContent,' · 늘 싣는 줄');
 assert.ok(tags(short,'th').filter(t=>t.attrs.scope==='row').length===11);
 // 전체 목록 — 접혀 있고(열림 속성 없음), 20곳 + 그 밖 + 해외 전체
 const det=cls(m,'tic-all')[0];
 assert.equal(det.tag,'details');
 assert.equal(det.attrs.open,undefined);
 assert.equal(tags(det,'summary')[0].textContent,'전체 목록 — 20곳 · 그 밖 · 해외 전체');
 assert.ok(walk(det,x=>x===full).length===1);
 const all=tags(tags(full,'tbody')[0],'tr');
 assert.equal(all.length,21);
 assert.deepEqual(cells(all[20]),['—','그 밖','1,845bn','-7','+47','20.0%']);
 assert.deepEqual(all.filter(r=>r.attrs.class==='tic-korea').map(r=>cells(r)[1]),['한국']);   // 모든 줄이 있는 목록 — 글자 표시 없이 바탕만
 assert.equal(cls(full,'tic-mark').length,0);
 assert.deepEqual(cells(tags(tags(full,'tfoot')[0],'tr')[0]),['','해외 전체','9,241bn','-76','+3','100.0%']);
 // 표는 가로 스크롤 상자 안에서만 넘친다
 assert.ok(tags(m,'table').every(t=>walk(m,x=>x.attrs.class==='tic-scroll'&&x.kids.includes(t)).length===1));
});

test('countries are drawn in rank order even when the file keeps the Treasury table order',()=>{
 // 자료 파일의 차례는 재무부 표의 차례(tic_fetch는 rank만 마지막 달 값으로 매긴다) — 10위 대만과 13위 홍콩의 자리를 바꿔도 화면은 순위대로
 const t=tic();
 [t.countries[9],t.countries[12]]=[t.countries[12],t.countries[9]];
 assert.deepEqual([t.countries[9].rank,t.countries[12].rank],[13,10]);
 const x=load();
 assert.equal(x.api.TOP,10);
 x.api.render(supply(),t);
 const [short,full]=tags(x.slot,'table');
 const body=tags(tags(short,'tbody')[0],'tr');
 assert.deepEqual(body.slice(0,10).map(r=>cells(r)[0]),['1','2','3','4','5','6','7','8','9','10']);
 assert.equal(cells(body[9])[1],'대만');
 assert.deepEqual(cells(body[10]),['11~16위는 ‘전체 목록’에']);
 assert.deepEqual(cells(body[11]).slice(0,2),['17','한국 · 늘 싣는 줄']);
 const all=tags(tags(full,'tbody')[0],'tr').map(r=>cells(r)[0]);
 assert.deepEqual(all,[...Array.from({length:20},(_,i)=>String(i+1)),'—']);
});

test('Korea inside the top 10 needs no gap row; Korea at 12 says "11위"; absent Korea says it is in "그 밖"',()=>{
 const within=tic();
 const k=within.countries.splice(16,1)[0];within.countries.splice(7,0,k);
 within.countries.forEach((c,i)=>{if(c.rank!==null)c.rank=i+1;});
 let t=load();t.api.render(supply(),within);
 let body=tags(tags(tags(t.slot,'table')[0],'tbody')[0],'tr');
 assert.equal(body.length,10);
 assert.deepEqual(cells(body[7]).slice(0,2),['8','한국 · 늘 싣는 줄']);
 assert.equal(cls(t.slot,'tic-gap').length,0);
 const twelve=tic();
 const k2=twelve.countries.splice(16,1)[0];twelve.countries.splice(11,0,k2);
 twelve.countries.forEach((c,i)=>{if(c.rank!==null)c.rank=i+1;});
 t=load();t.api.render(supply(),twelve);
 assert.deepEqual(cls(t.slot,'tic-gap').map(r=>r.textContent),['11위는 ‘전체 목록’에']);
 const eleven=tic();
 const k3=eleven.countries.splice(16,1)[0];eleven.countries.splice(10,0,k3);
 eleven.countries.forEach((c,i)=>{if(c.rank!==null)c.rank=i+1;});
 t=load();t.api.render(supply(),eleven);
 assert.equal(cls(t.slot,'tic-gap').length,0);                                 // 11위 — 바로 이어져 사이 줄 없음
 assert.equal(tags(tags(tags(t.slot,'table')[0],'tbody')[0],'tr').length,11);
 // 한국이 없는 달 — korea null, 나라 줄에도 없음
 const none=tic({korea:null});none.countries=none.countries.filter(c=>c.name_en!=='Korea, South');
 t=load();t.api.render(supply(),none);
 assert.equal(cls(t.slot,'tic-korea').length,0);
 assert.ok(lines(t.slot).includes('muted|한국은 이번 달 재무부 표(상위 20곳)에 없습니다 — ‘그 밖’에 들어 있습니다.'));
 assert.equal(tags(tags(tags(t.slot,'table')[0],'tbody')[0],'tr').length,10);
 // korea 칸이 없는 옛 꼴 — 나라 줄에서 재무부 표의 이름으로 찾는다
 const old=tic();delete old.korea;
 t=load();t.api.render(supply(),old);
 assert.equal(cls(tags(t.slot,'table')[0],'tic-korea').length,1);
});

test('an unknown country shows its English name; data text never becomes markup',()=>{
 const t=tic();
 t.countries[2]={...t.countries[2],name_en:'Atlantis, Republic of',name_ko:null};
 t.countries[3]={...t.countries[3],name_en:'<b>Nowhere</b>',name_ko:7};
 const {api,slot}=load();
 api.render(supply(),t);
 const names=tags(tags(tags(slot,'table')[0],'tbody')[0],'tr').map(r=>cells(r)[1]);
 assert.equal(names[2],'Atlantis, Republic of');
 assert.equal(names[3],'<b>Nowhere</b>');
 assert.equal(tags(slot,'b').length,0);
 assert.ok(texts(slot).every(x=>typeof x==='string'));
 // 숫자가 아닌 보유·빈 이름의 줄은 버린다, 변화가 없으면 —
 const u=tic();
 u.countries[0]={...u.countries[0],level_bn:'1063.1'};u.countries[1]={...u.countries[1],name_en:''};
 u.countries[2]={...u.countries[2],chg_1m_bn:null,chg_12m_bn:undefined,share_pct:null};
 const w=load();w.api.render(supply(),u);
 const body=tags(tags(tags(w.slot,'table')[0],'tbody')[0],'tr');
 assert.deepEqual(cells(body[0]),['3','중국 본토','564bn','—','—','—']);
 assert.ok(!/undefined|NaN|null|\[object/.test(w.slot.textContent));
});

test('supply only: the monthly part is one "자료 없음", the weekly part draws as before',()=>{
 const bad=[null,undefined,'x',[1],{},tic({month:'2026-9'}),tic({month:'2026-13'}),tic({notices:[]}),tic({notices:['',7]}),
  tic({totals:null}),tic({totals:{grand:{level_bn:'9241'}}}),tic({month:null})];
 for(const t of bad){
  const {api,slot,calls}=load();
  assert.equal(api.render(supply(),t),true,JSON.stringify(t)?.slice(0,60));
  const m=part(slot.kids[0],1);
  assert.deepEqual(lines(m),['muted|자료 없음']);
  assert.equal(tags(m,'table').length,0);
  assert.equal(calls.length,2);                                              // 주간 둘만
  assert.ok(lines(part(slot.kids[0],0)).includes('supply-num|433bn · 4주 +23 (2019년 이후 p5 -45 / p95 +52) · 52주 +54'));
 }
});

test('tic only: the weekly part is one "자료 없음", the monthly part draws in full without the custody pair',()=>{
 const broken={schema:1,dealer:{...side('dealer'),notices:[]},custody:{...side('custody'),date:'x'}};
 for(const s of [null,undefined,'x',7,{},broken]){
  const {api,slot,calls}=load();
  assert.equal(api.render(s,tic()),true,String(s));
  const w=part(slot.kids[0],0);
  assert.deepEqual(lines(w),['muted|자료 없음']);
  assert.equal(calls.length,3);                                              // TIC 셋만
  const m=part(slot.kids[0],1);
  assert.equal(cls(m,'tic-total').length,4);
  assert.equal(cls(m,'tic-pair').length,0);                                   // 주간 수탁 숫자가 없으면 나란히 놓지 않는다
 }
});

test('both unusable: false and the slot stays empty; no slot is false too',()=>{
 const broken={dealer:{...side('dealer'),notices:[]},custody:{...side('custody'),line:''}};
 for(const [s,t] of [[null,null],[undefined,undefined],[{},{}],[broken,tic({notices:[]})],['x',tic({month:'2026-09-01'})]]){
  const {api,slot,calls}=load();
  assert.equal(api.render(s,t),false);
  assert.equal(slot.kids.length,0);
  assert.equal(calls.length,0);
 }
 const {api}=load({noSlot:true});
 assert.equal(api.render(supply(),tic()),false);
});

test('a part that breaks while drawing becomes "자료 없음" and the other part stays',()=>{
 const t=tic();
 Object.defineProperty(t,'countries',{get(){throw new Error('깨진 자료');}});
 const {api,slot}=load();
 assert.equal(api.render(supply(),t),true);
 assert.deepEqual(lines(part(slot.kids[0],1)),['muted|자료 없음']);
 assert.ok(lines(part(slot.kids[0],0)).includes('supply-num|433bn · 4주 +23 (2019년 이후 p5 -45 / p95 +52) · 52주 +54'));
});

test('caveats: custody attribution, holdings ≠ net purchases, revisions, TIC official vs WMTSECL1 with this run’s two numbers',()=>{
 const {api,slot}=load();
 api.render(supply(),tic());
 const m=part(slot.kids[0],1);
 const guide=cls(m,'rule-guide')[0];
 assert.equal(guide.tag,'details');
 assert.equal(tags(guide,'summary')[0].textContent,'읽는 법 — TIC 숫자의 단서');
 const paras=tags(guide,'p').map(p=>p.textContent);
 assert.deepEqual(paras.map(p=>p.split(' · ')[0]),[...api.GUIDE].map(g=>g[0]));
 const all=paras.join('\n');
 for(const w of ['실제 주인의 나라로 잡히지 않을 수 있습니다','TIC FAQ 7번','잔액을 바꾸므로','곧 판 것으로','순매입','고쳐 다시 내기도','2011년 12월',
  '범위가 다르고','평가 기준도 다를 수 있습니다','해외 보관 기관을 거친 몫은 공적으로 잡히지 않을 수 있습니다','WMTSECL1','매달 18일 무렵','SLT','BL2',
  '정해진 때 없이','전에 받은 표의 값을 둡니다'])assert.ok(all.includes(w),w);
 // 2026-11-19 검토 반영 — 나라는 '보관 기관이 있는 곳'이 아니고, TIC 공적이 수탁을 '모두' 포함한다고도, 기록 파일이 '해마다 한 번'이라고도 쓰지 않는다
 const card=slot.kids[0].textContent;
 for(const w of ['보관 기관이 있는 곳','어느 보관 기관에 맡겼든','그 가운데 뉴욕 연은','뉴욕 연은에 맡긴 몫만','해마다 한','중장기채','T-Bills'])
  assert.ok(!card.includes(w),w);
 assert.equal(api.GUIDE[0][0],'나라 ≠ 실제 주인일 수 있음');
 assert.ok(api.MONTHLY_NOTE.includes('보고된 보유자(또는 해외 보관 기관)의 소재지'));
 // 두 '해외 공적' 숫자 — 늘 보이는 한 줄로 공적 합계 바로 아래(접는 설명에는 숫자를 다시 적지 않는다)
 const pair=cls(m,'tic-pair');
 assert.deepEqual(pair.map(p=>p.textContent),['위 주간의 해외 공적 수탁(뉴욕 연은 보관, 2026-11-04 2,565bn)은 이 ‘그중 해외 공적’과 범위·재는 때가 달라 같은 양이 아닙니다 — 아래 ‘읽는 법’.']);
 const kids=m.kids.filter(k=>k instanceof El);
 assert.equal(kids.indexOf(pair[0]),kids.indexOf(cls(m,'tic-totals')[0])+1);
 assert.ok(!all.includes('2,565bn')&&!all.includes('이번 자료:'));
 assert.deepEqual(cls(m,'notices')[0].kids.map(k=>k.textContent),['TIC 계산값 고지','TIC 관계없음 고지']);
 const src=cls(m,'source-link').map(p=>p.textContent);
 assert.deepEqual(src,['자료: '+api.SOURCE+' ('+api.SOURCE_AT+')']);
 assert.ok(src[0].includes('Treasury International Capital (TIC)')&&src[0].includes('ticdata.treasury.gov'));
 assert.ok(lines(m).some(l=>l.startsWith('muted|재무부 TIC(Treasury International Capital) 표')&&l.includes('매달 18일 무렵 두 달 전 월말 자료')));
 assert.ok(lines(m).includes('tic-note|'+api.MONTHLY_NOTE));
});

test('charts go through chartFigure with captions, no repeated notices, and the line format',()=>{
 const {api,slot,calls}=load();
 api.render(supply(),tic());
 const tc=calls.slice(2);
 assert.deepEqual(tc.map(c=>c.spec.key),['tic_totals','tic_countries','tic_korea']);
 assert.deepEqual(tc.map(c=>[c.o.height,c.o.caption,c.o.notices]),[[190,true,false],[190,true,false],[190,true,false]]);
 assert.deepEqual([9241.2,3674.7,139.9].map(tc[0].o.format),['9,241bn','3,675bn','140bn']);
 assert.deepEqual(calls.slice(0,2).map(c=>[c.o.height,c.o.caption,c.o.format(2524.2)]),[[150,false,'2,524bn'],[150,false,'2,524bn']]);
 assert.equal(cls(part(slot.kids[0],1),'supply-row').filter(r=>tags(r,'figure').length).length,3);
 // 나라 그래프 아래 선마다 마지막 값 한 줄 — 일본·영국처럼 끝 값 글자가 겹쳐 그래프에서 빠져도 읽힌다
 const ends=cls(part(slot.kids[0],1),'tic-ends');
 assert.deepEqual(ends.map(p=>p.textContent),['2026-09 말: 일본 1,063bn · 영국 986bn · 중국 본토 564bn']);
 assert.deepEqual(cls(ends[0],'nw').map(n=>n.textContent),['일본 1,063bn','영국 986bn','중국 본토 564bn']);
 assert.ok(walk(cls(part(slot.kids[0],1),'supply-row')[2],x=>x===ends[0]).length===1);   // 그 그래프와 같은 칸
 // 선 하나뿐 · 마지막 날짜가 다름 · 꼴이 어긋남이면 줄을 두지 않는다
 for(const bad of [t=>{t.chart_countries.lines=t.chart_countries.lines.slice(0,1);},t=>{t.chart_countries.lines[1].points.pop();},
  t=>{t.chart_countries.lines[2].label='';},t=>{t.chart_countries.lines[0].points=[['x',1]];}]){
  const x=tic();bad(x);const u=load();u.api.render(supply(),x);
  assert.equal(cls(u.slot,'tic-ends').length,0);
 }
 const t=tic();delete t.chart_countries;delete t.chart_korea;t.chart={bad:true};   // 없는 그래프·그리지 못한 그래프는 빠질 뿐
 const u=load({charts:{lineChart:spec=>{if(spec.bad)throw new Error('x');return new El('figure');}}});
 assert.equal(u.api.render(supply(),t),true);
 assert.equal(tags(part(u.slot.kids[0],1),'figure').length,0);
 assert.equal(cls(part(u.slot.kids[0],1),'tic-total').length,4);
});

test('stale and late marks: not received this run, and a data month older than the release calendar',()=>{
 let t=load();t.api.render(supply(),tic({stale:true,failed_since:'2026-11-18'}));
 assert.ok(lines(part(t.slot.kids[0],1)).includes('supply-late|이번 갱신에서 받지 못해 직전에 받은 값을 싣습니다 (2026-11-18부터)'));
 t=load();t.api.render(supply(),tic({stale:true,failed_since:'어제'}));
 assert.ok(lines(part(t.slot.kids[0],1)).includes('supply-late|이번 갱신에서 받지 못해 직전에 받은 값을 싣습니다'));
 for(const v of ['true',1,false,null]){
  t=load();t.api.render(supply(),tic({stale:v}));
  assert.equal(cls(part(t.slot.kids[0],1),'supply-late').length,0,String(v));
 }
 const head=(month,now)=>{const x=load({now:Date.parse(now)});x.api.render(supply(),tic({month}));
  return cls(part(x.slot.kids[0],1),'supply-name')[0].textContent;};
 assert.equal(head('2026-09','2026-11-19T03:00:00Z'),'재무부 TIC 해외 보유 2026-09 말 기준 · 받은 날 2026-11-19');
 assert.equal(head('2026-08','2026-11-19T03:00:00Z'),'재무부 TIC 해외 보유 2026-08 말 기준 · 받은 날 2026-11-19');   // 18일 무렵 — 24일까지 봐준다
 assert.equal(head('2026-07','2026-11-19T03:00:00Z'),'재무부 TIC 해외 보유 2026-07 말 기준 · 받은 날 2026-11-19 · 다음 달 자료를 아직 받지 못함');
 assert.equal(head('2026-08','2026-11-25T03:00:00Z'),'재무부 TIC 해외 보유 2026-08 말 기준 · 받은 날 2026-11-19 · 다음 달 자료를 아직 받지 못함');
 assert.equal(head('2026-10','2027-01-02T03:00:00Z'),'재무부 TIC 해외 보유 2026-10 말 기준 · 받은 날 2026-11-19');       // 해를 넘겨도
 assert.equal(head('2026-09','2027-01-02T03:00:00Z'),'재무부 TIC 해외 보유 2026-09 말 기준 · 받은 날 2026-11-19 · 다음 달 자료를 아직 받지 못함');
 t=load();t.api.render(supply(),tic({retrieved:'어제',prev_month:'8월'}));
 const m=part(t.slot.kids[0],1);
 assert.equal(cls(m,'supply-name')[0].textContent,'재무부 TIC 해외 보유 2026-09 말 기준');
 assert.ok(lines(m).includes('muted|1개월·12개월은 한 달 전·1년 전 월말 잔액과의 차(bn), 비중은 해외 전체 보유 대비입니다.'));
});

test('real charts.js: TIC end labels use the same integer bn as the totals line',()=>{
 const mk=tag=>{const e=new El(tag);e.clientWidth=600;e.classList={add(){},remove(){}};e.appendChild=c=>{e.kids.push(c);return c;};return e;};
 const doc={createElement:mk,createElementNS:(ns,t)=>mk(t),documentElement:{dataset:{motion:'off'}}};
 const sc={document:doc,requestAnimationFrame:f=>f(),addEventListener(){}};sc.window=sc;
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../site/charts.js'),'utf8'),sc);
 const {api,slot}=load({charts:sc.MacroCharts});
 api.render(supply(),tic());
 const svgs=tags(part(slot.kids[0],1),'svg');
 assert.equal(svgs.length,3);
 assert.ok(svgs[0].attrs['aria-label'].includes('해외 전체 9,241bn(2026-09-30)'),svgs[0].attrs['aria-label']);
 assert.ok(svgs[2].attrs['aria-label'].includes('한국 140bn(2026-09-30)'),svgs[2].attrs['aria-label']);
 assert.ok(svgs[0].attrs['aria-label'].includes('그중 해외 공적 3,675bn(2026-09-30)'));
 assert.deepEqual(walk(svgs[0],n=>n.attrs.class==='ch-end').map(n=>n.textContent).sort(),['3,675bn','9,241bn']);
 assert.deepEqual(tags(part(slot.kids[0],1),'figcaption').map(f=>f.textContent),['해외 보유 미 국채 — 전체와 해외 공적','나라별 보유','한국 보유']);
 // 주간 그래프의 끝 값도 줄과 같은 꼴(2,565bn — 천 단위 쉼표)
 assert.deepEqual(walk(part(slot.kids[0],0),n=>n.attrs.class==='ch-end').map(n=>n.textContent),['433bn','2,565bn']);
 // 나라 그래프 — 일본(1,063)과 영국(986)의 끝 값 글자는 겹쳐 영국 것이 빠진다(charts.js 규칙) → 아래 한 줄이 대신한다
 assert.deepEqual(walk(svgs[1],n=>n.attrs.class==='ch-end').map(n=>n.textContent),['1,063bn','564bn']);
 assert.ok(cls(part(slot.kids[0],1),'tic-ends')[0].textContent.includes('영국 986bn'));
});

test('the 10-year term premium guide no longer carries the supply numbers — one pointer line to the card',()=>{
 const src=[slice('function el(tag, attrs','const SVG_NS'),slice('const GUIDE = {','// 읽는 법의 흐름도 — 요인'),
  slice('function guideDetails(g)','let activeView'),'({ GUIDE, guideDetails })'].join('\n');
 const target=new El('h3');target.offsetParent={};
 let scrolled=0;target.scrollIntoView=()=>{scrolled++;};target.focus=()=>{};
 const document={createElement:t=>new El(t),getElementById:id=>id==='supply-title'?target:null};
 const g=vm.runInNewContext(src,{document,tpFlowFigure:()=>new El('figure')});
 assert.equal(g.GUIDE.term_premium.title,'읽는 법 — 흐름도 · Kim-Wright와 ACM');
 const det=g.guideDetails(g.GUIDE.term_premium), text=det.textContent;
 assert.equal(tags(det,'summary')[0].textContent,'읽는 법 — 흐름도 · Kim-Wright와 ACM');
 const ptr=cls(det,'guide-pointer');
 assert.equal(ptr.length,1);
 assert.equal(ptr[0].textContent,'흐름도에서 TFP로 가는 요인 가운데 둘(딜러 재고, 해외 공적 수요)의 숫자는 같은 묶음 아래 ‘미 국채 수급 — 딜러 재고 · 해외 보유’ 카드에 있습니다(판정에 쓰지 않음).');
 const a=tags(ptr[0],'a')[0];
 assert.equal(a.attrs.href,'#rates');
 // 흐름도 바로 뒤
 const kids=det.kids.filter(k=>k instanceof El);
 assert.equal(kids.indexOf(ptr[0]),kids.findIndex(k=>k.tag==='figure')+1);
 for(const w of ['수급 참고','딜러 국채 순포지션','supply-num','bn ·','WMTSECL1'])assert.ok(!text.includes(w)&&!JSON.stringify(walk(det,()=>true).map(n=>n.attrs)).includes(w),w);
 // 누르면 카드가 그려진 화면에서는 주소를 바꾸지 않고 카드 제목으로
 let prevented=0;a.listeners.click({preventDefault(){prevented++;}});
 assert.deepEqual([prevented,scrolled,target.attrs.tabindex],[1,1,'-1']);
 target.offsetParent=null;prevented=0;a.listeners.click({preventDefault(){prevented++;}});
 assert.equal(prevented,0);                                                // 카드가 없으면 금리·커브 화면으로(주소 그대로 따른다)
 // 페이지에는 옛 칸의 함수·변수가 남아 있지 않다
 for(const w of ['supplyPanel','supplySide','supplyData','SUPPLY_SIDES'])assert.ok(!HTML.includes(w),w);
});

test('the real data files render: the labels the page shows are the card’s own names, Korea is in the short table',()=>{
 // 지어낸 자료가 아니라 저장소의 data/tic.json · data/supply.json — 화면에 실제로 나가는 이름(자료 파일의 name)을 본다(2026-11-19 검토 반영)
 const read=f=>JSON.parse(fs.readFileSync(path.join(__dirname,'../data',f),'utf8'));
 const tj=read('tic.json'), sj=read('supply.json');
 const {api,slot}=load({now:Date.parse(tj.retrieved+'T03:00:00Z')});
 assert.equal(api.render(sj,tj),true);
 const m=part(slot.kids[0],1);
 if(!api.ticOk(tj)){assert.deepEqual(lines(m),['muted|자료 없음']);return;}
 const names=cls(m,'tic-total').map(p=>tags(p,'strong')[0].textContent);
 const want=[...api.TOTALS].filter(([k])=>tj.totals[k]&&typeof tj.totals[k].level_bn==='number').map(x=>x[1]);
 assert.deepEqual(names,want);                                                // 자료 파일의 이름 = 카드가 정해 둔 이름
 for(const [k,name] of api.TOTALS)if(tj.totals[k])assert.equal(tj.totals[k].name,name,k);
 assert.ok(!('share_pct' in (tj.totals.official_bills||{})));               // share_pct는 해외 전체 대비에만
 const short=tags(m,'table')[0];
 assert.equal(cls(short,'tic-korea').length,tj.korea?1:0);
 const ranks=tags(tags(short,'tbody')[0],'tr').map(r=>cells(r)[0]).filter(c=>/^\d+$/.test(c)).map(Number);
 assert.deepEqual(ranks.slice(0,10),[...ranks.slice(0,10)].sort((a,b)=>a-b));
 assert.ok(!/undefined|NaN|null|\[object/.test(slot.textContent));
 // 판정 낱말 — ⚠ 줄(운영자 메모 구절을 그대로 옮긴 자료 파일의 글)은 빼고 센다
 const flags=cls(slot,'supply-flag').map(n=>n.textContent);
 let text=slot.textContent;for(const f of flags)text=text.split(f).join('');
 for(const w of BANNED)assert.ok(!clean(text).includes(w),w);
});

test('the source file keeps the house rules: no markup sinks, no requests, no watched words',()=>{
 const code=SUPPLY.replace(/\/\*[\s\S]*?\*\//g,'').replace(/^\s*\/\/.*$/gm,'');
 for(const w of ['innerHTML','outerHTML','insertAdjacentHTML','eval(','new Function','fetch(','XMLHttpRequest','localStorage','location.',
  'createElement','style.','url(','navigator.','<script'])assert.ok(!code.includes(w),w);
 for(const w of BANNED)assert.ok(!clean(code).includes(w),w);
});

test("command words 'TIC' · '해외 보유' · '국채 수급' open the rates view and move to the card; bare '수급' stays on Korea flows",()=>{
 const start=HTML.indexOf('function go(text) {');assert.ok(start>0);
 let depth=0,end=start;
 for(let i=HTML.indexOf('{',start);i<HTML.length;i++){if(HTML[i]==='{')depth++;else if(HTML[i]==='}'&&--depth===0){end=i+1;break;}}
 const views=HTML.slice(HTML.indexOf('const VIEWS = ['),HTML.indexOf('];',HTML.indexOf('const VIEWS = ['))+2);
 const sc={location:{hash:''}};
 const api=vm.runInNewContext(views+'\nlet jumpTo = null;\n'+HTML.slice(start,end)+'\n({go, jump: () => jumpTo})',sc);
 for(const q of ['TIC','tic','해외 보유','국채 수급','미 국채 수급','국채 수급·해외 보유','딜러 재고',' 해외 보유 ']){
  sc.location.hash='';
  assert.equal(api.go(q),true,q);
  assert.equal(sc.location.hash,'rates',q);
  assert.deepEqual(Array.from(api.jump()),['supply-title'],q);
 }
 for(const [q,hash] of [['수급','korea-flows'],['수급·입찰','korea-flows'],['금리','rates'],['기록','ledger']]){
  sc.location.hash='';api.go(q);
  assert.equal(sc.location.hash,hash,q);
  assert.equal(api.jump(),null,q);
 }
 api.go('연표');assert.deepEqual(Array.from(api.jump()),['timeline-title','timeline-empty']);
 const list=HTML.slice(HTML.indexOf('<datalist id="cmd-list">'),HTML.indexOf('</datalist>'));
 assert.ok(list.includes('<option value="국채 수급·해외 보유">'));
});
