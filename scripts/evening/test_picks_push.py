#!/usr/bin/env python3
"""AI 요약 층 게시(picks_push) 테스트 — 요약 파일 하나만 올리는가, main이 움직였을 때, 규칙판 실행을 기다리기.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요 — git · gh · 공개 전 검사는 모두 가짜 실행기다(부른 명령을 적고 정해 둔 답을 준다). 실제 저장소를 건드리지 않는다.
"""
import os
import shutil
import sys
import tempfile
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_picks as K
import digest_rules as R
import digest_schema as S
import fixtures as F
import picks_push as P
import test_digest_picks as TK

TH = R.TH
PATH = "data/digest_picks.json"
MOD, NEW = f" M {PATH}\n", f"?? {PATH}\n"
PUSH = ["git", "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential", "push", "origin", "HEAD:main"]
MSG = f"data: {F.EDITION} 저녁판 AI 요약"
ON, OFF = '[{"name":"EVENING_ENABLED","value":"true"}]', '[{"name":"EVENING_ENABLED","value":"false"}]'


def name_of(cmd):
    """명령 → 답을 찾는 이름: git의 하위 명령(옵션 -c는 건너뛴다) · "gh run list" · "gh workflow run" · "blind"(공개 전 검사)."""
    if cmd[0] == "gh":
        return " ".join(cmd[:3])
    if cmd[0] != "git":
        return "blind" if cmd[-1].replace("\\", "/").endswith("scripts/check_blind.py") else "other"
    rest = list(cmd[1:])
    while rest and rest[0] == "-c":
        rest = rest[2:]
    return rest[0]


class Tool:
    """가짜 git · gh · 공개 전 검사 — answers = {이름: 답 | [차례로 줄 답들] | 함수}. 답은 종료코드나 (종료코드, 출력), 예외면 던진다.
    정해 두지 않은 명령은 종료코드 0에 빈 출력."""

    def __init__(self, **answers):
        self.calls, self.kw = [], []
        self.answers = {k.replace("_", " ") if k.startswith("gh") else k.replace("_", "-"): v for k, v in answers.items()}

    def __call__(self, cmd, **kw):
        self.calls.append(list(cmd))
        self.kw.append(kw)
        got = self.answers.get(name_of(cmd), 0)
        if callable(got):
            got = got(cmd)
        elif isinstance(got, list):
            got = got.pop(0) if len(got) > 1 else got[0]
        if isinstance(got, BaseException):
            raise got
        code, out = got if isinstance(got, tuple) else (got, "")
        return types.SimpleNamespace(returncode=code, stdout=out.encode("utf-8"), stderr=b"")

    def names(self):
        return [name_of(c) for c in self.calls]

    def count(self, name):
        return self.names().count(name)


class Case(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo, True)
        S.write_json(os.path.join(self.repo, "data", "sources.json"), F.sources())
        S.write_json(os.path.join(self.repo, "data", "digest.json"), F.digest())
        self.put(TK.doc())

    def put(self, doc):
        self.path = os.path.join(self.repo, "data", "digest_picks.json")
        S.write_json(self.path, doc)
        with open(self.path, "rb") as f:
            return f.read()

    def raw(self):
        with open(self.path, "rb") as f:
            return f.read()

    def stops(self, code, fn, *a, **kw):
        with self.assertRaises(P.Stop) as cm:
            fn(*a, **kw)
        self.assertEqual(cm.exception.code, code)
        self.assertEqual(str(cm.exception), code)                  # 메시지는 코드뿐이다


def good(**more):
    """모두 잘 되는 날의 답 — 스위치는 켜져 있고, 작업 폴더는 main의 끝에 있고, 바뀐 것은 요약 파일 하나, 커밋 1개."""
    return {"status": (0, MOD), "rev_parse": lambda cmd: (0, "aaa111\naaa111\n" if "HEAD" in cmd else "aaa111\n"), "rev_list": (0, "1\n"), "diff": (0, PATH + "\n"),
            "gh_variable_list": (0, ON), **more}


class PublishTest(Case):
    def test_one_file_one_commit_one_push(self):
        git = Tool(**good())
        self.assertEqual(P.publish(self.repo, F.EDITION, run=git), "pushed")
        self.assertEqual(git.names(), ["status", "blind", "rev-parse", "add", "commit", "rev-list", "diff", "push"])
        self.assertEqual(git.calls[-1], PUSH)
        self.assertEqual(git.calls[3], ["git", "add", "--", PATH])
        self.assertEqual(git.calls[4], ["git", "commit", "--quiet", "-m", MSG, "--", PATH])
        self.assertEqual(git.calls[5], ["git", "rev-list", "--count", "origin/main..HEAD"])
        self.assertEqual(git.calls[6][-3:], ["--name-only", "origin/main", "HEAD"])
        self.assertTrue(all(kw["cwd"] == self.repo for kw in git.kw))
        self.assertEqual(git.calls[1][-1].replace("\\", "/"), "scripts/check_blind.py")

    def test_first_upload_is_an_untracked_file(self):
        self.assertEqual(P.publish(self.repo, F.EDITION, run=Tool(**good(status=(0, NEW)))), "pushed")

    def test_nothing_changed_means_nothing_to_do(self):
        git = Tool(**good(status=(0, "")))
        self.assertEqual(P.publish(self.repo, F.EDITION, run=git), "same")
        self.assertEqual(git.names(), ["status"])

    def test_another_file_in_the_tree_stops_before_anything_is_staged(self):
        for name, out in {"다른 파일": MOD + " M data/digest.json\n", "다른 파일만": " M site/evening.js\n", "새 파일": MOD + "?? note.txt\n",
                          "이미 올려 둔 것": f"M  {PATH}\n", "이름이 바뀐 것": f"R  data/x.json -> {PATH}\n",
                          "비슷한 이름": " M data/digest_picks.json.bak\n"}.items():
            with self.subTest(name):
                git = Tool(**good(status=(0, out)))
                self.stops("scope", P.publish, self.repo, F.EDITION, run=git)
                self.assertEqual(git.names(), ["status"])

    def test_two_commits_or_another_file_in_the_commit_stops_before_the_push(self):
        for name, more in {"커밋 2개": {"rev_list": (0, "2\n")}, "커밋 0개": {"rev_list": (0, "0\n")},
                           "다른 파일이 든 커밋": {"diff": (0, PATH + "\ndata/digest.json\n")}, "빈 커밋": {"diff": (0, "")},
                           "셈을 못 함": {"rev_list": (1, "")}}.items():
            with self.subTest(name):
                git = Tool(**good(**more))
                self.stops("commits", P.publish, self.repo, F.EDITION, run=git)
                self.assertEqual(git.count("push"), 0)

    def test_a_file_that_fails_its_own_check_is_never_committed(self):
        item = TK.doc()["items"][0]
        broken = {"권유가 든 문장": TK.doc(items=[{**item, "fact": "국고채 10년물은 지금 매수할 만하다."}]),
                  "원천이 아닌 채널의 글": TK.doc(items=[{**item, "src": [["fxpers1", 3001]]}]), "형식이 아님": {"schema": 1}}
        for name, d in broken.items():
            with self.subTest(name):
                S.write_json(self.path, d)
                git = Tool(**good())
                self.stops("file", P.publish, self.repo, F.EDITION, run=git)
                self.assertEqual(git.names(), ["status"])
        with open(self.path, "wb") as f:                           # 보기 좋게 다시 쓴 것 · 끝에 덧붙인 글자 — 검사한 자료와 나가는 바이트가 다르다
            f.write(S.dump(TK.doc()).encode("utf-8") + b"\n" + F.CANARIES[0].encode("utf-8"))
        self.stops("file", P.publish, self.repo, F.EDITION, run=Tool(**good()))
        self.put(TK.doc())
        self.stops("file", P.publish, self.repo, "2026-10-09", run=Tool(**good()))        # 올린다는 판 날짜와 파일의 날짜가 다르다

    def test_blind_check_failure_restores_the_file_and_stops(self):
        for status, undo in ((MOD, ["git", "checkout", "--quiet", "--", PATH]), (NEW, None)):
            with self.subTest(status):
                self.put(TK.doc())
                git = Tool(**good(status=(0, status), blind=1))
                self.stops("blind", P.publish, self.repo, F.EDITION, run=git)
                self.assertEqual((git.count("commit"), git.count("add"), git.count("push")), (0, 0, 0))
                if undo:
                    self.assertEqual(git.calls[-1], undo)
                else:
                    self.assertFalse(os.path.exists(self.path))     # 새 파일이면 지운다
        self.put(TK.doc())
        self.stops("blind", P.publish, self.repo, F.EDITION, run=Tool(**good(blind=2)))   # 검사 불가(검사어 없음)도 통과가 아니다

    def test_commit_failure_stops(self):
        for fail in ("commit", "add"):
            with self.subTest(fail):
                git = Tool(**good(**{fail: 1}))
                self.stops("commit", P.publish, self.repo, F.EDITION, run=git)
                self.assertEqual(git.count("push"), 0)
                self.assertEqual(git.calls[-1], ["git", "reset", "--quiet", "--", PATH])     # 스테이징을 풀고 멈춘다 — 다음 실행이 dirty로 막히지 않게


class MovedMainTest(Case):
    def moved(self, **more):
        """첫 push가 거절되고, 다시 받아 보니 main이 움직여 있다. 새 main으로 옮기면 파일은 그쪽 것(옛 내용)으로 돌아간다."""
        old = S.dump(K.blank_picks("2026-10-07", "2026-10-07T18:04:00+09:00")).encode("utf-8")

        def checkout(cmd):
            if "--detach" in cmd:
                with open(self.path, "wb") as f:
                    f.write(old)
            return 0
        return Tool(**{**good(rev_parse=[(0, "aaa111\naaa111\n"), (0, "bbb222\n")], push=[1, 0], checkout=checkout), **more})

    def test_same_file_is_committed_again_on_the_new_main(self):
        want = self.raw()
        git = self.moved()
        self.assertEqual(P.publish(self.repo, F.EDITION, run=git), "pushed")
        self.assertEqual(git.names(), ["status", "blind", "rev-parse", "add", "commit", "rev-list", "diff", "push",
                                       "fetch", "rev-parse", "checkout", "status", "add", "commit", "rev-list", "diff", "push"])
        self.assertEqual(git.calls[8], ["git", "fetch", "--quiet", "origin", "main"])
        self.assertEqual(git.calls[10], ["git", "checkout", "--quiet", "--detach", "origin/main"])
        self.assertEqual(self.raw(), want)                         # 다시 만들지 않고 같은 바이트를 새 main 위에 올린다
        self.assertEqual(git.count("blind"), 1)

    def test_only_one_more_try(self):
        git = self.moved(push=1)
        self.stops("push", P.publish, self.repo, F.EDITION, run=git)
        self.assertEqual(git.count("push"), 2)

    def test_push_refused_while_main_stood_still_is_not_retried(self):
        git = Tool(**good(push=1))
        self.stops("push", P.publish, self.repo, F.EDITION, run=git)
        self.assertEqual((git.count("push"), git.count("checkout")), (1, 0))       # 인증 · 훅 · 네트워크 — 다시 해도 같다

    def test_new_main_already_has_the_same_file(self):
        git = self.moved(status=[(0, MOD), (0, "")])
        self.assertEqual(P.publish(self.repo, F.EDITION, run=git), "same")
        self.assertEqual(git.count("push"), 1)

    def test_scope_is_checked_again_on_the_new_main(self):
        git = self.moved(rev_list=[(0, "1\n"), (0, "2\n")])
        self.stops("commits", P.publish, self.repo, F.EDITION, run=git)
        self.assertEqual(git.count("push"), 1)
        git = self.moved(status=[(0, MOD), (0, MOD + " M data/digest.json\n")])
        self.stops("scope", P.publish, self.repo, F.EDITION, run=git)

    def test_fetch_failure_after_a_refused_push(self):
        self.stops("fetch", P.publish, self.repo, F.EDITION, run=Tool(**good(push=1, fetch=1)))


class SyncTest(Case):
    def test_clean_folder_moves_to_the_tip_of_main(self):
        git = Tool(status=(0, ""))
        P.sync(self.repo, run=git)
        self.assertEqual(git.calls, [["git", "-c", "core.quotePath=false", "status", "--porcelain", "--untracked-files=all"],
                                     ["git", "fetch", "--quiet", "origin", "main"],
                                     ["git", "checkout", "--quiet", "--detach", "origin/main"]])

    def test_leftover_of_a_failed_run_is_put_back_first(self):
        git = Tool(status=(0, MOD))
        P.sync(self.repo, run=git)
        self.assertEqual(git.calls[1], ["git", "checkout", "--quiet", "--", PATH])
        self.assertEqual(git.names(), ["status", "checkout", "fetch", "checkout"])
        git = Tool(status=(0, NEW))
        P.sync(self.repo, run=git)
        self.assertFalse(os.path.exists(self.path))
        self.assertEqual(git.names(), ["status", "fetch", "checkout"])

    def test_anything_else_in_the_folder_is_left_alone(self):
        """게시 전용 폴더가 아닌 곳(작업 중인 폴더)을 잘못 준 날 — 남의 변경을 버리지 않고 멈춘다."""
        for out in (" M site/evening.js\n", MOD + "?? scripts/evening/new.py\n", f"M  {PATH}\nM  data/digest.json\n", f"R  data/x.json -> {PATH}\n",
                    f"D  {PATH}\n", f" D {PATH}\n"):
            with self.subTest(out):
                git = Tool(status=(0, out))
                self.stops("dirty", P.sync, self.repo, run=git)
                self.assertEqual(git.names(), ["status"])
        self.assertTrue(os.path.exists(self.path))

    def test_git_failures_have_their_own_codes(self):
        self.stops("status", P.sync, self.repo, run=Tool(status=1))
        self.stops("fetch", P.sync, self.repo, run=Tool(status=(0, ""), fetch=1))
        self.stops("detach", P.sync, self.repo, run=Tool(status=(0, ""), checkout=1))
        self.stops("git", P.sync, self.repo, run=Tool(status=FileNotFoundError("git")))


class Clock:
    def __init__(self):
        self.t, self.naps = 0.0, []

    def sleep(self, s):
        self.naps.append(s)
        self.t += s

    def now(self):
        return self.t


def runs(*rows):
    return (0, S.dump([{"databaseId": i, "status": st, "conclusion": c} for i, st, c in rows]))


class DispatchTest(Case):
    def go(self, git):
        clock = Clock()
        return P.dispatch(self.repo, run=git, sleep=clock.sleep, clock=clock.now), clock

    def test_starts_the_rules_run_and_waits_for_it(self):
        git = Tool(gh_run_list=[runs((70, "completed", "success")), runs((70, "completed", "success")),
                                runs((71, "queued", None), (70, "completed", "success")),
                                runs((71, "in_progress", None), (70, "completed", "success")),
                                runs((71, "completed", "success"), (70, "completed", "success"))])
        got, clock = self.go(git)
        self.assertEqual(got, "ok")
        self.assertEqual(git.calls[1], ["gh", "workflow", "run", "evening.yml", "--ref", "main"])
        self.assertEqual(git.calls[0], ["gh", "run", "list", "--workflow", "evening.yml", "--event", "workflow_dispatch", "--branch", "main",
                                        "--limit", "5", "--json", "databaseId,status,conclusion"])
        self.assertEqual(clock.naps, [TH["dispatch_poll_s"]] * 4)
        self.assertEqual((TH["dispatch_poll_s"], TH["dispatch_wait_s"]), (30, 720))

    def test_a_failed_run_is_reported_but_is_not_an_error(self):
        git = Tool(gh_run_list=[runs((70, "completed", "success")), runs((71, "completed", "failure"), (70, "completed", "success"))])
        self.assertEqual(self.go(git)[0], "failed")

    def test_an_older_run_is_not_mistaken_for_ours(self):
        git = Tool(gh_run_list=[runs((70, "in_progress", None)), runs((70, "completed", "success"))])
        got, clock = self.go(git)
        self.assertEqual(got, "timeout")                            # 우리 실행(70보다 뒤의 것)은 끝내 보이지 않았다
        self.assertEqual(sum(clock.naps), TH["dispatch_wait_s"])

    def test_gives_up_after_twelve_minutes(self):
        git = Tool(gh_run_list=[runs(), runs((71, "in_progress", None))])
        got, clock = self.go(git)
        self.assertEqual((got, len(clock.naps)), ("timeout", TH["dispatch_wait_s"] // TH["dispatch_poll_s"]))

    def test_cannot_start(self):
        self.assertEqual(self.go(Tool(gh_run_list=runs(), gh_workflow_run=1))[0], "error")
        self.assertEqual(self.go(Tool(gh_run_list=1))[0], "error")
        self.assertEqual(self.go(Tool(gh_run_list=FileNotFoundError("gh")))[0], "error")
        self.assertEqual(self.go(Tool(gh_run_list=(0, "not json " + F.CANARIES[0])))[0], "error")
        git = Tool(gh_run_list=runs(), gh_workflow_run=1)
        self.go(git)
        self.assertEqual(git.names(), ["gh run list", "gh workflow run"])        # 시작하지 못했으면 기다리지 않는다

    def test_a_bad_poll_is_just_another_wait(self):
        git = Tool(gh_run_list=[runs(), 1, (0, "{}"), runs((71, "completed", "success"))])
        got, clock = self.go(git)
        self.assertEqual((got, len(clock.naps)), ("ok", 3))


if __name__ == "__main__":
    unittest.main()
