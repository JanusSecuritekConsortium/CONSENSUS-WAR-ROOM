from __future__ import annotations

import json
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.export.verdict import export_latest_verdict


def test_verdict_export_json_contains_required_fields() -> None:
    trace = {
        "proposal_id": "prop_test_json",
        "timestamp": "2026-05-27T00:00:00Z",
        "taxonomy": "GENERAL",
        "votes": {"RATIONALIS": {"vote": "APPROVE"}},
        "confidence": 0.91,
        "final_verdict": "APPROVE",
        "terminal_branch": "majority",
        "review_triggers": [],
    }
    with tempfile.TemporaryDirectory() as tmp:
        result = export_latest_verdict(trace, output_dir=Path(tmp))
        payload = json.loads(Path(result["json_path"]).read_text(encoding="utf-8"))
        assert payload["proposal_id"] == "prop_test_json"
        assert payload["taxonomy"] == "GENERAL"
        assert payload["votes"]["RATIONALIS"]["vote"] == "APPROVE"


if __name__ == "__main__":
    test_verdict_export_json_contains_required_fields()
    print("test_verdict_export_json PASS")
