from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import integrations.msty.api as api_module
import ui.animations.bios_boot as bios_boot
from config.nodes import DEFAULT_NODES
from config.runtime import RuntimeConfig
from config.version import SYSTEM_VERSION
from core.cli import resolve_runtime_provider_status
from ui.animations.bios_boot import generate_bios_boot_lines


READY_PROVIDER = {
    "status": "ready",
    "active_backend": "msty-local",
    "backend": "msty-local",
    "base_url": "http://localhost:11964",
    "model_count": 9,
    "models": [
        "qwen3:latest",
        "deepseek-coder-33b-instruct.Q4_K_S:latest",
        "yi-34b-chat.Q4_K_S:latest",
        "cogito:latest",
    ],
    "required_models": {
        "ARBITER": "qwen3:latest",
        "RATIONALIS": "deepseek-coder-33b-instruct.Q4_K_S:latest",
        "AETERNUM": "yi-34b-chat.Q4_K_S:latest",
        "BELLATOR": "cogito:latest",
    },
    "missing_required_models": {},
    "mock_fallback_enabled": True,
}

DEGRADED_PROVIDER = {
    "status": "degraded",
    "active_backend": "ollama-direct",
    "backend": "ollama-direct",
    "base_url": "http://127.0.0.1:11434",
    "model_count": 1,
    "models": ["mistral:latest"],
    "required_models": READY_PROVIDER["required_models"],
    "missing_required_models": dict(READY_PROVIDER["required_models"]),
    "mock_fallback_enabled": True,
}


def _boot_post_for(provider_status: dict) -> str:
    return "\n".join(
        generate_bios_boot_lines(
            "ARASAKA",
            SYSTEM_VERSION,
            include_logo=False,
            include_loading=False,
            provider_status=provider_status,
        )
    )


def test_boot_output_matches_resolved_ready_provider_state() -> None:
    original_health = api_module.health_check
    try:
        api_module.health_check = lambda _config=None, _nodes=None: READY_PROVIDER
        resolved = resolve_runtime_provider_status(RuntimeConfig(backend="msty-local"), DEFAULT_NODES)
    finally:
        api_module.health_check = original_health

    text = _boot_post_for(resolved)

    assert resolved["status"] == "ready"
    assert resolved["missing_required_models"] == {}
    assert "[OK] Corporate Runtime" in text
    assert "MSTY PROVIDER DEGRADED" not in text
    assert "ollama-direct" not in text


def test_no_stale_provider_cache_survives_between_boot_runs() -> None:
    original_health = api_module.health_check
    states = [READY_PROVIDER, DEGRADED_PROVIDER]

    def fake_health(_config=None, _nodes=None):
        return states.pop(0)

    try:
        api_module.health_check = fake_health
        first = resolve_runtime_provider_status(RuntimeConfig(backend="msty-local"), DEFAULT_NODES)
        second = resolve_runtime_provider_status(RuntimeConfig(backend="msty-local"), DEFAULT_NODES)
    finally:
        api_module.health_check = original_health

    assert "[OK] Corporate Runtime" in _boot_post_for(first)
    assert "[WARN] MSTY PROVIDER DEGRADED (4 missing)" in _boot_post_for(second)


def test_bios_module_does_not_probe_or_fallback_provider_independently() -> None:
    source = inspect.getsource(bios_boot)
    forbidden = [
        "health_check(",
        "load_runtime_config",
        "apply_node_overrides",
        "DEFAULT_NODES",
        "OLLAMA_BASE_URL",
        "MSTY_BASE_URL",
        "ollama-direct",
    ]

    for token in forbidden:
        assert token not in source


if __name__ == "__main__":
    test_boot_output_matches_resolved_ready_provider_state()
    test_no_stale_provider_cache_survives_between_boot_runs()
    test_bios_module_does_not_probe_or_fallback_provider_independently()
    print("test_boot_provider_resolution_consistency PASS")
