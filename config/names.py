from __future__ import annotations

from typing import Dict, Tuple


ARBITER = "ARBITER"
RATIONALIS = "RATIONALIS"
AETERNUM = "AETERNUM"
BELLATOR = "BELLATOR"
AURELIUS = "AURELIUS"

CANONICAL_AGENT_IDS: Tuple[str, ...] = (
    ARBITER,
    BELLATOR,
    AETERNUM,
    RATIONALIS,
    AURELIUS,
)

TRIBUNAL_AGENT_IDS: Tuple[str, ...] = (
    BELLATOR,
    AETERNUM,
    RATIONALIS,
)

LEGACY_ROLE_TO_AGENT_ID: Dict[str, str] = {
    "LOGIC": RATIONALIS,
    "FINANCE": AETERNUM,
    "SECURITY": BELLATOR,
}
