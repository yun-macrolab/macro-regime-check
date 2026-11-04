/* 연준 인물 페이지(people.html)의 자료 — 사람이 고친다(자동 갱신 없음, 기준일 asof).
 * 사실·출처는 인물별 조사에서, 위치 눈금·흐름은 운영자 해석, 지도(map)는 미리 계산한 주 경계 그림.
 * 고칠 때: scripts/test_people_site.py가 꼴(사람 수·칸·범위·출처 주소)을 본다. */
window.PEOPLE_DATA = {
 "asof": "2026-11-04",
 "review": "draft",
 "notes": [
  "초안이 섞여 있다 — 2026년 투표권자 12명(워시·제퍼슨·보먼·월러·바·쿡·파월·윌리엄스·폴슨·해맥·카시카리·로건)의 기준선과 사실은 2026-11-04 1차 출처(연준·뉴욕 연은 원문은 직접, 지역 연은 원문은 검색 조각)로 다시 확인해 운영자가 승인했다(사람마다 ‘확인함’). 나머지 7명은 아직 초안이다(‘초안’) — 그쪽 1차 자료는 제3자 사본·검색 조각이고, 나머지는 2차 보도다.",
  "사실은 인물별 조사와 2026 회의 기록에서만 옮겼다. 장소의 도시·좌표와 연준 지구 경계만 일반 지식(대략값)이다.",
  "진영 꼬리표(매파·중도·비둘기·스윙·미상)는 언론·관찰자가 붙인 평판을 줄인 것이고 계산값이 아니다. 그런 라벨이 없으면 미상.",
  "기준선(평소·놀랄 일)과 ‘다음 확인’은 운영자가 조사에서 정리한 것이다(2026 투표권자 12명은 확인함, 나머지는 초안) — 예측이 아니라 새 발언을 견줄 틀이다. 목록 항목은 지우거나 순서를 바꾸지 않고, 고칠 때는 그 자리에서 고치거나 끝에 더한다.",
  "위치 눈금(−2 비둘기 … +2 매파)과 올해의 흐름·위치 근거는 운영자 해석이다. 빈 칸은 판단할 수 없다는 뜻이다(베너블·데일리 — 2026 금리 발언 없음).",
  "지구는 주 단위 근사다 — 실제로는 나뉜 주(CT·NJ·PA·KY·WV·TN·MS·LA·IL·IN·MI·WI·MO·NM)를 한 지구에 통째로 넣었다. 지구마다 근사 설명이 붙어 있다.",
  "걸어온 길의 좌표는 캠퍼스·본사 도시의 대략값이다. ‘위치 추정’은 조사에 장소가 없어 추정한 점(나라 중심 포함)이고, 연도가 빈 칸은 조사에 연도가 없는 것이다. ‘사전 지식’ 표시는 확인하지 않은 것이다.",
  "인용 문구는 조사에 옮겨진 그대로다 — 2차 보도가 옮긴 것이면 원문과 다를 수 있다. 2026 투표권자 12명의 인용은 2026-11-04 원문(또는 검색 조각)과 다시 맞췄다.",
  "애틀랜타는 임시 총재(베너블)이고 정식 후임은 발표 전이다(10-31 기준). 마이런(전 이사)은 반대표 기록에만 나온다.",
  "글은 이 저장소가 공개 자료(연준·연은 자료 — 사본·검색 조각 포함, 보도)를 읽고 쓴 요약이다. 인용은 짧게, 같은 날짜의 출처와 함께 싣는다. 사람 사진·기관 로고는 싣지 않는다.",
  "지도의 주 경계는 folium 예제 자료(us-states.json, MIT 라이선스 — 저작권 표시는 저장소의 THIRD_PARTY_NOTICES.md)를 앨버스 투영으로 미리 계산한 그림이다.",
  "‘새 발언 — 기준선 대비(자동 분류)’ 칸과 머리의 최근 발언 띠만 매일 자동으로 붙는다 — 언어 모델(AI)이 기사를 읽고 새 발언을 그 사람의 기준선(기준일·확인함/초안 표시)에 견준 결과이고, 사람 확인 없이 매일 올라간다. 틀릴 수 있고, 예측이 아니다. 인용은 언어 모델이 기사에서 발언자 본인의 말로 보고 15단어 이내로 옮긴 것이다. 위의 프로필 칸은 사람이 고친다.",
  "참고 — 예측 아님. 이 사이트의 규칙 판정·점검표에 쓰지 않는다. 프로필 칸은 매일 갱신하지 않는다(머리의 기준일을 본다) — 매일 붙는 것은 자동 분류 칸뿐이다."
 ],
 "stance_scale": {
  "min": -2,
  "max": 2,
  "step": 0.5,
  "labels": {
   "-2": "강한 비둘기(인하 쪽 반대표·인하 요구)",
   "-1": "인하 쪽 기울기",
   "0": "현 금리 유지가 기본",
   "1": "추가 인상이 기본 시나리오",
   "2": "강한 매파(인상 쪽 반대표 반복·즉시 인상 요구)"
  },
  "basis": "운영자 해석 — 인물별 기준선과 관찰자 평판을 읽은 것, 계산값 아님"
 },
 "camp_note": "진영 꼬리표는 2026-10 기준 언론·관찰자 라벨의 요약이다. 라벨을 붙인 보도는 꼬리표에 마우스를 올리면 보이고 출처 목록에도 있다. 그런 보도를 못 찾은 라벨은 ‘사전 지식’, 라벨이 없으면 미상.",
 "board": {
  "name": "Board of Governors of the Federal Reserve System",
  "name_ko": "연준 이사회",
  "city": "Washington, DC",
  "lat": 38.8929,
  "lon": -77.0459
 },
 "districts": [
  {
   "n": 1,
   "bank": "Federal Reserve Bank of Boston",
   "bank_ko": "보스턴 연은",
   "city": "Boston, MA",
   "lat": 42.3523,
   "lon": -71.0553,
   "states": [
    "CT",
    "MA",
    "ME",
    "NH",
    "RI",
    "VT"
   ],
   "president_key": "collins",
   "approx": "CT 페어필드 카운티는 실제 2지구"
  },
  {
   "n": 2,
   "bank": "Federal Reserve Bank of New York",
   "bank_ko": "뉴욕 연은",
   "city": "New York, NY",
   "lat": 40.7083,
   "lon": -74.0087,
   "states": [
    "NY",
    "NJ"
   ],
   "president_key": "williams",
   "approx": "NJ는 북부만 실제 2지구(남부는 3지구), 푸에르토리코·USVI 포함"
  },
  {
   "n": 3,
   "bank": "Federal Reserve Bank of Philadelphia",
   "bank_ko": "필라델피아 연은",
   "city": "Philadelphia, PA",
   "lat": 39.9526,
   "lon": -75.1503,
   "states": [
    "PA",
    "DE"
   ],
   "president_key": "paulson",
   "approx": "실제로는 PA 동·중부와 NJ 남부, PA 서부는 4지구"
  },
  {
   "n": 4,
   "bank": "Federal Reserve Bank of Cleveland",
   "bank_ko": "클리블랜드 연은",
   "city": "Cleveland, OH",
   "lat": 41.5025,
   "lon": -81.69,
   "states": [
    "OH"
   ],
   "president_key": "hammack",
   "approx": "실제로는 PA 서부·KY 동부·WV 북부 일부도 4지구"
  },
  {
   "n": 5,
   "bank": "Federal Reserve Bank of Richmond",
   "bank_ko": "리치먼드 연은",
   "city": "Richmond, VA",
   "lat": 37.5374,
   "lon": -77.4337,
   "states": [
    "VA",
    "MD",
    "NC",
    "SC",
    "WV",
    "DC"
   ],
   "president_key": "barkin",
   "approx": "WV 북부 일부는 실제 4지구"
  },
  {
   "n": 6,
   "bank": "Federal Reserve Bank of Atlanta",
   "bank_ko": "애틀랜타 연은",
   "city": "Atlanta, GA",
   "lat": 33.7816,
   "lon": -84.3871,
   "states": [
    "GA",
    "FL",
    "AL",
    "TN",
    "LA",
    "MS"
   ],
   "president_key": "venable",
   "approx": "TN 서부·MS 북부는 실제 8지구, LA 북부는 11지구"
  },
  {
   "n": 7,
   "bank": "Federal Reserve Bank of Chicago",
   "bank_ko": "시카고 연은",
   "city": "Chicago, IL",
   "lat": 41.8789,
   "lon": -87.6324,
   "states": [
    "IL",
    "IN",
    "IA",
    "MI",
    "WI"
   ],
   "president_key": "goolsbee",
   "approx": "IL·IN 남부는 실제 8지구, MI 어퍼반도·WI 북서부는 9지구"
  },
  {
   "n": 8,
   "bank": "Federal Reserve Bank of St. Louis",
   "bank_ko": "세인트루이스 연은",
   "city": "St. Louis, MO",
   "lat": 38.629,
   "lon": -90.188,
   "states": [
    "MO",
    "AR",
    "KY"
   ],
   "president_key": "musalem",
   "approx": "MO 서부는 실제 10지구, KY 동부는 4지구. IL·IN 남부·TN 서부·MS 북부는 8지구"
  },
  {
   "n": 9,
   "bank": "Federal Reserve Bank of Minneapolis",
   "bank_ko": "미니애폴리스 연은",
   "city": "Minneapolis, MN",
   "lat": 44.9846,
   "lon": -93.269,
   "states": [
    "MN",
    "MT",
    "ND",
    "SD"
   ],
   "president_key": "kashkari",
   "approx": "실제로는 WI 북서부·MI 어퍼반도도 9지구"
  },
  {
   "n": 10,
   "bank": "Federal Reserve Bank of Kansas City",
   "bank_ko": "캔자스시티 연은",
   "city": "Kansas City, MO",
   "lat": 39.0758,
   "lon": -94.5867,
   "states": [
    "CO",
    "KS",
    "NE",
    "OK",
    "WY",
    "NM"
   ],
   "president_key": "schmid",
   "approx": "실제로는 MO 서부도 10지구, NM 남부는 11지구"
  },
  {
   "n": 11,
   "bank": "Federal Reserve Bank of Dallas",
   "bank_ko": "댈러스 연은",
   "city": "Dallas, TX",
   "lat": 32.7884,
   "lon": -96.7967,
   "states": [
    "TX"
   ],
   "president_key": "logan",
   "approx": "실제로는 LA 북부·NM 남부도 11지구"
  },
  {
   "n": 12,
   "bank": "Federal Reserve Bank of San Francisco",
   "bank_ko": "샌프란시스코 연은",
   "city": "San Francisco, CA",
   "lat": 37.793,
   "lon": -122.399,
   "states": [
    "AK",
    "AZ",
    "CA",
    "HI",
    "ID",
    "NV",
    "OR",
    "UT",
    "WA"
   ],
   "president_key": "daly",
   "approx": "괌·아메리칸사모아·북마리아나 포함"
  }
 ],
 "meetings_2026": [
  {
   "first_day": "2026-01-27",
   "date": "2026-01-28",
   "decision": "동결 3.50~3.75%",
   "vote": "10-2",
   "dissents": [
    {
     "key": "miran",
     "side": "인하"
    },
    {
     "key": "waller",
     "side": "인하"
    }
   ],
   "note": "의장 파월. 마이런·월러 25bp 인하 주장 [1차 성명 검색 조각]",
   "chair": "powell"
  },
  {
   "first_day": "2026-03-17",
   "date": "2026-03-18",
   "decision": "동결 3.50~3.75%",
   "vote": "11-1",
   "dissents": [
    {
     "key": "miran",
     "side": "인하"
    }
   ],
   "note": "월러는 유가 위험으로 동결 쪽. 점도표 중간값 2026년 1회 인하 [2차]",
   "chair": "powell"
  },
  {
   "first_day": "2026-04-28",
   "date": "2026-04-29",
   "decision": "동결 3.50~3.75%",
   "vote": "8-4",
   "dissents": [
    {
     "key": "miran",
     "side": "인하"
    },
    {
     "key": "hammack",
     "side": "문구"
    },
    {
     "key": "kashkari",
     "side": "문구"
    },
    {
     "key": "logan",
     "side": "문구"
    }
   ],
   "note": "1992년 이후 최다 반대. 해맥·카시카리·로건은 완화 편향 문구에 반대. 파월 마지막 의장 회의",
   "chair": "powell"
  },
  {
   "first_day": "2026-06-16",
   "date": "2026-06-17",
   "decision": "동결 3.50~3.75%",
   "vote": "12-0",
   "dissents": [],
   "note": "워시 첫 회의. 성명 축약·완화 편향 삭제, 점도표 2026 중간값 3.8%(인상 쪽) [성명·의사록 1차: 12-0]",
   "chair": "warsh"
  },
  {
   "first_day": "2026-07-28",
   "date": "2026-07-29",
   "decision": "동결 3.50~3.75%",
   "vote": "9-3",
   "dissents": [
    {
     "key": "hammack",
     "side": "인상"
    },
    {
     "key": "kashkari",
     "side": "인상"
    },
    {
     "key": "logan",
     "side": "인상"
    }
   ],
   "note": "2016년 이후 같은 방향 최다 반대 [2차]",
   "chair": "warsh"
  },
  {
   "first_day": "2026-09-15",
   "date": "2026-09-16",
   "decision": "인상 +25bp → 3.75~4.00%",
   "vote": "12-0",
   "dissents": [],
   "note": "2023년 이후 첫 인상. 점 낸 18명 중 16명이 연내 한 번 더 [2차]",
   "chair": "warsh"
  },
  {
   "first_day": "2026-10-27",
   "date": "2026-10-28",
   "decision": "동결 3.75~4.00%",
   "vote": "10-2",
   "dissents": [
    {
     "key": "cook",
     "side": "인상"
    },
    {
     "key": "hammack",
     "side": "인상"
    }
   ],
   "note": "쿡 첫 반대. 성명 'solid'→'strong', FOMC 일정 개편 발표 [2차]",
   "chair": "warsh"
  },
  {
   "first_day": "2026-12-08",
   "date": "2026-12-09",
   "decision": "예정",
   "vote": null,
   "dissents": [],
   "note": "점도표 포함 [2차 일정]",
   "chair": "warsh"
  }
 ],
 "events_2026": [
  {
   "date": "2026-02-28",
   "text": "미·이스라엘-이란 전쟁 시작, 호르무즈 사실상 봉쇄 → 유가 약 70→100달러",
   "keys": [],
   "src": [],
   "cert": "2차"
  },
  {
   "date": "2026-05-13",
   "text": "상원, 워시 의장 인준 54-45(이사 인준 05-12 51-45)",
   "keys": [
    "warsh"
   ],
   "src": [
    {
     "outlet": "Orrick InfoBytes",
     "date": "2026-05-15",
     "url": "https://infobytes.orrick.com/2026-05-15/u-s-senate-confirms-kevin-warsh-to-serve-as-fed-chair/"
    }
   ],
   "cert": "2차"
  },
  {
   "date": "2026-05-15",
   "text": "파월 의장 임기 종료, 이사회가 임시 의장 지명",
   "keys": [
    "powell"
   ],
   "src": [
    {
     "outlet": "연준 보도자료",
     "date": "2026-05-15",
     "url": "https://www.federalreserve.gov/newsevents/pressreleases/other20260515a.htm"
    }
   ],
   "cert": "1차"
  },
  {
   "date": "2026-05-22",
   "text": "워시 취임. 마이런은 그날이나 직전 이사직 퇴임(날짜 미확인)",
   "keys": [
    "warsh"
   ],
   "src": [
    {
     "outlet": "연준 이사 약력",
     "date": "2026-05-22",
     "url": "https://www.federalreserve.gov/aboutthefed/bios/board/warsh.htm"
    }
   ],
   "cert": "1차"
  },
  {
   "date": "2026-06-29",
   "text": "대법원 5-4, 쿡 해임을 막은 하급심 명령 유지(절차 판단 — 해임 권한 자체는 미결)",
   "keys": [
    "cook"
   ],
   "src": [
    {
     "outlet": "HousingWire",
     "date": "2026-06",
     "url": "https://www.housingwire.com/articles/supreme-court-fed-cook-removal/"
    }
   ],
   "cert": "2차"
  },
  {
   "date": "2026-08-28",
   "text": "잭슨홀: 워시 인플레 경고, 2% PCE '확고하고 고정된 목표'",
   "keys": [
    "warsh"
   ],
   "src": [
    {
     "outlet": "연준 연설",
     "date": "2026-08-28",
     "url": "https://www.federalreserve.gov/newsevents/speech/warsh20260828a.htm"
    }
   ],
   "cert": "1차"
  },
  {
   "date": "2026-09-30",
   "text": "감찰관 보고서: 파월 개보수 건 형사 위반 없음. 트럼프는 사임 요구",
   "keys": [
    "powell"
   ],
   "src": [
    {
     "outlet": "CNBC",
     "date": "2026-09-30",
     "url": "https://www.cnbc.com/2026/09/30/fed-inspector-general-report-powell-trump.html"
    }
   ],
   "cert": "2차"
  },
  {
   "date": "2026-10-30",
   "text": "회의 직후: 무살렘 '곧 추가 긴축', 로건 '최소 두 번 더', 데일리는 AI만",
   "keys": [
    "musalem",
    "logan",
    "daly"
   ],
   "src": [
    {
     "outlet": "세인트루이스 연은 연설",
     "date": "2026-10-30",
     "url": "https://www.stlouisfed.org/from-the-president/remarks/2026/remarks-on-us-economy-and-monetary-policy-somc"
    },
    {
     "outlet": "댈러스 연은 연설",
     "date": "2026-10-30",
     "url": "https://www.dallasfed.org/news/speeches/logan/2026/lkl261030"
    }
   ],
   "cert": "1차"
  }
 ],
 "people": [
  {
   "key": "warsh",
   "name_ko": "케빈 워시",
   "name_en": "Kevin M. Warsh",
   "role_short": "의장·이사",
   "seat": "board",
   "district": null,
   "voter_2026": true,
   "voter_2027": true,
   "bg_type": "혼합",
   "bg_line": "모건스탠리 M&A·백악관 NEC·연준 이사(06~11)·후버연구소",
   "camp": "중도",
   "stance_now": 0.5,
   "stance_start_2026": -0.5,
   "stance_basis": "9월 인상 뒤 동결·12월 미정, 매파 쪽 중도(추론). 연초는 2025 인하론 시기",
   "shift_note": "2025 공개 인하론 → 9월 인상 주도 → 지금은 미리 정하지 않음",
   "journey": [
    {
     "from": "1992",
     "to": "1992",
     "org": "Stanford University",
     "org_ko": "스탠퍼드대",
     "kind": "school",
     "place": "Stanford, CA",
     "lat": 37.4275,
     "lon": -122.1697,
     "note": "AB(공공정책) 1992",
     "cert": "2차"
    },
    {
     "from": "1995",
     "to": "1995",
     "org": "Harvard Law School",
     "org_ko": "하버드 로스쿨",
     "kind": "school",
     "place": "Cambridge, MA",
     "lat": 42.378,
     "lon": -71.119,
     "note": "JD 1995(cum laude)",
     "cert": "2차"
    },
    {
     "from": "1995",
     "to": "2002",
     "org": "Morgan Stanley",
     "org_ko": "모건스탠리",
     "kind": "company",
     "place": "New York, NY",
     "lat": 40.7603,
     "lon": -73.9857,
     "note": "M&A, VP·전무까지",
     "cert": "2차"
    },
    {
     "from": "2002",
     "to": "2006",
     "org": "White House National Economic Council",
     "org_ko": "백악관 국가경제위원회(NEC)",
     "kind": "government",
     "place": "Washington, DC",
     "lat": 38.8977,
     "lon": -77.0365,
     "note": "경제정책 특보 겸 사무국장",
     "cert": "2차"
    },
    {
     "from": "2006",
     "to": "2011",
     "org": "Federal Reserve Board",
     "org_ko": "연준 이사회",
     "kind": "fed",
     "place": "Washington, DC",
     "lat": 38.8929,
     "lon": -77.0459,
     "note": "이사(부시 임명, 35세 최연소 보도)",
     "cert": "2차"
    },
    {
     "from": "2011",
     "to": "2026",
     "org": "Hoover Institution · Stanford GSB",
     "org_ko": "후버연구소·스탠퍼드 GSB",
     "kind": "academia",
     "place": "Stanford, CA",
     "lat": 37.4277,
     "lon": -122.1667,
     "note": "방문 펠로·GSB 강사",
     "cert": "2차"
    },
    {
     "from": null,
     "to": null,
     "org": "UPS",
     "org_ko": "UPS",
     "kind": "company",
     "place": "Atlanta, GA",
     "lat": 33.9304,
     "lon": -84.3533,
     "note": "이사(연도 미상, 2011~26 기간)",
     "cert": "2차"
    },
    {
     "from": "2019",
     "to": "2026",
     "org": "Coupang",
     "org_ko": "쿠팡",
     "kind": "company",
     "place": "Seoul, South Korea",
     "lat": 37.5665,
     "lon": 126.978,
     "note": "사외이사, 인준과 함께 사임",
     "cert": "2차"
    },
    {
     "from": "2026",
     "to": null,
     "org": "Federal Reserve Board",
     "org_ko": "연준 이사회",
     "kind": "fed",
     "place": "Washington, DC",
     "lat": 38.8929,
     "lon": -77.0459,
     "note": "의장 취임 2026-05-22",
     "cert": "2차",
     "now": true
    }
   ],
   "style": [
    "포워드 가이던스·회의 예단 없음, 점도표 점 미제출",
    "짧은 성명·회견 '한 사람 한 질문', 신호는 큰 연설 한 번",
    "정치 질문엔 답하지 않음, 이사 시절엔 반대를 표 아닌 글로"
   ],
   "phrases": [
    {
     "text": "inflation is too high and has been for too long",
     "date": "2026-09-16"
    },
    {
     "text": "I don't believe in forward guidance absent exigent circumstances",
     "date": "2026-10-28"
    }
   ],
   "dissents_2026": [],
   "recent": [
    {
     "date": "2026-10-28",
     "text": "동결 10-2. 위기 아니면 가이던스 없음, 점 낼 계획 없음"
    },
    {
     "date": "2026-10-16",
     "text": "IMF 연차총회(방콕) 대담 — 임박한 인상 신호 피함(2차)"
    },
    {
     "date": "2026-09-16",
     "text": "+25bp 인상 12-0, '물가 너무 높고 너무 오래'"
    },
    {
     "date": "2026-08-28",
     "text": "잭슨홀: '결정 아닌 규율', 행동 기준('분명히, 충분한 속도로')"
    }
   ],
   "baseline": {
    "usual": [
     "'물가 너무 높고 너무 오래'·'2% PCE, 연성 목표 없음'·'물가안정 반드시 달성'",
     "가이던스·점 없음, 회의마다 판단",
     "성장이 물가 원인 아님(생산성)·'고용 해칠 필요 없다'",
     "제도 개편은 이번 국면 영향 작음",
     "'interrogate reality'·데이터 한 점 아닌 추세"
    ],
    "hawk_surprise": [
     "12월·연속 인상 미리 약속",
     "50bp·'훨씬 더 긴축해야'",
     "'과열' 단정·AI 투자가 물가 올린다고 명시",
     "인상 쪽 반대 가담·점 제출"
    ],
    "dove_surprise": [
     "12월 동결 시사·'이제 긴축적, 할 만큼 했다'",
     "유가·생산성으로 인상 종료 선언",
     "고용 약화를 주된 위험으로·2027 인하",
     "트럼프 인하 요구에 맞추는 말투"
    ]
   },
   "review": "approved",
   "watch": "11-16 생산성 청문회, 12월 FOMC 금융여건 문구·점 미제출 유지",
   "conf": "회견·성명·의사록·약력·잭슨홀 연설은 federalreserve.gov 직접 확인(2026-11-04), 쿠팡·UPS·인준 표수는 2차",
   "sources": [
    {
     "outlet": "연준 기자회견 녹취(1차)",
     "date": "2026-10-28",
     "url": "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20261028.pdf"
    },
    {
     "outlet": "연준 기자회견 녹취(1차)",
     "date": "2026-09-16",
     "url": "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20260916.pdf"
    },
    {
     "outlet": "연준 연설(1차)",
     "date": "2026-08-28",
     "url": "https://www.federalreserve.gov/newsevents/speech/warsh20260828a.htm"
    },
    {
     "outlet": "연준 보도자료",
     "date": "2026-05-22",
     "url": "https://www.federalreserve.gov/newsevents/pressreleases/other20260522a.htm"
    },
    {
     "outlet": "24/7 Wall St",
     "date": "2026-08-06",
     "url": "https://247wallst.com/investing/2026/08/06/bank-of-america-says-federal-reserve-chair-kevin-warsh-facing-credibility-shock/"
    },
    {
     "outlet": "Orrick InfoBytes",
     "date": "2026-05-15",
     "url": "https://infobytes.orrick.com/2026-05-15/u-s-senate-confirms-kevin-warsh-to-serve-as-fed-chair/"
    }
   ],
   "camp_src": [
    {
     "outlet": "24/7 Wall St",
     "date": "2026-08-06",
     "url": "https://247wallst.com/investing/2026/08/06/bank-of-america-says-federal-reserve-chair-kevin-warsh-facing-credibility-shock/"
    }
   ]
  },
  {
   "key": "jefferson",
   "name_ko": "필립 제퍼슨",
   "name_en": "Philip N. Jefferson",
   "role_short": "부의장·이사",
   "seat": "board",
   "district": null,
   "voter_2026": true,
   "voter_2027": true,
   "bg_type": "학계",
   "bg_line": "스워스모어 교수·데이비슨 학장, 빈곤·통화정책 연구",
   "camp": "중도",
   "stance_now": 0.5,
   "stance_start_2026": 0,
   "stance_basis": "인상 배제 않되 서두르지 않음, 의장과 함께 매파 쪽으로 움직인 중도",
   "shift_note": "1월 '신중한 낙관' → 7월 '기조 재고' → 9월 인상 찬성",
   "journey": [
    {
     "from": null,
     "to": null,
     "org": "Washington, DC (hometown)",
     "org_ko": "성장지 워싱턴 DC",
     "kind": "other",
     "place": "Washington, DC",
     "lat": 38.9072,
     "lon": -77.0369,
     "note": "워싱턴 DC에서 자람",
     "cert": "1차"
    },
    {
     "from": "1983",
     "to": "1983",
     "org": "Vassar College",
     "org_ko": "바사 칼리지",
     "kind": "school",
     "place": "Poughkeepsie, NY",
     "lat": 41.6868,
     "lon": -73.8964,
     "note": "경제학 학사(졸업 1983은 2차)",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "University of Virginia",
     "org_ko": "버지니아대",
     "kind": "school",
     "place": "Charlottesville, VA",
     "lat": 38.0336,
     "lon": -78.508,
     "note": "경제학 석사·박사",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "Federal Reserve Board",
     "org_ko": "연준 이사회",
     "kind": "fed",
     "place": "Washington, DC",
     "lat": 38.8929,
     "lon": -77.0459,
     "note": "이코노미스트(연도 미확인)",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "Columbia University",
     "org_ko": "컬럼비아대",
     "kind": "academia",
     "place": "New York, NY",
     "lat": 40.8075,
     "lon": -73.9626,
     "note": "강의(미재확인)",
     "cert": "2차"
    },
    {
     "from": null,
     "to": null,
     "org": "University of Virginia",
     "org_ko": "버지니아대",
     "kind": "academia",
     "place": "Charlottesville, VA",
     "lat": 38.0336,
     "lon": -78.508,
     "note": "강의(미재확인)",
     "cert": "2차"
    },
    {
     "from": "1997",
     "to": null,
     "org": "Swarthmore College",
     "org_ko": "스워스모어 칼리지",
     "kind": "academia",
     "place": "Swarthmore, PA",
     "lat": 39.9021,
     "lon": -75.3499,
     "note": "Centennial 교수·경제학과장",
     "cert": "1차"
    },
    {
     "from": "2019",
     "to": "2022",
     "org": "Davidson College",
     "org_ko": "데이비슨 칼리지",
     "kind": "academia",
     "place": "Davidson, NC",
     "lat": 35.5007,
     "lon": -80.8456,
     "note": "교무 부총장·학장·Freeland 교수(연도 2019~22는 사전 지식)",
     "cert": "1차"
    },
    {
     "from": "2022",
     "to": null,
     "org": "Federal Reserve Board",
     "org_ko": "연준 이사회",
     "kind": "fed",
     "place": "Washington, DC",
     "lat": 38.8929,
     "lon": -77.0459,
     "note": "이사 2022-05, 부의장 2023-09",
     "cert": "1차",
     "now": true
    }
   ],
   "style": [
    "정형 원고: 전망→정책→주제, '내 견해' 각주",
    "'대응할 위치'·'지표·전망·위험 균형'·'예단 안 함' 반복",
    "문구가 성명을 따라감, 반대표 기록 없음"
   ],
   "phrases": [
    {
     "text": "We do not have the luxury of considering each shock in a vacuum.",
     "date": "2026-07-16"
    }
   ],
   "dissents_2026": [],
   "recent": [
    {
     "date": "2026-10-28",
     "text": "동결 10-2, 다수 편(추정 — 의사록 미공개)"
    },
    {
     "date": "2026-10-01",
     "text": "다든 연설: 9월 인상 지지, '시간이 더 걸릴 수 있다'"
    },
    {
     "date": "2026-09-22",
     "text": "뉴욕 연은: 재할인창구 현대화, 전망 언급 없음"
    },
    {
     "date": "2026-07-16",
     "text": "스탠퍼드: 물가 안 식으면 기조 재고 적절할 수도"
    }
   ],
   "baseline": {
    "usual": [
     "'대응할 위치'·'지표·전망·위험 균형'",
     "에너지 충격이 지속 물가·기대로 번질 위험 경계",
     "'시간을 갖고 판단'",
     "AI가 중립금리를 올리면 덜 긴축적"
    ],
    "hawk_surprise": [
     "12월 인상이 '필요하다'고 단정",
     "두 번 이상·'충분히 긴축적이지 않다'",
     "중립금리 상승으로 지금 느슨하다 단정",
     "인상 쪽 반대표(반대 기록 없음)"
    ],
    "dove_surprise": [
     "'9월 인상으로 충분, 긴축 끝'",
     "'고용이 약해 받쳐줘야' 복귀",
     "향후 인하 가능성 직접 언급(교과서식 설명 제외)",
     "지도부 인상안에 반대"
    ]
   },
   "review": "approved",
   "watch": "12월 블랙아웃(11-28~) 전 '시간 더 걸릴 수'가 바뀌는지",
   "conf": "연설·표결·약력은 연준 원문(11-04 확인), 경력 연도는 2차·사전 지식",
   "sources": [
    {
     "outlet": "연준 연설",
     "date": "2026-10-01",
     "url": "https://www.federalreserve.gov/newsevents/speech/jefferson20261001a.htm"
    },
    {
     "outlet": "연준 연설",
     "date": "2026-07-16",
     "url": "https://www.federalreserve.gov/newsevents/speech/jefferson20260716a.htm"
    },
    {
     "outlet": "Reuters via Spokesman-Review",
     "date": "2026-10-01",
     "url": "https://www.spokesman.com/stories/2026/oct/01/fed-may-take-time-to-make-next-interest-rate-move-/"
    },
    {
     "outlet": "연준 이사 약력",
     "date": "2026-11-04",
     "url": "https://www.federalreserve.gov/aboutthefed/bios/board/jefferson.htm"
    },
    {
     "outlet": "investinglive",
     "date": "2025-09-17",
     "url": "https://investinglive.com/news/fomc-hawks-and-doves-a-comprehensive-overview-20250917/amp"
    }
   ],
   "camp_src": [
    {
     "outlet": "investinglive",
     "date": "2025-09-17",
     "url": "https://investinglive.com/news/fomc-hawks-and-doves-a-comprehensive-overview-20250917/amp"
    }
   ]
  },
  {
   "key": "bowman",
   "name_ko": "미셸 보먼",
   "name_en": "Michelle W. Bowman",
   "role_short": "감독 부의장·이사",
   "seat": "board",
   "district": null,
   "voter_2026": true,
   "voter_2027": true,
   "bg_type": "혼합",
   "bg_line": "법학 JD·의회·국토안보부 → 가족 은행 → 캔자스 은행감독청장",
   "camp": "스윙",
   "stance_now": 0,
   "stance_start_2026": -1.5,
   "stance_basis": "다수안에 표, 인상 속도 조절 쪽 '급하지 않다'. 1월엔 본인 점 3회 인하",
   "shift_note": "1월 '3회 인하' → 9월 인상 찬성 → 10월 '급하지 않다'",
   "journey": [
    {
     "from": null,
     "to": null,
     "org": "University of Kansas",
     "org_ko": "캔자스대",
     "kind": "school",
     "place": "Lawrence, KS",
     "lat": 38.9543,
     "lon": -95.2558,
     "note": "학사(전공 미기재)",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "Washburn University School of Law",
     "org_ko": "워시번대 로스쿨",
     "kind": "school",
     "place": "Topeka, KS",
     "lat": 39.0337,
     "lon": -95.7018,
     "note": "JD",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "U.S. Congress",
     "org_ko": "미 의회",
     "kind": "government",
     "place": "Washington, DC",
     "lat": 38.8899,
     "lon": -77.0091,
     "note": "밥 돌 상원의원 보좌·하원 위원회 법률고문",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "FEMA",
     "org_ko": "연방재난관리청(FEMA)",
     "kind": "government",
     "place": "Washington, DC",
     "lat": 38.8857,
     "lon": -77.0219,
     "note": "의회·정부간 업무 국장",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "U.S. Department of Homeland Security",
     "org_ko": "국토안보부",
     "kind": "government",
     "place": "Washington, DC",
     "lat": 38.9389,
     "lon": -77.0855,
     "note": "부차관보·리지 장관 정책 자문",
     "cert": "1차"
    },
    {
     "from": "2010",
     "to": "2017",
     "org": "Farmers & Drovers Bank",
     "org_ko": "파머스앤드드로버스 은행",
     "kind": "company",
     "place": "Council Grove, KS",
     "lat": 38.6611,
     "lon": -96.4919,
     "note": "부행장 2010~17(가족 소유는 2차)",
     "cert": "1차"
    },
    {
     "from": "2017",
     "to": "2018",
     "org": "Kansas Office of the State Bank Commissioner",
     "org_ko": "캔자스주 은행감독청",
     "kind": "government",
     "place": "Topeka, KS",
     "lat": 39.0483,
     "lon": -95.678,
     "note": "청장 2017-01~2018-11",
     "cert": "1차"
    },
    {
     "from": "2018",
     "to": null,
     "org": "Federal Reserve Board",
     "org_ko": "연준 이사회",
     "kind": "fed",
     "place": "Washington, DC",
     "lat": 38.8929,
     "lon": -77.0459,
     "note": "이사 2018-11, 감독 부의장 2025-06",
     "cert": "1차",
     "now": true
    },
    {
     "from": "2025",
     "to": null,
     "org": "Financial Stability Board",
     "org_ko": "금융안정위원회(FSB)",
     "kind": "other",
     "place": "Basel, Switzerland",
     "lat": 47.5596,
     "lon": 7.5886,
     "note": "감독·규제협력 상임위(SRC) 의장",
     "cert": "1차",
     "now": true
    }
   ],
   "style": [
    "통화정책 연설 드묾 — 2026년 3건, 나머지는 규제·감독",
    "인하·인상·동결 조건을 적은 '결정 틀'을 미리 공개",
    "반대표를 쓰는 사람: 2024-09 매파, 2025-07 비둘기 쪽"
   ],
   "phrases": [
    {
     "text": "I don’t currently see an urgent need for further action",
     "date": "2026-10-01"
    },
    {
     "text": "unwarranted policy restraint",
     "date": "2026-05-29"
    }
   ],
   "dissents_2026": [],
   "recent": [
    {
     "date": "2026-10-28",
     "text": "동결 10-2, 다수 쪽(추론 — 명단은 11월 의사록)"
    },
    {
     "date": "2026-10-14",
     "text": "방콕: SVB 뒤 감독 개편 연설(원고에 금리 없음), 별도 문답 '지켜볼 시간 있다'(2차)"
    },
    {
     "date": "2026-10-06",
     "text": "감독 조직 5개 권역 재편, 자산 문턱 연내 갱신 검토"
    },
    {
     "date": "2026-10-01",
     "text": "애틀랜틱 카운슬: eSLR 연설, 문답 '지금 추가 조치 급히 필요 없다'(주최 측 인용)"
    },
    {
     "date": "2026-09-18",
     "text": "런던: SVB 독립 검토 초기 결과, 연내 자본 규제 확정 예상"
    }
   ],
   "baseline": {
    "usual": [
     "'급하지 않다, wait and see'",
     "자료와 기업 접촉으로 판단",
     "관세 뺀 근원·절사평균 강조",
     "규제·감독(eSLR·바젤III·SVB)"
    ],
    "hawk_surprise": [
     "12월 인상 명시 지지",
     "에너지 충격이 근원·기대로 번져 추가 인상 필요",
     "'아직 충분히 긴축적이지 않다'",
     "인상 쪽 반대표"
    ],
    "dove_surprise": [
     "12월 인상에 반대표(연설로 예고 가능)",
     "9월 인상 되돌림·2027 인하",
     "노동 약화로 'behind the curve'·인하 요구 복귀"
    ]
   },
   "review": "approved",
   "watch": "12월 블랙아웃(11-28~) 전 '급하지 않다' 유지 여부, 바젤III 연내 확정",
   "conf": "통화정책 연설·표결·약력은 연준 원문(11-04 확인), 10-01·10-14 금리 문답은 2차(주최 측·보도)",
   "sources": [
    {
     "outlet": "연준 연설",
     "date": "2026-05-29",
     "url": "https://www.federalreserve.gov/newsevents/speech/bowman20260529a.htm"
    },
    {
     "outlet": "Reuters via US News",
     "date": "2026-10-14",
     "url": "https://money.usnews.com/investing/news/articles/2026-10-14/feds-bowman-says-theres-time-to-wait-and-see-before-any-more-action"
    },
    {
     "outlet": "연준 보도자료",
     "date": "2025-06-09",
     "url": "https://www.federalreserve.gov/newsevents/pressreleases/other20250609a.htm"
    },
    {
     "outlet": "Federal Reserve History",
     "date": "—",
     "url": "https://www.federalreservehistory.org/people/michelle-w-bowman"
    },
    {
     "outlet": "Reuters via Kitco",
     "date": "2024-09-20",
     "url": "https://www.kitco.com/news/off-the-wire/2024-09-20/us-inflation-data-cemented-big-cut-one-fed-official-dissent-another"
    },
    {
     "outlet": "상원 은행위 소수당",
     "date": "2025-11-07",
     "url": "https://www.banking.senate.gov/newsroom/minority/warren-presses-fed-for-details-on-reported-30-cuts-to-supervision-and-regulation-team"
    },
    {
     "outlet": "연준 이사 약력",
     "date": "2026-11-04",
     "url": "https://www.federalreserve.gov/aboutthefed/bios/board/bowman.htm"
    },
    {
     "outlet": "Atlantic Council(주최 측 인용)",
     "date": "2026-10-01",
     "url": "https://www.atlanticcouncil.org/event/federal-reserve-vice-chair-michelle-bowman-on-modernizing-financial-regulation/"
    },
    {
     "outlet": "연준 연설",
     "date": "2026-10-01",
     "url": "https://www.federalreserve.gov/newsevents/speech/bowman20261001a.htm"
    }
   ],
   "camp_src": [
    {
     "outlet": "Reuters via Kitco",
     "date": "2024-09-20",
     "url": "https://www.kitco.com/news/off-the-wire/2024-09-20/us-inflation-data-cemented-big-cut-one-fed-official-dissent-another"
    },
    {
     "outlet": "상원 은행위 소수당",
     "date": "2025-11-07",
     "url": "https://www.banking.senate.gov/newsroom/minority/warren-presses-fed-for-details-on-reported-30-cuts-to-supervision-and-regulation-team"
    }
   ]
  },
  {
   "key": "waller",
   "name_ko": "크리스토퍼 월러",
   "name_en": "Christopher J. Waller",
   "role_short": "이사",
   "seat": "board",
   "district": null,
   "voter_2026": true,
   "voter_2027": true,
   "bg_type": "학계",
   "bg_line": "인디애나·켄터키·노터데임 교수 → 세인트루이스 연은 연구국장",
   "camp": "스윙",
   "stance_now": 1,
   "stance_start_2026": -1.5,
   "stance_basis": "'예상대로면 추가 인상, 연속일 필요 없음'. 1월엔 인하 쪽 반대표",
   "shift_note": "1월 인하 반대표 → 3월 동결 → 9월 인상 → 추가 인상",
   "journey": [
    {
     "from": "1981",
     "to": "1981",
     "org": "Bemidji State University",
     "org_ko": "베미지 주립대",
     "kind": "school",
     "place": "Bemidji, MN",
     "lat": 47.4875,
     "lon": -94.8722,
     "note": "학사 1981",
     "cert": "2차"
    },
    {
     "from": "1984",
     "to": "1985",
     "org": "Washington State University",
     "org_ko": "워싱턴 주립대",
     "kind": "school",
     "place": "Pullman, WA",
     "lat": 46.7319,
     "lon": -117.1542,
     "note": "경제학 석사 1984·박사 1985",
     "cert": "2차"
    },
    {
     "from": "1985",
     "to": "1998",
     "org": "Indiana University",
     "org_ko": "인디애나대",
     "kind": "academia",
     "place": "Bloomington, IN",
     "lat": 39.1682,
     "lon": -86.523,
     "note": "경제학 교수",
     "cert": "2차"
    },
    {
     "from": "1998",
     "to": "2003",
     "org": "University of Kentucky",
     "org_ko": "켄터키대",
     "kind": "academia",
     "place": "Lexington, KY",
     "lat": 38.0307,
     "lon": -84.504,
     "note": "Gatton 석좌",
     "cert": "2차"
    },
    {
     "from": "2003",
     "to": "2009",
     "org": "University of Notre Dame",
     "org_ko": "노터데임대",
     "kind": "academia",
     "place": "Notre Dame, IN",
     "lat": 41.7052,
     "lon": -86.2353,
     "note": "Schaefer 석좌(연도는 사전 지식)",
     "cert": "2차"
    },
    {
     "from": "2009",
     "to": "2020",
     "org": "Federal Reserve Bank of St. Louis",
     "org_ko": "세인트루이스 연은",
     "kind": "fed",
     "place": "St. Louis, MO",
     "lat": 38.629,
     "lon": -90.188,
     "note": "수석부총재·연구국장",
     "cert": "2차"
    },
    {
     "from": "2020",
     "to": null,
     "org": "Federal Reserve Board",
     "org_ko": "연준 이사회",
     "kind": "fed",
     "place": "Washington, DC",
     "lat": 38.8929,
     "lon": -77.0459,
     "note": "이사 2020-12, 연은 운영 감독",
     "cert": "2차",
     "now": true
    }
   ],
   "style": [
    "회의 2~4주 전 전망 연설 = 사실상 표 예고",
    "'IF 자료가 이러면 THEN 이렇게' 반응함수를 스스로 공개",
    "반대표 뒤 설명문, 직설·구어체 표현"
   ],
   "phrases": [
    {
     "text": "Zero. Zip. Nada.",
     "date": "2026-01-30"
    },
    {
     "text": "The hikes do not need to come at consecutive meetings",
     "date": "2026-10-08"
    }
   ],
   "dissents_2026": [
    {
     "date": "2026-01-28",
     "side": "인하"
    }
   ],
   "recent": [
    {
     "date": "2026-10-28",
     "text": "동결 10-2 찬성(반대는 쿡·해맥뿐)"
    },
    {
     "date": "2026-10-08",
     "text": "이스탄불: 예상대로면 추가 인상, 연속 회의일 필요 없음"
    },
    {
     "date": "2026-09-16",
     "text": "+25bp 인상 찬성(12-0)"
    },
    {
     "date": "2026-09-03",
     "text": "로이터 NEXT: 디스인플레 조짐, 뜨거우면 인상 고려"
    }
   ],
   "baseline": {
    "usual": [
     "'예상대로면 추가 인상, 연속 아님'",
     "다음 표를 특정 물가 발표에 건다",
     "AI = 성장 + 기술재 물가 압력",
     "지금은 가이던스 부적절(워시 동의), SEP 신호 옹호"
    ],
    "hawk_surprise": [
     "데이터 전에 12월 인상 무조건 지지",
     "연속 인상·50bp",
     "인상 쪽 반대표",
     "2~5년 기대 '이미 상승·이탈' 판단(위험 우려는 평소)"
    ],
    "dove_surprise": [
     "'9월 한 번이면 충분'",
     "노동 약화가 지배적이라는 1월식 틀",
     "자기 전망으로 2027 인하 제시(점도표 해설 제외)",
     "3개월 근원 둔화 확인으로 12월 동결 지지(조건문 제외)"
    ]
   },
   "review": "approved",
   "watch": "11월 전망 연설: 12월 표를 걸 지표, '두 번'·'50bp' 언급",
   "conf": "연설·성명·약력은 1차(연준 원문 2026-11-04 확인), 학력 연도·3월 접은 반대는 2차",
   "sources": [
    {
     "outlet": "연준 연설(1차)",
     "date": "2026-10-08",
     "url": "https://www.federalreserve.gov/newsevents/speech/waller20261008a.htm"
    },
    {
     "outlet": "연준 반대 설명문(1차)",
     "date": "2026-01-30",
     "url": "https://www.federalreserve.gov/newsevents/speech/waller20260130a.htm"
    },
    {
     "outlet": "Reuters via Kitco",
     "date": "2026-03-20",
     "url": "https://www.kitco.com/news/off-the-wire/2026-03-20/feds-waller-says-was-planning-call-rate-cut-until-oil-shock-raised"
    },
    {
     "outlet": "Federal Reserve History",
     "date": "—",
     "url": "https://federalreservehistory.org/people/christopher-waller"
    },
    {
     "outlet": "Reuters ROI 칼럼 via Zawya",
     "date": "2026-07-16",
     "url": "https://www.zawya.com/en/web-section/insights/fed-flip-flops-make-case-for-less-talk-mike-dolan-394207"
    },
    {
     "outlet": "연준 연설(1차)",
     "date": "2026-09-03",
     "url": "https://www.federalreserve.gov/newsevents/speech/waller20260903a.htm"
    }
   ],
   "camp_src": [
    {
     "outlet": "Reuters ROI 칼럼 via Zawya",
     "date": "2026-07-16",
     "url": "https://www.zawya.com/en/web-section/insights/fed-flip-flops-make-case-for-less-talk-mike-dolan-394207"
    }
   ]
  },
  {
   "key": "barr",
   "name_ko": "마이클 바",
   "name_en": "Michael S. Barr",
   "role_short": "이사(전 감독 부의장)",
   "seat": "board",
   "district": null,
   "voter_2026": true,
   "voter_2027": true,
   "bg_type": "혼합",
   "bg_line": "법학자·재무부 차관보 → 미시간대 학장 → 감독 부의장",
   "camp": "미상",
   "stance_now": 1,
   "stance_start_2026": 0,
   "stance_basis": "9월부터 '추가 조정이 기본 시나리오', 반대표 없음. 봄엔 '당분간 동결'",
   "shift_note": "봄 '당분간 동결·특히 경계' → 9월 '추가 조정 기본'",
   "journey": [
    {
     "from": null,
     "to": null,
     "org": "Yale University",
     "org_ko": "예일대",
     "kind": "school",
     "place": "New Haven, CT",
     "lat": 41.3163,
     "lon": -72.9223,
     "note": "BA 역사",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "University of Oxford",
     "org_ko": "옥스퍼드대",
     "kind": "school",
     "place": "Oxford, United Kingdom",
     "lat": 51.7548,
     "lon": -1.2544,
     "note": "MPhil 국제관계, 로즈 장학생(2차)",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "Yale Law School",
     "org_ko": "예일 로스쿨",
     "kind": "school",
     "place": "New Haven, CT",
     "lat": 41.3115,
     "lon": -72.9266,
     "note": "JD",
     "cert": "1차"
    },
    {
     "from": "1993",
     "to": "1994",
     "org": "U.S. Supreme Court",
     "org_ko": "연방 대법원",
     "kind": "government",
     "place": "Washington, DC",
     "lat": 38.8906,
     "lon": -77.0044,
     "note": "수터 대법관 재판연구원(1993 회기)",
     "cert": "1차"
    },
    {
     "from": "1995",
     "to": "2001",
     "org": "U.S. Department of the Treasury",
     "org_ko": "재무부",
     "kind": "government",
     "place": "Washington, DC",
     "lat": 38.8987,
     "lon": -77.0342,
     "note": "루빈 장관 밑 지역개발 정책 6년",
     "cert": "1차"
    },
    {
     "from": "2001",
     "to": null,
     "org": "University of Michigan Law School",
     "org_ko": "미시간대(로스쿨)",
     "kind": "academia",
     "place": "Ann Arbor, MI",
     "lat": 42.2808,
     "lon": -83.743,
     "note": "교수(로스쿨·2001~는 사전 지식)",
     "cert": "1차"
    },
    {
     "from": "2009",
     "to": "2010",
     "org": "U.S. Department of the Treasury",
     "org_ko": "재무부",
     "kind": "government",
     "place": "Washington, DC",
     "lat": 38.8987,
     "lon": -77.0342,
     "note": "금융기관 담당 차관보, 도드-프랭크",
     "cert": "1차"
    },
    {
     "from": "2017",
     "to": "2022",
     "org": "University of Michigan Ford School",
     "org_ko": "미시간대 포드 공공정책대학원",
     "kind": "academia",
     "place": "Ann Arbor, MI",
     "lat": 42.2766,
     "lon": -83.7383,
     "note": "학장(포드스쿨·연도는 사전 지식)",
     "cert": "1차"
    },
    {
     "from": "2022",
     "to": null,
     "org": "Federal Reserve Board",
     "org_ko": "연준 이사회",
     "kind": "fed",
     "place": "Washington, DC",
     "lat": 38.8929,
     "lon": -77.0459,
     "note": "이사, 감독 부의장 ~2025-02",
     "cert": "1차",
     "now": true
    }
   ],
   "style": [
    "통화정책 견해는 주제 연설 앞 짧은 문단으로",
    "'balance of risks'·'timely', 양방향 조건문, 경로 숫자 없음",
    "반대는 FOMC 아닌 이사회 규제 표결에서, 성명으로"
   ],
   "phrases": [
    {
     "text": "especially vigilant",
     "date": "2026-03-26"
    },
    {
     "text": "when the bill comes due",
     "date": "2026-06-06"
    },
    {
     "text": "in my base case",
     "date": "2026-09-29"
    }
   ],
   "dissents_2026": [],
   "recent": [
    {
     "date": "2026-10-28",
     "text": "동결 10-2 찬성(반대는 쿡·해맥뿐)"
    },
    {
     "date": "2026-09-29",
     "text": "디트로이트: '기본 시나리오에서 추가 조정', 물가 위험 커짐"
    },
    {
     "date": "2026-09-23",
     "text": "시카고 연은 주택 서밋: 인상 지지, 구입능력 21년 최저"
    },
    {
     "date": "2026-09-01",
     "text": "재기 대출 포럼: 둔화 확신 없으면 '단호히 인상'"
    }
   ],
   "baseline": {
    "usual": [
     "'timely'·'balance of risks'·'기본 시나리오'",
     "AI는 인하 근거 아님(r* 상승)",
     "규제 완화 비판·반대 성명",
     "대차대조표 축소 반대"
    ],
    "hawk_surprise": [
     "FOMC 첫 반대표(인상 쪽)",
     "50bp·연속 인상·목표 수준 제시",
     "r* 상승으로 지금 덜 긴축적이라 단정",
     "대차대조표 축소 찬성(체제 변화)"
    ],
    "dove_surprise": [
     "'인상 충분'·장기 동결",
     "AI 일자리 대체·노동 하방을 근거로 인상 보류 주장",
     "금융안정 위험으로 인상 반대",
     "인하 지지·시점 제시(조건·부정형 제외)"
    ]
   },
   "review": "approved",
   "watch": "12월 전 '기본 시나리오 추가 조정' 유지 여부, 첫 반대표 여부",
   "conf": "연설·표결·학력·직함은 1차(연준 원문 2026-11-04 확인), 로즈 장학·미시간 재직 연도는 2차/사전 지식",
   "sources": [
    {
     "outlet": "연준 연설(1차)",
     "date": "2026-09-29",
     "url": "https://www.federalreserve.gov/newsevents/speech/barr20260929a.htm"
    },
    {
     "outlet": "연준 연설(1차)",
     "date": "2026-03-26",
     "url": "https://www.federalreserve.gov/newsevents/speech/barr20260326a.htm"
    },
    {
     "outlet": "연준 연설(1차)",
     "date": "2026-06-06",
     "url": "https://www.federalreserve.gov/newsevents/speech/barr20260606a.htm"
    },
    {
     "outlet": "연준 이사 약력(1차)",
     "date": "2025-03-01",
     "url": "https://www.federalreserve.gov/aboutthefed/bios/board/barr.htm"
    },
    {
     "outlet": "연준 연설(1차)",
     "date": "2026-09-23",
     "url": "https://www.federalreserve.gov/newsevents/speech/barr20260923a.htm"
    },
    {
     "outlet": "연준 연설(1차)",
     "date": "2026-09-01",
     "url": "https://www.federalreserve.gov/newsevents/speech/barr20260901a.htm"
    }
   ]
  },
  {
   "key": "cook",
   "name_ko": "리사 쿡",
   "name_en": "Lisa D. Cook",
   "role_short": "이사",
   "seat": "board",
   "district": null,
   "voter_2026": true,
   "voter_2027": true,
   "bg_type": "학계",
   "bg_line": "MSU 교수, 혁신·특허·경제사 연구, 재무부·CEA 참모",
   "camp": "매파",
   "stance_now": 1.5,
   "stance_start_2026": 0.5,
   "stance_basis": "인플레 우선 매파, 10월 첫 인상 쪽 반대. 2월 '위험이 인플레 쪽'",
   "shift_note": "2025 합의파 → 2월부터 단계적 매파 예고 → 10월 첫 반대",
   "journey": [
    {
     "from": null,
     "to": null,
     "org": "Milledgeville, Georgia (hometown)",
     "org_ko": "고향 조지아주 밀레지빌",
     "kind": "other",
     "place": "Milledgeville, GA",
     "lat": 33.0801,
     "lon": -83.2321,
     "note": "나고 자람",
     "cert": "1차"
    },
    {
     "from": "1986",
     "to": "1986",
     "org": "Spelman College",
     "org_ko": "스펠먼 칼리지",
     "kind": "school",
     "place": "Atlanta, GA",
     "lat": 33.7457,
     "lon": -84.4113,
     "note": "철학 학사(연준 약력). 1986은 사전 지식",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "Georgia Institute of Technology",
     "org_ko": "조지아공대",
     "kind": "school",
     "place": "Atlanta, GA",
     "lat": 33.7756,
     "lon": -84.3963,
     "note": "스펠먼과 함께 다님(본인)",
     "cert": "1차"
    },
    {
     "from": "1988",
     "to": "1988",
     "org": "University of Oxford",
     "org_ko": "옥스퍼드대",
     "kind": "school",
     "place": "Oxford, United Kingdom",
     "lat": 51.7548,
     "lon": -1.2544,
     "note": "마셜 장학생, PPE 학사(연준 약력). 1988은 사전 지식",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "Senegal (philosophy study)",
     "org_ko": "세네갈(철학 공부)",
     "kind": "other",
     "place": "(도시 미상), Senegal",
     "lat": 14.4974,
     "lon": -14.4524,
     "note": "철학→경제학 전환, 도시는 미기재",
     "cert": "1차",
     "loc_guess": true
    },
    {
     "from": "1991",
     "to": "1997",
     "org": "University of California, Berkeley",
     "org_ko": "UC버클리",
     "kind": "school",
     "place": "Berkeley, CA",
     "lat": 37.8719,
     "lon": -122.2585,
     "note": "경제학 박사(1997은 사전 지식)",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "AEA Summer Program (Stanford)",
     "org_ko": "AEA 여름 프로그램(스탠퍼드)",
     "kind": "school",
     "place": "Stanford, CA",
     "lat": 37.4275,
     "lon": -122.1697,
     "note": "학생으로 거침",
     "cert": "1차"
    },
    {
     "from": "1997",
     "to": null,
     "org": "Harvard University (CID · Kennedy School)",
     "org_ko": "하버드(국제개발센터·케네디스쿨)",
     "kind": "academia",
     "place": "Cambridge, MA",
     "lat": 42.3717,
     "lon": -71.1213,
     "note": "케네디스쿨 교수진·CID 아프리카 연구 부국장(연준 약력). 1997은 사전 지식",
     "cert": "1차"
    },
    {
     "from": "2000",
     "to": "2001",
     "org": "U.S. Department of the Treasury",
     "org_ko": "재무부",
     "kind": "government",
     "place": "Washington, DC",
     "lat": 38.8987,
     "lon": -77.0342,
     "note": "국제업무국 선임 고문(2000~01, 연준 약력)",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "Stanford University · Hoover Institution",
     "org_ko": "스탠퍼드·후버연구소",
     "kind": "academia",
     "place": "Stanford, CA",
     "lat": 37.4277,
     "lon": -122.1667,
     "note": "박사후 3년·후버 펠로, 특허 연구",
     "cert": "1차"
    },
    {
     "from": "2005",
     "to": "2022",
     "org": "Michigan State University",
     "org_ko": "미시간주립대",
     "kind": "academia",
     "place": "East Lansing, MI",
     "lat": 42.7018,
     "lon": -84.4822,
     "note": "경제학·국제관계 교수(연도 사전 지식)",
     "cert": "1차"
    },
    {
     "from": "2011",
     "to": "2012",
     "org": "White House Council of Economic Advisers",
     "org_ko": "백악관 경제자문위원회(CEA)",
     "kind": "government",
     "place": "Washington, DC",
     "lat": 38.8975,
     "lon": -77.039,
     "note": "선임 이코노미스트(2011~12, 연준 약력)",
     "cert": "1차"
    },
    {
     "from": "2020",
     "to": "2020",
     "org": "Biden transition team",
     "org_ko": "바이든 인수위",
     "kind": "government",
     "place": "Washington, DC",
     "lat": 38.9072,
     "lon": -77.0369,
     "note": "연준·금융규제기관 검토팀",
     "cert": "사전 지식"
    },
    {
     "from": "2022",
     "to": null,
     "org": "Federal Reserve Board",
     "org_ko": "연준 이사회",
     "kind": "fed",
     "place": "Washington, DC",
     "lat": 38.8929,
     "lon": -77.0459,
     "note": "이사, 이사회 금융안정위원장",
     "cert": "1차",
     "now": true
    }
   ],
   "style": [
    "원고형: 전망→정책, 금리 경로 예측은 피함",
    "매파 전환을 2~9월 몇 달에 걸쳐 단계적으로 예고",
    "인터뷰·즉석 발언·10월 반대 설명문은 못 찾음"
   ],
   "phrases": [
    {
     "text": "I am prepared to act by raising rates, if necessary",
     "date": "2026-08-05"
    },
    {
     "text": "The labor market appears to be well positioned to handle an increase in rates",
     "date": "2026-09-28"
    },
    {
     "text": "inflation, which has been too high for too long",
     "date": "2026-09-28"
    }
   ],
   "dissents_2026": [
    {
     "date": "2026-10-28",
     "side": "인상"
    }
   ],
   "recent": [
    {
     "date": "2026-10-28",
     "text": "동결에 반대, +25bp 인상 주장(2022-06 첫 회의 뒤 첫 반대 — 전 성명 확인)"
    },
    {
     "date": "2026-09-30",
     "text": "리치먼드 연은 농촌 회의: '너무 높고 너무 오래', 9월 인상 찬성"
    },
    {
     "date": "2026-09-28",
     "text": "오클랜드: 노동은 인상 감당 가능, AI 부문 가격은 금리로 안 싸움"
    },
    {
     "date": "2026-08-05",
     "text": "앵커리지: '필요하면 인상할 준비'"
    }
   ],
   "baseline": {
    "usual": [
     "'위험이 인플레 쪽'·'prepared to act'",
     "AI 수요·중동 에너지 충격이 물가를 더함",
     "노동 안정(저채용·저해고)·인상 감당 가능",
     "AI 부문 가격은 금리로 안 싸움(전력·건설로 번질 위험 경계)",
     "AI 일자리 대체: 큰 위험이지만 1년 전보다 안 커짐"
    ],
    "hawk_surprise": [
     "50bp·'확실히 제약적 수준까지'·2027에도 연속 인상",
     "중장기 기대가 풀린다는 판단",
     "대차대조표 축소 재개 지지"
    ],
    "dove_surprise": [
     "12월 동결 지지·'더 기다리자'",
     "10월 반대를 물리거나 금리 밖 이유로",
     "'고용 하방 위험이 더 크다' 복귀",
     "'충분히 제약적'"
    ]
   },
   "review": "approved",
   "watch": "첫 연설(반대 설명)·11-18 의사록, 해임 소송·백악관 청문(12월 연기 보도), 12월 표결",
   "conf": "연설·표결·학력·재무부/CEA 연도는 1차(연준 원문), 대법원·백악관 청문은 2차",
   "sources": [
    {
     "outlet": "연준 FOMC 성명(1차)",
     "date": "2026-10-28",
     "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm"
    },
    {
     "outlet": "연준 연설(1차)",
     "date": "2026-09-28",
     "url": "https://www.federalreserve.gov/newsevents/speech/cook20260928a.htm"
    },
    {
     "outlet": "연준 연설(1차)",
     "date": "2026-08-05",
     "url": "https://www.federalreserve.gov/newsevents/speech/cook20260805a.htm"
    },
    {
     "outlet": "CNN live",
     "date": "2026-10-28",
     "url": "https://www.cnn.com/2026/10/28/business/live-news/federal-reserve-interest-rate-october"
    },
    {
     "outlet": "CNBC",
     "date": "2026-10-28",
     "url": "https://www.cnbc.com/2026/10/28/fed-interest-rate-decision-october-2026.html"
    },
    {
     "outlet": "HousingWire",
     "date": "2026-06",
     "url": "https://www.housingwire.com/articles/supreme-court-fed-cook-removal/"
    },
    {
     "outlet": "연준 이사 약력(1차)",
     "date": "2023-09-13",
     "url": "https://www.federalreserve.gov/aboutthefed/bios/board/cook.htm"
    }
   ],
   "voter_note": "2027 재직은 해임 다툼에 달림(불확실)",
   "camp_src": [
    {
     "outlet": "CNN 라이브",
     "date": "2026-10-28",
     "url": "https://www.cnn.com/2026/10/28/business/live-news/federal-reserve-interest-rate-october"
    },
    {
     "outlet": "CNBC",
     "date": "2026-10-28",
     "url": "https://www.cnbc.com/2026/10/28/fed-interest-rate-decision-october-2026.html"
    }
   ]
  },
  {
   "key": "powell",
   "name_ko": "제롬 파월",
   "name_en": "Jerome H. Powell",
   "role_short": "이사(전 의장)",
   "seat": "board",
   "district": null,
   "voter_2026": true,
   "voter_2027": true,
   "bg_type": "혼합",
   "bg_line": "변호사·딜런 리드·재무부 차관·칼라일 → 연준 이사·의장",
   "camp": "미상",
   "stance_now": 0.5,
   "stance_start_2026": -0.5,
   "stance_basis": "공개 발언 없이 다수 쪽 투표(9월 인상 찬성). 4월엔 완화 편향 유지 쪽",
   "shift_note": "4월 완화 편향 유지 → 9월 인상 찬성(투표로만 드러남)",
   "journey": [
    {
     "from": null,
     "to": null,
     "org": "Washington, DC (hometown)",
     "org_ko": "성장지 워싱턴 DC",
     "kind": "other",
     "place": "Washington, DC",
     "lat": 38.9072,
     "lon": -77.0369,
     "note": "워싱턴 DC에서 자람",
     "cert": "1차"
    },
    {
     "from": "1975",
     "to": "1975",
     "org": "Princeton University",
     "org_ko": "프린스턴대",
     "kind": "school",
     "place": "Princeton, NJ",
     "lat": 40.3431,
     "lon": -74.6551,
     "note": "정치학 전공, 1975 졸업",
     "cert": "1차"
    },
    {
     "from": "1979",
     "to": "1979",
     "org": "Georgetown University Law Center",
     "org_ko": "조지타운대 로스쿨",
     "kind": "school",
     "place": "Washington, DC",
     "lat": 38.8981,
     "lon": -77.0129,
     "note": "법학 1979, 로저널 편집장(연준 약력)",
     "cert": "1차"
    },
    {
     "from": "1979",
     "to": "1984",
     "org": "Davis Polk & Wardwell (and others)",
     "org_ko": "재판연구원·로펌 변호사",
     "kind": "company",
     "place": "New York, NY",
     "lat": 40.7546,
     "lon": -73.9787,
     "note": "항소법원 재판연구원·데이비스 포크 등",
     "cert": "사전 지식",
     "loc_guess": true
    },
    {
     "from": "1984",
     "to": "1990",
     "org": "Dillon, Read & Co.",
     "org_ko": "딜런 리드",
     "kind": "company",
     "place": "New York, NY",
     "lat": 40.7074,
     "lon": -74.0113,
     "note": "말단 어소시에이트(연도 사전 지식)",
     "cert": "1차"
    },
    {
     "from": "1990",
     "to": "1993",
     "org": "U.S. Department of the Treasury",
     "org_ko": "재무부",
     "kind": "government",
     "place": "Washington, DC",
     "lat": 38.8987,
     "lon": -77.0342,
     "note": "차관보→국내금융 차관(연도 사전 지식)",
     "cert": "1차"
    },
    {
     "from": "1993",
     "to": "1995",
     "org": "Dillon, Read & Co.",
     "org_ko": "딜런 리드",
     "kind": "company",
     "place": "New York, NY",
     "lat": 40.7074,
     "lon": -74.0113,
     "note": "복귀(사전 지식)",
     "cert": "사전 지식"
    },
    {
     "from": null,
     "to": null,
     "org": "Bankers Trust",
     "org_ko": "뱅커스 트러스트",
     "kind": "company",
     "place": "New York, NY",
     "lat": 40.709,
     "lon": -74.012,
     "note": "연도 미상(사전 지식)",
     "cert": "사전 지식"
    },
    {
     "from": "1997",
     "to": "2005",
     "org": "The Carlyle Group",
     "org_ko": "칼라일 그룹",
     "kind": "company",
     "place": "Washington, DC",
     "lat": 38.905,
     "lon": -77.0386,
     "note": "파트너 1997~2005(연준 약력)",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "Severn Capital (and others)",
     "org_ko": "세번 캐피털 등",
     "kind": "company",
     "place": "Washington, DC",
     "lat": 38.9072,
     "lon": -77.0369,
     "note": "연도 미상·위치는 추정(사전 지식)",
     "cert": "사전 지식",
     "loc_guess": true
    },
    {
     "from": "2010",
     "to": "2012",
     "org": "Bipartisan Policy Center",
     "org_ko": "초당적정책센터",
     "kind": "other",
     "place": "Washington, DC",
     "lat": 38.901,
     "lon": -77.041,
     "note": "부채 한도 작업(사전 지식)",
     "cert": "사전 지식"
    },
    {
     "from": "2012",
     "to": null,
     "org": "Federal Reserve Board",
     "org_ko": "연준 이사회",
     "kind": "fed",
     "place": "Washington, DC",
     "lat": 38.8929,
     "lon": -77.0459,
     "note": "이사 2012·의장 2018~26·다시 이사",
     "cert": "1차",
     "now": true
    }
   ],
   "style": [
    "의장 시절 매 회의 기자회견, 'meeting-by-meeting'",
    "실수를 인정하는 말을 남김('잘못하면 인정하고 바꾼다')",
    "이사 전환 뒤 공개 발언 거의 없음 — '의장은 하나'"
   ],
   "phrases": [
    {
     "text": "I plan to keep a low profile as a Governor",
     "date": "2026-04-29"
    },
    {
     "text": "well and truly over, with transparency and finality",
     "date": "2026-04-29"
    },
    {
     "text": "When we make mistakes, we acknowledge them and change course",
     "date": "2026-05-31"
    }
   ],
   "dissents_2026": [],
   "recent": [
    {
     "date": "2026-10-28",
     "text": "동결 10-2 찬성(반대는 쿡·해맥뿐, 12명 투표 — 11월 의사록 명단으로 재확인)"
    },
    {
     "date": "2026-09-30",
     "text": "감찰관: 형사 회부 근거 없음, 트럼프 사임 요구 · 10-02 법무부 재수사 안 함(2차) — 파월 반응 없음"
    },
    {
     "date": "2026-09-16",
     "text": "+25bp 인상 찬성(12-0, 의사록 명단)"
    },
    {
     "date": "2026-05-31",
     "text": "JFK 도서관 재단 소감: 독립성, 금리 언급 없음"
    }
   ],
   "baseline": {
    "usual": [
     "독립성·법치 원칙론(금리 언급 없이)",
     "'high-profile dissident'는 안 함"
    ],
    "hawk_surprise": [
     "12월 동결이면 인상 쪽 반대 합류",
     "공개적으로 '추가 인상 필요'"
    ],
    "dove_surprise": [
     "인상 결정에 동결 쪽 반대표",
     "'이제 충분히 긴축적' 공개 발언"
    ]
   },
   "review": "approved",
   "watch": "12월 표결, 10월 의사록 명단(11월), 이사직 유지 — 04-29 '조사 완전 종결까지' 조건, 10-02 법무부 재수사 안 함 뒤 본인 언급 없음",
   "conf": "회견·성명·의사록·약력·연설은 federalreserve.gov 직접 확인(2026-11-04), 딜런 리드 연도·감찰관·법무부 건은 사전 지식·2차",
   "sources": [
    {
     "outlet": "연준 기자회견 녹취(1차)",
     "date": "2026-04-29",
     "url": "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20260429.pdf"
    },
    {
     "outlet": "연준 연설(1차)",
     "date": "2026-05-31",
     "url": "https://www.federalreserve.gov/newsevents/speech/powell20260531a.htm"
    },
    {
     "outlet": "CNBC",
     "date": "2026-09-30",
     "url": "https://www.cnbc.com/2026/09/30/fed-inspector-general-report-powell-trump.html"
    },
    {
     "outlet": "NAHB Eye on Housing",
     "date": "2026-04",
     "url": "https://eyeonhousing.org/2026/04/powells-chair-ends-but-he-keeps-his-board-seat/"
    },
    {
     "outlet": "연준 이사 약력(1차)",
     "date": "2026-05-22",
     "url": "https://www.federalreserve.gov/aboutthefed/bios/board/powell.htm"
    },
    {
     "outlet": "CNBC",
     "date": "2026-10-02",
     "url": "https://www.cnbc.com/2026/10/02/doj-says-it-will-not-reopen-criminal-probe-into-former-fed-chair-powell.html"
    }
   ],
   "voter_note": "2027 투표는 이사로 남을 때(조건부)"
  },
  {
   "key": "williams",
   "name_ko": "존 윌리엄스",
   "name_en": "John C. Williams",
   "role_short": "뉴욕 연은·FOMC 부의장",
   "seat": "ny",
   "district": 2,
   "voter_2026": true,
   "voter_2027": true,
   "bg_type": "혼합",
   "bg_line": "테일러 제자, 연준 연구직·r* 모형 → SF·뉴욕 연은 총재",
   "camp": "중도",
   "stance_now": 0.5,
   "stance_start_2026": -0.5,
   "stance_basis": "'서두를 필요 없다', 전망대로면 연말 한 번 더(조건부), 2027엔 불필요. 연초는 완화 쪽",
   "shift_note": "연초 완화 쪽 → 7월 '잘 자리 잡음' → 9월 '연말 한 번 더'",
   "journey": [
    {
     "from": "1984",
     "to": "1984",
     "org": "University of California, Berkeley",
     "org_ko": "UC버클리",
     "kind": "school",
     "place": "Berkeley, CA",
     "lat": 37.8719,
     "lon": -122.2585,
     "note": "학사(뉴욕 연은 약력). 1984는 사전 지식",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "London School of Economics",
     "org_ko": "런던정경대(LSE)",
     "kind": "school",
     "place": "London, United Kingdom",
     "lat": 51.5144,
     "lon": -0.1165,
     "note": "석사, '1980년대 말'(본인)",
     "cert": "1차"
    },
    {
     "from": "1989",
     "to": "1994",
     "org": "Stanford University",
     "org_ko": "스탠퍼드대",
     "kind": "school",
     "place": "Stanford, CA",
     "lat": 37.4275,
     "lon": -122.1697,
     "note": "경제학 박사, 지도교수 존 테일러",
     "cert": "1차"
    },
    {
     "from": "1994",
     "to": null,
     "org": "Federal Reserve Board",
     "org_ko": "연준 이사회",
     "kind": "fed",
     "place": "Washington, DC",
     "lat": 38.8929,
     "lon": -77.0459,
     "note": "이코노미스트(1994, 뉴욕 연은 약력), 2000-12 LW r* 메모",
     "cert": "1차"
    },
    {
     "from": null,
     "to": "2000",
     "org": "White House Council of Economic Advisers",
     "org_ko": "백악관 경제자문위원회(CEA)",
     "kind": "government",
     "place": "Washington, DC",
     "lat": 38.8975,
     "lon": -77.039,
     "note": "파견, 2000-07 이사회 복귀",
     "cert": "1차"
    },
    {
     "from": "2002",
     "to": "2011",
     "org": "Federal Reserve Bank of San Francisco",
     "org_ko": "샌프란시스코 연은",
     "kind": "fed",
     "place": "San Francisco, CA",
     "lat": 37.793,
     "lon": -122.399,
     "note": "2002 입행, 연구국장·수석부총재(뉴욕 연은 약력)",
     "cert": "1차"
    },
    {
     "from": "2011",
     "to": "2018",
     "org": "Federal Reserve Bank of San Francisco",
     "org_ko": "샌프란시스코 연은",
     "kind": "fed",
     "place": "San Francisco, CA",
     "lat": 37.793,
     "lon": -122.399,
     "note": "총재(2011-03 무렵 취임, 추정)",
     "cert": "1차"
    },
    {
     "from": "2018",
     "to": null,
     "org": "Federal Reserve Bank of New York",
     "org_ko": "뉴욕 연은",
     "kind": "fed",
     "place": "New York, NY",
     "lat": 40.7083,
     "lon": -74.0087,
     "note": "총재 겸 FOMC 부의장",
     "cert": "1차",
     "now": true
    }
   ],
   "style": [
    "대중문화 제목·인용, 매번 성장·실업·물가 점 전망",
    "'totality of the data' 정형구, 뉴욕 연은 자체 지표 근거",
    "성명 문구를 연설에서 먼저 씀('accumulation of more data' 9/29 → 10/28 성명), 되풀이도('timelier return')"
   ],
   "phrases": [
    {
     "text": "The accumulation of more data should provide greater clarity",
     "date": "2026-09-29"
    },
    {
     "text": "getting inflation back to 2 percent is job No. 1",
     "date": "2026-09-29"
    },
    {
     "text": "there is no need for urgency",
     "date": "2026-09-29"
    }
   ],
   "dissents_2026": [],
   "recent": [
    {
     "date": "2026-10-28",
     "text": "동결 찬성(성명 10-2, 반대는 쿡·해맥뿐)"
    },
    {
     "date": "2026-10-13",
     "text": "블룸버그 인터뷰: 연말 1회 더 견해 그대로, 2027 추가 인상 불필요(2차)"
    },
    {
     "date": "2026-09-24",
     "text": "런던: 연말 전 추가 인상 '합리적', 10월은 확약 안 함(2차)"
    },
    {
     "date": "2026-09-29",
     "text": "버펄로대: 물가 3.7% '너무 높다', 전망대로면 연말 한 번 더"
    },
    {
     "date": "2026-09-22",
     "text": "국채시장 회의: 중앙청산 전환 순조, 실행 3원칙"
    },
    {
     "date": "2026-07-15",
     "text": "'현재 정책 잘 자리 잡음', 물가 정점 지났다고 볼 이유 여섯"
    }
   ],
   "baseline": {
    "usual": [
     "'물가 너무 높다·1번 과제'",
     "'서두를 필요 없다'·'데이터 전체(totality)'",
     "조건부 '연말 한 번 더 인상'",
     "전망: 성장 2¼%·실업 4%·물가 26년 3½%→27년 2% 초반",
     "1회 뒤 2027 추가 인상 불필요·'전반적 과열 아님'",
     "기대 인플레 잘 고정·노동은 물가 압력 아님(HPW)"
    ],
    "hawk_surprise": [
     "12월 인상 무조건·2회 이상·2027 추가 인상 시사",
     "'충분히 긴축적이지 않다'·AI로 r* 상향",
     "기대 인플레 이탈 인정",
     "인상 쪽 반대표"
    ],
    "dove_surprise": [
     "12월 전 '연말 1회 더' 철회하고 '현 정책 잘 자리 잡음'",
     "노동 하방 위험 재강조",
     "에너지·AI 물가는 대응 없이 넘겨본다(look through) 명시",
     "금융여건 악화를 동결 근거로"
    ]
   },
   "review": "approved",
   "watch": "11-06 ECB 대담 등 11월 '연말 한 번 더'·'2027 불필요' 유지 여부, 12월 SEP 대비 본인 물가 전망",
   "conf": "연설·약력은 뉴욕 연은 원문(2026-11-04 확인), 표결은 성명, 학부 연도는 사전 지식, 10-13 인터뷰는 2차",
   "sources": [
    {
     "outlet": "뉴욕 연은 연설(1차)",
     "date": "2026-09-29",
     "url": "https://www.newyorkfed.org/newsevents/speeches/2026/wil260929"
    },
    {
     "outlet": "뉴욕 연은 연설(1차)",
     "date": "2026-09-22",
     "url": "https://www.newyorkfed.org/newsevents/speeches/2026/wil260922"
    },
    {
     "outlet": "뉴욕 연은 연설(1차)",
     "date": "2026-07-15",
     "url": "https://www.newyorkfed.org/newsevents/speeches/2026/wil260715"
    },
    {
     "outlet": "연준 보도자료 — 총재 재임명(검색 조각)",
     "date": "2025-12-11",
     "url": "https://www.federalreserve.gov/newsevents/pressreleases/other20251211a.htm"
    },
    {
     "outlet": "investinglive",
     "date": "2025-09-17",
     "url": "https://investinglive.com/news/fomc-hawks-and-doves-a-comprehensive-overview-20250917/amp"
    },
    {
     "outlet": "뉴욕 연은 총재 약력(1차)",
     "date": "2026-11-04",
     "url": "https://www.newyorkfed.org/aboutthefed/orgchart/williams"
    },
    {
     "outlet": "Bloomberg(2차)",
     "date": "2026-10-13",
     "url": "https://www.bloomberg.com/news/articles/2026-10-13/fed-s-williams-currently-sees-no-need-for-rate-hike-in-2027"
    }
   ],
   "camp_src": [
    {
     "outlet": "investinglive",
     "date": "2025-09-17",
     "url": "https://investinglive.com/news/fomc-hawks-and-doves-a-comprehensive-overview-20250917/amp"
    }
   ]
  },
  {
   "key": "collins",
   "name_ko": "수전 콜린스",
   "name_en": "Susan M. Collins",
   "role_short": "보스턴 연은 총재",
   "seat": "bank",
   "district": 1,
   "voter_2026": false,
   "voter_2027": false,
   "bg_type": "학계",
   "bg_line": "MIT 박사, 하버드·조지타운 교수 → 미시간대 학장·교무처장",
   "camp": "미상",
   "stance_now": 1,
   "stance_start_2026": -0.5,
   "stance_basis": "'연말 전 조금 더 인상' 예상(횟수 미언급). 3월엔 '조정 긴급성 없음'",
   "shift_note": "3월 '긴급성 없음' → 5월 '인내 줄어' → 10월 '조금 더 인상'",
   "journey": [
    {
     "from": null,
     "to": null,
     "org": "Scotland (birthplace)",
     "org_ko": "출생지 스코틀랜드",
     "kind": "other",
     "place": "Scotland, United Kingdom",
     "lat": 56.4907,
     "lon": -4.2026,
     "note": "출생(도시 미기재, 부모 자메이카)",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "New York City (hometown)",
     "org_ko": "성장지 뉴욕(맨해튼)",
     "kind": "other",
     "place": "New York, NY",
     "lat": 40.7831,
     "lon": -73.9712,
     "note": "맨해튼에서 자람",
     "cert": "1차"
    },
    {
     "from": "1980",
     "to": "1980",
     "org": "Harvard University",
     "org_ko": "하버드대",
     "kind": "school",
     "place": "Cambridge, MA",
     "lat": 42.377,
     "lon": -71.1167,
     "note": "AB(사전 지식)",
     "cert": "사전 지식"
    },
    {
     "from": null,
     "to": null,
     "org": "Massachusetts Institute of Technology",
     "org_ko": "MIT",
     "kind": "school",
     "place": "Cambridge, MA",
     "lat": 42.3601,
     "lon": -71.0942,
     "note": "경제학 박사(1984 무렵, 추론)",
     "cert": "1차"
    },
    {
     "from": "1984",
     "to": "1992",
     "org": "Harvard University",
     "org_ko": "하버드대",
     "kind": "academia",
     "place": "Cambridge, MA",
     "lat": 42.377,
     "lon": -71.1167,
     "note": "경제학과 교수진(국제거시)",
     "cert": "1차"
    },
    {
     "from": "1989",
     "to": "1990",
     "org": "White House Council of Economic Advisers",
     "org_ko": "백악관 경제자문위원회(CEA)",
     "kind": "government",
     "place": "Washington, DC",
     "lat": 38.8975,
     "lon": -77.039,
     "note": "국제거시 선임 스태프 1년",
     "cert": "1차"
    },
    {
     "from": "1992",
     "to": "2007",
     "org": "Georgetown University",
     "org_ko": "조지타운대",
     "kind": "academia",
     "place": "Washington, DC",
     "lat": 38.9076,
     "lon": -77.0723,
     "note": "교수",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "Brookings Institution",
     "org_ko": "브루킹스 연구소",
     "kind": "other",
     "place": "Washington, DC",
     "lat": 38.9095,
     "lon": -77.0397,
     "note": "선임 펠로(약 30년 관계)",
     "cert": "1차"
    },
    {
     "from": "2007",
     "to": "2017",
     "org": "University of Michigan Ford School",
     "org_ko": "미시간대 포드스쿨",
     "kind": "academia",
     "place": "Ann Arbor, MI",
     "lat": 42.2766,
     "lon": -83.7383,
     "note": "학장 10년(연도는 추론)",
     "cert": "1차"
    },
    {
     "from": "2020",
     "to": "2022",
     "org": "University of Michigan",
     "org_ko": "미시간대",
     "kind": "academia",
     "place": "Ann Arbor, MI",
     "lat": 42.278,
     "lon": -83.7382,
     "note": "교무처장(연도는 사전 지식)",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "Federal Reserve Bank of Chicago",
     "org_ko": "시카고 연은",
     "kind": "fed",
     "place": "Chicago, IL",
     "lat": 41.8789,
     "lon": -87.6324,
     "note": "이사회 이사 9년",
     "cert": "1차"
    },
    {
     "from": "2022",
     "to": null,
     "org": "Federal Reserve Bank of Boston",
     "org_ko": "보스턴 연은",
     "kind": "fed",
     "place": "Boston, MA",
     "lat": 42.3523,
     "lon": -71.0553,
     "note": "총재(2022-07~)",
     "cert": "1차",
     "now": true
    }
   ],
   "style": [
    "'Key Takeaways'로 시작, 최빈 시나리오+대안 시나리오",
    "자기 전망을 SEP 중앙값·참가자 전망에 비춰 말함",
    "뉴잉글랜드 기업·은행 일화, 비정책 행사엔 전망 안 함"
   ],
   "phrases": [
    {
     "text": "raise rates a bit further before the end of the year",
     "date": "2026-10-13"
    },
    {
     "text": "almost as likely",
     "date": "2026-10-13"
    },
    {
     "text": "continued evidence that inflation is indeed coming down",
     "date": "2026-08-25"
    }
   ],
   "dissents_2026": [],
   "recent": [
    {
     "date": "2026-10-13",
     "text": "커뮤니티 은행 콘퍼런스: 9월 인상 지지, '연말 전 조금 더'"
    },
    {
     "date": "2026-10-09",
     "text": "리히 추모 콘퍼런스: 경제·정책 언급 안 함"
    },
    {
     "date": "2026-08-25",
     "text": "서면 전망: 지속 진전 증거 없으면 곧 긴축"
    },
    {
     "date": "2026-05-13",
     "text": "보스턴 이코노믹 클럽: 공급 충격 넘겨볼 인내 줄었다"
    }
   ],
   "baseline": {
    "usual": [
     "'연말 전 조금 더'·'데이터 전체'",
     "최빈 시나리오: 효율 향상 디스인플레",
     "물가가 에너지·AI 품목에 갇혔나"
    ],
    "hawk_surprise": [
     "50bp·'여러 번' 인상",
     "기대 인플레가 풀렸다 단정",
     "생산성 낙관 시나리오 폐기",
     "10월 동결이 잘못"
    ],
    "dove_surprise": [
     "12월 인상 불필요·2027 인하",
     "노동 하방(AI 대체)을 주된 위험으로",
     "에너지 충격 look-through"
    ]
   },
   "review": "draft",
   "watch": "11월에 '연말 전 조금 더' 유지 여부(비투표, 다음 투표 2028)",
   "conf": "연설은 1차 사본(보스턴 연은 미러), 10-13 일부는 2차, 학부는 사전 지식",
   "sources": [
    {
     "outlet": "보스턴 연은 연설(1차 사본)",
     "date": "2026-10-13",
     "url": "https://www.bostonfed.org/news-and-events/speeches/2026/perspectives-economy-banking-landscape.aspx"
    },
    {
     "outlet": "Reuters via Kitco",
     "date": "2026-10-13",
     "url": "https://www.kitco.com/news/off-the-wire/2026-10-13/feds-collins-sees-another-rate-hike-table-end-2026"
    },
    {
     "outlet": "보스턴 연은 서면(1차 사본)",
     "date": "2026-08-25",
     "url": "https://www.bostonfed.org/news-and-events/speeches/2026/perspectives-on-the-economy.aspx"
    },
    {
     "outlet": "보스턴 연은 연설(1차 사본, 약력)",
     "date": "2022-09-26",
     "url": "https://www.bostonfed.org/news-and-events/speeches/2022/perspectives-on-the-economy-and-on-the-opportunities-ahead.aspx"
    }
   ]
  },
  {
   "key": "paulson",
   "name_ko": "애나 폴슨",
   "name_en": "Anna L. Paulson",
   "role_short": "필라델피아 연은 총재",
   "seat": "bank",
   "district": 3,
   "voter_2026": true,
   "voter_2027": false,
   "bg_type": "학계",
   "bg_line": "시카고 연은 연구국장 출신 연구 경제학자, 가계 금융 연구",
   "camp": "스윙",
   "stance_now": 1,
   "stance_start_2026": -1,
   "stance_basis": "'예상대로면 소폭 추가 긴축 정당화', 표는 늘 다수. 1월엔 '연내 소폭 인하' 전망",
   "shift_note": "1월 '연내 소폭 인하' → 5월 '인하는 진전 뒤' → 8월 '열린 마음' → 9월 '소폭 추가 긴축'",
   "journey": [
    {
     "from": null,
     "to": null,
     "org": "Carleton College",
     "org_ko": "칼턴 칼리지",
     "kind": "school",
     "place": "Northfield, MN",
     "lat": 44.4626,
     "lon": -93.1539,
     "note": "학사(연준 약력)",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "University of Chicago",
     "org_ko": "시카고대",
     "kind": "school",
     "place": "Chicago, IL",
     "lat": 41.7886,
     "lon": -87.5987,
     "note": "경제학 박사(연준 약력)",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "Northwestern University Kellogg School",
     "org_ko": "노스웨스턴대 켈로그",
     "kind": "academia",
     "place": "Evanston, IL",
     "lat": 42.0565,
     "lon": -87.6753,
     "note": "재무 조교수(연준 약력, 프린스턴 박사후 뒤)",
     "cert": "1차"
    },
    {
     "from": "2001",
     "to": "2025",
     "org": "Federal Reserve Bank of Chicago",
     "org_ko": "시카고 연은",
     "kind": "fed",
     "place": "Chicago, IL",
     "lat": 41.8789,
     "lon": -87.6324,
     "note": "이코노미스트→수석부총재·연구국장",
     "cert": "1차"
    },
    {
     "from": "2025",
     "to": null,
     "org": "Federal Reserve Bank of Philadelphia",
     "org_ko": "필라델피아 연은",
     "kind": "fed",
     "place": "Philadelphia, PA",
     "lat": 39.9526,
     "lon": -75.1503,
     "note": "총재(2025-07~)",
     "cert": "1차",
     "now": true
    }
   ],
   "style": [
    "쉬운 영어·이야기형(히치봇 일화, R*='mythical beast')",
    "물가를 상품·주거·서비스로 분해, 기조 물가를 본다",
    "의견은 연설로, 표는 합의로 — 반대표 0"
   ],
   "phrases": [
    {
     "text": "returning inflation to 2 percent is non-negotiable",
     "date": "2026-09-24"
    },
    {
     "text": "some modest further tightening may be warranted",
     "date": "2026-09-24"
    }
   ],
   "dissents_2026": [],
   "recent": [
    {
     "date": "2026-10-28",
     "text": "동결 찬성(추론 — 인상파 반대에 합류 안 함)"
    },
    {
     "date": "2026-09-24",
     "text": "핀테크 콘퍼런스: 인상 지지, '소폭 추가 긴축 정당화될 수도'"
    },
    {
     "date": "2026-08-04",
     "text": "에세이 'Keeping an Open Mind': 동결 지지, 진전 없으면 더 제약적"
    },
    {
     "date": "2026-05-19",
     "text": "애틀랜타 연은 콘퍼런스: '약간 긴축적', 인하는 진전 뒤에만"
    }
   ],
   "baseline": {
    "usual": [
     "'소폭 추가 긴축 정당화 가능'",
     "'too high for too long'",
     "AI 투자 수요가 물가를 올림",
     "기조 물가 2.5~3%, R* 약 3.1%"
    ],
    "hawk_surprise": [
     "인상 쪽 반대표",
     "'두 번 더'·연속·50bp",
     "조건 없이 '추가 인상 필요' 단정",
     "장기 기대 이탈 단정"
    ],
    "dove_surprise": [
     "9-24 문장 철회",
     "인하·노동 위험을 물가 위로",
     "9월 인상이 과했다",
     "1990년대 '인내'로 추가 긴축 불필요"
    ]
   },
   "review": "approved",
   "watch": "블랙아웃 전 11월 발언에서 9-24 문장 유지·강화·철회",
   "conf": "연설·표결·약력은 1차, 10-28 찬성은 추론(의사록 전)",
   "sources": [
    {
     "outlet": "필라델피아 연은 연설(1차 사본)",
     "date": "2026-09-24",
     "url": "https://www.philadelphiafed.org/the-economy/monetary-policy/260924-10th-annual-fintech-conference-speech"
    },
    {
     "outlet": "필라델피아 연은 연설(1차 사본)",
     "date": "2026-05-19",
     "url": "https://www.philadelphiafed.org/the-economy/monetary-policy/260519-2026-financial-markets-conference"
    },
    {
     "outlet": "필라델피아 연은 에세이(1차)",
     "date": "2026-08-04",
     "url": "https://www.philadelphiafed.org/the-economy/monetary-policy/monetary-policy-perspective-keeping-an-open-mind"
    },
    {
     "outlet": "Axios",
     "date": "2025-04-17",
     "url": "https://www.axios.com/2025/04/17/federal-reserve-philadelphia-interest-rates"
    },
    {
     "outlet": "Reuters via Kitco",
     "date": "2026-01-06",
     "url": "https://www.kitco.com/news/off-the-wire/2026-01-06/fed-hawks-and-doves-what-us-central-bankers-are-saying"
    },
    {
     "outlet": "연준 이사회 — 필라델피아 연은 총재 약력(1차)",
     "date": "2026-11-04",
     "url": "https://www.federalreserve.gov/aboutthefed/federal-reserve-system-philadelphia.htm"
    }
   ],
   "camp_src": [
    {
     "outlet": "Reuters via Kitco",
     "date": "2026-01-06",
     "url": "https://www.kitco.com/news/off-the-wire/2026-01-06/fed-hawks-and-doves-what-us-central-bankers-are-saying"
    }
   ]
  },
  {
   "key": "hammack",
   "name_ko": "베스 해맥",
   "name_en": "Beth M. Hammack",
   "role_short": "클리블랜드 연은 총재",
   "seat": "bank",
   "district": 4,
   "voter_2026": true,
   "voter_2027": false,
   "bg_type": "실무(시장)",
   "bg_line": "골드만 30년: 트레저러·레포·파이낸싱 공동대표, TBAC 의장(전)",
   "camp": "매파",
   "stance_now": 2,
   "stance_start_2026": 0,
   "stance_basis": "+25bp씩 '작게, 비교적 빨리', 올해 반대 3회(4월 문구·7·10월 인상). 2월엔 '인내'",
   "shift_note": "2월 '중립 부근·인내' → 4·7·10월 매파 쪽 반대",
   "journey": [
    {
     "from": null,
     "to": null,
     "org": "Stanford University",
     "org_ko": "스탠퍼드대",
     "kind": "school",
     "place": "Stanford, CA",
     "lat": 37.4275,
     "lon": -122.1697,
     "note": "학사(계량경제학·역사, 연준 약력)",
     "cert": "1차"
    },
    {
     "from": "1993",
     "to": null,
     "org": "Goldman Sachs",
     "org_ko": "골드만삭스",
     "kind": "company",
     "place": "New York, NY",
     "lat": 40.7149,
     "lon": -74.0145,
     "note": "1993~, 2010 파트너·파이낸싱 그룹 공동대표(연은 약력)",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "Treasury Borrowing Advisory Committee",
     "org_ko": "재무부 국채차입자문위(TBAC)",
     "kind": "other",
     "place": "Washington, DC",
     "lat": 38.8987,
     "lon": -77.0342,
     "note": "의장(전, 연준 약력)",
     "cert": "1차"
    },
    {
     "from": "2024",
     "to": null,
     "org": "Federal Reserve Bank of Cleveland",
     "org_ko": "클리블랜드 연은",
     "kind": "fed",
     "place": "Cleveland, OH",
     "lat": 41.5025,
     "lon": -81.69,
     "note": "총재(2024-08-21~, 메스터 후임)",
     "cert": "1차",
     "now": true
    }
   ],
   "style": [
    "반대표를 의사표시로 쓰고, 연은 웹에 설명 성명",
    "조건부 '반응함수'로 말함 — 포워드 가이던스 거부",
    "클리블랜드 자체 지표(중위·절사평균)와 지역 일화"
   ],
   "phrases": [
    {
     "text": "A reaction function is not forward guidance",
     "date": "2026-10-12"
    },
    {
     "text": "in a timely fashion",
     "date": "2024-12-20"
    }
   ],
   "dissents_2026": [
    {
     "date": "2026-04-29",
     "side": "문구"
    },
    {
     "date": "2026-07-29",
     "side": "인상"
    },
    {
     "date": "2026-10-28",
     "side": "인상"
    }
   ],
   "recent": [
    {
     "date": "2026-10-28",
     "text": "동결에 반대, +25bp 인상(쿡과 함께)"
    },
    {
     "date": "2026-10-12",
     "text": "NABE 'Trimming the Sails': 제약적 스탠스, 작게·비교적 빨리"
    },
    {
     "date": "2026-09-16",
     "text": "+25bp 인상 찬성(12-0)"
    },
    {
     "date": "2026-07-29",
     "text": "동결에 반대, +25bp(카시카리·로건과 함께)"
    }
   ],
   "baseline": {
    "usual": [
     "'충분히 제약적이지 않다'",
     "주거 제외 근원 서비스·'inflationary mindset'",
     "가이던스 거부, 조건부 반응함수",
     "인상 1번으론 부족, 작게·빨리"
    ],
    "hawk_surprise": [
     "50bp·12월에도 '더 크게' 반대",
     "장기 기대 'unanchored' 선언",
     "QT 재개·RMP 중단 요구",
     "인상 횟수·도달 금리 명시"
    ],
    "dove_surprise": [
     "12월 동결에 반대 없이 찬성",
     "한 번 더 뒤 '충분히 제약적'",
     "에너지·관세 넘겨보고 추가 인상 불필요",
     "노동 악화·인하 언급"
    ]
   },
   "review": "approved",
   "watch": "12월 표: 인상이면 폭, 동결이면 반대 여부",
   "conf": "표결·약력·연설은 1차, 10월 반대 설명문은 미확인",
   "sources": [
    {
     "outlet": "클리블랜드 연은 연설(1차 사본)",
     "date": "2026-10-12",
     "url": "https://www.clevelandfed.org/collections/speeches/2026/sp-20261012-trimming-the-sails-communicating-my-reaction-function"
    },
    {
     "outlet": "연준 FOMC 성명(1차)",
     "date": "2026-10-28",
     "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm"
    },
    {
     "outlet": "연준 FOMC 성명(1차)",
     "date": "2026-07-29",
     "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260729a.htm"
    },
    {
     "outlet": "클리블랜드 연은 연설(1차 사본)",
     "date": "2026-06-02",
     "url": "https://www.clevelandfed.org/collections/speeches/2026/sp-20260602-it-takes-two-to-make-an-economy-go-right"
    },
    {
     "outlet": "CNN 라이브",
     "date": "2026-10-28",
     "url": "https://www.cnn.com/2026/10/28/business/live-news/federal-reserve-interest-rate-october"
    },
    {
     "outlet": "클리블랜드 연은 — 2024-12 반대 성명(1차)",
     "date": "2024-12-20",
     "url": "https://www.clevelandfed.org/collections/speeches/2024/sp-20241220-fomc-statement-president-beth-hammack"
    },
    {
     "outlet": "연준 FOMC 성명(1차)",
     "date": "2026-04-29",
     "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260429a.htm"
    },
    {
     "outlet": "연준 이사회 — 클리블랜드 연은 총재 약력(1차)",
     "date": "2026-11-04",
     "url": "https://www.federalreserve.gov/aboutthefed/federal-reserve-system-cleveland.htm"
    }
   ],
   "camp_src": [
    {
     "outlet": "CNN 라이브",
     "date": "2026-10-28",
     "url": "https://www.cnn.com/2026/10/28/business/live-news/federal-reserve-interest-rate-october"
    }
   ]
  },
  {
   "key": "barkin",
   "name_ko": "토머스 바킨",
   "name_en": "Thomas I. Barkin",
   "role_short": "리치먼드 연은 총재",
   "seat": "bank",
   "district": 5,
   "voter_2026": false,
   "voter_2027": true,
   "bg_type": "실무(경영)",
   "bg_line": "맥킨지 30년(CFO·위험책임자) → 애틀랜타 연은 이사 → 총재",
   "camp": "중도",
   "stance_now": 0.5,
   "stance_start_2026": 0,
   "stance_basis": "물가 우선 서술, 추가 인상은 'We'll see'. 3월엔 '동결이 신중'",
   "shift_note": "3월 '동결이 신중' → 9월 인상 설명 → 추가는 'We'll see'",
   "journey": [
    {
     "from": null,
     "to": null,
     "org": "Harvard University",
     "org_ko": "하버드대",
     "kind": "school",
     "place": "Cambridge, MA",
     "lat": 42.377,
     "lon": -71.1167,
     "note": "학사·JD·MBA(사전 지식), '80년대 대학'",
     "cert": "사전 지식"
    },
    {
     "from": "1987",
     "to": "2017",
     "org": "McKinsey & Company (Atlanta)",
     "org_ko": "맥킨지(애틀랜타)",
     "kind": "company",
     "place": "Atlanta, GA",
     "lat": 33.749,
     "lon": -84.388,
     "note": "CFO·최고위험책임자·남부 총괄",
     "cert": "1차"
    },
    {
     "from": "2009",
     "to": "2014",
     "org": "Federal Reserve Bank of Atlanta",
     "org_ko": "애틀랜타 연은",
     "kind": "fed",
     "place": "Atlanta, GA",
     "lat": 33.7816,
     "lon": -84.3871,
     "note": "이사회 이사, 그중 2년 의장",
     "cert": "1차"
    },
    {
     "from": "2018",
     "to": null,
     "org": "Federal Reserve Bank of Richmond",
     "org_ko": "리치먼드 연은",
     "kind": "fed",
     "place": "Richmond, VA",
     "lat": 37.5374,
     "lon": -77.4337,
     "note": "총재(2018-01~)",
     "cert": "1차",
     "now": true
    }
   ],
   "style": [
    "현장 일화·설문(CFO Survey) 근거, 비유 많은 쉬운 말",
    "회의별 지침은 피함('Our Lips Are Sealed'), 결정은 뒤에 설명",
    "매번 양쪽 시나리오와 하방 목록을 나란히"
   ],
   "phrases": [
    {
     "text": "inflation is our troublemaker",
     "date": "2026-09-22"
    },
    {
     "text": "Will additional hikes be required, and how many? We'll see.",
     "date": "2026-09-22"
    },
    {
     "text": "My custom is to never prejudge the path forward",
     "date": "2026-08-13"
    }
   ],
   "dissents_2026": [],
   "recent": [
    {
     "date": "2026-09-22",
     "text": "'Why Hike?'(볼티모어): 물가가 말썽꾼, 추가 인상은 'We'll see'"
    },
    {
     "date": "2026-08-13",
     "text": "그린빌: 'YOLO' 소비·AI 투자, 경로는 미리 정하지 않음"
    },
    {
     "date": "2026-05-21",
     "text": "롤리: 공급 충격 넘겨보기 세 질문, 장기 기대 'well anchored'"
    },
    {
     "date": "2026-03-27",
     "text": "존슨시티: 중립 상단, PCE 진전 'stalling' 위험"
    }
   ],
   "baseline": {
    "usual": [
     "추가 인상 'We'll see'",
     "기업 일화·CFO 설문 숫자",
     "하방 목록(소비·시장 조정·고용) 나열",
     "'다음 회의 지침 없음'"
    ],
    "hawk_surprise": [
     "12월 인상 회의 전 명시 지지",
     "인상 횟수·도달 금리 제시",
     "'뒤처졌다'",
     "2027 반대 시사"
    ],
    "dove_surprise": [
     "9월은 일회성·추가 인상 불필요",
     "위험 무게가 고용으로",
     "공급 충격 무조건 넘겨보기",
     "인하 언급"
    ]
   },
   "review": "draft",
   "watch": "2027 첫 투표 해 1월 전망 연설, 12월 전 회의 방향 문장",
   "conf": "연설·의사록은 1차 사본, 학력·맥킨지 연도는 사전 지식",
   "sources": [
    {
     "outlet": "리치먼드 연은 연설(1차 사본)",
     "date": "2026-09-22",
     "url": "https://www.richmondfed.org/press_room/speeches/thomas_i_barkin/2026/barkin_speech_20260922"
    },
    {
     "outlet": "리치먼드 연은 연설(1차 사본)",
     "date": "2026-08-13",
     "url": "https://www.richmondfed.org/press_room/speeches/thomas_i_barkin/2026/barkin_speech_20260813"
    },
    {
     "outlet": "리치먼드 연은 연설(1차 사본)",
     "date": "2026-05-21",
     "url": "https://www.richmondfed.org/press_room/speeches/thomas_i_barkin/2026/barkin_speech_20260521"
    },
    {
     "outlet": "리치먼드 연은 연설(1차 사본, 약력)",
     "date": "2018-08-08",
     "url": "https://www.richmondfed.org/press_room/speeches/thomas_i_barkin/2018/barkin_speech_20180808"
    }
   ],
   "camp_src": [
    {
     "outlet": "리치먼드 연은 연설",
     "date": "2026-09-22",
     "url": "https://www.richmondfed.org/press_room/speeches/thomas_i_barkin/2026/barkin_speech_20260922"
    }
   ]
  },
  {
   "key": "venable",
   "name_ko": "셰릴 베너블",
   "name_en": "Cheryl L. Venable",
   "role_short": "애틀랜타 연은 임시 총재",
   "seat": "bank",
   "district": 6,
   "voter_2026": false,
   "voter_2027": true,
   "bg_type": "정책 관료",
   "bg_line": "애틀랜타 연은 수석부총재(운영 책임), 이전 경력 미확인",
   "camp": "미상",
   "stance_now": null,
   "stance_start_2026": null,
   "stance_basis": "통화정책 공개 발언 없음 — 판단 불가(침묵이 기준선)",
   "shift_note": "입장 변화 기록 없음, 정식 총재 인선이 관건",
   "journey": [
    {
     "from": null,
     "to": "2026",
     "org": "Federal Reserve Bank of Atlanta",
     "org_ko": "애틀랜타 연은",
     "kind": "fed",
     "place": "Atlanta, GA",
     "lat": 33.7816,
     "lon": -84.3871,
     "note": "수석부총재(취임일 미확인)",
     "cert": "1차"
    },
    {
     "from": "2026",
     "to": null,
     "org": "Federal Reserve Bank of Atlanta",
     "org_ko": "애틀랜타 연은",
     "kind": "fed",
     "place": "Atlanta, GA",
     "lat": 33.7816,
     "lon": -84.3871,
     "note": "임시 총재 겸 CEO(2026-03~)",
     "cert": "1차",
     "now": true
    }
   ],
   "style": [
    "정책 연설·인터뷰 기록 없음(조사 범위 안)",
    "발언하면 지역경제·운영·지급결제 위주일 것(추정)"
   ],
   "phrases": [],
   "dissents_2026": [],
   "recent": [
    {
     "date": "2026-10-28",
     "text": "FOMC 대체위원 — 투표권 없음"
    },
    {
     "date": "2026-10-07",
     "text": "9월 의사록에 대체위원으로 — 임시 체제 1차 확인"
    },
    {
     "date": "2026-06-23",
     "text": "CNBC: 정식 총재 후보로 포켄더 검토 보도(지위 미상)"
    },
    {
     "date": "2026-03-01",
     "text": "보스틱 퇴임 뒤 임시 총재 겸 CEO"
    }
   ],
   "baseline": {
    "usual": [
     "지역경제·운영 이야기(추정)"
    ],
    "hawk_surprise": [
     "추가 인상 공개 요구",
     "금리 경로 명시 자체"
    ],
    "dove_surprise": [
     "인상 종료·인하 공개 주장"
    ]
   },
   "review": "draft",
   "watch": "정식 총재 발표(포켄더 등), 2027-01 애틀랜타 몫 투표자",
   "conf": "직함·대체위원은 1차(의사록·검색 조각), 학력·경력·한글 표기 미확인",
   "sources": [
    {
     "outlet": "애틀랜타 연은 총재 선임 페이지(검색 조각)",
     "date": "2026",
     "url": "https://www.atlantafed.org/presidentialsearch"
    },
    {
     "outlet": "연준 FOMC 의사록(1월 회의)",
     "date": "2026-02-18",
     "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260218a.htm"
    },
    {
     "outlet": "CNBC",
     "date": "2026-06-23",
     "url": "https://www.cnbc.com/amp/2026/06/23/fed-warsh-atlanta-michael-faulkender.html"
    }
   ],
   "voter_note": "2027 애틀랜타 표는 그때도 임시 체제면 그녀"
  },
  {
   "key": "goolsbee",
   "name_ko": "오스탄 굴스비",
   "name_en": "Austan D. Goolsbee",
   "role_short": "시카고 연은 총재",
   "seat": "bank",
   "district": 7,
   "voter_2026": false,
   "voter_2027": true,
   "bg_type": "혼합",
   "bg_line": "MIT 박사·시카고대 부스 교수, 오바마 정부 CEA 의장",
   "camp": "스윙",
   "stance_now": 1,
   "stance_start_2026": 0,
   "stance_basis": "'지속 공급 충격은 못 넘겨본다', 조건부 추가 긴축 쪽. 3월엔 양방향",
   "shift_note": "25-12 동결 쪽 반대 → 3월 양방향 → 9월 '어려운 길뿐'",
   "journey": [
    {
     "from": "1991",
     "to": "1991",
     "org": "Yale University",
     "org_ko": "예일대",
     "kind": "school",
     "place": "New Haven, CT",
     "lat": 41.3163,
     "lon": -72.9223,
     "note": "경제학 학사·석사(사전 지식)",
     "cert": "사전 지식"
    },
    {
     "from": "1995",
     "to": "1995",
     "org": "Massachusetts Institute of Technology",
     "org_ko": "MIT",
     "kind": "school",
     "place": "Cambridge, MA",
     "lat": 42.3601,
     "lon": -71.0942,
     "note": "경제학 박사(사전 지식)",
     "cert": "사전 지식"
    },
    {
     "from": "1995",
     "to": null,
     "org": "University of Chicago Booth School of Business",
     "org_ko": "시카고대 부스",
     "kind": "academia",
     "place": "Chicago, IL",
     "lat": 41.7894,
     "lon": -87.5956,
     "note": "경제학 교수(Gwinn 석좌)",
     "cert": "사전 지식"
    },
    {
     "from": "2004",
     "to": "2008",
     "org": "Obama Senate & presidential campaigns",
     "org_ko": "오바마 상원·대선 캠프",
     "kind": "other",
     "place": "Chicago, IL",
     "lat": 41.8781,
     "lon": -87.6298,
     "note": "경제 고문(사전 지식)",
     "cert": "사전 지식"
    },
    {
     "from": "2009",
     "to": "2011",
     "org": "White House Council of Economic Advisers",
     "org_ko": "백악관 경제자문위원회(CEA)",
     "kind": "government",
     "place": "Washington, DC",
     "lat": 38.8975,
     "lon": -77.039,
     "note": "위원→의장(2010-09~2011-08)",
     "cert": "사전 지식"
    },
    {
     "from": "2011",
     "to": null,
     "org": "University of Chicago Booth School of Business",
     "org_ko": "시카고대 부스",
     "kind": "academia",
     "place": "Chicago, IL",
     "lat": 41.7894,
     "lon": -87.5956,
     "note": "부스 복귀",
     "cert": "사전 지식"
    },
    {
     "from": "2023",
     "to": null,
     "org": "Federal Reserve Bank of Chicago",
     "org_ko": "시카고 연은",
     "kind": "fed",
     "place": "Chicago, IL",
     "lat": 41.8789,
     "lon": -87.6324,
     "note": "총재(에번스 후임)",
     "cert": "1차",
     "now": true
    }
   ],
   "style": [
    "모형·역사 사례로 조건부 논리를 세우는 학자형 사고실험",
    "쉬운 비유·한 줄('Ten times zero is still zero')",
    "Q&A·패널 등 즉석 형식이 많고 경로는 못박지 않음"
   ],
   "phrases": [
    {
     "text": "don't do nothing. Looking through won't work.",
     "date": "2026-09-21"
    },
    {
     "text": "the only way back is the hard way",
     "date": "2026-09-21"
    },
    {
     "text": "If the central bank reacts too slowly, it makes the problem worse.",
     "date": "2026-05-08"
    }
   ],
   "dissents_2026": [],
   "recent": [
    {
     "date": "2026-09-21",
     "text": "OMFIF: 지속 공급 충격은 넘겨볼 수 없다, 물가 정점이 2027로 밀림"
    },
    {
     "date": "2026-06-22",
     "text": "영상: '인플레가 일자리 감소보다 큰 문제'(2차)"
    },
    {
     "date": "2026-05-08",
     "text": "후버: 기대된 생산성 붐이면 지금 금리를 올려야 할 수도"
    },
    {
     "date": "2026-03-23",
     "text": "블룸버그: 전쟁 전개 따라 인상도 인하 재개도 그릴 수 있다(2차)"
    }
   ],
   "baseline": {
    "usual": [
     "'인플레가 최대 문제'",
     "지속적 공급 충격은 지나쳐 볼 수 없다",
     "기대된 AI 생산성은 적정 금리를 올림",
     "'모든 선택지가 열려 있다'"
    ],
    "hawk_surprise": [
     "12월 인상 명시 지지",
     "'최소 두 번 더'처럼 횟수 못박음",
     "50bp·'behind the curve'",
     "2027 인상 쪽 반대 예고"
    ],
    "dove_surprise": [
     "9월로 '충분'·장기 동결",
     "유가·관세 충격 '지나쳐 보자'",
     "생산성 붐으로 인하 논리",
     "AI주 급락·고용 둔화로 인하 시사"
    ]
   },
   "review": "draft",
   "watch": "11-02 발언: 9월 OMFIF 기준을 최근 자료에 어떻게 적용하나",
   "conf": "2026 원고 2편·의사록은 1차 사본, 학력·경력은 사전 지식, 인터뷰는 2차",
   "sources": [
    {
     "outlet": "시카고 연은 연설(1차 사본)",
     "date": "2026-09-21",
     "url": "https://www.chicagofed.org/publications/speeches/2026/sept-21-omfif"
    },
    {
     "outlet": "시카고 연은 연설(1차 사본)",
     "date": "2026-05-08",
     "url": "https://www.chicagofed.org/publications/speeches/2026/may-8-hoover-institution-monetary-policy"
    },
    {
     "outlet": "Bloomberg",
     "date": "2026-03-23",
     "url": "https://www.bloomberg.com/news/articles/2026-03-23/fed-s-goolsbee-says-he-could-see-circumstances-for-rate-hike"
    },
    {
     "outlet": "연준 FOMC 성명(1차 사본, 2025-12 반대)",
     "date": "2025-12-10",
     "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20251210a.htm"
    }
   ],
   "camp_src": [],
   "camp_cert": "사전 지식"
  },
  {
   "key": "musalem",
   "name_ko": "알베르토 무살렘",
   "name_en": "Alberto G. Musalem",
   "role_short": "세인트루이스 연은 총재",
   "seat": "bank",
   "district": 8,
   "voter_2026": false,
   "voter_2027": false,
   "bg_type": "혼합",
   "bg_line": "IMF → 월가 투자회사 14년 → 뉴욕 연은 → 퀀트 회사 운영",
   "camp": "매파",
   "stance_now": 1.5,
   "stance_start_2026": 0,
   "stance_basis": "'추가 긴축 필요, 이르고 점진적으로'(10-30). 1월엔 '실질 중립, 더 내리면 안 됨'",
   "shift_note": "1월 '실질 중립' → 4월 인상 지지 가능 → 10월 '추가 긴축'",
   "journey": [
    {
     "from": null,
     "to": null,
     "org": "London School of Economics",
     "org_ko": "런던정경대(LSE)",
     "kind": "school",
     "place": "London, United Kingdom",
     "lat": 51.5144,
     "lon": -0.1165,
     "note": "모교(본인), 학사·석사는 사전 지식",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "University of Pennsylvania",
     "org_ko": "펜실베이니아대",
     "kind": "school",
     "place": "Philadelphia, PA",
     "lat": 39.9522,
     "lon": -75.1932,
     "note": "경제학 박사(사전 지식)",
     "cert": "사전 지식"
    },
    {
     "from": "1995",
     "to": "2000",
     "org": "International Monetary Fund",
     "org_ko": "국제통화기금(IMF)",
     "kind": "government",
     "place": "Washington, DC",
     "lat": 38.8988,
     "lon": -77.0434,
     "note": "위기국 지원(본인), 연도 사전 지식",
     "cert": "1차"
    },
    {
     "from": "2000",
     "to": "2013",
     "org": "Tudor Investment Corp.",
     "org_ko": "튜더 인베스트먼트",
     "kind": "company",
     "place": "Stamford, CT",
     "lat": 41.0534,
     "lon": -73.5387,
     "note": "월가 투자회사 14년(본인)·회사명 사전 지식",
     "cert": "사전 지식"
    },
    {
     "from": "2014",
     "to": "2017",
     "org": "Federal Reserve Bank of New York",
     "org_ko": "뉴욕 연은",
     "kind": "fed",
     "place": "New York, NY",
     "lat": 40.7083,
     "lon": -74.0087,
     "note": "'몇 년'(본인), 수석부총재는 사전 지식",
     "cert": "1차"
    },
    {
     "from": "2018",
     "to": "2024",
     "org": "Evince Asset Management",
     "org_ko": "에빈스 자산운용",
     "kind": "company",
     "place": "New York, NY",
     "lat": 40.7128,
     "lon": -74.006,
     "note": "퀀트 회사 운영(본인)·위치 추정",
     "cert": "사전 지식",
     "loc_guess": true
    },
    {
     "from": "2024",
     "to": null,
     "org": "Federal Reserve Bank of St. Louis",
     "org_ko": "세인트루이스 연은",
     "kind": "fed",
     "place": "St. Louis, MO",
     "lat": 38.629,
     "lon": -90.188,
     "note": "총재(2024-04~)",
     "cert": "1차",
     "now": true
    }
   ],
   "style": [
    "요약 먼저·각주 많은 원고에 실질금리·기간 프리미엄 감각",
    "'~이면 ~를 지지' 조건부 양방향, 18개월 시나리오로 말함",
    "1970년대 석유 충격·1990년대 그린스펀 비유"
   ],
   "phrases": [
    {
     "text": "Acting sooner and incrementally now is likely to be less disruptive",
     "date": "2026-10-30"
    },
    {
     "text": "further firming will likely be necessary",
     "date": "2026-10-30"
    },
    {
     "text": "Commitment, not silence",
     "date": "2026-09-29"
    }
   ],
   "dissents_2026": [],
   "recent": [
    {
     "date": "2026-10-30",
     "text": "SOMC: 정책·금융여건 여전히 완화적, 18개월 안 2% 위해 추가 긴축"
    },
    {
     "date": "2026-09-29",
     "text": "LSE: 경로 약속 대신 시나리오·확률·18개월 시계 공개 제안"
    },
    {
     "date": "2026-08-06",
     "text": "상파울루: 'AI·생산성 낙관론자'지만 기대로 완화하면 안 됨"
    },
    {
     "date": "2026-05-28",
     "text": "레이캬비크: 장기 기대인플레 '상승 중', 지금 수요 압력에 맞서야"
    }
   ],
   "baseline": {
    "usual": [
     "'추가 긴축, 이르고 점진적'",
     "인플레 '높고 넓게', 기대는 '대체로 고정'",
     "AI 생산성 기대로 완화 말라",
     "장기금리는 연준 의지에 달림"
    ],
    "hawk_surprise": [
     "50bp·연속·'최소 n번'",
     "'behind the curve'·10월 동결 실수",
     "대차대조표 등 금리 밖 도구",
     "기대 'unanchoring'·최종금리 제시"
    ],
    "dove_surprise": [
     "12월 동결 수용·'인내'",
     "'덜 그럴듯한' 시나리오가 그럴듯해짐",
     "노동 하방을 주 위험으로",
     "금융여건으로 인상 보류"
    ]
   },
   "review": "draft",
   "watch": "블랙아웃 전 12월 인상 명시 여부, 두 시나리오 무게 변화",
   "conf": "연설은 1차 사본(세인트루이스 연은 미러), 학력·회사명·연도는 사전 지식",
   "sources": [
    {
     "outlet": "세인트루이스 연은 연설(1차 사본)",
     "date": "2026-10-30",
     "url": "https://www.stlouisfed.org/from-the-president/remarks/2026/remarks-on-us-economy-and-monetary-policy-somc"
    },
    {
     "outlet": "CNBC",
     "date": "2026-10-30",
     "url": "https://www.cnbc.com/2026/10/30/musalem-fed-monetary-policy-tightening.html"
    },
    {
     "outlet": "세인트루이스 연은 연설(1차 사본)",
     "date": "2026-09-29",
     "url": "https://www.stlouisfed.org/from-the-president/remarks/2026/how-and-why-communicating-monetary-policy-framework-london"
    },
    {
     "outlet": "세인트루이스 연은 Q&A(1차 사본, 약력)",
     "date": "2026-05-06",
     "url": "https://www.stlouisfed.org/from-the-president/remarks/2026/ms-bankers-association-qa"
    }
   ],
   "camp_src": [
    {
     "outlet": "CNBC",
     "date": "2026-10-30",
     "url": "https://www.cnbc.com/2026/10/30/musalem-fed-monetary-policy-tightening.html"
    }
   ]
  },
  {
   "key": "kashkari",
   "name_ko": "닐 카시카리",
   "name_en": "Neel Kashkari",
   "role_short": "미니애폴리스 연은 총재",
   "seat": "bank",
   "district": 9,
   "voter_2026": true,
   "voter_2027": false,
   "bg_type": "혼합",
   "bg_line": "엔지니어 → 골드만 → 재무부 TARP → 핌코 → 주지사 후보",
   "camp": "매파",
   "stance_now": 1,
   "stance_start_2026": -0.5,
   "stance_basis": "점진 매파, '연내 1회+27년 1회'(27년은 중앙값 위). 전쟁 전엔 완화 편향·1회 인하 지지",
   "shift_note": "연초 1회 인하 지지 → 4·7월 매파 반대 → '연내 1회+27년 1회'",
   "journey": [
    {
     "from": "1973",
     "to": "1973",
     "org": "Akron, Ohio (birthplace)",
     "org_ko": "출생지 오하이오주 애크런",
     "kind": "other",
     "place": "Akron, OH",
     "lat": 41.0814,
     "lon": -81.519,
     "note": "1973년 출생(사전 지식)",
     "cert": "사전 지식"
    },
    {
     "from": null,
     "to": null,
     "org": "University of Illinois Urbana-Champaign",
     "org_ko": "일리노이대 어배너-섐페인",
     "kind": "school",
     "place": "Urbana, IL",
     "lat": 40.102,
     "lon": -88.2272,
     "note": "기계공학 학사·석사",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "TRW (aerospace)",
     "org_ko": "TRW 항공우주",
     "kind": "company",
     "place": "Redondo Beach, CA",
     "lat": 33.8492,
     "lon": -118.3884,
     "note": "엔지니어, 1990년대 말(위치 추정)",
     "cert": "사전 지식",
     "loc_guess": true
    },
    {
     "from": null,
     "to": null,
     "org": "Wharton School, University of Pennsylvania",
     "org_ko": "펜실베이니아대 와튼스쿨",
     "kind": "school",
     "place": "Philadelphia, PA",
     "lat": 39.9496,
     "lon": -75.1915,
     "note": "MBA",
     "cert": "1차"
    },
    {
     "from": "2002",
     "to": "2006",
     "org": "Goldman Sachs (San Francisco)",
     "org_ko": "골드만삭스(샌프란시스코)",
     "kind": "company",
     "place": "San Francisco, CA",
     "lat": 37.7897,
     "lon": -122.4,
     "note": "기술 기업 투자은행(연도는 사전 지식)",
     "cert": "1차"
    },
    {
     "from": "2006",
     "to": "2009",
     "org": "U.S. Department of the Treasury",
     "org_ko": "재무부",
     "kind": "government",
     "place": "Washington, DC",
     "lat": 38.8987,
     "lon": -77.0342,
     "note": "폴슨 보좌관→차관보 대행(TARP)",
     "cert": "1차"
    },
    {
     "from": "2009",
     "to": "2013",
     "org": "PIMCO",
     "org_ko": "핌코",
     "kind": "company",
     "place": "Newport Beach, CA",
     "lat": 33.6189,
     "lon": -117.9298,
     "note": "글로벌 주식 부문 책임자(연도는 사전 지식)",
     "cert": "1차"
    },
    {
     "from": "2014",
     "to": "2014",
     "org": "California governor race",
     "org_ko": "캘리포니아 주지사 선거",
     "kind": "other",
     "place": "Sacramento, CA",
     "lat": 38.5816,
     "lon": -121.4944,
     "note": "공화당 후보, 패배",
     "cert": "1차",
     "loc_guess": true
    },
    {
     "from": "2016",
     "to": null,
     "org": "Federal Reserve Bank of Minneapolis",
     "org_ko": "미니애폴리스 연은",
     "kind": "fed",
     "place": "Minneapolis, MN",
     "lat": 44.9846,
     "lon": -93.269,
     "note": "총재(2016-01-01~)",
     "cert": "1차",
     "now": true
    }
   ],
   "style": [
    "그림 붙은 장문 에세이, 반대 뒤 같은 주에 해설",
    "조건부 두 갈래 시나리오, '미리 정한 경로' 거부",
    "시장 가격·연은 직원 연구로 논증하는 실무자형"
   ],
   "phrases": [
    {
     "text": "I would rather tighten policy incrementally",
     "date": "2026-07-31"
    },
    {
     "text": "Federal funds rate increases, potentially a series of them, could be warranted",
     "date": "2026-05-01"
    }
   ],
   "dissents_2026": [
    {
     "date": "2026-04-29",
     "side": "문구"
    },
    {
     "date": "2026-07-29",
     "side": "인상"
    }
   ],
   "recent": [
    {
     "date": "2026-10-28",
     "text": "동결 찬성(추론 — 반대자는 쿡·해맥뿐)"
    },
    {
     "date": "2026-10-01",
     "text": "'10월 인상엔 강한 견해 없음', 연내 1회+27년 1회(2차)"
    },
    {
     "date": "2026-09-16",
     "text": "+25bp 인상 찬성(12-0)"
    },
    {
     "date": "2026-07-29",
     "text": "+25bp 쪽 반대, 해설 '연속 충격엔 통화정책 몫'"
    }
   ],
   "baseline": {
    "usual": [
     "'아직 너무 높다'·5년 넘게 목표 위·기대 고정",
     "'look through 한계'·'작은 걸음'",
     "연내 1회(=12월)+27년 1회",
     "12월 동결이면 인상 쪽 반대(표 예상)"
    ],
    "hawk_surprise": [
     "50bp·매 회의 연속 인상",
     "27년 2회 이상(총 3회+)·'상당히 긴축적'까지",
     "장기 기대 이탈 '이미 시작'"
    ],
    "dove_surprise": [
     "12월 동결·'추가 인상 불필요'",
     "연속 충격론 접고 '이번 에너지 충격은 지나쳐 볼 수 있다'",
     "중립금리 하향·2027 인하"
    ]
   },
   "review": "approved",
   "watch": "10월 AI주 급락을 금융여건 긴축으로 읽어 인상 필요를 낮추나",
   "conf": "에세이·표결은 1차, 학력·경력은 2015 선임 발표(1차), 10/01 발언은 2차",
   "sources": [
    {
     "outlet": "미니애폴리스 연은 에세이(1차 사본)",
     "date": "2026-05-01",
     "url": "https://www.minneapolisfed.org/article/2026/why-i-dissented"
    },
    {
     "outlet": "미니애폴리스 연은 성명(1차 사본)",
     "date": "2026-07-31",
     "url": "https://www.minneapolisfed.org/article/2026/statement-on-my-fomc-dissent"
    },
    {
     "outlet": "연준 FOMC 성명(1차 사본)",
     "date": "2026-07-29",
     "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260729a.htm"
    },
    {
     "outlet": "Continuum Economics",
     "date": "2026-07",
     "url": "https://continuumeconomics.com/a/df2af25a/us-feds-kashkari-hammack-and-logan-explain-their-hawkish-dissents"
    },
    {
     "outlet": "미니애폴리스 연은 보도자료(총재 선임, 1차)",
     "date": "2015-11-10",
     "url": "https://www.minneapolisfed.org/news-releases/2015/federal-reserve-bank-of-minneapolis-announcement-november-10-2015"
    },
    {
     "outlet": "Reuters via Kitco",
     "date": "2026-10-01",
     "url": "https://www.kitco.com/news/off-the-wire/2026-10-01/feds-kashkari-expects-more-rate-hikes-unsure-need-act-month"
    }
   ],
   "camp_src": [
    {
     "outlet": "Continuum",
     "date": "2026-07",
     "url": "https://continuumeconomics.com/a/df2af25a/us-feds-kashkari-hammack-and-logan-explain-their-hawkish-dissents"
    }
   ]
  },
  {
   "key": "schmid",
   "name_ko": "제프리 슈미드",
   "name_en": "Jeffrey R. Schmid",
   "role_short": "캔자스시티 연은 총재",
   "seat": "bank",
   "district": 10,
   "voter_2026": false,
   "voter_2027": false,
   "bg_type": "실무(은행·감독)",
   "bg_line": "OCC 검사역 → 오마하 은행 CEO → 은행 대학원장",
   "camp": "매파",
   "stance_now": 1.5,
   "stance_start_2026": 0.5,
   "stance_basis": "'정책은 긴축적이지 않아 더 조여야'(8월), 9월 인상 지지. 3월부터 물가 쪽",
   "shift_note": "25년 인하에 두 번 반대 → 8월 '더 조여야' → 9월 인상 지지",
   "journey": [
    {
     "from": null,
     "to": null,
     "org": "Nebraska (home state)",
     "org_ko": "고향 네브래스카",
     "kind": "other",
     "place": "Nebraska, United States",
     "lat": 41.4925,
     "lon": -99.9018,
     "note": "'my home state'(본인)",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "University of Nebraska–Lincoln",
     "org_ko": "네브래스카대 링컨",
     "kind": "school",
     "place": "Lincoln, NE",
     "lat": 40.8202,
     "lon": -96.7005,
     "note": "학사(사전 지식)",
     "cert": "사전 지식"
    },
    {
     "from": null,
     "to": null,
     "org": "Graduate School of Banking, UW–Madison",
     "org_ko": "위스콘신대 은행 대학원",
     "kind": "school",
     "place": "Madison, WI",
     "lat": 43.0766,
     "lon": -89.4125,
     "note": "수료(사전 지식)",
     "cert": "사전 지식"
    },
    {
     "from": null,
     "to": null,
     "org": "Office of the Comptroller of the Currency",
     "org_ko": "통화감독청(OCC)",
     "kind": "government",
     "place": "Washington, DC",
     "lat": 38.8846,
     "lon": -77.0167,
     "note": "국법은행 검사역(근무지 미상)",
     "cert": "사전 지식",
     "loc_guess": true
    },
    {
     "from": null,
     "to": null,
     "org": "American National Bank (Omaha)",
     "org_ko": "아메리칸 내셔널 뱅크",
     "kind": "company",
     "place": "Omaha, NE",
     "lat": 41.2565,
     "lon": -95.9345,
     "note": "경영진·CEO(사전 지식)",
     "cert": "사전 지식"
    },
    {
     "from": "2007",
     "to": "2020",
     "org": "Mutual of Omaha Bank",
     "org_ko": "뮤추얼 오브 오마하 은행",
     "kind": "company",
     "place": "Omaha, NE",
     "lat": 41.26,
     "lon": -95.96,
     "note": "회장 겸 CEO, 매각까지(사전 지식)",
     "cert": "사전 지식"
    },
    {
     "from": "2021",
     "to": "2023",
     "org": "Southwest Graduate School of Banking (SMU Cox)",
     "org_ko": "SMU 콕스 은행 대학원",
     "kind": "academia",
     "place": "Dallas, TX",
     "lat": 32.8412,
     "lon": -96.7845,
     "note": "회장 겸 CEO(사전 지식)",
     "cert": "사전 지식"
    },
    {
     "from": "2023",
     "to": null,
     "org": "Federal Reserve Bank of Kansas City",
     "org_ko": "캔자스시티 연은",
     "kind": "fed",
     "place": "Kansas City, MO",
     "lat": 39.0758,
     "lon": -94.5867,
     "note": "총재(2023-08~·사전 지식), 잭슨홀 주최",
     "cert": "1차",
     "now": true
    }
   ],
   "style": [
    "분권 구조·'지역의 목소리'로 시작, 지역 이야기→전망",
    "'물가가 최우선 걱정'으로 끝맺음, 문장 재활용 많음",
    "금리 경로 숫자·점도표·중립금리 수치는 말하지 않음"
   ],
   "phrases": [
    {
     "text": "My primary concern is inflation, which is too hot",
     "date": "2026-07-16"
    },
    {
     "text": "I do not see the current stance of monetary policy as restrictive",
     "date": "2026-08-04"
    },
    {
     "text": "our inflation problem is not just about energy",
     "date": "2026-09-18"
    }
   ],
   "dissents_2026": [],
   "recent": [
    {
     "date": "2026-09-18",
     "text": "베일: 9월 인상 지지, '물가 문제는 에너지만이 아니다'"
    },
    {
     "date": "2026-08-27",
     "text": "Bloomberg 인터뷰: 통화정책 소통(내용 미확인)"
    },
    {
     "date": "2026-08-04",
     "text": "오마하: '정책은 긴축적이지 않다, 더 조여야'"
    },
    {
     "date": "2026-07-16",
     "text": "그랜드아일랜드: 공급 충격 넘겨보기 반대, 식품 근원 포함 주장"
    }
   ],
   "baseline": {
    "usual": [
     "'My primary concern is inflation…'",
     "'에너지만의 문제가 아니다'",
     "노동 균형·성장 견조"
    ],
    "hawk_surprise": [
     "인상 폭·횟수를 숫자로",
     "대차대조표를 긴축 수단으로",
     "10월 동결·의장 공개 비판"
    ],
    "dove_surprise": [
     "'이제 충분히 긴축적'",
     "'인내·지켜볼 수 있다'",
     "노동 약화를 걱정거리로",
     "'에너지는 지나쳐 볼 수 있다'"
    ]
   },
   "review": "draft",
   "watch": "10/28 뒤 첫 발언에서 'not restrictive' 판단 유지 여부",
   "conf": "2026 연설·2025 반대표는 1차 사본, 학력·은행 경력은 사전 지식",
   "sources": [
    {
     "outlet": "캔자스시티 연은 연설(1차 사본)",
     "date": "2026-09-18",
     "url": "https://www.kansascityfed.org/speeches/the-strategic-imperative-of-instant-payments-for-community-banks/"
    },
    {
     "outlet": "캔자스시티 연은 연설(1차 사본)",
     "date": "2026-08-04",
     "url": "https://www.kansascityfed.org/speeches/agriculture-the-economy-and-the-kansas-city-fed-august-2026/"
    },
    {
     "outlet": "연준 FOMC 성명(1차 사본, 2025-12 반대)",
     "date": "2025-12-10",
     "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20251210a.htm"
    },
    {
     "outlet": "Bloomberg Government",
     "date": "2026-09-18",
     "url": "https://news.bgov.com/banking-law/feds-schmid-backed-rate-hike-says-inflation-goes-beyond-energy"
    },
    {
     "outlet": "Scotsman Guide",
     "date": "2025-12-10",
     "url": "https://www.scotsmanguide.com/news/fed-cuts-rates-though-three-officials-dissent/"
    },
    {
     "outlet": "캔자스시티 연은 연설",
     "date": "2026-07-16",
     "url": "https://www.kansascityfed.org/speeches/the-federal-reserve-economic-outlook-and-monetary-policy-july-2026/"
    }
   ],
   "camp_src": [
    {
     "outlet": "Scotsman Guide",
     "date": "2025-12-10",
     "url": "https://www.scotsmanguide.com/news/fed-cuts-rates-though-three-officials-dissent/"
    }
   ]
  },
  {
   "key": "logan",
   "name_ko": "로리 로건",
   "name_en": "Lorie K. Logan",
   "role_short": "댈러스 연은 총재",
   "seat": "bank",
   "district": 11,
   "voter_2026": true,
   "voter_2027": false,
   "bg_type": "실무(시장)",
   "bg_line": "뉴욕 연은 23년(시장그룹 22년)·SOMA 운용책임자 → 댈러스 총재",
   "camp": "매파",
   "stance_now": 1.5,
   "stance_start_2026": 0,
   "stance_basis": "'최소 두 번 더 25bp 뒤 멈춤', 목적지는 강경·시점은 유연. 2월엔 중립 근처",
   "shift_note": "2월 '중립 근처' → 4·7월 반대 → '최소 두 번 더'",
   "journey": [
    {
     "from": null,
     "to": null,
     "org": "Versailles, Kentucky (hometown)",
     "org_ko": "성장지 켄터키주 베르사유",
     "kind": "other",
     "place": "Versailles, KY",
     "lat": 38.0526,
     "lon": -84.7297,
     "note": "켄터키에서 자람(본인)",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "Davidson College",
     "org_ko": "데이비슨 칼리지",
     "kind": "school",
     "place": "Davidson, NC",
     "lat": 35.5007,
     "lon": -80.8456,
     "note": "정치학 학사, 1부 배구 선수",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "Teaching English in Japan",
     "org_ko": "일본(영어 교사)",
     "kind": "other",
     "place": "(도시 미상), Japan",
     "lat": 36.2048,
     "lon": 138.2529,
     "note": "졸업 뒤 영어 교사, 도시 미기재",
     "cert": "1차",
     "loc_guess": true
    },
    {
     "from": null,
     "to": null,
     "org": "Columbia University SIPA",
     "org_ko": "컬럼비아대 국제공공정책대학원",
     "kind": "school",
     "place": "New York, NY",
     "lat": 40.8075,
     "lon": -73.9626,
     "note": "MPA",
     "cert": "1차"
    },
    {
     "from": "1999",
     "to": "2022",
     "org": "Federal Reserve Bank of New York",
     "org_ko": "뉴욕 연은",
     "kind": "fed",
     "place": "New York, NY",
     "lat": 40.7083,
     "lon": -74.0087,
     "note": "은행감독(1999-06)→시장그룹(2000)→SOMA 운용책임자(2019)",
     "cert": "1차"
    },
    {
     "from": "2022",
     "to": null,
     "org": "Federal Reserve Bank of Dallas",
     "org_ko": "댈러스 연은",
     "kind": "fed",
     "place": "Dallas, TX",
     "lat": 32.7884,
     "lon": -96.7967,
     "note": "총재(2022-08-22~)",
     "cert": "1차",
     "now": true
    }
   ],
   "style": [
    "연설로 '목적지'를 미리 알리되 매 회의 표는 안 알림",
    "숫자를 직접 말함('최소 두 번 25bp'), 물가 지표 여럿 병행",
    "시장 가격·기간 프리미엄을 판단에 넣는 운용 실무자"
   ],
   "phrases": [
    {
     "text": "skipping a meeting does not change the monetary policy destination",
     "date": "2026-10-30"
    },
    {
     "text": "modestly higher interest rates would better balance the outlook and risks",
     "date": "2026-07-16"
    },
    {
     "text": "skate where the puck is going",
     "date": "2026-07-16"
    }
   ],
   "dissents_2026": [
    {
     "date": "2026-04-29",
     "side": "문구"
    },
    {
     "date": "2026-07-29",
     "side": "인상"
    }
   ],
   "recent": [
    {
     "date": "2026-10-30",
     "text": "데이비슨: 동결에 투표, '최소 두 번 더 25bp 뒤 멈춤'"
    },
    {
     "date": "2026-10-01",
     "text": "'정책 기조는 오프사이드', 추가 50bp 이상 필요"
    },
    {
     "date": "2026-07-29",
     "text": "동결에 반대, +25bp(해맥·카시카리와 함께)"
    },
    {
     "date": "2026-07-16",
     "text": "휴스턴: '약간 더 높은 금리가 균형에 맞다'"
    }
   ],
   "baseline": {
    "usual": [
     "'최소 두 번 25bp 뒤 멈춤'",
     "근원 PCE 3%대·넓은 압력",
     "금융여건 순풍 = 긴축 부족",
     "절사평균은 낮게 치우침",
     "물가 추세 '2% 중반'(2%까지 안 감)"
    ],
    "hawk_surprise": [
     "한 번에 50bp·'곧' 시급성",
     "'상당히 긴축적'·세 번 이상",
     "12월 반대하며 50bp 요구"
    ],
    "dove_surprise": [
     "'한 번이면 충분'·이미 긴축적",
     "기간 프리미엄이 '일을 대신했다'",
     "고용 악화를 멈춤 이유로",
     "물가 추세 2%로"
    ]
   },
   "review": "approved",
   "watch": "12월 동결 시 반대 여부, 목적지(최소 50bp) 유지 여부",
   "conf": "연설·표결은 1차, 학력·취임일은 뉴욕·댈러스 연은 약력(1차)",
   "sources": [
    {
     "outlet": "댈러스 연은 연설(1차 사본)",
     "date": "2026-10-30",
     "url": "https://www.dallasfed.org/news/speeches/logan/2026/lkl261030"
    },
    {
     "outlet": "댈러스 연은 연설(1차 사본)",
     "date": "2026-10-01",
     "url": "https://www.dallasfed.org/news/speeches/logan/2026/lkl261001"
    },
    {
     "outlet": "댈러스 연은 연설(1차 사본)",
     "date": "2026-07-16",
     "url": "https://www.dallasfed.org/news/speeches/logan/2026/lkl260716"
    },
    {
     "outlet": "댈러스 연은 듀크 졸업 연설(1차 사본, 약력)",
     "date": "2026-05-10",
     "url": "https://www.dallasfed.org/news/speeches/logan/2026/lkl260510"
    },
    {
     "outlet": "Continuum",
     "date": "2026-07",
     "url": "https://continuumeconomics.com/a/df2af25a/us-feds-kashkari-hammack-and-logan-explain-their-hawkish-dissents"
    },
    {
     "outlet": "뉴욕 연은 약력(1차)",
     "date": "2022",
     "url": "https://www.newyorkfed.org/aboutthefed/orgchart/logan"
    }
   ],
   "camp_src": [
    {
     "outlet": "Continuum",
     "date": "2026-07",
     "url": "https://continuumeconomics.com/a/df2af25a/us-feds-kashkari-hammack-and-logan-explain-their-hawkish-dissents"
    }
   ]
  },
  {
   "key": "daly",
   "name_ko": "메리 데일리",
   "name_en": "Mary C. Daly",
   "role_short": "샌프란시스코 연은 총재",
   "seat": "bank",
   "district": 12,
   "voter_2026": false,
   "voter_2027": true,
   "bg_type": "학계",
   "bg_line": "고교 중퇴·GED → 경제학 박사 → SF 연은 30년(연구→총재)",
   "camp": "미상",
   "stance_now": null,
   "stance_start_2026": null,
   "stance_basis": "2026년 금리 발언 미확인 — 판단 보류(2025엔 인하 지지)",
   "shift_note": "2025 인하 지지 → 2026 금리 발언 없음(판단 보류)",
   "journey": [
    {
     "from": null,
     "to": null,
     "org": "Ballwin, Missouri (hometown)",
     "org_ko": "성장지 미주리주 볼윈",
     "kind": "other",
     "place": "Ballwin, MO",
     "lat": 38.595,
     "lon": -90.5462,
     "note": "고교 중퇴·도넛 야간 근무·GED",
     "cert": "1차"
    },
    {
     "from": null,
     "to": null,
     "org": "University of Missouri–Kansas City",
     "org_ko": "미주리대 캔자스시티(UMKC)",
     "kind": "school",
     "place": "Kansas City, MO",
     "lat": 39.0335,
     "lon": -94.5763,
     "note": "경제학·철학 학사(학교명 사전 지식)",
     "cert": "사전 지식"
    },
    {
     "from": null,
     "to": null,
     "org": "University of Illinois Urbana-Champaign",
     "org_ko": "일리노이대 어배너-섐페인",
     "kind": "school",
     "place": "Urbana, IL",
     "lat": 40.102,
     "lon": -88.2272,
     "note": "석사(사전 지식)",
     "cert": "사전 지식"
    },
    {
     "from": "1994",
     "to": "1994",
     "org": "Syracuse University",
     "org_ko": "시러큐스대",
     "kind": "school",
     "place": "Syracuse, NY",
     "lat": 43.0392,
     "lon": -76.1351,
     "note": "박사(학교·연도는 사전 지식)",
     "cert": "사전 지식"
    },
    {
     "from": null,
     "to": null,
     "org": "Northwestern University",
     "org_ko": "노스웨스턴대",
     "kind": "academia",
     "place": "Evanston, IL",
     "lat": 42.0565,
     "lon": -87.6753,
     "note": "박사후 과정(사전 지식)",
     "cert": "사전 지식"
    },
    {
     "from": "1996",
     "to": "2018",
     "org": "Federal Reserve Bank of San Francisco",
     "org_ko": "샌프란시스코 연은",
     "kind": "fed",
     "place": "San Francisco, CA",
     "lat": 37.793,
     "lon": -122.399,
     "note": "이코노미스트→연구국장(2017 무렵)",
     "cert": "1차"
    },
    {
     "from": "2018",
     "to": null,
     "org": "Federal Reserve Bank of San Francisco",
     "org_ko": "샌프란시스코 연은",
     "kind": "fed",
     "place": "San Francisco, CA",
     "lat": 37.793,
     "lon": -122.399,
     "note": "총재(2018-10 무렵~)",
     "cert": "1차",
     "now": true
    }
   ],
   "style": [
    "개인 일화로 시작, 짧고 쉬운 문장, 원칙을 셋씩 묶음",
    "날짜·폭 약속 않음 — '말은 금리보다 되돌리기 어렵다'",
    "기업 대화·세분 자료 강조, 2026 하반기 원고 연설 드묾"
   ],
   "phrases": [
    {
     "text": "Anchor. Assess. Decide.",
     "date": "2025-09-24"
    },
    {
     "text": "In my 30 years at the Fed",
     "date": "2026-04-08"
    }
   ],
   "dissents_2026": [],
   "recent": [
    {
     "date": "2026-10-30",
     "text": "AI의 물가·고용 영향 언급, 인상·멈춤 선호 안 밝힘(2차·낮음)"
    },
    {
     "date": "2026-04-08",
     "text": "세인트조지: 연준 지역주의·독립성 옹호, 금리 언급 없음"
    },
    {
     "date": "2026-03-01",
     "text": "새 5년 임기 시작(2차)"
    },
    {
     "date": "2026-02-17",
     "text": "산호세 'AI의 순간?': 거시 생산성 효과 증거 아직 적음"
    }
   ],
   "baseline": {
    "usual": [
     "'목표에 기대고, 상충을 따지고, 결정'",
     "AI·신기술, 1990년대 인내 비유",
     "연준 구조·독립성·소통 원칙"
    ],
    "hawk_surprise": [
     "12월 추가 인상 명시",
     "AI 붐이 물가를 올린다",
     "'긴축적이지 않다'·기대 위험",
     "2027 인상 쪽 반대"
    ],
    "dove_surprise": [
     "9월 인상이 과했다",
     "'노동은 넘어지면 빠르고 세게' 복귀",
     "AI 생산성을 덜 올릴 이유로",
     "인하 언급"
    ]
   },
   "review": "draft",
   "watch": "11월 발언에서 2026년 첫 명시적 금리 입장, 2027 첫 투표",
   "conf": "원고는 1차 사본, 2026 금리 발언 미확인, 학교명은 사전 지식",
   "sources": [
    {
     "outlet": "SF 연은 연설(1차 사본)",
     "date": "2026-02-17",
     "url": "https://www.frbsf.org/news-and-media/speeches/mary-c-daly/2026/02/the-ai-moment-possibilities-productivity-and-policy/"
    },
    {
     "outlet": "SF 연은 연설(1차 사본)",
     "date": "2026-04-08",
     "url": "https://www.frbsf.org/news-and-media/speeches/mary-c-daly/2026/04/many-voices-one-purpose/"
    },
    {
     "outlet": "SF 연은 졸업 연설(1차 사본, 약력)",
     "date": "2025-05-16",
     "url": "https://www.frbsf.org/news-and-media/speeches/mary-c-daly/2025/05/choose-and-choose-again/"
    },
    {
     "outlet": "Quartz",
     "date": "2026-10-30",
     "url": "https://qz.com/fed-officials-signal-more-interest-rate-hikes-103026"
    },
    {
     "outlet": "SF 연은 연설",
     "date": "2025-09-24",
     "url": "https://www.frbsf.org/news-and-media/speeches/mary-c-daly/2025/09/steady-through-change-policy-business-life/"
    }
   ]
  }
 ],
 "map": {
  "w": 960,
  "h": 600,
  "proj": {
   "p1": 29.5,
   "p2": 45.5,
   "lat0": 37.5,
   "lon0": -96.0,
   "s": 1264.0272698930878,
   "ox": 489.9164537181963,
   "oy": 321.30498675463247
  },
  "paths": {
   "AL": "M644.5,369.9L675.8,367.1L681.1,385.8L688.7,413.2L691.5,419.1L693.9,422.4L693.4,424.7L695.6,425.7L692.8,428.9L693.3,431.7L692.1,435.6L694.7,442.0L694.0,447.9L696.7,453.7L687.5,454.9L648.1,458.8L647.7,461.8L652.3,465.6L651.9,469.3L653.5,471.0L651.0,474.5L648.5,475.4L643.4,472.2L642.4,466.9L640.9,466.4L639.5,470.6L639.2,474.7L634.3,474.0L630.1,440.4L631.0,398.0L631.5,373.5L629.5,371.3L644.5,369.9Z",
   "AK": "M207.1,549.4L206.9,548.8L207.5,549.0L207.6,549.6L207.1,549.7ZM206.3,548.5L206.8,548.8L206.8,549.5L206.3,548.5ZM202.9,545.8L203.4,545.6L203.7,546.2L203.3,546.4L202.9,546.2ZM201.8,546.5L202.7,546.3L203.1,546.9L204.2,547.4L204.6,547.7L205.0,548.1L205.2,548.6L205.7,549.0L205.9,549.4L206.8,550.8L206.2,551.2L205.8,550.6L205.0,550.4L204.8,551.0L205.4,550.9L205.5,551.6L204.2,551.0L203.9,550.6L203.4,550.3L203.6,549.8L203.8,549.4L203.5,548.8L202.7,548.0L202.4,547.6L202.2,547.2L201.8,546.7ZM202.4,549.3L203.0,549.0L203.2,549.7L202.4,549.3ZM200.6,544.7L200.3,544.4L201.6,544.1L202.0,543.9L202.6,544.5L203.3,544.8L203.2,545.5L202.5,545.9L201.6,546.2L201.3,545.4L201.1,544.9L200.6,544.7ZM200.7,546.3L199.9,545.7L199.9,545.0L201.1,545.1L201.4,545.7L201.2,546.6L201.4,547.6L201.2,548.0L200.5,546.9L200.7,546.3ZM199.9,547.3L198.5,546.3L197.9,545.9L197.6,544.7L196.9,544.1L197.2,543.3L198.0,543.6L198.6,544.1L199.5,545.8L199.9,547.3ZM197.8,540.7L198.5,540.7L199.7,541.7L199.3,542.0L199.8,542.3L200.2,543.2L199.9,543.5L199.4,544.7L198.9,544.1L198.7,543.1L198.3,542.4L197.8,541.1L197.4,540.8L197.2,540.1L197.8,540.7ZM196.6,544.4L197.3,544.8L196.9,545.5L196.8,544.8L196.6,544.4ZM195.0,541.5L195.5,541.4L195.8,541.0L196.4,541.3L196.3,541.8L196.5,541.4L197.2,541.3L197.7,541.6L197.7,542.4L198.3,543.2L197.9,543.5L196.8,543.0L197.0,543.8L196.4,544.1L196.1,543.7L195.6,543.5L195.2,542.9L194.7,542.7L194.6,542.1L194.7,541.4ZM174.2,538.1L173.5,539.1L172.9,539.8L173.0,539.2L173.6,538.6L173.9,537.9ZM173.2,536.9L173.2,537.6L173.0,538.4L172.8,537.3L173.2,536.9ZM169.6,502.4L170.4,502.6L171.2,502.4L172.0,502.4L172.9,502.9L173.6,502.9L174.2,502.5L174.9,502.1L175.9,502.3L176.4,502.6L176.9,502.9L177.7,503.2L178.3,503.2L184.8,536.2L185.7,536.3L186.7,536.2L187.0,535.5L188.1,535.2L188.1,536.2L188.4,536.5L189.1,536.7L189.4,537.1L191.6,538.5L192.2,539.6L192.4,539.2L193.1,538.5L193.6,537.9L193.4,537.2L193.6,536.6L194.2,536.3L194.8,535.6L195.9,536.2L196.3,537.1L197.5,537.7L197.9,538.2L198.8,538.4L200.6,540.0L201.0,540.5L201.5,540.9L202.5,541.9L203.4,542.7L203.9,543.1L204.0,543.8L204.6,543.9L204.9,544.5L205.3,544.3L206.5,544.7L207.1,544.6L207.5,544.8L208.1,545.1L208.7,545.0L209.1,545.3L209.1,546.2L209.3,546.8L210.0,547.7L209.8,549.2L209.3,550.1L209.0,549.8L208.4,549.4L208.0,548.8L208.3,548.3L207.8,548.8L207.3,548.9L206.2,548.4L206.2,547.5L205.8,548.0L205.4,548.2L205.3,547.3L205.1,546.9L204.8,547.4L204.2,546.8L203.7,546.4L203.9,545.9L204.0,545.3L203.9,544.6L202.9,544.3L202.2,543.8L201.1,543.6L200.7,542.2L200.2,541.6L199.1,540.9L198.9,540.5L198.0,540.7L196.9,539.9L195.8,537.6L195.8,538.2L196.0,538.7L196.6,539.5L197.0,540.4L197.1,540.9L196.3,540.4L195.4,540.7L195.2,539.9L194.7,539.3L193.2,539.2L193.8,539.5L194.4,539.9L194.8,540.3L195.2,540.8L194.7,541.3L194.4,541.7L193.8,541.4L193.3,541.3L192.3,540.8L191.5,540.3L190.9,539.5L189.9,539.4L189.3,539.1L188.3,538.8L187.6,538.5L187.9,537.8L187.5,537.1L186.4,538.1L185.3,538.1L184.3,537.8L183.8,537.7L183.3,537.5L182.3,537.4L181.7,537.5L180.4,537.9L179.9,538.1L179.2,537.7L178.5,537.6L178.0,536.8L177.5,536.9L177.4,537.4L176.4,536.9L175.4,537.2L175.0,537.9L174.7,537.4L175.2,537.1L176.0,536.6L175.5,536.5L175.3,536.1L174.4,535.1L173.7,535.5L172.7,535.7L172.3,536.2L172.2,535.4L171.7,536.2L172.2,536.4L172.6,537.4L172.5,538.0L172.6,539.0L172.2,539.2L171.5,539.3L170.7,539.2L170.3,539.5L169.8,539.7L169.6,540.2L169.1,540.7L168.7,541.0L168.1,541.3L167.4,542.2L166.8,542.3L166.3,542.5L165.6,542.1L165.7,541.5L166.2,541.3L167.1,540.6L166.4,540.7L165.8,540.5L166.0,539.3L166.5,538.6L166.7,538.0L166.7,537.4L166.4,536.8L167.0,536.5L168.1,535.6L168.4,535.9L169.3,535.6L168.7,535.1L168.4,534.8L167.6,534.7L167.0,535.1L166.8,535.6L166.3,535.8L165.7,536.4L165.2,536.9L164.9,537.6L164.7,538.4L164.1,538.9L164.4,539.2L164.2,539.8L163.6,539.9L163.6,540.6L163.1,540.9L162.6,541.1L162.4,541.5L161.7,541.8L161.5,542.9L162.3,542.9L163.0,543.2L162.9,544.2L162.5,544.5L162.0,544.8L161.9,545.4L161.6,546.0L161.0,546.5L160.3,546.7L159.7,546.9L159.3,547.3L158.5,548.3L157.9,548.2L157.6,548.6L157.3,549.4L156.9,550.3L156.2,550.4L155.7,550.8L154.6,551.5L154.1,551.3L154.0,551.8L153.3,551.9L152.9,552.4L153.5,552.6L152.8,553.7L151.1,553.9L150.5,554.9L150.5,554.1L149.7,554.1L148.9,554.7L148.6,555.2L147.9,554.9L147.1,555.4L146.6,555.4L146.5,554.4L146.2,554.8L145.3,556.3L144.5,556.2L144.5,555.5L144.1,556.4L143.6,556.6L143.4,556.0L143.3,556.5L142.5,556.9L143.0,557.1L142.0,557.5L140.9,557.3L140.4,557.5L139.7,557.9L139.2,557.1L139.7,556.9L140.1,556.2L141.6,555.9L142.3,556.0L142.5,556.5L142.8,556.2L143.2,555.6L144.4,554.8L145.2,554.0L146.2,553.4L147.2,553.2L147.7,553.4L148.1,553.2L147.9,553.9L148.8,553.8L149.2,554.2L148.7,553.5L149.2,552.4L149.7,551.9L150.4,551.5L151.4,551.1L152.2,550.5L152.8,550.7L152.8,549.9L153.4,549.1L154.2,548.6L154.8,547.9L155.4,544.8L156.2,544.0L156.1,543.4L154.3,544.2L153.8,544.1L153.4,543.5L153.0,543.3L152.8,543.9L153.1,544.7L152.7,545.0L151.9,543.6L151.5,542.9L151.1,543.3L150.7,543.0L150.3,542.3L149.2,542.9L148.3,543.3L147.4,543.9L147.1,543.5L147.5,543.1L147.5,542.0L147.4,540.9L147.9,540.5L147.6,539.6L147.4,539.0L147.2,538.3L146.9,537.9L146.7,538.5L145.4,538.9L144.5,539.0L143.7,538.6L143.7,538.0L143.0,536.9L142.5,536.7L142.1,535.7L142.6,535.4L142.8,534.7L142.5,534.4L142.4,533.6L141.9,533.7L142.0,533.1L141.5,532.6L141.6,532.1L141.3,531.7L141.5,531.1L142.1,531.1L142.2,530.5L142.4,530.1L143.7,528.8L144.0,528.4L144.1,527.9L144.7,526.9L145.1,526.6L145.7,526.5L146.2,526.8L146.8,527.5L147.9,526.9L148.7,526.1L149.8,526.4L150.5,526.2L151.2,525.3L151.0,524.2L150.6,523.0L150.5,522.5L150.9,522.7L151.4,522.3L151.0,521.2L150.5,521.7L149.8,521.8L149.2,522.0L148.7,522.3L148.5,522.8L148.2,522.4L147.7,522.6L147.1,522.0L146.0,521.8L145.2,522.1L144.3,521.8L143.2,521.3L142.8,520.6L143.0,520.2L142.7,519.7L143.2,519.1L143.2,518.5L142.5,518.2L141.8,517.9L141.5,517.6L141.1,517.2L142.0,516.5L143.2,515.9L144.0,515.5L144.4,515.9L145.0,515.7L144.7,515.2L145.8,514.8L147.0,514.6L147.6,514.7L147.7,515.4L147.5,516.1L147.6,516.6L148.5,516.7L149.1,516.7L149.6,517.0L150.4,517.1L150.9,516.4L151.4,516.6L151.0,515.8L150.5,516.0L150.6,515.4L150.2,514.7L149.8,514.4L149.7,513.9L150.5,514.4L150.5,515.2L151.0,515.7L150.7,514.6L151.0,513.6L150.3,513.6L149.7,513.5L148.2,512.8L148.1,511.3L147.9,510.9L147.5,510.5L146.7,509.6L146.4,509.2L145.5,508.3L145.0,507.9L145.4,507.7L145.7,507.2L146.0,506.1L147.1,506.4L148.5,506.4L149.6,505.8L150.2,505.0L150.4,504.2L150.8,503.5L151.3,503.0L151.6,502.6L152.2,501.9L152.7,502.2L153.5,502.0L153.9,501.6L155.1,500.5L155.9,500.6L157.0,500.5L157.8,500.0L158.6,499.0L160.0,499.5L159.7,500.2L159.5,500.7L160.1,500.6L160.4,500.0L160.6,499.5L161.2,500.1L161.5,500.7L162.0,500.5L162.8,500.3L163.6,500.5L163.8,501.4L164.5,501.6L165.3,502.2L165.8,501.8L166.4,501.9L166.9,501.7L167.8,501.7L168.3,501.9L168.8,502.2L169.6,502.4ZM163.9,546.6L163.2,546.5L163.7,545.6L164.4,544.7L164.7,545.4L165.5,545.5L164.8,546.2L163.9,546.6ZM162.0,548.4L162.5,547.9L162.0,547.4L162.4,547.1L162.7,547.7L162.9,546.8L163.3,547.1L164.0,546.9L164.8,547.1L164.8,548.1L165.4,548.0L165.0,548.7L164.3,548.5L164.6,548.9L164.0,549.1L164.0,549.8L163.4,550.1L162.5,550.8L161.9,551.2L161.7,550.4L161.3,550.9L160.9,550.4L160.8,549.6L160.4,549.3L160.7,548.5L161.4,548.0L162.0,548.4ZM160.8,551.8L160.4,552.5L160.8,551.8ZM158.6,554.2L158.8,555.0L158.2,554.9L158.6,554.2ZM149.8,556.0L149.6,556.7L148.9,557.3L149.3,556.4L149.8,556.0ZM148.6,555.6L148.9,556.0L148.5,556.4L148.2,556.1L147.9,555.7L148.6,555.6ZM144.9,556.5L144.6,557.0L144.9,556.5ZM148.5,525.5L148.2,525.9L148.5,525.5ZM143.5,558.2L143.9,558.3L143.5,558.6ZM137.7,558.0L137.5,558.5L137.7,558.0ZM137.2,558.4L136.5,558.7L136.8,558.1L137.2,558.4ZM140.1,536.2L140.6,536.4L141.2,536.7L141.1,537.7L140.4,538.1L139.6,537.9L138.7,537.3L138.2,536.8L138.4,536.3L139.0,536.5L139.4,536.2L139.9,536.0ZM135.8,558.7L136.1,559.0L135.3,559.5L136.3,559.3L135.8,559.8L135.2,560.0L134.4,560.5L133.8,560.4L133.4,560.7L132.7,560.8L132.4,560.4L133.2,560.2L134.0,560.1L134.3,559.4L134.7,559.7L134.3,559.3L134.4,558.6L135.3,558.5L135.8,558.7ZM130.1,560.6L131.1,560.1L131.6,559.6L132.3,559.8L131.3,560.5L130.7,561.2L130.2,561.3L130.1,560.6ZM127.9,561.0L127.4,561.3L127.9,561.0ZM130.8,545.7L130.5,546.0L130.8,545.7ZM125.8,561.2L125.4,561.7L125.8,561.2ZM134.0,522.3L135.1,523.2L135.9,522.9L136.4,523.4L137.0,524.2L137.9,524.7L138.4,525.0L138.0,525.5L137.2,525.3L136.6,525.9L136.4,525.3L136.1,524.9L135.7,524.4L135.1,523.8L134.0,523.9L133.7,523.6L134.0,522.3ZM121.8,561.3L121.3,561.7L121.8,561.3ZM119.0,561.4L120.0,561.8L119.0,561.8ZM117.7,560.5L118.1,560.1L118.4,560.6L117.9,560.7L117.5,561.0L116.5,561.1L116.0,560.9L116.8,560.8L117.7,560.5ZM112.6,560.4L112.9,560.9L112.4,560.7L111.7,561.0L111.7,560.2L112.1,559.8L112.3,560.3ZM111.3,559.6L111.1,560.3L111.3,559.6ZM109.3,558.9L109.8,559.6L109.3,559.9L109.3,558.9ZM20.9,451.0L20.4,451.5L20.0,450.7L20.5,450.1L20.9,451.0Z",
   "AZ": "M263.0,316.8L245.7,441.6L208.1,436.0L187.8,424.3L144.0,398.3L146.7,393.8L150.4,393.7L151.8,391.9L151.6,387.7L149.1,387.1L149.6,378.7L153.8,376.4L155.0,373.2L155.3,368.0L158.2,364.6L161.3,363.7L164.0,361.2L161.1,357.4L159.8,351.2L157.6,347.1L158.2,344.3L159.8,341.5L160.2,337.4L159.6,332.9L161.1,319.9L167.6,320.3L169.2,323.4L171.0,323.6L173.5,320.2L176.9,302.6L237.9,313.1L263.0,316.8Z",
   "AR": "M516.7,343.3L592.6,340.5L594.4,344.7L591.8,347.5L589.3,351.8L600.7,351.1L600.4,355.3L597.9,356.7L597.5,360.1L594.4,364.0L595.0,369.3L593.5,373.3L591.8,374.0L593.0,375.9L590.2,377.8L589.2,381.6L587.4,382.7L587.9,387.1L584.7,388.5L584.9,389.9L581.3,393.8L582.6,396.1L579.5,399.8L576.9,406.8L580.3,409.5L578.8,411.4L580.0,416.0L578.8,419.1L533.9,420.5L525.9,420.6L525.7,408.8L523.1,407.9L519.5,409.1L517.5,407.1L517.9,367.9L514.2,343.4L516.7,343.3Z",
   "CA": "M52.7,157.9L66.1,161.7L87.0,167.9L103.3,172.2L93.8,209.5L86.7,236.7L103.1,261.5L119.1,285.4L131.9,304.7L141.3,318.8L158.2,344.3L157.6,347.1L159.8,351.2L161.1,357.4L164.0,361.2L161.3,363.7L158.2,364.6L155.3,368.0L155.0,373.2L153.8,376.4L149.6,378.7L149.1,387.1L151.6,387.7L151.8,391.9L150.4,393.7L146.7,393.8L122.3,390.9L102.4,388.5L100.9,385.1L101.8,380.6L101.6,375.0L100.0,370.6L95.6,364.1L89.7,357.5L88.0,358.5L85.5,357.0L86.4,355.0L84.3,349.9L80.0,349.8L73.4,344.8L73.0,342.0L68.9,337.5L63.3,336.2L59.1,333.6L53.1,332.7L50.8,329.1L53.1,323.2L52.3,322.0L54.0,318.0L50.4,313.6L51.3,309.2L49.7,308.5L47.9,303.9L46.2,302.6L45.9,300.0L41.8,289.4L39.5,285.9L40.8,278.8L41.9,279.8L44.3,276.0L42.9,271.6L39.8,271.2L36.9,266.7L36.3,263.6L37.3,261.1L36.4,257.2L38.0,251.5L41.1,252.4L42.1,244.2L40.5,244.6L39.1,248.4L35.6,248.3L32.5,244.2L33.4,239.0L32.0,234.3L29.4,230.9L28.5,227.5L25.3,220.6L26.6,219.2L26.5,211.4L28.7,207.7L29.0,201.3L26.7,194.3L23.7,189.8L24.1,185.7L30.9,177.6L32.7,174.7L32.6,172.0L36.0,166.0L36.5,159.8L35.2,157.9L37.4,153.4L52.7,157.9Z",
   "CO": "M293.6,231.0L329.5,235.2L357.1,237.6L390.0,240.1L388.6,262.4L384.5,329.2L367.9,327.9L344.6,326.2L300.7,321.7L291.1,320.5L263.0,316.8L266.6,291.1L266.7,288.6L269.3,269.9L275.1,228.6L293.6,231.0Z",
   "CT": "M859.6,175.4L879.5,170.8L882.9,183.8L882.5,186.1L881.0,186.1L874.4,189.5L866.0,191.1L863.1,195.0L859.5,196.9L855.6,200.5L853.8,198.3L857.2,194.9L855.6,193.4L852.7,176.8L859.6,175.4Z",
   "DE": "M832.9,232.7L832.0,235.6L830.6,237.4L831.7,240.8L834.8,243.5L836.6,248.7L841.4,253.5L843.1,253.4L845.5,260.7L834.7,262.9L827.2,235.8L829.5,232.8L832.9,232.7Z",
   "FL": "M687.5,454.9L696.7,453.7L700.1,459.8L726.0,458.0L750.2,456.4L751.8,460.9L754.1,460.4L754.3,455.9L752.9,451.9L754.4,450.0L759.0,451.1L764.2,451.2L766.8,460.5L770.9,470.7L778.6,483.8L789.5,497.3L788.4,498.6L789.9,505.4L794.8,512.6L803.0,527.2L805.0,531.8L805.8,536.8L806.6,555.0L804.8,555.7L803.8,561.5L804.8,563.2L801.6,567.8L799.9,567.1L796.5,569.4L790.3,571.4L788.1,569.4L788.4,566.0L782.5,557.1L778.7,555.9L775.9,557.6L772.7,552.7L771.4,548.4L766.6,544.1L765.1,541.1L765.1,536.3L762.7,535.8L763.7,538.5L761.7,539.5L753.8,528.6L750.9,526.0L755.5,516.5L751.8,517.5L749.6,520.6L746.5,516.7L748.2,504.3L747.4,494.3L744.8,492.2L743.6,489.1L739.8,488.9L734.8,484.2L731.1,482.5L730.5,479.3L727.9,478.4L725.5,475.1L717.6,471.2L711.4,473.1L712.1,476.4L710.0,476.0L702.6,481.1L694.2,483.0L694.2,480.6L691.9,477.9L681.3,472.5L674.0,470.5L667.6,470.4L662.3,471.4L651.0,474.5L653.5,471.0L651.9,469.3L652.3,465.6L647.7,461.8L648.1,458.8L687.5,454.9Z",
   "GA": "M720.2,361.3L717.0,366.5L717.0,368.9L723.6,372.8L725.5,372.1L728.9,376.6L729.8,379.0L733.3,383.2L737.9,385.4L740.8,389.1L746.2,392.2L746.4,394.7L750.2,398.3L755.6,400.9L757.3,404.4L758.2,409.0L761.0,410.2L764.8,415.6L765.5,419.3L770.0,420.6L766.7,428.7L766.5,432.7L765.1,436.3L765.4,439.8L763.6,441.7L764.2,451.2L759.0,451.1L754.4,450.0L752.9,451.9L754.3,455.9L754.1,460.4L751.8,460.9L750.2,456.4L726.0,458.0L700.1,459.8L696.7,453.7L694.0,447.9L694.7,442.0L692.1,435.6L693.3,431.7L692.8,428.9L695.6,425.7L693.4,424.7L693.9,422.4L691.5,419.1L688.7,413.2L681.1,385.8L675.8,367.1L698.7,364.3L711.2,362.9L720.2,361.3Z",
   "HI": "M308.0,575.0L303.0,573.2L302.2,571.3L302.9,566.5L299.3,558.3L302.1,555.6L304.0,551.9L302.6,549.4L303.0,546.9L308.7,549.9L315.0,552.0L318.9,555.3L318.9,558.1L324.7,562.6L321.2,566.4L314.9,568.2L310.4,571.0L308.0,575.0ZM288.6,530.7L290.9,533.6L293.9,532.3L300.4,535.7L299.4,538.7L292.8,540.2L291.5,539.7L291.2,535.9L287.8,535.1L286.4,533.0L288.6,530.7ZM280.7,526.9L278.7,529.1L274.1,529.1L275.5,526.6L280.7,526.9ZM261.3,516.5L263.4,521.5L262.3,524.4L258.0,524.8L255.2,518.9L257.7,518.8L261.3,516.5ZM231.0,505.0L233.3,505.3L234.3,507.5L233.7,510.6L231.3,512.6L225.0,510.0L225.8,506.6L231.0,505.0Z",
   "ID": "M198.3,36.0L193.6,57.8L197.1,64.8L195.9,70.7L198.2,73.9L201.0,75.4L201.0,77.0L205.3,83.9L205.5,86.4L208.9,89.4L208.8,90.9L213.2,91.6L209.5,99.3L208.1,104.3L209.0,107.9L205.8,109.7L206.4,112.2L205.2,114.4L208.0,117.3L212.3,115.1L214.3,113.0L216.6,115.6L215.8,117.3L216.6,121.8L218.2,126.6L219.8,128.5L218.9,132.7L220.4,134.8L223.5,135.6L224.3,143.0L225.8,144.5L227.8,142.8L232.6,143.8L236.5,142.5L238.4,143.9L242.2,143.6L242.8,144.9L246.1,144.6L250.4,140.6L252.2,144.8L254.6,147.6L246.0,201.8L228.0,198.9L197.9,193.4L150.4,183.4L159.3,143.8L162.9,137.2L162.1,135.1L159.2,134.1L158.8,130.9L163.6,123.9L165.4,123.6L167.7,120.7L167.8,118.7L170.2,116.4L171.9,112.9L176.5,107.2L175.9,104.0L172.7,101.7L171.4,97.5L172.2,93.8L171.1,89.6L171.7,87.8L178.1,59.2L184.2,32.9L198.3,36.0Z",
   "IL": "M576.5,207.4L606.4,205.7L622.2,204.5L622.1,208.7L625.0,213.5L628.3,221.4L632.9,273.7L631.4,277.9L633.9,282.4L634.6,286.3L632.7,289.7L632.4,292.6L629.7,297.6L627.8,298.2L628.5,300.9L627.3,302.1L626.7,307.4L627.4,308.9L625.4,312.2L627.3,316.0L620.4,318.6L619.9,321.0L621.7,323.8L619.7,325.8L613.1,322.8L611.1,323.2L608.7,327.3L609.7,328.5L606.9,328.4L602.5,322.4L603.9,320.8L602.1,316.7L601.9,313.2L596.0,308.9L594.2,309.5L592.1,306.7L586.8,302.5L586.6,298.9L589.2,293.0L588.6,291.0L590.1,288.2L587.6,286.8L583.8,286.0L582.0,288.2L580.6,286.9L579.1,279.7L573.2,275.2L567.7,269.8L565.3,263.1L564.9,258.6L566.2,255.3L566.3,251.3L570.8,248.6L571.1,245.2L573.1,242.9L573.2,239.0L570.3,236.0L571.2,232.0L577.5,230.6L582.5,227.5L582.8,224.1L584.9,222.5L585.2,218.2L584.6,215.4L580.8,213.4L580.3,211.2L576.5,207.4Z",
   "IN": "M653.1,217.9L672.3,215.7L672.5,217.2L675.7,243.5L679.1,274.4L677.9,275.6L680.0,281.5L677.1,281.9L674.1,284.4L669.7,283.9L670.4,288.2L667.7,290.4L666.9,293.3L664.0,294.7L663.0,300.4L661.2,302.1L657.1,300.4L656.2,298.0L652.7,301.1L653.3,303.5L649.5,304.8L648.2,302.7L644.0,305.3L642.8,307.7L638.2,304.8L636.0,305.8L634.4,304.3L633.1,306.0L628.8,306.7L627.4,308.9L626.7,307.4L627.3,302.1L628.5,300.9L627.8,298.2L629.7,297.6L632.4,292.6L632.7,289.7L634.6,286.3L633.9,282.4L631.4,277.9L632.9,273.7L628.3,221.4L630.0,222.7L635.0,222.2L639.6,219.2L653.1,217.9Z",
   "IA": "M563.7,186.0L566.1,185.9L566.4,189.2L568.9,191.2L567.1,194.0L567.9,198.9L569.3,202.4L575.2,204.6L576.5,207.4L580.3,211.2L580.8,213.4L584.6,215.4L585.2,218.2L584.9,222.5L582.8,224.1L582.5,227.5L577.5,230.6L571.2,232.0L570.3,236.0L573.2,239.0L573.1,242.9L571.1,245.2L570.8,248.6L566.3,251.3L566.2,255.3L564.4,254.7L560.8,250.3L559.1,250.5L535.5,252.0L512.6,252.7L493.8,252.5L491.9,249.6L492.8,243.9L491.1,238.9L491.2,233.3L488.4,231.3L487.9,228.3L488.9,225.6L487.8,221.7L485.6,220.3L482.7,210.3L479.7,205.4L481.2,202.1L481.7,197.7L483.0,196.2L481.0,194.0L481.5,190.1L480.6,188.3L482.7,187.8L563.7,186.0Z",
   "KS": "M391.1,262.5L501.5,265.5L503.2,267.6L508.6,269.3L504.9,275.8L507.1,277.9L509.8,283.1L513.5,284.2L514.1,332.3L418.6,330.9L384.5,329.2L388.6,262.4L391.1,262.5Z",
   "KY": "M695.4,279.9L699.6,282.5L702.1,280.5L708.7,281.4L710.3,278.9L712.6,277.9L713.8,281.5L715.9,281.9L718.6,284.6L719.1,291.3L721.7,295.2L724.9,298.1L726.1,300.5L729.8,302.5L732.1,302.6L726.4,309.5L720.5,313.6L720.8,315.3L718.4,317.1L718.5,319.1L715.3,320.4L714.5,323.0L705.6,327.3L705.3,327.7L690.4,329.4L677.4,330.2L673.9,330.8L654.6,332.0L632.6,334.5L628.7,333.8L629.3,337.8L607.5,339.3L605.4,339.7L606.2,336.8L608.9,337.6L609.7,328.5L608.7,327.3L611.1,323.2L613.1,322.8L619.7,325.8L621.7,323.8L619.9,321.0L620.4,318.6L627.3,316.0L625.4,312.2L627.4,308.9L628.8,306.7L633.1,306.0L634.4,304.3L636.0,305.8L638.2,304.8L642.8,307.7L644.0,305.3L648.2,302.7L649.5,304.8L653.3,303.5L652.7,301.1L656.2,298.0L657.1,300.4L661.2,302.1L663.0,300.4L664.0,294.7L666.9,293.3L667.7,290.4L670.4,288.2L669.7,283.9L674.1,284.4L677.1,281.9L680.0,281.5L677.9,275.6L679.1,274.4L685.5,273.7L689.5,277.8L690.0,279.8L695.4,279.9Z",
   "LA": "M533.9,420.5L578.8,419.1L580.6,421.6L579.3,422.6L579.4,427.1L582.2,429.8L583.0,436.3L581.0,441.5L576.8,444.9L575.9,449.9L574.0,449.5L574.1,457.6L571.9,458.0L573.4,462.3L572.1,463.9L607.7,461.9L606.3,469.3L609.8,473.9L610.7,477.5L613.2,479.7L607.7,483.1L607.5,485.3L612.2,486.4L613.9,482.8L618.1,486.0L618.0,488.8L615.8,490.1L611.4,489.4L612.1,491.4L610.8,494.6L614.7,497.1L620.6,497.6L623.0,500.7L624.7,501.0L621.9,505.0L618.5,504.5L615.4,500.8L608.2,499.3L607.9,495.5L604.5,496.9L604.9,500.1L603.5,503.1L601.0,503.7L599.0,500.6L594.5,500.7L593.1,504.2L590.2,505.3L587.0,503.4L584.4,503.3L581.7,498.0L577.3,495.8L575.6,496.2L573.7,491.7L568.7,492.6L568.5,489.8L563.7,492.6L564.4,494.7L560.7,496.8L554.8,496.0L547.9,493.2L543.0,492.0L532.7,493.4L531.3,494.3L529.6,492.1L533.9,484.2L532.3,480.0L533.6,477.6L533.0,474.6L534.8,472.3L536.6,466.5L536.2,461.8L530.8,453.0L530.6,448.1L526.4,443.4L525.9,420.6L533.9,420.5Z",
   "ME": "M890.7,144.0L888.4,143.0L888.1,140.8L885.0,139.0L876.4,111.2L872.0,97.6L877.6,92.9L876.2,91.7L877.7,87.8L879.8,85.5L879.0,84.4L880.8,81.8L879.0,78.3L878.9,72.3L880.7,69.8L879.9,63.6L886.5,44.2L889.3,44.2L890.6,48.1L892.9,48.9L896.9,45.2L899.8,44.3L901.4,42.2L906.5,44.3L909.7,46.4L917.0,69.9L918.5,75.7L924.0,75.6L924.0,78.3L926.0,80.2L925.6,82.6L928.7,85.2L931.3,83.6L936.3,90.3L934.3,94.6L932.1,93.9L931.3,96.7L929.0,96.7L929.4,98.8L926.5,99.4L923.4,105.3L921.4,102.5L919.8,102.7L921.5,105.9L918.6,108.5L916.9,106.1L915.7,108.0L911.8,109.1L910.8,106.0L908.7,107.4L909.8,109.5L909.0,114.8L909.8,115.9L907.7,119.3L904.6,119.2L903.7,122.3L901.4,123.4L900.1,126.1L897.7,126.3L896.3,124.2L894.0,128.9L895.5,131.0L893.2,132.5L893.6,134.5L891.4,137.8L890.7,144.0Z",
   "MD": "M832.0,275.1L831.2,275.2L832.0,275.1ZM766.3,247.7L827.2,235.8L834.7,262.9L845.5,260.7L844.3,270.7L841.8,271.6L837.4,273.9L834.0,275.6L833.4,272.0L831.7,270.9L833.3,268.9L829.9,265.9L829.4,267.6L825.9,268.0L823.9,264.3L825.0,264.1L824.0,258.9L824.6,256.7L821.7,250.1L822.7,245.6L825.3,244.3L824.9,240.0L822.9,241.0L823.3,243.1L819.5,246.8L818.8,249.6L819.8,255.9L818.8,259.3L820.6,264.1L823.5,267.1L823.8,269.8L825.7,272.2L825.3,274.1L820.7,271.5L814.9,270.9L812.5,267.9L809.8,270.4L808.1,268.1L809.9,264.2L810.7,260.4L812.4,257.7L809.9,256.0L808.7,257.6L806.2,256.0L802.5,255.6L801.8,252.4L799.7,250.9L797.0,251.1L794.0,245.3L791.2,245.9L788.0,244.4L786.7,246.4L784.0,246.7L783.8,249.3L778.6,248.6L775.9,252.4L773.6,252.1L771.0,256.4L768.1,259.0L766.3,247.7Z",
   "MA": "M888.4,148.5L890.0,148.5L891.6,152.1L891.7,155.3L890.0,158.8L890.8,162.1L894.4,161.6L897.4,164.5L897.8,167.3L899.7,167.5L900.5,169.9L905.5,170.8L910.0,167.4L909.7,170.7L902.9,175.3L900.2,176.2L898.0,174.7L895.6,175.9L895.9,177.5L893.2,179.2L891.0,175.7L890.3,175.1L888.3,174.0L886.1,169.2L883.8,169.8L879.6,171.1L859.6,175.4L852.7,176.8L852.2,176.1L852.5,161.0L865.3,158.2L883.6,154.2L884.8,151.8L888.4,148.5Z",
   "MI": "M694.3,213.6L672.5,217.2L672.3,215.7L653.1,217.9L639.6,219.2L642.6,216.0L644.3,210.8L646.1,207.6L647.1,203.2L647.4,197.1L646.4,190.6L640.4,178.2L641.3,173.3L639.7,167.6L642.7,161.3L643.0,156.3L642.2,153.7L644.6,152.3L644.6,148.7L648.5,147.3L651.1,143.0L651.7,151.0L653.4,151.2L655.0,147.0L654.3,140.2L655.4,138.4L659.5,136.8L657.6,132.3L659.9,128.0L663.3,127.4L667.5,129.4L671.3,129.3L673.5,132.2L676.4,132.1L681.6,134.3L683.3,134.0L686.5,138.3L684.7,141.1L687.2,144.1L688.4,147.7L688.6,156.0L685.7,158.5L685.5,162.8L681.9,164.7L680.5,170.0L681.5,171.8L685.5,173.2L688.1,170.0L690.8,163.9L695.9,161.0L698.8,162.3L700.9,165.2L703.8,174.1L704.7,178.6L707.2,183.9L706.7,192.1L704.3,193.7L703.8,190.8L702.1,191.9L701.1,198.8L698.1,201.8L697.9,207.0L694.4,211.7L694.3,213.6ZM651.3,129.6L651.8,132.2L649.8,132.9L650.3,129.1L651.3,129.6ZM620.6,146.8L618.0,144.7L619.2,141.4L615.5,141.3L616.7,138.1L616.5,134.3L613.1,131.9L611.1,129.3L604.4,127.6L602.4,128.5L595.7,125.8L579.6,122.4L577.7,118.7L574.8,117.6L580.6,114.9L583.1,112.1L589.6,110.6L593.7,107.1L595.7,106.8L597.2,104.4L601.6,100.8L603.8,97.8L607.2,95.8L610.6,97.0L605.3,104.2L604.1,106.6L604.5,110.7L607.1,107.3L612.4,107.4L616.6,109.2L620.8,114.9L622.9,115.8L626.6,114.4L627.6,115.7L631.5,116.0L639.1,110.2L643.3,109.3L649.0,108.9L652.6,106.8L655.5,106.3L656.7,112.4L659.8,112.8L662.7,111.5L664.1,112.8L665.9,110.8L670.2,109.6L671.2,117.3L673.6,120.3L676.8,120.7L676.8,118.5L679.7,118.1L681.6,120.2L680.5,122.1L672.0,121.7L668.1,123.2L663.4,121.0L662.4,123.6L663.3,125.6L661.3,125.3L658.1,122.6L653.0,121.4L650.5,121.6L648.4,124.7L644.4,125.9L640.0,125.7L638.4,127.1L638.2,129.5L633.6,132.1L633.6,129.2L631.4,128.8L630.9,131.8L627.4,132.3L625.9,133.8L624.0,139.2L620.2,146.2L620.6,146.8ZM596.9,85.1L593.4,88.2L591.5,88.7L591.5,86.4L600.4,80.5L598.9,84.3L596.9,85.1Z",
   "MN": "M550.4,115.8L549.2,114.9L546.2,116.8L546.7,129.8L545.8,131.2L541.5,133.1L538.2,138.0L538.0,141.1L539.8,141.3L541.8,144.0L540.2,147.5L540.6,151.2L539.8,159.3L544.1,163.2L547.3,163.4L549.1,165.8L554.0,168.0L554.9,170.9L559.5,174.4L562.1,175.2L565.4,179.9L565.1,183.4L566.1,185.9L563.7,186.0L482.7,187.8L482.9,148.1L479.4,145.5L476.7,141.2L481.0,136.6L481.3,134.0L480.8,125.2L478.9,122.9L477.7,118.1L478.0,112.2L477.5,111.2L477.1,97.2L474.2,89.7L473.1,85.5L472.8,76.6L473.8,73.7L471.9,66.7L502.3,66.8L502.3,58.4L505.1,58.6L507.1,60.3L509.1,71.6L510.7,72.9L515.5,73.2L516.1,74.2L521.8,74.6L522.5,77.0L527.3,76.2L527.3,75.3L531.0,74.0L534.4,74.4L538.2,76.0L539.4,78.3L541.5,78.0L543.7,82.8L544.6,80.7L548.3,79.6L549.1,81.6L553.5,82.9L553.6,84.8L555.9,86.2L560.3,85.2L562.9,82.9L566.4,81.4L567.9,84.5L570.4,83.7L573.4,84.2L576.9,83.5L581.1,86.0L584.9,85.3L584.6,86.5L579.8,89.6L573.0,92.2L568.6,94.7L562.5,100.7L559.8,104.3L555.7,108.5L549.2,114.0L550.4,115.8Z",
   "MS": "M624.7,371.7L629.5,371.3L631.5,373.5L631.0,398.0L630.1,440.4L634.3,474.0L632.3,475.1L627.7,475.0L625.7,473.7L621.2,475.0L615.0,478.0L613.2,479.7L610.7,477.5L609.8,473.9L606.3,469.3L607.7,461.9L572.1,463.9L573.4,462.3L571.9,458.0L574.1,457.6L574.0,449.5L575.9,449.9L576.8,444.9L581.0,441.5L583.0,436.3L582.2,429.8L579.4,427.1L579.3,422.6L580.6,421.6L578.8,419.1L580.0,416.0L578.8,411.4L580.3,409.5L576.9,406.8L579.5,399.8L582.6,396.1L581.3,393.8L584.9,389.9L584.7,388.5L587.9,387.1L587.4,382.7L589.2,381.6L590.2,377.8L593.0,375.9L591.8,374.0L624.7,371.7Z",
   "MO": "M559.1,250.5L560.8,250.3L564.4,254.7L566.2,255.3L564.9,258.6L565.3,263.1L567.7,269.8L573.2,275.2L579.1,279.7L580.6,286.9L582.0,288.2L583.8,286.0L587.6,286.8L590.1,288.2L588.6,291.0L589.2,293.0L586.6,298.9L586.8,302.5L592.1,306.7L594.2,309.5L596.0,308.9L601.9,313.2L602.1,316.7L603.9,320.8L602.5,322.4L606.9,328.4L609.7,328.5L608.9,337.6L606.2,336.8L605.4,339.7L604.3,339.7L603.3,339.8L603.8,345.3L600.7,351.1L589.3,351.8L591.8,347.5L594.4,344.7L592.6,340.5L516.7,343.3L514.2,343.4L514.1,332.3L513.5,284.2L509.8,283.1L507.1,277.9L504.9,275.8L508.6,269.3L503.2,267.6L501.5,265.5L497.4,259.7L493.8,252.5L512.6,252.7L535.5,252.0L559.1,250.5Z",
   "MT": "M372.1,61.8L370.1,86.6L366.5,128.6L364.8,149.4L335.7,146.6L286.8,140.6L256.4,136.1L254.6,147.6L252.2,144.8L250.4,140.6L246.1,144.6L242.8,144.9L242.2,143.6L238.4,143.9L236.5,142.5L232.6,143.8L227.8,142.8L225.8,144.5L224.3,143.0L223.5,135.6L220.4,134.8L218.9,132.7L219.8,128.5L218.2,126.6L216.6,121.8L215.8,117.3L216.6,115.6L214.3,113.0L212.3,115.1L208.0,117.3L205.2,114.4L206.4,112.2L205.8,109.7L209.0,107.9L208.1,104.3L209.5,99.3L213.2,91.6L208.8,90.9L208.9,89.4L205.5,86.4L205.3,83.9L201.0,77.0L201.0,75.4L198.2,73.9L195.9,70.7L197.1,64.8L193.6,57.8L198.3,36.0L263.7,48.5L293.4,52.9L372.1,61.8Z",
   "NE": "M372.5,194.3L399.7,196.3L449.8,198.5L450.3,199.6L458.5,203.8L460.5,201.6L462.8,202.1L470.3,202.3L478.8,206.5L479.8,209.6L482.7,210.3L485.6,220.3L487.8,221.7L488.9,225.6L487.9,228.3L488.4,231.3L491.2,233.3L491.1,238.9L492.8,243.9L491.9,249.6L493.8,252.5L497.4,259.7L501.5,265.5L391.1,262.5L388.6,262.4L390.0,240.1L357.1,237.6L360.9,193.4L372.5,194.3Z",
   "NV": "M150.4,183.4L197.9,193.4L176.9,302.6L173.5,320.2L171.0,323.6L169.2,323.4L167.6,320.3L161.1,319.9L159.6,332.9L160.2,337.4L159.8,341.5L158.2,344.3L141.3,318.8L131.9,304.7L119.1,285.4L103.1,261.5L86.7,236.7L93.8,209.5L103.3,172.2L123.9,177.4L150.4,183.4Z",
   "NH": "M872.0,97.6L876.4,111.2L885.0,139.0L888.1,140.8L888.4,143.0L890.7,144.0L890.0,148.5L888.4,148.5L884.8,151.8L883.6,154.2L865.3,158.2L863.5,156.9L862.9,153.7L863.9,152.2L863.0,149.1L861.9,139.8L863.5,134.9L863.6,129.7L864.5,127.6L863.1,122.3L867.6,119.0L869.2,114.7L866.8,111.6L868.0,107.5L867.3,105.5L868.0,99.4L871.6,99.1L872.0,97.6Z",
   "NJ": "M845.4,199.3L851.5,201.2L851.1,207.9L848.8,210.0L848.1,213.6L852.9,214.2L853.9,216.6L854.7,228.7L851.6,238.6L848.8,241.9L847.0,248.0L844.7,244.8L839.5,244.1L832.6,240.6L831.5,237.5L831.3,237.0L832.0,235.6L832.9,232.7L836.9,229.9L836.8,228.2L841.0,223.5L841.4,221.4L835.8,218.1L835.0,215.4L832.8,215.1L832.0,212.6L833.7,208.3L831.8,206.3L834.9,200.9L835.2,198.3L837.0,196.3L845.4,199.3Z",
   "NM": "M291.1,320.5L300.7,321.7L344.6,326.2L367.9,327.9L367.0,339.0L366.4,339.0L362.2,394.1L360.1,416.6L358.5,438.7L292.7,432.6L291.9,434.7L293.8,437.5L262.6,433.7L261.3,443.7L245.7,441.6L263.0,316.8L291.1,320.5Z",
   "NY": "M839.5,112.5L840.7,116.9L840.9,121.1L843.2,124.7L843.8,128.9L843.1,133.7L845.9,139.2L845.5,141.2L848.8,144.2L851.9,159.2L852.5,161.0L852.2,176.1L852.7,176.8L855.6,193.4L857.2,194.9L853.8,198.3L855.6,200.5L862.8,200.6L863.9,198.9L869.8,197.5L872.6,196.0L876.7,191.4L877.6,193.7L880.5,194.2L875.4,198.8L864.1,206.7L859.2,208.9L855.6,209.5L853.3,211.1L851.1,207.9L851.5,201.2L845.4,199.3L837.0,196.3L835.9,194.9L833.4,195.4L829.7,192.3L829.4,189.0L826.9,187.0L825.7,187.4L823.3,184.8L753.0,198.6L752.0,193.1L760.6,184.8L761.6,181.5L764.4,178.9L762.5,175.4L761.1,174.9L759.1,169.1L767.8,164.9L776.0,163.5L779.4,163.5L783.4,165.2L785.4,163.8L792.2,162.5L796.0,160.1L799.5,155.3L802.3,154.6L801.2,148.6L801.9,144.9L797.9,143.3L798.1,140.4L803.5,135.4L805.1,131.7L810.8,122.9L816.9,117.7L827.4,115.9L839.5,112.5Z",
   "NC": "M752.5,321.4L764.4,319.8L778.0,317.6L840.7,305.2L844.5,313.4L839.5,313.6L839.1,314.8L833.5,317.4L832.9,318.8L829.1,319.9L829.6,321.4L834.1,319.4L835.0,320.2L840.0,318.0L842.1,319.7L845.1,318.2L847.3,323.2L846.8,325.9L844.8,326.6L841.6,332.9L835.8,334.4L835.6,338.3L838.8,341.4L841.0,341.7L838.5,348.6L835.2,348.5L829.7,350.3L826.1,352.4L820.8,357.8L817.1,364.2L815.9,371.6L811.8,370.8L805.7,373.4L781.7,356.2L761.8,359.2L761.7,356.6L758.4,353.3L756.7,354.9L756.3,352.7L734.3,354.9L729.6,356.4L726.1,359.0L720.2,361.3L711.2,362.9L698.7,364.3L698.6,359.1L702.0,358.2L702.9,354.4L706.8,350.5L711.6,349.8L715.5,345.8L719.9,344.0L723.0,338.5L725.2,336.7L726.0,338.8L732.3,333.6L735.6,334.0L737.2,329.6L740.3,328.0L740.2,322.7L752.5,321.4Z",
   "ND": "M471.9,66.7L473.8,73.7L472.8,76.6L473.1,85.5L474.2,89.7L477.1,97.2L477.5,111.2L478.0,112.2L477.7,118.1L478.9,122.9L480.8,125.2L481.3,134.0L366.5,128.6L370.1,86.6L372.1,61.8L471.9,66.7Z",
   "OH": "M740.9,201.1L745.7,230.6L743.5,232.2L745.1,234.4L745.5,237.8L744.1,243.4L743.9,251.7L738.6,259.9L736.6,261.2L734.5,260.0L733.1,263.4L731.2,263.6L729.7,268.1L730.5,270.6L729.1,272.9L726.1,269.9L723.8,275.7L725.1,278.9L723.2,280.4L723.0,283.4L718.6,284.6L715.9,281.9L713.8,281.5L712.6,277.9L710.3,278.9L708.7,281.4L702.1,280.5L699.6,282.5L695.4,279.9L690.0,279.8L689.5,277.8L685.5,273.7L679.1,274.4L675.7,243.5L672.5,217.2L694.3,213.6L701.0,215.7L703.4,217.3L704.8,215.3L708.8,218.3L711.2,219.1L718.4,215.1L722.9,215.0L727.1,210.2L733.4,205.2L740.9,201.1Z",
   "OK": "M418.6,330.9L514.1,332.3L514.2,343.4L517.9,367.9L517.5,407.1L510.5,404.7L508.7,402.2L504.0,400.0L502.8,402.0L498.1,401.9L497.1,400.7L492.9,402.9L491.1,401.7L487.2,402.8L483.6,406.2L482.2,404.2L478.4,402.6L474.4,402.6L473.2,400.0L468.5,404.9L467.1,402.1L465.0,403.0L463.4,401.1L459.2,399.3L455.9,402.2L454.6,399.1L452.0,398.7L450.6,396.2L447.1,395.2L444.8,397.2L443.3,395.3L439.8,395.5L435.9,393.4L432.2,393.5L431.0,389.2L425.3,388.8L423.1,389.4L419.2,385.0L417.9,385.2L419.7,342.1L387.9,340.4L367.0,339.0L367.9,327.9L384.5,329.2L418.6,330.9Z",
   "OR": "M79.1,69.5L80.5,69.7L83.0,72.8L83.6,75.8L82.5,82.4L89.5,86.9L96.9,85.3L101.1,86.1L105.5,88.6L105.6,90.1L114.6,89.2L116.3,90.8L120.8,91.4L125.1,90.2L132.1,90.0L138.1,91.1L140.5,90.2L171.4,97.5L172.7,101.7L175.9,104.0L176.5,107.2L171.9,112.9L170.2,116.4L167.8,118.7L167.7,120.7L165.4,123.6L163.6,123.9L158.8,130.9L159.2,134.1L162.1,135.1L162.9,137.2L159.3,143.8L150.4,183.4L123.9,177.4L103.3,172.2L87.0,167.9L66.1,161.7L52.7,157.9L37.4,153.4L35.9,150.3L36.8,143.1L38.5,138.4L37.6,134.0L40.2,131.0L43.0,125.7L47.1,120.3L49.7,115.3L56.9,97.8L57.4,95.3L61.2,87.9L65.1,77.2L66.1,70.9L67.9,67.6L74.7,66.2L76.6,69.4L79.1,69.5Z",
   "PA": "M752.0,193.1L753.0,198.6L823.3,184.8L825.7,187.4L826.9,187.0L829.4,189.0L829.7,192.3L833.4,195.4L835.9,194.9L837.0,196.3L835.2,198.3L834.9,200.9L831.8,206.3L833.7,208.3L832.0,212.6L832.8,215.1L835.0,215.4L835.8,218.1L841.4,221.4L841.0,223.5L836.8,228.2L836.9,229.9L832.9,232.7L829.5,232.8L827.2,235.8L766.3,247.7L749.0,250.7L745.7,230.6L740.9,201.1L743.7,199.4L751.9,192.7Z",
   "RI": "M891.0,175.7L893.2,179.2L890.2,180.5L891.0,175.7ZM883.8,169.8L886.1,169.2L888.3,174.0L890.3,175.1L888.3,175.2L887.5,178.8L888.2,183.5L882.5,186.1L882.9,183.8L879.6,171.1L883.8,169.8Z",
   "SC": "M726.1,359.0L729.6,356.4L734.3,354.9L756.3,352.7L756.7,354.9L758.4,353.3L761.7,356.6L761.8,359.2L781.7,356.2L805.7,373.4L802.7,375.1L799.5,379.4L796.6,385.7L796.7,390.4L794.3,394.5L790.3,395.3L789.8,398.0L786.0,401.7L784.2,405.2L780.6,407.1L777.1,411.2L776.9,412.8L773.4,415.2L770.0,420.6L765.5,419.3L764.8,415.6L761.0,410.2L758.2,409.0L757.3,404.4L755.6,400.9L750.2,398.3L746.4,394.7L746.2,392.2L740.8,389.1L737.9,385.4L733.3,383.2L729.8,379.0L728.9,376.6L725.5,372.1L723.6,372.8L717.0,368.9L717.0,366.5L720.2,361.3L726.1,359.0Z",
   "SD": "M366.5,128.6L481.3,134.0L481.0,136.6L476.7,141.2L479.4,145.5L482.9,148.1L482.7,187.8L480.6,188.3L481.5,190.1L481.0,194.0L483.0,196.2L481.7,197.7L481.2,202.1L479.7,205.4L482.7,210.3L479.8,209.6L478.8,206.5L470.3,202.3L462.8,202.1L460.5,201.6L458.5,203.8L450.3,199.6L449.8,198.5L399.7,196.3L372.5,194.3L360.9,193.4L364.5,149.4L366.5,128.6Z",
   "TN": "M629.3,337.8L628.7,333.8L632.6,334.5L654.6,332.0L673.9,330.8L677.4,330.2L690.4,329.4L705.3,327.7L705.6,327.3L740.2,322.7L740.3,328.0L737.2,329.6L735.6,334.0L732.3,333.6L726.0,338.8L725.2,336.7L723.0,338.5L719.9,344.0L715.5,345.8L711.6,349.8L706.8,350.5L702.9,354.4L702.0,358.2L698.6,359.1L698.7,364.3L675.8,367.1L644.5,369.9L629.5,371.3L624.7,371.7L591.8,374.0L593.5,373.3L595.0,369.3L594.4,364.0L597.5,360.1L597.9,356.7L600.4,355.3L600.7,351.1L603.8,345.3L603.3,339.8L604.3,339.7L605.4,339.7L607.5,339.3L629.3,337.8Z",
   "TX": "M387.9,340.4L419.7,342.1L417.9,385.2L419.2,385.0L423.1,389.4L425.3,388.8L431.0,389.2L432.2,393.5L435.9,393.4L439.8,395.5L443.3,395.3L444.8,397.2L447.1,395.2L450.6,396.2L452.0,398.7L454.6,399.1L455.9,402.2L459.2,399.3L463.4,401.1L465.0,403.0L467.1,402.1L468.5,404.9L473.2,400.0L474.4,402.6L478.4,402.6L482.2,404.2L483.6,406.2L487.2,402.8L491.1,401.7L492.9,402.9L497.1,400.7L498.1,401.9L502.8,402.0L504.0,400.0L508.7,402.2L510.5,404.7L517.5,407.1L519.5,409.1L523.1,407.9L525.7,408.8L525.9,420.6L526.4,443.4L530.6,448.1L530.8,453.0L536.2,461.8L536.6,466.5L534.8,472.3L533.0,474.6L533.6,477.6L532.3,480.0L533.9,484.2L529.6,492.1L531.3,494.3L528.2,494.5L518.3,497.7L514.7,496.0L514.0,492.4L511.5,495.0L509.7,494.4L508.8,497.5L510.8,498.9L511.2,503.0L507.6,507.3L501.9,512.8L490.2,518.6L489.0,517.7L485.5,519.1L485.4,517.8L480.6,518.7L478.4,516.0L477.0,516.6L482.1,522.3L478.4,524.0L474.9,522.9L474.3,526.9L469.9,531.0L465.3,538.5L462.3,546.4L460.1,545.7L459.5,548.6L461.8,547.9L460.6,553.7L459.1,553.9L458.9,557.1L460.8,559.0L461.2,565.6L463.4,567.9L463.8,572.1L465.5,575.8L459.4,578.0L456.9,575.1L452.2,573.9L446.0,574.0L440.7,570.3L436.7,569.8L433.7,566.9L429.6,565.8L426.8,562.9L425.2,556.3L421.8,552.2L422.3,548.8L420.8,545.2L421.5,542.1L419.1,538.5L417.1,538.1L413.9,534.8L413.0,530.8L410.3,527.1L406.2,523.9L404.5,517.2L402.7,515.3L400.4,509.8L399.8,505.5L397.5,502.2L393.5,499.2L392.7,497.2L389.0,495.3L386.4,490.3L378.0,488.8L373.0,488.7L368.8,486.7L367.7,488.9L363.1,489.4L359.3,493.7L356.7,500.9L355.5,500.9L352.6,505.1L349.4,504.9L344.9,501.2L333.5,494.8L331.4,491.7L327.1,488.5L324.4,482.0L324.7,476.3L321.9,471.4L321.6,467.4L319.7,464.7L312.8,460.2L309.4,454.7L306.4,452.6L303.5,447.9L299.0,445.1L296.4,439.0L293.8,437.5L291.9,434.7L292.7,432.6L358.5,438.7L360.1,416.6L362.2,394.1L366.4,339.0L367.0,339.0L387.9,340.4Z",
   "UT": "M228.0,198.9L246.0,201.8L242.5,223.8L275.1,228.6L269.3,269.9L266.7,288.6L266.6,291.1L263.0,316.8L237.9,313.1L176.9,302.6L197.9,193.4L228.0,198.9Z",
   "VT": "M867.3,105.5L868.0,107.5L866.8,111.6L869.2,114.7L867.6,119.0L863.1,122.3L864.5,127.6L863.6,129.7L863.5,134.9L861.9,139.8L863.0,149.1L863.9,152.2L862.9,153.7L863.5,156.9L865.3,158.2L852.5,161.0L851.9,159.2L848.8,144.2L845.5,141.2L845.9,139.2L843.1,133.7L843.8,128.9L843.2,124.7L840.9,121.1L840.7,116.9L839.5,112.5L855.2,108.8L867.3,105.5Z",
   "VA": "M841.8,271.6L844.3,270.7L842.9,274.8L840.8,276.7L840.6,282.0L838.8,290.8L836.2,293.1L834.7,290.3L834.7,283.3L837.4,273.9L841.8,271.6ZM786.0,250.0L796.0,255.6L797.0,251.1L799.7,250.9L801.8,252.4L802.5,255.6L806.2,256.0L808.7,257.6L810.7,260.4L809.9,264.2L808.1,265.6L807.4,268.9L808.6,271.1L813.0,269.4L814.5,272.7L820.7,273.0L822.9,275.4L828.2,277.4L827.4,283.9L830.3,288.3L828.5,291.0L828.8,293.8L831.3,295.1L829.5,298.2L825.2,295.4L824.6,296.8L828.2,298.7L836.8,297.5L840.7,305.2L778.0,317.6L764.4,319.8L752.5,321.4L740.2,322.7L705.6,327.3L714.5,323.0L715.3,320.4L718.5,319.1L718.4,317.1L720.8,315.3L720.5,313.6L726.4,309.5L732.1,302.6L732.1,304.4L735.0,307.8L738.2,309.2L740.3,308.7L743.2,305.3L745.9,307.3L750.1,305.4L757.2,299.9L758.1,301.1L760.8,298.7L760.2,294.7L761.5,290.9L764.1,287.1L764.7,282.9L767.4,278.2L767.8,273.0L771.2,275.5L774.1,275.9L775.5,273.8L777.7,265.4L780.2,266.9L786.3,256.6L786.0,250.0Z",
   "WA": "M184.2,32.9L178.1,59.2L171.7,87.8L171.1,89.6L172.2,93.8L171.4,97.5L140.5,90.2L138.1,91.1L132.1,90.0L125.1,90.2L120.8,91.4L116.3,90.8L114.6,89.2L105.6,90.1L105.5,88.6L101.1,86.1L96.9,85.3L89.5,86.9L82.5,82.4L83.6,75.8L83.0,72.8L80.5,69.7L79.1,69.5L76.6,69.4L74.7,66.2L72.3,64.6L69.8,65.2L67.5,62.6L69.0,59.8L71.3,58.9L69.7,53.7L71.2,41.7L70.5,39.8L71.4,31.3L69.5,27.3L70.3,20.8L73.1,17.2L75.4,20.0L80.4,24.4L84.4,25.5L88.1,27.7L92.1,27.8L93.4,30.1L96.8,31.0L97.8,36.3L99.6,36.4L98.2,42.8L97.6,48.7L99.2,48.5L99.1,43.3L100.9,38.7L104.6,34.5L103.3,32.0L104.1,28.5L103.8,24.3L105.3,21.7L105.3,18.3L103.1,17.1L101.7,14.1L102.9,12.0L184.2,32.9ZM99.3,26.6L101.4,26.2L99.9,30.4L98.1,28.1L99.3,26.6ZM96.6,19.6L99.0,17.3L100.1,21.2L98.7,23.9L95.6,22.2L96.6,19.6Z",
   "WV": "M745.7,230.6L749.0,250.7L766.3,247.7L768.1,259.0L771.0,256.4L773.6,252.1L775.9,252.4L778.6,248.6L783.8,249.3L784.0,246.7L786.7,246.4L788.0,244.4L791.2,245.9L794.0,245.3L797.0,251.1L796.0,255.6L786.0,250.0L786.3,256.6L780.2,266.9L777.7,265.4L775.5,273.8L774.1,275.9L771.2,275.5L767.8,273.0L767.4,278.2L764.7,282.9L764.1,287.1L761.5,290.9L760.2,294.7L760.8,298.7L758.1,301.1L757.2,299.9L750.1,305.4L745.9,307.3L743.2,305.3L740.3,308.7L738.2,309.2L735.0,307.8L732.1,304.4L732.1,302.6L729.8,302.5L726.1,300.5L724.9,298.1L721.7,295.2L719.1,291.3L718.6,284.6L723.0,283.4L723.2,280.4L725.1,278.9L723.8,275.7L726.1,269.9L729.1,272.9L730.5,270.6L729.7,268.1L731.2,263.6L733.1,263.4L734.5,260.0L736.6,261.2L738.6,259.9L743.9,251.7L744.1,243.4L745.5,237.8L745.1,234.4L743.5,232.2L745.7,230.6Z",
   "WI": "M574.8,117.6L577.7,118.7L579.6,122.4L595.7,125.8L602.4,128.5L604.4,127.6L611.1,129.3L613.1,131.9L616.5,134.3L616.7,138.1L615.5,141.3L619.2,141.4L618.0,144.7L620.6,146.8L620.2,149.5L617.3,150.2L615.2,155.5L614.5,159.1L616.4,159.5L618.6,157.0L620.8,152.5L623.8,150.5L625.9,144.7L629.0,143.2L629.0,146.1L627.0,149.0L623.5,158.5L622.8,163.7L623.2,167.3L621.7,168.7L620.6,173.8L621.5,177.9L620.4,180.8L619.1,187.9L620.0,193.3L622.3,198.0L622.2,204.5L606.4,205.7L576.5,207.4L575.2,204.6L569.3,202.4L567.9,198.9L567.1,194.0L568.9,191.2L566.4,189.2L566.1,185.9L565.1,183.4L565.4,179.9L562.1,175.2L559.5,174.4L554.9,170.9L554.0,168.0L549.1,165.8L547.3,163.4L544.1,163.2L539.8,159.3L540.6,151.2L540.2,147.5L541.8,144.0L539.8,141.3L538.0,141.1L538.2,138.0L541.5,133.1L545.8,131.2L546.7,129.8L546.2,116.8L549.2,114.9L550.4,115.8L553.8,115.9L564.2,111.7L568.0,109.4L569.4,110.9L567.5,113.9L572.7,117.3L574.8,117.6Z",
   "WY": "M286.8,140.6L335.7,146.6L364.5,149.4L360.9,193.4L357.1,237.6L329.5,235.2L293.6,231.0L275.1,228.6L242.5,223.8L246.0,201.8L254.6,147.6L256.4,136.1L286.8,140.6Z"
  }
 }
};
