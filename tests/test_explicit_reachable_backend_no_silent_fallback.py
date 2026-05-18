from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


class EmptyReachableBackend:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        if self.base_url == "http://localhost:11454":
            return []
        if self.base_url == "http://127.0.0.1:11434":
            return ["mistral:latest"]
        raise RuntimeError("offline")


def test_explicit_reachable_llama_cpp_does_not_fallback_to_ollama_when_models_missing(tmp_path: Path) -> None:
    original_backend = api_module.OllamaBackend
    original_probe = api_module._probe_api_shape
    original_cache = api_module.MODEL_CACHE_PATH
    try:
        api_module.OllamaBackend = EmptyReachableBackend
        api_module.MODEL_CACHE_PATH = tmp_path / "provider_model_cache.json"
        api_module._probe_api_shape = lambda base_url: {
            "base_url": base_url.rstrip("/"),
            "reachable": base_url.rstrip("/") == "http://localhost:11454",
            "api_shapes": ["health"],
            "models": [],
            "model_count": 0,
            "errors": {},
            "raw_routes": [],
        }
        status = api_module.health_check(RuntimeConfig(backend="msty-llama-cpp"))

        assert status["status"] == "degraded"
        assert status["active_backend"] == "msty-llama-cpp"
        assert status["base_url"] == "http://localhost:11454"
        assert status["degraded_reason"] == "models_not_enumerated"
        assert status["fallback_active"] is False
    finally:
        api_module.OllamaBackend = original_backend
        api_module._probe_api_shape = original_probe
        api_module.MODEL_CACHE_PATH = original_cache


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_explicit_reachable_llama_cpp_does_not_fallback_to_ollama_when_models_missing(Path(tmp))
    print("test_explicit_reachable_backend_no_silent_fallback PASS")
