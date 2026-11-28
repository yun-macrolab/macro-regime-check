/* 용어 사전 — 사이트에서 쓰는 낱말의 뜻을 모은 자료와 그리기. 화면 연결은 index.html이 한다.
   ENTRIES  한 줄에 한 항목, 꼴은 { id, term, def, see } 그대로다(scripts/test_glossary_site.py가 글자로 읽어 본다).
            def는 160자 이하의 합니다체 한두 문장. see는 관련 화면 id 또는 빈 글.
            사이트에만 있는 낱말과 표시의 뜻은 README.md의 해당 절에서 옮긴다. 문턱 숫자는 적지 않는다.
   render(container)  container 안을 <dl class="glossary"> 하나로 바꾼다. index.html의 el()을 쓰고, 글자는 전부 텍스트로만 넣는다.
   find(q)  낱말이 q로 시작하는(같은 것 포함, 대소문자 무시) 항목의 id 목록 — 명령줄 찾기용.
   바깥 요청과 바깥 링크는 없다. */
"use strict";
window.Glossary = (() => {
  // 관련 화면 링크의 이름 — index.html 메뉴의 이름(한국 시장의 두 갈래는 앞에 '한국'을 붙인다)
  const SCREENS = Object.freeze({ all: "전체", rates: "금리·커브", inflation: "물가", credit: "신용·경기", liquidity: "유동성",
    korea: "한국 시장", "korea-credit": "한국 신용·단기자금", "korea-flows": "한국 수급·입찰", ai: "AI 투자",
    ledger: "기록 장부", sources: "출처·갱신", evening: "저녁판", notes: "읽기 노트" });

  const ENTRIES = Object.freeze([
    // 단위와 시장 낱말
    { id: "bp", term: "bp와 %p", def: "%p(퍼센트포인트)는 퍼센트로 적은 두 값의 차이를 재는 단위입니다. bp(베이시스 포인트)는 그보다 작은 단위로, 1bp는 0.01%p입니다.", see: "" },
    { id: "bei", term: "BEI(손익분기 인플레이션)", def: "만기가 같은 명목 국채 금리에서 물가연동국채의 실질금리를 뺀 값입니다. 시장의 기대 인플레이션에 위험·유동성 프리미엄도 섞여 있습니다.", see: "inflation" },
    { id: "5y5y", term: "5년 뒤 5년", def: "지금부터 5년 뒤에 시작하는 5년 동안의 값을 시장 가격에서 계산한 것입니다. 이 사이트에서는 그 기간의 기대인플레이션 지표를 가리킵니다.", see: "inflation" },
    { id: "sofr", term: "SOFR", def: "미국 국채를 담보로 하루 동안 돈을 빌리는 거래의 금리를 모아 낸 지표입니다. 뉴욕 연은이 영업일마다 발표합니다.", see: "liquidity" },
    { id: "iorb", term: "IORB", def: "미국 은행이 연준에 맡긴 지급준비금에 연준이 주는 이자율입니다.", see: "liquidity" },
    { id: "tga", term: "TGA", def: "미국 재무부가 연준에 두고 쓰는 현금 계좌입니다. 다른 조건이 같으면 이 잔액이 늘 때 은행의 지급준비금은 줄어듭니다.", see: "liquidity" },
    { id: "rmp", term: "RMP(지준 관리 매입)", def: "연준이 지급준비금을 충분하게 유지하려고 단기 국채 등을 사들이는 것입니다. 만기가 되어 돌려받은 돈을 다시 넣는 재투자와는 따로 셉니다.", see: "liquidity" },
    { id: "h41", term: "H.4.1", def: "연준이 매주 내는 통계표로, 연준의 자산과 부채, 지급준비금 같은 재무상태를 보여 줍니다.", see: "liquidity" },
    { id: "srf", term: "SRF", def: "연준이 국채 등을 담보로 받고 정해 둔 금리로 하루짜리 자금을 빌려주는 상시 레포 창구입니다.", see: "liquidity" },
    { id: "ois", term: "OIS", def: "하루짜리 금리를 약정 기간 동안 복리로 쌓은 값과 고정금리를 맞바꾸는 금리 스와프입니다. 이 사이트의 국채–OIS 카드는 SOFR을 기준으로 한 OIS를 씁니다.", see: "rates" },
    { id: "par-zero", term: "par와 zero", def: "par 금리는 채권 가격이 액면가와 같아지게 하는 이표 금리이고, zero(현물) 금리는 만기에 한 번만 돈을 주는 채권의 금리입니다. 두 기준의 수준은 그대로 견주지 않습니다.", see: "rates" },
    { id: "term-premium", term: "기간 프리미엄", def: "장기 채권을 보유하는 불확실성에 대해 더 받는 보상입니다. 시장에서 바로 보이지 않아 모형으로 추정합니다.", see: "rates" },
    { id: "trp-tfp", term: "TRP와 TFP", def: "기간 프리미엄을 둘로 나눈 몫입니다. TRP는 금리가 움직일 위험을 지는 대가이고, TFP는 금리 위험 없이 돈을 오래 묶어 두는 대가입니다.", see: "rates" },
    { id: "kim-wright-acm", term: "Kim-Wright와 ACM", def: "둘 다 미국 국채의 기간 프리미엄을 추정하는 모형입니다. Kim-Wright는 연준 이사회, ACM은 뉴욕 연은의 추정치이며 두 모형의 수준은 서로 다릅니다.", see: "rates" },
    { id: "rho60", term: "ρ60(주가-금리 60영업일 상관)", def: "주가의 일간 수익률과 미 10년 금리의 일간 변화가 최근 60영업일 동안 함께 움직인 정도를 나타낸 상관계수입니다. 기준은 규칙 카드에 있습니다.", see: "rates" },
    { id: "2s10s", term: "2s10s", def: "10년 만기 국채 금리에서 2년 만기 국채 금리를 뺀 장단기 금리차입니다. 기준은 규칙 카드에 있습니다.", see: "rates" },
    // 신용·경기와 자료 이름
    { id: "sahm", term: "Sahm형 실업률 규칙", def: "실업률의 3개월 평균이 앞선 기간의 가장 낮은 수준보다 얼마나 높아졌는지 보는 방식의 규칙입니다. 기준은 규칙 카드에 있습니다.", see: "credit" },
    { id: "ndfi", term: "NDFI", def: "예금을 받지 않는 비은행 금융기관을 말합니다. 이 사이트는 은행이 이런 기관에 빌려준 대출의 흐름을 봅니다.", see: "credit" },
    { id: "ci-loans", term: "C&I 대출", def: "은행이 기업에 빌려주는 상업·산업 대출입니다. 부동산 담보 대출과는 따로 집계합니다.", see: "credit" },
    { id: "sloos", term: "SLOOS", def: "연준이 분기마다 은행의 대출 담당자에게 대출 기준과 수요의 변화를 묻는 설문 조사입니다.", see: "ai" },
    { id: "nfci", term: "NFCI", def: "시카고 연은이 매주 내는 미국 금융 여건 지수로, 값이 클수록 여건이 빠듯하다는 뜻입니다. 이 사이트는 그 가운데 신용 하위 지수를 씁니다.", see: "ai" },
    { id: "ebp", term: "EBP", def: "회사채 가산금리에서 부도 위험으로 설명되는 몫을 빼고 남은 초과 채권 프리미엄입니다. 연준 이사회가 월간 자료로 냅니다.", see: "ai" },
    { id: "cmdi", term: "CMDI", def: "뉴욕 연은이 내는 회사채 시장 스트레스 지수입니다. 발행 시장과 유통 시장의 가격·거래 지표를 묶어 시장 기능이 얼마나 나빠졌는지 봅니다.", see: "ai" },
    { id: "tic", term: "TIC", def: "미국 재무부의 국제 자본 흐름 통계 체계입니다. 해외가 보유한 미국 국채의 통계도 여기서 나옵니다.", see: "rates" },
    { id: "mspd", term: "MSPD", def: "미국 재무부가 매달 내는 공공부채 월간 명세서입니다. 시장성 국채의 종목별 잔액이 실립니다.", see: "liquidity" },
    { id: "soma", term: "SOMA", def: "연준이 공개시장 운영으로 보유한 증권을 담는 계정이며, 뉴욕 연은이 관리합니다.", see: "liquidity" },
    // 한국 시장과 파생상품
    { id: "minpyeong", term: "민평3사", def: "민간 채권평가사 세 곳이 평가한 금리의 평균을 가리킵니다. 최종호가 금리와는 평가 기준이 다릅니다.", see: "korea" },
    { id: "msb", term: "통안증권", def: "통화안정증권을 줄인 말로, 한국은행이 시중의 유동성을 조절하려고 발행하는 증권입니다.", see: "korea-flows" },
    { id: "ctd", term: "CTD", def: "국채선물을 실물 채권으로 결제할 때, 인도할 수 있는 채권 가운데 인도하는 쪽의 비용이 가장 적게 드는 채권(최저가 인도 채권)입니다.", see: "" },
    { id: "irs", term: "IRS", def: "정해진 기간 동안 같은 통화의 고정금리 이자와 변동금리 이자를 맞바꾸는 금리 스와프입니다.", see: "korea" },
    { id: "crs", term: "CRS", def: "서로 다른 통화의 원금과 이자를 정해진 기간 동안 맞바꾸는 통화 스와프입니다.", see: "korea" },
    // 이 사이트의 낱말 — 뜻은 README.md에서 옮긴다
    { id: "met", term: "충족", def: "규칙에 적힌 조건이 성립한다는 사실만 뜻하는 판정입니다. 기준은 규칙 카드에 있습니다.", see: "all" },
    { id: "not-met", term: "미충족", def: "규칙에 적힌 조건이 성립하지 않는다는 판정입니다. 기준은 규칙 카드에 있습니다.", see: "all" },
    { id: "unknown", term: "판정 불가", def: "자료가 모자라 충족인지 미충족인지 결론이 나지 않는다는 표시입니다. 자료 일부가 없어도 결론이 나는 경우는 충족이나 미충족으로 적습니다.", see: "all" },
    { id: "core-signals", term: "핵심 신호", def: "시나리오 이름표가 있는 규칙 가운데 충족한 수를 n/m 꼴로 적은 것입니다. 중립 규칙은 따로 셉니다.", see: "all" },
    { id: "neutral-rule", term: "중립 규칙", def: "시나리오 이름표가 없는 규칙으로, 이름표 자리에는 '—'를 적습니다. 핵심 신호에 넣지 않고 따로 셉니다.", see: "all" },
    { id: "regime-candidate", term: "국면 후보", def: "S&P 500의 13주 방향과 미 10년 금리의 13주 변화를 네 갈래로 나눈 참고값입니다. 완충 구간이면 공개 계산에서는 '판정불가'로 둡니다.", see: "all" },
    { id: "scenario-tag", term: "시나리오 이름표", def: "규칙 카드의 해석 줄에 붙는 표시로, 운영자가 정한 이름표이고 뜻은 공개하지 않습니다.", see: "all" },
    { id: "reference-card", term: "참고 카드", def: "규칙이 아닌 숫자를 모아 보여 주는 카드입니다. 규칙 수에 들지 않고 충족·미충족 판정이 없습니다.", see: "" },
    { id: "measurement", term: "측정 기록", def: "과거에 일어난 일이나 과거 자료로 잰 숫자를 정해 둔 방법이나 날짜와 함께 적어 둔 것입니다. 예측이 아닙니다.", see: "ledger" },
    { id: "not-received", term: "받지 못함(미수신)", def: "자료를 새로 받지 못했다는 표시입니다. 참고 카드는 직전 값이 있으면 '받지 못함'과 함께 남기고, 없으면 '미수신'이나 '자료 없음'으로 적습니다.", see: "sources" },
    { id: "site-calc", term: "이 사이트의 계산값", def: "원 출처 기관이 발표한 값이 아니라, 이 사이트가 받은 자료로 계산한 값이라는 표시입니다.", see: "" },
    { id: "before-protocol", term: "약속 전", def: "평가 약속이나 판단 연표 약속을 정한 날보다 앞선 전환이나 주라는 표시입니다. 목록에는 싣지만 요약에서는 뺍니다.", see: "ledger" },
    // 표시 읽는 법
    { id: "mark-reference", term: "참고 — 예측 아님", def: "참고로 싣는 글이나 숫자이며 예측이 아니라는 표시입니다. 카드에 따라 '참고 — 금리 예측 아님'처럼 낱말이 조금 다릅니다.", see: "" },
    { id: "mark-measurement", term: "측정 기록 — 예측 아님", def: "기록 장부와 판단 연표처럼 미리 정해 둔 방법대로 적은 기록이며, 예측이 아니라는 표시입니다.", see: "ledger" },
    { id: "mark-comparison", term: "공개 기록 대조 — 예측 아님", def: "날짜별 공개 기록끼리 견주어 달라진 것을 보이는 칸이며, 예측이 아니라는 표시입니다.", see: "all" },
    { id: "mark-grid-name", term: "운영자 판단 격자의 칸 이름(운영자 메모)", def: "노동 상태와 물가 상태를 엮은 격자에서 운영자가 칸마다 메모해 둔 이름입니다. 예측이 아니고, 예측력은 검증하지 않았습니다.", see: "all" },
    { id: "mark-auto", term: "자동 분류", def: "연준 인물 페이지에서 AI가 기사를 읽고 새 발언을 운영자가 정리한 기준선에 견준 결과입니다. 사람 확인 없이 올라가 틀릴 수 있고, 예측이 아닙니다.", see: "" },
    { id: "mark-appraiser", term: "평가사 산출값 · AI 요약", def: "'평가사 산출값'은 평가사 주간 보고서의 숫자를 옮긴 값이며, 스왑 스프레드·베이시스는 그 값을 이 사이트가 뺀 것입니다. 'AI 요약'은 AI가 보고서를 읽고 쓴 글이라 틀릴 수 있습니다.", see: "korea" },
  ]);

  // container 안을 용어 목록 하나로 바꾼다. 자리나 el()이 없으면 아무것도 하지 않는다
  function render(container) {
    if (!container || typeof el !== "function") return;
    container.replaceChildren(el("dl", { class: "glossary" }, ...ENTRIES.flatMap(e => [
      el("dt", { id: "g-" + e.id }, e.term),
      el("dd", {}, e.def, e.see ? el("span", { class: "glossary-see" }, " 관련 화면: ",
        el("a", { href: "#" + e.see }, SCREENS[e.see])) : null)])));
  }

  // 낱말이 입력과 같거나 입력으로 시작하는 항목의 id(사전 차례). 빈 입력이나 글이 아닌 값은 빈 목록
  function find(q) {
    const s = typeof q === "string" ? q.trim().toLowerCase() : "";
    return s ? ENTRIES.filter(e => e.term.toLowerCase().startsWith(s)).map(e => e.id) : [];
  }

  return Object.freeze({ ENTRIES, render, find });
})();
