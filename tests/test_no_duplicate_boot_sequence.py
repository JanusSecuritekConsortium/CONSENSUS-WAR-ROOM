from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.version import SYSTEM_VERSION
from ui.animations.bios_boot import generate_bios_boot_lines
from ui.themes.catalog import THEMES


def _section(lines: list[str], header: str) -> list[str]:
    start = next(index for index, line in enumerate(lines) if line.strip() == header)
    end = next((index for index in range(start + 1, len(lines)) if lines[index] == ""), len(lines))
    return [line.strip() for line in lines[start + 1 : end] if line.strip()]


def _assert_no_consecutive_duplicates(lines: list[str]) -> None:
    previous = None
    for line in lines:
        assert line != previous
        previous = line


def test_boot_blocks_have_no_duplicate_consecutive_lines() -> None:
    for theme_key in THEMES:
        lines = generate_bios_boot_lines(
            theme_key,
            SYSTEM_VERSION,
            include_logo=False,
            include_loading=False,
            randomize_phrases=True,
            seed=104,
            provider_status={"status": "ready", "missing_required_models": {}, "mock_fallback_enabled": False},
        )
        for header in ("Detecting devices:", "POST:", "Tribunal initialization:"):
            section = _section(lines, header)
            assert section, f"{theme_key}:{header}"
            _assert_no_consecutive_duplicates(section)


def test_deterministic_fallback_is_stable_without_randomization() -> None:
    first = generate_bios_boot_lines("MILITARY", SYSTEM_VERSION, include_logo=False, include_loading=False)
    second = generate_bios_boot_lines("MILITARY", SYSTEM_VERSION, include_logo=False, include_loading=False)

    assert first == second


if __name__ == "__main__":
    test_boot_blocks_have_no_duplicate_consecutive_lines()
    test_deterministic_fallback_is_stable_without_randomization()
    print("test_no_duplicate_boot_sequence PASS")
