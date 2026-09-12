from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
import sqlite3
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest
from unittest.mock import patch

from integrations.msty.aurelius_reports import parse_feed, morning_report, evening_report, collect_report
from integrations.mcp.consensus_mcp_server import handle_jsonrpc


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 12, 7, tzinfo=timezone.utc)

    def item(self, title='Real headline', date=None, url='https://example.org/news'):
        return '<item><title>' + title + '</title><link>' + url + '</link><pubDate>' + format_datetime(date or self.now) + '</pubDate></item>'

    def test_date_and_link_validation(self):
        data = ('<rss><channel>' + self.item() + self.item(date=self.now-timedelta(days=4)) + self.item(url='http://example.org') + self.item(url='https://bbc.co.uk/iplayer/episode') + '<item><title>Undated</title></item></channel></rss>').encode()
        self.assertEqual(len(parse_feed(data, self.now)), 1)

    def test_unsafe_xml(self):
        with self.assertRaises(ValueError):
            parse_feed(b'<!DOCTYPE rss><rss/>', self.now)

    def test_partial_sources(self):
        item = {'title': 'Real headline', 'url': 'https://example.org/news', 'published': self.now}
        results = [{'category': 'World', 'name': 'Publisher', 'items': [item], 'error': None}, {'name': 'Offline', 'items': [], 'error': 'URLError'}]
        body = morning_report(results, self.now)
        self.assertIn('Publisher reports: Real headline', body)
        self.assertIn('retrieval failed', body)
        self.assertEqual(body.count('AURELIUS MORNING BRIEF'), 1)
        self.assertIn('2026-09-12 09:00 UTC+0200', body)
        self.assertNotIn('time unavailable', body)
        self.assertIn('Published:', body)
        self.assertNotIn('https://', body)
        self.assertNotIn('http://', body)

    def test_total_failure_no_fake_news(self):
        body = morning_report([{'name': 'Offline', 'items': [], 'error': 'URLError'}], self.now)
        self.assertIn('NO VERIFIED CURRENT DATA', body)
        self.assertNotIn('reports:', body)

    def test_read_only_evening(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'test.db'
            with sqlite3.connect(path) as db:
                db.execute('CREATE TABLE scheduled_job_dispatches(id,label,status,scheduled_for)')
                db.execute('CREATE TABLE scheduled_job_delivery_attempts(dispatch_id,destination_kind,status)')
                db.execute('INSERT INTO scheduled_job_dispatches VALUES(?,?,?,?)', ('run','Morning Brief','completed','2026-09-12T05:00:00Z'))
                db.execute('INSERT INTO scheduled_job_delivery_attempts VALUES(?,?,?)', ('run','channel','delivered'))
            db.close()
            before = path.read_bytes()
            body = evening_report(path, self.now)
            self.assertIn('Morning Brief: completed', body)
            self.assertIn('Telegram delivery: delivered', body)
            self.assertEqual(before, path.read_bytes())

    def test_mcp_handoff(self):
        with patch('integrations.msty.aurelius_reports.collect_report', return_value='AURELIUS MORNING BRIEF\nGenerated: test'):
            response = handle_jsonrpc({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'aurelius_report','arguments':{'kind':'morning'}}})
        self.assertIn('body_text', response['result']['content'][0]['text'])

    def test_invalid_kind(self):
        with self.assertRaises(ValueError):
            collect_report('arbitrary')

    def test_tool_is_declared_read_only(self):
        response = handle_jsonrpc({'jsonrpc':'2.0','id':2,'method':'tools/list'})
        tool = next(tool for tool in response['result']['tools'] if tool['name']=='aurelius_report')
        self.assertTrue(tool['annotations']['readOnlyHint'])
        self.assertFalse(tool['annotations']['destructiveHint'])


if __name__ == '__main__':
    unittest.main()
