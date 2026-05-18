from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.animations.typewriter import reveal_text_with_cursor_sync, typewriter_frames


def test_typewriter_frames_include_cursor_and_lock() -> None:
    frames = typewriter_frames("APPROVED", pause_every=3)

    assert any(frame.endswith("_") for frame in frames)
    assert frames[-1] == "[CONSENSUS LOCKED]"
    assert "APPROVED" in frames


def test_enhanced_typewriter_skip_is_deterministic() -> None:
    updates: list[str] = []
    rendered = reveal_text_with_cursor_sync("CONSENSUS VERDICT", updates.append, speed=0, skip=True)

    assert rendered == "CONSENSUS VERDICT"
    assert updates == ["CONSENSUS VERDICT", "[CONSENSUS LOCKED]"]


if __name__ == "__main__":
    test_typewriter_frames_include_cursor_and_lock()
    test_enhanced_typewriter_skip_is_deterministic()
    print("test_verdict_typing_animation PASS")
