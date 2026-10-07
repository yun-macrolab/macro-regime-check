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
 data:{checked_at:'2026-10-08T01:00:00Z',feeds:Object.fromEntries(['credit','money','rates','foreign3','foreign10','calendar','auctions','offerings'].map(k=>[k,{ok:true}]))},
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
