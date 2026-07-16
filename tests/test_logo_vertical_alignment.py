from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.registry import THEME_GRAPHIC_ASSETS
from ui.components.header import logo_runtime_diagnostics


def test_logo_renderers_fit_their_resolved_regions() -> None:
    for theme_key in THEME_GRAPHIC_ASSETS:
        diagnostics = logo_runtime_diagnostics(theme_key)

        assert diagnostics["visible_artwork_width"] <= diagnostics["logo_region_width"], theme_key
        assert diagnostics["visible_artwork_height"] <= diagnostics["logo_region_height"], theme_key
        assert min(diagnostics["clearances"]) >= 0, theme_key


if __name__ == "__main__":
    test_logo_renderers_fit_their_resolved_regions()
    print("test_logo_vertical_alignment PASS")
