from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for
from ui.components.header import HEADER_TELEMETRY_FLEX


def _header_telemetry_box(theme_key: str):
    header = build_layout_for(theme_key).content.controls[0]
    status_row = header.content.controls[1].content.controls[1]
    return status_row.controls[1]


def _walk(control):
    yield control
    content = getattr(control, "content", None)
    if content is not None:
        yield from _walk(content)
    for child in getattr(control, "controls", []) or []:
        yield from _walk(child)


def test_top_header_contains_live_telemetry_panel_for_all_themes() -> None:
    primary_tokens = {
        "eva": "MELCHIOR",
        "arasaka": "ASSET LOAD",
        "janus": "CPU",
        "wh40k": "MACHINE SPIRIT",
        "helldivers": "DEMOCRACY",
        "military": "TACTICAL LOAD MATRIX",
    }

    for theme_key, primary_token in primary_tokens.items():
        telemetry_box = _header_telemetry_box(theme_key)
        text = "\n".join(control.value for control in _walk(telemetry_box) if hasattr(control, "value"))

        assert telemetry_box.data["role"] == "header_telemetry_panel"
        assert telemetry_box.width is None
        assert telemetry_box.expand == HEADER_TELEMETRY_FLEX
        assert telemetry_box.clip_behavior is not None
        assert "LIVE TELEMETRY" in text
        assert primary_token in text


if __name__ == "__main__":
    test_top_header_contains_live_telemetry_panel_for_all_themes()
    print("test_top_header_telemetry_layout PASS")
