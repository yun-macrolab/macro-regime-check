#!/usr/bin/env python3
"""유가·에너지 참고 자료(oil_fetch) 테스트 — 산식(답을 아는 합성 자료), 기저 경로·절벽, 원화 나눔의 합, 상태 경계,
칸마다 실패·직전 값 이어 싣기, 이용 조건 목록, 문구 원칙(판정 낱말 없음), 화면·워크플로 연결.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — FRED는 가짜 loader 또는 합성 캐시(--offline). 숫자는 모두 지어낸 것이다.
"""
import os, sys, io, re, json, math, datetime, tempfile, unittest, shutil, contextlib, statistics
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


def no_tags(text):
    """정해 둔 꼬리표 이름(운영자 정의 — '에너지 하락')은 낱말 검사에서 뺀다. 그 밖의 '하락'은 그대로 잡힌다."""
    return text.replace(oil.TAG_DOWN, "")


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
    S["PCEPILFE"] = [(m, 120 * 1.003 ** i) for i, m in enumerate(ms) if m <= D(2026, 9, 1)]     # 전년비 약 3.7% — 높음 · 보통
    S["IPN213111N"] = [(m, 100.0 if m.year < 2026 else 90.0) for m in ms if m <= D(2026, 9, 1)]
    S["CAPUTLG211S"] = [(m, 80.0 if m.year < 2026 else 85.0) for m in ms if m <= D(2026, 9, 1)]
    S["POILDUBUSDM"] = [(m, 70.0 if m.year < 2026 else 77.0) for m in ms if m <= D(2026, 9, 1)]
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

    def test_base_flat_is_the_twenty_day_mean(self):
        days = bdays(D(2025, 1, 1), D(2026, 10, 23))
        s = [(d, 50.0 + i * 0.1) for i, d in enumerate(days)]                  # 날마다 오른다 — 평균 ≠ 마지막 값
        flat, f0, f1, m0, path, _ = oil.base_path(s)
        want = sum(v for _, v in s[-20:]) / 20
        self.assertAlmostEqual(flat, want)
        self.assertAlmostEqual(s[-1][1] - flat, 0.95)                              # 0.1 × 9.5
        self.assertEqual((f0, f1), (s[-20][0], s[-1][0]))
        oct25 = [v for d, v in s if (d.year, d.month) == (2025, 10)]
        self.assertAlmostEqual(path[0], (want / (sum(oct25) / len(oct25)) - 1) * 100)

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

    def test_state_window_is_three_months(self):
        lvl = {(2026, 8): 120.0, (2026, 9): 120.0, (2026, 10): 130.0}           # 7월까지 100
        s = [(d, lvl.get((d.year, d.month), 100.0)) for d in bdays(D(2025, 1, 1), D(2026, 10, 23))]
        v = oil.calc_state({"DCOILBRENTEU": s})["values"]
        self.assertAlmostEqual(v["d3"], math.log(1.3) * 100, places=4)             # 10월 대 7월(2개월 전 8월이면 +8%·보합)
        self.assertEqual(v["state"], "up")

    def test_state_skips_a_month_whose_three_months_ago_is_thin(self):
        s = [(d, 100.0 if d.month < 9 or d.year < 2026 else 130.0) for d in bdays(D(2025, 1, 1), D(2026, 10, 23))
             if not (d.year == 2026 and d.month == 7 and d.day > 5)]                # 7월은 3일뿐 — 10월은 잴 수 없다
        v = oil.calc_state({"DCOILBRENTEU": s})["values"]
        self.assertEqual(v["month"], "2026-09-01")                                 # 9월 대 6월
        self.assertAlmostEqual(v["d3"], math.log(1.3) * 100, places=4)

    def test_state_and_path_months_differ_early_in_a_month(self):
        S = world(end=D(2026, 10, 7))                                             # 10월은 5일뿐 — 상태는 9월, 경로는 10월부터
        v = oil.calc_state(S)["values"]
        self.assertEqual((v["month"], v["path_month"]), ("2026-09-01", "2026-10-01"))
        line, extra = oil.texts("state", v, oil.calc_state(S)["date"])
        self.assertTrue(line.startswith("2026-09 "), line)
        self.assertIn("기저 절벽 2027-03(2026-10부터 앞 6개월, 가격이 그대로일 때)", line)
        self.assertIn("두 달이 다를 수 있어", " ".join(extra))
        self.assertIn("기저 절벽 없음(", oil.texts("state", dict(v, cliff=None), "2026-09-01")[0])

    def test_state_line_year_on_year_sign(self):
        v = oil.calc_state(world(end=D(2026, 10, 7)))["values"]
        for yoy, mark in ((12.3, "+"), (-0.4, "−"), (0.0, "0"), (None, "—")):
            self.assertIn(f" · 전년비 {mark} · ", oil.texts("state", dict(v, yoy=yoy), "2026-09-01")[0])

    def test_state_uses_only_months_with_ten_days(self):
        s = [(d, 100.0 if d < D(2026, 10, 1) else 200.0) for d in bdays(D(2025, 1, 1), D(2026, 10, 7))]
        v = oil.calc_state({"DCOILBRENTEU": s})["values"]
        self.assertEqual((v["month"], v["state"]), ("2026-09-01", "flat"))       # 10월은 5일뿐 — 9월로 적는다

    def test_krw_split_adds_up(self):
        for b1, b0, k1, k0 in ((100, 50, 1400, 1300), (80, 100, 1500, 1200), (100, 100, 1300, 1300), (120, 100, 1000, 1200)):
            y, d, f = oil.krw_split(b1, b0, k1, k0)
            self.assertAlmostEqual(y, (b1 * k1 / (b0 * k0) - 1) * 100)
            self.assertAlmostEqual(d + f, y, places=10)
        y, d, f = oil.krw_split(100, 50, 1400, 1300)                               # 몫 각각 = 전년비 × 로그 변화의 비율
        lb, lk = math.log(2), math.log(1400 / 1300)
        self.assertAlmostEqual(d, y * lb / (lb + lk))
        self.assertAlmostEqual(f, y * lk / (lb + lk))
        self.assertNotAlmostEqual(d, 100.0, places=1)                              # '달러 전년비 + 나머지'가 아니다
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
        lb, lk = math.log(100 / 50), math.log(1400 / 1300)
        self.assertAlmostEqual(v["usd_pp"], v["yoy"] * lb / (lb + lk), places=3)
        self.assertAlmostEqual(v["fx_pp"], v["yoy"] * lk / (lb + lk), places=3)
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
        gap = lambda d: 3 if d < D(2026, 8, 1) else 5 if d < D(2026, 10, 1) else 8
        S = dict(self.S, DCOILWTICO=[(d, v - gap(d)) for d, v in self.S["DCOILBRENTEU"]])
        v = oil.calc_spread(S)["values"]
        self.assertAlmostEqual(v["last"], 8)
        self.assertAlmostEqual(v["avg"], (17 * 8 + 3 * 5) / 20)                   # 10월 평일 17일 + 9월 끝 3일
        self.assertAlmostEqual(v["avg_13w"], 3)                                    # 91일 전 07-24까지 — 8월이 섞이면 3이 아니다

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
        self.assertEqual((v["gas_m"], v["gas_m_n"], v["gas_m_avg"], v["gas_m_ch"]), ("2026-10-01", 3, 4.0, 0.0))

    def test_observations_after_today_are_dropped(self):
        S = dict(self.S, DCOILBRENTEU=self.S["DCOILBRENTEU"] + [(D(2026, 11, 2), 999.0)])
        v = oil.compute(S, {}, NOW.date())["crude"]
        self.assertEqual((v["date"], v["values"]["brent"]), ("2026-10-23", 100.0))

    def test_wording(self):
        self.assertFalse([r for r in oil.REASONS.values() if "(" in r or ")" in r])   # '미수신(까닭)'이 겹 괄호가 되지 않게
        _, spread = oil.texts("spread", {"last": 1.0, "avg": 1.0, "avg_13w": 1.0}, "2026-10-23")
        self.assertIn("미국 밖 원유가 미국 원유보다 상대적으로 비싸졌다는 뜻이고, 좁혀지면 그 반대다", spread[0])
        v = oil.calc_bei(self.S)["values"]
        _, bei = oil.texts("bei", v, "2026-10-23")
        self.assertIn("5년 뒤 5년은 5년·10년 명목 국채와 TIPS 금리로 계산한", bei[0])

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
                    self.assertNotIn(word, no_tags(t), (spec["key"], word))
        state = oil.texts("state", core["state"]["values"], core["state"]["date"])
        self.assertIn(oil.STATE_DEF, state[1])                                     # 상태 이름은 정의와 함께만
        self.assertIn("예측하지 않는다", " ".join(state[1]))


def index(start, growths):
    """월간 지수 — start 달부터 달마다 growths[i]만큼 늘어난다(첫 달 100)."""
    out, v, (y, m) = [], 100.0, (start.year, start.month)
    for g in growths:
        v *= 1 + g
        out.append((D(y, m, 1), v))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def g_of(rate):
    """연율 rate(%)가 되는 달마다의 증가율."""
    return (1 + rate / 100) ** (1 / 12) - 1


class AddedLinesTest(unittest.TestCase):
    """운영자의 월간 점검에만 있던 줄 — 실질 WTI 분위·이번 달 평균·I4와 꼬리표·상태별 측정 기록·공급 반응·두바이."""

    @classmethod
    def setUpClass(cls):
        cls.S = world()

    # 실질 WTI 분위
    def wti_world(self, cpi_end=D(2026, 9, 1)):
        days = bdays(D(1985, 12, 2), D(2026, 10, 23))
        wti = [(d, 50.0) for d in days if not (d.year == 2000 and d.month == 2 and d.day > 7)]   # 2000-02는 5일뿐
        wti = [(d, 1.0 if d.year == 1985 else v) for d, v in wti]                                # 1986년 앞은 표본 밖
        ms = months(D(1985, 12, 1), cpi_end)
        cpi = [(m, 100 * 1.002 ** i) for i, m in enumerate(ms)]
        return {"DCOILBRENTEU": wti, "DCOILWTICO": wti, "CPIAUCSL": cpi}

    def test_real_wti_percentile_uses_same_month_cpi_and_the_last_cpi_for_a_new_month(self):
        r = oil.real_wti(self.wti_world())
        n = len(months(D(1986, 1, 1), D(2026, 10, 1))) - 1                           # 2000-02(관측 5일) 빠짐
        self.assertEqual((r["wti_month"], r["real_cpi_month"], r["real_n"], r["wti_avg"]), ("2026-10-01", "2026-09-01", n, 50.0))
        self.assertAlmostEqual(r["real_pct"], round(2 / n * 100, 1))                  # 10월 = 50 ÷ 9월 CPI = 9월 실질 — 둘이 가장 낮다
        self.assertEqual(r["nom_pct"], 100.0)                                         # 명목은 모두 50 — 같은 값은 '이하'에 든다

    def test_real_wti_needs_a_cpi_within_three_months(self):
        self.assertEqual(oil.real_wti(self.wti_world(cpi_end=D(2026, 7, 1)))["real_cpi_month"], "2026-07-01")
        self.assertIsNone(oil.real_wti(self.wti_world(cpi_end=D(2026, 6, 1))))       # 4개월 전 — 나누지 않는다
        S = self.wti_world(cpi_end=D(2026, 6, 1))
        v = oil.calc_crude(S)["values"]                                                # 원유 줄은 그대로, 분위만 빈다
        self.assertEqual({k: v[k] for k in oil.REAL_KEYS}, dict.fromkeys(oil.REAL_KEYS))
        line, extra = oil.texts("crude", v, "2026-10-23")
        self.assertNotIn("실질", line)
        self.assertEqual(len(extra), 1)
        self.assertEqual([s["series"] for s in oil.sources_of(oil.BY_KEY["crude"], "2026-10-30", v)],
                         ["DCOILBRENTEU", "DCOILWTICO"])                               # 쓰지 않은 CPI는 출처에 없다

    def test_crude_line_shows_the_percentiles(self):
        v = oil.calc_crude(self.wti_world())["values"]
        line, extra = oil.texts("crude", v, "2026-10-23")
        self.assertTrue(line.endswith(f" · 실질 WTI 2026-10 월평균 p{v['real_pct']:.0f} (명목 p100, 1986~)"), line)
        self.assertIn("이번엔 2026-09", extra[1])
        self.assertIn(f"1986년 이후 {v['real_n']}개 달", extra[1])

    def test_crude_without_cpi_keeps_its_numbers(self):
        S = {k: v for k, v in self.S.items() if k != "CPIAUCSL"}
        core = oil.compute(S, {"CPIAUCSL": "fetch"}, NOW.date())
        self.assertNotIsInstance(core["crude"], oil.ItemError)
        self.assertIsNone(core["crude"]["values"]["real_pct"])
        self.assertIsInstance(core["cpi"], oil.ItemError)
        self.assertIsInstance(core["i4"], oil.ItemError)

    # 소매가 이번 달 평균
    def test_month_to_date_against_last_month(self):
        s = [(D(2026, 9, 7), 3.0), (D(2026, 9, 14), 3.2), (D(2026, 10, 5), 3.3), (D(2026, 10, 12), 3.5), (D(2026, 10, 19), 3.7)]
        m, n, avg, ch = oil.month_to_date(s)
        self.assertEqual((oil._mday(m), n), (D(2026, 10, 1), 3))
        self.assertAlmostEqual(avg, 3.5)
        self.assertAlmostEqual(ch, (3.5 / 3.1 - 1) * 100)
        self.assertIsNone(oil.month_to_date(s[2:]))                                    # 지난달 관측이 없다
        self.assertIsNone(oil.month_to_date([]))
        self.assertIsNone(oil.month_to_date([(D(2026, 8, 31), 3.0)] + s[2:]))          # 두 달 전은 지난달이 아니다

    def test_month_to_date_is_the_mean_not_the_median(self):
        # 평균과 가운데 값이 다른 주간 값 — 이번 달 (3.0+3.1+3.8)/3 = 3.3(가운데 3.1), 지난달 (2.0+2.1+3.1)/3 = 2.4(가운데 2.1)
        s = [(D(2026, 9, 7), 2.0), (D(2026, 9, 14), 2.1), (D(2026, 9, 21), 3.1),
             (D(2026, 10, 5), 3.0), (D(2026, 10, 12), 3.1), (D(2026, 10, 19), 3.8)]
        m, n, avg, ch = oil.month_to_date(s)
        self.assertEqual(n, 3)
        self.assertAlmostEqual(avg, 3.3)
        self.assertAlmostEqual(ch, (3.3 / 2.4 - 1) * 100)

    def test_products_line_shows_this_month_and_skips_it_when_missing(self):
        v = oil.calc_products(self.S)["values"]
        v.update(gas_m_avg=3.5, gas_m_ch=12.9032, gas_m_n=3)
        line, extra = oil.texts("products", v, "2026-10-19")
        self.assertIn("전년비 +33.3% · 10월 평균 $3.50(3주) 대 9월 +12.9% / 경유", line)
        self.assertTrue(line.endswith(" · 10월 평균 $5.00(3주) 대 9월 0.0%"), line)
        self.assertIn("계절조정 없음", extra[1])
        v.update(dict.fromkeys(("gas_m", "gas_m_n", "gas_m_avg", "gas_m_ch")))
        line, _ = oil.texts("products", v, "2026-10-19")
        self.assertIn("전년비 +33.3% / 경유", line)
        self.assertEqual(line.count("평균"), 1)
        jan = dict(v, diesel_m="2026-01-01")
        self.assertIn("1월 평균 $5.00(3주) 대 12월", oil.texts("products", jan, "2026-01-19")[0])   # 해를 넘는 지난달

    # I4 · 물가 상태 · 꼬리표
    def test_band_hysteresis(self):
        cases = [(None, 3.1, "M"), (None, 3.1000004, "M"), (None, 3.100001, "H"), ("H", 2.9, "H"), ("H", 2.899999, "M"),
                 ("H", 2.5, "Lo"), (None, 2.6, "M"), (None, 2.599999, "Lo"), ("Lo", 2.7, "Lo"), ("Lo", 2.700001, "M"),
                 ("Lo", 3.2, "H"), ("M", 3.0, "M"), ("H", None, None)]
        for prev, y, want in cases:
            self.assertEqual(oil.band_step(prev, y), want, (prev, y))

    def test_momentum_class(self):
        cases = [([0.5], "A"), ([0.4999], "F"), ([None], None), ([], None), ([-0.3], None), ([0.1, -0.3], "F"),
                 ([-0.3, -0.3], "D"), ([None, -0.35], None), ([-0.31, -0.29], "F"), ([-0.4, 0.6], "A"),
                 ([-0.3000004, -0.2999996], "D")]
        for seq, want in cases:
            self.assertEqual(oil.mom_class(seq), want, seq)

    def test_infl_rows_y3_takes_two_of_three_months(self):
        s = index(D(2023, 1, 1), [g_of(2.0)] * 12 + [g_of(4.0)] * 14)                    # 2023-01 ~ 2025-02
        rows = oil.infl_rows([p for p in s if p[0] != D(2024, 10, 1)])                  # 결측월 — 그 달 전년비가 없다
        k = oil._mkey(D(2024, 11, 1))
        self.assertIsNone(rows.get(oil._mkey(D(2024, 10, 1))))
        y = lambda d: rows[oil._mkey(d)]["y12"]
        self.assertAlmostEqual(rows[k]["Y3"], (y(D(2024, 11, 1)) + y(D(2024, 9, 1))) / 2)  # 석 달 중 둘
        self.assertIsNone(rows[oil._mkey(D(2024, 1, 1))]["Y3"])                         # 첫 전년비 달 — 하나뿐
        self.assertAlmostEqual(rows[k]["a6"], (((s[22][1] / s[16][1]) ** 2) - 1) * 100)  # 6개월 연율
        self.assertIsNone(rows[oil._mkey(D(2025, 1, 1))]["a3"])                          # 3개월 전이 결측월

    def test_p_grid_is_fixed(self):
        self.assertEqual(oil.P_GRID, {("H", "A"): "P+", ("H", "F"): "P+", ("H", "D"): "Pd",
                                      ("M", "A"): "P+", ("M", "F"): "P0", ("M", "D"): "P−",
                                      ("Lo", "A"): "P0", ("Lo", "F"): "P−", ("Lo", "D"): "P−"})
        self.assertEqual((oil.SUPPLY_HC, oil.H_IN, oil.H_OUT, oil.LO_IN, oil.LO_OUT, oil.MOM, oil.MOM_N, oil.MOM_DN,
                          oil.MOM_DN_N), (1.0, 3.1, 2.9, 2.6, 2.7, 0.5, 1, 0.3, 2))

    def test_pce_states_carry_the_band_and_read_the_grid(self):
        flat = lambda rate, n: [g_of(rate)] * n
        rows = oil.pce_states(oil.infl_rows(index(D(2018, 1, 1), flat(3.6, 30) + flat(3.0, 6) + flat(2.4, 30))))
        ms = sorted(rows)
        self.assertIsNone(rows[ms[11]]["band"])                                           # 첫 해 — 전년비 없음
        self.assertEqual(rows[ms[24]]["band"], "H")
        self.assertAlmostEqual(rows[ms[24]]["mom"], 0.0, places=9)
        self.assertEqual((rows[ms[24]]["mom_class"], rows[ms[24]]["P"]), ("F", "P+"))
        lows = [t for t in ms if rows[t]["Y3"] is not None and rows[t]["Y3"] < 2.9]
        self.assertEqual(rows[lows[0]]["band"], "M")                                      # 2.9 밑으로 와야 높음에서 나온다
        self.assertTrue(all(rows[t]["band"] == "H" for t in ms[24:] if t < lows[0]))
        self.assertTrue(any(2.9 <= rows[t]["Y3"] <= 3.1 for t in ms[24:] if t < lows[0]))  # 사이 구간을 실제로 지난다
        self.assertIsNone(rows[ms[0]]["mom_class"])
        self.assertEqual(rows[ms[0]]["P"], "?")

    def test_pce_states_keep_the_band_across_a_month_without_y3(self):
        # 높음(H)에 들어간 뒤 Y3가 빈 달이 끼어도 그다음 달은 직전 띠(H)에서 이어 읽는다 — 2.9~3.1 사이면 H에 머문다
        rows = {1: {"Y3": 3.5, "mom": 0.0}, 2: {"Y3": None, "mom": None}, 3: {"Y3": 3.0, "mom": 0.0},
                4: {"Y3": 2.95, "mom": 0.0}, 5: {"Y3": 2.85, "mom": 0.0}}
        out = oil.pce_states(rows)
        self.assertEqual([out[t]["band"] for t in sorted(out)], ["H", None, "H", "H", "M"])
        self.assertEqual(out[3]["P"], "P+")
        self.assertEqual(out[2]["P"], "?")
        rows = {1: {"Y3": 2.4, "mom": 0.0}, 2: {"Y3": None, "mom": None}, 3: {"Y3": 2.65, "mom": 0.0}}   # 낮음(Lo)도
        self.assertEqual([r["band"] for _, r in sorted(oil.pce_states(rows).items())], ["Lo", None, "Lo"])

    def cpi_pair(self, i4, core=2.0, months_n=30, start=D(2024, 4, 1)):
        """근원 연율 core로 고르게, 전체는 마지막 석 달만 연율 core + i4로 — 마지막 달의 I4 = i4."""
        core_s = index(start, [g_of(core)] * months_n)
        head_s = index(start, [g_of(core)] * (months_n - 3) + [g_of(core + i4)] * 3)
        return head_s, core_s

    def tag_world(self, i4, pce_rate, pce_end=None):
        head, core = self.cpi_pair(i4)
        pce = index(D(2023, 1, 1), [g_of(pce_rate)] * 45)                                 # 2023-01 ~ 2026-09
        if pce_end:
            pce = [p for p in pce if p[0] <= pce_end]
        return {"CPIAUCSL": head, "CPILFESL": core, "PCEPILFE": pce}

    def test_supply_tag_needs_p_plus_and_i4_at_least_one(self):
        for i4, rate, want_p, want in ((1.0, 3.6, "P+", ["공급형(에너지)"]), (0.9999, 3.6, "P+", []),
                                       (2.0, 2.8, "P0", []), (-1.0, 3.6, "P+", ["에너지 하락"]),
                                       (-1.5, 2.0, "P−", ["에너지 하락"]), (-0.99, 2.0, "P−", [])):
            v = oil.energy_tags(self.tag_world(i4, rate))
            self.assertEqual((v["p"], v["tags"]), (want_p, want), (i4, rate))
            self.assertAlmostEqual(v["i4"], i4, places=4)
            self.assertEqual((v["month"], v["pce_month"]), ("2026-09-01", "2026-09-01"))
            self.assertAlmostEqual(v["hc_pce"], i4, places=4)

    def test_tags_use_the_i4_of_the_pce_month(self):
        v = oil.energy_tags(self.tag_world(1.5, 3.6, pce_end=D(2026, 8, 1)))           # PCE가 CPI보다 한 달 늦다
        self.assertEqual((v["month"], v["pce_month"]), ("2026-09-01", "2026-08-01"))
        self.assertAlmostEqual(v["i4"], 1.5, places=4)
        self.assertLess(v["hc_pce"], 1.0)                                                 # 8월의 I4는 석 달 중 두 달만
        self.assertEqual(v["tags"], [])
        line, _ = oil.texts("i4", v, "2026-09-01")
        self.assertIn(" — 근원 PCE 2026-08 물가 상태 P+ · 그 달 I4 +", line)

    def test_i4_without_pce(self):
        S = self.tag_world(1.5, 3.6)
        del S["PCEPILFE"]
        c = oil.calc_i4(S)
        self.assertEqual((c["date"], c["values"]["p"], c["values"]["tags"], c["values"]["pce_month"]), ("2026-09-01", None, None, None))
        line, _ = oil.texts("i4", c["values"], c["date"])
        self.assertTrue(line.endswith(" · 꼬리표: 근원 PCE 미수신"), line)
        self.assertEqual([s["series"] for s in oil.sources_of(oil.BY_KEY["i4"], "2026-10-30", c["values"])],
                         ["CPIAUCSL", "CPILFESL"])
        with self.assertRaises(oil.ItemError):
            oil.calc_i4({"CPIAUCSL": S["CPIAUCSL"][:2], "CPILFESL": S["CPILFESL"]})

    def test_i4_line_and_definitions(self):
        c = oil.calc_i4(self.tag_world(1.2, 3.6))
        line, extra = oil.texts("i4", c["values"], c["date"])
        self.assertEqual(line, "2026-09 I4(CPI 전체 a3 − 근원 a3) +1.20%p · 꼬리표 공급형(에너지) — 근원 PCE 2026-09 물가 상태 P+ 기준")
        joined = " ".join(extra)
        for part in ("+1.0%p 이상", "-1.0%p 이하", "3.1% 넘으면", "2.9% 밑에서", "2.6% 밑이면", "2.7% 넘어서", "+0.5%p",
                     "-0.3%p 이하가 2개 발표", "높음 × 둔화 = Pd", "2026-10-14", "예측하지 않는다"):
            self.assertIn(part, joined)
        later = dict(c["values"], pce_month="2026-10-01", hc_pce=None)                   # PCE 달에 CPI가 없으면 그 달 I4는 —
        self.assertTrue(oil.texts("i4", later, c["date"])[0].endswith("물가 상태 P+ · 그 달 I4 — 기준"))

    # 상태 줄의 측정 기록
    def test_state_line_carries_the_measured_averages(self):
        self.assertEqual(oil.STATE_AVG, {"up": 2.43, "flat": 0.81, "down": -1.16, "all": 0.83})
        self.assertEqual(oil.STATE_N, {"up": 117, "flat": 204, "down": 92})
        v = oil.calc_state(self.S)["values"]
        line, extra = oil.texts("state", v, "2026-10-01")
        self.assertTrue(line.endswith(" — 측정 기록: 다음 3개월 CPI 에너지 평균 오름 +2.43% · 보합 +0.81% · 내림 -1.16% "
                                      "(전체 +0.83%, 1990~)"), line)
        self.assertIn("413개 — 오름 117 · 보합 204 · 내림 92", extra[2])
        self.assertIn("예측이 아니며", extra[2])

    # 미국 공급 반응
    def test_supply(self):
        v = oil.calc_supply(self.S)["values"]
        self.assertEqual((v["drill_month"], v["util_month"], v["util"], v["util_1y"]), ("2026-09-01", "2026-09-01", 85.0, 80.0))
        self.assertAlmostEqual(v["drill_yoy"], -10.0)
        line, _ = oil.texts("supply", v, "2026-09-01")
        self.assertEqual(line, "석유·가스 시추 생산 전년비 -10.0%(2026-09) · 석유·가스 추출 가동률 85.0%(2026-09, 1년 전 80.0%)")
        S = dict(self.S, CAPUTLG211S=[p for p in self.S["CAPUTLG211S"] if p[0] != D(2025, 9, 1)],
                 IPN213111N=[p for p in self.S["IPN213111N"] if p[0] != D(2025, 9, 1)])
        v = oil.calc_supply(S)["values"]
        self.assertIsNone(v["util_1y"])                                                  # 1년 전 같은 달이 없으면 비운다
        self.assertEqual(v["drill_month"], "2026-08-01")                                 # 전년비는 1년 전 같은 달이 있는 마지막 달
        self.assertIn("1년 전 —", oil.texts("supply", v, "2026-09-01")[0])
        self.assertIn("시추 생산 전년비 +12.5%(", oil.texts("supply", dict(v, drill_yoy=12.5), "2026-09-01")[0])

    # 두바이 × 원/달러
    def test_dubai_split_adds_up_and_uses_monthly_fx(self):
        v = oil.calc_dubai(self.S)["values"]
        fx = lambda y, m: statistics.fmean(x for d, x in self.S["DEXKOUS"] if (d.year, d.month) == (y, m))
        k1, k0 = fx(2026, 9), fx(2025, 9)
        self.assertEqual(v["month"], "2026-09-01")
        self.assertAlmostEqual(v["yoy"], (77 * k1 / (70 * k0) - 1) * 100, places=3)
        self.assertAlmostEqual(v["usd_pp"] + v["fx_pp"], v["yoy"], places=3)
        lb, lk = math.log(77 / 70), math.log(k1 / k0)
        self.assertAlmostEqual(v["usd_pp"], v["yoy"] * lb / (lb + lk), places=3)
        self.assertAlmostEqual(v["krw"], 77 * k1 / 10000, places=3)
        line, extra = oil.texts("dubai", v, v["month"])
        a, b, c = [float(x) for x in re.findall(r"[+-]\d+\.\d", line.split("전년비 ")[1])]
        self.assertAlmostEqual(b + c, a, places=6)
        self.assertIn("IMF 두바이", extra[0])

    def test_dubai_month_needs_ten_fx_days(self):
        S = dict(self.S, DEXKOUS=[p for p in self.S["DEXKOUS"] if not (p[0].year == 2026 and p[0].month == 9 and p[0].day > 9)])
        self.assertEqual(oil.calc_dubai(S)["values"]["month"], "2026-08-01")
        with self.assertRaises(oil.ItemError):
            oil.calc_dubai(dict(self.S, POILDUBUSDM=self.S["POILDUBUSDM"][-6:]))           # 1년 전 달이 없다

    # 직전 파일 검사 — 새 꼴
    def test_previous_item_kinds(self):
        good = oil.build(oil.compute(self.S, {}, NOW.date()), {}, NOW)["items"]
        self.assertIsNotNone(oil.core_of(good["i4"], "i4"))
        for bad in ({"tags": ["매수"]}, {"tags": ["공급형(에너지)", "공급형(에너지)"]}, {"tags": "공급형(에너지)"},
                    {"p": "P++"}, {"p": 3}):
            it = json.loads(json.dumps(good["i4"]))
            it["values"].update(bad)
            self.assertIsNone(oil.core_of(it, "i4"), bad)
        it = json.loads(json.dumps(good["crude"]))
        it["values"]["real_n"] = -3
        self.assertIsNone(oil.core_of(it, "crude"))
        it["values"]["real_n"] = None
        self.assertIsNotNone(oil.core_of(it, "crude"))


class LicenceTest(unittest.TestCase):
    def test_series_list_is_fixed_and_public(self):
        self.assertEqual(set(oil.SERIES), {"DCOILBRENTEU", "DCOILWTICO", "GASREGW", "GASDESW", "DGASNYH", "DDFUELNYH",
                                           "CPIENGSL", "CPIAUCSL", "CPILFESL", "DEXKOUS", "T5YIE", "T5YIFR",
                                           "PCEPILFE", "IPN213111N", "CAPUTLG211S", "POILDUBUSDM"})
        self.assertEqual(oil.SERIES[-4:], ["PCEPILFE", "IPN213111N", "CAPUTLG211S", "POILDUBUSDM"])   # 새로 더한 것은 끝
        self.assertEqual(set(oil.LICENCE), set(oil.SERIES))
        self.assertEqual({s for s, v in oil.LICENCE.items() if v != "public-domain"}, {"T5YIE", "T5YIFR", "POILDUBUSDM"})
        self.assertEqual(set(oil.LICENCE.values()), {"public-domain", "citation-required"})
        self.assertFalse(set(oil.SERIES) & (set(rp.RESTRICTED) | set(ai.RESTRICTED)))
        for spec in oil.ITEMS:
            self.assertLessEqual(set(spec["series"]) | set(spec.get("optional", ())), set(oil.SERIES))
            self.assertFalse(set(spec["series"]) & set(spec.get("optional", ())))
            for field in spec.get("optional", {}).values():
                self.assertIn(field, spec["values"])
        self.assertEqual({sid for sid in oil.SERIES if oil.LICENCE[sid] == "citation-required"}, set(oil.SERIES_NOTICES))
        self.assertEqual(oil.SOURCES["POILDUBUSDM"], ("International Monetary Fund", "Global price of Dubai Crude"))

    def test_citation_required_items_carry_the_notice(self):
        self.assertIn(oil.CITATION_NOTICE, oil.notices(oil.BY_KEY["bei"]))
        self.assertEqual(oil.notices(oil.BY_KEY["dubai"]), [oil.COMPUTED_NOTICE, oil.IMF_NOTICE])
        for key in ("crude", "korea", "cpi", "i4", "supply"):
            self.assertEqual(oil.notices(oil.BY_KEY[key]), [oil.COMPUTED_NOTICE])
        self.assertIn("Copyright © International Monetary Fund", oil.IMF_NOTICE)
        self.assertIn("계산값", oil.IMF_NOTICE)
        self.assertEqual(oil.citation("POILDUBUSDM", "2026-10-30"),
                         "International Monetary Fund, Global price of Dubai Crude [POILDUBUSDM], retrieved from FRED, "
                         "Federal Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/POILDUBUSDM, October 30, 2026.")


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
        used = lambda key: [src["series"] for src in js["items"][key]["sources"]]
        self.assertEqual(used("crude"), ["DCOILBRENTEU", "DCOILWTICO", "CPIAUCSL"])    # 분위를 채웠으니 CPI도 출처에
        self.assertEqual(used("i4"), ["CPIAUCSL", "CPILFESL", "PCEPILFE"])
        self.assertEqual(used("dubai"), ["POILDUBUSDM", "DEXKOUS"])
        self.assertIn(oil.IMF_NOTICE, js["items"]["dubai"]["notices"])
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
        self.assertFalse(items["dubai"]["ok"])                                    # 원/달러를 함께 쓰는 두바이 줄도
        self.assertTrue(all(items[x]["ok"] for x in items if x not in oil.KOREA))
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

    def test_previous_checks_the_schema(self):
        good = {"crude": {"key": "crude"}, "base": {"key": "base"}}
        os.makedirs(self.out)
        for js, want in (({"schema": oil.SCHEMA, "items": good}, good),
                         ({"schema": oil.SCHEMA + 1, "items": good}, {}),
                         ({"items": good}, {}),
                         ({"schema": oil.SCHEMA, "items": [good]}, {}),
                         ([good], {}),
                         ({"schema": oil.SCHEMA, "items": dict(good, zzz={"key": "zzz"}, cpi="x")}, good)):
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(js, f)
            self.assertEqual(oil.previous(self.out), want, js)
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{깨진")
        self.assertEqual(oil.previous(self.out), {})

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
            self.assertNotIn(word, no_tags(dump), word)
        urls = {u.rstrip(".") for u in re.findall(r"https?://[^\s,;)\"]+", dump)}
        self.assertEqual(urls, {f"https://fred.stlouisfed.org/series/{sid}" for sid in oil.SERIES})
        self.assertNotIn("bad.invalid", dump)
        errors = {it["error"] for it in self.saved()["items"].values()} - {None}
        self.assertLessEqual(errors, set(oil.REASONS.values()))
        nested = re.compile(r"\([^()]*\(")
        for t in re.findall(r'"((?:[^"\\]|\\.)*)"', dump):
            self.assertIsNone(nested.search(t), t)


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

    def test_readme_counts(self):
        readme = self.read("README.md")
        m = re.search(r"\*\*아침 쪽 Python 테스트 (\d+)개 \+ node 테스트 (\d+)개\*\*\((.*?)\)와 \*\*저녁판", readme)
        py_part, node_part = m.group(3).split(" / node: ")
        nums = lambda part: [int(x) for x in re.findall(r" (\d+)(?= · |$)", re.sub(r"\([^()]*\)", "", part))]
        self.assertEqual(sum(nums(py_part)), int(m.group(1)))
        self.assertEqual(sum(nums(node_part)), int(m.group(2)))
        mine = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()
        self.assertIn(f" · 유가·에너지 참고 {mine} · ", py_part)
        cjs = len(re.findall(r"^test\(", self.read("scripts", "test_oil_render.cjs"), flags=re.M))
        self.assertTrue(node_part.endswith(f" · 유가 카드 그리기 {cjs}"), node_part)

    def test_page_wires_the_card_and_the_korea_line(self):
        page = self.read("site", "index.html")
        self.assertIn('getJson("data/oil.json")', page)
        self.assertIn('<script src="oil.js"></script>', page)
        self.assertIn('<a href="data/oil.json">', page)
        self.assertIn('g.id === "inflation" ? el("div", {id:"oil-slot"', page)   # 물가 묶음 안
        korea = page[page.index('<section id="korea-market"'):]
        self.assertIn('<div id="korea-oil" class="panel korea-oil" hidden', korea[:korea.index("</section>")])
        self.assertIn("window.OilEnergy.render(oil.value)", page)

    def test_card_shows_the_citations_the_notices_promise_and_one_intro(self):
        # CITATION_NOTICE·IMF_NOTICE는 'FRED 권장 인용과 함께 싣는다'고 적는다 — 화면이 그 licence의 citation을 글자로 싣는다
        js = self.read("site", "oil.js")
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        lic = re.search(r'const CITE_LICENCE = "([^"]+)";', code).group(1)
        self.assertEqual({sid for sid, v in oil.LICENCE.items() if v == lic}, {"T5YIE", "T5YIFR", "POILDUBUSDM"})
        self.assertEqual({sid for sid, t in oil.SERIES_NOTICES.items() if "함께 싣는다" in t}, {"T5YIE", "T5YIFR", "POILDUBUSDM"})
        self.assertIn("citeLines(items, CARD)", code)                              # 카드(T5YIE·T5YIFR)
        self.assertIn("citeLines(items, shown)", code)                             # 한국 시장 줄(두바이)
        self.assertNotIn("d.notice", code)
        about = "".join(re.findall(r'"([^"]*)"', code[code.index("const ABOUT = "):].split(";\n", 1)[0]))
        for sent in filter(None, re.split(r"(?<=\.)\s+", about)):
            self.assertTrue(sent.endswith("니다."), sent)
        for mine, theirs in (("규칙 수에 들지 않는", "규칙 점검에 쓰지 않는"), ("공개 통계와 그 산술", "공개 통계로 계산한 산술"),
                             ("유가나 금리를 예측하지 않습니다", "유가나 금리를 예측하지 않는다")):
            self.assertIn(mine, about)
            self.assertIn(theirs, oil.NOTICE)

    def test_screen_script_matches_the_file_and_avoids_verdict_words(self):
        js = self.read("site", "oil.js")
        card = re.findall(r'"(\w+)"', js[js.index("const CARD = ["):].split("]")[0])
        self.assertEqual(card, [s["key"] for s in oil.ITEMS if s["key"] not in oil.KOREA])
        korea = re.findall(r'"(\w+)"', js[js.index("const KOREA = ["):].split("]")[0])
        self.assertEqual(korea, [s["key"] for s in oil.ITEMS if s["key"] in oil.KOREA])
        self.assertEqual(list(oil.KOREA), korea)
        reasons = re.findall(r'"([^"]+)"', js[js.index("const REASONS = ["):].split("];")[0])
        self.assertEqual(reasons, list(oil.REASONS.values()))
        for tok in ("innerHTML", "outerHTML", "insertAdjacentHTML", "createElement", "fetch(", "eval("):
            self.assertNotIn(tok, js)
        body = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        for word in list(FORBIDDEN_TEXT) + list(VERDICT):
            self.assertNotIn(word, no_tags(body), word)
        self.assertIn('key === "state" ? el("p", { class: "oil-note" }, STATE_NOTE)', js)   # 상태 줄에는 늘 정의 안내
        css = self.read("site", "dashboard.css")
        self.assertRegex(css, r"\.oil-card p, \.korea-oil p \{[^}]*overflow-wrap: anywhere")


if __name__ == "__main__":
    unittest.main(verbosity=1)
