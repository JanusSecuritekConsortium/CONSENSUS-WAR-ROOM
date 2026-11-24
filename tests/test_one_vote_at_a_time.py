"""9.22.0: one real vote at a time across the window, background tickets, the web API and the command line;
web API votes run as tickets that can ask the owner; tickets show their progress (Codex review 2026-11-24)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from config.nodes import DEFAULT_NODES
from config.runtime import RuntimeConfig
from core import vote_lock
from core.models import Vote, VoteValue
from core.tribunal import Tribunal
from integrations.mcp import tribunal_job as job
from tests.test_tribunal_job import result


def test_a_second_vote_is_refused_while_one_holds_the_lock():
    assert vote_lock.holder() is None
    with vote_lock.hold("the desktop window"):
        held = vote_lock.holder()
        assert held["source"] == "the desktop window" and "already running" in held["detail"]
        with pytest.raises(vote_lock.VoteBusy, match="desktop window"):
            with vote_lock.hold("the command line"):
                pass
    assert vote_lock.holder() is None  # released when the vote ends


def test_a_background_vote_is_not_queued_while_a_window_vote_runs(tmp_path):
    with vote_lock.hold("the desktop window"):
        reply = job.start("Should we move the backups?", jobs_dir=tmp_path, launch=lambda ticket: None,
                          check_memory=lambda: None, free_local_ai=lambda: [])
    assert reply["status"] == "busy" and "desktop window" in reply["detail"]
    assert not list(tmp_path.glob("*.json"))


def test_a_real_tribunal_vote_holds_the_lock_and_a_simulated_one_does_not():
    real = Tribunal(DEFAULT_NODES, SimpleNamespace(config=SimpleNamespace(backend="msty-local")))
    with vote_lock.hold("a background vote"):
        with pytest.raises(vote_lock.VoteBusy):
            real.deliberate("Should the library open on Sundays?")
    seen = []
    simulated = Tribunal(DEFAULT_NODES, SimpleNamespace(config=SimpleNamespace(backend="mock")))
    simulated._deliberate = lambda *a, **kw: seen.append(vote_lock.holder()) or "done"
    with vote_lock.hold("a background vote"):
        assert simulated.deliberate("Should the library open on Sundays?") == "done"
    real._deliberate = lambda *a, **kw: seen.append(vote_lock.holder()["source"]) or "done"
    assert real.deliberate("q", source="the command line") == "done"
    assert seen[1] == "the command line"


def test_a_window_vote_is_refused_at_once_while_another_vote_runs():
    from ui import flet_app as gui
    state = SimpleNamespace(config=RuntimeConfig(backend="msty-local"))
    with vote_lock.hold("a background vote (phone, MCP or web API)"):
        with pytest.raises(vote_lock.VoteBusy, match="background vote"):
            gui.submit_proposal_live_for_gui(state, "Should the library open on Sundays?")


def test_a_ticket_shows_round_voter_and_model(tmp_path):
    ticket = job.start("Should we move the backups?", jobs_dir=tmp_path, launch=lambda ticket: None,
                       check_memory=lambda: None, free_local_ai=lambda: [])["ticket"]
    seen = {}

    def deliberate(query, ask_owner=None, on_event=None):
        on_event({"type": "round_started", "round": 2, "phase": "critique", "rerun": 0})
        on_event({"type": "agent_started", "round": 2, "phase": "critique", "agent_id": "BELLATOR"})
        seen["running"] = job.status(ticket, jobs_dir=tmp_path)
        vote = Vote(node_key="BELLATOR", role="security", vote=VoteValue.APPROVE, confidence=0.8, reasoning="r",
                    model="Ministral-3-8B")
        on_event({"type": "vote_received", "round": 2, "phase": "critique", "agent_id": "BELLATOR", "vote": vote})
        return result(query)

    record = job.run(ticket, jobs_dir=tmp_path, deliberate=deliberate)
    assert "Round 2, critique: BELLATOR is answering" in seen["running"]["detail"]
    assert record["progress"]["completed_turns"] == 1
    assert record["progress"]["step"] == "BELLATOR answered APPROVE on Ministral-3-8B"


def _api_client(monkeypatch, records):
    from fastapi.testclient import TestClient
    from integrations.msty import api
    started = []
    monkeypatch.setattr(api, "API_TICKET_POLL_SECONDS", 0)
    monkeypatch.setattr(job, "start", lambda query, **kw: started.append((query, kw)) or
                        {"status": "queued", "ticket": "abc123"})
    monkeypatch.setattr(job, "status", lambda ticket, **kw: records.pop(0) if len(records) > 1 else records[0])
    return TestClient(api.create_api_app(RuntimeConfig(backend="msty-local"), DEFAULT_NODES)), started


def test_a_real_api_vote_runs_as_a_ticket_and_returns_its_verdict(monkeypatch):
    records = [{"ticket": "abc123", "status": "running"},
               {"ticket": "abc123", "status": "finished", "result": {"verdict": "APPROVE", "confidence": 0.8}}]
    client, started = _api_client(monkeypatch, records)
    reply = client.post("/consensus", json={"query": "Should the library open on Sundays?", "sequential": True})
    assert reply.status_code == 200 and reply.json()["verdict"] == "APPROVE" and reply.json()["ticket"] == "abc123"
    assert started[0][1]["options"]["sequential"] is True and started[0][1]["options"]["source"] == "the web API"


def test_a_real_api_vote_waiting_for_the_owner_says_how_to_answer(monkeypatch):
    records = [{"ticket": "abc123", "status": "awaiting_answers", "questions": [{"agent": "BELLATOR", "asks": ["Budget?"]}]}]
    client, _ = _api_client(monkeypatch, records)
    reply = client.post("/consensus", json={"query": "Should the library open on Sundays?"})
    assert reply.status_code == 202
    body = reply.json()
    assert body["status"] == "awaiting_answers" and body["questions"][0]["asks"] == ["Budget?"]
    assert "/consensus/abc123/answer" in body["detail"]
    answers = []
    monkeypatch.setattr(job, "answer", lambda ticket, text, stop=False: answers.append((ticket, text, stop)) or
                        {"ticket": ticket, "status": "answered"})
    assert client.post("/consensus/abc123/answer", json={"answer": "Budget is 2,000 euros."}).json()["status"] == "answered"
    assert answers == [("abc123", "Budget is 2,000 euros.", False)]


def test_a_busy_tribunal_refuses_an_api_vote(monkeypatch):
    from fastapi.testclient import TestClient
    from integrations.msty import api
    monkeypatch.setattr(job, "start", lambda query, **kw: {"status": "busy", "detail": "Another deliberation is running"})
    client = TestClient(api.create_api_app(RuntimeConfig(backend="msty-local"), DEFAULT_NODES))
    reply = client.post("/consensus", json={"query": "Should the library open on Sundays?"})
    assert reply.status_code == 409 and "Another deliberation" in str(reply.json())
