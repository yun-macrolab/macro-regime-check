#!/usr/bin/env python3
"""국채–OIS 참고 자료(ois_fetch) 테스트 — 고르는 법(비공개 원본 ois_dtcc와 같은 경우들), 받기·실패 종류, 받아 둔 날(저장
파일)과 창, FRED 국채 금리, 칸·직전 값 이어 싣기, 이용 조건·출처, 문구 원칙(판정 낱말 없음·원격 글 없음), 화면·워크플로 연결.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — 가짜 urlopen(메모리 zip)·가짜 FRED loader·가짜 시계·임시 폴더. 행과 금리는 모두 지어낸 것이다(실제 DTCC 행이
아니다).
"""
import os, io, re, sys, csv, json, time, socket, shutil, zipfile, datetime, tempfile, unittest, contextlib, urllib.error

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import ois_fetch as of
import cds_fetch as cd
from test_render_public import FORBIDDEN_TEXT

REPO = os.path.dirname(SCRIPTS)
D = datetime.date
TODAY = D(2026, 11, 16)                       # 월요일 — 받을 날은 11-13(금)부터
NOW = datetime.datetime(2026, 11, 16, 22, 17, tzinfo=datetime.timezone.utc)
VERDICT = ("판정", "충족", "신호", "경보", "전망", "매수", "매도", "⚠", "●", "○", "강세", "약세", "호재", "악재", "우려", "부담",
           "상승", "하락", "→", "발동", "O/W", "U/W")
COLS = list(of.COLUMNS) + ["Package indicator", "Notional amount-Leg 1"]
_ids = iter(range(10 ** 6, 10 ** 7))


def row(day=D(2026, 11, 12), years=10, rate="0.0467", leg=1, action="NEWT", event="TRAD", upi="USD-SOFR-OIS Compound",
        ccy="USD", start_lag=2, post="FALSE", did=None, odid="", t="15:00:00", days=None):
    eff = day + datetime.timedelta(days=start_lag)
    if days is not None:
        exp = eff + datetime.timedelta(days=days)
    else:
        try:
            exp = eff.replace(year=eff.year + years)
        except ValueError:
            exp = eff.replace(year=eff.year + years, day=28)
    return {"Dissemination Identifier": did or str(next(_ids)), "Original Dissemination Identifier": odid,
            "Action type": action, "Event type": event, "Execution Timestamp": f"{day.isoformat()}T{t}Z",
            "Effective Date": eff.isoformat(), "Expiration Date": exp.isoformat(),
            "Fixed rate-Leg 1": rate if leg == 1 else "", "Fixed rate-Leg 2": rate if leg == 2 else "",
            "Notional currency-Leg 1": ccy, "Post-priced swap indicator": post, "UPI Underlier Name": upi,
            "Package indicator": "FALSE", "Notional amount-Leg 1": "7,654,321"}


BASE = {2: 4.70, 5: 4.55, 10: 4.60, 30: 4.75}


def day_rows(day, rates=None, n=of.MIN_TRADES, did=None):
    """그날 만기마다 n건 — 만기마다 rates(%) 또는 BASE를 중심으로 ±(중앙값이 정확히 그 값)."""
    out = []
    for t, base in BASE.items():
        for i in range(n):
            r = (rates or {}).get(t, base) + (i - (n - 1) / 2) * 0.002
            out.append(row(day, t, f"{r / 100:.6f}", did=(did + str(t) + str(i)) if did else None))
    return out


def zip_of(rows, cols=COLS, name="CFTC_CUMULATIVE_RATES.csv"):
    text = io.StringIO()
    w = csv.DictWriter(text, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(name, "﻿" + text.getvalue())
    return buf.getvalue()


class Resp:
    """조각으로 읽히는 응답. 조각마다 clock을 step초 민다."""
    def __init__(self, blob, clock=None, step=0.0):
        self.f, self.clock, self.step = io.BytesIO(blob), clock, step

    def read(self, n=-1):
        if self.clock:
            self.clock.t += self.step
        return self.f.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeOpener:
    """날짜 → 행 목록(zip으로 준다) · 'absent'(S3 403 AccessDenied) · 'boom'(연결 실패) · 'http500' · 'badzip' · 'archived' ·
    'nocol' · 'hang' · 'slow'. 여는 데 cost초, 조각마다 step초만큼 시계를 민다."""
    def __init__(self, days, clock=None, cost=0.0, step=0.0, need=0.0):
        self.days, self.clock, self.cost, self.step, self.need, self.calls = days, clock, cost, step, need, []

    def __call__(self, url, timeout=None):
        self.calls.append((url, timeout))
        if self.clock:
            self.clock.t += self.cost
        assert url.startswith("https://kgc0418-tdw-data-0.s3.amazonaws.com/cftc/eod/CFTC_CUMULATIVE_RATES_"), url
        day = D(*map(int, re.search(r"(\d{4})_(\d{2})_(\d{2})\.zip$", url).groups()))
        v = self.days.get(day, "absent")
        if v == "absent":
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, io.BytesIO(b"<Error><Code>AccessDenied</Code></Error>"))
        if v == "http500":
            raise urllib.error.HTTPError(url, 500, "err", {}, io.BytesIO(b"<b>remote https://bad.invalid</b>"))
        if v == "boom":
            raise urllib.error.URLError("remote text https://bad.invalid")
        if v == "badzip":
            return Resp(b"PK\x03\x04 not really a zip")
        if v == "archived":
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, io.BytesIO(
                b"<Error><Code>InvalidObjectState</Code><StorageClass>DEEP_ARCHIVE</StorageClass></Error>"))
        if v == "nocol":
            return Resp(zip_of([{"x": "1"}], ["x"]))
        if v == "hang":
            time.sleep(4)
            return Resp(zip_of([row()]))
        if v == "slow" or (self.need and timeout is not None and timeout < self.need):
            raise urllib.error.URLError(socket.timeout("timed out"))
        return Resp(zip_of(v), self.clock, self.step)


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def all_days(today=TODAY, rows_for=day_rows):
    return {d: rows_for(d) for d in of.targets(today)}


def weekdays(a, b):
    out, d = [], a
    while d <= b:
        if d.weekday() < 5:
            out.append(d)
        d += datetime.timedelta(days=1)
    return out


def tenors(r, n=20, offs=((2, 0.1), (5, -0.05), (10, 0.0), (30, 0.15))):
    """받아 둔 하루(만기마다) — r은 10년 중앙값(%) 또는 None(거래 없음)."""
    return {str(t): ({"n": n, "med": round(r + off, 6), "q1": round(r + off - 0.02, 6), "q3": round(r + off + 0.02, 6)}
                     if r is not None else {"n": 0, "med": None, "q1": None, "q3": None}) for t, off in offs}


def fill(store, days, rate_of, n=20):
    for d in days:
        store["days"][d.isoformat()] = tenors(rate_of(d), n)


def dgs_for(days, y=lambda d, t: {2: 4.90, 5: 4.85, 10: 5.00, 30: 5.40}[t]):
    return {t: [(d, y(d, t)) for d in days] for t in of.TENORS}


class FakeFred:
    """가짜 FRED loader — {ID: 시계열}. fail에 든 ID는 수신 실패, cache에 든 ID는 캐시로 대신."""
    def __init__(self, series, fail=(), cache=()):
        self.series, self.fail, self.cache, self.calls = series, set(fail), set(cache), []

    def __call__(self, sid, cache_dir, offline=False, timeout=None):
        self.calls.append((sid, timeout))
        if sid in self.fail:
            raise RuntimeError("remote text https://bad.invalid")
        return self.series[sid], ("cache" if offline or sid in self.cache else "net")


def fred_of(days, y=None):
    g = dgs_for(days, y) if y else dgs_for(days)
    return FakeFred({of.DGS[t]: s for t, s in g.items()})


class TempDir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)


# ---------- 하루 파일 → 만기별 중앙값 (비공개 원본과 같은 경우들) ----------

class SummarizeTest(unittest.TestCase):
    def test_median_per_tenor_from_spot_sofr_ois_only(self):
        d = D(2026, 11, 12)
        rows = [row(d, 10, r) for r in ("0.0460", "0.0462", "0.0464")] + [row(d, 10, "4.70", leg=2)]   # % 꼴·둘째 다리
        rows += [row(d, 10, "0.0400", upi="USD-Federal Funds-H.15-OIS-COMPOUND"),     # 연방기금 OIS
                 row(d, 10, "0.0400", ccy="EUR"), row(d, 10, "0.0400", action="MODI"), row(d, 10, "0.0400", event="NOVA"),
                 row(d, 10, "0.0400", start_lag=30),                                   # 선도 시작
                 row(d, 10, "0.0400", start_lag=-1),                                   # 체결 앞 시작
                 row(D(2026, 11, 11), 10, "0.0400"),                                   # 다른 날 체결(늦은 보고)
                 row(d, 10, "0.0400", post="TRUE"), row(d, 10, "0.0400", post=" yes "),   # 사후 가격
                 row(d, 9, "0.0400"), row(d, 7, "0.0400"),                             # 만기가 안 맞음
                 {**row(d, 10, "0.0400"), "Fixed rate-Leg 2": "0.04"},                 # 두 다리 다 고정
                 {**row(d, 10, ""), "Fixed rate-Leg 1": " "},                          # 고정 다리 없음
                 row(d, 10, "0.0400", did="X1"), row(d, 10, "", action="EROR", odid="X1"),   # 같은 파일 취소(원 식별자로)
                 row(d, 10, "0.0400", did="X2"), row(d, 10, "", action="EROR", did="X2"),    # 같은 식별자의 취소
                 row(d, 10, "0.30"), row(d, 10, "abc"), row(d, 10, "nan")]             # 30% — 범위 밖 · 숫자 아님
        s = of.summarize(rows, d)
        self.assertEqual(s["10"]["n"], 4)
        self.assertAlmostEqual(s["10"]["med"], 4.63, places=9)                     # 4.60 4.62 4.64 4.70
        self.assertEqual(s["2"], {"n": 0, "med": None, "q1": None, "q3": None})
        self.assertEqual(list(s), ["2", "5", "10", "30"])

    def test_quartiles_and_a_single_trade(self):
        d = D(2026, 11, 12)
        s = of.summarize([row(d, 5, f"{x / 100:.4f}") for x in (4.50, 4.52, 4.54, 4.56, 4.58)] + [row(d, 30, "0.0475")], d)
        self.assertEqual((s["5"]["n"], s["5"]["med"], s["5"]["q1"], s["5"]["q3"]), (5, 4.54, 4.51, 4.57))   # quantiles n=4
        self.assertEqual(s["30"], {"n": 1, "med": 4.75, "q1": 4.75, "q3": 4.75})
        self.assertTrue(of.day_ok(s))

    def test_tenor_tolerance_and_units(self):
        d = D(2026, 11, 12)
        tol = int(of.TENOR_TOL * 365.25)                                               # 10일 — 안
        s = of.summarize([row(d, 30, "0.0475"), row(d, 2, "4.68", leg=2), row(d, 5, "0.000001"),
                          row(d, days=round(10 * 365.25) + tol, rate="0.046"), row(d, days=round(10 * 365.25) - tol, rate="0.048"),
                          row(d, days=round(10 * 365.25) + tol + 2, rate="0.099")], d)                   # 12일 — 밖
        self.assertEqual((s["30"]["n"], s["2"]["med"], s["5"]["n"]), (1, 4.68, 0))   # 0.0001% — 범위 밖
        self.assertEqual((s["10"]["n"], s["10"]["med"]), (2, 4.7))
        self.assertEqual([of._rate(x) for x in ("0.05", "5", "1", "15", "15.01", "0.0004", "1,5", "")],
                         [5.0, 5.0, 1.0, 15.0, None, None, 15.0, None])            # 1 이상은 %, 쉼표는 지운다
        self.assertEqual((of._rate("0.0005"), of._rate("0.05")), (0.05, 5.0))          # 범위 끝은 들어간다

    def test_name_needs_usd_and_sofr_and_usd_notional(self):
        self.assertTrue(of.is_sofr_ois({"UPI Underlier Name": "usd-sofr-compound", "Notional currency-Leg 1": "usd"}))
        self.assertFalse(of.is_sofr_ois({"UPI Underlier Name": "EUR-ESTR-OIS", "Notional currency-Leg 1": "USD"}))
        self.assertFalse(of.is_sofr_ois({"UPI Underlier Name": "USD-SOFR-OIS Compound", "Notional currency-Leg 1": "EUR"}))
        self.assertFalse(of.is_sofr_ois({"UPI Underlier Name": "USD-Federal Funds", "Notional currency-Leg 1": "USD"}))
        self.assertFalse(of.is_sofr_ois({}))


# ---------- 받기 ----------

class FetchTest(unittest.TestCase):
    def test_parse_zip_reads_the_first_csv_in_memory_with_only_the_needed_columns(self):
        rows = of.parse_zip(zip_of([row(rate="0.0467")]))
        self.assertEqual(set(rows[0]), set(of.COLUMNS))                              # 필요한 칸만 남긴다
        self.assertEqual(rows[0]["Fixed rate-Leg 1"], "0.0467")
        self.assertTrue(rows[0]["Dissemination Identifier"][:1].isdigit())        # BOM이 머리글에 남지 않는다
        with self.assertRaises(cd.FetchError):
            of.parse_zip(b"not a zip")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("readme.txt", "x")
        with self.assertRaises(cd.FetchError):
            of.parse_zip(buf.getvalue())

    def test_blank_lines_and_short_rows_read_like_dictreader(self):
        text = ",".join(of.COLUMNS) + "\r\n\r\n" + "123,,NEWT\r\n"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("a.csv", text)
        rows = of.parse_zip(buf.getvalue())
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["Action type"], rows[0]["Event type"]), ("NEWT", None))
        self.assertEqual(of.summarize(rows, D(2026, 11, 12))["10"]["n"], 0)

    def test_fetch_absent_file_is_none_and_other_failures_raise(self):
        day = D(2026, 11, 12)
        op = FakeOpener({day: [row()], D(2026, 11, 11): "http500", D(2026, 11, 10): "boom"})
        self.assertEqual(len(of.fetch(day, 5, op)), 1)
        self.assertEqual(op.calls[0], ("https://kgc0418-tdw-data-0.s3.amazonaws.com/cftc/eod/"
                                        "CFTC_CUMULATIVE_RATES_2026_11_12.zip", 5))
        self.assertIsNone(of.fetch(D(2026, 11, 9), 5, op))
        kinds = []
        for d in (D(2026, 11, 11), D(2026, 11, 10)):
            with self.assertRaises(cd.FetchError) as c:
                of.fetch(d, 5, op)
            kinds.append(c.exception.kind)
            self.assertNotIn("bad.invalid", str(c.exception))                   # 원격 글을 담지 않는다
        self.assertEqual(kinds, ["day", "net"])

    def test_timeouts_corrupt_zips_and_the_deadline(self):
        day = D(2026, 11, 12)
        with self.assertRaises(cd.FetchError) as c:
            of.fetch(day, 5, FakeOpener({day: "slow"}))
        self.assertEqual(c.exception.kind, "timeout")
        with self.assertRaises(cd.FetchError) as c:
            of.fetch(day, 5, FakeOpener({day: "badzip"}))
        self.assertEqual(c.exception.kind, "day")
        clock = FakeClock()
        old = of.CHUNK
        of.CHUNK = 64
        try:
            with self.assertRaises(cd.FetchError) as c:
                of.fetch(day, 5, FakeOpener({day: [row()] * 30}, clock=clock, step=1), deadline=3, clock=clock)
        finally:
            of.CHUNK = old
        self.assertEqual(c.exception.kind, "budget")

    def test_403_without_access_denied_is_an_error_and_404_is_absent(self):
        def op403(url, timeout=None):
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, io.BytesIO(b"proxy says no"))
        with self.assertRaises(cd.FetchError) as c:
            of.fetch(D(2026, 11, 12), 5, op403)
        self.assertEqual(c.exception.kind, "net")

        def op404(url, timeout=None):
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b""))
        self.assertIsNone(of.fetch(D(2026, 11, 12), 5, op404))

    def test_header_case_and_spacing_changes_are_accepted(self):
        cols = [c.upper() if c == "Effective Date" else ("  " + c) if c == "UPI Underlier Name" else c for c in COLS]
        r0 = row(rate="0.0467")
        rows = of.parse_zip(zip_of([{new: r0[old] for old, new in zip(COLS, cols)}], cols))
        self.assertEqual(of.summarize(rows, D(2026, 11, 12))["10"], {"n": 1, "med": 4.67, "q1": 4.67, "q3": 4.67})

    def test_missing_columns_archived_days_and_odd_zips(self):
        day = D(2026, 11, 12)
        with self.assertRaises(cd.FetchError) as c:
            of.fetch(day, 5, FakeOpener({day: "nocol"}))
        self.assertEqual(c.exception.kind, "day")
        self.assertIsNone(of.fetch(day, 5, FakeOpener({day: "archived"})))
        raw = bytearray(zip_of([row()]))
        raw[8:10] = (9).to_bytes(2, "little")                                   # 압축 방식 9(Deflate64) — 지원하지 않음
        cen = raw.rfind(b"PK\x01\x02")
        raw[cen + 10:cen + 12] = (9).to_bytes(2, "little")
        with self.assertRaises(cd.FetchError) as c:
            of.parse_zip(bytes(raw))
        self.assertEqual(c.exception.kind, "day")

    def test_read1_lets_the_deadline_bite_between_small_reads(self):
        class Drip(Resp):
            def read1(self, n=-1):
                return Resp.read(self, 16)
        clock = FakeClock()
        op = lambda url, timeout=None: Drip(zip_of([row()] * 30), clock, step=1)
        with self.assertRaises(cd.FetchError) as c:
            of.fetch(D(2026, 11, 12), 5, op, deadline=5, clock=clock)
        self.assertEqual(c.exception.kind, "budget")
        self.assertLessEqual(clock.t, 7)

    def test_too_large_file_is_refused(self):
        old = of.MAX_BYTES
        of.MAX_BYTES = 10
        try:
            with self.assertRaises(cd.FetchError) as c:
                of.fetch(D(2026, 11, 12), 5, FakeOpener({D(2026, 11, 12): [row()]}))
        finally:
            of.MAX_BYTES = old
        self.assertEqual(c.exception.kind, "day")


# ---------- 받아 두기 ----------

class SyncTest(unittest.TestCase):
    def setUp(self):
        self.store = of.empty_store()
        self.N = len(of.targets(TODAY))

    def test_targets_are_weekdays_newest_first(self):
        t = of.targets(TODAY)
        self.assertEqual(t[:3], [D(2026, 11, 13), D(2026, 11, 12), D(2026, 11, 11)])
        self.assertTrue(all(d.weekday() < 5 for d in t))
        self.assertEqual(t, sorted(t, reverse=True))
        self.assertGreaterEqual(t[-1], TODAY - datetime.timedelta(days=of.TARGET_DAYS))
        self.assertEqual(len(t), len(weekdays(TODAY - datetime.timedelta(days=of.TARGET_DAYS), TODAY - datetime.timedelta(days=1))))

    def test_fetches_missing_days_once_and_keeps_only_medians(self):
        op = FakeOpener(all_days())
        r = of.sync(self.store, TODAY, opener=op, budget=500)
        self.assertEqual((r["fetched"], r["error"], r["missing"]), (self.N, None, 0))
        self.assertEqual([c[0][-14:-4] for c in op.calls[:2]], ["2026_11_13", "2026_11_12"])   # 새 날부터
        n = len(op.calls)
        r2 = of.sync(self.store, TODAY, opener=op)
        self.assertEqual((r2["fetched"], len(op.calls)), (0, n))                       # 둘째 실행은 요청 0번
        day = self.store["days"]["2026-11-13"]
        self.assertEqual(day["10"]["n"], of.MIN_TRADES)
        self.assertAlmostEqual(day["10"]["med"], 4.60, places=6)
        self.assertEqual(self.store["status"], {"date": "2026-11-16", "error": None})

    def test_budget_caps_each_request_and_stops(self):
        clock = FakeClock()
        op = FakeOpener(all_days(), clock=clock, cost=3)
        r = of.sync(self.store, TODAY, budget=10, opener=op, clock=clock)
        self.assertEqual([t for _, t in op.calls], [10, 7, 4, 1])
        self.assertEqual((r["fetched"], r["missing"], r["error"]), (3, self.N - 3, None))
        r2 = of.sync(self.store, TODAY, budget=0, opener=op)
        self.assertEqual((len(op.calls), r2["fetched"]), (4, 0))                       # 예산 0이면 요청하지 않는다

    def test_short_request_timeout_is_budget_not_failure(self):
        clock = FakeClock()
        op = FakeOpener(all_days(), clock=clock, cost=3, need=5)
        r = of.sync(self.store, TODAY, budget=10, opener=op, clock=clock)
        self.assertEqual((r["fetched"], r["error"], r["missing"]), (2, None, self.N - 2))
        r2 = of.sync(self.store, TODAY, opener=FakeOpener(all_days()), budget=500)
        self.assertFalse(r2["skipped"])                                             # 같은 날 다음 실행이 이어 받는다
        self.assertEqual(r2["fetched"], self.N - 2)

    def test_full_timeout_is_a_failure_and_the_rest_of_the_day_is_skipped(self):
        days = all_days()
        days[D(2026, 11, 13)] = "slow"
        r = of.sync(self.store, TODAY, opener=FakeOpener(days))
        self.assertEqual(r["error"], "timeout")
        op = FakeOpener(all_days())
        r2 = of.sync(self.store, TODAY, opener=op)
        self.assertEqual((r2["skipped"], r2["error"], len(op.calls)), (True, "timeout", 0))

    def test_one_bad_day_is_skipped_retried_daily_and_given_up(self):
        days = all_days()
        bad = D(2026, 11, 5)
        days[bad] = "http500"
        days[D(2026, 10, 28)] = "badzip"
        op = FakeOpener(days)
        r = of.sync(self.store, TODAY, opener=op, budget=500)
        self.assertEqual((r["fetched"], r["bad"], r["error"]), (self.N - 2, 2, None))
        n = len(op.calls)
        self.assertEqual(of.sync(self.store, TODAY, opener=op)["fetched"], 0)
        self.assertEqual(len(op.calls), n)                                           # 같은 날은 다시 보지 않는다
        for i in (1, 2):
            nxt = TODAY + datetime.timedelta(days=i)
            op.days = {**all_days(nxt), bad: "http500", D(2026, 10, 28): "badzip"}
            self.assertEqual(of.sync(self.store, nxt, opener=op, budget=500)["bad"], 2, i)
        nxt = TODAY + datetime.timedelta(days=3)
        op.days = {**all_days(nxt), bad: day_rows(bad)}                               # 이제 받을 수 있게 되어도
        r = of.sync(self.store, nxt, opener=op, budget=500)
        self.assertEqual((r["bad"], r["gave_up"]), (0, 2))                           # 서로 다른 사흘 실패 — 그만 받는다
        self.assertNotIn(bad.isoformat(), self.store["days"])

    def test_hard_deadline_for_a_hanging_request(self):
        days = all_days()
        days[D(2026, 11, 13)] = "hang"
        t0 = time.monotonic()
        r = of.sync(self.store, TODAY, budget=1.5, opener=FakeOpener(days))
        self.assertLess(time.monotonic() - t0, 3)
        self.assertEqual((r["fetched"], r["error"], r["missing"]), (0, None, self.N))

    def test_a_hang_given_the_full_timeout_is_a_failure(self):
        days = all_days()
        days[D(2026, 11, 13)] = "hang"
        old = of.TIMEOUT
        of.TIMEOUT = 1.5
        try:
            r = of.sync(self.store, TODAY, budget=1.5, opener=FakeOpener(days))
        finally:
            of.TIMEOUT = old
        self.assertEqual(r["error"], "timeout")
        self.assertTrue(of.sync(self.store, TODAY, opener=FakeOpener(all_days()))["skipped"])

    def test_bad_columns_and_archived_days_are_per_day(self):
        days = all_days()
        days[D(2026, 11, 5)] = "nocol"
        days[D(2026, 11, 4)] = "archived"
        r = of.sync(self.store, TODAY, opener=FakeOpener(days), budget=500)
        self.assertEqual((r["bad"], r["absent"], r["error"]), (1, 1, None))
        self.assertNotIn("2026-11-05", self.store["days"])                         # 칸 없는 날을 0건으로 남기지 않는다
        self.assertEqual({k: v["why"] for k, v in self.store["tries"].items()}, {"2026-11-05": "bad", "2026-11-04": "absent"})

    def test_a_day_whose_rows_break_the_count_is_bad(self):
        days = all_days()
        days[D(2026, 11, 5)] = [row(D(2026, 11, 5))]
        orig = of.summarize
        of.summarize = lambda rows, d: 1 / 0 if d == D(2026, 11, 5) else orig(rows, d)
        try:
            r = of.sync(self.store, TODAY, opener=FakeOpener(days), budget=500)
        finally:
            of.summarize = orig
        self.assertEqual((r["bad"], r["error"], self.store["tries"]["2026-11-05"]["why"]), (1, None, "bad"))

    def test_connection_failure_stops_next_day_retries_and_force(self):
        days = all_days()
        days[D(2026, 11, 11)] = "boom"
        r = of.sync(self.store, TODAY, opener=FakeOpener(days))
        self.assertEqual((r["fetched"], r["error"]), (2, "fetch"))
        self.assertEqual(self.store["status"], {"date": "2026-11-16", "error": "fetch"})
        self.assertTrue(of.sync(self.store, TODAY, opener=FakeOpener(all_days()))["skipped"])
        r3 = of.sync(self.store, TODAY, opener=FakeOpener(all_days()), force=True, budget=500)
        self.assertEqual((r3["skipped"], r3["error"], r3["fetched"]), (False, None, self.N - 2))
        s2 = of.empty_store()
        of.sync(s2, TODAY, opener=FakeOpener(days))
        self.assertFalse(of.sync(s2, TODAY + datetime.timedelta(days=1), opener=FakeOpener(all_days()))["skipped"])

    def test_recent_absent_days_are_not_errors(self):
        today = D(2026, 11, 19)                                                        # 목요일 — 사흘 안은 화·수
        days = all_days(today)
        for i in (1, 2, 3):
            days[today - datetime.timedelta(days=i)] = "absent"
        r = of.sync(self.store, today, opener=FakeOpener(days), budget=500)
        n = len(of.targets(today))
        self.assertEqual((r["error"], r["fetched"], r["absent"]), (None, n - 3, 0))
        self.assertNotIn("2026-11-18", self.store["days"])
        nxt = today + datetime.timedelta(days=1)
        of.sync(self.store, nxt, opener=FakeOpener(all_days(nxt)), budget=500)
        self.assertIn("2026-11-18", self.store["days"])                              # 다음 실행에 다시 본다

    def test_alarm_when_recent_days_fail_and_nothing_was_fetched(self):
        days = {d: "absent" for d in of.targets(TODAY)}
        op = FakeOpener(days)
        r = of.sync(self.store, TODAY, opener=op)
        young = sum(1 for d in of.targets(TODAY) if (TODAY - d).days <= of.RETRY_DAYS)
        self.assertEqual(len(op.calls), young + of.ALARM_DAYS)
        self.assertEqual(r["error"], "alarm")
        days = {d: "nocol" for d in of.targets(TODAY)}
        self.assertEqual(of.sync(of.empty_store(), TODAY, opener=FakeOpener(days))["error"], "alarm")
        days = all_days()
        days[D(2026, 11, 5)] = days[D(2026, 11, 4)] = days[D(2026, 11, 3)] = "absent"      # 받은 것이 있으면 넘어간다
        r = of.sync(of.empty_store(), TODAY, opener=FakeOpener(days), budget=500)
        self.assertEqual((r["error"], r["absent"], r["fetched"]), (None, 3, self.N - 3))

    def test_old_absent_days_are_not_an_alarm(self):
        days = all_days()
        for d in of.targets(TODAY)[-30:]:                                              # 2년 끝 쪽 — 보관되었거나 없는 날
            days[d] = "absent"
        r = of.sync(self.store, TODAY, opener=FakeOpener(days), budget=500)
        self.assertEqual((r["error"], r["absent"]), (None, 30))

    def test_never_raises(self):
        r = of.sync({"days": None}, TODAY, opener=FakeOpener(all_days()))
        self.assertEqual(r["error"], "fetch")


# ---------- FRED ----------

class FredTest(TempDir):
    def test_ten_year_first_budget_and_failures(self):
        days = weekdays(D(2026, 10, 1), D(2026, 11, 13))
        f = fred_of(days)
        dgs, err = of.load_fred(self.tmp, fred_load=f)
        self.assertEqual([s for s, _ in f.calls], ["DGS10", "DGS2", "DGS5", "DGS30"])     # 10년 먼저
        self.assertEqual((sorted(dgs), err), ([2, 5, 10, 30], {}))
        self.assertTrue(all(t <= of.ai.TIMEOUT and t <= of.FRED_BUDGET for _, t in f.calls))
        f2 = FakeFred(f.series, fail={"DGS30"}, cache={"DGS5"})
        dgs, err = of.load_fred(self.tmp, fred_load=f2)
        self.assertEqual((sorted(dgs), err), ([2, 10], {"DGS30": "fetch", "DGS5": "fetch"}))   # 온라인 캐시 대체도 못 받은 것
        dgs, err = of.load_fred(self.tmp, offline=True, fred_load=f2)
        self.assertIn(5, dgs)                                                          # --offline이면 캐시를 쓴다
        clock = FakeClock()
        f3 = FakeFred({**f.series, "DGS2": []})
        slow = lambda sid, *a, **k: (setattr(clock, "t", clock.t + 9), f3(sid, *a, **k))[1]
        dgs, err = of.load_fred(self.tmp, fred_load=slow, clock=clock)
        self.assertEqual(err, {"DGS2": "format", "DGS30": "fetch"})                   # 빈 시계열 · 예산(20초)을 다 씀
        self.assertEqual([s for s, _ in f3.calls], ["DGS10", "DGS2", "DGS5"])

    def test_real_loader_uses_the_cache_folder_offline(self):
        cache = os.path.join(self.tmp, of.CACHE)
        os.makedirs(cache)
        with open(os.path.join(cache, "DGS10.csv"), "w", encoding="utf-8") as fh:
            fh.write("observation_date,DGS10\n2026-11-12,4.10\n2026-11-13,.\n")
        dgs, err = of.load_fred(self.tmp, offline=True)
        self.assertEqual(dgs, {10: [(D(2026, 11, 12), 4.10)]})
        self.assertEqual(set(err), {"DGS2", "DGS5", "DGS30"})


# ---------- 창 ----------

class WindowTest(unittest.TestCase):
    def setUp(self):
        self.store = of.empty_store()
        self.days = weekdays(D(2025, 11, 3), D(2026, 11, 13))
        fill(self.store, self.days, lambda d: 4.60)                                   # OIS 10년 4.60% 고정
        y = lambda d, base: 5.00 + base + (0.0 if d < D(2026, 8, 1) else 0.05)        # 8월부터 국채가 5bp 올랐다
        self.dgs = {t: [(d, y(d, b)) for d in self.days] for t, b in ((2, -0.15), (5, -0.10), (10, 0.0), (30, 0.30))}

    def test_level_change_range_and_cover(self):
        w = of.window(self.store["days"], TODAY, self.dgs)
        self.assertEqual(w["end"], "2026-11-13")
        self.assertAlmostEqual(w["level"]["10"], 45.0, places=6)                      # (5.05 − 4.60) × 100
        self.assertAlmostEqual(w["level"]["2"], (5.05 - 0.15 - 4.70) * 100, places=6)
        self.assertAlmostEqual(w["level"]["5"], (5.05 - 0.10 - 4.55) * 100, places=6)
        self.assertAlmostEqual(w["level"]["30"], (5.35 - 4.75) * 100, places=6)
        self.assertAlmostEqual(w["chg13"], 0.0, places=6)                              # 91일 전(08-14 근처)도 8월 뒤
        self.assertEqual((w["range1y"]["lo"], w["range1y"]["hi"]), (40.0, 45.0))
        # 같은 값이면 이른 날 — 최저는 창(364일 전 금요일 다음 날부터)의 다섯째 평일, 최고는 8월 셋째 평일
        self.assertEqual((w["range1y"]["lo_day"], w["range1y"]["hi_day"]), ("2025-11-21", "2026-08-05"))
        self.assertEqual(w["cover"], {"days": 260, "weekdays": 260})
        self.assertEqual((w["age"], w["stale"], w["n10"], w["iqr10"]), (3, False, 20, 4.0))

    def test_thirteen_week_change_crosses_a_step(self):
        w = of.window(self.store["days"], D(2026, 10, 1), self.dgs)                  # 끝 09-30, 91일 전은 7월 — 계단 앞
        self.assertEqual(w["end"], "2026-09-30")
        self.assertAlmostEqual(w["chg13"], 5.0, places=6)

    def test_thin_days_missing_yields_and_gaps(self):
        fill(self.store, [D(2026, 11, 13)], lambda d: None)                           # 거래 없는 날(휴일)은 뺀다
        w = of.window(self.store["days"], TODAY, self.dgs)
        self.assertEqual(w["end"], "2026-11-12")
        fill(self.store, [D(2026, 11, 12)], lambda d: 4.6, n=of.MIN_TRADES - 1)       # 9건 — 그날은 쓰지 않는다
        self.assertEqual(of.window(self.store["days"], TODAY, self.dgs)["end"], "2026-11-11")
        w = of.window(self.store["days"], TODAY, {**self.dgs, 30: []})
        self.assertIsNone(w["level"]["30"])
        short = of.empty_store()
        fill(short, weekdays(D(2026, 11, 2), D(2026, 11, 5)), lambda d: 4.6)          # 네 날뿐 — 5영업일 중앙값 없음
        w = of.window(short["days"], TODAY, self.dgs)
        self.assertEqual((w["level"]["10"], w["chg13"], w["range1y"]), (None, None, None))
        self.assertIsNone(of.window({}, TODAY, self.dgs))
        self.assertIsNone(of.window(self.store["days"], TODAY, {}))
        self.assertEqual(of.why_none({}, TODAY, self.dgs), "none")
        self.assertEqual(of.why_none(self.store["days"], TODAY, {2: self.dgs[2]}), "fred")
        thin = of.empty_store()
        fill(thin, self.days, lambda d: 4.6, n=3)
        self.assertIsNone(of.window(thin["days"], TODAY, self.dgs))
        self.assertEqual(of.why_none(thin["days"], TODAY, self.dgs), "format")

    def test_five_values_must_sit_within_fourteen_days(self):
        s = of.empty_store()
        d0 = [D(2026, 10, 26), D(2026, 10, 27), D(2026, 10, 28), D(2026, 10, 29)]
        fill(s, d0 + [D(2026, 11, 9)], lambda d: 4.6)                                 # 다섯째가 끝 날, 첫째가 14일 전
        self.assertIsNotNone(of.window(s["days"], TODAY, self.dgs)["level"]["10"])
        s["days"].pop("2026-11-09")
        fill(s, [D(2026, 11, 10)], lambda d: 4.6)                                     # 15일 — 없음
        self.assertIsNone(of.window(s["days"], TODAY, self.dgs)["level"]["10"])

    def test_today_is_not_read_and_staleness(self):
        fill(self.store, [TODAY], lambda d: 3.0)
        dgs = {t: s + [(TODAY, 9.0)] for t, s in self.dgs.items()}
        self.assertEqual(of.window(self.store["days"], TODAY, dgs)["end"], "2026-11-13")
        w = of.window(self.store["days"], D(2026, 11, 20), self.dgs)
        self.assertEqual((w["age"], w["stale"]), (7, False))
        w = of.window(self.store["days"], D(2026, 11, 21), self.dgs)
        self.assertEqual((w["age"], w["stale"]), (8, True))

    def test_partial_cover_counts_only_held_days(self):
        s = of.empty_store()
        fill(s, self.days[-20:], lambda d: 4.6)
        w = of.window(s["days"], TODAY, self.dgs)
        self.assertEqual(w["cover"], {"days": 20, "weekdays": 260})
        self.assertIsNone(w["chg13"])                                                  # 13주 전 자료 없음


# ---------- 저장 파일 ----------

class StoreTest(TempDir):
    def test_text_is_valid_json_one_day_per_line_and_round_trips(self):
        s = of.empty_store()
        s["days"]["2026-11-13"] = tenors(4.6)
        s["days"]["2026-11-12"] = tenors(None)
        s["tries"] = {"2026-11-05": {"n": 1, "last": "2026-11-16", "why": "bad"}}
        s["status"] = {"date": "2026-11-16", "error": None}
        text = of.store_text(s)
        js = json.loads(text)
        self.assertEqual(set(js), {"schema", "notice", "source", "tenors", "days", "tries", "status"})
        self.assertEqual((js["source"], js["tenors"]), (of.CITATION, ["2", "5", "10", "30"]))
        lines = [l for l in text.splitlines() if l.startswith('"2026-')]
        self.assertEqual([l[1:11] for l in lines], ["2026-11-12", "2026-11-13"])         # 하루 한 줄, 날짜 차례
        with open(os.path.join(self.tmp, of.STORE), "w", encoding="utf-8") as f:
            f.write(text)
        self.assertEqual(of.load_store(self.tmp), s)
        self.assertEqual(json.loads(of.store_text(of.empty_store()))["days"], {})

    def test_load_drops_malformed_days_and_bookkeeping(self):
        good = tenors(4.6)
        bad_med = {**tenors(4.6), "10": {"n": 3, "med": 99.0, "q1": 99.0, "q3": 99.0}}        # RATE_PCT 밖
        extra = {**tenors(4.6), "10": {"n": 3, "med": 4.6, "q1": 4.5, "q3": 4.7, "id": "123456789"}}
        few = {k: v for k, v in tenors(4.6).items() if k != "30"}
        order = {**tenors(4.6), "10": {"n": 3, "med": 4.6, "q1": 4.7, "q3": 4.8}}              # q1 > med
        zero = {**tenors(4.6), "10": {"n": 0, "med": 4.6, "q1": None, "q3": None}}
        boolean = {**tenors(4.6), "10": {"n": True, "med": 4.6, "q1": 4.5, "q3": 4.7}}
        js = {"schema": 1, "days": {"2026-11-13": good, "2026-11-12": bad_med, "2026-11-11": extra, "2026-11-10": few,
                                    "2026-11-09": order, "2026-11-06": zero, "2026-11-05": boolean, "어제": good,
                                    "2026-11-04": "x"},
              "tries": {"2026-11-03": {"n": 1, "last": "2026-11-16", "why": "bad"},
                        "2026-11-02": {"n": 9, "last": "2026-11-16", "why": "bad"},
                        "2026-10-30": {"n": 1, "last": "2026-11-16", "why": "원격 글"}},
              "status": {"date": "2026-11-16", "error": "URLError: https://bad.invalid"}}
        with open(os.path.join(self.tmp, of.STORE), "w", encoding="utf-8") as f:
            json.dump(js, f, ensure_ascii=False)
        s = of.load_store(self.tmp)
        self.assertEqual(set(s["days"]), {"2026-11-13"})
        self.assertEqual(set(s["tries"]), {"2026-11-03"})
        self.assertEqual(s["status"], {})
        for body in ("{broken", json.dumps({"schema": 2, "days": {}}), json.dumps([1])):
            with open(os.path.join(self.tmp, of.STORE), "w", encoding="utf-8") as f:
                f.write(body)
            self.assertEqual(of.load_store(self.tmp), of.empty_store())

    def test_prune_keeps_only_the_targets(self):
        s = of.empty_store()
        for i in range(1, 800):
            s["days"][(TODAY - datetime.timedelta(days=i)).isoformat()] = tenors(4.6)
        s["days"][TODAY.isoformat()] = tenors(4.6)
        s["tries"] = {"2020-01-01": {"n": 1, "last": "2026-11-16", "why": "bad"},
                      "2026-11-05": {"n": 1, "last": "2026-11-16", "why": "bad"}}
        of.prune(s, TODAY)
        self.assertEqual(set(s["days"]), {d.isoformat() for d in of.targets(TODAY)})
        self.assertEqual(set(s["tries"]), {"2026-11-05"})


# ---------- 칸·실행 ----------

def held_store(end=D(2026, 11, 13), n_days=400):
    s = of.empty_store()
    days = weekdays(end - datetime.timedelta(days=n_days), end)
    fill(s, days, lambda d: 4.60 + (0.01 if d.toordinal() % 3 == 0 else 0.0))
    return s, dgs_for(days)


class ItemTest(unittest.TestCase):
    def test_texts(self):
        s, dgs = held_store()
        W = of.window(s["days"], TODAY, dgs)
        data = of.build(W, None, None, {}, NOW)
        lv, ten = data["items"]["level"], data["items"]["ten"]
        self.assertTrue(lv["ok"] and ten["ok"])
        self.assertEqual(lv["line"], "~2026-11-13 5영업일 중앙값: 2년 +20 · 5년 +30 · 10년 +40 · 30년 +65bp")
        self.assertIn("끝 날 10년 거래 20건 · 그날 10년 사분위 폭 4.0bp.", lv["extra"][1])
        self.assertIn("국채 − OIS = −(스와프 스프레드)", lv["extra"][0])
        self.assertIn("zero(현물)", lv["extra"][2])
        r = W["range1y"]
        self.assertEqual(ten["line"], f"~2026-11-13 10년: 13주 변화 {of._s(W['chg13'])}bp · 1년 범위 {of._s(r['lo'])}~"
                                      f"{of._s(r['hi'])}bp (최저 {r['lo_day']} · 최고 {r['hi_day']}) · 받은 날 260/260")
        self.assertEqual((lv["name"], ten["name"]), (of.TITLE["level"], of.TITLE["ten"]))
        self.assertEqual(data["order"], ["level", "ten"])

    def test_signs_rounding_and_missing_parts(self):
        self.assertEqual([of._s(x) for x in (None, 0.4, -0.4, 0.5, -1.5, 2.6, -37.2)], ["—", "0", "0", "0", "-2", "+3", "-37"])
        s = of.empty_store()
        days = weekdays(D(2026, 11, 2), D(2026, 11, 13))
        fill(s, days, lambda d: 4.6)
        W = of.window(s["days"], TODAY, {t: v for t, v in dgs_for(days).items() if t != 30})   # 30년 국채 금리를 못 받았다
        self.assertIsNone(W["level"]["30"])
        data = of.build(W, "fetch", None, {}, NOW, fred_missing=[30])
        lv, ten = data["items"]["level"], data["items"]["ten"]
        self.assertIn("13주 변화 — (13주 전 자료 모자람)", ten["line"])
        self.assertIn("받은 날 10/260", ten["line"])
        self.assertIn("이번 갱신에서 국채 금리(FRED)를 받지 못한 만기: 30년 — 그 만기는 '—'.", lv["extra"])
        self.assertIn("이번 갱신에서 받지 못한 날이 있다 · 수신 실패 — 다음 갱신에 이어 받는다.", ten["extra"])
        four = of.empty_store()
        fill(four, days[-4:], lambda d: 4.6)
        ten4 = of.build(of.window(four["days"], TODAY, dgs_for(days)), None, None, {}, NOW)["items"]["ten"]
        self.assertIn("1년 범위 — (자료 모자람)", ten4["line"])
        self.assertIn("10년 —", of.build(of.window(four["days"], TODAY, dgs_for(days)), None, None, {}, NOW)
                      ["items"]["level"]["line"])

    def test_values_guard_rejects_anything_outside_the_fixed_shape(self):
        s, dgs = held_store()
        v = of.core_from(of.window(s["days"], TODAY, dgs), None)["values"]
        self.assertTrue(of.values_ok(v))
        bad = []
        for mutate in (lambda x: x["level"].update({"10": 1e6}),                         # 지어낸 큰 값
                       lambda x: x["level"].update({"7": 1.0}),
                       lambda x: x["level"].pop("30"),
                       lambda x: x.update(level=dict(reversed(list(x["level"].items())))),
                       lambda x: x.update(chg13="3"),
                       lambda x: (x["level"].update({"10": None}), x.update(chg13=1.0)),  # 10년 수준 없이 13주 변화
                       lambda x: x["range1y"].update(lo=50.0, hi=40.0),
                       lambda x: x["range1y"].update(lo_day="2020-01-01"),
                       lambda x: x["range1y"].update(raw="USD-SOFR"),
                       lambda x: x["cover"].update(days=261),
                       lambda x: x["cover"].update(weekdays=400),
                       lambda x: x.update(n10=3),
                       lambda x: x.update(n10=True),
                       lambda x: x.update(iqr10=-1.0),
                       lambda x: x.update(fred_missing=[30, 2]),
                       lambda x: x.update(fred_missing=[10]),
                       lambda x: x.update(fred_missing=[True]),
                       lambda x: x.update(last_error="URLError"),
                       lambda x: x.update(id="1234567"),
                       lambda x: x.update(end="어제")):
            y = json.loads(json.dumps(v))
            mutate(y)
            bad.append(of.values_ok(y))
        self.assertEqual(bad, [False] * len(bad))
        self.assertFalse(of.values_ok(None))

    def test_values_outside_the_shape_are_never_written(self):
        s, dgs = held_store()
        W = of.window(s["days"], TODAY, dgs)
        W["level"]["10"] = 123456.0
        with contextlib.redirect_stderr(io.StringIO()):
            data = of.build(W, None, None, {}, NOW)
        for it in data["items"].values():
            self.assertEqual((it["ok"], it["stale"], it["error"]), (False, False, "계산할 자료가 모자람"))
            self.assertNotIn("values", it)
        self.assertNotIn("123456", json.dumps(data))
        good = of.build(of.window(s["days"], TODAY, dgs), None, None, {}, NOW)
        W["stale"] = True
        with contextlib.redirect_stderr(io.StringIO()):
            stale = of.build(W, None, None, good["items"], NOW + datetime.timedelta(days=9))["items"]["level"]
        self.assertEqual((stale["stale"], stale["values"]), (True, good["items"]["level"]["values"]))   # 직전 값으로

    def test_stale_window_keeps_numbers_with_reason_and_since(self):
        s, dgs = held_store(end=D(2026, 11, 6))
        data = of.build(of.window(s["days"], TODAY, dgs), None, None, {}, NOW)
        lv = data["items"]["level"]
        self.assertEqual((lv["ok"], lv["stale"], lv["error"], lv["failed_since"], lv["date"]),
                         (False, True, "새 날 자료가 들어오지 않음", "2026-11-16", "2026-11-06"))
        later = of.build(of.window(s["days"], D(2026, 11, 18), dgs), "fetch", None, data["items"],
                         NOW + datetime.timedelta(days=2))["items"]["level"]
        self.assertEqual((later["error"], later["failed_since"]), ("수신 실패", "2026-11-16"))   # 처음 실패한 날이 이어진다
        s2, dgs2 = held_store()
        fresh = of.build(of.window(s2["days"], TODAY, dgs2), None, None, data["items"], NOW)["items"]["level"]
        self.assertEqual((fresh["ok"], fresh["failed_since"]), (True, None))

    def test_no_window_reasons(self):
        for why, run, want in (("none", None, "받아 둔 자료 없음"), ("none", "fetch", "수신 실패"),
                               ("fred", "fetch", "국채 금리(FRED)를 받지 못함"), ("format", None, "계산할 자료가 모자람")):
            it = of.build(None, run, why, {}, NOW)["items"]["level"]
            self.assertEqual((it["ok"], it["stale"], it["error"]), (False, False, want), why)
            self.assertNotIn("values", it)


class MainTest(TempDir):
    def run_main(self, opener=None, now=NOW, args=(), clock=time.monotonic, fred=None):
        buf = io.StringIO()
        if fred is None:
            fred = fred_of(weekdays(D(2024, 9, 2), (now + datetime.timedelta(days=5)).date()))
        self.fred = fred
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            code = of.main(["--out", self.tmp, "--work", os.path.join(self.tmp, "work"), "--budget", "500", *args],
                           opener=opener, now=now, clock=clock, fred_load=fred)
        self.log = buf.getvalue()
        return code

    def saved(self, name=of.FILE):
        with open(os.path.join(self.tmp, name), encoding="utf-8") as f:
            return json.load(f)

    def raw(self, name):
        with open(os.path.join(self.tmp, name), encoding="utf-8") as f:
            return f.read()

    def days_with_rows(self, today=TODAY):
        return all_days(today, lambda d: day_rows(d, did="987654321"))

    def test_first_run_writes_both_files_and_keeps_only_medians(self):
        op = FakeOpener(self.days_with_rows())
        self.assertEqual(self.run_main(op), 0)
        data = self.saved()
        self.assertEqual(data["order"], ["level", "ten"])
        for key in data["order"]:
            it = data["items"][key]
            self.assertEqual((it["ok"], it["stale"], it["error"], it["date"], it["retrieved"]),
                             (True, False, None, "2026-11-13", "2026-11-16"))
            self.assertEqual(it["sources"][0], {"series": "CFTC_CUMULATIVE_RATES", "name": "DTCC Data Repository (U.S.) LLC",
                                                "licence": "cftc-part43-public-dissemination", "citation": of.CITATION})
            self.assertEqual([s["series"] for s in it["sources"][1:]], ["DGS2", "DGS5", "DGS10", "DGS30"])
            self.assertEqual(it["notices"], [of.COMPUTED_NOTICE, of.CAVEAT_NOTICE])
        self.assertEqual(data["items"]["level"]["line"], "~2026-11-13 5영업일 중앙값: 2년 +20 · 5년 +30 · 10년 +40 · 30년 +65bp")
        self.assertIn("13주 변화 0bp · 1년 범위 +40~+40bp", data["items"]["ten"]["line"])
        store = self.saved(of.STORE)
        self.assertEqual(store["days"]["2026-11-13"]["10"], {"n": 10, "med": 4.6, "q1": 4.5945, "q3": 4.6055})
        for name in (of.FILE, of.STORE):                                              # 원 행·식별자는 쓰지 않는다
            text = self.raw(name)
            for raw in ("987654321", "USD-SOFR-OIS", "NEWT", "TRAD", "T15:00", "7,654,321", "Dissemination", "Fixed rate",
                        "Effective", "Package", "0.045910", "2026-11-15"):
                self.assertNotIn(raw, text, (name, raw))
        self.assertEqual(sorted(os.listdir(self.tmp)), sorted([of.FILE, of.STORE]))     # FRED 캐시는 <work>/에만
        n = len(op.calls)
        self.assertEqual(self.run_main(op), 0)
        self.assertEqual(len(op.calls), n)                                             # 둘째 실행은 DTCC 요청 0번

    def test_next_day_fetches_one_day_and_prunes(self):
        self.run_main(FakeOpener(self.days_with_rows()))
        nxt = TODAY + datetime.timedelta(days=1)
        op2 = FakeOpener(self.days_with_rows(nxt))
        self.assertEqual(self.run_main(op2, now=NOW + datetime.timedelta(days=1)), 0)
        self.assertEqual([c[0][-14:-4] for c in op2.calls], ["2026_11_16"])
        store = self.saved(of.STORE)
        self.assertEqual(self.saved()["items"]["level"]["date"], "2026-11-16")
        self.assertEqual(set(store["days"]), {d.isoformat() for d in of.targets(nxt)})

    def test_connection_failure_with_held_days_keeps_fresh_numbers_and_exits_1(self):
        self.run_main(FakeOpener(self.days_with_rows()))
        nxt = TODAY + datetime.timedelta(days=1)
        days = self.days_with_rows(nxt)
        days[TODAY] = "boom"
        self.assertEqual(self.run_main(FakeOpener(days), now=NOW + datetime.timedelta(days=1)), 1)
        lv = self.saved()["items"]["level"]
        self.assertEqual((lv["ok"], lv["date"]), (True, "2026-11-13"))                 # 끝 날이 아직 7일 안
        self.assertEqual(lv["retrieved"], "2026-11-16")                                 # 받은 것 없는 실행은 받은 날을 옮기지 않는다
        self.assertIn("이번 갱신에서 받지 못한 날이 있다 · 수신 실패 — 다음 갱신에 이어 받는다.", lv["extra"])
        self.assertEqual(self.saved(of.STORE)["status"], {"date": "2026-11-17", "error": "fetch"})
        self.assertIn("::warning::국채–OIS 참고: 수신 실패", self.log)
        self.assertNotIn("bad.invalid", self.log)
        op = FakeOpener(self.days_with_rows(nxt))                                      # 같은 날 다시 — 건너뛴다
        self.assertEqual(self.run_main(op, now=NOW + datetime.timedelta(days=1, minutes=30)), 1)
        self.assertEqual(op.calls, [])
        self.assertEqual(self.run_main(op, now=NOW + datetime.timedelta(days=1, minutes=40), args=("--force",)), 0)
        lv = self.saved()["items"]["level"]
        self.assertEqual((lv["date"], lv["retrieved"]), ("2026-11-16", "2026-11-17"))  # 새 날을 받으면 그날로

    def test_fred_failures(self):
        days = weekdays(D(2024, 9, 2), D(2026, 11, 20))
        f = fred_of(days)
        part = FakeFred(f.series, fail={"DGS30"})
        self.assertEqual(self.run_main(FakeOpener(self.days_with_rows()), fred=part), 0)    # 30년만 — 그 만기만 '—'
        lv = self.saved()["items"]["level"]
        self.assertTrue(lv["ok"])
        self.assertIn("30년 —bp", lv["line"])
        self.assertEqual(lv["values"]["fred_missing"], [30])
        self.assertIn("국채 금리(FRED)를 받지 못한 시리즈 DGS30", self.log)
        first = self.saved()
        ten = FakeFred(f.series, fail={"DGS10"})                                         # 10년을 못 받으면 창이 없다
        self.assertEqual(self.run_main(FakeOpener({}), now=NOW + datetime.timedelta(days=1), fred=ten), 1)
        lv = self.saved()["items"]["level"]
        self.assertEqual((lv["ok"], lv["stale"], lv["error"], lv["values"]),
                         (False, True, "국채 금리(FRED)를 받지 못함", first["items"]["level"]["values"]))   # 직전 숫자
        shutil.rmtree(self.tmp)
        os.makedirs(self.tmp)
        self.assertEqual(self.run_main(FakeOpener(self.days_with_rows()), fred=ten), 1)  # 처음부터 — 숫자 없음
        lv = self.saved()["items"]["level"]
        self.assertEqual((lv["ok"], lv["stale"], lv["error"]), (False, False, "국채 금리(FRED)를 받지 못함"))
        self.assertNotIn("values", lv)
        self.assertTrue(self.saved(of.STORE)["days"])                                    # DTCC 쪽은 받아 두었다

    def test_stale_store_and_broken_store_fall_back(self):
        self.run_main(FakeOpener(self.days_with_rows()))
        first = self.saved()
        later = NOW + datetime.timedelta(days=10)
        self.assertEqual(self.run_main(FakeOpener({}), now=later), 1)                   # 모두 403 — 주소가 바뀐 꼴
        lv = self.saved()["items"]["level"]
        self.assertEqual((lv["ok"], lv["stale"], lv["error"], lv["failed_since"], lv["date"]),
                         (False, True, of.REASONS["alarm"], "2026-11-26", "2026-11-13"))
        self.assertEqual(lv["values"]["last_error"], "alarm")
        self.assertEqual(lv["values"]["level"], first["items"]["level"]["values"]["level"])   # 숫자는 받아 둔 날 그대로
        with open(os.path.join(self.tmp, of.STORE), "w", encoding="utf-8") as f:       # 저장 파일이 깨졌다
            f.write("{broken")
        self.assertEqual(self.run_main(FakeOpener({}), now=later + datetime.timedelta(days=1)), 1)
        lv2 = self.saved()["items"]["level"]
        self.assertEqual((lv2["ok"], lv2["stale"], lv2["failed_since"], lv2["date"], lv2["values"]),
                         (False, True, "2026-11-26", "2026-11-13", lv["values"]))     # 직전 ois.json 그대로
        self.assertEqual((lv2["line"], lv2["error"]), (lv["line"], of.REASONS["alarm"]))
        self.assertEqual(self.saved(of.STORE)["days"], {})                             # 깨진 저장은 새로 시작한다

    def test_first_failure_without_anything_has_no_numbers(self):
        self.assertEqual(self.run_main(FakeOpener({d: "boom" for d in of.targets(TODAY)})), 1)
        lv = self.saved()["items"]["level"]
        self.assertEqual((lv["ok"], lv["stale"], lv["error"]), (False, False, "수신 실패"))
        self.assertNotIn("values", lv)
        self.assertNotIn("line", lv)
        self.assertEqual(lv["sources"][0]["citation"], of.CITATION)
        self.assertNotIn("citation", lv["sources"][1])                                 # 받은 날이 없으면 FRED 인용도 없다

    def test_older_window_is_not_taken(self):
        self.run_main(FakeOpener(self.days_with_rows()))
        data = self.saved()
        data["items"]["level"]["date"] = data["items"]["level"]["values"]["end"] = "2026-11-14"   # 직전이 더 늦은 날
        with open(os.path.join(self.tmp, of.FILE), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        self.run_main(FakeOpener(self.days_with_rows()))
        lv = self.saved()["items"]["level"]
        self.assertEqual((lv["ok"], lv["stale"], lv["error"], lv["date"]), (False, True, "받은 자료가 직전 자료보다 오래됨", "2026-11-14"))

    def test_same_numbers_keep_the_file_and_the_retrieved_date(self):
        self.run_main(FakeOpener(self.days_with_rows()))
        path = os.path.join(self.tmp, of.FILE)
        os.utime(path, (1, 1))
        self.run_main(FakeOpener(self.days_with_rows()), now=NOW + datetime.timedelta(minutes=5))
        self.assertEqual(os.stat(path).st_mtime, 1)
        os.utime(path, (1, 1))
        self.assertEqual(self.run_main(FakeOpener({}), now=NOW + datetime.timedelta(days=1), args=("--offline",)), 0)
        self.assertEqual(os.stat(path).st_mtime, 1)                                     # 새 날이 없으면 그대로
        lv = self.saved()["items"]["level"]
        self.assertEqual((lv["ok"], lv["date"], lv["retrieved"]), (True, "2026-11-13", "2026-11-16"))   # 처음 받은 날

    def test_a_malformed_previous_file_is_not_carried(self):
        self.run_main(FakeOpener(self.days_with_rows()))
        data = self.saved()
        for key, mutate in (("level", lambda v: v["level"].update({"10": 987654.0})),
                            ("ten", lambda v: v.update(raw="USD-SOFR-OIS Compound"))):
            mutate(data["items"][key]["values"])
        with open(os.path.join(self.tmp, of.FILE), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        with open(os.path.join(self.tmp, of.STORE), "w", encoding="utf-8") as f:     # 저장 파일도 깨졌다
            f.write("{broken")
        self.assertEqual(self.run_main(FakeOpener({}), now=NOW + datetime.timedelta(days=1)), 1)
        text = self.raw(of.FILE)
        for key in ("level", "ten"):
            it = self.saved()["items"][key]
            self.assertEqual((it["ok"], it["stale"]), (False, False))
            self.assertNotIn("values", it)
        self.assertNotIn("987654", text)
        self.assertNotIn("USD-SOFR", text)

    def test_offline_reads_the_store_without_writing_it(self):
        self.run_main(FakeOpener(self.days_with_rows()))
        store = os.path.join(self.tmp, of.STORE)
        os.utime(store, (1, 1))
        os.remove(os.path.join(self.tmp, of.FILE))
        op = FakeOpener({})
        self.assertEqual(self.run_main(op, now=NOW + datetime.timedelta(days=1), args=("--offline",)), 0)
        self.assertEqual((op.calls, os.stat(store).st_mtime), ([], 1))
        self.assertTrue(self.saved()["items"]["level"]["ok"])
        self.assertTrue(all(t is not None for _, t in self.fred.calls))
        before = self.raw(of.STORE)                                                    # 두 달 뒤 — 지울 날이 생겨도 쓰지 않는다
        self.assertEqual(self.run_main(op, now=NOW + datetime.timedelta(days=60), args=("--offline",)), 1)
        self.assertEqual((op.calls, self.raw(of.STORE), os.stat(store).st_mtime), ([], before, 1))

    def test_budget_runs_out_and_the_next_run_continues(self):
        clock = FakeClock()
        op = FakeOpener(self.days_with_rows(), clock=clock, cost=1)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            code = of.main(["--out", self.tmp, "--work", os.path.join(self.tmp, "work"), "--budget", "5"], opener=op, now=NOW,
                           clock=clock, fred_load=fred_of(weekdays(D(2024, 9, 2), D(2026, 11, 20))))
        self.assertEqual(code, 0)
        self.assertEqual(len(self.saved(of.STORE)["days"]), 5)
        self.assertIn(f"못 받은 날 {len(of.targets(TODAY)) - 5}일", buf.getvalue())
        self.assertIn("2년 +20 · 5년 +30 · 10년 +40 · 30년 +65bp", self.saved()["items"]["level"]["line"])   # 새 날부터라 수준은 첫 실행에
        op2 = FakeOpener(self.days_with_rows())
        self.run_main(op2, now=NOW + datetime.timedelta(minutes=10))
        self.assertEqual(len(op2.calls), len(of.targets(TODAY)) - 5)

    def test_write_failure_exits_1_and_the_write_is_atomic(self):
        self.run_main(FakeOpener(self.days_with_rows()))
        before = self.raw(of.FILE)
        real = cd.os.replace
        def boom(*a):
            raise OSError("disk")
        cd.os.replace = boom
        try:
            self.assertEqual(self.run_main(FakeOpener(self.days_with_rows(TODAY + datetime.timedelta(days=1))),
                                           now=NOW + datetime.timedelta(days=1)), 1)
        finally:
            cd.os.replace = real
        self.assertEqual(self.raw(of.FILE), before)
        self.assertEqual(sorted(os.listdir(self.tmp)), sorted([of.FILE, of.STORE]))   # .tmp가 남지 않는다

    def test_every_string_is_fixed_text_without_verdict_words(self):
        self.run_main(FakeOpener(self.days_with_rows()))
        days = self.days_with_rows(TODAY + datetime.timedelta(days=1))
        days[TODAY] = "http500"
        days[D(2026, 10, 1)] = "boom"
        self.run_main(FakeOpener(days), now=NOW + datetime.timedelta(days=1),
                      fred=FakeFred(fred_of(weekdays(D(2024, 9, 2), D(2026, 11, 20))).series, fail={"DGS5"}))
        self.run_main(FakeOpener({}), now=NOW + datetime.timedelta(days=12))
        for name in (of.FILE, of.STORE):
            dump = self.raw(name)
            for word in list(FORBIDDEN_TEXT) + list(VERDICT):
                self.assertNotIn(word, dump, (name, word))
            hosts = set(re.findall(r"https?://([^/\"\s]+)", dump))
            self.assertLessEqual(hosts, {"fred.stlouisfed.org"} if name == of.FILE else set(), name)   # FRED 주소뿐
            self.assertNotIn("bad.invalid", dump)
            self.assertNotIn("URLError", dump)
            self.assertNotIn("RuntimeError", dump)
        errors = {it.get("error") for it in self.saved()["items"].values()} - {None}
        self.assertLessEqual(errors, set(of.REASONS.values()))
        nested = re.compile(r"\([^()]*\(")
        for t in re.findall(r'"((?:[^"\\]|\\.)*)"', self.raw(of.FILE)):
            self.assertIsNone(nested.search(t), t)
        self.assertNotIn("bad.invalid", self.log)


class LicenceTest(unittest.TestCase):
    def test_citation_and_licence_are_fixed(self):
        self.assertEqual(of.CITATION, "Source: DTCC Data Repository (U.S.) LLC, CFTC swap data public dissemination "
                                      "(17 CFR Part 43); site calculations")
        self.assertEqual(of.LICENCE, {"CFTC_CUMULATIVE_RATES": "cftc-part43-public-dissemination", "DGS2": "public-domain",
                                      "DGS5": "public-domain", "DGS10": "public-domain", "DGS30": "public-domain"})
        self.assertEqual(of.citation("DGS10", "2026-11-15"),
                         "Board of Governors of the Federal Reserve System (US), Market Yield on U.S. Treasury Securities at "
                         "10-Year Constant Maturity, Quoted on an Investment Basis [DGS10], retrieved from FRED, Federal "
                         "Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/DGS10, November 15, 2026.")
        for part in ("DTCC Data Repository (U.S.)에 보고된 거래만", "중간값(mid)이 아니고", "다음 날 이후 취소된 거래"):
            self.assertIn(part, of.CAVEAT_NOTICE)
        with open(os.path.join(SCRIPTS, "ois_fetch.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("2026-11-15 운영자가 DTCC 이용 약관을 확인", src)                 # 공개하기로 한 결정의 기록
        self.assertNotRegex(src, r"(?i)\.(png|svg|jpe?g|gif)\b")                    # 로고·그림을 싣지 않는다
        self.assertNotRegex(src, r"[\w.+-]+@[\w-]+\.[\w.]+")                          # 이메일 주소가 없다
        self.assertNotIn("User-Agent", src)                                             # FRED에 머리글을 붙이지 않는다

    def test_constants_match_the_private_original(self):
        # 비공개 원본 ois_dtcc.py와 같은 값 — 실제 대조는 비공개 쪽 test_ois_dtcc.PairTest(형제 폴더가 있을 때)
        self.assertEqual((of.TENORS, of.TENOR_TOL, of.SPOT_DAYS, of.RATE_PCT, of.MIN_TRADES, of.LEVEL_N, of.LEVEL_SPAN,
                          of.WEEKS13, of.YEAR, of.STALE_DAYS, of.TARGET_DAYS, of.RETRY_DAYS, of.GIVE_UP, of.RECENT_ALARM,
                          of.ALARM_DAYS),
                         ((2, 5, 10, 30), 0.03, 5, (0.05, 15.0), 10, 5, 14, 91, 364, 7, 400, 3, 3, 10, 2))
        self.assertEqual(of.DGS, {2: "DGS2", 5: "DGS5", 10: "DGS10", 30: "DGS30"})
        self.assertLessEqual(of.BUDGET + of.FRED_BUDGET, 100)                          # 워크플로 단계 2분 안


class StaticTest(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
            return f.read()

    def test_workflow_fetches_without_failing_the_run(self):
        wf = self.read(".github", "workflows", "daily.yml")
        self.assertTrue("id: ois\n" in wf, "daily.yml에 국채–OIS 단계(id: ois) 없음")
        step = wf[wf.index("id: ois\n"):]
        self.assertIn("continue-on-error: true", step[:200])
        self.assertIn("timeout-minutes: 2", step[:200])
        self.assertIn("python scripts/ois_fetch.py", step[:300])
        self.assertLess(wf.index("id: cds\n"), wf.index("id: ois\n"))                  # 같은 DTCC 버킷의 CDS 바로 뒤
        self.assertLess(wf.index("id: ois\n"), wf.index("공개 전 검사(새 산출물 포함)"))
        self.assertLess(wf.index("id: ois\n"), wf.index("git add data"))
        self.assertNotIn("ois", wf[wf.index("\n  alert:"):])                    # 실패해도 알림을 띄우지 않는다
        self.assertIn("node --test scripts/test_ois_render.cjs", wf[wf.index("\n  check:"):wf.index("\n  update:")])

    def test_page_wires_the_card_after_the_term_premium_card(self):
        page = self.read("site", "index.html")
        for snippet in ('getJson("data/ois.json")', '<script src="ois.js"></script>', "window.OisCard.render(",
                        '<a href="data/ois.json">', '<a href="data/ois_days.json">'):
            self.assertTrue(snippet in page, f"index.html에 {snippet} 없음")
        lines = page.splitlines()
        i = next(i for i, l in enumerate(lines) if 'id:"tp-slot"' in l)
        self.assertIn('id:"ois-slot"', lines[i + 1])                                    # 기간 프리미엄 모형 대조 바로 뒤
        self.assertIn('g.id === "rates" ? el("div", {id:"ois-slot", class:"oil-slot"})', page)
        self.assertLess(page.index('<script src="tp.js"></script>'), page.index('<script src="ois.js"></script>'))

    def test_readme_counts_and_section(self):
        readme = self.read("README.md")
        m = re.search(r"\*\*아침 쪽 Python 테스트 (\d+)개 \+ node 테스트 (\d+)개\*\*\((.*?)\)와 \*\*저녁판", readme)
        py_part, node_part = m.group(3).split(" / node: ")
        mine = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()
        self.assertTrue(re.search(rf"(^|· )국채–OIS 참고 {mine}( ·|$)", py_part), f"README에 '국채–OIS 참고 {mine}' 없음")
        cjs = len(re.findall(r"^test\(", self.read("scripts", "test_ois_render.cjs"), flags=re.M))
        self.assertTrue(re.search(rf"(^|· )국채–OIS 카드 그리기 {cjs}( ·|$)", node_part), f"README에 '국채–OIS 카드 그리기 {cjs}' 없음")
        self.assertIn("## 참고: 국채–OIS 스프레드", readme)
        self.assertIn("python -X utf8 scripts/test_ois_fetch.py", readme)
        self.assertIn("node --test scripts/test_ois_render.cjs", readme)
        self.assertIn("python -X utf8 scripts/ois_fetch.py --out", readme)
        self.assertIn(of.CITATION, readme)
        self.assertIn("cftc-part43-public-dissemination", readme)
        self.assertIn("2026-11-15 운영자가 DTCC 이용 약관을 확인", readme)

    def test_screen_script_matches_the_file_and_writes_text_only(self):
        js = self.read("site", "ois.js")
        card = re.findall(r'"(\w+)"', js[js.index("const CARD = ["):].split("]")[0])
        self.assertEqual(card, of.ORDER)
        reasons = re.findall(r'"([^"]+)"', js[js.index("const REASONS = ["):].split("];")[0])
        self.assertEqual(reasons, list(of.REASONS.values()))
        fred = re.findall(r'"(\w+)"', js[js.index("const FRED = ["):].split("]")[0])
        self.assertEqual(fred, [of.DGS[t] for t in of.TENORS])
        body = js[js.index("const SOURCE = "):].split(";\n", 1)[0]
        self.assertEqual("".join(re.findall(r'"([^"]*)"', body)), of.CITATION)
        self.assertIn('const LABEL = "참고 — 예측 아님";', js)
        self.assertIn('el("p", { class: "source-link" }, SOURCE)', js)                  # 출처는 늘 함께
        for tok in ("innerHTML", "outerHTML", "insertAdjacentHTML", "createElement", "fetch(", "eval(", "<img", "src="):
            self.assertNotIn(tok, js)
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        for word in list(FORBIDDEN_TEXT) + list(VERDICT):
            self.assertNotIn(word, code, word)


if __name__ == "__main__":
    unittest.main(verbosity=1)
