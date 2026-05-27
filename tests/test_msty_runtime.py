from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import AURELIUS, RATIONALIS
from config.runtime import RuntimeConfig
from integrations.msty.runtime import MstyRuntime


def _provider_ready_status() -> dict[str, object]:
    return {
        "status": "ready",
        "active_backend": "msty-local",
        "backend": "msty-local",
        "base_url": "http://localhost:11454",
        "models": ["deepseek-coder:33b"],
        "resolved_required_models": {RATIONALIS: "deepseek-coder:33b"},
        "missing_required_models": {},
    }


def test_session_isolation() -> None:
    runtime = MstyRuntime(RuntimeConfig(backend="mock"))
    first = runtime.send_to_agent(RATIONALIS, "review prototype")
    second = runtime.send_to_agent(AURELIUS, "summarize system")
    sessions = runtime.session_registry.list_sessions()

    assert "VOTE:" in first
    assert "AURELIUS STATUS" in second
    assert sessions[RATIONALIS].session_id != sessions[AURELIUS].session_id
    assert sessions[RATIONALIS].turns == 1
    assert sessions[AURELIUS].turns == 1


def test_fallback_degraded() -> None:
    import integrations.msty.api as api_module

    original_health_check = api_module.health_check
    try:
        api_module.health_check = lambda *_args, **_kwargs: {"status": "offline", "base_url": "http://127.0.0.1:1"}  # type: ignore[assignment]
        runtime = MstyRuntime(RuntimeConfig(backend="msty-local"))
        response = runtime.send_to_agent(RATIONALIS, "review prototype")
        health = runtime.health_check()
    finally:
        api_module.health_check = original_health_check  # type: ignore[assignment]

    assert "VOTE:" in response
    assert health["status"] == "degraded"


def test_provider_runtime_path_uses_single_health_lookup() -> None:
    import integrations.msty.api as api_module

    calls = {"health": 0, "send": 0}
    original_health_check = api_module.health_check
    original_send_prompt = api_module.send_prompt
    try:
        def fake_health_check(*_args, **_kwargs):
            calls["health"] += 1
            return _provider_ready_status()

        def fake_send_prompt(*_args, **_kwargs):
            calls["send"] += 1
            return "VOTE: APPROVE\nCONFIDENCE: 0.90\nREASONING: provider path verified\n"

        api_module.health_check = fake_health_check  # type: ignore[assignment]
        api_module.send_prompt = fake_send_prompt  # type: ignore[assignment]
        runtime = MstyRuntime(RuntimeConfig(backend="msty-local", mock_fallback_enabled=False))
        response = runtime.send_to_agent(RATIONALIS, "review prototype")
    finally:
        api_module.health_check = original_health_check  # type: ignore[assignment]
        api_module.send_prompt = original_send_prompt  # type: ignore[assignment]

    assert "VOTE: APPROVE" in response
    assert calls == {"health": 1, "send": 1}


def test_health_check_reports_provider_status_once() -> None:
    import integrations.msty.api as api_module

    calls = {"health": 0}
    original_health_check = api_module.health_check
    try:
        def fake_health_check(*_args, **_kwargs):
            calls["health"] += 1
            return _provider_ready_status()

        api_module.health_check = fake_health_check  # type: ignore[assignment]
        runtime = MstyRuntime(RuntimeConfig(backend="msty-local"))
        health = runtime.health_check()
    finally:
        api_module.health_check = original_health_check  # type: ignore[assignment]

    assert health["status"] == "ready"
    assert calls["health"] == 1


if __name__ == "__main__":
    test_session_isolation()
    test_fallback_degraded()
    test_provider_runtime_path_uses_single_health_lookup()
    test_health_check_reports_provider_status_once()
    print("test_msty_runtime PASS")
