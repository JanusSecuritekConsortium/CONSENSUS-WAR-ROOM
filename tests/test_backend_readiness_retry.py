from __future__ import annotations

import sys
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from core.cli import _print_provider_resolution
from integrations.msty import api as api_module


REQUIRED_MODELS = [
    "qwen3:latest",
    "deepseek-coder-33b-instruct.Q4_K_S:latest",
    "yi-34b-chat.Q4_K_S:latest",
    "cogito:latest",
]


class WarmupBackend:
    calls = 0

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        WarmupBackend.calls += 1
        if WarmupBackend.calls == 1:
            raise RuntimeError("startup socket not ready")
        return REQUIRED_MODELS


def test_first_failed_probe_second_success_resolves_to_llama_cpp(tmp_path: Path) -> None:
    original_backend = api_module.OllamaBackend
    original_cache = api_module.MODEL_CACHE_PATH
    original_sleep = api_module.time.sleep
    try:
        WarmupBackend.calls = 0
        api_module.OllamaBackend = WarmupBackend
        api_module.MODEL_CACHE_PATH = tmp_path / "provider_model_cache.json"
        api_module.time.sleep = lambda _seconds: None

        payload = api_module.list_models(
            RuntimeConfig(backend="msty-llama-cpp", msty_llama_cpp_base_url="http://runtime.local")
        )

        assert payload["status"] == "ready"
        assert payload["active_backend"] == "msty-llama-cpp"
        assert payload["fallback_active"] is False
        assert payload["readiness_retry"]["enabled"] is True
        assert payload["readiness_retry"]["result"] == "READY_AFTER_RETRY"
        assert payload["readiness_retry"]["warmup_retries"] == 1
        buffer = StringIO()
        with redirect_stdout(buffer):
            _print_provider_resolution(payload, verbose=True)
        output = buffer.getvalue()
        assert "READINESS RETRY: ENABLED" in output
        assert "READINESS ATTEMPTS: 3" in output
        assert "READINESS RESULT: READY_AFTER_RETRY" in output
    finally:
        api_module.OllamaBackend = original_backend
        api_module.MODEL_CACHE_PATH = original_cache
        api_module.time.sleep = original_sleep


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_first_failed_probe_second_success_resolves_to_llama_cpp(Path(tmp))
    print("test_backend_readiness_retry PASS")
