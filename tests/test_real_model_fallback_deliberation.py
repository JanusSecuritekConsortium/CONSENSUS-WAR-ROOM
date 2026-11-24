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
from tests.argument_fixture import argument_fields


def valid_response(reason, agent=None, context=None):
    return f"VOTE: APPROVE\nCONFIDENCE: 0.90\nEVIDENCE_QUALITY: 0.80\nCRITICAL_RISK: false\nRATIONALE: {reason}\nRISKS: resource assumptions\nCONDITIONS: audit and rollback" + argument_fields(reason, agent, context)


@pytest.fixture(autouse=True)
def isolated_logs(monkeypatch):
    for module in ("core.voting.orchestrator", "integrations.msty.runtime"):
        monkeypatch.setattr(module + ".log_event", lambda *a, **kw: None)
        monkeypatch.setattr(module + ".log_error", lambda *a, **kw: None)
    monkeypatch.setattr(VotingOrchestrator, "_build_bellator_context_packet", lambda *a: {})
    monkeypatch.setattr("core.voting.orchestrator.build_aeternum_data_enrichment", lambda *a, **kw: {})


@pytest.fixture(autouse=True)
def no_real_model_server(monkeypatch):
    # The memory check before each model load must never reach a real server: on Windows each refused
    # connection to the fixture address waits seconds, and with Msty running the test seemed to hang.
    # Tests of that check set their own fakes.
    monkeypatch.setattr(api, "loaded_models", lambda *a, **kw: [])
    monkeypatch.setattr(api, "model_file_sizes", lambda *a, **kw: {})


def provider(monkeypatch, models):
    monkeypatch.setattr(api, "health_check", lambda *a, **kw: {
        "status": "degraded", "models": models, "base_url": "http://localhost:1",
        "active_backend": "real-test-provider", "missing_required_models": {BELLATOR: "missing"},
    })


REAL_SAME_MAKER = api.same_model_maker


@pytest.fixture(autouse=True)
def any_maker_for_placeholder_names(monkeypatch):
    # These tests use placeholder names with no maker; the same-maker rule has its own test below.
    monkeypatch.setattr(api, "same_model_maker", lambda first, second: True)


def test_backups_come_only_from_the_voters_own_maker(monkeypatch):
    monkeypatch.setattr(api, "same_model_maker", REAL_SAME_MAKER)
    installed = ["unsloth/Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf", "NousResearch/Hermes-3-Llama-3.1-8B.Q4_K_M.gguf",
                 "Aurelius-Qwen3.5-9B-abliterated.Q5_K_M.gguf", "unsloth/Qwen3.8-27B-UD-Q4_K_M.gguf",
                 "gemma-3-12b-it-Q3_K_L.gguf", "unsloth/gemma-4-26B-A4B-it-UD-Q4_K_M.gguf", "ui-tars-1.5-7b-q4_k_m.gguf"]
    config = RuntimeConfig(base_model="Hermes-3-Llama-3.1-8B")
    candidates = lambda preferred: api.real_model_candidates(BELLATOR, preferred, installed, config)
    assert candidates("unsloth/Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf") == ["unsloth/Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf"]
    assert candidates("unsloth/Qwen3.8-27B-UD-Q4_K_M.gguf") == ["unsloth/Qwen3.8-27B-UD-Q4_K_M.gguf", "Aurelius-Qwen3.5-9B-abliterated.Q5_K_M.gguf"]
    assert candidates("unsloth/gemma-4-26B-A4B-it-UD-Q4_K_M.gguf") == ["unsloth/gemma-4-26B-A4B-it-UD-Q4_K_M.gguf", "gemma-3-12b-it-Q3_K_L.gguf"]
    assert candidates("NousResearch/Hermes-3-Llama-3.1-8B.Q4_K_M.gguf") == ["NousResearch/Hermes-3-Llama-3.1-8B.Q4_K_M.gguf"]
    assert api.model_maker("ui-tars-1.5-7b-q4_k_m.gguf") == ""
    config.backups_same_maker_only = False
    assert len(candidates("unsloth/Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf")) == len(installed)


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


def test_giant_models_are_never_swept_in_as_backups():
    # Llama 3.3 70B filled the PC's memory for 25 minutes as a last-resort backup (17 Nov vote 3).
    models = ["preferred", "Llama-3.3-70B-Instruct-Q3_K_L.gguf", "qwen2.5:72b", "Hermes-3-Llama-3.1-8B.gguf", "mixtral:8x7b"]
    config = RuntimeConfig(base_model="base")
    assert api.real_model_candidates(BELLATOR, "preferred", models, config) == ["preferred", "Hermes-3-Llama-3.1-8B.gguf", "mixtral:8x7b"]
    assert api.real_model_candidates(BELLATOR, "qwen2.5:72b", models, config)[0] == "qwen2.5:72b"


def test_one_available_model_completes_real_exchange_with_three_role_parameters(monkeypatch):
    provider(monkeypatch, ["base:latest"])
    calls = []
    def send(model, prompt, **kwargs):
        import json
        context = json.JSONDecoder().raw_decode(prompt.split("Shared machine context:\n", 1)[1])[0]
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
        return valid_response(reason, role, context)
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


@pytest.mark.parametrize("failure", [RuntimeError("provider error"), "empty", "malformed"])
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
    # A malformed answer gets one correction on the same model before the backup.
    preferred = ["preferred", "preferred"] if str(failure) == "malformed" else ["preferred"]
    assert [a["status"] for a in first["model_attempts"]] == ["failed"] * len(preferred) + ["completed"]
    runtime.send_to_agent(RATIONALIS, "critique", context)
    runtime.send_to_agent(RATIONALIS, "revision", context)
    assert calls == [*preferred, "base", "base", "base"]
    # A new proposal tries the preferred model again; pinning is proposal-specific.
    runtime.send_to_agent(RATIONALIS, "assessment", {**context, "session_id": "proposal-two"})
    assert calls[-len(preferred) - 1:] == [*preferred, "base"]


def test_exhausted_real_candidates_are_audited_and_never_simulated(monkeypatch):
    provider(monkeypatch, ["base", "another"])
    monkeypatch.setattr(api, "send_prompt", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("unusable model")))
    runtime = MstyRuntime(RuntimeConfig(base_model="base", mock_fallback_enabled=True))
    monkeypatch.setattr(runtime, "_fallback_response", lambda *a: pytest.fail("No fabricated votes"))
    orchestration = VotingOrchestrator(DEFAULT_NODES, runtime)
    votes = orchestration.cast_votes("Review a prototype", "failure", "military")
    result = ConsensusEngine(ConsensusRules(), "military").calculate_result("Review a prototype", votes, "failure")
    orchestration.attach_audit(result)
    assert result.verdict == FinalVerdict.NO_CONSENSUS
    assert not result.deliberation_complete and not result.simulation
    first, *rest = result.deliberation_transcript
    assert first["status"] == "failed" and [attempt["model"] for attempt in first["model_attempts"]] == ["base", "another"]
    # The round stops at the first failure: the other voters are recorded as not asked, with no model calls.
    assert [turn["status"] for turn in rest] == ["not_asked", "not_asked"]
    assert all(turn["model_attempts"] == [] for turn in rest)


def test_a_timeout_stops_instead_of_loading_more_models(monkeypatch):
    provider(monkeypatch, ["preferred", "base", "another"])
    calls = []
    def send(model, *a, **kw):
        calls.append(model)
        raise api.ProviderRequestError("Provider generation unavailable: Read timed out. (read timeout=900)")
    monkeypatch.setattr(api, "send_prompt", send)
    runtime = MstyRuntime(RuntimeConfig(base_model="base"))
    with pytest.raises(api.ProviderRequestError):
        runtime.send_to_agent(RATIONALIS, "assessment", {"model": "preferred", "session_id": "p", "require_real_model": True})
    assert calls == ["preferred"]
    assert RuntimeConfig().generation_timeout_seconds >= 600


def test_a_too_long_prompt_never_tries_backup_models(monkeypatch):
    # Every model on the server shares one window; on 17/11 the backups ended at a 70B model that jammed the PC.
    provider(monkeypatch, ["preferred", "base", "another"])
    calls = []
    def send(model, *a, **kw):
        calls.append(model)
        raise api.ProviderRequestError("Prompt too long for the model's context window at http://localhost:11454")
    monkeypatch.setattr(api, "send_prompt", send)
    runtime = MstyRuntime(RuntimeConfig(base_model="base"))
    with pytest.raises(api.ProviderRequestError):
        runtime.send_to_agent(RATIONALIS, "assessment", {"model": "preferred", "session_id": "p", "require_real_model": True})
    assert calls == ["preferred"]


def test_every_other_model_is_unloaded_before_a_voter_runs(monkeypatch):
    # Test vote 8: a model left loaded beside the voter's pushed it into swap; each answer took twenty minutes.
    provider(monkeypatch, ["deepseek:33b", "yi:34b", "base", "user-chat-model"])
    monkeypatch.setattr(api, "loaded_models", lambda base_url: ["yi:34b", "base", "user-chat-model"])
    unloaded = []
    monkeypatch.setattr(api, "unload_model", lambda base_url, model: unloaded.append(model) or True)
    monkeypatch.setattr(api, "send_prompt", lambda *a, **kw: valid_response("Room made"))
    config = RuntimeConfig(base_model="base", agent_model_overrides={RATIONALIS: "deepseek:33b", BELLATOR: "yi:34b"})
    MstyRuntime(config).send_to_agent(RATIONALIS, "assessment", {"model": "deepseek:33b", "session_id": "p", "require_real_model": True})
    assert unloaded == ["base", "user-chat-model", "yi:34b"]  # each reloads on its next use
    unloaded.clear()
    config.unload_idle_tribunal_models = False
    MstyRuntime(config).send_to_agent(RATIONALIS, "assessment", {"model": "deepseek:33b", "session_id": "q", "require_real_model": True})
    assert unloaded == []


def _health(active, models):
    return {"status": "ready", "models": models, "base_url": "http://localhost:1",
            "requested_backend": "msty-llama-cpp", "active_backend": active}


def test_a_voter_waits_for_its_own_server_instead_of_another_servers_model(monkeypatch):
    # Test vote 7: Msty's server was down, so a small Ollama "mistral:latest" stood in for Mistral Small 3.2.
    states = [_health("ollama-direct", ["mistral:latest"]), _health("ollama-direct", ["mistral:latest"]),
              _health("msty-llama-cpp", ["unsloth/Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf"])]
    monkeypatch.setattr(api, "health_check", lambda *a, **kw: states.pop(0) if len(states) > 1 else states[0])
    calls = []
    monkeypatch.setattr(api, "send_prompt", lambda model, *a, **kw: calls.append(model) or valid_response("Back", BELLATOR))
    runtime = MstyRuntime(RuntimeConfig())
    naps = []
    runtime._sleep = naps.append
    runtime.send_to_agent(BELLATOR, "assessment", {"model": "unsloth/Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf",
                                                   "session_id": "p", "require_real_model": True})
    assert calls == ["unsloth/Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf"]
    assert len(naps) == 2


def test_a_voter_fails_openly_when_its_server_stays_down(monkeypatch):
    import integrations.msty.runtime as runtime_module
    monkeypatch.setattr(api, "health_check", lambda *a, **kw: _health("ollama-direct", ["mistral:latest"]))
    monkeypatch.setattr(api, "send_prompt", lambda *a, **kw: pytest.fail("No other server's model may answer"))
    clock = [0.0]
    monkeypatch.setattr(runtime_module.time, "monotonic", lambda: clock[0])
    runtime = MstyRuntime(RuntimeConfig())
    runtime._sleep = lambda seconds: clock.__setitem__(0, clock[0] + seconds)
    with pytest.raises(RuntimeError, match="does not switch"):
        runtime.send_to_agent(BELLATOR, "assessment", {"model": "mistral-small", "session_id": "p", "require_real_model": True})
    assert clock[0] >= runtime_module.OWN_SERVER_WAIT_SECONDS


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


def _roomy_provider(monkeypatch, free):
    provider(monkeypatch, ["deepseek:33b"])
    gb = 2**30
    monkeypatch.setattr(api, "loaded_models", lambda base_url: [])
    monkeypatch.setattr(api, "model_file_sizes", lambda base_url: {"deepseek:33b": 17 * gb})
    monkeypatch.setattr(api, "free_memory_bytes", lambda: free.pop(0) * gb if len(free) > 1 else free[0] * gb)
    calls = []
    monkeypatch.setattr(api, "send_prompt", lambda model, *a, **kw: calls.append(model) or valid_response("Fits"))
    runtime = MstyRuntime(RuntimeConfig(base_model="deepseek:33b", agent_model_overrides={RATIONALIS: "deepseek:33b"}))
    slept = []
    runtime._sleep = slept.append
    return runtime, calls, slept


def test_a_voter_waits_until_its_model_fits_in_memory(monkeypatch):
    # 17 GB model plus 3 GB headroom: 12 GB free is too little, 21 GB is enough.
    runtime, calls, slept = _roomy_provider(monkeypatch, [12, 12, 21])
    runtime.send_to_agent(RATIONALIS, "assessment", {"model": "deepseek:33b", "session_id": "m", "require_real_model": True})
    assert calls == ["deepseek:33b"] and len(slept) == 2


def test_a_voter_fails_openly_instead_of_answering_from_swap(monkeypatch):
    import integrations.msty.runtime as runtime_module
    runtime, calls, slept = _roomy_provider(monkeypatch, [12])
    clock = iter(range(0, 10_000, 300))
    monkeypatch.setattr(runtime_module.time, "monotonic", lambda: next(clock))
    with pytest.raises(RuntimeError, match="Not enough free memory for deepseek:33b"):
        runtime.send_to_agent(RATIONALIS, "assessment", {"model": "deepseek:33b", "session_id": "n", "require_real_model": True})
    assert calls == []


def test_a_voter_moves_to_its_smaller_backup_when_memory_is_short(monkeypatch):
    # Codex review 2026-11-24: "not enough memory" ended the voter instead of trying the installed smaller backup.
    import integrations.msty.runtime as runtime_module
    provider(monkeypatch, ["big:33b", "small:8b"])
    gb = 2**30
    monkeypatch.setattr(api, "loaded_models", lambda base_url: [])
    monkeypatch.setattr(api, "model_file_sizes", lambda base_url: {"big:33b": 17 * gb, "small:8b": 5 * gb})
    monkeypatch.setattr(api, "free_memory_bytes", lambda: 12 * gb)
    clock = iter(range(0, 100_000, 300))
    monkeypatch.setattr(runtime_module.time, "monotonic", lambda: next(clock))
    calls = []
    monkeypatch.setattr(api, "send_prompt", lambda model, *a, **kw: calls.append(model) or valid_response("Fits"))
    runtime = MstyRuntime(RuntimeConfig(base_model="small:8b", agent_model_overrides={RATIONALIS: "big:33b"}))
    runtime._sleep = lambda seconds: None
    response = runtime.send_to_agent(RATIONALIS, "assessment", {"model": "big:33b", "session_id": "s", "require_real_model": True})
    assert calls == ["small:8b"] and "Fits" in response


def test_a_missing_main_model_never_lets_another_makers_model_in(monkeypatch):
    # Codex review 2026-11-24: with the main model not installed, the rule had nothing to compare against.
    monkeypatch.setattr(api, "same_model_maker", REAL_SAME_MAKER)
    config = RuntimeConfig(base_model="Hermes-3-Llama-3.1-8B")
    hermes = "NousResearch/Hermes-3-Llama-3.1-8B.Q4_K_M.gguf"
    ministral = "mistralai/Ministral-3-8B-Instruct-2512-Q4_K_M.gguf"
    mistral_small = "unsloth/Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf"
    assert api.real_model_candidates(BELLATOR, mistral_small, [hermes, ministral], config) == [ministral]
    assert api.real_model_candidates(BELLATOR, mistral_small, [hermes, "gemma-3-12b-it-Q3_K_L.gguf"], config) == []


def test_a_missing_main_model_still_lets_unnamed_local_models_stand_in(monkeypatch):
    # 9.21.2 lesson: the owner's own unnamed models (and the local stand-in for online voters) stay allowed.
    monkeypatch.setattr(api, "same_model_maker", REAL_SAME_MAKER)
    config = RuntimeConfig(base_model="base")
    mistral_small = "unsloth/Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf"
    assert api.real_model_candidates(BELLATOR, mistral_small, ["base", "another"], config) == ["base"]
