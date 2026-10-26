"""Offline tests for the scheduled briefing publish tool; no Telegram or vault access."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
import sys
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
    def call(self, now, arguments):
        with patch.object(server, '_madrid_now', return_value=now):
            return server.call_tool('aurelius_publish_briefing', arguments)

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
