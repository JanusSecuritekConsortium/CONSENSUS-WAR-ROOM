from datetime import datetime, timezone
from email.message import EmailMessage
from unittest.mock import MagicMock, patch
import pytest

from integrations.msty.personal import connectors as c, store
from integrations.msty.personal.review import possible_misses, render

NOW = datetime(2026, 9, 16, 12, tzinfo=timezone.utc)


def test_accounts_keep_roles_separate_and_disabled():
    accounts = store.defaults()['accounts']
    assert len(accounts)==9
    assert not any(a['enabled'] for a in accounts)
    assert next(a for a in accounts if a['id']=='rotary')['kind']=='gmail'
    assert next(a for a in accounts if a['id']=='work')['group']=='work'


def test_missing_sources_never_all_clear():
    results = c.collect(store.defaults(), NOW)
    body = render(results, NOW)
    assert 'not confirmation that nothing was missed' in body
    assert body.count('not configured')==9


def test_bridge_is_loopback_only():
    with pytest.raises(ValueError, match='loopback'):
        c.imap_mail({'kind':'bridge','host':'external.test'}, NOW)


def test_imap_read_only_sent_discovery_and_bounded_fetch():
    message = EmailMessage()
    message['From']='person@example.org'
    message['Subject']='Please confirm'
    message['Date']='Tue, 15 Sep 2026 12:00:00 +0000'
    message['Message-ID']='<one@example.org>'
    message.set_content('Please confirm the appointment.')
    raw = message.as_bytes()
    client = MagicMock()
    client.__enter__.return_value = client
    client.list.return_value = ('OK',[b'(\\Sent) "/" "Sent Items"'])
    client.select.return_value = ('OK',[b'1'])
    client.response.return_value = ('UIDVALIDITY',[b'8'])
    def uid(action, *args):
        if action=='search':
            return 'OK',[b'1']
        assert action=='fetch'
        if args[1]=='(RFC822.SIZE)':
            return 'OK',[b'1 (RFC822.SIZE 400)']
        assert args[1]=='(BODY.PEEK[])'
        return 'OK',[(b'1 BODY[]',raw)]
    client.uid.side_effect=uid
    account = next(a for a in store.defaults()['accounts'] if a['id']=='work')
    with patch.object(c, 'secret_read', return_value={'password':'test-only'}), patch.object(c.imaplib,'IMAP4_SSL',return_value=client):
        result=c.imap_mail(account,NOW)
    assert {m['direction'] for m in result['messages']}=={'inbox','sent'}
    assert all(call.kwargs['readonly'] for call in client.select.call_args_list)
    assert client.select.call_args_list[1].args[0]=='"Sent Items"'


def test_replies_and_bulk_are_not_unanswered_candidates():
    item={'direction':'inbox','date':'2026-09-10T12:00:00+00:00','subject':'Please confirm',
          'body':'Please confirm','message_id':'<a@example.org>'}
    assert possible_misses([item],NOW)==[item]
    reply=dict(item,direction='sent', references='<a@example.org>')
    assert not possible_misses([item,reply],NOW)
    assert not possible_misses([dict(item,bulk=True)],NOW)


def test_calendar_recurrence_exclusions_and_cancellation(tmp_path):
    path=tmp_path/'calendar.ics'
    path.write_text('''BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//EN
BEGIN:VEVENT
UID:recurring
DTSTART;TZID=Europe/Madrid:20260921T100000
DTEND;TZID=Europe/Madrid:20260921T110000
RRULE:FREQ=DAILY;COUNT=3
EXDATE;TZID=Europe/Madrid:20260922T100000
SUMMARY:Meeting
END:VEVENT
BEGIN:VEVENT
UID:cancelled
DTSTART;TZID=Europe/Madrid:20260924T100000
DTEND;TZID=Europe/Madrid:20260924T110000
STATUS:CANCELLED
SUMMARY:Cancelled meeting
END:VEVENT
BEGIN:VEVENT
UID:all-day
DTSTART;VALUE=DATE:20260925
DTEND;VALUE=DATE:20260926
SUMMARY:All day
END:VEVENT
END:VCALENDAR
''')
    result=c.calendar_events({'path':str(path)},NOW)
    assert len(result['events'])==3
    assert [e['start'] for e in result['events'][:2]]==['2026-09-21T10:00:00+02:00','2026-09-23T10:00:00+02:00']
    assert result['events'][2]['all_day']
    assert 'refresh the export' in result['warnings'][0]


def test_next_week_uses_local_calendar_across_dst():
    now=datetime(2026,10,20,12,tzinfo=timezone.utc)
    start,end=c.next_week(now)
    assert start.isoformat()=='2026-10-26T00:00:00+01:00'
    assert end.isoformat()=='2026-11-02T00:00:00+01:00'


def test_connector_failure_does_not_expose_secret():
    config={'accounts':[dict(store.defaults()['accounts'][0],enabled=True)]}
    with patch.dict(c.READERS, {'bridge':MagicMock(side_effect=ValueError('password SECRET'))}):
        result=c.collect(config,NOW)[0]
    assert result['status']=='unavailable'
    assert 'SECRET' not in str(result)


def test_dpapi_round_trip_and_no_plaintext(tmp_path):
    pytest.importorskip('win32crypt', reason='DPAPI is a Windows-only credential store')
    with patch.object(store,'ROOT',tmp_path):
        store.secret_write('test',{'password':'test-dummy-secret'})
        assert store.secret_read('test')['password']=='test-dummy-secret'
        assert b'test-dummy-secret' not in (tmp_path/'test.dpapi').read_bytes()
        with pytest.raises(ValueError):
            store.secret_read('../bad')


def test_drive_inventory_does_not_read_contents(tmp_path):
    (tmp_path/'note.txt').write_text('Private document body')
    result=c.drive_files({'path':str(tmp_path)},datetime.now(timezone.utc))
    assert result['files'][0]['name']=='note.txt'
    assert 'Private document body' not in str(result)


def test_graph_rejects_external_pagination():
    app,cache=MagicMock(),MagicMock()
    app.get_accounts.return_value=[{'username':'u@example.org'}]
    app.acquire_token_silent.return_value={'access_token':'test-dummy-token'}
    response=MagicMock()
    response.json.return_value={'value':[], '@odata.nextLink':'https://external.example/steal'}
    session=MagicMock()
    session.get.return_value=response
    with patch.object(c,'microsoft_app',return_value=(app,cache)), patch.object(c,'save_microsoft_cache'), patch('requests.Session',return_value=session):
        with pytest.raises(ValueError,match='pagination'):
            c.graph_mail({'id':'test','username':'u@example.org'},NOW)
    assert session.get.call_count==1
