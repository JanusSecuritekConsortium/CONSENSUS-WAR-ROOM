from __future__ import annotations

import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.proposals.lifecycle import link_decision_trace_to_proposal
from core.proposals.store import create_proposal, get_proposal


def test_linkage_updates_proposal_from_decision_trace() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        history = Path(tmp) / "proposal_history.jsonl"
        proposal = create_proposal(title="Link me", body="Assess", source="manual", status="SUBMITTED", path=history)
        history.write_text(history.read_text(encoding="utf-8") + "{corrupt}\n", encoding="utf-8")
        trace = {
            "proposal_id": "trace_1",
            "timestamp": "2026-05-27T00:00:00Z",
            "final_verdict": "APPROVE",
            "terminal_branch": "majority",
            "votes": {"RATIONALIS": {"vote": "APPROVE"}},
            "confidence": 0.9,
        }
        result = link_decision_trace_to_proposal(trace, proposal_id=proposal["proposal_id"], export_verdict=False, path=history)
        updated = get_proposal(proposal["proposal_id"], path=history)
        assert result["linked"] is True
        assert updated["linked_decision_trace_id"] == "trace_1"
        assert updated["decision_status"] == "DECIDED"


if __name__ == "__main__":
    test_linkage_updates_proposal_from_decision_trace()
    print("test_proposal_decision_linking PASS")
