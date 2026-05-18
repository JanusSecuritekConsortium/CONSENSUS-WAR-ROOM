from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import ARBITER, TRIBUNAL_AGENT_IDS
from config.nodes import DEFAULT_NODES
from config.runtime import RuntimeConfig, runtime_config_to_dict
from core.cli import main as cli_main
from integrations.msty import api as api_module
from integrations.msty.runtime import MstyRuntime


class MistralOnlyBackend:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        return ["mistral:latest"]


def test_available_model_remap_marks_degraded_but_usable() -> None:
    original_backend = api_module.OllamaBackend
    original_cache = api_module.MODEL_CACHE_PATH
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            api_module.MODEL_CACHE_PATH = Path(tmpdir) / "provider_model_cache.json"
            api_module.OllamaBackend = MistralOnlyBackend
            status = api_module.health_check(
                RuntimeConfig(
                    backend="msty-local",
                    use_available_model_fallback=True,
                ),
                DEFAULT_NODES,
            )

        assert status["status"] == "degraded"
        assert status["mode"] == "DEGRADED_MODEL_REMAP"
        assert status["model_remap_active"] is True
        assert status["model_remap_model"] == "mistral:latest"
        assert status["fallback_active"] is False
    finally:
        api_module.OllamaBackend = original_backend
        api_module.MODEL_CACHE_PATH = original_cache


def test_runtime_uses_remapped_model_instead_of_mock_fallback() -> None:
    original_health = api_module.health_check
    original_send = api_module.send_prompt
    captured: dict[str, str] = {}
    try:
        api_module.health_check = lambda _config=None, _nodes=None: {
            "status": "degraded",
            "active_backend": "ollama-direct",
            "backend": "ollama-direct",
            "base_url": "http://127.0.0.1:11434",
            "models": ["mistral:latest"],
            "missing_required_models": {"RATIONALIS": "deepseek-coder:33b"},
            "model_remap_active": True,
            "model_remap_model": "mistral:latest",
        }

        def fake_send(model, *_args, **kwargs):
            captured["model"] = model
            captured["base_url"] = kwargs.get("base_url")
            return "VOTE: APPROVE\nCONFIDENCE: 0.80\nREASONING: remapped model path\n"

        api_module.send_prompt = fake_send
        response = MstyRuntime(RuntimeConfig(backend="msty-local", use_available_model_fallback=True)).send_to_agent(
            "RATIONALIS",
            "test proposal",
            {"model": "deepseek-coder:33b"},
        )

        assert "VOTE: APPROVE" in response
        assert captured["model"] == "mistral:latest"
        assert captured["base_url"] == "http://127.0.0.1:11434"
    finally:
        api_module.health_check = original_health
        api_module.send_prompt = original_send


def test_set_all_models_updates_runtime_config() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "genesis_config.json"
        config_path.write_text(json.dumps(runtime_config_to_dict(RuntimeConfig()), indent=2), encoding="utf-8")
        stdout = io.StringIO()
        original_argv = sys.argv
        try:
            sys.argv = ["main.py", "--config", str(config_path), "--set-all-models", "mistral:latest"]
            with contextlib.redirect_stdout(stdout):
                cli_main()
        finally:
            sys.argv = original_argv

        data = json.loads(config_path.read_text(encoding="utf-8"))

    assert data["agent_model_overrides"][ARBITER] == "mistral:latest"
    for agent_id in TRIBUNAL_AGENT_IDS:
        assert data["agent_model_overrides"][agent_id] == "mistral:latest"
        assert data["node_overrides"][agent_id]["model"] == "mistral:latest"


if __name__ == "__main__":
    test_available_model_remap_marks_degraded_but_usable()
    test_runtime_uses_remapped_model_instead_of_mock_fallback()
    test_set_all_models_updates_runtime_config()
    print("test_model_remap_fallback PASS")
