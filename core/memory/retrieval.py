from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from core.paths import HISTORY_PATH, SESSION_MEMORY_PATH
from core.memory.session import load_session_memory


def keywords(text: str) -> set[str]:
    clean = "".join(char.lower() if char.isalnum() else " " for char in text)
    return {word for word in clean.split() if len(word) >= 4}


def _load_history(path: Path = HISTORY_PATH) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return payload if isinstance(payload, list) else []


def retrieve_relevant_context(
    query: str,
    tags: List[str] | None = None,
    limit: int = 3,
    latest: int = 3,
    session_path: Path = SESSION_MEMORY_PATH,
    history_path: Path = HISTORY_PATH,
) -> Dict[str, Any]:
    query_terms = keywords(query)
    tag_terms = {tag.lower() for tag in (tags or []) if tag}
    sessions = [item for item in load_session_memory(session_path).get("sessions", []) if isinstance(item, dict)]
    history = _load_history(history_path)

    candidates_by_session: Dict[str, Dict[str, Any]] = {}
    for item in [*sessions, *history]:
        proposal = str(item.get("proposal") or item.get("query") or "")
        summary = str(item.get("synthesis_summary") or item.get("reason") or "")
        item_tags = {str(tag).lower() for tag in item.get("tags", []) if tag} if isinstance(item.get("tags", []), list) else set()
        overlap = query_terms & keywords(f"{proposal} {summary}")
        tag_overlap = tag_terms & item_tags
        score = len(overlap) + (2 * len(tag_overlap))
        if score:
            session_id = str(item.get("session_id") or f"anonymous-{len(candidates_by_session)}")
            candidate = {
                    "session_id": session_id,
                    "proposal": proposal,
                    "verdict": item.get("verdict"),
                    "summary": summary,
                    "theme": item.get("active_theme") or item.get("theme"),
                    "timestamp": item.get("timestamp"),
                    "score": score,
                    "matched_keywords": sorted(overlap),
                    "matched_tags": sorted(tag_overlap),
                }
            existing = candidates_by_session.get(session_id)
            if existing is None or candidate["score"] >= existing["score"]:
                candidates_by_session[session_id] = candidate
    candidates = list(candidates_by_session.values())
    candidates.sort(key=lambda item: (item["score"], str(item.get("timestamp") or "")), reverse=True)

    latest_items = []
    latest_seen: set[str] = set()
    for item in [*sessions, *history][-latest:]:
        if isinstance(item, dict):
            session_id = str(item.get("session_id") or "")
            if session_id in latest_seen:
                continue
            latest_seen.add(session_id)
            latest_items.append(
                {
                    "session_id": session_id,
                    "proposal": str(item.get("proposal") or item.get("query") or ""),
                    "verdict": item.get("verdict"),
                    "summary": str(item.get("synthesis_summary") or item.get("reason") or ""),
                    "theme": item.get("active_theme") or item.get("theme"),
                    "timestamp": item.get("timestamp"),
                }
            )

    selected = candidates[:limit]
    seen = {item.get("session_id") for item in selected}
    for item in latest_items:
        if len(selected) >= limit:
            break
        if item.get("session_id") not in seen:
            selected.append({**item, "score": 0, "matched_keywords": [], "matched_tags": []})

    return {
        "query": query,
        "retrieval": "keyword_overlap",
        "prior_decisions_used": len(selected),
        "items": selected,
        "summary": summarize_context(selected),
    }


def summarize_context(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "No prior decisions retrieved."
    lines = []
    for item in items:
        proposal = str(item.get("proposal", "")).replace("\n", " ")[:120]
        lines.append(
            f"{item.get('session_id', '--')} | {item.get('verdict', '--')} | {proposal}"
        )
    return "\n".join(lines)


def search_decisions(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    packet = retrieve_relevant_context(query, limit=limit, latest=0)
    return packet["items"]
