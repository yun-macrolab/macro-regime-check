#!/usr/bin/env python3
"""연준 재무상태표 참고 자료(fedbs_fetch) 테스트 — 산식(손으로 셀 수 있는 합성 자료), 지준/GDP가 규칙 카드와 같은 값, 4주 평균의
정의, 분모 바뀜(새 분기·개정·같은 주), 4주/13주 나눔의 합·창·표시와 13주가 지준·재정 카드와 같은 값, 단기자금 5영업일(최대·이른
날·n/m·월말·15일), 주의 꼬리표와 FOMC 표(연준 인물 페이지의 회의 장부와 같다), 지준 관리 매입(RMP) 대조(연방 공휴일과 9영업일
창 규칙·경계일·소액 시험 운영과 매각 제외·끝나지 않은 창·MBS 상환 수요일·보이는 숫자끼리 뺄셈·뉴욕 연은 응답 꼴·요청 머리글과
예산)와 공식 계획(뉴욕 연은 Operational Details 페이지의 표 읽기 — 두 문장 꼴·형식 모름·깨진 날짜·태그·&nbsp;·차례·같은 기간·
옛 창·크기 상한·표 없음, 공식 기간으로 잡는 대조 창과 규칙으로 잡는 창, 요청 꼴·예산·캐시), 칸마다 실패·직전 값 이어 싣기, 이용
조건 목록, 문구 원칙(판정 낱말 없음), 화면·워크플로 연결, 정책 사실 칸의 원문 인용.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — FRED는 가짜 loader 또는 합성 캐시(--offline), 뉴욕 연은 국채 운영 결과·공식 계획 페이지는 가짜 ops_load·
plan_load·가짜 opener. 숫자와 계획 페이지 HTML은 모두 지어낸 것이다(실자료 숫자를 넣지 않는다).
"""
import os, sys, io, re, json, datetime, tempfile, unittest, shutil, contextlib
from unittest import mock

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import fedbs_fetch as fb
import liquidity_fetch as liq
import ai_invest_fetch as ai
import credit_fetch as cf
import regime_check as rc
import regime_rules as rr
import render_public as rp
from test_render_public import FORBIDDEN_TEXT
from test_people_site import load_data as load_people

REPO = os.path.dirname(SCRIPTS)
D = datetime.date
TD = datetime.timedelta
NOW = datetime.datetime(2026, 10, 30, 22, 30, tzinfo=datetime.timezone.utc)
# 판정·방향 낱말 — 공개 카드 어디에도 없어야 한다(FORBIDDEN_TEXT에 더해)
VERDICT = ("판정", "충족", "신호", "경보", "전망", "매수", "매도", "⚠", "●", "○", "강세", "약세", "호재", "악재", "우려", "부담",
           "상승", "하락", "→", "긴축", "완화", "위험", "문턱", "임계", "발동")
# 카드 주제 낱말 — FORBIDDEN_TEXT의 '재정'은 이 꼴로만 허용한다(앞 카드 이름 '지준·재정')
TOPIC = ("지준·재정",)

# 수요일 수준(백만 달러): 07-29 이하 = 기준, 07-29 뒤 ~ 09-30 = 중간, 09-30 뒤 = 마지막
# → 13주(07-29 → 10-28)·4주(09-30 분기말 → 10-28) 변화를 손으로 셀 수 있다
LEVELS = {"WRBWFRBL": (3_000_000, 2_950_000, 2_900_000),     # 지준 −100 / −50
          "WDTGAL": (800_000, 850_000, 880_000),             # TGA +80 / +30 → 지준 쪽 −80 / −30
          "WLRRAOL": (10_000, 5_000, 2_000),                 # 익일물 역레포 −8 / −3 → +8 / +3
          "WLRRAFOIAL": (300_000, 310_000, 300_000),         # 해외 공적 0 / −10 → 0 / +10
          "WSHOBL": (200_000, 230_000, 260_000),             # 단기채 +60 / +30
          "WSHONBNL": (3_600_000, 3_598_000, 3_597_000),     # 이표채 −3 / −1
          "WSHOMCB": (2_000_000, 1_970_000, 1_950_000),      # MBS −50 / −20
          "WCICL": (2_400_000, 2_410_000, 2_415_000)}        # 현금 +15 / +5 → −15 / −5
# 그 밖: 13주 −100 − (−80 + 8 + 0 + 60 − 3 − 50 − 15) = −20 · 4주 −50 − (−30 + 3 + 10 + 30 − 1 − 20 − 5) = −37
WANT13 = {"res": -100, "tga": -80, "onrrp": 8, "pool": 0, "bills": 60, "coupons": -3, "mbs": -50, "cur": -15, "other": -20}
WANT4 = {"res": -50, "tga": -30, "onrrp": 3, "pool": 10, "bills": 30, "coupons": -1, "mbs": -20, "cur": -5, "other": -37}
WED = D(2026, 10, 28)


def weds(start, end):
    out, d = [], start
    while d <= end:
        out.append(d)
        d += TD(days=7)
    return out


def bdays(start, end):
    out, d = [], start
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += TD(days=1)
    return out


def level(sid, d):
    a, b, c = LEVELS[sid]
    return a if d <= D(2026, 7, 29) else b if d <= D(2026, 9, 30) else c


def world(last_wed=WED, last_day=D(2026, 10, 30)):
    """주 평균 지준 2,800bn(마지막 네 주 3,100·3,000·2,900·2,800 → 4주 평균 2,950) ÷ GDP 2026Q3 32,000 = 8.75%(하한 9.0 대비
    −0.25%p ≈ −80bn · 4주 평균 9.21875%). 단기자금: SOFR − IORB 10-26~10-30 = 0 · +2 · 0 · 0 · +8(10-30 월말) → 최대 +8 · 2/5일,
    상시 레포 10-30에 12.5bn, 익일물 역레포 마지막 3.2bn."""
    W = weds(D(2025, 1, 1), last_wed)
    S = {"WRESBAL": [(d, 3_000_000.0) for d in W[:-4]]
         + list(zip(W[-4:], (3_100_000.0, 3_000_000.0, 2_900_000.0, 2_800_000.0))),
         "GDP": [(D(2026, 1, 1), 29_000.0), (D(2026, 4, 1), 30_000.0), (D(2026, 7, 1), 32_000.0)]}
    for sid in LEVELS:
        S[sid] = [(d, float(level(sid, d))) for d in W]
    B = bdays(D(2026, 9, 1), last_day)
    S["IORB"] = [(D(2026, 9, 1) + TD(days=i), 3.90) for i in range((last_day - D(2026, 9, 1)).days + 1)]
    S["SOFR"] = [(d, {D(2026, 10, 30): 3.98, D(2026, 10, 27): 3.92}.get(d, 3.90)) for d in B]
    S["RPONTTLD"] = [(d, 12.5 if d == D(2026, 10, 30) else 0.0) for d in B]
    S["RRPONTSYD"] = [(d, 3.2 if d == last_day else 1.0) for d in B]
    return S


class FakeFred:
    def __init__(self, data, fail=(), cache=()):
        self.data, self.fail, self.cache, self.calls = data, set(fail), set(cache), []

    def __call__(self, sid, cache_dir, offline=False, timeout=None):
        self.calls.append((sid, timeout))
        if sid in self.fail:
            raise RuntimeError(f"{sid}: 원문 사유 https://bad.invalid/xyz-77")
        return list(self.data[sid]), ("cache" if sid in self.cache else "net")


B = 1_000_000_000                                                                # 달러 → 십억 달러


def op(day, amt, way="P", status="Results", oid=None, kind="Outright Bill Purchase"):
    """뉴욕 연은 국채 운영 결과 한 줄(지어낸 것) — 금액은 십억 달러로 받아 달러 글자로."""
    return {"operationId": oid or f"OP {day} {kind} {amt}", "auctionStatus": status, "operationType": kind,
            "operationDate": day, "settlementDate": day, "operationDirection": way,
            "totalParAmtSubmitted": str(int(round(amt * B * 3))), "totalParAmtAccepted": str(int(round(amt * B))), "note": ""}


# 2026년 창(9영업일: 07-13 · 08-13 · 09-14 노동절 · 10-14 콜럼버스 · 11-13 재향군인)과 지어낸 운영 — NOW(10-30) 기준 끝난 창
# 07·08·09월과 끝나지 않은 10월 창
OPS_ROWS = [op("2026-07-13", 9.0),                                               # 7월 9영업일 그날 — 6월 창(싣지 않는다)
            op("2026-07-14", 5.0), op("2026-07-28", 4.0), op("2026-08-13", 3.0),  # 7월 창 12.0(끝 날 08-13 포함)
            op("2026-08-14", 6.0), op("2026-08-20", 0.05, kind="Outright FRN Purchase"),   # 8월 창: 소액 시험 운영은 뺀다
            op("2026-08-25", 0.025, "S", kind="Outright Coupon Sale"), op("2026-09-14", 2.0),   # 매각은 세지 않는다 → 8.0
            op("2026-09-15", 7.0), op("2026-09-30", 1.5, kind="Outright Coupon Purchase"), op("2026-10-14", 2.5),   # 9월 11.0
            op("2026-10-15", 3.0), op("2026-10-29", 1.2),                         # 10월 창(끝나지 않음) 4.2
            op("2026-10-31", 9.9),                                                # 오늘 뒤 — 빼고 센다
            op("2026-09-16", 99.0, status="Announcement"),                        # 결과가 아닌 줄은 보지 않는다
            {**op("2026-09-15", 7.0), "note": "같은 operationId — 한 번만"}]
OPS_BLOB = json.dumps({"treasury": {"auctions": OPS_ROWS}}).encode()
# 실행 테스트(MainTest)의 기본 응답 — 오늘 뒤 운영(10-31)을 뺀 것: 다음 날 실행에도 같은 숫자여야 하는 테스트가 있다
MAIN_BLOB = json.dumps({"treasury": {"auctions": [r for r in OPS_ROWS if r["operationDate"] <= "2026-10-30"]}}).encode()


def mbs_series(drops=None, start=D(2026, 1, 7), end=D(2026, 10, 28)):
    """수요일 WSHOMCB(백만 달러) — drops {수요일: 그 주에 줄어든 백만 달러}. 기본: 7월 10.5bn(07-22 3.0 + 07-29 7.5) ·
    8월 8.7bn(08-19 2.0 + 08-26 6.7) · 9월 10.9bn(09-23 1.0 + 09-30 9.9) · 10월 8.0bn(10-28)."""
    drops = {D(2026, 7, 22): 3000, D(2026, 7, 29): 7500, D(2026, 8, 19): 2000, D(2026, 8, 26): 6700,
             D(2026, 9, 23): 1000, D(2026, 9, 30): 9900, D(2026, 10, 28): 8000} if drops is None else drops
    lvl, out = 2_000_000.0, []
    for d in weds(start, end):
        lvl -= drops.get(d, 0)
        out.append((d, lvl))
    return out


def rmp_world():
    S = world()
    S["WSHOMCB"] = mbs_series()
    return S


class FakeOps:
    """가짜 뉴욕 연은 요청(fedbs_fetch.main의 ops_load) — 부른 주소를 적고, 정해 둔 원문을 돌려주거나 실패한다."""
    def __init__(self, blob=None, fail=False):
        self.blob, self.fail, self.calls = MAIN_BLOB if blob is None else blob, fail, []

    def __call__(self, url, deadline):
        self.calls.append(url)
        if self.fail:
            raise OSError("원문 사유 https://bad.invalid/xyz-77")
        return self.blob


def plan_text(reinvest, rmp=None, verb="conduct", additional=True):
    """지어낸 계획 문장 — 정해 둔 꼴(rmp None이면 'no reserve management purchases')."""
    tail = ("no reserve management purchases" if rmp is None else
            ("an additional " if additional else "") + f"approximately ${rmp} billion in reserve management purchases")
    return (f"The Desk plans to {verb} approximately ${reinvest} billion in reinvestment purchases and {tail} over the "
            "noted monthly period.")


def plan_html(rows, head=("Period", "Planned Operation Amount", "Tentative Schedule", "Results", "Next Schedule Release"),
              before="", after=""):
    """지어낸 공식 계획 페이지 — rows [(기간 칸 HTML, 문장 칸 HTML)]. 페이지처럼 script 안의 '<table>' 글과 머리 행이 있다."""
    body = "".join(f"\n\t <tr>\n  <td>{p}</td>\n  <td>{t}</td>\n  <td><a class=\"pdf\" href=\"/x.pdf\">Schedule</a></td>"
                   "\n  <td></td>\n  <td>&nbsp;</td>\n </tr>" for p, t in rows)
    return ("<html><head><script>var table = $('<table></table>');</script></head><body>" + before +
            "<table class=\"nyfed-table\" id=\"pagination-table\"><thead><tr>" + "".join(f"<th>{h}</th>" for h in head) +
            "</tr></thead><tbody id=\"data-container\">" + body + "</tbody></table>" + after + "</body></html>").encode()


# 지어낸 계획(숫자는 실자료가 아니다) — 기간은 9영업일 규칙과 같다(MainTest의 대조 숫자가 규칙으로 셈한 것과 같게)
PLAN_ROWS = [("6/12/2026 -<br>7/13/2026", plan_text("10.1", "3")),
             ("7/14/2026 -<br>8/13/2026", plan_text("11.1", "5")),
             ("8/14/2026 -<br>9/14/2026", plan_text("12.2")),
             ("9/15/2026 -<br>10/14/2026", plan_text("13.3", "2.5", additional=False)),
             ("10/15/2026 -<br>11/13/2026", plan_text("9.0"))]
PLAN_BLOB = plan_html(list(reversed(PLAN_ROWS)))                                  # 페이지처럼 새 창이 위


class FakePlan:
    """가짜 뉴욕 연은 공식 계획 요청(fedbs_fetch.main의 plan_load) — 부른 주소를 적고, 정해 둔 원문을 돌려주거나 실패한다."""
    def __init__(self, blob=None, fail=False):
        self.blob, self.fail, self.calls = PLAN_BLOB if blob is None else blob, fail, []

    def __call__(self, url, deadline):
        self.calls.append(url)
        if self.fail:
            raise OSError("원문 사유 https://bad.invalid/xyz-77")
        return self.blob


def calc(key, S=None, today=NOW.date()):
    if key == "rmp":
        return fb.calc_rmp(rmp_world() if S is None else S, today, fb.parse_ops(OPS_BLOB))
    return fb.BY_KEY[key]["calc"](world() if S is None else S, today)


def dec_numbers(line):
    """나눔 줄의 보이는 정수 — {창: [지준, TGA, 익일물, 해외, 단기채, 이표채, MBS, 현금, 그 밖]} ('—'는 None)."""
    assert line.endswith(" " + fb.SIGN_NOTE), line
    body = line[:-len(fb.SIGN_NOTE) - 1]
    pairs = re.findall(r"(—|[+-]?[\d,]+)/(—|[+-]?[\d,]+)", body)
    num = lambda x: None if x == "—" else int(x.replace(",", ""))
    return {"4": [num(a) for a, _ in pairs], "13": [num(b) for _, b in pairs]}


class ArithmeticTest(unittest.TestCase):
    def test_reserves_values_and_line(self):
        c = calc("reserves")
        v = c["values"]
        self.assertEqual(c["date"], "2026-10-28")
        self.assertEqual((v["level"], v["gdp_quarter"], v["gdp_bn"], v["low"]), (2800.0, "2026-07-01", 32000.0, 9.0))
        self.assertAlmostEqual(v["value"], 8.75)
        self.assertAlmostEqual(v["gap_pp"], -0.25)
        self.assertAlmostEqual(v["gap_bn"], -80.0)
        self.assertAlmostEqual(v["avg4"], 2950 / 32000 * 100, places=6)
        self.assertEqual(v["avg4_from"], "2026-10-07")
        self.assertEqual((v["base_quarter"], v["base_bn"], v["denom_pp"]), (None, None, None))
        self.assertEqual((v["first_quarter"], v["first_bn"]), ("2026-07-01", 32000.0))   # 이 주를 처음 실을 때의 GDP
        line, extra = fb.texts("reserves", v, c["date"])
        self.assertEqual(line, "지준 2,800.0bn (주 평균) = 명목 GDP의 8.75% (2026Q3) · 규칙 하한 9.0% 대비 -0.25%p ≈ -80.0bn · "
                               "4주 평균 9.22%")
        self.assertIn("2026Q3 32,000bn", extra[0])
        self.assertTrue(extra[1].startswith(fb.AVG4_DEF + " — 2026-10-07~2026-10-28 네 주"), extra[1])

    def test_reserves_match_the_rule_card(self):
        for S in (world(), {"WRESBAL": [(d, 2_950_000.0 + 7 * i) for i, d in enumerate(weds(D(2026, 1, 7), D(2026, 10, 21)))],
                            "GDP": [(D(2026, 1, 1), 31_234.5), (D(2026, 4, 1), 32_100.25)]}):
            ind, _, _ = rc.compute(S, D(2026, 10, 30))
            want = ind["reserves_gdp"]
            v = fb.calc_reserves(S, D(2026, 10, 30))["values"]
            rule = liq.calc_rule(S)["values"]
            self.assertAlmostEqual(v["value"], want["value"], places=6)
            self.assertEqual(v["gdp_quarter"], want["gdp_quarter"])
            self.assertEqual(fb.calc_reserves(S, D(2026, 10, 30))["date"], want["asof"])
            self.assertEqual(v["low"], rr.TH["reserves_gdp_low"])
            self.assertAlmostEqual(v["gap_pp"], rule["gap_pp"], places=4)              # 지준·재정 카드의 하한 대비와 같은 값
            self.assertAlmostEqual(v["gap_bn"], rule["gap_bn"], places=4)
            self.assertEqual(f"{v['value']:.2f}", f"{rule['value']:.2f}")            # 화면의 같은 숫자

    def test_four_week_average_needs_four_consecutive_weeks(self):
        S = world()
        S["WRESBAL"] = S["WRESBAL"][:-3] + S["WRESBAL"][-2:]                           # 10-14 주가 빠졌다
        v = fb.calc_reserves(S, NOW.date())["values"]
        self.assertEqual((v["avg4"], v["avg4_from"]), (None, None))
        line, extra = fb.texts("reserves", v, "2026-10-28")
        self.assertTrue(line.endswith("4주 평균 —"), line)
        self.assertIn("최근 네 주가 이어지지 않아", extra[1])
        S["WRESBAL"] = world()["WRESBAL"][-3:]                                         # 세 주뿐
        self.assertIsNone(fb.calc_reserves(S, NOW.date())["values"]["avg4"])

    def test_four_week_average_divides_by_the_latest_gdp(self):
        # 정의는 하나 — (최근 4주 지준 평균) ÷ 최신 GDP. 각 주를 그 주의 GDP로 나눈 평균이 아니다
        S = world()
        S["GDP"] = S["GDP"] + [(D(2026, 10, 1), 40_000.0)]                             # 마지막 주 안에 새 분기가 들어와도
        v = fb.calc_reserves(S, NOW.date())["values"]
        self.assertAlmostEqual(v["avg4"], 2950 / 40000 * 100, places=6)
        self.assertEqual(v["gdp_quarter"], "2026-10-01")

    def test_chart_lines_are_52_weeks_and_the_floor_uses_the_latest_gdp(self):
        c = calc("reserves")
        res, low = c["lines"]["res"], c["lines"]["low"]
        self.assertEqual(len(res), fb.CHART_WEEKS)
        self.assertEqual([p[0] for p in res], [p[0] for p in low])
        self.assertEqual(res[-1], ["2026-10-28", 2800.0])
        self.assertEqual({p[1] for p in low}, {9.0 / 100 * 32000})                     # 2,880bn — 지난 주들도 지금 GDP로
        self.assertEqual(res[0][0], (WED - TD(weeks=51)).isoformat())

    @staticmethod
    def shown_with(core, q, g, date="2026-10-21"):
        """직전 파일의 칸 — 그 주를 GDP (q, g)로 처음 실었다."""
        return {"date": date, "values": dict(core["values"], gdp_quarter=q, gdp_bn=g, first_quarter=q, first_bn=g)}

    def test_denominator_change_new_quarter(self):
        core = calc("reserves")
        old = self.shown_with(core, "2026-04-01", 30000.0)
        v = fb.with_base(core, old)["values"]
        self.assertEqual((v["base_quarter"], v["base_bn"]), ("2026-04-01", 30000.0))
        self.assertAlmostEqual(v["denom_pp"], 2800 / 32000 * 100 - 2800 / 30000 * 100, places=6)
        line, extra = fb.texts("reserves", v, "2026-10-28")
        self.assertTrue(line.endswith(" · 분모 바뀜 -0.58%p (GDP 2026Q2에서 2026Q3로)"), line)
        self.assertIn("직전 주를 처음 실을 때의 GDP(2026Q2 30,000bn)", extra[-1])
        self.assertEqual((v["first_quarter"], v["first_bn"]), ("2026-07-01", 32000.0))   # 이번 주는 이번 GDP로 처음 싣는다

    def test_denominator_change_same_quarter_revision(self):
        core = calc("reserves")
        old = self.shown_with(core, "2026-07-01", 31000.0)
        v = fb.with_base(core, old)["values"]
        self.assertAlmostEqual(v["denom_pp"], 2800 / 32000 * 100 - 2800 / 31000 * 100, places=6)
        self.assertTrue(fb.texts("reserves", v, "2026-10-28")[0].endswith(" · 분모 바뀜 -0.28%p (2026Q3 개정)"))

    def test_denominator_same_gdp_or_first_week_is_quiet(self):
        core = calc("reserves")
        v = fb.with_base(core, {"date": "2026-10-21", "values": dict(core["values"])})["values"]
        self.assertEqual((v["base_quarter"], v["base_bn"], v["denom_pp"]), ("2026-07-01", 32000.0, None))   # 기준은 남긴다
        self.assertNotIn("분모 바뀜", fb.texts("reserves", v, "2026-10-28")[0])
        v = fb.with_base(core, None)["values"]                                          # 처음 싣는 주 — 견줄 것이 없다
        self.assertEqual((v["base_quarter"], v["denom_pp"]), (None, None))

    def test_denominator_same_week_keeps_its_base(self):
        core = calc("reserves")
        shown = fb.with_base(core, self.shown_with(core, "2026-04-01", 30000.0))
        again = fb.with_base(core, shown)["values"]                                    # 같은 주를 다음 날 다시
        self.assertEqual((again["base_quarter"], again["base_bn"]), ("2026-04-01", 30000.0))
        self.assertEqual(again["denom_pp"], shown["values"]["denom_pp"])
        first = fb.with_base(core, None)                                                # 같은 주, 기준 없음 → 계속 없음
        self.assertIsNone(fb.with_base(core, first)["values"]["denom_pp"])

    def test_denominator_compares_with_the_gdp_the_last_week_was_first_shown_with(self):
        # 검토 F1(site): 같은 주 안에서 GDP만 바뀌면(H.4.1이 하루 늦은 주의 GDP 발표 등) 다음 주가 그 바뀜을 싣는다 — 기준은 직전
        # 주를 처음 실을 때의 GDP(비공개 fed_bs가 메일로 실은 주의 GDP와 견주는 것과 같은 뜻)
        S = world(last_wed=D(2026, 10, 21), last_day=D(2026, 10, 23))
        S["GDP"] = S["GDP"][:-1]                                                        # 10-21 주를 2026Q2 GDP 30,000으로
        day1 = fb.with_base(fb.calc_reserves(S, D(2026, 10, 22)), None)
        S["GDP"] = world()["GDP"]                                                       # 같은 주, 다음 날 GDP 2026Q3 32,000
        day2 = fb.with_base(fb.calc_reserves(S, D(2026, 10, 23)), day1)["values"]
        self.assertEqual((day2["gdp_quarter"], day2["first_quarter"], day2["first_bn"]), ("2026-07-01", "2026-04-01", 30000.0))
        self.assertIsNone(day2["denom_pp"])                                             # 처음 실은 주라 그 주엔 견줄 기준이 없다
        nxt = fb.with_base(calc("reserves"), {"date": "2026-10-21", "values": day2})["values"]   # 10-28 주
        self.assertEqual((nxt["base_quarter"], nxt["base_bn"]), ("2026-04-01", 30000.0))
        self.assertAlmostEqual(nxt["denom_pp"], 2800 / 32000 * 100 - 2800 / 30000 * 100, places=6)
        self.assertEqual((nxt["first_quarter"], nxt["first_bn"]), ("2026-07-01", 32000.0))

    def test_decomposition_adds_up(self):
        c = calc("dec")
        v = c["values"]
        self.assertEqual((c["date"], v["to"], v["from4"], v["from13"]), ("2026-10-28", "2026-10-28", "2026-09-30", "2026-07-29"))
        for w, want in (("4", WANT4), ("13", WANT13)):
            for k, x in want.items():
                self.assertAlmostEqual(v[f"{k}{w}"], x, msg=f"{k}{w}")
            self.assertAlmostEqual(sum(v[f"{k}{w}"] for k in fb.PARTS), v[f"res{w}"])
        line, extra = fb.texts("dec", v, c["date"])
        self.assertEqual(line, "지준 변화 4주/13주 -50/-100bn = 재무부 현금(TGA) -30/-80 · 익일물 역레포 +3/+8 · 해외 공적 역레포 "
                               "+10/0 · 연준 단기채 +30/+60 · 연준 이표채 -1/-3 · 연준 MBS -20/-50 · 현금 통화 -5/-15 · "
                               "그 밖 -37/-20 (부호는 지준 쪽)")
        self.assertEqual(line.count(fb.SIGN_NOTE), 1)
        self.assertTrue(extra[0].startswith("창: 4주 2026-09-30(분기말)~2026-10-28 · 13주 2026-07-29~2026-10-28 — "), extra[0])
        self.assertTrue(extra[1].startswith("4주 창은 분기말(2026-09-30)에서 출발해"), extra[1])

    def test_thirteen_weeks_equal_the_liquidity_card(self):
        S = world()
        S["WLRRAL"] = [(d, a + b) for (d, a), (_, b) in zip(S["WLRRAOL"], S["WLRRAFOIAL"])]
        lq = liq.calc_reserves(S)
        v = fb.calc_dec(S, NOW.date())["values"]
        self.assertEqual((lq["date"], lq["values"]["from"]), (v["to"], v["from13"]))
        for mine, theirs in ((v["res13"], "res"), (v["tga13"], "tga"), (v["bills13"], "bills"), (v["coupons13"], "coupons"),
                             (v["onrrp13"] + v["pool13"], "rrp"), (v["mbs13"] + v["cur13"] + v["other13"], "other")):
            self.assertAlmostEqual(mine, lq["values"][theirs], places=6, msg=theirs)

    def test_one_window_can_be_missing(self):
        S = world()
        for sid in ("WDTGAL",):                                                         # 09-23·09-30 두 주가 빠졌다 → 4주 출발이 없다
            S[sid] = [p for p in S[sid] if p[0] not in (D(2026, 9, 23), D(2026, 9, 30))]
        v = fb.calc_dec(S, NOW.date())["values"]
        self.assertIsNone(v["from4"])
        self.assertTrue(all(v[f"{k}4"] is None for k in ("res", *fb.PARTS)))
        self.assertEqual(v["from13"], "2026-07-29")
        line, extra = fb.texts("dec", v, v["to"])
        self.assertEqual(dec_numbers(line)["4"], [None] * 9)
        self.assertEqual(dec_numbers(line)["13"], [WANT13[k] for k in ("res", *fb.PARTS)])
        self.assertIn("4주 —", extra[0])
        self.assertTrue(fb._dec_ok(v))
        S = {sid: [(WED, 1.0)] for sid in fb.BS.values()}                               # 창이 하나도 없다
        with self.assertRaises(fb.ItemError) as e:
            fb.calc_dec(S, NOW.date())
        self.assertEqual(e.exception.code, "format")

    def test_window_needs_an_observation_near_the_start(self):
        for gap, ok in ((6, True), (7, False)):
            old = WED - TD(days=91 + gap)
            S = {sid: [(old, 1000.0), (WED, 2000.0)] for sid in fb.BS.values()}
            r = fb.decompose(S, 91)
            self.assertEqual(r is not None, ok, gap)

    def test_last_common_wednesday(self):
        S = world()
        S["WCICL"] = S["WCICL"][:-1]                                                    # 현금 통화가 한 주 늦다
        v = fb.calc_dec(S, NOW.date())["values"]
        self.assertEqual((v["to"], v["from4"], v["from13"]), ("2026-10-21", "2026-09-23", "2026-07-22"))

    def test_shown_numbers_add_up_even_when_each_rounds_away(self):
        base = calc("dec")["values"]
        cases = [dict(res4=-0.6, tga4=0.4, onrrp4=0.4, pool4=0.4, bills4=0.4, coupons4=0.4, mbs4=0.4, cur4=0.4, other4=-3.4),
                 dict(res4=10.5, tga4=2.5, onrrp4=3.5, pool4=-0.5, bills4=1.5, coupons4=0.5, mbs4=0.5, cur4=0.5, other4=1.5),
                 dict(res4=1234.4, tga4=-1100.6, onrrp4=0.49, pool4=2000.51, bills4=-0.5, coupons4=0.5, mbs4=-1.5, cur4=0.0,
                      other4=335.44)]
        for case in cases:
            v = dict(base, **case)
            nums = dec_numbers(fb.texts("dec", v, "2026-10-28")[0])["4"]
            self.assertEqual(sum(nums[1:]), nums[0], (case, nums))
            self.assertEqual(nums[0], round(case["res4"]))
        self.assertIn("지준 변화 4주/13주 +1,234/-100bn", fb.texts("dec", dict(base, **cases[2]), "2026-10-28")[0])

    def test_level_and_daily_tags(self):
        self.assertEqual([fb.level_tag(D(2026, m, d)) for m, d in ((9, 30), (10, 31), (10, 15), (10, 14), (12, 31), (11, 30))],
                         ["분기말", "월말", "15일", "", "분기말", "월말"])
        days = bdays(D(2026, 11, 2), D(2026, 12, 3))                                    # 11-15는 일요일 → 11-16(월)이 15일 표시
        self.assertEqual(fb.cal_tag(D(2026, 11, 16), days), "15일")
        self.assertEqual(fb.cal_tag(D(2026, 11, 17), days), "")
        self.assertEqual(fb.cal_tag(D(2026, 11, 30), days), "월말")                      # 다음 관측이 다음 달
        self.assertEqual(fb.cal_tag(D(2026, 10, 30), bdays(D(2026, 10, 1), D(2026, 10, 30))), "월말")   # 마지막 관측(금), 뒤 평일 없음
        self.assertEqual(fb.cal_tag(D(2026, 10, 29), bdays(D(2026, 10, 1), D(2026, 10, 29))), "")    # 마지막 관측이지만 30일(금)이 남음

    def test_short_term_funding(self):
        v = calc("spread")["values"]
        self.assertEqual(v, {"from": "2026-10-26", "max_bp": 8.0, "max_date": "2026-10-30", "max_tag": "월말", "pos": 2,
                             "n": 5, "days": 5})
        self.assertEqual(fb.texts("spread", v, "2026-10-30")[0],
                         "SOFR − IORB 최대 +8bp (2026-10-30 월말) · 0보다 큰 날 2/5일 (2026-10-26~2026-10-30)")
        s = calc("srf")
        self.assertEqual(s["values"], {"from": "2026-10-26", "max_bn": 12.5, "max_date": "2026-10-30", "max_tag": "월말"})
        self.assertEqual(fb.texts("srf", s["values"], s["date"])[0], "상시 레포 이용 최대 12.5bn (2026-10-30 월말) · 2026-10-26~2026-10-30")
        r = calc("rrp")
        self.assertEqual((r["date"], r["values"]), ("2026-10-30", {"bn": 3.2, "tag": "월말"}))
        self.assertEqual(fb.texts("rrp", r["values"], r["date"])[0], "익일물 역레포 3.2bn (2026-10-30 월말)")

    def test_ties_take_the_earliest_day_and_far_iorb_is_left_out(self):
        S = world()
        S["SOFR"] = [(d, 3.95 if d in (D(2026, 10, 27), D(2026, 10, 30)) else 3.90) for d, _ in S["SOFR"]]
        S["RPONTTLD"] = [(d, 0.0) for d, _ in S["RPONTTLD"]]
        self.assertEqual(calc("spread", S)["values"]["max_date"], "2026-10-27")         # 같은 최대면 이른 날(월말이 가져가지 않게)
        self.assertEqual(calc("srf", S)["values"]["max_date"], "2026-10-26")
        S["IORB"] = [p for p in S["IORB"] if p[0] <= D(2026, 10, 25)]                   # IORB가 10-25에서 끊겼다
        v = calc("spread", S)["values"]
        self.assertEqual((v["n"], v["days"]), (3, 5))                                   # 10-26·27·28(3일 안)만
        line, extra = fb.texts("spread", v, "2026-10-30")
        self.assertIn("0보다 큰 날 1/3일", line)
        self.assertIn("5일 중 3일만", extra[-1])
        S["IORB"] = [p for p in S["IORB"] if p[0] <= D(2026, 10, 10)]
        with self.assertRaises(fb.ItemError):
            calc("spread", S)

    def test_week_tags_and_next_fomc(self):
        v = calc("week")["values"]
        self.assertEqual(v, {"from": "2026-10-22", "d15": False, "month_end": False, "fomc": ["2026-10-28"],
                             "next_fomc": "2026-12-09", "next_tentative": False})
        line, extra = fb.texts("week", v, "2026-10-28")
        self.assertEqual(line, "이 주(2026-10-22~2026-10-28) FOMC 뒤 첫 H.4.1(2026-10-28 결정) · 다음 FOMC 2026-12-09")
        self.assertTrue(extra[0].startswith("FOMC 결정일(수)이 이 주의 마지막 날이라"), extra[0])
        S = world(last_wed=D(2026, 9, 30))                                               # 09-24~09-30: 월말(분기말) 포함, FOMC 없음
        v = fb.calc_week(S, D(2026, 10, 1))["values"]
        self.assertEqual((v["month_end"], v["d15"], v["fomc"], v["next_fomc"]), (True, False, [], "2026-10-28"))
        self.assertTrue(fb.texts("week", v, "2026-09-30")[0].startswith("이 주(2026-09-24~2026-09-30) 월말 포함 · 다음 FOMC"))
        v = fb.calc_week(world(last_wed=D(2026, 9, 16)), D(2026, 9, 16))["values"]      # 09-10~09-16: 15일 + 결정일 09-16
        self.assertEqual((v["d15"], v["fomc"], v["next_fomc"]), (True, ["2026-09-16"], "2026-09-16"))   # 결정일 당일은 '다음'
        self.assertIn("15일 포함 · FOMC 뒤 첫 H.4.1(2026-09-16 결정)", fb.texts("week", v, "2026-09-16")[0])
        v = fb.calc_week(world(last_wed=D(2026, 10, 21)), D(2026, 10, 21))["values"]
        self.assertTrue(fb.texts("week", v, "2026-10-21")[0].startswith("이 주(2026-10-15~2026-10-21) 15일 포함 · 다음 FOMC"))
        v = fb.calc_week(world(), D(2026, 12, 10))["values"]                             # 2027년은 연준 일정 페이지의 잠정 일정
        self.assertEqual((v["next_fomc"], v["next_tentative"]), ("2027-01-27", True))
        self.assertTrue(fb.texts("week", v, "2026-10-28")[0].endswith("다음 FOMC 2027-01-27(잠정)"))
        v = fb.calc_week(world(), D(2027, 3, 18))["values"]                              # 검토 F1: 3월 뒤에도 4월 회의가 있다
        self.assertEqual((v["next_fomc"], v["next_tentative"]), ("2027-04-28", True))
        S = world()
        S["WRESBAL"] = [(D(2027, 4, 21), 3_000_000.0), (D(2027, 4, 28), 3_000_000.0)]     # 04-22~04-28 주 = 04-28 결정 주
        v = fb.calc_week(S, D(2027, 4, 30))["values"]
        self.assertEqual((v["fomc"], v["next_fomc"]), (["2027-04-28"], "2027-06-09"))
        self.assertIn("FOMC 뒤 첫 H.4.1(2027-04-28 결정)", fb.texts("week", v, "2027-04-28")[0])
        v = fb.calc_week(world(), D(2027, 12, 9))["values"]                              # 표 밖(2027-12-08 뒤)
        self.assertEqual((v["next_fomc"], v["next_tentative"]), (None, False))
        self.assertTrue(fb.texts("week", v, "2026-10-28")[0].endswith("다음 FOMC 미기재"))
        v = calc("week", world(last_wed=D(2026, 10, 7)), D(2026, 10, 9))["values"]       # 15일·월말·FOMC 없음
        self.assertIn("이 주(2026-10-01~2026-10-07) 15일·월말·FOMC 없음", fb.texts("week", v, "2026-10-07")[0])

    def test_next_fomc_is_the_first_meeting_without_a_statement_yet(self):
        # 검토 F2: 예약 실행(UTC 22:17)은 결정일에도 성명(14:00 미 동부) 뒤다 — 그날 회의는 '다음'이 아니다
        utc = datetime.timezone.utc
        S = world(last_wed=D(2026, 12, 2), last_day=D(2026, 12, 4))
        at = lambda *a: fb.calc_week(S, D(*a[:3]), datetime.datetime(*a, tzinfo=utc))["values"]["next_fomc"]
        self.assertEqual(at(2026, 12, 9, 22, 17), "2027-01-27")                         # 결정일 저녁 예약 실행 — 다음 회의
        self.assertEqual(at(2026, 12, 9, 15, 0), "2026-12-09")                          # 성명 전(10:00 EST) — 그날 회의
        self.assertEqual(at(2026, 12, 9, 18, 59), "2026-12-09")                         # 겨울(EST)엔 19:00 UTC
        self.assertEqual(at(2026, 12, 9, 19, 0), "2027-01-27")
        self.assertEqual(at(2026, 10, 28, 17, 59), "2026-10-28")                        # 서머타임(EDT)엔 18:00 UTC
        self.assertEqual(at(2026, 10, 28, 18, 0), "2026-12-09")
        self.assertEqual(at(2026, 12, 8, 22, 17), "2026-12-09")                         # 하루 앞
        v = fb.calc_week(S, D(2026, 12, 9))["values"]                                   # 시각을 주지 않으면 그날 0시(UTC)
        self.assertEqual(v["next_fomc"], "2026-12-09")
        naive = fb.calc_week(S, D(2026, 12, 9), datetime.datetime(2026, 12, 9, 22, 17))["values"]   # 시간대 없으면 UTC로
        self.assertEqual(naive["next_fomc"], "2027-01-27")
        # compute·main이 실행 시각을 주 칸에 넘긴다
        core = fb.compute(S, {}, D(2026, 12, 9), datetime.datetime(2026, 12, 9, 22, 17, tzinfo=utc))
        self.assertEqual(core["week"]["values"]["next_fomc"], "2027-01-27")
        self.assertEqual(fb.compute(S, {}, D(2026, 12, 9))["week"]["values"]["next_fomc"], "2026-12-09")

    def test_decision_time_follows_us_daylight_saving(self):
        utc = datetime.timezone.utc
        self.assertEqual(fb.decided_at(D(2026, 3, 18)), datetime.datetime(2026, 3, 18, 18, tzinfo=utc))   # 03-08부터 EDT
        self.assertEqual(fb.decided_at(D(2026, 1, 28)), datetime.datetime(2026, 1, 28, 19, tzinfo=utc))
        self.assertEqual(fb.decided_at(D(2026, 11, 4)), datetime.datetime(2026, 11, 4, 19, tzinfo=utc))   # 11-01부터 EST
        self.assertEqual(fb.decided_at(D(2026, 10, 28)), datetime.datetime(2026, 10, 28, 18, tzinfo=utc))
        self.assertEqual(fb.decided_at(D(2027, 3, 17)), datetime.datetime(2027, 3, 17, 18, tzinfo=utc))   # 2027-03-14부터 EDT
        try:
            from zoneinfo import ZoneInfo
            ny = ZoneInfo("America/New_York")
        except Exception:                                                              # 시간대 자료가 없는 환경 — 위 손 셈만
            return
        for _, b, _ in fb.FOMC:                                                         # 표의 모든 결정일 — tzdata와 같다
            d = D.fromisoformat(b)
            want = datetime.datetime(d.year, d.month, d.day, fb.DECISION_HOUR, tzinfo=ny).astimezone(utc)
            self.assertEqual(fb.decided_at(d), want, b)

    def test_fomc_table_matches_the_people_page(self):
        with open(os.path.join(REPO, "site", "people-data.js"), encoding="utf-8") as f:
            page = load_people(f.read())
        theirs = [(m["first_day"], m["date"]) for m in page["meetings_2026"]]
        mine = [(a, b) for a, b, _ in fb.FOMC if b.startswith("2026")]
        self.assertEqual(mine, theirs)
        for a, b, tentative in fb.FOMC:
            self.assertEqual(D.fromisoformat(b).weekday(), 2, b)                       # 결정일은 수요일
            self.assertEqual(D.fromisoformat(b) - D.fromisoformat(a), TD(days=1))
            self.assertEqual(tentative, b >= "2027", b)                                # 잠정은 2027년만
        self.assertEqual([b for _, b, _ in fb.FOMC], sorted(b for _, b, _ in fb.FOMC))
        # 2027년 = 연준 FOMC 일정 페이지(2026-10-28 갱신, 2026-11-03 확인)의 여덟 회의(검토 F1 — 전엔 2차 보도의 3월까지만)
        self.assertEqual([(a, b) for a, b, _ in fb.FOMC if b.startswith("2027")],
                         [("2027-01-26", "2027-01-27"), ("2027-03-16", "2027-03-17"), ("2027-04-27", "2027-04-28"),
                          ("2027-06-08", "2027-06-09"), ("2027-07-27", "2027-07-28"), ("2027-09-14", "2027-09-15"),
                          ("2027-10-26", "2027-10-27"), ("2027-12-07", "2027-12-08")])

    def test_observations_after_today_are_dropped(self):
        S = world()
        S["WDTGAL"] = S["WDTGAL"] + [(D(2026, 11, 4), 999_999.0)]
        S["SOFR"] = S["SOFR"] + [(D(2026, 11, 2), 9.0)]
        out = fb.compute(S, {}, NOW.date())
        self.assertEqual(out["dec"]["date"], "2026-10-28")
        self.assertEqual(out["spread"]["values"]["max_bp"], 8.0)

    def test_every_item_computes_and_texts_have_no_verdict_words(self):
        core = fb.compute(rmp_world(), {}, NOW.date(), ops=fb.parse_ops(OPS_BLOB), plan=fb.parse_plan(PLAN_BLOB))
        for spec in fb.ITEMS:
            c = core[spec["key"]]
            self.assertNotIsInstance(c, fb.ItemError, spec["key"])
            self.assertEqual(set(c["values"]), set(spec["values"]), spec["key"])
            self.assertTrue(fb.values_ok(spec, c["values"], c["lines"]), spec["key"])
            line, extra = fb.texts(spec["key"], c["values"], c["date"])
            for t in [line, *extra, spec["title"], fb.NOTICE, fb.COMPUTED_NOTICE, fb.WEEK_NOTICE, fb.SPREAD_DERIVED,
                      fb.SRF_DERIVED, fb.RMP_DERIVED, fb.RMP_NO_MBS, fb.PLAN_COPIED, fb.PLAN_ABOUT, fb.PLAN_FORMS,
                      *[ln["label"] for ln in spec.get("lines", ())],
                      spec.get("chart", {}).get("note", "")]:
                self.assertNotIn("None", t)
                body = t
                for ok in TOPIC:
                    body = body.replace(ok, "")
                for word in list(FORBIDDEN_TEXT) + list(VERDICT):
                    self.assertNotIn(word, body, (spec["key"], word))


class RmpTest(unittest.TestCase):
    """지준 관리 매입(RMP) 대조 — 창 규칙(9영업일, 연방 공휴일·대체일·토요일 공휴일), 경계일 운영, 소액 시험 운영·매각 제외, 이표채
    매입 포함, 끝나지 않은 창, 상환 수요일, 상환 없음, 보이는 숫자끼리 뺄셈, 응답 꼴, 요청·예산, 칸만 실패. 운영·금액은 지어낸 것.
    (공식 계획이 없을 때 — 규칙으로 잡는 창. 공식 기간으로 잡는 창은 PlanTest)"""

    def test_fed_holidays_follow_the_rules(self):
        self.assertEqual(sorted(fb.fed_holidays(2026)),
                         [D(2026, 1, 1), D(2026, 1, 19), D(2026, 2, 16), D(2026, 5, 25), D(2026, 6, 19), D(2026, 9, 7),
                          D(2026, 10, 12), D(2026, 11, 11), D(2026, 11, 26), D(2026, 12, 25)])    # 07-04(토)은 대체 없음
        self.assertNotIn(D(2026, 7, 3), fb.fed_holidays(2026))                          # 토요일 공휴일 — 앞 금요일에 연다
        self.assertIn(D(2027, 7, 5), fb.fed_holidays(2027))                             # 07-04(일) → 월요일
        self.assertNotIn(D(2027, 12, 24), fb.fed_holidays(2027))                        # 12-25(토) — 대체 없음
        self.assertIn(D(2023, 1, 2), fb.fed_holidays(2023))                             # 새해(일) → 월요일
        self.assertNotIn(D(2021, 12, 31), fb.fed_holidays(2021))                        # 2022-01-01(토) — 앞 해 금요일에 연다
        self.assertIn(D(2022, 6, 20), fb.fed_holidays(2022))                            # 준틴스(일) → 월요일
        self.assertNotIn(D(2020, 6, 19), fb.fed_holidays(2020))                         # 준틴스는 2021년부터
        self.assertEqual(sorted(fb.fed_holidays(2027))[:3], [D(2027, 1, 1), D(2027, 1, 18), D(2027, 2, 15)])
        self.assertIn(D(2027, 5, 31), fb.fed_holidays(2027))                            # 5월 마지막 월요일
        self.assertIn(D(2027, 11, 25), fb.fed_holidays(2027))                           # 11월 넷째 목요일

    def test_ninth_business_day(self):
        got = {(y, m): fb.bday_n(y, m) for y, m in ((2026, 6), (2026, 7), (2026, 8), (2026, 9), (2026, 10), (2026, 11),
                                                    (2027, 1), (2027, 7))}
        self.assertEqual(got, {(2026, 6): D(2026, 6, 11), (2026, 7): D(2026, 7, 13),     # 07-03(금)은 영업일
                               (2026, 8): D(2026, 8, 13), (2026, 9): D(2026, 9, 14),     # 노동절
                               (2026, 10): D(2026, 10, 14), (2026, 11): D(2026, 11, 13),  # 콜럼버스 · 재향군인
                               (2027, 1): D(2027, 1, 14), (2027, 7): D(2027, 7, 14)})     # 새해(금) · 07-05 대체일
        for (y, m), d in got.items():                                                   # 손 셈과 따로 — 평일 − 공휴일을 센다
            days = [D(y, m, 1) + TD(days=i) for i in range(31)]
            bd = [x for x in days if x.month == m and x.weekday() < 5 and x not in fb.fed_holidays(y)]
            self.assertEqual(bd[8], d)

    def test_running_window_and_request_range(self):
        for today, want in ((D(2026, 10, 14), (2026, 9)), (D(2026, 10, 15), (2026, 10)), (D(2026, 11, 13), (2026, 10)),
                            (D(2026, 11, 16), (2026, 11)), (D(2027, 1, 5), (2026, 12)), (D(2027, 1, 14), (2026, 12)),
                            (D(2027, 1, 15), (2027, 1))):
            self.assertEqual(fb.running_month(today), want, today)
        self.assertEqual(fb.ops_range(D(2026, 11, 3)), (D(2026, 6, 1), D(2026, 11, 3)))
        self.assertEqual(fb.ops_range(D(2027, 2, 10)), (D(2026, 9, 1), D(2027, 2, 10)))
        for today in (D(2026, 10, 15), D(2027, 1, 5), D(2027, 3, 31)):                  # 요청 범위가 실을 넷 창을 늘 덮는다
            first = fb.bday_n(*fb._shift(fb.running_month(today), -fb.RMP_ENDED))
            self.assertLess(fb.ops_range(today)[0], first)

    def test_mbs_paydown_wednesdays(self):
        self.assertEqual(fb.first_wed(D(2026, 11, 25)), D(2026, 11, 25))                  # 25일이 수요일이면 그날
        self.assertEqual(fb.first_wed(D(2026, 7, 25)), D(2026, 7, 29))                    # 토요일 → 다음 수요일
        self.assertEqual(fb.first_wed(D(2026, 10, 25)), D(2026, 10, 28))                  # 일요일
        self.assertEqual(fb.first_wed(D(2026, 6, 25)), D(2026, 7, 1))                     # 목요일 → 다음 달
        w = fb.rmp_window((2026, 7), [], dict(mbs_series()), D(2026, 12, 1))
        self.assertEqual((w["red_from"], w["red_to"], w["red_bn"]), ("2026-07-01", "2026-07-29", 10.5))
        w = fb.rmp_window((2026, 11), [], dict(mbs_series(end=D(2026, 12, 30))), D(2026, 12, 31))
        self.assertEqual((w["red_from"], w["red_to"]), ("2026-10-28", "2026-11-25"))
        self.assertEqual(w["red_bn"], 0.0)                                              # 그 사이 줄어든 것이 없으면 0

    def test_paydown_wednesday_moves_past_a_holiday_25th(self):
        # 패니메이·프레디맥 25일 상환은 25일이 주말·연방 공휴일이면 다음 영업일에 결제된다 — 성탄(12-25)이 수요일인 해엔 그날
        # 수요일 수준에 지니메이 몫만 들어, 그 달 상환 수요일은 다음 수요일이다(2024-12 실자료의 꼴: 12-25 주 작게, 01-01 주 크게)
        self.assertEqual(fb.paydown_wed(2030, 12), D(2031, 1, 1))
        self.assertEqual(fb.paydown_wed(2024, 12), D(2025, 1, 1))
        self.assertEqual(fb.paydown_wed(2026, 11), D(2026, 11, 25))                       # 25일이 영업일인 수요일이면 그날
        moved = [(y, m) for y in range(2020, 2046) for m in range(1, 13)
                 if fb.paydown_wed(y, m) != fb.first_wed(D(y, m, fb.MBS_DAY))]
        self.assertEqual(moved, [(2024, 12), (2030, 12), (2041, 12)])                   # 다른 달은 25일 이후 첫 수요일 그대로
        drops = {D(2030, 12, 4): 1000, D(2030, 12, 25): 3000, D(2031, 1, 1): 12000, D(2031, 1, 29): 9000}
        mbs = dict(mbs_series(drops, start=D(2030, 10, 2), end=D(2031, 3, 5)))
        dec, jan = (fb.rmp_window(ym, [], mbs, D(2031, 3, 31)) for ym in ((2030, 12), (2031, 1)))
        self.assertEqual((dec["red_from"], dec["red_to"], dec["red_bn"]), ("2030-11-27", "2031-01-01", 16.0))
        self.assertEqual((jan["red_from"], jan["red_to"], jan["red_bn"]), ("2031-01-01", "2031-01-29", 9.0))
        self.assertTrue(fb._windows_ok([dec, jan]))

    def test_windows_count_purchases_with_the_rules(self):
        c = calc("rmp")
        ws = c["values"]["windows"]
        self.assertEqual(c["date"], "2026-10-29")                                       # 오늘(10-30) 이하 마지막 결과 운영일
        self.assertTrue(c["values"]["mbs_ok"])
        self.assertEqual([(w["month"], w["from"], w["until"], w["ended"]) for w in ws],
                         [("2026-07", "2026-07-14", "2026-08-13", True), ("2026-08", "2026-08-14", "2026-09-14", True),
                          ("2026-09", "2026-09-15", "2026-10-14", True), ("2026-10", "2026-10-15", "2026-11-13", False)])
        self.assertEqual({w["bound"] for w in ws}, {"rule"})                            # 공식 계획을 넘기지 않으면 규칙
        self.assertEqual([w["ops"] for w in ws],
                         [["2026-07-14", "2026-07-28", "2026-08-13"],                    # 07-13(9영업일 그날)은 앞 창, 08-13은 이 창
                          ["2026-08-14", "2026-09-14"],                                  # 소액 시험 운영·매각은 빠진다
                          ["2026-09-15", "2026-09-30", "2026-10-14"],                    # 이표채 매입도 든다 · 같은 operationId는 한 번
                          ["2026-10-15", "2026-10-29"]])                                 # 오늘 뒤(10-31)는 빠진다
        self.assertEqual([w["bn"] for w in ws], [12.0, 8.0, 11.0, 4.2])
        self.assertEqual([(w["small"], w["sales"]) for w in ws], [(0, 0), (1, 1), (0, 0), (0, 0)])
        self.assertEqual([w["red_bn"] for w in ws], [10.5, 8.7, 10.9, None])            # 끝나지 않은 창은 상환을 견주지 않는다
        self.assertEqual([w["rmp_bn"] for w in ws], [1.5, -0.7, 0.1, None])
        self.assertTrue(fb._windows_ok(ws))

    def test_text_line_and_extras(self):
        c = calc("rmp")
        line, extra = fb.texts("rmp", c["values"], c["date"])
        self.assertEqual(line, "거꾸로 셈한 RMP(월 일정 창의 매입 − 그 달 MBS 상환): 2026-07 +1.5bn · 2026-08 -0.7bn · "
                               "2026-09 +0.1bn · 2026-10 아직 끝나지 않은 창 — 2번 운영, 합 4.2bn(2026-10-29까지)")
        self.assertEqual(extra[0], "2026-07 창(운영일 2026-07-14~2026-08-13 · 9영업일 규칙): 매입 3번 12.0bn(2026-07-14~"
                                   "2026-08-13) − 2026-07 MBS 상환 10.5bn(WSHOMCB 2026-07-01~2026-07-29 사이 줄어든 몫) = +1.5bn.")
        self.assertTrue(extra[1].endswith("= -0.7bn · 소액 시험 운영 1번 뺌 · 매각 운영 1번 셈하지 않음."), extra[1])
        self.assertEqual(extra[3], "2026-10 창(운영일 2026-10-15~2026-11-13 · 9영업일 규칙): 아직 끝나지 않은 창 — 2번 운영, "
                                   "합 4.2bn(2026-10-29까지) — 끝나기 전에는 상환과 견주지 않는다.")
        self.assertNotIn("상환 8.0", extra[3])
        self.assertEqual(extra[-2:], [fb.RMP_METHOD, fb.RMP_LIMITS])
        for word in ("운영 결과로 거꾸로 셈한 대조이고 공식 수치가 아니다", "공식 계획은 위 계획 줄", "계획과 실제 매입은 다를 수",
                     "예상 상환", "기관 CMBS는 WSHOMCB에 들어 있지만", "전달 실제 상환", "기관채 상환은 WSHOMCB에 없어",
                     "Treasury Securities Operational Details", "공식 기간이 없는 달의 창 경계는 9영업일 규칙의 근사",
                     "늘려 잡지 않는다"):
            self.assertIn(word, fb.RMP_LIMITS)
        for word in ("공식 나눔 수치가 아니라", "이 카드는 그것을 받지 않는다", "추정"):                     # 옛 문장
            self.assertNotIn(word, fb.RMP_LIMITS + fb.RMP_METHOD)
        for word in ("위 계획 줄의 공식 기간", "9영업일", "어느 쪽인지 적는다", "이웃 창이 겹치거나 사이에 영업일이 비면",
                     "다음 달 창과의 사이도"):
            self.assertIn(word, fb.RMP_METHOD)
        nested = re.compile(r"\([^()]*\(")
        for t in [line, *extra, fb.RMP_DERIVED, fb.RMP_DERIVED_EN, fb.RMP_NO_MBS]:
            self.assertIsNone(nested.search(t), t)
            self.assertNotIn("None", t)
            for word in list(FORBIDDEN_TEXT) + list(VERDICT) + ["재개", "중단", "진행"]:
                self.assertNotIn(word, t, word)

    def test_visible_numbers_subtract(self):
        # 보이는 소수 한 자리끼리 뺀다 — 27.64 − 17.46 = 10.18(10.2)이 아니라 27.6 − 17.5 = 10.1
        ops = fb.parse_ops(json.dumps({"treasury": {"auctions": [op("2026-07-20", 27.64)]}}))
        w = fb.rmp_window((2026, 7), ops, dict(mbs_series({D(2026, 7, 29): 17460})), D(2026, 9, 1))
        self.assertEqual((w["bn"], w["red_bn"], w["rmp_bn"]), (27.64, 17.46, 10.1))
        self.assertIn("매입 1번 27.6bn(2026-07-20) − 2026-07 MBS 상환 17.5bn", fb._win_long(w))
        self.assertTrue(fb._win_long(w).endswith("= +10.1bn."))
        w = fb.rmp_window((2026, 7), ops, dict(mbs_series({D(2026, 7, 29): 27640})), D(2026, 9, 1))
        self.assertEqual(w["rmp_bn"], 0.0)
        self.assertEqual(fb._win_short(w), "2026-07 0.0bn")                              # 0이면 부호 없이

    def test_no_paydown_leaves_the_estimate_empty(self):
        S = rmp_world()
        S["WSHOMCB"] = [p for p in S["WSHOMCB"] if p[0] <= D(2026, 9, 23)]               # 09-30 수요일 관측이 아직 없다
        ws = fb.calc_rmp(S, NOW.date(), fb.parse_ops(OPS_BLOB))["values"]["windows"]
        self.assertEqual([w["rmp_bn"] for w in ws], [1.5, -0.7, None, None])
        line, extra = fb.texts("rmp", {"windows": ws, "mbs_ok": True}, "2026-10-29")
        self.assertIn("2026-09 매입 11.0bn · 상환 —", line)
        self.assertIn("WSHOMCB 2026-08-26·2026-09-30 두 수요일 관측이 다 있지 않아 상환·대조를 비웠다", extra[2])
        del S["WSHOMCB"]                                                                # MBS 보유를 받지 못함 — 매입은 싣는다
        core = fb.compute(S, {"WSHOMCB": "fetch"}, NOW.date(), ops=fb.parse_ops(OPS_BLOB))["rmp"]
        self.assertFalse(core["values"]["mbs_ok"])
        self.assertEqual([w["bn"] for w in core["values"]["windows"]], [12.0, 8.0, 11.0, 4.2])
        self.assertTrue(all(w["red_bn"] is None and w["rmp_bn"] is None for w in core["values"]["windows"]))
        line, extra = fb.texts("rmp", core["values"], core["date"])
        self.assertIn(fb.RMP_NO_MBS, extra)
        self.assertTrue(fb.values_ok(fb.BY_KEY["rmp"], core["values"], {}))

    def test_parse_ops_shapes(self):
        rows = [op("2026-07-20", 1.0), op("2026-07-20", 1.0, oid="A"), op("2026-07-20", 2.0, oid="A"),   # 같은 ID는 나중 것
                {**op("2026-07-21", 0), "totalParAmtAccepted": "1,500,000,000"}, {**op("2026-07-22", 0), "totalParAmtAccepted": 2 * B},
                {"auctionStatus": "Announcement", "totalParAmtAccepted": "?"}]
        got = fb.parse_ops(json.dumps({"treasury": {"auctions": rows}}).encode())
        self.assertEqual(got, [(D(2026, 7, 20), "P", 1.0 * B), (D(2026, 7, 20), "P", 2.0 * B), (D(2026, 7, 21), "P", 1.5 * B),
                               (D(2026, 7, 22), "P", 2.0 * B)])
        bad = [b"{", b"[]", json.dumps({"treasury": {}}).encode(), json.dumps({"treasury": {"auctions": {}}}).encode(),
               json.dumps({"treasury": {"auctions": ["x"]}}).encode(), "\udcff".encode("utf-8", "surrogatepass")]
        for row in ({**op("2026-07-20", 1.0), "operationDate": "07/20/2026"}, {**op("2026-07-20", 1.0), "operationDirection": "X"},
                    {**op("2026-07-20", 1.0), "totalParAmtAccepted": "abc"}, {**op("2026-07-20", 1.0), "totalParAmtAccepted": "-5"},
                    {**op("2026-07-20", 1.0), "totalParAmtAccepted": True}, {**op("2026-07-20", 1.0), "totalParAmtAccepted": ""},
                    {**op("2026-07-20", 1.0), "totalParAmtAccepted": str(fb.OP_MAX + 1)}):   # 운영 하나가 터무니없이 크면 단위 의심
            bad.append(json.dumps({"treasury": {"auctions": [row]}}).encode())
        for blob in bad:
            with self.assertRaises(fb.ItemError, msg=blob[:60]) as e:
                fb.parse_ops(blob)
            self.assertEqual(e.exception.code, "format")
        with self.assertRaises(fb.ItemError):                                           # 결과 운영이 하나도 없으면 셈할 것이 없다
            fb.calc_rmp(rmp_world(), NOW.date(), fb.parse_ops(json.dumps({"treasury": {"auctions": []}})))

    def test_load_ops_requests_once_and_never_falls_back_to_cache(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        ops = FakeOps(OPS_BLOB)
        got = fb.load_ops(tmp, D(2026, 11, 3), ops_load=ops)
        self.assertEqual(len(got), 14)                                                  # 결과 운영만, 같은 operationId는 한 번
        self.assertEqual(ops.calls, [fb.OPS_URL + "?startDate=2026-06-01&endDate=2026-11-03"])
        with open(os.path.join(tmp, fb.CACHE, fb.OPS_CACHE), "rb") as f:
            self.assertEqual(f.read(), OPS_BLOB)
        e = fb.load_ops(tmp, D(2026, 11, 4), ops_load=FakeOps(fail=True))                # 받지 못하면 캐시로 대신하지 않는다
        self.assertEqual((type(e), e.code), (fb.ItemError, "fetch"))
        e = fb.load_ops(tmp, D(2026, 11, 4), ops_load=FakeOps(blob=b"<html>"))
        self.assertEqual(e.code, "format")
        with open(os.path.join(tmp, fb.CACHE, fb.OPS_CACHE), "rb") as f:
            self.assertEqual(f.read(), OPS_BLOB)                                        # 깨진 응답은 캐시를 덮지 않는다
        with mock.patch.object(cf.urllib.request, "urlopen", side_effect=AssertionError("요청")):
            self.assertEqual(len(fb.load_ops(tmp, D(2026, 11, 4), offline=True)), 14)   # --offline은 캐시만
            self.assertEqual(fb.load_ops(os.path.join(tmp, "없음"), D(2026, 11, 4), offline=True).code, "fetch")

    def test_new_york_fed_request_keeps_its_host_and_budget(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        seen = []

        class Resp(io.BytesIO):
            def __init__(self, body, url):
                super().__init__(body)
                self.url = url

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def geturl(self):
                return self.url

        def opener(req, timeout=None):
            seen.append((req.get_header("User-agent"), timeout))
            return Resp(OPS_BLOB, "https://elsewhere.invalid/x")                        # 다른 곳으로 넘겨짐
        self.assertEqual(fb.load_ops(tmp, D(2026, 11, 3), opener=opener).code, "fetch")
        self.assertEqual(seen, [(cf.UA, cf.REQ_TIMEOUT)])
        t = [0.0]

        def clock():
            t[0] += 7.0
            return t[0]
        seen.clear()                                                                    # 예산(OPS_BUDGET초)을 다 쓰면 요청하지 않는다
        self.assertEqual(fb.load_ops(tmp, D(2026, 11, 3), clock=clock, opener=opener, budget=5).code, "fetch")
        self.assertEqual(seen, [])
        self.assertLessEqual(fb.BUDGET + fb.OPS_BUDGET, 90)                              # 단계 제한 2분 안

    def test_compute_without_ops_leaves_the_item_out(self):
        # 운영 결과를 넘기지 않는 호출(비공개 쪽 짝 테스트 등)은 rmp를 셈하지 않고 파일에도 넣지 않는다
        core = fb.compute(world(), {}, NOW.date())
        self.assertNotIn("rmp", core)
        data = fb.build(core, {}, NOW)
        self.assertNotIn("rmp", data["items"])
        self.assertEqual(data["order"], ["reserves", "dec", "spread", "srf", "rrp", "week"])
        self.assertTrue(all(it["ok"] for it in data["items"].values()))
        core = fb.compute(world(), {}, NOW.date(), ops=fb.ItemError("fetch"))
        self.assertEqual(core["rmp"].code, "fetch")
        self.assertNotIn("rmp_plan", core)                                               # 계획을 넘기지 않으면 그 칸도 없다
        core = fb.compute(rmp_world(), {}, NOW.date(), plan=fb.parse_plan(PLAN_BLOB))
        self.assertEqual((sorted(k for k in core if k.startswith("rmp"))), ["rmp_plan"])   # 계획만 넘기면 계획 칸만

    def test_windows_check_rejects_odd_carried_values(self):
        good = calc("rmp")["values"]["windows"]
        self.assertTrue(fb._windows_ok(good))
        cases = [lambda w: w.pop(1),                                                    # 달이 이어지지 않는다
                 lambda w: w[0].pop("bound"),                                           # 경계 칸이 없다
                 lambda w: w[0].update(bound="plan?"),
                 lambda w: w[0].update(bound=["rule"]),
                 lambda w: w[1].update(**{"from": "2026-08-15"}),                       # 규칙인데 규칙 날짜가 아니다
                 lambda w: w[1].update(bound="plan", **{"from": "2026-07-31"}),          # 공식 기간인데 시작일이 그 달이 아니다
                 lambda w: w[1].update(bound="plan", **{"from": "2026-08-13"}),          # 앞 창과 겹친다
                 lambda w: w[0].update(ended=False),                                    # 끝나지 않은 창이 앞에
                 lambda w: w[0].update(rmp_bn=1.6),                                     # 매입 − 상환과 다르다
                 lambda w: w[3].update(red_bn=1.0, rmp_bn=_t(w[3])),                    # 끝나지 않은 창에 상환
                 lambda w: w[1]["ops"].append("2026-12-01"),                            # 운영일이 창 밖·수가 다르다
                 lambda w: w[1].update(n=3),
                 lambda w: w[2].update(bn=-1.0),
                 lambda w: w[0].update(extra=1),
                 lambda w: w[0].update(month="2026-13"),
                 lambda w: w.extend(json.loads(json.dumps(w[:2])))]                      # 다섯 창
        for i, f in enumerate(cases):
            ws = json.loads(json.dumps(good))
            f(ws)
            self.assertFalse(fb._windows_ok(ws), i)

    def test_main_ops_failure_only_stales_its_item(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        out, work = os.path.join(tmp, "data"), os.path.join(tmp, ".work")
        run = lambda ops, now, fred=None: fb.main(["--out", out, "--work", work], fred_load=fred or FakeFred(rmp_world()),
                                                   now=now, ops_load=ops, plan_load=FakePlan())
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            self.assertEqual(run(FakeOps(), NOW), 0)
            self.assertEqual(run(FakeOps(fail=True), NOW + TD(days=1)), 0)
        with open(os.path.join(out, fb.FILE), encoding="utf-8") as f:
            items = json.load(f)["items"]
        r = items["rmp"]
        self.assertEqual((r["ok"], r["stale"], r["error"], r["failed_since"], r["retrieved"]),
                         (False, True, "수신 실패", "2026-10-31", "2026-10-30"))
        self.assertIn("2026-07 +1.5bn", r["line"])                                      # 직전 숫자에서 다시 만든 문구
        self.assertTrue(items["rmp_plan"]["ok"])                                         # 계획 칸은 따로
        self.assertTrue(all(it["ok"] for k, it in items.items() if k != "rmp"))
        self.assertIn("::warning::연준 재무상태표 참고 rmp 받지 못함: 수신 실패", buf.getvalue())
        self.assertNotIn("xyz-77", buf.getvalue() + json.dumps(items, ensure_ascii=False))


class PlanTest(unittest.TestCase):
    """지준 관리 매입(RMP) 공식 계획 — 뉴욕 연은 Operational Details 페이지의 표 읽기(두 문장 꼴·형식 모름·깨진 날짜·태그·&nbsp;·
    줄바꿈·차례·같은 기간·옛 창·크기 상한·표 없음), 네 달 창과 글, 대조 칸의 창을 공식 기간으로 잡을 때와 규칙으로 잡을 때, 요청 꼴
    (User-Agent·다른 호스트로 넘김 거절·함께 쓰는 예산)·캐시, 칸만 실패, 옛 파일. 페이지 HTML·금액은 모두 지어낸 것."""

    def periods(self, blob):
        return [(a.isoformat(), b.isoformat(), x, y) for a, b, x, y in fb.parse_plan(blob)["periods"]]

    def test_reads_the_two_forms_and_leaves_other_forms_unknown(self):
        rows = [("10/15/2026 -<br>11/13/2026", plan_text("9.0")),                       # RMP 없음
                ("9/15/2026 - 10/14/2026", plan_text("13.3", "2.5", additional=False)),  # 'an additional' 없이
                ("8/14/2026 – 9/14/2026", plan_text("12.2", "7", verb="purchase")),   # 긴 줄표·purchase
                ("<span>7/14/2026</span>\n   -\n   8/13/2026",                              # 태그·줄바꿈·&nbsp;·여분 공백
                 "<strong>The Desk</strong> plans to conduct&nbsp;approximately $11.1 billion in\n    reinvestment purchases "
                 "and an additional approximately <b>$5</b> billion in reserve management purchases over the noted monthly "
                 "  period. "),
                ("6/12/2026 - 7/13/2026", "The Desk plans to conduct small value operations of approximately $150 million "
                                          "over the monthly period from 6/12/2026 to 7/13/2026."),   # 소액 시험 운영 창
                ("5/14/2026 - 6/11/2026", "The Desk will not conduct any Treasury securities operations over the monthly "
                                          "period from 5/14/26 to 6/11/26."),                      # 운영 없음
                ("4/14/2026 - 5/13/2026", plan_text("8.8", "4") + " Of the reserve management purchases, approximately $1 "
                                          "billion will be in Treasury coupon securities."),       # 쿠폰 배분 문장이 붙음
                ("3/13/2026 - 4/13/2026", "The Desk plans to purchase approximately $20.0 billion in reinvestment purchases "
                                          "and an additional approximately $60.0 billion in reserve management purchases "
                                          "of bills over the noted monthly period."),              # 옛 창의 꼴
                ("2/13/2026 - 3/12/2026", plan_text("1,000")),                                     # 쉼표 금액 — 정해 둔 꼴 밖
                ("3/16/2020", "The Desk plans to purchase approximately $40.0 billion in Treasury purchases."),   # 하루짜리 옛 행
                ("13/40/2026 - 14/12/2026", plan_text("1.0")), ("TBD", plan_text("1.0")),          # 기간을 읽지 못하는 행
                ("2/30/2026 - 3/12/2026", plan_text("1.0")), ("5/10/2026 - 4/10/2026", plan_text("1.0")),
                ("1/1/2026 - 6/30/2026", plan_text("1.0")), ("11/1/26 - 11/30/26", plan_text("1.0"))]
        got = fb.parse_plan(plan_html(rows))
        self.assertEqual(got["dropped"], 6)
        self.assertEqual(self.periods(plan_html(rows)), [
            ("2020-03-16", "2020-03-16", None, None),
            ("2026-02-13", "2026-03-12", None, None), ("2026-03-13", "2026-04-13", None, None),
            ("2026-04-14", "2026-05-13", None, None), ("2026-05-14", "2026-06-11", None, None),
            ("2026-06-12", "2026-07-13", None, None), ("2026-07-14", "2026-08-13", "11.1", "5"),
            ("2026-08-14", "2026-09-14", "12.2", "7"), ("2026-09-15", "2026-10-14", "13.3", "2.5"),
            ("2026-10-15", "2026-11-13", "9.0", "0")])
        self.assertEqual(fb._period("12/12/2025 -  1/14/2026"), (D(2025, 12, 12), D(2026, 1, 14)))   # 해를 넘는 창
        self.assertIsNone(fb._period("12/12/2025 - 1/14/2026 (tentative)"))

    def test_same_period_twice_and_row_order(self):
        rows = [("8/14/2026 - 9/14/2026", plan_text("12.2")), ("7/14/2026 - 8/13/2026", plan_text("11.1", "5")),
                ("9/15/2026 - 10/14/2026", plan_text("13.3")), ("8/14/2026 - 9/14/2026", plan_text("12.2")),   # 같은 숫자
                ("7/14/2026 - 8/13/2026", plan_text("11.1", "6")),                              # 같은 기간에 다른 숫자
                ("10/15/2026 - 11/13/2026", "<td>stray cell")]                                 # 칸이 밀린 행 — 형식 모름
        self.assertEqual(self.periods(plan_html(rows)),
                         [("2026-07-14", "2026-08-13", None, None), ("2026-08-14", "2026-09-14", "12.2", "0"),
                          ("2026-09-15", "2026-10-14", "13.3", "0"), ("2026-10-15", "2026-11-13", None, None)])

    def test_finds_the_table_by_its_head(self):
        decoy = ("<table><tr><th>Date</th><th>Amount</th></tr><tr><td>10/15/2026 - 11/13/2026</td><td>" + plan_text("99.0")
                 + "</td></tr></table>")
        got = self.periods(plan_html([("10/15/2026 - 11/13/2026", plan_text("9.0"))], before=decoy))
        self.assertEqual(got, [("2026-10-15", "2026-11-13", "9.0", "0")])                # 머리가 다른 표는 보지 않는다
        head = ("PERIOD", "Planned Operation Amount (USD)", "Tentative Schedule")           # 대소문자·덧붙인 말
        self.assertEqual(self.periods(plan_html([("9/15/2026 - 10/14/2026", plan_text("13.3"))], head=head)),
                         [("2026-09-15", "2026-10-14", "13.3", "0")])
        loose = ("<table><tr><th>Period<th>Planned Operation Amount<tr><td>10/15/2026 - 11/13/2026<td>" + plan_text("9.0")
                 + "<tr><td>9/15/2026 - 10/14/2026<td>" + plan_text("13.3", "1")).encode()    # 닫는 태그가 없는 표
        self.assertEqual(self.periods(loose), [("2026-09-15", "2026-10-14", "13.3", "1"), ("2026-10-15", "2026-11-13", "9.0", "0")])
        for blob, code in ((b"<html><body><p>no table</p><script>$('<table><tr><th>Period</th>')</script></body></html>", "table"),
                           (plan_html([], head=("Date", "Amount")), "table"),
                           (plan_html([]), "format"),                                            # 머리뿐
                           (plan_html([("TBD", plan_text("1.0"))]), "format"),                   # 읽은 기간이 없다
                           (None, "format"), ("\udcff<table", "table")):
            with self.assertRaises(fb.ItemError, msg=repr(blob)[:60]) as e:
                fb.parse_plan(blob)
            self.assertEqual(e.exception.code, code)

    def test_size_cap(self):
        big = PLAN_BLOB + b"<!--" + b"x" * fb.PLAN_MAX + b"-->"
        with self.assertRaises(fb.ItemError) as e:
            fb.parse_plan(big)
        self.assertEqual(e.exception.code, "fetch")
        self.assertLessEqual(len(PLAN_BLOB), fb.PLAN_MAX)
        self.assertEqual(fb.PLAN_MAX, 2_000_000)

    def test_four_month_windows_and_text(self):
        c = fb.calc_plan({}, NOW.date(), fb.parse_plan(PLAN_BLOB))
        ws = c["values"]["windows"]
        self.assertEqual(c["date"], "2026-10-15")                                       # 실은 창 가운데 마지막 시작일
        self.assertEqual([w["month"] for w in ws], ["2026-07", "2026-08", "2026-09", "2026-10"])   # 대조 칸과 같은 네 달
        self.assertEqual([w["now"] for w in ws], [False, False, False, True])
        self.assertEqual((c["values"]["rows"], c["values"]["dropped"]), (5, 0))
        self.assertTrue(fb.values_ok(fb.BY_KEY["rmp_plan"], c["values"], {}))
        line, extra = fb.texts("rmp_plan", c["values"], c["date"])
        self.assertEqual(line, "2026-07-14~2026-08-13 재투자 약 11.1bn · RMP 약 5bn / 2026-08-14~2026-09-14 재투자 약 12.2bn · "
                               "RMP 없음 / 2026-09-15~2026-10-14 재투자 약 13.3bn · RMP 약 2.5bn / 2026-10-15~2026-11-13(지금 창) "
                               "재투자 약 9.0bn · RMP 없음")
        self.assertEqual(extra, [fb.PLAN_ABOUT, "페이지 표의 기간 5개 가운데 이 카드의 네 달 창만 싣는다 — 시작일이 그 달인 기간 "
                                                "하나를 그 달 창으로 본다.", fb.PLAN_FORMS])
        for word in ("계획이다", "실제 매입은 운영 결과", "대조 줄"):
            self.assertIn(word, fb.PLAN_ABOUT)
        for word in ("no reserve management purchases", "형식 모름", "숫자를 짓지", "쿠폰 배분 문장", "conduct(또는 purchase)"):
            self.assertIn(word, fb.PLAN_FORMS)
        for verb in ("conduct", "purchase"):                                            # 화면 글과 읽는 꼴이 같다
            self.assertEqual(fb._plan_sentence(f"The Desk plans to {verb} approximately $5.0 billion in reinvestment purchases "
                                               "and no reserve management purchases over the noted monthly period."), ("5.0", "0"))
        odd = plan_html([("7/14/2026 - 8/13/2026", "The Desk will not conduct any Treasury securities operations."),
                         ("8/14/2026 - 8/27/2026", plan_text("6.0")), ("8/28/2026 - 9/14/2026", plan_text("6.1")),
                         ("10/15/2026 - 11/13/2026", plan_text("9.0", "3")), ("9/15/2026 - 13/14/2026", plan_text("1.0"))])
        c = fb.calc_plan({}, NOW.date(), fb.parse_plan(odd))
        self.assertTrue(fb.values_ok(fb.BY_KEY["rmp_plan"], c["values"], {}))
        line, extra = fb.texts("rmp_plan", c["values"], c["date"])
        self.assertEqual(line, "2026-07-14~2026-08-13 형식 모름 / 2026-08 창 형식 모름 — 그 달에 시작하는 기간이 여럿 / 2026-09 창 "
                               "페이지에 없음 / 2026-10-15~2026-11-13(지금 창) 재투자 약 9.0bn · RMP 약 3bn")
        self.assertIn("표의 행 가운데 기간 날짜를 읽지 못한 1개는 뺐다.", extra)
        for t in [line, *extra, fb.PLAN_COPIED, fb.PLAN_COPIED_EN, fb.BY_KEY["rmp_plan"]["title"]]:
            for word in list(FORBIDDEN_TEXT) + list(VERDICT) + ["재개", "중단", "None"]:
                self.assertNotIn(word, t, word)
            self.assertIsNone(re.search(r"\([^()]*\(", t), t)                            # 겹 괄호 없음
        old = plan_html([("1/15/2026 - 2/12/2026", plan_text("1.0"))])                   # 네 달에 든 기간이 없다
        with self.assertRaises(fb.ItemError) as e:
            fb.calc_plan({}, NOW.date(), fb.parse_plan(old))
        self.assertEqual(e.exception.code, "format")

    def test_plan_window_check_rejects_odd_values(self):
        good = fb.calc_plan({}, NOW.date(), fb.parse_plan(PLAN_BLOB))["values"]["windows"]
        self.assertTrue(fb._plan_windows_ok(good))
        cases = [lambda w: w.pop(1),                                                    # 달이 이어지지 않는다
                 lambda w: w[0].update(rmp="10<b>"),                                    # 숫자 글이 아니다
                 lambda w: w[0].update(rmp=10),
                 lambda w: w[0].update(reinvest=None),                                  # ok인데 숫자가 없다
                 lambda w: w[0].update(form="unknown"),                                 # 형식 모름인데 숫자가 있다
                 lambda w: w[0].update(form="weird"),
                 lambda w: w[1].update(**{"from": "2026-07-31"}),                       # 시작일이 그 달이 아니다
                 lambda w: w[1].update(**{"from": "2026-08-13"}),
                 lambda w: w[1].update(until=None),                                     # 날짜가 하나만
                 lambda w: w[1].update(until="2026-12-31"),                             # 기간이 너무 길다·겹친다
                 lambda w: w[2].update(form="missing", reinvest=None, rmp=None),        # 없는데 날짜가 있다
                 lambda w: w[3].update(now="yes"),
                 lambda w: w[0].update(extra=1),
                 lambda w: [x.update(form="missing", reinvest=None, rmp=None, now=False, **{"from": None, "until": None})
                            for x in w],                                                # 날짜가 하나도 없다
                 lambda w: w.extend(json.loads(json.dumps(w[:1])))]                      # 다섯 창
        for i, f in enumerate(cases):
            ws = json.loads(json.dumps(good))
            f(ws)
            self.assertFalse(fb._plan_windows_ok(ws), i)

    def test_rmp_windows_take_the_official_periods(self):
        # 지어낸 공식 기간이 규칙과 하루 다르다 — 7월 창 07-14~08-12, 8월 창 08-13~09-14: 08-13 운영(3.0)이 규칙으로는 7월 창,
        # 공식 기간으로는 8월 창에 든다
        plan = fb.parse_plan(plan_html([("7/14/2026 - 8/12/2026", plan_text("11.1", "5")),
                                        ("8/13/2026 - 9/14/2026", plan_text("12.2")),
                                        ("9/15/2026 - 10/14/2026", "not a known sentence"),     # 형식 모름이어도 기간은 공식
                                        ("10/15/2026 - 11/13/2026", plan_text("9.0"))]))
        ops = fb.parse_ops(OPS_BLOB)
        c = fb.calc_rmp(rmp_world(), NOW.date(), ops, plan)
        ws = c["values"]["windows"]
        self.assertEqual([(w["from"], w["until"], w["bound"]) for w in ws],
                         [("2026-07-14", "2026-08-12", "plan"), ("2026-08-13", "2026-09-14", "plan"),
                          ("2026-09-15", "2026-10-14", "plan"), ("2026-10-15", "2026-11-13", "plan")])
        self.assertEqual([w["bn"] for w in ws], [9.0, 11.0, 11.0, 4.2])                   # 규칙으로는 12.0 · 8.0
        self.assertEqual([w["rmp_bn"] for w in ws], [-1.5, 2.3, 0.1, None])
        self.assertEqual(ws[1]["ops"], ["2026-08-13", "2026-08-14", "2026-09-14"])
        self.assertTrue(fb._windows_ok(ws))
        line, extra = fb.texts("rmp", c["values"], c["date"])
        self.assertTrue(extra[0].startswith("2026-07 창(운영일 2026-07-14~2026-08-12 · 공식 기간): 매입 2번 9.0bn"), extra[0])
        # 그 달 기간이 없거나 여럿이면 그 달만 규칙 — 이웃 창과 사이가 비지 않을 때
        plan = fb.parse_plan(plan_html([("7/14/2026 - 8/13/2026", plan_text("11.1", "5")),
                                        ("8/14/2026 - 8/27/2026", plan_text("6.0")), ("8/28/2026 - 9/14/2026", plan_text("6.1")),
                                        ("10/15/2026 - 11/13/2026", plan_text("9.0"))]))
        ws = fb.calc_rmp(rmp_world(), NOW.date(), ops, plan)["values"]["windows"]
        self.assertEqual([w["bound"] for w in ws], ["plan", "rule", "rule", "plan"])
        self.assertEqual([w["bn"] for w in ws], [12.0, 8.0, 11.0, 4.2])
        self.assertTrue(fb._windows_ok(ws))
        self.assertIn("· 9영업일 규칙): ", fb.texts("rmp", {"windows": ws, "mbs_ok": True}, "2026-10-29")[1][1])
        # 공식 기간 끝(08-12)과 규칙으로 잡은 다음 창의 시작(08-14) 사이에 영업일(08-13 목)이 비면 네 창 모두 규칙 — 전엔 7월만
        # 공식 기간으로 잡아 08-13 운영(3.0)이 어느 창에도 들지 않았다(검토 F1)
        plan = fb.parse_plan(plan_html([("7/14/2026 - 8/12/2026", plan_text("11.1", "5")),
                                        ("8/14/2026 - 8/27/2026", plan_text("6.0")), ("8/28/2026 - 9/14/2026", plan_text("6.1")),
                                        ("10/15/2026 - 11/13/2026", plan_text("9.0"))]))
        ws = fb.calc_rmp(rmp_world(), NOW.date(), ops, plan)["values"]["windows"]
        self.assertEqual({w["bound"] for w in ws}, {"rule"})
        self.assertEqual([w["bn"] for w in ws], [12.0, 8.0, 11.0, 4.2])
        self.assertIn("2026-08-13", ws[0]["ops"])
        # 공식 기간이 이웃 창과 겹치면 네 창 모두 규칙
        plan = fb.parse_plan(plan_html([("7/14/2026 - 8/14/2026", plan_text("11.1")), ("8/14/2026 - 9/14/2026", plan_text("1"))]))
        ws = fb.calc_rmp(rmp_world(), NOW.date(), ops, plan)["values"]["windows"]
        self.assertEqual({w["bound"] for w in ws}, {"rule"})
        self.assertEqual([w["bn"] for w in ws], [12.0, 8.0, 11.0, 4.2])
        # 끝 날이 공식 기간이면 '끝난 창'도 그 날로 — 오늘이 공식 끝 날(규칙의 끝 날보다 이르다) 뒤면 끝남. 다음 달 기간이 바로
        # 이어질 때만(10-30 금 → 11-02 월, 사이는 주말뿐) — 다음 달 기간이 아직 없으면 사이(10-30~11-13)가 비어 규칙으로(아래)
        plan = fb.parse_plan(plan_html([("10/15/2026 - 10/30/2026", plan_text("9.0")), ("11/2/2026 - 11/27/2026", plan_text("8.0"))]))
        weekday_ops = [o for o in ops if o[0] != D(2026, 10, 31)]                       # 지어낸 토요일 운영은 빼고
        ws = fb.calc_rmp(rmp_world(), D(2026, 11, 1), weekday_ops, plan)["values"]["windows"]
        self.assertEqual((ws[-1]["until"], ws[-1]["ended"], ws[-1]["bound"]), ("2026-10-30", True, "plan"))
        self.assertTrue(fb._windows_ok(ws))
        plan = fb.parse_plan(plan_html([("10/15/2026 - 10/29/2026", plan_text("9.0"))]))
        ws = fb.calc_rmp(rmp_world(), NOW.date(), ops, plan)["values"]["windows"]
        self.assertEqual((ws[-1]["until"], ws[-1]["ended"], ws[-1]["bound"]), ("2026-11-13", False, "rule"))
        self.assertTrue(fb._windows_ok(ws))

    def test_rmp_windows_fall_back_when_official_periods_leave_a_gap(self):
        # 반 달씩 나눈 행(이 페이지의 2020-06~2021-02 꼴 — 'The Desk's current schedule covers purchases from …', 날짜·금액은
        # 지어낸 것): 8월에 시작하는 행이 반 달짜리 하나뿐이면 그 행이 8월 창이 되고 다음 행(09-01~)은 9월 행이라 9월은 여럿 → 규칙.
        # 8월 공식 끝(08-31)과 9월 규칙 시작(09-15) 사이가 비어 09-14 운영(2.0)이 빠지던 꼴 — 네 창 모두 규칙으로 돌아가야 한다
        half = lambda a, b: f"The Desk's current schedule covers purchases from {a} to {b}."
        ops = fb.parse_ops(OPS_BLOB)
        rows = [("7/14/2026 - 7/31/2026", half("7/14", "7/31")), ("8/14/2026 - 8/31/2026", half("8/14", "8/31")),
                ("9/1/2026 - 9/14/2026", half("9/1", "9/14")), ("9/15/2026 - 9/30/2026", half("9/15", "9/30")),
                ("10/15/2026 - 11/13/2026", plan_text("9.0"))]
        plan = fb.parse_plan(plan_html(rows))
        months = fb.rmp_months(NOW.date())
        self.assertEqual([b[2] for b in fb.plan_bounds(months, plan)], ["rule"] * 4)
        ws = fb.calc_rmp(rmp_world(), NOW.date(), ops, plan)["values"]["windows"]
        self.assertEqual([w["bn"] for w in ws], [12.0, 8.0, 11.0, 4.2])                   # 규칙 창 = 운영 결과 전부
        self.assertTrue(fb._windows_ok(ws))
        inside = sum(1 for o in ops if o[1] == "P" and o[2] >= fb.SMALL_MIN and o[0] <= NOW.date()
                     and any(w["from"] <= o[0].isoformat() <= w["until"] for w in ws))
        self.assertEqual(inside, sum(w["n"] for w in ws))
        self.assertEqual(inside, 10)                                                    # 07-14 ~ 10-29의 매입 운영 열이 모두 든다
        # 지금 창만 반 달짜리 — 공식 끝(10-23)과 다음 달 창(11월 기간이 없어 규칙: 11-14~) 사이가 비면 규칙으로. 전엔 지금 창이
        # 10-23에 끝나 네 창이 모두 '끝난 창'이 되고 10-29 운영이 빠졌다
        plan = fb.parse_plan(plan_html([("10/15/2026 - 10/23/2026", half("10/15", "10/23"))]))
        self.assertEqual([b[2] for b in fb.plan_bounds(months, plan)], ["rule"] * 4)
        ws = fb.calc_rmp(rmp_world(), NOW.date(), ops, plan)["values"]["windows"]
        self.assertEqual((ws[-1]["from"], ws[-1]["until"], ws[-1]["ended"], ws[-1]["bn"]), ("2026-10-15", "2026-11-13", False, 4.2))
        # 주말·연방 공휴일만 사이에 있으면 비지 않은 것 — 지금 창 10-15~10-30(금), 다음 달 창 11-02(월)~
        plan = fb.parse_plan(plan_html([("10/15/2026 - 10/30/2026", plan_text("9.0")), ("11/2/2026 - 11/27/2026", plan_text("8.0"))]))
        self.assertEqual([b[2] for b in fb.plan_bounds(months, plan)], ["rule", "rule", "rule", "plan"])
        ws = fb.calc_rmp(rmp_world(), NOW.date(), ops, plan)["values"]["windows"]
        self.assertEqual((ws[-1]["until"], ws[-1]["ended"]), ("2026-10-30", False))
        self.assertTrue(fb._windows_ok(ws))
        self.assertFalse(fb.bday_gap(D(2026, 11, 13), D(2026, 11, 16)))                   # 주말
        self.assertFalse(fb.bday_gap(D(2026, 10, 9), D(2026, 10, 13)))                    # 주말 + 콜럼버스 데이(10-12)
        self.assertTrue(fb.bday_gap(D(2026, 10, 9), D(2026, 10, 14)))                     # 10-13 화
        self.assertTrue(fb.bday_gap(D(2026, 8, 12), D(2026, 8, 14)))                      # 08-13 목
        self.assertFalse(fb.bday_gap(D(2026, 8, 13), D(2026, 8, 14)))                     # 바로 이어짐
        self.assertFalse(fb.bday_gap(D(2026, 8, 14), D(2026, 8, 13)))                     # 겹침은 따로 본다
        # 이어 싣는 값도 — 사이가 빈 창 목록은 받지 않는다
        good = fb.calc_rmp(rmp_world(), NOW.date(), ops)["values"]["windows"]
        ws = json.loads(json.dumps(good))
        ws[0].update(bound="plan", until="2026-08-13")                                  # 규칙 날짜와 같은 공식 기간 — 받음
        self.assertTrue(fb._windows_ok(ws))
        ws[0].update(until="2026-08-11", ops=["2026-07-14", "2026-07-28"], n=2, bn=9.0, rmp_bn=-1.5)   # 08-12·08-13이 빔
        self.assertFalse(fb._windows_ok(ws))
        ws[0].update(until="2026-08-12", ops=["2026-07-14", "2026-07-28"], n=2, bn=9.0, rmp_bn=-1.5)   # 08-13 하루가 빔
        self.assertFalse(fb._windows_ok(ws))

    def test_load_plan_requests_once_caches_and_never_falls_back(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        pl = FakePlan()
        got = fb.load_plan(tmp, plan_load=pl)
        self.assertEqual(pl.calls, [fb.PLAN_URL])
        self.assertEqual(len(got["periods"]), 5)
        path = os.path.join(tmp, fb.CACHE, fb.PLAN_CACHE)
        with open(path, "rb") as f:
            self.assertEqual(f.read(), PLAN_BLOB)
        self.assertEqual(fb.load_plan(tmp, plan_load=FakePlan(fail=True)).code, "fetch")   # 캐시로 대신하지 않는다
        self.assertEqual(fb.load_plan(tmp, plan_load=FakePlan(b"<html>moved</html>")).code, "table")
        self.assertEqual(fb.load_plan(tmp, plan_load=FakePlan(PLAN_BLOB + b"x" * fb.PLAN_MAX)).code, "fetch")
        with open(path, "rb") as f:
            self.assertEqual(f.read(), PLAN_BLOB)                                       # 깨진 응답은 캐시를 덮지 않는다
        with mock.patch.object(cf.urllib.request, "urlopen", side_effect=AssertionError("요청")):
            self.assertEqual(len(fb.load_plan(tmp, offline=True)["periods"]), 5)         # --offline은 캐시만
            self.assertEqual(fb.load_plan(os.path.join(tmp, "없음"), offline=True).code, "fetch")

    def test_plan_request_keeps_its_host_ua_and_shares_the_budget(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        seen = []

        class Resp(io.BytesIO):
            def __init__(self, body, url):
                super().__init__(body)
                self.url = url

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def geturl(self):
                return self.url

        def opener(req, timeout=None):
            seen.append((req.full_url, req.get_header("User-agent"), timeout))
            return Resp(PLAN_BLOB, "https://elsewhere.invalid/x")                       # 다른 곳으로 넘겨짐
        self.assertEqual(fb.load_plan(tmp, opener=opener).code, "fetch")
        self.assertEqual(seen, [(fb.PLAN_URL, cf.UA, cf.REQ_TIMEOUT)])
        self.assertEqual(urllib_split(fb.PLAN_URL)[:2], ("https", fb.PLAN_HOST))
        self.assertFalse(os.path.exists(os.path.join(tmp, fb.CACHE, fb.PLAN_CACHE)))
        seen.clear()
        self.assertEqual(fb.load_plan(tmp, opener=opener, budget=0.5).code, "fetch")    # 남은 예산이 없으면 요청하지 않는다
        self.assertEqual(seen, [])
        # main — 뉴욕 연은 두 요청이 OPS_BUDGET초를 함께 쓴다: 운영 결과에 쓴 만큼 계획 페이지의 예산이 준다
        t = [0.0]

        def clock():
            t[0] += 4.0
            return t[0]
        budgets = []
        real = fb.load_plan

        def spy(*a, **kw):
            budgets.append(kw["budget"])
            return real(*a, **kw)
        out = os.path.join(tmp, "data")
        with mock.patch.object(fb, "load_plan", spy), contextlib.redirect_stdout(io.StringIO()):
            fb.main(["--out", out, "--work", os.path.join(tmp, ".work")], fred_load=FakeFred(rmp_world()), now=NOW,
                    clock=clock, ops_load=FakeOps(), plan_load=FakePlan())
        self.assertEqual(len(budgets), 1)
        self.assertTrue(0 < budgets[0] < fb.OPS_BUDGET, budgets)

    def test_main_plan_failure_only_stales_its_item(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        out, work = os.path.join(tmp, "data"), os.path.join(tmp, ".work")
        run = lambda plan, now: fb.main(["--out", out, "--work", work], fred_load=FakeFred(rmp_world()), now=now,
                                        ops_load=FakeOps(), plan_load=plan)
        load = lambda: read_json(os.path.join(out, fb.FILE))["items"]
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            self.assertEqual(run(FakePlan(), NOW), 0)
            first = load()["rmp_plan"]
            self.assertEqual(run(FakePlan(fail=True), NOW + TD(days=1)), 0)
            items = load()
            r = items["rmp_plan"]
            self.assertEqual((r["ok"], r["stale"], r["error"], r["failed_since"], r["retrieved"], r["line"]),
                             (False, True, "수신 실패", "2026-10-31", "2026-10-30", first["line"]))   # 직전 값 + 받지 못함
            self.assertTrue(all(it["ok"] for k, it in items.items() if k != "rmp_plan"))
            self.assertEqual({w["bound"] for w in items["rmp"]["values"]["windows"]}, {"rule"})   # 그날 대조 창은 규칙
            self.assertEqual(run(FakePlan(b"<html>no table</html>"), NOW + TD(days=2)), 0)
            r = load()["rmp_plan"]
            self.assertEqual((r["stale"], r["error"], r["failed_since"]), (True, fb.REASONS["table"], "2026-10-31"))
        self.assertIn("::warning::연준 재무상태표 참고 rmp_plan 받지 못함: 수신 실패", buf.getvalue())
        self.assertNotIn("xyz-77", buf.getvalue() + json.dumps(load(), ensure_ascii=False))
        self.assertEqual(sorted(os.listdir(out)), [fb.FILE])                             # 받은 HTML은 공개 data에 없다

    def test_an_old_file_without_the_plan_or_bound_still_carries(self):
        # 2026-11-03 첫 공개의 fedbs.json — rmp 창에 bound가 없고 rmp_plan 칸이 없다. 규칙 날짜의 창이면 이어 싣는다
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        out, work = os.path.join(tmp, "data"), os.path.join(tmp, ".work")
        with contextlib.redirect_stdout(io.StringIO()):
            fb.main(["--out", out, "--work", work], fred_load=FakeFred(rmp_world()), now=NOW, ops_load=FakeOps(),
                    plan_load=FakePlan(fail=True))
            path = os.path.join(out, fb.FILE)
            js = read_json(path)
            self.assertEqual((js["items"]["rmp_plan"]["ok"], js["items"]["rmp_plan"]["stale"]), (False, False))
            self.assertNotIn("line", js["items"]["rmp_plan"])                            # 직전 값이 없으면 사유만
            for w in js["items"]["rmp"]["values"]["windows"]:
                del w["bound"]
            del js["items"]["rmp_plan"]
            js["order"].remove("rmp_plan")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(js, f, ensure_ascii=False)
            fb.main(["--out", out, "--work", work], fred_load=FakeFred(rmp_world()), now=NOW + TD(days=1),
                    ops_load=FakeOps(fail=True), plan_load=FakePlan())
        items = read_json(path)["items"]
        self.assertEqual((items["rmp"]["stale"], items["rmp"]["retrieved"]), (True, "2026-10-30"))
        self.assertEqual({w["bound"] for w in items["rmp"]["values"]["windows"]}, {"rule"})
        self.assertTrue(items["rmp_plan"]["ok"])
        moved = json.loads(json.dumps(js["items"]["rmp"]["values"]))
        moved["windows"][0]["from"] = "2026-07-15"                                      # 규칙 날짜가 아닌 옛 창은 그대로(걸린다)
        self.assertFalse(fb.values_ok(fb.BY_KEY["rmp"], fb._upgrade_rmp(moved), {}))
        self.assertIs(fb._upgrade_rmp(None), None)


def urllib_split(url):
    import urllib.parse
    return urllib.parse.urlsplit(url)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _t(w):
    return fb._t1(fb._t1(w["bn"]) - fb._t1(1.0))


class LicenceTest(unittest.TestCase):
    def test_series_list_is_fixed_and_checked(self):
        self.assertEqual(fb.SERIES, ["WRESBAL", "GDP", "WRBWFRBL", "WDTGAL", "WLRRAOL", "WLRRAFOIAL", "WSHOBL", "WSHONBNL",
                                     "WSHOMCB", "WCICL", "SOFR", "IORB", "RPONTTLD", "RRPONTSYD"])
        self.assertEqual(fb.LICENCE, {**{sid: "public-domain" for sid in fb.SERIES},
                                      "SOFR": "citation-required", "RPONTTLD": "citation-required",
                                      "RRPONTSYD": "citation-required"})
        self.assertFalse(set(fb.SERIES) & (set(rp.RESTRICTED) | set(ai.RESTRICTED)))
        self.assertIn("SOFR", rp.CITATION_REQUIRED)                                    # 규칙 카드와 같은 판단
        for spec in fb.ITEMS:
            self.assertLessEqual(set(spec["series"]), set(fb.SERIES))
        for sid in ("WRESBAL", "GDP", "SOFR"):                                        # 규칙 카드와 같은 인용
            self.assertEqual(fb.SOURCES[sid], (rp.FRED_SOURCE[sid], rp.FRED_TITLE[sid]))
        for sid in ("WRBWFRBL", "WDTGAL", "WSHOBL", "WSHONBNL"):                       # 지준·재정 카드와 같은 인용
            self.assertEqual(fb.SOURCES[sid], liq.SOURCES[sid])

    def test_citation_form(self):
        self.assertEqual(fb.citation("RPONTTLD", "2026-11-03"),
                         "Federal Reserve Bank of New York, Overnight Repurchase Agreements: Total Securities Purchased by the "
                         "Federal Reserve in the Temporary Open Market Operations [RPONTTLD], retrieved from FRED, Federal "
                         "Reserve Bank of St. Louis; https://fred.stlouisfed.org/series/RPONTTLD, November 3, 2026.")

    def test_new_york_fed_items_carry_the_notices(self):
        sp = fb.notices("spread", "2026-11-03")
        for t in (rp.SOFR_NOTICE, rp.SOFR_DTCC, rp.nyfed_attribution("2026"), rp.NOT_AFFILIATED, fb.SPREAD_DERIVED,
                  fb.SPREAD_DERIVED_EN):
            self.assertIn(t, sp)
        for key in ("srf", "rrp"):
            nt = fb.notices(key, "2027-01-04")
            self.assertIn(rp.nyfed_attribution("2027"), nt)
            self.assertIn(rp.NOT_AFFILIATED, nt)
            self.assertNotIn(rp.SOFR_NOTICE, nt)                                       # 참조금리 고지는 SOFR 칸만
        self.assertIn(fb.SRF_DERIVED, fb.notices("srf", "2026-11-03"))
        rm = fb.notices("rmp", "2027-01-04")                                             # 국채 운영 결과 — 수급 카드 딜러와 같은 꼴
        for t in (fb.RMP_DERIVED, fb.RMP_DERIVED_EN, rp.nyfed_attribution("2027"), rp.NOT_AFFILIATED):
            self.assertIn(t, rm)
        self.assertNotIn(rp.SOFR_NOTICE, rm)
        pl = fb.notices("rmp_plan", "2027-01-04")                                        # 공식 계획 — 옮긴 것이라는 표시(한·영)
        self.assertEqual(pl, [fb.PLAN_COPIED, fb.PLAN_COPIED_EN, rp.nyfed_attribution("2027"), rp.NOT_AFFILIATED])
        self.assertIn("국채 매입 운영 결과", rp.DATA_LICENSE)                               # 꼬리말의 뉴욕 연은 자료 목록
        self.assertIn("국채 매입 월 일정 계획 페이지 'Treasury Securities Operational Details'", rp.DATA_LICENSE)
        for key in ("reserves", "dec", "week"):
            self.assertFalse([t for t in fb.notices(key, "2026-11-03") if "New York" in t], key)
        self.assertIn("newyorkfed.org 이용약관", rp.DATA_LICENSE)
        self.assertRegex(rp.DATA_LICENSE, r"뉴욕 연은 자료\([^)]*상시 레포·익일물 역레포[^)]*\)는 newyorkfed\.org 이용약관")


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.out = os.path.join(self.tmp, "data")
        self.work = os.path.join(self.tmp, ".work")
        self.path = os.path.join(self.out, fb.FILE)
        self.S = world()

    def run_main(self, fred=None, now=NOW, extra=(), clock=None, ops=None, plan=None):
        fred = fred or FakeFred(self.S)
        buf = io.StringIO()
        kw = {"clock": clock} if clock else {}
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = fb.main(["--out", self.out, "--work", self.work, *extra], fred_load=fred, now=now,
                           ops_load=ops or FakeOps(), plan_load=plan or FakePlan(), **kw)
        return code, buf.getvalue()

    def saved(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def save(self, js):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(js, f, ensure_ascii=False)

    def test_first_run_writes_every_item(self):
        code, log = self.run_main()
        self.assertEqual(code, 0, log)
        js = self.saved()
        self.assertEqual(set(js), {"schema", "generated_at", "notice", "order", "items"})
        self.assertEqual(js["order"], ["reserves", "dec", "rmp_plan", "rmp", "spread", "srf", "rrp", "week"])
        for key, it in js["items"].items():
            self.assertTrue(it["ok"], key)
            want = {"ok", "stale", "error", "failed_since", "key", "name", "date", "values", "retrieved", "line", "extra",
                    "notices", "sources"} | ({"chart"} if key == "reserves" else set())
            self.assertEqual(set(it), want, key)
            self.assertEqual(it["retrieved"], "2026-10-30")
            self.assertEqual([s["series"] for s in it["sources"]],
                             fb.BY_KEY[key]["series"] + {"rmp": [fb.OPS], "rmp_plan": [fb.PLAN]}.get(key, []))
            for src in it["sources"]:
                if src["series"] in (fb.OPS, fb.PLAN):                                 # 뉴욕 연은에서 직접 — FRED가 아니다
                    self.assertEqual((src["licence"], src["url"], src["name"]),
                                     ("nyfed-terms", fb.OPS_URL if src["series"] == fb.OPS else fb.PLAN_URL,
                                      "Federal Reserve Bank of New York"))
                    self.assertEqual(src["citation"], {
                        fb.OPS: "Federal Reserve Bank of New York, Treasury Securities Operations, results summary, retrieved "
                                "from https://markets.newyorkfed.org/api/tsy/all/results/summary/search.json, October 30, 2026.",
                        fb.PLAN: "Federal Reserve Bank of New York, Treasury Securities Operational Details, retrieved from "
                                 "https://www.newyorkfed.org/markets/domestic-market-operations/monetary-policy-implementation/"
                                 "treasury-securities/treasury-securities-operational-details, October 30, 2026."}[src["series"]])
                    continue
                self.assertEqual(src["licence"], fb.LICENCE[src["series"]])
                self.assertTrue(src["citation"].startswith(fb.SOURCES[src["series"]][0]))
                self.assertTrue(src["citation"].endswith("October 30, 2026."))
        ch = js["items"]["reserves"]["chart"]
        self.assertEqual([ln["key"] for ln in ch["lines"]], ["res", "low"])
        self.assertEqual((ch["unit"], ch["threshold"]), ("bn", None))
        self.assertEqual(len(ch["lines"][0]["points"]), fb.CHART_WEEKS)
        self.assertNotIn("2,800", log)                                                 # 로그에는 날짜와 사유만
        self.assertNotIn("-80", log)

    def test_one_missing_series_only_stales_its_items(self):
        self.run_main()
        code, log = self.run_main(fred=FakeFred(self.S, fail={"WDTGAL"}), now=NOW + TD(days=1))
        self.assertEqual(code, 0, log)
        items = self.saved()["items"]
        d = items["dec"]
        self.assertEqual((d["ok"], d["stale"], d["error"], d["failed_since"]), (False, True, fb.REASONS["fetch"], "2026-10-31"))
        self.assertEqual(d["retrieved"], "2026-10-30")
        self.assertIn("재무부 현금(TGA) -30/-80", d["line"])                             # 직전 숫자에서 다시 만든 문구
        self.assertTrue(all(items[k]["ok"] for k in ("reserves", "rmp_plan", "rmp", "spread", "srf", "rrp", "week")))
        self.assertIn("::warning::연준 재무상태표 참고 dec 받지 못함", log)
        self.assertNotIn("xyz-77", log)
        self.run_main(fred=FakeFred(self.S, fail={"IORB", "WRESBAL"}), now=NOW + TD(days=2))
        items = self.saved()["items"]
        self.assertEqual({k for k, it in items.items() if not it["ok"]}, {"spread", "reserves", "week"})
        self.assertEqual(items["dec"]["failed_since"], None)                           # 다시 받으면 실패 날짜가 지워진다
        self.run_main(fred=FakeFred(self.S, fail={"IORB"}), now=NOW + TD(days=3))
        self.assertEqual(self.saved()["items"]["spread"]["failed_since"], "2026-11-01")  # 못 받기 시작한 날을 지킨다

    def test_first_failure_without_previous_has_no_numbers(self):
        self.run_main(fred=FakeFred(self.S, cache={"RRPONTSYD"}))
        it = self.saved()["items"]["rrp"]
        self.assertEqual((it["ok"], it["stale"], it["error"]), (False, False, fb.REASONS["cache"]))
        for k in ("line", "values", "notices", "chart"):
            self.assertNotIn(k, it)
        self.assertEqual([s["series"] for s in it["sources"]], ["RRPONTSYD"])

    def test_offline_reads_the_cache(self):
        cache = os.path.join(self.work, fb.CACHE)
        os.makedirs(cache)
        for sid, s in self.S.items():
            with open(os.path.join(cache, f"{sid}.csv"), "w", encoding="utf-8") as f:
                f.write("observation_date," + sid + "\n" + "".join(f"{d.isoformat()},{v}\n" for d, v in s))
        with open(os.path.join(cache, fb.OPS_CACHE), "wb") as f:
            f.write(OPS_BLOB)
        with open(os.path.join(cache, fb.PLAN_CACHE), "wb") as f:
            f.write(PLAN_BLOB)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), mock.patch.object(ai.urllib.request, "urlopen", side_effect=AssertionError("요청")):
            code = fb.main(["--out", self.out, "--work", self.work, "--offline"], now=NOW)
        self.assertEqual(code, 0, buf.getvalue())
        items = self.saved()["items"]
        self.assertTrue(all(it["ok"] for it in items.values()))
        self.assertAlmostEqual(items["dec"]["values"]["other13"], -20)
        self.assertEqual([w["bn"] for w in items["rmp"]["values"]["windows"]], [12.0, 8.0, 11.0, 4.2])   # 받아 둔 운영 결과
        self.assertEqual({w["bound"] for w in items["rmp"]["values"]["windows"]}, {"plan"})                # 받아 둔 계획의 기간
        self.assertEqual([w["reinvest"] for w in items["rmp_plan"]["values"]["windows"]], ["11.1", "12.2", "13.3", "9.0"])

    def test_online_fetch_goes_through_the_bounded_reader(self):
        bodies = {sid: ("observation_date," + sid + "\n" + "".join(f"{d.isoformat()},{v}\n" for d, v in s)).encode()
                  for sid, s in self.S.items()}

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read1(self, n=-1):
                return self.read(n)
        seen = []

        def opener(req, timeout=None):
            if isinstance(req, str):                                                    # FRED — 주소 글자만(머리글 없음)
                self.assertTrue(req.startswith("https://fred.stlouisfed.org/graph/fredgraph.csv?id="), req)
                sid = req.split("id=")[1]
                seen.append((sid, timeout))
                return Resp(bodies[sid])
            # 뉴욕 연은 — 이 프로젝트를 밝히는 User-Agent(credit_fetch와 같은 글, 이메일 없음), 요청 하나엔 min(10초, 남은 예산)
            self.assertEqual(req.get_header("User-agent"), cf.UA)
            self.assertNotIn("@", cf.UA)
            if req.full_url == fb.PLAN_URL:                                             # 공식 계획 페이지 — 쿼리 없음
                seen.append((fb.PLAN, timeout))
                r = Resp(PLAN_BLOB)
            else:
                self.assertEqual(req.full_url, fb.OPS_URL + "?startDate=2026-05-01&endDate=2026-10-30")
                seen.append((fb.OPS, timeout))
                r = Resp(OPS_BLOB)
            r.geturl = lambda: req.full_url
            return r
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = fb.main(["--out", self.out, "--work", self.work], now=NOW, opener=opener)
        self.assertEqual(code, 0, buf.getvalue())
        self.assertEqual([s for s, _ in seen], fb.SERIES + [fb.OPS, fb.PLAN])           # FRED 시리즈마다 한 번 + 뉴욕 연은 두 번
        self.assertTrue(all(0 < t <= ai.TIMEOUT for _, t in seen))
        self.assertTrue(all(0 < t <= cf.REQ_TIMEOUT for _, t in seen[-2:]))
        with open(os.path.join(self.work, fb.CACHE, fb.PLAN_CACHE), "rb") as f:
            self.assertEqual(f.read(), PLAN_BLOB)                                       # 계획 페이지 원문도 캐시에(공개 data 밖)
        self.assertEqual(os.listdir(self.out), [fb.FILE])
        self.assertTrue(os.path.exists(os.path.join(self.work, fb.CACHE, "WSHOMCB.csv")))
        with open(os.path.join(self.work, fb.CACHE, fb.OPS_CACHE), "rb") as f:
            self.assertEqual(f.read(), OPS_BLOB)                                        # 받은 원문을 캐시에
        self.assertTrue(self.saved()["items"]["rmp"]["ok"])
        self.assertTrue(self.saved()["items"]["rmp_plan"]["ok"])

    def test_requests_carry_no_custom_headers(self):
        # FRED는 사용자 정의 User-Agent를 붙이면 응답을 멈춘다 — 이 파일은 주소 글자만 넘기고 Request 객체·머리글을 만들지
        # 않는다. 뉴욕 연은 요청만 credit_fetch.fetch_bytes(이 프로젝트를 밝히는 UA)로 — 실제 머리글은 위 opener 테스트가 본다
        with open(os.path.join(SCRIPTS, "fedbs_fetch.py"), encoding="utf-8") as f:
            src = f.read()
        code = re.sub(r'(?s)^#![^\n]*\n""".*?"""', "", src)                         # 머리말은 뺀다(설명에 이름이 나온다)
        code = re.sub(r"#[^\n]*", "", code)
        for tok in ("User-Agent", "Request(", "headers", "urlopen"):
            self.assertNotIn(tok, code)
        self.assertEqual(code.count("cf.fetch_bytes("), 2)
        self.assertIn("fetch_bytes(url, OPS_HOST,", code)
        self.assertIn("fetch_bytes(PLAN_URL, PLAN_HOST,", code)

    def test_older_data_is_not_taken(self):
        self.run_main()
        short = dict(self.S, SOFR=self.S["SOFR"][:-1])
        self.run_main(fred=FakeFred(short), now=NOW + TD(days=1))
        it = self.saved()["items"]["spread"]
        self.assertEqual((it["ok"], it["stale"], it["error"]), (False, True, fb.REASONS["older"]))
        self.assertEqual(it["date"], "2026-10-30")
        short = dict(self.S, GDP=self.S["GDP"][:-1])                                    # 칸 날짜는 그대로, GDP 분기만 이르다
        self.run_main(fred=FakeFred(short), now=NOW + TD(days=2))
        self.assertEqual(self.saved()["items"]["reserves"]["error"], fb.REASONS["older"])

    def test_same_numbers_keep_the_file(self):
        self.run_main()
        with open(self.path, "rb") as f:
            first = f.read()
        self.run_main(now=NOW + TD(days=1))
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), first)

    def test_a_new_week_compares_the_denominator_with_the_last_file(self):
        S = world(last_wed=D(2026, 10, 21), last_day=D(2026, 10, 23))
        S["GDP"] = S["GDP"][:-1]                                                        # 10-21 주엔 2026Q2 GDP 30,000까지
        self.run_main(fred=FakeFred(S), now=datetime.datetime(2026, 10, 22, 22, 30, tzinfo=datetime.timezone.utc))
        r = self.saved()["items"]["reserves"]
        self.assertEqual((r["date"], r["values"]["denom_pp"]), ("2026-10-21", None))   # 처음 싣는 주엔 견줄 것이 없다
        self.run_main(now=NOW)                                                          # 10-28 주, 2026Q3 GDP 32,000
        r = self.saved()["items"]["reserves"]
        self.assertEqual((r["date"], r["retrieved"], r["values"]["base_quarter"]), ("2026-10-28", "2026-10-30", "2026-04-01"))
        self.assertAlmostEqual(r["values"]["denom_pp"], 2800 / 32000 * 100 - 2800 / 30000 * 100, places=6)
        self.assertIn("분모 바뀜 -0.58%p (GDP 2026Q2에서 2026Q3로)", r["line"])
        self.run_main(now=NOW + TD(days=1))                                             # 같은 주 다음 날 — 견줌을 그대로
        r2 = self.saved()["items"]["reserves"]
        self.assertEqual((r2["line"], r2["retrieved"]), (r["line"], "2026-10-30"))
        self.run_main(fred=FakeFred(self.S, fail={"GDP"}), now=NOW + TD(days=2))      # 이어 실을 때도 문구 그대로
        self.assertEqual(self.saved()["items"]["reserves"]["line"], r["line"])

    def test_a_gdp_change_inside_a_week_shows_on_the_next_week(self):
        # 검토 F1(site): 10-21 주를 2분기 GDP로 처음 싣고 → 같은 주에 3분기 GDP가 들어옴 → 10-28 주가 분모 바뀜을 싣는다
        S = world(last_wed=D(2026, 10, 21), last_day=D(2026, 10, 23))
        S["GDP"] = S["GDP"][:-1]
        self.run_main(fred=FakeFred(S), now=datetime.datetime(2026, 10, 22, 22, 30, tzinfo=datetime.timezone.utc))
        S2 = world(last_wed=D(2026, 10, 21), last_day=D(2026, 10, 23))
        self.run_main(fred=FakeFred(S2), now=datetime.datetime(2026, 10, 23, 22, 30, tzinfo=datetime.timezone.utc))
        r = self.saved()["items"]["reserves"]
        self.assertEqual((r["date"], r["values"]["gdp_quarter"], r["values"]["first_quarter"]),
                         ("2026-10-21", "2026-07-01", "2026-04-01"))
        self.run_main(now=NOW)                                                          # 10-28 주
        r = self.saved()["items"]["reserves"]
        self.assertIn("분모 바뀜 -0.58%p (GDP 2026Q2에서 2026Q3로)", r["line"])
        self.run_main(now=NOW + TD(days=7))                                             # 같은 숫자의 다음 실행 — 그대로
        self.assertIn("분모 바뀜 -0.58%p", self.saved()["items"]["reserves"]["line"])

    def test_a_broken_previous_file_is_not_carried(self):
        self.run_main()
        js = self.saved()
        js["items"]["week"]["values"]["fomc"] = ["어제"]                                # 날짜 꼴이 아니다
        js["items"]["dec"]["values"]["res4"] = None                                     # 창의 숫자가 반만 있다
        js["items"]["spread"]["values"]["pos"] = 9                                      # n보다 크다
        js["items"]["reserves"]["chart"]["lines"][0]["points"][0][1] = "9"              # 그래프 점이 숫자가 아니다
        js["items"]["rrp"]["values"]["tag"] = "<b>"                                     # 정해 둔 표시가 아니다
        js["items"]["srf"]["values"]["extra"] = 1.0                                     # 모르는 값
        js["items"]["rmp"]["values"]["windows"][0]["rmp_bn"] = 99.9                     # 매입 − 상환과 다르다
        js["items"]["rmp_plan"]["values"]["windows"][0]["rmp"] = "열"                    # 숫자 글이 아니다
        self.save(js)
        self.run_main(fred=FakeFred(self.S, fail=set(self.S)), now=NOW + TD(days=1), ops=FakeOps(fail=True),
                      plan=FakePlan(fail=True))
        items = self.saved()["items"]
        for key in fb.BY_KEY:
            self.assertEqual((items[key]["ok"], items[key]["stale"]), (False, False), key)
            self.assertNotIn("line", items[key])
        self.assertNotIn("어제", json.dumps(self.saved(), ensure_ascii=False))

    def test_carried_text_is_rebuilt_from_numbers(self):
        self.run_main()
        js = self.saved()
        for it in js["items"].values():
            it["line"] = "<b>원문 오류 https://bad.invalid</b>"
            it["extra"] = ["매수"]
            it["notices"] = ["바깥 글"]
            it["name"] = "바뀐 이름"
        js["items"]["reserves"]["chart"]["note"] = "바깥 글"
        self.save(js)
        self.run_main(fred=FakeFred(self.S, fail=set(self.S)), now=NOW + TD(days=1), ops=FakeOps(fail=True),
                      plan=FakePlan(fail=True))
        dump = json.dumps(self.saved(), ensure_ascii=False)
        for bad in ("bad.invalid", "매수", "바깥 글", "바뀐 이름"):
            self.assertNotIn(bad, dump)
        self.assertTrue(all(it["stale"] for it in self.saved()["items"].values()))

    def test_previous_checks_the_schema(self):
        good = {"reserves": {"key": "reserves"}, "dec": {"key": "dec"}}
        os.makedirs(self.out)
        for js, want in (({"schema": fb.SCHEMA, "items": good}, good),
                         ({"schema": fb.SCHEMA + 1, "items": good}, {}),
                         ({"items": good}, {}),
                         ({"schema": fb.SCHEMA, "items": [good]}, {}),
                         ([good], {}),
                         ({"schema": fb.SCHEMA, "items": dict(good, zzz={"key": "zzz"}, week="x")}, good)):
            self.save(js)
            self.assertEqual(fb.previous(self.out), want, js)
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{깨진")
        self.assertEqual(fb.previous(self.out), {})

    def test_budget_runs_out_without_waiting(self):
        t = [0.0]

        def clock():
            t[0] += 15.0
            return t[0]
        fred = FakeFred(self.S)
        code, log = self.run_main(fred=fred, clock=clock)
        self.assertLess(len(fred.calls), len(fb.SERIES))
        self.assertTrue(all(1 <= tmo <= ai.TIMEOUT for _, tmo in fred.calls))
        self.assertIn("::warning::", log)

    def test_nothing_fetched_exits_1(self):
        code, log = self.run_main(fred=FakeFred(self.S, fail=set(self.S)), ops=FakeOps(fail=True), plan=FakePlan(fail=True))
        self.assertEqual(code, 1, log)
        self.assertTrue(all(not it["ok"] for it in self.saved()["items"].values()))

    def test_a_calculation_error_fails_only_its_item(self):
        with mock.patch.dict(fb.BY_KEY["srf"], calc=mock.Mock(side_effect=ZeroDivisionError("원문"))):   # ITEMS와 같은 dict
            code, log = self.run_main()
        self.assertEqual(code, 0, log)
        items = self.saved()["items"]
        self.assertEqual((items["srf"]["ok"], items["srf"]["error"]), (False, fb.REASONS["format"]))
        self.assertTrue(items["rrp"]["ok"])
        self.assertNotIn("원문", log)

    def test_the_write_is_atomic(self):
        self.run_main()
        with open(self.path, "rb") as f:
            before = f.read()
        with mock.patch.object(ai.os, "replace", side_effect=OSError("disk full")):
            S = dict(self.S, RRPONTSYD=self.S["RRPONTSYD"] + [(D(2026, 11, 2), 4.0)])
            code, log = self.run_main(fred=FakeFred(S), now=NOW + TD(days=3))
        self.assertEqual(code, 1, log)
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), before)
        self.assertEqual(os.listdir(self.out), [fb.FILE])

    def test_every_string_is_fixed_text_without_verdict_words(self):
        odd = plan_html([("7/14/2026 - 8/13/2026", plan_text("11.1", "5")),             # 형식 모름·깨진 날짜·지금 창 없음
                         ("8/14/2026 - 9/14/2026", "The Desk plans to conduct small value operations of approximately $150 "
                                                   "million over the monthly period."),
                         ("9/15/2026 - 13/40/2026", plan_text("13.3")), ("10/15/2026 - 11/13/2026", plan_text("9.0"))])
        runs = [(FakeFred(self.S, fail={"IORB"}), NOW, FakeOps(fail=True), FakePlan(fail=True)),   # 직전 값 없는 첫 실패
                (FakeFred(self.S), NOW + TD(days=1), FakeOps(), FakePlan()),
                (FakeFred(self.S, fail={"WRESBAL", "WSHOMCB"}), NOW + TD(days=2), FakeOps(), FakePlan(odd)),   # 이어 싣기·상환 비움
                (FakeFred(self.S, cache={"SOFR"}), NOW + TD(days=3), FakeOps(fail=True), FakePlan(fail=True))]
        urls, errors = set(), set()
        for fred, now, ops, plan in runs:                                               # 실행마다 파일 전체를 본다
            self.run_main(fred=fred, now=now, ops=ops, plan=plan)
            dump = json.dumps(self.saved(), ensure_ascii=False)
            body = dump
            for ok in TOPIC:
                body = body.replace(ok, "")
            for word in list(FORBIDDEN_TEXT) + list(VERDICT):
                self.assertNotIn(word, body, word)
            urls |= {u.rstrip(".") for u in re.findall(r"https?://[^\s,;)\"]+", dump)}
            self.assertNotIn("bad.invalid", dump)
            self.assertNotIn("@", dump)
            errors |= {it["error"] for it in self.saved()["items"].values()} - {None}
            nested = re.compile(r"\([^()]*\(")                                         # 겹 괄호 없음('미수신(까닭)'이 겹치지 않게)
            for t in re.findall(r'"((?:[^"\\]|\\.)*)"', dump):
                self.assertIsNone(nested.search(t), t)
        self.assertEqual(urls, {f"https://fred.stlouisfed.org/series/{sid}" for sid in fb.SERIES} | {fb.OPS_URL, fb.PLAN_URL})
        self.assertEqual(errors, {fb.REASONS["fetch"], fb.REASONS["cache"]})          # 정해 둔 문구만


class StaticTest(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
            return f.read()

    def test_workflow_fetches_without_failing_the_run(self):
        wf = self.read(".github", "workflows", "daily.yml")
        self.assertTrue("id: fedbs" in wf, "daily.yml에 연준 재무상태표 단계(id: fedbs) 없음")
        step = wf[wf.index("id: fedbs"):]
        self.assertIn("continue-on-error: true", step[:200])
        self.assertIn("timeout-minutes: 2", step[:200])
        self.assertIn("python scripts/fedbs_fetch.py", step[:300])
        self.assertLess(wf.index("id: liquidity"), wf.index("id: fedbs"))               # 지준·재정 바로 뒤
        self.assertLess(wf.index("id: fedbs"), wf.index("id: tp"))
        self.assertLess(wf.index("id: fedbs"), wf.index("공개 전 검사(새 산출물 포함)"))
        self.assertLess(wf.index("id: fedbs"), wf.index("git add data"))
        self.assertNotIn("fedbs", wf[wf.index("\n  alert:"):])                           # 실패해도 알림을 띄우지 않는다
        self.assertIn("node --test scripts/test_fedbs_render.cjs", wf[wf.index("\n  check:"):wf.index("\n  update:")])
        # 갱신 잡의 상한 주석 — 참고 단계 제한의 합(2분짜리 단계 수 × 2 + 한국 4)
        m = re.search(r"timeout-minutes: (\d+) +# 참고 자료 단계 제한의 합\((.*?) = (\d+)분\)", wf)
        self.assertIsNotNone(m)
        parts = [int(x) for x in re.findall(r"(\d+)(?= \+| =|$)", m.group(2))]
        self.assertEqual(sum(parts), int(m.group(3)))
        upd = wf[wf.index("\n  update:"):wf.index("\n  deploy:")]
        steps = re.findall(r"^ {8}timeout-minutes: (\d+)", upd, flags=re.M)          # 단계(들여쓰기 8칸)만 — 잡의 상한은 빼고
        self.assertEqual(sum(int(x) for x in steps), int(m.group(3)))                  # 주석의 합 = 실제 단계 제한의 합
        self.assertLess(int(m.group(3)), int(m.group(1)))

    def test_readme_counts_and_section(self):
        readme = self.read("README.md")
        m = re.search(r"\*\*아침 쪽 Python 테스트 (\d+)개 \+ node 테스트 (\d+)개\*\*\((.*?)\)와 \*\*저녁판", readme)
        py_part, node_part = m.group(3).split(" / node: ")
        mine = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()
        self.assertRegex(py_part, rf"(^| · )연준 재무상태표 참고 {mine}( · |$)")
        cjs = len(re.findall(r"^test\(", self.read("scripts", "test_fedbs_render.cjs"), flags=re.M))
        self.assertRegex(node_part, rf"(^| · )연준 재무상태표 카드 그리기 {cjs}( · |$)")
        self.assertIn("## 참고: 연준 재무상태표", readme)
        sec = readme[readme.index("## 참고: 연준 재무상태표"):]
        sec = sec[:sec.index("\n## ", 5)]
        for sid in fb.SERIES:
            self.assertIn(f"`{sid}`", sec, sid)
        self.assertIn("python -X utf8 scripts/fedbs_fetch.py", readme)
        self.assertIn("node --test scripts/test_fedbs_render.cjs", readme)

    def test_page_wires_the_card(self):
        page = self.read("site", "index.html")
        for snippet in ('getJson("data/fedbs.json")', '<script src="fedbs.js"></script>',
                        '<a href="data/fedbs.json">', 'id:"fedbs-slot"', "window.FedBsCard.render("):
            self.assertTrue(snippet in page, f"index.html에 {snippet} 없음")
        group = page[page.index('g.id === "liquidity" ? el("div", {id:"liquidity-slot"'):][:300]   # 유동성 묶음, 지준·재정 바로 뒤
        self.assertIn('g.id === "liquidity" ? el("div", {id:"fedbs-slot", class:"oil-slot"})', group)
        self.assertLess(page.index('<script src="charts.js"></script>'), page.index('<script src="fedbs.js"></script>'))
        line = next(l for l in page.splitlines() if "window.FedBsCard.render(" in l)
        self.assertRegex(line, r"^\s*try \{ if \(isObj\(fbs\) && window\.FedBsCard\)")   # 깨져도 그 카드만 빠진다

    def test_page_names_the_new_york_fed_operations_source(self):
        # '출처와 자료 상태'의 'FRED 밖의 공개 자료' — RMP 두 줄(공식 계획 페이지·Markets API 운영 결과)은 뉴욕 연은에서 직접
        # 받는다(카드의 출처 줄과 같은 뜻)
        page = self.read("site", "index.html")
        art = page[page.index("<h3>FRED 밖의 공개 자료</h3>"):]
        art = art[:art.index("</article>")]
        for word in ("지준 관리 매입(RMP) 두 줄은 뉴욕 연은에서 직접 받습니다", "'Treasury Securities Operational Details' 페이지",
                     "정해 둔 꼴만 옮긴", "계획이지 실제 매입이 아닙니다", "Markets API(markets.newyorkfed.org)의 국채 운영 결과",
                     "newyorkfed.org 이용약관", "공식 수치가 아닙니다", "'연준 대차대조표 정책 — 1차 출처' 칸"):
            self.assertIn(word, art)
        self.assertNotIn("<a ", art)
        self.assertNotIn("RMP) 추정 줄", page)                                           # 옛 이름
        fred = page[page.index("<h3>미국 공개 자료 (FRED 경유)</h3>"):]
        fred = fred[:fred.index("</article>")]
        self.assertIn("RMP) 공식 계획·대조 줄은 FRED 밖, 아래", fred)

    def test_limits_say_what_the_official_page_and_wshomcb_hold(self):
        # 2026-11-03 검토: 공식 계획 나눔은 정적 HTML·CSV에 있다('스크립트로 그려져 받지 않는다'가 아니다), WSHOMCB = 기관 MBS +
        # 기관 CMBS(빠지는 것은 기관채뿐) — 화면 글·머리말·README가 같은 뜻이고 옛 문장이 남지 않는다. 같은 날 공식 계획을 싣게
        # 되며(사용자 결정 '앞에 2개 실행') '이 카드는 받지 않는다' 문장도 없어졌다
        readme = self.read("README.md")
        row = next(l for l in readme.splitlines() if l.startswith("| 지준 관리 매입(RMP) 대조"))
        plan_row = next(l for l in readme.splitlines() if l.startswith("| 지준 관리 매입(RMP) 공식 계획"))
        for text in (fb.RMP_LIMITS, fb.__doc__, row, plan_row):
            for gone in ("스크립트로 그려", "기관채·CMBS", "이 카드는 그것을 받지 않는다", "카드는 받지 않", "이 카드는 받지 않"):
                self.assertNotIn(gone, text)
            self.assertIn("Treasury Securities Operational Details", text)
        for text in (fb.RMP_LIMITS, fb.__doc__, row):
            for word in ("전달 실제 상환", "기관 CMBS"):
                self.assertIn(word, text)
        for text in (fb.RMP_METHOD, fb.__doc__, row):
            self.assertIn("성탄이 수요일인 해", text)
        for text in (fb.__doc__, plan_row):                                             # 읽는 꼴·형식 모름·계획이라는 것
            flat = " ".join(text.split())                                               # 머리말은 줄을 바꿔 쓴다
            for word in ("no reserve management purchases", "reinvestment purchases", "형식 모름", "계획"):
                self.assertIn(word, flat)

    def test_card_intro_is_one_register_and_covers_the_notice(self):
        js = self.read("site", "fedbs.js")
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        self.assertNotIn("d.notice", code)
        self.assertIn('el("p", { class: "muted" }, ABOUT)', code)
        about = "".join(re.findall(r'"([^"]*)"', code[code.index("const ABOUT = "):].split(";\n", 1)[0]))
        for sent in filter(None, re.split(r"(?<=\.)\s+", about)):
            self.assertTrue(sent.endswith("니다."), sent)
        for mine, theirs in (("규칙 수에 들지 않습니다", "규칙 점검에 쓰지 않는"),
                             ("뉴욕 연은 월 일정 공지의 계획 금액을 싣고, 국채 매입 운영 결과로 거꾸로 셈한 대조 줄을 함께 둡니다",
                              "뉴욕 연은 월 일정 공지의 계획 금액을 싣고, 국채 매입 운영 결과로 거꾸로 셈한 대조 줄을 함께 둔다"),
                             ("계획은 계획이고 대조 줄은 공식 수치가 아닙니다", "계획은 계획이고 대조 줄은 공식 수치가 아니다"),
                             ("H.4.1 주간 대차대조표와 단기자금 시장의 공개 통계", "H.4.1 주간 대차대조표와 단기자금 시장의 공개 통계"),
                             ("'지준과 통화승수'의 지준/GDP와 지준·재정 카드의 13주 나눔을 주간으로 읽는 재료",
                              "'지준과 통화승수'의 지준/GDP와 지준·재정 카드의 13주 나눔을 주간으로 읽는 재료"),
                             ("금리나 자금 여건을 예측하지 않습니다", "금리나 자금 여건을 예측하지 않는다")):
            self.assertIn(mine, about)
            self.assertIn(theirs, fb.NOTICE)

    def test_screen_script_matches_the_file_and_avoids_verdict_words(self):
        js = self.read("site", "fedbs.js")
        card = re.findall(r'"(\w+)"', js[js.index("const CARD = ["):].split("]")[0])
        self.assertEqual(card, [s["key"] for s in fb.ITEMS])
        self.assertIn(f'const OPS = "{fb.OPS}";', js)
        self.assertIn(f'const PLAN = "{fb.PLAN}";', js)
        self.assertIn('const OPTIONAL = ["rmp_plan", "rmp"];', js)
        reasons = re.findall(r'"([^"]+)"', js[js.index("const REASONS = ["):].split("];")[0])
        self.assertEqual(reasons, list(fb.REASONS.values()))
        self.assertIn('const LABEL = "참고 — 예측 아님";', js)
        self.assertIn('"연준 재무상태표(H.4.1 주간)"', js)
        for tok in ("innerHTML", "outerHTML", "insertAdjacentHTML", "createElement", "fetch(", "eval(", "location.",
                    "localStorage", "<img", "src=", "href"):
            self.assertNotIn(tok, js)
        body = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        for ok in TOPIC:
            body = body.replace(ok, "")
        for word in list(FORBIDDEN_TEXT) + list(VERDICT):
            self.assertNotIn(word, body, word)
        self.assertIn('getElementById("fedbs-slot")', js)
        self.assertIn("window.FedBsCard = ", js)

    def test_policy_quotes_match_the_checked_primary_text(self):
        # 정책 사실 칸(접힌 읽는 법 밖) — 2026-11-03 연준·뉴욕 연은 원문(보도자료 monetary20251029a · a1 · 20251210a ·
        # 20261028a, 뉴욕 연은 운영 방침 251210a, 의장 기자회견 예비 녹취록)에서 옮긴 그대로 — 글자를 바꾸지 않는다
        js = self.read("site", "fedbs.js")
        flat = "".join(re.findall(r'"([^"]*)"', js[js.index("const POLICY = ["):].split("\n  ];", 1)[0]))
        for quote in ("The Committee decided to conclude the reduction of its aggregate securities holdings on December 1.",
                      "Beginning on December 1, reinvest all principal payments from the Federal Reserve's holdings of agency "
                      "securities into Treasury bills.",
                      "will initiate purchases of shorter-term Treasury securities as needed to maintain an ample supply of "
                      "reserves on an ongoing basis.",
                      "on or around the ninth business day of each month",
                      "the pace of total purchases will likely be significantly reduced",
                      "The Committee is continuing its policy of maintaining ample reserves in the banking system.",
                      "will be fed into the FOMC probably early in the first quarter, but don't hold me exactly to that timing.",
                      "federalreserve.gov/newsevents/pressreleases/monetary20251029a.htm", "monetary20251029a1.htm",
                      "federalreserve.gov/newsevents/pressreleases/monetary20251210a.htm",
                      "federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm",
                      "newyorkfed.org/markets/opolicy/operating_policy_251210a",
                      "federalreserve.gov/mediacenter/files/FOMCpresconf20261028.pdf",
                      "2025-12-01", "3-3/4~4%", "약 $40bn", "2027년 1분기 초쯤", "단정하지 않았습니다"):
            self.assertIn(quote, flat)
        self.assertNotIn("https://", flat)                                              # 주소는 글자로(링크 아님)
        self.assertIn('const POLICY_HEAD = "연준 대차대조표 정책 — 1차 출처";', js)
        self.assertIn('const POLICY_ASOF = "2026-11-03";', js)                          # 사람이 고치는 고정 글의 기준일
        self.assertIn("자동으로 갱신하지 않습니다", js)
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        self.assertLess(code.index("...CARD.map(k => row(items[k], k))"), code.index("policy(),"))   # 줄 뒤, 접힌 읽는 법 앞
        self.assertLess(code.index("policy(),"), code.index('el("details"'))
        guide = js[js.index("const GUIDE = ["):js.index("const POLICY_HEAD")]
        for gone in ("conclude the reduction", "will initiate purchases", "8·9월 창", "늘려 잡"):   # 정책 사실·손 셈은 GUIDE에 두 번 없다
            self.assertNotIn(gone, guide)
        self.assertIn("'연준 대차대조표 정책 — 1차 출처' 칸", guide)                       # GUIDE는 가리키기만
        self.assertIn("'공식 계획' 줄", guide)
        self.assertIn("대조 줄", guide)
        self.assertNotIn("RMP 추정", js)                                                 # 옛 이름(추정 줄)이 화면 글에 없다
        fomc = "".join(re.findall(r'"([^"]*)"', js[js.index('["FOMC 뒤 첫 H.4.1"'):].split("]", 1)[0]))
        for word in ("2026-10-28 갱신", "확정되기 전까지 잠정", "FOMCpresconf20261028", "14:00 미 동부"):
            self.assertIn(word, fomc)
        self.assertNotIn("2차 보도", fomc)

if __name__ == "__main__":
    unittest.main(verbosity=1)
