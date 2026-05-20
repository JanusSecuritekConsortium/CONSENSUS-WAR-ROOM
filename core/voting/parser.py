from __future__ import annotations

import re
from typing import List, Optional

from core.models import NodeIdentity, Vote, VoteValue


def parse_vote(raw: str, node: NodeIdentity, elapsed: float, backend_name: str) -> Vote:
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

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        match = re.match(
            r"^(VOTE|RESULT|CONFIDENCE|EVIDENCE_QUALITY|CRITICAL_RISK|RATIONALE|REASONING|RISKS|CONDITIONS)\s*:\s*(.*)$",
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
                if candidate.value in upper:
                    vote = candidate
                    break
            else:
                validation_errors.append(f"invalid or arbiter-only vote result: {value}")
        elif active_field == "CONFIDENCE":
            found = re.search(r"([01](?:\.\d+)?|\.\d+|100%|\d{1,2}%)", value)
            if found:
                token = found.group(1)
                confidence = float(token.rstrip("%")) / 100.0 if token.endswith("%") else float(token)
                confidence = max(0.0, min(1.0, confidence))
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

    if not reasoning_lines:
        reasoning_lines = ["No explicit reasoning was returned by the model."]

    if not saw_vote:
        validation_errors.append("missing vote result")
    if evidence_quality is None:
        validation_errors.append("missing evidence_quality")
    if critical_risk is None:
        validation_errors.append("missing critical_risk")

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
    )


def split_list(value: str) -> List[str]:
    return [
        item.strip(" -;\t")
        for item in re.split(r",|;", value)
        if item.strip(" -;\t")
    ]


def parse_unit_float(value: str) -> Optional[float]:
    found = re.search(r"([01](?:\.\d+)?|\.\d+|100%|\d{1,2}%)", value)
    if not found:
        return None
    token = found.group(1)
    parsed = float(token.rstrip("%")) / 100.0 if token.endswith("%") else float(token)
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
