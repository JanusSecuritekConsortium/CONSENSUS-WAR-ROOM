from __future__ import annotations

from core.data_sources import source_config
from core.intelligence import world_events


def test_feeds_switch_in_the_env_file_stops_outside_downloads(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("BELLATOR_FEEDS_ENABLED=0\n", encoding="utf-8")
    monkeypatch.setattr(source_config, "DOTENV_PATH", env_file)
    monkeypatch.delenv("CONSENSUS_DATA_ENV_FILE", raising=False)
    monkeypatch.delenv("BELLATOR_FEEDS_ENABLED", raising=False)
    monkeypatch.setenv("BELLATOR_GDELT_EVENTS", "1")

    assert source_config.feeds_switch() == "0"
    assert world_events.gdelt_enabled() is False


def test_the_process_environment_wins_over_the_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("BELLATOR_FEEDS_ENABLED=0\n", encoding="utf-8")
    monkeypatch.setattr(source_config, "DOTENV_PATH", env_file)
    monkeypatch.delenv("CONSENSUS_DATA_ENV_FILE", raising=False)
    monkeypatch.setenv("BELLATOR_FEEDS_ENABLED", "1")

    assert source_config.feeds_switch() == "1"


def test_feed_keys_in_the_env_file_reach_the_feed_clients(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("NASA_FIRMS_MAP_KEY=example-key\n", encoding="utf-8")
    monkeypatch.setattr(source_config, "DOTENV_PATH", env_file)
    monkeypatch.delenv("CONSENSUS_DATA_ENV_FILE", raising=False)
    monkeypatch.delenv("NASA_FIRMS_MAP_KEY", raising=False)

    assert source_config.env_setting("NASA_FIRMS_MAP_KEY") == "example-key"


def test_the_news_refresh_tool_downloads_nothing_when_feeds_are_off(tmp_path, monkeypatch, capsys):
    import tools.poll_rss_feeds as tool

    monkeypatch.setenv("BELLATOR_FEEDS_ENABLED", "0")
    monkeypatch.setattr(tool, "RssIntelligenceBackbone", lambda: (_ for _ in ()).throw(AssertionError("polled")))
    monkeypatch.setattr("sys.argv", ["poll_rss_feeds.py"])

    assert tool.main() == 0
    assert "DISABLED" in capsys.readouterr().out
