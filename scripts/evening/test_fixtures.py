#!/usr/bin/env python3
"""저녁판 테스트 자료(fixtures) 테스트 — 지어낸 글이 겨냥한 경우를 실제로 담고 있는지, 예시 산출물에 심은 글자가 없는지.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요.
"""
import contextlib
import io
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_rules as R
import digest_schema as S
import fixtures as F


class PostsTest(unittest.TestCase):
    def test_counts_and_window(self):
        self.assertEqual((len(F.posts()), len(F.old_posts()), len(F.all_posts())), (40, 2, 42))
        self.assertTrue(all(F.WINDOW["from"] < p["at"] <= F.WINDOW["to"] for p in F.posts()))
        self.assertEqual(S.collect_window(S.parse_iso(F.NOW), F.state())["from"], F.WINDOW["from"])
        self.assertEqual(len({(p["ch"], p["id"]) for p in F.all_posts()}), 42)
        self.assertTrue({p["ch"] for p in F.all_posts()} <= set(F.REQUESTED))

    def test_cases_the_posts_are_meant_to_cover(self):
        ps = F.posts()
        self.assertGreaterEqual(sum(p["fwd"] is not None for p in ps), 3)                 # 전달
        self.assertGreaterEqual(sum(p["card"] is not None for p in ps), 2)                # 링크 카드
        self.assertGreaterEqual(sum(bool(p["links"]) for p in ps), 12)                    # 주소
        self.assertEqual(sum(p["via"] == "search" for p in ps), 8)                        # 속보형은 검색으로 읽는다
        self.assertEqual({F.ROLE[p["ch"]] for p in ps}, {"source", "wire", "topic", "context"})
        self.assertEqual({F.GROUP[p["ch"]] for p in ps}, set(R.GROUPS))
        same_url = [p for p in ps if any("cpi-sept" in u for u in p["links"])]
        self.assertGreaterEqual(len({u for p in same_url for u in p["links"]}), 3)        # 같은 기사, 꼬리표만 다른 주소
        self.assertEqual(len({p["card"]["title"] for p in ps if p["card"]}), 1)
        self.assertEqual(len({p["card"]["url"] for p in ps if p["card"]}), 2)             # 같은 카드 제목, 다른 단축 주소

    def test_every_planted_string_is_in_the_raw_posts(self):
        raw = "\n".join(p["text"] + " ".join(p["links"]) + (p["card"] or {}).get("title", "") for p in F.posts())
        for i, canary in enumerate(F.CANARIES):
            self.assertIn(canary, raw, i)
        self.assertEqual(F.leaks(raw), list(range(len(F.CANARIES))))
        self.assertEqual(F.leaks("깨끗한 글 3.1% 미 CPI https://t.me/fxbond1/501"), [])
        self.assertEqual(F.leaks("앞 EVE​CANARY‍ZW 뒤"), [4])
        self.assertEqual(F.leaks('{"t":"eve\\u200bcanary\\u200dzw"}'), [4])               # JSON 이스케이프로 숨어도 찾는다
        self.assertEqual(F.leaks("https://CANARY.invalid/x 그리고 zqx7"), [0, 6])

    def test_drop_answers_match_the_rules(self):
        got = {(p["ch"], p["id"]): R.drop_code(p["text"], len(p["links"])) for p in F.posts()}
        self.assertEqual({k: v for k, v in got.items() if v}, F.EXPECT_DROP)
        self.assertEqual(set(F.EXPECT_DROP.values()), set(R.DROP_CODES))                  # 버리는 사유 다섯 가지가 다 있다

    def test_term_answers_match_the_rules(self):
        by = {(p["ch"], p["id"]): p for p in F.posts()}
        for key, want in F.EXPECT_TERMS.items():
            with self.subTest(key):
                self.assertEqual([h["term"] for h in R.match_terms(by[key]["text"])], want)

    def test_group_answers_are_consistent(self):
        ids = {(p["ch"], p["id"]) for p in F.posts()}
        named = [i for group in F.EXPECT_SAME.values() for i in group]
        self.assertEqual(len(named), len(set(named)))
        self.assertTrue(set(named) <= ids - set(F.EXPECT_DROP))
        for a, b in F.EXPECT_APART:
            self.assertTrue({a, b} <= ids)
            self.assertFalse(any(a in g and b in g for g in F.EXPECT_SAME.values()))
        cpi = F.EXPECT_SAME["cpi"]                                                         # 설계 4절의 예: 채권 3 · 애널 2 · 개인 3 · 속보형 1
        count = lambda group, role: len({ch for ch, _ in cpi if (F.GROUP[ch], F.ROLE[ch]) == (group, role)})
        got = (count("bond", "source"), count("analyst", "source"), count("personal", "source"), count("personal", "wire"))
        self.assertEqual(got, (3, 2, 3, 1))
        quotes = [{v for v in (h["v"] for h in R.find_nums(p["text"])) if R.is_quote(v)} for p in F.posts()
                  if (p["ch"], p["id"]) in F.EXPECT_APART[0]]
        self.assertEqual(len(quotes[0] & quotes[1]), 4)                                    # 시세 숫자 넷이 같아도 묶이면 안 되는 쌍


class PagesTest(unittest.TestCase):
    def test_pages_carry_the_preview_skeleton(self):
        pages = F.pages()
        self.assertEqual(sorted(pages), sorted(f"{ch}-1.html" for ch in F.REQUESTED))
        self.assertNotIn("fxoff1-1.html", pages)
        page = F.render_page("fxbond1")
        self.assertEqual(re.findall(r'data-post="fxbond1/(\d+)"', page), ["501", "502"])
        self.assertEqual(page.count("tgme_widget_message_text js-message_text"), 2)
        self.assertRegex(page, r'<time datetime="2026-10-07T12:41:00\+00:00" class="time">')          # 올린 시각은 UTC로 실린다
        self.assertIn('class="tgme_widget_message_forwarded_from_name" href="https://t.me/fxbond1/501"', F.render_page("fxanal1"))
        card = F.render_page("fxbond2")
        self.assertIn('class="tgme_widget_message_link_preview" href="https://sho.example/x1"', card)
        self.assertIn('<div class="link_preview_title" dir="auto">', card)
        self.assertNotIn("js-message_text", F.render_page("fxanal6").split('data-post="fxanal6/12"')[1])   # 본문 없는 글
        self.assertIn("&lt;b&gt;EVE-TAG-5T1&lt;/b&gt;", F.render_page("fxbond5"))                       # 글 속의 태그는 글자로 실린다
        self.assertEqual(len(F.render_page("fxbond1", only=[]).split("data-post")), 1)
        S.validate_manifest(F.manifest())

    def test_titles_match_the_source_list(self):
        src = {c["handle"]: c for c in F.sources()["channels"]}
        for ch in F.REQUESTED:
            self.assertEqual(S.title_sha(S.page_title(F.render_page(ch))), src[ch]["title_sha"], ch)


class SamplesTest(unittest.TestCase):
    def test_sample_clusters_follow_the_answers(self):
        cs = F.clusters_doc()["clusters"]
        where = {(m["ch"], m["id"]): i for i, c in enumerate(cs) for m in c["members"]}
        for name, ids in F.EXPECT_SAME.items():
            self.assertEqual(len({where[i] for i in ids}), 1, name)
        for a, b in F.EXPECT_APART:
            self.assertNotEqual(where[a], where[b])
        self.assertFalse(set(F.EXPECT_DROP) & set(where))
        self.assertEqual(len(where), 35)
        cpi = cs[where[("fxbond1", 501)]]
        self.assertEqual([(n["term"], n["result"], n["v"]) for n in cpi["nums"]],
                         [("미 CPI", "상회", "3.1%"), ("미 CPI", None, "0.3%")])       # 낱말에서 먼 금리 수준 5.31%는 짝이 없어 싣지 않는다
        self.assertEqual(cpi["key"][0], "f")
        single = cs[where[("fxpers5", 611)]]
        self.assertEqual((single["terms"], single["cell"], single["key"][0]), ([], None, "g"))

    def test_sample_edition(self):
        d = F.digest()
        self.assertEqual([x["id"] for x in d["must"]], ["20261008-fxbond1-501", "20261008-fxbond4-640", "20261008-fxbond2-213"])
        self.assertEqual(d["must"][0]["coverage"], {"bond": 3, "analyst": 2, "personal": 3, "wire": 1})
        self.assertEqual([g["cell"] for g in d["rest"]], ["펀더멘털/글로벌", "통화정책/국내", "수급/국내", "기타"])
        self.assertEqual(d["funnel"], {"posts": 40, "clusters": 10, "candidates": 3, "must": 3, "truncated": 0})
        wire = {c["ch"]: c for c in d["wire"]["channels"]}
        self.assertEqual(wire["fxwire1"], {"ch": "fxwire1", "read": 7, "joined": 1, "hit": 6})        # 여섯 줄이 맞았지만
        self.assertEqual(sum(r["ch"] == "fxwire1" for r in d["wire"]["rows"]), R.TH["rows_per_channel"])   # 다섯 줄만 싣는다
        self.assertEqual([(r["ch"], r["term"], r["v"]) for r in d["solo"]["rows"]],
                         [("fxpers6", "국고채 발행계획", "12.5조원"), ("fxpers7", "미 CPI", "3.1%")])
        self.assertEqual([x["ch"] for x in d["context"]], ["fxctx1"])
        self.assertEqual(d["sources"], {"channels_ok": 24, "channels_total": 24})

    def test_sample_scores_add_up_to_the_table(self):
        for c in F.scored_doc()["clusters"]:
            s = c["score"]
            self.assertEqual(s["total"], s["C"] + s["X"] + s["K"] + s["E"] + s["M"] + s["Y"] - s["P"])
            self.assertEqual(c["pick"] == "must", c["gate"]["pass"])
        self.assertEqual(sum(c["pick"] == "must" for c in F.scored_doc()["clusters"]), 3)

    def test_state_after_keeps_yesterday_as_base(self):
        st = F.state_after()
        self.assertEqual((st["edition"]["date"], st["base"]["date"]), ("2026-10-08", "2026-10-07"))
        self.assertEqual(st["base"], F.state()["edition"])
        self.assertEqual(st["edition"]["channels"]["fxbond1"]["last_post"], 502)
        self.assertEqual(S.collect_window(S.parse_iso("2026-10-08T21:00:00+09:00"), st)["from"], F.WINDOW["from"])    # 다시 돌아도 같은 창

    def test_korea_stub_has_the_fields_the_evening_reads(self):
        k = F.korea()
        cards = {c["key"]: c for c in k["cards"]}
        self.assertEqual(set(cards), {"kr3", "kr10", "us10"})
        want = {"kr10": ("2026-10-08", 4.376, 0.7), "kr3": ("2026-10-08", 3.961, 2.8), "us10": ("2026-10-07", 5.27, -4.0)}
        for key, (day, value, chg) in want.items():
            pts, m = cards[key]["points"], cards[key]["metrics"]
            self.assertGreaterEqual(len(pts), R.TH["m_obs"] + 1)
            self.assertEqual((m["date"], m["value"], m["changes"]["1"]["value"]), (day, value, chg))
            self.assertEqual(pts[-1], [day, value])
            self.assertAlmostEqual((pts[-1][1] - pts[-2][1]) * 100, chg, places=6)
            self.assertEqual([p[0] for p in pts], sorted(p[0] for p in pts))
        self.assertTrue(all({"date", "tenor"} <= set(r) for r in k["calendar"]["rows"]))
        self.assertTrue(all({"date", "tenor", "offered_100m"} <= set(r) for r in k["offerings"]))

    def test_samples_written_to_disk_are_valid_and_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(F.main(["--out", tmp]), 0)
            self.assertEqual(out.getvalue(), "[fixtures] files=13 posts=40\n")
            public = os.path.join(tmp, "public")
            names = sorted(os.listdir(public))
            self.assertEqual(names, sorted(["digest", "digest.json", "digest_index.json", "digest_state.json", "digest_status.json",
                                            "sources.json", "calendar.json", "digest_overrides.json"]))
            src = S.read_json(os.path.join(public, "sources.json"))
            handles = S.handles_of(src)
            labels = [c["label"] for c in src["channels"]] + list(R.GROUPS.values()) + list(R.ROLES.values())
            for name in [n for n in names if n != "digest"] + [f"digest/{F.EDITION}.json"]:
                with open(os.path.join(public, name), encoding="utf-8") as f:
                    text = f.read()
                doc = S.validator_for(name)(S.read_json(os.path.join(public, name)))
                self.assertEqual(F.leaks(text), [], name)
                self.assertEqual(S.closed_violations(doc, handles if name != "sources.json" else S.handles_of(src, list(R.ROLES)),
                                                     labels if name == "sources.json" else ()), [], name)
            for name in ("posts.json", "collect_status.json", "clusters.json", "scored.json", "pages/manifest.json"):
                S.validator_for(name)(S.read_json(os.path.join(tmp, name)))
            self.assertEqual(len(os.listdir(os.path.join(tmp, "pages"))), 25)             # 24쪽 + manifest
            with open(os.path.join(tmp, "clusters.json"), encoding="utf-8") as f:
                self.assertEqual(F.leaks(f.read()), [])                                    # 묶음부터는 원문이 없다
            with open(os.path.join(tmp, "posts.json"), encoding="utf-8") as f:
                self.assertEqual(len(F.leaks(f.read())), len(F.CANARIES))


if __name__ == "__main__":
    unittest.main()
