import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from integrations.gdelt.client import GdeltAdapter


class Response:
    def raise_for_status(self): return None
    def json(self): return {"articles": [{"title": "Example", "url": "https://example.test/a", "seendate": "2026-01-01"}]}


class Session:
    def get(self, *_args, **_kwargs): return Response()


def test_gdelt_mock_fetch_normalizes_article() -> None:
    adapter = GdeltAdapter({"enabled": True, "base_url": "https://example.test"}, Session())
    result = adapter.fetch("query")
    items = adapter.normalize(result["items"])
    assert result["status"] == "READY"
    assert items[0].source == "gdelt"
    assert items[0].title == "Example"


if __name__ == "__main__":
    test_gdelt_mock_fetch_normalizes_article()
    print("test_gdelt_adapter_mock PASS")
