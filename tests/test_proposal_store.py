from __future__ import annotations

import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.proposals.store import create_proposal, get_proposal, list_recent_proposals, update_proposal


def test_proposal_store_crud_and_corrupt_line_tolerance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "proposal_history.jsonl"
        path.write_text("{corrupt json}\n", encoding="utf-8")
        created = create_proposal(
            title="Decision",
            body="Choose option A",
            taxonomy_hint="TECHNICAL_DECISION",
            source="manual",
            status="DRAFT",
            path=path,
        )
        assert get_proposal(created["proposal_id"], path=path)["title"] == "Decision"
        updated = update_proposal(created["proposal_id"], status="SUBMITTED", path=path)
        assert updated["status"] == "SUBMITTED"
        recent = list_recent_proposals(path=path)
        assert len(recent) == 1
        assert recent[0]["proposal_id"] == created["proposal_id"]


if __name__ == "__main__":
    test_proposal_store_crud_and_corrupt_line_tolerance()
    print("test_proposal_store PASS")
