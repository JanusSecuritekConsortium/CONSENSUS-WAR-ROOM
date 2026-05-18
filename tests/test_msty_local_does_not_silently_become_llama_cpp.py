from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


class EmptyButReachableMstyBackend:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        if self.base_url == "http://127.0.0.1:11964":
            return []
        if self.base_url == "http://localhost:11454":
            return ["llama3.3:70b", "deepseek-coder:33b", "mixtral:8x7b"]
        raise RuntimeError(f"unreachable {self.base_url}")


def test_reachable_msty_claw_with_no_models_stays_active_degraded() -> None:
    original_backend = api_module.OllamaBackend
    original_probe = api_module._probe_api_shape
    try:
        api_module.OllamaBackend = EmptyButReachableMstyBackend
        api_module._probe_api_shape = lambda base_url: {
            "base_url": base_url.rstrip("/"),
            "reachable": base_url.rstrip("/") == "http://127.0.0.1:11964",
            "api_shapes": ["health"],
            "models": [],
            "model_count": 0,
            "errors": {},
            "raw_routes": [
                {
                    "path": "/health",
                    "status_code": 200,
                    "content_type": "application/json",
                    "detected_schema": "health",
                    "models": [],
                    "rejection_reason": "models_not_enumerated",
                }
            ],
        }
        status = api_module.health_check(RuntimeConfig(backend="msty-claw"))

        assert status["status"] == "degraded"
        assert status["active_backend"] == "msty-claw"
        assert status["base_url"] == "http://127.0.0.1:11964"
        assert status["degraded_reason"] == "models_not_enumerated"
        assert status["fallback_active"] is False
    finally:
        api_module.OllamaBackend = original_backend
        api_module._probe_api_shape = original_probe


if __name__ == "__main__":
    test_reachable_msty_claw_with_no_models_stays_active_degraded()
    print("test_msty_local_does_not_silently_become_llama_cpp PASS")
