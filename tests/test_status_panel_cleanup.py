from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.status_panel import build_status_panel
from ui.themes.catalog import THEMES


def _flatten_text(control) -> list[str]:
    values: list[str] = []
    if hasattr(control, "value") and isinstance(control.value, str):
        values.append(control.value)
    if hasattr(control, "content") and control.content is not None:
        values.extend(_flatten_text(control.content))
    for child in getattr(control, "controls", []) or []:
        values.extend(_flatten_text(child))
    return values


def test_status_panel_is_grouped_by_operational_sections() -> None:
    panel = build_status_panel(
        THEMES["military"],
        {"status": "ready", "provider": {"status": "ready", "base_url": "http://localhost:11454"}},
        "AVAILABLE",
        lifecycle_state="IDLE",
    )
    text = "\n".join(_flatten_text(panel))

    for label in ("PROVIDER", "MEMORY", "CONTEXT", "LIFECYCLE"):
        assert label in text
    assert "ENDPOINT: http://localhost:11454" in text
    assert "SESSION MEMORY:" in text


if __name__ == "__main__":
    test_status_panel_is_grouped_by_operational_sections()
    print("test_status_panel_cleanup PASS")
