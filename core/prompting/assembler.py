from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from core.models import NodeIdentity
from core.paths import SYSTEM_ROOT


PROFILE_DIR = SYSTEM_ROOT / "monoliths" / "profiles"


def load_monolith_profile(agent_id: str) -> Dict[str, Any]:
    path = PROFILE_DIR / f"{agent_id.lower()}.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing monolith profile: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Monolith profile must be a JSON object: {path}")
    return payload


def assemble_monolith_prompt(node: NodeIdentity, proposal: str, context: Dict[str, Any]) -> str:
    profile = load_monolith_profile(node.codename)
    memory_context = context.get("memory_context", {}) if isinstance(context, dict) else {}
    context_summary = memory_context.get("summary", "No prior decisions retrieved.") if isinstance(memory_context, dict) else "No prior decisions retrieved."
    selected_model = context.get("model", node.model) if isinstance(context, dict) else node.model
    shared_context = json.dumps(context, indent=2, ensure_ascii=True) if context else "{}"

    return f"""
{node.prompt}

DOCTRINAL PROFILE:
- canonical_id: {profile.get('canonical_id', node.codename)}
- display_role: {profile.get('display_role', node.role)}
- doctrine: {profile.get('doctrine', '')}
- preferred_reasoning_style: {profile.get('preferred_reasoning_style', '')}
- risk_bias: {profile.get('risk_bias', '')}
- evidence_weighting: {profile.get('evidence_weighting', '')}
- refusal_escalation_behavior: {profile.get('refusal_escalation_behavior', '')}

SELECTED MODEL:
{selected_model}

Mission focus:
{node.mission}

Proposal:
{proposal}

RELEVANT MEMORY CONTEXT:
{context_summary}

Shared machine context:
{shared_context}

Return exactly this parseable schema:
VOTE: APPROVE | DENY | CONDITIONAL | ABSTAIN | ESCALATE
CONFIDENCE: 0.00 to 1.00
REASONING: concise but specific reasoning grounded in doctrine and retrieved context
RISKS: comma-separated risks
CONDITIONS: comma-separated conditions, if any
""".strip()
