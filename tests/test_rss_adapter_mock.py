import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from integrations.rss.client import RssAdapter


class Response:
    text = "<rss><channel><item><title>Example</title><link>https://example.test/rss</link><description>Summary</description></item></channel></rss>"
    status_code = 200
    url = "https://example.test/feed"
    headers = {"Content-Type": "application/rss+xml"}
    def raise_for_status(self): return None


class Session:
    def get(self, *_args, **_kwargs): return Response()


def test_rss_mock_fetch_normalizes_feed() -> None:
    adapter = RssAdapter({"enabled": True, "feeds": [{"url": "https://example.test/feed", "topics": ["world"]}]}, Session())
    items = adapter.normalize(adapter.fetch()["items"])
    assert items[0].title == "Example"
    assert items[0].topics == ["world"]


if __name__ == "__main__":
    test_rss_mock_fetch_normalizes_feed()
    print("test_rss_adapter_mock PASS")
