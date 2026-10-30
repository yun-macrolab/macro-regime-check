#!/usr/bin/env python3
"""유가·에너지 참고 자료(oil_fetch) 테스트 — 산식(답을 아는 합성 자료), 기저 경로·절벽, 원화 나눔의 합, 상태 경계,
칸마다 실패·직전 값 이어 싣기, 이용 조건 목록, 문구 원칙(판정 낱말 없음), 화면·워크플로 연결.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — FRED는 가짜 loader 또는 합성 캐시(--offline). 숫자는 모두 지어낸 것이다.
"""
import os, sys, io, re, json, math, datetime, tempfile, unittest, shutil, contextlib
from unittest import mock

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import oil_fetch as oil
import ai_invest_fetch as ai
import render_public as rp
from test_render_public import FORBIDDEN_TEXT

REPO = os.path.dirname(SCRIPTS)
D = datetime.date
NOW = datetime.datetime(2026, 10, 30, 1, 30, tzinfo=datetime.timezone.utc)
# 판정·방향 낱말 — 공개 카드 어디에도 없어야 한다(FORBIDDEN_TEXT에 더해)
VERDICT = ("판정", "충족", "신호", "경보", "전망", "매수", "매도", "⚠", "강세", "약세", "호재", "악재", "우려", "부담",
           "상승", "하락", "→")


def bdays(start, end):
    out, d = [], start
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += datetime.timedelta(days=1)
    return out


def months(start, end):
    out, (y, m) = [], (start.year, start.month)
    while D(y, m, 1) <= end:
        out.append(D(y, m, 1))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def brent_month(d):
    """Brent 월별 고정 가격: 2026-03 80 · 2026-04 90 · 2026-05 이후 100, 그 전은 50."""
    if d >= D(2026, 5, 1):
        return 100.0
    return {(2026, 3): 80.0, (2026, 4): 90.0}.get((d.year, d.month), 50.0)


def world(end=D(2026, 10, 23)):
    days = bdays(D(2024, 1, 1), end)
    S = {"DCOILBRENTEU": [(d, brent_month(d)) for d in days],
         "DCOILWTICO": [(d, brent_month(d) - 5) for d in days],
         "DGASNYH": [(d, 2.5) for d in days], "DDFUELNYH": [(d, 3.0) for d in days],
         "DEXKOUS": [(d, 1300.0 if d.year < 2026 else 1400.0) for d in days if d.weekday() != 2],   # 수요일 빠짐
         "T5YIE": [(d, 2.2 if d < D(2026, 7, 27) else 2.5) for d in days],       # 13주 전(07-24)까지 옛 값
         "T5YIFR": [(d, 2.3 if d < D(2026, 7, 27) else 2.2) for d in days]}
    mondays = [d for d in days if d.weekday() == 0 and d <= D(2026, 10, 19)]
    S["GASREGW"] = [(d, 3.0 if d < D(2026, 1, 1) else 4.0) for d in mondays]
    S["GASDESW"] = [(d, 4.0 if d < D(2026, 1, 1) else 5.0) for d in mondays]
    ms = months(D(2023, 1, 1), D(2026, 10, 1))
    S["CPIAUCSL"] = [(m, 300 * 1.003 ** i) for i, m in enumerate(ms)]
    S["CPILFESL"] = [(m, 310 * 1.0025 ** i) for i, m in enumerate(ms) if m != D(2025, 10, 1)]   # 결측월
    S["CPIENGSL"] = [(m, 280 * 1.01 ** i) for i, m in enumerate(ms) if m <= D(2026, 9, 1)]
    return S


class FakeFred:
    def __init__(self, data, fail=(), cache=()):
        self.data, self.fail, self.cache, self.calls = data, set(fail), set(cache), []

    def __call__(self, sid, cache_dir, offline=False, timeout=None):
        self.calls.append((sid, timeout))
        if sid in self.fail:
            raise RuntimeError(f"{sid}: 원문 사유 https://bad.invalid/xyz-77")
        return list(self.data[sid]), ("cache" if sid in self.cache else "net")


class ArithmeticTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.S = world()

    def test_at_or_before_keeps_a_tolerance(self):
        s = [(D(2026, 1, 1), 1.0), (D(2026, 1, 20), 2.0)]
        self.assertEqual(oil.at_or_before(s, D(2026, 1, 8)), s[0])                 # 7일 안
        self.assertIsNone(oil.at_or_before(s, D(2026, 1, 9)))                      # 8일 — 비운다
        self.assertIsNone(oil.at_or_before(s, D(2025, 12, 31)))

    def test_crude_13_weeks_and_year_on_year(self):
        v = oil.calc_crude(self.S)["values"]
        self.assertEqual((v["brent"], v["brent_date"], v["wti"]), (100.0, "2026-10-23", 95.0))
        self.assertAlmostEqual(v["brent_13w"], 0.0)                                # 2026-07-24도 100
        self.assertAlmostEqual(v["brent_yoy"], 100.0)                              # 1년 전 50
        self.assertAlmostEqual(v["wti_yoy"], (95 / 45 - 1) * 100, places=3)

    def test_base_path_and_cliff(self):
        flat, f0, f1, m0, path, cliff = oil.base_path(self.S["DCOILBRENTEU"])
        self.assertEqual((flat, f1, oil._mday(m0)), (100.0, D(2026, 10, 23), D(2026, 10, 1)))
        self.assertEqual(f0, self.S["DCOILBRENTEU"][-20][0])
        want = [100, 100, 100, 100, 100, (100 / 80 - 1) * 100, (100 / 90 - 1) * 100]
        for got, w in zip(path, want):
            self.assertAlmostEqual(got, w)
        self.assertEqual(oil._mday(cliff), D(2027, 3, 1))                          # 100 → 25: 75%p 낮아지는 첫 달

    def test_cliff_needs_more_than_30pp(self):
        s = [(d, 130.0 if d >= D(2026, 9, 1) else 100.0) for d in bdays(D(2025, 1, 1), D(2026, 10, 23))]
        *_, path, cliff = oil.base_path(s)
        self.assertAlmostEqual(path[0], 30.0)
        self.assertIsNone(cliff)                                                   # 기준 달(2025-10~2026-04)이 모두 100 — 내내 +30%
        s2 = [(d, 100.0 if d.year == 2025 and d.month < 12 else 130.0) for d in bdays(D(2025, 1, 1), D(2026, 10, 23))]
        *_, path2, cliff2 = oil.base_path(s2)                                      # 2025-12부터 기준 130: +30 → 0, 딱 30%p
        self.assertAlmostEqual(path2[0] - path2[2], 30.0)
        self.assertIsNone(cliff2)                                                  # '넘게'만 — 30%p는 절벽이 아니다

    def test_base_month_with_few_days_is_left_blank(self):
        s = [p for p in self.S["DCOILBRENTEU"] if not (p[0].year == 2025 and p[0].month == 12 and p[0].day > 5)]
        *_, path, cliff = oil.base_path(s)
        self.assertIsNone(path[2])                                                 # 2025-12는 관측 10일 미만
        self.assertIsNotNone(path[1])

    def test_state_boundaries(self):
        self.assertEqual(oil.state_of(10.0), "flat")
        self.assertEqual(oil.state_of(10.0000004), "flat")                         # 소수 6자리 반올림 뒤
        self.assertEqual(oil.state_of(10.000001), "up")
        self.assertEqual(oil.state_of(-10.0), "flat")
        self.assertEqual(oil.state_of(-10.000001), "down")
        self.assertEqual(oil.state_of(0.0), "flat")

    def test_state_from_monthly_averages(self):
        for ratio, want in ((math.exp(0.1), "flat"), (math.exp(0.1001), "up"), (math.exp(-0.2), "down")):
            s = [(d, 100.0 * (ratio if d >= D(2026, 10, 1) else 1.0)) for d in bdays(D(2025, 1, 1), D(2026, 10, 23))]
            v = oil.calc_state({"DCOILBRENTEU": s})["values"]
            self.assertEqual((v["state"], v["month"]), (want, "2026-10-01"), ratio)
            self.assertAlmostEqual(v["d3"], math.log(ratio) * 100, places=4)
        v = oil.calc_state(self.S)["values"]
        self.assertEqual((v["state"], v["cliff"]), ("flat", "2027-03-01"))
        self.assertAlmostEqual(v["yoy"], 100.0)

    def test_state_uses_only_months_with_ten_days(self):
        s = [(d, 100.0 if d < D(2026, 10, 1) else 200.0) for d in bdays(D(2025, 1, 1), D(2026, 10, 7))]
        v = oil.calc_state({"DCOILBRENTEU": s})["values"]
        self.assertEqual((v["month"], v["state"]), ("2026-09-01", "flat"))       # 10월은 5일뿐 — 9월로 적는다

    def test_krw_split_adds_up(self):
        for b1, b0, k1, k0 in ((100, 50, 1400, 1300), (80, 100, 1500, 1200), (100, 100, 1300, 1300), (120, 100, 1000, 1200)):
            y, d, f = oil.krw_split(b1, b0, k1, k0)
            self.assertAlmostEqual(y, (b1 * k1 / (b0 * k0) - 1) * 100)
            self.assertAlmostEqual(d + f, y, places=10)
        y, d, f = oil.krw_split(110, 100, 1000, 1100)                              # 두 로그 변화가 지운다
        self.assertAlmostEqual(y, 0.0, places=10)
        self.assertAlmostEqual(d, math.log(1.1) * 100)
        self.assertAlmostEqual(d + f, 0.0, places=10)

    def test_korea_uses_common_days_and_shown_parts_add_up(self):
        v = oil.calc_korea(self.S)["values"]
        self.assertEqual(v["month"], "2026-10-01")
        self.assertEqual(v["days"], 14)                                            # 10월 1~23일 평일 17 − 수요일 3(7·14·21일)
        self.assertAlmostEqual(v["krw"], 100 * 1400 / 10000)
        self.assertAlmostEqual(v["yoy"], (100 * 1400 / (50 * 1300) - 1) * 100, places=3)
        self.assertAlmostEqual(v["usd_pp"] + v["fx_pp"], v["yoy"], places=3)
        line, _ = oil.texts("korea", v, "2026-10-01")
        nums = [float(x) for x in re.findall(r"[+-]\d+\.\d", line.split("전년비 ")[1])]
        self.assertEqual(len(nums), 3)
        self.assertAlmostEqual(nums[1] + nums[2], nums[0], places=6)               # 보이는 숫자끼리 합이 맞다
        for odd in ((101.3, 50.0, 1361.7, 1300.0), (99.95, 50.05, 1349.95, 1300.05)):
            y, d, f = oil.krw_split(*odd[:2], *odd[2:])
            line, _ = oil.texts("korea", dict(v, yoy=y, usd_pp=d, fx_pp=f), "2026-10-01")
            a, b, c = [float(x) for x in re.findall(r"[+-]\d+\.\d", line.split("전년비 ")[1])]
            self.assertAlmostEqual(b + c, a, places=6)

    def test_korea_month_needs_ten_common_days(self):
        S = dict(self.S, DEXKOUS=[p for p in self.S["DEXKOUS"] if not (p[0] >= D(2026, 10, 1) and p[0].day > 9)])
        self.assertEqual(oil.calc_korea(S)["values"]["month"], "2026-09-01")

    def test_cracks(self):
        self.assertAlmostEqual(oil.crack_321(2.5, 3.0, 95.0), (2 * 2.5 * 42 + 3.0 * 42) / 3 - 95)
        v = oil.calc_cracks(self.S)["values"]
        self.assertAlmostEqual(v["c321"], 112 - 95)
        self.assertAlmostEqual(v["c321_avg"], 112 - 95)
        self.assertAlmostEqual(v["c321_avg_1y"], 112 - 45)
        self.assertAlmostEqual(v["ulsd"], 3.0 * 42 - 100)
        self.assertAlmostEqual(v["ulsd_avg_1y"], 3.0 * 42 - 50)

    def test_avg_ending_needs_twenty_and_a_close_end(self):
        s = [(d, float(i)) for i, d in enumerate(bdays(D(2026, 1, 1), D(2026, 3, 31)))]
        self.assertAlmostEqual(oil.avg_ending(s, s[-1][0]), sum(range(len(s) - 20, len(s))) / 20)
        self.assertIsNone(oil.avg_ending(s, s[10][0]))                             # 20개가 안 된다
        self.assertIsNone(oil.avg_ending(s, D(2026, 5, 1)))                        # 끝 관측이 너무 이르다

    def test_spread(self):
        S = dict(self.S, DCOILWTICO=[(d, v - (5 if d < D(2026, 10, 1) else 8)) for d, v in self.S["DCOILBRENTEU"]])
        v = oil.calc_spread(S)["values"]
        self.assertAlmostEqual(v["last"], 8)
        self.assertAlmostEqual(v["avg"], (17 * 8 + 3 * 5) / 20)                   # 10월 평일 17일 + 9월 끝 3일
        self.assertAlmostEqual(v["avg_13w"], 5)

    def test_cpi_same_month_and_last_month_both_exist(self):
        v = oil.calc_cpi(self.S)["values"]
        self.assertEqual((v["month"], v["energy_month"]), ("2026-09-01", "2026-09-01"))   # 근원 2025-10이 비어 10월은 없다
        self.assertAlmostEqual(v["head"], (1.003 ** 12 - 1) * 100, places=3)
        self.assertAlmostEqual(v["core"], (1.0025 ** 12 - 1) * 100, places=3)
        self.assertAlmostEqual(v["energy"], (1.01 ** 12 - 1) * 100, places=3)
        line, _ = oil.texts("cpi", v, "2026-09-01")
        h, c, g = [float(x) for x in re.findall(r"전체 ([\d.]+)% − 근원 ([\d.]+)% = ([+-][\d.]+)%p", line)[0]]
        self.assertAlmostEqual(h - c, g, places=6)

    def test_bei_in_bp(self):
        v = oil.calc_bei(self.S)["values"]
        self.assertAlmostEqual(v["be5_13w"], 30)
        self.assertAlmostEqual(v["fwd_13w"], -10)
        self.assertAlmostEqual(v["gap"], 30)
        self.assertAlmostEqual(v["gap_13w"], 40)

    def test_products(self):
        v = oil.calc_products(self.S)["values"]
        self.assertEqual(v["gas_date"], "2026-10-19")
        self.assertAlmostEqual(v["gas_yoy"], (4 / 3 - 1) * 100, places=3)
        self.assertAlmostEqual(v["diesel_13w"], 0.0)

    def test_every_item_computes_and_texts_have_no_verdict_words(self):
        core = oil.compute(self.S, {}, NOW.date())
        for spec in oil.ITEMS:
            c = core[spec["key"]]
            self.assertNotIsInstance(c, oil.ItemError, spec["key"])
            self.assertEqual(set(c["values"]), set(spec["values"]), spec["key"])
            line, extra = oil.texts(spec["key"], c["values"], c["date"])
            for t in [line, *extra, spec["title"]]:
                self.assertNotIn("None", t)
                for word in list(FORBIDDEN_TEXT) + list(VERDICT):
                    self.assertNotIn(word, t, (spec["key"], word))
        state = oil.texts("state", core["state"]["values"], core["state"]["date"])
        self.assertIn(oil.STATE_DEF, state[1])                                     # 상태 이름은 정의와 함께만
        self.assertIn("예측하지 않는다", " ".join(state[1]))


class LicenceTest(unittest.TestCase):
    def test_series_list_is_fixed_and_public(self):
        self.assertEqual(set(oil.SERIES), {"DCOILBRENTEU", "DCOILWTICO", "GASREGW", "GASDESW", "DGASNYH", "DDFUELNYH",
                                           "CPIENGSL", "CPIAUCSL", "CPILFESL", "DEXKOUS", "T5YIE", "T5YIFR"})
        self.assertEqual(set(oil.LICENCE), set(oil.SERIES))
        self.assertEqual({s for s, v in oil.LICENCE.items() if v != "public-domain"}, {"T5YIE", "T5YIFR"})
        self.assertEqual(set(oil.LICENCE.values()), {"public-domain", "citation-required"})
        self.assertFalse(set(oil.SERIES) & (set(rp.RESTRICTED) | set(ai.RESTRICTED)))
        for spec in oil.ITEMS:
            self.assertLessEqual(set(spec["series"]), set(oil.SERIES))

    def test_citation_required_items_carry_the_notice(self):
        self.assertIn(oil.CITATION_NOTICE, oil.notices(oil.BY_KEY["bei"]))
        for key in ("crude", "korea", "cpi"):
            self.assertEqual(oil.notices(oil.BY_KEY[key]), [oil.COMPUTED_NOTICE])


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.out = os.path.join(self.tmp, "data")
        self.work = os.path.join(self.tmp, ".work")
        self.path = os.path.join(self.out, oil.FILE)
        self.S = world()

    def run_main(self, fred=None, now=NOW, extra=(), clock=None):
        fred = fred or FakeFred(self.S)
        buf = io.StringIO()
        kw = {"clock": clock} if clock else {}
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = oil.main(["--out", self.out, "--work", self.work, *extra], fred_load=fred, now=now, **kw)
        return code, buf.getvalue()

    def saved(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def test_first_run_writes_every_item(self):
        code, log = self.run_main()
        self.assertEqual(code, 0, log)
        js = self.saved()
        self.assertEqual(set(js), {"schema", "generated_at", "notice", "order", "items"})
        self.assertEqual(js["order"], [s["key"] for s in oil.ITEMS])
        for key, it in js["items"].items():
            self.assertTrue(it["ok"], key)
            self.assertEqual(it["retrieved"], "2026-10-30")
            self.assertTrue(it["notices"])
            for src in it["sources"]:
                self.assertEqual(src["licence"], oil.LICENCE[src["series"]])
                self.assertTrue(src["citation"].startswith(oil.SOURCES[src["series"]][0]))
                self.assertTrue(src["citation"].endswith("October 30, 2026."))
        chart = js["items"]["base"]["chart"]
        self.assertEqual([ln["key"] for ln in chart["lines"]], ["yoy", "path"])
        self.assertEqual([p[0] for p in chart["lines"][1]["points"]][-1], "2027-04-01")
        self.assertEqual(chart["lines"][0]["points"][-1][0], "2026-10-01")
        self.assertNotIn("chart", js["items"]["crude"])

    def test_one_missing_series_only_stales_its_items(self):
        self.run_main()
        code, log = self.run_main(fred=FakeFred(self.S, fail={"DEXKOUS"}), now=NOW + datetime.timedelta(days=1))
        self.assertEqual(code, 0, log)
        items = self.saved()["items"]
        k = items["korea"]
        self.assertEqual((k["ok"], k["stale"], k["error"], k["failed_since"]), (False, True, oil.REASONS["fetch"], "2026-10-31"))
        self.assertEqual(k["retrieved"], "2026-10-30")
        self.assertTrue(all(items[x]["ok"] for x in items if x != "korea"))
        self.assertIn("::warning::유가·에너지 참고 korea 받지 못함", log)
        self.assertNotIn("xyz-77", log)
        self.run_main(fred=FakeFred(self.S, fail={"DCOILBRENTEU"}), now=NOW + datetime.timedelta(days=2))
        items = self.saved()["items"]
        bad = {k for k, it in items.items() if not it["ok"]}
        self.assertEqual(bad, {"crude", "base", "cracks", "spread", "state", "korea"})
        self.assertEqual(items["korea"]["failed_since"], "2026-10-31")             # 못 받기 시작한 날을 지킨다

    def test_first_failure_without_previous_has_no_numbers(self):
        self.run_main(fred=FakeFred(self.S, cache={"T5YIFR"}))
        it = self.saved()["items"]["bei"]
        self.assertEqual((it["ok"], it["stale"], it["error"]), (False, False, oil.REASONS["cache"]))
        self.assertNotIn("line", it)

    def test_offline_reads_the_cache(self):
        cache = os.path.join(self.work, oil.CACHE)
        os.makedirs(cache)
        for sid, s in self.S.items():
            with open(os.path.join(cache, f"{sid}.csv"), "w", encoding="utf-8") as f:
                f.write("observation_date," + sid + "\n" + "".join(f"{d.isoformat()},{v}\n" for d, v in s))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), mock.patch.object(ai.urllib.request, "urlopen", side_effect=AssertionError("요청")):
            code = oil.main(["--out", self.out, "--work", self.work, "--offline"], now=NOW)
        self.assertEqual(code, 0, buf.getvalue())
        self.assertTrue(all(it["ok"] for it in self.saved()["items"].values()))

    def test_older_data_is_not_taken(self):
        self.run_main()
        short = dict(self.S, GASDESW=self.S["GASDESW"][:-1])
        self.run_main(fred=FakeFred(short), now=NOW + datetime.timedelta(days=1))
        it = self.saved()["items"]["products"]
        self.assertEqual((it["ok"], it["stale"], it["error"]), (False, True, oil.REASONS["older"]))
        self.assertEqual(it["values"]["diesel_date"], "2026-10-19")

    def test_same_numbers_keep_the_file(self):
        self.run_main()
        with open(self.path, "rb") as f:
            first = f.read()
        self.run_main(now=NOW + datetime.timedelta(days=1))
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), first)

    def test_a_broken_previous_file_is_not_carried(self):
        self.run_main()
        js = self.saved()
        js["items"]["state"]["values"]["state"] = "매수"                          # 정해 둔 이름 밖
        js["items"]["base"]["chart"]["lines"][0]["points"][0][1] = "9"
        js["items"]["korea"]["values"]["days"] = -1
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(js, f, ensure_ascii=False)
        self.run_main(fred=FakeFred(self.S, fail={"DCOILBRENTEU"}), now=NOW + datetime.timedelta(days=1))
        items = self.saved()["items"]
        for key in ("state", "base", "korea"):
            self.assertEqual((items[key]["ok"], items[key]["stale"]), (False, False), key)
            self.assertNotIn("line", items[key])
        self.assertTrue(items["crude"]["stale"])
        self.assertNotIn("매수", json.dumps(self.saved(), ensure_ascii=False))

    def test_budget_runs_out_without_waiting(self):
        t = [0.0]

        def clock():
            t[0] += 30.0
            return t[0]
        fred = FakeFred(self.S)
        code, log = self.run_main(fred=fred, clock=clock)
        self.assertLess(len(fred.calls), len(oil.SERIES))
        self.assertTrue(all(1 <= tmo <= ai.TIMEOUT for _, tmo in fred.calls))
        self.assertIn("::warning::", log)

    def test_nothing_fetched_exits_1(self):
        code, log = self.run_main(fred=FakeFred(self.S, fail=set(self.S)))
        self.assertEqual(code, 1, log)
        self.assertTrue(all(not it["ok"] for it in self.saved()["items"].values()))

    def test_the_write_is_atomic(self):
        self.run_main()
        with open(self.path, "rb") as f:
            before = f.read()
        with mock.patch.object(ai.os, "replace", side_effect=OSError("disk full")):
            code, log = self.run_main(fred=FakeFred(dict(self.S, T5YIE=[(d, v + 0.1) for d, v in self.S["T5YIE"]])),
                                      now=NOW + datetime.timedelta(days=1))
        self.assertEqual(code, 1, log)
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), before)
        self.assertEqual(os.listdir(self.out), [oil.FILE])

    def test_every_string_is_fixed_text_without_verdict_words(self):
        self.run_main(fred=FakeFred(self.S, fail={"CPIENGSL"}))
        self.run_main(now=NOW + datetime.timedelta(days=1))
        self.run_main(fred=FakeFred(self.S, fail={"DCOILBRENTEU", "T5YIE"}), now=NOW + datetime.timedelta(days=2))
        dump = json.dumps(self.saved(), ensure_ascii=False)
        for word in list(FORBIDDEN_TEXT) + list(VERDICT):
            self.assertNotIn(word, dump, word)
        urls = {u.rstrip(".") for u in re.findall(r"https?://[^\s,;)\"]+", dump)}
        self.assertEqual(urls, {f"https://fred.stlouisfed.org/series/{sid}" for sid in oil.SERIES})
        self.assertNotIn("bad.invalid", dump)
        errors = {it["error"] for it in self.saved()["items"].values()} - {None}
        self.assertLessEqual(errors, set(oil.REASONS.values()))


class StaticTest(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
            return f.read()

    def test_workflow_fetches_without_failing_the_run(self):
        wf = self.read(".github", "workflows", "daily.yml")
        step = wf[wf.index("id: oil"):]
        self.assertIn("continue-on-error: true", step[:200])
        self.assertIn("timeout-minutes: 2", step[:200])
        self.assertIn("python scripts/oil_fetch.py", step[:300])
        self.assertLess(wf.index("id: oil"), wf.index("공개 전 검사(새 산출물 포함)"))
        self.assertLess(wf.index("id: oil"), wf.index("git add data"))
        self.assertNotIn("oil", wf[wf.index("\n  alert:"):])                    # 실패해도 알림을 띄우지 않는다
        self.assertIn("node --test scripts/test_oil_render.cjs", wf[wf.index("\n  check:"):wf.index("\n  update:")])

    def test_job_timeout_covers_the_step_limits(self):
        wf = self.read(".github", "workflows", "daily.yml")
        job = wf[wf.index("\n  update:"):wf.index("\n  deploy:")]
        m = re.search(r"timeout-minutes: (\d+) +# 참고 자료 단계 제한의 합\(([^)]*?) = (\d+)분\)", job)
        total, named, summed = int(m.group(1)), [int(x) for x in re.findall(r"\d+", m.group(2))], int(m.group(3))
        steps = [int(m) for m in re.findall(r"continue-on-error: true\n\s+timeout-minutes: (\d+)", job)]
        self.assertEqual(sorted(named), sorted(steps))                             # 주석의 항목 = 실제 단계 제한
        self.assertEqual(sum(steps), summed)
        self.assertGreaterEqual(total - sum(steps), 5)                             # 수집·생성 몫이 남는다

    def test_page_wires_the_card_and_the_korea_line(self):
        page = self.read("site", "index.html")
        self.assertIn('getJson("data/oil.json")', page)
        self.assertIn('<script src="oil.js"></script>', page)
        self.assertIn('<a href="data/oil.json">', page)
        self.assertIn('g.id === "inflation" ? el("div", {id:"oil-slot"', page)   # 물가 묶음 안
        korea = page[page.index('<section id="korea-market"'):]
        self.assertIn('<div id="korea-oil" class="panel korea-oil" hidden', korea[:korea.index("</section>")])
        self.assertIn("window.OilEnergy.render(oil.value)", page)

    def test_screen_script_matches_the_file_and_avoids_verdict_words(self):
        js = self.read("site", "oil.js")
        card = re.findall(r'"(\w+)"', js[js.index("const CARD = ["):].split("]")[0])
        self.assertEqual(card, [s["key"] for s in oil.ITEMS if s["key"] != "korea"])
        reasons = re.findall(r'"([^"]+)"', js[js.index("const REASONS = ["):].split("];")[0])
        self.assertEqual(reasons, list(oil.REASONS.values()))
        for tok in ("innerHTML", "outerHTML", "insertAdjacentHTML", "createElement", "fetch(", "eval("):
            self.assertNotIn(tok, js)
        body = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        for word in list(FORBIDDEN_TEXT) + list(VERDICT):
            self.assertNotIn(word, body, word)
        self.assertIn('key === "state" ? el("p", { class: "oil-note" }, STATE_NOTE)', js)   # 상태 줄에는 늘 정의 안내
        css = self.read("site", "dashboard.css")
        self.assertRegex(css, r"\.oil-card p, \.korea-oil p \{[^}]*overflow-wrap: anywhere")


if __name__ == "__main__":
    unittest.main(verbosity=1)
