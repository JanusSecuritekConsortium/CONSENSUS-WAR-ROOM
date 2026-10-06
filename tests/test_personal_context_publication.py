from datetime import datetime, timezone
import json
import sqlite3
from unittest.mock import patch
import pytest
from integrations.msty.personal.context import mail_context, agenda
from integrations.msty.personal import publication as p

NOW = datetime(2026,9,27,12,tzinfo=timezone.utc)


def message(**kwargs):
    return dict({'direction':'inbox','date':'2026-09-26T08:00:00Z','from':'Person <person@example.org>',
                 'to':'me@example.org','subject':'Project','body':'Could you review the proposal?',
                 'message_id':'<one@example.org>'}, **kwargs)


def test_isolated_request_low_priority_prior_exchange_promoted():
    incoming = message()
    assert mail_context([incoming],NOW)[0] == []
    assert len(mail_context([incoming],NOW)[1]) == 1
    sent = message(direction='sent',to='Person <PERSON@example.org>',date='2026-09-24T10:00:00Z')
    priority, low = mail_context([incoming,sent],NOW)
    assert len(priority)==1 and priority[0]['previous_outgoing']==1 and not low


def test_later_unrelated_sent_mail_does_not_establish_prior_interest():
    sent = message(direction='sent',to='person@example.org',date='2026-09-27T10:00:00Z')
    assert not mail_context([message(),sent],NOW)[0]


def test_actual_reply_suppresses_but_does_not_mark_completed():
    sent = message(direction='sent',date='2026-09-27T10:00:00Z',references='<one@example.org>')
    assert mail_context([message(),sent],NOW)==([],[])


def test_explicit_action_notice_and_new_request_not_delayed_two_days():
    incoming=message(subject='Action required: payment failed',body='See billing details.',automated=True)
    assert mail_context([incoming],NOW)[0][0]['urgent']


def event(uid,start,end,**kwargs):
    return dict({'uid':uid,'start':'2026-09-28T'+start+':00+02:00',
                 'end': '2026-09-28T'+end+':00+02:00' if end else None,'title':uid,'all_day':False},**kwargs)


def source(events):
    return [{'id':'cal','label':'Calendar','status':'ok','events':events}]


def test_agenda_names_days_and_exact_overlap_not_adjacency():
    text='\n'.join(agenda(source([event('Alpha','09:00','10:00'),event('Beta','09:45','11:00'),event('Gamma','11:00','12:00')])))
    assert 'Monday 28/09' in text and '09:00–10:00: Alpha' in text
    assert '09:45–10:00: Alpha ↔ Beta' in text
    assert 'Beta ↔ Gamma' not in text


def test_no_fabricated_conflicts_missing_end_free_and_duplicate():
    a=event('Alpha','09:00','10:00')
    text='\n'.join(agenda(source([a,a,event('Unknown','09:10',None),event('Free','09:15','09:30',transparent=True)])))
    assert 'OVERLAPS DE HORARIO' not in text
    assert text.count('09:00–10:00: Alpha')==1


def test_busy_title_limitation_visible():
    assert 'does not share the title' in '\n'.join(agenda(source([event('Busy','09:00','10:00')])))


def test_busy_calendar_warns_in_source_coverage(tmp_path):
    from integrations.msty.personal.connectors import calendar_events
    path=tmp_path/'busy.ics'
    path.write_text('BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nUID:busy\nDTSTART:20260928T100000Z\nDTEND:20260928T110000Z\nSUMMARY:Busy\nEND:VEVENT\nEND:VCALENDAR\n')
    result=calendar_events({'path':str(path)},NOW,'morning')
    assert any('full-view' in warning for warning in result['warnings'])


@pytest.mark.parametrize('body', ['a'*4097,'🚀'*2049])
def test_oversized_text_never_becomes_attachment(tmp_path,body):
    with patch.object(p,'telegram_call') as call:
        with pytest.raises(ValueError):
            p.deliver(body,{'status':'prepared','message_ids':[]},tmp_path/'receipt.json',{'chat_id':'123'})
    call.assert_not_called()


def test_document_transport_is_disabled():
    with patch('requests.post') as post:
        with pytest.raises(RuntimeError):
            p.telegram_call({'token':'dummy'},'sendDocument',{})
    post.assert_not_called()


def test_delivery_receipts_prevent_duplicate_and_uncertain_retry(tmp_path):
    state={'status':'prepared','message_ids':[]}
    route={'chat_id':'123','token':'not-a-real-token'}
    with patch.object(p,'telegram_call',return_value={'chat':{'id':123},'message_id':7}) as call:
        p.deliver('hello',state,tmp_path/'state.json',route)
        p.deliver('hello',state,tmp_path/'state.json',route)
        assert call.call_count==1
    assert state['status']=='delivered'
    broken={'status':'prepared','message_ids':[]}
    with patch.object(p,'telegram_call',side_effect=RuntimeError('network')) as call:
        with pytest.raises(RuntimeError): p.deliver('hello',broken,tmp_path/'failed.json',route)
        with pytest.raises(RuntimeError): p.deliver('hello',broken,tmp_path/'failed.json',route)
        assert call.call_count==1
    assert json.loads((tmp_path/'failed.json').read_text())['status']=='uncertain'


def test_archive_retrieval_rejects_path_escape(tmp_path):
    (tmp_path/'index.json').write_text(json.dumps({'latest':{'note':'../outside.md'}}))
    with pytest.raises(ValueError): p.recall(vault=tmp_path)


def test_publish_archives_links_and_delivers_once(tmp_path):
    report={'body_text':'AURELIUS\n1. EMAIL\nSin tareas confirmadas.', 'generated_at':NOW.isoformat(),'coverage':[]}
    route={'chat_id':'123','token':'dummy'}
    def api(route,method,data):
        return {'id':123,'type':'private'} if method=='getChat' else {'message_id':42,'chat':{'id':123}}
    with patch('integrations.msty.personal.store.load',return_value={'telegram_briefing_format':'text'}), \
         patch('integrations.msty.personal.review.build',return_value=report) as build, \
         patch.object(p,'news_section',return_value='5. NOTICIAS\nNone'), \
         patch.object(p,'telegram_route',return_value=route), \
         patch.object(p,'telegram_call',side_effect=api) as call, \
         patch('integrations.msty.aurelius_memory.remember') as remember:
        first=p.publish('evening',True,vault=tmp_path)
        second=p.publish('evening',True,vault=tmp_path)
        assert first['status']=='delivered' and second['status']=='already_delivered'
        assert build.call_count==0 and call.call_count==2 and remember.call_count==1
    recalled=p.recall(vault=tmp_path)
    assert recalled['status']=='available' and 'source-snapshot' in recalled['body_text']


def test_schedule_migration_keeps_times_and_route_but_sends_only_via_publisher(tmp_path):
    from integrations.msty.personal.schedules import install_telegram
    db_path=tmp_path/'msty.db'
    with sqlite3.connect(db_path) as db:
        db.execute('CREATE TABLE scheduled_jobs(id,label,payload_json,enabled,cron_expression,updated_at,timezone,next_run_at)')
        db.execute('CREATE TABLE scheduled_job_destinations(job_id,kind,config_json,enabled)')
        db.execute('CREATE TABLE providers(id,base_url)')
        db.execute("INSERT INTO providers VALUES('local','http://127.0.0.1:11964')")
        for key,label,cron in [('main','Morning Brief','0 7 * * *'),('evening','End-of-Day Shutdown','30 17 * * 1-5'),
                               ('weekly','Weekly review and next-week appointments','0 18 * * 0'),
                               ('aurelius-personal-morning-v1','Legacy','15 7 * * *')]:
            db.execute('INSERT INTO scheduled_jobs VALUES(?,?,?,1,?,NULL,NULL,NULL)',(key,label,json.dumps({'providerId':'local'}),cron))
        db.execute("INSERT INTO scheduled_job_destinations VALUES('main','channel','{\"presetId\":\"existing\",\"template\":\"{{body_text}}\"}',1)")
    with patch('integrations.msty.personal.publication.telegram_route'):
        install_telegram(db_path,tmp_path/'backups')
        install_telegram(db_path,tmp_path/'backups')
    with sqlite3.connect(db_path) as db:
        payload,enabled,cron=db.execute("SELECT payload_json,enabled,cron_expression FROM scheduled_jobs WHERE id='main'").fetchone()
        assert 'publish --mode morning --telegram' in json.loads(payload)['prompt']
        assert enabled==1 and cron=='0 7 * * *'
        assert db.execute("SELECT enabled FROM scheduled_jobs WHERE id='aurelius-personal-morning-v1'").fetchone()[0]==0
        config,enabled=db.execute('SELECT config_json,enabled FROM scheduled_job_destinations').fetchone()
        assert json.loads(config)=={'presetId':'existing','template':'{{body_text}}'} and enabled==0


def test_large_evening_digest_keeps_all_sections_within_one_message():
    from integrations.msty.personal.digest import personal_digest, units
    events=[event('Meeting '+str(i)+' 🚀'*80,'09:00','10:00') for i in range(100)]
    text=personal_digest(source(events),NOW,tasks=['Task 🚀'*80 for _ in range(50)])
    assert units(text)<=4096
    assert all(title in text for title in ('SAVED TASKS','EMAIL','AGENDA','OVERLAPS'))
    assert 'more items; details' in text


def test_morning_publication_does_not_fetch_news(tmp_path):
    report={'body_text':'full private report','telegram_text':'AURELIUS · CIERRE','generated_at':NOW.isoformat(),'coverage':[]}
    with patch('integrations.msty.personal.review.build',return_value=report), patch.object(p,'news_section') as news, patch('integrations.msty.aurelius_memory.remember'):
        result=p.publish('morning',False,vault=tmp_path)
    news.assert_not_called()
    receipt=json.loads(next((tmp_path/'Deliveries').glob('*.json')).read_text(encoding='utf-8'))
    assert receipt['telegram_text']=='AURELIUS · CIERRE' and 'full private report' in receipt['body_text']
