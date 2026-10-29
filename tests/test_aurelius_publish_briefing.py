"""Offline tests for the scheduled briefing publish tool; no Telegram or vault access."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.mcp import consensus_mcp_server as server

MADRID = ZoneInfo('Europe/Madrid')
PUBLISH = 'integrations.msty.personal.publication.publish'


def at(hour, minute, day=dt.date(2026, 10, 27)):
    return dt.datetime.combine(day, dt.time(hour, minute), MADRID)


class PublishBriefingToolTests(unittest.TestCase):
    def setUp(self):
        # Run records go to a temporary folder, and no failure notice reaches Telegram.
        runs = tempfile.TemporaryDirectory()
        self.addCleanup(runs.cleanup)
        self.runs = Path(runs.name)
        self.notices = []
        for name, value in (('_runs_dir', lambda: self.runs),
                            ('_notify_late_failure', lambda mode, error: self.notices.append((mode, str(error))))):
            patcher = patch.object(server, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def call(self, now, arguments, tool='aurelius_publish_briefing'):
        with patch.object(server, '_madrid_now', return_value=now):
            return server.call_tool(tool, arguments)

    def run_record(self, mode, day=dt.date(2026, 10, 27)):
        return json.loads((self.runs / f'{day.isoformat()}-{mode}.run.json').read_text(encoding='utf-8'))

    def test_inside_window_publishes_with_telegram(self):
        result_by_mode = {'status': 'delivered', 'note': 'n.md', 'memory': 'linked',
                          'consultation_id': 'abc', 'message_ids': [7]}
        for mode, now in (('morning', at(7, 0)), ('morning', at(9, 59)),
                          ('evening', at(17, 30)), ('evening', at(20, 29))):
            with self.subTest(mode=mode, now=now), patch(PUBLISH, return_value=result_by_mode) as publish:
                result = self.call(now, {'mode': mode})
                publish.assert_called_once_with(mode, send=True)
                self.assertEqual(result['status'], 'delivered')
                self.assertEqual(result['mode'], mode)
                self.assertEqual(result['message_ids'], [7])

    def test_outside_window_sends_nothing(self):
        for mode, now in (('morning', at(6, 59)), ('morning', at(10, 0)), ('morning', at(17, 45)),
                          ('evening', at(17, 29)), ('evening', at(20, 30)), ('evening', at(7, 30))):
            with self.subTest(mode=mode, now=now), patch(PUBLISH) as publish:
                result = self.call(now, {'mode': mode})
                publish.assert_not_called()
                self.assertEqual(result['status'], 'outside_window')
                self.assertIn('Europe/Madrid', result['window'])

    def test_window_uses_local_time_across_daylight_saving_change(self):
        # 25 Oct 2026 switches from CEST to CET; 07:30 local is 06:30 UTC.
        now = dt.datetime(2026, 10, 25, 6, 30, tzinfo=dt.timezone.utc).astimezone(MADRID)
        with patch(PUBLISH, return_value={'status': 'delivered', 'message_ids': [1]}) as publish:
            self.assertEqual(self.call(now, {'mode': 'morning'})['status'], 'delivered')
            publish.assert_called_once()

    def test_repeat_and_uncertain_deliveries_are_left_to_publish(self):
        with patch(PUBLISH, return_value={'status': 'already_delivered', 'note': 'n.md', 'message_ids': [3]}):
            self.assertEqual(self.call(at(8, 0), {'mode': 'morning'})['status'], 'already_delivered')
        with patch(PUBLISH, side_effect=RuntimeError('Delivery uncertain; inspect saved receipt before resending')):
            with self.assertRaisesRegex(RuntimeError, 'uncertain'):
                self.call(at(8, 0), {'mode': 'morning'})

    def test_slow_publish_returns_before_msty_timeout_and_still_finishes(self):
        release = threading.Event()
        calls = []

        def slow_publish(mode, send):
            calls.append(mode)
            release.wait(5)
            return {'status': 'delivered', 'message_ids': [5]}

        with patch.object(server, 'PUBLISH_WAIT_SECONDS', 0.05), patch(PUBLISH, side_effect=slow_publish):
            started = time.monotonic()
            first = self.call(at(7, 0), {'mode': 'morning'})
            second = self.call(at(7, 1), {'mode': 'morning'})
            self.assertLess(time.monotonic() - started, 2)
            self.assertEqual(first['status'], 'publishing')
            self.assertEqual(second['status'], 'publishing')
            self.assertEqual(calls, ['morning'])  # no duplicate publish while one is running
            worker = server._publishing['morning']
            self.assertFalse(worker.daemon)
            self.assertEqual(self.run_record('morning')['status'], 'running')
            release.set()
            worker.join(5)
            self.assertEqual(worker.outcome['result']['status'], 'delivered')
        self.assertEqual(self.run_record('morning')['status'], 'delivered')
        self.assertEqual(self.notices, [])

    def test_late_failure_is_recorded_and_sent_to_the_user(self):
        release = threading.Event()

        def failing_publish(mode, send):
            release.wait(5)
            raise RuntimeError('Telegram request failed; delivery may require verification')

        with patch.object(server, 'PUBLISH_WAIT_SECONDS', 0.05), patch(PUBLISH, side_effect=failing_publish):
            self.assertEqual(self.call(at(17, 30), {'mode': 'evening'})['status'], 'publishing')
            worker = server._publishing['evening']
            release.set()
            worker.join(5)
        record = self.run_record('evening')
        self.assertEqual(record['status'], 'failed')
        self.assertIn('Telegram request failed', record['error'])
        self.assertIn('finished_at', record)
        self.assertEqual(self.notices, [('evening', 'Telegram request failed; delivery may require verification')])

    def test_failure_inside_the_wait_is_returned_without_extra_notice(self):
        with patch(PUBLISH, side_effect=RuntimeError('Another briefing publication is running')):
            with self.assertRaisesRegex(RuntimeError, 'Another briefing'):
                self.call(at(8, 0), {'mode': 'morning'})
        self.assertEqual(self.run_record('morning')['status'], 'failed')
        self.assertEqual(self.notices, [])

    def test_status_tool_reads_the_run_record_and_sends_nothing(self):
        self.assertEqual(self.call(at(9, 0), {'mode': 'morning'}, 'aurelius_briefing_status')['status'], 'not_started')
        with patch(PUBLISH, return_value={'status': 'awaiting_choice', 'message_ids': [4]}) as publish:
            self.call(at(7, 0), {'mode': 'morning'})
            status = self.call(at(9, 0), {'mode': 'morning'}, 'aurelius_briefing_status')
            publish.assert_called_once()
        self.assertEqual(status['status'], 'awaiting_choice')
        self.assertEqual(status['date'], '2026-10-27')
        tool = next(t for t in server.TOOLS if t['name'] == 'aurelius_briefing_status')
        self.assertTrue(tool['annotations']['readOnlyHint'])
        with self.assertRaises(ValueError):
            self.call(at(9, 0), {'mode': 'weekly'}, 'aurelius_briefing_status')

    def test_rejects_other_arguments(self):
        for arguments in ({}, {'mode': 'weekly'}, {'mode': 'morning', 'edition': 'x'}, {'kind': 'morning'}):
            with self.subTest(arguments=arguments), patch(PUBLISH) as publish:
                with self.assertRaises(ValueError):
                    self.call(at(8, 0), arguments)
                publish.assert_not_called()

    def test_jsonrpc_failure_is_an_error_not_a_result(self):
        message = {'jsonrpc': '2.0', 'id': 9, 'method': 'tools/call',
                   'params': {'name': 'aurelius_publish_briefing', 'arguments': {'mode': 'evening'}}}
        with patch.object(server, '_madrid_now', return_value=at(17, 31)), \
                patch(PUBLISH, side_effect=RuntimeError('Telegram request failed; delivery may require verification')):
            response = server.handle_jsonrpc(message)
        self.assertNotIn('result', response)
        self.assertIn('Telegram request failed', response['error']['message'])

    def test_tool_is_listed_as_a_sending_tool(self):
        tool = next(t for t in server.TOOLS if t['name'] == 'aurelius_publish_briefing')
        self.assertFalse(tool['annotations']['readOnlyHint'])
        self.assertEqual(tool['inputSchema']['properties']['mode']['enum'], ['morning', 'evening'])
        self.assertEqual(tool['inputSchema']['required'], ['mode'])
        self.assertIn('aurelius_publish_briefing', server.TOOL_HANDLERS)


if __name__ == '__main__':
    unittest.main()
