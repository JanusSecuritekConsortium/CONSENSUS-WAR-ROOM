from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol


class Impact(str, Enum):
    READ = 'read'
    WRITE = 'write'
    HIGH = 'high_impact'


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    schema: dict
    handler: Callable[[dict], Any]
    impact: Impact = Impact.HIGH
    domain: str = 'external'
    untrusted: bool = True

    def descriptor(self):
        return {'name': self.name, 'description': self.description,
                'inputSchema': self.schema, 'impact': self.impact.value}


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict


@dataclass(frozen=True)
class Step:
    text: str = ''
    call: ToolCall | None = None


class Executor(Protocol):
    def step(self, messages: list[dict], tools: list[dict], timeout: float) -> Step: ...


@dataclass
class AgentResult:
    run_id: str
    status: str
    text: str
    rounds: int = 0
    executed_tools: list[str] = field(default_factory=list)
    pending: dict | None = None
    reason: str | None = None

    def as_dict(self):
        from dataclasses import asdict
        return asdict(self)
