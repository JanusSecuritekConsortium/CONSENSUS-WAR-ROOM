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


def _trace(proposal_id: str) -> str:
    return json.dumps({"timestamp": proposal_id, "level": "INFO", "event_type": "decision_trace", "payload": {"proposal_id": proposal_id}})


def test_decision_trace_reader_includes_rotated_parts_in_order(tmp_path: Path) -> None:
    path = tmp_path / "system.jsonl"
    (tmp_path / "system.jsonl.20260501-120000-000000001").write_text(_trace("oldest") + "\n", encoding="utf-8")
    (tmp_path / "system.jsonl.20261001-120000-000000002").write_text(_trace("middle") + "\n", encoding="utf-8")
    (tmp_path / "system.jsonl.notes").write_text(_trace("not-a-rotated-part") + "\n", encoding="utf-8")
    path.write_text(_trace("newest") + "\n", encoding="utf-8")

    assert [item["proposal_id"] for item in list_recent_traces(10, path)] == ["oldest", "middle", "newest"]
    assert read_trace_by_proposal_id("oldest", path) is not None
    assert read_latest_trace(path)["proposal_id"] == "newest"


def test_decision_trace_reader_finds_rotated_parts_without_a_current_file(tmp_path: Path) -> None:
    path = tmp_path / "system.jsonl"
    (tmp_path / "system.jsonl.20260501-120000-000000001").write_text(_trace("only") + "\n", encoding="utf-8")

    assert read_latest_trace(path)["proposal_id"] == "only"


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_decision_trace_reader_tolerates_missing_file(Path(tmp))
        test_decision_trace_reader_skips_corrupt_lines(Path(tmp))
    print("test_decision_trace_reader PASS")
