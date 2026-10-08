#!/usr/bin/env python3
"""저녁판 규칙(digest_rules) 테스트 — 숫자 표가 설계의 예시와 맞는지, 사전이 엉뚱한 글자에 걸리지 않는지, 숫자를 한 꼴로 맞추는지.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요 — 보기 문장은 전부 지어낸 것이다.
"""
import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_rules as R

TH = R.TH


def terms(text):
    return [h["term"] for h in R.match_terms(text)]


def nums(text):
    return [h["v"] for h in R.find_nums(text)]


def group_score(group, n):
    """설계 4절의 C: 그룹의 첫 채널 w, 둘째부터 0.5w, 그룹 상한 2w."""
    w = TH["w"][group]
    return min(w + (n - 1) * TH["w_next"] * w, TH["w_group_cap"] * w) if n else 0


class NumbersTableTest(unittest.TestCase):
    def test_caps_add_up(self):
        self.assertEqual(sum(TH["w_group_cap"] * w for w in TH["w"].values()) + TH["w_wire"], TH["c_cap"])
        self.assertEqual(TH["x_bond_plus"] + TH["x_all"], TH["x_cap"])
        self.assertEqual(TH["k"]["A"] + TH["k_result"], TH["k_cap"])
        self.assertEqual(max(TH["e"].values()), TH["e_cap"])
        self.assertEqual(max(v for _, v in TH["m_steps"]), TH["m_cap"])
        self.assertEqual(sum(TH[k] for k in ("c_cap", "x_cap", "k_cap", "e_cap", "m_cap", "y_cap")), TH["s_max"])
        self.assertEqual(TH["p_repeat"] + TH["p_fwd"] + TH["p_c_only_etc"], TH["p_cap"])
        self.assertEqual((TH["w"]["bond"], TH["w"]["analyst"], TH["w"]["personal"]), (2.0, 1.0, 0.5))
        self.assertEqual((TH["w_wire"], TH["gate_s"]), (0.25, 5.0))

    def test_design_examples(self):
        # 미 고용 발표일: 채권 3 · 애널 2 · 개인 3 · 속보형 → C 6.75, 세 그룹 X 1.5, A급 + 결과 낱말 K 2.25, 일정 E 2.0 = 12.5
        c = group_score("bond", 3) + group_score("analyst", 2) + group_score("personal", 3) + TH["w_wire"]
        self.assertEqual((group_score("bond", 3), group_score("analyst", 2), group_score("personal", 3), c), (4.0, 1.5, 1.0, 6.75))
        self.assertEqual(c + TH["x_cap"] + TH["k_cap"] + TH["e"]["A"], 12.5)
        # 채권 1곳만 쓴 국고 5년 입찰: 2.0 + B 1.0 + 일정 B 1.0 = 4.0 탈락, 2곳이면 5.0 통과
        self.assertLess(group_score("bond", 1) + TH["k"]["B"] + TH["e"]["B"], TH["gate_s"])
        self.assertEqual(group_score("bond", 2) + TH["k"]["B"] + TH["e"]["B"], TH["gate_s"])
        # 개인 4곳 + 속보형이 돌린 소문: 1.0 + 0.25 + B 1.0 = 2.25 탈락
        self.assertEqual(group_score("personal", 4) + TH["w_wire"] + TH["k"]["B"], 2.25)

    def test_collection_and_public_limits(self):
        self.assertEqual((TH["pause_s"], TH["timeout_s"], TH["max_requests"], TH["budget_s"]), (3.0, 20, 30, 360))
        self.assertEqual((TH["edition_shift_h"], TH["window_first_h"], TH["window_max_h"]), (6, 24, 96))
        self.assertEqual((TH["min_bond_ok"], TH["min_total_ok"], TH["min_text_ratio"], TH["empty_streak_fail"]), (3, 16, 0.5, 3))
        self.assertEqual((TH["must_max"], TH["cell_max"], TH["nums_max"], TH["links_max"], TH["links_personal_max"]), (3, 2, 3, 6, 2))
        self.assertEqual((TH["rest_max"], TH["rows_per_channel"], TH["bytes_max"], TH["keep_days"]), (30, 5, 60_000, 35))
        self.assertEqual((TH["lead_chars"], TH["min_chars"], TH["jaccard_min"], TH["contain_min"]), (80, 20, 0.55, 0.80))
        self.assertEqual((TH["num_key_hours"], TH["topic_key_hours"], TH["cluster_max_posts"]), (18, 12, 40))
        self.assertEqual((TH["num_key_nums"], TH["num_term_chars"], TH["row_digits_max"], TH["row_pp_max"]), (2, 40, 6, 5.0))
        self.assertEqual(TH["row_term_chars"], 20)
        self.assertEqual((TH["run_kst"], TH["late_kst"]), ("17:41", "22:41"))

    def test_cells(self):
        self.assertEqual(len(R.CELLS), 8)
        self.assertEqual(R.cell_id("통화정책", "글로벌"), "통화정책/글로벌")
        self.assertEqual((R.cell_id("기술적", "국내"), R.cell_id("기타", "글로벌")), ("기술적", "기타"))
        self.assertEqual({R.cell_id(f, r) for f in R.FACTORS for r in R.REGIONS}, set(R.CELLS))
        for bad in (("금리", "국내"), ("수급", "한국"), ("수급", None)):
            with self.assertRaises(ValueError):
                R.cell_id(*bad)
        self.assertEqual((tuple(R.GROUPS), R.GROUP_ORDER), (("bond", "analyst", "personal"),) * 2)
        self.assertEqual(tuple(R.ROLES), ("source", "wire", "topic", "context", "off"))


class LexiconTest(unittest.TestCase):
    def test_table_is_well_formed(self):
        names = [e["term"] for e in R.LEXICON]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(160 <= len(names) <= 210, len(names))        # 2026-10-08 저녁에 47개를 더했다(test_digest_words.py)
        for e in R.LEXICON:
            self.assertIn(e["grade"], R.GRADES, e["term"])
            self.assertIn(R.cell_id(e["factor"], e["region"]), R.CELLS, e["term"])
            self.assertTrue(e["pats"] and set(e["tags"]) <= {R.TOPIC_TAG, R.RATE_TAG}, e["term"])
            self.assertTrue(0 < len(e["term"]) <= 12 and e["term"] == e["term"].strip(), e["term"])
        self.assertEqual({R.cell_id(e["factor"], e["region"]) for e in R.LEXICON}, set(R.CELLS))        # 여덟 칸 모두에 낱말이 있다

    def test_grades_follow_the_design(self):
        a = sorted(e["term"] for e in R.LEXICON if e["grade"] == "A")
        self.assertEqual(a, sorted(["FOMC", "금통위", "미 CPI", "미 PCE", "미 고용", "한국 CPI", "한국 GDP", "국고채 발행계획"]))
        for term in ("연준 발언", "한은 발언", "미 PPI", "ISM", "국고채 입찰", "미 국채 입찰", "외국인 국채선물", "WGBI", "유가", "커브",
                     "설비투자 금액", "Capex 가이던스", "AI 회사채 발행"):
            self.assertEqual(R.grade_of(term), "B", term)
        for term in ("AI Capex", "원/달러 환율", "신용 스프레드", "관세"):
            self.assertEqual(R.grade_of(term), "C", term)
        self.assertEqual(R.best_grade(["관세", "커브", "미 CPI"]), "A")
        self.assertEqual((R.best_grade(["관세", "커브"]), R.best_grade(["관세"]), R.best_grade([])), ("B", "C", None))
        self.assertTrue(R.has_tag(["관세", "AI Capex"], R.TOPIC_TAG) and R.has_tag(["커브"], R.RATE_TAG))
        self.assertFalse(R.has_tag(["관세", "미 CPI"], R.TOPIC_TAG) or R.has_tag(["미 CPI"], R.RATE_TAG))

    def test_made_up_sentences(self):
        cases = {
            "미 CPI 9월 전년 대비 3.1%로 예상 상회": ["미 CPI"],
            "간밤 미국의 소비자물가가 예상을 웃돌았다": ["미 CPI"],
            "CPI 헤드라인이 높게 나왔다": ["미 CPI"],
            "한국 9월 소비자물가 2.1% 상승": ["한국 CPI"],
            "통계청이 내놓은 9월 소비자물가": ["한국 CPI"],
            "비농업 고용 25.4만 명, 실업률 4.1%": ["미 고용"],
            "FOMC에서 금리를 동결했다": ["FOMC", "금리"],
            "FOMC 의사록이 공개됐다": ["연준 의사록"],
            "연준 이사가 인하를 서두르지 않겠다고 했다": ["연준 발언"],
            "금통위가 기준금리를 동결": ["금통위", "기준금리"],
            "금통위 의사록에서 소수의견 확인": ["금통위 의사록", "소수의견"],
            "한은 총재 기자간담회": ["한은 발언"],
            "한국은행은 성장률 전망을 유지": ["한은"],
            "국고채 발행계획이 나왔다": ["국고채 발행계획"],
            "국고 10년 입찰 응찰률이 높았다": ["국고채 입찰"],
            "미 30년물 입찰은 부진했다": ["미 국채 입찰"],
            "외국인이 10년 국채선물 순매수로 돌아섰다": ["외국인 국채선물"],
            "WGBI 편입 일정": ["WGBI"],
            "WTI가 배럴당 80달러를 넘었다": ["유가"],
            "설비투자 85조원을 제시": ["설비투자 금액"],
            "Capex 가이던스를 올렸다": ["Capex 가이던스"],
            "AI 데이터센터용 회사채 발행이 늘었다": ["AI 회사채 발행"],
            "원/달러 환율이 올랐다": ["원/달러 환율"],
            "관세 협상이 길어진다": ["관세"],
            "커브가 가팔라졌다": ["커브"],
            "미 국채 10년 금리가 올랐다": ["미 국채 금리"],
            "스테이블코인 법안 논의": ["스테이블코인"],
        }
        for text, want in cases.items():
            with self.subTest(text):
                self.assertEqual(terms(text), want)

    def test_words_that_only_look_alike(self):
        for text in ("배터리 고용량 셀 양산", "유가증권시장 상장사", "유가족에게 위로를", "고용노동부 발표", "권한은 위원회에 있다",
                     "신한은행 창구", "소통방식을 바꿨다", "흥미 있는 입찰 공고", "공사 입찰 담합", "인상적인 발표였다", "", None):
            with self.subTest(text):
                self.assertEqual([t for t in terms(text) if R.grade_of(t) in ("A", "B")], [])
        self.assertEqual(terms("의미 있는 숫자였다"), [])
        self.assertNotIn("미 국채 입찰", terms("의미 있는 입찰이었다"))                  # '의미'의 미는 미국이 아니다
        # 나라를 안 밝힌 '입찰'은 국고채 입찰로 세지 않는다 — 해외 채권 글의 입찰이 국고채 입찰 일정(E)과 맞아 버린다.
        # 국채·만기가 붙은 입찰은 지역을 정하지 않는 '국채 입찰'(수급/글로벌, B급)로 센다. 보기 문장은 전부 지어낸 것이다
        for text in ("10년물 국채 입찰 얘기를 지어낸 한 줄", "국채 입찰 수요를 다룬 지어낸 한 줄", "7년물 입찰 응찰률 9.9배라는 지어낸 숫자"):
            with self.subTest(text):
                self.assertEqual([t for t in terms(text) if R.grade_of(t) in ("A", "B")], ["국채 입찰"])
        for text in ("전파 대역을 입찰로 나눈다는 지어낸 이야기", "공사 입찰 담합", "국채 입찰 공고가 났다는 지어낸 말"):
            with self.subTest(text):
                self.assertFalse({"국고채 입찰", "국채 입찰"} & set(terms(text)))
        self.assertEqual((R.TERMS["국채 입찰"]["factor"], R.TERMS["국채 입찰"]["region"]), ("수급", "글로벌"))
        self.assertEqual(terms("국고 30년 입찰을 지어낸 예문"), ["국고채 입찰"])           # 더 긴 자리(나라를 밝힌 쪽)가 이긴다
        self.assertEqual(terms("오늘 국고채 10년물 입찰, 물가채 입찰은 내일"), ["국고채 입찰"])
        self.assertEqual(terms("미 국채 7년물 입찰을 지어낸 예문"), ["미 국채 입찰"])
        # 입찰 결과를 '입찰'이라는 말 없이 쓴 글(응찰률 · 낙찰금리 · 프라이머리딜러)도 '국채 입찰'로 센다. 나라를 밝힌 입찰 낱말이
        # 같은 글에 있으면 그쪽만 센다 — 한 글에 국내·글로벌 입찰 낱말이 겹쳐 붙지 않게
        for text in ("응찰률 2.5배로 끝났다는 지어낸 한 줄", "프라이머리딜러 배정이 늘었다는 지어낸 말", "낙찰금리가 높게 나왔다는 지어낸 말"):
            with self.subTest(text):
                self.assertEqual([t for t in terms(text) if R.grade_of(t) in ("A", "B")], ["국채 입찰"])
        self.assertEqual(terms("국고 10년 입찰 결과: 응찰률 247.4%, 낙찰금리 4.365%"), ["국고채 입찰", "금리"])
        self.assertEqual(terms("미 30년물 입찰은 부진했다. 응찰률이 낮았다"), ["미 국채 입찰"])
        self.assertEqual([h[0] for h in R.term_hits("국고 10년 입찰 응찰률 247.4%")], ["국고채 입찰"])       # 숫자의 짝도 나라를 밝힌 쪽
        self.assertEqual(terms("FOMC 회의록을 지어낸 예문"), ["연준 의사록"])             # 의사록을 회의록이라고도 쓴다
        self.assertNotIn("금통위", terms("신한은행 기준금리 인하"))
        self.assertNotIn("미 고용", terms("한국 9월 고용 동향"))
        self.assertIn("한국 고용", terms("한국 9월 고용 동향"))

    def test_lookalikes_seen_in_the_pilot(self):
        """시범 수집에서 잘못 걸린 꼴 — 보기 문장은 전부 지어낸 것이다."""
        for text in ("골드만삭스가 냈다는 지어낸 보고서", "골드필즈라는 지어낸 회사 이름", "그렇게 된 이유가 무엇인지 묻는 지어낸 글"):
            with self.subTest(text):
                self.assertEqual(terms(text), [])
        self.assertEqual(terms("골드 가격이 올랐다는 지어낸 말"), ["금"])
        for text in ("유가가 올랐다는 지어낸 말", "국제유가 급등", "고유가 부담", "저유가 국면"):
            self.assertEqual(terms(text), ["유가"], text)
        for text in ("완전고용에 가깝다는 지어낸 평가", "최대고용 목표를 다룬 지어낸 문장", "고용이 늘었다는 지어낸 말"):
            self.assertNotIn("미 고용", terms(text), text)                              # 나라도 지표도 없는 '고용'은 세지 않는다
        for text in ("미 고용 지표가 나왔다", "신규 고용 25만명", "고용보고서를 기다린다", "실업률 4.1%", "미국 9월 고용이 식었다"):
            self.assertIn("미 고용", terms(text), text)
        self.assertNotIn("연준 발언", terms("연준 이사회가 지어낸 규정을 냈다"))            # 기관 이름
        self.assertIn("연준 발언", terms("연준 이사가 지어낸 말을 했다"))
        self.assertNotIn("외국인 국채선물", terms("외국인이 주식 현물과 선물 매도에 나섰다는 지어낸 시황"))    # 주식 선물
        self.assertIn("외국인 국채선물", terms("외인 3년 선물 순매도"))
        self.assertNotIn("국내 크레딧", terms("회사채 발행이 늘었다는 지어낸 해외 소식"))    # 나라를 알 수 없는 회사채 발행
        self.assertIn("국내 크레딧", terms("회사채 수요예측 결과"))
        self.assertIn("국내 크레딧", terms("원화 회사채 발행이 늘었다"))

    def test_a_long_run_of_digits_is_scanned_quickly(self):
        start = time.perf_counter()
        self.assertEqual(terms("9" * 4096), [])                                       # 숫자만 이어진 글(텔레그램 글 상한 길이)
        self.assertLess(time.perf_counter() - start, 0.1)

    def test_all_places_of_a_term_and_the_nearest_one_before_a_number(self):
        text = "미 CPI 발표를 앞둔 메모. " + "가" * 60 + " CPI 3.1%로 나왔다. 유가는 2.1% 내렸다."
        hits = R.term_hits(text)
        self.assertEqual([h[0] for h in hits], ["미 CPI", "미 CPI", "유가"])              # match_terms는 낱말마다 첫 자리만 준다
        self.assertEqual(terms(text), ["미 CPI", "유가"])
        at = {n["v"]: n["pos"] for n in R.find_nums(text)}
        self.assertEqual((R.named_before(hits, at["3.1%"]), R.named_before(hits, at["2.1%"])), ("미 CPI", "유가"))
        far = "미 CPI 얘기. " + "가" * (TH["num_term_chars"] + 1) + " 3.1%"
        self.assertIsNone(R.named_before(R.term_hits(far), R.find_nums(far)[0]["pos"]))     # 낱말이 멀면 짝이 아니다
        self.assertIsNone(R.named_before(R.term_hits("3.1%라는 숫자 뒤에 미 CPI"), 0))       # 숫자 뒤의 낱말도 짝이 아니다
        self.assertIsNone(R.named_before(R.term_hits("환율 얘기 끝에 3.1%"), 9))            # C급 낱말은 짝이 되지 않는다
        self.assertEqual(R.named_before(R.term_hits("설비투자 85조원 제시"), 5), "설비투자 금액")   # 숫자를 품은 낱말 자리
        mid = "유가 얘기. " + "가" * 25 + " 1.45%"                                              # 낱말 끝에서 30자 남짓
        at = R.find_nums(mid)[0]["pos"]
        self.assertEqual((R.named_before(R.term_hits(mid), at), R.named_before(R.term_hits(mid), at, TH["row_term_chars"])), ("유가", None))

    def test_a_longer_match_swallows_the_shorter_one_inside_it(self):
        self.assertEqual(terms("한국 CPI와 미국 CPI가 함께 나왔다"), ["한국 CPI", "미 CPI"])
        self.assertEqual(terms("한국 GDP 속보치"), ["한국 GDP"])
        self.assertEqual(terms("Capex 가이던스 상향. 설비투자 85조원 제시"), ["Capex 가이던스", "설비투자 금액"])   # 걸치기만 하면 둘 다 남는다
        self.assertEqual(terms("미 CPI 발표, 그리고 한국 CPI"), ["미 CPI", "한국 CPI"])

    def test_positions_are_counted_on_tidied_text(self):
        hit = R.match_terms("  \n\n미​ CPI 발표   " + "가" * 90 + " 금통위")
        self.assertEqual([(h["term"], h["pos"]) for h in hit], [("미 CPI", 0), ("금통위", 100)])
        self.assertEqual(R.norm_text("ＣＰＩ　３．１％\n\n상회"), "CPI 3.1% 상회")              # 전각 글자를 맞춘다
        self.assertEqual(R.norm_text(None), "")

    def test_result_words(self):
        got = [h["result"] for h in R.match_results("예상을 웃돌았다. 금리는 동결. 응찰률 247%, 낙찰금리 4.3%")]
        self.assertEqual(got, ["상회", "동결", "응찰률", "낙찰금리"])
        self.assertEqual([h["result"] for h in R.match_results("인상적인 첫인상")], [])
        self.assertTrue(set(R.RESULT_K) <= set(R.RESULT_WORDS))
        self.assertEqual(len(R.RESULT_WORDS), len(set(R.RESULT_WORDS)))
        self.assertFalse(set(R.RESULT_WORDS) & {"금리상방", "금리하방", "상방", "하방", "강세", "약세"})   # 규칙은 방향을 내지 않는다
        self.assertFalse(set(R.TERMS) & set(R.RESULT_WORDS))


class NumbersTest(unittest.TestCase):
    def test_one_form_for_the_same_number(self):
        self.assertEqual(nums("3.1%"), ["3.1%"])
        for text in ("3.10%", "3.1 %", "+3.1%", "3.1퍼센트", "３．１％"):
            self.assertEqual(nums(text), ["3.1%"], text)
        self.assertEqual(nums("5,418계약 순매수, 25.4만 명 증가, 2.8조 원 낙찰, 12조원, 100억 달러"),
                         ["5418계약", "25.4만명", "2.8조원", "12조원", "100억달러"])
        self.assertEqual(nums("25bp 인하, 0.25%p 인상, 50bps, 3.0%"), ["25bp", "0.25%p", "50bp", "3%"])
        self.assertEqual(nums("전일 대비 -4bp, (-0.7bp), −2.5bp"), ["-4bp", "-0.7bp", "-2.5bp"])
        self.assertEqual(nums("3-5% 구간, 2024-25년"), ["5%"])                           # 범위의 줄표는 부호가 아니다
        self.assertEqual(nums("3.1% 그리고 또 3.1%"), ["3.1%"])
        self.assertEqual([(h["v"], h["pos"]) for h in R.find_nums("가나 3.1%, 0.3%")], [("3.1%", 3), ("0.3%", 9)])

    def test_digits_of_other_scripts_are_not_numbers(self):
        """정규식의 숫자 기호(d)는 아라비아-인도 · 타이 · 데바나가리 숫자도 받는다 — 그런 글자가 '숫자'로 공개본에 실리면 안 된다."""
        for text in ("3.\u0663\u096d5%", "\u0663.5%", "8201012.\u0e52\u0e529원", "\u0968\u096bbp", "12\u0663%"):
            self.assertEqual(nums(text), [], ascii(text))
        for v in ("3.\u06635%", "\u0663%", "1\u0e52bp", "-\u0663.1%", "3.1\u0663%"):
            self.assertFalse(R.is_num(v), ascii(v))
        self.assertEqual(nums("\u0663 3.1%"), ["3.1%"])                                 # 떨어져 있는 보통 숫자는 그대로 읽는다
        self.assertFalse(R.is_phrase("채권 채널 \u0663곳"))
        self.assertTrue(all(c.isascii() for v in nums("\uff13\uff0e\uff11\uff05 그리고 \uff12\uff15\uff42\uff50") for c in v))   # 전각은 NFKC로 풀린다

    def test_numbers_a_single_channel_may_show(self):
        for v in ("3.1%", "25bp", "12.5조원", "4732계약", "0.4%p", "240.6%", "21.5만명"):
            self.assertTrue(R.solo_num_ok(v), v)
        for v in ("1234567.891명", "8201012원", "1234567%", "4.376%", "0.7bp", "1450원", "85달러", "25%p", "-7%p"):
            self.assertFalse(R.solo_num_ok(v), v)                                       # 긴 숫자 · 시세 수준 · 상식 밖의 %p

    def test_units_do_not_bite_into_words(self):
        for text in ("3원칙", "2조치", "10배율", "5억불", "1명분", "버전 3.1", "10년물", "A4용지 100%p수익", "GPT4 모델", "",
                     "전화 010-1234-5678", "2026-10-08", "12:30", "1,23%"):
            self.assertEqual([v for v in nums(text) if v not in ("100%p",)], [], text)
        self.assertEqual(nums("2조를 넘었고 3배나 늘어 7명이 반대, 1,450원대"), ["2조", "3배", "7명", "1450원"])

    def test_public_form(self):
        for v in ("3.1%", "-4bp", "0.25%p", "2.8조원", "5418계약", "25.4만명", "0%", "1450원", "100억달러", "3배"):
            self.assertTrue(R.is_num(v), v)
        for v in ("3.10%", "03%", "+3%", "3.1 %", "3.1", "%", "3.1%\n", "삼 %", "3.1234%", "12345678%", "3.1%p상승", None, 3.1):
            self.assertFalse(R.is_num(v), repr(v))
        self.assertEqual((R.num_unit("-4bp"), R.num_unit("25.4만명")), (("-4", "bp"), ("25.4", "만명")))
        with self.assertRaises(ValueError):
            R.num_unit("약 3%")

    def test_market_quotes(self):
        for v in ("4.376%", "0.7bp", "-4bp", "2.8bp", "1450원", "85달러"):
            self.assertTrue(R.is_quote(v), v)
        for v in ("3.1%", "0.3%", "25bp", "50bp", "2.8조원", "247.4%", "5418계약", "0.25%p", "100억달러"):
            self.assertFalse(R.is_quote(v), v)


class DropAndPhraseTest(unittest.TestCase):
    def test_drop_reasons(self):
        self.assertEqual((R.drop_code(""), R.drop_code(None), R.drop_code(" \n​ ")), ("empty",) * 3)
        self.assertEqual(R.drop_code("ㅋㅋ 대박"), "short")
        self.assertIsNone(R.drop_code("링크만 남깁니다", 1))                             # 짧아도 링크가 있으면 둔다
        self.assertEqual((R.drop_code("", 1), R.drop_code(None, 2)), (None, None))      # 주소뿐인 글(수집이 주소 글자를 본문에서 뺀다)도 둔다
        self.assertEqual(R.drop_code("무료 리딩방 회원 모집! 선착순 입장은 아래 링크", 1), "ad")
        self.assertEqual(R.drop_code("FOMC 해설 웨비나 신청 안내. 선착순 100명입니다"), "ad")       # 광고는 낱말이 있어도 버린다
        self.assertEqual(R.drop_code("비트코인 급등. 알트코인도 따라 오르는 중입니다"), "coin")
        self.assertEqual(R.drop_code("어느 회사가 유상증자 공시를 냈다고 합니다. 참고"), "filing")
        self.assertIsNone(R.drop_code("미 CPI 발표 뒤 비트코인도 흔들렸다는 이야기입니다"))          # A·B급 낱말이 있으면 둔다
        self.assertIsNone(R.drop_code("스테이블코인 법안이 미 국채 수요에 주는 영향 정리"))
        self.assertIsNone(R.drop_code("오늘 장은 조용했다. 내일 다시 정리해 보겠습니다."))
        self.assertEqual(set(R.DROP_CODES), {"empty", "short", "ad", "coin", "filing"})

    def test_fixed_phrases(self):
        self.assertEqual(R.phrase("why_bond", n=3), "채권 채널 3곳")
        self.assertEqual(R.phrase("why_all"), "세 그룹 모두")
        for code, template in R.PHRASES.items():
            text = R.phrase(code, n=7) if "{n}" in template else R.phrase(code)
            self.assertTrue(R.is_phrase(text), code)
        for bad in ("채권 채널 0곳", "채권 채널 세곳", "채권 채널 3곳 ", "채권 채널 3곳\n", "채권 채널 1234곳", "세 그룹 모두!", "", None, 3):
            self.assertFalse(R.is_phrase(bad), repr(bad))
        for code, slots in (("why_bond", {}), ("why_bond", {"n": "3"}), ("why_bond", {"n": 0}), ("why_all", {"n": 3}),
                            ("why_bond", {"n": 3, "x": 1}), ("why_bond", {"n": True})):
            with self.assertRaises(ValueError):
                R.phrase(code, **slots)
        with self.assertRaises(KeyError):
            R.phrase("why_nothing")
        self.assertFalse(set(R.DIRS + R.CURVES + R.BASES) & set(R.TERMS))
        self.assertIn("물가채", R.TENORS)


if __name__ == "__main__":
    unittest.main()
