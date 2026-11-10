const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const scope={window:{},document:{addEventListener(){}},setInterval(){}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../site/korea.js'),'utf8'),scope);
const {health,oldObservation}=scope.window.KoreaMarket;
const now=Date.parse('2026-10-08T05:00:00Z'), expected=Date.parse('2026-10-07T22:17:00Z');
function fixture(){return {
 data:{checked_at:'2026-10-08T01:00:00Z',feeds:Object.fromEntries(['credit','money','rates','foreign3','foreign10','calendar','auctions','offerings','ktb_plans','ktb_ops','msb','msb_plans'].map(k=>[k,{ok:true}]))},
 run:{schema:1,state:'success',ok:true,started_at:'2026-10-08T00:59:00Z',checked_at:'2026-10-08T01:01:00Z'}
};}
test('current completed run is healthy',()=>{const {data,run}=fixture();assert.equal(health(data,run,expected,now).warning,false);});
test('old green JSON becomes late without a new collector run',()=>{const {data,run}=fixture();data.checked_at='2026-10-06T01:00:00Z';assert.equal(health(data,run,expected,now).late,true);});
test('failed run overrides previously green feed flags',()=>{const {data,run}=fixture();run.ok=false;run.state='failure';assert.match(health(data,run,expected,now).issue,/실패/);});
test('stuck running attempt is not reported as healthy',()=>{const {data,run}=fixture();run.ok=false;run.state='running';assert.match(health(data,run,expected,now).issue,/중단|지연/);});
test('missing run status and missing feeds warn',()=>{const {data}=fixture();delete data.feeds.rates;const result=health(data,null,expected,now);assert.equal(result.warning,true);assert.ok(result.failures.includes('rates'));});
test('successful status cannot bless an older snapshot',()=>{const {data,run}=fixture();run.started_at='2026-10-08T02:00:00Z';assert.match(health(data,run,expected,now).issue,/시각/);});
test('weekend uses last scheduled run, not a 24-hour freshness cutoff',()=>{const {data,run}=fixture();const sunday=Date.parse('2026-10-11T03:00:00Z');data.checked_at='2026-10-10T01:00:00Z';run.started_at='2026-10-10T00:59:00Z';run.checked_at='2026-10-10T01:01:00Z';assert.equal(health(data,run,Date.parse('2026-10-09T22:17:00Z'),sunday).warning,false);});
test('observation age is recalculated using Korean calendar dates',()=>{assert.equal(oldObservation('2026-10-01',now),false);assert.equal(oldObservation('2026-09-30',now),true);assert.equal(oldObservation('2026-10-09',now),true);});
test('partial run flags only the failed feed, not the whole Korea section',()=>{const {data,run}=fixture();run.state='partial';run.ok=false;data.feeds.offerings={ok:false,reason:'unreadable_notices'};const r=health(data,run,expected,now);assert.equal(r.issue,'');assert.deepEqual([...r.failures],['offerings']);assert.equal(r.warning,true);});
test('partial status must say ok false',()=>{const {data,run}=fixture();run.state='partial';run.ok=true;assert.match(health(data,run,expected,now).issue,/실패/);});
test('partial status cannot bless an older snapshot',()=>{const {data,run}=fixture();run.state='partial';run.ok=false;run.started_at='2026-10-08T02:00:00Z';assert.match(health(data,run,expected,now).issue,/시각/);});
test('unreadable notices are named after the feed that failed',()=>{const {failLabel}=scope.window.KoreaMarket;
 assert.equal(failLabel('auctions',{ok:false,reason:'unreadable_notices'}),'입찰 결과 공고 형식 확인 실패');
 assert.equal(failLabel('offerings',{ok:false,reason:'unreadable_notices'}),'발행공고 형식 확인 실패');
 assert.equal(failLabel('ktb_plans',{ok:false,reason:'unreadable_notices'}),'발행계획 보도자료 형식 확인 실패');
 assert.equal(failLabel('ktb_ops',{ok:false,reason:'unreadable_notices'}),'매입·교환 결과 공고 형식 확인 실패');
 assert.equal(failLabel('ktb_plans',{ok:false,reason:'stale'}),'관측일 지연');
 assert.equal(failLabel('auctions',{ok:false,reason:'timeout'}),'수신 시간 초과');assert.equal(failLabel('rates',{ok:false}),'수신 실패');});

// 국고채 발행계획·바이백 칸 — 아주 작은 가짜 DOM 위에서 render()를 돌려 글을 본다(숫자는 지어낸 것)
class El {
 constructor(tag){this.tag=tag;this.kids=[];this.attrs={};this.dataset={};this.style={};this.className='';this.hidden=false;}
 append(...xs){for(const x of xs)this.kids.push(typeof x==='string'?{text:x}:x);}
 replaceChildren(...xs){this.kids=[];this.append(...xs);}
 setAttribute(k,v){this.attrs[k]=String(v);}
 get textContent(){return this.kids.map(k=>k instanceof El?k.textContent:k.text).join('');}
 set textContent(v){this.kids=[{text:String(v)}];}
}
const walk=(n,f,out=[])=>{if(n instanceof El){if(f(n))out.push(n);n.kids.forEach(k=>walk(k,f,out));}return out;};
function renderWith(data,opts={}){
 const ids={};const doc={createElement:t=>new El(t),getElementById:id=>(ids[id]=ids[id]||new El('div')),querySelectorAll:()=>[],addEventListener(){}};
 const charts=[],chartOpts=[];
 const win=opts.noCharts?{}:{MacroCharts:{lineChart:(spec,o)=>{charts.push(spec);chartOpts.push(o);if(opts.chartThrows)throw new Error('x');return new El('figure');}}};
 const sc={window:win,document:doc,setInterval(){},URL};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../site/korea.js'),'utf8'),sc);
 sc.window.KoreaMarket.render(data,null);
 const root=ids['korea-market-content'];          // opts.title: 그 제목(h3)의 칸 — 일정·결과 칸과 지표 카드는 표식(dataset)이 없다
 const panel=opts.title ? walk(root,n=>n.tag==='article' && n.kids[0] instanceof El && n.kids[0].tag==='h3' && n.kids[0].textContent===opts.title)[0]
  : walk(root,n=>(opts.panel||'ktbIssuance') in n.dataset)[0];
 assert.ok(panel,opts.title||opts.panel||'ktbIssuance');
 return {panel,ids,text:panel.textContent,charts,chartOpts,links:walk(panel,n=>n.tag==='a').map(a=>a.href),
  anchors:walk(panel,n=>n.tag==='a').map(a=>[a.textContent,a.href]),
  notes:()=>walk(panel,n=>n.className==='reading-note').map(n=>n.textContent),
  rows:label=>{const t=walk(panel,n=>n.tag==='table'&&n.attrs['aria-label']===label)[0];assert.ok(t,label);return t.kids.find(k=>k.tag==='tbody').kids.map(tr=>tr.kids.map(td=>td.textContent));},
  deltas:()=>walk(panel,n=>n.className==='market-deltas')[0].kids.map(d=>d.kids.map(k=>k.textContent)),
  warnings:()=>walk(panel,n=>n.className==='market-warning').map(n=>n.textContent)};
}
function issuance(){
 const plan=(m,total,long,y30,actual)=>({id:'MOSF_'+m.replace('-',''),month:m,published:m+'-01',competitive_100m:total,
   tenors:[{tenor:'3년',amount_100m:total-long},{tenor:'30년',amount_100m:long}],long_share_pct:long_share(long,total),y30_share_pct:y30,
   stated_prev_change_100m:null,stated_plan_change_100m:null,buyback_plan:null,exchange_plan:null,
   prev_actual:actual?{month:actual[0],amount_100m:actual[1]}:null,source_url:'https://mofe.go.kr/nw/nes/detailNesDtaView.do?searchNttId1=X'});
 const long_share=(l,t)=>Math.round(l/t*1000)/10;
 const plans=[plan('2030-04',150000,40000,26.7,['2030-03',170000]),plan('2030-05',140000,30000,21.4,['2030-04',151230])];
 plans[1].stated_plan_change_100m=-20000; plans[1].buyback_plan={amount_100m:22000,dates:['2030-05-15']};
 return {schema:1,checked_at:'2030-05-20T01:00:00Z',cards:[],notices:[],calendar:null,auctions:[],offerings:[],
   feeds:Object.fromEntries(['credit','money','rates','foreign3','foreign10','calendar','auctions','offerings','ktb_plans','ktb_ops','msb','msb_plans'].map(k=>[k,{ok:true}])),
   ktb_plans:plans,ktb_ops:[{id:'MOSF_9',kind:'buyback',date:'2030-05-15',offered_100m:22000,bids_100m:55000,bid_cover_pct:250,awarded_100m:22000,
     source_url:'https://mofe.go.kr/st/fnancstats/updateTbFnancstatsView.do?searchSn=MOSF_9'},
     {id:'MOSF_8',kind:'exchange',date:'2030-05-14',offered_100m:3000,bids_100m:7500,bid_cover_pct:250,awarded_100m:3000,source_url:'https://evil.invalid/x'}],
   ktb_summary:{latest_month:'2030-05',prev_month_change_100m:-10000,progress:{year:2030,months:['2030-03','2030-04'],through:'2030-04',missing:['2030-01','2030-02'],
     actual_100m:321230,limit_100m:null,limit_published:null,limit_source_url:null,pct:null}}};
}
test('issuance panel shows plan, mix, computed changes and operations',()=>{
 const {text,charts,links}=renderWith(issuance());
 for(const want of ['2030년 5월 계획','14.0조원','-1.0조원 (계산값)','-2.0조원','21.4%','30년','매입(바이백) 계획 2.2조원 (2030-05-15)','교환 계획: 보도자료에 계획 없음',
   '2030-05-15','매입','250.0%','교환','연간 한도 미등록','이 사이트의 규칙 판정에 쓰지 않는 참고 자료입니다.','재정경제부',
   '2030년 5월 매입(바이백) 계획','2030년 보도자료 발행 규모 합계 32.123조원','재정경제부가 밝힌 누계와 다를 수 있습니다'])
  assert.ok(text.includes(want),want);
 assert.ok(!text.includes('이달'));assert.ok(!text.includes('발행 실적 누계'));
 assert.equal(charts.length,1);assert.equal(JSON.stringify(charts[0].lines.map(l=>[l.key,l.points])),JSON.stringify([['long',[['2030-04-01',26.7],['2030-05-01',21.4]]],['y30',[['2030-04-01',26.7],['2030-05-01',21.4]]]]));
 assert.ok(links.every(h=>new URL(h).hostname==='mofe.go.kr'),links.join(' '));          // 허용 밖 주소는 글자로만
 assert.ok(!/판정(?!에 쓰지)|신호|경보|충족|⚠|축소|확대/.test(text));
});
test('issuance panel: registered limit shows a ratio only without missing months',()=>{
 const d=issuance();Object.assign(d.ktb_summary.progress,{limit_100m:2000000,limit_published:'2029-12-20',limit_source_url:'https://mofe.go.kr/x'});
 let r=renderWith(d);assert.ok(r.text.includes('연간 한도 200.0조원'));assert.ok(r.text.includes('2030년 1월, 2030년 2월'));assert.ok(!r.text.includes('200.0조원 대비'));
 Object.assign(d.ktb_summary.progress,{missing:[],months:['2030-01','2030-02','2030-03','2030-04'],pct:40});
 r=renderWith(d);assert.ok(r.text.includes('연간 한도 200.0조원 대비 40.0% (계산값)'));
});
test('issuance panel survives malformed rows',()=>{
 const d=issuance();d.ktb_summary.progress={year:2030};d.ktb_plans[1].tenors=[null,{tenor:'2년',amount_100m:1}];d.ktb_plans[1].buyback_plan={amount_100m:1,dates:'x'};
 const {text}=renderWith(d);assert.ok(text.includes('발행 실적이 적힌 보도자료를 아직 확인하지 못했습니다.'));assert.ok(text.includes('2년'));
});
test('issuance panel survives missing or failed feeds',()=>{
 const d=issuance();delete d.ktb_plans;delete d.ktb_ops;delete d.ktb_summary;d.feeds.ktb_plans={ok:false,reason:'timeout'};
 const {text,charts}=renderWith(d);
 for(const want of ['국고채 발행계획: 수신 시간 초과 · 마지막 성공 자료','확인된 발행계획이 없습니다.','확인된 매입·교환 결과가 없습니다.','발행 실적이 적힌 보도자료를 아직 확인하지 못했습니다.'])
  assert.ok(text.includes(want),want);
 assert.equal(charts.length,0);
});

test('issuance panel: cells of each table and the three deltas',()=>{
 const r=renderWith(issuance());
 assert.deepEqual(r.rows('2030년 5월 만기별 경쟁입찰 계획'),[['3년','11.0조원','78.6%'],['30년','3.0조원','21.4%']]);
 assert.deepEqual(r.rows('최근 국고채 매입·교환 입찰 결과'),[['2030-05-15','매입','2.2조원','250.0%','2.2조원','결과'],['2030-05-14','교환','0.3조원','250.0%','0.3조원','결과']]);
 assert.deepEqual(r.deltas(),[['전월 계획 대비','-1.0조원 (계산값)'],['당초 계획 대비(보도자료)','-2.0조원'],['20·30·50년 비중 · 30년','21.4% · 21.4%']]);
 assert.ok(!r.warnings().some(w=>w.includes('읽지 못했습니다')));
});
test('issuance panel: amounts keep every 억 and shares keep one decimal',()=>{
 const d=issuance();d.ktb_summary.prev_month_change_100m=400;d.ktb_plans[1].stated_plan_change_100m=-1450;d.ktb_plans[1].y30_share_pct=15;
 d.ktb_ops[0].offered_100m=1500;d.ktb_ops[0].awarded_100m=1450;
 const r=renderWith(d);
 assert.deepEqual(r.deltas(),[['전월 계획 대비','+0.04조원 (계산값)'],['당초 계획 대비(보도자료)','-0.145조원'],['20·30·50년 비중 · 30년','21.4% · 15.0%']]);
 assert.deepEqual(r.rows('최근 국고채 매입·교환 입찰 결과')[0].slice(2,5),['0.15조원','250.0%','0.145조원']);
});
test('issuance panel: stated fallbacks are labelled by where the number came from',()=>{
 const d=issuance();delete d.ktb_summary.prev_month_change_100m;d.ktb_plans[1].stated_prev_change_100m=5000;d.ktb_plans[1].stated_plan_change_100m=null;
 let r=renderWith(d);
 assert.deepEqual(r.deltas().slice(0,2),[['전월 대비(보도자료 문구)','+0.5조원'],['당초 계획 대비(보도자료)','보도자료에서 확인되지 않음']]);
 assert.ok(!r.text.includes('전월 계획 대비'));
 d.ktb_plans[1].stated_plan_change_unread=true;r=renderWith(d);
 assert.equal(r.deltas()[1][1],'문구를 읽지 못함 — 원문 확인');
 assert.ok(r.links.includes('https://mofe.go.kr/nw/nes/detailNesDtaView.do?searchNttId1=X'));
 d.ktb_plans[1].stated_prev_change_100m=null;r=renderWith(d);assert.deepEqual(r.deltas()[0],['전월 계획 대비','전월 계획 없음']);
});
test('issuance panel: unread operation notices exclude not_tried and ids still shown',()=>{
 const d=issuance();d.feeds.ktb_ops.skipped=[{id:'MOSF_7',reason:'field_changed'},{id:'MOSF_9',reason:'timeout'},{id:'MOSF_6',reason:'not_tried'}];
 assert.ok(renderWith(d).warnings().includes('매입·교환 결과 공고 1건을 읽지 못했습니다. 원문은 공식 결과 목록에서 확인해 주세요.'));
});
test('issuance panel: unread plan notices exclude not_tried and months still shown',()=>{
 const d=issuance();d.feeds.ktb_plans={ok:true,skipped:[{id:'MOSF_new',reason:'field_changed'},{id:'MOSF_203005',reason:'parse'},{id:'x',reason:'not_tried'}]};
 assert.ok(renderWith(d).warnings().includes('발행계획 보도자료 1건을 읽지 못했습니다. 원문은 보도자료 목록에서 확인해 주세요.'));
 d.feeds.ktb_plans.skipped=[{id:'MOSF_203005',reason:'network'}];
 assert.ok(!renderWith(d).warnings().some(w=>w.includes('읽지 못했습니다')));
});
test('issuance panel: chart failure, a single month and a missing chart helper',()=>{
 assert.ok(renderWith(issuance(),{chartThrows:true}).text.includes('차트를 표시하지 못했습니다'));
 const d=issuance();d.ktb_plans=[d.ktb_plans[1]];let r=renderWith(d);assert.equal(r.charts.length,0);assert.ok(r.text.includes('두 달 이상 자료가 모이면'));
 r=renderWith(issuance(),{noCharts:true});assert.ok(!r.text.includes('두 달 이상 자료가 모이면'));assert.ok(!r.text.includes('차트를 표시하지 못했습니다'));
});
test('issuance panel: progress track is labelled and clamped',()=>{
 const d=issuance();Object.assign(d.ktb_summary.progress,{limit_100m:2000000,limit_published:'2029-12-20',limit_source_url:'https://mofe.go.kr/x',missing:[],pct:140});
 const {panel}=renderWith(d);const t=walk(panel,n=>n.className==='range-track')[0];
 assert.equal(t.attrs.role,'img');assert.equal(t.attrs['aria-label'],'연간 한도 대비 보도자료 발행 규모 합계 140.0%');assert.equal(t.kids[0].style.left,'100%');
});
test('issuance panel: closing note names the computed numbers by which prev-month row is shown',()=>{
 const calc='비중·전월 대비·합계는 이 사이트의 계산값입니다.';
 const stated='비중·합계는 이 사이트의 계산값이고, 전월 대비(보도자료 문구)는 보도자료에 적힌 숫자입니다.';
 let r=renderWith(issuance());
 assert.ok(r.notes().some(n=>n.endsWith(calc)));assert.ok(!r.text.includes(stated));
 const d=issuance();delete d.ktb_summary.prev_month_change_100m;d.ktb_plans[1].stated_prev_change_100m=5000;
 r=renderWith(d);assert.equal(r.deltas()[0][0],'전월 대비(보도자료 문구)');
 assert.ok(r.notes().some(n=>n.endsWith(stated)));assert.ok(!r.text.includes(calc));
});
test('issuance panel: an empty result list per kind is its own warning, not a notice count',()=>{
 const d=issuance();d.feeds.ktb_ops.skipped=[{id:'exchange',reason:'no_notices'}];
 let w=renderWith(d).warnings();
 assert.ok(w.includes('교환 입찰 결과 목록에서 공고를 찾지 못했습니다(목록 형식 확인 필요).'),w.join('|'));
 assert.ok(!w.some(x=>x.includes('건을 읽지 못했습니다')),w.join('|'));
 d.feeds.ktb_ops.skipped=[{id:'buyback',reason:'no_notices'},{id:'MOSF_7',reason:'field_changed'}];
 w=renderWith(d).warnings();
 assert.ok(w.includes('매입 입찰 결과 목록에서 공고를 찾지 못했습니다(목록 형식 확인 필요).'),w.join('|'));
 assert.ok(!w.some(x=>x.startsWith('교환 입찰 결과 목록')));
 assert.ok(w.includes('매입·교환 결과 공고 1건을 읽지 못했습니다. 원문은 공식 결과 목록에서 확인해 주세요.'),w.join('|'));
});
test('issuance panel: only a boolean true marks the 당초 wording as unread',()=>{
 for(const v of ['false',1,'true',{}]){
  const d=issuance();d.ktb_plans[1].stated_plan_change_100m=null;d.ktb_plans[1].stated_plan_change_unread=v;
  assert.deepEqual(renderWith(d).deltas()[1],['당초 계획 대비(보도자료)','보도자료에서 확인되지 않음'],String(v));
 }
});
test('issuance panel: the unread 당초 row links its own 원문 확인',()=>{
 const d=issuance();d.ktb_plans[1].stated_plan_change_100m=null;d.ktb_plans[1].stated_plan_change_unread=true;
 d.ktb_plans[1].source_url='https://mofe.go.kr/nw/nes/detailNesDtaView.do?searchNttId1=Y';
 const r=renderWith(d);
 assert.deepEqual(r.anchors.filter(a=>a[0]==='원문 확인'),[['원문 확인','https://mofe.go.kr/nw/nes/detailNesDtaView.do?searchNttId1=Y']].concat(  // 칸 + 월별 표의 그 달
  [['원문 확인','https://mofe.go.kr/nw/nes/detailNesDtaView.do?searchNttId1=Y']]));
 const row=walk(r.panel,n=>n.className==='market-deltas')[0].kids[1];
 assert.deepEqual(walk(row,n=>n.tag==='a').map(a=>a.href),['https://mofe.go.kr/nw/nes/detailNesDtaView.do?searchNttId1=Y']);
});
test('issuance panel: a computed prev-month change wins over the stated one, with its own label',()=>{
 const d=issuance();d.ktb_plans[1].stated_prev_change_100m=5000;          // 계산값 -1.0조원과 다른 보도자료 문구 +0.5조원
 const r=renderWith(d);
 assert.deepEqual(r.deltas()[0],['전월 계획 대비','-1.0조원 (계산값)']);
 assert.ok(!r.text.includes('전월 대비(보도자료 문구)'));assert.ok(!r.text.includes('+0.5조원'));
});
test('issuance panel: limit source, plan source and release date are shown',()=>{
 const d=issuance();Object.assign(d.ktb_summary.progress,{limit_100m:2000000,limit_published:'2029-12-20',limit_source_url:'https://mofe.go.kr/limit'});
 d.ktb_plans[1].published='2030-04-25';
 const r=renderWith(d);
 assert.ok(r.anchors.some(a=>a[0]==='2030년 국고채 발행계획 보도자료(2029-12-20)' && a[1]==='https://mofe.go.kr/limit'),JSON.stringify(r.anchors));
 assert.ok(r.anchors.some(a=>a[0]==='2030년 5월 계획 원문' && a[1]==='https://mofe.go.kr/nw/nes/detailNesDtaView.do?searchNttId1=X'),JSON.stringify(r.anchors));
 assert.ok(walk(r.panel,n=>n.className==='muted').some(n=>n.textContent==='2030년 5월 계획 · 보도자료 2030-04-25'));
});
test('issuance panel: chart values use the same one-decimal percent as the panel',()=>{
 const r=renderWith(issuance());
 assert.equal(r.chartOpts.length,1);
 assert.equal(r.chartOpts[0].format(25.8),'25.8%');assert.equal(r.chartOpts[0].format(26),'26.0%');
 // 실제 charts.js: format을 주면 끝 값·읽기 글이 그 꼴, 주지 않으면 전과 같은 소수 두 자리
 const draw=format=>{
  const mk=tag=>{const e=new El(tag);e.addEventListener=()=>{};e.clientWidth=600;e.classList={add(){},remove(){}};return e;};
  const doc={createElement:mk,createElementNS:(ns,t)=>mk(t),documentElement:{dataset:{motion:'off'}}};
  const sc={document:doc,requestAnimationFrame:f=>f(),addEventListener(){}};sc.window=sc;const w=sc;vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../site/charts.js'),'utf8'),sc);
  const spec={key:'k',title:'t',unit:'%',zero:true,threshold:null,years:1,lines:[{key:'a',label:'a',role:'series',points:[['2030-04-01',26.7],['2030-05-01',25.8]],series:[]}]};
  const fig=w.MacroCharts.lineChart(spec,format?{height:170,format}:{height:170});
  const svgEl=walk(fig,n=>n.tag==='svg')[0];
  return [svgEl.attrs['aria-label'],walk(svgEl,n=>n.attrs.class==='ch-end').map(n=>n.textContent)];
 };
 let [aria,ends]=draw(r.chartOpts[0].format);
 assert.ok(aria.includes('a 25.8%(2030-05-01)'),aria);assert.deepEqual(ends,['25.8%']);
 [aria,ends]=draw(null);
 assert.ok(aria.includes('a 25.80%(2030-05-01)'),aria);assert.deepEqual(ends,['25.80%']);
});
const MONTHS='월별 경쟁입찰 계획·장기물 비중·매입 계획';
test('issuance panel: month table, newest first, with 당초 and buyback plan',()=>{
 const r=renderWith(issuance());
 assert.deepEqual(r.rows(MONTHS),[['2030-05','14.0','-2.0','21.4%','2.2 (05-15)'],['2030-04','15.0','—','26.7%','—']]);
 const t=walk(r.panel,n=>n.tag==='table'&&n.attrs['aria-label']===MONTHS)[0];
 assert.deepEqual(walk(t,n=>n.tag==='th').map(n=>n.textContent),['월','경쟁입찰 계획(조원)','당초 대비(보도자료)','20·30·50년 비중','매입 계획(조원, 날짜)']);
 assert.equal(walk(r.panel,n=>n.className==='market-scroll'&&n.kids[0]===t).length,1);     // 좁은 화면에서 옆으로 밀리는 틀 안
 const d=issuance();d.ktb_plans[0].stated_plan_change_100m=1450;d.ktb_plans[0].long_share_pct=26;
 d.ktb_plans[0].buyback_plan={amount_100m:5000,dates:['2030-04-08','2030-04-22']};d.ktb_plans[1].competitive_100m=null;d.ktb_plans[1].long_share_pct=null;
 assert.deepEqual(renderWith(d).rows(MONTHS),[['2030-05','—','-2.0','—','2.2 (05-15)'],['2030-04','15.0','+0.145','26.0%','0.5 (04-08, 04-22)']]);
 assert.ok(!/undefined|NaN|null/.test(renderWith(d).text));
});
test('issuance panel: month table — unread 당초 links its own release, anything else is a dash',()=>{
 const d=issuance();d.ktb_plans[0].stated_plan_change_unread=true;d.ktb_plans[0].source_url='https://mofe.go.kr/nw/nes/detailNesDtaView.do?searchNttId1=APR';
 let r=renderWith(d);
 assert.deepEqual(r.rows(MONTHS).map(row=>row[2]),['-2.0','원문 확인']);
 const t=walk(r.panel,n=>n.tag==='table'&&n.attrs['aria-label']===MONTHS)[0];
 assert.deepEqual(walk(t,n=>n.tag==='a').map(a=>a.href),['https://mofe.go.kr/nw/nes/detailNesDtaView.do?searchNttId1=APR']);
 for(const v of ['true',1,{},false]){d.ktb_plans[0].stated_plan_change_unread=v;assert.equal(renderWith(d).rows(MONTHS)[1][2],'—',String(v));}
});
test('chart table view: one-decimal percent only for a chart given opts.format',()=>{
 const r=renderWith(issuance());
 const open=format=>{
  const mk=tag=>{const e=new El(tag);e.on={};e.addEventListener=(k,f)=>{e.on[k]=f;};e.clientWidth=600;e.classList={add(){},remove(){}};return e;};
  const doc={createElement:mk,createElementNS:(ns,t)=>mk(t),documentElement:{dataset:{motion:'off'}}};
  const sc={document:doc,requestAnimationFrame:f=>f(),addEventListener(){}};sc.window=sc;vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../site/charts.js'),'utf8'),sc);
  const spec={key:'k',title:'t',unit:'%',zero:true,threshold:null,years:1,lines:[{key:'a',label:'a',role:'series',points:[['2030-04-01',26.7],['2030-05-01',25.8]],series:[]}]};
  const fig=sc.MacroCharts.lineChart(spec,format?{height:170,format}:{height:170});
  const det=walk(fig,n=>n.tag==='details')[0];det.open=true;det.on.toggle();
  const tb=walk(det,n=>n.tag==='table')[0];
  return [walk(tb,n=>n.tag==='th').map(n=>n.textContent),walk(tb,n=>n.tag==='td').map(n=>n.textContent)];
 };
 assert.deepEqual(open(r.chartOpts[0].format),[['날짜','a'],['2030-05-01','25.8%','2030-04-01','26.7%']]);
 assert.deepEqual(open(null),[['날짜','a (%)'],['2030-05-01','25.800','2030-04-01','26.700']]);    // 다른 그래프는 그대로
});

// 통화안정증권 경쟁입찰 결과 칸 — 숫자는 지어낸 것
function msbData(){
 const d=issuance();
 const r=(id,date,tenor,kind,rate,offered,bids,awarded)=>({id,date,tenor,offered_100m:offered,bids_100m:bids,bidders:12,awarded_100m:awarded,rate_kind:kind,rate_pct:rate,
   bid_cover_pct:Math.round(bids/offered*1000)/10,source_url:'https://www.bok.or.kr/portal/bbs/P0001773/view.do?nttId='+id+'&menuNo=200295'});
 d.msb=[r('905','2030-05-15','1년','yield',3.51,7000,5200,4500),r('904','2030-05-13','91일','discount',3.175,6000,2300,1900),
   r('903','2030-05-08','2년','yield',3.86,25000,32500,21800),r('902','2030-05-06','91일','discount',3.2,6000,9000,6000),
   Object.assign(r('901','2030-04-29','91일','discount',3.19,6000,9500,6000),{source_url:'https://evil.invalid/x'})];
 d.msb_summary={months:[{month:'2030-05',count:4,offered_100m:44000,bids_100m:49000,awarded_100m:34200,short:2,through:'2030-05-15'},
   {month:'2030-04',count:7,offered_100m:60000,bids_100m:90000,awarded_100m:58000,short:0,through:'<b>x</b>'}]};
 d.feeds.msb={ok:true,skipped:[]};
 d.msb_plans=[{id:'801',month:'2030-05',published:'2030-04-25',total_100m:66000,competitive_100m:60000,offer_min_100m:5000,offer_max_100m:6000,
   redemption_100m:13000,redemption_unread:false,source_url:'https://www.bok.or.kr/portal/bbs/P0001773/view.do?nttId=801&menuNo=200295'},
   {id:'800',month:'2030-03',published:'2030-02-26',total_100m:65000,competitive_100m:60000,offer_min_100m:5000,offer_max_100m:5000,
   redemption_100m:null,redemption_unread:true,source_url:'https://www.bok.or.kr/portal/bbs/P0001773/view.do?nttId=800&menuNo=200295'},
   null,{month:'bad'}];
 d.feeds.msb_plans={ok:true,skipped:[]};
 return d;
}
test('msb panel: table, per-tenor chart, month sums and source',()=>{
 const r=renderWith(msbData(),{panel:'msb'});
 const J=JSON.stringify;
 assert.equal(J(r.rows('최근 통화안정증권 경쟁입찰 결과')[0]),J(['2030-05-15','1년','0.70조원','0.52조원','74.3%','0.45조원','3.510% (수익률)','결과']));
 assert.equal(J(r.rows('최근 통화안정증권 경쟁입찰 결과')[1]),J(['2030-05-13','91일','0.60조원','0.23조원','38.3%','0.19조원','3.175% (할인율)','결과']));
 assert.equal(J(r.rows('달마다 통화안정증권 경쟁입찰 합계')),J([['2030년 5월 (05-15까지)','4회','6.0조원','4.40조원','4.90조원','3.42조원','2회'],['2030년 4월','7회','—','6.00조원','9.00조원','5.80조원','0회']]));   // 꼴이 다른 through는 붙이지 않는다 · 계획이 없는 달은 —
 const chart=r.charts.find(c=>c.key==='msb_rates');
 assert.equal(J(chart.lines.map(l=>[l.label,l.points])),J([['91일 할인율',[['2030-04-29',3.19],['2030-05-06',3.2],['2030-05-13',3.175]]]]));   // 두 번 미만인 만기는 뺀다
 assert.equal(r.chartOpts[r.charts.indexOf(chart)].format(3.2),'3.200%');
 assert.ok(r.links.every(h=>new URL(h).hostname==='www.bok.or.kr'),r.links.join(' '));       // 허용 밖 주소는 글자로만
 assert.ok(r.links.some(h=>h.startsWith('https://www.bok.or.kr/portal/singl/newsData/list.do?menuNo=200295')));
 for(const want of ['낙찰할인율','낙찰수익률','응찰액÷발행예정액','이 사이트의 규칙 판정에 쓰지 않는 참고 자료입니다.','자료: 한국은행 '])assert.ok(r.text.includes(want),want);
 assert.ok(!/판정(?!에 쓰지)|신호|경보|충족|⚠|축소|확대|부진|호조|우려/.test(r.text));
 assert.equal(J(r.warnings().filter(w=>!w.includes('예정된 한국 자료 갱신'))),'[]');      // 이 고정 자료는 날짜가 지나 갱신 지연 안내가 붙는다
});
test('msb panel: unread notices, failed feed and empty data',()=>{
 let d=msbData();d.feeds.msb={ok:true,skipped:[{id:'906',reason:'rate_kind'},{id:'905',reason:'network'},{id:'907',reason:'not_tried'}]};
 let r=renderWith(d,{panel:'msb'});
 assert.equal(JSON.stringify(r.warnings().filter(w=>!w.includes('예정된 한국 자료 갱신'))),JSON.stringify(['통화안정증권 결과 공고 1건을 읽지 못했습니다. 원문은 한국은행 공개시장운영 공지에서 확인해 주세요.']));
 d=msbData();d.feeds.msb={ok:false,reason:'unreadable_notices'};r=renderWith(d,{panel:'msb'});
 assert.ok(r.warnings().includes('통안증권 입찰 결과: 통화안정증권 결과 공고 형식 확인 실패 · 마지막 성공 자료'));
 d=msbData();delete d.msb;delete d.msb_summary;d.feeds.msb={ok:false,reason:'stale'};r=renderWith(d,{panel:'msb',noCharts:true});
 assert.ok(r.text.includes('확인된 통화안정증권 입찰 결과가 없습니다.'));assert.ok(r.text.includes('관측일 지연 · 마지막 성공 자료'));
 d=msbData();d.msb.push(null,{date:'x'},{tenor:'1년'});d.msb_summary={months:'x'};r=renderWith(d,{panel:'msb',chartThrows:true});
 assert.equal(r.rows('최근 통화안정증권 경쟁입찰 결과').length,5);assert.ok(r.text.includes('차트를 표시하지 못했습니다'));
});
test('health: a failed msb feed lights only that feed',()=>{
 const {data,run}=fixture();run.state='partial';run.ok=false;data.feeds.msb={ok:false,reason:'stale'};
 const r=health(data,run,expected,now);assert.equal(JSON.stringify([...r.failures]),'["msb"]');assert.equal(r.issue,'');
});

test('msb panel: latest plan, plan versus awarded, plan table',()=>{
 const r=renderWith(msbData(),{panel:'msb'}), J=JSON.stringify;
 for(const want of ['통화안정증권 발행 계획·입찰 결과','2030년 5월 발행 계획 · 2030-04-25 공고','6.6조원','발행 계획(모집 최대 기준)','경쟁입찰 계획6.0조원','모집 계획0.5~0.6조원','중도환매 예정1.3조원',
   '2030년 5월 낙찰액 합 3.42조원 — 경쟁입찰 계획 6.0조원의 57.0% (05-15까지, 계산값)','중도환매는 만기 전의 통화안정증권을 한국은행이 되사는 것입니다.'])
  assert.ok(r.text.includes(want),want);
 assert.equal(J(r.rows('달마다 통화안정증권 발행 계획')),J([['2030년 5월','6.6조원','6.0조원','0.5~0.6조원','1.3조원','계획'],['2030년 3월','6.5조원','6.0조원','0.5조원','원문 확인','계획']]));
 assert.ok(r.anchors.some(([t,h])=>t==='원문 확인' && h.endsWith('nttId=800&menuNo=200295')));
 assert.ok(r.links.some(h=>h.includes('searchKwd=%ED%86%B5%ED%99%94%EC%95%88%EC%A0%95%EC%A6%9D%EA%B6%8C+%EB%B0%9C%ED%96%89+%EA%B3%84%ED%9A%8D')));
 assert.ok(!/판정(?!에 쓰지)|신호|경보|충족|⚠|축소|확대|부진|호조|우려/.test(r.text));
});
test('msb panel: plan feed failure, unread plans, no plans, no redemption table',()=>{
 let d=msbData();d.feeds.msb_plans={ok:false,reason:'unreadable_notices',skipped:[{id:'802',reason:'sum_mismatch'},{id:'801',reason:'network'},{id:'803',reason:'not_tried'}]};
 let r=renderWith(d,{panel:'msb'});
 assert.ok(r.warnings().includes('통안증권 발행계획: 통화안정증권 발행 계획 형식 확인 실패 · 마지막 성공 자료'),r.warnings().join('|'));
 assert.ok(r.warnings().includes('통화안정증권 발행 계획 공고 1건을 읽지 못했습니다. 원문은 한국은행 공개시장운영 공지에서 확인해 주세요.'));
 d=msbData();delete d.msb_plans;r=renderWith(d,{panel:'msb'});
 assert.ok(r.text.includes('확인된 통화안정증권 발행 계획이 없습니다.'));assert.ok(!r.text.includes('낙찰액 합 3.42조원 —'));
 d=msbData();d.msb_plans[0].redemption_100m=null;r=renderWith(d,{panel:'msb'});
 assert.ok(r.text.includes('중도환매 예정계획에 없음'));
 d=msbData();d.msb_plans[0].month='2030-06';d.msb_plans[0].competitive_100m=0;r=renderWith(d,{panel:'msb'});   // 이번 달 계획이 없으면 견주지 않는다
 assert.ok(!r.text.includes('경쟁입찰 계획 6.0조원의'));
});

// 국고채 입찰 일정·결과 칸 — 숫자는 지어낸 것. 같은 날·같은 만기 공고 둘(한 만기 두 종목, 2026-11-09 3년 같은 꼴)
function schedule(){
 const d=issuance();
 const res=(id,date,tenor,amt,cover,y)=>({id,date,tenor,offered_100m:amt,awarded_100m:amt,bid_cover_pct:cover,yield_pct:y,
   source_url:'https://mofe.go.kr/st/fnancstats/updateTbFnancstatsView.do?searchSn='+id});
 const off=(id,date,tenor,amt)=>({id,date,tenor,offered_100m:amt,source_url:'https://www.bok.or.kr/portal/bbs/P0001794/view.do?nttId='+id+'&menuNo=200364'});
 d.calendar={month:'2030-05',source_url:'https://ktb.mofe.go.kr/mnbyIsuCldr.do',
   rows:[{date:'2030-05-06',tenor:'3년'},{date:'2030-05-07',tenor:'10년'},{date:'2030-05-08',tenor:'5년'},{date:'2030-05-12',tenor:'20년'}]};
 d.auctions=[res('MOSF_A2','2030-05-07','10년',9000,280,3.9),res('MOSF_A1','2030-05-06','3년',11000,321.3,3.645),res('MOSF_A0','2030-05-06','3년',11000,303,3.65)];
 d.offerings=[off('103','2030-05-08','5년',12000),off('103','2030-05-08','5년',12000),off('102','2030-05-07','10년',9000),
   off('101','2030-05-07','10년',8000),off('100','2030-05-06','3년',11000),off('99','2030-05-06','3년',11000)];
 return d;
}
const SCHEDULE='국고채 월별 입찰 일정';
test('schedule: notices of the same date and tenor are added, each amount linked to its own notice',()=>{
 const r=renderWith(schedule(),{title:'국고채 입찰 일정'});
 assert.deepEqual(r.rows(SCHEDULE),[
  ['2030-05-06','3년','22,000억원 (2건: 11,000억원 + 11,000억원)'],   // 결과 둘 = 발행공고 둘 → 결과
  ['2030-05-07','10년','17,000억원 (2건: 9,000억원 + 8,000억원)'],     // 결과 하나 < 발행공고 둘 → 발행공고
  ['2030-05-08','5년','12,000억원'],                                     // 같은 공고 번호는 한 번만
  ['2030-05-12','20년','공고 확인']]);
 const t=walk(r.panel,n=>n.tag==='table'&&n.attrs['aria-label']===SCHEDULE)[0];
 const hrefs=t.kids.find(k=>k.tag==='tbody').kids.map(tr=>walk(tr,n=>n.tag==='a').map(a=>a.href.replace(/^.*(searchSn=|nttId=)/,'').replace(/&menuNo=\d+$/,'')));
 assert.deepEqual(hrefs,[['MOSF_A1','MOSF_A0'],['102','101'],['103'],['https://ktb.mofe.go.kr/isuNdReprchsPblanc.do']]);
});
test('schedule: a correction notice for the same bond (same code) is not added — the later notice only',()=>{
 const d=schedule(), code=(o,c)=>Object.assign(o,{code:c});
 d.auctions=[];                                                            // 결과 없음 — 발행공고 금액
 d.offerings=[code(d.offerings[4],'03000-2909-0300'),code(d.offerings[5],'02750-2903-0300'),
   code({...d.offerings[4],id:'105',offered_100m:12000,source_url:d.offerings[4].source_url.replace('100','105')},'03000-2909-0300'),
   code(d.offerings[2],'03250-3606-1000'),code({...d.offerings[3],id:'98'},'03250-3606-1000'),d.offerings[0]];
 const r=renderWith(d,{title:'국고채 입찰 일정'});
 assert.deepEqual(r.rows(SCHEDULE).slice(0,3),[
  ['2030-05-06','3년','23,000억원 (2건: 11,000억원 + 12,000억원)'],   // 두 종목 — 03000 종목은 정정 공고(105)만
  ['2030-05-07','10년','9,000억원'],                                     // 같은 종목의 공고 둘(102·98) — 번호가 큰 102만
  ['2030-05-08','5년','12,000억원']]);
 const t=walk(r.panel,n=>n.tag==='table'&&n.attrs['aria-label']===SCHEDULE)[0];
 const hrefs=t.kids.find(k=>k.tag==='tbody').kids.slice(0,2).map(tr=>walk(tr,n=>n.tag==='a').map(a=>a.href.replace(/^.*nttId=/,'').replace(/&menuNo=\d+$/,'')));
 assert.deepEqual(hrefs,[['99','105'],['102']]);
});
test('schedule: one shared delay note for both amount feeds, two different failures both shown',()=>{
 let d=schedule(), r=renderWith(d,{title:'국고채 입찰 일정'});            // 이 고정 자료는 날짜가 지나 갱신 지연 안내가 붙는다
 assert.deepEqual(r.warnings(),['입찰금액: 예정된 한국 자료 갱신이 반영되지 않았습니다 · 자료일 확인']);
 d.feeds.offerings={ok:false,reason:'timeout'};d.feeds.auctions={ok:false,reason:'unreadable_notices'};r=renderWith(d,{title:'국고채 입찰 일정'});
 assert.deepEqual(r.warnings(),['입찰금액: 수신 시간 초과 · 마지막 성공 자료 · 입찰 결과 공고 형식 확인 실패 · 마지막 성공 자료']);
 d=schedule();d.feeds.offerings={ok:true,skipped:[{id:'104',reason:'parse'},{id:'101',reason:'network'}]};r=renderWith(d,{title:'국고채 입찰 일정'});
 assert.ok(r.warnings().includes('입찰 예정액: 발행공고 1건을 읽지 못했습니다. 금액이 없는 회차는 공고 목록으로 연결합니다.'),r.warnings().join('|'));   // 전에 읽은 값이 남은 101은 빼고
});
test('results: cells in column order, unread count without kept ids, source is the board the collector reads',()=>{
 const d=schedule();d.feeds.auctions={ok:true,skipped:[{id:'MOSF_A9',reason:'parse'},{id:'MOSF_A1',reason:'network'}]};
 const r=renderWith(d,{title:'최근 국고채 입찰 결과'});
 assert.deepEqual(r.rows('최근 국고채 경쟁입찰 결과'),[['2030-05-07','10년','9,000억원','280%','3.9%','결과'],
  ['2030-05-06','3년','11,000억원','321.3%','3.645%','결과'],['2030-05-06','3년','11,000억원','303%','3.65%','결과']]);
 assert.ok(r.warnings().includes('입찰 결과 공고 1건을 읽지 못했습니다. 원문은 공식 결과 목록에서 확인해 주세요.'),r.warnings().join('|'));
 assert.ok(r.anchors.some(([t,h])=>t==='자료: 재정경제부 국채 입찰 결과 공고' && h==='https://mofe.go.kr/st/fnancstats/ktb50201.do?bbsId=MOSFBBS_000000000049&menuNo=6050300'),JSON.stringify(r.anchors));
 assert.ok(!r.links.some(h=>h.includes('bidResult')));
});
test('msb panel: the result table keeps the newest 12 of 13',()=>{
 const d=msbData(), base=d.msb[0];
 d.msb=Array.from({length:13},(_,i)=>({...base,id:String(950-i),date:'2030-05-'+String(28-2*i).padStart(2,'0')}));
 const rows=renderWith(d,{panel:'msb'}).rows('최근 통화안정증권 경쟁입찰 결과');
 assert.equal(rows.length,12);assert.equal(rows[0][0],'2030-05-28');assert.equal(rows[11][0],'2030-05-06');
});
test('lastScheduledRun follows the daily.yml cron: weekdays at RUN_UTC, GRACE_MS after the slot',()=>{
 const page=fs.readFileSync(path.join(__dirname,'../site/index.html'),'utf8');
 const head=page.match(/^const RUN_UTC = .*;$/m), start=page.indexOf('function lastScheduledRun(now) {'), end=page.indexOf('\n}\n',start);
 assert.ok(head && start>0 && end>start);
 const got=vm.runInNewContext(head[0]+'\n'+page.slice(start,end+2)+'\n({RUN_UTC,GRACE_MS,lastScheduledRun});',{});
 const cron=fs.readFileSync(path.join(__dirname,'../.github/workflows/daily.yml'),'utf8').match(/cron: "(\d+) (\d+) \* \* 1-5"/);
 assert.ok(cron,'daily.yml cron');
 assert.deepEqual([got.RUN_UTC.minute,got.RUN_UTC.hour],[+cron[1],+cron[2]]);assert.equal(got.GRACE_MS,5*36e5);
 const run=t=>got.lastScheduledRun(new Date(t)).toISOString();
 for(const [now,want] of [['2026-10-08T05:00:00Z','2026-10-07T22:17:00.000Z'],['2026-10-11T03:00:00Z','2026-10-09T22:17:00.000Z'],   // 일요일 → 금요일 차례
   ['2026-11-07T12:00:00Z','2026-11-06T22:17:00.000Z'],['2026-11-09T03:00:00Z','2026-11-06T22:17:00.000Z'],
   ['2026-11-10T03:16:00Z','2026-11-06T22:17:00.000Z'],['2026-11-10T03:18:00Z','2026-11-09T22:17:00.000Z']])   // 차례 뒤 5시간을 넘긴 때부터 그 차례
  assert.equal(run(now),want,now);
 const {data,run:st}=fixture();data.checked_at='2026-10-10T01:00:00Z';st.started_at='2026-10-10T00:59:00Z';st.checked_at='2026-10-10T01:01:00Z';
 const sunday=Date.parse('2026-10-11T03:00:00Z');
 assert.equal(health(data,st,got.lastScheduledRun(new Date(sunday)).getTime(),sunday).warning,false);
});
function cardData(){
 const d=issuance(), src={name:'한국은행 금융·경제 스냅샷',url:'https://snapshot.bok.or.kr/dashboard/A'};
 const ch=(v,from)=>({value:v,from});
 d.cards=[
  {key:'kr3',title:'국고채 3년 · 최종호가',group:'rates',unit:'%',note:'q',feed:'rates',source:src,
   points:[['2029-04-10',2.52],['2029-05-21',2.9],['2030-05-17',3.6],['2030-05-20',3.639]],
   metrics:{date:'2030-05-20',value:3.639,changes:{'1':ch(3.9,'2030-05-17'),'5':ch(-10.1,'2030-05-13'),'20':ch(-28.2,'2030-04-22')},sums:{},
     distribution:{from:'2029-05-21',to:'2030-05-20',count:245,min:2.831,max:4.119,range_position:62.4,percentile:70.1}}},
  {key:'kr_us',title:'한국−미국 10년 금리차',group:'rates',unit:'bp',note:'q',feed:'rates',source:src,
   points:[['2030-05-19',-119.4],['2030-05-20',-100.7]],metrics:{date:'2030-05-20',value:-100.7,changes:{'1':ch(18.7,'2030-05-19')},sums:{},distribution:null}},
  {key:'foreign10',title:'외국인 10년 국채선물 순매수',group:'flows',unit:'계약',note:'q',feed:'foreign10',source:{name:'한국거래소',url:'https://ktb.mofe.go.kr/invstrDelngTrend.do'},
   points:[['2030-05-14',-26130],['2030-05-20',4594]],metrics:{date:'2030-05-20',value:4594,changes:{},sums:{'1':ch(4594,'2030-05-20'),'5':ch(29918,'2030-05-14'),'20':ch(-8781,'2030-04-22')},distribution:null}}];
 return d;
}
test('metric cards: chart window is the 1-year range, chart values use the card format, dates on hover, teaser sign',()=>{
 const d=cardData(), r=renderWith(d,{title:'국고채 3년 · 최종호가'});
 const spec=k=>r.charts.find(s=>s.key===k), opt=k=>r.chartOpts[r.charts.indexOf(spec(k))];
 assert.deepEqual(spec('kr3').lines[0].points,[['2029-05-21',2.9],['2030-05-17',3.6],['2030-05-20',3.639]]);   // 분포 시작일 앞 관측은 그리지 않는다
 assert.equal(spec('kr_us').lines[0].points.length,2);                                                   // 분포가 없으면 받아 둔 관측 전부
 const cards=walk(r.ids['korea-market-content'],n=>n.className==='market-card');
 for(const c of d.cards){
  const card=cards.find(n=>n.kids[0].textContent===c.title);
  const shown=walk(card,n=>n.className==='market-value')[0].kids[0].textContent;
  assert.equal(opt(c.key).format(c.metrics.value),shown,c.key);
 }
 assert.deepEqual(d.cards.map(c=>opt(c.key).format(c.metrics.value)),['3.639%','-100.7bp','+4,594계약']);
 const titles=k=>walk(cards.find(n=>n.kids[0].textContent===d.cards.find(c=>c.key===k).title),n=>n.className==='market-deltas')[0].kids.map(x=>x.title);
 assert.deepEqual(titles('kr3'),['비교 시작일: 2030-05-17','비교 시작일: 2030-05-13','비교 시작일: 2030-04-22']);
 assert.deepEqual(titles('foreign10'),['관측일: 2030-05-20','누적 시작일: 2030-05-14','누적 시작일: 2030-04-22']);
 const teaser=walk(r.ids['korea-teaser-values'],n=>n.tag==='strong').map(n=>n.textContent);
 assert.deepEqual(teaser,['-100.7bp','+4,594계약']);                                                     // 카드와 같은 꼴(계약수는 + 부호)
});
test('issuance panel: buyback and exchange results start on different dates — the page says so',()=>{
 const note='매입·교환 결과는 종류마다 따로 읽어 시작일이 다릅니다 — 교환 2030-05-14, 매입 2030-05-15부터. 각 시작일 앞의 입찰은 이 표에 없을 수 있습니다.';
 let r=renderWith(issuance());
 assert.ok(walk(r.panel,n=>n.className==='muted').some(n=>n.textContent===note),r.text);
 const d=issuance();d.ktb_ops=d.ktb_ops.filter(o=>o.kind==='buyback');r=renderWith(d);
 assert.ok(!r.text.includes('시작일이 다릅니다'));
 d.ktb_ops=issuance().ktb_ops;d.ktb_ops[1].date='2030-05-15';r=renderWith(d);
 assert.ok(!r.text.includes('시작일이 다릅니다'));
});
