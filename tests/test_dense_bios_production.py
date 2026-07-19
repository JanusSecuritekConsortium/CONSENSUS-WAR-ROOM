from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.version import SYSTEM_AUTHOR, SYSTEM_LAST_PATCH_DATE, SYSTEM_VERSION
from ui.animations.bios_boot import (
    BootHardwareSnapshot,
    DENSE_READY_LINES,
    _boot_color_values,
    capture_boot_hardware_snapshot,
    generate_dense_bios_boot_lines,
    hardware_diagnostic_rows,
)
from ui.animations.loading import format_loading_bar, get_loading_style
from tools.eva_boot_dummy import HANDOFF_LINES


GUI_THEMES = ("eva", "arasaka", "military", "wh40k", "helldivers", "janus")

READY_PROVIDER = {
    "status": "ready",
    "active_backend": "msty-local",
    "missing_required_models": {},
    "mock_fallback_enabled": False,
}


def test_dense_bios_is_complete_for_every_gui_theme() -> None:
    identity_markers = {
        "eva": "SYSTEM DIAGNOSTICS",
        "military": "EXCOMM TACTICAL AMIBIOS",
        "arasaka": "ARASAKA SYSTEM CONFIGURATION / EXECUTIVE SECURITY GRID",
        "helldivers": "SUPER EARTH COMMAND BASIC",
        "janus": "JANUS DUAL-FRONT INITIALIZATION",
        "wh40k": "LITANY OF AWAKENING / SANCTIFIED COGITATOR RITE",
    }
    for theme_key in GUI_THEMES:
        text = "\n".join(
            generate_dense_bios_boot_lines(
                theme_key,
                SYSTEM_VERSION,
                include_logo=False,
                total_memory_mb=32768,
                provider_status=READY_PROVIDER,
                seed=7,
            )
        )

        assert f"Chief Architect: {SYSTEM_AUTHOR}" in text
        assert f"BUILD: v{SYSTEM_VERSION}" in text
        assert identity_markers[theme_key] in text
        assert "32,768" in text
        if theme_key == "wh40k":
            assert "CORES /" in text
            assert "THREADS" in text
        else:
            assert "PHYSICAL" in text
            assert "LOGICAL" in text
        assert "[OK]" in text
        assert get_loading_style(theme_key).label in text
        assert format_loading_bar(theme_key, 100) in text
        assert DENSE_READY_LINES[theme_key] in text
        assert text.endswith(HANDOFF_LINES[theme_key])
        assert SYSTEM_LAST_PATCH_DATE in text


def test_terminal_palette_overrides_fix_requested_contrast() -> None:
    arasaka = _boot_color_values("arasaka")
    eva = _boot_color_values("eva")

    assert arasaka["data"] == "#c7c7c7"
    assert arasaka["data"] != "#1a1a1a"
    assert arasaka["success"] == "#ffffff"
    assert eva["success"] == "#008fbd"
    assert eva["success"] != "#00d5ff"
    assert eva["logo"] == "#7a0018"


def test_each_theme_loading_bar_has_distinct_geometry() -> None:
    bars = {theme_key: format_loading_bar(theme_key, 50, ascii_only=True) for theme_key in GUI_THEMES}

    assert len(set(bars.values())) == len(bars)
    assert "TACTICAL [" in bars["military"]
    assert "MAGI-LINK <" in bars["eva"]
    assert "SECURITY CLEARANCE ||" in bars["arasaka"]
    assert "MACHINE-SPIRIT PURITY {" in bars["wh40k"]
    assert "DEMOCRATIC AUTHORIZATION >>>" in bars["helldivers"]
    assert "DUAL-CHANNEL SYNC <" in bars["janus"]


def test_hardware_snapshot_is_refreshed_for_each_boot_generation(monkeypatch) -> None:
    detected = {
        "memory": (32768, False),
        "topology": (8, 16, False),
    }
    monkeypatch.setattr(
        "ui.animations.bios_boot._system_memory_mb",
        lambda: detected["memory"],
    )
    monkeypatch.setattr(
        "ui.animations.bios_boot._system_cpu_topology",
        lambda: detected["topology"],
    )

    first = "\n".join(generate_dense_bios_boot_lines("eva", include_logo=False, include_loading=False))
    detected["memory"] = (65536, False)
    detected["topology"] = (16, 24, False)
    second = "\n".join(generate_dense_bios_boot_lines("eva", include_logo=False, include_loading=False))

    assert "8 PHYSICAL CORES" in first
    assert "16 LOGICAL THREADS" in first
    assert "32,768 MB / 32.0 GiB" in first
    assert "16 PHYSICAL CORES" in second
    assert "24 LOGICAL THREADS" in second
    assert "65,536 MB / 64.0 GiB" in second


def test_hardware_snapshot_accepts_deterministic_memory_override() -> None:
    snapshot = capture_boot_hardware_snapshot(total_memory_mb=16384)

    assert snapshot.total_memory_mb == 16384
    assert snapshot.physical_cores >= 1
    assert snapshot.logical_threads >= snapshot.physical_cores


def test_hardware_fallback_values_are_explicitly_marked() -> None:
    rows = hardware_diagnostic_rows(
        BootHardwareSnapshot(
            total_memory_mb=65536,
            physical_cores=24,
            logical_threads=24,
            memory_fallback=True,
            topology_fallback=True,
        )
    )

    assert all(row[-1] == "WARN" for row in rows)
    assert all("FALLBACK" in row[2] for row in rows)
