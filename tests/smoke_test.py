from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from monoliths.registry import DEFAULT_NODES
from core.history import result_to_dict
from core.logging import log_event
from core.paths import HISTORY_PATH
from core.tribunal import Tribunal
from core.voting.rules import ConsensusRules
from config.runtime import RuntimeConfig
from integrations.msty.runtime import MstyRuntime


def main() -> int:
    log_event("system_command", {"command": "tests/smoke_test.py"})
    tribunal = Tribunal(
        DEFAULT_NODES,
        MstyRuntime(RuntimeConfig(backend="mock")),
        rules=ConsensusRules(minimum_confidence=0.6, quorum=2, majority=2),
        theme_key="military",
    )
    result = tribunal.deliberate("Smoke test proposal: validate runtime coherence.")
    payload = result_to_dict(result)

    assert result.verdict.value == "APPROVE", payload
    assert len(result.votes) == 3, payload
    assert HISTORY_PATH.name == "decision_history.json", str(HISTORY_PATH)
    assert HISTORY_PATH.exists(), str(HISTORY_PATH)
    assert result.session_id in HISTORY_PATH.read_text(encoding="utf-8"), result.session_id

    print("SMOKE TEST PASS")
    print(f"session_id={result.session_id}")
    print(f"history_path={HISTORY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
