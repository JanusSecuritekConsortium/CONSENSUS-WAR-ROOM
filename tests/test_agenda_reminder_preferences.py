"""Private reminder preferences omit named routines, not every recurring event."""
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import patch

from integrations.msty.personal.context import agenda
from integrations.msty.personal.digest import personal_digest
from integrations.msty.personal import review


NOW = datetime(2026, 10, 11, 5, tzinfo=timezone.utc)


def event(title, start='08:00', end='08:15', day=11):
    return {'uid': title+str(day), 'title': title, 'start': f'2026-10-{day:02}T{start}:00+02:00',
            'end': f'2026-10-{day:02}T{end}:00+02:00', 'all_day': False, 'recurring': True}


def sources(events):
    return [{'id': 'calendar', 'label': 'Calendar', 'status': 'ok', 'events': events}]


def test_exact_normalized_titles_only_and_sources_unchanged():
    data = sources([event('Routine   check'), event('Routine check with advisor', '10:00', '11:00'),
                    event('Weekly review', '15:00', '16:00')])
    original = deepcopy(data)
    text = '\n'.join(agenda(data, excluded_titles=[' ROUTINE CHECK ']))
    assert '08:00' not in text
    assert 'Routine check with advisor' in text and 'Weekly review' in text
    assert data == original
    assert '08:00–08:15: Routine check' in '\n'.join(agenda(data))


def test_routine_overlaps_keep_other_appointment_warning_without_private_title():
    text = '\n'.join(agenda(sources([event('Routine block', '12:00', '14:00'),
                                     event('Project meeting', '13:00', '13:30')]),
                            excluded_titles=['Routine block']))
    assert 'Routine block' not in text
    assert '13:00–13:30: Project meeting' in text
    assert 'routine calendar block ↔ Project meeting' in text


def test_only_excluded_events_do_not_imply_empty_calendar_or_announce_routine_conflicts():
    data = sources([event('Routine block', '12:00', '14:00'), event('Routine check', '13:00', '13:30')])
    text = personal_digest(data, NOW, tasks=[], excluded_titles=['Routine block', 'Routine check'])
    assert 'No other appointments to remind you about' in text
    assert 'Routine block' not in text and 'Routine check' not in text and '↔' not in text


def test_exclusion_before_digest_budget_preserves_later_appointments():
    data = sources([event('Routine block '+str(i), '08:00', '08:01', day=11+i//10) for i in range(60)]
                   +[event('Important appointment', '17:00', '18:00', day=17)])
    excluded = ['Routine block '+str(i) for i in range(60)]
    assert 'Important appointment' not in personal_digest(data, NOW, tasks=[])
    filtered = personal_digest(data, NOW, tasks=[], excluded_titles=excluded)
    assert 'Important appointment' in filtered and 'Routine block' not in filtered
    assert 'Sunday 11/10' not in filtered  # No empty day headings.


def test_build_applies_private_config_to_reminder_and_keeps_detailed_agenda():
    config = {'accounts': [], 'agenda_reminder_excluded_titles': ['Routine check']}
    data = sources([event('Routine check'), event('Project meeting', '10:00', '11:00')])
    with patch.object(review, 'load', return_value=config), patch.object(review, 'collect', return_value=data), \
            patch('integrations.msty.personal.publication.saved_tasks', return_value=[]):
        report = review.build('morning')
    assert 'Routine check' not in report['telegram_text']
    assert 'Project meeting' in report['telegram_text']
    assert 'Routine check' in report['body_text'].split('DETAILS AND SOURCES', 1)[1]
