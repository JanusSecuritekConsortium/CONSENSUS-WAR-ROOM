import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.helpers.gui_harness import make_gui_state
from ui.flet_app import COMMAND_PALETTE_ACTIONS, build_data_sources_viewer, execute_command_palette_action


def _text(control) -> str:
    values = []
    if isinstance(getattr(control, "value", None), str):
        values.append(control.value)
    if getattr(control, "content", None) is not None:
        values.append(_text(control.content))
    for child in getattr(control, "controls", []):
        values.append(_text(child))
    return "\n".join(values)


def test_data_source_overlay_and_palette_actions() -> None:
    assert "View Source Health" in COMMAND_PALETTE_ACTIONS
    state = make_gui_state("eva")
    execute_command_palette_action(state, "View Source Health")
    assert state.data_sources_viewer_open is True
    assert "DATA SOURCES STATUS" in _text(build_data_sources_viewer(state))


if __name__ == "__main__":
    test_data_source_overlay_and_palette_actions()
    print("test_gui_data_sources_overlay PASS")
