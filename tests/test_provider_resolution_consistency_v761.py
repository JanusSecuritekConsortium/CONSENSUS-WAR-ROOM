from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.nodes import DEFAULT_NODES
from config.runtime import RuntimeConfig
from core.cli import resolve_runtime_provider_status
from integrations.msty import api as api_module
from integrations.msty.runtime import MstyRuntime
from ui.animations.bios_boot import generate_bios_boot_lines


class ReadyLlamaBackend:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        if self.base_url == "http://localhost:11454":
            return [
                "llama3.3:70b",
                "deepseek-coder:33b",
                "mixtral:8x7b",
                "qwen3:latest",
                "deepseek-coder-33b-instruct.Q4_K_S:latest",
                "yi-34b-chat.Q4_K_S:latest",
                "cogito:latest",
            ]
        raise RuntimeError("offline")


def test_cli_runtime_and_bios_share_resolved_provider_object() -> None:
    original_backend = api_module.OllamaBackend
    env_names = ("CONSENSUS_MSTY_BASE_URL", "MSTY_BASE_URL", "MSTY_LLAMA_CPP_BASE_URL", "OLLAMA_BASE_URL")
    original_env = {name: os.environ.get(name) for name in env_names}
    try:
        for name in env_names:
            os.environ.pop(name, None)
        api_module.OllamaBackend = ReadyLlamaBackend
        config = RuntimeConfig(backend="msty-local", model_cache_ttl_seconds=0)
        cli_status = resolve_runtime_provider_status(config, DEFAULT_NODES)
        runtime_status = MstyRuntime(config).health_check()["provider"]
        boot_text = "\n".join(
            generate_bios_boot_lines("ARASAKA", "7.6.1", provider_status=cli_status, include_logo=False)
        )

        assert cli_status["active_backend"] == runtime_status["active_backend"] == "msty-llama-cpp"
        assert cli_status["fallback_active"] is False
        assert cli_status["missing_required_models"] == {}
        assert "[OK] Corporate Runtime" in boot_text
        assert "MSTY PROVIDER DEGRADED" not in boot_text
    finally:
        api_module.OllamaBackend = original_backend
        for name, value in original_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


if __name__ == "__main__":
    test_cli_runtime_and_bios_share_resolved_provider_object()
    print("test_provider_resolution_consistency_v761 PASS")
