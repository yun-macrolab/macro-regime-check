/* Korean market reference panels. DOM text only; no external runtime dependency. */
"use strict";
window.KoreaMarket = (() => {
  let data = null;
  const names = {credit:"회사채 스프레드", money:"CD·CP", rates:"한미 국채", foreign3:"외국인 3년 선물", foreign10:"외국인 10년 선물", calendar:"입찰 일정", auctions:"입찰 결과", offerings:"입찰 예정액"};
  const groups = {rates:"금리·커브", credit:"신용·단기자금", flows:"수급·입찰"};
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
  function feedNote(key) {
    const f = data?.feeds?.[key];
    return !f?.ok ? "수신 실패 · 마지막 성공 자료" : "";
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
    const note=[feedNote(c.feed),c.stale ? "최근 관측이 7일 이상 지났습니다" : ""].filter(Boolean).join(" · ");
    if(note) card.append(node("p","market-warning",note));
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
      schedule.append(table(["입찰일","만기","예정액"],cal.rows.map(r=>{
        const result=(data.auctions||[]).find(a=>a.date===r.date && a.tenor===r.tenor);
        const offer=result || (data.offerings||[]).find(a=>a.date===r.date && a.tenor===r.tenor);
        return [r.date,r.tenor,offer?sourceLink(number(offer.offered_100m,"억원"),offer.source_url):sourceLink("공고 확인","https://ktb.mofe.go.kr/isuNdReprchsPblanc.do")];
      }),"국고채 월별 입찰 일정"));
      schedule.append(node("p","market-source",sourceLink("공식 월별 일정",cal.source_url)," · 일반 국고채 경쟁입찰 예정액입니다. 확인된 발행·결과 공고만 숫자로 표시하며 금액을 누르면 원문으로 이동합니다."));
    } else schedule.append(node("p","market-warning","일정을 불러오지 못했습니다."));
    const results=node("article","panel",node("h3","","최근 국고채 입찰 결과"));
    if(feedNote("auctions"))results.append(node("p","market-warning",feedNote("auctions")));
    if(data.auctions?.length) results.append(table(["입찰일","만기","입찰금액","응찰률","평균 낙찰금리","원문"],data.auctions.map(a=>
      [a.date,a.tenor,number(a.offered_100m,"억원"),number(a.bid_cover_pct,"%"),number(a.yield_pct,"%"),sourceLink("결과",a.source_url)]),"최근 국고채 경쟁입찰 결과"));
    else results.append(node("p","market-warning","확인된 입찰 결과가 없습니다."));
    results.append(node("p","reading-note","응찰률은 응찰금액÷입찰금액입니다. 만기·발행 규모가 다른 입찰을 숫자 하나로 비교하지 마세요. 최근 공고 목록에서 확인한 일반 국고채 경쟁입찰만 표시합니다."),
      node("p","market-source",sourceLink("자료: 공식 국채시장 입찰 결과","https://ktb.mofe.go.kr/bidResult.do")));
    wrap.append(schedule,results);return wrap;
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
  function render(value) {
    if(!value || value.schema!==1 || !Array.isArray(value.cards)) throw new Error("Invalid Korean market data");
    data=value;
    const failures=Object.keys(data.feeds).filter(k=>!data.feeds[k].ok);
    document.getElementById("korea-market-status").textContent="한국 자료 확인: "+new Date(data.checked_at).toLocaleString("ko-KR",{timeZone:"Asia/Seoul"})+" (KST)"+
      (failures.length?" · 수신 실패: "+failures.map(k=>names[k]||k).join(", "):" · 각 지표의 관측일을 확인하세요");
    const content=document.getElementById("korea-market-content");content.replaceChildren();
    for(const [id,title] of Object.entries(groups)) {
      const section=node("section","market-group");section.dataset.group=id;
      section.append(node("h2","",title),node("div","market-grid",...data.cards.filter(c=>c.group===id).map(metricCard)));
      if(!data.cards.some(c=>c.group===id))section.append(node("p","market-warning","이 영역의 자료를 불러오지 못했습니다."));
      if(id==="flows")section.append(auctionPanels());
      content.append(section);
    }
    const teaser=document.getElementById("korea-teaser-values");teaser.replaceChildren();
    for(const key of ["kr_us","aa_spread","foreign10"]) {
      const c=data.cards.find(c=>c.key===key);if(!c)continue;
      const a=node("a","metric",node("span","",c.title),node("strong","",number(c.metrics?.value,c.unit)),node("small","",c.metrics?.date||"자료일 없음"));
      a.href=c.group==="rates"?"#korea":"#korea-"+c.group;
      if(feedNote(c.feed)||c.stale)a.append(node("small","market-warning","이전 자료 · 갱신 확인 필요"));
      teaser.append(a);
    }
    document.getElementById("korea-market-notices").replaceChildren(...(data.notices||[]).map(t=>node("p","",t)),
      node("p","",sourceLink("한국은행 스냅샷 이용지침","https://snapshot.bok.or.kr/guideline")));
    document.getElementById("korea-source-status").replaceChildren(...Object.entries(data.feeds).map(([key,f])=>node("li","",
      (names[key]||key)+": "+(f.ok?"수신 성공":"수신 실패")+" · 마지막 성공 "+(f.last_success||"없음"))));
  }
  return {render,setView};
})();
