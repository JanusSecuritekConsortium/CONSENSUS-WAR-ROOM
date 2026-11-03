"""Tribunal over MCP: a ticket at once, one deliberation at a time, and a verdict summary without raw output."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.models import FinalVerdict, TribunalResult, Vote, VoteValue
from integrations.mcp import consensus_mcp_server as server
from integrations.mcp import tribunal_job as job


def result(query):
    vote = Vote(node_key="BELLATOR", role="security", vote=VoteValue.DENY, confidence=0.8,
                reasoning="No offsite copy.", raw_response="RAW MODEL OUTPUT", model="mixtral", response_time=4.0)
    return TribunalResult(query=query, verdict=FinalVerdict.DENY, confidence=0.8, reason="Security risk.",
                          votes={"BELLATOR": vote}, vote_distribution={"DENY": 1}, quorum_met=True,
                          review_triggers=[], session_id="s1", theme="military")


class TribunalJobTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.jobs = Path(folder.name)
        self.launched = []

    def start(self, question="Should we move the backups?"):
        return job.start(question, jobs_dir=self.jobs, launch=self.launched.append)

    def test_start_returns_a_ticket_and_launches_once(self):
        started = self.start("  Should   we move the backups? ")
        self.assertEqual(started["status"], "queued")
        self.assertEqual(self.launched, [started["ticket"]])
        self.assertEqual(job.status(started["ticket"], jobs_dir=self.jobs)["query"], "Should we move the backups?")

    def test_only_one_deliberation_at_a_time(self):
        first = self.start()
        busy = self.start("Another question?")
        self.assertEqual(busy, {**busy, "status": "busy", "ticket": first["ticket"]})
        self.assertEqual(len(self.launched), 1)

    def test_run_stores_a_summary_without_raw_output(self):
        ticket = self.start()["ticket"]
        record = job.run(ticket, jobs_dir=self.jobs, deliberate=result)
        self.assertEqual(record["status"], "finished")
        self.assertEqual(record["result"]["verdict"], "DENY")
        self.assertEqual(record["result"]["votes"]["BELLATOR"]["reasoning"], "No offsite copy.")
        self.assertNotIn("RAW MODEL OUTPUT", json.dumps(record))
        self.assertEqual(job.run(ticket, jobs_dir=self.jobs, deliberate=result)["status"], "finished")  # not rerun
        self.assertEqual(self.start("Next question?")["status"], "queued")

    def test_failures_and_stale_runs_are_reported(self):
        ticket = self.start()["ticket"]

        def broken(query):
            raise RuntimeError("model server offline")
        self.assertEqual(job.run(ticket, jobs_dir=self.jobs, deliberate=broken)["error"], "model server offline")
        old = self.start("Old question?")["ticket"]
        path = self.jobs / f"{old}.json"
        record = json.loads(path.read_text())
        record["requested_at"] = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        path.write_text(json.dumps(record))
        self.assertEqual(job.status(old, jobs_dir=self.jobs)["status"], "failed")
        self.assertEqual(self.start("New question?")["status"], "queued")

    def test_bad_input_is_refused(self):
        for question in ("", "x" * (job.MAX_QUERY_CHARS + 1), "Region: [REGION] Question: [QUESTION]"):
            with self.assertRaises(ValueError):
                self.start(question)
        for ticket in ("../secrets", "ffffffffffff"):
            with self.assertRaises(ValueError):
                job.status(ticket, jobs_dir=self.jobs)

    def test_mcp_tools_are_listed_and_validate_arguments(self):
        names = [tool["name"] for tool in server.TOOLS]
        self.assertIn("tribunal_deliberate", names)
        self.assertIn("tribunal_verdict", names)
        with self.assertRaises(ValueError):
            server.call_tool("tribunal_deliberate", {"question": "q", "model": "x"})
        with self.assertRaises(ValueError):
            server.call_tool("tribunal_verdict", {})


if __name__ == "__main__":
    unittest.main()
