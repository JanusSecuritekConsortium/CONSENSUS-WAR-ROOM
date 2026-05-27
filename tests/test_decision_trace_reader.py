from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.decision_trace import list_recent_traces, read_latest_trace, read_trace_by_proposal_id


def test_decision_trace_reader_tolerates_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "missing.jsonl"

    assert read_latest_trace(path) is None
    assert read_trace_by_proposal_id("none", path) is None
    assert list_recent_traces(path=path) == []


def test_decision_trace_reader_skips_corrupt_lines(tmp_path: Path) -> None:
    path = tmp_path / "system.jsonl"
    records = [
        "not json",
        json.dumps({"event_type": "other", "payload": {"proposal_id": "ignored"}}),
        json.dumps({"timestamp": "t1", "level": "INFO", "event_type": "decision_trace", "payload": {"proposal_id": "p1", "final_verdict": "APPROVE"}}),
        "{broken",
        json.dumps({"timestamp": "t2", "level": "INFO", "event_type": "decision_trace", "payload": {"proposal_id": "p2", "final_verdict": "DENY"}}),
    ]
    path.write_text("\n".join(records), encoding="utf-8")

    assert read_latest_trace(path)["proposal_id"] == "p2"
    assert read_trace_by_proposal_id("p1", path)["final_verdict"] == "APPROVE"
    assert [item["proposal_id"] for item in list_recent_traces(2, path)] == ["p1", "p2"]


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_decision_trace_reader_tolerates_missing_file(Path(tmp))
        test_decision_trace_reader_skips_corrupt_lines(Path(tmp))
    print("test_decision_trace_reader PASS")
