from __future__ import annotations

import argparse
import ctypes
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft
from PIL import Image, ImageDraw, ImageGrab

from config.nodes import DEFAULT_NODES, apply_node_overrides
from config.runtime import load_runtime_config
from config.version import SYSTEM_VERSION
from core.paths import CONFIG_PATH
from ui.flet_app import _render_page, create_gui_state
from ui.themes.catalog import THEMES, get_gui_theme_options


WINDOW_TITLE = "CONSENSUS War Room"
THEME_GALLERY_DIR = ROOT / "reports" / "theme_gallery"
LOGO_AUDIT_DIR = ROOT / "reports" / "logo_audit"
ARASAKA_BEFORE_AUDIT_TEXT = """   .sdmNNNs-     mNNNNNNNNNNm/    /ymNNNm+          mM+NNNmy:-.
 .yMMMhsohNNs.   NMMhssssssdMMd  .dMMyssdMMmo     ///yyMMyyyy-
 oMMd     +mMMo  MMo:       hhss  dMMs    /MNN-    .ymmMM
 .MMMy     dMMo  dMMdmo-          NMM+    /MMM:      /ymMMmy:
  -mMMm+--`dMMo  dNMmNMMdo-        +NNNy/--`MMM/        +yNMMMm
   . smMMMNsdMMo    `odNMMdo-        :hmMMMM/MMM:   MMMMMMMMMM
"""


def serve_theme(theme_key: str, marker: Path | None = None) -> None:
    config = load_runtime_config(CONFIG_PATH)
    config.theme = theme_key
    nodes = apply_node_overrides(DEFAULT_NODES, config.node_overrides)
    state = create_gui_state(theme_key, config, nodes)

    def target(page: ft.Page) -> None:
        _render_page(page, state)
        page.title = theme_window_title(theme_key)
        page.update()
        if marker is not None:
            marker.write_text("ready", encoding="utf-8")

    ft.app(target=target, view=ft.AppView.FLET_APP)


def theme_window_title(theme_key: str) -> str:
    return f"{WINDOW_TITLE} [{theme_key.upper()}]"


def _flet_process_ids() -> set[int]:
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process flet -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id",
            ],
            text=True,
            capture_output=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return set()
    return {int(line.strip()) for line in completed.stdout.splitlines() if line.strip().isdigit()}


def _cleanup_spawned_flet_processes(before: set[int]) -> None:
    for pid in _flet_process_ids() - before:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"],
            capture_output=True,
            timeout=5,
        )


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


def _find_window(theme_key: str, timeout: float) -> tuple[int, Tuple[int, int, int, int]]:
    expected_title = theme_window_title(theme_key)
    deadline = time.monotonic() + timeout
    best_match: tuple[int, Tuple[int, int, int, int]] | None = None
    while time.monotonic() < deadline:
        for hwnd, title, rect in _enum_windows():
            if expected_title in title and rect[2] - rect[0] > 200 and rect[3] - rect[1] > 200:
                best_match = (hwnd, rect)
                if rect[2] - rect[0] >= 1600 and rect[3] - rect[1] >= 850:
                    return hwnd, rect
        time.sleep(0.2)
    if best_match is not None:
        return best_match
    raise TimeoutError(f"Could not find visible Flet window titled {expected_title!r}")


def _capture_window(hwnd: int, rect: Tuple[int, int, int, int]) -> Image.Image:
    width = max(1, rect[2] - rect[0])
    height = max(1, rect[3] - rect[1])
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    _bring_window_to_front(hwnd)
    try:
        foreground = ImageGrab.grab(bbox=_screen_safe_rect(rect))
        if not _looks_blank_capture(foreground):
            return foreground
    except OSError:
        pass
    window_dc = user32.GetWindowDC(hwnd)
    memory_dc = gdi32.CreateCompatibleDC(window_dc)
    bitmap = gdi32.CreateCompatibleBitmap(window_dc, width, height)
    old_bitmap = gdi32.SelectObject(memory_dc, bitmap)
    try:
        if user32.PrintWindow(hwnd, memory_dc, 2):
            buffer = ctypes.create_string_buffer(width * height * 4)
            if gdi32.GetBitmapBits(bitmap, len(buffer), buffer):
                image = Image.frombuffer("RGB", (width, height), buffer, "raw", "BGRX", 0, 1).copy()
                if not _looks_blank_capture(image):
                    return image
    finally:
        gdi32.SelectObject(memory_dc, old_bitmap)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(hwnd, window_dc)
    return ImageGrab.grab(bbox=_screen_safe_rect(rect))


def _screen_safe_rect(rect: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    return (max(0, rect[0]), max(0, rect[1]), max(1, rect[2]), max(1, rect[3]))


def _bring_window_to_front(hwnd: int) -> None:
    user32 = ctypes.windll.user32
    hwnd_topmost = -1
    hwnd_notopmost = -2
    swp_nosize = 0x0001
    swp_nomove = 0x0002
    swp_showwindow = 0x0040
    try:
        user32.ShowWindow(hwnd, 9)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetWindowPos(hwnd, hwnd_topmost, 0, 0, 0, 0, swp_nomove | swp_nosize | swp_showwindow)
        user32.SetWindowPos(hwnd, hwnd_notopmost, 0, 0, 0, 0, swp_nomove | swp_nosize | swp_showwindow)
    except Exception:
        pass
    time.sleep(0.7)


def _looks_blank_capture(image: Image.Image) -> bool:
    sample = image.convert("RGB").resize((80, 45))
    bright_pixels = 0
    for red, green, blue in sample.getdata():
        if red + green + blue > 45:
            bright_pixels += 1
    return bright_pixels < 20


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    color = value.lstrip("#")
    return tuple(int(color[index : index + 2], 16) for index in (0, 2, 4))


def _looks_theme_rendered(image: Image.Image, theme_key: str) -> bool:
    expected = _hex_to_rgb(THEMES[theme_key].primary_color)
    width, height = image.size
    crop = image.crop((0, 44, width, max(44, height - 44))).convert("RGB").resize((160, 90))
    matching_pixels = 0
    for red, green, blue in crop.getdata():
        if abs(red - expected[0]) + abs(green - expected[1]) + abs(blue - expected[2]) < 120:
            matching_pixels += 1
    return matching_pixels > 30


def capture_theme(theme_key: str, timeout: float = 30.0) -> Image.Image:
    marker = Path(tempfile.gettempdir()) / f"consensus_theme_gallery_{theme_key}_{time.time_ns()}.ready"
    before = _flet_process_ids()
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--serve-theme", theme_key, "--marker", str(marker)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not marker.exists():
            if process.poll() is not None:
                stdout, stderr = process.communicate(timeout=1)
                raise RuntimeError(f"Theme gallery process exited early: {stdout} {stderr}")
            time.sleep(0.1)
        if not marker.exists():
            raise TimeoutError(f"Theme gallery process did not initialize within {timeout} seconds")
        hwnd, rect = _find_window(theme_key, timeout)
        image = _capture_window(hwnd, rect)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            image = _capture_window(hwnd, rect)
            if _looks_theme_rendered(image, theme_key):
                return image
            time.sleep(0.5)
        return image
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
        _cleanup_spawned_flet_processes(before)


def _write_arasaka_before() -> Path:
    LOGO_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    target = LOGO_AUDIT_DIR / f"arasaka_before_v{SYSTEM_VERSION}.png"
    image = Image.new("RGB", (1280, 360), "#050505")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 1260, 340), outline="#ff1f2d", width=3)
    draw.text((44, 44), "ARASAKA PRE-REPAIR AUDIT REFERENCE", fill="#ff1f2d")
    draw.text((44, 88), ARASAKA_BEFORE_AUDIT_TEXT, fill="#f2f2f2")
    image.save(target)
    return target


def export_theme_gallery(timeout: float = 90.0) -> list[Path]:
    THEME_GALLERY_DIR.mkdir(parents=True, exist_ok=True)
    LOGO_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = [_write_arasaka_before()]
    for theme in get_gui_theme_options():
        image = capture_theme(theme.key, timeout=timeout)
        gallery_path = THEME_GALLERY_DIR / f"{theme.key}_v{SYSTEM_VERSION}.png"
        audit_path = LOGO_AUDIT_DIR / f"{theme.key}_logo_v{SYSTEM_VERSION}.png"
        image.save(gallery_path)
        image.save(audit_path)
        outputs.extend([gallery_path, audit_path])
        if theme.key == "arasaka":
            after_path = LOGO_AUDIT_DIR / f"arasaka_after_v{SYSTEM_VERSION}.png"
            image.save(after_path)
            outputs.append(after_path)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Export CONSENSUS theme and logo audit screenshots.")
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--serve-theme", choices=[theme.key for theme in get_gui_theme_options()], default=None, help=argparse.SUPPRESS)
    parser.add_argument("--marker", type=Path, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve_theme:
        serve_theme(args.serve_theme, args.marker)
        return 0
    outputs = export_theme_gallery(timeout=args.timeout)
    for path in outputs:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
