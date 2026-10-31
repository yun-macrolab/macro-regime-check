#!/usr/bin/env python3
"""기간 프리미엄 모형 대조 참고 자료(tp_fetch) 테스트 — 산식(답을 아는 합성 자료: 4주 변화·σ·z·점수, 10년 중 몫, 월간 대조의
z·경우·해석 갈림·몫·일치도), ACM CSV 해석, 칸마다 실패·직전 값 이어 싣기, ACM 주소 넘김·크기·마감, 이용 조건과 출처 표기,
문구 원칙(정해 둔 글뿐), 화면 스크립트와 자료 파일의 짝, 페이지·워크플로·README 연결.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — FRED는 가짜 loader, ACM은 가짜 opener 또는 합성 캐시(--offline). 숫자는 모두 지어낸 것이다.
"""
import os, sys, io, re, json, math, datetime, tempfile, unittest, shutil, contextlib, statistics
from unittest import mock

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import tp_fetch as tp
import ai_invest_fetch as ai
import render_public as rp
from test_render_public import FORBIDDEN_TEXT

REPO = os.path.dirname(SCRIPTS)
D = datetime.date
TODAY = D(2026, 10, 30)
NOW = datetime.datetime(2026, 10, 30, 22, 17, tzinfo=datetime.timezone.utc)
# 공개 카드에 없어야 하는 낱말 — FORBIDDEN_TEXT에 더해 판정·시장 전망 낱말과 운영자 시트의 내부 이름
WORDS = ("판정", "충족", "신호", "경보", "전망", "매수", "매도", "⚠", "강세", "약세", "호재", "악재", "우려", "부담",
         "12행", "정책 행", "10·11행", "시트", "메모")


def fridays(start, end):
    out, d = [], start
    while d <= end:
        out.append(d)
        d += datetime.timedelta(days=7)
    return out


def friday_world():
    """금요일 KW: 2023-01-06부터 4주씩 0.50 · 0.60 번갈아(4주 변화가 늘 ±10bp), 그 전은 0.50, 마지막 관측(2026-10-16)만 +0.25.
    2023년 이후 금요일 198개 → 4주 변화 194개: +10이 97개, −10이 96개, 마지막(+10 + 25) = +35. 적합 10년 = 3.0 + 2 × TP."""
    fr = fridays(D(2022, 1, 7), D(2026, 10, 16))
    k0 = fr.index(D(2023, 1, 6))
    kw = [(d, 0.5 if i < k0 else 0.5 + 0.10 * (((i - k0) // 4) % 2)) for i, d in enumerate(fr)]
    kw[-1] = (kw[-1][0], kw[-1][1] + 0.25)
    fy = [(d, 3.0 + 2 * v) for d, v in kw]
    return kw, fy


def month_ends(start, n):
    out, (y, m) = [], (start.year, start.month)
    for _ in range(n):
        y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        out.append(D(y2, m2, 1) - datetime.timedelta(days=1))
        y, m = y2, m2
    return out


# 월간 세계: 2022-12-31부터 월말 25개 → 2023년 이후 달 24개. 변화(bp) — 앞 22달은 ACM ±5 · KW ±4 같은 부호로 번갈아,
# 23번째 ACM +2 · KW +3, 마지막(2024-12) ACM +2 · KW +12. 실제 10년(GSW) 변화 = 2.5 × KW 변화(마지막 +30)
A_D = [5 if i % 2 == 0 else -5 for i in range(22)] + [2, 2]
K_D = [4 if i % 2 == 0 else -4 for i in range(22)] + [3, 12]
G_D = [2.5 * k for k in K_D]


def month_world(a_d=A_D, k_d=K_D, g_d=G_D, gsw=True):
    ends = month_ends(D(2022, 12, 1), 25)
    acm, kw, a, k, g = [], [], 0.80, 1.00, 4.00
    for i, e in enumerate(ends):
        if i:
            a, k, g = a + a_d[i - 1] / 100, k + k_d[i - 1] / 100, g + g_d[i - 1] / 100
        acm.append({"date": e, "tp": a, "fit": 4.0, "gsw": g if gsw else None})
        kw.append((e, k))
    return kw, acm


def acm_csv(rows, cols=("TERMYld", "ACMFITYld", "GSWYld"), eol="\n"):
    key = {"TERMYld": "tp", "ACMFITYld": "fit", "GSWYld": "gsw"}
    mon = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    return "RunDates," + ",".join(cols) + eol + "".join(
        f"{r['date'].day:02d}-{mon[r['date'].month - 1]}-{r['date'].year}," + ",".join(
            "" if r.get(key[c]) is None else f"{r[key[c]]:.6f}" for c in cols) + eol for r in rows)


def full_world(end=D(2026, 10, 23)):
    """일간 KW(영업일) + 적합 10년 + ACM 월말(2021-01 ~ 2026-09). 값은 지어낸 물결."""
    days, d = [], D(2021, 1, 4)
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += datetime.timedelta(days=1)
    kw = [(d, round(0.6 + 0.3 * math.sin(i / 37) + 0.05 * math.sin(i / 5), 4)) for i, d in enumerate(days)]
    fy = [(d, round(4.0 + 2 * v, 4)) for d, v in kw]
    rows = []
    for i, e in enumerate(month_ends(D(2020, 12, 1), 70)):
        k = tp.ff.on_or_before(kw, e)
        if k:
            rows.append({"date": e, "tp": round(0.4 + 0.8 * k[1] + 0.03 * math.sin(i), 4), "fit": 4.2,
                         "gsw": round(4.3 + 2 * k[1], 4)})
    return {"THREEFYTP10": kw, "THREEFY10": fy}, rows


class FakeFred:
    def __init__(self, data, fail=(), cache=()):
        self.data, self.fail, self.cache, self.calls = data, set(fail), set(cache), []

    def __call__(self, sid, cache_dir, offline=False, timeout=None):
        self.calls.append((sid, timeout))
        if sid in self.fail:
            raise RuntimeError(f"{sid}: 원문 사유 https://bad.invalid/xyz-77")
        return list(self.data[sid]), ("cache" if sid in self.cache else "net")


class FakeResponse:
    def __init__(self, body, final, clock=None, step=0.0, chunk=4096):
        self.body, self.final, self.clock, self.step, self.chunk, self.pos = body, final, clock, step, chunk, 0

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def geturl(self):
        return self.final

    def read1(self, n):
        if self.clock:
            self.clock.t += self.step
        out = self.body[self.pos:self.pos + min(n, self.chunk)]
        self.pos += len(out)
        return out


class FakeOpener:
    """ACM 주소만 받는다(다른 주소는 실패). final로 넘겨진 주소, step으로 읽을 때마다 흐르는 시간을 흉내 낸다."""
    def __init__(self, text, final=tp.ACM_URL, clock=None, step=0.0, chunk=4096):
        self.body, self.final, self.clock, self.step, self.calls = text.encode("utf-8"), final, clock, step, []
        self.chunk = chunk

    def __call__(self, url, timeout=None):
        self.calls.append((url, timeout))
        if url != tp.ACM_URL:
            raise AssertionError(f"뜻밖의 요청 {url}")
        return FakeResponse(self.body, self.final, self.clock, self.step, self.chunk)


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class ArithmeticTest(unittest.TestCase):
    def test_tp_score_boundaries(self):
        for z, want in ((0.0, 0), (0.999, 0), (-0.999, 0), (1.0, -1), (-1.0, 1), (1.999, -1), (2.0, -2), (-2.0, 2),
                        (7.5, -2), (-7.5, 2)):
            self.assertEqual(tp.tp_score(z), want, z)
            self.assertIs(type(tp.tp_score(z)), int)

    def test_classify_and_split_table(self):
        for za, zk, case, split in ((1.2, 0.3, "ACM만", True), (1.05, 0.86, "ACM만", False),   # 문턱에 걸친 작은 차이
                                    (0.29, 1.33, "KW만", True), (-1.2, 1.1, "반대", True), (1.2, 1.5, "공통 TP↑", False),
                                    (-1.2, -1.0, "공통 TP↓", False), (0.5, -0.4, "둘 다 약함", False),
                                    (1.0, 0.3, "ACM만", True), (1.0, 0.31, "ACM만", False)):
            self.assertEqual(tp.classify(za, zk), case, (za, zk))
            self.assertEqual(tp.is_split(za, zk), split, (za, zk))

    def test_parse_acm_reads_columns_by_name_and_skips_bad_lines(self):
        text = ("RunDates,GSWYld,TERMYld\r\n31-Aug-2026,4.2,0.55\r\nbad,line\r\n30-Sep-2026,4.3,0.61\r\n"
                "15-Foo-2026,1,2\r\n31-Oct-2026,4.4,nan\r\n31-Jul-2026,4.1,0.50\r\n")
        rows = tp.parse_acm(text)
        self.assertEqual([r["date"] for r in rows], [D(2026, 7, 31), D(2026, 8, 31), D(2026, 9, 30)])   # 날짜순, nan TP는 버림
        self.assertEqual([(r["tp"], r["gsw"], r["fit"]) for r in rows], [(0.5, 4.1, None), (0.55, 4.2, None), (0.61, 4.3, None)])
        self.assertEqual([r["tp"] for r in tp.parse_acm("RunDates,X\n31-Aug-2026,0.7\n")], [0.7])     # 이름이 없으면 둘째 열
        self.assertEqual(tp.parse_acm(""), [])
        self.assertEqual(tp.parse_acm("RunDates,TERMYld\n"), [])

    def test_month_ends_takes_the_last_row_of_each_month(self):
        rows = [{"date": D(2026, 8, d), "tp": d / 100} for d in (3, 17, 31)] + [{"date": D(2026, 9, 2), "tp": 0.9}]
        self.assertEqual([r["date"] for r in tp.month_ends(rows)], [D(2026, 8, 31), D(2026, 9, 2)])

    def test_weekly_change_sigma_z_and_score(self):
        kw, fy = friday_world()
        v = tp.calc_weekly({tp.KW_ID: kw}, TODAY)["values"]
        sigma = statistics.stdev([10.0] * 97 + [-10.0] * 96 + [35.0])
        self.assertEqual((v["kw_asof"], v["kw_base"], v["sigma_n"]), ("2026-10-16", "2026-09-18", 194))
        self.assertAlmostEqual(v["tp_4w_bp"], 35.0)
        self.assertEqual(v["sigma_bp"], round(sigma, 1))                          # 비공개 tp_auto와 같은 자리(bp 1자리)
        self.assertAlmostEqual(v["z"], 35.0 / sigma, places=5)
        self.assertEqual((v["score"], v["age"]), (-2, None))                    # z ≈ 3.39 — 기간 프리미엄이 오르면 −
        down = kw[:-1] + [(kw[-1][0], kw[-1][1] - 0.50)]                          # 마지막 4주 −15bp(0.50 → 0.35)
        v = tp.calc_weekly({tp.KW_ID: down}, TODAY)["values"]
        self.assertAlmostEqual(v["tp_4w_bp"], -15.0)
        self.assertAlmostEqual(v["z"], -15.0 / statistics.stdev([10.0] * 97 + [-10.0] * 96 + [-15.0]), places=5)
        self.assertEqual(v["score"], 1)                                           # z ≈ −1.49 — 내리면 +

    def test_weekly_base_is_the_last_observation_28_days_back_or_earlier(self):
        kw, _ = friday_world()
        gap = [p for p in kw if p[0] != D(2026, 9, 18)]
        v = tp.calc_weekly({tp.KW_ID: gap}, TODAY)["values"]
        self.assertEqual(v["kw_base"], "2026-09-11")

    def test_weekly_needs_twenty_four_week_changes(self):
        kw, _ = friday_world()
        short = [p for p in kw if p[0] >= D(2026, 6, 1) or p[0] < D(2023, 1, 1)]    # 2023년 이후 금요일 20개 → 변화 16개
        n = sum(1 for d, _ in short if d >= D(2023, 1, 1)) - 4
        self.assertLess(n, tp.MIN_SIGMA_OBS)
        with self.assertRaises(tp.ItemError):
            tp.calc_weekly({tp.KW_ID: short}, TODAY)
        flat = [(d, 0.5) for d, _ in kw]
        with self.assertRaises(tp.ItemError):                                     # σ = 0
            tp.calc_weekly({tp.KW_ID: flat}, TODAY)
        with self.assertRaises(tp.ItemError):                                     # 4주 전 관측 없음
            tp.calc_weekly({tp.KW_ID: kw[-3:]}, TODAY)

    def test_weekly_older_than_14_days_keeps_numbers_without_a_score(self):
        kw, _ = friday_world()                                                    # 마지막 관측 10-16
        v = tp.calc_weekly({tp.KW_ID: kw}, D(2026, 10, 30))["values"]
        self.assertEqual((v["score"], v["age"]), (-2, None))                      # 14일 — 매긴다
        v = tp.calc_weekly({tp.KW_ID: kw}, D(2026, 10, 31))["values"]
        self.assertEqual((v["score"], v["age"]), (None, 15))                      # 15일 — 매기지 않는다
        self.assertAlmostEqual(v["tp_4w_bp"], 35.0)
        line, _ = tp.texts("weekly", v, v["kw_asof"])
        self.assertIn("운영자 주간 점수 없음(마지막 관측이 15일 전 — 14일 넘음)", line)

    def test_ten_year_share_and_typical_share(self):
        kw, fy = friday_world()
        v = tp.calc_weekly({tp.KW_ID: kw, tp.FY_ID: fy}, TODAY)["values"]
        self.assertAlmostEqual(v["y_4w_bp"], 70.0)                                # 2 × 35
        self.assertAlmostEqual(v["tp_share"], 0.5)
        self.assertAlmostEqual(v["tp_share_typical"], 0.5)                        # ΔTP = 0.5 × Δ10년, 모든 주
        v = tp.calc_weekly({tp.KW_ID: kw, tp.FY_ID: fy[:-1]}, TODAY)["values"]     # 10년 관측일이 TP와 다르면 비운다
        self.assertEqual((v["y_4w_bp"], v["tp_share"], v["tp_share_typical"]), (None, None, None))
        small = kw[:-1] + [(kw[-1][0], kw[-5][1] + 0.04)]                         # ΔTP +4bp → 10년 +8bp(10bp 미만)
        fy2 = [(d, 3.0 + 2 * x) for d, x in small]
        v = tp.calc_weekly({tp.KW_ID: small, tp.FY_ID: fy2}, TODAY)["values"]
        self.assertAlmostEqual(v["y_4w_bp"], 8.0)
        self.assertIsNone(v["tp_share"])
        self.assertAlmostEqual(v["tp_share_typical"], 0.5)

    def test_weekly_acm_reference_and_split(self):
        kw, acm = month_world()
        v = tp.calc_weekly({tp.KW_ID: kw, tp.ACM: acm}, D(2025, 1, 10))["values"]
        self.assertEqual(v["acm_month"], "2024-12-31")
        self.assertAlmostEqual(v["acm_month_bp"], 2.0)
        self.assertAlmostEqual(v["kw_same_month_bp"], 12.0)
        self.assertIs(v["models_agree"], True)
        sa, sk = statistics.stdev(A_D), statistics.stdev(K_D)
        self.assertAlmostEqual(v["acm_z"], 2 / sa, places=2)
        self.assertAlmostEqual(v["kw_month_z"], 12 / sk, places=2)
        pairs = tp.month_pairs(kw, [(r["date"], r["tp"]) for r in acm])          # 원값 z — 비공개 tp_auto처럼 3자리로 한 번만
        za = pairs[-1][1] / statistics.stdev(p[1] for p in pairs)
        zk = pairs[-1][2] / statistics.stdev(p[2] for p in pairs)
        self.assertEqual((v["acm_z"], v["kw_month_z"]), (round(za, 3), round(zk, 3)))
        self.assertEqual((v["models_case"], v["models_split"]), ("KW만", True))
        _, extra = tp.texts("weekly", v, v["kw_asof"])
        ref = [t for t in extra if t.startswith("ACM 참고")][0]
        self.assertEqual(ref, f"ACM 참고: 2024-12 +2.0bp, 같은 기간 Kim-Wright +12.0bp — 해석 갈림(z ACM {round(za, 3):+.2f} · "
                              f"KW {round(zk, 3):+.2f}): 이 점수만 보지 말고 정책 기대의 변화와 함께 볼 것")

    def test_weekly_numbers_round_once_like_the_private_line(self):
        # 원값을 비공개 tp_auto의 자리(bp 1 · 몫 3)로 곧장 — 4자리로 저장한 뒤 다시 반올림하면 -8.14999가 -8.2로 보였다
        kw, _ = friday_world()
        kw = kw[:-1] + [(kw[-1][0], kw[-5][1] - 0.0814999)]                       # 4주 −8.14999bp
        fy = [(d, 3.0 + 2 * x) for d, x in kw]
        fy[-1] = (fy[-1][0], fy[-5][1] - 0.1004999)                               # 같은 4주 10년 −10.04999bp
        v = tp.calc_weekly({tp.KW_ID: kw, tp.FY_ID: fy}, TODAY)["values"]
        chg, y = (kw[-1][1] - kw[-5][1]) * 100, (fy[-1][1] - fy[-5][1]) * 100
        self.assertAlmostEqual(chg, -8.14999, places=9)
        self.assertEqual((v["tp_4w_bp"], v["y_4w_bp"], v["tp_share"]), (-8.1, -10.0, round(chg / y, 3)))
        line, extra = tp.texts("weekly", v, v["kw_asof"])
        self.assertIn("4주(2026-09-18부터) -8.1bp ÷ σ ", line)
        self.assertNotIn("-8.2bp", line)
        self.assertTrue(extra[0].startswith("같은 4주 10년(Kim-Wright 적합) -10.0bp 중 기간 프리미엄 81%"), extra[0])
        wk = [x for x in tp.ff.weekly_last(kw) if x[0] >= tp.SIGMA_SINCE]          # 평소 몫(기울기)도 3자리에서 한 번
        fyd = dict(tp.ff.weekly_last(fy))
        slope = statistics.linear_regression([(fyd[b[0]] - fyd[a[0]]) * 100 for a, b in zip(wk, wk[4:])],
                                             [(b[1] - a[1]) * 100 for a, b in zip(wk, wk[4:])]).slope
        self.assertNotEqual(round(slope, 4), round(slope, 3))                       # 4자리로 두면 다른 값이 되는 경우
        self.assertEqual(v["tp_share_typical"], round(slope, 3))
        # 몫은 3자리에서 한 번 — 원값 0.6347은 비공개 줄처럼 64%(0.635)
        kw2 = kw[:-1] + [(kw[-1][0], kw[-5][1] + 0.06347)]
        fy2 = [(d, 3.0 + 2 * x) for d, x in kw2]
        fy2[-5], fy2[-1] = (fy2[-5][0], 0.0), (fy2[-1][0], 0.1)                   # 10년 정확히 +10bp
        v = tp.calc_weekly({tp.KW_ID: kw2, tp.FY_ID: fy2}, TODAY)["values"]
        self.assertEqual(v["tp_share"], 0.635)
        self.assertIn("+10.0bp 중 기간 프리미엄 64%", tp.texts("weekly", v, v["kw_asof"])[1][0])

    def test_weekly_share_from_exactly_10bp_like_the_private_rule(self):
        # 비공개 tp_auto: |10년 4주 변화| ≥ 10bp면 몫을 낸다(경계 포함)
        kw, _ = friday_world()
        kw = kw[:-1] + [(kw[-1][0], kw[-5][1] + 0.05)]                            # ΔTP +5bp
        for f0, f1, want in ((0.0, 0.1, 0.5), (0.1, 0.0, -0.5), (0.0, 0.0999, None), (0.0999, 0.0, None)):
            fy = [(d, 3.0 + 2 * x) for d, x in kw]
            fy[-5], fy[-1] = (fy[-5][0], f0), (fy[-1][0], f1)
            if want is not None:
                self.assertEqual(abs((f1 - f0) * 100), tp.MIN_SHARE_BP)             # 정말 경계값인지
            v = tp.calc_weekly({tp.KW_ID: kw, tp.FY_ID: fy}, TODAY)["values"]
            self.assertEqual(v["tp_share"], want, (f0, f1))

    def test_weekly_acm_z_only_when_the_last_acm_month_has_a_kim_wright_pair(self):
        # 마지막 ACM 달(2024-12)에 Kim-Wright 짝이 없으면 z를 싣지 않는다 — 앞 달(11월, 해석 갈림)의 z가 12월 이름으로 나가지 않게
        kw, acm = month_world(k_d=K_D[:-2] + [9, 12])
        moved = kw[:-1] + [(kw[-1][0] - datetime.timedelta(days=8), kw[-1][1])]   # 12월 말 관측이 8일 앞(7일 넘음)
        pairs = tp.month_pairs(moved, [(r["date"], r["tp"]) for r in acm])
        self.assertGreaterEqual(len(pairs), tp.MIN_PAIRS)                          # 앞 달들은 넉넉하다
        self.assertEqual(pairs[-1][0], D(2024, 11, 30))
        sa, sk = statistics.stdev(p[1] for p in pairs), statistics.stdev(p[2] for p in pairs)
        self.assertTrue(tp.is_split(pairs[-1][1] / sa, pairs[-1][2] / sk))         # 11월만 보면 해석 갈림
        v = tp.calc_weekly({tp.KW_ID: moved, tp.ACM: acm}, D(2025, 1, 10))["values"]
        self.assertEqual(v["acm_month"], "2024-12-31")
        self.assertEqual((v["acm_z"], v["kw_month_z"], v["models_case"], v["models_split"]), (None, None, None, None))
        ref = [t for t in tp.texts("weekly", v, v["kw_asof"])[1] if t.startswith("ACM 참고")][0]
        self.assertTrue(ref.startswith("ACM 참고: 2024-12 +2.0bp"), ref)
        self.assertNotIn("해석 갈림", ref)
        self.assertNotIn("z ACM", ref)

    def test_weekly_acm_direction_differs_and_too_few_months(self):
        kw, acm = month_world(a_d=A_D[:-1] + [-2], k_d=K_D[:-1] + [3])           # 둘 다 약함 · 방향 다름
        v = tp.calc_weekly({tp.KW_ID: kw, tp.ACM: acm}, D(2025, 1, 10))["values"]
        self.assertEqual((v["models_agree"], v["models_split"], v["models_case"]), (False, False, "둘 다 약함"))
        _, extra = tp.texts("weekly", v, v["kw_asof"])
        self.assertTrue(any(t.endswith("— 모형 방향 다름") for t in extra))
        late = [r for r in acm if r["date"] >= D(2024, 1, 31)]                    # 같은 기간 달 11개 — z를 내지 않는다
        v = tp.calc_weekly({tp.KW_ID: kw, tp.ACM: late}, D(2025, 1, 10))["values"]
        self.assertIsNotNone(v["acm_month_bp"])
        self.assertEqual((v["acm_z"], v["kw_month_z"], v["models_case"], v["models_split"]), (None, None, None, None))
        late = [r for r in acm if r["date"] >= D(2023, 12, 31)]                   # 12개 — 낸다(비공개 원본: 12쌍 이상)
        self.assertEqual(len(tp.month_pairs(kw, [(r["date"], r["tp"]) for r in late])), tp.MIN_PAIRS)
        v = tp.calc_weekly({tp.KW_ID: kw, tp.ACM: late}, D(2025, 1, 10))["values"]
        self.assertIsNotNone(v["acm_z"])
        v = tp.calc_weekly({tp.KW_ID: kw}, D(2025, 1, 10))["values"]
        _, extra = tp.texts("weekly", v, v["kw_asof"])
        self.assertIn("ACM 참고 불가 — 이번에 받지 못했거나 견줄 관측이 모자람", extra)

    def test_models_known_world(self):
        kw, acm = month_world()
        v = tp.calc_models({tp.KW_ID: kw, tp.ACM: acm})["values"]
        sa, sk = statistics.stdev(A_D), statistics.stdev(K_D)
        self.assertEqual((v["month"], v["first"], v["n"], v["yield_src"]), ("2024-12-31", "2023-01-31", 24, "GSW"))
        self.assertAlmostEqual(v["dy"], 30.0)
        self.assertAlmostEqual(v["acm_dtp"], 2.0)
        self.assertAlmostEqual(v["kw_dtp"], 12.0)
        self.assertAlmostEqual(v["z_acm"], 2 / sa, places=5)
        self.assertAlmostEqual(v["z_kw"], 12 / sk, places=5)
        self.assertEqual((v["case"], v["split"]), ("KW만", True))
        self.assertAlmostEqual(v["share_kw"], 0.4)                                # 12 / 30
        self.assertAlmostEqual(v["share_acm"], 2 / 30, places=4)
        self.assertAlmostEqual(v["typ_kw"], 0.4)                                  # 10년 = 2.5 × KW, 모든 달
        mg = statistics.fmean(G_D)
        beta = sum((g - mg) * (a - statistics.fmean(A_D)) for g, a in zip(G_D, A_D)) / sum((g - mg) ** 2 for g in G_D)
        self.assertAlmostEqual(v["typ_acm"], beta, places=4)
        self.assertEqual(v["recent"], [["2024-10-31", "ACM만", False], ["2024-11-30", "둘 다 약함", False],
                                       ["2024-12-31", "KW만", True]])
        self.assertAlmostEqual(v["corr12"], statistics.correlation(A_D[-12:], K_D[-12:]), places=4)
        self.assertEqual((v["n12"], v["agree12"], v["low_trust"]), (12, 1.0, False))

    def test_models_numbers_are_raw_like_the_private_block(self):
        # 비공개 tp_compare.render_block은 반올림하지 않은 값으로 그린다 — 10년 +12.50004bp는 +13bp(4자리 저장 뒤면 +12bp였다)
        kw, acm = month_world(g_d=G_D[:-1] + [12.50004])
        v = tp.calc_models({tp.KW_ID: kw, tp.ACM: acm})["values"]
        rows = tp.monthly_rows(kw, acm)
        last = rows[-1]
        sa = statistics.stdev(r["acm_dtp"] for r in rows)
        sk = statistics.stdev(r["kw_dtp"] for r in rows)
        self.assertEqual((v["dy"], v["acm_dtp"], v["kw_dtp"]), (last["dy"], last["acm_dtp"], last["kw_dtp"]))
        self.assertEqual((v["z_acm"], v["z_kw"]), (last["acm_dtp"] / sa, last["kw_dtp"] / sk))
        self.assertEqual(v["share_kw"], last["kw_dtp"] / last["dy"])
        recent = rows[-tp.WINDOW:]
        self.assertEqual(v["corr12"], tp.ff.pearson([r["acm_dtp"] for r in recent], [r["kw_dtp"] for r in recent]))
        line, extra = tp.texts("models", v, v["month"])
        self.assertTrue(line.startswith("2024-12 해석 갈림: 10년 +13bp 중 기간 프리미엄 몫 KW +12bp(96%) · ACM +2bp(16%)"), line)
        self.assertIn(f"(z ACM {last['acm_dtp'] / sa:+.2f} · KW {last['kw_dtp'] / sk:+.2f}는 2024-12)", extra[1])

    def test_models_low_trust_is_strictly_below_0_6(self):
        # 비공개 tp_compare: corr < 0.6이면 신뢰 낮음(0.6은 아님)
        kw, acm = month_world()
        for corr, want in ((0.6, False), (0.6 - 1e-9, True), (None, False)):
            with mock.patch.object(tp.ff, "pearson", return_value=corr):
                v = tp.calc_models({tp.KW_ID: kw, tp.ACM: acm})["values"]
            self.assertEqual(v["low_trust"], want, corr)
            self.assertEqual(any("신뢰 낮음" in t for t in tp.texts("models", v, v["month"])[1]), want, corr)

    def test_models_low_trust_below_0_6(self):
        k_d = K_D[:12] + [-k for k in K_D[12:22]] + [3, 12]                       # 최근 12개월 중 10달이 반대 방향
        kw, acm = month_world(k_d=k_d, g_d=[2.5 * k for k in k_d])
        v = tp.calc_models({tp.KW_ID: kw, tp.ACM: acm})["values"]
        self.assertLess(v["corr12"], 0.6)
        self.assertTrue(v["low_trust"])
        self.assertAlmostEqual(v["agree12"], 2 / 12, places=4)
        _, extra = tp.texts("models", v, v["month"])
        self.assertTrue(any("신뢰 낮음 — 요즘은 기간 프리미엄 해석 자체를 덜 믿을 때(상관 0.6 미만)" in t for t in extra))
        k_d = [-k if i in (12, 13) else k for i, k in enumerate(K_D)]           # 두 달만 반대 — 상관 약 0.53
        kw, acm = month_world(k_d=k_d, g_d=[2.5 * k for k in k_d])
        v = tp.calc_models({tp.KW_ID: kw, tp.ACM: acm})["values"]
        self.assertTrue(0.5 < v["corr12"] < 0.6)
        self.assertTrue(v["low_trust"])
        kw, acm = month_world()
        v = tp.calc_models({tp.KW_ID: kw, tp.ACM: acm})["values"]
        self.assertFalse(v["low_trust"])
        self.assertFalse(any("신뢰 낮음" in t for t in tp.texts("models", v, v["month"])[1]))

    def test_models_drops_a_month_whose_kim_wright_is_over_7_days_away(self):
        kw, acm = month_world()
        moved = [(d - datetime.timedelta(days=8), x) if d == D(2024, 6, 30) else (d, x) for d, x in kw]
        v = tp.calc_models({tp.KW_ID: moved, tp.ACM: acm})["values"]
        self.assertEqual(v["n"], 22)                                              # 6월과 7월이 빠진다
        moved = [(d - datetime.timedelta(days=7), x) if d == D(2024, 6, 30) else (d, x) for d, x in kw]
        self.assertEqual(tp.calc_models({tp.KW_ID: moved, tp.ACM: acm})["values"]["n"], 24)

    def test_models_ten_year_is_gsw_only_like_the_private_block(self):
        # 비공개 월간 점검은 models_block에 적합 10년을 넘기지 않는다 — GSW가 없으면 10년·몫·평소를 비우고 적합 10년으로 대신하지 않는다
        kw, acm = month_world(gsw=False)
        fy = [(d, 3.0 + 3 * x) for d, x in kw]                                    # 적합 10년이 있어도
        v = tp.calc_models({tp.KW_ID: kw, tp.ACM: acm, tp.FY_ID: fy})["values"]
        self.assertEqual(v, tp.calc_models({tp.KW_ID: kw, tp.ACM: acm})["values"])
        self.assertEqual((v["dy"], v["yield_src"], v["share_kw"], v["share_acm"], v["typ_kw"], v["typ_acm"]), (None,) * 6)
        self.assertEqual(tp.series_of("models", v), [tp.KW_ID, tp.ACM])
        line, extra = tp.texts("models", v, v["month"])
        self.assertEqual(line, "2024-12 해석 갈림: 기간 프리미엄 몫 KW +12bp · ACM +2bp")
        self.assertIn("표본 2023-01~2024-12 24개월. 10년은 이 달 자료 없음.", extra)
        _, acm2 = month_world()                                                    # 마지막 달만 GSW가 없으면 평소는 앞 달들로
        acm2[-1] = dict(acm2[-1], gsw=None)
        v = tp.calc_models({tp.KW_ID: kw, tp.ACM: acm2, tp.FY_ID: fy})["values"]
        self.assertEqual((v["dy"], v["yield_src"], v["share_kw"], v["share_acm"]), (None, None, None, None))
        self.assertAlmostEqual(v["typ_kw"], 0.4)
        self.assertIn("10년은 이 달 자료 없음.", tp.texts("models", v, v["month"])[1][-2])
        self.assertEqual(tp.YIELD_SRC, ("GSW",))
        self.assertEqual(tp.BY_KEY["models"]["optional"], {})

    def test_models_need_three_months_and_spread(self):
        kw, acm = month_world()
        with self.assertRaises(tp.ItemError):                                     # 월말 셋 = 달 둘
            tp.calc_models({tp.KW_ID: kw, tp.ACM: acm[-5:-2]})
        self.assertEqual(tp.calc_models({tp.KW_ID: kw, tp.ACM: acm[-6:-2]})["values"]["n"], 3)
        flat = [dict(r, tp=0.8) for r in acm]
        with self.assertRaises(tp.ItemError):
            tp.calc_models({tp.KW_ID: kw, tp.ACM: flat})

    def test_share_bounds(self):
        self.assertIsNone(tp._share(5, 9.9))
        self.assertIsNone(tp._share(5, None))
        self.assertAlmostEqual(tp._share(5, 10), 0.5)
        self.assertIsNone(tp._share(-5, 20))                                      # 부호가 다르면
        self.assertIsNone(tp._share(41, 20))                                      # 200% 넘음
        self.assertAlmostEqual(tp._share(40, 20), 2.0)

    def test_z_text_truncates_toward_zero(self):
        self.assertEqual([tp.z_text(z) for z in (0.998, -0.998, 1.555, -1.559, 0.004)], ["+0.99", "-0.99", "+1.55", "-1.55", "0.00"])

    def test_observations_after_today_are_dropped(self):
        S, rows = full_world()
        out = tp.compute(dict(S, ACM=rows), {}, D(2026, 9, 1))
        self.assertEqual(out["weekly"]["values"]["kw_asof"], "2026-09-01")
        self.assertEqual(out["models"]["values"]["month"], "2026-08-31")


class WordingTest(unittest.TestCase):
    def test_weekly_line(self):
        kw, fy = friday_world()
        v = tp.calc_weekly({tp.KW_ID: kw, tp.FY_ID: fy}, TODAY)["values"]
        line, extra = tp.texts("weekly", v, v["kw_asof"])
        self.assertEqual(line, f"2026-10-16 기준 4주(2026-09-18부터) +35.0bp ÷ σ {v['sigma_bp']:.1f}bp = z +3.39 · 운영자 주간 점수 -2")
        self.assertEqual(extra[0], "같은 4주 10년(Kim-Wright 적합) +70.0bp 중 기간 프리미엄 50%, 평소 50%(2023년 이후 주간 기울기)")
        self.assertEqual(extra[-2:], [tp.SCORE_DEF, tp.SCORE_NOTE])
        v["score"] = 0
        self.assertTrue(tp.texts("weekly", v, v["kw_asof"])[0].endswith("운영자 주간 점수 0"))

    def test_models_line(self):
        kw, acm = month_world()
        v = tp.calc_models({tp.KW_ID: kw, tp.ACM: acm})["values"]
        line, extra = tp.texts("models", v, v["month"])
        self.assertEqual(line, f"2024-12 해석 갈림: 10년 +30bp 중 기간 프리미엄 몫 KW +12bp(40%) · ACM +2bp(7%), "
                               f"평소 KW 40% · ACM {v['typ_acm'] * 100:.0f}%")
        self.assertEqual(extra[0], "이 움직임을 KW는 기간 프리미엄 변화로, ACM은 기대 경로 변화로 더 읽음 — 이 달 기간 프리미엄 "
                                   "해석은 정책 기대의 변화와 함께 볼 것")
        self.assertEqual(extra[1], f"최근 3달: 10월 ACM만 · 11월 둘 다 약함 · 12월 해석 갈림 (z ACM {v['z_acm']:+.2f} · "
                                   f"KW {v['z_kw']:+.2f}는 2024-12)")
        self.assertTrue(extra[2].startswith("12개월 일치도: 상관 "))
        self.assertEqual(extra[3], "표본 2023-01~2024-12 24개월. 10년은 ACM 파일의 실제 10년 무이표 금리(GSW).")
        self.assertEqual(extra[-1], tp.MODELS_DEF)
        for case, want in (("ACM만", "ACM은 기간 프리미엄 변화로"), ("반대", "방향이 반대")):
            self.assertIn(want, tp.texts("models", dict(v, case=case), v["month"])[1][0])
        v2 = dict(v, split=False, case="공통 TP↑")
        self.assertTrue(tp.texts("models", v2, v["month"])[0].startswith("2024-12 공통 TP↑: "))
        self.assertTrue(tp.texts("models", v2, v["month"])[1][0].startswith("최근 3달"))

    def test_fixed_texts_have_no_forbidden_words(self):
        kw, acm = month_world()
        fixed = [tp.NOTICE, tp.COMPUTED_NOTICE, tp.KW_NOTICE, tp.ACM_DERIVED, tp.SCORE_DEF, tp.SCORE_NOTE, tp.MODELS_DEF,
                 *tp.REASONS.values(), *(s["title"] for s in tp.ITEMS)]
        for case in tp.CASES:
            for split in (True, False):
                fixed += [tp.split_reading(case), tp.case_text(case, split)]
        v = tp.calc_models({tp.KW_ID: kw, tp.ACM: acm})["values"]
        w = tp.calc_weekly({tp.KW_ID: kw, tp.ACM: acm}, D(2025, 1, 10))["values"]
        for key, vals in (("models", v), ("weekly", w)):
            line, extra = tp.texts(key, vals, "2025-01-10")
            fixed += [line, *extra]
        for t in fixed:
            for word in list(FORBIDDEN_TEXT) + list(WORDS):
                self.assertNotIn(word, t, (word, t))


class LicenceTest(unittest.TestCase):
    def test_series_list_licence_and_no_restricted_series(self):
        self.assertEqual(tp.SERIES, ["THREEFYTP10", "ACM", "THREEFY10"])          # 설명 줄의 적합 10년은 끝
        self.assertEqual(set(tp.SOURCES), set(tp.SERIES))
        self.assertEqual(tp.LICENCE, {"THREEFYTP10": "public-domain", "THREEFY10": "public-domain", "ACM": "nyfed-terms"})
        self.assertFalse(set(tp.SERIES) & (set(rp.RESTRICTED) | set(ai.RESTRICTED)))
        self.assertEqual(tp.SOURCES["THREEFYTP10"][1], rp.FRED_TITLE["THREEFYTP10"])   # 규칙 카드와 같은 제목
        self.assertTrue(tp.ACM_URL.startswith("https://www.newyorkfed.org/"))
        for spec in tp.ITEMS:
            self.assertLessEqual(set(spec["series"]) | set(spec["optional"]), set(tp.SERIES))
            for field in spec["optional"].values():
                self.assertTrue(field is None or field in spec["values"])

    def test_citations_and_notices(self):
        self.assertEqual(tp.citation("THREEFYTP10", "2026-10-30"),
                         "Board of Governors of the Federal Reserve System (US), Term Premium on a 10 Year Zero Coupon Bond "
                         "[THREEFYTP10], retrieved from FRED, Federal Reserve Bank of St. Louis; "
                         "https://fred.stlouisfed.org/series/THREEFYTP10, October 30, 2026.")
        self.assertEqual(tp.citation("ACM", "2026-10-30"),
                         "Federal Reserve Bank of New York, Treasury Term Premia (Adrian, Crump, and Moench), 10-year term "
                         f"premium [TERMYld], retrieved from {tp.ACM_URL}, October 30, 2026.")
        acm_notes = [tp.ACM_DERIVED, tp.ACM_DERIVED_EN, rp.nyfed_attribution("2026"), rp.NOT_AFFILIATED, tp.ACM_PAPER]
        self.assertEqual(tp.notices("models", "2026-10-30", {}), [tp.COMPUTED_NOTICE, tp.KW_NOTICE, *acm_notes])
        self.assertEqual(tp.notices("weekly", "2026-10-30", {"acm_month": None}), [tp.COMPUTED_NOTICE, tp.KW_NOTICE])
        self.assertEqual(tp.notices("weekly", "2026-10-30", {"acm_month": "2026-09-30"})[2:], acm_notes)
        self.assertIn("© 2026 Federal Reserve Bank of New York", tp.notices("models", "2026-10-30")[4])
        self.assertIn("Pricing the Term Structure with Linear Regressions", tp.ACM_PAPER)
        self.assertIn("2005-33", tp.KW_NOTICE)


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.out = os.path.join(self.tmp, "data")
        self.work = os.path.join(self.tmp, ".work")
        self.path = os.path.join(self.out, tp.FILE)
        self.S, self.rows = full_world()

    def run_main(self, fred=None, opener=None, now=NOW, extra=(), clock=None):
        fred = fred or FakeFred(self.S)
        opener = opener or FakeOpener(acm_csv(self.rows))
        buf = io.StringIO()
        kw = {"clock": clock} if clock else {}
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = tp.main(["--out", self.out, "--work", self.work, *extra], fred_load=fred, opener=opener, now=now, **kw)
        return code, buf.getvalue()

    def saved(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def test_first_run_writes_both_items(self):
        code, log = self.run_main()
        self.assertEqual(code, 0, log)
        js = self.saved()
        self.assertEqual(set(js), {"schema", "generated_at", "notice", "order", "items"})
        self.assertEqual(js["order"], ["weekly", "models"])
        for key, it in js["items"].items():
            self.assertTrue(it["ok"], key)
            self.assertEqual(it["retrieved"], "2026-10-30")
            self.assertEqual(set(it), {"ok", "stale", "error", "failed_since", "key", "name", "date", "values", "retrieved",
                                       "line", "extra", "notices", "sources"})
            for src in it["sources"]:
                self.assertEqual(src["licence"], tp.LICENCE[src["series"]])
                self.assertTrue(src["citation"].endswith("October 30, 2026."))
        used = lambda key: [s["series"] for s in js["items"][key]["sources"]]
        self.assertEqual(used("weekly"), ["THREEFYTP10", "THREEFY10", "ACM"])
        self.assertEqual(used("models"), ["THREEFYTP10", "ACM"])
        self.assertEqual(js["items"]["models"]["sources"][1]["url"], tp.ACM_PAGE)
        self.assertEqual(js["items"]["weekly"]["values"]["kw_asof"], "2026-10-23")
        self.assertEqual(js["items"]["models"]["values"]["month"], "2026-09-30")
        self.assertTrue(os.path.exists(os.path.join(self.work, tp.CACHE, tp.ACM_CACHE)))

    def test_acm_failure_stales_models_and_keeps_weekly(self):
        self.run_main()
        code, log = self.run_main(opener=FakeOpener("<html>점검 중</html>"), now=NOW + datetime.timedelta(days=1))
        self.assertEqual(code, 0, log)
        items = self.saved()["items"]
        m, w = items["models"], items["weekly"]
        self.assertEqual((m["ok"], m["stale"], m["error"], m["failed_since"]), (False, True, tp.REASONS["format"], "2026-10-31"))
        self.assertEqual(m["retrieved"], "2026-10-30")
        self.assertTrue(w["ok"])
        self.assertIsNone(w["values"]["acm_month"])                               # 이번에 받지 못한 ACM은 이어 싣지 않는다
        self.assertEqual([s["series"] for s in w["sources"]], ["THREEFYTP10", "THREEFY10"])
        self.assertNotIn(tp.ACM_DERIVED, w["notices"])
        self.assertIn("::warning::기간 프리미엄 모형 대조 models 받지 못함", log)
        self.assertNotIn("점검 중", json.dumps(self.saved(), ensure_ascii=False))

    def test_first_failure_without_previous_has_no_numbers(self):
        self.run_main(fred=FakeFred(self.S, cache={"THREEFYTP10"}))
        for key in ("weekly", "models"):
            it = self.saved()["items"][key]
            self.assertEqual((it["ok"], it["stale"], it["error"]), (False, False, tp.REASONS["cache"]))
            self.assertNotIn("line", it)
            self.assertNotIn("values", it)

    def test_acm_moved_elsewhere_or_too_large_is_refused(self):
        for opener in (FakeOpener(acm_csv(self.rows), final="http://www.newyorkfed.org/x.csv"),
                       FakeOpener(acm_csv(self.rows), final="https://example.org/acm.csv"),
                       FakeOpener("RunDates,TERMYld\n" + "31-Aug-2026,0.5\n" * 400_000)):
            code, log = self.run_main(opener=opener)
            m = self.saved()["items"]["models"]
            self.assertEqual((m["ok"], m["error"]), (False, tp.REASONS["fetch"]))
            self.assertTrue(self.saved()["items"]["weekly"]["ok"])
            self.assertFalse(os.path.exists(os.path.join(self.work, tp.CACHE, tp.ACM_CACHE)))

    def test_acm_read_stops_at_the_deadline(self):
        clock = Clock()
        opener = FakeOpener(acm_csv(self.rows), clock=clock, step=10.0, chunk=256)  # 256바이트 조각마다 10초
        code, log = self.run_main(opener=opener, clock=clock)
        self.assertEqual(self.saved()["items"]["models"]["error"], tp.REASONS["fetch"])
        self.assertLessEqual(clock.t, tp.BUDGET + 10.0)
        self.assertTrue(all(1 <= t <= ai.TIMEOUT for _, t in opener.calls))

    def test_offline_reads_the_cache(self):
        cache = os.path.join(self.work, tp.CACHE)
        os.makedirs(cache)
        for sid, s in self.S.items():
            with open(os.path.join(cache, f"{sid}.csv"), "w", encoding="utf-8") as f:
                f.write("observation_date," + sid + "\n" + "".join(f"{d.isoformat()},{v}\n" for d, v in s))
        with open(os.path.join(cache, tp.ACM_CACHE), "w", encoding="utf-8") as f:
            f.write(acm_csv(self.rows, eol="\r\n"))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), mock.patch.object(tp.urllib.request, "urlopen", side_effect=AssertionError("요청")), \
                mock.patch.object(ai.urllib.request, "urlopen", side_effect=AssertionError("요청")):
            code = tp.main(["--out", self.out, "--work", self.work, "--offline"], now=NOW)
        self.assertEqual(code, 0, buf.getvalue())
        self.assertTrue(all(it["ok"] for it in self.saved()["items"].values()))

    def test_older_data_is_not_taken(self):
        self.run_main()
        self.run_main(opener=FakeOpener(acm_csv(self.rows[:-1])), now=NOW + datetime.timedelta(days=1))
        m = self.saved()["items"]["models"]
        self.assertEqual((m["ok"], m["stale"], m["error"]), (False, True, tp.REASONS["older"]))
        self.assertEqual(m["values"]["month"], "2026-09-30")
        short = dict(self.S, THREEFYTP10=self.S["THREEFYTP10"][:-1])
        self.run_main(fred=FakeFred(short), now=NOW + datetime.timedelta(days=2))
        w = self.saved()["items"]["weekly"]
        self.assertEqual((w["ok"], w["error"], w["values"]["kw_asof"]), (False, tp.REASONS["older"], "2026-10-23"))

    def test_same_numbers_keep_the_file(self):
        self.run_main()
        with open(self.path, "rb") as f:
            first = f.read()
        self.run_main(now=NOW + datetime.timedelta(days=1))                          # 나이 하루 늘어도(14일 안) 같은 내용
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), first)

    def test_a_broken_previous_file_is_not_carried(self):
        self.run_main()
        js = self.saved()
        js["items"]["weekly"]["values"]["score"] = 3                               # 점수 범위 밖
        js["items"]["models"]["values"]["case"] = "매수"                            # 정해 둔 경우 밖
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(js, f, ensure_ascii=False)
        self.run_main(fred=FakeFred(self.S, fail={"THREEFYTP10"}), now=NOW + datetime.timedelta(days=1))
        items = self.saved()["items"]
        for key in ("weekly", "models"):
            self.assertEqual((items[key]["ok"], items[key]["stale"]), (False, False), key)
            self.assertNotIn("line", items[key])
        self.assertNotIn("매수", json.dumps(self.saved(), ensure_ascii=False))
        bad = {"recent": [["2026-09-30", "공통 TP↑", "yes"]], "score": 1.0, "low_trust": 1, "yield_src": "<b>"}
        for k, x in bad.items():
            self.run_main()
            js = self.saved()
            item = js["items"]["weekly" if k == "score" else "models"]
            item["values"][k] = x
            self.assertIsNone(tp.core_of(item, item["key"]), k)

    def test_new_values_must_pass_the_same_checks(self):
        kw, acm = month_world()
        good = tp.calc_models({tp.KW_ID: kw, tp.ACM: acm})
        for k, x in (("case", "<b>"), ("n", -1), ("recent", []), ("split", None)):
            core = {"date": good["date"], "values": dict(good["values"], **{k: x})}
            out = tp.build({"weekly": tp.ItemError("fetch"), "models": core}, {}, NOW)["items"]["models"]
            self.assertEqual((out["ok"], out["error"]), (False, tp.REASONS["format"]), k)
            self.assertNotIn("values", out)
        self.assertTrue(tp.build({"weekly": tp.ItemError("fetch"), "models": good}, {}, NOW)["items"]["models"]["ok"])

    def test_previous_checks_the_schema(self):
        good = {"weekly": {"key": "weekly"}, "models": {"key": "models"}}
        os.makedirs(self.out)
        for js, want in (({"schema": tp.SCHEMA, "items": good}, good),
                         ({"schema": tp.SCHEMA + 1, "items": good}, {}),
                         ({"items": good}, {}),
                         ({"schema": tp.SCHEMA, "items": [good]}, {}),
                         ([good], {}),
                         ({"schema": tp.SCHEMA, "items": dict(good, zzz={"key": "zzz"})}, good)):
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(js, f)
            self.assertEqual(tp.previous(self.out), want, js)
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{깨진")
        self.assertEqual(tp.previous(self.out), {})

    def test_budget_runs_out_without_waiting(self):
        t = [0.0]

        def clock():
            t[0] += 30.0
            return t[0]
        fred = FakeFred(self.S)
        code, log = self.run_main(fred=fred, clock=clock)
        self.assertLess(len(fred.calls), 2)                                        # 적합 10년(끝)은 받지 못한다
        self.assertTrue(all(1 <= tmo <= ai.TIMEOUT for _, tmo in fred.calls))
        self.assertIn("THREEFY10 받지 못함", log)

    def test_nothing_fetched_exits_1(self):
        code, log = self.run_main(fred=FakeFred(self.S, fail=set(self.S)), opener=FakeOpener("x"))
        self.assertEqual(code, 1, log)
        self.assertTrue(all(not it["ok"] for it in self.saved()["items"].values()))

    def test_the_write_is_atomic(self):
        self.run_main()
        with open(self.path, "rb") as f:
            before = f.read()
        moved = dict(self.S, THREEFYTP10=[(d, v * 1.1) for d, v in self.S["THREEFYTP10"]])     # 변화가 달라지게
        with mock.patch.object(ai.os, "replace", side_effect=OSError("disk full")):
            code, log = self.run_main(fred=FakeFred(moved), now=NOW + datetime.timedelta(days=1))
        self.assertEqual(code, 1, log)
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), before)
        self.assertEqual(os.listdir(self.out), [tp.FILE])

    def test_every_string_is_fixed_text(self):
        self.run_main(opener=FakeOpener("<b>원문 https://bad.invalid/q</b>"))
        self.run_main(now=NOW + datetime.timedelta(days=1))
        self.run_main(fred=FakeFred(self.S, fail={"THREEFYTP10"}), now=NOW + datetime.timedelta(days=2))
        dump = json.dumps(self.saved(), ensure_ascii=False)
        for word in list(FORBIDDEN_TEXT) + list(WORDS):
            self.assertNotIn(word, dump, word)
        urls = {u.rstrip(".") for u in re.findall(r"https?://[^\s,;)\"]+", dump)}
        self.assertEqual(urls, {f"https://fred.stlouisfed.org/series/{s}" for s in ("THREEFYTP10", "THREEFY10")}
                         | {tp.ACM_URL, tp.ACM_PAGE})
        self.assertNotIn("bad.invalid", dump)
        self.assertNotIn("@", dump)                                                # 연락 주소 같은 것은 없다
        errors = {it["error"] for it in self.saved()["items"].values()} - {None}
        self.assertLessEqual(errors, set(tp.REASONS.values()))


class ScreenTest(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
            return f.read()

    def test_screen_script_matches_the_file_and_avoids_page_risks(self):
        js = self.read("site", "tp.js")
        card = re.findall(r'"(\w+)"', js[js.index("const CARD = ["):].split("]")[0])
        self.assertEqual(card, [s["key"] for s in tp.ITEMS])
        reasons = re.findall(r'"([^"]+)"', js[js.index("const REASONS = ["):].split("];")[0])
        self.assertEqual(reasons, list(tp.REASONS.values()))
        self.assertIn('const LABEL = "참고 — 금리 예측 아님";', js)
        self.assertIn('key === "weekly" ? el("p", { class: "oil-note" }, SCORE_NOTE) : null', js)   # 점수에는 늘 안내
        body = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        for tok in ("innerHTML", "outerHTML", "insertAdjacentHTML", "createElement", "fetch(", "eval(", "location.",
                    "navigator.", "localStorage", "url("):
            self.assertNotIn(tok, body, tok)
        for word in list(FORBIDDEN_TEXT) + list(WORDS):
            self.assertNotIn(word, body, word)

    def test_card_shows_every_citation_this_script_writes(self):
        # 고지가 'FRED 권장 인용과 함께 싣는다'고 적으므로 카드가 그 인용을 실제로 싣는다 — 화면의 꼴 검사(CITE)가 이 파일의 인용을
        # 모두 받아들이는지(시리즈 셋 × 달 이름이 가장 긴 날·짧은 날)
        js = self.read("site", "tp.js")
        cite = re.compile(re.search(r"const CITE = /(.+)/;", js).group(1))
        self.assertIn("citeLine(items)", js[js.index("function card("):])
        for sid in tp.SERIES:
            for day in ("2026-09-30", "2026-05-01", "2027-01-09"):
                self.assertRegex(tp.citation(sid, day), cite, (sid, day))
        self.assertNotRegex("<b>원문</b>, retrieved from x, October 30, 2026.", cite)


class WiringTest(unittest.TestCase):
    """페이지·워크플로·README 연결 — 이 파일을 만든 단계에서는 없고, 묶는 단계에서 맞춘다."""
    def read(self, *parts):
        with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
            return f.read()

    def test_workflow_fetches_without_failing_the_run(self):
        wf = self.read(".github", "workflows", "daily.yml")
        step = wf[wf.index("id: tp\n"):]
        self.assertIn("continue-on-error: true", step[:200])
        self.assertIn("timeout-minutes: 2", step[:200])
        self.assertIn("python scripts/tp_fetch.py", step[:300])
        self.assertLess(wf.index("id: tp\n"), wf.index("공개 전 검사(새 산출물 포함)"))
        self.assertLess(wf.index("id: tp\n"), wf.index("git add data"))
        self.assertNotIn("tp_fetch", wf[wf.index("\n  alert:"):])
        self.assertIn("node --test scripts/test_tp_render.cjs", wf[wf.index("\n  check:"):wf.index("\n  update:")])

    def test_page_wires_the_card(self):
        page = self.read("site", "index.html")
        self.assertIn('getJson("data/tp.json")', page)
        self.assertIn('<script src="tp.js"></script>', page)
        self.assertIn('<a href="data/tp.json">', page)
        self.assertIn('id:"tp-slot"', page)
        self.assertIn("window.TpCard.render(", page)

    def test_readme_counts(self):
        readme = self.read("README.md")
        m = re.search(r"\*\*아침 쪽 Python 테스트 (\d+)개 \+ node 테스트 (\d+)개\*\*\((.*?)\)와 \*\*저녁판", readme)
        py_part, node_part = m.group(3).split(" / node: ")
        mine = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()
        self.assertRegex(py_part, rf"(^|· )기간 프리미엄 모형 대조 {mine}( ·|$)")
        cjs = len(re.findall(r"^test\(", self.read("scripts", "test_tp_render.cjs"), flags=re.M))
        self.assertRegex(node_part, rf"(^|· )기간 프리미엄 카드 그리기 {cjs}( ·|$)")


if __name__ == "__main__":
    unittest.main(verbosity=1)
