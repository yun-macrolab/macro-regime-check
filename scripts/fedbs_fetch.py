#!/usr/bin/env python3
"""참고 자료 — 연준 재무상태표(H.4.1 주간) (2026-11-03 추가, 사용자 결정: 운영자 비공개 결론 런 메일의 연준 재무상태표
주간 줄(fed_bs)을 공개 카드로 — 먼저 올려 써 보며 다듬기로).

공개 통계의 숫자와 산술(나눔·4주/13주 차·5영업일 최대)만 싣는다. 규칙이 아니다 — 충족·판정·문턱 표식이 없고, 판정·공개본·
그래프 스크립트는 이 파일(<out>/fedbs.json)을 읽지 않는다. 유동성 묶음에서 지준·재정 카드 바로 뒤의 카드이고, 규칙 카드
'지준과 통화승수'의 지준/GDP와 지준·재정 카드의 13주 나눔을 주간으로 읽는 재료다. 칸(ITEMS — 화면 차례):
  reserves  지준(주 평균 WRESBAL)과 지준/명목GDP — regime_check.compute와 같은 식(liquidity_fetch.reserves_gdp: 주 평균의 마지막
            값 ÷ 1000 ÷ 마지막 분기 GDP × 100)이라 규칙 카드와 같은 숫자다(테스트가 견준다). 규칙 하한(regime_rules.TH
            ['reserves_gdp_low'])의 차 %p·bn. 4주 평균 = (최근 4주 WRESBAL 평균) ÷ 최신 GDP — 정의는 이것 하나(네 주가 이어질
            때만, 첫 주와 마지막 주가 21일 차). 분모 바뀜: 직전 fedbs.json의 주를 처음 실을 때의 GDP(first)와 이번 GDP가
            다르면(새 분기·개정) 같은 지준으로 견준 분모 몫(%p) — 같은 주를 다시 실을 때는 그 주의 견줌을 그대로 두고, 같은 주
            안에서 GDP만 바뀌면 다음 주가 싣는다(비공개가 메일로 실은 주의 GDP와 견주는 것과 같은 뜻). 그래프: 최근 52주 지준과
            규칙 하한 × 마지막 분기 GDP(지난 주들도 지금 GDP로 그은 선)
  dec       지준 변화의 나눔 4주/13주 — 수요일 수준(WRBWFRBL) = 재무부 현금 TGA(WDTGAL) · 익일물 역레포(WLRRAOL — H.4.1
            '역레포: 그 밖', 익일물 역레포 기구가 대부분) · 해외 공적 역레포 풀(WLRRAFOIAL — 부채 쪽, 자산 쪽 FIMA 레포 기구가
            아니다) · 연준 단기채(WSHOBL) · 이표채(WSHONBNL) · MBS(WSHOMCB) · 현금 통화(WCICL) · 그 밖(나머지). 부호는 지준 쪽.
            창 규칙은 liquidity_fetch.calc_reserves와 같다(여덟 시리즈가 모두 있는 마지막 수요일과 그 28·91일 전 이하 마지막
            공통 관측 — NEAR_DAYS 안). 13주는 지준·재정 카드의 13주 나눔과 같은 창·같은 값이다(역레포 = 익일물 + 해외 공적,
            그 카드의 그 밖 = MBS + 현금 통화 + 이 카드의 그 밖 — 테스트가 견준다). 보이는 정수끼리 합이 맞게 '그 밖'이 반올림을
            받는다. 1주는 15일·월말 하루에 크게 흔들려 싣지 않는다. 두 창의 출발·끝 수요일이 월말(분기 끝 달이면 분기말)·15일이면
            표시한다(창은 옮기지 않는다)
  spread    SOFR − IORB 최근 5영업일(SOFR의 마지막 관측 다섯): 최대 bp와 날짜(같은 값이면 이른 날)·0보다 큰 날 n/m(그 SOFR
            날짜 이하 IORB가 3일보다 멀면 그날은 비우고 m에서 뺀다)·월말·15일 표시
  srf       상시 레포(SRF) 이용(RPONTTLD) 최근 5영업일 최대 bn과 날짜
  rrp       익일물 역레포(RRPONTSYD) 마지막 값
  rmp_view  지준 관리 매입(RMP) 칸 — 이 카드에만 있는 칸(비공개 메일 줄에는 없다). 2026-11-03 사용자 결정 '앞에 2개 실행'으로 생긴
            계획 줄(rmp_plan)·대조 줄(rmp)을 같은 날 '잘 읽히지 않는다 — 추천안대로'로 한 칸에 모았다: 머리 한 줄 · 다음 날짜 ·
            묶음 표 · RMP 시작 뒤 지준 나눔 · 하한의 달러 크기 · 운영 결과 대조의 차 한 줄. 재료는 넷이다:
              계획    뉴욕 연은 'Treasury Securities Operational Details' 페이지(PLAN_URL — 정적 HTML)의 표(머리 Period · Planned
                      Operation Amount …, 탭 이름 'Operation Period Details')를 1번 받아 행마다 기간·계획 문장·다음 공지(Next
                      Schedule Release) 칸을 읽는다(parse_plan):
                기간    'M/D/YYYY - M/D/YYYY'(날짜 하나면 그 하루). 날짜 꼴이 아님·없는 날·끝이 시작보다 이름·PLAN_SPAN_MAX일
                        넘음은 그 행을 버리고 버린 수를 싣는다
                문장    정해 둔 꼴(PLAN_FORM) 하나만 읽는다 — 'The Desk plans to conduct approximately $X billion in
                        reinvestment purchases and' 다음에 'no reserve management purchases'(RMP 0) 또는 '(an additional )?
                        approximately $Y billion in reserve management purchases', 끝은 'over the noted monthly period.'(conduct
                        자리에 purchase도). 다른 꼴(소액 시험 운영·운영 없음·쿠폰 배분 문장·두 문장 등)은 '꼴 모름' — 숫자를 짓지
                        않는다. 금액은 페이지의 숫자 글 그대로(소수 자리까지)
                글      태그를 벗기고(<br>은 한 칸) &nbsp;·줄바꿈·여분 공백을 한 칸으로. 같은 기간이 여러 번이면 하나로 — 읽은
                        숫자가 다르면 꼴 모름. 표가 없으면 이 칸만 실패(table), PLAN_MAX바이트보다 크면 받지 않는다
                창      시작 달로 부른다 — RMP 시작 창(RMP_FROM 2025-12-12)이 든 달부터 페이지의 마지막 시작 달까지 달마다 그 달에
                        시작하는 기간 하나(여럿이면 꼴 모름, 없으면 '페이지에 없음'). 페이지 표의 기간 가운데 RMP_FROM 앞의 것
                        (2019~2025-11 — 다른 문장 꼴)은 쓰지 않는다
                머리    마지막 창(오늘이 그 기간 안이면 '지금 창', 아직 시작 전이면 '다음 창', 끝났으면 '마지막 창' — 다음 창 계획은
                        페이지에 아직 없음): RMP 금액 · 같은 금액이 이어진 창 수(0이면 'n창째 0', 아니면 'n창째 같은 금액', 한
                        창이면 '지난 창 Y에서 바뀜') · RMP_FROM 창부터의 계획 누적(꼴 모름·없는 창이 하나라도 있으면 '—') · 그 창의
                        재투자. 마지막 창이 꼴 모름이면 숫자를 짓지 않는다
                표      같은 RMP가 이어진 창끼리 한 줄(GROUPS_MAX줄까지 — 그 앞의 창은 누적에만 든다): 창 수·누적·재투자 범위
                날짜    다음 두 계획 공지(마지막 시작 달의 다음 달부터 — 페이지의 다음 공지 칸에 날짜가 있으면 그 날, 비어 있으면
                        그 달 RMP_BDAY영업일 bday_n에 '께')와 다음 FOMC(주 칸과 같은 규칙)
              대조    뉴욕 연은 Markets API 국채 운영 결과(요청 1번 — OPS_FROM(RMP 시작 달 1일) ~ 오늘, OPS_MAX바이트 상한)를 창마다
                      더해 그 달 MBS 상환(WSHOMCB)을 뺀다(rmp_window) — 화면엔 끝난 창의 '대조 − 계획 RMP' 범위 한 줄만, 창마다의
                      운영 수·합·운영일·상환 수요일·대조값은 values.checks에 남긴다:
                매입    운영 결과(auctionStatus 'Results')가 나온 매입(operationDirection 'P') 운영의 받아들인 금액
                        (totalParAmtAccepted, 달러) 합 — 1억 달러(SMALL_MIN) 미만은 소액 시험 운영(small value exercise —
                        2026-06-23 FRN 매입 2,500만 달러처럼 따로 공지)이라 빼고(뺀 수는 checks에), 매각('S')은 세지 않는다. 잔존
                        3년 이하 이표채로 옮긴 매입도 든다. 같은 operationId는 하나
                창      M월 창 = 계획 페이지에 M월에 시작하는 기간이 하나 있으면 그 기간(시작~끝, 양 끝 포함 — bound 'plan'),
                        없으면(그 달 기간이 없거나 여럿) 운영일이 M월 9영업일(RMP_BDAY) 뒤이고 M+1월 9영업일 이하인 운영(bound
                        'rule') — 뉴욕 연은은 월 매입 금액을 그 달 9영업일께 다음 약 30일 치 일정과 함께 발표한다(운영 방침
                        2025-12-10). 2025-12~2026-10 열한 창의 공식 기간은 이 규칙과 같았다(2026-11-03). 영업일 = 평일 − 연방
                        공휴일(fed_holidays — 새해·MLK·대통령의 날·메모리얼·준틴스·독립기념일·노동절·콜럼버스·재향군인·추수감사절·
                        성탄. 일요일이면 월요일 대체, 토요일이면 대체 없음 — 연준은 그 앞 금요일에 연다). 이웃 창이 겹치거나 사이에
                        영업일이 비면(반 달씩 나눈 행 같은 꼴 — 2020-06~2021-02 페이지에 있다) 모든 창을 규칙으로 — 마지막 창은
                        그다음 달의 창과도 사이가 비는지 본다(plan_bounds·bday_gap). 공식 기간 행의 문장이 꼴 모름이어도 기간은
                        경계로 쓴다. 창이 끝났다 = 오늘이 창의 끝 날보다 뒤
                상환    M월 MBS 상환 = WSHOMCB(M−1월 상환 수요일) − WSHOMCB(M월 상환 수요일). 상환 수요일(paydown_wed) = 그 달
                        25일 이후 첫 수요일(25일이 수요일이면 그날) — 지니메이 20일·패니메이·프레디맥 25일 상환이 한 번씩 든다.
                        25일이 주말·연방 공휴일이면 패니메이·프레디맥 상환이 다음 영업일에 결제되므로 그날부터 센다 — 달라지는 것은
                        성탄이 수요일인 해(2024·2030·2041)의 12월뿐이고 그 달은 다음 수요일이다(12-25 수요일 수준엔 지니메이 몫만
                        든다 — 2024-12 실자료: 12-25 주 3.3bn·01-01 주 12.2bn). WSHOMCB는 H.4.1 MBS 보유 = 기관 MBS + 기관
                        CMBS다(뉴욕 연은 SOMA 요약의 두 칸 합과 같다 — 2026-11-03 확인)
                대조    끝난 창만 — 보이는 소수 한 자리의 매입 − 보이는 소수 한 자리의 상환, 그것과 계획 RMP의 차(소수 한 자리).
                        끝나지 않은 창은 운영 수·합·운영일만 남기고 상환과 견주지 않는다
                한계    공식 수치가 아니라 운영 결과로 셈한 대조다. 재투자는 기관채·MBS는 그 달 예상 상환, 기관 CMBS는 전달 실제
                        상환 기준이라(뉴욕 연은 FAQ) MBS는 예상과 실제 상환이 어긋날 수 있고, 기관 CMBS 상환은 WSHOMCB에 들어
                        있지만 재투자가 한 달 늦게 따라오며(작다), 기관채 상환은 WSHOMCB에 없어 빠진다(H.4.1 연방 기관채 보유 약
                        2.3bn — 2026-07~10 변화 없음). 공식 기간이 없는 달의 창 경계는 9영업일 규칙의 근사다
              시작 뒤 RMP_FROM 앞의 마지막 네 수요일과 마지막 네 수요일(BRIDGE 일곱 시리즈가 모두 있는 날, 이어진 네 주 — 한 주라도
                      빠지면 비운다)의 수요일 수준 평균 차: 지준 = 연준 단기채+MBS · 재무부 현금(TGA) · 현금 통화 · 역레포(익일물 +
                      해외 공적) · 그 밖(이표채·TIPS·대출·기타 부채 등의 나머지). 부호는 지준 쪽, 보이는 정수끼리 합이 맞게 '그
                      밖'이 반올림 차를 받는다. 나눔 칸이 이미 받는 시리즈뿐이라 새 요청이 없다. 한 주 끝점으로 셈하면 재무부 현금
                      한 주치에 부호까지 바뀌어(2026-11-03 실자료: 2025-12-10에서 2026-10-28로 지준 −78.5bn, 출발을 한 주 앞
                      12-03으로 옮기면 +17.1bn) 네 주 평균만 싣는다
              하한    규칙 하한(regime_rules.TH['reserves_gdp_low']) × RMP_FROM이 든 분기의 명목 GDP와 × 마지막 분기 GDP(현재
                      개정치 — 지준 칸과 같은 분기). 이 사이트 규칙 카드의 추정값이고 연준이 말하는 'ample'의 기준이 아니라는
                      이름표와 단기자금 칸 가리킴을 함께 싣는다
            판정 낱말 없이 숫자·날짜·뺄셈만. 화면에서 뺀 셈 규칙(문장 꼴·창 경계·상환 수요일·소액 운영·한계)은 README 'RMP 칸의 셈
            규칙' 절에 있다. compute에 공식 계획(plan)을 넘기지 않는 호출(비공개 쪽 짝 테스트 등)에서는 이 칸을 셈하지 않고 파일에도
            넣지 않는다. 운영 결과(ops)를 받지 못하면 대조 한 줄만 '미수신', FRED 시리즈를 받지 못하면 그 줄(시작 뒤 나눔·하한)만
  week      그 H.4.1 주(목~수)가 15일·월말·FOMC 결정일을 품는지('FOMC 뒤 첫 H.4.1' — 결정일(수)이 그 주 마지막 날이라 그 주
            숫자는 시행 전 값)와 다음 FOMC 결정일(실행 시각에 아직 성명 — 결정일 14:00 미 동부 — 이 나오지 않은 첫 회의: 예약
            실행 UTC 22:17은 결정일에도 성명 뒤라 그날 회의는 '다음'이 아니다). FOMC 일정은 이 파일의 FOMC 표(2026년은
            site/people-data.js의 회의 장부와 같다, 테스트가 견준다. 2027년은 연준 FOMC 일정 페이지(2026-10-28 갱신)의 여덟
            회의 — 연준 고지대로 각 회의는 직전 회의에서 확정되기 전까지 잠정이라 '(잠정)')
산식은 비공개 파이프라인의 fed_bs.py와 같다(저장소를 넘어 가져오지 않고 여기서 따로 쓴다 — 고치면 양쪽을 같이 — rmp_view
칸은 이 카드에만 있다). 비공개 쪽과 다른 곳: 상태 파일이 없다 — 날마다 받고, '분모 바뀜'은 직전 fedbs.json의 주를 처음 실을 때의
GDP와 견준다(비공개는 메일로 실은 주의 GDP와 — 같은 뜻, 같은 주를 다시 실을 때도 그 견줌을 보인다).
화면(site/fedbs.js)에는 이 파일 밖의 고정 글 '연준 대차대조표 정책 — 1차 출처'(기준일 2026-11-03, 사람이 고친다)도 있다.
같은 주를 다시 실을 때 '싣는 때' 규칙(새 주 한 번·보완·미수신 한 줄)은 없다 — 카드는 늘 마지막으로 받은 값을 보인다.
날짜는 YYYY-MM-DD(RMP 칸은 같은 해 안이면 창 범위의 둘째 날짜와 다음 날짜를 MM-DD로 줄인다), 분기는 2026Q3, 음수 부호는
'-'(지준·재정 카드와 같은 꼴), '→' 대신 '~'·'에서 …로'.

자료 이용 조건(2026-11-03 이 샌드박스에서 FRED 시리즈 쪽 JSON-LD의 license와 Suggested Citation으로 확인 — LICENCE):
  'Public Domain: Citation Requested' — 연준 이사회 H.4.1 열(WRESBAL·WRBWFRBL·WDTGAL·WLRRAOL·WLRRAFOIAL·WSHOBL·WSHONBNL·
  WSHOMCB·WCICL)·IORB, BEA GDP. FRED 권장 인용을 자료 파일(sources[].citation)에 싣는다.
  'Copyrighted: Citation Required' — 뉴욕 연은 SOFR·RPONTTLD·RRPONTSYD. FRED 권장 인용을 카드에 글자로, 뉴욕 연은 이용약관의
  기본 출처 형식(© 연도)과 관계없음 고지, 계산값 표시(한·영)를 함께 — SOFR은 참조금리 고지·DTCC 문장도(규칙 카드 SOFR과
  같은 문구, render_public). 그 밖의 조건이 붙은 시리즈는 이 파일에 넣지 않는다(테스트가 목록을 고정한다).
  뉴욕 연은 공식 계획 페이지·국채 운영 결과(Markets API) — rmp_view 칸: newyorkfed.org 이용약관 — 수급 카드의 딜러 통계와 같은
  꼴로 기본 출처 형식(© 연도)·관계없음 고지에, 계획 금액은 정해 둔 꼴만 옮겼고 누적·묶음·연속 창 수·대조는 이 사이트의 계산값이라는
  표시를 한 쌍(한·영, RMP_NOTICE)으로 싣고, 권장 인용 'Federal Reserve Bank of New York, Treasury Securities Operational Details,
  retrieved from <주소>, <날짜>.'와 국채 운영 결과의 인용을 sources[].citation(licence 'nyfed-terms')에 글자로. 주소는 글자로만
  (사이트는 FRED·GitHub에만 링크를 건다).

수신: FRED CSV 14개(기본 머리글 그대로 — 머리글을 더하면 FRED가 응답을 멈춘다, ai_invest_fetch.load_series), 요청마다 min(15초, 남은 예산),
수신 전체 BUDGET초(응답을 읽는 동안에도 본다). 그 뒤 뉴욕 연은 2번 — 국채 운영 결과(OPS_URL?startDate=…&endDate=… — RMP 시작 달
1일(OPS_FROM) ~ 오늘, 응답 OPS_MAX바이트 상한)와 공식 계획 페이지(PLAN_URL) — 둘 다 credit_fetch.fetch_bytes로(이 프로젝트를 밝히는
User-Agent·이메일 없음, https·같은 호스트만, 다른 곳으로 넘겨지면 받지 않음), FRED와 따로 두 요청을 합쳐 OPS_BUDGET초(요청 하나엔
min(10초, 남은 예산) — 운영 결과가 늦으면 계획 페이지는 남은 시간만). 받으면 원문을 <work>/fedbs/tsy_ops.json·tsy_plan.html에
둔다(공개 data에는 싣지 않는다, --offline이면 이것만 읽는다). 온라인에서 받지 못하면 캐시로 대신하지 않는다 — 계획 페이지를
받지 못하면 RMP 칸이 직전 값 + '받지 못함', 운영 결과를 받지 못하면 그 칸의 대조 한 줄만 '미수신'. 주간·일간 모두 실행마다 받는다(공개 쪽은 하루 1회 실행
— 상태 파일 없음).
H.4.1은 목요일 16:30(미 동부)에 나오고 FRED에 몇 분 안에 들어온다 — 예약 실행(UTC 22:17, 미 동부 같은 날 17:17·18:17)이 같은
날 받는다(국경일이 끼면 하루 늦게 나온다).

실패·이어 싣기·문구 원칙은 liquidity_fetch·oil_fetch와 같다: 칸마다 따로, 못 받은 칸은 직전 숫자를 '받지 못함'과 그날부터라는
날짜와 함께(직전 값이 없으면 사유만), 받은 자료가 직전보다 이르면 받지 않는다, 문구는 이 파일에 정해 둔 것뿐(오류 원문은 싣지
않는다), 같은 내용이면 다시 쓰지 않는다.

종료코드: 0 한 칸이라도 이번에 받음 / 1 하나도 못 받음(또는 파일을 쓰지 못함). 워크플로 단계는 continue-on-error, 알림 없음.

사용법: python scripts/fedbs_fetch.py [--out data] [--work .work] [--offline]
"""
import os, re, sys, json, time, argparse, datetime, urllib.parse, html.parser

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import regime_rules as rr                     # 규칙 하한(TH['reserves_gdp_low'])만 읽는다 — 공유 파일, 고치지 않는다
import render_public as rp                    # FRED 주소·SOFR 고지·뉴욕 연은 출처 형식
import ai_invest_fetch as ai                  # 수신(load_series)·쓰기·꼴 검사를 그대로 쓴다
import liquidity_fetch as liq                 # 지준/GDP 식(reserves_gdp)·13주 창 상수(WEEKS13·NEAR_DAYS)
import credit_fetch as cf                     # 뉴욕 연은 요청 한 건(fetch_bytes — 이 프로젝트를 밝히는 UA, 호스트·옮김 검사)

SCHEMA = 1
REPO = os.path.dirname(SCRIPTS)
DEFAULT_OUT = os.path.join(REPO, "data")
DEFAULT_WORK = os.path.join(REPO, ".work")
FILE = "fedbs.json"
CACHE = "fedbs"                               # <work>/fedbs/<ID>.csv

BUDGET = 60                                   # 수신 전체(초) — 워크플로 단계 제한(2분) 안에서 끝나게
WIN4, WIN13 = 28, liq.WEEKS13                 # 4주·13주(91일) — 창 규칙은 지준·재정 카드와 같다
NEAR_DAYS = liq.NEAR_DAYS
MM_DAYS = 5                                   # 단기자금 최근 5영업일(시리즈마다 마지막 관측 다섯)
IORB_GAP = 3                                  # SOFR 날짜 이하 IORB 관측이 이보다 멀면 그날은 비운다
CHART_WEEKS = 52
AVG4_DEF = "4주 평균 = (최근 4주 WRESBAL 평균) ÷ 최신 GDP"   # 정의는 이것 하나 — 비공개 fed_bs.AVG4_DEF와 같은 글

_BOARD = "Board of Governors of the Federal Reserve System (US)"
_NYFED = "Federal Reserve Bank of New York"
# FRED 권장 인용의 출처·제목(2026-11-03 시리즈 쪽 Suggested Citation 그대로)
SOURCES = {
    "WRESBAL": (rp.FRED_SOURCE["WRESBAL"], rp.FRED_TITLE["WRESBAL"]),
    "GDP": (rp.FRED_SOURCE["GDP"], rp.FRED_TITLE["GDP"]),
    "WRBWFRBL": (_BOARD, "Liabilities and Capital: Other Factors Draining Reserve Balances: Reserve Balances with Federal "
                         "Reserve Banks: Wednesday Level"),
    "WDTGAL": (_BOARD, "Liabilities and Capital: Liabilities: Deposits with F.R. Banks, Other Than Reserve Balances: "
                       "U.S. Treasury, General Account: Wednesday Level"),
    "WLRRAOL": (_BOARD, "Liabilities and Capital: Liabilities: Reverse Repurchase Agreements: Others: Wednesday Level"),
    "WLRRAFOIAL": (_BOARD, "Liabilities and Capital: Liabilities: Reverse Repurchase Agreements: Foreign Official and "
                           "International Accounts: Wednesday Level"),
    "WSHOBL": (_BOARD, "Assets: Securities Held Outright: U.S. Treasury Securities: Bills: Wednesday Level"),
    "WSHONBNL": (_BOARD, "Assets: Securities Held Outright: U.S. Treasury Securities: Notes and Bonds, Nominal: "
                         "Wednesday Level"),
    "WSHOMCB": (_BOARD, "Assets: Securities Held Outright: Mortgage-Backed Securities: Wednesday Level"),
    "WCICL": (_BOARD, "Liabilities and Capital: Other Factors Draining Reserve Balances: Currency in Circulation: "
                      "Wednesday Level"),
    "SOFR": (rp.FRED_SOURCE["SOFR"], rp.FRED_TITLE["SOFR"]),
    "IORB": (_BOARD, "Interest Rate on Reserve Balances (IORB Rate)"),
    "RPONTTLD": (_NYFED, "Overnight Repurchase Agreements: Total Securities Purchased by the Federal Reserve in the "
                         "Temporary Open Market Operations"),
    "RRPONTSYD": (_NYFED, "Overnight Reverse Repurchase Agreements: Treasury Securities Sold by the Federal Reserve in "
                          "the Temporary Open Market Operations"),
}
# 시리즈 쪽 JSON-LD의 license(2026-11-03 확인). 이 값 밖의 시리즈는 싣지 않는다
CITE_REQUIRED = ("SOFR", "RPONTTLD", "RRPONTSYD")
LICENCE = {sid: ("citation-required" if sid in CITE_REQUIRED else "public-domain") for sid in SOURCES}
SERIES = list(SOURCES)
RES_AVG = "WRESBAL"
BS = {"res": "WRBWFRBL", "tga": "WDTGAL", "onrrp": "WLRRAOL", "pool": "WLRRAFOIAL", "bills": "WSHOBL",
      "coupons": "WSHONBNL", "mbs": "WSHOMCB", "cur": "WCICL"}     # 수요일 수준, 백만 달러 — 순서가 문구의 순서다
SIGN = {"tga": -1, "onrrp": -1, "pool": -1, "bills": 1, "coupons": 1, "mbs": 1, "cur": -1}   # 지준 쪽 부호
PARTS = (*SIGN, "other")
PART_NAME = {"tga": "재무부 현금(TGA)", "onrrp": "익일물 역레포", "pool": "해외 공적 역레포", "bills": "연준 단기채",
             "coupons": "연준 이표채", "mbs": "연준 MBS", "cur": "현금 통화", "other": "그 밖"}
SIGN_NOTE = "(부호는 지준 쪽)"
WINDOWS = (("4", WIN4), ("13", WIN13))

# FOMC 결정일 표 — (첫날, 결정일, 잠정). 2025-12·2026년은 연준 FOMC 성명 일정(2026년은 site/people-data.js의 meetings_2026과
# 같다 — 테스트가 견준다). 2027년은 연준 FOMC 일정 페이지(federalreserve.gov/monetarypolicy/fomccalendars.htm, 'Last Update:
# October 28, 2026' — 2026-11-03 확인)의 여덟 회의다. 연준 고지('Each meeting date is tentative until confirmed at the meeting
# immediately preceding it')대로 잠정 표시를 붙인다. 2027년 회의 하나(가을부터, 어느 회의인지 미정)는 표결·성명 없는 전략
# 회의라고 의장이 밝혔다(기자회견 2026-10-28). 매년 1월 갱신 때 비공개 fed_people.json의 fomc와 같이 고친다(그쪽 짝 테스트가
# 이 표가 그 일정의 앞부분과 같은지 본다)
FOMC = (("2025-12-09", "2025-12-10", False),
        ("2026-01-27", "2026-01-28", False), ("2026-03-17", "2026-03-18", False), ("2026-04-28", "2026-04-29", False),
        ("2026-06-16", "2026-06-17", False), ("2026-07-28", "2026-07-29", False), ("2026-09-15", "2026-09-16", False),
        ("2026-10-27", "2026-10-28", False), ("2026-12-08", "2026-12-09", False),
        ("2027-01-26", "2027-01-27", True), ("2027-03-16", "2027-03-17", True), ("2027-04-27", "2027-04-28", True),
        ("2027-06-08", "2027-06-09", True), ("2027-07-27", "2027-07-28", True), ("2027-09-14", "2027-09-15", True),
        ("2027-10-26", "2027-10-27", True), ("2027-12-07", "2027-12-08", True))
DECISION_HOUR = 14                            # FOMC 성명 시각(미 동부) — 이보다 늦은 실행에서 그날 회의는 '다음'이 아니다

NOTICE = ("이 사이트의 규칙 점검에 쓰지 않는 참고 자료다. 연준 H.4.1 주간 대차대조표와 단기자금 시장의 공개 통계로 계산한 "
          "산술만 싣는다. 규칙 카드 '지준과 통화승수'의 지준/GDP와 지준·재정 카드의 13주 나눔을 주간으로 읽는 재료다. "
          "지준 관리 매입(RMP)은 뉴욕 연은 월 일정 공지의 계획 금액이고, 운영 결과로 셈한 대조(공식 수치 아님)는 차 한 줄로만 "
          "둔다. "
          "금리나 자금 여건을 예측하지 않는다.")
COMPUTED_NOTICE = ("지준/GDP·하한 대비 차·4주 평균·분모 바뀜·4주/13주 차·5영업일 최대·RMP 시작 뒤 네 주 평균의 차·하한의 "
                   "달러 크기는 macro-regime-check가 원자료로 계산한 값이다.")
SPREAD_DERIVED = ("SOFR − IORB 차와 그 5영업일 최대·0보다 큰 날 수는 macro-regime-check가 뉴욕 연은 SOFR 일별 자료와 연준 "
                  "이사회 IORB(FRED 경유)로 계산한 값이다. 뉴욕 연은이 발표한 값이 아니다.")
SPREAD_DERIVED_EN = ("The SOFR − IORB spread, its 5-business-day maximum and the count of positive days are computed by "
                     "macro-regime-check from SOFR (New York Fed) and IORB (Federal Reserve Board) data via FRED; they are "
                     "not published by the New York Fed.")
SRF_DERIVED = ("상시 레포 이용의 5영업일 최대는 macro-regime-check가 뉴욕 연은 임시 공개시장 운영 자료(FRED 경유)에서 고른 "
               "값이다. 뉴욕 연은이 발표한 값이 아니다.")
SRF_DERIVED_EN = ("The 5-business-day maximum of standing repo usage is selected by macro-regime-check from New York Fed "
                  "temporary open market operations data via FRED; it is not published by the New York Fed.")
WEEK_NOTICE = ("주의 15일·월말·FOMC 표시는 macro-regime-check가 H.4.1 주(목~수)의 날짜와 이 저장소에 적어 둔 연준 FOMC "
               "일정으로 붙인 것이다.")
REASONS = {
    "fetch": "수신 실패",
    "cache": "수신 실패 · 묵은 캐시는 싣지 않음",
    "format": "계산할 자료가 모자람",
    "older": "받은 자료가 직전 자료보다 오래됨",
    "table": "공식 페이지에서 계획 표를 찾지 못함",
}

# 지준 관리 매입(RMP) 칸 — 뉴욕 연은 국채 운영 결과(2026-11-03 이 샌드박스에서 응답 꼴 확인: {"treasury": {"auctions":
# [{operationId, auctionStatus 'Results', operationType 'Outright Bill Purchase'·'Outright Coupon Purchase'·'Outright FRN
# Purchase'·'Outright Coupon Sale' …, operationDate, settlementDate, operationDirection 'P'·'S', totalParAmtAccepted(문자열,
# 달러) …}]}})
OPS = "TSYOPS"                                # 이 파일 안의 이름(sources[].series) — 뉴욕 연은 시리즈 ID가 아니다
OPS_HOST = "markets.newyorkfed.org"
OPS_URL = f"https://{OPS_HOST}/api/tsy/all/results/summary/search.json"
OPS_TITLE = "Treasury Securities Operations, results summary"
OPS_LICENCE = "nyfed-terms"
OPS_CACHE = "tsy_ops.json"                    # <work>/fedbs/tsy_ops.json — 받은 원문
OPS_BUDGET = 25                               # 뉴욕 연은 요청 두 번(운영 결과 · 공식 계획 페이지)의 합(초) — FRED 수신(BUDGET)과
                                              # 따로. 합쳐도 단계 제한 2분 안
RMP_FROM = datetime.date(2025, 12, 12)        # RMP 시작 창의 첫 날 — 뉴욕 연은 운영 방침 2025-12-10(첫 일정 12-11 발표, 매입은
                                              # 12-12부터). 계획 페이지의 기간 가운데 이 날부터의 창만 쓴다
OPS_FROM = RMP_FROM.replace(day=1)            # 운영 결과 요청의 첫 날 — RMP 시작 달 1일(끝난 창을 모두 대조한다, 요청은 1번 그대로)
OPS_MAX = 2_000_000                           # 바이트 — 운영 결과 응답 상한(2026-11-03: 2025-11 ~ 68건이 약 32KB)
RMP_BDAY = 9                                  # 뉴욕 연은이 월 매입 금액을 발표하는 그 달 '9영업일께'(운영 방침 2025-12-10)
SMALL_MIN = 100_000_000                       # 달러 — 받아들인 금액이 이보다 작은 매입은 소액 시험 운영으로 뺀다
OP_MAX = 200_000_000_000                      # 달러 — 운영 하나가 이보다 크면 단위를 잘못 읽은 것으로 보고 닫힌 쪽으로
MBS_DAY = 25                                  # 그 달 MBS 상환 = 전달 상환 수요일 − 그 달 상환 수요일(WSHOMCB, paydown_wed)
MBS = "WSHOMCB"
GROUPS_MAX = 6                                # 묶음 표의 줄 상한 — 그 앞의 창은 누적에만 든다
RELEASE_AHEAD = 62                            # 페이지의 다음 공지 칸 날짜는 오늘부터 이 날 수 안일 때만 쓴다
WEEKS4 = 4                                    # RMP 시작 뒤 나눔 — 수요일 수준 네 주 평균
# RMP 시작 뒤 나눔의 시리즈(나눔 칸이 받는 것 가운데 일곱 — 이표채(WSHONBNL)는 '그 밖'에 들어 따로 쓰지 않는다)
BRIDGE = {"res": "WRBWFRBL", "tga": "WDTGAL", "onrrp": "WLRRAOL", "pool": "WLRRAFOIAL", "bills": "WSHOBL", "mbs": "WSHOMCB",
          "cur": "WCICL"}
BRIDGE_PARTS = ("bm", "tga", "cur", "rrp", "other")     # 문구의 차례
BRIDGE_NAME = {"bm": "연준 단기채+MBS", "tga": "재무부 현금(TGA)", "cur": "현금 통화", "rrp": "역레포", "other": "그 밖"}
RMP_NAME = "지준 관리 매입(RMP) — 뉴욕 연은 월 일정 계획"
TABLE_HEAD = ("창(시작 달)", "RMP 계획", "RMP 누적", "재투자 계획")
BRIDGE_TAG = "RMP 시작 뒤 지준"
FLOOR_TAG = "같은 기간 규칙 하한의 달러 크기"
RMP_MEAN = ("재투자는 MBS 상환분만큼 단기채를 되사는 보유 교체라 MBS 감소와 합하면 지준에 대략 0이고, 지준을 늘리는 몫은 "
            "RMP다.")
AMPLE = ("는 이 사이트 규칙 카드의 추정값이고 연준이 말하는 'ample'의 기준이 아니다(단기자금 여건은 아래 SOFR − IORB·상시 "
         "레포 칸).")
CHK_HEAD = "운영 결과 대조(이 사이트의 셈 — 창의 매입 합 − 그 달 MBS 상환)"
RMP_NOTICE = ("RMP 칸의 계획 금액은 macro-regime-check가 뉴욕 연은 'Treasury Securities Operational Details' 페이지의 월 일정 창 "
              "계획 문장에서 정해 둔 꼴만 옮긴 것이고 고치지 않았다. 누적·묶음·연속 창 수·운영 결과 대조는 그 금액과 뉴욕 연은 국채 "
              "운영 결과(Markets API)·연준 H.4.1 MBS 보유(WSHOMCB, FRED 경유)로 계산한 값이다. 뉴욕 연은이 발표한 값이 아니다.")
RMP_NOTICE_EN = ("Planned amounts in the RMP row are transcribed by macro-regime-check from the monthly-period sentences on the "
                 "New York Fed's Treasury Securities Operational Details page (fixed sentence forms only, unaltered); cumulative "
                 "totals, groupings, run counts and the cross-check gap are computed by macro-regime-check from those amounts, New "
                 "York Fed Treasury securities operation results (Markets API) and Federal Reserve H.4.1 MBS holdings (WSHOMCB) "
                 "via FRED; they are not published by the New York Fed.")
KO_WD = "월화수목금토일"
NATIVE = {2: "두", 3: "세", 4: "네", 5: "다섯", 6: "여섯", 7: "일곱", 8: "여덟", 9: "아홉", 10: "열"}

# 지준 관리 매입(RMP) 공식 계획 — 뉴욕 연은 'Treasury Securities Operational Details' 페이지(2026-11-03 이 샌드박스에서 이
# 프로젝트의 User-Agent로 HTTP 200, 정적 HTML 약 190KB — 표 id 'pagination-table', 머리 Period · Planned Operation Amount ·
# Tentative Schedule · Results · Next Schedule Release, 행마다 '10/15/2026 -<br>11/13/2026' · 'The Desk plans to conduct
# approximately $14.6 billion in reinvestment purchases and no reserve management purchases over the noted monthly period.' …
# 다음 공지 칸은 2026-11-03 모든 행이 &nbsp;)
PLAN = "TSYPLAN"                              # 이 파일 안의 이름(sources[].series) — 뉴욕 연은 시리즈 ID가 아니다
PLAN_HOST = "www.newyorkfed.org"
PLAN_URL = (f"https://{PLAN_HOST}/markets/domestic-market-operations/monetary-policy-implementation/treasury-securities/"
            "treasury-securities-operational-details")
PLAN_TITLE = "Treasury Securities Operational Details"
PLAN_CACHE = "tsy_plan.html"                  # <work>/fedbs/tsy_plan.html — 받은 원문(공개 data에는 싣지 않는다)
PLAN_MAX = 2_000_000                          # 바이트 — 이보다 큰 응답은 받지 않는다
PLAN_SPAN_MAX = 62                            # 기간 하나의 길이 상한(일) — 넘으면 그 행의 기간을 읽지 못한 것으로
PLAN_ROWS_MAX = 1000                          # 표의 기간 수 상한(꼴 검사)
_AMT = r"(\d{1,4}(?:\.\d{1,2})?)"
# 정해 둔 계획 문장 꼴 — 이 꼴이 아니면 '꼴 모름'(숫자를 짓지 않는다). 2026-11-03 페이지의 2025-12 ~ 2026-10 열한 창이 이 꼴
PLAN_FORM = re.compile(r"The Desk plans to (?:conduct|purchase) approximately \$" + _AMT + r" billion in reinvestment purchases "
                       r"and (?:(no) reserve management purchases|(?:an additional )?approximately \$" + _AMT +
                       r" billion in reserve management purchases) over the noted monthly period\.")
_MDY = r"(\d{1,2})/(\d{1,2})/(\d{4})"
PLAN_PERIOD = re.compile(_MDY + r"(?:\s*[-\u2013\u2014]\s*" + _MDY + r")?")
_MONTHS_EN = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
              "December")
# 다음 공지 칸의 날짜 꼴 — 'M/D/YYYY' 또는 'November 13, 2026'(요일이 앞에 붙어도 — 'Friday, November 13, 2026'). 그 밖은 비어 있는 것으로
PLAN_RELEASE = re.compile(r"(?:[A-Z][a-z]+, )?(?:" + _MDY + r"|(" + "|".join(_MONTHS_EN) + r") (\d{1,2}), (\d{4}))")


class ItemError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


D = datetime.date
TD = datetime.timedelta
_r = ai._r
_iso = ai._iso


def _r6(v):
    return None if v is None else round(v, 6) + 0.0


def _day(s):
    return D.fromisoformat(s)


# ---------- 날짜 표시 ----------

def level_tag(d):
    """수요일 수준 날짜(창의 출발·끝)가 그 달 마지막 날(분기 끝 달이면 '분기말', 아니면 '월말')이거나 15일이면 그 표시 — 아니면 ''."""
    if (d + TD(days=1)).month != d.month:
        return "분기말" if d.month % 3 == 0 else "월말"
    return "15일" if d.day == 15 else ""


def cal_tag(d, dates):
    """일간 관측 날짜의 표시 — 월말(그 달의 마지막 관측: 다음 관측이 다음 달이거나, 마지막 관측이면 그 뒤 사흘 안에 그 달
    평일이 없음) · 15일(15일, 또는 15일이 주말이라 밀린 16·17일의 첫 관측) — 아니면 ''."""
    i = dates.index(d)
    nxt = dates[i + 1] if i + 1 < len(dates) else None
    if nxt is not None:
        end = nxt.month != d.month
    else:
        end = all((d + TD(days=k)).month != d.month or (d + TD(days=k)).weekday() >= 5 for k in range(1, 4))
    if end:
        return "월말"
    prev = dates[i - 1] if i else None
    if d.day == 15 or (d.day in (16, 17) and prev is not None and prev.month == d.month and prev.day < 15):
        return "15일"
    return ""


def meetings():
    """FOMC 표 → [(첫날, 결정일, 잠정)] 날짜 차례."""
    return sorted((_day(a), _day(b), t) for a, b, t in FOMC)


def _nth_sunday(y, m, n):
    first = D(y, m, 1)
    return first + TD(days=(6 - first.weekday()) % 7 + 7 * (n - 1))


def decided_at(b):
    """결정일 b의 성명 시각(DECISION_HOUR시 미 동부)을 UTC로 — 서머타임(2007년 규칙: 3월 둘째 일요일 ~ 11월 첫 일요일)이면
    UTC−4, 아니면 UTC−5. 결정일은 수요일이라 전환 날(일요일)에 걸리지 않는다. 시간대 자료(tzdata)에 기대지 않는다."""
    off = 4 if _nth_sunday(b.year, 3, 2) <= b < _nth_sunday(b.year, 11, 1) else 5
    return datetime.datetime(b.year, b.month, b.day, DECISION_HOUR + off, tzinfo=datetime.timezone.utc)


# ---------- 산술 ----------

def calc_reserves(S, today):
    """지준(주 평균)·지준/GDP(규칙 카드와 같은 식)·하한 대비·4주 평균과 그래프(최근 52주 지준 · 하한 × 마지막 분기 GDP).
    분모 바뀜 칸은 비워 두고 build가 직전 파일과 견줘 채운다(with_base)."""
    value, wd, gd, g = liq.reserves_gdp(S)
    low = float(rr.TH["reserves_gdp_low"])
    w = S[RES_AVG]
    last4 = w[-4:]
    avg4 = (sum(v for _, v in last4) / 4 / 1000 / g * 100
            if len(last4) == 4 and (last4[-1][0] - last4[0][0]).days == 21 else None)
    floor = low / 100 * g
    pts = w[-CHART_WEEKS:]
    return {"date": _iso(wd),
            "values": {"level": _r(w[-1][1] / 1000), "value": _r6(value), "gdp_quarter": _iso(gd), "gdp_bn": _r(g),
                       "low": low, "gap_pp": _r(value - low), "gap_bn": _r((value - low) / 100 * g),
                       "avg4": _r6(avg4), "avg4_from": _iso(last4[0][0]) if avg4 is not None else None,
                       "base_quarter": None, "base_bn": None, "denom_pp": None,
                       "first_quarter": _iso(gd), "first_bn": _r(g)},
            "lines": {"res": [[_iso(d), round(v / 1000, 1)] for d, v in pts],
                      "low": [[_iso(d), round(floor, 1)] for d, _ in pts]}}


def with_base(core, old):
    """분모 바뀜 — 기준은 직전 주를 처음 실을 때의 GDP(비공개 fed_bs가 메일로 실은 주의 GDP와 견주는 것과 같은 뜻).
    직전 파일의 칸(old core)이 이번보다 이른 주면 그 주의 first(처음 실을 때의 GDP)를, 같은 주면 그 주가 견준 기준과 first를
    그대로 둔다. 기준과 이번 GDP(분기·크기)가 다르면 같은 지준으로 견준 분모 몫 = 지준 ÷ 이번 GDP − 지준 ÷ 기준 GDP(%p).
    first는 이번 주를 처음 실을 때의 GDP다 — 같은 주 안에서 GDP만 바뀌어도(H.4.1이 하루 늦은 주의 GDP 발표 등) 다음 주가 그
    바뀜을 분모 바뀜으로 싣는다."""
    v = dict(core["values"], base_quarter=None, base_bn=None, denom_pp=None,
             first_quarter=core["values"]["gdp_quarter"], first_bn=core["values"]["gdp_bn"])
    base = None
    if old:
        ov = old["values"]
        if core["date"] > old["date"]:
            base = (ov["first_quarter"], ov["first_bn"])
        elif core["date"] == old["date"]:
            v["first_quarter"], v["first_bn"] = ov["first_quarter"], ov["first_bn"]
            if ov.get("base_quarter") and ov.get("base_bn"):
                base = (ov["base_quarter"], ov["base_bn"])
    if base and base[1]:
        v["base_quarter"], v["base_bn"] = base
        if base != (v["gdp_quarter"], v["gdp_bn"]):
            v["denom_pp"] = _r6(v["level"] / v["gdp_bn"] * 100 - v["level"] / base[1] * 100)
    return {**core, "values": v}


def decompose(S, days):
    """여덟 수요일 수준 시리즈가 모두 있는 마지막 수요일과 그 days일 전 이하 마지막 공통 관측(NEAR_DAYS 안) → (출발, 끝,
    {지준: 변화, 몫: 지준 쪽 부호의 변화}) 또는 None. 십억 달러. 그 밖 = 지준 변화 − 나머지 합."""
    common = sorted(set.intersection(*(set(d for d, _ in S[sid]) for sid in BS.values())))
    if not common:
        return None
    d1 = common[-1]
    old = [d for d in common if d <= d1 - TD(days=days)]
    if not old or (d1 - TD(days=days) - old[-1]).days > NEAR_DAYS:
        return None
    d0 = old[-1]
    v = {k: dict(S[sid]) for k, sid in BS.items()}
    ch = {k: (v[k][d1] - v[k][d0]) / 1000 for k in BS}
    parts = {k: SIGN[k] * ch[k] for k in SIGN}
    parts["other"] = ch["res"] - sum(parts.values())
    return d0, d1, {"res": ch["res"], **parts}


def calc_dec(S, today):
    common = sorted(set.intersection(*(set(d for d, _ in S[sid]) for sid in BS.values())))
    if not common:
        raise ItemError("format")
    vals = {"to": _iso(common[-1])}
    any_ok = False
    for w, days in WINDOWS:
        r = decompose(S, days)
        vals[f"from{w}"] = _iso(r[0]) if r else None
        for k in ("res", *PARTS):
            vals[f"{k}{w}"] = _r(r[2][k]) if r else None
        any_ok = any_ok or r is not None
    if not any_ok:
        raise ItemError("format")
    return {"date": vals["to"], "values": vals, "lines": {}}


def _max_with_date(rows):
    d, v = max(rows, key=lambda x: x[1])             # 같은 값이면 이른 날(첫 최대)
    return v, d


def calc_spread(S, today):
    sofr, iorb = S["SOFR"], S["IORB"]
    win = sofr[-MM_DAYS:]
    rows = []
    for d, v in win:
        b = None
        for x in reversed(iorb):                     # 그 날 이하 마지막 IORB
            if x[0] <= d:
                b = x
                break
        if b and (d - b[0]).days <= IORB_GAP:
            rows.append((d, round((v - b[1]) * 100, 6)))
    if not rows:
        raise ItemError("format")
    mx, md = _max_with_date(rows)
    dates = [d for d, _ in sofr]
    return {"date": _iso(win[-1][0]),
            "values": {"from": _iso(win[0][0]), "max_bp": mx + 0.0, "max_date": _iso(md), "max_tag": cal_tag(md, dates),
                       "pos": sum(1 for _, x in rows if x > 0), "n": len(rows), "days": len(win)},
            "lines": {}}


def calc_srf(S, today):
    srf = S["RPONTTLD"]
    win = srf[-MM_DAYS:]
    mx, md = _max_with_date(win)
    return {"date": _iso(win[-1][0]),
            "values": {"from": _iso(win[0][0]), "max_bn": _r(mx), "max_date": _iso(md),
                       "max_tag": cal_tag(md, [d for d, _ in srf])},
            "lines": {}}


def calc_rrp(S, today):
    rrp = S["RRPONTSYD"]
    d, v = rrp[-1]
    return {"date": _iso(d), "values": {"bn": _r(v), "tag": cal_tag(d, [x for x, _ in rrp])}, "lines": {}}


def next_fomc(today, now=None):
    """다음 FOMC — now(실행 시각, UTC)에 아직 성명(decided_at)이 나오지 않은 첫 회의 → (결정일, 잠정) 또는 None. now가 없으면
    today 0시(UTC)로 본다(그날 회의는 '다음'). 주 칸과 RMP 칸의 다음 날짜가 같이 쓴다."""
    if now is None:
        now = datetime.datetime.combine(today, datetime.time(0), tzinfo=datetime.timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)
    return next(((b, t) for _, b, t in meetings() if decided_at(b) > now), None)


def calc_week(S, today, now=None):
    """그 H.4.1 주(목~수 — 주 평균 지준의 마지막 수요일)가 15일·월말·FOMC 결정일을 품는지와 다음 FOMC 결정일 — now(실행 시각,
    UTC)에 아직 성명(decided_at)이 나오지 않은 첫 회의. now가 없으면 today 0시(UTC)로 본다(그날 회의는 '다음')."""
    wed = S[RES_AVG][-1][0]
    start = wed - TD(days=6)
    days = [start + TD(days=i) for i in range(7)]
    ms = meetings()
    nxt = next_fomc(today, now)
    return {"date": _iso(wed),
            "values": {"from": _iso(start), "d15": any(d.day == 15 for d in days),
                       "month_end": any((d + TD(days=1)).month != d.month for d in days),
                       "fomc": [_iso(b) for _, b, _ in ms if start <= b <= wed],
                       "next_fomc": _iso(nxt[0]) if nxt else None, "next_tentative": bool(nxt and nxt[1])},
            "lines": {}}


# ---------- 지준 관리 매입(RMP) — 영업일·상환 수요일·운영 결과 ----------

def _nth_weekday(y, m, wd, n):
    """y년 m월의 n번째 wd요일(월=0). n = -1이면 마지막."""
    if n < 0:
        last = D(y + (m == 12), m % 12 + 1, 1) - TD(days=1)
        return last - TD(days=(last.weekday() - wd) % 7)
    first = D(y, m, 1)
    return first + TD(days=(wd - first.weekday()) % 7 + 7 * (n - 1))


def fed_holidays(y):
    """y년의 연방 공휴일 가운데 연준이 쉬는 날 — 날짜가 정해진 다섯(새해·준틴스(2021~)·독립기념일·재향군인·성탄)은 일요일이면
    월요일에 쉬고 토요일이면 대체 없이 연다(연준은 그 앞 금요일에 연다), 요일로 정해진 여섯(MLK 1월 셋째 월 · 대통령의 날 2월
    셋째 월 · 메모리얼 5월 마지막 월 · 노동절 9월 첫 월 · 콜럼버스 10월 둘째 월 · 추수감사절 11월 넷째 목)."""
    fixed = [D(y, 1, 1), D(y, 7, 4), D(y, 11, 11), D(y, 12, 25)] + ([D(y, 6, 19)] if y >= 2021 else [])
    out = set()
    for d in fixed:
        if d.weekday() == 6:
            out.add(d + TD(days=1))
        elif d.weekday() < 5:
            out.add(d)
    out |= {_nth_weekday(y, 1, 0, 3), _nth_weekday(y, 2, 0, 3), _nth_weekday(y, 5, 0, -1), _nth_weekday(y, 9, 0, 1),
            _nth_weekday(y, 10, 0, 2), _nth_weekday(y, 11, 3, 4)}
    return out


def bday_n(y, m, n=RMP_BDAY):
    """y년 m월의 n번째 영업일(평일 − fed_holidays)."""
    hol, d, k = fed_holidays(y), D(y, m, 1), 0
    while True:
        if d.weekday() < 5 and d not in hol:
            k += 1
            if k == n:
                return d
        d += TD(days=1)


def _shift(ym, k):
    y, m = ym
    i = y * 12 + (m - 1) + k
    return i // 12, i % 12 + 1


def first_wed(d):
    """d 이후(d가 수요일이면 d) 첫 수요일."""
    return d + TD(days=(2 - d.weekday()) % 7)


def paydown_wed(y, m):
    """y년 m월의 MBS 상환 수요일 — 그 달 MBS_DAY(25일)부터 첫 영업일(평일 − fed_holidays) 이후 첫 수요일(그날이 수요일이면
    그날). 패니메이·프레디맥 상환은 25일이 주말·연방 공휴일이면 다음 영업일에 결제된다. 25일 이후 첫 수요일과 다른 것은 성탄
    (12-25)이 수요일인 해(2024·2030·2041)의 12월뿐이다 — 그날 수요일 수준엔 지니메이 몫만 들어 다음 수요일로 간다."""
    hol, d = fed_holidays(y), D(y, m, MBS_DAY)
    while d.weekday() >= 5 or d in hol:
        d += TD(days=1)
    return first_wed(d)


def ops_range(today):
    """요청 범위 — RMP 시작 달 1일(OPS_FROM) ~ 오늘. 끝난 창을 모두 대조한다(요청은 1번 — 응답은 OPS_MAX바이트 상한)."""
    return OPS_FROM, today


def _usd(v):
    """받아들인 금액(달러) — 숫자 글자(쉼표 허용)나 정수. 0 ~ OP_MAX 밖이거나 읽지 못하면 None."""
    if type(v) is int:
        x = float(v)
    elif isinstance(v, str) and re.fullmatch(r"\d{1,15}(\.\d{1,6})?", v.strip().replace(",", "")):
        x = float(v.strip().replace(",", ""))
    else:
        return None
    return x if 0 <= x <= OP_MAX else None


def parse_ops(blob):
    """뉴욕 연은 국채 운영 결과 원문 → [(운영일, 방향 'P'|'S', 받아들인 금액 달러)] 날짜 차례. 결과(auctionStatus 'Results')가
    나온 운영만 보고, 같은 operationId는 하나. 꼴이 다르거나 결과 운영의 날짜·방향·금액을 읽지 못하면 닫힌 쪽으로(format).
    OPS_MAX바이트보다 크면 받지 않은 것으로(fetch)."""
    if isinstance(blob, (bytes, str)) and len(blob) > OPS_MAX:
        raise ItemError("fetch")                 # 상한보다 큰 응답은 받지 않은 것으로
    try:
        js = json.loads(blob.decode("utf-8") if isinstance(blob, bytes) else blob)
        rows = js["treasury"]["auctions"]
    except (ValueError, UnicodeDecodeError, KeyError, TypeError, AttributeError):
        raise ItemError("format")
    if not isinstance(rows, list):
        raise ItemError("format")
    seen = {}
    for r in rows:
        if not isinstance(r, dict):
            raise ItemError("format")
        if r.get("auctionStatus") != "Results":
            continue
        day, way, amt = r.get("operationDate"), r.get("operationDirection"), _usd(r.get("totalParAmtAccepted"))
        if not ai._is_day(day) or way not in ("P", "S") or amt is None:
            raise ItemError("format")
        oid = r.get("operationId")
        key = oid if isinstance(oid, str) and oid.strip() else (day, way, amt, str(r.get("operationType")))
        seen[key] = (_day(day), way, amt)
    return sorted(seen.values())


def _t1(v):
    """보이는 소수 한 자리(f'{v:.1f}' 그대로)의 값 — 보이는 숫자끼리 뺄셈이 맞게."""
    return None if v is None else float(f"{v:.1f}") + 0.0


def rule_bounds(ym):
    """9영업일 규칙의 M월 창 — (첫 운영일 후보 = M월 9영업일 다음 날, 끝 = M+1월 9영업일, 'rule')."""
    return bday_n(*ym) + TD(days=1), bday_n(*_shift(ym, 1)), "rule"


def bday_gap(a, b):
    """a와 b 사이(양 끝 빼고)에 영업일(평일 − fed_holidays)이 하나라도 있으면 True — 이웃 창 사이가 빈 것."""
    d = a + TD(days=1)
    while d < b:
        if d.weekday() < 5 and d not in fed_holidays(d.year):
            return True
        d += TD(days=1)
    return False


def plan_bounds(months, plan):
    """운영 결과 대조의 창 경계 — 달마다 공식 계획에 그 달에 시작하는 기간이 하나 있으면 그 기간(시작~끝, 양 끝 포함, 'plan'), 없으면
    9영업일 규칙. 이웃 창이 겹치거나(끝 ≥ 다음 시작) 사이가 비면(끝과 다음 시작 사이에 영업일이 있음 — 반 달씩 나눈 행 같은 꼴,
    빈 날의 운영이 어느 창에도 들지 않는다) 모든 창을 규칙으로. 마지막 창은 그다음 달의 창(같은 규칙으로 고른 것)과도 사이가
    비는지 본다 — 지금 창이 반 달짜리 행에서 끝나 오늘까지의 운영이 빠지지 않게. plan이 없으면(받지 못함) 규칙."""
    rule = [rule_bounds(ym) for ym in months]
    if not plan:
        return rule
    out = []
    for ym in [*months, _shift(months[-1], 1)]:
        c = [p for p in plan["periods"] if (p[0].year, p[0].month) == ym]
        out.append((c[0][0], c[0][1], "plan") if len(c) == 1 else rule_bounds(ym))
    shown = out[:-1]
    if any(a[1] >= b[0] or bday_gap(a[1], b[0]) for a, b in zip(shown, shown[1:])) or bday_gap(shown[-1][1], out[-1][0]):
        return rule
    return shown


def rmp_window(ym, ops, mbs, today, bounds=None):
    """한 달의 월 일정 창 — 매입(운영 수·합·운영일)·뺀 소액 시험 운영 수·셈하지 않은 매각 수, 끝난 창이면 그 달 MBS 상환과
    RMP 대조값(보이는 소수 한 자리끼리). 끝나지 않은 창은 상환·대조를 비운다. bounds = (시작, 끝, 'plan'|'rule') — 없으면 규칙."""
    start, until, how = bounds or rule_bounds(ym)
    ended = today > until
    inside = [o for o in ops if start <= o[0] <= until]
    buys = [o for o in inside if o[1] == "P" and o[2] >= SMALL_MIN]
    bn = _r(sum(o[2] for o in buys) / 1e9)
    red_from, red_to = paydown_wed(*_shift(ym, -1)), paydown_wed(*ym)
    red = None
    if ended and red_from in mbs and red_to in mbs:
        red = _r((mbs[red_from] - mbs[red_to]) / 1000)
    return {"month": f"{ym[0]:04d}-{ym[1]:02d}", "from": _iso(start), "until": _iso(until), "bound": how, "ended": ended,
            "n": len(buys), "bn": bn, "ops": [_iso(o[0]) for o in buys],
            "small": sum(1 for o in inside if o[1] == "P" and o[2] < SMALL_MIN),
            "sales": sum(1 for o in inside if o[1] == "S"),
            "red_from": _iso(red_from), "red_to": _iso(red_to), "red_bn": red,
            "rmp_bn": None if red is None else _t1(_t1(bn) - _t1(red))}


# ---------- 지준 관리 매입(RMP) 공식 계획 ----------

class _Tables(html.parser.HTMLParser):
    """HTML의 표마다 행마다 칸의 글 — 태그를 벗기고(<br>은 한 칸), 문자 참조(&nbsp; 등)를 풀고, 공백·줄바꿈을 한 칸으로.
    닫는 태그가 빠진 칸·행은 다음 칸·행·표 끝에서 닫는다. 표 안의 표는 따로 센다. script·style 안의 글은 보지 않는다."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self._st = [], []           # _st: 열린 표마다 {"rows", "row", "cell"}

    def _close_cell(self, t):
        if t["cell"] is not None and t["row"] is not None:
            t["row"].append(" ".join("".join(t["cell"]).split()))
        t["cell"] = None

    def _close_row(self, t):
        self._close_cell(t)
        if t["row"] is not None:
            t["rows"].append(t["row"])
        t["row"] = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._st.append({"rows": [], "row": None, "cell": None})
        elif not self._st:
            return
        elif tag == "tr":
            self._close_row(self._st[-1])
            self._st[-1]["row"] = []
        elif tag in ("td", "th"):
            t = self._st[-1]
            self._close_cell(t)
            if t["row"] is None:
                t["row"] = []
            t["cell"] = []
        elif tag == "br" and self._st[-1]["cell"] is not None:
            self._st[-1]["cell"].append(" ")

    def handle_endtag(self, tag):
        if not self._st:
            return
        t = self._st[-1]
        if tag in ("td", "th"):
            self._close_cell(t)
        elif tag == "tr":
            self._close_row(t)
        elif tag == "table":
            self._close_row(t)
            self.tables.append(self._st.pop()["rows"])

    def handle_data(self, data):
        if self._st and self._st[-1]["cell"] is not None:
            self._st[-1]["cell"].append(data)

    def close(self):
        super().close()
        while self._st:                          # 닫히지 않은 표도 센다
            t = self._st.pop()
            self._close_row(t)
            self.tables.append(t["rows"])


def _plan_table(text):
    """머리가 Period · Planned Operation Amount인 첫 표의 행(머리 뒤) — 없으면 None."""
    p = _Tables()
    try:
        p.feed(text)
        p.close()
    except Exception:                            # html.parser가 깨진 꼴에 뜻밖의 오류를 내도 표 없음으로
        return None
    for rows in p.tables:
        if rows and len(rows[0]) >= 2 and rows[0][0].lower() == "period" \
                and rows[0][1].lower().startswith("planned operation amount"):
            return rows[1:]
    return None


def _period(text):
    """기간 칸 → (시작, 끝) 또는 None — 'M/D/YYYY - M/D/YYYY'(날짜 하나면 그 하루), 없는 날·끝 < 시작·PLAN_SPAN_MAX일 넘음은 None."""
    m = PLAN_PERIOD.fullmatch(text)
    if not m:
        return None
    g = m.groups()
    try:
        a = D(int(g[2]), int(g[0]), int(g[1]))
        b = D(int(g[5]), int(g[3]), int(g[4])) if g[3] else a
    except ValueError:
        return None
    if b < a or (b - a).days > PLAN_SPAN_MAX:
        return None
    return a, b


def _plan_sentence(text):
    """계획 문장 → (재투자 글, RMP 글) 또는 (None, None)(형식 모름). 'no reserve management purchases'는 RMP '0'."""
    m = PLAN_FORM.fullmatch(text)
    if not m:
        return None, None
    reinvest, no, rmp = m.groups()
    return reinvest, ("0" if no else rmp)


def _release_day(text):
    """다음 공지(Next Schedule Release) 칸 → 날짜 또는 None(비었거나 정해 둔 꼴이 아님 — 'M/D/YYYY'·'November 13, 2026')."""
    m = PLAN_RELEASE.fullmatch(text or "")
    if not m:
        return None
    g = m.groups()
    try:
        if g[0]:
            return D(int(g[2]), int(g[0]), int(g[1]))
        return D(int(g[5]), _MONTHS_EN.index(g[3]) + 1, int(g[4]))
    except ValueError:
        return None


def parse_plan(blob):
    """공식 계획 페이지 원문 → {"periods": [(시작, 끝, 재투자 글|None, RMP 글|None)] 시작 차례, "dropped": 기간을 읽지 못한 행 수,
    "release": 시작이 가장 늦은 기간 행의 다음 공지 칸 날짜 또는 None}. 재투자·RMP가 None이면 꼴 모름. 같은 기간이 여러 번이면
    하나로 — 읽은 숫자가 다르면 꼴 모름. PLAN_MAX바이트보다 크면 받지 않은 것으로(fetch), 표가 없으면 table, 기간이 하나도 없으면
    format."""
    if isinstance(blob, bytes):
        if len(blob) > PLAN_MAX:
            raise ItemError("fetch")
        text = blob.decode("utf-8", errors="replace")
    elif isinstance(blob, str):
        if len(blob.encode("utf-8", errors="replace")) > PLAN_MAX:
            raise ItemError("fetch")
        text = blob
    else:
        raise ItemError("format")
    rows = _plan_table(text)
    if rows is None:
        raise ItemError("table")
    seen, nxt, dropped = {}, {}, 0
    for r in rows:
        per = _period(r[0]) if len(r) >= 2 else None
        if per is None:
            dropped += 1
            continue
        got = _plan_sentence(r[1])
        if per in seen and seen[per] != got:
            got = (None, None)                   # 같은 기간에 다른 숫자 — 어느 쪽인지 고르지 않는다
        seen[per] = got
        day = _release_day(r[4]) if len(r) >= 5 else None
        if per not in nxt or nxt[per] is None:
            nxt[per] = day
    if not seen or len(seen) > PLAN_ROWS_MAX:
        raise ItemError("format")
    last = max(seen)
    return {"periods": sorted((a, b, *v) for (a, b), v in seen.items()), "dropped": dropped, "release": nxt.get(last)}


def plan_window(ym, periods):
    """한 달의 공식 계획 — 시작일이 그 달이고 RMP_FROM 이상인 기간 하나: form 'ok'(숫자를 읽음)·'unknown'(꼴 모름 — 기간이 여럿이면
    날짜도 비운다)·'missing'(페이지에 없음)."""
    c = [p for p in periods if (p[0].year, p[0].month) == ym and p[0] >= RMP_FROM]
    w = {"month": _mstr(ym), "from": None, "until": None, "form": "missing", "reinvest": None, "rmp": None}
    if len(c) > 1:
        w["form"] = "unknown"
    elif c:
        a, b, reinvest, rmp = c[0]
        w.update({"from": _iso(a), "until": _iso(b), "form": "ok" if reinvest is not None else "unknown",
                  "reinvest": reinvest, "rmp": rmp})
    return w


def _mstr(ym):
    return f"{ym[0]:04d}-{ym[1]:02d}"


def _ym(d):
    return d.year, d.month


def rmp_months(plan):
    """RMP 시작 달부터 페이지의 마지막 시작 달(RMP_FROM 이상인 기간 가운데)까지 — 차례대로. 그런 기간이 없으면 []."""
    starts = [p[0] for p in plan["periods"] if p[0] >= RMP_FROM]
    if not starts:
        return []
    last, ym, out = _ym(max(starts)), _ym(RMP_FROM), []
    while ym <= last:
        out.append(ym)
        ym = _shift(ym, 1)
    return out


def window_state(w, today):
    """마지막 창이 오늘에 대해 — 'now'(그 기간 안) · 'next'(아직 시작 전) · 'between'(끝남 — 다음 창 계획은 페이지에 아직 없음) ·
    'unknown'(그 달 기간이 여럿이라 날짜가 없음)."""
    if w["from"] is None:
        return "unknown"
    if today < _day(w["from"]):
        return "next"
    return "now" if today <= _day(w["until"]) else "between"


def next_dates(last_ym, release, today, now=None):
    """다음 날짜 — 마지막 시작 달의 다음 달부터 계획 공지 둘(오늘 이후인 것 — 첫 달은 페이지의 다음 공지 칸 날짜가 오늘부터
    RELEASE_AHEAD일 안이면 그 날 'official', 아니면 그 달 RMP_BDAY영업일)과 다음 FOMC(next_fomc), 날짜 차례."""
    out, ym = [], _shift(last_ym, 1)
    for k in range(4):
        if sum(1 for x in out if x["kind"] == "plan") == 2:
            break
        day, official = bday_n(*ym), False
        if k == 0 and release is not None and today <= release <= today + TD(days=RELEASE_AHEAD):
            day, official = release, True
        if day >= today:
            out.append({"kind": "plan", "month": _mstr(ym), "date": _iso(day), "official": official})
        ym = _shift(ym, 1)
    f = next_fomc(today, now)
    if f:
        out.append({"kind": "fomc", "date": _iso(f[0]), "tentative": bool(f[1])})
    return sorted(out, key=lambda x: (x["date"], x["kind"]))


def bridge(S):
    """RMP 시작 뒤 지준 나눔 → (값, None) 또는 (None, 사유 코드 또는 못 받은 시리즈 ID). 기준 = BRIDGE 일곱 시리즈가 모두 있는
    수요일 가운데 RMP_FROM 앞의 마지막 네 날, 끝 = 마지막 네 날 — 둘 다 이어진 네 주(첫 날과 마지막 날이 21일 차)일 때만.
    네 주 평균의 차(십억 달러), 지준 쪽 부호: bm = 단기채 + MBS · tga = −TGA · cur = −현금 통화 · rrp = −(익일물 + 해외 공적
    역레포) · other = 지준 − 나머지 합(이표채·TIPS·대출·기타 부채 등)."""
    miss = [sid for sid in BRIDGE.values() if not S.get(sid)]
    if miss:
        return None, miss[0]
    common = sorted(set.intersection(*(set(d for d, _ in S[sid]) for sid in BRIDGE.values())))
    base = [d for d in common if d < RMP_FROM][-WEEKS4:]
    end = common[-WEEKS4:]
    run = lambda ds: len(ds) == WEEKS4 and (ds[-1] - ds[0]).days == 7 * (WEEKS4 - 1)
    if not (run(base) and run(end)) or end[0] <= base[-1]:
        return None, "format"
    v = {k: dict(S[sid]) for k, sid in BRIDGE.items()}
    ch = {k: (sum(v[k][d] for d in end) - sum(v[k][d] for d in base)) / WEEKS4 / 1000 for k in BRIDGE}
    parts = {"bm": ch["bills"] + ch["mbs"], "tga": -ch["tga"], "cur": -ch["cur"], "rrp": -(ch["onrrp"] + ch["pool"])}
    parts["other"] = ch["res"] - sum(parts.values())
    return {"b0": _iso(base[0]), "b1": _iso(base[-1]), "e0": _iso(end[0]), "e1": _iso(end[-1]), "res": _r(ch["res"]),
            **{k: _r(x) for k, x in parts.items()}}, None


def _quarter(d):
    return D(d.year, (d.month - 1) // 3 * 3 + 1, 1)


def floor_size(S):
    """규칙 하한의 달러 크기 → (값, None) 또는 (None, 사유) — 하한 × RMP_FROM이 든 분기의 GDP와 × 마지막 분기 GDP(지준 칸과
    같은 분기, 현재 개정치)."""
    g = S.get("GDP")
    if not g:
        return None, "GDP"
    gd = dict(g)
    q0, (q1, g1) = _quarter(RMP_FROM), g[-1]
    if not gd.get(q0) or not g1 or q1 < q0:
        return None, "format"
    return {"low": float(rr.TH["reserves_gdp_low"]), "q0": _iso(q0), "g0": _r(gd[q0]), "q1": _iso(q1), "g1": _r(g1)}, None


def calc_view(S, today, plan, ops=None, errors=None, now=None):
    """지준 관리 매입(RMP) 칸 — RMP 시작 달부터의 창(공식 계획), 끝난 창의 운영 결과 대조(ops가 목록일 때 — 아니면 그 사유),
    마지막 창의 상태, 다음 날짜, RMP 시작 뒤 지준 나눔, 하한의 달러 크기. 칸 날짜 = 실은 창 가운데 마지막 시작일. RMP 창이
    없거나 날짜가 하나도 없으면 format."""
    errors = errors or {}
    why = lambda code: code if code in REASONS else errors.get(code, "fetch")
    months = rmp_months(plan)
    if not months or len(months) > PLAN_ROWS_MAX:
        raise ItemError("format")
    wins = [plan_window(ym, plan["periods"]) for ym in months]
    starts = [w["from"] for w in wins if w["from"]]
    if not starts:
        raise ItemError("format")
    checks, chk_why = None, None
    if isinstance(ops, list):
        got = [o for o in ops if o[0] <= today]
        if got:
            mbs = dict(S.get(MBS) or [])
            checks = [rmp_window(ym, got, mbs, today, b) for ym, b in zip(months, plan_bounds(months, plan))]
            if not any(c["rmp_bn"] is not None for c in checks):
                chk_why = errors.get(MBS, "format") if not mbs else "format"
        else:
            chk_why = "format"
    else:
        chk_why = ops.code if isinstance(ops, ItemError) else "format"
    br, br_why = bridge(S)
    fl, fl_why = floor_size(S)
    full = all(S.get(sid) for sid in BS.values())             # 나눔 칸과 같은 창의 연준 단기채(뜻 덧줄의 괄호) — 다 받았을 때만
    b4 = decompose(S, WIN4) if full else None
    b13 = decompose(S, WIN13) if full else None
    return {"date": max(starts),
            "values": {"rows": len(plan["periods"]), "dropped": plan["dropped"], "windows": wins,
                       "state": window_state(wins[-1], today),
                       "next": next_dates(months[-1], plan.get("release"), today, now),
                       "checks": checks, "chk_why": chk_why,
                       "bills4": _r(b4[2]["bills"]) if b4 else None, "bills13": _r(b13[2]["bills"]) if b13 else None,
                       "bridge": br, "bridge_why": None if br else why(br_why),
                       "floor": fl, "floor_why": None if fl else why(fl_why)},
            "lines": {}}


# ---------- 칸 정의 (차례 = 화면 차례) ----------

def _l(key, label, role, series):
    return {"key": key, "label": label, "role": role, "series": series}


def _dec_values():
    out = {"to": "day"}
    for w, _ in WINDOWS:
        out[f"from{w}"] = "day?"
        out.update({f"{k}{w}": "num?" for k in ("res", *PARTS)})
    return out


def _dec_ok(v):
    """창마다 출발 날짜가 있으면 숫자가 모두 있고, 없으면 모두 비었다. 적어도 한 창은 있다."""
    seen = False
    for w, _ in WINDOWS:
        nums = [v[f"{k}{w}"] for k in ("res", *PARTS)]
        if v[f"from{w}"] is None:
            if any(x is not None for x in nums):
                return False
        else:
            if any(x is None for x in nums) or not v[f"from{w}"] < v["to"]:
                return False
            seen = True
    return seen


WIN_KEYS = ("month", "from", "until", "bound", "ended", "n", "bn", "ops", "small", "sales", "red_from", "red_to", "red_bn",
            "rmp_bn")


def _bound_ok(w, ym):
    """창 경계 — 규칙이면 그 달 규칙의 날짜 그대로, 공식 기간이면 시작일이 그 달(끝은 시작 뒤 PLAN_SPAN_MAX일 안)."""
    if w["bound"] == "rule":
        a, b, _ = rule_bounds(ym)
        return (w["from"], w["until"]) == (_iso(a), _iso(b))
    if w["bound"] == "plan":
        a, b = _day(w["from"]), _day(w["until"])
        return (a.year, a.month) == ym and (b - a).days <= PLAN_SPAN_MAX
    return False


def _windows_ok(ws):
    """RMP 칸의 운영 결과 대조(values.checks) — 1~PLAN_ROWS_MAX개, 달이 이어지고, 창이 겹치지 않고 사이에 영업일이 비지 않고,
    경계가 규칙·공식 기간의 꼴이고, 끝나지 않은 창은 끝에만 이어서, 운영일은 창 안의 날짜 차례, 운영이 없으면 합 0, 끝나지 않은
    창은 상환·대조가 비고, 대조값은 보이는 소수 한 자리의 매입 − 상환과 같다(이어 싣는 값도 다시 맞춰 본다)."""
    if not isinstance(ws, list) or not 1 <= len(ws) <= PLAN_ROWS_MAX:
        return False
    prev, last_until = None, None
    for i, w in enumerate(ws):
        if not isinstance(w, dict) or set(w) != set(WIN_KEYS):
            return False
        m = w["month"]
        if not (isinstance(m, str) and re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", m)):
            return False
        ym = (int(m[:4]), int(m[5:]))
        if prev is not None and ym != _shift(prev, 1):
            return False
        prev = ym
        days = [w[k] for k in ("from", "until", "red_from", "red_to")]
        if not all(ai._is_day(x) for x in days) or w["bound"] not in ("plan", "rule") or not _bound_ok(w, ym):
            return False
        if last_until is not None and (not last_until < w["from"] or bday_gap(_day(last_until), _day(w["from"]))):
            return False
        last_until = w["until"]
        ints = [w[k] for k in ("n", "small", "sales")]
        if not (all(ai._is_day(x) for x in days) and all(type(x) is int and x >= 0 for x in ints)
                and type(w["ended"]) is bool and ai._is_num(w["bn"]) and w["bn"] >= 0
                and isinstance(w["ops"], list) and len(w["ops"]) == w["n"] <= 60
                and all(ai._is_day(x) and w["from"] <= x <= w["until"] for x in w["ops"]) and w["ops"] == sorted(w["ops"])
                and w["from"] <= w["until"] and (w["n"] > 0 or w["bn"] == 0)
                and (w["ended"] or all(x.get("ended") is False for x in ws[i:]))
                and (w["red_bn"] is None or ai._is_num(w["red_bn"])) and (w["rmp_bn"] is None or ai._is_num(w["rmp_bn"]))):
            return False
        if not w["ended"] and (w["red_bn"] is not None or w["rmp_bn"] is not None):
            return False
        want = None if w["red_bn"] is None else _t1(_t1(w["bn"]) - _t1(w["red_bn"]))
        if w["rmp_bn"] != want:
            return False
    return True


PLAN_KEYS = ("month", "from", "until", "form", "reinvest", "rmp")
_PLAN_AMT = re.compile(r"\d{1,4}(\.\d{1,2})?")
STATES = ("now", "next", "between", "unknown")


def _plan_windows_ok(ws):
    """RMP 칸의 창 목록(values.windows) — 1~PLAN_ROWS_MAX개, RMP 시작 달부터 달이 이어지고, 꼴(ok: 날짜·숫자 글 둘 · unknown:
    숫자 없음, 날짜는 둘 다 있거나 둘 다 없음 · missing: 모두 없음), 시작일이 그 달이고 RMP_FROM 이상, 날짜 있는 창끼리 겹치지
    않고, 마지막 창은 페이지에 있다(이어 싣는 값도 다시 맞춰 본다)."""
    if not isinstance(ws, list) or not 1 <= len(ws) <= PLAN_ROWS_MAX:
        return False
    prev, last_until = None, None
    amt = lambda v: isinstance(v, str) and _PLAN_AMT.fullmatch(v) is not None
    for w in ws:
        if not isinstance(w, dict) or set(w) != set(PLAN_KEYS):
            return False
        m = w["month"]
        if not (isinstance(m, str) and re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", m)):
            return False
        ym = (int(m[:4]), int(m[5:]))
        if ym != (_ym(RMP_FROM) if prev is None else _shift(prev, 1)):
            return False
        prev = ym
        if w["form"] not in ("ok", "unknown", "missing"):
            return False
        dated = w["from"] is not None
        if dated != (w["until"] is not None):
            return False
        if w["form"] == "ok" and not (dated and amt(w["reinvest"]) and amt(w["rmp"])):
            return False
        if w["form"] != "ok" and (w["reinvest"] is not None or w["rmp"] is not None):
            return False
        if w["form"] == "missing" and dated:
            return False
        if not dated:
            continue
        if not (ai._is_day(w["from"]) and ai._is_day(w["until"]) and w["from"] <= w["until"]):
            return False
        a, b = _day(w["from"]), _day(w["until"])
        if _ym(a) != ym or (b - a).days > PLAN_SPAN_MAX or a < RMP_FROM:
            return False
        if last_until is not None and not last_until < w["from"]:
            return False
        last_until = w["until"]
    return ws[-1]["form"] != "missing"


def _next_ok(v):
    """다음 날짜 — 0~3개, 날짜 차례, 계획 공지(month·date·official)와 FOMC(date·tentative) 꼴."""
    if not isinstance(v, list) or len(v) > 3:
        return False
    for x in v:
        if not isinstance(x, dict) or not ai._is_day(x.get("date")):
            return False
        if x.get("kind") == "plan":
            if set(x) != {"kind", "month", "date", "official"} or type(x["official"]) is not bool \
                    or not (isinstance(x["month"], str) and re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", x["month"])):
                return False
        elif x.get("kind") == "fomc":
            if set(x) != {"kind", "date", "tentative"} or type(x["tentative"]) is not bool:
                return False
        else:
            return False
    return [x["date"] for x in v] == sorted(x["date"] for x in v)


BRIDGE_KEYS = ("b0", "b1", "e0", "e1", "res", *BRIDGE_PARTS)


def _bridge_ok(v):
    """RMP 시작 뒤 나눔 — 네 날짜(이어진 네 주 두 개, 기준이 RMP_FROM 앞), 숫자, 지준 = 몫의 합."""
    if v is None:
        return True
    if not isinstance(v, dict) or set(v) != set(BRIDGE_KEYS):
        return False
    days = [v[k] for k in ("b0", "b1", "e0", "e1")]
    if not all(ai._is_day(x) for x in days) or not all(ai._is_num(v[k]) for k in ("res", *BRIDGE_PARTS)):
        return False
    b0, b1, e0, e1 = (_day(x) for x in days)
    span = 7 * (WEEKS4 - 1)
    return ((b1 - b0).days == span and (e1 - e0).days == span and b1 < RMP_FROM and b1 < e0
            and abs(v["res"] - sum(v[k] for k in BRIDGE_PARTS)) < 1e-3)


def _floor_ok(v):
    if v is None:
        return True
    return (isinstance(v, dict) and set(v) == {"low", "q0", "g0", "q1", "g1"} and ai._is_num(v["low"])
            and all(ai._is_day(v[k]) for k in ("q0", "q1")) and all(ai._is_num(v[k]) and v[k] > 0 for k in ("g0", "g1"))
            and v["q0"] <= v["q1"])


def _view_check(v):
    """칸 사이의 맞춤 — 대조 창의 달 = 창의 달, 상태 'unknown'은 마지막 창에 날짜가 없을 때만, 숫자가 없는 줄에만 사유."""
    if v["checks"] is not None and [c["month"] for c in v["checks"]] != [w["month"] for w in v["windows"]]:
        return False
    if (v["state"] == "unknown") != (v["windows"][-1]["from"] is None):
        return False
    if v["checks"] is None and v["chk_why"] is None:
        return False
    return ((v["bridge"] is None) == (v["bridge_why"] is not None) and (v["floor"] is None) == (v["floor_why"] is not None)
            and v["rows"] <= PLAN_ROWS_MAX and v["dropped"] <= 10 * PLAN_ROWS_MAX)


ITEMS = [
    {"key": "reserves", "title": "지준과 규칙 하한 (주 평균 · 지준/명목GDP)", "series": [RES_AVG, "GDP"],
     "calc": calc_reserves,
     "values": {"level": "num", "value": "num", "gdp_quarter": "day", "gdp_bn": "num", "low": "num", "gap_pp": "num",
                "gap_bn": "num", "avg4": "num?", "avg4_from": "day?", "base_quarter": "day?", "base_bn": "num?",
                "denom_pp": "num?", "first_quarter": "day", "first_bn": "num"},
     "ends": ["gdp_quarter"],
     "chart": {"unit": "bn", "zero": False,
               "note": "최근 52주 · 주 평균 지준(십억 달러) · 회색 선은 규칙 하한 × 마지막 분기 명목 GDP(지난 주들도 지금 GDP로 그은 선)"},
     "lines": [_l("res", "주 평균 지준", "main", [RES_AVG]), _l("low", "규칙 하한 × 마지막 분기 GDP", "ref", [RES_AVG, "GDP"])]},
    {"key": "dec", "title": "지준 변화의 나눔 4주/13주 (수요일 수준)", "series": list(BS.values()), "calc": calc_dec,
     "values": _dec_values(), "check": _dec_ok},
    {"key": "rmp_view", "title": RMP_NAME, "series": [*BRIDGE.values(), "GDP"], "ext": (PLAN, OPS), "calc": calc_view,
     "values": {"rows": "int", "dropped": "int", "windows": "plan_windows", "state": "state", "next": "next_dates",
                "checks": "checks?", "chk_why": "why?", "bills4": "num?", "bills13": "num?", "bridge": "bridge",
                "bridge_why": "why?", "floor": "floor", "floor_why": "why?"},
     "check": _view_check},
    {"key": "spread", "title": "SOFR − IORB (최근 5영업일)", "series": ["SOFR", "IORB"], "calc": calc_spread,
     "values": {"from": "day", "max_bp": "num", "max_date": "day", "max_tag": "tag", "pos": "int", "n": "int",
                "days": "int"},
     "check": lambda v: 0 <= v["pos"] <= v["n"] <= v["days"] <= MM_DAYS and v["n"] >= 1 and v["from"] <= v["max_date"]},
    {"key": "srf", "title": "상시 레포(SRF) 이용 (최근 5영업일)", "series": ["RPONTTLD"], "calc": calc_srf,
     "values": {"from": "day", "max_bn": "num", "max_date": "day", "max_tag": "tag"},
     "check": lambda v: v["from"] <= v["max_date"]},
    {"key": "rrp", "title": "익일물 역레포 (마지막 값)", "series": ["RRPONTSYD"], "calc": calc_rrp,
     "values": {"bn": "num", "tag": "tag"}},
    {"key": "week", "title": "이 H.4.1 주 (목~수)", "series": [RES_AVG], "calc": calc_week, "now": True,
     "values": {"from": "day", "d15": "bool", "month_end": "bool", "fomc": "days", "next_fomc": "day?",
                "next_tentative": "bool"},
     "check": lambda v: (v["next_fomc"] is not None or not v["next_tentative"]) and all(v["from"] <= x for x in v["fomc"])},
]
BY_KEY = {it["key"]: it for it in ITEMS}

TAGS = ("", "월말", "분기말", "15일")
_KIND = dict(ai._KIND, tag=lambda v: isinstance(v, str) and v in TAGS, bool=lambda v: type(v) is bool,
             days=lambda v: isinstance(v, list) and len(v) <= 3 and all(ai._is_day(x) for x in v) and v == sorted(set(v)),
             plan_windows=_plan_windows_ok, state=lambda v: v in STATES, next_dates=_next_ok,
             **{"checks?": lambda v: v is None or _windows_ok(v), "why?": lambda v: v is None or v in REASONS},
             bridge=_bridge_ok, floor=_floor_ok)


# ---------- 문구 ----------

def _s(v, nd=0):
    """부호·천 단위 쉼표 — 반올림해 0이면 부호 없이. 없으면 '—'."""
    return liq._s(v, nd)


def _q(day):
    return liq._q(day)


def _tagged(day, tag):
    """일간 날짜 표시 — '2026-10-30 월말'(괄호 안에 쓴다)."""
    return f"{day} {tag}" if tag else day


def _lvl(day):
    """창의 출발·끝 수요일 — '2026-09-30(분기말)'."""
    tag = level_tag(_day(day))
    return f"{day}({tag})" if tag else day


def _span(v, w):
    fr = v[f"from{w}"]
    if fr is None:
        return f"{w}주 —"
    return f"{w}주 {_lvl(fr)}~{_lvl(v['to'])}"


def shown(v, w):
    """창 하나의 보이는 정수 — (지준 변화, {몫: 정수}). 지준과 일곱 몫은 각자 반올림, 그 밖 = 반올림한 지준 − 일곱 몫의 합
    (보이는 숫자끼리 합이 맞게 — 지준·재정 카드 관례). 창이 없으면 (None, {})."""
    if v[f"from{w}"] is None:
        return None, {}
    sh = {k: round(v[f"{k}{w}"]) for k in SIGN}
    res = round(v[f"res{w}"])
    return res, {**sh, "other": res - sum(sh.values())}


def _pair(a, b):
    return f"{_s(a)}/{_s(b)}"


def _num(x):
    """계획 금액의 합·누적 — 소수 둘째 자리까지, 끝의 0은 뺀다(215 · 2.5 · 12.25), 천 단위 쉼표."""
    t = f"{x:,.2f}".rstrip("0").rstrip(".")
    return "0" if t in ("", "-0") else t


def _md(day, year):
    """날짜 — 그 해(year) 안이면 'MM-DD', 아니면 'YYYY-MM-DD'."""
    return day[5:] if int(day[:4]) == year else day


def _span_full(a, b):
    """'2026-10-15~11-13' — 둘째 날짜는 같은 해면 MM-DD."""
    return f"{a}~{_md(b, int(a[:4]))}"


def _span_short(a, b, year):
    """'10-15~11-13' — 둘 다 그 해(year) 안일 때만 줄이고, 아니면 _span_full."""
    return f"{a[5:]}~{b[5:]}" if int(a[:4]) == int(b[:4]) == year else _span_full(a, b)


def _wd(day):
    return KO_WD[_day(day).weekday()]


def _mname(month, year):
    """'2026-08' → '8월'(그 해 안), 아니면 '2025년 12월'."""
    y, m = int(month[:4]), int(month[5:])
    return f"{m}월" if y == year else f"{y}년 {m}월"


def _nth(k):
    """이어진 창 수 — '세 창째'(열까지 고유어), 그 뒤 '11창째'."""
    return f"{NATIVE[k]} 창째" if k in NATIVE else f"{k}창째"


def rmp_groups(ws):
    """같은 RMP가 이어진 창의 묶음 → [(첫 창 차례, 끝 창 차례, 키)] — 키는 ('ok', 금액) · ('unknown',) · ('missing',)."""
    key = lambda w: ("ok", float(w["rmp"])) if w["form"] == "ok" else (w["form"],)
    out = []
    for i, w in enumerate(ws):
        if out and out[-1][2] == key(w):
            out[-1] = (out[-1][0], i, out[-1][2])
        else:
            out.append((i, i, key(w)))
    return out


def rmp_cum(ws):
    """창마다 RMP_FROM 창부터의 계획 누적 — 꼴 모름·없는 창부터는 None."""
    out, total = [], 0.0
    for w in ws:
        total = None if total is None or w["form"] != "ok" else total + float(w["rmp"])
        out.append(total)
    return out


def rmp_diffs(v):
    """끝난 창의 '대조 − 계획 RMP'(보이는 소수 한 자리끼리) — 계획을 읽은 창만."""
    if v["checks"] is None:
        return []
    return [_t1(c["rmp_bn"] - float(w["rmp"])) for w, c in zip(v["windows"], v["checks"])
            if w["form"] == "ok" and c["ended"] and c["rmp_bn"] is not None]


def rmp_text(v, date):
    """RMP 칸의 글 — {window, head(토막 목록), dates, caption, table{head, rows[{cells, note}]}, mean, bridge{tag, text},
    floor{tag, text}, notes}. 정해 둔 문구에 숫자만 넣는다(판정 낱말 없음). 해는 마지막 창의 달로 줄인다(그 해 안이면 MM-DD)."""
    ws, state = v["windows"], v["state"]
    last = ws[-1]
    year = int(last["month"][:4])
    lead = {"now": "지금 창", "next": "다음 창", "between": "마지막 창"}.get(state, f"{_mname(last['month'], year)} 창")
    this = "이번 창" if state == "now" else "그 창"
    groups, cums = rmp_groups(ws), rmp_cum(ws)
    unknown = sum(1 for w in ws if w["form"] == "unknown")
    missing = sum(1 for w in ws if w["form"] == "missing")
    # 머리
    if last["form"] != "ok":
        head = [f"{lead} 계획 문장 꼴 모름 — 숫자를 짓지 않음"]
    elif state == "between":
        head = [f"{lead} RMP {last['rmp']}bn ({_mname(last['month'], year)} 창)", "다음 창 계획은 페이지에 아직 없음"]
    else:
        head = [f"{lead} RMP {last['rmp']}bn"]
        i0, i1, _ = groups[-1]
        k = i1 - i0 + 1
        if k >= 2:
            same = "0" if float(last["rmp"]) == 0 else "같은 금액"
            head.append(f"{_mname(ws[i0]['month'], year)} 창부터 {_nth(k)} {same}")
        elif i0 > 0 and ws[i0 - 1]["form"] == "ok":
            head.append(f"{'지난 창' if state == 'now' else '지금 창'} {ws[i0 - 1]['rmp']}bn에서 바뀜")
    gone = [x for x in (f"꼴 모름 창 {unknown}개" if unknown else "", f"페이지에 없는 창 {missing}개" if missing else "") if x]
    cum = f"{_num(cums[-1])}bn" if cums[-1] is not None else "—(" + " · ".join(gone) + ")"
    head.append(f"{_iso(RMP_FROM)} 창부터 계획 누적 {cum}")
    if last["form"] == "ok":
        head.append(f"{this} 단기채 매입 계획 {last['reinvest']}bn은 모두 MBS 상환분 재투자" if float(last["rmp"]) == 0 else
                    f"{this} 단기채 매입 계획은 재투자 {last['reinvest']}bn + RMP {last['rmp']}bn")
    window = f"{lead} {_span_full(last['from'], last['until'])}" if last["from"] else lead
    # 다음 날짜
    bits, rule = [], []
    for x in v["next"]:
        md = _md(x["date"], year)
        if x["kind"] == "plan":
            bits.append(f"{_mname(x['month'], year)} 계획 공지 {md}({_wd(x['date'])})" + ("" if x["official"] else "께"))
            if not x["official"]:
                rule.append(md)
        else:
            bits.append(f"FOMC {md}({_wd(x['date'])}" + (", 잠정)" if x["tentative"] else ")"))
    dates = "다음 날짜: " + " · ".join(bits) if bits else ""
    official = [_md(x["date"], year) for x in v["next"] if x["kind"] == "plan" and x["official"]]
    # 표
    shown = groups[-GROUPS_MAX:]
    rows = []
    for i0, i1, key in shown:
        label = ws[i0]["month"] if i0 == i1 else f"{ws[i0]['month']}~{ws[i1]['month']}"
        k = i1 - i0 + 1
        cell = f"{ws[i0]['rmp']} × {k}창" if key[0] == "ok" else ("꼴 모름" if key[0] == "unknown" else "페이지에 없음") + f" × {k}창"
        re_vals = sorted((float(w["reinvest"]), w["reinvest"]) for w in ws[i0:i1 + 1] if w["form"] == "ok")
        reinv = "—" if not re_vals else re_vals[0][1] if re_vals[0][0] == re_vals[-1][0] else f"{re_vals[0][1]}~{re_vals[-1][1]}"
        note = {"now": "지금 창까지", "next": "다음 창까지"}.get(state, "") if i1 == len(ws) - 1 else ""
        rows.append({"cells": [label, cell, _num(cums[i1]) if cums[i1] is not None else "—", reinv], "note": note})
    named = last if last["from"] else next((w for w in reversed(ws) if w["from"]), None)
    caption = "창마다의 계획 금액(bn) — 창은 시작 달로 부르고"
    if named:
        caption += f"({_mname(named['month'], year)} 창 = {_span_short(named['from'], named['until'], year)})"
    caption += ", RMP가 같은 창끼리 한 줄로 묶었다."
    if len(groups) > GROUPS_MAX:
        before = groups[-GROUPS_MAX][0]
        caption += f" 표는 마지막 {GROUPS_MAX}묶음만 — 그 앞 {before}창은 누적에만 든다."
    pair = ""
    if v["bills4"] is not None or v["bills13"] is not None:
        r = lambda x: None if x is None else round(x)
        pair = f"(4주/13주 {_pair(r(v['bills4']), r(v['bills13']))})"
    mean = RMP_MEAN + f" 위 나눔 칸의 연준 단기채{pair}는 둘의 합이다."
    # 시작 뒤 나눔·하한
    br = v["bridge"]
    if br:
        res = round(br["res"])
        sh = {k: round(br[k]) for k in BRIDGE_PARTS if k != "other"}
        sh["other"] = res - sum(sh.values())
        bridge_text = (f"{_s(res)}bn = " + " · ".join(f"{BRIDGE_NAME[k]} {_s(sh[k])}" for k in BRIDGE_PARTS)
                       + " (수요일 수준 네 주 평균의 차, 부호는 지준 쪽)")
    else:
        bridge_text = f"— 미수신({REASONS[v['bridge_why']]})"
    fl = v["floor"]
    if fl:
        f0, f1 = round(fl["low"] / 100 * fl["g0"]), round(fl["low"] / 100 * fl["g1"])
        floor_text = (f"{f0:,}bn({_q(fl['q0'])})에서 {f1:,}bn({_q(fl['q1'])})으로 {_s(f1 - f0)}bn "
                      f"({fl['low']:.1f}% × 분기 명목 GDP)")
    else:
        floor_text = f"— 미수신({REASONS[v['floor_why']]})"
    low = fl["low"] if fl else float(rr.TH["reserves_gdp_low"])
    four = (f"네 주 = RMP 시작 앞 {_span_full(br['b0'], br['b1'])}과 최근 {_span_full(br['e0'], br['e1'])} · " if br else "")
    notes = [f"{four}GDP는 현재 개정치. {low:.1f}%" + AMPLE]
    diffs = rmp_diffs(v)
    if diffs:
        lo, hi = min(diffs), max(diffs)
        rng = f"{_s(lo, 1)}bn" if lo == hi else f"{_s(lo, 1)}~{_s(hi, 1)}bn"
        chk = f"{CHK_HEAD}와 계획 RMP의 차는 끝난 {len(diffs)}창에서 {rng}"
    else:
        chk = f"{CHK_HEAD}: 미수신({REASONS[v['chk_why'] or 'format']})"
    tail = []
    if official:
        tail.append("·".join(official) + "은 공식 표의 다음 공지 칸 날짜")
    if rule:
        tail.append("·".join(rule) + "은 방침 '매달 9영업일께'로 센 날" + ("" if official else "(공식 표의 다음 공지 칸은 비어 있음)"))
    notes.append(" · ".join(["계획 금액은 뉴욕 연은 공지 문장을 옮긴 것이다", chk, *tail]) + ".")
    if v["dropped"]:
        notes.append(f"페이지 표의 행 가운데 기간 날짜를 읽지 못한 {v['dropped']}개는 뺐다.")
    return {"window": window, "head": head, "dates": dates, "caption": caption,
            "table": {"head": list(TABLE_HEAD), "rows": rows}, "mean": mean,
            "bridge": {"tag": BRIDGE_TAG, "text": bridge_text}, "floor": {"tag": FLOOR_TAG, "text": floor_text},
            "notes": notes}


def texts(key, v, date):
    """칸 → (숫자 줄, 덧붙이는 줄 목록). 정해 둔 문구에 숫자만 넣는다(판정 낱말·문턱 표식 없음)."""
    if key == "reserves":
        avg4 = "—" if v["avg4"] is None else f"{v['avg4']:.2f}%"
        line = (f"지준 {v['level']:,.1f}bn (주 평균) = 명목 GDP의 {v['value']:.2f}% ({_q(v['gdp_quarter'])}) · "
                f"규칙 하한 {v['low']:.1f}% 대비 {_s(v['gap_pp'], 2)}%p ≈ {_s(v['gap_bn'], 1)}bn · 4주 평균 {avg4}")
        extra = [f"{date} 주(목~수)의 주 평균 지준(WRESBAL) ÷ 마지막 분기 명목 GDP(계절조정 연율, {_q(v['gdp_quarter'])} "
                 f"{v['gdp_bn']:,.0f}bn)다 — 규칙 카드 '지준과 통화승수'와 같은 식·같은 GDP 분기다. 달러 환산 = (값 − 하한) × "
                 "그 분기 GDP."]
        if v["avg4"] is not None:
            extra.append(f"{AVG4_DEF} — {v['avg4_from']}~{date} 네 주가 이어질 때만 싣는다(각 주를 그 주의 GDP로 나눈 "
                         "평균이 아니다).")
        else:
            extra.append(f"{AVG4_DEF} — 최근 네 주가 이어지지 않아 싣지 않는다.")
        if v["denom_pp"] is not None:
            how = (f"{_q(v['gdp_quarter'])} 개정" if v["base_quarter"] == v["gdp_quarter"]
                   else f"GDP {_q(v['base_quarter'])}에서 {_q(v['gdp_quarter'])}로")
            line += f" · 분모 바뀜 {_s(v['denom_pp'], 2)}%p ({how})"
            extra.append(f"분모 바뀜 = 이번 지준 ÷ 이번 GDP − 같은 지준 ÷ 직전 주를 처음 실을 때의 GDP"
                         f"({_q(v['base_quarter'])} {v['base_bn']:,.0f}bn). 지준이 그대로여도 GDP가 바뀌면 하한까지의 거리가 "
                         "움직인다.")
        return line, extra
    if key == "dec":
        r4, p4 = shown(v, "4")
        r13, p13 = shown(v, "13")
        line = (f"지준 변화 4주/13주 {_pair(r4, r13)}bn = "
                + " · ".join(f"{PART_NAME[k]} {_pair(p4.get(k), p13.get(k))}" for k in PARTS) + f" {SIGN_NOTE}")
        extra = [f"창: {_span(v, '4')} · {_span(v, '13')} — H.4.1 수요일 수준의 차이고, bn은 십억 달러다."]
        starts = [(w, v[f"from{w}"], level_tag(_day(v[f"from{w}"]))) for w, _ in WINDOWS if v[f"from{w}"]]
        marked = [f"{w}주 창은 {t}({d})" for w, d, t in starts if t]
        if marked:
            extra.append(" · ".join(marked) + "에서 출발해, 그날 하루 튄 역레포·재무부 현금·지준이 되돌아온 몫이 그 칸에 "
                         "섞여 있다.")
        extra.append("부호는 지준 쪽이다 — 재무부 현금(TGA)·역레포·현금 통화가 늘면 그만큼 지준이 줄어 −, 연준 보유 단기채·"
                     "이표채·MBS가 늘면 +. '그 밖'은 나머지(대출·상시 레포·기타 부채 등)이고, 보이는 정수끼리 합이 맞게 반올림 "
                     "차를 받는다. 1주 변화는 15일·월말 하루에 크게 흔들려 싣지 않는다.")
        extra.append("13주 칸은 위 지준·재정 카드의 13주 나눔과 같은 규칙으로 낸 값이다 — 그 카드의 역레포는 익일물 + 해외 "
                     "공적 역레포, 그 카드의 '그 밖'은 연준 MBS + 현금 통화 + 이 카드의 '그 밖'이다.")
        return line, extra
    if key == "rmp_view":
        t = rmp_text(v, date)
        rows = [" · ".join(r["cells"]) + (f" ({r['note']})" if r["note"] else "") for r in t["table"]["rows"]]
        extra = [x for x in (t["dates"], t["caption"]) if x] + rows + [t["mean"], f"{t['bridge']['tag']} {t['bridge']['text']}",
                                                                      f"{t['floor']['tag']} {t['floor']['text']}", *t["notes"]]
        return " · ".join(t["head"]), extra
    if key == "spread":
        line = (f"SOFR − IORB 최대 {_s(v['max_bp'])}bp ({_tagged(v['max_date'], v['max_tag'])}) · 0보다 큰 날 "
                f"{v['pos']}/{v['n']}일 ({v['from']}~{date})")
        extra = ["SOFR(뉴욕 연은 담보부 익일물 금리)에서 그날 이하 마지막 IORB(연준 지준 부리 금리)를 뺀 bp다 — SOFR의 마지막 "
                 "관측 다섯(영업일). 같은 최대가 여러 날이면 이른 날을 적는다."]
        if v["n"] < v["days"]:
            extra.append(f"IORB 관측이 {IORB_GAP}일보다 먼 날은 비워 {v['days']}일 중 {v['n']}일만 견줬다.")
        return line, extra
    if key == "srf":
        line = f"상시 레포 이용 최대 {v['max_bn']:,.1f}bn ({_tagged(v['max_date'], v['max_tag'])}) · {v['from']}~{date}"
        return line, ["뉴욕 연은 임시 공개시장 운영의 익일물 레포 합계(RPONTTLD — 상시 레포 기구 SRF 이용), 십억 달러다. "
                      "시리즈의 마지막 관측 다섯 가운데 최대이고, 같은 값이면 이른 날을 적는다."]
    if key == "rrp":
        line = f"익일물 역레포 {v['bn']:,.1f}bn ({_tagged(date, v['tag'])})"
        return line, ["뉴욕 연은 익일물 역레포 기구(RRPONTSYD)의 마지막 값, 십억 달러다. 나눔 칸의 익일물 역레포(WLRRAOL)는 "
                      "H.4.1 수요일 수준이라 날짜가 다르다."]
    if key == "week":
        marks = [x for x, on in (("15일", v["d15"]), ("월말", v["month_end"])) if on]
        bits = [("·".join(marks) + " 포함") if marks else "",
                f"FOMC 뒤 첫 H.4.1({', '.join(v['fomc'])} 결정)" if v["fomc"] else ""]
        inside = " · ".join(b for b in bits if b) or "15일·월말·FOMC 없음"
        nxt = (f" · 다음 FOMC {v['next_fomc']}" + ("(잠정)" if v["next_tentative"] else "")) if v["next_fomc"] \
            else " · 다음 FOMC 미기재"
        line = f"이 주({v['from']}~{date}) {inside}{nxt}"
        extra = []
        if v["fomc"]:
            extra.append("FOMC 결정일(수)이 이 주의 마지막 날이라 이 주의 지준·나눔·주 평균은 결정이 시행되기 전 값이다 — "
                         "IORB·역레포 금리·운용 변경은 결정 다음 날(목)부터라 결정의 흔적은 다음 주 숫자에서 본다.")
        if marks:
            extra.append("15일·월말이 든 주는 수요일 수준이 그날 하루의 결제(국채 결제·세금)에 흔들릴 수 있다.")
        extra.append("H.4.1 주는 목요일부터 수요일까지이고, 연준이 다음 날(목) 16:30(미 동부)에 발표한다.")
        return line, extra
    raise KeyError(key)


def citation(sid, retrieved):
    d = datetime.date.fromisoformat(retrieved)
    src, title = SOURCES[sid]
    return (f"{src}, {title} [{sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; "
            f"{rp.FRED_URL.format(sid)}, {ai._MONTHS[d.month - 1]} {d.day}, {d.year}.")


def ops_citation(retrieved, title=OPS_TITLE, url=OPS_URL):
    """뉴욕 연은 국채 운영 결과·공식 계획 페이지의 인용(tp_fetch의 ACM과 같은 꼴 — 'retrieved from <주소>, <날짜>.')."""
    d = datetime.date.fromisoformat(retrieved)
    return f"{_NYFED}, {title}, retrieved from {url}, {ai._MONTHS[d.month - 1]} {d.day}, {d.year}."


EXT = {OPS: (OPS_URL, OPS_TITLE), PLAN: (PLAN_URL, PLAN_TITLE)}


def sources_of(spec, retrieved=None):
    out = []
    for sid in spec["series"]:
        s = {"series": sid, "name": SOURCES[sid][0], "url": rp.FRED_URL.format(sid), "licence": LICENCE[sid]}
        if retrieved:
            s["citation"] = citation(sid, retrieved)
        out.append(s)
    for ext in spec.get("ext", ()):
        url, title = EXT[ext]
        s = {"series": ext, "name": _NYFED, "url": url, "licence": OPS_LICENCE}
        if retrieved:
            s["citation"] = ops_citation(retrieved, title, url)
        out.append(s)
    return out


def notices(key, retrieved):
    year = retrieved[:4]
    if key == "spread":
        return [COMPUTED_NOTICE, SPREAD_DERIVED, SPREAD_DERIVED_EN, rp.SOFR_NOTICE, rp.SOFR_DTCC,
                rp.nyfed_attribution(year), rp.NOT_AFFILIATED]
    if key == "srf":
        return [COMPUTED_NOTICE, SRF_DERIVED, SRF_DERIVED_EN, rp.nyfed_attribution(year), rp.NOT_AFFILIATED]
    if key == "rrp":
        return [rp.nyfed_attribution(year), rp.NOT_AFFILIATED]
    if key == "week":
        return [WEEK_NOTICE]
    if key == "rmp_view":
        return [COMPUTED_NOTICE, RMP_NOTICE, RMP_NOTICE_EN, rp.nyfed_attribution(year), rp.NOT_AFFILIATED]
    return [COMPUTED_NOTICE]


def source_note(spec):
    names = list(dict.fromkeys(SOURCES[sid][0] for sid in spec["series"]))
    return "자료: " + " · ".join(names) + " (via FRED) · 하한 선은 macro-regime-check가 이 자료로 계산한 값"


def present(key, core, retrieved):
    spec = BY_KEY[key]
    line, extra = texts(key, core["values"], core["date"])
    out = {"key": key, "name": spec["title"], "date": core["date"], "values": core["values"], "retrieved": retrieved,
           "line": line, "extra": extra, "notices": notices(key, retrieved), "sources": sources_of(spec, retrieved)}
    if key == "rmp_view":
        out["view"] = rmp_text(core["values"], core["date"])     # 화면이 칸 안의 줄·표를 나눠 그린다(같은 글)
    if spec.get("lines"):
        c = spec["chart"]
        out["chart"] = {"key": f"fedbs_{key}", "title": spec["title"], "unit": c["unit"], "zero": c["zero"],
                        "threshold": None, "note": c["note"], "source_note": source_note(spec), "notices": [],
                        "lines": [{**ln, "derived": False, "points": core["lines"][ln["key"]]} for ln in spec["lines"]]}
    return out


# ---------- 직전 파일 ----------

def values_ok(spec, vals, lines):
    return (isinstance(vals, dict) and set(vals) == set(spec["values"])
            and all(_KIND[t](vals[k]) for k, t in spec["values"].items())
            and (spec.get("check") is None or spec["check"](vals))
            and isinstance(lines, dict) and set(lines) == {ln["key"] for ln in spec.get("lines", ())}
            and all(isinstance(pts, list) and len(pts) <= CHART_WEEKS
                    and all(isinstance(p, list) and len(p) == 2 and ai._is_day(p[0]) and ai._is_num(p[1]) for p in pts)
                    for pts in lines.values()))


def core_of(item, key):
    """직전 파일의 칸 → (core, 받은 날) 또는 None(없거나 꼴이 어긋남 — 이어 실을 값이 없는 것으로 본다)."""
    spec = BY_KEY[key]
    try:
        vals = item["values"]
        lines = {ln["key"]: ln["points"] for ln in item["chart"]["lines"]} if spec.get("lines") else {}
        ok = ai._is_day(item["date"]) and ai._is_day(item["retrieved"]) and values_ok(spec, vals, lines)
        if ok:
            texts(key, vals, item["date"])          # 문구를 다시 만들 수 있어야 한다
    except (KeyError, TypeError, IndexError, AttributeError, ValueError, OverflowError):
        return None
    if not ok:
        return None
    return {"date": item["date"], "values": dict(vals), "lines": lines}, item["retrieved"]


def previous(out):
    try:
        with open(os.path.join(out, FILE), encoding="utf-8") as f:
            js = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(js, dict) or js.get("schema") != SCHEMA or not isinstance(js.get("items"), dict):
        return {}
    return {k: v for k, v in js["items"].items() if k in BY_KEY and isinstance(v, dict)}


def _ends(key, core):
    return [("date", core["date"])] + [(k, core["values"].get(k)) for k in BY_KEY[key].get("ends", ())]


def item_ok(key, core, prev, today):
    old = core_of(prev, key) if prev else None
    if key == "reserves":
        core = with_base(core, old[0] if old else None)
    if not values_ok(BY_KEY[key], core["values"], core["lines"]):
        raise ItemError("format")                   # 새로 계산한 값도 같은 꼴을 넘어야 싣는다
    if old and any(new and was and new < was for (_, new), (_, was) in zip(_ends(key, core), _ends(key, old[0]))):
        raise ItemError("older")
    same = old and json.loads(json.dumps(old[0])) == json.loads(json.dumps(core))
    retrieved = old[1] if same else today.isoformat()
    return {"ok": True, "stale": False, "error": None, "failed_since": None, **present(key, core, retrieved)}


def item_failed(key, code, prev, today):
    since = prev.get("failed_since") if prev and ai._is_day(prev.get("failed_since")) else today.isoformat()
    old = core_of(prev, key) if prev else None
    if old:
        return {"ok": False, "stale": True, "error": REASONS[code], "failed_since": since, **present(key, *old)}
    spec = BY_KEY[key]
    return {"ok": False, "stale": False, "error": REASONS[code], "failed_since": since, "key": key,
            "name": spec["title"], "sources": sources_of(spec)}


def build(results, prev, now):
    """칸마다 싣는다. results에 없는 칸(운영 결과를 넘기지 않은 compute의 rmp)은 파일에도 넣지 않는다."""
    today = now.date()
    items = {}
    for spec in ITEMS:
        key = spec["key"]
        if key not in results:
            continue
        r, p = results[key], prev.get(key)
        if not isinstance(r, ItemError):
            try:
                items[key] = item_ok(key, r, p, today)
                continue
            except ItemError as e:
                r = e
        items[key] = item_failed(key, r.code, p, today)
    return {"schema": SCHEMA, "generated_at": now.isoformat(timespec="seconds"), "notice": NOTICE,
            "order": [s["key"] for s in ITEMS if s["key"] in items], "items": items}


# ---------- 수신 ----------

def load_all(work, offline=False, fred_load=None, clock=time.monotonic, budget=BUDGET, opener=None):
    """{ID: 시계열}과 {ID: 실패 코드}. 온라인에서 캐시로 대신한 것은 실패('cache')."""
    cache = os.path.join(work, CACHE)
    data, errors = {}, {}
    deadline = clock() + budget
    for sid in SERIES:
        left = deadline - clock()
        if not offline and left <= 1:
            errors[sid] = "fetch"
            continue
        try:
            if fred_load:
                series, src = fred_load(sid, cache, offline=offline, timeout=min(ai.TIMEOUT, max(1.0, left)))
            else:
                series, src = ai.load_series(sid, cache, offline, deadline, clock, opener)
        except Exception:
            errors[sid] = "fetch"
            continue
        if src != "net" and not offline:
            errors[sid] = "cache"
            continue
        if not series:
            errors[sid] = "format"
            continue
        data[sid] = series
    return data, errors


def compute(data, errors, today, now=None, ops=None, plan=None):
    """칸마다 계산 — now(실행 시각, UTC)는 '다음 FOMC'를 고르는 주 칸·RMP 칸만 쓴다(없으면 today 0시). plan은 공식 계획
    (load_plan — dict 또는 ItemError), ops는 뉴욕 연은 국채 운영 결과(load_ops — 목록 또는 ItemError)로 RMP 칸(rmp_view)에 쓴다.
    plan을 넘기지 않으면(None) 그 칸은 셈하지 않는다(결과에 없다 — 비공개 쪽 짝 테스트 등). ops를 받지 못하면 그 칸의 대조 한
    줄만, FRED 시리즈를 받지 못하면 시작 뒤 나눔·하한 줄만 미수신."""
    S = {sid: [(d, v) for d, v in s if d <= today] for sid, s in data.items()}
    out = {}
    for spec in ITEMS:
        if spec.get("ext"):
            if plan is None:
                continue
            if isinstance(plan, ItemError):
                out[spec["key"]] = plan
                continue
            try:
                out[spec["key"]] = spec["calc"](S, today, plan, ops, errors, now)
            except ItemError as e:
                out[spec["key"]] = e
            except Exception as e:              # 계산 쪽 뜻밖의 오류도 그 칸만 실패로
                print(f"[fedbs_fetch] {spec['key']} 계산 오류: {type(e).__name__}", file=sys.stderr)
                out[spec["key"]] = ItemError("format")
            continue
        miss = [sid for sid in spec["series"] if sid not in S or not S[sid]]
        if miss:
            out[spec["key"]] = ItemError(errors.get(miss[0], "format"))
            continue
        try:
            out[spec["key"]] = spec["calc"](S, today, now) if spec.get("now") else spec["calc"](S, today)
        except ItemError as e:
            out[spec["key"]] = e
        except Exception as e:                  # 계산 쪽 뜻밖의 오류도 그 칸만 실패로
            print(f"[fedbs_fetch] {spec['key']} 계산 오류: {type(e).__name__}", file=sys.stderr)
            out[spec["key"]] = ItemError("format")
    return out


def load_ops(work, today, offline=False, clock=time.monotonic, opener=None, ops_load=None, budget=OPS_BUDGET):
    """뉴욕 연은 국채 운영 결과 → [(운영일, 방향, 달러)] 또는 ItemError. 온라인이면 요청 1번(ops_range — credit_fetch.
    fetch_bytes: 이 프로젝트를 밝히는 UA(credit_fetch.UA)·https·같은 호스트, 요청 하나엔 min(10초, 남은 예산)), 읽히면 원문을 캐시에
    둔다. 받지 못하면 캐시로 대신하지 않는다('fetch'). --offline이면 캐시만. ops_load(주소, 마감)는 테스트가 바꿔 끼운다."""
    path = os.path.join(work, CACHE, OPS_CACHE)
    try:
        if offline:
            with open(path, "rb") as f:
                blob = f.read()
        else:
            start, end = ops_range(today)
            url = OPS_URL + "?" + urllib.parse.urlencode({"startDate": start.isoformat(), "endDate": end.isoformat()})
            deadline = clock() + budget
            blob = ops_load(url, deadline) if ops_load else cf.fetch_bytes(url, OPS_HOST, deadline, clock, opener)
    except Exception:
        return ItemError("fetch")
    try:
        ops = parse_ops(blob)
    except ItemError as e:
        return e
    if not offline:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            ai._atomic_write(path, blob.decode("utf-8") if isinstance(blob, bytes) else blob)
        except (OSError, UnicodeDecodeError):
            pass
    return ops


def load_plan(work, offline=False, clock=time.monotonic, opener=None, plan_load=None, budget=OPS_BUDGET):
    """뉴욕 연은 공식 계획 페이지 → parse_plan의 dict 또는 ItemError. 온라인이면 요청 1번(PLAN_URL — credit_fetch.fetch_bytes:
    이 프로젝트를 밝히는 UA·https·같은 호스트, 다른 곳으로 넘겨지면 받지 않음, 요청 하나엔 min(10초, 남은 예산)), 표를 읽으면
    원문을 <work>/fedbs/tsy_plan.html에 둔다. 받지 못하면 캐시로 대신하지 않는다('fetch'). --offline이면 캐시만.
    plan_load(주소, 마감)는 테스트가 바꿔 끼운다."""
    path = os.path.join(work, CACHE, PLAN_CACHE)
    try:
        if offline:
            with open(path, "rb") as f:
                blob = f.read(PLAN_MAX + 1)
        else:
            deadline = clock() + budget
            blob = plan_load(PLAN_URL, deadline) if plan_load else cf.fetch_bytes(PLAN_URL, PLAN_HOST, deadline, clock, opener)
    except Exception:
        return ItemError("fetch")
    try:
        plan = parse_plan(blob)
    except ItemError as e:
        return e
    if not offline:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            ai._atomic_write(path, blob.decode("utf-8", errors="replace") if isinstance(blob, bytes) else blob)
        except OSError:
            pass
    return plan


# ---------- 쓰기 ----------

def differs(out, data):
    try:
        with open(os.path.join(out, FILE), encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        return True
    strip = lambda d: {k: v for k, v in d.items() if k != "generated_at"} if isinstance(d, dict) else d
    return strip(old) != strip(json.loads(json.dumps(data)))


def write(out, data):
    os.makedirs(out, exist_ok=True)
    ai._atomic_write(os.path.join(out, FILE), json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def main(argv=None, fred_load=None, now=None, clock=time.monotonic, opener=None, ops_load=None, plan_load=None):
    ap = argparse.ArgumentParser(description="FRED 공개 통계 → 연준 재무상태표 참고 자료(<out>/fedbs.json)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    ap.add_argument("--work", default=DEFAULT_WORK, help="작업 폴더 — 원문 캐시는 <work>/fedbs/ (기본: 저장소의 .work/)")
    ap.add_argument("--offline", action="store_true", help="요청하지 않고 캐시만 읽는다(로컬 확인용)")
    a = ap.parse_args(argv)
    out, work = os.path.abspath(a.out), os.path.abspath(a.work)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    data, errors = load_all(work, a.offline, fred_load, clock, opener=opener)
    t0 = clock()                               # 뉴욕 연은 두 요청은 OPS_BUDGET초를 함께 쓴다
    ops = load_ops(work, now.date(), a.offline, clock, opener=opener, ops_load=ops_load)
    plan = load_plan(work, a.offline, clock, opener=opener, plan_load=plan_load, budget=OPS_BUDGET - (clock() - t0))
    data = build(compute(data, errors, now.date(), now, ops=ops, plan=plan), previous(out), now)
    for key, it in data["items"].items():      # Actions 로그 — 날짜와 정해 둔 사유만(값은 찍지 않는다)
        if it["ok"]:
            print(f"[fedbs_fetch] {key} {it['date']} 기준")
        else:
            kept = f" — 직전 값({it['date']} 기준) 유지" if it["stale"] else ""
            ai.annotate(f"연준 재무상태표 참고 {key} 받지 못함: {it['error']}{kept}")
    try:
        if differs(out, data):
            write(out, data)
    except OSError as e:
        print(f"[fedbs_fetch] {FILE}를 쓰지 못함: {type(e).__name__}", file=sys.stderr)
        return 1
    return 0 if any(it["ok"] for it in data["items"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
