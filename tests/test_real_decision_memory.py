"""Past-decision context and history trimming only treat decisions real models reached as precedent."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.history import is_real_decision, keep_latest
from core.memory.retrieval import retrieve_relevant_context


def decision(session_id, query, seconds=3.5, model="llama3.3:70b", simulation=False):
    return {"session_id": session_id, "query": query, "verdict": "APPROVE", "simulation": simulation,
            "votes": {"RATIONALIS": {"vote": "APPROVE", "model": model, "response_time": seconds}}}


class RealDecisionMemoryTest(unittest.TestCase):
    def test_only_real_model_answers_count(self):
        self.assertTrue(is_real_decision(decision("a", "q")))
        self.assertFalse(is_real_decision(decision("b", "q", seconds=0.0)))  # stubbed test vote
        self.assertFalse(is_real_decision(decision("c", "q", model="mock")))
        self.assertFalse(is_real_decision(decision("d", "q", simulation=True)))
        session = {"session_id": "e", "monolith_votes": {"BELLATOR": {"model": "mixtral:8x7b", "response_time": 4.0}}}
        self.assertTrue(is_real_decision(session))
        self.assertTrue(is_real_decision({"session_id": "f", "proposal": "imported decision"}))
        failed = decision("g", "q", seconds=700.0)
        failed["votes"]["RATIONALIS"]["validation_errors"] = ["runtime_failure:ProviderRequestError"]
        self.assertFalse(is_real_decision(failed))  # every model call timed out; nothing was decided

    def test_context_skips_test_runs(self):
        with tempfile.TemporaryDirectory() as folder:
            history = Path(folder) / "history.json"
            sessions = Path(folder) / "sessions.json"
            history.write_text(json.dumps([decision("real", "move backups to the new drive"),
                                           decision("fake", "move backups to the new drive test", seconds=0.0)]))
            packet = retrieve_relevant_context("Should we move backups to the new drive?",
                                               session_path=sessions, history_path=history)
        self.assertEqual([item["session_id"] for item in packet["items"]], ["real"])

    def test_trimming_drops_test_runs_before_real_decisions(self):
        items = [decision("real-old", "q"), *[decision(f"t{n}", "q", seconds=0.0) for n in range(3)], decision("real-new", "q")]
        kept = keep_latest(items, 3)
        self.assertEqual([item["session_id"] for item in kept], ["real-old", "t2", "real-new"])
        self.assertIs(keep_latest(items, 10), items)


if __name__ == "__main__":
    unittest.main()
