from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.flet_app import (
    build_command_palette,
    build_diagnostics_drawer,
    build_gui_layout,
    build_visual_review_status_viewer,
    create_gui_state,
    execute_command_palette_action,
)
from ui.layout_contract import CENTER_COLUMN_FLEX, LEFT_COLUMN_FLEX, RIGHT_COLUMN_FLEX


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


def _noop(*_args, **_kwargs) -> None:
    return None


def test_diagnostics_drawer_shows_visual_review_summary() -> None:
    state = create_gui_state("eva", RuntimeConfig(theme="eva", backend="mock"))
    drawer = build_diagnostics_drawer(state)
    text = "\n".join(_flatten_text(drawer))

    assert "VISUAL REVIEW FILE:" in text
    assert "VISUAL REVIEW PENDING:" in text


def test_command_palette_opens_visual_review_status_overlay() -> None:
    state = create_gui_state("eva", RuntimeConfig(theme="eva", backend="mock"))
    palette = build_command_palette(state)
    palette_text = "\n".join(_flatten_text(palette))

    assert "Visual Review Status" in palette_text
    execute_command_palette_action(state, "Visual Review Status")
    assert state.visual_review_viewer_open is True
    viewer = build_visual_review_status_viewer(state)
    assert "VISUAL REVIEW STATUS" in "\n".join(_flatten_text(viewer))


def test_visual_review_overlay_does_not_mutate_body_layout() -> None:
    state = create_gui_state("eva", RuntimeConfig(theme="eva", backend="mock"))
    execute_command_palette_action(state, "Visual Review Status")
    layout = build_gui_layout(state, _noop, _noop, _noop, _noop, _noop)
    body = layout.content.controls[1].content

    assert [control.expand for control in body.controls] == [LEFT_COLUMN_FLEX, CENTER_COLUMN_FLEX, RIGHT_COLUMN_FLEX]
    assert hasattr(layout, "visual_review_status_viewer")


if __name__ == "__main__":
    test_diagnostics_drawer_shows_visual_review_summary()
    test_command_palette_opens_visual_review_status_overlay()
    test_visual_review_overlay_does_not_mutate_body_layout()
    print("test_gui_visual_review_status PASS")
