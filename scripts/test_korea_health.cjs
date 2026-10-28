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
function renderWith(data){
 const ids={};const doc={createElement:t=>new El(t),getElementById:id=>(ids[id]=ids[id]||new El('div')),querySelectorAll:()=>[],addEventListener(){}};
 const charts=[];const sc={window:{MacroCharts:{lineChart:(spec)=>{charts.push(spec);return new El('figure');}}},document:doc,setInterval(){},URL};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../site/korea.js'),'utf8'),sc);
 sc.window.KoreaMarket.render(data,null);
 const panel=walk(ids['korea-market-content'],n=>'ktbIssuance' in n.dataset)[0];
 return {panel,text:panel.textContent,charts,links:walk(panel,n=>n.tag==='a').map(a=>a.href)};
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
   '2030-05-15','매입','250%','교환','연간 한도 미등록','이 사이트의 규칙 판정에 쓰지 않는 참고 자료입니다.','재정경제부'])
  assert.ok(text.includes(want),want);
 assert.equal(charts.length,1);assert.equal(JSON.stringify(charts[0].lines.map(l=>[l.key,l.points])),JSON.stringify([['long',[['2030-04-01',26.7],['2030-05-01',21.4]]],['y30',[['2030-04-01',26.7],['2030-05-01',21.4]]]]));
 assert.ok(links.every(h=>new URL(h).hostname==='mofe.go.kr'),links.join(' '));          // 허용 밖 주소는 글자로만
 assert.ok(!/판정(?!에 쓰지)|신호|경보|충족|⚠|축소|확대/.test(text));
});
test('issuance panel: registered limit shows a ratio only without missing months',()=>{
 const d=issuance();Object.assign(d.ktb_summary.progress,{limit_100m:2000000,limit_published:'2029-12-20',limit_source_url:'https://mofe.go.kr/x'});
 let r=renderWith(d);assert.ok(r.text.includes('연간 한도 200.0조원'));assert.ok(r.text.includes('2030년 1월, 2030년 2월'));assert.ok(!r.text.includes('200.0조원 대비'));
 Object.assign(d.ktb_summary.progress,{missing:[],months:['2030-01','2030-02','2030-03','2030-04'],pct:40});
 r=renderWith(d);assert.ok(r.text.includes('연간 한도 200.0조원 대비 40% (계산값)'));
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
