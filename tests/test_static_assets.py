from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.themes.catalog import THEMES


def test_logo_assets_are_readable() -> None:
    nerv_logo = ROOT / "static" / "logos" / "nerv_logo.txt"
    assert nerv_logo.exists()
    nerv_text = nerv_logo.read_text(encoding="utf-8")
    assert len(nerv_text.splitlines()) > 20
    assert max(len(line) for line in nerv_text.splitlines()) > 40

    for theme in THEMES.values():
        path = Path(theme.logo_path)
        assert path.exists(), path
        text = path.read_text(encoding="utf-8")
        assert text.strip(), path


if __name__ == "__main__":
    test_logo_assets_are_readable()
    print("test_static_assets PASS")
