from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


class FakeBackend:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def list_models(self) -> list[str]:
        return ["deepseek-coder:33b", "llama3.3:70b", "mixtral:8x7b"]


def test_provider_base_url_prefers_launcher_msty_env_before_runtime_config() -> None:
    original_msty = os.environ.get("MSTY_BASE_URL")
    original_ollama = os.environ.get("OLLAMA_BASE_URL")
    try:
        os.environ["MSTY_BASE_URL"] = "http://127.0.0.1:11964/"
        os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:11434"

        config = RuntimeConfig(backend="msty-llama-cpp", msty_llama_cpp_base_url="http://configured.local")
        assert api_module.resolve_provider_base_url(config) == "http://127.0.0.1:11964"
    finally:
        if original_msty is None:
            os.environ.pop("MSTY_BASE_URL", None)
        else:
            os.environ["MSTY_BASE_URL"] = original_msty
        if original_ollama is None:
            os.environ.pop("OLLAMA_BASE_URL", None)
        else:
            os.environ["OLLAMA_BASE_URL"] = original_ollama


def test_single_provider_resolver_keeps_msty_default_priority() -> None:
    resolution = api_module.resolve_provider(RuntimeConfig(backend="msty-local"))

    assert resolution["provider"] == "msty"
    assert resolution["requested_backend"] == "msty-llama-cpp"
    assert resolution["default_backend"] == "msty-llama-cpp"
    assert resolution["candidate_priority"][0]["backend"] == "msty-llama-cpp"
    assert all(candidate["backend"] != "msty-claw" for candidate in resolution["candidate_priority"])


def test_provider_discovery_reports_latency_and_models() -> None:
    original_backend = api_module.OllamaBackend
    try:
        api_module.OllamaBackend = FakeBackend
        payload = api_module.list_models(
            RuntimeConfig(
                backend="msty-llama-cpp",
                msty_llama_cpp_base_url="http://provider.local",
                refresh_model_cache=True,
            )
        )

        assert payload["backend"] == "msty-llama-cpp"
        assert payload["base_url"] == "http://provider.local"
        assert payload["latency_ms"] >= 0
        assert "llama3.3:70b" in payload["models"]
    finally:
        api_module.OllamaBackend = original_backend


def test_model_availability_report_marks_ready_and_missing_models() -> None:
    report = api_module.model_availability_report(
        {"RATIONALIS": "deepseek-coder:33b", "BELLATOR": "mixtral:8x7b"},
        ["deepseek-coder:33b"],
    )
    by_agent = {item["agent_id"]: item for item in report}

    assert by_agent["RATIONALIS"]["status"] == "ready"
    assert by_agent["BELLATOR"]["status"] == "missing"


if __name__ == "__main__":
    test_provider_base_url_prefers_launcher_msty_env_before_runtime_config()
    test_single_provider_resolver_keeps_msty_default_priority()
    test_provider_discovery_reports_latency_and_models()
    test_model_availability_report_marks_ready_and_missing_models()
    print("test_provider_discovery PASS")
