#!/usr/bin/env python3
"""저녁판 낱말 넓히기 테스트 — 2026-10-08 저녁에 더한 사전 낱말, 넓힌 패턴, 낱말 풀이와 공식 주소(digest_gloss).

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요 — 보기 문장은 전부 지어낸 것이다. 공식 주소가 실제로 열리는지는 여기서 보지 않는다(넣기 전에 사람이 urllib로 확인한다).
"""
import os
import re
import sys
import unicodedata
import unittest
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_gloss as G
import digest_rules as R
import digest_schema as S
import fixtures as F


def terms(text):
    return [h["term"] for h in R.match_terms(text)]


NEW = {     # 새 낱말 → (등급, 요인, 지역, 그 낱말이 나와야 하는 지어낸 문장들)
    "양적완화": ("B", "통화정책", "글로벌", ("양적완화를 다시 꺼냈다는 지어낸 말", "QE 재개를 다룬 지어낸 글")),
    "매파·비둘기": ("C", "통화정책", "글로벌", ("매파 쪽 발언이 늘었다는 지어낸 한 줄", "비둘기파로 기울었다는 지어낸 평가")),
    "중립금리": ("C", "통화정책", "글로벌", ("중립금리 추정치를 올렸다는 지어낸 말",)),
    "통화정책": ("C", "통화정책", "글로벌", ("통화정책 여력을 다룬 지어낸 글",)),
    "주요국 중앙은행": ("C", "통화정책", "글로벌", ("RBA가 지어낸 결정을 냈다", "캐나다 중앙은행의 지어낸 회의")),
    "금융여건": ("C", "통화정책", "글로벌", ("금융여건이 풀렸다는 지어낸 평가",)),
    "소수의견": ("B", "통화정책", "국내", ("인하 소수의견이 나왔다는 지어낸 말",)),
    "금융안정": ("C", "통화정책", "국내", ("금융안정 보고서를 지어낸 예문", "금융불균형을 걱정했다는 지어낸 말")),
    "대출 규제": ("C", "통화정책", "국내", ("대출 규제를 조였다는 지어낸 말", "스트레스 DSR 3단계라는 지어낸 예문")),
    "근원물가": ("C", "펀더멘털", "글로벌", ("근원물가가 끈적하다는 지어낸 평가", "슈퍼코어가 식었다는 지어낸 말")),
    "노동시장": ("C", "펀더멘털", "글로벌", ("노동시장이 식는다는 지어낸 진단",)),
    "소비": ("C", "펀더멘털", "글로벌", ("소비 둔화 신호라는 지어낸 말", "가계 소비가 버틴다는 지어낸 글")),
    "미 생산성": ("C", "펀더멘털", "글로벌", ("단위노동비용이 올랐다는 지어낸 숫자", "비농업 생산성을 다룬 지어낸 글")),
    "디폴트": ("C", "펀더멘털", "글로벌", ("디폴트 우려를 지어낸 예문", "채무불이행 가능성을 지어낸 글")),
    "지역 연은 지수": ("C", "펀더멘털", "글로벌", ("뉴욕 연은 제조업 지수가 지어낸 값으로 나왔다", "엠파이어스테이트를 지어낸 예문")),
    "미 무역수지": ("C", "펀더멘털", "글로벌", ("미국 무역적자가 줄었다는 지어낸 말",)),
    "경기선행지수": ("C", "펀더멘털", "글로벌", ("경기선행지수가 내렸다는 지어낸 숫자",)),
    "감원": ("C", "펀더멘털", "글로벌", ("감원 계획이 늘었다는 지어낸 말", "정리해고 소식을 지어낸 글")),
    "중국 경기": ("C", "펀더멘털", "글로벌", ("중국 경기가 식는다는 지어낸 진단", "중국 부동산을 다룬 지어낸 글")),
    "유럽 경기": ("C", "펀더멘털", "글로벌", ("유로존 경기가 버틴다는 지어낸 말", "독일 경제를 다룬 지어낸 글")),
    "내수": ("C", "펀더멘털", "국내", ("내수 부진이 길다는 지어낸 진단", "민간소비가 살아난다는 지어낸 말")),
    "건설·PF": ("C", "펀더멘털", "국내", ("부동산 PF 정리를 지어낸 예문", "건설경기가 나쁘다는 지어낸 말")),
    "한국 기업심리": ("C", "펀더멘털", "국내", ("BSI가 올랐다는 지어낸 숫자", "기업경기실사 결과를 지어낸 글")),
    "잠재성장률": ("C", "펀더멘털", "국내", ("잠재성장률이 낮아졌다는 지어낸 추정",)),
    "ETF": ("C", "기타", "글로벌", ("ETF로 돈이 들어왔다는 지어낸 말",)),
    "헤지펀드": ("C", "수급", "글로벌", ("헤지펀드 포지션을 지어낸 예문", "베이시스 트레이드가 풀린다는 지어낸 글")),
    "연준 대차대조표": ("C", "수급", "글로벌", ("대차대조표 규모를 다룬 지어낸 글", "연준 지준 잔고가 줄었다는 지어낸 말")),
    "채권 공급 부담": ("C", "수급", "글로벌", ("국채 공급 부담이 크다는 지어낸 말", "채권 발행 부담을 지어낸 예문")),
    "국내 재정": ("C", "수급", "국내", ("정부 예산안을 지어낸 예문", "국가채무가 늘었다는 지어낸 숫자", "세수 결손을 지어낸 글")),
    "개인 채권 투자": ("C", "수급", "국내", ("개인투자용 국채 청약을 지어낸 예문", "개인의 채권 순매수가 늘었다는 지어낸 말")),
    "재정증권": ("C", "수급", "국내", ("재정증권 발행을 지어낸 예문", "한은 일시차입을 지어낸 글")),
    "주금공 MBS": ("C", "수급", "국내", ("주금공 MBS 발행을 지어낸 예문", "주택금융공사 소식을 지어낸 글")),
    "캐리": ("C", "기술적", "글로벌", ("캐리 매력이 남았다는 지어낸 말", "롤다운을 노린다는 지어낸 글")),
    "실질금리": ("C", "기술적", "글로벌", ("실질금리가 올랐다는 지어낸 말",)),
    "물가연동채": ("C", "기술적", "글로벌", ("물가연동채 수요를 지어낸 예문", "TIPS 금리를 지어낸 글")),
    "장기금리": ("C", "기술적", "글로벌", ("장기금리가 뛰었다는 지어낸 말",)),
    "유럽 정치": ("C", "기타", "글로벌", ("프랑스 총리가 지어낸 말을 했다", "영국 정부 불신임 표결을 지어낸 예문")),
    "미중 갈등": ("C", "기타", "글로벌", ("미중 갈등이 깊어진다는 지어낸 말", "희토류 수출통제를 지어낸 글")),
    "엔화": ("C", "기타", "글로벌", ("엔화가 약해졌다는 지어낸 말", "엔저가 이어진다는 지어낸 글")),
    "위안화": ("C", "기타", "글로벌", ("위안화 고시를 지어낸 예문",)),
    "유로화": ("C", "기타", "글로벌", ("유로화가 올랐다는 지어낸 말",)),
    "신흥국": ("C", "기타", "글로벌", ("신흥국 통화를 다룬 지어낸 글", "이머징 자금을 지어낸 예문")),
    "해외 증시": ("C", "기타", "글로벌", ("닛케이가 올랐다는 지어낸 말", "유럽 증시 마감을 지어낸 글")),
    "공매도": ("C", "기타", "국내", ("공매도 잔고를 지어낸 예문",)),
    "위험 선호·회피": ("C", "기타", "글로벌", ("안전자산으로 몰렸다는 지어낸 말", "위험 선호가 살아났다는 지어낸 글", "리스크오프라는 지어낸 평가")),
    "한미 통상": ("C", "기타", "국내", ("한미 관세 협상을 지어낸 예문", "대미 투자를 다룬 지어낸 글")),
    "외환당국": ("C", "기타", "국내", ("외환당국 구두개입을 지어낸 예문", "외환보유액이 줄었다는 지어낸 숫자")),
}
WIDER = {   # 이미 있던 낱말에 더한 패턴 — 지어낸 문장 → 나와야 하는 낱말
    "추가 인상 가능성을 지어낸 한 줄": "정책 기대", "연내 인하를 지어낸 예문": "정책 기대",
    "물가 상방 위험을 지어낸 글": "인플레", "물가 안정 목표를 지어낸 말": "인플레",
    "비축유 방출을 지어낸 예문": "유가", "IEA 월간 보고서를 지어낸 글": "유가", "원유 재고가 줄었다는 지어낸 숫자": "유가",
    "에너지 가격이 뛰었다는 지어낸 말": "원자재", "메모리 업황을 지어낸 글": "반도체", "잠정실적이 나왔다는 지어낸 말": "실적",
    "레포 시장이 흔들렸다는 지어낸 말": "단기자금", "산금채 발행을 지어낸 예문": "은행채·공사채",
    "외국인 채권 자금이 들어왔다는 지어낸 말": "외국인 원화채", "유로클리어 연결을 지어낸 예문": "WGBI",
    "롱 포지션을 줄였다는 지어낸 말": "포지션", "박스권이라는 지어낸 평가": "기술적 수준",
    "FOMC 9월 의사록을 지어낸 예문": "연준 의사록", "연준 정례회의 의사록을 지어낸 글": "연준 의사록",
    "장단기 금리 역전을 지어낸 예문": "커브", "미국 증시가 올랐다는 지어낸 말": "미 증시", "국내 증시 마감을 지어낸 글": "국내 증시",
    "후티가 지어낸 일을 벌였다": "지정학", "무디스가 등급 전망을 바꿨다는 지어낸 말": "국가 신용등급", "전셋값이 올랐다는 지어낸 숫자": "부동산",
}


class NewTermsTest(unittest.TestCase):
    def test_table_grew_by_forty_to_eighty_words(self):
        names = [e["term"] for e in R.LEXICON]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(40 <= len(NEW) <= 80 and set(NEW) <= set(names))
        self.assertTrue(160 <= len(names) <= 210, len(names))
        for e in R.LEXICON:                                    # 화면의 낱말 꼴(20자 이하, 한글·영문·숫자와 · / & +)에 든다
            self.assertRegex(e["term"], r"^[가-힣A-Za-z0-9][가-힣A-Za-z0-9 ·/&+]{0,11}$")

    def test_each_new_word_has_its_grade_and_cell(self):
        for term, (grade, factor, region, _) in NEW.items():
            e = R.TERMS[term]
            self.assertEqual((e["grade"], e["factor"], e["region"]), (grade, factor, region), term)
        self.assertEqual(sorted(t for t, v in NEW.items() if v[0] == "A"), [])       # A급(결정·핵심 지표)은 늘리지 않는다

    def test_new_words_are_found_in_made_up_sentences(self):
        for term, (_, _, _, texts) in NEW.items():
            for text in texts:
                with self.subTest(text):
                    self.assertIn(term, terms(text))

    def test_wider_patterns_of_old_words(self):
        for text, term in WIDER.items():
            with self.subTest(text):
                self.assertIn(term, terms(text))

    def test_words_that_only_look_alike(self):
        plain = ("부도덕하다는 지어낸 비난", "캐리어를 끌고 갔다는 지어낸 말", "전세계가 놀랐다는 지어낸 말", "스피치 대회를 지어낸 글",
                 "오렌지 주스 값을 지어낸 예문", "소비자가 고른다는 지어낸 말", "커뮤니케이션을 다듬었다는 지어낸 말", "엔고쿠라는 지어낸 이름",
                 "공장 노동 생산성을 지어낸 글", "내년 예산안을 지어낸 예문")
        for text in plain:
            with self.subTest(text):
                self.assertEqual(terms(text), [])
        self.assertNotIn("캐리", terms("엔 캐리 트레이드 청산을 지어낸 예문"))             # 엔 캐리는 따로 있는 낱말이다
        self.assertIn("엔 캐리", terms("엔 캐리 트레이드 청산을 지어낸 예문"))
        self.assertNotIn("미 고용", terms("비농업 생산성을 다룬 지어낸 글"))               # 생산성 통계의 '비농업'은 고용 지표가 아니다
        self.assertNotIn("내수", terms("중국 내수 부진을 지어낸 글"))
        self.assertNotIn("국내 재정", terms("프랑스 예산안 표결을 지어낸 글"))
        self.assertNotIn("외환당국", terms("중국 외환보유액을 지어낸 숫자"))                # 다른 나라의 외환보유액은 국내 칸이 아니다
        for text in ("부품 가격 인상 가능성을 지어낸 글", "요금 추가 인상을 지어낸 말", "관세 인상 시점을 지어낸 예문"):
            self.assertNotIn("정책 기대", terms(text), text)                           # 금리가 아닌 것의 인상·인하
        self.assertNotIn("모기지", terms("주금공 MBS 발행을 지어낸 예문"))                 # 국내 주택저당증권은 국내 칸으로
        self.assertNotIn("통화정책", terms("통화정책방향 결정문을 지어낸 예문"))            # 더 긴 자리(금통위)가 이긴다
        self.assertIn("금통위", terms("통화정책방향 결정문을 지어낸 예문"))
        self.assertNotIn("인플레", terms("근원 인플레가 식었다는 지어낸 말"))              # 더 긴 자리(근원물가)가 이긴다
        self.assertNotIn("장기금리", terms("일본 장기금리가 올랐다는 지어낸 말"))
        self.assertNotIn("실적", terms("CPI 컨센서스를 지어낸 예문"))

    def test_look_alikes_found_in_review(self):
        """검토에서 걸린 닮은꼴(2026-10-08 밤) — 새 낱말과 넓힌 패턴이 뜻이 다른 말에 걸리지 않는다. 보기는 모두 지어낸 것이다."""
        not_this = {
            "채권 공급 부담": ("오버행 물량 부담을 지어낸 글", "원유 공급 부담을 지어낸 말"),
            "디폴트": ("디폴트옵션 상품을 지어낸 글",),
            "유럽 정치": ("일본 내각 불신임안을 지어낸 글", "장관 불신임을 지어낸 말"),
            "연준 대차대조표": ("은행 지준 부족을 지어낸 말", "한은 지준 잔고를 지어낸 숫자"),
            "소수의견": ("FOMC에서 소수의견이 나왔다는 지어낸 말", "대법원 소수의견을 지어낸 글"),
            "반도체": ("메모리얼 데이 휴장을 지어낸 글",),
            "감원": ("비용 절감원인을 지어낸 글",),
            "포지션": ("옵션 만기를 앞뒀다는 지어낸 글", "차익 실현이 나왔다는 지어낸 말", "저가 매수가 들어왔다는 지어낸 말"),
            "미 주거비": ("상가 임대료를 지어낸 예문",),
            "경상수지": ("중국 무역수지를 지어낸 숫자", "독일 경상수지를 지어낸 글"),
            "연준 의사록": ("연준과 금통위 의사록을 지어낸 글", "연준 인사들이 주주총회 의사록을 봤다는 지어낸 말"),
        }
        for term, texts in not_this.items():
            for text in texts:
                with self.subTest(text):
                    self.assertNotIn(term, terms(text))
        still = {"디폴트": "디폴트 우려를 지어낸 예문", "감원": "대규모 감원을 지어낸 글", "소수의견": "금통위에서 인하 소수의견이 나왔다는 지어낸 말",
                 "미 주거비": "주거비와 주택 임대료를 지어낸 숫자", "경상수지": "9월 무역수지를 지어낸 숫자", "반도체": "메모리 가격을 지어낸 글",
                 "금통위 의사록": "연준과 금통위 의사록을 지어낸 글"}
        for term, text in still.items():
            self.assertIn(term, terms(text), text)
        self.assertEqual(R.TERMS["ETF"]["factor"], "기타")                          # 주식 ETF 글이 채권 수급 칸으로 가지 않게
        self.assertNotIn("위험 선호", R.TERMS)                                      # 안전자산 선호도 걸리는 낱말이라 이름을 두 방향으로

    def test_wide_words_stand_behind_the_narrow_ones(self):
        """다른 낱말의 이름에 토막째 든 넓은 낱말(연준 ⊂ 연준 의사록)은 같은 등급 안에서 뒤로 가고, 좁은 낱말이 곁에 있으면 빠진다."""
        self.assertEqual(R.WIDE, frozenset({"연준", "한은", "AI", "금리", "커브", "국채 입찰", "실적"}))
        for wide in R.WIDE:                                                        # 사전에 그 낱말을 토막째 품은 좁은 낱말이 있다
            self.assertTrue(any(wide != t and wide.split() == t.split()[i:i + len(wide.split())]
                                for t in R.TERMS for i in range(len(t.split()))), wide)
            self.assertNotEqual(R.grade_of(wide), "A")                              # A급은 넣지 않는다(금통위와 그 의사록은 다른 일)
        self.assertFalse(R.WIDE & {"금통위", "인플레", "캐리", "단기자금", "경기"})    # 글자만 겹치거나 뜻이 갈리는 짝은 세지 않는다
        self.assertEqual(R.by_grade(["AI", "지정학", "관세", "금리", "유가"]), ["유가", "관세", "지정학", "AI", "금리"])
        self.assertEqual(R.by_count({"AI": 3, "관세": 3, "미 고용": 2}), [("관세", 3), ("AI", 3), ("미 고용", 2)])
        self.assertEqual(R.narrow(["연준", "연준 의사록", "AI", "AI Capex", "금리", "인플레", "기대인플레"]),
                         ["연준 의사록", "AI Capex", "금리", "인플레", "기대인플레"])
        self.assertEqual(R.narrow(["금리", "커브", "유가"], among=["미 국채 금리", "미 국채 커브"]), ["유가"])
        self.assertEqual(R.narrow(["금통위", "금통위 의사록"]), ["금통위", "금통위 의사록"])

    def test_rate_tag_survives_where_a_longer_word_swallows_the_plain_one(self):
        """'금리'를 품은 새 낱말(중립금리 · 실질금리 · 장기금리)은 금리 꼬리표를 물려받는다 — 금리 변동 가산(M)이 달라지지 않게."""
        for term in ("중립금리", "실질금리", "장기금리"):
            self.assertIn(R.RATE_TAG, R.TERMS[term]["tags"], term)
            self.assertNotIn("금리", terms(f"{term}를 다룬 지어낸 글"))
        self.assertEqual({t for t in NEW if R.TERMS[t]["tags"]}, {"중립금리", "실질금리", "장기금리"})

    def test_old_fixture_answers_still_hold(self):
        for (ch, pid), want in F.EXPECT_TERMS.items():
            text = next(p["text"] for p in F.posts() if (p["ch"], p["id"]) == (ch, pid))
            self.assertEqual(terms(text), want, (ch, pid))


class GlossTest(unittest.TestCase):
    def test_every_gloss_belongs_to_a_dictionary_word(self):
        self.assertTrue(set(G.GLOSS) <= set(R.TERMS))
        self.assertGreaterEqual(len(G.GLOSS), 60)
        for e in R.LEXICON:                                    # A·B급 낱말은 풀이가 있다(확신이 없어 비워 둔 것은 G.BLANK에 적는다)
            if e["grade"] in ("A", "B"):
                self.assertTrue(e["term"] in G.GLOSS or e["term"] in G.BLANK, e["term"])
        self.assertFalse(set(G.BLANK) & set(G.GLOSS))

    def test_gloss_is_one_plain_line_within_sixty_chars(self):
        for term, (text, url) in G.GLOSS.items():
            with self.subTest(term):
                self.assertTrue(0 < len(text) <= 60, len(text))
                self.assertEqual(text, unicodedata.normalize("NFC", text).strip())
                self.assertNotRegex(text, r"[\n\r\t<>@\\]|https?:|www\.")
                self.assertFalse(any(unicodedata.category(c) in ("Cf", "Cc") for c in text))
                self.assertEqual(R.find_nums(text), [], "풀이에 단위 붙은 숫자(시세·수준)를 쓰지 않는다")
                self.assertNotRegex(text, r"유망|추천|호재|악재|사야|팔아야|오를 것|내릴 것|좋다|나쁘다|급등|급락")     # 평가·매매 판단을 담지 않는다
                self.assertFalse(S.URL_RE.fullmatch(text) or R.is_num(text) or R.is_phrase(text))

    def test_official_addresses_are_https_on_the_allowed_domains(self):
        urls = [url for _, url in G.GLOSS.values() if url]
        self.assertGreaterEqual(len(urls), 15)
        for url in urls:
            with self.subTest(url):
                u = urllib.parse.urlsplit(url)
                self.assertEqual((u.scheme, u.username, u.port, u.fragment), ("https", None, None, ""))
                self.assertTrue(any(u.hostname == d or u.hostname.endswith("." + d) for d in G.OFFICIAL_DOMAINS), u.hostname)
                self.assertRegex(url, r"^https://[a-z0-9.-]+/[A-Za-z0-9/._?=&%-]*$")
                self.assertNotIn("t.me", u.hostname)
        for d in G.OFFICIAL_DOMAINS:                           # 허용 도메인은 공공 기관의 것만 — 쓰이지 않는 도메인을 두지 않는다
            self.assertRegex(d, r"^[a-z0-9-]+(?:\.[a-z0-9-]+)+$")
            self.assertTrue(any(urllib.parse.urlsplit(x).hostname.endswith(d) for x in urls), d)
            self.assertRegex(d, r"\.(?:gov|org|eu)$|\.(?:go|or)\.(?:kr|jp)$", d)

    def test_rules_carry_the_gloss_table(self):
        self.assertIs(R.GLOSS, G.GLOSS)
        self.assertEqual(R.gloss_of("연준 의사록"), {"term": "연준 의사록", "text": G.GLOSS["연준 의사록"][0], "url": G.GLOSS["연준 의사록"][1]})
        self.assertIsNone(R.gloss_of("금리"))                  # 뜻이 뻔한 낱말에는 풀이를 달지 않는다
        for term in ("연준", "한은", "인플레", "통화정책", "장기금리", "노동시장", "관세", "지정학", "AI"):      # 자주 나오는 낱말은 풀이가 닿는다
            self.assertIsNotNone(R.gloss_of(term), term)
        self.assertIsNone(R.gloss_of("사전에 없는 낱말"))
        got = R.glosses(["금리", "연준 의사록", "미 CPI", "연준 의사록", "FOMC"])
        self.assertEqual([g["term"] for g in got], ["FOMC", "연준 의사록", "미 CPI"])       # 한 번씩, 사전에 실린 순서로

    def test_hard_ones_say_what_they_are(self):
        """헷갈리기 쉬운 낱말의 풀이에 그 낱말을 가르는 알맹이가 들어 있는가."""
        need = {"기대인플레": ("BEI",), "기간 프리미엄": ("장기채", "보상"), "WGBI": ("FTSE", "지수"), "베이지북": ("12개", "연은"),
                "양적긴축": ("보유",), "단기자금": ("역레포",), "연준 의사록": ("3주",), "국채 입찰": ("응찰", "나라를 밝히지 않은"),
                "금통위 의사록": ("2주 뒤 첫 화요일",), "기준금리": ("중앙은행",), "연준": ("연방준비제도",), "경상수지": ("무역수지",)}
        for term, words in need.items():
            for w in words:
                self.assertIn(w, G.GLOSS[term][0], term)

    def test_gloss_does_not_claim_what_the_word_may_not_mean(self):
        """넓게 걸리는 낱말의 풀이·주소가 한 나라·한 기관의 것으로 못 박지 않는가, 전망·단정으로 읽히는 말이 없는가(검토 2026-10-08 밤)."""
        self.assertIsNone(G.GLOSS["국채 입찰"][1])                # 나라를 밝히지 않은 입찰 글에 미 재무부 쪽을 걸지 않는다
        self.assertIsNone(G.GLOSS["기준금리"][1])                 # 미국 기준금리 글에도 걸리는 낱말이다
        self.assertNotIn("한국은행이 정하는", G.GLOSS["기준금리"][0])
        self.assertIn("fraser.stlouisfed.org", G.GLOSS["연준 의사록"][1])
        self.assertIn("pet_pri_spt", G.GLOSS["유가"][1])           # 수급 주간 보고가 아니라 현물 가격 쪽
        for term, said in (("WGBI", "자금이 들어온다"), ("추경", "발행이 늘어난다"), ("외환당국", "시장에 개입한다"), ("물가연동채", "늘어나는"),
                           ("스테이블코인", "주로 단기 국채를 든다"), ("신용 스프레드", "신용 위험의 값이다"), ("사모신용", "BDC"),
                           ("국고채 금리", "국채선물 값")):
            self.assertNotIn(said, G.GLOSS[term][0], term)
        for term, (text, _) in G.GLOSS.items():
            self.assertNotRegex(text, r"들어온다|늘어난다|오른다|내린다|개입한다", term)

    def test_gloss_texts_and_addresses_are_closed_only_as_written(self):
        text, url = G.GLOSS["기간 프리미엄"]
        self.assertTrue(S.is_closed(text) and S.is_closed(url))
        for bad in (text + " ", text[:-1], text + F.C1, url + "/", url.replace("https", "http"), url + "?x=" + F.C1,
                    "https://www.newyorkfed.org/", "https://example.org/", "https://t.me/s/fxbond1"):
            self.assertFalse(S.is_closed(bad), bad[:20])


if __name__ == "__main__":
    unittest.main()
