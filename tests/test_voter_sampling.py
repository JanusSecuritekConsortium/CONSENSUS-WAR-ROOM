"""Each voter samples in its own way, and the settings reach the model server on both routes."""
from __future__ import annotations

from config.agents import AGENT_PROFILES
from config.names import AETERNUM, ARBITER, BELLATOR, RATIONALIS
from config.nodes import DEFAULT_NODES, apply_node_overrides
from config.runtime import RuntimeConfig
from core.llm import backends
from core.llm.backends import chat_sampling
from integrations.msty import api


def test_each_voter_has_its_own_sampling():
    styles = {agent: DEFAULT_NODES[agent].sampling() for agent in (RATIONALIS, AETERNUM, BELLATOR)}
    assert len({tuple(sorted(style.items())) for style in styles.values()}) == 3
    # RATIONALIS is the tightest, BELLATOR the widest, AETERNUM has room for long answers.
    assert styles[RATIONALIS]["top_p"] < styles[AETERNUM]["top_p"] < styles[BELLATOR]["top_p"]
    assert DEFAULT_NODES[AETERNUM].max_output_tokens > DEFAULT_NODES[RATIONALIS].max_output_tokens


def test_sampling_can_be_overridden_per_voter():
    nodes = apply_node_overrides(DEFAULT_NODES, {"BELLATOR": {"top_p": 0.7, "repeat_penalty": 1.1}})
    assert nodes[BELLATOR].sampling()["top_p"] == 0.7
    assert nodes[BELLATOR].sampling()["repeat_penalty"] == 1.1


def test_chat_route_keeps_only_set_sampling_values():
    assert chat_sampling({"temperature": 0.2, "top_p": 0.8, "top_k": None, "min_p": 0.05}) == {"top_p": 0.8, "min_p": 0.05}


def test_send_prompt_passes_sampling_to_both_routes(monkeypatch):
    sent = []

    class Response:
        def __init__(self, status, body):
            self.status_code, self._body = status, body

        def raise_for_status(self):
            pass

        def json(self):
            return self._body

    def post(url, json, timeout):
        sent.append((url, json))
        if url.endswith("/api/generate"):
            return Response(404, {})
        return Response(200, {"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(backends.requests, "post", post)
    text = api.send_prompt("m", "hello", config=RuntimeConfig(), base_url="http://x",
                           temperature=0.2, max_output_tokens=900, sampling={"top_p": 0.8, "top_k": 20})
    assert text == "ok"
    assert sent[0][1]["options"] == {"temperature": 0.2, "num_predict": 900, "top_p": 0.8, "top_k": 20}
    assert sent[1][1]["top_p"] == 0.8 and sent[1][1]["top_k"] == 20


def test_long_answer_limit_and_arbiter_default():
    assert RuntimeConfig().generation_timeout_seconds >= 1500
    assert AGENT_PROFILES[ARBITER].model_preference != AGENT_PROFILES[AETERNUM].model_preference
