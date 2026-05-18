from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass(frozen=True)
class KnowledgeSource:
    id: str
    title: str
    location: str
    source_type: str = "document"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat())

