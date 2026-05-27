from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import AURELIUS, RATIONALIS
from config.runtime import RuntimeConfig
from integrations.msty.runtime import MstyRuntime


def test_mock_runtime_fast_path_keeps_agent_sessions_isolated() -> None:
    runtime = MstyRuntime(RuntimeConfig(backend="mock"))

    first = runtime.send_to_agent(RATIONALIS, "review prototype")
    second = runtime.send_to_agent(AURELIUS, "summarize system")
    sessions = runtime.session_registry.list_sessions()

    assert "VOTE:" in first
    assert "AURELIUS STATUS" in second
    assert sessions[RATIONALIS].session_id != sessions[AURELIUS].session_id
    assert sessions[RATIONALIS].turns == 1
    assert sessions[AURELIUS].turns == 1


if __name__ == "__main__":
    test_mock_runtime_fast_path_keeps_agent_sessions_isolated()
    print("test_msty_runtime_fast_path PASS")
