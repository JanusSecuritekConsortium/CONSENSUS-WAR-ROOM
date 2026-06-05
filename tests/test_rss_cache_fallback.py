import tempfile
from pathlib import Path

from core.data_sources.rss_backbone import RssIntelligenceBackbone
from core.data_sources.rss_store import RssIntelligenceStore
from integrations.rss.probe import FeedProbeResult


def test_live_poll_failure_returns_marked_cache_fallback() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = RssIntelligenceStore(Path(tmp) / "intelligence.db")
        feed = {"source_id": "source", "name": "Source", "tier": 1, "url": "https://example.test/feed", "enabled": True, "taxonomy_tags": ["ENERGY"]}
        store.sync_sources([feed])
        store.upsert_items("source", [{"guid": "1", "title": "Energy alert", "url": "https://example.test/1", "excerpt": "Energy signal"}], ["ENERGY"])
        failure = lambda *_args, **_kwargs: FeedProbeResult("source", "HTTP_ERROR", feed["url"], feed["url"], 500, error="HTTP 500")
        packet = RssIntelligenceBackbone({"feeds": [feed]}, store=store, probe_fn=failure).build_packet("energy", live=True)
        assert packet["mode"] == "CACHE_FALLBACK"
        assert packet["item_count"] == 1


if __name__ == "__main__":
    test_live_poll_failure_returns_marked_cache_fallback()
    print("test_rss_cache_fallback PASS")
