from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.memory.retrieval import retrieve_relevant_context, search_decisions


def test_similar_prior_decision_can_be_retrieved() -> None:
    tmpdir = tempfile.TemporaryDirectory()
    base = Path(tmpdir.name)
    session_path = base / "session_memory.json"
    history_path = base / "decision_history.json"
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(
        json.dumps(
            {
                "version": 1,
                "sessions": [
                    {
                        "session_id": "s1",
                        "proposal": "Approve encrypted session memory for tribunal decisions.",
                        "verdict": "APPROVED",
                        "synthesis_summary": "Session memory approved with corruption backups.",
                        "tags": ["memory", "security"],
                        "timestamp": "2026-05-09T00:00:00",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    history_path.write_text("[]", encoding="utf-8")

    packet = retrieve_relevant_context(
        "Should we improve encrypted memory backups?",
        tags=["memory"],
        session_path=session_path,
        history_path=history_path,
    )

    assert packet["prior_decisions_used"] == 1
    assert packet["items"][0]["session_id"] == "s1"
    assert "memory" in packet["items"][0]["matched_keywords"]
    tmpdir.cleanup()


def test_cli_search_helper_works_offline() -> None:
    results = search_decisions("proposal unlikely to exist", limit=2)

    assert isinstance(results, list)


if __name__ == "__main__":
    test_similar_prior_decision_can_be_retrieved()
    test_cli_search_helper_works_offline()
    print("test_context_retrieval PASS")
