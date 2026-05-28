from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.reasoning_stream import convergence_bar_text


def test_convergence_bar_is_text_only_and_bounded() -> None:
    assert convergence_bar_text(0.0, width=6) == "[......] 0%"
    assert convergence_bar_text(1.0, width=6) == "[######] 100%"
    assert convergence_bar_text(2.0, width=6) == "[######] 100%"


if __name__ == "__main__":
    test_convergence_bar_is_text_only_and_bounded()
    print("test_convergence_visualization PASS")
