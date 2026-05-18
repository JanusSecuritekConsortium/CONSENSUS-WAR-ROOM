from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import ARBITER, AETERNUM, BELLATOR, RATIONALIS
from config.version import SYSTEM_VERSION
from ui.animations.bios_boot import generate_bios_boot_lines
from ui.animations.boot_phrases import boot_phrase_bank, theme_boot_phrase_count
from ui.themes.catalog import THEMES


READY_PROVIDER = {
    "status": "ready",
    "active_backend": "msty-llama-cpp",
    "base_url": "http://localhost:11454",
    "model_count": 10,
    "missing_required_models": {},
    "mock_fallback_enabled": True,
}


def _tribunal_phrase_lines(theme_key: str, seed: int) -> list[str]:
    return [
        line
        for line in generate_bios_boot_lines(
            theme_key,
            SYSTEM_VERSION,
            include_logo=False,
            include_loading=False,
            provider_status=READY_PROVIDER,
            randomize_phrases=True,
            seed=seed,
        )
        if "::" in line
    ]


def test_each_theme_has_broad_boot_phrase_bank() -> None:
    for theme_key in THEMES:
        assert theme_boot_phrase_count(theme_key) >= 50, theme_key
        for node_id in (RATIONALIS, AETERNUM, BELLATOR, ARBITER):
            assert len(boot_phrase_bank(theme_key, node_id)) >= 12, f"{theme_key}:{node_id}"


def test_seeded_boot_phrases_are_reproducible() -> None:
    first = _tribunal_phrase_lines("EVA", 42)
    second = _tribunal_phrase_lines("EVA", 42)
    different = _tribunal_phrase_lines("EVA", 43)

    assert first == second
    assert first != different


def test_randomized_boot_phrases_keep_node_online_markers() -> None:
    text = "\n".join(_tribunal_phrase_lines("WH40K", 7))

    assert "RATIONALIS....ONLINE ::" in text
    assert "AETERNUM......ONLINE ::" in text
    assert "BELLATOR......ONLINE ::" in text
    assert "ARBITER.......ONLINE ::" in text
    assert "NOOSPHERIC" in text or "OMNISSIAH" in text or "SANCTION" in text


if __name__ == "__main__":
    test_each_theme_has_broad_boot_phrase_bank()
    test_seeded_boot_phrases_are_reproducible()
    test_randomized_boot_phrases_keep_node_online_markers()
    print("test_boot_phrase_variations PASS")
