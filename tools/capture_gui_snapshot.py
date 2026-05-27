from __future__ import annotations

import argparse
import ctypes
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft
from PIL import Image, ImageDraw, ImageGrab

from config.nodes import DEFAULT_NODES, apply_node_overrides
from config.runtime import RuntimeConfig, load_runtime_config
from config.version import SYSTEM_VERSION
from core.paths import CONFIG_PATH
from ui.flet_app import _render_page, create_gui_state
from ui.visual_checks import assert_visual_invariants


WINDOW_TITLE = "CONSENSUS War Room"


def serve_desktop(marker: Optional[Path], diagnostics: bool = False, hidden: bool = False) -> None:
    config = load_runtime_config(CONFIG_PATH)
    nodes = apply_node_overrides(DEFAULT_NODES, config.node_overrides)
    state = create_gui_state(config.theme, config, nodes)
    state.diagnostics_drawer_open = diagnostics

    def target(page: ft.Page) -> None:
        _render_page(page, state)
        if marker is not None:
            marker.write_text("ready", encoding="utf-8")

    ft.app(target=target, view=ft.AppView.FLET_APP_HIDDEN if hidden else ft.AppView.FLET_APP)


def _flet_process_ids() -> set[int]:
    try:
        import subprocess as _subprocess

        completed = _subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process flet -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id",
            ],
            text=True,
            capture_output=True,
            timeout=5,
        )
        return {int(line.strip()) for line in completed.stdout.splitlines() if line.strip().isdigit()}
    except Exception:
        return set()


def _cleanup_spawned_flet_processes(before: set[int]) -> None:
    spawned = _flet_process_ids() - before
    for pid in spawned:
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"],
                capture_output=True,
                timeout=5,
            )
        except Exception:
            pass


def _enum_windows() -> list[tuple[int, str, tuple[int, int, int, int]]]:
    user32 = ctypes.windll.user32
    windows: list[tuple[int, str, tuple[int, int, int, int]]] = []

    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        title = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title, length + 1)
        rect = RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        windows.append((int(hwnd), title.value, (rect.left, rect.top, rect.right, rect.bottom)))
        return True

    user32.EnumWindows(callback_type(callback), 0)
    return windows


def _find_window(timeout: float) -> tuple[int, Tuple[int, int, int, int]]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for _hwnd, title, rect in _enum_windows():
            if WINDOW_TITLE in title and rect[2] - rect[0] > 200 and rect[3] - rect[1] > 200:
                return _hwnd, rect
        time.sleep(0.2)
    raise TimeoutError(f"Could not find visible Flet window titled {WINDOW_TITLE!r}")


def _capture_window(hwnd: int, rect: Tuple[int, int, int, int]) -> Image.Image:
    try:
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(0.4)
    return ImageGrab.grab(bbox=rect)


def _looks_rendered(image: Image.Image) -> bool:
    sample = image.convert("RGB").resize((80, 50))
    colors = sample.getcolors(maxcolors=4000) or []
    if len(colors) < 12:
        return False
    green_or_orange = 0
    for count, (red, green, blue) in colors:
        if green > 140 and red < 140:
            green_or_orange += count
        if red > 180 and green > 70 and blue < 80:
            green_or_orange += count
    return green_or_orange > 4


def _launch_and_capture(output: Path, diagnostics: bool, timeout: float) -> None:
    marker = Path(tempfile.gettempdir()) / f"consensus_gui_capture_{time.time_ns()}.ready"
    before_flet = _flet_process_ids()
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--serve-desktop",
        "--marker",
        str(marker),
    ]
    if diagnostics:
        command.append("--diagnostics")
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not marker.exists():
            if process.poll() is not None:
                stdout, stderr = process.communicate(timeout=1)
                raise RuntimeError(f"Flet capture process exited early: {stdout} {stderr}")
            time.sleep(0.1)
        if not marker.exists():
            raise TimeoutError(f"Flet capture process did not initialize within {timeout} seconds")
        hwnd, rect = _find_window(timeout=timeout)
        output.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + timeout
        image = _capture_window(hwnd, rect)
        while time.monotonic() < deadline:
            image = _capture_window(hwnd, rect)
            if _looks_rendered(image):
                break
            time.sleep(1.0)
        image.save(output)
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
        _cleanup_spawned_flet_processes(before_flet)


def _write_mock_snapshot(output: Path, diagnostics: bool = False) -> None:
    config = RuntimeConfig(backend="mock", theme="eva")
    state = create_gui_state("eva", config)
    state.diagnostics_drawer_open = diagnostics
    layout = __import__("ui.flet_app", fromlist=["build_gui_layout"]).build_gui_layout(
        state,
        lambda *_args: None,
        lambda *_args: None,
        lambda *_args: None,
        lambda *_args: None,
        lambda *_args: None,
    )
    assert_visual_invariants(layout)
    output.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1280, 760), "#050806")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 1260, 740), outline="#39ff14", width=3)
    draw.text((44, 44), f"MOCK GUI SNAPSHOT v{SYSTEM_VERSION}", fill="#39ff14")
    draw.text((44, 86), "WAR ROOM CONTROL TREE VERIFIED", fill="#d8ffe0")
    draw.text((44, 128), f"DIAGNOSTICS DRAWER: {'OPEN' if diagnostics else 'CLOSED'}", fill="#ffbf00")
    draw.text((44, 170), "This image is marked MOCK and is not a live desktop screenshot.", fill="#ff3b30")
    image.save(output)


def capture_gui_snapshots(output: Path, diagnostics_output: Optional[Path], timeout: float, mock: bool = False) -> None:
    if mock:
        _write_mock_snapshot(output, diagnostics=False)
        if diagnostics_output is not None:
            _write_mock_snapshot(diagnostics_output, diagnostics=True)
        return
    _launch_and_capture(output, diagnostics=False, timeout=timeout)
    if diagnostics_output is not None:
        _launch_and_capture(diagnostics_output, diagnostics=True, timeout=timeout)


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture CONSENSUS War Room GUI screenshots.")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / f"gui_snapshot_v{SYSTEM_VERSION}.png")
    parser.add_argument("--diagnostics-output", type=Path, default=None)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--mock", action="store_true", help="Write clearly marked MOCK control-tree screenshots.")
    parser.add_argument("--serve-desktop", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--diagnostics", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--hidden", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--marker", type=Path, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve_desktop:
        serve_desktop(args.marker, diagnostics=args.diagnostics, hidden=args.hidden)
        return 0
    capture_gui_snapshots(args.output, args.diagnostics_output, args.timeout, mock=args.mock)
    print(f"GUI SNAPSHOT: {args.output}")
    if args.diagnostics_output:
        print(f"GUI DIAGNOSTICS SNAPSHOT: {args.diagnostics_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
