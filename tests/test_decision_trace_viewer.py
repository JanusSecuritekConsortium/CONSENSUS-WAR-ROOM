from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.flet_app import build_decision_trace_viewer, create_gui_state, filter_decision_traces


def _flatten_text(control) -> list[str]:
    values: list[str] = []
    if hasattr(control, "value") and isinstance(control.value, str):
        values.append(control.value)
    if hasattr(control, "text") and isinstance(control.text, str):
        values.append(control.text)
    if hasattr(control, "label") and isinstance(control.label, str):
        values.append(control.label)
    if hasattr(control, "content") and control.content is not None:
        values.extend(_flatten_text(control.content))
    if hasattr(control, "controls"):
        for child in control.controls:
            values.extend(_flatten_text(child))
    return values


def test_filter_decision_traces_by_proposal_id() -> None:
    traces = [
        {"proposal_id": "alpha-1", "final_verdict": "APPROVED"},
        {"proposal_id": "beta-2", "final_verdict": "NO_CONSENSUS"},
    ]

    assert filter_decision_traces(traces, "alpha") == [traces[0]]
    assert filter_decision_traces(traces, "") == traces


def test_decision_trace_viewer_renders_filtered_traces() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    state.trace_filter = "beta"
    viewer = build_decision_trace_viewer(
        state,
        traces=[
            {"proposal_id": "alpha-1", "final_verdict": "APPROVED", "taxonomy": "technical"},
            {"proposal_id": "beta-2", "final_verdict": "NO_CONSENSUS", "taxonomy": "operational"},
        ],
    )
    text = "\n".join(_flatten_text(viewer))

    assert "DECISION TRACE VIEWER" in text
    assert "proposal_id filter" in text
    assert "beta-2" in text
    assert "NO_CONSENSUS" in text
    assert "alpha-1" not in text


if __name__ == "__main__":
    test_filter_decision_traces_by_proposal_id()
    test_decision_trace_viewer_renders_filtered_traces()
    print("test_decision_trace_viewer PASS")
