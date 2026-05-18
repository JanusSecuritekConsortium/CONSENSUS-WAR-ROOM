from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


class FlakyBackend:
    offline = False

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        if FlakyBackend.offline:
            raise RuntimeError("offline")
        return ["llama3.3:70b", "deepseek-coder:33b", "mixtral:8x7b"]


def test_stale_cache_does_not_make_offline_backend_ready(tmp_path: Path) -> None:
    original_backend = api_module.OllamaBackend
    original_cache = api_module.MODEL_CACHE_PATH
    original_reachable = api_module._endpoint_reachable
    try:
        FlakyBackend.offline = False
        api_module.OllamaBackend = FlakyBackend
        api_module.MODEL_CACHE_PATH = tmp_path / "provider_model_cache.json"
        api_module._endpoint_reachable = lambda base_url, timeout=1.25: (True, "test_reachable")

        config = RuntimeConfig(backend="msty-llama-cpp", msty_llama_cpp_base_url="http://runtime.local")
        warm = api_module.list_models(config)
        assert warm["status"] == "ready"

        FlakyBackend.offline = True
        api_module._endpoint_reachable = lambda base_url, timeout=1.25: (False, "offline")
        offline = api_module.list_models(config)

        assert offline["status"] == "offline"
        assert offline["from_cache"] is False
        assert any(probe.get("stale_cache_available") for probe in offline["probe_chain"])
    finally:
        api_module.OllamaBackend = original_backend
        api_module.MODEL_CACHE_PATH = original_cache
        api_module._endpoint_reachable = original_reachable


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_stale_cache_does_not_make_offline_backend_ready(Path(tmp))
    print("test_provider_model_cache_does_not_mask_backend_failure PASS")
