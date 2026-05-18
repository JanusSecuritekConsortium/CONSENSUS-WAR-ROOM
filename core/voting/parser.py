from __future__ import annotations

import re
from typing import List, Optional

from core.models import NodeIdentity, Vote, VoteValue


def parse_vote(raw: str, node: NodeIdentity, elapsed: float, backend_name: str) -> Vote:
    vote = VoteValue.ABSTAIN
    confidence = 0.5
    reasoning_lines: List[str] = []
    risks: List[str] = []
    conditions: List[str] = []
    active_field: Optional[str] = None

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        match = re.match(r"^(VOTE|CONFIDENCE|REASONING|RISKS|CONDITIONS)\s*:\s*(.*)$", stripped, re.I)
        if match:
            active_field = match.group(1).upper()
            value = match.group(2).strip()
        else:
            value = stripped

        if active_field == "VOTE":
            upper = value.upper()
            for candidate in VoteValue:
                if candidate.value in upper:
                    vote = candidate
                    break
        elif active_field == "CONFIDENCE":
            found = re.search(r"([01](?:\.\d+)?|\.\d+|100%|\d{1,2}%)", value)
            if found:
                token = found.group(1)
                confidence = float(token.rstrip("%")) / 100.0 if token.endswith("%") else float(token)
                confidence = max(0.0, min(1.0, confidence))
        elif active_field == "REASONING":
            reasoning_lines.append(value)
        elif active_field == "RISKS":
            risks.extend(split_list(value))
        elif active_field == "CONDITIONS":
            conditions.extend(split_list(value))

    if not reasoning_lines:
        reasoning_lines = ["No explicit reasoning was returned by the model."]

    return Vote(
        node_key=node.role.upper(),
        role=node.role,
        vote=vote,
        confidence=confidence,
        reasoning=" ".join(reasoning_lines).strip(),
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

