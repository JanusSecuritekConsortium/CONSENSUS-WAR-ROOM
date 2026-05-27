from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.flet_app import (
    COMMAND_PALETTE_ACTIONS,
    build_command_palette,
    create_gui_state,
    execute_command_palette_action,
)


def _flatten_text(control) -> list[str]:
    values: list[str] = []
    if hasattr(control, "value") and isinstance(control.value, str):
        values.append(control.value)
    if hasattr(control, "text") and isinstance(control.text, str):
        values.append(control.text)
    if hasattr(control, "content") and control.content is not None:
        values.extend(_flatten_text(control.content))
    if hasattr(control, "controls"):
        for child in control.controls:
            values.extend(_flatten_text(child))
    return values


def test_command_palette_lists_operator_actions() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    palette = build_command_palette(state)
    text = "\n".join(_flatten_text(palette))

    assert "COMMAND PALETTE" in text
    for action in COMMAND_PALETTE_ACTIONS:
        assert action in text


def test_command_palette_state_actions() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))

    execute_command_palette_action(state, "Open Diagnostics")
    assert state.diagnostics_drawer_open is True

    execute_command_palette_action(state, "Open Decision Trace Viewer")
    assert state.trace_viewer_open is True

    original_theme = state.theme_key
    execute_command_palette_action(state, "Toggle Theme")
    assert state.theme_key != original_theme


if __name__ == "__main__":
    test_command_palette_lists_operator_actions()
    test_command_palette_state_actions()
    print("test_command_palette PASS")
