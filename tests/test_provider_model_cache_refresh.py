from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


class RefreshBackend:
    calls = 0

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        RefreshBackend.calls += 1
        return ["llama3.3:70b", "deepseek-coder:33b", "mixtral:8x7b"]


def test_refresh_model_cache_bypasses_existing_cache(tmp_path: Path) -> None:
    original_backend = api_module.OllamaBackend
    original_cache = api_module.MODEL_CACHE_PATH
    original_reachable = api_module._endpoint_reachable
    try:
        RefreshBackend.calls = 0
        api_module.OllamaBackend = RefreshBackend
        api_module.MODEL_CACHE_PATH = tmp_path / "provider_model_cache.json"
        api_module._endpoint_reachable = lambda base_url, timeout=1.25: (True, "test_reachable")

        base_config = RuntimeConfig(backend="msty-llama-cpp", msty_llama_cpp_base_url="http://runtime.local")
        refresh_config = RuntimeConfig(
            backend="msty-llama-cpp",
            msty_llama_cpp_base_url="http://runtime.local",
            refresh_model_cache=True,
        )
        api_module.list_models(base_config)
        hit = api_module.list_models(base_config)
        refreshed = api_module.list_models(refresh_config)

        assert hit["from_cache"] is True
        assert refreshed["from_cache"] is False
        assert refreshed["model_cache"]["status"] == "refresh"
        assert RefreshBackend.calls == 2
    finally:
        api_module.OllamaBackend = original_backend
        api_module.MODEL_CACHE_PATH = original_cache
        api_module._endpoint_reachable = original_reachable


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_refresh_model_cache_bypasses_existing_cache(Path(tmp))
    print("test_provider_model_cache_refresh PASS")
