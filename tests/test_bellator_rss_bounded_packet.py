import tempfile
from pathlib import Path

from core.data_sources.rss_backbone import RssIntelligenceBackbone
from core.data_sources.rss_store import RssIntelligenceStore


def test_bellator_packet_is_cited_and_bounded_to_twelve_items() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = RssIntelligenceStore(Path(tmp) / "intelligence.db")
        feed = {"source_id": "bbc", "name": "BBC World", "tier": 2, "enabled": True, "taxonomy_tags": ["GEOPOLITICS"]}
        backbone = RssIntelligenceBackbone({"feeds": [feed]}, store=store)
        store.upsert_items(
            "bbc",
            [
                {"guid": str(index), "title": f"Alliance update {index}", "url": f"https://example.test/{index}", "excerpt": "Alliance policy"}
                for index in range(20)
            ],
            ["GEOPOLITICS"],
        )
        packet = backbone.build_packet("alliance", taxonomy_tags=["GEOPOLITICS"], limit=50)
        assert packet["item_count"] == 12
        assert len(packet["citations"]) == 12
        assert all({"title", "source", "url", "published_at", "fetched_at", "freshness_seconds", "taxonomy_tags", "excerpt"} <= set(item) for item in packet["items"])


if __name__ == "__main__":
    test_bellator_packet_is_cited_and_bounded_to_twelve_items()
    print("test_bellator_rss_bounded_packet PASS")
