from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.boot import resolve_startup_theme


def test_boot_theme_override_resolves_theme_alias() -> None:
    assert resolve_startup_theme("ARASAKA") == "arasaka"
    assert resolve_startup_theme("MILITARY") == "military"


if __name__ == "__main__":
    test_boot_theme_override_resolves_theme_alias()
    print("test_boot_theme_override PASS")
