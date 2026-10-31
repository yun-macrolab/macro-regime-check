// AI 투자 참고(site/ai_invest.js) — 아주 작은 가짜 DOM 위에서 render()를 돌려 글을 본다. 숫자는 지어낸 것이다.
// 2026-10-30: 비공개 알림에서 옮긴 두 칸(조달의 사모대출, 상관의 AI 고유 몫 b2 표)이 제 채널에 그려지는지를 함께 본다.
// 실행: node --test scripts/test_ai_invest_render.cjs
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

class El {
 constructor(tag){this.tag=tag;this.kids=[];this.attrs={};}
 append(...xs){for(const x of xs)this.kids.push(typeof x==='string'?{text:x}:x);}
 replaceChildren(...xs){this.kids=[];this.append(...xs);}
 setAttribute(k,v){this.attrs[k]=String(v);}
 set textContent(v){this.kids=[{text:String(v)}];}
 get textContent(){return this.kids.map(k=>k instanceof El?k.textContent:k.text).join('');}
}
const walk=(n,f,out=[])=>{if(n instanceof El){if(f(n))out.push(n);n.kids.forEach(k=>walk(k,f,out));}return out;};
const cls=(n,c)=>walk(n,x=>(x.attrs.class||'').split(' ').includes(c));
const tags=(n,t)=>walk(n,x=>x.tag===t);

function load(opts={}){
 const ids={'ai-head':new El('p'),'ai-body':new El('div'),'ai-teaser-values':new El('ul')};
 const charts=[];
 const el=(tag,attrs,...kids)=>{const n=new El(tag);for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,v);for(const c of kids)if(c!==null&&c!==undefined)n.append(c);return n;};
 const chartFigure=(spec)=>{if(!spec)return null;charts.push(spec);if(opts.chartThrows)return null;return new El('figure');};   // index.html: 실패하면 null
 const sc={window:{},document:{getElementById:id=>ids[id]||null},el,chartFigure};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../site/ai_invest.js'),'utf8'),sc);
 return {api:sc.window.AiInvest,ids,charts};
}
const KEYS=['ict_share','tech_orders','office_cons','financing','hq_spread','private_credit','power','curve_30_10',
 'corr60','corr20','partial60','ai_b2','sb_long'];
const chart=k=>({key:'ai_'+k,title:'t',unit:'%',years:5,zero:true,threshold:null,note:'n',source_note:'s',notices:[],
 lines:[{key:'a',label:'a',role:'main',series:[],derived:false,points:[['2026-09-01',1.23]]}]});
function item(key,extra={}){
 return Object.assign({key,ok:true,stale:false,error:null,failed_since:null,name:key+' 이름',date:'2026-10-23',values:{},
  retrieved:'2026-10-30',line:key+' 숫자 줄 +1.2',extra:[key+' 덧붙임'],chart:chart(key),notices:['계산값 고지'],sources:[]},extra);
}
function data(){
 const items=Object.fromEntries(KEYS.map(k=>[k,item(k)]));
 delete items.ai_b2.chart;                                                          // 표만 싣는 칸
 items.ai_b2.table={caption:'해마다 회귀 계수',columns:['해','b2 (bp)','t (b2)','b1 (bp)','t (b1)','관측일','기간'],
  rows:[['2025','+0.12','+1.3','-0.45','-2.1','240','2025-01-02 ~ 2025-12-31'],
        ['2026','+0.34','+2.2','-0.67','-3.4','200','2026-01-02 ~ 2026-10-23']]};
 items.private_credit.notices=['계산값 고지','Z.1 고지'];
 return {schema:1,notice:'참고 자료다.',order:KEYS,items};
}
const channelOf=(ids,title)=>walk(ids['ai-body'],n=>n.tag==='section'&&n.attrs['aria-label']===title)[0];
const names=sec=>cls(sec,'ai-name').map(n=>n.textContent);

test('every item lands in its channel, in the file order, with no stray words',()=>{
 const {api,ids}=load();
 assert.equal(api.render(data()),true);
 const order=[...api.CHANNELS.flatMap(c=>c[3])];                                  // 다른 realm의 배열 — 이쪽 배열로 옮겨 견준다
 assert.deepEqual(order,KEYS);
 assert.deepEqual(names(ids['ai-body']),KEYS.map(k=>k+' 이름'));
 const body=ids['ai-body'].textContent;
 assert.ok(!/undefined|NaN|null|\[object/.test(body));
 assert.equal(ids['ai-head'].textContent,api.ABOUT);                               // 자료 파일의 notice('참고 자료다.')를 붙이지 않는다
 assert.ok(!ids['ai-head'].textContent.includes('참고 자료다.'));
});

test('the intro is one polite paragraph and does not repeat the data notice',()=>{
 const src=fs.readFileSync(path.join(__dirname,'ai_invest_fetch.py'),'utf8');
 const m=src.match(/^NOTICE = \(([\s\S]*?)\)\n/m);
 assert.ok(m,'ai_invest_fetch.py의 NOTICE를 찾지 못함');
 const notice=[...m[1].matchAll(/"([^"]*)"/g)].map(x=>x[1]).join('');
 assert.ok(notice.length>20&&/다\.$/.test(notice));                                // 자료 파일 쪽은 한다체
 const {api,ids}=load();
 const d=data();d.notice=notice;
 assert.equal(api.render(d),true);
 const intro=ids['ai-head'].textContent;
 assert.equal(intro,api.ABOUT);
 for(const s of notice.split(/(?<=\.)\s+/))assert.ok(!intro.includes(s),s);          // 자료 파일의 문장이 하나도 붙지 않는다
 const sentences=intro.split(/(?<=\.)\s+/);
 assert.equal(sentences.length,2);
 for(const s of sentences)assert.match(s,/니다\.$/,s);                               // 합니다체 한 벌
 assert.ok(!/(?:다|이다)\.(?:\s|$)/.test(intro.replace(/니다\./g,'')));                // 한다체 문장 끝이 섞이지 않는다
 for(const part of['다섯 갈래','규칙 판정에 쓰지 않는','시장 전망으로 읽지 않습니다'])
  assert.equal(intro.split(part).length-1,1,part);                                   // 같은 말을 되풀이하지 않는다
 assert.equal(cls(ids['ai-body'],'notices').length>0,true);                          // 칸마다의 고지는 칸 아래에 그대로
});

test('private credit sits under the funding channel with its chart and both notices',()=>{
 const {api,ids,charts}=load();
 api.render(data());
 const fin=channelOf(ids,'조달');
 assert.deepEqual(names(fin),['financing 이름','hq_spread 이름','private_credit 이름']);
 const pc=cls(fin,'ai-item').find(n=>cls(n,'ai-name')[0].textContent==='private_credit 이름');
 assert.ok(pc.textContent.includes('private_credit 숫자 줄'));
 assert.equal(tags(pc,'figure').length,1);
 assert.deepEqual(cls(pc,'notices')[0].kids.map(k=>k.textContent),['계산값 고지','Z.1 고지']);
 assert.ok(charts.some(c=>c.key==='ai_private_credit'));
 assert.ok(api.CHANNELS.find(c=>c[0]==='finance')[2].includes('사모대출'));
});

test('b2 sits under the correlation channel as a wide table without a chart',()=>{
 const {api,ids,charts}=load();
 api.render(data());
 const corr=channelOf(ids,'주식과 미 10년 금리의 상관');
 assert.deepEqual(names(corr),['corr60 이름','corr20 이름','partial60 이름','ai_b2 이름','sb_long 이름']);
 const b2=cls(corr,'ai-item').find(n=>cls(n,'ai-name')[0].textContent==='ai_b2 이름');
 assert.ok(cls(b2,'ai-wide').length===1);                                          // 표가 있는 칸은 한 줄을 다 쓴다
 assert.equal(tags(b2,'figure').length,0);
 assert.ok(!charts.some(c=>c.key==='ai_ai_b2'));
 const tb=tags(b2,'table')[0];
 assert.equal(tags(tb,'caption')[0].textContent,'해마다 회귀 계수');
 assert.deepEqual(tags(tags(tb,'thead')[0],'th').map(t=>t.textContent),['해','b2 (bp)','t (b2)','b1 (bp)','t (b1)','관측일','기간']);
 const rows=tags(tags(tb,'tbody')[0],'tr');
 assert.deepEqual(rows.map(r=>r.kids[0].textContent),['2025','2026']);              // 해는 행 머리
 assert.equal(rows[1].kids[0].attrs.scope,'row');
 assert.equal(rows[1].kids[1].textContent,'+0.34');
 const about=api.CHANNELS.find(c=>c[0]==='corr')[2];
 assert.ok(about.includes('지수 값과 수익률은 재배포가 제한돼 싣지 않고 상관과 회귀 계수만 싣습니다')&&about.includes('예측이 아닙니다'));
});

test('a malformed b2 table is dropped but the line stays',()=>{
 for(const bad of [{columns:['해'],rows:[['2025','x']]},{columns:['해',1],rows:[]},{columns:[],rows:[]},'표',[['2025']]]){
  const {api,ids}=load();
  const d=data();d.items.ai_b2.table=bad;
  api.render(d);
  const corr=channelOf(ids,'주식과 미 10년 금리의 상관');
  assert.ok(corr.textContent.includes('ai_b2 숫자 줄'));
  assert.equal(tags(corr,'table').filter(t=>t.textContent.includes('2025')).length,0);
 }
});

test('items without notices or with a broken shape show one fixed line, and text is never parsed as markup',()=>{
 const {api,ids}=load();
 const d=data();
 d.items.private_credit.notices=[];                                                  // 고지가 없으면 숫자를 싣지 않는다
 d.items.ai_b2={key:'ai_b2',ok:false,stale:false,error:'<b>원문 오류 https://bad.invalid</b>',name:'ai_b2 이름'};
 d.items.corr20.line='<img src=x onerror=alert(1)>';
 api.render(d);
 const body=ids['ai-body'];
 for(const k of ['private_credit','ai_b2']){
  const it=cls(body,'ai-item').find(n=>cls(n,'ai-name')[0].textContent===k+' 이름');
  assert.equal(it.kids[1].textContent,'자료 없음');
  assert.equal(it.kids.length,2);
 }
 assert.ok(!body.textContent.includes('bad.invalid'));
 assert.ok(!body.textContent.includes('private_credit 숫자 줄'));
 assert.equal(walk(body,n=>n.tag==='img').length,0);                                 // 글자로만 들어간다
 assert.ok(body.textContent.includes('<img src=x onerror=alert(1)>'));
});

test('stale items say since when and keep their numbers',()=>{
 const {api,ids}=load();
 const d=data();
 Object.assign(d.items.ai_b2,{ok:false,stale:true,error:'수신 실패',failed_since:'2026-10-28'});
 Object.assign(d.items.private_credit,{ok:false,stale:true,error:'수신 실패',failed_since:'nope'});
 api.render(d);
 const late=cls(ids['ai-body'],'ai-late').map(n=>n.textContent);
 assert.equal(late.length,2);
 assert.ok(late.some(t=>t.endsWith('(2026-10-28부터)')));
 assert.ok(late.some(t=>t.endsWith('직전에 받은 값을 싣습니다')));                      // 날짜 꼴이 아니면 날짜를 붙이지 않는다
 assert.ok(ids['ai-body'].textContent.includes('ai_b2 숫자 줄'));
});

test('teaser keeps the first item of each channel and skips the new items',()=>{
 const {api,ids}=load();
 api.render(data());
 assert.deepEqual([...api.TEASER],['ict_share','financing','power','curve_30_10','corr60']);
 const t=ids['ai-teaser-values'].textContent;
 assert.ok(!t.includes('private_credit')&&!t.includes('ai_b2'));
});

test('nothing is drawn without a usable teaser item or a file',()=>{
 for(const d0 of [null,undefined,{},{items:null},'x']){const {api,ids}=load();assert.equal(api.render(d0),false);assert.equal(ids['ai-body'].kids.length,0);}
 const {api,ids}=load();const d=data();for(const k of api.TEASER)d.items[k].notices=[];
 assert.equal(api.render(d),false);assert.equal(ids['ai-body'].kids.length,0);
});

const UNL=(fs.readFileSync(path.join(__dirname,'ai_invest_fetch.py'),'utf8').match(/^UNLABELED = "([^"]+)"/m)||[])[1];
const z1=(sid,licence=UNL)=>({series:sid,name:'Board X',url:'https://fred.stlouisfed.org/series/'+sid,restricted:false,licence,
 citation:`Board X, Financial Accounts of the United States (Z.1), Title ${sid}; Liability, Level [${sid}], retrieved from FRED, `+
  `Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/${sid}, October 30, 2026.`});

test('the Z.1 private-credit item shows its Board citations as text, the unlabeled ones only',()=>{
 assert.equal(UNL,'board-public-domain (FRED unlabeled)');                            // 자료 파일 쪽 licence 글과 같다
 const {api,ids}=load();
 const d=data();
 d.items.private_credit.sources=[z1('BOGZ1FL893167205Q'),z1('BCNSDODNS','public-domain'),z1('BOGZ1FL103167205Q'),
  z1('BOGZ1FL893167205Q')];                                                          // 같은 시리즈는 한 번
 d.items.corr60.sources=[Object.assign(z1('SP500','restricted'),{restricted:true})];
 api.render(d);
 const fin=channelOf(ids,'조달');
 const pc=cls(fin,'ai-item').find(n=>cls(n,'ai-name')[0].textContent==='private_credit 이름');
 const lines=cls(pc,'cite-lines');
 assert.equal(lines.length,1);
 assert.deepEqual(lines[0].kids.map(k=>k.textContent),['BOGZ1FL893167205Q','BOGZ1FL103167205Q'].map(sid=>
  `권장 인용: Board X, Financial Accounts of the United States (Z.1), Title ${sid}; Liability, Level [${sid}], retrieved from FRED, `+
  `Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/${sid}, October 30, 2026.`));
 assert.ok(lines[0].kids.every(k=>k.attrs.class==='muted'));
 assert.ok(pc.textContent.indexOf('Z.1 고지')<pc.textContent.indexOf('권장 인용'));    // 고지 뒤에
 assert.equal(cls(ids['ai-body'],'cite-lines').length,1);                            // 다른 칸(공공 자료·제한 자료)은 없음
});

test('a malformed or missing citation draws no citation line',()=>{
 for(const f of [s=>{s.citation='<b>x</b>, retrieved from y, May 1, 2026.';},s=>{s.citation='x';},s=>{delete s.citation;},
   s=>{s.licence='public-domain';},s=>{s.restricted=true;},s=>{s.series='bad id';}]){
  const {api,ids}=load();
  const d=data();const src=z1('BOGZ1FL893167205Q');f(src);d.items.private_credit.sources=[src];
  api.render(d);
  assert.equal(cls(ids['ai-body'],'cite-lines').length,0);
  assert.ok(!ids['ai-body'].textContent.includes('<b>'));
 }
});
