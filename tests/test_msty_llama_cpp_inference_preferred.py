from __future__ import annotations

import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


class LlamaCppBackend:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        if self.base_url == "http://localhost:11454":
            return ["llama3.3:70b", "deepseek-coder:33b", "mixtral:8x7b"]
        if self.base_url == "http://127.0.0.1:11964":
            return ["tool-bridge"]
        if self.base_url == "http://127.0.0.1:11434":
            return ["mistral:latest"]
        raise RuntimeError("offline")


def test_msty_llama_cpp_is_default_inference_runtime() -> None:
    original_backend = api_module.OllamaBackend
    env_names = ("CONSENSUS_MSTY_BASE_URL", "MSTY_BASE_URL", "MSTY_LLAMA_CPP_BASE_URL", "OLLAMA_BASE_URL")
    original_env = {name: os.environ.get(name) for name in env_names}
    try:
        for name in env_names:
            os.environ.pop(name, None)
        api_module.OllamaBackend = LlamaCppBackend
        status = api_module.health_check(RuntimeConfig(backend="msty-local", refresh_model_cache=True))

        assert status["active_backend"] == "msty-llama-cpp"
        assert status["base_url"] == "http://localhost:11454"
    finally:
        api_module.OllamaBackend = original_backend
        for name, value in original_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


if __name__ == "__main__":
    test_msty_llama_cpp_is_default_inference_runtime()
    print("test_msty_llama_cpp_inference_preferred PASS")
