from __future__ import annotations

import json
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.msty.aurelius_provider import (
    MSTY_PROVIDER_ENDPOINT_NOT_CONFIGURED,
    ProviderErrorGate,
    resolve_aurelius_provider_config,
)

BOT_PATH = ROOT / "_ARBITER" / "Bot" / "aurelius_bot.py"


def _load_aurelius_bot():
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda *_args, **_kwargs: False
    previous = sys.modules.get("dotenv")
    sys.modules["dotenv"] = dotenv
    try:
        spec = importlib.util.spec_from_file_location("aurelius_bot_under_test", BOT_PATH)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if previous is None:
            sys.modules.pop("dotenv", None)
        else:
            sys.modules["dotenv"] = previous


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
    assert config.base_url_env == "AURELIUS_MSTY_BASE_URL"
    assert config.endpoint_source == "env"
    assert config.fallback_enabled is False


def test_aurelius_uses_msty_base_url_when_aurelius_env_missing() -> None:
    config = resolve_aurelius_provider_config(
        {
            "AURELIUS_PROVIDER": "msty",
            "MSTY_BASE_URL": "http://localhost:11964",
        }
    )

    assert config.ready
    assert config.base_url == "http://localhost:11964"
    assert config.base_url_env == "MSTY_BASE_URL"
    assert config.endpoint_source == "env"


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
    bot_source = BOT_PATH.read_text(encoding="utf-8")

    assert "localhost:11434" not in bot_source
    assert "127.0.0.1:11434" not in bot_source
    assert 'api_key = "ollama"' not in bot_source
    assert "from integrations.msty.aurelius_provider import" in bot_source
    assert "send_morning_brief" in bot_source
    assert "send_end_of_day_shutdown" in bot_source


def test_aurelius_bot_has_no_direct_ibkr_import() -> None:
    bot_source = BOT_PATH.read_text(encoding="utf-8")

    assert "ib_insync" not in bot_source
    assert "execute_ibkr_trade" not in bot_source


def test_anima_bot_is_archived_and_launchers_use_aurelius() -> None:
    bot_dir = ROOT / "_ARBITER" / "Bot"
    ecosystem = (bot_dir / "ecosystem.config.js").read_text(encoding="utf-8")
    launcher = (bot_dir / "aurelius_launcher.bat").read_text(encoding="utf-8")

    assert not (bot_dir / "anima_bot.py").exists()
    assert (ROOT / "archive" / "legacy_bots" / "anima_bot.py").exists()
    assert not (bot_dir / "anima_launcher.bat").exists()
    assert "aurelius_bot.py" in ecosystem
    assert "aurelius_bot.py" in launcher
    assert "anima_bot.py" not in ecosystem
    assert "anima_bot.py" not in launcher


def test_aurelius_bot_missing_telegram_token_is_clear() -> None:
    bot_module = _load_aurelius_bot()

    try:
        bot_module.validate_startup({})
    except RuntimeError as exc:
        assert "Missing TELEGRAM_BOT_TOKEN" in str(exc)
    else:
        raise AssertionError("missing Telegram token must fail startup validation")


def test_active_telegram_dependencies_are_declared_without_ibkr() -> None:
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert "openai" in requirements
    assert "python-dotenv" in requirements
    assert "schedule" in requirements
    assert "pyTelegramBotAPI" in requirements
    assert "requests" in requirements
    assert "ib_insync" not in requirements


def test_aurelius_bot_compiles() -> None:
    import py_compile

    py_compile.compile(str(BOT_PATH), doraise=True)


if __name__ == "__main__":
    test_aurelius_defaults_to_msty_without_ollama_endpoint()
    test_aurelius_uses_msty_env_endpoint()
    test_aurelius_uses_msty_base_url_when_aurelius_env_missing()
    test_aurelius_rejects_ollama_provider_and_port()
    test_provider_error_gate_logs_once()
    test_active_aurelius_config_is_msty_only()
    test_aurelius_bot_no_direct_ollama_endpoint()
    test_aurelius_bot_has_no_direct_ibkr_import()
    test_anima_bot_is_archived_and_launchers_use_aurelius()
    test_aurelius_bot_missing_telegram_token_is_clear()
    test_active_telegram_dependencies_are_declared_without_ibkr()
    test_aurelius_bot_compiles()
    print("test_aurelius_provider_config PASS")
