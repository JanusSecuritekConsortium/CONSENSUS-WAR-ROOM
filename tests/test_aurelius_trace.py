"""Offline contracts for the opt-in fine-tuning trace recorder."""
from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from assistant.agent.adapters import schema, text
from assistant.agent.config import AgentConfig
from assistant.agent.contracts import Impact, Step, Tool, ToolCall
from assistant.agent.loop import AgentRuntime
from assistant.agent.permissions import PermissionPolicy
from assistant.agent.registry import ToolRegistry
from assistant.agent.trace import RecordingExecutor, read_prompts, record


class Script:
    def __init__(self, *steps):
        self.steps = iter(steps)

    def step(self, messages, tools, timeout):
        step = next(self.steps)
        if isinstance(step, Exception):
            raise step
        return step


def call(name, **args):
    return Step(call=ToolCall(name, args))


class TraceTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict('os.environ', {'AURELIUS_ODYSSEUS_ENABLED': 'false'})
        environment.start()
        self.addCleanup(environment.stop)
        self.registry = ToolRegistry()
        self.written = []
        self.registry.register(Tool('search', 'read memory report analysis search',
            schema({'value': text()}, ['value']), lambda a: {'value': a['value']}, Impact.READ, 'memory'))
        self.registry.register(Tool('store', 'write memory report analysis store',
            schema({'value': text()}, ['value']), lambda a: self.written.append(a) or {'saved': True},
            Impact.HIGH, 'memory'))
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.out = Path(self.directory.name) / 'nested' / 'traces.jsonl'

    def run_record(self, prompts, *steps):
        recorder = RecordingExecutor(Script(*steps))
        runtime = AgentRuntime(recorder, self.registry, AgentConfig(enabled=True), PermissionPolicy())
        counts = record(runtime, recorder, prompts, self.out, 'teacher-model')
        rows = [json.loads(line) for line in self.out.read_text(encoding='utf-8').splitlines()] \
            if self.out.exists() else []
        return counts, rows

    def test_completed_run_yields_one_example_per_round_in_provider_shape(self):
        counts, rows = self.run_record(['search memory'], call('search', value='tópico'), Step(text='Done.'))
        self.assertEqual((counts['kept_runs'], counts['examples'], counts['dropped']), (1, 2, {}))
        first, final = rows
        target = first['messages'][-1]
        self.assertEqual([m['role'] for m in first['messages']], ['system', 'user', 'assistant'])
        self.assertIsNone(target['content'])
        self.assertEqual(target['tool_calls'][0]['id'], 'call_0')
        self.assertEqual(json.loads(target['tool_calls'][0]['function']['arguments']), {'value': 'tópico'})
        self.assertEqual({t['function']['name'] for t in first['tools']}, {'search', 'store'})
        self.assertEqual(first['tools'][0]['type'], 'function')
        self.assertIn('parameters', first['tools'][0]['function'])
        # The second example replays the exact exchange the loop sent, then the final answer.
        self.assertEqual([m['role'] for m in final['messages']],
                         ['system', 'user', 'assistant', 'tool', 'assistant'])
        self.assertEqual(final['messages'][2], target)
        self.assertEqual(final['messages'][3]['tool_call_id'], 'call_0')
        self.assertEqual(final['messages'][-1], {'role': 'assistant', 'content': 'Done.'})
        self.assertEqual((first['meta']['round'], final['meta']['round']), (1, 2))
        self.assertEqual(final['meta']['teacher'], 'teacher-model')
        self.assertEqual(final['meta']['tools_used'], ['search'])

    def test_write_requests_are_never_executed_or_kept(self):
        counts, rows = self.run_record(['store memory'], call('store', value='x'))
        self.assertEqual(self.written, [])
        self.assertEqual(rows, [])
        self.assertEqual(counts['dropped'], {'permission_required': 1})

    def test_failed_runs_are_dropped_and_later_prompts_still_record(self):
        counts, rows = self.run_record(
            ['search memory', 'search memory', 'search memory'],
            RuntimeError('provider down'),
            call('missing', value='x'),
            Step(text='Plain answer.'))
        self.assertEqual(counts['prompts'], 3)
        self.assertEqual(counts['dropped'], {'executor_failure': 2})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['messages'][-1]['content'], 'Plain answer.')

    def test_prompt_file_skips_blanks_and_comments(self):
        path = Path(self.directory.name) / 'prompts.txt'
        path.write_text('# heading\n\n  primera petición  \nsecond request\n', encoding='utf-8')
        self.assertEqual(read_prompts(path), ['primera petición', 'second request'])


if __name__ == '__main__':
    unittest.main()
