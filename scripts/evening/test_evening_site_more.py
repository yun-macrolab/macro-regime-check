#!/usr/bin/env python3
"""저녁판 화면 테스트(셋째 묶음) — 2026-10-08 저녁에 더한 '더 자세히' 칸을 화면이 어떻게 보여 주는가.

  꼭 볼 것 카드  고정 틀에 값을 끼운 한 문장 · 함께 나온 낱말과 곳 수(자료의 순서 그대로) · 직전 판과 견주기 ·
                출처 줄(시각 · 길이 · 붙은 것 · 이 글에서 더) · 낱말 풀이와 공식 자료 링크
  나머지·단독 줄  같은 것을 간략히, 숫자 없는 단독 줄도 그린다
  닫힌 글자      풀이는 규칙(digest_gloss.py)의 것과 지문이 같을 때만 글자로 들어가고, 공식 자료 링크는 허용 도메인의 https 주소일 때만 걸린다
  옛 형태        새 칸이 없는 판(10-08에 나간 첫 판)도 그대로 그려진다 — 지어낸 판에서 칸을 뺀 것과, data/에 게시된 판 둘 다

도구(가짜 문서 · 지어낸 판)는 test_evening_site.py의 것을 쓴다. 모양과 가로 넘침(폭 375px)은 여기서 볼 수 없다.
실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요. node가 없으면 그려 보는 테스트는 건너뛴다.
"""
import copy
import glob
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_rules as R
import digest_schema as S
import fixtures as F
from test_evening_site import (C1, C3, C4, C5, C7, NODE, POST, REPO, TAKEDOWN, THU_EVENING, Screen, blob, calls, draw, draws, flat, fx,
                               outside, posts, rules_block, site)

NEW_ITEM, NEW_LINK = ("words", "span", "prev"), ("more", "size", "pic", "n_terms")
CPI = "미국 소비자물가지수. 노동통계국(BLS)이 매달 내는 대표 물가 지표"       # digest_gloss.py의 풀이 — 우리가 쓴 글이다(채널 글이 아니다)


def mark(text):
    """글자 지문(FNV-1a 32비트, UTF-16 단위) — evening.js의 fingerprint()와 같은 셈."""
    h, raw = 0x811C9DC5, text.encode("utf-16-le")
    for i in range(0, len(raw), 2):
        h = ((h ^ int.from_bytes(raw[i:i + 2], "little")) * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def gloss_marks():
    """규칙의 풀이 전부의 지문 — evening.js의 RULES.gloss_marks가 이것과 같아야 한다(낱말과 풀이를 함께 묶는다)."""
    return sorted(mark(term + "\n" + text) for term, (text, _) in R.GLOSS.items())


def term_marks():
    """사전 낱말 전부의 지문 — evening.js의 RULES.term_marks가 이것과 같아야 한다."""
    return sorted(mark(t) for t in R.TERMS)


def marks_block(name, got):
    """evening.js에 붙여 넣을 꼴 — 지문 17개씩을 이어 붙인 문자열들(화면이 8자씩 끊어 읽는다. 17개 = 한 줄 150자 안)."""
    lines = ['"' + "".join(got[i:i + 17]) + '"' for i in range(0, len(got), 17)]
    return f'    "{name}": [\n      ' + ",\n      ".join(lines) + "]"


def kind_of(href):
    """공식 자료 링크의 이름 — 세인트루이스 연은이 모아 싣는 쪽(FRED · FRASER)은 '공식 자료'라 부르지 않는다."""
    return "시계열" if "//fred." in href else "문서 모음" if "//fraser." in href else "공식 자료"


def old_shape(d):
    """10-08에 나간 첫 판의 형태로 — 저녁에 더한 칸을 뺀다(숫자 없는 단독 줄도 그때는 없었다)."""
    d = copy.deepcopy(d)
    d.pop("gloss", None)
    for x in d["must"] + [x for g in d["rest"] for x in g["items"]]:
        for k in NEW_ITEM:
            x.pop(k, None)
        for ln in x["links"]:
            for k in NEW_LINK:
                ln.pop(k, None)
    for side in ("wire", "solo"):
        d[side]["rows"] = [{k: v for k, v in r.items() if k not in NEW_LINK} for r in d[side]["rows"] if r["v"] is not None]
    return d


def officials(frame):
    return [a for a in outside(frame) if a["href"] != TAKEDOWN and not a["href"].startswith("https://t.me/")]


def order(frame, *needles):
    text = flat(frame["text"])
    return [text.index(flat(n)) for n in needles]


# ---------- 규칙 쪽과 같아야 하는 값 ----------


class MoreRulesTest(unittest.TestCase):
    def test_sizes_thresholds_and_official_domains_match_the_rules(self):
        rules = rules_block()
        self.assertEqual(tuple(rules["sizes"]), R.SIZES)                       # 길이 구간 이름 → 화면에 쓰는 말
        self.assertEqual((rules["size_short"], rules["size_long"]), (R.TH["size_short"], R.TH["size_long"]))
        self.assertEqual(rules["official_domains"], list(R.OFFICIAL_DOMAINS))

    def test_gloss_marks_are_those_of_the_gloss_table(self):
        self.assertEqual("".join(rules_block()["gloss_marks"]), "".join(gloss_marks()),
                         "\n풀이(digest_gloss.py)가 바뀌었다 — evening.js의 RULES에 아래를 붙여 넣는다:\n" + marks_block("gloss_marks", gloss_marks()))
        self.assertEqual(len(set(gloss_marks())), len(R.GLOSS))                # 지문이 겹치지 않는다

    def test_term_marks_are_those_of_the_dictionary(self):
        self.assertEqual("".join(rules_block()["term_marks"]), "".join(term_marks()),
                         "\n낱말 사전(digest_rules.py)이 바뀌었다 — evening.js의 RULES에 아래를 붙여 넣는다:\n" + marks_block("term_marks", term_marks()))
        self.assertEqual(len(set(term_marks())), len(R.TERMS))
        self.assertFalse(set(term_marks()) & set(gloss_marks()))

    @unittest.skipUnless(NODE, "node가 없다")
    def test_term_guard_takes_dictionary_words_only(self):
        """검토(2026-10-08 밤): 화면의 낱말 가드가 꼴만 봐서 낱말처럼 생긴 글자가 새 칸으로 그려졌다 — 사전의 지문과 견준다."""
        made = ["지어낸 낱말", "금리 상승", "서비스 물가", "CPI", "미 CPI ", "위험 선호", C1, C3]
        self.assertEqual(calls("term", *R.TERMS, *made, None, 7, ["금리"]), [*R.TERMS, *[None] * (len(made) + 3)])

    @unittest.skipUnless(NODE, "node가 없다")
    def test_mark_is_the_same_sum_in_both_languages(self):
        samples = ["", "a", "미 CPI\n" + CPI, *[t + "\n" + text for t, (text, _) in list(R.GLOSS.items())[:20]], C1, C5]
        self.assertEqual(calls("fingerprint", *samples), [mark(s) for s in samples])

    @unittest.skipUnless(NODE, "node가 없다")
    def test_official_guard_takes_the_listed_addresses_and_nothing_else(self):
        good = sorted(R.OFFICIAL_URLS)
        bad = ["http://fred.stlouisfed.org/series/CPIAUCSL", "https://evilstlouisfed.org/series/CPIAUCSL",
               "https://stlouisfed.org.evil.example/series/CPIAUCSL", "https://fred.stlouisfed.org@evil.example/x",
               "https://fred.stlouisfed.org:8443/x", "https://fred.stlouisfed.org", "//fred.stlouisfed.org/x",
               "https://FRED.stlouisfed.org/x", "https://fred.stlouisfed.org/x y", "https://fred.stlouisfed.org/<b>",
               "https://fred.stlouisfed.org/x#" + C1, "https://fred.stlouisfed.org/\\evil.example", "https://t.me/fxbond1/501",
               "javascript:alert(1)", "data:text/html,x", "https://" + C7, "https://fred.stlouisfed.org/" + "a" * 200, "", None, 7,
               ["https://fred.stlouisfed.org/x"]]
        got = calls("official", *good, *bad)
        self.assertEqual([g and g["url"] for g in got], good + [None] * len(bad))
        for g in got[:len(good)]:
            self.assertTrue(any(g["host"] == d or g["host"].endswith("." + d) for d in R.OFFICIAL_DOMAINS), g["host"])


# ---------- 그려 보기: 새 칸 ----------


@unittest.skipUnless(NODE, "node가 없다")
class MoreCardTest(Screen):
    @classmethod
    def setUpClass(cls):
        cls.frame = draw(site())

    def test_card_reads_as_one_sentence_made_from_a_fixed_frame(self):
        # 시각 범위는 '묶인 글'의 것이다(속보형·전달 글도 든다) — 그 채널들이 쓴 시각이라고 읽히지 않게 문장 밖에 적는다(검토 2026-10-08 밤)
        self.shows(self.frame, "채권 3곳 · 애널 2곳 · 개인 3곳이 함께 다뤘습니다.", "묶인 글 9건 · 10-07 21:32 ~ 10-08 09:00 · 속보형 1곳 겹침",
                   "채권 2곳 · 애널 1곳이 함께 다뤘습니다.", "묶인 글 3건 · 10-08 11:40 ~ 13:05", "묶인 글 2건 · 10-08 14:10 ~ 14:25")
        self.lacks(self.frame, "사이에 함께")
        only = fx("digest")
        only["must"][0]["coverage"] = {"bond": 4, "analyst": 0, "personal": 0, "wire": 0}
        self.shows(draw(site(digest=only)), "채권 채널 4곳이 함께 다뤘습니다.")

    def test_the_card_comes_before_the_note_about_sentences(self):
        """폰 첫 화면에 카드의 제목이 들어오게 안내 줄은 카드 뒤에 둔다(검토 2026-10-08 밤: 폭 375에서 카드 제목이 첫 화면 밖이었다)."""
        note = "채널 글의 문장은 싣지 않습니다 — 낱말은 미리 정한 사전에서 찾은 것이고, 풀이는 이 사이트가 쓴 것입니다"
        at = order(self.frame, "꼭 3건", "미 CPI · 미 국채 금리", note, "다가오는 일정")
        self.assertEqual(at, sorted(at))
        self.shows(self.frame, "내용은 원문 링크에서 읽어 주세요", "풀이는 낱말의 뜻이지 그 글의 내용이 아닙니다",
                   "나라를 밝히지 않은 지표는 미국 지표로 셉니다")

    def test_card_blocks_come_as_topic_then_links_then_words(self):
        """좁은 화면에서는 블록이 차례로 쌓인다 — 원문 링크가 낱말 표보다 먼저 온다(검토 2026-10-08 밤)."""
        at = order(self.frame, "미 CPI · 미 국채 금리", "원문 링크", "가상 채권 bond1 10-07 21:41", "함께 나온 낱말", "고른 이유", "규칙 점수 13.125")
        self.assertEqual(at, sorted(at))

    def test_words_come_with_counts_in_the_order_the_data_gives(self):
        d = fx("digest")
        words = [("미 주거비", 6), ("근원물가", 4), ("유가", 4), ("관세", 2), ("인플레", 2)]
        d["must"][0]["words"] = [{"term": t, "n_ch": n} for t, n in words]
        back = copy.deepcopy(d)
        back["must"][0]["words"].reverse()
        one, two = draws(site(digest=d), site(digest=back))
        rows = [f"{t}{n}곳" for t, n in words]
        self.assertEqual(order(one, "함께 나온 낱말", *rows), sorted(order(one, "함께 나온 낱말", *rows)))
        self.assertEqual(order(two, *rows[::-1]), sorted(order(two, *rows[::-1])))     # 화면이 다시 섞지 않는다
        pips = sum(a == "class=eve-pip" for a in one["attrs"])
        self.assertEqual(pips, sum(n for _, n in words))                        # 곳 수만큼의 작은 막대(다른 두 카드에는 낱말 표가 없다)
        self.shows(one, "그 낱말을 쓴 채널 수", "제목의 낱말과 전달 글은 빼고")
        self.shows(self.frame, "미 주거비 2곳")                                   # 지어낸 판의 첫 카드 — 제목(미 CPI) 밖의 낱말

    def test_sixteen_shared_words_are_all_on_the_card(self):
        """검토(2026-10-08 밤): 두 곳 이상이 쓴 낱말 19개 중 11개가 카드 어디에도 없었다 — 16개까지 다 그린다."""
        names = [t for t in R.by_grade(R.TERMS) if t not in ("미 CPI", "미 국채 금리")][:17]
        d = fx("digest")
        d["must"][0]["words"] = [{"term": t, "n_ch": 2} for t in names]
        frame = draw(site(digest=d))
        self.shows(frame, *[f"{t} 2곳" for t in names[:16]])
        self.lacks(frame, f"{names[16]} 2곳")

    def test_many_channels_do_not_stretch_the_bar(self):
        d = fx("digest")
        d["must"][0]["words"] = [{"term": "미 주거비", "n_ch": 40}]
        frame = draw(site(digest=d))
        self.shows(frame, "미 주거비 40곳")
        self.assertEqual(sum(a == "class=eve-pip" for a in frame["attrs"]), 12)

    def test_previous_edition_is_named_as_the_same_word_not_the_same_story(self):
        """검토(2026-10-08 밤): 대표 낱말 하나가 같다고 '같은 주제 · N곳 늘었습니다'라고 쓰지 않는다."""
        self.shows(self.frame, "대표 낱말이 직전 판 10-07(수)에도 있었습니다", "그때 채권 2 · 개인 1 → 이번 채권 3 · 애널 2 · 개인 3",
                   "낱말이 같을 뿐 같은 묶음이 아닐 수 있습니다")
        self.assertEqual(flat(self.frame["text"]).count(flat("에도 있었습니다")), 1)     # 칸이 있는 항목에만
        self.lacks(self.frame, "나온 주제", "늘었습니다", "줄었습니다", "곳 수는 같습니다")

    def test_source_rows_tell_the_posts_apart(self):
        d = fx("digest")
        d["must"][0]["links"][0]["size"], d["must"][0]["links"][2]["size"] = "김", "보통"
        frame = draw(site(digest=d))
        self.shows(frame, "가상 채권 bond1 10-07 21:41 긴 글 사전 낱말 2개 공통 낱말만", "가상 채권 bond3 10-08 07:30 보통 길이 사전 낱말 1개",
                   "가상 애널 anal2 10-08 08:05 짧은 글 그림·파일 있음 사전 낱말 1개", "가상 채권 bond4 10-08 11:40 짧은 글 그림·파일 있음 사전 낱말 2개 이 글에서 더: 금리",
                   "이 글에서 더: 장기물 수요", "이 글에서 더: 가계부채",
                   "채널마다 한 글 · 묶인 글 9건 중 6건")                        # 링크는 채널마다 하나다 — 묶인 글이 더 많으면 그렇다고 적는다
        self.lacks(frame, "묶인 글 3건 중", "묶인 글 2건 중")
        self.assertEqual(posts(frame), posts(self.frame))                       # 새 칸이 링크를 바꾸지 않는다

    def test_lead_term_is_explained_on_the_card_and_the_rest_unfold(self):
        self.shows(self.frame, "미 CPI " + CPI, "국고채 입찰 국고채 경쟁입찰. 국고채전문딜러(PD)가 응찰한다")
        self.assertTrue(any(flat(f).startswith(flat("다른 낱말 풀이 2개")) for f in self.frame["folds"]), self.frame["folds"])
        cpi = [a for a in officials(self.frame) if a["href"] == "https://fred.stlouisfed.org/series/CPIAUCSL"]
        self.assertGreaterEqual(len(cpi), 2)                                    # 카드에 한 번, 풀이 절에 한 번
        for a in officials(self.frame):
            self.assertIn(a["href"], R.OFFICIAL_URLS)
            self.assertEqual((a["target"], a["rel"]), ("_blank", "noopener noreferrer"), a["href"])
            self.assertTrue(a["text"].startswith(kind_of(a["href"]) + " · "), a)
        self.assertTrue(any(a.startswith("aria-label=미 CPI 시계열") for a in self.frame["attrs"]))

    def test_st_louis_fed_pages_are_not_called_official(self):
        """검토(2026-10-08 밤): FRED는 통계를 내는 곳이 아니라 모아 싣는 곳이다 — '시계열' · '문서 모음'이라고 적는다."""
        d = fx("digest")
        d["tomorrow"][0]["term"] = "연준 의사록"
        d["gloss"] = R.glosses(S.shown_terms(d))
        names = {a["href"]: a["text"] for a in officials(draw(site(digest=d)))}
        self.assertEqual({kind_of(h) for h in names}, {"시계열", "문서 모음", "공식 자료"})
        for href, text in names.items():
            self.assertTrue(text.startswith(kind_of(href) + " · "), text)
        self.assertEqual(names[R.GLOSS["연준 의사록"][1]], "문서 모음 · fraser.stlouisfed.org")
        self.assertEqual(names[R.GLOSS["미 CPI"][1]], "시계열 · fred.stlouisfed.org")
        self.assertEqual(names[R.GLOSS["국고채 입찰"][1]], "공식 자료 · ktb.mofe.go.kr")

    def test_glossary_lists_every_term_on_the_screen_once(self):
        d = fx("digest")
        heads = self.frame["heads"]
        self.assertLess(heads.index("참고 링크"), heads.index("낱말 풀이"))
        self.assertTrue(any(flat(f).startswith(flat(f"풀이 {len(d['gloss'])}개")) for f in self.frame["folds"]), self.frame["folds"])
        self.shows(self.frame, f"이 판에 나온 낱말 가운데 {len(d['gloss'])}개", *[g["text"] for g in d["gloss"]])
        text = flat(self.frame["text"])
        tail = text[text.index(flat(f"이 판에 나온 낱말 가운데 {len(d['gloss'])}개")):]
        for g in d["gloss"]:
            self.assertEqual(tail.count(flat(g["text"])), 1, g["term"])
        self.assertEqual(len([a for a in self.frame["attrs"] if a.startswith("open=")]), 2)      # 풀이는 접어 둔다(펼친 것은 나머지 표 둘)

    def test_rest_rows_carry_the_same_things_briefly(self):
        self.shows(self.frame, "함께 나온 낱말: 빅테크 실적 2곳", "글 4건 · 10-08 06:20 ~ 08:30",
                   "가상 애널 anal4 10-08 07:55 · 짧은 글 · 사전 낱말 4개", "글 5건 · 10-08 10:02 ~ 10:40")
        self.lacks(self.frame, "함께 나온 낱말: 관세", "글 1건 · 10-08")            # 제목의 낱말뿐이거나 글 하나면 되풀이하지 않는다
        d = fx("digest")
        multi = d["rest"][0]["items"][0]                                        # 두 곳이 쓴 줄 — 링크마다 '더:'가 따로 붙는다
        multi["links"][0]["more"], multi["links"][1]["fwd"] = ["유가"], True
        lone = d["rest"][1]["items"][0]                                         # 채권 한 곳만 쓴 글 — 낱말은 모두 1곳
        lone["words"] = [{"term": t, "n_ch": 1} for t in ("기준금리", "가계부채")]
        lone["links"][0]["more"] = ["유가"]
        lone["prev"] = {"date": "2026-10-07", "bond": 1, "analyst": 0, "personal": 0}
        frame = draw(site(digest=d))
        # 한 곳뿐인 글은 그 글의 낱말을 한 줄로 합친다 — '이 글의 다른 낱말'과 '더:'로 갈라 부르지 않는다(검토 2026-10-08 밤)
        self.shows(frame, "이 글의 낱말: 기준금리 · 가계부채 · 유가", "대표 낱말이 직전 판 10-07(수)에도 있음",
                   "가상 애널 anal4 10-08 07:55 · 짧은 글 · 사전 낱말 4개 · 더: 유가", "가상 개인 pers4 10-08 08:30 · 전달 · 짧은 글")
        self.lacks(frame, "기준금리 1곳", "이 글의 다른 낱말", "가계부채 · 유가 · 더")
        self.assertEqual(flat(frame["text"]).count(flat("더: 유가")), 1)

    def test_lone_bond_posts_stand_under_their_channel_and_show_their_body_words(self):
        """검토(2026-10-08 밤): 본문에 낱말이 10개 넘게 걸린 채권 글이 '낱말 없는 글' 뒤에 접혀 있었다 — 첫머리에 낱말이 없으면 본문 낱말로
        부르고, 사전 낱말이 정말 없는 글만 접는다. 채널 이름은 줄마다 되풀이하지 않고 채널별로 묶는다."""
        d = fx("digest")
        a, b = d["rest"][1]["items"][0], d["rest"][2]["items"][0]               # fxbond1-502 · fxbond3-89
        b["terms"] = []
        b["words"] = [{"term": t, "n_ch": 1} for t in ("국고채 입찰", "유가", "커브")]
        b["links"][0]["more"] = ["국고채 금리"]
        bare = {**copy.deepcopy(a), "id": "20261008-fxbond1-503", "terms": [], "links": [{**a["links"][0], "url": "https://t.me/fxbond1/503"}]}
        bare["links"][0].pop("more", None)
        d["rest"][1]["items"].append(bare)
        frame = draw(site(digest=d))
        self.shows(frame, "가상 채권 bond1 1건", "가상 채권 bond3 1건", "15:20 통화정책 / 국내 금통위 의사록 · 소수의견 · 국고채 금리",
                   "본문 낱말 국고채 입찰 · 유가", "이 글의 낱말: 커브 · 국고채 금리")
        folds = [flat(f) for f in frame["folds"]]
        self.assertEqual(sum(f.startswith(flat("사전 낱말이 없는 글 1건")) for f in folds), 1, folds)      # 정말 빈 글 하나만 접힌다
        self.lacks(frame, "대표 낱말 없음")
        for url in ("https://t.me/fxbond1/502", "https://t.me/fxbond3/89", "https://t.me/fxbond1/503"):
            self.assertIn(url, posts(frame))
        self.assertTrue(any(a.startswith("aria-label=가상 채권 bond3 원문 10-08 16:05") for a in frame["attrs"]))

    def test_rows_named_by_body_words_do_not_repeat_them_per_link_and_lone_bond_rows_go_by_time(self):
        d = fx("digest")
        both = d["rest"][0]["items"][0]                                         # 두 곳의 줄 — 대표 낱말 없이 링크의 덧낱말만 있는 경우(전달 글뿐인 묶음)
        both["terms"], both["nums"] = [], []
        both.pop("words", None)
        for ln in both["links"]:
            ln["more"], ln["fwd"] = ["미 PPI", "데이터센터"], True
        both["links"][1]["more"] = ["미 PPI", "유가"]
        a = d["rest"][1]["items"][0]                                            # fxbond1-502(15:20) 앞에 같은 채널의 더 이른 글을 뒤에 놓는다
        early = {**copy.deepcopy(a), "id": "20261008-fxbond1-499", "terms": ["관세"]}
        early["links"][0].update(url="https://t.me/fxbond1/499", at="2026-10-08T09:10:00+09:00")
        d["rest"][-1]["items"].append({**early, "cell": {"factor": "기타", "region": "글로벌"}})
        frame = draw(site(digest=d))
        self.shows(frame, "본문 낱말 미 PPI · 데이터센터", "가상 개인 pers4 10-08 08:30 · 전달 · 짧은 글 · 사전 낱말 3개 · 더: 유가", "가상 채권 bond1 2건")
        self.assertEqual(flat(frame["text"]).count(flat("더: 미 PPI")), 0)        # 제목에 쓴 낱말을 링크마다 되풀이하지 않는다
        at = order(frame, "가상 채권 bond1 2건", "09:10 기타 관세", "15:20 통화정책 / 국내 금통위 의사록")
        self.assertEqual(at, sorted(at))                                        # 칸 순서가 아니라 올린 시각순

    def test_side_rows_without_a_number_are_drawn(self):
        self.shows(self.frame, "가상 개인 pers8 2건 중 1건", "15:30 한은 발언 · 가계부채 · 기준금리 짧은 글",
                   "첫 두 줄에 사전 낱말이 있는 글(A·B급 낱말이 있거나 낱말이 둘 이상인 글)을 채널당 5줄까지",
                   "낱말은 그 글에 나온 것을 등급순으로", "숫자가 붙은 줄은 한 곳만 쓴 숫자입니다")
        self.lacks(self.frame, "주요 낱말이 있는 글", "한은 발언 더:")
        many = fx("digest")
        many["solo"]["rows"][1]["n_terms"] = 12                                 # 줄에 실린 것보다 낱말이 많은 글은 그 수를 적는다
        self.shows(draw(site(digest=many)), "15:30 한은 발언 · 가계부채 · 기준금리 짧은 글 사전 낱말 12개")
        self.lacks(self.frame, "기준금리 짧은 글 사전 낱말")                       # 줄에 다 실린 글에는 수를 되풀이하지 않는다
        self.assertIn("https://t.me/fxpers8/56", posts(self.frame))
        d = fx("digest")
        d["solo"]["rows"][1]["v"] = "3.1% " + C1                                # 숫자 칸이 깨졌으면 그 줄은 뺀다(숫자 없는 줄로 살리지 않는다)
        d["solo"]["rows"][0]["v"] = None
        d["solo"]["rows"][0]["result"] = "상회"
        frame = draw(site(digest=d))
        self.assertNotIn("https://t.me/fxpers8/56", posts(frame))
        self.assertIn("https://t.me/fxpers6/73", posts(frame))
        self.lacks(frame, "12.5조원", "국고채 발행계획 · 상회")                    # 숫자가 없으면 결과 낱말도 쓰지 않는다
        self.assertEqual(F.leaks(blob(frame)), [])

    def test_source_note_names_what_is_new(self):
        self.shows(self.frame, "글 길이 구간(200자 미만 짧은 글 · 700자 이상 긴 글)", "그림·파일이 붙었는지", "그 글에서 걸린 사전 낱말의 수",
                   "낱말 풀이는 채널의 글이 아니라 이 사이트가 직접 쓴 한 줄입니다", "'공식 자료' 링크는 공공 기관의 쪽",
                   "세인트루이스 연은이 통계와 문서를 모아 싣는 쪽(FRED · FRASER)", "민간 기관이 내는 지표도")
        self.lacks(self.frame, "그 통계·회의를 내는 공공 기관의 고정 쪽")

    def test_nothing_planted_is_on_the_screen(self):
        self.assertEqual(F.leaks(blob(self.frame)), [])
        for bad in ("undefined", "NaN", "[object", "null"):
            self.assertNotIn(bad, self.frame["text"])


@unittest.skipUnless(NODE, "node가 없다")
class MoreDirtyTest(Screen):
    def test_a_gloss_is_drawn_only_when_it_is_ours(self):
        d = fx("digest")
        by = {g["term"]: g for g in d["gloss"]}
        made = "서비스 물가가 끈적하다는 평가가 많다는 지어낸 문장"
        by["미 CPI"]["text"] = made                                             # 풀이 꼴의 다른 문장
        by["국고채 입찰"]["text"] = C3
        by["한은 발언"]["text"] = C4
        by["유가"]["text"] = by["미 PPI"]["text"]                                # 다른 낱말의 풀이
        by["WGBI"]["text"] = by["WGBI"]["text"] + " "
        by["ISM"]["term"] = C5
        d["gloss"] += [None, 7, "풀이", {"term": "관세"}, {"term": "관세", "text": ["x"], "url": None},
                       {"term": "관세", "text": CPI, "url": None}]
        frame = draw(site(digest=d))
        self.assertEqual(F.leaks(blob(frame)), [])
        self.lacks(frame, made, "미 CPI " + CPI, "세계국채지수", "유가 미국 생산자물가지수")
        self.assertEqual(flat(frame["text"]).count(flat(by["미 PPI"]["text"])), 1)        # 제 낱말 밑에서만 한 번
        self.shows(frame, "꼭 3건", "미 CPI · 미 국채 금리", f"이 판에 나온 낱말 가운데 {len(fx('digest')['gloss']) - 6}개")
        self.assertEqual([a for a in officials(frame) if "CPIAUCSL" in a["href"]], [])   # 풀이가 빠지면 그 링크도 없다

    def test_only_official_https_addresses_become_links(self):
        d = fx("digest")
        linked = [g for g in d["gloss"] if g["url"]]
        bad = ["http://fred.stlouisfed.org/series/CPIAUCSL", "https://evilstlouisfed.org/x", "https://stlouisfed.org.evil.example/x",
               "https://fred.stlouisfed.org@evil.example/x", "javascript:alert(1)", "https://t.me/fxbond1/501", "https://" + C7]
        self.assertGreaterEqual(len(linked), len(bad))
        for g, url in zip(linked, bad):
            g["url"] = url
        frame = draw(site(digest=d))
        self.assertEqual(sorted({a["href"] for a in officials(frame)}), sorted(g["url"] for g in linked[len(bad):]))
        self.assertNotRegex(blob(frame), r"evil|javascript:|http://")
        self.assertEqual(posts(frame), posts(draw(site())))                     # 풀이의 주소가 원문 링크가 되지도 않는다
        self.shows(frame, *[g["text"] for g in linked])                         # 주소가 걸러져도 풀이 글자는 남는다
        self.assertEqual(F.leaks(blob(frame)), [])

    def test_broken_new_fields_leave_the_item_standing(self):
        junk = [7, "깨짐", [None, 3, "x", {}, {"term": C3, "n_ch": 2}, {"term": "미 CPI", "n_ch": "많음"}], {"from": C1, "to": 5, "posts": "x"},
                {"date": "어제", "bond": "x"}, True]
        frames = []
        for bad in junk:
            d = fx("digest")
            for x in d["must"] + [x for g in d["rest"] for x in g["items"]]:
                x.update(words=bad, span=bad, prev=bad)
                for ln in x["links"]:
                    ln.update(more=bad, size=bad, pic=bad)
            for r in d["wire"]["rows"] + d["solo"]["rows"]:
                r.update(more=bad, size=bad, pic=bad)
            d["gloss"] = bad
            frames.append(site(digest=d))
        for frame in draws(*frames):
            self.shows(frame, "꼭 3건", "미 CPI · 미 국채 금리", "미 CPI · 상회 · 3.1%", "채권 3곳 · 애널 2곳 · 개인 3곳이 함께 다뤘습니다.",
                       "가상 개인 wire1 7건 중 5건", "채권 채널 단독 글", "가상 채권 bond1 1건")
            self.assertEqual(posts(frame), posts(draw(site())))
            self.assertEqual(F.leaks(blob(frame)), [])
            for bad in ("undefined", "NaN", "[object", "그리지 못했습니다"):
                self.assertNotIn(bad, frame["text"])
            self.assertNotIn("낱말 풀이", frame["heads"])
            self.assertFalse(any("풀이" in f for f in frame["folds"]), frame["folds"])

    def test_sentences_in_the_new_word_lists_are_not_drawn(self):
        d = fx("digest")
        d["must"][0]["words"] = [{"term": C3, "n_ch": 5}, {"term": C4, "n_ch": 4}, {"term": "미 CPI", "n_ch": 3}]
        d["must"][0]["links"][1]["more"] = [C5, C7, "미 주거비"]
        d["must"][0]["links"][1]["size"] = C1
        d["solo"]["rows"][1]["more"] = [C3, "가계부채"]
        frame = draw(site(digest=d))
        self.assertEqual(F.leaks(blob(frame)), [])
        self.shows(frame, "미 CPI 3곳", "이 글에서 더: 미 주거비", "15:30 한은 발언 · 가계부채")
        self.assertNotRegex(blob(frame), "canary")

    def test_word_shaped_text_that_is_not_in_the_dictionary_is_not_drawn(self):
        """검토(2026-10-08 밤): 낱말 꼴(20자 이하)의 지어낸 글자가 새 낱말 칸으로 그려졌다 — 사전의 지문과 견줘 거른다."""
        d = fx("digest")
        made = ["지어낸 낱말 하나", "서비스 물가 끈적", "금리 급등 전망"]
        d["must"][0]["words"] = [{"term": made[0], "n_ch": 5}, {"term": "미 주거비", "n_ch": 3}]
        d["must"][0]["links"][1]["more"] = [made[1], "유가"]
        d["must"][0]["terms"] = ["미 CPI", made[2]]
        d["solo"]["rows"][1]["more"] = [made[0], "가계부채"]
        d["rest"][0]["items"][0]["terms"] = [made[1]]
        d["head"]["top_terms"] = [made[2], "미 CPI"]
        d["gloss"] += [{"term": made[0], "text": CPI, "url": None}]
        frame = draw(site(digest=d))
        self.lacks(frame, *made)
        self.shows(frame, "미 주거비 3곳", "이 글에서 더: 유가", "15:30 한은 발언 · 가계부채", "가장 많이 다뤄진 주제: 미 CPI")

    def test_hidden_items_take_their_glosses_along(self):
        d = fx("digest")
        gone = d["must"][1]
        kept = S.shown_terms({**d, "must": [x for x in d["must"] if x is not gone]})
        lost = [g for g in d["gloss"] if g["term"] not in kept]
        self.assertTrue(lost)                                                   # 그 항목에만 나온 낱말이 있다
        frame = draw(site(overrides=F.overrides(hide_ids=[gone["id"]])))
        self.lacks(frame, *[g["text"] for g in lost])
        self.shows(frame, f"이 판에 나온 낱말 가운데 {len(d['gloss']) - len(lost)}개", CPI)
        down = draw(site(overrides=F.overrides(withdraw=True)))
        self.lacks(down, CPI)                                                   # 내린 판에는 풀이도 없다
        self.assertNotIn("낱말 풀이", down["heads"])

    def test_official_links_do_not_need_the_source_list(self):
        frame = draw(site(sources=None))
        self.assertEqual([a["href"] for a in outside(frame) if a["href"].startswith("https://t.me/")], [])
        self.assertTrue(officials(frame))                                       # 공식 자료는 채널 목록과 무관하다
        for a in officials(frame):
            self.assertIn(a["href"], R.OFFICIAL_URLS)


# ---------- 그려 보기: 옛 형태 ----------


@unittest.skipUnless(NODE, "node가 없다")
class OldShapeTest(Screen):
    def test_an_edition_without_the_new_fields_draws_as_before(self):
        old = old_shape(fx("digest"))
        S.validate_digest(old, fx("sources"))                                   # 옛 형태도 계약에 맞는 판이다
        frame, new = draws(site(digest=old), site())
        self.shows(frame, "저녁판 2026-10-08(목)", "꼭 3건", "미 CPI · 미 국채 금리", "미 CPI · 상회 · 3.1% 8곳",
                   "채권 3곳 · 애널 2곳 · 개인 3곳이 함께 다뤘습니다.", "속보형 1곳 겹침", "가상 채권 bond1 10-07 21:41", "규칙 점수 13.125",
                   "통화정책 / 국내 금통위 의사록 · 소수의견 · 국고채 금리", "08:01 미 PPI · 부합 0.2%", "국고채 발행계획 12.5조원",
                   "줄 없이 건수만: 가상 개인 wire2 1건", "가상 개인 pers8 2건")
        self.lacks(frame, "함께 나온 낱말", "이 글에서 더", "사이에", "묶인 글", "직전 판", "그림·파일 있음", "가상 개인 pers8 2건 중",
                   "공통 낱말만", "이 글의 낱말", "채널마다 한 글", "본문 낱말")
        self.assertNotIn("낱말 풀이", frame["heads"])
        self.assertFalse(any("풀이" in f for f in frame["folds"]), frame["folds"])
        self.assertFalse(any(a == "class=eve-tag" for a in frame["attrs"]))
        self.assertEqual(posts(frame), [u for u in posts(new) if u != "https://t.me/fxpers8/56"])
        self.assertEqual(officials(frame), [])
        self.assertFalse(any(a == "class=eve-pip" for a in frame["attrs"]))
        for bad in ("undefined", "NaN", "[object", "null", "그리지 못했습니다"):
            self.assertNotIn(bad, frame["text"])

    def test_published_editions_draw_with_the_screen_as_it_is_now(self):
        data = os.path.join(REPO, "data")
        names = ["digest.json", *sorted("digest/" + os.path.basename(p) for p in glob.glob(os.path.join(data, "digest", "*.json")))]
        human = {n: S.read_json(os.path.join(data, n)) for n in ("sources.json", "digest_overrides.json", "digest_index.json")}
        handles = {c["handle"] for c in human["sources.json"]["channels"]}
        editions = [S.read_json(os.path.join(data, *n.split("/"))) for n in names if os.path.isfile(os.path.join(data, *n.split("/")))]
        if not editions:
            self.skipTest("게시된 판이 없다")
        frames = draws(*[({**{"data/" + k: v for k, v in human.items()}, "data/digest.json": d}, d["collected_at"]) for d in editions])
        for d, frame in zip(editions, frames):
            day = d["date"]
            self.shows(frame, f"저녁판 {day}")
            for bad in ("undefined", "NaN", "[object", "그리지 못했습니다"):
                self.assertNotIn(bad, frame["text"], day)
            shown = d["status"] == "ok" and not human["digest_overrides.json"]["withdraw"]
            self.assertEqual(bool(posts(frame)), shown and bool(d["must"] or d["rest"]), day)
            if shown and d["must"]:
                self.shows(frame, f"꼭 {len(d['must'])}건", "함께 다뤘습니다.")
            for a in outside(frame):
                m = POST.match(a["href"]) or a["href"].startswith("https://t.me/")
                ok = a["href"] == TAKEDOWN or a["href"] in R.OFFICIAL_URLS or (m and a["href"].split("/")[3] in handles)
                self.assertTrue(ok, day)


if __name__ == "__main__":
    unittest.main()
