from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.flet_app import HEARTBEAT_MESSAGES, advance_gui_heartbeat, create_gui_state


def test_heartbeat_rotates_without_provider() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    seen = [state.heartbeat_text]

    for _ in range(len(HEARTBEAT_MESSAGES) * 2):
        seen.append(advance_gui_heartbeat(state))

    assert set(HEARTBEAT_MESSAGES) <= set(seen)
    assert state.provider_status["status"] == "ready"


if __name__ == "__main__":
    test_heartbeat_rotates_without_provider()
    print("test_gui_heartbeat PASS")
