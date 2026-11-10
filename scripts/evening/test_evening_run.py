#!/usr/bin/env python3
"""저녁판 실행 묶음(evening_run)과 게시(digest_publish) 테스트 — 단계 순서와 종료코드, 실패한 날의 상태, 22:41 감시, data/로 옮기기.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요 — 단계 스크립트는 가짜 실행기로 부르고(조립·검사만 진짜로 돈다), 공개 페이지는 가짜 응답으로 대신한다.
"""
import contextlib
import copy
import datetime
import io
import os
import sys
import tempfile
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_build as B
import digest_check as C
import digest_publish as P
import digest_schema as S
import evening_run as E
import fixtures as F

DAY = f"digest/{F.EDITION}.json"
FILES = ("digest.json", DAY, "digest_index.json", "digest_state.json", "digest_status.json")
REAL = {"digest_build.py": B, "digest_check.py": C}
_FX = {}


def fx(name):
    if name not in _FX:
        _FX[name] = getattr(F, name)()
    return copy.deepcopy(_FX[name])


def index_before():
    old = fx("index")["editions"][1]
    return {"schema": 1, "updated_at": old["collected_at"], "latest": old["date"], "editions": [old]}


def edition_files():
    d = fx("digest")
    return {"digest.json": d, DAY: d, "digest_index.json": fx("index"), "digest_state.json": fx("state_after"),
            "digest_status.json": fx("status")}


def put(folder, files):
    for name, doc in files.items():
        S.write_json(os.path.join(folder, *name.split("/")), doc)
    return folder


def tree(folder):
    return sorted(os.path.relpath(os.path.join(r, n), folder).replace(os.sep, "/") for r, _, ns in os.walk(folder) for n in ns)


def raw(folder, name):
    with open(os.path.join(folder, *name.split("/")), "rb") as f:
        return f.read()


def quiet(name, main, argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = S.run_cli(name, main, argv)
    return code, buf.getvalue()


class Runner:
    """가짜 실행기 — 부른 명령을 적어 두고, codes에 있는 것은 그 종료코드를, 조립·검사는 진짜로 돌려 돌려준다."""

    def __init__(self, **codes):
        self.calls, self.codes = [], {k: list(v) if isinstance(v, (list, tuple)) else [v] for k, v in codes.items()}

    def __call__(self, cmd, **kw):
        script, args = os.path.basename(cmd[3]), cmd[4:]                       # [python, -X, utf8, 스크립트, 인자…]
        self.calls.append((script, list(args)))
        key = script[:-3] + ("_error" if "--error" in args else "")
        if self.codes.get(key):
            code = self.codes[key].pop(0) if len(self.codes[key]) > 1 else self.codes[key][0]
        else:
            code = S.run_cli(script[:-3], REAL[script].main, list(args)) if script in REAL else 0
        return types.SimpleNamespace(returncode=code)


class PipelineCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work, self.data, self.out = (os.path.join(self.tmp.name, n) for n in ("work", "data", "_evening"))
        self.gh = os.path.join(self.tmp.name, "github_output")
        put(self.work, {"scored.json": fx("scored_doc"), "collect_status.json": fx("collect_status"), "posts.json": fx("posts_doc")})
        put(self.data, {"sources.json": fx("sources"), "digest_state.json": fx("state"), "digest_index.json": index_before(),
                        "digest_overrides.json": F.overrides()})

    def run_pipeline(self, runner, *extra):
        argv = ["pipeline", "--work", self.work, "--out", self.out, "--data", self.data, "--github-output", self.gh, *extra]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = S.run_cli("evening_run", lambda v: E.main(v, run=runner), argv)
        return code, buf.getvalue()

    def outputs(self):
        with open(self.gh, encoding="utf-8") as f:
            return dict(line.rstrip("\n").split("=", 1) for line in f)


class PipelineTest(PipelineCase):
    def test_stages_run_in_order_with_the_contract_arguments(self):
        runner = Runner()
        code, text = self.run_pipeline(runner)
        self.assertEqual(code, 0, text)
        src, state = os.path.join(self.data, "sources.json"), os.path.join(self.data, "digest_state.json")
        self.assertEqual(runner.calls, [
            ("tg_collect.py", ["--sources", src, "--state", state, "--work", self.work]),
            ("digest_cluster.py", ["--work", self.work, "--overrides", os.path.join(self.data, "digest_overrides.json")]),
            ("digest_score.py", ["--work", self.work, "--calendar", os.path.join(self.data, "calendar.json"),
                                 "--korea", os.path.join(self.data, "korea.json"), "--state", state]),
            ("digest_build.py", ["--work", self.work, "--out", self.out, "--data", self.data]),
            ("digest_check.py", ["--public", self.out, "--raw", self.work, "--sources", src, "--strict"]),
        ])
        self.assertEqual(self.outputs(), {"publish": "true", "alert": "false", "reason": "ok", "stage": "done"})
        self.assertEqual(tree(self.out), sorted(FILES))
        self.assertIn("[evening_run] pipeline publish=true alert=false reason=ok stage=done\n", text)
        self.assertEqual(F.leaks(text), [])

    def test_replay_and_now_reach_the_collector_only(self):
        runner = Runner()
        self.assertEqual(self.run_pipeline(runner, "--replay", "--now", F.NOW)[0], 0)
        self.assertEqual(runner.calls[0][1][-3:], ["--replay", "--now", F.NOW])
        self.assertNotIn("--now", runner.calls[3][1])

    def test_short_edition_is_published_and_flagged(self):
        put(self.work, {"collect_status.json": F.collect_status(fail={"fxbond1": "fetch", "fxbond2": "fetch", "fxbond3": "empty"})})
        code, text = self.run_pipeline(Runner())
        self.assertEqual((code, self.outputs()), (0, {"publish": "true", "alert": "true", "reason": "short", "stage": "done"}))
        self.assertEqual(S.read_json(os.path.join(self.out, "digest.json"))["status"], "short")

    def test_changed_channel_is_flagged_by_its_own_name(self):
        put(self.work, {"collect_status.json": F.collect_status(fail={"fxanal6": "title"})})
        code, text = self.run_pipeline(Runner())
        self.assertEqual((code, self.outputs()), (0, {"publish": "true", "alert": "true", "reason": "channel", "stage": "done"}))

    def test_broken_preview_publishes_the_status_only(self):
        collect = fx("collect_status")
        for c in collect["channels"]:
            c["with_text"] = 1
        put(self.work, {"collect_status.json": {**collect, "verdict": "broken"}})
        code, text = self.run_pipeline(Runner())
        self.assertEqual((code, self.outputs()), (0, {"publish": "true", "alert": "true", "reason": "broken", "stage": "done"}))
        self.assertEqual(tree(self.out), ["digest_status.json"])

    def test_failed_stage_leaves_an_error_status_and_stops_there(self):
        for stage, script in (("collect", "tg_collect"), ("cluster", "digest_cluster"), ("score", "digest_score")):
            with self.subTest(stage):
                runner = Runner(**{script: 1})
                code, text = self.run_pipeline(runner, "--now", "2026-10-08T18:30:00+09:00")
                self.assertEqual((code, self.outputs()), (0, {"publish": "true", "alert": "true", "reason": "error", "stage": stage}))
                names = [c[0] for c in runner.calls]
                self.assertEqual(names[names.index(script + ".py") + 1:], ["digest_build.py", "digest_check.py"])    # 뒤 단계는 돌지 않는다
                self.assertIn("--error", runner.calls[-2][1])
                self.assertNotIn("--raw", runner.calls[-1][1])
                status = S.read_json(os.path.join(self.out, "digest_status.json"))
                self.assertEqual(tree(self.out), ["digest_status.json"])
                self.assertEqual((status["reason"], status["published"], status["edition"]), ("error", False, F.EDITION))
                os.remove(self.gh)

    def test_edition_that_fails_the_check_is_wiped(self):
        runner = Runner(digest_check=[1, 0])                                    # 조립한 판이 검사에 걸렸다
        code, text = self.run_pipeline(runner, "--now", "2026-10-08T18:30:00+09:00")
        self.assertEqual((code, self.outputs()), (0, {"publish": "true", "alert": "true", "reason": "error", "stage": "check"}))
        self.assertEqual(tree(self.out), ["digest_status.json"])               # 걸린 판은 게시 폴더에 남지 않는다

    def test_build_failure_and_hopeless_day(self):
        code, text = self.run_pipeline(Runner(digest_build=1), "--now", "2026-10-08T18:30:00+09:00")
        self.assertEqual((code, self.outputs()["stage"], tree(self.out)), (0, "build", ["digest_status.json"]))
        os.remove(self.gh)
        code, text = self.run_pipeline(Runner(tg_collect=1, digest_build_error=1))
        self.assertEqual((code, self.outputs()), (1, {"publish": "false", "alert": "true", "reason": "error", "stage": "collect"}))
        self.assertEqual(tree(self.out) if os.path.isdir(self.out) else [], [])

    def test_leftovers_of_an_earlier_run_are_cleared_first(self):
        put(self.out, {**edition_files(), "digest/2026-10-06.json": {"old": 1}})
        with open(os.path.join(self.out, "notes.txt"), "w", encoding="utf-8") as f:
            f.write("keep")
        code, text = self.run_pipeline(Runner(tg_collect=1, digest_build_error=1))
        self.assertEqual((code, tree(self.out)), (1, ["notes.txt"]))           # 저녁판 파일만 지운다

    def test_a_late_scheduled_run_collects_nothing(self):
        # 2026-11-10 점검 ep-03: 몇 시간 늦은 예약 실행이 06:00 KST를 넘기면 이튿날(금요일 것은 토요일) 판을 냈고, 그 판 때문에
        # 그날 17:45 PC의 실행 시작이 막혔다 — 판의 저녁(평일 17:30 ~ 이튿날 06:00) 밖의 예약 실행은 아무 단계도 돌리지 않는다
        late = {"이튿날 06:00": "2026-10-09T06:00:00+09:00", "이튿날 06:10": "2026-10-09T06:10:00+09:00",
                "이튿날 낮": "2026-10-09T12:00:00+09:00", "그날 17:29": "2026-10-09T17:29:00+09:00",
                "토요일 아침(금 판의 늦은 실행)": "2026-10-10T06:10:00+09:00", "토요일 저녁": "2026-10-10T19:00:00+09:00",
                "일요일 새벽": "2026-10-11T03:00:00+09:00"}
        for name, now in late.items():
            with self.subTest(name):
                runner = Runner()
                code, text = self.run_pipeline(runner, "--event", "schedule", "--now", now)
                self.assertEqual((code, self.outputs()), (0, {"publish": "false", "alert": "false", "reason": "late", "stage": "skip"}))
                self.assertEqual(runner.calls, [])                              # 채널 요청 0회 — 수집 단계도 부르지 않는다
                self.assertEqual(tree(self.out) if os.path.isdir(self.out) else [], [])
                self.assertIn("[evening_run] pipeline publish=false alert=false reason=late stage=skip\n", text)
                os.remove(self.gh)

    def test_scheduled_runs_inside_the_evening_and_manual_runs_go_ahead(self):
        go = {("schedule", "2026-10-08T17:41:00+09:00"): "제시각", ("schedule", "2026-10-08T17:30:00+09:00"): "17:30",
              ("schedule", "2026-10-09T04:06:00+09:00"): "새벽의 늦은 실행(전날 판을 다시 계산)",
              ("schedule", "2026-10-10T05:59:00+09:00"): "토요일 새벽(금 판)",
              ("workflow_dispatch", "2026-10-09T08:40:00+09:00"): "수동 실행은 때를 가리지 않는다",
              (None, "2026-10-10T11:00:00+09:00"): "이벤트를 주지 않은 실행(PC의 시범 실행)"}
        for (event, now), name in go.items():
            with self.subTest(name):
                runner = Runner()
                code, text = self.run_pipeline(runner, "--now", now, *(["--event", event] if event else []))
                self.assertEqual(code, 0, text)
                self.assertEqual([c[0] for c in runner.calls], ["tg_collect.py", "digest_cluster.py", "digest_score.py",
                                                                 "digest_build.py", "digest_check.py"])
                self.assertEqual(self.outputs()["publish"], "true")
                os.remove(self.gh)

    def test_the_time_rule_is_the_pcs_dispatch_rule(self):
        # 예약 수집과 PC의 규칙판 실행 시작(evening_llm.due)이 같은 때의 규칙(S.in_evening)을 쓴다
        times = ["2026-10-08T17:29:59+09:00", "2026-10-08T17:30:00+09:00", "2026-10-09T05:59:00+09:00", "2026-10-09T06:00:00+09:00",
                 "2026-10-10T05:59:00+09:00", "2026-10-10T06:00:00+09:00", "2026-10-10T19:00:00+09:00", "2026-10-12T17:30:00+09:00"]
        self.assertEqual([S.in_evening(S.parse_iso(t)) for t in times], [False, True, True, False, True, False, False, True])
        import evening_llm as L
        with tempfile.TemporaryDirectory() as repo:                            # 아직 한 판도 없는 저장소 — 때의 규칙만 남는다
            self.assertEqual([L.due(S.parse_iso(t), repo) for t in times], [S.in_evening(S.parse_iso(t)) for t in times])

    def test_out_must_not_be_the_data_folder(self):
        code, text = quiet("evening_run", lambda v: E.main(v, run=Runner()),
                           ["pipeline", "--work", self.work, "--out", self.data, "--data", self.data])
        self.assertEqual((code, text), (1, "[evening_run] 실패: ValueError\n"))
        self.assertIn("digest_state.json", tree(self.data))


class CalendarWarningTest(PipelineCase):
    """일정표가 곧 끝나면 경고 한 줄 — 게시와 출력 값은 그대로다."""

    def calendar(self, *days):
        put(self.data, {"calendar.json": {"schema": 1, "updated": "2026-10-01",
                                          "events": [{"date": d, "time": None, "term": "금통위", "tier": "A"} for d in days]}})

    def test_warns_when_the_last_event_is_near_and_still_publishes(self):
        today = S.edition_date(S.parse_iso(F.NOW))
        near = (datetime.date.fromisoformat(today) + datetime.timedelta(days=E.CAL_AHEAD - 1)).isoformat()
        self.calendar(today, near)
        code, text = self.run_pipeline(Runner(), "--now", F.NOW)
        self.assertEqual(code, 0, text)
        self.assertIn(f"::warning::일정표(data/calendar.json)가 {near}에서 끝난다({E.CAL_AHEAD - 1}일 남음)", text)
        self.assertEqual(self.outputs(), {"publish": "true", "alert": "false", "reason": "ok", "stage": "done"})
        self.assertEqual(F.leaks(text), [])

    def test_quiet_when_the_calendar_reaches_far_enough(self):
        far = (datetime.date.fromisoformat(S.edition_date(S.parse_iso(F.NOW))) + datetime.timedelta(days=E.CAL_AHEAD)).isoformat()
        self.calendar(far)
        code, text = self.run_pipeline(Runner(), "--now", F.NOW)
        self.assertEqual(code, 0, text)
        self.assertNotIn("::warning::", text)

    def test_a_calendar_that_already_ended_says_how_long_ago(self):
        today = datetime.date.fromisoformat(S.edition_date(S.parse_iso(F.NOW)))
        gone, last = [(today - datetime.timedelta(days=d)).isoformat() for d in (9, 5)]
        self.calendar(gone, last)
        text = self.run_pipeline(Runner(), "--now", F.NOW)[1]
        self.assertIn(f"::warning::일정표(data/calendar.json)가 {last}에서 끝났다(5일 지남)", text)
        self.assertNotIn("남음", text)                                           # 음수 날수를 '남음'으로 쓰지 않는다
        self.calendar((today - datetime.timedelta(days=1)).isoformat(), today.isoformat())
        self.assertIn(f"{today.isoformat()}에서 끝난다(0일 남음)", self.run_pipeline(Runner(), "--now", F.NOW)[1])   # 오늘이 마지막 일정

    def test_empty_or_missing_calendar(self):
        self.calendar()
        self.assertIn("::warning::일정표(data/calendar.json)가 비어 있다", self.run_pipeline(Runner(), "--now", F.NOW)[1])
        os.remove(os.path.join(self.data, "calendar.json"))                      # 못 읽으면 조용히(점수 단계가 알린다)
        self.assertNotIn("::warning::", self.run_pipeline(Runner(), "--now", F.NOW)[1])

    def test_the_real_calendar_is_read_with_the_edition_date(self):
        a = types.SimpleNamespace(data=S.DATA, now="2026-12-31T01:30:00+09:00")    # 자정을 넘긴 12-30 판의 재실행
        cal = S.read_json(os.path.join(S.DATA, "calendar.json"))
        last = max(e["date"] for e in cal["events"])
        with contextlib.redirect_stdout(io.StringIO()):
            msg = E._calendar_warning(a)
        left = (datetime.date.fromisoformat(last) - datetime.date(2026, 12, 30)).days
        self.assertEqual(msg is None, left >= E.CAL_AHEAD)


class Page:
    """공개 페이지의 가짜 응답."""

    def __init__(self, body=None, fail=None):
        self.body, self.fail, self.urls = body, fail, []

    def __call__(self, url, timeout=None):
        self.urls.append((url, timeout))
        if self.fail:
            raise self.fail
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, n=-1):
        return self.body[:n] if n and n > 0 else self.body


class WatchTest(unittest.TestCase):
    NOW = "2026-10-08T22:41:00+09:00"
    URL = "https://example-owner.github.io/example-repo"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data, self.gh = os.path.join(self.tmp.name, "data"), os.path.join(self.tmp.name, "github_output")
        put(self.data, {"digest_status.json": fx("status")})

    def watch(self, page, now=None, url=None):
        argv = ["watch", "--data", self.data, "--page-url", url or self.URL, "--now", now or self.NOW, "--github-output", self.gh]
        code, text = quiet("evening_run", lambda v: E.main(v, opener=page), argv)
        out = {}
        if os.path.exists(self.gh):
            with open(self.gh, encoding="utf-8") as f:
                out = dict(line.rstrip("\n").split("=", 1) for line in f)
            os.remove(self.gh)
        return code, out, text

    def body(self, **change):
        return S.dump({**fx("status"), **change}).encode("utf-8")

    def test_page_already_shows_todays_edition(self):
        page = Page(self.body())
        code, out, text = self.watch(page)
        self.assertEqual((code, out), (0, {"redeploy": "false", "missing": "false"}))
        self.assertEqual(len(page.urls), 1)                                     # 요청은 공개 페이지에 한 번뿐 — 텔레그램에는 가지 않는다
        self.assertRegex(page.urls[0][0], r"^https://example-owner\.github\.io/example-repo/data/digest_status\.json\?t=\d+$")
        self.assertEqual(page.urls[0][1], E.TIMEOUT)
        self.assertEqual(text, "[evening_run] watch redeploy=false missing=false\n")

    def test_stale_page_asks_for_a_redeploy(self):
        cases = {"어제 판": self.body(edition="2026-10-07"), "같은 날의 앞선 실행": self.body(checked_at="2026-10-08T18:00:00+09:00"),
                 "실패 상태": self.body(published=False, ok=False, reason="error"), "깨진 응답": b"<html>404</html>",
                 "형식이 다른 응답": b'{"edition":"2026-10-08"}', "너무 큰 응답": b" " * (E.MAX_BYTES + 1) + self.body()}
        for name, body in cases.items():
            with self.subTest(name):
                self.assertEqual(self.watch(Page(body))[:2], (0, {"redeploy": "true", "missing": "false"}))
        code, out, text = self.watch(Page(fail=OSError(F.CANARIES[0])))
        self.assertEqual((code, out, F.leaks(text)), (0, {"redeploy": "true", "missing": "false"}, []))

    def test_missing_edition_on_main_fails_without_asking_the_page(self):
        cases = {"어제 판뿐": fx("status") | {"edition": "2026-10-07"}, "실패한 날": fx("status") | {"published": False, "ok": False,
                 "reason": "error"}, "파일 없음": None, "형식이 다름": {"edition": F.EDITION, "published": True}}
        for name, doc in cases.items():
            with self.subTest(name):
                path = os.path.join(self.data, "digest_status.json")
                os.remove(path) if doc is None else S.write_json(path, doc)
                page = Page(self.body())
                code, out, text = self.watch(page)
                self.assertEqual((code, out, page.urls), (1, {"redeploy": "false", "missing": "true"}, []))
                put(self.data, {"digest_status.json": fx("status")})

    def test_edition_date_follows_the_clock(self):
        self.assertEqual(self.watch(Page(self.body()), now="2026-10-09T05:59:00+09:00")[0], 0)      # 새벽까지는 전날 판
        self.assertEqual(self.watch(Page(self.body()), now="2026-10-09T22:41:00+09:00")[0], 1)      # 다음 날 저녁에는 그날 판이 있어야

    def test_a_late_watch_compares_with_the_edition_that_was_due(self):
        # 2026-11-10 08:08 KST: 22:41 감시가 9시간 반 늦게 돌아 멀쩡한 11-09 판을 '없다'고 알렸다(판 날짜를 지금 − 6시간으로 셌다).
        # 이제 화면(dueEdition)처럼 22:41이 지난 마지막 평일의 판과 견준다
        for now in ("2026-10-09T08:08:00+09:00", "2026-10-09T12:00:00+09:00", "2026-10-09T17:30:00+09:00", "2026-10-09T22:40:59+09:00"):
            with self.subTest(now):
                self.assertEqual(self.watch(Page(self.body()), now=now)[:2], (0, {"redeploy": "false", "missing": "false"}))
        friday = fx("status") | {"edition": "2026-10-09"}
        cases = {("2026-10-10T08:00:00+09:00", "2026-10-09"): 0,               # 금요일 감시가 토요일 아침에 늦게 돌았다
                 ("2026-10-12T08:00:00+09:00", "2026-10-09"): 0,               # 주말판은 없다
                 ("2026-10-10T08:00:00+09:00", "2026-10-08"): 1,               # 금요일 판이 정말 없다
                 ("2026-10-09T21:00:00+09:00", "2026-10-09"): 0}               # 마감 전이어도 더 새 판이 올라와 있으면 된다
        for (now, edition), want in cases.items():
            with self.subTest(now=now, edition=edition):
                put(self.data, {"digest_status.json": friday | {"edition": edition}})
                body = S.dump(friday | {"edition": edition}).encode("utf-8")
                self.assertEqual(self.watch(Page(body), now=now)[:2],
                                 (want, {"redeploy": "false", "missing": "true" if want else "false"}))

    def test_due_edition_rule(self):
        want = {"2026-10-08T22:40:59+09:00": "2026-10-07", "2026-10-08T22:41:00+09:00": "2026-10-08",
                "2026-10-09T08:08:00+09:00": "2026-10-08", "2026-10-10T12:00:00+09:00": "2026-10-09",
                "2026-10-11T23:00:00+09:00": "2026-10-09", "2026-10-12T09:00:00+09:00": "2026-10-09",
                "2026-10-13T03:00:00+09:00": "2026-10-12"}
        self.assertEqual({t: E.due_edition(S.parse_iso(t)) for t in want}, want)
        self.assertEqual(E.due_edition(S.parse_iso("2026-10-08T21:00:00+09:00"), "20:30"), "2026-10-08")   # 상태 파일의 마감 시각을 따른다

    def test_page_address_must_be_plain_https(self):
        for url in ("http://example-owner.github.io/example-repo", "https://user:pw@example.com/x", "https://example.com/x?y=1",
                    "file:///etc/passwd", "example.com"):
            with self.subTest(url):
                page = Page(self.body())
                code, out, text = self.watch(page, url=url)
                self.assertEqual((code, out, text), (1, {}, "[evening_run] 실패: ValueError\n"))      # 설정이 틀린 것 — 조용히 넘기지 않는다
                self.assertEqual(page.urls, [])                                 # 꼴이 다른 주소로는 요청하지 않는다


class PublishTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.src, self.data = os.path.join(self.tmp.name, "_evening"), os.path.join(self.tmp.name, "data")
        put(self.src, edition_files())
        put(self.data, {"sources.json": fx("sources"), "korea.json": {"morning": 1}, "digest/2026-10-07.json": {"old": 1},
                        "digest/2026-08-01.json": {"old": 2}, "digest.json": {"old": 3}})

    def publish(self, *extra):
        return quiet("digest_publish", P.main, ["--from", self.src, "--data", self.data, *extra])

    def test_moves_the_evening_files_and_nothing_else(self):
        before = raw(self.data, "korea.json")
        code, text = self.publish()
        self.assertEqual(code, 0, text)
        for name in FILES:
            self.assertEqual(raw(self.data, name), raw(self.src, name), name)
        self.assertEqual(raw(self.data, "korea.json"), before)
        self.assertEqual(tree(self.data), sorted(FILES + ("digest/2026-10-07.json", "korea.json", "sources.json")))     # 목차에 없는 지난 판은 지운다
        self.assertEqual(text, "[digest_publish] files=5 removed=1 edition=2026-10-08 reason=ok\n")
        self.assertEqual(C.check_folder(self.src, fx("sources"))[0], [])

    def test_refuses_what_the_check_refuses(self):
        bad = fx("digest")
        bad["must"][0]["terms"][0] = F.CANARIES[0]
        put(self.src, {"digest.json": bad, DAY: bad})
        before = {n: raw(self.data, n) for n in tree(self.data)}
        code, text = self.publish()
        self.assertEqual(code, 1)
        self.assertEqual({n: raw(self.data, n) for n in tree(self.data)}, before)      # 아무것도 옮기지 않는다
        self.assertEqual(F.leaks(text), [])
        self.assertIn("violations=", text)

    def test_status_only_day_keeps_the_last_edition(self):
        for name in FILES[:-1]:
            os.remove(os.path.join(self.src, *name.split("/")))
        put(self.src, {"digest_status.json": {**fx("status"), "ok": False, "reason": "error", "published": False, "channels": [],
                                              "counts": dict.fromkeys(fx("status")["counts"], 0)}})
        before = tree(self.data)
        code, text = self.publish()
        self.assertEqual((code, tree(self.data)), (0, sorted(before + ["digest_status.json"])))
        self.assertEqual(S.read_json(os.path.join(self.data, "digest.json")), {"old": 3})
        self.assertEqual(text, "[digest_publish] files=1 removed=0 edition=2026-10-08 reason=error\n")

    def test_refuses_to_go_back_in_time(self):
        self.assertEqual(self.publish()[0], 0)
        older = {**fx("status"), "checked_at": "2026-10-08T18:00:00+09:00"}
        put(self.src, {"digest_status.json": older})
        code, text = self.publish()
        self.assertEqual((code, text), (1, "[digest_publish] 실패: ValueError\n"))
        self.assertEqual(S.read_json(os.path.join(self.data, "digest_status.json")), fx("status"))
        self.assertEqual(self.publish("--data", self.src)[0], 1)                # 같은 폴더로는 옮기지 않는다


if __name__ == "__main__":
    unittest.main()
