"""The phone page: sign-in with operator profiles, submitting proposals, and what a phone may see."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core import identity
from core.identity import store
from integrations.mcp import tribunal_job as job
from integrations.phone import server

PIN = "2468-fixture"  # a test value, not anyone's real PIN


@pytest.fixture
def users(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / "users.json"
    monkeypatch.setattr(store, "USERS_PATH", path)
    identity.sign_in(None)
    yield path
    identity.sign_in(None)


@pytest.fixture
def phone(users: Path, tmp_path: Path):
    from fastapi.testclient import TestClient

    identity.add_operator("Owner", PIN)
    identity.add_operator("Guest", "guest-pin-1")
    jobs_dir = tmp_path / "jobs"
    launched: list[str] = []

    def start(question, *, jobs_dir, submitted_by):
        return job.start(question, jobs_dir=jobs_dir, launch=launched.append, check_memory=lambda: None,
                         free_local_ai=lambda: [], submitted_by=submitted_by)
    clock = [1000.0]
    sessions = server.Sessions(clock=lambda: clock[0])
    app = server.create_app(jobs_dir=jobs_dir, start=start, sleep=lambda seconds: None, sessions=sessions)
    return TestClient(app), jobs_dir, launched, clock


def _sign_in(client, name="Owner", pin=PIN):
    return client.post("/phone/v1/login", json={"name": name, "pin": pin})


def test_no_profiles_no_phone_page(users: Path, tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="manage_users"):
        server.create_app(jobs_dir=tmp_path)


def test_page_loads_without_sign_in_but_nothing_else_does(phone) -> None:
    client, _, launched, _ = phone
    page = client.get("/")
    assert page.status_code == 200 and "CONSENSUS" in page.text
    assert page.headers["x-frame-options"] == "DENY" and "frame-ancestors 'none'" in page.headers["content-security-policy"]
    assert client.get("/phone/v1/operators").json() == {"operators": ["Owner", "Guest"]}
    assert client.get("/phone/v1/me").status_code == 401
    assert client.get("/phone/v1/proposals").status_code == 401
    assert client.post("/phone/v1/proposals", json={"question": "Should we?"}).status_code == 401
    client.cookies.set(server.COOKIE, "made-up-token")
    assert client.get("/phone/v1/me").status_code == 401
    assert launched == []
    assert client.get("/docs").status_code == 404 and client.get("/openapi.json").status_code == 404


def test_sign_in_needs_the_right_pin_and_sets_a_protected_cookie(phone) -> None:
    client, _, _, _ = phone
    wrong = _sign_in(client, pin="wrong-pin")
    assert wrong.status_code == 401 and server.COOKIE not in wrong.cookies
    assert _sign_in(client, name="Nobody").status_code == 401
    good = _sign_in(client)
    assert good.status_code == 200 and good.json() == {"name": "Owner"}
    cookie = good.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert PIN not in good.text and PIN not in cookie
    assert client.get("/phone/v1/me").json() == {"name": "Owner"}


def test_wrong_pins_from_the_phone_use_the_same_growing_wait(phone) -> None:
    client, _, _, _ = phone
    for _ in range(3):
        assert _sign_in(client, pin="wrong-pin").status_code == 401
    blocked = _sign_in(client)  # right PIN, but the profile is waiting
    assert blocked.status_code == 401 and "Wait" in blocked.json()["detail"]


def test_a_proposal_becomes_a_ticket_with_the_operators_name(phone) -> None:
    client, jobs_dir, launched, _ = phone
    _sign_in(client, "Guest", "guest-pin-1")
    response = client.post("/phone/v1/proposals", json={"question": "Should we adopt the new backup plan?"})
    assert response.status_code == 202
    ticket = response.json()["ticket"]
    assert launched == [ticket]
    record = json.loads((jobs_dir / f"{ticket}.json").read_text())
    assert record["submitted_by"] == "Guest" and "guest" not in record

    # A second proposal while one is running is refused, not queued behind it.
    assert client.post("/phone/v1/proposals", json={"question": "Another one?"}).status_code == 409
    assert client.post("/phone/v1/proposals", json={"question": ""}).status_code == 422
    assert client.post("/phone/v1/proposals", json={"question": "x" * 4001}).status_code == 422


def test_the_worker_records_the_operator_on_the_decision(phone) -> None:
    client, jobs_dir, _, _ = phone
    _sign_in(client)
    ticket = client.post("/phone/v1/proposals", json={"question": "Should we adopt the new backup plan?"}).json()["ticket"]
    seen: list[str | None] = []

    class Result:
        pass

    def deliberate(query):
        seen.append(identity.current_operator_name())
        raise RuntimeError("stop after the sign-in check")
    job.run(ticket, jobs_dir=jobs_dir, deliberate=deliberate)
    assert seen == ["Owner"]


def test_the_list_shows_phone_tickets_only_and_a_summary_only(phone) -> None:
    client, jobs_dir, _, _ = phone
    jobs_dir.mkdir(parents=True, exist_ok=True)
    base = {"status": "finished", "requested_at": "2026-11-12T10:00:00+00:00", "finished_at": "2026-11-12T10:30:00+00:00"}
    result = {"verdict": "APPROVE", "confidence": 0.8, "reason": "Sound plan.", "next_steps": ["Do it"],
              "votes": {"RATIONALIS": {"vote": "APPROVE", "reasoning": "raw model text"}}}
    (jobs_dir / "aaaaaaaaaaaa.json").write_text(json.dumps({**base, "ticket": "aaaaaaaaaaaa", "query": "Phone question",
                                                             "submitted_by": "Owner", "result": result}))
    (jobs_dir / "bbbbbbbbbbbb.json").write_text(json.dumps({**base, "ticket": "bbbbbbbbbbbb", "query": "Owner desktop question"}))
    (jobs_dir / "cccccccccccc.json").write_text(json.dumps({**base, "ticket": "cccccccccccc", "query": "Guest system question",
                                                             "guest": True, "submitted_by": "spoof"}))
    _sign_in(client, "Guest", "guest-pin-1")
    listed = client.get("/phone/v1/proposals").json()["proposals"]
    assert [item["question"] for item in listed] == ["Phone question"]
    assert listed[0]["submitted_by"] == "Owner"  # one shared record, with names on it
    assert listed[0]["result"] == {"verdict": "APPROVE", "confidence": 0.8, "reason": "Sound plan.", "next_steps": ["Do it"]}
    assert "raw model text" not in json.dumps(listed)


def test_sign_out_expiry_and_removed_profiles_end_access(phone) -> None:
    client, _, _, clock = phone
    _sign_in(client)
    assert client.post("/phone/v1/logout").json() == {"signed_out": True}
    assert client.get("/phone/v1/me").status_code == 401

    _sign_in(client)
    clock[0] += server.SESSION_SECONDS + 1
    assert client.get("/phone/v1/me").status_code == 401

    _sign_in(client, "Guest", "guest-pin-1")
    assert client.get("/phone/v1/me").status_code == 200
    identity.remove_operator("Guest")
    assert client.get("/phone/v1/me").status_code == 401


def test_host_choice_never_opens_to_every_network() -> None:
    assert server.resolve_host("") == "127.0.0.1"
    assert server.resolve_host("100.64.0.7") == "100.64.0.7"
    assert server.resolve_host("tailscale", find_tailscale=lambda: "100.101.102.103") == "100.101.102.103"
    with pytest.raises(RuntimeError, match="Tailscale"):
        server.resolve_host("tailscale", find_tailscale=lambda: "")
    for everywhere in ("0.0.0.0", "::"):
        with pytest.raises(RuntimeError):
            server.resolve_host(everywhere)

    class Done:
        def __init__(self, code, out):
            self.returncode, self.stdout = code, out
    assert server.tailscale_address(run=lambda *a, **k: Done(0, "100.101.102.103\n")) == "100.101.102.103"
    assert server.tailscale_address(run=lambda *a, **k: Done(1, "")) == ""
    assert server.tailscale_address(run=lambda *a, **k: Done(0, "192.168.1.5\n")) == ""

    def missing(*a, **k):
        raise FileNotFoundError
    assert server.tailscale_address(run=missing) == ""
