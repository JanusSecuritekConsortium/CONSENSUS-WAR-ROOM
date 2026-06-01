import tempfile
from datetime import datetime, timezone
from pathlib import Path

from core.data_sources.rss_backbone import RssIntelligenceBackbone
from core.data_sources.rss_store import RssIntelligenceStore, parse_timestamp
from integrations.rss.probe import FeedProbeResult


NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)


def test_failure_backoff_doubles_per_source() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = RssIntelligenceStore(Path(tmp) / "intelligence.db")
        config = {
            "poll_interval_seconds": 1200,
            "backoff_base_seconds": 300,
            "backoff_max_seconds": 7200,
            "feeds": [{"source_id": "broken", "name": "Broken", "url": "https://example.test/feed", "tier": 1, "enabled": True}],
        }
        failure = lambda *_args, **_kwargs: FeedProbeResult("broken", "HTTP_ERROR", "https://example.test/feed", "https://example.test/feed", 503, error="HTTP 503")
        backbone = RssIntelligenceBackbone(config, store=store, now_fn=lambda: NOW, probe_fn=failure)
        backbone.poll(force=True)
        first = parse_timestamp(store.source("broken")["next_poll_at"])
        backbone.poll(force=True)
        second = parse_timestamp(store.source("broken")["next_poll_at"])
        assert int((first - NOW).total_seconds()) == 300
        assert int((second - NOW).total_seconds()) == 600


if __name__ == "__main__":
    test_failure_backoff_doubles_per_source()
    print("test_rss_failure_backoff PASS")
