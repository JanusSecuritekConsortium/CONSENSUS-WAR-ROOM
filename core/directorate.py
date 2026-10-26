"""Small, presentation-independent record of observed operational events.

Producers may run on worker threads. Readers receive immutable snapshots; no
provider context, prompts, raw responses or exception bodies enter this stream.
"""
from __future__ import annotations

import json
import threading
import time
import sqlite3
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from core.paths import ARBITER_DIR

STATES = {"PENDING", "RUNNING", "AVAILABLE", "DEGRADED", "FAILED", "CANCELLED"}
STARTUP_COMPONENTS = ("CONFIG", "INTERFACE", "PROVIDER", "MEMORY", "AURELIUS")
ACTIVITY_LIMIT = 80
DISPATCH_LIMIT = 20
PREFERENCES_PATH = ARBITER_DIR / "directorate_preferences.json"
DISPATCH_ARCHIVE_PATH = ARBITER_DIR / "directorate_dispatches.sqlite3"


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
    "DISPATCH_ARCHIVE_FAILED",
    "SUBMISSION_CANCELLED",
    "MODEL_SUBSTITUTED", "ASSESSMENT_FAILED", "PROCESSING_FAILED",
    "SESSION_SAVE_FAILED", "REPORT_ARCHIVED", "REPORT_EXPORT_FAILED",
    "DECISION_SAVE_FAILED",
})


class Directorate:
    def __init__(self, limit: int = ACTIVITY_LIMIT, archive_path: Path | None = None) -> None:
        self._lock = threading.RLock()
        self._events: deque[OperationalEvent] = deque(maxlen=max(1, limit))
        self._checks: dict[str, OperationalEvent] = {}
        self._notices: deque[OperationalEvent] = deque(maxlen=ACTIVITY_LIMIT)
        self._dispatches: deque[DecisionDispatch] = deque(maxlen=DISPATCH_LIMIT)
        self._dispatch_number = 0
        self.archive_path = None
        if archive_path is not None:
            self.enable_archive(archive_path)

    def enable_archive(self, path: Path) -> None:
        """Opt-in durable public reports; raw provider audits stay in their existing stores."""
        with self._lock:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with sqlite3.connect(path, timeout=3) as db:
                    db.execute("CREATE TABLE IF NOT EXISTS dispatches (number INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, session_id TEXT NOT NULL UNIQUE, subject TEXT NOT NULL, verdict TEXT NOT NULL, report TEXT NOT NULL)")
                    rows = db.execute("SELECT number,timestamp,session_id,subject,verdict,report FROM dispatches ORDER BY number DESC LIMIT ?", (DISPATCH_LIMIT,)).fetchall()
                    self._dispatch_number = int(db.execute("SELECT COALESCE(MAX(number),0) FROM dispatches").fetchone()[0])
                self.archive_path = path
                self._dispatches = deque((DecisionDispatch(*row, 0.0) for row in reversed(rows)), maxlen=DISPATCH_LIMIT)
            except (OSError, sqlite3.Error):
                self.emit("LOCAL ARCHIVE", "DISPATCH_ARCHIVE_FAILED", "FAILED", "Dispatch archive unavailable; existing file preserved. New reports remain available for this session.")

    def search_dispatches(self, query: str = "", limit: int = 50) -> tuple[DecisionDispatch, ...]:
        with self._lock:
            if self.archive_path is None:
                needle = query.casefold().strip()
                return tuple(d for d in self._dispatches if not needle or needle in (d.subject + d.report + d.verdict + d.session_id).casefold())
            try:
                pattern = "%" + query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
                with sqlite3.connect(self.archive_path, timeout=3) as db:
                    rows = db.execute("SELECT number,timestamp,session_id,subject,verdict,report FROM dispatches WHERE report LIKE ? ESCAPE '\\' OR subject LIKE ? ESCAPE '\\' OR verdict LIKE ? ESCAPE '\\' OR session_id LIKE ? ESCAPE '\\' ORDER BY number DESC LIMIT ?", (pattern, pattern, pattern, pattern, max(1, min(limit, 100)))).fetchall()
                live = {d.session_id: d for d in self._dispatches}
                return tuple(live.get(row[2]) or DecisionDispatch(*row, 0.0) for row in reversed(rows))
            except sqlite3.Error:
                self.emit("LOCAL ARCHIVE", "DISPATCH_ARCHIVE_FAILED", "FAILED", "Dispatch archive search failed; local diagnostics available")
                return tuple(self._dispatches)

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
            if self.archive_path is not None:
                try:
                    with sqlite3.connect(self.archive_path, timeout=3) as db:
                        db.execute("INSERT OR IGNORE INTO dispatches (timestamp,session_id,subject,verdict,report) VALUES (?,?,?,?,?)", (dispatch.timestamp, dispatch.session_id, dispatch.subject, dispatch.verdict, dispatch.report))
                        row = db.execute("SELECT number,timestamp,session_id,subject,verdict,report FROM dispatches WHERE session_id=?", (dispatch.session_id,)).fetchone()
                    dispatch = DecisionDispatch(*row, dispatch.received_at)
                    self._dispatch_number = max(self._dispatch_number, dispatch.number)
                except sqlite3.Error:
                    self.emit("LOCAL ARCHIVE", "DISPATCH_ARCHIVE_FAILED", "FAILED", "Dispatch could not be saved; copy or export the report to retain it", result.session_id)
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
