"""Derive reviewable next steps from public fields, without scheduling actions."""
from core.models import FinalVerdict, TribunalResult
from core.public_text import public_text


def unresolved_next_steps(result: TribunalResult) -> list[str]:
    if result.verdict not in {FinalVerdict.NO_CONSENSUS, FinalVerdict.ESCALATE, FinalVerdict.CAUTION}:
        return []
    steps = []
    if not result.deliberation_complete and any(v.validation_errors for v in result.votes.values()):
        steps.append("Resolve the failed model response in Diagnostics, then rerun the complete tribunal.")
    for key, vote in result.votes.items():
        if vote.validation_errors:
            continue
        for audit in vote.evidence_audit:
            if audit.get("support") == "contradicts" or audit.get("freshness") in {"stale", "unknown"}:
                steps.append(f"{key}: Obtain a current passage supporting the claim and review the conflicting evidence.")
        if vote.review_required and vote.review_reason:
            steps.append(f"{key}: Request human review: {public_text(vote.review_reason)}")
        condition = public_text((vote.argument or {}).get("change_condition"))
        if condition:
            steps.append(f"{key}: Before reassessment: {condition}")
        for objection in vote.unresolved_disagreements:
            steps.append(f"{key}: Resolve objection: {public_text(objection)}")
    if not steps:
        steps.append("Clarify the proposal and supply the missing evidence, then request reassessment.")
    return list(dict.fromkeys(steps))[:12]
