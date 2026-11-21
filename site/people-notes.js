/* 연준 인물 페이지(people.html)의 '발언 정리' 자료 — 사람이 고친다(자동 갱신 없음, 기준일 asof). 2026-11-16 시작.
 * 운영자가 받은 발언 요약을 이 저장소가 자기 말로 다시 쓴 것: head = 한 줄 결론, chips = 쟁점 칩([글, up|mid|down]), points = 주제별 문장(t) ·
 * 발언자 본인의 영어 원문(q — 짧게, 원문·보도에서 찾은 것만). 새 묶음을 받으면 같은 꼴로 notes 앞쪽에 더한다(id = <키>-<날짜>).
 * 연준 밖 인사는 others에 이름·기관을 적고 같은 notes에 넣는다(화면의 '기타' 칸). 꼴은 scripts/test_people_site.py가 본다. */
window.PEOPLE_NOTES = {
 "asof": "2026-11-21",
 "about": "운영자가 받은 발언 요약을 이 저장소가 다시 쓴 것이다. 문장은 이 저장소의 요약이고, q(따옴표)만 발언자 본인의 영어 원문이다. 확인 수준: 원문 확인(1차 자료를 직접 읽어 인용을 찾음) · 보도 확인(보도·검색으로 날짜·자리·인용을 찾음) · 출처 미확인. 칩은 운영자가 읽은 것이고 예측이 아니다.",
 "topics": [
  [
   "policy",
   "정책 경로"
  ],
  [
   "rates",
   "금리 수준"
  ],
  [
   "inflation",
   "물가"
  ],
  [
   "labor",
   "고용"
  ],
  [
   "growth",
   "성장·소비"
  ],
  [
   "ai",
   "AI"
  ],
  [
   "finstab",
   "금융안정"
  ],
  [
   "market",
   "시장 기능"
  ],
  [
   "housing",
   "주택"
  ]
 ],
 "issues": [
  [
   "next",
   "다음 결정"
  ],
  [
   "pace",
   "속도"
  ],
  [
   "level",
   "지금 금리"
  ],
  [
   "inflation",
   "물가 진단"
  ],
  [
   "labor",
   "고용"
  ],
  [
   "ai",
   "AI"
  ]
 ],
 "others": {
  "bailey": {
   "name_ko": "앤드루 베일리",
   "name_en": "Andrew Bailey",
   "org": "영란은행",
   "role": "총재 · 금융안정위원회(FSB) 의장",
   "region": "영국"
  },
  "lombardelli": {
   "name_ko": "클레어 롬바르델리",
   "name_en": "Clare Lombardelli",
   "org": "영란은행",
   "role": "통화정책 담당 부총재 · 통화정책위원회(MPC) 위원",
   "region": "영국"
  },
  "greene": {
   "name_ko": "메건 그린",
   "name_en": "Megan Greene",
   "org": "영란은행",
   "role": "통화정책위원회(MPC) 외부 위원",
   "region": "영국"
  },
  "nagel": {
   "name_ko": "요아힘 나겔",
   "name_en": "Joachim Nagel",
   "org": "독일 분데스방크",
   "role": "총재 · ECB 정책위원",
   "region": "유로존"
  },
  "lane": {
   "name_ko": "필립 레인",
   "name_en": "Philip R. Lane",
   "org": "유럽중앙은행(ECB)",
   "role": "집행이사 · 수석 이코노미스트",
   "region": "유로존"
  },
  "kazaks": {
   "name_ko": "마르틴시 카작스",
   "name_en": "Mārtiņš Kazāks",
   "org": "라트비아 중앙은행",
   "role": "총재 · ECB 정책위원",
   "region": "유로존"
  },
  "makhlouf": {
   "name_ko": "가브리엘 마클루프",
   "name_en": "Gabriel Makhlouf",
   "org": "아일랜드 중앙은행",
   "role": "총재 · ECB 정책위원",
   "region": "유로존"
  },
  "vujcic": {
   "name_ko": "보리스 부이치치",
   "name_en": "Boris Vujčić",
   "org": "유럽중앙은행(ECB)",
   "role": "부총재(2026-06~) · 전 크로아티아 중앙은행 총재",
   "region": "유로존"
  }
 },
 "notes": [
  {
   "id": "cook-20261120",
   "who": "cook",
   "date": "2026-11-20",
   "venue": "연설",
   "event": "칠레 중앙은행 제29회 연례 콘퍼런스 기조연설(산티아고)",
   "src": "https://www.federalreserve.gov/newsevents/speech/cook20261120a.htm",
   "cert": "원문 확인",
   "head": "10월 동결 반대·25bp 인상 선호 — 미루면 뒤처질 위험, 9월 한 번으론 모자랄 듯",
   "chips": {
    "next": [
     "추가 인상(10월 반대표)",
     "up"
    ],
    "pace": [
     "기다림에도 비용",
     "up"
    ],
    "level": [
     "금융여건 너무 완화적",
     "up"
    ],
    "inflation": [
     "67개월째 목표 위·넓게 퍼짐",
     "up"
    ],
    "labor": [
     "최대고용 부합",
     "mid"
    ],
    "ai": [
     "성장 가속·가격 파급",
     "up"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "9월 목표 범위 3.75~4%로의 인상엔 찬성했고 10월 동결엔 반대해 25bp 더 올리길 원했다. 첫째 이유: 물가가 목표를 끈질기게 웃돌고 둔화 조짐도 뚜렷하지 않은데 금융여건이 너무 완화적이다 — 지금 기조는 AI 인프라 구축을 누르지 못하는 듯하고 주가는 계속 소비를 받친다.",
     "q": "financial conditions are too accommodative at a time when inflation remains stubbornly above target, with no clear signs of disinflation in train"
    },
    {
     "t": "policy",
     "s": "그래서 동결을 이어가면 플러스 산출갭이 벌어지고 물가 압력도 커진다. 금리를 그대로 두는 것도 올리는 것과 똑같이 하나의 통화정책 행동으로 본다.",
     "q": "I see the act of holding the rate steady as much a monetary policy action as the act of increasing the rate"
    },
    {
     "t": "policy",
     "s": "둘째 이유는 급함 — 5년 반 넘게 목표를 웃돌아 하루가 지날수록 가격·임금 결정자가 기대인플레이션을 올려 잡을 위험이 커진다. 인상을 미루면 뒤처질 위험이 있고, 뒤처지면 나중에 따라잡느라 더 많이·더 크게 올려야 할 수 있어 금융시스템의 스트레스를 키우고 가계에 불필요한 피해를 줄 수 있다.",
     "q": "waiting longer to implement rate increases risks getting behind the curve"
    },
    {
     "t": "policy",
     "s": "다른 환경이라면 위원회가 인내할 수 있겠지만 지금은 그럴 여유가 없다. 9월 인상 뒤 나온 물가 지표(지난주 발표 포함)는 물가가 지속 가능한 경로로 돌아간다는 충분한 증거가 못 된다.",
     "q": "in this economic climate we do not have that luxury"
    },
    {
     "t": "policy",
     "s": "9월 25bp 한 번으로 물가 경로가 바뀔지는 회의적이다. 앞으로의 조정 횟수와 폭은 정책에 대한 경제의 반응을 지켜보며 정해야 한다.",
     "q": "I am skeptical that September's single 1/4 point rate increase will be enough to change the path of inflation"
    },
    {
     "t": "inflation",
     "s": "물가는 67개월째 2%를 웃돈다. 지난주 지표로 추정한 10월 PCE 전년비 3.8%, 근원 3.2% — 에너지가 큰 몫이지만 압력의 원천이 갈수록 다양해진다.",
     "q": "the sources of price pressure facing American families are increasingly varied"
    },
    {
     "t": "inflation",
     "s": "2022년 중반~작년 초엔 2%로 가는 듯했으나 지난 18개월 통상정책 변화·지정학·기술 인프라 대규모 투자로 일부 되돌려졌다. 올해 대부분 3%를 웃돌았고 둔화 증거가 거의 없다 — 최근 지표에선 항공료·가전·가구·호텔·외식 등 넓은 품목이 빠르게 오른다.",
     "q": "there is little evidence inflation is declining"
    },
    {
     "t": "inflation",
     "s": "중동 분쟁으로 올해 에너지 가격이 다시 올랐고, 기반시설 손상·재고 고갈로 유가가 오래 높을 수 있다는 전문가 경고가 있다. 미국에서 관세의 물가 효과는 누그러진 것으로 보이지만 앞으로의 통상정책 불확실성은 남아 있다."
    },
    {
     "t": "labor",
     "s": "10월 실업률 4.1%로 1년 가까이 소폭 내려왔다. 10월 고용 +16.5만명에 업종도 넓어지는 조짐, 9월 구인 750만건(대체로 그대로), 신규 실업수당 청구 4주 평균 약 19.5만건(역사적 저점 근처) — 노동시장은 대체로 균형이고 서서히 나아진다."
    },
    {
     "t": "labor",
     "s": "'낮은 채용' 환경이 신규 진입자에게 특히 어렵고 임금이 물가의 타격을 넘을 만큼 오르지 않아 불만은 이해할 만하다. 그래도 낮은 실업률은 최대고용에 부합해, 통화정책 결정자로서 물가 쪽에 더 집중한다.",
     "q": "I am more focused on the inflation side of our remit"
    },
    {
     "t": "growth",
     "s": "성장은 강하고 빨라진다. 3분기 GDP 연율 3.4%로 상반기보다 높아졌고 AI 인프라 구축이 큰 기여 요인이다. 높은 에너지 가격과 물가에도 실질 가계지출이 연율 3.8% 늘었다.",
     "q": "The AI infrastructure buildout I previously discussed is a significant contributor to this acceleration"
    },
    {
     "t": "ai",
     "s": "기업들이 발표한 데이터센터 건설 계획은 2조달러를 넘지만 실현된 건 일부다. 이미 산출 지표에 보이고, 반도체·첨단장비 가격, 건설 임금, 전기요금으로 번진다는 증거가 있다. 일부 추정으로는 건설 중인 세계 데이터센터 용량의 약 절반이 미국 밖이다.",
     "q": "there is evidence of spillovers to other parts of the economy"
    },
    {
     "t": "labor",
     "s": "AI가 총실업률에 뚜렷한 흔적을 남긴 증거는 거의 없지만 도입 초기라 안심하기 이르다. 소프트웨어 코딩·동시통역 일자리 수요가 식었다는 증거가 이미 일부 있고, 젊은 층의 구직이 길어지는 것을 초급 일자리에 대한 AI 압력 탓으로 보는 이도 있다.",
     "q": "I think it is too soon to feel comforted"
    },
    {
     "t": "ai",
     "s": "역사로 보면 성공적 전환 가능성이 크고 영구적 일자리 손실은 가능성이 낮지만, 전환이 오래 걸리고 AI로 인한 일자리 감소가 새 일자리 창출보다 먼저 올 가능성도 0이 아니다. 업종별 AI 도입 속도와 기업 안 일자리 구성 변화를 지켜본다.",
     "q": "job losses due to AI could precede new job creation"
    },
    {
     "t": "finstab",
     "s": "AI는 증기기관·전기·인터넷에 견주거나 넘어설 수 있는 범용기술로 생산성 붐을 가져올 수 있지만, 고통스러운 노동시장 전환과 사이버·금융안정 위험을 깊이 걱정한다. 받은 요약에는 AI 인프라 자금조달 방식을 신중히 지켜본다는 대목도 있으나 연설 원문에서 원래 문장은 찾지 못했다(질의응답은 확인하지 못함).",
     "q": "I worry deeply about our shared risks resulting from the technology"
    }
   ]
  },
  {
   "id": "paulson-20261120",
   "who": "paulson",
   "date": "2026-11-20",
   "venue": "인터뷰",
   "event": "블룸버그 뉴스 인터뷰(뉴욕)",
   "src": "https://www.investing.com/news/economy-news/feds-paulson-open-to-backtoback-rate-hikes-at-steady-pace-5042425",
   "cert": "보도 확인",
   "date_note": "블룸버그 기사 주소의 날짜와 '뉴욕에서 한 블룸버그 인터뷰'라는 보도 조각으로 정함 — 기사 본문을 열지 못해 미 동부 날짜를 직접 확인하지는 못했다(11-19 뉴욕 연설과는 다른 자리)",
   "head": "금리는 더 높아져야 — 연속 인상도 검토하되 일정 약속 없이 신중한 속도로",
   "chips": {
    "next": [
     "인상(연속도 검토)",
     "up"
    ],
    "pace": [
     "신중한 속도·일정 약속 없음",
     "mid"
    ],
    "level": [
     "더 높아져야",
     "up"
    ],
    "inflation": [
     "최우선(위험은 양쪽)",
     "up"
    ],
    "labor": [
     "임금 압력 확산 증거 없음",
     "mid"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "금리가 어느 쪽으로 가야 하는지는 아주 분명하다 — 더 높아져야 한다.",
     "q": "The direction of travel, in terms of where rates need to go, is really clear"
    },
    {
     "t": "policy",
     "s": "올리더라도 신중한 속도로 가야 한다는 뜻을 다시 밝혔다. 보도에 따르면 가계·기업·은행이 적응할 시간을 주려는 것이고, 여건보다 너무 앞서거나 뒤처지지 않으려는 취지의 설명도 했다 — 그 대목의 원래 문장은 찾지 못했다."
    },
    {
     "t": "policy",
     "s": "연속 인상도 충분히 검토할 만한 선택지라고 했다. 다만 매 회의나 한 회의 걸러 올리는 식의 정해진 일정을 약속하지는 않는다는 뜻도 보도됐다 — 보도마다 옮긴 말이 달라 원래 문장은 찾지 못했다.",
     "q": "I'm certainly open to considering that. I think that's a very reasonable thing to have on the table"
    },
    {
     "t": "inflation",
     "s": "물가가 분명히 우선이지만 위험은 양쪽에 다 있다고 했다.",
     "q": "Clearly inflation is the priority, but there are risks on both sides"
    },
    {
     "t": "growth",
     "s": "보도에 따르면 경제가 꽤 잘 돌아간다고 했다 — 보도마다 표현이 조금 달라 원래 문장은 찾지 못했다."
    },
    {
     "t": "labor",
     "s": "보도에 따르면 개별 임금 압력 사례는 눈여겨보지만 그런 사례가 노동시장 전반으로 번진다는 증거는 아직 없다고 했다. 임금 상승률이 그동안 2% 물가와 맞아 왔다는 대목은 원래 문장을 찾지 못했다."
    }
   ]
  },
  {
   "id": "jefferson-20261119",
   "who": "jefferson",
   "date": "2026-11-19",
   "venue": "연설",
   "event": "IMF·브라질 중앙은행 '중남미 물가목표제 25년' 콘퍼런스 패널(브라질리아)",
   "src": "https://www.federalreserve.gov/newsevents/speech/jefferson20261119a.htm",
   "cert": "원문 확인",
   "head": "에너지 충격 전부터 물가는 2% 위 — 기대가 흔들리면 물가에 더 강하게, 억제되면 고용 위험을 앞세울 수도",
   "chips": {
    "next": [
     "조건부(기대·물가 압력)",
     "mid"
    ],
    "inflation": [
     "에너지 충격 전부터 2% 위",
     "up"
    ],
    "labor": [
     "AI 대체·새 일자리 모두",
     "mid"
    ],
    "ai": [
     "지금은 수요·물가 상방",
     "up"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "충격이 산출 갭과 물가를 같은 방향으로 움직이면 두 목표가 함께 가지만, 반대로 움직이면 상충이 생긴다. 중동 분쟁과 엮인 최근 유가 상승이 그 예 — 에너지 충격은 물가를 밀어 올리면서 실질소득과 수요를 누를 수 있다. 대응은 각 목표를 놓쳤을 때의 상대적 비용과 위험 균형에 달렸다.",
     "q": "The appropriate response depends on the relative costs of missing each objective and the balance of risks"
    },
    {
     "t": "inflation",
     "s": "최근 에너지 가격 충격이 닥쳤을 때 미국 물가는 이미 2% 목표를 웃돌고 있었다.",
     "q": "inflation in the U.S. was already above our 2 percent target"
    },
    {
     "t": "policy",
     "s": "기대인플레이션이 고정에서 풀릴 위험이 있으면 물가에 더 강하게 대응하는 것이 맞고, 물가 압력이 억제돼 있으면 고용의 하방 위험을 앞세우는 것이 신중할 수 있다 — 어느 쪽인지는 조건으로만 말했다.",
     "q": "If inflation expectations risk becoming unanchored, a stronger reaction to inflation is warranted"
    },
    {
     "t": "ai",
     "s": "빠른 AI 도입은 수요와 공급에 시차를 두고 닿는 까다로운 충격이다. 기업의 AI 도입은 지난 2년 새 크게 늘었다. 수요 쪽에선 낙관론이 데이터센터·첨단 컴퓨팅 장비 투자를 끌고, 공급 쪽에선 업무 자동화·보강으로 생산성과 잠재성장률을 높일 수 있다. 지금은 구축이 수요·물가를 밀어 올리지만 앞으로는 생산성 향상이 성장을 받치며 물가를 누를 수 있다.",
     "q": "Currently, the AI buildout is exerting upward pressure on demand and inflation"
    },
    {
     "t": "labor",
     "s": "AI는 일부 일자리를 대체할 수 있고 해당 가계엔 적잖은 어려움이다. 다만 과거의 여러 기술 혁신처럼 아직 상상하지 못한 새 일자리와 기업을 만들 수도 있다.",
     "q": "AI could lead to the creation of new jobs and new firms that we have not yet imagined"
    },
    {
     "t": "policy",
     "s": "에너지·무역·AI 충격이 한꺼번에 펼쳐져 연준과 각국 중앙은행이 동시에 따져야 한다. 과제는 각자 책무에 주의를 기울이며 정책 기조를 목표에 맞게 조율하는 것 — 미국 경제에 대한 목표는 견조한 노동시장을 지키면서 물가 안정을 되찾는 것이다.",
     "q": "my goal is to restore price stability while maintaining a solid labor market"
    }
   ]
  },
  {
   "id": "goolsbee-20261119",
   "who": "goolsbee",
   "date": "2026-11-19",
   "venue": "대담",
   "event": "이코노믹 클럽 오브 인디애나 오찬 대담(인디애나폴리스) · 같은 날 기자 전화 회견",
   "src": "https://www.investing.com/news/economy-news/feds-goolsbee-says-ai-surge-could-strain-us-capacity-overheat-economy-5039887",
   "cert": "보도 확인",
   "head": "AI 붐이 과열 위험을 키운다 — 연준의 일은 과열을 막는 것, 지금은 2%로 가는 경로 아님",
   "chips": {
    "next": [
     "모든 선택지(폭은 미언급)",
     "up"
    ],
    "inflation": [
     "경계선상 우려 수준",
     "up"
    ],
    "ai": [
     "투자 과열·IPO 부 효과 주시",
     "up"
    ]
   },
   "points": [
    {
     "t": "ai",
     "s": "AI 붐이 경제의 과열 가능성을 키운다 — 달리 보기 어렵다. 거의 전례 없는 규모의 기업 투자가 한꺼번에 몰려, 경제의 생산능력이 그 덩어리를 소화하지 못할 위험이 크다.",
     "q": "there's a high danger that the economy's capacity cannot handle that kind of a pig through the python"
    },
    {
     "t": "policy",
     "s": "AI가 나중에 생산성 붐을 가져올 수는 있어도, 그사이 연준의 일은 물가를 잡는 것 — 곧 이 붐이 경제를 과열시키지 않게 막는 것이다.",
     "q": "The Fed's job is to prevent this thing from overheating the economy"
    },
    {
     "t": "growth",
     "s": "과열을 부를 수 있는 두 힘은 데이터센터 건설과, 앞으로 생길 AI 관련 부를 미리 당겨 쓰는 소비다 — 보도로는 둘 다 경제를 쉽게 달굴 수 있다고 했다. 부가 1조달러 단위로 생기면 그 돈은 쓰이게 마련이다.",
     "q": "If you hand people a trillion dollars of wealth, they're going to spend it"
    },
    {
     "t": "growth",
     "s": "그가 '1.5조달러짜리 IPO'라 부른 앤트로픽 상장으로 초기 주주의 지분이 1조달러를 훌쩍 넘는다 — 그 돈을 어떻게 쓰느냐가 거시적으로 의미 있는 통계가 될 것이다. 다만 보도로는 지금까지 과열 위험은 새 주주의 소비보다 AI 투자 쪽이 더 컸고, 이미 효과가 났다고 걱정하기보다 지켜보는 단계라고 했다.",
     "q": "is going to become a macro-relevant statistic"
    },
    {
     "t": "inflation",
     "s": "여러 달 연속 경계선상의, 우려스러울 만큼 높은 물가가 이어졌고, 진전을 기대한 부문에서도 진전이 거의 없다.",
     "q": "borderline, disturbingly high inflation rates"
    },
    {
     "t": "policy",
     "s": "물가가 저절로 2%로 돌아가리라고 보느냐 아니냐를 짚었는데(앞뒤 원래 문장은 찾지 못했다), 지금까지의 증거는 그 경로를 가리키지 않는다고 했다. 12월에 더 큰 폭의 인상을 지지할지는 밝히지 않았고, 보도로는 모든 선택지가 열려 있다고 했다.",
     "q": "The evidence does not suggest we're on a path back to 2%"
    },
    {
     "t": "ai",
     "s": "보도로는 연준이 AI 생산성 효과가 기술 부문 밖으로 번지는 증거를 아직 찾는 중이고, 넓게 번지지 않으면 AI가 반짝하고 마는 현상에 그칠 수 있다고 했다."
    },
    {
     "t": "labor",
     "s": "받은 요약에는 이민 정책이 바뀌어 경기를 판단할 때 월간 고용 증가 폭의 무게가 줄었다는 대목도 있다 — 원래 문장은 찾지 못했다."
    }
   ]
  },
  {
   "id": "barr-20261119",
   "who": "barr",
   "date": "2026-11-19",
   "venue": "대담",
   "event": "FinRegLab 2026 AI 심포지엄 대담(워싱턴)",
   "src": "https://www.investing.com/news/economy-news/feds-barr-worried-regulation-changes-may-increase-financial-sector-risks-5039831",
   "cert": "보도 확인",
   "head": "물가 너무 높아 통화정책 더 조정해야 — 감독·규제 변화는 당장보다 긴 꼬리가 걱정",
   "chips": {
    "next": [
     "추가 조정 필요(인상 쪽)",
     "up"
    ],
    "level": [
     "금융여건 꽤 완화적",
     "up"
    ],
    "inflation": [
     "너무 높음",
     "up"
    ],
    "ai": [
     "접근성 확대·뱅크런 가속 위험",
     "mid"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "물가가 너무 높아 통화정책을 더 조정해야 할 것으로 본다. 전날(11-18) 뉴욕 연은 행사의 연설 원고에선 경제가 지금 전망대로 가면 금리를 더 올리는 것이 적절하다고 했다.",
     "q": "I think we're going to need to adjust monetary policy further"
    },
    {
     "t": "rates",
     "s": "보도로는 금융여건이 꽤 완화적이어서 경기를 받쳐 주고 있다고 했다 — 원래 문장은 찾지 못했다."
    },
    {
     "t": "finstab",
     "s": "최근의 감독·규제 변화는 당장 걱정할 일은 아니지만 길게 이어질 결과를 낳는다. 보도로는 시간이 갈수록 감독이 서서히 약해져 은행 체계가 덜 안전해질 수 있고, 앞으로 시장의 문제를 알아채고 대응하기도 어려워질 수 있다고 했다.",
     "q": "longer term tails to them, longer term consequences"
    },
    {
     "t": "finstab",
     "s": "어느 한 변화도 내일 닥칠 위험은 아니지만 걱정할 만한 위험은 있다. 지난 1년 반 동안의 감독·규제 방향에 반대한다는 뜻을 공개적으로 밝혀 왔다고 했다.",
     "q": "there are risks worth worrying about"
    },
    {
     "t": "ai",
     "s": "보도로는 AI가 금융서비스 접근성을 넓힐 수 있지만 금융 부문 규정을 따라야 하고 뱅크런을 더 빠르게 만들 위험도 있다고 했다 — 원래 문장은 찾지 못했다. 사흘 전(11-16) 밀라노 연설 원고에도 AI 에이전트가 자금을 빠르게 옮겨 몇 분 만에 번지는 뱅크런을 부추길 수 있다는 대목이 있다."
    }
   ]
  },
  {
   "id": "paulson-20261119",
   "who": "paulson",
   "date": "2026-11-19",
   "venue": "연설·대담",
   "event": "머니 마케티어스(뉴욕) — 통화정책 소통 연설과 질의응답",
   "src": "https://www.philadelphiafed.org/the-economy/monetary-policy/261119-money-marketeers-speech",
   "cert": "보도 확인",
   "head": "긴축할 일이 더 남았다 — 평시엔 금리 경로 안내보다 반응함수를 함께 이해하는 게 중요",
   "chips": {
    "next": [
     "추가 긴축(시점 언급 없음)",
     "up"
    ],
    "pace": [
     "신중히(악화 시 더 빠르게)",
     "mid"
    ],
    "level": [
     "금리 더 높여야",
     "up"
    ],
    "inflation": [
     "너무 높음 — 우선 과제",
     "up"
    ],
    "labor": [
     "완전고용",
     "mid"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "연설 뒤 질의응답에서: 성장은 강해졌고 노동시장은 완전고용이라 지금은 물가가 분명한 우선 과제다. 보도에 따르면 준비한 원고에는 가까운 정책 전망이 없었다.",
     "q": "it's clear that inflation needs to be ... the priority"
    },
    {
     "t": "policy",
     "s": "물가를 끌어내리는 길은 금리를 높이는 것이고 긴축할 일이 더 남았다고 질의응답에서 말했다.",
     "q": "The way we bring inflation down is by having higher rates"
    },
    {
     "t": "policy",
     "s": "10월 동결은 방향이 아니라 속도의 문제다. 보도에 따르면 시장이 추가 긴축을 예상하고 있어 한 번 쉬어도 정책이 있어야 할 자리보다 뒤처지지 않았고, 신중한 속도는 경제가 적응할 시간을 주고 새 정보를 소화하기에도 낫다고 했다.",
     "q": "I see holding rates steady in October as a matter of pace, not direction"
    },
    {
     "t": "policy",
     "s": "기대인플레이션이 오르거나 임금 압력이 커지거나 기조 물가가 높아지면 더 빨리 움직이겠다 — 11월 10일 연설의 세 조건을 되풀이했다.",
     "q": "I would want to move more quickly"
    },
    {
     "t": "policy",
     "s": "연설의 물음은 제목대로 '서로 이해하느냐'다. 소통은 반응함수를 함께 이해하게 할 때 가장 잘 작동하고 사람들은 믿는 메시지에 따라 움직인다 — 그래서 신뢰가 핵심이고 그것을 당연하게 여기지 않는다.",
     "q": "I don't take credibility for granted"
    },
    {
     "t": "policy",
     "s": "보도에 따르면 평시에는 반응함수가 잘 이해되면 금리 경로 안내의 값어치가 크지 않다고 했다. 안내가 가장 값진 때는 기준금리가 제로 하한 근처일 때(통상의 반응함수에서 벗어나겠다는 약속)라는 대목은 의역으로만 봤고 원래 문장은 찾지 못했다."
    },
    {
     "t": "policy",
     "s": "점도표의 쓸모는 시기에 따라 다르다 — 어떤 때엔 매우 유용하고 어떤 때엔 덜하다.",
     "q": "I view the dot plot as very helpful in some periods and less helpful in others"
    },
    {
     "t": "inflation",
     "s": "일시적 충격은 신뢰를 잃지 않고 넘겨 볼 수 있다 — 다만 무엇을 일시적으로 보는지, 무엇이 그 판단을 바꿀지 함께 설명해야 한다는 취지다. 장기 기대가 잘 고정돼 있을 때라는 조건과 충격이 이어지면 대응한다는 믿음이 전제라는 대목은 원래 문장을 찾지 못했다."
    },
    {
     "t": "inflation",
     "s": "보도에 따르면 장기 기대인플레이션이 안정돼 있다는 것은 연준이 신뢰를 지키고 있다는 증거라고 했다."
    },
    {
     "t": "labor",
     "s": "보도에 따르면 임금 상승률은 2% 물가와 맞는 흐름이라고 했다 — 다만 그 흐름을 흔들 수 있는 현장 일화는 눈여겨볼 만하다는 것이다."
    }
   ]
  },
  {
   "id": "barkin-20261119",
   "who": "barkin",
   "date": "2026-11-19",
   "venue": "대담",
   "event": "버지니아 주 상원 재정·세출위원회 연례회의(샬러츠빌)",
   "src": "https://virginiabusiness.com/barkin-fed-richmond-workforce-ai-data-centers/",
   "cert": "보도 확인",
   "date_note": "보도(11-20 자)의 '목요일' — 위원회 연례회의 일정(11-19~20)으로 맞춘 미 동부 날짜",
   "head": "수요가 견조한 까닭의 일부는 AI — 나중엔 문제 될 수도, 노동력은 늘지 않아",
   "chips": {
    "next": [
     "확인한 보도엔 언급 없음",
     "mid"
    ],
    "labor": [
     "노동력 늘지 않음",
     "mid"
    ],
    "ai": [
     "지금 수요 요인·나중엔 문제",
     "mid"
    ]
   },
   "points": [
    {
     "t": "ai",
     "s": "경제 전반의 수요가 견조한 까닭의 일부는 AI다. 지금은 성장을 돕지만 나중에는 문제를 낳을 수도 있다.",
     "q": "Part of the reason demand's so healthy in the entire economy is AI"
    },
    {
     "t": "growth",
     "s": "보도에 따르면 데이터센터 투자가 꺾이거나 AI발 해고가 늘면 경제의 약 70%를 차지하는 소비가 줄어들 수 있다고 짚었다."
    },
    {
     "t": "labor",
     "s": "지금까지는 AI가 실업률 급등을 부르지 않았다."
    },
    {
     "t": "labor",
     "s": "미국과 버지니아의 노동력이 모두 늘지 않는다 — 은퇴, 낮은 출산율, 그리고 3년 전 약 200만 명이던 이민 유입이 사실상 0으로 줄어든 탓."
    },
    {
     "t": "housing",
     "s": "적정 가격 주택이 모자라 일하는 사람이 다른 주로 떠나면 버지니아 노동력이 줄어들 위험이 있다."
    }
   ]
  },
  {
   "id": "waller-20261118",
   "who": "waller",
   "date": "2026-11-18",
   "venue": "인터뷰",
   "event": "CNBC 스쿼크박스",
   "src": "https://www.cnbc.com/2026/11/18/federal-reserve-governor-christopher-waller.html",
   "cert": "보도 확인",
   "head": "12월 50bp가 아마 필요 — 25bp라면 1월 인상을 아주 분명히 예고해야",
   "chips": {
    "next": [
     "50bp 또는 25bp+1월 예고",
     "up"
    ],
    "pace": [
     "분명한 신호로 빨리",
     "up"
    ],
    "level": [
     "작년 인하 3번 되돌려야",
     "up"
    ],
    "inflation": [
     "서비스로 확산·3% 굳기",
     "up"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "12월 8~9일 회의에서는 50bp 인상이 아마 필요하다 — 사람들을 놀라게 할 만큼 움직여야 할 수도 있다.",
     "q": "You might need to, like, shock people"
    },
    {
     "t": "policy",
     "s": "25bp로 그치려면 1월에도 올린다는 것을 시장에 아주 분명히 알려야 하고, 그러지 않을 거면 12월에 50bp로 해 둬야 한다. 로이터는 대안을 '2027년 더 빠른 인상 속도를 알리는 것'으로 전했다.",
     "q": "If you're not going to signal this very clearly to markets"
    },
    {
     "t": "policy",
     "s": "로이터는 워시 의장이 선제 안내를 피하려 하지만 지금은 강한 소통이 필요하다는 대목도 전했다 — 월러 본인의 말인지 기사의 설명인지는 가리지 못했다. 그 신호를 FOMC 성명과 의장 기자회견으로 내야 한다는 대목 — 원래 문장은 찾지 못했다. 보도는 시장에 분명히 신호하라는 데까지만 전한다."
    },
    {
     "t": "rates",
     "s": "보도로는 작년의 인하 세 번은 되돌려야 한다고 했다."
    },
    {
     "t": "inflation",
     "s": "최근 물가는 연율 3%를 웃돌고 빨라지고 있을 수 있다. 방향이 잘못됐고 번지는 중이다 — 빨리 오르는 품목 상당수가 서비스라 높은 유가 같은 일시적 요인으로는 대부분 설명되지 않는다."
    },
    {
     "t": "inflation",
     "s": "기업들이 3% 안팎을 당연한 인상 폭으로 여기고 소비자에게 넘기기 시작했다. 지난주 만난 한 사업가는 고객이 감당할 수 있다고 봐 3%를 올렸다고 했다 — 이런 말이 들리기 시작하면 물가를 끌어내리기 어려워진다.",
     "q": "that's when you start having problems trying to get inflation down"
    },
    {
     "t": "inflation",
     "s": "기업이 3% 인상을 당연하게 여기는 이런 심리를 이제 깨기 시작해야 한다 — 그래서 물가 대응이 더 적극적이어야 한다.",
     "q": "That's the kind of psychology we need to start breaking"
    }
   ]
  },
  {
   "id": "daly-20261118",
   "who": "daly",
   "date": "2026-11-18",
   "venue": "대담",
   "event": "세인트루이스 연은 행사(화상 대담)",
   "src": "https://www.bloomberg.com/news/articles/2026-11-18/fed-s-daly-urges-rate-hikes-with-a-thoughtful-measured-approach",
   "cert": "보도 확인",
   "head": "추가 긴축이 필요하다 — 다만 지금까지처럼 신중한 접근으로",
   "chips": {
    "next": [
     "추가 인상 필요",
     "up"
    ],
    "pace": [
     "신중한 접근 유지",
     "mid"
    ],
    "inflation": [
     "너무 오래 높았음",
     "up"
    ],
    "labor": [
     "안정·역동성 낮음",
     "mid"
    ],
    "ai": [
     "AI 투자도 불확실성",
     "mid"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "물가가 2%로 서서히 내려가는 경로에 있다고 완전히 확신할 수 있는 데까지 가려면 금리를 더 올려야 한다.",
     "q": "We'll have to further tighten interest rates"
    },
    {
     "t": "policy",
     "s": "지금까지 해 온 신중한 접근이 옳은 길이라고 했다(한 보도는 이를 이어 가는 것을 지지한다는 말까지 실었다). 들어오는 지표를 따져 보고 기업·소비자의 이야기를 들으며 움직인다는 것.",
     "q": "the right way to go"
    },
    {
     "t": "policy",
     "s": "보도로는 신중해야 하는 까닭으로 높은 불확실성을 들었다 — 관세 정책의 향방, 이란 전쟁, AI 인프라 투자의 결과가 아직 분명하지 않다."
    },
    {
     "t": "inflation",
     "s": "속보 머리글로는 물가가 너무 오래 너무 높았다고 했다."
    },
    {
     "t": "growth",
     "s": "속보 머리글로는 소비가 소득 하위층에서도 견조하고, 이 회복력은 강점이지만 위험이기도 하다고 했다. 받은 요약은 그 위험을 물가 안정의 부담으로 읽었지만 원래 문장은 찾지 못했다."
    },
    {
     "t": "labor",
     "s": "속보 머리글로는 노동시장이 전반적으로 안정돼 있지만 역동성은 크지 않다고 했다."
    }
   ]
  },
  {
   "id": "barr-20261118",
   "who": "barr",
   "date": "2026-11-18",
   "venue": "연설",
   "event": "뉴욕 연은 '빠진 시장 만들기' 콘퍼런스 — 소외 지역 투자",
   "src": "https://www.federalreserve.gov/newsevents/speech/barr20261118a.htm",
   "cert": "원문 확인",
   "head": "전망대로면 추가 인상이 적절 — 경제는 강하지만 중·저소득층은 힘들고 일부 지역은 뒤처짐",
   "chips": {
    "next": [
     "전망대로면 추가 인상",
     "up"
    ],
    "inflation": [
     "너무 높음 — 생계비 부담",
     "up"
    ],
    "labor": [
     "실업률 낮음",
     "mid"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "물가를 2% 목표로 제때 되돌리는 일이 중요하다. 경제가 지금 전망대로 움직이면 그 목표를 위해 금리를 더 올리는 것이 적절할 것으로 본다 — 판단은 들어오는 지표, 바뀌는 전망, 위험의 균형을 계속 보며 한다.",
     "q": "If the economy evolves as I currently forecast, I expect it will be appropriate to raise rates further"
    },
    {
     "t": "inflation",
     "s": "물가가 너무 높아 가계가 생활비를 감당하기 어렵고, 힘겨운 가정이 많다.",
     "q": "inflation is too high, making it hard for American families to make ends meet"
    },
    {
     "t": "growth",
     "s": "경제 전체는 강하다 — 실업률이 낮고 소비가 견조하며 기업투자도 탄탄하다.",
     "q": "the economy is strong, with low unemployment, solid consumer spending, and robust business investment"
    },
    {
     "t": "growth",
     "s": "나라 전체로는 활동과 고용이 늘지만 모든 가계·지역이 잘되는 것은 아니다. 부유한 가계는 괜찮지만 중·저소득 가계는 힘들고 일부 지역은 뒤처진다. 연준 소비자금융조사로는 가계 대다수가 가진 재산이 매우 적고, 많은 지역에서 경제가 강해도 보수 좋은 일자리를 찾기 어려운 사람이 있다.",
     "q": "middle- and lower-income households are struggling, and the economy is leaving some communities behind"
    },
    {
     "t": "housing",
     "s": "미국인의 44%가 빈곤선 아래 인구가 5분의 1 이상인 저소득 지역에 산다는 추정(브루킹스)을 들며, 이런 지역은 주택·사업·기반시설 투자가 모자란 경우가 많다고 했다.",
     "q": "These communities often lack sufficient investment in housing, business, and infrastructure."
    },
    {
     "t": "housing",
     "s": "공공·민간·비영리가 모두 필요하다 — 정보 비대칭 같은 시장 실패가 민간이 혼자 들어가는 것을 자주 막는다. 은행이 CDFI 등 지역개발 단체와 손잡으면 그 단체들이 정보 비용을 낮추고 대출을 조율하며 위험을 나눠, 은행이 신용·투자·서비스를 넓히도록 돕는다.",
     "q": "there are market failures that often prevent the private sector from coming in on its own"
    },
    {
     "t": "housing",
     "s": "사례로 브루클린 City Point(슈퍼마켓·저렴 주택 120가구·소상공인 상가, 신시장세액공제로 민간 투자를 끌어냄)와 시러큐스의 혼합소득 주택 회전 대출기금(종잣돈 3천만 달러 + 민간 파트너 1억2천만 달러)을 들었다. 저소득주택세액공제는 지난 40년간 400만 가구 가까이를 짓거나 지키는 데 도움이 됐고, 이 사업들의 바탕은 지역재투자법(CRA)이다."
    }
   ]
  },
  {
   "id": "kashkari-20261118",
   "who": "kashkari",
   "date": "2026-11-18",
   "venue": "대담",
   "event": "FinRegLab AI 심포지엄 노변 대담(워싱턴, 진행 캐서린 램펠)",
   "src": "https://www.investing.com/news/economy-news/feds-kashkari-says-interest-rates-can-impact-tech-investment-5037179",
   "cert": "보도 확인",
   "head": "금리는 AI 투자에도 영향을 줄 수 있다 — 물가 쪽 책무는 못 맞춰, 기대인플레이션 고정이 관건",
   "chips": {
    "next": [
     "12월 선호 언급 못 찾음",
     "mid"
    ],
    "inflation": [
     "공급충격 반복·목표 못 맞춤",
     "up"
    ],
    "labor": [
     "회복력 유지",
     "mid"
    ],
    "ai": [
     "투자도 금리 영향 받음",
     "mid"
    ]
   },
   "points": [
    {
     "t": "ai",
     "s": "금리가 기술 투자 규모에 영향을 줄 수 있다고 봤다 — AI 인프라 투자가 거센 지금도 금리는 작동한다. 데이터센터 투자는 빠르게 늘지만 금리의 영향을 받고 있고, 금리가 지금보다 훨씬 낮았다면 이 분야 투자는 더 많았을 것이라고 했다."
    },
    {
     "t": "inflation",
     "s": "최근 높은 물가에는 잇따른 공급충격이 영향을 줬다고 봤다. 한편 연준이 책무 가운데 물가 쪽을 분명히 맞추지 못하고 있다고 했고, 기대인플레이션이 고정된 채로 있는 것이 중요하다고 강조했다."
    },
    {
     "t": "growth",
     "s": "미국 수요가 예상보다 다소 강하다고 했다. AI를 미국 경제의 주요 성장 동력으로 꼽았다."
    },
    {
     "t": "labor",
     "s": "노동시장은 회복력을 유지하고 있다고 평가했다."
    },
    {
     "t": "policy",
     "s": "시장은 연준이 위원들의 지금 전망보다 금리를 더 올려야 할 것으로 본다고 짚었다. 12월 회의에서 본인이 바라는 결정은 검색으로 본 보도에서 찾지 못했다."
    }
   ]
  },
  {
   "id": "warsh-20261116",
   "who": "warsh",
   "date": "2026-11-16",
   "venue": "연설",
   "event": "생산성·일자리 태스크포스 콘퍼런스 개회사(이사회·샌프란시스코 연은 공동 주최, 샌프란시스코)",
   "src": "https://www.federalreserve.gov/newsevents/speech/warsh20261116a.htm",
   "cert": "원문 확인",
   "head": "초지능이 성장률을 크게 높일 수도 — 생산성 돌파는 아직, 시나리오 셋은 예측 아님",
   "chips": {
    "next": [
     "정책 경로 언급 없음",
     "mid"
    ],
    "labor": [
     "대체 땐 실업 오를 수도",
     "mid"
    ],
    "ai": [
     "성장 높일 수도 — 예측 아님",
     "mid"
    ]
   },
   "points": [
    {
     "t": "ai",
     "s": "지금은 그가 성인이 된 뒤 가장 큰 전환기일 수 있다 — 범용기술 '초지능(SI)'의 등장. 내연기관·전기 같은 과거 범용기술은 뒤따르는 혁신을 낳았을 뿐 아이디어 생산 자체를 자동화하진 않았지만, SI는 혁신의 방법과 속도를 바꾸는 것으로 보인다. 아이디어 생산이 넓어지면 성장이 장기 평균보다 상당히 높게 이어질 수 있다.",
     "q": "If idea generation broadens, growth could be sustained at a level substantially higher than the long-run average"
    },
    {
     "t": "growth",
     "s": "지난 수십 년 획기적 아이디어는 찾기 어려워졌다 — 어떤 추정으로는 연구 투입이 1930년대보다 20배 넘게 늘었지만, 블룸·존스 등이 짚었듯 연구 생산성은 그보다 더 크게 떨어졌다. 인구 증가 둔화까지 겹쳐 금융위기 뒤 장기 정체론이 다시 나왔다. 생산성 증가율은 오르내렸고 최근 몇 분기는 꽤 강했지만 구조적으로 확실히 위로 올라서진 않았다.",
     "q": "But it hasn't yet broken out definitively and structurally to the upside"
    },
    {
     "t": "policy",
     "s": "이 기술이 넓게 쓰이면 경제에 큰 영향을 주고 앞으로 통화정책에도 중요한 함의가 있다. 연준의 몫은 옹호도 반대도 아니다. 큰 질문은 크기·범위·시점 — 총요소생산성이 오를지, 언제 시작해 언제 잦아들지, 다른 나라보다 빠를지 — 이고 시간이 지나며 훨씬 분명해질 것으로 본다.",
     "q": "with important implications for monetary policy down the road"
    },
    {
     "t": "policy",
     "s": "미래를 점치러 온 자리가 아니다 — 미래는 알 수 없고 아는 척해서도 안 되며, 할 일은 무엇이 오든 대비하는 비상 계획이다. 이사회 실무진이 양식화한 모형으로 시나리오를 짜기 시작했지만 예시일 뿐 예측이 아니고, 가장 맞을 결과를 포함해 다른 결과도 많이 그릴 수 있다. 이 개회사엔 다음 결정이나 금리 경로 언급이 없다.",
     "q": "These are illustrative scenarios, not forecasts"
    },
    {
     "t": "growth",
     "s": "시나리오 ① 생산성이 오르고 그 이득이 노동과 자본 소유자에게 넓게 나뉘면 실질 GDP 성장률이 장기 평균을 꾸준히 웃돌고 완전고용 가까이 머문다.",
     "q": "real GDP growth rises persistently above its long-run average, and the U.S. stays close to full employment"
    },
    {
     "t": "labor",
     "s": "시나리오 ② SI 주도 확장에서 일부 일자리가 기술에 보완되기보다 대체되면 노동시장이 크게 흔들릴 수 있다. 성장률은 여전히 장기 평균을 웃돌지만, 넓은 자동화와 노동시장 마찰이 겹쳐 실업률이 완전고용에 맞는 수준 위로 오를 수 있다.",
     "q": "widespread automation, combined with labor market frictions, could push the jobless rate above levels consistent with full employment"
    },
    {
     "t": "growth",
     "s": "시나리오 ③ SI가 실망을 줄 수도 있다 — 큰 자본 투자와 주가 상승 뒤 기대수익이 꺾이고 주식 가치가 떨어지면 경기가 둔화하고 실업이 더 뚜렷이 오른다. 경제는 결국 회복하지만 생산성 이득은 없다.",
     "q": "expected returns could turn down and equity valuations could fall, leading to an economic slowdown and a more notable rise in unemployment"
    },
    {
     "t": "ai",
     "s": "큰 기회가 위험 없이 오는 일은 드물고, 그 위험을 놓치면 크게 흔들리고 비용도 클 수 있다. SI는 나쁜 행위자에게도 힘을 주므로 핵심 기반시설과 그 취약성을 특히 살핀다 — 적대 세력이 미국 경제를 해치려 SI를 서둘러 쓸지도 질문으로 꼽았다.",
     "q": "SI empowers all, including bad actors"
    },
    {
     "t": "ai",
     "s": "그래도 사람을 과소평가해선 안 된다 — 기계는 판단·도덕·책임을 대신하지 못하고 결정은 사람이 해야 한다. '초지능 없이 초강대국일 수 있나'를 물으며, 예측은 하지 않지만 미국의 주도에 대해서는 중립이 아니라고 했다.",
     "q": "Humans are the designers and the builders, and humans must be the deciders"
    }
   ]
  },
  {
   "id": "barr-20261116",
   "who": "barr",
   "date": "2026-11-16",
   "venue": "연설",
   "event": "제7회 ACM 금융 AI 국제회의(이탈리아 밀라노)",
   "src": "https://www.federalreserve.gov/newsevents/speech/barr20261116a.htm",
   "cert": "원문 확인",
   "head": "AI 붐의 빚·부외 의무(잠재 최대치 3조달러 초과) — 직접 손실보다 급반전 땐 디레버리징 경계",
   "chips": {
    "ai": [
     "빚·부외 구조·쏠림 경계",
     "mid"
    ]
   },
   "points": [
    {
     "t": "growth",
     "s": "최근 몇 주 투자자들이 AI 투자 붐의 지속 가능성에 의문을 제기했다. 여러 시나리오 중 하나로, AI가 생산성을 크게 높여도 수익이 기대한 때·규모로 나오지 않아 크게 재평가되면 그 투자 손실이 투자 감소와 부의 손실에 따른 소비(어쩌면 기업 지출) 감소, 두 경로로 성장을 낮출 수 있다. 주식 위험 프리미엄은 역사적으로 낮지만 닷컴 붐 때만큼 낮지는 않다 — 연준은 시장 수준을 겨냥하지 않는다는 단서를 달았다.",
     "q": "The potential investment losses that could result from a large-scale repricing could lower output growth in two ways"
    },
    {
     "t": "finstab",
     "s": "AI 확장은 점점 빚으로 조달된다. 연설이 정리한 FSR 내용으로, 7대 AI 기업의 재무상태표 부채가 올해 크게 늘어 연말 전 8,000억달러를 넘을 전망이다. 1990년대 말~2000년대 초 통신 투자 순환을 떠올리게 하고, 하이퍼스케일러의 2020년 이후 누적 설비투자·부채 발행이 1995년에 시작된 통신업계 순환에 아직 못 미치지만 최근 설비투자 가속을 보면 곧 넘어설 수 있다.",
     "q": "expected to exceed $800 billion before year's end"
    },
    {
     "t": "finstab",
     "s": "장기계약·리스 약정·잔존가치 보증 같은 다른 의무는 더 빨리 늘었다. FSR은 이런 부외 부채의 잠재적 최대 명목가치를 3조달러 넘게 본다(할인 전 금액이라 재무상태표 숫자와 바로 견주긴 어렵다). 이런 복잡한 구조는 덜 정교한 투자자에게 불투명해, 심리가 바뀔 때 위험이 어디 있는지 몰라 매도가 커질 수 있으니 면밀히 봐야 한다.",
     "q": "that opacity can exacerbate selloffs when investor sentiment shifts"
    },
    {
     "t": "finstab",
     "s": "외부 조달에 기대는 신용 약한 업체는 최근 자본비용이 크게 올라 더 복잡한 자산담보 조달로 옮겨 간다. 하이퍼스케일러·GPU 업체는 LLM 연구소·클라우드 신생사에 누적 1,000억달러 넘게 지분 투자했고(순환 조달), 담보로 쓰인 데이터센터·GPU의 재판매 가치를 보증하기도 한다."
    },
    {
     "t": "finstab",
     "s": "붐을 받치는 빚이 아직 제한적이라 직접 손실은 덜 걱정한다. 다만 헤지펀드 레버리지와 전반적 위험선호가 꽤 높아 보여 급반전 땐 빠른 디레버리징과 자기강화적 투매가 생길 수 있다. 주식 전략 레버리지도 최근 몇 년 늘었고 일부를 대형 딜러의 프라임 브로커리지가 대므로 주식시장 변동기엔 거래상대방 익스포저가 늘 수 있다 — 대형 은행 자본이 방파제지만 AI에 큰 포지션을 쥔 상대방을 포함해 계속 봐야 한다.",
     "q": "a sharp reversal could lead to rapid deleveraging and, potentially, self-reinforcing fire sales"
    },
    {
     "t": "market",
     "s": "생성형 AI는 진입 장벽을 낮추고 참여자를 다양하게 하며 시장 감시를 도와 효율·건전성·기능을 높일 수 있다(대규모 자율 거래엔 아직 쓰이지 않는 것으로 안다). 그러나 비슷한 데이터로 학습한 비슷한 모델에 기대면 쏠림 위험이 있다 — 전략이 비슷해지고 뉴스 반응이 한꺼번에 움직일 수 있고, 같은 결함을 가질 수 있는 모델이 많으면 실패가 시스템 전체로 번질 수 있다.",
     "q": "If traders rely on a small set of similar AI models trained on similar data, they face the risk of herding behavior"
    },
    {
     "t": "finstab",
     "s": "올해 사고들은 AI 모델이 보안 경계를 지킬 규칙이 아니라 넘을 장애물로 다루는 위험을 보여 줬다. 방어 쪽도 AI로 훨씬 빨리 취약점을 고치지만, 최근 사고는 방어가 늘 불리할 수 있는지 묻게 한다 — 사이버 위험 관리는 금융안정에 계속 중요하고, 업계가 방어에서 협력하길 바란다.",
     "q": "Attackers only need to be right once, while defenders need to be right all the time"
    },
    {
     "t": "finstab",
     "s": "대형 은행들이 진위·동의를 확인할 수 없는 AI 에이전트가 고객 계좌에서 행동하려 한 사례를 보고한다 — 엄격한 인증·동의 확인 같은 안전장치가 필요하다. 스트레스 때 에이전트가 수익률 차·안정 신호를 즉시 감지해 자금을 자동으로 옮기면 예금 유출이 빨라져, 몇 분 만에 번지는 뱅크런을 가속할 수 있다.",
     "q": "potentially accelerating runs that unfold in minutes"
    },
    {
     "t": "ai",
     "s": "금융사가 생성형·에이전트 AI를 핵심 업무에 쓰려면 모델에 기댄 결정이 잘 통제되고 수치·법적으로 정확하며 설명·재현 가능해야 한다 — 개발자들은 아직 이 기준들에서 어느 정도 애를 먹는다. 담합·시장 조작·큰 변동성 위험을 막아야 하고, 투자 권유의 이해상충, 대출 심사의 편향·공정대출 위험도 짚었다.",
     "q": "well controlled, numerically and legally precise, explainable, and replicable"
    }
   ]
  },
  {
   "id": "hammack-20261116",
   "who": "hammack",
   "date": "2026-11-16",
   "venue": "인터뷰",
   "event": "블룸버그TV",
   "src": "https://www.investing.com/news/economy-news/feds-hammack-reiterates-case-for-slow-steady-rate-hikes-bloomberg-tv-5030761",
   "cert": "보도 확인",
   "head": "금융여건이 아직 성장을 못 누른다 — 작게·꾸준히 올리되 뒤처지면 크게",
   "chips": {
    "next": [
     "추가 인상(작은 폭)",
     "up"
    ],
    "pace": [
     "작게·꾸준히(뒤처지면 크게)",
     "mid"
    ],
    "level": [
     "아직 제약 부족",
     "up"
    ],
    "inflation": [
     "잘못된 방향·확산",
     "up"
    ],
    "labor": [
     "균형·역동성 부족",
     "mid"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "작은 폭으로 꾸준히 올려 정책의 제약을 경제에 되살리는 쪽을 선호한다. 물가 압력이 번지지만 아직 더 공격적인 경로로 바꿀 준비는 안 됐다.",
     "q": "I like moving in smaller increments"
    },
    {
     "t": "policy",
     "s": "예측할 수 있는 조정이 가계·기업의 계획을 돕고, 점진적인 길은 경제 활동을 불필요하게 흔들지 않고 제약을 되살린다는 설명이다."
    },
    {
     "t": "policy",
     "s": "뒤처져서 제약을 더 넣어야 한다면 큰 폭으로도 얼마든지 움직일 수 있다. FOMC 회의에는 늘 열린 마음으로 들어간다고도 했다.",
     "q": "If we get behind the curve and we need to put more restriction in, we absolutely can move in those larger increments"
    },
    {
     "t": "policy",
     "s": "인플레이션 심리가 자리 잡으면 더 큰 폭으로, 그렇지 않을 때보다 더 높은 곳까지 올려야 할 수 있다. 그런 경우라면 지난주 월러 이사가 꺼낸 더 큰 폭 인상 제안에도 열려 있다고 보도됐다.",
     "q": "to a higher destination than we might otherwise need to"
    },
    {
     "t": "rates",
     "s": "금융여건이 아직 성장을 누르지 못하고, 그 제약 부족이 경제 전반에서 보인다 — 시장 차입비용이 더 올라야 한다. 경제는 제약을 더 견딜 수 있지만 연준이 어디까지 가야 할지는 분명하지 않다."
    },
    {
     "t": "inflation",
     "s": "물가가 잘못된 방향으로 가고 압력이 넓게 번지는 것으로 보인다."
    },
    {
     "t": "inflation",
     "s": "기업들이 높아진 비용을 소비자에게 점점 더 넘기고, 가격을 올리는 쪽으로 기울고 있다."
    },
    {
     "t": "labor",
     "s": "노동시장은 대체로 균형이지만 역동적이지 않다. 문제는 물가 쪽이라 두 책무 사이의 긴장은 크지 않다고 봤다."
    }
   ]
  },
  {
   "id": "waller-20261110",
   "who": "waller",
   "date": "2026-11-10",
   "venue": "연설",
   "event": "영란은행 워처스 콘퍼런스(런던)",
   "src": "https://www.federalreserve.gov/newsevents/speech/waller20261110a.htm",
   "cert": "원문 확인",
   "head": "12월 25bp 인상 쪽 — 10월 근원 CPI가 0.3% 이상이면 50bp도 검토",
   "chips": {
    "next": [
     "인상 25bp(50 검토)",
     "up"
    ],
    "pace": [
     "시사한 경로를 제때",
     "up"
    ],
    "level": [
     "실질금리 올려야",
     "up"
    ],
    "inflation": [
     "광범위 확산",
     "up"
    ],
    "labor": [
     "최대고용 근처",
     "mid"
    ],
    "ai": [
     "물가 압력 오래 감",
     "up"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "10월 물가가 9월보다 나아져도 12월 25bp 인상 지지 쪽으로 기운다. 2%로 가는 경로로 되돌리려면 추가 긴축은 이를수록 좋다.",
     "q": "leaning toward supporting an increase in our policy rate of 25 basis points"
    },
    {
     "t": "policy",
     "s": "10월 근원 CPI가 앞선 두 달처럼 0.3% 안팎이거나 그 이상이면 12월에 50bp를 검토해야 한다 — 25bp에 그치면 신뢰가 흔들린다.",
     "q": "Hiking only 25 basis points would put our credibility at risk"
    },
    {
     "t": "policy",
     "s": "10월 동결에 찬성한 까닭: 긴축을 소통한 것만으로 시장이 인상을 일부 반영했다. 연속 인상까지는 아니어도 시사한 경로는 합리적인 기간 안에 실행해야 한다 — 미루면 시장금리가 먼저 내려 바라지 않는 완화가 된다."
    },
    {
     "t": "rates",
     "s": "긴축 정도를 지키려면 실질금리가 올라야 하고, 최소한 앞서 한 예방적 인하 3번은 되돌려야 한다. 다만 150~200bp씩 올릴 일은 아니다."
    },
    {
     "t": "inflation",
     "s": "9월 PCE 전월비 0.5%·전년비 3.7%, 근원 0.3%·3.1% — 나쁜 숫자. 근원 상품과 주거 뺀 시장기반 서비스가 높고, 근원 PCE 서비스 항목의 70% 넘게가 전년비 3%를 웃돈다.",
     "q": "September's inflation data were bad"
    },
    {
     "t": "inflation",
     "s": "호르무즈 해협 통과 보험·환적 비용이 유가를 배럴당 20~30달러 높인 것으로 추정한다. 정제능력이 모자라 경유값도 쉽게 내리지 않을 것."
    },
    {
     "t": "ai",
     "s": "연준 연구로는 AI 하이테크 상품과 에너지의 가격 압력이 금방 사라지지 않는다. 팬데믹 뒤 근원 물가가 에너지 충격에 더 민감해져 유가가 높게 머물면 압력이 2027년까지 갈 수 있다."
    },
    {
     "t": "labor",
     "s": "10월 실업률 4.1%, 비농업 고용 +16.5만명, 6·12개월 평균 8만명 안팎 — 수급은 대체로 균형이고 최대고용에 가깝다."
    },
    {
     "t": "labor",
     "s": "적게 뽑고 적게 내보내는 환경이라 역동성은 떨어졌을 수 있다. 장기실업자와 신규 진입자의 실업 비중이 올라, 헤드라인 실업률만큼 건강하지 않을 수도 있다.",
     "q": "low hire, low fire"
    },
    {
     "t": "growth",
     "s": "3분기 실질GDP +3.4% — 소비와 AI 하이테크 설비투자가 끌었다. 이번 분기는 소비가 소득·자산에 맞는 수준으로 둔화해 조금 약해지겠지만 견조할 것."
    }
   ]
  },
  {
   "id": "logan-20261110",
   "who": "logan",
   "date": "2026-11-10",
   "venue": "연설",
   "event": "댈러스·캔자스시티 연은 에너지 콘퍼런스(휴스턴)",
   "src": "https://www.dallasfed.org/news/speeches/logan/2026/lkl261110",
   "cert": "보도 확인",
   "head": "25bp 인상이 최소 두 번 더 — 이번 겨울엔 올가을보다 빠를 수도",
   "chips": {
    "next": [
     "추가 인상 2회 이상",
     "up"
    ],
    "pace": [
     "겨울엔 더 빠르게",
     "up"
    ],
    "level": [
     "다소 긴축보다 50bp+ 낮음",
     "up"
    ],
    "inflation": [
     "추세 고착 우려",
     "up"
    ],
    "labor": [
     "최대고용·조금 타이트",
     "mid"
    ],
    "ai": [
     "데이터센터가 성장 견인",
     "mid"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "지금 전망이면 25bp 인상이 최소 두 번 더 필요하다. 속도는 단기 경제·금융 여건에 달렸고, 이번 겨울엔 올가을보다 빨리 움직일 수 있다.",
     "q": "It may be possible to move more rapidly this winter"
    },
    {
     "t": "policy",
     "s": "10월 동결은 시장 변동성이 커져 속도를 조절한 것일 뿐, 가려는 곳은 그대로다.",
     "q": "Skipping one meeting does not change the monetary policy destination"
    },
    {
     "t": "rates",
     "s": "지금 기준금리는 '다소 긴축적'인 수준보다 최소 50bp 낮다고 본다. 두 번 올린 뒤에는 멈추고 추가 조치를 점검하는 게 합리적이다."
    },
    {
     "t": "rates",
     "s": "중립 실질금리 추정치는 1.00~1.85%인데, 기대인플레이션 3.1%를 뺀 실질 기준금리는 0.78%로 하단보다 낮다 — 완화적인 정책이 물가 압력을 키운다. 장기금리 상승은 성장·중립금리 기대를 반영한 것이지 장기 구간만의 따로 노는 요인이 아니다."
    },
    {
     "t": "inflation",
     "s": "물가가 6년 가까이 목표를 웃돌았다. 10월 CPI가 예상보다 높아 10월 PCE가 걱정이고, 주거·운송 뺀 근원 서비스가 9월 3.2%로 목표에 맞는 속도보다 0.8%p 높다 — 넓은 추세가 이어질 가능성이 크다."
    },
    {
     "t": "inflation",
     "s": "목표 초과가 길어질수록 인플레이션 인식이 행동에 굳는다. 2026년 물가를 메우려는 2027년 임금 인상이 번지면 경기를 더 식혀야 한다.",
     "q": "baked into behavior"
    },
    {
     "t": "labor",
     "s": "실업률은 4%를 조금 넘는 사실상 최대고용. 균형이고 오히려 조금씩 타이트해진다 — 역동성은 낮지만 구인과 자발적 이직이 늘어 나아지는 조짐도 있다."
    },
    {
     "t": "growth",
     "s": "3분기 실질GDP +3.4%, 주간경제지수도 3% 안팎 성장과 맞는다. 부유층 소비와 데이터센터 장비투자(3분기 전년비 14%)가 받친다."
    }
   ]
  },
  {
   "id": "schmid-20261110",
   "who": "schmid",
   "date": "2026-11-10",
   "venue": "대담",
   "event": "댈러스·캔자스시티 연은 에너지 콘퍼런스 오찬 대담(휴스턴)",
   "src": "https://www.investing.com/news/economy-news/feds-schmid-calls-for-tighter-policy-to-control-inflation-5016588",
   "cert": "보도 확인",
   "head": "지금 금리는 꽤 완화적 — 수요가 강해 조정을 망설일 이유가 없다",
   "chips": {
    "next": [
     "조정 망설임 없음",
     "up"
    ],
    "level": [
     "꽤 완화적",
     "up"
    ],
    "inflation": [
     "에너지 밑 추세도 우려",
     "up"
    ],
    "labor": [
     "채용 꽤 견조",
     "mid"
    ]
   },
   "points": [
    {
     "t": "rates",
     "s": "작년에도 금리가 긴축적이라고 보지 않았고 지금은 꽤 완화적이다. 주택은 흥미로운 흐름이지만 다른 곳에선 정책이 수요를 누른다는 증거를 못 찾겠다.",
     "q": "I didn't think our rate was restrictive last year, and I believe today it's fairly accommodative"
    },
    {
     "t": "policy",
     "s": "수요가 강해 기준금리 조정을 망설일 이유가 없다."
    },
    {
     "t": "inflation",
     "s": "물가가 최우선 관심사다. 에너지 문제 밑에서도 걱정스러운 가격 흐름이 보이고, 정책이 물가 추세에 가장 크게 영향을 줄 수 있는 곳을 본다.",
     "q": "some concerning trends in prices, underneath the whole energy story"
    },
    {
     "t": "labor",
     "s": "요즘 채용은 꽤 견조하다. 12월 회의 전까지 볼 지표가 많다.",
     "q": "hiring is pretty robust lately"
    }
   ]
  },
  {
   "id": "bowman-20261110",
   "who": "bowman",
   "date": "2026-11-10",
   "venue": "연설",
   "event": "C. Peter McColough 국제경제 강연(뉴욕)",
   "src": "https://www.federalreserve.gov/newsevents/speech/bowman20261110a.htm",
   "cert": "원문 확인",
   "head": "아직 할 일이 남았다 — 다만 추가 긴축의 이익을 금리 민감 부문의 비용과 신중히 견줘야",
   "chips": {
    "next": [
     "정해진 경로 없음",
     "mid"
    ],
    "pace": [
     "단계적·조정 가능",
     "mid"
    ],
    "level": [
     "금융여건 다소 긴축",
     "mid"
    ],
    "inflation": [
     "확산 조짐·대부분 상대가격",
     "mid"
    ],
    "labor": [
     "타이트하지 않음",
     "down"
    ],
    "ai": [
     "초과 물가의 약 1/4",
     "up"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "물가 압력이 이어지고 노동시장이 단단해지는 신호가 있어 2% 근처로 되돌리려면 할 일이 남았다. 다만 금융여건이 조금 긴축돼 추가 긴축의 이익을 금리 민감 부문의 비용과 신중히 견줘야 한다.",
     "q": "the benefit of additional policy tightening has to be carefully weighed against its costs"
    },
    {
     "t": "policy",
     "s": "속도와 시점을 함께 봐야 한다 — 작년의 점진적 인하 → 동결 → 인상 재개처럼 단계적으로 조정할 수 있다. 정해진 경로는 없다."
    },
    {
     "t": "policy",
     "s": "10월 동결에 찬성한 것은 최근 인상이 기조적 흐름에 주는 영향을 더 본 뒤 바꾸려고였다."
    },
    {
     "t": "inflation",
     "s": "물가 진전은 2년가량 멈췄고 최근 확산 조짐이 있다. 10월 근원 PCE는 3.3%로 올랐을 것으로 추정하고, 관세·에너지·AI가 목표 초과분의 각각 약 1/4이다."
    },
    {
     "t": "inflation",
     "s": "충격 대부분이 특정 부문의 상대가격 충격이라 사라지면 내년 근원 PCE는 2%에 가까워질 것. 다만 AI·중동 위험이 줄어야 확신할 수 있고, 장기 기대인플레이션은 잘 고정돼 있지만 판단을 좌우할 지표는 아니다."
    },
    {
     "t": "inflation",
     "s": "일시적인 에너지발 물가는 가능하면 넘겨 보되, 넓은 가격이나 기대로 번지는지는 경계한다.",
     "q": "look through temporary energy-driven inflation, when possible"
    },
    {
     "t": "labor",
     "s": "10월 실업률 4.1%는 자연실업률 근처, 고용은 월평균 약 8만명 증가. 적게 뽑고 적게 내보내는 환경인데도 임금 상승률이 3.1%로 둔화 — 타이트한 수준은 아니다."
    },
    {
     "t": "growth",
     "s": "3분기 실질GDP는 3% 넘게 성장했을 것. AI 설비투자와 소비가 끌었고, 모기지 금리 상승으로 주택은 더 위축됐다."
    },
    {
     "t": "finstab",
     "s": "주가 하락·시장금리 상승·달러 강세로 금융여건이 다소 긴축됐다. AI 관련 부채가 올해 8,000억달러를 넘을 전망 — AI 수익이 기대에 못 미치면 주가 급락과 조달비용 상승이 나타날 수 있다."
    }
   ]
  },
  {
   "id": "paulson-20261110",
   "who": "paulson",
   "date": "2026-11-10",
   "venue": "연설",
   "event": "제81회 연례 현장회의(펜실베이니아 콘쇼호켄)",
   "src": "https://www.philadelphiafed.org/the-economy/monetary-policy/261110-81st-annual-field-meeting-capstone-speech",
   "cert": "보도 확인",
   "head": "점진적 추가 긴축이 적절 — 10월 동결은 방향이 아니라 속도의 문제",
   "chips": {
    "next": [
     "점진적 추가 긴축",
     "up"
    ],
    "pace": [
     "점진(악화 시 더 빠르게)",
     "mid"
    ],
    "level": [
     "다소 긴축적이어야",
     "up"
    ],
    "inflation": [
     "기조 2.5~3.0%에 고착",
     "up"
    ],
    "labor": [
     "강해짐",
     "mid"
    ],
    "ai": [
     "물가 세 요인 중 하나",
     "up"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "물가를 2%로 되돌리려면 정책이 '다소 긴축적'이어야 한다. 9월 인상·10월 동결에 모두 찬성 — 한 번 쉰 건 방향이 아니라 속도 문제이고 할 일이 더 남았다.",
     "q": "Skipping a meeting is a matter of pace, not direction"
    },
    {
     "t": "policy",
     "s": "여건이 허락하면 점진적 긴축을 선호한다. 가계·기업·금융기관이 높은 금리에 적응할 시간을 주고 지표·현장 의견을 보며 다음 걸음을 정할 수 있어서다. 당분간은 추가 점진 긴축이 적절하지만 정확한 경로는 여건에 달렸다.",
     "q": "further gradual tightening seems appropriate"
    },
    {
     "t": "policy",
     "s": "기대인플레이션·임금 압력·기조 물가가 오르면 더 빨리 움직이겠다. 지금은 장기 기대가 고정돼 있고 임금 압력도 제한적이며, 시장이 추가 긴축을 예상하고 있어 점진적 접근이 뒤처진 대응은 아니다.",
     "q": "I would want to act more quickly"
    },
    {
     "t": "inflation",
     "s": "물가는 5년 반 동안 목표 위에 있었다. 9월 PCE 전년비 3.6%, 10월 CPI도 압력이 여전함을 보여 준다. 관세·에너지·AI 투자가 세 요인 — 관세 효과는 2월 정점 뒤 약해지지만 에너지 공급과 AI 수요는 가늠이 어렵다."
    },
    {
     "t": "inflation",
     "s": "기조 물가가 2.5~3.0%에 머물러 저절로 사라질 문제가 아니다. 임금이 압력을 더하지 않고 시장도 2% 복귀를 보는 점은 긍정적이지만 위험은 여전히 높다.",
     "q": "elevated inflation isn't just about factors that will go away on their own"
    },
    {
     "t": "labor",
     "s": "생계비 부담에 대응해 더 큰 임금 인상을 검토하는 기업이 일부 있다 — 넓지는 않지만 번지면 2% 복귀가 어려워져 지켜본다."
    },
    {
     "t": "labor",
     "s": "10월 실업률 4.1%, 올해 월평균 고용 +8.6만명(작년 1만명)으로 업종도 넓어졌다. 수년째 최대고용 근처이고 2026년 노동시장은 강해졌다."
    },
    {
     "t": "growth",
     "s": "올해 성장률은 평균 2.7%로 작년 12월 FOMC 중간값(2.3%)을 웃돈다. 관할 제조업체 100%가 내년 설비투자 확대·유지를 계획(1968년 이후 20개월뿐)할 만큼 AI 밖도 견조하다. 실질소비 2.8%가 실질소득 1.3%를 웃돈 건 차입·저축 인출·투자이익 지출 때문일 것."
    },
    {
     "t": "growth",
     "s": "최근 주가·유가 변동이 컸고 소비 강세 일부가 주가와 이어져 있어 생각보다 오래 못 갈 수 있다 — 그러면 노동시장에도 번질 수 있다."
    }
   ]
  },
  {
   "id": "goolsbee-20261110",
   "who": "goolsbee",
   "date": "2026-11-10",
   "venue": "인터뷰",
   "event": "PBS 뉴스아워(CPI 발표일)",
   "src": "https://www.pbs.org/newshour/show/u-s-inflation-report-highlights-strain-of-rising-food-energy-and-housing-costs",
   "cert": "보도 확인",
   "head": "10월 CPI는 '거의 우려스러운' 수준 — 진짜 물가 문제가 생겼고 대응해야",
   "chips": {
    "next": [
     "모든 선택지(큰 폭 포함)",
     "up"
    ],
    "inflation": [
     "잘못된 방향·서비스·의료",
     "up"
    ],
    "labor": [
     "꾸준·안정",
     "mid"
    ],
    "ai": [
     "수요 측 압력",
     "up"
    ]
   },
   "points": [
    {
     "t": "inflation",
     "s": "10월 CPI는 또 한 번 실망스러운, 거의 우려스러운 지표다. 진전을 기대했지만 그간 쌓인 물가 문제가 현실이 됐고 대응해야 한다.",
     "q": "We have got a real inflation issue on our hands that has been developing, and we're going to have to deal with that"
    },
    {
     "t": "policy",
     "s": "12월 큰 폭 인상은 그때 정할 일 — 모든 선택지가 열려 있고 물가를 목표로 되돌려야 하는데 지금은 잘못된 방향이다.",
     "q": "everything is always on the table, and we must get inflation back down to target, and it's going the wrong way at this point"
    },
    {
     "t": "inflation",
     "s": "가장 걱정스러운 건 의료를 포함한 서비스 물가다. 유가나 관세 탓만은 아니다 — 관세의 상품 가격 효과는 끝났어야 하는데 아직 남아 있다."
    },
    {
     "t": "ai",
     "s": "AI 데이터센터 구축이 물가에 수요 측 압력을 더했고, 과열이 서비스 등 다른 품목으로 번질까 걱정이다. 물가가 기대에 반영되면 큰 문제다."
    },
    {
     "t": "inflation",
     "s": "관세 같은 요인이 바라던 대로 시간이 지나며 사그라드는 모습을 보지 못했다. 소비자·기업이 높은 물가를 예상하기 시작하면 큰 걱정 — 그때는 물가를 식히는 일이 훨씬 고통스러워진다.",
     "q": "much more painful"
    },
    {
     "t": "policy",
     "s": "다만 다음 회의의 손을 묶을 만큼 구체적인 입장을 미리 밝히는 건 좋아하지 않는다."
    },
    {
     "t": "labor",
     "s": "노동시장은 꾸준하고 안정적이다."
    }
   ]
  },
  {
   "id": "hammack-20261112",
   "who": "hammack",
   "date": "2026-11-12",
   "venue": "대담",
   "event": "오하이오주립대 피셔 경영대 학생 대담",
   "src": "https://www.investing.com/news/economy-news/feds-hammack-signals-support-for-gradual-ratehike-path-5022530",
   "cert": "보도 확인",
   "head": "긴축적인 기조로 옮겨야 — 작게, 자주, 꾸준히",
   "chips": {
    "next": [
     "추가 인상",
     "up"
    ],
    "pace": [
     "작게·자주",
     "mid"
    ],
    "level": [
     "긴축적으로 옮겨야",
     "up"
    ],
    "inflation": [
     "잘못된 방향·확산",
     "up"
    ],
    "labor": [
     "목표 부합·역동성 부족",
     "mid"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "물가를 2%로 되돌리려면 긴축적인 기조로 옮겨야 한다 — 그렇지 않으면 인플레이션 심리가 자리 잡을 수 있다.",
     "q": "we need to move to a restrictive stance of policy"
    },
    {
     "t": "policy",
     "s": "더 작고 잦은 폭으로 꾸준히 올리는 쪽을 선호한다. 가계·기업이 대응하기 쉽고, 급격한 조정보다 경제에 덜 파괴적이어서다.",
     "q": "less disruptive to the overall economy"
    },
    {
     "t": "policy",
     "s": "지금 연준이 뒤처져 있지는 않다. 뒤처지면 더 공격적인 대응을 생각할 것.",
     "q": "if we get behind the curve, then that might be something that we need to consider"
    },
    {
     "t": "policy",
     "s": "자신의 전망은 약속도 포워드가이던스도 아닌 조건부 기대이고, 회의마다 열린 마음으로 간다."
    },
    {
     "t": "inflation",
     "s": "연준은 수년째 물가 목표를 못 맞추고 있다. 최근 지표는 물가가 잘못된 방향으로 가고 압력이 번진다는 신호이고, 실질적인 수요 압력도 작용한다.",
     "q": "moving in the wrong direction"
    },
    {
     "t": "labor",
     "s": "고용은 목표에 맞지만 역동성이 모자라 건강하다고 보긴 어렵다."
    }
   ]
  },
  {
   "id": "barr-20261112",
   "who": "barr",
   "date": "2026-11-12",
   "venue": "연설",
   "event": "예일대 — 미국의 불평등과 AI의 미래",
   "src": "https://www.federalreserve.gov/newsevents/speech/barr20261112a.htm",
   "cert": "원문 확인",
   "head": "AI는 지금 물가·투자로 나타나는 중 — 노동 대체는 아직 적지만 젊은 층부터 조짐",
   "chips": {
    "labor": [
     "단기 혼란 대비",
     "down"
    ],
    "inflation": [
     "AI가 물가에 반영",
     "up"
    ],
    "ai": [
     "노동 대체 조짐(젊은 층)",
     "mid"
    ]
   },
   "points": [
    {
     "t": "ai",
     "s": "지금 AI의 영향은 주로 물가에 나타나고, 투자와 GDP를 끌어올리고 있다."
    },
    {
     "t": "labor",
     "s": "AI로 노동자가 대체된 경우는 아직 비교적 적다 — 일부의 생산성을 높이고 새 직종도 생긴다. 다만 경험이 적은 젊은 노동자를 중심으로 대체 조짐이 있는 것도 사실이다.",
     "q": "relatively little displacement of workers by AI"
    },
    {
     "t": "labor",
     "s": "노동시장의 심각한 단기 혼란에 대비해야 한다 — 변화가 빠를수록 적응이 어렵고 혼란이 커진다.",
     "q": "serious short-term disruptions in the labor market"
    },
    {
     "t": "ai",
     "s": "국민소득 중 근로소득 비중이 2026년 2분기 52.8%로 사상 최저다. AI가 자본에 수익을 몰아주는 혁신이라면 근로소득 몫이 더 줄고 불평등이 커질 수 있다."
    }
   ]
  },
  {
   "id": "goolsbee-20261112",
   "who": "goolsbee",
   "date": "2026-11-12",
   "venue": "인터뷰",
   "event": "야후 파이낸스 인베스트 2026(화상 대담)",
   "src": "https://finance.yahoo.com/economy/policy/article/chicago-feds-austan-goolsbee-were-at-a-precarious-moment-with-inflation-183700943.html",
   "cert": "보도 확인",
   "head": "물가가 여러 면에서 잘못된 방향 — 불안한 국면, 더 나빠지기 전에 막아야",
   "chips": {
    "next": [
     "선택지 열어 둠",
     "up"
    ],
    "inflation": [
     "서비스·의료 끈질김",
     "up"
    ],
    "ai": [
     "일종의 경기부양",
     "up"
    ]
   },
   "points": [
    {
     "t": "inflation",
     "s": "물가가 여러 면에서 잘못된 방향이다. 서비스·의료처럼 끈질긴 품목의 오름세가 강하고, 뜨거운 10월은 일회성 요인 탓이 아니다.",
     "q": "more disturbingly persistent categories like services, health care"
    },
    {
     "t": "inflation",
     "s": "관세가 지나가고 유가가 내리면 크게 낮아질 줄 알았지만 그렇지 않아 지금은 불안한 국면 — 어느 중앙은행에나 역사적으로 어려운 영역으로 조금씩 들어가고 있다.",
     "q": "So we're at a precarious moment"
    },
    {
     "t": "policy",
     "s": "더 나빠지기 전에 막는 게 낫다. 지표와 그에 따른 대응엔 냉정해야 하고, 결정을 미리 단정하지 않되 선택지를 논의할 여지는 충분하다.",
     "q": "We'd do well to try to prevent it from getting worse"
    },
    {
     "t": "ai",
     "s": "AI 투자는 일종의 경기 부양책이다 — 경제 전반의 과열 신호를 살펴야 한다."
    }
   ]
  },
  {
   "id": "daly-20261112",
   "who": "daly",
   "date": "2026-11-12",
   "venue": "연설·대담",
   "event": "스탠퍼드 SIEPR 가을 정책 포럼 — AI 시대의 경제정책",
   "src": "https://finance.yahoo.com/economy/policy/articles/fed-time-calibrate-rate-hikes-205839359.html",
   "cert": "보도 확인",
   "head": "추가 긴축이 필요할 것이라는 쪽 — 폭과 시기는 지표를 더 보고",
   "chips": {
    "next": [
     "추가 긴축 쪽",
     "up"
    ],
    "pace": [
     "서두르지 않음",
     "mid"
    ],
    "level": [
     "채권금리 상승 환영",
     "mid"
    ],
    "inflation": [
     "서비스로 번짐",
     "up"
    ],
    "labor": [
     "안정",
     "mid"
    ],
    "ai": [
     "주된 원인 아님",
     "mid"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "추가 긴축이 필요할 것이라는 쪽으로 기운다. 9월 인상에도 만족한다. 다만 정확한 폭과 시기는 지금 정할 필요가 없고, 여러 분기에 걸쳐 지표를 더 볼 수 있다.",
     "q": "My bias is that further tightening will be needed"
    },
    {
     "t": "rates",
     "s": "채권금리 상승은 매우 반갑다 — 금융여건이 긴축돼 정교하게 조정할 시간이 생긴다. 시장이 물가 하락을 돕지만 연준의 일은 끝나지 않았다.",
     "q": "gives us a little more time to make really calibrated decisions"
    },
    {
     "t": "inflation",
     "s": "노동시장은 안정되고 성장도 양호하지만 물가 문제는 분명하다. 압력이 에너지·상품에서 서비스로 번지고, 서비스 물가는 한번 오르면 잘 안 내린다. 충격이 쌓일 수 있어 안주할 수 없다."
    },
    {
     "t": "ai",
     "s": "AI발 물가 압력은 분명하지만 직접 기여는 제한적이다 — 물가 문제의 주된 원인은 AI가 아니고, 노동시장 영향도 제한적이다.",
     "q": "AI is not doing most of the driving"
    },
    {
     "t": "ai",
     "s": "물가 문제가 크다고 생산성 향상이 물가를 낮출 가능성을 무시하면 안 된다 — 앞으로 1~3년 생산성 개선이 나타날 수 있다."
    },
    {
     "t": "growth",
     "s": "AI 주가 재조정은 관심이 식은 게 아니어서 성장에 위험이 되지 않을 것. 성장률을 낮추면서도 양호한 성장·안정된 노동시장·더 낮은 물가가 가능하다.",
     "q": "you can slow the growth rate and still have a good economy growing"
    }
   ]
  },
  {
   "id": "williams-20261106",
   "who": "williams",
   "date": "2026-11-06",
   "date_note": "추정 — 11-06 프랑크푸르트 발언 보도와 가장 가깝다",
   "venue": "발언",
   "event": "날짜·자리 확인 중",
   "src": "",
   "cert": "출처 미확인",
   "head": "통화정책을 맞추려면 할 일이 남았다 — 시간을 두고 조치",
   "chips": {
    "next": [
     "추가 조치(시간 두고)",
     "up"
    ],
    "pace": [
     "시간을 두고",
     "mid"
    ],
    "inflation": [
     "너무 높고 끈질김",
     "up"
    ],
    "labor": [
     "강해지는 중",
     "mid"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "정책을 적절한 수준에 맞추려면 할 일이 남았다. 물가를 제때, 지속적으로 2%로 되돌리려면 시간을 두고 조치해야 한다."
    },
    {
     "t": "inflation",
     "s": "물가는 너무 높고 끈질기다. 정책의 목표는 물가 수준이 아니라 상승률 — 수준 자체를 끌어내리려 하면 경제 여건이 나빠질 수 있다."
    },
    {
     "t": "growth",
     "s": "경제는 회복력이 있고 성장이 견조하다. 노동시장은 계속 강해지지만 과열은 아니다."
    }
   ]
  },
  {
   "id": "bailey-20261113",
   "who": "bailey",
   "date": "2026-11-13",
   "venue": "연설",
   "event": "금융안정위원회(FSB) 의장 기조연설 — IOSCO 25주년 콘퍼런스",
   "src": "https://www.fsb.org/2026/11/financial-stability-in-a-rapidly-changing-world/",
   "cert": "보도 확인",
   "head": "보이는 스트레스가 없다고 위험이 없는 건 아니다 — 사모신용·스테이블코인을 규모보다 연결로 봐야",
   "chips": {},
   "points": [
    {
     "t": "finstab",
     "s": "눈에 보이는 스트레스가 없다는 것과 위험이 없다는 것은 다르다. 사모신용과 스테이블코인은 흔한 규모 지표가 말하는 것보다 빨리 금융안정 위험이 될 수 있다.",
     "q": "The absence of visible stress should not be mistaken for the absence of risk"
    },
    {
     "t": "finstab",
     "s": "사모신용은 거래가 드물고 가치평가가 잘 안 드러나며 계약 조건도 제각각이다. 은행·보험·펀드의 공통 노출이 충격을 키울 수 있어 핵심은 상호연계성 — 혼자서는 시스템을 흔들지 못해도 도미노 하나가 될 수 있다."
    },
    {
     "t": "finstab",
     "s": "스테이블코인은 시가총액보다, 신뢰를 잃을 때 대규모 환매가 얼마나 빨리 일어날 수 있는지가 문제다."
    },
    {
     "t": "market",
     "s": "헤지펀드의 시장 참여 자체는 문제가 아니고 평소엔 유동성을 공급한다. 고레버리지 포지션이 한꺼번에 청산될 때 취약성이 드러난다."
    },
    {
     "t": "market",
     "s": "2025년 4월 관세 발표 뒤 미 장기 국채금리 급등은 전례 없고 해석하기 어려웠다 — 당국은 기존 지표에 경고가 켜지기 전에 그럴듯한 확산 경로를 미리 점검해야 한다.",
     "q": "unprecedented and difficult to interpret"
    }
   ]
  },
  {
   "id": "goolsbee-20261113",
   "who": "goolsbee",
   "date": "2026-11-13",
   "venue": "인터뷰",
   "event": "CNBC 스쿼크박스",
   "src": "https://www.cnbc.com/2026/11/13/chicago-feds-goolsbee-says-central-bank-has-definitely-got-work-to-do-on-inflation.html",
   "cert": "보도 확인",
   "head": "지금은 2%로 가는 경로에 있지 않다 — 신뢰를 지키려면 할 일이 남았다",
   "chips": {
    "next": [
     "지표 나쁘면 더 공격적",
     "up"
    ],
    "inflation": [
     "예상보다 끈질김",
     "up"
    ],
    "labor": [
     "임금은 후행지표",
     "mid"
    ],
    "ai": [
     "데이터센터도 물가 요인",
     "up"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "지금은 물가가 2%로 돌아가는 경로에 있지 않아 대응이 필요한 때다. 연준이 신뢰를 지키려면 분명히 할 일이 남았다.",
     "q": "Are we on a path back to 2%? My feeling is right now we are not and we got to deal with that"
    },
    {
     "t": "policy",
     "s": "지표가 물가 악화를 가리킬수록 더 공격적으로 대응할 것 — 수요가 과열되지 않게 해야 한다."
    },
    {
     "t": "inflation",
     "s": "물가는 예상보다 훨씬 끈질기고 에너지와 무관한 품목으로 번진다. 서비스·의료의 추세는 곧 바뀔 것 같지 않고, 수요가 과열되면 일시적이라 볼 수 없다. 데이터센터 구축도 물가 요인이다."
    },
    {
     "t": "inflation",
     "s": "몇 달째 불안 신호가 이어졌고 물가가 다시 오른다. 처음 공급 충격에서 예상한 것보다 훨씬 끈질기고, 이제는 고전적인 수요 과열의 모습 — 수요 과열은 무슨 수를 써서라도 막는 게 상식이다.",
     "q": "We have had signs of trouble now for several months in a row"
    },
    {
     "t": "inflation",
     "s": "유가가 빨리 떨어져도 정제설비 부족은 여전히 문제로 남는다."
    },
    {
     "t": "rates",
     "s": "보도 요약으로는 기준금리가 언젠가는 지금보다 훨씬 낮아질 것이라고도 했다 — 원래 문장은 찾지 못했다."
    },
    {
     "t": "labor",
     "s": "임금은 후행지표라 노동시장이 물가에 주는 영향을 읽을 때 신중해야 한다."
    }
   ]
  },
  {
   "id": "logan-20261113",
   "who": "logan",
   "date": "2026-11-13",
   "venue": "연설",
   "event": "댈러스 연은 은행 자금조달 콘퍼런스 개회사",
   "src": "https://www.dallasfed.org/news/speeches/logan/2026/lkl261113",
   "cert": "보도 확인",
   "head": "정책은 덜이 아니라 더 긴축적으로 — 국채시장 지원은 경기 부양과 섞지 말아야",
   "chips": {
    "next": [
     "더 긴축적으로",
     "up"
    ],
    "level": [
     "더 긴축 필요",
     "up"
    ],
    "inflation": [
     "높고 가파름",
     "up"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "물가가 지나치게 높고 추세도 가팔라 정책을 덜이 아니라 더 긴축적으로 조정해야 한다."
    },
    {
     "t": "market",
     "s": "지금 국채시장 기능에 장애가 생기면 FOMC는 같은 자산매입으로 부양과 시장 안정을 동시에 노릴 여유가 없다 — 수단 하나로 두 목표를 노리면 소통이 흐려지고 단호하게 대응하기 어렵다.",
     "q": "would not have the luxury"
    },
    {
     "t": "market",
     "s": "대출 창구와 달리 시장 기능 지원용 국채매입은 기간 프리미엄을 낮춰 경기를 부양한다. 가능하면 대출 수단을 쓰고, 매입이 필요하면 별도 계정에 두고 되도록 빨리 팔겠다고 약속해 원치 않는 부양을 피할 수 있다."
    },
    {
     "t": "market",
     "s": "국채시장은 지금 아주 잘 작동한다. 금리 변동성이 커도 거래는 원활 — 높은 금리나 빠른 상승 자체는 기능 장애 신호가 아니고, 연준은 심각한 장애가 있는 극단적 상황에서만 개입해야 한다.",
     "q": "I don't see high yields or rapidly rising yields, in themselves, as a sign of dysfunction"
    },
    {
     "t": "market",
     "s": "국채 발행이 딜러 대차대조표 여력보다 빨리 늘어 현금 확보용 매도가 거세질 때의 취약성은 커졌다. 긴축이 필요한 때일수록 불필요한 부양 없이 시장 기능을 지원할 수단을 키워야 한다."
    },
    {
     "t": "market",
     "s": "즉시결제 확산과 2028~2029년 Fedwire 일요일·공휴일 운영 계획으로 은행의 유동성 수요가 늘 수 있어 할인창구를 주말·공휴일로 넓히는 게 맞다. 연준 레포의 중앙청산, 시스템적으로 중요한 금융시장인프라(DFMU) 대출 준비도 강화해야 한다."
    }
   ]
  },
  {
   "id": "collins-20261113",
   "who": "collins",
   "date": "2026-11-13",
   "venue": "연설·인터뷰",
   "event": "보스턴 연은 제70회 경제 콘퍼런스(주택) 개회사 · 같은 날 블룸버그TV",
   "src": "https://www.bostonfed.org/news-and-events/speeches/2026/observations-on-housing-market-challenges.aspx",
   "cert": "보도 확인",
   "head": "가야 할 방향은 분명 — 곧 추가 긴축, 두 달 전 예상보다 조금 더 긴축적일 수도",
   "chips": {
    "next": [
     "곧 추가 긴축",
     "up"
    ],
    "pace": [
     "신중한 조정",
     "mid"
    ],
    "inflation": [
     "공급·에너지·관세, 생산성이 일부 상쇄",
     "mid"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "통화정책이 갈 방향은 분명하다. 곧 추가 긴축이 적절하고, 두 달 전 생각보다 다소 더 긴축적인 경로가 맞을 수 있다.",
     "q": "soon some additional firming, tightening of policy is appropriate"
    },
    {
     "t": "policy",
     "s": "얼마나 높이·빨리 올릴지는 미리 정하지 않는다. 최선은 신중한 조정이지만 생각을 바꿀 시나리오도 있다.",
     "q": "I don't want to get ahead in terms of how high we should go or how fast"
    },
    {
     "t": "policy",
     "s": "가장 그럴듯한 그림은 소비·기업 투자 수요가 탄탄한 가운데 조금 더 긴축적인 경로로 노동시장을 크게 흔들지 않고 적당한 기간 안에 물가를 낮추는 것. 물가가 더 끈질긴 시나리오도 염두에 둔다."
    },
    {
     "t": "inflation",
     "s": "가격 압력이 넓게 번지고 있고, 높은 상태가 오래 이어졌다.",
     "q": "I see the price pressures broadening, and it's been elevated for a long time"
    },
    {
     "t": "inflation",
     "s": "팬데믹 공급망 제약, 해외 분쟁의 에너지 충격, 관세가 모두 물가를 올렸다. 최근엔 빠른 생산성 향상이 압력 일부를 눌렀다."
    },
    {
     "t": "housing",
     "s": "단기적으로 긴축은 주택 시장 압력을 덜어 줄 재고 확대를 막고, 모기지를 쓰려는 의향과 능력에도 영향을 줘 수요를 누를 수 있다."
    },
    {
     "t": "housing",
     "s": "그래도 물가 안정을 위해 때로는 긴축이 필요하다. 높은 금리는 단기적으로 주택 구입·건설 비용을 올리지만, 장기적으로는 안정된 물가가 예측 가능한 여건을 만들어 주택과 경제 전반에 이롭다.",
     "q": "stable prices create predictable economic conditions that are good for housing"
    },
    {
     "t": "housing",
     "s": "주택은 경기순환에 큰 영향을 주는 전달 경로다 — 2000년대 중반 호황기 GDP 성장의 약 17%, 이후 침체기 생산 감소의 약 41%가 주택이었다. 2022년 긴축 뒤 모기지 금리가 뛰어 신규 주거투자가 둔화했다."
    },
    {
     "t": "housing",
     "s": "경제 전체의 생산성은 좋아졌지만 건설업은 오히려 떨어졌다 — 2020년 같은 투입 대비 산출이 1970년보다 약 40% 적고, 팬데믹 뒤 더 떨어졌다."
    }
   ]
  },
  {
   "id": "daly-20261113",
   "who": "daly",
   "date": "2026-11-13",
   "venue": "대담",
   "event": "네바다대(UNLV) 경제전망 포럼(헨더슨)",
   "src": "https://ca.finance.yahoo.com/news/fed-likely-raise-rates-amid-184220181.html",
   "cert": "보도 확인",
   "head": "십중팔구 금리를 올려야 — 지금 정책이 충분히 긴축적이라 말하기 어렵다",
   "chips": {
    "next": [
     "인상 가능성 높음",
     "up"
    ],
    "level": [
     "충분히 긴축적 아님",
     "up"
    ],
    "inflation": [
     "주거 뺀 서비스 역행",
     "up"
    ],
    "labor": [
     "소비 견조·일부 지친 조짐",
     "mid"
    ],
    "ai": [
     "생산성 증거 아직 적음",
     "mid"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "십중팔구 금리를 올려야 할 것이고 12월 회의에서 동료들과 논의한다. 지금 정책이 충분히 긴축적이라 말하기 어렵다.",
     "q": "We're going to need to, in all likelihood, raise rates"
    },
    {
     "t": "inflation",
     "s": "물가라는 문제 하나만 빼면 좋은 경제다. 여러 요인이 물가를 올려 걱정이고, 주거 뺀 서비스 물가가 맞는 방향으로 움직이지 않는다.",
     "q": "a good economy with one problem, inflation"
    },
    {
     "t": "inflation",
     "s": "생산자들이 비용을 마진으로 흡수할 여력이 바닥나 이제 소비자에게 넘기는 방안을 진지하게 검토한다고 전한다 — 피하고 싶은 물가 상승 압력이다. 주거 뺀 서비스 물가는 한번 오르면 잘 안 내려가 더 걱정이다."
    },
    {
     "t": "growth",
     "s": "소비는 놀라울 만큼 견조하고 위축 조짐이 없다. 다만 라스베이거스 등에서 소비 여력이 바닥난다는 얘기가 나오기 시작했다 — 심리와 지출의 괴리가 어떻게 좁혀질지 본다.",
     "q": "the consumer may be running out of gas"
    },
    {
     "t": "ai",
     "s": "AI가 노동생산성을 끌어올린다는 증거는 아직 많지 않다."
    }
   ]
  },
  {
   "id": "jefferson-20261113",
   "who": "jefferson",
   "date": "2026-11-13",
   "venue": "연설",
   "event": "UC 샌디에이고 경제 원탁회의",
   "src": "https://www.federalreserve.gov/newsevents/speech/jefferson20261113a.htm",
   "cert": "원문 확인",
   "head": "정책 기조엔 물가 경로가 더 중요한 신호 — 높은 에너지 가격이 넓게 번질까 경계",
   "chips": {
    "next": [
     "지표·전망·위험 보며",
     "mid"
    ],
    "inflation": [
     "목표 크게 웃돎",
     "up"
    ],
    "labor": [
     "최대고용 부합",
     "mid"
    ],
    "ai": [
     "중립금리 상승 가능성",
     "up"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "10월 동결에 찬성했다. 이후 지표는 활동·노동시장이 대체로 견조한 가운데 물가 압력이 이어짐을 보여 준다. 기조를 정하는 데는 물가 경로가 더 중요한 신호이고, 향후 조정은 추세·전망·위험 균형을 살펴 정한다.",
     "q": "I see the trajectory of inflation as providing the more important signal"
    },
    {
     "t": "inflation",
     "s": "물가는 2%를 크게 웃돈다 — 9월 PCE 전년비 3.6%, 근원 3.1%. 에너지 비용이 항공료·운송으로 번지고, 신기술 수요 급증으로 메모리 같은 투입재를 쓰는 상품·서비스 가격이 크게 올랐다. 10월 지표도 같은 흐름이다."
    },
    {
     "t": "inflation",
     "s": "높은 에너지 가격이 넓은 물가 상승으로 번질 위험을 걱정한다. 단기 기대인플레이션은 에너지 탓에 높지만 장기 기대는 2%에 맞게 잘 고정돼 있다."
    },
    {
     "t": "labor",
     "s": "실업률은 올해 대체로 횡보하며 최대고용에 부합한다. 해고는 적고 구인은 소폭 늘었으며, 고용 증가가 여러 업종으로 넓어진 점이 고무적이다."
    },
    {
     "t": "growth",
     "s": "3분기 GDP +3.4%, 기업투자는 매우 강하고 소비도 견조하다. 내년에도 잠재성장률 수준의 확장이 이어질 것. 위험은 대체로 균형 — 중동 긴장은 하방, 투자 급증은 상방.",
     "q": "roughly balanced"
    },
    {
     "t": "ai",
     "s": "AI 기대가 이미 총수요를 크게 늘린다 — 주가 상승의 상당 부분이 신기술 열기이고 자산 효과가 소비를, 데이터센터 투자가 기업투자를 끈다. 이 지출이 가동률과 물가를 밀어 올리지만 중기적으로는 공급 확대·생산성이 압력을 덜 것이다."
    },
    {
     "t": "ai",
     "s": "AI의 생산성 기여는 아직 제한적이지만 크게 커질 잠재력이 있다. 2020~2025년 노동생산성 증가율 평균 2.2%(직전 순환 1.5%)지만 AI 몫을 판단하기는 이르고, 시기와 크기는 매우 불확실하다."
    },
    {
     "t": "labor",
     "s": "AI가 노동자를 적응·재교육 속도보다 훨씬 빨리 대체해 실업률이 오를 위험도 있다. 그러면 구조적 실업인지 가리는 게 핵심 난제 — 통화정책은 경기적 여건엔 대응해도 구조적 요인은 풀지 못한다.",
     "q": "could displace workers much faster than they can adapt and retrain"
    },
    {
     "t": "rates",
     "s": "AI로 생산성 증가율이 영구히 높아지면 투자 수요 증가와 저축 감소로 중립금리가 오를 수 있다 — 그러면 같은 기준금리라도 정책이 사실상 더 완화적이다. 예측이 어려워 실시간으로 봐야 한다.",
     "q": "policy effectively becomes more accommodative"
    }
   ]
  },
  {
   "id": "collins-20261114",
   "who": "collins",
   "date": "2026-11-14",
   "date_note": "블룸버그·로이터 보도 제목으로 찾은 날짜 — 기사 주소는 못 찾음",
   "venue": "발언",
   "event": "보스턴 연은 경제 콘퍼런스 둘째 날 — 기자들과 대화",
   "src": "",
   "cert": "출처 미확인",
   "head": "지금은 꾸준하고 점진적인 인상이 맞아 보인다 — 다만 생각은 열어 둔다",
   "chips": {
    "next": [
     "꾸준·점진 인상",
     "up"
    ],
    "pace": [
     "점진(정해진 주기 아님)",
     "mid"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "지금은 꾸준하고 점진적인 경로가 적절해 보이지만 열린 마음으로 본다. 위험은 양쪽에 있고, '점진적'이 회의마다 같은 주기를 뜻하지는 않는다."
    }
   ]
  },
  {
   "id": "schmid-20261115",
   "who": "schmid",
   "date": "2026-11-15",
   "venue": "연설",
   "event": "전국신용협동조합경영협회(NCUMA) 연례 콘퍼런스(하와이) — 경제 전망·통화정책·지급결제",
   "src": "https://www.cnbc.com/2026/11/15/fed-has-some-work-to-do-on-inflation-kansas-city-fed-chief-says.html",
   "cert": "보도 확인",
   "head": "물가는 목표를 불편할 만큼 웃돌고 방향도 틀렸다 — '연준이 어쩔 수 없다'는 설명은 받아들이지 않는다",
   "chips": {
    "next": [
     "할 일 남음",
     "up"
    ],
    "inflation": [
     "불편할 만큼 높고 악화",
     "up"
    ]
   },
   "points": [
    {
     "t": "inflation",
     "s": "물가가 2% 목표를 불편할 만큼 웃돌고, 움직이는 방향도 틀렸다.",
     "q": "uncomfortably above the 2% price stability target, and moving in the wrong direction"
    },
    {
     "t": "policy",
     "s": "워시 의장이 8월에 '연준이 물가에 할 일이 있다'고 했는데, 그 뒤 일은 더 어려워졌다고 본다."
    },
    {
     "t": "inflation",
     "s": "물가를 공급 충격 탓으로 보는 설명과 금리에 반응하지 않는 수요 탓으로 보는 설명은 뿌리가 같다 — 물가가 연준이 다룰 수 없는 영역에 있다는 생각이다. 그는 물가가 늘 수요와 공급의 불균형에서 온다고 반박한다.",
     "q": "inflation is always the result of an imbalance between supply and demand"
    }
   ]
  },
  {
   "id": "nagel-20261110",
   "who": "nagel",
   "date": "2026-11-10",
   "venue": "인터뷰",
   "event": "블룸버그TV 인터뷰(리가 — 라트비아 중앙은행 연례 콘퍼런스 전날)",
   "src": "https://www.bloomberg.com/news/videos/2026-11-10/nagel-ecb-rate-hike-in-december-looks-rather-obvious-video",
   "cert": "보도 확인",
   "head": "12월에 올려야 한다는 건 꽤 분명해 보인다 — 유로존 물가가 너무 높다",
   "chips": {
    "next": [
     "12월 인상",
     "up"
    ],
    "inflation": [
     "너무 높음",
     "up"
    ]
   },
   "points": [
    {
     "t": "inflation",
     "s": "유로존 물가가 너무 높다."
    },
    {
     "t": "policy",
     "s": "이미 두 번 올렸지만 그 위에 더 해야 한다는 결론은 꽤 분명하고, 새 숫자가 나오면 더 분명해질 것이다.",
     "q": "it is rather obvious that we have to increase in December"
    }
   ]
  },
  {
   "id": "kazaks-20261110",
   "who": "kazaks",
   "date": "2026-11-10",
   "venue": "인터뷰",
   "event": "블룸버그TV 인터뷰(리가)",
   "src": "https://www.bloomberg.com/news/videos/2026-11-10/kazaks-sees-rate-hike-judgments-getting-more-nuanced-video",
   "cert": "보도 확인",
   "head": "추가 긴축이 어느 정도 필요해 보인다 — 다만 따질 득실은 더 미묘해졌다",
   "chips": {
    "next": [
     "추가 긴축 일부",
     "up"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "높은 에너지 가격이 이어지면 추가 긴축이 필요할 수 있다. 다만 따져야 할 득실이 더 미묘해졌다 — 보도마다 어조가 달라, 받은 요약보다 조건이 붙은 말에 가깝다."
    }
   ]
  },
  {
   "id": "lane-20261110",
   "who": "lane",
   "date": "2026-11-10",
   "venue": "인터뷰",
   "event": "블룸버그TV 인터뷰(같은 날 런던 영란은행 워처스 콘퍼런스 기조연설)",
   "src": "https://www.bloomberg.com/news/articles/2026-11-10/ecb-s-lane-sees-december-hike-as-prudent-if-data-don-t-shift",
   "cert": "보도 확인",
   "head": "12월 정보가 지금과 똑같다면 인상이 신중한 선택 — 물가 정점은 아직",
   "chips": {
    "next": [
     "정보 그대로면 12월 인상",
     "up"
    ],
    "inflation": [
     "연말 4% 조금 위",
     "up"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "12월에 손에 쥔 정보가 지금과 똑같다면 금리를 올리는 게 신중한 판단이다.",
     "q": "it would be prudent indeed to hike"
    },
    {
     "t": "inflation",
     "s": "물가 정점은 아직 오지 않았다. 올해 말 4%를 조금 넘고, 식품·근원 물가는 특히 2027년 1분기에 빨라질 것으로 본다.",
     "q": "There will be more to come in terms of peak inflation."
    }
   ]
  },
  {
   "id": "vujcic-20261110",
   "who": "vujcic",
   "date": "2026-11-10",
   "date_note": "받은 표의 날짜 — 보도로 확인하지 못함",
   "venue": "발언",
   "event": "자리 확인 못 함(브뤼셀 발언이라는 2차 소식지만 찾음)",
   "src": "",
   "cert": "출처 미확인",
   "head": "이란 전쟁이 이어지는 한 물가 압력도 이어진다 — 소비자 물가의 2차 효과는 내년에",
   "chips": {
    "inflation": [
     "운송비·원자재 간접 효과",
     "up"
    ]
   },
   "points": [
    {
     "t": "inflation",
     "s": "이란 전쟁이 이어지는 동안 물가 압력도 이어진다. 운송비 급등과 원자재 값 재상승이 시간이 지나며 간접적으로 물가를 올릴 수 있다."
    },
    {
     "t": "inflation",
     "s": "이미 두 번 올렸지만 소비자 물가에 대한 2차 효과는 내년에야 나타날 것이다."
    },
    {
     "t": "labor",
     "s": "2027년에도 임금 압력이 더 있겠지만 지난 물가 주기만큼 세지는 않을 것이다."
    }
   ]
  },
  {
   "id": "lombardelli-20261110",
   "who": "lombardelli",
   "date": "2026-11-10",
   "venue": "인터뷰",
   "event": "가디언 인터뷰(로이터 보도)",
   "src": "https://live.euronext.com/en/financial-news/boes-lombardelli-does-not-rule-out-december-rate-hike-she-tells-guardian",
   "cert": "보도 확인",
   "head": "12월 인상을 배제하지 않는다 — 다만 아직 판단할 정보가 충분하지 않다",
   "chips": {
    "next": [
     "12월 인상 배제 안 함",
     "mid"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "12월이든 2월이든 인상을 넣지도 빼지도 않는다 — 분쟁과 에너지 가격, 더 넓은 지표에 달렸다. 아직 정보가 충분하지 않다.",
     "q": "I wouldn't rule December in or out, February in or out"
    },
    {
     "t": "policy",
     "s": "그 전주 기준금리를 4%로 올린 결정(8대 1)에 다수 쪽으로 찬성했다."
    }
   ]
  },
  {
   "id": "makhlouf-20261111",
   "who": "makhlouf",
   "date": "2026-11-11",
   "venue": "발언",
   "event": "자리 확인 못 함(11-11~12 보도)",
   "src": "https://www.newsquawk.com/headlines/ecbs-makhlouf-says-price-pressures-are-largely-confined-to-energy-but-upside-risks-remain",
   "cert": "보도 확인",
   "head": "지표와 12월 새 전망을 기다릴 때 — 가격 압력은 주로 에너지에",
   "chips": {
    "next": [
     "지표·12월 전망 대기",
     "mid"
    ],
    "inflation": [
     "주로 에너지·상방 위험",
     "mid"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "신호가 엇갈려 지금은 지표와 12월 직원 전망을 기다려야 한다."
    },
    {
     "t": "inflation",
     "s": "가격 압력은 대체로 에너지에 머물지만 위쪽 위험은 남아 있다. 2027년 초 물가가 오를 것으로 본다."
    },
    {
     "t": "policy",
     "s": "앞선 두 번의 인상 효과가 아직 다 나타나지 않았고, 국채금리 상승으로 자금 조달 여건도 이미 조였다. 임금 상승은 제한적이고 기대인플레이션은 안정적이다."
    }
   ]
  },
  {
   "id": "greene-20261111",
   "who": "greene",
   "date": "2026-11-11",
   "venue": "기고",
   "event": "파이낸셜타임스 기고(로이터 보도)",
   "src": "https://uk.finance.yahoo.com/news/boes-greene-says-proactively-tighten-183937290.html",
   "cert": "보도 확인",
   "head": "임금이 높게 굳고 비용이 가격으로 넘어갈 위험이 커졌다 — 선제적으로 조여야",
   "chips": {
    "next": [
     "선제 긴축",
     "up"
    ],
    "labor": [
     "유휴 여력 생각보다 적음",
     "up"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "임금 상승이 높은 수준에 굳고 기업이 그 비용을 가격에 넘기는 걸 막으려면 통화정책 기조를 선제적으로 조여야 한다.",
     "q": "proactively tighten our monetary policy stance"
    },
    {
     "t": "labor",
     "s": "경제의 유휴 여력이 생각만큼 크지 않고 이미 정점을 지났을 수도 있다. 임금 상승률은 3.5% 이상에서 안정될 것으로 본다.",
     "q": "we don't have as much slack as we thought and it may already have peaked"
    }
   ]
  },
  {
   "id": "nagel-20261113",
   "who": "nagel",
   "date": "2026-11-13",
   "venue": "연설",
   "event": "프랑크푸르트 은행인 콘퍼런스 기조연설",
   "src": "https://www.bloomberg.com/news/articles/2026-11-13/nagel-says-highly-probable-that-ecb-will-have-to-act-again",
   "cert": "보도 확인",
   "head": "상황이 그대로면 다시 움직여야 할 가능성이 매우 크다 — 9월의 비관 시나리오에 근접",
   "chips": {
    "next": [
     "다시 행동 가능성 매우 큼",
     "up"
    ],
    "inflation": [
     "비관 시나리오 근접",
     "up"
    ]
   },
   "points": [
    {
     "t": "policy",
     "s": "지금 상황이 이어지면 다시 행동해야 할 가능성이 매우 크다. 높은 물가가 한 달 이어질 때마다 2차 효과 위험이 커진다.",
     "q": "If the situation stays as it is, it seems highly probable that we'll have to act again"
    },
    {
     "t": "inflation",
     "s": "9월 전망 때 그린 비관 시나리오에 가까워지고 있다. 기조 물가는 여전히 높고 단기 기대인플레이션은 헤드라인 급등을 따라 올랐다 — 중기 기대는 아직 꽤 잘 고정돼 있다."
    },
    {
     "t": "inflation",
     "s": "가스·전력 가격의 상승세가 최근 몇 주 힘을 얻었고, 가격 사슬의 앞단에서도 압력이 보인다."
    },
    {
     "t": "growth",
     "s": "보도로는 유로존 경제가 회복력을 보여 왔다고 했다. 책무를 다하면 2022년 같은 급등은 되풀이되지 않는다는 대목은 원래 문장을 찾지 못했다."
    }
   ]
  }
 ]
};
