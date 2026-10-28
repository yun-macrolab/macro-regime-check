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
 data:{checked_at:'2026-10-08T01:00:00Z',feeds:Object.fromEntries(['credit','money','rates','foreign3','foreign10','calendar','auctions','offerings','ktb_plans','ktb_ops'].map(k=>[k,{ok:true}]))},
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
 const panel=walk(ids['korea-market-content'],n=>'ktbIssuance' in n.dataset)[0];
 return {panel,text:panel.textContent,charts,chartOpts,links:walk(panel,n=>n.tag==='a').map(a=>a.href),
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
   feeds:Object.fromEntries(['credit','money','rates','foreign3','foreign10','calendar','auctions','offerings','ktb_plans','ktb_ops'].map(k=>[k,{ok:true}])),
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
 assert.deepEqual(r.anchors.filter(a=>a[0]==='원문 확인'),[['원문 확인','https://mofe.go.kr/nw/nes/detailNesDtaView.do?searchNttId1=Y']]);
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
