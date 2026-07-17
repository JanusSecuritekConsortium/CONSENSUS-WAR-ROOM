from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.flet_app import build_diagnostics_drawer, build_gui_layout, create_gui_state
from ui.layout_contract import CENTER_COLUMN_FLEX, LEFT_COLUMN_FLEX, RIGHT_COLUMN_FLEX


def _noop(*_args, **_kwargs) -> None:
    return None


def _flatten_text(control) -> list[str]:
    values: list[str] = []
    if hasattr(control, "value") and isinstance(control.value, str):
        values.append(control.value)
    if hasattr(control, "content") and control.content is not None:
        values.extend(_flatten_text(control.content))
    if hasattr(control, "controls"):
        for child in control.controls:
            values.extend(_flatten_text(child))
    return values


def test_diagnostics_drawer_does_not_change_main_layout_contract() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    layout = build_gui_layout(state, _noop, _noop, _noop, _noop, _noop)
    shell = layout.content
    body_row = shell.controls[1].content

    assert isinstance(shell, ft.Column)
    assert [control.expand for control in body_row.controls] == [LEFT_COLUMN_FLEX, CENTER_COLUMN_FLEX, RIGHT_COLUMN_FLEX]
    assert hasattr(layout, "diagnostics_drawer")


def test_diagnostics_drawer_shows_required_observability_fields() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    drawer = build_diagnostics_drawer(state)
    text = "\n".join(_flatten_text(drawer))

    assert "DIAGNOSTICS" in text
    assert "PROVIDER BACKEND:" in text
    assert "ENDPOINT STATUS:" in text
    assert "ACTIVE MODELS" in text
    assert "LAST VERDICT:" in text
    assert "LAST TEST MANIFEST:" in text
    assert "DEGRADED REASON:" in text


if __name__ == "__main__":
    test_diagnostics_drawer_does_not_change_main_layout_contract()
    test_diagnostics_drawer_shows_required_observability_fields()
    print("test_gui_diagnostic_drawer PASS")
