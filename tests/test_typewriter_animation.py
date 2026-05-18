from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.animations.typewriter import reveal_text_async, reveal_text_sync


def test_typewriter_can_skip_for_tests() -> None:
    updates: list[str] = []
    rendered = reveal_text_sync("ARBITER SYNTHESIS", updates.append, speed=0, skip=True)

    assert rendered == "ARBITER SYNTHESIS"
    assert updates == ["ARBITER SYNTHESIS"]


def test_typewriter_async_no_delay_is_deterministic() -> None:
    updates: list[str] = []

    async def run() -> str:
        return await reveal_text_async("READY", updates.append, speed=0)

    rendered = asyncio.run(run())

    assert rendered == "READY"
    assert updates == ["READY"]


if __name__ == "__main__":
    test_typewriter_can_skip_for_tests()
    test_typewriter_async_no_delay_is_deterministic()
    print("test_typewriter_animation PASS")
