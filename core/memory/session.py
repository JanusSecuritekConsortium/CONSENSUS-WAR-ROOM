from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.logging import log_error, log_event
from core.paths import CONTEXT_INDEX_PATH, SESSION_MEMORY_PATH


class SessionMemoryError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now().isoformat()


def _empty_sessions() -> Dict[str, Any]:
    return {"version": 1, "sessions": []}


def _backup_corrupt(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.stem}.corrupt.{timestamp}{path.suffix}.bak")
    backup.parent.mkdir(parents=True, exist_ok=True)
    os.replace(path, backup)
    return backup


def _load_json_object(path: Path, empty: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return dict(empty)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        backup = _backup_corrupt(path)
        log_error("session_memory_corruption", exc, {"path": str(path), "backup": str(backup)})
        return dict(empty)
    if not isinstance(payload, dict):
        backup = _backup_corrupt(path)
        log_event("session_memory_invalid_shape", {"path": str(path), "backup": str(backup)}, level="WARN")
        return dict(empty)
    return payload


def _atomic_write(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def load_session_memory(path: Path = SESSION_MEMORY_PATH) -> Dict[str, Any]:
    payload = _load_json_object(path, _empty_sessions())
    sessions = payload.get("sessions")
    if not isinstance(sessions, list):
        sessions = []
    payload["version"] = payload.get("version", 1)
    payload["sessions"] = sessions
    return payload


def save_session_memory(memory: Dict[str, Any], path: Path = SESSION_MEMORY_PATH) -> None:
    if not isinstance(memory, dict):
        raise SessionMemoryError("Session memory payload must be a dictionary.")
    memory.setdefault("version", 1)
    if not isinstance(memory.get("sessions"), list):
        memory["sessions"] = []
    _atomic_write(path, memory)
    log_event("session_memory_write", {"path": str(path), "sessions": len(memory["sessions"])})


def upsert_session_record(record: Dict[str, Any], path: Path = SESSION_MEMORY_PATH) -> Dict[str, Any]:
    if not record.get("session_id"):
        raise SessionMemoryError("Session record requires session_id.")
    memory = load_session_memory(path)
    sessions: List[Dict[str, Any]] = [item for item in memory["sessions"] if isinstance(item, dict)]
    session_id = str(record["session_id"])
    record = {**record, "updated_at": _now()}
    for index, existing in enumerate(sessions):
        if str(existing.get("session_id")) == session_id:
            sessions[index] = {**existing, **record}
            break
    else:
        record.setdefault("created_at", _now())
        sessions.append(record)
    memory["sessions"] = sessions[-1000:]
    save_session_memory(memory, path)
    rebuild_context_index(memory, CONTEXT_INDEX_PATH)
    return record


def rebuild_context_index(memory: Dict[str, Any], path: Path = CONTEXT_INDEX_PATH) -> Dict[str, Any]:
    entries = []
    for session in memory.get("sessions", []):
        if not isinstance(session, dict):
            continue
        text_parts = [
            str(session.get("proposal", "")),
            str(session.get("verdict", "")),
            str(session.get("synthesis_summary", "")),
            " ".join(str(tag) for tag in session.get("tags", []) if tag),
        ]
        keywords = sorted(_keywords(" ".join(text_parts)))
        entries.append(
            {
                "session_id": session.get("session_id"),
                "timestamp": session.get("timestamp"),
                "theme": session.get("active_theme"),
                "verdict": session.get("verdict"),
                "keywords": keywords,
                "tags": session.get("tags", []),
                "summary": session.get("synthesis_summary", ""),
            }
        )
    payload = {"version": 1, "updated_at": _now(), "entries": entries[-1000:]}
    _atomic_write(path, payload)
    return payload


def _keywords(text: str) -> set[str]:
    clean = "".join(char.lower() if char.isalnum() else " " for char in text)
    return {word for word in clean.split() if len(word) >= 4}


def session_summary(path: Path = SESSION_MEMORY_PATH, limit: int = 5) -> str:
    memory = load_session_memory(path)
    sessions = [item for item in memory.get("sessions", []) if isinstance(item, dict)]
    lines = [
        f"SESSION MEMORY: ACTIVE",
        f"TOTAL SESSIONS: {len(sessions)}",
        f"CONTEXT INDEX: {CONTEXT_INDEX_PATH}",
    ]
    for session in sessions[-limit:]:
        lines.append(
            f"- {session.get('session_id')} | {session.get('verdict', '--')} | {session.get('active_theme', '--')} | {session.get('proposal', '')[:80]}"
        )
    return "\n".join(lines)


def memory_status(path: Path = SESSION_MEMORY_PATH) -> Dict[str, Any]:
    memory = load_session_memory(path)
    sessions = [item for item in memory.get("sessions", []) if isinstance(item, dict)]
    return {
        "session_memory": "ACTIVE",
        "session_count": len(sessions),
        "session_memory_path": str(path),
        "context_index_path": str(CONTEXT_INDEX_PATH),
        "context_index_exists": CONTEXT_INDEX_PATH.exists(),
    }
