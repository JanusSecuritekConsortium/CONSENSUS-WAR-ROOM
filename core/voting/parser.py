from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from core.models import NodeIdentity, Vote, VoteValue


def parse_vote(raw: str, node: NodeIdentity, elapsed: float, backend_name: str, context: Optional[Dict[str, Any]] = None) -> Vote:
    vote = VoteValue.ABSTAIN
    confidence = 0.5
    evidence_quality: Optional[float] = None
    critical_risk: Optional[bool] = None
    reasoning_lines: List[str] = []
    risks: List[str] = []
    conditions: List[str] = []
    validation_errors: List[str] = []
    active_field: Optional[str] = None
    saw_vote = False
    saw_confidence = False
    structured: Dict[str, Any] = {}
    json_fields = {"ARGUMENT": dict, "PEER_RESPONSES": list, "UNRESOLVED_DISAGREEMENTS": list}

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        match = re.match(
            r"^(VOTE|RESULT|CONFIDENCE|EVIDENCE_QUALITY|CRITICAL_RISK|RATIONALE|REASONING|RISKS|CONDITIONS|ARGUMENT|PEER_RESPONSES|REVIEW_REQUIRED|REVIEW_REASON|VOTE_CHANGE_REASON|UNRESOLVED_DISAGREEMENTS)\s*:\s*(.*)$",
            stripped,
            re.I,
        )
        if match:
            active_field = match.group(1).upper()
            value = match.group(2).strip()
        else:
            value = stripped

        if active_field in {"VOTE", "RESULT"}:
            saw_vote = True
            upper = value.upper()
            for candidate in (VoteValue.APPROVE, VoteValue.DENY, VoteValue.ABSTAIN):
                if candidate.value == upper:
                    vote = candidate
                    break
            else:
                validation_errors.append(f"invalid or arbiter-only vote result: {value}")
        elif active_field == "CONFIDENCE":
            saw_confidence = True
            parsed_confidence = parse_unit_float(value)
            if parsed_confidence is None:
                validation_errors.append(f"invalid confidence: {value}")
            else:
                confidence = parsed_confidence
        elif active_field == "EVIDENCE_QUALITY":
            evidence_quality = parse_unit_float(value)
            if evidence_quality is None:
                validation_errors.append(f"invalid evidence_quality: {value}")
        elif active_field == "CRITICAL_RISK":
            critical_risk = parse_bool(value)
            if critical_risk is None:
                validation_errors.append(f"invalid critical_risk: {value}")
        elif active_field in {"RATIONALE", "REASONING"}:
            reasoning_lines.append(value)
        elif active_field == "RISKS":
            risks.extend(split_list(value))
        elif active_field == "CONDITIONS":
            conditions.extend(split_list(value))
        elif active_field in json_fields:
            try:
                parsed = json.loads(value)
                if not isinstance(parsed, json_fields[active_field]):
                    raise ValueError("wrong JSON type")
                if active_field == "PEER_RESPONSES" and any(not isinstance(item, dict) for item in parsed):
                    raise ValueError("peer responses must be objects")
                if active_field == "UNRESOLVED_DISAGREEMENTS" and any(not isinstance(item, str) or not item.strip() for item in parsed):
                    raise ValueError("disagreements must be strings")
                structured[active_field] = parsed
            except (ValueError, TypeError):
                validation_errors.append(f"invalid {active_field.lower()} JSON")
        elif active_field == "REVIEW_REQUIRED":
            parsed = parse_bool(value)
            if parsed is None:
                validation_errors.append("invalid review_required")
            else:
                structured[active_field] = parsed
        elif active_field in {"REVIEW_REASON", "VOTE_CHANGE_REASON"}:
            structured[active_field] = value

    if not reasoning_lines:
        validation_errors.append("missing rationale")
        reasoning_lines = ["No explicit reasoning was returned by the model."]

    if not saw_vote:
        validation_errors.append("missing vote result")
    if not saw_confidence:
        validation_errors.append("missing confidence")
    if evidence_quality is None:
        validation_errors.append("missing evidence_quality")
    if critical_risk is None:
        validation_errors.append("missing critical_risk")

    argument_fields = {
        "argument": structured.get("ARGUMENT", {}), "peer_responses": structured.get("PEER_RESPONSES", []),
        "review_required": structured.get("REVIEW_REQUIRED", False), "review_reason": structured.get("REVIEW_REASON", ""),
        "vote_change_reason": structured.get("VOTE_CHANGE_REASON", ""), "unresolved_disagreements": structured.get("UNRESOLVED_DISAGREEMENTS", []),
    }
    if (context or {}).get("require_traceable_argument"):
        from core.voting.arguments import validate_argument
        for field in ("ARGUMENT", "PEER_RESPONSES", "REVIEW_REQUIRED", "REVIEW_REASON", "VOTE_CHANGE_REASON", "UNRESOLVED_DISAGREEMENTS"):
            if field not in structured:
                validation_errors.append(f"missing {field.lower()}")
        draft = Vote(node.codename, node.role, vote, confidence, " ".join(reasoning_lines), evidence_quality=evidence_quality or 0.0, critical_risk=bool(critical_risk), **argument_fields)
        validation_errors.extend(validate_argument(draft, context or {}))
    if validation_errors:
        return Vote(
            node_key=node.codename,
            role=node.role,
            vote=VoteValue.ABSTAIN,
            confidence=0.0,
            reasoning="Malformed vote coerced to ABSTAIN: " + "; ".join(validation_errors),
            evidence_quality=0.0,
            critical_risk=False,
            validation_errors=validation_errors,
            risks=risks,
            conditions=conditions,
            model=node.model if backend_name != "mock" else "mock",
            response_time=elapsed,
            raw_response=raw,
            **{**argument_fields, "argument": {}, "peer_responses": [], "unresolved_disagreements": []},
        )

    return Vote(
        node_key=node.codename,
        role=node.role,
        vote=vote,
        confidence=confidence,
        reasoning=" ".join(reasoning_lines).strip(),
        evidence_quality=evidence_quality,
        critical_risk=critical_risk,
        risks=risks,
        conditions=conditions,
        model=node.model if backend_name != "mock" else "mock",
        response_time=elapsed,
        raw_response=raw,
        **argument_fields,
    )


def split_list(value: str) -> List[str]:
    return [
        item.strip(" -;\t")
        for item in re.split(r",|;", value)
        if item.strip(" -;\t")
    ]


def parse_unit_float(value: str) -> Optional[float]:
    found = re.search(r"(?<![\w.])([+-]?(?:\d+(?:\.\d+)?|\.\d+))\s*(%)?(?![\w.])", value)
    if not found:
        return None
    token = found.group(1)
    parsed = float(token) / 100.0 if found.group(2) else float(token)
    if parsed < 0.0 or parsed > 1.0:
        return None
    return parsed


def parse_bool(value: str) -> Optional[bool]:
    normalized = value.strip().lower()
    if normalized in {"true", "yes", "y", "1", "critical", "present"}:
        return True
    if normalized in {"false", "no", "n", "0", "none", "absent"}:
        return False
    return None
