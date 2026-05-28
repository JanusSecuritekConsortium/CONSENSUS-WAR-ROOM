from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from core.models import FinalVerdict, TribunalResult
from ui import flet_app


def test_layout_render_does_not_dispatch_voice() -> None:
    original_dispatch = flet_app.dispatch_arbiter_verdict_voice
    try:
        flet_app.dispatch_arbiter_verdict_voice = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("voice dispatched on render"))
        state = flet_app.create_gui_state("military", RuntimeConfig(theme="military", backend="mock"))
        state.current_result = TribunalResult(
            query="dummy",
            verdict=FinalVerdict.NO_CONSENSUS,
            confidence=0.0,
            reason="No consensus.",
            votes={},
            vote_distribution={},
            quorum_met=False,
            review_triggers=[],
            session_id="voice-render",
            theme="military",
        )
        flet_app.build_gui_layout(
            state,
            lambda _proposal: None,
            lambda _theme: None,
            lambda _event=None: None,
            lambda _event=None: None,
            lambda _event=None: None,
        )
    finally:
        flet_app.dispatch_arbiter_verdict_voice = original_dispatch


if __name__ == "__main__":
    test_layout_render_does_not_dispatch_voice()
    print("test_arbiter_voice_not_on_repaint PASS")
