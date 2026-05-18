from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module
from integrations.msty.runtime import MstyRuntime


DEGRADED_STATUS = {
    "status": "degraded",
    "base_url": "mock://provider",
    "models": [],
    "missing_required_models": {"RATIONALIS": "deepseek-coder:33b"},
}


def test_fallback_policy_modes() -> None:
    runtime = MstyRuntime(RuntimeConfig(backend="msty-local", mock_fallback_enabled=True))

    assert runtime.fallback_policy({"status": "ready", "missing_required_models": {}})["mode"] == "real"
    assert runtime.fallback_policy(DEGRADED_STATUS)["mode"] == "degraded"
    assert runtime.fallback_policy({"status": "offline", "missing_required_models": {}})["action"] == "mock_all_monoliths"


def test_missing_model_uses_mock_fallback_when_enabled() -> None:
    original_health = api_module.health_check
    original_send = api_module.send_prompt
    try:
        api_module.health_check = lambda _config=None, _nodes=None: DEGRADED_STATUS

        def fail_send(*_args, **_kwargs):
            raise AssertionError("send_prompt should not be called for a missing model")

        api_module.send_prompt = fail_send
        response = MstyRuntime(RuntimeConfig(backend="msty-local", mock_fallback_enabled=True)).send_to_agent(
            "RATIONALIS",
            "test prompt",
            {"model": "deepseek-coder:33b"},
        )

        assert "VOTE:" in response
    finally:
        api_module.health_check = original_health
        api_module.send_prompt = original_send


def test_strict_mode_fails_when_model_missing() -> None:
    original_health = api_module.health_check
    try:
        api_module.health_check = lambda _config=None, _nodes=None: DEGRADED_STATUS
        runtime = MstyRuntime(RuntimeConfig(backend="msty-local", strict_provider_mode=True))

        try:
            runtime.send_to_agent("RATIONALIS", "test prompt", {"model": "deepseek-coder:33b"})
        except RuntimeError as exc:
            assert "Required model unavailable" in str(exc)
        else:
            raise AssertionError("strict mode should fail when model is unavailable")
    finally:
        api_module.health_check = original_health


if __name__ == "__main__":
    test_fallback_policy_modes()
    test_missing_model_uses_mock_fallback_when_enabled()
    test_strict_mode_fails_when_model_missing()
    print("test_provider_fallback_policy PASS")
