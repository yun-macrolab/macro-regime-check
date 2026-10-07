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

    def test_motion_and_shortcuts_can_be_turned_off(self):
        self.assertIn('id="motion-toggle"', self.page)
        self.assertIn('id="keys-toggle"', self.page)
        self.assertIn('html[data-motion="off"]', self.css)
        self.assertIn("ev.repeat", self.page)                     # 키를 누르고 있어도 화면이 계속 넘어가지 않는다
        self.assertIn("ev.isComposing", self.page)                # 한글 조합 중에는 단축키로 보지 않는다

    def test_print_shows_lines_that_were_never_scrolled_into_view(self):
        block = self.css[self.css.index("@media print"):]
        self.assertIn("stroke-dasharray: none", block)


if __name__ == "__main__":
    unittest.main()
