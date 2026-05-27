from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.version import SYSTEM_VERSION
from tools import export_theme_gallery


def test_theme_gallery_exports_expected_logo_audit_paths() -> None:
    original_capture = export_theme_gallery.capture_theme
    original_gallery_dir = export_theme_gallery.THEME_GALLERY_DIR
    original_audit_dir = export_theme_gallery.LOGO_AUDIT_DIR
    original_themes = export_theme_gallery.get_gui_theme_options
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            export_theme_gallery.THEME_GALLERY_DIR = root / "theme_gallery"
            export_theme_gallery.LOGO_AUDIT_DIR = root / "logo_audit"
            export_theme_gallery.capture_theme = lambda _theme, timeout=30.0: Image.new("RGB", (320, 180), "#111111")
            export_theme_gallery.get_gui_theme_options = lambda: [
                type("ThemeRef", (), {"key": "eva"})(),
                type("ThemeRef", (), {"key": "arasaka"})(),
            ]

            outputs = export_theme_gallery.export_theme_gallery(timeout=1.0)
            output_names = {path.name for path in outputs}

            assert f"eva_v{SYSTEM_VERSION}.png" in output_names
            assert f"eva_logo_v{SYSTEM_VERSION}.png" in output_names
            assert f"arasaka_logo_v{SYSTEM_VERSION}.png" in output_names
            assert f"arasaka_before_v{SYSTEM_VERSION}.png" in output_names
            assert f"arasaka_after_v{SYSTEM_VERSION}.png" in output_names
            for path in outputs:
                assert path.exists()
    finally:
        export_theme_gallery.capture_theme = original_capture
        export_theme_gallery.THEME_GALLERY_DIR = original_gallery_dir
        export_theme_gallery.LOGO_AUDIT_DIR = original_audit_dir
        export_theme_gallery.get_gui_theme_options = original_themes


if __name__ == "__main__":
    test_theme_gallery_exports_expected_logo_audit_paths()
    print("test_theme_gallery_logos PASS")
