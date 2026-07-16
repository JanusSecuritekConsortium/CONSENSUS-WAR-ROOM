from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.version import SYSTEM_VERSION
from tools import export_theme_gallery


def test_theme_gallery_exports_expected_logo_audit_paths() -> None:
    original_capture = export_theme_gallery.capture_theme
    original_gallery_dir = export_theme_gallery.THEME_GALLERY_DIR
    original_current_gallery_dir = export_theme_gallery.CURRENT_THEME_GALLERY_DIR
    original_audit_dir = export_theme_gallery.LOGO_AUDIT_DIR
    original_current_audit_dir = export_theme_gallery.CURRENT_LOGO_AUDIT_DIR
    original_visual_audit_path = export_theme_gallery.LOGO_VISUAL_AUDIT_PATH
    original_themes = export_theme_gallery.get_gui_theme_options
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            export_theme_gallery.THEME_GALLERY_DIR = root / "theme_gallery"
            export_theme_gallery.CURRENT_THEME_GALLERY_DIR = root / "theme_gallery" / "current"
            export_theme_gallery.LOGO_AUDIT_DIR = root / "logo_audit"
            export_theme_gallery.CURRENT_LOGO_AUDIT_DIR = root / "logo_audit" / "current"
            export_theme_gallery.LOGO_VISUAL_AUDIT_PATH = root / "logo_audit" / "current" / "logo_visual_audit.json"
            capture_calls: list[tuple[str, float, bool]] = []

            def fake_capture_theme(theme_key: str, timeout: float = 30.0, *, live_backend: bool = False) -> Image.Image:
                capture_calls.append((theme_key, timeout, live_backend))
                return Image.new("RGB", (320, 180), "#111111")

            export_theme_gallery.capture_theme = fake_capture_theme
            export_theme_gallery.get_gui_theme_options = lambda: [
                type("ThemeRef", (), {"key": "eva"})(),
                type("ThemeRef", (), {"key": "arasaka"})(),
            ]

            outputs = export_theme_gallery.export_theme_gallery(timeout=1.0)
            output_names = {path.name for path in outputs}

            assert f"eva_v{SYSTEM_VERSION}.png" in output_names
            assert "eva.png" in output_names
            assert f"eva_logo_v{SYSTEM_VERSION}.png" in output_names
            assert "eva_logo_crop.png" in output_names
            assert f"arasaka_logo_v{SYSTEM_VERSION}.png" in output_names
            assert "arasaka_logo_crop.png" in output_names
            assert f"arasaka_before_v{SYSTEM_VERSION}.png" in output_names
            assert f"arasaka_after_v{SYSTEM_VERSION}.png" in output_names
            assert "logo_visual_audit.json" in output_names
            assert capture_calls == [("eva", 1.0, False), ("arasaka", 1.0, False)]
            for path in outputs:
                assert path.exists()
            audit = json.loads((export_theme_gallery.LOGO_VISUAL_AUDIT_PATH).read_text(encoding="utf-8"))
            assert audit["system_version"] == SYSTEM_VERSION
            assert {item["theme_key"] for item in audit["themes"]} == {"eva", "arasaka"}
    finally:
        export_theme_gallery.capture_theme = original_capture
        export_theme_gallery.THEME_GALLERY_DIR = original_gallery_dir
        export_theme_gallery.CURRENT_THEME_GALLERY_DIR = original_current_gallery_dir
        export_theme_gallery.LOGO_AUDIT_DIR = original_audit_dir
        export_theme_gallery.CURRENT_LOGO_AUDIT_DIR = original_current_audit_dir
        export_theme_gallery.LOGO_VISUAL_AUDIT_PATH = original_visual_audit_path
        export_theme_gallery.get_gui_theme_options = original_themes


def test_logo_visual_audit_detects_filled_header_logo_region() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        image = Image.new("RGB", (360, 240), "#100302")
        draw = ImageDraw.Draw(image)
        draw.line((8, 40, 350, 40), fill="#ff8a00", width=1)
        draw.rectangle((22, 60, 190, 196), fill="#ff8a00")

        audit = export_theme_gallery.audit_logo_capture(
            image,
            "eva",
            root / "eva.png",
            root / "eva_logo_crop.png",
        )

        assert audit.renderer_mode == "supersampled_rect"
        assert audit.crop_width == 185
        assert audit.crop_height == 168
        assert audit.width_fill_ratio >= 0.85
        assert audit.height_fill_ratio >= 0.70
        assert audit.pixel_fill_ratio >= 0.015
        assert audit.passed is True
        assert (root / "eva_logo_crop.png").exists()


if __name__ == "__main__":
    test_theme_gallery_exports_expected_logo_audit_paths()
    test_logo_visual_audit_detects_filled_header_logo_region()
    print("test_theme_gallery_logos PASS")
