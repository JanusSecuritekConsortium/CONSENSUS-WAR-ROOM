from __future__ import annotations

from typing import Any, Dict

from core.models import Vote


def evidence_source_ids(context: Dict[str, Any]) -> list[str]:
    """Only supplied source identities count; peer statements are not new evidence."""
    sources = {"proposal"}
    keys = {"id", "source", "source_id", "record_id", "url", "source_url", "source_path", "source_urls", "source_paths", "document_id", "proposal_id", "decision_id", "path"}
    def collect(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"deliberation", "system_prompt", "evidence_source_ids"}:
                    continue
                if key in keys and isinstance(item, str) and item.strip():
                    sources.add(item)
                if key in keys and isinstance(item, list):
                    sources.update(value for value in item if isinstance(value, str) and value.strip())
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)
    collect(context)
    return sorted(sources)


def validate_argument(vote: Vote, context: Dict[str, Any]) -> list[str]:
    errors: list[str] = []
    argument = vote.argument
    for key in ("claim", "strongest_objection", "change_condition"):
        if not isinstance(argument.get(key), str) or not argument[key].strip():
            errors.append(f"missing argument.{key}")
    assumptions = argument.get("assumptions")
    if not isinstance(assumptions, list) or any(not isinstance(item, str) or not item.strip() for item in assumptions):
        errors.append("invalid argument.assumptions")
    evidence = argument.get("evidence")
    if not isinstance(evidence, list):
        errors.append("invalid argument.evidence")
    else:
        allowed = set(evidence_source_ids(context))
        for item in evidence:
            if not isinstance(item, dict) or not isinstance(item.get("detail"), str) or not item["detail"].strip():
                errors.append("invalid argument evidence entry")
            elif not isinstance(item.get("source"), str) or item["source"] not in allowed:
                errors.append("argument evidence source not supplied")
        if not evidence and vote.evidence_quality > 0:
            errors.append("positive evidence quality without supporting evidence")
    if vote.review_required and not vote.review_reason.strip():
        errors.append("review_required needs review_reason")

    deliberation = context.get("deliberation", {})
    phase = deliberation.get("phase", "assessment")
    rounds = deliberation.get("previous_rounds", [])
    if phase == "assessment":
        if vote.peer_responses:
            errors.append("initial assessment cannot reference unseen peers")
        return errors
    if not rounds:
        return [*errors, "peer round unavailable"]
    latest = rounds[-1]
    peers = set(latest.get("assessments", {})) - {vote.node_key}
    addressed = set()
    for response in vote.peer_responses:
        peer = response.get("peer")
        target_round = response.get("round")
        if not isinstance(peer, str) or not isinstance(target_round, int) or isinstance(target_round, bool):
            errors.append("invalid peer response identity or round")
            continue
        target = next((item for item in rounds if item.get("round") == target_round), {})
        claim = target.get("assessments", {}).get(peer, {}).get("argument", {}).get("claim")
        if peer not in peers or not claim or response.get("claim") != claim:
            errors.append("peer response must quote a supplied peer claim")
        if not isinstance(response.get("stance"), str) or response["stance"] not in {"support", "challenge", "accept", "reject"}:
            errors.append("invalid peer response stance")
        if not isinstance(response.get("reason"), str) or not response["reason"].strip():
            errors.append("peer response needs reason")
        if target_round == latest.get("round"):
            addressed.add(peer)
    if addressed != peers:
        errors.append("must address each peer in the latest completed round")
    previous = latest.get("assessments", {}).get(vote.node_key, {})
    changed = previous.get("vote") != vote.vote.value
    cleared_risk = previous.get("critical_risk") and not vote.critical_risk
    cleared_review = previous.get("review_required") and not vote.review_required
    if (changed or cleared_risk or cleared_review) and not vote.vote_change_reason.strip():
        errors.append("decision change needs vote_change_reason")
    return errors
