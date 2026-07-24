from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path

from fastapi.testclient import TestClient

from config.nodes import DEFAULT_NODES
from config.runtime import RuntimeConfig
from core.models import FinalVerdict, TribunalResult, Vote, VoteValue
from integrations.msty import api


def _result(query: str = "API test proposal") -> TribunalResult:
    votes = {
        name: Vote(
            node_key=name,
            role=node.role,
            vote=VoteValue.APPROVE,
            confidence=0.8,
            reasoning="Bounded test rationale.",
            response_time=float(index),
        )
        for index, (name, node) in enumerate(DEFAULT_NODES.items(), start=1)
    }
    return TribunalResult(
        query=query,
        verdict=FinalVerdict.APPROVE,
        confidence=0.8,
        reason="Test majority.",
        votes=votes,
        vote_distribution={"APPROVE": 3},
        quorum_met=True,
        review_triggers=[],
        session_id="api-test-session",
        theme="military",
        terminal_branch="majority",
        timestamp="2026-07-24T12:00:00+00:00",
    )


class FakeTribunal:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def deliberate(self, query: str, sequential: bool = False) -> TribunalResult:
        return _result(query)


def test_api_exposes_json_and_csv_decision_summary(tmp_path: Path, monkeypatch) -> None:
    history_path = tmp_path / "history.json"
    history_path.write_text(json.dumps([api.result_to_dict(_result())]), encoding="utf-8")
    monkeypatch.setattr(api, "HISTORY_PATH", history_path)
    app = api.create_api_app(RuntimeConfig(backend="mock"), DEFAULT_NODES)

    with TestClient(app) as client:
        summary = client.get("/analytics/summary")
        assert summary.status_code == 200
        assert summary.json()["decision_count"] == 1

        exported = client.get("/analytics/summary.csv")
        assert exported.status_code == 200
        assert exported.headers["content-type"].startswith("text/csv")
        assert "consensus_summary_" in exported.headers["content-disposition"]
        rows = list(csv.DictReader(StringIO(exported.text)))
        assert any(row["metric"] == "decision_count" and row["value"] == "1" for row in rows)


def test_websocket_streams_bounded_consensus_lifecycle(monkeypatch) -> None:
    monkeypatch.setattr(api, "Tribunal", FakeTribunal)
    app = api.create_api_app(RuntimeConfig(backend="mock"), DEFAULT_NODES)

    with TestClient(app) as client:
        with client.websocket_connect("/ws/tribunal") as websocket:
            connected = websocket.receive_json()
            assert connected["type"] == "connected"

            websocket.send_json({"type": "ping"})
            assert websocket.receive_json()["type"] == "pong"

            response = client.post("/consensus", json={"query": "Stream this verdict"})
            assert response.status_code == 200
            started = websocket.receive_json()
            completed = websocket.receive_json()
            assert started == {
                "type": "consensus_started",
                "timestamp": started["timestamp"],
                "source": "api",
                "query_preview": "Stream this verdict",
                "query_length": 19,
            }
            assert completed["type"] == "consensus_complete"
            assert completed["session_id"] == "api-test-session"
            assert completed["verdict"] == "APPROVE"
            assert "reason" not in completed
            assert "votes" not in completed
