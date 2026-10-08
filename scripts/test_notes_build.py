#!/usr/bin/env python3
"""읽기 노트 빌더(notes_build) 테스트 — 받는 문법만 블록으로 풀고, 그 밖의 것은 줄 번호와 함께 멈추는지.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — 문법 테스트는 지어낸 글만 쓴다(읽은 글의 문장은 테스트에 넣지 않는다).
끝의 RepoTest는 저장소의 notes/*.md와 data/notes.json이 서로 맞는지 본다(다시 만들어 비교).
"""
import os, re, sys, io, json, shutil, tempfile, unittest, contextlib, subprocess

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import notes_build as nb

REPO = os.path.dirname(SCRIPTS)
SLUG = "2026-01-05-made-up-note"
HEAD = {"제목": "지어낸 노트 제목", "날짜": "2026-01-05", "출처": "어느 기관 소식지 1호", "원문 제목": "A Made-up Title",
        "원문 주소": "https://example.org/letters/1", "저자": "가 · 나", "발행일": "2026-01-02", "읽는 시간": "7",
        "난이도": "하", "한 줄 결론": "**첫 문장이다.** 둘째 문장이다."}
QUESTIONS = "::질문\n1. 첫째 질문인가?\n2. 둘째 질문인가?\n3. 셋째 질문인가?\n"
FENCE = "`" * 3
DIAGRAM = {
    "kind": "balance", "title": "지어낸 도식", "alt": "두 칸짜리 개념도. 왼쪽은 위로, 오른쪽은 0 근처에 놓인다.",
    "zero": "차이 = 0", "net": "차이가 놓이는 곳",
    "forces": [{"key": "lift", "label": "위로 미는 힘", "short": "위", "effect": "위로 민다(+)"},
               {"key": "drag", "label": "아래로 미는 힘", "short": "아래", "effect": "아래로 민다(−)"}],
    "columns": [{"label": "왼쪽", "forces": [{"key": "lift", "dir": "up", "size": 2, "note": "있다"},
                                            {"key": "drag", "dir": "down", "size": 1, "note": "작다"}],
                 "net": [{"pos": "above", "note": "양(+)"}]},
                {"label": "오른쪽", "highlight": True, "forces": [],
                 "net": [{"pos": "below", "tag": "전", "note": "음(−)"}, {"pos": "zero", "tag": "뒤", "note": "0 근처"}]}],
    "foot": "화살표 길이는 순서만 뜻한다.",
}


def note(body="## 요약\n\n문단 하나.\n", questions=QUESTIONS, **head):
    """지어낸 노트 한 편의 글 — 머리말 + 본문 + 질문. head에 None을 주면 그 이름을 뺀다."""
    fields = {**HEAD, **head}
    front = "\n".join(f"{k}: {v}" for k, v in fields.items() if v is not None)
    return f"---\n{front}\n---\n\n{body}\n{questions}"


def parse(body="## 요약\n\n문단 하나.\n", slug=SLUG, **kw):
    return nb.parse_note(slug, note(body, **kw))


def blocks(body):
    return parse(body)["blocks"][:-1]            # 끝의 질문 블록은 뺀다


def fenced(d):
    return f"{FENCE}도식\n{json.dumps(d, ensure_ascii=False, indent=1)}\n{FENCE}\n"


class InlineTest(unittest.TestCase):
    def test_plain_text_is_one_piece(self):
        self.assertEqual(nb.inline("가나다 라마"), [{"text": "가나다 라마"}])

    def test_bold_and_link(self):
        self.assertEqual(nb.inline("가 **나** 다"), [{"text": "가 "}, {"text": "나", "bold": True}, {"text": " 다"}])
        self.assertEqual(nb.inline("[글](https://example.org/a?b=1#c)"),
                         [{"text": "글", "href": "https://example.org/a?b=1#c"}])
        self.assertEqual(nb.inline("**굵은 [글](https://example.org/a) 끝**"),
                         [{"text": "굵은 ", "bold": True}, {"text": "글", "bold": True, "href": "https://example.org/a"},
                          {"text": " 끝", "bold": True}])

    def test_ordinary_marks_stay_text(self):
        for s in ("근원물가<3%이고 a < b", "A&B 그리고 R&D", "[추정] 값은 (괄호) 안에", "snake_case_name 그대로", "50% 넘게 + 1"):
            self.assertEqual(nb.inline(s), [{"text": s}], s)

    def test_only_https_links(self):
        for url in ("http://example.org/a", "javascript:alert(1)", "/notes/other", "other.md", "mailto:a@example.org",
                    "ftp://example.org/a", "//example.org/a", "https://", "https://exa mple.org", "data:text/html,x", ""):
            with self.assertRaises(nb.NoteError, msg=url):
                nb.inline(f"[글]({url})")

    def test_unknown_inline_syntax_stops_the_build(self):
        bad = ["`코드`", "역슬래시 \\* 하나", "<b>굵게</b>", "줄<br/>바꿈", "<!-- 숨긴 글 -->", "![그림](https://example.org/a.png)",
               "*기울임*", "별표 * 하나", "_기울임_", "~~지움~~", "맨 주소 https://example.org/a", "www.example.org 참고",
               "&amp; 엔티티", "&#39; 엔티티", "**닫히지 않은 굵게", "** **", "[](https://example.org/a)",
               "[ ](https://example.org/a)", "[글] (https://example.org/a) 그리고 [글](", "[글][참조]", "탭\t문자",
               "[`코드`](https://example.org/a)", "[<b>굵게</b>](https://example.org/a)"]      # 링크의 글도 같은 검사를 거친다
        for s in bad:
            with self.assertRaises(nb.NoteError, msg=s):
                nb.inline(s)

    def test_invisible_characters_are_rejected(self):
        # 폭 없는 공백 · 방향을 뒤집는 글자 · 글 가운데의 BOM · 부드러운 붙임표 — 눈에 안 보여 원본과 화면이 달라진다
        for s in ("폭 없는\u200b공백", "방향을 뒤집는\u202e글자", "글 가운데\ufeff표식", "부드러운\u00ad붙임표"):
            with self.assertRaises(nb.NoteError, msg=ascii(s)):
                nb.inline(s)
        for url in ("https://example.org/a\u200bb", "https://example.org/a\x01b", "https://example.org/\u202ea"):
            with self.assertRaises(nb.NoteError, msg=ascii(url)):
                nb.inline(f"[글]({url})")
            with self.assertRaises(nb.NoteError, msg=ascii(url)):
                parse(**{"원문 주소": url})

    def test_error_carries_the_line_number(self):
        with self.assertRaises(nb.NoteError) as cm:
            nb.inline("`코드`", 12)
        self.assertEqual(cm.exception.line, 12)
        self.assertIn("12째 줄", str(cm.exception))


class HeadTest(unittest.TestCase):
    def test_reads_every_field(self):
        n = parse()
        self.assertEqual(list(n), ["slug", "title", "date", "source", "minutes", "level", "summary", "blocks"])
        self.assertEqual((n["slug"], n["title"], n["date"], n["minutes"], n["level"]),
                         (SLUG, "지어낸 노트 제목", "2026-01-05", 7, "하"))
        self.assertEqual(n["source"], {"name": "어느 기관 소식지 1호", "title": "A Made-up Title",
                                       "url": "https://example.org/letters/1", "authors": "가 · 나", "published": "2026-01-02"})
        self.assertEqual(n["summary"], [{"text": "첫 문장이다.", "bold": True}, {"text": " 둘째 문장이다."}])

    def test_value_may_contain_a_colon(self):
        self.assertEqual(parse(**{"원문 제목": "Part One: A Made-up Title"})["source"]["title"], "Part One: A Made-up Title")

    def test_value_may_be_wrapped_in_double_quotes(self):
        # GitHub이 머리말을 YAML로 읽는다 — **로 시작하거나 ': '가 든 값은 따옴표로 감싸야 오류 상자가 안 뜬다
        n = parse(**{"한 줄 결론": '"**첫 문장이다.** 둘째 문장이다."', "제목": '"지어낸 노트 제목"'})
        self.assertEqual(n, parse())
        self.assertEqual(parse(**{"난이도": "'하'"})["level"], "'하'")           # 작은따옴표는 글자다
        with self.assertRaises(nb.NoteError):
            parse(**{"저자": '""'})                                           # 따옴표뿐인 값은 빈 값

    def test_every_name_is_required_and_no_other_is_allowed(self):
        for name in HEAD:
            with self.assertRaises(nb.NoteError, msg=name):
                parse(**{name: None})
        with self.assertRaises(nb.NoteError):
            parse(**{"태그": "물가"})
        with self.assertRaises(nb.NoteError):
            nb.parse_note(SLUG, note().replace("난이도: 하", "난이도: 하\n난이도: 중"))        # 같은 이름 두 번
        with self.assertRaises(nb.NoteError):
            parse(**{"저자": ""})

    def test_front_matter_must_open_and_close(self):
        with self.assertRaises(nb.NoteError):
            nb.parse_note(SLUG, "## 요약\n\n문단.\n\n" + QUESTIONS)
        with self.assertRaises(nb.NoteError):
            nb.parse_note(SLUG, note().replace("---\n\n## 요약", "\n## 요약"))

    def test_dates_numbers_and_address_are_checked(self):
        for name, value in (("날짜", "2026-13-40"), ("날짜", "1월 5일"), ("발행일", "2026/01/02"), ("읽는 시간", "7분"),
                            ("읽는 시간", "0"), ("읽는 시간", "1000"), ("원문 주소", "http://example.org/letters/1"),
                            ("원문 주소", "example.org/letters/1"), ("제목", "**굵은** 제목"),
                            ("저자", "[가](https://example.org/a)"), ("제목", "가" * 81), ("한 줄 결론", "가" * 401)):
            with self.assertRaises(nb.NoteError, msg=f"{name}={value}"):
                parse(**{name: value})

    def test_file_name_carries_the_note_date(self):
        with self.assertRaises(nb.NoteError):
            parse(slug="2026-01-06-made-up-note")                    # 머리말 날짜와 다르다
        for slug in ("made-up-note", "2026-01-05", "2026-01-05-Made-Up", "2026-01-05-지어낸-노트", "2026-01-05-a b",
                     "2026-01-05-a--b", "../2026-01-05-a"):
            with self.assertRaises(nb.NoteError, msg=slug):
                parse(slug=slug)


class BlockTest(unittest.TestCase):
    def test_headings_get_running_ids(self):
        got = blocks("## 첫 절\n\n문단.\n\n### 작은 절\n\n문단.\n\n## 둘째 절\n\n문단.\n")
        heads = [b for b in got if b["type"] == "heading"]
        self.assertEqual(heads, [{"type": "heading", "level": 2, "text": "첫 절", "id": "s1"},
                                 {"type": "heading", "level": 3, "text": "작은 절", "id": "s2"},
                                 {"type": "heading", "level": 2, "text": "둘째 절", "id": "s3"}])

    def test_other_heading_levels_are_rejected(self):
        for body in ("# 큰 제목\n", "#### 너무 작은 제목\n", "##붙여 쓴 제목\n", "## **굵은** 제목\n", "## \n"):
            with self.assertRaises(nb.NoteError, msg=body):
                parse(body)

    def test_lines_of_a_paragraph_are_joined(self):
        self.assertEqual(blocks("첫 줄이고\n둘째 줄이다.\n\n다음 문단 **굵게**.\n"),
                         [{"type": "para", "spans": [{"text": "첫 줄이고 둘째 줄이다."}]},
                          {"type": "para", "spans": [{"text": "다음 문단 "}, {"text": "굵게", "bold": True}, {"text": "."}]}])

    def test_lists(self):
        got = blocks("- 하나\n- 둘은\n  이어 쓴다\n\n1. 첫째\n2. **둘째**\n")
        self.assertEqual(got[0], {"type": "list", "ordered": False,
                                  "items": [[{"text": "하나"}], [{"text": "둘은 이어 쓴다"}]]})
        self.assertEqual(got[1], {"type": "list", "ordered": True,
                                  "items": [[{"text": "첫째"}], [{"text": "둘째", "bold": True}]]})

    def test_broken_lists_are_rejected(self):
        for body in ("1. 첫째\n3. 셋째\n", "2. 둘째부터\n", "- 하나\n  - 안쪽 목록\n", "- 하나\n1. 섞어 쓴 번호\n",
                     "- 하나\n바로 붙은 문단\n", "-붙여 쓴 항목\n", "* 별표 목록\n", "+ 더하기 목록\n",
                     "- 하나\n 한 칸만 들여 쓴 줄\n", "- 하나\n\n- 둘\n", "1. 하나\n\n2. 둘\n", "1. 하나\n\n1. 다시 하나\n",
                     "- 하나\n \n\n- 둘\n"):
            with self.assertRaises(nb.NoteError, msg=body):
                parse(body)

    def test_blank_line_between_items_is_named(self):
        # 빈 줄을 사이에 둔 항목은 조용히 한 항목짜리 목록 여러 개가 되지 않는다 — 그 줄과 까닭을 알린다
        for body, second in (("- 하나\n\n- 둘\n", "- 둘"), ("1. 하나\n\n2. 둘\n", "2. 둘")):
            text = note("## 요약\n\n" + body)
            with self.assertRaises(nb.NoteError) as cm:
                nb.parse_note(SLUG, text)
            self.assertEqual(text.split("\n")[cm.exception.line - 1], second)
            self.assertIn("빈 줄", cm.exception.reason)
        # 종류가 다른 목록은 빈 줄을 두고 이어 써도 된다
        self.assertEqual([b["ordered"] for b in blocks("- 하나\n\n1. 첫째\n\n- 둘\n")], [False, True, False])

    def test_table(self):
        got = blocks("| 이름 | 값 | 비고 |\n|---|---|:--|\n| 가 | **1** | |\n| 나 | [글](https://example.org/a) | 끝 |\n")
        self.assertEqual(got, [{"type": "table",
                                "head": [[{"text": "이름"}], [{"text": "값"}], [{"text": "비고"}]],
                                "rows": [[[{"text": "가"}], [{"text": "1", "bold": True}], []],
                                         [[{"text": "나"}], [{"text": "글", "href": "https://example.org/a"}], [{"text": "끝"}]]]}])
        self.assertEqual(blocks("| | 값 |\n|---|---|\n| 가 | 1 |\n")[0]["head"], [[], [{"text": "값"}]])   # 빈 머리 칸

    def test_broken_tables_are_rejected(self):
        for body in ("| 이름 | 값 |\n| 가 | 1 |\n", "| 이름 | 값 |\n|---|---|\n", "| 이름 | 값 |\n|---|---|\n| 가 |\n",
                     "| 이름 | 값 |\n|---|---|\n| 가 | 1 | 2 |\n", "| 이름 | 값 |\n|---|---|\n| 가 | 1\n"):
            with self.assertRaises(nb.NoteError, msg=body):
                parse(body)

    def test_figure_directives(self):
        got = blocks("::사이트그래프 some_rule | 사이트의 오늘 자료 — **지어낸** 캡션\n\n::정적그래프 made_up | 받아 둔 값\n")
        self.assertEqual(got[0], {"type": "figure", "kind": "site_chart", "rule": "some_rule",
                                  "caption": [{"text": "사이트의 오늘 자료 — "}, {"text": "지어낸", "bold": True}, {"text": " 캡션"}]})
        self.assertEqual(got[1], {"type": "figure", "kind": "static_chart", "chart": "made_up",
                                  "caption": [{"text": "받아 둔 값"}]})

    def test_unknown_or_malformed_directives_are_rejected(self):
        for body in ("::그림 some_rule | 캡션\n", "::사이트그래프 some_rule\n", "::사이트그래프 some_rule |\n",
                     "::사이트그래프 Some-Rule | 캡션\n", "::사이트그래프 | 캡션\n", "::정적그래프 ../x | 캡션\n", "::\n",
                     "::질문 하나 더\n"):
            with self.assertRaises(nb.NoteError, msg=body):
                parse(body)

    def test_questions_block(self):
        n = parse()
        self.assertEqual(n["blocks"][-1], {"type": "questions", "items": [[{"text": "첫째 질문인가?"}],
                                                                         [{"text": "둘째 질문인가?"}], [{"text": "셋째 질문인가?"}]]})

    def test_a_note_has_exactly_one_block_of_three_questions(self):
        with self.assertRaises(nb.NoteError):
            parse(questions="")                                             # 질문이 없다
        with self.assertRaises(nb.NoteError):
            parse(questions=QUESTIONS + "\n" + QUESTIONS)                     # 두 번
        with self.assertRaises(nb.NoteError):
            parse(questions="::질문\n1. 하나뿐인가?\n")
        with self.assertRaises(nb.NoteError):
            parse(questions="::질문\n1. 하나\n2. 둘\n3. 셋\n4. 넷\n")
        with self.assertRaises(nb.NoteError):
            parse(questions="::질문\n- 번호 없는 목록\n- 둘\n- 셋\n")
        with self.assertRaises(nb.NoteError):
            parse(questions="::질문\n\n문단이 온다.\n")

    def test_diagram(self):
        got = blocks(fenced(DIAGRAM))
        self.assertEqual(got, [{"type": "figure", "kind": "diagram", "diagram": DIAGRAM}])
        slim = {k: v for k, v in DIAGRAM.items() if k != "foot"}
        self.assertNotIn("foot", blocks(fenced(slim))[0]["diagram"])            # 없어도 되는 이름

    def test_diagram_declaration_is_validated(self):
        def changed(path, value):
            d = json.loads(json.dumps(DIAGRAM))
            node = d
            for k in path[:-1]:
                node = node[k]
            if value is None:
                del node[path[-1]]
            else:
                node[path[-1]] = value
            return d
        cases = [(("kind",), "flow"), (("title",), None), (("alt",), ""), (("alt",), 3), (("extra",), "모르는 이름"),
                 (("title",), "<b>굵게</b>"), (("title",), "**굵게**"), (("title",), "가" * 61), (("forces",), []),
                 (("forces", 0, "key"), "Lift!"), (("forces", 1, "key"), "lift"), (("columns",), []),
                 (("columns",), [DIAGRAM["columns"][0]] * 5), (("columns", 0, "forces", 0, "key"), "other"),
                 (("columns", 0, "forces", 1, "key"), "lift"), (("columns", 0, "forces", 0, "dir"), "left"),
                 (("columns", 0, "forces", 0, "size"), 4), (("columns", 0, "forces", 0, "size"), True),
                 (("columns", 0, "forces", 0, "size"), "2"), (("columns", 0, "net"), []),
                 (("columns", 0, "net", 0, "pos"), "middle"), (("columns", 1, "highlight"), "yes"),
                 (("columns", 1, "net", 0, "tag"), "가" * 11), (("columns", 0, "color"), "red"),
                 # 화면이 그리는 한도(힘 둘 · 자리 둘 · 설명 600자)를 넘는 것 — 넘으면 화면이 조용히 잘라 그린다
                 (("forces",), DIAGRAM["forces"] + [{**DIAGRAM["forces"][0], "key": "third"}]),
                 (("columns", 0, "net"), [{"pos": p, "note": "자리 셋"} for p in ("above", "zero", "below")]),
                 (("alt",), "가" * 601),
                 # 꼬리표: 그림 폭에 들어갈 만큼만(한글 5자 · 영문과 숫자 10자), 두 자리는 서로 달라야 겹치지 않는다
                 (("columns", 1, "net", 0, "tag"), "가" * 6), (("columns", 1, "net", 0, "tag"), "a" * 11),
                 (("columns", 1, "net", 1, "pos"), "below")]
        for path, value in cases:
            with self.assertRaises(nb.NoteError, msg=f"{path}={value!r}"):
                parse(fenced(changed(path, value)))
        for tag in ("가" * 5, "2026년 뒤", "a" * 10):                           # 한도 안의 꼬리표
            got = blocks(fenced(changed(("columns", 1, "net", 0, "tag"), tag)))[0]["diagram"]
            self.assertEqual(got["columns"][1]["net"][0]["tag"], tag)

    def test_diagram_json_errors_name_the_line(self):
        raw = json.dumps(DIAGRAM, ensure_ascii=False, indent=1).split("\n")
        raw[2] = raw[2].replace(":", "", 1)                                  # 펜스 안 셋째 줄의 콜론을 뺀다
        text = note(f"{FENCE}도식\n" + "\n".join(raw) + f"\n{FENCE}\n")
        with self.assertRaises(nb.NoteError) as cm:
            nb.parse_note(SLUG, text)
        self.assertEqual(text.split("\n")[cm.exception.line - 1], raw[2])    # 펜스를 연 줄이 아니라 틀린 그 줄
        with self.assertRaises(nb.NoteError):
            parse(f"{FENCE}도식\n{'[' * 100000}\n{FENCE}\n")                  # 깊이 겹친 JSON도 줄 번호와 함께 멈춘다
        twice = fenced(DIAGRAM).replace('"kind": "balance",', '"kind": "flow",\n "kind": "balance",', 1)
        self.assertIn('"kind": "flow"', twice)
        with self.assertRaises(nb.NoteError):
            parse(twice)                                                     # 같은 이름 두 번 — 뒤 것이 조용히 이기지 않는다

    def test_only_the_diagram_fence_is_known(self):
        for body in (f"{FENCE}\n코드\n{FENCE}\n", f"{FENCE}python\nprint(1)\n{FENCE}\n", f"{FENCE}도식\n{{깨진 json\n{FENCE}\n",
                     f"{FENCE}도식\n{json.dumps(DIAGRAM)}\n", f"{FENCE}도식\n[1, 2]\n{FENCE}\n"):
            with self.assertRaises(nb.NoteError, msg=body):
                parse(body)

    def test_unknown_block_syntax_stops_the_build(self):
        for body in ("> 인용문\n", "---\n", "***\n", "    들여 쓴 코드\n", " 한 칸 들여 쓴 문단\n", "<div>원시 HTML</div>\n",
                     "<script>alert(1)</script>\n", "문단 다음 줄에\n<b>태그</b>\n", "제목처럼\n===\n"):
            with self.assertRaises(nb.NoteError, msg=body):
                parse(body)

    def test_error_names_the_line_in_the_file(self):
        text = note("## 요약\n\n문단 하나.\n\n> 인용문\n")
        with self.assertRaises(nb.NoteError) as cm:
            nb.parse_note(SLUG, text)
        self.assertEqual(text.split("\n")[cm.exception.line - 1], "> 인용문")

    def test_windows_line_endings_and_bom_change_nothing(self):
        text = note("## 요약\n\n- 하나\n- 둘\n\n| 가 | 나 |\n|---|---|\n| 1 | 2 |\n")
        want = nb.parse_note(SLUG, text)
        self.assertEqual(nb.parse_note(SLUG, text.replace("\n", "\r\n")), want)
        self.assertEqual(nb.parse_note(SLUG, "\ufeff" + text), want)

    def test_a_note_needs_a_body(self):
        with self.assertRaises(nb.NoteError):
            parse(body="", questions="")


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.notes, self.out = os.path.join(self.tmp, "notes"), os.path.join(self.tmp, "data")
        os.makedirs(self.notes)

    def put(self, slug, text):
        with open(os.path.join(self.notes, slug + ".md"), "w", encoding="utf-8", newline="") as f:
            f.write(text)

    def run_main(self, *args):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            rc = nb.main(["--notes", self.notes, "--out", self.out, *args])
        return rc, err.getvalue()

    def test_newest_note_comes_first(self):
        srcs = [("2026-01-05-made-up-note", note()), ("2026-02-01-later-note", note(**{"날짜": "2026-02-01"})),
                ("2026-01-05-another-note", note())]
        got = nb.build(srcs)
        self.assertEqual(set(got), {"schema", "notes"})
        self.assertEqual(got["schema"], nb.SCHEMA)
        self.assertEqual([n["slug"] for n in got["notes"]],
                         ["2026-02-01-later-note", "2026-01-05-made-up-note", "2026-01-05-another-note"])
        self.assertEqual(nb.build(list(reversed(srcs))), got)                  # 읽은 순서와 무관

    def test_same_input_gives_the_same_bytes(self):
        self.put(SLUG, note(fenced(DIAGRAM)))
        self.assertEqual(self.run_main()[0], 0)
        path = os.path.join(self.out, "notes.json")
        with open(path, "rb") as f:
            first = f.read()
        self.assertEqual(self.run_main()[0], 0)
        with open(path, "rb") as f:
            self.assertEqual(f.read(), first)
        self.assertTrue(first.endswith(b"\n") and b"\r" not in first)        # 어느 운영체제에서 만들어도 같은 줄바꿈
        self.assertEqual(json.loads(first)["notes"][0]["slug"], SLUG)
        self.assertNotRegex(first.decode("utf-8"), r"\d{2}:\d{2}:\d{2}")      # 만든 시각을 싣지 않는다
        self.assertEqual(os.listdir(self.out), ["notes.json"])                # 임시 파일을 남기지 않는다

    def test_check_mode_compares_without_writing(self):
        self.put(SLUG, note())
        self.assertEqual(self.run_main("--check")[0], 1)                      # 아직 만든 적이 없다
        self.assertFalse(os.path.exists(os.path.join(self.out, "notes.json")))
        self.assertEqual(self.run_main()[0], 0)
        self.assertEqual(self.run_main("--check")[0], 0)
        self.put(SLUG, note("## 요약\n\n고친 문단.\n"))
        self.assertEqual(self.run_main("--check")[0], 1)

    def test_one_bad_note_stops_everything_and_keeps_the_old_file(self):
        self.put(SLUG, note())
        self.assertEqual(self.run_main()[0], 0)
        with open(os.path.join(self.out, "notes.json"), "rb") as f:
            before = f.read()
        self.put("2026-02-01-later-note", note("> 인용문\n", **{"날짜": "2026-02-01"}))
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("2026-02-01-later-note.md", err)                        # 어느 파일 몇째 줄인지
        self.assertRegex(err, r"\d+째 줄")
        with open(os.path.join(self.out, "notes.json"), "rb") as f:
            self.assertEqual(f.read(), before)

    def test_badly_named_or_undecodable_files_are_errors(self):
        self.put("draft", note())
        self.assertEqual(self.run_main()[0], 1)
        os.remove(os.path.join(self.notes, "draft.md"))
        with open(os.path.join(self.notes, SLUG + ".md"), "wb") as f:
            f.write(note().encode("cp949"))
        self.assertEqual(self.run_main()[0], 1)

    def test_other_files_in_the_folder_are_left_alone(self):
        self.put(SLUG, note())
        with open(os.path.join(self.notes, "메모.txt"), "w", encoding="utf-8") as f:
            f.write("> 노트가 아니다")
        self.assertEqual(self.run_main()[0], 0)

    def test_no_notes_is_an_empty_list(self):
        self.assertEqual(nb.build([]), {"schema": nb.SCHEMA, "notes": []})
        self.assertEqual(nb.collect(self.notes), [])                          # 폴더는 있고 글이 아직 없다
        self.assertEqual(self.run_main()[0], 0)
        with open(os.path.join(self.out, "notes.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["notes"], [])

    def test_missing_folder_is_an_error_not_an_empty_list(self):
        # --notes를 잘못 적었을 때 빈 notes.json을 쓰고 성공으로 끝나지 않는다
        rc, err = self.run_main("--notes", os.path.join(self.tmp, "없는 폴더"))
        self.assertEqual(rc, 1)
        self.assertIn("노트 폴더가 없다", err)
        self.assertFalse(os.path.exists(os.path.join(self.out, "notes.json")))

    def test_notes_with_another_spelling_of_the_extension_are_errors(self):
        # .MD · .markdown은 조용히 건너뛰지 않는다(글을 썼는데 목록에 안 나오는 일이 없게)
        for name in (SLUG + ".MD", SLUG + ".Md", SLUG + ".markdown"):
            path = os.path.join(self.notes, name)
            with open(path, "w", encoding="utf-8") as f:
                f.write(note())
            rc, err = self.run_main()
            os.remove(path)
            self.assertEqual(rc, 1, name)
            self.assertIn(name, err)


class ConsoleTest(unittest.TestCase):
    """한글 윈도 콘솔(cp949)로 내보내도 안내 문구가 죽지 않는다 — 문구에 cp949에 없는 글자(긴 줄표)가 있다."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.env = {**os.environ, "PYTHONIOENCODING": "cp949", "PYTHONUTF8": "0"}

    def test_check_mode_says_so_when_the_file_differs(self):
        notes = os.path.join(self.tmp, "notes")
        os.makedirs(notes)
        with open(os.path.join(notes, SLUG + ".md"), "w", encoding="utf-8", newline="") as f:
            f.write(note())
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "notes_build.py"), "--notes", notes,
                            "--out", os.path.join(self.tmp, "data"), "--check"], capture_output=True, env=self.env, timeout=60)
        self.assertEqual(r.returncode, 1)
        self.assertIn("다르다", r.stdout.decode("utf-8", "replace"))
        self.assertNotIn(b"UnicodeEncodeError", r.stderr)

    def test_every_note_script_switches_the_console_to_utf8(self):
        # 셋 다 저장소의 파일을 건드리지 않고 끝나는 길로 부른다: 없는 노트 폴더 · .work/ 밖의 미리보기 폴더 · 수신 실패
        missing, out = os.path.join(self.tmp, "nowhere"), os.path.join(self.tmp, "data")
        calls = {"notes_build": f"m.main(['--notes', {missing!r}, '--out', {out!r}])",
                 "notes_preview": f"m.main(['--out', {out!r}])",
                 "notes_charts": f"m.main(['--out', {out!r}], opener=lambda *a, **k: open({missing!r}))"}
        for name, call in calls.items():
            code = f"import sys; sys.path.insert(0, {SCRIPTS!r}); import {name} as m; {call}; print(sys.stdout.encoding)"
            r = subprocess.run([sys.executable, "-c", code], capture_output=True, env=self.env, timeout=60)
            self.assertEqual(r.stdout.decode("ascii", "replace").split()[-1:], ["utf-8"], name)


def walk(x):
    """dict·list 안의 모든 dict."""
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk(v)


class RepoTest(unittest.TestCase):
    """저장소에 실린 노트 — 원본과 산출물이 맞는지, 그림이 가리키는 자료가 있는지."""

    @classmethod
    def setUpClass(cls):
        cls.built = nb.build(nb.collect(nb.DEFAULT_NOTES))
        with open(os.path.join(REPO, "data", "notes.json"), encoding="utf-8") as f:   # 줄바꿈은 읽을 때 맞춘다
            cls.stored = f.read()

    def test_notes_json_matches_the_sources(self):
        # 어긋나면: python scripts/notes_build.py 를 다시 돌려 함께 커밋한다
        self.assertEqual(self.stored, nb.dumps(self.built))

    def test_there_is_at_least_one_note(self):
        self.assertGreaterEqual(len(self.built["notes"]), 1)

    def test_every_link_is_https(self):
        hrefs = [d["href"] for d in walk(self.built) if "href" in d] + [n["source"]["url"] for n in self.built["notes"]]
        self.assertTrue(hrefs)
        for h in hrefs:
            self.assertRegex(h, r"^https://[A-Za-z0-9.-]+/", h)

    def test_site_charts_are_rules_the_page_knows(self):
        # 매일 바뀌는 data/charts.json이 아니라 화면에 적힌 규칙 목록으로 본다(자료가 하루 비어도 검사가 막히지 않게)
        with open(os.path.join(REPO, "site", "index.html"), encoding="utf-8") as f:
            page = f.read()
        known = set(re.findall(r'"([a-z0-9_]+)"', "".join(re.findall(r"keys: \[([^\]]*)\]", page))))
        self.assertIn("real_rate_bei", known)
        for d in walk(self.built):
            if d.get("kind") == "site_chart":
                self.assertIn(d["rule"], known)

    def test_static_charts_exist_in_the_stored_chart_file(self):
        wanted = {d["chart"] for d in walk(self.built) if d.get("kind") == "static_chart"}
        if not wanted:
            return
        with open(os.path.join(REPO, "data", "notes_charts.json"), encoding="utf-8") as f:
            charts = json.load(f)["charts"]
        self.assertLessEqual(wanted, set(charts))


if __name__ == "__main__":
    unittest.main()
