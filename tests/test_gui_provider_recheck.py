from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.flet_app import create_gui_state, recheck_provider_for_gui, submit_proposal_live_for_gui


def test_degraded_provider_allows_mock_fallback_submission() -> None:
    from integrations.msty import api as api_module

    original_health = api_module.health_check
    original_send_prompt = api_module.send_prompt
    try:
        api_module.health_check = lambda _config=None: {
            "backend": "msty-local",
            "status": "unavailable",
            "base_url": "http://127.0.0.1:11964",
            "error": "offline",
        }

        def fail_prompt(*_args, **_kwargs):
            raise RuntimeError("provider offline")

        api_module.send_prompt = fail_prompt
        state = create_gui_state("ARASAKA", RuntimeConfig(theme="arasaka", backend="msty-local"))
        result = submit_proposal_live_for_gui(
            state,
            "Approve a degraded provider fallback test.",
            skip_animations=True,
        )

        assert state.provider_status["status"] == "degraded"
        assert state.provider_warning == "PROVIDER DEGRADED - MOCK FALLBACK ACTIVE"
        assert result.votes
    finally:
        api_module.health_check = original_health
        api_module.send_prompt = original_send_prompt


def test_provider_recheck_updates_status_model() -> None:
    from integrations.msty import api as api_module

    status = {"value": "unavailable"}
    original_health = api_module.health_check
    try:
        def fake_health(_config=None):
            return {"backend": "msty-local", "status": status["value"], "base_url": "mock://provider"}

        api_module.health_check = fake_health
        state = create_gui_state("MILITARY", RuntimeConfig(theme="military", backend="msty-local"))

        assert state.provider_status["status"] == "degraded"
        status["value"] = "ready"
        rechecked = recheck_provider_for_gui(state)

        assert rechecked["status"] == "ready"
        assert state.provider_status["status"] == "ready"
        assert state.provider_warning == ""
    finally:
        api_module.health_check = original_health


if __name__ == "__main__":
    test_degraded_provider_allows_mock_fallback_submission()
    test_provider_recheck_updates_status_model()
    print("test_gui_provider_recheck PASS")
