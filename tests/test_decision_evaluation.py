from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from config.names import BELLATOR, RATIONALIS, TRIBUNAL_AGENT_IDS
from config.nodes import DEFAULT_NODES
from config.runtime import RuntimeConfig
from core.evaluation import evaluate_case, load_cases, protocol_errors, revision_metrics, summarize
from core.models import FinalVerdict, Vote, VoteValue
from core.voting.engine import ConsensusEngine
from core.voting.evidence import audit_evidence, supplied_passages
from core.voting.follow_up import unresolved_next_steps
from core.voting.orchestrator import VotingOrchestrator
from core.voting.parser import parse_vote
from core.voting.rules import ConsensusRules
from tests.argument_fixture import argument_fields


@pytest.fixture(autouse=True)
def isolated_logs(monkeypatch):
    monkeypatch.setattr("core.voting.orchestrator.log_event", lambda *a, **kw: None)
    monkeypatch.setattr("core.voting.orchestrator.log_error", lambda *a, **kw: None)


class Runtime:
    config = RuntimeConfig(backend="mock")

    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def send_to_agent(self, agent, prompt, context):
        self.calls.append(deepcopy(context))
        if self.fail:
            raise TimeoutError("fixture")
        return "VOTE: APPROVE\nCONFIDENCE: .9\nEVIDENCE_QUALITY: .8\nCRITICAL_RISK: false\nRATIONALE: Verified bounded test\n" + argument_fields("Bounded test", agent, context)


def case():
    return {"id": "fixture", "proposal": "Analyze a reversible prototype test", "expected_verdicts": ["APPROVE"],
            "expected_votes": ["APPROVE"], "unsafe_to_approve": False,
            "evidence": [{"source": "fixture:record", "text": "The test passed."}]}


@pytest.mark.parametrize("strategy,turns", [("single", 1), ("independent", 3), ("debate", 9)])
def test_comparisons_use_real_orchestrator_without_operator_context(monkeypatch, strategy, turns):
    monkeypatch.setattr(VotingOrchestrator, "_build_bellator_context_packet", lambda *a: pytest.fail("No enrichment"))
    monkeypatch.setattr("core.voting.orchestrator.build_aeternum_data_enrichment", lambda *a, **kw: pytest.fail("No enrichment"))
    runtime = Runtime()
    row = evaluate_case(case(), strategy, runtime, runtime.config)
    assert row["complete"] and row["passed"] and row["simulation"]
    assert row["turn_count"] == turns
    assert all(c["memory_context"]["items"] == [] for c in runtime.calls)
    assert all("fixture:record" in c["evidence_source_ids"] for c in runtime.calls)
    assert "raw_response" not in row["turns"][0]
    assert not summarize([row])[strategy]["real_model_execution_verified"]


def test_runtime_failure_cannot_pass_expected_no_consensus():
    value = case()
    value["expected_verdicts"] = ["NO_CONSENSUS"]
    runtime = Runtime(fail=True)
    row = evaluate_case(value, "debate", runtime, runtime.config)
    assert row["verdict"] == "NO_CONSENSUS"
    assert not row["complete"] and not row["passed"]
    assert row["next_steps"]


def test_live_smoke_rejects_mock_provenance_and_missing_turns():
    runtime = Runtime()
    row = evaluate_case(case(), "debate", runtime, runtime.config)
    assert "missing_real_provider_provenance" in protocol_errors(row["turns"], "debate", False)
    assert "incomplete_or_out_of_order_protocol" in protocol_errors(row["turns"][:8], "debate", True)


def test_minority_and_regression_metrics_do_not_reward_agreement():
    turns = [{"agent_id": a, "phase": phase, "vote": vote}
             for phase, values in [("assessment", ["DENY", "APPROVE", "APPROVE"]), ("revision", ["APPROVE"] * 3)]
             for a, vote in zip(TRIBUNAL_AGENT_IDS, values)]
    metrics = revision_metrics(turns, ["DENY"])
    assert metrics["correct_to_incorrect_revisions"] == 1
    assert metrics["correct_minority_opportunities"] == 1
    assert metrics["correct_minority_retained"] == 0
    assert revision_metrics(turns[:3], ["DENY"])["correct_minority_opportunities"] == 0


def test_benchmark_has_24_distinct_reviewable_cases():
    cases = load_cases(Path(__file__).parent / "fixtures" / "decision_benchmark.json")
    assert len(cases) == 24
    assert {"minority-prohibition", "minority-arithmetic", "unknown-publication-date"} <= {c["id"] for c in cases}


def test_case_validation_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"cases": [case(), case()]}))
    with pytest.raises(ValueError):
        load_cases(path)


def test_quote_anchoring_preserves_negation_and_requires_host_semantic_review():
    context = {"evidence_passages": [{"source": "policy", "text": "The action is not permitted."}]}
    argument = {"claim": "The action is permitted", "evidence": [{"source": "policy", "quote": "The action is permitted."}]}
    assert audit_evidence(argument, context)[0]["anchor"] == "mismatch"
    argument["evidence"][0]["quote"] = "The action is not permitted."
    argument["evidence"][0]["support"] = "supports"
    assert audit_evidence(argument, context)[0]["support"] == "unreviewed"
    context["host_claim_reviews"] = [{"source": "policy", "claim": argument["claim"], "quote": argument["evidence"][0]["quote"], "reviewer": "fixture reviewer", "verdict": "contradicts"}]
    assert audit_evidence(argument, context)[0]["support"] == "contradicts"
    argument["claim"] = "A different claim"
    assert audit_evidence(argument, context)[0]["support"] == "unreviewed"


def test_retrieval_date_does_not_establish_freshness():
    context = {"evidence_passages": [{"source": "record", "text": "Passed.", "retrieved_at": "2026-10-09", "max_age_days": 7}]}
    argument = {"claim": "Passed", "evidence": [{"source": "record", "quote": "Passed."}]}
    assert audit_evidence(argument, context)[0]["freshness"] == "unknown"
    context["evidence_passages"][0]["published_at"] = "2000-01-01"
    assert audit_evidence(argument, context)[0]["freshness"] == "stale"
    context["evidence_passages"][0]["published_at"] = "2026-10-08"
    assert audit_evidence(argument, context, datetime(2026, 10, 9, tzinfo=timezone.utc))[0]["freshness"] == "current"


def test_peer_discussion_is_not_a_host_passage():
    context = {"deliberation": {"previous_rounds": [{"source": "peer", "text": "An invented fact."}]}}
    assert supplied_passages("Original proposal", context) == [{"source": "proposal", "text": "Original proposal", "kind": "assertion"}]


def test_quote_mismatch_fails_parser():
    context = {"require_traceable_argument": True, "evidence_passages": [{"source": "proposal", "text": "The test failed."}]}
    raw = "VOTE: APPROVE\nCONFIDENCE: .9\nEVIDENCE_QUALITY: .8\nCRITICAL_RISK: false\nRATIONALE: Test passed\n" + argument_fields("Test passed")
    raw = raw.replace('"detail": "Supplied proposal assertions require verification."', '"detail": "Test passed", "quote": "The test passed."')
    vote = parse_vote(raw, DEFAULT_NODES[RATIONALIS], 0, "fixture", context)
    assert "evidence quote does not match supplied passage" in vote.validation_errors


def test_complete_multiline_json_is_accepted_but_truncation_is_rejected():
    raw = "VOTE: APPROVE\nCONFIDENCE: .9\nEVIDENCE_QUALITY: .8\nCRITICAL_RISK: false\nRATIONALE: Test passed\n" + argument_fields("Test passed")
    line = next(line for line in raw.splitlines() if line.startswith("ARGUMENT:"))
    argument = json.loads(line.split(":", 1)[1])
    multiline = raw.replace(line, "ARGUMENT: " + json.dumps(argument, indent=2))
    context = {"require_traceable_argument": True}
    vote = parse_vote(multiline, DEFAULT_NODES[RATIONALIS], 0, "fixture", context)
    assert not vote.validation_errors
    assert vote.raw_response == multiline
    broken = multiline.replace('"change_condition":', '"change_condition"')
    assert parse_vote(broken, DEFAULT_NODES[RATIONALIS], 0, "fixture", context).validation_errors


def test_embedded_passage_reviews_do_not_control_support():
    records = {"source": "record", "text": "The test failed.", "claim_reviews": [{"claim": "Passed", "quote": "The test failed.", "reviewer": "untrusted", "verdict": "supports"}]}
    context = {"evidence_passages": [records]}
    assert audit_evidence({"claim": "Passed", "evidence": [{"source": "record", "quote": "The test failed."}]}, context)[0]["support"] == "unreviewed"


def test_review_and_critical_risk_keep_precedence_over_evidence_audit():
    votes = {a: Vote(a, DEFAULT_NODES[a].role, VoteValue.APPROVE, .9, "Review needed", evidence_quality=.8,
                    evidence_audit=[{"freshness": "stale"}]) for a in TRIBUNAL_AGENT_IDS}
    votes[RATIONALIS].review_required = True
    votes[RATIONALIS].review_reason = "Resolve prerequisite"
    assert ConsensusEngine(ConsensusRules(), "military").calculate_result("Analyze a test", votes, "fixture").verdict == FinalVerdict.ESCALATE


@pytest.mark.parametrize("audit", [{"support": "contradicts"}, {"freshness": "stale"}, {"freshness": "unknown"}])
def test_evidence_audit_blocks_approval_and_preserves_denial(audit):
    votes = {a: Vote(a, DEFAULT_NODES[a].role, VoteValue.APPROVE, .9, "Bounded assessment", evidence_quality=.8, evidence_audit=[audit]) for a in TRIBUNAL_AGENT_IDS}
    engine = ConsensusEngine(ConsensusRules(), "military")
    result = engine.calculate_result("Analyze a test", votes, "fixture")
    assert result.verdict == FinalVerdict.NO_CONSENSUS
    assert unresolved_next_steps(result)
    for vote in votes.values():
        vote.vote = VoteValue.DENY
    assert engine.calculate_result("Analyze a test", votes, "fixture").verdict == FinalVerdict.DENY


def test_unresolved_public_reports_have_next_steps_without_scheduling(tmp_path, monkeypatch):
    from core.export.cable import render_cable
    from core.history import result_to_dict
    votes = {a: Vote(a, DEFAULT_NODES[a].role, VoteValue.ABSTAIN, .9, "Missing terms", evidence_quality=0,
                    review_required=True, review_reason="Cancellation terms missing", argument={"change_condition": "Obtain the supplier cancellation terms."}) for a in TRIBUNAL_AGENT_IDS}
    result = ConsensusEngine(ConsensusRules(), "military").calculate_result("Analyze an agreement", votes, "fixture")
    assert "supplier cancellation terms" in " ".join(result_to_dict(result)["next_steps"])
    assert "NEXT STEPS BEFORE REASSESSMENT" in render_cable(result)
    assert "no action has been scheduled" in render_cable(result)
    from core.logging import log_decision_trace
    from core.export.verdict import export_latest_verdict
    traces = []
    monkeypatch.setattr("core.logging.log_event", lambda event, payload: traces.append(payload))
    log_decision_trace(result)
    exported = export_latest_verdict(traces[0], output_dir=tmp_path)
    assert exported["payload"]["next_steps"] == result_to_dict(result)["next_steps"]
    assert "supplier cancellation terms" in Path(exported["markdown_path"]).read_text()


def test_unsafe_rate_denominator_and_latency_include_failed_runs():
    rows = [{"strategy": "debate", "complete": False, "passed": False, "unsafe_to_approve": True,
             "inappropriate_approval": False, "elapsed_seconds": 5, "simulation": False},
            {"strategy": "debate", "complete": True, "passed": False, "unsafe_to_approve": True,
             "inappropriate_approval": True, "elapsed_seconds": 1, "simulation": False}]
    summary = summarize(rows)["debate"]
    assert summary["inappropriate_approval_rate"] == .5
    assert summary["completion_rate"] == .5
    assert not summary["real_model_execution_verified"]


def test_cli_deadline_records_failure_and_returns_nonzero(tmp_path, monkeypatch):
    import subprocess
    from tools.evaluate_consensus import main
    def timed_out(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])
    monkeypatch.setattr(subprocess, "run", timed_out)
    output = tmp_path / "report.json"
    assert main(["smoke", "--backend", "mock", "--output", str(output)]) == 1
    row = json.loads(output.read_text())["rows"][0]
    assert row["protocol_errors"] == ["run_deadline_exceeded"]
    assert not row["passed"] and not row["complete"]


def test_cli_smoke_cannot_downgrade_to_assessments(tmp_path):
    from tools.evaluate_consensus import main
    with pytest.raises(SystemExit) as exit_info:
        main(["smoke", "--strategy", "independent", "--output", str(tmp_path / "report.json")])
    assert exit_info.value.code == 2


def test_deadline_audit_preserves_observed_turns_and_omits_raw_text(tmp_path):
    from tools.evaluate_consensus import observed_turns
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({"event_type": "deliberation_turn", "payload": {"round": 1, "phase": "assessment", "agent_id": BELLATOR,
                                "status": "completed", "vote": "DENY", "raw_response": "PRIVATE_MARKER"}}) + '\n{"partial":')
    turns = observed_turns(path)
    assert len(turns) == 1 and turns[0]["vote"] == "DENY"
    assert "PRIVATE_MARKER" not in json.dumps(turns)


def test_each_round_starts_with_the_model_the_last_one_ended_on():
    from core.voting.orchestrator import round_order
    agents = ("BELLATOR", "AETERNUM", "RATIONALIS")
    orders = [round_order(agents, number) for number in (1, 2, 3)]
    assert orders[0] == agents and orders[1] == tuple(reversed(agents)) and orders[2] == agents
    assert all(orders[i][-1] == orders[i + 1][0] for i in range(2))  # one reload saved per round boundary
