import tempfile
from pathlib import Path

from core.data_sources.rss_store import RssIntelligenceStore


def test_fts_retrieval_filters_taxonomy_and_omits_unrecorded_sentiment() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = RssIntelligenceStore(Path(tmp) / "intelligence.db")
        store.sync_sources([{"source_id": "source", "name": "Official Source", "tier": 1, "enabled": True, "taxonomy_tags": ["SECURITY"]}])
        store.upsert_items(
            "source",
            [{"guid": "1", "title": "Cyber advisory issued", "url": "https://example.test/1", "excerpt": "Critical infrastructure guidance"}],
            ["SECURITY"],
        )
        items = store.search("cyber", taxonomy_tags=["SECURITY"])
        assert len(items) == 1
        assert items[0]["source"] == "Official Source"
        assert "sentiment_confidence" not in items[0]
        assert store.search("cyber", taxonomy_tags=["ENERGY"]) == []


if __name__ == "__main__":
    test_fts_retrieval_filters_taxonomy_and_omits_unrecorded_sentiment()
    print("test_rss_fts_retrieval PASS")
