"""화면(site/)의 정적 검사 — 브라우저 없이 글자만 본다. 네트워크 불필요."""
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
        return f.read()


class PageTest(unittest.TestCase):
    def setUp(self):
        self.page = read("site", "index.html")
        self.css = read("site", "dashboard.css")

    def test_styles_live_in_the_stylesheet_only(self):
        self.assertIn('href="dashboard.css"', self.page)
        self.assertNotIn("<style", self.page)

    def test_only_fonts_come_from_outside(self):
        hosts = set(re.findall(r'<(?:link|script)\b[^>]*?(?:href|src)="https?://([^/"]+)', self.page))
        self.assertEqual(hosts, {"fonts.googleapis.com", "fonts.gstatic.com"})
        self.assertFalse(re.search(r'<script\b[^>]*\bsrc="(?:https?:)?//', self.page))   # 스크립트는 저장소의 것만

    def test_status_line_sits_outside_the_first_screen_box(self):
        # 수신 상태·안내는 다른 화면에서도, 공개본을 못 읽었을 때도 보여야 한다
        bridge = self.page.index('<div id="bridge"')
        for mark in ('<div id="status"', '<p id="notice"'):
            self.assertLess(self.page.index(mark), bridge, mark)     # 첫 화면 상자가 열리기 전에 나온다

    def test_tape_carries_no_channel_numbers(self):
        # 국고채 참고 자료(채널 글)의 숫자는 고지가 함께 보이는 절에서만 나간다
        start = self.page.index("function renderTape(")
        body = self.page[start:self.page.index("\nfunction ", start + 1)]
        for tok in ("latest", "tenor", "국고"):
            self.assertNotIn(tok, body)
        self.assertRegex(self.page, r"renderTape\([^,()]*(?:\([^()]*\))?[^,()]*, charts\)")

    def test_tape_skips_values_that_need_a_notice(self):
        # Moody's Baa−10년(2026-10-30 공개 — 회색 지대)은 고지가 함께 보이는 카드에서만: 띠는 그 규칙을 통째로 건너뛴다
        skip = re.search(r"const TAPE_SKIP = new Set\(\[([^\]]*)\]\);", self.page)
        self.assertIsNotNone(skip)
        self.assertIn('"credit_spread"', skip.group(1))
        start = self.page.index("function renderTape(")
        body = self.page[start:self.page.index("\nfunction ", start + 1)]
        loop = body[body.index("for (const r of"):]
        self.assertRegex(loop[:loop.index("items.push(")], r"if \(!r \|\| TAPE_SKIP\.has\(r\.key\)\) continue;")

    def test_source_section_matches_the_licence_decision(self):
        # '출처와 자료 상태'의 '싣지 않는 것' — ICE 값·S&P 값은 남고, Moody's·Nasdaq 정수 낙폭 %는 2026-10-30부터 싣는다
        start = self.page.index("<h3>싣지 않는 것</h3>")
        block = self.page[start:self.page.index("</article>", start)]
        for word in ("ICE BofA", "S&amp;P 500의 값·수익률·13주 변화 %", "낙폭 시계열", "EBP", "CMDI"):
            self.assertIn(word, block)
        self.assertNotIn("Moody", block)
        self.assertNotIn("낙폭 %는", block)
        source = self.page[self.page.index("<h3>미국 공개 자료 (FRED 경유)</h3>"):start]
        for word in ("Copyrighted: Citation Required", "Moody's 고지", "정수 낙폭 %", "민간 지수 3개"):
            self.assertIn(word, source)

    def test_motion_and_shortcuts_can_be_turned_off(self):
        self.assertIn('id="motion-toggle"', self.page)
        self.assertIn('id="keys-toggle"', self.page)
        self.assertIn('html[data-motion="off"]', self.css)
        self.assertIn("ev.repeat", self.page)                     # 키를 누르고 있어도 화면이 계속 넘어가지 않는다
        self.assertIn("ev.isComposing", self.page)                # 한글 조합 중에는 단축키로 보지 않는다

    def test_print_shows_lines_that_were_never_scrolled_into_view(self):
        block = self.css[self.css.index("@media print"):]
        self.assertIn("stroke-dasharray: none", block)

    def test_evening_and_notes_screens_are_wired(self):
        for view, key, script, style in (("evening", "8", "evening.js", "evening.css"), ("notes", "9", "notes.js", "notes.css")):
            self.assertIn(f'data-view="{view}" aria-keyshortcuts="{key}"', self.page)
            self.assertIn(f'<section id="{view}-wrap" hidden', self.page)
            self.assertIn(f'<script src="{script}"></script>', self.page)
            self.assertIn(f'href="{style}"', self.page)
            self.assertTrue(os.path.getsize(os.path.join(REPO, "site", script)) > 2000, script)   # 뼈대가 아니라 구현
        self.assertEqual(self.page.count("/^[1-9]$/"), 2)        # 명령줄과 숫자 키 둘 다 1~9

    def test_every_loaded_file_is_linked_and_every_script_exists(self):
        # 화면이 읽는 자료 파일은 꼬리말의 '원자료'에서도 열 수 있고, 싣는 스크립트는 site/에 실제로 있다
        loaded = set(re.findall(r'getJson\("(data/[\w.-]+\.json)"\)', self.page))
        self.assertGreaterEqual(len(loaded), 14)
        footer = self.page[self.page.index("<footer>"):self.page.index("</footer>")]
        for path in sorted(loaded):
            self.assertIn(f'<a href="{path}">', footer, path)
        for src in re.findall(r'<script src="([\w.-]+\.js)"></script>', self.page):
            self.assertTrue(os.path.isfile(os.path.join(REPO, "site", src)), src)

    def test_reference_cards_fail_alone(self):
        # 참고 카드(2026-10-30 더한 넷 포함)는 그리기가 깨져도 그 카드만 빠진다 — 부르는 줄마다 try 안, 스크립트가 없어도 부르지 않는다
        for name in ("OilEnergy", "TpCard", "LiquidityCard", "CreditCard", "CdsCard"):
            line = next(l for l in self.page.splitlines() if f"window.{name}.render(" in l)
            self.assertRegex(line, rf"^\s*try \{{ if \(isObj\(\w+\) && window\.{name}\b", name)
        # 신용 긴축·CDS 절은 처음에 숨어 있고, 둘 중 하나라도 그렸을 때 AI 투자 화면에서만 열린다
        self.assertIn('<section id="ai-credit" hidden', self.page)
        self.assertIn('getElementById("ai-credit").hidden = !(available.aiCredit && activeView === "ai")', self.page)
        for slot in ("credit-slot", "cds-slot"):
            section = self.page[self.page.index('<section id="ai-credit"'):]
            self.assertIn(f'id="{slot}"', section[:section.index("</section>")], slot)
        self.assertIn(".credit-slot:empty", self.css)                               # 빈 자리는 보이지 않는다

    def test_morning_status_is_hidden_on_evening_and_notes(self):
        # 아침 갱신의 상태 줄·실패 배너가 저녁판·읽기 노트의 것처럼 읽히지 않게
        self.assertIn('dataset.view = activeView', self.page)
        for view in ("evening", "notes"):
            self.assertIn(f'main[data-view="{view}"] > :is(#status, #notice, #banner)', self.css)


if __name__ == "__main__":
    unittest.main()
