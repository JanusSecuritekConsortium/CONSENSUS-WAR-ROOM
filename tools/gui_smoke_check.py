from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class SmokePage:
    title = ""
    bgcolor = ""
    theme = None
    scroll = "auto"
    padding = 10
    spacing = 10

    def __init__(self) -> None:
        self.controls = []
        self.overlay = []
        self.updated = 0

    def add(self, control) -> None:
        self.controls.append(control)

    def update(self) -> None:
        self.updated += 1

    def close(self) -> None:
        return None

    def run_thread(self, handler) -> None:
        return None


def run_control_tree_smoke() -> bool:
    from ui.flet_app import _render_page

    state = build_smoke_gui_state()
    page = SmokePage()
    _render_page(page, state)  # type: ignore[arg-type]
    if page.updated != 1 or not page.controls:
        raise RuntimeError("GUI control-tree smoke did not render a page.")
    return True


def _smoke_provider_status() -> dict[str, Any]:
    model_report = [
        {"agent_id": "RATIONALIS", "resolved_model": "smoke-rationalis", "status": "ready"},
        {"agent_id": "AETERNUM", "resolved_model": "smoke-aeternum", "status": "ready"},
        {"agent_id": "BELLATOR", "resolved_model": "smoke-bellator", "status": "ready"},
        {"agent_id": "ARBITER", "resolved_model": "smoke-arbiter", "status": "ready"},
    ]
    provider = {
        "status": "ready",
        "active_backend": "msty-local",
        "backend": "msty-local",
        "base_url": "http://localhost:11454",
        "models": [item["resolved_model"] for item in model_report],
        "model_count": len(model_report),
        "missing_required_models": {},
        "model_availability_report": model_report,
    }
    return {"status": "ready", "provider": provider, "fallback_enabled": False}


def _smoke_telemetry() -> dict[str, Any]:
    return {
        "status": "READY",
        "source": "gui-smoke",
        "latest": {
            "cpu": {"percent": 0.0},
            "ram": {"percent": 0.0},
            "disk": {"percent": 0.0},
            "gpu": {"status": "unavailable", "usage_percent": None, "vram_percent": None, "temperature_c": None},
        },
        "history": {"cpu": [0.0], "ram": [0.0], "gpu": []},
    }


def build_smoke_gui_state():
    from config.nodes import DEFAULT_NODES, apply_node_overrides
    from config.runtime import RuntimeConfig
    from ui.flet_app import GuiState

    config = RuntimeConfig(theme="eva", backend="mock")
    nodes = apply_node_overrides(DEFAULT_NODES, config.node_overrides)
    state = GuiState(
        theme_key="eva",
        config=config,
        nodes=nodes,
        provider_status=_smoke_provider_status(),
        memory_status="AVAILABLE",
        monolith_statuses={agent_id: "ONLINE" for agent_id in nodes},
    )
    state.heartbeat_text = "SMOKE READY"
    state.timeline_events = ["[00:00:00] SYSTEM GUI SMOKE READY"]
    state.telemetry_snapshot = _smoke_telemetry()
    state.runtime_snapshot_cache = {
        "health_badge": {"label": "READY", "color_role": "primary"},
        "integrity_status": {"status": "CLEAN"},
        "visual_review": {"screenshot_status": "MANUAL_REVIEW_REQUIRED", "pending_count": 0},
    }
    return state


def serve_smoke_app(marker: Path | None = None, hidden: bool = False) -> None:
    import flet as ft
    from ui.flet_app import _render_page

    state = build_smoke_gui_state()

    def target(page: ft.Page) -> None:
        _render_page(page, state)
        if marker is not None:
            marker.write_text("ready", encoding="utf-8")
        page.close()

    ft.app(target=target, view=ft.AppView.FLET_APP_HIDDEN if hidden else ft.AppView.FLET_APP)


def run_hidden_gui_smoke(timeout: float = 12.0) -> bool:
    marker = Path(tempfile.gettempdir()) / f"consensus_gui_smoke_{time.time_ns()}.ready"
    command = [
        sys.executable,
        str(ROOT / "tools" / "gui_smoke_check.py"),
        "--serve-smoke",
        "--hidden",
        "--marker",
        str(marker),
    ]
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            if marker.exists():
                return True
            if process.poll() is not None:
                stdout, stderr = process.communicate(timeout=1)
                raise RuntimeError(f"GUI process exited early: {stdout} {stderr}")
            time.sleep(0.1)
        return run_control_tree_smoke()
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        try:
            marker.unlink()
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch the Flet GUI in hidden test mode and verify startup.")
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--control-tree-only", action="store_true", help="Run deterministic Flet control-tree initialization only.")
    parser.add_argument("--serve-smoke", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--hidden", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--marker", type=Path, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve_smoke:
        serve_smoke_app(args.marker, hidden=args.hidden)
        return 0
    if args.control_tree_only:
        run_control_tree_smoke()
        print("GUI SMOKE PASS mode=control-tree")
        return 0
    run_hidden_gui_smoke(args.timeout)
    print("GUI SMOKE PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
