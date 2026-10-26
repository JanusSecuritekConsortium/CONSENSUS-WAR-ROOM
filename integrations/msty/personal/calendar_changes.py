"""Calendar observations compared only with acknowledged briefing snapshots."""
from datetime import datetime
import json
from .connectors import calendar_window, TZ
from .context import clean
from .language import choose


def snapshot(results, now, mode='morning'):
    start, end = calendar_window(now, mode)
    sources = {}
    for source in results:
        if source.get('kind') != 'calendar' and 'events' not in source:
            continue
        sources[source['id']] = {
            'status': source['status'], 'source_key': source.get('source_key'),
            'complete': source.get('complete', False),
            'start': source.get('window_start', start.isoformat()),
            'end': source.get('window_end', end.isoformat()),
            'events': [{k: event.get(k) for k in ('uid', 'recurrence_id', 'start', 'end', 'title', 'status', 'all_day')}
                       for event in source.get('events', [])+source.get('cancelled_events', [])],
        }
    return {'generated_at': now.isoformat(), 'sources': sources}


def baseline(vault, target_hash=None):
    receipts = []
    for path in (vault/'Deliveries').glob('*.json'):
        try:
            receipt = json.loads(path.read_text(encoding='utf-8'))
            snap = receipt.get('calendar_snapshot')
            if (receipt.get('status') == 'delivered' and snap
                    and (target_hash is None or receipt.get('target_hash') == target_hash)):
                datetime.fromisoformat(snap['generated_at'])
                receipts.append(snap)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return max(receipts, key=lambda snap: datetime.fromisoformat(snap['generated_at'])) if receipts else None


def identity(event):
    # Expanded recurrences keep RECURRENCE-ID when moved. Without it, repeated
    # UIDs are ambiguous and are excluded from comparison rather than guessed.
    return (event.get('uid'), event.get('recurrence_id') or '')


def indexed(events):
    groups = {}
    for event in events:
        if event.get('uid'):
            groups.setdefault(identity(event), []).append(event)
    return {key: values[0] for key, values in groups.items() if len(values) == 1}


def date_of(event):
    try:
        value = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
        return value.astimezone(TZ) if value.tzinfo else value.replace(tzinfo=TZ)
    except (ValueError, TypeError, KeyError):
        return None


def when(event):
    stamp = date_of(event)
    value = stamp.strftime('%d/%m'+('' if event.get('all_day') else ' %H:%M')) if stamp else '?'
    if not event.get('all_day') and event.get('end'):
        end = date_of({'start': event['end']})
        if end:
            value += '–'+end.strftime('%H:%M' if stamp and stamp.date()==end.date() else '%d/%m %H:%M')
    return value


def compare(current, previous, *, excluded_titles=(), lang='en'):
    if not previous:
        return [choose(lang, 'Change tracking starts with the first delivered snapshot.',
                       'El seguimiento de cambios comienza con el primer informe entregado.')]
    excluded = {clean(title).casefold() for title in excluded_titles if isinstance(title, str)}
    lines, incomplete = [], False
    for source_id, new in current['sources'].items():
        old = previous['sources'].get(source_id)
        if (not old or new['status'] != 'ok' or old['status'] != 'ok'
                or not new.get('complete') or not old.get('complete')
                or not new.get('source_key') or new['source_key'] != old.get('source_key')):
            incomplete = True
            continue
        lower = max(datetime.fromisoformat(new['start']), datetime.fromisoformat(old['start']),
                    datetime.fromisoformat(current['generated_at']).astimezone(TZ))
        upper = min(datetime.fromisoformat(new['end']), datetime.fromisoformat(old['end']))
        if lower >= upper:
            incomplete = True
            continue
        before, after = indexed(old['events']), indexed(new['events'])
        ambiguous = {identity(event) for events in (old['events'], new['events']) for event in events
                     if sum(identity(other)==identity(event) for other in events)>1}
        before = {key: value for key, value in before.items() if key not in ambiguous}
        after = {key: value for key, value in after.items() if key not in ambiguous}
        if ambiguous:
            incomplete = True
        def eligible(event):
            stamp = date_of(event)
            return (stamp and lower <= stamp < upper and clean(event.get('title', '')).casefold() not in excluded)
        for key in sorted(before.keys() | after.keys()):
            prior, event = before.get(key), after.get(key)
            if event and (event.get('status') or '').upper() == 'CANCELLED':
                if prior and eligible(prior) and (prior.get('status') or '').upper() != 'CANCELLED':
                    lines.append(choose(lang, '- Cancelled: ', '- Cancelado: ')+clean(prior['title'])+' · '+when(prior))
            elif prior and event:
                if not (eligible(prior) or eligible(event)) or clean(event.get('title', '')).casefold() in excluded:
                    continue
                if prior['start'] != event['start'] or prior.get('end') != event.get('end'):
                    lines.append(choose(lang, '- Moved: ', '- Reprogramado: ')+clean(event['title'])+' · '+when(prior)+' → '+when(event))
                elif clean(prior['title']) != clean(event['title']):
                    lines.append(choose(lang, '- Renamed: ', '- Nombre cambiado: ')+clean(prior['title'])+' → '+clean(event['title']))
            elif event and eligible(event):
                lines.append(choose(lang, '- Added: ', '- Añadido: ')+clean(event['title'])+' · '+when(event))
            elif prior and eligible(prior) and (prior.get('status') or '').upper() != 'CANCELLED':
                lines.append(choose(lang, '- Removed from calendar (cancellation unconfirmed): ',
                                    '- Retirado del calendario (cancelación sin confirmar): ')+clean(prior['title'])+' · '+when(prior))
    if not lines:
        lines.append(choose(lang, 'No changes detected in comparable future appointments.',
                            'No se detectaron cambios en las citas futuras comparables.'))
    if incomplete:
        lines.append(choose(lang, 'Some calendars cannot be compared; unavailable data does not establish cancellations.',
                            'Algunos calendarios no se pueden comparar; los datos no disponibles no confirman cancelaciones.'))
    return lines
