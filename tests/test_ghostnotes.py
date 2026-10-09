import sqlite3
import pytest
from core.knowledge.ghostnotes import search
from core.memory import context


@pytest.fixture
def index(tmp_path, monkeypatch):
    monkeypatch.setenv('CONSENSUS_SECOND_BRAIN',str(tmp_path))
    folder=tmp_path/'50 Agents'
    folder.mkdir()
    path=folder/'ghostnotes.sqlite'
    with sqlite3.connect(path) as db:
        db.execute('CREATE VIRTUAL TABLE passages USING fts5(title,body,local_path UNINDEXED,source_url UNINDEXED,retrieved_at UNINDEXED,page UNINDEXED)')
        db.execute('CREATE TABLE metadata(key TEXT,value TEXT)')
        db.executemany('INSERT INTO metadata VALUES (?,?)',[('schema_version','1'),('snapshot_at','2026-10-05')])
        db.executemany('INSERT INTO passages VALUES (?,?,?,?,?,?)',[
            ('Radio communications','Radio communications source example','a.md','https://example.org/a','2026-10-05',''),
            ('Radio communications','Second radio communications passage','a.md','https://example.org/a','2026-10-05',''),
            ('Radio reference','Communications radio reference','b.pdf','https://example.org/b','2026-10-05','2'),
            ('Unrelated','Completely unrelated subject','c.md','https://example.org/c','2026-10-05','')])
    return path


def test_retrieval_is_bounded_attributed_and_deduplicated(index):
    result=search('radio communications',2)
    assert result['status']=='available'
    assert len(result['matches'])==2
    assert len({r['local_path'] for r in result['matches']})==2
    assert all(r['source_url'] and r['retrieved_at'] for r in result['matches'])
    assert next(r for r in result['matches'] if r['local_path']=='b.pdf')['page']=='2'


def test_query_cannot_execute_sql_or_fts_operators(index):
    search('radio"; DROP TABLE passages; -- NOT communications*',2)
    assert search('radio')['matches']
    assert not search('unfindablexyz')['matches']
    assert search('the and')['status']=='no_search_terms'
    with pytest.raises(ValueError): search('radio',True)
    with pytest.raises(ValueError): search('x'*2001)


def test_missing_database_is_not_created(tmp_path,monkeypatch):
    monkeypatch.setenv('CONSENSUS_SECOND_BRAIN',str(tmp_path))
    assert search('radio')['status']=='unavailable'
    assert not list(tmp_path.iterdir())


def test_shared_packet_and_mcp_retrieve_same_sources(index,monkeypatch):
    monkeypatch.setattr(context,'retrieve_relevant_context',lambda *a,**k:{'summary':'prior','items':[]})
    packet=context.build_context_packet('radio communications')
    assert packet['summary']=='prior'
    assert packet['external_reference_context']['matches']
    from config.nodes import DEFAULT_NODES
    from core.prompting.assembler import assemble_monolith_prompt
    for node in DEFAULT_NODES.values():
        assert 'https://example.org/a' in assemble_monolith_prompt(node,'radio communications',{'memory_context':packet})
    from integrations.mcp.consensus_mcp_server import ghostnotes_search, TOOLS
    assert ghostnotes_search({'query':'radio communications'})['matches']==search('radio communications')['matches']
    assert any(t['name']=='ghostnotes_search' for t in TOOLS)


def test_archived_briefing_context_does_not_become_current_news(index):
    from core.knowledge.ghostnotes import briefing_background
    from integrations.msty.personal.digest import news_digest
    current='- Current publisher: radio communications update\n  https://example.org/current'
    background=briefing_background(['radio communications'])
    assert 'archived reference, not current reporting' in background
    assert 'https://example.org/a' in background
    assert news_digest(current+background)==news_digest(current)


def test_jsonrpc_returns_citable_passages(index):
    import json
    from integrations.mcp.consensus_mcp_server import handle_jsonrpc
    response=handle_jsonrpc({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'ghostnotes_search','arguments':{'query':'radio communications','limit':1}}})
    payload=json.loads(response['result']['content'][0]['text'])
    assert payload['status']=='available'
    assert len(payload['matches'])==1
    assert payload['matches'][0]['source_url']


def test_news_archive_includes_retrieved_background(index,monkeypatch):
    from datetime import datetime, timezone
    from integrations.msty import aurelius_reports
    from integrations.msty.personal.publication import news_section
    now=datetime(2026,10,5,tzinfo=timezone.utc)
    monkeypatch.setattr(aurelius_reports,'FEEDS',())
    monkeypatch.setattr(aurelius_reports,'select_stories',lambda *a,**k:[({'name':'Publisher'},{'title':'Radio communications update','published':now,'url':'https://example.org/current'})])
    report=news_section(now)
    assert 'https://example.org/current' in report
    assert 'Source: https://example.org/a' in report
    assert 'archived reference, not current reporting' in report
