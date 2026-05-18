from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.nodes import DEFAULT_NODES
from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


class HealthCacheBackend:
    calls = 0

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        HealthCacheBackend.calls += 1
        return ["llama3.3:70b", "deepseek-coder:33b", "mixtral:8x7b"]


def test_health_uses_cached_model_list_when_backend_reachable(tmp_path: Path) -> None:
    original_backend = api_module.OllamaBackend
    original_cache = api_module.MODEL_CACHE_PATH
    original_reachable = api_module._endpoint_reachable
    try:
        HealthCacheBackend.calls = 0
        api_module.OllamaBackend = HealthCacheBackend
        api_module.MODEL_CACHE_PATH = tmp_path / "provider_model_cache.json"
        api_module._endpoint_reachable = lambda base_url, timeout=1.25: (True, "test_reachable")

        config = RuntimeConfig(backend="msty-llama-cpp", msty_llama_cpp_base_url="http://runtime.local")
        first = api_module.health_check(config, DEFAULT_NODES)
        second = api_module.health_check(config, DEFAULT_NODES)

        assert first["status"] == "ready"
        assert second["status"] == "ready"
        assert second["from_cache"] is True
        assert second["model_cache"]["status"] == "hit"
        assert HealthCacheBackend.calls == 1
    finally:
        api_module.OllamaBackend = original_backend
        api_module.MODEL_CACHE_PATH = original_cache
        api_module._endpoint_reachable = original_reachable


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_health_uses_cached_model_list_when_backend_reachable(Path(tmp))
    print("test_health_uses_model_cache PASS")
