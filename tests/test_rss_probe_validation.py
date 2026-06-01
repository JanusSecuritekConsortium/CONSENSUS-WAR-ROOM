from integrations.rss.probe import probe_feed


class Response:
    def __init__(self, text: str, *, content_type: str = "application/rss+xml", status: int = 200, url: str = "https://example.test/feed") -> None:
        self.text = text
        self.status_code = status
        self.url = url
        self.headers = {"Content-Type": content_type}


class Session:
    def __init__(self, response: Response) -> None:
        self.response = response

    def get(self, *_args, **_kwargs):
        return self.response


def test_probe_accepts_rss_and_rejects_html_redirects() -> None:
    feed = {"source_id": "test", "url": "https://example.test/feed", "enabled": True}
    valid = probe_feed(
        feed,
        session=Session(Response("<rss><channel><item><title>Signal</title><link>https://example.test/a</link><pubDate>Sun, 31 May 2026 09:00:00 GMT</pubDate></item></channel></rss>")),
    )
    assert valid.status == "READY"
    assert valid.entries[0]["title"] == "Signal"
    assert valid.entries[0]["published_at"].startswith("2026-05-31T09:00:00")
    html = probe_feed(feed, session=Session(Response("<html><body>landing page</body></html>", content_type="text/html")))
    assert html.status == "REDIRECTED_TO_HTML"


if __name__ == "__main__":
    test_probe_accepts_rss_and_rejects_html_redirects()
    print("test_rss_probe_validation PASS")
