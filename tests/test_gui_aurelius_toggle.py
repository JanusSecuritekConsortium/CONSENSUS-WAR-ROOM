from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.flet_app import build_gui_layout, create_gui_state, set_aurelius_voice_loop


def _noop(*args, **kwargs):
    return None


def _walk(control) -> Iterable[object]:
    yield control
    content = getattr(control, "content", None)
    if content is not None:
        yield from _walk(content)
    for child in getattr(control, "controls", []) or []:
        yield from _walk(child)


def test_gui_footer_exposes_aurelius_voice_loop_toggle() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    layout = build_gui_layout(state, _noop, _noop, _noop, _noop, _noop, toggle_aurelius_voice=_noop)
    switches = [control for control in _walk(layout) if isinstance(control, ft.Switch)]
    labels = [switch.label for switch in switches]
    assert "AURELIUS Voice Loop" in labels


def test_gui_aurelius_toggle_updates_runtime_state() -> None:
    state = create_gui_state("JANUS", RuntimeConfig(theme="janus", backend="mock"))
    set_aurelius_voice_loop(state, True)
    assert state.aurelius_voice_loop_enabled is True
    assert state.aurelius_runtime is not None
    assert state.aurelius_runtime.status()["voice_loop_enabled"] is True
    set_aurelius_voice_loop(state, False)
    assert state.aurelius_voice_loop_enabled is False
    assert state.aurelius_runtime.status()["voice_loop_enabled"] is False


if __name__ == "__main__":
    test_gui_footer_exposes_aurelius_voice_loop_toggle()
    test_gui_aurelius_toggle_updates_runtime_state()
    print("test_gui_aurelius_toggle PASS")
