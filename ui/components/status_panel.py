from __future__ import annotations

from typing import Dict

import flet as ft

from config.version import SYSTEM_VERSION
from core.models import Theme
from ui.components.safe_text import safe_ellipsis, safe_wrap


def build_status_panel(
    theme: Theme,
    provider: Dict[str, object],
    memory_status: str,
    lifecycle_state: str = "IDLE",
    provider_warning: str = "",
    ambient_status: str = "MONOLITH LINK STABLE",
    session_memory_status: str = "ACTIVE",
    context_retrieval_status: str = "NONE",
    prior_decisions_used: int = 0,
    current_session_id: str = "--",
) -> ft.Control:
    provider_payload = provider.get("provider", provider)
    if not isinstance(provider_payload, dict):
        provider_payload = {}
    provider_status = str(provider_payload.get("status", provider.get("status", "unknown"))).upper()
    provider_color = theme.primary_color if provider_status == "READY" else theme.warning_color
    label_color = theme.panel_label or theme.secondary_text or theme.secondary_color
    value_color = theme.panel_value or theme.text_color
    muted_color = theme.muted_text or theme.secondary_text or theme.secondary_color
    endpoint = str(provider_payload.get("base_url") or "--")
    active_backend = str(provider_payload.get("active_backend") or provider_payload.get("backend") or provider.get("backend") or "--")
    latency = provider_payload.get("latency_ms")
    latency_text = "--" if latency is None else f"{latency} ms"
    model_count = provider_payload.get("model_count", len(provider_payload.get("models", []) or []))
    missing_models = provider_payload.get("missing_required_models", {}) or {}
    missing_text = ", ".join(f"{agent}:{model}" for agent, model in missing_models.items()) or "--"
    fallback_enabled = bool(provider.get("fallback_enabled", provider_payload.get("mock_fallback_enabled", False)))
    strict_mode = bool(provider.get("strict_provider_mode", provider_payload.get("strict_provider_mode", False)))
    fallback_text = "STRICT" if strict_mode else ("ACTIVE" if fallback_enabled and provider_status != "READY" else "INACTIVE")
    remap_model = provider_payload.get("model_remap_model")
    availability_report = provider_payload.get("model_availability_report", []) or []
    resolved_required = provider_payload.get("resolved_required_models", {}) or {}
    required_models = provider_payload.get("required_models", {}) or {}
    active_model_rows = []
    if isinstance(availability_report, list) and availability_report:
        for item in availability_report[:4]:
            if not isinstance(item, dict):
                continue
            agent_id = str(item.get("agent_id", "--"))
            model_name = str(item.get("resolved_model") or item.get("required_model") or "--")
            status = str(item.get("status", "unknown")).upper()
            active_model_rows.append((agent_id, f"{model_name} [{status}]"))
    elif isinstance(resolved_required, dict) and resolved_required:
        active_model_rows = [(str(agent_id), str(model_name)) for agent_id, model_name in resolved_required.items()]
    elif isinstance(required_models, dict) and required_models:
        active_model_rows = [(str(agent_id), f"{model_name} [UNRESOLVED]") for agent_id, model_name in required_models.items()]
    warning_controls = []
    if provider_warning:
        warning_controls.append(ft.Text(provider_warning, color=theme.warning_color, weight=ft.FontWeight.BOLD, size=12))
    if provider_payload.get("model_remap_active") and remap_model:
        warning_controls.append(
            ft.Text(f"MODEL REMAP ACTIVE: {remap_model}", color=theme.warning_color, weight=ft.FontWeight.BOLD, size=12)
        )

    def section(title: str) -> ft.Control:
        return ft.Text(title, color=theme.accent_color, weight=ft.FontWeight.BOLD, size=11)

    def row(label: str, value: str, color: str | None = None, bold: bool = False, wrap_value: bool = False) -> ft.Control:
        display = f"{label}: {value}"
        if wrap_value:
            return ft.Text(
                "\n".join(safe_wrap(display, width=42, max_lines=2)),
                color=color or value_color,
                size=10,
                weight=ft.FontWeight.BOLD if bold else None,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
                font_family=theme.font_family,
            )
        return ft.Text(
            safe_ellipsis(display, 54),
            color=color or value_color,
            size=10,
            weight=ft.FontWeight.BOLD if bold else None,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            font_family=theme.font_family,
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("SYSTEM STATUS", color=theme.primary_color, weight=ft.FontWeight.BOLD),
                        ft.Text("* POLLING", color=theme.accent_color, font_family=theme.font_family, size=11),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                section("PROVIDER"),
                row("STATUS", provider_status, provider_color, bold=True),
                row("BACKEND", active_backend),
                row("ENDPOINT", endpoint),
                row("LATENCY", latency_text),
                row("MODELS", str(model_count)),
                row("MISSING", missing_text, theme.warning_color if missing_models else muted_color),
                row("FALLBACK", fallback_text, theme.warning_color if fallback_text == "ACTIVE" else value_color),
                *warning_controls,
                section("ACTIVE MODELS"),
                *[row(agent_id, model_name, theme.warning_color if "[MISSING]" in model_name else value_color) for agent_id, model_name in active_model_rows],
                section("CODEX / DEV"),
                row("VERSION", SYSTEM_VERSION),
                row("ACTIVE COMPILE", "TEST REGISTERED"),
                row("RUNTIME LOGS", "JSONL"),
                section("MEMORY"),
                row("SYSTEM", memory_status),
                row("SESSION MEMORY", session_memory_status),
                section("CONTEXT"),
                row("CONTEXT RETRIEVAL", context_retrieval_status),
                row("PRIOR DECISIONS USED", str(prior_decisions_used)),
                row("CURRENT SESSION", current_session_id),
                row("KNOWLEDGE", "METADATA INDEX READY"),
                section("LIFECYCLE"),
                row("STATE", lifecycle_state, theme.accent_color, bold=True),
                row("ACTIVITY", ambient_status, muted_color, wrap_value=True),
            ],
            spacing=6,
        ),
        padding=8,
        border=ft.border.all(1, label_color),
        bgcolor=theme.surface_color,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        data={"role": "right_system_status_panel", "bounded_text": True},
    )
