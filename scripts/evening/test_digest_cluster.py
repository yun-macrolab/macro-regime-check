#!/usr/bin/env python3
"""저녁판 묶기(digest_cluster) 테스트 — 열쇠마다 같은 일을 다룬 글이 묶이는지, 붙는 글이 두 묶음을 잇지 않는지, 원문이 남지 않는지.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요 — 글은 전부 지어낸 것이고 채널은 fixtures.py의 가짜 이름이다.
"""
import contextlib
import copy
import io
import os
import subprocess
import sys
import tempfile
import unicodedata
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_cluster as DC
import digest_rules as R
import digest_schema as S
import fixtures as F

# 사전 낱말·숫자가 없는 지어낸 글(서로 닮지 않았다)
PLAIN = ("봄 소풍 도시락을 싸는 순서를 길게 적어 두었다.", "겨울 산행에 챙길 준비물 목록을 다시 훑어보았다.",
         "가을 독서 모임에서 나온 이야기를 간단히 남긴다.", "여름 바다에서 주운 조개껍데기를 색깔별로 나눴다.",
         "동네 빵집의 새 메뉴를 하나씩 먹어 본 기록이다.", "주말 농장에 심은 상추가 벌써 손바닥만큼 자랐다.")
URL_A, URL_B, URL_C = "https://news.example.com/a/1", "https://news.example.com/b/2", "https://news.example.com/c/3"
CARD = {"title": "지어낸 기사 제목: 어느 마을의 가을 축제 소식", "site": "지어낸신문"}


def post(ch, pid, when, text, links=(), fwd=None, card=None):
    """지어낸 글 하나. when = "일 시:분"(2026-10, 수집 창 안)."""
    return {"ch": ch, "id": pid, "at": f"2026-10-{when[:2]}T{when[3:]}:00+09:00", "text": text, "links": list(links),
            "fwd": fwd and {"ch": fwd[0], "id": fwd[1]}, "card": card and dict(card), "reply": False, "media": not text,
            "via": "search" if F.ROLE[ch] == "wire" else "page"}


def run(*posts, events=()):
    """글들을 묶고 계약대로인지 본 뒤 돌려준다."""
    doc = {**F.posts_doc(), "posts": sorted(posts, key=lambda p: (p["at"], p["ch"], p["id"]))}
    return S.validate_clusters_doc(DC.cluster_posts(S.validate_posts_doc(doc), F.collect_status(), events))


def where(out):
    """{(채널, 글 번호): 묶음 번호}"""
    return {(m["ch"], m["id"]): i for i, c in enumerate(out["clusters"]) for m in c["members"]}


def same(out, *ids):
    return len({where(out)[i] for i in ids}) == 1


def of(out, ident):
    return out["clusters"][where(out)[ident]]


def kinds(c):
    return {k[0] for k in c["keys"]}


class LinkTest(unittest.TestCase):
    def test_tracking_and_host_noise_are_removed(self):
        forms = ["https://news.example.com/a/1", "http://www.news.example.com/a/1/", "https://news.example.com/a/1?ref=share",
                 "https://m.news.example.com/a/1?utm_source=tg&utm_medium=social&fbclid=abc#top"]
        self.assertEqual({DC.norm_link(u) for u in forms}, {("u", "news.example.com/a/1")})
        self.assertEqual(DC.norm_link("https://news.example.com/a/1?utm_medium=x&id=7"), ("u", "news.example.com/a/1?id=7"))
        self.assertNotEqual(DC.norm_link("https://news.example.com/a/1?id=7"), DC.norm_link("https://news.example.com/a/1?id=8"))

    def test_videos_and_naver_news_are_matched_by_id(self):
        tube = ["https://youtu.be/AbCdEfGhIjK", "https://www.youtube.com/watch?v=AbCdEfGhIjK&t=120s",
                "https://m.youtube.com/watch?v=AbCdEfGhIjK", "https://youtube.com/shorts/AbCdEfGhIjK?si=zz"]
        self.assertEqual({DC.norm_link(u) for u in tube}, {("u", "youtube:AbCdEfGhIjK")})
        naver = ["https://n.news.naver.com/mnews/article/001/0012345678?sid=101", "https://n.news.naver.com/article/001/0012345678",
                 "https://news.naver.com/main/read.naver?mode=LSD&oid=001&aid=0012345678",
                 "https://m.news.naver.com/read?oid=001&aid=0012345678"]
        self.assertEqual({DC.norm_link(u) for u in naver}, {("u", "naver:001/0012345678")})

    def test_a_link_to_a_post_is_forward_material(self):
        self.assertEqual(DC.norm_link("https://t.me/fxbond1/501"), ("f", "fxbond1/501"))
        self.assertEqual(DC.norm_link("https://t.me/s/FxBond1/501?single"), ("f", "fxbond1/501"))
        self.assertIsNone(DC.norm_link("https://t.me/fxbond1"))                      # 채널 첫 화면

    def test_short_links_are_kept_as_they_are(self):
        self.assertEqual(DC.norm_link("https://sho.example/x1"), ("u", "sho.example/x1"))
        self.assertNotEqual(DC.norm_link("https://sho.example/x1"), DC.norm_link("https://bit.example/yy"))

    def test_what_is_not_an_article_gives_no_key(self):
        for bad in ("https://news.example.com/", "https://news.example.com", "ftp://x.example/a", "javascript:alert(1)", "", None, 7,
                    "https://[bad", "그냥 글자"):
            self.assertIsNone(DC.norm_link(bad), bad)

    def test_footer_links_are_those_repeated_on_one_channel(self):
        foot = "https://blog.example.com/my-page"
        mine = [post("fxpers1", i, f"08 0{i}:00", PLAIN[i], [foot, f"https://news.example.com/x/{i}"]) for i in (1, 2, 3)]
        other = post("fxpers2", 9, "08 09:00", PLAIN[4], [foot])
        got = DC.footer_links(mine + [other])
        self.assertEqual(got["fxpers1"], {("u", "blog.example.com/my-page")})
        self.assertEqual(got["fxpers2"], set())
        out = run(*mine, other)
        self.assertEqual(len(out["clusters"]), 4)                                    # 꼬리말 링크로는 묶이지 않는다
        tiny = [post("fxpers3", i, f"08 1{i}:00", "짧은 글", [foot]) for i in (1, 2, 3)]
        self.assertEqual(run(*tiny)["stats"]["dropped"]["short"], 3)                 # 꼬리말뿐인 짧은 글은 링크 없는 글이다


class LeadTest(unittest.TestCase):
    def test_lead_is_the_first_two_lines_and_at_most_eighty_chars(self):
        cap = R.TH["lead_chars"]
        self.assertEqual(DC.lead_end("가" * 200), cap)                               # 줄을 나누지 않은 글
        self.assertEqual(DC.lead_end("제목 줄\n둘째 줄\n셋째 줄 " + "가" * 100), len("제목 줄 둘째 줄"))
        self.assertEqual(DC.lead_end("제목\n\n \n둘째\n셋째"), len("제목 둘째"))       # 빈 줄은 세지 않는다
        self.assertEqual(DC.lead_end("가" * 60 + "\n" + "나" * 60 + "\n다"), cap)
        self.assertEqual(DC.lead_end("첫 줄\n둘째 줄"), cap)
        self.assertEqual(DC.lead_end(""), cap)

    def test_mention_keeps_closed_values_and_marks_the_lead(self):
        text = f"미 CPI 3.1% 상회\n근원은 0.3% {F.C1}\n" + "그 밖의 이야기를 길게 적는다. " * 4 + "유가는 2.1% 내렸고 예상 하회."
        m = DC.mention(post("fxbond1", 1, "08 09:00", text), "bond", "source")
        self.assertEqual((m["terms"], m["lead"]), (["미 CPI", "유가"], ["미 CPI"]))
        self.assertEqual((m["nums"], m["lead_nums"]), (["3.1%", "0.3%", "2.1%"], ["3.1%", "0.3%"]))
        self.assertEqual(m["results"], ["상회"])                                     # 첫머리의 결과 낱말만
        self.assertEqual(set(m), {"ch", "id", "at", "group", "role", "fwd", "terms", "lead", "results", "nums", "lead_nums", "row"})
        self.assertEqual(F.leaks(S.dump(m)), [])
        self.assertEqual(DC.lead_top(m), "미 CPI")
        self.assertIsNone(DC.lead_top({**m, "lead": []}))
        self.assertEqual(DC.lead_top({**m, "lead": ["금리", "외국인 국채선물", "미 고용"]}), "외국인 국채선물")    # 먼저 나온 A·B급
        self.assertEqual(DC.lead_top({**m, "lead": ["금리", "원/달러 환율"]}), "금리")

    def test_row_pairs_the_first_lead_number_with_the_term_before_it(self):
        row = lambda text: DC.mention(post("fxpers1", 1, "08 09:00", text), "personal", "source")["row"]
        self.assertEqual(row("미 CPI 3.1%로 나왔다는 지어낸 글"), {"term": "미 CPI", "v": "3.1%"})
        self.assertEqual(row("금통위 얘기 조금. 유가는 2.1% 내렸다는 지어낸 글"), {"term": "유가", "v": "2.1%"})    # 숫자 앞의 가장 가까운 낱말
        self.assertIsNone(row("지어낸 가게 매출이 1.45% 늘었다. 유가 얘기는 뒤에 적는다."))            # 숫자가 낱말보다 앞
        self.assertIsNone(row("유가 얘기로 시작해서 지어낸 가게들의 등락을 길게 늘어놓는다. 첫째 1.45%"))    # 한 곳만 쓴 숫자는 낱말 바로 곁이어야 한다
        self.assertIsNone(row("미 PCE 1234567.891명이라는 지어낸 숫자"))                              # 긴 숫자(전화번호 크기)
        self.assertIsNone(row("금통위 인하 폭이 25%p라는 지어낸 오타"))                               # 상식 밖의 %p
        self.assertIsNone(row("유가 85달러 얘기 뒤에 미 CPI 3.1%"))                                  # 첫 숫자가 시세 수준 — 다음 숫자로 넘어가지 않는다
        self.assertIsNone(row("환율 얘기 끝에 3.1%"))                                               # C급 낱말뿐
        self.assertIsNone(row("미 CPI 얘기만 있고 숫자는 없는 지어낸 글"))
        self.assertIsNone(row("첫 줄에는 아무것도 없다\n둘째 줄도 마찬가지다\n미 CPI 3.1%는 셋째 줄"))   # 첫머리 밖

    def test_plain_texts_carry_no_terms(self):
        for t in PLAIN:
            self.assertEqual((R.match_terms(t), R.find_nums(t), R.drop_code(t)), ([], [], None), t)


class KeyTest(unittest.TestCase):
    """열쇠 하나씩 — 다른 열쇠가 걸리지 않게 개인 채널의 서로 다른 글로 본다(주제 열쇠만 채권·애널)."""

    def test_u_same_article(self):
        out = run(post("fxpers1", 1, "08 09:00", PLAIN[0], [URL_A + "?utm_source=x"]),
                  post("fxpers2", 2, "08 09:30", PLAIN[1], ["http://www." + URL_A[8:] + "/#top"]),
                  post("fxpers3", 3, "08 09:40", PLAIN[2], [URL_B]))
        self.assertTrue(same(out, ("fxpers1", 1), ("fxpers2", 2)))
        bare = run(post("fxbond1", 1, "08 09:00", "", [URL_A]), post("fxanal1", 2, "08 09:30", PLAIN[1], [URL_A + "?ref=share"]),
                   post("fxbond2", 3, "08 09:40", "", []))
        self.assertTrue(same(bare, ("fxbond1", 1), ("fxanal1", 2)))                  # 주소뿐인 글(본문이 빈다)도 같은 주소로 묶인다
        self.assertEqual((bare["stats"]["kept"], bare["stats"]["dropped"]["empty"]), (2, 1))   # 본문도 링크도 없는 글만 버린다
        self.assertFalse(same(out, ("fxpers1", 1), ("fxpers3", 3)))
        c = of(out, ("fxpers1", 1))
        self.assertEqual(c["keys"], [S.key_of("u", "news.example.com/a/1")])
        self.assertEqual(c["seed"], {"ch": "fxpers1", "id": 1})

    def test_f_forward_of_the_same_post(self):
        out = run(post("fxpers1", 10, "08 09:00", PLAIN[0]),
                  post("fxpers2", 20, "08 09:30", PLAIN[1], fwd=("fxpers1", 10)),
                  post("fxpers3", 30, "08 09:50", PLAIN[2], ["https://t.me/fxpers1/10"]),      # 글 안에 그 글의 주소
                  post("fxpers4", 40, "08 10:00", PLAIN[3], fwd=("fxpers1", 11)))
        self.assertTrue(same(out, ("fxpers1", 10), ("fxpers2", 20), ("fxpers3", 30)))
        self.assertFalse(same(out, ("fxpers1", 10), ("fxpers4", 40)))
        c = of(out, ("fxpers1", 10))
        self.assertEqual(c["keys"], [S.key_of("f", "fxpers1/10")])
        self.assertEqual([m["fwd"] for m in c["members"]], [False, True, False])

    def test_f_forwards_of_a_post_outside_the_list(self):
        out = run(post("fxpers1", 11, "08 09:00", PLAIN[0], fwd=("outsidechan", 5)),
                  post("fxpers2", 21, "08 09:30", PLAIN[1], fwd=("OutsideChan", 5)),
                  post("fxpers3", 31, "08 09:40", PLAIN[2], fwd=("outsidechan", 6)),
                  post("fxpers4", 41, "08 09:50", PLAIN[3], fwd=(None, None)))                  # 원글 주소가 없는 전달
        self.assertTrue(same(out, ("fxpers1", 11), ("fxpers2", 21)))
        self.assertEqual(len(out["clusters"]), 3)
        self.assertEqual(run()["clusters"], [])                                      # 글이 없는 판
        self.assertEqual(of(out, ("fxpers1", 11))["keys"], [S.key_of("f", "outsidechan/5")])
        self.assertEqual(kinds(of(out, ("fxpers4", 41))), {"g"})

    def test_t_same_card_title(self):
        out = run(post("fxpers1", 1, "08 09:00", PLAIN[0], ["https://sho.example/x1"], card={**CARD, "url": "https://sho.example/x1"}),
                  post("fxpers2", 2, "08 09:30", PLAIN[1], ["https://bit.example/yy"], card={**CARD, "url": "https://bit.example/yy"}),
                  post("fxpers3", 3, "08 09:40", PLAIN[2], ["https://bit.example/z1"], card={"title": "가을 축제", "site": "x",
                                                                                              "url": "https://bit.example/z1"}),
                  post("fxpers4", 4, "08 09:50", PLAIN[3], ["https://bit.example/z2"], card={"title": "가을 축제", "site": "x",
                                                                                              "url": "https://bit.example/z2"}))
        self.assertTrue(same(out, ("fxpers1", 1), ("fxpers2", 2)))
        self.assertEqual(kinds(of(out, ("fxpers1", 1))), {"t"})
        self.assertFalse(same(out, ("fxpers3", 3), ("fxpers4", 4)))                  # 제목이 card_title_min자보다 짧다

    def test_g_nearly_the_same_text(self):
        long = "오늘 장은 조용했다. 큰 소식 없이 거래가 한산했고 마감까지 별다른 변화가 없었다는 메모를 남긴다."
        out = run(post("fxpers1", 1, "08 09:00", long), post("fxpers2", 2, "08 09:30", long + " 그렇다고 한다"),
                  post("fxpers3", 3, "08 09:40", "거래가 한산했고 마감까지 별다른 변화가 없었다는 메모를 남긴다."),    # 긴 글에 통째로 들어 있다
                  post("fxpers4", 5, "08 10:10", PLAIN[0]))
        self.assertTrue(same(out, ("fxpers1", 1), ("fxpers2", 2), ("fxpers3", 3)))
        self.assertEqual(of(out, ("fxpers1", 1))["keys"], [S.key_of("g", "fxpers1/1")])
        self.assertFalse(same(out, ("fxpers1", 1), ("fxpers4", 5)))

    def test_g_needs_enough_text_and_two_channels(self):
        short = "오늘은 별일 없이 조용히 지나간 하루였다"                                # 지문을 만들기엔 짧다
        long = "오늘 장은 조용했다. 큰 소식 없이 거래가 한산했고 마감까지 별다른 변화가 없었다는 메모를 남긴다."
        out = run(post("fxpers1", 1, "08 09:00", short), post("fxpers2", 2, "08 09:30", short),
                  post("fxpers3", 3, "08 09:40", long), post("fxpers3", 4, "08 09:50", long + " 다시 적는다"))
        self.assertEqual(len(out["clusters"]), 4)
        self.assertEqual(DC.shingles(short), frozenset())
        self.assertGreaterEqual(len(DC.shingles(long)), R.TH["min_chars"])
        self.assertEqual(DC.shingles(long), DC.shingles(long.upper() + " https://x.example/a?b=1"))   # 주소·대소문자는 지문에 넣지 않는다

    def test_n_two_same_numbers_paired_with_the_same_term_within_hours(self):
        a = post("fxpers1", 1, "07 19:00", "추경 규모가 12.5조원으로 잡혔다는 말이 돈다. 적자 국채는 7.2조원이라고 한다.")
        b = post("fxpers2", 2, "08 12:00", "들은 얘기로는 전체 추경이 12.5조원 정도이고 그 가운데 적자 국채가 7.2조원.")   # 17시간 뒤
        late = post("fxpers3", 3, "08 14:00", "추경 12.5조원에 적자 국채 7.2조원이라는 숫자를 다시 봤다.")            # 19시간 뒤
        one = post("fxpers4", 4, "08 09:00", "추경이 12.5조원이라는데 나머지 숫자는 모르겠다.")
        bare = post("fxpers5", 5, "08 09:10", "어느 가게가 12.5조원을 벌고 7.2조원을 남겼다는 농담을 들었다.")        # 사전 낱말이 없다
        out = run(a, b, late, one, bare)
        self.assertTrue(same(out, ("fxpers1", 1), ("fxpers2", 2)))
        self.assertEqual(len(out["clusters"]), 4)
        self.assertEqual(of(out, ("fxpers1", 1))["keys"], [S.key_of("n", "12.5조원|7.2조원|추경")])

    def test_n_needs_the_numbers_paired_with_the_same_term(self):
        """흔한 숫자 둘과 낱말 하나가 우연히 겹친 글끼리는 묶지 않는다 — 두 숫자가 두 글에서 같은 A·B급 낱말과 짝지어져 있어야 한다."""
        a = post("fxpers1", 1, "08 08:00", "유가가 5% 올랐다는 지어낸 소식. 한편 어느 가게는 매출이 10% 늘었다고 한다. 금리 얘기도 조금.")
        b = post("fxpers2", 2, "08 09:00", "금리 메모. 지어낸 가게의 손님이 5% 줄었고 다른 가게는 10% 늘었다. 유가는 따로 적는다.")
        c = post("fxpers3", 3, "08 10:00", "FOMC 뒤에 5% 얘기와 10% 얘기를 지어냈다. 유가와 금리는 이름만 적는다.")
        out = run(a, b, c)
        self.assertEqual(len(out["clusters"]), 3)                                    # 같은 숫자 둘 + 같은 낱말 둘이지만 짝이 다르다
        self.assertFalse(any(kinds(c) & {"n"} for c in out["clusters"]))
        far = "유가 얘기로 시작하는 지어낸 긴 글. " + "가" * R.TH["num_term_chars"] + " 어느 가게는 5% 그리고 10%."
        out = run(a, post("fxpers4", 4, "08 11:00", far))
        self.assertEqual(len(out["clusters"]), 2)                                    # 낱말이 숫자에서 멀면 짝이 아니다

    def test_n_must_match_the_seed_post_not_a_later_one(self):
        a = post("fxpers1", 1, "08 08:00", "추경 규모가 12.5조원으로 잡혔다는 말이 돈다. 적자 국채는 7.2조원이라고 한다.")
        b = post("fxpers2", 2, "08 09:00", "추경 12.5조원, 그중 7.2조원이 국채. 지방에 3.4조원, 예비비로 1.1조원을 둔다고.")
        c = post("fxpers3", 3, "08 10:00", "추경 가운데 지방 몫 3.4조원과 예비비 1.1조원이 눈에 띈다.")
        out = run(a, b, c)
        self.assertTrue(same(out, ("fxpers1", 1), ("fxpers2", 2)))
        self.assertFalse(same(out, ("fxpers1", 1), ("fxpers3", 3)))                  # 씨앗 글과는 숫자가 겹치지 않는다

    def test_n_ignores_market_level_numbers(self):
        quote = "국고 3년 3.961%(+2.8bp), 10년 4.376%(+0.7bp)"
        level = "미 국채 10년 금리 5.31%, 2년 금리 4.87%"
        out = run(post("fxpers1", 1, "08 15:00", f"장 마감 메모를 남긴다. 거래는 한산했고 특별한 일은 없었다. {quote}."),
                  post("fxpers2", 2, "08 15:30", f"퇴근길에 적는 한 줄. 오늘 숫자는 이렇게 끝났다고 한다. {quote}."),
                  post("fxpers3", 3, "08 07:00", f"간밤 숫자를 옮겨 둔다. 자세한 얘기는 나중에 하기로 한다. {level}."),
                  post("fxpers4", 4, "08 07:30", f"아침에 본 화면을 그대로 적는다. 해석은 붙이지 않는다. {level}."))
        self.assertEqual(len(out["clusters"]), 4)
        fx = "환율은 1,385.5원, 유가는 82.4달러"                                     # 원·달러 수준(R.is_quote)
        out = run(post("fxpers1", 1, "08 15:00", f"점심 먹고 본 화면을 그대로 옮긴다. 별다른 뜻은 없다. {fx}."),
                  post("fxpers2", 2, "08 15:30", f"잊기 전에 적어 두는 숫자들. 나중에 다시 볼 생각이다. {fx}."))
        self.assertEqual(len(out["clusters"]), 2)
        pairs = DC.num_pairs(f"설명 없이 {level} 그리고 미 CPI 3.1% 상회")              # 금리 수준 숫자 둘은 빠진다
        self.assertEqual({v: p[:2] for v, p in pairs.items()}, {"3.1%": ("미 CPI", "상회")})

    def test_k_same_lead_term_for_bond_and_analyst_only(self):
        out = run(post("fxbond1", 1, "07 19:00", "금통위 의사록에서 눈에 띈 대목을 정리해 둔다."),
                  post("fxanal1", 2, "07 22:00", "어제 나온 금통위 의사록을 읽고 든 생각 몇 가지를 적는다."),
                  post("fxpers1", 3, "07 22:10", "금통위 의사록 얘기가 많아서 나도 한 줄 남겨 본다."),             # 개인 채널
                  post("fxbond2", 4, "08 11:30", "금통위 의사록의 소수의견 부분만 따로 떼어 다시 본다."),           # 13시간 반 뒤
                  post("fxbond3", 5, "07 22:20", "환율 얘기만 하는 글이라 주제 열쇠가 없다."),                    # C급 낱말뿐
                  post("fxbond4", 6, "07 22:30", "환율이 다시 화제라 짧게 메모한다. 별 내용은 없다."),
                  post("fxbond5", 7, "07 22:40", "오늘 읽은 것들\n이것저것 모아 둔다\n금통위 의사록도 있었다."))   # 첫머리 밖
        self.assertTrue(same(out, ("fxbond1", 1), ("fxanal1", 2)))
        self.assertEqual(len(out["clusters"]), 6)
        self.assertEqual(of(out, ("fxbond1", 1))["keys"], [S.key_of("k", "금통위 의사록|국내")])

    def test_k_follows_a_run_of_posts_with_gaps_under_twelve_hours(self):
        out = run(post("fxbond1", 1, "07 19:00", "금통위 의사록에서 눈에 띈 대목을 정리해 둔다."),
                  post("fxbond3", 2, "08 06:00", "금통위 의사록을 아침에 다시 펼쳐 보았다. 메모만 남긴다."),
                  post("fxbond2", 4, "08 11:30", "금통위 의사록의 소수의견 부분만 따로 떼어 다시 본다."))
        self.assertEqual(len(out["clusters"]), 1)

    def test_event_key_is_off_unless_events_are_given(self):
        ps = (post("fxbond1", 1, "07 22:00", "FOMC를 앞두고 미 PPI 숫자를 어떻게 볼지 적어 둔다."),         # 대표 낱말은 FOMC
              post("fxanal1", 2, "08 08:00", "미 PPI가 나왔다. 품목별로는 아직 살펴보지 못했다."),
              post("fxpers1", 3, "08 08:10", "미 PPI 얘기가 많아 나도 한 줄 적어 둔다."),                   # 개인 채널
              post("fxbond2", 4, "07 19:00", "미 PPI 발표를 기다리며 지난달 숫자를 복기한다."))             # 일정 전
        self.assertEqual(len(run(*ps)["clusters"]), 4)                              # 일정 없이는 대표 낱말·시간이 달라 따로다
        event = {"date": "2026-10-07", "time": "21:30", "term": "미 PPI", "tier": "B", "detail": [], "src": "calendar"}
        out = run(*ps, events=[event])
        self.assertTrue(same(out, ("fxbond1", 1), ("fxanal1", 2)))
        self.assertEqual(len(out["clusters"]), 3)
        self.assertIn(S.key_of("k", "e|미 PPI|2026-10-07"), of(out, ("fxbond1", 1))["keys"])


class AttachTest(unittest.TestCase):
    """속보형 · 주제 한정 · 전달 글은 가장 많이 맞는 묶음 하나에만 붙는다."""

    def setUp(self):
        self.a = (post("fxpers1", 1, "08 09:00", PLAIN[0], [URL_A]), post("fxpers2", 2, "08 09:10", PLAIN[1], [URL_A]))
        self.b = (post("fxpers3", 3, "08 09:20", PLAIN[2], [URL_B], card={**CARD, "url": URL_B}),
                  post("fxpers4", 4, "08 09:30", PLAIN[3], [URL_B], card={**CARD, "url": URL_B}))

    def test_a_wire_post_cannot_bridge_two_clusters(self):
        out = run(*self.a, *self.b, post("fxwire1", 9, "08 10:00", PLAIN[4], [URL_A, URL_B]))
        self.assertEqual(len(out["clusters"]), 2)
        self.assertFalse(same(out, ("fxpers1", 1), ("fxpers3", 3)))
        self.assertTrue(same(out, ("fxpers1", 1), ("fxwire1", 9)))                   # 맞은 수가 같으면 더 이른 묶음

    def test_it_goes_where_it_matches_most(self):
        out = run(*self.a, *self.b, post("fxwire1", 9, "08 10:00", PLAIN[4], [URL_A, URL_B], card={**CARD, "url": URL_B}))
        self.assertTrue(same(out, ("fxpers3", 3), ("fxwire1", 9)))                   # 주소 하나 대 주소 + 카드 제목
        self.assertFalse(same(out, ("fxpers1", 1), ("fxpers3", 3)))

    def test_forwards_and_topic_posts_do_not_bridge_either(self):
        out = run(*self.a, *self.b, post("fxpers5", 5, "08 10:00", PLAIN[4], [URL_B], fwd=("fxpers1", 1)),
                  post("fxtopp1", 6, "08 10:10", PLAIN[5], [URL_A, URL_B]))
        self.assertEqual(len(out["clusters"]), 2)
        self.assertTrue(same(out, ("fxpers1", 1), ("fxpers5", 5), ("fxtopp1", 6)))
        self.assertFalse(same(out, ("fxpers1", 1), ("fxpers3", 3)))

    def test_wire_posts_do_not_tie_separate_posts_or_each_other(self):
        out = run(post("fxpers1", 1, "08 09:00", PLAIN[0], [URL_A]), post("fxpers3", 3, "08 09:20", PLAIN[2], [URL_B]),
                  post("fxwire1", 9, "08 10:00", PLAIN[4], [URL_A, URL_B]),
                  post("fxwire1", 10, "08 10:05", PLAIN[5], [URL_C]), post("fxwire2", 11, "08 10:06", PLAIN[3], [URL_C]))
        self.assertFalse(same(out, ("fxpers1", 1), ("fxpers3", 3)))
        self.assertFalse(same(out, ("fxwire1", 10), ("fxwire2", 11)))                # 속보형끼리는 묶음을 만들지 못한다
        self.assertEqual(len(out["clusters"]), 4)

    def test_context_posts_always_stand_alone(self):
        out = run(*self.a, post("fxctx1", 7, "08 10:00", PLAIN[4], [URL_A]))
        self.assertEqual(len(out["clusters"]), 2)
        self.assertEqual(len(of(out, ("fxctx1", 7))["members"]), 1)

    def test_a_wire_post_joins_the_forwards_of_it(self):
        out = run(post("fxwire1", 9, "08 09:00", PLAIN[0]), post("fxpers1", 1, "08 09:10", PLAIN[0], fwd=("fxwire1", 9)),
                  post("fxpers2", 2, "08 09:20", PLAIN[0], fwd=("fxwire1", 9)))
        self.assertEqual(len(out["clusters"]), 1)
        self.assertEqual(out["clusters"][0]["seed"], {"ch": "fxpers1", "id": 1})     # 씨앗은 가장 이른 원천 글
        self.assertEqual(kinds(out["clusters"][0]), {"f"})


class ShapeTest(unittest.TestCase):
    def test_a_channel_counts_once_in_a_cluster(self):
        out = run(post("fxbond1", 1, "08 09:00", "미 CPI 3.1%로 나왔다. 근원 0.3%. 첫 메모.", [URL_A]),
                  post("fxbond1", 2, "08 09:20", "미 CPI 3.1%, 근원 0.3% 관련해 이어서 적는다.", [URL_A]),
                  post("fxanal1", 3, "08 09:40", "미 CPI를 다룬 기사 하나를 옮겨 둔다.", [URL_A]))
        c = out["clusters"][0]
        self.assertEqual(len(c["members"]), 3)
        self.assertEqual(c["terms"], [{"term": "미 CPI", "n_ch": 2}])
        self.assertEqual(c["nums"], [])                                              # 같은 채널이 두 번 쓴 숫자는 '두 곳'이 아니다

    def test_a_cluster_holds_at_most_forty_posts(self):
        card = lambda i: {**CARD, "url": f"https://sho.example/{i}"}                 # 같은 카드 제목, 글마다 다른 주소
        ps = [post(f"fxpers{i % 8 + 1}", 100 + i, f"08 {9 + i // 30:02d}:{i % 30:02d}", PLAIN[i % 6], [card(i)["url"]], card=card(i))
              for i in range(45)]
        out = run(*ps)
        sizes = sorted(len(c["members"]) for c in out["clusters"])
        self.assertEqual(sizes, [5, R.TH["cluster_max_posts"]])
        self.assertEqual(out["stats"]["kept"], 45)

    def test_numbers_need_two_channels_writing_them_themselves(self):
        cpi = "미 CPI 3.1%로 예상 상회, 근원은 0.3%. 미 국채 10년 금리 5.31%."
        out = run(post("fxbond1", 1, "08 09:00", cpi, [URL_A]), post("fxanal1", 2, "08 09:10", cpi, [URL_A], fwd=("fxbond1", 1)),
                  post("fxpers1", 3, "08 09:20", "CPI 3.1% 상회라니 놀랍다. 다른 숫자는 아직 못 봤다.", [URL_A]))
        self.assertEqual(out["clusters"][0]["nums"], [{"term": "미 CPI", "result": "상회", "v": "3.1%", "n_ch": 2}])

    def test_numbers_are_not_pinned_on_the_top_term(self):
        """낱말과 짝이 없는 숫자는 싣지 않는다 — 묶음의 대표 낱말에 대신 붙이면 없는 사실(유가 · 37%)이 만들어진다."""
        a = post("fxbond1", 1, "08 09:00", "유가 얘기로 시작하는 지어낸 글. " + "가" * 50 + " 어느 가게 매출이 37% 늘었다고 한다.", [URL_A])
        b = post("fxanal1", 2, "08 09:10", "어느 가게 매출이 37% 늘었다는 지어낸 글. 유가는 끝에 한 번 적는다.", [URL_A])
        c = run(a, b)["clusters"][0]
        self.assertEqual((len(c["members"]), c["terms"][0]["term"]), (2, "유가"))
        self.assertEqual(c["nums"], [])
        near = "유가가 37% 올랐다는 지어낸 글."
        c = run(post("fxbond1", 1, "08 09:00", near, [URL_A]), post("fxanal1", 2, "08 09:10", near + " 옮겨 적는다.", [URL_A]))["clusters"][0]
        self.assertEqual(c["nums"], [{"term": "유가", "result": None, "v": "37%", "n_ch": 2}])      # 두 곳이 그 낱말과 짝지은 숫자만

    def test_digits_of_other_scripts_never_reach_the_output(self):
        odd = chr(0x0663)
        text = f"국고채 입찰 응찰률 251.{odd}9% 라는 지어낸 숫자. 미 CPI 3.{odd}5% 그리고 1{odd}bp"
        out = run(post("fxbond4", 1, "08 09:00", text, [URL_A]), post("fxbond5", 2, "08 09:10", text + " 옮겨 적는다.", [URL_A]),
                  post("fxpers8", 3, "08 09:20", f"미 CPI 3.{odd}5% 라는 지어낸 한 줄"))
        self.assertEqual([c for c in S.dump(out) if unicodedata.category(c) == "Nd" and not c.isascii()], [])
        self.assertEqual([n for c in out["clusters"] for m in c["members"] for n in m["nums"]], [])

    def test_cell_needs_a_majority_of_channels(self):
        cpi, bok, plan = "미 CPI 얘기를 적는다. 길게 쓰지는 않는다.", "금통위 얘기를 적는다. 길게 쓰지는 않는다.", "국고채 발행계획을 본다. 메모만."
        split = run(post("fxpers1", 1, "08 09:00", cpi, [URL_A]), post("fxpers2", 2, "08 09:10", bok, [URL_A]))["clusters"][0]
        self.assertEqual(split["cell"], {"factor": "기타", "region": "글로벌"})       # 갈리면 분류 보류 — 계약상 null 대신 기타
        self.assertEqual([t["term"] for t in split["terms"]], ["금통위", "미 CPI"])
        home = run(post("fxpers1", 1, "08 09:00", plan, [URL_A]), post("fxpers2", 2, "08 09:10", bok, [URL_A]))["clusters"][0]
        self.assertEqual(home["cell"], {"factor": "기타", "region": "국내"})          # 칸은 갈려도 지역은 같다
        two = run(post("fxpers1", 1, "08 09:00", cpi, [URL_A]), post("fxpers2", 2, "08 09:10", bok, [URL_A]),
                  post("fxpers3", 3, "08 09:20", bok.replace("적는다", "남긴다"), [URL_A]), post("fxpers4", 4, "08 09:30", PLAIN[0], [URL_A]))
        self.assertEqual(two["clusters"][0]["cell"], {"factor": "통화정책", "region": "국내"})     # 낱말이 없는 채널은 세지 않는다
        none = run(post("fxpers1", 1, "08 09:00", PLAIN[0], [URL_A]), post("fxpers2", 2, "08 09:10", PLAIN[1], [URL_A]))["clusters"][0]
        self.assertEqual((none["cell"], none["terms"]), (None, []))

    def test_shape_builds_a_valid_cluster_from_closed_members(self):
        ms = [m for c in F.clusters_doc()["clusters"] for m in c["members"] if (m["ch"], m["id"]) in F.EXPECT_SAME["auction"]]
        c = S.validate_cluster(DC.shape(ms, [S.key_of("k", "국고채 입찰|국내")]))
        self.assertEqual((c["cell"], c["terms"][0]), ({"factor": "수급", "region": "국내"}, {"term": "국고채 입찰", "n_ch": 3}))
        self.assertEqual(c["results"][0], {"result": "응찰률", "n_ch": 2})
        leads = (["금리", "FOMC"], ["금리", "국고채 입찰"], ["국고채 입찰", "금리"])
        ms = [{**m, "lead": lead, "terms": lead, "row": None} for m, lead in zip(ms, leads)]
        c = S.validate_cluster(DC.shape(ms, [S.key_of("k", "국고채 입찰|국내")]))
        # 두 곳 이상이 쓴 낱말이 먼저(그 안에서 A·B급 → 많이 쓴 순) — 한 곳만 쓴 A급 낱말(FOMC)이 여럿이 쓴 낱말을 밀어내지 않는다
        self.assertEqual([t["term"] for t in c["terms"]], ["국고채 입찰", "금리", "FOMC"])
        self.assertEqual(c["cell"], {"factor": "수급", "region": "국내"})                        # 세 채널 가운데 둘


class FixtureTest(unittest.TestCase):
    """fixtures의 지어낸 글 40개 — 겨냥한 답(EXPECT_*)대로 묶이고, 원문은 한 글자도 남지 않는다."""

    @classmethod
    def setUpClass(cls):
        cls.posts, cls.status = F.posts_doc(), F.collect_status()
        cls.out = DC.cluster_posts(cls.posts, cls.status)

    def test_output_follows_the_contract(self):
        S.validate_clusters_doc(self.out)
        self.assertEqual(self.out["stats"], {"posts": 40, "kept": 35, "dropped": {c: 1 for c in R.DROP_CODES}})
        self.assertEqual({k: self.out[k] for k in ("schema", "edition", "window", "collected_at")},
                         {k: self.posts[k] for k in ("schema", "edition", "window", "collected_at")})

    def test_groups_match_the_answers(self):
        got = where(self.out)
        for name, ids in F.EXPECT_SAME.items():
            self.assertEqual(len({got[i] for i in ids}), 1, name)
            self.assertEqual(len(of(self.out, ids[0])["members"]), len(ids), name)   # 그 밖의 글이 섞이지 않았다
        for a, b in F.EXPECT_APART:
            self.assertNotEqual(got[a], got[b])
        self.assertFalse(set(F.EXPECT_DROP) & set(got))
        self.assertEqual((len(got), len(self.out["clusters"])), (35, 17))

    def test_each_cluster_carries_the_keys_that_tied_it(self):
        want = {"cpi": {"f", "u", "k", "n", "g"}, "auction": {"k", "n"}, "capex": {"u", "n"}, "rumor": {"f", "u", "g"}, "card": {"t", "k"}}
        for name, ks in want.items():
            self.assertEqual(kinds(of(self.out, F.EXPECT_SAME[name][0])), ks, name)
        cpi = of(self.out, ("fxbond1", 501))
        self.assertEqual((cpi["key"], cpi["seed"]), (S.key_of("f", "fxbond1/501"), {"ch": "fxbond1", "id": 501}))
        for kind, material in (("u", "news.example.com/cpi-sept"), ("k", "미 CPI|글로벌"), ("n", "0.3%|3.1%|미 CPI")):
            self.assertIn(S.key_of(kind, material), cpi["keys"])
        self.assertIn(S.key_of("u", "youtube:AbCdEfGhIjK"), of(self.out, ("fxanal4", 905))["keys"])
        alone = of(self.out, ("fxpers5", 611))
        self.assertEqual((alone["keys"], alone["terms"], alone["cell"]), ([S.key_of("g", "fxpers5/611")], [], None))

    def test_terms_cells_and_numbers(self):
        cpi, auction, capex = (of(self.out, F.EXPECT_SAME[n][0]) for n in ("cpi", "auction", "capex"))
        self.assertEqual(cpi["terms"][0], {"term": "미 CPI", "n_ch": 9})
        self.assertEqual(cpi["cell"], {"factor": "펀더멘털", "region": "글로벌"})
        self.assertEqual(cpi["nums"], [{"term": "미 CPI", "result": "상회", "v": "3.1%", "n_ch": 6},
                                       {"term": "미 CPI", "result": None, "v": "0.3%", "n_ch": 5}])      # 금리 수준 5.31%는 싣지 않는다
        self.assertEqual(auction["nums"], [{"term": "국고채 입찰", "result": "응찰률", "v": "247.4%", "n_ch": 2},
                                           {"term": "국고채 입찰", "result": None, "v": "2.8조원", "n_ch": 2}])
        self.assertEqual(auction["cell"], {"factor": "수급", "region": "국내"})
        self.assertEqual(capex["nums"], [{"term": "설비투자 금액", "result": None, "v": "85조원", "n_ch": 2},
                                         {"term": "AI 회사채 발행", "result": None, "v": "12조원", "n_ch": 2}])
        self.assertEqual(of(self.out, ("fxbond2", 213))["cell"], {"factor": "통화정책", "region": "국내"})
        self.assertEqual(of(self.out, ("fxpers5", 610))["cell"], {"factor": "기타", "region": "글로벌"})
        for key, want in F.EXPECT_TERMS.items():
            m = next(m for m in of(self.out, key)["members"] if (m["ch"], m["id"]) == key)
            self.assertEqual(m["terms"], want, key)

    def test_no_raw_text_survives(self):
        blob = S.dump(self.out)
        self.assertEqual(F.leaks(blob), [])
        self.assertEqual(S.closed_violations(self.out, S.handles_of(F.sources())), [])
        for p in self.posts["posts"]:
            for line in filter(None, (x.strip() for x in p["text"].split("."))):
                self.assertFalse(len(line) >= 8 and line in blob)

    def test_inputs_are_untouched_and_the_result_repeats(self):
        posts, status = copy.deepcopy(self.posts), copy.deepcopy(self.status)
        again = DC.cluster_posts(posts, status)
        self.assertEqual((posts, status), (self.posts, self.status))
        self.assertEqual(again, self.out)
        self.assertEqual(DC.cluster_posts({**posts, "posts": posts["posts"][::-1]}, status), self.out)     # 글 순서와 무관

    def test_a_post_from_an_unlisted_channel_is_refused(self):
        bad = {**self.posts, "posts": self.posts["posts"] + [post("fxoff1", 1, "08 17:00", PLAIN[0])]}
        with self.assertRaises(ValueError) as e:
            DC.cluster_posts(bad, self.status)
        self.assertEqual(F.leaks(str(e.exception)), [])

    def test_events_from_fixtures_keep_the_same_groups(self):
        events = DC.events_of(F.calendar(), F.korea())
        self.assertEqual([(e["date"], e["time"], e["term"], e["tier"], e["detail"], e["src"]) for e in events], [
            ("2026-10-07", "21:30", "미 CPI", "A", [], "calendar"), ("2026-10-08", None, "국고채 입찰", "A", ["10년", "2.8조원"], "korea"),
            ("2026-10-09", "21:30", "미 PPI", "B", [], "calendar"), ("2026-10-12", None, "국고채 입찰", "B", ["3년", "2.4조원"], "korea"),
            ("2026-10-15", None, "금통위", "A", [], "calendar")])
        out = S.validate_clusters_doc(DC.cluster_posts(self.posts, self.status, events))
        self.assertEqual([[(m["ch"], m["id"]) for m in c["members"]] for c in out["clusters"]],
                         [[(m["ch"], m["id"]) for m in c["members"]] for c in self.out["clusters"]])


class EventsTest(unittest.TestCase):
    def test_auction_rows_are_read_defensively(self):
        korea = {"calendar": {"rows": [{"date": "2026-10-12", "tenor": "3년"}, {"date": "2026-10-13", "tenor": "7년"},
                                       {"date": "어제", "tenor": "5년"}, "줄이 아님", {"date": "2026-10-14", "tenor": "30년"}]},
                 "offerings": [{"date": "2026-10-12", "tenor": "3년", "offered_100m": 30000}, {"date": "2026-10-14", "tenor": "30년",
                                                                                               "offered_100m": "많이"}]}
        got = DC.events_of(None, korea)
        self.assertEqual([(e["date"], e["tier"], e["detail"]) for e in got], [("2026-10-12", "B", ["3년", "3조원"]),
                                                                              ("2026-10-14", "A", ["30년"])])
        for broken in (None, {}, [], {"calendar": None}, {"calendar": {"rows": "x"}}, "korea"):
            self.assertEqual(DC.events_of(None, broken), [])
        self.assertEqual(DC.events_of({"events": []}, None), [])


class CliTest(unittest.TestCase):
    def write(self, tmp, posts=None, status=None):
        S.write_json(os.path.join(tmp, "posts.json"), F.posts_doc() if posts is None else posts)
        S.write_json(os.path.join(tmp, "collect_status.json"), F.collect_status() if status is None else status)

    def call(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = S.run_cli("digest_cluster", DC.main, argv)
        return code, out.getvalue(), err.getvalue()

    def test_writes_clusters_and_prints_counts_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp)
            code, out, err = self.call(["--work", tmp])
            self.assertEqual((code, err), (0, ""))
            self.assertEqual(out, "[digest_cluster] posts=40 kept=35 dropped=5 clusters=17 joined=5\n")
            with open(os.path.join(tmp, "clusters.json"), encoding="utf-8") as f:
                text = f.read()
            self.assertEqual(F.leaks(text), [])
            self.assertEqual(S.validate_clusters_doc(S.read_json(os.path.join(tmp, "clusters.json"))),
                             DC.cluster_posts(F.posts_doc(), F.collect_status()))
            self.assertEqual(sorted(os.listdir(tmp)), ["clusters.json", "collect_status.json", "posts.json"])

    def test_event_keys_are_switched_on_by_the_two_options(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as data:
            self.write(tmp)
            S.write_json(os.path.join(data, "calendar.json"), F.calendar())
            S.write_json(os.path.join(data, "korea.json"), F.korea())
            flags = ["--calendar", os.path.join(data, "calendar.json"), "--korea", os.path.join(data, "korea.json")]
            self.assertEqual(self.call(["--work", tmp, *flags]), (0, "[digest_cluster] posts=40 kept=35 dropped=5 clusters=17 joined=5\n", ""))
            keys = {k for c in S.read_json(os.path.join(tmp, "clusters.json"))["clusters"] for k in c["keys"]}
            self.assertLessEqual({S.key_of("k", "e|미 CPI|2026-10-07"), S.key_of("k", "e|국고채 입찰|2026-10-08")}, keys)
            self.call(["--work", tmp])                                               # 옵션 없이는 일정 열쇠가 없다
            keys = {k for c in S.read_json(os.path.join(tmp, "clusters.json"))["clusters"] for k in c["keys"]}
            self.assertNotIn(S.key_of("k", "e|미 CPI|2026-10-07"), keys)

    def test_failure_prints_only_the_kind_of_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.call(["--work", tmp]), (1, "", "[digest_cluster] 실패: FileNotFoundError\n"))
            broken = F.posts_doc()
            broken["posts"][0]["id"] = F.C3                                          # 형태가 틀린 글 — 값은 지시문 글자
            self.write(tmp, posts=broken)
            self.assertEqual(self.call(["--work", tmp]), (1, "", "[digest_cluster] 실패: ValueError\n"))
            other = {**F.collect_status(), "edition": "2026-10-07", "window": F.state()["edition"]["window"],
                     "collected_at": "2026-10-07T18:04:00+09:00"}
            self.write(tmp, status=other)                                            # 다른 판의 수집 상태
            self.assertEqual(self.call(["--work", tmp]), (1, "", "[digest_cluster] 실패: ValueError\n"))
            self.assertNotIn("clusters.json", os.listdir(tmp))

    def test_a_crash_in_the_middle_leaks_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp)
            real = DC.mention

            def boom(post, *rest):
                raise RuntimeError(post["text"])                                     # 원문이 든 예외
            DC.mention = boom
            try:
                code, out, err = self.call(["--work", tmp])
            finally:
                DC.mention = real
            self.assertEqual((code, out, err), (1, "", "[digest_cluster] 실패: RuntimeError\n"))

    def test_script_runs_from_the_repo_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp)
            done = subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, "digest_cluster.py"), "--work", tmp],
                                  capture_output=True, text=True, encoding="utf-8", cwd=S.REPO, timeout=120)
            self.assertEqual((done.returncode, done.stderr), (0, ""))
            self.assertEqual(F.leaks(done.stdout), [])
            self.assertTrue(done.stdout.startswith("[digest_cluster] posts=40 "))


if __name__ == "__main__":
    unittest.main()
