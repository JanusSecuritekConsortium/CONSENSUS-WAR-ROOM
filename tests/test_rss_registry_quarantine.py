from core.data_sources.source_config import load_data_source_config


def test_reuters_and_ap_are_quarantined_pending_valid_xml_endpoints() -> None:
    feeds = load_data_source_config()["sources"]["rss"]["feeds"]
    by_id = {feed["source_id"]: feed for feed in feeds}
    for source_id in ("reuters_world", "ap_top_news"):
        assert by_id[source_id]["quarantined"] is True
        assert by_id[source_id]["enabled"] is False
    assert by_id["bbc_world"]["enabled"] is True
    for source_id in ("nato_news", "ecb_press", "eu_council_press"):
        assert by_id[source_id]["discovery_url"].startswith("https://")


if __name__ == "__main__":
    test_reuters_and_ap_are_quarantined_pending_valid_xml_endpoints()
    print("test_rss_registry_quarantine PASS")
