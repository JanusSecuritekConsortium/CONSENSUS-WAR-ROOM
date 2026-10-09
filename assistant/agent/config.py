from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping


@dataclass(frozen=True)
class AgentConfig:
    enabled: bool = False
    max_rounds: int = 8
    max_tools: int = 6
    context_chars: int = 24000
    result_chars: int = 6000
    deadline_seconds: float = 120.0
    executor_backend: str = 'msty'
    executor_model: str = ''
    background_enabled: bool = False
    scheduled_enabled: bool = False
    auto_write_tools: frozenset[str] = frozenset()

    def __post_init__(self):
        if not 1 <= self.max_rounds <= 32 or not 1 <= self.max_tools <= 32:
            raise ValueError('Agent round/tool limits must be between 1 and 32')
        if not 8000 <= self.context_chars <= 128000 or not 256 <= self.result_chars <= 16000:
            raise ValueError('Invalid agent context/result budget')
        if not 1 <= self.deadline_seconds <= 1800:
            raise ValueError('Invalid agent deadline')
        if self.executor_backend != 'msty':
            raise ValueError('Only the verified existing Msty backend is configured')
        if 'ajax' in self.executor_model.casefold():
            raise ValueError('Ajax activation requires verified weights, license and backend; unavailable')

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None):
        env = os.environ if environ is None else environ
        def flag(name):
            value = env.get(name, 'false').strip().lower()
            if value not in {'true', 'false', '1', '0', 'yes', 'no', 'on', 'off'}:
                raise ValueError('Invalid boolean configuration: ' + name)
            return value in {'true', '1', 'yes', 'on'}
        return cls(
            enabled=flag('AURELIUS_AGENT_ENABLED'),
            background_enabled=flag('AURELIUS_AGENT_BACKGROUND_ENABLED'),
            scheduled_enabled=flag('AURELIUS_AGENT_SCHEDULED_ENABLED'),
            max_rounds=int(env.get('AURELIUS_AGENT_MAX_ROUNDS', '8')),
            max_tools=int(env.get('AURELIUS_AGENT_MAX_TOOLS', '6')),
            context_chars=int(env.get('AURELIUS_AGENT_CONTEXT_CHARS', '24000')),
            result_chars=int(env.get('AURELIUS_AGENT_RESULT_CHARS', '6000')),
            deadline_seconds=float(env.get('AURELIUS_AGENT_DEADLINE_SECONDS', '120')),
            executor_backend=env.get('AURELIUS_EXECUTOR_BACKEND', 'msty'),
            executor_model=env.get('AURELIUS_EXECUTOR_MODEL', ''),
        )
