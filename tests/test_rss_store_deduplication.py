import tempfile
from pathlib import Path

from core.data_sources.rss_store import RssIntelligenceStore


def test_store_deduplicates_guid_canonical_url_and_content_hash() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = RssIntelligenceStore(Path(tmp) / "intelligence.db")
        store.sync_sources([{"source_id": "bbc", "name": "BBC", "tier": 2, "enabled": True, "taxonomy_tags": ["GEOPOLITICS"]}])
        base = {"guid": "g-1", "title": "Policy update", "url": "https://example.test/a?utm_source=x", "excerpt": "Brief"}
        assert store.upsert_items("bbc", [base], ["GEOPOLITICS"])["inserted"] == 1
        assert store.upsert_items("bbc", [{**base, "url": "https://example.test/changed"}], ["GEOPOLITICS"])["deduplicated"] == 1
        assert store.upsert_items("bbc", [{**base, "guid": "g-2", "url": "https://example.test/a"}], ["GEOPOLITICS"])["deduplicated"] == 1
        assert store.status()["item_count"] == 1


if __name__ == "__main__":
    test_store_deduplicates_guid_canonical_url_and_content_hash()
    print("test_rss_store_deduplication PASS")
