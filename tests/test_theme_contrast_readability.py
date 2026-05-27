from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.header import system_status_label_color
from ui.themes.catalog import THEMES


def test_arasaka_readability_fix_does_not_touch_other_theme_status_label_mapping() -> None:
    for key, theme in THEMES.items():
        if key == "arasaka":
            continue
        assert system_status_label_color(theme) == theme.secondary_color


if __name__ == "__main__":
    test_arasaka_readability_fix_does_not_touch_other_theme_status_label_mapping()
    print("test_theme_contrast_readability PASS")
