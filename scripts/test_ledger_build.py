#!/usr/bin/env python3
"""변화 층 · 규칙 장부(ledger_build) 테스트 — 지어낸 날짜별 기록과 그래프 자료(임시 폴더)로 답을 아는 셈을 본다.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)   ·   python -X utf8 scripts/test_ledger_build.py
네트워크 불필요, 표준 라이브러리만. 마지막 묶음(RealDataTest)은 저장소의 실제 data/history · data/charts.json을 임시 폴더로
돌려 꼴만 본다(쓰지 않는다).
"""
import io, os, re, sys, json, datetime, tempfile, unittest, subprocess, contextlib
from decimal import Decimal

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import ledger_build as lb

D = datetime.date
REPO = os.path.dirname(SCRIPTS)
NOW = "2026-11-18T00:00:00+00:00"
VERDICT = ("적중", "맞았다", "틀렸다", "매수", "매도", "유망")
TITLES = {"alpha": "규칙 가", "beta": "규칙 나", "gamma": "규칙 다", "delta": "규칙 라"}
PLANTED = ("7.654321", "7.65", "9.876543", "9.88", "5432.1", "비밀 해석 줄")     # 관측값·해석 줄에 심어 둔 것 — 어디에도 나오면 안 된다
WEEK = datetime.timedelta(days=7)


def day(s):
    return D.fromisoformat(s)


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def read_json(path):
    return json.loads(read_text(path))


def quiet_main(argv, now=NOW):
    """lb.main — 실행 줄(stdout · stderr)은 테스트 출력에 섞지 않는다."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return lb.main(argv, now=now)


def plus(d, n):
    return d + datetime.timedelta(days=n)


# ── 지어낸 자료 ─────────────────────────────────────────────────────────────────────────────────────────────
def rule(key, status):
    """그날 공개본의 규칙 한 장 — 관측값과 해석 줄에는 심어 둔 숫자(PLANTED)를 넣는다."""
    return {"key": key, "title": TITLES.get(key, key), "rule": "지어낸 규칙 문장", "status": status,
            "scenario": "A", "reading": "비밀 해석 줄 Baa 7.65%p",
            "observations": [{"label": "Baa−10년", "unit": "%p", "series": ["BAA10Y"], "derived": False,
                              "computed": False, "value": 7.654321, "asof": "2026-01-02"},
                             {"label": "HY OAS", "unit": "%p", "series": ["BAMLH0A0HYM2"], "derived": False,
                              "computed": False, "value": 9.876543, "asof": "2026-01-02"},
                             {"label": "S&P 500", "unit": "", "series": ["SP500"], "derived": False,
                              "computed": False, "value": 5432.1, "asof": "2026-01-02"}],
            "restricted_series": [], "notices": []}


def regime(core=(2, 11), neutral=(0, 2), cand="A′", auto=1):
    return {"notice": "지어낸 참고", "headline": "지어낸 머리",
            "core": {"total": core[1], "met": core[0], "unknown": 0},
            "neutral": {"total": neutral[1], "met": neutral[0], "unknown": 0},
            "reference": {"candidate": cand, "candidate_note": "사분면 판정", "sp_13w": "하락",
                          "y10_13w_bp": 47.0, "transition": {"t2": "OFF", "t4": "ON", "auto_on": auto}, "lines": []},
            "manual_checks": [], "more_values": [{"label": "M2", "value": 7.654321}]}


def hl(series, fetched="net", stale=False, last="2026-11-01", label=None):
    return {"series": series, "label": label or f"{series} 이름", "owner": "FRB", "url": "https://example.invalid/",
            "last": last, "age_days": 3, "fetched": fetched, "stale": stale, "display": "value",
            "citation_required": False, "citation": "지어낸 인용"}


def snap(date, statuses, reg=None, health=None):
    """statuses — [(key, status)] 차례대로."""
    rules = [rule(k, st) for k, st in statuses]
    d = {"schema": 1, "date": date, "generated_at": date + "T04:00:00+00:00", "notice": "지어낸 고지", "attribution": [],
         "summary": {"total": len(rules), "met": sum(1 for r in rules if r["status"] == "met"),
                     "not_met": sum(1 for r in rules if r["status"] == "not_met"),
                     "unknown": sum(1 for r in rules if r["status"] == "unknown")},
         "rules": rules, "data_health": health if health is not None else [], "warnings": []}
    if reg is not None:
        d["regime"] = reg
    return d


def line(key, sid, points):
    return {"key": key, "label": key, "role": "main", "series": [sid], "derived": False,
            "points": [[d.isoformat() if isinstance(d, D) else d, v] for d, v in points]}


def charts(dgs10=(), t10y2y=(), tp=(), date="2026-11-17"):
    return {"schema": 1, "date": date, "generated_at": date + "T04:00:00+00:00", "attribution": [],
            "overview": [{"key": "yield10", "title": "미 10년 금리 분해", "unit": "%",
                          "lines": [line("dgs10", "DGS10", dgs10), line("dfii10", "DFII10", [(day("2026-01-02"), 7.654321)])]},
                         {"key": "term", "title": "기간 프리미엄과 10년−2년", "unit": "%",
                          "lines": [line("tp", "THREEFYTP10", tp), line("t10y2y", "T10Y2Y", t10y2y)]}],
            "rules": {}}


def fridays(start, n):
    d = day(start)
    return [plus(d, 7 * k) for k in range(n)]


def as_dec(points):
    return [(d, Decimal(repr(v))) for d, v in points]


class World(unittest.TestCase):
    """임시 data/ 폴더 하나 — history/와 charts.json을 쓰고 build를 부른다."""

    def setUp(self):
        self.box = tempfile.TemporaryDirectory()
        self.data = self.box.name
        self.hist = os.path.join(self.data, "history")
        os.makedirs(self.hist)

    def tearDown(self):
        self.box.cleanup()

    def put(self, snaps, chart=None, extra=None):
        for s in snaps:
            with open(os.path.join(self.hist, s["date"] + ".json"), "w", encoding="utf-8") as f:
                json.dump(s, f, ensure_ascii=False)
        for name, text in (extra or {}).items():
            with open(os.path.join(self.hist, name), "w", encoding="utf-8") as f:
                f.write(text)
        if chart is not None:
            with open(os.path.join(self.data, "charts.json"), "w", encoding="utf-8") as f:
                json.dump(chart, f, ensure_ascii=False)

    def build(self):
        return lb.build(self.data, now=NOW)

    def rule_of(self, ledger, key):
        return next(r for r in ledger["rules"] if r["key"] == key)


# ── 꼴 검사(실제 자료 연기 시험에도 쓴다) ─────────────────────────────────────────────────────────────────────────
DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")
RATIO = re.compile(r"\d+/\d+$")


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and abs(v) != float("inf")


def check_changes(t, c):
    t.assertEqual(set(c), {"schema", "generated_at", "notice", "asof", "headline", "windows", "recent_from", "recent"})
    t.assertEqual(c["schema"], 1)
    t.assertEqual(c["notice"], lb.CHANGES_NOTICE)
    t.assertRegex(c["asof"], DATE)
    t.assertTrue(1 <= len(c["headline"]) <= 3 and all(isinstance(x, str) and x for x in c["headline"]))
    t.assertEqual([(w["key"], w["label"]) for w in c["windows"]], [(k, lb_) for k, lb_, _ in lb.WINDOWS])
    for w in c["windows"]:
        t.assertEqual(set(w), {"key", "label", "from", "rules", "met", "core", "neutral", "candidate", "transition", "health"})
        t.assertTrue(w["from"] is None or DATE.match(w["from"]))
        for r in w["rules"]:
            t.assertEqual(set(r), {"key", "title", "from", "to"})
            t.assertIn(r["from"], lb.STATUSES + (None,))
            t.assertIn(r["to"], lb.STATUSES)
            t.assertNotEqual(r["from"], r["to"])
        t.assertEqual(set(w["met"]), {"from", "to", "total_from", "total_to"})
        for k in ("core", "neutral"):
            t.assertTrue(all(v is None or RATIO.match(v) for v in w[k].values()))
        t.assertTrue(all(v is None or v in lb.CANDIDATES + (lb.UNDECIDED,) for v in w["candidate"].values()))
        t.assertTrue(all(v is None or (isinstance(v, int) and 0 <= v <= lb.TRANSITION_AUTO) for v in w["transition"].values()))
        t.assertEqual(set(w["health"]), {"lost", "recovered", "stale", "fresh"})
        for items in w["health"].values():
            t.assertTrue(all(set(i) == {"series", "label"} for i in items))
        if w["from"] is None:
            t.assertEqual(w["rules"], [])
    dates = [e["date"] for e in c["recent"]]
    t.assertEqual(dates, sorted(dates, reverse=True))
    for e in c["recent"]:
        t.assertEqual(set(e), {"date", "key", "title", "from", "to"})
        t.assertIn(e["from"], lb.KNOWN)
        t.assertIn(e["to"], lb.KNOWN)
        t.assertTrue(c["recent_from"] <= e["date"] <= c["asof"])


CITE = re.compile(r"[^<>]{1,300}, retrieved from [^<>]{1,300}, [A-Z][a-z]+ \d{1,2}, \d{4}\.$")   # site/ledger.js · tp.js의 CITE


def check_ledger(t, l):
    t.assertEqual(set(l), {"schema", "generated_at", "notice", "protocol", "history", "charts", "sources", "notices", "rules"})
    t.assertEqual(l["notices"], [lb.COMPUTED_NOTICE, lb.COMPUTED_NOTICE_EN])
    t.assertEqual([s["series"] for s in l["sources"]], [sid for _, _, sid in lb.OUTCOMES])
    for s in l["sources"]:
        t.assertEqual(set(s), {"series", "url", "citation", "citation_required"})
        t.assertEqual(s["url"], "https://fred.stlouisfed.org/series/" + s["series"])
        t.assertEqual(s["citation_required"], s["series"] == "T10Y2Y")
        if l["charts"]["date"]:
            t.assertRegex(s["citation"], CITE)
            t.assertIn(f"[{s['series']}], retrieved from FRED, Federal Reserve Bank of St. Louis", s["citation"])
        else:
            t.assertIsNone(s["citation"])
    t.assertEqual(l["schema"], 1)
    t.assertEqual(l["notice"], lb.LEDGER_NOTICE)
    p = l["protocol"]
    t.assertEqual((p["version"], p["fixed"], p["horizons_weeks"], p["n_min"], p["tolerance_days"]),
                  (lb.PROTOCOL_VERSION, lb.PROTOCOL_FIXED, list(lb.HORIZONS), lb.N_MIN, lb.TOL_DAYS))
    t.assertEqual(p["outcomes"], [{"key": k, "label": a, "series": s} for k, a, s in lb.OUTCOMES])
    t.assertEqual(p["text"], lb.protocol_text())
    t.assertEqual(set(l["history"]), {"from", "to", "snapshots", "skipped"})
    t.assertEqual(set(l["charts"]), {"date", "window", "last", "baseline", "baseline_detail"})
    t.assertEqual(list(l["charts"]["last"]), [k for k, _, _ in lb.OUTCOMES])
    t.assertTrue(all(v is None or DATE.match(v) for v in l["charts"]["last"].values()))
    keys = [k for k, _, _ in lb.OUTCOMES]
    for h in lb.HORIZONS:
        t.assertEqual(list(l["charts"]["baseline"][str(h)]), keys)
        t.assertTrue(all(v is None or _num(v) for v in l["charts"]["baseline"][str(h)].values()))
    for r in l["rules"]:
        t.assertEqual(set(r), {"key", "title", "first", "last", "start", "now", "since", "unknown_days", "events", "summary"})
        t.assertIn(r["start"], lb.KNOWN + (None,))
        t.assertIn(r["now"], lb.STATUSES)
        t.assertTrue((r["since"] is None) == (r["start"] is None))
        for e in r["events"]:
            t.assertEqual(set(e), {"date", "from", "to", "before_protocol", "core", "candidate", "outcomes"})
            t.assertEqual(e["before_protocol"], e["date"] < lb.PROTOCOL_FIXED)
            t.assertNotEqual(e["from"], e["to"])
            t.assertEqual(list(e["outcomes"]), [str(h) for h in lb.HORIZONS])
            for h in lb.HORIZONS:
                t.assertEqual(list(e["outcomes"][str(h)]), keys)
                for o in e["outcomes"][str(h)].values():
                    t.assertEqual(set(o), {"state", "start", "end", "change_bp", "demeaned_bp"})
                    if o["state"] == "done":
                        t.assertTrue(DATE.match(o["start"]) and DATE.match(o["end"]) and _num(o["change_bp"]))
                        t.assertTrue(o["demeaned_bp"] is None or _num(o["demeaned_bp"]))
                    else:
                        t.assertIn(o["state"], ("pending", "missing"))
                        t.assertEqual((o["end"], o["change_bp"], o["demeaned_bp"]), (None, None, None))
                        if o["state"] == "pending":
                            t.assertRegex(o["start"], DATE)
        for name in ("to_met", "to_not_met"):
            for h in lb.HORIZONS:
                for s in r["summary"][name][str(h)].values():
                    t.assertEqual(set(s), {"n", "mean_demeaned_bp", "up_share"})
                    if s["n"] < lb.N_MIN:
                        t.assertEqual((s["mean_demeaned_bp"], s["up_share"]), (None, None))


# ── 전환의 정의 ─────────────────────────────────────────────────────────────────────────────────────────────
class EventTest(World):
    def test_flips_skip_unknown_and_start_is_not_an_event(self):
        days = ["2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09"]
        alpha = ["met", "unknown", "met", "not_met", "unknown", "not_met", "met"]
        beta = ["unknown", "unknown", "not_met", "met", "met", "met", "met"]
        self.put([snap(d, [("alpha", a), ("beta", b)]) for d, a, b in zip(days, alpha, beta)])
        _, led = self.build()
        a = self.rule_of(led, "alpha")
        self.assertEqual([(e["date"], e["from"], e["to"]) for e in a["events"]],
                         [("2026-10-06", "met", "not_met"), ("2026-10-09", "not_met", "met")])
        self.assertEqual((a["first"], a["start"], a["now"], a["since"], a["unknown_days"]),
                         ("2026-10-01", "met", "met", "2026-10-09", 2))
        b = self.rule_of(led, "beta")
        self.assertEqual([(e["date"], e["from"], e["to"]) for e in b["events"]], [("2026-10-06", "not_met", "met")])
        self.assertEqual((b["start"], b["since"], b["unknown_days"]), ("not_met", "2026-10-06", 2))

    def test_unknown_at_the_end_keeps_the_known_run(self):
        self.put([snap("2026-10-01", [("alpha", "not_met")]), snap("2026-10-02", [("alpha", "met")]),
                  snap("2026-10-05", [("alpha", "unknown")])])
        a = self.rule_of(self.build()[1], "alpha")
        self.assertEqual((a["now"], a["since"], a["unknown_days"], len(a["events"])), ("unknown", "2026-10-02", 1, 1))

    def test_never_judged_rule(self):
        self.put([snap("2026-10-01", [("alpha", "unknown")]), snap("2026-10-02", [("alpha", "unknown")])])
        a = self.rule_of(self.build()[1], "alpha")
        self.assertEqual((a["start"], a["since"], a["now"], a["events"], a["unknown_days"]), (None, None, "unknown", [], 2))

    def test_added_rule_starts_at_its_first_snapshot(self):
        self.put([snap("2026-10-01", [("alpha", "met")]), snap("2026-10-02", [("alpha", "met")]),
                  snap("2026-10-05", [("alpha", "met"), ("beta", "met")]),
                  snap("2026-10-06", [("alpha", "met"), ("beta", "not_met")])])
        b = self.rule_of(self.build()[1], "beta")
        self.assertEqual((b["first"], b["start"]), ("2026-10-05", "met"))
        self.assertEqual([e["date"] for e in b["events"]], ["2026-10-06"])

    def test_rule_order_latest_then_dropped_rules(self):
        self.put([snap("2026-10-01", [("gamma", "met"), ("alpha", "met"), ("beta", "not_met")]),
                  snap("2026-10-02", [("beta", "met"), ("alpha", "not_met")])])
        led = self.build()[1]
        self.assertEqual([r["key"] for r in led["rules"]], ["beta", "alpha", "gamma"])
        g = self.rule_of(led, "gamma")
        self.assertEqual((g["last"], g["now"]), ("2026-10-01", "met"))

    def test_title_comes_from_the_latest_snapshot_with_the_rule(self):
        old, new = snap("2026-10-01", [("alpha", "met")]), snap("2026-10-02", [("alpha", "met")])
        old["rules"][0]["title"] = "옛 이름"
        self.put([old, new])
        self.assertEqual(self.rule_of(self.build()[1], "alpha")["title"], "규칙 가")

    def test_titles_with_angle_brackets_fall_back_to_the_key(self):
        """화면(site/ledger.js의 PLAIN)은 꺾쇠가 든 글을 받지 않는다 — 장부도 key로 대신해 화면이 그 규칙을 빼지 않게."""
        a = snap("2026-11-10", [("alpha", "met"), ("beta", "met")], health=[hl("S1", label="이름<b>")])
        b = snap("2026-11-17", [("alpha", "not_met"), ("beta", "met")], health=[hl("S1", fetched="missing", last=None, label="이름<b>")])
        for s_ in (a, b):
            s_["rules"][0]["title"] = "근원 CPI<3%"
            s_["rules"][1]["title"] = "규칙 > 나"
        self.put([a, b])
        ch, led = self.build()
        self.assertEqual([(r["key"], r["title"]) for r in led["rules"]], [("alpha", "alpha"), ("beta", "beta")])
        self.assertEqual(ch["windows"][1]["rules"], [{"key": "alpha", "title": "alpha", "from": "met", "to": "not_met"}])
        self.assertEqual(ch["windows"][1]["health"]["lost"], [{"series": "S1", "label": "S1"}])
        self.assertEqual(ch["headline"][1], "1주 사이 바뀐 규칙 1개: alpha(충족→미충족)")
        for obj in (ch, led):
            self.assertNotIn("<", lb.dumps(obj))
            self.assertNotIn(">", lb.dumps(obj))

    def test_malformed_files_are_skipped_and_counted(self):
        good = [snap("2026-10-01", [("alpha", "met")]), snap("2026-10-06", [("alpha", "not_met")])]
        wrong_schema = snap("2026-10-02", [("alpha", "not_met")])
        wrong_schema["schema"] = 2
        wrong_date = snap("2026-10-03", [("alpha", "not_met")])
        wrong_date["date"] = "2026-10-04"
        no_rules = snap("2026-10-04", [])
        no_rules["rules"] = {"alpha": "met"}
        self.put(good, extra={
            "2026-10-02.json": json.dumps(wrong_schema), "2026-10-03.json": json.dumps(wrong_date),
            "2026-10-04.json": json.dumps(no_rules), "2026-10-05.json": "{깨짐", "2026-09-30.json": "[1, 2]",
            "2026-02-30.json": json.dumps(snap("2026-02-30", [("alpha", "met")])),
            "notes.json": "{}", "2026-10-07.json.tmp": "{}", "readme.txt": "x"})
        ch, led = self.build()
        self.assertEqual(led["history"], {"from": "2026-10-01", "to": "2026-10-06", "snapshots": 2, "skipped": 6})
        self.assertEqual([e["date"] for e in self.rule_of(led, "alpha")["events"]], ["2026-10-06"])
        self.assertEqual(ch["asof"], "2026-10-06")

    def test_bad_rule_items_are_skipped_and_odd_status_is_unknown(self):
        s1 = snap("2026-10-01", [("alpha", "met"), ("beta", "met")])
        s2 = snap("2026-10-02", [("alpha", "met"), ("beta", "met")])
        s2["rules"][0]["status"] = "maybe"
        s2["rules"] += ["문자열", {"key": "Bad Key", "status": "met"}, {"key": "beta", "status": "not_met"}]
        s3 = snap("2026-10-05", [("alpha", "not_met"), ("beta", "met")])
        self.put([s1, s2, s3])
        led = self.build()[1]
        self.assertEqual([r["key"] for r in led["rules"]], ["alpha", "beta"])
        a = self.rule_of(led, "alpha")
        self.assertEqual((a["unknown_days"], [e["date"] for e in a["events"]]), (1, ["2026-10-05"]))
        self.assertEqual(self.rule_of(led, "beta")["events"], [])         # 같은 key의 두 번째 항목은 보지 않는다

    def test_context_from_that_days_snapshot(self):
        self.put([snap("2026-10-01", [("alpha", "met")]),
                  snap("2026-10-02", [("alpha", "not_met")]),                                  # regime 없음
                  snap("2026-10-05", [("alpha", "met")], regime((3, 11), cand="B")),
                  snap("2026-10-06", [("alpha", "not_met")], regime((1, 11), cand="Z — 지어낸 글")),
                  snap("2026-10-07", [("alpha", "met")], {"core": {"total": 11, "met": 12}, "reference": "x"}),
                  snap("2026-10-08", [("alpha", "not_met")], regime((2, 11), cand=None))])                # 완충 구간
        ev = self.rule_of(self.build()[1], "alpha")["events"]
        self.assertEqual([(e["core"], e["candidate"]) for e in ev],
                         [(None, None), ("3/11", "B"), ("1/11", None), (None, None), ("2/11", "판정불가")])

    def test_before_protocol_split(self):
        self.put([snap("2026-11-16", [("alpha", "met")]), snap("2026-11-17", [("alpha", "not_met")]),
                  snap("2026-11-18", [("alpha", "met")]), snap("2026-11-19", [("alpha", "not_met")])])
        ev = self.rule_of(self.build()[1], "alpha")["events"]
        self.assertEqual([(e["date"], e["before_protocol"]) for e in ev],
                         [("2026-11-17", True), ("2026-11-18", False), ("2026-11-19", False)])


# ── 결과의 정의 ─────────────────────────────────────────────────────────────────────────────────────────────
class OutcomeTest(unittest.TestCase):
    D0 = day("2026-01-02")                                                   # 금요일

    def pts(self, *pairs):
        return [(plus(self.D0, n), Decimal(v)) for n, v in pairs]

    def test_match_window_and_tie_goes_to_the_earlier_point(self):
        t = plus(self.D0, 28)
        dates = lambda *ns: [plus(self.D0, n) for n in ns]
        self.assertEqual(lb.match(dates(0, 26, 30, 40), t), 1)              # 같은 거리(2일) — 이른 점
        self.assertEqual(lb.match(dates(0, 25, 29, 40), t), 2)              # 1일 < 3일
        self.assertEqual(lb.match(dates(0, 25, 31, 40), t), 1)              # ±3일 끝 둘 — 이른 점
        self.assertIsNone(lb.match(dates(0, 24, 32, 40), t))                # 4일 — 범위 밖

    def test_holiday_week_point_on_thursday(self):
        p = self.pts((0, "4.00"), (7, "4.10"), (14, "4.20"), (21, "4.30"), (27, "4.55"), (35, "4.60"))
        o = lb.outcome(p, self.D0, 4, None)
        self.assertEqual((o["state"], o["start"], o["end"], o["change_bp"]), ("done", "2026-01-02", "2026-01-29", 55.0))

    def test_tie_in_outcome(self):
        p = self.pts((0, "1.00"), (26, "1.20"), (30, "1.50"), (40, "1.70"))
        o = lb.outcome(p, self.D0, 4, None)
        self.assertEqual((o["end"], o["change_bp"]), ("2026-01-28", 20.0))

    def test_start_is_the_first_point_on_or_after_the_event_day(self):
        """그날 기록은 그 앞날까지의 자료로 정해졌다 — 전환을 만든 움직임(그 앞 금요일 → 전환 날)은 결과에 넣지 않는다."""
        p = self.pts((0, "2.00"), (7, "2.50"), (28, "3.00"), (35, "3.00"), (60, "3.10"))
        o = lb.outcome(p, plus(self.D0, 5), 4, None)                      # 수요일 전환 → 그 주 금요일에서(앞 금요일이 아니다)
        self.assertEqual((o["start"], o["end"], o["change_bp"]), ("2026-01-09", "2026-02-06", 50.0))
        o = lb.outcome(p, plus(self.D0, 7), 4, None)                      # 금요일 전환 → 그날 점에서
        self.assertEqual((o["start"], o["end"], o["change_bp"]), ("2026-01-09", "2026-02-06", 50.0))
        o = lb.outcome(p, plus(self.D0, 8), 4, None)                      # 토요일 전환 → 다음 점은 20일 뒤 — 7일 넘음
        self.assertEqual((o["state"], o["start"]), ("missing", None))
        q = self.pts((0, "2.00"), (6, "2.40"), (40, "2.90"), (60, "3.10"))
        o = lb.outcome(q, plus(self.D0, 1), 4, None)                      # 휴일 주 목요일 점(6일 뒤)은 7일 안
        self.assertEqual((o["state"], o["start"]), ("missing", "2026-01-08"))   # 끝 점(34±3일)이 없어 자료 없음
        self.assertEqual(lb.START_DAYS, 7)

    def test_before_the_first_point_and_after_the_last(self):
        p = self.pts((0, "2.00"), (28, "2.50"), (60, "3.10"))
        self.assertEqual(lb.outcome(p, plus(self.D0, -8), 4, None),          # 첫 점이 8일 뒤 — 출발 점 없음
                         {"state": "missing", "start": None, "end": None, "change_bp": None, "demeaned_bp": None})
        self.assertEqual(lb.outcome(p, plus(self.D0, -1), 4, None)["start"], "2026-01-02")   # 하루 뒤 첫 점은 출발 점
        self.assertEqual(lb.outcome([], self.D0, 4, None)["state"], "missing")
        self.assertEqual(lb.outcome(p, plus(self.D0, 61), 4, None),          # 전환 날 이후의 점이 아직 없다
                         {"state": "pending", "start": None, "end": None, "change_bp": None, "demeaned_bp": None})

    def test_pending_until_the_whole_window_has_passed(self):
        p = self.pts((0, "1.00"), (7, "1.10"), (30, "1.30"))              # 30일 점이 범위 안에 있어도 28 + 3 > 30
        o = lb.outcome(p, self.D0, 4, None)
        self.assertEqual((o["state"], o["start"], o["end"], o["change_bp"]), ("pending", "2026-01-02", None, None))
        p = self.pts((0, "1.00"), (7, "1.10"), (31, "1.30"))              # 28 + 3 = 31 — 닫혔다
        self.assertEqual(lb.outcome(p, self.D0, 4, None)["state"], "done")

    def test_missing_when_no_point_in_range(self):
        p = self.pts((0, "1.00"), (20, "1.10"), (40, "1.30"))
        o = lb.outcome(p, self.D0, 4, None)
        self.assertEqual((o["state"], o["start"], o["end"]), ("missing", "2026-01-02", None))

    def test_thirteen_weeks(self):
        p = self.pts((0, "3.00"), (91, "2.75"), (100, "2.70"))
        o = lb.outcome(p, self.D0, 13, -2.1)
        self.assertEqual((o["end"], o["change_bp"], o["demeaned_bp"]), ("2026-04-03", -25.0, -22.9))

    def test_rounding_reads_the_written_decimals(self):
        p = [(self.D0, Decimal(repr(4.86))), (plus(self.D0, 28), Decimal(repr(5.15))), (plus(self.D0, 60), Decimal("5"))]
        self.assertEqual(lb.outcome(p, self.D0, 4, None)["change_bp"], 29.0)          # 5.15 − 4.86 = 0.29000000000000004
        up = [(self.D0, Decimal("0.123")), (plus(self.D0, 28), Decimal("0.1235")), (plus(self.D0, 60), Decimal("0"))]
        self.assertEqual(lb.outcome(up, self.D0, 4, None)["change_bp"], 0.1)          # 0.05 → 0에서 먼 쪽
        down = [(self.D0, Decimal("0.1235")), (plus(self.D0, 28), Decimal("0.123")), (plus(self.D0, 60), Decimal("0"))]
        self.assertEqual(lb.outcome(down, self.D0, 4, None)["change_bp"], -0.1)

    def test_demeaned_uses_the_shown_numbers_and_never_minus_zero(self):
        p = self.pts((0, "1.000"), (28, "1.500"), (60, "2"))
        o = lb.outcome(p, self.D0, 4, 33.3)
        self.assertEqual((o["change_bp"], o["demeaned_bp"]), (50.0, 16.7))
        o = lb.outcome(p, self.D0, 4, 50.0)
        self.assertEqual(o["demeaned_bp"], 0.0)
        self.assertEqual(json.dumps(o["demeaned_bp"]), "0.0")
        flat = self.pts((0, "1.0"), (28, "1.0"), (60, "1.0"))
        o = lb.outcome(flat, self.D0, 4, 0.0)
        self.assertEqual((json.dumps(o["change_bp"]), json.dumps(o["demeaned_bp"])), ("0.0", "0.0"))

    def test_baseline_linear_line(self):
        dates = fridays("2026-01-02", 30)
        pts = [(d, Decimal(1) + Decimal("0.01") * k) for k, d in enumerate(dates)]
        # 마지막 점(29)은 끝 점이 될 수 없다 — 출발 + 7H + 3일이 늘 마지막 점보다 뒤라 기다리는 중(약속의 '닫힌 창'만)
        mean, n, first, last = lb.baseline(pts, 4)
        self.assertEqual((mean, n, first, last), (Decimal(4), 25, dates[0], dates[28]))
        mean, n, first, last = lb.baseline(pts, 13)
        self.assertEqual((mean, n, first, last), (Decimal(13), 16, dates[0], dates[28]))

    def test_baseline_mean_skips_unmatched_and_pending_points(self):
        dates = fridays("2026-01-02", 7)
        pts = list(zip(dates, map(Decimal, ["0", "0.1", "0.3", "0.6", "1.0", "1.5", "2.0"])))   # 2→6은 기다리는 중
        mean, n, _, _ = lb.baseline(pts, 4)
        self.assertEqual((mean, n), (Decimal(120), 2))                      # (100 + 140) / 2
        del pts[4]                                                           # 0의 짝이 없다 — 1→5만
        mean, n, first, _ = lb.baseline(pts, 4)
        self.assertEqual((mean, n, first), (Decimal(140), 1, dates[1]))
        self.assertIsNone(lb.baseline(pts[:3], 4))
        self.assertIsNone(lb.baseline([], 4))


# ── 요약 ─────────────────────────────────────────────────────────────────────────────────────────────────────
class SummaryTest(World):
    """11-06부터 7일마다 기록, alpha가 기록마다 뒤집힌다(met로 시작). 그래프는 금요일 주간 점 — 2차식 + 흔들림이라 변화가 제각각."""

    START = "2026-11-06"

    def world(self, n_snaps, chart_weeks):
        days = [plus(day(self.START), 7 * i) for i in range(n_snaps)]
        self.put([snap(d.isoformat(), [("alpha", "met" if i % 2 == 0 else "not_met")]) for i, d in enumerate(days)])
        dates = fridays("2026-01-02", chart_weeks)
        vals = [round(1 + 0.0007 * k * k - 0.3 * (k % 3) + (0.123 if k % 5 == 0 else 0), 3) for k in range(len(dates))]
        pts = list(zip(dates, vals))
        self.put([], charts(dgs10=pts, t10y2y=pts, tp=pts[: len(pts) - 2]))
        return days, dates, [Decimal(repr(v)) for v in vals]

    def expected(self, days, dates, vals, to, h, weeks):
        """같은 셈을 다르게 — 모든 날이 금요일이라 출발 = 그날 점, 끝 = h주 뒤 점(자리 + h)."""
        idx = {d: k for k, d in enumerate(dates)}
        changes = [(vals[k + h] - vals[k]) * 100 for k in range(weeks - h - 1)]     # 마지막 점은 끝 점이 아니다
        base = Decimal(repr(lb._q(sum(changes) / len(changes))))
        got = []
        for i, d in enumerate(days):
            if i == 0 or d.isoformat() < lb.PROTOCOL_FIXED or ("met" if i % 2 == 0 else "not_met") != to:
                continue
            k = idx.get(d)
            if k is None or k + h >= weeks - 1:                              # 그래프 밖 · 기다리는 중
                continue
            ch = ((vals[k + h] - vals[k]) * 100).quantize(Decimal("0.1"), rounding="ROUND_HALF_UP")
            got.append((ch, ch - base))
        if len(got) < lb.N_MIN:
            return {"n": len(got), "mean_demeaned_bp": None, "up_share": None}
        mean = lb._q(sum(dm for _, dm in got) / len(got))
        up = lb._q(Decimal(sum(1 for c, _ in got if c > 0)) / len(got), Decimal("0.01"))
        return {"n": len(got), "mean_demeaned_bp": mean, "up_share": up}

    def test_summary_known_answers(self):
        days, dates, vals = self.world(24, 90)
        a = self.rule_of(self.build()[1], "alpha")
        self.assertEqual(len(a["events"]), 23)
        self.assertTrue(a["events"][0]["before_protocol"])                   # 11-13 → 미충족은 약속 전
        for name, to in (("to_met", "met"), ("to_not_met", "not_met")):
            for h in lb.HORIZONS:
                want = self.expected(days, dates, vals, to, h, 90)
                self.assertEqual(a["summary"][name][str(h)]["dgs10"], want, (name, h))
                self.assertEqual(a["summary"][name][str(h)]["t10y2y"], want, (name, h))
        shares = {a["summary"][n][str(h)]["dgs10"]["up_share"] for n in ("to_met", "to_not_met") for h in lb.HORIZONS}
        self.assertTrue(shares - {0.0, 1.0}, shares)                         # 오르고 내린 전환이 섞인 세계여야 몫을 본다
        self.assertEqual(a["summary"]["to_met"]["4"]["dgs10"]["n"], 11)
        self.assertEqual(a["summary"]["to_not_met"]["4"]["dgs10"]["n"], 11)    # 약속 전 하나는 뺐다

    def test_judgment_on_hold_below_n_min(self):
        days, dates, vals = self.world(20, 90)
        s = self.rule_of(self.build()[1], "alpha")["summary"]
        self.assertEqual(s["to_met"]["4"]["dgs10"], {"n": 9, "mean_demeaned_bp": None, "up_share": None})
        self.assertEqual(s["to_not_met"]["13"]["tp"], {"n": 9, "mean_demeaned_bp": None, "up_share": None})

    def test_pending_events_are_not_counted(self):
        days, dates, vals = self.world(24, 62)                               # 그래프 끝 2027-02-19 — 뒤쪽 전환은 기다리는 중
        a = self.rule_of(self.build()[1], "alpha")
        states = [e["outcomes"]["13"]["dgs10"]["state"] for e in a["events"]]
        self.assertIn("pending", states)
        n13 = a["summary"]["to_met"]["13"]["dgs10"]["n"]
        n4 = a["summary"]["to_met"]["4"]["dgs10"]["n"]
        self.assertLess(n13, n4)
        self.assertEqual(n13, sum(1 for e in a["events"] if e["to"] == "met" and not e["before_protocol"]
                                  and e["outcomes"]["13"]["dgs10"]["state"] == "done"))
        for name, to in (("to_met", "met"), ("to_not_met", "not_met")):
            for h in lb.HORIZONS:
                self.assertEqual(a["summary"][name][str(h)]["dgs10"], self.expected(days, dates, vals, to, h, 62))

    def test_summary_without_baseline_gives_no_mean(self):
        ev = [{"to": "met", "before_protocol": False,
               "outcomes": {str(h): {k: {"state": "done", "start": "x", "end": "y", "change_bp": -1.0 if i % 4 == 0 else 2.0,
                                         "demeaned_bp": None} for k, _, _ in lb.OUTCOMES} for h in lb.HORIZONS}}
              for i in range(12)]
        s = lb.summarize(ev)
        self.assertEqual(s["to_met"]["4"]["dgs10"], {"n": 12, "mean_demeaned_bp": None, "up_share": 0.75})
        self.assertEqual(s["to_not_met"]["4"]["dgs10"], {"n": 0, "mean_demeaned_bp": None, "up_share": None})


class LedgerChartsTest(World):
    def test_baseline_and_window_in_ledger(self):
        dates = fridays("2025-01-03", 40)
        pts = [(d, round(1 + 0.01 * k, 2)) for k, d in enumerate(dates)]
        self.put([snap("2025-03-03", [("alpha", "met")]), snap("2025-03-10", [("alpha", "not_met")])],
                 charts(dgs10=pts, t10y2y=pts[:20], tp=[]))
        led = self.build()[1]
        c = led["charts"]
        self.assertEqual(c["date"], "2026-11-17")
        self.assertEqual(c["window"], {"from": "2025-01-03", "to": dates[-1].isoformat()})
        self.assertEqual(c["last"], {"dgs10": dates[-1].isoformat(), "t10y2y": dates[19].isoformat(), "tp": None})
        self.assertEqual(c["baseline"], {"4": {"dgs10": 4.0, "t10y2y": 4.0, "tp": None},
                                         "13": {"dgs10": 13.0, "t10y2y": 13.0, "tp": None}})
        self.assertEqual(c["baseline_detail"]["4"]["dgs10"], {"n": 35, "from": "2025-01-03", "to": dates[38].isoformat()})
        self.assertEqual(c["baseline_detail"]["13"]["t10y2y"], {"n": 6, "from": "2025-01-03", "to": dates[18].isoformat()})
        self.assertIsNone(c["baseline_detail"]["4"]["tp"])
        o = led["rules"][0]["events"][0]["outcomes"]
        self.assertEqual(o["4"]["dgs10"], {"state": "done", "start": "2025-03-14", "end": "2025-04-11",   # 월요일 전환 → 그 주 금요일
                                           "change_bp": 4.0, "demeaned_bp": 0.0})
        self.assertEqual(o["4"]["tp"]["state"], "missing")
        self.assertEqual(o["13"]["t10y2y"]["state"], "pending")              # 20주까지만 — 13주 뒤 + 3일이 끝보다 뒤
        self.assertNotIn("dfii10", json.dumps(led))

    def test_charts_missing_or_broken_still_computes_but_main_keeps_the_old_ledger(self):
        """build는 셈을 돌려준다(결과는 모두 'missing') — main은 그런 날 ledger.json을 쓰지 않고 직전 파일을 그대로 둔다."""
        self.put([snap("2026-10-01", [("alpha", "met")]), snap("2026-10-02", [("alpha", "not_met")])])
        good = charts(*(3 * ([(d, 1.0) for d in fridays("2026-06-05", 30)],)))
        path = os.path.join(self.data, "charts.json")
        for text in (None, "{깨짐", json.dumps({"schema": 2, "overview": []}), json.dumps({"schema": 1, "overview": "x"})):
            if text is None:
                if os.path.exists(path):
                    os.remove(path)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
            led = self.build()[1]
            self.assertEqual(led["charts"]["date"], None)
            self.assertEqual(led["charts"]["window"], {"from": None, "to": None})
            self.assertEqual(led["charts"]["baseline"]["4"], {"dgs10": None, "t10y2y": None, "tp": None})
            self.assertTrue(all(s["citation"] is None for s in led["sources"]))
            o = led["rules"][0]["events"][0]["outcomes"]
            self.assertTrue(all(x["state"] == "missing" for h in o.values() for x in h.values()))
        out = os.path.join(self.data, "out")
        self.put([], good)
        self.assertEqual(quiet_main(["--data", self.data, "--out", out]), 0)
        kept = read_text(os.path.join(out, "ledger.json"))
        self.put([snap("2026-10-05", [("alpha", "met")])])                                 # 기록은 하루 늘었다
        for text in (None, "{깨짐", json.dumps({"schema": 2, "overview": []})):
            if text is None:
                os.remove(path)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
            self.assertEqual(quiet_main(["--data", self.data, "--out", out]), 0)
            self.assertEqual(read_text(os.path.join(out, "ledger.json")), kept)              # 장부는 그대로
            self.assertEqual(read_json(os.path.join(out, "changes.json"))["asof"], "2026-10-05")   # 변화 층은 새로

    def test_one_missing_line_keeps_the_old_ledger(self):
        """한 시리즈만 못 받은 날(그래프에서 선 하나가 빠짐)에도 지난 결과를 '자료 없음'으로 덮지 않는다."""
        pts = [(d, round(4 + 0.01 * k, 2)) for k, d in enumerate(fridays("2026-06-05", 30))]
        self.put([snap("2026-10-01", [("alpha", "met")]), snap("2026-10-09", [("alpha", "not_met")])], charts(pts, pts, pts))
        out = os.path.join(self.data, "out")
        self.assertEqual(quiet_main(["--data", self.data, "--out", out]), 0)
        kept = read_text(os.path.join(out, "ledger.json"))
        self.assertEqual(read_json(os.path.join(out, "ledger.json"))["rules"][0]["events"][0]["outcomes"]["4"]["dgs10"]["state"], "done")
        for drop in ({"dgs10": ()}, {"t10y2y": ()}, {"tp": ()}):
            lines = {"dgs10": pts, "t10y2y": pts, "tp": pts, **drop}
            self.put([snap("2026-10-12", [("alpha", "not_met")])], charts(**lines))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(lb.main(["--data", self.data, "--out", out], now=NOW), 0)
            self.assertIn("::warning::", buf.getvalue())
            self.assertIn(list(drop)[0], buf.getvalue())
            self.assertEqual(read_text(os.path.join(out, "ledger.json")), kept)
            self.assertEqual(read_json(os.path.join(out, "changes.json"))["asof"], "2026-10-12")
        self.assertEqual(lb.chart_gaps("2026-11-17", {"dgs10": [1], "t10y2y": [1], "tp": [1]}), [])
        self.assertEqual(lb.chart_gaps(None, {}), ["charts.json", "dgs10", "t10y2y", "tp"])

    def test_no_ledger_is_written_without_charts_on_the_first_run(self):
        self.put([snap("2026-10-01", [("alpha", "met")])])
        out = os.path.join(self.data, "out")
        self.assertEqual(quiet_main(["--data", self.data, "--out", out]), 0)
        self.assertEqual(os.listdir(out), ["changes.json"])

    def test_sources_carry_the_fred_citation_of_the_charts_day(self):
        pts = [(d, 1.0) for d in fridays("2026-06-05", 30)]
        self.put([snap("2026-10-01", [("alpha", "met")])], charts(pts, pts, pts, date="2026-11-17"))
        led = self.build()[1]
        check_ledger(self, led)
        by = {s["series"]: s for s in led["sources"]}
        self.assertTrue(by["T10Y2Y"]["citation"].startswith("Federal Reserve Bank of St. Louis, 10-Year Treasury Constant Maturity "
                                                            "Minus 2-Year Treasury Constant Maturity [T10Y2Y], retrieved from FRED"))
        self.assertTrue(all(s["citation"].endswith("November 17, 2026.") for s in led["sources"]))
        self.assertEqual([s["series"] for s in led["sources"] if s["citation_required"]], ["T10Y2Y"])
        self.assertIn("macro-regime-check가", led["notices"][0])
        self.assertIn("not published by", led["notices"][1])

    def test_bad_points_are_dropped(self):
        dates = fridays("2026-01-02", 10)
        pts = [[d.isoformat(), 1.0 + k / 10] for k, d in enumerate(dates)]
        pts[3] = [dates[3].isoformat(), None]
        pts[4] = ["2026-13-01", 9.0]
        pts[5] = [dates[5].isoformat(), True]
        pts.append("깨짐")
        ch = charts()
        ch["overview"][0]["lines"][0]["points"] = pts
        self.put([snap("2026-01-02", [("alpha", "met")])], ch)
        _, lines = lb.load_charts(os.path.join(self.data, "charts.json"))
        self.assertEqual([d for d, _ in lines["dgs10"]], [d for k, d in enumerate(dates) if k not in (3, 4, 5)])


# ── 변화 층 ──────────────────────────────────────────────────────────────────────────────────────────────────
class ChangesTest(World):
    def world(self):
        h_w1 = [hl("S1"), hl("S2", fetched="missing", last=None), hl("S3", stale=True), hl("S4")]
        h_now = [hl("S1", fetched="missing", last=None), hl("S2"), hl("S3"), hl("S4", stale=True), hl("S5", fetched="cache")]
        self.put([
            snap("2026-10-01", [("alpha", "met"), ("beta", "not_met")]),
            snap("2026-10-20", [("alpha", "met"), ("beta", "not_met")], regime((1, 11), cand="A", auto=2)),
            snap("2026-11-05", [("alpha", "not_met"), ("beta", "not_met"), ("gamma", "not_met")], regime()),
            snap("2026-11-10", [("alpha", "not_met"), ("beta", "met"), ("gamma", "unknown")],
                 regime((1, 11), (1, 2), cand=None, auto=2), h_w1),
            snap("2026-11-16", [("alpha", "not_met"), ("beta", "met"), ("gamma", "not_met")], regime(), h_now),
            snap("2026-11-17", [("alpha", "met"), ("beta", "met"), ("gamma", "not_met"), ("delta", "unknown")],
                 regime((2, 11), (0, 2), cand="A′", auto=0), h_now),
        ])
        return self.build()[0]

    def test_windows_pick_prev_one_week_and_four_weeks(self):
        c = self.world()
        self.assertEqual(c["asof"], "2026-11-17")
        self.assertEqual([(w["key"], w["from"]) for w in c["windows"]],
                         [("prev", "2026-11-16"), ("w1", "2026-11-10"), ("w4", "2026-10-20")])
        rules = {w["key"]: [(r["key"], r["from"], r["to"]) for r in w["rules"]] for w in c["windows"]}
        self.assertEqual(rules["prev"], [("alpha", "not_met", "met"), ("delta", None, "unknown")])
        self.assertEqual(rules["w1"], [("alpha", "not_met", "met"), ("gamma", "unknown", "not_met"), ("delta", None, "unknown")])
        self.assertEqual(rules["w4"], [("beta", "not_met", "met"), ("gamma", None, "not_met"), ("delta", None, "unknown")])
        self.assertEqual(c["windows"][1]["rules"][0]["title"], "규칙 가")

    def test_window_counts_and_regime_pairs(self):
        w1 = self.world()["windows"][1]
        self.assertEqual(w1["met"], {"from": 1, "to": 2, "total_from": 3, "total_to": 4})
        self.assertEqual(w1["core"], {"from": "1/11", "to": "2/11"})
        self.assertEqual(w1["neutral"], {"from": "1/2", "to": "0/2"})
        self.assertEqual(w1["candidate"], {"from": "판정불가", "to": "A′"})                  # 절은 있는데 후보가 없던 날(완충 구간)
        self.assertEqual(w1["transition"], {"from": 2, "to": 0})
        w4 = self.build()[0]["windows"][2]
        self.assertEqual((w4["candidate"], w4["transition"]), ({"from": "A", "to": "A′"}, {"from": 2, "to": 0}))

    def test_candidate_null_means_no_regime_section_and_undecided_means_buffer_zone(self):
        self.put([snap("2026-11-03", [("alpha", "met")]),                                   # 레짐 점검 절 없음
                  snap("2026-11-10", [("alpha", "met")], regime(cand=None)),                # 절은 있고 후보 없음
                  snap("2026-11-16", [("alpha", "met")], regime(cand="Z — 지어낸 글")),     # 모르는 글은 옮기지 않는다
                  snap("2026-11-17", [("alpha", "met")], regime(cand="A′"))])
        w = {x["key"]: x["candidate"] for x in self.build()[0]["windows"]}
        self.assertEqual(w, {"prev": {"from": None, "to": "A′"}, "w1": {"from": "판정불가", "to": "A′"},
                             "w4": {"from": None, "to": "A′"}})
        self.put([snap("2026-11-24", [("alpha", "met")], regime(cand=None))])
        c = self.build()[0]
        self.assertEqual(c["windows"][0]["candidate"], {"from": "A′", "to": "판정불가"})
        self.assertEqual(c["headline"][2], "국면 후보 판정불가 · 1주 전 A′")
        self.put([snap("2026-11-25", [("alpha", "met")], regime(cand=None)),
                  snap("2026-12-01", [("alpha", "met")], regime(cand=None))])
        self.assertEqual(len(self.build()[0]["headline"]), 2)                # 두 쪽 다 판정불가 — 셋째 줄은 없다

    def test_transition_count_is_zero_to_two(self):
        self.put([snap("2026-11-10", [("alpha", "met")], regime(auto=3)), snap("2026-11-17", [("alpha", "met")], regime(auto=2))])
        self.assertEqual(self.build()[0]["windows"][0]["transition"], {"from": None, "to": 2})      # 3은 꼴이 아니다

    def test_health_lost_recovered_stale_fresh(self):
        c = self.world()
        name = lambda xs: [x["series"] for x in xs]
        h = c["windows"][1]["health"]
        self.assertEqual((name(h["lost"]), name(h["recovered"]), name(h["stale"]), name(h["fresh"])),
                         (["S1"], ["S2"], ["S4"], ["S3"]))
        self.assertEqual(h["lost"][0], {"series": "S1", "label": "S1 이름"})
        self.assertEqual(c["windows"][0]["health"], {"lost": [], "recovered": [], "stale": [], "fresh": []})   # 같은 상태
        self.assertEqual(c["windows"][2]["health"], {"lost": [], "recovered": [], "stale": [], "fresh": []})   # 그땐 목록 없음

    def test_not_received_is_the_pages_definition(self):
        self.assertTrue(lb.not_received({"last": None, "fetched": "net"}))
        self.assertTrue(lb.not_received({"last": "", "fetched": "net"}))
        self.assertTrue(lb.not_received({"last": "2026-11-01", "fetched": "missing"}))
        self.assertFalse(lb.not_received({"last": "2026-11-01", "fetched": "net"}))
        self.assertFalse(lb.not_received({"last": "2026-11-01", "fetched": "cache"}))      # 화면 notReceived()와 같다
        page = read_text(os.path.join(REPO, "site", "index.html"))
        self.assertIn('function notReceived(h) { return !h.last || h.fetched === "missing"; }', page)

    def test_headline_full(self):
        c = self.world()
        self.assertEqual(c["headline"], [
            "핵심 신호 2/11 · 1주 전 1/11",
            "1주 사이 바뀐 규칙 3개: 규칙 가(미충족→충족) · 규칙 다(판정 불가→미충족) 외 1개",
            "국면 후보 A′ · 1주 전 판정불가 · 받지 못한 시리즈 1개"])

    def test_recent_flips_newest_first(self):
        c = self.world()
        self.assertEqual(c["recent_from"], "2026-10-19")
        self.assertEqual([(e["date"], e["key"], e["from"], e["to"]) for e in c["recent"]],
                         [("2026-11-17", "alpha", "not_met", "met"), ("2026-11-10", "beta", "not_met", "met"),
                          ("2026-11-05", "alpha", "met", "not_met")])
        self.assertEqual(c["recent"][0]["title"], "규칙 가")

    def test_recent_window_edge(self):
        self.put([snap("2026-10-17", [("alpha", "met"), ("beta", "met")]),
                  snap("2026-10-18", [("alpha", "not_met"), ("beta", "met")]),      # asof − 30일 — 빠진다
                  snap("2026-10-19", [("alpha", "not_met"), ("beta", "not_met")]),  # asof − 29일 — 든다
                  snap("2026-11-17", [("alpha", "not_met"), ("beta", "not_met")])])
        c = self.build()[0]
        self.assertEqual([(e["date"], e["key"]) for e in c["recent"]], [("2026-10-19", "beta")])

    def test_same_day_flips_follow_rule_order(self):
        self.put([snap("2026-11-10", [("beta", "met"), ("alpha", "met")]),
                  snap("2026-11-17", [("beta", "not_met"), ("alpha", "not_met")])])
        self.assertEqual([e["key"] for e in self.build()[0]["recent"]], ["beta", "alpha"])

    def test_flips_inside_the_week_show_in_the_headline(self):
        self.put([snap("2026-11-10", [("alpha", "met"), ("beta", "met")]),
                  snap("2026-11-12", [("alpha", "not_met"), ("beta", "met")]),
                  snap("2026-11-14", [("alpha", "met"), ("beta", "unknown")]),
                  snap("2026-11-17", [("alpha", "met"), ("beta", "met")])])
        c = self.build()[0]
        self.assertEqual(c["headline"][1], "1주 사이 바뀐 규칙 없음 · 그 사이 전환 2번")        # 11-10의 전환은 1주 전 기록이 이미 본다
        self.assertEqual([(e["date"], e["key"]) for e in c["recent"]], [("2026-11-14", "alpha"), ("2026-11-12", "alpha")])

    def test_single_snapshot(self):
        self.put([snap("2026-11-17", [("alpha", "met"), ("beta", "not_met")], health=[hl("S1")])])
        c = self.build()[0]
        self.assertEqual([w["from"] for w in c["windows"]], [None, None, None])
        self.assertEqual(c["windows"][0]["met"], {"from": None, "to": 1, "total_from": None, "total_to": 2})
        self.assertEqual(c["windows"][0]["core"], {"from": None, "to": None})
        self.assertEqual(c["headline"], ["충족 규칙 1/2"])
        self.assertEqual(c["recent"], [])
        check_changes(self, c)


class HeadlineTest(unittest.TestCase):
    def s(self, date, statuses, reg=None, health=None):
        return lb._snapshot(snap(date, statuses, reg, health), day(date))

    def test_line_one_branches(self):
        now = self.s("2026-11-17", [("alpha", "met"), ("beta", "met")], regime((2, 11)))
        w1 = self.s("2026-11-10", [("alpha", "met"), ("beta", "not_met")], regime((1, 11)))
        bare_now = self.s("2026-11-17", [("alpha", "met"), ("beta", "met")])
        bare_w1 = self.s("2026-11-10", [("alpha", "met"), ("beta", "not_met"), ("gamma", "met")])
        self.assertEqual(lb.headline(now, w1, [])[0], "핵심 신호 2/11 · 1주 전 1/11")
        self.assertEqual(lb.headline(now, bare_w1, [])[0], "충족 규칙 2/2 · 1주 전 2/3")
        self.assertEqual(lb.headline(bare_now, w1, [])[0], "충족 규칙 2/2 · 1주 전 1/2")
        self.assertEqual(lb.headline(now, None, []), ["핵심 신호 2/11", "국면 후보 A′"])
        self.assertEqual(lb.headline(bare_now, None, []), ["충족 규칙 2/2"])

    def test_line_two_branches(self):
        now = self.s("2026-11-17", [("alpha", "met")])
        w1 = self.s("2026-11-10", [("alpha", "met")])
        r = lambda k, a, b: {"key": k, "title": TITLES[k], "from": a, "to": b}
        self.assertEqual(lb.headline(now, w1, [])[1], "1주 사이 바뀐 규칙 없음")
        self.assertEqual(lb.headline(now, w1, [r("alpha", "not_met", "met")])[1], "1주 사이 바뀐 규칙 1개: 규칙 가(미충족→충족)")
        self.assertEqual(lb.headline(now, w1, [r("alpha", "met", "unknown"), r("beta", None, "not_met")])[1],
                         "1주 사이 바뀐 규칙 2개: 규칙 가(충족→판정 불가) · 규칙 나(새 규칙→미충족)")
        four = [r("alpha", "met", "not_met"), r("beta", "not_met", "met"), r("gamma", None, "met"), r("delta", "unknown", "met")]
        self.assertEqual(lb.headline(now, w1, four)[1], "1주 사이 바뀐 규칙 4개: 규칙 가(충족→미충족) · 규칙 나(미충족→충족) 외 2개")

    def test_line_two_counts_flips_the_endpoints_hide(self):
        """두 끝만 견주면 오갔다 돌아온 전환이 보이지 않는다 — 그 주의 전환이 끝끼리 바뀐 규칙(판정된 상태끼리)보다 많으면 붙인다."""
        now = self.s("2026-11-17", [("alpha", "met")])
        w1 = self.s("2026-11-10", [("alpha", "met")])
        r = lambda k, a, b: {"key": k, "title": TITLES[k], "from": a, "to": b}
        self.assertEqual(lb.headline(now, w1, [], 0)[1], "1주 사이 바뀐 규칙 없음")
        self.assertEqual(lb.headline(now, w1, [], 2)[1], "1주 사이 바뀐 규칙 없음 · 그 사이 전환 2번")
        one = [r("alpha", "not_met", "met")]
        self.assertEqual(lb.headline(now, w1, one, 1)[1], "1주 사이 바뀐 규칙 1개: 규칙 가(미충족→충족)")
        self.assertEqual(lb.headline(now, w1, one, 3)[1], "1주 사이 바뀐 규칙 1개: 규칙 가(미충족→충족) · 그 사이 전환 3번")
        added = [r("beta", None, "met")]                                     # 새 규칙의 처음 상태는 전환이 아니다
        self.assertEqual(lb.headline(now, w1, added, 0)[1], "1주 사이 바뀐 규칙 1개: 규칙 나(새 규칙→충족)")
        self.assertEqual(lb.headline(now, w1, added, 1)[1], "1주 사이 바뀐 규칙 1개: 규칙 나(새 규칙→충족) · 그 사이 전환 1번")

    def test_line_three_branches(self):
        st = [("alpha", "met")]
        no_cand = regime(cand=None)
        miss = [hl("S1", fetched="missing", last=None), hl("S2", last=None), hl("S3", fetched="cache")]
        self.assertEqual(len(lb.headline(self.s("2026-11-17", st, no_cand), self.s("2026-11-10", st, no_cand), [])), 2)
        self.assertEqual(lb.headline(self.s("2026-11-17", st, no_cand, miss), self.s("2026-11-10", st, no_cand), [])[2],
                         "받지 못한 시리즈 2개")
        self.assertEqual(lb.headline(self.s("2026-11-17", st, regime(cand="B")), self.s("2026-11-10", st), [])[2],
                         "국면 후보 B · 1주 전 —")
        self.assertEqual(lb.headline(self.s("2026-11-17", st), self.s("2026-11-10", st, regime(cand="C")), [])[2],
                         "국면 후보 — · 1주 전 C")
        self.assertEqual(len(lb.headline(self.s("2026-11-17", st), self.s("2026-11-10", st), [])), 2)


# ── 파일 · 명령 ────────────────────────────────────────────────────────────────────────────────────────────────
class FileTest(World):
    def full_world(self):
        dates = fridays("2026-06-05", 30)
        pts = [(d, round(4 + 0.03 * k - 0.02 * (k % 4), 2)) for k, d in enumerate(dates)]
        self.put([snap("2026-11-03", [("alpha", "met"), ("beta", "not_met")], regime(), [hl("BAA10Y", label="Baa−10년")]),
                  snap("2026-11-10", [("alpha", "not_met"), ("beta", "not_met")], regime(), [hl("BAA10Y", label="Baa−10년")]),
                  snap("2026-11-17", [("alpha", "met"), ("beta", "met")], regime(cand="A"), [hl("BAA10Y", label="Baa−10년")])],
                 charts(pts, pts, pts))

    def run_main(self, out, now=NOW):
        return quiet_main(["--data", self.data, "--out", out], now=now)

    def test_writes_two_json_files_atomically(self):
        self.full_world()
        out = os.path.join(self.data, "out")
        self.assertEqual(self.run_main(out), 0)
        self.assertEqual(sorted(os.listdir(out)), ["changes.json", "ledger.json"])        # .tmp가 남지 않는다
        for name in ("changes.json", "ledger.json"):
            text = read_text(os.path.join(out, name))
            self.assertTrue(text.endswith("}\n") and not text.endswith("\n\n"))
            obj = json.loads(text)
            self.assertEqual(text, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
            self.assertNotIn("NaN", text)
            self.assertNotIn("\\u", text)                                                  # ensure_ascii=False
        check_changes(self, read_json(os.path.join(out, "changes.json")))
        check_ledger(self, read_json(os.path.join(out, "ledger.json")))

    def test_default_out_is_the_data_folder(self):
        self.full_world()
        self.assertEqual(quiet_main(["--data", self.data]), 0)
        self.assertTrue(os.path.exists(os.path.join(self.data, "changes.json")))
        self.assertTrue(os.path.exists(os.path.join(self.data, "ledger.json")))

    def test_no_history_writes_nothing(self):
        out = os.path.join(self.data, "out")
        self.assertEqual(self.run_main(out), 0)
        self.assertFalse(os.path.exists(out))
        self.put([], extra={"2026-11-17.json": "{깨짐"})
        self.assertEqual(self.run_main(out), 0)
        self.assertFalse(os.path.exists(out))
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(quiet_main(["--data", empty]), 0)
            self.assertEqual(os.listdir(empty), [])

    def test_deterministic_except_generated_at(self):
        self.full_world()
        a, b = lb.build(self.data, now="A"), lb.build(self.data, now="B")
        for x, y in zip(a, b):
            self.assertEqual(x.pop("generated_at"), "A")
            self.assertEqual(y.pop("generated_at"), "B")
            self.assertEqual(lb.dumps(x), lb.dumps(y))

    def test_same_content_is_not_rewritten(self):
        self.full_world()
        out = os.path.join(self.data, "out")
        self.run_main(out, now="2026-11-18T00:00:00+00:00")
        before = {n: read_text(os.path.join(out, n)) for n in os.listdir(out)}
        self.run_main(out, now="2026-11-19T00:00:00+00:00")
        after = {n: read_text(os.path.join(out, n)) for n in os.listdir(out)}
        self.assertEqual(before, after)
        self.put([snap("2026-11-18", [("alpha", "not_met"), ("beta", "met")], regime())])
        self.run_main(out, now="2026-11-20T00:00:00+00:00")
        for n in ("changes.json", "ledger.json"):
            self.assertEqual(read_json(os.path.join(out, n))["generated_at"], "2026-11-20T00:00:00+00:00")

    def test_restricted_numbers_and_readings_are_never_copied(self):
        self.full_world()
        for obj in lb.build(self.data, now=NOW):
            text = lb.dumps(obj)
            for planted in PLANTED + ("SP500", "BAMLH0A0HYM2", "observations", "reading", "scenario"):
                self.assertNotIn(planted, text)

    def test_no_verdict_words_and_says_not_a_prediction(self):
        self.full_world()
        for obj in lb.build(self.data, now=NOW):
            text = lb.dumps(obj)
            for w in VERDICT:
                self.assertNotIn(w, text)
        text = " ".join(lb.protocol_text())
        self.assertIn("예측 아님", text)
        self.assertIn("예측이 아니", lb.CHANGES_NOTICE)
        self.assertIn("예측이 아니", lb.LEDGER_NOTICE)

    def test_cli(self):
        self.full_world()
        out = os.path.join(self.data, "out")
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "ledger_build.py"), "--data", self.data, "--out", out],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("[ledger_build] 2026-11-17 기준", r.stdout)
        self.assertEqual(sorted(os.listdir(out)), ["changes.json", "ledger.json"])

    def test_write_failure_exits_one(self):
        self.full_world()
        blocker = os.path.join(self.data, "file")
        open(blocker, "w").close()
        self.assertEqual(self.run_main(os.path.join(blocker, "sub")), 1)


class ProtocolTextTest(unittest.TestCase):
    """평가 약속의 숫자 — 코드의 상수, 화면에 가는 글, README가 같은 숫자를 말한다."""

    def facts(self):
        return ([lb.PROTOCOL_FIXED, f"{lb.PROTOCOL_VERSION}판", f"±{lb.TOL_DAYS}일"] + [f"{h}주" for h in lb.HORIZONS]
                + [sid for _, _, sid in lb.OUTCOMES])

    def test_constants(self):
        self.assertEqual((lb.PROTOCOL_VERSION, lb.PROTOCOL_FIXED, lb.HORIZONS, lb.N_MIN, lb.TOL_DAYS),
                         (1, "2026-11-18", (4, 13), 10, 3))
        self.assertEqual(lb.OUTCOMES, [("dgs10", "미 10년", "DGS10"), ("t10y2y", "10년−2년", "T10Y2Y"),
                                       ("tp", "기간 프리미엄(Kim-Wright)", "THREEFYTP10")])

    def test_protocol_text_states_the_constants(self):
        text = " ".join(lb.protocol_text())
        for fact in self.facts() + [f"{lb.N_MIN}개"]:
            self.assertIn(fact, text)
        for w in VERDICT:
            self.assertNotIn(w, text)

    def section(self):
        readme = read_text(os.path.join(REPO, "README.md"))
        m = re.search(r"^## 참고: 기록 장부와 평가 약속\n(.*?)(?=^## |\Z)", readme, re.M | re.S)
        self.assertIsNotNone(m, "README에 '## 참고: 기록 장부와 평가 약속' 절이 없다")
        return m.group(0)

    def test_readme_states_the_constants(self):
        section = self.section()
        for fact in self.facts() + ["data/changes.json", "data/ledger.json", "scripts/ledger_build.py", "site/ledger.js"]:
            self.assertIn(fact, section, f"README 절에 {fact!r}가 없다")
        self.assertTrue(any(x in section for x in (f"{lb.N_MIN}개", f"≥ {lb.N_MIN}", f"/{lb.N_MIN})")),
                        f"README 절에 n_min {lb.N_MIN}이 없다")
        for w in VERDICT:
            self.assertNotIn(w, section)

    def test_readme_names_the_charts_window_that_rolls(self):
        """평균은 그래프 창(render_charts의 yield10 · term 'years')으로 갱신마다 다시 잰다 — README가 그 길이를 말한다."""
        import render_charts as rc
        years = {c["key"]: c["years"] for c in rc.chart_table()["overview"] if c["key"] in ("yield10", "term")}
        self.assertEqual(len(set(years.values())), 1, years)
        n = years["yield10"]
        section = self.section()
        self.assertIn(f"최근 {n}년", section)
        self.assertIn("창", " ".join(lb.protocol_text()))

    def test_readme_quotes_the_protocol_sentences_as_written(self):
        """화면 · ledger.json의 protocol.text와 README가 같은 글 — 약속 문장을 고치면 README 절도 같이."""
        section = self.section()
        for i, t in enumerate(lb.protocol_text(), 1):
            self.assertIn(f"\n{i}. {t}\n", section, f"README 절에 약속 문장 {i}이 글자 그대로 없다")


# ── 워크플로 · README ────────────────────────────────────────────────────────────────────────────────────────
class StaticTest(unittest.TestCase):
    def test_workflow_builds_right_after_the_charts_without_alerting(self):
        wf = read_text(os.path.join(REPO, ".github", "workflows", "daily.yml"))
        self.assertIn("id: ledger", wf, "daily.yml에 기록 장부 단계(id: ledger) 없음")
        start = wf.rindex("      - name:", 0, wf.index("id: ledger"))
        step = wf[start:wf.index("\n      - ", start + 1)]
        self.assertIn("name: 기록 장부·변화 만들기", step)
        self.assertIn("continue-on-error: true", step)
        self.assertIn("timeout-minutes: 1", step)
        self.assertIn("run: python scripts/ledger_build.py", step)
        self.assertNotIn("if:", step)                                                    # 공개본·그래프가 실패한 날에도 돈다
        between = wf[wf.index("id: charts"):start]
        self.assertNotIn("\n      - ", between, "그래프 자료 단계 바로 뒤가 아니다")      # 사이에 주석 말고 다른 단계가 없다
        self.assertLess(wf.index("id: ledger"), wf.index("id: ktb"))
        self.assertLess(wf.index("id: ledger"), wf.index("공개 전 검사(새 산출물 포함)"))
        self.assertLess(wf.index("id: ledger"), wf.index("git add data"))
        self.assertNotIn("ledger", wf[wf.index("\n  alert:"):])                          # 실패해도 알림을 띄우지 않는다
        self.assertIn("node --test scripts/test_ledger_render.cjs", wf[wf.index("\n  check:"):wf.index("\n  update:")])

    def test_readme_counts_and_commands(self):
        readme = read_text(os.path.join(REPO, "README.md"))
        m = re.search(r"\*\*아침 쪽 Python 테스트 (\d+)개 \+ node 테스트 (\d+)개\*\*\((.*?)\)와 \*\*저녁판", readme)
        py_part, node_part = m.group(3).split(" / node: ")
        mine = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()
        self.assertRegex(py_part, rf"(^| · )기록 장부 {mine}( · |$)")
        cjs = len(re.findall(r"^test\(", read_text(os.path.join(SCRIPTS, "test_ledger_render.cjs")), flags=re.M))
        self.assertRegex(node_part, rf"(^| · )기록 장부 그리기 {cjs}( · |$)")
        for cmd in ("python -X utf8 scripts/test_ledger_build.py", "node --test scripts/test_ledger_render.cjs",
                    "python -X utf8 scripts/ledger_build.py --out"):
            self.assertIn(cmd, readme)
        self.assertIn("(#참고-기록-장부와-평가-약속)", readme[readme.index("## 규칙 13개"):readme.index("## 동작 방식")])


# ── 실제 자료 ────────────────────────────────────────────────────────────────────────────────────────────────
class RealDataTest(unittest.TestCase):
    DATA = os.path.join(REPO, "data")

    def setUp(self):
        if not os.path.isdir(os.path.join(self.DATA, "history")):
            self.skipTest("저장소에 data/history가 없다")

    def test_builder_runs_on_the_repository_data(self):
        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(quiet_main(["--data", self.DATA, "--out", out]), 0)
            c = read_json(os.path.join(out, "changes.json"))
            l = read_json(os.path.join(out, "ledger.json"))
        check_changes(self, c)
        check_ledger(self, l)
        names = sorted(n for n in os.listdir(os.path.join(self.DATA, "history")) if lb.FILE_RE.match(n))
        self.assertEqual(l["history"]["snapshots"] + l["history"]["skipped"], len(names))
        self.assertEqual(c["asof"], l["history"]["to"])
        for text in (lb.dumps(c), lb.dumps(l)):
            for w in VERDICT:
                self.assertNotIn(w, text)

    def test_flips_match_a_plain_reread_of_the_files(self):
        """기록 파일을 따로 읽어 같은 정의로 센 전환과 같다."""
        l = lb.build(self.DATA, now=NOW)[1]
        last, want = {}, {}
        for n in sorted(os.listdir(os.path.join(self.DATA, "history"))):
            if not lb.FILE_RE.match(n):
                continue
            raw = read_json(os.path.join(self.DATA, "history", n))
            for r in raw.get("rules", []):
                st = r.get("status")
                if st not in ("met", "not_met"):
                    continue
                if r["key"] in last and last[r["key"]] != st:
                    want.setdefault(r["key"], []).append((raw["date"], last[r["key"]], st))
                last[r["key"]] = st
        got = {r["key"]: [(e["date"], e["from"], e["to"]) for e in r["events"]] for r in l["rules"] if r["events"]}
        self.assertEqual(got, want)

    def test_published_files_validate_when_present(self):
        for name, check in (("changes.json", check_changes), ("ledger.json", check_ledger)):
            path = os.path.join(self.DATA, name)
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    check(self, json.load(f))


if __name__ == "__main__":
    unittest.main()
