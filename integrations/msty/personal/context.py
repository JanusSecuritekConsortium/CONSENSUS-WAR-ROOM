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


def agenda(results):
    days = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
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
    lines, day = [], None
    for start, end, source, event in events:
        if day != start.date():
            day = start.date()
            lines.extend(['', days[start.weekday()].capitalize()+' '+start.strftime('%d/%m')])
        when = 'All day' if event.get('all_day') else start.strftime('%H:%M')
        if not event.get('all_day'):
            when += ('–'+end.strftime('%H:%M' if end.date() == start.date() else '%d/%m %H:%M')) if end else ' (end time not provided)'
        elif event.get('end'):
            last = datetime.fromisoformat(event['end']).date()-timedelta(days=1)
            if last > start.date():
                when += ' through '+last.strftime('%d/%m')
        location = ' · '+clean(event['location']) if event.get('location') else ''
        lines.append('- '+when+': '+event_title(event)+location+' ['+clean(source['label'])+']')
    if not events:
        lines.append('No events retrieved for this period; check source coverage.')
    conflicts = []
    for i, (start, end, source, event) in enumerate(events):
        if not end or end <= start or event.get('all_day') or event.get('transparent'):
            continue
        for other_start, other_end, other_source, other in events[i+1:]:
            if other_start >= end:
                break
            if not other_end or other_end <= other_start or other.get('all_day') or other.get('transparent'):
                continue
            if start < other_end and other_start < end:
                conflicts.append('- '+days[other_start.weekday()].capitalize()+' '+other_start.strftime('%d/%m')+' '+
                    max(start, other_start).strftime('%H:%M')+'–'+min(end, other_end).strftime('%H:%M')+': '+
                    event_title(event)+' ↔ '+event_title(other)+'. Check whether the overlap is intentional.')
    lines.extend(['', 'SCHEDULE OVERLAPS']+conflicts if conflicts else
                 ['', 'No overlaps detected between events with known start and end times.'])
    if any('does not share the title' in event_title(e) for _, _, _, e in events):
        lines.append('Event names are missing from the source: share full calendar details or use an ICS export with titles to identify them.')
    lines.append('Events without an end time, all-day events and events marked as available are excluded from conflict checks. Calendar entries do not confirm attendance.')
    return lines
