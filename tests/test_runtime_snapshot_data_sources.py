from core.data_sources.health import build_data_sources_status


def test_data_sources_snapshot_has_redacted_status() -> None:
    status = build_data_sources_status(attempt_live=False)
    assert "enabled_sources" in status
    assert "source_health" in status
    assert "redacted_config" in status
    assert status["mode"] == "cache_only"


if __name__ == "__main__":
    test_data_sources_snapshot_has_redacted_status()
    print("test_runtime_snapshot_data_sources PASS")
