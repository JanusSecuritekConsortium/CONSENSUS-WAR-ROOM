from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


def test_msty_local_compatibility_alias_is_not_claw_endpoint() -> None:
    candidates = api_module._provider_candidates(RuntimeConfig(backend="msty-local"))

    assert candidates[0]["backend"] == "msty-llama-cpp"
    assert candidates[0]["base_url"] == "http://localhost:11454"
    assert not any(candidate["base_url"].endswith(":11964") for candidate in candidates)


def test_msty_local_diagnostics_include_raw_probe_routes() -> None:
    original_probe = api_module._probe_api_shape
    try:
        api_module._probe_api_shape = lambda base_url: {
            "base_url": base_url.rstrip("/"),
            "reachable": True,
            "api_shapes": ["openai_models"],
            "models": ["qwen3:latest"],
            "model_count": 1,
            "errors": {},
            "raw_routes": [
                {
                    "path": "/v1/models",
                    "status_code": 200,
                    "content_type": "application/json",
                    "detected_schema": "openai_models",
                    "models": ["qwen3:latest"],
                    "rejection_reason": "",
                }
            ],
        }
        diagnostics = api_module.provider_diagnostics(RuntimeConfig(backend="msty-local"))
        local = next(endpoint for endpoint in diagnostics["endpoints"] if endpoint["name"] == "MSTY_CLAW_SERVICE")

        assert local["raw_routes"][0]["path"] == "/v1/models"
        assert local["raw_routes"][0]["status_code"] == 200
        assert local["raw_routes"][0]["detected_schema"] == "openai_models"
    finally:
        api_module._probe_api_shape = original_probe


if __name__ == "__main__":
    test_msty_local_compatibility_alias_is_not_claw_endpoint()
    test_msty_local_diagnostics_include_raw_probe_routes()
    print("test_msty_local_primary_endpoint PASS")
