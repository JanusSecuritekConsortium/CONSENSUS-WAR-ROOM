"""9.22.0, from the nightly Codex review of 2026-11-24: quotes for outside references, cut-off answers,
the majority setting, backups in the background memory check, and the context-window error in window votes."""
from __future__ import annotations

import json

import httpx
import pytest

from config.names import AETERNUM, BELLATOR, RATIONALIS
from config.runtime import RuntimeConfig
from core.llm import generation
from core.llm.backends import OllamaBackend, ProviderRequestError
from core.models import FinalVerdict, Vote, VoteValue
from core.voting.engine import ConsensusEngine
from core.voting.evidence import audit_evidence
from core.voting.rules import ConsensusRules, majority_result
from integrations.msty import api
from tests.test_traceable_arguments_and_review import parsed, raw_vote

REFERENCE = {"source": "https://example.org/report", "text": "Turnout fell by 4 percent in 2025.", "kind": "reference"}


# ---- 6: evidence from an outside reference needs its quote -------------------------------------------

def test_an_outside_reference_cited_without_a_quote_is_sent_back():
    argument = {"claim": "Turnout rose", "evidence": [{"source": REFERENCE["source"], "detail": "it rose"}]}
    assert audit_evidence(argument, {"evidence_passages": [REFERENCE]})[0]["anchor"] == "missing_quote"
    raw = raw_vote().replace('"source": "proposal", "detail": "Supplied proposal assertions require verification."',
                             f'"source": "{REFERENCE["source"]}", "detail": "Turnout rose."')
    vote = parsed(raw, {"evidence_passages": [REFERENCE]})
    assert vote.vote == VoteValue.ABSTAIN
    assert any("needs a short exact quote" in error for error in vote.validation_errors)


def test_the_proposal_itself_and_quoted_references_need_nothing_more():
    proposal = {"source": "proposal", "text": "Open the library on Sundays.", "kind": "assertion"}
    argument = {"claim": "c", "evidence": [{"source": "proposal", "detail": "d"},
                                           {"source": REFERENCE["source"], "quote": "Turnout fell by 4 percent"}]}
    anchors = [audit["anchor"] for audit in audit_evidence(argument, {"evidence_passages": [proposal, REFERENCE]})]
    assert anchors == ["not_quoted", "matched"]


# ---- 7: an answer cut off at the output limit is refused -------------------------------------------

class _Reply:
    def __init__(self, status, body):
        self.status_code, self._body, self.text = status, body, json.dumps(body)

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


@pytest.mark.parametrize("routes", [
    {"/api/generate": _Reply(200, {"response": "VOTE: APPROVE", "done": True, "done_reason": "length"})},
    {"/api/generate": _Reply(404, {}), "/v1/chat/completions": _Reply(200, {"choices": [
        {"message": {"content": "VOTE: APPROVE"}, "finish_reason": "length"}]})},
])
def test_a_cut_off_answer_is_refused(monkeypatch, routes):
    from core.llm import backends
    monkeypatch.setattr(backends.requests, "post",
                        lambda url, **kw: next(reply for path, reply in routes.items() if url.endswith(path)))
    with pytest.raises(ProviderRequestError, match="did not complete"):
        api.backend_requests_post(OllamaBackend(base_url="http://fixture", timeout=5),
                                  {"model": "m", "prompt": "p", "options": {}})


def test_a_finished_answer_still_passes(monkeypatch):
    from core.llm import backends
    monkeypatch.setattr(backends.requests, "post", lambda url, **kw: _Reply(200, {"response": "VOTE: APPROVE",
                                                                                   "done_reason": "stop"}))
    reply = api.backend_requests_post(OllamaBackend(base_url="http://fixture", timeout=5), {"model": "m", "prompt": "p"})
    assert reply["response"] == "VOTE: APPROVE"


def _window_server(monkeypatch, handler):
    real = httpx.AsyncClient
    monkeypatch.setattr(generation.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(handler), **kw))


def _generate():
    return generation.generate_response("http://fixture", {"model": "m", "prompt": "p", "options": {}},
                                        generation.GenerationControl(timeout=10))


def test_a_window_vote_refuses_a_cut_off_json_answer(monkeypatch):
    def handler(request):
        if request.url.path == "/api/generate":
            return httpx.Response(200, json={"response": "VOTE: APPROVE", "done": True, "done_reason": "length"})
        return httpx.Response(404)
    _window_server(monkeypatch, handler)
    with pytest.raises(ProviderRequestError, match="did not complete"):
        _generate()


# ---- minor fix: a window vote keeps the "context window" error, so no backup is loaded in vain ------

def test_a_window_vote_reports_a_prompt_too_long_for_the_context_window(monkeypatch):
    def handler(request):
        if request.url.path == "/api/generate":
            return httpx.Response(400, json={"error": {"type": "exceed_context_size_error"}})
        return httpx.Response(404)
    _window_server(monkeypatch, handler)
    with pytest.raises(ProviderRequestError, match="context window"):
        _generate()


def test_other_window_errors_keep_the_general_message(monkeypatch):
    _window_server(monkeypatch, lambda request: httpx.Response(500 if request.url.path == "/api/generate" else 404))
    with pytest.raises(ProviderRequestError, match="inspect local diagnostics"):
        _generate()


# ---- 8: the majority setting is honoured ---------------------------------------------------------------

def _vote(key, value, confidence=0.85):
    return Vote(node_key=key, role=key, vote=value, confidence=confidence, reasoning="r", evidence_quality=0.8)


def test_the_configured_majority_is_required():
    votes = [_vote(RATIONALIS, VoteValue.APPROVE), _vote(AETERNUM, VoteValue.APPROVE), _vote(BELLATOR, VoteValue.DENY)]
    assert majority_result(votes) == VoteValue.APPROVE
    assert majority_result(votes, 2) == VoteValue.APPROVE  # the default: the same as before
    assert majority_result(votes, 3) is None


def test_unanimity_is_not_overridden_by_the_priority_tie_break():
    votes = {RATIONALIS: _vote(RATIONALIS, VoteValue.APPROVE), AETERNUM: _vote(AETERNUM, VoteValue.APPROVE),
             BELLATOR: _vote(BELLATOR, VoteValue.DENY)}
    strict = ConsensusRules(majority=3)
    result = ConsensusEngine(strict, "military").calculate_result("Should the library open on Sundays?", votes, "s")
    assert result.verdict == FinalVerdict.NO_CONSENSUS and "configured_majority_not_met" in result.review_triggers
    assert strict.consensus_reached(votes) is False  # so the vote reruns instead of stopping
    assert ConsensusEngine(ConsensusRules(), "military").calculate_result("Should the library open on Sundays?", votes, "s").verdict != FinalVerdict.NO_CONSENSUS


# ---- 9: the background memory check counts a voter's smaller same-maker backup --------------------------

def test_a_background_vote_starts_when_the_smaller_same_maker_backup_fits(monkeypatch):
    from unittest import mock
    from integrations.mcp import tribunal_job as job
    gb = 2**30
    small = "unsloth/Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf"
    ministral = "mistralai/Ministral-3-8B-Instruct-2512-Q4_K_M.gguf"
    gemma = "gemma-3-12b-it-Q3_K_L.gguf"
    sizes = {small: 15 * gb, ministral: 5 * gb, gemma: 7 * gb}
    config = RuntimeConfig(agent_model_overrides={BELLATOR: small}, agent_model_fallbacks={BELLATOR: [ministral]},
                           backups_same_maker_only=True)
    with mock.patch("config.runtime.load_runtime_config", return_value=config), \
            mock.patch.object(api, "resolve_provider_base_url", return_value="http://router"), \
            mock.patch.object(api, "model_file_sizes", return_value=sizes), \
            mock.patch.object(api, "loaded_models", return_value=[]), \
            mock.patch.object(job, "_free_gpu_bytes", return_value=0), \
            mock.patch("core.llm.online.routes_for", return_value=[]), \
            mock.patch("psutil.virtual_memory", return_value=mock.Mock(available=10 * gb)):
        # 15 GB does not fit in 10 GB, but the 5 GB Ministral backup does; Gemma (another maker) never counts.
        assert job.memory_note() is None
        with mock.patch("psutil.virtual_memory", return_value=mock.Mock(available=6 * gb)):
            assert "BELLATOR's model needs about 5 GB" in job.memory_note()
