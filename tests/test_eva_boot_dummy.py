from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.version import SYSTEM_VERSION
from tools.eva_boot_dummy import (
    AUTHOR_LINE,
    ExtendedBootTelemetry,
    EvaPalette,
    HANDOFF_LINES,
    PreviewControls,
    READY_LINES,
    SUPPORTED_THEME_KEYS,
    _extended_diagnostics_lines,
    _palette,
    _parser,
    _poll_controls,
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
    assert text.endswith(HANDOFF_LINES["eva"])


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
        assert AUTHOR_LINE in text
        assert text.endswith(HANDOFF_LINES[theme_key])

    assert len(set(HANDOFF_LINES.values())) == len(SUPPORTED_THEME_KEYS)


def test_each_non_eva_prototype_has_a_distinct_boot_screen_structure() -> None:
    markers = {
        "eva": "SYSTEM DIAGNOSTICS",
        "military": "EXCOMM TACTICAL AMIBIOS",
        "arasaka": "ARASAKA SYSTEM CONFIGURATION / EXECUTIVE SECURITY GRID",
        "helldivers": "SUPER EARTH COMMAND BASIC",
        "janus": "PRIMARY FACE / FORWARD",
        "wh40k": "LITANY OF AWAKENING / SANCTIFIED COGITATOR RITE",
    }
    previews = {
        theme_key: "\n".join(
            build_theme_dummy_lines(theme_key, width=120, patch_date="2026-07-16", unicode=False)
        )
        for theme_key in SUPPORTED_THEME_KEYS
    }

    assert len(set(previews.values())) == len(SUPPORTED_THEME_KEYS)
    for theme_key, marker in markers.items():
        assert marker in previews[theme_key]
        for other_key, other_preview in previews.items():
            if other_key != theme_key:
                assert marker not in other_preview

    assert "CONSENSUS SYSTEM CONFIGURATION" in previews["eva"]
    for theme_key in set(SUPPORTED_THEME_KEYS) - {"eva"}:
        assert "CONSENSUS SYSTEM CONFIGURATION" not in previews[theme_key]


def test_each_prototype_has_a_full_multi_stage_boot_sequence() -> None:
    for theme_key in SUPPORTED_THEME_KEYS:
        lines = build_theme_dummy_lines(theme_key, width=120, unicode=False)

        assert len(lines) >= 55
        assert sum(bool(line.strip()) for line in lines) >= 50


def test_distinct_prototypes_keep_live_hardware_labels_visible() -> None:
    previews = {
        theme_key: "\n".join(build_theme_dummy_lines(theme_key, width=120, unicode=False))
        for theme_key in SUPPORTED_THEME_KEYS
    }

    assert "PHYSICAL CORES" in previews["military"]
    assert "LOGICAL THREADS" in previews["military"]
    assert "PHYSICAL CORES" in previews["arasaka"]
    assert "LOGICAL THREADS" in previews["arasaka"]
    assert "PHYSICAL FREEDOM CORES" in previews["helldivers"]
    assert "LOGICAL LIBERTY THREADS" in previews["helldivers"]
    assert "PHYSICAL CORES" in previews["janus"]
    assert "LOGICAL THREADS" in previews["janus"]
    assert "MEMORY RELIQUARY" in previews["wh40k"]
    assert "CORES /" in previews["wh40k"]
    for preview in previews.values():
        assert "AVAILABLE" in preview


def test_compact_layout_preserves_identity_telemetry_and_handoff_without_wrapping() -> None:
    for theme_key in SUPPORTED_THEME_KEYS:
        full = build_theme_dummy_lines(theme_key, width=120, unicode=False, layout="full")
        compact = build_theme_dummy_lines(theme_key, width=72, unicode=False, layout="compact")
        text = "\n".join(compact)

        assert len(compact) < len(full)
        assert all(len(line) <= 72 for line in compact)
        assert "F2" in text
        assert get_loading_style(theme_key).label in text
        assert text.endswith(HANDOFF_LINES[theme_key])


def test_only_helldivers_prototype_uses_the_full_field_blue_background() -> None:
    assert _palette(True, "helldivers").background == "\x1b[48;2;38;54;184m"
    for theme_key in set(SUPPORTED_THEME_KEYS) - {"helldivers"}:
        assert _palette(True, theme_key).background == ""


def test_memory_check_sits_inside_military_and_arasaka_hardware_sections() -> None:
    military = build_theme_dummy_lines("military", width=120, unicode=False)
    arasaka = build_theme_dummy_lines("arasaka", width=120, unicode=False)

    military_memory = next(index for index, line in enumerate(military) if "MEMORY CHECK:" in line)
    military_display = next(index for index, line in enumerate(military) if "DISPLAY ADAPTER:" in line)
    assert military.index(AUTHOR_LINE) < military_memory < military_display

    arasaka_author = next(index for index, line in enumerate(arasaka) if AUTHOR_LINE in line)
    arasaka_memory = next(index for index, line in enumerate(arasaka) if "MEMORY CHECK:" in line)
    arasaka_processor = next(index for index, line in enumerate(arasaka) if "Main Processor" in line)
    assert arasaka_author < arasaka_memory < arasaka_processor


def test_no_color_mode_retains_theme_choreography_identity() -> None:
    palette = _palette(False, "janus")

    assert palette.theme_key == "janus"
    assert palette.reset == ""


def test_wh40k_frames_keep_gold_borders_around_ivory_copy() -> None:
    palette = EvaPalette(
        orange="GOLD",
        red="DATA",
        cyan="SUCCESS",
        white="IVORY",
        reset="RESET",
        theme_key="wh40k",
    )

    assert _styled_segments("╠════╣", palette) == [("GOLD", "╠════╣")]
    assert _styled_segments("║ LITANY ║", palette) == [
        ("IVORY", ""),
        ("GOLD", "║"),
        ("IVORY", " LITANY "),
        ("GOLD", "║"),
        ("IVORY", ""),
    ]


def test_privacy_safe_extended_telemetry_is_available_to_every_layout() -> None:
    telemetry = ExtendedBootTelemetry(
        total_memory_mb=32768,
        physical_cores=8,
        logical_threads=16,
        available_memory_mb=24576,
        cpu_model="TEST PROCESSOR",
        gpu_model="TEST DISPLAY ADAPTER",
        os_version="TEST OS",
        system_drive_total_gib=1000.0,
        system_drive_free_gib=750.0,
    )

    for theme_key in SUPPORTED_THEME_KEYS:
        text = "\n".join(
            build_theme_dummy_lines(
                theme_key,
                width=120,
                unicode=False,
                telemetry=telemetry,
            )
        )
        assert "24,576" in text
        assert "TEST PROCESSOR" in text
        assert "TEST DISPLAY ADAPTER" in text
        assert "TEST OS" in text

    diagnostics = "\n".join(_extended_diagnostics_lines("eva", telemetry, 120))
    assert "USER, NETWORK AND SERIAL IDENTIFIERS SUPPRESSED" in diagnostics


def test_preview_cli_exposes_responsive_motion_and_keyboard_options() -> None:
    args = _parser().parse_args(
        ["--theme", "JANUS", "--layout", "compact", "--reduced-motion", "--no-controls"]
    )

    assert args.layout == "compact"
    assert args.reduced_motion is True
    assert args.no_controls is True


def test_windows_preview_controls_map_skip_details_and_static_keys(monkeypatch) -> None:
    if sys.platform != "win32":
        return
    import msvcrt

    keys = ["\x00", chr(60), "\x00", chr(134), " "]
    monkeypatch.setattr(msvcrt, "kbhit", lambda: bool(keys))
    monkeypatch.setattr(msvcrt, "getwch", lambda: keys.pop(0))
    controls = PreviewControls()

    _poll_controls(controls)

    assert controls.extended is True
    assert controls.static is True
    assert controls.skip is True
