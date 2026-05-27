from __future__ import annotations

import json
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.export.dossier import export_dossier
from core.export.verdict import export_latest_verdict
from core.proposals.lifecycle import attach_verdict_exports, update_proposal_decision_status
from core.proposals.store import create_proposal, update_proposal


def test_dossier_json_contains_proposal_and_verdict() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        history = root / "proposal_history.jsonl"
        proposal = create_proposal(title="Dossier", body="Decide this", source="manual", status="SUBMITTED", path=history)
        trace = {
            "proposal_id": "trace_dossier",
            "timestamp": "2026-05-27T00:00:00Z",
            "taxonomy": "GENERAL",
            "votes": {"ARBITER": {"vote": "APPROVE"}},
            "confidence": 0.8,
            "final_verdict": "APPROVE",
            "terminal_branch": "majority",
            "review_triggers": [],
        }
        exports = export_latest_verdict(trace, output_dir=root / "verdicts")
        update_proposal(proposal["proposal_id"], path=history, linked_decision_trace_id="trace_dossier")
        update_proposal_decision_status(proposal["proposal_id"], "DECIDED", decision_timestamp=trace["timestamp"], path=history)
        attach_verdict_exports(proposal["proposal_id"], exports, path=history)
        dossier = export_dossier(proposal["proposal_id"], output_dir=root / "dossiers", history_path=history)
        payload = json.loads(Path(dossier["json_path"]).read_text(encoding="utf-8"))
        assert payload["proposal"]["proposal_id"] == proposal["proposal_id"]
        assert payload["decision"]["final_verdict"] == "APPROVE"
        assert payload["decision"]["votes"]["ARBITER"]["vote"] == "APPROVE"


if __name__ == "__main__":
    test_dossier_json_contains_proposal_and_verdict()
    print("test_dossier_export_json PASS")
