from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.proposals.lifecycle import decision_status_from_trace


def test_no_consensus_and_escalation_mapping() -> None:
    assert decision_status_from_trace({"final_verdict": "NO_CONSENSUS", "terminal_branch": "classification_failure"}) == "NO_CONSENSUS"
    assert decision_status_from_trace({"final_verdict": "ESCALATE", "terminal_branch": "escalation"}) == "ESCALATED"
    assert decision_status_from_trace({"final_verdict": "APPROVE", "terminal_branch": "majority"}) == "DECIDED"
    assert decision_status_from_trace({"error": "runtime"}) == "ERROR"


if __name__ == "__main__":
    test_no_consensus_and_escalation_mapping()
    print("test_proposal_status_transitions PASS")
