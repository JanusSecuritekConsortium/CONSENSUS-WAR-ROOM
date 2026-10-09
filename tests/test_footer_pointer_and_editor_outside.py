from types import SimpleNamespace
import flet as ft
import pytest
from tests.test_directorate_submit_controls import scene, editor
from tests.test_directorate_interaction import walk, button
from ui import flet_app as gui


def test_first_outside_pointer_event_collapses_without_a_blur_event(monkeypatch):
    page, state = scene()
    field = editor(page)
    field.on_focus(None)
    blurred = []
    monkeypatch.setattr(field, "blur", lambda: blurred.append(True))
    field.on_tap_outside(SimpleNamespace(control=field))
    assert not state.proposal_expanded and not state.proposal_input_focused
    assert blurred == [True]
    assert editor(page) is field and field.value == "Fixture proposal"
    field.on_blur(None)
    assert not state.proposal_expanded


def test_only_actual_action_targets_protect_submit_from_pointer_down(monkeypatch):
    page, state = scene()
    field = editor(page)
    field.on_focus(None)
    monkeypatch.setattr(field, "blur", lambda: None)
    actions = next(c for c in walk(state.proposal_regions[0]) if c.data == {"role": "proposal_actions"})
    assert actions.on_hover is None
    target = next(c for c in walk(actions) if c.data == {"role": "proposal_action_target"})
    target.on_hover(SimpleNamespace(data="true"))
    field.on_tap_outside(SimpleNamespace(control=field))
    assert state.proposal_expanded
    submit = button(page, "SUBMIT TO TRIBUNAL")
    submit.on_click(None)
    assert not state.proposal_expanded and len(page.jobs) == 1


@pytest.mark.parametrize("key,attribute,role", [
    ("K", "command_palette_open", "command_palette"),
    ("D", "diagnostics_drawer_open", "diagnostics_drawer"),
    ("P", "directorate_open", "directorate_desk"),
    ("H", "proposal_history_open", "proposal_history_viewer"),
])
def test_footer_click_targets_reopen_and_close_viewers_above_the_footer(key, attribute, role):
    page, state = scene()
    def command():
        return next(c for root in page.controls for c in walk(root)
                    if c.data == {"role": "footer_command", "key": key})
    target = command()
    assert isinstance(target, ft.Container) and target.ink and target.height == 40
    assert target._get_attr("onClick") is True
    target.on_click(None)
    assert getattr(state, attribute)
    overlay = next(c for c in page.overlay if c.data == role)
    assert overlay.bottom >= gui.FOOTER_HEIGHT
    assert overlay.clip_behavior == ft.ClipBehavior.HARD_EDGE
    command().on_click(None)
    assert not getattr(state, attribute)
    assert not any(c.data == role for c in page.overlay)


def test_footer_export_displays_its_outcome(monkeypatch):
    page, state = scene()
    def fixture_export(state, action):
        assert action == "Export Latest Verdict"
        state.operator_status = "No verdict available to export."
    monkeypatch.setattr(gui, "execute_command_palette_action", fixture_export)
    button(page, "Ctrl+E Export").on_click(None)
    assert state.operator_status != "OPERATOR READY"
    assert state.submission_message == state.operator_status


def test_footer_theme_click_changes_theme():
    page, state = scene()
    previous = state.theme_key
    button(page, "Ctrl+T Theme").on_click(None)
    assert state.theme_key != previous


def test_closed_history_and_trace_viewers_do_not_block_footer_redraw(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("Unopened disk-backed viewer was constructed")
    for name in ("build_decision_trace_viewer", "build_proposal_history_viewer",
                 "build_visual_review_status_viewer", "build_telemetry_snapshot_viewer",
                 "build_simulation_viewer", "build_simulation_create_overlay",
                 "build_branch_tree_viewer"):
        monkeypatch.setattr(gui, name, unexpected)
    page, state = scene()
    button(page, "Ctrl+K Command").on_click(None)
    assert state.command_palette_open
    button(page, "Ctrl+D Diagnostics").on_click(None)
    assert state.diagnostics_drawer_open
