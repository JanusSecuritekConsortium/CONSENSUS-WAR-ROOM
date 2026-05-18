from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Optional

from core.paths import CONFIG_PATH


@dataclass
class RuntimeConfig:
    theme: str = "military"
    backend: str = "mock"
    sequential: bool = False
    minimum_confidence: float = 0.6
    quorum: int = 2
    majority: int = 2
    high_risk_review: bool = True
    ollama_base_url: str = "http://127.0.0.1:11434"
    msty_base_url: str = "http://127.0.0.1:11964"
    msty_llama_cpp_base_url: str = "http://localhost:11454"
    mock_fallback_enabled: bool = True
    strict_provider_mode: bool = False
    use_available_model_fallback: bool = False
    refresh_model_cache: bool = False
    model_cache_ttl_seconds: int = 120
    msty_live_context_default_theme: str = "eva"
    api_host: str = "127.0.0.1"
    api_port: int = 8888
    node_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    agent_model_overrides: Dict[str, str] = field(default_factory=dict)


DEFAULT_RUNTIME_CONFIG = RuntimeConfig()


def runtime_config_to_dict(config: RuntimeConfig) -> Dict[str, Any]:
    return asdict(config)


def write_default_config(path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            json.dumps(runtime_config_to_dict(DEFAULT_RUNTIME_CONFIG), indent=2),
            encoding="utf-8",
        )


def load_runtime_config(path: Optional[Path]) -> RuntimeConfig:
    if path is None:
        path = CONFIG_PATH
    if not path.exists():
        write_default_config(path)
        return DEFAULT_RUNTIME_CONFIG

    raw = json.loads(path.read_text(encoding="utf-8"))
    base = runtime_config_to_dict(DEFAULT_RUNTIME_CONFIG)
    base.update({key: value for key, value in raw.items() if key in base})
    return RuntimeConfig(**base)


def apply_cli_overrides(config: RuntimeConfig, args: argparse.Namespace) -> RuntimeConfig:
    updates: Dict[str, Any] = {}
    for key in [
        "theme",
        "backend",
        "minimum_confidence",
        "quorum",
        "majority",
        "api_host",
        "api_port",
        "ollama_base_url",
        "msty_base_url",
        "msty_llama_cpp_base_url",
        "model_cache_ttl_seconds",
    ]:
        value = getattr(args, key, None)
        if value is not None:
            updates[key] = value
    if args.sequential:
        updates["sequential"] = True
    if args.no_high_risk_review:
        updates["high_risk_review"] = False
    if getattr(args, "no_mock_fallback", False):
        updates["mock_fallback_enabled"] = False
    if getattr(args, "strict_provider_mode", False):
        updates["strict_provider_mode"] = True
    if getattr(args, "use_available_model_fallback", False):
        updates["use_available_model_fallback"] = True
    if getattr(args, "refresh_model_cache", False):
        updates["refresh_model_cache"] = True
    return replace(config, **updates)
