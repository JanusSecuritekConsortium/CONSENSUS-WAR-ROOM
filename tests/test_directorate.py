from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace

import pytest

from config.nodes import DEFAULT_NODES
from config.runtime import RuntimeConfig
from core.directorate import ACTIVITY_LIMIT, Directorate, read_preferences, write_preferences
from core.export.cable import export_cable, render_cable, retrieved_sources
from core.models import FinalVerdict, TribunalResult, Vote, VoteValue
from ui import flet_app as gui
from ui.directorate import build_activity, build_boot, contrast_ratio, status_color
from ui.themes.catalog import THEMES
from ui.visual_checks import flatten_text


def result_fixture(**updates):
    return replace(TribunalResult(
        query="Assess the proposed operation.", verdict=FinalVerdict.NO_CONSENSUS,
        confidence=.9, reason="Explicit evaluation: more evidence required.",
        votes={"BELLATOR": Vote("BELLATOR", "security", VoteValue.DENY, .9,
                                "MODEL_PRIVATE_REASONING_MARKER", model="fixture-model", backend="fixture",
                                raw_response="RAW_PRIVATE_MARKER", unresolved_disagreements=["Source reliability unresolved."])},
        vote_distribution={"DENY": 1}, quorum_met=False, review_triggers=["quorum"],
        session_id="fixture-session", theme="military", deliberation_complete=False,
    ), **updates)


def make_state():
    return gui.GuiState(theme_key="military", config=RuntimeConfig(backend="msty-local"), nodes=DEFAULT_NODES)


def stub_startup(monkeypatch, tmp_path, status):
    history = tmp_path / "history.json"
    session = tmp_path / "session.json"
    history.write_text("[]")
    session.write_text('{"sessions": []}')
    monkeypatch.setattr(gui, "HISTORY_PATH", history)
    monkeypatch.setattr("core.paths.SESSION_MEMORY_PATH", session)
    monkeypatch.setattr(gui, "refresh_gui_status", lambda state: setattr(state, "provider_status", status[0]))
    monkeypatch.setattr(gui, "refresh_telemetry_for_gui", lambda state: {})
    monkeypatch.setattr(gui, "get_aurelius_runtime", lambda: SimpleNamespace(status=lambda: {}))
    return history, session


def test_bounded_thread_safe_events_and_immutable_snapshots():
    journal = Directorate()
    def producer(index):
        for n in range(200):
            journal.emit(f"worker-{index}", "MODEL_STARTED", "RUNNING", "Request dispatched", str(n))
            journal.events()
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(producer, range(8)))
    snapshot = journal.events()
    assert len(snapshot) == ACTIVITY_LIMIT
    journal.emit("UI", "COPIED", "AVAILABLE", "Copied")
    assert snapshot[-1].kind == "MODEL_STARTED"
    assert len(journal.events()) == ACTIVITY_LIMIT


def test_no_ready_before_all_checks_complete():
    journal = Directorate()
    assert journal.startup_status() == "CHECKING"
    for component in ("CONFIG", "INTERFACE", "PROVIDER", "MEMORY"):
        journal.emit(component, "STARTUP_CHECK", "AVAILABLE", "Checked", check=True)
    assert journal.startup_status() == "CHECKING"
    journal.emit("AURELIUS", "STARTUP_CHECK", "AVAILABLE", "Runtime", check=True)
    assert journal.startup_status() == "READY"
    journal.emit("PROVIDER", "STARTUP_CHECK", "FAILED", "Unavailable", check=True)
    assert journal.startup_status() == "DEGRADED"
    journal.emit("CONFIG", "STARTUP_CHECK", "FAILED", "Unreadable", check=True)
    assert journal.startup_status() == "FAILED"


def test_available_offline_and_retry_preserve_failure(monkeypatch, tmp_path):
    statuses = [{"status": "degraded", "provider": {"status": "offline", "error": "SECRET_ENDPOINT"}}]
    stub_startup(monkeypatch, tmp_path, statuses)
    state = make_state()
    state.directorate.emit("CONFIG", "STARTUP_CHECK", "AVAILABLE", "Loaded", check=True)
    state.directorate.emit("INTERFACE", "STARTUP_CHECK", "AVAILABLE", "Mounted", check=True)
    updates = []
    gui.initialize_directorate(state, lambda: updates.append(state.directorate.startup_status()))
    assert state.directorate.startup_status() == "DEGRADED"
    assert not state.directorate_busy
    statuses[0] = {"status": "ready", "provider": {"status": "ready"}}
    gui.initialize_directorate(state)
    assert state.directorate.startup_status() == "READY"
    assert any(e.component == "PROVIDER" and e.status == "FAILED" for e in state.directorate.events())
    assert "SECRET_ENDPOINT" not in str(state.directorate.events())
    assert "CHECKING" in updates


def test_mock_provider_never_claims_live_availability(monkeypatch, tmp_path):
    statuses = [{"status": "ready", "provider": {"status": "ready"}}]
    stub_startup(monkeypatch, tmp_path, statuses)
    state = make_state()
    state.config.backend = "mock"
    gui.initialize_directorate(state)
    provider = next(e for e in state.directorate.checks() if e.component == "PROVIDER")
    assert provider.status == "DEGRADED"
    assert "SIMULATION ONLY" in provider.summary


def test_config_failure_retries_without_replacing_corrupt_file(monkeypatch, tmp_path):
    statuses = [{"status": "ready", "provider": {"status": "ready"}}]
    stub_startup(monkeypatch, tmp_path, statuses)
    config = tmp_path / "config.json"
    config.write_text("{invalid")
    state = make_state()
    state.directorate_config_failed = True
    state.directorate_config_path = config
    gui.initialize_directorate(state)
    assert state.directorate_config_failed and not state.directorate_busy
    assert state.directorate.startup_status() == "FAILED"
    assert config.read_text() == "{invalid"
    config.write_text('{"backend": "msty-local"}')
    gui.initialize_directorate(state)
    assert not state.directorate_config_failed
    assert any(e.component == "CONFIG" and e.status == "FAILED" for e in state.directorate.events())


def test_desktop_mounts_before_scheduling_provider_checks(monkeypatch):
    state = make_state()
    monkeypatch.setattr(gui, "ensure_flet_desktop_runtime", lambda: None)
    monkeypatch.setattr(gui, "create_gui_state", lambda *a, **kw: state if kw["initialize"] is False else pytest.fail("Synchronous initialization"))
    order = []
    monkeypatch.setattr(gui, "_render_page", lambda p, s: order.append("mounted"))
    monkeypatch.setattr(gui, "initialize_directorate", lambda *a: pytest.fail("Provider check before worker scheduling"))
    page = SimpleNamespace(run_thread=lambda callback: order.append("scheduled"))
    monkeypatch.setattr(gui.ft, "app", lambda target: target(page))
    gui.run_flet_gui("military", state.config)
    assert order == ["mounted", "scheduled"]
    assert not state.directorate_boot_open


@pytest.mark.parametrize("theme", list(THEMES.values()), ids=list(THEMES))
def test_theme_adapters_contrast_collapsing_and_reduced_motion(theme):
    journal = Directorate()
    journal.emit("PROVIDER", "STARTUP_CHECK", "RUNNING", "Checking", check=True)
    journal.emit("TRIBUNAL", "ASSESSMENT_FAILED", "FAILED", "Assessment unavailable")
    for status in ("PENDING", "RUNNING", "AVAILABLE", "DEGRADED", "FAILED"):
        assert contrast_ratio(status_color(theme, status), theme.surface_color) >= 4.5
    full = flatten_text(build_activity(theme, journal, False))
    collapsed = flatten_text(build_activity(theme, journal, True))
    assert any("Assessment unavailable" in text for text in full)
    assert not any("Checking" in text for text in full)
    assert not any("Assessment unavailable" in text for text in collapsed)
    boot = build_boot(theme, journal, True, reduced_motion=True)
    progress = boot.content.controls[2]
    assert progress.value == 0  # no indeterminate movement


def test_preferences_round_trip_and_invalid_input(tmp_path):
    path = tmp_path / "prefs.json"
    write_preferences({"reduced_motion": True, "animation": False, "collapsed": True, "cable": True}, path)
    assert read_preferences(path)["reduced_motion"]
    path.write_text('{"reduced_motion":"false", "unknown":true}')
    assert read_preferences(path) == {}
    path.write_text("[]")
    assert read_preferences(path) == {}


def test_cable_complete_missing_and_no_raw_reasoning(tmp_path):
    result = result_fixture()
    sources = retrieved_sources({"external_reference_context": {"matches": [
        {"title": "Fixture source", "source_url": "https://example.org/evidence", "page": 4, "retrieved_at": "2026-10-06"},
        {"title": "Local path", "source_url": "G:/private.txt"},
    ]}})
    cable = render_cable(result, sources)
    assert "fixture-session" in cable and "https://example.org/evidence" in cable
    assert "page 4" in cable and "Source reliability unresolved" in cable
    assert "MODEL_PRIVATE_REASONING_MARKER" not in cable and "RAW_PRIVATE_MARKER" not in cable
    assert "90%" not in cable and "calibrated" in cable
    assert "G:/private.txt" not in cable
    assert export_cable(result, sources, tmp_path).read_text(encoding="utf-8") == cable
    missing = render_cable(result_fixture(query="", votes={}, timestamp="", session_id=""))
    assert "Not available" in missing
    assert "No assessment available" in render_cable(None)


def test_cable_export_failure_is_not_a_receipt(tmp_path):
    file = tmp_path / "file"
    file.write_text("existing")
    with pytest.raises(OSError):
        export_cable(result_fixture(), output_dir=file)
    assert file.read_text() == "existing"


def test_reference_provenance_covers_real_feed_and_local_memory():
    assert retrieved_sources({"external_reference_context": None, "bellator_context_packet": None,
                              "aeternum_data_packet": {"items": None}, "memory_context": None}) == []
    sources = retrieved_sources({
        "bellator_context_packet": {
            "rss_intelligence": {"items": [{"title": "RSS", "url": "https://example.org/rss", "fetched_at": "2026-10-06"}]},
            "real_data_layer": {"items": [{"title": "Feed", "url": "https://example.org/feed"}]},
        },
        "aeternum_data_packet": {"items": [{"title": "Market", "url": "https://example.org/market"}]},
        "memory_context": {"items": [{"session_id": "prior-fixture", "timestamp": "2026-10-01", "proposal": "PRIVATE_QUERY_MARKER"}]},
    })
    cable = render_cable(result_fixture(), sources)
    assert all(value in cable for value in ("https://example.org/rss", "https://example.org/feed", "https://example.org/market", "prior-fixture"))
    assert "PRIVATE_QUERY_MARKER" not in cable


def test_earlier_explicit_dissent_and_model_substitution_are_retained():
    result = result_fixture(deliberation_transcript=[{
        "agent_id": "BELLATOR", "round": 2, "model": "earlier-model",
        "peer_responses": [{"stance": "reject", "peer": "AETERNUM", "reason": "Explicit objection"}],
    }])
    cable = render_cable(result)
    assert "earlier-model" in cable and "Explicit objection" in cable
    assert "may have been resolved" in cable


def test_background_deliberation_events_follow_callbacks_not_completion(monkeypatch):
    state = make_state()
    state.config.backend = "mock"
    state.reduced_motion = True
    monkeypatch.setattr(gui, "create_proposal", lambda **kwargs: {"proposal_id": "fixture"})
    monkeypatch.setattr(gui, "build_context_packet", lambda query: {"items": [], "prior_decisions_used": 0})
    monkeypatch.setattr(gui, "record_result", lambda result: None)
    monkeypatch.setattr(gui, "log_decision_trace", lambda result: None)
    monkeypatch.setattr(gui, "read_latest_trace", lambda: {})
    monkeypatch.setattr(gui, "link_decision_trace_to_proposal", lambda *a, **kw: {})
    monkeypatch.setattr(gui, "upsert_session_record", lambda record: None)
    monkeypatch.setattr(gui, "read_recent_log_events", lambda: [])
    monkeypatch.setattr(gui, "read_recent_decisions", lambda: [])
    monkeypatch.setattr(gui, "reveal_text_with_cursor_sync", lambda text, **kw: kw["on_update"](text))
    monkeypatch.setattr("core.voting.orchestrator.build_aeternum_data_enrichment", lambda *a, **kw: {})
    monkeypatch.setattr("core.voting.orchestrator.VotingOrchestrator._build_bellator_context_packet", lambda *a: {})
    # Use the actual three-round orchestrator and mock backend on a worker.
    observed = []
    def capture():
        observed.append((dict(state.monolith_statuses), len(state.deliberation_records)))
    with ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(gui.submit_proposal_live_for_gui, state, "Evaluate the risky operation.",
                             on_update=capture).result(timeout=10)
    events = state.directorate.events()
    assert sum(e.kind == "MODEL_STARTED" for e in events) == 9
    assert sum(e.kind == "ASSESSMENT_RECEIVED" for e in events) == 9
    assert len(state.deliberation_records) == 9
    assert {r["round"] for r in state.deliberation_records} == {1, 2, 3}
    assert {r["phase"] for r in state.deliberation_records} == {"assessment", "critique", "revision"}
    assert not state.deliberation_pending
    assert all(r["simulation"] for r in state.deliberation_records)
    assert state.monolith_feedback["ARBITER"][0] == result.verdict.value
    assert any("THINKING" in statuses.values() and "QUEUED" in statuses.values() for statuses, count in observed)
    assert set(range(10)) <= {count for statuses, count in observed}
    assert all(e.session_id == result.session_id for e in events)
    assert not any(e.kind == "CONTRADICTION_FOUND" for e in events)
    assert not any(e.kind == "REPORT_ARCHIVED" for e in events)
    assert state.consensus_locked == (result.verdict not in {FinalVerdict.NO_CONSENSUS, FinalVerdict.ESCALATE, FinalVerdict.ERROR})


def test_no_consensus_does_not_emit_or_display_a_consensus_lock(monkeypatch):
    state = make_state()
    state.config.backend = "mock"
    monkeypatch.setattr(gui, "create_proposal", lambda **kwargs: {"proposal_id": "fixture"})
    monkeypatch.setattr(gui, "build_context_packet", lambda query: {})
    vote = result_fixture().votes["BELLATOR"]
    vote.validation_errors = ["runtime_failure"]
    orchestrator = SimpleNamespace(cast_votes=lambda *a, **kw: {"BELLATOR": vote},
                                   attach_audit=lambda r: None)
    monkeypatch.setattr(gui, "VotingOrchestrator", lambda *a: orchestrator)
    monkeypatch.setattr(gui, "record_result", lambda result: None)
    monkeypatch.setattr(gui, "log_decision_trace", lambda result: None)
    monkeypatch.setattr(gui, "link_decision_trace_to_proposal", lambda *a, **kw: {})
    monkeypatch.setattr(gui, "upsert_session_record", lambda record: None)
    monkeypatch.setattr(gui, "read_latest_trace", lambda: {})
    monkeypatch.setattr(gui, "read_recent_log_events", lambda: [])
    monkeypatch.setattr(gui, "read_recent_decisions", lambda: [])
    locks = []
    monkeypatch.setattr(gui, "reveal_text_with_cursor_sync", lambda text, **kw: locks.append(kw["lock_text"]))
    result = gui.submit_proposal_live_for_gui(state, "Evaluate operation.", skip_animations=True)
    assert result.verdict == FinalVerdict.NO_CONSENSUS
    assert not state.consensus_locked
    assert locks == ["[VERDICT RECORDED]"]
    assert not any(e.kind == "CONSENSUS_REACHED" for e in state.directorate.events())


def test_reduced_motion_stops_animation_without_stopping_observation(monkeypatch):
    state = make_state()
    state.reduced_motion = True
    state.cursor_visible = True
    monkeypatch.setattr(gui, "detect_proposal_file_change", lambda value: (True, 42))
    gui.advance_war_room_activity(state)
    assert not state.cursor_visible and state.pulse_index == 0
    assert state.proposal_file_mtime == 42


def test_narrow_layout_scrolls_without_shrinking_controls():
    from tests.helpers.gui_harness import make_gui_state, noop
    state = make_gui_state()
    layout = gui.build_gui_layout(state, noop, noop, noop, noop, noop, viewport_width=850)
    body = layout.content.controls[1].content
    assert body.scroll == gui.ft.ScrollMode.AUTO
    assert [control.width for control in body.controls] == [340, 640, 340]
    assert all(control.expand is None for control in body.controls)


def test_boot_invalid_configuration_keeps_desktop_retry(monkeypatch, tmp_path):
    from tools import boot
    path = tmp_path / "config.json"
    path.write_text("[]")
    monkeypatch.setattr(boot, "build_dependency_report", lambda: {"missing_required": []})
    monkeypatch.setattr(boot, "print_human_report", lambda report: None)
    monkeypatch.setattr(boot, "health_check", lambda *a: pytest.fail("Provider probe before desktop"))
    launched = []
    assert boot.run_boot(config_path=path, launch_gui=lambda *a, **kw: launched.append(kw)) == 0
    assert launched[0]["startup_config_error"]
    assert path.read_text() == "[]"


def test_cable_buttons_use_clipboard_and_export_worker(monkeypatch, tmp_path):
    from tools.gui_smoke_check import SmokePage
    class Page(SmokePage):
        def __init__(self):
            super().__init__()
            self.clipboard = []
            self.jobs = []
        def update(self, *controls):
            self.updated += 1
        def set_clipboard(self, text):
            self.clipboard.append(text)
        def run_thread(self, handler, *args):
            self.jobs.append((handler, args))
    state = make_state()
    state.current_result = result_fixture()
    state.proposal_input_text = "Keep the operator draft"
    monkeypatch.setattr(gui, "save_directorate_preferences", lambda state: None)
    monkeypatch.setattr(gui, "export_cable", lambda result, sources: export_cable(result, sources, tmp_path))
    page = Page()
    gui._render_page(page, state)
    def find_button(label):
        def walk(control):
            yield control
            if getattr(control, "content", None) is not None:
                yield from walk(control.content)
            for child in getattr(control, "controls", []) or []:
                yield from walk(child)
        return next(c for root in page.controls for c in walk(root)
                    if isinstance(c, gui.ft.TextButton) and c.text == label)
    find_button("CABLE VIEW").on_click(None)
    assert state.directorate_cable and state.proposal_input_text == "Keep the operator draft"
    find_button("COPY CABLE").on_click(None)
    assert page.clipboard == [render_cable(state.current_result, [])]
    find_button("EXPORT CABLE").on_click(None)
    assert not any(e.kind == "REPORT_ARCHIVED" for e in state.directorate.events())
    worker, args = page.jobs.pop()
    worker(*args)
    assert any(e.kind == "REPORT_ARCHIVED" for e in state.directorate.events())
    assert (tmp_path / "directorate_cable_fixture-session.txt").exists()
    def fail_export(*args):
        raise OSError("PRIVATE_PATH_MARKER")
    monkeypatch.setattr(gui, "export_cable", fail_export)
    find_button("EXPORT CABLE").on_click(None)
    worker, args = page.jobs.pop()
    worker(*args)
    assert state.directorate.events()[-1].kind == "REPORT_EXPORT_FAILED"
    assert "PRIVATE_PATH_MARKER" not in str(state.directorate.events())


def test_cli_gui_config_retry_preserves_explicit_overrides(monkeypatch, tmp_path):
    from core import cli
    path = tmp_path / "config.json"
    path.write_text("{invalid")
    monkeypatch.setattr("sys.argv", ["main.py", "--gui", "--config", str(path), "--theme", "JANUS", "--backend", "mock"])
    launched = []
    monkeypatch.setattr(gui, "run_flet_gui", lambda *args, **kwargs: launched.append((args, kwargs)))
    cli.main()
    args, kwargs = launched[0]
    assert args[0] == "janus" and kwargs["startup_config_error"]
    path.write_text('{"backend": "msty-local"}')
    assert kwargs["startup_config_loader"]().backend == "mock"
