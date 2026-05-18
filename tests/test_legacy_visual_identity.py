from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import AETERNUM, BELLATOR, RATIONALIS
from ui.themes.boot_profiles import GLOBAL_BOOT_MARKERS
from ui.themes.catalog import THEMES


def test_recovered_legacy_logos() -> None:
    logos = ROOT / "static" / "logos"
    assert len((logos / "nerv_logo.txt").read_text(encoding="utf-8").splitlines()) > 20
    assert len((logos / "arasaka_logo.txt").read_text(encoding="utf-8").splitlines()) > 20
    assert "Duobus vultibus" in (logos / "janus_logo.txt").read_text(encoding="utf-8")


def test_recovered_theme_labels() -> None:
    for key in ["eva", "nerv"]:
        labels = THEMES[key].monolith_labels
        assert labels[BELLATOR]["node"] == "MAGI MELCHIOR-1"
        assert labels[AETERNUM]["node"] == "MAGI BALTHASAR-2"
        assert labels[RATIONALIS]["node"] == "MAGI CASPER-3"

    wh40k = " ".join(label["node"] for label in THEMES["wh40k"].monolith_labels.values())
    assert "MUNITORUM" in wh40k
    assert "ADMINISTRATUM" in wh40k
    assert "ADEPTUS MECHANICUS" in wh40k

    helldivers = THEMES["helldivers"]
    assert helldivers.monolith_labels[BELLATOR]["node"] == "LIBERTY DEFENSE MATRIX"
    assert helldivers.interface_labels["analytics"] == "MANAGED DEMOCRACY INSIGHTS"


def test_global_boot_identity_markers() -> None:
    marker_text = "\n".join(GLOBAL_BOOT_MARKERS)
    assert "CONSENSUS TACTICAL BIOS" in marker_text
    assert "WAR ROOM INIT PROTOCOL" in marker_text
    assert "CONSENSUS SYSTEM READY" in marker_text


if __name__ == "__main__":
    test_recovered_legacy_logos()
    test_recovered_theme_labels()
    test_global_boot_identity_markers()
    print("test_legacy_visual_identity PASS")
