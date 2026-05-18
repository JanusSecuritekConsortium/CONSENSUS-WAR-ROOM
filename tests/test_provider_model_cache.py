from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


MODELS = ["llama3.3:70b", "deepseek-coder:33b", "mixtral:8x7b"]


class CountingBackend:
    calls = 0

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        CountingBackend.calls += 1
        return MODELS


def test_second_model_check_uses_cache_and_key_separates_endpoints(tmp_path: Path) -> None:
    original_backend = api_module.OllamaBackend
    original_cache = api_module.MODEL_CACHE_PATH
    original_reachable = api_module._endpoint_reachable
    try:
        CountingBackend.calls = 0
        api_module.OllamaBackend = CountingBackend
        api_module.MODEL_CACHE_PATH = tmp_path / "provider_model_cache.json"
        api_module._endpoint_reachable = lambda base_url, timeout=1.25: (True, "test_reachable")

        config = RuntimeConfig(backend="msty-llama-cpp", msty_llama_cpp_base_url="http://runtime-a.local")
        first = api_module.list_models(config)
        second = api_module.list_models(config)
        other = api_module.list_models(
            RuntimeConfig(backend="msty-llama-cpp", msty_llama_cpp_base_url="http://runtime-b.local")
        )

        assert first["from_cache"] is False
        assert first["model_cache"]["status"] == "miss"
        assert second["from_cache"] is True
        assert second["model_cache"]["status"] == "hit"
        assert other["from_cache"] is False
        assert CountingBackend.calls == 2
    finally:
        api_module.OllamaBackend = original_backend
        api_module.MODEL_CACHE_PATH = original_cache
        api_module._endpoint_reachable = original_reachable


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_second_model_check_uses_cache_and_key_separates_endpoints(Path(tmp))
    print("test_provider_model_cache PASS")
