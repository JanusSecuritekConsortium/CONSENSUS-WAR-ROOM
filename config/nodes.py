from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict

from config.agents import AGENT_PROFILES
from config.names import AETERNUM, BELLATOR, LEGACY_ROLE_TO_AGENT_ID, RATIONALIS
from core.models import NodeIdentity


DEFAULT_NODES: Dict[str, NodeIdentity] = {
    RATIONALIS: NodeIdentity(
        role="Logic",
        codename=RATIONALIS,
        core_name="Logic Core",
        monolith_name=RATIONALIS,
        symbol="R",
        model=AGENT_PROFILES[RATIONALIS].model_preference,
        temperature=0.1,
        mission="formal reasoning, contradictions, feasibility, hidden assumptions",
        prompt=(
            AGENT_PROFILES[RATIONALIS].system_prompt
        ),
    ),
    AETERNUM: NodeIdentity(
        role="Finance",
        codename=AETERNUM,
        core_name="Finance Core",
        monolith_name=AETERNUM,
        symbol="A",
        model=AGENT_PROFILES[AETERNUM].model_preference,
        temperature=0.3,
        mission="cost, market impact, opportunity cost, historical precedent",
        prompt=(
            AGENT_PROFILES[AETERNUM].system_prompt
        ),
    ),
    BELLATOR: NodeIdentity(
        role="Security",
        codename=BELLATOR,
        core_name="Security Core",
        monolith_name=BELLATOR,
        symbol="B",
        model=AGENT_PROFILES[BELLATOR].model_preference,
        temperature=0.6,
        mission="operational risk, attack surface, resilience, tactical exposure",
        prompt=(
            AGENT_PROFILES[BELLATOR].system_prompt
        ),
    ),
}


def apply_node_overrides(
    nodes: Dict[str, NodeIdentity],
    overrides: Dict[str, Dict[str, Any]],
) -> Dict[str, NodeIdentity]:
    configured = dict(nodes)
    allowed = {
        "role",
        "codename",
        "core_name",
        "monolith_name",
        "symbol",
        "model",
        "temperature",
        "mission",
        "prompt",
    }

    for key, patch in overrides.items():
        normalized_key = LEGACY_ROLE_TO_AGENT_ID.get(key.upper(), key.upper())
        if normalized_key not in configured:
            continue
        clean_patch = {
            field_name: value
            for field_name, value in patch.items()
            if field_name in allowed
        }
        configured[normalized_key] = replace(configured[normalized_key], **clean_patch)
    return configured
