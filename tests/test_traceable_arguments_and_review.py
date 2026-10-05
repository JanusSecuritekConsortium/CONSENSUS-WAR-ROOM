import json
from copy import deepcopy

import pytest

from config.names import AETERNUM, BELLATOR, RATIONALIS, TRIBUNAL_AGENT_IDS
from config.nodes import DEFAULT_NODES
from core.history import result_to_dict
from core.models import FinalVerdict, Vote, VoteValue
from core.voting.arguments import evidence_source_ids
from core.voting.engine import ConsensusEngine
from core.voting.orchestrator import VotingOrchestrator
from core.voting.parser import parse_vote
from core.voting.rules import ConsensusRules
from integrations.msty import api
from integrations.msty.runtime import MstyRuntime
from tests.argument_fixture import argument_fields


def raw_vote(agent=BELLATOR, context=None, value="APPROVE"):
    return (f"VOTE: {value}\nCONFIDENCE: 0.9\nEVIDENCE_QUALITY: 0.8\nCRITICAL_RISK: false\n"
            "RATIONALE: The proposal includes a reversible audit plan.\nRISKS: unverified assumptions\nCONDITIONS: audit\n"
            + argument_fields("A reversible audit plan supports the prototype", agent, context, value))


def replace_field(raw, field, value):
    return "\n".join(f"{field}: {value}" if line.startswith(field + ":") else line for line in raw.splitlines())


def parsed(raw, context=None):
    return parse_vote(raw, DEFAULT_NODES[BELLATOR], 0, "test", {"require_traceable_argument": True, **(context or {})})


def prior_context(phase="revision"):
    assessments = {}
    for role in TRIBUNAL_AGENT_IDS:
        vote = parse_vote(raw_vote(role), DEFAULT_NODES[role], 0, "test")
        assessments[role] = VotingOrchestrator._discussion_view(vote)
        assessments[role]["argument"]["claim"] = f"{role} requires a verified audit"
    return {"deliberation": {"phase": phase, "previous_rounds": [{"round": 1 if phase == "critique" else 2, "phase": "assessment" if phase == "critique" else "critique", "assessments": assessments}]}}


def test_complete_argument_is_retained_with_reference_identity():
    vote = parsed(raw_vote())
    assert not vote.validation_errors
    assert vote.argument["evidence"][0]["source"] == "proposal"
    assert vote.argument["strongest_objection"]
    assert not vote.review_required and not vote.peer_responses


@pytest.mark.parametrize("key", ["claim", "evidence", "assumptions", "strongest_objection", "change_condition"])
def test_missing_argument_components_are_rejected(key):
    raw = raw_vote()
    argument = parsed(raw).argument
    argument.pop(key)
    assert parsed(replace_field(raw, "ARGUMENT", json.dumps(argument))).validation_errors


def test_known_external_source_is_allowed_but_unprovided_and_peer_sources_are_rejected():
    context = {"memory_context": {"items": [{"source_url": "https://example.test/audit", "record_id": "audit-1"}]},
               "deliberation": {"previous_rounds": [{"assessments": {AETERNUM: {"source_url": "https://invented.test/peer"}}}]}}
    assert evidence_source_ids(context) == ["audit-1", "https://example.test/audit", "proposal"]
    raw = raw_vote()
    argument = parsed(raw).argument
    for source, valid in [("https://example.test/audit", True), ("https://invented.test/peer", False), ("unknown-1", False)]:
        argument["evidence"][0]["source"] = source
        assert bool(parsed(replace_field(raw, "ARGUMENT", json.dumps(argument)), context).validation_errors) != valid


def test_missing_evidence_is_allowed_only_when_quality_is_zero():
    raw = raw_vote()
    argument = parsed(raw).argument
    argument["evidence"] = []
    raw = replace_field(raw, "ARGUMENT", json.dumps(argument))
    assert parsed(raw).validation_errors
    assert not parsed(replace_field(raw, "EVIDENCE_QUALITY", "0")).validation_errors


@pytest.mark.parametrize("field,value", [("ARGUMENT", "[]"), ("PEER_RESPONSES", "[3]"), ("REVIEW_REQUIRED", "maybe"), ("UNRESOLVED_DISAGREEMENTS", "[3]")])
def test_invalid_structured_types_are_rejected(field, value):
    assert parsed(replace_field(raw_vote(), field, value)).validation_errors


def test_independent_assessment_cannot_invent_peer_responses():
    peers = [{"peer": AETERNUM, "round": 1, "claim": "unseen claim", "stance": "challenge", "reason": "unknown"}]
    assert parsed(replace_field(raw_vote(), "PEER_RESPONSES", json.dumps(peers))).validation_errors


@pytest.mark.parametrize("phase", ["critique", "revision"])
def test_both_peer_claims_are_required_but_agreement_is_valid(phase):
    context = prior_context(phase)
    raw = raw_vote(context=context)
    vote = parsed(raw, context)
    assert not vote.validation_errors
    assert {peer["peer"] for peer in vote.peer_responses} == {AETERNUM, RATIONALIS}
    assert all(peer["stance"] == "support" for peer in vote.peer_responses)
    assert vote.unresolved_disagreements == []
    assert parsed(replace_field(raw, "PEER_RESPONSES", json.dumps(vote.peer_responses[:1])), context).validation_errors
    peers = deepcopy(vote.peer_responses)
    peers[0]["claim"] = "The peer never made this claim"
    assert parsed(replace_field(raw, "PEER_RESPONSES", json.dumps(peers)), context).validation_errors


@pytest.mark.parametrize("change", ["vote", "risk", "review"])
def test_changed_vote_or_cleared_flag_needs_a_reason(change):
    context = prior_context()
    if change == "risk":
        context["deliberation"]["previous_rounds"][-1]["assessments"][BELLATOR]["critical_risk"] = True
    if change == "review":
        context["deliberation"]["previous_rounds"][-1]["assessments"][BELLATOR]["review_required"] = True
    raw = raw_vote(context=context, value="DENY" if change == "vote" else "APPROVE")
    raw = replace_field(raw, "VOTE_CHANGE_REASON", "")
    assert parsed(raw, context).validation_errors
    assert not parsed(replace_field(raw, "VOTE_CHANGE_REASON", "The peer supplied a verified audit or a concrete mitigation."), context).validation_errors


def test_review_request_needs_explanation_and_vote_values_are_exact():
    raw = replace_field(raw_vote(value="ABSTAIN"), "REVIEW_REQUIRED", "true")
    assert parsed(raw).validation_errors
    assert not parsed(replace_field(raw, "REVIEW_REASON", "Authorization for the security control is unresolved.")).validation_errors
    for value in ("DISAPPROVE", "CONDITIONAL_APPROVE", "ESCALATE"):
        assert parsed(raw_vote(value=value)).validation_errors


def test_invalid_peer_stance_is_rejected_without_crashing():
    context = prior_context()
    raw = raw_vote(context=context)
    peers = parsed(raw, context).peer_responses
    peers[0]["stance"] = []
    assert parsed(replace_field(raw, "PEER_RESPONSES", json.dumps(peers)), context).validation_errors


def test_malformed_argument_keeps_original_response_but_exposes_safe_structured_fields():
    raw = replace_field(raw_vote(), "ARGUMENT", '{"evidence":[3]}')
    vote = parsed(raw)
    assert vote.validation_errors and vote.raw_response == raw
    assert vote.argument == {} and vote.peer_responses == []


def votes():
    return {role: Vote(role, DEFAULT_NODES[role].role, VoteValue.APPROVE, .95, "Synthetic decision", evidence_quality=.8)
            for role in TRIBUNAL_AGENT_IDS}


def decide(items, **rules):
    return ConsensusEngine(ConsensusRules(**rules), "military").calculate_result("Security threat attack containment", items, "test")


def test_domain_critical_denial_blocks_two_approvals_even_below_confidence_threshold():
    items = votes()
    items[BELLATOR].vote = VoteValue.DENY
    items[BELLATOR].critical_risk = True
    items[BELLATOR].confidence = .2
    items[BELLATOR].risks = ["Unresolved containment failure"]
    result = decide(items)
    assert result.verdict == FinalVerdict.ESCALATE
    assert "critical_risk_reported:BELLATOR" in result.review_triggers
    assert "Unresolved containment failure" in result.reason


def test_out_of_domain_risk_does_not_automatically_override_expert_votes():
    items = votes()
    items[AETERNUM].critical_risk = True
    assert decide(items).verdict == FinalVerdict.APPROVE


def test_explicit_risk_review_opt_out_is_audited():
    items = votes()
    items[BELLATOR].critical_risk = True
    result = decide(items, high_risk_review=False)
    assert result.verdict == FinalVerdict.APPROVE
    assert "domain_critical_risk_review_disabled" in result.review_triggers


def test_explicit_review_request_blocks_majority_and_keeps_reason_separate_from_vote():
    items = votes()
    items[RATIONALIS].vote = VoteValue.ABSTAIN
    items[RATIONALIS].review_required = True
    items[RATIONALIS].review_reason = "Success criteria contradict the implementation constraint"
    result = decide(items)
    assert result.verdict == FinalVerdict.ESCALATE
    assert result.terminal_branch == "explicit_review_requested"
    assert items[RATIONALIS].vote == VoteValue.ABSTAIN
    assert items[RATIONALIS].review_reason in result.reason


def test_review_request_survives_classification_failure():
    items = votes()
    items[RATIONALIS].review_required = True
    items[RATIONALIS].review_reason = "The proposal needs defined success criteria"
    result = ConsensusEngine(ConsensusRules(), "military").calculate_result("xyzzy", items, "test")
    assert result.verdict == FinalVerdict.ESCALATE
    assert "review_requested:RATIONALIS" in result.review_triggers
    assert items[RATIONALIS].review_reason in result.reason


@pytest.mark.parametrize("domain_only", [True, False])
def test_evidence_gaps_block_majority_approval(domain_only):
    items = votes()
    if domain_only:
        items[BELLATOR].evidence_quality = .1
        items[BELLATOR].confidence = .2
    else:
        for vote in items.values():
            vote.evidence_quality = .1
    result = decide(items)
    assert result.verdict == FinalVerdict.NO_CONSENSUS
    assert result.terminal_branch == "evidence_gate_no_consensus"


def test_majority_denial_remains_denial_with_review_trigger():
    items = votes()
    for role in (BELLATOR, AETERNUM):
        items[role].vote = VoteValue.DENY
    items[BELLATOR].critical_risk = True
    result = decide(items)
    assert result.verdict == FinalVerdict.DENY
    assert "critical_risk_reported:BELLATOR" in result.review_triggers


def test_argument_failure_advances_to_another_real_model_without_simulation(monkeypatch):
    monkeypatch.setattr(api, "health_check", lambda *a, **kw: {"status": "ready", "models": ["preferred", "base"], "base_url": "http://localhost:1"})
    calls = []
    def send(model, *a, **kw):
        calls.append(model)
        return replace_field(raw_vote(), "ARGUMENT", "{}") if model == "preferred" else raw_vote()
    monkeypatch.setattr(api, "send_prompt", send)
    from config.runtime import RuntimeConfig
    runtime = MstyRuntime(RuntimeConfig(base_model="base"))
    monkeypatch.setattr(runtime, "_fallback_response", lambda *a: pytest.fail("Cannot fabricate arguments"))
    runtime.send_to_agent(BELLATOR, "Review prototype", {"model": "preferred", "require_real_model": True, "require_traceable_argument": True})
    assert calls == ["preferred", "base"]
    assert runtime.last_execution[BELLATOR]["model_attempts"][0]["error_type"] == "ValueError"


def test_serialization_keeps_argument_and_review_metadata():
    items = votes()
    items[BELLATOR] = parsed(raw_vote())
    result = decide(items)
    payload = result_to_dict(result)
    assert payload["votes"][BELLATOR]["argument"]["claim"]
    assert payload["votes"][BELLATOR]["unresolved_disagreements"] == []
