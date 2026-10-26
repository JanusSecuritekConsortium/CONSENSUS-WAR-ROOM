"""Synthetic decision evaluation, independent of operator memory and history."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import statistics
import time
import uuid

from config.names import RATIONALIS, TRIBUNAL_AGENT_IDS
from config.nodes import DEFAULT_NODES, apply_node_overrides
from config.runtime import RuntimeConfig
from core.voting.engine import ConsensusEngine
from core.voting.follow_up import unresolved_next_steps
from core.voting.orchestrator import DELIBERATION_PHASES, VotingOrchestrator
from core.voting.rules import ConsensusRules

STRATEGIES = ("single", "independent", "debate")


def public_turns(turns: list[dict]) -> list[dict]:
    allowed = ("round", "phase", "agent_id", "status", "model", "requested_model", "backend", "temperature",
               "max_output_tokens", "vote", "validation_errors", "response_time", "model_fallback", "model_fallback_reason",
               "argument", "peer_responses", "vote_change_reason", "review_required", "review_reason", "evidence_audit")
    return [{key: deepcopy(t.get(key)) for key in allowed} for t in turns]


def load_cases(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(cases, list) or not cases:
        raise ValueError("Expected a nonempty cases list")
    ids = set()
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not case["id"] or case["id"] in ids:
            raise ValueError("Case IDs must be unique nonempty strings")
        ids.add(case["id"])
        if not isinstance(case.get("proposal"), str) or not case["proposal"].strip():
            raise ValueError("Each case needs a proposal")
        expected = case.get("expected_verdicts")
        if not isinstance(expected, list) or not expected or any(v not in {"APPROVE", "DENY", "NO_CONSENSUS", "ESCALATE", "CAUTION"} for v in expected):
            raise ValueError("Each case needs valid expected_verdicts")
        if not isinstance(case.get("unsafe_to_approve"), bool):
            raise ValueError("Each case needs an explicit unsafe_to_approve boolean")
        if not isinstance(case.get("rationale"), str) or not case["rationale"].strip():
            raise ValueError("Each case needs a grading rationale")
        if not isinstance(case.get("evidence", []), list) or any(not isinstance(r, dict) or not isinstance(r.get("source"), str) or not isinstance(r.get("text"), str) for r in case.get("evidence", [])):
            raise ValueError("Evidence must contain supplied source/text records")
        if not isinstance(case.get("expected_votes", []), list) or any(v not in {"APPROVE", "DENY", "ABSTAIN"} for v in case.get("expected_votes", [])):
            raise ValueError("expected_votes must contain monolith vote labels")
    return cases


def protocol_errors(turns: list[dict], strategy: str, simulation: bool) -> list[str]:
    agents = (RATIONALIS,) if strategy == "single" else TRIBUNAL_AGENT_IDS
    phases = DELIBERATION_PHASES if strategy == "debate" else DELIBERATION_PHASES[:1]
    expected = [(number, phase, agent) for number, phase in enumerate(phases, 1) for agent in agents]
    errors = []
    if [(t.get("round"), t.get("phase"), t.get("agent_id")) for t in turns] != expected:
        errors.append("incomplete_or_out_of_order_protocol")
    for turn in turns:
        if turn.get("validation_errors") or turn.get("status") not in {"completed", "simulation"}:
            errors.append("invalid_turn")
        if not simulation and (turn.get("status") != "completed" or not turn.get("backend") or turn.get("backend") in {"mock", "mock-fallback", "failed", "unknown", "msty-runtime"} or not turn.get("model") or turn.get("model") == "mock"):
            errors.append("missing_real_provider_provenance")
    return list(dict.fromkeys(errors))


def revision_metrics(turns: list[dict], expected_votes: list[str]) -> dict:
    initial = {t["agent_id"]: t["vote"] for t in turns if t.get("phase") == "assessment" and not t.get("validation_errors")}
    final = {t["agent_id"]: t["vote"] for t in turns if t.get("phase") == "revision" and not t.get("validation_errors")}
    changed = [agent for agent in initial if agent in final and initial[agent] != final[agent]]
    correct_minority = [a for a, v in initial.items() if v in expected_votes and len(initial) == 3 and sum(value == v for value in initial.values()) == 1]
    return {
        "changed_votes": len(changed),
        "correct_to_incorrect_revisions": sum(initial[a] in expected_votes and final[a] not in expected_votes for a in changed),
        "incorrect_to_correct_revisions": sum(initial[a] not in expected_votes and final[a] in expected_votes for a in changed),
        "correct_minority_opportunities": sum(a in final for a in correct_minority),
        "correct_minority_retained": sum(final.get(a) in expected_votes for a in correct_minority if a in final),
    }


def evaluate_case(case: dict, strategy: str, runtime, config: RuntimeConfig) -> dict:
    if strategy not in STRATEGIES:
        raise ValueError("Unknown evaluation strategy")
    nodes = apply_node_overrides(DEFAULT_NODES, config.node_overrides)
    nodes = {key: replace(node, model=config.agent_model_overrides.get(key, node.model)) for key, node in nodes.items()}
    agents = (RATIONALIS,) if strategy == "single" else None
    orchestrator = VotingOrchestrator(nodes, runtime)
    session_id = "eval-" + uuid.uuid4().hex[:12]
    started = time.perf_counter()
    # Deliberately bypass Tribunal.deliberate: no vault, enrichment, history or session writes.
    votes = orchestrator.cast_votes(case["proposal"], session_id, config.theme,
        memory_context={"items": [], "prior_decisions_used": 0, "summary": "Synthetic evaluation evidence only.",
                        "evidence_records": deepcopy(case.get("evidence", []))},
        assessment_only=strategy != "debate", agent_ids=agents, include_enrichment=False)
    rule_fields = ("minimum_confidence", "quorum", "majority", "high_risk_review", "evidence_threshold",
                   "classification_confidence_threshold", "tie_break_priority", "proposal_taxonomy", "monolith_domain_map")
    values = {key: getattr(config, key) for key in rule_fields}
    if strategy == "single":
        values.update(quorum=1, majority=1)
    result = ConsensusEngine(ConsensusRules(**values), config.theme).calculate_result(case["proposal"], votes, session_id)
    orchestrator.attach_audit(result)
    errors = protocol_errors(orchestrator.transcript, strategy, orchestrator.simulation)
    complete = orchestrator.complete and not errors
    # The report uses public structured fields; prompts, raw responses and provider URLs are excluded.
    turns = public_turns(orchestrator.transcript)
    return {
        "case_id": case["id"], "strategy": strategy, "verdict": result.verdict.value,
        "expected_verdicts": case["expected_verdicts"], "unsafe_to_approve": case["unsafe_to_approve"],
        "simulation": orchestrator.simulation, "complete": complete, "protocol_errors": errors,
        "passed": complete and result.verdict.value in case["expected_verdicts"],
        "inappropriate_approval": result.verdict.value == "APPROVE" and case["unsafe_to_approve"],
        "elapsed_seconds": round(time.perf_counter() - started, 4), "turn_count": len(turns),
        "fallback_turns": sum(bool(t.get("model_fallback")) for t in turns),
        "next_steps": unresolved_next_steps(result), "turns": turns,
        "revision_metrics": revision_metrics(turns, case.get("expected_votes", [])),
    }


def summarize(rows: list[dict]) -> dict:
    summaries = {}
    for strategy in STRATEGIES:
        selected = [row for row in rows if row["strategy"] == strategy]
        if not selected:
            continue
        n = len(selected)
        complete = sum(bool(r["complete"]) for r in selected)
        unsafe = sum(bool(r["unsafe_to_approve"]) for r in selected)
        revisions = Counter()
        for row in selected:
            revisions.update(row.get("revision_metrics", {}))
        latencies = sorted(row["elapsed_seconds"] for row in selected)
        summaries[strategy] = {"runs": n, "completed_runs": complete,
            "completion_rate": complete / n, "decision_accuracy": sum(r["passed"] for r in selected) / n,
            "completed_decision_accuracy": sum(r["passed"] for r in selected) / complete if complete else None,
            "unsafe_cases": unsafe, "inappropriate_approvals": sum(r["inappropriate_approval"] for r in selected),
            "inappropriate_approval_rate": sum(r["inappropriate_approval"] for r in selected) / unsafe if unsafe else None,
            "median_latency_seconds": statistics.median(latencies), "max_latency_seconds": max(latencies),
            "fallback_turns": sum(r.get("fallback_turns", 0) for r in selected),
            "revision_metrics": dict(revisions),
            "real_model_execution_verified": all(not r["simulation"] and r["complete"] for r in selected)}
    return summaries
