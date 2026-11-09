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


# ---------- 월간 발행 계획 ----------
def plan_text(month="2030.5", total="6.6", comp="6.0", lo="0.5", hi="0.6", word="규모", redemption="new", extra=""):
    """계획 PDF의 글 층(지어낸 숫자 — 꼴은 실제 계획과 같다: 첫 문장, 지표종목 표, 중도환매 총액 문장과 표가 글자 붙은 채로)."""
    y, m = month.split(".")
    rng = f"{lo}~{hi}" if hi else lo
    head = (f"{y}년 {m}월중 통화안정증권 정례입찰 계획 공고(안)□한국은행은 {y}년 {m}월중 {total}조원* {word}(경쟁입찰 {comp}조원, "
            f"모집 {rng}조원)의 통화안정증권을 발행할 계획  * 모집 발행예정액(범위) 중 최대규모 기준\n"
            f"경쟁입찰[10:00~10:10]91일{m}. 4(월){m}. 5(화) 0.5 {m}.11(월)2){m}.12(화)2) 0.51년{m}. 6(수){m}. 7(목) 0.5\n"
            "만기종목명지표종목지정일1)통합발행기간1년통안00000-3105-012030. 5. 63개월2031년 1월\n")
    tables = {
        "new": (f"□{y}년 {m}월중 중도환매 총 예정액은 1.3조원으로 중도환매Ⅰ과 중도환매Ⅱ를 각각 1.0조원, 0.3조원 규모로 실시할 예정"
                f"{y}년 {m}월중 통화안정증권 중도환매 계획구 분1)입찰일결제일대상종목환매예정액(조원)중도환매Ⅰ[10:20~10:30]{m}.5(화){m}. 7(목)"
                "통안00001-3001-01통안00002-3002-021.0\n중도환매Ⅱ[10:20~10:30]{m}.19(화){m}.21(목) 통안00003-3003-012)통안00004-3004-030.3주:1)[  ] 안은 입찰시간"
                "※발행계획은 공개시장운영 여건 및 채권시장 상황 등에 따라 변경될 수 있으므로"),
        "old": (f"{y}년 {m}월중 통화안정증권 중도환매 계획입찰일결제일입찰시간대상종목환매예정액(조원){m}.7(금){m}.11(화)10:00~10:10"
                f"통안00001-3001-01통안00002-3002-030.4{m}.18(화){m}.20(목)10:00~10:10통안00003-3003-01통안00004-3004-022.3  ※ 발행계획은"),
        "none": "※ 발행계획은 공개시장운영 여건 및 채권시장 상황 등에 따라 수정될 수 있으므로",
    }
    return head + tables[redemption] + extra


def plan_item(ident, title, date="2030.04.25", bbs="P0001773"):
    return (f'<li class="bbsRowCls"><span class="dataInfo"><span class="depart"><span class="sr-only">담당부서</span>시장운영팀</span>'
            f'<span class="date"><span class="sr-only">등록일</span>{date}</span></span>'
            f'<div class="set"><a href="/portal/bbs/{bbs}/view.do?nttId={ident}&amp;searchCnd=2&amp;menuNo=200295" class="title">'
            f'<!-- x -->\n {html.escape(title)}\n</a></div></li>')


def plan_listing(rows):
    body = "".join(plan_item(*r) for r in rows)
    return ("<ul>" + body + "</ul><ul>" + body + "</ul>").encode()


def plan_view(paths=("/fileSrc/portal/ab12/2/cd34.pdf",)):
    links = "".join(f'<li><a href="{p}" title="x.pdf">x.pdf</a><a href="{p}" class="file">다운로드</a></li>' for p in paths)
    return (f'<h2 class="subject">2030년 5월중 통화안정증권 발행 계획</h2><div class="down-set"><ul>{links}</ul></div>'
            '<div class="dbdata"><p>* 자세한 내용은 첨부파일을 참고하시기 바랍니다.</p></div>').encode()


class PlanParseTests(unittest.TestCase):
    def parse(self, text, ym="2030-05", today=TODAY):
        return km.parse_plan_text(text, "77", ym, "2030-04-25", today)

    def test_new_format(self):
        r = self.parse(plan_text())
        self.assertEqual(r, {"id": "77", "month": "2030-05", "published": "2030-04-25", "total_100m": 66000, "competitive_100m": 60000,
                             "offer_min_100m": 5000, "offer_max_100m": 6000, "redemption_100m": 13000, "redemption_unread": False,
                             "source_url": km.view_url("77")})

    def test_old_row_format_with_glued_dates(self):
        """옛 꼴: 총액 문장이 없고 표의 줄마다 마지막 종목 번호 뒤에 금액, 그 뒤에 다음 줄 날짜가 붙는다('…-030.45.18(화)')."""
        r = self.parse(plan_text(redemption="old", word="수준"))
        self.assertEqual((r["redemption_100m"], r["redemption_unread"]), (27000, False))

    def test_no_redemption_table(self):
        self.assertEqual(self.parse(plan_text(redemption="none"))["redemption_100m"], None)
        self.assertFalse(self.parse(plan_text(redemption="none"))["redemption_unread"])
        only = plan_text(redemption="none", extra="□2030년 5월중 중도환매 총 예정액은 0.8조원으로 실시할 예정")
        self.assertEqual(self.parse(only)["redemption_100m"], 8000)

    def test_redemption_unread_keeps_the_plan(self):
        r = self.parse(plan_text().replace("총 예정액은 1.3조원", "총 예정액은 1.4조원"))     # 표의 합 1.3과 다르다
        self.assertEqual((r["competitive_100m"], r["redemption_100m"], r["redemption_unread"]), (60000, None, True))
        r = self.parse(plan_text(redemption="none", extra="2030년 5월중 통화안정증권 중도환매 계획입찰일결제일"))   # 표 제목만
        self.assertEqual((r["redemption_100m"], r["redemption_unread"]), (None, True))

    def test_redemption_row_count_is_checked(self):
        """총액 문장이 없는 옛 꼴: 한 줄의 금액 앞에 각주가 끼면 그 줄을 못 읽는다 — 줄 수(입찰시간 수)와 맞춰 보고 '못 읽음'."""
        r = self.parse(plan_text(redemption="old").replace("-022.3", "-021)2.3"))
        self.assertEqual((r["redemption_100m"], r["redemption_unread"]), (None, True))
        r = self.parse(plan_text().replace("-021.0", "-021)1.0"))                        # 새 꼴도 같다(총액과도 다르다)
        self.assertEqual((r["redemption_100m"], r["redemption_unread"]), (None, True))
        r = self.parse(plan_text(redemption="none", extra="□2030년 5월중 중도환매 총 예정액은 99.9조원으로"))
        self.assertEqual((r["redemption_100m"], r["redemption_unread"]), (None, True))   # 범위 밖

    def test_corrected_title(self):
        raw = plan_listing([("906", "2030년 5월중 통화안정증권 발행 계획(정정)", "2030.04.28")])
        self.assertEqual(km.plan_links(raw), [("906", ("2030-05", "2030-04-28"))])

    def test_single_offer_amount(self):
        r = self.parse(plan_text(total="6.5", hi=None))
        self.assertEqual((r["offer_min_100m"], r["offer_max_100m"]), (5000, 5000))

    def fails(self, code, text, ym="2030-05", today=TODAY):
        with self.assertRaises(ValueError) as e: self.parse(text, ym, today)
        self.assertEqual(k.skip_reason(e.exception), code, str(e.exception))

    def test_rejects(self):
        self.fails("month_mismatch", plan_text(), ym="2030-06")
        self.fails("sum_mismatch", plan_text(total="7.0"))                      # 6.0 + 0.6 = 6.6
        self.fails("field_changed", plan_text().replace("경쟁입찰 6.0조원", "경쟁 6.0조원"))
        self.fails("field_changed", plan_text() + plan_text(total="6.7", comp="6.1"))   # 첫 문장이 둘이고 다르다
        self.fails("out_of_range", plan_text(lo="0.7", hi="0.6", total="6.6"))
        self.fails("future", plan_text(month="2030.8"), ym="2030-08")
        self.assertEqual(self.parse(plan_text() + plan_text())["total_100m"], 66000)  # 같은 문장이 두 번(보도 쪽 붙임)이면 받는다
        self.assertEqual(self.parse(plan_text(month="2030.6"), ym="2030-06")["month"], "2030-06")   # 다음 달 계획은 받는다

    def test_plan_pdf_layer_goes_through_the_shared_reader(self):
        with self.assertRaises(ValueError) as e: km.parse_plan(b"<html>not a pdf</html>", "77", "2030-05", None, TODAY)
        self.assertEqual(k.skip_reason(e.exception), "pdf_shape")


class PlanListTests(unittest.TestCase):
    def test_links_dates_and_filters(self):
        raw = plan_listing([("905", "2030년 6월중 통화안정증권 발행 계획", "2030.05.28"),
                            ("904", "[보도참고자료] 2030년 6월 통화안정증권 발행 계획", "2030.05.28", "B0000502"),
                            ("903", "2030년 5월 통화안정증권 발행 계획", "2030.04.25"),           # '중' 없는 꼴
                            ("902", "2030년 5월중 통화안정증권 발행 계획", "2030.04.24"),         # 같은 달 — 목록에서 먼저 나온 것만
                            ("901", "2030년 13월중 통화안정증권 발행 계획"),
                            ("900", "2030년 4월중 통화안정증권 발행 계획", "날짜 없음")])
        self.assertEqual(km.plan_links(raw), [("905", ("2030-06", "2030-05-28")), ("903", ("2030-05", "2030-04-25")),
                                              ("900", ("2030-04", None))])
        with self.assertRaises(ValueError): km.plan_links(plan_listing([("1", "2030년 5월중 RP매각 계획")]))

    def test_pdf_url(self):
        self.assertEqual(km.plan_pdf_url(plan_view()), "https://www.bok.or.kr/fileSrc/portal/ab12/2/cd34.pdf")
        for bad in ((), ("/fileSrc/portal/ab12/2/cd34.pdf", "/fileSrc/portal/ab12/3/ef56.pdf"), ("/fileSrc/portal/ab12/1/cd34.hwp",)):
            with self.assertRaises(ValueError) as e: km.plan_pdf_url(plan_view(bad))
            self.assertEqual(k.skip_reason(e.exception), "pdf_link")
        self.assertIn("pageUnit=60", km.plan_list_url())

    def test_read_order_and_merge(self):
        prow = lambda i, m: {"id": i, "month": m, "competitive_100m": 1}
        links = [("9", ("2030-06", None)), ("8", ("2030-05", None)), ("7", ("2030-04", None)), ("6", ("2030-03", None))]
        self.assertEqual(km.plans_to_read(links, [prow("8", "2030-05")]), [links[0], links[2], links[3], links[1]])
        full = [prow(str(100 + i), f"{2029 + (i + 3) // 12}-{(i + 3) % 12 + 1:02d}") for i in range(km.MAX_PLANS)]   # 2029-04 ~ 2030-04
        self.assertEqual(km.plans_to_read([("50", ("2029-03", None)), ("51", ("2030-05", None))], full), [("51", ("2030-05", None))])
        repost = [("15", ("2030-05", None)), ("7", ("2030-04", None))]                    # 저장된 5월(8)을 번호가 큰 15로 다시 냄
        self.assertEqual(km.plans_to_read(repost, [prow("8", "2030-05"), prow("7", "2030-04")]), [repost[0], repost[1]])
        self.assertEqual(km.plans_to_read([("5", ("2030-05", None))], [prow("8", "2030-05")]), [])   # 번호가 작은 옛 공고는 읽지 않는다
        many = [(str(900 - i), (f"{2030 - (i + 7) // 12}-{(4 - i) % 12 + 1:02d}", None)) for i in range(20)]   # 2030-05부터 거꾸로 20달
        store, reads = [], 0
        for _ in range(5):                                                                 # 처음 채우기: 새 13달만 읽는다
            todo = km.plans_to_read(many, store)
            reads += len([t for t in todo if t[0] not in {r["id"] for r in store}])
            store = km.merge_plans([prow(i, m) for i, (m, _) in todo], store)
        self.assertEqual((len(store), reads, store[0]["month"], store[-1]["month"]), (km.MAX_PLANS, km.MAX_PLANS, "2029-05", "2030-05"))
        merged = km.merge_plans([prow("12", "2030-05"), prow("11", "2030-05")], [prow("10", "2030-05"), prow("3", "2030-04"), "junk"])
        self.assertEqual([(r["id"], r["month"]) for r in merged], [("3", "2030-04"), ("12", "2030-05")])
        self.assertEqual(len(km.merge_plans(full + [prow("999", "2030-05")], [])), km.MAX_PLANS)
        self.assertEqual(km.merge_plans(full + [prow("999", "2030-05")], [])[0]["month"], "2029-05")


def plan_board(texts=None, rows=None, view_error=None):
    rows = rows or [("905", "2030년 5월중 통화안정증권 발행 계획", "2030.04.25"), ("904", "2030년 4월중 통화안정증권 발행 계획", "2030.03.27")]
    texts = texts or {"905": plan_text(), "904": plan_text(month="2030.4")}
    msb = board()
    def fetch(url, *args):
        if url == km.plan_list_url(): return plan_listing(rows)
        if url.startswith(km.VIEW) and re.search(r"nttId=(\d+)", url)[1] in texts:
            if view_error: raise view_error
            return plan_view((f"/fileSrc/portal/ab{re.search(r'nttId=(\d+)', url)[1]}/2/cd.pdf",))
        if url.startswith(km.BOK + "/fileSrc/"):
            return texts[re.search(r"/ab(\d+)/", url)[1]].encode()
        return msb(url, *args)
    return fetch


class PlanBuildTests(unittest.TestCase):
    def build(self, fetch, old=None, now=dt.datetime(2030, 5, 20, 3, tzinfo=k.UTC)):
        with patch("builtins.print") as out, patch.object(km.ki, "pdf_text", lambda raw, max_pages=12: raw.decode()):
            r = k.build(old or {}, now, fetch)
        return r, "\n".join(str(c.args[0]) for c in out.call_args_list)

    def test_feed(self):
        r, _ = self.build(plan_board())
        f = r["feeds"]["msb_plans"]
        self.assertEqual((f["ok"], f["skipped"]), (True, []))
        self.assertEqual([(p["month"], p["competitive_100m"], p["published"]) for p in r["msb_plans"]],
                         [("2030-04", 60000, "2030-03-27"), ("2030-05", 60000, "2030-04-25")])
        self.assertTrue(r["feeds"]["msb"]["ok"])                         # 결과 묶음과 따로
        self.assertIn("msb_plans", status.FEEDS)

    def test_one_bad_plan_keeps_the_other(self):
        texts = {"905": plan_text(total="9.9"), "904": plan_text(month="2030.4")}
        r, log = self.build(plan_board(texts=texts), now=dt.datetime(2030, 5, 5, 3, tzinfo=k.UTC))
        f = r["feeds"]["msb_plans"]
        self.assertEqual((f["ok"], f["skipped"]), (True, [{"id": "905", "reason": "sum_mismatch"}]))
        self.assertEqual([p["month"] for p in r["msb_plans"]], ["2030-04"])
        self.assertIn("msb_plans skip 905: sum_mismatch", log)
        r, _ = self.build(plan_board(texts=texts))                        # 5월 20일에 5월 계획이 없다 — 묶음 실패, 전에 받은 자료(없음) 그대로
        self.assertEqual((r["feeds"]["msb_plans"]["ok"], r["feeds"]["msb_plans"]["reason"], r["msb_plans"]), (False, "stale", []))

    def test_freshness_window(self):
        r, _ = self.build(plan_board(rows=[("904", "2030년 4월중 통화안정증권 발행 계획", "2030.03.27")]),
                          now=dt.datetime(2030, 5, 7, 3, tzinfo=k.UTC))
        self.assertTrue(r["feeds"]["msb_plans"]["ok"])                   # 7일까지는 지난달 계획까지
        with self.assertRaises(k.FeedError) as e:
            k.validate_freshness("msb_plans", [{"month": "2030-04"}], None, dt.date(2030, 5, 8))
        self.assertEqual(str(e.exception), "stale")
        with self.assertRaises(k.FeedError) as e:
            k.validate_freshness("msb_plans", [{"month": "2030-05"}], [{"month": "2030-06"}], TODAY)
        self.assertEqual(str(e.exception), "regressed")

    def test_previous_plan_kept_on_transient_error(self):
        first, _ = self.build(plan_board())
        old = {"schema": 1, "feeds": {"msb_plans": first["feeds"]["msb_plans"]}}
        r, _ = self.build(plan_board(view_error=urllib.error.URLError("down")), old)
        self.assertTrue(r["feeds"]["msb_plans"]["ok"])
        self.assertEqual(r["msb_plans"], first["msb_plans"])
        self.assertEqual(r["feeds"]["msb_plans"]["skipped"], [{"id": "905", "reason": "network"}])

    def test_site_constant(self):
        js = (SITE / "korea.js").read_text(encoding="utf-8")
        self.assertIn('const BOK_MSB_PLANS="' + km.PLAN_PAGE + '";', js)
        self.assertIn('msb_plans:"통안증권 발행계획"', js)


if __name__ == "__main__":
    unittest.main()
