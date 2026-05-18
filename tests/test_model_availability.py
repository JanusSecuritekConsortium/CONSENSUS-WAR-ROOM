from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.nodes import DEFAULT_NODES
from config.runtime import RuntimeConfig
from integrations.msty import api as api_module


def test_model_availability_marks_missing_required_models() -> None:
    original_list_models = api_module.list_models
    try:
        api_module.list_models = lambda _config=None: {
            "backend": "msty-local",
            "base_url": "mock://provider",
            "models": ["deepseek-coder:33b"],
            "latency_ms": 12.5,
        }

        status = api_module.health_check(RuntimeConfig(backend="msty-local"), DEFAULT_NODES)

        assert status["status"] == "degraded"
        assert status["model_status"]["RATIONALIS"] == "ready"
        assert status["model_status"]["AETERNUM"] == "missing"
        assert status["model_status"]["BELLATOR"] == "missing"
        assert status["missing_required_models"]["AETERNUM"] == "llama3.3:70b"
    finally:
        api_module.list_models = original_list_models


def test_model_availability_ready_when_all_models_exist() -> None:
    original_list_models = api_module.list_models
    try:
        api_module.list_models = lambda _config=None: {
            "backend": "msty-local",
            "base_url": "mock://provider",
            "models": ["deepseek-coder:33b", "llama3.3:70b", "mixtral:8x7b"],
            "latency_ms": 4.0,
        }

        status = api_module.health_check(RuntimeConfig(backend="msty-local"), DEFAULT_NODES)

        assert status["status"] == "ready"
        assert status["missing_required_models"] == {}
        assert status["model_count"] == 3
    finally:
        api_module.list_models = original_list_models


if __name__ == "__main__":
    test_model_availability_marks_missing_required_models()
    test_model_availability_ready_when_all_models_exist()
    print("test_model_availability PASS")
