from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


class RetryThenFallbackBackend:
    llama_calls = 0

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        if self.base_url == "http://runtime.local":
            RetryThenFallbackBackend.llama_calls += 1
            raise RuntimeError("llama still starting")
        if self.base_url == "http://127.0.0.1:11434":
            return ["mistral:latest"]
        raise RuntimeError("unexpected endpoint")


def test_all_retries_fail_then_fallback_is_transparent(tmp_path: Path) -> None:
    original_backend = api_module.OllamaBackend
    original_cache = api_module.MODEL_CACHE_PATH
    original_sleep = api_module.time.sleep
    try:
        RetryThenFallbackBackend.llama_calls = 0
        api_module.OllamaBackend = RetryThenFallbackBackend
        api_module.MODEL_CACHE_PATH = tmp_path / "provider_model_cache.json"
        api_module.time.sleep = lambda _seconds: None

        payload = api_module.list_models(
            RuntimeConfig(
                backend="msty-llama-cpp",
                msty_llama_cpp_base_url="http://runtime.local",
                ollama_base_url="http://127.0.0.1:11434",
            )
        )

        assert RetryThenFallbackBackend.llama_calls == api_module.DEFAULT_READINESS_RETRY_ATTEMPTS + 1
        assert payload["active_backend"] == "ollama-direct"
        assert payload["fallback_active"] is True
        assert payload["fallback_reason"] == "endpoint unreachable after readiness retry"
        assert payload["readiness_retry"]["result"] == "FAILED_AFTER_RETRY"
    finally:
        api_module.OllamaBackend = original_backend
        api_module.MODEL_CACHE_PATH = original_cache
        api_module.time.sleep = original_sleep


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_all_retries_fail_then_fallback_is_transparent(Path(tmp))
    print("test_backend_retry_before_fallback PASS")
