/* Korean market reference panels. DOM text only; no external runtime dependency. */
"use strict";
window.KoreaMarket = (() => {
  let data = null, attempt = null, healthState = null;
  const names = {credit:"회사채 스프레드", money:"CD·CP", rates:"한미 국채", foreign3:"외국인 3년 선물", foreign10:"외국인 10년 선물", calendar:"입찰 일정", auctions:"입찰 결과", offerings:"입찰 예정액", ktb_plans:"국고채 발행계획", ktb_ops:"매입·교환 결과", msb:"통안증권 입찰 결과", msb_plans:"통안증권 발행계획"};
  const groups = {rates:"금리·커브", credit:"신용·단기자금", flows:"수급·입찰"};
  const reasons = {stale:"관측일 지연", regressed:"과거 자료로 되돌아옴", calendar_month:"이번 달 일정 미확인", empty_or_duplicate:"빈 자료·중복 행", timeout:"수신 시간 초과", unavailable:"수신·형식 확인 실패", unreadable_notices:"발행공고 형식 확인 실패"};
  function health(value, run, expectedAfter, now=Date.now()) {
    const checked=Date.parse(value?.checked_at), started=Date.parse(run?.started_at), ended=Date.parse(run?.checked_at);
    const valid=Number.isFinite(checked) && checked<=now+300000;
    const late=!valid || checked<expectedAfter;
    const failures=Object.keys(names).filter(k=>value?.feeds?.[k]?.ok!==true);
    let issue="";
    if(!run || run.schema!==1) issue="갱신 실행 상태를 확인할 수 없습니다";
    else if(run.state==="running") issue=Number.isFinite(started) && now-started<240000 ? "한국 자료 갱신 중" : "한국 자료 갱신이 중단되었거나 지연됐습니다";
    else if(!((run.state==="success" && run.ok===true) || (run.state==="partial" && run.ok===false))) issue="최근 한국 자료 갱신에 실패했습니다";
    else if(!valid || !Number.isFinite(started) || !Number.isFinite(ended) || ended>now+300000 || checked<started || checked>ended) issue="갱신 상태와 자료의 시각이 맞지 않습니다";
    if(late) issue="예정된 한국 자료 갱신이 반영되지 않았습니다";
    return {issue, late, failures, warning:!!issue || !!failures.length};
  }
  function oldObservation(date, now=Date.now()) {
    const day=Date.parse(date+"T00:00:00+09:00");
    const today=Math.floor((now+9*36e5)/864e5), observation=Math.floor((day+9*36e5)/864e5);
    return !Number.isFinite(day) || observation>today || today-observation>7;
  }
  function node(tag, cls, ...children) {
    const e = document.createElement(tag); if(cls) e.className = cls;
    for(const c of children) if(c !== null && c !== undefined) e.append(c);
    return e;
  }
  function sourceLink(label, url) {
    try {
      const u = new URL(url);
      if(u.protocol !== "https:" || !["snapshot.bok.or.kr","ktb.mofe.go.kr","mofe.go.kr","www.bok.or.kr"].includes(u.hostname)) return node("span", "", label);
      const a = node("a", "", label); a.href = u.href; a.rel = "noopener"; return a;
    } catch { return node("span", "", label); }
  }
  function number(v, unit, signed=false) {
    if(!Number.isFinite(v)) return "자료 없음";
    const digits = unit === "계약" || unit === "억원" ? 0 : unit === "bp" ? 1 : 3;
    return (signed && v>0 ? "+" : "")+v.toLocaleString("ko-KR",{maximumFractionDigits:digits})+unit;
  }
  const unreadable = {auctions:"입찰 결과 공고 형식 확인 실패", ktb_plans:"발행계획 보도자료 형식 확인 실패", ktb_ops:"매입·교환 결과 공고 형식 확인 실패", msb:"통화안정증권 결과 공고 형식 확인 실패", msb_plans:"통화안정증권 발행 계획 형식 확인 실패"};
  function failLabel(key, f) {      // 같은 코드라도 묶음마다 읽은 공고가 다르다(입찰 결과·발행계획·매입/교환 = 재정경제부, 예정액·통안증권 = 한국은행)
    return (f?.reason==="unreadable_notices" && unreadable[key]) || reasons[f?.reason] || "수신 실패";
  }
  function feedNote(key) {
    const f = data?.feeds?.[key];
    if(f?.ok!==true) return failLabel(key,f)+" · 마지막 성공 자료";
    return healthState?.issue ? healthState.issue+" · 자료일 확인" : "";
  }
  function refreshHealth() {
    if(!data) return;
    const now=Date.now();
    const expected=typeof lastScheduledRun==="function" ? lastScheduledRun(new Date(now)).getTime() : now-96*36e5;
    healthState=health(data,attempt,expected,now);
    const notes=[healthState.issue,healthState.failures.length ? "확인 필요: "+healthState.failures.map(k=>names[k]).join(", ") : ""].filter(Boolean);
    const checked=new Date(data.checked_at).toLocaleString("ko-KR",{timeZone:"Asia/Seoul"});
    document.getElementById("korea-market-status").textContent="한국 자료 확인: "+checked+" (KST) · "+(notes.join(" · ") || "각 지표의 관측일을 확인하세요");
    const summary=document.getElementById("korea-teaser-status");
    summary.textContent=notes.join(" · "); summary.hidden=!notes.length;
    window.koreaWarning=!!healthState.warning;                      // 머리 표시등은 시계가 매초 다시 그린다 — 거기서 함께 판정
    if(typeof paintLamp==="function") paintLamp(new Date());
    document.querySelectorAll("[data-market-feed]").forEach(e=>{
      const note=[feedNote(e.dataset.marketFeed),e.dataset.marketDate && oldObservation(e.dataset.marketDate,now) ? "최근 관측이 7일을 넘었거나 자료일 확인이 필요합니다" : ""].filter(Boolean).join(" · ");
      e.textContent=note; e.hidden=!note;
    });
    document.getElementById("korea-source-status").replaceChildren(...Object.keys(names).map(key=>{
      const f=data.feeds?.[key], stamp=f?.last_success ? new Date(f.last_success).toLocaleString("ko-KR",{timeZone:"Asia/Seoul"})+" (KST)" : "없음";
      return node("li","",names[key]+": "+(feedNote(key) || "수신 성공")+" · 마지막 성공 "+stamp);
    }));
  }
  function smallChart(c) {
    if(!window.MacroCharts || !Array.isArray(c.points) || !c.points.length) return null;
    // 그래프·'표로 보기'는 아래 '최근 1년 범위'와 같은 창(분포의 시작일부터) — 수집기는 400일을 둔다. 분포가 없으면 받아 둔 관측 전부
    const from=c.metrics?.distribution?.from;
    const points=typeof from==="string" ? c.points.filter(p=>Array.isArray(p) && p[0]>=from) : c.points;
    const spec = {key:c.key, title:c.title, unit:c.unit, zero:c.unit!=="%", threshold:null,
      source_note:"자료: "+c.source.name+" · 변화·분포는 이 사이트의 계산값", note:null, notices:[],
      lines:[{key:c.key,label:c.title,role:"series",points}]};
    // 끝 값·읽기 글·'표로 보기'는 카드의 숫자와 같은 꼴(소수 자리·천 단위·계약수의 + 부호)
    try { return window.MacroCharts.lineChart(spec,{height:180,caption:false,format:v=>number(v,c.unit,c.unit==="계약")}); }
    catch { return node("p","muted","차트를 표시하지 못했습니다. 표의 수치를 확인해 주세요."); }
  }
  function metricCard(c) {
    const m=c.metrics;
    const card=node("article","market-card",node("h3","",c.title),node("p","market-question",c.note));
    card.append(node("div","market-value",node("strong","",number(m?.value,c.unit,c.unit==="계약")),node("span","muted",m?.date || "자료일 없음")));
    const warning=node("p","market-warning"); warning.dataset.marketFeed=c.feed; warning.dataset.marketDate=m?.date || "unknown";
    card.append(warning);
    const stats=node("div","market-deltas");
    for(const n of [1,5,20]) {
      const v=c.unit==="계약"?m?.sums?.[n]:m?.changes?.[n];
      const label=c.unit==="계약"?(n===1?"당일":"최근 "+n+"관측일 누적"):(n+"관측일 전 대비");
      const item=node("div","",node("span","",label),node("strong","",number(v?.value,c.unit==="계약"?"계약":"bp",true)));
      // 마우스를 올리면 보이는 날짜 — 계약수 칸은 비교가 아니라 더한 첫 날(당일은 그 관측일)
      if(v) item.title=(c.unit==="계약"?(n===1?"관측일: ":"누적 시작일: "):"비교 시작일: ")+v.from;
      stats.append(item);
    }
    card.append(stats,smallChart(c) || "");
    const d=m?.distribution;
    if(d) {
      const range=node("div","market-range");
      range.append(node("p","",`최근 1년 범위 ${number(d.min,c.unit)} ~ ${number(d.max,c.unit)}`));
      if(Number.isFinite(d.range_position)) {
        const track=node("div","range-track"), dot=node("span","range-dot");
        dot.style.left=Math.min(100,Math.max(0,d.range_position))+"%"; track.append(dot);
        track.setAttribute("role","img");track.setAttribute("aria-label",`최저~최고 범위에서 현재 위치 ${d.range_position}%`);range.append(track);
      }
      range.append(node("small","",`분포 백분위 ${d.percentile}% · ${d.count}개 관측 · ${d.from}~${d.to}`));
      card.append(range);
    } else if(c.unit!=="계약") card.append(node("p","muted","1년 분포: 관측 이력이 충분하지 않습니다."));
    card.append(node("p","market-source",sourceLink("원 출처",c.source.url)," · ",c.source.name));
    return card;
  }
  function table(headers, rows, label) {
    const t=node("table","market-table");t.setAttribute("aria-label",label);
    const head=node("tr","");for(const text of headers){const th=node("th","",text);th.scope="col";head.append(th);}
    const body=node("tbody","");for(const cells of rows)body.append(node("tr","",...cells.map(c=>node("td","",c))));
    t.append(node("thead","",head),body);return node("div","market-scroll",t);
  }
  // 그날·그 만기의 공고 — 같은 번호는 한 번만(번호가 없는 줄은 가려내지 못해 그대로)
  function sameAuction(list, r) {
    const seen=new Set();
    return (Array.isArray(list)?list:[]).filter(a=>{
      if(!a || a.date!==r.date || a.tenor!==r.tenor) return false;
      if(a.id===undefined || a.id===null) return true;
      if(seen.has(a.id)) return false;
      seen.add(a.id); return true;
    });
  }
  // 일정 칸의 예정액 — 공고 하나면 그 금액(원문 링크), 둘 이상이면(한 만기 두 종목을 같은 날 입찰) 합과 공고마다의 금액
  function amountCell(rows) {
    if(!rows.length) return sourceLink("공고 확인","https://ktb.mofe.go.kr/isuNdReprchsPblanc.do");
    if(rows.length===1) return sourceLink(number(rows[0].offered_100m,"억원"),rows[0].source_url);
    const each=rows.flatMap((a,i)=>(i ? [" + "] : []).concat([sourceLink(number(a.offered_100m,"억원"),a.source_url)]));
    return node("span","",number(rows.reduce((s,a)=>s+a.offered_100m,0),"억원")+" ("+rows.length+"건: ",...each,")");
  }
  function auctionPanels() {
    const wrap=node("div","auction-grid");
    const cal=data.calendar;
    const schedule=node("article","panel",node("h3","","국고채 입찰 일정"));
    if(cal) {
      schedule.append(node("p","muted",cal.month+" 공식 일정 · "+(feedNote("calendar") || "공고에 따라 변경될 수 있습니다")));
      // 두 묶음이 같은 안내(갱신 지연 등)면 한 번만 — 서로 다른 실패는 둘 다
      const amountNotes=[...new Set([feedNote("offerings"),feedNote("auctions")].filter(Boolean))];
      if(amountNotes.length)schedule.append(node("p","market-warning","입찰금액: "+amountNotes.join(" · ")));
      const kept=new Set((data.offerings||[]).map(o=>o.id)), skipped=data.feeds?.offerings?.skipped;
      const unread=Array.isArray(skipped) ? skipped.filter(s=>!kept.has(s.id)) : [];   // 전에 읽은 값이 남은 공고는 빼고
      if(unread.length)schedule.append(node("p","market-warning","입찰 예정액: 발행공고 "+unread.length+"건을 읽지 못했습니다. 금액이 없는 회차는 공고 목록으로 연결합니다."));
      schedule.append(table(["입찰일","만기","예정액"],cal.rows.map(r=>{
        const results=sameAuction(data.auctions,r), offers=sameAuction(data.offerings,r);
        // 결과 공고가 먼저 — 그날·그 만기의 결과를 발행공고보다 적게 읽었으면(일부 결과만) 발행공고 금액
        return [r.date,r.tenor,amountCell(results.length && results.length>=offers.length ? results : offers)];
      }),"국고채 월별 입찰 일정"));
      schedule.append(node("p","market-source",sourceLink("공식 월별 일정",cal.source_url)," · 일반 국고채 경쟁입찰 예정액입니다. 확인된 발행·결과 공고만 숫자로 표시하며 금액을 누르면 원문으로 이동합니다."));
    } else schedule.append(node("p","market-warning","일정을 불러오지 못했습니다."));
    const results=node("article","panel",node("h3","","최근 국고채 입찰 결과"));
    if(feedNote("auctions"))results.append(node("p","market-warning",feedNote("auctions")));
    const shown=new Set((data.auctions||[]).map(a=>a.id)), missed=data.feeds?.auctions?.skipped;
    const unreadResults=Array.isArray(missed) ? missed.filter(s=>!shown.has(s.id)) : [];   // 전에 읽은 값이 남은 공고는 빼고
    if(unreadResults.length)results.append(node("p","market-warning","입찰 결과 공고 "+unreadResults.length+"건을 읽지 못했습니다. 원문은 공식 결과 목록에서 확인해 주세요."));
    if(data.auctions?.length) results.append(table(["입찰일","만기","입찰금액","응찰률","평균 낙찰금리","원문"],data.auctions.map(a=>
      [a.date,a.tenor,number(a.offered_100m,"억원"),number(a.bid_cover_pct,"%"),number(a.yield_pct,"%"),sourceLink("결과",a.source_url)]),"최근 국고채 경쟁입찰 결과"));
    else results.append(node("p","market-warning","확인된 입찰 결과가 없습니다."));
    results.append(node("p","reading-note","응찰률은 응찰금액÷입찰금액입니다. 만기·발행 규모가 다른 입찰을 숫자 하나로 비교하지 마세요. 최근 공고 목록에서 확인한 일반 국고채 경쟁입찰만 표시합니다."),
      node("p","market-source",sourceLink("자료: 재정경제부 국채 입찰 결과 공고",MOFE_RESULTS)));     // 수집기가 읽는 결과 목록(매입·교환과 같은 게시판)
    wrap.append(schedule,results,msbPanel());return wrap;
  }
  // 통화안정증권 경쟁입찰 결과 — 한국은행 공개시장운영 공지의 숫자(scripts/korea_msb.py). 화면 글은 아래 고정 문구뿐이다(방향·평가 낱말 없음)
  const BOK_MSB="https://www.bok.or.kr/portal/singl/newsData/list.do?menuNo=200295&searchCnd=2&searchKwd=%ED%86%B5%ED%99%94%EC%95%88%EC%A0%95%EC%A6%9D%EA%B6%8C+%EA%B2%BD%EC%9F%81%EC%9E%85%EC%B0%B0+%EC%8B%A4%EC%8B%9C+%EA%B2%B0%EA%B3%BC";
  const BOK_MSB_PLANS="https://www.bok.or.kr/portal/singl/newsData/list.do?menuNo=200295&searchCnd=2&searchKwd=%ED%86%B5%ED%99%94%EC%95%88%EC%A0%95%EC%A6%9D%EA%B6%8C+%EB%B0%9C%ED%96%89+%EA%B3%84%ED%9A%8D";
  const joP = v => Number.isFinite(v) ? (v/10000).toLocaleString("ko-KR",{minimumFractionDigits:1,maximumFractionDigits:2})+"조원" : "자료 없음";   // 계획은 0.1조원 단위
  const offerRange = p => !Number.isFinite(p.offer_min_100m) || !Number.isFinite(p.offer_max_100m) ? "자료 없음"
    : p.offer_min_100m===p.offer_max_100m ? joP(p.offer_max_100m) : joP(p.offer_min_100m).replace("조원","")+"~"+joP(p.offer_max_100m);
  function redemptionText(p) {           // 숫자 / 표는 있는데 못 읽음(원문으로) / 계획에 중도환매 표가 없음
    return Number.isFinite(p.redemption_100m) ? joP(p.redemption_100m)
      : p.redemption_unread===true ? sourceLink("원문 확인",p.source_url) : "계획에 없음";
  }
  function planRows(data) {
    return (Array.isArray(data.msb_plans)?data.msb_plans:[]).filter(p=>p && typeof p.month==="string" && /^\d{4}-\d{2}$/.test(p.month))
      .sort((a,b)=>a.month<b.month?-1:a.month>b.month?1:0);
  }
  const MSB_KIND={discount:"할인율",yield:"수익률"};
  const MSB_ROWS=12;
  const jo2 = v => Number.isFinite(v) ? (v/10000).toLocaleString("ko-KR",{minimumFractionDigits:2,maximumFractionDigits:2})+"조원" : "자료 없음";   // 공고는 0.01조원 단위
  const pct = v => Number.isFinite(v) ? v.toLocaleString("ko-KR",{minimumFractionDigits:1,maximumFractionDigits:1})+"%" : "자료 없음";   // 비중·응찰률 — 소수 한 자리
  function msbDays(t) { const m=/^(\d{1,3})(일|년)$/.exec(t||""); return m ? +m[1]*(m[2]==="년"?365:1) : Infinity; }
  const pct3 = v => v.toLocaleString("ko-KR",{minimumFractionDigits:3,maximumFractionDigits:3})+"%";   // 공고와 같은 소수 셋째 자리
  function msbRate(r) { return Number.isFinite(r.rate_pct) ? pct3(r.rate_pct)+" ("+(MSB_KIND[r.rate_kind]||"금리")+")" : "자료 없음"; }
  function msbChart(rows) {
    if(!window.MacroCharts) return null;
    const tenors=[...new Set(rows.map(r=>r.tenor))].sort((a,b)=>msbDays(a)-msbDays(b));
    const lines=tenors.map(t=>{
      const these=rows.filter(r=>r.tenor===t && Number.isFinite(r.rate_pct)).sort((a,b)=>a.date<b.date?-1:a.date>b.date?1:0);
      return {key:"msb_"+t,label:t+" "+(MSB_KIND[these[0]?.rate_kind]||"금리"),role:"series",points:these.map(r=>[r.date,r.rate_pct])};
    }).filter(l=>l.points.length>=2);
    if(!lines.length) return null;
    const spec={key:"msb_rates",title:"통화안정증권 낙찰금리(만기별)",unit:"%",zero:false,threshold:null,
      source_note:"자료: 한국은행 공개시장운영 공지(통화안정증권 경쟁입찰 실시 결과)",note:"1년 미만(91일물 등)은 낙찰할인율, 1년 이상은 낙찰수익률입니다.",notices:[],lines};
    try { return node("div","",node("p","reading-note",spec.title),window.MacroCharts.lineChart(spec,{height:180,caption:false,format:pct3})); }
    catch { return node("p","muted","차트를 표시하지 못했습니다. 표의 수치를 확인해 주세요."); }
  }
  function msbPanel() {
    const rows=(Array.isArray(data.msb)?data.msb:[]).filter(r=>r && typeof r.date==="string" && typeof r.tenor==="string");
    const months=(Array.isArray(data.msb_summary?.months)?data.msb_summary.months:[]).filter(m=>m && typeof m.month==="string");
    const plans=planRows(data), plan=plans[plans.length-1], planOf=m=>plans.find(p=>p.month===m);
    const panel=node("article","panel",node("h3","","통화안정증권 발행 계획·입찰 결과"));
    panel.dataset.msb="";
    if(feedNote("msb")) panel.append(node("p","market-warning",names.msb+": "+feedNote("msb")));
    if(feedNote("msb_plans")) panel.append(node("p","market-warning",names.msb_plans+": "+feedNote("msb_plans")));
    const keptPlans=new Set(plans.map(p=>p.id)), missedPlans=data.feeds?.msb_plans?.skipped;
    const unreadPlans=Array.isArray(missedPlans) ? missedPlans.filter(s=>s && !keptPlans.has(s.id) && s.reason!=="not_tried") : [];
    if(unreadPlans.length) panel.append(node("p","market-warning","통화안정증권 발행 계획 공고 "+unreadPlans.length+"건을 읽지 못했습니다. 원문은 한국은행 공개시장운영 공지에서 확인해 주세요."));
    if(plan) {
      panel.append(node("p","muted",monthLabel(plan.month)+" 발행 계획"+(typeof plan.published==="string" && /^\d{4}-\d{2}-\d{2}$/.test(plan.published) ? " · "+plan.published+" 공고" : "")));
      panel.append(node("div","market-value",node("strong","",joP(plan.total_100m)),node("span","muted","발행 계획(모집 최대 기준)")));
      panel.append(node("div","market-deltas",
        node("div","",node("span","","경쟁입찰 계획"),node("strong","",joP(plan.competitive_100m))),
        node("div","",node("span","","모집 계획"),node("strong","",offerRange(plan))),
        node("div","",node("span","","중도환매 예정"),node("strong","",redemptionText(plan)))));
      // 끝나지 않은 이번 달: 그달 계획이 있으면 낙찰액 합을 경쟁입찰 계획에 견준다(계산값)
      const cur=months.find(m=>typeof m.through==="string"), cp=cur && planOf(cur.month);
      if(cp && Number.isFinite(cur.awarded_100m) && cp.competitive_100m>0)
        panel.append(node("p","reading-note",monthLabel(cur.month)+" 낙찰액 합 "+jo2(cur.awarded_100m)+" — 경쟁입찰 계획 "+joP(cp.competitive_100m)+"의 "
          +pct(Math.round(cur.awarded_100m/cp.competitive_100m*1000)/10)+" ("+cur.through.slice(5)+"까지, 계산값)"));
    } else panel.append(node("p","market-warning","확인된 통화안정증권 발행 계획이 없습니다."));
    const kept=new Set(rows.map(r=>r.id)), missed=data.feeds?.msb?.skipped;
    const unread=Array.isArray(missed) ? missed.filter(s=>s && !kept.has(s.id) && s.reason!=="not_tried") : [];   // 전에 읽은 값이 남은 공고는 빼고
    if(unread.length) panel.append(node("p","market-warning","통화안정증권 결과 공고 "+unread.length+"건을 읽지 못했습니다. 원문은 한국은행 공개시장운영 공지에서 확인해 주세요."));
    if(rows.length) {
      panel.append(table(["입찰일","만기","발행예정액","응찰액","응찰률","낙찰액","낙찰금리","원문"],rows.slice(0,MSB_ROWS).map(r=>
        [r.date,r.tenor,jo2(r.offered_100m),jo2(r.bids_100m),pct(r.bid_cover_pct),jo2(r.awarded_100m),msbRate(r),sourceLink("결과",r.source_url)]),
        "최근 통화안정증권 경쟁입찰 결과"));
      const chart=msbChart(rows);
      if(chart) panel.append(chart);       // 차트 도구가 없거나 만기마다 두 번 미만이면 그래프만 빠진다
      if(months.length) panel.append(table(["월","입찰(읽은 공고)","경쟁입찰 계획","발행예정액 합","응찰액 합","낙찰액 합","응찰액이 예정액보다 적은 입찰"],months.map(m=>
        [monthLabel(m.month)+(typeof m.through==="string" && /^\d{4}-\d{2}-\d{2}$/.test(m.through) ? " ("+m.through.slice(5)+"까지)" : ""),Number.isFinite(m.count)?m.count+"회":"—",
         planOf(m.month) ? joP(planOf(m.month).competitive_100m) : "—",jo2(m.offered_100m),jo2(m.bids_100m),jo2(m.awarded_100m),Number.isFinite(m.short)?m.short+"회":"—"]),
        "달마다 통화안정증권 경쟁입찰 합계"));
    } else panel.append(node("p","market-warning","확인된 통화안정증권 입찰 결과가 없습니다."));
    if(plans.length) panel.append(table(["월","발행 계획(모집 최대)","경쟁입찰","모집","중도환매 예정","원문"],plans.slice().reverse().map(p=>
      [monthLabel(p.month),joP(p.total_100m),joP(p.competitive_100m),offerRange(p),redemptionText(p),sourceLink("계획",p.source_url)]),
      "달마다 통화안정증권 발행 계획"));
    panel.append(node("p","reading-note","발행 계획은 한국은행이 전달 말에 공고하는 그달 정례입찰 계획(첨부 PDF)입니다. 총액은 모집 발행예정액 범위의 최대를 넣은 값이고, 입찰 전 영업일의 최종 입찰정보로 바뀔 수 있습니다. 중도환매는 만기 전의 통화안정증권을 한국은행이 되사는 것입니다."));
    panel.append(node("p","reading-note","통화안정증권은 한국은행이 시중 유동성을 조절하려고 발행하는 채권입니다. 1년 미만(91일물 등)은 할인채라 낙찰할인율, 1년 이상은 낙찰수익률을 적습니다 — 할인율은 같은 채권의 수익률보다 낮게 나오므로 두 숫자를 그대로 견주지 마세요. 응찰률은 응찰액÷발행예정액입니다(공고 금액이 0.01조원 단위로 반올림돼 있어 근사). 응찰액이 발행예정액보다 적으면 낙찰액도 예정액에 못 미칩니다."),
      node("p","reading-note","이 사이트의 규칙 판정에 쓰지 않는 참고 자료입니다. 금액·금리는 결과 공고와 발행 계획에서 옮긴 값이고, 응찰률·달마다 합계·계획 대비 비율은 이 사이트의 계산값입니다. 합계는 이 사이트가 읽은 공고만 더하고, 읽은 기록이 그달 1일 앞부터 있는 달만 싣습니다. 이번 달은 아직 끝나지 않아 마지막으로 읽은 입찰일까지의 합입니다."),
      node("p","market-source","자료: 한국은행 공개시장운영 공지 — ",sourceLink("통화안정증권 경쟁입찰 실시 결과",BOK_MSB)," · ",sourceLink("통화안정증권 발행 계획",BOK_MSB_PLANS)));
    return panel;
  }
  // 국고채 발행계획·매입(바이백)·교환 — 재정경제부 보도자료와 입찰 결과 공고의 숫자. 화면 글은 아래 고정 문구뿐이다(방향·평가 낱말 없음)
  const MOFE_PLANS="https://mofe.go.kr/nw/nes/nesdta.do?searchBbsId1=MOSFBBS_000000000028&menuNo=4010100";
  const MOFE_RESULTS="https://mofe.go.kr/st/fnancstats/ktb50201.do?bbsId=MOSFBBS_000000000049&menuNo=6050300";
  function joNum(v, signed=false) {  // 억원 → 조원 숫자만(소수 한 자리 이상, 억 단위까지 그대로 — 1,450억 = 0.145)
    const x=v/10000;
    return (signed && x>0 ? "+" : "")+x.toLocaleString("ko-KR",{minimumFractionDigits:1,maximumFractionDigits:4});
  }
  const jo = (v, signed=false) => Number.isFinite(v) ? joNum(v,signed)+"조원" : "자료 없음";
  const monthLabel = m => typeof m==="string" && /^\d{4}-\d{2}$/.test(m) ? m.slice(0,4)+"년 "+(+m.slice(5))+"월" : "달 미상";
  function shareChart(plans) {
    if(!window.MacroCharts) return null;
    const pts=k=>plans.filter(p=>Number.isFinite(p[k])).map(p=>[p.month+"-01",p[k]]);
    const spec={key:"ktb_long_share",title:"월별 경쟁입찰 계획 중 장기물 비중",unit:"%",zero:true,threshold:null,
      source_note:"자료: 재정경제부 월별 국고채 발행계획 보도자료 · 비중은 이 사이트의 계산값",note:null,notices:[],
      lines:[{key:"long",label:"20·30·50년 비중",role:"series",points:pts("long_share_pct")},
             {key:"y30",label:"30년 비중",role:"series",points:pts("y30_share_pct")}]};
    try { return node("div","",node("p","reading-note",spec.title),window.MacroCharts.lineChart(spec,{height:170,caption:false,format:pct})); }   // 칸의 비중과 같은 소수 한 자리
    catch { return node("p","muted","차트를 표시하지 못했습니다. 표의 수치를 확인해 주세요."); }
  }
  // 월별 표 — 그래프의 '표로 보기'와 같이 최근 달이 위. 숫자는 보도자료 값 그대로(당초 대비는 보도자료 문구, 없으면 —)
  function monthTable(plans) {
    const rows=plans.slice().reverse().map(p=>{
      const stated=Number.isFinite(p.stated_plan_change_100m) ? joNum(p.stated_plan_change_100m,true)
        : p.stated_plan_change_unread===true ? sourceLink("원문 확인",p.source_url) : "—";
      const bb=p.buyback_plan, dates=Array.isArray(bb?.dates) ? bb.dates.filter(d=>typeof d==="string").map(d=>d.slice(5)) : [];
      const buyback=!bb ? "—" : (Number.isFinite(bb.amount_100m) ? joNum(bb.amount_100m) : "자료 없음")+(dates.length ? " ("+dates.join(", ")+")" : "");
      return [p.month,Number.isFinite(p.competitive_100m) ? joNum(p.competitive_100m) : "—",stated,
        Number.isFinite(p.long_share_pct) ? pct(p.long_share_pct) : "—",buyback];
    });
    return table(["월","경쟁입찰 계획(조원)","당초 대비(보도자료)","20·30·50년 비중","매입 계획(조원, 날짜)"],rows,"월별 경쟁입찰 계획·장기물 비중·매입 계획");
  }
  function opPlan(label, item) {
    const dates=Array.isArray(item?.dates) ? item.dates.filter(d=>typeof d==="string") : [];
    return item ? label+" "+jo(item.amount_100m)+(dates.length ? " ("+dates.join(", ")+")" : "") : label+": 보도자료에 계획 없음";
  }
  function issuancePanel() {
    const plans=(Array.isArray(data.ktb_plans)?data.ktb_plans:[]).filter(p=>p && typeof p.month==="string");
    const ops=(Array.isArray(data.ktb_ops)?data.ktb_ops:[]).filter(o=>o && typeof o.date==="string");
    const sum=data.ktb_summary && typeof data.ktb_summary==="object" ? data.ktb_summary : {}, latest=plans[plans.length-1];
    const panel=node("article","panel",node("h3","","국고채 발행계획·바이백"));
    panel.dataset.ktbIssuance="";
    let statedPrevShown=false;     // '전월 대비(보도자료 문구)' 줄을 썼는가 — 끝의 계산값 안내 글이 따른다
    for(const key of ["ktb_plans","ktb_ops"]) if(feedNote(key)) panel.append(node("p","market-warning",names[key]+": "+feedNote(key)));
    const keptPlans=new Set(plans.map(p=>p.id)), missedPlans=data.feeds?.ktb_plans?.skipped;
    const unreadPlans=Array.isArray(missedPlans) ? missedPlans.filter(s=>s && !keptPlans.has(s.id) && s.reason!=="not_tried") : [];   // 전에 읽은 값이 남은 보도자료는 빼고
    if(unreadPlans.length) panel.append(node("p","market-warning","발행계획 보도자료 "+unreadPlans.length+"건을 읽지 못했습니다. 원문은 보도자료 목록에서 확인해 주세요."));
    if(latest) {
      panel.append(node("p","muted",monthLabel(latest.month)+" 계획 · 보도자료 "+(latest.published||"날짜 미상")));
      panel.append(node("div","market-value",node("strong","",jo(latest.competitive_100m)),node("span","muted","경쟁입찰 발행 계획")));
      // 당초 대비: 숫자 / '당초' 문구는 있는데 꼴이 달라 못 읽음 / 문구를 찾지 못함(없거나 못 읽음 — '언급 없음'이라 단정하지 않는다)
      const stated=Number.isFinite(latest.stated_plan_change_100m) ? jo(latest.stated_plan_change_100m,true)
        : latest.stated_plan_change_unread===true ? node("span","","문구를 읽지 못함 — ",sourceLink("원문 확인",latest.source_url)) : "보도자료에서 확인되지 않음";
      // 전월 대비: 두 달 계획이 다 있으면 계산값(계획 대 계획). 없으면 보도자료 문구 — 실적 대비일 수 있어 이름을 달리 붙인다
      const computed=Number.isFinite(sum.prev_month_change_100m), statedPrev=Number.isFinite(latest.stated_prev_change_100m);
      const prev=computed ? jo(sum.prev_month_change_100m,true)+" (계산값)" : statedPrev ? jo(latest.stated_prev_change_100m,true) : "전월 계획 없음";
      statedPrevShown=!computed && statedPrev;
      const prevLabel=statedPrevShown ? "전월 대비(보도자료 문구)" : "전월 계획 대비";
      panel.append(node("div","market-deltas",
        node("div","",node("span","",prevLabel),node("strong","",prev)),
        node("div","",node("span","","당초 계획 대비(보도자료)"),node("strong","",stated)),
        node("div","",node("span","","20·30·50년 비중 · 30년"),node("strong","",pct(latest.long_share_pct)+" · "+pct(latest.y30_share_pct)))));
      const tenors=(Array.isArray(latest.tenors)?latest.tenors:[]).filter(t=>t && typeof t.tenor==="string");
      if(tenors.length) panel.append(table(["만기","경쟁입찰 계획","비중"],tenors.map(t=>[t.tenor,jo(t.amount_100m),
        pct(Number.isFinite(t.amount_100m) && latest.competitive_100m>0 ? Math.round(t.amount_100m/latest.competitive_100m*1000)/10 : NaN)]),
        monthLabel(latest.month)+" 만기별 경쟁입찰 계획"));
      panel.append(node("p","reading-note",monthLabel(latest.month)+" "+opPlan("매입(바이백) 계획",latest.buyback_plan)+" · "+opPlan("교환 계획",latest.exchange_plan)));
      const chart=plans.length<2 ? node("p","muted","장기물 비중 그래프는 두 달 이상 자료가 모이면 표시합니다.") : shareChart(plans);
      if(chart) panel.append(chart);       // 차트 도구가 없으면 그래프만 빠진다(표·수치는 그대로)
      panel.append(monthTable(plans));
    } else panel.append(node("p","market-warning","확인된 발행계획이 없습니다."));
    const p=sum.progress, progress=node("div","market-range");
    if(p && Array.isArray(p.months) && Array.isArray(p.missing)) {
      const head=p.year+"년 보도자료 발행 규모 합계 "+jo(p.actual_100m)+" ("+p.months.length+"개월, "+monthLabel(p.through)+"까지)";
      if(!Number.isFinite(p.limit_100m)) progress.append(node("p","",head+" · 연간 한도 미등록"));
      else {
        progress.append(node("p","",head+" · 연간 한도 "+jo(p.limit_100m)+(Number.isFinite(p.pct) ? " 대비 "+pct(p.pct)+" (계산값)" : "")));
        if(Number.isFinite(p.pct)) {
          const track=node("div","range-track"), dot=node("span","range-dot");
          dot.style.left=Math.min(100,Math.max(0,p.pct))+"%"; track.append(dot);
          track.setAttribute("role","img"); track.setAttribute("aria-label","연간 한도 대비 보도자료 발행 규모 합계 "+pct(p.pct)); progress.append(track);
        } else progress.append(node("small","","실적이 확인되지 않은 달("+p.missing.map(monthLabel).join(", ")+")이 있어 한도 대비 비율은 표시하지 않습니다."));
        progress.append(node("small",""," 연간 한도: ",sourceLink(p.year+"년 국고채 발행계획 보도자료("+p.limit_published+")",p.limit_source_url)));
      }
    } else progress.append(node("p","muted","발행 실적이 적힌 보도자료를 아직 확인하지 못했습니다."));
    panel.append(progress);
    const kept=new Set(ops.map(o=>o.id)), missed=data.feeds?.ktb_ops?.skipped;
    // 종류 하나의 결과 목록에서 공고를 하나도 못 찾음(id = 종류 이름, no_notices) — 공고 건수와 따로 적는다
    const emptyKinds=Array.isArray(missed) ? ["exchange","buyback"].filter(k=>missed.some(s=>s && s.id===k && s.reason==="no_notices")) : [];
    const unread=Array.isArray(missed) ? missed.filter(s=>s && !kept.has(s.id) && s.reason!=="not_tried" && s.reason!=="no_notices") : [];
    if(unread.length) panel.append(node("p","market-warning","매입·교환 결과 공고 "+unread.length+"건을 읽지 못했습니다. 원문은 공식 결과 목록에서 확인해 주세요."));
    for(const k of emptyKinds) panel.append(node("p","market-warning",(k==="exchange"?"교환":"매입")+" 입찰 결과 목록에서 공고를 찾지 못했습니다(목록 형식 확인 필요)."));
    if(ops.length) panel.append(table(["입찰일","구분","입찰금액","응찰률","낙찰금액","원문"],ops.map(o=>
      [o.date,o.kind==="exchange"?"교환":o.kind==="buyback"?"매입":"기타",jo(o.offered_100m),pct(o.bid_cover_pct),jo(o.awarded_100m),sourceLink("결과",o.source_url)]),
      "최근 국고채 매입·교환 입찰 결과"));
    else panel.append(node("p","market-warning","확인된 매입·교환 결과가 없습니다."));
    // 두 결과 목록은 따로 읽어(각 최근 6건) 표의 가장 오래된 날이 종류마다 다르다 — 날짜순으로 섞인 표가 빈 기간을 감추지 않게 적는다
    const first=k=>ops.filter(o=>o.kind===k).map(o=>o.date).sort()[0];
    if(first("exchange") && first("buyback") && first("exchange")!==first("buyback"))
      panel.append(node("p","muted","매입·교환 결과는 종류마다 따로 읽어 시작일이 다릅니다 — 교환 "+first("exchange")+", 매입 "+first("buyback")+"부터. 각 시작일 앞의 입찰은 이 표에 없을 수 있습니다."));
    panel.append(node("p","reading-note","경쟁입찰 계획은 비경쟁인수·교환을 뺀 금액입니다. 발행 규모는 다음 달 보도자료 참고표에 적힌 보도 시점 값입니다(뒤에 확정되는 20년물 비경쟁인수와 모집분은 빠져 있어 재정경제부가 밝힌 누계와 다를 수 있습니다). 매입은 만기 전 국고채를 정부가 사들이는 입찰, 교환은 경과 종목을 지표 종목으로 바꾸는 입찰입니다. 응찰률은 응찰금액÷입찰금액입니다."),
      node("p","reading-note","이 사이트의 규칙 판정에 쓰지 않는 참고 자료입니다. 숫자는 보도자료·결과 공고에서 옮긴 값이며, "
        +(statedPrevShown ? "비중·합계는 이 사이트의 계산값이고, 전월 대비(보도자료 문구)는 보도자료에 적힌 숫자입니다." : "비중·전월 대비·합계는 이 사이트의 계산값입니다.")),
      node("p","market-source","자료: 재정경제부 ",sourceLink("보도자료(국고채 발행 계획)",MOFE_PLANS)," · ",sourceLink("국채 입찰 결과 공고",MOFE_RESULTS),
        latest ? node("span",""," · ",sourceLink(monthLabel(latest.month)+" 계획 원문",latest.source_url)) : null));
    return panel;
  }
  function setView(view) {
    const on=view==="korea" || view.startsWith("korea-");
    document.getElementById("korea-market").hidden=!on;
    document.getElementById("korea-teaser").hidden=view!=="all";
    const group=view==="korea-credit"?"credit":view==="korea-flows"?"flows":"rates";
    document.querySelectorAll("#korea-tabs a").forEach(a=>{
      if(a.dataset.group===group)a.setAttribute("aria-current","page");else a.removeAttribute("aria-current");
    });
    document.querySelectorAll(".market-group").forEach(s=>{s.hidden=s.dataset.group!==group;});
  }
  function render(value, status=null) {
    if(!value || value.schema!==1 || !Array.isArray(value.cards)) throw new Error("Invalid Korean market data");
    data=value; attempt=status; refreshHealth();
    const content=document.getElementById("korea-market-content");content.replaceChildren();
    for(const [id,title] of Object.entries(groups)) {
      const section=node("section","market-group");section.dataset.group=id;
      section.append(node("h2","",title),node("div","market-grid",...data.cards.filter(c=>c.group===id).map(metricCard)));
      if(!data.cards.some(c=>c.group===id))section.append(node("p","market-warning","이 영역의 자료를 불러오지 못했습니다."));
      if(id==="flows")section.append(auctionPanels(),node("div","auction-grid",issuancePanel()));
      content.append(section);
    }
    const teaser=document.getElementById("korea-teaser-values");teaser.replaceChildren();
    for(const key of ["kr_us","aa_spread","foreign10"]) {
      const c=data.cards.find(c=>c.key===key);if(!c)continue;
      const a=node("a","metric",node("span","",c.title),node("strong","",number(c.metrics?.value,c.unit,c.unit==="계약")),node("small","",c.metrics?.date||"자료일 없음"));   // 카드와 같은 꼴(계약수는 + 부호)
      a.href=c.group==="rates"?"#korea":"#korea-"+c.group;
      const warning=node("small","market-warning"); warning.dataset.marketFeed=c.feed; warning.dataset.marketDate=c.metrics?.date || "unknown"; a.append(warning);
      teaser.append(a);
    }
    document.getElementById("korea-market-notices").replaceChildren(...(data.notices||[]).map(t=>node("p","",t)),
      node("p","",sourceLink("한국은행 스냅샷 이용지침","https://snapshot.bok.or.kr/guideline")));
    refreshHealth();
  }
  setInterval(refreshHealth,60000);
  document.addEventListener("visibilitychange",refreshHealth);
  return {render,setView,health,oldObservation,failLabel};
})();
