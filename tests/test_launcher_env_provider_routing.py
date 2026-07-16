from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


MODELS = ["llama3.3:70b", "deepseek-coder:33b", "mixtral:8x7b"]


class EndpointAwareBackend:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        if self.base_url in {"http://127.0.0.1:11964", "http://127.0.0.1:11454"}:
            return MODELS
        raise RuntimeError(f"unreachable {self.base_url}")


def _restore_env(original: dict[str, str | None]) -> None:
    for name, value in original.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


def _run_health_with_env(env: dict[str, str]) -> dict:
    names = ["CONSENSUS_MSTY_BASE_URL", "MSTY_BASE_URL", "MSTY_LLAMA_CPP_BASE_URL"]
    original_env = {name: os.environ.get(name) for name in names}
    original_backend = api_module.OllamaBackend
    try:
        for name in names:
            os.environ.pop(name, None)
        os.environ.update(env)
        api_module.OllamaBackend = EndpointAwareBackend
        return api_module.health_check(
            RuntimeConfig(
                backend="msty-local",
                msty_llama_cpp_base_url="http://config.local",
                model_cache_ttl_seconds=0,
            )
        )
    finally:
        api_module.OllamaBackend = original_backend
        _restore_env(original_env)


def test_consensus_msty_base_url_drives_provider_status() -> None:
    status = _run_health_with_env(
        {
            "CONSENSUS_MSTY_BASE_URL": "http://127.0.0.1:11964",
            "MSTY_BASE_URL": "http://127.0.0.1:11454",
        }
    )

    assert status["status"] == "ready"
    assert status["base_url"] == "http://127.0.0.1:11964"
    assert status["endpoint_source"] == "env"
    assert status["source"] == "env_consensus_msty_base_url"


def test_msty_base_url_drives_provider_status_when_consensus_env_missing() -> None:
    status = _run_health_with_env({"MSTY_BASE_URL": "http://127.0.0.1:11454"})

    assert status["status"] == "ready"
    assert status["base_url"] == "http://127.0.0.1:11454"
    assert status["endpoint_source"] == "env"
    assert status["source"] == "env_msty_base_url"


if __name__ == "__main__":
    test_consensus_msty_base_url_drives_provider_status()
    test_msty_base_url_drives_provider_status_when_consensus_env_missing()
    print("test_launcher_env_provider_routing PASS")
