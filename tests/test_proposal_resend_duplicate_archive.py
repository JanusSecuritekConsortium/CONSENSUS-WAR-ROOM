from __future__ import annotations

import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.proposals.store import archive_proposal, create_proposal, duplicate_proposal, list_recent_proposals, resend_proposal


def test_resend_duplicate_archive_lifecycle() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "proposal_history.jsonl"
        original = create_proposal(
            title="Original",
            body="Assess operational exposure",
            taxonomy_hint="OPERATIONAL_RISK",
            source="manual",
            status="SUBMITTED",
            path=path,
        )
        resent = resend_proposal(original["proposal_id"], path=path)
        duplicate = duplicate_proposal(original["proposal_id"], path=path)
        archive_proposal(original["proposal_id"], path=path)

        assert resent["proposal_id"] != original["proposal_id"]
        assert resent["status"] == "RESUBMITTED"
        assert resent["parent_proposal_id"] == original["proposal_id"]
        assert duplicate["status"] == "DRAFT"
        assert duplicate["body"] == original["body"]
        visible_ids = {item["proposal_id"] for item in list_recent_proposals(path=path)}
        assert original["proposal_id"] not in visible_ids
        assert resent["proposal_id"] in visible_ids


if __name__ == "__main__":
    test_resend_duplicate_archive_lifecycle()
    print("test_proposal_resend_duplicate_archive PASS")
