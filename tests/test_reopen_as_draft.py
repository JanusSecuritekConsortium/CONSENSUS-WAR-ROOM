from __future__ import annotations

import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.proposals.store import create_proposal, duplicate_proposal, get_proposal, update_proposal


def test_reopen_as_draft_preserves_original() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        history = Path(tmp) / "proposal_history.jsonl"
        original = create_proposal(title="Original", body="Body", source="manual", status="SUBMITTED", path=history)
        update_proposal(original["proposal_id"], decision_status="DECIDED", path=history)
        reopened = duplicate_proposal(original["proposal_id"], path=history)
        assert reopened["status"] == "DRAFT"
        assert reopened["parent_proposal_id"] == original["proposal_id"]
        assert get_proposal(original["proposal_id"], path=history)["decision_status"] == "DECIDED"


if __name__ == "__main__":
    test_reopen_as_draft_preserves_original()
    print("test_reopen_as_draft PASS")
