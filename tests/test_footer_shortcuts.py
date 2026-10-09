from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for


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


def test_footer_lists_operator_shortcuts() -> None:
    text = "\n".join(_flatten_text(build_layout_for("eva")))
    assert "Ctrl+K Command" in text
    assert "Ctrl+D Diagnostics" in text
    assert "Ctrl+P DIRECTORATE" in text
    assert "Ctrl+H History" in text
    assert "Ctrl+E Export" in text


if __name__ == "__main__":
    test_footer_lists_operator_shortcuts()
    print("test_footer_shortcuts PASS")


def test_footer_clicks_and_keyboard_share_actions(monkeypatch):
    from types import SimpleNamespace
    from tests.helpers.gui_harness import make_gui_state
    from tests.test_diagnostics_overlay_reentrant_guard import FakePage
    from ui import flet_app as gui

    state = make_gui_state("janus")
    page = FakePage()
    gui._render_page(page, state)
    buttons = page.controls[0].content.controls[2].content.controls[1].content.controls
    assert len(buttons) == 6
    actions = []
    monkeypatch.setattr(gui, "_render_page", lambda *args: None)
    monkeypatch.setattr(gui, "execute_command_palette_action", lambda state, action: actions.append(action))
    for button, key, attribute in zip(buttons, ("K", "D", "P", "T", "H", "E"),
                                      ("command_palette_open", "diagnostics_drawer_open", "directorate_open", None, "proposal_history_open", None)):
        assert button.on_click is not None
        button.on_click(None)
        if attribute:
            assert getattr(state, attribute) is True
        page.on_keyboard_event(SimpleNamespace(key=key, ctrl=True))
        if attribute:
            assert getattr(state, attribute) is False
    assert actions == ["Toggle Theme", "Toggle Theme", "Export Latest Verdict", "Export Latest Verdict"]
