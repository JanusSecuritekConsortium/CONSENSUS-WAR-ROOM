from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.nodes import DEFAULT_NODES, apply_node_overrides
from config.runtime import load_runtime_config
from core.paths import CONFIG_PATH
from integrations.msty.api import health_check, validate_health_endpoint


def build_provider_status_report(config_path: Path | None = None) -> dict[str, Any]:
    config = load_runtime_config(config_path or CONFIG_PATH)
    nodes = apply_node_overrides(DEFAULT_NODES, config.node_overrides)
    status = health_check(config, nodes)
    endpoint = status.get("selected_endpoint") or status.get("base_url")
    endpoint_validity = status.get("health_endpoint") or {}
    if endpoint and not endpoint_validity:
        endpoint_validity = validate_health_endpoint(str(endpoint))

    return {
        "provider": "msty",
        "status": status.get("status"),
        "backend": status.get("active_backend") or status.get("backend"),
        "requested_backend": status.get("requested_backend"),
        "endpoint": endpoint,
        "endpoint_source": status.get("endpoint_source"),
        "selected_backend": status.get("selected_backend") or status.get("active_backend") or status.get("backend"),
        "selected_endpoint": endpoint,
        "endpoint_validity": endpoint_validity,
        "active_models": status.get("models", []),
        "model_availability_report": status.get("model_availability_report", []),
        "missing_models": status.get("missing_required_models", {}),
        "degraded_reason": status.get("degraded_reason"),
        "fallback_active": status.get("fallback_active"),
        "fallback_reason": status.get("fallback_reason"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export current CONSENSUS provider status.")
    parser.add_argument("--config", type=Path, default=None, help="Runtime config path.")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON.")
    args = parser.parse_args()

    report = build_provider_status_report(args.config)
    print(json.dumps(report, indent=None if args.compact else 2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
