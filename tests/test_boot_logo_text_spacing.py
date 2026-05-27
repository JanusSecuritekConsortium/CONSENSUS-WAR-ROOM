from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.animations.bios_boot import generate_bios_boot_lines
from ui.themes.catalog import THEMES


def test_arasaka_boot_has_explicit_logo_to_bios_gap() -> None:
    lines = "\n".join(generate_bios_boot_lines("ARASAKA", include_logo=True, include_loading=False)).splitlines()
    logo_line_count = len(Path(THEMES["arasaka"].logo_path).read_text(encoding="utf-8").rstrip("\n").splitlines())
    bios_index = next(index for index, line in enumerate(lines) if "ARASAKA EXECUTIVE SECURITY BIOS" in line)
    gap = lines[logo_line_count:bios_index]

    assert len(gap) >= 4
    assert all(line == "" for line in gap)


def test_other_boot_logos_keep_standard_two_blank_gap() -> None:
    for theme_key in ("eva", "wh40k", "helldivers", "military", "janus"):
        lines = "\n".join(generate_bios_boot_lines(theme_key, include_logo=True, include_loading=False)).splitlines()
        logo_line_count = len(Path(THEMES[theme_key].logo_path).read_text(encoding="utf-8").rstrip("\n").splitlines())
        bios_index = next(index for index, line in enumerate(lines) if "BIOS" in line)
        gap = lines[logo_line_count:bios_index]

        assert len(gap) >= 2, theme_key
        assert all(line == "" for line in gap), theme_key
        assert "ARASAKA EXECUTIVE SECURITY BIOS" not in lines[bios_index], theme_key


if __name__ == "__main__":
    test_arasaka_boot_has_explicit_logo_to_bios_gap()
    test_other_boot_logos_keep_standard_two_blank_gap()
    print("test_boot_logo_text_spacing PASS")
