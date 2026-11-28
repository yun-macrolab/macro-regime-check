#!/usr/bin/env python3
"""저녁판 AI 요약을 넓힌 것(2026-11-28 E3)의 검사 테스트 — 항목 문장 220자 · 3문장에 맞춘 기준, 오늘 판 한 단락(overview)의 여섯 검사 ·
파일의 칸 · 화면이 붙이는 규칙(attach_overview).

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 · 모델 호출이 없다. 글과 문장은 모두 지어낸 것이다(fixtures.py와 아래 상수).
"""
import copy
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_picks as K
import digest_rules as R
import digest_schema as S
import evening_llm as L
import fixtures as F

TH = R.TH
CPI, AUCTION, CARD = "f:e7b13565420b", "n:f4afc845c5b8", "t:dc5468f7dee6"
GOOD = {CPI: "미국 9월 소비자물가는 전년 대비 3.1% 올라 예상을 웃돌았다. 근원 지수는 전월 대비 0.3% 상승했다.",
        AUCTION: "10년 만기 국고채 2.8조원이 응찰률 247.4%로 낙찰됐다.", CARD: "한은 총재가 가계부채 문제를 다시 꺼냈다."}
# 지어낸 한 단락 — 위 세 문장과 규칙판 줄에 있는 숫자 · 낱말 · 이름만 쓴다(실제 채널 글이 아니다)
OVERVIEW = ("오늘 판은 미국 물가 지표와 국고채 입찰, 한은 총재의 발언이 함께 다뤄졌다. 미국 9월 소비자물가는 3.1% 올랐고 "
            "10년 만기 국고채 입찰에서는 2.8조원이 낙찰됐다. 물가 항목은 채권 3곳과 애널 2곳이 다뤘다.")
# 지어낸 원문 한 줄(베낌 기준을 볼 때만 쓴다)
POST = "| 미 9월 CPI 전년비 3.1% 상승해 컨센 상회, 근원은 전월비 0.3% 상승으로 시장 예상에 부합했고 주거비가 끌어올렸다는 평가"

# 교차 검토(2026-11-28)의 재현 입력 — 지어낸 원문 한 문장과, 그 문장을 그대로 넣고 다른 두 문장을 덧붙인 150자 출력
SHORT_POST = "지역별 자금흐름을 점검했다."
DILUTED = ("지역별 자금흐름을 점검했다. 회의에서는 자료의 작성 절차와 집계 대상의 범위를 구분해 설명하고 담당 부서에서 제출한 문서의 구성과 "
           "각 부록에 수록한 표의 작성 과정을 차례로 소개했다. 참석자들은 각 표의 작성 시점과 공표 방식에 관한 설명을 듣고 관련 기록을 정리했다.")

_DIGEST = []


def digest():
    if not _DIGEST:
        _DIGEST.append(F.digest())                                                    # 만드는 데 시간이 걸린다 — 한 번만
    return copy.deepcopy(_DIGEST[0])


def rows(keys=(CPI, AUCTION, CARD)):
    """한 단락의 입력 — [(규칙판 항목, 실린 문장)] (evening_llm.overview_rows가 고르는 것과 같은 차례)."""
    return L.overview_rows(digest(), [{"key": k} for k in keys], {k: GOOD[k] for k in keys})


def doc(overview=OVERVIEW, keys=(CPI, AUCTION, CARD)):
    """한 단락이 실린 요약 층 — 꼭 볼 것 세 건의 문장이 모두 실린 날."""
    asked = []
    for x in digest()["must"]:
        if x["key"] in keys:
            read = [ln for ln in x["links"] if not ln["fwd"] and F.ROLE[ln["ch"]] == "source" and F.GROUP[ln["ch"]] in ("bond", "analyst")]
            asked.append({"key": x["key"], "id": x["id"], "src": [[ln["ch"], int(ln["url"].rsplit("/", 1)[1])] for ln in read[:3]]})
    return K.picks_doc(F.EDITION, F.PICKS_AT, "claude-fx-1", asked, {k: GOOD[k] for k in keys}, None, overview)


class LimitTest(unittest.TestCase):
    """한도 — 전/후를 숫자로 묶어 둔다(README '저녁판(시범)'의 'AI 요약' 절과 같아야 한다)."""

    def test_the_new_limits(self):
        self.assertEqual((TH["llm_items_max"], TH["llm_rest_sources"], TH["llm_posts_max"], TH["llm_post_chars"], TH["llm_requests"]),
                         (10, 1, 3, 1500, 20))
        self.assertEqual((TH["fact_chars"], TH["fact_sentences"]), (220, 3))
        self.assertEqual((TH["overview_chars"], TH["overview_min_chars"], TH["overview_sentences_min"], TH["overview_sentences"],
                          TH["overview_items_min"]), (300, 60, 2, 4, 2))

    def test_copy_and_number_limits_did_not_move(self):
        """베낌 · 숫자 기준은 길이와 무관하게 그대로다 — 절대 수(copy_run · copy_stems)는 문장이 길어져도 느슨해지지 않는다."""
        self.assertEqual((TH["copy_run"], TH["copy_gram"], TH["copy_ratio"], TH["copy_stems"], TH["copy_piece"], TH["copy_cover"],
                          TH["num_ctx_chars"]), (20, 3, 0.6, 5, 10, 0.5, 12))

    def test_a_full_layer_fits_the_size_cap(self):
        fact = ("가" * (TH["fact_chars"] - 2)) + "다."
        items = [{"key": f"k:{i:012x}", "id": f"20261008-fxbond1-{500 + i}", "src": [["fxbond1", 500 + i], ["fxbond2", 200 + i],
                                                                                       ["fxanal1", 50 + i]], "fact": fact}
                 for i in range(TH["llm_items_max"])]
        full = {**doc(), "items": items, "overview": "가" * (TH["overview_chars"] - 2) + "다."}
        self.assertLess(len(S.dump(full).encode("utf-8")), TH["picks_bytes_max"])


class LongFactTest(unittest.TestCase):
    """220자 · 3문장 문장에서도 검사가 같은 자리에서 걸린다."""

    def setUp(self):
        self.item = {"terms": ["미 CPI"], "words": [], "src": [("fxbond1", 1)]}

    def long_fact(self, middle):
        return "미국 9월 소비자물가 발표가 나왔다. " + middle + " 여러 글은 주거비와 근원 지수를 함께 다뤘다."

    def test_three_sentences_and_220_chars_pass_the_shape(self):
        fact = self.long_fact("근원 지수는 전월 대비 0.3% 상승했다.")
        self.assertIsNone(K.fact_plain(fact))
        self.assertIsNone(K.fact_plain(fact[:-1] + " " + "가" * (TH["fact_chars"] - len(fact) - 2) + "다."))
        self.assertEqual(K.fact_plain(fact + " 환율은 그대로였다."), "shape")                         # 네 문장
        self.assertEqual(K.fact_plain("가" * TH["fact_chars"] + "다."), "shape")

    def test_a_20_char_run_is_still_a_copy_in_a_long_fact(self):
        text = POST
        run = "근원은전월비0.3%상승으로시장예상에부합했"                          # 공백 · 문장부호를 빼면 20자 넘게 원문과 이어진다
        self.assertGreaterEqual(len(K._flat(run)), TH["copy_run"])
        copied = self.long_fact("근원은 전월비 0.3% 상승으로 시장 예상에 부합했다.")
        self.assertFalse(K.ok_copy(copied, [text]))
        mine = self.long_fact("근원 지수는 전월 대비 0.3% 올라 시장의 예상과 같았다.")
        self.assertTrue(K.ok_copy(mine, [text]))

    def test_a_short_copied_sentence_is_not_diluted_by_the_others(self):
        """교차 검토(2026-11-28)의 재현 — 20자 미만인 원문의 완결 문장을 그대로 넣고 다른 문장을 덧붙여 비율을 희석한 출력(지어낸 글)."""
        self.assertEqual(len(DILUTED), 150)
        self.assertFalse(K.ok_copy(SHORT_POST, [SHORT_POST]))
        checks = K.fact_checks(DILUTED, {"terms": [], "words": []}, [SHORT_POST])
        self.assertEqual(checks, {**{c: True for c in K.CHECKS}, "copy": False})       # 전에는 여섯 검사를 모두 통과했다
        self.assertFalse(K.ok_copy("지역별 자금 흐름을 점검했다. " + DILUTED.split(". ", 1)[1], [SHORT_POST]))   # 띄어쓰기만 바꿔도
        self.assertFalse(K.ok_copy(DILUTED.split(". ", 1)[1] + " 지역별 자금흐름을 점검했다.", ["| 회의 메모\n| 지역별 자금흐름을 점검했다"]))
        mine = "회의에서는 지역마다 돈이 어디로 움직였는지를 살폈다. " + DILUTED.split(". ", 1)[1]
        self.assertTrue(K.ok_copy(mine, [SHORT_POST]))                               # 자기 말로 쓴 문장은 걸리지 않는다

    def test_five_stems_in_order_is_still_a_copy(self):
        text = "| 연준 위원들은 고용 둔화와 물가 둔화를 함께 거론하며 속도 조절을 언급했다"
        fact = self.long_fact("연준 위원들이 고용 둔화와 물가 둔화를 들었다.")
        self.assertFalse(K.ok_copy(fact, [text]))                                    # 조사만 바꾼 다섯 어절
        self.assertTrue(K.ok_copy(self.long_fact("연준에서는 물가와 고용이 함께 식는다는 말이 나왔다."), [text]))

    def test_the_third_sentence_is_checked_like_the_first(self):
        base = "미국 9월 소비자물가 발표가 나왔다. 근원 지수는 전월 대비 0.3% 상승했다. "
        self.assertEqual(K.fact_plain(base + "금리는 연말까지 오를 것으로 보인다."), "banned")        # 셋째 문장의 전망도 걸린다
        self.assertEqual(K.fact_plain(base + "지금 장기채를 매수할 만하다."), "banned")
        self.assertIsNone(K.fact_plain(base + "연말 금리 경로를 두고 여러 글이 엇갈렸다."))             # 지난 일로 맺었다
        self.assertFalse(K.ok_number(base + "근원은 0.4% 올랐다.", [POST]))                          # 셋째 문장의 숫자도 원문과 견준다


class OverviewCheckTest(unittest.TestCase):
    """오늘 판 한 단락 — 여섯 검사가 항목 문장과 같고, 숫자 · 낱말 · 이름은 실린 문장과 규칙판 줄에서만 찾는다."""

    def test_the_example_passes_every_check(self):
        self.assertEqual(K.overview_checks(OVERVIEW, rows(), [POST]), {c: True for c in K.CHECKS})
        self.assertIsNone(K.overview_code(OVERVIEW, rows(), [POST], K.names_of(F.sources())))

    def test_too_few_items_or_nothing_written(self):
        self.assertEqual(K.overview_code(OVERVIEW, rows((CPI,)), []), "none")                      # 실린 문장이 하나뿐인 날은 묻지 않는다
        self.assertEqual(K.overview_code(None, rows(), []), "none")

    def test_shape(self):
        cases = {"한 문장": "오늘 판은 미국 물가 지표와 국고채 입찰, 한은 총재의 발언이 함께 다뤄졌다.",
                 "다섯 문장": OVERVIEW + " 입찰은 2.8조원이었다. 물가는 3.1%였다.",
                 "너무 김": OVERVIEW[:-1] + " " + "가" * (TH["overview_chars"] - len(OVERVIEW)) + "다.",
                 "너무 짧음": "물가가 올랐다. 입찰이 끝났다.", "주소": OVERVIEW + " 자세한 것은 t.me/fxbond1/501 에 있다.",
                 "채널 이름": OVERVIEW.replace("물가 항목은", "fxbond1 쪽은")}
        names = K.names_of(F.sources())
        for name, text in cases.items():
            with self.subTest(name):
                self.assertEqual(K.overview_code(text, rows(), [], names), "shape")

    def test_banned(self):
        for tail in ("금리는 더 오를 것으로 보인다.", "장기채를 매수할 기회다.", "물가 발표는 채권에 부담이다.", "연말에는 인하가 이어진다."):
            with self.subTest(tail):
                self.assertEqual(K.overview_code(OVERVIEW + " " + tail if len(OVERVIEW) + len(tail) < 300 else tail, rows(), []), "banned")

    def test_copy_of_a_fact_or_a_post(self):
        stitched = GOOD[CPI] + " " + GOOD[AUCTION]                                   # 실린 문장을 이어 붙였을 뿐이다
        self.assertEqual(K.overview_code(stitched, rows(), []), "copy")
        via = "오늘 판은 물가가 중심이었다. 근원은 전월비 0.3% 상승으로 시장 예상에 부합했다. 입찰도 함께 다뤄졌다."
        self.assertEqual(K.overview_code(via, rows(), [POST]), "copy")              # 원문 토막이 20자 넘게 이어졌다
        self.assertIsNone(K.overview_code(OVERVIEW, rows(), [POST]))
        empty = [({"terms": []}, "자료 작성 과정을 설명했다."), ({"terms": []}, "참석자들이 문서를 정리했다.")]
        self.assertEqual(K.overview_code(DILUTED, empty, [SHORT_POST]), "copy")      # 교차 검토의 재현 — 단락도 문장마다 본다(전에는 None)
        self.assertEqual(K.overview_code("오늘 판은 여러 자료가 함께 다뤄졌다. " + GOOD[AUCTION] + " 다른 항목도 같이 실렸다.", rows(), []), "copy")

    def test_numbers_must_be_in_the_facts_or_the_board(self):
        for wrong in ("3.2%", "3.1bp", "4곳"):
            text = OVERVIEW.replace("3.1%" if wrong != "4곳" else "3곳", wrong)
            with self.subTest(wrong):
                self.assertEqual(K.overview_code(text, rows(), []), "number")
        board_only = OVERVIEW.replace("물가 항목은 채권 3곳과 애널 2곳이 다뤘다.", "입찰 항목은 응찰률 247.4%를 적었다.")
        self.assertIsNone(K.overview_code(board_only, rows(), []))                  # 규칙판 줄에 있는 숫자는 된다
        self.assertEqual(K.overview_code(OVERVIEW.replace("3.1%", "예상 3.1%"), rows(), []), "number")   # 꼬리표도 같아야 한다

    def test_terms_and_names_must_come_from_the_items(self):
        wgbi = OVERVIEW.replace("물가 항목은", "WGBI 편입과 물가 항목은")
        self.assertIn(K.overview_code(wgbi, rows(), []), ("term", "name"))           # 고른 항목에 없는 주제 · 약어
        person = OVERVIEW.replace("한은 총재의", "홍길동 총재의")
        self.assertEqual(K.overview_code(person, rows(), []), "name")
        flipped = OVERVIEW.replace("3.1% 올랐고", "3.1% 내렸고")
        self.assertEqual(K.overview_code(flipped, rows(), []), "term")              # 방향을 문장과 반대로


class OverviewFileTest(unittest.TestCase):
    """data/digest_picks.json의 overview 칸 — null 또는 검사를 통과한 한 단락. 없는 파일(11-28 앞)도 읽는다."""

    def test_the_field(self):
        d = K.validate_picks(doc(), F.sources())
        self.assertEqual(d["overview"], OVERVIEW)
        self.assertIsNone(K.validate_picks(doc(None), F.sources())["overview"])
        self.assertIsNone(K.blank_picks(F.EDITION, F.PICKS_AT)["overview"])
        old = doc()
        del old["overview"]                                                          # 넓히기 앞에 올라간 파일
        self.assertIs(K.validate_picks(old), old)
        self.assertIs(K.validate_picks(old, plain=False), old)

    def test_bad_overviews_are_refused(self):
        cases = {"권유": doc(OVERVIEW.replace("함께 다뤄졌다.", "함께 다뤄져 매수할 기회다.")), "너무 김": doc("가" * 300 + "다."),
                 "문자열이 아님": doc(31), "한 항목뿐": doc(OVERVIEW, (CPI,)), "꺾쇠": doc(OVERVIEW.replace("오늘", "<b>오늘</b>"))}
        for name, d in cases.items():
            with self.subTest(name), self.assertRaises(ValueError):
                K.validate_picks(d)
        with self.assertRaises(ValueError):
            K.validate_picks(cases["너무 김"], plain=False)                           # 형식만 보는 읽기도 길이는 본다
        loose = doc(OVERVIEW.replace("함께 다뤄졌다.", "함께 다뤄져 매수할 기회다."))
        self.assertIs(K.validate_picks(loose, plain=False), loose)                   # 문장 규칙은 화면 · 다음 실행이 다시 가린다


class OverviewAttachTest(unittest.TestCase):
    """화면이 한 단락을 붙이는 규칙(파이썬 판) — 실린 항목 문장이 모두 이 판에 붙고 숨긴 것이 없을 때만."""

    def test_attached_only_when_every_item_attaches(self):
        d, src = digest(), F.sources()
        self.assertEqual(K.attach_overview(d, doc(), src), OVERVIEW)
        self.assertIsNone(K.attach_overview(d, doc(None), src))
        later = copy.deepcopy(d)
        later["must"] = later["must"][:2]                                            # 다시 계산한 판에서 한 항목이 빠졌다
        self.assertIsNone(K.attach_overview(later, doc(), src))
        self.assertIsNone(K.attach_overview({**d, "date": "2026-10-09"}, doc(), src))
        self.assertIsNone(K.attach_overview({**d, "status": "withdrawn"}, doc(), src))

    def test_hidden_items_and_channels_take_it_down(self):
        d, src = digest(), F.sources()
        for hold in (F.overrides(hide_ids=[d["must"][2]["id"]]), F.overrides(hide_channels=["fxanal5"]), F.overrides(withdraw=True)):
            with self.subTest(hold):
                self.assertIsNone(K.attach_overview(d, doc(), src, hold))
        self.assertEqual(K.attach_overview(d, doc(), src, F.overrides()), OVERVIEW)


if __name__ == "__main__":
    unittest.main()
