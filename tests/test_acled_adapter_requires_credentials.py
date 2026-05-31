import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from integrations.acled.client import AcledAdapter


class Response:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): return None
    def json(self): return self.payload


class Session:
    def post(self, *_args, **_kwargs): return Response({"access_token": "oauth-token"})
    def get(self, *_args, **kwargs):
        assert kwargs["headers"]["Authorization"] == "Bearer oauth-token"
        return Response({"data": []})


def test_acled_requires_token_when_enabled() -> None:
    adapter = AcledAdapter({"enabled": True, "base_url": "https://example.test"})
    assert adapter.health_check()["status"] == "MISSING_CREDENTIALS"
    assert adapter.fetch()["items"] == []


def test_acled_accepts_oauth_email_password() -> None:
    adapter = AcledAdapter(
        {"enabled": True, "base_url": "https://example.test", "email": "operator@example.test", "password": "secret"},
        Session(),
    )
    assert adapter.fetch()["status"] == "READY"


if __name__ == "__main__":
    test_acled_requires_token_when_enabled()
    test_acled_accepts_oauth_email_password()
    print("test_acled_adapter_requires_credentials PASS")
