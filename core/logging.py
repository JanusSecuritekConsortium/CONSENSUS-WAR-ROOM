from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.paths import SYSTEM_LOG_PATH

# When the log reaches this size it is renamed to <name>.<YYYYmmdd-HHMMSS-nanoseconds> and a new one starts.
# Old files are never deleted here: decision traces live in them, so the readers below search them too.
SYSTEM_LOG_MAX_BYTES = 25 * 1024 * 1024
_ROTATED_SUFFIX = re.compile(r"^\d{8}-\d{6}-\d{9}$")


def rotated_log_files(path: Path) -> List[Path]:
    """The renamed earlier parts of a log, oldest first."""
    if not path.parent.is_dir():
        return []
    prefix = path.name + "."
    parts = [
        candidate
        for candidate in path.parent.glob(path.name + ".*")
        if candidate.is_file() and _ROTATED_SUFFIX.match(candidate.name[len(prefix):])
    ]
    return sorted(parts, key=lambda candidate: candidate.name)


def log_files(path: Path) -> List[Path]:
    """Every part of a log that exists, oldest first, the current file last."""
    files = rotated_log_files(path)
    if path.is_file():
        files.append(path)
    return files


def _rotate_if_large(path: Path) -> None:
    try:
        if path.stat().st_size < SYSTEM_LOG_MAX_BYTES:
            return
    except OSError:
        return
    stamp = f"{datetime.now():%Y%m%d-%H%M%S}-{time.time_ns() % 1_000_000_000:09d}"
    try:
        path.rename(path.with_name(f"{path.name}.{stamp}"))
    except OSError:
        # Windows refuses while another process has the file open; keep appending and try next time.
        pass


def log_event(
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    level: str = "INFO",
) -> None:
    SYSTEM_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _rotate_if_large(SYSTEM_LOG_PATH)
    record = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "event_type": event_type,
        "payload": payload or {},
    }
    with SYSTEM_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True, default=str) + "\n")


def log_error(event_type: str, error: Exception, payload: Optional[Dict[str, Any]] = None) -> None:
    error_payload = dict(payload or {})
    error_payload["error_type"] = error.__class__.__name__
    error_payload["error"] = str(error)
    log_event(event_type, error_payload, level="ERROR")


def log_decision_trace(result: Any) -> None:
    from core.voting.follow_up import unresolved_next_steps
    votes = {
        agent_id: {
            "vote": vote.vote.value,
            "confidence": vote.confidence,
            "evidence_quality": vote.evidence_quality,
            "critical_risk": vote.critical_risk,
            "model": vote.model,
            "backend": vote.backend,
            "argument": vote.argument, "peer_responses": vote.peer_responses,
            "evidence_audit": vote.evidence_audit,
            "review_required": vote.review_required, "review_reason": vote.review_reason,
            "vote_change_reason": vote.vote_change_reason, "unresolved_disagreements": vote.unresolved_disagreements,
        }
        for agent_id, vote in result.votes.items()
    }
    log_event(
        "decision_trace",
        {
            "proposal_id": result.session_id,
            "session_id": result.session_id,
            "taxonomy": result.proposal_classification,
            "votes": votes,
            "final_verdict": result.verdict.value,
            "confidence": result.confidence,
            "terminal_branch": result.terminal_branch,
            "review_triggers": result.review_triggers,
            "next_steps": unresolved_next_steps(result),
            "deliberation_transcript": result.deliberation_transcript,
            "deliberation_complete": result.deliberation_complete,
            "simulation": result.simulation,
            "lifecycle_events": list(getattr(result, "lifecycle_events", [])),
            "phase_durations": dict(getattr(result, "phase_durations", {})),
            "reasoning_stream": list(getattr(result, "reasoning_stream", [])),
            "convergence_percent": getattr(result, "convergence_percent", 0.0),
        },
    )


def fsync_file(handle: Any) -> None:
    handle.flush()
    os.fsync(handle.fileno())
