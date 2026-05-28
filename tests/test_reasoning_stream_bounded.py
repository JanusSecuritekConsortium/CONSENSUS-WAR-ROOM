from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.tribunal_events import REASONING_STREAM_LIMIT, append_reasoning_event, theme_reasoning_phrase


def test_reasoning_stream_keeps_bounded_status_events() -> None:
    events: list[str] = []
    for index in range(REASONING_STREAM_LIMIT + 6):
        append_reasoning_event(events, f"status event {index}")

    assert len(events) == REASONING_STREAM_LIMIT
    assert events[0] == "status event 6"


def test_theme_reasoning_phrases_are_status_only() -> None:
    assert "MAGI" in theme_reasoning_phrase("eva", "CLASSIFYING")
    assert "Machine spirit" in theme_reasoning_phrase("wh40k", "NO_CONSENSUS")
    assert "step-by-step" not in theme_reasoning_phrase("arasaka", "ANALYZING").lower()


if __name__ == "__main__":
    test_reasoning_stream_keeps_bounded_status_events()
    test_theme_reasoning_phrases_are_status_only()
    print("test_reasoning_stream_bounded PASS")
