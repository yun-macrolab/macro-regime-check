#!/usr/bin/env python3
"""TIC 해외 보유 미 국채(tic_fetch) 테스트 — 표 5·과거 표 읽기(너그러운 빈칸·따옴표·줄 끝, 닫힌 쪽으로 실패하는 꼴), 과거 표 위에
표 5를 덮는 그래프, 1개월·12개월 변화와 문구, 한국 줄, 모르는 이름, 합계 검사, 한쪽·양쪽 실패와 직전 값 이어 싣기, 같은 내용이면
다시 쓰지 않음, 예산·굳은 상한, 문구 원칙(판정 낱말·이메일 없음).

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — 미 재무부 응답은 지어낸 표(실제 꼴: 2026-11-19 받은 파일의 머리 줄·합계 줄·주석·CRLF·따옴표·13열 옛 덩어리)를
가짜 opener로 돌려준다. 숫자는 모두 지어낸 것이다. 실제 파일로 읽어 보는 테스트(RealFilesTest)는 환경 변수 TIC_REAL_DIR이나
.work/tic/(온라인으로 한 번 돌린 캐시)에 두 파일이 있을 때만 돌고, 없으면 건너뛴다.
"""
import os, io, re, sys, json, time, shutil, datetime, tempfile, threading, unittest, contextlib, http.client
from unittest import mock

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import tic_fetch as tf
from test_render_public import FORBIDDEN_TEXT

REPO = os.path.dirname(SCRIPTS)
D = datetime.date
NOW = datetime.datetime(2026, 11, 19, 1, 30, tzinfo=datetime.timezone.utc)
TODAY = NOW.date()
SPEC_KEYS = {"key", "title", "unit", "years", "zero", "threshold", "note", "source_note", "notices", "lines"}
LINE_KEYS = {"key", "label", "role", "series", "derived", "points"}
VERDICT = ["매수", "매도", "유망", "적중", "전망", "예상", "추천", "과열", "위험 신호", "경고"]
ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# 지어낸 나라 20곳 — 표 5에 실제로 오르는 이름 꼴(마지막 달 값, 십 분의 일 단위 정수)
NAMES = ["Japan", "United Kingdom", "China, Mainland", "Belgium", "Cayman Islands", "Canada", "Luxembourg", "Ireland",
         "France", "Taiwan", "Switzerland", "Singapore", "Hong Kong", "India", "Norway", "Brazil", "Korea, South",
         "Saudi Arabia", "Bermuda", "United Arab Emirates"]


def back(m0, n):
    """m0부터 거꾸로 n개 달."""
    out = [m0]
    while len(out) < n:
        out.append(tf._prev_month(out[-1]))
    return out


def tenths(i, j):
    """나라 i의 j달 전 값(십 분의 일 단위 정수) — 큰 차례가 표의 차례와 같게, 달마다 조금씩."""
    return 12000 - 550 * i - 7 * j + (j % 3) * 4


def table_rows(m0="2026-09", n=13, names=NAMES):
    """원표의 숫자(십 분의 일 단위 정수) — {months, countries [[이름, [..]]], other, grand, official, bills, notes}."""
    months = back(m0, n)
    countries = [[nm, [tenths(i, j) for j in range(n)]] for i, nm in enumerate(names)]
    other = [18000 + 3 * j for j in range(n)]
    grand = [sum(c[1][j] for c in countries) + other[j] for j in range(n)]
    official = [g * 4 // 10 for g in grand]
    bills = [o * 8 // 100 for o in official]
    notes = [o - b for o, b in zip(official, bills)]
    return {"months": months, "countries": countries, "other": other, "grand": grand, "official": official,
            "bills": bills, "notes": notes}


def fmt(v):
    return "*" if v == "*" else f"{v / 10:.1f}"


def table_text(t=None, eol="\r\n", quote=False, extra_after_header=(), drop=(), notes=True, pad=True):
    """표 5의 글자 — 2026-11-19 받은 파일과 같은 꼴(머리 넉 줄, 'Country' 머리 줄, 나라 20줄, 그 밖, 합계 넷, 주석)."""
    t = t or table_rows()
    tabs = "\t" * len(t["months"]) if pad else ""
    lines = ["Table 5: Major Foreign Holders of Treasury Securities" + tabs, "Holdings at end of time period" + tabs,
             "Billions of dollars" + tabs, "Link: https://ticdata.treasury.gov/x" + tabs, tabs,
             "\t".join(["Country"] + t["months"])]
    lines += list(extra_after_header)
    for nm, vals in t["countries"]:
        lines.append("\t".join([f'"{nm}"' if quote and "," in nm else nm] + [fmt(v) for v in vals]))
    for label, key in (("All Other", "other"), ("Grand Total", "grand"), ("Of Which: Foreign Official", "official"),
                       ("Of Which: Foreign Official Treasury Bills", "bills"),
                       ("Of Which: Foreign Official T-Bonds & Notes", "notes")):
        if label not in drop and t.get(key) is not None:
            lines.append("\t".join([label] + [fmt(v) for v in t[key]]))
    if notes:
        lines += [tabs, "Notes:" + tabs, "The data in this table are collected primarily from U.S.-based custodians." + tabs]
    return eol.join(lines) + eol


def hist_value(m):
    """과거 표의 지어낸 월말 값(십 분의 일 단위 정수) — 해·달로 정해진다."""
    y, mo = int(m[:4]), int(m[5:7])
    k = (y - 2009) * 12 + mo
    return {"grand": 40000 + 300 * k, "official": 30000 + 40 * k, "Japan": 9000 + 10 * k, "United Kingdom": 1000 + 30 * k,
            "China, Mainland": 11000 - 20 * k, "Korea, South": 400 + 5 * k, "Belgium": 2000 + k}


def hist_text(years=range(2025, 2008, -1), value=hist_value, eol="\r\n", skip=(), date="9/16/2026"):
    """과거 표의 글자 — 해마다 한 덩어리(2011과 그 앞은 'Jun'이 두 번인 13열), 따옴표 이름, 주석 표시 이름, 앞 빈칸 합계 줄."""
    out = ["\t\t\tMAJOR FOREIGN HOLDERS OF TREASURY SECURITIES", "\t\t\t\t    (in billions of dollars)", ""]
    for y in years:
        if y in skip:
            continue
        cols = ["Dec", "Nov", "Oct", "Sep", "Aug", "Jul", "Jun"] + (["Jun"] if y <= 2011 else []) + \
               ["May", "Apr", "Mar", "Feb", "Jan"]
        ms = [f"{y}-{ABBR.index(c) + 1:02d}" for c in cols]
        out += ["", "\t" + "\t".join(cols) + "\t\t", "Country\t" + "\t".join(str(y) for _ in cols) + "\t\t",
                "\t" + "\t".join("------" for _ in cols) + "\t\t", ""]

        def row(label, key):
            vals = []
            for m in ms:
                v = value(m)[key]
                vals.append(str(v // 10) if v % 10 == 0 else f"{v / 10:.1f}")     # 1200 또는 1200.5 — 둘 다 나온다
            return label + "\t" + "\t".join(vals) + "\t\t"
        out.append(row("Japan", "Japan"))
        out.append(row('"China, Mainland"', "China, Mainland"))
        out.append(row("United Kingdom 2/" if y <= 2011 else "United Kingdom", "United Kingdom"))
        out.append(row('"Korea, South"', "Korea, South"))
        out.append(row("Belgium", "Belgium"))
        out.append("All Other\t" + "\t".join("1.0" for _ in cols))
        out.append(row("Grand Total", "grand"))
        out += ["", "Of which:"]
        out.append(row("  For. Official" if y <= 2022 else "For. Official", "official"))
        out.append("    Treasury Bills\t" + "\t".join("1.0" for _ in cols))
        out.append("    T-Bonds & Notes\t" + "\t".join("1.0" for _ in cols))
    out += ["", "", "Department of the Treasury/Federal Reserve Board", date, '"(2025 revised July 14, 2026)"', "",
            "*     Less than $50 million.", "17/   Denotes series break."]
    return eol.join(out) + eol


class Resp(io.BytesIO):
    def __init__(self, body, final):
        super().__init__(body)
        self.final = final
        self.length = None

    def geturl(self):
        return self.final

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Route:
    """urlopen 대역 — 주소마다 본문(글자·바이트) 또는 예외. 부른 주소와 timeout을 적는다. cost초만큼 가짜 시계를 민다."""
    def __init__(self, table=None, hist=None, final=None, clock=None, cost=0.0):
        self.by = {tf.TABLE_URL: table_text() if table is None else table,
                   tf.HIST_URL: hist_text() if hist is None else hist}
        self.final, self.clock, self.cost, self.calls = final or {}, clock, cost, []

    def __call__(self, req, timeout=None):
        url = req.full_url
        self.calls.append((url, timeout, req.get_header("User-agent")))
        if self.clock is not None:
            self.clock.t += self.cost
        body = self.by[url]
        if isinstance(body, BaseException):
            raise body
        return Resp(body.encode("utf-8") if isinstance(body, str) else body, self.final.get(url, url))


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)


def run(out, route=None, argv=(), now=NOW, clock=None, work=None):
    """main()을 돌린다 — (종료코드, 표준 출력, 산출물 dict 또는 None)."""
    work = work or os.path.join(out, "_work")
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        code = tf.main(["--out", out, "--work", work, *argv], opener=route or Route(), now=now,
                       clock=clock or time.monotonic)
    path = os.path.join(out, tf.FILE)
    data = load_json(path) if os.path.exists(path) else None
    return code, buf.getvalue(), data


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def tmpdir(case):
    d = tempfile.mkdtemp()
    case.addCleanup(shutil.rmtree, d)
    return d


# ---------- 표 5 읽기 ----------

class ParseTableTest(unittest.TestCase):
    def test_reads_the_real_shape(self):
        t = tf.parse_table(table_text(), TODAY)
        self.assertEqual(t["months"], back("2026-09", 13))
        self.assertEqual([r[0] for r in t["countries"]], NAMES)
        rows = table_rows()
        self.assertEqual(t["grand"], [v / 10 for v in rows["grand"]])
        self.assertEqual(t["official"][0], rows["official"][0] / 10)
        self.assertEqual(t["official_bills"][12], rows["bills"][12] / 10)
        self.assertEqual(t["official_notes_bonds"][1], rows["notes"][1] / 10)
        self.assertEqual(t["other"][0], 1800.0)
        self.assertEqual(t["countries"][16], ["Korea, South", [tenths(16, j) / 10 for j in range(13)]])

    def test_whitespace_quotes_line_ends_and_bom_are_lenient(self):
        want = tf.parse_table(table_text(), TODAY)
        for text in (table_text(eol="\n", quote=True), table_text(eol="\r", pad=False),
                     "\ufeff" + table_text().replace("Japan\t", "  Japan  \t").replace("\t1", "\t 1"),
                     table_text(extra_after_header=["\t------" * 13, ""])):
            self.assertEqual(tf.parse_table(text, TODAY), want)

    def test_a_less_than_50_million_star_is_no_value_in_a_country_cell_only(self):
        t = table_rows()
        t["countries"][19][1][5] = "*"                                   # 별은 '5천만 달러 미만'
        got = tf.parse_table(table_text(t), TODAY)
        self.assertIsNone(got["countries"][19][1][5])
        bad = table_rows()
        bad["official"][0] = "*"
        with self.assertRaises(tf.TicError) as e:
            tf.parse_table(table_text(bad), TODAY)
        self.assertEqual(e.exception.code, "format")

    def fails(self, text, code="format", today=TODAY):
        with self.assertRaises(tf.TicError) as e:
            tf.parse_table(text, today)
        self.assertEqual(e.exception.code, code)

    def test_missing_totals_fail_closed(self):
        self.fails(table_text(drop=("Grand Total",)))
        self.fails(table_text(drop=("Of Which: Foreign Official",)))
        self.fails(table_text(drop=("All Other",)))                     # 그 밖 줄도 꼭 — 나라 합 검사와 순위의 바탕
        # 단기채·이표채는 없어도 읽는다(값을 지어내지 않고 칸을 비운다)
        t = tf.parse_table(table_text(drop=("Of Which: Foreign Official Treasury Bills",
                                            "Of Which: Foreign Official T-Bonds & Notes")), TODAY)
        self.assertIsNotNone(t["other"])
        self.assertIsNone(t["official_bills"])
        self.assertIsNone(t["official_notes_bonds"])

    def test_a_renamed_all_other_row_is_not_read_as_the_top_country(self):
        """'All Other'가 이름만 바뀌면 전엔 나라 1위로 읽혀 한국 순위까지 밀렸다(2026-11-19 검토) — 이제 표를 받지 않는다."""
        for label in ("All Others", "Other Countries", "All Other Countries", "Rest of World", "Others", "Remainder"):
            self.fails(table_text().replace("All Other\t", label + "\t"))
        for label in ("Total Foreign", "Grand Totals"):                         # 합계 줄의 다른 이름도 나라로 받지 않는다
            self.fails(table_text().replace("Bermuda\t", label + "\t"))
        # 실제 나라 이름은 그대로 읽는다(낱말 경계 — 'Mother' 같은 글자 조각에 걸리지 않는다)
        self.assertIsNone(tf.row_kind("Motherland"))
        self.assertEqual(tf.row_kind("All Other"), "other")
        self.assertEqual(tf.row_kind("Others"), "bad")

    def test_no_header_or_months_that_do_not_follow_fail(self):
        self.fails(table_text().replace("Country\t", "Nation\t"))
        t = table_rows()
        t["months"][3], t["months"][4] = t["months"][4], t["months"][3]
        self.fails(table_text(t))
        t = table_rows()
        t["months"][12] = "2025-08"                                      # 한 달 건너뜀
        self.fails(table_text(t))
        self.fails(table_text().replace("2026-09", "2026-9"))           # 달 꼴이 아니면 머리 줄이 아니다

    def test_non_numbers_blanks_and_junk_rows_fail(self):
        self.fails(table_text().replace("Japan\t1200.0", "Japan\tn/a"))
        self.fails(table_text().replace("Japan\t1200.0", "Japan\t"))           # 한 칸만 빈 줄 — 나라 칸이어도 빈 칸은 실패
        self.fails(table_text().replace("Japan\t1200.0", "Japan\t1.2e3"))
        self.assertIn("빈 칸은 어디서나 실패", tf.__doc__)                    # 머리말이 코드와 같은 규칙을 적는다

    def test_out_of_range_values_fail_as_range(self):
        t = table_rows()
        t2 = {**t, "grand": [g * 1000 for g in t["grand"]]}                  # 백만 달러로 읽힌 것
        self.fails(table_text(t2), "range")
        t3 = {**t, "official": [g + 10 for g in t["grand"]]}                 # 공적이 전체보다 크다
        self.fails(table_text(t3), "range")
        t4 = table_rows()
        t4["countries"][0][1][0] = 60000                                       # 한 나라 6조 달러
        self.fails(table_text(t4), "range")

    def test_duplicate_names_too_few_rows_and_future_month_fail(self):
        names = list(NAMES)
        names[5] = "Japan"
        self.fails(table_text(table_rows(names=names)))
        names = list(NAMES)
        names[5] = "South Korea"                                               # 표기만 다른 같은 나라
        self.fails(table_text(table_rows(names=names[:17] + ["Korea"] + names[18:])))
        self.fails(table_text(table_rows(names=NAMES[:4])))
        self.fails(table_text(table_rows(m0="2026-12")))                       # 오늘(2026-11) 뒤의 달

    def test_notes_and_trailing_label_rows_end_the_table(self):
        text = table_text().replace("Notes:", "Notes:\t9\t9")                 # 주석 줄에 숫자가 섞여도 표 끝
        self.assertEqual(len(tf.parse_table(text, TODAY)["countries"]), 20)


# ---------- 과거 표 읽기 ----------

class ParseHistoryTest(unittest.TestCase):
    def test_reads_monthly_values_from_2011_12_only(self):
        h = tf.parse_history(hist_text())
        ks = sorted(h["months"])
        self.assertEqual((ks[0], ks[-1], len(ks)), ("2011-12", "2025-12", 169))
        self.assertEqual(h["file_date"], "2026-09-16")
        for m in ("2011-12", "2016-02", "2024-07", "2025-12"):
            v = hist_value(m)
            self.assertEqual(h["months"][m]["grand"], v["grand"] / 10)
            self.assertEqual(h["months"][m]["official"], v["official"] / 10)      # 앞 빈칸이 붙은 'For. Official'
            self.assertEqual(h["months"][m]["countries"]["China, Mainland"], v["China, Mainland"] / 10)   # 따옴표 이름
            self.assertEqual(h["months"][m]["countries"]["Korea, South"], v["Korea, South"] / 10)

    def test_footnote_marked_rows_are_a_different_definition(self):
        h = tf.parse_history(hist_text())
        self.assertNotIn("United Kingdom", h["months"]["2011-12"]["countries"])   # 'United Kingdom 2/'
        self.assertEqual(h["months"]["2012-01"]["countries"]["United Kingdom"], hist_value("2012-01")["United Kingdom"] / 10)

    def test_the_13_column_blocks_before_2011_12_are_skipped(self):
        h = tf.parse_history(hist_text())
        self.assertNotIn("2011-11", h["months"])
        self.assertNotIn("2011-06", h["months"])                                 # 두 번 나온 'Jun'
        self.assertNotIn("2010-12", h["months"])

    def test_line_ends_and_leading_spaces_are_lenient(self):
        want = tf.parse_history(hist_text())
        self.assertEqual(tf.parse_history(hist_text(eol="\n")), want)
        self.assertEqual(tf.parse_history(hist_text().replace("Japan\t", " Japan \t")), want)

    def fails(self, text, code="format"):
        with self.assertRaises(tf.TicError) as e:
            tf.parse_history(text)
        self.assertEqual(e.exception.code, code)

    def test_a_missing_year_block_is_a_gap(self):
        self.fails(hist_text(skip=(2019,)))

    def test_a_missing_total_or_a_duplicated_block_fails(self):
        self.fails(hist_text().replace("Grand Total", "Grand  Sum", 1))
        text = hist_text(years=[2025, 2025, 2024, 2023])
        self.fails(text)

    def test_out_of_range_and_too_little_history_fail(self):
        big = lambda m: {**hist_value(m), "grand": hist_value(m)["grand"] * 1000}
        self.fails(hist_text(value=big), "range")
        with mock.patch.object(tf, "MIN_HIST_MONTHS", 13):
            self.fails(hist_text(years=[2012]))                                   # 한 해(12개월)뿐

    def test_garbage_is_a_format_error(self):
        for text in ("", "<html>잠시 후 다시</html>", "Country\t2025\n"):
            self.fails(text)


class ParseHistoryMinimumTest(unittest.TestCase):
    def test_one_year_block_is_enough(self):
        h = tf.parse_history(hist_text(years=[2013]))
        self.assertEqual(sorted(h["months"])[0], "2013-01")
        self.assertEqual(len(h["months"]), 12)


# ---------- 계산 ----------

class ComputeTest(unittest.TestCase):
    def setUp(self):
        self.out = tmpdir(self)

    def test_totals_changes_shares_and_lines(self):
        code, _, d = run(self.out)
        self.assertEqual(code, 0)
        t = table_rows()
        g0, g1, g12 = (t["grand"][j] / 10 for j in (0, 1, 12))
        o0, o1, o12 = (t["official"][j] / 10 for j in (0, 1, 12))
        self.assertEqual((d["month"], d["prev_month"], d["year_ago"], d["month_end"]),
                         ("2026-09", "2026-08", "2025-09", "2026-09-30"))
        self.assertEqual(d["totals"]["grand"], {"name": "해외 전체 보유", "level_bn": g0, "chg_1m_bn": round(g0 - g1, 1),
                                                "chg_12m_bn": round(g0 - g12, 1)})
        self.assertEqual(d["totals"]["official"]["share_pct"], round(o0 / g0 * 100, 1))
        self.assertEqual(d["totals"]["official"]["chg_12m_bn"], round(o0 - o12, 1))
        b0 = t["bills"][0] / 10
        self.assertEqual(d["totals"]["bills_share_of_official_pct"], round(b0 / o0 * 100, 1))
        self.assertEqual(d["lines"]["grand"],
                         f"{round(g0):,}bn · 1개월 {tf._signed(g0 - g1)} · 12개월 {tf._signed(g0 - g12)}")
        self.assertTrue(d["lines"]["official"].startswith(f"{tf._int(o0):,}bn · 전체의 {o0 / g0 * 100:.1f}% · 1개월 "))

    def test_signed_integers_round_half_away_from_zero_and_zero_has_no_sign(self):
        self.assertEqual([tf._signed(v) for v in (-75.5, 2.5, -2.5, 0.4, -0.4, 0.0, 1234.5, None)],
                         ["-76", "+3", "-3", "0", "0", "0", "+1,235", "—"])
        self.assertEqual(tf._signed(9241.2 - 9316.7), "-76")                     # 부동소수 찌꺼기(-75.50000000000091)
        self.assertEqual(tf._level(9241.2), "9,241")

    def test_countries_keep_table_order_with_rank_share_and_line(self):
        _, _, d = run(self.out)
        rows = d["countries"]
        self.assertEqual([r["name_en"] for r in rows], NAMES + ["All Other"])
        self.assertEqual([r["rank"] for r in rows], list(range(1, 21)) + [None])
        jp = rows[0]
        g0 = table_rows()["grand"][0] / 10
        self.assertEqual(jp, {"rank": 1, "name_en": "Japan", "name_ko": "일본", "level_bn": 1200.0,
                              "chg_1m_bn": round(1200.0 - tenths(0, 1) / 10, 1),
                              "chg_12m_bn": round(1200.0 - tenths(0, 12) / 10, 1), "share_pct": round(120000 / g0, 1),
                              "line": jp["line"]})
        self.assertEqual(jp["line"], "1,200bn · 전체의 7.8% · 1개월 0 · 12개월 +8")       # +0.3 · +8.4
        self.assertEqual(rows[-1]["name_ko"], "그 밖")

    def test_rank_follows_the_latest_value_even_if_the_table_order_differs(self):
        t = table_rows()
        t["countries"][0], t["countries"][1] = t["countries"][1], t["countries"][0]
        _, _, d = run(self.out, Route(table=table_text(t)))
        self.assertEqual([r["rank"] for r in d["countries"][:3]], [2, 1, 3])

    def test_korea_row_and_line(self):
        _, _, d = run(self.out)
        k = d["korea"]
        self.assertEqual((k["name_en"], k["name_ko"], k["rank"], k["level_bn"]), ("Korea, South", "한국", 17, 320.0))
        self.assertEqual(d["lines"]["korea"],
                         f"320bn · 17위 · 전체의 {k['share_pct']:.1f}% · 1개월 {tf._signed(k['chg_1m_bn'])} · "
                         f"12개월 {tf._signed(k['chg_12m_bn'])}")

    def test_korea_absent_this_month(self):
        names = NAMES[:16] + ["Germany"] + NAMES[17:]
        _, _, d = run(self.out, Route(table=table_text(table_rows(names=names))))
        self.assertIsNone(d["korea"])
        self.assertIn("없음", d["lines"]["korea"])
        self.assertEqual(d["countries"][16]["name_ko"], "독일")
        pts = d["chart_korea"]["lines"][0]["points"]                         # 그래프는 과거 표까지만, 그 뒤 달은 null
        self.assertEqual(pts[-1], ["2026-09-30", None])
        self.assertEqual(pts[-10][0], "2025-12-31")
        self.assertIsNotNone(pts[-10][1])

    def test_unknown_names_have_no_korean_name(self):
        names = NAMES[:19] + ["Atlantis"]
        _, _, d = run(self.out, Route(table=table_text(table_rows(names=names))))
        self.assertEqual((d["countries"][19]["name_en"], d["countries"][19]["name_ko"]), ("Atlantis", None))

    def test_aliases_map_to_one_name(self):
        for alias in ("South Korea", "Korea", "Korea, Republic of"):
            self.assertEqual(tf.canonical(alias), "Korea, South", alias)
            self.assertEqual(tf.name_ko(alias), "한국")
        self.assertEqual(tf.name_ko("China, Mainland"), "중국 본토")
        self.assertEqual(tf.name_ko("Türkiye"), "튀르키예")
        for nm in NAMES:
            self.assertIsNotNone(tf.name_ko(nm), nm)

    def test_totals_check_mismatch_is_published_with_a_note(self):
        t = table_rows()
        t["other"][3] += 12                                                     # 1.2bn 어긋남(반올림보다 크다)
        code, out, d = run(self.out, Route(table=table_text(t)))
        self.assertEqual(code, 0)
        self.assertTrue(d["ok"])
        self.assertEqual((d["checks"]["sum_ok"], d["checks"]["sum_gap_bn"]), (False, 1.2))
        self.assertIn("1.2bn", d["checks"]["note"])
        self.assertIn("::warning::", out)
        self.assertEqual(d["totals"]["grand"]["level_bn"], t["grand"][0] / 10)   # 값은 표 그대로
        t = table_rows()
        t["other"][3] += 5                                                      # 0.5bn — 반올림 안
        _, _, d = run(tmpdir(self), Route(table=table_text(t)))
        self.assertTrue(d["checks"]["sum_ok"])
        self.assertIsNone(d["checks"]["note"])
        t = table_rows()
        t["bills"][0] += 2
        _, _, d = run(tmpdir(self), Route(table=table_text(t)))
        self.assertEqual((d["checks"]["parts_ok"], d["checks"]["parts_gap_bn"]), (False, 0.2))


# ---------- 그래프 ----------

class ChartTest(unittest.TestCase):
    def setUp(self):
        self.out = tmpdir(self)

    def test_history_then_table5_with_table5_winning_on_overlap(self):
        _, _, d = run(self.out)
        c = d["chart"]
        self.assertEqual(set(c), SPEC_KEYS)
        self.assertTrue(all(set(line) == LINE_KEYS for line in c["lines"]))
        g = c["lines"][0]["points"]
        self.assertEqual(len(g), 178)                                            # 2011-12 … 2026-09
        self.assertEqual(g[0], ["2011-12-31", hist_value("2011-12")["grand"] / 10])
        self.assertEqual(g[2][0], "2012-02-29")                                  # 윤년 말일
        self.assertEqual(g[-1], ["2026-09-30", table_rows()["grand"][0] / 10])
        at = dict(g)
        self.assertEqual(at["2025-09-30"], table_rows()["grand"][12] / 10)       # 겹치는 달 — 표 5
        self.assertEqual(at["2025-08-31"], hist_value("2025-08")["grand"] / 10)  # 표 5 앞 — 과거 표
        o = dict(c["lines"][1]["points"])
        self.assertEqual(o["2025-12-31"], table_rows()["official"][9] / 10)

    def test_country_chart_has_three_lines_and_only_months_where_each_is_present(self):
        _, _, d = run(self.out)
        lines = {line["key"]: line["points"] for line in d["chart_countries"]["lines"]}
        self.assertEqual(list(lines), ["Japan", "United Kingdom", "China, Mainland"])
        self.assertEqual(lines["Japan"][0][0], "2011-12-31")
        self.assertEqual(lines["United Kingdom"][0][0], "2012-01-31")          # 2011-12는 주석 표시 줄('2/')
        self.assertEqual(lines["China, Mainland"][-1], ["2026-09-30", tenths(2, 0) / 10])
        self.assertEqual([x["label"] for x in d["chart_countries"]["lines"]], ["일본", "영국", "중국 본토"])
        # 영국 선이 한 달 늦게 시작하는 까닭은 그 그래프의 덧줄에만(2026-11-19 검토) — 전체 그래프는 그대로
        self.assertEqual(d["chart_countries"]["note"], tf.CHART_NOTE + " · " + tf.UK_NOTE)
        self.assertEqual((d["chart"]["note"], d["chart_korea"]["note"]), (tf.CHART_NOTE, tf.CHART_NOTE))
        self.assertIn("2012년 1월부터", tf.UK_NOTE)
        self.assertIn("2/", tf.UK_NOTE)

    def test_gap_between_history_and_table5_is_filled_by_the_previous_file_else_null(self):
        old = os.path.join(self.out, "old")
        run(old)                                                                 # 직전 파일 — 2026-09까지
        shutil.copy(os.path.join(old, tf.FILE), os.path.join(self.out, tf.FILE))
        # 다음 해 6월: 표 5는 2026-06 … 2027-06, 과거 표는 그대로 2025년까지 — 2026-01 … 2026-05가 빈다
        later = datetime.datetime(2027, 8, 20, tzinfo=datetime.timezone.utc)
        t = table_rows(m0="2027-06")
        _, _, d = run(self.out, Route(table=table_text(t)), now=later)
        at = dict(d["chart"]["lines"][0]["points"])
        prev = dict(load_json(os.path.join(old, tf.FILE))["chart"]["lines"][0]["points"])
        self.assertEqual(at["2026-03-31"], prev["2026-03-31"])                  # 직전 파일(그때의 표 5)
        self.assertEqual(at["2026-06-30"], t["grand"][12] / 10)                 # 지금 표 5
        # 직전 파일이 없으면 그 달들은 null — 곧은 선으로 잇지 않는다
        bare = tmpdir(self)
        _, _, d = run(bare, Route(table=table_text(t)), now=later)
        at = dict(d["chart"]["lines"][0]["points"])
        self.assertEqual([at[tf.month_end(m)] for m in ("2026-01", "2026-05")], [None, None])
        self.assertEqual(len(at), (2027 - 2011) * 12 + 6 - 11)

    def test_a_month_that_leaves_table5_keeps_its_table5_value_until_a_newer_history_file(self):
        """2026-11-19 검토: 13개 달 창에서 빠진 달이 더 옛 과거 표의 값으로 돌아가던 것. 과거 표(9/16/2026)보다 나중에 받은 표 5의
        값은 다음 발표에서 창을 벗어나도 남고, 그보다 새 과거 표가 오면 그때 과거 표가 이긴다."""
        first = table_rows()                                                     # 2026-09 … 2025-09, 받은 날 2026-11-19
        run(self.out)
        d0 = load_json(os.path.join(self.out, tf.FILE))
        self.assertEqual(d0["table_asof"]["grand"]["2025-09"], "2026-11-19")
        self.assertNotIn("2025-08", d0["table_asof"]["grand"])                 # 과거 표에서 온 달은 적지 않는다
        g = lambda d, m: dict(d["chart"]["lines"][0]["points"])[tf.month_end(m)]
        jp = lambda d, m: dict(d["chart_countries"]["lines"][0]["points"])[tf.month_end(m)]
        self.assertNotEqual(first["grand"][12] / 10, hist_value("2025-09")["grand"] / 10)   # 두 값이 다른 달
        # 한 달 뒤 발표 — 2025-09가 창을 벗어난다
        t1 = table_rows(m0="2026-10")
        _, _, d1 = run(self.out, Route(table=table_text(t1)), now=datetime.datetime(2026, 12, 18, tzinfo=datetime.timezone.utc))
        self.assertEqual(g(d1, "2025-09"), first["grand"][12] / 10)               # 과거 표의 옛 값으로 돌아가지 않는다
        self.assertEqual(jp(d1, "2025-09"), tenths(0, 12) / 10)
        self.assertEqual(d1["table_asof"]["grand"]["2025-09"], "2026-11-19")
        self.assertEqual(d1["table_asof"]["grand"]["2025-10"], "2026-12-18")
        self.assertEqual(g(d1, "2025-08"), hist_value("2025-08")["grand"] / 10)  # 표 5에 없던 달은 그대로 과거 표
        # 두 달 뒤 — 2025-10도 창을 벗어나고, 둘 다 표 5의 값
        t2 = table_rows(m0="2026-11")
        _, _, d2 = run(self.out, Route(table=table_text(t2)), now=datetime.datetime(2027, 1, 19, tzinfo=datetime.timezone.utc))
        self.assertEqual((g(d2, "2025-09"), g(d2, "2025-10")), (first["grand"][12] / 10, t1["grand"][12] / 10))
        # 그보다 새 과거 표(2027-01-20) — 과거 표가 이기고 그 달들의 받은 날을 지운다
        _, _, d3 = run(self.out, Route(table=table_text(t2), hist=hist_text(date="1/20/2027")),
                       now=datetime.datetime(2027, 1, 21, tzinfo=datetime.timezone.utc))
        self.assertEqual((g(d3, "2025-09"), g(d3, "2025-10")),
                         (hist_value("2025-09")["grand"] / 10, hist_value("2025-10")["grand"] / 10))
        self.assertNotIn("2025-09", d3["table_asof"]["grand"])
        self.assertEqual(g(d3, "2025-11"), t2["grand"][12] / 10)                  # 지금 표 5의 달은 늘 표 5

    def test_an_older_previous_file_without_table_asof_still_keeps_its_table5_months(self):
        """table_asof가 없던 파일(2026-11-19 첫 판)을 직전 파일로 두어도 그 원표의 달은 그 원표를 받은 날로 본다."""
        first = table_rows()
        run(self.out)
        path = os.path.join(self.out, tf.FILE)
        d0 = load_json(path)
        del d0["table_asof"]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(d0, f, ensure_ascii=False)
        _, _, d1 = run(self.out, Route(table=table_text(table_rows(m0="2026-10"))),
                       now=datetime.datetime(2026, 12, 18, tzinfo=datetime.timezone.utc))
        self.assertEqual(dict(d1["chart"]["lines"][0]["points"])["2025-09-30"], first["grand"][12] / 10)
        # 꼴이 어긋난 table_asof 칸은 버린다(날짜·달 꼴이 아니면 그 칸만)
        d1["table_asof"] = {"grand": {"2025-09": "어제", "x": "2026-11-19"}, "official": "x", "7": {"2025-08": "2026-11-19"}}
        self.assertEqual(tf.prev_asof(d1, None), {"7": {"2025-08": "2026-11-19"}})


# ---------- 실패 · 이어 싣기 ----------

class FailureTest(unittest.TestCase):
    def setUp(self):
        self.out = tmpdir(self)

    def first(self):
        code, _, d = run(self.out)
        self.assertEqual(code, 0)
        return d

    def test_table_fails_without_previous_writes_status_only(self):
        code, out, d = run(self.out, Route(table=OSError("down")))
        self.assertEqual(code, 1)
        self.assertEqual((d["ok"], d["stale"], d["error"], d["failed_since"]), (False, False, "수신 실패", "2026-11-19"))
        self.assertNotIn("totals", d)
        self.assertNotIn("chart", d)
        self.assertIn("::warning::TIC 해외 보유 표 5 받지 못함: 수신 실패", out)
        self.assertTrue(d["history"]["ok"])

    def test_table_fails_with_previous_keeps_numbers_as_stale_and_failed_since_holds(self):
        before = self.first()
        nxt = NOW + datetime.timedelta(days=1)
        code, out, d = run(self.out, Route(table=OSError("down")), now=nxt)
        self.assertEqual(code, 1)
        self.assertEqual((d["ok"], d["stale"], d["failed_since"], d["retrieved"]), (False, True, "2026-11-20", "2026-11-19"))
        for k in ("month", "totals", "countries", "korea", "lines", "chart", "chart_countries", "table"):
            self.assertEqual(d[k], before[k], k)
        self.assertIn("직전 값(2026-09 월말) 유지", out)
        code, _, d = run(self.out, Route(table=OSError("down")), now=nxt + datetime.timedelta(days=3))
        self.assertEqual(d["failed_since"], "2026-11-20")                         # 못 받기 시작한 날을 지킨다
        code, _, d = run(self.out, now=nxt + datetime.timedelta(days=4))         # 다시 받으면 지운다
        self.assertEqual((code, d["ok"], d["stale"], d["failed_since"]), (0, True, False, None))

    def test_history_fails_table_ok_uses_previous_chart_points(self):
        before = self.first()
        code, out, d = run(self.out, Route(hist="<html>점검 중</html>"), now=NOW + datetime.timedelta(days=1))
        self.assertEqual(code, 0)
        self.assertTrue(d["ok"])
        self.assertEqual(d["history"], {"ok": False, "stale": True, "error": "형식이 다름(표를 읽지 못함)",
                                        "failed_since": "2026-11-20", "file_date": "2026-09-16", "last_month": "2025-12"})
        self.assertEqual(d["chart"], before["chart"])
        self.assertEqual(d["chart_countries"], before["chart_countries"])
        self.assertIn("::warning::TIC 과거 표 받지 못함: 형식이 다름(표를 읽지 못함) — 직전 그래프 점 유지", out)

    def test_history_fails_without_previous_charts_only_table5_months(self):
        code, _, d = run(self.out, Route(hist=OSError("down")))
        self.assertEqual(code, 0)
        self.assertEqual((d["history"]["ok"], d["history"]["stale"]), (False, False))
        self.assertEqual(len(d["chart"]["lines"][0]["points"]), 13)

    def test_both_fail_with_previous(self):
        before = self.first()
        code, _, d = run(self.out, Route(table=OSError("x"), hist=OSError("y")), now=NOW + datetime.timedelta(days=1))
        self.assertEqual((code, d["ok"], d["stale"], d["history"]["ok"]), (1, False, True, False))
        self.assertEqual(d["chart"], before["chart"])
        self.assertEqual(d["totals"], before["totals"])

    def test_malformed_and_out_of_range_tables_keep_previous(self):
        before = self.first()
        for body, err in (("garbage", "형식이 다름(표를 읽지 못함)"),
                          (table_text({**table_rows(), "grand": [g * 1000 for g in table_rows()["grand"]]}),
                           "값이 범위 밖(단위나 열을 잘못 읽었을 수 있음)")):
            code, _, d = run(self.out, Route(table=body), now=NOW + datetime.timedelta(days=1))
            self.assertEqual((code, d["ok"], d["stale"], d["error"]), (1, False, True, err))
            self.assertEqual(d["totals"], before["totals"])

    def test_a_table_older_than_the_previous_one_is_refused(self):
        self.first()
        code, _, d = run(self.out, Route(table=table_text(table_rows(m0="2026-08"))), now=NOW + datetime.timedelta(days=1))
        self.assertEqual((code, d["ok"], d["stale"], d["error"], d["month"]),
                         (1, False, True, "받은 자료가 직전 자료보다 오래됨", "2026-09"))

    def test_a_history_older_than_the_previous_one_is_refused(self):
        self.first()
        code, _, d = run(self.out, Route(hist=hist_text(years=range(2024, 2008, -1))), now=NOW + datetime.timedelta(days=1))
        self.assertEqual((code, d["history"]["ok"], d["history"]["error"]), (0, False, "받은 자료가 직전 자료보다 오래됨"))
        self.assertEqual(d["history"]["last_month"], "2025-12")

    def test_a_revised_table_for_the_same_month_is_taken(self):
        self.first()
        t = table_rows()
        t["countries"][0][1][1] += 3
        t["other"][1] -= 3
        code, _, d = run(self.out, Route(table=table_text(t)), now=NOW + datetime.timedelta(days=1))
        self.assertEqual((code, d["ok"], d["retrieved"]), (0, True, "2026-11-20"))
        self.assertEqual(d["countries"][0]["chg_1m_bn"], round(1200.0 - (tenths(0, 1) + 3) / 10, 1))

    def test_broken_previous_files_mean_no_previous(self):
        good = self.first()
        path = os.path.join(self.out, tf.FILE)
        for broken in ("{깨짐", json.dumps({**good, "schema": 2}),
                       json.dumps({**good, "table": {**good["table"], "grand": ["9241.2"] + good["table"]["grand"][1:]}}),
                       json.dumps({**good, "retrieved": "어제"})):
            with open(path, "w", encoding="utf-8") as f:
                f.write(broken)
            code, _, d = run(self.out, Route(table=OSError("x")), now=NOW + datetime.timedelta(days=1))
            self.assertEqual((code, d["ok"], d["stale"]), (1, False, False))
            self.assertNotIn("totals", d)

    def test_redirects_oversize_and_truncation_are_fetch_failures(self):
        clock = Clock()
        for final in ("https://example.org/x", "http://ticdata.treasury.gov/x"):
            r = Route(final={tf.TABLE_URL: final})
            with self.assertRaises(tf.TicError) as e:
                tf.fetch_bytes(tf.TABLE_URL, 1e9, clock, r)
            self.assertEqual(e.exception.code, "fetch")
        with mock.patch.object(tf, "MAX_BYTES", 100), self.assertRaises(tf.TicError):
            tf.fetch_bytes(tf.TABLE_URL, 1e9, clock, Route())
        with self.assertRaises(tf.TicError):
            tf.fetch_bytes("https://example.org/slt_table5.txt", 1e9, clock, Route())   # 다른 호스트는 묻지도 않는다
        body = table_text().encode()

        def http_response(cut):
            class Sock:
                def makefile(self, mode):
                    return io.BytesIO(b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n" % len(body) + body[:len(body) - cut])
            resp = http.client.HTTPResponse(Sock())
            resp.begin()
            resp.url = tf.TABLE_URL
            return resp
        self.assertEqual(tf.fetch_bytes(tf.TABLE_URL, 1e9, clock, lambda req, timeout: http_response(0)), body)
        with self.assertRaises(tf.TicError) as e:
            tf.fetch_bytes(tf.TABLE_URL, 1e9, clock, lambda req, timeout: http_response(40))
        self.assertEqual(e.exception.code, "fetch")

    def test_the_request_names_the_project_without_contact_details(self):
        r = Route()
        run(self.out, r)
        self.assertEqual([c[0] for c in r.calls], [tf.TABLE_URL, tf.HIST_URL])
        ua = r.calls[0][2]
        self.assertTrue(ua.startswith("macro-regime-check/"))
        self.assertNotIn("@", ua)


# ---------- 같은 내용 · 예산 · 캐시 ----------

class RunTest(unittest.TestCase):
    def setUp(self):
        self.out = tmpdir(self)

    def test_unchanged_content_is_not_rewritten_and_retrieved_holds(self):
        run(self.out)
        path = os.path.join(self.out, tf.FILE)
        os.utime(path, (1, 1))
        code, _, d = run(self.out, now=NOW + datetime.timedelta(days=2))
        self.assertEqual(code, 0)
        self.assertEqual(os.stat(path).st_mtime, 1)                              # 다시 쓰지 않았다
        self.assertEqual(d["retrieved"], "2026-11-19")
        self.assertEqual(sorted(os.listdir(self.out)), sorted([tf.FILE, "_work"]))   # .tmp가 남지 않는다

    def test_per_request_timeout_is_min_of_timeout_and_the_remaining_budget(self):
        clock = Clock()
        r = Route(clock=clock, cost=30.0)
        run(self.out, r, clock=clock)
        self.assertEqual([c[1] for c in r.calls], [tf.TIMEOUT, tf.BUDGET - 30.0])

    def test_an_exhausted_budget_skips_the_second_request(self):
        clock = Clock()
        r = Route(clock=clock, cost=tf.BUDGET - 0.5)
        code, out, d = run(self.out, r, clock=clock)
        self.assertEqual(len(r.calls), 1)                                       # 과거 표는 남은 0.5초로 묻지 않는다
        self.assertEqual((code, d["ok"]), (0, True))
        self.assertEqual(d["history"]["error"], "수신 시간 상한")
        r = Route(clock=clock, cost=tf.BUDGET + 1)                               # 응답이 마감 뒤에 왔다 — 읽은 것을 버린다
        clock.t = 0.0
        code, _, d = run(tmpdir(self), r, clock=clock)
        self.assertEqual((code, d["error"]), (1, "수신 시간 상한"))
        r = Route()
        code, _, d = run(tmpdir(self), r, argv=["--budget", "0.5"])
        self.assertEqual((code, r.calls, d["error"]), (1, [], "수신 시간 상한"))

    def test_a_hanging_request_is_cut_at_the_hard_cap(self):
        release = threading.Event()
        self.addCleanup(release.set)

        def hang(req, timeout=None):
            release.wait(10)
            raise OSError("late")
        t0 = time.monotonic()
        code, _, d = run(self.out, hang, argv=["--budget", "1.6"])
        self.assertLess(time.monotonic() - t0, 5)
        self.assertEqual((code, d["error"], d["history"]["error"]), (1, "수신 시간 상한", "수신 시간 상한"))

    def test_offline_reads_the_cache_written_by_an_online_run(self):
        work = os.path.join(self.out, "_work")
        _, _, online = run(self.out)
        self.assertEqual(sorted(os.listdir(os.path.join(work, "tic"))), ["mfhhis01.txt", "slt_table5.txt"])
        other = tmpdir(self)
        r = Route()
        code, _, offline = run(other, r, argv=["--offline"], work=work)
        self.assertEqual((code, r.calls), (0, []))
        strip = lambda d: {k: v for k, v in d.items() if k != "generated_at"}
        self.assertEqual(strip(offline), strip(online))
        code, _, d = run(tmpdir(self), Route(), argv=["--offline"], work=os.path.join(other, "none"))
        self.assertEqual((code, d["error"]), (1, "수신 실패"))

    def test_a_cache_is_not_written_for_a_file_that_did_not_parse(self):
        work = os.path.join(self.out, "_work")
        run(self.out, Route(table="garbage"))
        self.assertEqual(os.listdir(os.path.join(work, "tic")), ["mfhhis01.txt"])

    def test_a_write_failure_returns_1(self):
        with mock.patch.object(tf, "write", side_effect=OSError("disk")):
            code, _, _ = run(self.out)
        self.assertEqual(code, 1)


# ---------- 문구 원칙 · 꼴 ----------

class TextTest(unittest.TestCase):
    def test_no_verdict_words_no_email_and_only_fixed_error_texts(self):
        out = tmpdir(self)
        _, _, ok = run(out)
        _, _, stale = run(out, Route(table=OSError("secret-host-detail"), hist=OSError("x")),
                          now=NOW + datetime.timedelta(days=1))
        for d in (ok, stale):
            text = "\n".join(strings(d))
            for w in FORBIDDEN_TEXT + VERDICT:
                self.assertNotIn(w, text, w)
            self.assertNotIn("@", text)
            self.assertNotIn("secret-host-detail", text)
            self.assertFalse(set(re.findall(r"https?://([\w.-]+)", text)) - {tf.HOST, "ticdata.treasury.gov"})
        self.assertIn(stale["error"], tf.REASONS.values())
        self.assertIn(stale["history"]["error"], tf.REASONS.values())

    def test_contract_keys(self):
        _, _, d = run(tmpdir(self))
        for k in ("schema", "generated_at", "ok", "stale", "error", "failed_since", "retrieved", "month", "prev_month",
                  "year_ago", "totals", "countries", "korea", "lines", "chart", "chart_countries", "source", "notices",
                  "release_note"):
            self.assertIn(k, d)
        self.assertEqual(set(d["totals"]), {"grand", "official", "official_bills", "official_notes_bonds",
                                            "bills_share_of_official_pct"})
        # share_pct는 어디서나 해외 전체 대비 — 단기채의 공적 대비 비중은 bills_share_of_official_pct 한 곳에만(2026-11-19 검토)
        self.assertEqual(set(d["totals"]["official_bills"]), {"name", "level_bn", "chg_1m_bn", "chg_12m_bn"})
        self.assertEqual(set(d["totals"]["official_notes_bonds"]), {"name", "level_bn", "chg_1m_bn", "chg_12m_bn"})
        self.assertNotIn("share_pct", d["totals"]["grand"])
        self.assertEqual([d["totals"][k]["name"] for k in ("official_bills", "official_notes_bonds")],
                         ["공적 중 단기채(T-bill)", "공적 중 이표채(T-note · T-bond)"])
        self.assertEqual(set(d["table_asof"]), {"grand", "official", "Japan", "United Kingdom", "China, Mainland",
                                                "Korea, South"})
        self.assertEqual(set(d["source"]) >= {"table", "history", "name"}, True)
        self.assertEqual(d["source"]["table"], tf.TABLE_URL)
        self.assertRegex(d["source"]["citation"], r"retrieved from https://ticdata\.treasury\.gov/.*, November 19, 2026\.$")
        self.assertTrue(any("not affiliated" in n for n in d["notices"]))
        self.assertTrue(any("실제 주인" in n for n in d["notices"]))
        # 화면이 따로 적는 단서는 고지 칸이 아니라 caveats에(2026-11-19 통합) — 평가 기준은 양식 이름까지만
        self.assertEqual(len(d["notices"]), 4)
        self.assertTrue(any("순매입이 아니다" in n for n in d["caveats"]))
        self.assertTrue(any("추정치다" in n for n in d["caveats"]))
        self.assertFalse(any("공정가치" in n or "시장가" in n for n in d["notices"] + d["caveats"]))
        for ch in ("chart", "chart_countries", "chart_korea"):
            self.assertEqual(set(d[ch]), SPEC_KEYS, ch)
            for line in d[ch]["lines"]:
                self.assertEqual(set(line), LINE_KEYS)
                self.assertTrue(all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", p[0]) and p[0] == tf.month_end(p[0][:7])
                                    for p in line["points"]))

    def test_the_committed_file_re_presents_identically(self):
        """저장소의 data/tic.json(실자료)을 직전 파일로 두고 두 파일을 다 못 받았다고 하면 같은 숫자·그래프가 다시 나온다 —
        원표(table)와 그래프 점만으로 화면의 모든 숫자를 다시 만들 수 있다."""
        path = os.path.join(REPO, "data", tf.FILE)
        if not os.path.exists(path):
            self.skipTest("data/tic.json 없음")
        prev = load_json(path)
        if not prev.get("ok"):
            self.skipTest("저장소의 tic.json이 실패 상태")
        today = datetime.date.fromisoformat(prev["retrieved"])
        now = datetime.datetime.combine(today, datetime.time(1), datetime.timezone.utc)
        d = tf.build(tf.TicError("fetch"), tf.TicError("fetch"), prev, now)
        # 숫자만 견준다 — 문구(lines·line·notices)는 코드를 고치면 다음 실행에서 바뀌므로 저장된 글과 묶지 않는다
        nums = lambda rows: [{k: v for k, v in r.items() if k != "line"} for r in rows]
        self.assertEqual((d["month"], d["totals"], d["table"], d["checks"]["sum_gap_bn"]),
                         (prev["month"], prev["totals"], prev["table"], prev["checks"]["sum_gap_bn"]))
        self.assertEqual(nums(d["countries"]), nums(prev["countries"]))
        for k in ("chart", "chart_countries", "chart_korea"):
            self.assertEqual([x["points"] for x in d[k]["lines"]], [x["points"] for x in prev[k]["lines"]], k)


class RealFilesTest(unittest.TestCase):
    """실제 파일(미 재무부에서 받은 두 원문)이 있으면 읽어 본다 — TIC_REAL_DIR 또는 .work/tic/. 없으면 건너뛴다."""
    def setUp(self):
        for d in (os.environ.get("TIC_REAL_DIR"), os.path.join(REPO, ".work", "tic")):
            if d and all(os.path.exists(os.path.join(d, n)) for n in (tf.TABLE_CACHE, tf.HIST_CACHE)):
                self.dir = d
                return
        self.skipTest("실제 TIC 원문 없음(TIC_REAL_DIR 또는 .work/tic/)")

    def read(self, name):
        with open(os.path.join(self.dir, name), "rb") as f:
            return tf._decode(f.read())

    def test_real_files_parse_and_add_up(self):
        # 오늘 날짜로 읽는다 — 고정한 TODAY(2026-11-19)로 읽으면 다음 해 2월 18일 무렵 받은 표(2026-12 자료)가 '미래 달'로 막힌다
        t = tf.parse_table(self.read(tf.TABLE_CACHE), datetime.date.today())
        h = tf.parse_history(self.read(tf.HIST_CACHE))
        self.assertEqual(len(t["countries"]), 20)
        self.assertEqual(len(t["months"]), 13)
        self.assertTrue(tf.checks_of(t)["sum_ok"] and tf.checks_of(t)["parts_ok"])
        self.assertEqual(min(h["months"]), "2011-12")
        for name in ("Japan", "United Kingdom", "China, Mainland"):
            self.assertIn(name, [tf.canonical(r[0]) for r in t["countries"]])
        self.assertTrue(all(tf.name_ko(r[0]) for r in t["countries"]))         # 표의 모든 나라에 한국어 이름
        if t["months"][0] == "2026-09":                                        # 2026-11-18 발표분 — 손으로 다시 셈한 값
            self.assertEqual((t["grand"][0], t["official"][0]), (9241.2, 3674.7))
            self.assertEqual((round(t["grand"][0] - t["grand"][1], 1), round(t["grand"][0] - t["grand"][12], 1)), (-75.5, 3.0))
            korea = dict((tf.canonical(r[0]), r[1]) for r in t["countries"])["Korea, South"]
            self.assertEqual((korea[0], korea[1], korea[12]), (139.9, 134.2, 142.7))
            self.assertEqual(h["months"]["2025-09"]["grand"], 9237.5)          # 과거 표 — 표 5(9238.2)와 개정만큼 다르다
            pts = tf.present(t, h["months"], {}, {"ok": True}, "2026-11-19")["chart"]["lines"][0]["points"]
            self.assertEqual((len(pts), pts[0], pts[-1]), (178, ["2011-12-31", 5004.4], ["2026-09-30", 9241.2]))
            # 검토 재현(2026-11-19): 한 달 밀린 표 5(2026-10 맨 앞 · 2025-09 빠짐)를 이 파일 위에 받아도 2025-09는 표 5의 9238.2
            now = datetime.datetime(2026, 11, 19, 1, tzinfo=datetime.timezone.utc)
            d0 = tf.build(t, h, {}, now)
            shifted = {"months": ["2026-10"] + t["months"][:-1], "countries": [[n, [v[0]] + v[:-1]] for n, v in t["countries"]],
                       **{k: [t[k][0]] + t[k][:-1] for k in ("other", "grand", "official", "official_bills",
                                                              "official_notes_bonds")}}
            d1 = tf.build(shifted, h, json.loads(json.dumps(d0)), datetime.datetime(2026, 12, 18, tzinfo=datetime.timezone.utc))
            at = dict(d1["chart"]["lines"][0]["points"])
            self.assertEqual((at["2025-09-30"], at["2025-10-31"], at["2025-12-31"]), (9238.2, 9231.3, 9270.5))
            uk = dict(d1["chart_countries"]["lines"][1]["points"])
            self.assertEqual(uk["2025-12-31"], 863.2)                         # 과거 표 863.1



class StaticTest(unittest.TestCase):
    """워크플로·README·화면 연결(2026-11-19 통합) — 다른 참고 단계와 같은 원칙인지 글만 읽어 본다."""
    def read(self, *parts):
        with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
            return f.read()

    def test_workflow_fetches_without_failing_the_run(self):
        wf = self.read(".github", "workflows", "daily.yml")
        self.assertIn("id: tic\n", wf, "daily.yml에 재무부 TIC 단계(id: tic) 없음")
        step = wf[wf.index("id: tic\n"):]
        self.assertIn("continue-on-error: true", step[:200])
        self.assertIn("timeout-minutes: 2", step[:200])
        self.assertIn("python scripts/tic_fetch.py", step[:300])
        self.assertLess(wf.index("id: supply"), wf.index("id: tic\n"))                     # 같은 카드의 주간 부분 바로 다음
        self.assertLess(wf.index("id: tic\n"), wf.index("id: ai_invest"))
        self.assertLess(wf.index("id: tic\n"), wf.index("공개 전 검사(새 산출물 포함)"))       # 새 파일도 검사를 거쳐
        self.assertLess(wf.index("id: tic\n"), wf.index("git add data"))                   # 봇 커밋에 실린다
        alert = wf[wf.index("\n  alert:"):]
        self.assertNotIn("tic", alert)                                                    # 실패해도 알림을 띄우지 않는다
        outputs = wf[wf.index("    outputs:", wf.index("\n  update:")):wf.index("    steps:", wf.index("\n  update:"))]
        self.assertNotIn("tic", outputs)
        self.assertIn("node --test scripts/test_supply_card_render.cjs", wf[wf.index("\n  check:"):wf.index("\n  update:")])
        # 단계 전체 상한(BUDGET)이 단계 제한(2분) 안에 든다
        self.assertLess(tf.BUDGET + 30, 120)

    def test_readme_counts_and_section(self):
        readme = self.read("README.md")
        m = re.search(r"\*\*아침 쪽 Python 테스트 (\d+)개 \+ node 테스트 (\d+)개\*\*\((.*?)\)와 \*\*저녁판", readme)
        py_part, node_part = m.group(3).split(" / node: ")
        mine = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()
        self.assertRegex(py_part, rf"(^| · )재무부 TIC 해외 보유 참고 {mine}( · |$)")
        cjs = len(re.findall(r"^test\(", self.read("scripts", "test_supply_card_render.cjs"), flags=re.M))
        self.assertRegex(node_part, rf"(^| · )미 국채 수급 카드 그리기 {cjs}( · |$)")
        self.assertIn("## 참고: 재무부 TIC 해외 보유", readme)
        sec = readme[readme.index("## 참고: 재무부 TIC 해외 보유"):]
        sec = sec[:sec.index("\n## ", 5)]
        for word in (tf.TABLE_URL, tf.HIST_URL, "WMTSECL1", "순매입", "18일", "2011-12", "공공 영역", "운영자 결정"):
            self.assertIn(word, sec, word)
        self.assertIn("python -X utf8 scripts/tic_fetch.py --out .work/public", readme)
        self.assertIn("python -X utf8 scripts/test_tic_fetch.py", readme)
        self.assertIn("node --test scripts/test_supply_card_render.cjs", readme)

    def test_page_reads_the_file_and_names_the_source(self):
        page = self.read("site", "index.html")
        self.assertIn('getJson("data/tic.json")', page)
        self.assertIn('<a href="data/tic.json">tic.json</a>', page)                       # 꼬리말 '원자료' 줄
        card = self.read("site", "supply.js")
        self.assertIn(tf.SOURCE_NAME, card)                                               # 출처 이름이 자료 파일과 같다
        self.assertNotIn("ticdata.treasury.gov/", card.split("const SOURCE_AT")[0].split("window.SupplyCard")[1])
        import render_public as rp
        self.assertIn("미 재무부 TIC", rp.DATA_LICENSE)                                     # 꼬리말 자료 이용 조건


if __name__ == "__main__":
    unittest.main()
