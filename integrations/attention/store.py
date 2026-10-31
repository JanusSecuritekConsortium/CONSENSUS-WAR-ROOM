"""Authoritative attention state in SQLite; Markdown files are generated from it.

Model output reaches this module only through `upsert_from_source`, which never
reopens an item the user (or a detected reply) already closed.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import unicodedata
import uuid

from . import config, log

# Semantic states. NO_ACTION belongs to conversations, the rest to items.
NO_ACTION = 'NO_ACTION'
NEEDS_REPLY = 'NEEDS_REPLY'
WAITING_ON_ME = 'WAITING_ON_ME'
WAITING_ON_OTHER = 'WAITING_ON_OTHER'
COMMITMENT_OPEN = 'COMMITMENT_OPEN'
APPOINTMENT_PROPOSED = 'APPOINTMENT_PROPOSED'
SNOOZED = 'SNOOZED'
COMPLETED = 'COMPLETED'
IGNORED = 'IGNORED'
CANCELLED = 'CANCELLED'

KIND_STATES = {
    'reply': {NEEDS_REPLY, WAITING_ON_ME},
    'waiting': {WAITING_ON_OTHER},
    'commitment': {COMMITMENT_OPEN},
    'appointment': {APPOINTMENT_PROPOSED},
}
OPEN = set().union(*KIND_STATES.values())
CLOSED = {COMPLETED, IGNORED, CANCELLED}
PRIORITIES = ('LOW', 'NORMAL', 'HIGH', 'URGENT')

SCHEMA = '''
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS contacts(
    id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS identities(
    channel TEXT NOT NULL, address TEXT NOT NULL, contact_id TEXT NOT NULL REFERENCES contacts(id),
    display_name TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'confirmed',
    PRIMARY KEY(channel, address));
CREATE TABLE IF NOT EXISTS identity_proposals(
    channel TEXT NOT NULL, address TEXT NOT NULL, contact_id TEXT NOT NULL, reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed', created_at TEXT NOT NULL,
    PRIMARY KEY(channel, address, contact_id));
CREATE TABLE IF NOT EXISTS threads(
    key TEXT PRIMARY KEY, channel TEXT NOT NULL, account TEXT NOT NULL, contact_id TEXT,
    subject TEXT NOT NULL DEFAULT '', last_message_at TEXT, last_direction TEXT,
    fingerprint TEXT, processed_fingerprint TEXT, state TEXT, retained_json TEXT,
    error TEXT, updated_at TEXT NOT NULL, address TEXT);
CREATE TABLE IF NOT EXISTS items(
    id TEXT PRIMARY KEY, key TEXT NOT NULL UNIQUE, kind TEXT NOT NULL, state TEXT NOT NULL,
    prior_state TEXT, priority TEXT NOT NULL DEFAULT 'NORMAL', overdue INTEGER NOT NULL DEFAULT 0,
    priority_reasons TEXT NOT NULL DEFAULT '[]', pinned_priority TEXT, urgent INTEGER NOT NULL DEFAULT 0,
    follow_ups INTEGER NOT NULL DEFAULT 0, confidence REAL NOT NULL, review INTEGER NOT NULL DEFAULT 0,
    contact_id TEXT, channel TEXT NOT NULL, thread_key TEXT, source_ref TEXT,
    title TEXT NOT NULL, summary TEXT NOT NULL, action TEXT, due_at TEXT, due_text TEXT,
    event_json TEXT, snoozed_until TEXT, resolution TEXT, origin TEXT NOT NULL,
    first_seen_at TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, closed_at TEXT);
CREATE INDEX IF NOT EXISTS items_state ON items(state);
CREATE INDEX IF NOT EXISTS items_thread ON items(thread_key);
CREATE TABLE IF NOT EXISTS drafts(
    id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT NOT NULL REFERENCES items(id),
    body TEXT NOT NULL, model TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS exports(path TEXT PRIMARY KEY, sha TEXT NOT NULL);
'''

# Allowed state changes requested by people or tools. Model updates use their own, stricter path.
TRANSITIONS = {
    'complete': (OPEN | {SNOOZED}, COMPLETED),
    'ignore': (OPEN | {SNOOZED}, IGNORED),
    'cancel': (OPEN | {SNOOZED}, CANCELLED),
    'snooze': (OPEN, SNOOZED),
    'reopen': (CLOSED | {SNOOZED}, None),
}


class InvalidTransition(ValueError):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat(timespec='seconds') if value else None


def parse(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def digest(*parts: str, length: int = 12) -> str:
    return hashlib.sha256('\0'.join(parts).encode()).hexdigest()[:length]


def slug(text: str) -> str:
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', text.casefold()).strip('-')[:40] or 'contact'


def normalized(text: str) -> str:
    return re.sub(r'\W+', ' ', text.casefold()).strip()


def database_path(home: Path | None = None) -> Path:
    return (home or config.home()) / 'system' / 'state.sqlite3'


@contextmanager
def connect(home: Path | None = None):
    path = database_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA foreign_keys=ON')
        db.executescript(SCHEMA)
        migrate(db)
        with db:
            yield db
    finally:
        db.close()


def migrate(db) -> None:
    """Bring an older store up to the current schema without losing anything."""
    if 'address' not in {row['name'] for row in db.execute('PRAGMA table_info(threads)')}:
        db.execute('ALTER TABLE threads ADD COLUMN address TEXT')
        # Where the contact has a single identity on the thread's channel, that is the thread's address.
        # Other threads get theirs at the next scan.
        db.execute('''UPDATE threads SET address=(SELECT address FROM identities i
                          WHERE i.contact_id=threads.contact_id AND i.channel=threads.channel)
                      WHERE contact_id IS NOT NULL AND (SELECT COUNT(*) FROM identities i
                          WHERE i.contact_id=threads.contact_id AND i.channel=threads.channel)=1''')
        db.commit()


def meta_get(db, key, default=None):
    row = db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
    return json.loads(row['value']) if row else default


def meta_set(db, key, value) -> None:
    db.execute('INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
               (key, json.dumps(value, sort_keys=True)))


CLAIM_MINUTES = 45


def claim_scan(db, now: datetime, minutes: int = CLAIM_MINUTES) -> str | None:
    """One scan at a time across processes. Returns the owner token, or None while another scan holds it.

    A single conditional write takes the claim, so two processes cannot both win; a crashed scan's claim expires.
    """
    owner = uuid.uuid4().hex
    claim = json.dumps({'owner': owner, 'until': iso(now + timedelta(minutes=minutes))}, sort_keys=True)
    db.commit()
    taken = db.execute(
        "INSERT INTO meta(key,value) VALUES('scan_claim',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value "
        "WHERE coalesce(json_extract(meta.value,'$.until'), json_extract(meta.value,'$')) <= ?",
        (claim, iso(now))).rowcount
    db.commit()
    return owner if taken else None


def renew_scan(db, owner: str, now: datetime, minutes: int = CLAIM_MINUTES) -> bool:
    """Extend a long scan's claim; False means another scan has taken over."""
    renewed = db.execute(
        "UPDATE meta SET value=json_set(value,'$.until',?) WHERE key='scan_claim' AND json_extract(value,'$.owner')=?",
        (iso(now + timedelta(minutes=minutes)), owner)).rowcount
    db.commit()
    return bool(renewed)


def release_scan(db, owner: str) -> None:
    """Release only this scan's own claim, never a newer scan's."""
    db.execute("DELETE FROM meta WHERE key='scan_claim' AND json_extract(value,'$.owner')=?", (owner,))


# Contacts --------------------------------------------------------------------

def contact_for(db, channel: str, address: str, display_name: str, now: datetime) -> str:
    """Return the contact for an identity, creating a separate contact for a new one.

    Names alone never merge identities: a matching name only records a proposal.
    """
    address = address.strip().casefold()
    row = db.execute('SELECT contact_id FROM identities WHERE channel=? AND address=?', (channel, address)).fetchone()
    if row:
        if display_name:
            db.execute("UPDATE identities SET display_name=? WHERE channel=? AND address=? AND display_name=''",
                       (display_name, channel, address))
        return row['contact_id']
    name = display_name.strip() or address.split('@')[0]
    base = slug(name)
    contact_id = base
    while db.execute('SELECT 1 FROM contacts WHERE id=?', (contact_id,)).fetchone():
        contact_id = f'{base}-{digest(channel, address, length=4)}'
        if db.execute('SELECT 1 FROM contacts WHERE id=?', (contact_id,)).fetchone():
            contact_id = f'{base}-{digest(channel, address, length=8)}'
    stamp = iso(now)
    db.execute('INSERT INTO contacts(id,name,created_at,updated_at) VALUES(?,?,?,?)', (contact_id, name, stamp, stamp))
    db.execute('INSERT INTO identities(channel,address,contact_id,display_name) VALUES(?,?,?,?)',
               (channel, address, contact_id, display_name))
    for match in db.execute('SELECT id FROM contacts WHERE lower(name)=lower(?) AND id<>?', (name, contact_id)):
        db.execute('INSERT OR IGNORE INTO identity_proposals VALUES(?,?,?,?,?,?)',
                   (channel, address, match['id'], 'same display name', 'proposed', stamp))
    log.event('contact_created', contact_id=contact_id, channel=channel)
    return contact_id


def link_identity(db, channel: str, address: str, contact_id: str, decision: str, now: datetime) -> dict:
    """Confirm or reject a mapping. Confirming moves this identity and its own conversations and items.

    Other identities of the former contact keep their records. Only when the former contact has no
    identity left is it merged: its remaining records move and it is removed.
    """
    address = address.strip().casefold()
    if decision not in ('confirm', 'reject'):
        raise ValueError('decision must be confirm or reject')
    if not db.execute('SELECT 1 FROM contacts WHERE id=?', (contact_id,)).fetchone():
        raise KeyError('Unknown contact')
    row = db.execute('SELECT contact_id FROM identities WHERE channel=? AND address=?', (channel, address)).fetchone()
    if not row:
        raise KeyError('Unknown identity')
    if decision == 'reject':
        db.execute("INSERT INTO identity_proposals VALUES(?,?,?,?,?,?) ON CONFLICT DO UPDATE SET status='rejected'",
                   (channel, address, contact_id, 'rejected by user', 'rejected', iso(now)))
        return {'status': 'separate', 'contact_id': row['contact_id']}
    old = row['contact_id']
    db.execute("UPDATE identities SET contact_id=?, status='confirmed' WHERE channel=? AND address=?",
               (contact_id, channel, address))
    db.execute("UPDATE identity_proposals SET status='accepted' WHERE channel=? AND address=? AND contact_id=?",
               (channel, address, contact_id))
    own = [row['key'] for row in db.execute('SELECT key FROM threads WHERE channel=? AND address=? AND contact_id=?',
                                             (channel, address, old))]
    if own:
        marks = ','.join('?' * len(own))
        db.execute(f'UPDATE items SET contact_id=? WHERE contact_id=? AND thread_key IN ({marks})', (contact_id, old, *own))
        db.execute(f'UPDATE threads SET contact_id=? WHERE key IN ({marks})', (contact_id, *own))
    if old != contact_id and not db.execute('SELECT 1 FROM identities WHERE contact_id=?', (old,)).fetchone():
        for table in ('items', 'threads'):
            db.execute(f'UPDATE {table} SET contact_id=? WHERE contact_id=?', (contact_id, old))
        db.execute('DELETE FROM identity_proposals WHERE contact_id=?', (old,))
        db.execute('DELETE FROM contacts WHERE id=?', (old,))
    log.event('identity_linked', contact_id=contact_id, channel=channel)
    return {'status': 'confirmed', 'contact_id': contact_id}


# Items -----------------------------------------------------------------------

def item_id(kind: str, key: str) -> str:
    return f'{kind}-{digest(key, length=10)}'


def row_dict(row) -> dict:
    item = dict(row)
    item['priority_reasons'] = json.loads(item.get('priority_reasons') or '[]')
    item['event'] = json.loads(item.pop('event_json') or 'null')
    item['review'] = bool(item['review'])
    item['overdue'] = bool(item['overdue'])
    item['urgent'] = bool(item['urgent'])
    return item


def get_item(db, identity: str) -> dict | None:
    row = db.execute('SELECT * FROM items WHERE id=?', (identity,)).fetchone()
    return row_dict(row) if row else None


def upsert_from_source(db, *, key: str, kind: str, state: str, fields: dict, now: datetime) -> str | None:
    """Create or refresh an item derived from a source. Closed items stay closed."""
    if state not in KIND_STATES[kind]:
        raise ValueError('state does not match kind')
    identity = item_id(kind, key)
    existing = db.execute('SELECT * FROM items WHERE key=?', (key,)).fetchone()
    stamp = iso(now)
    if existing is None:
        values = dict(fields, id=identity, key=key, kind=kind, state=state, origin=fields.get('origin', 'source'),
                      first_seen_at=fields.get('first_seen_at') or stamp, created_at=stamp, updated_at=stamp)
        if 'event' in values:
            values['event_json'] = json.dumps(values.pop('event'), sort_keys=True)
        columns = ','.join(values)
        db.execute(f'INSERT INTO items({columns}) VALUES({",".join("?" * len(values))})', tuple(values.values()))
        log.event('commitment_created' if kind == 'commitment' else 'attention_item_created',
                  item_id=identity, kind=kind, state=state)
        return identity
    if existing['state'] in CLOSED:
        return None
    updates = {name: value for name, value in fields.items() if name not in ('origin', 'first_seen_at')}
    if 'event' in updates:
        updates['event_json'] = json.dumps(updates.pop('event'), sort_keys=True)
    if existing['state'] == SNOOZED:
        updates['prior_state'] = state
    else:
        updates['state'] = state
    changed = {name: value for name, value in updates.items() if existing[name] != value}
    if changed:
        changed['updated_at'] = stamp
        db.execute(f'UPDATE items SET {",".join(n + "=?" for n in changed)} WHERE id=?', (*changed.values(), identity))
        log.event('attention_item_updated', item_id=identity, fields=sorted(changed))
    return identity


def close_from_source(db, identity: str, resolution: str, now: datetime) -> bool:
    """Close an open item because the conversation shows it is handled."""
    row = db.execute('SELECT state, kind FROM items WHERE id=?', (identity,)).fetchone()
    if not row or row['state'] in CLOSED:
        return False
    db.execute('UPDATE items SET state=?, resolution=?, snoozed_until=NULL, updated_at=?, closed_at=? WHERE id=?',
               (COMPLETED, resolution, iso(now), iso(now), identity))
    name = {'replied': 'reply_detected', 'detected_done': 'commitment_completed'}.get(resolution, 'attention_item_updated')
    log.event(name, item_id=identity, resolution=resolution)
    return True


def transition(db, identity: str, action: str, now: datetime, *, until: datetime | None = None,
               note: str | None = None) -> dict:
    """Apply a user or tool requested change after validating it."""
    if action not in TRANSITIONS:
        raise InvalidTransition(f'Unknown action {action}')
    item = get_item(db, identity)
    if item is None:
        raise KeyError(f'Unknown item {identity}')
    allowed, target = TRANSITIONS[action]
    if item['state'] not in allowed:
        raise InvalidTransition(f'Cannot {action} an item in state {item["state"]}')
    if action == 'cancel' and item['kind'] != 'commitment':
        raise InvalidTransition('Only commitments can be cancelled')
    stamp = iso(now)
    if action == 'snooze':
        if not until or until <= now:
            raise InvalidTransition('Snooze needs a future time')
        db.execute('UPDATE items SET prior_state=state, state=?, snoozed_until=?, updated_at=? WHERE id=?',
                   (SNOOZED, iso(until), stamp, identity))
    elif action == 'reopen':
        state = item['prior_state'] if item['state'] == SNOOZED else open_state(item)
        db.execute('UPDATE items SET state=?, snoozed_until=NULL, resolution=NULL, closed_at=NULL, updated_at=? WHERE id=?',
                   (state, stamp, identity))
    else:
        db.execute('UPDATE items SET state=?, resolution=?, snoozed_until=NULL, updated_at=?, closed_at=? WHERE id=?',
                   (target, note or f'user:{action}', stamp, stamp, identity))
    log.event('item_' + action, item_id=identity)
    return get_item(db, identity)


def open_state(item: dict) -> str:
    states = KIND_STATES[item['kind']]
    return item['prior_state'] if item.get('prior_state') in states else sorted(states)[0]


def create_manual(db, *, kind: str, title: str, summary: str, now: datetime, contact_id: str | None = None,
                  action: str | None = None, due_at: str | None = None, due_text: str | None = None,
                  channel: str = 'manual', state: str | None = None) -> dict:
    """Record something a person told an agent, e.g. a promise made in person."""
    if kind not in KIND_STATES:
        raise ValueError('Unknown kind')
    state = state or sorted(KIND_STATES[kind])[0]
    if not title.strip():
        raise ValueError('title is required')
    if contact_id and not db.execute('SELECT 1 FROM contacts WHERE id=?', (contact_id,)).fetchone():
        raise KeyError('Unknown contact')
    if due_at:
        due_at = validate_due(due_at)
    key = f'manual:{kind}:{normalized(title)}:{contact_id or ""}'
    identity = upsert_from_source(db, key=key, kind=kind, state=state, now=now, fields={
        'title': title.strip()[:160], 'summary': summary.strip()[:300] or title.strip()[:160], 'action': action,
        'confidence': 1.0, 'contact_id': contact_id, 'channel': channel, 'due_at': due_at, 'due_text': due_text,
        'origin': 'manual'})
    return get_item(db, identity or item_id(kind, key))


EDITABLE = {'title', 'summary', 'action', 'due_at', 'due_text', 'contact_id', 'priority'}


def update_fields(db, identity: str, changes: dict, now: datetime) -> dict:
    unknown = set(changes) - EDITABLE
    if unknown:
        raise ValueError(f'Fields cannot be edited: {", ".join(sorted(unknown))}')
    if get_item(db, identity) is None:
        raise KeyError(f'Unknown item {identity}')
    if changes.get('due_at'):
        changes['due_at'] = validate_due(changes['due_at'])
    if 'priority' in changes:
        if changes['priority'] not in PRIORITIES:
            raise ValueError('Unknown priority')
        changes['pinned_priority'] = changes.pop('priority')  # kept over the computed priority
    if changes.get('contact_id') and not db.execute('SELECT 1 FROM contacts WHERE id=?', (changes['contact_id'],)).fetchone():
        raise KeyError('Unknown contact')
    if changes:
        assignments = ','.join(name + '=?' for name in changes)
        db.execute(f"UPDATE items SET {assignments}, origin=CASE origin WHEN 'source' THEN 'edited' ELSE origin END, "
                   'updated_at=? WHERE id=?',
                   (*changes.values(), iso(now), identity))
        log.event('attention_item_updated', item_id=identity, fields=sorted(changes))
    return get_item(db, identity)


def validate_due(value: str) -> str:
    """Accept a date (YYYY-MM-DD) or a timestamp; never invent one from vague text."""
    value = str(value).strip()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        datetime.strptime(value, '%Y-%m-%d')
        return value
    return iso(parse(value))


def wake_snoozed(db, now: datetime) -> list[str]:
    woken = []
    for row in db.execute('SELECT id, prior_state, kind FROM items WHERE state=? AND snoozed_until<=?', (SNOOZED, iso(now))):
        state = row['prior_state'] if row['prior_state'] in KIND_STATES[row['kind']] else sorted(KIND_STATES[row['kind']])[0]
        db.execute('UPDATE items SET state=?, snoozed_until=NULL, updated_at=? WHERE id=?', (state, iso(now), row['id']))
        log.event('snooze_expired', item_id=row['id'])
        woken.append(row['id'])
    return woken


def query_items(db, *, kinds=None, states=None, contact_id=None, text=None, include_closed=False, limit=50) -> list[dict]:
    sql, args = 'SELECT * FROM items WHERE 1=1', []
    if kinds:
        sql += f' AND kind IN ({",".join("?" * len(kinds))})'
        args += list(kinds)
    if states:
        sql += f' AND state IN ({",".join("?" * len(states))})'
        args += list(states)
    elif not include_closed:
        sql += f' AND state NOT IN ({",".join("?" * len(CLOSED))})'
        args += sorted(CLOSED)
    if contact_id:
        sql += ' AND contact_id=?'
        args.append(contact_id)
    if text:
        sql += ' AND (title LIKE ? OR summary LIKE ? OR action LIKE ? OR contact_id LIKE ?)'
        args += [f'%{text}%'] * 4
    sql += " ORDER BY CASE priority WHEN 'URGENT' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'NORMAL' THEN 2 ELSE 3 END, first_seen_at LIMIT ?"
    args.append(max(1, min(int(limit), 200)))
    return [row_dict(row) for row in db.execute(sql, args)]
