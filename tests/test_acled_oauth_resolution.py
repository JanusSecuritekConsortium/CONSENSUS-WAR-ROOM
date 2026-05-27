from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.feeds import acled_client


ACLED_ENV_KEYS = (
    "ACLED_ACCESS_TOKEN",
    "ACLED_EMAIL",
    "ACLED_PASSWORD",
    "ACLED_API_KEY",
    "ACLED_KEY",
    "ACLED_ENABLE_LEGACY_KEY",
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def _clear_acled_env():
    previous = {key: os.environ.get(key) for key in ACLED_ENV_KEYS}
    for key in ACLED_ENV_KEYS:
        os.environ.pop(key, None)
    return previous


def _restore_env(previous) -> None:
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def test_acled_oauth_password_flow_fetches_with_bearer_token() -> None:
    previous_env = _clear_acled_env()
    original_urlopen = acled_client.urlopen
    calls = []
    try:
        os.environ["ACLED_EMAIL"] = "user@example.invalid"
        os.environ["ACLED_PASSWORD"] = "not-a-real-password"

        def fake_urlopen(request, timeout=8):
            calls.append(request)
            if request.full_url == acled_client.DEFAULT_TOKEN_URL:
                return FakeResponse({"access_token": "token-from-oauth", "expires_in": 86400})
            return FakeResponse(
                {
                    "data": [
                        {
                            "event_type": "Protests",
                            "country": "Exampleland",
                            "event_date": "2026-05-19",
                        }
                    ]
                }
            )

        acled_client.urlopen = fake_urlopen

        result = acled_client.fetch_acled_events(days=1, limit=1)

        assert result["ok"] is True
        assert result["status"] == "ok"
        assert result["diagnostics"]["auth_mode"] == "oauth_password"
        assert result["diagnostics"]["oauth_success"] is True
        assert len(calls) == 2
        assert calls[1].headers["Authorization"] == "Bearer token-from-oauth"
        assert "key=" not in calls[1].full_url
    finally:
        acled_client.urlopen = original_urlopen
        _restore_env(previous_env)


def test_acled_access_token_has_priority_over_password_flow() -> None:
    previous_env = _clear_acled_env()
    try:
        os.environ["ACLED_ACCESS_TOKEN"] = "existing-token"
        os.environ["ACLED_EMAIL"] = "user@example.invalid"
        os.environ["ACLED_PASSWORD"] = "not-a-real-password"

        auth = acled_client.resolve_acled_auth()

        assert auth["ok"] is True
        assert auth["auth_mode"] == "access_token"
        assert auth["headers"]["Authorization"] == "Bearer existing-token"
    finally:
        _restore_env(previous_env)


def test_acled_missing_credentials_uses_new_diagnostic() -> None:
    previous_env = _clear_acled_env()
    try:
        result = acled_client.fetch_acled_events()

        assert result["ok"] is False
        assert result["status"] == "missing_credentials"
        assert result["diagnostics"]["missing_credentials"] is True
        assert "ACLED_ACCESS_TOKEN" in result["diagnostics"]["requires"]
        assert "ACLED_EMAIL + ACLED_PASSWORD" in result["diagnostics"]["requires"]
    finally:
        _restore_env(previous_env)


if __name__ == "__main__":
    test_acled_oauth_password_flow_fetches_with_bearer_token()
    test_acled_access_token_has_priority_over_password_flow()
    test_acled_missing_credentials_uses_new_diagnostic()
    print("test_acled_oauth_resolution PASS")
