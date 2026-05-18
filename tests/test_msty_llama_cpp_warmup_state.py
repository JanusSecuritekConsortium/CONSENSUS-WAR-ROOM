from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


class SlowStartBackend:
    calls = 0

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        SlowStartBackend.calls += 1
        if SlowStartBackend.calls == 1:
            raise RuntimeError("warming")
        return ["qwen3:latest"]


def test_probe_chain_records_warming_up_before_ready(tmp_path: Path) -> None:
    original_backend = api_module.OllamaBackend
    original_cache = api_module.MODEL_CACHE_PATH
    original_sleep = api_module.time.sleep
    try:
        SlowStartBackend.calls = 0
        api_module.OllamaBackend = SlowStartBackend
        api_module.MODEL_CACHE_PATH = tmp_path / "provider_model_cache.json"
        api_module.time.sleep = lambda _seconds: None

        payload = api_module.list_models(
            RuntimeConfig(backend="msty-llama-cpp", msty_llama_cpp_base_url="http://warm.local")
        )

        statuses = [probe["status"] for probe in payload["probe_chain"]]
        assert "warming_up" in statuses
        assert statuses[-1] == "ready"
        assert payload["readiness_retry"]["result"] == "READY_AFTER_RETRY"
    finally:
        api_module.OllamaBackend = original_backend
        api_module.MODEL_CACHE_PATH = original_cache
        api_module.time.sleep = original_sleep


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_probe_chain_records_warming_up_before_ready(Path(tmp))
    print("test_msty_llama_cpp_warmup_state PASS")
