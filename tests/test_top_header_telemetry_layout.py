from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for


def _header_telemetry_box(theme_key: str):
    header = build_layout_for(theme_key).content.controls[0]
    status_row = header.content.controls[1].content.controls[1]
    return status_row.controls[1]


def test_top_header_contains_live_telemetry_panel_for_all_themes() -> None:
    for theme_key in ("eva", "arasaka", "janus", "wh40k", "helldivers", "military"):
        telemetry_box = _header_telemetry_box(theme_key)
        text = "\n".join(control.value for control in telemetry_box.content.controls if hasattr(control, "value"))

        assert telemetry_box.data["role"] == "header_telemetry_panel"
        assert telemetry_box.width >= 420
        assert "LIVE TELEMETRY" in text
        assert any(token in text for token in ("CPU", "CORE SYNC", "MACHINE SPIRIT", "DEMOCRACY", "ASSET"))


if __name__ == "__main__":
    test_top_header_contains_live_telemetry_panel_for_all_themes()
    print("test_top_header_telemetry_layout PASS")
