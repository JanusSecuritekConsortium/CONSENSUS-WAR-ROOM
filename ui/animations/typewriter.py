from __future__ import annotations

import asyncio
import random
from typing import Awaitable, Callable, List


TextUpdate = Callable[[str], None | Awaitable[None]]


async def reveal_text_async(
    text: str,
    on_update: TextUpdate | None = None,
    speed: float = 0.015,
    skip: bool = False,
) -> str:
    if skip or speed <= 0:
        if on_update is not None:
            result = on_update(text)
            if asyncio.iscoroutine(result):
                await result
        return text

    rendered = ""
    for char in text:
        rendered += char
        if on_update is not None:
            result = on_update(rendered)
            if asyncio.iscoroutine(result):
                await result
        await asyncio.sleep(speed)
    return rendered


def typewriter_frames(
    text: str,
    cursor: str = "_",
    lock_text: str = "[CONSENSUS LOCKED]",
    pause_every: int = 14,
) -> List[str]:
    frames: List[str] = []
    rendered = ""
    for index, char in enumerate(text, start=1):
        rendered += char
        frames.append(f"{rendered}{cursor}")
        if pause_every > 0 and index % pause_every == 0:
            frames.append(f"{rendered}{cursor}")
    frames.append(text)
    frames.append(lock_text)
    return frames


async def reveal_text_with_cursor_async(
    text: str,
    on_update: TextUpdate | None = None,
    speed: float = 0.015,
    skip: bool = False,
    cursor: str = "_",
    lock_text: str = "[CONSENSUS LOCKED]",
    seed: int | None = None,
) -> str:
    if skip or speed <= 0:
        if on_update is not None:
            result = on_update(text)
            if asyncio.iscoroutine(result):
                await result
            result = on_update(lock_text)
            if asyncio.iscoroutine(result):
                await result
        return text

    rng = random.Random(seed)
    rendered = ""
    for char in text:
        rendered += char
        if on_update is not None:
            result = on_update(f"{rendered}{cursor}")
            if asyncio.iscoroutine(result):
                await result
        await asyncio.sleep(speed * rng.uniform(0.75, 1.55))
    if on_update is not None:
        result = on_update(text)
        if asyncio.iscoroutine(result):
            await result
        result = on_update(lock_text)
        if asyncio.iscoroutine(result):
            await result
    return text


def reveal_text_sync(
    text: str,
    on_update: Callable[[str], None] | None = None,
    speed: float = 0.015,
    skip: bool = False,
) -> str:
    async def runner() -> str:
        return await reveal_text_async(text, on_update=on_update, speed=speed, skip=skip)

    return asyncio.run(runner())


def reveal_text_with_cursor_sync(
    text: str,
    on_update: Callable[[str], None] | None = None,
    speed: float = 0.015,
    skip: bool = False,
    cursor: str = "_",
    lock_text: str = "[CONSENSUS LOCKED]",
    seed: int | None = None,
) -> str:
    async def runner() -> str:
        return await reveal_text_with_cursor_async(
            text,
            on_update=on_update,
            speed=speed,
            skip=skip,
            cursor=cursor,
            lock_text=lock_text,
            seed=seed,
        )

    return asyncio.run(runner())


__all__ = [
    "reveal_text_async",
    "reveal_text_sync",
    "reveal_text_with_cursor_async",
    "reveal_text_with_cursor_sync",
    "typewriter_frames",
]
