#!/usr/bin/env python3
"""공개 전 검사(check_blind.py) 테스트 — 임시 git 저장소에 가짜 검사어로 돌린다.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
git이 없으면 건너뛴다. 진짜 검사어(.blind_patterns)는 쓰지 않는다.
종료코드 규약: 0 통과 / 1 발견 / 2 검사 불가 — 2는 통과로 치지 않는다.
"""
import json, os, shutil, subprocess, sys, tempfile, unicodedata, unittest

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(SCRIPTS, "check_blind.py")
GIT = shutil.which("git")
PATTERNS = "# 주석 줄\n비밀단어\nsecretword\n"
NOREPLY = "1+tester@users.noreply.github.com"
ID = {"GIT_AUTHOR_NAME": "tester", "GIT_AUTHOR_EMAIL": NOREPLY,
      "GIT_COMMITTER_NAME": "tester", "GIT_COMMITTER_EMAIL": NOREPLY}


@unittest.skipUnless(GIT, "git 필요")
class CheckBlindTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = os.path.join(self.tmp, "repo")
        os.makedirs(self.repo)
        self.git("init", "-q", "-b", "main")
        self.write(".gitignore", ".blind_patterns\n")
        self.commit_file("a.txt", "깨끗한 내용\n", "init")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, *args, cwd=None, **ident):
        env = {**os.environ, **ID, **ident}
        return subprocess.run([GIT, "-c", "commit.gpgsign=false", *args], cwd=cwd or self.repo,
                              env=env, check=True, capture_output=True)

    def write(self, name, data):
        if isinstance(data, bytes):
            with open(os.path.join(self.repo, name), "wb") as f:
                f.write(data)
        else:
            with open(os.path.join(self.repo, name), "w", encoding="utf-8", newline="\n") as f:
                f.write(data)

    def commit_file(self, name, data, msg, **ident):
        self.write(name, data)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg, **ident)

    def run_check(self, cwd=None, patterns=PATTERNS):
        env = {k: v for k, v in os.environ.items() if k != "BLIND_PATTERNS"}
        if patterns is not None:
            env["BLIND_PATTERNS"] = patterns
        r = subprocess.run([sys.executable, SCRIPT], cwd=cwd or self.repo, env=env,
                           capture_output=True, text=True, encoding="utf-8")
        return r.returncode, r.stdout + r.stderr

    def assertNoLeak(self, out):
        out = unicodedata.normalize("NFC", out)   # 자모 분해(NFD)로 찍혀도 새는 것
        self.assertNotIn("비밀단어", out)
        self.assertNotIn("secretword", out.lower())

    # --- 기본 ---
    def test_clean_repo_passes(self):
        rc, out = self.run_check()
        self.assertEqual(rc, 0, out)
        self.assertIn("✓ 검사어 2개", out)

    def test_no_patterns_cannot_check(self):
        rc, out = self.run_check(patterns=None)
        self.assertEqual(rc, 2, out)

    def test_current_file_hit_reports_line_only(self):
        self.commit_file("b.txt", "첫 줄\n여기 비밀단어 있음\n", "add b")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)
        self.assertIn("b.txt: 줄 2", out)
        self.assertNoLeak(out)

    def test_ascii_pattern_is_case_insensitive(self):
        with open(os.path.join(self.repo, "c.txt"), "w", encoding="utf-8") as f:
            f.write("SecretWord\n")   # 커밋 전(새로 추가될 파일)도 검사 대상
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)
        self.assertNoLeak(out)

    def test_tracked_pattern_file_fails(self):
        self.write(".blind_patterns", "zzz\n")   # .gitignore에 있어도 -f로 추가하면 추적된다
        self.git("add", "-f", ".blind_patterns")
        self.git("commit", "-q", "-m", "oops")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)

    def test_file_name_hit_does_not_print_name(self):
        # 이름과 내용에 모두 검사어가 있어도 로그에는 이름이 찍히지 않아야 한다
        self.commit_file("secretword.txt", "secretword\n", "add")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)
        self.assertNoLeak(out)

    # --- 과거 기록: 지운 파일·고친 줄도 공개 저장소 기록에는 남는다 ---
    def test_removed_file_in_history_is_found(self):
        self.commit_file("old.txt", "비밀단어\n", "add old")
        self.git("rm", "-q", "old.txt")
        self.git("commit", "-q", "-m", "remove old")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)
        self.assertIn("old.txt", out)
        self.assertNoLeak(out)

    def test_rewritten_line_in_history_is_found(self):
        self.commit_file("a.txt", "비밀단어\n", "leak")
        self.commit_file("a.txt", "고침\n", "fix")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)
        self.assertNoLeak(out)

    def test_old_file_name_in_history_is_found(self):
        self.commit_file("secretword.txt", "내용\n", "add")
        self.git("mv", "secretword.txt", "renamed.txt")
        self.git("commit", "-q", "-m", "rename")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)
        self.assertNoLeak(out)

    def test_old_path_spanning_folders_is_found(self):
        # 로컬 경로처럼 폴더를 걸친 검사어는 전체 경로로만 걸린다
        os.makedirs(os.path.join(self.repo, "abc"))
        self.commit_file("abc/def.txt", "깨끗한 내용\n", "add")   # a.txt와 같은 내용 → 같은 blob
        self.git("mv", "abc", "zzz")
        self.git("commit", "-q", "-m", "move")
        rc, out = self.run_check(patterns=PATTERNS + "abc/def\n")
        self.assertEqual(rc, 1, out)

    def test_korean_file_name_is_found(self):
        # git은 기본 설정(core.quotePath)에서 한글 파일 이름을 \355… 로 바꿔 찍는다 — 그대로면 검사어와 안 맞는다
        self.commit_file("비밀단어.txt", "내용\n", "add")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)
        self.assertNoLeak(out)

    def test_old_korean_file_name_in_history_is_found(self):
        self.commit_file("비밀단어.txt", "내용\n", "add")
        self.git("mv", "비밀단어.txt", "renamed.txt")
        self.git("commit", "-q", "-m", "rename")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)
        self.assertNoLeak(out)

    def test_commit_message_on_other_branch_is_found(self):
        self.git("checkout", "-q", "-b", "side")
        self.commit_file("s.txt", "내용\n", "비밀단어 메모")
        self.git("checkout", "-q", "main")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)
        self.assertNoLeak(out)

    # --- 커밋 이메일 ---
    def test_non_noreply_email_fails(self):
        self.commit_file("d.txt", "내용\n", "d", GIT_AUTHOR_EMAIL="someone@example.com")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)
        self.assertNotIn("someone@example.com", out)

    def test_github_web_committer_allowed(self):
        # GitHub 웹 UI(PR 병합 등)로 만든 커밋의 커미터는 noreply@github.com
        self.commit_file("e.txt", "내용\n", "e", GIT_COMMITTER_NAME="GitHub",
                         GIT_COMMITTER_EMAIL="noreply@github.com")
        rc, out = self.run_check()
        self.assertEqual(rc, 0, out)

    def test_actions_bot_email_allowed(self):
        self.commit_file("f.txt", "내용\n", "data", GIT_AUTHOR_NAME="github-actions[bot]",
                         GIT_AUTHOR_EMAIL="41898282+github-actions[bot]@users.noreply.github.com")
        rc, out = self.run_check()
        self.assertEqual(rc, 0, out)

    # --- 검사 불가는 통과가 아니다 ---
    def test_shallow_clone_cannot_check(self):
        self.commit_file("a.txt", "둘째\n", "second")
        clone = os.path.join(self.tmp, "shallow")
        url = "file:///" + self.repo.replace("\\", "/").lstrip("/")
        self.git("clone", "-q", "--depth", "1", url, clone, cwd=self.tmp)
        rc, out = self.run_check(cwd=clone)
        self.assertEqual(rc, 2, out)

    def test_missing_staged_object_cannot_check(self):
        self.write("new.txt", "새 파일\n")
        self.git("add", "new.txt")
        blob = self.git("rev-parse", ":new.txt").stdout.decode().strip()
        obj = os.path.join(self.repo, ".git", "objects", blob[:2], blob[2:])
        os.chmod(obj, 0o644)
        os.remove(obj)
        rc, out = self.run_check()
        self.assertEqual(rc, 2, out)

    def test_missing_object_cannot_check(self):
        blob = self.git("rev-parse", "HEAD:a.txt").stdout.decode().strip()
        obj = os.path.join(self.repo, ".git", "objects", blob[:2], blob[2:])
        os.chmod(obj, 0o644)   # git 객체 파일은 읽기 전용
        os.remove(obj)
        rc, out = self.run_check()
        self.assertEqual(rc, 2, out)

    # --- 검사어 파일: BOM·CRLF·앞뒤 공백 때문에 검사어가 조용히 죽으면 안 된다 ---
    # 메모장·PowerShell로 저장하면 BOM·CRLF가 붙는다. 첫 검사어는 뒤 공백, 둘째는 앞 탭
    BOM_PATTERNS = "\ufeffsecretword \r\n\t비밀단어\r\n".encode("utf-8")

    def test_patterns_file_with_bom_and_trailing_space(self):
        self.write(".blind_patterns", self.BOM_PATTERNS)
        self.commit_file("x.txt", "name is secretword\n", "x")
        rc, out = self.run_check(patterns=None)
        self.assertEqual(rc, 1, out)
        self.assertIn("x.txt: 줄 1", out)

    def test_patterns_file_with_leading_tab(self):
        self.write(".blind_patterns", self.BOM_PATTERNS)
        self.commit_file("x.txt", "첫 글자 비밀단어\n", "x")
        rc, out = self.run_check(patterns=None)
        self.assertEqual(rc, 1, out)
        self.assertIn("x.txt: 줄 1", out)

    def test_clean_repo_with_bom_patterns_counts_two(self):
        self.write(".blind_patterns", self.BOM_PATTERNS)
        rc, out = self.run_check(patterns=None)
        self.assertEqual(rc, 0, out)
        self.assertIn("✓ 검사어 2개", out)

    def test_utf16_patterns_file_cannot_check(self):
        self.write(".blind_patterns", "secretword\r\n".encode("utf-16"))
        rc, out = self.run_check(patterns=None)
        self.assertEqual(rc, 2, out)

    def test_bom_in_env_patterns(self):
        self.commit_file("x.txt", "secretword\n", "x")
        rc, out = self.run_check(patterns="\ufeffsecretword\n")
        self.assertEqual(rc, 1, out)

    # --- 텍스트로 읽을 수 없는 파일은 통과가 아니라 검사 불가 ---
    def test_binary_file_cannot_check_and_does_not_leak_name(self):
        self.commit_file("secretword_cv.pdf", b"PNG\x00\x00secretword\x00", "bin")
        rc, out = self.run_check()
        self.assertEqual(rc, 2, out)
        self.assertNoLeak(out)

    def test_utf16_file_cannot_check(self):
        self.commit_file("notes.txt", "작성자: 비밀단어\r\n".encode("utf-16"), "u16")
        rc, out = self.run_check()
        self.assertEqual(rc, 2, out)

    def test_cp949_file_cannot_check(self):
        self.commit_file("members.csv", "이름,비밀단어\n".encode("cp949"), "cp949")
        rc, out = self.run_check()
        self.assertEqual(rc, 2, out)

    def test_nfd_name_and_content_found(self):
        # macOS에서 만든 파일은 한글이 자모 분해(NFD)로 들어올 수 있다
        nfd = unicodedata.normalize("NFD", "비밀단어")
        self.commit_file(nfd + "_cv.txt", "작성: " + nfd + "\n", "nfd")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)
        self.assertNoLeak(out)

    def test_nfd_name_with_clean_content_found(self):
        nfd = unicodedata.normalize("NFD", "비밀단어")
        self.commit_file(nfd + "_cv.txt", "clean\n", "nfd")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)
        self.assertNoLeak(out)

    # --- 과거 기록의 나머지 경로 ---
    def test_unborn_orphan_head_still_checks_history(self):
        self.commit_file("old.txt", "secretword\n", "leak", GIT_AUTHOR_EMAIL="me@example.com")
        self.git("checkout", "-q", "--orphan", "fresh")
        self.git("rm", "-rqf", ".")
        self.write("b.txt", "clean\n")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)

    def test_annotated_tag_message_found(self):
        self.git("tag", "-a", "v1", "-m", "secretword release note")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)
        self.assertNoLeak(out)

    def test_tagger_email_must_be_noreply(self):
        self.git("tag", "-a", "v2", "-m", "release", GIT_COMMITTER_EMAIL="someone@example.com")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)
        self.assertNotIn("someone@example.com", out)

    def test_ref_name_found(self):
        self.git("branch", "feature/secretword")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)
        self.assertNoLeak(out)

    def test_file_added_only_in_merge_found(self):
        self.git("checkout", "-q", "-b", "side")
        self.commit_file("s.txt", "side\n", "side")
        self.git("checkout", "-q", "main")
        self.commit_file("m.txt", "main\n", "main")
        self.git("checkout", "-q", "side")
        self.git("merge", "-q", "--no-commit", "--no-ff", "main")
        self.write("비밀단어_메모.txt", "깨끗한 내용\n")   # a.txt와 같은 내용 → 같은 blob, 이름만 다르다
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "merge")
        self.git("checkout", "-q", "main")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)
        self.assertNoLeak(out)

    def test_staged_content_found(self):
        self.commit_file("about.md", "clean\n", "about")
        self.write("about.md", "secretword\n")
        self.git("add", "about.md")
        self.write("about.md", "clean\n")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)

    def test_replaced_commit_still_checked(self):
        # git replace로 가려도 원래 커밋은 공개 저장소에서 꺼낼 수 있다
        self.commit_file("b.txt", "secretword\n", "leak")
        bad = self.git("rev-parse", "HEAD").stdout.decode().strip()
        self.git("checkout", "-q", "-b", "tmp", "HEAD~1")
        self.commit_file("b.txt", "clean\n", "leak")
        good = self.git("rev-parse", "HEAD").stdout.decode().strip()
        self.git("checkout", "-q", "main")
        self.git("branch", "-q", "-D", "tmp")
        self.git("replace", bad, good)
        self.git("reset", "-q", "--hard")   # 스테이징·작업 트리도 가린 쪽(깨끗한 내용)으로 — 원래 커밋에만 남게
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)


    # --- 2차 리뷰: 검사어 파일의 보이지 않는 문자, 여러 보기(줄 경계·이스케이프·호환 문자), 머리 필드 ---
    def test_invisible_char_in_pattern_cannot_check(self):
        # 웹·메신저에서 복사한 검사어에 섞인 폭 없는 공백(U+200B)이나 중간 BOM은 그 검사어를 조용히 죽인다
        for bad in (chr(0x200B), chr(0xFEFF)):
            rc, out = self.run_check(patterns="zzz\n" + bad + "secretword\n")
            self.assertEqual(rc, 2, out)
            self.assertNoLeak(out)

    def test_term_split_across_lines_found(self):
        self.commit_file("README.md", "maintained by Fake\nPerson as a portfolio\n", "readme")
        rc, out = self.run_check(patterns=PATTERNS + "fake person\n")
        self.assertEqual(rc, 1, out)

    def test_html_entity_and_nbsp_found(self):
        for i, text in enumerate(("Fake&nbsp;Person", "Fake" + chr(0xA0) + "Person")):
            self.commit_file(f"p{i}.html", f"<p>{text}</p>\n", f"html {i}")
        rc, out = self.run_check(patterns=PATTERNS + "fake person\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("p0.html", out)
        self.assertIn("p1.html", out)

    def test_json_escaped_path_found(self):
        bs = chr(92)
        path = "C:" + bs + "Users" + bs + "fakeuser" + bs + "cache"
        self.commit_file("w.json", json.dumps({"warn": path + " 오류"}, ensure_ascii=False) + "\n", "json")
        rc, out = self.run_check(patterns=PATTERNS + "Users" + bs + "fakeuser\n")
        self.assertEqual(rc, 1, out)

    def test_json_unicode_escape_found(self):
        self.commit_file("n.json", json.dumps({"name": "작성 비밀단어"}) + "\n", "json")   # ensure_ascii 기본값: \uXXXX
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)

    def test_fullwidth_found(self):
        self.commit_file("f.txt", "".join(chr(ord(c) + 0xFEE0) for c in "SecretWord") + "\n", "fullwidth")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)

    def test_cp949_bytes_that_decode_as_utf8_found(self):
        # CP949 한글 일부는 우연히 올바른 UTF-8 바이트열이 된다 — 글자는 깨져도 원래 바이트로 찾아야
        data = "name,club\n홍철,창천\n".encode("cp949")
        data.decode("utf-8")   # 전제: UTF-8로 읽히는 조합
        self.commit_file("m.csv", data, "cp949")
        rc, out = self.run_check(patterns="창천\n")
        self.assertEqual(rc, 1, out)

    def test_lfs_pointer_cannot_check(self):
        pointer = "version https://git-lfs.github.com/spec/v1\noid sha256:" + "0" * 64 + "\nsize 17\n"
        self.commit_file("profile.md", pointer, "lfs")
        rc, out = self.run_check()
        self.assertEqual(rc, 2, out)

    def make_commit(self, body):
        """git이 쓰는 커밋 원문을 직접 만든다(서명 태그 병합의 mergetag 같은 머리 필드 재현용)."""
        head = self.git("rev-parse", "HEAD").stdout.decode().strip()
        tree = self.git("rev-parse", "HEAD^{tree}").stdout.decode().strip()
        who = f"tester <{NOREPLY}> 1700000000 +0000"
        text = f"tree {tree}\nparent {head}\nauthor {who}\ncommitter {who}\n{body}"
        sha = subprocess.run([GIT, "hash-object", "-t", "commit", "-w", "--stdin"], cwd=self.repo,
                             input=text.encode(), capture_output=True, check=True).stdout.decode().strip()
        self.git("update-ref", "refs/heads/made", sha)

    def test_mergetag_header_checked(self):
        head = self.git("rev-parse", "HEAD").stdout.decode().strip()
        self.make_commit(f"mergetag object {head}\n type commit\n tag v1\n"
                         " tagger secretword <someone@example.com> 1700000000 +0000\n \n release\n\nmerge v1\n")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)
        self.assertIn("noreply가 아닌", out)
        self.assertNoLeak(out)
        self.assertNotIn("someone@example.com", out)

    def test_other_header_field_checked(self):
        self.make_commit("encoding secretword\n\nmsg\n")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)

    def test_detached_head_without_refs_checks_history(self):
        self.commit_file("s.txt", "secretword\n", "leak")
        self.commit_file("s.txt", "clean\n", "fix")
        self.git("checkout", "-q", "--detach")
        self.git("branch", "-q", "-D", "main")
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)

    def test_grafts_cannot_check(self):
        head = self.git("rev-parse", "HEAD").stdout.decode().strip()
        os.makedirs(os.path.join(self.repo, ".git", "info"), exist_ok=True)
        with open(os.path.join(self.repo, ".git", "info", "grafts"), "w") as f:
            f.write(head + "\n")   # 기록을 여기서 끊는다
        rc, out = self.run_check()
        self.assertEqual(rc, 2, out)

    def test_name_only_in_tag_to_tree_found(self):
        # 같은 하위 트리가 두 이름으로 걸리면 rev-list는 한 이름만 찍는다 — 트리 항목 이름을 직접 봐야
        blob = self.git("rev-parse", "HEAD:a.txt").stdout.decode().strip()
        sub = self.mktree(f"100644 blob {blob}\tx.txt")
        self.git("tag", "a-snap", self.mktree(f"040000 tree {sub}\tdocs"))
        self.git("tag", "b-snap", self.mktree(f"040000 tree {sub}\t비밀단어"))
        rc, out = self.run_check()
        self.assertEqual(rc, 1, out)
        self.assertNoLeak(out)

    def mktree(self, line):
        r = subprocess.run([GIT, "mktree", "-z"], cwd=self.repo, input=line.encode() + b"\0",
                           capture_output=True, check=True)
        return r.stdout.decode().strip()

    def test_non_utf8_file_name_cannot_check(self):
        blob = self.git("rev-parse", "HEAD:a.txt").stdout.decode().strip()
        name = "비밀단어_이력서.txt".encode("cp949")
        subprocess.run([GIT, "update-index", "-z", "--index-info"], cwd=self.repo, check=True,
                       input=b"100644 " + blob.encode() + b"\t" + name + b"\0", capture_output=True)
        self.git("commit", "-q", "-m", "cp949 name")
        rc, out = self.run_check()
        self.assertEqual(rc, 2, out)

    def test_control_char_file_name_does_not_crash(self):
        # 이름에 든 제어 문자·탭·줄바꿈이 git 출력 줄을 깨도 검사가 죽거나 엉뚱한 객체를 찾지 않아야
        blob = self.git("rev-parse", "HEAD:a.txt").stdout.decode().strip()
        tree = self.mktree(f"100644 blob {blob}\tx" + chr(0x1C) + "y" + chr(9) + "z w.txt" + chr(0)
                           + f"100644 blob {blob}\tp" + chr(10) + "q.txt")
        head = self.git("rev-parse", "HEAD").stdout.decode().strip()
        sha = self.git("commit-tree", tree, "-p", head, "-m", "odd").stdout.decode().strip()
        self.git("update-ref", "refs/heads/odd", sha)
        rc, out = self.run_check()
        self.assertEqual(rc, 0, out)
        self.assertNotIn("Traceback", out)

    def test_unexpected_error_is_cannot_check(self):
        # git을 못 찾는 것 같은 예기치 못한 오류도 1(발견)이 아니라 2(검사 불가)
        empty = os.path.join(self.tmp, "nopath")
        os.makedirs(empty)
        env = {k: v for k, v in os.environ.items() if k not in ("BLIND_PATTERNS", "PATH")}
        r = subprocess.run([sys.executable, SCRIPT], cwd=self.repo, capture_output=True, text=True,
                           encoding="utf-8", env={**env, "PATH": empty, "BLIND_PATTERNS": PATTERNS})
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
