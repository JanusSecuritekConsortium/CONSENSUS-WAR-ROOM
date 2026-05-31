import tempfile
from pathlib import Path

from core.data_sources.cache import DataSourceCache


def test_cache_reports_stale_when_ttl_elapsed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cache = DataSourceCache(Path(tmp))
        cache.write("gdelt", "q", [], "2000-01-01T00:00:00+00:00")
        assert cache.read("gdelt", "q", ttl_seconds=1)["freshness"] == "stale"


if __name__ == "__main__":
    test_cache_reports_stale_when_ttl_elapsed()
    print("test_data_cache_ttl PASS")
