"""Evidence-based mail priority and human-readable calendar summaries."""
from datetime import datetime, timedelta
from email.utils import getaddresses
import re
from .connectors import TZ


def stamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.astimezone(TZ) if parsed.tzinfo else None
    except (ValueError, TypeError, AttributeError):
        return None


def addresses(value):
    return {address.casefold() for _, address in getaddresses([value or '']) if '@' in address}


def mail_context(messages, now):
    from .review import request_evidence, ACTION_REQUIRED
    sent = [m for m in messages if m.get('direction') == 'sent' and stamp(m.get('date'))]
    priority, low = [], []
    for message in messages:
        received = stamp(message.get('date'))
        if message.get('direction') != 'inbox' or message.get('bulk') or not received or received > now:
            continue
        evidence = request_evidence(message)
        urgent = bool(ACTION_REQUIRED.search(message.get('subject', '')))
        if not evidence and not urgent:
            continue
        mid = message.get('message_id')
        # A sent response is evidence of a response, never of task completion.
        replied = any(stamp(r['date']) >= received and (
            (mid and mid in re.findall(r'<[^>]+>', r.get('references', ''))) or
            (message.get('conversation_id') and message['conversation_id'] == r.get('conversation_id'))
        ) for r in sent)
        if replied:
            continue
        sender = addresses(message.get('from'))
        previous = [r for r in sent if stamp(r['date']) < received and sender & addresses(r.get('to'))]
        reason = ('There are '+str(len(previous))+' earlier emails from you to this sender; the latest was on '+
                  max(stamp(r['date']) for r in previous).strftime('%d/%m')+'.' if previous
                  else 'No earlier exchange appears in the reviewed window; this may not interest you (inference).')
        item = {'message': message, 'reason': reason, 'evidence': evidence or 'Explicit action notice in the subject',
                'urgent': urgent, 'previous_outgoing': len(previous)}
        (priority if previous or urgent else low).append(item)
    priority.sort(key=lambda item: (not item['urgent'], -stamp(item['message']['date']).timestamp()))
    return priority, low


def clean(value):
    return ' '.join(str(value).split())


def event_title(event):
    title = clean(event.get('title', ''))
    if title.casefold() in ('', 'busy', 'busy / no title', 'occupied', 'ocupado', 'private event'):
        return 'Busy (calendar does not share the title)'
    return title


def agenda(results, *, excluded_titles=(), include_locations=False, lang='en'):
    """Render an agenda; reminder exclusions hide titles, not occupied time."""
    if not isinstance(excluded_titles, (list, tuple, set)):
        excluded_titles = ()
    excluded = {clean(title).casefold() for title in excluded_titles if isinstance(title, str) and title.strip()}
    def omitted(event):
        return event_title(event).casefold() in excluded
    from .language import choose
    def shown_title(event):
        title = event_title(event)
        return choose(lang, title, 'Ocupado (el calendario no comparte el título)') if title == 'Busy (calendar does not share the title)' else title
    def conflict_title(event):
        return choose(lang, 'routine calendar block', 'bloque rutinario del calendario') if omitted(event) else shown_title(event)
    days = (('lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo') if lang == 'es' else
            ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'))
    events, seen = [], set()
    for source in results:
        if source.get('status') != 'ok':
            continue
        for event in source.get('events', []):
            start = stamp(event.get('start'))
            # All-day dates have no zone and no implied time.
            if event.get('all_day'):
                try:
                    start = datetime.fromisoformat(event['start']).replace(tzinfo=TZ)
                except (ValueError, KeyError):
                    continue
            if not start or event.get('status', '').upper() == 'CANCELLED':
                continue
            key = (event.get('uid') or source['id'] + event_title(event), event['start'])
            if key in seen:
                continue
            seen.add(key)
            events.append((start, stamp(event.get('end')), source, event))
    events.sort(key=lambda entry: entry[0])
    visible = [entry for entry in events if not omitted(entry[3])]
    lines, day = [], None
    for start, end, source, event in visible:
        if day != start.date():
            day = start.date()
            lines.extend(['', days[start.weekday()].capitalize()+' '+start.strftime('%d/%m')])
        when = choose(lang, 'All day', 'Todo el día') if event.get('all_day') else start.strftime('%H:%M')
        if not event.get('all_day'):
            when += ('–'+end.strftime('%H:%M' if end.date() == start.date() else '%d/%m %H:%M')) if end else choose(lang, ' (end time not provided)', ' (hora de finalización no disponible)')
        elif event.get('end'):
            last = datetime.fromisoformat(event['end']).date()-timedelta(days=1)
            if last > start.date():
                when += choose(lang, ' through ', ' hasta ')+last.strftime('%d/%m')
        location = ' · '+clean(event['location']) if include_locations and event.get('location') else ''
        lines.append('- '+when+': '+shown_title(event)+location+' ['+clean(source['label'])+']')
    if not visible:
        lines.append(choose(lang, 'No other appointments to remind you about in the retrieved calendar.',
                            'No hay otras citas que recordar en el calendario consultado.') if events else
                     choose(lang, 'No events retrieved for this period; check source coverage.',
                            'No se obtuvieron eventos para este período; revisa la cobertura de las fuentes.'))
    conflicts = []
    for i, (start, end, source, event) in enumerate(events):
        if not end or end <= start or event.get('all_day') or event.get('transparent'):
            continue
        for other_start, other_end, other_source, other in events[i+1:]:
            if other_start >= end:
                break
            if omitted(event) and omitted(other):
                continue
            if not other_end or other_end <= other_start or other.get('all_day') or other.get('transparent'):
                continue
            if start < other_end and other_start < end:
                conflicts.append('- '+days[other_start.weekday()].capitalize()+' '+other_start.strftime('%d/%m')+' '+
                    max(start, other_start).strftime('%H:%M')+'–'+min(end, other_end).strftime('%H:%M')+': '+
                    conflict_title(event)+' ↔ '+conflict_title(other)+choose(lang, '. Check whether the overlap is intentional.', '. Comprueba si el solapamiento es intencional.'))
    lines.extend(['', choose(lang, 'SCHEDULE OVERLAPS', 'SOLAPAMIENTOS DE HORARIO')]+conflicts if conflicts else
                 ['', choose(lang, 'No overlaps detected among the appointments included in this reminder.',
                             'No se detectaron solapamientos entre las citas de este recordatorio.') if len(visible) < len(events) else
                  choose(lang, 'No overlaps detected between events with known start and end times.',
                         'No se detectaron solapamientos entre eventos con horas de inicio y fin conocidas.')])
    if any('does not share the title' in event_title(e) for _, _, _, e in visible):
        lines.append(choose(lang, 'Event names are missing from the source: share full calendar details or use an ICS export with titles to identify them.',
                            'Faltan nombres en la fuente: comparte los detalles del calendario o utiliza una exportación ICS con títulos.'))
    lines.append(choose(lang, 'Events without an end time, all-day events and events marked as available are excluded from conflict checks. Calendar entries do not confirm attendance.',
                        'Los eventos sin hora de fin, de todo el día o marcados como disponibles no se comprueban para solapamientos. Las citas no confirman asistencia.'))
    return lines
