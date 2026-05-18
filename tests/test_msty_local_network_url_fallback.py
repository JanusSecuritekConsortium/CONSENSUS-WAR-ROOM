from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


REQUIRED_MODELS = ["llama3.3:70b", "deepseek-coder:33b", "mixtral:8x7b"]


class NetworkMstyBackend:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        if self.base_url == "http://localhost:11454":
            return REQUIRED_MODELS
        raise RuntimeError(f"unreachable {self.base_url}")


def test_msty_local_alias_uses_llama_cpp_not_claw_network_url() -> None:
    original_backend = api_module.OllamaBackend
    try:
        api_module.OllamaBackend = NetworkMstyBackend
        status = api_module.health_check(RuntimeConfig(backend="msty-local"))

        assert status["requested_backend"] == "msty-llama-cpp"
        assert status["active_backend"] == "msty-llama-cpp"
        assert status["base_url"] == "http://localhost:11454"
        assert status["fallback_active"] is False
    finally:
        api_module.OllamaBackend = original_backend


if __name__ == "__main__":
    test_msty_local_alias_uses_llama_cpp_not_claw_network_url()
    print("test_msty_local_network_url_fallback PASS")
