from types import SimpleNamespace
import flet as ft
import pytest

from core.directorate import STARTUP_COMPONENTS
from tests.helpers.gui_harness import make_gui_state
from tests.test_directorate_interaction import walk, button
from tools.gui_smoke_check import SmokePage
from ui import flet_app as gui
from ui.directorate import build_boot


class Page(SmokePage):
    def __init__(self):
        super().__init__()
        self.jobs = []
        self.on_keyboard_event = None
    def update(self, *controls):
        self.updated += 1
    def run_thread(self, handler, *args):
        self.jobs.append((handler, args))


def scene(draft="Fixture proposal"):
    state = make_gui_state()
    state.proposal_input_text = draft
    for component in STARTUP_COMPONENTS:
        state.directorate.emit(component, "STARTUP_CHECK", "AVAILABLE", "Fixture check", check=True)
    page = Page()
    gui._render_page(page, state)
    return page, state


def editor(page):
    return next(c for root in page.controls for c in walk(root) if isinstance(c, ft.TextField))


def feedback(state):
    return next(c for c in walk(state.proposal_regions[0])
                if c.data == {"role": "proposal_submission_feedback"}).value


def test_directorate_footer_keyboard_and_palette_open_same_desk_without_janus():
    page, state = scene()
    assert not state.directorate_boot_open
    button(page, "Ctrl+P DIRECTORATE").on_click(None)
    assert state.directorate_open
    assert not state.directorate_boot_open
    assert any(c.data == "directorate_desk" for c in page.overlay)
    assert {e.component for e in state.directorate.checks()} == set(STARTUP_COMPONENTS)
    assert "JANUS" not in STARTUP_COMPONENTS
    page.on_keyboard_event(SimpleNamespace(key="P", ctrl=True))
    assert not state.directorate_open
    assert not any(c.data == "directorate_desk" for c in page.overlay)
    gui.execute_command_palette_action(state, "Open DIRECTORATE")
    assert state.directorate_open


def test_checks_can_close_while_optional_provider_check_is_running():
    page, state = scene()
    state.directorate_busy = True
    button(page, "Ctrl+D Diagnostics").on_click(None)
    button(page, "SYSTEM CHECKS").on_click(None)
    close = button(page, "CLOSE")
    assert not close.disabled
    close.on_click(None)
    assert not state.directorate_boot_open and state.directorate_busy


def test_startup_checks_do_not_include_janus_and_invalid_config_still_opens_recovery(monkeypatch, tmp_path):
    from tests.test_directorate import stub_startup
    statuses = [{"status": "ready", "provider": {"status": "ready"}}]
    stub_startup(monkeypatch, tmp_path, statuses)
    state = gui.create_gui_state("janus", gui.RuntimeConfig(backend="mock"), initialize=False)
    gui.initialize_directorate(state)
    assert {e.component for e in state.directorate.checks()} == set(STARTUP_COMPONENTS)
    assert not any(e.component == "JANUS" for e in state.directorate.events())
    monkeypatch.setattr(gui, "ensure_flet_desktop_runtime", lambda: None)
    monkeypatch.setattr(gui, "create_gui_state", lambda *args, **kwargs: state)
    monkeypatch.setattr(gui.ft, "app", lambda target: target(Page()))
    gui.run_flet_gui("janus", state.config, startup_config_error=True)
    assert state.directorate_boot_open and state.directorate_config_failed


def test_submit_stays_put_between_input_blur_and_click():
    page, state = scene()
    field = editor(page)
    field.on_focus(None)
    proposal = state.proposal_regions[0]
    actions = next(c for c in walk(proposal) if c.data == {"role": "proposal_action_target"})
    submit = button(page, "SUBMIT TO TRIBUNAL")
    actions.on_hover(SimpleNamespace(data="true"))
    field.on_blur(None)
    assert state.proposal_expanded and proposal.expand is True
    assert button(page, "SUBMIT TO TRIBUNAL") is submit
    submit.on_click(None)
    assert not state.proposal_expanded and len(page.jobs) == 1
    assert "accepted" in feedback(state)


def test_leaving_actions_after_blur_collapses_without_losing_draft():
    page, state = scene()
    field = editor(page)
    field.on_focus(None)
    actions = next(c for c in walk(state.proposal_regions[0]) if c.data == {"role": "proposal_action_target"})
    actions.on_hover(SimpleNamespace(data="true"))
    field.on_blur(None)
    actions.on_hover(SimpleNamespace(data="false"))
    assert not state.proposal_expanded
    assert editor(page) is field and field.value == "Fixture proposal"


def test_ctrl_enter_submits_while_background_checks_run_and_duplicate_is_visible():
    page, state = scene()
    state.directorate_busy = True
    page.on_keyboard_event(SimpleNamespace(key="Enter", ctrl=True))
    assert len(page.jobs) == 1 and state.submission_lock.locked()
    assert "accepted" in feedback(state)
    button(page, "SUBMIT TO TRIBUNAL").on_click(None)
    assert len(page.jobs) == 1 and "already being reviewed" in feedback(state)


def test_blank_and_invalid_config_have_visible_feedback():
    page, state = scene("")
    button(page, "SUBMIT TO TRIBUNAL").on_click(None)
    assert "Enter a proposal" in feedback(state) and not page.jobs
    field = editor(page)
    field.value = "New draft"
    field.on_change(SimpleNamespace(control=field))
    state.directorate_config_failed = True
    button(page, "SUBMIT TO TRIBUNAL").on_click(None)
    assert "Configuration needs attention" in feedback(state) and not page.jobs
    assert not state.submission_lock.locked()


@pytest.mark.parametrize("failure", ["scheduler", "render"])
def test_dispatch_failure_releases_lock_and_keeps_retry_available(monkeypatch, failure):
    page, state = scene()
    original_render = gui._render_page
    if failure == "scheduler":
        page.run_thread = lambda *args: (_ for _ in ()).throw(RuntimeError("Fixture scheduler unavailable"))
    else:
        monkeypatch.setattr(gui, "_render_page", lambda *args: (_ for _ in ()).throw(RuntimeError("Fixture mount unavailable")))
    button(page, "SUBMIT TO TRIBUNAL").on_click(None)
    assert not state.submission_lock.locked() and "Could not start" in feedback(state)
    page.run_thread = lambda handler, *args: page.jobs.append((handler, args))
    monkeypatch.setattr(gui, "_render_page", original_render)
    button(page, "SUBMIT TO TRIBUNAL").on_click(None)
    assert len(page.jobs) == 1 and state.submission_lock.locked()


def test_worker_failure_is_visible_and_releases_lock(monkeypatch):
    page, state = scene()
    monkeypatch.setattr(gui, "submit_proposal_live_for_gui", lambda *args, **kwargs:
                        (_ for _ in ()).throw(ValueError("PRIVATE_EXCEPTION_MARKER")))
    button(page, "SUBMIT TO TRIBUNAL").on_click(None)
    worker, args = page.jobs.pop()
    worker(*args)
    assert not state.submission_lock.locked()
    assert "Submission failed" in feedback(state) and "PRIVATE_EXCEPTION_MARKER" not in feedback(state)


def test_actual_submit_button_completes_all_nine_mock_assessments(monkeypatch):
    page, state = scene("Evaluate the fixture operation.")
    state.config.backend = "mock"
    state.reduced_motion = True
    monkeypatch.setattr(gui, "create_proposal", lambda **kwargs: {"proposal_id": "ui-submit-fixture"})
    monkeypatch.setattr(gui, "build_context_packet", lambda query: {"items": [], "prior_decisions_used": 0})
    monkeypatch.setattr(gui, "record_result", lambda result: None)
    monkeypatch.setattr(gui, "log_decision_trace", lambda result: None)
    monkeypatch.setattr(gui, "read_latest_trace", lambda: {})
    monkeypatch.setattr(gui, "link_decision_trace_to_proposal", lambda *args, **kwargs: {})
    monkeypatch.setattr(gui, "upsert_session_record", lambda record: None)
    monkeypatch.setattr(gui, "read_recent_log_events", lambda: [])
    monkeypatch.setattr(gui, "read_recent_decisions", lambda: [])
    monkeypatch.setattr("core.voting.orchestrator.build_aeternum_data_enrichment", lambda *args, **kwargs: {})
    monkeypatch.setattr("core.voting.orchestrator.VotingOrchestrator._build_bellator_context_packet", lambda *args: {})
    button(page, "SUBMIT TO TRIBUNAL").on_click(None)
    worker, args = page.jobs.pop()
    worker(*args)
    assert not state.submission_lock.locked() and state.current_result is not None
    assert len(state.deliberation_records) == 9
    assert sum(e.kind == "ASSESSMENT_RECEIVED" for e in state.directorate.events()) == 9
    assert "Verdict recorded" in feedback(state)
