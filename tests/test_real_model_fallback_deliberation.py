from dataclasses import replace

import pytest

from config.names import BELLATOR, RATIONALIS, TRIBUNAL_AGENT_IDS
from config.nodes import DEFAULT_NODES
from config.runtime import RuntimeConfig, load_runtime_config, runtime_config_to_dict
from core.export.verdict import deliberation_markdown
from core.history import result_to_dict
from core.models import FinalVerdict
from core.voting.engine import ConsensusEngine
from core.voting.orchestrator import VotingOrchestrator
from core.voting.rules import ConsensusRules
from integrations.msty import api
from integrations.msty.runtime import MstyRuntime


def valid_response(reason):
    return f"VOTE: APPROVE\nCONFIDENCE: 0.90\nEVIDENCE_QUALITY: 0.80\nCRITICAL_RISK: false\nRATIONALE: {reason}\nRISKS: resource assumptions\nCONDITIONS: audit and rollback"


@pytest.fixture(autouse=True)
def isolated_logs(monkeypatch):
    for module in ("core.voting.orchestrator", "integrations.msty.runtime"):
        monkeypatch.setattr(module + ".log_event", lambda *a, **kw: None)
        monkeypatch.setattr(module + ".log_error", lambda *a, **kw: None)
    monkeypatch.setattr(VotingOrchestrator, "_build_bellator_context_packet", lambda *a: {})
    monkeypatch.setattr("core.voting.orchestrator.build_aeternum_data_enrichment", lambda *a, **kw: {})


def provider(monkeypatch, models):
    monkeypatch.setattr(api, "health_check", lambda *a, **kw: {
        "status": "degraded", "models": models, "base_url": "http://localhost:1",
        "active_backend": "real-test-provider", "missing_required_models": {BELLATOR: "missing"},
    })


def test_candidate_priority_deduplication_aliases_and_strict_mode():
    models = ["other", "base:latest", "role:latest", "preferred:latest", "mock", "role:latest"]
    config = RuntimeConfig(base_model="base", agent_model_fallbacks={BELLATOR: ["absent", "role", "base"]})
    assert api.real_model_candidates(BELLATOR, "preferred", models, config) == ["preferred:latest", "role:latest", "base:latest", "other"]
    config.strict_provider_mode = True
    assert api.real_model_candidates(BELLATOR, "preferred", models, config) == ["preferred:latest"]
    assert api.real_model_candidates(BELLATOR, "missing", models, config) == []
    config.strict_provider_mode = False
    config.real_model_fallback_enabled = False
    assert api.real_model_candidates(BELLATOR, "missing", models, config) == []


def test_one_available_model_completes_real_exchange_with_three_role_parameters(monkeypatch):
    provider(monkeypatch, ["base:latest"])
    calls = []
    def send(model, prompt, **kwargs):
        calls.append((model, prompt, kwargs))
        role = next(role for role in TRIBUNAL_AGENT_IDS if f"Agent: {role}\n" in prompt)
        if "DELIBERATION ROUND: CRITIQUE" in prompt:
            assert "initial assessment" in prompt
            reason = f"{role} challenges the other roles' resource assumptions and requires audit"
        elif "DELIBERATION ROUND: REVISION" in prompt:
            assert "challenges the other roles" in prompt
            reason = f"{role} accepts the peer audit condition, retaining resource concerns"
        else:
            reason = f"{role} initial assessment of resources"
        return valid_response(reason)
    monkeypatch.setattr(api, "send_prompt", send)
    runtime = MstyRuntime(RuntimeConfig(base_model="base"))
    monkeypatch.setattr(runtime, "_fallback_response", lambda *a: pytest.fail("Must use a real model"))
    nodes = {role: replace(node, prompt=f"Custom instructions for {role}: {node.mission}", max_output_tokens=300 + i)
             for i, (role, node) in enumerate(DEFAULT_NODES.items())}
    orchestration = VotingOrchestrator(nodes, runtime)
    votes = orchestration.cast_votes("Review a prototype", "one-model", "military")
    result = ConsensusEngine(ConsensusRules(), "military").calculate_result("Review a prototype", votes, "one-model")
    orchestration.attach_audit(result)
    assert result.deliberation_complete and not result.simulation
    assert len(calls) == len(result.deliberation_transcript) == 9
    assert "real_model_fallback" in result.review_triggers
    assert "shared_model_roles" in result.review_triggers
    for turn, (model, prompt, kwargs) in zip(result.deliberation_transcript, calls):
        node = nodes[turn["agent_id"]]
        assert model == turn["model"] == "base:latest"
        assert turn["requested_model"] == node.model
        assert turn["model_fallback"]
        assert kwargs["system_prompt"] == node.prompt
        assert kwargs["temperature"] == node.temperature
        assert kwargs["max_output_tokens"] == node.max_output_tokens
        assert node.mission in prompt
    markdown = deliberation_markdown(result_to_dict(result))
    assert "preferred_model_unavailable" in markdown and "Model attempt: base:latest" in markdown


@pytest.mark.parametrize("failure", [TimeoutError("load timeout"), RuntimeError("empty"), ValueError("malformed")])
def test_failed_preferred_model_uses_base_and_pins_it_for_later_rounds(monkeypatch, failure):
    provider(monkeypatch, ["preferred", "base"])
    calls = []
    def send(model, *a, **kw):
        calls.append(model)
        if model == "preferred":
            if str(failure) == "empty":
                return ""
            if str(failure) == "malformed":
                return "I agree."
            raise failure
        return valid_response("Role preserved using base")
    monkeypatch.setattr(api, "send_prompt", send)
    runtime = MstyRuntime(RuntimeConfig(base_model="base"))
    context = {"model": "preferred", "session_id": "proposal-one", "require_real_model": True}
    runtime.send_to_agent(RATIONALIS, "assessment", context)
    first = runtime.last_execution[RATIONALIS]
    assert first["model_fallback"] and first["model_fallback_reason"] == "preferred_model_call_failed"
    assert [a["status"] for a in first["model_attempts"]] == ["failed", "completed"]
    runtime.send_to_agent(RATIONALIS, "critique", context)
    runtime.send_to_agent(RATIONALIS, "revision", context)
    assert calls == ["preferred", "base", "base", "base"]
    # A new proposal tries the preferred model again; pinning is proposal-specific.
    runtime.send_to_agent(RATIONALIS, "assessment", {**context, "session_id": "proposal-two"})
    assert calls[-2:] == ["preferred", "base"]


def test_exhausted_real_candidates_are_audited_and_never_simulated(monkeypatch):
    provider(monkeypatch, ["base", "another"])
    monkeypatch.setattr(api, "send_prompt", lambda *a, **kw: (_ for _ in ()).throw(TimeoutError("unusable model")))
    runtime = MstyRuntime(RuntimeConfig(base_model="base", mock_fallback_enabled=True))
    monkeypatch.setattr(runtime, "_fallback_response", lambda *a: pytest.fail("No fabricated votes"))
    orchestration = VotingOrchestrator(DEFAULT_NODES, runtime)
    votes = orchestration.cast_votes("Review a prototype", "failure", "military")
    result = ConsensusEngine(ConsensusRules(), "military").calculate_result("Review a prototype", votes, "failure")
    orchestration.attach_audit(result)
    assert result.verdict == FinalVerdict.NO_CONSENSUS
    assert not result.deliberation_complete and not result.simulation
    assert len(result.deliberation_transcript) == 3
    assert all([attempt["model"] for attempt in turn["model_attempts"]] == ["base", "another"] for turn in result.deliberation_transcript)


def test_no_available_real_models_fail_explicitly(monkeypatch):
    provider(monkeypatch, [])
    monkeypatch.setattr(api, "send_prompt", lambda *a, **kw: pytest.fail("No real model to call"))
    with pytest.raises(RuntimeError, match="no real fallback available"):
        MstyRuntime().send_to_agent(RATIONALIS, "assessment", {"require_real_model": True})


def test_fallback_config_roundtrip_and_health_policy(tmp_path, monkeypatch):
    import json
    config = RuntimeConfig(base_model="base", agent_model_fallbacks={RATIONALIS: ["role"]})
    path = tmp_path / "config.json"
    path.write_text(json.dumps(runtime_config_to_dict(config)))
    restored = load_runtime_config(path)
    assert restored.base_model == "base" and restored.agent_model_fallbacks[RATIONALIS] == ["role"]
    provider(monkeypatch, ["base"])
    assert MstyRuntime(restored).health_check()["fallback_policy"]["mode"] == "real_model_fallback"
