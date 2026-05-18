from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.components.status_panel import build_status_panel
from ui.components.verdict_panel import build_verdict_panel
from ui.themes.catalog import THEMES


def _flatten_text(control) -> list[str]:
    values: list[str] = []
    if hasattr(control, "value") and isinstance(control.value, str):
        values.append(control.value)
    if hasattr(control, "content") and control.content is not None:
        values.extend(_flatten_text(control.content))
    if hasattr(control, "controls"):
        for child in control.controls:
            values.extend(_flatten_text(child))
    return values


def test_status_panel_shows_memory_indicators() -> None:
    panel = build_status_panel(
        THEMES["eva"],
        {"status": "ready", "provider": {"status": "ready", "model_count": 3}},
        "AVAILABLE",
        session_memory_status="ACTIVE",
        context_retrieval_status="ACTIVE",
        prior_decisions_used=2,
        current_session_id="abc123",
    )
    text = "\n".join(_flatten_text(panel))

    assert "SESSION MEMORY: ACTIVE" in text
    assert "CONTEXT RETRIEVAL: ACTIVE" in text
    assert "PRIOR DECISIONS USED: 2" in text
    assert "CURRENT SESSION: abc123" in text


def test_verdict_panel_shows_context_used() -> None:
    panel = build_verdict_panel(
        THEMES["eva"],
        None,
        prior_decisions_used=3,
        context_summary="prior context",
    )
    text = "\n".join(_flatten_text(panel))

    assert "Context used: 3 prior decisions" in text
    assert "prior context" in text


if __name__ == "__main__":
    test_status_panel_shows_memory_indicators()
    test_verdict_panel_shows_context_used()
    print("test_gui_memory_indicators PASS")
