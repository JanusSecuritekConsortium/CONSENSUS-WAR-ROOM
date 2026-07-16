from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from integrations.msty import api as api_module
from ui.components.status_panel import build_status_panel
from ui.themes.catalog import THEMES


class ProbeBackend:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        if self.base_url == "http://127.0.0.1:11434" or self.base_url == "http://ollama.local":
            return ["mistral:latest"]
        raise RuntimeError(f"unreachable {self.base_url}")


def _flatten_text(control) -> list[str]:
    values: list[str] = []
    if hasattr(control, "value") and isinstance(control.value, str):
        values.append(control.value)
    if hasattr(control, "content") and control.content is not None:
        values.extend(_flatten_text(control.content))
    if hasattr(control, "controls"):
        for child in control.controls:
            values.extend(_flatten_text(child))
    return values


def test_msty_unreachable_falls_back_to_ollama_direct() -> None:
    original_backend = api_module.OllamaBackend
    env_names = ("CONSENSUS_MSTY_BASE_URL", "MSTY_BASE_URL", "MSTY_LLAMA_CPP_BASE_URL", "OLLAMA_BASE_URL")
    original_env = {name: os.environ.get(name) for name in env_names}
    try:
        for name in env_names:
            os.environ.pop(name, None)
        api_module.OllamaBackend = ProbeBackend
        status = api_module.health_check(
            RuntimeConfig(
                backend="msty-local",
                msty_base_url="http://127.0.0.1:11964",
                ollama_base_url="http://127.0.0.1:11964",
                model_cache_ttl_seconds=0,
            )
        )

        assert status["active_backend"] == "ollama-direct"
        assert status["backend"] == "ollama-direct"
        assert status["base_url"] == "http://127.0.0.1:11434"
        assert status["models"] == ["mistral:latest"]
        assert status["model_count"] == 1
    finally:
        api_module.OllamaBackend = original_backend
        for name, value in original_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def test_ollama_base_url_uses_ollama_direct_label() -> None:
    original_backend = api_module.OllamaBackend
    original_env = os.environ.get("OLLAMA_BASE_URL")
    original_msty_env = os.environ.get("MSTY_BASE_URL")
    try:
        os.environ.pop("MSTY_BASE_URL", None)
        os.environ["OLLAMA_BASE_URL"] = "http://ollama.local"
        api_module.OllamaBackend = ProbeBackend
        payload = api_module.list_models(RuntimeConfig(backend="ollama", ollama_base_url=""))

        assert payload["active_backend"] == "ollama-direct"
        assert payload["backend"] == "ollama-direct"
        assert payload["base_url"] == "http://ollama.local"
        assert payload["models"] == ["mistral:latest"]
    finally:
        api_module.OllamaBackend = original_backend
        if original_env is None:
            os.environ.pop("OLLAMA_BASE_URL", None)
        else:
            os.environ["OLLAMA_BASE_URL"] = original_env
        if original_msty_env is None:
            os.environ.pop("MSTY_BASE_URL", None)
        else:
            os.environ["MSTY_BASE_URL"] = original_msty_env


def test_gui_provider_panel_shows_ollama_direct_backend() -> None:
    provider = {
        "status": "ready",
        "provider": {
            "status": "ready",
            "active_backend": "ollama-direct",
            "backend": "ollama-direct",
            "base_url": "http://127.0.0.1:11434",
            "latency_ms": 7.0,
            "model_count": 1,
            "missing_required_models": {},
        },
    }
    panel = build_status_panel(THEMES["arasaka"], provider, "AVAILABLE")
    text = "\n".join(_flatten_text(panel))

    assert "BACKEND: ollama-direct" in text
    assert "ENDPOINT: http://127.0.0.1:11434" in text


if __name__ == "__main__":
    test_msty_unreachable_falls_back_to_ollama_direct()
    test_ollama_base_url_uses_ollama_direct_label()
    test_gui_provider_panel_shows_ollama_direct_backend()
    print("test_ollama_direct_backend PASS")
