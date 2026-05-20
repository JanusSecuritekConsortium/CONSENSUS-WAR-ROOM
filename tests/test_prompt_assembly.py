from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.nodes import DEFAULT_NODES
from core.prompting.assembler import assemble_monolith_prompt


def test_prompt_assembler_includes_doctrine_context_and_vote_schema() -> None:
    node = DEFAULT_NODES["RATIONALIS"]
    prompt = assemble_monolith_prompt(
        node,
        "Approve a persistent memory index.",
        {
            "session_id": "s1",
            "model": "deepseek-coder-33b-instruct.Q4_K_S:latest",
            "memory_context": {
                "summary": "prior-1 | APPROVED | persistent memory was approved",
                "prior_decisions_used": 1,
            },
        },
    )

    assert "DOCTRINAL PROFILE:" in prompt
    assert "canonical_id: RATIONALIS" in prompt
    assert "RELEVANT MEMORY CONTEXT:" in prompt
    assert "prior-1 | APPROVED" in prompt
    assert "VOTE: APPROVE | DENY | ABSTAIN" in prompt
    assert "CONFIDENCE: 0.00 to 1.00" in prompt
    assert "EVIDENCE_QUALITY: 0.00 to 1.00" in prompt
    assert "CRITICAL_RISK: true | false" in prompt


if __name__ == "__main__":
    test_prompt_assembler_includes_doctrine_context_and_vote_schema()
    print("test_prompt_assembly PASS")
