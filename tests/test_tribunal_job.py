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

    def start(self, question="Should we move the backups?", memory=None):
        return job.start(question, jobs_dir=self.jobs, launch=self.launched.append, check_memory=lambda: memory,
                         free_local_ai=lambda: [])

    def test_local_ai_is_freed_before_memory_is_measured(self):
        order = []
        job.start("Should we move the backups?", jobs_dir=self.jobs, launch=self.launched.append,
                  free_local_ai=lambda: order.append("free") or [], check_memory=lambda: order.append("check"))
        self.assertEqual(order, ["free", "check"])

    def test_low_memory_refuses_before_anything_starts(self):
        refused = self.start(memory="Low memory: BELLATOR's model needs about 28 GB, but only about 6 GB ...")
        self.assertEqual(refused["status"], "not_started")
        self.assertIn("Low memory", refused["detail"])
        self.assertEqual((self.launched, list(self.jobs.glob("*.json"))), ([], []))

    def test_memory_note_compares_the_largest_voter_with_free_memory(self):
        from unittest import mock
        from integrations.msty import api
        gb = 2**30
        sizes = {"deepseek.gguf": 18 * gb, "mixtral-q5.gguf": 30 * gb, "chat.gguf": 40 * gb}
        config = mock.Mock(agent_model_overrides={"RATIONALIS": "deepseek.gguf", "BELLATOR": "mixtral-q5.gguf"})
        with mock.patch("config.runtime.load_runtime_config", return_value=config), \
                mock.patch.object(api, "resolve_provider_base_url", return_value="http://router"), \
                mock.patch.object(api, "model_file_sizes", return_value=sizes), \
                mock.patch.object(api, "loaded_models", return_value=["deepseek.gguf"]), \
                mock.patch.object(job, "_free_gpu_bytes", return_value=3 * gb), \
                mock.patch("psutil.virtual_memory", return_value=mock.Mock(available=6 * gb)):
            note = job.memory_note()  # 6 + 3 free, plus 18 the tribunal itself would unload = 27 < 30
            self.assertIn("BELLATOR's model needs about 30 GB", note)
            with mock.patch("psutil.virtual_memory", return_value=mock.Mock(available=12 * gb)):
                self.assertIsNone(job.memory_note())  # the owner's 40 GB chat model is not the tribunal's
            # BELLATOR on an online model loads nothing locally, so its 30 GB file no longer counts.
            with mock.patch("core.llm.online.routes_for", side_effect=lambda agent: ["online"] if agent == "BELLATOR" else []):
                self.assertIsNone(job.memory_note())

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

    def test_a_long_run_with_a_heartbeat_stays_running(self):
        import os
        ticket = self.start()["ticket"]
        path = self.jobs / f"{ticket}.json"
        record = json.loads(path.read_text())
        old = datetime.now(timezone.utc) - timedelta(hours=3)
        record.update(status="running", requested_at=old.isoformat(), started_at=old.isoformat())
        path.write_text(json.dumps(record))
        alive = path.with_suffix(".alive")
        alive.touch()  # beating now
        running = job.status(ticket, jobs_dir=self.jobs)
        self.assertEqual(running["status"], "running")
        self.assertEqual(running["elapsed_minutes"], 180)
        self.assertEqual(self.start("Another question?")["status"], "busy")
        stopped = (datetime.now(timezone.utc) - timedelta(minutes=10)).timestamp()
        os.utime(alive, (stopped, stopped))  # the process died ten minutes ago
        self.assertEqual(job.status(ticket, jobs_dir=self.jobs)["status"], "failed")

    def test_run_leaves_no_heartbeat_behind(self):
        ticket = self.start()["ticket"]
        job.run(ticket, jobs_dir=self.jobs, deliberate=result)
        self.assertEqual(list(self.jobs.glob("*.alive")), [])

    def test_other_local_model_work_can_see_a_deliberation(self):
        self.assertFalse(job.deliberation_running(self.jobs))
        ticket = self.start()["ticket"]
        self.assertTrue(job.deliberation_running(self.jobs))
        job.run(ticket, jobs_dir=self.jobs, deliberate=result)
        self.assertFalse(job.deliberation_running(self.jobs))

    def test_the_email_scan_waits_for_a_deliberation(self):
        from unittest import mock
        from integrations.attention import backup
        with mock.patch.object(job, "deliberation_running", return_value=True), \
                mock.patch.object(backup, "log") as log, mock.patch.object(backup.scan, "run") as scan:
            self.assertEqual(backup.main(["scan"]), 0)
        scan.assert_not_called()
        log.assert_called_once_with("scan deferred: tribunal deliberating")

    def test_local_ai_models_are_unloaded_by_name(self):
        from unittest import mock
        from core.llm import backends
        from integrations.msty import api
        posts = []
        listing = mock.Mock(json=lambda: {"models": [{"name": "qwen3.5:9b"}]}, raise_for_status=lambda: None)
        with mock.patch.object(backends.requests, "get", return_value=listing), \
                mock.patch.object(backends.requests, "post", side_effect=lambda url, json, timeout: posts.append((url, json)) or mock.Mock(ok=True)):
            self.assertEqual(api.unload_ollama_models("http://local-ai/"), ["qwen3.5:9b"])
        self.assertEqual(posts, [("http://local-ai/api/generate", {"model": "qwen3.5:9b", "keep_alive": 0})])

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
