from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.version import SYSTEM_AUTHOR, SYSTEM_LAST_PATCH_DATE, SYSTEM_VERSION
from ui.animations.bios_boot import (
    DENSE_READY_LINES,
    _boot_color_values,
    generate_dense_bios_boot_lines,
)
from ui.animations.loading import format_loading_bar, get_loading_style


GUI_THEMES = ("eva", "arasaka", "military", "wh40k", "helldivers", "janus")

READY_PROVIDER = {
    "status": "ready",
    "active_backend": "msty-local",
    "missing_required_models": {},
    "mock_fallback_enabled": False,
}


def test_dense_bios_is_complete_for_every_gui_theme() -> None:
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
        assert "SYSTEM DIAGNOSTICS" in text
        assert "CONSENSUS SYSTEM CONFIGURATION" in text
        assert "MEMORY BANK" in text
        assert "032768 MB" in text
        assert get_loading_style(theme_key).label in text
        assert format_loading_bar(theme_key, 100) in text
        assert DENSE_READY_LINES[theme_key] in text
        assert text.endswith("HANDOFF TO MAIN INTERFACE")
        if theme_key != "wh40k":
            assert f"LAST PATCH: {SYSTEM_LAST_PATCH_DATE}" in text


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
