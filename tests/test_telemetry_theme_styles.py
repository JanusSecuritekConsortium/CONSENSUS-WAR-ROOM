from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.telemetry_panel import TELEMETRY_GRAPH_WIDTH, TELEMETRY_STYLE_NAMES, telemetry_graph_lines, themed_telemetry_graph


def test_each_theme_has_tactical_telemetry_style_label() -> None:
    for theme_key in ("military", "eva", "nerv", "wh40k", "helldivers", "arasaka", "janus"):
        assert theme_key in TELEMETRY_STYLE_NAMES
        lines = telemetry_graph_lines(theme_key, {"history": {"cpu": [1, 2], "gpu": [3, 4]}})
        assert lines[0] == TELEMETRY_STYLE_NAMES[theme_key]
        assert len(lines[1].split()[-1]) >= TELEMETRY_GRAPH_WIDTH


def test_theme_telemetry_graphs_use_wide_theme_specific_forms() -> None:
    assert themed_telemetry_graph("wh40k", [50]).startswith("[")
    assert "|" in themed_telemetry_graph("wh40k", [50])
    assert "=" in themed_telemetry_graph("helldivers", [50])
    assert "~" in themed_telemetry_graph("eva", [50])
    assert "#" in themed_telemetry_graph("arasaka", [50])


if __name__ == "__main__":
    test_each_theme_has_tactical_telemetry_style_label()
    test_theme_telemetry_graphs_use_wide_theme_specific_forms()
    print("test_telemetry_theme_styles PASS")
