"""The history line naming who answered each vote: company or local model, backup and not-asked voters."""
from __future__ import annotations

import json

from config.names import AETERNUM, BELLATOR, RATIONALIS
from core.voting.sources import vote_sources, vote_sources_for_file


def turn(agent, **fields):
    return {"agent_id": agent, "status": "completed", "model_fallback": False, "model_fallback_reason": "", **fields}


VERDICT = {
    "votes": {
        RATIONALIS: {"model": "claude-cli:sonnet", "backend": "online:claude-cli"},
        AETERNUM: {"model": r"G:\models\yi-34b-chat.Q4_K_M.gguf", "backend": "msty-local"},
        BELLATOR: {"model": "deepseek:deepseek-chat", "backend": "online:deepseek"},
    },
    "deliberation_transcript": [
        turn(RATIONALIS),
        turn(AETERNUM, model_fallback=True, model_fallback_reason="online_model_failed"),
        turn(BELLATOR, model_fallback=True, model_fallback_reason="online_model_failed"),
    ],
}


def test_each_vote_names_its_company_or_local_model_and_any_backup():
    assert vote_sources(VERDICT) == (
        "BELLATOR DeepSeek · API (backup) | AETERNUM local yi-34b-chat.Q4_K_M (online failed) | "
        "RATIONALIS Claude · subscription"
    )


def test_simulations_failures_and_unasked_voters_are_named():
    verdict = {
        "votes": {
            BELLATOR: {"model": "mixtral", "backend": "failed", "validation_errors": ["runtime_failure:RuntimeError"]},
            AETERNUM: {"model": "yi", "backend": "not-asked", "validation_errors": ["not_asked_after_failure"]},
            RATIONALIS: {"model": "mock", "backend": "mock"},
        },
        "deliberation_transcript": [],
    }
    assert vote_sources(verdict) == "BELLATOR failed | AETERNUM not asked | RATIONALIS simulation"
    assert vote_sources({}) == ""


def test_verdict_files_are_read_and_bad_ones_are_skipped(tmp_path):
    path = tmp_path / "verdict.json"
    path.write_text(json.dumps(VERDICT), encoding="utf-8")
    assert vote_sources_for_file(str(path)).startswith("BELLATOR DeepSeek")
    path.write_text("not json", encoding="utf-8")
    import os
    os.utime(path, (1, 1))
    assert vote_sources_for_file(str(path)) == ""
    assert vote_sources_for_file(str(tmp_path / "missing.json")) == ""
    assert vote_sources_for_file(None) == ""


def test_history_rows_show_who_answered(tmp_path):
    import flet as ft
    from tests.helpers.gui_harness import make_gui_state
    from ui.flet_app import build_proposal_history_viewer

    path = tmp_path / "verdict.json"
    path.write_text(json.dumps(VERDICT), encoding="utf-8")
    proposals = [{"proposal_id": "p1", "status": "DECIDED", "title": "Move backups",
                  "linked_verdict_export_json": str(path)}, {"proposal_id": "p2", "status": "DRAFT"}]
    view = build_proposal_history_viewer(make_gui_state("janus"), proposals=proposals)

    def walk(control):
        yield control
        for child in [getattr(control, "content", None), *(getattr(control, "controls", None) or [])]:
            if isinstance(child, ft.Control):
                yield from walk(child)
    lines = [c.value for c in walk(view) if c.data == {"role": "proposal_vote_sources"}]
    assert lines == ["Answered by: " + vote_sources(VERDICT)]
