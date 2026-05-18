from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import AETERNUM, BELLATOR, RATIONALIS, TRIBUNAL_AGENT_IDS
from config.nodes import DEFAULT_NODES
from core.tribunal import Tribunal
from core.voting.rules import ConsensusRules


class RecordingRuntime:
    def __init__(self) -> None:
        self.calls = []

    def send_to_agent(
        self,
        agent_id: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        self.calls.append({"agent_id": agent_id, "prompt": prompt, "context": context or {}})
        votes = {
            RATIONALIS: ("APPROVE", "0.90", "Logic accepts."),
            AETERNUM: ("APPROVE", "0.84", "Finance accepts."),
            BELLATOR: ("CONDITIONAL", "0.76", "Security attaches guardrails."),
        }
        vote, confidence, reasoning = votes[agent_id]
        return (
            f"VOTE: {vote}\n"
            f"CONFIDENCE: {confidence}\n"
            f"REASONING: {reasoning}\n"
            "RISKS: test risk\n"
            "CONDITIONS: test condition\n"
        )


def test_voting_uses_runtime() -> None:
    runtime = RecordingRuntime()
    tribunal = Tribunal(
        DEFAULT_NODES,
        runtime,
        rules=ConsensusRules(minimum_confidence=0.6, quorum=2, majority=2),
        theme_key="military",
    )
    result = tribunal.deliberate("runtime integration vote")

    assert result.verdict.value == "APPROVED"
    assert [call["agent_id"] for call in runtime.calls] == list(TRIBUNAL_AGENT_IDS)
    assert set(result.votes) == set(TRIBUNAL_AGENT_IDS)


if __name__ == "__main__":
    test_voting_uses_runtime()
    print("test_voting_runtime_integration PASS")

