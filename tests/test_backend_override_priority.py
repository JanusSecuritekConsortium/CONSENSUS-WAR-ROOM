from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


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


if __name__ == "__main__":
    test_explicit_backend_selection_is_first_candidate()
    test_msty_local_compatibility_alias_targets_llama_cpp_inference()
    print("test_backend_override_priority PASS")
