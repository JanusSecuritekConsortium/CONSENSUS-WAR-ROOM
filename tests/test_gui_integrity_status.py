from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui import flet_app
from ui.flet_app import build_command_palette, build_diagnostics_drawer, create_gui_state, execute_command_palette_action


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


def test_diagnostics_drawer_shows_integrity_status() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    state.runtime_snapshot_cache["integrity_status"] = {"status": "CLEAN"}
    drawer = build_diagnostics_drawer(state)
    text = "\n".join(_flatten_text(drawer))

    assert "INTEGRITY STATUS: CLEAN" in text


def test_command_palette_has_verify_integrity_action() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    palette = build_command_palette(state)
    text = "\n".join(_flatten_text(palette))

    assert "Verify Integrity" in text


def test_verify_integrity_action_updates_gui_state() -> None:
    original_verify = flet_app.verify_active_manifest
    try:
        flet_app.verify_active_manifest = lambda: {"status": "DRIFT", "modified": ["core/x.py"]}
        state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))

        execute_command_palette_action(state, "Verify Integrity")

        assert state.runtime_snapshot_cache["integrity_status"]["status"] == "DRIFT"
        assert state.operator_status == "Integrity DRIFT"
    finally:
        flet_app.verify_active_manifest = original_verify


if __name__ == "__main__":
    test_diagnostics_drawer_shows_integrity_status()
    test_command_palette_has_verify_integrity_action()
    test_verify_integrity_action_updates_gui_state()
    print("test_gui_integrity_status PASS")
