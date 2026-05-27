from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.version import SYSTEM_VERSION
from ui.animations.bios_boot import generate_bios_boot_lines


READY_PROVIDER = {
    "status": "ready",
    "active_backend": "msty-local",
    "base_url": "http://127.0.0.1:11964",
    "model_count": 4,
    "missing_required_models": {},
    "mock_fallback_enabled": True,
}


def _boot(theme: str, seed: int) -> list[str]:
    return generate_bios_boot_lines(
        theme,
        SYSTEM_VERSION,
        include_logo=False,
        include_loading=False,
        provider_status=READY_PROVIDER,
        randomize_phrases=True,
        seed=seed,
    )


def _section(lines: list[str], header: str) -> list[str]:
    start = next(index for index, line in enumerate(lines) if line.strip() == header)
    end = next((index for index in range(start + 1, len(lines)) if lines[index] == ""), len(lines))
    return [line.strip() for line in lines[start + 1 : end] if line.strip()]


def test_seeded_boot_randomization_is_reproducible() -> None:
    first = _boot("EVA", 7851)
    second = _boot("EVA", 7851)
    different = _boot("EVA", 7852)

    assert first == second
    assert first != different


def test_boot_randomization_applies_to_devices_post_and_monoliths() -> None:
    first = _boot("ARASAKA", 10)
    second = _boot("ARASAKA", 11)

    assert _section(first, "Detecting devices:") != _section(second, "Detecting devices:")
    assert _section(first, "POST:") != _section(second, "POST:")
    assert _section(first, "Tribunal initialization:") != _section(second, "Tribunal initialization:")


if __name__ == "__main__":
    test_seeded_boot_randomization_is_reproducible()
    test_boot_randomization_applies_to_devices_post_and_monoliths()
    print("test_boot_phrase_randomization PASS")
