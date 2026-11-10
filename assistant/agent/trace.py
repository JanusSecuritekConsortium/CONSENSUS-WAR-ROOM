"""Opt-in fine-tuning trace recorder. Never active in the normal agent route.

Unlike the audit log, traces contain prompts, tool arguments and tool output.
They stay in the git-ignored runtime directory and are written only by the
explicit CLI below. Non-read tools are never executed while recording.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

from .contracts import Step


def tool_definitions(descriptors):
    """Same wire shape MstyExecutor sends to the provider."""
    return [{'type': 'function', 'function': {
        'name': t['name'], 'description': t['description'], 'parameters': deepcopy(t['inputSchema'])}}
        for t in descriptors]


def target_message(step: Step, exchange_index: int):
    """The assistant turn the model produced, in the shape Context.record replays."""
    if step.call is None:
        return {'role': 'assistant', 'content': step.text}
    call_id = f'call_{exchange_index}'
    return {'role': 'assistant', 'content': None, 'tool_calls': [{'id': call_id, 'type': 'function',
            'function': {'name': step.call.name,
                         'arguments': json.dumps(step.call.arguments, ensure_ascii=False)}}]}


class RecordingExecutor:
    """Wraps a real executor; keeps each round's exact input and output in memory."""
    def __init__(self, inner):
        self.inner = inner
        self.steps = []

    def reset(self):
        self.steps = []

    def step(self, messages, tools, timeout):
        result = self.inner.step(messages, tools, timeout)
        self.steps.append((deepcopy(messages), deepcopy(tools), result))
        return result

    def examples(self, meta=None):
        """One supervised example per round of a completed run."""
        # Before the final answer, every recorded round adds one tool exchange.
        # Context.record counts all exchanges, including ones trimmed from the prompt.
        return [{'messages': messages + [target_message(step, index - 1)],
                 'tools': tool_definitions(tools),
                 'meta': dict(meta or {}, round=index)}
                for index, (messages, tools, step) in enumerate(self.steps, 1)]


def record(runtime, recorder, prompts, out_path, model=''):
    """Run each prompt through the real loop; keep only cleanly completed runs."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    counts = {'prompts': 0, 'kept_runs': 0, 'examples': 0, 'dropped': {}}
    with out_path.open('a', encoding='utf-8') as handle:
        for prompt in prompts:
            counts['prompts'] += 1
            recorder.reset()
            result = runtime.run(prompt)
            if result.status == 'waiting_approval':
                runtime.cancel(result.run_id)  # Recording never approves a write.
            if result.status != 'completed':
                key = result.reason or result.status
                counts['dropped'][key] = counts['dropped'].get(key, 0) + 1
                continue
            rows = recorder.examples({'run_id': result.run_id, 'teacher': model,
                                      'tools_used': list(result.executed_tools)})
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
            counts['kept_runs'] += 1
            counts['examples'] += len(rows)
    return counts


def read_prompts(path):
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith('#')]


def main(argv=None):
    parser = argparse.ArgumentParser(description='Record AURELIUS agent traces for fine-tuning')
    parser.add_argument('--prompts', required=True, help='UTF-8 text file, one operator request per line')
    parser.add_argument('--out', help='JSONL output; default is the git-ignored agent runtime directory')
    parser.add_argument('--model', default='',
                        help='Teacher model id; defaults to the AURELIUS model settings in the environment or project .env')
    args = parser.parse_args(argv)
    try:
        import os
        from dotenv import load_dotenv
        from core.paths import ARBITER_DIR
        from integrations.msty.aurelius import AureliusOperator
        from .adapters import Filesystem, build_registry
        from .config import AgentConfig
        from .executor import MstyExecutor
        from .loop import AgentRuntime
        from .permissions import PermissionPolicy
        root = Path(__file__).resolve().parents[2]
        load_dotenv(root / '.env', override=False)
        settings = AgentConfig.from_env()
        model = args.model or settings.executor_model or os.getenv('AURELIUS_MODEL', '')
        # Explicit invocation is the opt-in; auto-approved writes stay off regardless of environment.
        settings = replace(settings, enabled=True, auto_write_tools=frozenset(), executor_model=model)
        recorder = RecordingExecutor(MstyExecutor(model))
        # No write root and no Telegram sender: recording has read tools only at its disposal.
        registry = build_registry(AureliusOperator(), Filesystem(root))
        runtime = AgentRuntime(recorder, registry, settings, PermissionPolicy())
        out = args.out or ARBITER_DIR / 'aurelius_agent' / 'traces' / 'traces.jsonl'
        counts = record(runtime, recorder, read_prompts(args.prompts), out, model)
        print(json.dumps(dict(counts, out=str(out)), ensure_ascii=False))
        return 0 if counts['kept_runs'] else 1
    except Exception as error:
        print(json.dumps({'status': 'degraded', 'error_type': type(error).__name__}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
