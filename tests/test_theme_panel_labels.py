from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import AETERNUM, BELLATOR, RATIONALIS
from ui.themes.catalog import THEMES


EXPECTED_PANEL_LABELS = {
    "eva": {
        RATIONALIS: "MAGI CASPER-3",
        AETERNUM: "MAGI BALTHASAR-2",
        BELLATOR: "MAGI MELCHIOR-1",
    },
    "nerv": {
        RATIONALIS: "MAGI CASPER-3",
        AETERNUM: "MAGI BALTHASAR-2",
        BELLATOR: "MAGI MELCHIOR-1",
    },
    "wh40k": {
        RATIONALIS: "ADEPTUS MECHANICUS LOGIS",
        AETERNUM: "ADMINISTRATUM HISTORICUS",
        BELLATOR: "MUNITORUM TACTICUS",
    },
    "helldivers": {
        RATIONALIS: "DEMOCRACY ASSESSMENT ENGINE",
        AETERNUM: "FREEDOM FORECASTING SYSTEM",
        BELLATOR: "LIBERTY DEFENSE MATRIX",
    },
    "janus": {
        RATIONALIS: "ANALYTIC MIRROR",
        AETERNUM: "COUNTERPART HORIZON",
        BELLATOR: "JANUS GATEKEEPER",
    },
}


def test_canonical_theme_panel_labels_are_preserved() -> None:
    for theme_key, expected in EXPECTED_PANEL_LABELS.items():
        labels = THEMES[theme_key].monolith_labels
        for agent_id, node_label in expected.items():
            assert labels[agent_id]["node"] == node_label


if __name__ == "__main__":
    test_canonical_theme_panel_labels_are_preserved()
    print("test_theme_panel_labels PASS")
