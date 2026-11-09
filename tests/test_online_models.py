"""Online voter models: routing, request shapes, key safety, local fallback and personal-context privacy."""
from __future__ import annotations

import json

import httpx
import pytest

from config.names import AETERNUM, AURELIUS, BELLATOR, RATIONALIS
from config.nodes import DEFAULT_NODES
from config.runtime import RuntimeConfig
from core.llm import online
from core.voting.orchestrator import VotingOrchestrator
from integrations.msty import api
from integrations.msty.runtime import MstyRuntime
from tests.argument_fixture import argument_fields

KEY = "sk-test-not-a-real-key"


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    for name in ("CONSENSUS_ONLINE_MODELS", "CONSENSUS_ONLINE_SHARE_PERSONAL", "CONSENSUS_ONLINE_TOKEN_BUDGET",
                 "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY",
                 *(online.ENV_PREFIX + agent for agent in (RATIONALIS, AETERNUM, BELLATOR, AURELIUS))):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CONSENSUS_ONLINE_ENV_FILE", "")
    for module in ("core.voting.orchestrator", "integrations.msty.runtime"):
        monkeypatch.setattr(module + ".log_event", lambda *a, **kw: None)
        monkeypatch.setattr(module + ".log_error", lambda *a, **kw: None)
    monkeypatch.setattr(VotingOrchestrator, "_build_bellator_context_packet", lambda *a: {})
    monkeypatch.setattr("core.voting.orchestrator.build_aeternum_data_enrichment", lambda *a, **kw: {})


def _response(status: int, payload: dict) -> httpx.Response:
    return httpx.Response(status, json=payload, request=httpx.Request("POST", "https://example.invalid"))


def test_a_voter_goes_online_only_with_a_model_and_a_key(monkeypatch):
    monkeypatch.setenv(online.ENV_PREFIX + RATIONALIS, "anthropic:claude-sonnet-5-5")
    monkeypatch.setenv(online.ENV_PREFIX + BELLATOR, "deepseek:deepseek-chat")
    monkeypatch.setenv(online.ENV_PREFIX + AETERNUM, "nonsense")
    monkeypatch.setenv(online.ENV_PREFIX + AURELIUS, "openai:gpt-5")
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    monkeypatch.setenv("OPENAI_API_KEY", KEY)
    assert online.route_for(RATIONALIS).label == "anthropic:claude-sonnet-5-5"
    assert online.route_for(BELLATOR) is None  # no DeepSeek key
    assert online.route_for(AETERNUM) is None
    assert online.route_for(AURELIUS) is None  # the assistant is not a tribunal voter
    states = {row["agent_id"]: row["state"] for row in online.status_report()}
    assert states == {RATIONALIS: "online", BELLATOR: "no key (DEEPSEEK_API_KEY)", AETERNUM: "invalid setting"}
    assert KEY not in json.dumps(online.status_report())
    monkeypatch.setenv("CONSENSUS_ONLINE_MODELS", "0")
    assert online.route_for(RATIONALIS) is None


def test_settings_come_from_the_env_file_and_the_shell_wins(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(f"{online.ENV_PREFIX}BELLATOR=openai:gpt-file\nOPENAI_API_KEY={KEY}\n", encoding="utf-8")
    monkeypatch.setenv("CONSENSUS_ONLINE_ENV_FILE", str(env_file))
    assert online.route_for(BELLATOR).model == "gpt-file"
    monkeypatch.setenv(online.ENV_PREFIX + BELLATOR, "openai:gpt-shell")
    assert online.route_for(BELLATOR).model == "gpt-shell"


def test_anthropic_request_and_answer(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    sent = {}

    def post(url, headers, body, timeout):
        sent.update(url=url, headers=headers, body=body)
        return _response(200, {"content": [{"type": "text", "text": "VOTE: APPROVE"}], "stop_reason": "end_turn",
                               "usage": {"input_tokens": 1200, "output_tokens": 80}})

    route = online.parse_route(RATIONALIS, "anthropic:claude-sonnet-5-5")
    result = online.complete(route, "You are RATIONALIS.", "Proposal", temperature=0.3, max_tokens=900, post=post)
    assert (result.text, result.input_tokens, result.output_tokens) == ("VOTE: APPROVE", 1200, 80)
    assert sent["url"] == "https://api.anthropic.com/v1/messages"
    assert sent["headers"]["x-api-key"] == KEY and sent["headers"]["anthropic-version"]
    assert sent["body"]["system"] == "You are RATIONALIS." and sent["body"]["temperature"] == 0.3
    assert sent["body"]["max_tokens"] == online.MIN_OUTPUT_TOKENS


@pytest.mark.parametrize("name,field", [("openai", "max_completion_tokens"), ("deepseek", "max_tokens")])
def test_openai_style_requests(monkeypatch, name, field):
    monkeypatch.setenv(online.PROVIDERS[name].key_env, KEY)
    sent = {}

    def post(url, headers, body, timeout):
        sent.update(url=url, headers=headers, body=body)
        return _response(200, {"choices": [{"message": {"content": "VOTE: DENY"}, "finish_reason": "stop"}],
                               "usage": {"prompt_tokens": 50, "completion_tokens": 5}})

    result = online.complete(online.parse_route(BELLATOR, f"{name}:m"), "sys", "Proposal", max_tokens=9000, post=post)
    assert result.text == "VOTE: DENY" and result.input_tokens == 50
    assert sent["url"].endswith("/chat/completions") and sent["headers"]["authorization"] == f"Bearer {KEY}"
    assert sent["body"][field] == 9000 and sent["body"]["messages"][0] == {"role": "system", "content": "sys"}


def test_errors_never_contain_the_key_and_temperature_is_retried(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", KEY)
    route = online.parse_route(BELLATOR, "openai:gpt-5")
    with pytest.raises(online.OnlineModelError) as error:
        online.complete(route, "", "x", post=lambda *a: _response(401, {"error": {"message": f"bad key {KEY}"}}))
    assert KEY not in str(error.value) and "OPENAI_API_KEY" in str(error.value)

    bodies = []

    def picky(url, headers, body, timeout):
        bodies.append(dict(body))
        if "temperature" in body:
            return _response(400, {"error": {"message": "Unsupported value: 'temperature'"}})
        return _response(200, {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]})

    assert online.complete(route, "", "x", temperature=0.2, post=picky).text == "ok"
    assert "temperature" in bodies[0] and "temperature" not in bodies[1]

    with pytest.raises(online.OnlineModelError, match="did not finish"):
        online.complete(route, "", "x", post=lambda *a: _response(200, {"choices": [{"message": {"content": "VO"}, "finish_reason": "length"}]}))


def _local_provider(monkeypatch, calls):
    monkeypatch.setattr(api, "health_check", lambda *a, **kw: {
        "status": "ready", "models": ["base:latest"], "base_url": "http://localhost:1", "active_backend": "local-test"})

    def send(model, prompt, **kwargs):
        context = json.JSONDecoder().raw_decode(prompt.split("Shared machine context:\n", 1)[1])[0]
        agent = next(a for a in (RATIONALIS, AETERNUM, BELLATOR) if f"Agent: {a}\n" in prompt)
        calls.append(("local", agent, prompt))
        return _vote(agent, context)
    monkeypatch.setattr(api, "send_prompt", send)


def _vote(agent, context):
    reason = f"{agent} reviewed the prototype resources"
    return ("VOTE: APPROVE\nCONFIDENCE: 0.90\nEVIDENCE_QUALITY: 0.80\nCRITICAL_RISK: false\n"
            f"RATIONALE: {reason}\nRISKS: resources\nCONDITIONS: audit" + argument_fields(reason, agent, context))


def _deliberate(runtime):
    memory = {"prior_decisions_used": 0, "items": [], "summary": "none", "second_brain": {"brief": "PRIVATE-OWNER-NOTE"}}
    orchestration = VotingOrchestrator(DEFAULT_NODES, runtime)
    orchestration.cast_votes("Review a prototype", "online-test", "military", memory_context=memory)
    return orchestration.transcript


def test_online_voter_deliberates_without_personal_context(monkeypatch):
    monkeypatch.setenv(online.ENV_PREFIX + RATIONALIS, "anthropic:claude-sonnet-5-5")
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    calls = []
    _local_provider(monkeypatch, calls)

    def fake_complete(route, system, prompt, **kwargs):
        context = json.JSONDecoder().raw_decode(prompt.split("Shared machine context:\n", 1)[1])[0]
        calls.append(("online", route.agent_id, prompt))
        return online.OnlineResult(_vote(route.agent_id, context), 3000, 200)
    monkeypatch.setattr(online, "complete", fake_complete)

    transcript = _deliberate(MstyRuntime(RuntimeConfig(base_model="base")))
    assert len(transcript) == 9
    for turn in transcript:
        if turn["agent_id"] == RATIONALIS:
            assert turn["backend"] == "online:anthropic" and turn["model"] == "anthropic:claude-sonnet-5-5"
        else:
            assert turn["backend"] == "local-test"
    for where, agent, prompt in calls:
        assert ("PRIVATE-OWNER-NOTE" in prompt) == (where == "local")
        assert (where == "online") == (agent == RATIONALIS)


def test_failed_online_call_falls_back_to_the_local_model(monkeypatch):
    monkeypatch.setenv(online.ENV_PREFIX + BELLATOR, "deepseek:deepseek-chat")
    monkeypatch.setenv("DEEPSEEK_API_KEY", KEY)
    calls = []
    _local_provider(monkeypatch, calls)
    monkeypatch.setattr(online, "complete", lambda *a, **kw: (_ for _ in ()).throw(online.OnlineModelError("DeepSeek could not be reached")))

    transcript = _deliberate(MstyRuntime(RuntimeConfig(base_model="base")))
    bellator = [turn for turn in transcript if turn["agent_id"] == BELLATOR]
    assert bellator and all(turn["backend"] == "local-test" and turn["model_fallback"] for turn in bellator)
    assert bellator[0]["model_fallback_reason"] == "online_model_failed"
    assert bellator[0]["model_attempts"][0]["model"] == "deepseek:deepseek-chat"
    assert all(turn["status"] == "completed" for turn in transcript)


def test_token_budget_sends_later_rounds_to_the_local_model(monkeypatch):
    monkeypatch.setenv(online.ENV_PREFIX + AETERNUM, "openai:gpt-5")
    monkeypatch.setenv("OPENAI_API_KEY", KEY)
    monkeypatch.setenv("CONSENSUS_ONLINE_TOKEN_BUDGET", "1000")
    calls = []
    _local_provider(monkeypatch, calls)

    def fake_complete(route, system, prompt, **kwargs):
        context = json.JSONDecoder().raw_decode(prompt.split("Shared machine context:\n", 1)[1])[0]
        return online.OnlineResult(_vote(route.agent_id, context), 900, 200)
    monkeypatch.setattr(online, "complete", fake_complete)

    transcript = _deliberate(MstyRuntime(RuntimeConfig(base_model="base")))
    backends = [turn["backend"] for turn in transcript if turn["agent_id"] == AETERNUM]
    assert backends == ["online:openai", "local-test", "local-test"]


def test_subscription_tools_route_when_installed_and_never_get_api_keys(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda name: f"C:/tools/{name}.exe" if name in {"claude", "codex"} else None)
    monkeypatch.setenv(online.ENV_PREFIX + RATIONALIS, "claude-cli:sonnet")
    monkeypatch.setenv(online.ENV_PREFIX + AETERNUM, "codex-cli:default")
    monkeypatch.setenv(online.ENV_PREFIX + BELLATOR, "grok-cli:default")
    assert online.route_for(RATIONALIS).provider.subscription
    assert online.route_for(AETERNUM).label == "codex-cli:default"
    assert online.route_for(BELLATOR) is None
    assert {row["agent_id"]: row["state"] for row in online.status_report()}[BELLATOR] == "'grok' not installed"

    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    assert "ANTHROPIC_API_KEY" not in online._cli_env(online.PROVIDERS["claude-cli"])

    files = [tmp_path / name for name in ("prompt.txt", "system.txt", "answer.txt")]
    claude = online.cli_command(online.route_for(RATIONALIS), "sys", *files)
    codex = online.cli_command(online.route_for(AETERNUM), "sys", *files)
    assert claude[1] == "-p" and claude[claude.index("--tools") + 1] == "" and "--model" in claude
    assert codex[-1] == "-" and "--model" not in codex and "read-only" in codex


def test_subscription_answers_are_read(tmp_path):
    claude = online.parse_route(RATIONALIS, "claude-cli:sonnet")
    stdout = json.dumps({"is_error": False, "result": "VOTE: APPROVE",
                         "usage": {"input_tokens": 3, "cache_read_input_tokens": 1000, "output_tokens": 9}})
    result = online._cli_result(claude, "log line\n" + stdout, tmp_path / "none")
    assert (result.text, result.input_tokens, result.output_tokens) == ("VOTE: APPROVE", 1003, 9)
    with pytest.raises(online.OnlineModelError):
        online._cli_result(claude, json.dumps({"is_error": True, "result": "limit reached"}), tmp_path / "none")
    answer = tmp_path / "answer.txt"
    answer.write_text("VOTE: DENY", encoding="utf-8")
    assert online._cli_result(online.parse_route(AETERNUM, "codex-cli:default"), "", answer).text == "VOTE: DENY"
