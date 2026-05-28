from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import header_logo_control_for
from ui.components.header import LOGO_FONT_FAMILY


def test_user_ascii_headers_are_monospace_non_wrapping_non_selectable() -> None:
    for theme_key in ("eva", "helldivers"):
        logo = header_logo_control_for(theme_key)

        assert logo.font_family == LOGO_FONT_FAMILY
        assert logo.style.font_family == LOGO_FONT_FAMILY
        assert logo._Control__attrs["nowrap"][0] is True
        assert logo.selectable is False


if __name__ == "__main__":
    test_user_ascii_headers_are_monospace_non_wrapping_non_selectable()
    print("test_header_no_wrap PASS")
