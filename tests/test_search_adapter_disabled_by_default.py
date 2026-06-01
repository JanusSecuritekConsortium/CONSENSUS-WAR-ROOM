import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from integrations.search.client import SearchAdapter


def test_search_is_disabled_by_default() -> None:
    adapter = SearchAdapter({})
    assert adapter.enabled is False
    assert adapter.health_check()["status"] == "DISABLED"


if __name__ == "__main__":
    test_search_is_disabled_by_default()
    print("test_search_adapter_disabled_by_default PASS")
