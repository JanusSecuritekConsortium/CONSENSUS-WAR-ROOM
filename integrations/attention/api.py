"""Query and update interface shared by the CLI, MCP tools, Msty Go, Aurelius and CONSENSUS.

Every mutation is validated in store.py and followed by a Markdown export.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import re

from . import classify, config, export, google_contacts, log, scan, store
from .store import (APPOINTMENT_PROPOSED, COMMITMENT_OPEN, NEEDS_REPLY, WAITING_ON_ME, WAITING_ON_OTHER)


def _now(now=None):
    return now or store.utcnow()


def _changed(settings, now):
    with store.connect() as db:
        scan.refresh(db, now, settings)
    export.write_all(settings, now)


def _items(**filters):
    settings = config.load()
    now = store.utcnow()
    with store.connect() as db:
        scan.refresh(db, now, settings)
        return store.query_items(db, **filters)


def get_attention_summary(now=None) -> dict:
    settings = config.load()
    now = _now(now)
    with store.connect() as db:
        scan.refresh(db, now, settings)
        data = export.snapshot(db, now, settings)
    return {'brief': export.current_brief(data, now, settings), 'counts': export.counts(data['items'])}


def get_pending_replies() -> list[dict]:
    return _items(kinds=['reply'], states=[NEEDS_REPLY, WAITING_ON_ME])


def get_overdue_items() -> list[dict]:
    return [item for item in _items() if item['overdue']]


def get_open_commitments() -> list[dict]:
    return _items(kinds=['commitment'], states=[COMMITMENT_OPEN])


def get_waiting_on_others() -> list[dict]:
    return _items(kinds=['waiting'], states=[WAITING_ON_OTHER])


def get_appointment_candidates() -> list[dict]:
    return _items(kinds=['appointment'], states=[APPOINTMENT_PROPOSED])


def list_items(kind=None, state=None, contact_id=None, include_closed=False, limit=50) -> list[dict]:
    kinds = [kind] if kind else None
    states = [state.upper()] if state else None
    if states and states[0] not in store.OPEN | store.CLOSED | {store.SNOOZED}:
        raise ValueError(f'Unknown state {state}')
    return _items(kinds=kinds, states=states, contact_id=contact_id, include_closed=include_closed, limit=limit)


def search(text=None, contact=None, include_closed=False, limit=50) -> list[dict]:
    contact_ids = [c['id'] for c in search_contacts(contact)] if contact else [None]
    found = []
    for contact_id in contact_ids:
        found += _items(text=text, contact_id=contact_id, include_closed=include_closed, limit=limit)
    return found[:limit]


def get_item(item_id: str) -> dict:
    with store.connect() as db:
        item = store.get_item(db, item_id)
        if item is None:
            raise KeyError(f'Unknown item {item_id}')
        draft = db.execute('SELECT body, created_at FROM drafts WHERE item_id=? ORDER BY id DESC LIMIT 1', (item_id,)).fetchone()
        item['draft'] = dict(draft) if draft else None
        return item


def get_contact_state(contact: str) -> dict:
    matches = search_contacts(contact)
    if not matches:
        raise KeyError(f'No contact matches {contact}')
    result = []
    with store.connect() as db:
        for match in matches[:5]:
            identities = [dict(r) for r in db.execute('SELECT channel, address, status FROM identities WHERE contact_id=?', (match['id'],))]
            proposals = [dict(r) for r in db.execute(
                "SELECT p.channel, p.address, p.contact_id FROM identity_proposals p JOIN identities i "
                "ON i.channel=p.channel AND i.address=p.address WHERE p.status='proposed' AND (i.contact_id=? OR p.contact_id=?)",
                (match['id'], match['id']))]
            items = store.query_items(db, contact_id=match['id'])
            result.append(dict(match, identities=identities, proposed_links=proposals, open_items=items))
    return {'contacts': result}


def search_contacts(text: str) -> list[dict]:
    pattern = f'%{text.strip()}%'
    with store.connect() as db:
        rows = db.execute('''SELECT DISTINCT c.id, c.name FROM contacts c LEFT JOIN identities i ON i.contact_id=c.id
                             WHERE c.id LIKE ? OR c.name LIKE ? OR i.address LIKE ? OR i.display_name LIKE ?
                             ORDER BY c.name LIMIT 20''', (pattern,) * 4)
        return [dict(row) for row in rows]


def link_contact(channel: str, address: str, contact_id: str, decision: str = 'confirm') -> dict:
    settings, now = config.load(), store.utcnow()
    with store.connect() as db:
        result = store.link_identity(db, channel, address, contact_id, decision, now)
    _changed(settings, now)
    return result


def _transition(item_id, action, until=None, note=None):
    settings, now = config.load(), store.utcnow()
    with store.connect() as db:
        item = store.transition(db, item_id, action, now, until=until, note=note)
    _changed(settings, now)
    return item


def mark_done(item_id: str, note: str | None = None) -> dict:
    return _transition(item_id, 'complete', note=note)


def ignore_item(item_id: str) -> dict:
    return _transition(item_id, 'ignore')


def cancel_commitment(item_id: str) -> dict:
    return _transition(item_id, 'cancel')


def reopen_item(item_id: str) -> dict:
    return _transition(item_id, 'reopen')


def parse_until(value: str, now: datetime | None = None) -> datetime:
    """Accept an ISO date/time, 'tomorrow', or '<n>h' / '<n>d'."""
    settings = config.load()
    now = _now(now)
    value = str(value).strip().casefold()
    local = now.astimezone(settings['tz'])
    if value == 'tomorrow':
        return (local + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
    match = re.fullmatch(r'(\d{1,3})\s*([hd])', value)
    if match:
        return now + timedelta(**{'hours' if match[2] == 'h' else 'days': int(match[1])})
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return datetime.strptime(value, '%Y-%m-%d').replace(hour=8, tzinfo=settings['tz'])
    parsed = datetime.fromisoformat(value.upper().replace('Z', '+00:00'))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=settings['tz'])


def snooze_item(item_id: str, until) -> dict:
    return _transition(item_id, 'snooze', until=until if isinstance(until, datetime) else parse_until(until))


def create_item(kind: str, title: str, summary: str = '', contact: str | None = None, action: str | None = None,
                due: str | None = None, due_text: str | None = None) -> dict:
    settings, now = config.load(), store.utcnow()
    contact_id = None
    if contact:
        matches = search_contacts(contact)
        exact = [m for m in matches if contact.casefold() in (m['id'], m['name'].casefold())]
        if len(exact) == 1 or len(matches) == 1:
            contact_id = (exact or matches)[0]['id']
        elif matches:
            raise ValueError('Several contacts match; use a contact id: ' + ', '.join(m['id'] for m in matches[:5]))
        else:
            with store.connect() as db:
                contact_id = store.contact_for(db, 'manual', contact, contact, now)
    with store.connect() as db:
        item = store.create_manual(db, kind=kind, title=title, summary=summary, now=now, contact_id=contact_id,
                                   action=action, due_at=due, due_text=due_text)
    _changed(settings, now)
    return item


def update_item(item_id: str, **changes) -> dict:
    settings, now = config.load(), store.utcnow()
    with store.connect() as db:
        item = store.update_fields(db, item_id, {k: v for k, v in changes.items() if v is not None}, now)
    _changed(settings, now)
    return item


def draft_reply(item_id: str) -> dict:
    """Generate a local draft for a reply item. Drafts are stored, never sent."""
    settings, now = config.load(), store.utcnow()
    with store.connect() as db:
        item = store.get_item(db, item_id)
        if item is None:
            raise KeyError(f'Unknown item {item_id}')
        if item['kind'] not in ('reply', 'appointment'):
            raise ValueError('Drafts are for replies and appointment proposals')
        contact = db.execute('SELECT name FROM contacts WHERE id=?', (item['contact_id'],)).fetchone()
    body = classify.draft(item, contact['name'] if contact else None, settings)
    with store.connect() as db:
        db.execute('INSERT INTO drafts(item_id, body, model, created_at) VALUES(?,?,?,?)',
                   (item_id, body, settings['model'], store.iso(now)))
    log.event('draft_generated', item_id=item_id)
    export.write_all(settings, now)
    return {'item_id': item_id, 'draft': body, 'sent': False}


def import_contacts(path: str | None = None) -> dict:
    """Import a Google Contacts CSV now; starred contacts become favourites."""
    settings, now = config.load(), store.utcnow()
    if path:
        settings = dict(settings, google_contacts_csv=path)
    with store.connect() as db:
        result = google_contacts.sync(db, settings, now, force=True)
        if result is None:
            raise FileNotFoundError(f'No contacts export at {google_contacts.csv_path(settings)}')
        scan.refresh(db, now, settings)
    export.write_all(settings, now)
    return result


def current_brief(save: bool = False) -> dict:
    settings, now = config.load(), store.utcnow()
    summary = get_attention_summary(now)
    export.write_all(settings, now)
    path = export.archive_brief(summary['brief'], now, settings) if save else None
    return {'brief': summary['brief'], 'counts': summary['counts'], 'archived': str(path) if path else None}


def status(probe: bool = True) -> dict:
    settings = config.load()
    with store.connect() as db:
        meta = {'last_scan': store.meta_get(db, 'last_scan'), 'paused': store.meta_get(db, 'paused', False),
                'msty': store.meta_get(db, 'msty')}
        items = export.snapshot(db, store.utcnow(), settings)['items']
    scan_info = meta['last_scan'] or {}
    sources = {name: value['status'] for name, value in (scan_info.get('sources') or {}).items()}
    mail = [v for k, v in sources.items() if k.startswith('email:')]
    email = ('OK' if mail and all(v == 'ok' for v in mail) else 'PARTIAL' if any(v == 'ok' for v in mail)
             else 'UNAVAILABLE' if mail else 'NOT SCANNED')
    from integrations.msty.personal import store as accounts
    calendar_enabled = any(a.get('kind') == 'calendar' and a.get('enabled') for a in accounts.load()['accounts'])
    return {
        'email': email, 'email_accounts': sources,
        'telegram': chat_status(sources, 'telegram', 'python -m integrations.attention.telegram_user setup'),
        'whatsapp': chat_status(sources, 'whatsapp', 'python -m integrations.attention.whatsapp pair'),
        'calendar': 'CONFIGURED' if calendar_enabled else 'NOT CONFIGURED',
        'msty': ('OK' if classify.available(settings) else 'UNAVAILABLE') if probe else (meta['msty'] or {}).get('status', 'unknown'),
        'model': settings['model'], 'paused': meta['paused'],
        **export.counts(items),
        'last_scan': scan_info.get('finished_at'), 'pending_analysis': scan_info.get('pending', 0),
        'state_folder': str(config.home()),
    }


def chat_status(sources: dict, channel: str, setup: str) -> str:
    if channel in sources:
        return {'ok': 'OK', 'stale': 'STALE (listener not running; using the stored copy)'}.get(sources[channel], 'UNAVAILABLE')
    return f'NOT SET UP ({setup})'


def set_paused(paused: bool) -> dict:
    with store.connect() as db:
        store.meta_set(db, 'paused', bool(paused))
    log.event('scan_paused' if paused else 'scan_resumed')
    export.write_all()
    return {'paused': bool(paused)}
