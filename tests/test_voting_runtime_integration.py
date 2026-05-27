from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import AETERNUM, BELLATOR, RATIONALIS, TRIBUNAL_AGENT_IDS
from config.nodes import DEFAULT_NODES
from core.intelligence.bellator_context_builder import ANTI_FABRICATION_INSTRUCTION
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
            RATIONALIS: ("APPROVE", "0.90", "0.82", "false", "Logic accepts."),
            AETERNUM: ("APPROVE", "0.84", "0.78", "false", "Finance accepts."),
            BELLATOR: ("ABSTAIN", "0.76", "0.68", "false", "Security attaches guardrails."),
        }
        vote, confidence, evidence_quality, critical_risk, reasoning = votes[agent_id]
        return (
            f"VOTE: {vote}\n"
            f"CONFIDENCE: {confidence}\n"
            f"EVIDENCE_QUALITY: {evidence_quality}\n"
            f"CRITICAL_RISK: {critical_risk}\n"
            f"RATIONALE: {reasoning}\n"
            "RISKS: test risk\n"
            "CONDITIONS: test condition\n"
        )


def test_voting_uses_runtime() -> None:
    os.environ["BELLATOR_FEEDS_ENABLED"] = "0"
    runtime = RecordingRuntime()
    tribunal = Tribunal(
        DEFAULT_NODES,
        runtime,
        rules=ConsensusRules(minimum_confidence=0.6, quorum=2, majority=2),
        theme_key="military",
    )
    result = tribunal.deliberate("runtime integration vote")

    assert result.verdict.value == "APPROVE"
    assert [call["agent_id"] for call in runtime.calls] == list(TRIBUNAL_AGENT_IDS)
    assert set(result.votes) == set(TRIBUNAL_AGENT_IDS)
    bellator_call = next(call for call in runtime.calls if call["agent_id"] == BELLATOR)
    assert "bellator_context_packet" in bellator_call["context"]
    assert "BELLATOR CONTEXT PACKET" in bellator_call["prompt"]
    assert ANTI_FABRICATION_INSTRUCTION in bellator_call["prompt"]
    for call in runtime.calls:
        if call["agent_id"] != BELLATOR:
            assert "bellator_context_packet" not in call["context"]
            assert "BELLATOR CONTEXT PACKET" not in call["prompt"]
            assert ANTI_FABRICATION_INSTRUCTION not in call["prompt"]


def test_tribunal_can_route_verdict_to_voice_announcer() -> None:
    os.environ["BELLATOR_FEEDS_ENABLED"] = "0"
    runtime = RecordingRuntime()
    announced = []
    tribunal = Tribunal(
        DEFAULT_NODES,
        runtime,
        rules=ConsensusRules(minimum_confidence=0.6, quorum=2, majority=2),
        theme_key="military",
        voice_announcer=announced.append,
    )
    result = tribunal.deliberate("announce runtime integration vote")

    assert announced == [result]


def test_sequential_voting_keeps_bellator_packet_isolated() -> None:
    os.environ["BELLATOR_FEEDS_ENABLED"] = "0"
    runtime = RecordingRuntime()
    tribunal = Tribunal(
        DEFAULT_NODES,
        runtime,
        rules=ConsensusRules(minimum_confidence=0.6, quorum=2, majority=2),
        theme_key="military",
    )
    tribunal.deliberate("sequential packet isolation vote", sequential=True)

    for call in runtime.calls:
        if call["agent_id"] == BELLATOR:
            assert "bellator_context_packet" in call["context"]
        else:
            assert "bellator_context_packet" not in call["context"]


if __name__ == "__main__":
    test_voting_uses_runtime()
    test_tribunal_can_route_verdict_to_voice_announcer()
    test_sequential_voting_keeps_bellator_packet_isolated()
    print("test_voting_runtime_integration PASS")
