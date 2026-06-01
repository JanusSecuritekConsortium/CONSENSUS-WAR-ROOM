from integrations.rss.probe import probe_feed


class Session:
    def get(self, url, **_kwargs):
        if url == "https://example.test/rss-directory":
            return type(
                "DirectoryResponse",
                (),
                {
                    "status_code": 200,
                    "url": url,
                    "text": '<html><a href="/feeds/press.xml">Press releases</a></html>',
                },
            )()
        return type(
            "FeedResponse",
            (),
            {
                "status_code": 200,
                "url": url,
                "headers": {"Content-Type": "application/rss+xml"},
                "text": "<rss><channel><item><title>Official release</title></item></channel></rss>",
            },
        )()


def test_probe_discovers_feed_from_official_directory() -> None:
    result = probe_feed(
        {
            "source_id": "official",
            "enabled": True,
            "url": "",
            "discovery_url": "https://example.test/rss-directory",
            "discovery_match": "press.xml",
        },
        session=Session(),
    )
    assert result.status == "READY"
    assert result.final_url == "https://example.test/feeds/press.xml"
    assert result.discovered_from == "https://example.test/rss-directory"


if __name__ == "__main__":
    test_probe_discovers_feed_from_official_directory()
    print("test_rss_official_directory_discovery PASS")
