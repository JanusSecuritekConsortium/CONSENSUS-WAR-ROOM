"""What happened after a verdict: whether it was followed and how it turned out.

The owner records an outcome per decision; retrieval shows it beside the past decision, so later deliberations
cite a track record rather than only what was decided. A member's track record counts only decisions that were
followed and turned out clearly good or bad: approving a good result or denying a bad one is right.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.history import is_real_decision
from core.paths import ARBITER_DIR, HISTORY_PATH

OUTCOMES_PATH = ARBITER_DIR / "memory" / "outcomes.json"
RESULTS = ("good", "mixed", "bad")
DECIDED = ("APPROVE", "APPROVED", "CONDITIONAL_APPROVAL", "CAUTION", "DENY", "DENIED")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_outcomes(path: Path = OUTCOMES_PATH) -> Dict[str, Dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _decisions(history_path: Path) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [item for item in payload if isinstance(item, dict) and is_real_decision(item)] if isinstance(payload, list) else []


def record_outcome(session_id: str, *, followed: bool, result: str, note: str = "",
                   path: Path = OUTCOMES_PATH, history_path: Path = HISTORY_PATH, now: Optional[str] = None) -> Dict[str, Any]:
    if result not in RESULTS:
        raise ValueError(f"Result must be one of: {', '.join(RESULTS)}")
    if not any(str(item.get("session_id")) == session_id for item in _decisions(history_path)):
        raise ValueError(f"No real decision with session id {session_id}")
    outcomes = load_outcomes(path)
    outcome = {"followed": bool(followed), "result": result, "note": " ".join(note.split())[:500], "recorded_at": now or _now()}
    outcomes[session_id] = outcome
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(outcomes, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)
    return outcome


def describe(outcome: Optional[Dict[str, Any]]) -> str:
    if not outcome:
        return "outcome not recorded"
    text = ("followed" if outcome.get("followed") else "not followed") + f", turned out {outcome.get('result')}"
    return text + (f" ({outcome['note']})" if outcome.get("note") else "")


def pending_outcomes(min_age_days: int = 7, *, path: Path = OUTCOMES_PATH, history_path: Path = HISTORY_PATH,
                     now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Real decided verdicts at least `min_age_days` old with no outcome yet, oldest first."""
    outcomes = load_outcomes(path)
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=min_age_days)
    pending = []
    for item in _decisions(history_path):
        if str(item.get("verdict") or "").upper() not in DECIDED or str(item.get("session_id")) in outcomes:
            continue
        try:
            stamp = datetime.fromisoformat(str(item.get("timestamp")))
        except ValueError:
            continue
        if (stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)) <= cutoff:
            pending.append(item)
    return pending


def track_record(*, path: Path = OUTCOMES_PATH, history_path: Path = HISTORY_PATH) -> Dict[str, Dict[str, int]]:
    outcomes = load_outcomes(path)
    record: Dict[str, Dict[str, int]] = {}
    for item in _decisions(history_path):
        outcome = outcomes.get(str(item.get("session_id")))
        if not outcome or not outcome.get("followed") or outcome.get("result") == "mixed":
            continue
        for agent, vote in (item.get("votes") or {}).items():
            value = str((vote or {}).get("vote") or "").upper()
            if value not in ("APPROVE", "DENY"):
                continue
            right = (value == "APPROVE") == (outcome["result"] == "good")
            counts = record.setdefault(agent, {"right": 0, "wrong": 0})
            counts["right" if right else "wrong"] += 1
    return record


def overview(limit: int = 10, *, path: Path = OUTCOMES_PATH, history_path: Path = HISTORY_PATH,
             now: Optional[datetime] = None) -> Dict[str, Any]:
    """Recent real decisions with their outcomes, the ones still waiting for an outcome, and the track record."""
    outcomes = load_outcomes(path)

    def brief(item: Dict[str, Any]) -> Dict[str, Any]:
        query = " ".join(str(item.get("query") or "").split())
        return {"session_id": str(item.get("session_id")), "timestamp": item.get("timestamp"),
                "question": query[:200] + ("..." if len(query) > 200 else ""), "verdict": item.get("verdict"),
                "outcome": describe(outcomes.get(str(item.get("session_id"))))}

    decisions = sorted(_decisions(history_path), key=lambda item: str(item.get("timestamp") or ""), reverse=True)
    record = track_record(path=path, history_path=history_path)
    return {
        "recent": [brief(item) for item in decisions[:limit]],
        "awaiting_outcome": [brief(item) for item in pending_outcomes(path=path, history_path=history_path, now=now)],
        "track_record": record,
        "summary": track_record_line(record) or "No followed decision has a clear good or bad outcome yet.",
        "recorded_outcomes": len(outcomes),
    }


def track_record_line(record: Dict[str, Dict[str, int]]) -> str:
    if not record:
        return ""
    parts = [f"{agent} {counts['right']} right, {counts['wrong']} wrong" for agent, counts in sorted(record.items())]
    return "Track record on decisions with recorded outcomes: " + "; ".join(parts) + "."
