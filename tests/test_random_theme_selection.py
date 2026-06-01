from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.boot import resolve_startup_theme
from ui.themes.catalog import get_gui_theme_options


def test_random_theme_selection_is_seeded_and_uses_gui_catalog() -> None:
    valid = {theme.key for theme in get_gui_theme_options()}
    first = resolve_startup_theme("RANDOM", seed=41)
    second = resolve_startup_theme("RANDOM", seed=41)
    assert first == second
    assert first in valid


if __name__ == "__main__":
    test_random_theme_selection_is_seeded_and_uses_gui_catalog()
    print("test_random_theme_selection PASS")
