"""Failures must preserve valid observations and never report an old run as fresh."""
import datetime as dt
import io
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

import korea_market as k
import korea_status as status
from test_korea_market import export, TODAY

NOW=dt.datetime(2026,10,8,tzinfo=k.UTC)


class NetworkTests(unittest.TestCase):
    def test_transient_failure_retries_once(self):
        calls=[]
        def opener(*args, **kwargs):
            calls.append(kwargs)
            if len(calls)==1: raise urllib.error.HTTPError('https://example.invalid',503,'temporary',{},None)
            return io.BytesIO(b'good')
        sleeps=[];fetch=k.PublicFetcher(opener=opener,sleep=sleeps.append)
        self.assertEqual(fetch('url',{'q':'x'}),b'good');self.assertEqual(len(calls),2)
        self.assertEqual(calls[0]['data'],calls[1]['data']);self.assertEqual(sleeps,[1])

    def test_nontransient_does_not_retry(self):
        calls=[]
        def opener(*args, **kwargs):
            calls.append(1);raise urllib.error.HTTPError('url',404,'missing',{},None)
        with self.assertRaises(urllib.error.HTTPError): k.PublicFetcher(opener=opener)('url')
        self.assertEqual(len(calls),1)

    def test_timeout_retries_are_bounded(self):
        with patch.object(k.urllib.request,'urlopen',side_effect=TimeoutError) as opener:
            fetch=k.PublicFetcher(opener=opener,sleep=lambda n:None)
            with self.assertRaises(TimeoutError): fetch('url')
        self.assertEqual(opener.call_count,2)

    def test_feed_budget_can_reset_but_total_cannot(self):
        clock=[0];fetch=k.PublicFetcher(budget=10,per_feed=3,clock=lambda:clock[0])
        fetch.start_feed();clock[0]=4
        with self.assertRaises(k.FeedError): fetch.remaining()
        fetch.start_feed();self.assertEqual(fetch.remaining(),3)
        clock[0]=11;fetch.start_feed()
        with self.assertRaises(k.FeedError): fetch.remaining()

    def test_slow_body_is_not_accepted_after_budget(self):
        clock=[0]
        class Slow(io.BytesIO):
            def read1(self,n): clock[0]+=3;return super().read1(n)
        fetch=k.PublicFetcher(budget=2,clock=lambda:clock[0],opener=lambda *a,**kw:Slow(b'x'))
        with self.assertRaises(k.FeedError): fetch('url')

    def test_oversized_body_does_not_retry(self):
        with patch.object(k,'LIMIT',5):
            fetch=k.PublicFetcher(opener=lambda *a,**kw:io.BytesIO(b'123456'))
            with self.assertRaises(ValueError): fetch('url')


class SnapshotTests(unittest.TestCase):
    def old(self):
        return {'schema':1,'feeds':{'credit':{'data':{'aa_spread':[['2026-10-07',68.3]]},'last_success':'2026-10-07T00:00:00+00:00'}}}

    def build(self,points,now=NOW):
        def fetch(url,*args):
            if 'chart_id=857' in url: return export(points=points)
            raise OSError('private upstream details')
        with patch('builtins.print'): return k.build(self.old(),now,fetch)

    def test_regression_keeps_newer_success(self):
        result=self.build([['2026-10-06',0.7]])
        self.assertEqual(result['feeds']['credit']['reason'],'regressed')
        self.assertEqual(result['cards'][0]['metrics']['date'],'2026-10-07')

    def test_same_date_revision_allowed(self):
        result=self.build([['2026-10-07',0.69]])
        self.assertTrue(result['feeds']['credit']['ok']);self.assertEqual(result['cards'][0]['metrics']['value'],69)

    def test_stale_success_is_rejected(self):
        result=self.build([['2026-10-07',0.7]],NOW+dt.timedelta(days=8))
        self.assertFalse(result['feeds']['credit']['ok']);self.assertEqual(result['feeds']['credit']['reason'],'stale')
        self.assertTrue(result['cards'][0]['stale'])

    def test_successful_feed_survives_other_failures(self):
        result=self.build([['2026-10-08',0.7]])
        self.assertTrue(result['feeds']['credit']['ok']);self.assertFalse(result['feeds']['money']['ok'])
        self.assertEqual(result['cards'][0]['metrics']['date'],'2026-10-08')
        self.assertNotIn('private upstream',json.dumps(result))

    def test_empty_calendar_rejected(self):
        with self.assertRaises(k.FeedError):
            k.parse_calendar(b'<input id="searchYear" value="2026"><input id="searchMonth" value="10">',TODAY)

    def test_previous_month_calendar_rejected(self):
        with self.assertRaises(k.FeedError):
            k.parse_calendar(b'<input id="searchYear" value="2026"><input id="searchMonth" value="09">',TODAY)

    def test_duplicate_calendar_rejected(self):
        raw='<input id="searchYear" value="2026"><input id="searchMonth" value="10">'+2*'<tr><td>2026.10.12.</td><td>3년물</td></tr>'
        with self.assertRaises(k.FeedError): k.parse_calendar(raw.encode(),TODAY)

    def test_unreadable_previous_snapshot_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'korea.json';path.write_text('{broken',encoding='utf-8')
            with patch('builtins.print'),patch.object(k,'build') as build:
                self.assertEqual(k.main(['--out',folder]),1)
            build.assert_not_called();self.assertEqual(path.read_text(),'{broken')

    def test_invalid_previous_type_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'korea.json';path.write_text('[]',encoding='utf-8')
            with patch('builtins.print'): self.assertEqual(k.main(['--out',folder]),1)
            self.assertEqual(path.read_text(),'[]')

    def test_atomic_replace_failure_keeps_file_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'korea.json';path.write_text('old',encoding='utf-8')
            with patch.object(Path,'replace',side_effect=PermissionError):
                with self.assertRaises(PermissionError): k.atomic_json(path,{'new':True})
            self.assertEqual(path.read_text(),'old');self.assertEqual(list(Path(folder).iterdir()),[path])

    def test_nonfinite_not_written(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'korea.json';path.write_text('old',encoding='utf-8')
            with self.assertRaises(ValueError): k.atomic_json(path,{'value':float('nan')})
            self.assertEqual(path.read_text(),'old')


class RunStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.out=Path(self.temp.name)
        self.snapshot={'schema':1,'checked_at':NOW.isoformat(),'feeds':{key:{'ok':True} for key in status.FEEDS}}
        self.write()
    def write(self): k.atomic_json(self.out/'korea.json',self.snapshot)
    def update(self,state,now=NOW): return status.update(self.out,state,now,env={})
    def test_started_is_not_success(self):
        r=self.update('started');self.assertEqual(r['state'],'running');self.assertFalse(r['ok'])
    def test_current_completed_snapshot_is_success(self):
        self.update('started');r=self.update('success',NOW+dt.timedelta(seconds=5));self.assertTrue(r['ok'])
    def test_old_snapshot_cannot_pass_success(self):
        self.update('started',NOW+dt.timedelta(seconds=5));self.assertFalse(self.update('success',NOW+dt.timedelta(seconds=6))['ok'])
    def test_missing_feed_cannot_pass_success(self):
        self.update('started');del self.snapshot['feeds']['rates'];self.write();self.assertFalse(self.update('success')['ok'])
    def test_failed_feed_cannot_pass_success(self):
        self.update('started');self.snapshot['feeds']['rates']['ok']=False;self.write();self.assertFalse(self.update('success')['ok'])
    def test_failure_preserves_data_and_previous_success(self):
        self.update('started');self.update('success');before=(self.out/'korea.json').read_bytes()
        self.update('started',NOW+dt.timedelta(days=1));r=self.update('failure',NOW+dt.timedelta(days=1))
        self.assertEqual(r['last_success'],NOW.isoformat());self.assertFalse(r['ok'])
        self.assertEqual((self.out/'korea.json').read_bytes(),before)
    def test_missing_start_cannot_report_success(self): self.assertFalse(self.update('success')['ok'])
    def test_skipped_or_cancelled_is_failure(self):
        for state in ['skipped','cancelled']:
            self.update('started');self.assertEqual(self.update(state)['state'],'failure')


if __name__=='__main__': unittest.main()
