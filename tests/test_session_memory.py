from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.memory.session import load_session_memory, upsert_session_record


def test_session_memory_persists_and_deduplicates() -> None:
    tmpdir = tempfile.TemporaryDirectory()
    path = Path(tmpdir.name) / "session_memory.json"
    record = {
        "session_id": "abc123",
        "active_theme": "eva",
        "proposal": "Approve secure memory system.",
        "monolith_votes": {},
        "arbiter_verdict": "APPROVED",
        "verdict": "APPROVED",
        "synthesis_summary": "Approved with audit logging.",
        "provider_backend": "msty-local",
        "model_mapping": {"RATIONALIS": "test"},
        "timestamp": "2026-05-09T00:00:00",
        "tags": ["memory"],
    }

    upsert_session_record(record, path)
    upsert_session_record({**record, "synthesis_summary": "Updated summary."}, path)
    memory = load_session_memory(path)

    assert len(memory["sessions"]) == 1
    assert memory["sessions"][0]["synthesis_summary"] == "Updated summary."
    tmpdir.cleanup()


def test_corrupt_session_memory_creates_backup_and_recovers() -> None:
    tmpdir = tempfile.TemporaryDirectory()
    path = Path(tmpdir.name) / "session_memory.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{broken", encoding="utf-8")

    memory = load_session_memory(path)

    assert memory["sessions"] == []
    assert list(path.parent.glob("session_memory.corrupt.*.json.bak"))
    tmpdir.cleanup()


if __name__ == "__main__":
    test_session_memory_persists_and_deduplicates()
    test_corrupt_session_memory_creates_backup_and_recovers()
    print("test_session_memory PASS")
