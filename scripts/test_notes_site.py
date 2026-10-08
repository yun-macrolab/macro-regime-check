"""읽기 노트 화면(site/notes.js · site/notes.css)의 정적 검사 — 브라우저 없이 글자만 본다. 네트워크 불필요.

node가 있으면 문법 검사(node --check)와 가짜 DOM 위의 그리기 테스트(test_notes_render.cjs)도 함께 돌린다.
"""
import glob
import os
import re
import shutil
import subprocess
import unicodedata
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which("node")
ISSUES = "https://github.com/yun-macrolab/macro-regime-check/issues"
DIM_FLOOR = "#8a8a8a"                 # 사이트가 흐린 글자에 쓰는 가장 어두운 색 — 글자는 이보다 어둡게 쓰지 않는다


def read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
        return f.read()


def luminance(colour):
    """#rgb · #rrggbb → 상대 휘도(WCAG)."""
    h = colour.strip().lstrip("#")
    h = "".join(c * 2 for c in h) if len(h) == 3 else h
    parts = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    r, g, b = (c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in parts)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def code_only(js):
    """주석을 뗀 스크립트 — 설명 글에 나온 낱말로 검사가 걸리지 않게(문자열 안의 //는 주소뿐이라 남긴다)."""
    return "\n".join(re.sub(r"(?<![:\"'])//.*$", "", line) for line in js.split("\n"))


class ScriptTest(unittest.TestCase):
    def setUp(self):
        self.js = read("site", "notes.js")
        self.code = code_only(self.js)

    def test_text_never_goes_in_as_markup(self):
        for word in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "DOMParser", "createContextualFragment",
                     "eval(", "new Function", "setAttribute(\"on", "srcdoc"):
            self.assertNotIn(word, self.code, word)
        self.assertNotIn("document.createElement", self.code)        # 요소는 index.html의 el() · svgEl()로만 만든다
        self.assertRegex(self.code, r"\bel\(")
        self.assertRegex(self.code, r"\bsvgEl\(")

    def test_no_request_leaves_the_site(self):
        for word in ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource", "sendBeacon", "import(", "importScripts",
                     "new Image", "navigator.", "localStorage", "sessionStorage", "document.cookie", "window.open", "location."):
            self.assertNotIn(word, self.code, word)
        # 읽는 것은 data/ 아래 JSON 셋뿐 — getJson에는 정해 둔 경로만 넘긴다
        self.assertEqual(re.findall(r"getJson\(([^)]*)\)", self.code), ["FILES[name]"])
        files = re.search(r"const FILES = \{([^}]*)\}", self.code).group(1)
        self.assertEqual(sorted(re.findall(r'"([^"]+)"', files)),
                         ["data/charts.json", "data/notes.json", "data/notes_charts.json"])

    def test_only_https_addresses_and_only_the_issues_page_is_written_in(self):
        self.assertEqual(set(re.findall(r"https?://[^\s\"'`)]+", self.code)), {ISSUES})
        self.assertNotRegex(self.code, r"[\"'`]//")                  # 규약 없는 주소도 없다
        self.assertIn("HTTPS.test(s.href)", self.code)              # 자료의 링크는 https일 때만 건다
        self.assertIn("HTTPS.test(src.url)", self.code)
        self.assertRegex(self.code, r"const HTTPS = /\^https:")

    def test_new_window_links_cut_the_opener(self):
        # 새 창 링크는 outLink 한 곳에서만 만든다 — 여는 쪽을 끊고(noopener noreferrer), 화면 읽기용 '(새 창)'을 붙인다
        opened = re.findall(r"\{[^{}]*target: \"_blank\"[^{}]*\}", self.code)
        self.assertEqual(len(opened), 1)
        self.assertIn('rel: "noopener noreferrer"', opened[0])
        self.assertEqual(self.code.count("_blank"), 1)
        maker = self.code[self.code.index("function outLink("):self.code.index("function pieces(")]
        self.assertIn('target: "_blank"', maker)
        self.assertIn('el("span", { class: "sr" }, " (새 창)")', maker)
        self.assertNotRegex(self.code, r'\btitle: "')                # '새 창' 안내를 title 속성에만 적어 두지 않는다

    def test_fixed_notice_is_spelled_out(self):
        self.assertIn("이 노트는 원문을 읽고 내 말로 옮긴 공부 기록이다. 번역이나 전재가 아니며 원문의 문장·그림·표를 싣지 않았다. 틀린 곳은 ",
                      self.js)
        self.assertRegex(self.js, r'outLink\("저장소 Issues", ISSUES\), "로\."\)')
        self.assertEqual(self.code.count("fixedNotice()"), 3)        # 정의 + 목록 + 글

    def test_motion_follows_the_switch(self):
        self.assertIn('behavior: calm() ? "auto" : "smooth"', self.code)
        self.assertNotIn("setInterval", self.code)
        self.assertNotIn(".animate(", self.code)

    def test_keyboard_reaches_everything(self):
        self.assertNotRegex(self.code, r'tabindex: "[1-9]')         # 초점 순서를 바꾸지 않는다
        self.assertNotIn("onclick", self.code)
        # 누르는 것은 링크와 버튼뿐이다 — 버튼이 아닌 것에 click을 걸지 않는다
        self.assertEqual(len(re.findall(r'addEventListener\("click"', self.code)),
                         len(re.findall(r'el\("button", \{ type: "button"', self.code)))
        self.assertEqual(re.findall(r'addEventListener\("(\w+)"', self.code).count("click"),
                         len(re.findall(r"addEventListener\(\"", self.code)) - self.code.count('addEventListener("resize"'))

    def test_page_still_offers_what_the_script_uses(self):
        page = read("site", "index.html")
        for mark in ("function el(tag, attrs, ...children)", "function svgEl(tag, attrs, text)", "async function getJson(path)",
                     "const calm = ()", 'window.ReadingNotes?.setView(activeView, viewArg)', '<script src="notes.js"></script>',
                     '<section id="notes-wrap"', '<link rel="stylesheet" href="notes.css">', 'href="#notes"'):
            self.assertIn(mark, page, mark)
        self.assertLess(page.index('<script src="charts.js">'), page.index('<script src="notes.js">'))

    def test_functions_and_file_stay_small(self):
        self.assertLess(len(self.js.split("\n")), 800)
        starts = [i for i, line in enumerate(self.js.split("\n")) if re.match(r"  (?:async )?function \w+\(", line)]
        lines = self.js.split("\n")
        for a in starts:
            end = next(i for i in range(a + 1, len(lines)) if lines[i] == "  }")
            self.assertLessEqual(end - a + 1, 50, lines[a].strip())

    @unittest.skipUnless(NODE, "node가 없다")
    def test_syntax(self):
        r = subprocess.run([NODE, "--check", os.path.join(REPO, "site", "notes.js")], capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))

    @unittest.skipUnless(NODE, "node가 없다")
    def test_renders_on_a_fake_dom(self):
        r = subprocess.run([NODE, "--test", os.path.join(REPO, "scripts", "test_notes_render.cjs")], capture_output=True,
                           timeout=180)
        self.assertEqual(r.returncode, 0, r.stdout.decode("utf-8", "replace")[-3000:])


class StyleTest(unittest.TestCase):
    def setUp(self):
        self.css = read("site", "notes.css")
        self.rules = re.sub(r"/\*.*?\*/", "", self.css, flags=re.S)
        self.base = read("site", "dashboard.css")

    def test_colours_and_fonts_come_from_the_shared_variables(self):
        self.assertNotRegex(self.rules, r"#[0-9a-fA-F]{3,8}\b")      # 색을 직접 적지 않는다
        self.assertNotRegex(self.rules, r"\b(?:rgb|rgba|hsl|hsla|oklch|color-mix)\(")
        self.assertNotIn("font-family: \"", self.rules)
        for value in re.findall(r"font(?:-family)?:\s*([^;}]+)", self.rules):
            self.assertRegex(value, r"var\(--f-(?:text|mono)\)", value)
        used = set(re.findall(r"var\((--[a-z0-9-]+)", self.rules))
        local = set(re.findall(r"(--note-[a-z]+)\s*:", self.rules))
        for name in used - local:
            self.assertIn(name + ":", self.base, name)                # dashboard.css에 있는 변수만

    def test_nothing_is_loaded_from_outside(self):
        for word in ("url(", "@import", "http:", "https:", "expression("):
            self.assertNotIn(word, self.rules, word)

    def test_narrow_screens_stack_tables_and_diagram(self):
        narrow = self.rules[self.rules.index("@media (max-width: 720px)"):]
        self.assertIn("content: attr(data-label)", narrow)           # 표: 줄마다 카드, 칸마다 머리 글자
        self.assertRegex(narrow, r"\.note-table table[^{]*\{ display: block; \}")
        self.assertRegex(narrow, r"\.nd-grid \{ grid-template-columns: minmax\(0, 1fr\); \}")
        self.assertIn("overflow-wrap: anywhere", self.rules)         # 긴 영문·주소가 글줄을 밀어내지 않게
        self.assertNotRegex(self.rules, r"(?<!max-)(?<!min-)width:\s*\d{3,}px")    # 고정 폭으로 화면을 넘기지 않는다
        self.assertNotIn("white-space: nowrap", narrow.split("@media print")[0])

    def test_reading_measure_is_about_forty_korean_letters(self):
        line = int(re.search(r"--note-line: (\d+)px", self.rules).group(1))
        size = float(re.search(r"\.note \{ font-size: ([\d.]+)px", self.rules).group(1))
        self.assertTrue(36 <= line / size <= 44, line / size)
        self.assertIn(".note-body > * { max-width: var(--note-line); }", self.rules)

    def test_body_rules_do_not_swallow_figures_and_questions(self):
        # .note-body p · .note-body > ol 은 클래스 하나짜리 규칙보다 세다 — 그 안의 그림 글·질문·끝 줄은 더 센 선택자로 적는다
        for selector in (".note-body .note-cap {", ".note-body .note-end {", ".note-body .nd-name {", ".note-fig .ch-note { margin:",
                         ".note-fig .notices p { margin:", ".note-body > .note-questions {", ".note-body > .note-questions > li {",
                         ".note-body .note-questions p {", ".note-body .note-gist p {", ".note-fig .ch-legend { line-height:"):
            self.assertIn(selector, self.rules, selector)
        # 굵은 글의 색·굵기는 글 조각(문단·목록·표 칸) 바로 아래에만 — 본문에 끼운 사이트 그래프의 툴팁 숫자(.ch-tip strong)까지 바꾸지 않게
        self.assertIn(".note-body :is(p, li, td, th) > strong {", self.rules)
        self.assertNotRegex(self.rules, r"\.note-body strong\b")
        # 표 머리 줄의 빈 모서리 칸은 th가 아니라 td다(notes.js) — 머리 줄의 바탕색이 그 칸에서 끊기지 않게 함께 칠한다
        self.assertIn(".note-table thead :is(th, td) { background: var(--bar);", self.rules)

    def test_text_is_never_dimmer_than_the_dim_text_colour(self):
        # 글자 색(color · svg 글자의 fill)은 흐린 글자의 하한보다 어둡지 않게. 축·격자 색(--ch-axis 등)은 선에만 쓴다.
        # 밝은 바탕(노란 키 · 호박색 딱지) 위의 글자는 검정이어야 한다
        names = dict(re.findall(r"(--[a-z0-9-]+):\s*([^;]+);", self.base))

        def colour(name):
            m = re.fullmatch(r"var\((--[a-z0-9-]+)\)", names[name].strip())
            return colour(m.group(1)) if m else names[name].strip()
        floor, seen = luminance(DIM_FLOOR), 0
        for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", self.rules):
            ink = re.search(r"(?<![a-z-])(?:color|fill):\s*var\((--[a-z0-9-]+)\)", body)
            if not ink:
                continue
            seen += 1
            ground = re.search(r"background:\s*var\((--[a-z0-9-]+)\)", body)
            if ground and luminance(colour(ground.group(1))) > 0.3:
                self.assertEqual(colour(ink.group(1)), names["--black"], selector.strip())
            else:
                self.assertGreaterEqual(luminance(colour(ink.group(1))), floor, selector.strip() + " " + ink.group(1))
        self.assertGreater(seen, 15)

    def test_print_keeps_the_source_address_and_fits_the_graphs(self):
        # 종이에는 링크가 없다 — 원문 주소를 글자로 찍고, 화면 폭으로 그린 그래프는 종이 폭에 맞춰 줄인다
        printed = self.rules[self.rules.index("@media print"):]
        self.assertRegex(printed, r"\.note-facts \.note-out::after \{ content: \" \(\" attr\(href\) \"\)\"; \}")
        self.assertRegex(printed, r"\.note-fig \.ch-plot svg \{ max-width: 100%; height: auto; \}")

    def test_empty_cells_stay_in_the_row_on_narrow_screens(self):
        # 빈 칸을 display: none으로 빼면 그 줄의 칸 수가 줄어, 뒤 칸이 앞 열의 머리에 이어져 읽힌다 — 화면에서만 숨긴다
        narrow = self.rules[self.rules.index("@media (max-width: 600px)"):self.rules.index("@media print")]
        rule = re.search(r"\.note-table td\.none \{([^}]*)\}", narrow).group(1)
        self.assertNotIn("display: none", rule)
        self.assertIn("clip-path: inset(50%)", rule)

    def test_no_motion_of_its_own(self):
        for word in ("animation", "transition", "@keyframes"):
            self.assertNotIn(word, self.rules, word)

    def test_classes_used_by_the_script_have_styles(self):
        js = read("site", "notes.js")
        names = set(re.findall(r'class: "([a-z -]+)"', js)) | set(re.findall(r'"(nd-cell nd-key|nd-cell)"', js))
        plain = {"has", "notes", "ch-source"}                        # 표식으로만 쓰는 이름(ch-source는 charts.js와 같은 이름)
        styled = set(re.findall(r"\.([a-z][a-z0-9-]*)", self.rules + self.base))
        self.assertEqual({n for group in names for n in group.split()} - styled - plain, set())


class SourceTest(unittest.TestCase):
    def test_no_invisible_characters_in_the_note_files(self):
        # 보이지 않는 글자(BOM · 폭 없는 공백 등)는 이스케이프(\\ufeff)로 적는다 — 그대로 두면 편집기나 정리 도구가
        # 조용히 지워 뜻이 바뀌고, 눈으로는 알 수 없다. 탭도 쓰지 않는다
        paths = [p for pattern in (("scripts", "notes_*.py"), ("scripts", "test_notes_*"), ("site", "notes.*"),
                                   ("notes", "*.md"), ("data", "notes*.json")) for p in glob.glob(os.path.join(REPO, *pattern))]
        self.assertGreaterEqual(len(paths), 11)
        for path in sorted(paths):
            with open(path, encoding="utf-8", newline="") as f:
                text = f.read()
            odd = sorted({f"U+{ord(c):04X}" for c in text if c not in "\r\n" and unicodedata.category(c) in ("Cc", "Cf")})
            self.assertEqual(odd, [], os.path.relpath(path, REPO))


if __name__ == "__main__":
    unittest.main()
