from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.msty.aurelius_provider import (
    MSTY_PROVIDER_ENDPOINT_NOT_CONFIGURED,
    ProviderErrorGate,
    resolve_aurelius_provider_config,
)


def test_aurelius_defaults_to_msty_without_ollama_endpoint() -> None:
    config = resolve_aurelius_provider_config({})

    assert config.provider == "msty"
    assert config.status == "DEGRADED"
    assert config.degraded_reason == MSTY_PROVIDER_ENDPOINT_NOT_CONFIGURED
    assert config.fallback_enabled is False
    assert config.base_url is None


def test_aurelius_uses_msty_env_endpoint() -> None:
    config = resolve_aurelius_provider_config(
        {
            "AURELIUS_PROVIDER": "msty",
            "AURELIUS_MSTY_BASE_URL": "http://localhost:11454",
            "AURELIUS_PROVIDER_FALLBACK_ENABLED": "false",
        }
    )

    assert config.ready
    assert config.provider == "msty"
    assert config.base_url == "http://localhost:11454"
    assert config.api_base_url == "http://localhost:11454/v1"
    assert config.fallback_enabled is False


def test_aurelius_rejects_ollama_provider_and_port() -> None:
    provider_config = resolve_aurelius_provider_config(
        {
            "AURELIUS_PROVIDER": "ollama",
            "AURELIUS_MSTY_BASE_URL": "http://localhost:11434",
        }
    )
    port_config = resolve_aurelius_provider_config(
        {
            "AURELIUS_PROVIDER": "msty",
            "AURELIUS_MSTY_BASE_URL": "http://localhost:11434",
        }
    )

    assert provider_config.provider == "msty"
    assert provider_config.status == "DEGRADED"
    assert "Ollama provider is disabled" in str(provider_config.degraded_reason)
    assert port_config.status == "DEGRADED"
    assert port_config.base_url is None


def test_provider_error_gate_logs_once() -> None:
    gate = ProviderErrorGate()

    assert gate.should_log("scheduled:msty-missing") is True
    assert gate.should_log("scheduled:msty-missing") is False
    assert gate.should_log("manual:msty-missing") is True


def test_active_aurelius_config_is_msty_only() -> None:
    config = json.loads((ROOT / "_ARBITER" / "config.json").read_text(encoding="utf-8"))
    llm = config["llm"]

    assert llm["provider"] == "msty"
    assert llm["base_url"] == ""
    assert llm["base_url_env"] == "AURELIUS_MSTY_BASE_URL"
    assert llm["fallback_enabled"] is False


def test_aurelius_bot_no_direct_ollama_endpoint() -> None:
    bot_source = (ROOT / "_ARBITER" / "Bot" / "anima_bot.py").read_text(encoding="utf-8")

    assert "localhost:11434" not in bot_source
    assert "127.0.0.1:11434" not in bot_source
    assert 'api_key = "ollama"' not in bot_source
    assert "send_morning_brief" in bot_source
    assert "send_end_of_day_shutdown" in bot_source


def test_aurelius_bot_compiles() -> None:
    import py_compile

    py_compile.compile(str(ROOT / "_ARBITER" / "Bot" / "anima_bot.py"), doraise=True)


if __name__ == "__main__":
    test_aurelius_defaults_to_msty_without_ollama_endpoint()
    test_aurelius_uses_msty_env_endpoint()
    test_aurelius_rejects_ollama_provider_and_port()
    test_provider_error_gate_logs_once()
    test_active_aurelius_config_is_msty_only()
    test_aurelius_bot_no_direct_ollama_endpoint()
    test_aurelius_bot_compiles()
    print("test_aurelius_provider_config PASS")
