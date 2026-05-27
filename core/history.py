from __future__ import annotations

import json
import os
import time
import uuid
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from config.names import LEGACY_ROLE_TO_AGENT_ID
from config.nodes import DEFAULT_NODES
from core.logging import log_error, log_event
from core.models import FinalVerdict, TribunalResult, Vote, VoteValue
from core.paths import ARBITER_DIR, HISTORY_PATH, LEGACY_HISTORY_PATH


def result_to_dict(result: TribunalResult) -> Dict[str, Any]:
    payload = asdict(result)
    payload["verdict"] = result.verdict.value
    payload["votes"] = {key: serialize_vote(vote) for key, vote in result.votes.items()}
    return payload


def serialize_vote(vote: Vote) -> Dict[str, Any]:
    data = asdict(vote)
    data["vote"] = vote.vote.value
    return data


def record_result(result: TribunalResult, history_path: Path = HISTORY_PATH) -> None:
    ARBITER_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = history_path.with_name(f"{history_path.name}.lock")
    lock_fd = _acquire_lock(lock_path)
    try:
        history: List[Dict[str, Any]] = []
        if history_path.exists():
            try:
                loaded = json.loads(history_path.read_text(encoding="utf-8"))
                if isinstance(loaded, list):
                    history = loaded
            except json.JSONDecodeError as exc:
                log_error("history_load_error", exc, {"path": str(history_path)})
                raise RuntimeError(f"Decision history is corrupt: {history_path}") from exc

        history.append(result_to_dict(result))
        _atomic_write_json(history_path, history[-1000:])
        log_event("decision_history_write", {"path": str(history_path), "session_id": result.session_id})
    finally:
        _release_lock(lock_fd, lock_path)


def _acquire_lock(lock_path: Path, timeout_seconds: float = 10.0) -> int:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            return os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Timed out waiting for decision history lock: {lock_path}")
            time.sleep(0.05)


def _release_lock(lock_fd: int, lock_path: Path) -> None:
    try:
        os.close(lock_fd)
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def migrate_legacy_history(
    legacy_path: Path = LEGACY_HISTORY_PATH,
    target_path: Path = HISTORY_PATH,
) -> int:
    """Copy legacy decision records into the Genesis audit log without editing legacy data."""

    if not legacy_path.exists():
        return 0

    try:
        legacy_records = json.loads(legacy_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0

    if not isinstance(legacy_records, list):
        return 0

    existing: List[Dict[str, Any]] = []
    if target_path.exists():
        try:
            loaded = json.loads(target_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                existing = loaded
        except json.JSONDecodeError:
            existing = []

    seen = {
        (
            item.get("migration", {}).get("source"),
            item.get("migration", {}).get("legacy_session_id"),
            item.get("timestamp"),
            item.get("query"),
        )
        for item in existing
    }

    migrated_count = 0

    for record in legacy_records:
        if not isinstance(record, dict):
            continue

        marker = (
            str(legacy_path),
            record.get("session_id"),
            record.get("timestamp"),
            record.get("query"),
        )
        if marker in seen:
            continue

        votes: Dict[str, Dict[str, Any]] = {}
        legacy_votes = record.get("votes", {})
        if isinstance(legacy_votes, dict):
            for legacy_name, vote_data in legacy_votes.items():
                key = LEGACY_ROLE_TO_AGENT_ID.get(
                    str(legacy_name).upper(),
                    str(legacy_name).upper(),
                )
                if key is None or not isinstance(vote_data, dict):
                    continue
                vote_value = str(vote_data.get("vote", "ERROR")).upper()
                if vote_value not in VoteValue.__members__:
                    vote_value = VoteValue.ERROR.value
                votes[key] = {
                    "node_key": key,
                    "role": DEFAULT_NODES[key].role,
                    "vote": vote_value,
                    "confidence": float(vote_data.get("confidence", 0.0) or 0.0),
                    "reasoning": str(vote_data.get("reasoning", "")),
                    "risks": [],
                    "conditions": [],
                    "model": str(vote_data.get("model", "legacy")),
                    "response_time": float(vote_data.get("response_time", 0.0) or 0.0),
                    "raw_response": "",
                    "timestamp": str(vote_data.get("timestamp", record.get("timestamp", ""))),
                }

        migrated = {
            "query": record.get("query", ""),
            "verdict": record.get("verdict", FinalVerdict.ERROR.value),
            "confidence": float(record.get("confidence", 0.0) or 0.0),
            "reason": "Migrated from legacy CONSENSUS decision history.",
            "votes": votes,
            "vote_distribution": dict(Counter(v.get("vote", "ERROR") for v in votes.values())),
            "quorum_met": False,
            "review_triggers": ["legacy_migration"],
            "session_id": f"legacy-{record.get('session_id', uuid.uuid4().hex[:8])}",
            "theme": "legacy",
            "timestamp": record.get("timestamp", datetime.now().isoformat()),
            "migration": {
                "source": str(legacy_path),
                "legacy_session_id": record.get("session_id"),
                "migrated_at": datetime.now().isoformat(),
            },
        }
        existing.append(migrated)
        seen.add(marker)
        migrated_count += 1

    target_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(target_path, existing[-1000:])
    return migrated_count


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        last_error: OSError | None = None
        for _ in range(6):
            try:
                os.replace(tmp_path, path)
                last_error = None
                break
            except OSError as exc:
                last_error = exc
                time.sleep(0.05)
        if last_error is not None:
            raise last_error
    except OSError as exc:
        log_error("history_write_error", exc, {"path": str(path), "tmp_path": str(tmp_path)})
        raise RuntimeError(f"Unable to write decision history: {path}") from exc
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
