from core.knowledge.second_brain import MAX_BRIEF_BYTES, shared_brain_context
from core.memory import context


def test_only_curated_brief_is_loaded(tmp_path, monkeypatch):
    monkeypatch.setenv("CONSENSUS_SECOND_BRAIN", str(tmp_path))
    agents = tmp_path / "50 Agents"
    agents.mkdir()
    (agents / "Shared Context.md").write_text("Reviewed startup context", encoding="utf-8")
    (tmp_path / "medical.md").write_text("PRIVATE RECORD", encoding="utf-8")
    result = shared_brain_context()
    assert result["status"] == "available"
    assert result["content"] == "Reviewed startup context"
    assert "PRIVATE RECORD" not in str(result)


def test_missing_invalid_and_oversized_brief(tmp_path, monkeypatch):
    monkeypatch.setenv("CONSENSUS_SECOND_BRAIN", str(tmp_path))
    assert shared_brain_context()["status"] == "unavailable"
    agents = tmp_path / "50 Agents"
    agents.mkdir()
    brief = agents / "Shared Context.md"
    for data, status in [(b"\xff", "unavailable"), (b" ", "empty"), (b"x" * (MAX_BRIEF_BYTES + 1), "brief_too_large")]:
        brief.write_bytes(data)
        assert shared_brain_context()["status"] == status


def test_brief_added_without_changing_prior_decisions(monkeypatch):
    original = {"summary": "Prior decision", "items": [{"id": "old"}], "prior_decisions_used": 1}
    monkeypatch.setattr(context, "retrieve_relevant_context", lambda *a, **kw: dict(original))
    monkeypatch.setattr(context, "shared_brain_context", lambda: {"status": "available", "content": "brief"})
    packet = context.build_context_packet("query")
    assert all(packet[key] == value for key, value in original.items())
    assert packet["second_brain"]["content"] == "brief"


def test_each_monolith_prompt_receives_the_brief(monkeypatch):
    from config.nodes import DEFAULT_NODES
    from core.prompting.assembler import assemble_monolith_prompt

    monkeypatch.setattr(context, "retrieve_relevant_context", lambda *a, **kw: {"summary": "No prior decisions."})
    monkeypatch.setattr(context, "shared_brain_context", lambda: {"status": "available", "content": "UNIQUE_CURATED_BRIEF"})
    packet = context.build_context_packet("query")
    for node in DEFAULT_NODES.values():
        prompt = assemble_monolith_prompt(node, "query", {"memory_context": packet})
        assert "UNIQUE_CURATED_BRIEF" in prompt
