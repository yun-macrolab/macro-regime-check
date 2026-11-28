#!/usr/bin/env python3
"""저녁판 항목의 안내 테스트 — 관련 화면(screens) · 다가오는 일정(soon) · 직전 판과의 차이(new · prev) (2026-11-28).

  규칙   낱말 → 화면 표(R.SCREENS)는 사전 낱말만, 한 낱말은 한 화면에만, 화면 id는 index.html의 것만
  조립   제목의 낱말로 화면 · 일정을 붙인다. 일정은 판 날짜부터 7일 안이고 수집 창이 끝난 뒤의 것. '새로 나옴'은 직전 판을 알 때만
  계약   허용 목록 밖 화면 id · 항목에 없는 낱말의 일정 · 직전 판의 칸과 함께 온 '새로 나옴'은 떨어진다. 상태 기록과 어긋나면 검사에 걸린다
  화면   정해 둔 문구에 날짜 · 낱말 · 수만 끼워 그린다. 링크는 같은 페이지의 해시뿐이고, 이상한 값은 그 칸만 뺀다

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요 — 글은 fixtures.py의 지어낸 것뿐이다. 화면의 모양과 가로 넘침(폭 390px)은 여기서 볼 수 없다.
"""
import copy
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import digest_build as B
import digest_check as C
import digest_rules as R
import digest_schema as S
import fixtures as F
import test_digest_build as TB
import test_digest_check as TC
from test_evening_site import NODE, PAGE, Screen, blob, draw, draws, flat, rules_block, site

fx, edit = TC.fx, TC.edit
EVENTS = [  # 지어낸 일정 — 판 날짜 2026-10-08, 수집 창의 끝 18:07
    ("2026-10-07", "21:30", "미 CPI"),          # 판 날짜 앞
    ("2026-10-08", "09:00", "국고채 입찰"),      # 판 날짜지만 창이 끝나기 전
    ("2026-10-08", None, "미 CPI"),             # 시각을 모르는 오늘 일정 — 이미 나왔을 수 있다
    ("2026-10-08", "21:30", "미 국채 금리"),      # 오늘 밤
    ("2026-10-15", None, "미 CPI"),             # 7일째
    ("2026-10-14", "21:30", "미 CPI"),          # 같은 낱말의 더 이른 것
    ("2026-10-16", None, "국고채 입찰"),         # 8일째
    ("2026-10-12", None, "FOMC"),              # 항목에 없는 낱말
]


def calendar():
    return {"schema": 1, "updated": "2026-10-01", "events": [
        {"date": d, "term": t, "tier": "A", **({"time": at} if at else {})} for d, at, t in EVENTS]}


def assembled(**change):
    given = {"scored": fx("scored_doc"), "collect": fx("collect_status"), "state": fx("state"), "calendar": calendar(), **change}
    return B.assemble(given["scored"], given["collect"], given["state"], TB.index_before(), F.overrides(), fx("sources"),
                      given["calendar"])[1]


def items(d):
    return d["must"] + [x for g in d["rest"] for x in g["items"]]


def item_of(d, seed):
    return next(x for x in items(d) if x["id"].endswith(seed))


class TableTest(unittest.TestCase):
    def test_screen_table_uses_dictionary_words_once_and_page_screens(self):
        words = [t for _, _, terms in R.SCREENS for t in terms]
        self.assertEqual([t for t in words if t not in R.TERMS], [])
        self.assertEqual(len(words), len(set(words)))
        known = re.search(r"const known = \[(.*?)\];", PAGE).group(1)
        groups = re.findall(r'\{ id: "([a-z-]+)", title: "([^"]+)"', PAGE)
        screens = set(re.findall(r'"([a-z-]+)"', known)) | {g for g, _ in groups}
        self.assertEqual([s for s in R.SCREEN_IDS if s not in screens], [])
        self.assertFalse({"all", "evening", "notes"} & set(R.SCREEN_IDS))
        menu = re.findall(r'data-view="([a-z-]+)"', PAGE)                       # 순서는 메뉴 순서(한국 아래 화면은 '한국 시장' 자리)
        order = [menu.index("korea" if s.startswith("korea") else s) for s in R.SCREEN_IDS]
        self.assertEqual(order, sorted(order))
        self.assertNotIn("금리", words)                                          # 넓은 낱말은 어느 화면에도 잇지 않는다

    def test_screens_follow_the_menu_and_the_examples(self):
        self.assertEqual(R.screens_of(["국고채 입찰", "미 CPI", "FOMC", "연준"]), ["rates", "inflation", "korea-flows"])
        for term, screen in (("통안채", "korea-flows"), ("FOMC", "rates"), ("연준", "rates"), ("미 CPI", "inflation"),
                             ("미 PCE", "inflation"), ("단기자금", "liquidity"), ("AI", "ai")):
            self.assertEqual(R.screens_of([term]), [screen], term)
        self.assertEqual(R.screens_of(["관세", "금리", "국채 입찰", "없는 낱말"]), [])     # 나라를 안 밝힌 입찰은 한국 화면에 잇지 않는다

    def test_screen_names_and_phrases_are_the_same_on_both_sides(self):
        rules = rules_block()
        self.assertEqual(rules["screens"], {s: name for s, name, _ in R.SCREENS})
        self.assertEqual(rules["view_phrases"], R.VIEW_PHRASES)
        self.assertEqual(rules["soon_max"], R.TH["soon_max"])

    def test_readme_table_lists_every_screen_word(self):
        with open(os.path.join(REPO, "README.md"), encoding="utf-8") as f:
            text = f.read()
        for screen, name, terms in R.SCREENS:
            self.assertIn(f"| `#{screen}` | {name} | {' · '.join(terms)} |", text)


class BuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = assembled()
        cls.d = cls.files["digest.json"]

    def test_the_result_passes_the_contract(self):
        S.validate_digest(self.d, fx("sources"))
        self.assertEqual(C.check_edition(self.d, fx("sources")), [])
        S.validate_state(self.files["digest_state.json"])
        self.assertLess(len(S.dump(self.d).encode("utf-8")), C.EDITION_BYTES)

    def test_screens_come_from_the_title_words(self):
        for x in items(self.d):
            self.assertEqual(x.get("screens", []), R.screens_of(x["terms"]), x["id"])
        self.assertEqual(self.d["must"][0]["screens"], ["rates", "inflation"])       # 미 CPI · 미 국채 금리
        self.assertEqual(self.d["must"][1]["screens"], ["korea-flows"])              # 국고채 입찰

    def test_soon_takes_the_next_seven_days_after_the_window_one_per_word(self):
        self.assertEqual(self.d["must"][0]["soon"], [{"date": "2026-10-08", "term": "미 국채 금리"}, {"date": "2026-10-14", "term": "미 CPI"}])
        self.assertNotIn("soon", self.d["must"][1])                                  # 창 앞 · 8일째
        for none in (None, {"schema": 1, "updated": "2026-10-01", "events": []}):
            self.assertFalse([x for x in items(assembled(calendar=none)["digest.json"]) if "soon" in x])

    def test_seventh_day_is_in_and_eighth_is_out(self):
        only = lambda day: {"schema": 1, "updated": "2026-10-01", "events": [{"date": day, "term": "미 CPI", "tier": "A"}]}
        for day, want in (("2026-10-09", True), ("2026-10-15", True), ("2026-10-16", False), ("2026-10-08", False)):
            self.assertEqual("soon" in assembled(calendar=only(day))["digest.json"]["must"][0], want, day)

    def test_new_and_prev_say_which_lead_words_were_there_before(self):
        cpi, auction = self.d["must"][0], self.d["must"][1]
        self.assertEqual(("prev" in cpi, "new" in cpi), (True, False))
        self.assertEqual(("prev" in auction, auction.get("new")), (False, True))
        state = fx("state")                                                          # 직전 판의 제목에 있었지만 대표는 아니었다 → 아무 말도 안 한다
        state["edition"]["seen"] = sorted(state["edition"]["seen"] + [S.topic_key(auction["terms"][0])])
        middle = assembled(state=state)["digest.json"]["must"][1]
        self.assertEqual(("prev" in middle, "new" in middle), (False, False))

    def test_nothing_is_called_new_without_a_whole_previous_edition(self):
        short, bare, gone, old = fx("state"), fx("state"), fx("state"), fx("state")
        short["edition"]["read_to"] = short["edition"]["window"]["from"]             # 직전 판이 수집 부족
        bare["edition"].pop("seen")                                                  # 이 칸이 없던 때의 기록
        gone["edition"].update(seen=[], topics=[])                                   # 내린 판
        old["edition"]["read_to"] = old["edition"]["window"]["to"]
        for state in (short, bare, gone, B.EMPTY_STATE):
            self.assertFalse([x for x in items(assembled(state=state)["digest.json"]) if "new" in x])
        self.assertTrue([x for x in items(assembled(state=old)["digest.json"]) if "new" in x])

    def test_wide_words_are_never_marked(self):
        for x in items(self.d):
            if x.get("new") or x.get("prev"):
                self.assertTrue(R.comparable(x["terms"][0]), x["id"])

    def test_state_remembers_the_title_words_as_hashes_and_rerun_keeps_the_base(self):
        ed = self.files["digest_state.json"]["edition"]
        self.assertEqual(ed["seen"], sorted({S.topic_key(t) for x in items(self.d) for t in x["terms"]}))
        self.assertTrue({t["key"] for t in ed["topics"]} <= set(ed["seen"]))
        again = assembled(state=self.files["digest_state.json"], collect={**fx("collect_status"), "window_kind": "rerun"})
        marks = lambda d: [(x["id"], x.get("new"), x.get("prev")) for x in items(d)]
        self.assertEqual(marks(again["digest.json"]), marks(self.d))

    def test_takedown_clears_the_remembered_words(self):
        files = B.blank(S.parse_iso(F.NOW), fx("state_after"), S.handles_of(fx("sources")))
        for snap in (files["digest_state.json"]["edition"], files["digest_state.json"]["base"]):
            self.assertEqual((snap["topics"], snap["seen"]), ([], []))
        S.validate_state(files["digest_state.json"])

    def test_the_most_items_fit_in_the_remembered_list(self):
        th = R.TH
        self.assertGreaterEqual(th["seen_max"], th["must_max"] * th["terms_max"] + th["rest_max"] * th["rest_terms_max"])
        self.assertGreaterEqual(th["topics_max"], th["must_max"] + th["rest_max"])    # 대표 낱말 목록도 잘리지 않는다

    def test_command_line_reads_the_calendar_from_the_data_folder(self):
        case = TB.BuildCase("run")
        case.setUp()
        try:
            S.write_json(os.path.join(case.data, "calendar.json"), calendar())
            self.assertEqual(case.build()[0], 0)
            self.assertEqual(case.doc("digest.json"), self.d)
            case.passes_check()
        finally:
            case.doCleanups()
            case.tearDown()


class ContractTest(unittest.TestCase):
    def test_refusals(self):
        good = assembled()["digest.json"]
        cases = {
            "목록에 없는 화면": (["must", 0, "screens"], ["evening"], "screens"),
            "주소 꼴의 화면": (["must", 0, "screens"], ["https://example.org/"], "screens"),
            "화면 순서": (["must", 0, "screens"], ["inflation", "rates"], "screens"),
            "같은 화면 두 번": (["must", 0, "screens"], ["rates", "rates"], "screens"),
            "빈 화면 목록": (["must", 0, "screens"], [], "screens"),
            "항목에 없는 낱말의 일정": (["must", 0, "soon"], [{"date": "2026-10-12", "term": "FOMC"}], "soon"),
            "8일 뒤": (["must", 0, "soon"], [{"date": "2026-10-16", "term": "미 CPI"}], "soon"),
            "판 날짜 앞": (["must", 0, "soon"], [{"date": "2026-10-07", "term": "미 CPI"}], "soon"),
            "같은 낱말 두 번": (["must", 0, "soon"], [{"date": "2026-10-09", "term": "미 CPI"}, {"date": "2026-10-10", "term": "미 CPI"}], "soon"),
            "문장이 든 일정": (["must", 0, "soon"], [{"date": "2026-10-09", "term": F.C1}], "soon"),
            "일정의 덧붙인 칸": (["must", 0, "soon"], [{"date": "2026-10-09", "term": "미 CPI", "text": F.C1}], "soon"),
            "직전 판의 칸과 함께": (["must", 0, "new"], True, "new"),
            "거짓 표시": (["must", 1, "new"], False, "new"),
        }
        for name, (path, value, where) in cases.items():
            with self.subTest(name), self.assertRaises(ValueError) as e:
                S.validate_digest(edit(good, path, value), fx("sources"))
            self.assertIn(where, str(e.exception), name)
            self.assertEqual(F.leaks(str(e.exception)), [])

    def test_public_strings_stay_closed(self):
        d = assembled()["digest.json"]
        self.assertEqual(S.closed_violations(d, S.handles_of(fx("sources"))), [])
        self.assertEqual(F.leaks(S.dump(d)), [])
        for text in R.VIEW_PHRASES.values():                                   # 화면의 틀은 자료에 실리지 않는다
            self.assertNotIn(text, S.dump(d))

    def test_new_mark_must_agree_with_the_state_file(self):
        d, state = fx("digest"), fx("state_after")
        self.assertEqual(C._new_found(d, state["base"]), [])
        known = copy.deepcopy(state["base"])
        known["seen"] = sorted(known["seen"] + [S.topic_key(d["must"][1]["terms"][0])])
        for base in (known, {**state["base"], "seen": []}, None,
                     {**state["base"], "read_to": state["base"]["window"]["from"]}):
            self.assertTrue(C._new_found(d, base))
            self.assertTrue(all(f["code"] == "cross" for f in C._new_found(d, base)))

    def test_seen_must_be_sorted_hashes(self):
        state = fx("state_after")
        for bad in (state["edition"]["seen"][::-1], state["edition"]["seen"][:1] * 2, ["미 CPI"]):
            with self.assertRaises(ValueError):
                S.validate_state(edit(state, ["edition", "seen"], bad))


@unittest.skipUnless(NODE, "node가 없다")
class ScreenTest(Screen):
    def test_card_and_rows_show_links_schedule_and_the_difference(self):
        frame = draw(site(digest=assembled()["digest.json"]))
        self.shows(frame, "관련 화면 금리·커브 물가", "다가오는 일정: 10-08 미 국채 금리", "다가오는 일정: 10-14 미 CPI",
                   "직전 판에도 있음(채널 수 3→8)", "새로 나옴", "관련 화면 한국 수급·입찰", "관련 화면 AI 투자")
        inside = {(a["href"], a["text"]) for a in frame["links"] if a["href"].startswith("#") and not a["href"].startswith("#evening")}
        self.assertTrue(inside)
        self.assertEqual(inside - {("#" + s, name) for s, name, _ in R.SCREENS}, set())
        for a in frame["links"]:
            if a["href"].startswith("#"):
                self.assertIsNone(a["target"])

    def test_counts_of_new_marks_follow_the_data(self):
        d = fx("digest")
        new = sum(bool(x.get("new")) for x in items(d))
        self.assertGreater(new, 1)
        frame = draw(site(digest=d))
        self.assertEqual(flat(frame["text"]).count(flat("새로 나옴")), new + 1)         # 항목마다 하나 + 맨 아래 안내 문단의 한 번

    def test_odd_values_drop_only_their_own_piece(self):
        d = assembled()["digest.json"]
        d["must"][0]["screens"] = ["javascript:alert(1)", "https://example.org", F.C1, "evening", "__proto__", "inflation", "inflation"]
        d["must"][0]["soon"] = [{"date": "2026-02-30", "term": "미 CPI"}, {"date": "2026-10-09", "term": "FOMC"},
                                {"date": F.C1, "term": "미 CPI"}, None, "문장", {"date": "2026-10-09", "term": F.C3}]
        d["must"][1]["new"] = "참"
        d["must"][2].update(screens="rates", soon={"date": "2026-10-09"}, new=F.C4)
        wrong, clean = draws(site(digest=d), site(digest=assembled()["digest.json"]))
        self.assertEqual(F.leaks(blob(wrong)), [])
        self.lacks(wrong, "다가오는 일정: 02-30", "다가오는 일정: 10-09")
        self.assertEqual({a["href"] for a in wrong["links"] if not a["href"].startswith(("https://", "#evening"))}
                         - {"#" + s for s in R.SCREEN_IDS}, set())
        self.assertEqual(sum(a["href"] == "#inflation" for a in wrong["links"]),
                         sum(a["href"] == "#inflation" for a in clean["links"]))     # 겹친 id는 한 번만
        self.assertLess(flat(wrong["text"]).count(flat("새로 나옴")), flat(clean["text"]).count(flat("새로 나옴")))
        self.shows(wrong, "꼭 3건")
        self.lacks(wrong, "undefined", "NaN", "[object", "그리지 못했습니다")

    def test_withdrawn_screen_has_no_item_links(self):
        frame = draw(site(overrides=F.overrides(withdraw=True)))
        self.assertEqual([a for a in frame["links"] if a["href"].lstrip("#") in R.SCREEN_IDS], [])


if __name__ == "__main__":
    unittest.main()
