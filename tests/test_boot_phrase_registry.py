from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import ARBITER, AETERNUM, BELLATOR, RATIONALIS
from ui.boot.phrases import boot_phrase_bank
from ui.boot.registry import BASE_DETECTED_DEVICES, BASE_POST_CHECKS, BOOT_PHRASE_REGISTRY
from ui.themes.catalog import THEMES


def test_boot_phrase_registry_covers_all_active_themes() -> None:
    assert set(THEMES) <= set(BOOT_PHRASE_REGISTRY)
    for theme_key, registry in BOOT_PHRASE_REGISTRY.items():
        assert registry.theme_key == theme_key
        assert registry.devices
        assert registry.post_checks
        assert all(line.strip() == line and line for line in registry.devices)
        assert all(line.startswith(("[OK]", "[WARN]", "[SYNC]")) for line in registry.post_checks + registry.rare_post_checks)


def test_legacy_claudsensus_boot_material_is_preserved_or_adapted() -> None:
    base_text = "\n".join((*BASE_DETECTED_DEVICES, *BASE_POST_CHECKS))

    assert "Consensus Neural Thread v9.12" in base_text
    assert "Quantum Entanglement Buffers" in base_text
    assert "Voice Carrier Modulator" in base_text
    assert "Verdict Transmission Bus" in base_text

    eva_text = "\n".join(
        phrase
        for node_id in (RATIONALIS, AETERNUM, BELLATOR, ARBITER)
        for phrase in boot_phrase_bank("eva", node_id)
    )
    assert "RATIONALIS LOGIC ENGINE" in eva_text
    assert "AETERNUM TEMPORAL ANALYST" in eva_text
    assert "BELLATOR TACTICAL ASSESSOR" in eva_text
    assert "CENTRAL DOGMA" in eva_text


if __name__ == "__main__":
    test_boot_phrase_registry_covers_all_active_themes()
    test_legacy_claudsensus_boot_material_is_preserved_or_adapted()
    print("test_boot_phrase_registry PASS")
