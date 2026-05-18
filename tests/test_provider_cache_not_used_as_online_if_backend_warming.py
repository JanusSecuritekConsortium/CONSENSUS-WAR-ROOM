from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


class CacheWarmBackend:
    offline = False

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        if CacheWarmBackend.offline:
            raise RuntimeError("offline")
        return ["qwen3:latest"]


def test_cache_does_not_report_ready_when_reachability_fails_during_warmup(tmp_path: Path) -> None:
    original_backend = api_module.OllamaBackend
    original_cache = api_module.MODEL_CACHE_PATH
    original_reachable = api_module._endpoint_reachable
    original_sleep = api_module.time.sleep
    try:
        api_module.OllamaBackend = CacheWarmBackend
        api_module.MODEL_CACHE_PATH = tmp_path / "provider_model_cache.json"
        api_module.time.sleep = lambda _seconds: None
        config = RuntimeConfig(backend="msty-llama-cpp", msty_llama_cpp_base_url="http://runtime.local")

        CacheWarmBackend.offline = False
        api_module._endpoint_reachable = lambda base_url, timeout=1.25: (True, "reachable")
        first = api_module.list_models(config)
        assert first["status"] == "ready"

        CacheWarmBackend.offline = True
        api_module._endpoint_reachable = lambda base_url, timeout=1.25: (False, "warming")
        second = api_module.list_models(config)

        assert second["from_cache"] is False
        assert second["active_backend"] != "msty-llama-cpp" or second["status"] != "ready"
        assert any(probe.get("stale_cache_available") for probe in second["probe_chain"])
        assert second["readiness_retry"]["result"] == "FAILED_AFTER_RETRY"
    finally:
        api_module.OllamaBackend = original_backend
        api_module.MODEL_CACHE_PATH = original_cache
        api_module._endpoint_reachable = original_reachable
        api_module.time.sleep = original_sleep


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_cache_does_not_report_ready_when_reachability_fails_during_warmup(Path(tmp))
    print("test_provider_cache_not_used_as_online_if_backend_warming PASS")
