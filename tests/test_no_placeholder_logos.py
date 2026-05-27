from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.logo_normalizer import read_normalized_logo
from ui.assets.registry import THEME_GRAPHIC_ASSETS


PLACEHOLDER_FRAGMENTS = (
    "E X C O M M   W A R   R O O M   T R I B U N A L",
    "A R A S A K A   E X E C U T I V E",
    "ADEPTUS MECHANICUS :: IMPERIAL COGITATOR TRIBUNAL",
    "[ SUPER EARTH COMMAND ]",
    "HELLDIVERS STRATEGIC VOTE UPLINK",
    "PLACEHOLDER",
    "MINIATURE",
)


def test_no_theme_uses_known_placeholder_logo_fragments() -> None:
    for theme_key, asset in THEME_GRAPHIC_ASSETS.items():
        logo = read_normalized_logo(asset.logo_path).text
        for fragment in PLACEHOLDER_FRAGMENTS:
            assert fragment not in logo, f"{theme_key} contains placeholder fragment {fragment!r}"


def test_no_theme_logo_can_shrink_below_registered_floor() -> None:
    for theme_key, asset in THEME_GRAPHIC_ASSETS.items():
        logo = read_normalized_logo(asset.logo_path)

        assert logo.width >= asset.expected_min_width, theme_key
        assert logo.height >= asset.expected_min_lines, theme_key


if __name__ == "__main__":
    test_no_theme_uses_known_placeholder_logo_fragments()
    test_no_theme_logo_can_shrink_below_registered_floor()
    print("test_no_placeholder_logos PASS")
