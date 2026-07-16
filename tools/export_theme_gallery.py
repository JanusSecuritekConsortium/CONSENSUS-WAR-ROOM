from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft
from PIL import Image, ImageDraw, ImageGrab

from config.names import ARBITER, TRIBUNAL_AGENT_IDS
from config.nodes import DEFAULT_NODES, apply_node_overrides
from config.runtime import RuntimeConfig, load_runtime_config
from config.version import SYSTEM_VERSION
from core.paths import CONFIG_PATH
from ui.components.header import header_logo_layout, logo_runtime_diagnostics, theme_logo_layout_mode
from ui.flet_app import GuiState, _render_page, ambient_message, append_timeline, create_gui_state, refresh_telemetry_for_gui
from ui.themes.catalog import THEMES, get_gui_theme_options


WINDOW_TITLE = "CONSENSUS War Room"
THEME_GALLERY_DIR = ROOT / "reports" / "theme_gallery"
CURRENT_THEME_GALLERY_DIR = THEME_GALLERY_DIR / "current"
LOGO_AUDIT_DIR = ROOT / "reports" / "logo_audit"
CURRENT_LOGO_AUDIT_DIR = LOGO_AUDIT_DIR / "current"
LOGO_VISUAL_AUDIT_PATH = CURRENT_LOGO_AUDIT_DIR / "logo_visual_audit.json"
ARASAKA_BEFORE_AUDIT_TEXT = """   .sdmNNNs-     mNNNNNNNNNNm/    /ymNNNm+          mM+NNNmy:-.
 .yMMMhsohNNs.   NMMhssssssdMMd  .dMMyssdMMmo     ///yyMMyyyy-
 oMMd     +mMMo  MMo:       hhss  dMMs    /MNN-    .ymmMM
 .MMMy     dMMo  dMMdmo-          NMM+    /MMM:      /ymMMmy:
  -mMMm+--`dMMo  dNMmNMMdo-        +NNNy/--`MMM/        +yNMMMm
   . smMMMNsdMMo    `odNMMdo-        :hmMMMM/MMM:   MMMMMMMMMM
"""
LOGO_AUDIT_THRESHOLDS = {
    "eva": {"min_width_fill": 0.80, "min_height_fill": 0.70, "min_fill_ratio": 0.015},
    "nerv": {"min_width_fill": 0.80, "min_height_fill": 0.70, "min_fill_ratio": 0.015},
    "wh40k": {"min_width_fill": 0.70, "min_height_fill": 0.70, "min_fill_ratio": 0.015},
    "helldivers": {"min_width_fill": 0.55, "min_height_fill": 0.45, "min_fill_ratio": 0.008},
    "arasaka": {"min_width_fill": 0.45, "min_height_fill": 0.20, "min_fill_ratio": 0.004},
    "janus": {"min_width_fill": 0.35, "min_height_fill": 0.16, "min_fill_ratio": 0.004},
    "military": {"min_width_fill": 0.55, "min_height_fill": 0.20, "min_fill_ratio": 0.004},
}


@dataclass(frozen=True)
class LogoVisualAudit:
    theme_key: str
    screenshot_path: str
    logo_crop_path: str
    renderer_mode: str
    crop_box: tuple[int, int, int, int]
    crop_width: int
    crop_height: int
    artwork_bounds: tuple[int, int, int, int] | None
    artwork_width: int
    artwork_height: int
    width_fill_ratio: float
    height_fill_ratio: float
    pixel_fill_ratio: float
    clearances: tuple[int, int, int, int]
    runtime_diagnostics: dict[str, object]
    passed: bool
    failures: list[str]


def create_gallery_gui_state(theme_key: str, config: RuntimeConfig, nodes) -> GuiState:
    state = GuiState(theme_key=theme_key, config=config, nodes=nodes, window_mode="maximized")
    required_models = {agent_id: nodes[agent_id].model for agent_id in TRIBUNAL_AGENT_IDS if agent_id in nodes}
    state.provider_status = {
        "status": "ready",
        "fallback_enabled": False,
        "strict_provider_mode": False,
        "provider": {
            "status": "ready",
            "backend": "mock",
            "active_backend": "mock",
            "requested_backend": "mock",
            "base_url": None,
            "latency_ms": 0,
            "models": ["mock"],
            "model_count": 1,
            "missing_required_models": {},
            "required_models": required_models,
            "resolved_required_models": required_models,
            "model_status": {agent_id: "mock" for agent_id in required_models},
            "model_availability_report": [
                {"agent_id": agent_id, "required_model": model, "resolved_model": "mock", "status": "mock"}
                for agent_id, model in required_models.items()
            ],
            "mock_fallback_enabled": True,
            "strict_provider_mode": False,
        },
    }
    state.memory_status = "VISUAL AUDIT"
    state.session_memory_status = "ACTIVE"
    state.context_retrieval_status = "NONE"
    state.provider_warning = ""
    state.monolith_statuses = {**{agent_id: "ONLINE" for agent_id in TRIBUNAL_AGENT_IDS}, ARBITER: "ONLINE"}
    refresh_telemetry_for_gui(state)
    state.heartbeat_text = ambient_message(state.theme_key, state.pulse_index)
    state.timeline_events = [append_timeline([], "SYSTEM", f"{state.theme.display_name} interface online")[0]]
    return state


def serve_theme(theme_key: str, marker: Path | None = None, *, live_backend: bool = False) -> None:
    if live_backend:
        config = load_runtime_config(CONFIG_PATH)
        config.theme = theme_key
    else:
        config = RuntimeConfig(theme=theme_key, startup_theme=theme_key, backend="mock")
    nodes = apply_node_overrides(DEFAULT_NODES, config.node_overrides)
    state = create_gui_state(theme_key, config, nodes) if live_backend else create_gallery_gui_state(theme_key, config, nodes)

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


def _color_distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> int:
    return abs(left[0] - right[0]) + abs(left[1] - right[1]) + abs(left[2] - right[2])


def _matches_color(pixel: tuple[int, int, int], expected: tuple[int, int, int], tolerance: int = 120) -> bool:
    return _color_distance(pixel, expected) <= tolerance


def _looks_theme_rendered(image: Image.Image, theme_key: str) -> bool:
    theme = THEMES[theme_key]
    expected_colors = (
        _hex_to_rgb(theme.primary_color),
        _hex_to_rgb(theme.secondary_color),
        _hex_to_rgb(theme.accent_color),
    )
    width, height = image.size
    crop = image.crop((0, 0, width, min(height, 230))).convert("RGB").resize((240, 120))
    matching_pixels = 0
    for red, green, blue in crop.getdata():
        pixel = (red, green, blue)
        if any(_matches_color(pixel, expected, tolerance=120) for expected in expected_colors):
            matching_pixels += 1
    return matching_pixels > 80


def _header_top_y(image: Image.Image, theme_key: str) -> int:
    rgb = image.convert("RGB")
    width, height = rgb.size
    theme = THEMES[theme_key]
    colors = (
        _hex_to_rgb(theme.primary_color),
        _hex_to_rgb(theme.secondary_color),
        _hex_to_rgb(theme.accent_color),
    )
    for y in range(min(30, height), min(height, 110)):
        matches = 0
        for x in range(0, width, max(1, width // 240)):
            pixel = rgb.getpixel((x, y))
            if any(_matches_color(pixel, color, tolerance=90) for color in colors):
                matches += 1
        if matches >= 60:
            return y
    return 0


def _header_left_x(image: Image.Image, theme_key: str, header_top: int) -> int:
    rgb = image.convert("RGB")
    width, height = rgb.size
    theme = THEMES[theme_key]
    colors = (_hex_to_rgb(theme.primary_color), _hex_to_rgb(theme.secondary_color))
    y = min(max(0, header_top), height - 1)
    for x in range(0, min(width, 80)):
        pixel = rgb.getpixel((x, y))
        if any(_matches_color(pixel, color, tolerance=90) for color in colors):
            return x
    return 0


def logo_crop_box_for_image(image: Image.Image, theme_key: str) -> tuple[int, int, int, int]:
    layout = header_logo_layout(THEMES[theme_key])
    width, height = image.size
    logo_width = int(layout.logo_box_width or 162)
    logo_height = int(layout.logo_box_height or 162)
    header_top = _header_top_y(image, theme_key)
    header_left = _header_left_x(image, theme_key, header_top)
    left = min(max(0, header_left + 8), max(0, width - 1))
    top = min(max(0, header_top + 8), max(0, height - 1))
    right = min(width, left + logo_width)
    bottom = min(height, top + logo_height)
    if right <= left or bottom <= top:
        return (0, 0, min(width, logo_width), min(height, logo_height))
    return (left, top, right, bottom)


def _artwork_bounds(crop: Image.Image, theme_key: str) -> tuple[tuple[int, int, int, int] | None, int]:
    rgb = crop.convert("RGB")
    width, height = rgb.size
    primary = _hex_to_rgb(THEMES[theme_key].primary_color)
    accent = _hex_to_rgb(THEMES[theme_key].accent_color)
    xs: list[int] = []
    ys: list[int] = []
    for y in range(2, max(2, height - 2)):
        for x in range(2, max(2, width - 2)):
            pixel = rgb.getpixel((x, y))
            if _matches_color(pixel, primary, tolerance=120) or _matches_color(pixel, accent, tolerance=95):
                xs.append(x)
                ys.append(y)
    if not xs or not ys:
        return None, 0
    return (min(xs), min(ys), max(xs) + 1, max(ys) + 1), len(xs)


def audit_logo_capture(image: Image.Image, theme_key: str, screenshot_path: Path, crop_path: Path) -> LogoVisualAudit:
    crop_box = logo_crop_box_for_image(image, theme_key)
    crop = image.crop(crop_box)
    crop_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(crop_path)
    bounds, matching_pixels = _artwork_bounds(crop, theme_key)
    crop_width, crop_height = crop.size
    if bounds is None:
        artwork_width = 0
        artwork_height = 0
        clearances = (crop_width, crop_width, crop_height, crop_height)
    else:
        left, top, right, bottom = bounds
        artwork_width = right - left
        artwork_height = bottom - top
        clearances = (left, crop_width - right, top, crop_height - bottom)
    width_fill = round(artwork_width / max(1, crop_width), 4)
    height_fill = round(artwork_height / max(1, crop_height), 4)
    pixel_fill = round(matching_pixels / max(1, crop_width * crop_height), 5)
    thresholds = LOGO_AUDIT_THRESHOLDS.get(theme_key, {"min_width_fill": 0.35, "min_height_fill": 0.16, "min_fill_ratio": 0.004})
    failures: list[str] = []
    if width_fill < float(thresholds["min_width_fill"]):
        failures.append(f"width_fill_ratio {width_fill} below {thresholds['min_width_fill']}")
    if height_fill < float(thresholds["min_height_fill"]):
        failures.append(f"height_fill_ratio {height_fill} below {thresholds['min_height_fill']}")
    if pixel_fill < float(thresholds["min_fill_ratio"]):
        failures.append(f"pixel_fill_ratio {pixel_fill} below {thresholds['min_fill_ratio']}")
    if min(clearances) < 0:
        failures.append(f"negative clearance {clearances}")
    return LogoVisualAudit(
        theme_key=theme_key,
        screenshot_path=str(screenshot_path.relative_to(ROOT)) if screenshot_path.is_relative_to(ROOT) else str(screenshot_path),
        logo_crop_path=str(crop_path.relative_to(ROOT)) if crop_path.is_relative_to(ROOT) else str(crop_path),
        renderer_mode=str(theme_logo_layout_mode(THEMES[theme_key])["mode"]),
        crop_box=crop_box,
        crop_width=crop_width,
        crop_height=crop_height,
        artwork_bounds=bounds,
        artwork_width=artwork_width,
        artwork_height=artwork_height,
        width_fill_ratio=width_fill,
        height_fill_ratio=height_fill,
        pixel_fill_ratio=pixel_fill,
        clearances=clearances,
        runtime_diagnostics=logo_runtime_diagnostics(theme_key, header_width=image.size[0]),
        passed=not failures,
        failures=failures,
    )


def write_logo_visual_audit(audits: list[LogoVisualAudit]) -> Path:
    LOGO_VISUAL_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "system_version": SYSTEM_VERSION,
        "status": "PASS" if all(audit.passed for audit in audits) else "FAIL",
        "themes": [asdict(audit) for audit in audits],
    }
    LOGO_VISUAL_AUDIT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return LOGO_VISUAL_AUDIT_PATH


def capture_theme(theme_key: str, timeout: float = 30.0, *, live_backend: bool = False) -> Image.Image:
    marker = Path(tempfile.gettempdir()) / f"consensus_theme_gallery_{theme_key}_{time.time_ns()}.ready"
    before = _flet_process_ids()
    command = [sys.executable, str(Path(__file__).resolve()), "--serve-theme", theme_key, "--marker", str(marker)]
    if live_backend:
        command.append("--live-backend")
    process = subprocess.Popen(
        command,
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
        raise TimeoutError(f"Theme gallery process did not render theme {theme_key!r} within {timeout} seconds")
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


def export_theme_gallery(timeout: float = 90.0, *, live_backend: bool = False) -> list[Path]:
    THEME_GALLERY_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_THEME_GALLERY_DIR.mkdir(parents=True, exist_ok=True)
    LOGO_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_LOGO_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = [_write_arasaka_before()]
    audits: list[LogoVisualAudit] = []
    for theme in get_gui_theme_options():
        image = capture_theme(theme.key, timeout=timeout, live_backend=live_backend)
        gallery_path = THEME_GALLERY_DIR / f"{theme.key}_v{SYSTEM_VERSION}.png"
        current_gallery_path = CURRENT_THEME_GALLERY_DIR / f"{theme.key}.png"
        audit_path = LOGO_AUDIT_DIR / f"{theme.key}_logo_v{SYSTEM_VERSION}.png"
        current_crop_path = CURRENT_LOGO_AUDIT_DIR / f"{theme.key}_logo_crop.png"
        image.save(gallery_path)
        image.save(current_gallery_path)
        image.save(audit_path)
        audits.append(audit_logo_capture(image, theme.key, current_gallery_path, current_crop_path))
        outputs.extend([gallery_path, current_gallery_path, audit_path, current_crop_path])
        if theme.key == "arasaka":
            after_path = LOGO_AUDIT_DIR / f"arasaka_after_v{SYSTEM_VERSION}.png"
            image.save(after_path)
            outputs.append(after_path)
    outputs.append(write_logo_visual_audit(audits))
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Export CONSENSUS theme and logo audit screenshots.")
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--serve-theme", choices=[theme.key for theme in get_gui_theme_options()], default=None, help=argparse.SUPPRESS)
    parser.add_argument("--marker", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument(
        "--live-backend",
        action="store_true",
        help="Use the configured live provider while exporting screenshots. The default uses mock backend for deterministic visual captures.",
    )
    args = parser.parse_args()
    if args.serve_theme:
        serve_theme(args.serve_theme, args.marker, live_backend=args.live_backend)
        return 0
    outputs = export_theme_gallery(timeout=args.timeout, live_backend=args.live_backend)
    for path in outputs:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
