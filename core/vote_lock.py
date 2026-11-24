"""One real vote at a time on this PC, whoever starts it.

The voters share one graphics card. Before 9.22.0 the desktop window, the background-vote queue
(phone, MCP, web API) and the command line each checked only their own work, so two votes could
overlap and keep unloading each other's model (Codex review 2026-11-24).

`hold(source)` takes an operating-system file lock for the whole vote, including any wait for the
owner's answers. The system releases it when the process ends, even after a crash, so a dead vote
never blocks the next one. Simulated (mock) votes need no graphics card and take no lock.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterator, Optional


class VoteBusy(RuntimeError):
    """Another real vote holds the voters' graphics card."""


def lock_path() -> Path:
    override = os.environ.get("CONSENSUS_VOTE_LOCK")
    if override:
        return Path(override)
    from core.paths import ARBITER_DIR
    return ARBITER_DIR / "memory" / "vote_in_progress.lock"


def _info_path(path: Path) -> Path:
    return path.with_suffix(".json")


def _try_lock(handle) -> bool:
    try:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _unlock(handle) -> None:
    try:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass


def _describe(info: Optional[Dict[str, Any]]) -> str:
    source = (info or {}).get("source") or "another part of CONSENSUS"
    since = (info or {}).get("since")
    return f"A vote started from {source} is already running" + (f" (since {since} UTC)" if since else "") + \
        "; the voters share one graphics card, so wait until it ends."


def holder() -> Optional[Dict[str, Any]]:
    """Who holds the lock now ({"source", "since", "pid", "detail"}), or None when no real vote runs."""
    path = lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+b") as handle:
        if _try_lock(handle):
            _unlock(handle)
            return None
    try:
        info = json.loads(_info_path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        info = {}
    info = info if isinstance(info, dict) else {}
    return {**info, "detail": _describe(info)}


@contextmanager
def hold(source: str) -> Iterator[None]:
    """Hold the lock for one real vote; raise VoteBusy at once if another vote holds it."""
    path = lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "a+b")
    if not _try_lock(handle):
        handle.close()
        busy = holder() or {"detail": _describe(None)}
        raise VoteBusy(busy["detail"])
    try:
        info = {"source": source, "pid": os.getpid(),
                "since": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")}
        try:
            _info_path(path).write_text(json.dumps(info), encoding="utf-8")
        except OSError:
            pass  # the lock alone still keeps a second vote out
        yield
    finally:
        _unlock(handle)
        handle.close()
