"""Synthetic fixtures only: units, missing dates, sums, schema drift and fallback."""
import datetime as dt
import html
import io
import unittest
import zipfile
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
        with self.assertRaises(ValueError): self.parse(OFFER.replace('(1)', '(3)'))
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
