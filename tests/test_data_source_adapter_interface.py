from core.data_sources.models import DataSourceAdapter
from core.data_sources.registry import build_data_source_registry


def test_all_registered_sources_implement_adapter_interface() -> None:
    for adapter in build_data_source_registry().list_adapters():
        assert isinstance(adapter, DataSourceAdapter)
        assert adapter.source_id
        assert callable(adapter.health_check)
        assert callable(adapter.fetch)
        assert callable(adapter.normalize)


if __name__ == "__main__":
    test_all_registered_sources_implement_adapter_interface()
    print("test_data_source_adapter_interface PASS")
