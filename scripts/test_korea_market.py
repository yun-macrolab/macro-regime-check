"""Synthetic fixtures only: units, missing dates, sums, schema drift and fallback."""
import datetime as dt
import html
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape
from unittest.mock import patch

import korea_market as k

TODAY = dt.date(2026, 10, 8)


def book(rows):
    xml = ['<worksheet xmlns="'+k.NS['x']+'"><sheetData>']
    for n, row in enumerate(rows, 1):
        xml.append(f'<row r="{n}">')
        for col, v in enumerate(row):
            if v is None: continue
            ref = chr(65+col)+str(n)
            if isinstance(v, str): xml.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(v)}</t></is></c>')
            else: xml.append(f'<c r="{ref}"><v>{v}</v></c>')
        xml.append('</row>')
    xml.append('</sheetData></worksheet>')
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z: z.writestr('xl/worksheets/sheet1.xml',''.join(xml))
    return out.getvalue()


def export(unit='(%p)', points=None):
    return book([['범례名' if unit=='bad-header' else '범례명','회사채(AA-, 3년) - 국고채(3년)'],
                 ['단위',unit],['주기','일']]+(points or [['2026-10-06',0.7],['2026-10-07',0.683]]))


def flows(value='5,000', bank='-5,000', day='2026/10/07'):
    return ('<div>단위:계약, 백만원</div><table><tr><th>년/월/일</th><th>은행</th><th>외국인</th><th>합계</th></tr>'
            f'<tr><td>{day}</td><td>{bank}</td><td>{value}</td><td>0</td></tr></table>').encode()


def notice(text):
    return ('<input id="cn" value="'+html.escape(text, quote=True)+'">').encode()


AUCTION = "입찰일시 : ’26.10.7.(수) 입찰금액 : 30년물(국고04500-5609) 18,000억원 응찰금액 : 43,310억원 응찰률 : 240.6% 낙찰금액 : 18,000억원 가중평균낙찰금리 : 4.495%"
OFFER = "국고 03500-2906-0310 발행공고 (1) 경쟁입찰 입 찰 일 : 2026.10.12.(월) 발행예정금액 : 24,000억원 (2) 일반인입찰 발행예정금액 : 4,800억원"


class OfferingTests(unittest.TestCase):
    def parse(self, text=OFFER): return k.parse_offering_text(text, '123', '03500-2906-0310', TODAY)
    def test_competitive_amount_only(self):
        r=self.parse();self.assertEqual((r['date'],r['tenor'],r['offered_100m']),('2026-10-12','3년',24000))
    def test_wrong_bond(self):
        with self.assertRaises(ValueError): self.parse(OFFER.replace('03500','04000'))
    def test_missing_section(self):
        with self.assertRaises(ValueError): self.parse(OFFER.replace('경쟁입찰', '모집'))
    def test_unnumbered_section_without_retail_tranche(self):
        # 2026-10-14 실측(50년물 통합발행 공고): 일반인입찰이 없어 '(1)경쟁입찰 … (2)' 번호가 없다
        text = ("국고04625-7609-5001 발행공고 국채법 제5조에 의하여 “국고04625-7609-5001” 국고채권을 … 통합발행 함을 공고합니다. "
                "1. 발 행 일 자 : 2026. 9. 10. 2. 상 환 일 자 : 2076. 9. 10. 3. 발 행 방 법 ㅇ 경쟁입찰(국고04625-7609-5001) "
                "- 입 찰 일 : 2026.10.16.(금) 10:40~11:00 - 발행예정금액 : 6,000억원 - 대 금 납 입 일 : 2026.10.19.(월) 15:50까지"
                "4. 발행, 상환 및 등록 업무 : 국채법에 따라 한국은행이 담당 ※ 기타 자세한 사항은 별첨 참조. 발행예정금액 : 9,999억원")
        r = k.parse_offering_text(text, '9', '04625-7609-5001', TODAY)
        self.assertEqual((r['date'], r['tenor'], r['offered_100m']), ('2026-10-16', '50년', 6000))   # '4.' 뒤 금액은 구역 밖
    def test_unnumbered_section_stops_at_other_tranches(self):
        text = "국고 03500-2906-0310 ㅇ경쟁입찰 - 입찰일 : 2026.10.12.(월) 일반인입찰 - 발행예정금액 : 4,800억원"
        with self.assertRaises(ValueError): self.parse(text)                                 # 경쟁입찰 구역엔 금액이 없다
        two = "국고 03500-2906-0310 ㅇ경쟁입찰 - 입찰일 : 2026.10.12. - 발행예정금액 : 1억원 ㅇ경쟁입찰 - 입찰일 : 2026.10.13."
        with self.assertRaises(ValueError): self.parse(two)                                  # 번호 없이 두 번이면 가르지 않는다
        self.assertEqual(self.parse(OFFER.replace('(1)', '(3)'))['offered_100m'], 24000)     # 번호가 달라도 다음 구역 '(2)'에서 끊는다
    def test_ambiguous_amount(self):
        with self.assertRaises(ValueError): self.parse(OFFER.replace('(2)', '발행예정금액 : 2,000억원 (2)'))
    def test_future_bound(self):
        with self.assertRaises(ValueError): self.parse(OFFER.replace('2026.10.12.', '2028.10.12.'))
    def test_only_official_pdf(self):
        raw=b'<a href="https://other.invalid/a.pdf">pdf</a><a href="/fileSrc/portal/abc/2/def.pdf">pdf</a>'
        self.assertEqual(k.offering_pdf_url(raw),'https://www.bok.or.kr/fileSrc/portal/abc/2/def.pdf')
        with self.assertRaises(ValueError): k.offering_pdf_url(b'<a href="/unexpected.pdf">pdf</a>')
    def test_only_general_ktb_links(self):
        href="javascript:popup('https://www.bok.or.kr/portal/bbs/P0001794/view.do?nttId=123&menuNo=200364')"
        raw=f'<a href="{html.escape(href,quote=True)}">국고 03500-2906-0310 국고채권 발행공고</a>'
        raw+=f'<a href="{html.escape(href,quote=True)}">물가 01125-3606-L103 국고채권 발행공고</a>'
        self.assertEqual(k.offering_links(raw.encode()),[('123','03500-2906-0310')])
    def test_failed_offering_preserves_old(self):
        old={'schema':1,'feeds':{'offerings':{'data':[self.parse()],'last_success':'previous'}}}
        with patch('builtins.print'):
            r=k.build(old,dt.datetime(2026,10,8,tzinfo=k.UTC),lambda *args:b'')
        self.assertFalse(r['feeds']['offerings']['ok']);self.assertEqual(r['offerings'],[self.parse()])


def offer_text(code, date, amount):
    return f"국고 {code} 발행공고 (1) 경쟁입찰 입 찰 일 : {date}.(월) 발행예정금액 : {amount}억원 (2) 일반인입찰 발행예정금액 : 4,800억원"


NOTICES = {"1": ("03500-2906-0310", "2026.10.12", "24,000"), "2": ("04000-7609-5005", "2026.10.16", "6,000"),
           "3": ("02750-3612-1005", "2026.10.19", "21,000")}


def board(views=None, pdfs=None, ids=("1", "2", "3")):
    """공고 목록·상세·PDF(본문 글)를 돌려주는 가짜 fetch. 값이 예외면 그 요청에서 던진다. 다른 묶음은 빈 응답."""
    views, pdfs = views or {}, pdfs or {}
    def fetch(url, *args):
        if url == k.OFFER_LIST:
            href = "javascript:popup('https://www.bok.or.kr/portal/bbs/P0001794/view.do?nttId={}&menuNo=200364')"
            return "".join(f'<a href="{html.escape(href.format(i), quote=True)}">국고 {NOTICES[i][0]} 국고채권 발행공고</a>'
                           for i in ids).encode()
        if "/portal/bbs/P0001794/view.do" in url:
            i = url.split("nttId=")[1].split("&")[0]
            v = views.get(i, f'<a href="/fileSrc/portal/ab/{i}/cd.pdf">pdf</a>'.encode())
        elif "/fileSrc/portal/ab/" in url:
            i = url.split("/fileSrc/portal/ab/")[1].split("/")[0]
            v = pdfs.get(i, offer_text(*NOTICES[i]).encode())
        else:
            return b""
        if isinstance(v, Exception): raise v
        return v
    return fetch


class OfferingIsolationTests(unittest.TestCase):
    """공고 하나가 못 읽혀도 나머지는 갱신하고, 못 읽은 공고는 고정 사유 코드로만 남긴다(2026-10-14)."""
    def build(self, fetch, old=None):
        text = lambda raw, ident, code, today: k.parse_offering_text(raw.decode(), ident, code, today)
        with patch.object(k, "parse_offering", text), patch("builtins.print") as out:
            r = k.build(old or {}, dt.datetime(2026, 10, 8, tzinfo=k.UTC), fetch)
        return r, "\n".join(str(c.args[0]) for c in out.call_args_list)

    def test_one_unreadable_notice_keeps_the_others(self):
        two = b'<a href="/fileSrc/portal/ab/2/cd.pdf">a</a><a href="/fileSrc/portal/ab/2/ef.pdf">b</a>'
        r, log = self.build(board(views={"2": two}))
        f = r["feeds"]["offerings"]
        self.assertTrue(f["ok"])
        self.assertEqual([(o["id"], o["tenor"], o["offered_100m"]) for o in r["offerings"]], [("1", "3년", 24000), ("3", "10년", 21000)])
        self.assertEqual(f["skipped"], [{"id": "2", "reason": "pdf_link"}])
        self.assertIn("offerings skip 2: pdf_link", log)

    def test_previous_reading_of_the_same_notice_is_kept(self):
        prev = k.parse_offering_text(offer_text(*NOTICES["2"]), "2", NOTICES["2"][0], TODAY)
        old = {"schema": 1, "feeds": {"offerings": {"data": [prev], "last_success": "previous"}}}
        bad = offer_text(*NOTICES["2"]).replace("경쟁입찰", "모집").encode()
        r, _ = self.build(board(pdfs={"2": bad}), old)
        self.assertTrue(r["feeds"]["offerings"]["ok"])
        self.assertEqual([o["id"] for o in r["offerings"]], ["1", "2", "3"])
        self.assertEqual(r["offerings"][1], prev)
        self.assertEqual(r["feeds"]["offerings"]["skipped"], [{"id": "2", "reason": "no_competitive_section"}])

    def test_no_readable_notice_fails_only_this_feed(self):
        old = {"schema": 1, "feeds": {"offerings": {"data": [{"id": "old"}], "last_success": "previous"}}}
        bad = {i: offer_text(*NOTICES[i]).replace("경쟁입찰", "모집").encode() for i in NOTICES}
        r, _ = self.build(board(pdfs=bad), old)
        f = r["feeds"]["offerings"]
        self.assertEqual((f["ok"], f["reason"], f["last_success"]), (False, "unreadable_notices", "previous"))
        self.assertEqual(r["offerings"], [{"id": "old"}])
        self.assertEqual([x["reason"] for x in f["skipped"]], ["no_competitive_section"] * 3)

    def test_budget_timeout_stops_and_marks_the_rest(self):
        r, _ = self.build(board(views={"2": k.FeedError("timeout")}))
        f = r["feeds"]["offerings"]
        self.assertTrue(f["ok"])
        self.assertEqual([o["id"] for o in r["offerings"]], ["1"])
        self.assertEqual(f["skipped"], [{"id": "2", "reason": "timeout"}, {"id": "3", "reason": "not_tried"}])

    def test_list_failure_is_not_per_notice(self):
        r, _ = self.build(lambda *a: b"")
        self.assertEqual((r["feeds"]["offerings"]["ok"], r["feeds"]["offerings"]["reason"]), (False, "unavailable"))
        self.assertEqual(r["feeds"]["offerings"]["skipped"], [])

    def test_skip_reasons_are_fixed_codes(self):
        from pypdf.errors import PdfReadError
        import urllib.error
        cases = [(urllib.error.HTTPError("https://x.invalid/secret", 404, "secret", {}, None), "http_404"),
                 (urllib.error.URLError("secret host"), "network"), (TimeoutError("secret"), "network"),
                 (UnicodeDecodeError("utf-8", b"\xff", 0, 1, "secret"), "decode"), (PdfReadError("secret"), "pdf_read"),
                 (ValueError("missing competitive section"), "no_competitive_section"),
                 (ValueError("ambiguous offering fields"), "ambiguous_fields"), (ValueError("원격 문구 secret"), "parse"),
                 (KeyError("secret"), "parse"), (k.FeedError("timeout"), "timeout")]
        for exc, want in cases:
            self.assertEqual(k.skip_reason(exc), want, exc)
            self.assertNotIn("secret", k.skip_reason(exc))
        for code in k.SKIP_REASONS.values():
            self.assertRegex(code, r"^[a-z_]+$")

    def test_skips_reach_actions_log_as_warning_only(self):
        two = b'<a href="/fileSrc/portal/ab/2/cd.pdf">a</a><a href="/fileSrc/portal/ab/2/ef.pdf">b</a>'
        fetch, build = board(views={"2": two}), k.build
        with tempfile.TemporaryDirectory() as folder, patch.object(k, "build", lambda old, now: build(old, now, fetch)), \
                patch.object(k, "parse_offering", lambda raw, i, c, t: k.parse_offering_text(raw.decode(), i, c, t)), \
                patch("builtins.print") as out:
            code = k.main(["--out", folder])
            saved = json.loads((Path(folder) / "korea.json").read_text(encoding="utf-8"))
        lines = [str(c.args[0]) for c in out.call_args_list]
        self.assertEqual(code, 1)                                       # 다른 묶음(빈 응답)은 실패 — 종료코드는 그대로
        self.assertTrue(saved["feeds"]["offerings"]["ok"])
        self.assertIn("::warning::한국은행 발행공고 1건을 읽지 못함 — 2 pdf_link", lines)


class ParserTests(unittest.TestCase):
    def parse(self, raw): return k.parse_bok(raw,k.CHARTS['credit'][1],TODAY)
    def test_bok_units(self): self.assertEqual(self.parse(export())['aa_spread'][-1],['2026-10-07',68.3])
    def test_unit_change(self):
        with self.assertRaises(ValueError): self.parse(export('(bp)'))
    def test_label_change(self):
        with self.assertRaises(ValueError): self.parse(export('bad-header'))
    def test_null_not_zero(self):
        self.assertEqual(len(self.parse(export(points=[['2026-10-06',None],['2026-10-07',0.683]]))['aa_spread']),1)
    def test_future_rejected(self):
        with self.assertRaises(ValueError): self.parse(export(points=[['2026-10-09',1]]))
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError): self.parse(export(points=[['2026-10-07',1],['2026-10-07',2]]))
    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError): self.parse(export(points=[['2026-10-07',float('nan')]]))
    def test_no_recent_data(self):
        with self.assertRaises(ValueError): self.parse(export(points=[['2020-10-07',1]]))
    def test_flow_zero_is_observation(self): self.assertEqual(k.parse_flows(flows('0','0'),TODAY),[['2026-10-07',0]])
    def test_flow_sign_and_units(self): self.assertEqual(k.parse_flows(flows('-5,000','5,000'),TODAY),[['2026-10-07',-5000]])
    def test_flow_balance(self):
        with self.assertRaises(ValueError): k.parse_flows(flows(bank='0'),TODAY)
    def test_flow_schema_change(self):
        with self.assertRaises(ValueError): k.parse_flows(flows().replace('외국인'.encode(),b'other'),TODAY)
    def test_flow_missing_not_zero(self):
        with self.assertRaises(ValueError): k.parse_flows(flows(value='-'),TODAY)
    def test_calendar(self):
        raw='<input id="searchYear" value="2026"><input id="searchMonth" value="10"><tr><td>2026.10.12.</td><td>3년물</td></tr>'
        self.assertEqual(k.parse_calendar(raw.encode())['rows'],[{'date':'2026-10-12','tenor':'3년'}])
    def test_calendar_wrong_month(self):
        raw='<input id="searchYear" value="2026"><input id="searchMonth" value="10"><tr><td>2026.09.12.</td><td>3년물</td></tr>'
        with self.assertRaises(ValueError): k.parse_calendar(raw.encode())
    def test_auction(self):
        r=k.parse_result(notice(AUCTION),'MOSF_1',30,TODAY)
        self.assertEqual((r['offered_100m'],r['bid_cover_pct'],r['yield_pct']),(18000,240.6,4.495))
    def test_auction_ratio_check(self):
        with self.assertRaises(ValueError): k.parse_result(notice(AUCTION.replace('240.6%','99%')),'MOSF_1',30,TODAY)
    def test_auction_missing_field(self):
        with self.assertRaises(ValueError): k.parse_result(notice(AUCTION.replace('가중평균낙찰금리','최고낙찰금리')),'MOSF_1',30,TODAY)
    def test_auction_fixed_fields_only(self):
        r=k.parse_result(notice(AUCTION+' secret personal prose <script>bad</script>'),'MOSF_1',30,TODAY)
        self.assertNotIn('secret',str(r))


class ComputationTests(unittest.TestCase):
    def test_same_date_join(self):
        self.assertEqual(k.difference([['2026-10-06',4],['2026-10-07',5]],[['2026-10-05',3],['2026-10-06',3]]),[['2026-10-06',100]])
    def test_change_bp(self):
        m=k.metrics([['2026-10-06',3.9],['2026-10-07',4]],'%')
        self.assertEqual(m['changes']['1'],{'value':10,'from':'2026-10-06'})
        self.assertNotIn('5',m['changes'])
    def test_observation_days_not_calendar(self):
        m=k.metrics([['2026-10-02',5],['2026-10-06',6]],'bp')
        self.assertEqual(m['changes']['1']['from'],'2026-10-02')
    def test_flow_sums_not_differences(self):
        points=[[(TODAY-dt.timedelta(days=20-i)).isoformat(),i-10] for i in range(20)]
        m=k.metrics(points,'계약')
        self.assertEqual(m['sums']['20']['value'],-10)
        self.assertEqual(m['sums']['5']['value'],35)
        self.assertEqual(m['changes'],{})
    def test_insufficient_history_no_distribution(self):
        self.assertIsNone(k.metrics([['2026-10-07',5]],'bp')['distribution'])
    def test_distribution_window_and_percentile(self):
        points=[[(TODAY-dt.timedelta(days=400-i)).isoformat(),i] for i in range(401)]
        d=k.metrics(points,'bp')['distribution']
        self.assertEqual((d['count'],d['min'],d['max'],d['range_position']),(366,35,400,100))
        self.assertAlmostEqual(d['percentile'],99.9)
    def test_flat_distribution(self):
        points=[[(TODAY-dt.timedelta(days=i)).isoformat(),3] for i in range(365,-1,-1)]
        d=k.metrics(points,'bp')['distribution'];self.assertEqual(d['percentile'],50);self.assertIsNone(d['range_position'])
    def test_all_feeds_fail_preserves_data(self):
        old={'schema':1,'feeds':{'credit':{'last_success':'2026-10-07T00:00:00+00:00','data':{'aa_spread':[['2026-10-07',68.3]]}}}}
        def fail(*a): raise OSError('do not expose URL or prose')
        with patch('builtins.print'):
            r=k.build(old,dt.datetime(2026,10,8,tzinfo=k.UTC),fail)
        self.assertFalse(r['feeds']['credit']['ok']);self.assertEqual(r['cards'][0]['metrics']['value'],68.3)
        self.assertEqual(r['feeds']['credit']['last_success'],old['feeds']['credit']['last_success'])
        self.assertNotIn('do not expose',str(r))
    def test_first_failure_no_fake_values(self):
        with patch('builtins.print'):
            r=k.build({},dt.datetime(2026,10,8,tzinfo=k.UTC),lambda *args: b'')
        self.assertEqual(r['cards'],[]);self.assertEqual(r['auctions'],[])


if __name__=='__main__': unittest.main()
