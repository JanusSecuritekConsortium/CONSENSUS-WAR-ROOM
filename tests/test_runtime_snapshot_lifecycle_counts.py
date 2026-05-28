from __future__ import annotations

import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.proposals.lifecycle import proposal_lifecycle_summary
from core.proposals.store import create_proposal, update_proposal


def test_lifecycle_summary_counts_terminal_statuses() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        history = Path(tmp) / "proposal_history.jsonl"
        decided = create_proposal(title="A", body="A", source="manual", status="SUBMITTED", path=history)
        no_consensus = create_proposal(title="B", body="B", source="manual", status="SUBMITTED", path=history)
        escalated = create_proposal(title="C", body="C", source="manual", status="SUBMITTED", path=history)
        update_proposal(decided["proposal_id"], path=history, decision_status="DECIDED")
        update_proposal(no_consensus["proposal_id"], path=history, decision_status="NO_CONSENSUS")
        update_proposal(escalated["proposal_id"], path=history, decision_status="ESCALATED")
        summary = proposal_lifecycle_summary(history)
        assert summary["decided_total"] == 1
        assert summary["no_consensus_total"] == 1
        assert summary["escalated_total"] == 1


if __name__ == "__main__":
    test_lifecycle_summary_counts_terminal_statuses()
    print("test_runtime_snapshot_lifecycle_counts PASS")
