from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.agents import AGENT_PROFILES
from config.names import CANONICAL_AGENT_IDS


def test_agent_profiles_complete() -> None:
    assert set(CANONICAL_AGENT_IDS) == set(AGENT_PROFILES)
    for agent_id, profile in AGENT_PROFILES.items():
        assert profile.id == agent_id
        assert profile.display_name
        assert profile.role
        assert profile.model_preference
        assert profile.system_prompt
        assert profile.memory_scope
        assert profile.voice_profile
        assert profile.enabled is True


if __name__ == "__main__":
    test_agent_profiles_complete()
    print("test_agent_profiles PASS")

