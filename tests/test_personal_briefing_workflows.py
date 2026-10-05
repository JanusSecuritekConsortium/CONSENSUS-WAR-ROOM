from datetime import datetime, timezone
import json
import sqlite3
from unittest.mock import patch

import pytest

from integrations.msty.personal import connectors, schedules, service, store
from integrations.msty.personal.review import render
from integrations.mcp.consensus_mcp_server import handle_jsonrpc
from integrations.msty.aurelius import AureliusOperator


def test_daily_calendar_window_is_not_next_week():
    now = datetime(2026, 9, 27, 8, tzinfo=timezone.utc)
    start, end = connectors.calendar_window(now, 'morning')
    assert (str(start.date()), str(end.date())) == ('2026-09-27', '2026-10-04')
    start, end = connectors.calendar_window(now, 'evening')
    assert (str(start.date()), str(end.date())) == ('2026-09-28', '2026-09-29')
    start, end = connectors.calendar_window(now, 'weekly')
    assert (str(start.date()), str(end.date())) == ('2026-09-28', '2026-10-05')


def test_calendar_modes_across_dst():
    now = datetime(2026, 10, 24, 8, tzinfo=timezone.utc)
    start, end = connectors.calendar_window(now, 'morning')
    assert start.utcoffset().total_seconds() == 7200
    assert end.utcoffset().total_seconds() == 3600
    assert (end.astimezone(timezone.utc)-start.astimezone(timezone.utc)).total_seconds() == 169*3600


def test_morning_calendar_collection_includes_today(tmp_path):
    path = tmp_path/'calendar.ics'
    path.write_text('BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nUID:today\nDTSTART:20260927T100000Z\nSUMMARY:Today\nEND:VEVENT\nBEGIN:VEVENT\nUID:nextweek\nDTSTART:20260930T100000Z\nSUMMARY:Later\nEND:VEVENT\nEND:VCALENDAR\n')
    account = dict(next(a for a in store.defaults()['accounts'] if a['kind']=='calendar'), enabled=True, path=str(path))
    now = datetime(2026,9,27,8,tzinfo=timezone.utc)
    results = connectors.collect({'accounts':[account]},now,mode='morning')
    assert [e['uid'] for e in results[0]['events']] == ['today', 'nextweek']
    body = render(results,now,mode='morning')
    assert 'NEXT SEVEN DAYS' in body
    assert 'Today' in body and 'Later' in body


def test_personal_workflows_use_same_local_service():
    with patch('integrations.msty.personal.review.run', return_value='LOCAL REVIEW') as run:
        reply = handle_jsonrpc({'jsonrpc':'2.0','id':9,'method':'tools/call','params':{'name':'aurelius_personal_review','arguments':{'mode':'evening'}}})
        assert 'LOCAL REVIEW' in reply['result']['content'][0]['text']
        run.assert_called_once_with(mode='evening')
        operator = AureliusOperator.__new__(AureliusOperator)
        assert operator.call_workflow_integration('personal_review', {'mode':'weekly'})['body_text'].startswith('LOCAL REVIEW\n\nConsultation: ')
    with pytest.raises(ValueError):
        service.personal_review('arbitrary')


def test_schedule_upgrade_repairs_payloads_preserves_public_jobs(tmp_path):
    path = tmp_path/'msty.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE scheduled_jobs(id TEXT PRIMARY KEY,label,job_kind,resource_kind,trigger_kind,cron_expression,timezone,payload_json,policy_json,enabled,next_run_at,updated_at)')
        db.execute('CREATE TABLE providers(id,base_url)')
        db.execute('CREATE TABLE scheduled_job_destinations(id TEXT PRIMARY KEY,job_id,kind,config_json,enabled,position)')
        db.execute('INSERT INTO providers VALUES(?,?)', ('local','http://127.0.0.1:11964'))
        payload=json.dumps({'providerId':'local','model':'local-model'})
        db.execute('INSERT INTO scheduled_jobs(id,label,payload_json,policy_json,enabled) VALUES(?,?,?,?,?)',('news','Morning Brief',payload,'{}',1))
        db.execute('INSERT INTO scheduled_jobs(id,label,payload_json,policy_json,enabled) VALUES(?,?,?,?,?)',('aurelius-personal-morning-v1','Old','{}','{}',0))
        db.execute('INSERT INTO scheduled_job_destinations VALUES(?,?,?,?,?,?)',('remote','aurelius-personal-morning-v1','channel','{}',1,0))
        before = db.execute("SELECT * FROM scheduled_jobs WHERE id='news'").fetchone()
    accounts = [dict(a,enabled=True,last_test_ok=True) for a in store.defaults()['accounts'] if a['id'] in ('gmail','proton-calendar')]
    with patch.object(store,'load', return_value={'accounts':accounts}), patch('integrations.msty.personal.status.missing_fields',return_value=[]):
        schedules.install(True, path, tmp_path/'backups')
        schedules.install(True, path, tmp_path/'backups')
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT * FROM scheduled_jobs WHERE id='news'").fetchone() == before
        rows = db.execute("SELECT id,payload_json,enabled,next_run_at FROM scheduled_jobs WHERE id LIKE 'aurelius-personal-%'").fetchall()
        assert len(rows) == 3
        for job_id, payload, enabled, next_run in rows:
            mode = 'weekly' if 'weekly' in job_id else 'evening' if 'evening' in job_id else 'morning'
            parsed=json.loads(payload)
            assert '--mode '+mode in parsed['prompt']
            assert '\n' in parsed['prompt'] and '\\n' not in parsed['prompt']
            assert parsed['workspacePath'] == 'G:\\CONSENSUS_SYSTEM'
            assert enabled == 1 and next_run
        assert db.execute("SELECT enabled FROM scheduled_job_destinations WHERE id='remote'").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM scheduled_job_destinations WHERE kind='in_app' AND enabled=1").fetchone()[0] == 3


def test_schedule_enable_requires_verified_sources(tmp_path):
    with patch.object(store, 'load', side_effect=store.defaults):
        with pytest.raises(ValueError, match='Verify and enable'):
            schedules.install(True, tmp_path/'unused.db')
