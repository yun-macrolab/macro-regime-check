/* 저녁판 — 텔레그램 공개 채널 여러 곳이 함께 다룬 주제를 규칙으로 고른 판(data/digest*.json)을 그린다 (2026-10-08, 1단계 규칙 선별판).
   index.html의 applyView()가 setView(화면 이름, 뒤에 붙은 값)를 부른다 — "#evening"이면 최신 판, "#evening/2026-10-07"이면 그날 판.
   index.html 안의 el() · getJson() · calm()을 쓴다(부를 때 이미 정의돼 있다). 자료는 이 화면에 처음 들어올 때 읽는다.

   화면에 나가는 글자는 닫혀 있다. 채널 글의 글자는 자료에 없고(digest_check가 막는다), 자료가 잘못돼도 화면이 문장을 옮기지 않게 한 번 더 거른다:
     낱말      낱말 꼴(20자 이하, 한글·영문·숫자와 · / & +)이고 지문이 RULES.term_marks(사전 낱말)에 있을 때만 — term().
               사전 밖의 닫힌 낱말(요인·지역 · 방향 · 결과 낱말 · 만기)은 꼴만 본다 — word()
     고정 문구  아래 RULES.phrases에 있는 것만(digest_rules.py의 PHRASES와 같다)
     숫자      숫자 + 허용 단위 꼴만
     원문 링크  https://t.me/<채널>/<글 번호> 꼴이고, 주소의 채널이 그 줄의 채널과 같고, sources.json 목록에 있는 채널일 때만
     출처 라벨  sources.json(사람이 쓰는 파일)의 라벨, 이상하면 채널 이름
     낱말 풀이  문장이 들어갈 수 있는 유일한 칸이라 꼴이 아니라 지문으로 거른다 — (낱말 · 풀이)의 지문이 RULES.gloss_marks에 있을 때만
               (digest_gloss.py에 우리가 쓴 풀이의 지문이다. 풀이를 고치면 지문도 고친다 — test_evening_site_more.py가 견준다)
     공식 자료  https이고 도메인이 RULES.official_domains(공공 기관)에 들거나 그 하위일 때만 링크로(FRED · FRASER는 '시계열' · '문서 모음')
     길이 구간  RULES.sizes에 있는 이름일 때만
     AI 요약    닫힌 값이 아닌 하나뿐인 칸 — data/digest_picks.json의 문장(AI가 채권·애널 원천 채널의 글을 읽고 쓴 것, 2026-10-09). 최신 판 화면이고
               판 날짜 · 항목의 key · 읽힌 글(그 항목의 걸린 링크)이 맞을 때만, 꼴을 한 번 더 보고(fact) 'AI 요약' 표시와 함께 — picksOf() · aiOf()
   2026-10-08 저녁에 더한 칸(함께 나온 낱말 · 첫 글~마지막 글 · 직전 판 · 덧낱말 · 낱말 수 · 길이 · 붙은 것 · 풀이)은 모두 없어도 되는 칸이다 —
   있을 때만 그리고, 없는 판(10-08 첫 판)은 예전 그대로 그린다. 낱말 목록은 자료의 순서 그대로 둔다(화면이 다시 섞지 않는다).
   글자는 전부 el()의 텍스트 노드로 넣는다. 바깥 요청은 없다(자료는 data/ 아래 JSON뿐).
   숨김 목록(digest_overrides.json)이나 출처 목록(sources.json)을 읽지 못하면 닫는 쪽으로 간다 — 항목을 가리고, 링크를 걸지 않는다. */
"use strict";
window.Evening = (() => {
  // 규칙 쪽과 같아야 하는 값 — scripts/evening/digest_rules.py · digest_schema.py가 기준이다. JSON 꼴로 두고 test_evening_site.py가 견준다
  const RULES = {
    "phrases": {
      "why_bond": "채권 채널 {n}곳", "why_analyst": "애널 채널 {n}곳", "why_personal": "개인 채널 {n}곳",
      "why_wire": "속보형 겹침", "why_cross": "채권 + 다른 그룹", "why_all": "세 그룹 모두",
      "why_grade_a": "A급 낱말", "why_result": "같은 결과 낱말 {n}곳", "why_num": "같은 숫자 {n}곳",
      "why_event": "발표일 일치", "why_auction": "입찰일 일치", "why_bond_alone": "채권 1곳 + 일정",
      "why_move": "금리 변동 큼", "why_repeat": "어제와 같은 주제", "why_fwd": "전달 글이 절반 넘음",
      "note_short": "수집 부족 — 꼭 볼 것을 비웠습니다", "note_withdrawn": "이 판은 내렸습니다",
      "note_fewer": "오늘은 {n}건", "note_none": "오늘은 기준을 넘은 묶음이 없습니다",
      "note_prev_close": "금리는 전일 종가 — 방향 표시를 비웠습니다", "note_no_rates": "금리 자료를 읽지 못했습니다",
      "note_capped": "수집 창이 96시간 상한에 걸렸습니다", "note_rerun": "같은 판을 다시 계산했습니다",
      "note_truncated": "나머지 표에서 {n}줄을 줄였습니다", "note_channels": "채널 {n}곳을 읽지 못했습니다",
      "note_slim": "크기 상한에 맞추려고 낱말 풀이나 단독 줄을 줄였습니다"
    },
    "groups": {"bond": "채권", "analyst": "애널", "personal": "개인"},
    "roles": {"source": "원천", "wire": "속보형", "topic": "주제 한정", "context": "참고", "off": "제외"},
    "units": ["%p", "%", "bp", "조원", "조달러", "조", "억원", "억달러", "억", "만명", "천명", "명", "만계약", "계약", "달러", "원", "배"],
    "no_region": ["기술적", "기타"],
    "codes": {"fetch": "수신 실패", "no_preview": "미리보기 없음", "empty": "글을 읽지 못함", "title": "채널 제목이 바뀜",
              "rewind": "글 번호·시각이 거꾸로 감", "budget": "요청 예산 초과"},
    "reasons": {"broken": "채널 글의 형식이 바뀐 것으로 보여 판을 내지 않았습니다", "error": "실행이 실패해 판을 내지 못했습니다",
                "empty_streak": "꼭 볼 것이 없는 판이 여러 영업일 이어지고 있습니다"},
    "src": {"korea": "국고채 입찰 일정", "calendar": "일정표"},
    "run_kst": "17:41", "late_kst": "22:41", "edition_shift_h": 6, "show_editions": 10, "keep_days": 35,
    "min_bond_ok": 3, "min_total_ok": 16, "rows_per_channel": 5, "wire_query": "금리",
    "fact_min_chars": 10, "fact_chars": 140, "llm_items_max": 6, "llm_posts_max": 3,
    "sizes": {"짧음": "짧은 글", "보통": "보통 길이", "김": "긴 글"}, "size_short": 200, "size_long": 700,
    "official_domains": ["stlouisfed.org", "newyorkfed.org", "kansascityfed.org", "chicagofed.org", "treasury.gov", "treasurydirect.gov",
      "bea.gov", "eia.gov", "boj.or.jp", "mof.go.jp", "stat.go.jp", "europa.eu", "imf.org", "bok.or.kr", "mods.go.kr", "mofe.go.kr",
      "tradedata.go.kr", "nps.or.kr", "hf.go.kr"],
    "gloss_marks": [
      "02335a85024d516002fbe06d04f43f11074e541c08505a380b031b180d88bf0b0f4cf94e1127cdcb1392068414089ce91929b0d21ae5052f1c5233101ddbf5811de0fe4a",
      "1e5796951f2c5d501f840f0322f6b78023d330f9240b83fe245ec54724b90918253ab802274b3b95301ac5013488a569351fce7a35ec3ad33663b709368fbbd3374a1304",
      "381cab413bc1954b3c23f4023cb776053cce6c833e5c3b083fd8808a3ff2f3424230f2674514818b47ad64cf47d55de3481337c4495ec4f45202987c52e86a6d534f1a5a",
      "5499baa055722ce6558ad6c5560359075a002be25ab0a95b5f0ec8f76358e8e2643dc5916637d34a68219ef3683985956a0758406adb68316f4188006f9e9b5670920c2c",
      "7139adf8730405f973c192bd74c2b60d74f6f1db7cad19e07db717487e6bf27e7ef4c94e805abfd282ed9b7386bd530587cc476a8ccaf2a08d0ce41291e4eb0d940147a2",
      "9473c7659902759d9d8347349ee3ed3f9eeb80aba28abb19a680cf11a95261f2a96456c6ac9493e9ad236461ade4c51cae09fa3baf0b80c0b1ea320fb2627821b3652f83",
      "b9271cd1b9e0124abeb7fae4bec66283c2d32f89c509a4f5c989b734ca01b103cc39f081cc45350dcf6a13badec502c9e02356c3e4cd2ad1e56d9913e7f58c76ebc0feb9",
      "ecb0482aed01c1b9ef2a6ccbf03120dcf0a5aad3f0e9aab7f2d0e2eff44f86aaf599196bf5e63cb4f6a4245cf70a2f3ef8446983f917165cf9eb7baefacdb875fed0e4af",
      "ff0335f3ffb8c9cb"],
    "term_marks": [
      "00a5d847019bec5001e257a702496fb0037c155c03d704bd0586a1930808efde08eb63cf08f2bb8c098195230a2b42650a7c20610b284c610bbdd76d0c658bb70d53308e",
      "0e92660210f52ee7117dc855135f365a1491977d1515962f15bd1f4716224b55178fa32017a6b26c1b6bee7a1c1914f61db817821dd5526b1e42bf64201a83ad21a35594",
      "23d5135f25aa5882273b80e828ea29882a3efb662b890aef2cbe95ed2ceebc33333328d633f8f6dd355dadcb369af43c3840450239e231603dbbecbe3ea71ba93fe8d879",
      "451370f04602bd1546662a4347025ceb4716813d4af258574ba86efa4da350d94df4f5fc4f89077e50e3e28150fd9f925365bd5c5447b74d59d5eb905ac1e9bd5e1df786",
      "6486d6dd65c3415566aa2b45677cb12e67ff1f4568efc397697539586b0d06816bc662f96bec7c976cbaa4e56db8eb9f741547bc745b086476a4299176d411017ae38666",
      "7e461a5f807189b581531d5c822d7b5483e0fd9b86663708872702dd8c82cda68e3c96148e85762590610d85916a99989256ee209305c7e5961bf1c296be159a96f5907e",
      "97b8adfb97fa0ce19934a3519ab709219b145ef39d9446579df6360b9e4de0819f16a4269fd7e752a555053faded8ab8ae3d5061ae5d2395af8811d6b2e41cecb3d3e025",
      "b662564db716d9e9b96a597fb9d3003dba68c434bd50780dc24f42ffc4155271c43587dbc59c4f10c64ec9d7c8829339c8bed6cccb76dc93cbb64e37cc467b7dccfd2b0a",
      "cdc3fdddcf04bcc6cf771f75d2753d10d3b59f09d3d32374d5095a9ad8f3f22ed95934dedaed65fddde3f108decb810be432701be6d2eb72e6e5ebe3e72ec4b5e7368c35",
      "e7aa03e6e880cb42eab5a9f7eae05ae2ee1af6def2296ffaf26d0c52f361d288f518ce19f6d8622bf9f96225fa0f8bcefa1e0b51fd249389fec68596"]
  };
  const P = RULES.phrases;
  const QUIET_NOTES = ["note_short", "note_withdrawn", "note_fewer", "note_none", "note_channels"];   // 판 머리가 아닌 자리에서 말하는 알림
  const SCORE_PARTS = [["C", "다룬 곳"], ["X", "그룹을 넘은 확인"], ["K", "낱말 등급"], ["E", "일정"], ["M", "금리 변동"], ["Y", "유튜브"],
    ["P", "감점"]];
  const HOW = [
    `텔레그램 공개 채널의 웹 미리보기를 평일 저녁에 읽습니다(예약 ${RULES.run_kst} KST — 늦게 돌거나 같은 판을 다시 계산할 수 있어 실제 수집 시각을 위에 적습니다. AI 요약에 쓸 글이 있는 채널은 운영자 PC가 한 번 더 읽습니다). ` +
      "로그인하지 않으며 누구나 볼 수 있는 미리보기 쪽만 읽습니다.",
    "채널 글의 문장은 옮겨 싣지 않습니다. 채널 글에서 가져오는 것은 미리 정한 낱말 사전의 낱말과 그 낱말을 쓴 채널 수, 두 곳 이상이 똑같이 쓴 숫자와 단위, " +
      `글을 올린 시각, 글 길이 구간(${RULES.size_short}자 미만 짧은 글 · ${RULES.size_long}자 이상 긴 글), 그 글에서 걸린 사전 낱말의 수, ` +
      "그림·파일이 붙었는지, 원문 링크뿐입니다. " +
      "다만 속보형·개인 채널이 혼자 쓴 글의 숫자는 한 곳만 쓴 숫자입니다(낱말 바로 곁의 숫자 하나). " +
      "무슨 내용인지는 링크를 눌러 원문에서 읽어 주세요.",
    `'AI 요약' 표시가 붙은 문장은 채널의 글이 아니라 AI(Claude)가 쓴 것입니다. 채권·애널 그룹 원천 채널의 글을 항목마다 ${RULES.llm_posts_max}건까지 읽고 ` +
      "자기 말로 한두 문장을 씁니다(개인·속보형 채널의 글과 전달 글은 읽히지 않습니다). 원문과 길게 겹치지 않는지, 숫자와 단위가 원문에 있는지, 정해 둔 권유·전망 표현이 없는지 같은 " +
      "자동 검사를 통과한 문장만 싣습니다(짧은 어구는 원문과 겹칠 수 있습니다). 그래도 뜻이 틀릴 수 있습니다 — 원문에서 확인해 주세요. 요약은 운영자의 PC에서 따로 만들어 " +
      "올리므로 문장이 없는 날과 항목이 있습니다. 텔레그램 약관은 플랫폼에서 얻은 자료를 AI에 쓰는 것을 제한합니다 — 채널 운영자가 요청하면 그 채널을 내립니다(아래 '삭제·정정 요청').",
    "낱말 풀이는 채널의 글이 아니라 이 사이트가 직접 쓴 한 줄입니다. 낱말의 뜻만 적고(그 글의 내용이 아닙니다) 시세·전망·평가는 담지 않습니다. " +
      "나라를 밝히지 않은 지표는 미국 지표로 셉니다. '공식 자료' 링크는 공공 기관의 쪽이고(첫 쪽일 때도 있습니다), " +
      "'시계열' · '문서 모음' 링크는 세인트루이스 연은이 통계와 문서를 모아 싣는 쪽(FRED · FRASER)입니다 — 민간 기관이 내는 지표도 그 안에 있습니다. " +
      "어느 것도 채널 글이 가리킨 주소가 아닙니다.",
    "고르는 일은 LLM 없이 규칙이 합니다(AI는 규칙이 고른 항목에 요약 문장만 붙입니다). 규칙은 몇 곳이 함께 다뤘는지를 셀 뿐이고 금리의 방향이나 강도, 매매 판단을 내지 않습니다. " +
      "낱말과 숫자만으로는 글의 뜻을 잘못 짚을 수 있습니다.",
    "이 화면은 아침 점검표의 규칙 판정과 무관한 참고 자료입니다. 시범 운영 중이라 낱말 사전과 점수 기준은 바뀔 수 있습니다."
  ];
  const TAKEDOWN = "https://github.com/yun-macrolab/macro-regime-check/issues/new?template=takedown.md";
  // 판이 늦거나 실행이 실패했을 때 무엇을 하면 되는지 — 읽는 사람이 곧 운영자다(바깥 링크는 늘리지 않고 글로만 적는다)
  const RERUN = " 저장소 Actions의 evening 실행 기록에서 원인을 볼 수 있고, 수동 실행으로 다시 돌릴 수 있습니다.";
  const CARD_NOTE = "채널 글의 문장은 싣지 않습니다 — 낱말은 미리 정한 사전에서 찾은 것이고, 풀이는 이 사이트가 쓴 것입니다. " +
    "풀이는 낱말의 뜻이지 그 글의 내용이 아닙니다(나라를 밝히지 않은 지표는 미국 지표로 셉니다). 내용은 원문 링크에서 읽어 주세요.";
  const AI_NOTE = " 'AI 요약'은 AI(Claude)가 채권·애널 채널의 글을 읽고 자기 말로 쓴 문장입니다 — 채널 글의 문장이 아니고, 틀릴 수 있습니다.";
  const UNFOLD = 10;                                                      // 나머지 표가 이 줄 수 이하면 펼쳐 둔다
  const PIPS = 12;                                                        // 곳 수 막대의 칸 수 상한(넘으면 숫자만 커진다)
  const COMMON = ["digest.json", "digest_index.json", "digest_status.json", "sources.json", "digest_overrides.json", "digest_picks.json"];
  const PIECES = ["latest", "index", "status", "sources", "overrides"];        // COMMON과 같은 순서(끝의 요약 층은 따로 — 못 받으면 비운다)
  const HOUR = 36e5, DAY = 24 * HOUR, KST = 9 * HOUR, BEAT_MS = 6e4, REFETCH_MS = 10 * 6e4;
  const DOW = "일월화수목금토";

  // ---------- 꼴 검사 — 자료에서 온 값은 모두 여기를 거친다 ----------
  const HANDLE = "[A-Za-z][A-Za-z0-9_]{3,31}";
  const HANDLE_RE = new RegExp("^" + HANDLE + "$");
  const POST_RE = new RegExp("^https://t\\.me/(" + HANDLE + ")/([1-9]\\d{0,9})$");
  const ID_RE = new RegExp("^\\d{8}-" + HANDLE + "-[1-9]\\d{0,9}$");
  const NUM_RE = new RegExp("^-?(?:0|[1-9]\\d{0,6})(?:\\.\\d{0,2}[1-9])?(?:" + RULES.units.join("|") + ")$");
  const WORD_RE = /^[가-힣A-Za-z0-9][가-힣A-Za-z0-9 ·\/&+]{0,19}$/;
  const DATE_RE = /^\d{4}-\d{2}-\d{2}$/, HHMM_RE = /^(?:[01]\d|2[0-3]):[0-5]\d$/;
  const ISO_RE = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}):\d{2}\+09:00$/;
  const NOT_LABEL = /[<>@\\\p{Cc}\p{Cf}\p{Zl}\p{Zp}]|https?:/u;
  const OFFICIAL_RE = /^https:\/\/((?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,})\/[A-Za-z0-9._~\/?&=%-]*$/;
  const FACT_RE = new RegExp(`^[가-힣A-Za-z0-9 .,·%()~/+:&-]{${RULES.fact_min_chars},${RULES.fact_chars}}$`);
  const LINKISH = /https?:|www\.|[A-Za-z0-9-]+\.[A-Za-z]{2,}/i;
  const marks = rows => new Set(rows.join("").match(/.{8}/g));              // 지문 8자씩 이어 붙여 둔 것 → 집합
  const MARKS = marks(RULES.gloss_marks), TERMS = marks(RULES.term_marks);
  const PHRASE_RES = Object.entries(P).map(([code, text]) =>
    [code, new RegExp("^" + text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace("\\{n\\}", "[1-9]\\d{0,2}") + "$")]);

  const isObj = v => !!v && typeof v === "object" && !Array.isArray(v);
  const list = v => (Array.isArray(v) ? v : []);
  const own = (o, k) => typeof k === "string" && Object.prototype.hasOwnProperty.call(o, k);
  const count = v => (Number.isInteger(v) && v >= 0 && v < 1e7 ? v : null);
  const isHandle = v => typeof v === "string" && HANDLE_RE.test(v);
  const word = v => (typeof v === "string" && WORD_RE.test(v) ? v : null);
  // 사전 낱말 — 낱말 꼴이고 지문이 사전에 있을 때만(낱말처럼 생긴 다른 글자는 그리지 않는다)
  const term = v => (word(v) && TERMS.has(fingerprint(v)) ? v : null);
  const label = v => (typeof v === "string" && v.length > 0 && v.length <= 40 && v === v.trim() && !NOT_LABEL.test(v) ? v : null);
  const hhmm = (v, fallback) => (typeof v === "string" && HHMM_RE.test(v) ? v : fallback);
  // AI 요약 문장은 닫힌 값이 아니다 — 꼴을 한 번 더 본다(digest_picks.ok_shape의 앞부분): 길이 · 정해 둔 글자만(제어 문자 · 꺾쇠 · @ · 줄바꿈 없음) · 주소 꼴 없음 · '…다.'로 맺음
  const fact = v => (typeof v === "string" && FACT_RE.test(v) && !LINKISH.test(v) && v === v.trim() && v.endsWith("다.") ? v : null);
  // 숫자 + 허용 단위. 보기 좋게 정수부에 쉼표만 넣는다("4732계약" → "4,732계약")
  const num = v => (typeof v === "string" && NUM_RE.test(v)
    ? v.replace(/^(-?)(\d+)/, (_, sign, n) => sign + n.replace(/\B(?=(\d{3})+$)/g, ",")) : null);
  function phraseCode(v) {
    const hit = typeof v === "string" ? PHRASE_RES.find(([, rx]) => rx.test(v)) : null;
    return hit ? hit[0] : null;
  }
  // 공식 자료 주소 → {url, host}. https이고 도메인이 허용 목록에 들거나 그 하위일 때만(포트·계정·조각이 붙은 주소는 받지 않는다)
  function official(v) {
    const m = typeof v === "string" && v.length <= 200 ? OFFICIAL_RE.exec(v) : null;
    return m && RULES.official_domains.some(d => m[1] === d || m[1].endsWith("." + d)) ? { url: v, host: m[1] } : null;
  }
  // 글자 지문(FNV-1a 32비트, 16진 8자리) — 풀이가 규칙에 적힌 그 글자인지 견주는 데 쓴다
  function fingerprint(s) {
    let h = 0x811c9dc5;
    for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 0x01000193);
    return (h >>> 0).toString(16).padStart(8, "0");
  }
  // 판의 낱말 풀이 → {낱말: {text, link}}. 낱말 꼴이고 (낱말 · 풀이)의 지문이 규칙에 있을 때만 — 그 밖의 글자는 한 글자도 그리지 않는다
  function glossary(d) {
    const rows = list(isObj(d) ? d.gloss : null).filter(g => isObj(g) && term(g.term) && typeof g.text === "string"
      && g.text.length <= 60 && MARKS.has(fingerprint(g.term + "\n" + g.text)));
    return new Map(rows.map(g => [g.term, { text: g.text, link: official(g.url) }]));
  }
  // 링크·단독 줄에 붙는 것: 이 글에만 더 있는 낱말 · 길이 구간 · 그림·파일 · 그 글의 사전 낱말 수(n)
  function extras(x, n) {
    return { more: list(x.more).map(term).filter(Boolean).slice(0, n), size: own(RULES.sizes, x.size) ? RULES.sizes[x.size] : null,
      pic: x.pic === true, n: count(x.n_terms) };
  }
  // 꼬리표 — 낱말 수는 줄에 이미 실린 낱말(shown개)보다 많을 때만 적는다
  const tags = (x, shown) => [x.size, x.pic ? "그림·파일 있음" : null, x.n > (shown || 0) ? `사전 낱말 ${x.n}개` : null].filter(Boolean);
  const tagNodes = (x, shown) => tags(x, shown).flatMap(t => [" ", el("span", { class: "eve-tag" }, t)]);
  function realDate(v) {
    if (typeof v !== "string" || !DATE_RE.test(v)) return false;
    const t = Date.parse(v + "T00:00:00Z");                               // 2월 30일 같은 없는 날짜를 브라우저마다 다르게 읽는다
    return Number.isFinite(t) && new Date(t).toISOString().slice(0, 10) === v;
  }
  // 판으로 쓸 수 있는 자료인가 — 이 화면이 아는 형식이고 날짜가 있다
  const usable = d => (isObj(d) && d.schema === 1 && realDate(d.date) ? d : null);

  // ---------- 시각 · 판 날짜 ----------
  const clock = () => Date.now();
  const dow = date => DOW[new Date(date + "T00:00:00Z").getUTCDay()];
  const md = date => `${date.slice(5)}(${dow(date)})`;                    // "10-08(목)"
  const weekday = date => "월화수목금".includes(dow(date));
  const kstDay = ms => new Date(ms + KST).toISOString().slice(0, 10);
  // 판 날짜 = (시각 − 6시간)의 한국 날짜 — digest_base.edition_date와 같다
  const editionOf = ms => kstDay(ms - RULES.edition_shift_h * HOUR);
  function stamp(iso) {                                                   // 자료의 시각(ISO +09:00) → "10-08 18:07"
    const m = typeof iso === "string" ? ISO_RE.exec(iso) : null;
    return m && realDate(m[1]) ? { iso, date: m[1], text: `${m[1].slice(5)} ${m[2]}` } : null;
  }
  function when(iso) {
    const s = stamp(iso);
    return s ? el("time", { datetime: s.iso }, s.text) : null;
  }
  // 지금까지 나왔어야 하는 가장 최근 판 날짜 — 평일 d의 마감 시각(late, 기본 22:41 KST)이 지났으면 d. 주말판은 없고 한국 휴일에는 돈다
  function dueEdition(ms, late) {
    const [h, m] = hhmm(late, RULES.late_kst).split(":").map(Number);
    for (let back = 0; back < 8; back++) {
      const day = kstDay(ms - back * DAY);
      if (weekday(day) && ms >= Date.parse(day + "T00:00:00+09:00") + (h * 60 + m) * 6e4) return day;
    }
    return null;
  }
  // 보이는 판(날짜)이 지금 기준으로 어떤가: none 판 없음 · late 나왔어야 할 판이 없다 · pending 오늘 판은 아직 수집 전 · fresh
  function judge(date, ms, late) {
    if (!realDate(date)) return { kind: "none", due: null };
    const due = dueEdition(ms, late), today = editionOf(ms);
    if (due && date < due) return { kind: "late", due };
    return weekday(today) && date < today ? { kind: "pending", due: today } : { kind: "fresh", due: null };
  }

  // ---------- 자료 읽기 ----------
  const live = { on: false, want: "", bad: false, seq: 0, timer: 0, model: null, alerts: null, body: null, said: null };
  const store = { common: null, pending: null, editions: new Map() };

  async function fetchCommon() {
    const got = await Promise.allSettled(COMMON.map(name => getJson("data/" + name)));
    const pick = i => (got[i].status === "fulfilled" && isObj(got[i].value) ? got[i].value : null);
    return { latest: usable(pick(0)), index: pick(1), status: pick(2), sources: pick(3), overrides: pick(4), picks: pick(5), at: clock() };
  }
  // 공용 자료 — 처음 한 번 읽고, 10분이 지났으면 다시 읽는다. 다시 읽다 못 받은 조각은 가진 것을 둔다(잠깐의 수신 실패로 화면이 비지 않게).
  // AI 요약 층만은 못 받으면 비운다(picks) — 없는 날이 보통이고, 내려간 문장이 열어 둔 화면에 남으면 안 된다
  function common() {
    if (store.common && clock() - store.common.at < REFETCH_MS) return Promise.resolve(store.common);
    if (!store.pending) store.pending = fetchCommon().then(next => {
      const old = store.common || {}, merged = { at: next.at, picks: next.picks };
      for (const k of PIECES) merged[k] = next[k] || old[k] || null;
      store.common = merged;
      store.pending = null;
      return merged;
    }, e => { store.pending = null; throw e; });
    return store.pending;
  }
  // 지난 판 하나(없으면 null). 파일 이름과 안의 날짜가 같아야 그 판이다. 읽은 판은 다시 받지 않는다
  async function edition(date) {
    if (store.editions.has(date)) return store.editions.get(date);
    let d = null;
    try { d = usable(await getJson(`data/digest/${date}.json`)); } catch (e) { d = null; }
    if (!d || d.date !== date) return null;
    store.editions.set(date, d);
    return d;
  }
  const mark = c => JSON.stringify([c.latest && [c.latest.date, c.latest.collected_at], c.status && c.status.checked_at,
    c.index && c.index.updated_at, c.overrides, !!c.sources, c.picks && [c.picks.date, c.picks.made_at]]);

  // ---------- 화면 전환 · 다시 판정 ----------
  // index.html의 applyView()가 화면이 바뀔 때마다 부른다. 여기서 난 예외가 다른 화면의 전환을 막지 않게 삼킨다
  function setView(view, arg) {
    try { turn(view, arg); } catch (e) { /* 저녁판만 비고 나머지 화면은 그대로 돈다 */ }
  }
  function turn(view, arg) {
    if (view !== "evening") { live.on = false; return; }
    const want = realDate(arg) ? arg : "", bad = !!arg && !want;
    const same = live.on && live.model && live.want === want && live.bad === bad;
    Object.assign(live, { on: true, want, bad });
    if (!live.timer) {                                                    // 열어 둔 채 시간이 지나도 다시 판정한다
      live.timer = setInterval(beat, BEAT_MS);
      document.addEventListener("visibilitychange", beat);
    }
    if (same) paintAlerts(); else show();
  }
  async function show() {
    const ticket = ++live.seq;
    try {
      if (!store.common) paint({ loading: true });
      const c = await common();
      const past = live.want && !(c.latest && c.latest.date === live.want) ? live.want : "";
      const digest = past ? await edition(past) : c.latest;
      if (ticket === live.seq) paint({ ...c, digest, past, bad: live.bad });   // 기다리는 사이 다른 판으로 넘어갔으면 그리지 않는다
    } catch (e) {
      if (ticket === live.seq) quiet(() => paint({ failed: true }));
    }
  }
  // 1분마다, 그리고 탭으로 돌아올 때 — 알림을 지금 시각으로 다시 쓰고, 10분이 지났으면 자료를 다시 읽어 달라졌을 때만 다시 그린다
  async function beat() {
    try {
      if (!live.on || !live.model || live.model.loading) return;
      if (live.model.failed) { show(); return; }
      paintAlerts();
      const c = store.common;
      if (!c || document.visibilityState === "hidden" || clock() - c.at < REFETCH_MS) return;
      const before = mark(c);
      if (mark(await common()) !== before && live.on) show();
    } catch (e) { /* 다시 읽지 못하면 보던 판을 그대로 둔다 */ }
  }

  // ---------- 출처 목록 · 숨김 목록 ----------
  // sources.json → {채널 이름: {handle, label, group, role}}. 못 읽었으면 null — 그러면 링크를 걸지 않는다
  function directory(sources) {
    if (!isObj(sources) || !Array.isArray(sources.channels)) return null;
    return new Map(sources.channels.filter(c => isObj(c) && isHandle(c.handle))
      .map(c => [c.handle, { handle: c.handle, label: label(c.label) || c.handle, group: c.group, role: c.role }]));
  }
  // 그룹·역할 이름 — sources.json의 라벨, 없으면 규칙의 이름
  function names(sources, key) {
    const mine = list(isObj(sources) ? sources[key] : null).filter(x => isObj(x) && own(RULES[key], x.id) && label(x.label));
    return { ...RULES[key], ...Object.fromEntries(mine.map(x => [x.id, x.label])) };
  }
  // 그리는 데 쓰는 것들. hide.all이면 판의 항목을 모두 가린다: 숨김 목록을 못 읽었거나(broken), 내리기 스위치가 켜졌거나, 내린 판이거나
  function context(m) {
    const ov = m.overrides, d = m.digest, dir = directory(m.sources);
    const ok = isObj(ov) && ov.schema === 1 && typeof ov.withdraw === "boolean" && Array.isArray(ov.hide_ids)
      && Array.isArray(ov.hide_channels);
    const hide = { broken: !ok, all: !ok || ov.withdraw || (!!d && d.status === "withdrawn"),
      ids: new Set(ok ? ov.hide_ids : []), chans: new Set(ok ? ov.hide_channels : []) };
    // gloss = 이 판의 풀이, used = 화면에 실제로 나간 사전 낱말(풀이 절은 이 낱말의 것만 싣는다 — 숨긴 항목의 낱말은 빠진다), ai = 그려진 요약 문장 수
    return { dir, hide, group: names(m.sources, "groups"), role: names(m.sources, "roles"), gloss: glossary(d), used: new Set(),
      picks: picksOf(m), ai: 0, label: ch => (dir && dir.has(ch) ? dir.get(ch).label : ch) };
  }
  // AI 요약 층 → {항목의 key: {fact, src} | null}. 최신 판 화면이고 파일의 판 날짜가 보는 판과 같을 때만(digest_schema.py 머리말 'AI 요약 층' — 파이썬 판은
  // digest_picks.attach. 내린 판은 항목을 그리지 않아 붙일 자리가 없다). 물을 수 있는 수보다 많이 든 파일은 통째로 믿지 않는다. 문장마다 key ·
  // 읽힌 글 1~3개([채널, 글 번호], 겹치지 않게) · 문장의 꼴을 보고, 어긋난 문장과 key가 겹친 문장은 그 문장만 뺀다(null)
  function picksOf(m) {
    const p = m.picks, d = m.digest, got = new Map(), rows = list(isObj(p) ? p.items : null), most = RULES.llm_posts_max;
    if (m.past || !d || !isObj(p) || p.schema !== 1 || p.mode !== "ai" || p.date !== d.date || rows.length > RULES.llm_items_max) return got;
    const post = s => Array.isArray(s) && s.length === 2 && Number.isInteger(s[1]);
    const read = v => Array.isArray(v) && v.length > 0 && v.length <= most && v.every(post) && new Set(v.map(String)).size === v.length;
    for (const x of rows.filter(x => isObj(x) && typeof x.key === "string"))
      got.set(x.key, !got.has(x.key) && read(x.src) && fact(x.fact) ? { fact: x.fact, src: x.src } : null);
    return got;
  }
  // 새 창으로 여는 바깥 링크는 여기서만 만든다 — 연 쪽 창을 건드리지 못하고, 어디서 왔는지 넘기지 않는다
  function out(href, text, name) {
    const a = el("a", { href, target: "_blank", rel: "noopener noreferrer" }, text);
    if (name) a.setAttribute("aria-label", name);
    return a;
  }
  // 원문 링크 하나. 꼴이 어긋났거나 숨긴 채널·목록에 없는 채널이면 null, 출처 목록을 못 읽었으면 링크 없이 채널 이름만
  function source(ctx, ch, url, text, name) {
    const m = typeof url === "string" ? POST_RE.exec(url) : null;
    if (!m || m[1] !== ch || ctx.hide.chans.has(ch)) return null;
    if (!ctx.dir) return el("span", { class: "eve-meta" }, text || ch);
    const c = ctx.dir.get(ch);
    return c && c.role !== "off" ? out(url, text || c.label, name) : null;
  }

  // ---------- 알림 줄 ----------
  function alertsFor(m, ms) {
    const lines = [], say = (bad, ...parts) => lines.push(el("p", { class: bad ? "banner" : "eve-info" }, ...parts));
    if (m.loading) { say(false, "저녁판을 불러오는 중…"); return lines; }
    if (m.failed) { say(true, "저녁판 자료를 불러오지 못했습니다. 잠시 뒤 다시 열어 주세요."); return lines; }
    const d = m.digest, latest = () => el("a", { href: "#evening" }, "최신 판 보기");
    if (m.bad) say(false, "주소의 날짜를 읽을 수 없어 최신 판을 보여 줍니다.");
    if (m.past && d) say(false, `지난 판(${md(m.past)})을 보고 있습니다. `, latest());
    if (m.past && !d)
      say(true, `${md(m.past)} 판이 없습니다 — 그날 판이 나오지 않았거나 보관 기간(${RULES.keep_days}일)이 지났습니다. `, latest());
    if (!m.past) timeAlerts(m, ms, say);
    if (d) editionAlerts(d, context(m), say);
    return lines;
  }
  // 최신 판 화면에서만: 판이 없다 · 오늘 판이 아직 없다 · 최근 실행이 실패했다
  function timeAlerts(m, ms, say) {
    const d = m.digest, st = isObj(m.status) ? m.status : {}, expect = isObj(st.expect) ? st.expect : {};
    const run = hhmm(expect.run_kst, RULES.run_kst), late = hhmm(expect.late_kst, RULES.late_kst);
    const j = judge(d && d.date, ms, late), below = d ? ` 아래는 ${md(d.date)} 판입니다.` : "";
    if (j.kind === "none") say(true, "아직 판이 없습니다 — 첫 저녁 실행 전이거나 판 파일을 읽지 못했습니다.");
    if (j.kind === "late")
      say(true, `${md(j.due)} 판이 아직 없습니다 — 평일 ${run} 예약 실행이 ${late}까지 반영되지 않았습니다.` + below + RERUN);
    if (j.kind === "pending") say(false, `오늘 ${md(j.due)} 판은 평일 ${run}(KST) 수집 뒤에 나옵니다.` + below);
    const ran = st.ok === false && own(RULES.reasons, st.reason) ? stamp(st.checked_at) : null;
    if (ran && (!d || st.checked_at >= String(d.collected_at)))            // 보이는 판보다 앞선 실행의 실패는 지난 일이다
      say(true, `최근 저녁 실행(${ran.text}): ${RULES.reasons[st.reason]}.` + (st.published === false ? below : "")
        + (st.reason === "empty_streak" ? "" : RERUN));
  }
  function editionAlerts(d, ctx, say) {
    const s = isObj(d.sources) ? d.sources : {}, ok = count(s.channels_ok), total = count(s.channels_total);
    if (ctx.hide.broken) say(true, "숨김 목록(digest_overrides.json)을 읽지 못해 이 판의 항목을 가렸습니다.");
    else if (ctx.hide.all) say(true, P.note_withdrawn + ".");
    else if (d.status === "short")
      say(true, `${P.note_short}. 채권 채널 ${RULES.min_bond_ok}곳 미만이거나 전체 ${RULES.min_total_ok}곳 미만만 읽혔습니다.`);
    if (ctx.hide.all) return;
    if (ok !== null && total !== null && ok < total)
      say(false, `채널 일부를 읽지 못했습니다 — ${total}채널 중 ${ok} 읽음. 채널별 상태는 맨 아래 '출처와 수집 방식'에 있습니다.`);
    if (!ctx.dir) say(true, "출처 목록(sources.json)을 읽지 못해 원문 링크를 걸지 않았습니다.");
  }
  function paintAlerts() {
    if (!live.model || !live.alerts) return;
    const lines = alertsFor(live.model, clock()), text = lines.map(n => n.textContent).join("\n");
    if (text === live.said) return;                                       // 같은 말이면 다시 쓰지 않는다(화면 읽기가 1분마다 되풀이해 읽지 않게)
    live.said = text;
    live.alerts.replaceChildren(...lines);
  }

  // ---------- 그리기 ----------
  function paint(m) {
    live.model = m;
    if (!live.body) {                                                     // 알림 줄과 본문 자리를 한 번 만든다(붙이고 나서야 기억한다)
      const alerts = el("div", { class: "eve-alerts", role: "status" }), body = el("div", { class: "eve-body" });
      document.getElementById("evening-wrap").replaceChildren(alerts, body);
      Object.assign(live, { alerts, body, said: null });
    }
    paintAlerts();
    if (m.loading || m.failed) { live.body.replaceChildren(); return; }
    const ctx = context(m), d = m.digest, open = d && !ctx.hide.all;
    // 항목 절을 판 머리보다 먼저 만든다 — 머리의 배지가 그려진 요약 문장 수(ctx.ai)를 쓴다. 풀이 절은 맨 뒤(머리와 항목에 나간 낱말을 다 센 뒤)
    const secs = (open ? [mustSection, tomorrowSection, restSection, bondSection, sideSection, contextSection] : []).map(f => part(() => f(ctx, d)));
    const top = [d ? () => headBox(ctx, d, m.status) : null, ctx.hide.all ? null : () => editionNav(m.index, d ? d.date : "")].map(part);
    live.body.replaceChildren(...[...top, ...secs, open ? part(() => glossSection(ctx)) : null, part(() => about(ctx, m))].filter(Boolean));
    if (!calm()) {                                                        // 판이 그려질 때 숫자가 한 번 깜박인다(움직임을 껐으면 하지 않는다)
      live.body.classList.add("eve-fresh");
      setTimeout(() => live.body.classList.remove("eve-fresh"), 1000);
    }
  }
  // 절 하나 — 자료의 어느 칸이 깨져도 그 절만 빠지고 나머지는 그린다
  function part(make) {
    if (!make) return null;
    try { return make(); } catch (e) { return el("p", { class: "empty-state" }, "이 절을 그리지 못했습니다 — 자료의 형식을 확인해야 합니다."); }
  }
  const quiet = make => { try { return make(); } catch (e) { return null; } };      // 줄 하나 — 깨졌으면 그 줄만 뺀다
  const section = (title, sub, ...children) => el("section", { class: "eve-sec" },
    el("div", { class: "section-heading" }, el("h2", {}, title), sub ? el("span", {}, sub) : null), ...children);

  // ---------- 판 머리 ----------
  function headBox(ctx, d, status) {
    const f = isObj(d.funnel) ? d.funnel : {}, s = isObj(d.sources) ? d.sources : {}, w = isObj(d.window) ? d.window : {};
    const n = v => el("strong", {}, count(v) === null ? "—" : String(v));
    const open = ctx.hide.all ? [] : [                                     // 금리와 주제가 먼저 — 폰 첫 화면에 들어오게
      part(() => ratesLine(d.head)), part(() => topTerms(ctx, d.head)),
      el("p", { class: "eve-funnel" }, "읽은 ", n(f.posts), "건 → 묶음 ", n(f.clusters), " → 후보 ", n(f.candidates), " → 꼭 ", n(f.must), "건 · ",
        n(s.channels_total), "채널 중 ", n(s.channels_ok), " 읽음", unread(ctx, d, status)),
      part(() => notes(d.notes))];
    return el("section", { class: "box eve-head" },
      el("div", { class: "eve-bar" }, el("h2", {}, `저녁판 ${d.date}(${dow(d.date)})`),
        el("span", { class: "eve-badges" }, el("span", { class: "eve-badge eve-pilot" }, "시범"),
          el("span", { class: "eve-badge" }, ctx.ai ? "규칙 선별 + AI 요약" : "규칙 선별 · 문장 없음"))),
      el("div", { class: "eve-head-body" },
        el("p", {}, "수집 ", when(d.collected_at) || "시각 없음", " (KST) · 수집 창 ", when(w.from) || "?", " ~ ", when(w.to) || "?"),
        ...open));
  }
  const codeText = code => (own(RULES.codes, code) ? RULES.codes[code] : "실패");
  // 이번 판에서 읽지 못한 채널 — 상태 파일이 이 판의 것일 때만
  function unread(ctx, d, status) {
    if (!isObj(status) || status.edition !== d.date) return null;
    const lost = list(status.channels).filter(c => isObj(c) && c.ok === false && isHandle(c.ch) && !ctx.hide.chans.has(c.ch)
      && (!ctx.dir || ctx.dir.has(c.ch)));
    return lost.length ? el("small", {}, " · 읽지 못한 곳: " + lost.map(c => `${ctx.label(c.ch)}(${codeText(c.code)})`).join(", ")) : null;
  }
  function bp(v) {
    const s = v.toFixed(1);
    return (Number(s) === 0 ? "0.0" : (v > 0 ? "+" : "") + s) + "bp";
  }
  function rate(name, r) {                                                // "국고 10년 4.376% (+0.7bp) 자료일 10-08"
    if (!isObj(r) || !Number.isFinite(r.value) || r.value <= 0 || r.value >= 20) return null;
    return el("span", { class: "eve-rate" }, name + " ", el("strong", {}, r.value.toFixed(3).replace(/0$/, "") + "%"),
      Number.isFinite(r.chg_bp) ? ` (${bp(r.chg_bp)})` : null, realDate(r.asof) ? el("small", {}, " 자료일 " + r.asof.slice(5)) : null);
  }
  // 금리 한 줄. 방향(약세·강세, 스팁·플랫)은 자료에 있을 때만 — 자료일이 수집 창과 안 맞으면 조립 단계가 비워 보낸다
  function ratesLine(head) {
    const h = isObj(head) ? head : {}, kr10 = rate("국고 10년", h.kr10), kr3 = rate("국고 3년", h.kr3), us10 = rate("미 10년", h.us10);
    if (!kr10 && !kr3 && !us10) return el("p", {}, "금리 자료 없음");
    const dir = [word(h.dir), word(h.curve)].filter(Boolean).join(" · "), basis = word(h.basis);
    const turn = kr10 || kr3
      ? el("span", { class: "eve-dir" }, dir ? "→ " + dir : "방향 표시 없음", basis ? el("small", {}, " " + basis) : null) : null;
    return el("p", { class: "eve-rates" }, kr10, kr3, turn, us10);
  }
  function topTerms(ctx, head) {
    const terms = list(isObj(head) ? head.top_terms : null).map(term).filter(Boolean).slice(0, 3);
    terms.forEach(t => ctx.used.add(t));
    return terms.length ? el("p", {}, "가장 많이 다뤄진 주제: ", el("strong", {}, terms.join(" · ")),
      el("small", {}, " (건수 기준 — 금리가 움직인 원인을 뜻하지 않습니다)")) : null;
  }
  function notes(raw) {
    const lines = list(raw).filter(t => { const code = phraseCode(t); return code && !QUIET_NOTES.includes(code); });
    return lines.length ? el("ul", { class: "eve-notes", "aria-label": "이 판의 알림" }, ...lines.map(t => el("li", {}, t))) : null;
  }
  // 지난 판 넘기기 — 최근 10영업일. 맨 앞(최신)은 "#evening", 나머지는 "#evening/<날짜>"
  function editionNav(index, shown) {
    const rows = list(isObj(index) ? index.editions : null).filter(e => isObj(e) && realDate(e.date))
      .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0)).slice(0, RULES.show_editions);
    if (!rows.length) return null;
    const latest = rows[0].date;
    return el("nav", { class: "eve-editions", "aria-label": "지난 판 넘기기" }, ...rows.map(e => {
      const tail = e.status === "short" ? "수집 부족" : e.status === "withdrawn" ? "내림" : count(e.must) === null ? "" : `꼭 ${e.must}`;
      const a = el("a", { href: e.date === latest ? "#evening" : "#evening/" + e.date }, md(e.date),
        tail ? el("small", {}, " " + tail) : null);
      if (e.date === shown) a.setAttribute("aria-current", "page");
      return a;
    }));
  }

  // ---------- 항목 ----------
  function cellName(cell) {                                               // {요인, 지역} → "펀더멘털 / 글로벌". 없으면 null(분류 보류)
    const factor = isObj(cell) ? word(cell.factor) : null, region = isObj(cell) ? word(cell.region) : null;
    if (!factor || !region) return null;
    return RULES.no_region.includes(factor) ? factor : `${factor} / ${region}`;
  }
  const cellTag = name => el("span", { class: name ? "eve-cell" : "eve-cell eve-hold" }, name || "분류 보류");
  function numRow(n) {
    const v = isObj(n) ? num(n.v) : null;
    return v ? { v, term: term(n.term), lead: [term(n.term), word(n.result)].filter(Boolean).join(" · "), n: count(n.n_ch) } : null;
  }
  function coverText(ctx, c) {                                            // "채권 3 · 애널 2 · 개인 3 · 속보형 1"
    if (!isObj(c)) return "";
    const rows = Object.keys(RULES.groups).map(g => [ctx.group[g], count(c[g])]).concat([[ctx.role.wire, count(c.wire)]]);
    return rows.filter(([, n]) => n).map(([name, n]) => `${name} ${n}`).join(" · ");
  }
  // 첫 글~마지막 글 → {text "10-07 21:32 ~ 10-08 09:00"(같은 날이면 뒤는 시각만), one(글 하나), posts}. 없거나 뒤집혔으면 null
  function spanOf(sp) {
    const a = isObj(sp) ? stamp(sp.from) : null, b = a ? stamp(sp.to) : null;
    if (!b || a.iso > b.iso) return null;
    const one = a.iso === b.iso;
    return { text: one ? a.text : `${a.text} ~ ${b.date === a.date ? b.text.slice(6) : b.text}`, one, posts: count(sp.posts) };
  }
  // 직전 판에 같은 대표 낱말이 있었을 때 — 그때와 이번의 채널 수(속보형은 뺀다). 같은 묶음이라는 뜻이 아니라 늘었다·줄었다고는 쓰지 않는다
  function prevOf(ctx, x) {
    const p = x.prev, c = x.coverage, text = o => coverText(ctx, { ...o, wire: 0 }) || "0곳";
    return isObj(p) && isObj(c) && realDate(p.date) ? { date: p.date, then: text(p), now: text(c) } : null;
  }
  // 꼭 볼 것·나머지 항목에서 화면에 쓸 것만 추린다. id가 이상하거나, 숨긴 항목이거나, 걸 수 있는 링크가 하나도 없으면 null.
  // 새 칸(words · span · prev · 링크의 more · size · pic)은 있으면 쓰고, 없거나 깨졌으면 그 칸만 비운다
  function item(ctx, x) {
    if (!isObj(x) || typeof x.id !== "string" || !ID_RE.test(x.id) || ctx.hide.ids.has(x.id)) return null;
    const links = list(x.links).filter(isObj).map(l => ({ ch: l.ch, url: l.url, node: source(ctx, l.ch, l.url), at: when(l.at),
      st: stamp(l.at), fwd: l.fwd === true, ...extras(l, 4) })).filter(l => l.node);
    if (!links.length) return null;
    const terms = list(x.terms).map(term).filter(Boolean).slice(0, 4), nums = list(x.nums).map(numRow).filter(Boolean).slice(0, 3);
    const words = list(x.words).map(w => (isObj(w) && term(w.term) && count(w.n_ch) ? { term: w.term, n: w.n_ch } : null))
      .filter(Boolean).slice(0, 16);
    const all = [...new Set([...terms, ...nums.map(n => n.term).filter(Boolean), ...words.map(w => w.term), ...links.flatMap(l => l.more)])];
    all.forEach(t => ctx.used.add(t));
    // head = 제목의 낱말: 대표 낱말(첫머리의 것), 없으면 본문에서 걸린 낱말 둘(body)
    const body = !terms.length, head = body ? all.slice(0, 2) : terms;
    return { raw: x, links, terms, nums, words, all, head, body, cell: cellName(x.cell), cover: coverText(ctx, x.coverage),
      span: spanOf(x.span), prev: quiet(() => prevOf(ctx, x)), ai: quiet(() => aiOf(ctx, x, links)) };
  }
  // 이 항목에 붙일 요약 {fact, n(읽힌 글 수)} — key가 같고, 읽힌 글이 모두 이 항목의 걸린 링크 가운데 채권·애널 원천 채널의 전달 아닌 글일 때만
  // (숨긴 채널 · 목록에 없는 채널의 글로 쓴 문장은 빠진다). 출처 목록을 못 읽었으면 붙이지 않는다 — 어느 채널의 글인지 견줄 수 없다
  function aiOf(ctx, x, links) {
    const p = ctx.picks.get(x.key), from = ch => (ctx.dir && ctx.dir.get(ch)) || {};
    const read = ([ch, n]) => from(ch).role === "source" && ["bond", "analyst"].includes(from(ch).group)
      && links.some(l => l.ch === ch && !l.fwd && l.url === `https://t.me/${ch}/${n}`);
    return p && p.src.every(read) ? { fact: p.fact, n: p.src.length } : null;
  }
  // AI 요약 한 토막 — 표시 · 틀릴 수 있다는 말 · 문장(텍스트 노드) · 읽힌 글 수. 카드에서는 한 문단, 나머지 줄(row)에서는 낱말 줄 아래에 작게
  function aiNote(ctx, it, row) {
    if (!it.ai) return null;
    ctx.ai += 1;
    return el(row ? "span" : "p", { class: row ? "eve-ai eve-ai-row" : "eve-ai" }, el("span", { class: "eve-ai-tag" }, "AI 요약"), " ",
      el("small", {}, "틀릴 수 있습니다 — 원문에서 확인하세요"), " ", el("span", { class: "eve-ai-text" }, it.ai.fact), " ",
      el("small", {}, `채권·애널 채널 글 ${it.ai.n}건을 읽고 씀`));
  }
  const items = (ctx, raw) => list(raw).map(x => quiet(() => item(ctx, x))).filter(Boolean);
  const termNodes = it => (it.head.length ? [it.body ? el("small", {}, "본문 낱말 ") : null, el("strong", {}, it.head[0]),
    it.head.length > 1 ? " · " + it.head.slice(1).join(" · ") : null] : ["사전 낱말 없음"]);
  const capt = (title, sub) => el("h4", { class: "eve-cap" }, title, sub ? el("small", {}, " " + sub) : null);

  // ---------- 낱말 풀이 ----------
  // 풀이의 몸통 — 풀이 글자(텍스트 노드)와, 허용 도메인일 때만 붙는 공식 자료 링크
  const kind = host => (host.startsWith("fred.") ? "시계열" : host.startsWith("fraser.") ? "문서 모음" : "공식 자료");
  const defBody = (g, t) => [g.text, g.link ? " " : null, g.link
    ? out(g.link.url, `${kind(g.link.host)} · ${g.link.host}`, `${t} ${kind(g.link.host)} · ${g.link.host} (새 창)`) : null];
  function defLine(ctx, t) {                                              // 낱말 하나의 풀이 한 줄(없으면 null)
    const g = t ? ctx.gloss.get(t) : null;
    return g ? el("p", { class: "eve-def" }, el("strong", {}, t), " ", ...defBody(g, t)) : null;
  }
  function defList(ctx, terms) {                                          // 낱말들 가운데 풀이가 있는 것 → {n, first, node}. 없으면 null
    const rows = terms.filter(t => ctx.gloss.has(t));
    return rows.length ? { n: rows.length, first: rows.slice(0, 3).join(" · "), node: el("dl", { class: "eve-defs" },
      ...rows.map(t => el("div", {}, el("dt", {}, t), el("dd", {}, ...defBody(ctx.gloss.get(t), t))))) } : null;
  }
  // 이 판의 낱말 풀이 — 화면에 나간 낱말의 것만, 사전에 실린 순서로. 접어 둔다
  function glossSection(ctx) {
    const got = defList(ctx, [...ctx.gloss.keys()].filter(t => ctx.used.has(t)));
    return got ? section("낱말 풀이", `이 판에 나온 낱말 가운데 ${got.n}개 — 이 사이트가 쓴 낱말의 뜻입니다(채널 글의 내용이 아닙니다)`,
      el("details", { class: "eve-fold" }, el("summary", {}, el("strong", {}, `풀이 ${got.n}개`), " 약어·지표 이름의 뜻과 공식 자료",
        el("small", {}, got.first + (got.n > 3 ? " …" : ""))), got.node)) : null;
  }

  // ---------- 꼭 볼 것 ----------
  function mustSection(ctx, d) {
    const shown = items(ctx, d.must), n = shown.length, lost = list(d.must).length - n;
    const sub = n >= 3 ? "여러 곳이 함께 다룬 묶음 가운데 기준을 모두 넘은 것"
      : n ? `${P.note_fewer.replace("{n}", n)} — 기준을 넘은 묶음만 싣습니다` : null;
    const why = d.status === "short" ? P.note_short : lost ? "표시할 수 있는 항목이 없습니다" : P.note_none;
    const where = d.status === "ok" && !lost ? " 아래 '채권 채널 단독 글'과 '나머지'에서 채널들이 쓴 낱말을 볼 수 있습니다." : "";
    return section(n ? `꼭 ${n}건` : "꼭 볼 것", sub,
      n ? el("ol", { class: "eve-must" }, ...shown.map((it, i) => el("li", {}, mustCard(ctx, it, i + 1))))
        : el("p", { class: "empty-state" }, why + "." + where),
      lost > 0 ? el("p", { class: "reading-note" }, `표시하지 않은 항목 ${lost}건 — 숨김 목록에 있거나 자료의 형식이 맞지 않습니다.`) : null,
      el("p", { class: "eve-note" }, CARD_NOTE + (ctx.ai ? AI_NOTE : "")));   // 카드 뒤에 — 폰 첫 화면에 카드의 제목이 들어오게
  }
  // 고정 틀에 값을 끼운 한 문장 — "채권 채널 4곳이 함께 다뤘습니다." + 작게 "묶인 글 7건 · 10-08 05:44 ~ 10:12"(값은 채널 수·글 수·시각뿐).
  // 시각 범위는 묶인 글(속보형·전달 포함)의 것이라 문장 밖에 적는다
  function lede(ctx, it) {
    const c = isObj(it.raw.coverage) ? it.raw.coverage : {}, sp = it.span, wire = count(c.wire);
    const rows = Object.keys(RULES.groups).map(g => [ctx.group[g], count(c[g])]).filter(([, n]) => n);
    if (!rows.length) return null;
    const who = rows.length > 1 ? rows.map(([name, n]) => `${name} ${n}곳`).join(" · ") : `${rows[0][0]} 채널 ${rows[0][1]}곳`;
    const many = rows.reduce((n, [, k]) => n + k, 0) > 1, posts = sp && sp.posts ? `묶인 글 ${sp.posts}건 · ` : null;
    return el("p", { class: "eve-lede" }, el("strong", {}, who), "이 ", many ? "함께 다뤘습니다." : "다뤘습니다.",
      posts || wire ? el("small", {}, " ", posts, posts ? el("span", { class: "eve-when" }, sp.text) : null,
        wire ? `${posts ? " · " : ""}${ctx.role.wire} ${wire}곳 겹침` : null) : null);
  }
  // 함께 나온 낱말과 곳 수 — 자료의 순서(곳 수 → 등급 → 가나다) 그대로. 막대는 곳 수만큼의 칸이고 화면 읽기에는 숫자만 읽힌다(좁으면 감춘다)
  function wordBars(words) {
    if (!words.length) return null;
    const pips = n => el("span", { class: "eve-pips", "aria-hidden": "true" },
      ...Array.from({ length: Math.min(n, PIPS) }, () => el("span", { class: "eve-pip" })));
    return el("div", { class: "eve-words" }, capt("함께 나온 낱말", "그 낱말을 쓴 채널 수 · 제목의 낱말과 전달 글은 빼고 셈"),
      el("ol", {}, ...words.map(w => el("li", {}, el("span", { class: "eve-w" }, w.term), pips(w.n),
        el("span", { class: "eve-n" }, el("strong", {}, String(w.n)), "곳")))));
  }
  // 출처 줄 — 채널 · 시각 · 길이 · 붙은 것 · 낱말 수 · 전달, 그리고 이 글에만 더 있는 낱말(어느 글을 누를지 고를 수 있게).
  // 그런 낱말이 없으면 '공통 낱말만'(제목의 낱말과 여러 곳이 함께 쓴 낱말뿐인 글)
  const linkRow = l => el("li", {}, l.node, l.at ? " " : null, l.at, ...tagNodes(l),
    l.fwd ? el("span", { class: "eve-tag eve-fwd" }, "전달") : null,
    l.more.length ? el("span", { class: "eve-more" }, "이 글에서 더:\u00a0", el("b", {}, l.more.join(" · ")))
      : l.n ? el("span", { class: "eve-tag" }, "공통 낱말만") : null);
  function glossFold(ctx, it) {                                           // 카드에 나온 나머지 낱말의 풀이 — 접어 둔다
    const lead = it.terms[0], got = defList(ctx, it.all.filter(t => t !== lead));
    return got ? el("details", { class: "eve-gloss" }, el("summary", {}, ctx.gloss.has(lead) ? "다른 낱말 풀이 " : "낱말 풀이 ",
      el("strong", {}, `${got.n}개`), " · " + got.first), got.node) : null;
  }
  // 카드 안은 세 토막 — 주제 → 원문 링크 → 함께 나온 낱말 · 고른 이유 · 접어 둔 것. 넓으면 나란히, 좁으면 이 순서로 쌓인다
  function mustCard(ctx, it, rank) {
    const why = list(it.raw.why).filter(phraseCode).slice(0, 4), p = it.prev, sp = it.span;
    const rich = it.links.some(l => l.size || l.pic || l.more.length);        // 옛 판에는 고를 거리가 없다 — 안내도 붙이지 않는다
    const some = sp && sp.posts > it.links.length ? `채널마다 한 글 · 묶인 글 ${sp.posts}건 중 ${it.links.length}건` : null;
    return el("article", { class: "eve-item" },
      el("div", { class: "eve-item-head" }, el("span", { class: "eve-rank", "aria-hidden": "true" }, String(rank)), cellTag(it.cell)),
      el("div", { class: "eve-cols" }, el("div", {},
        el("h3", { class: "eve-terms" }, ...termNodes(it)), quiet(() => lede(ctx, it)), aiNote(ctx, it), defLine(ctx, it.terms[0]),
        p ? el("p", { class: "eve-prev" }, `대표 낱말이 직전 판 ${md(p.date)}에도 있었습니다 — 그때 ${p.then} → 이번 ${p.now} `,
          el("small", {}, "(낱말이 같을 뿐 같은 묶음이 아닐 수 있습니다)")) : null,
        it.nums.length ? el("ul", { class: "eve-nums", "aria-label": "두 곳 이상이 똑같이 쓴 숫자" }, ...it.nums.map(n => el("li", {},
          n.lead ? el("span", {}, n.lead + " · ") : null, el("strong", {}, n.v), n.n ? el("small", {}, ` ${n.n}곳`) : null))) : null),
      el("div", {}, capt("원문 링크", [some, rich ? "길이·낱말 수를 보고 고르세요" : null].filter(Boolean).join(" — ")),
        el("ul", { class: "eve-links" }, ...it.links.map(linkRow))),
      el("div", {}, wordBars(it.words),
        why.length ? capt("고른 이유", "규칙이 센 것 — 방향·강도가 아닙니다") : null,
        why.length ? el("ul", { class: "eve-why" }, ...why.map(t => el("li", {}, t))) : null,
        quiet(() => glossFold(ctx, it)), quiet(() => scoreFold(it.raw.score)))));
  }
  // 규칙 점수 — 여러 곳이 함께 다뤘는지를 센 값이다(방향·강도가 아니다). 접어 둔다
  function scoreFold(s) {
    if (!isObj(s) || !Number.isFinite(s.total)) return null;
    const show = v => String(Math.round(v * 1000) / 1000);
    const rows = SCORE_PARTS.filter(([k]) => Number.isFinite(s[k]) && (s[k] !== 0 || "CXKE".includes(k)))
      .map(([k, name]) => el("div", {}, el("dt", {}, name), el("dd", {}, (k === "P" && s[k] ? "-" : "") + show(s[k]))));
    return el("details", { class: "eve-score" }, el("summary", {}, "규칙 점수 ", el("strong", {}, show(s.total)), " · 항별 보기"),
      el("dl", {}, ...rows), el("p", {}, "여러 곳이 함께 다뤘는지를 센 값입니다. 금리의 방향이나 강도가 아닙니다."));
  }

  // ---------- 내일 볼 것 · 나머지 · 채권 단독 ----------
  function tomorrowSection(ctx, d) {
    const rows = list(d.tomorrow).map(e => quiet(() => dayRow(ctx, e))).filter(Boolean);
    return rows.length ? section("다가오는 일정", "발표·입찰 — 수집이 끝난 뒤의 오늘 일정부터", el("ul", { class: "eve-rows eve-boxed" }, ...rows))
      : null;
  }
  function dayRow(ctx, e) {
    if (!isObj(e) || !realDate(e.date) || !term(e.term)) return null;
    ctx.used.add(e.term);
    const detail = list(e.detail).map(x => word(x) || num(x)).filter(Boolean).join(" · ");
    return el("li", {}, el("time", { datetime: e.date }, md(e.date) + (hhmm(e.time, "") ? " " + e.time : "")),
      el("span", { class: "eve-main" }, el("strong", {}, e.term), detail ? " · " + detail : null),
      e.tier === "A" || e.tier === "B" ? el("span", { class: "eve-badge" }, e.tier + "급") : null,
      own(RULES.src, e.src) ? el("span", { class: "eve-meta" }, RULES.src[e.src]) : null);
  }
  // 채권 채널 한 곳만 쓴 글은 나머지 표에서 따로 떼어 보여 준다
  const bondAlone = it => { const c = it.raw.coverage; return isObj(c) && c.bond === 1 && !c.analyst && !c.personal; };
  function restGroups(ctx, d) {
    return list(d.rest).filter(isObj).map(g => ({ cell: word(g.cell), items: items(ctx, g.items) })).filter(g => g.items.length);
  }
  // 한 곳만 쓴 줄인가(링크 하나, 낱말은 모두 1곳) — 그 글의 낱말을 한 줄로 합쳐 적는다
  const lone = it => it.links.length === 1 && !it.words.some(w => w.n > 1);
  // 나머지 줄의 출처 하나 — 채널 · 시각, 작게 전달 · 길이 · 붙은 것 · 낱말 수 · 더 있는 낱말(한 곳만 쓴 줄은 낱말 줄에 합쳤다)
  // skip = 줄의 제목에 이미 쓴 낱말(본문 낱말로 부른 것) — 링크마다 되풀이하지 않는다
  function rowLink(l, merged, skip) {
    const more = merged ? [] : l.more.filter(t => !(skip || []).includes(t));
    return el("span", { class: "eve-src" }, l.node, l.at ? " " : null, l.at,
      ...[l.fwd ? "전달" : null, ...tags(l), more.length ? "더:\u00a0" + more.join(" · ") : null].filter(Boolean)
        .map(t => el("small", {}, " · " + t)));
  }
  // 줄의 낱말 한 줄 — 여러 곳이 쓴 묶음은 "함께 나온 낱말: X 2곳 · …", 한 곳만 쓴 글은 "이 글의 낱말: …"(제목의 낱말은 빼고 6개까지)
  function wordsNote(it) {
    const rows = lone(it) ? it.all.filter(t => !it.head.includes(t)).slice(0, 6) : it.words.map(w => `${w.term} ${w.n}곳`);
    return rows.length ? el("span", { class: "eve-sub" }, lone(it) ? "이 글의 낱말: " : "함께 나온 낱말: ", rows.join(" · ")) : null;
  }
  function restRow(ctx, it, withCell) {
    const n = it.nums[0], s = it.raw.s, sp = it.span;
    return el("li", {},
      el("span", { class: "eve-main" }, withCell ? cellTag(it.cell) : null, withCell ? " " : null, ...termNodes(it)),
      n ? el("span", { class: "eve-v" }, n.lead ? n.lead + " " : null, el("strong", {}, n.v)) : null,
      it.cover ? el("span", { class: "eve-meta" }, it.cover) : null,
      Number.isFinite(s) ? el("span", { class: "eve-meta" }, `점수 ${Math.round(s * 100) / 100}`) : null,
      sp && sp.posts > 1 ? el("span", { class: "eve-meta" }, `글 ${sp.posts}건 · ${sp.text}`) : null,
      it.prev ? el("span", { class: "eve-meta" }, `대표 낱말이 직전 판 ${md(it.prev.date)}에도 있음`) : null,
      wordsNote(it), aiNote(ctx, it, true), el("span", { class: "eve-row-links" }, ...it.links.map(l => rowLink(l, lone(it), it.head))));
  }
  function restSection(ctx, d) {
    const groups = restGroups(ctx, d).map(g => ({ ...g, items: g.items.filter(it => !bondAlone(it)) })).filter(g => g.items.length);
    const total = groups.reduce((n, g) => n + g.items.length, 0), cut = count(isObj(d.funnel) ? d.funnel.truncated : null);
    if (!total) return null;
    const fold = total > UNFOLD ? { class: "eve-fold" } : { class: "eve-fold", open: "" };       // 몇 줄 안 되면 펼쳐 둔다
    return section("나머지", `${total}줄 · 분류 칸별` + (total > UNFOLD ? "로 접혀 있습니다" : ""), ...groups.map(g => el("details", fold,
      el("summary", {}, el("strong", {}, g.cell || "분류 보류"), ` ${g.items.length}줄`,
        el("small", {}, g.items.map(it => it.terms[0]).filter(Boolean).slice(0, 3).join(" · "))),
      el("ul", { class: "eve-rows" }, ...g.items.map(it => restRow(ctx, it, false))))),
      cut ? el("p", { class: "reading-note" }, P.note_truncated.replace("{n}", cut) + ".") : null);
  }
  // 채권 채널 한 곳만 쓴 글 한 줄 — 시각 · 칸 · 낱말 · 꼬리표 · 원문(채널 이름은 묶음의 머리에 한 번만)
  function bondRow(ctx, it) {
    const l = it.links[0], name = `${ctx.label(l.ch)} 원문${l.st ? " " + l.st.text : ""}`;
    return el("li", {}, l.at, el("span", { class: "eve-main" }, cellTag(it.cell), " ", ...termNodes(it), ...tagNodes(l)),
      it.prev ? el("span", { class: "eve-meta" }, `대표 낱말이 직전 판 ${md(it.prev.date)}에도 있음`) : null, wordsNote(it),
      source(ctx, l.ch, l.url, "원문", name));
  }
  // 사전 낱말이 하나도 없는 글만 한데 접는다(첫머리에 없어도 본문에 있으면 '본문 낱말'로 보여 준다)
  function bondSection(ctx, d) {
    const alone = restGroups(ctx, d).flatMap(g => g.items.filter(bondAlone));
    const named = alone.filter(it => it.head.length), bare = alone.filter(it => !it.head.length);
    const iso = it => (it.links[0].st ? it.links[0].st.iso : ""), early = (a, b) => (iso(a) > iso(b) ? 1 : iso(a) < iso(b) ? -1 : 0);
    const mine = ch => named.filter(it => it.links[0].ch === ch).sort(early);       // 채널 안에서는 올린 시각순
    return alone.length ? section("채권 채널 단독 글", "채권 채널 한 곳만 쓴 글 — 채널별로, 낱말과 링크만",
      ...[...new Set(named.map(it => it.links[0].ch))].map(ch => el("div", { class: "eve-side-ch" },
        el("p", {}, el("strong", {}, ctx.label(ch)), ` ${mine(ch).length}건`),
        el("ul", { class: "eve-rows" }, ...mine(ch).map(it => bondRow(ctx, it))))),
      bare.length ? el("details", { class: "eve-fold" }, el("summary", {}, el("strong", {}, `사전 낱말이 없는 글 ${bare.length}건`), " 링크만"),
        el("ul", { class: "eve-rows" }, ...bare.map(it => el("li", {}, el("span", { class: "eve-main" }, ...it.links.map(l => rowLink(l))))))) : null)
      : null;
  }

  // ---------- 속보형 · 개인 단독 · 참고 ----------
  // 혼자 쓴 글 한 줄 — 낱말(굵게) · (있으면) 숫자 · 그 글의 다른 낱말(자료의 순서 = 등급순) · 길이 · 붙은 것 · 원문.
  // 숫자 칸이 비어 있으면(v null) 숫자 없는 줄이고, 숫자가 아닌 것이 들었으면 줄째 뺀다(숫자 없는 줄로 살리지 않는다)
  function sideRow(ctx, r) {
    if (!isObj(r) || (r.v !== null && r.v !== undefined && !num(r.v))) return null;
    const v = num(r.v), lead = term(r.term), at = lead ? stamp(r.at) : null;
    const link = lead ? source(ctx, r.ch, r.url, "원문", `${ctx.label(r.ch)} 원문${at ? " " + at.text : ""}`) : null;
    if (!link) return null;
    const x = extras(r, 2);
    [lead, ...x.more].forEach(t => ctx.used.add(t));
    return { ch: r.ch, node: el("li", {}, when(r.at), el("span", { class: "eve-main" },
      el("b", {}, [lead, v ? word(r.result) : null].filter(Boolean).join(" · ")), v ? " " : null, v ? el("strong", {}, v) : null,
      x.more.length ? el("small", {}, " · " + x.more.join(" · ")) : null,
      ...tagNodes(x, 1 + x.more.length)), link) };
  }
  function sideBlock(ctx, side, title, note) {
    if (!isObj(side)) return null;
    const rows = list(side.rows).map(r => quiet(() => sideRow(ctx, r))).filter(Boolean);
    const chans = list(side.channels).filter(c => isObj(c) && isHandle(c.ch) && count(c.read) !== null && !ctx.hide.chans.has(c.ch)
      && (!ctx.dir || ctx.dir.has(c.ch)));
    if (!chans.length) return null;
    const mine = c => rows.filter(r => r.ch === c.ch).map(r => r.node);
    const loud = chans.filter(c => mine(c).length), still = chans.filter(c => !mine(c).length);
    const more = c => [count(c.joined) === null ? null : `다른 채널과 겹친 글 ${c.joined}`,
      count(c.hit) === null ? null : `조건에 맞은 단독 글 ${c.hit}`].filter(Boolean).join(" · ");
    return el("div", { class: "eve-side" }, el("h3", {}, title), note ? el("p", { class: "eve-quiet" }, note) : null,
      ...loud.map(c => el("div", { class: "eve-side-ch" },
        el("p", {}, el("strong", {}, ctx.label(c.ch)), ` ${c.read}건 중 ${mine(c).length}건`, more(c) ? el("small", {}, " · " + more(c)) : null),
        el("ul", { class: "eve-rows" }, ...mine(c)))),
      still.length ? el("p", { class: "eve-quiet" }, "줄 없이 건수만: " + still.map(c => `${ctx.label(c.ch)} ${c.read}건`).join(" · ")) : null);
  }
  function sideSection(ctx, d) {
    const searched = `건수는 하루 전체가 아니라 검색어 '${RULES.wire_query}'에 걸린 글 수입니다.`;
    const blocks = [quiet(() => sideBlock(ctx, d.wire, "속보형 채널", searched)), quiet(() => sideBlock(ctx, d.solo, "개인 채널"))]
      .filter(Boolean);
    return blocks.length ? section("속보형·개인 채널이 혼자 쓴 글",
      `첫 두 줄에 사전 낱말이 있는 글(A·B급 낱말이 있거나 낱말이 둘 이상인 글)을 채널당 ${RULES.rows_per_channel}줄까지, 나머지는 건수만 — ` +
        "낱말은 그 글에 나온 것을 등급순으로 놓았고, 숫자가 붙은 줄은 한 곳만 쓴 숫자입니다",
      ...blocks) : null;
  }
  function contextSection(ctx, d) {
    const rows = list(d.context).filter(isObj).map(x => ({ link: source(ctx, x.ch, x.url), at: when(x.at) })).filter(r => r.link)
      .map(r => el("li", {}, r.at, el("span", { class: "eve-main" }, r.link)));
    return rows.length ? section("참고 링크", "점수에 넣지 않는 시황 채널의 글", el("ul", { class: "eve-rows eve-boxed" }, ...rows)) : null;
  }

  // ---------- 출처와 수집 방식 ----------
  function channelList(ctx, status) {
    if (!ctx.dir) return el("p", {}, "출처 목록을 읽지 못했습니다.");
    const health = new Map(list(status && status.channels).filter(c => isObj(c) && isHandle(c.ch)).map(c => [c.ch, c]));
    const state = h => (!h ? "" : h.ok === false ? ` · 이번 판에서 읽지 못함(${codeText(h.code)})`
      : count(h.in_window) === null ? "" : ` · 창 안 글 ${h.in_window}건`);
    const row = c => el("li", {}, out("https://t.me/" + c.handle, c.label), " ",
      el("small", {}, (own(ctx.role, c.role) ? ctx.role[c.role] : "") + state(health.get(c.handle))));
    const all = [...ctx.dir.values()].filter(c => !ctx.hide.chans.has(c.handle));
    return el("div", {}, ...Object.keys(RULES.groups).map(g => [g, all.filter(c => c.group === g)]).filter(([, cs]) => cs.length)
      .flatMap(([g, cs]) => [el("h4", {}, `${ctx.group[g]} ${cs.length}곳`), el("ul", { class: "eve-chans" }, ...cs.map(row))]));
  }
  function about(ctx, m) {
    const d = m.digest, status = isObj(m.status) && d && m.status.edition === d.date ? m.status : null;
    return el("details", { class: "eve-about" }, el("summary", {}, "출처와 수집 방식"),
      el("h3", {}, "수집 방식"), ...HOW.map(t => el("p", {}, t)),
      el("h3", {}, "삭제·정정 요청"),
      el("p", {}, "채널 운영자가 요청하면 그 채널을 목록에서 내립니다. 잘못 실린 것이 있으면 알려 주세요 — ", out(TAKEDOWN, "GitHub 이슈로 요청하기")),
      el("h3", {}, "채널 목록"), part(() => channelList(ctx, status)));
  }

  return { setView, _: { editionOf, dueEdition, judge, num, word, term, label, phraseCode, official, fingerprint, fact } };
})();
