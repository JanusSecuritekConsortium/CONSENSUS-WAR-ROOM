from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


def test_msty_claw_and_llama_cpp_roles_are_distinct() -> None:
    original_probe = api_module._probe_api_shape
    try:
        api_module._probe_api_shape = lambda base_url: {
            "base_url": base_url.rstrip("/"),
            "reachable": True,
            "api_shapes": ["health"] if base_url.rstrip().endswith(":11964") else ["openai_models"],
            "models": [] if base_url.rstrip().endswith(":11964") else ["llama3.3:70b"],
            "model_count": 0 if base_url.rstrip().endswith(":11964") else 1,
            "errors": {},
            "raw_routes": [],
        }
        diagnostics = api_module.provider_diagnostics(RuntimeConfig())
        by_name = {endpoint["name"]: endpoint for endpoint in diagnostics["endpoints"]}

        assert by_name["MSTY_CLAW_SERVICE"]["backend"] == "msty-claw"
        assert by_name["MSTY_CLAW_SERVICE"]["service_classification"] == "tool_bridge"
        assert by_name["MSTY_CLAW_SERVICE"]["model_inference"] == "optional / not assumed"
        assert by_name["MSTY_LLAMA_CPP_SERVICE"]["backend"] == "msty-llama-cpp"
        assert by_name["MSTY_LLAMA_CPP_SERVICE"]["service_classification"] == "inference_runtime"
        assert by_name["MSTY_LLAMA_CPP_SERVICE"]["model_inference"] == "expected"
    finally:
        api_module._probe_api_shape = original_probe


if __name__ == "__main__":
    test_msty_claw_and_llama_cpp_roles_are_distinct()
    print("test_msty_service_role_classification PASS")
