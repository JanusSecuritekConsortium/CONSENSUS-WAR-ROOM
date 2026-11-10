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

from assistant.agent import trace
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

    def run_record(self, prompts, *steps, context_chars=24000):
        recorder = RecordingExecutor(Script(*steps))
        settings = AgentConfig(enabled=True, context_chars=context_chars)
        runtime = AgentRuntime(recorder, self.registry, settings, PermissionPolicy())
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

    def test_trimmed_context_keeps_tool_ids_in_sync_with_runtime(self):
        self.registry.register(Tool('lookup', 'lookup evidence',
            schema({'value': text()}, ['value']), lambda _: {'evidence': 'x' * 4200}, Impact.READ, 'memory'))
        counts, rows = self.run_record(
            ['lookup evidence'], call('lookup', value='first'), call('lookup', value='second'),
            call('lookup', value='third'), Step(text='Done.'), context_chars=8000)
        self.assertEqual(counts['kept_runs'], 1)
        ids = [
            [item['id'] for message in row['messages'] for item in message.get('tool_calls', [])]
            for row in rows
        ]
        self.assertEqual(ids, [['call_0'], ['call_0', 'call_1'], ['call_1', 'call_2'], ['call_2']])
        self.assertEqual(rows[2]['messages'][-1], rows[3]['messages'][-3])
        self.assertEqual(rows[3]['messages'][-2]['tool_call_id'], 'call_2')

    def test_cli_loads_project_dotenv_without_overriding_process_settings(self):
        from integrations.msty.aurelius_provider import resolve_aurelius_provider_config

        root = Path(self.directory.name)
        fake_module = root / 'assistant' / 'agent' / 'trace.py'
        (root / '.env').write_text(
            'AURELIUS_EXECUTOR_MODEL=dotenv-teacher\nAURELIUS_MSTY_BASE_URL=http://127.0.0.1:1\n',
            encoding='utf-8')
        prompts = root / 'prompts.txt'
        prompts.write_text('Synthetic prompt\n', encoding='utf-8')
        cases = [
            ({}, [], 'dotenv-teacher'),
            ({'AURELIUS_EXECUTOR_MODEL': 'environment-teacher'}, [], 'environment-teacher'),
            ({'AURELIUS_EXECUTOR_MODEL': 'environment-teacher'}, ['--model', 'explicit-teacher'], 'explicit-teacher'),
        ]

        def record_without_provider(runtime, recorder, prompts, out, model):
            self.assertTrue(resolve_aurelius_provider_config().ready)
            return {'kept_runs': 1}

        for env, args, expected in cases:
            with self.subTest(model=expected), patch.dict('os.environ', env, clear=True), \
                    patch.object(trace, '__file__', str(fake_module)), \
                    patch('integrations.msty.aurelius.AureliusOperator'), \
                    patch('assistant.agent.adapters.build_registry', return_value=self.registry), \
                    patch('assistant.agent.executor.MstyExecutor') as executor, \
                    patch.object(trace, 'record', side_effect=record_without_provider), patch('builtins.print'):
                self.assertEqual(trace.main(['--prompts', str(prompts), '--out', str(self.out), *args]), 0)
                executor.assert_called_once_with(expected)

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
