from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_flet_app_imports_without_launching_window() -> None:
    import ui.flet_app as flet_app

    assert callable(flet_app.create_gui_state)
    assert callable(flet_app.submit_proposal_for_gui)
    assert callable(flet_app.run_flet_gui)


if __name__ == "__main__":
    test_flet_app_imports_without_launching_window()
    print("test_flet_app_import PASS")
