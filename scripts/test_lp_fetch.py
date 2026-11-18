#!/usr/bin/env python3
"""노동 L × 물가 P 판단 격자 참고 자료(lp_fetch) 테스트 — 손으로 셀 수 있는 합성 자료로 규칙의 갈래마다, 히스테리시스,
띠·모멘텀 경계(소수 6자리 반올림 뒤 같은 값), 9칸·16칸, 청구 다리, JOLTS 달 고르기, 실업률 빠진 달, 꼬리표 빼기, 사례 대조,
전부 아니면 쓰지 않는 수신, 같은 내용이면 다시 쓰지 않기, 자료 꼴, 문구 원칙, 워크플로 단계 · README 절과 개수 · 화면 스크립트(site/lp.js)가
따로 적어 둔 칸 이름 · 9칸 · 문턱 키가 이 파일과 같은지.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — FRED는 가짜 loader 또는 임시 폴더. 숫자는 모두 지어낸 것이다.
비공개 측정 도구와 같은 답을 내는지는 비공개 저장소의 짝 테스트가 본다(이 저장소는 그쪽 코드를 가져오지 않는다).
"""
import os, re, sys, io, ast, json, math, datetime, tempfile, unittest, contextlib, shutil, itertools
from unittest import mock

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import lp_fetch as lp
import oil_fetch as oil
import render_public as rp
import fred_fetch as ff
from test_render_public import FORBIDDEN_TEXT

D = datetime.date
NOW = datetime.datetime(2026, 11, 18, 4, 30, tzinfo=datetime.timezone.utc)
L_MM, L_M, L_0, L_P = lp.L_MM, lp.L_M, lp.L_0, lp.L_P
P_P, P_0, P_D, P_M = lp.P_P, lp.P_0, lp.P_D, lp.P_M
# 노동 다리가 모두 조용한 달
NEUTRAL = {"month": "2026-01", "sahm": 0.1, "rising3": False, "claims_on": False, "layoff_share": None, "epop3_d6": 0.0,
           "vu3_d6": 0.0, "p3": 100.0, "hi_gap": -0.1, "d6u3": 0.0, "quits3_d6": 0.0, "c4_down13_4w": False}
ADVICE = ("매수", "매도", "유망", "적중", "전망", "예상", "추천")
DIRECTION = ("상방", "하방", "되돌림", "박스", "스티프닝", "골디락스", "스태그")


def g(**kw):
    return dict(NEUTRAL, **kw)


def mon(mp):
    return [(lp.mdate(m), v) for m, v in sorted(mp.items())]


def saturdays(start, n):
    return [start + datetime.timedelta(days=7 * i) for i in range(n)]


# ---------- 합성 세계 ----------
# 실업률: 1958~2023 5.0 고정 → 2024-01 4.0에서 달마다 +0.1(2024-09 4.8) → 2024-12까지 4.8 → 2025-01부터 달마다 −0.1(4.0까지) →
# 4.0. 2025-10은 빠진 달. 근원 PCE는 연율 구간(PCE_RATES)으로 지은 지수. 근원 CPI도 2025-10이 빠진다.
PCE_RATES = [("1958-01", 2.0), ("2021-03", 5.0), ("2022-10", 4.0), ("2023-07", 2.4), ("2024-01", 3.5),
             ("2024-04", 1.4), ("2025-01", 2.9), ("2026-01", 3.4)]


def unrate_map():
    un, u = {}, 5.0
    for m in lp.mrange("1958-01", "2026-10"):
        if m < "2024-01":
            u = 5.0
        elif m <= "2024-09":
            u = round(4.0 + 0.1 * (int(m[5:7]) - 1), 4)
        elif m <= "2024-12":
            u = 4.8
        else:
            u = max(4.0, round(u - 0.1, 4))
        if m != "2025-10":
            un[m] = u
    return un


def world():
    un = unrate_map()
    w = {"UNRATE": mon(un)}
    w["LNS12300060"] = mon({m: 80.5 - 0.9 * (u - 4.0) for m, u in un.items()})
    unemp = {m: u * 1650 for m, u in un.items()}
    w["UNEMPLOY"] = mon(unemp)
    w["LNS13026638"] = mon({m: 900 + 0.2 * (v - 6600) for m, v in unemp.items()})
    priv, lvl, prev = {}, 90000.0, None
    for m in sorted(un):
        lvl += 150 - 1500 * ((un[m] - prev) if prev is not None else 0.0)
        prev = un[m]
        priv[m] = lvl
    w["USPRIV"] = mon(priv)
    jm = [m for m in un if m >= "2000-12" and m <= "2026-09"]
    w["JTSJOL"] = mon({m: 7600 - 900 * (un[m] - 4.0) for m in jm})
    w["JTSQUR"] = mon({m: 2.4 - 0.15 * (un[m] - 4.0) for m in jm})
    last_u, wk = {}, []
    for m in lp.mrange("1958-01", "2026-11"):
        last_u[m] = un.get(m, last_u.get(lp.mshift(m, -1), 5.0))
    sat = D(1967, 1, 7)
    while sat <= D(2026, 11, 7):
        wk.append(sat)
        sat += datetime.timedelta(days=7)
    w["ICSA"] = [(d, 220000 + 30000 * (last_u[lp.mkey(d)] - 4.0)) for d in wk]
    w["CCSA"] = [(d, 8 * v) for d, v in w["ICSA"][:-1]]                     # 계속 청구는 한 주 늦다
    idx, pce, rates = 100.0, {}, PCE_RATES
    for m in lp.mrange("1958-01", "2026-09"):
        r = [x for a, x in rates if a <= m][-1]
        idx *= (1 + r / 100) ** (1 / 12)
        pce[m] = idx
    w["PCEPILFE"] = mon(pce)
    cpi = {m: v * 1.004 ** (lp.mdiff(m, "1958-01") / 12) for m, v in pce.items() if m != "2025-10"}
    cpi["2026-10"] = cpi["2026-09"] * 1.002
    w["CPILFESL"] = mon(cpi)
    w["CPIAUCSL"] = mon({m: v * (1 + 0.02 * math.sin(lp.mdiff(m, "1958-01") / 6)) for m, v in cpi.items()})
    w["CUSR0000SACL1E"] = mon({m: 100 * 1.01 ** (lp.mdiff(m, "1958-01") / 12) for m in cpi})
    return w


_W = {}


def W():
    if "w" not in _W:
        _W["w"] = world()
    return _W["w"]


def fred_text(series, sid):
    return f"observation_date,{sid}\n" + "".join(f"{d.isoformat()},{v}\n" for d, v in series)


class FakeFred:
    """lp.fetch_all의 loader 자리 — ff.load와 같은 꼴(sid, cache_dir, offline, timeout) → (시계열, 'net'|'cache')."""

    def __init__(self, data, fail=(), cache=()):
        self.data, self.fail, self.cache, self.calls = data, set(fail), set(cache), []

    def __call__(self, sid, cache_dir, offline=False, timeout=None):
        self.calls.append((sid, offline, timeout))
        if sid in self.fail or sid not in self.data:
            raise RuntimeError(f"{sid}: 수신 실패 https://bad.invalid/x")
        return list(self.data[sid]), ("cache" if (offline or sid in self.cache) else "net")


class Clock:
    def __init__(self, step=0.0):
        self.t, self.step = 1000.0, step

    def __call__(self):
        self.t += self.step
        return self.t


# ---------- 상수·약속 ----------

class ConstantsTest(unittest.TestCase):
    def test_constants_equal_the_contract(self):
        self.assertEqual(lp.CONSTANTS, {"sahm_on": 0.5, "sahm_watch": 0.4, "hi_gap": -0.3, "d6u": -0.2, "claims_ratio": 1.25,
                                        "claims_weeks": 4, "epop_up": 0.2, "epop_dn": -0.3, "vu_up": 0.1, "vu_dn": -0.15,
                                        "quits_up": 0.1, "h_in": 3.1, "h_out": 2.9, "lo_in": 2.6, "lo_out": 2.7,
                                        "mom": 0.5, "mom_n": 1, "mom_dn": 0.3, "mom_dn_n": 2,
                                        "layoff_hi": 0.5, "layoff_lo": 0.3})
        self.assertEqual((lp.FIXED, lp.HOLDOUT, lp.SINCE, lp.LABOR_START, lp.REPLAY_START, lp.HISTORY_FROM),
                         ("2026-10-14", "2024-01", D(1960, 1, 1), "1960-01", "1990-01", "2022-01"))
        self.assertEqual((lp.LAYOFF_HI, lp.LAYOFF_LO, lp.MIN_DU, lp.MIN_WINDOWS, lp.CCSA_TOL, lp.DAYS_3M),
                         (0.5, 0.3, 100, 9, 13, 91))

    def test_state_names_use_the_unicode_minus(self):
        self.assertEqual((L_MM, L_M, P_M), ("L−−", "L−", "P−"))
        self.assertEqual(lp.GRID_L, ("L+", "L0", "L−", "L−−"))
        self.assertEqual(lp.GRID_P, ("P+", "P0", "Pd", "P−"))

    def test_leg_names_follow_the_constants(self):
        self.assertEqual(lp.LEG_ORDER, (
            "Sahm형 ≥ 0.50", "Sahm형 ≥ 0.40", "u3 상승(3개월 전보다)", "청구 다리(1.25 × 4주 + CCSA 상승)", "해고 몫(표시만)",
            "핵심연령 고용률 3개월 Δ6 ≤ −0.3", "V/U 3개월 Δ6 ≤ −0.15", "민간고용 3개월 평균 ≤ 0(천 명)",
            "고점 대비 하락(U2: hi_gap ≤ −0.30 · Δ6 ≤ −0.20)", "회복 확인(고용률 ≥ +0.2)", "회복 확인(V/U Δ6 ≥ +0.10)",
            "근원 PCE Y3 띠", "근원 PCE 모멘텀(a6 − y12)"))
        self.assertEqual(set(lp.LEG_THS) | {lp.LEG_RISING}, set(lp.LEG_ORDER))

    def test_series_are_the_thirteen_public_ones(self):
        self.assertEqual(lp.SERIES, ("UNRATE", "LNS12300060", "UNEMPLOY", "LNS13026638", "USPRIV", "ICSA", "CCSA", "JTSJOL",
                                     "JTSQUR", "PCEPILFE", "CPIAUCSL", "CPILFESL", "CUSR0000SACL1E"))
        self.assertEqual(set(lp.SOURCES), set(lp.SERIES) | {"LNS13025699"})
        for sid in ("ICNSA", "JTSLDR", "NROU", "SAHMREALTIME", "PCETRIM12M159SFRBDAL", "DGS2", "THREEFYTP10", "T10YIE"):
            self.assertNotIn(sid, lp.SOURCES)

    def test_citation_has_the_render_public_form(self):
        for sid in ("UNRATE", "PCEPILFE", "CPILFESL"):                       # render_public이 아는 시리즈는 글자까지 같다
            self.assertEqual(lp.citation(sid, "2026-11-18"), rp.citation(sid, "2026-11-18"))
        self.assertEqual(lp.citation("ICSA", "2026-11-18"),
                         "U.S. Employment and Training Administration, Initial Claims [ICSA], retrieved from FRED, Federal "
                         "Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/ICSA, November 18, 2026.")

    def test_standard_library_and_this_repo_only(self):
        with open(os.path.join(SCRIPTS, "lp_fetch.py"), encoding="utf-8") as f:
            src = f.read()
        mods = set()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Import):
                mods |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                mods.add(node.module.split(".")[0])
        self.assertEqual(mods - set(sys.stdlib_module_names), {"fred_fetch", "render_public"})
        for word in ("User-Agent", "urlopen", "daily-macro", "references/"):
            self.assertNotIn(word, src)


# ---------- 비교 ----------

class CompareTest(unittest.TestCase):
    def test_six_decimal_rounding(self):
        self.assertTrue(lp.ge(0.4 - 1e-9, 0.4))                     # 0.3999999990 → 0.4
        self.assertFalse(lp.ge(0.399999, 0.4))
        self.assertTrue(lp.le(-0.3 + 4e-7, -0.3))
        self.assertFalse(lp.gt(3.1000004, 3.1))
        self.assertTrue(lp.gt(3.100001, 3.1))
        self.assertTrue(lp.lt(2.599999, 2.6))
        self.assertFalse(lp.lt(2.5999996, 2.6))
        for f in (lp.ge, lp.le, lp.gt, lp.lt):
            self.assertFalse(f(None, 0.0))


# ---------- 노동 L ----------

class LaborStateTest(unittest.TestCase):
    def test_a_watch_and_rising(self):
        self.assertEqual(lp.l_raw(g(sahm=0.45, rising3=True)), L_M)
        self.assertEqual(lp.l_raw(g(sahm=0.40, rising3=True)), L_M)                   # 경계 포함
        self.assertEqual(lp.l_raw(g(sahm=0.4 - 4e-7, rising3=True)), L_M)             # 6자리 반올림 뒤 0.4
        self.assertEqual(lp.l_raw(g(sahm=0.39, rising3=True)), L_0)
        self.assertEqual(lp.l_raw(g(sahm=0.45, rising3=None)), lp.UNKNOWN)           # 주의 위인데 상승을 모름
        self.assertEqual(lp.l_raw(g(sahm=0.35, rising3=None)), L_0)                  # 주의 아래면 상승을 몰라도 (a) 아님

    def test_b_sahm_on_without_claims(self):
        self.assertEqual(lp.l_raw(g(sahm=0.53, rising3=False)), L_M)
        self.assertEqual(lp.l_raw(g(sahm=0.53, rising3=True, layoff_share=0.6)), L_M)  # 해고 몫은 판단에 쓰지 않는다
        self.assertEqual(lp.l_raw(g(sahm=0.53, rising3=False, claims_on=True)), L_0)   # (b)는 청구 다리가 꺼졌을 때만

    def test_c_two_deterioration_legs(self):
        self.assertEqual(lp.l_raw(g(epop3_d6=-0.3, vu3_d6=-0.15)), L_M)               # 경계 포함
        self.assertEqual(lp.l_raw(g(epop3_d6=-0.3, p3=0.0)), L_M)
        self.assertEqual(lp.l_raw(g(vu3_d6=-0.2, p3=-5.0)), L_M)
        self.assertEqual(lp.l_raw(g(epop3_d6=-0.29, vu3_d6=-0.15)), L_0)              # 하나뿐
        self.assertEqual(lp.l_raw(g(p3=-10.0)), L_0)
        self.assertTrue(lp.breadth_on(g(epop3_d6=-0.4, vu3_d6=-0.2)))
        self.assertFalse(lp.breadth_on(g(epop3_d6=None, vu3_d6=-0.2)))               # 없는 다리는 거짓으로 센다

    def test_d_claims_plus_one_leg(self):
        self.assertEqual(lp.l_raw(g(claims_on=True, p3=-10.0)), L_M)
        self.assertEqual(lp.l_raw(g(claims_on=True)), L_0)                            # 청구 단독으로는 L−가 아니다
        self.assertEqual(lp.l_raw(g(claims_on=None, p3=-10.0)), L_0)                  # '?'인 청구는 켜짐이 아니다

    def test_l_minus_minus(self):
        self.assertEqual(lp.l_raw(g(sahm=0.5, rising3=True, claims_on=True)), L_MM)
        self.assertEqual(lp.l_raw(g(sahm=0.6, rising3=None, claims_on=True)), lp.UNKNOWN)
        self.assertEqual(lp.l_raw(g(sahm=0.6, rising3=False, claims_on=True)), L_0)
        self.assertEqual(lp.l_raw(g(sahm=0.49, rising3=True, claims_on=True)), L_M)   # Sahm 0.50 아래면 (a)·(d)

    def test_l_plus_recovery_and_reheat(self):
        self.assertEqual(lp.l_raw(g(hi_gap=-0.4, d6u3=-0.3, epop3_d6=0.3)), L_P)
        self.assertEqual(lp.l_raw(g(hi_gap=-0.30, d6u3=-0.20, c4_down13_4w=True)), L_P)   # 경계 포함 · 청구 확인
        self.assertEqual(lp.l_raw(g(hi_gap=-0.30, d6u3=-0.20, vu3_d6=0.10)), L_P)
        self.assertEqual(lp.l_raw(g(hi_gap=-0.4, d6u3=-0.3)), L_0)                      # U2만, 확인 없음
        self.assertEqual(lp.l_raw(g(hi_gap=-0.29, d6u3=-0.3, epop3_d6=0.3)), L_0)
        self.assertEqual(lp.l_raw(g(sahm=-0.1, vu3_d6=0.12, quits3_d6=0.1)), L_P)        # 재과열형
        self.assertEqual(lp.l_raw(g(sahm=0.0, vu3_d6=0.10, quits3_d6=0.10)), L_P)
        self.assertEqual(lp.l_raw(g(sahm=0.01, vu3_d6=0.12, quits3_d6=0.1)), L_0)
        self.assertEqual(lp.l_raw(g(sahm=None)), lp.UNKNOWN)

    def test_raw_rules_follow_l_raw(self):
        """화면의 '그 달 조건' 줄 — l_raw와 같은 갈래(격자 전부에서 L−−·L−·L+이면 절이 있고, L0·'?'이면 없다)."""
        self.assertEqual(lp.raw_rules(g(sahm=0.6, rising3=True, claims_on=True)), ["L−−"])
        self.assertEqual(lp.raw_rules(g(sahm=0.45, rising3=True)), ["a"])
        self.assertEqual(lp.raw_rules(g(sahm=0.55, rising3=True, claims_on=None)), ["a", "b"])  # 청구 '?'는 해고 미확인
        self.assertEqual(lp.raw_rules(g(epop3_d6=-0.4, vu3_d6=-0.2)), ["c"])
        self.assertEqual(lp.raw_rules(g(claims_on=True, p3=-1.0)), ["d"])
        self.assertEqual(lp.raw_rules(g(hi_gap=-0.4, d6u3=-0.3, epop3_d6=0.3)), ["A"])
        self.assertEqual(lp.raw_rules(g(sahm=0.0, vu3_d6=0.1, quits3_d6=0.1)), ["B"])
        self.assertEqual(lp.raw_rules(NEUTRAL), [])
        self.assertEqual(lp.raw_rules(g(sahm=None)), [])
        vals = {"sahm": (None, 0.0, 0.3999996, 0.45, 0.5), "rising3": (None, True, False), "claims_on": (None, True, False),
                "epop3_d6": (-0.3, 0.2), "vu3_d6": (-0.15, 0.1), "p3": (0.0, 5.0), "hi_gap": (None, -0.3), "d6u3": (-0.2, 0.0),
                "quits3_d6": (0.1, 0.0), "c4_down13_4w": (True, False)}
        for combo in itertools.product(*vals.values()):
            x = dict(zip(vals, combo))
            raw, rules = lp.l_raw(x), lp.raw_rules(x)
            self.assertEqual(bool(rules), raw in (L_MM, L_M, L_P), x)
            self.assertTrue(set(rules) <= {L_MM: {"L−−"}, L_M: set("abcd"), L_P: set("AB")}.get(raw, set()), x)

    def test_layoff_share_classes(self):
        share, cls = lp.layoff_share(300, 200)
        self.assertAlmostEqual(share, 2 / 3, places=12)
        self.assertEqual(cls, "해고형")
        self.assertEqual(lp.layoff_share(99.9999, 80), (None, None))
        self.assertEqual(lp.layoff_share(100, 50), (0.5, "해고형"))
        self.assertEqual(lp.layoff_share(400, 80)[1], "진입형")
        self.assertEqual(lp.layoff_share(400, 160)[1], "모호")
        self.assertEqual(lp.layoff_share(None, 80), (None, None))


class ReplayTest(unittest.TestCase):
    L = staticmethod(lambda seq: [r["L"] for r in lp.replay_l(seq)])

    def test_two_release_entry_and_one_release_l_minus_minus(self):
        up = g(hi_gap=-0.4, d6u3=-0.3, epop3_d6=0.3)
        self.assertEqual(self.L([NEUTRAL, up, NEUTRAL]), [L_0] * 3)                    # 한 발표는 안 바뀐다
        self.assertEqual(self.L([NEUTRAL, up, up, up]), [L_0, L_0, L_P, L_P])
        deter = g(sahm=0.45, rising3=True)
        self.assertEqual(self.L([NEUTRAL, deter, deter]), [L_0, L_0, L_M])
        mm = g(sahm=0.6, rising3=True, claims_on=True)
        self.assertEqual(self.L([NEUTRAL, mm]), [L_0, L_MM])                           # L−−는 한 발표로
        self.assertEqual(self.L([NEUTRAL, deter, deter, mm]), [L_0, L_0, L_M, L_MM])   # L− → L−− 한 번에
        lminus = g(sahm=0.55, rising3=True)
        self.assertEqual(self.L([mm, lminus, lminus, lminus]), [L_MM, L_MM, L_M, L_M])  # L−− → L−는 두 발표
        self.assertEqual(self.L([mm, lminus, mm, lminus]), [L_MM] * 4)
        self.assertEqual(self.L([up, up, NEUTRAL, NEUTRAL]), [L_0, L_P, L_P, L_0])     # L+ → L0도 두 발표

    def test_exit_two_releases_and_the_peak_tag_once(self):
        deter, peak = g(sahm=0.45, rising3=True), g(sahm=0.4, rising3=False)
        out = lp.replay_l([NEUTRAL, deter, deter, peak, peak, peak])
        self.assertEqual([r["L"] for r in out], [L_0, L_0, L_M, L_M, L_0, L_0])
        self.assertEqual([i for i, r in enumerate(out) if r["tags"]], [4])
        self.assertEqual(out[4]["tags"], [lp.TAG_PEAK])
        mm = g(sahm=0.6, rising3=True, claims_on=True)
        out = lp.replay_l([mm, peak, peak, peak])
        self.assertEqual([r["L"] for r in out], [L_MM, L_MM, L_0, L_0])               # L−−에서도 이탈 두 발표
        claims_peak = dict(peak, claims_on=True)                                       # 청구 다리가 켜져 있으면 나오지 않는다
        self.assertEqual(self.L([deter, deter, claims_peak, claims_peak, claims_peak]), [L_0] + [L_M] * 4)

    def test_sticky_sahm_cannot_enter_and_breadth_can(self):
        sticky = g(sahm=0.55, rising3=False)                                           # (b) — 그 달 이탈 조건이 켜져 있다
        self.assertEqual(self.L([sticky] * 3), [L_0] * 3)
        broad = g(sahm=0.1, rising3=False, epop3_d6=-0.4, vu3_d6=-0.2, p3=-20.0)       # (c) — u3 평평
        self.assertFalse(lp.exit_ok(broad))
        self.assertEqual(self.L([broad] * 4), [L_0, L_M, L_M, L_M])
        out = lp.replay_l([broad, broad, NEUTRAL, NEUTRAL, NEUTRAL])
        self.assertEqual([r["L"] for r in out], [L_0, L_M, L_M, L_0, L_0])
        self.assertIsNone(lp.exit_ok(g(rising3=None)))

    def test_unknown_month_breaks_the_run_but_keeps_the_state(self):
        deter, unk = g(sahm=0.45, rising3=True), g(sahm=None)
        self.assertEqual(self.L([deter, deter, unk, deter]), [L_0, L_M, lp.UNKNOWN, L_M])
        self.assertEqual(self.L([NEUTRAL, deter, unk, deter, deter]), [L_0, L_0, lp.UNKNOWN, L_0, L_M])
        out = lp.replay_l([deter, deter, unk])
        self.assertEqual(out[2]["state"], L_M)
        peak = g(sahm=0.4, rising3=False)
        self.assertEqual(self.L([deter, deter, peak, unk, peak, peak]), [L_0, L_M, L_M, lp.UNKNOWN, L_M, L_0])

    def test_only_an_unknown_l_breaks_the_run_not_an_unknown_p(self):
        """자료 파일의 재생 규칙 글 그대로 — L을 모르는 달만 연속 셈을 끊는다. 근원 PCE가 아직 없는 달(P '?')은 칸만 보류이고
        L의 두 발표 셈은 이어진다(P는 replay_l의 입력이 아니다)."""
        w = W()
        rows = {r["month"]: r for r in lp.compute(w, NOW.date())["rows"]}
        cut = dict(w, PCEPILFE=[x for x in w["PCEPILFE"] if x[0] < D(2025, 3, 1)])      # 2025-03부터 P '?'
        rows2 = {r["month"]: r for r in lp.compute(cut, NOW.date())["rows"]}
        late = [m for m in rows if m >= "2025-03"]
        self.assertTrue(all(rows2[m]["P"] == lp.UNKNOWN and rows2[m]["kind"] == "hold" for m in late))
        self.assertEqual([(rows2[m]["L"], rows2[m]["L_raw"]) for m in late], [(rows[m]["L"], rows[m]["L_raw"]) for m in late])
        self.assertTrue(any(rows[m]["L"] != rows[lp.mshift(m, -1)]["L"] for m in late))   # 그 사이 L이 실제로 바뀐다
        replay = " ".join(lp.DEFS["replay"])
        self.assertIn("그 달 L을 모르면('?') L의 연속 셈은 끊긴다", replay)
        self.assertIn("P만 모르면", replay)
        self.assertNotIn("L이나 P를 모르면", replay)

    def test_peak_tag_is_the_fact_only(self):
        self.assertEqual(lp.TAG_PEAK, "고점 통과")                                       # 비공개 꼬리표의 해석 부분은 싣지 않는다
        self.assertTrue(lp.PRIVATE_TAG_PEAK.startswith(lp.TAG_PEAK + " — "))
        for word in DIRECTION:
            self.assertNotIn(word, lp.TAG_PEAK)


# ---------- 물가 P ----------

class InflationStateTest(unittest.TestCase):
    def test_band_hysteresis_edges(self):
        self.assertEqual(lp.bands([3.0, 3.15, 3.0, 2.95, 2.85, 2.65, 2.55, 2.68, 2.75]),
                         ["M", "H", "H", "H", "M", "M", "Lo", "Lo", "M"])
        self.assertEqual(lp.bands([3.1, 3.1000004, 3.100001]), ["M", "M", "H"])       # H는 3.1 초과로 들어간다
        self.assertEqual(lp.bands([3.2, 2.9, 2.8999996, 2.899999]), ["H", "H", "H", "M"])    # 2.9 미만에서 나온다
        self.assertEqual(lp.bands([2.6, 2.5999996, 2.599999]), ["M", "M", "Lo"])      # Lo는 2.6 미만으로 들어간다
        self.assertEqual(lp.bands([2.5, 2.7, 2.7000004, 2.700001]), ["Lo", "Lo", "Lo", "M"])  # 2.7 초과에서 나온다
        self.assertEqual(lp.bands([3.2, None, 2.95]), ["H", None, "H"])               # 빈 달은 상태를 넘긴다
        self.assertEqual(lp.bands([2.5, 3.2]), ["Lo", "H"])

    def test_momentum_classes(self):
        mc = lp.mom_class
        self.assertEqual(mc([None, 0.5]), "A")                                         # 가속은 한 발표, 앞 달이 없어도
        self.assertEqual(mc([0.9, 0.5 - 4e-7]), "A")
        self.assertEqual(mc([0.9, 0.499999]), "F")
        self.assertEqual(mc([-0.3, -0.3]), "D")                                        # 둔화는 두 발표 연속(경계 포함)
        self.assertEqual(mc([-0.4, -0.3 + 4e-7]), "D")
        self.assertEqual(mc([0.1, -0.5]), "F")
        self.assertEqual(mc([-0.29, -0.31]), "F")
        self.assertIsNone(mc([None, -0.35]))                                           # 둔화 쪽인데 앞 발표가 없다
        self.assertIsNone(mc([-0.35]))
        self.assertIsNone(mc([0.6, None]))                                             # 그 달 값이 없다
        self.assertIsNone(mc([]))
        self.assertEqual(mc([None, -0.29]), "F")                                       # 두 문턱 사이면 앞 달과 무관
        self.assertEqual(mc([-0.4, 0.5]), "A")

    def test_nine_p_cells(self):
        want = {("H", "A"): P_P, ("H", "F"): P_P, ("H", "D"): P_D, ("M", "A"): P_P, ("M", "F"): P_0,
                ("M", "D"): P_M, ("Lo", "A"): P_0, ("Lo", "F"): P_M, ("Lo", "D"): P_M}
        self.assertEqual(lp.P_GRID, want)
        for (b, m), p in want.items():
            self.assertEqual(lp.p_state(b, m), p)
        for b, m in ((None, "A"), ("H", None), (None, None)):
            self.assertEqual(lp.p_state(b, m), "?")

    def test_pce_states_walk_the_months(self):
        rows = lp.pce_states({"2026-01": {"Y3": 3.0, "mom": 0.6}, "2026-02": {"Y3": 3.0, "mom": 0.4},
                              "2026-03": {"Y3": 3.2, "mom": -0.1}, "2026-04": {"Y3": 3.2, "mom": -0.35},
                              "2026-05": {"Y3": 3.0, "mom": -0.4}, "2026-06": {"Y3": 2.85, "mom": -0.6},
                              "2026-07": {"Y3": 2.85, "mom": -0.25}})
        self.assertEqual([rows[m]["mom_class"] for m in sorted(rows)], ["A", "F", "F", "F", "D", "D", "F"])
        self.assertEqual([rows[m]["P"] for m in sorted(rows)], [P_P, P_0, P_P, P_P, P_D, P_M, P_0])

    def test_infl_rows_exact_base_and_two_of_three(self):
        m = {lp.mshift("2024-01", i): 100 * 1.003 ** i for i in range(30)}
        del m["2025-02"]
        rows = lp.infl_rows(m)
        self.assertIsNone(rows["2026-02"]["y12"])                                      # 1년 전 달이 빠졌다
        self.assertIsNone(rows["2025-05"]["a3"])
        self.assertAlmostEqual(rows["2026-03"]["y12"], (1.003 ** 12 - 1) * 100, places=10)
        self.assertEqual(rows["2026-03"]["Y3_n"], 2)                                   # 2026-01·03만
        self.assertAlmostEqual(rows["2026-03"]["mom"], rows["2026-03"]["a6"] - rows["2026-03"]["y12"], places=12)
        cpi = lp.infl_rows(m, cpi=True)
        self.assertEqual(cpi["2026-04"]["shutdown"], ["a3", "a6", "y12"])
        self.assertEqual(rows["2026-04"]["shutdown"], [])                             # PCE에는 붙지 않는다

    def test_p_state_agrees_with_the_oil_card(self):
        """유가 카드(oil_fetch)도 같은 운영자 정의로 P를 쓴다 — 같은 입력이면 띠·모멘텀·P·Y3·모멘텀 값이 같다."""
        series = W()["PCEPILFE"]
        mine = lp.pce_states(lp.infl_rows(lp.mmap(series)))
        theirs = oil.pce_states(oil.infl_rows(series))
        self.assertEqual(len(mine), len(theirs))
        for d, _ in series:
            a, b = mine[lp.mkey(d)], theirs[oil._mkey(d)]
            self.assertEqual((a["band"], a["mom_class"], a["P"], a["Y3"], a["mom"], a["y12"], a["a3"], a["a6"]),
                             (b["band"], b["mom_class"], b["P"], b["Y3"], b["mom"], b["y12"], b["a3"], b["a6"]), d)
        self.assertEqual((lp.H_IN, lp.H_OUT, lp.LO_IN, lp.LO_OUT, lp.MOM, lp.MOM_N, lp.MOM_DN, lp.MOM_DN_N, lp.SUPPLY_HC),
                         (oil.H_IN, oil.H_OUT, oil.LO_IN, oil.LO_OUT, oil.MOM, oil.MOM_N, oil.MOM_DN, oil.MOM_DN_N,
                          oil.SUPPLY_HC))
        self.assertEqual(lp.P_GRID, oil.P_GRID)
        self.assertEqual((lp.TAG_SUPPLY, lp.TAG_ENERGY_DOWN), (oil.TAG_SUPPLY, oil.TAG_DOWN))


class CellTest(unittest.TestCase):
    def test_sixteen_cells(self):
        self.assertEqual(len(lp.CELLS), 16)
        kinds = {"up": {(L_P, P_P), (L_P, P_0), (L_0, P_P)}, "mixed": {(L_M, P_P), (L_MM, P_P)},
                 "box": {(L_P, P_D), (L_P, P_M), (L_0, P_0), (L_0, P_D)}}
        for L in lp.GRID_L:
            for P in lp.GRID_P:
                want = next((k for k, cells in kinds.items() if (L, P) in cells), "down")
                self.assertEqual(lp.cell(L, P)[1], want, (L, P))
                self.assertEqual(lp.cell(L, P), lp.CELLS[(L, P)])
        self.assertEqual(lp.cell(L_M, P_M), ("되돌림 위험 (2024 하반기형)", "down"))
        self.assertEqual(lp.cell(L_P, P_P), ("금리 상방 여지 (확인)", "up"))
        self.assertEqual(lp.cell(L_0, P_0), ("박스", "box"))

    def test_hold(self):
        self.assertEqual(lp.cell("?", "?"), ("판정 보류(노동·물가)", "hold"))
        self.assertEqual(lp.cell(L_0, "?"), ("판정 보류(물가)", "hold"))
        self.assertEqual(lp.cell("?", P_P), ("판정 보류(노동)", "hold"))
        self.assertEqual(lp.cell(L_0, None), ("판정 보류(물가)", "hold"))


# ---------- 청구 다리 ----------

class ClaimsTest(unittest.TestCase):
    def test_flags_need_four_weeks_and_ccsa_up(self):
        rows = lambda q, up: [{"ratio52": x, "ccsa_up": up} for x in q]
        self.assertTrue(lp.claims_on_flags(rows([1.3] * 4, True))[-1])
        self.assertFalse(lp.claims_on_flags(rows([1.0, 1.3, 1.3, 1.3], True))[-1])   # 3주
        self.assertFalse(lp.claims_on_flags(rows([1.3] * 4, False))[-1])             # 계속 청구가 낮아짐
        self.assertIsNone(lp.claims_on_flags(rows([1.3] * 4, None))[-1])             # 비교할 수 없으면 '?'
        self.assertTrue(lp.claims_on_flags(rows([1.25] * 4, True))[-1])              # 경계 포함
        self.assertTrue(lp.claims_on_flags(rows([1.25 - 4e-7] * 4, True))[-1])
        self.assertFalse(lp.claims_on_flags(rows([1.2499] * 4, True))[-1])
        self.assertFalse(lp.claims_on_flags(rows([1.3, None, 1.3, 1.3, 1.3], True))[-2])   # 빈 주는 연속을 끊는다

    def test_panel_ratio_and_the_first_on_week(self):
        sat = saturdays(D(2024, 1, 6), 70)
        icsa = [(d, 200000.0 if i < 60 else 260000.0) for i, d in enumerate(sat)]
        ccsa = [(d, 1.6e6 if i < 60 else 2.0e6) for i, d in enumerate(sat)]
        p = lp.claims_panel(icsa, ccsa)
        self.assertIsNone(p[42]["ratio52"])                                              # 앞 c4가 39개
        self.assertAlmostEqual(p[43]["ratio52"], 1.0, places=12)                         # 40개부터
        self.assertAlmostEqual(p[62]["ratio52"], 1.225, places=12)
        self.assertAlmostEqual(p[63]["ratio52"], 1.3, places=12)
        self.assertEqual([r["week"] for r in p if r["claims_on"]][0], sat[66])          # 63주째부터 4주
        self.assertFalse(p[65]["claims_on"])

    def test_exactly_one_and_a_quarter(self):
        sat = saturdays(D(2024, 1, 6), 70)
        icsa = [(d, 200000.0 if i < 60 else 250000.0) for i, d in enumerate(sat)]
        p = lp.claims_panel(icsa, [(d, 1.6e6 if i < 60 else 2.0e6) for i, d in enumerate(sat)])
        self.assertAlmostEqual(p[63]["ratio52"], 1.25, places=12)
        self.assertEqual([r["week"] for r in p if r["claims_on"]][0], sat[66])

    def test_ccsa_one_week_late_and_missing(self):
        sat = saturdays(D(2020, 1, 4), 80)
        up = [(d, 200000.0 if i < 60 else 260000.0) for i, d in enumerate(sat)]
        cc = [(d, 1.6e6 if i < 60 else 2.0e6 + 1000 * i) for i, d in enumerate(sat)]
        p = lp.claims_panel(up, cc[:-1])                                                  # CCSA는 한 주 늦다
        self.assertEqual((p[-1]["claims_on"], p[-1]["ccsa_week"]), (True, sat[-2]))
        p = lp.claims_panel(up, cc[:-2])                                                  # 두 주 전(14일)은 13일 밖
        self.assertIsNone(p[-1]["claims_on"])
        self.assertNotIn("ccsa_week", p[-1])
        self.assertEqual((p[-2]["claims_on"], p[-2]["ccsa_week"]), (True, sat[-3]))
        p = lp.claims_panel(up, cc[:-3])                                                  # 3주 비면 '?'
        self.assertIsNone(p[-1]["claims_on"])
        self.assertTrue(p[-3]["claims_on"])
        flat = [(d, 1.6e6) for d in sat]
        self.assertFalse(lp.claims_panel(up, flat)[-1]["claims_on"])                     # 13주 전보다 높지 않음
        self.assertIsNone(lp.claims_panel(up, [])[-1]["claims_on"])

    def test_c4_needs_four_consecutive_weeks_and_the_13_week_fall(self):
        sat = saturdays(D(2020, 1, 4), 80)
        p = lp.claims_panel([(d, 1.0) for i, d in enumerate(sat) if i != 10], [])
        self.assertIsNone(p[10]["c4"])                                                    # 빠진 주가 낀 4주
        self.assertIsNone(p[12]["c4"])
        self.assertIsNotNone(p[13]["c4"])
        down = [(d, 250000.0 if i < 60 else 200000.0) for i, d in enumerate(sat)]
        p = lp.claims_panel(down, [(d, 1.6e6) for d in sat])
        self.assertEqual(next(i for i, r in enumerate(p) if r["c4_down13_4w"]), 63)


# ---------- 발표일·JOLTS ----------

class ReleaseTest(unittest.TestCase):
    def test_release_dates(self):
        self.assertEqual(lp.release_date("cps", "2026-10"), D(2026, 11, 6))           # 다음 달 첫 금요일
        self.assertEqual(lp.release_date("cps", "2026-04"), D(2026, 5, 1))
        self.assertEqual(lp.release_date("pce", "2026-09"), D(2026, 10, 30))          # 다음 달 마지막 평일
        self.assertEqual(lp.release_date("pce", "2026-04"), D(2026, 5, 29))           # 5-31은 일요일
        self.assertEqual(lp.release_date("jolts", "2026-03"), D(2026, 5, 7))          # 다다음 달 7일
        self.assertEqual(lp.release_date("jolts", "2026-01"), D(2026, 3, 9))          # 3-07은 토요일
        self.assertEqual(lp.release_date("ccsa", D(2026, 10, 31)), D(2026, 11, 12))
        self.assertEqual(lp.release_date("cps", "2025-10"), D(2025, 12, 16))          # 셧다운 표
        self.assertEqual(lp.release_date("pce", "2025-09"), D(2025, 12, 5))
        with self.assertRaises(ValueError):
            lp.release_date("gdp", "2026Q1")

    def test_jolts_month(self):
        jm = lp.mrange("2024-01", "2026-09")
        self.assertEqual(lp.jolts_month(jm, "2026-09"), "2026-08")       # 08월분(10-07)은 PCE 09월분(10-30) 전, 09월분(11-09)은 뒤
        self.assertEqual(lp.jolts_month(jm, "2026-10"), "2026-09")       # 11-09 ≤ 11-30
        self.assertEqual(lp.jolts_month(lp.mrange("2024-01", "2026-07"), "2026-09"), "2026-07")
        self.assertEqual(lp.jolts_month(jm, "2025-09"), "2025-09")       # PCE가 12-05로 늦어 같은 달 JOLTS(11-07)까지
        self.assertIsNone(lp.jolts_month(["2026-09"], "2026-09"))
        self.assertIsNone(lp.jolts_month([], "2026-09"))


# ---------- 노동 다리 ----------

class LaborPanelTest(unittest.TestCase):
    def test_known_legs(self):
        ms = lp.mrange("2020-01", "2024-06")
        mo = lambda f: [(lp.mdate(m), f(i, m)) for i, m in enumerate(ms) if f(i, m) is not None]
        data = {"UNRATE": mo(lambda i, m: 4.0),
                "UNEMPLOY": mo(lambda i, m: 6000.0 if m < "2023-03" else 6300.0),
                "LNS13026638": mo(lambda i, m: 900.0 if m < "2023-03" else 1100.0),
                "USPRIV": mo(lambda i, m: 100000.0 - 50.0 * max(0, lp.mdiff(m, "2023-09"))),
                "LNS12300060": mo(lambda i, m: 80.0 - 0.05 * i),
                "JTSJOL": mo(lambda i, m: 6000.0 if m >= "2022-06" else None),
                "JTSQUR": mo(lambda i, m: 2.0 + 0.01 * lp.mdiff(m, "2022-06") if m >= "2022-06" else None)}
        by = {r["month"]: r for r in lp.labor_panel(data, D(2020, 1, 1))["rows"]}
        r = by["2023-12"]
        self.assertAlmostEqual(r["d_unemp12"], 300.0, places=9)
        self.assertAlmostEqual(r["layoff_share"], 2 / 3, places=12)
        self.assertEqual(r["layoff_class"], "해고형")
        self.assertEqual((by["2024-06"]["layoff_share"], by["2024-06"]["layoff_class"]), (None, None))
        self.assertAlmostEqual(r["p3"], -50.0, places=9)
        self.assertAlmostEqual(r["epop3_d6"], -0.30, places=9)
        self.assertEqual(r["jolts_month"], "2023-11")
        self.assertAlmostEqual(r["vu3"], 6000 / 6300, places=12)
        self.assertAlmostEqual(r["vu3_d6"], 0.0, places=12)
        self.assertAlmostEqual(r["quits3_d6"], 0.06, places=12)
        self.assertEqual((r["sahm"], r["hi_gap"], r["rising3"]), (0.0, 0.0, False))
        self.assertEqual(r["absent"], ["청구"])                                          # 청구 시리즈 없음
        self.assertIn("V/U", by["2022-06"]["absent"])                                    # JOLTS가 아직 없는 달
        self.assertNotIn("V/U", by["2023-12"]["absent"])

    def test_history_before_1960_is_kept_for_the_windows(self):
        old = {"UNRATE": [(lp.mdate(m), 5.0 + 0.01 * i) for i, m in enumerate(lp.mrange("1958-01", "1962-12"))]}
        rows = lp.labor_panel(old)["rows"]
        self.assertEqual(rows[0]["month"], "1960-01")                                    # 기준월은 1960부터
        self.assertIsNotNone(rows[0]["sahm"])                                             # 창은 1959 자료로
        self.assertEqual(lp.labor_panel({})["rows"], [])

    def test_missing_unrate_month_uses_two_months_and_tags_it(self):
        rep = lp.compute(W(), NOW.date())
        legs = rep["legs"]
        self.assertNotIn("2025-10", legs)                                                 # 실업률이 빠진 달은 기준월이 아니다
        self.assertEqual((legs["2025-09"]["u3_n"], legs["2025-11"]["u3_n"], legs["2025-12"]["u3_n"],
                          legs["2026-01"]["u3_n"]), (3, 2, 2, 3))
        un = lp.mmap(W()["UNRATE"])
        self.assertAlmostEqual(legs["2025-11"]["u3"], (un["2025-11"] + un["2025-09"]) / 2, places=12)
        rows = {r["month"]: r for r in rep["rows"]}
        self.assertIn(lp.TAG_TWO_MONTH, rows["2025-11"]["tags"])
        self.assertIn(lp.TAG_TWO_MONTH, rows["2025-12"]["tags"])
        self.assertNotIn(lp.TAG_TWO_MONTH, rows["2026-01"]["tags"])
        self.assertIn(lp.TAG_DELAYED, rows["2025-09"]["tags"])
        self.assertNotIn(lp.TAG_DELAYED, rows["2026-01"]["tags"])

    def test_perm_fallback_series(self):
        w = dict(W())
        alt = [(d, v * 1.3) for d, v in w.pop("LNS13026638")]
        self.assertIsNone(lp.perm_sid(w))
        w["LNS13025699"] = alt
        self.assertEqual(lp.perm_sid(w), "LNS13025699")
        panel = lp.labor_panel(w)
        self.assertEqual(panel["perm_sid"], "LNS13025699")
        self.assertNotIn("해고 몫", panel["absent"])


# ---------- 꼬리표 ----------

class TagsTest(unittest.TestCase):
    def tags(self, P, head, core, goods=None, t="2026-08", shutdown=False):
        cpi_all = {t: {"a3": head}}
        cpi_core = {t: {"a3": core, "shutdown": ["y12"] if shutdown else []}}
        goods_m = {} if goods is None else {t: 100 * (1 + goods / 100) ** 0.5, lp.mshift(t, -6): 100.0}
        return lp.infl_tags(t, {"P": P, "seasonal": int(t[5:7]) <= 6}, cpi_all, cpi_core, goods_m)

    def test_supply_energy_goods_seasonal_shutdown(self):
        self.assertEqual(self.tags(P_P, 4.0, 2.5), [lp.TAG_SUPPLY])
        self.assertEqual(self.tags(P_P, 3.5, 2.5), [lp.TAG_SUPPLY])                     # 경계 포함
        self.assertEqual(self.tags(P_0, 4.0, 2.5), [])                                  # 공급형은 P+에서만
        self.assertEqual(self.tags(P_0, 0.5, 2.0), [lp.TAG_ENERGY_DOWN])               # 에너지 하락은 P와 무관
        self.assertEqual(self.tags(P_P, 2.5, 2.5, goods=2.0), [lp.TAG_GOODS])
        self.assertEqual(self.tags(P_P, 2.5, 2.5, goods=1.9), [])
        self.assertEqual(self.tags(P_0, None, None, t="2026-03"), [lp.TAG_SEASONAL])
        self.assertEqual(self.tags(P_0, None, None, shutdown=True), [lp.TAG_SHUTDOWN])

    def test_trimmed_mean_tag_and_the_other_two_are_never_made(self):
        rep = lp.compute(W(), NOW.date())
        seen = {t for r in rep["rows"] for t in r["tags"]}
        self.assertFalse(seen & set(lp.EXCLUDED_TAGS))
        self.assertEqual(lp.EXCLUDED_TAGS, ("상당 부분 반영", "TP 주도", "폭 좁음(트림 ≤ 3)"))
        self.assertTrue(any(r["P"] == P_P for r in rep["rows"]))                       # P+ 달이 있어도
        allowed = {lp.TAG_PEAK, lp.TAG_SUPPLY, lp.TAG_ENERGY_DOWN, lp.TAG_GOODS, lp.TAG_SEASONAL, lp.TAG_SHUTDOWN,
                   lp.TAG_TWO_MONTH, lp.TAG_DELAYED}
        self.assertEqual({t for t in seen if not t.startswith("단일 자료(")} - allowed, set())

    def test_single_source_tag_when_a_leg_has_no_data(self):
        w = {k: v for k, v in W().items() if k != "JTSJOL"}
        rows = {r["month"]: r for r in lp.compute(w, NOW.date())["rows"]}
        self.assertIn("단일 자료(V/U 없음)", rows["2026-09"]["tags"])
        rows = {r["month"]: r for r in lp.compute(W(), NOW.date())["rows"]}
        self.assertIn("단일 자료(V/U 없음)", rows["1999-06"]["tags"])                  # JOLTS 시작(2000-12) 전
        self.assertFalse(any(t.startswith("단일 자료(") for t in rows["2026-09"]["tags"]))


# ---------- 재생·지금 칸·사례 ----------

class DecisionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rep = lp.compute(W(), NOW.date())

    def test_rows_and_history(self):
        rows = self.rep["rows"]
        self.assertEqual(rows[0]["month"], "1990-01")
        self.assertEqual(rows[-1]["month"], "2026-10")
        hist = self.rep["history"]
        self.assertEqual(hist[0]["month"], "2022-01")
        self.assertEqual([r["month"] for r in hist], sorted(r["month"] for r in hist))
        r = next(r for r in rows if r["month"] == "2026-09")
        self.assertEqual(r["known"], D(2026, 10, 30))                                     # PCE 발표가 가장 늦다

    def test_current_is_the_last_month_with_a_cell_and_latest_the_newer_hold(self):
        cur, lat = self.rep["current"], self.rep["latest"]
        self.assertEqual(cur["month"], "2026-09")                                         # 근원 PCE가 9월까지
        self.assertNotEqual(cur["kind"], "hold")
        self.assertEqual((lat["month"], lat["P"], lat["kind"]), ("2026-10", "?", "hold"))
        self.assertEqual(lat["cell"], "판정 보류(물가)")
        legs = cur["legs"]
        self.assertEqual([x[0] for x in legs], list(lp.LEG_ORDER))
        self.assertEqual(legs[-2][1:], (cur["inflation"]["Y3"], "2026-09", cur["band"]))
        self.assertEqual(legs[-1][1:], (cur["inflation"]["mom"], "2026-09", cur["mom_class"]))
        self.assertEqual(legs[6][2], self.rep["legs"]["2026-09"]["jolts_month"])        # V/U는 JOLTS 달
        w = {k: [x for x in v if x[0] < D(2026, 10, 1)] for k, v in W().items()}        # 마지막 달에 칸이 있으면 latest 없음
        rep = lp.compute(w, NOW.date())
        self.assertEqual((rep["current"]["month"], rep["latest"]), ("2026-09", None))

    def test_all_hold_and_empty(self):
        rep = lp.compute({"UNRATE": W()["UNRATE"]}, NOW.date())                          # 물가가 없으면 모두 보류
        self.assertEqual(rep["current"]["month"], rep["rows"][-1]["month"])
        self.assertEqual(rep["current"]["kind"], "hold")
        self.assertIsNone(rep["latest"])
        rep = lp.compute({}, NOW.date())
        self.assertEqual((rep["rows"], rep["current"], rep["latest"], rep["history"]), ([], None, None, []))

    def test_observations_after_asof_are_dropped(self):
        rep = lp.compute(W(), D(2026, 6, 15))
        self.assertEqual(rep["rows"][-1]["month"], "2026-06")
        self.assertLessEqual(rep["current"]["month"], "2026-06")

    def test_expected_cases(self):
        fake = [{"month": "2022-03", "L": L_P, "P": P_P, "cell": "금리 상방 여지 (확인)"},
                {"month": "2022-04", "L": L_M, "P": P_P, "cell": "x"},
                {"month": "2024-08", "L": L_M, "P": P_M, "cell": "되돌림 위험 (2024 하반기형)"},
                {"month": "2024-09", "L": "?", "P": "?", "cell": "판정 보류(노동·물가)"},
                {"month": "2026-05", "L": L_0, "P": P_D, "cell": "박스 (하단 시험)"},
                {"month": "2026-11", "L": L_MM, "P": P_0, "cell": "큰 되돌림 위험"}]
        res = {e["case"]: e for e in lp.expected_check(fake)}
        self.assertEqual([e["case"] for e in lp.expected_check(fake)],
                         ["2022", "2023 하반기", "2024 1분기", "2024-08~09", "2024-12~2025-01", "2026-05 이후"])
        self.assertEqual((res["2022"]["n"], res["2022"]["matched"]), (2, 1))
        self.assertEqual([i["match"] for i in res["2022"]["items"]], [True, False])
        self.assertEqual((res["2024-08~09"]["n"], res["2024-08~09"]["matched"]), (2, 1))
        self.assertEqual((res["2026-05 이후"]["n"], res["2026-05 이후"]["matched"]), (2, 1))   # 끝이 열린 사례, L은 무관
        self.assertEqual(res["2023 하반기"]["n"], 0)
        self.assertEqual([e["holdout"] for e in lp.expected_check(fake)], [False, False, True, True, True, True])
        self.assertEqual(res["2024-08~09"]["tag_unchecked"], "상당 부분 반영")
        self.assertEqual(res["2026-05 이후"]["tag_unchecked"], "TP 주도")
        self.assertIsNone(res["2022"]["tag_unchecked"])
        self.assertEqual((res["2026-05 이후"]["want_L"], res["2026-05 이후"]["want_P"]), (None, [P_P, P_D]))
        self.assertEqual(set(res["2022"]["items"][0]), {"month", "L", "P", "cell", "match"})


# ---------- 공개 파일 ----------

class NumTest(unittest.TestCase):
    def test_four_decimals_unless_a_threshold_would_flip(self):
        self.assertEqual(lp.num(0.456789), 0.4568)
        self.assertEqual(lp.num(0.39996, (0.4,)), 0.39996)                              # 넷째 자리면 0.4000으로 문턱에 닿는다
        self.assertEqual(lp.num(0.40004, (0.4,)), 0.40004)
        self.assertEqual(lp.num(0.4, (0.4,)), 0.4)
        self.assertEqual(lp.num(0.4000004, (0.4,)), 0.4)                                # 비교도 0.4와 같다
        self.assertEqual(lp.num(3.10004, lp.LEG_THS[lp.LEG_BAND]), 3.10004)
        self.assertEqual(lp.num(-0.29996, lp.LEG_THS[lp.LEG_MOM]), -0.29996)
        self.assertEqual(lp.num(1.24999, (1.25,)), 1.24999)
        self.assertEqual(repr(lp.num(-0.00001)), "0.0")                                 # −0.0을 쓰지 않는다
        self.assertIs(lp.num(True), True)
        self.assertIsNone(lp.num(None))


class ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        info = {sid: "net" for sid in lp.SERIES}
        cls.c = lp.build(W(), info, NOW)
        cls.text = json.dumps(cls.c, ensure_ascii=False)

    def test_top_level_keys_and_fixed_fields(self):
        c = self.c
        for k in ("schema", "generated_at", "asof", "notice", "label", "fixed", "holdout_from", "constants", "grid", "defs",
                  "current", "latest", "history", "expected", "excluded_tags", "series", "sources", "notices"):
            self.assertIn(k, c)
        self.assertEqual((c["schema"], c["generated_at"], c["asof"], c["fixed"], c["holdout_from"]),
                         (1, "2026-11-18T04:30:00+00:00", "2026-11-18", "2026-10-14", "2024-01"))
        self.assertEqual(c["label"], "운영자 판단 격자의 칸 이름(운영자 메모) — 예측 아님 · 예측력 검증 안 됨")
        self.assertEqual(c["constants"], lp.CONSTANTS)
        self.assertEqual(c["excluded_tags"], ["상당 부분 반영", "TP 주도", "폭 좁음(트림 ≤ 3)"])
        self.assertEqual(len(c["notices"]), 2)
        self.assertIn("macro-regime-check", c["notices"][1])
        self.assertTrue(c["notice"].endswith("다.") and all(x.endswith("다.") for x in (c["notice"], c["notices"][0])))

    def test_grid_and_defs(self):
        gr = self.c["grid"]
        self.assertEqual((gr["L"], gr["P"]), (["L+", "L0", "L−", "L−−"], ["P+", "P0", "Pd", "P−"]))
        self.assertEqual(len(gr["cells"]), 4)
        for L, row in zip(gr["L"], gr["cells"]):
            self.assertEqual([x["P"] for x in row], gr["P"])
            for x in row:
                self.assertEqual(set(x), {"L", "P", "name", "kind"})
                self.assertEqual(x["L"], L)
                self.assertEqual((x["name"], x["kind"]), lp.CELLS[(x["L"], x["P"])])
                self.assertIn(x["kind"], ("up", "down", "box", "mixed"))
        d = self.c["defs"]
        self.assertEqual([x["state"] for x in d["L"]], ["L−−", "L−", "L+", "L0"])
        self.assertEqual([x["state"] for x in d["P"]], ["P+", "P0", "Pd", "P−"])
        self.assertEqual([x["band"] for x in d["band"]], ["H", "M", "Lo"])
        self.assertEqual([x["mom"] for x in d["mom"]], ["A", "F", "D"])
        self.assertEqual(len(d["pgrid"]), 9)
        self.assertEqual({(x["band"], x["mom"]): x["P"] for x in d["pgrid"]}, lp.P_GRID)
        for part in ("L", "P", "band", "mom"):
            self.assertTrue(all(isinstance(x["text"], str) and x["text"] for x in d[part]))
        texts = lambda part: " ".join(x["text"] for x in d[part])                       # 설명 글의 숫자가 상수와 같다
        for n in ("0.50", "0.40", "−0.3", "−0.15", "+0.2", "+0.10", "+0.1", "0.30%p", "0.20%p"):
            self.assertIn(n, texts("L"))
        for n in ("3.1", "2.9", "2.6", "2.7"):
            self.assertIn(n, texts("band"))
        self.assertIn(f"+{lp.MOM:g}", texts("mom"))
        self.assertIn(f"−{lp.MOM_DN:g}이 두 발표 연속", texts("mom"))
        self.assertIn(f"{lp.CLAIMS_RATIO:g}배", " ".join(d["replay"]))
        L = {x["state"]: x["text"] for x in d["L"]}                                    # 정의 글이 자리에 기대지 않는다
        self.assertIn("L−−·L−가 아니면서", L[L_P])
        self.assertEqual(L[L_0], "L−−·L−·L+가 아닌 달.")
        self.assertIn("해고 미확인(청구 다리가 켜져 있지 않음 — 꺼짐 또는 ?)", L[L_M])    # 청구 '?'도 (b)
        self.assertNotIn("청구 다리 꺼짐", json.dumps(d, ensure_ascii=False))
        self.assertIn("직전 띠", {x["band"]: x["text"] for x in d["band"]}["M"])         # M은 고정 구간이 아니다
        self.assertNotIn("(2.6~3.1)", texts("band"))
        for word in ("Δ6", "V/U", "hi_gap"):
            self.assertIn(word, " ".join(d["replay"]))
        self.assertEqual(d["tags"][0], {"tag": lp.TAG_PEAK, "text": d["tags"][0]["text"]})

    def test_current_block(self):
        cur = self.c["current"]
        self.assertEqual(list(cur), ["month", "known", "L", "L_raw", "P", "band", "mom_class", "cell", "kind", "tags", "legs",
                                     "inflation", "raw_rules", "d6u3"])
        self.assertEqual(cur["raw_rules"], lp.raw_rules(lp.compute(W(), NOW.date())["legs"]["2026-09"]))
        self.assertIsInstance(cur["d6u3"], float)
        self.assertEqual(cur["month"], "2026-09")
        D.fromisoformat(cur["known"])
        self.assertIn(cur["L"], lp.GRID_L)
        self.assertIn(cur["P"], lp.GRID_P)
        self.assertIn(cur["band"], ("H", "M", "Lo"))
        self.assertIn(cur["mom_class"], ("A", "F", "D"))
        self.assertEqual((cur["cell"], cur["kind"]), lp.CELLS[(cur["L"], cur["P"])])
        self.assertEqual(len(cur["legs"]), 13)
        self.assertEqual([x["name"] for x in cur["legs"]], list(lp.LEG_ORDER))
        for x in cur["legs"]:
            self.assertEqual(set(x), {"name", "value", "month", "on"})
            self.assertRegex(x["month"], r"^\d{4}-\d{2}$")
            self.assertTrue(x["value"] is None or isinstance(x["value"], (bool, int, float)))
            if isinstance(x["value"], float):
                self.assertEqual(x["value"], round(x["value"], 6))
        on = {x["name"]: x["on"] for x in cur["legs"]}
        for name in (lp.LEG_LAYOFF, lp.LEG_BAND, lp.LEG_MOM):
            self.assertIsInstance(on[name], str)
        self.assertIn(on[lp.LEG_LAYOFF], ("해고형", "진입형", "모호", "-"))
        for name in set(lp.LEG_ORDER) - {lp.LEG_LAYOFF, lp.LEG_BAND, lp.LEG_MOM}:
            self.assertIn(on[name], (True, False, None))
        self.assertEqual(set(cur["inflation"]), {"y12", "a3", "a6", "mom", "Y3", "Y3_n"})
        self.assertIsInstance(cur["inflation"]["Y3_n"], int)

    def test_latest_history_expected(self):
        lat = self.c["latest"]
        self.assertEqual(set(lat), {"month", "known", "L", "P", "cell", "kind", "tags"})
        self.assertEqual(lat["kind"], "hold")
        self.assertEqual(lat["known"], next(r["known"] for r in self.c["history"] if r["month"] == lat["month"]))
        hist = self.c["history"]
        self.assertEqual(hist[0]["month"], "2022-01")
        self.assertEqual(hist[-1]["month"], "2026-10")
        for r in hist:
            self.assertEqual(list(r), ["month", "known", "L", "L_raw", "P", "band", "mom_class", "cell", "kind", "tags"])
        for e in self.c["expected"]:
            for k in ("case", "want", "from", "to", "holdout", "n", "matched", "items"):
                self.assertIn(k, e)
            self.assertIsInstance(e["holdout"], bool)
            self.assertEqual(e["n"], len(e["items"]))
            self.assertEqual(e["matched"], sum(i["match"] for i in e["items"]))
        self.assertEqual(self.c["expected"][0]["want"], "노동 L0 또는 L+ · 물가 P+")
        self.assertIn("계산하지 않는다", self.c["expected_note"])
        note = self.c["expected_note"]                                                    # 표본 밖은 '문턱을 정한 뒤'가 아니다
        self.assertIn("표본 밖(hold-out)으로 지정한 구간", note)
        self.assertIn("2024-09", note)
        self.assertNotIn("정한 뒤의 구간", note)

    def test_series_and_sources(self):
        self.assertEqual([s["series"] for s in self.c["series"]], list(lp.SERIES))
        for s in self.c["series"]:
            self.assertEqual(set(s), {"series", "title", "last", "fetched"})
            self.assertEqual(s["fetched"], "net")
            D.fromisoformat(s["last"])
        self.assertEqual([s["series"] for s in self.c["sources"]], list(lp.SERIES))
        for s in self.c["sources"]:
            self.assertEqual(set(s), {"series", "url", "citation", "citation_required"})
            self.assertEqual(s["url"], f"https://fred.stlouisfed.org/series/{s['series']}")
            self.assertTrue(s["citation"].endswith("November 18, 2026."))
            self.assertIs(s["citation_required"], s["series"] in rp.CITATION_REQUIRED)    # ledger_build.sources()와 같은 규칙
            self.assertIs(s["citation_required"], False)                                   # 지금은 열세 시리즈 모두 공공 자료
        with mock.patch.object(rp, "CITATION_REQUIRED", rp.CITATION_REQUIRED + ("UNRATE",)):
            c = lp.build(W(), {sid: "net" for sid in lp.SERIES}, NOW)
        self.assertEqual({s["series"]: s["citation_required"] for s in c["sources"]}["UNRATE"], True)

    def test_fallback_series_listed_in_place(self):
        w = dict(W())
        w["LNS13025699"] = w.pop("LNS13026638")
        c = lp.build(w, {**{sid: "net" for sid in lp.SERIES}, "LNS13026638": "missing", "LNS13025699": "net"}, NOW)
        self.assertEqual([s["series"] for s in c["series"]][2:5], ["UNEMPLOY", "LNS13026638", "LNS13025699"])
        self.assertEqual(c["series"][3]["fetched"], "missing")
        self.assertIn("LNS13025699", [s["series"] for s in c["sources"]])
        self.assertNotIn("LNS13026638", [s["series"] for s in c["sources"]])

    def operator_text_removed(self):
        t = self.text
        names = sorted({n for n, _ in lp.CELLS.values()} | {"판정 보류(노동·물가)", "판정 보류(노동)", "판정 보류(물가)",
                                                          lp.LABEL, lp.TAG_PEAK}, key=len, reverse=True)
        for n in names:
            t = t.replace(n, "")
        return t

    def test_no_advice_or_direction_words_outside_the_operator_names(self):
        t = self.operator_text_removed()
        for word in ADVICE + DIRECTION:
            self.assertNotIn(word, t)
        self.assertEqual(t.count("판정"), t.count("판정 보류"))                             # 설명 글의 '판정 보류'뿐
        for word in FORBIDDEN_TEXT:
            self.assertNotIn(word, t)
        for word in ADVICE:                                                               # 칸 이름에도 없다
            self.assertNotIn(word, self.text)

    def test_no_email_no_local_paths_no_licensed_series(self):
        for word in ("@", "/home", "\\", ".work", "C:", "users", "Users"):
            self.assertNotIn(word, self.text)
        for sid in ("SP500", "BAML", "NASDAQ", "BAA10Y"):
            self.assertNotIn(sid, self.text)

    def test_compact_json_and_stable(self):
        with tempfile.TemporaryDirectory() as d:
            lp.write(d, self.c)
            with open(os.path.join(d, lp.FILE), encoding="utf-8") as f:
                raw = f.read()
            self.assertNotIn("\n", raw)
            self.assertEqual(json.loads(raw), json.loads(self.text))
            self.assertEqual(os.listdir(d), [lp.FILE])                                    # 임시 파일이 남지 않는다


# ---------- 수신·쓰기 ----------

class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.out, self.cache, self.reuse = (os.path.join(self.tmp, x) for x in ("data", "cache", "fred"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_main(self, fake, now=NOW, extra=(), clock=None):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = lp.main(["--out", self.out, "--cache", self.cache, "--reuse", self.reuse, *extra], now=now,
                           clock=clock or Clock(), loader=fake)
        return code, buf.getvalue()

    def read(self):
        with open(os.path.join(self.out, lp.FILE), encoding="utf-8") as f:
            return json.load(f)

    def test_first_run_writes(self):
        fake = FakeFred(W())
        code, out = self.run_main(fake)
        self.assertEqual(code, 0)
        c = self.read()
        self.assertEqual(c["current"]["month"], "2026-09")
        self.assertEqual([s for s, *_ in fake.calls], list(lp.SERIES))                   # 대안 시리즈는 받지 않는다
        self.assertTrue(all(t == lp.TIMEOUT for _, off, t in fake.calls))
        self.assertNotIn("::warning::", out)

    def test_one_missing_series_writes_nothing_and_keeps_yesterday(self):
        os.makedirs(self.out)
        with open(os.path.join(self.out, lp.FILE), "w", encoding="utf-8") as f:
            f.write('{"schema":1,"yesterday":true}')
        code, out = self.run_main(FakeFred(W(), fail={"JTSQUR"}))
        self.assertEqual(code, 0)
        self.assertTrue(self.read()["yesterday"])
        self.assertIn("::warning::[lp_fetch]", out)
        self.assertIn("JTSQUR", out)
        self.assertNotIn("bad.invalid", out)                                             # 오류 원문은 싣지 않는다
        self.assertEqual(out.count("::warning::"), 1)

    def test_online_cache_fallback_counts_as_missing(self):
        code, out = self.run_main(FakeFred(W(), cache={"CCSA"}))
        self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(os.path.join(self.out, lp.FILE)))
        self.assertIn("CCSA", out)

    def test_perm_fallback_and_the_pair_counted_once(self):
        w = dict(W())
        w["LNS13025699"] = [(d, v * 1.3) for d, v in w["LNS13026638"]]
        fake = FakeFred(w, fail={"LNS13026638"})
        code, out = self.run_main(fake)
        self.assertEqual(code, 0)
        c = self.read()
        got = {s["series"]: s["fetched"] for s in c["series"]}
        self.assertEqual((got["LNS13026638"], got["LNS13025699"]), ("missing", "net"))
        self.assertEqual([s for s, *_ in fake.calls].index("LNS13025699"), 4)
        code, out = self.run_main(FakeFred(w, fail={"LNS13026638", "LNS13025699"}))
        self.assertIn("LNS13026638/LNS13025699", out)

    def test_budget_and_per_request_timeout(self):
        fake = FakeFred(W())
        code, out = self.run_main(fake, extra=("--budget", "10"), clock=Clock(step=1.0))
        self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(os.path.join(self.out, lp.FILE)))              # 시간이 모자라 뒤 시리즈를 못 받음
        timeouts = [t for _, _, t in fake.calls]
        self.assertTrue(all(0 < t <= lp.TIMEOUT for t in timeouts))
        self.assertLess(timeouts[-1], lp.TIMEOUT)                                       # 남은 시간이 상한
        self.assertLess(len(fake.calls), len(lp.SERIES))
        self.assertIn("::warning::", out)

    def test_reuses_todays_regime_check_files_only(self):
        os.makedirs(self.reuse)
        w = W()
        for sid in ("UNRATE", "PCEPILFE"):
            with open(ff.cache_path(self.reuse, sid), "w", encoding="utf-8") as f:
                f.write(fred_text(w[sid], sid))
        ts = NOW.timestamp()
        os.utime(ff.cache_path(self.reuse, "UNRATE"), (ts, ts))
        old = (NOW - datetime.timedelta(days=1)).timestamp()
        os.utime(ff.cache_path(self.reuse, "PCEPILFE"), (old, old))
        fake = FakeFred(w)
        code, _ = self.run_main(fake)
        self.assertEqual(code, 0)
        asked = [s for s, *_ in fake.calls]
        self.assertNotIn("UNRATE", asked)                                               # 오늘 받은 것은 다시 받지 않는다
        self.assertIn("PCEPILFE", asked)                                                # 어제 것은 받는다
        self.assertEqual({s["series"]: s["fetched"] for s in self.read()["series"]}["UNRATE"], "net")
        self.assertTrue(os.path.exists(ff.cache_path(self.cache, "UNRATE")))           # 이 카드의 캐시에도 옮겨 둔다

    def test_offline_reads_the_cache(self):
        os.makedirs(self.cache)
        for sid in lp.SERIES:
            with open(ff.cache_path(self.cache, sid), "w", encoding="utf-8") as f:
                f.write(fred_text(W()[sid], sid))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = lp.main(["--out", self.out, "--cache", self.cache, "--reuse", self.reuse, "--offline"], now=NOW)
        self.assertEqual(code, 0)
        c = self.read()
        self.assertEqual({s["fetched"] for s in c["series"]}, {"cache"})
        self.assertEqual(c["current"]["month"], "2026-09")

    def test_same_content_is_not_rewritten(self):
        self.run_main(FakeFred(W()))
        path = os.path.join(self.out, lp.FILE)
        first = self.read()
        os.utime(path, (1, 1))
        code, out = self.run_main(FakeFred(W()), now=NOW + datetime.timedelta(hours=2))
        self.assertEqual(code, 0)
        self.assertIn("다시 쓰지 않음", out)
        self.assertEqual(os.path.getmtime(path), 1)
        self.assertEqual(self.read()["generated_at"], first["generated_at"])
        code, out = self.run_main(FakeFred(W()), now=NOW + datetime.timedelta(days=1))   # 다음 날은 asof가 달라 다시 쓴다
        self.assertEqual(self.read()["asof"], "2026-11-19")

    def test_write_failure_exits_one(self):
        with open(os.path.join(self.tmp, "afile"), "w") as f:
            f.write("x")
        self.out = os.path.join(self.tmp, "afile")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            code = lp.main(["--out", self.out, "--cache", self.cache, "--reuse", self.reuse], now=NOW, clock=Clock(),
                           loader=FakeFred(W()))
        self.assertEqual(code, 1)

    def test_calculation_error_keeps_the_file(self):
        with mock.patch.object(lp, "replay", side_effect=TypeError("깨짐")):            # 계산 쪽 뜻밖의 오류
            code, out = self.run_main(FakeFred(W()))
        self.assertEqual(code, 0)
        self.assertIn("계산 오류", out)
        self.assertFalse(os.path.exists(os.path.join(self.out, lp.FILE)))

    def test_non_finite_observations_are_dropped_and_never_written(self):
        """FRED CSV의 'NaN' 행 — float()가 받아 버려 그대로면 lp.json에 맨 NaN이 실려 JSON이 깨진다(화면의 JSON.parse가 실패하고,
        커밋되면 다음 날 check 잡이 실패해 모든 갱신이 멈춘다). 받는 자리에서 버린다."""
        os.makedirs(self.reuse)
        w = W()
        for sid in lp.SERIES:
            text = fred_text(w[sid], sid)
            if sid == "LNS12300060":
                text = text.replace("2026-09-01,", "2026-09-01,NaN\n2026-09-01x,")    # 그 달 값이 NaN
            if sid == "JTSQUR":
                text += "2026-10-01,inf\n"
            with open(ff.cache_path(self.reuse, sid), "w", encoding="utf-8") as f:
                f.write(text)
            os.utime(ff.cache_path(self.reuse, sid), (NOW.timestamp(), NOW.timestamp()))
        self.assertTrue(math.isnan(dict(ff.parse_csv(open(ff.cache_path(self.reuse, "LNS12300060"), encoding="utf-8").read()))
                                   [D(2026, 9, 1)]))                                       # 거르지 않으면 NaN이 들어온다
        code, out = self.run_main(FakeFred({}))
        self.assertEqual(code, 0, out)
        with open(os.path.join(self.out, lp.FILE), encoding="utf-8") as f:
            raw = f.read()
        for tok in ("NaN", "Infinity"):
            self.assertNotIn(tok, raw)
        json.loads(raw, parse_constant=lp._strict)
        last = {s["series"]: s["last"] for s in self.read()["series"]}
        self.assertEqual(last["JTSQUR"], w["JTSQUR"][-1][0].isoformat())               # inf 행은 버렸다

    def test_a_nan_that_reaches_the_file_keeps_yesterday(self):
        os.makedirs(self.out)
        with open(os.path.join(self.out, lp.FILE), "w", encoding="utf-8") as f:
            f.write('{"schema":1,"yesterday":true}')
        real = lp.build
        def broken(*a, **kw):
            c = real(*a, **kw)
            c["current"]["legs"][0]["value"] = float("nan")
            return c
        with mock.patch.object(lp, "build", broken):
            code, out = self.run_main(FakeFred(W()))
        self.assertEqual(code, 0)
        self.assertTrue(self.read()["yesterday"])
        self.assertIn("계산 오류(ValueError)", out)
        with self.assertRaises(ValueError):
            lp.dumps({"x": float("inf")})
        with open(os.path.join(self.out, lp.FILE), "w", encoding="utf-8") as f:   # NaN이 든 옛 파일은 늘 다르다고 본다
            f.write('{"schema":1,"x":NaN}')
        self.assertTrue(lp.differs(self.out, {"schema": 1, "x": 0}))


# ---------- 워크플로 · README ----------

class StaticTest(unittest.TestCase):
    REPO = os.path.dirname(SCRIPTS)

    def read(self, *parts):
        with open(os.path.join(self.REPO, *parts), encoding="utf-8") as f:
            return f.read()

    def test_workflow_fetches_without_failing_the_run(self):
        wf = self.read(".github", "workflows", "daily.yml")
        self.assertIn("id: lp\n", wf, "daily.yml에 판단 격자 단계(id: lp) 없음")
        start = wf.rindex("      - name:", 0, wf.index("id: lp\n"))
        step = wf[start:wf.index("\n      - ", start + 1)]
        self.assertIn("name: 판단 격자 L × P 참고 자료 받기", step)
        self.assertIn("continue-on-error: true", step)
        self.assertIn("timeout-minutes: 2", step)
        self.assertIn("run: python scripts/lp_fetch.py", step)
        self.assertNotIn("if:", step)                                                    # 수집·판정이 실패한 날에도 돈다(스스로 받는다)
        self.assertLess(wf.index("id: fetch"), wf.index("id: lp\n"))                    # 수집·판정이 .work/fred/에 받아 둔 뒤
        self.assertLess(wf.index("id: oil"), wf.index("id: lp\n"))                      # 유가·에너지 다음
        self.assertLess(wf.index("id: lp\n"), wf.index("id: korea_start"))
        self.assertLess(wf.index("id: lp\n"), wf.index("공개 전 검사(새 산출물 포함)"))
        self.assertLess(wf.index("id: lp\n"), wf.index("git add data"))
        self.assertNotIn("lp", re.findall(r"[a-z_]+", wf[wf.index("\n  alert:"):]))    # 실패해도 알림을 띄우지 않는다
        self.assertIn("node --test scripts/test_lp_render.cjs", wf[wf.index("\n  check:"):wf.index("\n  update:")])
        self.assertEqual(os.path.relpath(lp.DEFAULT_REUSE, self.REPO), os.path.join(".work", "fred"))   # 규칙 점검의 원자료 자리

    def test_readme_counts_and_section(self):
        readme = self.read("README.md")
        m = re.search(r"\*\*아침 쪽 Python 테스트 (\d+)개 \+ node 테스트 (\d+)개\*\*\((.*?)\)와 \*\*저녁판", readme)
        py_part, node_part = m.group(3).split(" / node: ")
        mine = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()
        self.assertRegex(py_part, rf"(^| · )판단 격자 L × P 참고 {mine}( · |$)")
        cjs = len(re.findall(r"^test\(", self.read("scripts", "test_lp_render.cjs"), flags=re.M))
        self.assertRegex(node_part, rf"(^| · )판단 격자 L × P 그리기 {cjs}( · |$)")
        for cmd in ("python -X utf8 scripts/test_lp_fetch.py", "node --test scripts/test_lp_render.cjs",
                    "python -X utf8 scripts/lp_fetch.py --out"):
            self.assertIn(cmd, readme)
        self.assertIn("## 참고: 판단 격자 L × P", readme)
        sec = readme[readme.index("## 참고: 판단 격자 L × P"):]
        sec = sec[:sec.index("\n## ", 5)]
        for sid in lp.SOURCES:
            self.assertIn(f"`{sid}`", sec, sid)
        self.assertIn(lp.LABEL, sec)
        for (L, P), (name, _kind) in lp.CELLS.items():                                   # 칸 이름 16개 — 이름표 아래의 표
            self.assertIn(f"| {name} |", sec[sec.index(lp.LABEL):], f"{L} × {P}")
        for t in lp.EXCLUDED_TAGS:
            self.assertIn(f"'{t}'", sec, t)
        self.assertIn(f"문턱 {lp.FIXED} 고정", sec)
        self.assertIn("(#참고-판단-격자-l--p)", readme[:readme.index("## 공개 원칙")])          # 머리 표에서 이 절로

    def test_screen_script_keeps_the_same_grid_and_constants(self):
        """site/lp.js는 운영자 표(칸 이름 16개 · 띠 × 모멘텀 9칸)를 따로 적어 두고 다르면 파일을 그리지 않는다 — 이 파일과 같아야 한다.
        이 파일과 비공개 도구가 같은지는 비공개 쪽 짝 테스트가 본다(둘을 이으면 화면 = 비공개 도구)."""
        js = self.read("site", "lp.js")
        block = lambda name: js[js.index(f"const {name} = "):].split(";\n", 1)[0]
        cells = re.findall(r'"([^"|]+)\|([^"|]+)": \["([^"]+)", "(\w+)"\]', block("CELLS"))
        self.assertEqual({(L, P): (name, kind) for L, P, name, kind in cells}, lp.CELLS)
        self.assertEqual(len(cells), 16)
        pg = re.findall(r'"(\w+)\|(\w)": "([^"]+)"', block("P_GRID"))
        self.assertEqual({(b, m): P for b, m, P in pg}, lp.P_GRID)
        self.assertEqual(tuple(re.findall(r'"([^"]+)"', block("L_STATES").split("//")[0])), lp.GRID_L)
        self.assertEqual(tuple(re.findall(r'"([^"]+)"', block("P_STATES").split("//")[0])), lp.GRID_P)
        self.assertEqual(re.search(r'const LABEL = "([^"]+)";', js).group(1), lp.LABEL)
        self.assertEqual(tuple(re.findall(r'"([^"]+)"', block("EXCLUDED"))), lp.EXCLUDED_TAGS)
        keys = re.findall(r'"(\w+)"', block("CONSTANTS"))
        self.assertEqual(sorted(keys + ["layoff_hi", "layoff_lo"]), sorted(lp.CONSTANTS))  # 해고 몫 경계는 있으면 쓰고 없으면 기본값
        self.assertIn(f"const LAYOFF = {{ layoff_hi: {lp.LAYOFF_HI:g}, layoff_lo: {lp.LAYOFF_LO:g} }};", js)
        self.assertEqual(sorted(re.findall(r'"(\w+)"', block("SERIES"))), sorted(lp.SOURCES))
        heads = re.findall(r'head: "([^"]+)"', block("LEGS"))
        self.assertEqual(len(heads), len(lp.LEG_ORDER))
        for head, name in zip(heads, lp.LEG_ORDER):                                      # 다리는 차례와 이름 앞부분으로 읽는다
            self.assertTrue(name.startswith(head), (head, name))
        legs = block("LEGS")[block("LEGS").index("["):]                                  # 다리마다 견주는 문턱 = LEG_THS
        specs = []
        for head, body in re.findall(r'\{ head: "([^"]+)"([^}]*)\}', legs):
            m = re.search(r'ths: (?:c|\(\)) => \[([^\]]*)\]', body)
            specs.append((head, m.group(1) if m else ""))
        self.assertEqual(len(specs), len(lp.LEG_ORDER))

        def value(tok):
            tok = tok.strip()
            sign = -1 if tok.startswith("-") else 1
            tok = tok.lstrip("-")
            return sign * (lp.CONSTANTS[tok[2:]] if tok.startswith("c.") else float(tok))
        for (head, ths), name in zip(specs, lp.LEG_ORDER):
            got = sorted(value(t) for t in ths.split(",")) if ths else []
            self.assertEqual(got, sorted(lp.LEG_THS.get(name, ())), name)
        self.assertIn(f'const STALE_DAYS = 10;', js)


if __name__ == "__main__":
    unittest.main()
