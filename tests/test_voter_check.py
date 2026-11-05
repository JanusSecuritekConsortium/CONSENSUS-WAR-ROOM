"""Voter readiness check: one voter at a time, the server's load error shown, nothing started. No model server."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.mcp import voter_check as vc

Q3 = "TheBloke/Mixtral-8x7B-Instruct-v0.1-GGUF/mixtral-8x7b-instruct-v0.1.Q3_K_M.gguf"
YI = "TheBloke/Yi-34B-Chat-GGUF/yi-34b-chat.Q4_K_S.gguf"
HERMES = "NousResearch/Hermes-3-Llama-3.1-8B-GGUF/Hermes-3-Llama-3.1-8B.Q4_K_M.gguf"


def reply(status, body):
    return mock.Mock(ok=status == 200, status_code=status, content=b"x", json=lambda: body)


class VoterCheckTest(unittest.TestCase):
    def test_a_model_that_answers_is_ready_with_its_speed(self):
        ticks = iter([0.0, 42.0])
        row = vc.check_model("http://router/", YI, clock=lambda: next(ticks),
                             post=lambda url, **kw: reply(200, {"timings": {"predicted_per_second": 18.26}}))
        self.assertEqual(row, {"model": YI, "ok": True, "seconds": 42.0, "tokens_per_second": 18.3, "error": ""})

    def test_a_file_the_server_cannot_read_says_so(self):
        failed = reply(500, {"error": {"message": f"model name={Q3} failed to load"}})
        row = vc.check_model("http://router", Q3, post=lambda url, **kw: failed)
        self.assertFalse(row["ok"])
        self.assertIn("failed to load", row["error"])
        self.assertIn("replace the file with a current one", row["error"])

    def test_an_offline_server_is_reported_not_raised(self):
        def offline(url, **kw):
            raise ConnectionError("refused")
        self.assertIn("ConnectionError", vc.check_model("http://router", YI, post=offline)["error"])

    def test_each_voter_runs_alone_and_a_missing_model_is_named(self):
        config = mock.Mock(agent_model_overrides={"RATIONALIS": "deepseek-missing.gguf", "AETERNUM": YI, "BELLATOR": Q3},
                           base_model=HERMES, generation_timeout_seconds=900)
        events = []
        with mock.patch("integrations.msty.api.resolve_provider_base_url", return_value="http://router"):
            rows = vc.check(config=config, available=lambda url: [YI, Q3, HERMES],
                            unload_all=lambda url: events.append("unload"),
                            check_one=lambda url, model: events.append(model) or {
                                "model": model, "ok": model != Q3, "seconds": 1.0, "tokens_per_second": None,
                                "error": "" if model != Q3 else "failed to load"})
        self.assertEqual([row["agent"] for row in rows], ["RATIONALIS", "AETERNUM", "BELLATOR", "BASE"])
        self.assertIn("does not list", rows[0]["error"])
        self.assertEqual(events, ["unload", YI, "unload", Q3, "unload", HERMES, "unload"])
        text = vc.render(rows)
        self.assertIn("BELLATOR   NOT READY mixtral-8x7b-instruct-v0.1.Q3_K_M.gguf: failed to load", text)
        self.assertIn("AETERNUM   ready     yi-34b-chat.Q4_K_S.gguf: first answer in 1.0 s", text)

    def test_refuses_while_a_deliberation_runs(self):
        from integrations.mcp import tribunal_job
        with mock.patch.object(tribunal_job, "deliberation_running", return_value=True), \
                mock.patch.object(vc, "check") as checked:
            self.assertEqual(vc.main([]), 2)
        checked.assert_not_called()


if __name__ == "__main__":
    unittest.main()
