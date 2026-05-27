from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.telemetry_panel import build_telemetry_panel
from ui.themes.catalog import THEMES


def test_telemetry_panel_uses_no_internal_scroll_for_default_content() -> None:
    telemetry = {
        "latest": {
            "cpu": {"percent": 15},
            "ram": {"percent": 25},
            "disk": {"percent": 35},
            "gpu": {"status": "ready", "usage_percent": 45, "vram_percent": 55, "temperature_c": 65},
        },
        "history": {"cpu": [15, 16], "gpu": [45, 46]},
    }

    for theme in THEMES.values():
        panel = build_telemetry_panel(theme, telemetry)
        assert panel.content.scroll is None


if __name__ == "__main__":
    test_telemetry_panel_uses_no_internal_scroll_for_default_content()
    print("test_telemetry_no_scroll_required PASS")
