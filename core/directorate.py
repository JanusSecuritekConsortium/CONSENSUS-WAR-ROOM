"""Small, presentation-independent record of observed operational events.

Producers may run on worker threads. Readers receive immutable snapshots; no
provider context, prompts, raw responses or exception bodies enter this stream.
"""
from __future__ import annotations

import json
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from core.paths import ARBITER_DIR

STATES = {"PENDING", "RUNNING", "AVAILABLE", "DEGRADED", "FAILED"}
STARTUP_COMPONENTS = ("CONFIG", "INTERFACE", "PROVIDER", "MEMORY", "AURELIUS")
ACTIVITY_LIMIT = 80
DISPATCH_LIMIT = 20
PREFERENCES_PATH = ARBITER_DIR / "directorate_preferences.json"


def provider_observation(payload: dict, simulated: bool = False) -> tuple[str, str]:
    if simulated:
        return "DEGRADED", "SIMULATION ONLY; no real provider connection"
    provider = payload.get("provider", payload)
    if not isinstance(provider, dict):
        return "FAILED", "Provider returned an invalid health response; retry available"
    status = str(provider.get("status", "unknown")).lower()
    if status == "ready":
        return "AVAILABLE", "Health and model inventory available; generation not yet tested"
    if status in {"offline", "unavailable", "fail", "failed", "error"} or provider.get("error") or payload.get("error"):
        return "FAILED", "Provider unavailable; check local service and retry"
    return "DEGRADED", "Provider inventory incomplete; configured real-model fallback may apply"


@dataclass(frozen=True)
class OperationalEvent:
    timestamp: str
    component: str
    kind: str
    status: str
    summary: str
    session_id: str = ""


@dataclass(frozen=True)
class DecisionDispatch:
    number: int
    timestamp: str
    session_id: str
    subject: str
    verdict: str
    report: str
    received_at: float


# Routine turns and health checks belong to Live Deliberation / Diagnostics.
NOTICE_KINDS = frozenset({
    "MODEL_SUBSTITUTED", "ASSESSMENT_FAILED", "PROCESSING_FAILED",
    "SESSION_SAVE_FAILED", "REPORT_ARCHIVED", "REPORT_EXPORT_FAILED",
    "DECISION_SAVE_FAILED",
})


class Directorate:
    def __init__(self, limit: int = ACTIVITY_LIMIT) -> None:
        self._lock = threading.RLock()
        self._events: deque[OperationalEvent] = deque(maxlen=max(1, limit))
        self._checks: dict[str, OperationalEvent] = {}
        self._notices: deque[OperationalEvent] = deque(maxlen=ACTIVITY_LIMIT)
        self._dispatches: deque[DecisionDispatch] = deque(maxlen=DISPATCH_LIMIT)
        self._dispatch_number = 0

    def record_decision(self, result, sources=None) -> DecisionDispatch:
        """Freeze a public report, independently of mutable live result state."""
        from core.export.cable import render_cable
        from core.public_text import public_text
        report = render_cable(result, sources)
        with self._lock:
            existing = next((d for d in self._dispatches if d.session_id == result.session_id), None)
            if existing is not None:
                return existing
            self._dispatch_number += 1
            dispatch = DecisionDispatch(self._dispatch_number, result.timestamp,
                result.session_id, " ".join(public_text(result.query).split())[:160],
                result.verdict.value, report, time.monotonic())
            self._dispatches.append(dispatch)
            return dispatch

    def dispatches(self) -> tuple[DecisionDispatch, ...]:
        with self._lock:
            return tuple(self._dispatches)

    def notices(self) -> tuple[OperationalEvent, ...]:
        with self._lock:
            return tuple(self._notices)

    def emit(self, component: str, kind: str, status: str, summary: str,
             session_id: str = "", *, check: bool = False) -> OperationalEvent:
        if status not in STATES:
            raise ValueError("Unknown operational state")
        event = OperationalEvent(
            datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            component, kind, status, " ".join(summary.split())[:240], session_id,
        )
        with self._lock:
            self._events.append(event)
            if kind in NOTICE_KINDS:
                self._notices.append(event)
            if check:
                self._checks[component] = event
        return event

    def events(self) -> tuple[OperationalEvent, ...]:
        with self._lock:
            return tuple(self._events)

    def checks(self) -> tuple[OperationalEvent, ...]:
        with self._lock:
            return tuple(self._checks.values())

    def startup_status(self) -> str:
        checks = {event.component: event.status for event in self.checks()}
        required = STARTUP_COMPONENTS
        if any(checks.get(key) == "FAILED" for key in ("CONFIG", "INTERFACE")):
            return "FAILED"
        if any(checks.get(key, "PENDING") in {"PENDING", "RUNNING"} for key in required):
            return "CHECKING"
        if any(checks[key] != "AVAILABLE" for key in required):
            return "DEGRADED"
        return "READY"


def read_preferences(path: Path = PREFERENCES_PATH) -> dict[str, bool]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {key: value for key, value in data.items()
                if key in {"reduced_motion", "animation", "collapsed", "cable", "watch_deliberation"}
                and isinstance(value, bool)}
    except (OSError, ValueError, AttributeError):
        return {}


def write_preferences(values: dict[str, bool], path: Path = PREFERENCES_PATH) -> None:
    from core.memory.session import _atomic_write
    _atomic_write(path, values)
