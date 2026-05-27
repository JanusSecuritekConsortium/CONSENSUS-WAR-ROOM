from __future__ import annotations

import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.export.dossier import export_dossier
from core.proposals.store import create_proposal, update_proposal


def test_dossier_markdown_is_operator_readable() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        history = root / "proposal_history.jsonl"
        proposal = create_proposal(title="Briefing", body="Submitted content", source="manual", status="SUBMITTED", path=history)
        update_proposal(
            proposal["proposal_id"],
            path=history,
            decision_status="NO_CONSENSUS",
            linked_decision_trace_id="trace_no_consensus",
            decision_timestamp="2026-05-27T00:00:00Z",
        )
        dossier = export_dossier(proposal["proposal_id"], output_dir=root / "dossiers", history_path=history)
        markdown = Path(dossier["markdown_path"]).read_text(encoding="utf-8")
        assert "# Tribunal Dossier: Briefing" in markdown
        assert "Submitted Content" in markdown
        assert "NO_CONSENSUS" in markdown


if __name__ == "__main__":
    test_dossier_markdown_is_operator_readable()
    print("test_dossier_export_markdown PASS")
