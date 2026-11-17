"""A voter's prompt is trimmed to fit the local model's window, and a too-long refusal never tries backup models."""
from unittest.mock import MagicMock

import pytest

from core.prompting import fit


def render(context):
    return str(context)


def test_short_prompt_is_left_alone():
    context = {"memory_context": {"external_reference_context": {"matches": ["a", "b"]}}}
    prompt, trimmed = fit.fit_prompt(render, context, 900)
    assert trimmed == [] and context["memory_context"]["external_reference_context"]["matches"] == ["a", "b"]


def test_extras_go_first_and_the_proposal_and_round_stay(monkeypatch):
    monkeypatch.setattr(fit, "char_budget", lambda *a: 2_000)
    context = {
        "proposal": "Keep me",
        "memory_context": {"external_reference_context": {"matches": ["r" * 400] * 3},
                           "second_brain": {"content": "b" * 300}},
        "bellator_context_packet": {"rss_intelligence": {"items": ["n" * 400] * 3, "citations": []}},
        "deliberation": {"round": 2, "previous_rounds": [{"round": 1}]},
    }
    prompt, trimmed = fit.fit_prompt(render, context, 900)
    assert len(prompt) <= 2_000
    assert trimmed[:3] == ["memory_context.external_reference_context.matches"] * 3  # archive references first
    assert "Keep me" in prompt and context["deliberation"]["round"] == 2
    assert context["bellator_context_packet"]["rss_intelligence"]["items"]  # some news still kept


def test_personal_brief_is_shortened_last_and_never_below_the_floor(monkeypatch):
    monkeypatch.setattr(fit, "char_budget", lambda *a: 1_000)
    context = {"memory_context": {"second_brain": {"content": "b" * 5_000}}}
    prompt, trimmed = fit.fit_prompt(render, context, 900)
    content = context["memory_context"]["second_brain"]["content"]
    assert set(trimmed) == {"memory_context.second_brain"}
    assert content.endswith("[shortened to fit]") and len(content) >= fit.BRIEF_FLOOR


def test_budget_leaves_room_for_the_answer():
    assert fit.char_budget(900) > fit.char_budget(2_000)
    assert fit.char_budget(900, 1_000) == fit.char_budget(900) - 1_000


def test_too_long_refusal_is_named_and_stops_backups():
    from integrations.msty import api
    from core.llm.backends import ProviderRequestError

    backend = MagicMock(base_url="http://localhost:11454", timeout=10)
    refused = MagicMock(status_code=400, text='{"error":{"type":"exceed_context_size_error","n_ctx":8192}}')
    first = MagicMock(status_code=404)
    from core.llm import backends
    original = backends.requests.post
    backends.requests.post = MagicMock(side_effect=[first, refused])
    try:
        with pytest.raises(ProviderRequestError, match="context window"):
            api.backend_requests_post(backend, {"model": "m", "prompt": "p", "options": {}})
    finally:
        backends.requests.post = original
