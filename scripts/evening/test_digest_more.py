#!/usr/bin/env python3
"""저녁판 '더 자세히' 칸 테스트 — 2026-10-08 저녁에 더한 없어도 되는 칸(계약: digest_schema.py 머리말).

  글에 붙는 것   길이 구간(size) · 붙은 그림(pic) · 첫 두 줄의 낱말(head) · 숫자 없는 줄(row의 v가 null)
  항목에 붙는 것 함께 나온 낱말과 곳 수(words) · 첫 글~마지막 글(span) · 링크별 덧낱말(more) · 직전 판의 채널 수(prev)
  판에 붙는 것   이 판에 나온 낱말의 풀이(gloss) · 상태 기록의 대표 낱말 id(topics)
  닫힌 글자      심은 글자 · 규칙에 없는 풀이 · 허용 목록 밖 주소 · 글에 나온 순서대로 늘어놓은 낱말이 모두 걸리는가
  이미 나간 판   새 칸이 없는 10-08 판과 상태 기록(data/)을 새 코드가 그대로 읽는가

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요 — 글은 fixtures.py의 지어낸 것과 여기서 지어낸 한두 줄뿐이다. data/의 파일은 이미 공개된 산출물이다(채널 글이 아니다).
"""
import copy
import os
import shutil
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import digest_build as B
import digest_check as C
import digest_cluster as DC
import digest_rules as R
import digest_schema as S
import fixtures as F
import test_digest_build as TB
import test_digest_check as TC

TH = R.TH
fx, edit, codes = TC.fx, TC.edit, TC.codes
SOLO = "fxpers8"


def post(text, pic=False, ch="fxpers1", pid=1):
    return {"ch": ch, "id": pid, "at": "2026-10-08T09:00:00+09:00", "text": text, "links": [], "fwd": None, "card": None, "reply": False,
            "media": False, "via": "page", "pic": pic}


def made(text, **kw):
    return DC.mention(post(text, **kw), "personal", "source")


def assembled(**change):
    """fixtures의 입력으로 조립한 파일들. change = scored · collect · state · overrides 가운데 바꿀 것."""
    given = {"scored": fx("scored_doc"), "collect": fx("collect_status"), "state": fx("state"), "overrides": F.overrides(), **change}
    code, files, _ = B.assemble(given["scored"], given["collect"], given["state"], TB.index_before(), given["overrides"], fx("sources"))
    return code, files


def item_of(d, seed):
    return next(x for x in d["must"] + [x for g in d["rest"] for x in g["items"]] if x["id"].endswith(seed))


class MemberTest(unittest.TestCase):
    def test_size_is_one_of_three_names(self):
        got = [R.size_of("가" * n) for n in (0, 199, 200, 699, 700, 5000)]
        self.assertEqual(got, ["짧음", "짧음", "보통", "보통", "김", "김"])
        self.assertEqual((TH["size_short"], TH["size_long"], R.SIZES), (200, 700, ("짧음", "보통", "김")))
        self.assertEqual(R.size_of("가  \n\n  나"), "짧음")                       # 정리한 글자 수로 센다

    def test_a_post_carries_its_size_picture_and_the_words_of_its_first_two_lines(self):
        m = made("한은 총재 발언을 지어낸 첫 줄\n\n둘째 줄에는 기준금리 얘기\n셋째 줄에는 미 CPI 얘기", pic=True)
        self.assertEqual((m["size"], m["pic"]), ("짧음", True))
        self.assertEqual((m["head"], m["terms"]), (["한은 발언", "기준금리"], ["한은 발언", "기준금리", "미 CPI"]))    # 빈 줄은 세지 않는다
        self.assertTrue(set(m["lead"]) <= set(m["head"]) <= set(m["terms"]))
        far = made("지어낸 첫 줄 " + "가" * TH["row_head_chars"] + " 금통위")       # 한 줄이 길어도 첫머리는 row_head_chars자까지
        self.assertEqual((far["head"], far["terms"], far["pic"]), ([], ["금통위"], False))
        self.assertEqual(TH["row_head_chars"], 200)
        S.validate_cluster(DC.shape([m], [S.key_of("g", "fxpers1/1")]))

    def test_old_posts_without_the_picture_flag_are_read_as_no_picture(self):
        old = {k: v for k, v in post("미 CPI를 지어낸 한 줄").items() if k != "pic"}
        self.assertFalse(DC.mention(old, "personal", "source")["pic"])
        S.validate_post(old)

    def test_a_row_may_have_no_number(self):
        cases = {
            "한은 총재 발언을 지어낸 메모.\n기준금리 얘기가 길었다.": {"term": "한은 발언", "v": None},
            "기준금리 얘기 끝에 한은 총재 발언을 적은 지어낸 메모": {"term": "한은 발언", "v": None},           # A·B급이 C급보다 먼저
            "환율과 코스피를 함께 적은 지어낸 한 줄": {"term": "원/달러 환율", "v": None},                   # C급뿐이면 낱말이 둘 이상일 때만
            "환율 얘기만 적은 지어낸 한 줄": None,
            "환율 얘기를 적은 지어낸 첫 줄\n지어낸 둘째 줄\n셋째 줄에는 코스피": {"term": "원/달러 환율", "v": None},     # 글 전체에 낱말이 둘이면 된다
            "낱말이 하나도 없는 지어낸 글 한 줄입니다": None,
            "미 PPI 전월 대비 0.2% 상승이라는 지어낸 속보": {"term": "미 PPI", "v": "0.2%"},                 # 숫자의 짝은 예전 그대로
            "국고채 30년 입찰 낙찰금리 4.365%, 응찰률 240.6%": {"term": "국고채 입찰", "v": None},            # 첫 숫자가 시세면 다음 숫자로 넘어가지 않는다
            "지어낸 첫 줄\n지어낸 둘째 줄\n셋째 줄에야 금통위와 FOMC": None,                                # 첫 두 줄 밖
        }
        for text, want in cases.items():
            with self.subTest(text):
                self.assertEqual(made(text)["row"], want)

    def test_a_post_keeps_up_to_twenty_four_words(self):
        text = ("FOMC 베이지북 잭슨홀 ECB BOJ BOE 인민은행 금통위 가계부채 PCE ISM JOLTS ADP 유가 반도체 추경 통안채 국민연금 커브 관세 "
                "지정학 코스피 환율 공매도 엔화 위안화 신흥국 ETF 헤지펀드 매파")
        m = made(text)
        self.assertEqual((len(m["terms"]), TH["member_terms_max"]), (24, 24))
        self.assertEqual(m["terms"][:3], ["FOMC", "베이지북", "잭슨홀"])            # 글 안(<work>)에서는 자리순 그대로다

    def test_member_rules_are_checked(self):
        c = DC.shape([made("한은 총재 발언을 지어낸 메모.\n기준금리 얘기가 길었다.")], [S.key_of("g", "fxpers1/1")])
        for change in ({"head": ["한은 발언"], "lead": ["한은 발언", "기준금리"]}, {"head": ["한은 발언", "기준금리", "유가"]},
                       {"row": {"term": "유가", "v": None}}, {"row": {"term": "기준금리", "v": "3%"}}, {"size": "아주 김"}, {"pic": "예"},
                       {"terms": ["기준금리"], "head": ["기준금리"], "lead": ["기준금리"], "row": {"term": "기준금리", "v": None}}):
            bad = copy.deepcopy(c)
            bad["members"][0].update(change)
            bad = {**bad, "terms": DC.shape(bad["members"], bad["keys"])["terms"]}
            with self.subTest(change), self.assertRaises(ValueError):
                S.validate_cluster(bad)


class EditionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code, cls.files = assembled()
        cls.d = S.validate_digest(cls.files["digest.json"], fx("sources"))

    def test_words_are_what_two_or_more_wrote_beyond_the_title(self):
        cpi = self.d["must"][0]
        self.assertEqual(cpi["terms"], ["미 CPI", "미 국채 금리"])
        # 제목의 낱말(미 CPI — 직접 쓴 6곳)은 되풀이하지 않는다. 직접 쓴 두 곳 이상이 글 '전체'에서 쓴 낱말만: 한 곳은 첫머리, 한 곳은 셋째 줄
        self.assertEqual(cpi["words"], [{"term": "미 주거비", "n_ch": 2}])
        self.assertEqual(item_of(self.d, "fxanal4-905")["words"], [{"term": "빅테크 실적", "n_ch": 2}])
        self.assertNotIn("words", item_of(self.d, "fxbond4-640"))                  # 두 곳 이상이 쓴 낱말이 제목의 것뿐이면 칸이 없다
        self.assertNotIn("words", item_of(self.d, "fxbond1-502"))                  # 한 채널뿐이고 그 글의 낱말이 제목에 다 있을 때도
        scored = fx("scored_doc")
        lone = next(c for c in scored["clusters"] if c["seed"] == {"ch": "fxbond1", "id": 502})
        lone["members"][0]["terms"] += ["유가", "금리", "미 CPI"]                  # 첫머리 밖에서 걸린 낱말(지어낸 것)
        single = item_of(assembled(scored=scored)[1]["digest.json"], "fxbond1-502")
        self.assertEqual(single["terms"], ["금통위 의사록", "소수의견", "국고채 금리"])
        self.assertEqual(single["words"], [{"term": t, "n_ch": 1} for t in ("미 CPI", "유가")])      # 제목 밖의 낱말만, 등급 → 가나다.
        self.assertNotIn("more", single["links"][0])                               # '금리'는 '국고채 금리' 곁이라 어디에도 싣지 않는다
        self.assertEqual(single["links"][0]["n_terms"], 6)                         # 그 글에서 걸린 사전 낱말 수는 그대로 센다

    def test_words_drop_the_title_and_the_wide_word_beside_its_narrow_one(self):
        """검토(2026-10-08 밤): 카드의 낱말 8칸 중 4칸이 제목·겹치는 말이었다 — 제목의 낱말과, 좁은 낱말 곁의 넓은 낱말은 뺀다."""
        mk = lambda ch, terms, fwd=False: {"ch": ch, "role": "source", "fwd": fwd, "terms": terms}
        both = ["연준 의사록", "금리", "연준", "인플레", "AI", "AI Capex", "관세", "미 고용"]
        ms = [mk("fxbond1", both), mk("fxbond2", both), mk("fxbond3", ["연준 의사록", "금리", "연준", "인플레", "관세", "유가"])]
        words, shared = B._words(ms, TH["words_max"], ["연준 의사록", "금리"])
        self.assertEqual([(w["term"], w["n_ch"]) for w in words], [("관세", 3), ("인플레", 3), ("미 고용", 2), ("AI Capex", 2)])
        self.assertEqual(shared, set(both))                                        # 링크의 '이 글에서 더'는 두 곳 이상이 쓴 낱말을 다 뺀다
        self.assertEqual(B._words(ms, 2, ["연준 의사록", "금리"])[0], words[:2])
        self.assertEqual(TH["words_max"], 16)                                      # 두 곳 이상이 쓴 낱말이 카드 어디에도 없는 일이 드물게

    def test_forwards_alone_do_not_make_shared_words(self):
        """검토(2026-10-08 밤): 같은 글을 두 채널이 옮긴 묶음에 '2곳'이 붙었다 — 옮긴 것은 쓴 것이 아니다."""
        mk = lambda ch, fwd: {"ch": ch, "role": "source", "fwd": fwd, "terms": ["미 PPI", "AI", "반도체"]}
        self.assertEqual(B._words([mk("fxanal1", True), mk("fxpers1", True)], 16, []), ([], set()))
        words, shared = B._words([mk("fxanal1", True), mk("fxpers1", True), mk("fxbond1", False)], 16, [])
        self.assertEqual([(w["term"], w["n_ch"]) for w in words], [("미 PPI", 1), ("반도체", 1), ("AI", 1)])     # 직접 쓴 한 곳의 낱말로만
        self.assertEqual(shared, set())
        scored = fx("scored_doc")
        rumor = next(c for c in scored["clusters"] if c["seed"] == {"ch": "fxpers5", "id": 610})
        for m in rumor["members"]:
            m["fwd"] = m["role"] == "source" and m["ch"] != "fxpers5"              # 씨앗 글만 직접 쓴 글, 나머지는 옮긴 글
            m["terms"] = m["terms"] + ["유가"] if m["role"] == "source" else m["terms"]
        got = item_of(assembled(scored=S.validate_scored_doc(scored))[1]["digest.json"], "fxpers5-610")
        self.assertEqual(got["words"], [{"term": "유가", "n_ch": 1}])                # 옮긴 세 곳을 세어 '4곳'이라 하지 않는다
        for x in self.d["must"]:
            self.assertLessEqual(len(x.get("words", [])), TH["words_max"])
        for g in self.d["rest"]:
            for x in g["items"]:
                self.assertLessEqual(len(x.get("words", [])), TH["rest_words_max"])

    def test_span_is_the_first_and_last_post_and_the_count(self):
        self.assertEqual(self.d["must"][0]["span"], {"from": "2026-10-07T21:32:00+09:00", "to": "2026-10-08T09:00:00+09:00", "posts": 9})
        self.assertEqual(item_of(self.d, "fxbond1-502")["span"]["posts"], 1)

    def test_each_link_says_what_only_that_post_has(self):
        links = {ln["ch"]: ln for ln in self.d["must"][0]["links"]}
        self.assertNotIn("more", links["fxbond2"])                                 # 두 곳이 쓴 낱말(미 주거비)은 '이 글에만'이 아니다
        self.assertNotIn("more", links["fxbond1"])                                 # 그 글의 낱말이 항목의 낱말에 다 있으면 칸도 없다
        self.assertNotIn("more", links["fxbond3"])
        self.assertEqual({ch: ln["n_terms"] for ch, ln in links.items()},          # 글마다 걸린 사전 낱말 수 — 어느 글이 넓게 다뤘는지
                         {"fxbond1": 2, "fxbond2": 2, "fxbond3": 1, "fxanal2": 1, "fxpers2": 2, "fxpers3": 1})
        auction = {ln["ch"]: ln.get("more") for ln in self.d["must"][1]["links"]}
        self.assertEqual(auction, {"fxbond4": ["금리"], "fxbond5": ["장기물 수요"], "fxanal3": ["외국인 국채선물"]})     # 이 글에만 더 있는 낱말
        m = {"ch": "fxbond1", "id": 1, "terms": ["미 국채 커브", "커브", "금리", "유가", "매파·비둘기"], "size": "김"}
        self.assertEqual(B._more(m, {"연준 의사록"}, 4)["more"], ["미 국채 커브", "유가", "매파·비둘기", "금리"])       # 좁은 낱말 곁의 '커브'는 빠진다
        self.assertEqual(B._more(m, {"연준 의사록", "국고채 금리"}, 4)["more"], ["미 국채 커브", "유가", "매파·비둘기"])
        self.assertEqual({ln["size"] for ln in links.values()}, {"짧음"})
        self.assertEqual([ch for ch, ln in links.items() if ln.get("pic")], ["fxanal2"])
        self.assertTrue(item_of(self.d, "fxbond4-640")["links"][0]["pic"])
        for x in self.d["must"]:
            for ln in x["links"]:
                self.assertFalse(set(ln.get("more", [])) & (set(x["terms"]) | {w["term"] for w in x.get("words", [])}))
                self.assertLessEqual(len(ln.get("more", [])), TH["more_max"])

    def test_a_lone_post_without_a_number_becomes_a_row(self):
        rows = [r for r in self.d["solo"]["rows"] if r["ch"] == SOLO]
        self.assertEqual(rows, [{"ch": SOLO, "term": "한은 발언", "result": None, "v": None, "at": "2026-10-08T15:30:00+09:00",
                                 "url": f"https://t.me/{SOLO}/56", "more": ["가계부채", "기준금리"], "size": "짧음", "n_terms": 3}])
        self.assertEqual(next(c for c in self.d["solo"]["channels"] if c["ch"] == SOLO)["hit"], 1)
        numbered = [r for r in self.d["wire"]["rows"] + self.d["solo"]["rows"] if r["v"]]
        self.assertGreaterEqual(len(numbered), 7)                                  # 숫자가 붙는 줄은 예전 그대로다

    def test_five_rows_a_channel_best_grade_first_then_numbers_then_early(self):
        scored = fx("scored_doc")
        base = next(c for c in scored["clusters"] if c["seed"] == {"ch": SOLO, "id": 56})
        plan = [("09:10", "유가", None), ("09:20", "유가", "2.1%"), ("09:30", "미 CPI", None), ("09:40", "유가", None),
                ("09:50", "유가", "3.4%"), ("10:00", "유가", None), ("10:10", "금리", None)]
        for i, (hhmm, term, v) in enumerate(plan):
            c = copy.deepcopy(base)
            head = [term] + (["원/달러 환율"] if term == "금리" else [])            # C급 낱말은 둘 이상일 때만 줄이 된다
            c["members"][0].update(id=900 + i, at=f"2026-10-08T{hhmm}:00+09:00", terms=head, lead=head, head=head,
                                   nums=[v] if v else [], lead_nums=[v] if v else [], row={"term": term, "v": v})
            scored["clusters"].append({**DC.shape(c["members"], [S.key_of("g", f"{SOLO}/{900 + i}")]),
                                       **{k: c[k] for k in ("coverage", "score", "gate", "why", "pick", "rank")}})
        scored["stats"]["kept"] += len(plan)
        scored["stats"]["posts"] += len(plan)
        scored["clusters"].sort(key=lambda c: (c["first_at"], c["seed"]["ch"], c["seed"]["id"]))
        collect = fx("collect_status")
        for ch in collect["channels"]:
            if ch["ch"] == SOLO:
                ch.update({k: ch[k] + len(plan) for k in ("in_window", "posts", "with_text")})
        d = S.validate_digest(assembled(scored=S.validate_scored_doc(scored), collect=collect)[1]["digest.json"], fx("sources"))
        got = [(r["at"][11:16], r["term"], r["v"]) for r in d["solo"]["rows"] if r["ch"] == SOLO]
        # A급(09:30) → 숫자 있는 B급(09:20 · 09:50) → 이른 B급(09:10 · 09:40)까지 다섯, 실을 때는 시각순. 10:00 · 10:10 · 15:30은 밀린다
        self.assertEqual(got, [("09:10", "유가", None), ("09:20", "유가", "2.1%"), ("09:30", "미 CPI", None), ("09:40", "유가", None),
                               ("09:50", "유가", "3.4%")])
        self.assertEqual(next(c for c in d["solo"]["channels"] if c["ch"] == SOLO)["hit"], 8)

    def test_a_row_without_a_number_leads_with_its_best_word(self):
        """검토(2026-10-08 밤): 단독 줄 14개 중 10개가 흔한 C급 낱말로 시작하고 더 높은 등급이 '더:' 뒤에 있었다."""
        mk = lambda terms, head, v=None: {"ch": SOLO, "id": 7, "at": "2026-10-08T09:00:00+09:00", "terms": terms, "results": ["상회"],
                                          "size": "보통", "row": {"term": head, "v": v}}
        row = B._row(mk(["금리", "국채 입찰", "연준 의사록", "유가"], "금리"))
        self.assertEqual((row["term"], row["more"], row["result"]), ("연준 의사록", ["유가", "국채 입찰"], None))     # 등급 → 넓은 낱말은 뒤 → 가나다
        row = B._row(mk(["AI", "AI Capex"], "AI"))
        self.assertEqual((row["term"], row.get("more"), row["n_terms"]), ("AI Capex", None, 2))                # 좁은 낱말 곁의 넓은 낱말은 싣지 않는다
        row = B._row(mk(["금리", "미 PPI", "유가"], "미 PPI", "0.2%"))
        self.assertEqual((row["term"], row["v"], row["result"]), ("미 PPI", "0.2%", "상회"))                    # 숫자의 짝은 그대로 둔다
        self.assertIsNone(B._row({**mk(["금리"], "금리"), "row": None}))

    def test_gloss_holds_each_shown_word_once_in_dictionary_order(self):
        g = self.d["gloss"]
        terms = [x["term"] for x in g]
        self.assertEqual(g, R.glosses(S.shown_terms(self.d)))
        self.assertEqual(len(terms), len(set(terms)))
        self.assertTrue({"미 CPI", "한은 발언", "국고채 입찰", "기준금리", "국고채 발행계획"} <= set(terms))
        self.assertNotIn("FOMC", terms)                                            # 이 판에 나오지 않은 낱말의 풀이는 싣지 않는다
        self.assertEqual(terms, sorted(terms, key=list(R.TERMS).index))
        self.assertTrue(any(x["url"] for x in g) and any(x["url"] is None for x in g))
        hidden = assembled(overrides=F.overrides(hide_channels=["fxpers6"]))[1]["digest.json"]
        self.assertNotIn("국고채 발행계획", [x["term"] for x in hidden["gloss"]])    # 줄이 빠지면 그 낱말의 풀이도 빠진다

    def test_prev_tells_how_many_covered_the_same_word_last_edition(self):
        self.assertEqual(self.d["must"][0]["prev"], {"date": "2026-10-07", "bond": 2, "analyst": 0, "personal": 1})
        self.assertNotIn("prev", self.d["must"][1])
        topics = self.files["digest_state.json"]["edition"]["topics"]
        self.assertEqual([t["key"] for t in topics], sorted(t["key"] for t in topics))
        mine = next(t for t in topics if t["key"] == F.topic_key("미 CPI"))
        self.assertEqual(mine, {"key": F.topic_key("미 CPI"), "bond": 3, "analyst": 2, "personal": 3})
        self.assertEqual(self.files["digest_state.json"]["base"]["topics"], fx("state")["edition"]["topics"])
        # 대표 낱말이 C급('관세')인 줄은 견주지 않는다 — 흔한 낱말 하나로는 같은 주제라 할 수 없다(검토 2026-10-08 밤)
        self.assertNotIn(F.topic_key("관세"), [t["key"] for t in topics])
        state = fx("state")
        state["edition"]["topics"] = sorted(state["edition"]["topics"] + [{"key": F.topic_key("관세"), "bond": 0, "analyst": 0, "personal": 2}],
                                            key=lambda t: t["key"])
        again = assembled(state=state)[1]["digest.json"]
        self.assertNotIn("prev", item_of(again, "fxpers5-610"))
        self.assertIn("prev", again["must"][0])
        first = assembled(state=B.EMPTY_STATE)[1]["digest.json"]                    # 첫 실행 · 새 칸이 없는 지난 상태 → prev 없음
        old = fx("state")
        del old["edition"]["topics"]
        for d in (first, assembled(state=old)[1]["digest.json"]):
            self.assertFalse([x for x in d["must"] if "prev" in x])

    def test_same_day_rerun_compares_with_the_edition_before_again(self):
        again = assembled(state=self.files["digest_state.json"], collect={**fx("collect_status"), "window_kind": "rerun"})[1]
        self.assertEqual(again["digest.json"]["must"][0]["prev"], self.d["must"][0]["prev"])
        self.assertEqual(again["digest_state.json"]["edition"]["topics"], self.files["digest_state.json"]["edition"]["topics"])

    def test_withdrawn_edition_carries_none_of_it(self):
        files = assembled(overrides=F.overrides(withdraw=True))[1]
        self.assertNotIn("gloss", files["digest.json"])
        self.assertEqual(files["digest_state.json"]["edition"].get("topics", []), [])

    def test_nothing_new_is_a_free_string(self):
        self.assertEqual(F.leaks(S.dump(self.files)), [])
        for name, doc in self.files.items():
            self.assertEqual(S.closed_violations(S.validator_for(name)(doc), S.handles_of(fx("sources"))), [], name)
        self.assertLess(len(S.dump(self.d).encode("utf-8")), C.EDITION_BYTES)
        self.assertTrue(20_000 < C.EDITION_BYTES <= 40_000)

    def test_when_too_big_glosses_go_first_then_lone_rows_then_the_rest(self):
        """검토(2026-10-08 밤): 상한에 걸리면 나머지 표(채권 채널 글)만 줄었다 — 풀이 → 단독 줄 → 나머지 표 순으로 덜어 낸다."""
        args = (fx("scored_doc"), fx("collect_status"), fx("sources"), F.overrides(), S.state_base(fx("state"), F.EDITION))
        size = lambda d: len(S.dump(d).encode("utf-8"))
        rows = lambda d: len(d["wire"]["rows"]) + len(d["solo"]["rows"])
        rest = lambda d: sum(len(g["items"]) for g in d["rest"])

        def at(limit):
            with mock.patch.object(C, "EDITION_BYTES", limit):
                return S.validate_digest(B.edition(*args)[0], fx("sources"))
        full = at(C.EDITION_BYTES)
        self.assertEqual((full, R.phrase("note_slim") in full["notes"]), (self.d, False))
        one = at(size(full) - 1)                                                   # 1단계: 나머지·단독 줄에만 나온 낱말의 풀이
        core = S.shown_terms({**full, "rest": [], "wire": {"channels": [], "rows": []}, "solo": {"channels": [], "rows": []}})
        self.assertEqual([g["term"] for g in one["gloss"]], [g["term"] for g in full["gloss"] if g["term"] in core])
        self.assertTrue(0 < len(one["gloss"]) < len(full["gloss"]))
        self.assertEqual((rows(one), rest(one), one["must"]), (rows(full), rest(full), full["must"]))
        self.assertIn(R.phrase("note_slim"), one["notes"])
        two = at(size(one) - 1)                                                    # 2단계: 단독 줄을 채널당 3줄로
        self.assertEqual((rows(two), rest(two), two["funnel"]["truncated"]), (rows(full) - 2, rest(full), 0))
        self.assertEqual(two["wire"]["channels"], full["wire"]["channels"])        # 건수(read · hit)는 그대로 남는다
        none = at(size({**one, "wire": {**one["wire"], "rows": []}, "solo": {**one["solo"], "rows": []}}) + 200)
        self.assertEqual((rows(none), rest(none)), (0, rest(full)))                # 단독 줄이 다 빠질 때까지 나머지 표는 그대로다
        cut = at(size(none) - 1)                                                   # 그다음에야 나머지 표가 점수 낮은 줄부터
        self.assertEqual((rest(cut), cut["funnel"]["truncated"], cut["must"]), (rest(full) - 1, 1, full["must"]))
        bare = at(size({**cut, "rest": [], "gloss": []}) + 60)                     # 끝까지 가면 남은 풀이도 비운다(판은 낸다)
        self.assertEqual((bare["gloss"], rest(bare), bare["must"]), ([], 0, full["must"]))
        with mock.patch.object(C, "EDITION_BYTES", 500), self.assertRaises(ValueError):
            B.edition(*args)


class ShapeTest(unittest.TestCase):
    def refused(self, doc, where):
        with self.assertRaises(ValueError) as e:
            S.validate_digest(doc, fx("sources"))
        self.assertIn(where, str(e.exception))
        self.assertEqual(F.leaks(str(e.exception)), [])

    def test_word_lists_must_be_in_the_fixed_order_not_the_order_of_the_post(self):
        d = fx("digest")
        single = next(x for g in d["rest"] for x in g["items"] if x["id"].endswith("fxbond1-502"))
        single["words"] = [{"term": t, "n_ch": 1} for t in ("국고채 금리", "미 CPI")]    # 등급 → 가나다가 아니다
        self.refused(d, "words")
        d = fx("digest")
        link = next(ln for ln in d["solo"]["rows"] if ln["ch"] == SOLO)
        link["more"] = link["more"][::-1]
        self.refused(d, "solo.rows")
        self.assertEqual(R.by_grade(["금리", "미 CPI", "유가", "미 CPI"]), ["미 CPI", "유가", "금리"])
        self.assertEqual(R.by_count({"금리": 3, "유가": 3, "미 CPI": 2}), [("유가", 3), ("금리", 3), ("미 CPI", 2)])

    def test_refusals(self):
        good = fx("digest")
        solo = next(i for i, r in enumerate(good["solo"]["rows"]) if r["ch"] == SOLO)
        rumor = next((gi, i) for gi, g in enumerate(good["rest"]) for i, x in enumerate(g["items"]) if x["id"].endswith("fxpers5-610"))
        cases = {
            "곳 수가 1과 여럿으로 섞임": (edit(good, ["must", 0, "words"], [{"term": "관세", "n_ch": 6}, {"term": "유가", "n_ch": 1}]), "words"),
            "같은 낱말 두 번": (edit(good, ["must", 0, "words"], [{"term": "관세", "n_ch": 6}] * 2), "words"),
            "제목의 낱말을 되풀이": (edit(good, ["must", 0, "words"], [{"term": "미 CPI", "n_ch": 6}]), "words"),
            "C급 대표 낱말의 직전 판": (edit(good, ["rest", rumor[0], "items", rumor[1], "prev"],
                                     {"date": "2026-10-07", "bond": 0, "analyst": 0, "personal": 2}), "prev"),
            "낱말 수가 덧낱말보다 적음": (edit(good, ["must", 1, "links", 0, "n_terms"], 0), "links[0]"),
            "이 판에 없는 낱말의 풀이": (edit(good, ["gloss"], R.glosses([g["term"] for g in good["gloss"]] + ["잭슨홀"])), "gloss"),
            "덧낱말이 항목의 낱말과 겹침": (edit(good, ["must", 0, "links", 0, "more"], ["미 CPI"]), "more"),
            "덧낱말이 순서 밖": (edit(good, ["must", 0, "links", 0, "more"], ["금리", "유가"]), "more"),
            "길이 구간이 아님": (edit(good, ["must", 0, "links", 0, "size"], "1,234자"), "size"),
            "그림 표시는 참뿐": (edit(good, ["must", 0, "links", 0, "pic"], False), "pic"),
            "첫 글이 마지막 글보다 늦음": (edit(good, ["must", 0, "span"], {"from": good["window"]["to"], "to": good["must"][0]["span"]["from"],
                                                               "posts": 9}), "span"),
            "창 밖의 시각": (edit(good, ["must", 0, "span", "from"], "2026-10-06T09:00:00+09:00"), "span"),
            "글 수가 링크보다 적음": (edit(good, ["must", 0, "span", "posts"], 1), "span"),
            "직전 판이 오늘": (edit(good, ["must", 0, "prev", "date"], good["date"]), "prev"),
            "숫자 없는 줄의 결과 낱말": (edit(good, ["solo", "rows", solo, "result"], "상회"), "rows"),
            "줄의 낱말이 덧낱말에도": (edit(good, ["solo", "rows", solo, "more"], ["한은 발언"]), "rows"),
            "같은 풀이 두 번": (edit(good, ["gloss"], good["gloss"][:1] + good["gloss"]), "gloss"),
            "풀이가 없는 낱말의 줄": (edit(good, ["gloss"], [{"term": "금리", "text": good["gloss"][0]["text"], "url": None}]), "gloss"),
            "다른 낱말의 풀이 문구": (edit(good, ["gloss", 0, "text"], good["gloss"][1]["text"]), "gloss"),
            "규칙에 없는 풀이 문구": (edit(good, ["gloss", 0, "text"], good["gloss"][0]["text"] + "."), "gloss[0].text"),
            "심은 글자가 든 풀이": (edit(good, ["gloss", 0, "text"], F.C1), "gloss[0].text"),
            "허용 목록 밖 주소": (edit(good, ["gloss", 0, "url"], "https://example.org/"), "gloss[0].url"),
            "허용 도메인의 다른 쪽": (edit(good, ["gloss", 0, "url"], "https://fred.stlouisfed.org/series/" + F.C1), "gloss[0].url"),
            "풀이 순서가 다름": (edit(good, ["gloss"], good["gloss"][::-1]), "gloss"),
        }
        for name, (bad, where) in cases.items():
            with self.subTest(name):
                self.refused(bad, where)
        c_only = edit(edit(good, ["solo", "rows", solo, "term"], "기준금리"), ["solo", "rows", solo, "more"], None)
        del c_only["solo"]["rows"][solo]["more"]
        c_only["solo"]["rows"][solo]["n_terms"] = 1
        c_only["gloss"] = R.glosses(S.shown_terms(c_only))
        self.refused(c_only, "rows")                                               # C급 낱말 하나뿐인 줄
        c_only["solo"]["rows"][solo]["n_terms"] = 2                                # 낱말이 둘인 글인데 하나가 넓은 낱말이라 빠진 줄은 된다
        S.validate_digest(c_only, fx("sources"))
        # 조립은 늘 이 판의 낱말만큼만 싣지만(EditionTest), 검사는 '빠짐없이'를 묻지 않는다 — 항목을 손으로 내린 판이 풀이 때문에 떨어지지 않게
        S.validate_digest(edit(good, ["gloss"], good["gloss"][1:]), fx("sources"))

    def test_state_topics(self):
        state = fx("state_after")
        S.validate_state(state)
        for bad in (state["edition"]["topics"][::-1], state["edition"]["topics"][:1] * 2,
                    [{**state["edition"]["topics"][0], "key": "미 CPI"}], [{**state["edition"]["topics"][0], "term": "미 CPI"}]):
            with self.assertRaises(ValueError):
                S.validate_state(edit(state, ["edition", "topics"], bad))
        self.assertEqual(S.closed_violations(state, S.handles_of(fx("sources"))), [])
        self.assertRegex(F.topic_key("미 CPI"), r"^k:[0-9a-f]{12}$")               # 낱말 글자는 상태 기록에 남지 않는다
        self.assertNotIn("미 CPI", S.dump(state["edition"]["topics"]))


class CheckTest(TC.FolderCase):
    def test_planted_text_in_any_new_field_is_refused(self):
        good = fx("digest")
        solo = next(i for i, r in enumerate(good["solo"]["rows"]) if r["ch"] == SOLO)
        cases = {
            "풀이 문구": edit(good, ["gloss", 0, "text"], F.C3), "공식 주소": edit(good, ["gloss", 0, "url"], "https://" + F.C7),
            "링크의 덧낱말": edit(good, ["must", 0, "links", 0, "more"], [F.C1]), "함께 나온 낱말": edit(good, ["must", 0, "words", 0, "term"], F.C2),
            "줄의 덧낱말": edit(good, ["solo", "rows", solo, "more"], [F.C5]), "길이 구간": edit(good, ["must", 0, "links", 0, "size"], F.C4),
            "첫 글 시각": edit(good, ["must", 0, "span", "from"], F.C1), "새 칸 옆의 모르는 칸": edit(good, ["must", 0, "span", "note"], F.C6),
            "직전 판의 날짜": edit(good, ["must", 0, "prev", "date"], F.C1),
        }
        for name, bad in cases.items():
            with self.subTest(name):
                self.assertTrue(self.check(raw=True, digest=bad)[0])
                code, text = self.cli(raw=True)
                self.assertEqual((code, F.leaks(text)), (1, []))
        found, _ = self.check(raw=True, digest=cases["풀이 문구"])
        self.assertEqual([f["at"] for f in found if f["code"] in ("open", "leak")], ["$.gloss[0].text"] * 2)      # 판 둘(digest · 날짜별)
        state = edit(fx("state_after"), ["edition", "topics", 0, "key"], F.C1)
        self.assertTrue(self.check(digest_state=state)[0])

    def test_gloss_must_be_the_one_written_in_the_rules(self):
        good = fx("digest")
        other = next(g for g in R.GLOSS.values() if g[1] and g[1] != good["gloss"][0]["url"])
        for bad in (edit(good, ["gloss", 0, "text"], good["gloss"][0]["text"].replace(" ", "  ", 1)),      # 글자 하나가 다르다
                    edit(good, ["gloss", 0, "text"], other[0]),                                             # 규칙에 있지만 다른 낱말의 풀이
                    edit(good, ["gloss", 0, "url"], other[1]),                                              # 규칙에 있지만 다른 낱말의 주소
                    edit(good, ["gloss", 0, "url"], "https://www.newyorkfed.org/"),                         # 허용 도메인이지만 목록에 없는 쪽
                    edit(good, ["gloss"], R.glosses([g["term"] for g in good["gloss"]] + ["잭슨홀"]))):       # 규칙의 풀이지만 이 판에 없는 낱말
            found, _ = self.check(digest=bad)
            self.assertTrue(found)
            self.assertTrue({f["at"].split("[")[0] for f in found} <= {"$.gloss", "digest.gloss"}, found)
            self.assertEqual(self.cli()[0], 1)

    def test_words_in_the_order_of_the_post_are_refused(self):
        good = fx("digest")
        solo = next(i for i, r in enumerate(good["solo"]["rows"]) if r["ch"] == SOLO)
        text = next(p["text"] for p in fx("posts") if (p["ch"], p["id"]) == (SOLO, 56))
        in_post_order = [t["term"] for t in R.match_terms(text)][1:]               # 글에 나온 순서: 기준금리 → 가계부채
        self.assertEqual(in_post_order, good["solo"]["rows"][solo]["more"][::-1])
        found, _ = self.check(raw=True, digest=edit(good, ["solo", "rows", solo, "more"], in_post_order))
        self.assertIn("shape", {f["code"] for f in found})                         # 낱말은 다 그 글의 것이어도 순서가 글의 것이면 떨어진다
        self.assertEqual(self.cli(raw=True)[0], 1)

    def test_what_a_link_says_must_be_true_of_that_post(self):
        good = fx("digest")
        solo = next(i for i, r in enumerate(good["solo"]["rows"]) if r["ch"] == SOLO)
        cases = {
            "그 글에 없는 덧낱말": (edit(good, ["must", 0, "links", 0, "more"], ["유가"]), ("mismatch", "link")),
            "다른 길이 구간": (edit(good, ["must", 0, "links", 0, "size"], "김"), ("mismatch", "link")),
            "없는 그림": (edit(good, ["must", 0, "links", 0, "pic"], True), ("mismatch", "link")),
            "줄에 없는 덧낱말": (edit(good, ["solo", "rows", solo, "more"], ["유가"]), ("mismatch", "row")),
            "줄의 다른 길이 구간": (edit(good, ["solo", "rows", solo, "size"], "보통"), ("mismatch", "row")),
            "글의 낱말 수가 다름": (edit(good, ["must", 0, "links", 0, "n_terms"], 1), ("mismatch", "link")),
            "줄의 낱말 수가 다름": (edit(good, ["solo", "rows", solo, "n_terms"], 9), ("mismatch", "row")),
        }
        for name, (bad, want) in cases.items():
            bad["gloss"] = R.glosses(S.shown_terms(bad))
            with self.subTest(name):
                self.assertEqual(self.check(digest=bad)[0], [])                    # 원문 없이는 알 수 없다
                self.assertIn(want, codes(self.check(raw=True, digest=bad)[0]))
        self.assertEqual(self.check(raw=True)[0], [])

    def test_the_word_count_of_a_post_is_capped_like_the_post_itself(self):
        text = ("FOMC 베이지북 잭슨홀 ECB BOJ BOE 인민은행 금통위 가계부채 PCE ISM JOLTS ADP 유가 반도체 추경 통안채 국민연금 커브 관세 "
                "지정학 코스피 환율 공매도 엔화 위안화 신흥국 ETF 헤지펀드 매파")       # 사전 낱말 서른 개가 걸리는 지어낸 글
        p = post(text)
        self.assertGreater(len(R.match_terms(text)), TH["member_terms_max"])
        size = R.size_of(text)
        self.assertTrue(C._more_in({"size": size, "n_terms": TH["member_terms_max"]}, p))     # 글 하나의 낱말은 24개까지만 센다
        self.assertTrue(C._more_in({"size": size}, p))                                        # 칸이 없는 옛 판의 링크
        self.assertFalse(C._more_in({"size": size, "n_terms": len(R.match_terms(text))}, p))

    def test_prev_must_agree_with_the_state_file(self):
        bad = edit(fx("digest"), ["must", 0, "prev", "bond"], 5)
        self.assertIn(("cross", "edition"), codes(self.check(digest=bad)[0]))
        state = fx("state_after")
        del state["base"]["topics"]
        self.assertIn(("cross", "edition"), codes(self.check(digest_state=state)[0]))

    def test_a_bad_row_costs_only_that_row(self):
        bad = edit(fx("digest"), ["solo", "rows", 0, "url"], "https://t.me/fxoff1/1")
        pruned, found = C.prune(bad, self.src)
        self.assertEqual(codes(found), [("url", "row")])
        self.assertEqual(codes(C.check_edition(bad, self.src)), [("url", "row")])   # 걸린 줄 하나만 — 풀이 칸이 덩달아 걸리지 않는다
        self.assertEqual(C.check_edition(pruned, self.src), [])


class PublishedTest(unittest.TestCase):
    """10-08에 이미 나간 판(새 칸 없음)을 새 코드가 그대로 읽는가 — data/의 공개 산출물만 본다."""

    def setUp(self):
        self.data = os.path.join(REPO, "data")
        self.src = S.validate_sources(S.read_json(os.path.join(self.data, "sources.json")))

    def test_published_files_are_still_valid_and_closed(self):
        names = [n for n in S.PUBLIC_FILES] + [f"digest/{n}" for n in sorted(os.listdir(os.path.join(self.data, "digest")))]
        self.assertIn("digest/2026-10-08.json", names)
        for name in names:
            doc = S.read_json(os.path.join(self.data, *name.split("/")))
            S.validator_for(name)(doc)
            self.assertEqual(S.closed_violations(doc, S.handles_of(self.src)), [], name)
        first = S.read_json(os.path.join(self.data, "digest", "2026-10-08.json"))
        self.assertEqual((first["schema"], S.SCHEMA), (1, 1))
        self.assertEqual(C.check_edition(first, self.src), [])

    def test_published_folder_passes_the_check_as_it_is(self):
        found, facts = C.check_folder(self.data, self.src)
        self.assertEqual(found, [])
        self.assertTrue(facts["published"])

    def test_the_next_edition_builds_on_the_published_state(self):
        state = S.validate_state(S.read_json(os.path.join(self.data, "digest_state.json")))
        index = S.validate_index(S.read_json(os.path.join(self.data, "digest_index.json")))
        nxt = S.collect_window(S.parse_iso("2026-10-09T17:41:00+09:00"), state)
        self.assertEqual((nxt["kind"], nxt["from"]), ("next", state["edition"].get("read_to") or state["edition"]["window"]["to"]))
        self.assertIsNotNone(S.state_base(state, "2026-10-09"))
        moved = S.next_state(state, {**state["edition"], "date": "2026-10-09", "window": {"from": nxt["from"], "to": nxt["to"]},
                                     "collected_at": nxt["to"], "must": [], "topics": []})
        S.validate_state(moved)
        self.assertEqual(index["editions"][0]["date"], "2026-10-08")


if __name__ == "__main__":
    unittest.main()
