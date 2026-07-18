from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.version import SYSTEM_VERSION
from tools.eva_boot_dummy import (
    EvaPalette,
    READY_LINES,
    SUPPORTED_THEME_KEYS,
    _palette,
    _styled_segments,
    build_eva_dummy_lines,
    build_theme_dummy_lines,
    format_magi_loading_bar,
)
from ui.animations.loading import get_loading_style


def test_eva_dummy_preserves_identity_and_adds_dense_startup_sections() -> None:
    text = "\n".join(build_eva_dummy_lines(width=100, patch_date="2026-07-16", unicode=False))

    assert f"MAGI / NERV BIOS v{SYSTEM_VERSION}" in text
    assert "Copyright (C) NERV / MAGI Tactical Systems" in text
    assert "Chief Architect: Erhardt Von Grupten Mundt" in text
    assert f"LAST PATCH: 2026-07-16 | BUILD: v{SYSTEM_VERSION}" in text
    assert "SYSTEM DIAGNOSTICS" in text
    assert "CPU CORES" in text
    assert "PHYSICAL CORES" in text
    assert "CPU THREADS" in text
    assert "LOGICAL THREADS" in text
    assert "SYSTEM RAM" in text
    assert "CONSENSUS SYSTEM CONFIGURATION" in text
    assert "MAGI CONSENSUS ARRAY" in text
    assert "MELCHIOR-1" in text
    assert "BALTHASAR-2" in text
    assert "CASPER-3" in text
    assert "MAGI-LINK <||||||||||||||||||> 100%" in text
    assert text.endswith("TRANSFERRING CONTROL TO WAR ROOM...")


def test_magi_loading_bar_clamps_percentages() -> None:
    assert format_magi_loading_bar(-20, unicode=False).endswith("  0%")
    assert format_magi_loading_bar(120, unicode=False).endswith("100%")


def test_eva_palette_assigns_identity_status_and_loading_colors() -> None:
    palette = EvaPalette(orange="O", red="R", cyan="C", white="W", reset="X")

    assert _styled_segments("MAGI / NERV BIOS v7", palette) == [("O", "MAGI / NERV BIOS v7")]
    assert _styled_segments("DATE: 2026-07-17", palette) == [("W", "DATE: 2026-07-17")]
    assert _styled_segments("CO-CPU  CHECK  OK", palette) == [("R", "CO-CPU  CHECK  "), ("C", "OK")]
    assert _styled_segments("MAGI-LINK [####] 100%", palette) == [("O", "MAGI-LINK [####] 100%")]


def test_eva_logo_uses_dedicated_dark_crimson() -> None:
    palette = _palette(True, "eva")

    assert palette.logo == "\x1b[38;2;122;0;24m"
    assert palette.logo != palette.orange


def test_all_gui_theme_prototypes_use_their_own_identity_and_loading_stage() -> None:
    for theme_key in SUPPORTED_THEME_KEYS:
        text = "\n".join(
            build_theme_dummy_lines(theme_key, width=120, patch_date="2026-07-16", unicode=False)
        )

        assert get_loading_style(theme_key).label in text
        assert READY_LINES[theme_key] in text
        assert f"BUILD: v{SYSTEM_VERSION}" in text
        assert text.endswith("TRANSFERRING CONTROL TO WAR ROOM...")
