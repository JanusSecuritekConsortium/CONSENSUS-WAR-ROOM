from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.boot.phrases import all_theme_boot_phrases
from ui.boot.registry import select_detected_devices, select_post_checks


EXPECTED_THEME_TOKENS = {
    "eva": ("MAGI", "DOGMA", "BALTHASAR", "MELCHIOR", "CASPER"),
    "nerv": ("MAGI", "DOGMA", "BALTHASAR", "MELCHIOR", "CASPER"),
    "arasaka": ("EXECUTIVE", "CORPORATE", "BLACKWALL"),
    "military": ("EXCOMM", "STRATEGIC COMMAND", "THREATCON"),
    "wh40k": ("COGITATOR", "MACHINE SPIRIT", "NOOSPHERIC"),
    "helldivers": ("SUPER EARTH", "MANAGED DEMOCRACY", "LIBERTYCOM"),
    "janus": ("DUAL-VECTOR", "BIFURCATED", "MIRRORED"),
}


def test_theme_boot_vocabulary_appears_in_selected_pools() -> None:
    for theme_key, tokens in EXPECTED_THEME_TOKENS.items():
        rng = random.Random(42)
        text = "\n".join(
            (
                *select_detected_devices(theme_key, rng, count=16),
                *select_post_checks(theme_key, rng, count=12, include_rare=True),
                *all_theme_boot_phrases(theme_key),
            )
        ).upper()

        for token in tokens:
            assert token in text, f"{theme_key}:{token}"


def test_boot_output_remains_structured() -> None:
    from config.version import SYSTEM_VERSION
    from ui.animations.bios_boot import generate_bios_boot_lines

    lines = generate_bios_boot_lines("JANUS", SYSTEM_VERSION, include_logo=False, include_loading=False, randomize_phrases=True, seed=6)
    text = "\n".join(lines)

    assert text.index("Detecting devices:") < text.index("POST:") < text.index("Tribunal initialization:")


if __name__ == "__main__":
    test_theme_boot_vocabulary_appears_in_selected_pools()
    test_boot_output_remains_structured()
    print("test_theme_boot_phrase_selection PASS")
