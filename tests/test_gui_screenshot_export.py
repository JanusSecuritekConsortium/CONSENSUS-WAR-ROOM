from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image

from tools.capture_gui_snapshot import capture_gui_snapshots


def test_mock_screenshot_export_writes_marked_pngs(tmp_path: Path) -> None:
    output = tmp_path / "gui_snapshot_mock.png"
    diagnostics_output = tmp_path / "gui_diagnostics_snapshot_mock.png"

    capture_gui_snapshots(output, diagnostics_output, timeout=1, mock=True)

    assert output.exists()
    assert diagnostics_output.exists()
    with Image.open(output) as image:
        assert image.size == (1280, 760)
    with Image.open(diagnostics_output) as image:
        assert image.size == (1280, 760)


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_mock_screenshot_export_writes_marked_pngs(Path(tmp))
    print("test_gui_screenshot_export PASS")
