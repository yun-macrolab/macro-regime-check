#!/usr/bin/env python3
"""하이퍼스케일러 조달 참고 자료(sec_fetch) 테스트 — 지어낸 XBRL 꼴 자료(가짜 회사 둘·가짜 응답·가짜 시계)로.

누적(YTD) → 분기(회계연도 6월·5월 말, 4분기 = 연간 − 9개월), 정정 공시, TTM 연속 요건, 0 채움, 대체 태그·더하는 부분,
금융리스 원금, 필수 줄의 앞 누적 없는 누적·같은 날 대체 태그, 5사 합(비공개 원본 sec_capex의 테스트를 옮긴 것),
조달 흐름(달력 분기 맞춤 — 5월 말 회계연도는 한 달 앞선 분기, 5사 완전 분기, 연속 감소 셈의 끊김·같은 값·상한, 외부 조달
몫은 모든 회사가 알 때만, 자사주 매입 0·매입·모름, 1년 전), 재무상태 잔액(시점 사실만, 늦게 낸 것, 첫 줄 필수·뒤 줄 0 채움·
받지 못한 줄은 모름, 1년 전 355~375일·365일에 가까운 것, 리스·수주잔고는 잔액 날짜 이하, 합의 요건),
연락처(환경 변수에서만·sec.gov https에만 — urllib이 붙는 호스트로 보고 '@'·역슬래시·포트 꼼수 거절, 실제 옮김 경로도 —
어디에도 쓰지 않음, 쓰기·로그 직전 검사로 섞인 글은 그 칸만 정해 둔 사유로),
받기(간격·시간 상한·흐름 먼저 그다음 잔액·실패 종류·칸마다 따로 실패·SEC 거절이면 모두 멈춤), 직전 파일 이어 싣기, 문구 원칙.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요. 숫자·회사·연락처는 모두 지어낸 것이다.
"""
import os, sys, io, re, json, gzip, shutil, calendar, datetime, tempfile, unittest, contextlib, email.message, urllib.error, \
    urllib.parse, urllib.request
from unittest import mock

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import sec_fetch as sf
from test_render_public import FORBIDDEN_TEXT

D = datetime.date
TODAY = D(2026, 10, 30)
NOW = datetime.datetime(2026, 10, 30, 1, 30, tzinfo=datetime.timezone.utc)
B = 1e9
FAKE_UA = "Test Org fake.tester@example.invalid"          # 지어낸 연락처 — 어디에도 쓰이면 안 된다
AT = chr(64)                                              # 사용자 정보 꼴 주소를 소스에 이메일 꼴 글로 두지 않게
VERDICT = ("판정", "충족", "신호", "경보", "전망", "매수", "매도", "⚠", "강세", "약세", "호재", "악재", "우려", "부담",
           "상승", "하락", "→")


def month_end(y, m):
    while m > 12:
        y, m = y + 1, m - 12
    return D(y, m, calendar.monthrange(y, m)[1])


def ytd(fy_end_month, fy_year, qvals, filed="2026-01-01", form10q="10-Q", form10k="10-K"):
    """회계연도 하나(fy_year에 끝남)의 누적 사실 — 3개월·6개월·9개월·연간. qvals = 네 분기 값(None이면 거기까지)."""
    start = month_end(fy_year - 1, fy_end_month) + datetime.timedelta(days=1)
    out, acc = [], 0
    for i, v in enumerate(qvals):
        if v is None:
            break
        acc += v
        end = month_end(start.year, start.month + 3 * (i + 1) - 1)
        out.append({"start": start.isoformat(), "end": end.isoformat(), "val": acc, "filed": filed,
                    "form": form10k if i == 3 else form10q, "fy": fy_year, "fp": "FY" if i == 3 else f"Q{i + 1}"})
    return out


def concept(*facts):
    return {"cik": 1, "tag": "x", "units": {"USD": [f for fs in facts for f in (fs if isinstance(fs, list) else [fs])]}}


# 지어낸 회사 둘 — 6월 말 회계연도(가)·5월 말(나). 태그 이름은 실제 꼴, 값은 지어낸 것.
CO_A = ("TSTA", "가회사", "0000000011", 6, {
    "ocf": [[sf.OCF]], "capex": [[sf.PPE]], "flease": [[sf.FLPP]],
    "debt_iss": [["ProceedsFromDebtA", "ProceedsFromDebtB"]], "debt_rep": [["RepaymentsX"]],
    "eq_iss": [[sf.EQ], [sf.CVPREF]], "buyback": [[sf.BUYBACK]]})
CO_B = ("TSTB", "나회사", "0000000022", 5, {
    "ocf": [[sf.OCF]], "capex": [[sf.PPE]], "flease": [[sf.FLPP]],
    "debt_iss": [], "debt_rep": [], "eq_iss": [], "buyback": [[sf.BUYBACK]]})


def concepts_a():
    """가회사: 회계연도 2025·2026·2027 1분기(2026-09). 분기 영업현금 10·11·12·13 / 14·15·16·17 / 18."""
    return {
        sf.OCF: concept(ytd(6, 2025, [10 * B, 11 * B, 12 * B, 13 * B]), ytd(6, 2026, [14 * B, 15 * B, 16 * B, 17 * B]),
                        ytd(6, 2027, [18 * B])),
        sf.PPE: concept(ytd(6, 2025, [5 * B, 5 * B, 6 * B, 6 * B]), ytd(6, 2026, [8 * B, 9 * B, 10 * B, 12 * B]),
                        ytd(6, 2027, [20 * B])),
        sf.FLPP: concept(ytd(6, 2026, [1 * B, 1 * B, 1 * B, 1 * B]), ytd(6, 2027, [2 * B])),
        # 차입 발행 — 앞 회계연도는 A 태그, 뒤는 B 태그. 2026 회계연도는 9개월·연간에만 줄이 있다(앞 분기 0)
        "ProceedsFromDebtA": concept(ytd(6, 2025, [3 * B, 0, 0, 0])),
        "ProceedsFromDebtB": concept([f for f in ytd(6, 2026, [0, 0, 4 * B, 6 * B]) if f["fp"] in ("Q3", "FY")],
                                     ytd(6, 2027, [5 * B])),
        "RepaymentsX": None,                                                   # 쓰지 않는 태그(404)
        sf.EQ: concept(ytd(6, 2026, [1 * B, 1 * B, 1 * B, 1 * B]), ytd(6, 2027, [1 * B])),
        sf.CVPREF: concept(ytd(6, 2027, [10 * B])),                          # 이번 분기에만
        sf.BUYBACK: concept(ytd(6, 2026, [2 * B, 2 * B, 2 * B, 2 * B]), ytd(6, 2027, [3 * B])),
    }


def concepts_b():
    """나회사: 5월 말 회계연도 2026·2027 1분기(2026-08). 설비투자가 영업현금보다 크다."""
    return {
        sf.OCF: concept(ytd(5, 2026, [5 * B, 5 * B, 5 * B, 5 * B]), ytd(5, 2027, [6 * B])),
        sf.PPE: concept(ytd(5, 2026, [6 * B, 7 * B, 8 * B, 9 * B]), ytd(5, 2027, [10 * B])),
        sf.FLPP: None,
        sf.BUYBACK: concept(ytd(5, 2026, [1 * B, 0, 0, 0])),
    }


def inst(end, val, filed="2026-10-20", form="10-Q"):
    """시점 사실 하나(start 없음)."""
    return {"end": end, "val": val, "filed": filed, "form": form, "fy": 2027, "fp": "Q1"}


# 지어낸 회사 둘의 잔액 태그 차림 — 실제 태그 이름, 가회사는 마이크로소프트 꼴(현금 한 줄·RPO 있음), 나회사는 오라클 꼴
BAL_A = {"cash": [[sf.CASH_STI]], "debt": [[sf.LTD_NC], [sf.LTD_C]], "lease": [[sf.OP_LEASE], [sf.FIN_LEASE]],
         "rpo": [[sf.RPO]]}
BAL_B = {"cash": [[sf.CASH], [sf.MSEC]], "debt": [[sf.NOTES_LT], [sf.NOTES_C]], "lease": [[sf.OP_LEASE], [sf.FIN_LEASE]],
         "rpo": []}
FAKE_BAL = {"TSTA": BAL_A, "TSTB": BAL_B}


def bal_a():
    """가회사 잔액: 2026-09-30 현금 64.5(정정 공시가 63을 이김) · 장기 차입 31(유동 줄 없음 → 0) · 1년 전(2025-09-30) 50 ·
    30 + 4, 리스는 연간에만(2026-06-30 운용 10 + 금융 2), 수주잔고 100(1년 전 80)."""
    return {
        sf.CASH_STI: concept([inst("2025-09-30", 50 * B, "2025-10-28"), inst("2026-06-30", 60 * B, "2026-07-29", "10-K"),
                              inst("2026-09-30", 63 * B, "2026-10-21"), inst("2026-09-30", 64.5 * B, "2026-10-28", "10-Q/A")]),
        sf.LTD_NC: concept([inst("2025-09-30", 30 * B), inst("2026-06-30", 30 * B, form="10-K"), inst("2026-09-30", 31 * B)]),
        sf.LTD_C: concept([inst("2025-09-30", 4 * B), inst("2026-06-30", 3 * B, form="10-K")]),
        sf.OP_LEASE: concept([inst("2025-06-30", 9 * B, form="10-K"), inst("2026-06-30", 10 * B, form="10-K")]),
        sf.FIN_LEASE: concept([inst("2026-06-30", 2 * B, form="10-K")]),
        sf.RPO: concept([inst("2025-09-30", 80 * B), inst("2026-09-30", 100 * B)]),
    }


def bal_b():
    """나회사 잔액(5월 말 회계연도): 2026-08-31 현금 10 + 단기 5 · 차입 40 + 2 · 1년 전(2025-08-31) 12 + 3 · 30 + 1,
    리스 운용 3(금융 404 → 0), 수주잔고 쓰지 않음."""
    return {
        sf.CASH: concept([inst("2025-08-31", 12 * B), inst("2026-05-31", 11 * B, form="10-K"), inst("2026-08-31", 10 * B)]),
        sf.MSEC: concept([inst("2025-08-31", 3 * B), inst("2026-08-31", 5 * B)]),
        sf.NOTES_LT: concept([inst("2025-08-31", 30 * B), inst("2026-05-31", 35 * B, form="10-K"),
                              inst("2026-08-31", 40 * B)]),
        sf.NOTES_C: concept([inst("2025-08-31", 1 * B), inst("2026-08-31", 2 * B)]),
        sf.OP_LEASE: concept([inst("2026-08-31", 3 * B)]),
        sf.FIN_LEASE: None,                                                    # 쓰지 않는 태그(404)
    }


def facts_of(a=None, b=None):
    """{회사 키: {태그: 시점 사실 목록}} — bal_calc의 입력 꼴(받지 않은 태그는 빼고, 404는 빈 목록)."""
    out = {}
    for co, cs in ((CO_A, a), (CO_B, b)):
        if cs is not None:
            out[co[0]] = {t: (sf.trim_instant(js, TODAY) if js else []) for t, js in cs.items()}
    return out


def got_of(a=None, b=None):
    """{CIK: {태그: 사실 목록}} — fetch_both의 got이 갖는 꼴."""
    out = {}
    for co, cs in ((CO_A, a), (CO_B, b)):
        if cs is not None:
            out[co[2]] = {t: (sf.trim(js, TODAY) if js else []) for t, js in cs.items()}
    return out


class Base(unittest.TestCase):
    def setUp(self):
        self.orig = (sf.COMPANIES, sf.GAP, sf.BAL)
        sf.COMPANIES, sf.BAL = [CO_A, CO_B], FAKE_BAL
        self.tmp = tempfile.mkdtemp()
        self.out = os.path.join(self.tmp, "data")

    def tearDown(self):
        sf.COMPANIES, sf.GAP, sf.BAL = self.orig
        shutil.rmtree(self.tmp)


# ---------- 분기 (비공개 원본 테스트를 옮긴 것) ----------

class QuarterTest(Base):
    def test_june_fiscal_year_ytd_to_quarters_and_q4_is_fy_minus_9m(self):
        cq = sf.company_quarters(got_of(concepts_a())[CO_A[2]], CO_A)
        ocf = cq["items"]["ocf"]
        self.assertEqual([ocf[e] / B for e in cq["ends"]], [10, 11, 12, 13, 14, 15, 16, 17, 18])
        self.assertEqual(cq["ends"][3], "2025-06-30")                 # 4분기 = 연간(10+11+12+13) − 9개월(10+11+12)
        self.assertEqual(cq["ends"][-1], "2026-09-30")

    def test_may_fiscal_year(self):
        cq = sf.company_quarters(got_of(b=concepts_b())[CO_B[2]], CO_B)
        self.assertEqual(cq["ends"], ["2025-08-31", "2025-11-30", "2026-02-28", "2026-05-31", "2026-08-31"])
        self.assertEqual([cq["items"]["capex"][e] / B for e in cq["ends"]], [6, 7, 8, 9, 10])

    def test_amendment_latest_filed_wins(self):
        f = ytd(12, 2026, [10 * B, 10 * B, 10 * B, 10 * B])
        for x, day in zip(f, ("2026-04-25", "2026-07-25", "2026-10-25")):   # 실제 차례: 3개월 → 6개월 → 정정 → 9개월
            x["filed"] = day
        amend = dict(f[1], val=25 * B, filed="2026-08-15", form="10-Q/A")        # 6개월을 정정(늦게 냄)
        q, _ = sf.quarters(sf.merged([("T", sf.trim(concept(f, [amend]), TODAY))]))
        self.assertEqual(q["2026-06-30"][0] / B, 15)                  # 25 − 10
        self.assertEqual(q["2026-09-30"][0] / B, 5)                   # 30 − 25(9개월을 낸 날의 6개월은 정정본)
        early = dict(f[1], val=99 * B, filed="2026-07-01")           # 먼저 낸 것은 지지 않는다
        self.assertEqual(sf.quarters(sf.merged([("T", sf.trim(concept(f, [early]), TODAY))]))[0]["2026-06-30"][0] / B, 10)
        # 다음 해 10-Q가 앞 누적(3·6·9개월) 비교 수치만 고쳐 냈고 연간은 아직 그대로(2026-11-10 점검 sec-01) — 빼는 앞 누적은
        # 뒤 누적(연간)을 낸 날의 판: 4분기 = 연간 40 − 그때의 9개월 30 = 10(고친 9개월 28을 빼면 12). 연간을 고쳐 내면 그때의 9개월 28.
        s0 = "2025-01-01"
        old = [[s0, e, v * B, d, "10-Q"] for e, v, d in (("2025-03-31", 10, "2025-04-25"), ("2025-06-30", 20, "2025-07-25"),
                                                          ("2025-09-30", 30, "2025-10-25"))] + \
              [[s0, "2025-12-31", 40 * B, "2026-02-05", "10-K"]]
        new = [[s0, e, v * B, d, "10-Q"] for e, v, d in (("2025-03-31", 9, "2026-04-25"), ("2025-06-30", 19, "2026-07-25"),
                                                          ("2025-09-30", 28, "2026-10-25"))]
        q, _ = sf.quarters(sf.merged([("T", old + new)]))
        self.assertEqual({e: v / B for e, (v, _t) in q.items()},
                         {"2025-03-31": 9, "2025-06-30": 10, "2025-09-30": 9, "2025-12-31": 10})   # 앞 셋은 고친 판끼리
        q, _ = sf.quarters(sf.merged([("T", old + new + [[s0, "2025-12-31", 38 * B, "2027-02-05", "10-K"]])]))
        self.assertEqual(q["2025-12-31"][0] / B, 10)                  # 38 − 28 — 연간을 고쳐 내도 그대로
        best = sf.merged([("A", [[s0, "2025-03-31", 1 * B, "2025-05-01", "10-Q"]]),
                          ("B", [[s0, "2025-03-31", 2 * B, "2025-05-01", "10-Q"], [s0, "2025-03-31", 3 * B, "2025-06-01", "10-Q"]])])
        self.assertEqual([sf.as_of(best, (s0, "2025-03-31"), d) / B for d in ("2025-04-01", "2025-05-01", "2025-05-31", "2025-06-01")],
                         [1, 1, 1, 3])                                # 그 날 이하의 가장 늦은 판(같은 날은 앞 태그), 없으면 가장 이른 판

    def test_trim_keeps_10q_10k_duration_facts_inside_window(self):
        js = concept(ytd(12, 2026, [1, 2, 3, 4]), ytd(12, 2019, [1, 1, 1, 1]),
                     [dict(ytd(12, 2026, [7])[0], form="8-K"), {"end": "2026-06-30", "val": 5, "filed": "2026-07-01", "form": "10-Q"},
                      dict(ytd(12, 2026, [7])[0], val=True), dict(ytd(12, 2026, [7])[0], val="7")])
        t = sf.trim(js, TODAY)
        self.assertEqual([x[2] for x in t], [1, 3, 6, 10])           # 8-K·시점 사실·KEEP_DAYS 밖·숫자 아닌 값 제외
        self.assertTrue(all(x[4].startswith("10-") for x in t))

    def test_optional_line_missing_from_early_filings_is_zero_and_prior_ytd_is_zero(self):
        cq = sf.company_quarters(got_of(concepts_a())[CO_A[2]], CO_A)
        d = cq["items"]["debt_iss"]
        self.assertEqual(d["2025-09-30"], 0)                          # 6개월 공시에 줄 없음 → 0
        self.assertEqual(d["2026-03-31"] / B, 4)                      # 9개월(4) − 앞 누적 없음(0)
        self.assertEqual(d["2026-06-30"] / B, 6)                      # 연간 10 − 9개월 4
        self.assertIn("2025-09-30", cq["filled"]["debt_iss"])
        self.assertNotIn("2026-03-31", cq["filled"]["debt_iss"])

    def test_required_lines_are_never_zero_filled(self):
        a = concepts_a()
        a[sf.PPE] = concept(ytd(6, 2026, [8 * B, 9 * B, None]), ytd(6, 2027, [20 * B]))   # 9개월·연간 없음
        s = sf.company_summary(got_of(a), CO_A)
        self.assertEqual((s["ok"], s["reason"]), (False, "not_consecutive"))

    def test_ttm_needs_four_consecutive_quarters(self):
        self.assertTrue(sf.consecutive(["2025-12-31", "2026-03-31", "2026-06-30", "2026-09-30"]))
        self.assertFalse(sf.consecutive(["2025-09-30", "2026-03-31", "2026-06-30", "2026-09-30"]))
        b = concepts_b()
        b[sf.OCF] = concept(ytd(5, 2025, [4 * B] * 4), [f for f in ytd(5, 2026, [5 * B] * 4) if f["fp"] != "Q2"],
                            ytd(5, 2027, [6 * B]))
        b[sf.PPE] = concept(ytd(5, 2025, [3 * B] * 4), ytd(5, 2026, [6 * B, 7 * B, 8 * B, 9 * B]), ytd(5, 2027, [10 * B]))
        cq = sf.company_quarters(got_of(b=b)[CO_B[2]], CO_B)        # 6개월 공시 없음 → 2분기도 3분기도 못 만든다
        self.assertEqual(cq["ends"][-4:], ["2025-05-31", "2025-08-31", "2026-05-31", "2026-08-31"])
        s = sf.company_summary(got_of(b=b), CO_B)                    # 마지막 4개는 있어도 연속이 아니다
        self.assertEqual((s["ok"], s["reason"], s["last_q"]), (False, "not_consecutive", "2026-08-31"))

    def test_year_ago_ttm_must_join_the_current_window(self):
        def gap_year(q):                                              # 1분기·6개월 공시 없음, 2·3분기는 3개월 사실
            f = lambda a, b, v, fp: {"start": a, "end": b, "val": v, "filed": "2026-07-01", "form": "10-Q", "fy": 2026, "fp": fp}
            return [f("2025-09-01", "2025-11-30", q, "Q2"), f("2025-12-01", "2026-02-28", q, "Q3"),
                    f("2025-06-01", "2026-02-28", 3 * q, "Q3"), {**f("2025-06-01", "2026-05-31", 4 * q, "FY"), "form": "10-K"}]
        b = concepts_b()
        b[sf.OCF] = concept(ytd(5, 2025, [4 * B] * 4), gap_year(5 * B), ytd(5, 2027, [6 * B]))
        b[sf.PPE] = concept(ytd(5, 2025, [3 * B] * 4), gap_year(7 * B), ytd(5, 2027, [10 * B]))
        cq = sf.company_quarters(got_of(b=b)[CO_B[2]], CO_B)
        self.assertEqual(cq["ends"][-5:], ["2025-05-31", "2025-11-30", "2026-02-28", "2026-05-31", "2026-08-31"])
        self.assertTrue(sf.consecutive(cq["ends"][-8:-4]))           # 1년 전 4분기는 그 자체로 연속이지만
        s = sf.company_summary(got_of(b=b), CO_B)                    # 지금 창 바로 앞(2025-08)이 빠져 이어지지 않는다
        self.assertTrue(s["ok"])
        self.assertIsNone(s["ttm_prev"])
        b[sf.OCF] = concept(ytd(5, 2025, [4 * B] * 4), ytd(5, 2026, [5 * B] * 4), ytd(5, 2027, [6 * B]))
        b[sf.PPE] = concept(ytd(5, 2025, [3 * B] * 4), ytd(5, 2026, [7 * B] * 4), ytd(5, 2027, [10 * B]))
        self.assertEqual(sf.company_summary(got_of(b=b), CO_B)["ttm_prev"]["to"], "2025-08-31")   # 빈 분기가 없으면 있다

    def test_a_four_month_span_is_not_a_quarter(self):
        self.assertTrue(sf.consecutive(["2026-05-31", "2026-08-31"]))
        self.assertFalse(sf.consecutive(["2026-05-31", "2026-09-30"]))          # 122일
        self.assertFalse(sf.consecutive(["2026-06-30", "2026-08-31"]))          # 62일
        self.assertEqual((sf.Q_MIN, sf.Q_MAX), (80, 100))

    def test_alternative_tags_parts_and_last_quarter_tag(self):
        s = sf.company_summary(got_of(concepts_a()), CO_A)
        t = s["ttm"]                                                  # 2025-12 ~ 2026-09
        self.assertEqual((t["from"], t["to"]), ("2025-12-31", "2026-09-30"))
        self.assertEqual(t["debt_iss"], 15.0)                         # 0 + 4 + 6 + 5 (B 태그)
        self.assertEqual(t["eq_iss"], 14.0)                           # 보통주 1+1+1+1 + 전환우선주 10(그 분기만)
        self.assertEqual((t["buyback"], t["eq_net"]), (9.0, 5.0))
        self.assertEqual((t["debt_rep"], t["debt_net"]), (0.0, 15.0))   # 404 태그 = 0
        self.assertEqual(s["tags"]["debt_iss"], "ProceedsFromDebtB")
        self.assertEqual(s["tags"]["eq_iss"], sf.EQ)                  # 첫 부분의 태그
        self.assertEqual((s["filled"]["debt_rep"], s["filled"]["debt_iss"]), (4, 1))

    def test_ttm_numbers_ratio_fcf_and_finance_lease_variant(self):
        s = sf.company_summary(got_of(concepts_a()), CO_A)
        t = s["ttm"]
        self.assertEqual((t["ocf"], t["capex"], t["fcf"]), (66.0, 51.0, 15.0))   # 15+16+17+18 · 9+10+12+20
        self.assertEqual(t["ratio"], round(51 / 66 * 100, 4))
        self.assertEqual((t["flease"], t["fcf_l"]), (5.0, 10.0))
        self.assertEqual(s["ttm_prev"]["ratio"], 50.0)                # 영업현금 11+12+13+14 · 설비투자 5+6+6+8
        self.assertEqual((s["last_q"], s["last_fcf"]), ("2026-09-30", -2.0))
        self.assertEqual([r["q"] for r in s["rows"]][-1], "2026-09-30")
        self.assertEqual(len(s["rows"]), sf.ROWS)

    def test_tag_not_received_is_unknown_not_zero(self):
        a = concepts_a()
        del a[sf.FLPP]
        got = got_of(a)
        s = sf.company_summary(got, CO_A)
        self.assertIsNone(s["ttm"]["flease"])
        self.assertIsNone(s["ttm"]["fcf_l"])
        self.assertEqual(s["ttm"]["fcf"], 15.0)
        del got[CO_A[2]][sf.CVPREF]                                   # 더하는 부분 하나를 받지 않았으면 칸 전체가 모름
        t = sf.company_summary(got, CO_A)["ttm"]
        self.assertIsNone(t["eq_iss"])
        self.assertIsNone(t["eq_net"])

    def test_unused_lines_are_zero_and_counted(self):
        s = sf.company_summary(got_of(b=concepts_b()), CO_B)
        self.assertEqual((s["ttm"]["eq_iss"], s["ttm"]["debt_iss"], s["ttm"]["flease"]), (0.0, 0.0, 0.0))
        self.assertEqual(s["ttm"]["buyback"], 0.0)                    # 1분기(2025-08)만 1 — TTM 밖
        self.assertEqual(s["filled"]["eq_iss"], 4)
        self.assertEqual(s["ttm"]["ratio"], round(34 / 21 * 100, 4))

    def test_total_over_companies_and_partial(self):
        v = sf.summary(got_of(concepts_a(), concepts_b()))
        t = v["total"]
        self.assertEqual((t["n"], t["of"], t["over"]), (2, 2, 1))
        self.assertEqual(t["ocf"], 87.0)                              # 66 + 21
        self.assertEqual(t["ratio"], round(85 / 87 * 100, 4))
        self.assertEqual(t["fcf"], 2.0)                               # 15 + (21 − 34)
        self.assertEqual(t["last_q"], "2026-09-30")
        line, _, _ = sf.texts(v)
        self.assertIn("2사 TTM 설비투자/영업현금 98%", line)
        self.assertIn("TSTB 162%(~2026-08)", line)                    # 마지막 분기가 다르면 표시
        detail = sf.texts(v)[2]                 # 회사별 꼬리는 잰 것만 — 조달을 짐작하는 말이 없다(2026-11-10 점검 sec-04)
        self.assertEqual([d.rsplit(" · ", 1)[-1] for d in detail if "회계연도" in d], ["영업현금 안", "영업현금 초과"])
        self.assertNotIn("조달", "\n".join(detail))
        b = concepts_b()                     # 비율은 넷째 자리로 두고 글에서 한 번만 반올림(2026-11-10 점검 sec-02)
        b[sf.PPE] = concept(ytd(5, 2026, [6 * B, 7 * B, 8 * B, 9 * B]), ytd(5, 2027, [8.06 * B]))
        w = sf.summary(got_of(concepts_a(), b))
        self.assertEqual(w["total"]["ratio"], round(83.06 / 87 * 100, 4))       # 95.4713
        self.assertIn("2사 TTM 설비투자/영업현금 95%", sf.texts(w)[0])          # 첫째 자리 95.5에서 다시 반올림하면 96%
        self.assertIn("TSTA 77% ·", line)
        v = sf.summary(got_of(concepts_a()))
        line, _, detail = sf.texts(v)
        self.assertIn("1/2사 TTM", line)
        self.assertIn("TSTB 영업현금 자료 없음", line)
        self.assertIn("TSTB(나회사): 영업현금 자료 없음", detail)
        with self.assertRaises(sf.ItemError):
            sf.summary({})

    def test_partial_total_field_is_blank_when_one_company_is_unknown(self):
        a = concepts_a()
        del a[sf.FLPP]
        t = sf.summary(got_of(a, concepts_b()))["total"]
        self.assertIsNone(t["fcf_l"])                                 # 한 회사가 모르면 합을 비운다
        self.assertEqual(t["fcf"], 2.0)

    def test_exactly_100_percent_is_not_over(self):
        b = concepts_b()
        b[sf.PPE] = concept(ytd(5, 2026, [5 * B] * 4), ytd(5, 2027, [6 * B]))       # 설비투자 = 영업현금
        v = sf.summary(got_of(concepts_a(), b))
        self.assertEqual(v["companies"][1]["ttm"]["ratio"], 100.0)
        self.assertEqual(v["total"]["over"], 0)

    def test_year_ago_total_needs_every_company_of_the_current_total(self):
        v = sf.summary(got_of(concepts_a(), concepts_b()))
        self.assertIsNone(v["total"]["fcf_prev"])                    # 나회사는 1년 전 TTM이 없다
        self.assertTrue(v["companies"][0]["ttm_prev"])
        self.assertNotIn("1년 전", sf.texts(v)[0])
        v = sf.summary(got_of(concepts_a()))                          # 가회사만이면 1년 전 합이 있다
        self.assertEqual(v["total"]["fcf_prev"], 25.0)                       # 영업현금 50 − 설비투자 25
        self.assertIn("(1년 전 +25.0)", sf.texts(v)[0])

    def test_required_ytd_without_earlier_ytd_is_not_a_whole_quarter(self):
        a = concepts_a()                                              # 설비투자 2026 회계연도에 6개월 누적이 없다
        a[sf.PPE] = concept(ytd(6, 2025, [5 * B, 5 * B, 6 * B, 6 * B]),
                            [f for f in ytd(6, 2026, [8 * B, 9 * B, 10 * B, 12 * B]) if f["fp"] != "Q2"], ytd(6, 2027, [20 * B]))
        got = got_of(a)[CO_A[2]]
        ref = set(sf.merged([(sf.OCF, got[sf.OCF])]))                # 영업현금엔 6개월 누적이 있다
        best = sf.merged([(sf.PPE, got[sf.PPE])])
        q, filled = sf.quarters(best, ref, optional=False)
        self.assertNotIn("2026-03-31", q)                             # 9개월 누적 27을 통째로 한 분기로 치지 않는다
        self.assertNotIn("2025-12-31", q)
        self.assertEqual((q["2026-06-30"][0] / B, filled), (12, set()))  # 연간 39 − 9개월 27
        q, filled = sf.quarters(best, ref, optional=True)             # 선택 줄이면 앞 누적 = 0 으로 친다(대조)
        self.assertEqual(q["2026-03-31"][0] / B, 27)
        self.assertIn("2025-12-31", filled)
        cq = sf.company_quarters(got, CO_A)
        self.assertNotIn("2026-03-31", cq["items"]["capex"])
        self.assertNotIn("2026-03-31", cq["ends"])
        s = sf.company_summary(got_of(a), CO_A)
        self.assertEqual((s["ok"], s["reason"]), (False, "not_consecutive"))

    def test_same_day_alternative_tags_earlier_listed_wins(self):
        s, e = "2026-01-01", "2026-03-31"
        best = sf.merged([("TagA", [[s, e, 1 * B, "2026-04-20", "10-Q"]]), ("TagB", [[s, e, 2 * B, "2026-04-20", "10-Q"]])])
        self.assertEqual(best[(s, e)], (1 * B, "2026-04-20", "TagA"))   # 같은 날 — 앞 태그
        best = sf.merged([("TagA", [[s, e, 1 * B, "2026-04-20", "10-Q"]]), ("TagB", [[s, e, 2 * B, "2026-04-21", "10-Q/A"]])])
        self.assertEqual(best[(s, e)], (2 * B, "2026-04-21", "TagB"))   # 늦게 낸 것은 뒤 태그여도
        a = concepts_a()                                              # 2027 1분기를 A·B 두 태그가 같은 날 냈다
        a["ProceedsFromDebtA"] = concept(ytd(6, 2025, [3 * B, 0, 0, 0]), ytd(6, 2027, [7 * B]))
        c = sf.company_summary(got_of(a), CO_A)
        self.assertEqual((c["tags"]["debt_iss"], c["ttm"]["debt_iss"]), ("ProceedsFromDebtA", 17.0))   # 0 + 4 + 6 + 7

    def test_real_company_table_is_the_private_one(self):
        self.assertEqual([c[0] for c in self.orig[0]], ["MSFT", "GOOGL", "AMZN", "META", "ORCL"])
        self.assertEqual([c[2] for c in self.orig[0]], ["0000789019", "0001652044", "0001018724", "0001326801", "0001341439"])
        self.assertEqual([c[3] for c in self.orig[0]], [6, 12, 12, 12, 5])
        sf.COMPANIES, sf.BAL = self.orig[0], self.orig[2]
        self.assertEqual(sum(len(sf.tags_of(c)) for c in sf.COMPANIES), 37)
        # 메타 차입 상환(2026-11-02 검토 F4): 상환 공시가 생기면 어느 태그로 내든 잡히게 — 둘 다 없으면 지금처럼 0
        self.assertEqual(sf.COMPANIES[3][4]["debt_rep"], [["RepaymentsOfLongTermDebt", "RepaymentsOfSeniorDebt"]])
        # 잔액 태그(2026-11-02 탐침으로 확인한 차림 — 비공개 원본과 같다): 첫 줄 필수, 뒤 줄은 그 날짜에 없으면 0
        debt, lease = [["LongTermDebtNoncurrent"], ["LongTermDebtCurrent"]], [["OperatingLeaseLiability"], ["FinanceLeaseLiability"]]
        rpo = [["RevenueRemainingPerformanceObligation"]]
        self.assertEqual(sf.BAL, {
            "MSFT": {"cash": [["CashCashEquivalentsAndShortTermInvestments"]], "debt": debt, "lease": lease, "rpo": rpo},
            "GOOGL": {"cash": [["CashCashEquivalentsAndShortTermInvestments"]], "debt": debt, "lease": lease, "rpo": rpo},
            "AMZN": {"cash": [["CashAndCashEquivalentsAtCarryingValue"], ["MarketableSecuritiesCurrent"]], "debt": debt,
                     "lease": lease, "rpo": []},
            "META": {"cash": [["CashAndCashEquivalentsAtCarryingValue"], ["MarketableSecuritiesCurrent"]], "debt": debt,
                     "lease": lease, "rpo": []},
            "ORCL": {"cash": [["CashAndCashEquivalentsAtCarryingValue"], ["AvailableForSaleSecuritiesDebtSecuritiesCurrent"]],
                     "debt": [["LongTermNotesAndLoans"], ["NotesPayableCurrent"]], "lease": lease, "rpo": rpo}})
        self.assertEqual(sum(len(sf.bal_tags_of(c[0])) for c in sf.COMPANIES), 31)
        self.assertEqual(len(sf.flow_plan()) + len(sf.bal_plan()), 68)
        self.assertEqual(sf.ORDER, ["funding", "flow", "bal"])


# ---------- 조달 흐름 (flow) ----------

def quarterly_of(a=None, b=None):
    """{회사 키: items} — flow_calc의 입력 꼴(company_quarters의 items)."""
    got = got_of(a, b)
    out = {}
    for co in (CO_A, CO_B):
        if co[2] in got:
            out[co[0]] = sf.company_quarters(got[co[2]], co)["items"]
    return out


def flat(qs):
    """{회사 키: {분기 끝: (영업현금, 설비투자)}} → flow_calc 입력(나머지 칸은 0) — 연속 감소 셈을 손으로 짜기 위한 것."""
    out = {}
    for key, rows in qs.items():
        items = {k: {e: 0 for e in rows} for k in sf.ITEMS}
        items["ocf"] = {e: o for e, (o, _c) in rows.items()}
        items["capex"] = {e: c for e, (_o, c) in rows.items()}
        out[key] = items
    return out


def q_ends(y, m, n):
    """y년 m월 끝부터 3달씩 n개의 분기 끝."""
    return [month_end(y, m + 3 * i).isoformat() for i in range(n)]


class FlowTest(Base):
    def test_calendar_quarter_is_the_end_month(self):
        self.assertEqual([sf.cal_label(sf.cal_q(e)) for e in ("2026-02-28", "2026-03-31", "2026-05-31", "2026-08-31",
                                                                  "2026-09-30", "2026-11-30", "2026-12-31", "2027-01-31")],
                         ["26Q1", "26Q1", "26Q2", "26Q3", "26Q3", "26Q4", "26Q4", "27Q1"])
        self.assertEqual(sf.cal_label(sf.cal_q("2099-12-31")), "99Q4")

    def test_two_company_quarters_and_the_shifted_fiscal_year(self):
        v = sf.flow_calc(quarterly_of(concepts_a(), concepts_b()))
        self.assertEqual((v["asof"], v["last"], v["of"]), ("2026-09-30", "26Q3", 2))
        self.assertEqual(v["quarters"], [{"cal": "25Q3", "fcf": 5.0}, {"cal": "25Q4", "fcf": 4.0}, {"cal": "26Q1", "fcf": 3.0},
                                         {"cal": "26Q2", "fcf": 1.0}, {"cal": "26Q3", "fcf": -6.0}])   # 가 FCF + 나 FCF
        self.assertEqual(v["dec"], 4)                                  # 25Q2엔 나회사가 없어 셈이 거기서 멈춘다
        b = v["companies"][1]
        self.assertEqual([(r["cal"], r["end"]) for r in b["rows"]][-1], ("26Q3", "2026-08-31"))   # 8월 말 = 3분기
        line, extra, detail = sf.flow_texts(v)
        self.assertTrue(line.startswith("2사 분기 FCF(달력 분기, bn): 25Q3 +5.0, 25Q4 +4.0, 26Q1 +3.0, 26Q2 +1.0, "
                                        "26Q3 -6.0 · 연속 감소 4분기 · "), line)
        self.assertIn("나회사는 분기 끝이 2·5·8·11월이라 한 달 앞선 분기를 같은 달력 분기로 센다.", extra[0])
        self.assertNotIn("가회사", extra[0])
        self.assertIn("26Q3 -4.0(2026-08 말)", detail[1])
        self.assertIn("26Q3 -2.0 ·", detail[0])                        # 달력 분기 끝과 같은 달이면 표시 없음

    def test_external_share_needs_every_company(self):
        v = sf.flow_calc(quarterly_of(concepts_a(), concepts_b()))
        # 가 TTM: 순차입 15 + 순주식(14 − 9) = 20, 설비투자 51 · 나: 0, 34 → 20 / 85
        self.assertEqual((v["ext"], v["ext_n"]), (round(20 / 85 * 100, 4), 2))   # 소수 넷째 자리로 저장(글은 정수 %)
        self.assertEqual((v["companies"][0]["ext"], v["companies"][0]["capex"]), (20.0, 51.0))
        self.assertEqual((v["ext_prev"], v["ext_prev_n"]), (None, 1))     # 나회사는 1년 전 4분기가 없다
        self.assertEqual((v["companies"][0]["ext_prev"], v["companies"][0]["capex_prev"]), (-1.0, 25.0))
        self.assertIn("외부 조달(순)/설비투자 TTM 24% ·", sf.flow_texts(v)[0])
        a = concepts_a()
        del a["RepaymentsX"]                                           # 받지 못한 태그 — 그 회사의 외부 조달은 모름
        q = quarterly_of(a, concepts_b())
        w = sf.flow_calc(q)
        self.assertEqual((w["ext"], w["ext_n"], w["companies"][0]["ext"]), (None, 1, None))
        self.assertIn("외부 조달(순)/설비투자 TTM — (1/2사만 계산됨)", sf.flow_texts(w)[0])
        self.assertEqual(w["quarters"], v["quarters"])                 # FCF는 그대로

    def test_external_share_is_stored_at_four_places_and_rounded_once(self):
        def world(debt_a, rep_a):
            q = flat({"TSTA": {e: (30 * B, 25 * B) for e in q_ends(2025, 12, 4)},
                      "TSTB": {e: (30 * B, 25 * B) for e in q_ends(2025, 11, 4)}})       # 설비투자 TTM 합 200
            last = q_ends(2025, 12, 4)[-1]
            q["TSTA"]["debt_iss"][last], q["TSTA"]["debt_rep"][last] = debt_a, rep_a
            return q
        v = sf.flow_calc(world(0.5346 * 200 * B, 0))   # 53.46% — 한 자리로 저장하면 53.5 → '54%'(두 번 반올림, 비공개 원본은 53%)
        self.assertEqual(v["ext"], 53.46)
        self.assertIn("외부 조달(순)/설비투자 TTM 53% ·", sf.flow_texts(v)[0])
        v = sf.flow_calc(world(0, 0.003 * 200 * B))      # −0.3% → '0%'('-0%'가 아니라 — 비공개 원본과 같은 글)
        self.assertEqual(v["ext"], -0.3)
        self.assertIn("외부 조달(순)/설비투자 TTM 0% ·", sf.flow_texts(v)[0])

    def test_buybacks_last_quarter_zero_buyers_unknown_and_ttm(self):
        v = sf.flow_calc(quarterly_of(concepts_a(), concepts_b()))
        self.assertEqual((v["zero_n"], v["buyers"], v["unknown"]), (1, [["TSTA", 3.0]], []))
        self.assertEqual((v["bb"], v["bb_prev"]), (9.0, None))          # 가 2+2+2+3 · 나 0, 1년 전은 나회사에 없음
        line = sf.flow_texts(v)[0]
        self.assertIn("마지막 분기 자사주 매입 0: 1/2사 (매입: TSTA 3.0bn) · TTM 자사주 매입 9.0bn", line)
        self.assertNotIn("1년 전", line)
        a = concepts_a()
        del a[sf.BUYBACK]
        w = sf.flow_calc(quarterly_of(a, concepts_b()))
        self.assertEqual((w["zero_n"], w["buyers"], w["unknown"], w["bb"]), (1, [], ["TSTA"], None))
        self.assertIn("마지막 분기 자사주 매입 0: 1/2사 (모름: TSTA) · TTM 자사주 매입 —bn", sf.flow_texts(w)[0])

    def test_buyback_zero_from_a_missing_line_is_named_apart(self):
        """마지막 분기 매입 0 가운데 그 공시에 줄이 없어 0으로 채운 회사는 '줄 없음'으로 따로(검토 F2) — 셈·분모는 그대로."""
        got = got_of(concepts_a(), concepts_b())
        quarterly, filled = {}, {}
        for co in (CO_A, CO_B):
            cq = sf.company_quarters(got[co[2]], co)
            quarterly[co[0]], filled[co[0]] = cq["items"], cq["filled"]
        v = sf.flow_calc(quarterly, filled)                            # 나회사 2026-08 분기 공시엔 매입 줄이 없다(0으로 채움)
        self.assertEqual((v["zero_n"], v["noline"], v["buyers"]), (1, ["TSTB"], [["TSTA", 3.0]]))
        self.assertIn("마지막 분기 자사주 매입 0: 1/2사 (줄 없음 1: TSTB · 매입: TSTA 3.0bn)", sf.flow_texts(v)[0])
        self.assertEqual(sf.compute_flow(got)["values"]["noline"], ["TSTB"])   # 실제 경로(compute_flow)도 채움을 넘긴다
        self.assertTrue(sf.flow_values_ok(json.loads(json.dumps(v))))
        b = concepts_b()                                               # 공시가 0이라고 낸 것은 '줄 없음'이 아니다
        b[sf.BUYBACK] = concept(ytd(5, 2026, [1 * B, 0, 0, 0]), ytd(5, 2027, [0]))
        w = sf.compute_flow(got_of(concepts_a(), b))["values"]
        self.assertEqual((w["zero_n"], w["noline"]), (1, []))
        self.assertIn("마지막 분기 자사주 매입 0: 1/2사 (매입: TSTA 3.0bn)", sf.flow_texts(w)[0])
        self.assertEqual(sf.flow_calc(quarterly)["noline"], [])        # 채움을 모르면 비운다(순수 함수의 옛 꼴)
        extra = sf.flow_texts(v)[1]
        self.assertIn("앞 분기 대비이고 계절조정이 아니다", extra[1])      # 연속 감소의 뜻(검토 F3)
        self.assertIn("자사주 매입 0의 '줄 없음'은 그 분기 공시에 매입 줄이 없어 0으로 채운 회사다", extra[1])

    def test_decline_count_stops_at_a_gap_an_equal_value_and_the_history(self):
        ends = q_ends(2024, 9, 9)                                      # 2024-09 ~ 2026-09, 9분기
        def world(fcf_a, fcf_b=None):
            fcf_b = fcf_b or [0] * len(ends)
            return flat({"TSTA": {e: (f * B, 0) for e, f in zip(ends, fcf_a) if f is not None},
                         "TSTB": {e: (f * B, 0) for e, f in zip(ends, fcf_b)}})
        self.assertEqual(sf.flow_calc(world([9, 8, 7, 6, 5, 4, 3, 2, 1]))["dec"], 7)   # 8분기 이력 → 최대 7
        self.assertEqual(sf.flow_calc(world([1, 2, 3, 4, 5, 6, 7, 8, 9]))["dec"], 0)
        self.assertEqual(sf.flow_calc(world([9, 8, 7, 6, 5, 5, 3, 2, 1]))["dec"], 3)   # 같은 값은 감소가 아니다
        self.assertEqual(sf.flow_calc(world([9, 8, 7, 6, None, 4, 3, 2, 1]))["dec"], 3)  # 빈 분기에서 멈춘다
        v = sf.flow_calc(world([9, 8, 7, 6, 5, 4, 3, 2, 1]))
        self.assertIn("연속 감소 7분기", sf.flow_texts(v)[0])
        self.assertIn("연속 감소 없음", sf.flow_texts(sf.flow_calc(world([1, 2, 3, 4, 5, 6, 7, 8, 9])))[0])
        half = sf.flow_calc(world([9, 8, 7, 6, 5, 4, 3, 2.5, 2.5000004]))   # 반올림하면 같아도 반올림 전 값으로
        self.assertEqual((half["dec"], [q["fcf"] for q in half["quarters"]][-2:]), (0, [2.5, 2.5]))

    def test_latest_complete_quarter_and_missing_middle_quarter(self):
        ends = q_ends(2025, 3, 7)                                      # 2025-03 ~ 2026-09
        qa = {e: (2 * B, 1 * B) for e in ends}
        qb = {e: (1 * B, 0) for e in ends[:-1] if e != "2025-12-31"}   # 나회사는 마지막 분기와 25Q4가 없다
        v = sf.flow_calc(flat({"TSTA": qa, "TSTB": qb}))
        self.assertEqual((v["last"], v["asof"]), ("26Q2", "2026-06-30"))
        self.assertEqual([q["fcf"] for q in v["quarters"]], [2.0, 2.0, None, 2.0, 2.0])
        self.assertIn("25Q4 —", sf.flow_texts(v)[0])
        with self.assertRaises(sf.ItemError):                           # 한 회사가 아예 없으면 5사 분기가 없다
            sf.flow_calc(flat({"TSTA": qa}))
        with self.assertRaises(sf.ItemError):
            sf.flow_calc({"TSTA": None, "TSTB": {}})
        with self.assertRaises(sf.ItemError):                           # 함께 가진 달력 분기가 없다
            sf.flow_calc(flat({"TSTA": {ends[0]: (1, 0)}, "TSTB": {ends[-1]: (1, 0)}}))

    def test_two_ends_in_one_calendar_quarter_keep_the_later(self):
        qa = {"2026-07-31": (5 * B, 0), "2026-09-30": (2 * B, 0)}
        qb = {"2026-08-31": (1 * B, 0)}
        v = sf.flow_calc(flat({"TSTA": qa, "TSTB": qb}))
        self.assertEqual((v["quarters"][-1]["fcf"], v["asof"]), (3.0, "2026-09-30"))

    def test_flow_values_check_refuses_odd_shapes(self):
        v = json.loads(json.dumps(sf.flow_calc(quarterly_of(concepts_a(), concepts_b()))))
        self.assertTrue(sf.flow_values_ok(v))
        for mutate in (lambda x: x.update(dec=8), lambda x: x["quarters"].pop(), lambda x: x["quarters"].reverse(),
                       lambda x: x["quarters"][-1].update(fcf=None), lambda x: x.update(last="26Q4"),
                       lambda x: x["buyers"].append(["TSTB", 1.0]), lambda x: x.update(unknown=["ZZZZ"]),
                       lambda x: x.update(zero_n=2), lambda x: x["companies"].reverse(), lambda x: x.update(extra=1),
                       lambda x: x["companies"][0]["rows"][0].update(cal="2026Q3"), lambda x: x.update(ext_n=1),
                       lambda x: x["companies"][0].update(capex="51"), lambda x: x["quarters"][0].update(fcf=float("nan")),
                       lambda x: x.pop("noline"), lambda x: x.update(noline=["ZZZZ"]), lambda x: x.update(noline=["TSTA"]),
                       lambda x: x.update(noline=["TSTB", "TSTB"]), lambda x: x.update(noline="TSTB")):
            w = json.loads(json.dumps(v))
            mutate(w)
            self.assertFalse(sf.flow_values_ok(w), mutate)


# ---------- 재무상태 잔액 (bal) ----------

class BalTest(Base):
    def test_trim_instant_keeps_10q_10k_point_facts_only(self):
        js = concept([inst("2026-09-30", 5), dict(inst("2026-09-30", 6), start="2026-07-01"),   # 기간 사실은 뺀다
                      dict(inst("2026-09-30", 7), form="8-K"), inst("2020-06-30", 8),            # 8-K · KEEP_DAYS 밖
                      inst("2026-12-31", 9), dict(inst("2026-09-30", 1), val=True),             # 오늘 뒤 · 참/거짓
                      dict(inst("2026-09-30", 1), val=float("nan")), dict(inst("2026-09-30", 1), val="3"),
                      dict(inst("2026-09-30", 1), end="2026-9-30"), dict(inst("2026-09-30", 1), filed=None),
                      inst("2026-06-30", 4, form="10-K/A")])
        self.assertEqual(sf.trim_instant(js, TODAY), [["2026-06-30", 4, "2026-10-20", "10-K/A"],
                                                      ["2026-09-30", 5, "2026-10-20", "10-Q"]])
        self.assertEqual(sf.trim_instant({"units": {"EUR": [inst("2026-09-30", 1)]}}, TODAY), [])

    def test_two_companies_numbers(self):
        v = sf.bal_calc(facts_of(bal_a(), bal_b()))
        a, b = v["companies"]
        self.assertEqual((a["date"], a["cash"], a["debt"], a["net"]), ("2026-09-30", 64.5, 31.0, 33.5))   # 정정 공시가 이긴다
        self.assertEqual((a["prev_date"], a["cash_prev"], a["debt_prev"], a["net_prev"]), ("2025-09-30", 50.0, 34.0, 16.0))
        self.assertEqual((a["lease"], a["lease_date"]), (12.0, "2026-06-30"))
        self.assertEqual((a["rpo"], a["rpo_date"], a["rpo_prev"]), (100.0, "2026-09-30", 80.0))
        self.assertEqual(a["filled"], {"cash": 0, "debt": 1, "lease": 0, "rpo": 0})   # 유동 차입 줄 없음 → 0
        self.assertEqual((b["date"], b["cash"], b["debt"], b["net"], b["net_prev"]), ("2026-08-31", 15.0, 42.0, -27.0, -16.0))
        self.assertEqual((b["lease"], b["filled"]["lease"], b["rpo"], b["rpo_date"]), (3.0, 1, None, None))   # 금융리스 404
        t = v["total"]
        self.assertEqual((t["n"], t["of"], t["date"], t["cash"], t["debt"], t["net"]), (2, 2, "2026-09-30", 79.5, 73.0, 6.5))
        self.assertEqual((t["cash_prev"], t["debt_prev"], t["net_prev"], t["pos"]), (65.0, 65.0, 0.0, 1))
        self.assertEqual((t["lease"], t["rpo_of"], t["rpo_n"], t["rpo"], t["rpo_prev"]), (15.0, 1, 1, 100.0, 80.0))
        line, extra, detail = sf.bal_texts(v)
        self.assertEqual(line, "2사 분기 말 잔액(회사마다 마지막 공시일): 현금 79.5bn · 장기 차입 73.0bn · 순현금 +6.5bn "
                               "(1년 전 0.0) · 순현금 양(+) 1/2사 · 리스부채 15.0bn · 수주잔고(RPO) 1사 100.0bn (1년 전 80.0) "
                               "— 순현금 TSTA +33.5(리스 ~2026-06) · TSTB -27.0(~2026-08)")
        self.assertIn("수주잔고(RPO)는 그 줄을 공시하는 회사만(가회사).", extra[0])
        self.assertIn("TSTA(가회사, 잔액 2026-09-30, 1년 전 2025-09-30): 현금 64.5bn", detail[0])
        self.assertIn("리스부채 12.0bn (2026-06-30) · 수주잔고 100.0bn · 1년 전 80.0 · 0으로 채운 줄: 장기 차입 1", detail[0])
        self.assertIn("수주잔고 싣지 않음 · 0으로 채운 줄: 리스부채 1", detail[1])

    def test_year_before_window_and_closest(self):
        d = "2026-09-30"
        self.assertEqual(sf._year_before(["2025-10-10", "2025-09-20"], d), "2025-10-10")   # 355·375일 — 둘 다 안, 같은 거리 → 늦은 날
        self.assertIsNone(sf._year_before(["2025-10-11", "2025-09-19", "2026-06-30"], d))   # 354·376일 밖
        self.assertEqual(sf._year_before(["2025-10-05", "2025-09-30", "2025-09-25"], d), "2025-09-30")
        b = bal_b()                                                    # 1년 전 잔액이 없으면 합도 없다
        b[sf.CASH] = concept([inst("2026-05-31", 11 * B, form="10-K"), inst("2026-08-31", 10 * B)])
        v = sf.bal_calc(facts_of(bal_a(), b))
        self.assertEqual((v["companies"][1]["prev_date"], v["total"]["net_prev"], v["total"]["cash_prev"]), (None, None, None))
        self.assertNotIn("1년 전", sf.bal_texts(v)[0].split("수주잔고")[0])

    def test_balance_date_needs_cash_and_debt_first_lines(self):
        a = bal_a()                                                    # 2026-09-30 장기 차입 첫 줄이 없으면 그 날은 아니다
        a[sf.LTD_NC] = concept([inst("2025-09-30", 30 * B), inst("2026-06-30", 30 * B, form="10-K")])
        c = sf.bal_calc(facts_of(a, bal_b()))["companies"][0]
        self.assertEqual((c["date"], c["cash"], c["debt"]), ("2026-06-30", 60.0, 33.0))
        self.assertEqual((c["lease_date"], c["rpo_date"], c["rpo"], c["rpo_prev"]), ("2026-06-30", "2025-09-30", 80.0, None))
        self.assertIn("TSTA +27.0(~2026-06 · RPO ~2025-09) · TSTB -27.0", sf.bal_texts(sf.bal_calc(facts_of(a, bal_b())))[0])   # 잔액 날짜 이하의 마지막
        a[sf.LTD_NC] = None                                            # 첫 줄이 404면 그 회사는 잔액 없음
        v = sf.bal_calc(facts_of(a, bal_b()))
        self.assertEqual(v["companies"][0], {"key": "TSTA", "ok": False, "reason": "no_bal"})
        self.assertEqual((v["total"]["n"], v["total"]["rpo"], v["total"]["rpo_n"]), (1, None, 0))
        line = sf.bal_texts(v)[0]
        self.assertTrue(line.startswith("1/2사 분기 말 잔액"), line)
        self.assertIn("수주잔고(RPO) — (0/1사만 있음)", line)
        self.assertIn("TSTA 잔액 자료 없음", line)
        with self.assertRaises(sf.ItemError):
            sf.bal_calc({})

    def test_tag_not_received_is_unknown_not_zero(self):
        a = bal_a()
        del a[sf.FIN_LEASE]                                            # 받지 못한 뒤 줄 — 리스부채 모름(0이 아님)
        v = sf.bal_calc(facts_of(a, bal_b()))
        self.assertEqual((v["companies"][0]["lease"], v["companies"][0]["lease_date"], v["total"]["lease"]), (None, None, None))
        self.assertIn("리스부채 —bn", sf.bal_texts(v)[0])
        self.assertIn("TSTA +33.5(리스 모름) · TSTB", sf.bal_texts(v)[0])   # 비공개 원본과 같은 표식(검토 F6)
        a = bal_a()
        del a[sf.LTD_C]                                                # 받지 못한 장기 차입 줄 — 그 회사의 잔액을 모름
        self.assertEqual(sf.bal_calc(facts_of(a, bal_b()))["companies"][0]["reason"], "no_bal")
        f = facts_of(bal_a(), bal_b())
        for t in (sf.CASH_STI, sf.LTD_NC):                             # 깨진 날짜(순수 함수에 바로 준 입력)는 그 회사만
            f["TSTA"][t].append(["2026-99-99", 1, "2026-10-01", "10-Q"])
        self.assertEqual(sf.bal_calc(f)["companies"][0]["reason"], "calc")

    def test_same_date_later_filing_and_first_listed_tag(self):
        best = sf._inst_part({"X": [["2026-09-30", 1, "2026-10-01", "10-Q"]], "Y": [["2026-09-30", 2, "2026-10-01", "10-Q"]]},
                             ["X", "Y"])
        self.assertEqual(best, {"2026-09-30": 1})                       # 같은 날 낸 것 — 앞 태그
        best = sf._inst_part({"X": [["2026-09-30", 1, "2026-10-01", "10-Q"]], "Y": [["2026-09-30", 2, "2026-10-02", "10-Q"]]},
                             ["X", "Y"])
        self.assertEqual(best, {"2026-09-30": 2})
        self.assertIsNone(sf._inst_part({}, ["X"]))

    def test_rpo_without_a_year_ago_value_has_no_year_ago_sum(self):
        a = bal_a()                                                    # 수주잔고는 있는데 1년 전 수주잔고가 없는 회사(검토 docs F4)
        a[sf.RPO] = concept([inst("2026-09-30", 100 * B)])
        v = sf.bal_calc(facts_of(a, bal_b()))
        self.assertEqual((v["companies"][0]["rpo"], v["companies"][0]["rpo_prev"]), (100.0, None))
        self.assertEqual((v["total"]["rpo"], v["total"]["rpo_prev"]), (100.0, None))
        line = sf.bal_texts(v)[0]
        self.assertIn("수주잔고(RPO) 1사 100.0bn — 순현금", line)          # '(1년 전 …)' 없음
        self.assertIn("수주잔고 100.0bn · 1년 전 — ·", sf.bal_texts(v)[2][0])

    def test_oracle_current_notes_note(self):
        self.assertIn("오라클의 유동 줄 NotesPayableCurrent는 재무상태표에 기업어음 줄이 따로 없어 기업어음 등 단기 차입이 섞일 수 "
                      "있다", sf.bal_texts(sf.bal_calc(facts_of(bal_a(), bal_b())))[1][0])   # 검토 F8

    def test_net_cash_sign_count_uses_unrounded_values(self):
        a = bal_a()
        a[sf.LTD_NC] = concept([inst("2025-09-30", 30 * B), inst("2026-09-30", 64.5 * B - 1000)])   # 순현금 +0.000001bn
        v = sf.bal_calc(facts_of(a, bal_b()))
        self.assertEqual((v["companies"][0]["net"], v["total"]["pos"]), (0.0, 1))

    def test_bal_values_check_refuses_odd_shapes(self):
        v = json.loads(json.dumps(sf.bal_calc(facts_of(bal_a(), bal_b()))))
        self.assertTrue(sf.bal_values_ok(v))
        for mutate in (lambda x: x["total"].update(n=3), lambda x: x["companies"].reverse(),
                       lambda x: x["companies"][0].update(lease_date="2026-12-31"),
                       lambda x: x["companies"][1].update(rpo=5.0, rpo_date="2026-08-31"),
                       lambda x: x["companies"][0].update(cash="64.5"), lambda x: x["companies"][0]["filled"].update(x=1),
                       lambda x: x["total"].update(rpo_of=2), lambda x: x["total"].update(date="2026-08-31"),
                       lambda x: x["companies"][0].update(extra=1), lambda x: x["total"].update(pos=3),
                       lambda x: x["companies"][0].update(prev_date="2026-09-30")):
            w = json.loads(json.dumps(v))
            mutate(w)
            self.assertFalse(sf.bal_values_ok(w), mutate)


# ---------- 받기 ----------

class Resp:
    def __init__(self, blob, headers=None, drip=None, clock=None):
        self.f, self.headers, self.drip, self.clock = io.BytesIO(blob), headers or {}, drip, clock

    def read1(self, n=-1):
        if self.drip:
            self.clock.t += self.drip
            return self.f.read(1)
        return self.f.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeOpener:
    """요청을 기록하고 지어낸 응답을 준다. answer(cik, tag) → dict · None(404) · 'block' · 'rate' · 'boom' · 'bad' ·
    ('gzip', dict) · ('drip', dict)."""
    def __init__(self, answer, clock=None, cost=0.0):
        self.answer, self.clock, self.cost, self.reqs = answer, clock, cost, []

    def __call__(self, req, timeout=None):
        self.reqs.append((req, timeout))
        if self.clock:
            self.clock.t += self.cost
        parts = req.full_url.rsplit("/", 3)
        cik, tag = parts[-3][3:], parts[-1][:-5]
        v = self.answer(cik, tag)
        if v is None:
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, io.BytesIO(b"{}"))
        if v == "block":
            raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {},
                                         io.BytesIO(b"<title>Your Request Originates from an Undeclared Automated Tool</title>"))
        if v == "rate":
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many", {}, io.BytesIO(b""))
        if v == "boom":
            raise urllib.error.URLError(f"연결 실패 {req.get_header('User-agent')}")   # 오류 문구에 연락처가 섞여도
        if v == "bad":
            return Resp(b"{not json")
        if isinstance(v, tuple) and v[0] == "gzip":
            return Resp(gzip.compress(json.dumps(v[1]).encode()), {"Content-Encoding": "gzip"})
        if isinstance(v, tuple) and v[0] == "drip":
            return Resp(json.dumps(v[1]).encode(), drip=5.0, clock=self.clock)
        return Resp(json.dumps(v).encode())


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def world_answer(a=None, b=None, ba=None, bb=None):
    """흐름 태그(concepts_*)와 잔액 태그(bal_*)를 함께 답한다 — 둘 다에 없는 태그는 404."""
    by = {CO_A[2]: {**(ba or bal_a()), **(a or concepts_a())}, CO_B[2]: {**(bb or bal_b()), **(b or concepts_b())}}
    return lambda cik, tag: by[cik].get(tag)


N_TAGS = len(sf.tags_of(CO_A)) + len(sf.tags_of(CO_B))
N_BAL = len({t for f in BAL_A.values() for alts in f for t in alts}) + len({t for f in BAL_B.values() for alts in f for t in alts})


class FetchTest(Base):
    def run_main(self, opener, env=None, now=NOW, clock=None, sleep=None):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = sf.main(["--out", self.out], opener=opener, now=now, clock=clock or FakeClock(),
                           sleep=sleep or (lambda s: None), env={"SEC_USER_AGENT": FAKE_UA} if env is None else env)
        return code, buf.getvalue()

    def saved(self):
        with open(os.path.join(self.out, sf.FILE), encoding="utf-8") as f:
            return json.load(f)

    def test_user_agent_comes_only_from_the_environment(self):
        self.assertEqual(sf.user_agent({"SEC_USER_AGENT": "  " + FAKE_UA + " "}), FAKE_UA)
        for bad in ({}, {"SEC_USER_AGENT": ""}, {"SEC_USER_AGENT": "   "}, {"SEC_USER_AGENT": "a\r\nX-Evil: 1"},
                    {"SEC_USER_AGENT": "x" * 201}, {"OTHER": FAKE_UA}):
            self.assertIsNone(sf.user_agent(bad), bad)
        with open(os.path.join(SCRIPTS, "sec_fetch.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIsNone(re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", src))     # 코드에 연락처 꼴 글이 없다

    def test_missing_contact_makes_no_request_and_keeps_the_previous_value(self):
        op = FakeOpener(world_answer())
        code, log = self.run_main(op, env={})
        self.assertEqual((code, op.reqs), (1, []))
        it = self.saved()["items"]["funding"]
        for key in sf.ORDER:                                                    # 세 칸 모두 그 사유
            it = self.saved()["items"][key]
            self.assertEqual((it["ok"], it["stale"], it["error"]), (False, False, "연락처 미설정(SEC_USER_AGENT)"), key)
            self.assertNotIn("line", it)
            self.assertIn(f"::warning::SEC 조달 참고 {key} 받지 못함: 연락처 미설정(SEC_USER_AGENT)", log)
        self.assertIn("[sec_fetch] 요청 0번 (흐름 0 · 잔액 0)", log)
        self.run_main(FakeOpener(world_answer()))                                  # 받은 뒤 연락처가 빠지면
        op = FakeOpener(world_answer())
        code, _ = self.run_main(op, env={"SEC_USER_AGENT": " "}, now=NOW + datetime.timedelta(days=1))
        self.assertEqual((code, len(op.reqs)), (1, 0))
        for key, head in (("funding", "2사 TTM"), ("flow", "2사 분기 FCF"), ("bal", "2사 분기 말 잔액")):
            it = self.saved()["items"][key]
            self.assertEqual((it["stale"], it["failed_since"], it["error"]), (True, "2026-10-31", sf.REASONS["no_ua"]), key)
            self.assertTrue(it["line"].startswith(head), key)

    def test_header_goes_only_to_sec_https(self):
        op = FakeOpener(world_answer())
        code, _ = self.run_main(op)
        self.assertEqual((code, len(op.reqs)), (0, N_TAGS + N_BAL))
        for req, timeout in op.reqs:
            self.assertEqual(req.get_header("User-agent"), FAKE_UA)
            self.assertTrue(req.full_url.startswith("https://data.sec.gov/api/xbrl/companyconcept/CIK"))
            self.assertLessEqual(timeout, sf.TIMEOUT)
        for url in ("http://data.sec.gov/x", "https://example.com/x", "https://data.sec.gov.evil.example/x",
                    "ftp://www.sec.gov/x", "https://user@evil.example/x"):
            with self.assertRaises(ValueError):
                sf.sec_request(url, FAKE_UA)
        self.assertEqual(sf.sec_request("https://www.sec.gov/x", FAKE_UA).get_header("User-agent"), FAKE_UA)

    def test_redirects_off_sec_https_are_refused(self):
        h = sf.SecOnlyRedirect()
        req = sf.sec_request("https://data.sec.gov/api/x.json", FAKE_UA)
        for bad in ("https://evil.example/x", "http://data.sec.gov/api/x.json"):
            with self.assertRaises(urllib.error.HTTPError):
                h.redirect_request(req, io.BytesIO(b""), 302, "Found", {}, bad)
        ok = h.redirect_request(req, io.BytesIO(b""), 302, "Found", {}, "https://www.sec.gov/y.json")
        self.assertEqual(ok.full_url, "https://www.sec.gov/y.json")
        opener = sf._default_opener()
        self.assertTrue(any(isinstance(x, sf.SecOnlyRedirect) for x in opener.__self__.handlers))
        self.assertFalse(any(type(x) is urllib.request.HTTPRedirectHandler for x in opener.__self__.handlers))

    BAD_URLS = (f"https://evil.example\\{AT}www.sec.gov/x.json",     # 역슬래시 사용자 정보 — urlsplit만 sec.gov로 읽는다
                f"https://evil.example%5C{AT}www.sec.gov/x.json",    # 같은 것을 퍼센트로
                f"https://user{AT}www.sec.gov/x.json", f"https://user:pw{AT}data.sec.gov/x.json",   # '@' 사용자 정보
                "http://www.sec.gov/x.json", "HTTP://data.sec.gov/x.json",                    # 평문
                "https://evil.example/x.json", "https://www.sec.gov.evil.example/x.json",    # 다른 호스트
                "https://www.sec.gov%2Eevil.example/x.json", "https://www%2Esec%2Egov/x.json", "https://data.sec.gov./x",
                "https://www.sec.gov:8443/x.json", "https://www.sec.gov:443:80/x.json",     # 포트 꼼수
                "https://www.sec.gov:/x.json", "https://www.sec.gov:abc/x.json", "https://www.sec.gov:0443/x.json",
                "https://www.sec.gov\t/x.json", "https://www.sec.gov /x.json", "https:///www.sec.gov/x.json")
    GOOD_URLS = ("https://www.sec.gov/x.json", "https://data.sec.gov/api/x.json", "https://sec.gov/x.json",
                 "https://WWW.SEC.GOV/x.json", "https://www.sec.gov:443/x.json")

    def test_host_check_reads_the_host_urllib_connects_to(self):
        u = self.BAD_URLS[0]                                         # 전제: 두 읽기가 다르다
        self.assertEqual(urllib.parse.urlsplit(u).hostname, "www.sec.gov")
        self.assertNotEqual(urllib.request.Request(u).host, "www.sec.gov")
        h = sf.SecOnlyRedirect()
        req = sf.sec_request("https://data.sec.gov/api/x.json", FAKE_UA)
        for bad in self.BAD_URLS:
            with self.assertRaises(ValueError, msg=bad):
                sf.sec_request(bad, FAKE_UA)
            with self.assertRaises(urllib.error.HTTPError, msg=bad):
                h.redirect_request(req, io.BytesIO(b""), 302, "Found", {}, bad)
        for good in self.GOOD_URLS:
            self.assertEqual(sf.sec_request(good, FAKE_UA).get_header("User-agent"), FAKE_UA)
            self.assertEqual(h.redirect_request(req, io.BytesIO(b""), 302, "Found", {}, good).full_url, good)

    def test_netloc_and_control_checks_stand_on_their_own(self):
        """urllib이 언젠가 사용자 정보·공백을 걷어 내고 Request.host를 준다 해도 '@'·제어 문자 검사가 따로 막는다."""
        class Stub:                                                    # Request.host = urlsplit이 읽은 호스트
            def __init__(self, url, *a, **k):
                p = urllib.parse.urlsplit(url)
                self.type, self.host = p.scheme, p.hostname
        with mock.patch.object(sf.urllib.request, "Request", Stub):
            self.assertTrue(sf._sec_https("https://www.sec.gov/x.json"))
            for bad in (f"https://user{AT}www.sec.gov/x.json", f"https://evil.example\\{AT}www.sec.gov/x.json",
                        "https://www.sec.gov\t/x.json", "https://www.sec.gov/x\n.json", "http://www.sec.gov/x.json"):
                self.assertFalse(sf._sec_https(bad), bad)

    def test_redirect_path_follows_sec_https_only(self):
        """urllib의 실제 옮김 경로(http_error_30x — 상대 주소 잇기·퍼센트 처리 뒤)로."""
        class Parent:
            def __init__(self):
                self.opened = []

            def open(self, req, timeout=None):
                self.opened.append(req)
                return "opened"

        def follow(location, code=302):
            h, msg = sf.SecOnlyRedirect(), email.message.Message()
            h.parent = Parent()
            msg["Location"] = location
            req = sf.sec_request("https://data.sec.gov/api/xbrl/companyconcept/CIK1/us-gaap/X.json", FAKE_UA)
            req.timeout = 5
            getattr(h, f"http_error_{code}")(req, io.BytesIO(b""), code, "Moved", msg)
            return h.parent.opened
        for code in (301, 302, 303, 307, 308):
            for loc, want in (("/api/xbrl/other.json", "https://data.sec.gov/api/xbrl/other.json"),
                              ("https://www.sec.gov/y.json", "https://www.sec.gov/y.json")):
                opened = follow(loc, code)
                self.assertEqual([r.full_url for r in opened], [want], (code, loc))
                self.assertEqual(opened[0].get_header("User-agent"), FAKE_UA)
            for bad in (f"https://evil.example\\{AT}www.sec.gov/", f"https://user{AT}www.sec.gov/", "//evil.example/x",
                        "http://www.sec.gov/y.json", "https://www.sec.gov:8443/y.json", "https://evil.example/y.json"):
                with self.assertRaises(urllib.error.HTTPError, msg=(code, bad)):
                    follow(bad, code)

    def test_contact_bits_and_leak_check(self):
        bits = sf.contact_bits(FAKE_UA)
        for b in (FAKE_UA, "fake.tester@example.invalid", "fake.tester", "example.invalid"):
            self.assertIn(b, bits)
        self.assertEqual(sf.contact_bits(None), [])
        self.assertNotIn("ab", sf.contact_bits("x ab@c.invalid"))         # 짧은 조각은 보지 않는다
        for t in (f"줄 {FAKE_UA}", "줄 FAKE.Tester 끝", "도메인 Example.Invalid", "아무 주소 q@w.example"):
            self.assertTrue(sf.leaks(t, FAKE_UA), t)
        self.assertTrue(sf.leaks("아무 주소 q@w.example"))           # 연락처를 몰라도 이메일 꼴은 거절
        for t in ("2사 TTM 설비투자/영업현금 98% · 2026-09-30 · https://www.sec.gov/edgar/sec-api-documentation", "Test Org"):
            self.assertFalse(sf.leaks(t, FAKE_UA), t)
        ua = "Org fake\\tester@example.invalid"                       # JSON에선 역슬래시가 둘로 — 문자열도 따로 본다
        d = {"line": "x fake\\tester y"}
        self.assertFalse(sf.leaks(sf.dump(d), ua))
        self.assertTrue(sf.data_leaks(d, ua))
        self.assertTrue(sf.data_leaks({"fake\\tester": 1}, ua))       # 키도 본다
        self.assertFalse(sf.data_leaks({"line": "평범한 줄"}, FAKE_UA))

    def test_log_lines_with_contact_are_replaced(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            sf.say("[sec_fetch] x fake.tester y", FAKE_UA)
            sf.say("[sec_fetch] 평범한 줄", FAKE_UA)
            sf.say("경고 example.invalid", FAKE_UA, warn=True)
        self.assertEqual(buf.getvalue().splitlines(), [sf.SAY_LEAK, "[sec_fetch] 평범한 줄", "::warning::" + sf.SAY_LEAK])
        self.assertFalse(sf.leaks(sf.SAY_LEAK, FAKE_UA))

    def test_write_refuses_text_with_contact(self):
        for data, ua in (({"line": "x fake.tester"}, FAKE_UA), ({"line": "q@w.example"}, None)):
            with self.assertRaises(sf.ItemError) as cm:
                sf.write(self.out, data, ua)
            self.assertEqual(cm.exception.code, "leak")
            self.assertFalse(os.path.exists(os.path.join(self.out, sf.FILE)))
        sf.write(self.out, {"line": "평범한 줄"}, FAKE_UA)
        self.assertTrue(os.path.exists(os.path.join(self.out, sf.FILE)))

    def test_contact_in_built_text_fails_the_item_with_a_fixed_reason(self):
        self.run_main(FakeOpener(world_answer()))                    # 영업현금 합 87 — 직전 값
        path = os.path.join(self.out, sf.FILE)
        orig = sf.texts

        def leaky(when):
            def texts(v):
                line, extra, detail = orig(v)
                return (line + " fake.tester" if when(v) else line), extra, detail
            return texts
        b = concepts_b()                                              # 나회사 이번 분기 영업현금 6 → 7(합 88)
        b[sf.OCF] = concept(ytd(5, 2026, [5 * B] * 4), ytd(5, 2027, [7 * B]))
        why = sf.REASONS["leak"]
        with mock.patch.object(sf, "texts", leaky(lambda v: v["total"]["ocf"] != 87.0)):
            code, log = self.run_main(FakeOpener(world_answer(b=b)), now=NOW + datetime.timedelta(days=1))
        items = self.saved()["items"]
        it = items["funding"]
        self.assertEqual((code, it["ok"], it["stale"], it["error"], it["failed_since"]), (0, False, True, why, "2026-10-31"))
        self.assertEqual((it["values"]["total"]["ocf"], it["retrieved"]), (87.0, "2026-10-30"))   # 새 숫자 대신 직전 값
        self.assertTrue(items["flow"]["ok"] and items["bal"]["ok"])    # 섞인 칸만 — 나머지 칸은 이번 숫자
        self.assertEqual(items["flow"]["retrieved"], "2026-10-31")     # 나회사 영업현금이 바뀌어 흐름도 새 숫자
        self.assertIn(why, log)
        with mock.patch.object(sf, "texts", leaky(lambda v: True)):  # 직전 값의 글에도 섞이면 직전 값 없이
            code, log = self.run_main(FakeOpener(world_answer(b=b)), now=NOW + datetime.timedelta(days=2))
        it = self.saved()["items"]["funding"]
        self.assertEqual((code, it["ok"], it["stale"], it["error"]), (0, False, False, why))
        self.assertFalse({"values", "line", "detail"} & set(it))
        orig_bal = sf.bal_texts                                       # 잔액 칸의 글에 섞여도 그 칸만
        with mock.patch.object(sf, "bal_texts", lambda v: (orig_bal(v)[0] + " Example.Invalid",) + orig_bal(v)[1:]):
            code, log = self.run_main(FakeOpener(world_answer(b=b)), now=NOW + datetime.timedelta(days=3))
        items = self.saved()["items"]
        self.assertEqual((code, items["bal"]["ok"], items["bal"]["stale"], items["bal"]["error"]), (0, False, False, why))
        self.assertTrue(items["flow"]["ok"])
        with open(path, "rb") as f:
            before = f.read()
        with mock.patch.object(sf, "NOTICE", sf.NOTICE + " fake.tester"):     # 정해 둔 글에까지 섞이면 아무것도 쓰지 않는다
            self.assertIsNone(sf.guarded({k: sf.ItemError("fetch") for k in sf.ORDER}, {}, NOW, FAKE_UA))
            code, log = self.run_main(FakeOpener(world_answer()), now=NOW + datetime.timedelta(days=4))
        self.assertEqual(code, 1)
        self.assertIn(f"{sf.FILE}를 쓰지 않음", log)
        with open(path, "rb") as f:
            self.assertEqual(f.read(), before)
        self.assertNotIn("fake.tester", before.decode("utf-8"))
        self.assertNotIn("fake.tester", log)
        self.assertNotIn("example.invalid", before.decode("utf-8").casefold())
        bad = sf.build({k: sf.ItemError("fetch") for k in sf.ORDER}, {}, NOW)   # 검사를 지나온 글이어도 쓰기에서 한 번 더
        bad["items"]["funding"]["name"] += " fake.tester"
        with mock.patch.object(sf, "guarded", lambda *a: bad):
            code, log = self.run_main(FakeOpener(world_answer()), now=NOW + datetime.timedelta(days=5))
        self.assertEqual(code, 1)
        with open(path, "rb") as f:
            self.assertEqual(f.read(), before)
        self.assertNotIn("fake.tester", log)

    def test_contact_is_written_nowhere(self):
        for answer in (world_answer(), lambda c, t: "boom", lambda c, t: "block", lambda c, t: "bad"):
            code, log = self.run_main(FakeOpener(answer))
            self.assertNotIn("@", log)
            self.assertNotIn("fake.tester", log)
            for root, _, files in os.walk(self.tmp):
                for name in files:
                    with open(os.path.join(root, name), encoding="utf-8") as f:
                        text = f.read()
                    self.assertNotIn("@", text, name)
                    self.assertNotIn("fake.tester", text, name)

    def test_absent_tag_is_zero_and_gzip_reads(self):
        a = {k: (("gzip", v) if v else v) for k, v in concepts_a().items()}
        ba = {k: (("gzip", v) if v else v) for k, v in bal_a().items()}
        code, _ = self.run_main(FakeOpener(world_answer(a, ba=ba)))
        self.assertEqual(code, 0)
        c = self.saved()["items"]["funding"]["values"]["companies"][0]
        self.assertEqual((c["ttm"]["debt_rep"], c["filled"]["debt_rep"]), (0.0, 4))
        self.assertEqual(self.saved()["items"]["bal"]["values"]["companies"][0]["cash"], 64.5)

    def test_any_flow_failure_stops_the_flow_tags_and_keeps_their_previous_values(self):
        self.run_main(FakeOpener(world_answer()))
        cases = (("boom", "수신 실패", N_BAL), ("block", "SEC 거절 · 요청 한도 또는 미신고 도구", 0),
                 ("rate", "SEC 거절 · 요청 한도 또는 미신고 도구", 0), ("bad", "계산할 자료가 모자람", N_BAL))
        for i, (kind, why, n_bal) in enumerate(cases, 1):
            third = sf.tags_of(CO_A)[2]
            op = FakeOpener(lambda c, t, k=kind: k if t == third else world_answer()(c, t))
            code, log = self.run_main(op, now=NOW + datetime.timedelta(days=i))
            items = self.saved()["items"]
            self.assertEqual(len(op.reqs), 3 + n_bal, kind)             # 흐름은 실패한 곳에서 멈추고, SEC 거절이면 잔액도 받지 않는다
            for key in ("funding", "flow"):
                it = items[key]
                self.assertEqual((it["ok"], it["stale"], it["error"], it["failed_since"]),
                                 (False, True, why, "2026-10-31"), (kind, key))
                self.assertEqual(it["retrieved"], "2026-10-30")
            self.assertIn("funding 받지 못함", log)
            self.assertIn("직전 값(2026-09-30 기준) 유지", log)
            if n_bal:                                                   # 잔액은 따로 받는다
                self.assertEqual((code, items["bal"]["ok"]), (0, True), kind)
            else:
                self.assertEqual((code, items["bal"]["ok"], items["bal"]["stale"], items["bal"]["error"]),
                                 (1, False, True, why), kind)

    def test_a_balance_failure_fails_only_the_balance_item(self):
        self.run_main(FakeOpener(world_answer()))
        for i, kind in enumerate(("boom", "bad", "block"), 1):
            op = FakeOpener(lambda c, t, k=kind: k if t == sf.LTD_C else world_answer()(c, t))
            code, log = self.run_main(op, now=NOW + datetime.timedelta(days=i))
            items = self.saved()["items"]
            self.assertEqual(code, 0, kind)
            self.assertTrue(items["funding"]["ok"] and items["flow"]["ok"], kind)
            bal = items["bal"]
            self.assertEqual((bal["ok"], bal["stale"], bal["failed_since"], bal["retrieved"]),
                             (False, True, "2026-10-31", "2026-10-30"), kind)
            self.assertEqual(bal["values"]["total"]["cash"], 79.5)
            self.assertIn("SEC 조달 참고 bal 받지 못함", log)
            self.assertEqual(len(op.reqs), N_TAGS + 3, kind)                       # 잔액은 실패한 곳에서 멈춘다(유동 차입 = 셋째)

    def test_odd_usd_shape_fails_only_its_group_and_never_escapes(self):
        """units.USD가 목록이 아닌 응답(수·참/거짓·객체) — 예외가 main 밖으로 나가지 않고 그 묶음만 '계산할 자료가 모자람'(검토 S2)."""
        self.run_main(FakeOpener(world_answer()))
        for i, odd in enumerate((5, True, {"x": 1}), 1):
            op = FakeOpener(lambda c, t, o=odd: {"units": {"USD": o}} if t == sf.CASH_STI else world_answer()(c, t))
            code, log = self.run_main(op, now=NOW + datetime.timedelta(days=i))          # 잔액만 깨짐 — 흐름 칸은 이번 값
            items = self.saved()["items"]
            self.assertEqual(code, 0, odd)
            self.assertTrue(items["funding"]["ok"] and items["flow"]["ok"], odd)
            self.assertEqual((items["bal"]["ok"], items["bal"]["stale"], items["bal"]["error"]),
                             (False, True, "계산할 자료가 모자람"), odd)
            self.assertNotIn("Traceback", log)
        op = FakeOpener(lambda c, t: {"units": {"USD": 5}} if t == sf.OCF else world_answer()(c, t))
        code, log = self.run_main(op, now=NOW + datetime.timedelta(days=9))               # 흐름 태그가 깨짐 — 흐름 두 칸만
        items = self.saved()["items"]
        self.assertEqual(code, 0)
        self.assertEqual({k: items[k]["error"] for k in ("funding", "flow")}, {"funding": "계산할 자료가 모자람",
                                                                              "flow": "계산할 자료가 모자람"})
        self.assertTrue(items["bal"]["ok"])
        self.assertEqual(len(op.reqs), 1 + N_BAL)                                     # 흐름은 첫 태그에서 멈추고 잔액은 받는다
        with self.assertRaises(sf.FetchError):                                         # fetch가 먼저 거른다
            sf.fetch(CO_A[2], sf.OCF, FAKE_UA, 1e9, clock=lambda: 0.0,
                     opener=FakeOpener(lambda c, t: {"units": {"USD": 5}}))
        got, code, n = sf._fetch_plan([(CO_A[2], sf.OCF)], FAKE_UA, TODAY, 1e9, lambda js, today: [x for x in 5], [None],
                                      FakeOpener(world_answer()), lambda: 0.0, lambda s: None)
        self.assertEqual((got, code, n), ({}, "format", 1))                            # 뜻밖의 오류도 정해 둔 사유로

    def test_fresh_numbers_pass_the_same_shape_check_or_fail_only_their_item(self):
        orig = sf.flow_calc

        def nan_flow(q):
            v = orig(q)
            v["quarters"][0]["fcf"] = float("nan")
            return v
        with mock.patch.object(sf, "flow_calc", nan_flow):
            code, log = self.run_main(FakeOpener(world_answer()))
        items = self.saved()["items"]
        self.assertEqual((code, items["flow"]["ok"], items["flow"]["error"]), (0, False, "계산할 자료가 모자람"))
        self.assertTrue(items["funding"]["ok"] and items["bal"]["ok"])
        with open(os.path.join(self.out, sf.FILE), encoding="utf-8") as f:
            self.assertNotIn("NaN", f.read())
        with mock.patch.object(sf, "bal_calc", lambda f: (_ for _ in ()).throw(ZeroDivisionError("x"))):
            code, log = self.run_main(FakeOpener(world_answer()), now=NOW + datetime.timedelta(days=1))
        bal = self.saved()["items"]["bal"]
        self.assertEqual((bal["ok"], bal["stale"], bal["error"]), (False, True, "계산할 자료가 모자람"))
        self.assertIn("compute_bal 계산 오류: ZeroDivisionError", log)

    def test_flow_tags_go_first_then_balance_tags_in_one_budget(self):
        op = FakeOpener(world_answer())
        f = sf.fetch_both(FAKE_UA, TODAY, opener=op, clock=FakeClock(), sleep=lambda s: None)
        tags = [r.full_url.rsplit("/", 1)[-1][:-5] for r, _ in op.reqs]
        self.assertEqual(tags[:N_TAGS], [t for c in (CO_A, CO_B) for t in sf.tags_of(c)])
        self.assertEqual(tags[N_TAGS:], [t for c in (CO_A, CO_B) for t in sf.bal_tags_of(c[0])])
        self.assertEqual((f["code"], f["bcode"], f["n"], f["nb"]), (None, None, N_TAGS, N_BAL))
        self.assertEqual(f["bgot"][CO_B[2]][sf.FIN_LEASE], [])                    # 404 = 빈 목록
        self.assertTrue(all(len(x) == 4 for x in f["bgot"][CO_A[2]][sf.CASH_STI]))   # 시점 사실 꼴
        clock = FakeClock()                                                          # 흐름에 시간을 다 쓰면 잔액은 시간 상한
        op = FakeOpener(world_answer(), clock=clock, cost=10.0)
        f = sf.fetch_both(FAKE_UA, TODAY, budget=N_TAGS * 10 + 1, opener=op, clock=clock, sleep=lambda s: None)
        self.assertEqual((f["code"], f["bcode"], f["n"], f["nb"]), (None, "budget", N_TAGS, 0))
        clock, waits = FakeClock(), []                                              # 간격은 두 묶음 사이에도
        op = FakeOpener(world_answer(), clock=clock, cost=0.1)

        def sleep(s):
            waits.append(round(s, 6))
            clock.t += s
        sf.GAP = 0.25
        sf.fetch_both(FAKE_UA, TODAY, opener=op, clock=clock, sleep=sleep)
        self.assertEqual(waits, [0.15] * (N_TAGS + N_BAL - 1))
        self.assertEqual(sf.fetch_both(None, TODAY, opener=op)["bcode"], "no_ua")

    def test_budget_caps_the_run_and_a_dripping_response(self):
        clock = FakeClock()
        op = FakeOpener(world_answer(), clock=clock, cost=10.0)
        f = sf.fetch_both(FAKE_UA, TODAY, budget=35, opener=op, clock=clock, sleep=lambda s: None)
        self.assertEqual((f["code"], f["n"], f["bcode"], f["nb"]), ("budget", 4, "budget", 0))   # 0·10·20·30초에 시작,
        self.assertTrue(all(t <= sf.TIMEOUT for _, t in op.reqs))                             # 40초엔 남은 시간 없음
        clock = FakeClock()
        op = FakeOpener(lambda c, t: ("drip", concepts_a()[sf.OCF]), clock=clock)
        f = sf.fetch_both(FAKE_UA, TODAY, budget=60, opener=op, clock=clock, sleep=lambda s: None)
        self.assertEqual((f["code"], f["n"], f["bcode"], f["nb"]), ("budget", 1, "budget", 0))   # 조금씩 흘려보내도 마감에서
        self.assertLessEqual(clock.t, 70)                                                     # 멈춘다

    def test_first_run_writes_the_item_with_its_source(self):
        code, log = self.run_main(FakeOpener(world_answer()))
        self.assertEqual(code, 0, log)
        js = self.saved()
        self.assertEqual(set(js), {"schema", "generated_at", "notice", "order", "items"})
        it = js["items"]["funding"]
        self.assertEqual((it["ok"], it["date"], it["retrieved"]), (True, "2026-09-30", "2026-10-30"))
        self.assertEqual(it["sources"], [{"series": "EDGAR", "name": "U.S. Securities and Exchange Commission",
                                          "url": sf.DOC_URL, "licence": "public",
                                          "citation": "Source: SEC EDGAR XBRL API (data.sec.gov); site calculations. "
                                                      "Retrieved October 30, 2026."}])
        self.assertEqual(len(it["detail"]), 4)                                   # 회사마다 두 줄
        self.assertEqual(js["order"], ["funding", "flow", "bal"])
        for key, date, title in (("flow", "2026-09-30", sf.FLOW_TITLE), ("bal", "2026-09-30", sf.BAL_TITLE)):
            x = js["items"][key]
            self.assertEqual((x["ok"], x["date"], x["retrieved"], x["name"], x["key"]), (True, date, "2026-10-30", title, key))
            self.assertEqual((x["sources"], x["notices"]), (it["sources"], [sf.COMPUTED_NOTICE]))
            self.assertEqual(len(x["detail"]), 2)                                # 회사마다 한 줄
        self.assertTrue(js["items"]["flow"]["line"].startswith("2사 분기 FCF(달력 분기, bn): 25Q3 +5.0, "))
        self.assertTrue(js["items"]["bal"]["line"].startswith("2사 분기 말 잔액(회사마다 마지막 공시일): 현금 79.5bn"))
        for key in sf.ORDER:
            self.assertIn(f"[sec_fetch] {key} 2026-09-30 기준", log)
        self.assertIn(f"[sec_fetch] 요청 {N_TAGS + N_BAL}번 (흐름 {N_TAGS} · 잔액 {N_BAL})", log)

    def test_same_numbers_keep_the_file_older_is_refused_and_broken_previous_is_not_carried(self):
        self.run_main(FakeOpener(world_answer()))
        path = os.path.join(self.out, sf.FILE)
        with open(path, "rb") as f:
            first = f.read()
        self.run_main(FakeOpener(world_answer()), now=NOW + datetime.timedelta(days=1))
        with open(path, "rb") as f:
            self.assertEqual(f.read(), first)
        a = concepts_a()
        for k in (sf.OCF, sf.PPE):                                               # 마지막 분기(2026-09)가 빠진 응답
            a[k] = concept([f for f in a[k]["units"]["USD"] if f["fy"] != 2027])
        b = concepts_b()
        for k in (sf.OCF, sf.PPE):
            b[k] = concept([f for f in b[k]["units"]["USD"] if f["fy"] != 2027])
        code, _ = self.run_main(FakeOpener(world_answer(a, b)), now=NOW + datetime.timedelta(days=2))
        for key in ("funding", "flow"):                                          # 흐름 칸 둘 다 마지막 분기가 이르다
            it = self.saved()["items"][key]
            self.assertEqual((it["ok"], it["stale"], it["error"]), (False, True, "받은 자료가 직전 자료보다 오래됨"), key)
        self.assertEqual((code, self.saved()["items"]["bal"]["ok"]), (0, True))
        js = self.saved()
        js["items"]["funding"]["values"]["companies"][0]["tags"]["capex"] = "<b>NotATag</b>"
        js["items"]["flow"]["values"]["quarters"][0]["cal"] = "<b>25Q3</b>"
        js["items"]["bal"]["values"]["companies"][1]["cash"] = "<b>15</b>"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(js, f, ensure_ascii=False)
        self.run_main(FakeOpener(lambda c, t: "boom"), now=NOW + datetime.timedelta(days=3))
        for key in sf.ORDER:
            it = self.saved()["items"][key]
            self.assertEqual((it["ok"], it["stale"]), (False, False), key)
        self.assertNotIn("<b>", json.dumps(self.saved()))

    def test_values_check_refuses_odd_shapes(self):
        v = sf.summary(got_of(concepts_a(), concepts_b()))
        self.assertTrue(sf.values_ok(json.loads(json.dumps(v))))
        for mutate in (lambda x: x["total"].update(n=3), lambda x: x["companies"].reverse(),
                       lambda x: x["companies"][0]["ttm"].update(ratio="77"), lambda x: x["companies"][0].update(extra=1),
                       lambda x: x["companies"][1].update(ok=False), lambda x: x["total"].update(last_q="2026-08-31"),
                       lambda x: x["companies"][0]["filled"].update(debt_rep=5)):
            w = json.loads(json.dumps(v))
            mutate(w)
            self.assertFalse(sf.values_ok(w))

    def test_every_string_is_fixed_text_without_verdict_words(self):
        self.run_main(FakeOpener(world_answer()))
        self.run_main(FakeOpener(lambda c, t: "boom"), now=NOW + datetime.timedelta(days=1))
        dump = json.dumps(self.saved(), ensure_ascii=False)
        for word in list(FORBIDDEN_TEXT) + list(VERDICT):
            self.assertNotIn(word, dump, word)
        nested = re.compile(r"\([^()]*\(")
        for t in re.findall(r'"((?:[^"\\]|\\.)*)"', dump):
            self.assertIsNone(nested.search(t), t)
        self.assertEqual({u.rstrip(".") for u in re.findall(r"https?://[^\s,;)\"]+", dump)}, {sf.DOC_URL})
        self.assertLessEqual({it["error"] for it in self.saved()["items"].values()} - {None}, set(sf.REASONS.values()))


if __name__ == "__main__":
    unittest.main(verbosity=1)
