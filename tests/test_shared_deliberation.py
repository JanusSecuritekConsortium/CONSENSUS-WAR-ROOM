from copy import deepcopy
from dataclasses import replace
import json

import pytest

from config.names import AETERNUM, BELLATOR, RATIONALIS, TRIBUNAL_AGENT_IDS
from config.nodes import DEFAULT_NODES
from config.runtime import RuntimeConfig
from core.history import result_to_dict
from core.models import FinalVerdict
from core.tribunal import Tribunal
from core.voting.engine import ConsensusEngine
from core.voting.orchestrator import VotingOrchestrator
from core.voting.rules import ConsensusRules
from integrations.msty import api
from integrations.msty.runtime import MstyRuntime


def response(reason, value="APPROVE"):
    return f"VOTE: {value}\nCONFIDENCE: 0.90\nEVIDENCE_QUALITY: 0.85\nCRITICAL_RISK: false\nRATIONALE: {reason}\nRISKS: residual risk\nCONDITIONS: audit and rollback"


class DiscussionRuntime:
    def __init__(self, failure=None, malformed=False):
        self.calls = []
        self.failure = failure
        self.malformed = malformed
        self.config = RuntimeConfig()

    def send_to_agent(self, agent_id, prompt, context=None):
        self.calls.append((agent_id, prompt, deepcopy(context)))
        phase = context["deliberation"]["phase"]
        if (agent_id, phase) == self.failure:
            if self.malformed:
                return "I approve without the required vote schema."
            raise TimeoutError("Controlled provider timeout")
        if phase == "assessment":
            return response(f"{agent_id} initial independent assessment")
        if phase == "critique":
            return response(f"{agent_id} challenges BELLATOR and AETERNUM cost assumptions; require audit and rollback")
        return response(f"{agent_id} accepts peer audit condition, rejects unsupported cost claim, and revises vote", "DENY" if agent_id == BELLATOR else "APPROVE")


@pytest.fixture(autouse=True)
def isolated_context(monkeypatch):
    monkeypatch.setattr(VotingOrchestrator, "_build_bellator_context_packet", lambda self, query: {"label": "BELLATOR CONTEXT PACKET"})
    monkeypatch.setattr("core.voting.orchestrator.build_aeternum_data_enrichment", lambda *a, **kw: {"label": "AETERNUM DATA PACKET"})
    monkeypatch.setattr("core.voting.orchestrator.log_event", lambda *a, **kw: None)
    monkeypatch.setattr("core.voting.orchestrator.log_error", lambda *a, **kw: None)


@pytest.mark.parametrize("sequential", [False, True])
def test_every_agent_sees_completed_assessments_and_critiques(sequential):
    runtime = DiscussionRuntime()
    orchestrator = VotingOrchestrator(DEFAULT_NODES, runtime)
    votes = orchestrator.cast_votes("Analyze a prototype with audit and rollback", "test", "military", sequential)
    assert [call[0] for call in runtime.calls] == list(TRIBUNAL_AGENT_IDS) * 3
    for agent, prompt, context in runtime.calls:
        rounds = context["deliberation"]["previous_rounds"]
        phase = context["deliberation"]["phase"]
        assert len(rounds) == {"assessment": 0, "critique": 1, "revision": 2}[phase]
        for shared in rounds:
            assert set(shared["assessments"]) == set(TRIBUNAL_AGENT_IDS)
            for peer, assessment in shared["assessments"].items():
                assert assessment["reasoning"] in prompt
                assert "audit and rollback" in assessment["conditions"]
        assert context["temperature"] == DEFAULT_NODES[agent].temperature
        assert context["max_output_tokens"] == DEFAULT_NODES[agent].max_output_tokens
        assert context["require_real_model"] is True
        assert ("bellator_context_packet" in context) == (agent == BELLATOR)
        assert ("aeternum_data_packet" in context) == (agent == AETERNUM)
    assert votes[BELLATOR].vote.value == "DENY"
    assert orchestrator.complete
    assert len(orchestrator.transcript) == 9
    assert orchestrator.transcript[0]["vote"] == "APPROVE"
    assert orchestrator.transcript[6]["vote"] == "DENY"


@pytest.mark.parametrize("phase,turn_count", [("assessment", 3), ("critique", 6), ("revision", 9)])
@pytest.mark.parametrize("malformed", [False, True])
def test_failed_or_malformed_turn_blocks_majority_and_stops_later_rounds(phase, turn_count, malformed):
    runtime = DiscussionRuntime((BELLATOR, phase), malformed)
    orchestrator = VotingOrchestrator(DEFAULT_NODES, runtime)
    votes = orchestrator.cast_votes("Analyze a safe prototype", "test", "military")
    result = ConsensusEngine(ConsensusRules(), "military").calculate_result("Analyze a safe prototype", votes, "test")
    orchestrator.attach_audit(result)
    assert len(runtime.calls) == turn_count
    assert result.verdict == FinalVerdict.NO_CONSENSUS
    assert not result.quorum_met
    assert not result.deliberation_complete
    assert result.terminal_branch == "deliberation_incomplete"
    assert votes[BELLATOR].validation_errors
    assert not result.simulation


def test_real_tribunal_never_uses_mock_fallback_or_another_available_model(monkeypatch):
    monkeypatch.setattr(api, "health_check", lambda *a, **kw: {
        "status": "degraded", "models": ["other-model"], "base_url": "http://localhost:1",
        "model_remap_active": True, "model_remap_model": "other-model",
    })
    monkeypatch.setattr(api, "send_prompt", lambda *a, **kw: pytest.fail("Missing assigned model must not generate"))
    runtime = MstyRuntime(RuntimeConfig(mock_fallback_enabled=True, use_available_model_fallback=True))
    monkeypatch.setattr(runtime, "_fallback_response", lambda *a: pytest.fail("Tribunal must not simulate failure"))
    with pytest.raises(RuntimeError, match="Required model unavailable"):
        runtime.send_to_agent(RATIONALIS, "review", {"model": "assigned-model", "require_real_model": True})
    assert runtime.last_execution[RATIONALIS]["status"] == "failed"


@pytest.mark.parametrize("agent", TRIBUNAL_AGENT_IDS)
def test_assigned_parameters_reach_generation_payload_and_actual_model_is_recorded(monkeypatch, agent):
    node = replace(DEFAULT_NODES[agent], max_output_tokens=321)
    monkeypatch.setattr(api, "health_check", lambda *a, **kw: {"status": "ready", "models": [node.model], "base_url": "http://localhost:1", "active_backend": "test-provider"})
    sent = []
    monkeypatch.setattr(api, "backend_requests_post", lambda backend, payload: sent.append(payload) or {"response": response("Provider verified")})
    runtime = MstyRuntime(RuntimeConfig())
    runtime.send_to_agent(agent, "review", {"model": node.model, "temperature": node.temperature, "max_output_tokens": node.max_output_tokens, "require_real_model": True})
    assert sent[0]["options"] == {"temperature": node.temperature, "num_predict": 321}
    assert runtime.last_execution[agent] == {"status": "ready", "model": node.model, "backend": "test-provider"}


def test_context_model_overrides_provider_roster_and_records_alias(monkeypatch):
    actual = "TheBloke/deepseek-coder-33B-instruct-GGUF/deepseek-coder-33b-instruct.Q4_K_S.gguf"
    monkeypatch.setattr(api, "health_check", lambda *a, **kw: {"status": "ready", "models": [actual, "unrelated-model"], "base_url": "http://localhost:1", "resolved_required_models": {RATIONALIS: "unrelated-model"}})
    monkeypatch.setattr(api, "send_prompt", lambda model, *a, **kw: response(model))
    runtime = MstyRuntime(RuntimeConfig())
    runtime.send_to_agent(RATIONALIS, "review", {"model": "deepseek-coder-33b-instruct.Q4_K_S:latest", "require_real_model": True})
    assert runtime.last_execution[RATIONALIS]["model"] == actual


def test_empty_real_response_is_failure_even_when_fallback_is_enabled(monkeypatch):
    model = DEFAULT_NODES[RATIONALIS].model
    monkeypatch.setattr(api, "health_check", lambda *a, **kw: {"status": "ready", "models": [model]})
    monkeypatch.setattr(api, "send_prompt", lambda *a, **kw: "")
    with pytest.raises(RuntimeError, match="empty response"):
        MstyRuntime().send_to_agent(RATIONALIS, "review", {"require_real_model": True})


def test_explicit_mock_is_labeled_and_transcript_is_serializable():
    runtime = MstyRuntime(RuntimeConfig(backend="mock"))
    orchestrator = VotingOrchestrator(DEFAULT_NODES, runtime)
    votes = orchestrator.cast_votes("Analyze a prototype", "test", "military")
    result = ConsensusEngine(ConsensusRules(), "military").calculate_result("Analyze a prototype", votes, "test")
    orchestrator.attach_audit(result)
    payload = json.loads(json.dumps(result_to_dict(result)))
    assert payload["simulation"] is True
    assert payload["deliberation_complete"] is True
    assert result.reason.startswith("SIMULATION ONLY:")
    assert all(turn["model"] == "mock" and turn["backend"] == "mock" for turn in payload["deliberation_transcript"])


def test_tribunal_persists_transcript_and_actual_provenance(monkeypatch):
    records = []
    monkeypatch.setattr("core.tribunal.build_context_packet", lambda q: {})
    monkeypatch.setattr("core.tribunal.record_result", lambda result: records.append(result_to_dict(result)))
    monkeypatch.setattr("core.tribunal.log_decision_trace", lambda result: None)
    monkeypatch.setattr("core.tribunal.upsert_session_record", lambda record: records.append(record))
    result = Tribunal(DEFAULT_NODES, DiscussionRuntime()).deliberate("Analyze a prototype")
    assert result.deliberation_complete
    assert len(records) == 2
    assert all(len(record["deliberation_transcript"]) == 9 for record in records)


def test_verdict_export_preserves_exchange(tmp_path):
    from core.export.verdict import export_latest_verdict
    orchestrator = VotingOrchestrator(DEFAULT_NODES, DiscussionRuntime())
    votes = orchestrator.cast_votes("Analyze a prototype", "test", "military")
    result = ConsensusEngine(ConsensusRules(), "military").calculate_result("Analyze a prototype", votes, "test")
    orchestrator.attach_audit(result)
    exported = export_latest_verdict(result_to_dict(result), output_dir=tmp_path)
    from pathlib import Path
    payload = json.loads(Path(exported["json_path"]).read_text())
    markdown = Path(exported["markdown_path"]).read_text(encoding="utf-8")
    assert len(payload["deliberation_transcript"]) == 9
    assert "Round 2: critique" in markdown
    assert "Round 3: revision" in markdown
    assert "accepts peer audit condition" in markdown


@pytest.mark.parametrize("broken", [
    "CONFIDENCE: 1.2", "CONFIDENCE: nan", "CONFIDENCE: -0.9", "EVIDENCE_QUALITY: 5.0",
])
def test_out_of_range_or_invalid_vote_values_are_rejected(broken):
    from core.voting.parser import parse_vote
    field = broken.split(":", 1)[0]
    raw = response("Valid reason").replace("CONFIDENCE: 0.90" if field == "CONFIDENCE" else "EVIDENCE_QUALITY: 0.85", broken)
    assert parse_vote(raw, DEFAULT_NODES[BELLATOR], 0, "test-provider").validation_errors


@pytest.mark.parametrize("missing", ["CONFIDENCE: 0.90\n", "RATIONALE: Valid reason\n"])
def test_missing_required_vote_fields_are_rejected(missing):
    from core.voting.parser import parse_vote
    assert parse_vote(response("Valid reason").replace(missing, ""), DEFAULT_NODES[BELLATOR], 0, "test-provider").validation_errors
