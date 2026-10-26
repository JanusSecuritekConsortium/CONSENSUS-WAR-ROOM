import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from core.llm.backends import ProviderRequestError
from core.llm.generation import GenerationControl, SubmissionCancelled, generate_response
from tests.test_directorate_submit_controls import scene, feedback
from tests.test_directorate_interaction import button
from ui import flet_app as gui


@pytest.fixture
def provider():
    received = threading.Event()
    release = threading.Event()
    requests = []
    mode = {"value": "headers"}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            self.send_error(404)
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append((self.path, body))
            if mode["value"] == "route" and self.path == "/api/generate":
                self.send_error(405)
                return
            if mode["value"] == "error":
                self.send_error(500)
                return
            received.set()
            if mode["value"] == "headers":
                release.wait(3)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            try:
                self.wfile.write(b'data: {"choices":[{"delta":{"content":"public reply"}}]}\n\n')
                self.wfile.flush()
                if mode["value"] == "body":
                    release.wait(3)
                if mode["value"] != "truncated":
                    self.wfile.write(b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n')
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}", received, release, requests, mode
    release.set()
    server.shutdown()
    server.server_close()


def payload():
    return {"model": "fixture-real", "prompt": "assigned role", "options": {"temperature": .47, "num_predict": 731}}


@pytest.mark.parametrize("stage", ["headers", "body"])
def test_cancel_closes_reader_before_worker_returns(provider, stage):
    url, received, release, requests, mode = provider
    mode["value"] = stage
    progress = []
    control = GenerationControl(progress.append)
    outcome = []
    def worker():
        try:
            outcome.append(generate_response(url, payload(), control))
        except Exception as exc:
            outcome.append(exc)
    thread = threading.Thread(target=worker)
    thread.start()
    assert received.wait(2)
    if stage == "body":
        deadline = time.monotonic() + 2
        while "GENERATING" not in progress and time.monotonic() < deadline:
            time.sleep(.01)
        assert "GENERATING" in progress
    assert control.cancel()
    thread.join(2)
    assert not thread.is_alive()
    assert len(outcome) == 1 and isinstance(outcome[0], SubmissionCancelled)
    assert len(requests) == 1


def test_route_translation_preserves_role_and_settings(provider):
    url, _, _, requests, mode = provider
    mode["value"] = "route"
    assert generate_response(url, payload(), GenerationControl()) == "public reply"
    assert [p for p, _ in requests] == ["/api/generate", "/v1/chat/completions"]
    body = requests[-1][1]
    assert body["temperature"] == .47 and body["max_tokens"] == 731
    assert body["messages"][0]["content"] == "assigned role" and body["stream"] is True


@pytest.mark.parametrize("mode_value", ["error", "truncated"])
def test_failure_never_replays_generation_or_accepts_partial_output(provider, mode_value):
    url, _, _, requests, mode = provider
    mode["value"] = mode_value
    with pytest.raises(ProviderRequestError):
        generate_response(url, payload(), GenerationControl())
    assert len(requests) == 1


def test_cancel_before_commit_and_commit_before_cancel_are_atomic():
    control = GenerationControl()
    assert control.cancel()
    with pytest.raises(SubmissionCancelled):
        control.commit()
    assert not control.committed
    control = GenerationControl()
    control.commit()
    assert not control.cancel()
    control.check()


def test_transport_deadline_closes_waiting_response(provider):
    url, _, _, requests, _ = provider
    with pytest.raises(ProviderRequestError, match="timed out"):
        generate_response(url, payload(), GenerationControl(timeout=.3))
    assert len(requests) <= 1


def test_cancellation_between_model_reply_and_parse_never_counts_vote_or_falls_back(monkeypatch):
    from config.names import BELLATOR
    from config.nodes import DEFAULT_NODES
    from config.runtime import RuntimeConfig
    from core.voting.orchestrator import VotingOrchestrator
    from integrations.msty.runtime import MstyRuntime
    from integrations.msty import api
    from tests.test_real_model_fallback_deliberation import valid_response
    control = GenerationControl()
    runtime = MstyRuntime(RuntimeConfig(base_model="base"), generation_control=control)
    monkeypatch.setattr(api, "health_check", lambda *a, **kw: {"status": "ready", "models": ["base", "another"], "base_url": "http://fixture", "backend": "real-fixture"})
    calls = []
    def reply(*args, **kwargs):
        calls.append(args[0])
        control.cancel()
        return valid_response("Late provider response")
    monkeypatch.setattr(api, "send_prompt", reply)
    monkeypatch.setattr(runtime, "_fallback_response", lambda *a: pytest.fail("Cancellation cannot fabricate fallback"))
    monkeypatch.setattr(VotingOrchestrator, "_build_bellator_context_packet", lambda *a: {})
    monkeypatch.setattr("core.voting.orchestrator.build_aeternum_data_enrichment", lambda *a, **kw: {})
    orchestrator = VotingOrchestrator(DEFAULT_NODES, runtime)
    events = []
    with pytest.raises(SubmissionCancelled):
        orchestrator.cast_votes("Fixture", "cancel-late", "eva", on_event=events.append)
    assert calls == ["base"] and not orchestrator.transcript and not orchestrator.complete
    assert not any(e["type"] == "vote_received" for e in events)
    assert runtime.last_execution[BELLATOR]["status"] == "cancelled"


def test_gui_cancel_before_worker_and_retry_preserves_original_proposal(monkeypatch):
    page, state = scene("Original proposal")
    monkeypatch.setattr(gui, "update_proposal", lambda *args, **kwargs: {})
    def submission(*args, **kwargs):
        state.generation_control.check()
        raise ValueError("fixture retry failure")
    monkeypatch.setattr(gui, "submit_proposal_live_for_gui", submission)
    button(page, "SUBMIT TO TRIBUNAL").on_click(None)
    assert not button(page, "CANCEL").disabled and button(page, "RETRY").disabled
    first_control = state.generation_control
    button(page, "CANCEL").on_click(None)
    assert state.submission_lock.locked() and button(page, "RETRY").disabled
    worker, args = page.jobs.pop()
    worker(*args)
    assert not state.submission_lock.locked() and state.current_result is None
    assert state.lifecycle_state == "CANCELLED" and "cancelled" in feedback(state)
    assert not state.directorate.dispatches()
    assert not button(page, "RETRY").disabled
    state.proposal_input_text = "Different draft"
    button(page, "RETRY").on_click(None)
    assert state.current_proposal == "Original proposal"
    assert state.generation_control is not first_control
    assert state.submission_lock.locked() and len(page.jobs) == 1
