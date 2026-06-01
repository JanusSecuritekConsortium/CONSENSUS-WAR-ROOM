from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class NormalizedDataItem:
    item_id: str
    source: str
    source_type: str
    title: str
    summary: str
    url: str
    published_at: str
    fetched_at: str
    geography: List[str] = field(default_factory=list)
    actors: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    confidence: float = 0.0
    credibility: float = 0.0
    bias_label: str | None = None
    raw_ref: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DataSourceHealth:
    source_id: str
    display_name: str
    enabled: bool
    status: str
    checked_at: str
    requires_credentials: bool = False
    degraded_reason: str | None = None
    missing_credentials: List[str] = field(default_factory=list)
    fetched_at: str | None = None
    freshness: str = "unknown"
    item_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DataSourceAdapter(ABC):
    source_id = "unknown"
    display_name = "Unknown"
    source_type = "unknown"
    requires_credentials = False

    def __init__(self, config: Dict[str, Any] | None = None, session: Any = None) -> None:
        self.config = dict(config or {})
        self.enabled = bool(self.config.get("enabled", False))
        self.session = session

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        raise NotImplementedError
    @abstractmethod
    def fetch(self, query: str = "", context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw_items: List[Dict[str, Any]]) -> List[NormalizedDataItem]:
        raise NotImplementedError
