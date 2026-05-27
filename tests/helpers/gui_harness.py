from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import flet as ft

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.nodes import DEFAULT_NODES, apply_node_overrides
from config.runtime import RuntimeConfig
from ui.components.header import logo_text_control_from_box
from ui.flet_app import GuiState, GuiWindowMode, build_gui_layout
from ui.themes.catalog import resolve_theme_key


def noop(*_args: Any, **_kwargs: Any) -> None:
    return None


def provider_status_ready() -> dict[str, Any]:
    model_report = [
        {"agent_id": "RATIONALIS", "resolved_model": "harness-rationalis", "status": "ready"},
        {"agent_id": "AETERNUM", "resolved_model": "harness-aeternum", "status": "ready"},
        {"agent_id": "BELLATOR", "resolved_model": "harness-bellator", "status": "ready"},
        {"agent_id": "ARBITER", "resolved_model": "harness-arbiter", "status": "ready"},
    ]
    provider = {
        "status": "ready",
        "active_backend": "msty-local",
        "backend": "msty-local",
        "base_url": "http://localhost:11454",
        "latency_ms": 0,
        "models": [item["resolved_model"] for item in model_report],
        "model_count": len(model_report),
        "missing_required_models": {},
        "model_availability_report": model_report,
        "health_endpoint": {"valid": True, "reason": "harness"},
    }
    return {"status": "ready", "provider": provider, "fallback_enabled": False}


def telemetry_snapshot_ready() -> dict[str, Any]:
    return {
        "status": "READY",
        "timestamp": "2026-05-27T00:00:00+00:00",
        "source": "test-harness",
        "latest": {
            "cpu": {"percent": 12.0},
            "ram": {"percent": 34.0},
            "disk": {"percent": 56.0},
            "gpu": {"status": "unavailable", "usage_percent": None, "vram_percent": None, "temperature_c": None},
        },
        "history": {"cpu": [12.0, 13.0], "ram": [34.0], "gpu": []},
    }


def make_gui_state(
    theme_key: str = "eva",
    *,
    window_mode: GuiWindowMode = "maximized",
    compact_header: bool = True,
) -> GuiState:
    resolved = resolve_theme_key(theme_key)
    config = RuntimeConfig(theme=resolved, backend="mock")
    nodes = apply_node_overrides(DEFAULT_NODES, config.node_overrides)
    state = GuiState(
        theme_key=resolved,
        config=config,
        nodes=nodes,
        compact_header=compact_header,
        window_mode=window_mode,
        provider_status=provider_status_ready(),
        memory_status="AVAILABLE",
        monolith_statuses={agent_id: "ONLINE" for agent_id in nodes},
    )
    state.heartbeat_text = "HARNESS READY"
    state.timeline_events = ["[00:00:00] SYSTEM GUI HARNESS READY"]
    state.runtime_snapshot_cache = {
        "health_badge": {"label": "READY", "color_role": "primary"},
        "integrity_status": {"status": "CLEAN"},
        "visual_review": {
            "latest_file": "reports/manual_visual_review_v7.10.12.json",
            "pending_count": 0,
            "needs_fix_count": 0,
            "rejected_count": 0,
            "screenshot_status": "MANUAL_REVIEW_REQUIRED",
        },
    }
    state.telemetry_snapshot = telemetry_snapshot_ready()
    return state


def build_layout_for(theme_key: str = "eva", *, window_mode: GuiWindowMode = "maximized") -> ft.Control:
    return build_gui_layout(make_gui_state(theme_key, window_mode=window_mode), noop, noop, noop, noop, noop)


def header_logo_control_for(theme_key: str) -> ft.Text:
    layout = build_layout_for(theme_key)
    return logo_text_control_from_box(layout.content.controls[0].content.controls[0])


def body_expand_contract(layout: ft.Control) -> list[int | None]:
    body_row = layout.content.controls[1].content
    return [control.expand for control in body_row.controls]


class FakeWindow:
    full_screen = False
    maximized = False
    resizable = False


class FakePage:
    def __init__(self) -> None:
        self.window = FakeWindow()
        self.window_full_screen = False
        self.window_maximized = False
