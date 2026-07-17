from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.header import logo_runtime_diagnostics


BASELINE_71333 = {
    "janus": {"region": (435.160, 162.000), "art": (275.280, 48.000)},
    "arasaka": {"region": (643.280, 162.000), "art": (555.520, 56.000)},
    "eva": {"region": (162.000, 162.000), "art": (148.800, 150.000)},
    "wh40k": {"region": (162.000, 162.000), "art": (150.000, 145.711)},
    "helldivers": {"region": (435.160, 162.000), "art": (355.880, 119.000)},
    "military": {"region": (745.000, 162.000), "art": (446.400, 81.000)},
}


def _min_clearance(theme_key: str) -> float:
    return min(logo_runtime_diagnostics(theme_key, header_width=1920)["clearances"])


def test_logo_geometry_matches_v71334_theme_policy() -> None:
    diagnostics = {
        theme_key: logo_runtime_diagnostics(theme_key, header_width=1920)
        for theme_key in BASELINE_71333
    }

    assert diagnostics["military"]["logo_region_width"] <= BASELINE_71333["military"]["region"][0] * 0.80
    assert diagnostics["military"]["visible_artwork_width"] <= BASELINE_71333["military"]["art"][0] * 0.90
    assert _min_clearance("military") >= 6

    assert diagnostics["janus"]["logo_region_width"] <= BASELINE_71333["janus"]["region"][0] * 0.80
    assert _min_clearance("janus") >= 8

    assert diagnostics["helldivers"]["logo_region_width"] < BASELINE_71333["helldivers"]["region"][0]
    assert _min_clearance("helldivers") >= 8

    assert diagnostics["arasaka"]["logo_region_width"] == BASELINE_71333["arasaka"]["region"][0]
    assert diagnostics["arasaka"]["visible_artwork_width"] >= (BASELINE_71333["arasaka"]["art"][0] * 1.12) - 0.01
    assert diagnostics["arasaka"]["visible_artwork_height"] >= (BASELINE_71333["arasaka"]["art"][1] * 1.12) - 0.01
    assert _min_clearance("arasaka") >= 8

    assert diagnostics["eva"]["logo_region_width"] == 185.0
    assert diagnostics["eva"]["visible_artwork_width"] >= BASELINE_71333["eva"]["art"][0] * 1.15
    assert _min_clearance("eva") >= 6

    assert diagnostics["wh40k"]["logo_region_width"] == 185.0
    assert diagnostics["wh40k"]["visible_artwork_width"] >= BASELINE_71333["wh40k"]["art"][0] * 1.07
    assert diagnostics["wh40k"]["visible_artwork_height"] >= BASELINE_71333["wh40k"]["art"][1] * 1.07
    assert _min_clearance("wh40k") >= 5


if __name__ == "__main__":
    test_logo_geometry_matches_v71334_theme_policy()
    print("test_header_logo_geometry_v71334 PASS")
