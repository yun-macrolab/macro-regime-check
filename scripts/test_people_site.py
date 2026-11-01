"""연준 인물 페이지(site/people.html · people.css · people.js · people-data.js)의 정적 검사 — 브라우저 없이 글자만 본다.
표준 라이브러리만, 네트워크 불필요.

  껍데기   문서 머리(문자 집합 · 화면 폭 · 제목) · 바깥에서는 글꼴만 · 스크립트는 자료 → 그리기 순 · 점검 페이지와 서로 잇는다
  표시     '참고 — 예측 아님'과 '초안'이 머리에 보이고, 비공개 쪽 낱말(비공개 · 분석실)은 없다 · 사람 사진 · 기관 로고(이미지)가 없다
  자료     people-data.js가 window.PEOPLE_DATA = {JSON}; 꼴이고, 사람 · 회의 · 지구 · 지도의 칸과 범위가 맞는다 ·
           출처 주소는 https · 이메일 주소가 없다 · 회의 반대표와 지구 총재가 명단(또는 명단 밖 위원)을 가리킨다
  저장     움직임 · 단축키는 점검 페이지와 같은 저장 이름(motion · keys)만 쓴다

실행:  python -X utf8 scripts/test_people_site.py   (아침 묶음 `python -m unittest discover -s scripts`가 함께 돈다)
자료를 고칠 때: 사람 · 출처를 더하면 이 검사가 꼴을 본다. 비공개 저장소의 인물 프로필과 이름 · 자리 · 투표권 · 진영 · 반대표가
같은지는 그쪽 테스트(형제 폴더가 있을 때)가 본다.
"""
import json
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(REPO, "site")
FILES = ("people.html", "people.css", "people.js", "people-data.js")

SEATS = {"board", "ny", "bank"}
CAMPS = {"매파", "중도", "비둘기", "스윙", "미상"}
KINDS = {"school", "fed", "academia", "company", "government", "other"}
CERTS = {"1차", "2차", "사전 지식"}
SIDES = {"인상", "인하", "동결", "문구"}              # 문구 = 성명 문구에 반대(비공개 프로필의 반대표 종류와 같다)
DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def read(name):
    with open(os.path.join(SITE, name), encoding="utf-8") as f:
        return f.read()


def load_data(text):
    """people-data.js → dict. 꼴이 다르면 ValueError(머리 주석 + window.PEOPLE_DATA = {JSON}; 한 문장만)."""
    m = re.fullmatch(r"\s*(?:/\*.*?\*/\s*)?window\.PEOPLE_DATA = (\{.*\});\s*", text, re.S)
    if not m:
        raise ValueError("people-data.js는 머리 주석과 window.PEOPLE_DATA = {...}; 한 문장이어야 한다")
    return json.loads(m.group(1))


class ShellTest(unittest.TestCase):
    def setUp(self):
        self.page = read("people.html")

    def test_document_head(self):
        self.assertTrue(self.page.startswith("<!doctype html>\n<html lang=\"ko\">"))
        for tag in ('<meta charset="utf-8">', '<meta name="viewport" content="width=device-width, initial-scale=1',
                    '<meta name="color-scheme" content="dark">', '<link rel="stylesheet" href="people.css">'):
            self.assertIn(tag, self.page)
        self.assertRegex(self.page, r"<title>매크로 관측실 · 연준 인물</title>")
        self.assertNotIn("<style", self.page)                      # 모양은 people.css에만

    def test_only_fonts_come_from_outside(self):
        hosts = set(re.findall(r'<(?:link|script)\b[^>]*?(?:href|src)="https?://([^/"]+)', self.page))
        self.assertEqual(hosts, {"fonts.googleapis.com", "fonts.gstatic.com"})

    def test_data_loads_before_the_drawing_and_both_exist(self):
        srcs = re.findall(r'<script src="([\w.-]+\.js)"></script>', self.page)
        self.assertEqual(srcs, ["people-data.js", "people.js"])
        for s in srcs:
            self.assertTrue(os.path.isfile(os.path.join(SITE, s)), s)
        self.assertLess(self.page.index('<script src="people.js">'), self.page.index("</body>"))

    def test_pages_link_each_other(self):
        self.assertIn('<a class="brand" href="./"', self.page)
        self.assertIn('<a href="./">← 매크로 관측실 점검 페이지</a>', self.page)
        nav = read("index.html")
        nav = nav[nav.index('<nav id="category-nav"'):]
        self.assertIn('<a href="people.html">연준 인물<span>', nav[:nav.index("</nav>")])

    def test_reference_and_draft_marks_are_visible(self):
        head = self.page[self.page.index('<header'):self.page.index('</header>')]
        self.assertIn("참고 — 예측 아님", head)
        self.assertIn("초안", head)
        self.assertIn("참고 — 예측 아님`", read("people.js"))    # 큰 제목 줄

    def test_no_private_wording(self):
        for name in FILES:
            text = read(name)
            for word in ("비공개", "분석실", "my_path", "fed_people", "알림 줄"):
                self.assertNotIn(word, text, f"{name}: {word}")

    def test_no_pictures_of_people_or_logos(self):
        for name in FILES:
            text = read(name)
            for pat in (r"<img\b", r"<picture\b", r"<video\b", r'createElement\("img"\)', r"new Image",
                        r"\.(?:png|jpe?g|gif|webp|avif)\b", r"data:image/"):
                self.assertIsNone(re.search(pat, text, re.I), f"{name}: {pat}")

    def test_no_email_addresses(self):
        for name in FILES:
            self.assertEqual(EMAIL.findall(read(name)), [], name)

    def test_storage_names_match_the_dashboard(self):
        names = set(re.findall(r'localStorage\.(?:get|set)Item\("([^"]+)"', read("people.js")))
        self.assertEqual(names, {"motion", "keys"})
        dash = set(re.findall(r'localStorage\.(?:get|set)Item\("([^"]+)"', read("index.html")))
        self.assertLessEqual(names, dash)                          # 한쪽에서 끄면 다른 쪽도 꺼진 채로 연다

    def test_readme_tells_the_page_and_counts(self):
        with open(os.path.join(REPO, "README.md"), encoding="utf-8") as f:
            readme = f.read()
        self.assertIn("## 참고: 연준 인물", readme)
        m = re.search(r"\*\*아침 쪽 Python 테스트 (\d+)개 \+ node 테스트 (\d+)개\*\*\((.*?)\)와 \*\*저녁판", readme)
        mine = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()
        self.assertRegex(m.group(3).split(" / node: ")[0], rf"(^|· )연준 인물 화면 {mine}( ·|$)")

    def test_missing_data_stops_with_a_message(self):
        js = read("people.js")
        start = js[:js.index("function el(")]
        self.assertIn("const DATA = window.PEOPLE_DATA || {};", start)
        self.assertIn('throw new Error("people-data.js 없음")', start)


class DataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data(read("people-data.js"))
        cls.people = cls.data["people"]
        cls.keys = {p["key"] for p in cls.people}

    def test_file_shape_is_one_assignment(self):
        self.assertRaises(ValueError, load_data, "window.PEOPLE_DATA = {};\nalert(1);")
        self.assertRaises(ValueError, load_data, "var x = 1;")
        self.assertEqual(load_data("/* 주석 */\nwindow.PEOPLE_DATA = {\"a\": 1};\n"), {"a": 1})

    def test_header_fields(self):
        self.assertRegex(self.data["asof"], DATE)
        self.assertTrue(any("초안" in n for n in self.data["notes"]))
        self.assertTrue(any("참고 — 예측 아님" in n for n in self.data["notes"]))
        scale = self.data["stance_scale"]
        self.assertEqual((scale["min"], scale["max"], scale["step"]), (-2, 2, 0.5))

    def test_people_have_unique_plain_keys(self):
        self.assertGreaterEqual(len(self.people), 12)
        self.assertEqual(len(self.keys), len(self.people))
        for p in self.people:
            self.assertRegex(p["key"], r"^[a-z]+$")

    def test_person_fields(self):
        for p in self.people:
            k = p["key"]
            for f in ("name_ko", "name_en", "role_short", "bg_type", "bg_line", "watch", "conf"):
                self.assertTrue(isinstance(p[f], str) and p[f].strip(), f"{k}.{f}")
            self.assertIn(p["seat"], SEATS, k)
            self.assertIn(p["camp"], CAMPS, k)
            self.assertIsInstance(p["voter_2026"], bool, k)
            self.assertIsInstance(p["voter_2027"], bool, k)
            if p["seat"] == "bank":
                self.assertIn(p["district"], range(1, 13), k)
            for f in ("stance_now", "stance_start_2026"):
                v = p[f]
                if v is not None:
                    self.assertTrue(-2 <= v <= 2 and abs(v * 2 - round(v * 2)) < 1e-9, f"{k}.{f}={v}")
            for side in ("usual", "hawk_surprise", "dove_surprise"):
                items = p["baseline"][side]
                self.assertTrue(items and all(isinstance(t, str) and t.strip() for t in items), f"{k}.baseline.{side}")
            for d in p["dissents_2026"]:
                self.assertRegex(d["date"], DATE)
                self.assertIn(d["side"], SIDES, k)

    def test_sources_are_https_links(self):
        for p in self.people:
            self.assertTrue(p["sources"], p["key"])
            for s in p["sources"]:
                self.assertRegex(s["url"], r"^https://[a-z0-9.-]+\.[a-z]{2,}/", p["key"])
                self.assertTrue(s["outlet"].strip(), p["key"])

    def test_journey_stops(self):
        for p in self.people:
            self.assertTrue(p["journey"], p["key"])
            for j in p["journey"]:
                self.assertIn(j["kind"], KINDS, p["key"])
                self.assertIn(j["cert"], CERTS, p["key"])
                self.assertTrue(j["org"] or j["org_ko"], p["key"])
                lat, lon = j["lat"], j["lon"]
                self.assertEqual(lat is None, lon is None, p["key"])
                if lat is not None:
                    self.assertTrue(-90 <= lat <= 90 and -180 <= lon <= 180, (p["key"], lat, lon))

    def test_meetings_and_districts_point_at_the_roster(self):
        off_roster = {"miran"}                                     # 반대표 기록에만 나오는 전 이사 — people.js의 OFFROSTER
        self.assertIn("miran: {", read("people.js"))
        for m in self.data["meetings_2026"]:
            self.assertRegex(m["date"], DATE)
            for d in m.get("dissents", []):
                self.assertIn(d["key"], self.keys | off_roster)
                self.assertIn(d["side"], SIDES)
        for e in self.data["events_2026"]:
            self.assertLessEqual(set(e.get("keys", [])), self.keys)
        ns = sorted(d["n"] for d in self.data["districts"])
        self.assertEqual(ns, list(range(1, 13)))
        for d in self.data["districts"]:
            self.assertIn(d["president_key"], self.keys, d["n"])

    def test_every_2026_dissent_appears_in_a_meeting(self):
        held = {(m["date"], d["key"], d["side"]) for m in self.data["meetings_2026"] for d in m.get("dissents", [])}
        for p in self.people:
            for d in p["dissents_2026"]:
                self.assertIn((d["date"], p["key"], d["side"]), held, p["key"])

    def test_map_is_precomputed_paths(self):
        mp = self.data["map"]
        self.assertTrue(mp["w"] > 0 and mp["h"] > 0)
        self.assertGreaterEqual(len(mp["paths"]), 48)
        for st, d in mp["paths"].items():
            self.assertRegex(st, r"^[A-Z]{2}$")
            self.assertRegex(d if isinstance(d, str) else d.get("d", ""), r"^M[-0-9.,\sMLZz]+$", st)


if __name__ == "__main__":
    unittest.main()
