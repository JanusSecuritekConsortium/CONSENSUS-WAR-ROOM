from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

from core.paths import RESOURCE_ROOT, SYSTEM_ROOT


DATA_SOURCE_CONFIG_PATH = RESOURCE_ROOT / "config" / "data_sources.json"
DOTENV_PATH = SYSTEM_ROOT / ".env"
SECRET_FRAGMENTS = ("token", "password", "secret", "api_key", "email", "account")
ENV_BINDINGS = {
    "acled": {"token": "ACLED_TOKEN", "access_token": "ACLED_ACCESS_TOKEN", "email": "ACLED_EMAIL", "password": "ACLED_PASSWORD"},
    "factal": {"api_key": "FACTAL_API_KEY"},
    "ground_news": {"api_key": "GROUND_NEWS_API_KEY"},
    "ibkr": {"base_url": "IBKR_BASE_URL"},
    "search": {"provider": "SEARCH_PROVIDER", "api_key": "SEARCH_API_KEY"},
}


def _dotenv_values(path: Path = DOTENV_PATH) -> Dict[str, str]:
    if not path.exists():
        return {}
    values: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _env(name: str, dotenv: Dict[str, str]) -> str:
    return str(os.getenv(name) or dotenv.get(name) or "")


def load_data_source_config(path: Path | None = None) -> Dict[str, Any]:
    target = path or DATA_SOURCE_CONFIG_PATH
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("sources"), dict):
        raise RuntimeError(f"Invalid data source config: {target}")
    resolved = deepcopy(payload)
    dotenv = _dotenv_values()
    for source_id, bindings in ENV_BINDINGS.items():
        source = resolved["sources"].setdefault(source_id, {})
        for key, env_name in bindings.items():
            value = _env(env_name, dotenv)
            if value:
                source[key] = value
    return resolved


def redacted_data_source_config(config: Dict[str, Any]) -> Dict[str, Any]:
    def redact(value: Any, key: str = "") -> Any:
        lowered = key.lower()
        if any(fragment in lowered for fragment in SECRET_FRAGMENTS):
            return "***REDACTED***" if value else ""
        if isinstance(value, dict):
            return {child_key: redact(child_value, child_key) for child_key, child_value in value.items()}
        if isinstance(value, list):
            return [redact(item) for item in value]
        return value

    return redact(deepcopy(config))


def missing_credentials(source_id: str, source: Dict[str, Any]) -> list[str]:
    if source_id == "acled":
        if source.get("access_token") or source.get("token") or (source.get("email") and source.get("password")):
            return []
        return ["ACLED_ACCESS_TOKEN or ACLED_TOKEN or ACLED_EMAIL + ACLED_PASSWORD"]
    requirements = {
        "factal": ("FACTAL_API_KEY", "api_key"),
        "ground_news": ("GROUND_NEWS_API_KEY", "api_key"),
        "ibkr": ("IBKR_BASE_URL", "base_url"),
        "search": ("SEARCH_PROVIDER", "provider"),
    }
    required = requirements.get(source_id)
    return [required[0]] if required and not source.get(required[1]) else []
