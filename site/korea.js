/* Korean market reference panels. DOM text only; no external runtime dependency. */
"use strict";
window.KoreaMarket = (() => {
  let data = null, attempt = null, healthState = null;
  const names = {credit:"회사채 스프레드", money:"CD·CP", rates:"한미 국채", foreign3:"외국인 3년 선물", foreign10:"외국인 10년 선물", calendar:"입찰 일정", auctions:"입찰 결과", offerings:"입찰 예정액", ktb_plans:"국고채 발행계획", ktb_ops:"매입·교환 결과"};
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
  const unreadable = {auctions:"입찰 결과 공고 형식 확인 실패", ktb_plans:"발행계획 보도자료 형식 확인 실패", ktb_ops:"매입·교환 결과 공고 형식 확인 실패"};
  function failLabel(key, f) {      // 같은 코드라도 묶음마다 읽은 공고가 다르다(입찰 결과·발행계획·매입/교환 = 재정경제부, 예정액 = 한국은행)
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
    const spec = {key:c.key, title:c.title, unit:c.unit, zero:c.unit!=="%", threshold:null, years:1,
      source_note:"자료: "+c.source.name+" · 변화·분포는 이 사이트의 계산값", note:null, notices:[],
      lines:[{key:c.key,label:c.title,role:"series",points:c.points,series:[],derived:["kr_us","kr_curve","cp_cd"].includes(c.key)}]};
    try { return window.MacroCharts.lineChart(spec,{height:180,caption:false}); } catch { return node("p","muted","차트를 표시하지 못했습니다. 표의 수치를 확인해 주세요."); }
  }
  function metricCard(c) {
    const m=c.metrics;
    const card=node("article","market-card",node("h3","",c.title),node("p","market-question",c.note));
    card.append(node("div","market-value",node("strong","",number(m?.value,c.unit,c.unit==="계약")),node("span","muted",m?.date || "자료일 없음")));
    const warning=node("p","market-warning"); warning.dataset.marketFeed=c.feed; warning.dataset.marketDate=m?.date || "unknown";
    card.append(warning);
    const stats=node("div","market-deltas");
    for(const n of c.unit==="계약"?[1,5,20]:[1,5,20]) {
      const v=c.unit==="계약"?m?.sums?.[n]:m?.changes?.[n];
      const label=c.unit==="계약"?(n===1?"당일":"최근 "+n+"관측일 누적"):(n+"관측일 전 대비");
      const item=node("div","",node("span","",label),node("strong","",number(v?.value,c.unit==="계약"?"계약":"bp",true)));
      if(v) item.title="비교 시작일: "+v.from;
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
  function auctionPanels() {
    const wrap=node("div","auction-grid");
    const cal=data.calendar;
    const schedule=node("article","panel",node("h3","","국고채 입찰 일정"));
    if(cal) {
      schedule.append(node("p","muted",cal.month+" 공식 일정 · "+(feedNote("calendar") || "공고에 따라 변경될 수 있습니다")));
      if(feedNote("offerings") || feedNote("auctions"))schedule.append(node("p","market-warning","입찰금액: "+[feedNote("offerings"),feedNote("auctions")].filter(Boolean).join(" · ")));
      const kept=new Set((data.offerings||[]).map(o=>o.id)), skipped=data.feeds?.offerings?.skipped;
      const unread=Array.isArray(skipped) ? skipped.filter(s=>!kept.has(s.id)) : [];   // 전에 읽은 값이 남은 공고는 빼고
      if(unread.length)schedule.append(node("p","market-warning","입찰 예정액: 발행공고 "+unread.length+"건을 읽지 못했습니다. 금액이 없는 회차는 공고 목록으로 연결합니다."));
      schedule.append(table(["입찰일","만기","예정액"],cal.rows.map(r=>{
        const result=(data.auctions||[]).find(a=>a.date===r.date && a.tenor===r.tenor);
        const offer=result || (data.offerings||[]).find(a=>a.date===r.date && a.tenor===r.tenor);
        return [r.date,r.tenor,offer?sourceLink(number(offer.offered_100m,"억원"),offer.source_url):sourceLink("공고 확인","https://ktb.mofe.go.kr/isuNdReprchsPblanc.do")];
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
      node("p","market-source",sourceLink("자료: 공식 국채시장 입찰 결과","https://ktb.mofe.go.kr/bidResult.do")));
    wrap.append(schedule,results);return wrap;
  }
  // 국고채 발행계획·매입(바이백)·교환 — 재정경제부 보도자료와 입찰 결과 공고의 숫자. 화면 글은 아래 고정 문구뿐이다(방향·평가 낱말 없음)
  const MOFE_PLANS="https://mofe.go.kr/nw/nes/nesdta.do?searchBbsId1=MOSFBBS_000000000028&menuNo=4010100";
  const MOFE_RESULTS="https://mofe.go.kr/st/fnancstats/ktb50201.do?bbsId=MOSFBBS_000000000049&menuNo=6050300";
  function jo(v, signed=false) {     // 억원 → 조원(소수 한 자리)
    if(!Number.isFinite(v)) return "자료 없음";
    const x=v/10000;
    return (signed && x>0 ? "+" : "")+x.toLocaleString("ko-KR",{minimumFractionDigits:1,maximumFractionDigits:1})+"조원";
  }
  const pct = v => Number.isFinite(v) ? v.toLocaleString("ko-KR",{maximumFractionDigits:1})+"%" : "자료 없음";
  const monthLabel = m => typeof m==="string" && /^\d{4}-\d{2}$/.test(m) ? m.slice(0,4)+"년 "+(+m.slice(5))+"월" : "달 미상";
  function shareChart(plans) {
    if(!window.MacroCharts || plans.length<2) return null;
    const pts=k=>plans.filter(p=>Number.isFinite(p[k])).map(p=>[p.month+"-01",p[k]]);
    const spec={key:"ktb_long_share",title:"월별 경쟁입찰 계획 중 장기물 비중",unit:"%",zero:true,threshold:null,years:1,
      source_note:"자료: 재정경제부 월별 국고채 발행계획 보도자료 · 비중은 이 사이트의 계산값",note:null,notices:[],
      lines:[{key:"long",label:"20·30·50년 비중",role:"series",points:pts("long_share_pct"),series:[],derived:true},
             {key:"y30",label:"30년 비중",role:"series",points:pts("y30_share_pct"),series:[],derived:true}]};
    try { return node("div","",node("p","reading-note",spec.title),window.MacroCharts.lineChart(spec,{height:170,caption:false})); }
    catch { return node("p","muted","차트를 표시하지 못했습니다. 표의 수치를 확인해 주세요."); }
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
    for(const key of ["ktb_plans","ktb_ops"]) if(feedNote(key)) panel.append(node("p","market-warning",names[key]+": "+feedNote(key)));
    if(latest) {
      panel.append(node("p","muted",monthLabel(latest.month)+" 계획 · 보도자료 "+(latest.published||"날짜 미상")));
      panel.append(node("div","market-value",node("strong","",jo(latest.competitive_100m)),node("span","muted","경쟁입찰 발행 계획")));
      const stated=Number.isFinite(latest.stated_plan_change_100m) ? jo(latest.stated_plan_change_100m,true) : "보도자료에 언급 없음";
      const prev=Number.isFinite(sum.prev_month_change_100m) ? jo(sum.prev_month_change_100m,true)+" (계산값)"
        : Number.isFinite(latest.stated_prev_change_100m) ? jo(latest.stated_prev_change_100m,true)+" (보도자료)" : "전월 계획 없음";
      panel.append(node("div","market-deltas",
        node("div","",node("span","","전월 계획 대비"),node("strong","",prev)),
        node("div","",node("span","","당초 계획 대비(보도자료)"),node("strong","",stated)),
        node("div","",node("span","","20·30·50년 비중 · 30년"),node("strong","",pct(latest.long_share_pct)+" · "+pct(latest.y30_share_pct)))));
      const tenors=(Array.isArray(latest.tenors)?latest.tenors:[]).filter(t=>t && typeof t.tenor==="string");
      if(tenors.length) panel.append(table(["만기","경쟁입찰 계획","비중"],tenors.map(t=>[t.tenor,jo(t.amount_100m),
        pct(Number.isFinite(t.amount_100m) && latest.competitive_100m>0 ? Math.round(t.amount_100m/latest.competitive_100m*1000)/10 : NaN)]),
        monthLabel(latest.month)+" 만기별 경쟁입찰 계획"));
      panel.append(node("p","reading-note","이달 "+opPlan("매입(바이백) 계획",latest.buyback_plan)+" · "+opPlan("교환 계획",latest.exchange_plan)));
      panel.append(shareChart(plans) || node("p","muted","장기물 비중 그래프는 두 달 이상 자료가 모이면 표시합니다."));
    } else panel.append(node("p","market-warning","확인된 발행계획이 없습니다."));
    const p=sum.progress, progress=node("div","market-range");
    if(p && Array.isArray(p.months) && Array.isArray(p.missing)) {
      const head=p.year+"년 발행 실적 누계 "+jo(p.actual_100m)+" ("+p.months.length+"개월, "+monthLabel(p.through)+"까지)";
      if(!Number.isFinite(p.limit_100m)) progress.append(node("p","",head+" · 연간 한도 미등록"));
      else {
        progress.append(node("p","",head+" · 연간 한도 "+jo(p.limit_100m)+(Number.isFinite(p.pct) ? " 대비 "+pct(p.pct)+" (계산값)" : "")));
        if(Number.isFinite(p.pct)) {
          const track=node("div","range-track"), dot=node("span","range-dot");
          dot.style.left=Math.min(100,Math.max(0,p.pct))+"%"; track.append(dot);
          track.setAttribute("role","img"); track.setAttribute("aria-label","연간 한도 대비 발행 실적 누계 "+p.pct+"%"); progress.append(track);
        } else progress.append(node("small","","실적이 확인되지 않은 달("+p.missing.map(monthLabel).join(", ")+")이 있어 한도 대비 비율은 표시하지 않습니다."));
        progress.append(node("small",""," 연간 한도: ",sourceLink(p.year+"년 국고채 발행계획 보도자료("+p.limit_published+")",p.limit_source_url)));
      }
    } else progress.append(node("p","muted","발행 실적이 적힌 보도자료를 아직 확인하지 못했습니다."));
    panel.append(progress);
    const kept=new Set(ops.map(o=>o.id)), missed=data.feeds?.ktb_ops?.skipped;
    const unread=Array.isArray(missed) ? missed.filter(s=>!kept.has(s.id) && s.reason!=="not_tried") : [];
    if(unread.length) panel.append(node("p","market-warning","매입·교환 결과 공고 "+unread.length+"건을 읽지 못했습니다. 원문은 공식 결과 목록에서 확인해 주세요."));
    if(ops.length) panel.append(table(["입찰일","구분","입찰금액","응찰률","낙찰금액","원문"],ops.map(o=>
      [o.date,o.kind==="exchange"?"교환":o.kind==="buyback"?"매입":"기타",jo(o.offered_100m),number(o.bid_cover_pct,"%"),jo(o.awarded_100m),sourceLink("결과",o.source_url)]),
      "최근 국고채 매입·교환 입찰 결과"));
    else panel.append(node("p","market-warning","확인된 매입·교환 결과가 없습니다."));
    panel.append(node("p","reading-note","경쟁입찰 계획은 비경쟁인수·교환을 뺀 금액이고, 발행 실적은 다음 달 보도자료에 적힌 전체 발행 규모입니다. 매입은 만기 전 국고채를 정부가 사들이는 입찰, 교환은 경과 종목을 지표 종목으로 바꾸는 입찰입니다. 응찰률은 응찰금액÷입찰금액입니다."),
      node("p","reading-note","이 사이트의 규칙 판정에 쓰지 않는 참고 자료입니다. 숫자는 보도자료·결과 공고에서 옮긴 값이며, 비중·전월 대비·누계는 이 사이트의 계산값입니다."),
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
      const a=node("a","metric",node("span","",c.title),node("strong","",number(c.metrics?.value,c.unit)),node("small","",c.metrics?.date||"자료일 없음"));
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
