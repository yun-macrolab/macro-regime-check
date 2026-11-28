"""용어 사전 자료(site/glossary.js) 검사 — 브라우저와 node 없이 글자만 본다. 표준 라이브러리만 쓴다.

  꼴        ENTRIES의 줄은 모두 { id: "…", term: "…", def: "…", see: "…" }, 한 줄에 한 항목(역슬래시 없음)
  수 · 겹침  항목 35개 이상, id는 소문자 · 숫자 · 하이픈, id와 낱말(대소문자 무시)은 겹치지 않는다
  관련 화면  see는 빈 글이거나 index.html이 아는 화면 — applyView의 const known 목록 · GROUPS의 id · paged 목록.
            목록은 index.html에서 읽으므로 화면이 더해지면(예: glossary) 그대로 따라간다. 링크 이름(SCREENS)도 있어야 한다
  정의      160자 이하, 한두 문장, '니다.'로 끝남, 예측 · 권유 낱말 없음
  글자      낱말 · 정의에 꺾쇠 · 제어 문자 없음. 파일 어디에도 'BAML' · 시나리오 이름(A~D)의 뜻을 적는 꼴 · 바깥 주소 없음,
            test_site_origin의 금지 낱말(BANNED)과 세는 낱말(WATCHED — createElement · fetch( · localStorage 등) 없음

실행:  python -X utf8 scripts/test_glossary_site.py
"""
import os
import re
import sys
import unicodedata
import unittest

from test_site_origin import BANNED, WATCHED

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOSSARY = os.path.join(REPO, "site", "glossary.js")
INDEX = os.path.join(REPO, "site", "index.html")

MIN_ENTRIES = 35
MAX_DEF = 160
FORBIDDEN = ("매수", "매도", "유망", "추천", "전망", "예상", "적중", "오른다", "내린다")      # 예측 · 권유 표현
SCENARIO = re.compile(r"시나리오\s*[A-D]")

BLOCK = re.compile(r"^  const ENTRIES = Object\.freeze\(\[\n(.*?)^  \]\);$", re.S | re.M)
ENTRY = re.compile(r'\s*\{ id: "([^"\\]*)", term: "([^"\\]*)", def: "([^"\\]*)", see: "([^"\\]*)" \},')
SCREENS = re.compile(r"const SCREENS = Object\.freeze\(\{(.*?)\}\);", re.S)
SCREEN_KEY = re.compile(r'(?:"([a-z-]+)"|\b([a-z]+)): "')


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def screen_ids(index):
    """index.html이 아는 화면 id — const known의 글자 값 + GROUPS의 id + paged 목록. 하나라도 읽지 못하면 ValueError."""
    known = re.search(r"const known = \[(.*?)\];", index, re.S)
    groups = re.search(r"const GROUPS = \[(.*?)\n\];", index, re.S)
    paged = re.search(r"\bpaged = \[(.*?)\]\.includes\(", index, re.S)
    if not (known and groups and paged):
        raise ValueError("index.html에서 화면 목록(const known · GROUPS · paged)을 읽지 못했다")
    out = set(re.findall(r'"([a-z0-9-]+)"', known.group(1) + paged.group(1)))
    if "GROUPS.map" in known.group(1):
        out |= set(re.findall(r'\bid: "([a-z0-9-]+)"', groups.group(1)))
    return out


def entries(text):
    """(항목 목록, 꼴이 어긋난 줄 목록). 목록 안의 빈 줄과 // 줄만 넘긴다."""
    block = BLOCK.search(text)
    if not block:
        return [], ["ENTRIES 목록을 찾지 못함"]
    good, bad = [], []
    for line in block.group(1).split("\n"):
        if not line.strip() or line.strip().startswith("//"):
            continue
        m = ENTRY.fullmatch(line)
        if m:
            good.append(dict(zip(("id", "term", "def", "see"), m.groups())))
        else:
            bad.append("꼴이 어긋난 줄: " + line.strip()[:60])
    return good, bad


def problems(text, index):
    """glossary.js 글자의 문제 → 문구 목록(없으면 빈 목록)."""
    rows, out = entries(text)
    screens = screen_ids(index)
    table = SCREENS.search(text)
    named = {a or b for a, b in SCREEN_KEY.findall(table.group(1))} if table else set()
    if len(rows) < MIN_ENTRIES:
        out.append("항목 %d개 — %d개 이상이어야 한다" % (len(rows), MIN_ENTRIES))
    ids, terms = set(), set()
    for r in rows:
        who = r["id"] or r["term"]
        if not re.fullmatch(r"[a-z0-9-]+", r["id"]):
            out.append(who + ": id 꼴")
        if r["id"] in ids:
            out.append(who + ": id 겹침")
        if not r["term"].strip() or r["term"] != r["term"].strip():
            out.append(who + ": 낱말이 비었거나 앞뒤 공백")
        if r["term"].lower() in terms:
            out.append(who + ": 낱말 겹침")
        ids.add(r["id"])
        terms.add(r["term"].lower())
        if r["see"] and r["see"] not in screens:
            out.append(who + ": 없는 화면 " + r["see"])
        if r["see"] and r["see"] not in named:
            out.append(who + ": 링크 이름(SCREENS)이 없는 화면 " + r["see"])
        d = r["def"]
        if len(d) > MAX_DEF:
            out.append("%s: 정의 %d자 — %d자 이하" % (who, len(d), MAX_DEF))
        if not d.endswith("니다."):
            out.append(who + ": 정의가 '니다.'로 끝나지 않음")
        if len(re.findall(r"\.(?=\s|$)", d)) > 2:
            out.append(who + ": 정의가 두 문장을 넘음")
        out += ["%s: 금지 낱말 %s" % (who, w) for w in FORBIDDEN if w in r["term"] or w in d]
        for key in ("term", "def", "see"):
            if any(c in "<>" or unicodedata.category(c)[0] == "C" for c in r[key]):
                out.append("%s: %s에 꺾쇠나 제어 문자" % (who, key))
    low = text.lower()
    if "baml" in low:
        out.append("파일에 BAML")
    if SCENARIO.search(text):
        out.append("파일에 시나리오 A~D 꼴")
    if "://" in text:
        out.append("파일에 바깥 주소")
    out += ["파일에 금지 낱말 " + w for w in BANNED + WATCHED if w.lower() in low]
    if any(c != "\n" and unicodedata.category(c)[0] == "C" for c in text):
        out.append("파일에 제어 문자(줄바꿈은 LF)")
    return out


def planted(text, line):
    """ENTRIES 목록의 첫 줄에 line을 끼워 넣은 사본."""
    head = "  const ENTRIES = Object.freeze([\n"
    assert head in text
    return text.replace(head, head + "    " + line + "\n", 1)


def row(id="trap", term="덫", definition="덫으로 넣은 정의입니다.", see=""):
    return '{ id: "%s", term: "%s", def: "%s", see: "%s" },' % (id, term, definition, see)


class GlossaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text, cls.index = read(GLOSSARY), read(INDEX)

    def test_the_file_passes_every_check(self):
        self.assertEqual(problems(self.text, self.index), [])
        # 항목으로 내려갈 때는 html의 scroll-padding-top 하나만 — dt에 scroll-margin-top을 겹치면 휴대폰에서 한참 아래에 선다
        css = read(os.path.join(REPO, "site", "dashboard.css"))
        rules = [r for r in re.findall(r"([^{}]+)\{([^{}]*)\}", css) if "glossary" in r[0]]
        self.assertTrue(rules)
        self.assertEqual([sel.strip() for sel, body in rules if "scroll-margin" in body], [])
        # 첫 화면 안내에서 사전으로 가는 링크 하나(국면 버튼과 같은 줄)
        self.assertIn('<button type="button" id="intro-regime">국면 참고 설명 보기</button>'
                      '<a class="intro-gloss" href="#glossary">용어 사전 보기</a>', self.index)
        self.assertIn("&& q.length >= 2) {", self.index)

    def test_every_line_is_read(self):
        rows, bad = entries(self.text)
        self.assertEqual(bad, [])
        self.assertGreaterEqual(len(rows), MIN_ENTRIES)
        self.assertEqual(len(rows), self.text.count('term: "'), "ENTRIES 밖의 항목이나 읽지 못한 항목이 있다")

    def test_screen_list_is_read_from_the_page(self):
        screens = screen_ids(self.index)
        for name in ("all", "rates", "inflation", "credit", "liquidity", "korea", "korea-credit", "korea-flows", "ai",
                     "ledger", "sources", "evening", "notes"):
            self.assertIn(name, screens)
        with self.assertRaises(ValueError):
            screen_ids("<p>x</p>")

    def test_a_new_screen_is_followed(self):
        page = ('const GROUPS = [\n  { id: "rates" }\n];\nconst known = ["all", ...GROUPS.map(g=>g.id)];\n'
                'const paged = ["notes", "glossary"].includes(base);\n')
        self.assertEqual(screen_ids(page), {"all", "rates", "notes", "glossary"})

    def check_trap(self, line, *words):
        found = problems(planted(self.text, line), self.index)
        for word in words:
            self.assertTrue(any(word in p for p in found), "%s 가 걸리지 않음: %s" % (word, found))

    def test_a_harmless_planted_line_passes(self):
        self.assertEqual(problems(planted(self.text, row()), self.index), [])

    def test_planted_forbidden_words_are_caught(self):
        for word in FORBIDDEN:
            self.check_trap(row(definition="이 낱말은 %s 표현입니다." % word), "금지 낱말 " + word)

    def test_a_planted_unknown_screen_is_caught(self):
        self.check_trap(row(see="nowhere"), "없는 화면 nowhere", "링크 이름(SCREENS)이 없는 화면 nowhere")

    def test_planted_bad_shapes_are_caught(self):
        self.check_trap('{ id: "trap", term: "덫", def: "순서가 다른 줄입니다." },', "꼴이 어긋난 줄")
        self.check_trap(row(definition="역슬래시 \\u003c 입니다."), "꼴이 어긋난 줄")
        self.check_trap(row(id="Trap_1"), "id 꼴")
        self.check_trap(row(id="sofr"), "id 겹침")
        self.check_trap(row(term="sofr"), "낱말 겹침")
        self.check_trap(row(definition="가" * MAX_DEF + "입니다."), "자 이하")
        self.check_trap(row(definition="한다체로 끝낸다."), "'니다.'로 끝나지 않음")
        self.check_trap(row(definition="하나입니다. 둘입니다. 셋입니다."), "두 문장을 넘음")

    def test_planted_bad_letters_are_caught(self):
        self.check_trap(row(definition="<b>굵은</b> 글입니다."), "def에 꺾쇠나 제어 문자")
        self.check_trap(row(term="덫\t덫"), "term에 꺾쇠나 제어 문자", "파일에 제어 문자")
        self.check_trap(row(definition="보이지 않는​ 글자입니다."), "def에 꺾쇠나 제어 문자")
        self.check_trap(row(definition="BAMLX 라는 글입니다."), "파일에 BAML")
        for name in "ABCD":
            self.check_trap(row(definition="시나리오 %s의 뜻입니다." % name), "시나리오 A~D")
        self.check_trap(row(definition="https://example.org 입니다."), "바깥 주소")
        for word in ("innerHTML", "createElement", "fetch(", "localStorage", "location."):
            self.check_trap("// " + word, "파일에 금지 낱말 " + word)

    def test_too_few_entries_are_caught(self):
        small = "  const ENTRIES = Object.freeze([\n    " + row() + "\n  ]);\n"
        self.assertIn("항목 1개 — %d개 이상이어야 한다" % MIN_ENTRIES, problems(small, self.index))


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    unittest.main()
