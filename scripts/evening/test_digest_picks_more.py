#!/usr/bin/env python3
"""AI 요약 문장 검사(digest_picks)의 보강 테스트 — 검토에서 통과해 버린 문장들: 조사만 바꾼 베낌 · 이어 붙인 베낌 · 단위와 대상을 바꾼
숫자 · 뒤집힌 방향 · 비켜 간 권유와 전망 · 글 하나가 넓힌 낱말 · 소문자 영문 토막. 그리고 지나치게 걸리던 전언 꼴.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요 — 글과 문장은 모두 지어낸 것이다. 실제 채널 글은 테스트에 넣지 않는다.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_picks as K
import digest_rules as R
import fixtures as F
import test_digest_picks as TK

TH = R.TH
NONE = {"terms": [], "words": []}


def item_for(*texts):
    """그 글자들에 든 사전 낱말을 모두 가진 항목 — 낱말 검사가 아닌 것을 볼 때 쓴다."""
    return {"terms": sorted({h["term"] for t in texts for h in R.match_terms(t)}), "words": []}


def check(name, fact, texts, item=None):
    return K.fact_checks(fact, item or item_for(fact, *texts), list(texts))[name]


class CopyMoreTest(unittest.TestCase):
    def test_every_particle_swapped(self):
        """어절마다 조사만 바꾼 문장 — 글자 3-gram은 조사에서 끊겨 절반 아래로 떨어지지만 조사를 뗀 어절은 그대로 이어진다."""
        text = ["지어낸 글: 한은이 물가를 다시 봤고 금리를 그대로 뒀고 성장을 낮게 봤다."]
        fact = "한은은 물가도 다시 봤고 금리는 그대로 뒀고 성장은 낮게 봤다."
        f, t = K._flat(fact), K._flat(text[0])
        grams = [f[i:i + 3] for i in range(len(f) - 2)]
        self.assertLess(sum(g in t for g in grams), TH["copy_ratio"] * len(grams))        # 글자 비율로는 안 걸린다
        self.assertFalse(check("copy", fact, text))
        self.assertEqual(TH["copy_stems"], 5)

    def test_own_words_keep_passing(self):
        self.assertTrue(check("copy", "10년 만기 국고채 입찰은 응찰률 247.4%, 낙찰금리 4.365%로 마무리됐다.", TK.PROSE))
        self.assertTrue(check("copy", TK.GOOD, TK.CPI))
        memo = ["미 CPI 9월 3.1% 예상 3.0% 전월 2.9%"]                          # 메모체 글의 숫자를 차례대로 엮은 문장 — 네 어절까지는 된다
        self.assertTrue(check("copy", "미국 9월 소비자물가 상승률은 3.1%로 예상 3.0%를 웃돌았고 전월 2.9%보다 높았다.", memo))

    def test_pieces_of_two_posts_spliced(self):
        """두 글에서 한 토막씩 그대로 이어 붙인 문장 — 글 하나씩 재면 비율도 연속 길이도 문턱 아래다."""
        a = "지어낸 글 하나: 오전에는 조용했지만 오후 들어 외국인이 국채선물을 대거 사들였다."
        b = "지어낸 글 둘: 장 마감 무렵에는 보험사의 장기물 수요가 다시 확인됐다."
        fact = "외국인이 국채선물을 대거 사들였고 보험사의 장기물 수요가 다시 확인됐다."
        f = K._flat(fact)
        for t in map(K._flat, (a, b)):
            self.assertFalse(any(f[i:i + TH["copy_run"]] in t for i in range(len(f) - TH["copy_run"] + 1)))
        self.assertFalse(check("copy", fact, [a, b]))
        self.assertFalse(check("copy", "오후 들어 외국인이 국채선물을 대거 사들였다는 말과 함께 보험사의 장기물 수요가 거론됐다.", [a, b]))
        self.assertEqual((TH["copy_piece"], TH["copy_cover"]), (10, 0.5))
        c = "지어낸 글 셋: 입찰에서는 장기투자기관의 초장기물 수요가 두드러졌다."       # 세 어절씩만 이어져 어절 검사에는 안 걸리는 토막들
        d = "지어낸 글 넷: 선물 시장에서는 외국인의 국채선물 순매수가 이어졌다."
        fact = "장기투자기관의 초장기물 수요와 외국인의 국채선물 순매수가 함께 거론됐다."
        mine, k = K._stems(fact), TH["copy_stems"]
        for t in map(K._stems, (c, d)):
            self.assertFalse(any(mine[i:i + k] == t[j:j + k] for i in range(len(mine) - k + 1) for j in range(len(t) - k + 1)))
        self.assertFalse(check("copy", fact, [c, d]))                          # 긴 토막 둘이 문장의 절반 넘게 덮는다
        self.assertTrue(check("copy", "장기투자기관과 외국인이 각각 초장기물과 국채선물에서 수요를 보였다는 말이 함께 나왔다.", [c, d]))

    def test_run_boundary(self):
        """연속 겹침은 꼭 copy_run자부터 — 20자는 걸리고 19자는 된다."""
        text = ["지어낸 글: 입찰에서는 장기투자기관의 초장기물 수요가 재확인됐다는 평이 나왔다."]
        head = "시장 참가자들은 이날 오후 내내 한산했던 거래 흐름 속에서도 "
        twenty, nineteen = head + "장기투자기관의 초장기물 수요가 재확인됐다는 점에 주목했다.", head + "장기투자기관의 초장기물 수요가 재확인됐다고 주목했다."
        shared = K._flat("장기투자기관의 초장기물 수요가 재확인됐다는")
        self.assertEqual((len(shared), TH["copy_run"]), (20, 20))
        self.assertIn(shared, K._flat(twenty))
        self.assertFalse(check("copy", twenty, text))
        self.assertTrue(check("copy", nineteen, text))


class NumberMoreTest(unittest.TestCase):
    def test_the_unit_must_match(self):
        """숫자는 같은데 단위 · 대상이 다르다 — 사람 수를 금리로, bp를 %로, 만기를 금리로, %를 %p로."""
        mpc = ["금통위원 6명 가운데 1명이 인하 소수의견을 냈다. 기준금리는 연 2.50%로 동결됐다."]
        ktb = ["국고채 3년 금리가 7bp 올랐다."]
        for fact, texts in (("금통위는 기준금리를 연 6%로 정했다.", mpc), ("국고채 3년 금리 오름폭은 7%에 이르렀다.", ktb),
                            ("국고채 금리는 3% 수준이 됐다.", ktb), ("국고채 금리는 3.0% 수준이 됐다.", ktb),
                            ("미 CPI는 전년 대비 3.1%p 올랐다.", TK.CPI), ("국고채 3년 금리가 7 올랐다.", ktb)):
            with self.subTest(fact):
                self.assertFalse(check("number", fact, texts))
        for fact, texts in (("금통위원 6명 가운데 1명이 다른 의견을 냈고 기준금리는 연 2.5%에 머물렀다.", mpc),
                            ("3년 만기 국고채 금리는 7bp 상승했다.", ktb), ("국고채 3년물 금리가 7bp 올랐다.", ["국고채 3년물 금리 7 bp 상승."]),
                            ("스프레드는 0.5%포인트 벌어졌다.", ["스프레드 0.5%p 확대."])):
            with self.subTest(fact):
                self.assertTrue(check("number", fact, texts))

    def test_the_label_belongs_to_its_own_number(self):
        """꼬리표는 문장 어딘가가 아니라 그 숫자 앞에 있어야 한다 — 예상치를 결과처럼 쓰고 뒤에서 '예상'을 말해도 안 된다."""
        texts = ["미 CPI는 3.4%로 예상 2.9%를 상회했다."]
        self.assertFalse(check("number", "미 CPI는 2.9%였다. 시장 예상과는 달랐다.", texts))
        self.assertTrue(check("number", "미 CPI는 3.4%로 예상 2.9%를 웃돌았다.", texts))
        self.assertTrue(check("number", "미 CPI는 예상치 2.9%보다 높은 3.4%였다.", texts))

    def test_two_numbers_and_the_word_between_them(self):
        """'A로 B를 웃돌았다' — 같은 단위의 두 숫자의 크기가 그 말과 맞아야 한다."""
        texts = ["낙찰금리는 5.300%였고 발행 전 거래 금리는 5.317%였다."]
        self.assertFalse(check("number", "낙찰 금리는 5.300%로 발행 전 거래 금리 5.317%를 웃돌았다.", texts))
        self.assertTrue(check("number", "낙찰 금리는 5.300%로 발행 전 거래 금리 5.317%를 밑돌았다.", texts))
        self.assertFalse(check("number", "낙찰 금리는 5.300%로 발행 전 거래 금리 5.317%보다 높았다.", texts))
        self.assertTrue(check("number", "10년물 낙찰 금리는 5.300%로 발행 전 거래 금리 5.317%보다 낮았다.", ["10년물 " + texts[0]]))


class TermMoreTest(unittest.TestCase):
    def test_the_direction_is_not_flipped(self):
        cases = (("외국인은 이날 3년 국채선물을 순매도했다.", "외국인은 이날 3년 국채선물을 순매수했다.", ["외국인이 3년 국채선물을 순매수했다는 집계."]),
                 ("국고채 3년 금리가 3bp 내렸다.", "국고채 3년 금리가 3bp 올랐다.", ["국고채 3년 금리 3bp 상승 마감."]),
                 ("미국 소비자물가는 시장 예상에 못 미쳤다.", "미국 소비자물가는 시장 예상보다 높았다.", TK.CPI[:1]),
                 ("참석자들은 기준금리를 한 번 더 내리는 쪽이 적절하다고 봤다.", "참석자들은 기준금리를 한 번 더 올리는 쪽이 적절하다고 봤다.",
                  ["참석자들은 연말까지 기준금리를 한 차례 더 올리는 것이 적절하다고 판단."]),
                 ("연준은 자산 매입을 확대했다.", "연준은 자산 보유를 줄였다.", ["연준 대차대조표 축소 지속."]))
        for flipped, kept, texts in cases:
            with self.subTest(flipped):
                self.assertFalse(check("term", flipped, texts))
                self.assertTrue(check("term", kept, texts))
        both = ["국고채 3년 금리는 올랐고 10년 금리는 내렸다."]                    # 글에 두 방향이 다 있으면 가릴 수 없다 — 둔다
        self.assertTrue(check("term", "국고채 3년 금리가 내렸다.", both))

    def test_a_decision_needs_a_decision_in_the_posts(self):
        """글에는 동결과 '인하 소수의견'뿐인데 인하했다고 쓴 문장 — 낱말이 글에 있다는 것만으로는 안 된다."""
        texts = ["한은 금통위가 기준금리를 연 2.50%로 동결했다. 위원 6명 가운데 1명은 인하 소수의견을 냈다."]
        for fact in ("한국은행은 이번에 기준금리를 인하했다.", "한국은행은 이번에 기준금리를 내렸다.", "한국은행은 기준금리 인하를 결정했다.",
                     "금통위원 다수가 인하 의견을 냈다."):
            with self.subTest(fact):
                self.assertFalse(check("term", fact, texts))
        for fact in ("한국은행은 이번에 기준금리를 동결했다.", "금통위원 1명이 인하 소수의견을 냈다."):
            with self.subTest(fact):
                self.assertTrue(check("term", fact, texts))
        self.assertTrue(check("term", "연준은 기준금리를 인하했다.", ["연준이 금리를 0.25%p 내렸다. 추가 인하 기대는 줄었다."]))

    def test_one_post_cannot_widen_the_vocabulary(self):
        """읽힌 채널이 둘 이상이면 한 채널만 쓴 A · B급 낱말은 문장에 올 수 없다(항목의 낱말은 된다) — 심은 글 하나가 주제를 넓히지 못하게.
        '금리' 같은 C급 낱말은 한 글에만 있어도 된다(실제 문장 둘이 그 낱말 하나로 빠졌다)."""
        a, b = "국고 10년 입찰은 무난했다. 응찰률 247.4%.", "국고채 10년물 입찰 2.8조원. 오늘 밤 금통위가 긴급하게 열린다는 말도 있다."
        fact = "오늘 밤 금통위가 긴급하게 열리기로 했다."
        item = {"terms": ["국고채 입찰"], "words": [], "src": [("fxbond4", 640), ("fxbond5", 333)]}
        self.assertFalse(K.fact_checks(fact, item, [a, b])["term"])
        self.assertTrue(K.fact_checks(fact, item, [a + " 금통위 얘기도 돌았다.", b])["term"])       # 두 채널이 함께 쓴 낱말
        self.assertFalse(K.fact_checks(fact, {**item, "src": [("fxbond4", 640), ("fxbond4", 641), ("fxbond5", 333)]},
                                       [a, a, b])["term"])
        same = {**item, "src": [("fxbond5", 333), ("fxbond5", 334)]}                              # 한 채널의 글뿐이면 견줄 곳이 없다
        self.assertTrue(K.fact_checks(fact, same, [b, b])["term"])
        self.assertTrue(K.fact_checks("국고채 10년물 입찰이 무난하게 끝났다.", item, [a, b])["term"])
        self.assertEqual((R.grade_of("금통위"), R.grade_of("금리")), ("A", "C"))
        self.assertTrue(K.fact_checks("국고채 10년물 입찰의 낙찰 금리가 정해졌다.", item, [a + " 낙찰 금리는 4.365%.", b])["term"])


class NameMoreTest(unittest.TestCase):
    def test_latin_fragments_from_nowhere(self):
        """모델의 맥락에만 있던 토막(계정 이름 · 폴더 이름 같은 것) — 소문자든 숫자가 붙었든 읽힌 글에 없으면 버린다."""
        for fact in ("문의는 abcd1234 계정으로 받는다.", "이 내용은 userdata 폴더에 있었다.", "자료는 AppData 아래에 있었다.",
                     "미국 소비자물가는 qe2 때와 달랐다."):
            with self.subTest(fact):
                self.assertFalse(check("name", fact, TK.CPI, TK.CPI_ITEM))
        for fact in ("금리는 4bp 올랐고 스프레드는 0.5%p 벌어졌다.", "CPI 발표 뒤 금리가 올랐다.", "S&P 500 지수는 내렸다."):
            with self.subTest(fact):
                self.assertTrue(check("name", fact, TK.CPI, TK.CPI_ITEM))
        self.assertTrue(check("name", "fxbank 보고서가 인용됐다.", ["Fxbank 보고서가 인용됐다는 글."], NONE))


class BannedMoreTest(unittest.TestCase):
    def test_advice_and_outlook_in_other_words(self):
        cases = ("투자자는 장기채를 팔아야 한다.", "지금은 국고채를 담아야 한다.", "지금은 장기채를 사들일 때다.", "듀레이션을 늘릴 시점이다.",
                 "이번 조정은 채권을 살 기회다.", "국고채 10년물은 지금 살 만하다.", "국채선물은 롱 포지션이 맞다.", "금리는 연말까지 더 오른다.",
                 "금리가 더 오를 것이라는 관측이 많다.", "연내 인하 전망이 우세하다.", "다음 회의에서 인하가 예상됐다.", "이번 결정은 금리 하락 재료다.",
                 "이번 지표는 금리 상승 요인이다.", "이번 입찰 결과는 채권 가격에 부담이다.", "지금 금리 수준은 매력적이다.",
                 "투자자는 듀레이션을 늘려야 한다.", "금리는 당분간 높은 수준에 머문다.", "물가는 내년에 2%로 내려갈 것으로 봤다.")
        for fact in cases:
            with self.subTest(fact):
                self.assertEqual(K.fact_plain(fact), "banned")

    def test_ads(self):
        for fact in ("무료 리딩방은 goldroom 이름으로 찾는다.", "자세한 내용은 텔레그램에서 검색하면 나온다.", "구독 문의는 운영자에게 하면 된다.",
                     "오픈채팅 입장 코드는 따로 안내한다.", "이 채널은 선착순으로 회원을 받는다."):
            with self.subTest(fact):
                self.assertEqual(K.fact_plain(fact), "banned")

    def test_what_someone_said_is_a_fact(self):
        """글에 적힌 조심스러운 말을 그대로 옮긴 전언 — 단정으로 바꾸게 만들지 않는다."""
        for fact in ("참석자들은 추가 인상이 적절할 가능성이 크다고 평가했다.", "위원들은 물가 안정이 더 필요하다고 봤다.",
                     "일부 위원은 긴축이 고용에 충격을 줄 수 있다고 우려했다.", "몇몇 참석자는 금리를 더 높여야 한다고 주장했다.",
                     "한은 총재는 신중한 입장을 유지했다.", "응찰률은 247.4%인 것으로 집계됐다.", "다음 회의는 11월로 예정됐다."):
            with self.subTest(fact):
                self.assertIsNone(K.fact_plain(fact))
        for fact in ("추가 인상이 적절할 가능성이 크다.", "물가 안정이 더 필요하다.", "긴축은 고용에 충격을 줄 수 있다.", "금리를 더 높여야 한다.",
                     "위원들은 채권을 사야 한다고 말했다.", "총재는 지금이 장기채를 살 기회라고 말했다."):
            with self.subTest(fact):
                self.assertEqual(K.fact_plain(fact), "banned")


class LooseTest(unittest.TestCase):
    def test_an_uploaded_layer_can_be_read_without_the_sentence_rules(self):
        """올라가 있는 파일을 형식만 보는 읽기 — 문장 규칙이나 출처 목록이 그 뒤에 바뀌어도 규칙판의 문이 되지 않게(화면이 다시 가린다)."""
        item = TK.doc()["items"][0]
        old = TK.doc(items=[{**item, "fact": "연준은 연내 금리를 내릴 것이다."}])               # 지금 규칙으로는 금지 낱말에 걸리는 문장
        with self.assertRaises(ValueError):
            K.validate_picks(old)
        self.assertIs(K.validate_picks(old, plain=False), old)
        for name, d in {"꺾쇠": TK.doc(items=[{**item, "fact": "미국 <b>물가</b>가 올랐다."}]), "너무 김": TK.doc(items=[{**item, "fact": "가" * 141}]),
                        "문자열이 아님": TK.doc(items=[{**item, "fact": None}]), "형식": TK.doc(mode="rules")}.items():
            with self.subTest(name), self.assertRaises(ValueError):
                K.validate_picks(d, plain=False)

    def test_same_basis_reads_the_date(self):
        """날짜만 다르고 물음이 같은 파일 — 다른 판의 것이니 다시 묻는다."""
        d = TK.doc()
        other = {**d, "date": "2026-10-09", "items": [], "dropped": {c: 0 for c in K.CODES}}
        self.assertEqual(other["basis"], K.basis(F.EDITION, TK.ASKED))
        self.assertTrue(K.same_basis(d, F.EDITION, TK.ASKED))
        self.assertFalse(K.same_basis(other, F.EDITION, TK.ASKED))


if __name__ == "__main__":
    unittest.main()
