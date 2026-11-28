"""화면 안전망 — site/index.html 안의 스크립트가 구문 오류 없이 읽히는지, node 테스트가 워크플로에서 빠지지 않았는지 본다.

무엇을:
  1. index.html의 src 없는 <script> 본문을 모두 꺼내 저장소 밖 임시 폴더에서 node --check로 컴파일한다(실행하지 않는다).
  2. scripts/test_*.cjs가 daily.yml의 check 잡에 모두 적혀 있는지 본다
     (test_study_*는 빼고 — test_study_site.py가 부른다).
  두 검사에는 일부러 망가뜨린 사본이 걸리는지 보는 덫이 하나씩 있다(저장소의 파일은 고치지 않는다).
왜:  본 앱 스크립트에 'if (x {' 한 줄만 들어가도 사이트 전체가 빈 화면이 되는데 다른 테스트는 모두 통과했고,
     새 node 테스트를 만들고 daily.yml에 적지 않아도 잡는 검사가 없었다.
node:  PATH에 node가 없으면 구문 검사는 CI(환경 변수 CI가 있으면)에서는 실패하고, 그 밖에서는 건너뛴다.
실행:  python -X utf8 scripts/test_page_parse.py
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_RE = re.compile(r"<script(?=[\s>])([^>]*)>(.*?)</script\s*>", re.S | re.I)
SRC_RE = re.compile(r"\ssrc\s*=", re.I)


def read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def inline_scripts(page):
    """src 없는 <script>마다 (본문이 시작하는 줄 — 1부터, 본문)."""
    return [(page.count("\n", 0, m.start(2)) + 1, m.group(2))
            for m in SCRIPT_RE.finditer(page) if not SRC_RE.search(m.group(1))]


def node_error(stderr, path, start):
    """node --check의 출력에서 오류 줄까지만 남기고, 오류가 난 곳을 index.html의 줄로 옮겨 적는다."""
    name = os.path.basename(path)
    kept = []
    for line in stderr.replace(path, name).splitlines():
        if line.strip() and not line.startswith(("(node:", "(Use `node")):     # node의 경고 두 줄은 뺀다
            kept.append(line)
        if re.match(r"\w*Error\b", line):       # 그 아래는 node 내부 호출 기록
            break
    at = re.search(re.escape(name) + r":(\d+)", stderr)
    where = [f"오류 위치: site/index.html {start + int(at.group(1)) - 1}행"] if at else []
    return "\n".join(where + kept)


def compile_errors(node, blocks):
    """블록마다 node --check로 컴파일만 한다 — 실패한 블록의 문구 목록."""
    errors = []
    with tempfile.TemporaryDirectory() as tmp:
        # 보통 스크립트로만 읽는다 — 정해 두지 않으면 node가 import·최상위 await를 ES 모듈로 다시 읽어 통과시킨다
        write(os.path.join(tmp, "package.json"), '{"type": "commonjs"}')
        for number, (start, body) in enumerate(blocks, 1):
            path = os.path.join(tmp, f"block{number}.js")
            write(path, body)
            done = subprocess.run([node, "--check", path], capture_output=True,
                                  encoding="utf-8", errors="replace", timeout=60)
            if done.returncode:
                errors.append(f"블록 {number}(site/index.html {start}행에서 시작) 컴파일 실패\n"
                              + node_error(done.stderr, path, start))
    return errors


def node_test_names():
    """daily.yml이 직접 돌려야 하는 node 테스트 파일 이름."""
    return sorted(n for n in os.listdir(os.path.join(REPO, "scripts"))
                  if n.startswith("test_") and n.endswith(".cjs") and not n.startswith("test_study_"))


def missing_in_check_job(workflow, names):
    """names 가운데 check 잡에 'node --test scripts/<이름>' 줄이 없는 것(주석으로 막은 줄은 없는 것)."""
    job = workflow[workflow.index("\n  check:"):workflow.index("\n  update:")]
    return [n for n in names
            if not re.search(rf"^\s*(?:run:\s*)?node --test scripts/{re.escape(n)}\s*(?:#.*)?$", job, re.M)]


def list_errors(workflow, names):
    missing = missing_in_check_job(workflow, names)
    if not missing:
        return []
    return ["daily.yml의 check 잡에 없는 node 테스트: " + ", ".join(missing)
            + " — '단위 테스트' 단계에 'node --test scripts/<이름>' 줄을 더한다"]


class InlineScriptTest(unittest.TestCase):
    def setUp(self):
        self.page = read("site", "index.html")
        self.blocks = inline_scripts(self.page)
        self.assertGreaterEqual(len(self.blocks), 2, "index.html에서 src 없는 <script>를 2개 이상 꺼내지 못했다 — 꺼내기가 망가졌다")

    def node(self):
        path = shutil.which("node")
        if not path:
            if "CI" in os.environ:
                self.fail("node가 PATH에 없다 — CI에서는 건너뛰지 않는다")
            self.skipTest("node가 PATH에 없다 — 구문 검사는 node --check가 필요하다(CI에서는 실패한다)")
        return path

    def test_inline_scripts_compile(self):
        errors = compile_errors(self.node(), self.blocks)
        if errors:
            self.fail("\n\n".join(errors))

    def test_trap_broken_app_script_is_caught(self):
        node = self.node()
        if compile_errors(node, self.blocks):
            self.fail("덫을 놓기 전부터 깨진 블록이 있다 — test_inline_scripts_compile의 오류를 먼저 고친다")
        start, body = max(self.blocks, key=lambda b: len(b[1]))     # 본 앱 블록 — 가장 긴 것
        errors = compile_errors(node, inline_scripts(self.page.replace(body, body + "if (x {\n", 1)))
        self.assertEqual(len(errors), 1, errors)
        for mark in (f"site/index.html {start}행에서 시작", f"오류 위치: site/index.html {start + body.count(chr(10))}행",
                     "if (x {", "SyntaxError"):
            self.assertIn(mark, errors[0])


class NodeTestListTest(unittest.TestCase):
    def setUp(self):
        self.workflow = read(".github", "workflows", "daily.yml")
        self.names = node_test_names()
        self.assertTrue(self.names, "scripts/에서 node 테스트를 하나도 찾지 못했다")

    def test_every_node_test_is_in_the_check_job(self):
        errors = list_errors(self.workflow, self.names)
        if errors:
            self.fail(errors[0])

    def test_trap_removed_line_is_caught(self):
        before = missing_in_check_job(self.workflow, self.names)
        name = next(n for n in self.names if n not in before)      # 지금 적혀 있는 것 하나의 줄을 지운다
        trimmed, count = re.subn(rf"^[ \t]*node --test scripts/{re.escape(name)}\n", "", self.workflow, flags=re.M)
        self.assertEqual(count, 1, name)
        self.assertEqual(missing_in_check_job(trimmed, self.names), sorted(before + [name]))
        self.assertIn(name, list_errors(trimmed, self.names)[0])


if __name__ == "__main__":
    unittest.main(verbosity=1)
