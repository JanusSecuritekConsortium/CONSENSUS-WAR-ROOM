from core.data_sources.source_config import redacted_data_source_config


def test_secrets_are_redacted_recursively() -> None:
    payload = {"sources": {"acled": {"token": "secret", "email": "operator@example.test"}, "search": {"api_key": "key"}}}
    redacted = redacted_data_source_config(payload)
    assert redacted["sources"]["acled"]["token"] == "***REDACTED***"
    assert redacted["sources"]["acled"]["email"] == "***REDACTED***"
    assert redacted["sources"]["search"]["api_key"] == "***REDACTED***"
    assert "secret" not in str(redacted)


if __name__ == "__main__":
    test_secrets_are_redacted_recursively()
    print("test_data_source_config_redaction PASS")
