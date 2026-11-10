"""The guest door: password, daily limit, privacy of the owner's tickets, and guest deliberations."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from threading import Event
from datetime import datetime, timedelta, timezone

import pytest

from integrations.guest import server
from integrations.mcp import tribunal_job as job

PASSWORD = "p" * 40


@pytest.fixture
def door(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    launched = []
    monkeypatch.setattr(server, "daily_limit", lambda: 2)

    def start(question, *, jobs_dir, guest, guest_limit):
        assert guest is True
        return job.start(question, jobs_dir=jobs_dir, launch=launched.append, check_memory=lambda: None,
                         free_local_ai=lambda: pytest.fail("a guest never unloads the owner's models"),
                         guest=True, guest_limit=guest_limit)
    app = server.create_app(password=PASSWORD, jobs_dir=tmp_path, start=start, sleep=lambda seconds: None)
    client = TestClient(app)
    client.headers["Authorization"] = f"Bearer {PASSWORD}"
    return client, tmp_path, launched


def test_no_password_no_door():
    with pytest.raises(RuntimeError, match="--new-password"):
        server.create_app(password="short")


def test_every_route_needs_the_password(door):
    client, _, launched = door
    for headers in ({"Authorization": "Bearer wrong"}, {"Authorization": ""}, {"Authorization": PASSWORD}):
        assert client.get("/guest/v1/health", headers=headers).status_code == 401
        assert client.post("/guest/v1/deliberations", json={"question": "Q?"}, headers=headers).status_code == 401
        assert client.get("/guest/v1/deliberations/abc123", headers=headers).status_code == 401
    assert launched == []
    assert client.get("/docs").status_code == 404 and client.get("/openapi.json").status_code == 404


def test_a_guest_question_gets_a_ticket_and_later_a_summary(door):
    client, jobs_dir, launched = door
    health = client.get("/guest/v1/health").json()
    assert health["questions_left_today"] == 2 and health["busy"] is False
    response = client.post("/guest/v1/deliberations", json={"question": "Should we adopt the new backup plan?"})
    assert response.status_code == 202
    ticket = response.json()["ticket"]
    assert launched == [ticket]
    record = json.loads((jobs_dir / f"{ticket}.json").read_text())
    assert record["guest"] is True
    # The job finishes; the guest sees its own summary and nothing else.
    record.update(status="finished", result={"verdict": "DENY", "votes": {}}, freed_models=["owner-model"])
    (jobs_dir / f"{ticket}.json").write_text(json.dumps(record))
    view = client.get(f"/guest/v1/deliberations/{ticket}").json()
    assert view["result"]["verdict"] == "DENY" and view["advisory_only"] is True
    assert "freed_models" not in view and view["question"] == "Should we adopt the new backup plan?"


def test_busy_and_limit_reveal_nothing_of_the_owner(door):
    client, jobs_dir, _ = door
    owner = job.start("The owner's private question?", jobs_dir=jobs_dir, launch=lambda t: None,
                      check_memory=lambda: None, free_local_ai=lambda: [])
    busy = client.post("/guest/v1/deliberations", json={"question": "Q?"})
    assert busy.status_code == 409 and owner["ticket"] not in busy.text and "private" not in busy.text
    assert client.get(f"/guest/v1/deliberations/{owner['ticket']}").status_code == 404
    assert client.get("/guest/v1/deliberations/../secrets").status_code == 404
    # The owner's job ends; the guest may ask until the daily limit.
    path = jobs_dir / f"{owner['ticket']}.json"
    path.write_text(json.dumps({**json.loads(path.read_text()), "status": "finished"}))
    for _ in range(2):
        ticket = client.post("/guest/v1/deliberations", json={"question": "Q?"}).json()["ticket"]
        guest_path = jobs_dir / f"{ticket}.json"
        guest_path.write_text(json.dumps({**json.loads(guest_path.read_text()), "status": "finished"}))
    assert client.post("/guest/v1/deliberations", json={"question": "Q?"}).status_code == 429
    old = datetime.now(timezone.utc) - timedelta(hours=25)
    for path in jobs_dir.glob("*.json"):
        record = json.loads(path.read_text())
        path.write_text(json.dumps({**record, "requested_at": old.isoformat()}))
    assert job.guest_daily_count(jobs_dir) == 0


def test_admission_is_shared_and_guest_limit_is_atomic(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    checking, proceed = Event(), Event()
    monkeypatch.setattr(server, "daily_limit", lambda: 1)

    def check_memory():
        checking.set()
        assert proceed.wait(10)

    def start(question, **kwargs):
        return job.start(question, launch=lambda _: None, check_memory=check_memory, **kwargs)

    client = TestClient(server.create_app(password=PASSWORD, jobs_dir=tmp_path, start=start))
    client.headers["Authorization"] = f"Bearer {PASSWORD}"

    def post():
        return client.post("/guest/v1/deliberations", json={"question": "Synthetic question?"})

    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(post)
        try:
            assert checking.wait(10)
            assert post().status_code == 409
            owner = job.start("Owner question?", jobs_dir=tmp_path,
                              free_local_ai=lambda: pytest.fail("admission already locked"))
            assert owner["status"] == "busy"
        finally:
            proceed.set()
        assert first.result(timeout=10).status_code == 202
    assert job.guest_daily_count(tmp_path) == 1
    assert post().status_code == 429


def test_bad_questions_are_refused(door):
    client, _, launched = door
    assert client.post("/guest/v1/deliberations", json={"question": ""}).status_code == 422
    assert client.post("/guest/v1/deliberations", json={"question": "x" * (job.MAX_QUERY_CHARS + 1)}).status_code == 422
    assert client.post("/guest/v1/deliberations", json={"question": "[REGION] [QUESTION]"}).status_code == 400
    assert launched == []


def test_a_guest_deliberation_uses_and_saves_nothing_of_the_owner(monkeypatch):
    from config.nodes import DEFAULT_NODES
    from core import tribunal as tribunal_module
    from core.models import FinalVerdict, TribunalResult

    calls = {}
    monkeypatch.setattr(tribunal_module, "build_context_packet", lambda query: pytest.fail("no owner memory"))
    for name in ("record_result", "log_decision_trace"):
        monkeypatch.setattr(tribunal_module, name, lambda result, name=name: pytest.fail(f"{name} for a guest"))
    monkeypatch.setattr(tribunal_module, "log_event", lambda *a, **kw: None)
    tribunal = tribunal_module.Tribunal(DEFAULT_NODES, runtime=object(),
                                        voice_announcer=lambda result: pytest.fail("no voice for a guest"))

    def cast_votes(query, session_id, theme, sequential, memory_context, *, include_enrichment=True):
        calls.update(memory=memory_context, enrichment=include_enrichment)
        return {}
    monkeypatch.setattr(tribunal.orchestrator, "cast_votes", cast_votes)
    monkeypatch.setattr(tribunal.orchestrator, "attach_audit", lambda result: None)
    monkeypatch.setattr(tribunal, "_record_session_memory", lambda *a: pytest.fail("no session memory"))
    monkeypatch.setattr(tribunal, "_queue_verdict_note", lambda result: pytest.fail("no voice note"))
    monkeypatch.setattr(tribunal.consensus_engine, "calculate_result", lambda q, v, s: TribunalResult(
        query=q, verdict=FinalVerdict.NO_CONSENSUS, confidence=0.0, reason="", votes={}, vote_distribution={},
        quorum_met=False, review_triggers=[], session_id=s, theme="military"))
    tribunal.deliberate("Question from another system?", guest=True)
    assert calls["enrichment"] is False
    assert calls["memory"]["items"] == [] and "second_brain" not in calls["memory"]


def test_the_password_is_saved_only_as_a_guest_setting(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from core.llm import online

    env_file = tmp_path / ".env"
    env_file.write_text("DEEPSEEK_API_KEY=keep\n", encoding="utf-8")
    monkeypatch.setenv("CONSENSUS_ONLINE_ENV_FILE", str(env_file))
    monkeypatch.delenv(server.PASSWORD_ENV, raising=False)
    first = server.new_password()
    client = TestClient(server.create_app(jobs_dir=tmp_path, sleep=lambda _: None))
    assert client.get("/guest/v1/health", headers={"Authorization": f"Bearer {first}"}).status_code == 200
    second = server.new_password()
    assert client.get("/guest/v1/health", headers={"Authorization": f"Bearer {first}"}).status_code == 401
    assert client.get("/guest/v1/health", headers={"Authorization": f"Bearer {second}"}).status_code == 200
    text = env_file.read_text(encoding="utf-8")
    assert len(first) >= server.MIN_PASSWORD_LENGTH and first != second
    assert text == f"DEEPSEEK_API_KEY=keep\n{server.PASSWORD_ENV}={second}\n"
    assert server.configured_password() == second
    for name in ("DEEPSEEK_API_KEY", "CONSENSUS_ONLINE_MODEL_BELLATOR"):
        with pytest.raises(ValueError):
            online.save_settings({name: "x"}, prefix="CONSENSUS_GUEST_")
    with pytest.raises(ValueError):
        online.save_settings({"DEEPSEEK_API_KEY": "x"}, prefix="DEEPSEEK_")
