from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.logo_normalizer import read_normalized_logo
from ui.assets.registry import THEME_GRAPHIC_ASSETS


def test_helldivers_ascii_is_flat_winged_command_mark() -> None:
    logo = read_normalized_logo(THEME_GRAPHIC_ASSETS["helldivers"].logo_path)

    assert "______" in logo.text
    assert "======" in logo.text
    assert "SUPER EARTH COMMAND" in logo.text
    assert "MANAGED DEMOCRACY ONLINE" in logo.text
    assert 8 <= logo.height <= 12


if __name__ == "__main__":
    test_helldivers_ascii_is_flat_winged_command_mark()
    print("test_helldivers_ascii_logo_quality PASS")
