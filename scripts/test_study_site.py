"""공부 화면(site/study/)의 정적 검사와 node 묶음 실행 — 브라우저 없이 글자만 본다. 표준 라이브러리만 쓴다.
node 묶음(scripts/test_study_*.cjs)은 여기서 불러 돌린다(워크플로에 줄을 더하지 않는다).

  모양    색 값은 :root에만 · 움직임 없음 · 입력 글자 16px 이상 · 누르는 곳 48px 이상
  쪽      뼈대 문서가 약속한 글자와 같다: 정책 meta의 자리, 머리 줄, 스크립트 차례와 판 글자, 뼈대 id 다섯, 매니페스트
  낱말    금지 낱말, 능력 표(능력마다 파일 하나), 저장 이름, 바깥 주소, 모듈의 꼴
  크기    파일 800줄 미만 · 함수 50줄 이하
  node    문법 검사와 묶음 실행(CI에서 node가 없으면 건너뛰지 않고 실패한다)

실행:  python -X utf8 scripts/test_study_site.py
       (아침 묶음이 줍는다. 저녁 묶음에는 scripts/evening/test_site_gate.py가 싣는다)
걸렸을 때:  파일을 더했으면 SCRIPTS · SUITES · CAPS에 줄을 더한다. 실패 문구가 파일 · 낱말을 알려 준다.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDY = os.path.join(REPO, "site", "study")


def read(*parts):
    """저장소 뿌리 기준 파일의 글자(줄 끝은 \\n으로 읽는다 — 작업 폴더가 CRLF여도 같다)."""
    with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
        return f.read()


def study(name):
    return read("site", "study", name)


# ── 모양 ────────────────────────────────────────────────────────────────────────────
COLORS = {"--black": "#000", "--panel": "#0a0a0a", "--bar": "#171717", "--rule": "#2c2c2c", "--amber": "#ff9e1b", "--ink": "#e9e6df",
          "--dim": "#8f8f8f", "--blue": "#5ab1ff", "--key": "#f6d200", "--go": "#36d07f", "--alert": "#ff5449", "--alert-bg": "#2a0907"}
CLASSES = ("st-btn", "st-btn-big", "st-input", "st-secret", "st-row", "st-warn", "st-amber", "st-red", "st-dim", "st-status",
           "st-strip", "st-cell", "st-fold", "st-group", "sr")
CSS_BANNED = ("animation", "transition", "@keyframes", "@import", "@media", "url(", "100vh", "fixed", "http")
TOUCH = ("button, .st-btn", 'input[type="text"], .st-input', "summary", "label", "audio", "#st-nav a", "#st-fallback a")   # 누르는 곳
TYPED = ('input[type="text"], .st-input',)                              # 적는 곳
FOCUS = "a:focus-visible, button:focus-visible, summary:focus-visible, input:focus-visible, audio:focus-visible"
FLOOR = "#8a8a8a"                                                       # 글자색은 이보다 어둡게 쓰지 않는다
BRIGHT = ("--key", "--amber", "--go", "--ink")                          # 이 바탕 위에서만 검정 글자를 쓴다


def css_rules(text):
    """[(선택자, {속성: 값})] — 주석을 떼고 읽는다. 겹친 블록(@media 등)은 쓰지 않는다."""
    plain = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    rules = []
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", plain):
        pairs = [d.split(":", 1) for d in body.split(";") if ":" in d]
        rules.append((" ".join(selector.split()), dict((k.strip(), v.strip()) for k, v in pairs)))
    return rules


def font_px(decls):
    """규칙이 정한 글자 크기(px). font-size가 없으면 font 줄임 꼴에서 읽고, 둘 다 없으면 None."""
    found = re.search(r"(\d+)px", decls.get("font-size", "") or decls.get("font", ""))
    return int(found.group(1)) if found else None


def luminance(color):
    """#rgb · #rrggbb의 밝기(0~1)."""
    h = color.lstrip("#")
    h = "".join(c * 2 for c in h) if len(h) == 3 else h
    parts = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [p / 12.92 if p <= 0.03928 else ((p + 0.055) / 1.055) ** 2.4 for p in parts]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def dark_text(rules, root):
    """글자색이 FLOOR보다 어두운 곳. 검정 글자는 밝은 바탕(BRIGHT) 위에서만 쓴다."""
    out = []
    for selector, decls in rules:
        var = re.match(r"var\((--[\w-]+)\)$", decls.get("color", ""))
        if "color" in decls and not var:
            out.append("글자색은 변수로만 쓴다: " + selector)
        elif var and luminance(root.get(var.group(1), "#000")) < luminance(FLOOR):
            back = re.match(r"var\((--[\w-]+)\)$", decls.get("background", ""))
            if not (back and back.group(1) in BRIGHT):
                out.append("글자색이 %s보다 어둡다: %s" % (FLOOR, selector))
    return out


def css_gaps(text):
    """모양 파일이 약속과 다른 곳 → 문구 목록."""
    rules, out = css_rules(text), []
    code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    by = dict(rules)
    root = by.get(":root", {})
    if dict((k, v) for k, v in root.items() if k in COLORS or re.search(r"#|rgb|hsl", v)) != COLORS:
        out.append(":root의 색 변수 12개가 약속과 다르다")
    tinted = [(s, v) for s, d in rules if s != ":root" for v in d.values() if re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", v)]
    out += ["색 값은 :root에만 적는다: %s { %s }" % pair for pair in tinted]
    out += ["쓰지 않는 글자: " + w for w in CSS_BANNED if w in code]
    classes = sorted(set(re.findall(r"\.(-?[A-Za-z_][\w-]*)", " ".join(s for s, d in rules))))
    if classes != sorted(CLASSES):
        out.append("클래스 이름이 약속과 다르다: %r" % sorted(set(classes) ^ set(CLASSES)))
    low = [s for s in TOUCH if int((re.findall(r"\d+", by.get(s, {}).get("min-height", "")) or ["0"])[0]) < 48]
    out += ["누르는 곳은 48px 이상: " + s for s in low]
    out += ["입력 글자는 16px 이상: " + s for s in TYPED if (font_px(by.get(s, {})) or 0) < 16]
    out += ["글자가 너무 작다: " + s for s, d in rules if font_px(d) is not None and font_px(d) < 14]
    out += ["있어야 하는 규칙: " + s for s in ("[hidden]", FOCUS) if s not in by]
    return out + dark_text(rules, root)


class StudyCssTest(unittest.TestCase):
    def test_style_file_keeps_the_agreement(self):
        self.assertEqual(css_gaps(study("study.css")), [])

    def test_root_holds_twelve_colors_and_two_fonts(self):
        rules = css_rules(study("study.css"))
        root = dict(rules).get(":root", {})
        self.assertEqual(dict((k, v) for k, v in root.items() if k in COLORS), COLORS)
        self.assertEqual(sorted(k for k in root if k not in COLORS), ["--f-mono", "--f-text", "color-scheme"])
        self.assertEqual(len([s for s, d in rules if s == ":root"]), 1, ":root 블록은 하나다")

    def test_focus_ring_and_hidden_are_restated(self):
        by = dict(css_rules(study("study.css")))
        self.assertEqual(by["[hidden]"], {"display": "none !important"})
        self.assertEqual(by[FOCUS], {"outline": "2px solid var(--key)", "outline-offset": "2px"})

    def test_planted_css_faults_are_caught(self):
        css = study("study.css")
        planted = (css + ".st-new { color: var(--ink); }\n", css + "p { color: #777; }\n", css + "p { color: var(--rule); }\n",
                   css + "p { transition: none; }\n", css + "#st-nav { position: fixed; }\n", css + "p { height: 100vh; }\n",
                   css.replace("min-height: 48px; margin: 6px 6px", "min-height: 44px; margin: 6px 6px"), css.replace("font: 17px/1.4", "font: 15px/1.4"),
                   css.replace("--dim: #8f8f8f", "--dim: #777"), css.replace("[hidden] { display: none !important; }\n", ""),
                   css + "@media (max-width: 400px) { p { margin: 0; } }\n", css + "small { font-size: 11px; }\n")
        self.assertEqual([len(css_gaps(p)) > 0 for p in planted], [True] * 12)
        self.assertEqual(css_gaps(css + ".st-btn-big { background: var(--key); color: var(--black); }\n"), [])


# ── 쪽 ──────────────────────────────────────────────────────────────────────────────
POLICY = ("default-src 'none'; script-src 'self'; style-src 'self'; connect-src https://api.github.com; media-src blob:; "
          "manifest-src 'self'; base-uri 'none'; form-action 'none'; object-src 'none'; worker-src 'none'; webrtc 'block'; "
          "require-trusted-types-for 'script'; trusted-types 'none'")
SCRIPTS = ("core.js", "store.js", "timer.js", "app.js", "today.js", "screens.js", "settings.js")   # index.html이 싣는 차례
IDS = ("st-fallback", "st-head", "st-nav", "st-note", "st-main")        # 뼈대의 id — 가짜 묶음의 SKELETON과 같다
GLOBALS = {"core.js": "StudyCore", "store.js": "StudyStore", "timer.js": "StudyTimer", "sync.js": "StudySync",
           "recorder.js": "StudyRecorder", "app.js": "StudyApp", "today.js": "StudyToday", "screens.js": "StudyScreens",
           "settings.js": "StudySettings"}                              # 파일 → 전역 이름. 이 차례가 스크립트의 끝 차례다
PAGE_FILES = ("index.html", "manifest.webmanifest", "study.css")
HEAD = (                                                                # 머리의 줄(이 차례). {v}는 판 글자, {name}은 문구 표의 APP_NAME
    '<meta charset="utf-8">',
    '<meta http-equiv="Content-Security-Policy" content="' + POLICY + '">',
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
    '<meta name="robots" content="noindex, nofollow">',
    '<meta name="referrer" content="no-referrer">',
    '<meta name="theme-color" content="#000000">',
    '<meta name="color-scheme" content="dark">',
    '<meta name="apple-mobile-web-app-capable" content="yes">',
    '<meta name="mobile-web-app-capable" content="yes">',
    '<meta name="apple-mobile-web-app-title" content="{name}">',
    '<meta name="apple-mobile-web-app-status-bar-style" content="black">',
    '<meta name="format-detection" content="telephone=no">',
    '<title>{name}</title>',
    '<link rel="manifest" href="manifest.webmanifest?v={v}">',
    '<link rel="stylesheet" href="study.css?v={v}">',
)
BODY = (
    '<p id="st-fallback">{fallback} <a href="./">{reload}</a></p>',
    '<header id="st-head"></header>',
    '<nav id="st-nav"></nav>',
    '<p id="st-note" role="status"></p>',
    '<main id="st-main"></main>',
)
MANIFEST = {"name": "{name}", "short_name": "{name}", "id": "./", "start_url": "./", "scope": "./", "display": "standalone",
            "background_color": "#000000", "theme_color": "#000000", "lang": "ko"}
NEVER = ("<style", " style=", "<base", "<iframe", "<img", "<form", "<object", "<embed", "<svg", 'rel="icon"', "apple-touch-icon",
         'rel="preconnect"', "fonts.", "../")                           # 뼈대 문서에 있으면 안 되는 글자


def table_text(key):
    """문구 표(core.js의 T)에서 키 하나의 글자."""
    found = re.search(r'^\s+%s: "([^"\\]*)",$' % re.escape(key), study("core.js"), re.M)
    return found.group(1) if found else ""


def version():
    found = re.search(r'^  const VERSION = "([^"]*)";$', study("app.js"), re.M)
    return found.group(1) if found else ""


def expected_page(scripts, v):
    """뼈대 문서가 가져야 할 글자 전부 — 표와 문구에서 만든다."""
    words = {"name": table_text("APP_NAME"), "fallback": table_text("FALLBACK"), "reload": table_text("RELOAD"), "v": v}
    tags = ['<script src="%s?v=%s"></script>' % (name, v) for name in scripts]
    rows = ["<!doctype html>", '<html lang="ko">', "<head>"] + list(HEAD) + ["</head>", "<body>"] + list(BODY) + tags + ["</body>", "</html>"]
    return "\n".join(rows).format(**words) + "\n"


def page_faults(html):
    """뼈대 문서에 있으면 안 되는 것 → 문구 목록. 인라인 코드 · 폴더 밖 주소 · 만들지 않기로 한 태그."""
    out = []
    lines = html.split("\n")
    at = lines.index(HEAD[0]) if HEAD[0] in lines else -1
    if at < 0 or lines[at + 1:at + 2] != [HEAD[1]] or html.count("Content-Security-Policy") != 1:
        out.append("정책 meta가 charset 바로 다음 줄에 약속한 글자로 한 번 있어야 한다")
    if re.search(r"<script\b(?![^>]*\bsrc=)[^>]*>|<script\b[^>]*>[^<]", html):
        out.append("인라인 스크립트")
    out += ["있으면 안 되는 글자: " + word for word in NEVER if word in html]
    if re.search(r"<[^>]*\son\w+\s*=", html):
        out.append("속성으로 넣은 처리기")
    hrefs = re.findall(r'\bhref="([^"]*)"', html)
    if [h.split("?")[0] for h in hrefs] != ["manifest.webmanifest", "study.css", "./"]:
        out.append("href는 매니페스트 · 모양 파일 · ./ 셋뿐이다: %r" % hrefs)
    if "://" in html.replace(POLICY, ""):
        out.append("바깥 주소")
    return out


def page_scripts(html):
    return re.findall(r'<script src="([^"]*)"></script>', html)


def fake_skeleton():
    """가짜 묶음이 미리 만드는 뼈대: (id 목록, 태그 목록)."""
    src = read("scripts", "study_fakes.cjs")
    ids = re.search(r"^const SKELETON = \[([^\]]*)\];$", src, re.M)
    tags = re.search(r"^const SKELETON_TAGS = \[([^\]]*)\];$", src, re.M)
    return [re.findall(r'"([^"]+)"', m.group(1)) if m else [] for m in (ids, tags)]


class StudyPageTest(unittest.TestCase):
    def test_page_is_exactly_the_agreed_text(self):
        got, want = study("index.html").split("\n"), expected_page(SCRIPTS, version()).split("\n")
        gaps = ["%d행: %r ≠ %r" % (i + 1, a, b) for i, (a, b) in enumerate(zip(got, want)) if a != b]
        self.assertEqual((gaps[:3], len(got)), ([], len(want)), "index.html이 약속한 글자와 다르다 — 줄을 더했으면 HEAD · BODY · SCRIPTS도 고친다")

    def test_policy_meta_follows_charset(self):
        lines = study("index.html").split("\n")
        self.assertEqual(lines[3:5], ['<meta charset="utf-8">', '<meta http-equiv="Content-Security-Policy" content="%s">' % POLICY])
        self.assertEqual(len(POLICY.split("; ")), 13)
        self.assertIn("connect-src https://api.github.com;", POLICY)

    def test_nothing_inline_and_nothing_from_outside(self):
        self.assertEqual(page_faults(study("index.html")), [])

    def test_scripts_follow_the_table_and_one_version(self):
        html, v = study("index.html"), version()
        self.assertRegex(v, r"^[0-9]{1,4}$", "판 글자(app.js의 VERSION)는 숫자 1~4자다")
        self.assertEqual(page_scripts(html), [name + "?v=" + v for name in SCRIPTS], "스크립트 차례가 SCRIPTS와 다르다")
        self.assertEqual(set(re.findall(r"\?v=([^\"]*)", html)), {v}, "모든 ?v=가 StudyApp.VERSION과 같아야 한다")
        self.assertEqual(html.count("<script"), len(SCRIPTS))
        self.assertEqual(list(SCRIPTS), [name for name in GLOBALS if name in SCRIPTS], "스크립트는 GLOBALS의 차례(끝 차례)를 따른다")

    def test_skeleton_ids_match_the_fakes(self):
        ids, tags = fake_skeleton()
        self.assertEqual((ids, len(tags)), (list(IDS), len(IDS)), "가짜 묶음의 SKELETON이 IDS와 다르다")
        html = study("index.html")
        for name, tag in zip(ids, tags):
            self.assertEqual(len(re.findall(r'<%s id="%s"[ >]' % (tag, name), html)), 1, name)
        self.assertEqual(re.findall(r'\bid="([^"]*)"', html), list(IDS))
        self.assertIn('<p id="st-note" role="status"></p>', html)

    def test_names_and_fallback_come_from_the_table(self):
        html, name = study("index.html"), table_text("APP_NAME")
        self.assertEqual(name, "2분 노트")
        self.assertIn("<title>%s</title>" % name, html)
        self.assertIn('<meta name="apple-mobile-web-app-title" content="%s">' % name, html)
        self.assertIn('<p id="st-fallback">%s <a href="./">%s</a></p>' % (table_text("FALLBACK"), table_text("RELOAD")), html)
        self.assertIn('<meta name="robots" content="noindex, nofollow">', html)

    def test_manifest(self):
        want = dict((k, v.format(name=table_text("APP_NAME"))) for k, v in MANIFEST.items())
        self.assertEqual(json.loads(study("manifest.webmanifest")), want, "매니페스트가 약속과 다르다(아이콘 항목은 두지 않는다)")

    def test_folder_holds_only_known_files(self):
        self.assertEqual(sorted(os.listdir(STUDY)), sorted(PAGE_FILES + SCRIPTS), "site/study/의 파일이 표와 다르다 — SCRIPTS에 줄을 더한다")
        self.assertEqual([n for n in SCRIPTS if n not in GLOBALS], [])

    def test_planted_page_faults_are_caught(self):
        page = expected_page(SCRIPTS, "7")
        self.assertEqual((page_faults(page), page_scripts(page)[0], page.count("?v=7")), ([], "core.js?v=7", len(SCRIPTS) + 2))
        moved = page.replace(HEAD[1] + "\n", "").replace("</head>", HEAD[1] + "\n</head>")
        planted = (moved, page.replace("</body>", "<script>go()</script>\n</body>"), page.replace('<main id="st-main">', '<main id="st-main" onclick="go()">'),
                   page.replace("</head>", '<link rel="icon" href="a.png">\n</head>'), page.replace('href="./"', 'href="../"'),
                   page.replace("</body>", '<script src="https://example.org/a.js"></script>\n</body>'), page.replace("<body>", '<body style="margin:0">'))
        self.assertEqual([len(page_faults(p)) > 0 for p in planted], [True] * 7)


# ── 낱말 ────────────────────────────────────────────────────────────────────────────
# 능력 표 — 파일 → 써도 되는 낱말 → 횟수(None이면 한 번 이상). 여기 없는 파일 · 낱말은 0번이다(주석은 떼고 센다).
CAPS = {
    "core.js": {"https://github.com/settings/personal-access-tokens/new": 1},
    "store.js": {"localStorage": None, "navigator.storage": None, "readKey(": 1},
    "timer.js": {"Date.now": None, "setInterval": None, "clearInterval": None},
    "app.js": {"document.createElement": 1, "document.addEventListener": None, "document.getElementById": None,
               "document.visibilityState": None, "navigator.standalone": None, "navigator.share": None, "navigator.clipboard": None,
               "location.hash": None, "location.protocol": None, "location.reload(": None, "history.replaceState": None,
               "crypto.getRandomValues": None, "window.top": None, "window.self": None, "window.addEventListener": None,
               "Date.now": None},
    "today.js": {},                                                     # 화면 모듈은 능력 낱말을 하나도 쓰지 않는다(틀과 기기 저장의 손만 빌린다)
    "screens.js": {},
    "settings.js": {},
}
SCREENS = ("today.js", "screens.js", "settings.js")                     # 화면 모듈 — 요소는 StudyApp.el로만, 기록은 StudyApp.write로만
SCREEN_BANNED = ("document", "navigator", "location", "localStorage", "fetch(", "appendLine(", "makeLine(", "absorb(", "dequeue(")
FAMILIES = (                                                            # 능력 낱말을 찾아내는 무늬 — 찾은 것마다 CAPS의 낱말로 시작해야 한다
    r"\blocalStorage\b", r"\bindexedDB\b", r"\bnavigator\.\w+", r"\blocation\.\w+\(?", r"\bdocument\.\w+", r"\bhistory\.\w+",
    r"\bcrypto\.\w+", r"\bwindow\.(?!Study)\w+", r"\bfetch\(", r"\bAbortController\b", r"\bAuthorization\b", r"\breadKey\(",
    r"\bMediaRecorder\b", r"\b(?:create|revoke)ObjectURL\b", r"\bDate\.now\b", r"\b(?:set|clear)(?:Timeout|Interval)\b",
    r"https?://[^\s\"'`)]+",
)
BANNED = (                                                              # site/ 어디서도 0번(.html · .js)
    "innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "DOMParser", "createContextualFragment", "setHTML", "srcdoc",
    "eval(", "new Function", "javascript:", 'setAttribute("on', "setAttribute('on",
    "serviceWorker", "import(", "importScripts", "RTCPeerConnection", "window.open", "location.assign", "location.replace",
    'rel="dns-prefetch"', 'rel="prefetch"', 'rel="prerender"',
)
STUDY_BANNED = (                                                        # 공부 쪽 .js에만 더 건다
    "console.", "Math.random", "performance.", "sessionStorage", "document.cookie", "XMLHttpRequest", "WebSocket", "EventSource",
    "sendBeacon", "postMessage", "classList", ".style", "location.href", "readText", "querySelector",
    "module.exports", "typeof window", "require(",
)
STUDY_BANNED_RE = (r"new Date\(\s*\)", r"location\.hash\s*=(?!=)", r"\.(?:hidden|disabled)\s*=(?!=)")   # 인자 없는 시계 · 주소 대입 · 속성 대입
NAME_LINES = {"store.js": 'const P = "macro-study.";'}                  # 저장 이름의 머리를 적는 줄(파일마다 한 줄). 다른 파일은 그 글자를 모른다
STORE_CALL = r"localStorage\.(?:getItem|setItem|removeItem)\(P \+ "     # 저장 공간을 부르는 꼴은 이것뿐이다(훑는 꼴이 없다)
OUTSIDE = ("https://api.github.com/repos/", "https://github.com/settings/personal-access-tokens/new")   # 코드에 적는 바깥 주소
JS_TOKEN = re.compile(                  # 문자열 셋 | 줄 주석 | 블록 주석 | 정규식 리터럴(앞 글자로 알아본다)
    r'"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|`(?:\\.|[^`\\])*`|//[^\n]*|/\*.*?\*/'
    r'|(?:[=(,:!&|?\[>]|\breturn)\s*/(?![/*])(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^/\\\n\[])+/', re.S)


def js_code(text):
    """주석을 뗀 스크립트. 문자열과 정규식은 그대로 둔다 — 그 안의 //(주소)는 주석이 아니다."""
    return JS_TOKEN.sub(lambda m: "" if m.group(0)[:2] in ("//", "/*") else m.group(0), text)


def banned_hits(name, code):
    """주석을 뗀 글자에서 찾은 금지 낱말. .js에는 공부 쪽 금지 낱말과 무늬까지 건다."""
    hits = [w for w in BANNED if w in code]
    if name.endswith(".js"):
        hits += [w for w in STUDY_BANNED if w in code] + [p for p in STUDY_BANNED_RE if re.search(p, code)]
    return hits


def cap_tokens(code):
    return [m.group(0) for pattern in FAMILIES for m in re.finditer(pattern, code)]


def cap_gaps(name, code, caps):
    """능력 표와 다른 곳 → 문구 목록. 표에 없는 낱말, 횟수가 다른 낱말, 쓰지 않는 줄."""
    allowed, tokens, out = caps.get(name, {}), cap_tokens(code), []
    for token in sorted(set(tokens)):
        if not any(token.startswith(word) for word in allowed):
            out.append("site/study/%s: `%s` — 능력 표(CAPS)에 없다" % (name, token))
    for word, times in allowed.items():
        got = sum(1 for token in tokens if token.startswith(word))
        if got == 0 or (times is not None and got != times):
            out.append("site/study/%s: `%s` %s, 지금 %d번" % (name, word, "한 번 이상" if times is None else "%d번" % times, got))
    return out


def name_gaps(name, code):
    """저장 이름의 머리를 아는 파일은 NAME_LINES의 것뿐이고, 저장 공간은 P로 시작하는 이름으로만 부른다."""
    out = []
    want = 1 if name in NAME_LINES else 0
    if code.count("macro-study") != want or (want and NAME_LINES[name] not in code):
        out.append("site/study/%s: 저장 이름의 머리(macro-study)는 NAME_LINES의 줄에만 %d번 적는다" % (name, want))
    if code.count("localStorage") != len(re.findall(STORE_CALL, code)):
        out.append("site/study/%s: 저장 공간은 getItem · setItem · removeItem(P + …)으로만 부른다(훑지 않는다)" % name)
    return out


def shape_gaps(name, text):
    """모듈의 꼴: 파일 하나가 window.StudyXxx = (() => { "use strict"; … })(); 하나다."""
    rows = [r for r in text.split("\n") if r.strip() and not r.startswith("//")]
    head = "window.%s = (() => {" % GLOBALS.get(name, "?")
    out = []
    if rows[:2] != [head, '  "use strict";'] or rows[-1:] != ["})();"]:
        out.append("site/study/%s: 첫 줄은 `%s`, 다음 줄은 \"use strict\", 끝 줄은 `})();`" % (name, head))
    if [r for r in rows[1:-1] if not r.startswith("  ")]:
        out.append("site/study/%s: 맨 위에 선언을 두지 않는다" % name)
    if [r for r in rows[1:] if re.search(r"=>\s*\{\s*$", r)]:
        out.append("site/study/%s: 화살표 함수는 한 줄짜리에만 쓴다" % name)
    if [r for r in rows if re.match(r"\s*(?:async )?function\b", r) and not re.match(r"  (?:async )?function \w+\(", r)]:
        out.append("site/study/%s: 이름 있는 함수는 2칸 들여쓴 `function 이름(` 꼴로만 쓴다" % name)
    return out


class StudyWordsTest(unittest.TestCase):
    def code(self):
        return [(n, js_code(study(n))) for n in SCRIPTS]

    def test_no_banned_word(self):
        hits = [(n, banned_hits(n, c)) for n, c in self.code() + [("index.html", study("index.html"))]]
        self.assertEqual([h for h in hits if h[1]], [], "금지 낱말이 있다 — 글자는 텍스트로만 넣고, 문서는 StudyApp.el로만 만든다")

    def test_capabilities_match_the_table(self):
        gaps = [g for n, c in self.code() for g in cap_gaps(n, c, CAPS)]
        self.assertEqual(gaps, [], "능력 표(CAPS)와 다르다 — 능력마다 그것을 만지는 파일은 하나다")
        self.assertEqual([n for n in CAPS if n not in SCRIPTS], [], "CAPS에 싣지 않는 파일의 줄이 있다")

    def test_screens_only_borrow_the_frame(self):
        shown = [(n, c) for n, c in self.code() if n in SCREENS]
        self.assertEqual([(n, w) for n, c in shown for w in SCREEN_BANNED if w in c], [], "화면 모듈은 문서 · 저장 공간 · 통신을 직접 만지지 않고, 기록 줄을 스스로 만들지 않는다")
        self.assertEqual([n for n, c in shown if CAPS.get(n) != {} or "StudyApp.register(" not in c], [], "화면 모듈의 능력 표는 비어 있고, 틀에 register로 들어간다")
        self.assertIn("today.js", [n for n, c in shown])

    def test_storage_names_start_with_the_prefix(self):
        self.assertEqual([g for n, c in self.code() for g in name_gaps(n, c)], [])
        self.assertEqual([n for n in PAGE_FILES if "macro-study" in study(n)], [])

    def test_outside_addresses_are_the_two_strings(self):
        urls = sorted(set(u for n, c in self.code() for u in re.findall(r"https?://[^\s\"'`)]+", c)))
        self.assertEqual([u for u in urls if u not in OUTSIDE], [], "코드에 적는 바깥 주소는 두 글자열뿐이다")
        self.assertEqual([n for n in ("study.css", "manifest.webmanifest") if "http" in study(n)], [])

    def test_module_shape(self):
        self.assertEqual([g for n in SCRIPTS for g in shape_gaps(n, study(n))], [])

    def test_planted_words_are_caught(self):
        code = js_code('// console.log 설명\nconst u = "https://example.org/a"; x.classList.add("a"); t = new Date( ); location.hash = "#a";\n'
                       'if (location.hash == "") node.hidden = true; fetch(u); navigator.geolocation; window.parent; localStorage.clear();\n')
        self.assertEqual(banned_hits("a.js", code), ["classList", r"new Date\(\s*\)", r"location\.hash\s*=(?!=)", r"\.(?:hidden|disabled)\s*=(?!=)"])
        self.assertEqual(banned_hits("a.html", '<a href="javascript:void 0">x</a>'), ["javascript:"])
        gaps = cap_gaps("a.js", code, {"a.js": {"location.hash": 1, "fetch(": None, "Date.now": None}})
        self.assertEqual([g.split(": ", 1)[1] for g in gaps], [
            "`https://example.org/a` — 능력 표(CAPS)에 없다", "`localStorage` — 능력 표(CAPS)에 없다", "`navigator.geolocation` — 능력 표(CAPS)에 없다",
            "`window.parent` — 능력 표(CAPS)에 없다", "`location.hash` 1번, 지금 2번", "`Date.now` 한 번 이상, 지금 0번"])
        self.assertEqual((len(name_gaps("a.js", code)), len(name_gaps("a.js", 'const k = "macro-study.key";'))), (1, 1))
        bad = 'window.StudyCore = (() => {\n  "use strict";\n  const f = x => {\n    return x;\n  };\n    function deep() {}\n})();\nconst top = 1;\n'
        self.assertEqual(len(shape_gaps("core.js", bad)), 4)


# ── 크기 ────────────────────────────────────────────────────────────────────────────
TESTS = os.path.join(REPO, "scripts")
SUITES = ("test_study_fakes.cjs", "test_study_core.cjs", "test_study_app.cjs", "test_study_today.cjs",
          "test_study_screens.cjs")                                     # node 묶음 — 아래 StudyNodeTest가 돌린다
MAX_LINES, MAX_BLOCK = 800, 50
BLOCKS = {                                                              # 확장자 → (덩어리의 첫 줄, 끝 줄)
    ".js": (r"  (?:async )?function \w+\(", r"  \}$"),
    ".cjs": (r"(?:async )?function \w+\(|class \w+|test\(", r"\}"),
    ".py": (r"(?:    )?def \w+\(", None),
}


def long_blocks(name, lines, limit):
    """함수(덩어리)가 limit 줄을 넘는 곳 → 문구 목록. .py는 들여쓰기로, 나머지는 끝 줄의 무늬로 끝을 찾는다."""
    start, end = BLOCKS[os.path.splitext(name)[1]]
    out = []
    for a, row in enumerate(lines):
        if not re.match(start, row):
            continue
        depth = len(row) - len(row.lstrip())
        rest = range(a + 1, len(lines))
        if end is None:
            b = next((i for i in rest if lines[i].strip() and len(lines[i]) - len(lines[i].lstrip()) <= depth), len(lines)) - 1
        else:
            b = next((i for i in rest if re.match(end, lines[i])), len(lines) - 1)
        if b - a + 1 > limit:
            out.append("%s %d행: %s — %d줄" % (name, a + 1, row.strip()[:40], b - a + 1))
    return out


def sized_files():
    """줄 수와 함수 길이를 재는 파일(저장소 뿌리 기준)."""
    tests = sorted(n for n in os.listdir(TESTS) if re.match(r"(?:test_)?study_\w+\.(?:cjs|py)$", n))
    return ["site/study/" + n for n in sorted(os.listdir(STUDY))] + ["scripts/" + n for n in tests]


class StudySizeTest(unittest.TestCase):
    def test_files_stay_under_800_lines(self):
        sizes = [(n, len(read(*n.split("/")).split("\n"))) for n in sized_files() + ["scripts/study_cases.json"]]
        self.assertEqual([s for s in sizes if s[1] >= MAX_LINES], [], "800줄에 닿은 파일이 있다 — 쪼갠다")
        self.assertIn("scripts/test_study_site.py", [s[0] for s in sizes])

    def test_functions_stay_within_50_lines(self):
        names = [n for n in sized_files() if os.path.splitext(n)[1] in BLOCKS]
        gaps = [g for n in names for g in long_blocks(n, read(*n.split("/")).split("\n"), MAX_BLOCK)]
        self.assertEqual(gaps, [], "50줄을 넘는 함수가 있다 — 쪼갠다")
        self.assertGreaterEqual(len(names), len(SCRIPTS) + len(SUITES) + 2)

    def test_every_suite_file_is_listed(self):
        found = sorted(n for n in os.listdir(TESTS) if re.match(r"test_study_\w+\.cjs$", n))
        self.assertEqual(found, sorted(SUITES), "scripts/test_study_*.cjs와 SUITES가 다르다 — 묶음을 더했으면 SUITES에 적는다")

    def test_planted_long_function_is_caught(self):
        body = ["    x += 1;"] * 49
        self.assertEqual(long_blocks("a.js", ["  function ok() {"] + body[:48] + ["  }"], 50), [])
        self.assertEqual(long_blocks("a.js", ["  function big(a) {"] + body + ["  }"], 50), ["a.js 1행: function big(a) { — 51줄"])
        self.assertEqual(len(long_blocks("a.cjs", ['test("긴 것", () => {'] + body + ["});"], 50)), 1)
        self.assertEqual(len(long_blocks("a.py", ["def big():"] + ["    x = 1"] * 50 + ["", "def small():", "    pass"], 50)), 1)
        self.assertEqual(long_blocks("a.py", ["class A:", "    def m(self):"] + ["        x = 1"] * 49 + ["    def n(self):", "        pass"], 50), [])


# ── node ────────────────────────────────────────────────────────────────────────────
NODE = shutil.which("node")
IN_CI = os.environ.get("GITHUB_ACTIONS") == "true"


def node_gate(node, in_ci):
    """node 테스트를 어떻게 할지: "run" · "skip"(이 PC에 node가 없다) · "fail"(CI에 node가 없다 — 건너뛰지 않는다)."""
    if node:
        return "run"
    return "fail" if in_ci else "skip"


def run_node(*args):
    return subprocess.run([NODE] + list(args), cwd=REPO, capture_output=True, timeout=300)


class StudyNodeTest(unittest.TestCase):
    def setUp(self):
        gate = "run" if self._testMethodName == "test_ci_never_skips" else node_gate(NODE, IN_CI)
        if gate == "fail":
            self.fail("CI에 node가 없다 — 공부 화면 테스트를 건너뛰지 않는다")
        if gate == "skip":
            self.skipTest("node가 없다")

    def test_ci_never_skips(self):
        self.assertEqual([node_gate("node", True), node_gate("node", False), node_gate(None, False), node_gate(None, True)],
                         ["run", "run", "skip", "fail"])

    def test_node_version_is_printed(self):
        v = run_node("--version").stdout.decode("utf-8", "replace").strip()
        self.assertRegex(v, r"^v\d+\.\d+")
        sys.stderr.write("node %s\n" % v)                               # Actions 로그에 실제로 돈 판을 남긴다

    def test_syntax(self):
        for name in SCRIPTS:
            r = run_node("--check", os.path.join(STUDY, name))
            self.assertEqual(r.returncode, 0, name + "\n" + r.stderr.decode("utf-8", "replace")[-2000:])

    def test_suites_pass(self):
        for name in SUITES:
            r = run_node("--test", os.path.join(TESTS, name))
            self.assertEqual(r.returncode, 0, name + "\n" + r.stdout.decode("utf-8", "replace")[-3000:])


if __name__ == "__main__":
    unittest.main()
