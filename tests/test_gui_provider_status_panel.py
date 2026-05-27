from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.status_panel import build_status_panel
from ui.themes.catalog import THEMES


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


def test_gui_provider_status_panel_shows_discovery_metadata() -> None:
    provider = {
        "status": "degraded",
        "fallback_enabled": True,
        "provider": {
            "status": "degraded",
            "base_url": "http://127.0.0.1:11964",
            "latency_ms": 13.2,
            "model_count": 2,
            "missing_required_models": {"BELLATOR": "mixtral:8x7b"},
        },
    }

    panel = build_status_panel(THEMES["eva"], provider, "1.2GB / 32GB", provider_warning="PROVIDER DEGRADED - MOCK FALLBACK ACTIVE")
    text = "\n".join(_flatten_text(panel))

    assert "ENDPOINT: http://127.0.0.1:11964" in text
    assert "LATENCY: 13.2 ms" in text
    assert "MODELS: 2" in text
    assert "BELLATOR:mixtral:8x7b" in text
    assert "FALLBACK: ACTIVE" in text


def test_gui_provider_status_panel_shows_active_models_and_dev_status() -> None:
    provider = {
        "status": "ready",
        "provider": {
            "status": "ready",
            "base_url": "http://localhost:11454",
            "model_availability_report": [
                {
                    "agent_id": "RATIONALIS",
                    "required_model": "deepseek-coder:33b",
                    "resolved_model": "deepseek-coder:33b",
                    "status": "ready",
                }
            ],
        },
    }

    panel = build_status_panel(THEMES["eva"], provider, "AVAILABLE")
    text = "\n".join(_flatten_text(panel))

    assert "ACTIVE MODELS" in text
    assert "RATIONALIS: deepseek-coder:33b [READY]" in text
    assert "CODEX / DEV" in text
    assert "RUNTIME LOGS: JSONL" in text


if __name__ == "__main__":
    test_gui_provider_status_panel_shows_discovery_metadata()
    test_gui_provider_status_panel_shows_active_models_and_dev_status()
    print("test_gui_provider_status_panel PASS")
