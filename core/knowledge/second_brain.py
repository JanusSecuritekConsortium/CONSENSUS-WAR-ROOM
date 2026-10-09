"""Read the bounded, curated startup brief; never crawl private source folders."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


MAX_BRIEF_BYTES = 8192


def shared_brain_context() -> dict[str, Any]:
    configured = os.environ.get("CONSENSUS_SECOND_BRAIN")
    if not configured and os.name != "nt":
        return {"status": "not_configured"}
    vault = Path(configured or r"G:\Obsidian\CONSENSUS_SYSTEM")
    brief = vault / "50 Agents" / "Shared Context.md"
    try:
        with brief.open("rb") as stream:
            raw = stream.read(MAX_BRIEF_BYTES + 1)
        if len(raw) > MAX_BRIEF_BYTES:
            return {"status": "brief_too_large"}
        content = raw.decode("utf-8-sig").strip()
    except (OSError, UnicodeError):
        return {"status": "unavailable"}
    if not content:
        return {"status": "empty"}
    return {
        "status": "available",
        "source": str(brief),
        "content": content,
        "scope": "curated startup brief only; full source documents are not loaded",
    }
