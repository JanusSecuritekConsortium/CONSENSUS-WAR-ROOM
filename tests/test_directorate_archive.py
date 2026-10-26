from concurrent.futures import ThreadPoolExecutor

from core.directorate import Directorate, DISPATCH_LIMIT
from core.export.cable import render_cable
from tests.test_directorate_dispatch_desk import decision
from tests.test_directorate_submit_controls import scene
from tests.test_directorate_interaction import button, walk
from ui.visual_checks import flatten_text
from ui.directorate import build_dispatch_roll


def test_archive_survives_restart_searches_evicted_reports_and_freezes_public_text(tmp_path):
    path = tmp_path / "dispatches.sqlite3"
    journal = Directorate(archive_path=path)
    result = decision("old-dispatch")
    result.query = "Archive original 50%_budget"
    result.votes["BELLATOR"].raw_response = "PRIVATE_RAW_MARKER"
    first = journal.record_decision(result)
    result.query = "Changed live proposal"
    for n in range(DISPATCH_LIMIT + 2):
        journal.record_decision(decision(str(n)))
    restarted = Directorate(archive_path=path)
    assert len(restarted.dispatches()) == DISPATCH_LIMIT
    found = restarted.search_dispatches("50%_budget")
    assert len(found) == 1 and found[0].report == first.report
    assert "PRIVATE_RAW_MARKER" not in found[0].report
    assert "Changed live" not in found[0].report and found[0].received_at == 0
    assert not restarted.search_dispatches("no such subject")
    assert restarted.record_decision(decision("next")).number > first.number + DISPATCH_LIMIT
    text = "\n".join(flatten_text(build_dispatch_roll(restarted, query="50%_budget")))
    assert "Archive original" in text and "END OF CABLE" in text


def test_independent_archive_writers_deduplicate_session_and_allocate_unique_numbers(tmp_path):
    path = tmp_path / "dispatches.sqlite3"
    first, second = Directorate(archive_path=path), Directorate(archive_path=path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        written = list(pool.map(lambda pair: pair[0].record_decision(decision(pair[1])), [(first, "same"), (second, "same")]))
    assert written[0].number == written[1].number
    assert len(Directorate(archive_path=path).dispatches()) == 1


def test_corrupt_archive_is_preserved_and_session_reports_remain_available(tmp_path):
    path = tmp_path / "dispatches.sqlite3"
    original = b"corrupt archive preserve me"
    path.write_bytes(original)
    journal = Directorate(archive_path=path)
    assert path.read_bytes() == original and journal.archive_path is None
    assert journal.notices()[-1].kind == "DISPATCH_ARCHIVE_FAILED"
    journal.record_decision(decision())
    assert journal.dispatches() and path.read_bytes() == original


def test_vote_development_reports_changes_and_stated_reasons_without_private_output():
    result = decision()
    result.deliberation_transcript = [
        {"agent_id": "BELLATOR", "phase": "assessment", "vote": "DENY", "raw_response": "PRIVATE_RAW"},
        {"agent_id": "BELLATOR", "phase": "critique", "vote": "CONDITIONAL", "vote_change_reason": "Audit condition accepted. <think>PRIVATE_THOUGHT</think>"},
        {"agent_id": "BELLATOR", "phase": "revision", "vote": "APPROVE", "vote_change_reason": "Rollback confirmed."},
    ]
    text = render_cable(result)
    assert "assessment: DENY -> critique: CONDITIONAL -> revision: APPROVE" in text
    assert "Audit condition accepted." in text and "Rollback confirmed." in text
    assert "PRIVATE_" not in text


def test_archive_search_updates_reader_without_unmounting_search_field(tmp_path):
    page, state = scene()
    state.directorate = Directorate(archive_path=tmp_path / "dispatches.sqlite3")
    one, two = decision("one"), decision("two")
    one.query, two.query = "Unique Alpha proposal", "Unique Beta proposal"
    state.directorate.record_decision(one)
    state.directorate.record_decision(two)
    button(page, "Ctrl+P DIRECTORATE").on_click(None)
    field = next(c for root in page.overlay for c in walk(root) if c.data == {"role": "directorate_archive_search"})
    field.value = "Unique Alpha"
    from types import SimpleNamespace
    field.on_submit(SimpleNamespace(control=field))
    assert state.directorate_search == "Unique Alpha"
    assert field is next(c for root in page.overlay for c in walk(root) if c.data == {"role": "directorate_archive_search"})
    roll = state.live_panels["directorate_roll"][0]
    text = "\n".join(flatten_text(roll))
    assert "Unique Alpha" in text and "Unique Beta" not in text
