import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from integrations.ground_news.client import GroundNewsAdapter


def test_ground_news_never_scrapes_without_official_access() -> None:
    adapter = GroundNewsAdapter({"enabled": True, "scraping_allowed": True})
    health = adapter.health_check()
    assert health["status"] == "OFFICIAL_ACCESS_REQUIRED"
    assert health["scraping_allowed"] is False
    assert adapter.fetch()["items"] == []


if __name__ == "__main__":
    test_ground_news_never_scrapes_without_official_access()
    print("test_ground_news_disabled_without_official_access PASS")
