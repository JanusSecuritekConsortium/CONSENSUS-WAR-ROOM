from integrations.rss.probe import probe_feed


class Session:
    def __init__(self) -> None:
        self.headers = {}

    def get(self, _url, **kwargs):
        self.headers = kwargs["headers"]
        return type(
            "Response",
            (),
            {"text": "", "status_code": 304, "url": "https://example.test/feed", "headers": {"ETag": "next"}},
        )()


def test_probe_sends_etag_and_last_modified_headers() -> None:
    session = Session()
    result = probe_feed(
        {"source_id": "test", "url": "https://example.test/feed", "enabled": True},
        session=session,
        conditional_headers={"If-None-Match": "old", "If-Modified-Since": "yesterday"},
    )
    assert result.status == "READY"
    assert result.not_modified is True
    assert session.headers["If-None-Match"] == "old"
    assert session.headers["If-Modified-Since"] == "yesterday"


if __name__ == "__main__":
    test_probe_sends_etag_and_last_modified_headers()
    print("test_rss_conditional_headers PASS")
