from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.header import build_header
from ui.themes.catalog import get_gui_theme_options


def _text_values(control) -> list[str]:
    values: list[str] = []
    value = getattr(control, "value", None)
    if isinstance(value, str):
        values.append(value)
    if getattr(control, "content", None) is not None:
        values.extend(_text_values(control.content))
    for child in getattr(control, "controls", []) or []:
        values.extend(_text_values(child))
    return values


def test_session_status_row_is_present_for_every_theme() -> None:
    for theme in get_gui_theme_options():
        values = _text_values(build_header(theme, "ready", "available", session_id="session-test"))
        assert "SESSION" in values, theme.key
        assert "session-test" in values, theme.key


if __name__ == "__main__":
    test_session_status_row_is_present_for_every_theme()
    print("test_session_row_present_all_themes PASS")
