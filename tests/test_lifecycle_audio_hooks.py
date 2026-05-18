from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.war_room_runtime import lifecycle_hook_names


def test_future_audio_lifecycle_hooks_are_declared_only() -> None:
    assert lifecycle_hook_names() == (
        "on_proposal_received",
        "on_vote_received",
        "on_consensus_locked",
        "on_error",
    )


if __name__ == "__main__":
    test_future_audio_lifecycle_hooks_are_declared_only()
    print("test_lifecycle_audio_hooks PASS")
