from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


REQUIRED_MODELS = [
    "llama3.3:70b",
    "deepseek-coder:33b",
    "mixtral:8x7b",
    "qwen3:latest",
    "deepseek-coder-33b-instruct.Q4_K_S:latest",
    "yi-34b-chat.Q4_K_S:latest",
    "cogito:latest",
]


class ChainBackend:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        if self.base_url == "http://localhost:11454":
            return REQUIRED_MODELS
        if self.base_url == "http://127.0.0.1:11434":
            return ["mistral:latest"]
        raise RuntimeError(f"unreachable {self.base_url}")


def test_fallback_chain_uses_msty_llama_cpp_before_ollama() -> None:
    original_backend = api_module.OllamaBackend
    try:
        api_module.OllamaBackend = ChainBackend
        status = api_module.health_check(RuntimeConfig(backend="msty-local"))

        assert status["status"] == "ready"
        assert status["requested_backend"] == "msty-llama-cpp"
        assert status["active_backend"] == "msty-llama-cpp"
        assert status["base_url"] == "http://localhost:11454"
        assert status["fallback_active"] is False
        assert status["fallback_reason"] is None
        assert status["missing_required_models"] == {}
    finally:
        api_module.OllamaBackend = original_backend


if __name__ == "__main__":
    test_fallback_chain_uses_msty_llama_cpp_before_ollama()
    print("test_fallback_resolution_chain PASS")
