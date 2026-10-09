from dataclasses import FrozenInstanceError
from concurrent.futures import ThreadPoolExecutor
import pytest

from core.directorate import Directorate, DISPATCH_LIMIT
from core.export.cable import render_cable, export_dispatch
from core.models import FinalVerdict
from tests.test_directorate import result_fixture
from tests.test_directorate_submit_controls import scene
from tests.test_directorate_interaction import button
from ui import flet_app as gui
from ui.directorate import (PAPER, INK, stamp, contrast_ratio, dispatch_body,
                           build_dispatch_roll, build_dispatch_desk)
from ui.themes.catalog import THEMES
from ui.visual_checks import flatten_text


def decision(session="dispatch-fixture"):
    result = result_fixture(session_id=session)
    vote = result.votes["BELLATOR"]
    vote.argument = {"claim": "Independent evidence is missing."}
    vote.conditions = ["Confirm source provenance."]
    vote.review_required = True
    vote.review_reason = "Independent review."
    vote.risks = ["Unverified claim."]
    return result


def test_dispatch_freezes_report_deduplicates_and_bounds_session_register():
    journal = Directorate()
    result = decision()
    sources = [{"title": "Fixture", "url": "https://example.org/record"}]
    first = journal.record_decision(result, sources)
    result.query = "Changed live result"
    sources[0]["url"] = "https://example.org/changed"
    assert journal.record_decision(result) is first
    assert "Changed live result" not in first.report and "example.org/changed" not in first.report
    with pytest.raises(FrozenInstanceError):
        first.verdict = "APPROVE"
    for n in range(DISPATCH_LIMIT + 2):
        journal.record_decision(decision(str(n)))
    records = journal.dispatches()
    assert len(records) == DISPATCH_LIMIT
    assert records[-1].number == DISPATCH_LIMIT + 3
    assert first.report


def test_concurrent_report_receipts_have_unique_monotonic_numbers():
    journal = Directorate()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda n: journal.record_decision(decision(str(n))), range(16)))
    assert [d.number for d in journal.dispatches()] == list(range(1, 17))


def test_dispatch_reports_structured_justification_dissent_conditions_and_sources_without_private_fields():
    result = decision()
    vote = result.votes["BELLATOR"]
    vote.argument["claim"] += " <think>PRIVATE_CLAIM\nPRIVATE_SECOND_LINE</think>"
    vote.conditions.append("<analysis>PRIVATE_CONDITION</analysis>Public condition.")
    vote.reasoning = "UNSTRUCTURED_REASONING"
    vote.raw_response = "RAW_RESPONSE"
    result.deliberation_transcript = [{"agent_id": "BELLATOR", "model_fallback": True,
        "requested_model": "preferred", "model": "replacement", "raw_response": "RAW_TRANSCRIPT"}]
    text = render_cable(result, [{"title": "Fixture", "url": "https://example.org/source"}])
    assert all(s in text for s in ("Independent evidence", "Source reliability unresolved",
        "Confirm source provenance", "Independent review", "https://example.org/source",
        "preferred", "replacement", "Public condition"))
    assert all(s not in text for s in ("PRIVATE_", "UNSTRUCTURED_REASONING", "RAW_RESPONSE", "RAW_TRANSCRIPT"))
    vote.validation_errors = ["PRIVATE_EXCEPTION"]
    assert "PRIVATE_EXCEPTION" not in render_cable(result)


def test_notices_exclude_vitals_and_routine_turns_and_survive_health_polling():
    journal = Directorate()
    notice = journal.emit("BELLATOR", "MODEL_SUBSTITUTED", "DEGRADED", "Actual replacement")
    for _ in range(100):
        journal.emit("PROVIDER", "STARTUP_CHECK", "AVAILABLE", "Healthy", check=True)
        journal.emit("TRIBUNAL", "MODEL_STARTED", "RUNNING", "Routine turn")
    assert journal.notices() == (notice,)
    text = "\n".join(flatten_text(build_dispatch_roll(journal)))
    assert "Actual replacement" in text and "Healthy" not in text and "Routine turn" not in text


def test_line_arrival_finishes_and_reduced_motion_keeps_the_whole_report(tmp_path):
    journal = Directorate()
    dispatch = journal.record_decision(decision())
    start = dispatch_body(dispatch, animation=True, reduced_motion=False, now=dispatch.received_at)
    end = dispatch_body(dispatch, animation=True, reduced_motion=False, now=dispatch.received_at + 3)
    assert len(start) < len(end) and "END OF CABLE" in end
    assert dispatch_body(dispatch, animation=True, reduced_motion=True, now=dispatch.received_at) == end
    assert dispatch_body(dispatch, animation=False, reduced_motion=False, now=dispatch.received_at) == end
    assert export_dispatch(dispatch, tmp_path).read_text(encoding="utf-8") == dispatch.report


@pytest.mark.parametrize("theme", THEMES.values(), ids=THEMES)
def test_paper_is_readable_and_outcomes_remain_distinct_across_themes(theme):
    assert contrast_ratio(INK, PAPER) >= 4.5
    for verdict in FinalVerdict:
        assert contrast_ratio(stamp(verdict.value)[1], PAPER) >= 4.5
    assert len({stamp(v)[1] for v in ("APPROVE", "DENY", "NO_CONSENSUS")}) == 3
    journal = Directorate()
    journal.record_decision(decision())
    roll = build_dispatch_roll(journal, reduced_motion=True)
    desk = build_dispatch_desk(theme, journal, roll)
    text = "\n".join(flatten_text(desk))
    assert "DISPATCH 0001" in text and "NO CONSENSUS" in text
    assert "PUBLIC JUSTIFICATIONS" in text and "CONDITIONS AND REQUIRED REVIEW" in text
    assert roll.auto_scroll is False


def test_desk_updates_in_place_and_keeps_latest_receipt_during_next_submission(monkeypatch, tmp_path):
    page, state = scene()
    page.clipboard = []
    page.set_clipboard = page.clipboard.append
    monkeypatch.setattr(gui, "export_dispatch", lambda d: export_dispatch(d, tmp_path))
    button(page, "Ctrl+P DIRECTORATE").on_click(None)
    roll = state.live_panels["directorate_roll"][0]
    assert button(page, "COPY LATEST DISPATCH").disabled
    dispatch = state.directorate.record_decision(decision())
    state.current_result = None  # Another query is being deliberated.
    state.reduced_motion = True
    gui._refresh_live_page(page, state)
    assert state.live_panels["directorate_roll"][0] is roll
    assert dispatch.session_id in "\n".join(flatten_text(roll))
    assert not button(page, "COPY LATEST DISPATCH").disabled
    button(page, "COPY LATEST DISPATCH").on_click(None)
    assert page.clipboard == [dispatch.report]
    button(page, "EXPORT LATEST DISPATCH").on_click(None)
    assert not any(n.kind == "REPORT_ARCHIVED" for n in state.directorate.notices())
    worker, args = page.jobs.pop()
    worker(*args)
    assert (tmp_path / "directorate_cable_dispatch-fixture.txt").read_text(encoding="utf-8") == dispatch.report
    assert state.directorate.notices()[-1].kind == "REPORT_ARCHIVED"
    button(page, "HISTORY").on_click(None)
    assert state.proposal_history_open and not state.directorate_open


def test_system_checks_are_reachable_from_diagnostics_and_do_not_replace_the_desk():
    page, state = scene()
    button(page, "Ctrl+D Diagnostics").on_click(None)
    button(page, "SYSTEM CHECKS").on_click(None)
    assert state.directorate_boot_open and not state.directorate_open
    assert not state.diagnostics_drawer_open
    button(page, "CLOSE").on_click(None)
    button(page, "Ctrl+P DIRECTORATE").on_click(None)
    assert state.directorate_open and not state.directorate_boot_open


def test_arriving_report_has_its_own_refresh_and_stops_after_completion(monkeypatch):
    from types import SimpleNamespace
    from tests.helpers.gui_harness import make_gui_state
    state = make_gui_state()
    state.directorate_open = True
    dispatch = state.directorate.record_decision(decision())
    clock = {"now": dispatch.received_at}
    monkeypatch.setattr(gui.time, "monotonic", lambda: clock["now"])
    roll = gui._register_live_panel(state, "directorate_roll", lambda: build_dispatch_roll(state.directorate))
    offsets = iter([1.0, 3.2, 4.0])
    def wait(interval):
        assert interval == .2
        offset = next(offsets, None)
        if offset is None:
            return True
        clock["now"] = dispatch.received_at + offset
        return False
    state.ui_stopped = SimpleNamespace(wait=wait)
    updates = []
    gui._poll_directorate_roll(SimpleNamespace(update=lambda c: updates.append(c)), state)
    assert updates == [roll, roll]
    assert "END OF CABLE" in "\n".join(flatten_text(roll))
