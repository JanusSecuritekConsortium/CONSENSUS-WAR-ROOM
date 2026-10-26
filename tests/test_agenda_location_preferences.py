"""Agenda locations are optional presentation data, preserved for explicit queries."""
from datetime import datetime
from copy import deepcopy
from unittest.mock import patch

import pytest

from integrations.msty.personal import agenda_query as q, review
from integrations.msty.personal.context import agenda
from integrations.msty.personal.digest import personal_digest


NOW = datetime(2026, 10, 11, 10, tzinfo=q.TZ)


def event(title='Project review', location='Example meeting room', start='14:00', end='15:00'):
    return {'uid': title, 'title': title, 'location': location,
            'start': '2026-10-11T'+start+':00+02:00', 'end': '2026-10-11T'+end+':00+02:00'}


def sources(events):
    return [{'id': 'cal', 'label': 'Calendar', 'status': 'ok', 'events': events}]


@pytest.fixture
def calendar(monkeypatch):
    data = [event()]
    config = {'accounts': [{'id': 'cal', 'label': 'Calendar', 'kind': 'calendar', 'enabled': True}],
              'agenda_include_locations_by_default': False, 'agenda_reminder_excluded_titles': ['Routine check']}
    monkeypatch.setattr(q.store, 'load', lambda: config)
    monkeypatch.setattr(q, 'calendar_events', lambda *a: {'events': data, 'warnings': []})
    return data


def test_reminders_hide_location_without_modifying_source():
    data = sources([event()])
    original = deepcopy(data)
    assert 'Example meeting room' not in '\n'.join(agenda(data))
    assert 'Example meeting room' not in personal_digest(data, NOW, tasks=[])
    assert 'Example meeting room' in '\n'.join(agenda(data, include_locations=True))
    assert data == original


def test_general_schedule_reply_does_not_disclose_location(calendar):
    body = q.answer('Show my agenda today', NOW)
    assert 'Project review' in body and '14:00' in body
    assert 'Example meeting room' not in body


@pytest.mark.parametrize('query', ['Where is my meeting today?', 'Where is Project review today?',
                                 'Show my schedule today with locations'])
def test_explicit_location_request_returns_recorded_location(calendar, query):
    assert 'Example meeting room' in q.answer(query, NOW)


def test_missing_location_is_reported_without_guessing(calendar):
    calendar[0]['location'] = ''
    assert 'No location is recorded' in q.answer('Where is my meeting today?', NOW)


def test_ambiguous_singular_location_question_asks_which_meeting(calendar):
    calendar.append(event('Planning meeting', 'Other meeting room', '16:00', '17:00'))
    body = q.answer('Where is my meeting today?', NOW)
    assert 'Which appointment' in body
    assert 'Project review' in body and 'Planning meeting' in body
    assert 'Example meeting room' not in body and 'Other meeting room' not in body


def test_plural_location_question_can_list_locations(calendar):
    calendar.append(event('Planning meeting', 'Other meeting room', '16:00', '17:00'))
    body = q.answer('Where are my meetings today?', NOW)
    assert 'Example meeting room' in body and 'Other meeting room' in body


def test_routine_exclusion_does_not_hide_an_explicit_named_location(calendar):
    calendar.append(event('Routine check', 'Routine meeting room', '08:00', '08:15'))
    assert 'Example meeting room' in q.answer('Where is my meeting today?', NOW)
    assert 'Routine meeting room' in q.answer('Where is Routine check today?', NOW)


def test_title_words_do_not_change_requested_day_or_period(calendar):
    calendar[0]['title'] = 'Tomorrow morning review'
    body = q.answer('Where is Tomorrow morning review today?', NOW)
    assert 'Example meeting room' in body


def test_mutation_request_is_not_answered_as_just_a_location_query():
    assert q.answer('Where is my meeting today and cancel it') is None


def test_build_keeps_location_in_private_details_and_omits_it_from_reminder():
    config = {'accounts': [], 'agenda_include_locations_by_default': False}
    with patch.object(review, 'load', return_value=config), patch.object(review, 'collect', return_value=sources([event()])), \
            patch('integrations.msty.personal.publication.saved_tasks', return_value=[]):
        report = review.build('morning')
    assert 'Example meeting room' not in report['telegram_text']
    assert 'Example meeting room' in report['body_text'].split('DETAILS AND SOURCES', 1)[1]
