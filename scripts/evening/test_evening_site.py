#!/usr/bin/env python3
"""저녁판 화면(site/evening.js · evening.css) 테스트. 미리 보기(preview.py)는 test_preview.py, 읽는 순서는 test_evening_site_order.py.

  글자 검사  브라우저 없이 파일의 글자만 본다: 글자는 텍스트 노드로만 · 자료는 data/ 아래에서만 · 코드에 적힌 바깥 주소는 t.me와 삭제 요청
             창구뿐(낱말 풀이의 공식 자료 링크는 자료에서 오고 허용 도메인으로 거른다 — test_evening_site_more.py) ·
             규칙 쪽과 같아야 하는 값(고정 문구 · 허용 단위 · 예약 시각)이 digest_rules와 같은지 · 색과 글꼴은 dashboard.css의 변수만
  그려 보기  node가 있으면 가짜 문서(evening_dom.cjs)에 지어낸 판을 실제로 그린다: 링크의 꼴 · 상태 문구 · 깨진 자료 · 숨김 목록 ·
             지난 판 · 열어 둔 채 시간이 지났을 때. 모양과 가로 넘침(폭 375px)은 여기서 볼 수 없다 — preview.py로 띄워 눈으로 본다

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요 — 자료는 fixtures.py의 지어낸 글로 만든 판뿐이다.
"""
import copy
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import digest_rules as R
import digest_schema as S
import fixtures as F
import preview as PV


def read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
        return f.read()


JS, CSS = read("site", "evening.js"), read("site", "evening.css")
PAGE, BASE = read("site", "index.html"), read("site", "dashboard.css")
NODE = shutil.which("node")
HARNESS = os.path.join(HERE, "evening_dom.cjs")
TAKEDOWN = "https://github.com/yun-macrolab/macro-regime-check/issues/new?template=takedown.md"
HANDLE = S.HANDLE_RE.pattern[1:-1]
POST = re.compile(rf"^https://t\.me/({HANDLE})/[1-9]\d{{0,9}}$")
CHANNEL = re.compile(rf"^https://t\.me/({HANDLE})$")
REQUEST = re.compile(r"^data/(?:digest|digest_index|digest_status|digest_overrides|sources|digest/\d{4}-\d{2}-\d{2})\.json$")
NAMES = {"digest": "digest.json", "index": "digest_index.json", "status": "digest_status.json", "sources": "sources.json",
         "overrides": "digest_overrides.json"}
THU_EVENING = "2026-10-08T19:00:00+09:00"      # 10-08(목) 판이 막 나온 저녁
FRI_MORNING = "2026-10-09T10:00:00+09:00"      # 다음 날 아침 — 오늘 판은 아직 수집 전
FRI_NIGHT = "2026-10-09T22:45:00+09:00"        # 22:41이 지났는데 10-09 판이 없다
C1, C2, C3, C4, C5, C6, C7 = F.CANARIES
_MADE = {}


def code_only(js):
    """주석을 뺀 코드. 문자열 안의 //(주소)는 그대로 둔다."""
    out, i, quote = [], 0, None
    while 0 <= i < len(js):
        c, two = js[i], js[i:i + 2]
        if quote:
            out.append(js[i:i + 2] if c == "\\" else c)
            i += 2 if c == "\\" else 1
            quote = None if c == quote else quote
        elif two == "//":
            i = js.find("\n", i)
        elif two == "/*":
            i = js.find("*/", i) + 2
        else:
            quote = c if c in "\"'`" else None
            out.append(c)
            i += 1
    return "".join(out)


def rules_block():
    """evening.js의 RULES(JSON 꼴로 써 둔 상자) → 사전."""
    return json.loads(re.search(r"const RULES = (\{.*?\n  \});", JS, re.S).group(1))


def fx(name):
    """fixtures의 자료 하나 — 한 번만 만들고 사본을 돌려준다(판 하나 만드는 데 0.1초쯤 든다)."""
    if name not in _MADE:
        _MADE[name] = getattr(F, name)()
    return copy.deepcopy(_MADE[name])


def site(past=None, **swap):
    """지어낸 판 한 벌 {data/ 아래 경로: 자료}. site(digest=None)처럼 빼거나 바꾸고, past = {날짜: 판}으로 지난 판을 둔다."""
    docs = {"digest": fx("digest"), "index": fx("index"), "status": fx("status"), "sources": fx("sources"), "overrides": F.overrides(), **swap}
    out = {"data/" + NAMES[k]: v for k, v in docs.items() if v is not None}
    out.update({f"data/digest/{day}.json": doc for day, doc in (past or {}).items()})
    return out


def play_all(runs):
    """가짜 문서 여러 벌을 node 한 번으로 돌린다. runs = [(자료, [단계 …]), …] → 벌마다 단계별 결과. 화면이 예외를 흘리면 실패한다."""
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in.json")
        with open(src, "w", encoding="utf-8") as f:
            json.dump({"runs": [{"files": files, "steps": list(steps)} for files, steps in runs]}, f, ensure_ascii=False)
        got = subprocess.run([NODE, HARNESS, src], capture_output=True, encoding="utf-8", timeout=120)
    if got.returncode:
        raise AssertionError("가짜 문서에서 화면이 죽었다:\n" + got.stderr[-3000:])
    return json.loads(got.stdout)


def play(files, *steps):
    """가짜 문서 한 벌에서 단계들을 돌린 결과(단계마다 하나)."""
    return play_all([(files, steps)])[0]


def draw(files, now=THU_EVENING, arg=""):
    return play(files, {"now": now, "view": "evening", "arg": arg})[0]


def draws(*cases):
    """저녁판을 연 화면 여러 벌 — cases = 자료, 또는 (자료, 지금), 또는 (자료, 지금, 주소 뒤에 붙은 값)."""
    full = [(c, THU_EVENING, "") if isinstance(c, dict) else (*c, "")[:3] for c in cases]
    return [frames[0] for frames in play_all([(files, [{"now": now, "view": "evening", "arg": arg}]) for files, now, arg in full])]


def calls(name, *arglists):
    """Evening._의 함수를 인자 묶음마다 부른 결과들(node 한 번)."""
    return play({}, *[{"fn": name, "args": list(a) if isinstance(a, tuple) else [a]} for a in arglists])


def named(docs):
    """preview.build()의 자료({이름: 자료})를 화면이 읽는 경로({data/이름: 자료})로."""
    return {"data/" + k: v for k, v in docs.items()}


def ms(when):
    return int(S.parse_iso(when).timestamp() * 1000)


def flat(s):
    return re.sub(r"\s+", "", s)


def blob(frame):
    """화면에 나간 글자 전부 — 본문 · 속성 · 주소."""
    return "\n".join([frame["text"], *frame["attrs"], *(str(a["href"]) for a in frame["links"])])


def outside(frame):
    return [a for a in frame["links"] if not str(a["href"]).startswith("#")]


def posts(frame):
    return [a["href"] for a in frame["links"] if POST.match(str(a["href"]))]


class Screen(unittest.TestCase):
    def shows(self, frame, *needles):
        for n in needles:
            self.assertIn(flat(n), flat(frame["text"]))

    def lacks(self, frame, *needles):
        for n in needles:
            self.assertNotIn(flat(n), flat(frame["text"]))


# ---------- 글자 검사 ----------


class SourceTest(unittest.TestCase):
    def test_text_goes_in_as_text_nodes_only(self):
        for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "DOMParser", "createContextualFragment",
                     "srcdoc", "eval(", "new Function", "createElement"):
            self.assertNotIn(sink, JS, sink)
        self.assertGreater(len(re.findall(r"\bel\(", code_only(JS))), 40)       # 요소는 index.html의 el()로만 만든다

    def test_data_comes_from_the_data_folder_only(self):
        code = code_only(JS)
        for call_ in ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource", "sendBeacon", "import(", "importScripts", "new Image",
                      "window.open", "location.", "postMessage", "localStorage", "sessionStorage", "cookie"):
            self.assertNotIn(call_, code, call_)
        self.assertNotRegex(code, r"\.(?:src|action|formAction)\s*=[^=]")      # 주소를 받는 속성에 손대지 않는다
        args = re.findall(r"getJson\(\s*(.{6})", code)
        self.assertGreaterEqual(len(args), 2)
        for a in args:
            self.assertIn(a, ('"data/', "`data/"))

    def test_outside_addresses_are_the_channel_site_and_the_takedown_form(self):
        found = {u.replace("\\\\.", ".") for u in re.findall(r"https?://[^\s\"'`<>)]+", JS)}
        self.assertIn(TAKEDOWN, found)
        for u in found - {TAKEDOWN}:
            self.assertTrue(u.startswith("https://t.me/"), u)
        self.assertNotRegex(CSS, r"url\(|@import|https?:|@font-face")

    def test_post_address_pattern_is_the_contract_one(self):
        self.assertIn(f'const HANDLE = "{HANDLE}";', JS)
        js_pattern = '"^https://t\\\\.me/(" + HANDLE + ")/([1-9]\\\\d{0,9})$"'
        self.assertIn(js_pattern, JS)
        built = js_pattern.replace('" + HANDLE + "', HANDLE).replace("\\\\", "\\").strip('"')
        self.assertEqual(built, S.URL_RE.pattern.replace("?P<ch>", "").replace("?P<id>", ""))

    def test_new_tab_links_are_made_in_one_place(self):
        code = code_only(JS)
        self.assertEqual(code.count("_blank"), 1)
        self.assertEqual(code.count('{ href, target: "_blank", rel: "noopener noreferrer" }'), 1)
        inner = re.findall(r"href:\s*(.{0,60})", code)                        # 그 밖의 링크는 화면 안의 #evening뿐
        self.assertTrue(inner)
        for expr in inner:
            self.assertIn('"#evening', expr)

    def test_rules_block_matches_the_rules(self):
        rules, th = rules_block(), R.TH
        self.assertEqual(rules["phrases"], R.PHRASES)
        self.assertEqual((rules["groups"], rules["roles"]), (R.GROUPS, R.ROLES))
        self.assertEqual(rules["units"], list(R.UNIT_NAMES))
        self.assertEqual(set(rules["codes"]), set(S.CH_CODES) - {"ok"})
        self.assertLess(set(rules["reasons"]), set(S.REASONS))
        self.assertEqual(set(rules["src"]), {"korea", "calendar"})
        self.assertEqual({f for f in R.FACTORS if R.cell_id(f, R.REGIONS[0]) == f}, set(rules["no_region"]))
        for key in ("run_kst", "late_kst", "edition_shift_h", "show_editions", "keep_days", "min_bond_ok", "min_total_ok",
                    "rows_per_channel", "wire_query"):
            self.assertEqual(rules[key], th[key], key)

    def test_colors_and_fonts_come_from_the_dashboard_variables(self):
        css = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
        self.assertNotRegex(css, r"#[0-9a-fA-F]{3,8}\b")                       # 새 색 값을 두지 않는다
        self.assertNotRegex(css, r"\b(?:rgba?|hsla?|color-mix)\(")
        self.assertNotRegex(css, r":\s*(?:white|black|red|orange|yellow|green|blue|gr[ae]y|silver|gold)\b")
        defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", BASE))
        used = set(re.findall(r"var\((--[a-z0-9-]+)", css))
        self.assertGreaterEqual(len(used), 8)
        self.assertEqual(used - defined, set())
        self.assertNotRegex(css, r"--[a-z0-9-]+\s*:")                          # 새 변수도 만들지 않는다
        for font in re.findall(r"font(?:-family)?\s*:\s*([^;}]+)", css):
            self.assertRegex(font, r"var\(--f-(?:text|mono)\)|inherit", font)

    def test_styles_stay_inside_the_evening_view(self):
        css = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
        css = re.sub(r"@media[^{]*\{", "", css)
        selectors = [s.strip() for block in re.findall(r"([^{}]+)\{", css) for s in block.split(",")]
        self.assertGreater(len(selectors), 30)
        for s in selectors:
            self.assertRegex(s, r"^(?:#evening-wrap\b|\.eve-)", s)

    def test_narrow_screens_are_planned_for(self):
        self.assertIn("@media (max-width: 720px)", CSS)
        self.assertIn("overflow-wrap: anywhere", CSS)
        for px in re.findall(r"(?<!max-)(?:min-)?width\s*:\s*(\d+)px", CSS) + re.findall(r"minmax\((\d+)px", CSS):
            self.assertLessEqual(int(px), 320, px)                             # 폭 375px 화면에 못 들어가는 고정 폭을 두지 않는다
        self.assertNotIn("<table", JS)
        self.assertNotIn('"table"', JS)                                        # 넓은 표 대신 줄이 접히는 목록으로 그린다

    def test_motion_follows_the_shared_switch(self):
        code = code_only(JS)
        self.assertIn("calm()", code)
        for moving in ("requestAnimationFrame", ".animate(", "smooth", "scrollTo", "scrollIntoView"):
            self.assertNotIn(moving, code, moving)
        self.assertIn('html[data-motion="off"] *', BASE)                       # CSS 움직임은 이 규칙이 한꺼번에 끈다
        self.assertNotIn("!important", CSS)                                    # 그 규칙을 이기려 들지 않는다

    def test_page_has_what_the_screen_leans_on(self):
        for mark in ("function el(tag, attrs, ...children)", "async function getJson(path)", "const calm = ()",
                     "window.Evening?.setView(activeView, viewArg)", 'id="evening-wrap"', '<script src="evening.js">',
                     'href="evening.css"'):
            self.assertIn(mark, PAGE, mark)
        self.assertLess(PAGE.index('<script src="evening.js">'), PAGE.index("applyView();"))

    def test_file_sizes_stay_small(self):
        self.assertLessEqual(JS.count("\n"), 800)
        # 60KB → 64KB(2026-10-08 밤): 지문 표 둘(풀이 138개 · 사전 낱말 168개, 합쳐 2.6KB)이 들어왔다 — 화면이 낱말·풀이를 사전과 견주려면 필요하다
        self.assertLess(len(JS.encode("utf-8")), 64_000)

    @unittest.skipUnless(NODE, "node가 없다")
    def test_node_accepts_the_syntax(self):
        for name in (os.path.join(REPO, "site", "evening.js"), HARNESS):
            got = subprocess.run([NODE, "--check", name], capture_output=True, encoding="utf-8", timeout=60)
            self.assertEqual(got.returncode, 0, got.stderr[-500:])


# ---------- 그려 보기: 규칙 ----------


@unittest.skipUnless(NODE, "node가 없다")
class GuardTest(unittest.TestCase):
    def test_edition_date_agrees_with_the_python_rule(self):
        times = ["2026-10-08T17:41:00+09:00", "2026-10-09T05:59:59+09:00", "2026-10-09T06:00:00+09:00", "2026-10-11T23:59:00+09:00",
                 "2026-12-31T23:00:00+09:00", "2027-01-01T03:00:00+09:00"]
        self.assertEqual(calls("editionOf", *map(ms, times)), [S.edition_date(S.parse_iso(t)) for t in times])

    def test_due_edition_is_the_last_weekday_whose_deadline_passed(self):
        want = {"2026-10-08T22:40:59+09:00": "2026-10-07", "2026-10-08T22:41:00+09:00": "2026-10-08",
                "2026-10-10T12:00:00+09:00": "2026-10-09", "2026-10-11T23:00:00+09:00": "2026-10-09",      # 주말판은 없다
                "2026-10-12T09:00:00+09:00": "2026-10-09", "2026-10-13T03:00:00+09:00": "2026-10-12"}
        got = calls("dueEdition", *[(ms(t), "22:41") for t in want], (ms("2026-10-08T21:00:00+09:00"), "20:30"),
                    (ms("2026-10-08T23:00:00+09:00"), "엉뚱한 값"), (ms("2026-10-08T21:00:00+09:00"), None))
        self.assertEqual(got[:-3], list(want.values()))
        self.assertEqual(got[-3:], ["2026-10-08", "2026-10-08", "2026-10-07"])   # 상태 파일의 시각을 따르고, 못 읽으면 22:41로 본다

    def test_judge_tells_fresh_pending_late_and_none(self):
        rows = [("2026-10-08", THU_EVENING, "fresh"), ("2026-10-08", FRI_MORNING, "pending"), ("2026-10-08", FRI_NIGHT, "late"),
                ("2026-10-09", "2026-10-10T12:00:00+09:00", "fresh"), ("2026-10-09", "2026-10-12T09:00:00+09:00", "pending"),
                ("2026-10-07", THU_EVENING, "pending"), ("2026-10-06", THU_EVENING, "late"), (None, THU_EVENING, "none")]
        got = calls("judge", *[(date, ms(now), "22:41") for date, now, _ in rows])
        self.assertEqual([g["kind"] for g in got], [kind for _, _, kind in rows])
        self.assertEqual(got[2]["due"], "2026-10-09")

    def test_number_guard_agrees_with_the_rules(self):
        d = fx("digest")
        seen = [n["v"] for x in d["must"] for n in x["nums"]] + [r["v"] for r in d["wire"]["rows"] + d["solo"]["rows"]]
        odd = ["3.1 %", "3.10%", "03%", "3.1%!", "3.1% 상회", "1e3%", "", "12345678%", "3.1퍼센트", "-0bp", "-4bp", "0.4%p", "+3%",
               "3.1", "%", C1, "3.1%" + C5, "1,234계약"]
        got = calls("num", *seen, *odd, "4732계약", "-1234567.5원")
        self.assertGreater(len(seen), 8)
        self.assertEqual([g is not None for g in got[:-2]], [R.is_num(v) for v in seen + odd])
        self.assertEqual(got[-2:], ["4,732계약", "-1,234,567.5원"])            # 보기 좋게 쉼표만 넣는다

    def test_word_guard_admits_the_whole_dictionary_and_refuses_sentences(self):
        words = [*R.TERMS, *R.RESULT_WORDS, *R.TENORS, *R.CELLS, *R.FACTORS, *R.REGIONS, *R.DIRS, *R.CURVES, *R.BASES]
        # 낱말 사전과 견주는 일은 digest_check의 몫이다 — 화면은 문장·태그·주소·보이지 않는 문자가 섞인 것만 거른다.
        # 그래서 낱말처럼 생긴 짧은 글자(C2 같은 것)는 여기서 걸러지지 않는다
        bad = [C1, C3, C4, C5, C6, C7, "서비스 물가가 끈적하다는 평가가 많다는 지어낸 문장", "미 CPI.", "낱말, 낱말", "", " 미 CPI",
               "a" * 21, 7, None, ["미 CPI"], {"term": "미 CPI"}]
        self.assertEqual(calls("word", *words, *bad), words + [None] * len(bad))

    def test_only_the_fixed_phrases_are_recognised(self):
        codes = list(R.PHRASES)
        good = [R.PHRASES[c].replace("{n}", "7") for c in codes]
        bad = [t + "!" for t in good] + [t.replace("7", "0") for t in good if "7" in t] + list(F.CANARIES) + ["", 3, None]
        self.assertEqual(calls("phraseCode", *good, *bad), codes + [None] * len(bad))

    def test_label_guard(self):
        real = S.read_json(os.path.join(REPO, "data", "sources.json"))           # 사람이 쓴 출처 라벨(채널 글이 아니다)
        ok = [c["label"] for c in fx("sources")["channels"] + real["channels"]]
        bad = [C4, C5, "https://example.org", "a" * 41, "", "@someone", "줄\n바꿈", " 앞뒤 공백 ", 5, None]
        self.assertEqual(calls("label", *ok, *bad), ok + [None] * len(bad))


# ---------- 그려 보기: 판 ----------


@unittest.skipUnless(NODE, "node가 없다")
class EditionTest(Screen):
    @classmethod
    def setUpClass(cls):
        cls.frame = draw(site())

    def test_nothing_is_read_before_the_view_is_opened(self):
        first, second = play(site(), {"now": THU_EVENING, "view": "all"}, {"now": THU_EVENING, "view": "evening"})
        self.assertEqual((first["requested"], first["text"]), ([], ""))       # 첫 화면 로딩을 늦추지 않는다
        self.assertEqual(sorted(second["requested"]), sorted("data/" + n for n in NAMES.values()))

    def test_head_of_the_edition(self):
        self.shows(self.frame, "저녁판 2026-10-08(목)", "시범", "규칙 선별 · 문장 없음", "수집 10-08 18:09",
                   "수집 창 10-07 18:02 ~ 10-08 18:07", "읽은 41건 → 묶음 11 → 후보 3 → 꼭 3건", "24채널 중 24 읽음",
                   "국고 10년 4.376% (+0.7bp) 자료일 10-08", "국고 3년 3.961% (+2.8bp) 자료일 10-08", "→ 보합 · 플랫 당일 종가",
                   "미 10년 5.27% (-4.0bp) 자료일 10-07", "가장 많이 다뤄진 주제: 미 CPI · 국고채 입찰 · 한은 발언")
        self.lacks(self.frame, "판이 없습니다", "수집 부족", "읽지 못했습니다", "내렸습니다")

    def test_must_items_carry_cell_terms_numbers_reasons_coverage_and_links(self):
        self.shows(self.frame, "꼭 3건", "펀더멘털 / 글로벌", "미 CPI · 미 국채 금리", "미 CPI · 상회 · 3.1% 8곳",
                   "채권 채널 3곳", "세 그룹 모두", "발표일 일치", "같은 숫자 8곳", "채권 3곳 · 애널 2곳 · 개인 3곳이", "속보형 1곳 겹침",
                   "가상 채권 bond1 10-07 21:41", "수급 / 국내", "국고채 입찰 · 응찰률 · 247.4% 2곳", "입찰일 일치", "규칙 점수 13.125")
        for url in ("https://t.me/fxbond1/501", "https://t.me/fxbond4/640", "https://t.me/fxanal5/318"):
            self.assertIn(url, posts(self.frame))

    def test_sections_come_in_reading_order(self):
        heads = self.frame["heads"]
        want = ["저녁판 2026-10-08(목)", "꼭 3건", "다가오는 일정", "나머지", "채권 채널 단독 글", "속보형·개인 채널이 혼자 쓴 글", "참고 링크"]
        at = [heads.index(h) for h in want]
        self.assertEqual(at, sorted(at))
        self.assertIn("출처와 수집 방식", self.frame["folds"])

    def test_the_rest_is_folded_by_cell_and_lone_bond_posts_stand_apart(self):
        folds = [flat(f) for f in self.frame["folds"]]
        self.assertTrue(any(f.startswith(flat("펀더멘털/글로벌 1줄")) for f in folds), folds)
        self.assertTrue(any(f.startswith(flat("기타 1줄")) for f in folds), folds)
        self.assertFalse(any(f.startswith(flat("통화정책/국내")) for f in folds), folds)     # 채권 한 곳만 쓴 글은 단독 절로 간다
        self.shows(self.frame, "통화정책 / 국내 금통위 의사록 · 소수의견 · 국고채 금리", "수급 / 국내 WGBI · 국고채 금리",
                   "AI 회사채 발행 12조원", "애널 2 · 개인 2")

    def test_tomorrow_wire_solo_and_context_rows(self):
        self.shows(self.frame, "10-09(금) 21:30 미 PPI", "B급 일정표", "10-12(월) 국고채 입찰 · 3년 · 2.4조원", "국고채 입찰 일정",
                   "가상 개인 wire1 7건 중 5건", "08:01 미 PPI · 부합 0.2%", "외국인 국채선물 · 순매수 4,732계약",
                   "줄 없이 건수만: 가상 개인 wire2 1건", "가상 개인 pers6 2건 중 1건", "국고채 발행계획 12.5조원",
                   "가상 애널 ctx1")
        self.assertIn("https://t.me/fxwire1/90012", posts(self.frame))
        self.assertNotIn("https://t.me/fxwire1/90017", posts(self.frame))      # 채널당 다섯 줄까지(자료가 그렇게 온다)
        self.assertIn("https://t.me/fxctx1/4100", posts(self.frame))

    def test_every_link_is_a_listed_post_a_listed_channel_an_official_page_or_the_takedown_form(self):
        handles = {c["handle"] for c in fx("sources")["channels"]}
        outs = outside(self.frame)
        self.assertGreater(len(posts(self.frame)), 20)
        for a in outs:
            m = POST.match(a["href"]) or CHANNEL.match(a["href"])
            self.assertTrue(a["href"] == TAKEDOWN or a["href"] in R.OFFICIAL_URLS or (m and m.group(1) in handles), a["href"])
            self.assertEqual((a["target"], a["rel"]), ("_blank", "noopener noreferrer"), a["href"])
            self.assertTrue(a["text"].strip(), a["href"])
        self.assertEqual(sum(a["href"] == TAKEDOWN for a in outs), 1)
        self.assertEqual({CHANNEL.match(a["href"]).group(1) for a in outs if CHANNEL.match(a["href"])}, handles)
        for a in self.frame["links"]:
            if a not in outs:
                self.assertRegex(a["href"], r"^#evening(?:/\d{4}-\d{2}-\d{2})?$")
                self.assertIsNone(a["target"])

    def test_source_note_says_how_and_where_to_ask(self):
        self.shows(self.frame, "웹 미리보기를 평일 저녁에 한 번", "채널 글의 문장은 싣지 않습니다", "규칙 판정과 무관한 참고 자료",
                   "채널 운영자가 요청하면 그 채널을 목록에서 내립니다", "채권 5곳", "애널 8곳", "개인 12곳", "가상 개인 off1 제외")

    def test_nothing_planted_is_in_the_fixture_screen(self):
        self.assertEqual(F.leaks(blob(self.frame)), [])

    def test_numbers_flash_once_unless_motion_is_off(self):
        on, off = (play(site(), {"now": THU_EVENING, "view": "evening", "calm": calm})[0] for calm in (False, True))
        self.assertTrue(any(a.startswith("class=") and "eve-fresh" in a for a in on["attrs"]))
        self.assertFalse(any("eve-fresh" in a for a in off["attrs"]))


@unittest.skipUnless(NODE, "node가 없다")
class DirtyDataTest(Screen):
    def test_sentences_tags_and_foreign_addresses_in_the_data_are_not_drawn(self):
        d, src = fx("digest"), fx("sources")
        d["must"][0]["terms"] = [C3, C4, C5, C7, "미 CPI"]
        d["must"][0]["why"] = [C1, "채권 채널 3곳"]
        d["must"][0]["nums"][0]["v"] = "3.1% " + C1
        d["must"][0]["cell"] = {"factor": C4, "region": "글로벌"}
        d["must"][1]["links"][0]["url"] = "https://" + C7
        d["must"][1]["links"][1]["url"] = "javascript:alert(1)"
        d["must"][2]["links"] = [{"ch": "fxbond2", "url": "https://t.me/notlisted1/5", "at": F.NOW, "fwd": False},
                                 {"ch": "fxoff1", "url": "https://t.me/fxoff1/9", "at": F.NOW, "fwd": False}]
        d["notes"] = [C3, R.phrase("note_rerun")]
        d["head"]["top_terms"] = [C6, "미 CPI"]
        d["head"]["dir"] = C1
        d["tomorrow"][0]["term"] = C3
        d["tomorrow"][1]["detail"] = [C4, "3년"]
        d["wire"]["rows"][0]["term"] = C5
        d["context"][0] = {"ch": "fxctx1", "url": "https://t.me/fxctx1/4100?" + C7, "at": F.NOW}
        d["rest"][0]["cell"] = C3
        src["channels"][0]["label"] = C4
        frame = draw(site(digest=d, sources=src))
        self.assertEqual(F.leaks(blob(frame)), [])
        self.assertNotRegex(blob(frame), r"javascript:|notlisted1|fxoff1/9|canary")
        self.shows(frame, "꼭 2건", "표시하지 않은 항목 1건", "분류 보류", "미 CPI", "채권 채널 3곳", "같은 판을 다시 계산했습니다",
                   "fxbond1 10-07 21:41", "10-12(월) 국고채 입찰 · 3년")       # 라벨이 이상하면 채널 이름으로, 나머지는 그대로
        self.assertEqual([u for u in posts(frame) if "/fxbond4/" in u or "/fxbond5/" in u], [])
        self.assertIn("https://t.me/fxanal3/58", posts(frame))                  # 깨진 링크 둘만 빠지고 남은 링크로 항목은 선다

    def test_a_broken_field_takes_down_only_its_own_section(self):
        junk = [None, 7, "깨짐", [], [None, 3, "x", {}], {"rows": 5, "channels": "x", "items": 3}]
        keys = ["window", "collected_at", "funnel", "sources", "head", "notes", "must", "rest", "wire", "solo", "context", "tomorrow"]
        steps, now = [], S.parse_iso(THU_EVENING)
        for key in keys:
            for bad in junk:
                now += datetime.timedelta(minutes=11)                           # 11분 뒤 다시 들어오면 자료를 다시 읽는다
                steps += [{"put": {"data/digest.json": {**fx("digest"), key: bad}}}, {"now": S.iso(now), "view": "all"},
                          {"now": S.iso(now), "view": "evening"}]
        frames = [f for f in play(site(), {"now": THU_EVENING, "view": "evening"}, *steps)[3::3]]
        self.assertEqual(len(frames), len(keys) * len(junk))
        for i, frame in enumerate(frames):
            key = keys[i // len(junk)]
            self.shows(frame, "저녁판 2026-10-08(목)")
            self.assertIn("출처와 수집 방식", frame["folds"], key)
            self.assertNotIn("[object", frame["text"], key)
            self.assertNotIn("undefined", frame["text"], key)
            self.assertNotIn("NaN", frame["text"], key)
            if key != "must":
                self.shows(frame, "꼭 3건", "미 CPI · 상회 · 3.1%")
            if key not in ("rest", "must"):
                self.shows(frame, "채권 채널 단독 글")

    def test_broken_items_are_skipped_one_by_one(self):
        d = fx("digest")
        good = d["must"][0]
        d["must"] = [None, 5, {"id": "20261008-fxbond1-501"}, {**good, "id": "순위-1"}, {**good, "links": "없음"}, good]
        d["rest"][0]["items"] = [None, "x", *d["rest"][0]["items"]]
        d["wire"]["rows"] = [None, {"ch": "fxwire1"}, *d["wire"]["rows"]]
        d["tomorrow"] = [None, {"date": "2026-02-30", "term": "미 PPI"}, *d["tomorrow"]]
        frame = draw(site(digest=d))
        self.shows(frame, "꼭 1건", "표시하지 않은 항목 5건", "미 CPI · 상회 · 3.1%", "AI 회사채 발행 12조원", "7건 중 5건",
                   "10-09(금) 21:30 미 PPI")
        self.lacks(frame, "02-30")

    def test_other_files_may_be_broken_too(self):
        junk = ([1, 2], "깨짐", 7, {"schema": 1, "channels": 5, "editions": "x", "expect": 3, "hide_ids": 1})
        cases = [(name, bad) for name in ("index", "status", "sources", "overrides") for bad in junk]
        *frames, nothing = draws(*[site(**{name: bad}) for name, bad in cases], {k: [1, 2] for k in site()})
        for (name, _), frame in zip(cases, frames):
            self.shows(frame, "저녁판 2026-10-08(목)")
            self.assertIn("출처와 수집 방식", frame["folds"], name)
        self.shows(nothing, "아직 판이 없습니다")

    def test_an_edition_from_another_schema_is_not_drawn(self):
        odd = ({**fx("digest"), "schema": 2}, {**fx("digest"), "date": "2026-13-45"}, {**fx("digest"), "date": None})
        for frame in draws(*[site(digest=bad) for bad in odd]):
            self.shows(frame, "아직 판이 없습니다")
            self.assertEqual(posts(frame), [])


# ---------- 그려 보기: 상태 ----------


@unittest.skipUnless(NODE, "node가 없다")
class StateTest(Screen):
    def test_loading_line_first(self):
        frame = draw(site())
        self.assertEqual(flat(frame["early"]), flat("저녁판을 불러오는 중…"))    # 자료가 오기 전
        self.lacks(frame, "불러오는 중")

    def test_a_failed_load_is_said_and_tried_again(self):
        _, broken, _, healed = play(site(), {"reader": False}, {"now": THU_EVENING, "view": "evening"}, {"reader": True},
                                    {"now": "2026-10-08T19:01:00+09:00", "tick": True})
        self.shows(broken, "저녁판 자료를 불러오지 못했습니다")
        self.assertEqual(posts(broken), [])
        self.shows(healed, "저녁판 2026-10-08(목)", "꼭 3건")                     # 1분 뒤 다시 읽는다
        self.lacks(healed, "불러오지 못했습니다")

    def test_a_missing_place_to_draw_does_not_throw_into_the_page(self):
        # 페이지 뼈대가 바뀌어 그릴 자리가 없어도 setView는 예외를 흘리지 않는다(흘리면 applyView가 멈춰 다른 화면도 안 바뀐다)
        _, lost, _, _, back = play(site(), {"wrap": False}, {"now": THU_EVENING, "view": "evening"}, {"wrap": True},
                                   {"now": THU_EVENING, "view": "all"}, {"now": THU_EVENING, "view": "evening"})
        self.assertEqual(lost["text"], "")
        self.shows(back, "저녁판 2026-10-08(목)", "꼭 3건")

    def test_no_edition_yet(self):
        frame, listed = draws({}, site(digest=None))
        self.shows(frame, "아직 판이 없습니다")
        self.assertEqual(posts(frame), [])
        self.assertIn("출처와 수집 방식", frame["folds"])                       # 수집 방식과 삭제 창구는 판이 없어도 보인다
        self.assertEqual([a["href"] for a in outside(frame)], [TAKEDOWN])
        self.shows(listed, "아직 판이 없습니다", "가상 채권 bond1 원천")          # 판이 없어도 출처 목록은 보인다
        self.assertEqual(posts(listed), [])

    def test_todays_edition_is_pending_then_late(self):
        st = {**fx("status"), "expect": {"run_kst": "17:41", "late_kst": "23:30"}}
        fresh, pending, late, weekend, patient = draws((site(), THU_EVENING), (site(), FRI_MORNING), (site(), FRI_NIGHT),
                                                       (site(), "2026-10-10T12:00:00+09:00"), (site(status=st), FRI_NIGHT))
        self.lacks(fresh, "판은 평일", "판이 아직 없습니다")
        self.shows(pending, "오늘 10-09(금) 판은 평일 17:41(KST) 수집 뒤에 나옵니다. 아래는 10-08(목) 판입니다.")
        self.lacks(pending, "판이 아직 없습니다")
        self.shows(late, "10-09(금) 판이 아직 없습니다", "22:41까지 반영되지 않았습니다. 아래는 10-08(목) 판입니다.", "꼭 3건",
                   "저장소 Actions의 evening 실행 기록에서 원인을 볼 수 있고, 수동 실행으로 다시 돌릴 수 있습니다")
        self.lacks(pending, "수동 실행")                                         # 아직 늦지 않았으면 할 일이 없다
        self.shows(weekend, "10-09(금) 판이 아직 없습니다")                      # 주말에도 금요일 판이 없으면 알린다
        self.lacks(patient, "판이 아직 없습니다")                                # 늦었다고 보는 시각은 상태 파일을 따른다

    def test_an_open_screen_judges_again_as_time_passes(self):
        newer = PV.shift(fx("digest"), 1)
        frames = play(site(), {"now": THU_EVENING, "view": "evening"}, {"now": "2026-10-08T19:05:00+09:00", "tick": True},
                      {"now": FRI_NIGHT, "tick": True}, {"put": {"data/digest.json": newer}},
                      {"now": "2026-10-09T23:00:00+09:00", "tick": True}, {"now": "2026-10-09T23:01:00+09:00", "view": "all"},
                      {"now": "2026-10-10T23:30:00+09:00", "tick": True})
        first, soon, night, _, after, away, later = frames
        self.assertEqual(len(soon["requested"]), len(first["requested"]))        # 5분 뒤 — 다시 읽지 않는다
        self.lacks(soon, "판이 아직 없습니다")
        self.shows(night, "10-09(금) 판이 아직 없습니다", "저녁판 2026-10-08(목)")   # 다시 그리지 않아도 알림은 바뀐다
        self.assertGreater(len(night["requested"]), len(first["requested"]))     # 10분이 넘었으면 다시 읽는다
        self.shows(after, "저녁판 2026-10-09(금)")
        self.lacks(after, "판이 아직 없습니다")
        self.assertEqual(len(later["requested"]), len(away["requested"]))        # 다른 화면에 있을 때는 읽지 않는다
        for path in later["requested"]:
            self.assertRegex(path, REQUEST)

    def test_a_failed_reread_keeps_what_is_on_screen(self):
        gone = {"put": {k: None for k in site()}}
        first, _, later = play(site(), {"now": THU_EVENING, "view": "evening"}, gone,
                               {"now": "2026-10-08T19:30:00+09:00", "tick": True})
        self.assertGreater(len(later["requested"]), len(first["requested"]))
        self.shows(later, "저녁판 2026-10-08(목)", "꼭 3건")
        self.assertEqual(posts(later), posts(first))

    def test_short_collection(self):
        docs = PV.build("short", datetime.date(2026, 10, 8))
        frame = draw(named(docs))
        self.shows(frame, "수집 부족 — 꼭 볼 것을 비웠습니다", "채권 채널 3곳 미만이거나 전체 16곳 미만", "24채널 중 13 읽음", "꼭 볼 것")
        self.lacks(frame, "꼭 3건", "기준을 넘은 묶음이 없습니다")
        self.assertEqual(flat(frame["text"]).count(flat("수집 부족 — 꼭 볼 것을 비웠습니다")), 2)   # 알림 한 번, 꼭 볼 것 자리에 한 번

    def test_some_channels_failed(self):
        docs = PV.build("partial", datetime.date(2026, 10, 8))
        frame = draw(named(docs))
        self.shows(frame, "채널 일부를 읽지 못했습니다 — 24채널 중 23 읽음", "읽지 못한 곳: 가상 채권 bond3(수신 실패)", "꼭 3건",
                   "가상 채권 bond3 원천 · 이번 판에서 읽지 못함(수신 실패)", "가상 채권 bond1 원천 · 창 안 글 2건")

    def test_fewer_and_none(self):
        day = datetime.date(2026, 10, 8)
        fewer, none = draws(named(PV.build("fewer", day)), named(PV.build("none", day)))
        self.shows(fewer, "꼭 2건", "오늘은 2건 — 기준을 넘은 묶음만 싣습니다")
        self.shows(none, "꼭 볼 것", "오늘은 기준을 넘은 묶음이 없습니다", "나머지", "다가오는 일정",
                   "아래 '채권 채널 단독 글'과 '나머지'에서 채널들이 쓴 낱말을 볼 수 있습니다")     # 0건인 날 어디를 볼지 말한다
        self.assertIn("꼭 볼 것", none["heads"])
        self.assertNotIn("꼭 0건", none["heads"])                                  # 0건은 제목이 아니라 이유 문구로 말한다

    def test_withdrawn_edition_and_withdraw_switch(self):
        blank = S.blank_digest(S.parse_iso(F.NOW))
        off = F.overrides(withdraw=True)
        gone, switched, past = draws(site(digest=blank), site(overrides=off),
                                     (site(overrides=off, past={"2026-10-07": PV.shift(fx("digest"), -1)}), THU_EVENING, "2026-10-07"))
        for frame in (gone, switched):
            self.shows(frame, "이 판은 내렸습니다", "저녁판 2026-10-08(목)")
            self.lacks(frame, "꼭 3건", "미 CPI", "읽은 41건", "다가오는 일정")
            self.assertEqual(posts(frame), [])
            self.assertEqual([a for a in frame["links"] if a["href"].startswith("#evening/")], [])
        self.shows(past, "이 판은 내렸습니다", "저녁판 2026-10-07(수)")
        self.assertEqual(posts(past), [])                                        # 내리기는 지난 판도 가린다

    def test_unreadable_hide_list_hides_the_items(self):
        odd = (None, [1], {"schema": 1, "withdraw": "false", "hide_ids": [], "hide_channels": []}, {"schema": 1},
               {"schema": 2, "withdraw": False, "hide_ids": [], "hide_channels": []})
        for frame in draws(*[site(overrides=bad) for bad in odd]):
            self.shows(frame, "숨김 목록(digest_overrides.json)을 읽지 못해 이 판의 항목을 가렸습니다")
            self.assertEqual(posts(frame), [])
            self.lacks(frame, "미 CPI")

    def test_hidden_items_and_channels(self):
        hidden = F.overrides(hide_ids=["20261008-fxbond4-640", "20261008-fxbond3-89"],
                             hide_channels=["fxpers2", "fxwire1", "fxbond2"])
        only = fx("digest")
        only["must"][2]["links"] = only["must"][2]["links"][:1]
        frame, fewer = draws(site(overrides=hidden), site(digest=only, overrides=hidden))
        self.shows(frame, "꼭 2건", "표시하지 않은 항목 1건", "미 CPI · 상회 · 3.1%")
        self.lacks(frame, "247.4%", "WGBI", "가상 개인 pers2", "가상 개인 wire1", "가상 채권 bond2")
        for url in posts(frame):
            self.assertNotRegex(url, r"/(?:fxpers2|fxwire1|fxbond2)/|/fxbond4/640$|/fxbond3/89$")
        self.assertNotRegex(blob(frame), r"t\.me/(?:fxpers2|fxwire1|fxbond2)\b")   # 채널 목록에서도 뺀다
        self.assertIn("https://t.me/fxanal5/318", posts(frame))                  # 채널 하나가 숨어도 남은 링크로 항목은 선다
        self.shows(fewer, "꼭 1건", "표시하지 않은 항목 2건")                     # 링크가 숨긴 채널 것뿐이면 항목째 뺀다

    def test_without_the_source_list_no_link_is_made(self):
        frame = draw(site(sources=None))
        self.shows(frame, "출처 목록(sources.json)을 읽지 못해 원문 링크를 걸지 않았습니다", "꼭 3건", "fxbond1 10-07 21:41",
                   "출처 목록을 읽지 못했습니다")
        self.assertEqual([a["href"] for a in outside(frame) if a["href"] not in R.OFFICIAL_URLS], [TAKEDOWN])   # 채널로 가는 링크는 없다

    def test_channels_off_the_list_get_no_link(self):
        src = fx("sources")
        src["channels"] = [c for c in src["channels"] if c["handle"] not in ("fxbond1", "fxwire1")]
        frame = draw(site(sources=src))
        self.assertEqual([u for u in posts(frame) if "/fxbond1/" in u or "/fxwire1/" in u], [])
        self.shows(frame, "꼭 3건")                                              # 목록에서 뺀 채널의 링크만 사라진다
        self.lacks(frame, "fxbond1", "fxwire1")

    def test_failed_run_is_told_apart_from_a_missing_one(self):
        st = {**PV.shift(fx("status"), 1), "ok": False, "reason": "broken", "published": False}
        old = {**fx("status"), "checked_at": "2026-10-07T18:04:00+09:00", "ok": False, "reason": "error"}
        streak = {**fx("status"), "ok": False, "reason": "empty_streak", "empty_streak": 3}
        frame, before, empty = draws((site(status=st), FRI_NIGHT), site(status=old), site(status=streak))
        self.shows(frame, "최근 저녁 실행(10-09 18:09): 채널 글의 형식이 바뀐 것으로 보여 판을 내지 않았습니다.",
                   "10-09(금) 판이 아직 없습니다", "저장소 Actions의 evening 실행 기록")
        self.lacks(before, "최근 저녁 실행")                                     # 이 판보다 앞선 실행의 실패는 알리지 않는다
        self.shows(empty, "꼭 볼 것이 없는 판이 여러 영업일 이어지고 있습니다")


@unittest.skipUnless(NODE, "node가 없다")
class PastEditionTest(Screen):
    def setUp(self):
        self.old = {**PV.shift(fx("digest"), -1), "must": PV.shift(fx("digest"), -1)["must"][:1]}
        self.files = site(past={"2026-10-07": self.old, "2026-10-08": fx("digest")})

    def test_turning_to_a_past_edition(self):
        latest, past, back = play(self.files, {"now": THU_EVENING, "view": "evening"},
                                  {"now": THU_EVENING, "view": "evening", "arg": "2026-10-07"}, {"now": THU_EVENING, "view": "evening"})
        nav = [(a["href"], flat(a["text"]), a["current"]) for a in latest["links"] if a["href"].startswith("#evening")]
        self.assertEqual(nav, [("#evening", flat("10-08(목) 꼭 3"), "page"), ("#evening/2026-10-07", flat("10-07(수) 꼭 1"), None)])
        self.assertIn("data/digest/2026-10-07.json", past["requested"])
        self.shows(past, "저녁판 2026-10-07(수)", "지난 판(10-07(수))을 보고 있습니다", "최신 판 보기", "꼭 1건")
        self.lacks(past, "판이 아직 없습니다")
        self.assertIn(("#evening/2026-10-07", "page"), [(a["href"], a["current"]) for a in past["links"]])
        self.assertIn("https://t.me/fxbond1/501", posts(past))
        self.shows(back, "저녁판 2026-10-08(목)", "꼭 3건")
        self.assertEqual(back["requested"].count("data/digest/2026-10-07.json"), 1)
        self.assertNotIn("data/digest/2026-10-08.json", back["requested"])       # 최신 판은 digest.json 하나로 본다

    def test_the_latest_date_in_the_address_is_the_latest_view(self):
        frame = draw(self.files, arg="2026-10-08")
        self.shows(frame, "저녁판 2026-10-08(목)")
        self.lacks(frame, "지난 판")
        self.assertNotIn("data/digest/2026-10-08.json", frame["requested"])

    def test_a_date_without_an_edition(self):
        frame, wrong = draws((self.files, THU_EVENING, "2026-10-06"),
                             (site(past={"2026-10-06": self.old}), THU_EVENING, "2026-10-06"))
        self.shows(frame, "10-06(화) 판이 없습니다", "보관 기간(35일)", "최신 판 보기")
        self.assertEqual(posts(frame), [])
        self.shows(wrong, "10-06(화) 판이 없습니다")                             # 파일 이름과 안의 날짜가 다르면 그 판이 아니다

    def test_a_strange_value_after_the_slash_is_not_requested(self):
        args = ("../../secret", "2026-13-45", "2026-02-30", "2026-10-07/x", "2026-10-07.json", "%2e%2e", "latest")
        for arg, frame in zip(args, draws(*[(self.files, THU_EVENING, arg) for arg in args])):
            self.shows(frame, "주소의 날짜를 읽을 수 없어 최신 판을 보여 줍니다", "저녁판 2026-10-08(목)")
            for path in frame["requested"]:
                self.assertRegex(path, REQUEST)
            self.assertFalse(any("digest/" in p for p in frame["requested"]), arg)

    def test_only_the_last_ten_editions_are_offered(self):
        day = datetime.date(2026, 10, 8)
        rows = [{**fx("index")["editions"][0], "date": (day - datetime.timedelta(days=i)).isoformat()} for i in range(14)]
        index = {**fx("index"), "editions": rows[::-1] + [None, {"date": "어제"}]}   # 순서가 뒤섞여 와도 최신순으로
        nav = [a["href"] for a in draw(site(index=index))["links"] if a["href"].startswith("#evening")]
        self.assertEqual(nav, ["#evening"] + [f"#evening/{r['date']}" for r in rows[1:10]])


if __name__ == "__main__":
    unittest.main()
