from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.gui_smoke_check import run_hidden_gui_smoke


def test_gui_launch_smoke_initializes_hidden_flet_app() -> None:
    assert run_hidden_gui_smoke(timeout=12.0) is True


if __name__ == "__main__":
    test_gui_launch_smoke_initializes_hidden_flet_app()
    print("test_gui_launch_smoke PASS")
