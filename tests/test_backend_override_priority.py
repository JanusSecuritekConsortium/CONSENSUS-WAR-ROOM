from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


def _restore_env(original: dict[str, str | None]) -> None:
    for name, value in original.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


def test_explicit_backend_selection_is_first_candidate() -> None:
    candidates = api_module._provider_candidates(RuntimeConfig(backend="msty-llama-cpp"))

    assert candidates[0]["backend"] == "msty-llama-cpp"
    assert candidates[0]["base_url"] == "http://localhost:11454"


def test_msty_local_compatibility_alias_targets_llama_cpp_inference() -> None:
    original = os.environ.get("MSTY_LLAMA_CPP_BASE_URL")
    try:
        os.environ["MSTY_LLAMA_CPP_BASE_URL"] = "http://env-llama.local"
        candidates = api_module._provider_candidates(
            RuntimeConfig(backend="msty-local", msty_llama_cpp_base_url="http://config-llama.local")
        )

        assert candidates[0]["source"] == "config_msty_llama_cpp"
        assert candidates[0]["base_url"] == "http://config-llama.local"
        assert candidates[1]["source"] == "env_msty_llama_cpp"
    finally:
        if original is None:
            os.environ.pop("MSTY_LLAMA_CPP_BASE_URL", None)
        else:
            os.environ["MSTY_LLAMA_CPP_BASE_URL"] = original


def test_launcher_consensus_env_endpoint_has_priority() -> None:
    names = ["CONSENSUS_MSTY_BASE_URL", "MSTY_BASE_URL", "MSTY_LLAMA_CPP_BASE_URL"]
    original = {name: os.environ.get(name) for name in names}
    try:
        os.environ["CONSENSUS_MSTY_BASE_URL"] = "http://127.0.0.1:11964"
        os.environ["MSTY_BASE_URL"] = "http://127.0.0.1:11454"
        candidates = api_module._provider_candidates(
            RuntimeConfig(backend="msty-local", msty_llama_cpp_base_url="http://config.local")
        )

        assert candidates[0]["source"] == "env_consensus_msty_base_url"
        assert candidates[0]["endpoint_source"] == "env"
        assert candidates[0]["base_url"] == "http://127.0.0.1:11964"
        assert candidates[1]["source"] == "env_msty_base_url"
        assert candidates[1]["base_url"] == "http://127.0.0.1:11454"
    finally:
        _restore_env(original)


def test_launcher_msty_env_endpoint_falls_back_before_config() -> None:
    names = ["CONSENSUS_MSTY_BASE_URL", "MSTY_BASE_URL", "MSTY_LLAMA_CPP_BASE_URL"]
    original = {name: os.environ.get(name) for name in names}
    try:
        os.environ.pop("CONSENSUS_MSTY_BASE_URL", None)
        os.environ["MSTY_BASE_URL"] = "http://127.0.0.1:11454"
        candidates = api_module._provider_candidates(
            RuntimeConfig(backend="msty-local", msty_llama_cpp_base_url="http://config.local")
        )

        assert candidates[0]["source"] == "env_msty_base_url"
        assert candidates[0]["endpoint_source"] == "env"
        assert candidates[0]["base_url"] == "http://127.0.0.1:11454"
        assert candidates[1]["source"] == "config_msty_llama_cpp"
    finally:
        _restore_env(original)


if __name__ == "__main__":
    test_explicit_backend_selection_is_first_candidate()
    test_msty_local_compatibility_alias_targets_llama_cpp_inference()
    test_launcher_consensus_env_endpoint_has_priority()
    test_launcher_msty_env_endpoint_falls_back_before_config()
    print("test_backend_override_priority PASS")
