"""통화안정증권 경쟁입찰 결과(korea_msb.py) — 지어낸 숫자를 공고와 같은 꼴에 넣어 본다(네트워크 없음)."""
import datetime as dt
import html
import json
import re
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

import korea_market as k
import korea_msb as km
import korea_status as status

TODAY = dt.date(2030, 5, 20)
SITE = Path(__file__).resolve().parents[1] / "site"


def body(date="2030.5.13(월)", tenor="- 91일물(DC000-0000-0000)", offered="0.50", bids="0.80", bidders="12",
         rng="2.000~2.500", awarded="0.50", winners="10", rate="낙찰할인율 : 2.250", partial="ㅇ 부분낙찰률 : 40%", extra=()):
    lines = [f"{date} 통화안정증권 경쟁입찰 실시 결과", tenor, "", "1. 응찰결과", f"ㅇ 발행예정액 : {offered}조원",
             f"ㅇ 응찰액(응찰기관수) : {bids}조원({bidders}개사)", f"ㅇ 응찰금리 : {rng}%", "", "2. 입찰결과",
             f"ㅇ 낙찰액(낙찰기관수) : {awarded}조원({winners}개사)", f"ㅇ {rate}%", partial, *extra, "", "문의 : 한국은행 시장운영팀(000-0000)"]
    return lines


def view(lines, subject=None, extra_body=""):
    """상세 쪽 HTML(공고와 같은 꼴: h2.subject + div.dbdata 안의 <p><span>)."""
    subject = subject if subject is not None else lines[0]
    paras = "".join(f'<p><span style="font-size: 10pt;">{html.escape(x) if x else "<br>"}</span></p>' for x in lines)
    return (f'<html><body><script>var view = {{nttSj : "{subject}"}};</script><div class="bd-view">'
            f'<h2 class="subject">{html.escape(subject)}</h2><div class="down-set"></div>'
            f'<div class="dbdata">\n<!-- 주석 -->{paras}{extra_body}\n</div></div></body></html>').encode()


def item(ident, title, depart="시장운영팀"):
    return (f'<li class="bbsRowCls"><span class="i"><span class="t1">공개시장운영 공지</span></span>'
            f'<span class="dataInfo"><span class="depart"><span class="sr-only">담당부서</span>{depart}</span></span>'
            f'<div class="set"><a href="/portal/bbs/P0001773/view.do?nttId={ident}&amp;searchCnd=2&amp;menuNo=200295" class="title">'
            f'<!-- <span class="ti-announcement"><span class="sr-only">공지사항</span></span> -->\n {html.escape(title)}\n</a></div></li>')


def listing(entries):
    """목록 조각 — 실제처럼 같은 줄이 두 번(화면 두 벌) 나온다."""
    rows = "".join(item(i, t) for i, t in entries)
    return ("<script>//@@@1@@@</script><ul>" + rows + "</ul><ul>" + rows + "</ul>").encode()


R = lambda d: f"{d} 통화안정증권 경쟁입찰 실시 결과"


class ParseTests(unittest.TestCase):
    def parse(self, lines, date="2030-05-13", **kw):
        return km.parse_result(view(lines, **kw), "123", date, TODAY)

    def test_discount_bill(self):
        r = self.parse(body())
        self.assertEqual(r, {"id": "123", "date": "2030-05-13", "tenor": "91일", "offered_100m": 5000, "bids_100m": 8000,
                             "bidders": 12, "awarded_100m": 5000, "rate_kind": "discount", "rate_pct": 2.25,
                             "bid_cover_pct": 160.0, "source_url": "https://www.bok.or.kr/portal/bbs/P0001773/view.do?nttId=123&menuNo=200295"})

    def test_coupon_bond_and_partial_forms(self):
        for partial in ("ㅇ 부분낙찰 없음", "ㅇ 부분낙찰률: 71%", "ㅇ 부분낙찰율 : 57%", "ㅇ 부분낙찰률 : 50~67%", "ㅇ 부분낙찰률 : 0~60%"):
            r = self.parse(body(date="2030.5.15(수)", tenor="- 2년물(00000-0000-0000)", offered="2.50", bids="3.25",
                                rng="3.500~3.900", awarded="2.18", winners="19", bidders="20", rate="낙찰수익률 : 3.860",
                                partial=partial), "2030-05-15")
            self.assertEqual((r["tenor"], r["rate_kind"], r["rate_pct"], r["offered_100m"], r["awarded_100m"], r["bid_cover_pct"]),
                             ("2년", "yield", 3.86, 25000, 21800, 130.0), partial)

    def test_undersubscribed_auction(self):
        r = self.parse(body(bids="0.23", bidders="11", awarded="0.19", winners="11"))
        self.assertEqual((r["bids_100m"], r["awarded_100m"], r["bid_cover_pct"]), (2300, 1900, 46.0))

    def test_single_bid_rate(self):
        self.assertEqual(self.parse(body(rng="2.250"))["rate_pct"], 2.25)
        with self.assertRaises(ValueError) as e: self.parse(body(rng="2.300"))
        self.assertEqual(str(e.exception), "msb outside range")

    def test_glyph_level_spans(self):
        """글자마다 <span>이 끼인 공고(2026-03-16 실측 꼴) — 줄은 문단에서만 나눈다."""
        lines = body(partial="")
        split = "".join(f"<span>{c}</span>" for c in "ㅇ 부분낙찰률 : 60%")
        r = km.parse_result(view(lines, extra_body=f"<p>{split}</p>"), "123", "2030-05-13", TODAY)
        self.assertEqual(r["rate_pct"], 2.25)

    def test_nested_divs_inside_the_body(self):
        """편집기가 본문에 넣는 '<div><br></div>'가 어디에 있든, 줄마다 <div>로 감싸도 본문 칸 끝까지 읽는다."""
        want = self.parse(body())
        lines = body()
        mid = lines.index("2. 입찰결과")
        paras = lambda xs: "".join(f"<p><span>{html.escape(x)}</span></p>" for x in xs)
        spacer = (f'<h2 class="subject">{lines[0]}</h2><div class="dbdata">{paras(lines[:mid])}<div><br></div>'
                  f'{paras(lines[mid:])}</div></div></form>').encode()
        self.assertEqual(km.parse_result(spacer, "123", "2030-05-13", TODAY), want)
        per_line = (f'<h2 class="subject">{lines[0]}</h2><div class="dbdata">'
                    + "".join(f"<div>{html.escape(x) or '<br>'}</div>" for x in lines) + "</div>").encode()
        self.assertEqual(km.parse_result(per_line, "123", "2030-05-13", TODAY), want)
        script = view(body(), extra_body="<script>var x = '낙찰액(낙찰기관수) : 9.99조원(1개사)';</script>")
        self.assertEqual(km.parse_result(script, "123", "2030-05-13", TODAY), want)     # 스크립트 글은 본문이 아니다
        unclosed = view(body()).replace(b"</div></div></body>", b"<div>")
        self.assertEqual(km.parse_result(unclosed, "123", "2030-05-13", TODAY), want)
        with self.assertRaises(ValueError):                                              # 본문이 일찍 닫히면 칸이 모자라 버린다
            km.parse_result(view(body()).replace(b"2. ", b"</div>2. ", 1), "123", "2030-05-13", TODAY)

    def test_entities_and_nbsp(self):
        lines = [x.replace(" : ", "&nbsp;:&nbsp;") for x in body()]
        paras = "".join(f"<p><span>{x}</span></p>" for x in lines)
        raw = f'<h2 class="subject">{lines[0]}</h2><div class="dbdata">{paras}</div>'.encode()
        self.assertEqual(km.parse_result(raw, "123", "2030-05-13", TODAY)["offered_100m"], 5000)

    def fails(self, code, lines=None, date="2030-05-13", **kw):
        with self.assertRaises(ValueError) as e: self.parse(lines if lines is not None else body(), date, **kw)
        self.assertEqual(k.skip_reason(e.exception), code, str(e.exception))

    def test_date_checks(self):
        self.fails("date_mismatch", date="2030-05-14")                                  # 목록의 입찰일과 다름
        self.fails("date_mismatch", body(date="2030.5.13(화)"))                          # 요일이 맞지 않음
        self.fails("date_mismatch", subject=R("2030.5.14(화)"))                          # 목록과 제목이 다름
        self.fails("date_mismatch", body(date="2030.5.14(화)"), subject=R("2030.5.13(월)"))   # 목록·제목과 본문 첫 줄이 다름
        self.fails("date_mismatch", body()[1:], subject=R("2030.5.13(월)"))              # 본문 첫 줄에 날짜 없음
        with self.assertRaises(ValueError) as e:
            km.parse_result(view(body(date="2030.5.27(월)")), "1", "2030-05-27", TODAY)
        self.assertEqual(k.skip_reason(e.exception), "future")

    def test_tenor_and_kind(self):
        self.fails("tenor_changed", body(tenor="- 91일물(DC0) - 1년물(000)"))
        self.fails("tenor_changed", body(tenor="- 600일물(DC0)"))
        self.fails("tenor_changed", body(tenor="91일물"))
        self.fails("rate_kind", body(rate="낙찰수익률 : 2.250"))
        self.fails("rate_kind", body(tenor="- 1년물(000)"))                              # 1년 이상인데 할인율

    def test_field_shape(self):
        self.fails("field_changed", body(extra=("ㅇ 발행예정액 : 0.40조원",)))            # 같은 칸이 둘
        self.fails("field_changed", body(partial=""))                                     # 부분낙찰 줄 없음
        self.fails("field_changed", body(partial="ㅇ 부분낙찰 없음", extra=("ㅇ 부분낙찰률 : 10%",)))
        self.fails("field_changed", body(offered="500"))                                  # 단위·꼴이 다름
        self.fails("field_changed", body(rate="가중평균낙찰금리 : 2.250"))
        self.fails("field_changed", body(offered="٠.٥٠"))                                 # ASCII 숫자만
        with self.assertRaises(ValueError) as e:
            km.parse_result(view(body()) + b'<div class="dbdata"></div>', "1", "2030-05-13", TODAY)
        self.assertEqual(k.skip_reason(e.exception), "field_changed")

    def test_consistency(self):
        self.fails("out_of_range", body(awarded="0.90", bids="0.80"))                    # 낙찰 > 응찰
        self.fails("out_of_range", body(winners="13", bidders="12"))                      # 낙찰기관 > 응찰기관
        self.fails("out_of_range", body(rate="낙찰할인율 : 2.600"))                        # 응찰금리 범위 밖
        self.fails("out_of_range", body(rng="2.500~2.000"))
        self.fails("out_of_range", body(partial="ㅇ 부분낙찰률 : 60~0%"))
        self.fails("out_of_range", body(partial="ㅇ 부분낙찰률 : 120%"))
        self.fails("out_of_range", body(offered="0.00"))
        self.fails("out_of_range", body(awarded="0.00", winners="0"))

    def test_view_url_rejects_odd_ids(self):
        for bad in ("١٢٣", "1&x=2", "", "1" * 13):
            with self.assertRaises(ValueError): km.view_url(bad)


class ListTests(unittest.TestCase):
    def test_results_only_newest_first_once(self):
        raw = listing([("905", R("2030.5.15(수)")), ("904", "2030.5.15(수) 통화안정증권 경쟁입찰 실시 정보"),
                       ("903", R("2030.5.13(월)")), ("902", "2030.5.13(월) RP매각 실시 결과"),
                       ("901", R("2030.5.12(월)")),                      # 요일이 틀린 제목은 뺀다
                       ("900", R("2030.5.8(수)") + " (정정)")])
        self.assertEqual(km.result_links(raw), [("905", "2030-05-15"), ("903", "2030-05-13"), ("900", "2030-05-08")])

    def test_ids_are_ascii_and_path_fixed(self):
        raw = listing([("١٢٣", R("2030.5.15(수)")), ("77", R("2030.5.13(월)"))])
        raw = raw.replace(b'nttId=77&amp;searchCnd=2&amp;menuNo=200295" class="title">', b'nttId=77" class="title">', 1)
        self.assertEqual(km.result_links(raw), [("77", "2030-05-13")])
        other = listing([("5", R("2030.5.15(수)"))]).replace(b"/portal/bbs/P0001773/", b"/portal/bbs/P0009999/")
        with self.assertRaises(ValueError): km.result_links(other)

    def test_empty_list_is_a_format_change(self):
        with self.assertRaises(ValueError) as e: km.result_links(b"<ul></ul>")
        self.assertEqual(k.skip_reason(e.exception), "parse")

    def test_request_shape(self):
        u = km.list_url()
        self.assertTrue(u.startswith("https://www.bok.or.kr/portal/singl/newsData/listCont.do?"))
        for part in ("menuNo=200295", "searchCnd=2", "pageUnit=200", "searchKwd=%ED%86%B5%ED%99%94"):
            self.assertIn(part, u)

    def test_read_order(self):
        links = [(str(i), "2030-05-01") for i in range(40, 0, -1)]
        prev = [row(str(i), "2030-05-01") for i in range(40, 30, -1)]
        got = km.to_read(links, prev)
        self.assertEqual(got[:km.READ_NEW], [(str(i), "2030-05-01") for i in range(30, 30 - km.READ_NEW, -1)])
        self.assertEqual(got[km.READ_NEW:], [("40", "2030-05-01"), ("39", "2030-05-01")])
        self.assertEqual(km.to_read(links[:3], prev[:3]), [("40", "2030-05-01"), ("39", "2030-05-01")])
        self.assertEqual(km.to_read(links[:2], ["junk", {"id": 5}]), links[:2])         # 깨진 저장 행은 없는 것으로

    def test_replaced_originals_are_not_read_again(self):
        prev = km.merge([row("12", "2030-05-08"), row("10", "2030-05-08")], [])           # 12가 10의 정정 공고
        self.assertEqual(prev[0]["replaces"], ["10"])
        links = [("12", "2030-05-08"), ("11", "2030-05-07"), ("10", "2030-05-08")]
        self.assertEqual(km.to_read(links, prev), [("11", "2030-05-07"), ("12", "2030-05-08")])
        again = km.merge([row("12", "2030-05-08")], prev)                                 # 정정 공고를 다시 읽어도 적어 둔 번호는 남는다
        self.assertEqual(again[0]["replaces"], ["10"])

    def test_nothing_older_than_a_full_store_is_read(self):
        prev = [row(str(1000 + i), (dt.date(2030, 1, 1) + dt.timedelta(days=i)).isoformat()) for i in range(km.MAX_ROWS)]
        links = [("2000", "2030-05-01"), ("999", "2029-12-31"), ("998", "2030-01-01")]
        self.assertEqual(km.to_read(links, prev)[:2], [("2000", "2030-05-01"), ("998", "2030-01-01")])
        self.assertIn(("999", "2029-12-31"), km.to_read(links, prev[:-1]))                # 다 차지 않았으면 읽는다

def row(ident, date, tenor="91일", offered=5000, bids=8000, awarded=5000):
    return {"id": ident, "date": date, "tenor": tenor, "offered_100m": offered, "bids_100m": bids, "bidders": 10,
            "awarded_100m": awarded, "rate_kind": "discount", "rate_pct": 2.5, "bid_cover_pct": round(bids / offered * 100, 1),
            "source_url": km.view_url(ident)}


class MergeSummaryTests(unittest.TestCase):
    def test_merge_prefers_new_reading_and_later_correction(self):
        prev = [row("10", "2030-05-13", awarded=4000), row("8", "2030-05-08"), {"id": "x"}, "junk"]
        got = [row("10", "2030-05-13"), row("12", "2030-05-08"), row("11", "2030-05-08", tenor="1년")]
        out = km.merge(got, prev)
        self.assertEqual([(r["id"], r["date"], r["tenor"]) for r in out],
                         [("10", "2030-05-13", "91일"), ("12", "2030-05-08", "91일"), ("11", "2030-05-08", "1년")])
        self.assertEqual(out[0]["awarded_100m"], 5000)
        self.assertEqual((out[1].get("replaces"), "replaces" in out[0]), (["8"], False))
        self.assertEqual(km.merge([dict(row("5", "2030-05-08"), replaces=["x", 7, "4"])], [])[0]["replaces"], ["4"])
        many = [row(str(1000 + i), (dt.date(2030, 1, 1) + dt.timedelta(days=i)).isoformat()) for i in range(130)]
        self.assertEqual(len(km.merge(many, [])), km.MAX_ROWS)
        self.assertEqual(km.merge(many, [])[0]["id"], "1129")

    def test_months_need_coverage_before_the_first(self):
        rows = [row("5", "2030-05-13", bids=4000, awarded=3500), row("4", "2030-05-06"), row("3", "2030-04-29", offered=7000),
                row("2", "2030-04-08"), row("1", "2030-03-30")]
        s = km.summary(rows, TODAY)
        self.assertEqual(s["months"], [
            {"month": "2030-05", "count": 2, "offered_100m": 10000, "bids_100m": 12000, "awarded_100m": 8500, "short": 1,
             "through": "2030-05-13"},
            {"month": "2030-04", "count": 2, "offered_100m": 12000, "bids_100m": 16000, "awarded_100m": 10000, "short": 0}])
        self.assertEqual(km.summary(rows[:2], TODAY), {"months": []})                     # 5월 1일 앞 기록이 없다
        self.assertEqual(km.summary([], TODAY), {"months": []})
        broken = rows + [dict(row("9", "2030-05-14"), offered_100m=1.5)]
        self.assertEqual(km.summary(broken, TODAY), s)                                    # 꼴이 다른 행은 세지 않는다

    def test_no_rows_for_months_after_the_last_auction(self):
        rows = [row("3", "2030-04-29"), row("2", "2030-04-08"), row("1", "2030-03-30")]
        s = km.summary(rows, dt.date(2030, 5, 1))                                        # 5월 첫 입찰 전 — '0회' 줄을 싣지 않는다
        self.assertEqual([m["month"] for m in s["months"]], ["2030-04"])
        self.assertNotIn("through", s["months"][0])                                       # 끝난 달
        s = km.summary(rows, dt.date(2030, 6, 20))                                       # 수집이 멈춘 채 달이 바뀜
        self.assertEqual([m["month"] for m in s["months"]], ["2030-04"])

    def test_current_month_carries_through(self):
        rows = [row("5", "2030-05-13"), row("4", "2030-05-06"), row("3", "2030-04-29"), row("2", "2030-03-30")]
        s = km.summary(rows, TODAY)
        self.assertEqual(s["months"][0]["through"], "2030-05-13")
        self.assertEqual([("through" in m) for m in s["months"]], [True, False])

    def test_months_cross_the_year(self):
        rows = [row("3", "2031-01-05"), row("2", "2030-12-10"), row("1", "2030-10-30")]
        self.assertEqual([m["month"] for m in km.summary(rows, dt.date(2031, 1, 6))["months"]], ["2031-01", "2030-12", "2030-11"])


def board(views=None, entries=None, list_error=None):
    """목록·상세를 돌려주는 가짜 fetch. 값이 예외면 그 요청에서 던진다. 다른 묶음은 빈 응답(그 묶음만 실패)."""
    entries = entries or [("903", R("2030.5.15(수)")), ("902", R("2030.5.13(월)")), ("901", R("2030.5.8(수)"))]
    views = views or {}
    default = {"903": body(date="2030.5.15(수)", tenor="- 1년물(000)", rate="낙찰수익률 : 2.250"),
               "902": body(), "901": body(date="2030.5.8(수)")}
    calls = []
    def fetch(url, *args):
        calls.append(url)
        if url == km.list_url():
            if list_error: raise list_error
            return listing(entries)
        if url.startswith(km.VIEW):
            i = re.search(r"nttId=(\d+)", url)[1]
            v = views.get(i, default.get(i))
            if isinstance(v, Exception): raise v
            return view(v)
        return b""
    fetch.calls = calls
    return fetch


class BuildTests(unittest.TestCase):
    def build(self, fetch, old=None, now=dt.datetime(2030, 5, 20, 3, tzinfo=k.UTC)):
        with patch("builtins.print") as out:
            r = k.build(old or {}, now, fetch)
        return r, "\n".join(str(c.args[0]) for c in out.call_args_list)

    def test_feed_rows_and_summary(self):
        r, _ = self.build(board())
        f = r["feeds"]["msb"]
        self.assertEqual((f["ok"], f["skipped"]), (True, []))
        self.assertEqual([(x["id"], x["date"], x["tenor"]) for x in r["msb"]],
                         [("903", "2030-05-15", "1년"), ("902", "2030-05-13", "91일"), ("901", "2030-05-08", "91일")])
        self.assertEqual(r["msb_summary"], {"months": []})              # 5월 앞 기록이 아직 없다
        self.assertTrue(any("통화안정증권" in n and "한국은행" in n for n in r["notices"]))
        self.assertIn("msb", status.FEEDS)

    def test_one_bad_notice_keeps_the_others(self):
        r, log = self.build(board(views={"902": body(rate="낙찰수익률 : 2.250")}))
        f = r["feeds"]["msb"]
        self.assertTrue(f["ok"])
        self.assertEqual([x["id"] for x in r["msb"]], ["903", "901"])
        self.assertEqual(f["skipped"], [{"id": "902", "reason": "rate_kind"}])
        self.assertIn("msb skip 902: rate_kind", log)

    def test_previous_reading_kept_on_transient_errors(self):
        first, _ = self.build(board())
        old = {"schema": 1, "feeds": {"msb": first["feeds"]["msb"]}}
        fetch = board(views={i: urllib.error.URLError("down") for i in ("903", "902")})
        r, _ = self.build(fetch, old)
        self.assertTrue(r["feeds"]["msb"]["ok"])                         # 다시 읽기만 실패 — 전에 읽은 값으로
        self.assertEqual(r["msb"], first["msb"])
        self.assertEqual(r["feeds"]["msb"]["skipped"], [{"id": "903", "reason": "network"}, {"id": "902", "reason": "network"}])
        self.assertEqual([u for u in fetch.calls if u.startswith(km.VIEW)], [km.view_url("903"), km.view_url("902")])

    def test_list_failure_fails_only_this_feed(self):
        first, _ = self.build(board())
        old = {"schema": 1, "feeds": {"msb": first["feeds"]["msb"]}}
        r, _ = self.build(board(list_error=urllib.error.URLError("down")), old)
        f = r["feeds"]["msb"]
        self.assertEqual((f["ok"], f["reason"], r["msb"]), (False, "unavailable", first["msb"]))
        self.assertTrue(r["feeds"]["auctions"]["ok"] is False and r["feeds"]["auctions"]["reason"] == "unavailable")

    def test_stale_and_regressed(self):
        r, _ = self.build(board(), now=dt.datetime(2030, 6, 6, 3, tzinfo=k.UTC))     # 마지막 입찰 5-15 → 22일
        self.assertEqual((r["feeds"]["msb"]["ok"], r["feeds"]["msb"]["reason"]), (False, "stale"))
        r, _ = self.build(board(), now=dt.datetime(2030, 6, 5, 3, tzinfo=k.UTC))     # 21일은 아직
        self.assertTrue(r["feeds"]["msb"]["ok"])
        old = {"schema": 1, "feeds": {"msb": {"data": [row("999", "2030-05-19")], "last_success": "previous"}}}
        r, _ = self.build(board(entries=[("903", R("2030.5.15(수)"))]), old)
        self.assertEqual(r["feeds"]["msb"]["ok"], True)                  # 전에 읽은 999가 남아 있어 되돌아가지 않는다
        self.assertEqual(r["msb"][0]["id"], "999")
        with self.assertRaises(k.FeedError) as e:
            k.validate_freshness("msb", [row("1", "2030-05-10")], [row("2", "2030-05-12")], TODAY)
        self.assertEqual(str(e.exception), "regressed")

    def test_unreadable_list_rows_fail_with_format_code(self):
        dates = {"903": "2030.5.15(수)", "902": "2030.5.13(월)", "901": "2030.5.8(수)"}
        r, _ = self.build(board(views={i: body(date=d, offered="x") for i, d in dates.items()}))
        f = r["feeds"]["msb"]
        self.assertEqual((f["ok"], f["reason"]), (False, "unreadable_notices"))
        self.assertEqual([s["reason"] for s in f["skipped"]], ["field_changed"] * 3)

    def test_main_warning_line(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d, patch.object(k, "build") as b, patch("builtins.print") as out:
            b.return_value = {"schema": 1, "checked_at": "x", "cards": [], "feeds": {
                **{n: {"ok": True} for n in status.FEEDS}, "msb": {"ok": True, "skipped": [{"id": "902", "reason": "rate_kind"}]}}}
            k.main(["--out", d])
        log = "\n".join(str(c.args[0]) for c in out.call_args_list)
        self.assertIn("::warning::통화안정증권 경쟁입찰 결과 공고 1건을 읽지 못함 — 902 rate_kind", log)


class SiteTests(unittest.TestCase):
    def test_site_link_matches_the_collector(self):
        js = (SITE / "korea.js").read_text(encoding="utf-8")
        self.assertIn('const BOK_MSB="' + km.LIST_PAGE + '";', js)
        self.assertIn('msb:"통안증권 입찰 결과"', js)

    def test_output_has_no_remote_prose(self):
        r = km.parse_result(view(body(), extra_body="<p>담당자 홍길동 010-0000-0000</p>"), "123", "2030-05-13", TODAY)
        self.assertEqual(set(r), {"id", "date", "tenor", "offered_100m", "bids_100m", "bidders", "awarded_100m",
                                  "rate_kind", "rate_pct", "bid_cover_pct", "source_url"})
        self.assertNotIn("홍길동", json.dumps(r, ensure_ascii=False))
        self.assertNotIn("DC000", json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
