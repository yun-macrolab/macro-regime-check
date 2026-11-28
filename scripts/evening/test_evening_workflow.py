#!/usr/bin/env python3
"""저녁 워크플로(.github/workflows/evening.yml)의 정적 검사 — 트리거, 권한, 액션 고정, 읽는 잡과 쓰는 잡의 경계.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요 — 파일의 글자만 본다(YAML 라이브러리를 쓰지 않는다. 들여쓰기로 잡을 가른다).
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PIN = re.compile(r"^[\w.-]+/[\w.-]+@[0-9a-f]{40} # v\d+\.\d+\.\d+$")
# data/digest_picks.json(PC가 올리는 AI 요약 층)은 여기 없다: 그 push마다 daily(push — 배포)와 이 워크플로(push — check뿐)가 같은
# concurrency 그룹에 함께 서는데, 그룹에는 기다리는 실행이 하나만 남는다 — 셋째 실행이 오면 기다리던 배포가 취소될 수 있다(2026-10-09 검토)
PATHS = ["scripts/evening/**", "site/evening.*", "data/sources.json", "data/calendar.json", ".github/workflows/evening.yml"]
COLLECT_CRON, WATCH_CRON = "41 8 * * 1-5", "41 13 * * 1-5"
ON = "vars.EVENING_ENABLED == 'true'"            # 켜는 스위치 — 변수가 없으면 꺼져 있다
# 알림: 수집이 알린 날 · 이어서 안 읽힌 채널이 있는 날(경고만) · Pages 올리기·배포가 실패한 날
ALERT_IF = ("always() && (needs.collect.outputs.alert == 'true' || needs.collect.outputs.stale != '' || "
            "needs.publish.result == 'failure' || needs.pages_build.result == 'failure' || needs.deploy.result == 'failure')")


def read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
        return f.read()


def code(text):
    """주석만 있는 줄을 뺀 글."""
    return "\n".join(x for x in text.split("\n") if not x.lstrip().startswith("#"))


def jobs(text):
    """{잡 이름: 그 잡의 글} — jobs: 아래 두 칸 들여쓴 이름으로 가른다."""
    out, name = {}, None
    for line in text.split("\njobs:\n", 1)[1].split("\n"):
        m = re.fullmatch(r"  ([a-z_]+):", line)
        if m:
            name = m.group(1)
            out[name] = []
        elif name:
            out[name].append(line)
    return {k: "\n".join(v) for k, v in out.items()}


def uses(text):
    return re.findall(r"^\s*(?:- )?uses: (.+)$", text, re.M)


def run_blocks(text):
    """run:의 내용들 — 한 줄짜리와 여러 줄(| · >-) 모두."""
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        m = re.match(r"^(\s*)run:\s*(.*)$", lines[i])
        i += 1
        if not m:
            continue
        if m.group(2) not in ("|", "|-", ">", ">-"):
            out.append(m.group(2))
            continue
        block = []
        while i < len(lines) and (not lines[i].strip() or len(lines[i]) - len(lines[i].lstrip()) > len(m.group(1))):
            block.append(lines[i])
            i += 1
        out.append("\n".join(block))
    return out


def permissions(job):
    """잡의 permissions: 아래 칸들. 없으면 None(워크플로의 것을 물려받는다)."""
    m = re.search(r"^    permissions:\n((?:      .+\n)+)", job, re.M)
    if not m:
        return None
    return dict(re.match(r"\s*([\w-]+): (\w+)", line).groups() for line in m.group(1).rstrip("\n").split("\n"))


def condition(job):
    """잡의 if: 식(여러 줄이면 이어 붙인다)."""
    m = re.search(r"^    if: (>-\n(?:      .+\n)+|.+\n)", job, re.M)
    return " ".join(m.group(1).replace(">-", "").split()) if m else ""


class WorkflowCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(".github", "workflows", "evening.yml")
        cls.daily = read(".github", "workflows", "daily.yml")
        cls.jobs = {k: code(v) for k, v in jobs(cls.text).items()}


class TriggerTest(WorkflowCase):
    def test_jobs(self):
        self.assertEqual(list(self.jobs), ["check", "collect", "publish", "takedown", "watch", "pages_build", "deploy", "alert"])
        self.assertIn("\nname: evening\n", self.text)

    def test_two_schedules_on_weekdays(self):
        self.assertEqual(re.findall(r'- cron: "([^"]+)"', self.text), [COLLECT_CRON, WATCH_CRON])
        self.assertIn(f"github.event.schedule == '{COLLECT_CRON}'", condition(self.jobs["collect"]))
        self.assertIn(f"github.event.schedule == '{WATCH_CRON}'", condition(self.jobs["watch"]))
        self.assertNotIn(WATCH_CRON, self.jobs["collect"])
        self.assertNotIn(COLLECT_CRON, self.jobs["watch"])

    def test_collect_tells_the_pipeline_which_event_started_it(self):
        # 예약 실행은 판의 저녁(평일 17:30 ~ 이튿날 06:00 KST) 밖이면 수집하지 않는다(evening_run.py --event — 2026-11-10 점검 ep-03).
        # 이벤트 이름은 Actions가 넣어 주는 환경 변수로 넘긴다(run 안에 표현식을 쓰지 않는다)
        (block,) = [b for b in run_blocks(self.jobs["collect"]) if "evening_run.py pipeline" in b]
        self.assertIn('--event "$GITHUB_EVENT_NAME"', block)

    def test_manual_run_has_a_takedown_switch(self):
        block = self.text.split("  workflow_dispatch:\n", 1)[1].split("\npermissions:", 1)[0]
        self.assertRegex(block, r"inputs:\n\s+takedown:\n(?:\s+.+\n)*?\s+type: boolean\n\s+default: false")

    def test_push_runs_only_the_check(self):
        block = self.text.split("\non:\n", 1)[1].split("  schedule:", 1)[0]
        self.assertIn("    branches: [main]\n", block)
        self.assertEqual(re.findall(r'^      - "(.+)"$', block, re.M), PATHS)
        for name in ("collect", "publish", "takedown", "watch"):          # push에서는 어느 것도 조건이 맞지 않는다
            self.assertRegex(condition(self.jobs[name]), r"github\.event_name == '(schedule|workflow_dispatch)'|needs\.collect", name)
        self.assertNotIn("github.event_name == 'push'", "".join(condition(self.jobs[n]) for n in self.jobs))

    def test_same_concurrency_group_as_the_morning(self):
        want = "\nconcurrency:\n  group: daily\n  cancel-in-progress: false\n"
        self.assertIn(want, self.text)
        self.assertIn(want, self.daily)

    def test_both_workflows_start_from_the_commit_their_check_saw(self):
        # 예약·수동 실행의 check는 가지의 지금 끝을 받아 그 커밋을 뒤 잡에 넘긴다 — 아침도 저녁과 같게(2026-11-10 점검 shell-06:
        # 실행이 걸린 때의 커밋에서 시작한 아침 update는, 기다리던 수동 재실행에서 앞 실행의 봇 커밋과 data/status.json rebase 충돌을 냈다)
        ref = "ref: ${{ github.event_name == 'push' && github.sha || github.ref }}"
        record = 'run: echo "sha=$(git rev-parse HEAD)" >> "$GITHUB_OUTPUT"'
        morning = {k: code(v) for k, v in jobs(self.daily).items()}
        for name, wf in (("evening", self.jobs), ("daily", morning)):
            check = wf["check"]
            self.assertIn("    outputs:\n      sha: ${{ steps.sha.outputs.sha }}\n", check, name)
            self.assertIn(ref, check, name)
            self.assertIn(record, check, name)
            self.assertLess(check.index(ref), check.index("id: sha"), name)
            self.assertLess(check.index("id: sha"), check.index("scripts/check_blind.py"), name)   # 기록한 커밋 = 검사한 커밋
        update = morning["update"]
        self.assertIn("ref: ${{ needs.check.outputs.sha }}", update[update.index("actions/checkout@"):update.index("actions/setup-python@")])
        for name in ("collect", "publish", "takedown", "watch"):
            self.assertIn("ref: ${{ needs.check.outputs.sha }}", self.jobs[name], name)
        # 봇 커밋 단계의 옛 주석 — rebase로 딸려 온 커밋은 그 실행의 공개 전 검사를 거치지 않는다(올린 쪽의 검사와 제 실행의 check를 거친다)
        for text in (self.text, self.daily):
            self.assertNotIn("검사를 거친 이 커밋", text)
            self.assertIn("rebase로 딸려 온 커밋", text)


class PermissionTest(WorkflowCase):
    def test_default_is_read_only(self):
        self.assertIn("\npermissions:\n  contents: read\n", self.text)

    def test_only_the_two_commit_jobs_can_write_the_repository(self):
        got = {name: permissions(job) for name, job in self.jobs.items()}
        self.assertEqual(got, {"check": None, "collect": {"contents": "read"}, "publish": {"contents": "write"},
                               "takedown": {"contents": "write"}, "watch": {"contents": "read"},
                               "pages_build": {"contents": "read"},                          # 올리기는 읽기뿐 — Pages·OIDC는 배포 잡에만
                               "deploy": {"pages": "write", "id-token": "write"}, "alert": None})
        for name, job in self.jobs.items():
            self.assertEqual("git push" in job, name in ("publish", "takedown"), name)
            self.assertEqual("git commit" in job, name in ("publish", "takedown"), name)

    def test_write_jobs_run_on_main_only(self):
        for name in ("publish", "takedown"):
            self.assertIn("github.ref == 'refs/heads/main'", condition(self.jobs[name]), name)
            self.assertIn("git push --quiet origin HEAD:main", self.jobs[name])
        self.assertIn(ON, condition(self.jobs["publish"]))
        self.assertNotIn("EVENING_ENABLED", condition(self.jobs["takedown"]))          # 꺼 둔 동안에도 내릴 수 있어야 한다
        # rebase로 main의 새 커밋을 받았으면(처음·재시도 모두) push 전에 최종 트리로 공개 전 검사를 다시 돈다 — 아침의 봇 커밋도 같다
        morning = code(jobs(self.daily)["update"])
        for name, job in (("publish", self.jobs["publish"]), ("takedown", self.jobs["takedown"]), ("daily update", morning)):
            step = job[job.index("- name: 봇 커밋"):]
            step = step.split("\n      - ", 1)[0]                                      # 봇 커밋 단계만(다음 단계 앞까지)
            self.assertRegex(step, r"id: commit\n\s+env:\n\s+BLIND_PATTERNS: \$\{\{ secrets\.BLIND_PATTERNS \}\}", name)
            func = step[step.index("pull_checked() {"):step.index("\n          }\n")]
            at = [func.index(x) for x in ('before="$(git rev-parse HEAD)"', "git pull --quiet --rebase origin main",
                                           'if [ "$(git rev-parse HEAD)" != "$before" ]; then',
                                           "git fetch --quiet origin '+refs/notes/*:refs/notes/*'", "python scripts/check_blind.py")]
            self.assertEqual(at, sorted(at), name)                                     # 새 커밋을 받았을 때만, push 전에
            rest = step.replace(func, "")
            self.assertNotIn("git pull", rest, name)                                   # 검사 없이 rebase하는 길이 없다
            calls = [line.split("#")[0].strip() for line in rest.split("\n") if line.strip().startswith("pull_checked")]
            self.assertEqual(calls, ["pull_checked", "pull_checked"], name)            # 처음 한 번 + 밀렸을 때 한 번
            self.assertLess(rest.index("pull_checked"), rest.index("git push --quiet origin HEAD:main"), name)

    def test_nothing_runs_on_schedule_until_it_is_switched_on(self):
        """저장소 변수 EVENING_ENABLED가 true일 때만 예약 수집 · 게시 · 감시가 돈다 — 변수를 안 넣은 저장소(main에 막 합친 날)는 꺼져 있다.
        꺼 둔 동안에는 수집 요청도, 아티팩트도, 실패 메일도 없다(게시만 끄면 판이 아티팩트로 남는다)."""
        collect = condition(self.jobs["collect"])
        self.assertIn(f"(github.event_name == 'schedule' && github.event.schedule == '{COLLECT_CRON}' && {ON} && "
                      "needs.check.outputs.skip != 'true')", collect)                    # 오늘 판이 이미 있으면 예약 수집은 건너뛴다
        self.assertIn("(github.event_name == 'workflow_dispatch' && inputs.takedown != true)", collect)     # 수동 실행은 시험용으로 남긴다
        self.assertEqual(collect.count("EVENING_ENABLED"), 1)
        for name in ("publish", "watch"):
            self.assertIn(ON, condition(self.jobs[name]), name)
        self.assertNotIn("!= 'false'", code(self.text))                                 # '꺼 두지 않았으면 켜짐'은 어디에도 없다
        self.assertEqual(condition(self.jobs["alert"]), ALERT_IF)      # 수집이 안 돌면 수집 알림도 없다(배포 실패는 감시·내리기의 배포도 알린다)

    def test_takedown_from_another_branch_fails_instead_of_doing_nothing(self):
        check = self.jobs["check"]
        self.assertRegex(check, r"if: inputs\.takedown == true && github\.ref != 'refs/heads/main'\n\s+run: \|\n(?:\s+.+\n)*?\s+exit 1\n")
        self.assertLess(check.index("github.ref != 'refs/heads/main'"), check.index("actions/checkout"))    # 맨 앞에서 멈춘다


class PinTest(WorkflowCase):
    def test_every_action_is_pinned_to_a_commit(self):
        found = uses(self.text)
        self.assertGreaterEqual(len(found), 14)
        for u in found:
            self.assertRegex(u, PIN)

    def test_shared_actions_use_the_same_commits_as_the_morning(self):
        morning = dict(u.split(" # ")[0].split("@") for u in uses(self.daily))
        mine = {}
        for u in uses(self.text):
            name, sha = u.split(" # ")[0].split("@")
            self.assertEqual(mine.setdefault(name, sha), sha, name)             # 한 액션은 한 커밋으로만
        self.assertEqual({k: v for k, v in mine.items() if k in morning}, morning)
        self.assertEqual(sorted(set(mine) - set(morning)), ["actions/download-artifact", "actions/upload-artifact"])

    def test_no_cache(self):
        self.assertNotIn("actions/cache", code(self.text))


class BoundaryTest(WorkflowCase):
    """읽는 잡에는 쓰기 권한·Secret이 없고, 쓰는 잡은 원문을 받지 않는다."""

    def test_collect_has_no_secret_and_no_write(self):
        job = self.jobs["collect"]
        for word in ("secrets.", "BLIND_PATTERNS", "contents: write", "check_blind", "id-token", "pages:"):
            self.assertNotIn(word, job, word)
        self.assertIn("persist-credentials: false", job)
        self.assertNotIn("${{ secrets", self.jobs["watch"] + self.jobs["alert"] + self.jobs["pages_build"] + self.jobs["deploy"])

    def test_only_the_public_folder_becomes_an_artifact(self):
        job = self.jobs["collect"]
        self.assertIn("--work .work/evening --out _evening --data data", job)
        step = job.split("actions/upload-artifact", 1)[1]
        paths = re.search(r"\n\s+path: \|\n((?:\s+_evening/\S+\n)+)", step)
        self.assertEqual(paths.group(1).split(), ["_evening/digest.json", "_evening/digest_*.json", "_evening/digest/*.json"])    # 폴더 통째가 아니다
        self.assertNotIn(".work", step)
        self.assertIn("if-no-files-found: error", step)
        self.assertIn("retention-days: 1\n", step)                                      # 내린 뒤에도 남는 사본은 하루만
        before = job.split("actions/upload-artifact", 1)[0].rsplit("- name:", 1)[1]
        self.assertIn(f"if: steps.run.outputs.publish == 'true' && {ON} && github.ref == 'refs/heads/main'", before)    # 게시할 때만 올린다
        self.assertEqual(self.text.count("actions/upload-artifact@"), 1)        # 올리는 곳은 한 곳뿐
        self.assertNotIn("include-hidden-files", self.text)

    def test_publish_never_sees_the_raw_folder(self):
        job = self.jobs["publish"]
        for word in (".work", "tg_collect", "evening_run.py", "--raw"):
            self.assertNotIn(word, job, word)
        self.assertRegex(job, r"actions/download-artifact@[0-9a-f]{40}[^\n]*\n\s+with:\n\s+name: evening-public\n\s+path: _evening\n")
        order = ["actions/download-artifact", "digest_check.py --public _evening --strict", "digest_publish.py --from _evening --data data",
                 "python scripts/check_blind.py", "git add data", "git commit", "git push"]
        at = [job.index(x) for x in order]
        self.assertEqual(at, sorted(at))
        self.assertNotIn(".work", "".join(self.jobs[n] for n in ("takedown", "watch", "pages_build", "deploy", "alert", "check")))

    def test_takedown_does_not_lean_on_the_evening_tests(self):
        job, check = self.jobs["takedown"], self.jobs["check"]
        self.assertEqual(condition(job), "github.event_name == 'workflow_dispatch' && inputs.takedown == true && "
                                         "github.ref == 'refs/heads/main'")
        self.assertIn("python scripts/evening/digest_build.py --blank --out data --data data", job)
        for word in ("unittest", "tg_collect", "evening_run.py", "download-artifact", "digest_publish"):
            self.assertNotIn(word, job, word)
        at = [job.index(x) for x in ("digest_build.py --blank", "python scripts/check_blind.py", "git commit")]
        self.assertEqual(at, sorted(at))
        # 빈 판조차 못 만드는 날(저녁 코드가 깨진 날)에도 내려간다 — 그때는 저녁판 파일만 지운다
        self.assertRegex(job, r"id: blank\n\s+continue-on-error: true\n\s+run: python scripts/evening/digest_build\.py --blank")
        self.assertIn("if: steps.blank.outcome == 'failure'", job)
        removed = [p for line in job.split("\n") if line.strip().startswith("rm ") for p in line.split()[2:]]
        self.assertEqual(removed, ["data/digest.json", "data/digest_index.json", "data/digest_state.json", "data/digest_status.json",
                                   "data/digest_picks.json", "data/digest"])            # AI 요약 층도 함께 내려간다
        self.assertRegex(check, r"name: 저녁 테스트\n\s+if: inputs\.takedown != true[^\n]*\n"
                                r"\s+run: python -m unittest discover -s scripts/evening\n")
        self.assertRegex(check, r"name: 공개 전 검사\n\s+env:\n\s+BLIND_PATTERNS: [^\n]+\n\s+run: python scripts/check_blind\.py\n")
        self.assertIn("inputs.takedown != true", condition(self.jobs["collect"]))

    def test_watch_collects_nothing(self):
        job = self.jobs["watch"]
        self.assertIn("- name: 나왔어야 할 판이 main과 공개 페이지에 있는지", job)  # 오늘 판이 아니다 — 22:41이 지난 마지막 평일의 판(ep-03)
        self.assertIn("evening_run.py watch --data data", job)
        self.assertIn('--page-url "https://${GITHUB_REPOSITORY_OWNER}.github.io/${GITHUB_REPOSITORY#*/}"', job)
        for word in ("pipeline", "tg_collect", "t.me", "upload-artifact", "git "):
            self.assertNotIn(word, job, word)
        self.assertIn(ON, condition(job))

    def test_deploy_is_the_mornings_deploy(self):
        # 올리기(pages_build)와 배포(deploy)는 다른 잡이다 — 같은 잡에서 올린 직후의 배포가 아티팩트를 못 찾았다(actions/deploy-pages#451)
        build, morning_build = self.jobs["pages_build"], code(jobs(self.daily)["pages_build"])
        job, morning = self.jobs["deploy"], code(jobs(self.daily)["deploy"])
        self.assertIn("needs: [check, publish, takedown, watch]", build)
        for out in ("needs.publish.outputs.publish == 'true'", "needs.takedown.outputs.publish == 'true'",
                    "needs.watch.outputs.redeploy == 'true'", "always()", "needs.check.result == 'success'"):
            self.assertIn(out, condition(build))
        gate = [b for b in run_blocks(morning_build) if "FETCH_HEAD" in b]      # 아침 push 실행만 보는 'main이 앞서 나갔는지' 단계
        self.assertEqual(len(gate), 1)                                          # (저녁에는 push로 배포하는 길이 없다 — 2026-11-04 push-4)
        self.assertEqual(run_blocks(build), [b for b in run_blocks(morning_build) if b not in gate])   # site/ + data/만 조립한다
        self.assertEqual(uses(build), uses(morning_build))
        self.assertEqual(permissions(build), permissions(morning_build))
        self.assertIn("needs: [pages_build]", job)
        self.assertIn("needs.pages_build.result == 'success'", condition(job))
        self.assertEqual(run_blocks(job), run_blocks(morning))                  # 배포 실패면 30초 쉬고 한 번만 다시
        self.assertEqual(uses(job), uses(morning))
        self.assertEqual(permissions(job), permissions(morning))
        self.assertRegex(job, r"- id: deployment\n\s+continue-on-error: true\n\s+uses: actions/deploy-pages@")
        self.assertRegex(job, r"- id: deployment_retry\n\s+if: steps\.deployment\.outcome == 'failure'\n\s+uses: actions/deploy-pages@")
        self.assertNotIn("upload-pages-artifact", job)
        self.assertNotIn("deploy-pages", build)

    def test_alert_ends_the_run_as_failed(self):
        job = self.jobs["alert"]
        self.assertEqual(condition(job), ALERT_IF)
        self.assertIn("needs: [collect, publish, pages_build, deploy]", job)  # 게시·배포를 마친 뒤에 끝낸다
        self.assertRegex(run_blocks(job)[0], r"exit 1\s*$")
        # 판을 못 냈거나 반쯤 낸 것 · 배포 실패만 실행을 실패로(bad) — 판은 나간 날의 정보성 사유는 경고만(note, exit 0). 사유는 모두 적는다
        self.assertRegex(run_blocks(job)[0], r'if \[ "\$fail" = 0 \]; then\n\s+exit 0')
        self.assertIn("for r in $REASONS; do", job)
        for reason, how in (("short", "bad"), ("broken", "bad"), ("empty_streak", "note"), ("title", "note"), ("rewind", "note"),
                            ("channel", "note")):
            self.assertIn(f"            {reason}) {how} ", job, reason)
        self.assertIn("GITHUB_STEP_SUMMARY", job)
        # 게시가 실패하면 오류(사이트는 직전 판), '판은 나갔다'는 게시 잡이 성공한 때만
        self.assertIn("PUBLISH: ${{ needs.publish.result }}", job)
        self.assertRegex(job, r'if \[ "\$PUBLISH" = "failure" \]; then\n\s+bad "판을 게시하지 못했다[^"]*사이트는 직전 판')
        self.assertRegex(job, r'if \[ "\$PUBLISH" = "success" \]; then\n\s+out="판은 나갔다"')
        self.assertEqual(job.count("판은 나갔다"), 1)                                   # 경고 문구는 $out으로만
        for reason in ("short", "empty_streak", "broken", "channel"):
            self.assertIn(f"            {reason}) ", job)
        for hint in ("title_sha=", "한 판 동안 목록에서", "오늘 안에 수동 실행"):          # 무엇을 하면 풀리는지 알림에 적는다
            self.assertIn(hint, job, hint)


class ShellTest(WorkflowCase):
    def test_no_expression_inside_run(self):
        blocks = run_blocks(self.text)
        self.assertGreaterEqual(len(blocks), 14)
        for b in blocks:
            self.assertNotIn("${{", b)
        self.assertNotIn("${{", "\n".join(x for x in self.text.split("\n") if x.lstrip().startswith("#")))     # 주석에도 두지 않는다

    def test_scripts_named_in_the_workflow_exist(self):
        names = set(re.findall(r"python (scripts/[\w/]+\.py)", self.text))
        self.assertEqual(names, {"scripts/check_blind.py", "scripts/evening/evening_run.py", "scripts/evening/digest_check.py",
                                 "scripts/evening/digest_publish.py", "scripts/evening/digest_build.py"})
        for n in names:
            self.assertTrue(os.path.isfile(os.path.join(REPO, *n.split("/"))), n)


class LayoutTest(WorkflowCase):
    def test_morning_discover_does_not_pick_up_evening_tests(self):
        self.assertFalse(os.path.exists(os.path.join(HERE, "__init__.py")))
        self.assertIn("python -m unittest discover -s scripts\n", self.daily)
        found = unittest.TestLoader().discover(os.path.join(REPO, "scripts"), pattern="test_digest_*.py")
        self.assertEqual(found.countTestCases(), 0)

    def test_takedown_issue_template(self):
        text = read(".github", "ISSUE_TEMPLATE", "takedown.md")
        head = text.split("---\n")[1]
        for key in ("name: ", "about: ", "title: ", "labels: takedown"):
            self.assertIn(key, head)
        for must in ("개인정보", "원문을 여기에 쓰지 마세요", "채널 이름과 판 날짜만", "화면에서는 바로 내립니다",
                     "저장소 기록에서 지우는 일은 따로입니다", "EVENING_ENABLED"):
            self.assertIn(must, text)
        self.assertNotRegex(text, r"https://t\.me/[A-Za-z]")                    # 실제 채널 주소를 예로 들지 않는다
        self.assertIn("'AI 요약'", text)                                         # AI가 쓴 문장이 실린다는 것을 숨기지 않는다
        for wrong in ("요약 문장도 만들지 않습니다", "사람이든 기계든", "평일 저녁에 한 번 읽습니다",   # 2026-10-08의 옛 문장
                      "한 번 더 읽습니다"):                                                     # PC는 하루 세 번까지 다시 읽는다
            self.assertNotIn(wrong, text)
        for at in ("17:45", "23:30", "07:30"):                                   # AI 요약을 위해 PC가 읽는 때
            self.assertIn(at, text)

    def test_readme_says_how_the_evening_reads_channels(self):
        # 2026-11-10 점검 ep-03 · ep-04 · ep-05의 검토 반영: '어디서 어떻게 읽는가'와 숨김 문단이 실제 흐름과 같은 말을 한다
        readme = read("README.md")
        part = readme.split("### 어디서 어떻게 읽는가\n", 1)[1].split("\n### ", 1)[0]
        (ai,) = [line for line in part.split("\n") if "'AI 요약'을 쓸 때" in line]
        self.assertNotIn("한 번 더 읽습니다", ai)                                 # PC는 하루 세 번까지 다시 읽는다(takedown.md와 같은 말)
        for at in ("17:45", "23:30", "07:30", "고른 글을 다 읽지 못했던 판"):
            self.assertIn(at, ai)
        self.assertIn("새 날짜의 판을 내어 그날 저녁 PC의 실행을 막는 일이 없게", part)   # 늦은 예약 실행을 건너뛰는 까닭 — 뜻이 뒤집혀 읽히지 않게
        self.assertNotIn("실행이 막히지 않게 하려는", part)
        (hide,) = [line for line in readme.split("\n") if "숨긴 채널의 글은 묶기 전에 빠져" in line]
        self.assertIn("판의 '읽은 N건'에도 세지 않습니다", hide)                  # funnel.posts도 숨긴 채널의 글을 뺀 수다

    def test_readme_evening_test_counts_are_the_suite(self):
        # README의 저녁판 테스트 수 두 곳('테스트' 절과 '검증' 절)이 실제 수와 같다 — 한쪽만 고쳐 어긋난 적이 있다(732 대 733)
        readme, n = read("README.md"), unittest.TestLoader().discover(HERE).countTestCases()
        self.assertEqual(re.findall(r"저녁판 테스트 (\d+)개", readme), [str(n)])
        self.assertEqual(re.findall(r"기준 (\d+)개입니다\(진짜 git", readme), [str(n)])


if __name__ == "__main__":
    unittest.main()
