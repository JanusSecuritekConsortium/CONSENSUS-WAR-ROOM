from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import Event, RLock
from time import monotonic, perf_counter
from uuid import uuid4
from .context import Context
from .contracts import AgentResult, Impact, ToolCall
from .permissions import PermissionPolicy, fingerprint


def audit(event, **fields):
    # Payloads, model output, personal facts and exception text never enter this audit.
    try:
        from core.logging import log_event
        log_event('aurelius_agent_' + event, fields)
    except Exception:
        pass


@dataclass
class _Run:
    id: str
    context: Context
    started: float
    started_wall: float = field(default_factory=perf_counter)
    cancelled: Event = field(default_factory=Event)
    rounds: int = 0
    executed: list = field(default_factory=list)
    attempted: set = field(default_factory=set)
    pending: ToolCall | None = None
    errors: bool = False
    lock: RLock = field(default_factory=RLock)


class AgentRuntime:
    def __init__(self, executor, registry, config, policy=None):
        self.executor = executor
        self.registry = registry
        self.config = config
        self.policy = policy or PermissionPolicy(auto_write_tools=config.auto_write_tools)
        self._runs = {}
        self._lock = RLock()

    def run(self, prompt, evidence=None, cancel_event=None):
        run_id = uuid4().hex
        if not self.config.enabled:
            return AgentResult(run_id, 'disabled', '', reason='feature_disabled')
        if not isinstance(prompt, str) or not prompt.strip():
            return AgentResult(run_id, 'degraded', 'AURELIUS requires nonempty operator input.', reason='invalid_input')
        try:
            context = Context(prompt, self.config.context_chars, self.config.result_chars, evidence)
        except Exception:
            return AgentResult(run_id, 'degraded', 'AURELIUS input exceeds its context budget.', reason='input_budget')
        run = _Run(run_id, context, monotonic(), cancelled=cancel_event or Event())
        with self._lock:
            expired = [key for key, item in self._runs.items()
                       if item.pending is not None and monotonic() - item.started > self.config.deadline_seconds]
            for key in expired:
                self._runs.pop(key, None)
            if len(self._runs) >= 32:
                return AgentResult(run_id, 'degraded', 'AURELIUS has too many pending runs.', reason='capacity')
            self._runs[run_id] = run
        audit('start', run_id=run_id)
        with run.lock:
            return self._advance(run)

    def resume(self, run_id):
        with self._lock:
            run = self._runs.get(run_id)
        if run is None:
            return AgentResult(run_id, 'degraded', 'Run unavailable; no action executed.', reason='run_missing')
        with run.lock:
            with self._lock:
                if run_id not in self._runs:
                    return AgentResult(run_id, 'degraded', 'Run already finished.', reason='run_missing')
            return self._advance(run)

    def cancel(self, run_id):
        with self._lock:
            run = self._runs.get(run_id)
            if run:
                run.cancelled.set()
        if run:
            # Drop idle approval waits without affecting active callbacks.
            if run.lock.acquire(blocking=False):
                try:
                    self._finish(run, 'cancelled', 'AURELIUS run cancelled.')
                finally:
                    run.lock.release()
        return run is not None

    def _finish(self, run, status, text, reason=None, pending=None):
        result = AgentResult(run.id, status, text, run.rounds, list(run.executed), pending, reason)
        if status != 'waiting_approval':
            with self._lock:
                self._runs.pop(run.id, None)
        audit('result', run_id=run.id, status=status, rounds=run.rounds, reason=reason,
              duration_ms=round((perf_counter() - run.started_wall)*1000, 2))
        return result

    def _advance(self, run):
        while True:
            remaining = self.config.deadline_seconds - (monotonic() - run.started)
            if run.cancelled.is_set():
                return self._finish(run, 'cancelled', 'AURELIUS run cancelled.')
            if remaining <= 0:
                return self._finish(run, 'degraded', 'AURELIUS reached its execution deadline.', 'deadline')
            if run.pending is None:
                if run.rounds >= self.config.max_rounds:
                    return self._finish(run, 'degraded', 'AURELIUS reached its round limit.', 'round_limit')
                query = run.context.base[1]['content']
                if run.context.exchanges:
                    query += ' ' + run.context.exchanges[-1][1]['content'][:1000]
                tools = self.registry.retrieve(query, self.config.max_tools)
                descriptors = [deepcopy(t.descriptor()) for t in tools]
                try:
                    messages = run.context.messages(descriptors)
                    step = self.executor.step(messages, descriptors, remaining)
                    run.rounds += 1
                    if step.call is None:
                        if not step.text.strip():
                            raise ValueError('Empty final response')
                        if run.cancelled.is_set() or monotonic() - run.started > self.config.deadline_seconds:
                            continue
                        if len(step.text) > self.config.result_chars:
                            return self._finish(run, 'degraded', step.text[:self.config.result_chars], 'output_limit')
                        return self._finish(run, 'degraded' if run.errors else 'completed', step.text,
                                            'tool_failure' if run.errors else None)
                    if step.call.name not in {t.name for t in tools}:
                        raise ValueError('Tool not retrieved for this round')
                    # Reject excessive arguments before hashing or validation.
                    from .context import size
                    if size(step.call.arguments) > self.config.result_chars:
                        raise ValueError('Tool arguments exceed budget')
                    self.registry.validate(step.call.name, step.call.arguments)
                    run.pending = ToolCall(step.call.name, deepcopy(step.call.arguments))
                except Exception as error:
                    audit('executor_error', run_id=run.id, error_type=type(error).__name__)
                    return self._finish(run, 'degraded', 'AURELIUS executor unavailable or returned an invalid response.', 'executor_failure')
                continue  # Check deadline/cancellation again before any tool side effect.
            call = run.pending
            tool = self.registry.get(call.name)
            if not self.policy.allowed(run.id, tool, call.arguments, run.context.untrusted_seen):
                return self._finish(run, 'waiting_approval', 'AURELIUS needs host approval for this exact action.',
                                    'permission_required', {'name': call.name, 'arguments': deepcopy(call.arguments),
                                    'impact': tool.impact.value, 'fingerprint': fingerprint(run.id, call.name, call.arguments)})
            key = fingerprint(run.id, call.name, call.arguments)
            if tool.impact != Impact.READ and key in run.attempted:
                return self._finish(run, 'degraded', 'AURELIUS will not repeat an attempted write.', 'duplicate_write')
            run.attempted.add(key)  # Record BEFORE calling: a timeout may have applied the action.
            audit('tool_start', run_id=run.id, tool=call.name, impact=tool.impact.value)
            try:
                result = tool.handler(deepcopy(call.arguments))
                if isinstance(result, dict) and (result.get('isError') or
                    any(result.get(key) is False for key in ('saved', 'delivered')) or
                    result.get('status') in {'error', 'failed', 'unavailable'}):
                    raise RuntimeError('Tool reported a failed outcome')
                run.executed.append(tool.name)
                run.context.record(call, result, tool.untrusted)
            except Exception as error:
                audit('tool_error', run_id=run.id, tool=call.name, error_type=type(error).__name__)
                if tool.impact != Impact.READ:
                    return self._finish(run, 'uncertain', 'AURELIUS could not verify the action outcome; inspect it before retrying.', 'write_outcome_unknown')
                run.errors = True
                run.context.record(call, {'status': 'unavailable', 'error_type': type(error).__name__}, True)
            run.pending = None
