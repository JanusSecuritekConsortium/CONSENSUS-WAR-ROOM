"""Which models the local model server holds in memory right now, refreshed in the background.

The War Room redraws often; this never blocks a redraw. It asks the llama.cpp router's /models list at most
every REFRESH_SECONDS on a background thread and returns the last answer it got.
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Dict, Iterable

REFRESH_SECONDS = 10.0
LABELS = {"loaded": "IN MEMORY", "loading": "LOADING", "unloaded": "ON DISK", "sleeping": "ON DISK"}

_cache: Dict[str, object] = {"at": None, "states": {}, "busy": False}


def fetch_states(base_url: str) -> Dict[str, str]:
    from core.llm import backends
    response = backends.requests.get(base_url.rstrip("/") + "/models", timeout=3)
    response.raise_for_status()
    return {str(item.get("id")): str((item.get("status") or {}).get("value") or "unknown")
            for item in response.json().get("data", []) if isinstance(item, dict)}


def load_states(base_url: str, *, now: float | None = None,
                fetch: Callable[[str], Dict[str, str]] = fetch_states,
                start: Callable[..., threading.Thread] = threading.Thread) -> Dict[str, str]:
    """Model id -> server status from the last check; starts a new check when the last one is old."""
    now = time.monotonic() if now is None else now
    last = _cache["at"]
    if not _cache["busy"] and (last is None or now - float(last) >= REFRESH_SECONDS):
        _cache["busy"], _cache["at"] = True, now

        def refresh() -> None:
            try:
                _cache["states"] = fetch(base_url)
            except Exception:
                _cache["states"] = {}  # server off or busy: show "--" rather than a stale answer
            finally:
                _cache["busy"] = False

        start(target=refresh, daemon=True).start()
    return dict(_cache["states"])  # type: ignore[arg-type]


def memory_label(model: str, states: Dict[str, str]) -> str:
    """IN MEMORY, LOADING, ON DISK, MISSING, or -- when the server has not answered."""
    if not states or not model:
        return "--"
    from integrations.msty.api import match_model_alias
    match, _ = match_model_alias(model, list(states))
    if match is None:
        return "MISSING"
    return LABELS.get(states[match].lower(), states[match].upper())


def reset(states: Iterable = ()) -> None:
    """For tests: forget the last check."""
    _cache.update(at=None, states=dict(states), busy=False)


__all__ = ["REFRESH_SECONDS", "load_states", "memory_label", "fetch_states", "reset"]
