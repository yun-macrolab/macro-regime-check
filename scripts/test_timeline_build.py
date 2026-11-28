#!/usr/bin/env python3
"""판단 연표(timeline_build) 테스트 — 지어낸 공개 기록 커밋(가짜 GitHub 응답 · 임시 git 저장소)과 지어낸 그래프 자료로 답을 아는 셈을
본다. 네트워크 불필요(가짜 opener만 — 진짜 urlopen은 부르지 않는다), 표준 라이브러리 + git 명령(GitTest만 — 없으면 건너뜀).

실행:  python -m unittest discover -s scripts   (저장소 루트에서)   ·   python -X utf8 scripts/test_timeline_build.py
"""
import io, os, re, sys, json, time, hashlib, datetime, tempfile, threading, unittest, subprocess, contextlib, shutil
import urllib.error, urllib.parse
from unittest import mock

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import timeline_build as tb
import ledger_build as lb
import lp_fetch as lpf

D = datetime.date
REPO = os.path.dirname(SCRIPTS)
NOW = "2027-07-01T00:00:00+00:00"
TOKEN = "ghs_FAKEtoken0123456789abcdef"
BANNED = ("매수", "매도", "유망", "적중", "맞았다", "틀렸다", "전망", "예상", "추천", "성적")
PLANTED = ("비밀 결론 글", "비밀 메모 글", "비밀 뉴스 제목", "비밀 근거 글", "비밀 요약 글", "비밀 하우스 뷰")
WEEK = datetime.timedelta(days=7)
DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")
ISO = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$")


def plus(d, n):
    return d + datetime.timedelta(days=n)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def run_main(argv, now=NOW, **kw):
    """tb.main — 실행 줄을 모아 돌려준다 → (종료코드, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = tb.main(argv, now=now, **kw)
    return code, out.getvalue(), err.getvalue()


# ── 지어낸 공개 기록 ─────────────────────────────────────────────────────────────────────────────────────────
def record(week, confirmed=False, dur=(0.0, "Neutral"), cur=(0.0, "Neutral"), edited=0, regime=None, **over):
    """macro-notes-public/1 꼴의 공개본 한 장 — 뉴스·결론·메모·근거에는 심어 둔 글(PLANTED)."""
    s = D.fromisoformat(week)
    rec = {"schema": "macro-notes-public/1", "notice": "지어낸 안내", "week": {"start": week, "end": plus(s, 6).isoformat()},
           "generated_at": week + "T04:00:00+00:00", "conclusion": "비밀 결론 글",
           "state": {"rows": [{"label": "펀더멘털·글로벌", "dur": 1.0, "cur": 0.0, "dur_prev": 0.0, "cur_prev": 0.0,
                               "dur_tag": "", "cur_tag": "", "note": "비밀 근거 글", "digest": "비밀 요약 글",
                               "news_dur": None, "news_cur": None, "house": "비밀 하우스 뷰", "locked": []}],
                     "dur": {"total": dur[0], "verdict": dur[1]}, "cur": {"total": cur[0], "verdict": cur[1]},
                     "confirmed": confirmed, "edited_n": edited,
                     "flags": {"regime": regime, "rho60": None, "transition": "OFF", "event_on": False, "tp_break": "OFF",
                               "core_cpi_lt3": False, "relax": False}},
           "divergences": [], "memo": [{"label": "메모", "value": "비밀 메모 글"}],
           "news": [{"date": week, "factor": "펀더멘털", "region": "글로벌", "keyword": "k", "title": "비밀 뉴스 제목",
                     "content": "c", "direction": "상방", "intensity": 1, "source": "s", "kind": "지표"}]}
    for k, v in over.items():
        rec["state"][k] = v
    return rec


def rb(rec):
    return json.dumps(rec, ensure_ascii=False).encode("utf-8")


def path(week):
    return f"records/{week}.json"


class MemSource:
    """process()에 넣는 메모리 원본 — commits: [(sha, at, {경로: 바이트 | None(지움) | ('R', 옛 경로, 바이트)})]."""

    def __init__(self, commits):
        self.files = {sha: f for sha, _, f in commits}

    def changed(self, sha):
        out = []
        for p, v in self.files[sha].items():
            if isinstance(v, tuple):
                out.append(("renamed", p, v[1]))
            else:
                out.append(("removed" if v is None else "modified", p, None))
        return out

    def content(self, sha, p):
        v = self.files[sha][p]
        return v[2] if isinstance(v, tuple) else v


def sha_of(i):
    return hashlib.sha1(f"commit-{i}".encode()).hexdigest()


class Resp:
    def __init__(self, body):
        self.b = io.BytesIO(body)

    def read(self, n=-1):
        return self.b.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.b.close()


class FakeGitHub:
    """GitHub API + raw의 가짜 — commits는 오래된 것부터 [(sha, at, {경로: 바이트 | None})]. 요청마다 (호스트, 주소, 머리글)을 남긴다.
    fail: 주소 조각 → HTTP 코드(그 요청에서 HTTPError). cost: 요청마다 가짜 시계를 미는 초."""

    def __init__(self, commits, readme_commits=(), fail=None, clock=None, cost=0.0):
        self.commits = list(commits)
        self.fail = dict(fail or {})
        self.clock, self.cost = clock, cost
        self.calls = []

    def newest_first(self):
        return list(reversed(self.commits))

    def tree_at(self, sha):
        tree = {}
        for s, _, files in self.commits:
            for p, v in files.items():
                if v is None:
                    tree.pop(p, None)
                else:
                    tree[p] = v
            if s == sha:
                return tree
        raise KeyError(sha)

    def __call__(self, req, timeout=None):
        url = req.full_url
        host = urllib.parse.urlsplit(url).hostname
        self.calls.append((host, url, {k.lower(): v for k, v in req.header_items()}, timeout))
        if self.clock is not None:
            self.clock.t += self.cost
        for frag, code in self.fail.items():
            if frag in url:
                raise urllib.error.HTTPError(url, code, "fake", {}, None)
        if url.startswith(tb.API + "/commits?"):
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            assert q["path"] == ["records"], q
            per, page = int(q["per_page"][0]), int(q["page"][0])
            items = self.newest_first()[(page - 1) * per: page * per]
            return Resp(json.dumps([{"sha": s, "commit": {"committer": {"date": at}}} for s, at, _ in items]).encode())
        if url.startswith(tb.API + "/commits/"):
            sha = url.rsplit("/", 1)[1]
            files = dict((s, f) for s, _, f in self.commits)[sha]
            return Resp(json.dumps({"sha": sha, "files": [{"filename": p, "status": "removed" if v is None else "modified"}
                                                           for p, v in files.items()]}).encode())
        prefix = f"https://{tb.RAW_HOST}/{tb.SOURCE_REPO}/"
        if url.startswith(prefix):
            sha, rest = url[len(prefix):].split("/", 1)
            tree = self.tree_at(sha)
            if rest not in tree:
                raise urllib.error.HTTPError(url, 404, "fake", {}, None)
            return Resp(tree[rest])
        raise urllib.error.HTTPError(url, 404, "fake", {}, None)


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


# ── 지어낸 그래프 · 기록 · 격자 ──────────────────────────────────────────────────────────────────────────────
FRI0 = D(2026, 1, 2)                                   # 금요일


def fridays(n, start=FRI0):
    return [plus(start, 7 * k) for k in range(n)]


def linear(dates, base, step):
    return [[d.isoformat(), round(base + step * k, 4)] for k, d in enumerate(dates)]


def charts_obj(dgs10, t10y2y, date="2027-06-30", with_tp=True):
    term = [{"key": "t10y2y", "series": ["T10Y2Y"], "points": t10y2y}]
    if with_tp:
        term.append({"key": "tp", "series": ["THREEFYTP10"], "points": [[p[0], 0.5] for p in t10y2y]})
    return {"schema": 1, "date": date, "generated_at": date + "T07:00:00+00:00", "attribution": [],
            "overview": [{"key": "yield10", "lines": [{"key": "dgs10", "series": ["DGS10"], "points": dgs10}]},
                         {"key": "term", "lines": term}], "rules": []}


def default_charts():
    ds = fridays(80)                                   # 2026-01-02 ~ 2027-07-02 무렵
    return charts_obj(linear(ds, 4.0, 0.01), linear(ds, 0.5, -0.01))


def snapshot(date, met=1, total=3, reg="A′", core=(2, 11), with_regime=True):
    d = {"schema": 1, "date": date, "rules": [{"key": f"r{i}", "title": f"규칙 {i}", "status": "met" if i < met else "not_met"}
                                              for i in range(total)], "data_health": []}
    if with_regime:
        d["regime"] = {"core": {"total": core[1], "met": core[0], "unknown": 0},
                       "reference": {"candidate": reg, "transition": {"auto_on": 0}}}
    return d


def lp_obj(rows):
    return {"schema": 1, "label": lpf.LABEL, "history": [{"month": m, "known": k, "L": L, "P": P, "cell": lpf.cell(L, P)[0],
                                                          "kind": "x", "tags": []} for m, k, L, P in rows]}


class DataDir:
    """임시 data 폴더 — charts.json · history/ · lp.json."""

    def __init__(self, charts=None, snaps=(), lp=None):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = self.tmp.name
        if charts is not False:
            write_json(os.path.join(self.path, "charts.json"), charts or default_charts())
        for s in snaps:
            write_json(os.path.join(self.path, "history", s["date"] + ".json"), s)
        if lp is not None:
            write_json(os.path.join(self.path, "lp.json"), lp)

    def file(self, name=tb.FILE):
        return os.path.join(self.path, name)

    def cleanup(self):
        self.tmp.cleanup()


def week_commits(spec):
    """[(at, {주: 공개본 | None})] → [(sha, at, {경로: 바이트 | None})] — sha는 차례로 지어낸 것."""
    return [(sha_of(i), at, {path(w): (None if r is None else rb(r)) for w, r in files.items()})
            for i, (at, files) in enumerate(spec)]


# 지어낸 공개 기록 이력: 두 주, 확정 전 → 확정 → 확정 뒤 고침, 그리고 README만 바꾼 커밋
SPEC = [
    ("2026-03-09T04:00:00Z", {"2026-03-02": record("2026-03-02", False, (-0.4, "Neutral"), (0.1, "Neutral"))}),
    ("2026-03-10T04:00:00Z", {"2026-03-02": record("2026-03-02", False, (-0.6, "U/W"), (0.6, "Flattening"))}),
    ("2026-03-11T04:00:00Z", {"2026-03-02": record("2026-03-02", True, (-0.6, "U/W"), (0.6, "Flattening"), edited=2,
                                                   regime="A′"),
                              "2026-03-09": record("2026-03-09", False)}),
    ("2026-03-16T04:00:00Z", {"2026-03-09": record("2026-03-09", True, (0.7, "O/W"), (-0.5, "Steepening"))}),
    ("2026-03-17T04:00:00Z", {"2026-03-02": record("2026-03-02", True, (0.0, "Neutral"), (0.6, "Flattening"), edited=3)}),
]


# ── 약속 ─────────────────────────────────────────────────────────────────────────────────────────────────────
class ProtocolTest(unittest.TestCase):
    def test_constants(self):
        self.assertEqual((tb.PROTOCOL_VERSION, tb.PROTOCOL_FIXED, tb.HORIZONS, tb.N_MIN, tb.TOL_DAYS, tb.START_DAYS,
                          tb.OPEN_UTC), (1, "2026-11-19", (1, 4), 10, 3, 7, (13, 30)))
        self.assertEqual([p[:3] for p in tb.PAIRS], [("dur", "dgs10", "DGS10"), ("cur", "t10y2y", "T10Y2Y")])
        self.assertEqual(tb.LABEL, "운영자 주간 판정(공개 기록에서 옮김) — 투자 판단·권유 아님 · 측정 기록")

    def test_reused_ledger_rules_have_the_same_numbers(self):
        """끝 점 맞추기(lb.match)와 늦게 확정한 주의 출발(lb.outcome)은 기록 장부의 상수로 돈다 — 그쪽이 바뀌면 여기가 걸린다."""
        self.assertEqual(lb.TOL_DAYS, tb.TOL_DAYS)
        self.assertEqual(lb.START_DAYS, tb.START_DAYS)
        self.assertEqual({k: sid for _, k, sid, _ in tb.PAIRS}, {k: sid for k, _, sid in lb.OUTCOMES if k in ("dgs10", "t10y2y")})

    def test_verdict_strings_are_the_operator_sheets(self):
        """운영자 시트(sheet_v2.verdict)가 내는 판정 글 — 강한 · 보통 · Neutral, 그리고 '채점 미완 n/7'(n 0~6)."""
        self.assertEqual(set(tb.VERDICTS["dur"]), {"강한 O/W", "O/W", "Neutral", "U/W", "강한 U/W"})
        self.assertEqual(set(tb.VERDICTS["cur"]), {"강한 Flattening", "Flattening", "Neutral", "Steepening", "강한 Steepening"})
        for n in range(7):
            self.assertTrue(tb.UNSCORED_RE.fullmatch(f"채점 미완 {n}/7"))
        for bad in ("채점 미완 7/7", "채점 미완 1/6", "채점미완 1/7", "채점 미완 -1/7"):
            self.assertIsNone(tb.UNSCORED_RE.fullmatch(bad), bad)
        groups = {b: [v for _, vs in tb.GROUPS[b] for v in vs] for b in tb.GROUPS}
        for b in groups:
            self.assertEqual(len(groups[b]), len(set(groups[b])))            # 한 판정은 한 묶음에만

    def test_text_states_the_constants(self):
        text = " ".join(tb.protocol_text())
        for fact in (tb.PROTOCOL_FIXED, f"{tb.PROTOCOL_VERSION}판", "1주·4주", f"±{tb.TOL_DAYS}일", "13:30 UTC",
                     f"{tb.START_DAYS}일", f"{tb.N_MIN}개", "DGS10", "T10Y2Y", "edited_n", "확정 뒤 고침", "늦게 확정",
                     "약속 전", "채점 미완", "GitHub API로 날짜 없이", "검증한 시각이 아니라 적힌 시각", "한국 시각 22:30",
                     "09:30 EDT", "아시아·런던 시간", "공개 기록에서 지움", "잠근 커밋이 지금 기록에 없음", "--rebuild",
                     "출발 점마다 하나로", "0이 초안 그대로라는 보장은 아니다", "발표일 근사", tb.SOURCE_REPO):
            self.assertIn(fact, text)
        self.assertNotIn("운영자 PC의 시계", text)                              # 게시기의 커밋은 GitHub이 시각을 적는다
        self.assertNotIn("현물 시장이 여는 가장 이른 때", text)                  # 13:30 UTC는 미 국채가 아니라 뉴욕 주식 시장의 개장
        self.assertEqual(tb.open_kst(), "22:30")

    def test_no_grading_or_advice_words_anywhere_we_write(self):
        for text in tb.protocol_text() + [tb.LABEL, tb.NOTICE, tb.COMPUTED_NOTICE, lpf.LABEL] + list(tb.REASONS.values()):
            for w in BANNED:
                self.assertNotIn(w, text)
        self.assertIn("예측", tb.NOTICE)
        self.assertIn("권유", tb.NOTICE)


# ── 공개본 한 판 읽기 ─────────────────────────────────────────────────────────────────────────────────────────
class RecordTest(unittest.TestCase):
    W = "2026-03-02"

    def read(self, rec, week=None):
        return tb.read_record(rb(rec) if isinstance(rec, dict) else rec, week or self.W)

    def test_good_record_keeps_only_the_used_fields(self):
        got = self.read(record(self.W, True, (-0.9, "U/W"), (0.88, "Flattening"), edited=4, regime="A′"))
        self.assertEqual(got, {"confirmed": True, "dur": {"total": -0.9, "verdict": "U/W"},
                               "cur": {"total": 0.88, "verdict": "Flattening"}, "edited_n": 4, "regime_flag": "A′",
                               "regime_flag_other": False})
        for w in PLANTED:
            self.assertNotIn(w, json.dumps(got, ensure_ascii=False))

    def test_confirmed_null_is_not_confirmed_and_other_types_fail(self):
        self.assertFalse(self.read(record(self.W, None))["confirmed"])
        self.assertIsNone(self.read(record(self.W, "Y")))
        self.assertIsNone(self.read(record(self.W, 1)))

    def test_schema_week_and_dates(self):
        r = record(self.W)
        r["schema"] = "macro-notes-public/2"
        self.assertIsNone(self.read(r))
        self.assertIsNone(self.read(record(self.W), week="2026-03-09"))          # 파일 이름의 주와 다름
        r = record(self.W)
        r["week"]["end"] = "2026-03-07"
        self.assertIsNone(self.read(r))
        r = record("2026-03-03")                                                  # 화요일
        self.assertIsNone(self.read(r, week="2026-03-03"))
        r = record(self.W)
        r["week"] = "2026-03-02"
        self.assertIsNone(self.read(r))

    def test_verdicts(self):
        for v in tb.VERDICTS["dur"] + ("채점 미완 0/7", "채점 미완 6/7"):
            self.assertIsNotNone(self.read(record(self.W, dur=(0.1, v))), v)
        for v in ("채점 미완 7/7", "Strong O/W", "Flattening", "", None, 1):
            self.assertIsNone(self.read(record(self.W, dur=(0.1, v))), v)
        self.assertIsNone(self.read(record(self.W, cur=(0.1, "O/W"))))            # 듀레이션 판정 글은 커브 칸에 없다

    def test_totals(self):
        self.assertEqual(self.read(record(self.W, dur=(None, "채점 미완 3/7")))["dur"]["total"], None)
        self.assertEqual(self.read(record(self.W, dur=(-0.0, "Neutral")))["dur"]["total"], 0.0)
        self.assertEqual(self.read(record(self.W, dur=(1, "강한 O/W")))["dur"]["total"], 1.0)
        for bad in (True, "0.5", [0.5], 1e9):
            self.assertIsNone(self.read(record(self.W, dur=(bad, "Neutral"))), bad)
        raw = rb(record(self.W)).replace(b'"total": 0.0', b'"total": NaN', 1)
        self.assertIsNone(self.read(raw))

    def test_edited_n(self):
        for bad in (True, -1, 1.5, "2", None):
            self.assertIsNone(self.read(record(self.W, edited=bad)), bad)
        self.assertEqual(self.read(record(self.W, edited=0))["edited_n"], 0)

    def test_regime_flag_outside_the_four_is_not_copied(self):
        for v in tb.REGIMES:
            got = self.read(record(self.W, regime=v))
            self.assertEqual((got["regime_flag"], got["regime_flag_other"]), (v, False))
        for v in ("A'", "D", "A/B", "판정불가", "a", 1, ["A"]):
            got = self.read(record(self.W, regime=v))
            self.assertIsNotNone(got, v)                                          # 판은 쓰고, 국면 칸만 옮기지 않는다
            self.assertEqual((got["regime_flag"], got["regime_flag_other"]), (None, True), v)   # 빈 칸과 가른다(글은 싣지 않는다)
        for v in (None, "", "  "):
            got = self.read(record(self.W, regime=v))
            self.assertEqual((got["regime_flag"], got["regime_flag_other"]), (None, False), v)
        r = record(self.W)
        r["state"]["flags"] = "A"
        self.assertIsNone(self.read(r))

    def test_bytes_bom_size_and_broken_json(self):
        self.assertIsNotNone(self.read(b"\xef\xbb\xbf" + rb(record(self.W))))
        self.assertIsNone(self.read(b"{not json"))
        self.assertIsNone(self.read(b"\xff\xfe"))
        self.assertIsNone(self.read(b""))
        self.assertIsNone(self.read(rb(record(self.W)) + b" " * tb.MAX_RECORD_BYTES))
        self.assertIsNone(self.read("문자열"))

    def test_record_path(self):
        self.assertEqual(tb.record_week("records/2026-03-02.json"), "2026-03-02")
        for p in ("records/README.md", "records/2026-13-01.json", "records/sub/2026-03-02.json", "x/records/2026-03-02.json",
                  "records/2026-03-02.json.bak", None):
            self.assertIsNone(tb.record_week(p), p)


class LateTest(unittest.TestCase):
    END = D(2026, 3, 8)                                   # 일요일 — 다음 월요일 2026-03-09

    def at(self, s):
        return tb._dt(s)

    def test_boundary_is_monday_1330_utc(self):
        self.assertFalse(tb.is_late(self.END, self.at("2026-03-09T13:30:00Z")))
        self.assertTrue(tb.is_late(self.END, self.at("2026-03-09T13:30:01Z")))
        self.assertFalse(tb.is_late(self.END, self.at("2026-03-09T13:02:00+09:00")))     # 운영자 PC의 13:02 KST
        self.assertTrue(tb.is_late(self.END, self.at("2026-03-09T22:31:00+09:00")))      # = 13:31 UTC
        self.assertFalse(tb.is_late(self.END, self.at("2026-03-07T10:00:00Z")))          # 미리 확정

    def test_times_are_written_in_utc(self):
        self.assertEqual(tb._iso(tb._dt("2026-11-18T18:20:39+09:00")), "2026-11-18T09:20:39+00:00")
        self.assertEqual(tb._iso(tb._dt("2026-11-18T09:20:39Z")), "2026-11-18T09:20:39+00:00")
        for bad in ("2026-11-18T09:20:39", "2026-11-18", "어제", None, 5):
            self.assertIsNone(tb._dt(bad), bad)


# ── 커밋 처리 ────────────────────────────────────────────────────────────────────────────────────────────────
class ProcessTest(unittest.TestCase):
    def run_spec(self, spec, weeks=None):
        commits = week_commits(spec)
        weeks = {} if weeks is None else weeks
        n = tb.process(weeks, [(s, tb._iso(tb._dt(at))) for s, at, _ in commits], MemSource(commits))
        return weeks, n, commits

    def test_first_confirmed_commit_locks_and_later_changes_are_shown_apart(self):
        weeks, skipped, commits = self.run_spec(SPEC)
        self.assertEqual(skipped, 0)
        w = weeks["2026-03-02"]
        self.assertEqual(w["lock"], {"sha": commits[2][0], "at": "2026-03-11T04:00:00+00:00", "first_upload": False,
                                     "in_history": True})                  # 확정 전 판이 먼저 올라왔다
        self.assertEqual((w["dur"], w["cur"], w["edited_n"], w["regime_flag"]),
                         ({"total": -0.6, "verdict": "U/W"}, {"total": 0.6, "verdict": "Flattening"}, 2, "A′"))
        self.assertEqual(w["changed_after"], {"at": "2026-03-17T04:00:00+00:00", "sha": commits[4][0],
                                              "dur": {"total": 0.0, "verdict": "Neutral"},
                                              "cur": {"total": 0.6, "verdict": "Flattening"}, "edited_n": 3})
        self.assertEqual(weeks["2026-03-09"]["lock"]["sha"], commits[3][0])

    def test_changed_back_clears_and_edited_only_is_not_a_change(self):
        base = SPEC[:3]
        weeks, _, _ = self.run_spec(base + [
            ("2026-03-12T04:00:00Z", {"2026-03-02": record("2026-03-02", True, (-0.6, "U/W"), (0.6, "Flattening"), edited=5)})])
        self.assertIsNone(weeks["2026-03-02"]["changed_after"])                  # 고친 칸 수만 바뀜 — 판정·합계 그대로
        self.assertEqual(weeks["2026-03-02"]["edited_n"], 2)                     # 처음 확정된 판의 값
        weeks, _, c = self.run_spec(base + [
            ("2026-03-12T04:00:00Z", {"2026-03-02": record("2026-03-02", True, (-1.2, "강한 U/W"), (0.6, "Flattening"))}),
            ("2026-03-13T04:00:00Z", {"2026-03-02": record("2026-03-02", True, (-1.2, "강한 U/W"), (0.6, "Flattening"), edited=9)}),
        ])
        self.assertEqual(weeks["2026-03-02"]["changed_after"]["sha"], c[3][0])   # 같은 값의 다음 판은 처음 바꾼 커밋 그대로
        self.assertEqual(weeks["2026-03-02"]["changed_after"]["edited_n"], 0)
        weeks, _, _ = self.run_spec(base + [
            ("2026-03-12T04:00:00Z", {"2026-03-02": record("2026-03-02", True, (-1.2, "강한 U/W"), (0.6, "Flattening"))}),
            ("2026-03-13T04:00:00Z", {"2026-03-02": record("2026-03-02", False, (-0.6, "U/W"), (0.6, "Flattening"))}),
        ])
        self.assertIsNone(weeks["2026-03-02"]["changed_after"])                  # 처음 값으로 돌아옴 — 확정을 풀어도 잠금은 그대로
        self.assertIsNotNone(weeks["2026-03-02"]["lock"])

    def test_unconfirmed_week_follows_the_latest_version(self):
        weeks, _, _ = self.run_spec(SPEC[:2])
        w = weeks["2026-03-02"]
        self.assertIsNone(w["lock"])
        self.assertEqual(w["dur"], {"total": -0.6, "verdict": "U/W"})

    def test_removed_week_keeps_its_lock_and_a_return_is_only_a_change(self):
        """한 번 잠근 판정은 바꾸지 않는다 — 지워도 판정 · 시각 · 셈은 그대로 두고 지운 커밋만 적고, 다시 올라와도 다시 잠그지 않는다."""
        weeks, _, c = self.run_spec(SPEC[:3] + [("2026-03-20T04:00:00Z", {"2026-03-02": None})])
        w = weeks["2026-03-02"]
        self.assertEqual(w["lock"]["sha"], c[2][0])
        self.assertEqual(w["dur"], {"total": -0.6, "verdict": "U/W"})
        self.assertEqual(w["removed"], {"at": "2026-03-20T04:00:00+00:00", "sha": c[3][0]})
        weeks, _, c = self.run_spec(SPEC[:3] + [
            ("2026-03-20T04:00:00Z", {"2026-03-02": None}),
            ("2026-03-23T04:00:00Z", {"2026-03-02": record("2026-03-02", True, (0.5, "O/W"), (0.0, "Neutral"))}),
        ])
        w = weeks["2026-03-02"]
        self.assertEqual((w["lock"]["sha"], w["lock"]["at"]), (c[2][0], "2026-03-11T04:00:00+00:00"))   # 다시 잠그지 않는다
        self.assertEqual(w["dur"]["verdict"], "U/W")
        self.assertIsNone(w["removed"])                                           # 다시 올라옴
        self.assertEqual((w["changed_after"]["sha"], w["changed_after"]["dur"]["verdict"]), (c[4][0], "O/W"))
        weeks, _, _ = self.run_spec(SPEC[:3] + [
            ("2026-03-20T04:00:00Z", {"2026-03-02": None}),
            ("2026-03-21T04:00:00Z", {"2026-03-02": record("2026-03-02", False, (-0.6, "U/W"), (0.6, "Flattening"))}),
        ])
        self.assertEqual((weeks["2026-03-02"]["removed"], weeks["2026-03-02"]["changed_after"]), (None, None))   # 같은 값으로 돌아옴
        weeks, skipped, _ = self.run_spec(SPEC[:3] + [
            ("2026-03-20T04:00:00Z", {"2026-03-02": None}),
            ("2026-03-21T04:00:00Z", {"2026-03-02": record("2026-03-02", True, (0.5, "엉뚱한 판정"))}),
        ])
        self.assertEqual(skipped, 1)
        self.assertIsNone(weeks["2026-03-02"]["removed"])                         # 꼴이 어긋난 판이어도 파일은 있다
        weeks, _, _ = self.run_spec(SPEC[:2] + [("2026-03-20T04:00:00Z", {"2026-03-02": None})])
        self.assertNotIn("2026-03-02", weeks)                                     # 확정 전인 주는 목록에서 뺀다
        weeks, _, c = self.run_spec(SPEC[:2] + [
            ("2026-03-20T04:00:00Z", {"2026-03-02": None}),
            ("2026-03-21T04:00:00Z", {"2026-03-02": record("2026-03-02", True)})])
        self.assertEqual(weeks["2026-03-02"]["lock"]["sha"], c[3][0])            # 잠근 적 없는 주는 처음 확정본으로 잠근다

    def test_first_upload_marks_a_week_that_appeared_already_confirmed(self):
        weeks, _, _ = self.run_spec(SPEC)
        self.assertFalse(weeks["2026-03-02"]["lock"]["first_upload"])
        self.assertFalse(weeks["2026-03-09"]["lock"]["first_upload"])
        weeks, _, _ = self.run_spec([("2026-03-11T04:00:00Z", {"2026-03-02": record("2026-03-02", True)})])
        self.assertTrue(weeks["2026-03-02"]["lock"]["first_upload"])             # 처음 올라온 판이 곧 확정본

    def test_renamed_file_marks_the_old_week_and_locks_the_new(self):
        commits = week_commits(SPEC[:3])
        old, new = path("2026-03-02"), path("2026-03-16")
        commits.append((sha_of(99), "2026-03-24T04:00:00Z",
                        {new: ("R", old, rb(record("2026-03-16", True)))}))
        weeks = {}
        tb.process(weeks, [(s, tb._iso(tb._dt(at))) for s, at, _ in commits], MemSource(commits))
        self.assertEqual(weeks["2026-03-02"]["removed"], {"at": "2026-03-24T04:00:00+00:00", "sha": sha_of(99)})
        self.assertEqual(weeks["2026-03-02"]["lock"]["sha"], commits[2][0])
        self.assertEqual(weeks["2026-03-16"]["lock"]["sha"], sha_of(99))
        commits = week_commits(SPEC[:2])                                          # 확정 전인 주를 옮기면 옛 주는 빠진다
        commits.append((sha_of(98), "2026-03-24T04:00:00Z", {new: ("R", old, rb(record("2026-03-16")))}))
        weeks = {}
        tb.process(weeks, [(s, tb._iso(tb._dt(at))) for s, at, _ in commits], MemSource(commits))
        self.assertEqual(list(weeks), ["2026-03-16"])

    def test_kept_locks_skip_versions_up_to_the_lock_time(self):
        """고쳐 쓴 기록을 다시 셀 때 — 넘겨받은 잠금의 시각 이하 판은 보지도 받지도 않는다."""
        commits = week_commits(SPEC)
        weeks = {"2026-03-02": {"week": "2026-03-02", "end": "2026-03-08",
                                "lock": {"sha": "f" * 40, "at": "2026-03-11T04:00:00+00:00", "first_upload": False,
                                         "in_history": False},
                                "dur": {"total": -0.6, "verdict": "U/W"}, "cur": {"total": 0.6, "verdict": "Flattening"},
                                "edited_n": 2, "regime_flag": None, "regime_flag_other": False, "changed_after": None,
                                "removed": None}}
        src = MemSource(commits)
        asked = []
        orig = src.content
        src.content = lambda sha, p: asked.append((sha, p)) or orig(sha, p)
        tb.process(weeks, [(s, tb._iso(tb._dt(at))) for s, at, _ in commits], src,
                   kept={"2026-03-02": tb._dt("2026-03-11T04:00:00Z")})
        w = weeks["2026-03-02"]
        self.assertEqual(w["lock"]["sha"], "f" * 40)
        self.assertEqual(w["changed_after"]["sha"], commits[4][0])                 # 잠근 뒤의 판만
        self.assertNotIn((commits[0][0], path("2026-03-02")), asked)               # 잠근 시각 앞 판은 받지 않는다
        self.assertNotIn((commits[2][0], path("2026-03-02")), asked)               # 잠근 시각과 같은 판도

    def test_bad_versions_are_skipped_and_never_lock(self):
        bad = record("2026-03-02", True, (0.6, "엉뚱한 판정"))
        spec = [("2026-03-09T04:00:00Z", {"2026-03-02": bad}),
                ("2026-03-10T04:00:00Z", {"2026-03-02": record("2026-03-09", True)}),            # 다른 주의 내용
                ("2026-03-11T04:00:00Z", {"2026-03-02": record("2026-03-02", True, (-0.6, "U/W"))})]
        weeks, skipped, c = self.run_spec(spec)
        self.assertEqual(skipped, 2)
        self.assertEqual(weeks["2026-03-02"]["lock"]["sha"], c[2][0])

    def test_other_paths_are_ignored(self):
        commits = [(sha_of(1), "2026-03-09T04:00:00Z", {"records/README.md": b"# x", "web/build.py": b"x",
                                                        path("2026-03-02"): rb(record("2026-03-02", True))})]
        weeks = {}
        self.assertEqual(tb.process(weeks, [(sha_of(1), "2026-03-09T04:00:00+00:00")], MemSource(commits)), 0)
        self.assertEqual(list(weeks), ["2026-03-02"])


# ── 결과(출발 · 끝) ──────────────────────────────────────────────────────────────────────────────────────────
def wk(week, at=None, dur="Neutral", cur="Neutral"):
    s = D.fromisoformat(week)
    lock = {"sha": "a" * 40, "at": at, "first_upload": False, "in_history": True} if at else None
    return {"week": week, "end": plus(s, 6).isoformat(), "lock": lock,
            "dur": {"total": 0.0, "verdict": dur}, "cur": {"total": 0.0, "verdict": cur}, "edited_n": 0, "regime_flag": None,
            "regime_flag_other": False, "changed_after": None, "removed": None}


class OutcomeTest(unittest.TestCase):
    def setUp(self):
        ds = fridays(30)
        self.pts = [(d, lb._dec(v)) for d, v in [(D.fromisoformat(a), b) for a, b in linear(ds, 4.0, 0.01)]]

    def out(self, w, h=1, base=None, pts=None):
        late = bool(w["lock"]) and tb.is_late(D.fromisoformat(w["end"]), tb._dt(w["lock"]["at"]))
        return tb.outcome(self.pts if pts is None else pts, w, late, h, base)

    def test_on_time_starts_at_the_weeks_last_point(self):
        o = self.out(wk("2026-03-02", "2026-03-09T04:00:00Z"), h=1, base=1.0)
        self.assertEqual(o, {"state": "done", "start": "2026-03-06", "end": "2026-03-13", "change_bp": 1.0, "demeaned_bp": 0.0})
        o = self.out(wk("2026-03-02", "2026-03-09T04:00:00Z"), h=4, base=1.5)
        self.assertEqual((o["start"], o["end"], o["change_bp"], o["demeaned_bp"]), ("2026-03-06", "2026-04-03", 4.0, 2.5))

    def test_holiday_week_uses_its_thursday_point(self):
        pts = [p for p in self.pts if p[0] != D(2026, 3, 6)] + [(D(2026, 3, 5), lb._dec(4.5))]
        pts.sort()
        o = self.out(wk("2026-03-02", "2026-03-09T04:00:00Z"), pts=pts)
        self.assertEqual(o["start"], "2026-03-05")
        self.assertEqual(o["end"], "2026-03-13")                                 # 03-12 ±3 안의 가장 가까운 점

    def test_late_lock_starts_on_or_after_the_lock_day(self):
        o = self.out(wk("2026-03-02", "2026-03-09T13:31:00Z"))                   # 늦게 확정 — 월요일 → 그 주 금요일 점
        self.assertEqual(o["start"], "2026-03-13")
        o = self.out(wk("2026-03-02", "2026-03-13T23:00:00Z"))                   # 금요일 잠금 — 그날 점(UTC 날짜)
        self.assertEqual(o["start"], "2026-03-13")
        o = self.out(wk("2026-03-02", "2026-03-14T01:00:00+09:00"))              # KST 토요일 01시 = UTC 금요일
        self.assertEqual(o["start"], "2026-03-13")
        gap = [p for p in self.pts if not D(2026, 3, 9) <= p[0] <= D(2026, 3, 25)]
        o = self.out(wk("2026-03-02", "2026-03-10T00:00:00Z"), pts=gap)          # 7일 안에 점 없음
        self.assertEqual((o["state"], o["start"]), ("missing", None))

    def test_pending_and_missing(self):
        last = self.pts[-1][0]
        o = self.out(wk("2026-03-02"))                                           # 확정 전
        self.assertEqual(o, tb.EMPTY)
        w = wk(plus(last, -4).isoformat(), plus(last, 3).isoformat() + "T04:00:00Z")   # 마지막 점이 든 주 — 1주 뒤가 아직
        o = self.out(w)
        self.assertEqual((o["state"], o["start"], o["end"]), ("pending", last.isoformat(), None))
        w = wk(plus(last, 10).isoformat(), plus(last, 17).isoformat() + "T04:00:00Z")  # 그래프가 아직 그 주에 닿지 않음
        self.assertEqual(self.out(w), tb.EMPTY)
        w = wk(plus(last, 10).isoformat(), plus(last, 30).isoformat() + "T04:00:00Z")  # 늦게 확정 · 점이 아직 없음
        self.assertEqual(self.out(w)["state"], "pending")
        w = wk("2025-12-01", "2025-12-08T04:00:00Z")                              # 그래프 창 앞
        self.assertEqual(self.out(w), {**tb.EMPTY, "state": "missing"})
        hole = [p for p in self.pts if p[0] != D(2026, 3, 6)]
        self.assertEqual(self.out(wk("2026-03-02", "2026-03-09T04:00:00Z"), pts=hole)["state"], "missing")
        hole = [p for p in self.pts if not D(2026, 3, 10) <= p[0] <= D(2026, 3, 16)]
        o = self.out(wk("2026-03-02", "2026-03-09T04:00:00Z"), pts=hole)          # 끝 점 범위(03-10~03-16)에 점 없음
        self.assertEqual((o["state"], o["start"]), ("missing", "2026-03-06"))
        self.assertEqual(self.out(wk("2026-03-02", "2026-03-09T04:00:00Z"), pts=[])["state"], "missing")

    def test_baseline_for_one_week_is_the_ledger_function(self):
        b = lb.baseline(self.pts, 1)
        self.assertEqual((float(b[0]), b[1]), (1.0, len(self.pts) - 2))      # 마지막 두 점은 끝 범위가 그래프 끝을 넘는다


# ── 요약 ─────────────────────────────────────────────────────────────────────────────────────────────────────
def summary_world(n_after, verdicts=None, before=0, extra=()):
    """약속 뒤에 잠근 주 n_after개(+ 약속 전 before개) — DGS10은 주마다 +1bp, 다섯째 주마다 −3bp(오른 몫을 아는 선)."""
    ds = fridays(100, start=D(2026, 9, 4))
    vals, v = [], 4.0
    for k, d in enumerate(ds):
        vals.append([d.isoformat(), round(v, 4)])
        v += -0.03 if k % 5 == 4 else 0.01
    weeks = {}
    mondays = [plus(D(2026, 11, 23), 7 * k) for k in range(n_after)]
    for k, m in enumerate(mondays):
        w = wk(m.isoformat(), plus(m, 7).isoformat() + "T04:00:00Z", dur=(verdicts or ["O/W"])[k % len(verdicts or ["O/W"])])
        weeks[w["week"]] = w
    for k in range(before):
        m = plus(D(2026, 9, 28), 7 * k)
        w = wk(m.isoformat(), plus(m, 7).isoformat() + "T04:00:00Z", dur="O/W")
        weeks[w["week"]] = w
    for w in extra:
        weeks[w["week"]] = w
    return weeks, charts_obj(vals, linear(ds, 0.5, 0.0))


class SummaryTest(unittest.TestCase):
    def build(self, weeks, charts):
        with tempfile.TemporaryDirectory() as d:
            write_json(os.path.join(d, "charts.json"), charts)
            date, lines = lb.load_charts(os.path.join(d, "charts.json"))
        src = {"newest_commit": None, "checked_at": NOW, "via": "api", "skipped_versions": 0}
        return tb.build(weeks, src, date, lines, [], [], NOW)

    def test_on_hold_below_n_min(self):
        weeks, charts = summary_world(9)
        s = self.build(weeks, charts)["summary"]
        self.assertEqual(s["dur"]["ow"]["1"], {"n": 9, "starts": 9, "mean_demeaned_bp": None, "up_share": None})
        self.assertEqual(s["dur"]["uw"]["1"]["n"], 0)

    def test_known_answer_at_n_min(self):
        weeks, charts = summary_world(10)
        obj = self.build(weeks, charts)
        done = [w["outcomes"]["1"]["dur"] for w in obj["weeks"] if w["outcomes"]["1"]["dur"]["state"] == "done"]
        self.assertEqual(len(done), 10)
        s = obj["summary"]["dur"]["ow"]["1"]
        ups = sum(1 for o in done if o["change_bp"] > 0)
        mean = sum(o["demeaned_bp"] for o in done) / 10
        self.assertEqual((s["n"], s["starts"]), (10, 10))
        self.assertEqual(s["up_share"], round(ups / 10, 2))
        self.assertAlmostEqual(s["mean_demeaned_bp"], round(mean, 1), places=6)
        self.assertNotIn(0, {round(ups / 10, 2), 1})                                 # 오른 주와 내린 주가 섞인 세계

    def test_before_protocol_unscored_in_progress_and_pending_are_not_counted(self):
        extra = [wk("2026-12-28", "2027-01-04T04:00:00Z", dur="채점 미완 5/7"), wk("2027-01-04", None, dur="O/W")]
        weeks, charts = summary_world(10, before=5, extra=extra)
        obj = self.build(weeks, charts)
        s = obj["summary"]["dur"]
        self.assertEqual(s["ow"]["1"]["n"], 8)                                   # 열 주 가운데 둘을 채점 미완 · 확정 전으로 바꿈
        before = [w for w in obj["weeks"] if w["before_protocol"]]
        self.assertEqual(len(before), 5)
        self.assertTrue(all(w["outcomes"]["1"]["dur"]["state"] == "done" for w in before))
        weeks, charts = summary_world(10)
        charts["overview"][0]["lines"][0]["points"] = [p for p in charts["overview"][0]["lines"][0]["points"]
                                                       if p[0] <= "2027-01-22"]
        obj = self.build(weeks, charts)
        self.assertEqual(obj["summary"]["dur"]["ow"]["1"]["n"], 7)            # 끝 범위가 그래프 끝을 넘는 세 주는 기다리는 중
        self.assertEqual(obj["weeks"][0]["outcomes"]["1"]["dur"]["state"], "pending")

    def test_weeks_sharing_a_start_count_once(self):
        """늦게 확정한 주가 뒤 주와 출발 점을 나누면 같은 움직임 — 출발 점마다 하나로 세고, 문턱도 출발 점 수로 본다."""
        weeks, charts = summary_world(10)
        late = wk("2026-11-16", "2026-11-25T04:00:00Z")                         # 수요일에 잠금 — 출발은 그 주(11-23 주)의 금요일 점
        late["dur"]["verdict"] = "O/W"
        weeks[late["week"]] = late
        obj = self.build(weeks, charts)
        row = next(w for w in obj["weeks"] if w["week"] == "2026-11-16")
        self.assertTrue(row["lock"]["late"])
        twin = next(w for w in obj["weeks"] if w["week"] == "2026-11-23")
        self.assertEqual(row["outcomes"]["1"]["dur"], twin["outcomes"]["1"]["dur"])
        s = obj["summary"]["dur"]["ow"]["1"]
        self.assertEqual((s["n"], s["starts"]), (11, 10))
        alone = self.build(summary_world(10)[0], charts)["summary"]["dur"]["ow"]["1"]
        self.assertEqual((s["mean_demeaned_bp"], s["up_share"]), (alone["mean_demeaned_bp"], alone["up_share"]))   # 겹친 주는 더하지 않는다
        weeks, charts = summary_world(9)                                           # 주는 10개여도 출발 점이 9개면 판단 보류
        late = wk("2026-11-16", "2026-11-25T04:00:00Z", dur="O/W")
        weeks[late["week"]] = late
        s = self.build(weeks, charts)["summary"]["dur"]["ow"]["1"]
        self.assertEqual((s["n"], s["starts"], s["mean_demeaned_bp"], s["up_share"]), (10, 9, None, None))

    def test_strong_verdicts_join_their_side(self):
        weeks, charts = summary_world(10, verdicts=["강한 O/W", "O/W", "강한 U/W", "Neutral"])
        s = self.build(weeks, charts)["summary"]["dur"]
        self.assertEqual((s["ow"]["1"]["n"], s["uw"]["1"]["n"], s["neutral"]["1"]["n"]), (6, 2, 2))
        self.assertEqual(set(self.build(weeks, charts)["summary"]["cur"]), {"flat", "neutral", "steep"})

    def test_lock_day_is_the_utc_date(self):
        m = D(2026, 11, 9)
        w1 = wk(m.isoformat(), "2026-11-18T20:00:00Z")                            # KST로는 11-19 05시 — UTC 날짜는 약속 전
        w2 = wk(plus(m, 7).isoformat(), "2026-11-19T00:00:00Z")
        obj = self.build({w1["week"]: w1, w2["week"]: w2}, summary_world(1)[1])
        got = {w["week"]: w["before_protocol"] for w in obj["weeks"]}
        self.assertEqual(got, {"2026-11-09": True, "2026-11-16": False})


# ── 맥락 ─────────────────────────────────────────────────────────────────────────────────────────────────────
class ContextTest(unittest.TestCase):
    def test_site_snapshot_at_the_weeks_sunday(self):
        snaps = [snapshot("2026-03-06", with_regime=False, met=1, total=3), snapshot("2026-03-08", reg=None, met=2, total=4),
                 snapshot("2026-03-09", reg="B")]
        dd = DataDir(snaps=snaps)
        try:
            got, _ = lb.load_history(os.path.join(dd.path, "history"))
        finally:
            dd.cleanup()
        self.assertEqual(tb.site_at(got, D(2026, 3, 8)),
                         {"snapshot": "2026-03-08", "core": "2/11", "met": "2/4", "candidate": "판정불가"})
        self.assertEqual(tb.site_at(got, D(2026, 3, 7)),
                         {"snapshot": "2026-03-06", "core": None, "met": "1/3", "candidate": None})
        self.assertEqual(tb.site_at(got, D(2026, 3, 1)),
                         {"snapshot": None, "core": None, "met": None, "candidate": None})

    def test_lp_month_known_by_sunday(self):
        rows = [("2026-01", "2026-02-27", "L0", "P+"), ("2026-02", "2026-03-27", "L+", "P0"), ("2026-03", "2026-04-30", "L+", "?")]
        dd = DataDir(lp=lp_obj(rows))
        try:
            got = tb.load_lp(dd.file("lp.json"))
        finally:
            dd.cleanup()
        self.assertEqual(tb.lp_at(got, D(2026, 3, 29)),
                         {"month": "2026-02", "L": "L+", "P": "P0", "cell": lpf.cell("L+", "P0")[0]})
        self.assertEqual(tb.lp_at(got, D(2026, 3, 1))["month"], "2026-01")
        self.assertIsNone(tb.lp_at(got, D(2026, 2, 1)))
        self.assertEqual(tb.lp_at(got, D(2026, 5, 3))["cell"], "판정 보류(물가)")

    def test_lp_rows_that_do_not_match_the_grid_are_dropped(self):
        obj = lp_obj([("2026-01", "2026-02-27", "L0", "P+"), ("2026-02", "2026-03-27", "L+", "P0")])
        obj["history"][1]["cell"] = "지어낸 칸 이름"
        obj["history"].append({"month": "2026-03", "known": "2026-04-30", "L": "L9", "P": "P+", "cell": "x"})
        obj["history"].append({"month": "2026-04", "known": "어느 날", "L": "L0", "P": "P+", "cell": lpf.cell("L0", "P+")[0]})
        dd = DataDir(lp=obj)
        try:
            got = tb.load_lp(dd.file("lp.json"))
            self.assertEqual([r[0] for r in got], ["2026-01"])
            self.assertEqual(tb.load_lp(dd.file("없는.json")), [])
        finally:
            dd.cleanup()


# ── 실행 · 수신 ──────────────────────────────────────────────────────────────────────────────────────────────
class ApiRunTest(unittest.TestCase):
    def setUp(self):
        self.dd = DataDir(snaps=[snapshot("2026-03-08"), snapshot("2026-03-15", reg="A")],
                          lp=lp_obj([("2026-01", "2026-02-27", "L0", "P+")]))
        self.commits = week_commits(SPEC)
        self.commits.insert(2, (sha_of(50), "2026-03-10T05:00:00Z", {"records/README.md": b"# readme"}))

    def tearDown(self):
        self.dd.cleanup()

    def gh(self, **kw):
        return FakeGitHub(self.commits, **kw)

    def run_api(self, gh, env=None, args=(), now=NOW, clock=None):
        return run_main(["--data", self.dd.path, *args], now=now, opener=gh, env={} if env is None else env,
                        clock=clock or Clock())

    def test_first_run_reads_every_commit_and_writes_the_contract(self):
        gh = self.gh()
        code, out, _ = self.run_api(gh)
        self.assertEqual(code, 0)
        obj = read_json(self.dd.file())
        check_timeline(self, obj)
        n_raw = sum(1 for _, _, f in self.commits for p in f if tb.record_week(p))
        self.assertEqual(len(gh.calls), 1 + len(self.commits) + n_raw)
        self.assertIn(f"요청 {len(gh.calls)}번", out)
        self.assertEqual(obj["source"]["newest_commit"], self.commits[-1][0])
        self.assertEqual(obj["source"]["checked_at"], NOW)
        self.assertEqual([w["week"] for w in obj["weeks"]], ["2026-03-09", "2026-03-02"])
        w = obj["weeks"][1]
        self.assertEqual((w["state"], w["lock"]["sha"], w["lock"]["late"], w["before_protocol"], w["edited_n"], w["regime_flag"],
                          w["lock"]["first_upload"], w["lock"]["in_history"], w["removed"]),
                         ("confirmed", self.commits[3][0], True, True, 2, "A′", False, True, None))
        self.assertIsNone(obj["source"]["rewritten_at"])
        self.assertEqual(w["changed_after"]["sha"], self.commits[5][0])
        self.assertEqual(w["site"], {"snapshot": "2026-03-08", "core": "2/11", "met": "1/3", "candidate": "A′"})
        self.assertEqual(w["lp"]["month"], "2026-01")
        self.assertEqual(w["outcomes"]["1"]["dur"]["start"], "2026-03-13")    # 늦게 확정(수요일) — 잠근 날 뒤 첫 점
        w = obj["weeks"][0]
        self.assertFalse(w["lock"]["late"])                                     # 월요일 04:00 UTC — 늦지 않음
        self.assertEqual(w["outcomes"]["1"]["dur"]["start"], "2026-03-13")    # 그 주 금요일 점
        text = json.dumps(obj, ensure_ascii=False)
        for word in PLANTED:
            self.assertNotIn(word, text)

    def test_headers_and_the_token_only_to_the_api_host(self):
        gh = self.gh()
        code, out, err = self.run_api(gh, env={"GITHUB_TOKEN": TOKEN})
        self.assertEqual(code, 0)
        hosts = {h for h, _, _, _ in gh.calls}
        self.assertEqual(hosts, {tb.API_HOST, tb.RAW_HOST})
        for host, url, hd, timeout in gh.calls:
            self.assertEqual(hd["user-agent"], tb.USER_AGENT)
            self.assertNotIn("@", hd["user-agent"])
            self.assertLessEqual(timeout, tb.TIMEOUT)
            if host == tb.API_HOST:
                self.assertEqual(hd["accept"], "application/vnd.github+json")
                self.assertEqual(hd["authorization"], "Bearer " + TOKEN)
            else:
                self.assertNotIn("authorization", hd)
        with open(self.dd.file(), encoding="utf-8") as f:
            text = f.read()
        for t in (out, err, text):
            self.assertNotIn(TOKEN, t)
            self.assertNotIn("FAKEtoken", t)

    def test_no_token_no_authorization_and_odd_tokens_are_not_sent(self):
        for env in ({}, {"GITHUB_TOKEN": ""}, {"GITHUB_TOKEN": "a b c d e f g h"}, {"GITHUB_TOKEN": "tok\nX-Evil: 1"}):
            gh = self.gh()
            self.run_api(gh, env=env)
            self.assertTrue(all("authorization" not in hd for _, _, hd, _ in gh.calls), env)

    def test_second_run_only_asks_for_new_commits(self):
        self.run_api(self.gh())
        gh = self.gh()
        code, out, _ = self.run_api(gh, now="2027-07-02T00:00:00+00:00")
        self.assertEqual(len(gh.calls), 1)                                       # 목록 한 쪽 — 맨 위가 직전의 마지막 커밋
        self.assertIn("새 커밋 0개", out)
        self.commits.append((sha_of(60), "2026-03-23T04:00:00Z", {path("2026-03-16"): rb(record("2026-03-16", True))}))
        gh = self.gh()
        self.run_api(gh, now="2027-07-03T00:00:00+00:00")
        self.assertEqual(len(gh.calls), 3)                                       # 목록 · 커밋 · 파일 하나
        obj = read_json(self.dd.file())
        self.assertEqual([w["week"] for w in obj["weeks"]], ["2026-03-16", "2026-03-09", "2026-03-02"])
        self.assertEqual(obj["source"]["newest_commit"], sha_of(60))

    def test_incremental_equals_a_full_rebuild(self):
        half = self.commits[:4]
        full = self.commits
        self.commits = half
        self.run_api(self.gh())
        self.commits = full
        self.run_api(self.gh())
        inc = read_json(self.dd.file())
        with tempfile.TemporaryDirectory() as out:
            run_main(["--data", self.dd.path, "--out", out, "--rebuild"], opener=self.gh(), env={}, clock=Clock())
            reb = read_json(os.path.join(out, tb.FILE))
        self.assertEqual(inc["weeks"], reb["weeks"])
        self.assertEqual(inc["source"], reb["source"])

    def test_pages(self):
        gh = self.gh()
        with mock.patch.object(tb, "PER_PAGE", 2):
            self.run_api(gh)
        lists = [u for _, u, _, _ in gh.calls if "/commits?" in u]
        self.assertEqual(len(lists), 4)                                          # 커밋 6개 → 2 · 2 · 2 · 빈 쪽
        self.assertEqual(read_json(self.dd.file())["source"]["newest_commit"], self.commits[-1][0])
        self.run_api(self.gh())                                                  # 이어서 — 멈춤 커밋이 첫 쪽에
        self.commits.append((sha_of(61), "2026-03-30T04:00:00Z", {path("2026-03-23"): rb(record("2026-03-23"))}))
        gh = self.gh()
        with mock.patch.object(tb, "PER_PAGE", 2):
            self.run_api(gh)
        self.assertEqual(len([u for _, u, _, _ in gh.calls if "/commits?" in u]), 1)

    def test_too_many_pages_is_a_failure(self):
        with mock.patch.object(tb, "PER_PAGE", 1), mock.patch.object(tb, "MAX_PAGES", 3):
            code, out, _ = self.run_api(self.gh())
        self.assertEqual(code, 0)
        self.assertIn("::warning::", out)
        self.assertFalse(os.path.exists(self.dd.file()))

    def failing_run(self, **kw):
        self.run_api(self.gh())
        before = read_json(self.dd.file())
        self.commits.append((sha_of(70), "2026-03-23T04:00:00Z", {path("2026-03-16"): rb(record("2026-03-16", True)),
                                                                  path("2026-03-02"): None}))
        code, out, err = self.run_api(self.gh(**kw), now="2027-07-02T00:00:00+00:00")
        return before, code, out, err

    def test_http_error_mid_way_keeps_the_previous_file(self):
        before, code, out, _ = self.failing_run(fail={"/records/2026-03-16.json": 500})
        self.assertEqual(code, 0)
        self.assertEqual(out.count("::warning::"), 1)
        self.assertIn("HTTP 오류 500", out)
        self.assertEqual(read_json(self.dd.file()), before)                     # 반쯤 처리한 커밋 목록은 쓰지 않는다(지운 주도 그대로)

    def test_rate_limit_and_redirect_reasons(self):
        for code_, word in ((403, "요청 한도 또는 거절"), (429, "요청 한도 또는 거절"), (301, "다른 주소로 옮김")):
            self.tearDown()
            self.setUp()
            _, code, out, _ = self.failing_run(fail={"/commits?": code_})
            self.assertEqual(code, 0)
            self.assertIn(word, out)

    def test_budget_runs_out(self):
        clock = Clock()
        gh = self.gh(clock=clock, cost=10.0)
        code, out, _ = self.run_api(gh, clock=clock, args=("--budget", "25"))
        self.assertEqual(code, 0)
        self.assertIn("시간 상한", out)
        self.assertFalse(os.path.exists(self.dd.file()))                        # 직전 파일이 없으면 아무것도 쓰지 않는다
        self.assertLessEqual(len(gh.calls), 3)

    def test_failure_still_refreshes_the_local_columns(self):
        self.run_api(self.gh())
        before = read_json(self.dd.file())
        write_json(os.path.join(self.dd.path, "history", "2026-03-15.json"), snapshot("2026-03-15", reg="C"))
        code, out, _ = self.run_api(self.gh(fail={"/commits?": 502}), now="2027-07-05T00:00:00+00:00")
        after = read_json(self.dd.file())
        self.assertEqual(after["source"], before["source"])                     # checked_at도 그대로 — 읽지 못한 날
        self.assertEqual(after["weeks"][0]["site"]["candidate"], "C")
        self.assertEqual(after["generated_at"], "2027-07-05T00:00:00+00:00")
        strip = lambda o: [{k: v for k, v in w.items() if k != "site"} for w in o["weeks"]]
        self.assertEqual(strip(after), strip(before))

    def test_failure_without_local_changes_does_not_rewrite(self):
        self.run_api(self.gh())
        mtime = os.stat(self.dd.file()).st_mtime_ns
        code, out, _ = self.run_api(self.gh(fail={"/commits?": 502}), now="2027-07-05T00:00:00+00:00")
        self.assertIn("다시 쓰지 않음", out)
        self.assertEqual(os.stat(self.dd.file()).st_mtime_ns, mtime)

    def rewritten(self, spec, tag):
        """같은 내용 · 새 sha(고쳐 쓴 기록) — [(at, {주: 공개본 | None})] → 커밋 목록."""
        return [(hashlib.sha1(f"{tag}-{i}".encode()).hexdigest(), at, {path(w): (None if r is None else rb(r)) for w, r in f.items()})
                for i, (at, f) in enumerate(spec)]

    def test_history_rewritten_keeps_the_locks(self):
        """기록을 고쳐 써 직전의 마지막 커밋이 없으면 — 잠근 판정 · 시각은 그대로(약속 전도 그대로), 잠근 커밋이 지금 기록에 있는지만
        적고, 잠근 시각 뒤의 커밋으로 확정 뒤 고침 · 지움을 다시 센다. 확정 전인 주는 새 기록에서 다시."""
        self.run_api(self.gh())
        before = {w["week"]: w for w in read_json(self.dd.file())["weeks"]}
        # 한 커밋으로 뭉쳐 다시 올림(2027-07-05) — 03-02는 마지막 값(Neutral)으로, 03-09는 그대로, 03-16은 새로 확정본
        self.commits = self.rewritten([("2027-07-05T00:00:00Z", {
            "2026-03-02": record("2026-03-02", True, (0.0, "Neutral"), (0.6, "Flattening"), edited=3),
            "2026-03-09": record("2026-03-09", True, (0.7, "O/W"), (-0.5, "Steepening")),
            "2026-03-16": record("2026-03-16", True)})], "squash")
        code, out, _ = self.run_api(self.gh(), now="2027-07-06T00:00:00+00:00")
        self.assertEqual(code, 0)
        self.assertIn("기록을 고쳐 씀", out)
        self.assertIn("잠근 커밋이 지금 기록에 없는 주 2개", out)
        obj = read_json(self.dd.file())
        check_timeline(self, obj)
        got = {w["week"]: w for w in obj["weeks"]}
        for wk_ in ("2026-03-02", "2026-03-09"):
            a, b = before[wk_], got[wk_]
            self.assertEqual({k: v for k, v in b["lock"].items() if k != "in_history"},
                             {k: v for k, v in a["lock"].items() if k != "in_history"})
            self.assertFalse(b["lock"]["in_history"])
            self.assertEqual((b["dur"], b["cur"], b["before_protocol"]), (a["dur"], a["cur"], True))
        self.assertEqual((got["2026-03-02"]["changed_after"]["sha"], got["2026-03-02"]["changed_after"]["dur"]["verdict"]),
                         (self.commits[0][0], "Neutral"))
        self.assertIsNone(got["2026-03-09"]["changed_after"])
        self.assertEqual(got["2026-03-16"]["lock"]["at"], "2027-07-05T00:00:00+00:00")   # 처음 보는 주는 새 기록에서 잠근다
        self.assertTrue(got["2026-03-16"]["lock"]["in_history"])
        self.assertEqual(obj["source"]["rewritten_at"], "2027-07-06T00:00:00+00:00")
        self.assertEqual(obj["summary"]["dur"]["neutral"]["1"]["n"], 0)                  # 약속 전 주가 요약으로 옮겨 가지 않는다
        # 다음 실행은 이어서 — 고쳐 쓴 표시와 잠금은 그대로
        gh = self.gh()
        self.run_api(gh, now="2027-07-07T00:00:00+00:00")
        self.assertEqual(len(gh.calls), 1)
        again = read_json(self.dd.file())
        self.assertEqual(again["weeks"], obj["weeks"])
        self.assertEqual(again["source"]["rewritten_at"], "2027-07-06T00:00:00+00:00")

    def test_history_rewritten_after_the_lock_keeps_the_lock_commit(self):
        self.run_api(self.gh())
        self.commits = week_commits(SPEC[:3])                                   # 앞부분은 같은 sha, 뒤만 사라짐
        code, out, _ = self.run_api(self.gh(), now="2027-07-02T00:00:00+00:00")
        obj = read_json(self.dd.file())
        got = {w["week"]: w for w in obj["weeks"]}
        self.assertTrue(got["2026-03-02"]["lock"]["in_history"])
        self.assertIsNone(got["2026-03-02"]["changed_after"])                   # 고친 커밋이 사라짐 — 지금 기록 기준으로 다시
        self.assertFalse(got["2026-03-09"]["lock"]["in_history"])
        self.assertEqual(got["2026-03-09"]["dur"]["verdict"], "O/W")            # 잠근 시각 앞의 확정 전 판은 보지 않는다
        self.assertIsNone(got["2026-03-09"]["changed_after"])
        self.assertEqual(obj["source"]["newest_commit"], self.commits[-1][0])

    def test_rewritten_history_with_an_empty_list_keeps_the_previous_file(self):
        self.run_api(self.gh())
        before = read_json(self.dd.file())
        self.commits = []
        code, out, _ = self.run_api(self.gh(), now="2027-07-02T00:00:00+00:00")
        self.assertEqual(code, 0)
        self.assertIn("커밋 목록이 비었음", out)
        self.assertEqual(read_json(self.dd.file())["weeks"], before["weeks"])
        self.assertEqual(read_json(self.dd.file())["source"], before["source"])

    def test_rebuild_flag_resets_the_locks(self):
        self.run_api(self.gh())
        self.commits = self.rewritten([("2027-07-05T00:00:00Z", {"2026-03-02": record("2026-03-02", True)})], "flag")
        self.run_api(self.gh(), args=("--rebuild",), now="2027-07-06T00:00:00+00:00")
        obj = read_json(self.dd.file())
        self.assertEqual([w["week"] for w in obj["weeks"]], ["2026-03-02"])
        self.assertEqual(obj["weeks"][0]["lock"]["at"], "2027-07-05T00:00:00+00:00")
        self.assertIsNone(obj["source"]["rewritten_at"])

    def test_offline_uses_the_previous_state(self):
        code, out, _ = run_main(["--data", self.dd.path, "--offline"], env={})
        self.assertIn("아무것도 쓰지 않음", out)
        self.run_api(self.gh())
        before = read_json(self.dd.file())
        with tempfile.TemporaryDirectory() as out_dir:
            code, out, _ = run_main(["--data", self.dd.path, "--out", out_dir, "--offline"], env={},
                                    opener=lambda *a, **k: self.fail("오프라인에서 요청"))
            after = read_json(os.path.join(out_dir, tb.FILE))
        self.assertNotIn("::warning::", out)
        self.assertEqual({k: v for k, v in after.items() if k != "generated_at"},
                         {k: v for k, v in before.items() if k != "generated_at"})

    def test_charts_missing_keeps_the_previous_file(self):
        self.run_api(self.gh())
        before = read_json(self.dd.file())
        obj = default_charts()
        obj["overview"][1]["lines"] = [ln for ln in obj["overview"][1]["lines"] if ln["key"] != "t10y2y"]
        write_json(os.path.join(self.dd.path, "charts.json"), obj)
        code, out, _ = self.run_api(self.gh(), now="2027-07-02T00:00:00+00:00")
        self.assertEqual(code, 0)
        self.assertIn("그래프 자료가 모자란다(t10y2y)", out)
        self.assertEqual(read_json(self.dd.file()), before)
        os.remove(os.path.join(self.dd.path, "charts.json"))
        code, out, _ = self.run_api(self.gh())
        self.assertIn("charts.json", out)

    def test_tp_line_is_not_needed(self):
        ds = fridays(80)
        write_json(os.path.join(self.dd.path, "charts.json"), charts_obj(linear(ds, 4.0, 0.01), linear(ds, 0.5, 0.0),
                                                                         with_tp=False))
        self.run_api(self.gh())
        self.assertTrue(os.path.exists(self.dd.file()))

    def test_broken_or_other_version_previous_file_rebuilds(self):
        self.run_api(self.gh())
        good = read_json(self.dd.file())
        for change in (lambda o: o["protocol"].update(version=2), lambda o: o["weeks"][0].update(state="in_progress"),
                       lambda o: o["source"].update(newest_commit="zz"), lambda o: o["weeks"].append(o["weeks"][0])):
            obj = json.loads(json.dumps(good))
            change(obj)
            write_json(self.dd.file(), obj)
            gh = self.gh()
            self.run_api(gh, now="2027-07-02T00:00:00+00:00")
            self.assertGreater(len(gh.calls), 1)                                 # 처음부터 다시 읽음
            self.assertEqual(read_json(self.dd.file())["weeks"], good["weeks"])
        with open(self.dd.file(), "w") as f:
            f.write("{깨진")
        self.assertIsNone(tb.load_previous(self.dd.file()))

    def test_same_content_is_not_rewritten_and_output_is_deterministic(self):
        self.run_api(self.gh())
        mtime = os.stat(self.dd.file()).st_mtime_ns
        code, out, _ = self.run_api(self.gh())                                  # 같은 시각 · 같은 입력
        self.assertIn("다시 쓰지 않음", out)
        self.assertEqual(os.stat(self.dd.file()).st_mtime_ns, mtime)
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            run_main(["--data", self.dd.path, "--out", a, "--rebuild"], now="2027-01-01T00:00:00+00:00", opener=self.gh(),
                     env={}, clock=Clock())
            run_main(["--data", self.dd.path, "--out", b, "--rebuild"], now="2027-01-01T00:00:00+00:00", opener=self.gh(),
                     env={}, clock=Clock())
            with open(os.path.join(a, tb.FILE), "rb") as fa, open(os.path.join(b, tb.FILE), "rb") as fb:
                self.assertEqual(fa.read(), fb.read())
            self.assertEqual(sorted(os.listdir(a)), [tb.FILE])                   # 임시 파일이 남지 않는다

    def test_write_failure_exits_one(self):
        with tempfile.TemporaryDirectory() as d:
            blocker = os.path.join(d, "file")
            with open(blocker, "w") as f:
                f.write("x")
            code, _, err = run_main(["--data", self.dd.path, "--out", os.path.join(blocker, "sub")], opener=self.gh(), env={},
                                    clock=Clock())
        self.assertEqual(code, 1)
        self.assertIn("쓰지 못함", err)


class RequestTest(unittest.TestCase):
    def test_hosts(self):
        self.assertEqual(tb.host_of(tb.LIST_URL.format(per=1, page=1)), tb.API_HOST)
        self.assertEqual(tb.host_of(tb.RAW_URL.format(sha="a" * 40, name="2026-03-02.json")), tb.RAW_HOST)
        userinfo = "https://user" + "@" + "api.github.com/x"     # 사용자 정보가 든 주소 — 글자를 나눠 적어 파일에 이메일 꼴을 두지 않는다
        for bad in ("http://api.github.com/x", "https://api.github.com:8443/x", userinfo,
                    "https://evil.example\\@api.github.com/x", "https://api.github.com.evil.example/x",
                    "https://example.invalid/x", "https://api.github.com/a b", "ftp://api.github.com/x", None):
            self.assertIsNone(tb.host_of(bad), bad)
            if bad:
                with self.assertRaises(ValueError):
                    tb.gh_request(bad, TOKEN)

    def test_request_headers(self):
        r = tb.gh_request(tb.API + "/commits/" + "a" * 40, TOKEN)
        self.assertEqual(r.get_header("Authorization"), "Bearer " + TOKEN)
        r = tb.gh_request(tb.RAW_URL.format(sha="a" * 40, name="2026-03-02.json"), TOKEN)
        self.assertIsNone(r.get_header("Authorization"))
        self.assertEqual(r.get_header("User-agent"), tb.USER_AGENT)

    def test_redirects_are_not_followed(self):
        h = tb.NoRedirect()
        req = tb.gh_request(tb.API + "/commits?path=records", TOKEN)
        with self.assertRaises(urllib.error.HTTPError):
            h.redirect_request(req, None, 302, "Found", {}, "https://example.invalid/steal")
        opener = tb._default_opener()
        self.assertTrue(any(isinstance(x, tb.NoRedirect) for x in opener.__self__.handlers))

    def test_reads_stop_at_the_deadline_and_the_size_limit(self):
        clock = Clock()

        class Slow(Resp):
            def read(self, n=-1):
                clock.t += 20
                return super().read(5)

        src = tb.ApiSource(clock() + 30, clock, opener=lambda req, timeout: Slow(b"x" * 100))
        with self.assertRaises(tb.FetchError) as cm:
            src._get(tb.API + "/commits/" + "a" * 40, 10 ** 6)
        self.assertEqual(cm.exception.kind, "budget")
        src = tb.ApiSource(clock() + 30, clock, opener=lambda req, timeout: Resp(b"x" * 100))
        with self.assertRaises(tb.FetchError) as cm:
            src._get(tb.API + "/commits/" + "a" * 40, 50)
        self.assertEqual(cm.exception.kind, "too_big")
        big = tb.ApiSource(clock() + 30, clock, opener=lambda req, timeout: Resp(b"x" * (tb.MAX_RECORD_BYTES + 10)))
        self.assertEqual(big.content("a" * 40, path("2026-03-02")), b"")         # 2MB 넘는 판 — 꼴이 어긋난 판으로

    def test_a_hanging_request_is_cut_at_the_hard_cap(self):
        """요청은 따로 스레드에서 — 연결이 걸려도(이름 풀이 · 여러 주소) 남은 시간 · 요청 상한을 넘겨 기다리지 않는다."""
        gate = threading.Event()
        self.addCleanup(gate.set)

        def hang(req, timeout):
            gate.wait(30)
            return Resp(b"[]")
        src = tb.ApiSource(time.monotonic() + 2.2, opener=hang)
        t0 = time.monotonic()
        with self.assertRaises(tb.FetchError) as cm:
            src.list_commits()
        self.assertEqual(cm.exception.kind, "budget")                             # 남은 시간(2.2초)이 걸렸다
        self.assertLess(time.monotonic() - t0, 5)
        with mock.patch.object(tb, "TIMEOUT", 0.3):
            src = tb.ApiSource(time.monotonic() + 30, opener=hang)
            t0 = time.monotonic()
            with self.assertRaises(tb.FetchError) as cm:
                src.changed("a" * 40)
            self.assertEqual(cm.exception.kind, "timeout")                        # 요청 상한(0.3초)이 걸렸다
            self.assertLess(time.monotonic() - t0, 3)

    def test_a_commit_with_more_files_than_one_page_is_a_failure(self):
        """GitHub의 커밋 응답은 바뀐 파일을 300개씩 나눠 준다 — 나머지를 읽지 않은 커밋은 쓰지 않는다."""
        clock = Clock()
        files = [{"filename": f"web/f{i}.txt", "status": "modified"} for i in range(tb.MAX_COMMIT_FILES)]
        src = tb.ApiSource(clock() + 30, clock, opener=lambda req, timeout: Resp(json.dumps({"files": files}).encode()))
        with self.assertRaises(tb.FetchError) as cm:
            src.changed("a" * 40)
        self.assertEqual(cm.exception.kind, "too_many_files")

        class Paged(Resp):
            headers = {"Link": '<https://api.github.com/repositories/1/commits/x?page=2>; rel="next", <…?page=3>; rel="last"'}
        src = tb.ApiSource(clock() + 30, clock, opener=lambda req, timeout: Paged(json.dumps({"files": files[:3]}).encode()))
        with self.assertRaises(tb.FetchError) as cm:
            src.changed("a" * 40)
        self.assertEqual(cm.exception.kind, "too_many_files")

        class Last(Resp):
            headers = {"Link": '<https://api.github.com/x?page=1>; rel="prev"'}
        src = tb.ApiSource(clock() + 30, clock, opener=lambda req, timeout: Last(json.dumps({"files": files[:3]}).encode()))
        self.assertEqual(len(src.changed("a" * 40)), 3)

    def test_bad_api_shapes_are_failures(self):
        clock = Clock()
        for body in (b"{}", b"[1]", b'[{"sha": "x", "commit": {"committer": {"date": "2026-01-01T00:00:00Z"}}}]',
                     b'[{"sha": "' + b"a" * 40 + b'", "commit": {}}]', b"not json"):
            src = tb.ApiSource(clock() + 30, clock, opener=lambda req, timeout, b=body: Resp(b))
            with self.assertRaises(tb.FetchError):
                src.list_commits()
        src = tb.ApiSource(clock() + 30, clock, opener=lambda req, timeout: Resp(b'{"files": "x"}'))
        with self.assertRaises(tb.FetchError):
            src.changed("a" * 40)


# ── 로컬 git 사본(--records-dir) ─────────────────────────────────────────────────────────────────────────────
@unittest.skipUnless(shutil.which("git"), "git 명령이 없다")
class GitTest(unittest.TestCase):
    def git(self, repo, *args, date=None):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        if date:
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        return subprocess.run(["git", "-C", repo, "-c", "user.name=test", "-c", "user.email=", "-c", "commit.gpgsign=false",
                               *args], check=True, capture_output=True, env=env).stdout.decode()

    def make_repo(self, spec):
        """SPEC 꼴 → 임시 git 저장소. 커밋 시각은 KST로 적는다(운영자 PC처럼). → (폴더, [(sha, at, 파일)])."""
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        self.git(tmp, "init", "-q")
        os.makedirs(os.path.join(tmp, "records"))
        with open(os.path.join(tmp, "records", "README.md"), "w") as f:
            f.write("# records\n")
        self.git(tmp, "add", "-A")
        self.git(tmp, "commit", "-q", "-m", "readme", date="2026-03-01T10:00:00+09:00")
        out = [(self.git(tmp, "rev-parse", "HEAD").strip(), "2026-03-01T01:00:00Z", {"records/README.md": b"# records\n"})]
        for at, files in spec:
            kst = tb._dt(at).astimezone(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
            done = {}
            for w, r in files.items():
                p = os.path.join(tmp, path(w))
                if r is None:
                    self.git(tmp, "rm", "-q", path(w))
                    done[path(w)] = None
                else:
                    with open(p, "wb") as f:
                        f.write(rb(r))
                    self.git(tmp, "add", path(w))
                    done[path(w)] = rb(r)
            self.git(tmp, "commit", "-q", "-m", "records", date=kst)
            out.append((self.git(tmp, "rev-parse", "HEAD").strip(), at, done))
        with open(os.path.join(tmp, "other.txt"), "w") as f:            # records/ 밖만 바꾼 커밋 — 목록에 들지 않는다
            f.write("x")
        self.git(tmp, "add", "-A")
        self.git(tmp, "commit", "-q", "-m", "other", date="2026-03-30T10:00:00+09:00")
        return tmp, out

    def test_local_clone_gives_the_same_weeks_and_locks_as_the_api(self):
        spec = SPEC + [("2026-03-24T04:00:00Z", {"2026-03-09": None}),
                       ("2026-03-25T04:00:00Z", {"2026-03-16": record("2026-03-16", True, (1.1, "강한 O/W"))})]
        repo, commits = self.make_repo(spec)
        dd = DataDir(snaps=[snapshot("2026-03-08")])
        self.addCleanup(dd.cleanup)
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            code, out, _ = run_main(["--data", dd.path, "--out", a, "--records-dir", repo], env={})
            self.assertEqual(code, 0, out)
            run_main(["--data", dd.path, "--out", b], opener=FakeGitHub(commits), env={}, clock=Clock())
            ga, gb = read_json(os.path.join(a, tb.FILE)), read_json(os.path.join(b, tb.FILE))
        check_timeline(self, ga)
        self.assertEqual(ga["weeks"], gb["weeks"])
        self.assertEqual(ga["summary"], gb["summary"])
        self.assertEqual(ga["source"]["newest_commit"], commits[-1][0])
        self.assertEqual((ga["source"]["via"], gb["source"]["via"]), ("git", "api"))
        self.assertEqual([w["week"] for w in ga["weeks"]], ["2026-03-16", "2026-03-09", "2026-03-02"])
        self.assertEqual(ga["weeks"][1]["removed"], {"at": "2026-03-24T04:00:00+00:00", "sha": commits[-2][0]})   # 지운 주도 잠금 그대로
        self.assertEqual(ga["weeks"][2]["lock"]["at"], "2026-03-11T04:00:00+00:00")   # KST로 적힌 커밋 시각 → UTC

    def test_shallow_clone_is_refused(self):
        """얕은 사본은 경계 커밋이 모든 파일을 새로 더한 것처럼 보여 잠금이 늦어진다 — 받지 않고 아무것도 쓰지 않는다."""
        repo, commits = self.make_repo(SPEC)
        shallow = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, shallow, True)
        subprocess.run(["git", "clone", "-q", "--depth", "2", "file://" + repo, shallow], check=True, capture_output=True,
                       env={k: v for k, v in os.environ.items() if not k.startswith("GIT_")})
        dd = DataDir()
        self.addCleanup(dd.cleanup)
        with tempfile.TemporaryDirectory() as a:
            code, out, _ = run_main(["--data", dd.path, "--out", a, "--records-dir", shallow, "--rebuild"], env={})
            self.assertEqual(code, 0)
            self.assertIn("얕은 사본", out)
            self.assertEqual(os.listdir(a), [])

    def test_ref_and_bad_refs(self):
        repo, commits = self.make_repo(SPEC)
        dd = DataDir()
        self.addCleanup(dd.cleanup)
        with tempfile.TemporaryDirectory() as a:
            run_main(["--data", dd.path, "--out", a, "--records-dir", repo, "--records-ref", commits[3][0]], env={})
            obj = read_json(os.path.join(a, tb.FILE))
        self.assertEqual(obj["source"]["newest_commit"], commits[3][0])
        self.assertIsNone(obj["weeks"][1]["changed_after"])
        for ref in ("--output=/tmp/x", "a..b", "-p", "x y", "../x"):
            with tempfile.TemporaryDirectory() as a:
                code, out, _ = run_main(["--data", dd.path, "--out", a, "--records-dir", repo, "--records-ref=" + ref], env={})
                self.assertEqual(code, 0)
                self.assertIn("로컬 git 읽기 실패", out)
                self.assertEqual(os.listdir(a), [])

    def test_not_a_repository(self):
        dd = DataDir()
        self.addCleanup(dd.cleanup)
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as empty:
            code, out, _ = run_main(["--data", dd.path, "--out", a, "--records-dir", empty], env={})
        self.assertEqual(code, 0)
        self.assertIn("로컬 git 읽기 실패", out)


# ── 꼴 검사 ──────────────────────────────────────────────────────────────────────────────────────────────────
def _num_or_none(v):
    return v is None or (isinstance(v, (int, float)) and not isinstance(v, bool))


def check_outcome(t, o):
    t.assertEqual(set(o), {"state", "start", "end", "change_bp", "demeaned_bp"})
    t.assertIn(o["state"], ("done", "pending", "missing"))
    t.assertTrue(o["start"] is None or DATE.match(o["start"]))
    t.assertTrue(o["end"] is None or DATE.match(o["end"]))
    t.assertEqual(o["state"] == "done", o["end"] is not None)
    t.assertEqual(o["state"] == "done", o["change_bp"] is not None)
    t.assertTrue(_num_or_none(o["change_bp"]) and _num_or_none(o["demeaned_bp"]))


def check_block(t, b, x):
    t.assertEqual(set(x), {"total", "verdict"})
    t.assertTrue(x["verdict"] in tb.VERDICTS[b] or tb.UNSCORED_RE.fullmatch(x["verdict"]), x)
    t.assertTrue(_num_or_none(x["total"]))


def check_timeline(t, obj):
    """data/timeline.json 약속 꼴 — 화면이 읽는 키."""
    t.assertEqual(set(obj), {"schema", "generated_at", "notice", "label", "lp_label", "source", "protocol", "charts", "weeks",
                             "summary", "sources", "notices"})
    t.assertEqual((obj["schema"], obj["notice"], obj["label"], obj["lp_label"]), (1, tb.NOTICE, tb.LABEL, lpf.LABEL))
    s = obj["source"]
    t.assertEqual(set(s), {"repo", "path", "site", "newest_commit", "checked_at", "via", "skipped_versions", "rewritten_at"})
    t.assertTrue(s["rewritten_at"] is None or ISO.match(s["rewritten_at"]))
    t.assertEqual((s["repo"], s["path"], s["site"]), (tb.SOURCE_REPO, "records/", tb.SOURCE_SITE))
    t.assertTrue(s["newest_commit"] is None or tb.SHA_RE.fullmatch(s["newest_commit"]))
    p = obj["protocol"]
    t.assertEqual((p["version"], p["fixed"], p["horizons_weeks"], p["n_min"], p["tolerance_days"], p["open_utc"], p["open_kst"]),
                  (1, "2026-11-19", [1, 4], 10, 3, "13:30", "22:30"))
    t.assertEqual([(x["verdict"], x["series"], x["label"]) for x in p["pairs"]],
                  [("dur", "DGS10", "미 10년"), ("cur", "T10Y2Y", "10년−2년")])
    t.assertEqual(p["text"], tb.protocol_text())
    t.assertEqual(set(obj["charts"]), {"date", "window", "last", "baseline", "baseline_detail"})
    for h in ("1", "4"):
        t.assertEqual(list(obj["charts"]["baseline"][h]), ["dgs10", "t10y2y"])
    weeks = [w["week"] for w in obj["weeks"]]
    t.assertEqual(weeks, sorted(weeks, reverse=True))
    t.assertEqual(len(weeks), len(set(weeks)))
    for w in obj["weeks"]:
        t.assertEqual(set(w), {"week", "end", "state", "lock", "before_protocol", "dur", "cur", "edited_n", "regime_flag",
                               "regime_flag_other", "changed_after", "removed", "site", "lp", "outcomes"})
        t.assertEqual(D.fromisoformat(w["week"]).weekday(), 0)
        t.assertEqual(w["end"], plus(D.fromisoformat(w["week"]), 6).isoformat())
        t.assertEqual(w["state"], "confirmed" if w["lock"] else "in_progress")
        if w["lock"]:
            t.assertEqual(set(w["lock"]), {"sha", "at", "late", "first_upload", "in_history"})
            t.assertIsInstance(w["lock"]["first_upload"], bool)
            t.assertIsInstance(w["lock"]["in_history"], bool)
            t.assertTrue(tb.SHA_RE.fullmatch(w["lock"]["sha"]))
            t.assertRegex(w["lock"]["at"], ISO)
            t.assertEqual(w["lock"]["late"], tb.is_late(D.fromisoformat(w["end"]), tb._dt(w["lock"]["at"])))
            t.assertEqual(w["before_protocol"], w["lock"]["at"][:10] < tb.PROTOCOL_FIXED)
        else:
            t.assertFalse(w["before_protocol"])
            t.assertIsNone(w["changed_after"])
            t.assertIsNone(w["removed"])                                              # 확정 전인 주를 지우면 목록에서 빠진다
        if w["removed"]:
            t.assertEqual(set(w["removed"]), {"at", "sha"})
            t.assertTrue(tb.SHA_RE.fullmatch(w["removed"]["sha"]))
            t.assertRegex(w["removed"]["at"], ISO)
        for b in ("dur", "cur"):
            check_block(t, b, w[b])
        t.assertTrue(isinstance(w["edited_n"], int) and w["edited_n"] >= 0)
        t.assertIn(w["regime_flag"], tb.REGIMES + (None,))
        t.assertIsInstance(w["regime_flag_other"], bool)
        t.assertFalse(w["regime_flag_other"] and w["regime_flag"] is not None)
        if w["changed_after"]:
            ca = w["changed_after"]
            t.assertEqual(set(ca), {"at", "sha", "dur", "cur", "edited_n"})
            t.assertNotEqual((ca["dur"], ca["cur"]), (w["dur"], w["cur"]))
            t.assertGreater(ca["at"], w["lock"]["at"])
        t.assertEqual(set(w["site"]), {"snapshot", "core", "met", "candidate"})
        t.assertIn(w["site"]["candidate"], lb.CANDIDATES + (lb.UNDECIDED, None))
        if w["lp"] is not None:
            t.assertEqual(set(w["lp"]), {"month", "L", "P", "cell"})
            t.assertEqual(w["lp"]["cell"], lpf.cell(w["lp"]["L"], w["lp"]["P"])[0])
        t.assertEqual(list(w["outcomes"]), ["1", "4"])
        for h in ("1", "4"):
            t.assertEqual(list(w["outcomes"][h]), ["dur", "cur"])
            for o in w["outcomes"][h].values():
                check_outcome(t, o)
                if w["state"] == "in_progress":
                    t.assertEqual(o, tb.EMPTY)
    t.assertEqual({b: list(g) for b, g in obj["summary"].items()},
                  {"dur": ["ow", "neutral", "uw"], "cur": ["flat", "neutral", "steep"]})
    for b, groups in obj["summary"].items():
        for g in groups.values():
            for h in ("1", "4"):
                t.assertEqual(set(g[h]), {"n", "starts", "mean_demeaned_bp", "up_share"})
                t.assertLessEqual(g[h]["starts"], g[h]["n"])
                t.assertEqual(g[h]["mean_demeaned_bp"] is None, g[h]["starts"] < tb.N_MIN)
    t.assertEqual([x["series"] for x in obj["sources"]], ["DGS10", "T10Y2Y"])
    t.assertEqual([x["citation_required"] for x in obj["sources"]], [False, True])
    t.assertEqual(obj["notices"], [tb.COMPUTED_NOTICE, tb.COMPUTED_NOTICE_EN])
    text = json.dumps(obj, ensure_ascii=False)
    for w in BANNED:
        t.assertNotIn(w, text)
    t.assertIsNone(re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text), "이메일 꼴")


# ── 문서 · 워크플로(통합 단계에서 생기면 견준다) ───────────────────────────────────────────────────────────────
class DocsTest(unittest.TestCase):
    def read(self, *p):
        with open(os.path.join(REPO, *p), encoding="utf-8") as f:
            return f.read()

    def section(self):
        readme = self.read("README.md")
        m = re.search(r"^## 참고: 판단 연표[^\n]*\n(.*?)(?=^## |\Z)", readme, re.M | re.S)
        if not m:
            self.skipTest("README에 '## 참고: 판단 연표' 절이 아직 없다")
        return m.group(0)

    def test_readme_quotes_the_protocol_sentences_as_written(self):
        section = self.section()
        for i, t in enumerate(tb.protocol_text(), 1):
            self.assertIn(f"\n{i}. {t}\n", section, f"README 절에 약속 문장 {i}이 글자 그대로 없다")
        for fact in ("data/timeline.json", "scripts/timeline_build.py", tb.LABEL):
            self.assertIn(fact, section)
        for w in BANNED:
            self.assertNotIn(w, section)

    def test_workflow_step(self):
        wf = self.read(".github", "workflows", "daily.yml")
        if "timeline_build.py" not in wf:
            self.skipTest("daily.yml에 판단 연표 단계가 아직 없다")
        start = wf.rindex("      - name:", 0, wf.index("timeline_build.py"))
        step = wf[start:wf.index("\n      - ", start + 1)]
        self.assertIn("continue-on-error: true", step)
        self.assertIn("timeout-minutes:", step)
        self.assertNotIn("secrets.", step.replace("secrets.GITHUB_TOKEN", ""))   # 넘기는 비밀은 GITHUB_TOKEN뿐
        self.assertLess(wf.index("id: charts"), start)                            # 그래프 자료 뒤
        self.assertLess(start, wf.index("git add data"))
        self.assertIn("id: timeline\n", step)
        self.assertIn("timeout-minutes: 2\n", step)
        self.assertIn("GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}", step)
        self.assertTrue(step.rstrip().endswith("run: python scripts/timeline_build.py"))
        self.assertEqual(wf.count("secrets.GITHUB_TOKEN"), 1)                           # 이 단계에만
        self.assertNotIn("if:", step)                                                    # 앞 단계가 실패한 날에도 돈다
        self.assertLess(wf.index("id: lp\n"), start)                                    # 오늘 받은 lp.json을 읽는다 — 판단 격자 뒤
        self.assertLess(wf.index("id: ledger"), start)
        self.assertLess(start, wf.index("id: korea_start"))
        self.assertLess(start, wf.index("공개 전 검사(새 산출물 포함)"))
        self.assertNotIn("timeline", wf[wf.index("\n  alert:"):])                       # 실패해도 알림을 띄우지 않는다
        self.assertIn("node --test scripts/test_timeline_render.cjs", wf[wf.index("\n  check:"):wf.index("\n  update:")])
        self.assertEqual(wf.count("timeline_build.py"), 1)

    def test_readme_counts_and_commands(self):
        readme = self.read("README.md")
        m = re.search(r"\*\*아침 쪽 Python 테스트 (\d+)개 \+ node 테스트 (\d+)개\*\*\((.*?)\)와 \*\*저녁판", readme)
        self.assertIsNotNone(m)
        py_part, node_part = m.group(3).split(" / node: ")
        mine = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()
        self.assertRegex(py_part, rf"(^| · )판단 연표 {mine}( · |$)")
        cjs = len(re.findall(r"^test\(", self.read("scripts", "test_timeline_render.cjs"), flags=re.M))
        self.assertRegex(node_part, rf"(^| · )판단 연표 그리기 {cjs}( · |$)")
        for cmd in ("python -X utf8 scripts/test_timeline_build.py", "node --test scripts/test_timeline_render.cjs",
                    "python -X utf8 scripts/timeline_build.py --out"):
            self.assertIn(cmd, readme)
        section = self.section()
        self.assertIn(f"판단 연표 약속 {tb.PROTOCOL_VERSION}판({tb.PROTOCOL_FIXED} 고정)", section)
        self.assertIn("(#참고-판단-연표)", readme[:readme.index("## 공개 원칙")])          # 머리 표에서 이 절로


# ── 저장소의 실제 자료 ─────────────────────────────────────────────────────────────────────────────────────────
@unittest.skipIf(os.environ.get("MRC_SKIP_REAL_DATA") == "1", "실자료 테스트 — CI 문(check)에서는 건너뛰고 봇 커밋 뒤에 경고만으로 돈다")
class RealDataTest(unittest.TestCase):
    DATA = os.path.join(REPO, "data")

    def test_published_file_has_the_contract_shape(self):
        p = os.path.join(self.DATA, tb.FILE)
        if not os.path.exists(p):
            self.skipTest("data/timeline.json이 아직 없다")
        obj = read_json(p)
        check_timeline(self, obj)
        self.assertIsNotNone(tb.load_previous(p), "다음 실행이 이어서 읽을 수 있어야 한다")

    def test_offline_rebuild_of_the_repository_data(self):
        p = os.path.join(self.DATA, tb.FILE)
        if not os.path.exists(p):
            self.skipTest("data/timeline.json이 아직 없다")
        with tempfile.TemporaryDirectory() as out:
            code, _, _ = run_main(["--data", self.DATA, "--out", out, "--offline"], env={})
            self.assertEqual(code, 0)
            obj = read_json(os.path.join(out, tb.FILE))
        check_timeline(self, obj)
        self.assertEqual(obj["source"], read_json(p)["source"])


if __name__ == "__main__":
    unittest.main()
