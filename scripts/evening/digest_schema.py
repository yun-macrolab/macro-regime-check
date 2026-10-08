#!/usr/bin/env python3
"""저녁판 계약 — 단계 사이에 오가는 자료의 형태와 검증 (2026-10-08, 1단계 규칙 선별판).

평일 저녁, 텔레그램 공개 채널 여러 곳이 함께 다룬 주제를 LLM 없이 규칙으로 고른다. 이 모듈이 단계들의 유일한 기준이다:
수집 → 묶기 → 점수 → 조립 → 검사가 서로 묻지 않고 맞물리도록 자료의 형태(validate_*)·판 날짜와 수집 창·주소와 id 만드는 법을
여기에 못 박는다. 다른 스크립트는 "import digest_schema as S" 하나로 쓴다:
  digest_rules.py   숫자(TH)와 낱말(사전·결과 낱말·고정 문구·허용 단위) — S.R 또는 import digest_rules
  digest_base.py    시각·수집 창·주소·열쇠·링크 순서·수집 판정·닫힌 글자 검사·읽고 쓰기 — S.collect_window처럼 여기서 그대로 나온다
  digest_schema.py  형태와 validate_* (이 파일)
  fixtures.py       지어낸 글과 단계별 예시 자료 — 모든 테스트가 쓴다

가장 중요한 선: 채널 글의 글자는 공개 산출물(data/*.json, site/*, 공개 Actions 로그)에 한 글자도 나가지 않는다.
  - 원문이 든 형태는 post 하나뿐이다(posts.json · pages/). <work> 밖으로 나가지 않고, 커밋·아티팩트·로그에 넣지 않는다.
  - 묶기(digest_cluster)가 원문을 읽는 마지막 단계다. clusters.json부터는 닫힌 값만 있다: 사전 낱말 · 결과 낱말 · 숫자+허용 단위 ·
    시각 · 목록의 채널 이름 · 글 번호 · 해시. 그래서 점수·조립 단계는 원문을 볼 길이 없다.
  - 공개본의 모든 문자열은 허용 목록으로 다시 조립돼야 한다(closed_violations). 규칙판의 글자 검사는 이것 하나다.
  - validate_*의 오류 메시지에는 "어느 칸이 왜"만 있고 값은 없다(값에 원문이 섞여 있을 수 있다).

CLI 계약 — 모두 scripts/evening/ 아래, 표준 라이브러리만, 저장소 루트에서 실행. __init__.py는 두지 않는다
(아침의 "unittest discover -s scripts"가 저녁 테스트를 줍지 않게. 저녁 테스트: python -m unittest discover -s scripts/evening).
  공통  · 출력에는 개수·날짜·코드만(report()). main은 run_cli()로 감싼다 — 예외가 나면 "[이름] 실패: 예외 종류"만 찍고 종료코드 1.
        · JSON은 read_json() · write_json()(UTF-8, 원자적 교체)으로 읽고 쓰고, 쓰기 전에 validate_*를 부른다.
        · --work 기본값 .work/evening (git 제외).
  1) tg_collect.py --sources data/sources.json --state data/digest_state.json --work .work/evening [--replay] [--now ISO]
       읽기  sources.json · digest_state.json(없으면 첫 실행) · https://t.me/s/<handle> (role off는 요청하지 않는다. wire는 ?q= 검색 1쪽)
       쓰기  <work>/pages/<handle>-<n>.html · <work>/pages/manifest.json · <work>/posts.json · <work>/collect_status.json
       --replay  네트워크 없이 pages/의 저장분으로 posts.json · collect_status.json을 다시 만든다(--now가 없으면 manifest의 now)
       종료코드  0 수집을 마침(채널 일부 실패·수집 부족 포함 — 판단은 collect_status.verdict) / 1 수집 자체가 실패(아무것도 쓰지 않음)
  2) digest_cluster.py --work .work/evening
       읽기  posts.json · collect_status.json      쓰기  <work>/clusters.json      종료코드 0 / 1
  3) digest_score.py --work .work/evening --calendar data/calendar.json --korea data/korea.json --state data/digest_state.json
       읽기  clusters.json · calendar.json · korea.json(아침 잡의 것, 읽기만) · digest_state.json(state_base로 '직전 판'을 고른다)
       쓰기  <work>/scored.json      종료코드 0 / 1
  4) digest_build.py --work .work/evening --out <폴더> [--data data] [--blank]
       읽기  scored.json · collect_status.json · <data>/digest_state.json · digest_index.json · digest_overrides.json(없으면 빈 것)
       쓰기  <out>/digest.json · <out>/digest/<판 날짜>.json · <out>/digest_index.json · <out>/digest_state.json · <out>/digest_status.json
       --blank   내리기 전용: scored 없이 blank_digest(status withdrawn)와 상태만 쓴다
       종료코드  0 판을 냄 / 2 판은 냈지만 실행을 실패로 끝내야 함(수집 부족, 꼭 볼 것 0건이 3판 연속)
                / 3 판을 내지 않고 digest_status.json만 씀(verdict broken — 형식이 바뀐 것으로 본다) / 1 실패(아무것도 쓰지 않음)
  5) digest_check.py --public <폴더> [--raw .work/evening] [--sources data/sources.json]
       읽기  <public>의 JSON 전부(PUBLIC_FILES + digest/*.json), --raw가 있으면 원문      쓰기  없음
       검사  validator_for(이름)(자료) + closed_violations() + 크기. --raw가 있으면 링크의 글이 실제로 수집됐는지, 심은 글자가 없는지
       종료코드  0 통과 / 1 위반(경로와 사유만 찍는다)
  6) digest_publish.py --from <폴더> --data data        (게시 잡 — 원문이 없는 곳에서 돈다)
       PUBLIC_FILES와 digest/<날짜>.json만 옮긴다. 옮기기 전에 다시 검사하고, keep_days가 지난 digest/ 파일을 지운다.  종료코드 0 / 1
  22:41 감시 실행은 evening_run.py watch — main의 data/digest_status.json이 오늘 판을 낸 상태인지 보고, 배포된 페이지의 같은 파일과
  edition · checked_at · published를 견준다(수집하지 않는다).

판 날짜와 수집 창 (collect_window 하나를 모두가 쓴다)
  판 날짜 = (실행 시각 − 6시간)의 KST 날짜. 창 = 직전 판의 read_to(없으면 window.to) ~ 지금, 최대 96시간, 상태가 없으면 24시간.
  read_to = '여기까지 제대로 읽었다' — 정상 판은 window.to, 수집 부족 판은 그 앞 판의 값 그대로(못 읽은 글을 다음 판이 다시 읽는다).
  같은 판 날짜에 다시 돌면 첫 실행의 window.from에서 다시 계산한다(멱등) — 상태 파일은 이 판(edition)과 그 직전 판(base)을
  따로 들고 있어서, 다시 돌아도 '어제'와 채널별 마지막 글 번호는 base에서 읽는다(state_base · next_state).

자료 형태 (칸 이름은 아래 _obj(...) 정의가 기준이다. 정해지지 않은 칸이 있으면 검증에서 떨어진다. 시각은 모두 ISO +09:00)
  <work> 안에서만
    posts.json           {schema, edition, window{from,to}, collected_at, posts[post]} — 창 안(from < at ≤ to)의 글, (at, ch, id) 순
      post               {ch, id, at, text, links[], fwd{ch,id}|null, card{title,site,url}|null, reply, media, via(page·search), pic?}
                         fwd의 ch·id는 전달 원글의 주소가 있을 때만(없으면 null — 원글 이름은 남기지 않는다)
    collect_status.json  {…, window_kind(first·next·rerun), capped, replay, requests, elapsed_s, verdict(ok·short·broken),
                          channels[{ch, group, role, ok, code, pages, posts, with_text, in_window, last_post, last_at, title_sha,
                          fail_streak}]} — 요청한 채널(off 제외) 전부. posts = 쪽에서 읽은 글, with_text = 그중 본문이 있는 글
    pages/manifest.json  {schema, now, pages[{ch, n, kind(page·search·more), file "<handle>-<n>.html", ok, code}]}
    clusters.json        {…, stats{posts, kept, dropped{empty,short,ad,coin,filing}}, clusters[cluster]} — 버리지 않은 글은 모두
                         한 묶음에 든다(혼자인 묶음 포함), 한 글은 한 묶음에만
      cluster            {seed{ch,id}, key, keys[], first_at, last_at, cell{factor,region}|null, terms[{term,n_ch}],
                          results[{result,n_ch}], nums[{term,result|null,v,n_ch≥2}], members[글]}
        글(원문 없음)     {ch, id, at, group, role, fwd, terms[], lead[], results[], nums[], lead_nums[], row?, size?, pic?, head?}
                         lead는 첫 80자 안의 것, head는 첫 두 줄 안의 것. row{term, v|null}|null = 혼자 쓴 글이 줄이 될 때의 짝
                         (첫머리의 첫 숫자와 그 앞의 가까운 A·B급 낱말. 짝이 없으면 첫 두 줄의 대표 낱말만 — 아래 '더 자세히')
        열쇠             "<f·u·t·n·k·g>:<해시 12자리>" = key_of(종류, 재료). 혼자인 묶음은 g 하나. key = primary_key(keys)
    scored.json          {…, stats, head, tomorrow[], clusters[cluster + {coverage{bond,analyst,personal,wire}, score{total,C,X,K,
                          E,M,Y,P,L}, gate{pass, fails[sources·grade·score·group]}, why[고정 문구], pick(must·rest·none), rank}]}
                         P는 감점의 크기(0 이상)이고 total = C+X+K+E+M+Y−P(+L). 1단계에서 Y = 0, L = null
  공개 (data/ 아래)
    digest.json · digest/<날짜>.json — validate_digest(판, sources)
      {schema, date, mode "rules", status(ok·short·withdrawn), window, collected_at, funnel{posts,clusters,candidates,must,truncated},
       sources{channels_ok,channels_total}, head{kr10,kr3,us10 → {value,chg_bp,asof,fits}|null, dir, curve, basis, top_terms[]},
       notes[고정 문구], must[≤3], rest[{cell(8칸 이름), items[]}], wire, solo, context[{ch,at,url}], tomorrow[], youtube{enabled false}}
      must 항목   {id, key, cell{factor,region}, terms[1~4], nums[≤3], score, why[≤4], coverage, links[1~6 {ch,url,at,fwd}]}
      rest 항목   {id, key, cell, terms[≤3], nums[≤1], s(총점), coverage, links[1~2]} — 모두 합쳐 30줄까지
      wire · solo {channels[{ch, read, joined, hit}], rows[{ch, term, result|null, v|null, at, url}]} — 줄은 채널당 5개까지
      tomorrow    [{date, time|null, term, detail[만기 낱말·숫자], tier(A·B), src(korea·calendar)}]
      id = item_id(판 날짜, 씨앗 글) — 순위가 아니라 seed_of(가장 이른 원천 글). 링크는 pick_links가 고른다
      칸의 뜻     status   short = 수집 부족(must를 비운다) · withdrawn = 내림(모든 절이 빈다, blank_digest)
                  funnel   posts 창 안에서 읽은 글 · clusters 원천 글이 든 묶음 · candidates 게이트를 모두 통과한 묶음 ·
                           must 실린 수 · truncated 나머지 표에서 30줄 상한으로 잘린 줄
                  head     fits = 자료일의 마감이 창 안(rate_fits). kr10이 안 맞으면 dir을, kr10·kr3 중 하나라도 안 맞으면 curve를
                           비운다. basis는 kr10 기준(당일 종가·전일 종가). top_terms = 가장 많이 다뤄진 주제(원인이 아니다)
                  coverage 그 묶음에서 점수에 센 채널 수(그룹별) + 속보형 채널 수
                  wire·solo read 창 안에서 읽은 글(속보형은 검색에 걸린 글) · joined 다른 채널과 묶인 글 · hit 혼자 쓴 글 가운데
                           줄이 될 수 있었던 글(줄은 그중 5개까지). 줄의 숫자는 첫머리의 첫 숫자가 바로 곁의 A·B급 낱말과 짝지어질
                           때만 붙는다 — 한 곳만 쓴 숫자다. solo는 개인 원천 채널, wire는 속보형 채널
                  at       글을 올린 시각(ISO). 화면이 보기 좋게 줄인다
    digest_index.json   {schema, updated_at, latest, editions[{date,status,must,rest,posts,channels_ok,channels_total,collected_at}]} 최신순
    digest_state.json   {schema, edition, base} — 판 기록 {date, window, collected_at, empty_streak, must[{id,keys[],c}],
                         channels{<handle>: {last_post,last_at,fail_streak}}, read_to?} (숫자·해시·시각만)
    digest_status.json  {schema, checked_at, ok, reason, edition, published, last_success{date,at}, empty_streak, counts{…},
                         channels[{ch,ok,code,posts,with_text,in_window,fail_streak}], expect{run_kst,late_kst}}
    sources.json        {schema, updated, groups[{id,label}], roles[{id,label}], channels[{handle,label,group,role,title_sha}], youtube[]}
    calendar.json       {schema, updated, events[{date, term(사전 낱말), tier(A·B), time?(HH:MM KST), detail?[]}]}
    digest_overrides.json {schema, withdraw, hide_ids[], hide_channels[]} — 화면(site/evening.js)도 읽는다: 든 것을 감추고,
                         withdraw면 판 전체를 감춘다(조립은 다음 실행부터 빼고 만든다 — 숨긴 자리를 다른 묶음으로 채우지 않는다)

더 자세히 — 2026-10-08 저녁에 더한 칸 (읽을거리를 늘리되 채널 글의 글자는 여전히 0자다)
  schema는 1 그대로이고 새 칸은 모두 '없어도 되는 칸'이다 — 10-08에 이미 나간 판(digest.json · digest/2026-10-08.json)과 상태 기록에는
  이 칸들이 없다. 화면은 칸이 있을 때만 그린다. 새 문자열은 전부 닫힌 값이다: 사전 낱말 · 길이 구간 이름(R.SIZES) · 시각 · 날짜 ·
  우리가 쓴 풀이(R.GLOSS의 것과 글자까지 같을 때만) · 공식 주소(R.OFFICIAL_URLS의 것과 글자까지 같을 때만).
  낱말 목록은 글에 나온 순서로 나가지 않는다 — 곳 수 ↓ → 등급 → (넓은 낱말 R.WIDE는 뒤) → 가나다(R.by_count), 곳 수가 없는 목록은
  등급 → (넓은 낱말은 뒤) → 가나다(R.by_grade). 이 순서가 아니면 형식 검사에서 떨어진다(낱말을 늘어놓은 것이 글의 요약 문장처럼
  읽히지 않게). 좁은 낱말이 곁에 있는 넓은 낱말('연준 의사록' 곁의 '연준', 'AI Capex' 곁의 'AI')은 싣지 않는다(R.narrow).
    must · rest 항목
      words  [{term, n_ch}]   함께 나온 낱말 — 그 묶음의 보이는 원천 글 가운데 '직접 쓴' 글 전체(첫머리만이 아니다)에서 걸린 사전
                              낱말과 그 낱말을 쓴 원천 채널 수. 전달 글은 세지 않는다 — 전달 글뿐인 묶음에는 칸이 없다.
                              여러 채널이 든 묶음은 두 곳 이상이 쓴 낱말만, 한 채널뿐인 묶음은 그 글의 낱말(모두 1곳).
                              항목의 낱말(terms)은 되풀이하지 않는다 — terms와 겹치면 형식 검사에서 떨어진다. must 16개 · rest 4개까지.
                              비면 칸이 없다.  예(terms가 연준 의사록 · 금리일 때): [{"term":"인플레","n_ch":4},{"term":"관세","n_ch":3}]
      span   {from, to, posts} 그 묶음의 보이는 글 가운데 첫 글·마지막 글의 시각(ISO)과 글 수(속보형·주제 한정 채널의 글, 전달 글도
                              센다 — 그래서 coverage의 채널들이 '쓴' 시각 범위가 아니라 '묶인 글'의 범위다. 화면도 그렇게 적는다)
      prev   {date, bond, analyst, personal}  직전 판(date)에 같은 대표 낱말(terms[0])을 단 항목이 있었으면 그때 센 채널 수.
                              대표 낱말이 A·B급일 때만 붙는다(흔한 C급 낱말은 날마다 다른 묶음의 대표가 된다). 같은 낱말일 뿐
                              같은 묶음이라는 뜻이 아니다 — 화면은 "대표 낱말이 직전 판에도 있었습니다"라고만 쓴다
      links[] 에 더해   more [낱말]  이 글에만 더 있는 낱말 — 그 링크의 글에서 걸렸지만 항목의 terms · words에 없고 두 곳 이상이
                              함께 쓴 낱말도 아닌 것(must 4개 · rest 2개까지, 등급 → 가나다). 비면 칸이 없다
                        n_terms 정수  그 글에서 걸린 사전 낱말 수(TH member_terms_max까지 센다) — 어느 글이 넓게 다뤘는지
                        size  "짧음"·"보통"·"김"  그 글의 길이 구간(TH size_short자 미만 · 그 사이 · size_long자 이상)
                        pic   true    그림·영상·파일이 붙은 글일 때만 싣는다(없으면 붙은 것이 없거나 모르는 것)
    wire · solo의 rows   v가 null일 수 있다(숫자 없는 줄). 줄이 되는 글 = 혼자 쓴 글 가운데 첫 두 줄(TH row_head_chars자까지)에
                        A·B급 낱말이 있는 글, 또는 첫 두 줄에 C급 낱말뿐이어도 그 글의 낱말이 둘 이상인 글.
                        숫자(v)는 예전 규칙대로 첫머리의 첫 숫자가 바로 곁의 A·B급 낱말과 짝지어질 때만이고, 그때 term은 그 짝이다.
                        숫자 없는 줄의 term = 그 글의 낱말 가운데 등급이 가장 높은 것(R.by_grade의 맨 앞 — 첫 두 줄의 낱말이 흔한
                        C급이어도 더 높은 등급이 덧낱말 뒤에 묻히지 않게. 글의 주제라는 뜻은 아니다). result는 v가 있을 때만 싣는다.
                        채널당 5줄은 A급 → B급 → C급, 숫자 있는 줄, 이른 글 순으로 고르고 시각순으로 싣는다.
                        + more [낱말 2개까지] · n_terms · size · pic (links와 같은 뜻)
    gloss  [{term, text, url|null}]  이 판에 나온 사전 낱말(S.shown_terms) 가운데 풀이가 있는 것 — 한 번씩, 사전에 실린 순서로.
                        text = 우리가 쓴 한 줄 풀이(60자 안쪽), url = 공공 기관의 쪽(없으면 null — digest_gloss.py 머리말).
                        조립은 R.glosses(S.shown_terms(판))을 싣고, 판이 크기 상한에 걸리면 꼭 볼 것·머리 줄·일정의 낱말 것만 남기거나
                        비운다. 검사는 풀이마다 그 낱말의 것(R.gloss_of)과 글자까지 같은지 · 겹치지 않는지 · 순서 · 그 낱말이 이 판에
                        나왔는지를 본다('빠짐없이'는 묻지 않는다 — 크기 때문에 덜어 낸 판이 떨어지지 않게)
    notes에 더해        "크기 상한에 맞추려고 낱말 풀이나 단독 줄을 줄였습니다"(note_slim) — 풀이·단독 줄을 덜어 낸 판에 붙는다
    digest_state.json의 판 기록   topics [{key, bond, analyst, personal}] — 이 판 항목들의 A·B급 대표 낱말마다 낱말 id
                        (key_of("k", "w|낱말")의 해시)와 그때 센 채널 수. 다음 판의 prev가 이것을 읽는다(낱말 글자는 두지 않는다 —
                        사전을 고쳐도 상태가 안 깨진다)
  <work> 안: post에 pic(그림·영상·파일이 붙음 — 본문이 있어도 참)이 붙고, 묶음의 글에 size · pic · head(첫 두 줄 안의 낱말)가 붙는다.
  글의 terms는 TH member_terms_max개까지(자리순), row의 v는 null일 수 있다.
  싣지 않기로 한 것: '짝 없이 두 곳 이상이 똑같이 쓴 숫자' 칸 — 10-08 저장분에서 원천 2곳 이상인 묶음 3개에 1개뿐이었고(작은 % 하나),
  무엇의 숫자인지 말할 수 없어 읽는 사람이 뜻을 지어내게 된다. 숫자 칸(nums)은 낱말과 짝지어진 것만 싣는 그대로다.

AI 요약 층 — 2026-10-09 (규칙판 위에 얹는 한두 문장. 규칙판의 계약과 파일은 하나도 바뀌지 않는다)
  규칙판은 지금처럼 Actions가 낸다. 요약은 이 PC에서만 만들어(evening_llm.py) data/digest_picks.json 하나로 올린다 — PC가 꺼졌거나
  로그인이 만료됐거나 문장이 검사에 걸린 날은 문장 없이 규칙판만 나간다. 이 파일은 PUBLIC_FILES가 아니다(Actions가 쓰지 않고, 아티팩트
  폴더에 있으면 계약에 없는 파일이다). 형태 · 검증 · 문장 검사는 digest_picks.py에 있다(validate_picks · fact_code · attach).
  위 '가장 중요한 선'이 여기서 달라지는 곳은 fact 한 칸뿐이다: 닫힌 값이 아니라 모델이 자기 말로 쓴 문장이고, 그래서 문장마다
  꼴 · 금지 낱말 · 베낌 · 숫자 대조 · 낱말 · 이름 검사를 모두 통과해야 실린다. 원문과 버린 문장은 어디에도 쓰지 않는다(개수만).
  켜는 스위치는 규칙판과 같은 저장소 변수 EVENING_ENABLED다 — 꺼져 있으면 PC도 규칙판 실행을 시작하지 않고 채널을 읽지도 모델을 부르지도
  않으며, 올라가 있는 문장은 빈 층으로 바꾼다. 올라간 파일을 CI가 다시 볼 때는 형식 · 다시 쓴 바이트만 본다(validate_picks plain=False):
  문장 규칙을 조이거나 채널을 끈 뒤에 요약 층이 규칙판의 문이 되지 않게 — 그런 문장은 화면이 다시 가리고 다음 PC 실행이 다시 만든다.
    data/digest_picks.json   가장 최근 한 판의 것만 둔다(통째로 덮어쓴다). 판을 내리면(digest_build --blank) 빈 것으로 바뀐다
      {schema 1, date(판 날짜), made_at(ISO), mode "ai", model(모델 이름 | null), basis(무엇을 물었는가의 지문 — 해시 16자리),
       items[≤ TH llm_items_max {key, id, src, fact}], dropped{shape, banned, copy, number, term, name, none → 개수}}
      key    그 판 항목의 key(묶음의 대표 열쇠) 그대로          id   만들 때 그 항목의 id(참고용 — 잇는 데 쓰지 않는다)
      src    [[채널, 글 번호], …] 1~TH llm_posts_max개 — 모델에게 읽힌 글. 그 항목 links 가운데 채권 · 애널 원천 채널의 전달 아닌 글만
             (개인 · 속보형 · 전달 글은 읽히지 않는다), 판의 links 순서
      fact   한국어 평서문 1~2문장, TH fact_chars자 이하. 검사를 통과한 것만 — 통과하지 못한 항목은 items에 없고 dropped에 개수만
      dropped  문장이 빠진 사유별 개수(꼴 · 금지 낱말 · 베낌 · 숫자 · 낱말 · 이름 · 모델이 쓰지 않음). 문장이 하나도 안 남아도 파일은 쓴다
               (items가 빈다 — 전날 문장이 남지 않게)
    화면이 문장을 붙이는 규칙 (digest_picks.attach가 같은 규칙의 파이썬 판이다 — 하나라도 어긋나면 그 문장은 붙이지 않는다)
      1) 파일이 형식에 맞고(schema 1 · mode "ai") 그 date가 지금 보는 판의 date와 같다. 지난 판 화면에는 붙이지 않는다
      2) 판이 내린 판(status withdrawn)이 아니고, 숨김(digest_overrides)에 걸린 항목이 아니다
      3) 항목의 key가 같다 — id로 잇지 않는다(씨앗 글로 만든 값이라 같은 판을 다시 계산하면 달라질 수 있다)
      4) src의 글이 모두 그 항목 links에 있다(https://t.me/<채널>/<글 번호>가 links[].url에 있다). 다시 계산한 판에서 글이 빠졌으면 안 붙는다
      5) fact는 글자로만 그린다(텍스트 노드). 길이 · 줄바꿈 · 꺾쇠 · 주소 꼴을 화면도 한 번 더 본다 — 'AI가 쓴 요약'이라는 표시와 함께
      화면(site/evening.js의 picksOf · aiOf)은 attach보다 좁게 본다 — 닫는 쪽으로만 다르다: 4)의 링크는 화면이 실제로 건 링크(목록에 있고
      숨기지 않은 채널)이고 채권 · 애널 원천 채널의 전달 아닌 글이어야 한다. 출처 목록을 못 읽었으면 붙이지 않는다. key가 겹친 문장은 둘 다,
      항목이 llm_items_max개를 넘는 파일은 통째로 뺀다. 열어 둔 화면이 요약 층을 다시 읽지 못하면 가진 것을 두지 않고 비운다
"""
import datetime
import re

import digest_rules as R
from digest_base import (     # 밑바탕(digest_base.py)의 것도 이 모듈에서 그대로 꺼내 쓴다 — 여기서 안 쓰는 이름도 일부러 들여온다
    SCHEMA, TH, KST, REPO, DATA, WORK, HANDLE_RE, URL_RE, ID_RE, KEY_KINDS, KEY_RE, SHA_RE, ISO_RE, DATE_RE, HHMM_RE, PAGE_FILE_RE,
    MAX_POST, MAX_TEXT, MAX_URL, FIELDS, WORDS, iso, parse_iso, edition_date, collect_window, state_base, next_state, in_window,
    rate_fits, post_url, item_id, key_of, topic_key, primary_key, title_sha, page_title, seed_of, pick_links, coverage_verdict, is_closed,
    closed_violations, dump, read_json, write_json, report, run_cli,
    _fail, _obj, _arr, _map, _enum, _re, _int, _num, _is, _null, _bool, _text, _iso, _date, _phrase, _detail, _label, _unique)

PUBLIC_FILES = ("digest.json", "digest_index.json", "digest_state.json", "digest_status.json")    # Actions가 쓴다(+ digest/<날짜>.json)
HUMAN_FILES = ("sources.json", "calendar.json", "digest_overrides.json")                          # 사람이 쓴다
STATUSES = ("ok", "short", "withdrawn")                # 판의 상태: 정상 · 수집 부족(꼭 볼 것을 비움) · 내림
VERDICTS = ("ok", "short", "broken")                   # 수집 판정: broken = 본문 비율이 절반 아래(판을 내지 않는다)
REASONS = ("ok", "short", "broken", "empty_streak", "withdrawn", "error")
CH_CODES = ("ok", "fetch", "no_preview", "empty", "title", "rewind", "budget")
#           읽음 · 수신 실패 · 미리보기 주소가 아님 · 글을 못 읽음 · 제목 해시가 다름 · 글 번호·시각이 거꾸로 · 요청 예산 초과
GATE_CODES = ("sources", "grade", "score", "group")    # 원천 2곳 미만 · A·B급 낱말 없음 · S 미달 · 채권·애널 없음
PICKS = ("must", "rest", "none")
# 쌓여 있는 기록(목차의 줄 · 상태의 꼭 볼 것)의 상한 — TH가 아니라 넉넉한 고정값이다. 한도 숫자(must_max · rest_max · c_cap)를
# 낮춘 날 지난 기록이 형식 검사에 걸려 실행이 날마다 멈추지 않게
KEPT_MUST, KEPT_REST, KEPT_C = 9, 300, 99

# ---------- 형태 ----------

_one = _is(SCHEMA)
_handle = _re(HANDLE_RE, "채널 이름 꼴이 아님")
_postid = _int(1, MAX_POST)
_url = _re(URL_RE, "t.me 글 주소 꼴이 아님")
_itemid = _re(ID_RE, "항목 id 꼴이 아님")
_key = _re(KEY_RE, "열쇠 꼴이 아님")
_sha = _re(SHA_RE, "제목 해시 꼴이 아님")
_hhmm = _re(HHMM_RE, "시각 꼴(HH:MM)이 아님")
_term, _result = _enum(*R.TERMS), _enum(*R.RESULT_WORDS)
_numv = _re(R.NUM_OUT_RE, "숫자+단위 꼴이 아님")
_group, _role, _tier = _enum(*R.GROUPS), _enum(*R.ROLES), _enum("A", "B")
_count = _int(0, 1_000_000)
_streak = _int(0, 9_999)
_window = _obj({"from": _iso, "to": _iso})
_DOC = {"schema": _one, "edition": _date, "window": _window, "collected_at": _iso}

_post = _obj({"ch": _handle, "id": _postid, "at": _iso, "text": _text(MAX_TEXT), "links": _arr(_text(MAX_URL), 50),
              "fwd": _null(_obj({"ch": _null(_handle), "id": _null(_postid)})),
              "card": _null(_obj({"title": _text(500), "site": _text(200), "url": _text(MAX_URL)})),
              "reply": _bool, "media": _bool, "via": _enum("page", "search")}, {"pic": _bool})
_posts_doc = _obj({**_DOC, "posts": _arr(_post, 5_000)})
_chan = {"ch": _handle, "ok": _bool, "code": _enum(*CH_CODES), "posts": _count, "with_text": _count, "in_window": _count,
         "fail_streak": _streak}
_collect = _obj({**_DOC, "window_kind": _enum("first", "next", "rerun"), "capped": _bool, "replay": _bool,
                 "requests": _int(0, 1_000), "elapsed_s": _num(0, 100_000), "verdict": _enum(*VERDICTS),
                 "channels": _arr(_obj({**_chan, "group": _group, "role": _role, "pages": _int(0, 9), "last_post": _null(_postid),
                                        "last_at": _null(_iso), "title_sha": _null(_sha)}), 100, 1)})
_manifest = _obj({"schema": _one, "now": _iso, "pages": _arr(_obj({
    "ch": _handle, "n": _int(1, 9), "kind": _enum("page", "search", "more"), "file": _re(PAGE_FILE_RE, "쪽 파일 이름 꼴이 아님"),
    "ok": _bool, "code": _enum(*CH_CODES)}), 300)})

_cell = _obj({"factor": _enum(*R.FACTORS), "region": _enum(*R.REGIONS)})
_numrow = _obj({"term": _term, "result": _null(_result), "v": _numv, "n_ch": _int(2, 99)})
_size = _enum(*R.SIZES)
_mention = _obj({"ch": _handle, "id": _postid, "at": _iso, "group": _group, "role": _role, "fwd": _bool,
                 "terms": _arr(_term, TH["member_terms_max"]), "lead": _arr(_term, 12), "results": _arr(_result, len(R.RESULT_WORDS)),
                 "nums": _arr(_numv, 12), "lead_nums": _arr(_numv, 12)},
                {"row": _null(_obj({"term": _term, "v": _null(_numv)})), "size": _size, "pic": _bool,
                 "head": _arr(_term, TH["member_terms_max"])})
_CLUSTER = {"seed": _obj({"ch": _handle, "id": _postid}), "key": _key, "keys": _arr(_key, 60, 1), "first_at": _iso, "last_at": _iso,
            "cell": _null(_cell), "terms": _arr(_obj({"term": _term, "n_ch": _int(1, 99)}), 12),
            "results": _arr(_obj({"result": _result, "n_ch": _int(1, 99)}), len(R.RESULT_WORDS)),
            "nums": _arr(_numrow, TH["nums_max"]), "members": _arr(_mention, TH["cluster_max_posts"], 1)}
_cluster = _obj(_CLUSTER)
_stats = _obj({"posts": _count, "kept": _count, "dropped": _obj({c: _count for c in R.DROP_CODES})})
_clusters_doc = _obj({**_DOC, "stats": _stats, "clusters": _arr(_cluster, 5_000)})

_score = _obj({"total": _num(-10, TH["s_max"]), "C": _num(0, TH["c_cap"]), "X": _num(0, TH["x_cap"]), "K": _num(0, TH["k_cap"]),
               "E": _num(0, TH["e_cap"]), "M": _num(0, TH["m_cap"]), "Y": _num(0, TH["y_cap"]), "P": _num(0, TH["p_cap"]),
               "L": _null(_num(TH["l_min"], TH["l_max"]))})
_coverage = _obj({g: _int(0, 99) for g in (*R.GROUPS, "wire")})
_rate = _null(_obj({"value": _num(TH["rate_min"], TH["rate_max"]), "chg_bp": _null(_num(-TH["chg_bp_max"], TH["chg_bp_max"])),
                    "asof": _date, "fits": _bool}))
_head = _obj({"kr10": _rate, "kr3": _rate, "us10": _rate, "dir": _null(_enum(*R.DIRS)), "curve": _null(_enum(*R.CURVES)),
              "basis": _null(_enum(*R.BASES)), "top_terms": _arr(_term, TH["top_terms_max"])})
_event = {"date": _date, "term": _term, "tier": _tier}
_tomorrow = _arr(_obj({**_event, "time": _null(_hhmm), "detail": _arr(_detail, 3), "src": _enum("korea", "calendar")}),
                 TH["tomorrow_max"])
_scored = _obj({**_CLUSTER, "coverage": _coverage, "score": _score, "why": _arr(_phrase, TH["why_max"]), "pick": _enum(*PICKS),
                "gate": _obj({"pass": _bool, "fails": _arr(_enum(*GATE_CODES), len(GATE_CODES))}),
                "rank": _null(_int(1, TH["must_max"]))})
_scored_doc = _obj({**_DOC, "stats": _stats, "head": _head, "tomorrow": _tomorrow, "clusters": _arr(_scored, 5_000)})

_LINK = {"ch": _handle, "url": _url, "at": _iso, "fwd": _bool}
_ITEM = {"id": _itemid, "key": _key, "cell": _cell, "coverage": _coverage}


def _link_more(n):
    """더 자세히(없어도 되는 칸) — 링크·줄에 붙는 덧낱말 n개까지 · 길이 구간 · 붙은 것 · 그 글의 사전 낱말 수."""
    return {"more": _arr(_term, n, 1), "size": _size, "pic": _is(True), "n_terms": _int(0, TH["member_terms_max"])}


def _item_more(n):
    """더 자세히(없어도 되는 칸) — 항목에 붙는 함께 나온 낱말 n개까지 · 첫 글~마지막 글 · 직전 판의 채널 수."""
    return {"words": _arr(_obj({"term": _term, "n_ch": _int(1, 99)}), n, 1),
            "span": _obj({"from": _iso, "to": _iso, "posts": _int(1, TH["cluster_max_posts"])}),
            "prev": _obj({"date": _date, **{g: _int(0, 99) for g in R.GROUPS}})}


_must = _obj({**_ITEM, "terms": _arr(_term, TH["terms_max"], 1), "nums": _arr(_numrow, TH["nums_max"]), "score": _score,
              "why": _arr(_phrase, TH["why_max"]), "links": _arr(_obj(_LINK, _link_more(TH["more_max"])), TH["links_max"], 1)},
             _item_more(TH["words_max"]))
_rest_item = _obj({**_ITEM, "terms": _arr(_term, TH["rest_terms_max"]), "nums": _arr(_numrow, TH["rest_nums_max"]),
                   "s": _num(-10, TH["s_max"]), "links": _arr(_obj(_LINK, _link_more(TH["rest_more_max"])), TH["rest_links_max"], 1)},
                  _item_more(TH["rest_words_max"]))
_side = _obj({"channels": _arr(_obj({"ch": _handle, "read": _count, "joined": _count, "hit": _count}), 50),
              "rows": _arr(_obj({"ch": _handle, "term": _term, "result": _null(_result), "v": _null(_numv), "at": _iso, "url": _url},
                                _link_more(TH["row_more_max"])), 250)})


def _gloss_text(v, path):
    if not (isinstance(v, str) and v in R.GLOSS_TEXTS):
        _fail(path, "규칙에 적힌 풀이가 아님")


def _gloss_url(v, path):
    if not (isinstance(v, str) and v in R.OFFICIAL_URLS):
        _fail(path, "규칙에 적힌 공식 주소가 아님")


_gloss = _arr(_obj({"term": _term, "text": _gloss_text, "url": _null(_gloss_url)}), len(R.GLOSS))
_digest = _obj({
    "schema": _one, "date": _date, "mode": _enum("rules"), "status": _enum(*STATUSES), "window": _window, "collected_at": _iso,
    "funnel": _obj({k: _count for k in ("posts", "clusters", "candidates", "must", "truncated")}),
    "sources": _obj({"channels_ok": _int(0, 100), "channels_total": _int(0, 100)}),
    "head": _head, "notes": _arr(_phrase, 7), "must": _arr(_must, TH["must_max"]),
    "rest": _arr(_obj({"cell": _enum(*R.CELLS), "items": _arr(_rest_item, TH["rest_max"], 1)}), len(R.CELLS)),
    "wire": _side, "solo": _side, "context": _arr(_obj({"ch": _handle, "at": _iso, "url": _url}), TH["context_max"]),
    "tomorrow": _tomorrow, "youtube": _obj({"enabled": _is(False), "rows": _arr(_bool, 0)})}, {"gloss": _gloss})

_index = _obj({"schema": _one, "updated_at": _iso, "latest": _null(_date), "editions": _arr(_obj({
    "date": _date, "status": _enum(*STATUSES), "must": _int(0, KEPT_MUST), "rest": _int(0, KEPT_REST), "posts": _count,
    "channels_ok": _int(0, 100), "channels_total": _int(0, 100), "collected_at": _iso}), 60)})
_snap = _obj({"date": _date, "window": _window, "collected_at": _iso, "empty_streak": _streak,
              "must": _arr(_obj({"id": _itemid, "keys": _arr(_key, 60, 1), "c": _num(0, KEPT_C)}), KEPT_MUST),
              "channels": _map(_obj({"last_post": _null(_postid), "last_at": _null(_iso), "fail_streak": _streak}), 100)},
             {"read_to": _iso, "topics": _arr(_obj({"key": _key, **{g: _int(0, 99) for g in R.GROUPS}}), TH["topics_max"])})
_state = _obj({"schema": _one, "edition": _null(_snap), "base": _null(_snap)})
_status = _obj({"schema": _one, "checked_at": _iso, "ok": _bool, "reason": _enum(*REASONS), "edition": _null(_date), "published": _bool,
                "last_success": _null(_obj({"date": _date, "at": _iso})), "empty_streak": _streak,
                "counts": _obj({k: _count for k in ("channels_ok", "channels_total", "bond_ok", "bond_total", "posts", "with_text")}),
                "channels": _arr(_obj(_chan), 100), "expect": _obj({"run_kst": _hhmm, "late_kst": _hhmm})})
_sources = _obj({"schema": _one, "updated": _date, "groups": _arr(_obj({"id": _group, "label": _label}), 3, 3),
                 "roles": _arr(_obj({"id": _role, "label": _label}), 5, 5), "youtube": _arr(_bool, 0),
                 "channels": _arr(_obj({"handle": _handle, "label": _label, "group": _group, "role": _role,
                                        "title_sha": _null(_sha)}), 100, 1)})
_calendar = _obj({"schema": _one, "updated": _date,
                  "events": _arr(_obj(_event, {"time": _null(_hhmm), "detail": _arr(_detail, 3)}), 500)})
_overrides = _obj({"schema": _one, "withdraw": _bool, "hide_ids": _arr(_itemid, 300), "hide_channels": _arr(_handle, 100)})

# ---------- 빈 판 · 채널 목록 ----------


def blank_digest(now):
    """빈 판(status withdrawn) — 내리기 전용 실행이 쓴다. 창은 지금 한 점이고 모든 절이 비어 있다."""
    at = iso(now)
    return {"schema": SCHEMA, "date": edition_date(now), "mode": "rules", "status": "withdrawn", "window": {"from": at, "to": at},
            "collected_at": at, "funnel": {"posts": 0, "clusters": 0, "candidates": 0, "must": 0, "truncated": 0},
            "sources": {"channels_ok": 0, "channels_total": 0},
            "head": {"kr10": None, "kr3": None, "us10": None, "dir": None, "curve": None, "basis": None, "top_terms": []},
            "notes": [R.phrase("note_withdrawn")], "must": [], "rest": [],
            "wire": {"channels": [], "rows": []}, "solo": {"channels": [], "rows": []}, "context": [], "tomorrow": [],
            "youtube": {"enabled": False, "rows": []}}


def shown_terms(d):
    """판에 나온 사전 낱말 전부 — 머리 줄의 주제 · 항목의 낱말과 함께 나온 낱말 · 링크별 덧낱말 · 숫자의 짝 · 단독 줄 · 일정.
    풀이 칸(gloss)은 이 낱말들로만 만든다."""
    out = set(d["head"]["top_terms"]) | {e["term"] for e in d["tomorrow"]}
    for x in d["must"] + [x for g in d["rest"] for x in g["items"]]:
        out.update(x["terms"], (n["term"] for n in x["nums"]), (w["term"] for w in x.get("words", ())))
        for ln in x["links"]:
            out.update(ln.get("more", ()))
    for side in ("wire", "solo"):
        for r in d[side]["rows"]:
            out.update((r["term"], *r.get("more", ())))
    return out


def handles_of(sources, roles=None):
    """sources.json → 채널 이름 집합. roles를 주면 그 역할만, 안 주면 off를 뺀 전부(요청하는 채널)."""
    roles = [r for r in R.ROLES if r != "off"] if roles is None else roles
    return {c["handle"] for c in sources["channels"] if c["role"] in roles}


# ---------- 검증 (틀리면 ValueError — 어느 칸이 왜. 값은 싣지 않는다) ----------


def _span(doc, path, strict=True):
    """창과 수집 시각: from ≤ to ≤ collected_at, 길이는 상한(96시간 + 같은 판을 다시 도는 하루) 안."""
    a, b, c = (parse_iso(doc["window"]["from"]), parse_iso(doc["window"]["to"]), parse_iso(doc["collected_at"]))
    if not (a < b or (a == b and not strict)):
        _fail(f"{path}.window", "창의 시작이 끝보다 늦음")
    if b - a > datetime.timedelta(hours=TH["window_max_h"] + 24) or not b <= c <= b + datetime.timedelta(hours=6):
        _fail(f"{path}.window", "창이 너무 길거나 수집 시각이 창의 끝과 맞지 않음")
    if edition_date(b) != doc.get("edition", doc.get("date")):
        _fail(path, "판 날짜가 창의 끝(실행 시각)과 맞지 않음")
    return doc["window"]["from"], doc["window"]["to"]


def _inside(at, span, path):
    if not span[0] < at <= span[1]:
        _fail(path, "시각이 수집 창 밖")


def validate_post(p, path="post"):
    _post(p, path)
    return p


def validate_posts_doc(d):
    _posts_doc(d, "posts")
    span = _span(d, "posts")
    keys = [(p["at"], p["ch"], p["id"]) for p in d["posts"]]
    _unique([k[1:] for k in keys], "posts.posts", "글(채널·번호)")
    if keys != sorted(keys):
        _fail("posts.posts", "(시각, 채널, 번호) 순이 아님")
    for i, p in enumerate(d["posts"]):
        _inside(p["at"], span, f"posts.posts[{i}].at")
    return d


def validate_collect_status(d):
    _collect(d, "collect")
    _span(d, "collect")
    _unique([c["ch"] for c in d["channels"]], "collect.channels", "채널")
    for i, c in enumerate(d["channels"]):
        if c["role"] == "off" or c["ok"] != (c["code"] == "ok") or not c["in_window"] <= c["posts"] >= c["with_text"]:
            _fail(f"collect.channels[{i}]", "역할·코드·개수가 서로 맞지 않음")
    if d["verdict"] != coverage_verdict(d["channels"])["verdict"]:
        _fail("collect.verdict", "채널 숫자로 다시 낸 판정과 다름")
    return d


def validate_manifest(d):
    _manifest(d, "manifest")
    _unique([(p["ch"], p["n"]) for p in d["pages"]], "manifest.pages", "쪽")
    if any(p["file"] != f"{p['ch']}-{p['n']}.html" for p in d["pages"]):
        _fail("manifest.pages", "파일 이름이 <채널>-<쪽 번호>.html이 아님")
    return d


def validate_cluster(c, path="cluster", span=None):
    """묶음 하나. span(창의 from·to)을 주면 글의 시각이 창 안인지도 본다."""
    _cluster(c, path)
    return _check_cluster(c, path, span)


def _check_cluster(c, path, span):
    ms = c["members"]
    order = [(m["at"], m["ch"], m["id"]) for m in ms]
    _unique([k[1:] for k in order], f"{path}.members", "글(채널·번호)")
    if order != sorted(order) or (c["first_at"], c["last_at"]) != (order[0][0], order[-1][0]):
        _fail(f"{path}.members", "(시각, 채널, 번호) 순이 아니거나 first_at·last_at이 글과 다름")
    if c["seed"] != seed_of(ms) or c["key"] != primary_key(c["keys"]) or len(set(c["keys"])) != len(c["keys"]):
        _fail(path, "씨앗 글이나 대표 열쇠가 규칙(seed_of · primary_key)과 다름")
    chans = len({m["ch"] for m in ms})
    for i, m in enumerate(ms):
        if not set(m["lead"]) <= set(m["terms"]) or not set(m["lead_nums"]) <= set(m["nums"]):
            _fail(f"{path}.members[{i}]", "첫머리 낱말·숫자가 그 글의 낱말·숫자에 없음")
        head = m.get("head", m["lead"])
        if not set(m["lead"]) <= set(head) <= set(m["terms"]):
            _fail(f"{path}.members[{i}].head", "첫 두 줄의 낱말이 첫머리 낱말을 품지 않거나 그 글의 낱말에 없음")
        row = m.get("row")
        graded = row and (R.grade_of(row["term"]) in ("A", "B") or (row["v"] is None and len(m["terms"]) > 1))
        paired = row and (row["term"] in head if row["v"] is None else row["term"] in m["lead"] and row["v"] in m["lead_nums"])
        if row and not (graded and paired):
            _fail(f"{path}.members[{i}].row", "줄의 짝이 그 글 첫머리의 낱말·숫자가 아니거나 등급 규칙에 어긋남")
        if span:
            _inside(m["at"], span, f"{path}.members[{i}].at")
    if any(x["n_ch"] > chans for x in c["terms"] + c["results"] + c["nums"]):
        _fail(path, "n_ch가 묶음의 채널 수보다 큼")
    if (c["cell"] is None) != (not c["terms"]):
        _fail(f"{path}.cell", "낱말이 있으면 칸이 있어야 하고, 없으면 null")
    return c


def _check_clusters(d, path, each):
    """묶음 문서 공통: 창, 묶음마다 each, 한 글은 한 묶음에만, 글 수."""
    span = _span(d, path)
    for i, c in enumerate(d["clusters"]):
        each(c, f"{path}.clusters[{i}]", span)
    _unique([(m["ch"], m["id"]) for c in d["clusters"] for m in c["members"]], f"{path}.clusters", "글(한 글은 한 묶음에만)")
    if d["stats"]["kept"] != sum(len(c["members"]) for c in d["clusters"]) or \
            d["stats"]["posts"] != d["stats"]["kept"] + sum(d["stats"]["dropped"].values()):
        _fail(f"{path}.stats", "글 수(posts = kept + dropped, kept = 묶음에 든 글)가 맞지 않음")


def validate_clusters_doc(d):
    _clusters_doc(d, "clusters")
    _check_clusters(d, "clusters", _check_cluster)
    return d


def _check_score(s, path):
    total = s["C"] + s["X"] + s["K"] + s["E"] + s["M"] + s["Y"] - s["P"] + (s["L"] or 0)
    if abs(total - s["total"]) > 1e-6:
        _fail(f"{path}.total", "S = C + X + K + E + M + Y − P (+ L)과 다름")


def validate_scored(c, path="scored", span=None):
    """점수 붙은 묶음 하나."""
    _scored(c, path)
    return _check_scored(c, path, span)


def _check_scored(c, path, span):
    _check_cluster(c, path, span)
    _check_score(c["score"], f"{path}.score")
    if c["gate"]["pass"] != (not c["gate"]["fails"]) or (c["pick"] == "must") != (c["rank"] is not None):
        _fail(path, "게이트·고름·순위가 서로 맞지 않음")
    if c["pick"] == "must" and not (c["gate"]["pass"] and c["terms"]):
        _fail(path, "꼭 볼 것은 게이트를 통과하고 낱말이 있어야 함")
    return c


def validate_scored_doc(d):
    _scored_doc(d, "scored")
    _check_clusters(d, "scored", _check_scored)
    ranks = sorted(c["rank"] for c in d["clusters"] if c["rank"] is not None)
    if ranks != list(range(1, len(ranks) + 1)):
        _fail("scored.clusters", "꼭 볼 것의 순위가 1부터 차례로가 아님")
    _check_head(d["head"], "scored.head")
    return d


def _check_head(h, path):
    for k in ("kr10", "kr3", "us10"):
        if h[k] and not TH["rate_min"] < h[k]["value"] < TH["rate_max"]:
            _fail(f"{path}.{k}.value", "금리가 범위 밖")
    fits10, fits3 = bool(h["kr10"] and h["kr10"]["fits"]), bool(h["kr3"] and h["kr3"]["fits"])
    if (h["dir"] and not fits10) or (h["curve"] and not (fits10 and fits3)):
        _fail(path, "자료일이 창과 맞지 않으면 방향 칸을 비워야 함")
    if (h["basis"] is None) != (h["kr10"] is None) or (h["kr10"] and (h["basis"] == R.BASES[0]) != fits10):
        _fail(f"{path}.basis", "종가 기준 표시가 국고 10년의 자료일과 맞지 않음")
    _unique(h["top_terms"], f"{path}.top_terms", "낱말")


def _check_links(item, path, date, span, roles):
    if item["id"][:8] != date.replace("-", ""):
        _fail(f"{path}.id", "id의 날짜가 판 날짜와 다름")
    _unique([x["ch"] for x in item["links"]], f"{path}.links", "채널(한 채널에 링크 하나)")
    _unique(item["terms"], f"{path}.terms", "낱말")
    for i, x in enumerate(item["links"]):
        if URL_RE.match(x["url"]).group("ch") != x["ch"]:
            _fail(f"{path}.links[{i}]", "주소의 채널이 ch와 다름")
        _inside(x["at"], span, f"{path}.links[{i}].at")
    _check_more(item, path, date, span)
    if roles is not None:
        got = [roles.get(x["ch"]) for x in item["links"]]
        rank = [(x["fwd"], R.GROUP_ORDER.index(g[0])) for x, g in zip(item["links"], got) if g]
        if any(g is None or g[1] != "source" for g in got) or rank != sorted(rank) \
                or sum(g[0] == "personal" for g in got) > TH["links_personal_max"]:
            _fail(f"{path}.links", "링크 규칙(원천 채널만 · 전달 아닌 글 → 채권 → 애널 → 개인 · 개인 2개까지)에 어긋남")


def _check_more(item, path, date, span):
    """더 자세히 칸 — 낱말 목록의 순서(곳 수 ↓ → 등급 → 가나다, 글에 나온 순서가 아니다) · 함께 나온 낱말이 항목의 낱말을 되풀이하지
    않는가 · 덧낱말이 항목의 낱말과 겹치지 않는가 · 첫 글~마지막 글이 창 안이고 링크의 시각을 품는가 · 직전 판의 날짜가 이 판보다
    앞이고 대표 낱말이 A·B급인가."""
    words = item.get("words", [])
    counts = {w["term"]: w["n_ch"] for w in words}
    if [(w["term"], w["n_ch"]) for w in words] != R.by_count(counts) or len(counts) != len(words) or set(counts) & set(item["terms"]) \
            or (words and min(counts.values()) < 2 and max(counts.values()) > 1):
        _fail(f"{path}.words", "함께 나온 낱말의 순서(곳 수 → 등급 → 가나다)가 다르거나 겹치거나 항목의 낱말을 되풀이하거나 곳 수가 규칙과 다름")
    shown = set(item["terms"]) | set(counts)
    for i, x in enumerate(item["links"]):
        more = x.get("more", [])
        if more != R.by_grade(more) or shown & set(more):
            _fail(f"{path}.links[{i}].more", "덧낱말의 순서(등급 → 가나다)가 다르거나 항목의 낱말과 겹침")
        if x.get("n_terms", len(more)) < len(more):
            _fail(f"{path}.links[{i}].n_terms", "그 글의 낱말 수가 덧낱말보다 적음")
    sp = item.get("span")
    if sp:
        _inside(sp["from"], span, f"{path}.span.from")
        _inside(sp["to"], span, f"{path}.span.to")
        if sp["from"] > sp["to"] or any(not sp["from"] <= x["at"] <= sp["to"] for x in item["links"]) or sp["posts"] < len(item["links"]):
            _fail(f"{path}.span", "첫 글·마지막 글의 시각이 뒤집혔거나 링크의 글을 품지 않음")
    if item.get("prev") and not (item["terms"] and R.grade_of(item["terms"][0]) in ("A", "B") and item["prev"]["date"] < date):
        _fail(f"{path}.prev", "직전 판의 날짜가 이 판보다 앞이 아니거나 대표 낱말이 없거나 A·B급이 아님")


def _check_side(side, path, span, roles, want):
    names = [c["ch"] for c in side["channels"]]
    _unique(names, f"{path}.channels", "채널")
    if any(c["joined"] > c["read"] or c["hit"] > c["read"] for c in side["channels"]):
        _fail(f"{path}.channels", "겹친 글·맞은 글이 읽은 글보다 많음")
    for i, r in enumerate(side["rows"]):
        if r["ch"] not in names or URL_RE.match(r["url"]).group("ch") != r["ch"]:
            _fail(f"{path}.rows[{i}]", "줄의 채널이 channels에 없거나 주소와 다름")
        _inside(r["at"], span, f"{path}.rows[{i}].at")
        more = r.get("more", [])
        if more != R.by_grade(more) or r["term"] in more or (r["v"] is None and r["result"] is not None):
            _fail(f"{path}.rows[{i}]", "덧낱말의 순서(등급 → 가나다)가 다르거나 줄의 낱말과 겹치거나, 숫자 없는 줄에 결과 낱말이 있음")
        if r["v"] is None and R.grade_of(r["term"]) == "C" and not more and r.get("n_terms", 1) < 2:
            _fail(f"{path}.rows[{i}]", "C급 낱말 하나뿐인 글은 줄이 될 수 없음")
        if r.get("n_terms", 1 + len(more)) < 1 + len(more):
            _fail(f"{path}.rows[{i}].n_terms", "그 글의 낱말 수가 줄에 실린 낱말보다 적음")
    if any(sum(r["ch"] == n for r in side["rows"]) > TH["rows_per_channel"] for n in names):
        _fail(f"{path}.rows", "채널당 줄 수가 상한을 넘음")
    if roles is not None and any(roles.get(n) not in want for n in names):
        _fail(f"{path}.channels", "이 절에 올 수 없는 역할의 채널")


def _check_shape(d):
    """판 안의 칸들이 서로 맞는가(개수·상태·칸 이름)."""
    items = d["must"] + [x for g in d["rest"] for x in g["items"]]
    _unique([x["id"] for x in items], "digest", "항목 id")
    f = d["funnel"]
    if f["must"] != len(d["must"]) or not f["posts"] >= f["clusters"] >= f["candidates"] >= f["must"] \
            or len(items) - len(d["must"]) > TH["rest_max"]:
        _fail("digest.funnel", "개수가 판의 내용과 맞지 않음(글 ≥ 묶음 ≥ 후보 ≥ 꼭 볼 것, must = 실린 수, 나머지 30줄까지)")
    if d["sources"]["channels_ok"] > d["sources"]["channels_total"]:
        _fail("digest.sources", "읽은 채널이 전체보다 많음")
    empty = not (items or d["wire"]["rows"] or d["solo"]["rows"] or d["context"] or d["tomorrow"])
    if (d["status"] != "ok" and d["must"]) or (d["status"] == "withdrawn" and not empty):
        _fail("digest.status", "수집 부족이면 꼭 볼 것이, 내린 판이면 모든 절이 비어 있어야 함")
    cells = [g["cell"] for g in d["rest"]]
    if cells != [c for c in R.CELLS if c in cells] or any(R.cell_id(**x["cell"]) != g["cell"] for g in d["rest"] for x in g["items"]):
        _fail("digest.rest", "칸이 8칸 순서가 아니거나 항목의 칸과 다름")
    if any(sum(R.cell_id(**x["cell"]) == c for x in d["must"]) > TH["cell_max"] for c in R.CELLS):
        _fail("digest.must", "같은 칸이 상한을 넘음")
    _unique(d["notes"], "digest.notes", "알림 줄")


def validate_digest(d, sources=None):
    """공개 판. sources(sources.json)를 주면 채널이 목록에 있는지·역할에 맞는 절에 있는지·링크 순서까지 본다."""
    _digest(d, "digest")
    span = _span(d, "digest", strict=d["status"] != "withdrawn")
    roles = None if sources is None else {c["handle"]: (c["group"], c["role"]) for c in sources["channels"]}
    _check_shape(d)
    _check_head(d["head"], "digest.head")
    for i, x in enumerate(d["must"]):
        _check_score(x["score"], f"digest.must[{i}].score")
        _check_links(x, f"digest.must[{i}]", d["date"], span, roles)
    for gi, g in enumerate(d["rest"]):
        for i, x in enumerate(g["items"]):
            _check_links(x, f"digest.rest[{gi}].items[{i}]", d["date"], span, roles)
    _check_side(d["wire"], "digest.wire", span, roles, [(g, "wire") for g in R.GROUPS])
    _check_side(d["solo"], "digest.solo", span, roles, [("personal", "source")])
    for i, x in enumerate(d["context"]):
        if URL_RE.match(x["url"]).group("ch") != x["ch"] or (roles is not None and (roles.get(x["ch"]) or ("", ""))[1] != "context"):
            _fail(f"digest.context[{i}]", "주소의 채널이 ch와 다르거나 참고 채널이 아님")
    gloss = d.get("gloss", [])
    if gloss != R.glosses(x["term"] for x in gloss) or not {x["term"] for x in gloss} <= shown_terms(d):
        _fail("digest.gloss", "풀이가 그 낱말의 것이 아니거나 겹치거나 사전에 실린 순서가 아니거나 이 판에 나오지 않은 낱말의 것임")
    if len(dump(d).encode("utf-8")) > TH["bytes_max"]:
        _fail("digest", "판이 크기 상한을 넘음")
    return d


def validate_index(d):
    _index(d, "index")
    dates = [e["date"] for e in d["editions"]]
    if dates != sorted(set(dates), reverse=True) or d["latest"] != (dates[0] if dates else None):
        _fail("index.editions", "날짜가 최신순이 아니거나 겹치거나 latest와 다름")
    return d


def validate_state(d):
    _state(d, "state")
    ed, base = d["edition"], d["base"]
    if base and (ed is None or base["date"] >= ed["date"]):
        _fail("state.base", "직전 판의 날짜가 이 판보다 앞서야 함")
    for name, s in (("edition", ed), ("base", base)):
        if s and (s["window"]["from"] > s["window"]["to"] or edition_date(parse_iso(s["window"]["to"])) != s["date"]):
            _fail(f"state.{name}", "창이 뒤집혔거나 판 날짜와 맞지 않음")
        if s and s.get("read_to", "") > s["window"]["to"]:
            _fail(f"state.{name}.read_to", "제대로 읽은 곳이 창의 끝보다 뒤")
        if s and [t["key"] for t in s.get("topics", [])] != sorted({t["key"] for t in s.get("topics", [])}):
            _fail(f"state.{name}.topics", "대표 낱말 id가 겹치거나 글자순이 아님")
    return d


def validate_status(d):
    _status(d, "status")
    _unique([c["ch"] for c in d["channels"]], "status.channels", "채널")
    if d["ok"] != (d["reason"] == "ok") or d["counts"]["channels_ok"] != sum(c["ok"] for c in d["channels"]):
        _fail("status", "ok·reason·채널 수가 서로 맞지 않음")
    return d


def validate_sources(d):
    _sources(d, "sources")
    _unique([c["handle"].lower() for c in d["channels"]], "sources.channels", "채널 이름")
    for name, table in (("groups", R.GROUPS), ("roles", R.ROLES)):
        if [(x["id"], x["label"]) for x in d[name]] != list(table.items()):
            _fail(f"sources.{name}", "digest_rules의 표와 다름")
    if any((c["role"] == "off") != (c["title_sha"] is None) for c in d["channels"]):
        _fail("sources.channels", "요청하는 채널은 title_sha가 있어야 하고, off 채널은 null")
    return d


def validate_calendar(d):
    _calendar(d, "calendar")
    return d


def validate_overrides(d):
    _overrides(d, "overrides")
    return d


VALIDATORS = {"digest.json": validate_digest, "digest_index.json": validate_index, "digest_state.json": validate_state,
              "digest_status.json": validate_status, "sources.json": validate_sources, "calendar.json": validate_calendar,
              "digest_overrides.json": validate_overrides, "posts.json": validate_posts_doc,
              "collect_status.json": validate_collect_status, "clusters.json": validate_clusters_doc,
              "scored.json": validate_scored_doc, "manifest.json": validate_manifest}


def validator_for(name):
    """파일 이름 → 검증 함수. "digest/2026-10-08.json"은 판과 같다. 모르는 이름이면 ValueError."""
    name = name.replace("\\", "/")
    if re.fullmatch(r"digest/\d{4}-\d{2}-\d{2}\.json", name, re.ASCII):
        return validate_digest
    name = "manifest.json" if name == "pages/manifest.json" else name
    if name not in VALIDATORS:
        raise ValueError("계약에 없는 파일 이름")
    return VALIDATORS[name]
