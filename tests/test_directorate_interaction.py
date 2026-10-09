from types import SimpleNamespace
import time

import flet as ft
import pytest

from config.names import BELLATOR
from core.models import Vote, VoteValue
from tests.helpers.gui_harness import make_gui_state, noop
from tools.gui_smoke_check import SmokePage
from ui import flet_app as gui
from ui.components.monolith_panel import card_border, feedback_color, VERDICT_FEEDBACK_SECONDS
from ui.deliberation import assessment_record, build_assessments
from ui.directorate import contrast_ratio
from ui.themes.catalog import THEMES
from ui.visual_checks import flatten_text


def walk(control):
    yield control
    if getattr(control, "content", None) is not None:
        yield from walk(control.content)
    for child in getattr(control, "controls", []) or []:
        yield from walk(child)


def button(page, label):
    return next(c for root in page.controls + page.overlay for c in walk(root)
                if (isinstance(c, ft.TextButton) and c.text == label)
                or (isinstance(c, ft.Container) and isinstance(c.content, ft.Text)
                    and c.content.value == label and c.on_click is not None))


@pytest.mark.parametrize("theme", THEMES)
def test_editor_fills_available_space_and_keeps_actions_outside_input(theme):
    state = make_gui_state(theme)
    state.proposal_input_text = "A long proposal\n" * 300
    layout = gui.build_gui_layout(state, noop, noop, noop, noop, noop,
        on_proposal_focus=noop, on_proposal_blur=noop,
        change_watch_deliberation=noop, open_deliberation=noop)
    center = layout.content.controls[1].content.controls[1].content
    proposal, verdict = center.controls
    editor = next(c for c in walk(proposal) if isinstance(c, ft.TextField))
    actions = next(c for c in walk(proposal) if c.data == {"role": "proposal_actions"})
    # Even a saved long draft stays compact until the operator edits it.
    assert proposal.height == gui.PROPOSAL_HEIGHT and proposal.expand is None
    assert verdict.visible is True
    gui._set_proposal_editing(SimpleNamespace(update=noop), state, True)
    assert proposal.expand is True and proposal.height in (None, "")
    assert verdict.visible is False
    assert editor.value == state.proposal_input_text
    assert editor.fit_parent_size and editor.expand and editor.max_lines is None
    assert proposal.content.content.controls[-1] is actions
    assert editor not in list(walk(actions))
    assert any(isinstance(c, ft.TextButton) and c.text == "SUBMIT TO TRIBUNAL" for c in walk(actions))
    gui._set_proposal_editing(SimpleNamespace(update=noop), state, False)
    assert proposal.height == gui.PROPOSAL_HEIGHT and proposal.expand is None
    assert verdict.expand is True and verdict.visible is True
    assert next(c for c in walk(proposal) if isinstance(c, ft.TextField)) is editor
    assert editor.value == state.proposal_input_text


@pytest.mark.parametrize("theme", THEMES.values(), ids=THEMES.keys())
def test_verdict_feedback_has_contrast_holds_then_returns_to_idle(theme):
    assert VERDICT_FEEDBACK_SECONDS > 10
    colors = {feedback_color(theme, status) for status in ("APPROVE", "DENY", "NO_CONSENSUS")}
    assert len(colors) == 3
    assert all(contrast_ratio(color, theme.surface_color) >= 4.5 for color in colors)
    for status in ("APPROVE", "DENY", "ABSTAIN", "NO_CONSENSUS", "ERROR"):
        feedback = (status, 100 + VERDICT_FEEDBACK_SECONDS)
        assert card_border(theme, status, feedback, 111)[0] == feedback_color(theme, status)
        assert card_border(theme, status, feedback, 113) == (theme.primary_color, 1)
    assert card_border(theme, "THINKING", None, 1)[0] != card_border(theme, "THINKING", None, 2)[0]
    assert card_border(theme, "THINKING", None, 1, reduced_motion=True) == card_border(theme, "THINKING", None, 2, reduced_motion=True)


def test_public_assessment_shows_arguments_and_revision_without_raw_or_tagged_reasoning():
    vote = Vote(BELLATOR, "security", VoteValue.DENY, .8,
                "<think>PRIVATE_THOUGHT</think>Public assessment", model="fixture-model",
                raw_response="PRIVATE_RAW", argument={"claim": "Explicit claim",
                    "evidence": [{"source": "supplied-source", "detail": "Explicit evidence"}],
                    "assumptions": ["Explicit assumption"], "strongest_objection": "Explicit objection",
                    "change_condition": "Independent confirmation"},
                peer_responses=[{"stance": "challenge", "peer": "AETERNUM", "reason": "Source too old"}],
                review_required=True, review_reason="Expert review", vote_change_reason="New evidence",
                risks=["Risk"], conditions=["Condition"], unresolved_disagreements=["Unresolved"])
    state = make_gui_state()
    state.deliberation_records = [assessment_record(vote, 2, "critique")]
    panel = build_assessments(state)
    text = "\n".join(flatten_text(panel))
    assert all(value in text for value in ("Public assessment", "Explicit claim", "Explicit evidence",
        "Explicit assumption", "Explicit objection", "Independent confirmation", "Source too old", "Expert review", "New evidence"))
    assert "PRIVATE_THOUGHT" not in text and "PRIVATE_RAW" not in text
    assert panel.auto_scroll is False
    vote.validation_errors = ["private diagnostic"]
    vote.reasoning = "PRIVATE_EXCEPTION_PATH"
    assert "PRIVATE_EXCEPTION_PATH" not in str(assessment_record(vote, 3, "revision"))


def test_watch_toggle_opens_on_submission_and_closing_keeps_worker_running(monkeypatch):
    class Page(SmokePage):
        def __init__(self):
            super().__init__()
            self.jobs = []
        def run_thread(self, handler, *args):
            self.jobs.append((handler, args))
        def update(self, *controls):
            pass
    state = make_gui_state()
    state.proposal_input_text = "Keep this draft"
    monkeypatch.setattr(gui, "save_directorate_preferences", lambda state: None)
    page = Page()
    gui._render_page(page, state)
    checkbox = next(c for root in page.controls for c in walk(root)
                    if isinstance(c, ft.Checkbox) and c.label == "Watch deliberation")
    checkbox.on_change(SimpleNamespace(control=SimpleNamespace(value=True)))
    editor = next(c for root in page.controls for c in walk(root) if isinstance(c, ft.TextField))
    editor.on_focus(None)
    assert state.proposal_expanded
    editor.on_blur(None)
    assert not state.proposal_expanded and state.proposal_input_text == "Keep this draft"
    editor.on_focus(None)
    button(page, "SUBMIT TO TRIBUNAL").on_click(None)
    assert not state.proposal_expanded
    assert state.deliberation_viewer_open and state.submission_lock.locked()
    assert len(page.jobs) == 1
    viewer = state.live_panels["deliberation_assessments"][0]
    state.deliberation_records = [assessment_record(Vote(BELLATOR, "security", VoteValue.APPROVE, .9, "First assessment"), 1, "assessment")]
    gui._refresh_live_page(page, state)
    assert state.live_panels["deliberation_assessments"][0] is viewer
    assert "First assessment" in "\n".join(flatten_text(viewer))
    button(page, "CLOSE").on_click(None)
    assert not state.deliberation_viewer_open and state.submission_lock.locked()
    assert len(page.jobs) == 1
    assert state.proposal_input_text == "Keep this draft"


@pytest.mark.parametrize("theme", THEMES)
def test_focus_resize_keeps_draft_and_input_mounted_until_blur(theme):
    class Page(SmokePage):
        def update(self, *controls):
            self.updated += 1
    page = Page()
    state = make_gui_state(theme)
    gui._render_page(page, state)
    shell = page.controls[0]
    editor = next(c for c in walk(shell) if isinstance(c, ft.TextField))
    proposal, verdict = state.proposal_regions
    assert not state.proposal_expanded and verdict.visible
    editor.on_focus(None)
    assert proposal.expand and proposal.height in (None, "") and not verdict.visible
    editor.value = "An editable draft\n" * 100
    editor.on_change(SimpleNamespace(control=editor))
    gui._refresh_live_page(page, state)
    assert page.controls == [shell]
    assert next(c for c in walk(proposal) if isinstance(c, ft.TextField)) is editor
    assert state.proposal_input_text == editor.value
    editor.on_blur(None)
    assert proposal.height == gui.PROPOSAL_HEIGHT and verdict.visible
    assert next(c for c in walk(proposal) if isinstance(c, ft.TextField)) is editor
    assert editor.value == state.proposal_input_text
    editor.on_focus(None)
    assert proposal.expand and not verdict.visible


def test_border_updates_preserve_card_controls_and_editor_focus():
    state = make_gui_state()
    gui.build_gui_layout(state, noop, noop, noop, noop, noop)
    panel = state.live_panels["build_monolith_panel"][0]
    card = panel.controls[1]
    state.monolith_statuses[card.data["agent_id"]] = "DENY"
    state.monolith_feedback[card.data["agent_id"]] = ("DENY", time.monotonic() + 12)
    gui._refresh_live_page(SimpleNamespace(update=noop), state)
    assert panel.controls[1] is card
    assert card.border.top.color == feedback_color(state.theme, "DENY")
