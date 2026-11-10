"""Who answered each vote of a saved verdict: which company or local model, and whether a backup stepped in."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.names import TRIBUNAL_AGENT_IDS

_cache: Dict[str, tuple[float, str]] = {}


def _local_name(model: str) -> str:
    name = Path(str(model or "?").replace("\\", "/")).name
    for suffix in (".gguf", ".GGUF"):
        name = name.removesuffix(suffix)
    return name[:28]


def _source(vote: Dict[str, Any], turns: List[Dict[str, Any]]) -> str:
    from core.llm import online

    backend = str(vote.get("backend") or "")
    model = str(vote.get("model") or "")
    if backend == "not-asked" or any(turn.get("status") == "not_asked" for turn in turns):
        return "not asked"
    if backend in {"mock", "mock-fallback"} or model == "mock":
        return "simulation"
    if backend == "failed" or (vote.get("validation_errors") and not backend.startswith("online:")):
        return "failed"
    online_failed = any(turn.get("model_fallback_reason") == "online_model_failed" for turn in turns)
    if backend.startswith("online:"):
        provider = online.PROVIDERS.get(backend.split(":", 1)[1])
        name = online.SHORT_NAMES.get(provider.name, provider.name) if provider else backend.split(":", 1)[1]
        kind = "subscription" if provider and provider.subscription else "API"
        return f"{name} · {kind}" + (" (backup)" if online_failed else "")
    label = f"local {_local_name(model)}"
    if online_failed:
        return label + " (online failed)"
    if any(turn.get("model_fallback") for turn in turns):
        return label + " (fallback)"
    return label


def vote_sources(verdict: Dict[str, Any]) -> str:
    """One line, e.g. "RATIONALIS Claude · subscription | BELLATOR DeepSeek · API (backup)"; "" when unknown."""
    votes = verdict.get("votes") if isinstance(verdict.get("votes"), dict) else {}
    transcript = [turn for turn in verdict.get("deliberation_transcript") or [] if isinstance(turn, dict)]
    parts = []
    for agent in [*TRIBUNAL_AGENT_IDS, *(key for key in votes if key not in TRIBUNAL_AGENT_IDS)]:
        vote = votes.get(agent)
        if not isinstance(vote, dict):
            continue
        turns = [turn for turn in transcript if turn.get("agent_id") == agent]
        parts.append(f"{agent} {_source(vote, turns)}")
    return " | ".join(parts)


def vote_sources_for_file(path: Optional[str]) -> str:
    """vote_sources() for a verdict export file, cached until the file changes; "" when unreadable."""
    if not path:
        return ""
    try:
        mtime = Path(path).stat().st_mtime
    except OSError:
        return ""
    cached = _cache.get(path)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        line = vote_sources(json.loads(Path(path).read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, AttributeError):
        line = ""
    _cache[path] = (mtime, line)
    return line
