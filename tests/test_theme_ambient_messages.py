from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.themes.catalog import THEMES
from ui.war_room_runtime import ambient_message, ambient_messages_for_theme


def test_each_theme_has_ambient_messages() -> None:
    for theme_key in THEMES:
        messages = ambient_messages_for_theme(theme_key)
        assert len(messages) >= 3
        assert all(message == message.upper() for message in messages)


def test_ambient_messages_are_theme_specific() -> None:
    assert "MAGI" in ambient_message("eva", 0)
    assert "COGITATOR" in ambient_message("wh40k", 0)
    assert "EXECUTIVE" in ambient_message("arasaka", 0)
    assert "DUAL" in ambient_message("janus", 0)


if __name__ == "__main__":
    test_each_theme_has_ambient_messages()
    test_ambient_messages_are_theme_specific()
    print("test_theme_ambient_messages PASS")
