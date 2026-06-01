"""Strict RSS/Atom probing and parsing for Bellator intelligence feeds."""

from __future__ import annotations

from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from html import unescape
import re
from typing import Any
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

import requests


HTML_CONTENT_TYPES = ("text/html", "application/xhtml+xml")
FEED_ROOTS = {"rss", "feed", "rdf"}


@dataclass(frozen=True)
class FeedProbeResult:
    source_id: str
    status: str
    requested_url: str
    final_url: str
    http_status: int | None = None
    content_type: str = ""
    etag: str = ""
    last_modified: str = ""
    entries: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    not_modified: bool = False
    error: str = ""
    discovered_from: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "status": self.status,
            "requested_url": self.requested_url,
            "final_url": self.final_url,
            "http_status": self.http_status,
            "content_type": self.content_type,
            "etag": self.etag,
            "last_modified": self.last_modified,
            "entries": list(self.entries),
            "not_modified": self.not_modified,
            "error": self.error,
            "discovered_from": self.discovered_from,
        }


def discover_feed_url(feed: dict[str, Any], session: Any | None = None) -> str:
    """Resolve a feed URL from an official directory page when configured."""

    directory_url = str(feed.get("discovery_url", "")).strip()
    match = str(feed.get("discovery_match", "")).strip().lower()
    if not directory_url:
        return ""
    client = session or requests.Session()
    response = client.get(directory_url, timeout=10, allow_redirects=True)
    if int(getattr(response, "status_code", 0)) != 200:
        return ""
    html = str(getattr(response, "text", ""))
    hrefs = re.findall(r"""href\s*=\s*["']([^"']+)["']""", html, flags=re.I)
    candidates = [
        urljoin(str(getattr(response, "url", directory_url)), href)
        for href in hrefs
        if not href.startswith("#")
    ]
    if match:
        candidates = [url for url in candidates if match in url.lower()]
    return candidates[0] if candidates else ""


def probe_feed(
    feed: dict[str, Any],
    *,
    session: Any | None = None,
    conditional_headers: dict[str, str] | None = None,
) -> FeedProbeResult:
    """Validate a configured feed and return normalized RSS/Atom entries."""

    source_id = str(feed.get("source_id") or feed.get("name") or "rss_feed")
    if not feed.get("enabled", True) or feed.get("quarantined", False):
        return FeedProbeResult(
            source_id=source_id,
            status="DISABLED",
            requested_url=str(feed.get("url", "")),
            final_url=str(feed.get("url", "")),
            error=str(feed.get("quarantine_reason", "disabled")),
        )

    client = session or requests.Session()
    requested_url = str(feed.get("url", "")).strip()
    discovered_from = ""
    if not requested_url:
        discovered_from = str(feed.get("discovery_url", "")).strip()
        try:
            requested_url = discover_feed_url(feed, client)
        except requests.RequestException as exc:
            return FeedProbeResult(source_id, "HTTP_ERROR", "", "", error=str(exc), discovered_from=discovered_from)
        if not requested_url:
            return FeedProbeResult(
                source_id,
                "INVALID_FORMAT",
                "",
                "",
                error="official RSS directory did not expose a matching feed URL",
                discovered_from=discovered_from,
            )

    headers = {"Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9"}
    headers.update(conditional_headers or {})
    try:
        response = client.get(requested_url, headers=headers, timeout=10, allow_redirects=True)
    except requests.RequestException as exc:
        return FeedProbeResult(source_id, "HTTP_ERROR", requested_url, requested_url, error=str(exc), discovered_from=discovered_from)

    status_code = int(getattr(response, "status_code", 0))
    final_url = str(getattr(response, "url", requested_url))
    response_headers = getattr(response, "headers", {}) or {}
    content_type = str(response_headers.get("Content-Type", "")).lower()
    etag = str(response_headers.get("ETag", ""))
    last_modified = str(response_headers.get("Last-Modified", ""))
    if status_code == 304:
        return FeedProbeResult(
            source_id,
            "READY",
            requested_url,
            final_url,
            status_code,
            content_type,
            etag,
            last_modified,
            not_modified=True,
            discovered_from=discovered_from,
        )
    if status_code < 200 or status_code >= 300:
        return FeedProbeResult(
            source_id,
            "HTTP_ERROR",
            requested_url,
            final_url,
            status_code,
            content_type,
            etag,
            last_modified,
            error=f"HTTP {status_code}",
            discovered_from=discovered_from,
        )

    text = str(getattr(response, "text", ""))
    if any(kind in content_type for kind in HTML_CONTENT_TYPES) or _looks_like_html(text):
        return FeedProbeResult(
            source_id,
            "REDIRECTED_TO_HTML",
            requested_url,
            final_url,
            status_code,
            content_type,
            etag,
            last_modified,
            error="feed endpoint returned HTML instead of XML",
            discovered_from=discovered_from,
        )

    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        return FeedProbeResult(
            source_id,
            "INVALID_FORMAT",
            requested_url,
            final_url,
            status_code,
            content_type,
            etag,
            last_modified,
            error=f"XML parse failed: {exc}",
            discovered_from=discovered_from,
        )
    if _local_name(root.tag) not in FEED_ROOTS:
        return FeedProbeResult(
            source_id,
            "INVALID_FORMAT",
            requested_url,
            final_url,
            status_code,
            content_type,
            etag,
            last_modified,
            error=f"unsupported XML root: {_local_name(root.tag)}",
            discovered_from=discovered_from,
        )

    entries = tuple(_parse_entries(root))
    return FeedProbeResult(
        source_id,
        "READY",
        requested_url,
        final_url,
        status_code,
        content_type,
        etag,
        last_modified,
        entries,
        discovered_from=discovered_from,
    )


def _parse_entries(root: ET.Element) -> list[dict[str, Any]]:
    if _local_name(root.tag) == "feed":
        return [_parse_atom_entry(entry) for entry in root if _local_name(entry.tag) == "entry"]
    return [_parse_rss_item(item) for item in root.iter() if _local_name(item.tag) == "item"]


def _parse_rss_item(item: ET.Element) -> dict[str, Any]:
    return {
        "guid": _child_text(item, "guid"),
        "title": _child_text(item, "title"),
        "url": _child_text(item, "link"),
        "published_at": _normalize_feed_date(_child_text(item, "pubDate") or _child_text(item, "date")),
        "excerpt": _clean_excerpt(_child_text(item, "description") or _child_text(item, "summary")),
    }


def _parse_atom_entry(entry: ET.Element) -> dict[str, Any]:
    link = ""
    for child in entry:
        if _local_name(child.tag) == "link":
            link = str(child.attrib.get("href", "")).strip() or (child.text or "").strip()
            if link:
                break
    return {
        "guid": _child_text(entry, "id"),
        "title": _child_text(entry, "title"),
        "url": link,
        "published_at": _normalize_feed_date(_child_text(entry, "published") or _child_text(entry, "updated")),
        "excerpt": _clean_excerpt(_child_text(entry, "summary") or _child_text(entry, "content")),
    }


def _child_text(element: ET.Element, name: str) -> str:
    for child in element:
        if _local_name(child.tag) == name.lower():
            return "".join(child.itertext()).strip()
    return ""


def _normalize_feed_date(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = parsedate_to_datetime(value)
        return parsed.isoformat()
    except (TypeError, ValueError):
        return value


def _clean_excerpt(value: str, max_length: int = 600) -> str:
    plain = re.sub(r"<[^>]+>", " ", unescape(value or ""))
    return re.sub(r"\s+", " ", plain).strip()[:max_length]


def _looks_like_html(text: str) -> bool:
    prefix = text.lstrip().lower()[:500]
    return prefix.startswith("<!doctype html") or "<html" in prefix


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()
