#!/usr/bin/env python3
"""읽기 노트의 정적 그래프 자료(notes_charts) 테스트 — 자료 조건을 닫힌 쪽으로 지키는지, 연평균 전년비를 맞게 계산하는지.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — 지어낸 숫자와 FRED 계열 쪽 뼈대만 흉내 낸 합성 HTML을 쓴다.
끝의 RepoTest는 저장소에 실린 data/notes_charts.json(손으로 돌려 받아 둔 값)의 꼴을 본다.
"""
import os, sys, io, json, math, shutil, datetime, tempfile, unittest, contextlib, urllib.error

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import notes_charts as nc

REPO = os.path.dirname(SCRIPTS)
D = datetime.date
DAY = D(2026, 10, 8)
FREE, CITED, CLOSED = ("Public Domain: Citation Requested", "Copyrighted: Citation Required",
                       "Copyrighted: Pre-approval Required")
CHART_KEYS = {"key", "title", "unit", "zero", "note", "source_note", "retrieved", "notices", "series", "lines"}


def monthly(first, last, growth=0.02, skip=(), until=12):
    """지어낸 월별 지수 — 해마다 growth만큼 오르고 달마다 조금씩 다르다. skip의 (해, 달)은 뺀다. 마지막 해는 until월까지."""
    return [(D(y, m, 1), 100 * (1 + growth) ** (y - first) * (1 + m / 100))
            for y in range(first, last + 1) for m in range(1, (until if y == last else 12) + 1) if (y, m) not in skip]


def yearly_rows(first, last, value=lambda y: 0.5):
    return [(D(y, 1, 1), value(y)) for y in range(first, last + 1)]


def csv_of(series, sid="X"):
    return f"observation_date,{sid}\n" + "".join(f"{d.isoformat()},{v}\n" for d, v in series)


def page(*tags, body=""):
    metas = "".join(f'<meta name="series-tag" content="{t}">' for t in tags)
    return f"<html><head><title>지어낸 계열</title>{metas}</head><body><p>{body}</p></body></html>"


class FakeOpener:
    """urlopen 대역 — 주소별 본문을 돌려주고 부른 주소를 적는다. 없는 주소는 404."""
    def __init__(self, pages):
        self.pages, self.calls = dict(pages), []

    def __call__(self, url, timeout=None):
        self.calls.append((url, timeout))
        if url not in self.pages:
            raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
        return contextlib.closing(io.BytesIO(self.pages[url].encode("utf-8")))


def site(jp_mark=FREE.lower(), us_mark=FREE.lower(), jp_last=2025, us=None, check=None):
    us = us if us is not None else monthly(1990, 2026, skip={(2025, 10)}, until=8)
    check = check if check is not None else yearly_rows(1990, 2024, lambda y: 2.0)
    return {nc.FRED_PAGE.format(nc.JP): page("annual", jp_mark), nc.FRED_PAGE.format(nc.US): page(us_mark, "monthly"),
            nc.FRED_CSV.format(sid=nc.JP): csv_of(yearly_rows(1960, jp_last, lambda y: (y % 7) / 4 - 0.5)),
            nc.FRED_CSV.format(sid=nc.US): csv_of(us),
            nc.FRED_CSV.format(sid=nc.US_CHECK): csv_of(check)}


class MarkTest(unittest.TestCase):
    def test_reads_the_copyright_tag_of_the_series_page(self):
        for mark in (FREE, CITED, CLOSED):
            self.assertEqual(nc.copyright_mark(page("monthly", mark.lower(), "nation")), mark)
            self.assertEqual(nc.copyright_mark(page(mark)), mark)                      # 대소문자는 가리지 않는다

    def test_missing_or_conflicting_marks_count_as_unknown(self):
        self.assertIsNone(nc.copyright_mark(page("monthly", "nation")))
        self.assertIsNone(nc.copyright_mark(page(FREE.lower(), CLOSED.lower())))
        self.assertIsNone(nc.copyright_mark(page("monthly", body=FREE)))            # 본문에 적힌 글은 표시가 아니다
        self.assertIsNone(nc.copyright_mark(""))


class AnnualTest(unittest.TestCase):
    def test_year_average_against_the_year_before(self):
        got = nc.annual_change(monthly(2000, 2003, growth=0.02))
        self.assertEqual(sorted(got), [2001, 2002, 2003])                             # 첫 해는 견줄 전 해가 없다
        for y in got:
            self.assertAlmostEqual(got[y][0], 2.0, places=9)
            self.assertEqual(got[y][1], 12)

    def test_only_months_present_in_both_years_are_compared(self):
        # 2002-10이 없으면 2002년과 2003년 모두 10월을 빼고 같은 달끼리 견준다 — 달 구성이 달라 값이 틀어지지 않게
        got = nc.annual_change(monthly(2000, 2003, growth=0.02, skip={(2002, 10)}))
        self.assertEqual((got[2002][1], got[2003][1], got[2001][1]), (11, 11, 12))
        self.assertAlmostEqual(got[2002][0], 2.0, places=9)
        self.assertAlmostEqual(got[2003][0], 2.0, places=9)

    def test_years_with_too_few_months_are_left_out(self):
        self.assertNotIn(2003, nc.annual_change(monthly(2000, 2003, until=8)))        # 덜 끝난 해
        self.assertNotIn(2002, nc.annual_change(monthly(2000, 2003, skip={(2002, 3), (2002, 4)})))
        self.assertIn(2003, nc.annual_change(monthly(2000, 2003, until=11)))
        self.assertEqual(nc.annual_change([]), {})

    def test_yearly_reads_annual_rows(self):
        self.assertEqual(nc.yearly(yearly_rows(2023, 2025, lambda y: y - 2020.5)), {2023: 2.5, 2024: 3.5, 2025: 4.5})


class RefusalTest(unittest.TestCase):
    def test_usable_series_have_no_reason(self):
        self.assertIsNone(nc.refusal("X", FREE, 2025))
        self.assertIsNone(nc.refusal("X", CITED, 2026))

    def test_closed_unknown_or_stale_series_are_refused(self):
        self.assertIn("Pre-approval", nc.refusal("X", CLOSED, 2026))
        self.assertIn("확인", nc.refusal("X", None, 2026))
        self.assertIn("2025", nc.refusal("X", FREE, 2024))
        self.assertIsNotNone(nc.refusal("X", FREE, None))
        self.assertIsNotNone(nc.refusal("X", "Some New Label", 2026))


class CrossCheckTest(unittest.TestCase):
    def test_largest_gap_over_the_shared_years(self):
        mine = {y: (2.0, 12) for y in range(1990, 2026)}
        ref = {**{y: 2.0 for y in range(1990, 2025)}, 2010: 2.031}
        self.assertEqual(nc.crosscheck(mine, ref), {"first": nc.START, "last": 2024, "max": 0.04})   # 올림 — 작게 적지 않는다

    def test_too_few_shared_years_is_no_check(self):
        self.assertIsNone(nc.crosscheck({2024: (2.0, 12)}, {2024: 2.0}))
        self.assertIsNone(nc.crosscheck({}, {}))


def built():
    jp = {y: (y % 7) / 4 - 0.5 for y in range(1960, 2026)}
    us = nc.annual_change(monthly(1990, 2026, skip={(2025, 10)}, until=8))
    return nc.build(jp, us, {nc.JP: FREE, nc.US: FREE}, DAY, {"first": 1995, "last": 2024, "max": 0.04})


class BuildTest(unittest.TestCase):
    def test_shape(self):
        c = built()
        self.assertEqual(set(c), CHART_KEYS)
        self.assertEqual((c["key"], c["unit"], c["zero"], c["retrieved"]), ("cpi_jp_us", "%", True, "2026-10-08"))
        self.assertEqual([(ln["key"], ln["series"], ln["computed"]) for ln in c["lines"]],
                         [("jp", [nc.JP], False), ("us", [nc.US], True)])
        for ln in c["lines"]:
            self.assertEqual(set(ln), {"key", "label", "series", "computed", "points"})
            self.assertEqual([p[0] for p in ln["points"]], list(range(nc.START, 2026)))   # 1995년부터, 해마다 하나
            for year, value in ln["points"]:
                self.assertIs(type(year), int)
                self.assertEqual(value, round(value, 2))
        self.assertEqual(c["lines"][0]["points"][0], [1995, (1995 % 7) / 4 - 0.5])        # 일본은 받은 값 그대로
        self.assertEqual(c["lines"][1]["points"][-1], [2025, 2.0])                        # 미국은 계산값(11개 달)

    def test_source_marks_and_citations_travel_with_the_points(self):
        c = built()
        self.assertEqual([(s["id"], s["mark"], s["url"]) for s in c["series"]],
                         [(nc.JP, FREE, "https://fred.stlouisfed.org/series/" + nc.JP),
                          (nc.US, FREE, "https://fred.stlouisfed.org/series/" + nc.US)])
        self.assertEqual(c["series"][0]["citation"],
                         "World Bank, Inflation, consumer prices for Japan [FPCPITOTLZGJPN], retrieved from FRED, "
                         "Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/FPCPITOTLZGJPN, October 8, 2026.")
        self.assertIn("U.S. Bureau of Labor Statistics", c["series"][1]["citation"])
        self.assertIn("via FRED", c["source_note"])
        self.assertIn("2026-10-08에 받은 값", c["source_note"])
        self.assertIn("계산", c["source_note"])                                            # 계산한 선이라는 표시
        text = " ".join(c["notices"])
        for part in ("2025년", "11개 달", "FPCPITOTLZGUSA", "0.04%p", FREE, "retrieved from FRED"):
            self.assertIn(part, text)

    def test_full_years_need_no_partial_year_notice(self):
        us = nc.annual_change(monthly(1990, 2025))
        c = nc.build({y: 0.5 for y in range(1990, 2026)}, us, {nc.JP: FREE, nc.US: CITED}, DAY,
                     {"first": 1995, "last": 2024, "max": 0.01})
        self.assertNotIn("개 달", " ".join(c["notices"]))
        self.assertIn(CITED, " ".join(c["notices"]))

    def test_inputs_are_not_changed(self):
        jp, us = {y: 0.5 for y in range(1990, 2026)}, nc.annual_change(monthly(1990, 2025))
        before = (dict(jp), dict(us))
        nc.build(jp, us, {nc.JP: FREE, nc.US: FREE}, DAY, {"first": 1995, "last": 2024, "max": 0.01})
        self.assertEqual((jp, us), before)


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.path = os.path.join(self.tmp, "notes_charts.json")

    def run_main(self, opener):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            rc = nc.main(["--out", self.tmp], opener=opener, today=DAY)
        return rc, err.getvalue()

    def test_writes_the_chart_and_asks_plainly(self):
        op = FakeOpener(site())
        self.assertEqual(self.run_main(op)[0], 0)
        with open(self.path, "rb") as f:
            first = f.read()
        data = json.loads(first)
        self.assertEqual((data["schema"], list(data["charts"])), (nc.SCHEMA, ["cpi_jp_us"]))
        self.assertEqual(data["charts"]["cpi_jp_us"]["lines"][1]["points"][-1], [2025, 2.0])
        self.assertTrue(first.endswith(b"\n") and b"\r" not in first)
        for url, timeout in op.calls:
            self.assertIsInstance(url, str)                                 # 머리말을 붙인 요청 객체가 아니다
            self.assertTrue(url.startswith("https://fred.stlouisfed.org/"))
            self.assertEqual(timeout, nc.TIMEOUT)
        self.assertEqual(len(op.calls), 5)                                  # 계열 쪽 둘 + CSV 셋
        self.assertEqual(self.run_main(FakeOpener(site()))[0], 0)
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), first)                               # 같은 입력·같은 날이면 같은 바이트

    def test_refused_series_write_nothing(self):
        for pages in (site(jp_mark=CLOSED.lower()), site(us_mark="monthly"), site(jp_last=2021),
                      site(us=monthly(1990, 2024))):
            rc, err = self.run_main(FakeOpener(pages))
            self.assertEqual(rc, 1)
            self.assertTrue(err.strip())
            self.assertFalse(os.path.exists(self.path))

    def test_a_computation_that_drifts_from_the_reference_is_not_published(self):
        off = yearly_rows(1990, 2024, lambda y: 2.0 + nc.CHECK_TOL * 2)
        self.assertEqual(self.run_main(FakeOpener(site(check=off)))[0], 1)
        self.assertEqual(self.run_main(FakeOpener(site(check=yearly_rows(2023, 2024, lambda y: 2.0))))[0], 1)
        self.assertFalse(os.path.exists(self.path))

    def test_network_failure_keeps_the_stored_file(self):
        self.assertEqual(self.run_main(FakeOpener(site()))[0], 0)
        with open(self.path, "rb") as f:
            before = f.read()
        pages = site()
        del pages[nc.FRED_CSV.format(sid=nc.US)]
        self.assertEqual(self.run_main(FakeOpener(pages))[0], 1)
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), before)

    def test_oversized_response_is_an_error(self):
        pages = site()
        pages[nc.FRED_PAGE.format(nc.JP)] = "x" * (nc.MAX_BYTES + 10)
        self.assertEqual(self.run_main(FakeOpener(pages))[0], 1)


class RepoTest(unittest.TestCase):
    """저장소에 실린 받아 둔 값 — 조건을 통과한 계열만, 출처·받은 날과 함께."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(REPO, "data", "notes_charts.json"), encoding="utf-8") as f:
            cls.data = json.load(f)

    def test_shape_and_conditions(self):
        self.assertEqual(self.data["schema"], nc.SCHEMA)
        for key, c in self.data["charts"].items():
            self.assertEqual(c["key"], key)
            self.assertEqual(set(c), CHART_KEYS)
            self.assertEqual(D.fromisoformat(c["retrieved"]).isoformat(), c["retrieved"])
            self.assertIn(c["retrieved"], c["source_note"])
            ids = {s["id"] for s in c["series"]}
            for s in c["series"]:
                self.assertIn(s["mark"], nc.USABLE)                          # 사전 허락이 필요한 계열은 없다
                self.assertEqual(s["url"], "https://fred.stlouisfed.org/series/" + s["id"])
                self.assertIn("retrieved from FRED", s["citation"])
            for ln in c["lines"]:
                self.assertLessEqual(set(ln["series"]), ids)                 # 선마다 어느 계열인지
                years = [p[0] for p in ln["points"]]
                self.assertEqual(years, list(range(years[0], years[-1] + 1)))
                self.assertGreaterEqual(years[-1], nc.MIN_LAST_YEAR)
                self.assertTrue(all(math.isfinite(p[1]) and -10 < p[1] < 30 for p in ln["points"]))

    def test_cpi_chart_starts_in_1995_and_marks_the_computed_line(self):
        c = self.data["charts"]["cpi_jp_us"]
        self.assertEqual([ln["points"][0][0] for ln in c["lines"]], [nc.START, nc.START])
        self.assertEqual([ln["computed"] for ln in c["lines"]], [False, True])
        self.assertIn("계산", c["lines"][1]["label"])


if __name__ == "__main__":
    unittest.main()
