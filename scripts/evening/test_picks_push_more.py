#!/usr/bin/env python3
"""AI 요약 층 게시(picks_push)의 보강 테스트 — 켜는 스위치, 커밋 직전에 끊긴 잔재, 가지 위에서 불렸을 때, 다시 올리는 길이 새 main의
판을 보는가(그사이 내린 판 위에 문장을 다시 올리지 않는다), 규칙판 실행이 둘일 때. 끝의 묶음은 임시 폴더의 진짜 git으로 돈다.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요 — gh와 공개 전 검사는 가짜다. 진짜 git은 임시 폴더의 저장소(원격도 그 안의 bare 저장소)만 건드린다.
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_picks as K
import digest_rules as R
import digest_schema as S
import fixtures as F
import picks_push as P
import test_digest_picks as TK
from test_picks_push import MOD, NEW, OFF, ON, PATH, Case, Clock, MovedMainTest, Tool, good, runs

TH = R.TH


class SwitchTest(Case):
    def test_reads_the_repository_variable(self):
        git = Tool(gh_variable_list=(0, ON))
        self.assertEqual(P.switch(self.repo, run=git), "on")
        self.assertEqual(git.calls, [["gh", "variable", "list", "--json", "name,value"]])
        other = '[{"name":"OTHER","value":"true"},{"name":"EVENING_ENABLED","value":"TRUE"}]'
        for name, out in {"false": OFF, "변수가 없음": "[]", "다른 변수만": '[{"name":"OTHER","value":"true"}]', "값의 꼴이 다름": other}.items():
            with self.subTest(name):
                self.assertEqual(P.switch(self.repo, run=Tool(gh_variable_list=(0, out))), "off")

    def test_unreadable_means_stop(self):
        """읽지 못한 날은 꺼져 있을지 모른다 — 닫는 쪽으로."""
        for name, got in {"실패": 1, "gh 없음": FileNotFoundError("gh"), "JSON 아님": (0, "not json " + F.CANARIES[0]), "빈 출력": (0, ""),
                          "목록이 아님": (0, '{"name":"EVENING_ENABLED","value":"true"}'), "꼴이 다른 줄": (0, '["EVENING_ENABLED"]')}.items():
            with self.subTest(name):
                self.stops("switch", P.switch, self.repo, run=Tool(gh_variable_list=got))


class LeftoverTest(Case):
    def test_staged_leftover_is_unstaged_and_put_back(self):
        """커밋 직전에 끊긴 실행이 남긴 것(스테이징만 된 요약 파일) — 그 한 경로만 풀고 되돌린다. 전에는 다음 실행부터 모두 dirty였다."""
        for staged, after in ((f"M  {PATH}\n", MOD), (f"A  {PATH}\n", NEW), (f"AM {PATH}\n", NEW), (f"MM {PATH}\n", MOD)):
            with self.subTest(staged):
                self.put(TK.doc())
                git = Tool(status=[(0, staged), (0, after)])
                P.sync(self.repo, run=git)
                self.assertEqual(git.calls[1], ["git", "reset", "--quiet", "--", PATH])
                self.assertEqual(git.names(), ["status", "reset", "status"] + (["checkout"] if after == MOD else []) + ["fetch", "checkout"])
                self.assertEqual(os.path.exists(self.path), after == MOD)      # 새 파일이었으면 지운다
        git = Tool(status=[(0, f"M  {PATH}\n"), (0, MOD + " M data/digest.json\n")])          # 풀고 보니 다른 것이 있다
        self.stops("dirty", P.sync, self.repo, run=git)


class HeadTest(Case):
    def test_called_on_a_branch_or_on_unpushed_commits(self):
        """작업 폴더가 origin/main의 끝이 아니면 커밋을 남기지 않고 멈춘다(run은 늘 sync 뒤라 해당 없음 — make --publish를 바로 부른 날)."""
        for name, out in {"올리지 않은 커밋 위": "ccc333\naaa111\n", "한 줄뿐": "aaa111\n", "빈 출력": ""}.items():
            with self.subTest(name):
                self.put(TK.doc())
                git = Tool(**good(rev_parse=(0, out)))
                self.stops("head", P.publish, self.repo, F.EDITION, run=git)
                self.assertEqual((git.count("add"), git.count("commit"), git.count("push")), (0, 0, 0))
        self.assertEqual(git.calls[2], ["git", "rev-parse", "HEAD", "origin/main"])


class MovedEditionTest(Case):
    """push가 거절돼 새 main 위에 다시 올릴 때 — 그사이 판이 내려갔거나 다시 계산됐으면 옛 판의 문장을 올리지 않는다."""

    def refused(self, digest=None, hold=None, sources=None):
        """새 main으로 옮기면(checkout --detach) 자료가 그쪽 것으로 바뀐다."""
        old = S.dump(K.blank_picks("2026-10-07", "2026-10-07T18:04:00+09:00")).encode("utf-8")
        for name, doc in (("digest.json", F.digest()), ("digest_overrides.json", F.overrides()), ("sources.json", F.sources())):
            S.write_json(os.path.join(self.repo, "data", name), doc)             # 올리려던 때의 자료로 되돌려 놓고
        self.put(TK.doc())

        def checkout(cmd):
            if "--detach" in cmd:
                for name, doc in (("digest.json", digest), ("digest_overrides.json", hold), ("sources.json", sources)):
                    if doc is not None:
                        S.write_json(os.path.join(self.repo, "data", name), doc)
                with open(self.path, "wb") as f:
                    f.write(old)
            return 0
        git = MovedMainTest.moved(self, checkout=checkout)
        self.stops("moved", P.publish, self.repo, F.EDITION, run=git)
        self.assertEqual((git.count("push"), git.count("commit")), (1, 1))      # 다시 커밋하지도, 다시 올리지도 않는다
        self.assertEqual(git.calls[-1], ["git", "checkout", "--quiet", "--", PATH])    # 써 둔 파일도 되돌린다

    def test_edition_taken_down_meanwhile(self):
        d = F.digest()
        self.refused(digest=S.blank_digest(S.parse_iso(F.NOW)))
        self.refused(hold=F.overrides(withdraw=True))
        self.refused(hold=F.overrides(hide_ids=[d["must"][0]["id"]]))
        self.refused(hold=F.overrides(hide_channels=["fxbond2"]))

    def test_edition_recomputed_meanwhile(self):
        d = F.digest()
        gone = copy.deepcopy(d)
        gone["must"][0]["links"] = [ln for ln in gone["must"][0]["links"] if ln["ch"] != "fxbond1"]     # 읽힌 글이 링크에서 빠졌다
        self.refused(digest=gone)
        self.refused(digest={**d, "date": "2026-10-09"})                       # 읽을 수 없는 자료도 같다(형식이 어긋난 판)
        off = F.sources()
        off["channels"] = [{**c, "role": "wire"} if c["handle"] == "fxbond1" else c for c in off["channels"]]
        self.refused(sources=off)                                              # 읽힌 채널이 원천이 아니게 됐다

    def test_empty_layer_for_another_edition_does_not_go_up(self):
        """빈 층은 붙일 문장이 없어 화면 규칙으로는 걸리지 않는다 — 판 날짜를 따로 본다(새 main에는 다음 날 판이 올라와 있다)."""
        import preview
        self.put(K.blank_picks(F.EDITION, F.COLLECTED))
        old = S.dump(K.blank_picks("2026-10-07", "2026-10-07T18:04:00+09:00")).encode("utf-8")
        later = S.validate_digest(preview.shift(F.digest(), 1), F.sources())
        self.assertNotEqual((later["date"], later["status"]), (F.EDITION, "withdrawn"))

        def checkout(cmd):
            if "--detach" in cmd:
                S.write_json(os.path.join(self.repo, "data", "digest.json"), later)
                with open(self.path, "wb") as f:
                    f.write(old)
            return 0
        git = MovedMainTest.moved(self, checkout=checkout)
        self.stops("moved", P.publish, self.repo, F.EDITION, run=git)
        self.assertEqual(git.count("push"), 1)

    def test_empty_layer_still_goes_up(self):
        raw = self.put(K.blank_picks(F.EDITION, F.COLLECTED))
        git = MovedMainTest.moved(self)
        self.assertEqual(P.publish(self.repo, F.EDITION, run=git), "pushed")
        self.assertEqual(self.raw(), raw)


class TwoRunsTest(Case):
    def test_the_first_new_run_is_ours(self):
        """시작한 뒤 새 실행이 둘 보이면(뒤따라 누가 또 시작했다) 먼저 생긴 것이 우리 것이다."""
        clock = Clock()
        git = Tool(gh_run_list=[runs((70, "completed", "success")),
                                runs((72, "completed", "failure"), (71, "in_progress", None), (70, "completed", "success")),
                                runs((72, "completed", "failure"), (71, "completed", "success"), (70, "completed", "success"))])
        self.assertEqual(P.dispatch(self.repo, run=git, sleep=clock.sleep, clock=clock.now), "ok")
        self.assertEqual(len(clock.naps), 2)                                  # 뒤의 것이 먼저 끝나도 우리 것을 기다린다


@unittest.skipUnless(shutil.which("git"), "git이 없다")
class RealGitTest(unittest.TestCase):
    """임시 폴더의 진짜 git — 원격은 그 안의 bare 저장소다. gh와 공개 전 검사만 가짜."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.origin, self.pc, self.other = (os.path.join(self.tmp, n) for n in ("origin.git", "pc", "other"))
        self.git(self.tmp, "init", "--quiet", "--bare", "--initial-branch=main", self.origin)
        for repo in (self.pc, self.other):
            self.git(self.tmp, "clone", "--quiet", self.origin, repo)
            for k, v in (("user.name", "fx"), ("user.email", "fx@example.invalid"), ("core.autocrlf", "false"), ("commit.gpgsign", "false")):
                self.git(repo, "config", k, v)
        self.write(self.other, {"sources.json": F.sources(), "digest.json": F.digest(), "digest_overrides.json": F.overrides()})
        self.commit(self.other, "seed")
        self.git(self.pc, "fetch", "--quiet", "origin", "main")
        self.git(self.pc, "checkout", "--quiet", "--detach", "origin/main")
        self.picks = os.path.join(self.pc, "data", K.FILE)

    def git(self, cwd, *args):
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, timeout=120)
        self.assertEqual(r.returncode, 0, (args[:2], r.stderr[-300:]))
        return r.stdout.decode("utf-8", "replace")

    def write(self, repo, docs):
        for name, doc in docs.items():
            S.write_json(os.path.join(repo, "data", name), doc)

    def commit(self, repo, message):
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "--quiet", "-m", message)
        self.git(repo, "push", "--quiet", "origin", "HEAD:main")

    def run_tool(self, cmd, **kw):
        """git은 진짜로(원격이 폴더라 인증 도우미는 불리지 않는다), 공개 전 검사는 통과한 셈으로."""
        if cmd[0] != "git":
            return subprocess.CompletedProcess(cmd, 0, b"", b"")
        return subprocess.run(cmd, **kw)

    def on_main(self, name):
        self.git(self.other, "fetch", "--quiet", "origin", "main")
        return json.loads(self.git(self.other, "show", f"origin/main:data/{name}"))

    def test_first_upload_then_a_leftover_then_nothing_to_do(self):
        S.write_json(self.picks, TK.doc())
        self.assertEqual(P.publish(self.pc, F.EDITION, run=self.run_tool), "pushed")
        self.assertEqual(self.on_main(K.FILE), TK.doc())
        self.assertEqual(self.git(self.pc, "rev-list", "--count", "origin/main").strip(), "2")
        S.write_json(self.picks, K.blank_picks(F.EDITION, F.COLLECTED))        # 커밋 직전에 끊긴 실행: 스테이징만 된 채 남았다
        self.git(self.pc, "add", "--", PATH)
        self.assertTrue(self.git(self.pc, "status", "--porcelain").startswith("M  "))
        P.sync(self.pc, run=self.run_tool)
        self.assertEqual(self.git(self.pc, "status", "--porcelain"), "")
        self.assertEqual(S.read_json(self.picks), TK.doc())
        self.assertEqual(P.publish(self.pc, F.EDITION, run=self.run_tool), "same")

    def test_sentences_do_not_come_back_on_top_of_a_takedown(self):
        """PC가 문장을 써 둔 사이 판이 내려갔다 — push는 거절되고, 새 main(내린 판) 위에는 다시 올리지 않는다."""
        S.write_json(self.picks, TK.doc())
        self.write(self.other, {"digest.json": S.blank_digest(S.parse_iso(F.NOW)), K.FILE: K.blank_picks(F.EDITION, F.NOW)})
        self.commit(self.other, "takedown")
        with self.assertRaises(P.Stop) as cm:
            P.publish(self.pc, F.EDITION, run=self.run_tool)
        self.assertEqual(cm.exception.code, "moved")
        self.assertEqual((self.on_main("digest.json")["status"], self.on_main(K.FILE)["items"]), ("withdrawn", []))
        self.assertEqual(self.git(self.pc, "status", "--porcelain"), "")       # 작업 폴더에도 남기지 않는다
        self.assertEqual(self.git(self.other, "rev-list", "--count", "origin/main").strip(), "2")

    def test_an_unrelated_commit_on_main_is_followed(self):
        S.write_json(self.picks, TK.doc())
        self.write(self.other, {"calendar.json": {"any": 1}})
        self.commit(self.other, "other")
        self.assertEqual(P.publish(self.pc, F.EDITION, run=self.run_tool), "pushed")
        self.assertEqual(self.on_main(K.FILE), TK.doc())
        self.assertEqual(self.git(self.other, "diff", "--name-only", "origin/main~1", "origin/main").strip(), PATH)

    def test_no_commit_is_left_on_a_branch(self):
        self.git(self.pc, "checkout", "--quiet", "-b", "work")
        self.write(self.pc, {"calendar.json": {"any": 1}})
        self.git(self.pc, "add", "-A")
        self.git(self.pc, "commit", "--quiet", "-m", "local work")
        S.write_json(self.picks, TK.doc())
        with self.assertRaises(P.Stop) as cm:
            P.publish(self.pc, F.EDITION, run=self.run_tool)
        self.assertEqual(cm.exception.code, "head")
        self.assertEqual(self.git(self.pc, "rev-list", "--count", "origin/main..HEAD").strip(), "1")       # 그 가지에 커밋을 더하지 않았다


if __name__ == "__main__":
    unittest.main()
