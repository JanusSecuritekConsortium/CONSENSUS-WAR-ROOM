from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ui.flet_app as flet_app
from tests.helpers.gui_harness import make_gui_state


def test_diagnostics_open_uses_cached_snapshot_fields_when_available() -> None:
    state = make_gui_state("eva")
    state.runtime_snapshot_cache.update(
        {
            "telemetry": {"latest": {}, "history": {"cpu": [], "gpu": []}},
            "proposal_history_status": {"recent_count": 1, "last_proposal_id": "cached"},
            "proposal_lifecycle_summary": {"decided_total": 1, "no_consensus_total": 0, "escalated_total": 0, "error_total": 0},
            "latest_verdict_export": {"latest_json": "cached_verdict.json"},
            "latest_dossier_export": {"latest_json": "cached_dossier.json"},
        }
    )
    originals = (
        flet_app.proposal_history_status,
        flet_app.proposal_lifecycle_summary,
        flet_app.latest_verdict_export_status,
        flet_app.latest_dossier_export_status,
    )
    try:
        flet_app.proposal_history_status = lambda: (_ for _ in ()).throw(AssertionError("history called"))
        flet_app.proposal_lifecycle_summary = lambda: (_ for _ in ()).throw(AssertionError("lifecycle called"))
        flet_app.latest_verdict_export_status = lambda: (_ for _ in ()).throw(AssertionError("verdict called"))
        flet_app.latest_dossier_export_status = lambda: (_ for _ in ()).throw(AssertionError("dossier called"))

        assert flet_app.set_diagnostics_drawer_open(state, True) is True
    finally:
        (
            flet_app.proposal_history_status,
            flet_app.proposal_lifecycle_summary,
            flet_app.latest_verdict_export_status,
            flet_app.latest_dossier_export_status,
        ) = originals


if __name__ == "__main__":
    test_diagnostics_open_uses_cached_snapshot_fields_when_available()
    print("test_diagnostics_cached_snapshot PASS")
