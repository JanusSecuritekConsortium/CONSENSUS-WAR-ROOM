from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from core.paths import ARBITER_DIR


RSS_INTELLIGENCE_DB_PATH = ARBITER_DIR / "cache" / "data_sources" / "intelligence.db"
RSS_HEALTH_STATES = {
    "READY",
    "STALE",
    "INVALID_FORMAT",
    "HTTP_ERROR",
    "REDIRECTED_TO_HTML",
    "DISABLED",
}
TRACKING_QUERY_PREFIXES = ("utm_", "fbclid", "gclid")


class RssIntelligenceStore:
    def __init__(self, path: Path = RSS_INTELLIGENCE_DB_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS rss_sources (
                    source_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL DEFAULT '',
                    tier INTEGER NOT NULL,
                    taxonomy_tags TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    quarantined INTEGER NOT NULL DEFAULT 0,
                    discovered_from TEXT,
                    status TEXT NOT NULL DEFAULT 'STALE',
                    etag TEXT,
                    last_modified TEXT,
                    last_attempt_at TEXT,
                    last_success_at TEXT,
                    next_poll_at TEXT,
                    failure_count INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    http_status INTEGER,
                    content_type TEXT,
                    final_url TEXT
                );
                CREATE TABLE IF NOT EXISTS rss_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id TEXT NOT NULL UNIQUE,
                    source_id TEXT NOT NULL,
                    guid TEXT NOT NULL DEFAULT '',
                    canonical_url TEXT NOT NULL DEFAULT '',
                    content_hash TEXT NOT NULL,
                    title TEXT NOT NULL,
                    excerpt TEXT NOT NULL,
                    published_at TEXT,
                    fetched_at TEXT NOT NULL,
                    taxonomy_tags TEXT NOT NULL,
                    sentiment_label TEXT,
                    sentiment_confidence REAL,
                    FOREIGN KEY(source_id) REFERENCES rss_sources(source_id)
                );
                CREATE INDEX IF NOT EXISTS idx_rss_items_guid ON rss_items(guid);
                CREATE INDEX IF NOT EXISTS idx_rss_items_url ON rss_items(canonical_url);
                CREATE INDEX IF NOT EXISTS idx_rss_items_hash ON rss_items(content_hash);
                CREATE INDEX IF NOT EXISTS idx_rss_items_source ON rss_items(source_id);
                CREATE VIRTUAL TABLE IF NOT EXISTS rss_items_fts USING fts5(
                    title,
                    excerpt,
                    content='rss_items',
                    content_rowid='id'
                );
                CREATE TRIGGER IF NOT EXISTS rss_items_ai AFTER INSERT ON rss_items BEGIN
                    INSERT INTO rss_items_fts(rowid, title, excerpt) VALUES (new.id, new.title, new.excerpt);
                END;
                CREATE TRIGGER IF NOT EXISTS rss_items_ad AFTER DELETE ON rss_items BEGIN
                    INSERT INTO rss_items_fts(rss_items_fts, rowid, title, excerpt) VALUES ('delete', old.id, old.title, old.excerpt);
                END;
                CREATE TRIGGER IF NOT EXISTS rss_items_au AFTER UPDATE ON rss_items BEGIN
                    INSERT INTO rss_items_fts(rss_items_fts, rowid, title, excerpt) VALUES ('delete', old.id, old.title, old.excerpt);
                    INSERT INTO rss_items_fts(rowid, title, excerpt) VALUES (new.id, new.title, new.excerpt);
                END;
                """
            )

    def sync_sources(self, feeds: Iterable[Dict[str, Any]]) -> None:
        with self.connect() as connection:
            for feed in feeds:
                status = "DISABLED" if not feed.get("enabled", False) or feed.get("quarantined", False) else "STALE"
                connection.execute(
                    """
                    INSERT INTO rss_sources(source_id, name, url, tier, taxonomy_tags, enabled, quarantined, discovered_from, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_id) DO UPDATE SET
                        name=excluded.name, url=excluded.url, tier=excluded.tier,
                        taxonomy_tags=excluded.taxonomy_tags, enabled=excluded.enabled,
                        quarantined=excluded.quarantined, discovered_from=excluded.discovered_from,
                        status=CASE WHEN excluded.enabled=0 OR excluded.quarantined=1 THEN 'DISABLED' ELSE rss_sources.status END
                    """,
                    (
                        str(feed["source_id"]),
                        str(feed["name"]),
                        str(feed.get("url") or ""),
                        int(feed.get("tier", 2)),
                        json.dumps(feed.get("taxonomy_tags", [])),
                        int(bool(feed.get("enabled", False))),
                        int(bool(feed.get("quarantined", False))),
                        str(feed.get("discovery_url") or ""),
                        status,
                    ),
                )

    def source(self, source_id: str) -> Dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM rss_sources WHERE source_id=?", (source_id,)).fetchone()
        return dict(row) if row else None

    def sources(self) -> List[Dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM rss_sources ORDER BY tier, source_id").fetchall()
        return [dict(row) for row in rows]

    def update_source(self, source_id: str, **values: Any) -> None:
        allowed = {
            "url", "status", "etag", "last_modified", "last_attempt_at", "last_success_at",
            "next_poll_at", "failure_count", "last_error", "http_status", "content_type", "final_url",
        }
        fields = [(key, value) for key, value in values.items() if key in allowed]
        if not fields:
            return
        with self.connect() as connection:
            connection.execute(
                f"UPDATE rss_sources SET {', '.join(f'{key}=?' for key, _ in fields)} WHERE source_id=?",
                (*[value for _, value in fields], source_id),
            )

    def upsert_items(
        self,
        source_id: str,
        entries: Iterable[Dict[str, Any]],
        taxonomy_tags: List[str],
        fetched_at: str | None = None,
    ) -> Dict[str, int]:
        inserted = 0
        deduplicated = 0
        with self.connect() as connection:
            for entry in entries:
                normalized = normalize_rss_item(source_id, {**entry, "fetched_at": fetched_at or entry.get("fetched_at")}, taxonomy_tags)
                existing = connection.execute(
                    """
                    SELECT id FROM rss_items
                    WHERE (? <> '' AND guid=?)
                       OR (? <> '' AND canonical_url=?)
                       OR content_hash=?
                    LIMIT 1
                    """,
                    (
                        normalized["guid"], normalized["guid"],
                        normalized["canonical_url"], normalized["canonical_url"],
                        normalized["content_hash"],
                    ),
                ).fetchone()
                if existing:
                    connection.execute(
                        "UPDATE rss_items SET fetched_at=?, taxonomy_tags=? WHERE id=?",
                        (normalized["fetched_at"], normalized["taxonomy_tags"], existing["id"]),
                    )
                    deduplicated += 1
                    continue
                connection.execute(
                    """
                    INSERT INTO rss_items(
                        item_id, source_id, guid, canonical_url, content_hash, title, excerpt,
                        published_at, fetched_at, taxonomy_tags, sentiment_label, sentiment_confidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    tuple(normalized[key] for key in (
                        "item_id", "source_id", "guid", "canonical_url", "content_hash", "title",
                        "excerpt", "published_at", "fetched_at", "taxonomy_tags", "sentiment_label",
                        "sentiment_confidence",
                    )),
                )
                inserted += 1
        return {"inserted": inserted, "deduplicated": deduplicated}

    def search(self, query: str = "", taxonomy_tags: List[str] | None = None, limit: int = 12) -> List[Dict[str, Any]]:
        requested_tags = {tag.upper() for tag in taxonomy_tags or []}
        tokens = re.findall(r"[A-Za-z0-9_]{2,}", query)
        with self.connect() as connection:
            if tokens:
                match = " OR ".join(f'"{token}"' for token in tokens[:12])
                rows = connection.execute(
                    """
                    SELECT rss_items.*, rss_sources.name AS source_name FROM rss_items_fts
                    JOIN rss_items ON rss_items.id=rss_items_fts.rowid
                    JOIN rss_sources ON rss_sources.source_id=rss_items.source_id
                    WHERE rss_items_fts MATCH ?
                    ORDER BY bm25(rss_items_fts)
                    LIMIT 120
                    """,
                    (match,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT rss_items.*, rss_sources.name AS source_name FROM rss_items
                    JOIN rss_sources ON rss_sources.source_id=rss_items.source_id
                    ORDER BY fetched_at DESC LIMIT 120
                    """
                ).fetchall()
        ranked: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            item = dict(row)
            tags = [str(tag).upper() for tag in json.loads(item["taxonomy_tags"])]
            if requested_tags and not requested_tags.intersection(tags):
                continue
            identity = item["canonical_url"] or item["guid"] or item["content_hash"]
            if identity in seen:
                continue
            seen.add(identity)
            freshness = freshness_seconds(item.get("published_at") or item.get("fetched_at"))
            ranked.append(
                {
                    "title": item["title"],
                    "source": item["source_name"],
                    "url": item["canonical_url"],
                    "published_at": item["published_at"],
                    "fetched_at": item["fetched_at"],
                    "freshness_seconds": freshness,
                    "taxonomy_tags": tags,
                    "excerpt": item["excerpt"],
                    **(
                        {
                            "sentiment_label": item["sentiment_label"],
                            "sentiment_confidence": item["sentiment_confidence"],
                        }
                        if item.get("sentiment_confidence") is not None
                        else {}
                    ),
                }
            )
        ranked.sort(key=lambda item: item["freshness_seconds"])
        return ranked[: max(0, min(limit, 12))]

    def status(self) -> Dict[str, Any]:
        sources = self.sources()
        with self.connect() as connection:
            item_count = int(connection.execute("SELECT COUNT(*) FROM rss_items").fetchone()[0])
        return {
            "database_path": str(self.path),
            "source_count": len(sources),
            "item_count": item_count,
            "source_health": sources,
            "fts5_enabled": True,
        }


def canonicalize_url(url: str) -> str:
    if not url:
        return ""
    split = urlsplit(url.strip())
    query = urlencode(
        sorted((key, value) for key, value in parse_qsl(split.query, keep_blank_values=True) if not key.lower().startswith(TRACKING_QUERY_PREFIXES))
    )
    return urlunsplit((split.scheme.lower(), split.netloc.lower(), split.path, query, ""))


def normalize_rss_item(source_id: str, entry: Dict[str, Any], taxonomy_tags: List[str]) -> Dict[str, Any]:
    guid = str(entry.get("guid") or "").strip()
    canonical_url = canonicalize_url(str(entry.get("url") or ""))
    title = str(entry.get("title") or "").strip()
    excerpt = str(entry.get("excerpt") or entry.get("summary") or "").strip()[:1200]
    published_at = iso_timestamp(entry.get("published_at"))
    fetched_at = iso_timestamp(entry.get("fetched_at")) or now_iso()
    content_hash = hashlib.sha256(f"{title}|{excerpt}|{canonical_url}".encode("utf-8", errors="replace")).hexdigest()
    return {
        "item_id": hashlib.sha256(f"{source_id}|{guid}|{canonical_url}|{content_hash}".encode("utf-8")).hexdigest()[:24],
        "source_id": source_id,
        "guid": guid,
        "canonical_url": canonical_url,
        "content_hash": content_hash,
        "title": title,
        "excerpt": excerpt,
        "published_at": published_at,
        "fetched_at": fetched_at,
        "taxonomy_tags": json.dumps(sorted({tag.upper() for tag in taxonomy_tags})),
        "sentiment_label": entry.get("sentiment_label") if entry.get("sentiment_confidence") is not None else None,
        "sentiment_confidence": entry.get("sentiment_confidence"),
    }


def freshness_seconds(value: Any) -> int:
    parsed = parse_timestamp(value)
    return max(0, int((datetime.now(timezone.utc) - parsed).total_seconds())) if parsed else 0


def iso_timestamp(value: Any) -> str | None:
    parsed = parse_timestamp(value)
    return parsed.isoformat() if parsed else None


def parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        from email.utils import parsedate_to_datetime

        try:
            parsed = parsedate_to_datetime(str(value))
        except (TypeError, ValueError):
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
