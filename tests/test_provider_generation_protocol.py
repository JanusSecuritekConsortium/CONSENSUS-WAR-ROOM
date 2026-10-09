from unittest.mock import Mock

import pytest
import requests

from core.llm.backends import OllamaBackend, ProviderRequestError
from integrations.msty.api import backend_requests_post


def reply(status, body):
    result = Mock(status_code=status)
    result.json.return_value = body
    if status >= 400:
        result.raise_for_status.side_effect = requests.HTTPError(f"Controlled HTTP {status}")
    return result


@pytest.mark.parametrize("rejected_route", [404, 405])
def test_msty_chat_translation_preserves_model_prompt_and_settings(monkeypatch, rejected_route):
    calls = []
    responses = iter([reply(rejected_route, {}), reply(200, {"choices": [{"message": {"content": "VOTE: APPROVE"}}]})])
    monkeypatch.setattr(requests, "post", lambda url, **kwargs: calls.append((url, kwargs)) or next(responses))
    result = backend_requests_post(OllamaBackend("http://localhost:1"), {"model": "assigned-model", "prompt": "role and proposal", "options": {"temperature": 0.6, "num_predict": 321}})
    assert result == {"response": "VOTE: APPROVE"}
    assert calls[1][0] == "http://localhost:1/v1/chat/completions"
    assert calls[1][1]["json"] == {"model": "assigned-model", "messages": [{"role": "user", "content": "role and proposal"}], "stream": False, "temperature": 0.6, "max_tokens": 321}


def test_ollama_success_does_not_call_chat(monkeypatch):
    post = Mock(return_value=reply(200, {"response": "vote"}))
    monkeypatch.setattr(requests, "post", post)
    assert backend_requests_post(OllamaBackend("http://localhost:1"), {"model": "model", "prompt": "proposal"}) == {"response": "vote"}
    assert post.call_count == 1


@pytest.mark.parametrize("failure", [requests.Timeout("Controlled timeout"), requests.ConnectionError("Controlled connection failure"), reply(500, {})])
def test_generation_failures_are_not_replayed(monkeypatch, failure):
    post = Mock(side_effect=failure) if isinstance(failure, Exception) else Mock(return_value=failure)
    monkeypatch.setattr(requests, "post", post)
    with pytest.raises(ProviderRequestError):
        backend_requests_post(OllamaBackend("http://localhost:1"), {"model": "model", "prompt": "proposal"})
    assert post.call_count == 1


def test_empty_chat_choices_are_explicit_failure(monkeypatch):
    post = Mock(side_effect=[reply(404, {}), reply(200, {"choices": []})])
    monkeypatch.setattr(requests, "post", post)
    with pytest.raises(ProviderRequestError, match="no choices"):
        backend_requests_post(OllamaBackend("http://localhost:1"), {"model": "model", "prompt": "proposal"})
