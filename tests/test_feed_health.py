from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.intelligence.feed_health import build_feed_health_report, print_env_template
from config.version import SYSTEM_VERSION


FEED_ENV_KEYS = (
    "ACLED_EMAIL",
    "ACLED_PASSWORD",
    "ACLED_ACCESS_TOKEN",
    "ACLED_API_KEY",
    "ACLED_KEY",
    "ACLED_ENABLE_LEGACY_KEY",
    "NASA_FIRMS_MAP_KEY",
    "FIRMS_MAP_KEY",
    "CLOUDFLARE_API_TOKEN",
    "CLOUDFLARE_RADAR_TOKEN",
    "URLHAUS_ENABLED",
    "URLHAUS_AUTH_KEY",
)


def _without_feed_env():
    previous = {key: os.environ.get(key) for key in FEED_ENV_KEYS}
    for key in FEED_ENV_KEYS:
        os.environ.pop(key, None)
    return previous


def _restore_env(previous) -> None:
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def test_no_credentials_returns_unusable_without_crash() -> None:
    previous = _without_feed_env()
    try:
        report = build_feed_health_report()

        assert report["label"] == "BELLATOR FEED HEALTH"
        assert report["version"] == SYSTEM_VERSION
        assert len(report["sources"]) == 4
        for source in report["sources"]:
            assert source["credentials_present"] is False
            assert source["live_check_attempted"] is False
            assert source["usable"] is False
            assert source["result_status"] == "not_attempted"
    finally:
        _restore_env(previous)


def test_env_template_contains_expected_keys() -> None:
    template = print_env_template()

    assert '$env:ACLED_ACCESS_TOKEN=""' in template
    assert '$env:ACLED_EMAIL=""' in template
    assert '$env:ACLED_PASSWORD=""' in template
    assert '$env:ACLED_API_KEY=""' not in template
    assert '$env:NASA_FIRMS_MAP_KEY=""' in template
    assert '$env:CLOUDFLARE_API_TOKEN=""' in template
    assert '$env:URLHAUS_ENABLED="0"' in template
    assert '$env:URLHAUS_AUTH_KEY=""' in template


def test_health_output_includes_cache_paths() -> None:
    previous = _without_feed_env()
    try:
        report = build_feed_health_report(attempt_live=False)

        for source in report["sources"]:
            path = source["cache_file_path"]
            assert "G:\\CONSENSUS_SYSTEM\\_ARBITER\\cache\\feeds" in path
            assert path.endswith(f"{source['source']}.json")
    finally:
        _restore_env(previous)


def test_urlhaus_does_not_attempt_live_without_opt_in() -> None:
    previous = _without_feed_env()
    try:
        os.environ["URLHAUS_AUTH_KEY"] = "dummy-key-alone-must-not-enable-live"

        report = build_feed_health_report()
        urlhaus = next(source for source in report["sources"] if source["source"] == "abuse_ch_urlhaus")

        assert urlhaus["credentials_present"] is False
        assert urlhaus["live_check_attempted"] is False
        assert urlhaus["usable"] is False
        assert "URLHAUS_ENABLED=1" in urlhaus["diagnostic"]
    finally:
        _restore_env(previous)


def test_acled_email_password_counts_as_credentials() -> None:
    previous = _without_feed_env()
    try:
        os.environ["ACLED_EMAIL"] = "user@example.invalid"
        os.environ["ACLED_PASSWORD"] = "not-a-real-password"

        report = build_feed_health_report(attempt_live=False)
        acled = next(source for source in report["sources"] if source["source"] == "acled")

        assert acled["credentials_present"] is True
        assert acled["live_check_attempted"] is False
        assert "ACLED_ACCESS_TOKEN" in acled["required_environment"]
        assert "ACLED_EMAIL + ACLED_PASSWORD" in acled["required_environment"]
    finally:
        _restore_env(previous)


if __name__ == "__main__":
    test_no_credentials_returns_unusable_without_crash()
    test_env_template_contains_expected_keys()
    test_health_output_includes_cache_paths()
    test_urlhaus_does_not_attempt_live_without_opt_in()
    test_acled_email_password_counts_as_credentials()
    print("test_feed_health PASS")
