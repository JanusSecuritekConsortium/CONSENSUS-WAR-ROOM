import tempfile
from pathlib import Path

from core.data_sources.cache import DataSourceCache
from core.data_sources.enrichment import build_bellator_data_enrichment
from core.data_sources.registry import DataSourceRegistry


def test_bellator_reports_unavailable_without_cached_items() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        registry = DataSourceRegistry(cache=DataSourceCache(Path(tmp)))
        packet = build_bellator_data_enrichment("query", registry=registry)
        assert packet["status"] == "DATA_UNAVAILABLE"
        assert "Do not invent" in packet["anti_fabrication_instruction"]


if __name__ == "__main__":
    test_bellator_reports_unavailable_without_cached_items()
    print("test_bellator_data_enrichment PASS")
