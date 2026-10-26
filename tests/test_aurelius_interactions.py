"""Synthetic end-to-end checks for local bilingual Telegram interactions."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from unittest.mock import Mock
import pytest

from integrations.msty.personal import (agenda_query as agenda, calendar_changes as changes,
    conversation, followups, interaction_store as state, publication, spoken_briefing,
    telegram_buttons, voice_relay as relay)
from integrations.msty.personal.language import detect
from integrations.msty.personal.digest import personal_digest, units
from integrations.msty.personal.connectors import TZ, calendar_events
from voice.text_normalization import normalize_for_speech

NOW = datetime(2026, 10, 11, 10, tzinfo=TZ)
ROUTE = {'chat_id': '42', 'token': 'dummy'}


@pytest.fixture(autouse=True)
def private(tmp_path, monkeypatch):
    monkeypatch.setattr(state.store, 'ROOT', tmp_path/'runtime')
    monkeypatch.setattr(publication, 'VAULT', tmp_path/'vault')
    monkeypatch.setattr(state.store, 'load', lambda: {'accounts': []})
    return tmp_path


def event(uid='meeting', time='14:00', day=11, **fields):
    return {'uid': uid, 'recurrence_id': '', 'title': 'Project review', 'status': '',
            'start': f'2026-10-{day:02d}T{time}:00+02:00',
            'end': f'2026-10-{day:02d}T15:00:00+02:00', 'all_day': False,
            'location': 'Example room', **fields}


def source(events, **fields):
    return {'id': 'calendar', 'kind': 'calendar', 'label': 'Calendar', 'status': 'ok',
            'source_key': 'same-source', 'complete': True, 'events': events, **fields}


def receipt(snapshot=None, items=(), status='delivered', name='baseline', target=None):
    value = {'status': status, 'generated_at': NOW.isoformat(), 'followups': list(items),
             'target_hash': target or state.owner(ROUTE)}
    if snapshot:
        value['calendar_snapshot'] = snapshot
        value['generated_at'] = snapshot['generated_at']
    path = publication.VAULT/'Deliveries'/(name+'.json')
    publication.atomic(path, json.dumps(value))
    return value


def message(text='', uid=100, **fields):
    return {'message_id': uid, 'text': text, 'chat': {'id': 42, 'type': 'private'},
            'from': {'id': 42}, **fields}


@pytest.mark.parametrize(('text', 'hint', 'expected'), [
    ('What is next?', None, 'en'), ('¿Qué sigue?', None, 'es'), ('Dónde es mi reunión', None, 'es'),
    ('Remind me tomorrow', None, 'en'), ('Recuérdamelo mañana', None, 'es'),
    ('No hagas cambios', None, 'es'), ('Muestra mi agenda en inglés', 'es', 'en'),
    ('What is next, in Spanish', 'en', 'es'), ('2', 'es', 'es'), ('2', None, 'en'),
])
def test_language_detection(text, hint, expected):
    assert detect(text, hint) == expected


@pytest.mark.parametrize('query', ['¿Qué sigue?', 'Cuál es mi próxima reunión', 'Muestra mi agenda hoy'])
def test_spanish_calendar_queries_preserve_titles_and_hide_locations(monkeypatch, query):
    monkeypatch.setattr(agenda.store, 'load', lambda: {'accounts': [dict(id='calendar', label='Calendar', kind='calendar', enabled=True)]})
    monkeypatch.setattr(agenda, 'calendar_events', lambda *a: {'events': [event()], 'warnings': []})
    answer = agenda.answer(query, NOW)
    assert 'Project review' in answer and 'Example room' not in answer
    assert ('Próximo:' in answer or 'Domingo' in answer) and 'No overlaps' not in answer


def test_spanish_location_missing_and_ambiguity(monkeypatch):
    data = [event(location='')]
    monkeypatch.setattr(agenda.store, 'load', lambda: {'accounts': [dict(id='calendar', label='Calendar', kind='calendar', enabled=True)]})
    monkeypatch.setattr(agenda, 'calendar_events', lambda *a: {'events': data, 'warnings': []})
    assert 'No hay ubicación registrada' in agenda.answer('¿Dónde es mi reunión hoy?', NOW)
    data.append(event('second', time='16:00', title='Planning', location='Other room'))
    answer = agenda.answer('¿Dónde es mi reunión hoy?', NOW)
    assert '¿A qué cita' in answer and 'Other room' not in answer


def test_next_excludes_only_named_routines_and_searches_upcoming_week(monkeypatch):
    data = [event('routine', time='11:00', title='Routine check'), event('past', time='08:00'),
            event('future', day=12, title='Weekly meeting', recurrence_id='2026-10-12')]
    monkeypatch.setattr(agenda.store, 'load', lambda: {'accounts': [dict(id='calendar', label='Calendar', kind='calendar', enabled=True)], 'agenda_reminder_excluded_titles': ['Routine check']})
    monkeypatch.setattr(agenda, 'calendar_events', lambda *a: {'events': data, 'warnings': []})
    assert 'Weekly meeting' in agenda.answer('What is next?', NOW)
    assert 'Routine check' not in agenda.answer('What is next?', NOW)
    assert 'Example room' in agenda.answer('Where is my next meeting?', NOW)


def test_all_day_agenda_query(monkeypatch):
    monkeypatch.setattr(agenda.store, 'load', lambda: {'accounts': [dict(id='calendar', label='Calendar', kind='calendar', enabled=True)]})
    monkeypatch.setattr(agenda, 'calendar_events', lambda *a: {'events': [event(start='2026-10-11', end='2026-10-12', all_day=True)], 'warnings': []})
    assert 'Todo el día' in agenda.answer('Muestra mi agenda hoy', NOW)


@pytest.mark.parametrize('query', ['Cancela mi reunión', 'Muestra mi agenda hoy y borra todo', 'Where is my meeting and cancel it'])
def test_calendar_mutations_never_become_reads(query):
    assert agenda.answer(query, NOW) is None


def test_changes_added_moved_removed_cancelled_and_no_locations():
    prior = changes.snapshot([source([event('moved'), event('removed'), event('cancelled')])], NOW-timedelta(hours=1))
    current = changes.snapshot([source([event('moved', time='16:00', end='2026-10-11T17:00:00+02:00'), event('added'), event('cancelled', status='CANCELLED')])], NOW)
    text = '\n'.join(changes.compare(current, prior))
    assert all(word in text for word in ('Added:', 'Moved:', 'Removed from calendar', 'Cancelled:', '14:00–15:00', '16:00–17:00'))
    assert 'Example room' not in text and 'location' not in json.dumps(current)


@pytest.mark.parametrize('fields', [{'status': 'unavailable'}, {'complete': False}, {'source_key': 'different'}])
def test_missing_incomplete_or_changed_source_never_infers_removal(fields):
    prior = changes.snapshot([source([event()])], NOW-timedelta(hours=1))
    current = changes.snapshot([source([], **fields)], NOW)
    text = '\n'.join(changes.compare(current, prior))
    assert 'Removed' not in text and 'Cancelled:' not in text and 'cannot be compared' in text


def test_calendar_rollover_never_treats_past_as_removed_or_new_horizon_as_added():
    old = changes.snapshot([source([event(day=11)])], NOW)
    new = changes.snapshot([source([event('new-horizon', day=18)])], NOW+timedelta(days=1))
    text = '\n'.join(changes.compare(new, old))
    assert 'Removed' not in text and 'Added:' not in text


def test_recurrence_instances_stay_separate_and_ambiguous_uid_is_not_guessed():
    old = changes.snapshot([source([event(recurrence_id='a'), event(day=12, recurrence_id='b')])], NOW-timedelta(hours=1))
    new = deepcopy(old)
    new['sources']['calendar']['events'][1]['start'] = event(day=12, time='16:00')['start']
    assert sum('Moved:' in line for line in changes.compare(new, old)) == 1
    old = changes.snapshot([source([event(), event(day=12)])], NOW-timedelta(hours=1))
    new = changes.snapshot([source([event(day=12)])], NOW)
    assert not any('Added:' in line or 'Removed' in line for line in changes.compare(new, old))


def test_routine_changes_are_omitted_and_spanish_output_is_localized():
    old = changes.snapshot([source([])], NOW-timedelta(hours=1))
    new = changes.snapshot([source([event(title='Routine check'), event('other', title='Planning')])], NOW)
    text = '\n'.join(changes.compare(new, old, excluded_titles=['Routine check'], lang='es'))
    assert 'Routine check' not in text and 'Añadido: Planning' in text and 'Added:' not in text


def test_baseline_only_uses_successful_delivery_for_same_owner():
    old = changes.snapshot([source([])], NOW-timedelta(days=1))
    fresh = changes.snapshot([source([event()])], NOW)
    receipt(old)
    receipt(fresh, status='awaiting_choice', name='offered')
    receipt(fresh, status='uncertain', name='uncertain')
    receipt(fresh, name='other-owner', target='different')
    assert changes.baseline(publication.VAULT, state.owner(ROUTE)) == old


def test_ics_expansion_preserves_recurrence_identity_and_complete_window(private):
    path = private/'source.ics'
    path.write_text('BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nUID:series\nDTSTART:20261011T120000Z\nDTEND:20261011T130000Z\nRRULE:FREQ=DAILY;COUNT=3\nSUMMARY:Series\nEND:VEVENT\nEND:VCALENDAR\n')
    result = calendar_events({'path': str(path)}, NOW, 'morning')
    assert len(result['events']) == 3 and result['complete']
    assert len({event['recurrence_id'] for event in result['events']}) == 3
    assert result['window_start'] < result['window_end'] and str(path) not in result['source_key']


def test_ics_nonrecurring_move_has_stable_identity_and_cancellation_is_separate(private):
    path = private/'source.ics'
    def write(time, status=''):
        path.write_text('BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nUID:single\nDTSTART:20261011T'+time+'00Z\nDTEND:20261011T170000Z\nSUMMARY:Review\n'+status+'END:VEVENT\nEND:VCALENDAR\n')
    write('1200')
    before = calendar_events({'path': str(path)}, NOW, 'morning')
    write('1400')
    after = calendar_events({'path': str(path)}, NOW, 'morning')
    assert before['events'][0]['recurrence_id'] == after['events'][0]['recurrence_id'] == ''
    old = changes.snapshot([{**source([]), **before}], NOW-timedelta(hours=1))
    new = changes.snapshot([{**source([]), **after}], NOW)
    assert any('Moved:' in line for line in changes.compare(new, old))
    write('1400', 'STATUS:CANCELLED\n')
    cancelled = calendar_events({'path': str(path)}, NOW, 'morning')
    assert not cancelled['events'] and len(cancelled['cancelled_events']) == 1
    new = changes.snapshot([{**source([]), **cancelled}], NOW)
    assert any('Cancelled:' in line for line in changes.compare(new, old))


def test_specific_followup_handled_without_suppressing_other_items():
    data = followups.items([], ['First task', 'Second task'], NOW)
    receipt(items=data)
    result = followups.answer(message('I have handled this'), ROUTE, 'en', 'one', now=NOW)
    assert len(result['items']) == 2 and 'Which follow-up' in result['text']
    state.bind(ROUTE, {}, 500, [item['id'] for item in data])
    result = followups.answer(message('handled 1', reply_to_message={'message_id': 500}), ROUTE, 'en', 'two', now=NOW)
    assert 'First task' in result['text']
    remaining = followups.items([], ['First task', 'Second task'], NOW)
    assert [item['title'] for item in remaining] == ['Second task']


def test_tomorrow_uses_madrid_day_and_retry_does_not_extend_snooze():
    now = datetime(2026, 10, 24, 22, 30, tzinfo=timezone.utc)  # local Oct 25, before DST fallback
    item = followups.items([], ['First task'], now)[0]
    result = state.mutate(item['id'], 'tomorrow', 'same-update', now, 'es')
    assert 'informe de mañana' in result
    assert not state.visible(item['id'], now)
    next_day = datetime(2026, 10, 26, 7, tzinfo=TZ)
    assert state.visible(item['id'], next_day)
    assert state.mutate(item['id'], 'tomorrow', 'same-update', next_day, 'es') == result
    assert state.visible(item['id'], next_day)


def test_new_email_same_subject_not_suppressed():
    old = followups.mail_item({'id': 'mail'}, {'message_id': '<old@example.org>', 'subject': 'Planning'})
    new = followups.mail_item({'id': 'mail'}, {'message_id': '<new@example.org>', 'subject': 'Planning'})
    state.register([old, new], NOW)
    state.mutate(old['id'], 'handled', 'one', NOW, 'en')
    assert not state.visible(old['id'], NOW) and state.visible(new['id'], NOW)


def test_number_without_reply_context_never_mutates():
    item = followups.items([], ['First task'], NOW)[0]
    receipt(items=[item])
    result = followups.answer(message('handled 1'), ROUTE, 'en', 'one', now=NOW)
    assert 'Reply to the follow-up list' in result['text'] and state.visible(item['id'], NOW)


def test_natural_typographic_apostrophe_in_handled_reply():
    item = followups.items([], ['First task'], NOW)[0]
    receipt(items=[item])
    state.bind(ROUTE, {}, 500, [item['id']])
    response = followups.answer(message('I’ve handled this.', reply_to_message={'message_id': 500}), ROUTE, 'en', 'one', now=NOW)
    assert 'stop reminding' in response['text'] and not state.visible(item['id'], NOW)


def callback(markup, message_id=500, sender=42):
    return {'id': 'callback', 'data': markup['inline_keyboard'][0][0]['callback_data'],
            'from': {'id': sender}, 'message': {'message_id': message_id, 'chat': {'id': 42, 'type': 'private'}}}


def test_buttons_are_opaque_expiring_owner_and_message_bound():
    markup = state.keyboard(ROUTE, [[('Handled', 'handled', {'id': 'private-item'})]], now=NOW)
    token = markup['inline_keyboard'][0][0]['callback_data']
    assert len(token.encode()) <= 64 and 'private-item' not in token and '42' not in token[:3]
    assert state.resolve(ROUTE, callback(markup), now=NOW) is None
    state.bind(ROUTE, markup, 500)
    assert state.resolve(ROUTE, callback(markup), now=NOW) == ('handled', {'id': 'private-item'})
    assert state.resolve(ROUTE, callback(markup, sender=12), now=NOW) is None
    assert state.resolve(ROUTE, callback(markup, message_id=501), now=NOW) is None
    assert state.resolve(ROUTE, callback(markup), now=NOW+timedelta(hours=19)) is None


def test_delivery_keyboard_binds_only_after_acknowledgement(private, monkeypatch):
    value = {'status': 'prepared', 'interactive': True, 'message_ids': []}
    def transport(route, method, data):
        cb = callback(data['reply_markup'], message_id=600)
        assert state.resolve(route, cb) is None
        return {'chat': {'id': 42}, 'message_id': 600}
    monkeypatch.setattr(publication, 'telegram_call', transport)
    publication.deliver('Briefing text', value, private/'receipt.json', ROUTE)
    assert state.resolve(ROUTE, callback(value['reply_markup'], message_id=600))[0] == 'choice'


def row(uid):
    with relay.database() as db:
        return dict(db.execute('SELECT * FROM inbox WHERE update_id=?', (uid,)).fetchone())


def test_voice_and_text_use_same_local_router_and_transcribe_only_once(monkeypatch):
    voice = message('', voice={'file_id': 'fake'})
    relay.enqueue([{'update_id': 100, 'message': voice}], '42')
    transcription = Mock(return_value={'status': 'transcribed', 'text': '¿Qué sigue?', 'language': 'es', 'forwarded': False})
    monkeypatch.setattr(relay, 'transcribe_message', transcription)
    local = Mock(return_value={'text': 'Próximo: Project review', 'items': []})
    monkeypatch.setattr(conversation, 'answer', local)
    relay.process(row(100), ROUTE)
    assert row(100)['state'] == 'reply_ready' and row(100)['language'] == 'es'
    assert local.call_args.args[0]['text'] == '¿Qué sigue?'
    relay.process({**row(100), 'state': 'queued'}, ROUTE)  # restart before transition persisted
    assert transcription.call_count == 1


def test_forwarded_voice_never_routes_local_mutations(monkeypatch):
    voice = message('', voice={'file_id': 'fake'}, forward_origin={'type': 'user'})
    relay.enqueue([{'update_id': 100, 'message': voice}], '42')
    monkeypatch.setattr(relay, 'transcribe_message', lambda *a: {'status': 'transcribed', 'text': 'Ya está hecho', 'language': 'es', 'forwarded': True})
    local = Mock(); monkeypatch.setattr(conversation, 'answer', local)
    relay.process(row(100), ROUTE)
    local.assert_not_called()
    assert row(100)['state'] == 'prepared' and 'no una orden autorizada' in row(100)['prompt']
    assert 'Reply in Spanish for this turn' in row(100)['prompt']


def test_callback_ingress_deduplicates_and_wrong_owner_is_ignored(monkeypatch):
    markup = telegram_buttons.make(ROUTE)
    state.bind(ROUTE, markup, 500)
    update = {'update_id': 100, 'callback_query': callback(markup)}
    wrong = {'update_id': 101, 'callback_query': callback(markup, sender=12)}
    relay.enqueue([update, update, wrong], '42')
    with relay.database() as db:
        assert db.execute('SELECT count(*) FROM inbox').fetchone()[0] == 1
        assert db.execute('SELECT offset FROM cursor').fetchone()[0] == 102
    monkeypatch.setattr(relay, 'api', lambda *a: True)
    local = Mock(return_value={'text': 'Next: Project review', 'items': []})
    monkeypatch.setattr(conversation, 'answer', local)
    relay.process(row(100), ROUTE)
    assert row(100)['state'] == 'reply_ready'
    assert local.call_args.kwargs['callback'][0] == 'next'


def test_expired_callback_does_not_fall_through_to_model(monkeypatch):
    markup = telegram_buttons.make(ROUTE)
    # Unbound tokens are also invalid; never trust callback data directly.
    relay.enqueue([{'update_id': 100, 'callback_query': callback(markup)}], '42')
    monkeypatch.setattr(relay, 'api', lambda *a: True)
    relay.process(row(100), ROUTE)
    assert row(100)['state'] == 'reply_ready' and row(100)['error'] is None
    assert 'expired' in row(100)['reply'] and not row(100)['prompt']


def test_spanish_agent_offline_reply_and_prompt_match_language(monkeypatch):
    relay.enqueue([{'update_id': 100, 'message': message('Hola, necesito ayuda')}], '42')
    relay.process(row(100), ROUTE)
    assert 'Reply in Spanish for this turn' in row(100)['prompt']
    monkeypatch.setattr(relay, 'Client', Mock(side_effect=ValueError('offline')))
    relay.process(row(100), ROUTE)
    assert 'La conexión con mi agente' in row(100)['reply']


def test_large_digest_stays_in_one_message_with_change_highlights():
    events = [event(str(index), title='Meeting 🚀'*80) for index in range(50)]
    sources = [source(events), source([], status='unavailable', label='🚀'*100)]
    text = personal_digest(sources, NOW, ['Task 🚀'*80 for _ in range(30)], changes=['- Added: 🚀'*80]*30)
    assert units(text) <= 4096 and all(title in text for title in ('SAVED TASKS', 'EMAIL', 'AGENDA', 'CHANGES', 'OVERLAPS'))


def test_control_layer_suppresses_only_summary_keeps_sources():
    tasks = ['First task', 'Second task']
    first = followups.items([], tasks, NOW)[0]
    state.mutate(first['id'], 'handled', 'one', NOW, 'en')
    summary = personal_digest([], NOW, tasks, controlled=True)
    assert 'First task' not in summary and 'Second task' in summary
    assert tasks == ['First task', 'Second task']


def test_spanish_speech_keeps_numbers_language_and_natural_punctuation():
    text = spoken_briefing.narration('Próximo · 12/10 14:00: Project review — no confirmado.', 'es')
    speech = normalize_for_speech(text, lang='es')
    assert '12 de octubre a las catorce en punto' in speech and 'Project review' in speech
    assert 'fourteen' not in speech and 'over' not in speech and '—' not in speech
    assert normalize_for_speech('09:00–11:00; −2; 1/2', lang='es') == 'nueve en punto a once en punto; menos 2; 1 entre 2'


@pytest.mark.parametrize(('language', 'expected'), [('en', 'the twelfth of October'), ('es', '12 de octubre')])
def test_narration_reads_bare_publisher_dates(language, expected):
    text = spoken_briefing.narration('AGENDA · 12/10\n- Project review.', language)
    assert expected in text and 'over' not in text and 'entre' not in text
