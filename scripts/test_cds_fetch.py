#!/usr/bin/env python3
"""단일종목 CDS 참고 자료(cds_fetch) 테스트 — 세는 법(비공개 원본 cds_dtcc와 같은 경우들), 받기·실패 종류, 받아 둔 날(저장
파일)과 창, 칸·직전 값 이어 싣기, 이용 조건·출처, 문구 원칙(판정 낱말 없음·원격 글 없음), 화면·워크플로 연결.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — 가짜 urlopen(메모리 zip)·가짜 시계·임시 폴더. 행과 숫자는 모두 지어낸 것이다(실제 DTCC 행이 아니다).
"""
import os, io, re, sys, csv, json, time, socket, shutil, zipfile, datetime, tempfile, unittest, contextlib, urllib.error

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import cds_fetch as cd
from test_render_public import FORBIDDEN_TEXT

REPO = os.path.dirname(SCRIPTS)
D = datetime.date
TODAY = D(2026, 10, 28)
NOW = datetime.datetime(2026, 10, 28, 22, 17, tzinfo=datetime.timezone.utc)
VERDICT = ("판정", "충족", "신호", "경보", "전망", "매수", "매도", "⚠", "강세", "약세", "호재", "악재", "우려", "부담",
           "상승", "하락", "→")
COLS = ["Dissemination Identifier", "Original Dissemination Identifier", "Action type", "Event type", "Underlier ID source-Leg 1",
        "Execution Timestamp", "Expiration Date", "Notional amount-Leg 1", "Fixed rate-Leg 1", "Spread-Leg 1",
        "Spread notation-Leg 1", "Other payment amount", "Underlier ID-Leg 1", "Underlying Asset Name", "UPI FISN", "UPI Underlier Name"]
_ids = iter(range(10 ** 6, 10 ** 7))


def row(name="ORACLE CORPORATION", day=D(2026, 10, 27), t="15:00:00", action="NEWT", event="TRAD", spread="",
        exp=None, notional="5,000,000+", upfront="", fisn="NA/CDS Corp SN Sr", uid=None, did=None, odid="", upi="",
        notation="3", idsrc=""):
    return {"Dissemination Identifier": did or str(next(_ids)), "Original Dissemination Identifier": odid,
            "Action type": action, "Event type": event, "Execution Timestamp": f"{day.isoformat()}T{t}Z",
            "Expiration Date": (exp or cd.five_year(day)).isoformat() if not isinstance(exp, str) else exp,
            "Notional amount-Leg 1": notional, "Fixed rate-Leg 1": "0.01", "Spread-Leg 1": spread,
            "Spread notation-Leg 1": notation if spread else "",
            "Other payment amount": upfront, "Underlier ID-Leg 1": uid or ("ID-" + name[:6]),
            "Underlying Asset Name": name, "UPI FISN": fisn, "UPI Underlier Name": upi, "Underlier ID source-Leg 1": idsrc}


def zip_of_cols(rows, cols, name="SEC_CUMULATIVE_CREDITS.csv"):
    text = io.StringIO()
    w = csv.DictWriter(text, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(name, "﻿" + text.getvalue())
    return buf.getvalue()


def zip_of(rows):
    return zip_of_cols(rows, COLS)


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
            return Resp(zip_of_cols([{"x": "1"}], ["x"]))
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


def all_days(today=TODAY, rows_for=lambda d: [row(day=d, spread="0.0300")]):
    return {d: rows_for(d) for d in cd.targets(today)}


def zero_day():
    return {k: {"new": 0, "q": 0, "med": None} for k in cd.KEYS}


def put(store, day, names):
    base = zero_day()
    base.update(names)
    store["days"][day.isoformat()] = base


class TempDir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)


# ---------- 하루 파일 → 이름별 셈 (비공개 원본과 같은 경우들) ----------

class SummarizeTest(unittest.TestCase):
    def test_standard_five_year_rolls_on_march_and_september_20(self):
        self.assertEqual(cd.five_year(D(2026, 3, 19)), D(2030, 12, 20))
        self.assertEqual(cd.five_year(D(2026, 3, 20)), D(2031, 6, 20))
        self.assertEqual(cd.five_year(D(2026, 9, 19)), D(2031, 6, 20))
        self.assertEqual(cd.five_year(D(2026, 9, 20)), D(2031, 12, 20))
        self.assertEqual(cd.five_year(D(2026, 12, 31)), D(2031, 12, 20))

    def test_names_match_the_messy_spellings_and_not_neighbours(self):
        cases = {"Oracle Cop": "oracle", "ORACLE CORPORATION": "oracle", "COREWEAVE;INC.": "coreweave",
                 "COREWEAVE INC 9.99 1Dec39": "coreweave", "Meta Platforms, Inc.": "meta", "FACEBOOK INC": "meta",
                 "Amazon.com, Inc.": "amazon", "Alphabet Inc.": "alphabet", "Microsoft Corporation": "microsoft",
                 "ADVANCED MICRO DEVICES INC": "amd", "Intel Corporation": "intel", "INTELSAT S.A.": None,
                 "Micron Technology, Inc.": "micron", "MICRONESIA FED": None, "Taiwan Semiconductor Mfg": "tsmc",
                 "NVIDIA CORP": "nvidia", "Broadcom Inc.": "broadcom", "Federative Republic of Brazil": None, "": None,
                 "Amentum (Amazon Holdco Inc)": None, "AMAZON.COM;INC.": "amazon"}
        for name, want in cases.items():
            self.assertEqual(cd.name_of({"Underlying Asset Name": name}), want, name)
        self.assertEqual(cd.name_of({"Underlying Asset Name": "", "UPI Underlier Name": "Oracle Corp"}), "oracle")
        tickers = {"ORCL CDS USD SR 5Y D14": "oracle", "AVGO CDS USD SR 5Y D14": "broadcom", "GOOGL CDS USD SR 5Y D14": "alphabet",
                   "META CDS USD SR 5Y D14": "meta", "MSFT CDS USD SR 5Y D14": "microsoft", "AMZN CDS USD SR 5Y D14": "amazon",
                   "AMD CDS USD SR 5Y D14": "amd", "ADVANCED CDS USD SR 5Y D14": "amd", "INTC CDS USD SR 5Y D14": "intel",
                   "NVDA CDS USD SR 5Y D14": "nvidia", "MU CDS USD SR 5Y D14": "micron", "TSMC LTD": "tsmc",
                   "CRWV CDS USD SR 5Y D14": "coreweave", "IBM CDS USD SR 5Y D14": None, "METAL CO CDS": None,
                   "MUFG CDS USD SR": None}
        for name, want in tickers.items():
            self.assertEqual(cd.name_of({"Underlying Asset Name": name, "UPI Underlier Name": "No name obtainable"}), want, name)

    def test_same_twelve_names_as_the_private_original(self):
        self.assertEqual(cd.KEYS, ["oracle", "meta", "amazon", "alphabet", "microsoft", "coreweave", "broadcom", "nvidia",
                                   "amd", "intel", "micron", "tsmc"])
        self.assertEqual([cd.LABEL[k] for k in cd.KEYS], ["오라클", "메타", "아마존", "알파벳", "MS", "코어위브", "브로드컴",
                                                         "엔비디아", "AMD", "인텔", "마이크론", "TSMC"])

    def test_counts_new_single_name_trades_and_median_five_year_quotes(self):
        day = D(2026, 10, 27)
        rows = [row(spread="0.0300", t="10:00:01"), row(spread="0.0310", t="10:00:02"), row(spread="0.0330", t="10:00:03"),
                row(spread="0.0240", exp=D(2029, 12, 20), t="10:00:04"),     # 5년이 아닌 만기 — 건수만
                row(upfront="111111.11", notional="3,000,000", t="10:00:05"),   # 선지급금만 — 건수만
                row(action="MODI", spread="0.0500", t="10:00:06"), row(action="CORR", event="", t="10:00:07"),
                row(event="NOVA", t="10:00:08"),
                row(fisn="NA/CDS Corp Basket", t="10:00:09"), row(fisn="NA/Cr Sw SN TRtn Corp Cs", t="10:00:10"),
                row(name="NVIDIA CORP", spread="0.0080", t="10:00:11"),
                row(name="Microsoft Corporation", spread="101", t="10:00:12"),  # 표기 3인데 bp로 적은 값 — 101bp
                row(name="Microsoft Corporation", spread="0.0001", t="10:00:13"),  # 1bp — QUOTE_BP 밖, 건수만
                row(name="Microsoft Corporation", spread="55", notation="4", t="10:00:15"),   # 표기 4 = bp
                row(name="Federative Republic of Brazil", spread="0.0124", fisn="NA/CDS Sov SN Sr", t="10:00:14")]
        out = cd.summarize(rows, day)
        self.assertEqual(list(out), cd.KEYS)
        self.assertEqual(out["oracle"], {"new": 5, "q": 3, "med": 310.0})
        self.assertEqual(out["nvidia"], {"new": 1, "q": 1, "med": 80.0})
        self.assertEqual(out["microsoft"], {"new": 3, "q": 2, "med": 78.0})     # [55, 101]
        self.assertEqual(out["micron"], {"new": 0, "q": 0, "med": None})
        self.assertTrue(all(cd.day_ok(out) for _ in [0]))

    def test_late_reports_future_dates_and_same_file_cancels_are_dropped(self):
        day = D(2026, 10, 27)
        cancelled = row(spread="0.0900", did="555", t="11:00:00")
        rows = [row(day=D(2026, 10, 24), spread="0.0300", t="11:00:01"),          # 3일 전 체결 — 센다
                row(day=D(2026, 10, 23), spread="0.0400", t="11:00:02"),          # 4일 전 — 늦은 보고
                row(day=D(2006, 2, 1), t="11:00:03"),                             # 옛 거래 일괄 보고
                row(day=D(2026, 10, 28), t="11:00:04"),                           # 파일 날짜 뒤
                cancelled, row(action="EROR", event="", odid="555", did="556", t="11:00:05")]
        self.assertEqual(cd.summarize(rows, day)["oracle"], {"new": 1, "q": 1, "med": 300.0})

    def test_quote_units(self):
        self.assertEqual(cd._quote_bp("0.0249", "3"), 249.0)
        self.assertEqual(cd._quote_bp("0.0249", ""), 249.0)
        self.assertEqual(cd._quote_bp("77", "3"), 77.0)
        self.assertEqual(cd._quote_bp("119", "4"), 119.0)
        self.assertIsNone(cd._quote_bp("0.0249", "4"))               # 표기 4(bp)에 소수 — 0.02bp, 범위 밖
        self.assertIsNone(cd._quote_bp("1.5", "3"))
        self.assertIsNone(cd._quote_bp("5000", "4"))
        self.assertIsNone(cd._quote_bp("abc"))
        self.assertEqual((cd._quote_bp("5", "4"), cd._quote_bp("3000", "4")), (5.0, 3000.0))   # 범위 끝은 들어간다

    def test_red_code_names_rows_without_a_name(self):
        day = D(2026, 10, 27)
        rows = [row(name="ORACLE CORPORATION", uid="FAKE01", idsrc="REDID", t="09:00:00"),
                row(name="", upi="SR NT", uid="FAKE01AA0", idsrc="REDID", t="09:00:01", spread="0.0300"),
                row(name="", upi="No name obtainable", uid="ZZZZZZ", idsrc="REDID", t="09:00:02")]
        out = cd.summarize(rows, day)
        self.assertEqual((out["oracle"]["new"], out["oracle"]["q"]), (2, 1))
        both = [row(name="ORACLE CORPORATION", uid="AAAAAA", idsrc="REDID", t="10:00:00"),
                row(name="Broadcom Inc.", uid="AAAAAA", idsrc="REDID", t="10:00:01"),
                row(name="", upi="NT", uid="AAAAAA", idsrc="REDID", t="10:00:02")]      # 두 이름에 쓰인 코드 — 쓰지 않는다
        out = cd.summarize(both, day)
        self.assertEqual((out["oracle"]["new"], out["broadcom"]["new"]), (1, 1))

    def test_portfolio_second_with_many_names_is_dropped_and_baskets_count(self):
        day = D(2026, 10, 16)
        names = ["ORACLE CORPORATION", "Taiwan Semiconductor Mfg", "Broadcom Inc."] + [f"OTHER CO {i}" for i in range(7)]
        rows = [row(name=n, day=day, uid=f"P{i}", t="07:07:07", notional=f"{i + 1},000,000", upfront=f"{100 + i}.0",
                    spread="0.0300") for i, n in enumerate(names)]
        rows.append(row(name="ORACLE CORPORATION", day=day, uid="P0", t="07:07:08", spread="0.0310"))
        out = cd.summarize(rows, day)
        self.assertEqual((out["oracle"]["new"], out["oracle"]["q"], out["tsmc"]["new"]), (1, 1, 0))
        basket = [row(name=n, day=day, uid=f"Q{i}", t="09:00:00", upfront=f"{i + 1}.0")      # 같은 초에 아홉 곳 — 센다
                  for i, n in enumerate(["ORACLE CORPORATION", "Broadcom Inc."] + [f"OTHER CO {i}" for i in range(7)])]
        out = cd.summarize(basket, day)
        self.assertEqual((out["oracle"]["new"], out["broadcom"]["new"]), (1, 1))

    def test_placeholder_ids_do_not_merge_different_names(self):
        day = D(2026, 10, 16)
        names = ["ORACLE CORPORATION", "Meta Platforms, Inc.", "Amazon.com, Inc."] + [f"OTHER CO {i}" for i in range(9)]
        rows = [row(name=n, day=day, uid="XSSNRREFOBL0", t="14:14:14", notional=f"{i + 1},000,000", upfront=f"{i}.5")
                for i, n in enumerate(names)]
        out = cd.summarize(rows, day)
        self.assertEqual((out["oracle"]["new"], out["meta"]["new"], out["amazon"]["new"]), (0, 0, 0))
        self.assertEqual(cd.entity_of({"Underlying Asset Name": "EXAMPLE WIDGETS INC 9.99 15Feb39"}), "EXAMPLE WIDGETS INC")
        self.assertEqual(cd.entity_of({"Underlying Asset Name": "IBM CDS USD SR 5Y D14"}), "IBM")
        self.assertEqual(cd.entity_of({"Underlying Asset Name": "", "UPI Underlier Name": "No name obtainable",
                                       "Underlier ID-Leg 1": "XSSNRREFOBL0"}), "")
        self.assertEqual(cd.entity_of({"Underlying Asset Name": "", "Underlier ID-Leg 1": "XS0000000009"}), "XS0000000009")

    def test_one_name_reported_with_red_and_isin_is_one_entity(self):
        day = D(2026, 7, 6)
        same = dict(day=day, t="20:20:20", notional="5,000,000+", upfront="1111111.00000")
        rows = [row(name="ADVANCED MICRO DEVICES INC", uid="FAKE02", spread="0.0123", exp=D(2031, 6, 20), **same),
                row(name="ADVANCED MICRO DEVICES INC", uid="XS0000000009", **same)]
        out = cd.summarize(rows, day)
        self.assertEqual((out["amd"]["new"], out["amd"]["q"], out["amd"]["med"]), (2, 1, 123.0))

    def test_bundle_rows_on_many_names_are_dropped(self):
        day = D(2026, 10, 27)
        same = dict(t="17:17:17", notional="1,000,000", upfront="22222.22")
        rows = [row(name="ADVANCED MICRO DEVICES INC", uid="A1", **same), row(name="NETFLIX INC", uid="N1", **same),
                row(name="INTERNATIONAL BUSINESS MACHINES", uid="I1", **same),
                row(name="ADVANCED MICRO DEVICES INC", uid="A1", t="17:17:18", notional="1,000,000", upfront="9.99")]
        self.assertEqual(cd.summarize(rows, day)["amd"]["new"], 1)
        twice = [row(name="NVIDIA CORP", uid="V1", **same), row(name="NVIDIA CORP", uid="V1", **same)]
        self.assertEqual(cd.summarize(twice, day)["nvidia"]["new"], 2)
        pair = [row(name="NVIDIA CORP", uid="V1", **same), row(name="NETFLIX INC", uid="N1", **same)]   # 두 실체면 묶음
        self.assertEqual(cd.summarize(pair, day)["nvidia"]["new"], 0)


# ---------- 받기 ----------

class FetchTest(unittest.TestCase):
    def test_parse_zip_reads_the_first_csv_in_memory(self):
        rows = cd.parse_zip(zip_of([row(spread="0.0249")]))
        self.assertEqual(rows[0]["Spread-Leg 1"], "0.0249")
        self.assertTrue(rows[0]["Dissemination Identifier"][:1].isdigit())        # BOM이 머리글에 남지 않는다
        with self.assertRaises(cd.FetchError):
            cd.parse_zip(b"not a zip")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("readme.txt", "x")
        with self.assertRaises(cd.FetchError):
            cd.parse_zip(buf.getvalue())

    def test_fetch_absent_file_is_none_and_other_failures_raise(self):
        day = D(2026, 10, 27)
        op = FakeOpener({day: [row()], D(2026, 10, 26): "http500", D(2026, 10, 25): "boom"})
        self.assertEqual(len(cd.fetch(day, 5, op)), 1)
        self.assertEqual(op.calls[0][0], "https://kgc0418-tdw-data-0.s3.amazonaws.com/sec/eod/"
                                         "SEC_CUMULATIVE_CREDITS_2026_10_27.zip")
        self.assertEqual(op.calls[0][1], 5)
        self.assertIsNone(cd.fetch(D(2026, 10, 24), 5, op))
        kinds = []
        for d in (D(2026, 10, 26), D(2026, 10, 25)):
            with self.assertRaises(cd.FetchError) as c:
                cd.fetch(d, 5, op)
            kinds.append(c.exception.kind)
            self.assertNotIn("bad.invalid", str(c.exception))                   # 원격 글을 담지 않는다
        self.assertEqual(kinds, ["day", "net"])

    def test_timeouts_corrupt_zips_and_the_deadline(self):
        day = D(2026, 10, 27)
        with self.assertRaises(cd.FetchError) as c:
            cd.fetch(day, 5, FakeOpener({day: "slow"}))
        self.assertEqual(c.exception.kind, "timeout")
        with self.assertRaises(cd.FetchError) as c:
            cd.fetch(day, 5, FakeOpener({day: "badzip"}))
        self.assertEqual(c.exception.kind, "day")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("a.csv", "x," * 5000)
        raw = bytearray(buf.getvalue())
        raw[60:80] = b"\xff" * 20
        with self.assertRaises(cd.FetchError):
            cd.parse_zip(bytes(raw))
        clock = FakeClock()
        old = cd.CHUNK
        cd.CHUNK = 64
        try:
            with self.assertRaises(cd.FetchError) as c:
                cd.fetch(day, 5, FakeOpener({day: [row()] * 30}, clock=clock, step=1), deadline=3, clock=clock)
        finally:
            cd.CHUNK = old
        self.assertEqual(c.exception.kind, "budget")

    def test_fetch_403_without_access_denied_is_an_error(self):
        def op(url, timeout=None):
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, io.BytesIO(b"proxy says no"))
        with self.assertRaises(cd.FetchError) as c:
            cd.fetch(D(2026, 10, 27), 5, op)
        self.assertEqual(c.exception.kind, "net")

    def test_header_case_and_spacing_changes_are_accepted(self):
        cols = [c.upper() if c == "Spread notation-Leg 1" else ("  " + c) if c == "UPI FISN" else c for c in COLS]
        r0 = row(spread="0.0300")
        rows = cd.parse_zip(zip_of_cols([{new: r0[old] for old, new in zip(COLS, cols)}], cols))
        self.assertEqual(rows[0]["Spread notation-Leg 1"], "3")
        self.assertEqual(cd.summarize(rows, D(2026, 10, 27))["oracle"], {"new": 1, "q": 1, "med": 300.0})

    def test_missing_columns_archived_days_and_odd_zips(self):
        day = D(2026, 10, 27)
        with self.assertRaises(cd.FetchError) as c:
            cd.fetch(day, 5, FakeOpener({day: "nocol"}))
        self.assertEqual(c.exception.kind, "day")
        self.assertIsNone(cd.fetch(day, 5, FakeOpener({day: "archived"})))
        raw = bytearray(zip_of([row()]))
        raw[8:10] = (9).to_bytes(2, "little")                                   # 압축 방식 9(Deflate64) — 지원하지 않음
        cen = raw.rfind(b"PK\x01\x02")
        raw[cen + 10:cen + 12] = (9).to_bytes(2, "little")
        with self.assertRaises(cd.FetchError) as c:
            cd.parse_zip(bytes(raw))
        self.assertEqual(c.exception.kind, "day")

    def test_read1_lets_the_deadline_bite_between_small_reads(self):
        class Drip(Resp):
            def read1(self, n=-1):
                return Resp.read(self, 16)
        clock = FakeClock()
        op = lambda url, timeout=None: Drip(zip_of([row()] * 30), clock, step=1)
        with self.assertRaises(cd.FetchError) as c:
            cd.fetch(D(2026, 10, 27), 5, op, deadline=5, clock=clock)
        self.assertEqual(c.exception.kind, "budget")
        self.assertLessEqual(clock.t, 7)

    def test_too_large_file_is_refused(self):
        old = cd.MAX_BYTES
        cd.MAX_BYTES = 10
        try:
            with self.assertRaises(cd.FetchError) as c:
                cd.fetch(D(2026, 10, 27), 5, FakeOpener({D(2026, 10, 27): [row()]}))
        finally:
            cd.MAX_BYTES = old
        self.assertEqual(c.exception.kind, "day")


# ---------- 받아 두기 ----------

class SyncTest(unittest.TestCase):
    N = cd.RECENT_DAYS + cd.YEAR_DAYS

    def setUp(self):
        self.store = cd.empty_store()

    def test_targets_are_recent_days_then_a_year_ago_newest_first(self):
        t = cd.targets(TODAY)
        self.assertEqual(len(t), self.N)
        self.assertEqual(t[0], D(2026, 10, 27))
        self.assertEqual(t[cd.RECENT_DAYS - 1], TODAY - datetime.timedelta(days=cd.RECENT_DAYS))
        self.assertEqual(t[cd.RECENT_DAYS], TODAY - datetime.timedelta(days=364))
        self.assertEqual(t[-1], TODAY - datetime.timedelta(days=364 + cd.YEAR_DAYS - 1))

    def test_fetches_missing_days_once(self):
        op = FakeOpener(all_days())
        r = cd.sync(self.store, TODAY, opener=op)
        self.assertEqual((r["fetched"], r["error"], r["missing"]), (self.N, None, 0))
        self.assertEqual([c[0][-14:-4] for c in op.calls[:2]], ["2026_10_27", "2026_10_26"])   # 새 날부터
        n = len(op.calls)
        r2 = cd.sync(self.store, TODAY, opener=op)
        self.assertEqual((r2["fetched"], len(op.calls)), (0, n))                       # 둘째 실행은 요청 0번
        self.assertEqual(self.store["days"]["2026-10-27"]["oracle"], {"new": 1, "q": 1, "med": 300.0})
        self.assertEqual(self.store["status"], {"date": "2026-10-28", "error": None})

    def test_budget_caps_each_request_and_stops(self):
        clock = FakeClock()
        op = FakeOpener(all_days(), clock=clock, cost=3)
        r = cd.sync(self.store, TODAY, budget=10, opener=op, clock=clock)
        self.assertEqual([t for _, t in op.calls], [10, 7, 4, 1])
        self.assertEqual((r["fetched"], r["missing"], r["error"]), (3, self.N - 3, None))
        r2 = cd.sync(self.store, TODAY, budget=0, opener=op)
        self.assertEqual((len(op.calls), r2["fetched"]), (4, 0))                       # 예산 0이면 요청하지 않는다

    def test_short_request_timeout_is_budget_not_failure(self):
        clock = FakeClock()
        op = FakeOpener(all_days(), clock=clock, cost=3, need=5)
        r = cd.sync(self.store, TODAY, budget=10, opener=op, clock=clock)
        self.assertEqual((r["fetched"], r["error"], r["missing"]), (2, None, self.N - 2))
        r2 = cd.sync(self.store, TODAY, opener=FakeOpener(all_days()))
        self.assertFalse(r2["skipped"])                                             # 같은 날 다음 실행이 이어 받는다
        self.assertEqual(r2["fetched"], self.N - 2)

    def test_full_timeout_is_a_failure_and_the_rest_of_the_day_is_skipped(self):
        days = all_days()
        days[D(2026, 10, 27)] = "slow"
        r = cd.sync(self.store, TODAY, opener=FakeOpener(days))
        self.assertEqual(r["error"], "timeout")
        op = FakeOpener(all_days())
        r2 = cd.sync(self.store, TODAY, opener=op)
        self.assertEqual((r2["skipped"], r2["error"], len(op.calls)), (True, "timeout", 0))

    def test_one_bad_day_is_skipped_retried_daily_and_given_up(self):
        days = all_days()
        bad = D(2026, 10, 20)
        days[bad] = "http500"
        days[D(2026, 10, 12)] = "badzip"
        op = FakeOpener(days)
        r = cd.sync(self.store, TODAY, opener=op)
        self.assertEqual((r["fetched"], r["bad"], r["error"]), (self.N - 2, 2, None))
        n = len(op.calls)
        self.assertEqual(cd.sync(self.store, TODAY, opener=op)["fetched"], 0)
        self.assertEqual(len(op.calls), n)                                           # 같은 날은 다시 보지 않는다
        for i in (1, 2):
            nxt = TODAY + datetime.timedelta(days=i)
            op.days = {**all_days(nxt), bad: "http500", D(2026, 10, 12): "badzip"}
            self.assertEqual(cd.sync(self.store, nxt, opener=op)["bad"], 2, i)
        nxt = TODAY + datetime.timedelta(days=3)
        op.days = {**all_days(nxt), bad: [row(day=bad, spread="0.0300")]}          # 이제 받을 수 있게 되어도
        r = cd.sync(self.store, nxt, opener=op)
        self.assertEqual((r["bad"], r["gave_up"]), (0, 2))                           # 서로 다른 사흘 실패 — 그만 받는다
        self.assertNotIn(bad.isoformat(), self.store["days"])

    def test_hard_deadline_for_a_hanging_request(self):
        days = all_days()
        days[D(2026, 10, 27)] = "hang"
        t0 = time.monotonic()
        r = cd.sync(self.store, TODAY, budget=1.5, opener=FakeOpener(days))
        self.assertLess(time.monotonic() - t0, 3)
        self.assertEqual((r["fetched"], r["error"], r["missing"]), (0, None, self.N))

    def test_a_hang_given_the_full_timeout_is_a_failure(self):
        days = all_days()
        days[D(2026, 10, 27)] = "hang"
        old = cd.TIMEOUT
        cd.TIMEOUT = 1.5
        try:
            r = cd.sync(self.store, TODAY, budget=1.5, opener=FakeOpener(days))
        finally:
            cd.TIMEOUT = old
        self.assertEqual(r["error"], "timeout")
        self.assertTrue(cd.sync(self.store, TODAY, opener=FakeOpener(all_days()))["skipped"])

    def test_bad_columns_and_archived_days_are_per_day(self):
        days = all_days()
        days[D(2026, 10, 20)] = "nocol"
        days[D(2026, 10, 19)] = "archived"
        r = cd.sync(self.store, TODAY, opener=FakeOpener(days))
        self.assertEqual((r["bad"], r["absent"], r["error"]), (1, 1, None))
        self.assertNotIn("2026-10-20", self.store["days"])                         # 칸 없는 날을 0건으로 남기지 않는다
        self.assertEqual({k: v["why"] for k, v in self.store["tries"].items()}, {"2026-10-20": "bad", "2026-10-19": "absent"})

    def test_connection_failure_stops_next_day_retries_and_force(self):
        days = all_days()
        days[D(2026, 10, 25)] = "boom"
        r = cd.sync(self.store, TODAY, opener=FakeOpener(days))
        self.assertEqual((r["fetched"], r["error"]), (2, "fetch"))
        self.assertEqual(self.store["status"], {"date": "2026-10-28", "error": "fetch"})
        self.assertTrue(cd.sync(self.store, TODAY, opener=FakeOpener(all_days()))["skipped"])
        r3 = cd.sync(self.store, TODAY, opener=FakeOpener(all_days()), force=True)
        self.assertEqual((r3["skipped"], r3["error"], r3["fetched"]), (False, None, self.N - 2))
        s2 = cd.empty_store()
        cd.sync(s2, TODAY, opener=FakeOpener(days))
        self.assertFalse(cd.sync(s2, TODAY + datetime.timedelta(days=1), opener=FakeOpener(all_days()))["skipped"])

    def test_recent_absent_days_are_not_errors(self):
        days = all_days()
        for i in (1, 2, 3):
            days[TODAY - datetime.timedelta(days=i)] = "absent"
        r = cd.sync(self.store, TODAY, opener=FakeOpener(days))
        self.assertEqual((r["error"], r["fetched"], r["absent"]), (None, self.N - 3, 0))
        self.assertNotIn("2026-10-27", self.store["days"])
        cd.sync(self.store, TODAY + datetime.timedelta(days=1), opener=FakeOpener(all_days(TODAY + datetime.timedelta(days=1))))
        self.assertIn("2026-10-27", self.store["days"])                              # 다음 실행에 다시 본다

    def test_alarm_when_recent_days_fail_and_nothing_was_fetched(self):
        days = {d: "absent" for d in cd.targets(TODAY)}
        op = FakeOpener(days)
        r = cd.sync(self.store, TODAY, opener=op)
        self.assertEqual(len(op.calls), cd.RETRY_DAYS + cd.ALARM_DAYS)
        self.assertEqual(r["error"], "alarm")
        days = {d: "nocol" for d in cd.targets(TODAY)}
        self.assertEqual(cd.sync(cd.empty_store(), TODAY, opener=FakeOpener(days))["error"], "alarm")
        days = all_days()
        days[D(2026, 10, 20)] = days[D(2026, 10, 19)] = days[D(2026, 10, 18)] = "absent"   # 받은 것이 있으면 넘어간다
        r = cd.sync(cd.empty_store(), TODAY, opener=FakeOpener(days))
        self.assertEqual((r["error"], r["absent"], r["fetched"]), (None, 3, self.N - 3))

    def test_missing_year_ago_days_with_the_rest_held_are_not_an_alarm(self):
        days = all_days()
        for i in (3, 4, 5):
            days[TODAY - datetime.timedelta(days=364 + i)] = "absent"
        cd.sync(self.store, TODAY, opener=FakeOpener(days))
        for i in (1, 2):
            nxt = TODAY + datetime.timedelta(days=i)
            days2 = {**days, **{d: [row(day=d)] for d in cd.targets(nxt) if d not in days}}
            self.assertIsNone(cd.sync(self.store, nxt, opener=FakeOpener(days2))["error"], i)

    def test_never_raises(self):
        r = cd.sync({"days": None}, TODAY, opener=FakeOpener(all_days()))
        self.assertEqual(r["error"], "fetch")


# ---------- 창 ----------

class WindowTest(unittest.TestCase):
    def setUp(self):
        self.store = cd.empty_store()

    def test_no_days_is_none_and_today_is_not_read(self):
        self.assertIsNone(cd.window({}, TODAY))
        put(self.store, TODAY, {"oracle": {"new": 1, "q": 3, "med": 200.0}})
        self.assertIsNone(cd.window(self.store["days"], TODAY))

    def test_level_is_quote_weighted_median_and_spans_line_up(self):
        end = D(2026, 10, 27)
        for i in range(400):
            put(self.store, end - datetime.timedelta(days=i), {"oracle": {"new": 2, "q": 0, "med": None}})
        put(self.store, end, {"oracle": {"new": 5, "q": 1, "med": 340.0}})
        put(self.store, end - datetime.timedelta(days=13), {"oracle": {"new": 5, "q": 3, "med": 300.0}})   # 창 끝(14일째)
        put(self.store, end - datetime.timedelta(days=14), {"oracle": {"new": 5, "q": 9, "med": 900.0}})   # 창 밖
        put(self.store, end - datetime.timedelta(days=28), {"oracle": {"new": 2, "q": 4, "med": 250.0}})   # 4주 전 창 끝
        put(self.store, end - datetime.timedelta(days=364), {"oracle": {"new": 2, "q": 2, "med": 75.0}})
        put(self.store, end - datetime.timedelta(days=370), {"oracle": {"new": 2, "q": 1, "med": 70.0}})
        put(self.store, TODAY, {"oracle": {"new": 99, "q": 9, "med": 999.0}})                       # 오늘 날은 읽지 않는다
        w = cd.window(self.store["days"], TODAY)
        o = w["names"][0]
        self.assertEqual((o["key"], o["label"]), ("oracle", "오라클"))
        self.assertEqual((w["end"], w["from"], w["age"], w["stale"]), ("2026-10-27", "2026-09-30", 1, False))
        self.assertEqual((o["level"], o["q"]), (300.0, 4))                             # [340, 300, 300, 300] → 300
        self.assertEqual((o["prior"], o["prior_q"]), (250.0, 4))
        self.assertEqual((o["level_1y"], o["q_1y"]), (75.0, 3))                        # [70, 75, 75] → 75
        self.assertEqual(o["new"], 2 * 28 + 3 * 3)
        self.assertEqual(o["new_1y"], 2 * 28)
        self.assertEqual(w["cover"], {"level": 14, "prior": 14, "level_1y": 14, "count": 28, "count_1y": 28})

    def test_four_weeks_ago_is_exactly_28_days_back(self):
        end = D(2026, 10, 27)
        for i in range(60):
            put(self.store, end - datetime.timedelta(days=i), {})
        put(self.store, end, {"oracle": {"new": 3, "q": 3, "med": 300.0}})
        put(self.store, end - datetime.timedelta(days=27), {"oracle": {"new": 9, "q": 9, "med": 500.0}})   # 27일 전 — 창 밖
        put(self.store, end - datetime.timedelta(days=28), {"oracle": {"new": 3, "q": 3, "med": 250.0}})   # 4주 전 창 끝
        put(self.store, end - datetime.timedelta(days=41), {"oracle": {"new": 3, "q": 3, "med": 260.0}})   # 4주 전 창 처음
        put(self.store, end - datetime.timedelta(days=42), {"oracle": {"new": 9, "q": 9, "med": 900.0}})   # 42일 전 — 창 밖
        sp = cd.spans(end)["prior"]
        self.assertEqual((sp[0], sp[-1], len(sp)), (end - datetime.timedelta(days=28), end - datetime.timedelta(days=41), 14))
        o = cd.window(self.store["days"], TODAY)["names"][0]
        self.assertEqual((o["level"], o["prior"], o["prior_q"]), (300.0, 255.0, 6))    # 27일이면 500, 29일이면 900
        q = cd.build(cd.window(self.store["days"], TODAY), None, {}, NOW)["items"]["quotes"]
        self.assertIn("오라클 300bp (+45)", q["line"])
        self.assertEqual(q["table"]["rows"][0][:3], ["오라클", "300", "+45"])
        self.assertEqual(cd.PRIOR_GAP, 28)

    def test_too_few_quotes_and_partial_year_ago(self):
        end = D(2026, 10, 27)
        for i in range(20):
            put(self.store, end - datetime.timedelta(days=i), {})
        put(self.store, end, {"intel": {"new": 3, "q": 2, "med": 90.0}})
        put(self.store, end - datetime.timedelta(days=364), {"intel": {"new": 4, "q": 0, "med": None}})
        w = cd.window(self.store["days"], TODAY)
        it = w["names"][cd.KEYS.index("intel")]
        self.assertEqual((it["level"], it["q"], it["prior"], it["level_1y"]), (None, 2, None, None))
        self.assertIsNone(it["new_1y"])                                                # 1년 전 28일을 다 받지 않았다
        self.assertEqual((w["cover"]["count"], w["cover"]["count_1y"]), (20, 1))

    def test_age_and_staleness(self):
        end = D(2026, 9, 28)
        for i in range(40):
            put(self.store, end - datetime.timedelta(days=i), {"oracle": {"new": 1, "q": 3, "med": 200.0}})
        w = cd.window(self.store["days"], TODAY)
        self.assertEqual((w["end"], w["age"], w["stale"], w["cover"]["level"]), ("2026-09-28", 30, True, 14))
        self.assertEqual(cd.window(self.store["days"], end + datetime.timedelta(days=cd.STALE_DAYS))["stale"], False)
        self.assertEqual(cd.window(self.store["days"], end + datetime.timedelta(days=cd.STALE_DAYS + 1))["stale"], True)

    def test_prune_keeps_targets_and_the_days_the_window_uses(self):
        for i in range(1, 800):
            put(self.store, TODAY - datetime.timedelta(days=i), {})
        self.store["tries"] = {"2020-01-01": {"n": 1, "last": "2026-10-28", "why": "bad"},
                               "2026-10-20": {"n": 1, "last": "2026-10-28", "why": "bad"}}
        cd.prune(self.store, TODAY)
        keep = {d.isoformat() for d in cd.targets(TODAY)}
        self.assertEqual(set(self.store["days"]), keep | {d.isoformat() for ds in cd.spans(D(2026, 10, 27)).values() for d in ds})
        self.assertEqual(set(self.store["tries"]), {"2026-10-20"})
        old = cd.empty_store()                                                         # 수신이 멈춰 끝 날이 오래된 때
        end = TODAY - datetime.timedelta(days=30)
        for i in range(500):
            put(old, end - datetime.timedelta(days=i), {})
        cd.prune(old, TODAY)
        w = cd.window(old["days"], TODAY)
        self.assertEqual(w["cover"], {"level": 14, "prior": 14, "level_1y": 14, "count": 28, "count_1y": 28})
        self.assertLessEqual(len(old["days"]), 2 * (cd.RECENT_DAYS + cd.YEAR_DAYS))


# ---------- 저장 파일 ----------

class StoreTest(TempDir):
    def test_text_is_valid_json_one_day_per_line_and_round_trips(self):
        s = cd.empty_store()
        put(s, D(2026, 10, 27), {"oracle": {"new": 5, "q": 3, "med": 310.0}})
        put(s, D(2026, 10, 26), {})
        s["tries"] = {"2026-10-20": {"n": 1, "last": "2026-10-28", "why": "bad"}}
        s["status"] = {"date": "2026-10-28", "error": None}
        text = cd.store_text(s)
        js = json.loads(text)
        self.assertEqual(set(js), {"schema", "notice", "source", "names", "days", "tries", "status"})
        self.assertEqual(js["source"], cd.CITATION)
        lines = [l for l in text.splitlines() if l.startswith('"2026-')]
        self.assertEqual([l[1:11] for l in lines], ["2026-10-26", "2026-10-27"])         # 하루 한 줄, 날짜 차례
        with open(os.path.join(self.tmp, cd.STORE), "w", encoding="utf-8") as f:
            f.write(text)
        back = cd.load_store(self.tmp)
        self.assertEqual(back, s)
        e = cd.empty_store()
        self.assertEqual(json.loads(cd.store_text(e))["days"], {})

    def test_load_drops_malformed_days_and_bookkeeping(self):
        good = zero_day()
        bad_med = {**zero_day(), "oracle": {"new": 1, "q": 1, "med": 1e9}}               # QUOTE_BP 밖
        extra = {**zero_day(), "oracle": {"new": 1, "q": 0, "med": None, "id": "123456789"}}   # 낯선 칸
        few = {k: v for k, v in zero_day().items() if k != "tsmc"}
        q_no_med = {**zero_day(), "meta": {"new": 2, "q": 2, "med": None}}
        q_over_new = {**zero_day(), "meta": {"new": 1, "q": 2, "med": 100.0}}
        js = {"schema": 1, "days": {"2026-10-27": good, "2026-10-26": bad_med, "2026-10-25": extra, "2026-10-24": few,
                                    "2026-10-23": q_no_med, "2026-10-22": q_over_new, "어제": good, "2026-10-21": "x"},
              "tries": {"2026-10-20": {"n": 1, "last": "2026-10-28", "why": "bad"},
                        "2026-10-19": {"n": 9, "last": "2026-10-28", "why": "bad"},
                        "2026-10-18": {"n": 1, "last": "2026-10-28", "why": "원격 글"}},
              "status": {"date": "2026-10-28", "error": "URLError: https://bad.invalid"}}
        with open(os.path.join(self.tmp, cd.STORE), "w", encoding="utf-8") as f:
            json.dump(js, f, ensure_ascii=False)
        s = cd.load_store(self.tmp)
        self.assertEqual(set(s["days"]), {"2026-10-27"})
        self.assertEqual(set(s["tries"]), {"2026-10-20"})
        self.assertEqual(s["status"], {})
        for body in ("{broken", json.dumps({"schema": 2, "days": {}}), json.dumps([1])):
            with open(os.path.join(self.tmp, cd.STORE), "w", encoding="utf-8") as f:
                f.write(body)
            self.assertEqual(cd.load_store(self.tmp), cd.empty_store())


# ---------- 칸·실행 ----------

def held_store(end=D(2026, 10, 27), n=400):
    s = cd.empty_store()
    for i in range(n):
        put(s, end - datetime.timedelta(days=i), {"oracle": {"new": 3, "q": 3, "med": 300.0 + (i % 3)},
                                                  "meta": {"new": 1, "q": 0, "med": None},
                                                  "intel": {"new": 1, "q": 1, "med": 90.0}})
    return s


class ItemTest(unittest.TestCase):
    def test_texts_and_tables(self):
        W = cd.window(held_store()["days"], TODAY)
        data = cd.build(W, None, {}, NOW)
        q, t = data["items"]["quotes"], data["items"]["trades"]
        self.assertTrue(q["ok"] and t["ok"])
        self.assertEqual(q["date"], "2026-10-27")
        self.assertTrue(q["line"].startswith("~2026-10-27 최근 14일 중앙값 — 괄호는 4주 전 대비 · 1년 전: 오라클 301bp (0 · 1년 전 301)"),
                        q["line"])
        self.assertIn("인텔 90bp (0 · 1년 전 90)", q["line"])
        self.assertIn("호가 없음: 메타·아마존·알파벳·MS·코어위브·브로드컴·엔비디아·AMD·마이크론·TSMC", q["line"])
        self.assertEqual(q["table"]["columns"], ["이름", "5년 호가", "4주 전 대비", "1년 전", "호가 수"])
        self.assertEqual(q["table"]["rows"][0], ["오라클", "301", "0", "301", "42"])
        self.assertEqual(q["table"]["rows"][1], ["메타", "호가 없음", "—", "—", "0"])
        self.assertEqual(q["table"]["rows"][cd.KEYS.index("intel")], ["인텔", "90", "0", "90", "14"])
        self.assertTrue(t["line"].startswith("2026-09-30~2026-10-27 28일 — 괄호는 1년 전 같은 28일: 오라클 84 (84) · 메타 28 (28)"),
                        t["line"])
        self.assertEqual(t["table"]["rows"][2], ["아마존", "0", "0"])
        self.assertEqual(len(q["table"]["rows"]), 12)

    def test_too_few_quotes_missing_prior_and_gaps_are_written_out(self):
        s = cd.empty_store()
        end = D(2026, 10, 27)
        for i in range(10):                                                           # 최근 10일만 — 4주 전·1년 전 없음
            put(s, end - datetime.timedelta(days=i), {"oracle": {"new": 1, "q": 1, "med": 300.0}})
        put(s, end, {"oracle": {"new": 1, "q": 1, "med": 300.0}, "nvidia": {"new": 2, "q": 2, "med": 120.0}})
        W = cd.window(s["days"], TODAY)
        data = cd.build(W, "fetch", {}, NOW)
        q, t = data["items"]["quotes"], data["items"]["trades"]
        self.assertIn("받은 날 10/14", q["line"])
        self.assertIn("오라클 300bp (4주 전 미수신)", q["line"])
        self.assertIn("엔비디아 호가 부족 2개", q["line"])
        self.assertEqual(q["table"]["rows"][cd.KEYS.index("nvidia")], ["엔비디아", "호가 부족", "—", "—", "2"])
        self.assertIn("받은 날 10/28, 받은 날만 셈", t["line"])
        self.assertNotIn("괄호는 1년 전", t["line"])
        self.assertIn("이번 갱신에서 받지 못한 날이 있다 · 수신 실패 — 다음 갱신에 이어 받는다.", q["extra"])
        prior = cd.empty_store()
        for i in range(40):                                                           # 4주 전 창에 호가가 모자라다
            put(prior, end - datetime.timedelta(days=i), {"oracle": {"new": 1, "q": 1 if i < 14 else 0,
                                                                     "med": 300.0 if i < 14 else None}})
        q2 = cd.build(cd.window(prior["days"], TODAY), None, {}, NOW)["items"]["quotes"]
        self.assertIn("오라클 300bp (4주 전 호가 부족)", q2["line"])
        self.assertEqual(q2["table"]["rows"][0][2], "4주 전 호가 부족")

    def test_values_guard_rejects_anything_outside_the_fixed_shape(self):
        W = cd.window(held_store()["days"], TODAY)
        v = cd.core_from(W, None)["values"]
        self.assertTrue(cd.values_ok(v))
        bad = []
        for mutate in (lambda x: x["names"][0].update(level=1e6),                       # 지어낸 지수 수준 같은 값
                       lambda x: x["names"][0].update(level=12.0, q=2),                 # 호가 부족인데 수준
                       lambda x: x["names"][0].update(raw="ORACLE CORPORATION"),
                       lambda x: x["names"][0].update(label="Oracle"),
                       lambda x: x["names"].reverse(),
                       lambda x: x["names"].pop(),
                       lambda x: x["cover"].update(level=15),
                       lambda x: x["cover"].update(count=-1),
                       lambda x: x.update(last_error="URLError"),
                       lambda x: x.update(id="1234567"),
                       lambda x: x.update(age=1),
                       lambda x: x.update(end="2026-09-01"),                              # 끝이 처음보다 이르다
                       lambda x: x["names"][1].update(new=True),
                       lambda x: x["names"][1].update(new_1y="12")):
            y = json.loads(json.dumps(v))
            mutate(y)
            bad.append(cd.values_ok(y))
        self.assertEqual(bad, [False] * len(bad))

    def test_values_outside_the_shape_are_never_written(self):
        W = cd.window(held_store()["days"], TODAY)
        W["names"][0]["level"] = 123456.0                                            # 지어낸 지수 수준 같은 값
        with contextlib.redirect_stderr(io.StringIO()):
            data = cd.build(W, None, {}, NOW)
        for it in data["items"].values():
            self.assertEqual((it["ok"], it["stale"], it["error"]), (False, False, "계산할 자료가 모자람"))
            self.assertNotIn("values", it)
        self.assertNotIn("123456", json.dumps(data))
        good = cd.build(cd.window(held_store()["days"], TODAY), None, {}, NOW)
        W["stale"] = True
        with contextlib.redirect_stderr(io.StringIO()):
            stale = cd.build(W, None, good["items"], NOW + datetime.timedelta(days=9))["items"]["quotes"]
        self.assertEqual((stale["stale"], stale["values"]), (True, good["items"]["quotes"]["values"]))   # 직전 값으로

    def test_stale_window_keeps_numbers_with_reason_and_since(self):
        s = held_store(end=D(2026, 10, 20))
        W = cd.window(s["days"], TODAY)
        data = cd.build(W, None, {}, NOW)
        q = data["items"]["quotes"]
        self.assertEqual((q["ok"], q["stale"], q["error"], q["failed_since"], q["date"]),
                         (False, True, "새 날 자료가 들어오지 않음", "2026-10-28", "2026-10-20"))
        later = cd.build(cd.window(s["days"], D(2026, 10, 30)), "fetch", data["items"],
                         NOW + datetime.timedelta(days=2))["items"]["quotes"]
        self.assertEqual((later["error"], later["failed_since"]), ("수신 실패", "2026-10-28"))   # 처음 실패한 날이 이어진다
        fresh = cd.build(cd.window(held_store()["days"], TODAY), None, data["items"], NOW)["items"]["quotes"]
        self.assertEqual((fresh["ok"], fresh["failed_since"]), (True, None))


class MainTest(TempDir):
    def run_main(self, opener=None, now=NOW, args=(), clock=time.monotonic):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            code = cd.main(["--out", self.tmp, *args], opener=opener, now=now, clock=clock)
        self.log = buf.getvalue()
        return code

    def saved(self, name=cd.FILE):
        with open(os.path.join(self.tmp, name), encoding="utf-8") as f:
            return json.load(f)

    def raw(self, name):
        with open(os.path.join(self.tmp, name), encoding="utf-8") as f:
            return f.read()

    def days_with_rows(self, today=TODAY):
        rows = lambda d: [row(day=d, spread="0.0300", uid="FAKE01", idsrc="REDID", did="9876543", notional="7,654,321"),
                          row(name="", upi="SR NT", day=d, spread="0.0310", uid="FAKE01AA0", idsrc="REDID", t="16:00:00"),
                          row(name="Meta Platforms, Inc.", day=d, upfront="12345.67", t="17:00:00")]
        return all_days(today, rows)

    def test_first_run_writes_both_files_and_keeps_only_counts(self):
        op = FakeOpener(self.days_with_rows())
        self.assertEqual(self.run_main(op), 0)
        data = self.saved()
        self.assertEqual(data["order"], ["quotes", "trades"])
        for key in data["order"]:
            it = data["items"][key]
            self.assertEqual((it["ok"], it["stale"], it["error"], it["date"], it["retrieved"]),
                             (True, False, None, "2026-10-27", "2026-10-28"))
            self.assertEqual(it["sources"], [{"series": "SEC_CUMULATIVE_CREDITS", "name": "DTCC Data Repository (U.S.) LLC",
                                              "licence": "sec-reg-sbsr-public-dissemination", "citation": cd.CITATION}])
            self.assertEqual(it["notices"], [cd.COMPUTED_NOTICE, cd.CAVEAT_NOTICE])
        self.assertEqual(data["items"]["quotes"]["table"]["rows"][0], ["오라클", "305", "0", "305", "28"])
        store = self.saved(cd.STORE)
        self.assertEqual(store["days"]["2026-10-27"]["oracle"], {"new": 2, "q": 2, "med": 305.0})
        self.assertEqual(store["days"]["2026-10-27"]["meta"], {"new": 1, "q": 0, "med": None})
        for name in (cd.FILE, cd.STORE):                                              # 원 행·식별자·RED 코드는 쓰지 않는다
            text = self.raw(name)
            for raw in ("ORACLE", "Meta Platforms", "ID-", "FAKE01", "9876543", "REDID", "SR NT", "CDS Corp", "7,654,321",
                        "12345.67", "T15:00", "Underlying", "Dissemination"):
                self.assertNotIn(raw, text, (name, raw))
        self.assertEqual(sorted(os.listdir(self.tmp)), sorted([cd.FILE, cd.STORE]))
        n = len(op.calls)
        self.assertEqual(self.run_main(op), 0)
        self.assertEqual(len(op.calls), n)                                             # 둘째 실행은 요청 0번

    def test_next_day_fetches_one_day_and_prunes(self):
        op = FakeOpener(self.days_with_rows())
        self.run_main(op)
        nxt = TODAY + datetime.timedelta(days=1)
        op2 = FakeOpener(self.days_with_rows(nxt))
        self.assertEqual(self.run_main(op2, now=NOW + datetime.timedelta(days=1)), 0)
        got = {c[0][-14:-4] for c in op2.calls}
        self.assertIn("2026_10_28", got)
        self.assertLessEqual(len(got), 2)                                              # 새 날 + 1년 전 쪽 하루
        store = self.saved(cd.STORE)
        self.assertEqual(self.saved()["items"]["quotes"]["date"], "2026-10-28")
        self.assertNotIn((TODAY - datetime.timedelta(days=cd.YEAR_GAP + cd.YEAR_DAYS - 1)).isoformat(), store["days"])

    def test_connection_failure_with_held_days_keeps_fresh_numbers_and_exits_1(self):
        self.run_main(FakeOpener(self.days_with_rows()))
        nxt = TODAY + datetime.timedelta(days=1)
        days = self.days_with_rows(nxt)
        days[TODAY] = "boom"
        self.assertEqual(self.run_main(FakeOpener(days), now=NOW + datetime.timedelta(days=1)), 1)
        q = self.saved()["items"]["quotes"]
        self.assertEqual((q["ok"], q["date"]), (True, "2026-10-27"))                     # 끝 날이 아직 4일 안
        self.assertIn("이번 갱신에서 받지 못한 날이 있다 · 수신 실패 — 다음 갱신에 이어 받는다.", q["extra"])
        self.assertEqual(self.saved(cd.STORE)["status"], {"date": "2026-10-29", "error": "fetch"})
        self.assertIn("::warning::단일종목 CDS 참고: 수신 실패", self.log)
        self.assertNotIn("bad.invalid", self.log)
        op = FakeOpener(self.days_with_rows(nxt))                                        # 같은 날 다시 — 건너뛴다
        self.assertEqual(self.run_main(op, now=NOW + datetime.timedelta(days=1, minutes=30)), 1)
        self.assertEqual(op.calls, [])
        self.assertEqual(self.run_main(op, now=NOW + datetime.timedelta(days=1, minutes=40), args=("--force",)), 0)
        self.assertEqual(self.saved()["items"]["quotes"]["date"], "2026-10-28")

    def test_stale_store_and_broken_store_fall_back(self):
        self.run_main(FakeOpener(self.days_with_rows()))
        first = self.saved()
        later = NOW + datetime.timedelta(days=10)
        self.assertEqual(self.run_main(FakeOpener({}, ), now=later), 1)                 # 모두 403 — 주소가 바뀐 꼴
        q = self.saved()["items"]["quotes"]
        self.assertEqual((q["ok"], q["stale"], q["error"], q["failed_since"], q["date"]),
                         (False, True, cd.REASONS["alarm"], "2026-11-07", "2026-10-27"))
        self.assertEqual(q["values"]["last_error"], "alarm")
        self.assertEqual(q["table"], first["items"]["quotes"]["table"])               # 숫자는 받아 둔 날 그대로
        with open(os.path.join(self.tmp, cd.STORE), "w", encoding="utf-8") as f:   # 저장 파일이 깨졌다
            f.write("{broken")
        self.assertEqual(self.run_main(FakeOpener({}), now=later + datetime.timedelta(days=1)), 1)
        q2 = self.saved()["items"]["quotes"]
        self.assertEqual((q2["ok"], q2["stale"], q2["failed_since"], q2["date"], q2["values"]),
                         (False, True, "2026-11-07", "2026-10-27", q["values"]))   # 직전 cds.json 그대로
        self.assertEqual((q2["line"], q2["error"]), (q["line"], cd.REASONS["alarm"]))
        self.assertEqual(self.saved(cd.STORE)["days"], {})                             # 깨진 저장은 새로 시작한다

    def test_first_failure_without_anything_has_no_numbers(self):
        self.assertEqual(self.run_main(FakeOpener({d: "boom" for d in cd.targets(TODAY)})), 1)
        q = self.saved()["items"]["quotes"]
        self.assertEqual((q["ok"], q["stale"], q["error"]), (False, False, "수신 실패"))
        self.assertNotIn("values", q)
        self.assertNotIn("line", q)
        self.assertEqual(q["sources"][0]["citation"], cd.CITATION)

    def test_older_window_is_not_taken(self):
        self.run_main(FakeOpener(self.days_with_rows()))
        data = self.saved()
        data["items"]["quotes"]["date"] = data["items"]["quotes"]["values"]["end"] = "2026-10-29"   # 직전이 더 늦은 날
        with open(os.path.join(self.tmp, cd.FILE), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        self.run_main(FakeOpener(self.days_with_rows()))
        q = self.saved()["items"]["quotes"]
        self.assertEqual((q["ok"], q["stale"], q["error"], q["date"]), (False, True, "받은 자료가 직전 자료보다 오래됨", "2026-10-29"))

    def test_same_numbers_keep_the_file_and_the_retrieved_date(self):
        self.run_main(FakeOpener(self.days_with_rows()))
        path = os.path.join(self.tmp, cd.FILE)
        os.utime(path, (1, 1))
        self.run_main(FakeOpener(self.days_with_rows()), now=NOW + datetime.timedelta(minutes=5))
        self.assertEqual(os.stat(path).st_mtime, 1)
        os.utime(path, (1, 1))
        self.assertEqual(self.run_main(FakeOpener({}), now=NOW + datetime.timedelta(days=1), args=("--offline",)), 0)
        self.assertEqual(os.stat(path).st_mtime, 1)                                     # 새 날이 없으면 그대로
        self.run_main(FakeOpener({}), now=NOW + datetime.timedelta(days=2), args=("--offline",))
        q = self.saved()["items"]["quotes"]
        self.assertEqual((q["ok"], q["date"], q["retrieved"]), (True, "2026-10-27", "2026-10-28"))   # 처음 받은 날

    def test_a_malformed_previous_file_is_not_carried(self):
        self.run_main(FakeOpener(self.days_with_rows()))
        data = self.saved()
        for key, mutate in (("quotes", lambda v: v["names"][0].update(level=987654.0)),
                            ("trades", lambda v: v.update(raw="ORACLE CORPORATION"))):
            mutate(data["items"][key]["values"])
        with open(os.path.join(self.tmp, cd.FILE), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        with open(os.path.join(self.tmp, cd.STORE), "w", encoding="utf-8") as f:   # 저장 파일도 깨졌다
            f.write("{broken")
        self.assertEqual(self.run_main(FakeOpener({}), now=NOW + datetime.timedelta(days=1)), 1)
        text = self.raw(cd.FILE)
        for key in ("quotes", "trades"):
            it = self.saved()["items"][key]
            self.assertEqual((it["ok"], it["stale"]), (False, False))
            self.assertNotIn("values", it)
        self.assertNotIn("987654", text)
        self.assertNotIn("ORACLE", text)

    def test_offline_reads_the_store_without_writing_it(self):
        self.run_main(FakeOpener(self.days_with_rows()))
        store = os.path.join(self.tmp, cd.STORE)
        os.utime(store, (1, 1))
        os.remove(os.path.join(self.tmp, cd.FILE))
        op = FakeOpener({})
        self.assertEqual(self.run_main(op, now=NOW + datetime.timedelta(days=1), args=("--offline",)), 0)
        self.assertEqual((op.calls, os.stat(store).st_mtime), ([], 1))
        self.assertTrue(self.saved()["items"]["quotes"]["ok"])
        before = self.raw(cd.STORE)                                                    # 두 달 뒤 — 지울 날이 생겨도 쓰지 않는다
        self.assertEqual(self.run_main(op, now=NOW + datetime.timedelta(days=60), args=("--offline",)), 1)
        self.assertEqual((op.calls, self.raw(cd.STORE), os.stat(store).st_mtime), ([], before, 1))
        self.assertTrue(self.saved()["items"]["quotes"]["stale"])

    def test_budget_runs_out_and_the_next_run_continues(self):
        clock = FakeClock()
        op = FakeOpener(self.days_with_rows(), clock=clock, cost=1)
        self.assertEqual(self.run_main(op, clock=clock, args=("--budget", "5")), 0)
        self.assertEqual(len(self.saved(cd.STORE)["days"]), 5)
        self.assertIn("못 받은 날 66일", self.log)
        op2 = FakeOpener(self.days_with_rows())
        self.run_main(op2, now=NOW + datetime.timedelta(minutes=10))
        self.assertEqual(len(op2.calls), cd.RECENT_DAYS + cd.YEAR_DAYS - 5)

    def test_write_failure_exits_1_and_the_write_is_atomic(self):
        self.run_main(FakeOpener(self.days_with_rows()))
        before = self.raw(cd.FILE)
        real = cd.os.replace
        def boom(*a):
            raise OSError("disk")
        cd.os.replace = boom
        try:
            self.assertEqual(self.run_main(FakeOpener(self.days_with_rows(TODAY + datetime.timedelta(days=1))),
                                           now=NOW + datetime.timedelta(days=1)), 1)
        finally:
            cd.os.replace = real
        self.assertEqual(self.raw(cd.FILE), before)
        self.assertEqual(sorted(os.listdir(self.tmp)), sorted([cd.FILE, cd.STORE]))   # .tmp가 남지 않는다

    def test_every_string_is_fixed_text_without_verdict_words(self):
        self.run_main(FakeOpener(self.days_with_rows()))
        days = self.days_with_rows(TODAY + datetime.timedelta(days=1))
        days[TODAY] = "http500"
        days[D(2026, 10, 1)] = "boom"
        self.run_main(FakeOpener(days), now=NOW + datetime.timedelta(days=1))
        self.run_main(FakeOpener({}), now=NOW + datetime.timedelta(days=12))
        for name in (cd.FILE, cd.STORE):
            dump = self.raw(name)
            for word in list(FORBIDDEN_TEXT) + list(VERDICT):
                self.assertNotIn(word, dump, (name, word))
            self.assertIsNone(re.search(r"https?://", dump), name)                    # 주소가 없다(원격 글도)
            self.assertNotIn("bad.invalid", dump)
            self.assertNotIn("URLError", dump)
        errors = {it.get("error") for it in self.saved()["items"].values()} - {None}
        self.assertLessEqual(errors, set(cd.REASONS.values()))
        nested = re.compile(r"\([^()]*\(")
        for t in re.findall(r'"((?:[^"\\]|\\.)*)"', self.raw(cd.FILE)):
            self.assertIsNone(nested.search(t), t)
        self.assertNotIn("bad.invalid", self.log)


class LicenceTest(unittest.TestCase):
    def test_citation_and_licence_are_fixed(self):
        self.assertEqual(cd.CITATION, "Source: DTCC Data Repository (U.S.) LLC, SEC security-based swap public dissemination "
                                      "(Reg SBSR); site calculations")
        self.assertEqual(cd.citation(), cd.CITATION)
        self.assertEqual(cd.LICENCE, {"SEC_CUMULATIVE_CREDITS": "sec-reg-sbsr-public-dissemination"})
        self.assertEqual([s["licence"] for s in cd.sources_of()], ["sec-reg-sbsr-public-dissemination"])
        caveat = cd.CAVEAT_NOTICE
        for part in ("DTCC 쪽 보고만", "중간값(mid)이 아니고", "나중에 취소"):              # 세 가지 단서
            self.assertIn(part, caveat)
        with open(os.path.join(SCRIPTS, "cds_fetch.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertNotRegex(src, r"(?i)\.(png|svg|jpe?g|gif)\b")                    # 로고·그림을 싣지 않는다
        self.assertNotRegex(src, r"[\w.+-]+@[\w-]+\.[\w.]+")                          # 이메일 주소가 없다


class StaticTest(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
            return f.read()

    def test_workflow_fetches_without_failing_the_run(self):
        wf = self.read(".github", "workflows", "daily.yml")
        self.assertTrue("id: cds\n" in wf, "daily.yml에 단일종목 CDS 단계(id: cds) 없음")
        step = wf[wf.index("id: cds\n"):]
        self.assertIn("continue-on-error: true", step[:200])
        self.assertIn("timeout-minutes: 2", step[:200])
        self.assertIn("python scripts/cds_fetch.py", step[:300])
        self.assertLess(wf.index("id: cds"), wf.index("공개 전 검사(새 산출물 포함)"))
        self.assertLess(wf.index("id: cds"), wf.index("git add data"))
        self.assertNotIn("cds", wf[wf.index("\n  alert:"):])                    # 실패해도 알림을 띄우지 않는다
        self.assertIn("node --test scripts/test_cds_render.cjs", wf[wf.index("\n  check:"):wf.index("\n  update:")])

    def test_page_wires_the_card(self):
        page = self.read("site", "index.html")
        for snippet in ('getJson("data/cds.json")', '<script src="cds.js"></script>', "window.CdsCard.render(",
                        '<a href="data/cds.json">'):
            self.assertTrue(snippet in page, f"index.html에 {snippet} 없음")
        self.assertTrue(re.search(r'id\s*[:=]\s*"cds-slot"', page), 'index.html에 id "cds-slot" 없음')

    def test_readme_counts(self):
        readme = self.read("README.md")
        m = re.search(r"\*\*아침 쪽 Python 테스트 (\d+)개 \+ node 테스트 (\d+)개\*\*\((.*?)\)와 \*\*저녁판", readme)
        py_part, node_part = m.group(3).split(" / node: ")
        mine = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()
        self.assertTrue(re.search(rf"(^|· )단일종목 CDS 참고 {mine}( ·|$)", py_part), f"README에 '단일종목 CDS 참고 {mine}' 없음")
        cjs = len(re.findall(r"^test\(", self.read("scripts", "test_cds_render.cjs"), flags=re.M))
        self.assertTrue(re.search(rf"(^|· )CDS 카드 그리기 {cjs}( ·|$)", node_part), f"README에 'CDS 카드 그리기 {cjs}' 없음")

    def test_screen_script_matches_the_file_and_writes_text_only(self):
        js = self.read("site", "cds.js")
        card = re.findall(r'"(\w+)"', js[js.index("const CARD = ["):].split("]")[0])
        self.assertEqual(card, cd.ORDER)
        reasons = re.findall(r'"([^"]+)"', js[js.index("const REASONS = ["):].split("];")[0])
        self.assertEqual(reasons, list(cd.REASONS.values()))
        body = js[js.index("const SOURCE = "):].split(";\n", 1)[0]
        self.assertEqual("".join(re.findall(r'"([^"]*)"', body)), cd.CITATION)
        self.assertIn('const LABEL = "참고 — 신용 사건 예측 아님";', js)
        self.assertIn('el("p", { class: "source-link" }, SOURCE)', js)                  # 출처는 늘 함께
        for tok in ("innerHTML", "outerHTML", "insertAdjacentHTML", "createElement", "fetch(", "eval(", "<img", "src="):
            self.assertNotIn(tok, js)
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        for word in list(FORBIDDEN_TEXT) + list(VERDICT):
            self.assertNotIn(word, code, word)


if __name__ == "__main__":
    unittest.main(verbosity=1)
