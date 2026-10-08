#!/usr/bin/env python3
"""저녁판 화면 테스트(넷째 묶음) — AI 요약 층(data/digest_picks.json)의 문장을 화면이 언제, 어떤 꼴로 붙이는가 (2026-10-09).

  붙이는 조건  digest_schema.py 머리말 'AI 요약 층'의 규칙 그대로(파이썬 판은 digest_picks.attach): 최신 판 화면이고 · 파일의 판 날짜가 보는
              판과 같고 · 항목의 key가 같고 · 읽힌 글(src)이 모두 그 항목의 걸린 링크일 때만. 화면은 조금 더 좁게 본다 — 읽힌 글이 채권 ·
              애널 원천 채널의 전달 아닌 글이어야 하고, 출처 목록을 못 읽었으면 붙이지 않는다. 어긋나면 그 문장만 빠지고 나머지는 그대로다
  2차 가드     문장은 닫힌 값이 아니라 AI가 쓴 글자다 — 화면도 꼴을 한 번 더 본다(길이 · 정해 둔 글자 · 주소 꼴). 글자는 텍스트 노드로만 넣는다
  보이는 꼴    'AI 요약' 표시 · 틀릴 수 있다는 말 · 읽힌 글 수 · 판 머리의 배지 · '출처와 수집 방식'의 안내
  그대로인 것  요약 파일이 없거나 깨졌을 때 · 지난 판 · 내린 판은 요약이 없는 화면과 글자 하나 다르지 않다

도구(가짜 문서 · 지어낸 판)는 test_evening_site.py의 것을 쓴다. 문장은 fixtures.PICK_FACTS(지어낸 것)다. 모양과 가로 넘침(폭 375px)은
여기서 볼 수 없다 — preview.py --ai로 띄워 눈으로 본다.
실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요. node가 없으면 그려 보는 테스트는 건너뛴다.
"""
import contextlib
import datetime
import io
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_picks as K
import digest_rules as R
import digest_schema as S
import fixtures as F
import preview as PV
from test_evening_site import (C4, C5, C7, CSS, JS, NODE, THU_EVENING, Screen, blob, calls, draw, draws, flat, fx, named, play, posts,
                               rules_block, site)
from test_evening_site_more import old_shape, order

PICKS = "data/" + K.FILE
F1, F2 = F.PICK_FACTS
MADE = "빅테크 두 곳이 같은 날 회사채 12조원을 발행했다."                     # 지어낸 문장(나머지 줄에 붙여 볼 것)
WARN = "틀릴 수 있습니다 — 원문에서 확인하세요"
ON, OFF = "규칙 선별 + AI 요약", "규칙 선별 · 문장 없음"
BAD_FACTS = ["가" * 139 + "다.", "짧은 글이다.", "마침표 없이 끝난 지어낸 문장", "자세한 내용은 https://example.org/a 에 있다.",
             "자세한 내용은 www.example.org 에 있다.", "자세한 내용은 example.org 에 있다.", "문의는 @someone 에게 하면 된다.",
             "줄이\n바뀐 지어낸 문장이다.", "탭이\t들어간 지어낸 문장이다.", "보이지 않는​ 글자가 든 문장이다.", "<b>굵게</b> 쓴 지어낸 문장이다.",
             '따옴표가 "든" 지어낸 문장이다.', "#해시태그 가 든 지어낸 문장이다.", " 앞에 공백이 있는 지어낸 문장이다.",
             "뒤에 공백이 있는 지어낸 문장이다. ", f"{C4} 이 든 지어낸 문장이다.", f"{C5} 이 든 지어낸 문장이다.", f"{C7} 이 든 지어낸 문장이다.",
             "", None, 7, [F1], {"fact": F1}]


def drawn(frame):
    """화면에 그려진 요약 문장의 수."""
    return sum(a == "class=eve-ai-text" for a in frame["attrs"])


def changed(fn, n=0, **swap):
    """지어낸 요약 층의 n번째 문장을 fn으로 고친 판 한 벌."""
    p = fx("picks")
    fn(p["items"][n])
    return site(picks=p, **swap)


def layer(x, fact, src):
    """판의 항목 x에 문장 하나를 얹은 요약 층."""
    asked = [{"key": x["key"], "id": x["id"], "src": src}]
    return K.picks_doc(F.EDITION, F.PICKS_AT, "claude-fx-1", asked, {x["key"]: fact})


# ---------- 규칙 쪽과 같아야 하는 값 ----------


class AiRulesTest(unittest.TestCase):
    def test_numbers_and_patterns_match_the_rules(self):
        rules = rules_block()
        for key in ("fact_chars", "fact_min_chars", "llm_items_max", "llm_posts_max"):
            self.assertEqual(rules[key], R.TH[key], key)
        self.assertIn(K._CHARS.pattern[1:-2] + "{", JS)                         # 문장에 올 수 있는 글자 — digest_picks와 같은 모둠
        self.assertIn("/" + K._LINKISH.pattern + "/i", JS)                      # 주소 꼴
        self.assertIn(f'"{K.FILE}"', JS)
        self.assertIn(f'p.mode !== "{K.MODE}"', JS)

    def test_the_sentence_reads_above_the_chips_and_inside_the_view(self):
        css = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
        size = lambda sel: float(re.search(re.escape(sel) + r" \{[^}]*?font(?:-size)?:[^;}]*?([\d.]+)px", css).group(1))
        self.assertGreaterEqual(size(".eve-ai-text"), 14)                       # 본문 글꼴로 읽기 좋게
        self.assertGreater(size(".eve-ai-text"), size(".eve-lede"))
        self.assertGreater(size(".eve-ai-text"), size(".eve-why li"))           # 낱말 칩보다 위계가 위
        self.assertGreater(size(".eve-ai-row .eve-ai-text"), size(".eve-sub"))  # 나머지 줄에서도 낱말 줄보다는 크게
        self.assertRegex(css, r"\.eve-ai-text \{[^}]*font:[^;}]*var\(--f-text\)")
        self.assertRegex(css, r"\.eve-ai \{[^}]*overflow-wrap: anywhere")       # 폭 375px에서 넘치지 않게
        self.assertRegex(css, r"forced-colors: active\) \{[^@]*\.eve-ai-tag")   # 배경색으로만 가른 표시는 고대비에서 테두리로


@unittest.skipUnless(NODE, "node가 없다")
class AiGuardTest(unittest.TestCase):
    def test_fact_guard_takes_what_the_rules_take_and_refuses_the_rest(self):
        good = [F1, F2, MADE, "가" * 138 + "다.", "연준(Fed)은 9월 회의에서 금리를 0.25%p 내렸다.", "국고 3년·10년 금리가 2~3bp 올랐다.",
                "A&B 비율은 1/2 수준이다: 3+1이다."]
        for s in good:
            self.assertTrue(K.ok_shape(s), s)                                   # 규칙이 받는 문장을 화면이 떨어뜨리면 안 된다
        for s in BAD_FACTS:
            self.assertFalse(K.ok_shape(s), s)
        self.assertEqual(calls("fact", *good, *BAD_FACTS), good + [None] * len(BAD_FACTS))


# ---------- 그려 보기: 붙이는 조건 ----------


@unittest.skipUnless(NODE, "node가 없다")
class AiAttachTest(Screen):
    @classmethod
    def setUpClass(cls):
        cls.base, cls.frame = draws(site(), site(picks=fx("picks")))

    def test_the_layer_is_read_with_the_other_files(self):
        self.assertEqual(self.frame["requested"].count(PICKS), 1)
        self.assertEqual(self.base["requested"].count(PICKS), 1)                # 없어도 한 번 물어 본다(404면 조용히 넘어간다)

    def test_sentences_stand_under_their_items(self):
        self.shows(self.frame, F1, F2, ON, "꼭 3건")
        self.lacks(self.frame, OFF)
        self.assertEqual(drawn(self.frame), 2)                                  # 셋째 항목은 문장이 없다 — 지금 그대로
        at = order(self.frame, "미 CPI · 미 국채 금리", "채권 3곳 · 애널 2곳 · 개인 3곳이 함께 다뤘습니다.", "속보형 1곳 겹침", F1, "원문 링크",
                   "채권 2곳 · 애널 1곳이 함께 다뤘습니다.", "묶인 글 3건 · 10-08 11:40 ~ 13:05", F2)
        self.assertEqual(at, sorted(at))                                        # 한 문장 소개 바로 아래
        self.assertEqual(posts(self.frame), posts(self.base))                   # 문장이 링크를 바꾸지 않는다

    def test_each_sentence_is_marked_as_written_by_ai_and_says_what_was_read(self):
        text = flat(self.frame["text"])
        for fact in (F1, F2):
            head, tail = text.split(flat(fact))
            self.assertTrue(head.endswith(flat("AI 요약" + WARN)), fact)          # 표시와 틀릴 수 있다는 말이 문장보다 먼저
            self.assertTrue(tail.startswith(flat("채권·애널 채널 글 3건을 읽고 씀")), fact)
        self.assertEqual(text.count(flat(WARN)), 2)
        one = draw(changed(lambda x: x.update(src=x["src"][:1])))
        self.shows(one, F1, "채권·애널 채널 글 1건을 읽고 씀")                       # 읽힌 글이 항목 링크의 일부여도 된다
        self.assertEqual(drawn(one), 2)

    def test_the_screen_agrees_with_the_python_rule(self):
        def moved(p, **kw):
            p["items"][0].update(kw)
            return p
        layers = [fx("picks"), PV.shift(fx("picks"), -1), moved(fx("picks"), key="f:000000000000"),
                  moved(fx("picks"), src=[["fxbond1", 999]]), moved(fx("picks"), src=[["fxbond2", 212]])]
        for p, frame in zip(layers, draws(*[site(picks=p) for p in layers])):
            want = K.attach(fx("digest"), p, fx("sources"))
            self.assertEqual(sorted(f for f in (F1, F2) if flat(f) in flat(frame["text"])), sorted(want.values()))
            self.assertEqual(drawn(frame), len(want))
        self.assertEqual([len(K.attach(fx("digest"), p, fx("sources"))) for p in layers], [2, 0, 1, 1, 2])

    def test_a_mismatch_takes_away_only_that_sentence(self):
        cases = {"key가 다른 항목": dict(key="f:000000000000"), "key 꼴이 아님": dict(key="순위-1"), "key가 글자가 아님": dict(key=7),
                 "글 번호가 다름": dict(src=[["fxbond1", 999]]), "다른 항목의 글": dict(src=[["fxbond4", 640]]),
                 "개인 채널의 글": dict(src=[["fxpers2", 912]]), "한 글만 어긋남": dict(src=[["fxbond1", 501], ["fxbond2", 999]]),
                 "읽힌 글 없음": dict(src=[]), "읽힌 글이 너무 많음": dict(src=[["fxbond1", 501], ["fxbond2", 212], ["fxbond3", 88], ["fxanal2", 77]]),
                 "같은 글 두 번": dict(src=[["fxbond1", 501], ["fxbond1", 501]]), "글 번호가 글자": dict(src=[["fxbond1", "501"]]),
                 "글 번호가 0": dict(src=[["fxbond1", 0]]), "글 번호가 소수": dict(src=[["fxbond1", 501.5]]), "칸이 하나": dict(src=[["fxbond1"]]),
                 "칸이 셋": dict(src=[["fxbond1", 501, 1]]), "목록이 아님": dict(src="fxbond1/501"), "빈 칸": dict(src=[None]),
                 "채널 꼴이 아님": dict(src=[["fx bond1", 501]]), "칸이 빠짐": None}
        files = [changed(lambda x, kw=kw: x.update(kw) if kw else x.pop("src")) for kw in cases.values()]
        for name, frame in zip(cases, draws(*files)):
            self.shows(frame, F2, ON)
            self.lacks(frame, F1)
            self.assertEqual(drawn(frame), 1, name)
            self.assertEqual(posts(frame), posts(self.base), name)
            for bad in ("undefined", "NaN", "[object", "그리지 못했습니다"):
                self.assertNotIn(bad, frame["text"], name)

    def test_the_read_posts_must_be_direct_posts_of_bond_and_analyst_source_channels(self):
        fwd, role, group, gone = fx("digest"), fx("sources"), fx("sources"), fx("sources")
        fwd["must"][0]["links"][1]["fwd"] = True                                # 읽힌 글이 전달 글로 바뀌었다
        for src, kw in ((role, dict(role="wire")), (group, dict(group="personal"))):
            next(c for c in src["channels"] if c["handle"] == "fxbond2").update(kw)
        gone["channels"] = [c for c in gone["channels"] if c["handle"] != "fxbond2"]
        frames = draws(site(picks=fx("picks"), digest=fwd), *[site(picks=fx("picks"), sources=s) for s in (role, group, gone)])
        for frame in frames:
            self.shows(frame, F2)
            self.lacks(frame, F1)
            self.assertEqual(drawn(frame), 1)

    def test_the_id_does_not_tie_a_sentence_to_an_item(self):
        """같은 판을 다시 계산하면 id(씨앗 글로 만든 값)는 달라질 수 있다 — key와 읽힌 글로만 잇는다."""
        d = fx("digest")
        d["must"][0]["id"] = "20261008-fxbond2-212"
        frame, other = draws(site(picks=fx("picks"), digest=d), changed(lambda x: x.update(id="20261008-fxpers9-1")))
        for f in (frame, other):
            self.shows(f, F1, F2)
            self.assertEqual(drawn(f), 2)

    def test_a_key_given_twice_and_a_layer_that_is_too_long_are_not_trusted(self):
        twice, many = fx("picks"), fx("picks")
        twice["items"].append({**twice["items"][0], "fact": MADE})              # 같은 항목에 문장이 둘 — 어느 것이 맞는지 알 수 없다
        many["items"] += [{**many["items"][0], "key": f"k:{i:012x}"} for i in range(R.TH["llm_items_max"] - 1)]
        dup, long = draws(site(picks=twice), site(picks=many))
        self.lacks(dup, F1, MADE)                                               # 둘 다 뺀다(나중 것이 앞의 것을 덮지 않는다)
        self.shows(dup, F2, ON)
        self.assertEqual(drawn(dup), 1)
        self.lacks(long, F1, F2)                                                # 물을 수 있는 수(6)보다 많이 든 파일은 통째로
        self.shows(long, OFF, "꼭 3건")
        self.assertEqual(drawn(long), 0)

    def test_polluted_sentences_are_not_drawn(self):
        frames = draws(*[changed(lambda x, bad=bad: x.update(fact=bad)) for bad in BAD_FACTS])
        for bad, frame in zip(BAD_FACTS, frames):
            self.assertEqual(drawn(frame), 1, bad)
            self.shows(frame, F2, ON)
            if isinstance(bad, str) and bad:
                self.lacks(frame, bad)
            self.assertEqual(F.leaks(blob(frame)), [], bad)
            self.assertNotRegex(blob(frame), r"example\.org|someone|<b>|canary")
            for junk in ("undefined", "NaN", "[object"):
                self.assertNotIn(junk, frame["text"], bad)
        edge = draw(changed(lambda x: x.update(fact="가" * 138 + "다.")))          # 딱 140자는 그린다
        self.assertEqual(drawn(edge), 2)

    def test_a_missing_or_broken_layer_leaves_the_screen_as_it_was(self):
        p = fx("picks")
        junk = [[1, 2], "깨짐", 7, {"schema": 1}, {**p, "schema": 2}, {**p, "mode": "rules"}, {**p, "items": "x"}, {**p, "items": None},
                {**p, "items": [None, 3, "x", [], {}]}, {**p, "date": None}, {**p, "date": "2026-10-07"}, {**p, "date": "2026-10-09"}]
        for bad, frame in zip(junk, draws(*[site(picks=bad) for bad in junk])):
            self.assertEqual(frame["text"], self.base["text"], bad if not isinstance(bad, dict) else sorted(bad))
            self.assertEqual((frame["attrs"], frame["links"]), (self.base["attrs"], self.base["links"]))
        self.shows(self.base, OFF)
        self.assertEqual(drawn(self.base), 0)

    def test_past_editions_carry_no_sentences(self):
        old = PV.shift(fx("digest"), -1)
        files = site(picks=fx("picks"), past={"2026-10-07": old})
        stale = site(picks=PV.shift(fx("picks"), -1), past={"2026-10-07": old})   # 요약 층이 지난 판의 것으로 남아 있을 때
        latest, past, named_latest, behind, same_day = draws(files, (files, THU_EVENING, "2026-10-07"), (files, THU_EVENING, "2026-10-08"),
                                                             stale, (stale, THU_EVENING, "2026-10-07"))
        self.assertEqual([drawn(f) for f in (latest, past, named_latest, behind, same_day)], [2, 0, 2, 0, 0])
        self.shows(past, "지난 판(10-07(수))을 보고 있습니다", OFF, "꼭 3건")
        self.lacks(past, F1, F2)
        self.lacks(same_day, F1, F2)                                            # 날짜가 맞아도 지난 판 화면에는 붙이지 않는다
        self.shows(behind, OFF)

    def test_hidden_items_hidden_channels_and_withdrawn_editions(self):
        d = fx("digest")
        blank = S.blank_digest(S.parse_iso(F.NOW))
        item, chan, off, gone, broken, nolist = draws(
            site(picks=fx("picks"), overrides=F.overrides(hide_ids=[d["must"][0]["id"]])),
            site(picks=fx("picks"), overrides=F.overrides(hide_channels=["fxbond2"])),      # 읽힌 글의 채널을 숨겼다 — 그 글로 쓴 문장도 내린다
            site(picks=fx("picks"), overrides=F.overrides(withdraw=True)), site(picks=fx("picks"), digest=blank),
            site(picks=fx("picks"), overrides=None), site(picks=fx("picks"), sources=None))
        for frame in (item, chan):
            self.shows(frame, F2, ON)
            self.lacks(frame, F1)
            self.assertEqual(drawn(frame), 1)
        for frame in (off, gone, broken, nolist):
            self.lacks(frame, F1, F2)
            self.assertEqual(drawn(frame), 0)
        self.shows(nolist, "꼭 3건", OFF, "출처 목록(sources.json)을 읽지 못해 원문 링크를 걸지 않았습니다")   # 견줄 목록이 없으면 붙이지 않는다

    def test_rest_rows_carry_the_sentence_small_under_the_words(self):
        d = fx("digest")
        both, alone = d["rest"][0]["items"][0], d["rest"][1]["items"][0]         # 애널 + 개인이 쓴 줄 · 채권 한 곳만 쓴 글
        row, lone = draws(site(picks=layer(both, MADE, [["fxanal4", 905]])), site(picks=layer(alone, MADE, [["fxbond1", 502]])))
        self.shows(row, MADE, "채권·애널 채널 글 1건을 읽고 씀", ON, "꼭 3건")
        at = order(row, "함께 나온 낱말: 빅테크 실적 2곳", "AI 요약" + WARN, MADE, "가상 애널 anal4 10-08 07:55")
        self.assertEqual(at, sorted(at))                                        # 낱말 줄 아래, 원문 링크 위
        self.assertEqual((drawn(row), row["attrs"].count("class=eve-ai eve-ai-row")), (1, 1))
        self.lacks(lone, MADE)                                                  # 채권 한 곳만 쓴 글은 요약할 항목이 아니다(고르는 규칙이 묻지 않는다)
        self.shows(lone, OFF)

    def test_an_edition_in_the_first_shape_takes_sentences_too_and_an_item_without_a_key_takes_none(self):
        old, bare = old_shape(fx("digest")), fx("digest")
        del bare["must"][0]["key"]
        first, nokey, neither = draws(site(picks=fx("picks"), digest=old), site(picks=fx("picks"), digest=bare),
                                      changed(lambda x: x.pop("key"), digest=bare))     # 항목에도 문장에도 key가 없다 — '없음'끼리 잇지 않는다
        self.shows(first, F1, F2, ON)
        for frame in (nokey, neither):
            self.shows(frame, F2, "꼭 3건", "미 CPI · 미 국채 금리")
            self.lacks(frame, F1)
            self.assertEqual(drawn(frame), 1)

    def test_an_open_screen_takes_new_sentences_and_lets_go_of_removed_ones(self):
        first, _, soon, later, _, gone = play(
            site(), {"now": THU_EVENING, "view": "evening"}, {"put": {PICKS: fx("picks")}},
            {"now": "2026-10-08T19:05:00+09:00", "tick": True}, {"now": "2026-10-08T19:11:00+09:00", "tick": True},
            {"put": {k: None for k in site(picks=fx("picks"))}}, {"now": "2026-10-08T19:22:00+09:00", "tick": True})
        self.assertEqual([drawn(f) for f in (first, soon, later, gone)], [0, 0, 2, 0])      # 10분이 지나야 다시 읽는다
        self.shows(later, F1, ON)
        self.shows(gone, OFF, "저녁판 2026-10-08(목)", "꼭 3건")                  # 판은 가진 것을 두고, 요약은 못 받으면 비운다
        self.lacks(gone, F1, F2)
        self.assertEqual(posts(gone), posts(first))


# ---------- 그려 보기: 안내 ----------


@unittest.skipUnless(NODE, "node가 없다")
class AiNoticeTest(Screen):
    @classmethod
    def setUpClass(cls):
        cls.base, cls.frame = draws(site(), site(picks=fx("picks")))

    def test_source_note_says_what_the_ai_reads_and_writes(self):
        for frame in (self.base, self.frame):                                   # 문장이 없는 날에도 방식은 적어 둔다
            self.shows(frame, "고르는 일은 LLM 없이 규칙이 합니다", "AI(Claude)가 쓴 것입니다", "채권·애널 그룹 원천 채널의 글을 항목마다 3건까지 읽고",
                       "자기 말로 한두 문장", "개인·속보형 채널의 글과 전달 글은 읽히지 않습니다", "원문과 길게 겹치지 않는지", "숫자와 단위가 원문에 있는지",
                       "정해 둔 권유·전망 표현이 없는지 같은 자동 검사를 통과한 문장만 싣습니다", "짧은 어구는 원문과 겹칠 수 있습니다",
                       "뜻이 틀릴 수 있습니다", "같은 판을 다시 계산할 수 있어", "AI 요약에 쓸 글이 있는 채널은 운영자 PC가 한 번 더 읽습니다",
                       "문장이 없는 날과 항목이 있습니다", "텔레그램 약관은 플랫폼에서 얻은 자료를 AI에 쓰는 것을 제한합니다",
                       "채널 운영자가 요청하면 그 채널을 내립니다", "채널 글에서 가져오는 것은")
            self.lacks(frame, "싣는 것은 미리 정한", "옮겨 싣지는 않습니다", "평일 저녁에 한 번 읽습니다")     # 단정해서 틀리던 문장들                               # '낱말·숫자·링크뿐'이라고 하던 문장은 고쳤다

    def test_card_note_names_the_ai_only_when_a_sentence_is_on_the_cards(self):
        line = "'AI 요약'은 AI(Claude)가 채권·애널 채널의 글을 읽고 자기 말로 쓴 문장입니다"
        self.shows(self.frame, line, "채널 글의 문장은 싣지 않습니다 — 낱말은 미리 정한 사전에서 찾은 것이고")
        self.lacks(self.base, line)
        at = order(self.frame, F2, "채널 글의 문장은 싣지 않습니다 — 낱말은", line, "다가오는 일정")
        self.assertEqual(at, sorted(at))

    def test_sentences_go_in_as_text_and_nothing_planted_comes_along(self):
        self.assertEqual(F.leaks(blob(self.frame)), [])
        for attr in self.frame["attrs"] + [str(a["href"]) for a in self.frame["links"]]:
            self.assertNotIn(F1[:12], attr)                                     # 속성이나 주소에는 문장이 들어가지 않는다
            self.assertNotIn(F2[:12], attr)
        for bad in ("undefined", "NaN", "[object", "null"):
            self.assertNotIn(bad, self.frame["text"])


# ---------- 미리 보기 ----------


class AiPreviewTest(Screen):
    DAY = datetime.date(2026, 10, 12)

    def test_made_up_sentences_follow_the_edition_when_asked_for(self):
        plain, docs = PV.build("ok", self.DAY), PV.build("ok", self.DAY, ai=True)
        self.assertNotIn(K.FILE, plain)                                         # 달라고 할 때만 둔다
        self.assertEqual({k: v for k, v in docs.items() if k != K.FILE}, plain)
        self.assertEqual(docs[K.FILE]["date"], docs["digest.json"]["date"])
        self.assertEqual(len(K.attach(docs["digest.json"], docs[K.FILE], docs["sources.json"])), 2)
        self.assertNotIn(K.FILE, PV.build("empty", self.DAY, ai=True))          # 판이 없으면 얹을 곳도 없다
        self.assertIn(K.FILE, PV.EVENING)                                       # data/에 올라간 진짜 요약 층을 지어낸 판에 섞지 않는다

    @unittest.skipUnless(NODE, "node가 없다")
    def test_the_preview_with_sentences_draws(self):
        frame = draws((named(PV.build("ok", self.DAY, ai=True)), "2026-10-12T19:00:00+09:00"))[0]
        self.shows(frame, F1, F2, ON, "저녁판 2026-10-12(월)")
        self.assertEqual(drawn(frame), 2)
        self.assertEqual(F.leaks(blob(frame)), [])

    def test_a_layer_from_a_file_is_added_only_when_it_is_valid(self):
        d = fx("digest")
        made = {"digest.json": d, f"digest/{F.EDITION}.json": d, "digest_index.json": fx("index"),
                "digest_state.json": fx("state_after"), "digest_status.json": fx("status")}
        human = {"sources.json": fx("sources"), "calendar.json": fx("calendar"), "digest_overrides.json": F.overrides()}
        with tempfile.TemporaryDirectory() as tmp:
            pub, data, out = (os.path.join(tmp, n) for n in ("public", "data", "preview"))
            for folder, files in ((pub, made), (data, human)):
                for name, doc in files.items():
                    S.write_json(os.path.join(folder, *name.split("/")), doc)
            good, bad = os.path.join(tmp, "picks.json"), os.path.join(tmp, "bad.json")
            S.write_json(good, fx("picks"))
            S.write_json(bad, {**fx("picks"), "mode": "rules"})
            with contextlib.redirect_stdout(io.StringIO()) as said:
                self.assertEqual(PV.main(["--from", pub, "--data", data, "--picks", good, "--out", out]), 0)
            self.assertIn("files=9", said.getvalue())
            self.assertEqual(S.read_json(os.path.join(out, "data", K.FILE)), fx("picks"))
            with self.assertRaises(ValueError):
                PV.real(pub, data, bad)                                         # 형식에 안 맞는 요약 층은 미리 보지도 않는다
            PV.assemble(out, PV.real(pub, data))
            self.assertFalse(os.path.exists(os.path.join(out, "data", K.FILE)))  # 다시 조립하면 앞서 둔 요약 층을 치운다


if __name__ == "__main__":
    unittest.main()
