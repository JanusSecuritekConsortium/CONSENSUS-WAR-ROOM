import tempfile
from pathlib import Path

from core.data_sources.cache import DataSourceCache
from core.data_sources.enrichment import build_aeternum_data_enrichment
from core.data_sources.registry import DataSourceRegistry


def test_aeternum_reports_unavailable_without_cached_items() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        registry = DataSourceRegistry(cache=DataSourceCache(Path(tmp)))
        packet = build_aeternum_data_enrichment("query", registry=registry)
        assert packet["status"] == "DATA_UNAVAILABLE"
        assert packet["mode"] == "cache_only"


if __name__ == "__main__":
    test_aeternum_reports_unavailable_without_cached_items()
    print("test_aeternum_data_enrichment PASS")
