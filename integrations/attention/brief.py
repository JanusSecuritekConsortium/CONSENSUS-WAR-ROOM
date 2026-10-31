"""One short attention brief: what needs the user, not everything that happened."""
from __future__ import annotations

from datetime import datetime

from . import priority, store

SECTION_LIMIT = 6


def when(item: dict, now: datetime) -> str:
    if item['overdue'] and item['kind'] == 'reply':
        return priority.age_text(now - store.parse(item['first_seen_at'])) + ' waiting, overdue'
    if item['overdue']:
        return next((r for r in item['priority_reasons'] if r.startswith('due')), 'overdue')
    return priority.age_text(now - store.parse(item['first_seen_at']))


def event_text(event: dict, settings: dict) -> str:
    parts = []
    if event.get('date'):
        parts.append(datetime.strptime(event['date'], '%Y-%m-%d').strftime('%a %d %b'))
    parts.append(event['time'] if event.get('time') else 'time not confirmed')
    if event.get('availability') == 'free':
        parts.append('appears free')
    elif event.get('availability') == 'busy':
        parts.append('clashes with ' + event.get('availability_detail', 'another event'))
    return ' · '.join(parts)


def line(item: dict, names: dict, now: datetime, settings: dict) -> list[str]:
    name = names.get(item['contact_id'], 'Someone')
    head = f'{name} · {item["channel"].capitalize()} · {when(item, now)}'
    body = item['summary']
    if item['kind'] == 'appointment' and item.get('event'):
        body += ' ' + event_text(item['event'], settings) + '.'
    lines = [head, '  ' + body]
    if item.get('draft'):
        lines.append('  Draft (not sent): ' + ' / '.join(item['draft'].splitlines())[:300])
    return lines


def section(title: str, items: list[dict], render) -> list[str]:
    if not items:
        return []
    lines = ['', title]
    for item in items[:SECTION_LIMIT]:
        lines += render(item)
    if len(items) > SECTION_LIMIT:
        lines.append(f'  + {len(items) - SECTION_LIMIT} more (see the attention folder)')
    return lines


def build(items: list[dict], names: dict, now: datetime, settings: dict, status_line: str = '') -> str:
    local = now.astimezone(settings['tz'])
    active = [i for i in items if i['state'] in store.OPEN and not priority.quiet(i)]
    attention = [i for i in active if i['kind'] in ('reply', 'commitment', 'appointment') and not i['review']]
    urgent = [i for i in attention if i['priority'] in ('URGENT', 'HIGH')]
    normal = [i for i in attention if i['priority'] in ('NORMAL', 'LOW') and i['kind'] == 'reply']
    review = [i for i in active if i['review'] and i['kind'] != 'waiting']
    commitments = [i for i in active if i['kind'] == 'commitment' and not i['review']]
    upcoming = [i for i in active if i['kind'] == 'appointment' and not i['review']]
    waiting = [i for i in active if i['kind'] == 'waiting']
    stale = [i for i in waiting if i['priority'] != 'LOW']

    lines = [f'PERSONAL ATTENTION — {local.strftime("%a %d %b, %H:%M")}']
    render = lambda item: line(item, names, now, settings)
    lines += section('HIGH', urgent, render)
    lines += section('NEEDS A REPLY', normal, render)
    lines += section('TO CONFIRM (not sure these need you)', review, render)

    def commitment(item):
        due = item['due_at'] or item['due_text'] or 'no date'
        if item['overdue']:
            due = next((r for r in item['priority_reasons'] if r.startswith('due')), 'overdue')
        return [f'• {item["title"]} — {due}']
    lines += section('OPEN COMMITMENTS', commitments, commitment)
    lines += section('UPCOMING', upcoming,
                     lambda i: [f'• {i["title"]} — {event_text(i.get("event") or {}, settings)}'])
    if waiting:
        text = f'{len(waiting)} conversation' + ('s' if len(waiting) != 1 else '') + ' waiting on others; no action needed.'
        if stale:
            text += ' No answer yet from ' + ', '.join(names.get(i['contact_id'], 'someone') for i in stale[:4]) + '.'
        lines += ['', 'WAITING ON OTHERS', text]
    if len(lines) == 1:
        lines += ['', 'Nothing needs you right now.']
    if status_line:
        lines += ['', status_line]
    return '\n'.join(lines)


def status_line(meta: dict, settings: dict) -> str:
    scan = meta.get('last_scan') or {}
    if not scan:
        return 'No scan has run yet.'
    sources = scan.get('sources', {})
    mail = [s for k, s in sources.items() if k.startswith('email:')]
    ok = sum(1 for s in mail if s['status'] == 'ok')
    finished = store.parse(scan.get('finished_at') or scan['started_at']).astimezone(settings['tz'])
    text = f'Email {ok}/{len(mail)} accounts read'
    for channel in ('telegram', 'whatsapp'):
        if channel in sources:
            text += f' · {channel.capitalize()} {sources[channel]["status"]}'
    text += f' · last scan {finished.strftime("%d %b %H:%M")}'
    if scan.get('msty') == 'unavailable':
        text += ' · Msty unavailable, some conversations not yet analysed'
    elif scan.get('pending'):
        text += f' · {scan["pending"]} conversations still to analyse'
    return text

