"""연준 인물 페이지(site/people.html · people.css · people.js · people-data.js)의 정적 검사 — 브라우저 없이 글자만 본다.
표준 라이브러리만, 네트워크 불필요.

  껍데기   문서 머리(문자 집합 · 화면 폭 · 제목) · 바깥에서는 글꼴만 · 스크립트는 자료 → 그리기 순 · 점검 페이지와 서로 잇는다
  표시     '참고 — 예측 아님'이 머리에 보이고 '초안'은 자료의 review가 draft일 때만 · 비공개 쪽 낱말(비공개 · 분석실 · 발언 판정의 꼴)이
           없다 · 사람 사진 · 기관 로고(이미지)가 없다 · 바깥에서 싣는 것은 글꼴뿐(CSP meta · url( · href · src)
  자료     people-data.js가 window.PEOPLE_DATA = {JSON}; 꼴이고, 사람 · 회의 · 지구 · 지도의 칸과 범위가 맞는다 ·
           출처 주소는 https · 이메일 주소가 없다 · 회의 반대표 ↔ 사람 반대표(양쪽) · 지구 총재 ↔ 그 사람의 지구 ·
           인용마다 같은 날짜의 출처 · 사람이 나오는 사건마다 출처 · 진영 꼬리표마다 라벨 출처(없으면 '사전 지식') ·
           이름에 앞뒤 · 겹 공백 없음(띠의 이름 표시가 빈 글자로 멈추지 않게) · 지구 총재는 지구 번호 순
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
VS_BASE = ("평소와 같음", "평소보다 매파", "평소보다 비둘기", "새 주제")   # 자동 분류 칸의 판정(scripts/people_push.py의 VS_BASE와 같다)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def read(name):
    with open(os.path.join(SITE, name), encoding="utf-8") as f:
        return f.read()


def load_data(text):
    """people-data.js → dict. 꼴이 다르면 ValueError(머리 주석 + window.PEOPLE_DATA = {JSON}; 한 문장만)."""
    m = re.fullmatch(r"\s*(?:/\*(?:(?!\*/).)*\*/\s*)?window\.PEOPLE_DATA = (\{.*\});\s*", text, re.S)
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
        self.assertIn("참고 — 예측 아님`", read("people.js"))    # 큰 제목 줄
        data = load_data(read("people-data.js"))
        self.assertIn(data["review"], ("draft", "approved"))
        if data["review"] == "draft":                               # 승인하면 자료의 review만 바꾼다 — 머리 표시는 people.js가 바꾼다
            self.assertIn("초안", head)
            self.assertTrue(data["notes"][0].startswith("초안"))
        self.assertIn('DATA.review !== "approved"', read("people.js"))

    def test_only_fonts_are_loaded_from_outside(self):
        # 싣는 것(link href · src · css url( · @import)은 같은 폴더의 파일 · 페이지 안 조각(#) · 글꼴 두 곳뿐
        css = re.sub(r"/\*.*?\*/", "", read("people.css"), flags=re.S)
        self.assertNotIn("@import", css)
        for target in re.findall(r"url\(\s*['\"]?([^'\")\s]*)", css):
            self.assertTrue(target.startswith("#"), target)
        loads = re.findall(r'<link\b[^>]*\bhref="([^"]*)"', self.page) + re.findall(r'\bsrc="([^"]*)"', self.page)
        for u in loads:
            host = re.match(r"(?:https:)?//([^/]+)", u)
            ok = (host and host.group(1) in ("fonts.googleapis.com", "fonts.gstatic.com")) or re.fullmatch(r"[\w.-]+", u)
            self.assertTrue(ok, u)
        csp = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">', self.page)
        self.assertIsNotNone(csp)
        for part in ("default-src 'none'", "script-src 'self'", "font-src https://fonts.gstatic.com", "connect-src 'self'",
                     "object-src 'none'", "base-uri 'none'", "trusted-types 'none'", "require-trusted-types-for 'script'"):
            self.assertIn(part, csp.group(1))
        # 읽기(fetch)는 같은 출처의 자동 분류 발언 파일 하나뿐 — connect-src에 바깥 주소가 없다(2026-11-04 'none' → 'self')
        self.assertEqual(re.findall(r"connect-src ([^;]+)", csp.group(1)), ["'self'"])

    def test_attributes_from_data_cannot_be_handlers(self):
        js = read("people.js")
        self.assertEqual(js.count("/^on/i.test(k)"), 2)            # el() · sv() 둘 다 on* 속성을 버린다
        self.assertEqual(re.findall(r"\bhref:", js), ["href:"])    # 바깥 링크는 safeLink 하나(https만)로
        self.assertIn('/^https:\\/\\//.test(u)', js[js.index("function safeLink"):js.index("function safeLink") + 200])

    def test_no_private_wording(self):
        for name in FILES:
            text = read(name)
            for word in ("비공개", "분석실", "my_path", "fed_people", "알림 줄", "page_data", "corrected_profile",
                         "닿은 항목", "기준선 갱신 검토", "프로필에 없는 반대표", "agree", "평가 로그"):
                self.assertNotIn(word, text, f"{name}: {word}")

    def test_verdict_words_only_in_the_automatic_section(self):
        # 2026-11-04 사용자 결정 — 발언 판정은 자동 분류로 이 페이지에 싣는다. 판정의 낱말은 그 칸의 열거값(people.js)에만 있고,
        # 사람이 고치는 프로필 자료 · 껍데기 · 모양에는 없다
        js = read("people.js")
        for word in VS_BASE:
            for name in ("people.html", "people.css", "people-data.js"):
                self.assertNotIn(word, read(name), f"{name}: {word}")
            self.assertEqual(js.count(f'"{word}"'), 2, word)       # 열거값(RM.vs) · 칩 모양(VS_LOOK) 두 곳

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
        py_part, node_part = m.group(3).split(" / node: ")
        self.assertRegex(py_part, rf"(^|· )연준 인물 화면 {mine}( ·|$)")
        with open(os.path.join(REPO, "scripts", "test_people_render.cjs"), encoding="utf-8") as f:
            cjs = len(re.findall(r"^test\(", f.read(), flags=re.M))
        self.assertRegex(node_part, rf"(^| · )연준 인물 그리기 {cjs}( · |$)")
        self.assertIn("node --test scripts/test_people_render.cjs", readme)
        with open(os.path.join(REPO, ".github", "workflows", "daily.yml"), encoding="utf-8") as f:
            wf = f.read()
        self.assertIn("node --test scripts/test_people_render.cjs", wf[wf.index("\n  check:"):wf.index("\n  update:")])   # 배포 앞의 검사

    def test_missing_data_stops_with_a_message(self):
        js = read("people.js")
        start = js[:js.index("function el(")]
        self.assertIn("const DATA = window.PEOPLE_DATA || {};", start)
        self.assertIn('throw new Error("people-data.js 없음")', start)


def remarks_block():
    """people.js의 '새 발언 — 기준선 대비(자동 분류)' 묶음(머리 주석부터 위원 모니터 앞까지)."""
    js = read("people.js")
    return js[js.index("/* ───────── 새 발언 — 기준선 대비(자동 분류)"):js.index("/* ───────── 위원 모니터 (명단)")]


def js_array(block, name):
    """RM 안의 `name: [ "..", .. ]` → 목록(JSON 꼴 문자열만)."""
    m = re.search(rf"\b{name}: (\[[^\]]*\])", block)
    return json.loads(m.group(1))


class RemarksCodeTest(unittest.TestCase):
    """자동 분류 발언 칸(2026-11-04) — 같은 출처 파일 하나를 읽고, 게시기(scripts/people_push.py)와 같은 약속으로 다시 검사하고, 글자로만 넣는다."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(REPO, "scripts"))
        import people_push
        cls.P = people_push
        cls.block = remarks_block()

    def test_one_relative_uncached_read(self):
        js = read("people.js")
        self.assertEqual(js.count("fetch("), 1)
        self.assertIn('url: "data/people_remarks.json"', self.block)            # 같은 폴더 기준 상대 주소(배포는 data/를 site 옆에 둔다)
        self.assertIn('await fetch(RM.url, { cache: "no-store", signal: ctl ? ctl.signal : undefined })', self.block)
        self.assertIn("setTimeout(() => { if (ctl) ctl.abort(); }, 15000)", self.block)   # 응답이 멈춰도 15초 뒤 '없음'으로
        self.assertEqual(self.P.PATH, "data/people_remarks.json")
        self.assertIn("paintStrip(); loadRemarks();", js[js.index("/* ───────── 시작"):])

    def test_contract_matches_the_publisher(self):
        b, P = self.block, self.P
        self.assertIn(f'schema: "{P.SCHEMA}"', b)
        for name, want in (("top", P.PUBLIC_KEYS), ("fields", P.FIELDS), ("venues", P.VENUES), ("access", P.ACCESS), ("vs", P.VS_BASE),
                           ("sides", P.SIDES), ("tags", P.TAGS), ("reviews", P.REVIEWS)):
            self.assertEqual(tuple(js_array(b, name)), want, name)
        self.assertEqual(VS_BASE, P.VS_BASE)
        limits = dict((k, int(v)) for k, v in re.findall(r"(\w+): (\d+)", re.search(r"limits: \{([^}]*)\}", b).group(1)))
        self.assertEqual(limits, P.LIMITS)
        nums = {k: int(v) for k, v in re.findall(r"\b(words|basisMax|basisText|pathMax|perPerson|maxItems|windowDays): (\d+)", b)}
        self.assertEqual(nums, {"words": P.QUOTE_WORDS, "basisMax": P.BASIS_MAX, "basisText": P.BASIS_TEXT, "pathMax": P.PATH_MAX,
                                "perPerson": P.PER_PERSON, "maxItems": P.MAX_ITEMS, "windowDays": P.WINDOW_DAYS})
        self.assertIn(f'cut: "{P.CUT}"', b)
        self.assertIn("show: 8, strip: 10", b)                                  # 파일 칸 8개(나머지는 접기) · 머리 띠 10개
        self.assertIn(r"/[\p{Cc}\p{Cf}\p{Zl}\p{Zp}\p{Cs}]/u", b)              # 보이지 않는 글자 = 게시기의 INVISIBLE
        self.assertEqual(P.INVISIBLE, ("Cc", "Cf", "Zl", "Zp", "Cs"))

    def test_whole_file_is_dropped_on_a_bad_head_and_bad_items_are_skipped(self):
        check = self.block[self.block.index("function checkRemarks"):self.block.index("const reviewKo")]
        self.assertIn("return null;", check)                                    # 머리의 꼴이 다르면 파일 전체를 버린다
        self.assertIn("skipped++; continue;", check)                            # 틀린 발언은 그 발언만
        self.assertIn("(per[r.who] || 0) >= RM.perPerson", check)
        load = self.block[self.block.index("async function loadRemarks"):]
        self.assertIn('{ state: "none", list: [] }', load)
        self.assertIn('rmNone("자동 발언 기록 없음")', self.block)

    def test_text_goes_in_as_text(self):
        b = self.block
        for word in ("innerHTML", "outerHTML", "insertAdjacent", "setAttribute(", "href", "document.write", "createElement("):
            self.assertNotIn(word, b, word)                                      # 요소는 el()로만 — el은 글을 textContent · 글 마디로 넣는다
        self.assertIn('if (k === "class") n.className = v; else if (k === "text") n.textContent = v;', read("people.js"))
        self.assertNotIn("lang: \"en\", text: r.quote", b)                       # 인용은 따옴표 안에
        self.assertEqual(b.count("text: `“${r.quote}”`"), 2)

    def test_fixed_label_and_headings(self):
        # 판정 · 까닭 · 인용 고르기는 언어 모델이 쓴다 — '운영 규칙'(이 사이트에서 규칙 = 정해 둔 계산)이라 하지 않는다(2026-11-04 검토)
        b = self.block
        label = ("자동 분류 — 언어 모델(AI)이 기사를 읽고 운영자가 정리한 ${base}에 견준 결과입니다. 사람 확인 없이 매일 올라가며 "
                 "틀릴 수 있고, 예측이 아닙니다. 인용은 발언자 본인의 말을 15단어 이내로 옮긴 것입니다.")
        self.assertIn(label, b)
        self.assertNotIn("운영 규칙", b)
        self.assertIn("기준선(${r.baseline_asof} · ${reviewKo(r.baseline_review)})", b)     # 발언 칸 = 그 발언이 견준(고정된) 기준선
        self.assertIn("기준선(${reviewKo(reviewOf(p))})", b)                                  # 발언이 없으면 지금 프로필의 것
        self.assertIn('v === "approved" ? "확인함" : "초안"', b)
        self.assertEqual(b.count("remarkLabel("), 3)                            # 정의 · 사람 파일 · 머리 띠
        for text in ('"최근 발언 — 기준선 대비(자동 분류)"', '"새 발언 — 기준선 대비(자동 분류)"', "견준 항목: ", "반대표 ", '"전언"'):
            self.assertIn(text, b, text)

    def test_baseline_review_is_per_person(self):
        # 사람마다 자료의 review(approved · draft), 없거나 다른 값이면 페이지 전체(DATA.review) — 기준선 칸과 발언 칸의 문구 둘 다
        js = read("people.js")
        self.assertIn("function reviewOf(p) { return p && RM.reviews.includes(p.review) ? p.review : DATA.review; }", self.block)
        body = js[js.index("function renderFile("):js.index("function routeTexts(")]
        self.assertIn('"운영자 정리 · " + reviewKo(reviewOf(p))', body)
        self.assertIn("remarkLabel(mine[0], p)", self.block)
        self.assertNotIn("DATA.review === \"approved\" ? \"확인함\"", js)
        for p in load_data(read("people-data.js"))["people"]:
            if "review" in p:
                self.assertIn(p["review"], ("draft", "approved"), p["key"])

    def test_quotes_carry_their_source(self):
        # 인용마다 출처(매체 · 제목, 둘 다 비면 '운영자가 모은 기사(매체 미기재)') — 머리 띠에도 인용 바로 뒤에, 전언 표시도 함께
        b = self.block
        self.assertIn('"출처: " + ([r.source, r.title].filter(Boolean).join(" · ") || "운영자가 모은 기사(매체 미기재)")', b)
        self.assertEqual(b.count("rmHearsay(r)"), 3)                             # 정의 · 사람 파일 · 머리 띠
        strip = b[b.index("function paintStrip"):b.index("async function loadRemarks")]
        self.assertLess(strip.index("r.quote ? el(\"span\", { class: \"rm-quote\""), strip.index("rmSource(r)"))
        self.assertIn('r.quote || r.source || r.title ? el("p", { class: "rm-src", text: rmSource(r) })', b)

    def test_empty_person_names_the_window_of_the_file(self):
        # 파일이 담은 기간(window_from ~ asof)을 그대로 말하고, 상한으로 덜어 낸 파일(window_from이 365일 창보다 늦다)이면 그렇다고 한다
        b = self.block
        self.assertIn("`${remarks.from}부터 ${remarks.asof}까지 공개된 이 사람의 자동 분류 발언 없음`", b)
        self.assertIn("(span < RM.windowDays - 1 ? ` (파일 상한으로 ${remarks.from} 앞의 발언은 싣지 않음)` : \"\")", b)
        self.assertNotIn("이후 이 사람의", b)
        self.assertEqual(int(re.search(r"\bwindowDays: (\d+)", b).group(1)), self.P.WINDOW_DAYS)

    def test_a_late_strip_keeps_the_view(self):
        # 띠가 화면 위에 있을 때 늘어난 만큼 스크롤을 맞춘다(스크롤 고정이 없는 브라우저 — 사람 주소로 연 좁은 화면의 파일이 밀리지 않게)
        load = self.block[self.block.index("async function loadRemarks"):]
        self.assertLess(load.index("getBoundingClientRect().bottom <= 0"), load.index("paintStrip();"))
        self.assertLess(load.index("paintStrip();"), load.index("window.scrollBy(0, dy)"))

    def test_names_open_the_file_the_way_the_page_navigates(self):
        b = self.block
        self.assertIn('el("button", { type: "button", class: "rm-who", "data-key": p.key', b)
        self.assertIn("select(p.key, { push: true, scroll: true, focus: true })", b)
        self.assertIn('$("caveat").after(box)', b)                               # 껍데기(people.html)는 CSP 말고 바꾸지 않는다

    def test_section_sits_after_the_baseline(self):
        js = read("people.js")
        body = js[js.index("function renderFile("):js.index("function routeTexts(")]
        self.assertLess(body.index("f.append(base);"), body.index('el("section", { id: "sec-new"'))
        self.assertLess(body.index('id: "sec-new"'), body.index('const routeSec = el("section"'))
        css = read("people.css")
        for cls in (".vs.same", ".vs.hawk", ".vs.dove", ".vs.new", ".rm-strip", ".rm-row", ".rm-list", ".rm-more summary"):
            self.assertIn(cls + " ", css, cls)

    def test_data_note_tells_the_section_is_automatic(self):
        notes = load_data(read("people-data.js"))["notes"]
        hit = [n for n in notes if "자동" in n and "사람 확인 없이" in n]
        self.assertEqual(len(hit), 1)
        self.assertIn("예측이 아니다", hit[0])
        self.assertIn("15단어", hit[0])


class DataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data(read("people-data.js"))
        cls.people = cls.data["people"]
        cls.keys = {p["key"] for p in cls.people}

    def test_file_shape_is_one_assignment(self):
        self.assertRaises(ValueError, load_data, "window.PEOPLE_DATA = {};\nalert(1);")
        self.assertRaises(ValueError, load_data, "var x = 1;")
        self.assertRaises(ValueError, load_data, "/* a */ alert(1); /* b */\nwindow.PEOPLE_DATA = {};\n")   # 두 주석 사이의 코드
        self.assertEqual(load_data("/* 주석 */\nwindow.PEOPLE_DATA = {\"a\": 1};\n"), {"a": 1})

    def test_header_fields(self):
        self.assertRegex(self.data["asof"], DATE)
        self.assertTrue(any("초안" in n for n in self.data["notes"]))
        self.assertTrue(any("참고 — 예측 아님" in n for n in self.data["notes"]))
        scale = self.data["stance_scale"]
        self.assertEqual((scale["min"], scale["max"], scale["step"]), (-2, 2, 0.5))

    def test_names_have_no_stray_spaces(self):
        # 띠는 사건 글에서 성(이름의 마지막 낱말)을 찾는다 — 끝 공백이면 성이 빈 글자가 된다(2026-11-01 검토: 페이지가 멈춤)
        for p in self.people:
            for f in ("name_ko", "name_en"):
                self.assertEqual(p[f], p[f].strip(), (p["key"], f))
                self.assertNotIn("  ", p[f], (p["key"], f))
            self.assertTrue(p["name_ko"].split()[-1], p["key"])

    def test_bank_presidents_follow_district_order(self):
        bank = [p["district"] for p in self.people if p["seat"] == "bank"]
        self.assertEqual(bank, sorted(bank))
        seats = [p["seat"] for p in self.people]
        self.assertEqual(seats, sorted(seats, key=["board", "ny", "bank"].index))

    def test_quotes_have_a_source_of_the_same_date(self):
        for p in self.people:
            dates = {s["date"] for s in p["sources"]}
            for q in p["phrases"]:
                self.assertIn(q["date"], dates, (p["key"], q["text"][:30]))
                self.assertLessEqual(len(q["text"].split()), 15, (p["key"], q["text"][:30]))

    def test_events_carry_a_level_and_people_events_a_source(self):
        for e in self.data["events_2026"]:
            self.assertIn(e["cert"], ("1차", "2차"), e["date"])
            for s in e["src"]:
                self.assertRegex(s["url"], r"^https://[a-z0-9.-]+\.[a-z]{2,}/", e["date"])
            if e.get("keys"):
                self.assertTrue(e["src"], f"{e['date']}: 사람이 나오는 사건은 출처가 있어야 한다")
        self.assertIn('확인 수준 ${e.cert', read("people.js"))           # 띠의 title에 확인 수준 · 출처

    def test_camp_labels_cite_who_said_so(self):
        for p in self.people:
            if p["camp"] == "미상":
                continue
            src = p.get("camp_src") or []
            self.assertTrue(src or p.get("camp_cert") == "사전 지식", p["key"])
            urls = {s["url"] for s in p["sources"]}
            for s in src:
                self.assertRegex(s["url"], r"^https://", p["key"])
                self.assertIn(s["url"], urls, p["key"])                  # 출처 목록에도 보인다

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
        by_key = {p["key"]: p for p in self.people}
        for m in self.data["meetings_2026"]:
            self.assertRegex(m["date"], DATE)
            for d in m.get("dissents", []):
                self.assertIn(d["key"], self.keys | off_roster)
                self.assertIn(d["side"], SIDES)
                if d["key"] in by_key:                                    # 회의 → 사람 방향도
                    self.assertIn({"date": m["date"], "side": d["side"]}, by_key[d["key"]]["dissents_2026"], d["key"])
        for e in self.data["events_2026"]:
            self.assertLessEqual(set(e.get("keys", [])), self.keys)
        ns = sorted(d["n"] for d in self.data["districts"])
        self.assertEqual(ns, list(range(1, 13)))
        for d in self.data["districts"]:
            self.assertIn(d["president_key"], self.keys, d["n"])
            pres = by_key[d["president_key"]]
            if d["n"] == 2:
                self.assertEqual(pres["seat"], "ny")
            else:
                self.assertEqual((pres["seat"], pres["district"]), ("bank", d["n"]), d["n"])

    def test_ledger_tallies_and_chairs(self):
        # 표결 장부의 '칸 합'(people.js)은 배포된 화면에서만 '?'를 띄우고, 의장 키가 틀리면 그 표시도 없다 — 회의 결과를 손으로
        # 옮길 때(12월 회의 등) 여기서 먼저 본다. 칸을 세는 규칙은 people.js와 같다: 2026 투표권자 가운데 지금 자리 시작일(memberSince —
        # 지금 자리 기록의 note에 적힌 날짜) 이후인 사람 + 명단 밖 위원(OFFROSTER)은 until까지
        off = re.search(r'const OFFROSTER = \{ miran: \{[^}]*until: "(\d{4}-\d{2}-\d{2})" \} \};', read("people.js"))
        self.assertIsNotNone(off, "people.js의 OFFROSTER 꼴이 다르다 — 이 검사도 같이 고친다")
        until = off.group(1)
        voters = [p for p in self.people if p["voter_2026"]]
        self.assertEqual(len(voters), 12)

        def since(p):
            j = next((x for x in p["journey"] if x.get("now") and x.get("from") == "2026"), None)
            m = re.search(r"(\d{4})-(\d{2})(?:-(\d{2}))?", (j or {}).get("note") or "")
            return f"{m.group(1)}-{m.group(2)}-{m.group(3) or '01'}" if j and m else None
        for m in self.data["meetings_2026"]:
            day = m["date"]
            self.assertIn(m["chair"], self.keys, f"{day}: 의장 {m['chair']!r}이 명단의 키가 아니다")
            dis = [x["key"] for x in m.get("dissents", [])]
            self.assertEqual(len(dis), len(set(dis)), day)
            self.assertEqual(m["vote"] is None, m["decision"] == "예정", f"{day}: 표가 없는 회의만 '예정'")
            if m["vote"] is None:
                self.assertEqual(dis, [], day)
                continue
            got = re.fullmatch(r"(\d{1,2})-(\d{1,2})", m["vote"])
            self.assertIsNotNone(got, f"{day}: 표 {m['vote']!r}")
            a, b = int(got.group(1)), int(got.group(2))
            seated = {p["key"] for p in voters if not since(p) or since(p) <= day} | ({"miran"} if day <= until else set())
            self.assertLessEqual(set(dis), seated, f"{day}: 반대표를 낸 사람이 그때 위원이 아니다")
            self.assertEqual((a, b), (len(seated) - len(dis), len(dis)),
                             f"{day}: 발표 {m['vote']} ≠ 칸 합 {len(seated) - len(dis)}-{len(dis)}")

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
