"""Decision outcomes: recorded per real verdict, shown beside past decisions, and turned into a track record."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.memory import outcomes
from core.memory.retrieval import retrieve_relevant_context


def vote(value):
    return {"vote": value, "model": "llama3.3:70b", "response_time": 4.0}


def decision(session_id, query, verdict="APPROVE", timestamp="2026-10-01T10:00:00", votes=None, seconds=4.0):
    votes = votes or {"RATIONALIS": vote("APPROVE"), "AETERNUM": vote("APPROVE"), "BELLATOR": vote("DENY")}
    for item in votes.values():
        item["response_time"] = seconds
    return {"session_id": session_id, "query": query, "verdict": verdict, "timestamp": timestamp, "votes": votes}


class DecisionOutcomesTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        self.history = root / "history.json"
        self.store = root / "outcomes.json"
        self.sessions = root / "sessions.json"
        self.history.write_text(json.dumps([
            decision("backup", "Move the backups to the new drive"),
            decision("gpu", "Buy a second GPU for the tribunal", verdict="DENY", timestamp="2026-10-30T10:00:00"),
            decision("stuck", "Rename the vault", verdict="NO_CONSENSUS"),
            decision("test", "Approve a lifecycle test", seconds=0.0),
        ]), encoding="utf-8")
        self.paths = dict(path=self.store, history_path=self.history)

    def test_records_only_real_decisions_with_known_results(self):
        outcome = outcomes.record_outcome("backup", followed=True, result="good", note="  copied fine ", now="t", **self.paths)
        self.assertEqual(outcome, {"followed": True, "result": "good", "note": "copied fine", "recorded_at": "t"})
        with self.assertRaises(ValueError):
            outcomes.record_outcome("test", followed=True, result="good", **self.paths)
        with self.assertRaises(ValueError):
            outcomes.record_outcome("backup", followed=True, result="great", **self.paths)

    def test_pending_lists_old_decided_verdicts_without_outcome(self):
        now = datetime(2026, 11, 3, tzinfo=timezone.utc)
        self.assertEqual([item["session_id"] for item in outcomes.pending_outcomes(now=now, **self.paths)], ["backup"])
        outcomes.record_outcome("backup", followed=False, result="mixed", **self.paths)
        self.assertEqual(outcomes.pending_outcomes(now=now, **self.paths), [])

    def test_track_record_counts_followed_clear_results(self):
        outcomes.record_outcome("backup", followed=True, result="good", **self.paths)
        outcomes.record_outcome("gpu", followed=True, result="bad", **self.paths)
        record = outcomes.track_record(**self.paths)
        self.assertEqual(record["RATIONALIS"], {"right": 1, "wrong": 1})
        self.assertEqual(record["BELLATOR"], {"right": 1, "wrong": 1})
        self.assertIn("RATIONALIS 1 right, 1 wrong", outcomes.track_record_line(record))

    def test_past_decisions_carry_their_outcome(self):
        outcomes.record_outcome("backup", followed=True, result="good", note="copied fine", **self.paths)
        packet = retrieve_relevant_context("Should we move the backups again?", session_path=self.sessions,
                                           history_path=self.history, outcomes_path=self.store)
        self.assertIn("backup | APPROVE | Move the backups to the new drive | followed, turned out good (copied fine)",
                      packet["summary"])
        self.assertIn("Track record on decisions with recorded outcomes", packet["summary"])


if __name__ == "__main__":
    unittest.main()
