from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import AETERNUM, BELLATOR, RATIONALIS, TRIBUNAL_AGENT_IDS
from config.nodes import DEFAULT_NODES
from ui.boot.phrases import BOOT_NODE_IDS


def test_tribunal_registration_order_matches_operator_layout() -> None:
    expected = (BELLATOR, AETERNUM, RATIONALIS)

    assert TRIBUNAL_AGENT_IDS == expected
    assert tuple(DEFAULT_NODES.keys()) == expected
    assert BOOT_NODE_IDS[:3] == expected


if __name__ == "__main__":
    test_tribunal_registration_order_matches_operator_layout()
    print("test_monolith_order_contract PASS")
