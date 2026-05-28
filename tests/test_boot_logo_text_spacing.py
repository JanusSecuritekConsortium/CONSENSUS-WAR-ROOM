from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ui.animations.bios_boot as bios_boot
from ui.animations.bios_boot import generate_bios_boot_lines, render_bios_boot_console
from ui.themes.catalog import THEMES


def test_arasaka_boot_has_explicit_logo_to_bios_gap() -> None:
    lines = "\n".join(generate_bios_boot_lines("ARASAKA", include_logo=True, include_loading=False)).splitlines()
    logo_line_count = len(Path(THEMES["arasaka"].logo_path).read_text(encoding="utf-8").rstrip("\n").splitlines())
    bios_index = next(index for index, line in enumerate(lines) if "ARASAKA EXECUTIVE SECURITY BIOS" in line)
    gap = lines[logo_line_count:bios_index]

    assert gap == [""]


def test_other_boot_logos_keep_standard_one_blank_gap() -> None:
    for theme_key in ("eva", "wh40k", "helldivers", "military", "janus"):
        lines = "\n".join(generate_bios_boot_lines(theme_key, include_logo=True, include_loading=False)).splitlines()
        logo_line_count = len(Path(THEMES[theme_key].logo_path).read_text(encoding="utf-8").rstrip("\n").splitlines())
        bios_index = next(index for index, line in enumerate(lines) if "BIOS" in line)
        gap = lines[logo_line_count:bios_index]

        assert gap == [""], theme_key
        assert "ARASAKA EXECUTIVE SECURITY BIOS" not in lines[bios_index], theme_key


def test_arasaka_console_boot_prints_blank_gap_after_logo() -> None:
    printed: list[str] = []
    original_clear = bios_boot._clear_console
    original_logo = bios_boot._print_logo_with_cursor
    original_print = bios_boot._print_with_cursor
    original_render = bios_boot._render_lines
    original_diag = bios_boot._render_runtime_diagnostics
    original_loading = bios_boot.render_loading_console
    original_await = bios_boot.await_user_interaction
    try:
        bios_boot._clear_console = lambda: None
        bios_boot._print_logo_with_cursor = lambda _logo, _theme_id, _delay: printed.append("LOGO")
        bios_boot._print_with_cursor = lambda line, _delay: printed.append(line)
        bios_boot._render_lines = lambda lines, _delay: printed.append(next(iter(lines)))
        bios_boot._render_runtime_diagnostics = lambda _theme_id, _delay, _rng: None
        bios_boot.render_loading_console = lambda *_args, **_kwargs: None
        bios_boot.await_user_interaction = lambda *_args, **_kwargs: None

        render_bios_boot_console("ARASAKA", speed="fast", seed=1)
    finally:
        bios_boot._clear_console = original_clear
        bios_boot._print_logo_with_cursor = original_logo
        bios_boot._print_with_cursor = original_print
        bios_boot._render_lines = original_render
        bios_boot._render_runtime_diagnostics = original_diag
        bios_boot.render_loading_console = original_loading
        bios_boot.await_user_interaction = original_await

    assert printed[:3] == ["LOGO", "", "ARASAKA EXECUTIVE SECURITY BIOS v" + bios_boot.SYSTEM_VERSION]


if __name__ == "__main__":
    test_arasaka_boot_has_explicit_logo_to_bios_gap()
    test_other_boot_logos_keep_standard_one_blank_gap()
    test_arasaka_console_boot_prints_blank_gap_after_logo()
    print("test_boot_logo_text_spacing PASS")
