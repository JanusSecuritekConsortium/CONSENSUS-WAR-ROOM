from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


def test_provider_candidate_priority_uses_llama_cpp_before_ollama_fallback() -> None:
    original_msty = os.environ.get("MSTY_BASE_URL")
    original_ollama = os.environ.get("OLLAMA_BASE_URL")
    original_llama = os.environ.get("MSTY_LLAMA_CPP_BASE_URL")
    try:
        os.environ.pop("MSTY_BASE_URL", None)
        os.environ.pop("OLLAMA_BASE_URL", None)
        os.environ.pop("MSTY_LLAMA_CPP_BASE_URL", None)
        config = RuntimeConfig(
            backend="msty-local",
            msty_base_url="http://127.0.0.1:11964",
            ollama_base_url="http://127.0.0.1:11434",
            msty_llama_cpp_base_url="http://localhost:11454",
        )
        candidates = api_module._provider_candidates(config)
        sources = [candidate["source"] for candidate in candidates]

        assert sources[:2] == [
            "config_msty_llama_cpp",
            "config_ollama",
        ]
        assert candidates[0]["base_url"] == "http://localhost:11454"
    finally:
        for key, value in {
            "MSTY_BASE_URL": original_msty,
            "OLLAMA_BASE_URL": original_ollama,
            "MSTY_LLAMA_CPP_BASE_URL": original_llama,
        }.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_llama_cpp_candidate_only_when_selected() -> None:
    candidates = api_module._provider_candidates(RuntimeConfig(backend="msty-llama-cpp"))

    assert candidates[0]["source"] == "config_msty_llama_cpp"
    assert candidates[0]["base_url"] == "http://localhost:11454"
    assert candidates[1]["backend"] == "ollama-direct"


def test_msty_claw_is_separate_explicit_backend() -> None:
    original = os.environ.get("MSTY_BASE_URL")
    try:
        os.environ["MSTY_BASE_URL"] = "http://explicit-msty.local/"
        candidates = api_module._provider_candidates(RuntimeConfig(backend="msty-claw"))

        assert candidates[0]["source"] == "config_msty_claw"
        assert candidates[0]["base_url"] == "http://127.0.0.1:11964"
    finally:
        if original is None:
            os.environ.pop("MSTY_BASE_URL", None)
        else:
            os.environ["MSTY_BASE_URL"] = original


def test_provider_diagnostics_reports_named_services_and_shapes() -> None:
    original_probe = api_module._probe_api_shape
    try:
        api_module._probe_api_shape = lambda base_url: {
            "base_url": base_url.rstrip("/"),
            "reachable": base_url.rstrip("/") in {"http://127.0.0.1:11964", "http://localhost:11454", "http://127.0.0.1:11434"},
            "api_shapes": ["health"] if base_url.rstrip("/") == "http://127.0.0.1:11964" else ["ollama_tags"],
            "models": [] if base_url.rstrip("/") == "http://127.0.0.1:11964" else ["mistral:latest"],
            "model_count": 1,
            "errors": {},
            "raw_routes": [],
        }
        diagnostics = api_module.provider_diagnostics(RuntimeConfig())
        by_name = {entry["name"]: entry for entry in diagnostics["endpoints"]}

        assert by_name["MSTY_CLAW_SERVICE"]["base_url"] == "http://127.0.0.1:11964"
        assert by_name["MSTY_CLAW_SERVICE"]["reachable"] is True
        assert by_name["MSTY_CLAW_SERVICE"]["service_classification"] == "tool_bridge"
        assert by_name["OLLAMA_DIRECT"]["base_url"] == "http://127.0.0.1:11434"
        assert by_name["MSTY_LLAMA_CPP_SERVICE"]["base_url"] == "http://localhost:11454"
    finally:
        api_module._probe_api_shape = original_probe


if __name__ == "__main__":
    test_provider_candidate_priority_uses_llama_cpp_before_ollama_fallback()
    test_llama_cpp_candidate_only_when_selected()
    test_msty_claw_is_separate_explicit_backend()
    test_provider_diagnostics_reports_named_services_and_shapes()
    print("test_provider_diagnostics PASS")
