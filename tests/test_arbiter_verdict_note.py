"""ARBITER's spoken verdict note: what it says, when it is sent, and that it is sent once. No voice or Telegram."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voice import arbiter_verdict_note as note


def vote(value, model="llama3.3:70b", reasoning="Looks sound. More detail follows."):
    return {"vote": value, "model": model, "reasoning": reasoning}


def record(**extra):
    base = {
        "session_id": "abc123",
        "query": "Should we move the backups to the new drive?",
        "verdict": "APPROVE",
        "votes": {"RATIONALIS": vote("APPROVE"), "AETERNUM": vote("APPROVE"),
                  "BELLATOR": vote("DENY", reasoning="The new drive has no offsite copy. Other notes.")},
        "next_steps": ["BELLATOR: Before reassessment: keep an offsite copy"],
        "simulation": False,
    }
    base.update(extra)
    return base


class VerdictNoteTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.history = self.root / "history.json"
        self.ledger = self.root / "sent.json"

    def test_script_reads_question_verdict_split_dissent_and_next_step(self):
        text = note.script(record())
        self.assertIn("Tribunal verdict on: Should we move the backups to the new drive.", text)
        self.assertIn("The proposal is approved.", text)
        self.assertIn("The vote was two to one.", text)
        self.assertIn("Bellator voted deny: The new drive has no offsite copy.", text)
        self.assertIn("Before this proceeds: keep an offsite copy.", text)

    def test_spanish_question_stays_in_the_caption_not_the_english_voice(self):
        item = record(query="¿Debo mover las copias al disco nuevo?", verdict="NO_CONSENSUS")
        self.assertTrue(note.script(item).startswith("Tribunal verdict on your question. No consensus was reached."))
        self.assertIn("¿Debo mover las copias al disco nuevo?", note.caption(item))

    def test_unanimous_vote(self):
        item = record(votes={k: vote("APPROVE") for k in ("RATIONALIS", "AETERNUM", "BELLATOR")}, next_steps=[])
        self.assertIn("The vote was unanimous: three approve.", note.script(item))

    def test_mock_and_simulation_runs_are_not_real(self):
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": ""}):
            self.assertTrue(note.is_real(record()))
            self.assertFalse(note.is_real(record(simulation=True)))
            self.assertFalse(note.is_real(record(votes={"RATIONALIS": vote("APPROVE", model="mock")})))
        self.assertFalse(note.is_real(record()))  # never while tests run

    def test_off_by_default_then_sent_once(self):
        self.history.write_text(json.dumps([record()]), encoding="utf-8")
        sent = []

        def render_fn(text, folder):
            path = folder / "verdict.ogg"
            path.write_bytes(b"ogg")
            return path

        def send_fn(path, text):
            sent.append(text)
            return {"message_id": 7}
        kwargs = dict(history_path=self.history, ledger_path=self.ledger, render_fn=render_fn, send_fn=send_fn)
        with patch.dict(os.environ, {note.ENV_FLAG: ""}):
            self.assertEqual(note.deliver("abc123", **kwargs), "off")
        with patch.dict(os.environ, {note.ENV_FLAG: "1", "PYTEST_CURRENT_TEST": ""}):
            self.assertEqual(note.deliver("missing", **kwargs), "not found")
            self.assertEqual(note.deliver("abc123", **kwargs), "sent")
            self.assertEqual(note.deliver("abc123", **kwargs), "already sent")
        self.assertEqual(len(sent), 1)
        self.assertTrue(sent[0].startswith("ARBITER: APPROVE\nShould we move the backups"))
        self.assertEqual(json.loads(self.ledger.read_text())["abc123"]["message_id"], 7)

    def test_caption_fits_telegram(self):
        item = record(query="x" * 2000, next_steps=["step " * 100] * 3)
        self.assertLessEqual(len(note.caption(item)), note.CAPTION_LIMIT)

    def test_queue_never_starts_during_tests(self):
        class Result:
            session_id = "abc123"
            simulation = False
        with patch.dict(os.environ, {note.ENV_FLAG: "1"}), patch.object(note.subprocess, "Popen") as popen:
            self.assertFalse(note.queue(Result()))
        popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
