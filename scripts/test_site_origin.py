"""화면 폴더(site/) 전체의 같은 출처 검사 — 브라우저 없이 글자만 본다.
표준 라이브러리만 쓴다(node · 네트워크 불필요, Python 3.9에서도 돈다).

같은 주소 아래에 놓이는 파일은 브라우저 저장 공간을 함께 쓴다. 그래서 화면 하나가 아니라 폴더를 통째로 훑는다.
  나무       site/에는 EXT_OK의 확장자만 둔다
  금지 낱말   site/의 모든 파일에서 BANNED가 0번(주석은 떼고 센다). 스크립트는 그 문서와 같은 폴더의 것만 싣는다
  허용 표     study/ 밖 파일의 WATCHED 낱말 횟수가 ALLOW와 같다(표에 없는 파일 · 낱말은 0번)
  덫         study/ 밖 파일은 study 쪽 저장 이름을 모른다 · data/는 전부 .json · .jsonl 파일이 없다 ·
             site/study/가 있으면 그 폴더의 검사도 있다

실행:  python -X utf8 scripts/test_site_origin.py
       (아침 묶음과 push 전 훅이 돌린다. 저녁 묶음에는 scripts/evening/test_site_gate.py가 싣는다)
걸렸을 때:  뜻한 변화면 바로 아래의 표를 고친다. 실패 문구가 파일 · 낱말 · 횟수를 알려 준다.
"""
import os
import re
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(REPO, "site")
DATA = os.path.join(REPO, "data")

# ── 허용 표 ──────────────────────────────────────────────────────────────────────────
EXT_OK = (".html", ".js", ".css", ".webmanifest")         # site/에 둘 수 있는 확장자

BANNED = (                                                 # 어느 파일에서도 0번 — 아래 ALLOW로는 풀지 않는다
    "innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "DOMParser", "createContextualFragment",
    "setHTML", "srcdoc",
    "eval(", "new Function", "javascript:",
    'setAttribute("on', "setAttribute('on",
    "serviceWorker", "import(", "importScripts", "RTCPeerConnection", "window.open", "location.assign", "location.replace",
    'rel="dns-prefetch"', 'rel="prefetch"', 'rel="prerender"',
)

WATCHED = (                                                # study/ 밖 파일에서 세는 낱말 — 횟수가 ALLOW와 같아야 한다
    'rel="preconnect"', "<script>", "<script", "<base",                  # 미리 잇기 · 인라인 스크립트 · 스크립트 태그 · 기준 주소
    "fetch(", "XMLHttpRequest", "WebSocket", "EventSource", "sendBeacon", "new Image", "new Worker", "url(", "@import",
    "localStorage", "sessionStorage", "indexedDB", "document.cookie",    # 저장
    "location.", "navigator.", "postMessage", "createElement",           # 주소 · 기기 · 창 사이 · 요소 만들기
)

ALLOW = {                                                  # 파일(site/ 기준) → 낱말 → 허용 횟수. 없는 파일 · 낱말은 0번
    "index.html": {'rel="preconnect"': 2, "<script>": 2, "<script": 6, "fetch(": 1, "localStorage": 4, "location.": 2,
                   "createElement": 2},
    "charts.js": {"createElement": 2},
    "korea.js": {"createElement": 1},
}

HINT = "새 확장자 · 새 저장 이름 · 새 바깥 요청은 이 파일 맨 위 허용 표에 한 줄을 더한다"

STUDY = "study/"                    # 이 폴더의 능력 표는 scripts/test_study_site.py가 갖는다(여기서는 확장자와 금지 낱말만 본다)
STUDY_NAME = "macro-study"          # study 쪽 저장 이름의 머리
STUDY_TEST = "test_study_site.py"
GATE = "evening/test_site_gate.py"
SKIP_DIRS = (".git", ".work", "__pycache__")


def files_under(root):
    """root 아래 모든 파일 → 그 폴더 기준 경로("/"로 잇고 정렬). 없는 폴더면 빈 목록."""
    out = []
    for folder, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        rel = os.path.relpath(folder, root).replace(os.sep, "/")
        out += [n if rel == "." else rel + "/" + n for n in names]
    return sorted(out)


def read(root, name):
    with open(os.path.join(root, *name.split("/")), encoding="utf-8", errors="replace") as f:
        return f.read()


def planted(files):
    """지어낸 파일 몇 개를 담은 임시 폴더 — 검사가 심어 둔 것을 실제로 잡는지 볼 때 쓴다(with로 열면 폴더 경로를 준다)."""
    box = tempfile.TemporaryDirectory()
    for name, text in files.items():
        path = os.path.join(box.name, *name.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    return box


def odd_extensions(site):
    """site/ 아래에서 EXT_OK 밖의 확장자를 가진 파일."""
    return [n for n in files_under(site) if os.path.splitext(n)[1] not in EXT_OK]


class SiteTreeTest(unittest.TestCase):
    def test_the_walk_really_sees_the_folder(self):
        self.assertIn("index.html", files_under(SITE), "site/를 읽지 못했다 — 빈 폴더가 아래 검사를 통과하지 않게 한다")

    def test_only_page_files_live_in_site(self):
        self.assertEqual(odd_extensions(SITE), [], "site/에 허용 목록(EXT_OK) 밖의 파일이 있다 — " + HINT)

    def test_a_planted_odd_file_is_caught(self):
        files = {"a.html": "", "b.JS": "", "study/m.webmanifest": "{}", "img/a.png": "x", "notes.txt": "x", ".nojekyll": ""}
        with planted(files) as site:
            self.assertEqual(odd_extensions(site), [".nojekyll", "b.JS", "img/a.png", "notes.txt"])


JS_TOKEN = re.compile(                  # 문자열 셋 | 줄 주석 | 블록 주석 | 정규식 리터럴(앞 글자로 알아본다)
    r'"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|`(?:\\.|[^`\\])*`|//[^\n]*|/\*.*?\*/'
    r'|(?:[=(,:!&|?\[>]|\breturn)\s*/(?![/*])(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^/\\\n\[])+/', re.S)
CSS_NOTE = re.compile(r"/\*.*?\*/", re.S)
HTML_NOTE = re.compile(r"<!--.*?-->", re.S)
INLINE = re.compile(r"(<script\b[^>]*>)(.*?)(</script\s*>)", re.S | re.I)
SRC = re.compile(r"<script\b[^>]*?\bsrc\s*=\s*[\"']?([^\"'\s>]*)", re.I)


def js_code(text):
    """주석을 뗀 스크립트. 문자열과 정규식은 그대로 둔다 — 그 안의 //(주소)와 /*("image/*")는 주석이 아니다."""
    return JS_TOKEN.sub(lambda m: "" if m.group(0)[:2] in ("//", "/*") else m.group(0), text)


def code_only(name, text):
    """주석을 뗀 글자 — 설명 글에 나온 낱말로 검사가 걸리지 않게. .html은 <!-- -->와 인라인 스크립트 안의 주석만 뗀다."""
    ext = os.path.splitext(name)[1]
    if ext == ".html":
        return INLINE.sub(lambda m: m.group(1) + js_code(m.group(2)) + m.group(3), HTML_NOTE.sub("", text))
    if ext == ".css":
        return CSS_NOTE.sub("", text)
    return js_code(text) if ext == ".js" else text


def banned_hits(site):
    """[(파일, 낱말)] — site/의 모든 파일(study/ 포함)에서 주석을 떼고 찾은 금지 낱말."""
    return [(n, w) for n in files_under(site) for w in BANNED if w in code_only(n, read(site, n))]


def foreign_scripts(site):
    """[(파일, 주소)] — .html이 싣는 스크립트 가운데 그 문서의 폴더 밖의 것(주소에 ':'이 있거나 '/'로 시작하거나 '..'을 지난다)."""
    out = []
    for n in files_under(site):
        if n.endswith(".html"):
            for src in SRC.findall(code_only(n, read(site, n))):
                if ":" in src or src.startswith("/") or ".." in src.split("/"):
                    out.append((n, src))
    return out


class SiteWordsTest(unittest.TestCase):
    def test_no_banned_word_in_any_site_file(self):
        self.assertEqual(banned_hits(SITE), [], "금지 낱말(BANNED)이 화면 파일에 있다 — 글자는 텍스트로만 넣는다. 허용 표로는 풀지 않는다")

    def test_scripts_come_from_this_folder_only(self):
        self.assertEqual(foreign_scripts(SITE), [], "문서의 폴더 밖 스크립트를 싣는다 — 스크립트는 그 문서와 같은 폴더의 파일만 싣는다")

    def test_comments_are_skipped_but_code_is_not(self):
        files = {
            "a.js": '// innerHTML 을 쓰지 않는다\n/* eval( 도 */\nconst u = "https://example.org/a"; // DOMParser\n'
                    'const QUOTES = /["\'`]/; // document.write 설명 — 정규식 안의 따옴표가 문자열을 열지 않는다\n'
                    "if (/^https:\\/\\//.test(u)) node.outerHTML = t; // 정규식이 //로 끝나도 뒤의 코드는 남는다\n",
            "b.html": '<!-- srcdoc -->\n<p>// <a href="javascript:void 0">x</a></p>\n<script>\n// document.write\n'
                      'const kind = "image/*"; box.insertAdjacentHTML("x", kind); /* 끝 */\n</script>\n',
            "study/c.js": "box.innerHTML = 1;\n",
            "d.css": "/* url( */\na { color: red; }\n",
        }
        with planted(files) as site:
            self.assertEqual(banned_hits(site), [("a.js", "outerHTML"), ("b.html", "insertAdjacentHTML"),
                                                 ("b.html", "javascript:"), ("study/c.js", "innerHTML")])
            self.assertIn('"https://example.org/a"', code_only("a.js", read(site, "a.js")))     # 문자열 안의 //는 주석이 아니다
            self.assertNotIn("url(", code_only("d.css", read(site, "d.css")))

    def test_a_planted_outside_script_is_caught(self):
        page = ('<script src="ok.js?v=1"></script><script src=bare.js></script>\n'
                '<script src="https://cdn.example/x.js"></script><script src="//cdn.example/y.js"></script>\n'
                '<script defer src="/other/z.js"></script><script src="../up.js"></script>\n')
        with planted({"index.html": page, "study/index.html": '<script src="../charts.js"></script>'}) as site:
            self.assertEqual(foreign_scripts(site), [
                ("index.html", "https://cdn.example/x.js"), ("index.html", "//cdn.example/y.js"),
                ("index.html", "/other/z.js"), ("index.html", "../up.js"), ("study/index.html", "../charts.js")])


def watched_counts(site):
    """{파일: {낱말: 횟수}} — study/ 밖 파일에서 주석을 떼고 센 WATCHED 낱말(0번은 싣지 않는다)."""
    out = {}
    for n in files_under(site):
        if not n.startswith(STUDY):
            code = code_only(n, read(site, n))
            row = {w: code.count(w) for w in WATCHED if w in code}
            if row:
                out[n] = row
    return out


def allow_gaps(site, allow):
    """허용 표와 실제가 다른 곳 → 문구 목록(파일 · 낱말 · 허용 횟수 · 지금 횟수). 늘어도 줄어도 걸린다 — 표가 묵지 않게."""
    seen, out = watched_counts(site), []
    for n in sorted(set(seen) | set(allow)):
        for w in WATCHED:
            want, got = allow.get(n, {}).get(w, 0), seen.get(n, {}).get(w, 0)
            if want != got:
                out.append("site/%s: `%s` 허용 %d번, 지금 %d번" % (n, w, want, got))
    return out


class SiteAllowTest(unittest.TestCase):
    def test_watched_words_match_the_table(self):
        self.assertEqual(allow_gaps(SITE, ALLOW), [], "허용 표(ALLOW)와 다르다 — 뜻한 변화면 숫자를 고친다. " + HINT)

    def test_table_rows_are_alive(self):
        for name, row in ALLOW.items():
            self.assertFalse(name.startswith(STUDY), name + ": study/ 아래 파일의 표는 scripts/" + STUDY_TEST + "가 갖는다")
            for word, times in row.items():
                self.assertIn(word, WATCHED, name + ": WATCHED에 없는 낱말은 세지 않는다 — 표에서 지우거나 WATCHED에 더한다")
                self.assertGreater(times, 0, name + " · " + word + ": 0번이면 줄을 지운다")

    def test_a_planted_change_is_caught(self):
        files = {"main.js": 'fetch("a.json"); fetch("b.json"); // fetch( 설명\n', "new.js": 'localStorage.getItem("k");\n',
                 "study/s.js": "localStorage.x; fetch(1);\n", "calm.css": "a { color: red; }\n"}
        with planted(files) as site:
            self.assertEqual(watched_counts(site), {"main.js": {"fetch(": 2}, "new.js": {"localStorage": 1}})
            self.assertEqual(allow_gaps(site, {"main.js": {"fetch(": 1}, "old.js": {"createElement": 1}}), [
                "site/main.js: `fetch(` 허용 1번, 지금 2번", "site/new.js: `localStorage` 허용 0번, 지금 1번",
                "site/old.js: `createElement` 허용 1번, 지금 0번"])
            self.assertEqual(allow_gaps(site, {"main.js": {"fetch(": 2}, "new.js": {"localStorage": 1}}), [])


def name_leaks(site):
    """study/ 밖 파일 가운데 study 쪽 저장 이름의 머리를 아는 것(주석까지 본다)."""
    return [n for n in files_under(site) if not n.startswith(STUDY) and STUDY_NAME in read(site, n)]


def not_json(data):
    return [n for n in files_under(data) if not n.endswith(".json")]


def line_logs(repo):
    return [n for n in files_under(repo) if n.lower().endswith(".jsonl")]


def study_gaps(repo):
    """site/study/가 있는데 그 폴더의 검사가 빠진 곳 → 문구 목록. 폴더가 없으면 빈 목록."""
    scripts, out = os.path.join(repo, "scripts"), []
    if not os.path.isdir(os.path.join(repo, "site", "study")):
        return out
    if not os.path.isfile(os.path.join(scripts, STUDY_TEST)):
        out.append("scripts/" + STUDY_TEST + " 가 없다 — site/study/의 능력 표와 정책 검사는 그 파일이 갖는다")
    gate = os.path.join(scripts, *GATE.split("/"))
    if not os.path.isfile(gate) or "from test_study_site import" not in read(scripts, GATE):
        out.append("scripts/" + GATE + " 가 test_study_site를 싣지 않는다 — 저녁 배포도 같은 검사를 지나야 한다")
    return out


class SiteTrapTest(unittest.TestCase):
    def test_study_storage_name_stays_inside_study(self):
        self.assertEqual(name_leaks(SITE), [], "study/ 밖 파일이 study 쪽 저장 이름(" + STUDY_NAME + ")을 안다 — "
                                               "그 저장 공간은 site/study/ 안에서만 만진다")

    def test_data_folder_is_json_only(self):
        self.assertTrue(files_under(DATA), "data/를 읽지 못했다")
        self.assertEqual(not_json(DATA), [], "data/에 .json이 아닌 파일이 있다 — data/에는 화면이 읽는 JSON만 둔다")

    def test_no_line_log_file_in_the_repository(self):
        self.assertEqual(line_logs(REPO), [], "저장소에 .jsonl 파일이 있다 — 줄 단위 기록 파일은 이 저장소에 두지 않는다")

    def test_study_folder_brings_its_own_checks(self):
        self.assertEqual(study_gaps(REPO), [], "site/study/의 검사가 빠졌다")

    def test_planted_traps_spring(self):
        files = {"site/index.html": "<p>x</p>", "site/a.js": "// 설명에 적어도 걸린다: macro-study.key\n",
                 "site/study/store.js": 'const P = "macro-study.";\n', "data/a.json": "{}", "data/digest/b.txt": "x",
                 "notes/2026-10.jsonl": "{}\n", ".work/cache.jsonl": "{}\n", "scripts/evening/test_site_gate.py": "import os\n"}
        with planted(files) as repo:
            self.assertEqual(name_leaks(os.path.join(repo, "site")), ["a.js"])
            self.assertEqual(not_json(os.path.join(repo, "data")), ["digest/b.txt"])
            self.assertEqual(line_logs(repo), ["notes/2026-10.jsonl"])                      # .work/는 보지 않는다
            self.assertEqual(len(study_gaps(repo)), 2)
            for name, text in (("scripts/" + STUDY_TEST, ""), ("scripts/" + GATE, "from test_study_site import *\n")):
                with open(os.path.join(repo, *name.split("/")), "w", encoding="utf-8") as f:
                    f.write(text)
            self.assertEqual(study_gaps(repo), [])


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):                 # push 전 훅은 -X utf8 없이 부른다 — 실패 문구의 한글이 깨지지 않게
        stream.reconfigure(encoding="utf-8", errors="replace")
    unittest.main()
