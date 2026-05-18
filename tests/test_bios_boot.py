from __future__ import annotations

import io
import sys
from pathlib import Path
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.version import SYSTEM_VERSION
from core.cli import resolve_selected_theme
import ui.animations.bios_boot as bios_boot
from ui.animations.bios_boot import await_user_interaction, generate_bios_boot_lines
from ui.animations.loading import get_loading_style
from ui.themes.catalog import THEMES


READY_PROVIDER = {
    "status": "ready",
    "active_backend": "msty-local",
    "base_url": "http://127.0.0.1:11964",
    "model_count": 4,
    "missing_required_models": {},
    "mock_fallback_enabled": True,
}


def test_bios_boot_lines_include_required_stages() -> None:
    text = "\n".join(
        generate_bios_boot_lines("NERV", SYSTEM_VERSION, total_memory_mb=65536, provider_status=READY_PROVIDER)
    )

    assert "Memory Test: 008192 MB OK" in text
    assert "Memory Test: 016384 MB OK" in text
    assert "Memory Test: 032768 MB OK" in text
    assert "Memory Test: 057344 MB OK" in text
    assert "Memory Test: 065536 MB OK" in text
    assert "POST:" in text
    assert "Tribunal initialization:" in text
    assert "WAR ROOM INIT PROTOCOL COMPLETE" in text
    assert "TRANSFERRING CONTROL TO CONSENSUS LOADER..." in text
    assert "INITIALIZING NERV MAGI INTERLOCK" in text


def test_bios_boot_does_not_require_external_provider() -> None:
    text = "\n".join(
        generate_bios_boot_lines(
            "NERV",
            SYSTEM_VERSION,
            provider_status={
                "status": "offline",
                "active_backend": "msty-local",
                "base_url": "http://127.0.0.1:11964",
                "model_count": 0,
                "missing_required_models": {},
                "mock_fallback_enabled": True,
            },
        )
    )

    assert "[WARN] PROVIDER OFFLINE - MOCK FALLBACK ACTIVE" in text
    assert "[FAIL] External Provider" not in text


def test_bios_boot_uses_selected_theme_only() -> None:
    arasaka = "\n".join(generate_bios_boot_lines("ARASAKA", SYSTEM_VERSION, provider_status=READY_PROVIDER))
    eva = "\n".join(generate_bios_boot_lines("EVA", SYSTEM_VERSION, provider_status=READY_PROVIDER))
    military = "\n".join(generate_bios_boot_lines("MILITARY", SYSTEM_VERSION, provider_status=READY_PROVIDER))
    wh40k = "\n".join(generate_bios_boot_lines("WH40K", SYSTEM_VERSION, provider_status=READY_PROVIDER))
    janus = "\n".join(generate_bios_boot_lines("JANUS", SYSTEM_VERSION, provider_status=READY_PROVIDER))
    helldivers = "\n".join(generate_bios_boot_lines("HELLDIVERS", SYSTEM_VERSION, provider_status=READY_PROVIDER))

    assert "ARASAKA EXECUTIVE SECURITY BIOS" in arasaka
    assert "NERV" not in arasaka
    assert "INITIALIZING ARASAKA EXECUTIVE GRID" in arasaka

    assert "MAGI / NERV BIOS" in eva
    assert "ARASAKA" not in eva
    assert "INITIALIZING MAGI CONSENSUS ARRAY" in eva

    assert "EXCOMM WAR ROOM BIOS" in military
    assert "NERV" not in military
    assert "ARASAKA" not in military
    assert "INITIALIZING EXCOMM WAR ROOM" in military

    assert "IMPERIAL COGITATOR BIOS" in wh40k
    assert "NERV" not in wh40k
    assert "ARASAKA" not in wh40k
    assert "AWAKENING IMPERIAL COGITATOR" in wh40k

    assert "JANUS DUAL-FRONT BIOS" in janus
    assert "NERV" not in janus
    assert "ARASAKA" not in janus
    assert "INITIALIZING JANUS MIRROR CHANNEL" in janus

    assert "SUPER EARTH COMMAND BIOS" in helldivers
    assert "NERV" not in helldivers
    assert "ARASAKA" not in helldivers
    assert "AUTHORIZING MANAGED DEMOCRACY INTERFACE" in helldivers


def _logo_text(theme_key: str) -> str:
    return Path(THEMES[theme_key].logo_path).read_text(encoding="utf-8").rstrip("\n")


def _bios_header_for(theme_key: str) -> str:
    return {
        "military": "EXCOMM WAR ROOM BIOS",
        "eva": "MAGI / NERV BIOS",
        "nerv": "MAGI / NERV BIOS",
        "wh40k": "IMPERIAL COGITATOR BIOS",
        "helldivers": "SUPER EARTH COMMAND BIOS",
        "arasaka": "ARASAKA EXECUTIVE SECURITY BIOS",
        "janus": "JANUS DUAL-FRONT BIOS",
    }[theme_key]


def test_bios_logo_order_and_deduplication() -> None:
    for theme_key in THEMES:
        text = "\n".join(generate_bios_boot_lines(theme_key, SYSTEM_VERSION, provider_status=READY_PROVIDER))
        logo = _logo_text(theme_key)
        header = _bios_header_for(theme_key)

        assert text.startswith(logo), theme_key
        assert text.count(logo) == 1, theme_key
        assert text.index(logo) < text.index(header), theme_key

        after_tribunal = text.split("Tribunal initialization:", 1)[1]
        assert logo not in after_tribunal, theme_key


def test_wh40k_visible_boot_uses_imperial_time_only() -> None:
    text = "\n".join(generate_bios_boot_lines("WH40K", SYSTEM_VERSION, provider_status=READY_PROVIDER))

    assert "DATE REF: 0918015.M03" in text
    assert "+++ ADEPTUS MECHANICUS COGITATOR RITE +++" in text
    for forbidden in ["GMT", "UTC", "DATE:", "REAL DATE:", "2026-"]:
        assert forbidden not in text


def test_bios_boot_includes_selected_loading_style() -> None:
    for theme_key in THEMES:
        text = "\n".join(generate_bios_boot_lines(theme_key, SYSTEM_VERSION, provider_status=READY_PROVIDER))
        style = get_loading_style(theme_key)

        assert f"[LOAD:{style.key}]" in text, theme_key
        assert style.label in text, theme_key
        assert style.stages[0] in text, theme_key


def test_bios_centering_and_build_metadata() -> None:
    text = "\n".join(
        generate_bios_boot_lines(
            "MILITARY",
            SYSTEM_VERSION,
            center_logo=True,
            total_memory_mb=32768,
            provider_status=READY_PROVIDER,
        )
    )

    assert f"EXCOMM WAR ROOM BIOS v{SYSTEM_VERSION}" in text
    assert f"BUILD: v{SYSTEM_VERSION}" in text
    assert "DATE:" in text
    assert "Memory Test: 032768 MB OK" in text
    assert any(line.startswith(" ") and line.strip() == "POST:" for line in text.splitlines())
    assert any(line.startswith(" ") and line.strip() == "Tribunal initialization:" for line in text.splitlines())


def test_memory_fallback_is_marked_when_detection_fails() -> None:
    original = bios_boot._system_memory_mb
    try:
        bios_boot._system_memory_mb = lambda: (65536, True)
        text = "\n".join(generate_bios_boot_lines("MILITARY", SYSTEM_VERSION, provider_status=READY_PROVIDER))
    finally:
        bios_boot._system_memory_mb = original

    assert "Memory Test: 065536 MB OK" in text
    assert "Memory Source: FALLBACK CONFIGURATION" in text


def test_boot_prompt_waits_only_for_interactive_stdin() -> None:
    class FakeStdin:
        def __init__(self, interactive: bool) -> None:
            self.interactive = interactive
            self.reads = 0

        def isatty(self) -> bool:
            return self.interactive

        def readline(self) -> str:
            self.reads += 1
            return "\n"

    non_interactive = FakeStdin(False)
    interactive = FakeStdin(True)

    with redirect_stdout(io.StringIO()) as output:
        await_user_interaction(non_interactive)
    assert "PRESS ENTER TO ENTER THE WAR ROOM" in output.getvalue()
    assert non_interactive.reads == 0

    with redirect_stdout(io.StringIO()):
        await_user_interaction(interactive)
    assert interactive.reads == 1


def test_random_theme_resolution_is_single_source_of_truth() -> None:
    selected = resolve_selected_theme(None, seed=42)

    assert selected in THEMES
    assert selected == resolve_selected_theme(None, seed=42)
    assert resolve_selected_theme("JANUS", seed=42) == "janus"


if __name__ == "__main__":
    test_bios_boot_lines_include_required_stages()
    test_bios_boot_does_not_require_external_provider()
    test_bios_boot_uses_selected_theme_only()
    test_bios_logo_order_and_deduplication()
    test_wh40k_visible_boot_uses_imperial_time_only()
    test_bios_boot_includes_selected_loading_style()
    test_bios_centering_and_build_metadata()
    test_memory_fallback_is_marked_when_detection_fails()
    test_boot_prompt_waits_only_for_interactive_stdin()
    test_random_theme_resolution_is_single_source_of_truth()
    print("test_bios_boot PASS")
