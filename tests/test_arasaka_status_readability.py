from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.header import system_status_label_color
from ui.themes.catalog import THEMES


def _hex_luminance(color: str) -> float:
    color = color.lstrip("#")
    r, g, b = [int(color[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def test_arasaka_system_status_labels_use_readable_secondary_text() -> None:
    theme = THEMES["arasaka"]
    label = system_status_label_color(theme)
    assert label != theme.secondary_color
    assert _hex_luminance(label) > _hex_luminance(theme.surface_color) + 0.2


if __name__ == "__main__":
    test_arasaka_system_status_labels_use_readable_secondary_text()
    print("test_arasaka_status_readability PASS")
