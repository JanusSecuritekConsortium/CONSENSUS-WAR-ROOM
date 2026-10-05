from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest

from integrations.msty.personal import actions, calendar_browser, store


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'ROOT', tmp_path)
    monkeypatch.setattr(store, 'load', lambda: {'accounts': [
        {'id': 'gmail', 'kind': 'gmail', 'username': 'sender@example.com', 'enabled': True}]})


def email(key='request-1', **extra):
    return actions.prepare('email', key, account_id='gmail', to='recipient@example.com',
                           subject='Test', body='Synthetic test', **extra)


def test_draft_idempotency_and_payload_binding(isolated):
    first=email()
    assert email()['action_id']==first['action_id']
    with pytest.raises(ValueError):
        actions.prepare('calendar','request-1',title='Other',start='2026-09-28T10:00:00+02:00',end='2026-09-28T11:00:00+02:00')


@pytest.mark.parametrize('value',['person','a@example.com, b@example.com','a@example.com\nBcc: b@example.com'])
def test_recipient_rejects_ambiguity(value):
    with pytest.raises(ValueError):
        actions.address(value)


def test_execute_only_once_with_concurrent_calls(isolated,monkeypatch):
    draft=email()
    send=Mock(return_value={'status':'submitted'})
    monkeypatch.setattr(actions,'send_email',send)
    def run(_):
        try:return actions.execute(draft['action_id'],'Send this exact synthetic email')
        except ValueError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(run,range(2)))
    assert send.call_count==1
    assert actions.status(draft['action_id'])['status']=='submitted'
    actions.execute(draft['action_id'],'Send this exact synthetic email')
    assert send.call_count==1


def test_unknown_delivery_never_retries(isolated,monkeypatch):
    draft=email()
    send=Mock(side_effect=TimeoutError('private server details'))
    monkeypatch.setattr(actions,'send_email',send)
    result=actions.execute(draft['action_id'],'Send this message')
    assert result['status']=='uncertain'
    assert 'private server details' not in str(result)
    with pytest.raises(ValueError):actions.execute(draft['action_id'],'Send this message')
    assert send.call_count==1


def test_ics_has_correct_times_and_no_invitations(isolated):
    import icalendar
    draft=actions.prepare('calendar','calendar-test',title='Synthetic appointment',
                          start='2026-09-28T10:00:00+02:00',end='2026-09-28T10:30:00+02:00')
    path=calendar_browser.event_file(draft['preview'],draft['action_id'])
    event=icalendar.Calendar.from_ical(path.read_bytes()).walk('VEVENT')[0]
    assert event.decoded('dtstart').hour==8
    assert event.decoded('dtend').hour==8
    assert event.decoded('dtend').minute==30
    assert not event.get('attendee')
    assert not event.walk('VALARM')


def test_naive_dates_rejected(isolated):
    with pytest.raises(ValueError):
        actions.prepare('calendar','bad-date',title='Test',start='2026-09-28T10:00:00',end='2026-09-28T11:00:00')


def test_smtp_quit_failure_does_not_turn_acceptance_into_failure(isolated,monkeypatch):
    client=Mock()
    client.send_message.return_value={}
    client.quit.side_effect=ConnectionError()
    monkeypatch.setattr(actions,'smtp_connection',lambda source:client)
    draft=email()
    assert actions.execute(draft['action_id'],'Send this message')['status']=='submitted'
    assert client.send_message.call_count==1
