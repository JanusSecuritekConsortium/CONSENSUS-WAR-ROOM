from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import ARBITER, TRIBUNAL_AGENT_IDS
from core.prompting.assembler import load_monolith_profile


def test_monolith_profiles_define_required_doctrinal_fields() -> None:
    required = {
        "canonical_id",
        "display_role",
        "doctrine",
        "preferred_reasoning_style",
        "risk_bias",
        "evidence_weighting",
        "refusal_escalation_behavior",
    }
    for agent_id in [ARBITER, *TRIBUNAL_AGENT_IDS]:
        profile = load_monolith_profile(agent_id)
        assert required <= set(profile), agent_id
        assert profile["canonical_id"] == agent_id
        assert "MAGI" not in profile["doctrine"]
        assert "ARASAKA" not in profile["doctrine"]


if __name__ == "__main__":
    test_monolith_profiles_define_required_doctrinal_fields()
    print("test_monolith_profiles PASS")
