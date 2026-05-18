from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


def test_msty_claw_is_not_in_default_inference_chain() -> None:
    candidates = api_module._provider_candidates(RuntimeConfig(backend="msty-local"))

    assert candidates[0]["backend"] == "msty-llama-cpp"
    assert all(candidate["backend"] != "msty-claw" for candidate in candidates)
    assert all(not candidate["base_url"].endswith(":11964") for candidate in candidates)


if __name__ == "__main__":
    test_msty_claw_is_not_in_default_inference_chain()
    print("test_msty_claw_not_default_inference_backend PASS")
