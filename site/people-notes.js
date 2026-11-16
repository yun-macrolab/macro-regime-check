/* 연준 인물 페이지(people.html)의 '발언 정리' 자료 — 사람이 고친다(자동 갱신 없음, 기준일 asof). 2026-11-16 시작.
 * 운영자가 받은 발언 요약을 이 저장소가 자기 말로 다시 쓴 것: head = 한 줄 결론, chips = 쟁점 칩([글, up|mid|down]), points = 주제별 문장(t) ·
 * 발언자 본인의 영어 원문(q — 짧게, 원문·보도에서 찾은 것만). 새 묶음을 받으면 같은 꼴로 notes 앞쪽에 더한다(id = <키>-<날짜>).
 * 연준 밖 인사는 others에 이름·기관을 적고 같은 notes에 넣는다(화면의 '기타' 칸). 꼴은 scripts/test_people_site.py가 본다. */
window.PEOPLE_NOTES = {
 "asof": "2026-11-16",
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
  }
 },
 "notes": [
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
  }
 ]
};
