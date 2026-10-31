#!/usr/bin/env python3
"""하이퍼스케일러 조달 참고 자료(sec_fetch) 테스트 — 지어낸 XBRL 꼴 자료(가짜 회사 둘·가짜 응답·가짜 시계)로.

누적(YTD) → 분기(회계연도 6월·5월 말, 4분기 = 연간 − 9개월), 정정 공시, TTM 연속 요건, 0 채움, 대체 태그·더하는 부분,
금융리스 원금, 필수 줄의 앞 누적 없는 누적·같은 날 대체 태그, 5사 합(비공개 원본 sec_capex의 테스트를 옮긴 것),
연락처(환경 변수에서만·sec.gov https에만 — urllib이 붙는 호스트로 보고 '@'·역슬래시·포트 꼼수 거절, 실제 옮김 경로도 —
어디에도 쓰지 않음, 쓰기·로그 직전 검사로 섞인 글은 정해 둔 사유로),
받기(간격·시간 상한·실패 종류·하나라도 못 받으면 직전 값), 직전 파일 이어 싣기, 문구 원칙.

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요. 숫자·회사·연락처는 모두 지어낸 것이다.
"""
import os, sys, io, re, json, gzip, shutil, calendar, datetime, tempfile, unittest, contextlib, email.message, urllib.error, \
    urllib.parse, urllib.request
from unittest import mock

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import sec_fetch as sf
import ai_invest_fetch as ai
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


def got_of(a=None, b=None):
    """{CIK: {태그: 사실 목록}} — fetch_all이 만드는 꼴."""
    out = {}
    for co, cs in ((CO_A, a), (CO_B, b)):
        if cs is not None:
            out[co[2]] = {t: (sf.trim(js, TODAY) if js else []) for t, js in cs.items()}
    return out


class Base(unittest.TestCase):
    def setUp(self):
        self.orig = (sf.COMPANIES, sf.GAP)
        sf.COMPANIES = [CO_A, CO_B]
        self.tmp = tempfile.mkdtemp()
        self.out = os.path.join(self.tmp, "data")

    def tearDown(self):
        sf.COMPANIES, sf.GAP = self.orig
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
        f = ytd(12, 2026, [10 * B, 10 * B, 10 * B, 10 * B], filed="2026-02-01")
        amend = dict(f[1], val=25 * B, filed="2026-03-01", form="10-Q/A")        # 6개월을 정정(늦게 냄)
        q, _ = sf.quarters(sf.merged([("T", sf.trim(concept(f, [amend]), TODAY))]))
        self.assertEqual(q["2026-06-30"][0] / B, 15)                  # 25 − 10
        self.assertEqual(q["2026-09-30"][0] / B, 5)                   # 30 − 25
        early = dict(f[1], val=99 * B, filed="2026-01-15")           # 먼저 낸 것은 지지 않는다
        self.assertEqual(sf.quarters(sf.merged([("T", sf.trim(concept(f, [early]), TODAY))]))[0]["2026-06-30"][0] / B, 10)

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
        self.assertEqual(t["ratio"], round(51 / 66 * 100, 1))
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
        self.assertEqual(s["ttm"]["ratio"], round(34 / 21 * 100, 1))

    def test_total_over_companies_and_partial(self):
        v = sf.summary(got_of(concepts_a(), concepts_b()))
        t = v["total"]
        self.assertEqual((t["n"], t["of"], t["over"]), (2, 2, 1))
        self.assertEqual(t["ocf"], 87.0)                              # 66 + 21
        self.assertEqual(t["ratio"], round(85 / 87 * 100, 1))
        self.assertEqual(t["fcf"], 2.0)                               # 15 + (21 − 34)
        self.assertEqual(t["last_q"], "2026-09-30")
        line, _, _ = sf.texts(v)
        self.assertIn("2사 TTM 설비투자/영업현금 98%", line)
        self.assertIn("TSTB 162%(~2026-08)", line)                    # 마지막 분기가 다르면 표시
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
        sf.COMPANIES = self.orig[0]
        self.assertEqual(sum(len(sf.tags_of(c)) for c in sf.COMPANIES), 35)


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


def world_answer(a=None, b=None):
    a, b = a or concepts_a(), b or concepts_b()
    by = {CO_A[2]: a, CO_B[2]: b}
    return lambda cik, tag: by[cik].get(tag)


N_TAGS = len(sf.tags_of(CO_A)) + len(sf.tags_of(CO_B))


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
        self.assertEqual((it["ok"], it["stale"], it["error"]), (False, False, "연락처 미설정(SEC_USER_AGENT)"))
        self.assertNotIn("line", it)
        self.assertIn("::warning::SEC 조달 참고 받지 못함: 연락처 미설정(SEC_USER_AGENT)", log)
        self.run_main(FakeOpener(world_answer()))                                  # 받은 뒤 연락처가 빠지면
        op = FakeOpener(world_answer())
        code, _ = self.run_main(op, env={"SEC_USER_AGENT": " "}, now=NOW + datetime.timedelta(days=1))
        it = self.saved()["items"]["funding"]
        self.assertEqual((code, len(op.reqs), it["stale"], it["failed_since"]), (1, 0, True, "2026-10-31"))
        self.assertTrue(it["line"].startswith("2사 TTM"))

    def test_header_goes_only_to_sec_https(self):
        op = FakeOpener(world_answer())
        code, _ = self.run_main(op)
        self.assertEqual((code, len(op.reqs)), (0, N_TAGS))
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
        it = self.saved()["items"]["funding"]
        self.assertEqual((code, it["ok"], it["stale"], it["error"], it["failed_since"]), (1, False, True, why, "2026-10-31"))
        self.assertEqual((it["values"]["total"]["ocf"], it["retrieved"]), (87.0, "2026-10-30"))   # 새 숫자 대신 직전 값
        self.assertIn(why, log)
        with mock.patch.object(sf, "texts", leaky(lambda v: True)):  # 직전 값의 글에도 섞이면 직전 값 없이
            code, log = self.run_main(FakeOpener(world_answer(b=b)), now=NOW + datetime.timedelta(days=2))
        it = self.saved()["items"]["funding"]
        self.assertEqual((code, it["ok"], it["stale"], it["error"]), (1, False, False, why))
        self.assertFalse({"values", "line", "detail"} & set(it))
        with open(path, "rb") as f:
            before = f.read()
        with mock.patch.object(sf, "NOTICE", sf.NOTICE + " fake.tester"):     # 정해 둔 글에까지 섞이면 아무것도 쓰지 않는다
            self.assertIsNone(sf.guarded(sf.ItemError("fetch"), None, NOW, FAKE_UA))
            code, log = self.run_main(FakeOpener(world_answer()), now=NOW + datetime.timedelta(days=3))
        self.assertEqual(code, 1)
        self.assertIn(f"{sf.FILE}를 쓰지 않음", log)
        with open(path, "rb") as f:
            self.assertEqual(f.read(), before)
        self.assertNotIn("fake.tester", before.decode("utf-8"))
        self.assertNotIn("fake.tester", log)
        bad = sf.build(sf.ItemError("fetch"), None, NOW)              # 검사를 지나온 글이어도 쓰기에서 한 번 더
        bad["items"]["funding"]["name"] += " fake.tester"
        with mock.patch.object(sf, "guarded", lambda *a: bad):
            code, log = self.run_main(FakeOpener(world_answer()), now=NOW + datetime.timedelta(days=4))
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
        self.assertEqual(sf.scrub(f"오류 {FAKE_UA} · x.y@z.example", FAKE_UA), "오류 <UA> · <연락처>")

    def test_absent_tag_is_zero_and_gzip_reads(self):
        a = {k: (("gzip", v) if v else v) for k, v in concepts_a().items()}
        code, _ = self.run_main(FakeOpener(world_answer(a)))
        self.assertEqual(code, 0)
        c = self.saved()["items"]["funding"]["values"]["companies"][0]
        self.assertEqual((c["ttm"]["debt_rep"], c["filled"]["debt_rep"]), (0.0, 4))

    def test_any_failure_stops_and_keeps_the_previous_value(self):
        self.run_main(FakeOpener(world_answer()))
        cases = (("boom", "수신 실패"), ("block", "SEC 거절 · 요청 한도 또는 미신고 도구"), ("rate", "SEC 거절 · 요청 한도 또는 미신고 도구"),
                 ("bad", "계산할 자료가 모자람"))
        for i, (kind, why) in enumerate(cases, 1):
            third = sf.tags_of(CO_A)[2]
            op = FakeOpener(lambda c, t, k=kind: k if t == third else world_answer()(c, t))
            code, log = self.run_main(op, now=NOW + datetime.timedelta(days=i))
            it = self.saved()["items"]["funding"]
            self.assertEqual((code, len(op.reqs)), (1, 3), kind)                  # 실패한 곳에서 멈춘다
            self.assertEqual((it["ok"], it["stale"], it["error"], it["failed_since"]), (False, True, why, "2026-10-31"), kind)
            self.assertEqual(it["retrieved"], "2026-10-30")
            self.assertIn("직전 값(2026-09-30 기준) 유지", log)

    def test_requests_are_spaced(self):
        clock, waits = FakeClock(), []
        op = FakeOpener(world_answer(), clock=clock, cost=0.1)

        def sleep(s):
            waits.append(round(s, 6))
            clock.t += s
        sf.GAP = 0.25
        got, code, n = sf.fetch_all(FAKE_UA, TODAY, opener=op, clock=clock, sleep=sleep)
        self.assertEqual((code, n), (None, N_TAGS))
        self.assertEqual(waits, [0.15] * (N_TAGS - 1))                          # 요청 0.1초 + 기다림 0.15초 = 간격 0.25초

    def test_budget_caps_the_run_and_a_dripping_response(self):
        clock = FakeClock()
        op = FakeOpener(world_answer(), clock=clock, cost=10.0)
        got, code, n = sf.fetch_all(FAKE_UA, TODAY, budget=35, opener=op, clock=clock, sleep=lambda s: None)
        self.assertEqual((code, n), ("budget", 4))                               # 0·10·20·30초에 시작, 40초엔 남은 시간 없음
        self.assertTrue(all(t <= sf.TIMEOUT for _, t in op.reqs))
        clock = FakeClock()
        op = FakeOpener(lambda c, t: ("drip", concepts_a()[sf.OCF]), clock=clock)
        got, code, n = sf.fetch_all(FAKE_UA, TODAY, budget=60, opener=op, clock=clock, sleep=lambda s: None)
        self.assertEqual((code, n), ("budget", 1))                               # 조금씩 흘려보내도 마감에서 멈춘다
        self.assertLessEqual(clock.t, 70)

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
        self.assertIn("[sec_fetch] funding 2026-09-30 기준 · 요청 13번", log)

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
        it = self.saved()["items"]["funding"]
        self.assertEqual((code, it["ok"], it["stale"], it["error"]), (1, False, True, "받은 자료가 직전 자료보다 오래됨"))
        js = self.saved()
        js["items"]["funding"]["values"]["companies"][0]["tags"]["capex"] = "<b>NotATag</b>"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(js, f, ensure_ascii=False)
        self.run_main(FakeOpener(lambda c, t: "boom"), now=NOW + datetime.timedelta(days=3))
        it = self.saved()["items"]["funding"]
        self.assertEqual((it["ok"], it["stale"]), (False, False))
        self.assertNotIn("NotATag", json.dumps(self.saved()))

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
